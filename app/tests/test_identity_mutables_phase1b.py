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
    def __init__(self, state: dict[str, dict[str, object]], query_log: list[str]) -> None:
        self._state = state
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

        if 'from identity_mutables' in normalized and 'where subject = %s' in normalized:
            subject = str(params[0])
            entry = self._state.get(subject)
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
    def __init__(self, state: dict[str, dict[str, object]], query_log: list[str]) -> None:
        self._state = state
        self._query_log = query_log
        self.committed = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self):
        return _MutableIdentityCursor(self._state, self._query_log)

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

    def test_mutable_identity_round_trip_keeps_one_canonical_row_per_subject(self) -> None:
        state: dict[str, dict[str, object]] = {}
        query_log: list[str] = []
        original_conn = memory_store._conn
        memory_store._conn = lambda: _MutableIdentityConnection(state, query_log)
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
                updated_by='identity-extractor',
                update_reason='rewrite',
            )
            user_item = memory_store.upsert_mutable_identity(
                'user',
                'L utilisateur prefere des reponses courtes.',
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
        self.assertEqual(llm_item['update_reason'], 'rewrite')
        self.assertEqual(llm_item['source_trace_id'], '00000000-0000-0000-0000-000000000002')
        self.assertEqual([item['subject'] for item in items], ['llm', 'user'])
        self.assertEqual(len([item for item in items if item['subject'] == 'llm']), 1)
        self.assertEqual(len(state), 2)
        self.assertTrue(query_log)
        self.assertTrue(all('identity_mutables' in query for query in query_log))

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
