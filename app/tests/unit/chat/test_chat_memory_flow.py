from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_memory_flow
from memory import hermeneutics_policy
from memory import memory_identity_dynamics


def _event_payloads(events, name: str):
    return [payload for event, payload in events if event == name]


def _trace(
    trace_id: str,
    *,
    conversation_id: str,
    role: str,
    content: str,
    timestamp: str,
    score: float = 0.8,
    summary_id: str | None = None,
    retrieval_score: float | None = None,
    semantic_score: float | None = None,
    source_kind: str | None = None,
    source_lane: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
):
    payload = {
        'trace_id': trace_id,
        'conversation_id': conversation_id,
        'role': role,
        'content': content,
        'timestamp': timestamp,
        'summary_id': summary_id,
        'score': score,
    }
    if retrieval_score is not None:
        payload['retrieval_score'] = retrieval_score
    if semantic_score is not None:
        payload['semantic_score'] = semantic_score
    if source_kind is not None:
        payload['source_kind'] = source_kind
    if source_lane is not None:
        payload['source_lane'] = source_lane
    if start_ts is not None:
        payload['start_ts'] = start_ts
    if end_ts is not None:
        payload['end_ts'] = end_ts
    return payload


class ChatMemoryFlowTests(unittest.TestCase):
    def test_prepare_memory_context_mode_off_keeps_raw_traces_without_arbiter(self) -> None:
        events = []
        observed = {'record_calls': 0, 'enrich_called_with': None}
        raw_traces = [
            _trace(
                'r1',
                conversation_id='conv-source-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.91,
            )
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='off',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-off',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: observed.update({'record_calls': observed['record_calls'] + 1}),
            enrich_traces_with_summaries=lambda traces: observed.update({'enrich_called_with': list(traces)})
            or [{**trace, 'enriched': True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError('arbiter should not run in off mode')
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )
        mode, memory_traces, context_hints = prepared

        self.assertEqual(mode, 'off')
        self.assertEqual(len(memory_traces), 1)
        self.assertEqual(memory_traces[0]['trace_id'], 'r1')
        self.assertTrue(memory_traces[0]['enriched'])
        self.assertTrue(memory_traces[0]['candidate_id'].startswith('cand-'))
        self.assertEqual(context_hints, [])
        self.assertEqual(observed['record_calls'], 0)
        self.assertEqual(observed['enrich_called_with'], raw_traces)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'pre_arbiter_basket_mode_off')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 1)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 0)
        self.assertEqual(_event_payloads(events, 'memory_arbitrated'), [])
        self.assertEqual(prepared.memory_arbitration['status'], 'skipped')
        self.assertEqual(prepared.memory_arbitration['reason_code'], 'mode_off')
        self.assertEqual(prepared.memory_arbitration['raw_candidates_count'], 1)
        self.assertEqual(prepared.memory_arbitration['basket_candidates_count'], 1)
        self.assertEqual(
            prepared.memory_arbitration['injected_candidate_ids'],
            [memory_traces[0]['candidate_id']],
        )
        self.assertEqual(prepared.memory_arbitration['decisions'], [])

    def test_prepare_memory_context_exposes_canonical_memory_retrieved_without_arbiter_fields(self) -> None:
        events = []
        raw_traces = [
            {
                'conversation_id': 'conv-source-a',
                'role': 'user',
                'content': 'Je cours le matin',
                'timestamp': '2026-03-01T08:00:00Z',
                'summary_id': 'sum-1',
                'score': 0.91,
            },
            {
                'conversation_id': 'conv-source-b',
                'role': 'assistant',
                'content': 'Tu avais parle de natation',
                'timestamp': '2026-03-02T09:15:00Z',
                'summary_id': None,
                'score': 0.73,
            },
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='shadow',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-canonical',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            _runtime_embedding_value=lambda field: 9 if field == 'top_k' else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [
                {
                    **trace,
                    'parent_summary': (
                        {
                            'id': 'sum-1',
                            'conversation_id': 'conv-source-a',
                            'start_ts': '2026-03-01T07:00:00Z',
                            'end_ts': '2026-03-01T08:30:00Z',
                            'content': 'Routine sportive du matin',
                        }
                        if trace.get('summary_id') == 'sum-1'
                        else None
                    ),
                }
                for trace in traces
            ],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda _traces, _recent_turns: (
                [raw_traces[0]],
                [{'candidate_id': '0', 'keep': True, 'reason': 'best_match'}],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )
        mode, memory_traces, context_hints = prepared

        self.assertEqual(mode, 'shadow')
        self.assertEqual(len(memory_traces), 2)
        self.assertEqual(context_hints, [])

        memory_retrieved = prepared.memory_retrieved
        self.assertEqual(memory_retrieved['schema_version'], 'v1')
        self.assertEqual(memory_retrieved['retrieval_query'], 'bonjour')
        self.assertEqual(memory_retrieved['top_k_requested'], 9)
        self.assertEqual(memory_retrieved['retrieved_count'], 2)
        self.assertEqual(len(memory_retrieved['traces']), 2)

        candidate_ids = [trace['candidate_id'] for trace in memory_retrieved['traces']]
        self.assertEqual(len(candidate_ids), len(set(candidate_ids)))

        first_trace = memory_retrieved['traces'][0]
        second_trace = memory_retrieved['traces'][1]
        self.assertEqual(first_trace['conversation_id'], 'conv-source-a')
        self.assertEqual(first_trace['role'], 'user')
        self.assertEqual(first_trace['content'], 'Je cours le matin')
        self.assertEqual(first_trace['timestamp_iso'], '2026-03-01T08:00:00Z')
        self.assertEqual(first_trace['retrieval_score'], 0.91)
        self.assertEqual(first_trace['summary_id'], 'sum-1')
        self.assertEqual(first_trace['parent_summary']['id'], 'sum-1')
        self.assertEqual(first_trace['parent_summary']['content'], 'Routine sportive du matin')
        self.assertNotIn('keep', first_trace)
        self.assertNotIn('reason', first_trace)

        self.assertEqual(second_trace['conversation_id'], 'conv-source-b')
        self.assertIsNone(second_trace['parent_summary'])
        self.assertNotIn('semantic_relevance', second_trace)
        self.assertNotIn('decision_source', second_trace)

    def test_prepare_memory_context_prefers_retrieve_for_arbiter_and_keeps_memory_retrieved_public(self) -> None:
        observed = {'arbiter_traces': None}
        internal_traces = [
            {
                'conversation_id': 'conv-source-a',
                'role': 'user',
                'content': 'codex-8192-live-1775296899',
                'timestamp': '2026-04-10T08:00:00Z',
                'summary_id': 'sum-1',
                'score': 0.98,
                'retrieval_score': 0.98,
                'semantic_score': 0.0,
            }
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='shadow',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-internal-retrieval',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: (_ for _ in ()).throw(
                AssertionError('public retrieve should not be used when retrieve_for_arbiter exists')
            ),
            retrieve_for_arbiter=lambda _msg: list(internal_traces),
            _runtime_embedding_value=lambda field: 5 if field == 'top_k' else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: list(traces),
            get_recent_context_hints=lambda **_kwargs: [],
        )

        def fake_filter(traces, _recent_turns):
            observed['arbiter_traces'] = list(traces)
            return [], [
                {
                    'candidate_id': traces[0]['candidate_id'],
                    'keep': False,
                    'semantic_relevance': 0.0,
                    'contextual_gain': 0.0,
                    'redundant_with_recent': False,
                    'reason': 'no_semantic_signal',
                    'decision_source': 'fallback',
                    'model': 'openai/gpt-5.4-mini',
                }
            ]

        arbiter_module = SimpleNamespace(filter_traces_with_diagnostics=fake_filter)
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertIsNotNone(observed['arbiter_traces'])
        self.assertEqual(observed['arbiter_traces'][0]['retrieval_score'], 0.98)
        self.assertEqual(observed['arbiter_traces'][0]['semantic_score'], 0.0)
        self.assertEqual(observed['arbiter_traces'][0]['source_lane'], 'global')
        self.assertTrue(observed['arbiter_traces'][0]['candidate_id'].startswith('cand-'))
        self.assertEqual(prepared.memory_retrieved['traces'][0]['retrieval_score'], 0.98)
        self.assertNotIn('semantic_score', prepared.memory_retrieved['traces'][0])

    def test_prepare_memory_context_exposes_canonical_memory_arbitration_with_stable_and_legacy_links(self) -> None:
        raw_traces = [
            {
                'conversation_id': 'conv-source-a',
                'role': 'user',
                'content': 'Je cours le matin',
                'timestamp': '2026-03-01T08:00:00Z',
                'summary_id': 'sum-1',
                'score': 0.91,
            },
            {
                'conversation_id': 'conv-source-b',
                'role': 'assistant',
                'content': 'Tu avais parle de natation',
                'timestamp': '2026-03-02T09:15:00Z',
                'summary_id': None,
                'score': 0.73,
            },
        ]
        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='shadow',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-arbitration',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: list(traces),
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[0]],
                [
                    {
                        'candidate_id': traces[0]['candidate_id'],
                        'keep': True,
                        'semantic_relevance': 0.94,
                        'contextual_gain': 0.81,
                        'redundant_with_recent': False,
                        'reason': 'best_match',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-test',
                    },
                    {
                        'candidate_id': traces[1]['candidate_id'],
                        'keep': False,
                        'semantic_relevance': 0.33,
                        'contextual_gain': 0.11,
                        'redundant_with_recent': True,
                        'reason': 'redundant',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-test',
                    },
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        memory_retrieved = prepared.memory_retrieved
        memory_arbitration = prepared.memory_arbitration
        candidate_ids = [trace['candidate_id'] for trace in memory_retrieved['traces']]

        self.assertEqual(memory_arbitration['schema_version'], 'v1')
        self.assertEqual(memory_arbitration['status'], 'available')
        self.assertIsNone(memory_arbitration['reason_code'])
        self.assertEqual(memory_arbitration['raw_candidates_count'], 2)
        self.assertEqual(memory_arbitration['basket_candidates_count'], 2)
        self.assertEqual(memory_arbitration['decisions_count'], 2)
        self.assertEqual(memory_arbitration['kept_count'], 1)
        self.assertEqual(memory_arbitration['rejected_count'], 1)
        self.assertEqual(memory_arbitration['injected_candidate_ids'], candidate_ids[:2])

        first_decision = memory_arbitration['decisions'][0]
        second_decision = memory_arbitration['decisions'][1]
        self.assertEqual(first_decision['candidate_id'], memory_retrieved['traces'][0]['candidate_id'])
        self.assertEqual(first_decision['retrieved_candidate_id'], memory_retrieved['traces'][0]['candidate_id'])
        self.assertIsNone(first_decision['legacy_candidate_id'])
        self.assertIsNone(first_decision['legacy_candidate_index'])
        self.assertTrue(first_decision['keep'])
        self.assertEqual(first_decision['semantic_relevance'], 0.94)
        self.assertEqual(first_decision['contextual_gain'], 0.81)
        self.assertFalse(first_decision['redundant_with_recent'])
        self.assertEqual(first_decision['reason'], 'best_match')
        self.assertEqual(first_decision['decision_source'], 'llm')
        self.assertEqual(first_decision['model'], 'openrouter/arbiter-test')
        self.assertEqual(first_decision['source_candidate_ids'], [memory_retrieved['traces'][0]['candidate_id']])
        self.assertNotIn('content', first_decision)

        self.assertEqual(second_decision['candidate_id'], memory_retrieved['traces'][1]['candidate_id'])
        self.assertEqual(second_decision['retrieved_candidate_id'], memory_retrieved['traces'][1]['candidate_id'])
        self.assertIsNone(second_decision['legacy_candidate_id'])
        self.assertIsNone(second_decision['legacy_candidate_index'])
        self.assertFalse(second_decision['keep'])
        self.assertTrue(second_decision['redundant_with_recent'])

    def test_prepare_memory_context_keeps_summary_candidate_ids_stable_through_basket_and_injection(self) -> None:
        raw_traces = [
            _trace(
                'summary-1',
                conversation_id='conv-prefs',
                role='summary',
                content='Preferences durables: reponses courtes et ton direct.',
                timestamp='2026-04-10T09:10:00Z',
                score=0.92,
                summary_id='sum-prefs',
                retrieval_score=0.92,
                semantic_score=0.92,
                source_kind='summary',
                source_lane='summaries',
                start_ts='2026-04-10T09:00:00Z',
                end_ts='2026-04-10T09:10:00Z',
            ),
            _trace(
                'trace-1',
                conversation_id='conv-prefs',
                role='user',
                content='Tu preferes les reponses courtes.',
                timestamp='2026-04-10T09:02:00Z',
                score=0.82,
                summary_id='sum-prefs',
                retrieval_score=0.82,
                semantic_score=0.82,
            ),
            _trace(
                'trace-2',
                conversation_id='conv-prefs',
                role='user',
                content='Tu veux un ton direct.',
                timestamp='2026-04-10T09:05:00Z',
                score=0.81,
                summary_id='sum-prefs',
                retrieval_score=0.81,
                semantic_score=0.81,
            ),
        ]
        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='enforced_all',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-summary-lane',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve_for_arbiter=lambda _msg: list(raw_traces),
            _runtime_embedding_value=lambda field: 5 if field == 'top_k' else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [
                {
                    **trace,
                    'parent_summary': None if trace.get('role') == 'summary' else {
                        'id': 'sum-prefs',
                        'conversation_id': 'conv-prefs',
                        'start_ts': '2026-04-10T09:00:00Z',
                        'end_ts': '2026-04-10T09:10:00Z',
                        'content': 'Preferences utilisateur durables',
                    },
                }
                for trace in traces
            ],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[0]],
                [
                    {
                        'candidate_id': traces[0]['candidate_id'],
                        'keep': True,
                        'semantic_relevance': 0.92,
                        'contextual_gain': 0.9,
                        'redundant_with_recent': False,
                        'reason': 'summary_wins',
                        'decision_source': 'fallback',
                        'model': 'tests',
                    }
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='preferences durables',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(len(prepared.memory_traces), 1)
        self.assertEqual(prepared.memory_traces[0]['candidate_id'], 'summary:sum-prefs')
        self.assertEqual(prepared.memory_traces[0]['role'], 'summary')
        self.assertIsNone(prepared.memory_traces[0]['parent_summary'])
        self.assertEqual(prepared.memory_arbitration['injected_candidate_ids'], ['summary:sum-prefs'])
        self.assertEqual(prepared.memory_arbitration['basket_candidates'][0]['candidate_id'], 'summary:sum-prefs')
        self.assertEqual(prepared.memory_arbitration['basket_candidates'][0]['source_kind'], 'summary')
        self.assertEqual(
            set(prepared.memory_arbitration['basket_candidates'][0]['source_candidate_ids']),
            {
                'summary:sum-prefs',
                prepared.memory_retrieved['traces'][1]['candidate_id'],
                prepared.memory_retrieved['traces'][2]['candidate_id'],
            },
        )

    def test_prepare_memory_context_mode_shadow_uses_pre_arbiter_basket_for_prompt_side(self) -> None:
        events = []
        observed = {
            'arbiter_recent_turns': None,
            'record_args': None,
            'enrich_called_with': None,
        }
        raw_traces = [
            _trace(
                'r1',
                conversation_id='conv-shadow-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.91,
            ),
            _trace(
                'r2',
                conversation_id='conv-shadow-b',
                role='assistant',
                content='Nous travaillons sur FridaDev',
                timestamp='2026-04-10T09:01:00Z',
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='shadow',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-shadow',
            'messages': [
                {'role': 'system', 'content': 'system'},
                {'role': 'user', 'content': 'hello'},
                {'role': 'assistant', 'content': 'world'},
            ],
        }

        def fake_filter(traces, recent_turns):
            observed['arbiter_recent_turns'] = list(recent_turns)
            decisions = [
                {
                    'candidate_id': traces[0]['candidate_id'],
                    'keep': False,
                    'semantic_relevance': 0.1,
                    'contextual_gain': 0.1,
                    'redundant_with_recent': False,
                    'reason': 'shadow',
                    'decision_source': 'llm',
                    'model': 'openrouter/arbiter-test',
                },
                {
                    'candidate_id': traces[1]['candidate_id'],
                    'keep': True,
                    'semantic_relevance': 0.9,
                    'contextual_gain': 0.8,
                    'redundant_with_recent': False,
                    'reason': 'keep',
                    'decision_source': 'llm',
                    'model': 'openrouter/arbiter-test',
                },
            ]
            return [traces[1]], decisions

        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda conversation_id, traces, decisions: observed.update(
                {'record_args': (conversation_id, list(traces), list(decisions))}
            ),
            enrich_traces_with_summaries=lambda traces: observed.update({'enrich_called_with': list(traces)})
            or [{**trace, 'enriched': True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(filter_traces_with_diagnostics=fake_filter)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        mode, memory_traces, _context_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(mode, 'shadow')
        self.assertEqual([trace['trace_id'] for trace in memory_traces], ['r1', 'r2'])
        self.assertTrue(all(trace['candidate_id'].startswith('cand-') for trace in memory_traces))
        self.assertEqual(observed['record_args'][0], 'conv-memory-shadow')
        self.assertEqual(
            [trace['trace_id'] for trace in observed['record_args'][1]],
            ['r1', 'r2'],
        )
        self.assertEqual(
            [decision['candidate_id'] for decision in observed['record_args'][2]],
            [trace['candidate_id'] for trace in observed['record_args'][1]],
        )
        self.assertEqual(observed['enrich_called_with'], raw_traces)
        self.assertEqual(
            [entry['role'] for entry in observed['arbiter_recent_turns']],
            ['user', 'assistant'],
        )
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'pre_arbiter_basket_shadow')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 2)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 1)
        self.assertEqual(_event_payloads(events, 'memory_arbitrated')[0]['decisions'], 2)

    def test_prepare_memory_context_mode_enforced_all_uses_filtered_traces(self) -> None:
        events = []
        raw_traces = [
            _trace(
                'r1',
                conversation_id='conv-enforced-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.91,
            ),
            _trace(
                'r2',
                conversation_id='conv-enforced-b',
                role='assistant',
                content='Nous travaillons sur FridaDev',
                timestamp='2026-04-10T09:01:00Z',
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='enforced_all',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-enforced-all',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [{**trace, 'enriched': True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[1]],
                [
                    {
                        'candidate_id': traces[0]['candidate_id'],
                        'keep': False,
                        'semantic_relevance': 0.2,
                        'contextual_gain': 0.1,
                        'redundant_with_recent': False,
                        'reason': 'reject',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-test',
                    },
                    {
                        'candidate_id': traces[1]['candidate_id'],
                        'keep': True,
                        'semantic_relevance': 0.9,
                        'contextual_gain': 0.8,
                        'redundant_with_recent': False,
                        'reason': 'keep',
                        'decision_source': 'llm',
                        'model': 'openrouter/arbiter-test',
                    },
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        mode, memory_traces, _context_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(mode, 'enforced_all')
        self.assertEqual([trace['trace_id'] for trace in memory_traces], ['r2'])
        self.assertTrue(memory_traces[0]['candidate_id'].startswith('cand-'))
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'arbiter_enforced')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 1)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 1)

    def test_prepare_memory_context_logs_context_hints_when_present(self) -> None:
        events = []
        context_hints = [{'identity_id': 'id-1'}, {'identity_id': 'id-2'}]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='off',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-hints',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: [],
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: context_hints,
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: ([], []),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        _mode, memory_traces, returned_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(memory_traces, [])
        self.assertEqual(returned_hints, context_hints)
        self.assertEqual(_event_payloads(events, 'context_hints_selected')[0]['count'], 2)

    def test_prepare_memory_context_emits_arbiter_skipped_when_no_raw_traces(self) -> None:
        events = []
        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='shadow',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-empty',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: [],
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError('arbiter should not run with empty traces')
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        try:
            _mode, memory_traces, context_hints = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg='bonjour',
                config_module=config_module,
                memory_store_module=memory_store_module,
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch

        self.assertEqual(memory_traces, [])
        self.assertEqual(context_hints, [])
        self.assertTrue(chat_events)
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, 'arbiter')
        self.assertEqual(kwargs['status'], 'skipped')
        self.assertEqual(kwargs['reason_code'], 'no_data')
        self.assertEqual(kwargs['payload']['raw_candidates'], 0)
        self.assertEqual(kwargs['payload']['kept_candidates'], 0)
        self.assertEqual(kwargs['payload']['mode'], 'shadow')
        self.assertEqual(branch_events, [('no_data', 'arbiter_no_traces')])

    def test_prepare_memory_context_emits_arbiter_skipped_when_mode_off_with_raw_traces(self) -> None:
        events = []
        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        raw_traces = [
            _trace(
                'r1',
                conversation_id='conv-off-a',
                role='user',
                content='Je suis Christophe Muck',
                timestamp='2026-04-10T09:00:00Z',
                score=0.91,
            ),
            _trace(
                'r2',
                conversation_id='conv-off-b',
                role='assistant',
                content='Nous travaillons sur FridaDev',
                timestamp='2026-04-10T09:01:00Z',
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE='off',
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            'id': 'conv-memory-off-skip',
            'messages': [{'role': 'user', 'content': 'hello'}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError('arbiter should not run in off mode')
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        try:
            _mode, memory_traces, context_hints = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg='bonjour',
                config_module=config_module,
                memory_store_module=memory_store_module,
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch

        self.assertEqual([trace['trace_id'] for trace in memory_traces], ['r1', 'r2'])
        self.assertTrue(all(trace['candidate_id'].startswith('cand-') for trace in memory_traces))
        self.assertEqual(context_hints, [])
        self.assertTrue(chat_events)
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, 'arbiter')
        self.assertEqual(kwargs['status'], 'skipped')
        self.assertEqual(kwargs['reason_code'], 'mode_off')
        self.assertEqual(kwargs['payload']['raw_candidates'], 2)
        self.assertEqual(kwargs['payload']['basket_candidates'], 2)
        self.assertEqual(kwargs['payload']['kept_candidates'], 2)
        self.assertEqual(kwargs['payload']['mode'], 'off')
        self.assertEqual(branch_events, [('mode_off', 'arbiter_disabled_for_mode')])

    def test_record_identity_entries_for_mode_handles_off_and_enforced(self) -> None:
        events = []
        observed = {
            'extract_called': 0,
            'persisted': None,
            'preview_called': 0,
            'evidence_called': 0,
        }

        arbiter_module = SimpleNamespace(
            extract_identities=lambda turns: observed.update({'extract_called': observed['extract_called'] + 1})
            or [{'identity_id': 'id-1'}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update({'persisted': (conversation_id, list(entries))}),
            preview_identity_entries=lambda entries: observed.update({'preview_called': observed['preview_called'] + 1}) or entries,
            record_identity_evidence=lambda *_args, **_kwargs: observed.update({'evidence_called': observed['evidence_called'] + 1}),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-off',
            [{'role': 'user', 'content': 'x'}],
            mode='off',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-enforced',
            [{'role': 'assistant', 'content': 'y'}],
            mode='enforced_all',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['extract_called'], 1)
        self.assertEqual(observed['persisted'], ('conv-identity-enforced', [{'identity_id': 'id-1'}]))
        self.assertEqual(observed['preview_called'], 0)
        self.assertEqual(observed['evidence_called'], 0)
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[0]['action'], 'skip_mode_off')
        self.assertEqual(
            _event_payloads(events, 'identity_mode_apply')[1]['action'],
            'record_legacy_identity_diagnostics_and_stage',
        )

    def test_record_identity_entries_for_mode_enforced_runs_periodic_identity_staging_after_legacy_persist(self) -> None:
        events = []
        order: list[str] = []
        observed = {'turn_pair': None}
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [{'identity_id': 'id-1'}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: order.append(
                f'persist:{conversation_id}:{len(list(entries))}'
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def fake_stage(conversation_id, turn_pair, **_kwargs):
            order.append(f'stage:{conversation_id}')
            observed['turn_pair'] = list(turn_pair)
            return {
                'status': 'buffering',
                'reason_code': 'below_threshold',
                'buffer_pairs_count': 1,
                'buffer_target_pairs': 15,
                'buffer_cleared': False,
                'writes_applied': False,
                'last_agent_status': 'buffering',
                'outcomes': [
                    {
                        'subject': 'llm',
                        'action': 'no_change',
                        'old_len': 0,
                        'new_len': 0,
                        'validation_ok': True,
                        'reason_code': 'no_change',
                    }
                ],
            }

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = fake_stage
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-enforced',
                [
                    {'role': 'user', 'content': 'x'},
                    {'role': 'assistant', 'content': 'y'},
                ],
                mode='enforced_all',
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(order, ['persist:conv-identity-enforced:1', 'stage:conv-identity-enforced'])
        self.assertEqual(
            observed['turn_pair'],
            [
                {'role': 'user', 'content': 'x'},
                {'role': 'assistant', 'content': 'y'},
            ],
        )
        stage_event = _event_payloads(events, 'identity_periodic_agent_apply')[0]
        self.assertEqual(stage_event['status'], 'buffering')
        self.assertEqual(stage_event['reason_code'], 'below_threshold')
        self.assertEqual(stage_event['buffer_pairs_count'], 1)
        self.assertEqual(
            _event_payloads(events, 'identity_mode_apply')[0]['action'],
            'record_legacy_identity_diagnostics_and_stage',
        )

    def test_record_identity_entries_for_mode_enforced_keeps_fail_open_when_periodic_agent_raises(self) -> None:
        events = []
        observed = {'persisted': None}
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [{'identity_id': 'id-1'}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def boom(*_args, **_kwargs):
            raise RuntimeError('periodic staging exploded')

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = boom
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-enforced',
                [
                    {'role': 'user', 'content': 'x'},
                    {'role': 'assistant', 'content': 'y'},
                ],
                mode='enforced_all',
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(observed['persisted'], ('conv-identity-enforced', [{'identity_id': 'id-1'}]))
        stage_event = _event_payloads(events, 'identity_periodic_agent_apply')[0]
        self.assertEqual(stage_event['status'], 'skipped')
        self.assertEqual(stage_event['reason_code'], 'periodic_agent_flow_error')
        self.assertEqual(
            _event_payloads(events, 'identity_mode_apply')[0]['action'],
            'record_legacy_identity_diagnostics_and_stage',
        )

    def test_record_identity_entries_for_mode_does_not_pass_partial_read_overclaim_to_identity_buffer(self) -> None:
        events = []
        observed = {
            'persisted': None,
            'buffered_turn_pair': None,
        }
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Claims to have read the full article in detail',
                    'confidence': 0.88,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def fake_stage(_conversation_id, turn_pair, **_kwargs):
            observed['buffered_turn_pair'] = list(turn_pair)
            return {
                'status': 'buffering',
                'reason_code': 'below_threshold',
                'buffer_pairs_count': 1,
                'buffer_target_pairs': 15,
                'buffer_cleared': False,
                'writes_applied': False,
                'last_agent_status': 'buffering',
                'outcomes': [
                    {
                        'subject': 'llm',
                        'action': 'no_change',
                        'old_len': 0,
                        'new_len': 0,
                        'validation_ok': True,
                        'reason_code': 'no_change',
                    }
                ],
            }

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = fake_stage
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-partial-guard',
                [
                    {'role': 'user', 'content': 'Peux-tu le lire ?'},
                    {'role': 'assistant', 'content': 'Claims to have read the full article in detail'},
                ],
                mode='enforced_all',
                web_input={'read_state': 'page_partially_read'},
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(observed['persisted'], ('conv-identity-partial-guard', []))
        self.assertEqual(
            observed['buffered_turn_pair'],
            [
                {'role': 'user', 'content': 'Peux-tu le lire ?'},
                {'role': 'assistant', 'content': ''},
            ],
        )
        stage_event = _event_payloads(events, 'identity_periodic_agent_apply')[0]
        self.assertEqual(stage_event['status'], 'buffering')
        self.assertEqual(stage_event['reason_code'], 'below_threshold')
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[0]['guard_filtered_count'], 1)

    def test_record_identity_entries_for_mode_shadow_emits_skipped_identity_write_per_side(self) -> None:
        events = []
        observed = {
            'extract_called': 0,
            'persist_called': 0,
            'preview_called': 0,
            'evidence_args': None,
        }
        preview_entries = [
            {'subject': 'llm', 'content': 'Frida profile', 'status': 'accepted'},
            {'subject': 'user', 'content': 'User preference one', 'status': 'deferred'},
            {'subject': 'user', 'content': 'User preference two', 'status': 'accepted'},
        ]

        arbiter_module = SimpleNamespace(
            extract_identities=lambda turns: observed.update({'extract_called': observed['extract_called'] + 1}) or list(turns),
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda *_args, **_kwargs: observed.update({'persist_called': observed['persist_called'] + 1}),
            preview_identity_entries=lambda _entries: observed.update({'preview_called': observed['preview_called'] + 1}) or preview_entries,
            record_identity_evidence=lambda conversation_id, entries: observed.update(
                {'evidence_args': (conversation_id, list(entries))}
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-shadow',
                [{'subject': 'user', 'content': 'hello'}],
                mode='shadow',
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch

        self.assertEqual(observed['extract_called'], 1)
        self.assertEqual(observed['persist_called'], 0)
        self.assertEqual(observed['preview_called'], 1)
        self.assertEqual(observed['evidence_args'], ('conv-identity-shadow', preview_entries))

        identity_events = [kwargs for stage, kwargs in chat_events if stage == 'identity_write']
        self.assertEqual(len(identity_events), 2)
        by_side = {event['payload']['target_side']: event for event in identity_events}
        self.assertSetEqual(set(by_side.keys()), {'frida', 'user'})
        self.assertTrue(all(event['status'] == 'skipped' for event in identity_events))
        self.assertTrue(all(event['reason_code'] == 'not_applicable' for event in identity_events))
        self.assertEqual(by_side['frida']['payload']['write_mode'], 'legacy_diagnostic_shadow')
        self.assertEqual(by_side['frida']['payload']['write_effect'], 'evidence_only')
        self.assertEqual(by_side['frida']['payload']['evidence_count'], 1)
        self.assertEqual(by_side['frida']['payload']['observed_count'], 1)
        self.assertEqual(by_side['user']['payload']['evidence_count'], 2)
        self.assertEqual(by_side['user']['payload']['observed_count'], 2)
        self.assertTrue(all(event['payload']['persisted_count'] == 0 for event in identity_events))
        self.assertTrue(all(event['payload']['retained_count'] == 0 for event in identity_events))
        self.assertTrue(all(event['payload']['content_present'] for event in identity_events))
        self.assertTrue(all('preview' not in event['payload'] for event in identity_events))
        self.assertTrue(all('entries' not in event['payload'] for event in identity_events))
        self.assertEqual(branch_events, [('not_applicable', 'identity_write_shadow_mode')])
        self.assertEqual(
            _event_payloads(events, 'identity_mode_apply')[0]['action'],
            'record_legacy_identity_evidence_shadow',
        )

    def test_record_identity_entries_for_mode_filters_unsupported_web_reading_claim_in_enforced_mode(self) -> None:
        events = []
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Claims to have the linked article open and read it',
                    'confidence': 0.91,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-guard-enforced',
            [{'role': 'assistant', 'content': 'bad claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_not_read_snippet_fallback'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-guard-enforced', []))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['action'], 'record_legacy_identity_diagnostics_and_stage')
        self.assertEqual(event['entries'], 0)
        self.assertEqual(event['extracted_entries'], 1)
        self.assertEqual(event['guard_filtered_count'], 1)
        self.assertEqual(event['guard_filtered_by_side'], {'frida': 1, 'user': 0})
        self.assertEqual(
            event['guard_reason_codes_by_side']['frida'],
            ['web_reading_claim_unsupported_for_page_not_read_snippet_fallback'],
        )
        self.assertEqual(event['guard_reason_codes_by_side']['user'], [])
        self.assertNotIn('guard_filtered_preview', event)

    def test_record_identity_entries_for_mode_filters_frida_pipeline_meta_identity_in_enforced_mode(self) -> None:
        events = []
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Unable to provide a substantive answer on that turn because the rules did not allow it',
                    'confidence': 0.92,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-meta-filter',
            [{'role': 'assistant', 'content': 'meta'}],
            mode='enforced_all',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-meta-filter', []))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 1)
        self.assertEqual(event['guard_filtered_by_side'], {'frida': 1, 'user': 0})
        self.assertEqual(
            event['guard_reason_codes_by_side']['frida'],
            ['llm_identity_pipeline_meta'],
        )
        self.assertEqual(event['guard_reason_codes_by_side']['user'], [])
        self.assertNotIn('guard_filtered_preview', event)

    def test_record_identity_entries_for_mode_keeps_prudent_web_limitation_statement(self) -> None:
        events = []
        observed = {'persisted': None}
        prudent_entry = {
            'subject': 'llm',
            'content': "Frida n'a pas accès au contenu complet d'un article via un lien direct dans ce contexte",
            'confidence': 0.82,
            'stability': 'episodic',
            'utterance_mode': 'self_description',
            'recurrence': 'first_seen',
            'scope': 'llm',
            'evidence_kind': 'explicit',
        }

        arbiter_module = SimpleNamespace(extract_identities=lambda _turns: [dict(prudent_entry)])
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-prudent',
            [{'role': 'assistant', 'content': 'prudent claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_not_read_crawl_empty'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-prudent', [prudent_entry]))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 0)

    def test_record_identity_entries_for_mode_keeps_supported_direct_reading_claim_when_page_read(self) -> None:
        events = []
        observed = {'persisted': None}
        direct_read_entry = {
            'subject': 'llm',
            'content': 'Claims to have the linked article open and read it',
            'confidence': 0.91,
            'stability': 'durable',
            'utterance_mode': 'self_description',
            'recurrence': 'repeated',
            'scope': 'llm',
            'evidence_kind': 'explicit',
        }

        arbiter_module = SimpleNamespace(extract_identities=lambda _turns: [dict(direct_read_entry)])
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-page-read',
            [{'role': 'assistant', 'content': 'supported claim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_read'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-page-read', [direct_read_entry]))
        event = _event_payloads(events, 'identity_mode_apply')[0]
        self.assertEqual(event['guard_filtered_count'], 0)

    def test_record_identity_entries_for_mode_filters_overclaim_when_page_partially_read(self) -> None:
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'llm',
                    'content': 'Claims to have read the full article in detail',
                    'confidence': 0.88,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'repeated',
                    'scope': 'llm',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {'persisted': (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-identity-partial',
            [{'role': 'assistant', 'content': 'overclaim'}],
            mode='enforced_all',
            web_input={'read_state': 'page_partially_read'},
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed['persisted'], ('conv-identity-partial', []))

    def test_record_identity_entries_for_mode_accepts_explicit_user_identity_revelation(self) -> None:
        observed = {'persisted': None}

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    'subject': 'user',
                    'content': 'Je suis Christophe Muck',
                    'confidence': 0.93,
                    'stability': 'durable',
                    'utterance_mode': 'self_description',
                    'recurrence': 'first_seen',
                    'scope': 'user',
                    'evidence_kind': 'explicit',
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {
                    'persisted': (
                        conversation_id,
                        memory_identity_dynamics.preview_identity_entries(
                            list(entries),
                            policy_module=hermeneutics_policy,
                            config_module=SimpleNamespace(
                                IDENTITY_MIN_CONFIDENCE=0.6,
                                IDENTITY_DEFER_MIN_CONFIDENCE=0.3,
                            ),
                            trace_float_fn=lambda value: float(value or 0.0),
                        ),
                    )
                }
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        chat_memory_flow.record_identity_entries_for_mode(
            'conv-user-identity-revelation',
            [{'role': 'user', 'content': 'Je suis Christophe Muck'}],
            mode='enforced_all',
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        persisted = observed['persisted']
        self.assertIsNotNone(persisted)
        self.assertEqual(persisted[0], 'conv-user-identity-revelation')
        self.assertEqual(persisted[1][0]['status'], 'accepted')
        self.assertIn('explicit_user_identity_revelation', persisted[1][0]['reason'])


if __name__ == '__main__':
    unittest.main()
