from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import conv_store
from memory import memory_store


class ServerPhase12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        original_init_db = memory_store.init_db
        original_init_catalog_db = conv_store.init_catalog_db
        original_init_messages_db = conv_store.init_messages_db
        sys.modules.pop('server', None)
        memory_store.init_db = lambda: None
        conv_store.init_catalog_db = lambda: None
        conv_store.init_messages_db = lambda: None
        try:
            cls.server = importlib.import_module('server')
        finally:
            memory_store.init_db = original_init_db
            conv_store.init_catalog_db = original_init_catalog_db
            conv_store.init_messages_db = original_init_messages_db

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_api_chat_uses_runtime_response_max_tokens_when_request_override_is_absent(self) -> None:
        observed = {'prompt_message_contents': []}
        original_get_main = self.server.runtime_settings.get_main_model_settings
        original_get_secret = self.server.runtime_settings.get_runtime_secret_value
        original_new_conversation = self.server.conv_store.new_conversation
        original_save_conversation = self.server.conv_store.save_conversation
        original_append_message = self.server.conv_store.append_message
        original_conversation_path = self.server.conv_store.conversation_path
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        original_decay_identities = self.server.memory_store.decay_identities
        original_maybe_summarize = self.server.summarizer.maybe_summarize
        original_build_identity_block = self.server.identity.build_identity_block
        original_retrieve = self.server.memory_store.retrieve
        original_get_recent_context_hints = self.server.memory_store.get_recent_context_hints
        original_log_event = self.server.admin_logs.log_event
        original_or_headers = self.server.llm.or_headers
        original_build_payload = self.server.llm.build_payload
        original_requests_post = self.server.requests.post
        original_count_tokens = self.server.token_utils.count_tokens
        original_save_new_traces = self.server.memory_store.save_new_traces
        original_record_identity = self.server.chat_service._record_identity_entries_for_mode
        original_reactivate = self.server.memory_store.reactivate_identities

        conversation = {"id": "conv-phase12", "created_at": "2026-03-25T00:00:00Z", "messages": []}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "reponse test"}}]}

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload={
                    'model': {'value': 'openrouter/runtime-main-model', 'origin': 'db'},
                    'temperature': {'value': 0.4, 'origin': 'db'},
                    'top_p': {'value': 1.0, 'origin': 'db'},
                    'response_max_tokens': {'value': 2048, 'origin': 'db_seed'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['max_tokens'] = max_tokens
            observed['stream'] = stream
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': [],
                'max_tokens': max_tokens,
                'stream': stream,
            }

        self.server.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        self.server.runtime_settings.get_runtime_secret_value = lambda *args, **kwargs: runtime_settings.RuntimeSecretValue(
            section='main_model',
            field='api_key',
            value='sk-phase12',
            source='db_encrypted',
            source_reason='db_row',
        )
        self.server.conv_store.new_conversation = lambda _system: conversation
        self.server.conv_store.save_conversation = lambda *args, **kwargs: None
        self.server.conv_store.append_message = (
            lambda conv, role, content, timestamp=None: conv["messages"].append(
                {"role": role, "content": content, "timestamp": timestamp}
            )
        )
        self.server.conv_store.conversation_path = lambda _id: 'conv/conv-phase12.json'
        def fake_build_prompt_messages(conversation_arg, *_args, **_kwargs):
            observed['prompt_message_contents'].append(
                [str(m.get('content') or '') for m in conversation_arg.get('messages', [])]
            )
            return [{"role": "user", "content": "Bonjour"}]

        self.server.conv_store.build_prompt_messages = fake_build_prompt_messages
        self.server.memory_store.decay_identities = lambda: None
        self.server.summarizer.maybe_summarize = lambda *args, **kwargs: False
        self.server.identity.build_identity_block = lambda: ("", [])
        self.server.memory_store.retrieve = lambda *_args, **_kwargs: []
        self.server.memory_store.get_recent_context_hints = lambda **_kwargs: []
        self.server.admin_logs.log_event = lambda *args, **kwargs: None
        self.server.llm.or_headers = lambda **_kwargs: {}
        self.server.llm.build_payload = fake_build_payload
        self.server.requests.post = lambda *args, **kwargs: FakeResponse()
        self.server.token_utils.count_tokens = lambda *_args, **_kwargs: 1
        self.server.memory_store.save_new_traces = lambda *_args, **_kwargs: None
        self.server.chat_service._record_identity_entries_for_mode = lambda *_args, **_kwargs: None
        self.server.memory_store.reactivate_identities = lambda *_args, **_kwargs: None
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
            legacy_response = self.client.post(
                '/api/chat',
                json={
                    'message': 'Bonjour legacy',
                    'history': [{'role': 'user', 'content': 'LEGACY_HISTORY_SHOULD_BE_IGNORED'}],
                },
            )
        finally:
            self.server.runtime_settings.get_main_model_settings = original_get_main
            self.server.runtime_settings.get_runtime_secret_value = original_get_secret
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.save_conversation = original_save_conversation
            self.server.conv_store.append_message = original_append_message
            self.server.conv_store.conversation_path = original_conversation_path
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            self.server.memory_store.decay_identities = original_decay_identities
            self.server.summarizer.maybe_summarize = original_maybe_summarize
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.retrieve = original_retrieve
            self.server.memory_store.get_recent_context_hints = original_get_recent_context_hints
            self.server.admin_logs.log_event = original_log_event
            self.server.llm.or_headers = original_or_headers
            self.server.llm.build_payload = original_build_payload
            self.server.requests.post = original_requests_post
            self.server.token_utils.count_tokens = original_count_tokens
            self.server.memory_store.save_new_traces = original_save_new_traces
            self.server.chat_service._record_identity_entries_for_mode = original_record_identity
            self.server.memory_store.reactivate_identities = original_reactivate

        self.assertEqual(response.status_code, 200)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(observed['max_tokens'], 2048)
        self.assertFalse(observed['stream'])
        self.assertTrue(observed['prompt_message_contents'])
        for prompt_contents in observed['prompt_message_contents']:
            self.assertNotIn('LEGACY_HISTORY_SHOULD_BE_IGNORED', '\n'.join(prompt_contents))

    def test_api_chat_keeps_request_max_tokens_override_over_runtime_default(self) -> None:
        observed = {}
        original_get_main = self.server.runtime_settings.get_main_model_settings
        original_get_secret = self.server.runtime_settings.get_runtime_secret_value
        original_new_conversation = self.server.conv_store.new_conversation
        original_save_conversation = self.server.conv_store.save_conversation
        original_append_message = self.server.conv_store.append_message
        original_conversation_path = self.server.conv_store.conversation_path
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        original_decay_identities = self.server.memory_store.decay_identities
        original_maybe_summarize = self.server.summarizer.maybe_summarize
        original_build_identity_block = self.server.identity.build_identity_block
        original_retrieve = self.server.memory_store.retrieve
        original_get_recent_context_hints = self.server.memory_store.get_recent_context_hints
        original_log_event = self.server.admin_logs.log_event
        original_or_headers = self.server.llm.or_headers
        original_build_payload = self.server.llm.build_payload
        original_requests_post = self.server.requests.post
        original_count_tokens = self.server.token_utils.count_tokens
        original_save_new_traces = self.server.memory_store.save_new_traces
        original_record_identity = self.server.chat_service._record_identity_entries_for_mode
        original_reactivate = self.server.memory_store.reactivate_identities

        conversation = {"id": "conv-phase12", "created_at": "2026-03-25T00:00:00Z", "messages": []}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "reponse test"}}]}

        def fake_get_main_model_settings():
            return runtime_settings.RuntimeSectionView(
                section='main_model',
                payload={
                    'model': {'value': 'openrouter/runtime-main-model', 'origin': 'db'},
                    'temperature': {'value': 0.4, 'origin': 'db'},
                    'top_p': {'value': 1.0, 'origin': 'db'},
                    'response_max_tokens': {'value': 2048, 'origin': 'db_seed'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['max_tokens'] = max_tokens
            observed['stream'] = stream
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': [],
                'max_tokens': max_tokens,
                'stream': stream,
            }

        self.server.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        self.server.runtime_settings.get_runtime_secret_value = lambda *args, **kwargs: runtime_settings.RuntimeSecretValue(
            section='main_model',
            field='api_key',
            value='sk-phase12',
            source='db_encrypted',
            source_reason='db_row',
        )
        self.server.conv_store.new_conversation = lambda _system: conversation
        self.server.conv_store.save_conversation = lambda *args, **kwargs: None
        self.server.conv_store.append_message = (
            lambda conv, role, content, timestamp=None: conv["messages"].append(
                {"role": role, "content": content, "timestamp": timestamp}
            )
        )
        self.server.conv_store.conversation_path = lambda _id: 'conv/conv-phase12.json'
        self.server.conv_store.build_prompt_messages = lambda *args, **kwargs: [{"role": "user", "content": "Bonjour"}]
        self.server.memory_store.decay_identities = lambda: None
        self.server.summarizer.maybe_summarize = lambda *args, **kwargs: False
        self.server.identity.build_identity_block = lambda: ("", [])
        self.server.memory_store.retrieve = lambda *_args, **_kwargs: []
        self.server.memory_store.get_recent_context_hints = lambda **_kwargs: []
        self.server.admin_logs.log_event = lambda *args, **kwargs: None
        self.server.llm.or_headers = lambda **_kwargs: {}
        self.server.llm.build_payload = fake_build_payload
        self.server.requests.post = lambda *args, **kwargs: FakeResponse()
        self.server.token_utils.count_tokens = lambda *_args, **_kwargs: 1
        self.server.memory_store.save_new_traces = lambda *_args, **_kwargs: None
        self.server.chat_service._record_identity_entries_for_mode = lambda *_args, **_kwargs: None
        self.server.memory_store.reactivate_identities = lambda *_args, **_kwargs: None
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'max_tokens': 512})
        finally:
            self.server.runtime_settings.get_main_model_settings = original_get_main
            self.server.runtime_settings.get_runtime_secret_value = original_get_secret
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.save_conversation = original_save_conversation
            self.server.conv_store.append_message = original_append_message
            self.server.conv_store.conversation_path = original_conversation_path
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            self.server.memory_store.decay_identities = original_decay_identities
            self.server.summarizer.maybe_summarize = original_maybe_summarize
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.retrieve = original_retrieve
            self.server.memory_store.get_recent_context_hints = original_get_recent_context_hints
            self.server.admin_logs.log_event = original_log_event
            self.server.llm.or_headers = original_or_headers
            self.server.llm.build_payload = original_build_payload
            self.server.requests.post = original_requests_post
            self.server.token_utils.count_tokens = original_count_tokens
            self.server.memory_store.save_new_traces = original_save_new_traces
            self.server.chat_service._record_identity_entries_for_mode = original_record_identity
            self.server.memory_store.reactivate_identities = original_reactivate

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['max_tokens'], 512)
        self.assertFalse(observed['stream'])


if __name__ == '__main__':
    unittest.main()
