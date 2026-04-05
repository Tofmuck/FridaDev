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


class ChatMemoryFlowTests(unittest.TestCase):
    def test_prepare_memory_context_mode_off_keeps_raw_traces_without_arbiter(self) -> None:
        events = []
        observed = {'record_calls': 0, 'enrich_called_with': None}
        raw_traces = [{'trace_id': 'r1'}]

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
            or [{'trace_id': trace['trace_id'], 'enriched': True} for trace in traces],
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
        self.assertEqual(memory_traces, [{'trace_id': 'r1', 'enriched': True}])
        self.assertEqual(context_hints, [])
        self.assertEqual(observed['record_calls'], 0)
        self.assertEqual(observed['enrich_called_with'], raw_traces)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'raw_mode_off')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 1)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 0)
        self.assertEqual(_event_payloads(events, 'memory_arbitrated'), [])
        self.assertEqual(prepared.memory_arbitration['status'], 'skipped')
        self.assertEqual(prepared.memory_arbitration['reason_code'], 'mode_off')
        self.assertEqual(prepared.memory_arbitration['raw_candidates_count'], 1)
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
        arbiter_decisions = [
            {
                'candidate_id': '0',
                'keep': True,
                'semantic_relevance': 0.94,
                'contextual_gain': 0.81,
                'redundant_with_recent': False,
                'reason': 'best_match',
                'decision_source': 'llm',
                'model': 'openrouter/arbiter-test',
            },
            {
                'candidate_id': '1',
                'keep': False,
                'semantic_relevance': 0.33,
                'contextual_gain': 0.11,
                'redundant_with_recent': True,
                'reason': 'redundant',
                'decision_source': 'llm',
                'model': 'openrouter/arbiter-test',
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
            filter_traces_with_diagnostics=lambda _traces, _recent_turns: (
                [raw_traces[0]],
                arbiter_decisions,
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

        self.assertEqual(memory_arbitration['schema_version'], 'v1')
        self.assertEqual(memory_arbitration['status'], 'available')
        self.assertIsNone(memory_arbitration['reason_code'])
        self.assertEqual(memory_arbitration['raw_candidates_count'], 2)
        self.assertEqual(memory_arbitration['decisions_count'], 2)
        self.assertEqual(memory_arbitration['kept_count'], 1)
        self.assertEqual(memory_arbitration['rejected_count'], 1)

        first_decision = memory_arbitration['decisions'][0]
        second_decision = memory_arbitration['decisions'][1]
        self.assertEqual(first_decision['legacy_candidate_id'], '0')
        self.assertEqual(first_decision['legacy_candidate_index'], 0)
        self.assertEqual(first_decision['retrieved_candidate_id'], memory_retrieved['traces'][0]['candidate_id'])
        self.assertTrue(first_decision['keep'])
        self.assertEqual(first_decision['semantic_relevance'], 0.94)
        self.assertEqual(first_decision['contextual_gain'], 0.81)
        self.assertFalse(first_decision['redundant_with_recent'])
        self.assertEqual(first_decision['reason'], 'best_match')
        self.assertEqual(first_decision['decision_source'], 'llm')
        self.assertEqual(first_decision['model'], 'openrouter/arbiter-test')
        self.assertNotIn('content', first_decision)

        self.assertEqual(second_decision['legacy_candidate_id'], '1')
        self.assertEqual(second_decision['legacy_candidate_index'], 1)
        self.assertEqual(second_decision['retrieved_candidate_id'], memory_retrieved['traces'][1]['candidate_id'])
        self.assertFalse(second_decision['keep'])
        self.assertTrue(second_decision['redundant_with_recent'])

    def test_prepare_memory_context_mode_shadow_calls_arbiter_but_keeps_raw_source(self) -> None:
        events = []
        observed = {
            'arbiter_recent_turns': None,
            'record_args': None,
            'enrich_called_with': None,
        }
        raw_traces = [{'trace_id': 'r1'}, {'trace_id': 'r2'}]
        filtered_traces = [{'trace_id': 'r2'}]
        arbiter_decisions = [{'trace_id': 'r1', 'keep': False}]

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
            return filtered_traces, arbiter_decisions

        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda conversation_id, traces, decisions: observed.update(
                {'record_args': (conversation_id, list(traces), list(decisions))}
            ),
            enrich_traces_with_summaries=lambda traces: observed.update({'enrich_called_with': list(traces)})
            or [{'trace_id': trace['trace_id'], 'enriched': True} for trace in traces],
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
        self.assertEqual(memory_traces, [{'trace_id': 'r1', 'enriched': True}, {'trace_id': 'r2', 'enriched': True}])
        self.assertEqual(
            observed['record_args'],
            ('conv-memory-shadow', raw_traces, arbiter_decisions),
        )
        self.assertEqual(observed['enrich_called_with'], raw_traces)
        self.assertEqual(
            [entry['role'] for entry in observed['arbiter_recent_turns']],
            ['user', 'assistant'],
        )
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'raw_shadow_non_blocking')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 2)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 1)
        self.assertEqual(_event_payloads(events, 'memory_arbitrated')[0]['decisions'], 1)

    def test_prepare_memory_context_mode_enforced_all_uses_filtered_traces(self) -> None:
        events = []
        raw_traces = [{'trace_id': 'r1'}, {'trace_id': 'r2'}]
        filtered_traces = [{'trace_id': 'r2'}]

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
            enrich_traces_with_summaries=lambda traces: [{'trace_id': trace['trace_id'], 'enriched': True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda _traces, _recent_turns: (filtered_traces, [{'trace_id': 'r1', 'keep': False}]),
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
        self.assertEqual(memory_traces, [{'trace_id': 'r2', 'enriched': True}])
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
        raw_traces = [{'trace_id': 'r1'}, {'trace_id': 'r2'}]

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

        self.assertEqual(memory_traces, raw_traces)
        self.assertEqual(context_hints, [])
        self.assertTrue(chat_events)
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, 'arbiter')
        self.assertEqual(kwargs['status'], 'skipped')
        self.assertEqual(kwargs['reason_code'], 'mode_off')
        self.assertEqual(kwargs['payload']['raw_candidates'], 2)
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
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[1]['action'], 'persist_enforced')

    def test_record_identity_entries_for_mode_enforced_runs_mutable_rewriter_after_legacy_persist(self) -> None:
        events = []
        order: list[str] = []
        observed = {'rewrite_turns': None}
        original_refresh = chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [{'identity_id': 'id-1'}],
            rewrite_identity_mutables=lambda _payload: None,
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: order.append(
                f'persist:{conversation_id}:{len(list(entries))}'
            ),
            get_mutable_identity=lambda _subject: None,
            upsert_mutable_identity=lambda *_args, **_kwargs: None,
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def fake_refresh(recent_turns, **_kwargs):
            order.append('rewrite')
            observed['rewrite_turns'] = list(recent_turns)
            return {
                'status': 'ok',
                'reason_code': 'processed',
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

        chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = fake_refresh
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-enforced',
                [{'role': 'assistant', 'content': 'y'}],
                mode='enforced_all',
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = original_refresh

        self.assertEqual(order, ['persist:conv-identity-enforced:1', 'rewrite'])
        self.assertEqual(observed['rewrite_turns'], [{'role': 'assistant', 'content': 'y'}])
        rewrite_event = _event_payloads(events, 'identity_mutable_rewrite_apply')[0]
        self.assertEqual(rewrite_event['status'], 'ok')
        self.assertEqual(rewrite_event['reason_code'], 'processed')
        self.assertEqual(rewrite_event['outcomes'][0]['subject'], 'llm')
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[0]['action'], 'persist_enforced')

    def test_record_identity_entries_for_mode_enforced_keeps_fail_open_when_mutable_rewriter_raises(self) -> None:
        events = []
        observed = {'persisted': None}
        original_refresh = chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities

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
            raise RuntimeError('rewrite exploded')

        chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = boom
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-identity-enforced',
                [{'role': 'assistant', 'content': 'y'}],
                mode='enforced_all',
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = original_refresh

        self.assertEqual(observed['persisted'], ('conv-identity-enforced', [{'identity_id': 'id-1'}]))
        rewrite_event = _event_payloads(events, 'identity_mutable_rewrite_apply')[0]
        self.assertEqual(rewrite_event['status'], 'skipped')
        self.assertEqual(rewrite_event['reason_code'], 'rewriter_flow_error')
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[0]['action'], 'persist_enforced')

    def test_record_identity_entries_for_mode_does_not_pass_partial_read_overclaim_to_mutable_rewriter(self) -> None:
        events = []
        observed = {
            'persisted': None,
            'rewrite_turns': None,
        }
        original_refresh = chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities

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

        def fake_refresh(recent_turns, **_kwargs):
            observed['rewrite_turns'] = list(recent_turns)
            return {
                'status': 'ok',
                'reason_code': 'processed',
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

        chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = fake_refresh
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
            chat_memory_flow.memory_identity_mutable_rewriter.refresh_mutable_identities = original_refresh

        self.assertEqual(observed['persisted'], ('conv-identity-partial-guard', []))
        self.assertEqual(observed['rewrite_turns'], [{'role': 'user', 'content': 'Peux-tu le lire ?'}])
        rewrite_event = _event_payloads(events, 'identity_mutable_rewrite_apply')[0]
        self.assertEqual(rewrite_event['status'], 'ok')
        self.assertEqual(rewrite_event['reason_code'], 'processed')
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
        self.assertEqual(by_side['frida']['payload']['write_mode'], 'shadow')
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
        self.assertEqual(_event_payloads(events, 'identity_mode_apply')[0]['action'], 'record_evidence_shadow')

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
        self.assertEqual(event['action'], 'persist_enforced')
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
