import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import chat_memory_flow


def _result(hints=None, status='ok', reason='dialogic_context_hints_extracted'):
    return {
        'status': status,
        'reason_code': reason,
        'schema_version': 'dialogic_context_hint_v1',
        'prompt_kind': 'dialogic_context_hint_extractor_v1',
        'hints': list(hints or []),
    }


class ChatMemoryFlowIdentityModePipelineTests(unittest.TestCase):
    def _run(self, pair, *, mode='enforced_all', result=None):
        observed = {'context_pairs': [], 'persisted': [], 'periodic_pairs': [], 'legacy_writes': 0}
        arbiter = SimpleNamespace(
            extract_dialogic_context_hints=lambda turns: observed['context_pairs'].append([dict(t) for t in turns]) or (result or _result())
        )
        store = SimpleNamespace(
            record_dialogic_context_hints=lambda cid, hints: observed['persisted'].append((cid, list(hints))) or {
                'status': 'ok', 'reason_code': 'dialogic_context_hints_persisted', 'persisted_count': len(hints),
            },
            persist_identity_entries=lambda *_args: observed.__setitem__('legacy_writes', observed['legacy_writes'] + 1),
            record_identity_evidence=lambda *_args: observed.__setitem__('legacy_writes', observed['legacy_writes'] + 1),
            add_identity=lambda *_args: observed.__setitem__('legacy_writes', observed['legacy_writes'] + 1),
        )

        def periodic(_cid, turns, **_kwargs):
            observed['periodic_pairs'].append([dict(t) for t in turns])
            return {}

        with (
            patch.object(chat_memory_flow, '_run_periodic_identity_agent', side_effect=periodic),
            patch.object(chat_memory_flow.chat_turn_logger, 'emit', return_value=True),
        ):
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-synthetic', pair, mode=mode, arbiter_module=arbiter,
                memory_store_module=store,
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            )
        return observed

    def test_presence_projects_only_marked_assistant_out_of_identity_sources(self):
        pair = [
            {'role': 'user', 'content': 'SYNTHETIC_USER'},
            {'role': 'assistant', 'content': '...', 'meta': {'assistant_turn': {'status': 'dialogic_presence'}}},
        ]
        observed = self._run(pair)
        self.assertEqual(observed['context_pairs'][0], pair)
        self.assertEqual(observed['periodic_pairs'][0][1]['content'], '')

    def test_unmarked_dot_messages_remain_identity_sources(self):
        pair = [{'role': 'user', 'content': '...'}, {'role': 'assistant', 'content': '...'}]
        observed = self._run(pair)
        self.assertEqual(observed['context_pairs'][0], pair)
        self.assertEqual(observed['periodic_pairs'][0], pair)

    def test_presence_meta_on_user_input_cannot_project_user_content_out(self):
        pair = [
            {'role': 'user', 'content': 'SYNTHETIC_USER', 'metadata': {'provenance': 'dialogic_presence'}},
            {'role': 'assistant', 'content': 'SYNTHETIC_ASSISTANT'},
        ]
        observed = self._run(pair)
        self.assertEqual(observed['context_pairs'][0], pair)
        self.assertEqual(observed['periodic_pairs'][0], pair)

    def test_record_identity_entries_for_mode_handles_off_and_enforced(self):
        pair = [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}]
        off = self._run(pair, mode='off')
        enforced = self._run(pair)
        self.assertEqual(off['context_pairs'], [])
        self.assertEqual(len(enforced['context_pairs']), 1)
        self.assertEqual(len(enforced['periodic_pairs']), 1)

    def test_record_identity_entries_for_mode_enforced_runs_periodic_identity_staging_after_legacy_persist(self):
        hint = {'subject': 'dialogue', 'content': 'H', 'confidence': 0.9, 'reason_code': 'active_question'}
        observed = self._run([{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}], result=_result([hint]))
        self.assertEqual(len(observed['persisted']), 1)
        self.assertEqual(observed['legacy_writes'], 0)
        self.assertEqual(len(observed['periodic_pairs']), 1)

    def test_record_identity_entries_for_mode_enforced_keeps_fail_open_when_periodic_agent_raises(self):
        events = []
        arbiter = SimpleNamespace(extract_dialogic_context_hints=lambda _turns: _result(status='not_selected'))
        store = SimpleNamespace(record_dialogic_context_hints=lambda *_args: self.fail('no hint must not persist'))
        with (
            patch.object(
                chat_memory_flow.memory_identity_periodic_agent,
                'stage_identity_turn_pair',
                side_effect=RuntimeError('synthetic-periodic-failure'),
            ),
            patch.object(chat_memory_flow.chat_turn_logger, 'emit', return_value=True),
        ):
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-synthetic',
                [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}],
                mode='enforced_all',
                arbiter_module=arbiter,
                memory_store_module=store,
                admin_logs_module=SimpleNamespace(log_event=lambda event, **fields: events.append((event, fields))),
            )
        judge_events = [fields for event, fields in events if event == 'mutable_identity_judge_apply']
        self.assertEqual(len(judge_events), 1)
        self.assertEqual(judge_events[0]['status'], 'skipped')
        self.assertEqual(judge_events[0]['reason_code'], 'mutable_judge_flow_error')

    def test_record_identity_entries_for_mode_passes_complete_pair_to_identity_buffer_after_guarding_diagnostics(self):
        pair = [{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}]
        observed = self._run(pair)
        self.assertEqual(observed['periodic_pairs'], [pair])
        self.assertEqual(observed['legacy_writes'], 0)

    def test_record_identity_entries_for_mode_shadow_emits_skipped_identity_write_per_side(self):
        observed = self._run([{'role': 'user', 'content': 'U'}, {'role': 'assistant', 'content': 'A'}], mode='shadow')
        self.assertEqual(len(observed['context_pairs']), 1)
        self.assertEqual(observed['legacy_writes'], 0)
        self.assertEqual(len(observed['periodic_pairs']), 1)


if __name__ == '__main__':
    unittest.main()
