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

from observability import log_store


class _NoopLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class LogStorePhase4Tests(unittest.TestCase):
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

    def test_no_opportunistic_reconstruction_after_delete_until_new_event(self) -> None:
        state: dict[str, list[dict[str, Any]]] = {
            'rows': [
                {
                    'event_id': 'evt-1',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'ts': datetime(2026, 3, 27, 10, 0, tzinfo=timezone.utc),
                    'stage': 'turn_start',
                    'status': 'ok',
                    'duration_ms': None,
                    'payload_json': {'marker': 'before-delete-1'},
                },
                {
                    'event_id': 'evt-2',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'ts': datetime(2026, 3, 27, 10, 1, tzinfo=timezone.utc),
                    'stage': 'turn_end',
                    'status': 'ok',
                    'duration_ms': 100,
                    'payload_json': {'marker': 'before-delete-2'},
                },
                {
                    'event_id': 'evt-3',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-2',
                    'ts': datetime(2026, 3, 27, 10, 2, tzinfo=timezone.utc),
                    'stage': 'turn_start',
                    'status': 'ok',
                    'duration_ms': None,
                    'payload_json': {'marker': 'other-turn'},
                },
            ]
        }

        class StatefulCursor:
            def __init__(self) -> None:
                self.rowcount = 0
                self._last_count = 0
                self._last_rows: list[tuple[Any, ...]] = []

            def __enter__(self) -> 'StatefulCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def _filter_rows(self, conversation_id: str | None, turn_id: str | None) -> list[dict[str, Any]]:
                rows = [row for row in state['rows'] if (conversation_id is None or row['conversation_id'] == conversation_id)]
                if turn_id is not None:
                    rows = [row for row in rows if row['turn_id'] == turn_id]
                return rows

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                compact = ' '.join(query.split()).lower()
                if compact.startswith('delete from observability.chat_log_events'):
                    conversation_id = str(params[0])
                    turn_id = str(params[1]) if 'turn_id = %s' in compact else None
                    before = len(state['rows'])
                    state['rows'] = [
                        row
                        for row in state['rows']
                        if not (
                            row['conversation_id'] == conversation_id
                            and (turn_id is None or row['turn_id'] == turn_id)
                        )
                    ]
                    self.rowcount = before - len(state['rows'])
                    return

                if 'select count(*)' in compact:
                    conversation_id = str(params[0]) if 'conversation_id = %s' in compact else None
                    turn_id = str(params[1]) if 'turn_id = %s' in compact else None
                    self._last_count = len(self._filter_rows(conversation_id, turn_id))
                    return

                if 'from observability.chat_log_events' in compact and 'order by ts desc, event_id desc' in compact:
                    idx = 0
                    conversation_id = None
                    turn_id = None
                    if 'conversation_id = %s' in compact:
                        conversation_id = str(params[idx])
                        idx += 1
                    if 'turn_id = %s' in compact:
                        turn_id = str(params[idx])
                        idx += 1
                    limit = int(params[idx])
                    offset = int(params[idx + 1])

                    filtered = self._filter_rows(conversation_id, turn_id)
                    filtered = sorted(filtered, key=lambda row: (row['ts'], row['event_id']), reverse=True)
                    page = filtered[offset : offset + limit]
                    self._last_rows = [
                        (
                            row['event_id'],
                            row['conversation_id'],
                            row['turn_id'],
                            row['ts'],
                            row['stage'],
                            row['status'],
                            row['duration_ms'],
                            row['payload_json'],
                        )
                        for row in page
                    ]
                    return

                raise AssertionError(f'Unsupported SQL in fake cursor: {query}')

            def fetchone(self) -> tuple[int]:
                return (self._last_count,)

            def fetchall(self) -> list[tuple[Any, ...]]:
                return self._last_rows

        class StatefulConn:
            def __enter__(self) -> 'StatefulConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> StatefulCursor:
                return StatefulCursor()

            def commit(self) -> None:
                return None

        conn_factory = lambda: StatefulConn()
        logger_instance = _NoopLogger()

        before = log_store.read_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            limit=20,
            offset=0,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(before['count'], 2)

        deleted = log_store.delete_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(deleted['scope'], 'turn_logs')
        self.assertEqual(deleted['deleted_count'], 2)

        after_once = log_store.read_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            limit=20,
            offset=0,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(after_once['count'], 0)
        self.assertEqual(after_once['items'], [])

        after_twice = log_store.read_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            limit=20,
            offset=0,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(after_twice['count'], 0)
        self.assertEqual(after_twice['items'], [])

        still_other_turn = log_store.read_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-2',
            limit=20,
            offset=0,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(still_other_turn['count'], 1)

        # Simulate a future runtime event: logs reappear only from new writes.
        state['rows'].append(
            {
                'event_id': 'evt-4',
                'conversation_id': 'conv-1',
                'turn_id': 'turn-1',
                'ts': datetime(2026, 3, 27, 10, 3, tzinfo=timezone.utc),
                'stage': 'turn_start',
                'status': 'ok',
                'duration_ms': None,
                'payload_json': {'marker': 'new-runtime-event'},
            }
        )
        after_new_event = log_store.read_chat_log_events(
            conversation_id='conv-1',
            turn_id='turn-1',
            limit=20,
            offset=0,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        self.assertEqual(after_new_event['count'], 1)
        self.assertEqual(after_new_event['items'][0]['event_id'], 'evt-4')


if __name__ == '__main__':
    unittest.main()
