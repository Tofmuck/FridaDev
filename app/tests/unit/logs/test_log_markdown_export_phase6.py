from __future__ import annotations

import json
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
                            'rejection_reason_code_counts': {'below_semantic_threshold': 2},
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
        self.assertIn('- payload_projection_schema: `admin_log_event_projection_v1`', markdown)
        self.assertIn('- content_free: `true`', markdown)
        self.assertIn('- raw_event_payloads_included: `false`', markdown)
        self.assertLess(markdown.find('turn_start'), markdown.find('arbiter'))
        self.assertIn('`prompt_kind`', markdown)
        self.assertIn('`rejected_candidates`', markdown)
        self.assertIn('`rejection_reason_code_counts`', markdown)
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

    def test_export_chat_logs_markdown_redacts_payload_sentinels(self) -> None:
        dangerous_values = (
            'RAW USER MESSAGE SENTINEL MARKDOWN 5A',
            'RAW PROMPT SENTINEL MARKDOWN 5A',
            'RAW PROVIDER PAYLOAD SENTINEL MARKDOWN 5A',
            'Authorization: Bearer RAW_TOKEN_SENTINEL_MARKDOWN_5A',
            'RAW EXCEPTION SENTINEL MARKDOWN 5A',
            'RAW FIELD SENTINEL MARKDOWN 5A',
            'BEGIN:VEVENT RAW DAV XML SENTINEL MARKDOWN 5A',
        )

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        'evt-markdown-redaction',
                        'conv-markdown-redaction',
                        'turn-markdown-redaction',
                        datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
                        'llm_call',
                        'error',
                        47,
                        {
                            'status_schema_version': 'agentic_v1',
                            'reason_code': 'provider_timeout',
                            'error_code': 'upstream_error',
                            'model': 'openai/gpt-5.4-mini',
                            'prompt_kind': 'chat_system_augmented',
                            'response_chars': 23,
                            'message': dangerous_values[0],
                            'prompt': dangerous_values[1],
                            'provider_payload': {'body': dangerous_values[2]},
                            'authorization': dangerous_values[3],
                            'error': dangerous_values[4],
                            'raw': dangerous_values[5],
                            'raw_content_included': True,
                            'caldav_xml': dangerous_values[6],
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
            conversation_id='conv-markdown-redaction',
            conn_factory=lambda: FakeConn(),
            generated_at=datetime(2026, 6, 21, 13, 0, tzinfo=timezone.utc),
        )

        encoded_result = json.dumps(result, ensure_ascii=False, sort_keys=True)
        markdown = result['markdown']
        for marker in dangerous_values:
            self.assertNotIn(marker, encoded_result)
        self.assertIn('`reason_code`: `provider_timeout`', markdown)
        self.assertIn('`error_code`: `upstream_error`', markdown)
        self.assertIn('`model`: `openai/gpt-5.4-mini`', markdown)
        self.assertIn('`prompt_kind`: `chat_system_augmented`', markdown)
        self.assertIn('`response_chars`: 23', markdown)
        self.assertIn('`raw_content_included`: false', markdown)
        self.assertNotIn('- `raw`:', markdown)

    def test_export_read_failure_logs_err_class_without_raw_exception(self) -> None:
        class FailingConn:
            def __enter__(self):
                raise RuntimeError('RAW MARKDOWN EXPORT EXCEPTION SENTINEL 5A')

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        with self.assertLogs('frida.log_markdown_export', level='ERROR') as captured:
            with self.assertRaisesRegex(RuntimeError, 'chat log markdown export read failed'):
                log_markdown_export.export_chat_logs_markdown(
                    conversation_id='conv-markdown-failure',
                    conn_factory=lambda: FailingConn(),
                )

        logs = '\n'.join(captured.output)
        self.assertIn('chat_log_markdown_export_read_failed', logs)
        self.assertIn('reason=chat_log_markdown_export_read_failed', logs)
        self.assertIn('err_class=RuntimeError', logs)
        self.assertNotIn('RAW MARKDOWN EXPORT EXCEPTION SENTINEL 5A', logs)


if __name__ == '__main__':
    unittest.main()
