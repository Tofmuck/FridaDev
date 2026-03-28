from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class ServerPhase13Tests(unittest.TestCase):
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

    def test_api_create_conversation_uses_backend_main_system_prompt_not_request_payload(self) -> None:
        observed = {}
        original_get_main_system_prompt = self.server.prompt_loader.get_main_system_prompt
        original_new_conversation = self.server.conv_store.new_conversation
        original_save_conversation = self.server.conv_store.save_conversation
        original_get_summary = self.server.conv_store.get_conversation_summary

        def fake_new_conversation(system_prompt: str, conversation_id=None, title: str = ""):
            observed['system_prompt'] = system_prompt
            observed['title'] = title
            return {
                'id': 'conv-phase13',
                'title': title,
                'created_at': '2026-03-26T00:00:00Z',
                'updated_at': '2026-03-26T00:00:00Z',
                'messages': [{'role': 'system', 'content': system_prompt, 'timestamp': '2026-03-26T00:00:00Z'}],
            }

        self.server.prompt_loader.get_main_system_prompt = lambda: 'BACKEND SYSTEM PROMPT'
        self.server.conv_store.new_conversation = fake_new_conversation
        self.server.conv_store.save_conversation = lambda *_args, **_kwargs: None
        self.server.conv_store.get_conversation_summary = lambda *_args, **_kwargs: None
        try:
            response = self.client.post(
                '/api/conversations',
                json={'title': 'Titre test', 'system': 'REQUEST SYSTEM PROMPT'},
            )
        finally:
            self.server.prompt_loader.get_main_system_prompt = original_get_main_system_prompt
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.save_conversation = original_save_conversation
            self.server.conv_store.get_conversation_summary = original_get_summary

        self.assertEqual(response.status_code, 201)
        self.assertEqual(observed['system_prompt'], 'BACKEND SYSTEM PROMPT')
        self.assertEqual(observed['title'], 'Titre test')

    def test_api_list_conversations_parses_query_params_with_contract_fallbacks(self) -> None:
        observed = {}
        original_list_conversations = self.server.conv_store.list_conversations

        def fake_list_conversations(limit: int, offset: int, include_deleted: bool):
            observed['limit'] = limit
            observed['offset'] = offset
            observed['include_deleted'] = include_deleted
            return {
                'items': [{'id': 'conv-phase4'}],
                'count': 1,
            }

        self.server.conv_store.list_conversations = fake_list_conversations
        try:
            response = self.client.get('/api/conversations?limit=oops&offset=bad&include_deleted=YeS')
        finally:
            self.server.conv_store.list_conversations = original_list_conversations

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(observed['limit'], 100)
        self.assertEqual(observed['offset'], 0)
        self.assertTrue(observed['include_deleted'])
        self.assertEqual(data['items'][0]['id'], 'conv-phase4')
        self.assertEqual(data['count'], 1)

    def test_api_get_conversation_messages_falls_back_to_runtime_summary_when_missing(self) -> None:
        observed = {}
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_read = self.server.conv_store.read_conversation
        original_get_summary = self.server.conv_store.get_conversation_summary

        self.server.conv_store.normalize_conversation_id = lambda _raw: 'conv-phase4'
        self.server.conv_store.read_conversation = lambda conv_id, _system_prompt: {
            'id': conv_id,
            'title': '',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:05:00Z',
            'messages': [
                {'role': 'system', 'content': 'system'},
                {'role': 'user', 'content': 'hello'},
                {'role': 'assistant', 'content': 'world'},
            ],
        }

        def fake_get_conversation_summary(conv_id: str, *, include_deleted: bool = False):
            observed['conv_id'] = conv_id
            observed['include_deleted'] = include_deleted
            return None

        self.server.conv_store.get_conversation_summary = fake_get_conversation_summary
        try:
            response = self.client.get('/api/conversations/conv-phase4/messages')
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.read_conversation = original_read
            self.server.conv_store.get_conversation_summary = original_get_summary

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['conversation_id'], 'conv-phase4')
        self.assertEqual(data['title'], 'Nouvelle conversation')
        self.assertEqual(data['created_at'], '2026-03-26T00:00:00Z')
        self.assertEqual(data['updated_at'], '2026-03-26T00:05:00Z')
        self.assertIsNone(data['deleted_at'])
        self.assertEqual(len(data['messages']), 3)
        self.assertEqual(observed['conv_id'], 'conv-phase4')
        self.assertTrue(observed['include_deleted'])

    def test_api_patch_conversation_returns_400_on_empty_title(self) -> None:
        observed = {'rename_called': False}
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_rename = self.server.conv_store.rename_conversation

        self.server.conv_store.normalize_conversation_id = lambda _raw: 'conv-phase4'

        def fake_rename_conversation(_conv_id: str, _title: str):
            observed['rename_called'] = True
            return {'id': 'conv-phase4', 'title': 'should-not-be-used'}

        self.server.conv_store.rename_conversation = fake_rename_conversation
        try:
            response = self.client.patch('/api/conversations/conv-phase4', json={'title': '   '})
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.rename_conversation = original_rename

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'title requis')
        self.assertFalse(observed['rename_called'])

    def test_api_delete_conversation_returns_400_on_invalid_conversation_id(self) -> None:
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_soft_delete = self.server.conv_store.soft_delete_conversation

        self.server.conv_store.normalize_conversation_id = lambda _raw: None
        self.server.conv_store.soft_delete_conversation = lambda _conv_id: True
        try:
            response = self.client.delete('/api/conversations/@@bad@@')
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.soft_delete_conversation = original_soft_delete

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'conversation_id invalide')

    def test_api_delete_conversation_returns_404_when_not_found(self) -> None:
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_soft_delete = self.server.conv_store.soft_delete_conversation

        self.server.conv_store.normalize_conversation_id = lambda _raw: 'conv-phase13'
        self.server.conv_store.soft_delete_conversation = lambda _conv_id: False
        try:
            response = self.client.delete('/api/conversations/conv-phase13')
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.soft_delete_conversation = original_soft_delete

        self.assertEqual(response.status_code, 404)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'conversation introuvable')

    def test_api_chat_ignores_request_system_and_uses_backend_main_system_prompt(self) -> None:
        observed = {}
        original_get_main_system_prompt = self.server.prompt_loader.get_main_system_prompt
        original_get_main_hermeneutical_prompt = self.server.prompt_loader.get_main_hermeneutical_prompt
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
        original_build_augmented_system = self.server.chat_service.chat_prompt_context.build_augmented_system

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "reponse test"}}]}

        def fake_get_main_model_settings():
            return self.server.runtime_settings.RuntimeSectionView(
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

        def fake_new_conversation(system_prompt: str):
            observed['system_prompt'] = system_prompt
            return {
                "id": "conv-phase13",
                "created_at": "2026-03-26T00:00:00Z",
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                        "timestamp": "2026-03-26T00:00:00Z",
                    }
                ],
            }

        def fake_build_augmented_system(*, system_prompt, hermeneutical_prompt, config_module, identity_module, now_iso):
            observed['turn_now_reference'] = now_iso
            return original_build_augmented_system(
                system_prompt=system_prompt,
                hermeneutical_prompt=hermeneutical_prompt,
                config_module=config_module,
                identity_module=identity_module,
                now_iso=now_iso,
            )

        def fake_build_prompt_messages(conversation_arg, *_args, **_kwargs):
            observed['augmented_system'] = conversation_arg["messages"][0]["content"]
            observed['turn_now_delta'] = _kwargs.get('now')
            return [{"role": "user", "content": "Bonjour"}]

        self.server.prompt_loader.get_main_system_prompt = lambda: 'BACKEND SYSTEM PROMPT'
        self.server.prompt_loader.get_main_hermeneutical_prompt = lambda: 'BACKEND HERMENEUTICAL PROMPT'
        self.server.runtime_settings.get_main_model_settings = fake_get_main_model_settings
        self.server.runtime_settings.get_runtime_secret_value = lambda *args, **kwargs: self.server.runtime_settings.RuntimeSecretValue(
            section='main_model',
            field='api_key',
            value='sk-phase13',
            source='db_encrypted',
            source_reason='db_row',
        )
        self.server.conv_store.new_conversation = fake_new_conversation
        self.server.conv_store.save_conversation = lambda *_args, **_kwargs: None
        self.server.conv_store.append_message = (
            lambda conv, role, content, timestamp=None: conv["messages"].append(
                {"role": role, "content": content, "timestamp": timestamp}
            )
        )
        self.server.chat_service.chat_prompt_context.build_augmented_system = fake_build_augmented_system
        self.server.conv_store.conversation_path = lambda _id: 'conv/conv-phase13.json'
        self.server.conv_store.build_prompt_messages = fake_build_prompt_messages
        self.server.memory_store.decay_identities = lambda: None
        self.server.summarizer.maybe_summarize = lambda *args, **kwargs: False
        self.server.identity.build_identity_block = lambda: ("[IDENTITÉ DU MODÈLE]\\nbloc identite", [])
        self.server.memory_store.retrieve = lambda *_args, **_kwargs: []
        self.server.memory_store.get_recent_context_hints = lambda **_kwargs: []
        self.server.admin_logs.log_event = lambda *args, **kwargs: None
        self.server.llm.or_headers = lambda **_kwargs: {}
        self.server.llm.build_payload = lambda *_args, **_kwargs: {
            'model': 'openrouter/runtime-main-model',
            'messages': [],
            'max_tokens': 2048,
            'stream': False,
        }
        self.server.requests.post = lambda *args, **kwargs: FakeResponse()
        self.server.token_utils.count_tokens = lambda *_args, **_kwargs: 1
        self.server.memory_store.save_new_traces = lambda *_args, **_kwargs: None
        self.server.chat_service._record_identity_entries_for_mode = lambda *_args, **_kwargs: None
        self.server.memory_store.reactivate_identities = lambda *_args, **_kwargs: None
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'system': 'REQUEST SYSTEM PROMPT'},
            )
        finally:
            self.server.prompt_loader.get_main_system_prompt = original_get_main_system_prompt
            self.server.prompt_loader.get_main_hermeneutical_prompt = original_get_main_hermeneutical_prompt
            self.server.runtime_settings.get_main_model_settings = original_get_main
            self.server.runtime_settings.get_runtime_secret_value = original_get_secret
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.save_conversation = original_save_conversation
            self.server.conv_store.append_message = original_append_message
            self.server.chat_service.chat_prompt_context.build_augmented_system = original_build_augmented_system
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
        self.assertEqual(observed['system_prompt'], 'BACKEND SYSTEM PROMPT')
        self.assertIn('BACKEND SYSTEM PROMPT', observed['augmented_system'])
        self.assertIn('BACKEND HERMENEUTICAL PROMPT', observed['augmented_system'])
        self.assertIn('[RÉFÉRENCE TEMPORELLE]', observed['augmented_system'])
        self.assertIn('[IDENTITÉ DU MODÈLE]', observed['augmented_system'])
        self.assertLess(
            observed['augmented_system'].index('BACKEND SYSTEM PROMPT'),
            observed['augmented_system'].index('BACKEND HERMENEUTICAL PROMPT'),
        )
        self.assertLess(
            observed['augmented_system'].index('BACKEND HERMENEUTICAL PROMPT'),
            observed['augmented_system'].index('[RÉFÉRENCE TEMPORELLE]'),
        )
        self.assertEqual(observed['turn_now_reference'], observed['turn_now_delta'])
