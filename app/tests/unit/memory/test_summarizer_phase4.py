from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
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

    def test_summarize_conversation_logs_provider_metadata_and_uses_resumer_caller(self) -> None:
        observed = {'headers': None, 'provider_logs': []}
        original_post = summarizer.requests.post
        original_or_headers = summarizer.llm_client.or_headers
        original_log_provider_metadata = summarizer.llm_client.log_provider_metadata
        original_get_summary_system_prompt = summarizer.prompt_loader.get_summary_system_prompt

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {
                    'id': 'gen-summary',
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {'prompt_tokens': 21, 'completion_tokens': 9, 'total_tokens': 30},
                    'choices': [{'message': {'content': 'resume test'}}],
                }

        def fake_post(_url, *, json, headers, timeout):
            observed['headers'] = dict(headers)
            return FakeResponse()

        summarizer.requests.post = fake_post
        summarizer.llm_client.or_headers = lambda caller='llm': {'Authorization': f'caller={caller}'}
        summarizer.llm_client.log_provider_metadata = lambda _logger, event_name, provider_metadata: observed['provider_logs'].append(
            (event_name, dict(provider_metadata))
        )
        summarizer.prompt_loader.get_summary_system_prompt = lambda: 'SYSTEM SUMMARY'
        try:
            result = summarizer.summarize_conversation(
                [{'role': 'user', 'content': 'bonjour', 'timestamp': '2026-03-24T10:00:00Z'}],
                'openai/gpt-5.4-mini',
            )
        finally:
            summarizer.requests.post = original_post
            summarizer.llm_client.or_headers = original_or_headers
            summarizer.llm_client.log_provider_metadata = original_log_provider_metadata
            summarizer.prompt_loader.get_summary_system_prompt = original_get_summary_system_prompt

        self.assertEqual(result, 'resume test')
        self.assertEqual(observed['headers'], {'Authorization': 'caller=resumer'})
        self.assertEqual(
            observed['provider_logs'],
            [
                (
                    'summarizer_provider_response',
                    {
                        'provider_generation_id': 'gen-summary',
                        'provider_model': 'openai/gpt-5.4-mini',
                        'provider_prompt_tokens': 21,
                        'provider_completion_tokens': 9,
                        'provider_total_tokens': 30,
                    },
                )
            ],
        )


if __name__ == '__main__':
    unittest.main()
