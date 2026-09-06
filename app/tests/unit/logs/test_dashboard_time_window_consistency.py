from __future__ import annotations

from datetime import datetime, timezone
import json
import unittest
from typing import Any, Sequence

from observability import dashboard_read_model


UTC = timezone.utc


class _NoopLogger:
    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def _fact_row(
    *,
    conversation_id: str,
    turn_id: str,
    latest_ts: datetime,
) -> tuple[Any, ...]:
    return (
        conversation_id,
        turn_id,
        latest_ts,
        latest_ts,
        'complete',
        100,
        1,
        f'{turn_id}-first',
        f'{turn_id}-latest',
        {'assistant_final_saved': True},
        {'main': {'present': True, 'status': 'ok'}},
        {'retrieved': 0, 'injected': 0},
        {'block_present': False},
        {'block_present': False},
        {'requested': False, 'injected': False},
        {'active_count': 0},
        {'used': False},
        {},
        {'total_ms': 10},
        {'error_count': 0, 'failed_count': 0, 'fallback_count': 0, 'problem_count': 0},
        {'turn_start': 1},
        {
            'status_schema': {
                'source_kind': 'v1',
                'schema_counts': {'agentic_v1': 1},
                'v1_event_count': 1,
                'legacy_event_count': 0,
            }
        },
        {'prompt_manifest_available': False},
        'dashboard_analytics_v1',
        latest_ts,
    )


def _status_row() -> tuple[Any, ...]:
    return (
        'dashboard_long_term_observability',
        'dashboard_analytics_v1',
        'ok',
        datetime(2026, 5, 1, tzinfo=UTC),
        datetime(2026, 9, 1, tzinfo=UTC),
        90,
        30,
        'day',
        4,
        False,
        False,
        'event-latest',
        datetime(2026, 8, 17, 12, 45, tzinfo=UTC),
        0,
        4,
        1,
        4,
        0,
        None,
        0,
        None,
        'retention_window_materialized',
        datetime(2026, 8, 17, 12, 50, tzinfo=UTC),
    )


def _as_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value.astimezone(UTC)
    text = str(value or '').strip()
    if not text or 'T' not in text:
        return None
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).astimezone(UTC)
    except ValueError:
        return None


class _FakeRelational:
    def __init__(
        self,
        facts: Sequence[tuple[Any, ...]],
        *,
        bucket_rows: Sequence[tuple[Any, ...]] = (),
    ) -> None:
        self.facts = list(facts)
        self.bucket_rows = list(bucket_rows)
        self.queries: list[tuple[str, tuple[Any, ...]]] = []

    def connect(self) -> '_FakeConnection':
        return _FakeConnection(self)

    def facts_in_params(self, params: tuple[Any, ...]) -> list[tuple[Any, ...]]:
        bounds = [parsed for value in params if (parsed := _as_datetime(value)) is not None]
        start = bounds[0] if bounds else datetime.min.replace(tzinfo=UTC)
        end = bounds[1] if len(bounds) > 1 else datetime.max.replace(tzinfo=UTC)
        ids = {str(value) for value in params if _as_datetime(value) is None and isinstance(value, str)}
        rows = [row for row in self.facts if start <= row[3] < end]
        conversation_ids = {value for value in ids if value.startswith('conv-')}
        turn_ids = {value for value in ids if value.startswith('turn-')}
        if conversation_ids:
            rows = [row for row in rows if row[0] in conversation_ids]
        if turn_ids:
            rows = [row for row in rows if row[1] in turn_ids]
        return rows


class _FakeConnection:
    def __init__(self, database: _FakeRelational) -> None:
        self.database = database

    def __enter__(self) -> '_FakeConnection':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def cursor(self) -> '_FakeCursor':
        return _FakeCursor(self.database)


class _FakeCursor:
    def __init__(self, database: _FakeRelational) -> None:
        self.database = database
        self.rows: list[tuple[Any, ...]] = []

    def __enter__(self) -> '_FakeCursor':
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        return False

    def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
        values = tuple(params or ())
        self.database.queries.append((query, values))
        if 'dashboard_materialization_status' in query:
            self.rows = [_status_row()]
            return
        if "'dashboard_summary_health' AS kind" in query:
            self.rows = [('dashboard_summary_health', 0, 0, 0, 0, 0, None)]
            return
        if 'FROM observability.dashboard_metric_buckets' in query:
            bounds = [_as_datetime(value) for value in values[1:3]]
            self.rows = [
                row for row in self.database.bucket_rows
                if row[0] == values[0] and bounds[0] <= row[1] < bounds[1]
            ]
            return
        if 'FROM observability.chat_log_events' in query:
            self.rows = []
            return
        if 'LEFT JOIN observability.dashboard_conversation_summaries' in query:
            self.rows = [
                (
                    row[0],
                    'Conversation temporelle',
                    'synthetic',
                    row[2],
                    row[3],
                    row[1],
                    row[4],
                    row[11],
                    row[14],
                    row[15],
                    row[16],
                    row[19],
                    row[21],
                )
                for row in self.database.facts_in_params(values)
            ]
            return
        if 'SELECT COUNT(*)::int' in query and 'dashboard_turn_facts' in query:
            self.rows = [(len(self.database.facts_in_params(values)),)]
            return
        if 'FROM observability.dashboard_turn_facts' in query:
            rows = self.database.facts_in_params(values)
            if 'ORDER BY latest_ts DESC' in query:
                rows = sorted(rows, key=lambda row: (row[3], row[1]), reverse=True)
            if 'LIMIT %s OFFSET %s' in query:
                limit, offset = int(values[-2]), int(values[-1])
                rows = rows[offset:offset + limit]
            elif 'LIMIT 2' in query:
                rows = rows[:2]
            self.rows = rows
            return
        self.rows = []

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def fetchall(self):
        return list(self.rows)


class DashboardTimeWindowConsistencyTests(unittest.TestCase):
    def assert_content_free(self, payload: dict[str, Any]) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        self.assertNotIn('RAW WINDOW CONTENT', encoded)
        self.assertFalse(payload['redaction']['raw_content_included'])

    def test_non_aligned_rolling_window_uses_the_same_exact_facts_as_conversations(self) -> None:
        start = datetime(2026, 8, 16, 12, 30, tzinfo=UTC)
        inside = datetime(2026, 8, 16, 12, 45, tzinfo=UTC)
        end = datetime(2026, 8, 17, 12, 30, tzinfo=UTC)
        database = _FakeRelational(
            [
                _fact_row(conversation_id='conv-window', turn_id='turn-before', latest_ts=start.replace(minute=29)),
                _fact_row(conversation_id='conv-window', turn_id='turn-start', latest_ts=start),
                _fact_row(conversation_id='conv-window', turn_id='turn-inside', latest_ts=inside),
                _fact_row(conversation_id='conv-window', turn_id='turn-end', latest_ts=end),
            ],
            bucket_rows=[
                (
                    'hour',
                    datetime(2026, 8, 16, 12, 0, tzinfo=UTC),
                    datetime(2026, 8, 16, 13, 0, tzinfo=UTC),
                    'pipeline',
                    3,
                    3,
                    {'classification_counts': {'complete': 3}},
                    'dashboard_analytics_v1',
                    end,
                )
            ],
        )

        overview = dashboard_read_model.read_dashboard_overview(
            {'window': '24h'},
            conn_factory=database.connect,
            logger_instance=_NoopLogger(),
            now=end,
        )
        conversations = dashboard_read_model.read_dashboard_conversations(
            {'window': '24h'},
            conn_factory=database.connect,
            logger_instance=_NoopLogger(),
            now=end,
        )

        self.assertEqual(overview['window']['start'], '2026-08-16T12:30:00+00:00')
        self.assertEqual(overview['window']['end'], '2026-08-17T12:30:00+00:00')
        self.assertEqual(overview['pulse']['turns_observed'], 2)
        self.assertEqual(conversations['items'][0]['turns_count'], 2)
        self.assertEqual(overview['window'].get('timestamp_field'), 'latest_ts')
        self.assertEqual(overview['window'].get('interval'), '[start,end)')
        pipeline_buckets = [
            bucket for bucket in overview['metric_buckets']
            if bucket['module_key'] == 'pipeline'
        ]
        self.assertEqual(pipeline_buckets[0]['bucket_start'], '2026-08-16T12:30:00+00:00')
        self.assertEqual(pipeline_buckets[0]['bucket_end'], '2026-08-16T13:00:00+00:00')
        self.assert_content_free(overview)
        self.assert_content_free(conversations)

    def test_custom_non_aligned_end_is_exact_and_shared_by_every_read_surface(self) -> None:
        start = datetime(2026, 8, 10, 12, 30, tzinfo=UTC)
        inside = datetime(2026, 8, 10, 13, 14, 59, tzinfo=UTC)
        end = datetime(2026, 8, 10, 13, 15, tzinfo=UTC)
        database = _FakeRelational(
            [
                _fact_row(conversation_id='conv-window', turn_id='turn-start', latest_ts=start),
                _fact_row(conversation_id='conv-window', turn_id='turn-inside', latest_ts=inside),
                _fact_row(conversation_id='conv-window', turn_id='turn-end', latest_ts=end),
            ]
        )
        params = {'ts_from': start.isoformat(), 'ts_to': end.isoformat()}
        calls = [
            dashboard_read_model.read_dashboard_overview(
                params, conn_factory=database.connect, logger_instance=_NoopLogger(), now=end
            ),
            dashboard_read_model.read_dashboard_conversations(
                params, conn_factory=database.connect, logger_instance=_NoopLogger(), now=end
            ),
            dashboard_read_model.read_dashboard_conversation_turns(
                'conv-window', params, conn_factory=database.connect, logger_instance=_NoopLogger(), now=end
            ),
            dashboard_read_model.read_dashboard_turn_inspection(
                'turn-start',
                {**params, 'conversation_id': 'conv-window'},
                conn_factory=database.connect,
                logger_instance=_NoopLogger(),
                now=end,
            ),
            dashboard_read_model.read_dashboard_turn_content(
                'turn-start',
                {**params, 'conversation_id': 'conv-window'},
                conn_factory=database.connect,
                logger_instance=_NoopLogger(),
                now=end,
            ),
        ]

        expected_window = calls[0]['window']
        self.assertEqual(expected_window['start'], '2026-08-10T12:30:00+00:00')
        self.assertEqual(expected_window['end'], '2026-08-10T13:15:00+00:00')
        self.assertTrue(all(payload['window'] == expected_window for payload in calls))
        self.assertEqual(calls[0]['pulse']['turns_observed'], 2)
        self.assertEqual(calls[1]['items'][0]['turns_count'], 2)
        self.assertEqual(calls[2]['total'], 2)
        self.assertEqual(
            {item['turn_id'] for item in calls[2]['items']},
            {'turn-start', 'turn-inside'},
        )
        pipeline_buckets = [
            bucket for bucket in calls[0]['metric_buckets']
            if bucket['module_key'] == 'pipeline'
        ]
        self.assertEqual(pipeline_buckets[-1]['bucket_end'], '2026-08-10T13:15:00+00:00')
        for payload in calls:
            self.assert_content_free(payload)

    def test_old_aligned_custom_window_uses_exact_facts(self) -> None:
        now = datetime(2026, 9, 6, 12, 0, tzinfo=UTC)
        start = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
        inside = datetime(2026, 7, 20, 12, 30, tzinfo=UTC)
        end = datetime(2026, 7, 20, 13, 0, tzinfo=UTC)
        database = _FakeRelational(
            [
                _fact_row(
                    conversation_id='conv-before',
                    turn_id='turn-before',
                    latest_ts=start.replace(hour=11, minute=59),
                ),
                _fact_row(conversation_id='conv-window', turn_id='turn-inside', latest_ts=inside),
                _fact_row(conversation_id='conv-end', turn_id='turn-end', latest_ts=end),
            ]
        )
        params = {'ts_from': start.isoformat(), 'ts_to': end.isoformat()}

        overview = dashboard_read_model.read_dashboard_overview(
            params,
            conn_factory=database.connect,
            logger_instance=_NoopLogger(),
            now=now,
        )
        conversations = dashboard_read_model.read_dashboard_conversations(
            params,
            conn_factory=database.connect,
            logger_instance=_NoopLogger(),
            now=now,
        )

        self.assertEqual(overview['pulse']['turns_observed'], 1)
        self.assertEqual(conversations['total'], 1)
        self.assertEqual(conversations['items'][0]['turns_count'], 1)
        self.assertEqual(conversations['items'][0]['conversation_id'], 'conv-window')
        self.assertTrue(any('dashboard_turn_facts' in query for query, _ in database.queries))
        self.assertFalse(any('dashboard_metric_buckets' in query for query, _ in database.queries))
        self.assert_content_free(overview)
        self.assert_content_free(conversations)

    def test_aligned_predefined_window_keeps_the_persisted_bucket_path(self) -> None:
        end = datetime(2026, 8, 10, 13, 0, tzinfo=UTC)
        start = datetime(2026, 8, 9, 13, 0, tzinfo=UTC)
        database = _FakeRelational(
            [],
            bucket_rows=[
                (
                    'hour',
                    start,
                    end,
                    'pipeline',
                    7,
                    7,
                    {'classification_counts': {'complete': 7}},
                    'dashboard_analytics_v1',
                    end,
                )
            ],
        )

        overview = dashboard_read_model.read_dashboard_overview(
            {'window': '24h'},
            conn_factory=database.connect,
            logger_instance=_NoopLogger(),
            now=end,
        )

        self.assertEqual(overview['pulse']['turns_observed'], 7)
        self.assertTrue(any('dashboard_metric_buckets' in query for query, _ in database.queries))
        self.assertFalse(any('dashboard_turn_facts' in query for query, _ in database.queries))


if __name__ == '__main__':
    unittest.main()
