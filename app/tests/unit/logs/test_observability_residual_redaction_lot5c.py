from __future__ import annotations

import json
import re
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

from observability import admin_log_projection
from observability import dashboard_analytics
from observability import dashboard_analytics_storage
from observability import dashboard_materialization_runtime
from observability import dashboard_read_model
from observability import log_store


RAW_EXCEPTION_SENTINEL = (
    'RAW_LOT5C_EXCEPTION https://provider.example/internal?token=secret '
    'Authorization: Bearer raw-secret'
)


class _CaptureLogger:
    def __init__(self) -> None:
        self.records: list[tuple[str, str, tuple[Any, ...]]] = []

    def error(self, message: str, *args: Any) -> None:
        self.records.append(('error', message, args))

    def warning(self, message: str, *args: Any) -> None:
        self.records.append(('warning', message, args))

    def info(self, message: str, *args: Any) -> None:
        self.records.append(('info', message, args))

    def rendered(self) -> list[str]:
        lines: list[str] = []
        for level, message, args in self.records:
            try:
                rendered = message % args
            except Exception:
                rendered = f'{message} {args!r}'
            lines.append(f'{level}:{rendered}')
        return lines


def _raise_raw_exception():
    raise RuntimeError(RAW_EXCEPTION_SENTINEL)


def _collect_keys(value: Any) -> set[str]:
    if isinstance(value, dict):
        keys: set[str] = set()
        for key, child in value.items():
            keys.add(str(key))
            keys.update(_collect_keys(child))
        return keys
    if isinstance(value, list):
        keys: set[str] = set()
        for child in value:
            keys.update(_collect_keys(child))
        return keys
    return set()


class ObservabilityResidualRedactionLot5CTests(unittest.TestCase):
    def assert_logger_redacted(self, logger: _CaptureLogger) -> None:
        self.assertTrue(logger.records)
        rendered = '\n'.join(logger.rendered())
        self.assertIn('err_class=RuntimeError', rendered)
        self.assertIn('reason=', rendered)
        self.assertNotIn('err=RAW_LOT5C_EXCEPTION', rendered)
        self.assertNotIn('provider.example', rendered)
        self.assertNotIn('raw-secret', rendered)
        self.assertNotIn('Bearer raw-secret', rendered)

    def test_observability_runtime_logs_use_err_class_not_raw_exception_text(self) -> None:
        forbidden = re.compile(r'err=%s|str\(exc\)|exc_info')
        offenders: list[str] = []
        for path in sorted((APP_DIR / 'observability').glob('*.py')):
            text = path.read_text(encoding='utf-8')
            if forbidden.search(text):
                offenders.append(path.name)
        self.assertEqual(offenders, [])

    def test_log_store_read_failure_logs_err_class_without_raw_exception(self) -> None:
        logger = _CaptureLogger()
        result = log_store.read_chat_log_events(
            limit=1,
            conn_factory=_raise_raw_exception,
            logger_instance=logger,
        )

        self.assertEqual(result['items'], [])
        self.assert_logger_redacted(logger)

    def test_dashboard_read_failure_logs_err_class_without_raw_exception(self) -> None:
        logger = _CaptureLogger()
        payload = dashboard_read_model.read_dashboard_overview(
            {'window': '24h'},
            conn_factory=_raise_raw_exception,
            logger_instance=logger,
            now=datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload['kind'], 'dashboard_overview')
        self.assertFalse(payload['redaction']['raw_content_included'])
        self.assert_logger_redacted(logger)

    def test_dashboard_storage_and_materialization_logs_err_class_without_raw_exception(self) -> None:
        logger = _CaptureLogger()
        dashboard_analytics_storage.init_dashboard_analytics_storage(
            conn_factory=_raise_raw_exception,
            logger_instance=logger,
        )
        analytics = dashboard_analytics_storage.materialize_dashboard_analytics_window(
            conn_factory=_raise_raw_exception,
            logger_instance=logger,
            now=datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
        )
        freshness = dashboard_materialization_runtime.ensure_recent_dashboard_analytics_fresh(
            conn_factory=_raise_raw_exception,
            logger_instance=logger,
            reason='lot5c_scan',
            now=datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(analytics['materialization_status']['status'], 'error')
        self.assertFalse(freshness['raw_content_included'])
        self.assert_logger_redacted(logger)

    def test_admin_and_dashboard_projections_redact_dangerous_payload_sentinels(self) -> None:
        dangerous_payload = {
            'status_schema_version': 'agentic_v1',
            'reason_code': 'provider_timeout',
            'model': 'openai/gpt-5.4-mini',
            'payload_json': {'body': 'RAW_LOT5C_PAYLOAD_JSON_MUST_NOT_LEAK'},
            'provider_payload': {'body': 'RAW_LOT5C_PROVIDER_PAYLOAD_MUST_NOT_LEAK'},
            'message': 'RAW_LOT5C_MESSAGE_MUST_NOT_LEAK',
            'prompt': 'RAW_LOT5C_PROMPT_MUST_NOT_LEAK',
            'url': 'https://provider.example/internal?token=raw-lot5c',
            'authorization': 'Bearer RAW_LOT5C_TOKEN_MUST_NOT_LEAK',
            'raw': 'RAW_LOT5C_RAW_FIELD_MUST_NOT_LEAK',
            'raw_content_included': True,
        }
        listing = admin_log_projection.project_event_listing(
            {
                'items': [
                    {
                        'event_id': 'evt-lot5c',
                        'conversation_id': 'conv-lot5c',
                        'turn_id': 'turn-lot5c',
                        'ts': '2026-06-21T12:00:00+00:00',
                        'stage': 'llm_call',
                        'status': 'failed',
                        'duration_ms': 12,
                        'payload': dangerous_payload,
                    }
                ]
            }
        )

        event = {
            'event_id': 'turn-lot5c:0001',
            'conversation_id': 'conv-lot5c',
            'turn_id': 'turn-lot5c',
            'ts': '2026-06-21T12:00:00+00:00',
            'stage': 'llm_call',
            'status': 'failed',
            'duration_ms': 12,
            'payload_json': dangerous_payload,
        }
        analytics = dashboard_analytics.build_dashboard_analytics(
            [event],
            now=datetime(2026, 6, 21, 13, 0, tzinfo=timezone.utc),
        )

        combined = json.dumps({'listing': listing, 'analytics': analytics}, ensure_ascii=False, sort_keys=True)
        for sentinel in (
            'RAW_LOT5C_PAYLOAD_JSON_MUST_NOT_LEAK',
            'RAW_LOT5C_PROVIDER_PAYLOAD_MUST_NOT_LEAK',
            'RAW_LOT5C_MESSAGE_MUST_NOT_LEAK',
            'RAW_LOT5C_PROMPT_MUST_NOT_LEAK',
            'RAW_LOT5C_TOKEN_MUST_NOT_LEAK',
            'RAW_LOT5C_RAW_FIELD_MUST_NOT_LEAK',
            'provider.example',
            'raw-lot5c',
        ):
            self.assertNotIn(sentinel, combined)

        keys = _collect_keys({'listing': listing, 'analytics': analytics})
        self.assertNotIn('raw', keys)
        self.assertNotIn('payload_json', keys)
        self.assertFalse(listing['redaction']['raw_event_payloads_included'])
        self.assertFalse(listing['items'][0]['payload']['raw_content_included'])
        self.assertEqual(analytics['turn_facts'][0]['errors']['failed_count'], 1)
        self.assertEqual(analytics['turn_facts'][0]['errors']['problem_count'], 1)


if __name__ == '__main__':
    unittest.main()
