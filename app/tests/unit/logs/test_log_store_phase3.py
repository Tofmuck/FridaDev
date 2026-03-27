from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
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


class LogStorePhase3Tests(unittest.TestCase):
    def test_read_chat_log_events_supports_filters_and_pagination(self) -> None:
        observed: dict[str, Any] = {'queries': []}

        class FakeCursor:
            def __init__(self) -> None:
                self._step = 0

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                observed['queries'].append((query, params))
                self._step += 1

            def fetchone(self) -> tuple[int]:
                return (3,)

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        'evt-2',
                        'conv-1',
                        'turn-1',
                        datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc),
                        'llm_call',
                        'ok',
                        25,
                        {'model': 'openrouter/test', 'response_chars': 42},
                    ),
                    (
                        'evt-1',
                        'conv-1',
                        'turn-1',
                        datetime(2026, 3, 27, 11, 59, tzinfo=timezone.utc),
                        'prompt_prepared',
                        'ok',
                        None,
                        {'prompt_kind': 'chat_system_augmented', 'messages_count': 8},
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_chat_log_events(
            limit=2,
            offset=1,
            conversation_id='conv-1',
            turn_id='turn-1',
            stage='llm_call',
            status='ok',
            ts_from='2026-03-27T11:00:00Z',
            ts_to='2026-03-27T13:00:00Z',
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['count'], 2)
        self.assertEqual(result['total'], 3)
        self.assertEqual(result['limit'], 2)
        self.assertEqual(result['offset'], 1)
        self.assertIsNone(result['next_offset'])
        self.assertEqual(result['filters']['conversation_id'], 'conv-1')
        self.assertEqual(result['filters']['turn_id'], 'turn-1')
        self.assertEqual(result['filters']['stage'], 'llm_call')
        self.assertEqual(result['filters']['status'], 'ok')
        self.assertEqual(result['filters']['ts_from'], '2026-03-27T11:00:00Z')
        self.assertEqual(result['filters']['ts_to'], '2026-03-27T13:00:00Z')
        self.assertEqual(result['items'][0]['event_id'], 'evt-2')
        self.assertEqual(result['items'][0]['payload']['response_chars'], 42)
        self.assertEqual(result['items'][1]['payload']['prompt_kind'], 'chat_system_augmented')

        joined_queries = '\n'.join(str(query) for query, _params in observed['queries'])
        self.assertIn('FROM observability.chat_log_events', joined_queries)
        self.assertIn('ORDER BY ts DESC, event_id DESC', joined_queries)
        self.assertIn('conversation_id = %s', joined_queries)
        self.assertIn('turn_id = %s', joined_queries)
        self.assertIn('stage = %s', joined_queries)
        self.assertIn('status = %s', joined_queries)
        self.assertIn('ts >= %s::timestamptz', joined_queries)
        self.assertIn('ts <= %s::timestamptz', joined_queries)

    def test_read_chat_log_events_rejects_invalid_status_filter(self) -> None:
        with self.assertRaisesRegex(ValueError, 'invalid chat log status filter'):
            log_store.read_chat_log_events(
                status='unknown',
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )

    def test_read_chat_log_events_rejects_invalid_ts_from(self) -> None:
        with self.assertRaisesRegex(ValueError, 'invalid ts_from timestamp'):
            log_store.read_chat_log_events(
                ts_from='not-a-date',
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )

    def test_read_chat_log_events_rejects_invalid_ts_to(self) -> None:
        with self.assertRaisesRegex(ValueError, 'invalid ts_to timestamp'):
            log_store.read_chat_log_events(
                ts_to='still-not-a-date',
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )

    def test_delete_chat_log_events_supports_conversation_scope(self) -> None:
        observed: dict[str, Any] = {'query': None, 'params': None, 'committed': False}

        class FakeCursor:
            def __init__(self) -> None:
                self.rowcount = 3

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

        result = log_store.delete_chat_log_events(
            conversation_id='conv-1',
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['scope'], 'conversation_logs')
        self.assertEqual(result['conversation_id'], 'conv-1')
        self.assertIsNone(result['turn_id'])
        self.assertEqual(result['deleted_count'], 3)
        self.assertIn('DELETE FROM observability.chat_log_events', str(observed['query']))
        self.assertIn('conversation_id = %s', str(observed['query']))
        self.assertNotIn('turn_id = %s', str(observed['query']))
        self.assertEqual(observed['params'], ('conv-1',))
        self.assertTrue(observed['committed'])

    def test_delete_chat_log_events_supports_turn_scope(self) -> None:
        observed: dict[str, Any] = {'query': None, 'params': None, 'committed': False}

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

        result = log_store.delete_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['scope'], 'turn_logs')
        self.assertEqual(result['conversation_id'], 'conv-1')
        self.assertEqual(result['turn_id'], 'turn-1')
        self.assertEqual(result['deleted_count'], 1)
        self.assertIn('conversation_id = %s', str(observed['query']))
        self.assertIn('turn_id = %s', str(observed['query']))
        self.assertEqual(observed['params'], ('conv-1', 'turn-1'))
        self.assertTrue(observed['committed'])

    def test_delete_chat_log_events_rejects_all_logs_scope(self) -> None:
        with self.assertRaisesRegex(ValueError, 'all_logs deletion is not supported in MVP'):
            log_store.delete_chat_log_events(
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )

    def test_delete_chat_log_events_rejects_turn_scope_without_conversation(self) -> None:
        with self.assertRaisesRegex(ValueError, 'turn_logs deletion requires conversation_id'):
            log_store.delete_chat_log_events(
                turn_id='turn-alone',
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
            )


if __name__ == '__main__':
    unittest.main()
