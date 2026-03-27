from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from logs import log_store


class _NoopLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class LogStorePhase1Tests(unittest.TestCase):
    def test_init_log_storage_creates_schema_table_and_indexes_without_memory_fk(self) -> None:
        observed = {
            'queries': [],
            'committed': False,
        }

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
                observed['queries'].append((query, params))

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed['committed'] = True

        log_store.init_log_storage(
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        queries = [entry[0] for entry in observed['queries']]
        joined = '\n'.join(queries)
        self.assertIn('CREATE SCHEMA IF NOT EXISTS observability;', joined)
        self.assertIn('CREATE TABLE IF NOT EXISTS observability.chat_log_events', joined)
        self.assertIn('chat_log_events_ts_idx', joined)
        self.assertIn('chat_log_events_conversation_ts_idx', joined)
        self.assertIn('chat_log_events_conversation_turn_ts_idx', joined)
        self.assertIn('chat_log_events_status_ts_idx', joined)
        self.assertNotIn('REFERENCES', joined.upper())
        self.assertTrue(observed['committed'])

    def test_insert_chat_log_event_inserts_minimal_event(self) -> None:
        observed = {
            'query': None,
            'params': None,
            'committed': False,
        }

        class FakeCursor:
            def __init__(self) -> None:
                self.rowcount = 1

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                observed['query'] = query
                observed['params'] = params

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed['committed'] = True

        inserted = log_store.insert_chat_log_event(
            {
                'event_id': 'evt-1',
                'conversation_id': 'conv-1',
                'turn_id': 'turn-1',
                'ts': '2026-03-27T10:00:00Z',
                'stage': 'turn_start',
                'status': 'ok',
                'duration_ms': 18,
                'payload_json': {'web_search_enabled': False},
            },
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertTrue(inserted)
        self.assertIn('INSERT INTO observability.chat_log_events', str(observed['query']))
        self.assertEqual(observed['params'][0], 'evt-1')
        self.assertEqual(observed['params'][1], 'conv-1')
        self.assertEqual(observed['params'][2], 'turn-1')
        self.assertEqual(observed['params'][4], 'turn_start')
        self.assertEqual(observed['params'][5], 'ok')
        self.assertEqual(observed['params'][6], 18)
        self.assertEqual(json.loads(observed['params'][7]), {'web_search_enabled': False})
        self.assertTrue(observed['committed'])

    def test_insert_chat_log_event_rejects_invalid_status(self) -> None:
        with self.assertRaisesRegex(ValueError, 'invalid chat log event status'):
            log_store.insert_chat_log_event(
                {
                    'event_id': 'evt-status',
                    'conversation_id': 'conv-status',
                    'turn_id': 'turn-status',
                    'ts': '2026-03-27T10:00:00Z',
                    'stage': 'llm_call',
                    'status': 'unknown',
                },
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )

    def test_insert_chat_log_event_requires_required_fields(self) -> None:
        with self.assertRaisesRegex(ValueError, 'missing required chat log event fields'):
            log_store.insert_chat_log_event(
                {
                    'event_id': 'evt-missing',
                    'conversation_id': 'conv-missing',
                    'ts': '2026-03-27T10:00:00Z',
                    'stage': 'llm_call',
                    'status': 'ok',
                },
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )
