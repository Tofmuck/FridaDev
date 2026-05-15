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

from observability import dashboard_analytics


class _NoopLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class DashboardAnalyticsLot2Tests(unittest.TestCase):
    def _event(
        self,
        stage: str,
        *,
        conversation_id: str = 'conv-dashboard',
        turn_id: str = 'turn-dashboard',
        ts: str = '2026-05-14T12:00:00+00:00',
        status: str = 'ok',
        duration_ms: int | None = None,
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            'event_id': event_id or f'{turn_id}:{stage}',
            'conversation_id': conversation_id,
            'turn_id': turn_id,
            'ts': ts,
            'stage': stage,
            'status': status,
            'duration_ms': duration_ms,
            'payload_json': dict(payload or {}),
        }

    def _complete_turn(
        self,
        *,
        conversation_id: str = 'conv-dashboard',
        turn_id: str = 'turn-dashboard',
        base_ts: str = '2026-05-14T12:00:00+00:00',
        web_search_enabled: bool = True,
    ) -> list[dict[str, Any]]:
        return [
            self._event(
                'turn_start',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={'web_search_enabled': web_search_enabled, 'user_msg_chars': 18},
                event_id=f'{turn_id}:0001:turn_start',
            ),
            self._event(
                'web_search',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={
                    'enabled': web_search_enabled,
                    'results_count': 2,
                    'context_injected': True,
                    'injected_chars': 77,
                    'read_state': 'page_read',
                    'query': 'RAW QUERY MUST NOT LEAK',
                    'context_block': 'RAW WEB CONTEXT MUST NOT LEAK',
                },
                event_id=f'{turn_id}:0002:web_search',
            ),
            self._event(
                'memory_chain_snapshot',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={
                    'retrieval': {'status': 'ok', 'retrieved_count': 4},
                    'basket': {'basket_candidates_count': 3, 'deduped_retrieved_count': 1},
                    'arbiter': {'kept_count': 2, 'rejected_count': 1},
                    'injection': {'injected_candidate_count': 2, 'context_hints_count': 1},
                    'retrieved_candidates': [{'content': 'RAW MEMORY MUST NOT LEAK'}],
                },
                event_id=f'{turn_id}:0003:memory_chain_snapshot',
            ),
            self._event(
                'primary_node',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={
                    'node_state_read_present': True,
                    'node_state_read_valid': True,
                    'node_state_write_attempted': True,
                    'node_state_write_succeeded': True,
                    'node_state_write_changed': False,
                    'node_state_schema_version': 'v1',
                    'fail_open': False,
                },
                event_id=f'{turn_id}:0004:primary_node',
            ),
            self._event(
                'prompt_prepared',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={
                    'messages_count': 4,
                    'identity_prompt_injection': {
                        'injected': True,
                        'identity_block_present': True,
                        'chars': 12,
                        'sha256_12': 'a' * 12,
                    },
                    'memory_prompt_injection': {
                        'injected': True,
                        'trace_memory_injected': True,
                        'trace_memory_injected_count': 2,
                    },
                    'memory_retrieval': {'status': 'ok', 'top_k_returned': 4},
                    'hermeneutic_prompt_injection': {
                        'present': True,
                        'chars': 23,
                        'sha256_12': 'b' * 12,
                    },
                    'prompt': 'RAW PROMPT MUST NOT LEAK',
                    'messages': ['RAW MESSAGE MUST NOT LEAK'],
                },
                event_id=f'{turn_id}:0005:prompt_prepared',
            ),
            self._event(
                'llm_call',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                duration_ms=120,
                payload={'provider_caller': 'llm', 'response_chars': 42, 'model': 'model-a'},
                event_id=f'{turn_id}:0006:llm_call',
            ),
            self._event(
                'persist_response',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={'persist_phase': 'assistant_final', 'conversation_saved': True, 'messages_written': 3},
                event_id=f'{turn_id}:0007:persist_response',
            ),
            self._event(
                'turn_end',
                conversation_id=conversation_id,
                turn_id=turn_id,
                ts=base_ts,
                payload={'final_status': 'ok'},
                event_id=f'{turn_id}:0008:turn_end',
            ),
        ]

    def _collect_keys(self, value: Any) -> set[str]:
        if isinstance(value, dict):
            keys = set(value.keys())
            for child in value.values():
                keys.update(self._collect_keys(child))
            return keys
        if isinstance(value, list):
            keys: set[str] = set()
            for child in value:
                keys.update(self._collect_keys(child))
            return keys
        return set()

    def test_build_dashboard_analytics_is_idempotent_and_content_free(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        events = [
            *self._complete_turn(),
            *self._complete_turn(
                conversation_id='conv-old',
                turn_id='turn-old',
                base_ts='2026-03-10T09:00:00+00:00',
                web_search_enabled=False,
            ),
        ]

        first = dashboard_analytics.build_dashboard_analytics(events, now=now)
        second = dashboard_analytics.build_dashboard_analytics(events, now=now)

        self.assertEqual(first, second)
        self.assertEqual(first['window']['retention_days'], 90)
        self.assertEqual(first['window']['recent_granularity_days'], 30)
        self.assertEqual(len(first['turn_facts']), 2)
        self.assertEqual(len(first['conversation_summaries']), 2)
        self.assertEqual(first['materialization_status']['source_events_truncated'], False)
        self.assertEqual(first['materialization_status']['event_limit_dependency'], False)
        self.assertEqual(first['materialization_status']['turns_materialized_count'], 2)

        recent_hour_buckets = [
            bucket for bucket in first['metric_buckets']
            if bucket['granularity'] == 'hour' and bucket['bucket_start'].startswith('2026-05-14T12:')
        ]
        old_hour_buckets = [
            bucket for bucket in first['metric_buckets']
            if bucket['granularity'] == 'hour' and bucket['bucket_start'].startswith('2026-03-10T09:')
        ]
        old_day_buckets = [
            bucket for bucket in first['metric_buckets']
            if bucket['granularity'] == 'day' and bucket['bucket_start'].startswith('2026-03-10T00:')
        ]
        self.assertTrue(recent_hour_buckets)
        self.assertFalse(old_hour_buckets)
        self.assertTrue(old_day_buckets)

        serialized = json.dumps(first, sort_keys=True)
        for forbidden_value in (
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
        ):
            self.assertNotIn(forbidden_value, serialized)
        for forbidden_key in ('payload', 'payload_json', 'prompt', 'messages', 'content', 'query', 'context_block'):
            self.assertNotIn(forbidden_key, self._collect_keys(first))

    def test_materialization_status_tracks_lag_without_raw_error_message(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        error = RuntimeError('RAW SECRET DSN MUST NOT LEAK')

        status = dashboard_analytics.build_dashboard_materialization_status(
            events=[],
            turn_facts=[],
            conversation_summaries=[],
            metric_buckets=[],
            now=now,
            error=error,
        )

        self.assertEqual(status['status'], 'error')
        self.assertEqual(status['last_error_code'], 'RuntimeError')
        self.assertEqual(status['last_error_chars'], len(str(error)))
        self.assertEqual(len(status['last_error_sha256_12']), 12)
        self.assertFalse(status['source_events_truncated'])
        self.assertFalse(status['event_limit_dependency'])
        self.assertNotIn('RAW SECRET DSN MUST NOT LEAK', json.dumps(status, sort_keys=True))

        analytics = dashboard_analytics.build_dashboard_analytics(
            self._complete_turn(base_ts='2026-05-15T11:59:30+00:00'),
            now=now,
        )
        self.assertEqual(analytics['materialization_status']['lag_seconds'], 30)

    def test_materialize_dashboard_analytics_window_reads_without_event_limit_and_upserts(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        observed: dict[str, Any] = {'queries': [], 'params': [], 'commits': 0}
        rows = [
            (
                event['event_id'],
                event['conversation_id'],
                event['turn_id'],
                datetime.fromisoformat(str(event['ts'])),
                event['stage'],
                event['status'],
                event['duration_ms'],
                event['payload_json'],
            )
            for event in self._complete_turn()
        ]

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
                observed['queries'].append(query)
                observed['params'].append(params)

            def fetchall(self) -> list[tuple[Any, ...]]:
                return rows

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed['commits'] += 1

        analytics = dashboard_analytics.materialize_dashboard_analytics_window(
            ts_from='2026-05-14T00:00:00Z',
            ts_to='2026-05-15T00:00:00Z',
            now=now,
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(analytics['materialization_status']['source_events_count'], len(rows))
        self.assertTrue(analytics['persist']['ok'])
        joined = '\n'.join(observed['queries'])
        read_query = observed['queries'][0]
        self.assertIn('FROM observability.chat_log_events', read_query)
        self.assertNotIn('LIMIT', read_query.upper())
        self.assertIn('ON CONFLICT (conversation_id, turn_id) DO UPDATE', joined)
        self.assertIn('ON CONFLICT (granularity, bucket_start, module_key) DO UPDATE', joined)
        self.assertIn('ON CONFLICT (materializer_key) DO UPDATE', joined)
        self.assertEqual(observed['commits'], 1)
        self.assertEqual(
            observed['params'][0],
            ('2026-05-14T00:00:00+00:00', '2026-05-15T00:00:00+00:00'),
        )

    def test_execute_dashboard_analytics_schema_creates_persistent_tables(self) -> None:
        observed: list[str] = []

        class FakeCursor:
            def execute(self, query: str, _params: tuple[Any, ...] | None = None) -> None:
                observed.append(query)

        dashboard_analytics.execute_dashboard_analytics_schema(FakeCursor())
        joined = '\n'.join(observed)

        self.assertIn('observability.dashboard_turn_facts', joined)
        self.assertIn('observability.dashboard_conversation_summaries', joined)
        self.assertIn('observability.dashboard_metric_buckets', joined)
        self.assertIn('observability.dashboard_materialization_status', joined)
        self.assertIn('CHECK (raw_event_payloads_included = false)', joined)
        self.assertIn('CHECK (source_events_truncated = false)', joined)
        self.assertIn('CHECK (event_limit_dependency = false)', joined)


if __name__ == '__main__':
    unittest.main()
