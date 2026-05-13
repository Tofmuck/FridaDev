from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_store


class _SchemaCursor:
    def __init__(self, observed_queries: list[str]) -> None:
        self._observed_queries = observed_queries

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, query, params=None):
        self._observed_queries.append(str(query))


class _SchemaConnection:
    def __init__(self, observed_queries: list[str]) -> None:
        self._observed_queries = observed_queries
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _SchemaCursor(self._observed_queries)

    def commit(self):
        self.committed = True


class _MutableIdentityCursor:
    def __init__(
        self,
        state: dict[str, dict[str, object]],
        audit_state: list[dict[str, object]],
        query_log: list[str],
    ) -> None:
        self._state = state
        self._audit_state = audit_state
        self._query_log = query_log
        self._counter = 0
        self._results: list[tuple[object, ...]] = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def _timestamp(self) -> str:
        self._counter += 1
        return f'2026-04-05T12:00:{self._counter:02d}Z'

    def _row(self, entry: dict[str, object]) -> tuple[object, ...]:
        return (
            entry['subject'],
            entry['content'],
            entry.get('source_trace_id'),
            entry.get('updated_by'),
            entry.get('update_reason'),
            entry['created_ts'],
            entry['updated_ts'],
        )

    def _audit_row(self, entry: dict[str, object]) -> tuple[object, ...]:
        return (
            entry['audit_id'],
            entry['subject'],
            entry['mutation_kind'],
            entry.get('actor'),
            entry.get('reason_code'),
            entry['old_chars'],
            entry['new_chars'],
            entry.get('old_sha256_12'),
            entry.get('new_sha256_12'),
            entry.get('source_trace_id'),
            entry['created_ts'],
        )

    def execute(self, query, params=None):
        normalized = ' '.join(str(query).split()).lower()
        self._query_log.append(normalized)
        params = params or ()

        if normalized.startswith('insert into identity_mutables'):
            subject, content, source_trace_id, updated_by, update_reason = params
            existing = self._state.get(subject)
            created_ts = existing['created_ts'] if existing else self._timestamp()
            entry = {
                'subject': subject,
                'content': content,
                'source_trace_id': source_trace_id,
                'updated_by': updated_by,
                'update_reason': update_reason,
                'created_ts': created_ts,
                'updated_ts': self._timestamp(),
            }
            self._state[subject] = entry
            self._results = [self._row(entry)]
            return

        if normalized.startswith('insert into identity_mutable_audit'):
            (
                subject,
                mutation_kind,
                actor,
                reason_code,
                old_chars,
                new_chars,
                old_sha256_12,
                new_sha256_12,
                source_trace_id,
            ) = params
            entry = {
                'audit_id': f'00000000-0000-0000-0000-000000000{len(self._audit_state) + 1:03d}',
                'subject': subject,
                'mutation_kind': mutation_kind,
                'actor': actor,
                'reason_code': reason_code,
                'old_chars': old_chars,
                'new_chars': new_chars,
                'old_sha256_12': old_sha256_12,
                'new_sha256_12': new_sha256_12,
                'source_trace_id': source_trace_id,
                'created_ts': self._timestamp(),
            }
            self._audit_state.append(entry)
            self._results = [self._audit_row(entry)]
            return

        if normalized.startswith('delete from identity_mutables'):
            subject = str(params[0])
            entry = self._state.pop(subject, None)
            self._results = [self._row(entry)] if entry else []
            return

        if 'from identity_mutable_audit' in normalized and 'where subject = %s' in normalized:
            subject = str(params[0])
            matches = [entry for entry in self._audit_state if entry.get('subject') == subject]
            self._results = [self._audit_row(matches[-1])] if matches else []
            return

        if 'from identity_mutables' in normalized and 'where subject = %s' in normalized:
            subject = str(params[0])
            entry = self._state.get(subject)
            if normalized.startswith('select content from identity_mutables'):
                self._results = [(entry['content'],)] if entry else []
                return
            self._results = [self._row(entry)] if entry else []
            return

        if 'from identity_mutables' in normalized and 'order by subject asc' in normalized:
            self._results = [self._row(self._state[key]) for key in sorted(self._state)]
            return

        raise AssertionError(f'unexpected query for mutable identity seam: {normalized}')

    def fetchone(self):
        return self._results[0] if self._results else None

    def fetchall(self):
        return list(self._results)


class _MutableIdentityConnection:
    def __init__(
        self,
        state: dict[str, dict[str, object]],
        audit_state: list[dict[str, object]],
        query_log: list[str],
    ) -> None:
        self._state = state
        self._audit_state = audit_state
        self._query_log = query_log
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _MutableIdentityCursor(self._state, self._audit_state, self._query_log)

    def commit(self):
        self.committed = True


class IdentityMutablesPhase1BTests(unittest.TestCase):
    def test_init_db_creates_identity_mutables_table_and_index(self) -> None:
        observed_queries: list[str] = []
        original_conn = memory_store._conn
        original_runtime_embedding_value = memory_store._runtime_embedding_value
        original_log_init = memory_store.log_store.init_log_storage

        memory_store._conn = lambda: _SchemaConnection(observed_queries)
        memory_store._runtime_embedding_value = lambda field: 768 if field == 'dimensions' else None
        memory_store.log_store.init_log_storage = lambda conn_factory: None
        try:
            memory_store.init_db()
        finally:
            memory_store._conn = original_conn
            memory_store._runtime_embedding_value = original_runtime_embedding_value
            memory_store.log_store.init_log_storage = original_log_init

        joined = '\n'.join(observed_queries).lower()
        self.assertIn('create table if not exists identity_mutables', joined)
        self.assertIn('constraint identity_mutables_subject_chk', joined)
        self.assertIn('create index if not exists identity_mutables_updated_ts_idx', joined)
        self.assertIn('create table if not exists identity_mutable_audit', joined)
        self.assertIn('constraint identity_mutable_audit_subject_chk', joined)
        self.assertIn('constraint identity_mutable_audit_kind_chk', joined)
        self.assertIn('create index if not exists identity_mutable_audit_subject_created_idx', joined)
        self.assertIn('create table if not exists identity_mutable_staging', joined)
        self.assertIn('create index if not exists identity_mutable_staging_updated_ts_idx', joined)

    def test_mutable_identity_round_trip_keeps_one_canonical_row_per_subject(self) -> None:
        state: dict[str, dict[str, object]] = {}
        audit_state: list[dict[str, object]] = []
        query_log: list[str] = []
        original_conn = memory_store._conn
        memory_store._conn = lambda: _MutableIdentityConnection(state, audit_state, query_log)
        try:
            first_llm = memory_store.upsert_mutable_identity(
                'llm',
                'Frida garde une voix structuree.',
                source_trace_id='00000000-0000-0000-0000-000000000001',
                updated_by='identity-extractor',
                update_reason='initial_seed',
            )
            second_llm = memory_store.upsert_mutable_identity(
                'llm',
                'Frida garde une voix structuree et compacte.',
                source_trace_id='00000000-0000-0000-0000-000000000002',
                updated_by='identity_periodic_agent',
                update_reason='periodic_agent',
            )
            user_item = memory_store.upsert_mutable_identity(
                'user',
                'L utilisateur garde une orientation stable et concise.',
                updated_by='identity-extractor',
                update_reason='initial_seed',
            )
            llm_item = memory_store.get_mutable_identity('llm')
            items = memory_store.list_mutable_identities()
        finally:
            memory_store._conn = original_conn

        self.assertIsNotNone(first_llm)
        self.assertIsNotNone(second_llm)
        self.assertIsNotNone(user_item)
        self.assertEqual(llm_item['content'], 'Frida garde une voix structuree et compacte.')
        self.assertEqual(llm_item['update_reason'], 'periodic_agent')
        self.assertEqual(llm_item['source_trace_id'], '00000000-0000-0000-0000-000000000002')
        self.assertEqual([item['subject'] for item in items], ['llm', 'user'])
        self.assertEqual(len([item for item in items if item['subject'] == 'llm']), 1)
        self.assertEqual(len(state), 2)
        self.assertEqual(len(audit_state), 3)
        self.assertTrue(query_log)
        self.assertTrue(all(('identity_mutables' in query or 'identity_mutable_audit' in query) for query in query_log))

    def test_mutable_identity_audit_records_set_and_clear_without_raw_content(self) -> None:
        state: dict[str, dict[str, object]] = {}
        audit_state: list[dict[str, object]] = []
        query_log: list[str] = []
        original_conn = memory_store._conn
        memory_store._conn = lambda: _MutableIdentityConnection(state, audit_state, query_log)
        try:
            first_content = 'Frida conserve une voix breve et stable.'
            second_content = 'Frida conserve une voix breve, stable et precise.'
            memory_store.upsert_mutable_identity(
                'llm',
                first_content,
                source_trace_id='00000000-0000-0000-0000-000000000010',
                updated_by='admin_identity_mutable_edit',
                update_reason='raison admin libre sensible a ne pas archiver',
                audit_reason_code='set_applied',
            )
            latest_admin_set = memory_store.get_latest_mutable_identity_audit('llm')
            memory_store.upsert_mutable_identity(
                'llm',
                second_content,
                source_trace_id='00000000-0000-0000-0000-000000000011',
                updated_by='identity_periodic_agent',
                update_reason='periodic_agent',
            )
            latest_set = memory_store.get_latest_mutable_identity_audit('llm')
            cleared = memory_store.clear_mutable_identity(
                'llm',
                updated_by='admin_identity_mutable_edit',
                update_reason='obsolete mutable parce que contexte humain libre',
                audit_reason_code='clear_applied',
            )
            latest_clear = memory_store.get_latest_mutable_identity_audit('llm')
        finally:
            memory_store._conn = original_conn

        self.assertIsNotNone(latest_admin_set)
        self.assertEqual(latest_admin_set['mutation_kind'], 'set')
        self.assertEqual(latest_admin_set['actor'], 'admin_identity_mutable_edit')
        self.assertEqual(latest_admin_set['reason_code'], 'set_applied')
        self.assertEqual(latest_admin_set['old_chars'], 0)
        self.assertEqual(latest_admin_set['new_chars'], len(first_content))

        self.assertIsNotNone(latest_set)
        self.assertEqual(latest_set['mutation_kind'], 'set')
        self.assertEqual(latest_set['actor'], 'identity_periodic_agent')
        self.assertEqual(latest_set['reason_code'], 'periodic_agent')
        self.assertEqual(latest_set['old_chars'], len(first_content))
        self.assertEqual(latest_set['new_chars'], len(second_content))
        self.assertEqual(len(latest_set['old_sha256_12']), 12)
        self.assertEqual(len(latest_set['new_sha256_12']), 12)

        self.assertIsNotNone(cleared)
        self.assertIsNotNone(latest_clear)
        self.assertEqual(latest_clear['mutation_kind'], 'clear')
        self.assertEqual(latest_clear['actor'], 'admin_identity_mutable_edit')
        self.assertEqual(latest_clear['reason_code'], 'clear_applied')
        self.assertEqual(latest_clear['old_chars'], len(second_content))
        self.assertEqual(latest_clear['new_chars'], 0)
        self.assertEqual(len(latest_clear['old_sha256_12']), 12)
        self.assertIsNone(latest_clear['new_sha256_12'])
        self.assertNotIn('content', latest_clear)
        self.assertNotIn('raison admin libre sensible', repr(audit_state))
        self.assertNotIn('obsolete mutable parce que contexte humain libre', repr(audit_state))
        self.assertNotIn(first_content, repr(audit_state))
        self.assertNotIn(second_content, repr(audit_state))

    def test_legacy_identity_facade_remains_distinct_from_mutable_canonical_store(self) -> None:
        observed: dict[str, object] = {}
        original_get_identities = memory_store.memory_context_read.get_identities

        def fake_get_identities(subject: str, top_n=None, status='accepted', conn_factory=None, default_top_n=None, logger=None):
            observed['args'] = (subject, top_n, status, default_top_n)
            return [{'identity_id': 'legacy-row', 'subject': subject}]

        memory_store.memory_context_read.get_identities = fake_get_identities
        try:
            rows = memory_store.get_identities('llm', top_n=3, status='accepted')
        finally:
            memory_store.memory_context_read.get_identities = original_get_identities

        self.assertEqual(rows, [{'identity_id': 'legacy-row', 'subject': 'llm'}])
        self.assertEqual(observed['args'], ('llm', 3, 'accepted', memory_store.config.IDENTITY_TOP_N))
