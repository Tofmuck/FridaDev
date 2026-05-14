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

from observability import log_store


class _NoopLogger:
    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class LogStorePhase3Tests(unittest.TestCase):
    def _event(
        self,
        stage: str,
        *,
        status: str = 'ok',
        payload: dict[str, Any] | None = None,
        event_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            'event_id': event_id or f'evt-{stage}',
            'conversation_id': 'conv-checklist',
            'turn_id': 'turn-checklist',
            'ts': '2026-05-14T12:00:00+00:00',
            'stage': stage,
            'status': status,
            'duration_ms': None,
            'payload': dict(payload or {}),
        }

    def _complete_turn_events(self, *, web_search_enabled: bool = False) -> list[dict[str, Any]]:
        return [
            self._event('turn_start', payload={'web_search_enabled': web_search_enabled, 'user_msg_chars': 7}),
            self._event(
                'stimmung_prompt_prepared',
                payload={'provider_caller': 'stimmung_agent', 'secondary_provider_payload': True},
            ),
            self._event('stimmung_agent', payload={'provider_caller': 'stimmung_agent'}),
            self._event('hermeneutic_node_insertion', payload={'insertion_point_reached': True}),
            self._event(
                'primary_node',
                payload={
                    'fail_open': False,
                    'node_state_read_present': True,
                    'node_state_read_valid': True,
                    'node_state_read_reason_code': 'ok',
                    'node_state_write_attempted': True,
                    'node_state_write_succeeded': True,
                    'node_state_write_changed': False,
                    'node_state_write_reason_code': 'unchanged',
                    'node_state_schema_version': 'v1',
                },
            ),
            self._event(
                'validation_prompt_prepared',
                payload={'provider_caller': 'validation_agent', 'secondary_provider_payload': True},
            ),
            self._event('validation_agent', payload={'provider_caller': 'validation_agent'}),
            self._event(
                'prompt_prepared',
                payload={
                    'prompt_kind': 'chat_system_augmented',
                    'messages_count': 4,
                    'identity_prompt_injection': {
                        'injected': True,
                        'identity_block_present': True,
                        'chars': 12,
                        'sha256_12': 'a' * 12,
                    },
                    'memory_prompt_injection': {
                        'injected': False,
                        'injection_class': 'none',
                        'trace_memory_injected': False,
                        'summary_context_injected': False,
                        'context_hints_injected': False,
                    },
                    'memory_retrieval': {
                        'status': 'ok',
                        'reason_code': 'no_data',
                        'top_k_returned': 0,
                    },
                    'hermeneutic_prompt_injection': {
                        'present': True,
                        'chars': 23,
                        'sha256_12': 'b' * 12,
                    },
                    'prompt': 'RAW PROMPT MUST NOT LEAK',
                    'messages': ['RAW MESSAGE MUST NOT LEAK'],
                },
            ),
            self._event('llm_call', payload={'provider_caller': 'llm', 'response_chars': 17}),
            self._event(
                'persist_response',
                payload={'persist_phase': 'assistant_final', 'conversation_saved': True, 'messages_written': 3},
            ),
            self._event('turn_end', payload={'final_status': 'ok'}),
        ]

    def _find_item(self, checklist: dict[str, Any], key: str) -> dict[str, Any]:
        return next(item for item in checklist['items'] if item['key'] == key)

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

    def test_build_llm_call_provider_metrics_segments_main_secondary_and_unknown(self) -> None:
        metrics = log_store.build_llm_call_provider_metrics(
            [
                {
                    'provider_caller': 'llm',
                    'status': 'ok',
                    'calls_count': 2,
                    'duration_ms_total': 120,
                    'duration_ms_count': 2,
                    'response_chars_total': 42,
                    'latest_ts': datetime(2026, 5, 14, 10, 0, tzinfo=timezone.utc),
                },
                {
                    'provider_caller': 'stimmung_agent',
                    'status': 'ok',
                    'calls_count': 1,
                    'duration_ms_total': 40,
                    'duration_ms_count': 1,
                    'response_chars_total': 6,
                    'latest_ts': datetime(2026, 5, 14, 10, 1, tzinfo=timezone.utc),
                },
                {
                    'provider_caller': 'validation_agent',
                    'status': 'error',
                    'calls_count': 1,
                    'duration_ms_total': 20,
                    'duration_ms_count': 1,
                    'response_chars_total': 0,
                    'latest_ts': datetime(2026, 5, 14, 10, 2, tzinfo=timezone.utc),
                },
                {
                    'provider_caller': 'web_reformulation',
                    'status': 'ok',
                    'calls_count': 1,
                    'duration_ms_total': 10,
                    'duration_ms_count': 1,
                    'response_chars_total': 12,
                    'latest_ts': datetime(2026, 5, 14, 10, 3, tzinfo=timezone.utc),
                },
                {
                    'provider_caller': '',
                    'status': 'ok',
                    'calls_count': 1,
                    'duration_ms_total': 5,
                    'duration_ms_count': 1,
                    'response_chars_total': 0,
                    'latest_ts': datetime(2026, 5, 14, 10, 4, tzinfo=timezone.utc),
                },
                {
                    'provider_caller': 'legacy_sidecar',
                    'status': 'ok',
                    'calls_count': 1,
                    'duration_ms_total': 7,
                    'duration_ms_count': 1,
                    'response_chars_total': 0,
                    'latest_ts': datetime(2026, 5, 14, 10, 5, tzinfo=timezone.utc),
                },
            ]
        )

        self.assertEqual(metrics['main_provider_caller'], 'llm')
        self.assertEqual(
            metrics['secondary_provider_callers'],
            ['stimmung_agent', 'validation_agent', 'web_reformulation'],
        )
        self.assertEqual(metrics['main_llm_call_count'], 2)
        self.assertEqual(metrics['secondary_llm_call_count'], 3)
        self.assertEqual(metrics['unknown_llm_call_count'], 2)
        self.assertEqual(metrics['total_llm_call_count'], 7)

        by_caller = metrics['by_provider_caller']
        self.assertEqual(by_caller['llm']['total_count'], 2)
        self.assertEqual(by_caller['llm']['ok_count'], 2)
        self.assertEqual(by_caller['stimmung_agent']['total_count'], 1)
        self.assertEqual(by_caller['validation_agent']['error_count'], 1)
        self.assertEqual(by_caller['web_reformulation']['response_chars_total'], 12)
        self.assertEqual(by_caller['unknown']['total_count'], 2)
        self.assertEqual(by_caller['unknown']['ok_count'], 2)
        self.assertNotIn('legacy_sidecar', by_caller)
        serialized = json.dumps(metrics, sort_keys=True)
        for forbidden in ('prompt', 'messages', 'content', 'response_text'):
            self.assertNotIn(forbidden, serialized)

    def test_read_llm_call_provider_metrics_queries_llm_calls_only(self) -> None:
        observed: dict[str, Any] = {'queries': []}

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                observed['queries'].append((query, params))

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    ('llm', 'ok', 3, 90, 3, 120, datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)),
                    ('validation_agent', 'ok', 1, 30, 1, 8, datetime(2026, 5, 14, 12, 1, tzinfo=timezone.utc)),
                    ('', 'ok', 1, 10, 1, 0, datetime(2026, 5, 14, 12, 2, tzinfo=timezone.utc)),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_llm_call_provider_metrics(
            ts_from='2026-05-14T00:00:00Z',
            ts_to='2026-05-15T00:00:00Z',
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['main_llm_call_count'], 3)
        self.assertEqual(result['secondary_llm_call_count'], 1)
        self.assertEqual(result['unknown_llm_call_count'], 1)
        self.assertEqual(result['by_provider_caller']['llm']['avg_duration_ms'], 30.0)
        self.assertEqual(result['filters']['ts_from'], '2026-05-14T00:00:00Z')
        self.assertEqual(result['filters']['ts_to'], '2026-05-15T00:00:00Z')

        joined_queries = '\n'.join(str(query) for query, _params in observed['queries'])
        self.assertIn("stage = 'llm_call'", joined_queries)
        self.assertIn('payload_json->>\'provider_caller\'', joined_queries)
        self.assertIn('GROUP BY provider_caller, status', joined_queries)
        self.assertEqual(
            observed['queries'][0][1],
            ('2026-05-14T00:00:00Z', '2026-05-15T00:00:00Z'),
        )

    def test_build_full_turn_metrics_snapshot_covers_dashboard_signals_without_raw_payloads(self) -> None:
        events = self._complete_turn_events(web_search_enabled=True)
        prompt_event = next(event for event in events if event['stage'] == 'prompt_prepared')
        prompt_event['payload']['memory_prompt_injection'].update(
            {
                'injected': True,
                'injection_class': 'mixed',
                'trace_memory_injected': True,
                'trace_memory_injected_count': 2,
                'summary_context_injected': True,
                'summary_context_injected_count': 1,
                'context_hints_injected': True,
                'context_hints_injected_count': 3,
                'injected_candidate_ids': ['cand-a', 'cand-b'],
            }
        )
        primary_event = next(event for event in events if event['stage'] == 'primary_node')
        primary_event['payload']['node_state_write_changed'] = True
        validation_event = next(event for event in events if event['stage'] == 'validation_agent')
        validation_event['payload'].update({'fallback_used': True, 'reason_code': 'validation_fail_open'})
        events.insert(
            1,
            self._event(
                'web_search',
                payload={
                    'enabled': True,
                    'results_count': 2,
                    'context_injected': True,
                    'injected_chars': 77,
                    'read_state': 'page_read',
                    'query': 'RAW QUERY MUST NOT LEAK',
                    'context_block': 'RAW WEB CONTEXT MUST NOT LEAK',
                },
            ),
        )
        events.insert(
            2,
            self._event(
                'memory_chain_snapshot',
                payload={
                    'retrieval': {'retrieved_count': 4},
                    'basket': {'basket_candidates_count': 3, 'deduped_retrieved_count': 1},
                    'arbiter': {'kept_count': 2},
                    'injection': {'injected_candidate_count': 2},
                    'retrieved_candidates': [{'content': 'RAW MEMORY MUST NOT LEAK'}],
                },
            ),
        )
        events.append(
            self._event(
                'embedding',
                status='error',
                payload={'error_code': 'embedding_failed', 'message': 'RAW ERROR MUST NOT LEAK'},
                event_id='evt-embedding-error',
            )
        )
        llm_metrics = log_store.build_llm_call_provider_metrics(
            [
                ('llm', 'ok', 1, 100, 1, 20, datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc)),
                ('validation_agent', 'ok', 1, 40, 1, 5, datetime(2026, 5, 14, 12, 1, tzinfo=timezone.utc)),
            ]
        )

        metrics = log_store.build_full_turn_metrics_snapshot(
            events,
            llm_call_provider_metrics=llm_metrics,
        )

        self.assertEqual(metrics['kind'], 'full_turn_metrics_snapshot')
        self.assertEqual(metrics['events_count'], len(events))
        self.assertEqual(metrics['turns_observed_count'], 1)
        self.assertEqual(metrics['checklist']['classification_counts']['degraded'], 1)
        self.assertEqual(metrics['llm_call_provider_metrics']['main_llm_call_count'], 1)
        self.assertEqual(metrics['llm_call_provider_metrics']['secondary_llm_call_count'], 1)
        self.assertEqual(metrics['prompt_lanes']['trace_memory']['turns_injected'], 1)
        self.assertEqual(metrics['prompt_lanes']['trace_memory']['items_injected_total'], 2)
        self.assertEqual(metrics['prompt_lanes']['summary_context']['items_injected_total'], 1)
        self.assertEqual(metrics['prompt_lanes']['context_hints']['items_injected_total'], 3)
        self.assertEqual(metrics['prompt_lanes']['identity_block']['turns_present'], 1)
        self.assertEqual(metrics['prompt_lanes']['hermeneutic_block']['turns_present'], 1)
        self.assertEqual(metrics['prompt_lanes']['turns_with_mixed_lanes'], 1)
        self.assertEqual(metrics['rag_funnel']['retrieved_candidates_total'], 4)
        self.assertEqual(metrics['rag_funnel']['basketed_candidates_total'], 3)
        self.assertEqual(metrics['rag_funnel']['kept_candidates_total'], 2)
        self.assertEqual(metrics['rag_funnel']['injected_candidates_total'], 2)
        self.assertEqual(metrics['node_state']['read_hit_count'], 1)
        self.assertEqual(metrics['node_state']['write_changed_count'], 1)
        self.assertEqual(metrics['web']['requested_turns'], 1)
        self.assertEqual(metrics['web']['successful_count'], 1)
        self.assertEqual(metrics['web']['injected_chars_total'], 77)
        self.assertEqual(metrics['web']['read_state_counts']['page_read'], 1)
        self.assertEqual(metrics['fallback_fail_open']['by_reason_code']['validation_fail_open'], 1)
        self.assertEqual(metrics['errors_by_stage']['embedding'], 1)

        serialized = json.dumps(metrics, sort_keys=True)
        for forbidden_value in (
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW ERROR MUST NOT LEAK',
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
        ):
            self.assertNotIn(forbidden_value, serialized)
        for forbidden_key in ('payload', 'prompt', 'messages', 'content', 'query', 'context_block'):
            self.assertNotIn(forbidden_key, self._collect_keys(metrics))

    def test_build_turn_pipeline_item_complete_turn_uses_memory_chain_snapshot_content_free(self) -> None:
        events = self._complete_turn_events(web_search_enabled=True)
        events.insert(
            1,
            self._event(
                'web_search',
                payload={
                    'enabled': True,
                    'query': 'RAW QUERY MUST NOT LEAK',
                    'query_present': True,
                    'query_chars': 18,
                    'query_sha256_12': 'c' * 12,
                    'results_count': 2,
                    'context_injected': True,
                    'injected_chars': 77,
                    'read_state': 'page_read',
                    'context_block': 'RAW WEB CONTEXT MUST NOT LEAK',
                },
                event_id='evt-web-search',
            ),
        )
        events.insert(
            2,
            self._event(
                'memory_chain_snapshot',
                payload={
                    'retrieval': {'status': 'ok', 'reason_code': 'observed', 'retrieved_count': 4},
                    'basket': {'status': 'ok', 'basket_candidates_count': 3, 'deduped_retrieved_count': 1},
                    'arbiter': {'status': 'ok', 'kept_count': 2, 'rejected_count': 1},
                    'injection': {'injected_candidate_count': 2, 'context_hints_count': 1},
                    'retrieved_candidates': [{'content': 'RAW MEMORY MUST NOT LEAK'}],
                    'basket_candidates': [{'reason': 'RAW ARBITER REASON MUST NOT LEAK'}],
                    'truncated': False,
                },
                event_id='evt-memory-chain-snapshot',
            ),
        )

        item = log_store.build_turn_pipeline_item(
            events,
            events_total=len(events),
            events_truncated=False,
        )

        self.assertEqual(item['kind'], 'chat_turn_pipeline_item')
        self.assertEqual(item['classification'], 'complete')
        self.assertEqual(item['persistence']['status'], 'saved')
        self.assertTrue(item['providers']['main']['present'])
        self.assertEqual(item['providers']['main']['provider_caller'], 'llm')
        self.assertTrue(item['providers']['secondary']['stimmung']['prepared_present'])
        self.assertEqual(item['rag']['source_kind'], 'memory_chain_snapshot')
        self.assertEqual(item['rag']['retrieved'], 4)
        self.assertEqual(item['rag']['basket'], 3)
        self.assertEqual(item['rag']['kept'], 2)
        self.assertEqual(item['rag']['injected'], 2)
        self.assertEqual(item['identity']['status'], 'present')
        self.assertEqual(item['identity']['chars'], 12)
        self.assertEqual(item['hermeneutic']['status'], 'present')
        self.assertTrue(item['hermeneutic']['node_state']['read_valid'])
        self.assertTrue(item['web']['requested'])
        self.assertTrue(item['web']['injected'])
        self.assertEqual(item['web']['query_sha256_12'], 'c' * 12)
        self.assertFalse(item['flags']['raw_event_payloads_included'])
        self.assertFalse(item['source']['events_truncated'])

        serialized = json.dumps(item, sort_keys=True)
        for forbidden_value in (
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW ARBITER REASON MUST NOT LEAK',
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
        ):
            self.assertNotIn(forbidden_value, serialized)
        for forbidden_key in ('payload', 'prompt', 'messages', 'content', 'query', 'context_block', 'memory'):
            self.assertNotIn(forbidden_key, self._collect_keys(item))

    def test_build_turn_pipeline_item_degraded_and_legacy_without_memory_snapshot(self) -> None:
        events = self._complete_turn_events(web_search_enabled=False)
        prompt_event = next(event for event in events if event['stage'] == 'prompt_prepared')
        prompt_event['payload']['identity_prompt_injection'] = {
            'injected': False,
            'identity_block_present': False,
            'identity_block_chars': 0,
            'identity_block_sha256_12': None,
        }

        degraded = log_store.build_turn_pipeline_item(events)

        self.assertEqual(degraded['classification'], 'degraded')
        self.assertEqual(degraded['identity']['status'], 'absent')
        self.assertEqual(degraded['rag']['source_kind'], 'prompt_prepared_legacy_fallback')
        self.assertEqual(degraded['rag']['legacy_reason_code'], 'missing_memory_chain_snapshot')
        self.assertEqual(degraded['checklist']['degraded_or_missing_items'][0]['reason_code'], 'identity_block_absent')

        legacy = log_store.build_turn_pipeline_item(
            [
                self._event('turn_start', payload={'web_search_enabled': False}),
                self._event('llm_call', payload={'response_chars': 5}),
                self._event('turn_end', payload={'final_status': 'ok'}),
            ],
            events_total=3,
            events_truncated=False,
        )

        self.assertEqual(legacy['classification'], 'legacy_incomplete')
        self.assertEqual(legacy['providers']['main']['status'], 'missing')
        self.assertEqual(legacy['providers']['main']['reason_code'], 'missing_main_llm_call')
        self.assertEqual(legacy['flags']['legacy_reason_code'], 'legacy_incomplete')
        self.assertEqual(legacy['rag']['legacy_reason_code'], 'missing_memory_chain_snapshot')

        for forbidden_key in ('payload', 'prompt', 'messages', 'content', 'query', 'context_block', 'memory'):
            self.assertNotIn(forbidden_key, self._collect_keys(degraded))
            self.assertNotIn(forbidden_key, self._collect_keys(legacy))

    def test_read_full_turn_metrics_snapshot_uses_same_event_window_for_llm_metrics(self) -> None:
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
                        'evt-llm',
                        'conv-metrics',
                        'turn-1',
                        datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
                        'llm_call',
                        'ok',
                        100,
                        {'provider_caller': 'llm', 'response_chars': 20},
                    ),
                    (
                        'evt-validation',
                        'conv-metrics',
                        'turn-1',
                        datetime(2026, 5, 14, 12, 1, tzinfo=timezone.utc),
                        'llm_call',
                        'ok',
                        40,
                        {'provider_caller': 'validation_agent', 'response_chars': 5},
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_full_turn_metrics_snapshot(
            ts_from='2026-05-14T00:00:00Z',
            ts_to='2026-05-15T00:00:00Z',
            event_limit=2,
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['source']['events_total'], 3)
        self.assertEqual(result['source']['events_read'], 2)
        self.assertTrue(result['source']['events_truncated'])
        self.assertEqual(result['filters']['event_limit'], 2)
        self.assertEqual(result['llm_call_provider_metrics']['main_llm_call_count'], 1)
        self.assertEqual(result['llm_call_provider_metrics']['secondary_llm_call_count'], 1)
        self.assertEqual(result['llm_call_provider_metrics']['by_provider_caller']['llm']['avg_duration_ms'], 100.0)
        joined_queries = '\n'.join(str(query) for query, _params in observed['queries'])
        self.assertIn('FROM observability.chat_log_events', joined_queries)
        self.assertIn('LIMIT %s', joined_queries)
        self.assertNotIn('WITH llm_calls', joined_queries)
        self.assertEqual(
            observed['queries'][1][1],
            ('2026-05-14T00:00:00Z', '2026-05-15T00:00:00Z', 2),
        )

    def test_read_chat_turn_pipeline_groups_turns_and_projects_compact_rows(self) -> None:
        observed: dict[str, Any] = {'queries': [], 'event_reads': []}

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
                return (2,)

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        'conv-pipeline',
                        'turn-1',
                        datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
                        datetime(2026, 5, 14, 12, 1, tzinfo=timezone.utc),
                        11,
                    )
                ]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        original_read_events = log_store.read_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            observed['event_reads'].append(kwargs)
            return {
                'items': self._complete_turn_events(web_search_enabled=False),
                'count': 11,
                'total': 11,
                'limit': 500,
                'offset': 0,
                'next_offset': None,
                'filters': {},
            }

        log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            result = log_store.read_chat_turn_pipeline(
                conversation_id='conv-pipeline',
                limit=1,
                offset=0,
                ts_from='2026-05-14T00:00:00Z',
                ts_to='2026-05-15T00:00:00Z',
                conn_factory=lambda: FakeConn(),
                logger_instance=_NoopLogger(),
            )
        finally:
            log_store.read_chat_log_events = original_read_events

        self.assertEqual(result['kind'], 'chat_turn_pipeline_read_model')
        self.assertEqual(result['count'], 1)
        self.assertEqual(result['total'], 2)
        self.assertEqual(result['next_offset'], 1)
        self.assertEqual(result['filters']['conversation_id'], 'conv-pipeline')
        self.assertTrue(result['source']['turns_truncated'])
        self.assertFalse(result['redaction']['raw_event_payloads_included'])
        self.assertEqual(result['items'][0]['classification'], 'complete')
        self.assertEqual(result['items'][0]['persistence']['status'], 'saved')
        self.assertEqual(observed['event_reads'][0]['limit'], 500)
        self.assertEqual(observed['event_reads'][0]['conversation_id'], 'conv-pipeline')
        self.assertEqual(observed['event_reads'][0]['turn_id'], 'turn-1')
        self.assertEqual(observed['event_reads'][0]['ts_from'], '2026-05-14T00:00:00Z')
        self.assertEqual(observed['event_reads'][0]['ts_to'], '2026-05-15T00:00:00Z')

        joined_queries = '\n'.join(str(query) for query, _params in observed['queries'])
        self.assertIn('GROUP BY conversation_id, turn_id', joined_queries)
        self.assertIn('ORDER BY MAX(ts) DESC', joined_queries)
        self.assertIn('LIMIT %s OFFSET %s', joined_queries)
        self.assertEqual(
            observed['queries'][0][1],
            ('conv-pipeline', '2026-05-14T00:00:00Z', '2026-05-15T00:00:00Z'),
        )
        self.assertEqual(
            observed['queries'][1][1],
            ('conv-pipeline', '2026-05-14T00:00:00Z', '2026-05-15T00:00:00Z', 1, 0),
        )

    def test_build_turn_observability_checklist_complete_turn_without_web(self) -> None:
        checklist = log_store.build_turn_observability_checklist(
            self._complete_turn_events(web_search_enabled=False)
        )

        self.assertEqual(checklist['kind'], 'turn_observability_checklist')
        self.assertEqual(checklist['classification'], 'complete')
        self.assertEqual(checklist['score'], 100)
        self.assertEqual(self._find_item(checklist, 'turn_start')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'llm_call_main')['status'], 'ok')
        self.assertEqual(
            self._find_item(checklist, 'persist_response_assistant_final')['reason_code'],
            'assistant_final_saved',
        )
        self.assertEqual(self._find_item(checklist, 'identity_prompt_injection')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'memory_prompt_injection')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'hermeneutic_prompt_injection')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'stimmung_agent')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'validation_agent')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'web_search')['status'], 'not_applicable')
        self.assertEqual(self._find_item(checklist, 'node_state')['status'], 'ok')
        self.assertEqual(self._find_item(checklist, 'stage_errors')['status'], 'ok')

        serialized = json.dumps(checklist, sort_keys=True)
        self.assertNotIn('RAW PROMPT MUST NOT LEAK', serialized)
        self.assertNotIn('RAW MESSAGE MUST NOT LEAK', serialized)
        for forbidden_key in ('prompt', 'messages', 'content', 'query', 'payload'):
            self.assertNotIn(forbidden_key, self._collect_keys(checklist))

    def test_build_turn_observability_checklist_web_skipped_with_reason_is_observed(self) -> None:
        events = self._complete_turn_events(web_search_enabled=True)
        events.insert(
            1,
            self._event(
                'web_search',
                status='skipped',
                payload={
                    'enabled': True,
                    'reason_code': 'no_data',
                    'results_count': 0,
                    'context_injected': False,
                    'read_state': 'no_results',
                    'query': 'RAW QUERY MUST NOT LEAK',
                },
            ),
        )

        checklist = log_store.build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'complete')
        web_item = self._find_item(checklist, 'web_search')
        self.assertEqual(web_item['status'], 'ok')
        self.assertEqual(web_item['reason_code'], 'observed_skipped')
        self.assertEqual(web_item['evidence']['read_state'], 'no_results')
        self.assertNotIn('RAW QUERY MUST NOT LEAK', json.dumps(checklist, sort_keys=True))

    def test_build_turn_observability_checklist_detects_secondary_llm_call_provider(self) -> None:
        events = self._complete_turn_events(web_search_enabled=False)
        events.insert(
            -2,
            self._event(
                'web_reformulation_prompt_prepared',
                payload={
                    'provider_caller': 'web_reformulation',
                    'secondary_provider_payload': True,
                },
                event_id='evt-web-reformulation-prepared',
            ),
        )
        events.insert(
            -2,
            self._event(
                'llm_call',
                payload={
                    'provider_caller': 'web_reformulation',
                    'response_chars': 11,
                },
                event_id='evt-web-reformulation-llm',
            ),
        )

        checklist = log_store.build_turn_observability_checklist(events)

        web_reformulation_item = self._find_item(checklist, 'web_reformulation')
        self.assertEqual(web_reformulation_item['status'], 'ok')
        self.assertEqual(web_reformulation_item['evidence']['prepared_count'], 1)
        self.assertEqual(web_reformulation_item['evidence']['llm_call_count'], 1)

    def test_build_turn_observability_checklist_degrades_empty_identity_fingerprint(self) -> None:
        events = self._complete_turn_events(web_search_enabled=False)
        prompt_event = next(event for event in events if event['stage'] == 'prompt_prepared')
        prompt_event['payload']['identity_prompt_injection'] = {
            'injected': False,
            'identity_block_present': False,
            'identity_block_chars': 0,
            'identity_block_sha256_12': None,
        }

        checklist = log_store.build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'degraded')
        self.assertLess(checklist['score'], 100)
        identity_item = self._find_item(checklist, 'identity_prompt_injection')
        self.assertEqual(identity_item['status'], 'degraded')
        self.assertEqual(identity_item['reason_code'], 'identity_block_absent')

    def test_build_turn_observability_checklist_requires_secondary_prepared_events(self) -> None:
        events = [
            event
            for event in self._complete_turn_events(web_search_enabled=False)
            if event['stage'] not in ('stimmung_prompt_prepared', 'validation_prompt_prepared')
        ]
        events.insert(
            -2,
            self._event(
                'llm_call',
                payload={'provider_caller': 'web_reformulation', 'response_chars': 11},
                event_id='evt-web-reformulation-llm',
            ),
        )

        checklist = log_store.build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'degraded')
        for key in ('stimmung_agent', 'validation_agent', 'web_reformulation'):
            item = self._find_item(checklist, key)
            self.assertEqual(item['status'], 'degraded')
            self.assertEqual(item['reason_code'], 'missing_secondary_provider_prepared')

    def test_build_turn_observability_checklist_fail_open_degrades_with_reason(self) -> None:
        events = self._complete_turn_events(web_search_enabled=False)
        primary_event = next(event for event in events if event['stage'] == 'primary_node')
        primary_event['payload'].update(
            {
                'fail_open': True,
                'reason_code': 'runtime_error',
                'error_class': 'RuntimeError',
            }
        )

        checklist = log_store.build_turn_observability_checklist(events)

        self.assertEqual(checklist['classification'], 'degraded')
        self.assertLess(checklist['score'], 100)
        node_state_item = self._find_item(checklist, 'node_state')
        self.assertEqual(node_state_item['status'], 'degraded')
        self.assertEqual(node_state_item['reason_code'], 'runtime_error')

    def test_build_turn_observability_checklist_legacy_and_unknown_provider_are_partial(self) -> None:
        checklist = log_store.build_turn_observability_checklist(
            [
                self._event('turn_start', payload={'web_search_enabled': False}),
                self._event('llm_call', payload={'response_chars': 5}),
                self._event('turn_end', payload={'final_status': 'ok'}),
            ]
        )

        self.assertEqual(checklist['classification'], 'legacy_incomplete')
        self.assertEqual(self._find_item(checklist, 'prompt_prepared')['status'], 'missing')
        llm_item = self._find_item(checklist, 'llm_call_main')
        self.assertEqual(llm_item['status'], 'missing')
        self.assertEqual(llm_item['reason_code'], 'missing_main_llm_call')
        self.assertEqual(llm_item['evidence']['unknown_llm_call_count'], 1)

    def test_build_turn_observability_checklist_accepts_empty_legacy_logs(self) -> None:
        checklist = log_store.build_turn_observability_checklist([])

        self.assertEqual(checklist['classification'], 'legacy_incomplete')
        self.assertEqual(checklist['score'], 0)
        self.assertEqual(checklist['events_count'], 0)
        self.assertTrue(checklist['items'])

    def test_read_chat_log_metadata_returns_conversations_and_turns_for_selected_conversation(self) -> None:
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

            def fetchall(self) -> list[tuple[Any, ...]]:
                if self._step == 1:
                    return [
                        ('conv-2', datetime(2026, 3, 27, 12, 5, tzinfo=timezone.utc), 5),
                        ('conv-1', datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc), 2),
                    ]
                if self._step == 2:
                    return [
                        ('turn-2', datetime(2026, 3, 27, 12, 5, tzinfo=timezone.utc), 3),
                        ('turn-1', datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc), 2),
                    ]
                return []

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_chat_log_metadata(
            conversation_id='conv-1',
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(result['selected_conversation_id'], 'conv-1')
        self.assertEqual(len(result['conversations']), 2)
        self.assertEqual(result['conversations'][0]['conversation_id'], 'conv-2')
        self.assertEqual(result['conversations'][0]['events_count'], 5)
        self.assertEqual(len(result['turns']), 2)
        self.assertEqual(result['turns'][0]['turn_id'], 'turn-2')
        self.assertEqual(result['turns'][0]['events_count'], 3)

        self.assertEqual(observed['queries'][0][1], ())
        self.assertEqual(observed['queries'][1][1], ('conv-1',))
        joined_queries = '\n'.join(str(query) for query, _params in observed['queries'])
        self.assertIn('GROUP BY conversation_id', joined_queries)
        self.assertIn('WHERE conversation_id = %s', joined_queries)
        self.assertIn('GROUP BY turn_id', joined_queries)

    def test_read_chat_log_metadata_without_conversation_returns_empty_turn_list(self) -> None:
        observed: dict[str, Any] = {'queries': []}

        class FakeCursor:
            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                observed['queries'].append((query, params))

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [('conv-1', datetime(2026, 3, 27, 12, 0, tzinfo=timezone.utc), 2)]

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        result = log_store.read_chat_log_metadata(
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertIsNone(result['selected_conversation_id'])
        self.assertEqual(len(result['conversations']), 1)
        self.assertEqual(result['conversations'][0]['conversation_id'], 'conv-1')
        self.assertEqual(result['turns'], [])
        self.assertEqual(len(observed['queries']), 1)

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


if __name__ == '__main__':
    unittest.main()
