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

from observability import log_markdown_export


class LogMarkdownExportPhase6Tests(unittest.TestCase):
    def test_export_chat_logs_markdown_conversation_scope_has_stable_compact_format(self) -> None:
        observed: dict[str, Any] = {'query': None, 'params': None}
        long_value = 'x' * 400

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                observed['query'] = query
                observed['params'] = params

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        'evt-1',
                        'conv-1',
                        'turn-1',
                        datetime(2026, 3, 28, 9, 0, tzinfo=timezone.utc),
                        'turn_start',
                        'ok',
                        None,
                        {'prompt_kind': 'chat_system_augmented'},
                    ),
                    (
                        'evt-2',
                        'conv-1',
                        'turn-1',
                        datetime(2026, 3, 28, 9, 1, tzinfo=timezone.utc),
                        'arbiter',
                        'ok',
                        18,
                        {
                            'rejected_candidates': 2,
                            'rejection_reason_counts': {'below_threshold': 2},
                            'long_text': long_value,
                        },
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_markdown_export.export_chat_logs_markdown(
            conversation_id='conv-1',
            conn_factory=lambda: FakeConn(),
            generated_at=datetime(2026, 3, 28, 10, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(result['scope'], 'conversation')
        self.assertEqual(result['conversation_id'], 'conv-1')
        self.assertIsNone(result['turn_id'])
        self.assertEqual(result['events_count'], 2)

        markdown = result['markdown']
        self.assertIn('# Frida Chat Logs Export', markdown)
        self.assertIn('- scope: `conversation`', markdown)
        self.assertIn('- conversation_id: `conv-1`', markdown)
        self.assertIn('- events_count: `2`', markdown)
        self.assertLess(markdown.find('turn_start'), markdown.find('arbiter'))
        self.assertIn('`prompt_kind`', markdown)
        self.assertIn('`rejected_candidates`', markdown)
        self.assertIn('`rejection_reason_counts`', markdown)
        self.assertNotIn('x' * 200, markdown)

        self.assertIn('WHERE conversation_id = %s', str(observed['query']))
        self.assertNotIn('turn_id = %s', str(observed['query']))
        self.assertEqual(observed['params'], ('conv-1',))

    def test_export_chat_logs_markdown_turn_scope_requires_conversation_and_filters_turn(self) -> None:
        observed: dict[str, Any] = {'params': None}

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, params: tuple[Any, ...]) -> None:
                observed['params'] = params

            def fetchall(self) -> list[tuple[Any, ...]]:
                return []

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_markdown_export.export_chat_logs_markdown(
            conversation_id='conv-2',
            turn_id='turn-9',
            conn_factory=lambda: FakeConn(),
            generated_at=datetime(2026, 3, 28, 10, 30, tzinfo=timezone.utc),
        )
        self.assertEqual(result['scope'], 'turn')
        self.assertEqual(result['conversation_id'], 'conv-2')
        self.assertEqual(result['turn_id'], 'turn-9')
        self.assertEqual(result['events_count'], 0)
        self.assertIn('_No log events found for this scope._', result['markdown'])
        self.assertEqual(observed['params'], ('conv-2', 'turn-9'))

        with self.assertRaisesRegex(ValueError, 'conversation_id is required for markdown export'):
            log_markdown_export.export_chat_logs_markdown(
                conversation_id='',
                turn_id='turn-alone',
                conn_factory=lambda: FakeConn(),
            )


if __name__ == '__main__':
    unittest.main()
