from __future__ import annotations

import importlib
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
from core import conv_store
from memory import memory_store


class _FakeResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {"choices": [{"message": {"content": "reponse test"}}]}


class ChatInputModeRouteTests(unittest.TestCase):
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

    def _patch_chat_runtime(self, *, conversation: dict[str, object]):
        originals = []
        observed = {'save_calls': [], 'payload_messages': []}

        def patch_attr(obj, name, value):
            originals.append((obj, name, getattr(obj, name)))
            setattr(obj, name, value)

        patch_attr(self.server.prompt_loader, 'get_main_system_prompt', lambda: 'BACKEND SYSTEM PROMPT')
        patch_attr(
            self.server.prompt_loader,
            'get_main_hermeneutical_prompt',
            lambda: 'BACKEND HERMENEUTICAL PROMPT',
        )
        patch_attr(
            self.server.runtime_settings,
            'get_main_model_settings',
            lambda: runtime_settings.RuntimeSectionView(
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
            ),
        )
        patch_attr(
            self.server.runtime_settings,
            'get_runtime_secret_value',
            lambda *args, **kwargs: runtime_settings.RuntimeSecretValue(
                section='main_model',
                field='api_key',
                value='sk-input-mode',
                source='db_encrypted',
                source_reason='db_row',
            ),
        )

        def normalize_conversation_id(raw):
            value = str(raw or '').strip()
            if value == 'conv-input-mode':
                return value
            return None

        def append_message(conv, role, content, meta=None, timestamp=None):
            message = {'role': role, 'content': content, 'timestamp': timestamp}
            if meta is not None:
                message['meta'] = meta
            conv['messages'].append(message)

        def save_conversation(*_args, **kwargs):
            observed['save_calls'].append({'kwargs': dict(kwargs)})

        patch_attr(self.server.conv_store, 'normalize_conversation_id', normalize_conversation_id)
        patch_attr(self.server.conv_store, 'load_conversation', lambda *_args, **_kwargs: conversation)
        patch_attr(self.server.conv_store, 'read_conversation', lambda *_args, **_kwargs: conversation)
        patch_attr(self.server.conv_store, 'new_conversation', lambda _system: conversation)
        patch_attr(self.server.conv_store, 'save_conversation', save_conversation)
        patch_attr(self.server.conv_store, 'append_message', append_message)
        patch_attr(self.server.conv_store, 'conversation_path', lambda _id: 'conv/conv-input-mode.json')
        patch_attr(
            self.server.conv_store,
            'build_prompt_messages',
            lambda conv, *_args, **_kwargs: [
                {
                    'role': str(message.get('role') or ''),
                    'content': str(message.get('content') or ''),
                }
                for message in conv.get('messages', [])
                if str(message.get('role') or '').strip() in {'system', 'user', 'assistant'}
            ],
        )
        patch_attr(
            self.server.conv_store,
            'get_conversation_summary',
            lambda *_args, **_kwargs: {
                'id': 'conv-input-mode',
                'title': 'Conversation input mode',
                'created_at': conversation['created_at'],
                'updated_at': conversation.get('updated_at'),
                'message_count': sum(
                    1
                    for msg in conversation.get('messages', [])
                    if str(msg.get('role') or '').strip() in {'user', 'assistant'}
                ),
                'last_message_preview': '',
                'deleted_at': None,
            },
        )
        patch_attr(self.server.memory_store, 'decay_identities', lambda: None)
        patch_attr(self.server.summarizer, 'maybe_summarize', lambda *args, **kwargs: False)
        patch_attr(self.server.identity, 'build_identity_block', lambda: ('', []))
        patch_attr(
            self.server.identity,
            'build_identity_input',
            lambda: {
                'schema_version': 'v2',
                'frida': {'static': {'content': '', 'source': None}, 'mutable': {'content': '', 'source_trace_id': None, 'updated_by': None, 'update_reason': None, 'updated_ts': None}},
                'user': {'static': {'content': '', 'source': None}, 'mutable': {'content': '', 'source_trace_id': None, 'updated_by': None, 'update_reason': None, 'updated_ts': None}},
            },
        )
        patch_attr(self.server.memory_store, 'retrieve', lambda *_args, **_kwargs: [])
        patch_attr(self.server.memory_store, 'get_recent_context_hints', lambda **_kwargs: [])
        patch_attr(self.server.memory_store, 'save_new_traces', lambda *_args, **_kwargs: None)
        patch_attr(self.server.memory_store, 'reactivate_identities', lambda *_args, **_kwargs: None)
        patch_attr(self.server.admin_logs, 'log_event', lambda *args, **kwargs: None)
        patch_attr(self.server.llm, 'or_headers', lambda **_kwargs: {})
        def build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['payload_messages'] = [dict(message) for message in _messages]
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': list(_messages),
                'max_tokens': max_tokens,
                'stream': stream,
            }

        patch_attr(self.server.llm, 'build_payload', build_payload)
        patch_attr(self.server.requests, 'post', lambda *args, **kwargs: _FakeResponse())
        patch_attr(self.server.token_utils, 'count_tokens', lambda *_args, **_kwargs: 1)
        patch_attr(self.server.token_utils, 'estimate_tokens', lambda *_args, **_kwargs: 1)
        patch_attr(self.server.chat_service, '_record_identity_entries_for_mode', lambda *_args, **_kwargs: None)
        patch_attr(
            self.server.chat_service.stimmung_agent,
            'build_affective_turn_signal',
            lambda **_kwargs: self.server.chat_service.stimmung_agent.StimmungAgentResult(
                signal={
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [{'tone': 'neutralite', 'strength': 3}],
                    'dominant_tone': 'neutralite',
                    'confidence': 0.55,
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            ),
        )

        def restore():
            while originals:
                obj, name, value = originals.pop()
                setattr(obj, name, value)

        return observed, restore

    def test_api_chat_persists_voice_input_mode_in_user_message_meta(self) -> None:
        conversation = {
            'id': 'conv-input-mode',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed, restore = self._patch_chat_runtime(conversation=conversation)
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'input_mode': 'voice'},
            )
            messages_response = self.client.get('/api/conversations/conv-input-mode/messages')
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertGreaterEqual(len(observed['save_calls']), 1)
        self.assertEqual(conversation['messages'][1]['role'], 'user')
        self.assertEqual(conversation['messages'][1]['content'], 'Bonjour')
        self.assertEqual(conversation['messages'][1]['meta'].get('input_mode'), 'voice')
        payload = messages_response.get_json()
        self.assertEqual(messages_response.status_code, 200)
        self.assertEqual(payload['messages'][1]['meta'].get('input_mode'), 'voice')

    def test_api_chat_keeps_keyboard_messages_free_of_input_mode_meta(self) -> None:
        conversation = {
            'id': 'conv-input-mode',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed, restore = self._patch_chat_runtime(conversation=conversation)
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'input_mode': 'keyboard'},
            )
            messages_response = self.client.get('/api/conversations/conv-input-mode/messages')
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertGreaterEqual(len(observed['save_calls']), 1)
        self.assertEqual(conversation['messages'][1]['role'], 'user')
        self.assertNotIn('input_mode', conversation['messages'][1].get('meta', {}))
        payload = messages_response.get_json()
        self.assertEqual(messages_response.status_code, 200)
        self.assertNotIn('input_mode', payload['messages'][1].get('meta', {}))

    def test_api_chat_rejects_invalid_input_mode(self) -> None:
        conversation = {
            'id': 'conv-input-mode',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        _observed, restore = self._patch_chat_runtime(conversation=conversation)
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'input_mode': 'dictaphone'},
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'input_mode invalide'})

    def test_api_chat_injects_voice_guard_block_into_prompt_for_voice_turn(self) -> None:
        conversation = {
            'id': 'conv-input-mode',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed, restore = self._patch_chat_runtime(conversation=conversation)
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'input_mode': 'voice'},
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['payload_messages'][0]['role'], 'system')
        system_prompt = observed['payload_messages'][0]['content']
        self.assertIn('[GARDE DE LECTURE VOCALE]', system_prompt)
        self.assertIn("transcription vocale", system_prompt)
        self.assertIn("scories d'oralite", system_prompt)
        self.assertIn('partiellement mixte', system_prompt)

    def test_api_chat_keeps_voice_guard_block_out_of_prompt_for_keyboard_turn(self) -> None:
        conversation = {
            'id': 'conv-input-mode',
            'created_at': '2026-03-26T00:00:00Z',
            'updated_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed, restore = self._patch_chat_runtime(conversation=conversation)
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Bonjour', 'input_mode': 'keyboard'},
            )
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['payload_messages'][0]['role'], 'system')
        system_prompt = observed['payload_messages'][0]['content']
        self.assertNotIn('[GARDE DE LECTURE VOCALE]', system_prompt)
        self.assertNotIn("transcription vocale", system_prompt)


if __name__ == '__main__':
    unittest.main()
