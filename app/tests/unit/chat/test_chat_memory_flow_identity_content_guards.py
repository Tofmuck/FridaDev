import unittest
from types import SimpleNamespace
from unittest.mock import patch

from core import chat_memory_flow


class ChatMemoryFlowIdentityContentGuardsTests(unittest.TestCase):
    def _assert_no_legacy_write(self, *, web_input=None):
        pair = [{'role': 'user', 'content': 'SYNTHETIC_USER'}, {'role': 'assistant', 'content': 'SYNTHETIC_ASSISTANT'}]
        observed = {'pairs': [], 'legacy': 0, 'periodic': 0}
        arbiter = SimpleNamespace(
            extract_dialogic_context_hints=lambda turns: observed['pairs'].append(list(turns)) or {
                'status': 'not_selected', 'reason_code': 'dialogic_context_no_hint',
                'schema_version': 'dialogic_context_hint_v1',
                'prompt_kind': 'dialogic_context_hint_extractor_v1', 'hints': [],
            }
        )
        store = SimpleNamespace(
            record_dialogic_context_hints=lambda *_args: {'status': 'not_selected', 'reason_code': 'dialogic_context_no_hint', 'persisted_count': 0},
            persist_identity_entries=lambda *_args: observed.__setitem__('legacy', observed['legacy'] + 1),
            record_identity_evidence=lambda *_args: observed.__setitem__('legacy', observed['legacy'] + 1),
            add_identity=lambda *_args: observed.__setitem__('legacy', observed['legacy'] + 1),
        )
        with (
            patch.object(chat_memory_flow, '_run_periodic_identity_agent', side_effect=lambda *_args, **_kwargs: observed.__setitem__('periodic', observed['periodic'] + 1) or {}),
            patch.object(chat_memory_flow.chat_turn_logger, 'emit', return_value=True),
        ):
            chat_memory_flow.record_identity_entries_for_mode(
                'conv-synthetic', pair, mode='enforced_all', web_input=web_input,
                arbiter_module=arbiter, memory_store_module=store,
                admin_logs_module=SimpleNamespace(log_event=lambda *_args, **_kwargs: None),
            )
        self.assertEqual(observed['pairs'], [pair])
        self.assertEqual(observed['legacy'], 0)
        self.assertEqual(observed['periodic'], 1)

    def test_record_identity_entries_for_mode_filters_unsupported_web_reading_claim_in_enforced_mode(self):
        self._assert_no_legacy_write(web_input={'read_status': 'not_read'})

    def test_record_identity_entries_for_mode_filters_frida_pipeline_meta_identity_in_enforced_mode(self):
        self._assert_no_legacy_write()

    def test_record_identity_entries_for_mode_keeps_prudent_web_limitation_statement(self):
        self._assert_no_legacy_write(web_input={'read_status': 'partial'})

    def test_record_identity_entries_for_mode_keeps_supported_direct_reading_claim_when_page_read(self):
        self._assert_no_legacy_write(web_input={'read_status': 'read'})

    def test_record_identity_entries_for_mode_filters_overclaim_when_page_partially_read(self):
        self._assert_no_legacy_write(web_input={'read_status': 'partial'})

    def test_record_identity_entries_for_mode_accepts_explicit_user_identity_revelation(self):
        self._assert_no_legacy_write()


if __name__ == '__main__':
    unittest.main()
