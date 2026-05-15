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

from observability import dashboard_read_model


class _NoopLogger:
    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class DashboardReadModelLot4Tests(unittest.TestCase):
    def _assert_content_free(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'secret-token',
            'postgres://',
        ):
            self.assertNotIn(forbidden, encoded)

    def test_resolve_dashboard_window_supports_expected_windows(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': '24h'}, now=now)['granularity'], 'hour')
        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': '7d'}, now=now)['key'], '7d')
        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': '30d'}, now=now)['key'], '30d')
        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': '90d'}, now=now)['granularity'], 'day')
        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': 'today'}, now=now)['label_fr'], 'Aujourd hui')
        self.assertEqual(dashboard_read_model.resolve_dashboard_window({'window': 'yesterday'}, now=now)['label_fr'], 'Hier')
        custom = dashboard_read_model.resolve_dashboard_window(
            {
                'ts_from': '2026-05-14T00:00:00Z',
                'ts_to': '2026-05-15T00:00:00Z',
            },
            now=now,
        )
        self.assertEqual(custom['key'], 'custom')

    def test_resolve_dashboard_window_rejects_invalid_or_too_long_windows(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)

        with self.assertRaisesRegex(ValueError, 'invalid dashboard window'):
            dashboard_read_model.resolve_dashboard_window({'window': 'broken'}, now=now)
        with self.assertRaisesRegex(ValueError, 'ts_from and ts_to are required'):
            dashboard_read_model.resolve_dashboard_window({'window': 'custom'}, now=now)
        with self.assertRaisesRegex(ValueError, 'dashboard window exceeds 90 days retention'):
            dashboard_read_model.resolve_dashboard_window(
                {
                    'ts_from': '2026-01-01T00:00:00Z',
                    'ts_to': '2026-05-15T00:00:00Z',
                },
                now=now,
            )

    def test_overview_degraded_state_is_content_free(self) -> None:
        def failing_conn():
            raise RuntimeError('db unavailable')

        payload = dashboard_read_model.read_dashboard_overview(
            {'window': '24h'},
            conn_factory=failing_conn,
            logger_instance=_NoopLogger(),
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(payload['kind'], 'dashboard_overview')
        self.assertEqual(payload['source']['status'], 'degraded')
        self.assertEqual(payload['source']['degraded_reason'], 'RuntimeError')
        self.assertFalse(payload['source']['limits']['event_limit_dependency'])
        self.assertFalse(payload['redaction']['raw_content_included'])
        self._assert_content_free(payload)

    def test_overview_does_not_sum_non_additive_bucket_metrics(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        status_row = (
            'dashboard_long_term_observability',
            'dashboard_analytics_v1',
            'ok',
            datetime(2026, 5, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc),
            90,
            30,
            'day',
            4,
            False,
            False,
            'evt-latest',
            datetime(2026, 5, 15, 11, 59, tzinfo=timezone.utc),
            60,
            2,
            1,
            4,
            0,
            None,
            0,
            None,
            'custom_window_materialized',
            datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        bucket_rows = [
            (
                'hour',
                datetime(2026, 5, 15, 10, 0, tzinfo=timezone.utc),
                datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc),
                'providers',
                1,
                2,
                {'main_duration_ms_total': 100, 'main_duration_ms_count': 1, 'main_duration_ms_p50': 100},
                'dashboard_analytics_v1',
                datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc),
            ),
            (
                'hour',
                datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc),
                datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
                'providers',
                1,
                2,
                {'main_duration_ms_total': 300, 'main_duration_ms_count': 1, 'main_duration_ms_p50': 300},
                'dashboard_analytics_v1',
                datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
            ),
        ]

        class FakeCursor:
            def __init__(self) -> None:
                self.rows: list[tuple[Any, ...]] = []

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, _params: tuple[Any, ...] | None = None) -> None:
                if 'dashboard_materialization_status' in query:
                    self.rows = [status_row]
                else:
                    self.rows = bucket_rows

            def fetchone(self):
                return self.rows[0] if self.rows else None

            def fetchall(self):
                return self.rows

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        payload = dashboard_read_model.read_dashboard_overview(
            {'window': '24h'},
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
            now=now,
        )

        provider_metrics = payload['module_totals']['providers']['metrics']
        self.assertEqual(provider_metrics['main_duration_ms_total'], 400)
        self.assertEqual(provider_metrics['main_duration_ms_count'], 2)
        self.assertNotIn('main_duration_ms_p50', provider_metrics)
        self._assert_content_free(payload)

    def test_turn_inspection_is_translated_and_content_free(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        status_row = (
            'dashboard_long_term_observability',
            'dashboard_analytics_v1',
            'ok',
            datetime(2026, 5, 14, 0, 0, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 0, 0, tzinfo=timezone.utc),
            90,
            30,
            'day',
            8,
            False,
            False,
            'evt-latest',
            datetime(2026, 5, 15, 11, 59, tzinfo=timezone.utc),
            60,
            1,
            1,
            9,
            0,
            None,
            0,
            None,
            'custom_window_materialized',
            datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        fact_row = (
            'conv-1',
            'turn-1',
            datetime(2026, 5, 15, 11, 59, tzinfo=timezone.utc),
            datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
            'complete',
            100,
            8,
            'evt-first',
            'evt-latest',
            {'status': 'saved', 'assistant_final_saved': True},
            {'main': {'present': True, 'status': 'ok'}},
            {'retrieved': 4, 'kept': 2, 'injected': 1},
            {'block_present': True, 'status': 'ok'},
            {'block_present': True, 'status': 'ok'},
            {'requested': False, 'status': 'not_applicable'},
            {'read_present': True, 'write_attempted': True},
            {'main_duration_ms': 120},
            {'error_count': 0, 'fallback_count': 0, 'reason_code_counts': {}},
            {'turn_start': 1},
            {'events_truncated': False},
            {'content_comprehension_status': 'compact_only'},
            'dashboard_analytics_v1',
            datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )

        class FakeCursor:
            def __init__(self) -> None:
                self.rows: list[tuple[Any, ...]] = []

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, _params: tuple[Any, ...] | None = None) -> None:
                if 'dashboard_materialization_status' in query:
                    self.rows = [status_row]
                else:
                    self.rows = [fact_row]

            def fetchone(self):
                return self.rows[0] if self.rows else None

            def fetchall(self):
                return self.rows

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        payload = dashboard_read_model.read_dashboard_turn_inspection(
            'turn-1',
            {'conversation_id': 'conv-1', 'window': '24h'},
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
            now=now,
        )

        self.assertEqual(payload['kind'], 'dashboard_turn_inspection')
        self.assertEqual(payload['conversation_id'], 'conv-1')
        summaries = [module['summary_fr'] for module in payload['modules']]
        self.assertIn('La memoire a trouve 4 elements, en a garde 2, et en a injecte 1.', summaries)
        self.assertFalse(payload['redaction']['raw_content_included'])
        self.assertFalse(payload['source']['limits']['event_limit_dependency'])
        self._assert_content_free(payload)


if __name__ == '__main__':
    unittest.main()
