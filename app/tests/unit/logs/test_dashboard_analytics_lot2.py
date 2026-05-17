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

    def _fact_to_persisted_row(self, fact: dict[str, Any]) -> tuple[Any, ...]:
        return (
            fact.get('conversation_id'),
            fact.get('turn_id'),
            datetime.fromisoformat(str(fact.get('first_ts'))),
            datetime.fromisoformat(str(fact.get('latest_ts'))),
            fact.get('classification'),
            fact.get('score'),
            fact.get('source_event_ids') or [],
            fact.get('source_event_count'),
            fact.get('source_first_event_id'),
            fact.get('source_latest_event_id'),
            fact.get('persistence') or {},
            fact.get('providers') or {},
            fact.get('rag') or {},
            fact.get('identity') or {},
            fact.get('hermeneutic') or {},
            fact.get('web') or {},
            fact.get('documents') or {},
            fact.get('node_state') or {},
            fact.get('latencies') or {},
            fact.get('errors') or {},
            fact.get('stage_counts') or {},
            fact.get('flags') or {},
            fact.get('content_availability') or {},
            fact.get('calculation_version'),
        )

    def _fact_from_insert_params(self, params: tuple[Any, ...]) -> dict[str, Any]:
        return {
            'kind': 'dashboard_turn_fact',
            'schema_version': '1',
            'calculation_version': params[23],
            'conversation_id': params[0],
            'turn_id': params[1],
            'first_ts': params[2],
            'latest_ts': params[3],
            'classification': params[4],
            'score': params[5],
            'source_event_ids': json.loads(params[6]),
            'source_event_count': params[7],
            'source_first_event_id': params[8],
            'source_latest_event_id': params[9],
            'persistence': json.loads(params[10]),
            'providers': json.loads(params[11]),
            'rag': json.loads(params[12]),
            'identity': json.loads(params[13]),
            'hermeneutic': json.loads(params[14]),
            'web': json.loads(params[15]),
            'documents': json.loads(params[16]),
            'node_state': json.loads(params[17]),
            'latencies': json.loads(params[18]),
            'errors': json.loads(params[19]),
            'stage_counts': json.loads(params[20]),
            'flags': json.loads(params[21]),
            'content_availability': json.loads(params[22]),
            'redaction': {'raw_content_stored': False, 'raw_event_payloads_included': False},
        }

    def _latest_ts(self, fact: dict[str, Any]) -> datetime:
        return datetime.fromisoformat(str(fact['latest_ts']))

    def _window_state_fake_conn(
        self,
        *,
        state: dict[tuple[str, str], dict[str, Any]],
        observed: dict[str, Any],
        event_rows: list[tuple[Any, ...]] | None = None,
    ):
        test = self

        class FakeCursor:
            def __init__(self) -> None:
                self._rows: list[tuple[Any, ...]] = []

            def __enter__(self) -> 'FakeCursor':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...] | None = None) -> None:
                observed.setdefault('queries', []).append(query)
                observed.setdefault('params', []).append(params)
                compact_query = ' '.join(query.split())

                if 'FROM observability.chat_log_events AS events' in query:
                    self._rows = list(event_rows or [])
                    return

                if compact_query.startswith('SELECT DISTINCT conversation_id FROM observability.dashboard_turn_facts'):
                    start = datetime.fromisoformat(str(params[0]))
                    end = datetime.fromisoformat(str(params[1]))
                    self._rows = sorted(
                        {
                            (fact['conversation_id'],)
                            for fact in state.values()
                            if start <= test._latest_ts(fact) < end
                        }
                    )
                    return

                if compact_query.startswith('DELETE FROM observability.dashboard_turn_facts'):
                    start = datetime.fromisoformat(str(params[0]))
                    end = datetime.fromisoformat(str(params[1]))
                    for key, fact in list(state.items()):
                        if start <= test._latest_ts(fact) < end:
                            del state[key]
                    self._rows = []
                    return

                if compact_query.startswith('INSERT INTO observability.dashboard_turn_facts'):
                    fact = test._fact_from_insert_params(params or ())
                    state[(str(fact['conversation_id']), str(fact['turn_id']))] = fact
                    self._rows = []
                    return

                if 'FROM observability.dashboard_turn_facts' in query and 'conversation_id = ANY' in query:
                    ids = set(params[0] or [])
                    self._rows = [
                        test._fact_to_persisted_row(fact)
                        for fact in sorted(state.values(), key=lambda item: str(item['latest_ts']))
                        if fact['conversation_id'] in ids
                    ]
                    return

                if 'FROM observability.dashboard_turn_facts' in query and 'latest_ts >=' in query:
                    start = datetime.fromisoformat(str(params[0]))
                    end = datetime.fromisoformat(str(params[1]))
                    self._rows = [
                        test._fact_to_persisted_row(fact)
                        for fact in sorted(state.values(), key=lambda item: str(item['latest_ts']))
                        if start <= test._latest_ts(fact) < end
                    ]
                    return

                if compact_query.startswith('INSERT INTO observability.dashboard_conversation_summaries'):
                    observed.setdefault('summary_params', []).append(params)
                    self._rows = []
                    return

                if compact_query.startswith('INSERT INTO observability.dashboard_metric_buckets'):
                    observed.setdefault('bucket_params', []).append(params)
                    self._rows = []
                    return

                self._rows = []

            def fetchall(self) -> list[tuple[Any, ...]]:
                return self._rows

        class FakeConn:
            def __enter__(self) -> 'FakeConn':
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed['commits'] = int(observed.get('commits') or 0) + 1

        return FakeConn

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

    def test_turn_fact_materializes_embedding_counts_content_free(self) -> None:
        events = [
            *self._complete_turn(),
            self._event(
                'embedding',
                payload={
                    'source_kind': 'query',
                    'mode': 'remote',
                    'provider': 'embed-provider',
                    'dimensions': 1536,
                    'text': 'RAW EMBEDDING TEXT MUST NOT LEAK',
                    'vector': [0.1, 0.2],
                },
                event_id='turn-dashboard:0009:embedding-query',
            ),
            self._event(
                'embedding',
                status='error',
                payload={
                    'source_kind': 'trace_user',
                    'mode': 'remote',
                    'provider': 'embed-provider',
                    'dimensions': 1536,
                    'error_message': 'RAW EMBEDDING ERROR MUST NOT LEAK',
                },
                event_id='turn-dashboard:0010:embedding-trace',
            ),
        ]

        fact = dashboard_analytics.build_dashboard_turn_fact(events)
        rag = fact['rag']

        self.assertEqual(rag['embeddings_source_kind'], 'chat_log_events.embedding')
        self.assertEqual(rag['embeddings_requested_count'], 2)
        self.assertEqual(rag['embeddings_success_count'], 1)
        self.assertEqual(rag['embeddings_error_count'], 1)
        self.assertEqual(rag['embeddings_status_counts'], {'error': 1, 'ok': 1})
        self.assertEqual(rag['embeddings_dimension_counts'], {'1536': 2})
        self.assertEqual(rag['embeddings_source_kind_counts'], {'query': 1, 'trace_user': 1})
        serialized = json.dumps(fact, sort_keys=True)
        self.assertNotIn('RAW EMBEDDING TEXT MUST NOT LEAK', serialized)
        self.assertNotIn('RAW EMBEDDING ERROR MUST NOT LEAK', serialized)
        self.assertNotIn('vector', self._collect_keys(fact))

    def test_turn_fact_materializes_active_summary_prompt_usage_content_free(self) -> None:
        events = self._complete_turn()
        prompt_event = next(event for event in events if event['stage'] == 'prompt_prepared')
        prompt_event['payload_json']['memory_prompt_injection'].update(
            {
                'summary_context_injected': True,
                'summary_context_injected_count': 2,
                'memory_context_injected': True,
                'memory_context_summary_count': 1,
                'injected_candidate_ids': ['trace-parent-1'],
                'injection_lanes': ['trace_memory', 'summary_context'],
            }
        )
        events.insert(
            4,
            self._event(
                'hermeneutic_node_insertion',
                payload={
                    'inputs': {
                        'memory_retrieved': {
                            'traces': [
                                {
                                    'candidate_id': 'trace-parent-1',
                                    'source_kind': 'trace',
                                    'summary_id': 'summary-parent-1',
                                    'content': 'RAW MEMORY MUST NOT LEAK',
                                    'parent_summary': {
                                        'id': 'summary-parent-1',
                                        'start_ts': '2026-05-01T00:00:00+00:00',
                                        'end_ts': '2026-05-02T00:00:00+00:00',
                                        'content': 'RAW PARENT SUMMARY MUST NOT LEAK',
                                    },
                                }
                            ],
                        },
                        'memory_arbitration': {
                            'injected_candidate_ids': ['trace-parent-1'],
                        },
                    },
                },
                event_id='turn-dashboard:0004a:hermeneutic_node_insertion',
            ),
        )
        events.insert(
            5,
            self._event(
                'summaries',
                payload={
                    'active_summary_present': True,
                    'summary_count_used': 1,
                    'summary_usage': 'prompt_injection',
                    'in_prompt': True,
                    'summary_generation_observed': False,
                    'content': 'RAW SUMMARY MUST NOT LEAK',
                },
                event_id='turn-dashboard:0004b:summaries',
            ),
        )

        fact = dashboard_analytics.build_dashboard_turn_fact(events)
        rag = fact['rag']

        self.assertEqual(rag['conversation_summary_source_kind'], 'summaries_event')
        self.assertTrue(rag['conversation_summary_event_present'])
        self.assertEqual(rag['conversation_summary_status'], 'ok')
        self.assertTrue(rag['conversation_summary_active_present'])
        self.assertTrue(rag['conversation_summary_in_prompt'])
        self.assertEqual(rag['conversation_summary_count'], 1)
        self.assertTrue(rag['summary_context_injected'])
        self.assertEqual(rag['summary_context_injected_count'], 2)
        self.assertEqual(rag['memory_context_summary_count'], 1)
        self.assertEqual(rag['injected_traces_with_summary_id_count'], 1)
        self.assertEqual(rag['injected_traces_with_parent_summary_count'], 1)
        self.assertEqual(rag['parent_summaries_resolved_count'], 1)
        self.assertEqual(rag['parent_summaries_injected_count'], 1)
        self.assertEqual(rag['parent_summaries_injected'][0]['summary_id'], 'summary-parent-1')
        self.assertEqual(rag['parent_summaries_injected'][0]['start_ts'], '2026-05-01T00:00:00+00:00')
        self.assertEqual(rag['parent_summaries_injected'][0]['end_ts'], '2026-05-02T00:00:00+00:00')
        self.assertEqual(rag['parent_summaries_injected'][0]['linked_trace_count'], 1)
        serialized = json.dumps(fact, sort_keys=True)
        self.assertNotIn('RAW SUMMARY MUST NOT LEAK', serialized)
        self.assertNotIn('RAW PARENT SUMMARY MUST NOT LEAK', serialized)
        self.assertNotIn('content', self._collect_keys(fact))

    def test_turn_fact_materializes_active_documents_content_free(self) -> None:
        events = [
            *self._complete_turn(),
            self._event(
                'active_documents',
                payload={
                    'source_kind': 'active_conversation_documents',
                    'active_count': 2,
                    'injected_count': 1,
                    'not_injected_count': 1,
                    'too_large_count': 1,
                    'ocr_applied_count': 1,
                    'ocr_duration_ms_total': 1200,
                    'ocr_engine_counts': {'stirling-pdf': 1},
                    'reason_code_counts': {'document_too_large_for_turn': 1},
                    'documents': [
                        {
                            'document_id': 'doc-injected',
                            'document_ref': 'refinject',
                            'filename': 'note.txt',
                            'media_type': 'text/plain',
                            'source_extension': '.txt',
                            'byte_size': 42,
                            'text_chars': 31,
                            'token_estimate': 8,
                            'text_sha256_12': 'hashtext1234',
                            'ocr_applied': True,
                            'ocr_engine': 'stirling-pdf',
                            'ocr_languages': 'fra+eng+deu',
                            'ocr_duration_ms': 1200,
                            'active': True,
                            'injected': True,
                            'raw_content_included': False,
                            'text_content': 'RAW DOCUMENT TEXT MUST NOT LEAK',
                        },
                        {
                            'document_id': 'doc-large',
                            'document_ref': 'reflarge',
                            'filename': 'grand.pdf',
                            'media_type': 'application/pdf',
                            'source_extension': '.pdf',
                            'byte_size': 900000,
                            'text_chars': 300000,
                            'token_estimate': 75000,
                            'text_sha256_12': 'hashlarge123',
                            'active': True,
                            'injected': False,
                            'reason_code': 'document_too_large_for_turn',
                            'raw_content_included': False,
                            'text_content': 'RAW LARGE DOCUMENT TEXT MUST NOT LEAK',
                        },
                    ],
                    'future_biblio_included': False,
                    'raw_content_included': False,
                },
                event_id='turn-dashboard:0009:active_documents',
            ),
        ]

        fact = dashboard_analytics.build_dashboard_turn_fact(events)
        documents = fact['documents']

        self.assertEqual(documents['source_kind'], 'active_conversation_documents')
        self.assertTrue(documents['event_present'])
        self.assertEqual(documents['active_count'], 2)
        self.assertEqual(documents['injected_count'], 1)
        self.assertEqual(documents['not_injected_count'], 1)
        self.assertEqual(documents['too_large_count'], 1)
        self.assertEqual(documents['ocr_applied_count'], 1)
        self.assertEqual(documents['ocr_duration_ms_total'], 1200)
        self.assertEqual(documents['ocr_engine_counts'], {'stirling-pdf': 1})
        self.assertFalse(documents['future_biblio_included'])
        self.assertFalse(documents['raw_content_included'])
        self.assertEqual(documents['documents'][0]['filename'], 'note.txt')
        self.assertTrue(documents['documents'][0]['ocr_applied'])
        self.assertEqual(documents['documents'][1]['reason_code'], 'document_too_large_for_turn')

        summaries = dashboard_analytics.build_dashboard_conversation_summaries([fact])
        self.assertEqual(summaries[0]['documents_active_turns'], 1)
        self.assertEqual(summaries[0]['documents_injected_total'], 1)
        self.assertEqual(summaries[0]['documents_not_injected_total'], 1)
        self.assertEqual(summaries[0]['modules_involved']['documents'], 1)

        buckets = dashboard_analytics.build_dashboard_metric_buckets(
            [fact],
            now=datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc),
        )
        doc_hour_bucket = next(
            bucket for bucket in buckets
            if bucket['module_key'] == 'documents' and bucket['granularity'] == 'hour'
        )
        self.assertEqual(doc_hour_bucket['metrics']['active_turns'], 1)
        self.assertEqual(doc_hour_bucket['metrics']['active_documents_total'], 2)
        self.assertEqual(doc_hour_bucket['metrics']['injected_documents_total'], 1)
        self.assertEqual(doc_hour_bucket['metrics']['not_injected_documents_total'], 1)
        self.assertEqual(doc_hour_bucket['metrics']['too_large_documents_total'], 1)
        self.assertEqual(doc_hour_bucket['metrics']['ocr_applied_documents_total'], 1)
        self.assertEqual(doc_hour_bucket['metrics']['ocr_engine_counts']['stirling-pdf'], 1)

        serialized = json.dumps({'fact': fact, 'summaries': summaries, 'buckets': buckets}, sort_keys=True)
        self.assertNotIn('RAW DOCUMENT TEXT MUST NOT LEAK', serialized)
        self.assertNotIn('RAW LARGE DOCUMENT TEXT MUST NOT LEAK', serialized)
        self.assertNotIn('text_content', self._collect_keys(fact))

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
        state: dict[tuple[str, str], dict[str, Any]] = {}
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

        FakeConn = self._window_state_fake_conn(
            state=state,
            observed=observed,
            event_rows=rows,
        )

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
        self.assertIn('WITH touched_turns AS', read_query)
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

    def test_materialize_window_keeps_complete_touched_turn_events(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        observed: dict[str, Any] = {'queries': [], 'params': [], 'commits': 0}
        state: dict[tuple[str, str], dict[str, Any]] = {}
        partial_boundary_events = [
            self._event(
                'turn_start',
                turn_id='turn-boundary',
                ts='2026-05-14T11:59:50+00:00',
                payload={'web_search_enabled': False},
                event_id='turn-boundary:0001:turn_start',
            ),
            self._event(
                'llm_call',
                turn_id='turn-boundary',
                ts='2026-05-14T12:00:05+00:00',
                payload={'provider_caller': 'llm', 'response_chars': 5},
                event_id='turn-boundary:0002:llm_call',
            ),
            self._event(
                'turn_end',
                turn_id='turn-boundary',
                ts='2026-05-14T12:00:20+00:00',
                payload={'final_status': 'ok'},
                event_id='turn-boundary:0003:turn_end',
            ),
        ]
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
            for event in partial_boundary_events
        ]
        FakeConn = self._window_state_fake_conn(
            state=state,
            observed=observed,
            event_rows=rows,
        )

        analytics = dashboard_analytics.materialize_dashboard_analytics_window(
            ts_from='2026-05-14T12:00:00Z',
            ts_to='2026-05-14T12:00:10Z',
            now=now,
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertEqual(analytics['turn_facts'][0]['source_event_count'], 3)
        self.assertEqual(state[('conv-dashboard', 'turn-boundary')]['source_event_count'], 3)
        self.assertIn('WITH touched_turns AS', observed['queries'][0])

    def test_small_window_rebuilds_conversation_summary_from_persisted_wide_facts(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        wide_events = [
            *self._complete_turn(turn_id='turn-early', base_ts='2026-05-14T10:00:00+00:00'),
            *self._complete_turn(turn_id='turn-late', base_ts='2026-05-14T12:00:00+00:00'),
        ]
        wide = dashboard_analytics.build_dashboard_analytics(wide_events, now=now)
        small = dashboard_analytics.build_dashboard_analytics(
            self._complete_turn(turn_id='turn-late', base_ts='2026-05-14T12:00:00+00:00'),
            now=now,
            window_start=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 5, 14, 13, 0, tzinfo=timezone.utc),
        )
        state = {
            (fact['conversation_id'], fact['turn_id']): dict(fact)
            for fact in wide['turn_facts']
        }
        observed: dict[str, Any] = {}
        FakeConn = self._window_state_fake_conn(state=state, observed=observed)

        result = dashboard_analytics.persist_dashboard_analytics(
            small,
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertTrue(result['ok'])
        self.assertEqual(result['conversation_summaries_written'], 1)
        summary_params = observed['summary_params'][-1]
        self.assertEqual(summary_params[0], 'conv-dashboard')
        self.assertEqual(summary_params[5], 2)
        self.assertEqual(sum(json.loads(summary_params[8]).values()), 2)
        self.assertEqual(len(state), 2)
        self.assertNotIn('RAW PROMPT MUST NOT LEAK', json.dumps(observed, sort_keys=True))

    def test_subday_window_rebuilds_daily_bucket_from_persisted_day_facts(self) -> None:
        now = datetime(2026, 5, 15, 12, 0, tzinfo=timezone.utc)
        wide_events = [
            *self._complete_turn(turn_id='turn-early', base_ts='2026-05-14T10:00:00+00:00'),
            *self._complete_turn(turn_id='turn-late', base_ts='2026-05-14T12:00:00+00:00'),
        ]
        wide = dashboard_analytics.build_dashboard_analytics(wide_events, now=now)
        small = dashboard_analytics.build_dashboard_analytics(
            self._complete_turn(turn_id='turn-late', base_ts='2026-05-14T12:00:00+00:00'),
            now=now,
            window_start=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
            window_end=datetime(2026, 5, 14, 13, 0, tzinfo=timezone.utc),
        )
        state = {
            (fact['conversation_id'], fact['turn_id']): dict(fact)
            for fact in wide['turn_facts']
        }
        observed: dict[str, Any] = {}
        FakeConn = self._window_state_fake_conn(state=state, observed=observed)

        result = dashboard_analytics.persist_dashboard_analytics(
            small,
            conn_factory=lambda: FakeConn(),
            logger_instance=_NoopLogger(),
        )

        self.assertTrue(result['ok'])
        day_pipeline_buckets = [
            params for params in observed['bucket_params']
            if params[0] == 'day'
            and str(params[1]).startswith('2026-05-14T00:00:00')
            and params[3] == 'pipeline'
        ]
        hour_pipeline_buckets = [
            params for params in observed['bucket_params']
            if params[0] == 'hour'
            and str(params[1]).startswith('2026-05-14T12:00:00')
            and params[3] == 'pipeline'
        ]
        self.assertEqual(day_pipeline_buckets[-1][4], 2)
        self.assertEqual(
            sum(json.loads(day_pipeline_buckets[-1][6])['classification_counts'].values()),
            2,
        )
        self.assertEqual(hour_pipeline_buckets[-1][4], 1)
        self.assertNotIn('RAW MEMORY MUST NOT LEAK', json.dumps(observed, sort_keys=True))

    def test_execute_dashboard_analytics_schema_creates_persistent_tables(self) -> None:
        observed: list[str] = []

        class FakeCursor:
            def execute(self, query: str, _params: tuple[Any, ...] | None = None) -> None:
                observed.append(query)

        dashboard_analytics.execute_dashboard_analytics_schema(FakeCursor())
        joined = '\n'.join(observed)

        self.assertIn('observability.dashboard_turn_facts', joined)
        self.assertIn('documents_json', joined)
        self.assertIn('observability.dashboard_conversation_summaries', joined)
        self.assertIn('observability.dashboard_metric_buckets', joined)
        self.assertIn('observability.dashboard_materialization_status', joined)
        self.assertIn('CHECK (raw_event_payloads_included = false)', joined)
        self.assertIn('CHECK (source_events_truncated = false)', joined)
        self.assertIn('CHECK (event_limit_dependency = false)', joined)


if __name__ == '__main__':
    unittest.main()
