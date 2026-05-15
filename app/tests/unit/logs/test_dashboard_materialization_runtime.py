from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import dashboard_materialization_runtime as runtime


class _NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        pass

    def warning(self, *_args: object, **_kwargs: object) -> None:
        pass


class _FreshnessCursor:
    def __init__(self, *, latest_event_ts: datetime | None, window_end: datetime | None) -> None:
        self.latest_event_ts = latest_event_ts
        self.window_end = window_end
        self._row: tuple[Any, ...] | None = None
        self.queries: list[str] = []

    def __enter__(self) -> '_FreshnessCursor':
        return self

    def __exit__(self, *_exc: object) -> None:
        pass

    def execute(self, query: str, _params: tuple[Any, ...] | None = None) -> None:
        self.queries.append(' '.join(query.split()))
        if 'MAX(ts)' in query:
            self._row = (self.latest_event_ts,)
            return
        if 'dashboard_materialization_status' in query:
            self._row = (self.window_end, self.window_end)
            return
        self._row = None

    def fetchone(self) -> tuple[Any, ...] | None:
        return self._row


class _FreshnessConn:
    def __init__(self, cursor: _FreshnessCursor) -> None:
        self.cursor_obj = cursor

    def __enter__(self) -> '_FreshnessConn':
        return self

    def __exit__(self, *_exc: object) -> None:
        pass

    def cursor(self) -> _FreshnessCursor:
        return self.cursor_obj


class DashboardMaterializationRuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime._REFRESH_RUNNING = False
        runtime._LAST_REFRESH_STARTED_MONOTONIC = 0.0

    def _conn_factory(
        self,
        *,
        latest_event_ts: datetime | None,
        window_end: datetime | None,
    ):
        cursor = _FreshnessCursor(latest_event_ts=latest_event_ts, window_end=window_end)

        def factory() -> _FreshnessConn:
            return _FreshnessConn(cursor)

        return factory

    def test_ensure_recent_materializes_when_events_are_after_window_end(self) -> None:
        now = datetime(2026, 5, 15, 12, 5, tzinfo=timezone.utc)
        calls: list[dict[str, Any]] = []

        def fake_materialize(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs)
            return {
                'materialization_status': {
                    'status': 'ok',
                    'turns_materialized_count': 1,
                    'source_events_count': 6,
                    'lag_seconds': 0,
                }
            }

        with patch.object(
            runtime.dashboard_analytics,
            'materialize_dashboard_analytics_window',
            side_effect=fake_materialize,
        ):
            result = runtime.ensure_recent_dashboard_analytics_fresh(
                conn_factory=self._conn_factory(
                    latest_event_ts=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
                    window_end=datetime(2026, 5, 15, 11, 0, tzinfo=timezone.utc),
                ),
                logger_instance=_NoopLogger(),
                reason='test_read',
                now=now,
                stale_grace_seconds=30,
            )

        self.assertTrue(result['refreshed'])
        self.assertEqual(result['reason_code'], 'materialization_stale')
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0]['ts_from'], '2026-05-14T12:05:00+00:00')
        self.assertEqual(calls[0]['ts_to'], '2026-05-15T12:05:00+00:00')
        self.assertNotIn('event_limit', calls[0])
        self.assertFalse(result['raw_content_included'])

    def test_ensure_recent_does_not_materialize_when_status_is_fresh_enough(self) -> None:
        now = datetime(2026, 5, 15, 12, 5, tzinfo=timezone.utc)

        with patch.object(
            runtime.dashboard_analytics,
            'materialize_dashboard_analytics_window',
        ) as materialize:
            result = runtime.ensure_recent_dashboard_analytics_fresh(
                conn_factory=self._conn_factory(
                    latest_event_ts=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
                    window_end=datetime(2026, 5, 15, 12, 4, 45, tzinfo=timezone.utc),
                ),
                logger_instance=_NoopLogger(),
                reason='test_read',
                now=now,
                stale_grace_seconds=30,
            )

        self.assertFalse(result['refreshed'])
        self.assertEqual(result['reason_code'], 'fresh_enough')
        materialize.assert_not_called()

    def test_schedule_recent_materialization_is_bounded_and_content_free(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        calls: list[dict[str, Any]] = []

        def fake_materialize(**kwargs: Any) -> dict[str, Any]:
            calls.append(kwargs)
            return {
                'materialization_status': {
                    'status': 'ok',
                    'turns_materialized_count': 2,
                    'source_events_count': 12,
                    'lag_seconds': 0,
                }
            }

        with patch.object(
            runtime.dashboard_analytics,
            'materialize_dashboard_analytics_window',
            side_effect=fake_materialize,
        ):
            result = runtime.schedule_recent_dashboard_analytics_materialization(
                conn_factory=lambda: None,
                logger_instance=_NoopLogger(),
                reason='chat_turn_end',
                run_async=False,
                now=now,
                min_refresh_interval_seconds=0,
            )

        self.assertTrue(result['scheduled'])
        self.assertFalse(result['async'])
        self.assertEqual(result['result']['turns_materialized_count'], 2)
        self.assertEqual(calls[0]['ts_from'], '2026-05-14T12:00:00+00:00')
        self.assertEqual(calls[0]['ts_to'], '2026-05-15T12:00:00+00:00')
        self.assertNotIn('event_limit', calls[0])
        self.assertNotIn('events', result)
        self.assertFalse(result['raw_content_included'])


if __name__ == '__main__':
    unittest.main()
