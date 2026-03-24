from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from memory import summarizer
import config


class SummarizerPhase4ModelTests(unittest.TestCase):
    def setUp(self) -> None:
        runtime_settings.invalidate_runtime_settings_cache()

    def _conversation(self):
        return {
            'id': 'conv-test',
            'messages': [
                {'role': 'user', 'content': 'message un ' * 120, 'timestamp': '2026-03-24T10:00:00Z'},
                {'role': 'assistant', 'content': 'reponse un ' * 120, 'timestamp': '2026-03-24T10:01:00Z'},
                {'role': 'user', 'content': 'message deux ' * 120, 'timestamp': '2026-03-24T10:02:00Z'},
                {'role': 'assistant', 'content': 'reponse deux ' * 120, 'timestamp': '2026-03-24T10:03:00Z'},
            ],
        }

    def test_maybe_summarize_uses_runtime_summary_model_from_db_when_present(self) -> None:
        observed = {'model': None}
        original_get_settings = summarizer.runtime_settings.get_summary_model_settings
        original_summarize_conversation = summarizer.summarize_conversation
        original_save_summary = None
        original_update_summary_id = None
        original_threshold = config.SUMMARY_THRESHOLD_TOKENS
        original_keep_turns = config.SUMMARY_KEEP_TURNS

        def fake_get_summary_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='summary_model',
                payload=runtime_settings.normalize_stored_payload(
                    'summary_model',
                    {
                        'model': {'value': 'openai/gpt-5.4-mini', 'origin': 'db'},
                        'temperature': {'value': 0.3, 'origin': 'db'},
                        'top_p': {'value': 1.0, 'origin': 'db'},
                    },
                ),
                source='db',
                source_reason='db_row',
            )

        def fake_summarize_conversation(turns, model):
            observed['model'] = model
            return 'resume test'

        import memory.memory_store as memory_store
        original_save_summary = memory_store.save_summary
        original_update_summary_id = memory_store.update_traces_summary_id
        memory_store.save_summary = lambda conv_id, summary_entry: None
        memory_store.update_traces_summary_id = lambda conv_id, summary_id, start_ts, end_ts: None
        config.SUMMARY_THRESHOLD_TOKENS = 1
        config.SUMMARY_KEEP_TURNS = 1
        summarizer.runtime_settings.get_summary_model_settings = fake_get_summary_model_settings
        summarizer.summarize_conversation = fake_summarize_conversation
        try:
            changed = summarizer.maybe_summarize(self._conversation(), 'token-model')
        finally:
            summarizer.runtime_settings.get_summary_model_settings = original_get_settings
            summarizer.summarize_conversation = original_summarize_conversation
            memory_store.save_summary = original_save_summary
            memory_store.update_traces_summary_id = original_update_summary_id
            config.SUMMARY_THRESHOLD_TOKENS = original_threshold
            config.SUMMARY_KEEP_TURNS = original_keep_turns

        self.assertTrue(changed)
        self.assertEqual(observed['model'], 'openai/gpt-5.4-mini')

    def test_maybe_summarize_keeps_env_fallback_when_db_row_is_missing(self) -> None:
        observed = {'model': None}
        original_get_settings = summarizer.runtime_settings.get_summary_model_settings
        original_summarize_conversation = summarizer.summarize_conversation
        original_save_summary = None
        original_update_summary_id = None
        original_threshold = config.SUMMARY_THRESHOLD_TOKENS
        original_keep_turns = config.SUMMARY_KEEP_TURNS

        def fake_get_summary_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='summary_model',
                payload=runtime_settings.build_env_seed_bundle('summary_model').payload,
                source='env',
                source_reason='empty_table',
            )

        def fake_summarize_conversation(turns, model):
            observed['model'] = model
            return 'resume fallback'

        import memory.memory_store as memory_store
        original_save_summary = memory_store.save_summary
        original_update_summary_id = memory_store.update_traces_summary_id
        memory_store.save_summary = lambda conv_id, summary_entry: None
        memory_store.update_traces_summary_id = lambda conv_id, summary_id, start_ts, end_ts: None
        config.SUMMARY_THRESHOLD_TOKENS = 1
        config.SUMMARY_KEEP_TURNS = 1
        summarizer.runtime_settings.get_summary_model_settings = fake_get_summary_model_settings
        summarizer.summarize_conversation = fake_summarize_conversation
        try:
            changed = summarizer.maybe_summarize(self._conversation(), 'token-model')
        finally:
            summarizer.runtime_settings.get_summary_model_settings = original_get_settings
            summarizer.summarize_conversation = original_summarize_conversation
            memory_store.save_summary = original_save_summary
            memory_store.update_traces_summary_id = original_update_summary_id
            config.SUMMARY_THRESHOLD_TOKENS = original_threshold
            config.SUMMARY_KEEP_TURNS = original_keep_turns

        self.assertTrue(changed)
        self.assertEqual(observed['model'], config.SUMMARY_MODEL)


if __name__ == '__main__':
    unittest.main()
