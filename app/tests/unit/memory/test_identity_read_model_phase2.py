from __future__ import annotations

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import patch


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_read_model_service, admin_identity_runtime_representations_service
from memory import memory_identity_read_model, memory_store

_FORBIDDEN_LEGACY_TEXT_KEYS = {
    'content',
    'content_norm',
    'last_reason',
    'override_reason',
    'reason',
    'content_a',
    'content_b',
}


class _NoopLogger:
    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class _FakeCursor:
    def __init__(self, count_row: tuple[Any, ...], rows: list[tuple[Any, ...]]) -> None:
        self._count_row = count_row
        self._rows = rows
        self._last_query = ''

    def __enter__(self) -> '_FakeCursor':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, _params: tuple[Any, ...]) -> None:
        self._last_query = ' '.join(query.lower().split())

    def fetchone(self) -> tuple[Any, ...]:
        if 'count(*)' in self._last_query:
            return self._count_row
        return self._rows[0] if self._rows else (0,)

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


class _FakeConn:
    def __init__(self, count_row: tuple[Any, ...], rows: list[tuple[Any, ...]]) -> None:
        self._count_row = count_row
        self._rows = rows

    def __enter__(self) -> '_FakeConn':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _FakeCursor:
        return _FakeCursor(self._count_row, self._rows)


class _StoredEvidenceCursor:
    def __init__(self, storage: '_StoredEvidenceStorage') -> None:
        self._storage = storage
        self._one: tuple[Any, ...] = (0,)
        self._many: list[tuple[Any, ...]] = []
        self.rowcount = 0

    def __enter__(self) -> '_StoredEvidenceCursor':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[Any, ...]) -> None:
        normalized_query = ' '.join(query.lower().split())
        self._one = (0,)
        self._many = []
        self.rowcount = 0

        if normalized_query.startswith('insert into identity_evidence'):
            created_ts = datetime(
                2026,
                9,
                3,
                8,
                len(self._storage.rows),
                tzinfo=timezone.utc,
            )
            self._storage.rows.append((f'ev-{len(self._storage.rows) + 1}', *params, created_ts))
            self.rowcount = 1
            return

        if 'from identity_evidence' in normalized_query:
            subject = str(params[0])
            matching = [row for row in self._storage.rows if row[2] == subject]
            if 'count(*)' in normalized_query:
                self._one = (len(matching),)
                return
            limit = int(params[1])
            self._many = [
                (
                    row[0],
                    row[1],
                    row[2],
                    row[3],
                    row[4],
                    row[5],
                    row[6],
                    row[7],
                    row[8],
                    row[9],
                    row[10],
                    row[11],
                    row[12],
                    row[13],
                    row[14],
                )
                for row in sorted(matching, key=lambda item: item[14], reverse=True)[:limit]
            ]
            return

        if 'from identities' in normalized_query or 'from identity_conflicts' in normalized_query:
            return

        raise AssertionError(f'unexpected query in stored evidence fake: {normalized_query}')

    def fetchone(self) -> tuple[Any, ...]:
        return self._one

    def fetchall(self) -> list[tuple[Any, ...]]:
        return list(self._many)


class _StoredEvidenceConn:
    def __init__(self, storage: '_StoredEvidenceStorage') -> None:
        self._storage = storage

    def __enter__(self) -> '_StoredEvidenceConn':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> _StoredEvidenceCursor:
        return _StoredEvidenceCursor(self._storage)

    def commit(self) -> None:
        self._storage.commits += 1


class _StoredEvidenceStorage:
    def __init__(self) -> None:
        self.rows: list[tuple[Any, ...]] = []
        self.commits = 0
        self.connection_count = 0

    def connect(self) -> _StoredEvidenceConn:
        self.connection_count += 1
        return _StoredEvidenceConn(self)


def _empty_static_snapshot(subject: str) -> SimpleNamespace:
    return SimpleNamespace(
        raw_content='',
        source_kind='resource_path_content',
        resource_field=f'{subject}_identity_path',
        configured_path=f'synthetic/{subject}.txt',
        resolution_kind='synthetic',
        resolved_path=f'/synthetic/{subject}.txt',
        editable_via='/api/admin/identity/static',
    )


class IdentityReadModelPhase2Tests(unittest.TestCase):
    def test_dialogue_hints_flow_through_real_store_facades_and_both_admin_responses(self) -> None:
        storage = _StoredEvidenceStorage()
        identity_module = SimpleNamespace(
            build_identity_input=lambda: {'schema_version': 'v2', 'frida': {}, 'user': {}},
            build_identity_block=lambda: ('', []),
        )
        store_facade = SimpleNamespace(
            record_dialogic_context_hints=memory_store.record_dialogic_context_hints,
            record_identity_evidence=memory_store.record_identity_evidence,
            list_identity_fragments=memory_store.list_identity_fragments,
            list_identity_evidence=memory_store.list_identity_evidence,
            list_identity_conflicts=memory_store.list_identity_conflicts,
            get_latest_mutable_identity_audit=lambda _subject: None,
            get_latest_identity_staging_state=lambda: None,
        )
        static_identity_module = SimpleNamespace(read_static_identity_snapshot=_empty_static_snapshot)
        hints = [
            {
                'subject': 'dialogue',
                'content': f'Synthetic dialogic hint {index}',
                'confidence': 0.8,
                'reason_code': 'synthetic_dialogic_context',
            }
            for index in range(1, 4)
        ]

        with patch.object(memory_store, '_conn', storage.connect):
            persisted = store_facade.record_dialogic_context_hints('conv-dialogue', hints)
            store_facade.record_identity_evidence(
                'conv-user',
                [{'subject': 'user', 'content': 'Synthetic user evidence', 'confidence': 0.7}],
            )
            store_facade.record_identity_evidence(
                'conv-llm',
                [{'subject': 'llm', 'content': 'Synthetic llm evidence', 'confidence': 0.6}],
            )
            read_model, read_model_status = admin_identity_read_model_service.identity_read_model_response(
                {'limit': 2},
                memory_store_module=store_facade,
                identity_module=identity_module,
                static_identity_content_module=static_identity_module,
            )
            representations, representations_status = (
                admin_identity_runtime_representations_service.identity_runtime_representations_response(
                    identity_module=identity_module,
                    memory_store_module=store_facade,
                )
            )
            user_evidence = store_facade.list_identity_evidence('user', limit=2)
            llm_evidence = store_facade.list_identity_evidence('llm', limit=2)

            connections_before_rejections = storage.connection_count
            invalid_evidence = store_facade.list_identity_evidence('invalid', limit=2)
            dialogue_fragments = store_facade.list_identity_fragments('dialogue', limit=2)
            dialogue_conflicts = store_facade.list_identity_conflicts('dialogue', limit=2)

        self.assertEqual(persisted['persisted_count'], 3)
        self.assertEqual(read_model_status, 200)
        self.assertEqual(read_model['dialogic_context']['total_count'], 3)
        self.assertEqual(read_model['dialogic_context']['limit'], 2)
        self.assertEqual(len(read_model['dialogic_context']['items']), 2)
        self.assertTrue(read_model['dialogic_context']['stored'])
        self.assertEqual(representations_status, 200)
        self.assertEqual(representations['dialogic_context']['total_count'], 3)
        self.assertEqual(representations['dialogic_context']['limit'], 20)
        self.assertEqual(len(representations['dialogic_context']['items']), 3)
        self.assertTrue(representations['dialogic_context']['stored'])
        self.assertEqual(user_evidence['total_count'], 1)
        self.assertEqual(llm_evidence['total_count'], 1)
        self.assertEqual(
            [row[2] for row in storage.rows],
            ['dialogue', 'dialogue', 'dialogue', 'user', 'llm'],
        )
        self.assertEqual(
            storage.connection_count,
            connections_before_rejections,
            'invalid evidence plus dialogue fragments/conflicts must be rejected before SQL',
        )
        for rejected in (invalid_evidence, dialogue_fragments, dialogue_conflicts):
            self.assertEqual(rejected, {'total_count': 0, 'limit': 2, 'items': []})

        serialized = json.dumps(
            {
                'read_model': read_model['dialogic_context'],
                'representations': representations['dialogic_context'],
            },
            sort_keys=True,
        )
        for hint in hints:
            self.assertNotIn(hint['content'], serialized)

    def test_dialogue_evidence_normalizes_subject_and_counts_before_page_limit(self) -> None:
        rows = [
            (
                f'ev-{index}',
                'conv-dialogue',
                'dialogue',
                f'Dialogue hint {index}',
                f'dialogue hint {index}',
                'episodic',
                'dialogic_context',
                'first_seen',
                'dialogue',
                'inferred',
                0.8,
                'accepted',
                'synthetic_dialogic_context',
                None,
                datetime(2026, 9, 3, 8, index, tzinfo=timezone.utc),
            )
            for index in range(3)
        ]

        snapshot = memory_identity_read_model.list_identity_evidence(
            ' Dialogue ',
            limit=2,
            conn_factory=lambda: _FakeConn((3,), rows[:2]),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 3)
        self.assertEqual(snapshot['limit'], 2)
        self.assertEqual(len(snapshot['items']), 2)
        self.assertTrue(all(item['subject'] == 'dialogue' for item in snapshot['items']))

    def test_dialogue_evidence_empty_storage_is_a_legitimate_zero(self) -> None:
        snapshot = memory_identity_read_model.list_identity_evidence(
            'dialogue',
            limit=2,
            conn_factory=lambda: _FakeConn((0,), []),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot, {'total_count': 0, 'limit': 2, 'items': []})

    def test_list_identity_fragments_returns_compact_snapshot(self) -> None:
        rows = [
            (
                'frag-1',
                'llm',
                'Fragment legacy',
                0.7,
                datetime(2026, 4, 6, 9, 0, tzinfo=timezone.utc),
                datetime(2026, 4, 6, 10, 0, tzinfo=timezone.utc),
                None,
                'durable',
                'self_description',
                'frequent',
                'user',
                'strong',
                0.9,
                'accepted',
                'fragment legacy',
                'reason',
                'conv-1',
                'none',
                '',
                '',
                None,
            )
        ]
        snapshot = memory_identity_read_model.list_identity_fragments(
            'llm',
            limit=5,
            conn_factory=lambda: _FakeConn((3,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 3)
        self.assertEqual(snapshot['limit'], 5)
        item = snapshot['items'][0]
        self.assertEqual(item['identity_id'], 'frag-1')
        self.assertTrue(item['content_present'])
        self.assertEqual(item['content_chars'], len('Fragment legacy'))
        self.assertNotIn('content_sha256_12', item)
        self.assertTrue(item['content_norm_present'])
        self.assertEqual(item['content_norm_chars'], len('fragment legacy'))
        self.assertNotIn('content_norm_sha256_12', item)
        self.assertEqual(item['last_reason_code'], 'text_reason_present')
        self.assertTrue(item['last_reason_present'])
        self.assertEqual(item['last_reason_chars'], len('reason'))
        self.assertTrue(_FORBIDDEN_LEGACY_TEXT_KEYS.isdisjoint(item.keys()))

    def test_list_identity_evidence_returns_compact_snapshot(self) -> None:
        rows = [
            (
                'ev-1',
                'conv-1',
                'user',
                'Evidence text',
                'evidence text',
                'episodic',
                'self_description',
                'rare',
                'situation',
                'weak',
                0.6,
                'accepted',
                'reason',
                None,
                datetime(2026, 4, 6, 11, 0, tzinfo=timezone.utc),
            )
        ]
        snapshot = memory_identity_read_model.list_identity_evidence(
            'user',
            limit=7,
            conn_factory=lambda: _FakeConn((4,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 4)
        self.assertEqual(snapshot['limit'], 7)
        item = snapshot['items'][0]
        self.assertEqual(item['evidence_id'], 'ev-1')
        self.assertTrue(item['content_present'])
        self.assertEqual(item['content_chars'], len('Evidence text'))
        self.assertNotIn('content_sha256_12', item)
        self.assertTrue(item['content_norm_present'])
        self.assertEqual(item['content_norm_chars'], len('evidence text'))
        self.assertEqual(item['reason_code'], 'text_reason_present')
        self.assertTrue(item['reason_present'])
        self.assertEqual(item['reason_chars'], len('reason'))
        self.assertTrue(_FORBIDDEN_LEGACY_TEXT_KEYS.isdisjoint(item.keys()))

    def test_list_identity_conflicts_returns_flattened_pairs(self) -> None:
        rows = [
            (
                'conf-1',
                0.85,
                'contradiction',
                'open',
                datetime(2026, 4, 6, 12, 0, tzinfo=timezone.utc),
                None,
                'frag-a',
                'llm',
                'Version A',
                'accepted',
                None,
                'none',
                'frag-b',
                'llm',
                'Version B',
                'deferred',
                None,
                'force_reject',
            )
        ]
        snapshot = memory_identity_read_model.list_identity_conflicts(
            'llm',
            limit=9,
            conn_factory=lambda: _FakeConn((2,), rows),
            logger=_NoopLogger(),
        )

        self.assertEqual(snapshot['total_count'], 2)
        self.assertEqual(snapshot['limit'], 9)
        item = snapshot['items'][0]
        self.assertEqual(item['conflict_id'], 'conf-1')
        self.assertEqual(item['identity_id_a'], 'frag-a')
        self.assertEqual(item['reason_code'], 'text_reason_present')
        self.assertTrue(item['reason_present'])
        self.assertEqual(item['reason_chars'], len('contradiction'))
        self.assertTrue(item['content_a_present'])
        self.assertEqual(item['content_a_chars'], len('Version A'))
        self.assertNotIn('content_a_sha256_12', item)
        self.assertTrue(item['content_b_present'])
        self.assertEqual(item['content_b_chars'], len('Version B'))
        self.assertNotIn('content_b_sha256_12', item)
        self.assertTrue(_FORBIDDEN_LEGACY_TEXT_KEYS.isdisjoint(item.keys()))


if __name__ == '__main__':
    unittest.main()
