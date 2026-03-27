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

        mode, memory_traces, context_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg='bonjour',
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(mode, 'off')
        self.assertEqual(memory_traces, [{'trace_id': 'r1', 'enriched': True}])
        self.assertEqual(context_hints, [])
        self.assertEqual(observed['record_calls'], 0)
        self.assertEqual(observed['enrich_called_with'], raw_traces)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['source'], 'raw_mode_off')
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['selected'], 1)
        self.assertEqual(_event_payloads(events, 'memory_mode_apply')[0]['filtered'], 0)
        self.assertEqual(_event_payloads(events, 'memory_arbitrated'), [])

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


if __name__ == '__main__':
    unittest.main()
