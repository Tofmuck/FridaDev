from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import chat_stream_control
from core import conv_store
from memory import memory_store


class ServerPhase14ChatServiceTests(unittest.TestCase):
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

    def _split_stream_body(self, response) -> tuple[str, dict[str, str] | None]:
        return chat_stream_control.split_text_and_terminal(response.get_data())

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post):
        originals = []
        observed = {'save_calls': [], 'save_new_traces_calls': []}

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
                value='sk-phase14',
                source='db_encrypted',
                source_reason='db_row',
            ),
        )
        patch_attr(self.server.conv_store, 'normalize_conversation_id', lambda _raw: None)
        patch_attr(self.server.conv_store, 'load_conversation', lambda *_args, **_kwargs: None)
        patch_attr(self.server.conv_store, 'new_conversation', lambda _system: conversation)

        def fake_save_conversation(*_args, **kwargs):
            observed['save_calls'].append({'kwargs': dict(kwargs)})

        patch_attr(self.server.conv_store, 'save_conversation', fake_save_conversation)
        patch_attr(
            self.server.conv_store,
            'append_message',
            lambda conv, role, content, timestamp=None, meta=None, **_kwargs: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp, 'meta': meta}
            ),
        )
        patch_attr(self.server.conv_store, 'conversation_path', lambda _id: 'conv/conv-phase14.json')
        patch_attr(
            self.server.conv_store,
            'build_prompt_messages',
            lambda *_args, **_kwargs: [{'role': 'user', 'content': 'Bonjour'}],
        )
        patch_attr(self.server.memory_store, 'decay_identities', lambda: None)
        patch_attr(self.server.summarizer, 'maybe_summarize', lambda *args, **kwargs: False)
        patch_attr(self.server.identity, 'build_identity_block', lambda: ('', []))
        patch_attr(
            self.server.identity,
            'build_identity_input',
            lambda: {
                'schema_version': 'v2',
                'frida': {
                    'static': {'content': '', 'source': None},
                    'mutable': {
                        'content': '',
                        'source_trace_id': None,
                        'updated_by': None,
                        'update_reason': None,
                        'updated_ts': None,
                    },
                },
                'user': {
                    'static': {'content': '', 'source': None},
                    'mutable': {
                        'content': '',
                        'source_trace_id': None,
                        'updated_by': None,
                        'update_reason': None,
                        'updated_ts': None,
                    },
                },
            },
        )
        patch_attr(self.server.memory_store, 'retrieve', lambda *_args, **_kwargs: [])
        patch_attr(self.server.memory_store, 'get_recent_context_hints', lambda **_kwargs: [])
        patch_attr(self.server.admin_logs, 'log_event', lambda *args, **kwargs: None)
        patch_attr(self.server.llm, 'or_headers', lambda **_kwargs: {})
        def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['payload_messages'] = [dict(message) for message in _messages]
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': list(_messages),
                'max_tokens': max_tokens,
                'stream': stream,
            }

        patch_attr(self.server.llm, 'build_payload', fake_build_payload)
        patch_attr(self.server.requests, 'post', requests_post)
        patch_attr(self.server.token_utils, 'count_tokens', lambda *_args, **_kwargs: 1)
        patch_attr(
            self.server.memory_store,
            'save_new_traces',
            lambda conv, *_args, **_kwargs: observed['save_new_traces_calls'].append(
                [dict(message) for message in conv.get('messages', [])]
            ),
        )
        patch_attr(self.server.chat_service, '_record_identity_entries_for_mode', lambda *_args, **_kwargs: None)
        patch_attr(self.server.memory_store, 'reactivate_identities', lambda *_args, **_kwargs: None)
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

    def test_api_chat_stream_keeps_content_type_and_conversation_headers(self) -> None:
        observed = {'stream_kw': None, 'stream_completed': False, 'now_iso_flags': []}
        conversation = {
            'id': 'conv-stream-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Bon"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"jour"}}]}'
                observed['stream_completed'] = True
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            observed['stream_kw'] = kwargs.get('stream')
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_now_iso = self.server.chat_service._now_iso
        now_values = iter(['2026-03-26T00:00:10Z', '2026-03-26T00:00:20Z'])

        def fake_now_iso():
            observed['now_iso_flags'].append(observed['stream_completed'])
            return next(now_values)

        self.server.chat_service._now_iso = fake_now_iso
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
            self.server.chat_service._now_iso = original_now_iso
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertEqual(response.headers.get('X-Conversation-Id'), 'conv-stream-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Created-At'), '2026-03-26T00:00:00Z')
        self.assertIsNone(response.headers.get('X-Conversation-Updated-At'))
        response_text, terminal = self._split_stream_body(response)
        self.assertEqual(response_text, 'Bonjour')
        self.assertEqual(terminal, {'event': 'done', 'updated_at': '2026-03-26T00:00:20Z'})
        self.assertTrue(observed['stream_kw'])
        self.assertEqual(conversation['messages'][-1]['timestamp'], '2026-03-26T00:00:20Z')
        self.assertEqual(observed_state['save_calls'][-1]['kwargs'].get('updated_at'), '2026-03-26T00:00:20Z')
        self.assertEqual(observed['now_iso_flags'], [False, True])

    def test_api_chat_stream_normalizes_ordinary_turn_for_first_party_surface(self) -> None:
        conversation = {
            'id': 'conv-stream-plain-text-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"JSON est un format.\\n\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"- Lisible.\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"1) Portable."}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': "Explique simplement ce qu'est JSON.", 'stream': True},
                buffered=True,
            )
        finally:
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertIsNone(response.headers.get('X-Conversation-Updated-At'))
        self.assertNotIn('\n- ', text)
        self.assertNotIn('\n1) ', text)
        self.assertIn('Lisible.', text)
        self.assertIn('Portable.', text)
        self.assertEqual(
            terminal,
            {'event': 'done', 'updated_at': conversation['messages'][-1]['timestamp']},
        )
        self.assertEqual(conversation['messages'][-1]['role'], 'assistant')
        self.assertEqual(conversation['messages'][-1]['content'], text)
        self.assertEqual(observed_state['save_calls'][-1]['kwargs'].get('updated_at'), conversation['messages'][-1]['timestamp'])
        self.assertEqual(len(observed_state['save_new_traces_calls']), 1)
        self.assertEqual(observed_state['save_new_traces_calls'][-1][-1]['content'], text)

    def test_api_chat_stream_preserves_explicit_plan_structure_for_first_party_surface(self) -> None:
        conversation = {
            'id': 'conv-stream-structured-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"1) Comprendre\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"2) Structurer"}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Donne-moi un plan simple en trois étapes.', 'stream': True},
                buffered=True,
            )
        finally:
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.headers.get('X-Conversation-Updated-At'))
        self.assertIn('1) Comprendre', text)
        self.assertIn('2) Structurer', text)
        self.assertEqual(
            terminal,
            {'event': 'done', 'updated_at': conversation['messages'][-1]['timestamp']},
        )
        self.assertEqual(conversation['messages'][-1]['content'], text)
        self.assertNotIn('assistant_turn', conversation['messages'][-1].get('meta') or {})
        self.assertEqual(observed_state['save_calls'][-1]['kwargs'].get('updated_at'), conversation['messages'][-1]['timestamp'])

    def test_api_chat_stream_removes_unrequested_fenced_code_blocks_for_first_party_surface(self) -> None:
        conversation = {
            'id': 'conv-stream-code-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Voici JSON :\\n\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"```json\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"{\\n  \\"nom\\": \\"Dupont\\"\\n}\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"```\\n"}}]}'
                yield 'data: {"choices":[{"delta":{"content":"C\\u2019est un format texte."}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': "Explique simplement ce qu'est JSON.", 'stream': True},
                buffered=True,
            )
        finally:
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertIsNone(response.headers.get('X-Conversation-Updated-At'))
        self.assertIn('Voici JSON :', text)
        self.assertIn('C’est un format texte.', text)
        self.assertNotIn('```', text)
        self.assertNotIn('"nom"', text)
        self.assertEqual(
            terminal,
            {'event': 'done', 'updated_at': conversation['messages'][-1]['timestamp']},
        )
        self.assertEqual(conversation['messages'][-1]['content'], text)
        self.assertEqual(observed_state['save_calls'][-1]['kwargs'].get('updated_at'), conversation['messages'][-1]['timestamp'])

    def test_api_chat_stream_emits_error_terminal_when_upstream_breaks_mid_stream(self) -> None:
        conversation = {
            'id': 'conv-stream-error-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class _FakeRequestException(Exception):
            pass

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Bon"}}]}'
                raise _FakeRequestException('boom stream')

        def fake_requests_post(*_args, **kwargs):
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_exc = self.server.requests.exceptions.RequestException
        self.server.requests.exceptions.RequestException = _FakeRequestException
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
            self.server.requests.exceptions.RequestException = original_exc
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertEqual(text, '')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'upstream_error',
                'updated_at': observed_state['save_calls'][-1]['kwargs'].get('updated_at'),
            },
        )
        assistant_message = conversation['messages'][-1]
        self.assertEqual(assistant_message.get('role'), 'assistant')
        self.assertEqual(assistant_message.get('content'), '')
        self.assertEqual(
            assistant_message.get('timestamp'),
            observed_state['save_calls'][-1]['kwargs'].get('updated_at'),
        )
        self.assertEqual(
            assistant_message.get('meta'),
            {
                'assistant_turn': {
                    'status': 'interrupted',
                    'error_code': 'upstream_error',
                }
            },
        )
        self.assertTrue(observed_state['save_calls'][-1]['kwargs'].get('updated_at'))
        self.assertEqual(observed_state['save_new_traces_calls'], [])

    def test_api_chat_stream_emits_error_terminal_when_local_finalize_breaks_and_does_not_persist_fragment(self) -> None:
        conversation = {
            'id': 'conv-stream-finalize-error-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeStreamResponse:
            encoding = None

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def raise_for_status(self):
                return None

            def iter_lines(self, decode_unicode=True, delimiter='\n'):
                yield 'data: {"choices":[{"delta":{"content":"Bon"}}]}'
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_record_identity = self.server.chat_service._record_identity_entries_for_mode

        def raising_record_identity(*_args, **_kwargs):
            raise RuntimeError('finalize boom')

        self.server.chat_service._record_identity_entries_for_mode = raising_record_identity
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
            self.server.chat_service._record_identity_entries_for_mode = original_record_identity
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertEqual(text, '')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'stream_finalize_error',
                'updated_at': observed_state['save_calls'][-1]['kwargs'].get('updated_at'),
            },
        )
        assistant_message = conversation['messages'][-1]
        self.assertEqual(assistant_message.get('role'), 'assistant')
        self.assertEqual(assistant_message.get('content'), '')
        self.assertEqual(
            assistant_message.get('timestamp'),
            observed_state['save_calls'][-1]['kwargs'].get('updated_at'),
        )
        self.assertEqual(
            assistant_message.get('meta'),
            {
                'assistant_turn': {
                    'status': 'interrupted',
                    'error_code': 'stream_finalize_error',
                }
            },
        )
        self.assertTrue(observed_state['save_calls'][-1]['kwargs'].get('updated_at'))
        self.assertEqual(observed_state['save_new_traces_calls'], [])

    def test_api_chat_rejects_empty_message_with_400_contract(self) -> None:
        response = self.client.post('/api/chat', json={'message': '   '})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'message vide'})

    def test_api_chat_returns_404_when_conversation_id_is_normalized_but_missing(self) -> None:
        observed = {'new_conversation_called': False}
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_load = self.server.conv_store.load_conversation
        original_new = self.server.conv_store.new_conversation

        self.server.conv_store.normalize_conversation_id = lambda _raw: 'conv-missing-phase14'
        self.server.conv_store.load_conversation = lambda *_args, **_kwargs: None

        def fake_new_conversation(_system):
            observed['new_conversation_called'] = True
            return {'id': 'should-not-be-created', 'created_at': '2026-03-26T00:00:00Z', 'messages': []}

        self.server.conv_store.new_conversation = fake_new_conversation
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'conversation_id': 'conv-missing'})
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.load_conversation = original_load
            self.server.conv_store.new_conversation = original_new

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'conversation introuvable'})
        self.assertFalse(observed['new_conversation_called'])

    def test_api_chat_returns_502_on_llm_request_exception(self) -> None:
        conversation = {
            'id': 'conv-err-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        def fake_requests_post(*_args, **_kwargs):
            raise self.server.requests.exceptions.RequestException('boom')

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            restore()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'Connexion au LLM: boom'},
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_keeps_hermeneutic_insertion_point_between_memory_and_prompt_build(self) -> None:
        order: list[str] = []
        conversation = {
            'id': 'conv-seam-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok seam'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_prepare = self.server.chat_service.chat_memory_flow.prepare_memory_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.chat_memory_flow.prepare_memory_context = (
            lambda **_kwargs: order.append('prepare_memory_context') or ('shadow', [], [])
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = (
            lambda **_kwargs: order.append('hermeneutic_insertion_point') or None
        )
        self.server.conv_store.build_prompt_messages = (
            lambda *_args, **_kwargs: order.append('build_prompt_messages') or [{'role': 'user', 'content': 'Bonjour'}]
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.chat_memory_flow.prepare_memory_context = original_prepare
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(
            order,
            ['prepare_memory_context', 'hermeneutic_insertion_point', 'build_prompt_messages'],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_injects_hermeneutic_judgment_block_from_validated_output(self) -> None:
        conversation = {
            'id': 'conv-validated-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validated block'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'judgment_posture': 'answer',
                'pipeline_directives_provisional': ['posture_answer'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'challenge',
                    'final_judgment_posture': 'answer',
                    'pipeline_directives_final': ['posture_answer', 'source_conflict_clarify'],
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )
        )
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Bonjour'},
            ]
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        system_prompt = observed_state['payload_messages'][0]['content']
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: answer.', system_prompt)
        self.assertIn('Consigne hermeneutique: Tu peux produire une reponse substantive normale.', system_prompt)
        self.assertIn('Directives finales actives: posture_answer, source_conflict_clarify.', system_prompt)
        self.assertNotIn('primary_verdict', system_prompt)
        self.assertNotIn('validation_dialogue_context', system_prompt)
        self.assertNotIn('justifications', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_injects_suspend_block_when_validation_agent_fail_opens(self) -> None:
        conversation = {
            'id': 'conv-validation-fail-open-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok fail open block'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'judgment_posture': 'answer',
                'pipeline_directives_provisional': ['posture_answer'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'suspend',
                    'final_judgment_posture': 'suspend',
                    'pipeline_directives_final': ['posture_suspend', 'fallback_validation'],
                },
                status='error',
                model='openai/gpt-5.4-nano',
                decision_source='fail_open',
                reason_code='timeout',
            )
        )
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Bonjour'},
            ]
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        system_prompt = observed_state['payload_messages'][0]['content']
        self.assertIn('[JUGEMENT HERMENEUTIQUE]', system_prompt)
        self.assertIn('Posture finale validee: suspend.', system_prompt)
        self.assertIn(
            'Consigne hermeneutique: Tu ne dois pas produire de reponse substantive normale. Tu dois expliciter la suspension ou la limite presente.',
            system_prompt,
        )
        self.assertIn('Directives finales actives: posture_suspend, fallback_validation.', system_prompt)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_active_summary_to_hermeneutic_insertion_point(self) -> None:
        observed = {'summary_input': None}
        conversation = {
            'id': 'conv-summary-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok summary'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-phase14',
            'conversation_id': 'conv-summary-phase14',
            'start_ts': '2026-03-20T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif de continuité',
        }

        def fake_insertion(**kwargs):
            observed['summary_input'] = kwargs.get('summary_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['summary_input']['schema_version'], 'v1')
        self.assertEqual(observed['summary_input']['status'], 'available')
        self.assertEqual(observed['summary_input']['summary']['id'], 'sum-phase14')
        self.assertEqual(observed['summary_input']['summary']['conversation_id'], 'conv-summary-phase14')
        self.assertEqual(observed['summary_input']['summary']['start_ts'], '2026-03-20T10:00:00Z')
        self.assertEqual(observed['summary_input']['summary']['end_ts'], '2026-03-24T18:00:00Z')
        self.assertEqual(observed['summary_input']['summary']['content'], 'Résumé actif de continuité')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_identity_input_to_hermeneutic_insertion_point(self) -> None:
        observed = {'identity_input': None}
        conversation = {
            'id': 'conv-identity-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok identity'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_identity_input = self.server.identity.build_identity_input
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        self.server.identity.build_identity_input = lambda: {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': 'Frida statique', 'source': '/runtime/llm_identity.txt'},
                'mutable': {
                    'content': 'Frida aime les raisonnements structurés',
                    'source_trace_id': '11111111-1111-1111-1111-111111111111',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-24T12:00:00Z',
                },
            },
            'user': {
                'static': {'content': 'Utilisateur statique', 'source': '/runtime/user_identity.txt'},
                'mutable': {
                    'content': 'Utilisateur prefere les réponses concises',
                    'source_trace_id': '22222222-2222-2222-2222-222222222222',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-03-25T09:30:00Z',
                },
            },
        }

        def fake_insertion(**kwargs):
            observed['identity_input'] = kwargs.get('identity_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['identity_input']['schema_version'], 'v2')
        self.assertEqual(observed['identity_input']['frida']['static']['content'], 'Frida statique')
        self.assertNotIn('staging', observed['identity_input']['frida'])
        self.assertEqual(
            observed['identity_input']['frida']['mutable']['source_trace_id'],
            '11111111-1111-1111-1111-111111111111',
        )
        self.assertEqual(
            observed['identity_input']['frida']['mutable']['updated_by'],
            'identity_periodic_agent',
        )
        self.assertEqual(observed['identity_input']['user']['static']['content'], 'Utilisateur statique')
        self.assertNotIn('staging', observed['identity_input']['user'])
        self.assertEqual(
            observed['identity_input']['user']['mutable']['source_trace_id'],
            '22222222-2222-2222-2222-222222222222',
        )
        self.assertEqual(
            observed['identity_input']['user']['mutable']['updated_by'],
            'identity_periodic_agent',
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_identity_block_and_payload_use_same_canonical_mutables_without_legacy_ids(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }
        mutable_entries = {
            'llm': {
                'content': 'Frida mutable narrative retenue',
                'source_trace_id': '11111111-1111-1111-1111-111111111111',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-03-24T12:00:00Z',
            },
            'user': {
                'content': 'User mutable narrative retenue',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-03-25T09:30:00Z',
            },
        }

        identity.load_llm_identity = lambda: 'Frida static baseline'
        identity.load_user_identity = lambda: 'User static baseline'
        identity._safe_static_identity_source = lambda field: f'data/identity/{field}.txt'
        self.server.memory_store.get_mutable_identity = lambda subject: dict(mutable_entries[subject])
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 4
        try:
            block, used_ids = identity.build_identity_block()
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertIn('Frida mutable narrative retenue', block)
        self.assertIn('User mutable narrative retenue', block)
        self.assertIn('Frida static baseline', block)
        self.assertIn('User static baseline', block)
        self.assertIn('[STATIQUE]', block)
        self.assertIn('[MUTABLE]', block)
        self.assertNotIn('stability=', block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['schema_version'], 'v2')
        self.assertNotIn('dynamic', payload['frida'])
        self.assertNotIn('dynamic', payload['user'])
        self.assertNotIn('staging', payload['frida'])
        self.assertNotIn('staging', payload['user'])
        self.assertEqual(payload['frida']['static']['content'], 'Frida static baseline')
        self.assertEqual(payload['user']['static']['content'], 'User static baseline')
        self.assertEqual(payload['frida']['mutable']['content'], 'Frida mutable narrative retenue')
        self.assertEqual(payload['user']['mutable']['content'], 'User mutable narrative retenue')

    def test_identity_input_loads_static_content_from_host_state_mirror_while_keeping_runtime_source(self) -> None:
        identity = self.server.identity
        originals = {
            'get_resources_settings': identity.runtime_settings.get_resources_settings,
            '_get_mutable_identity': identity._get_mutable_identity,
            'app_root': identity.static_identity_paths.APP_ROOT,
            'repo_root': identity.static_identity_paths.REPO_ROOT,
            'host_state_root': identity.static_identity_paths.HOST_STATE_ROOT,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            (tmp_path / 'app').mkdir()
            identity_dir = tmp_path / 'state' / 'data' / 'identity'
            identity_dir.mkdir(parents=True)
            llm_text = 'Frida statique host mirror'
            user_text = 'Utilisateur statique host mirror'
            (identity_dir / 'llm_identity.txt').write_text(llm_text, encoding='utf-8')
            (identity_dir / 'user_identity.txt').write_text(user_text, encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': 'data/identity/llm_identity.txt', 'origin': 'db'},
                            'user_identity_path': {'value': 'data/identity/user_identity.txt', 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            identity.runtime_settings.get_resources_settings = fake_get_resources_settings
            identity.static_identity_paths.APP_ROOT = tmp_path / 'app'
            identity.static_identity_paths.REPO_ROOT = tmp_path
            identity.static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            identity._get_mutable_identity = lambda _subject: None
            try:
                block, used_ids = identity.build_identity_block()
                payload = identity.build_identity_input()
            finally:
                identity.runtime_settings.get_resources_settings = originals['get_resources_settings']
                identity._get_mutable_identity = originals['_get_mutable_identity']
                identity.static_identity_paths.APP_ROOT = originals['app_root']
                identity.static_identity_paths.REPO_ROOT = originals['repo_root']
                identity.static_identity_paths.HOST_STATE_ROOT = originals['host_state_root']

        self.assertIn(llm_text, block)
        self.assertIn(user_text, block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['frida']['static']['content'], llm_text)
        self.assertEqual(payload['user']['static']['content'], user_text)
        self.assertEqual(payload['frida']['static']['source'], 'data/identity/llm_identity.txt')
        self.assertEqual(payload['user']['static']['source'], 'data/identity/user_identity.txt')
        self.assertNotIn('dynamic', payload['frida'])
        self.assertNotIn('dynamic', payload['user'])
        self.assertEqual(payload['frida']['mutable']['content'], '')
        self.assertEqual(payload['user']['mutable']['content'], '')

    def test_identity_input_keeps_explicit_user_mutable_revelation_available_for_next_turn(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }

        identity.load_llm_identity = lambda: ''
        identity.load_user_identity = lambda: ''
        identity._safe_static_identity_source = lambda _field: None
        self.server.memory_store.get_mutable_identity = lambda subject: (
            {
                'content': 'Je suis Christophe Muck',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-04-04T19:00:00Z',
            }
            if subject == 'user'
            else None
        )
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 32
        try:
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertEqual(payload['user']['mutable']['content'], 'Je suis Christophe Muck')

    def test_identity_active_path_keeps_mutable_present_when_static_identity_is_large(self) -> None:
        identity = self.server.identity
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }

        identity.load_llm_identity = lambda: 'Profil statique Frida ' * 120
        identity.load_user_identity = lambda: 'Profil statique utilisateur ' * 120
        identity._safe_static_identity_source = lambda _field: None
        self.server.memory_store.get_mutable_identity = lambda subject: (
            {
                'content': 'Je suis Christophe Muck',
                'source_trace_id': '22222222-2222-2222-2222-222222222222',
                'updated_by': 'identity_periodic_agent',
                'update_reason': 'periodic_agent',
                'updated_ts': '2026-04-04T19:00:00Z',
            }
            if subject == 'user'
            else None
        )
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not govern active identity path'
        )
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 80
        try:
            block, used_ids = identity.build_identity_block()
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.get_identities = original_get_identities

        self.assertIn('Je suis Christophe Muck', block)
        self.assertEqual(used_ids, [])
        self.assertEqual(payload['user']['mutable']['content'], 'Je suis Christophe Muck')

    def test_api_chat_exposes_canonical_recent_context_to_hermeneutic_insertion_point(self) -> None:
        observed = {'recent_context_input': None}
        conversation = {
            'id': 'conv-recent-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message ancien', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'assistant', 'content': 'Réponse récente', 'timestamp': '2026-03-25T09:00:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T12:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-phase14',
            'conversation_id': 'conv-recent-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_context_input'] = kwargs.get('recent_context_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_context_input']['schema_version'], 'v1')
        self.assertEqual(
            observed['recent_context_input']['messages'],
            [
                {
                    'role': 'assistant',
                    'content': 'Réponse récente',
                    'timestamp': '2026-03-25T09:00:00Z',
                },
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T12:00:00Z',
                },
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_rebuilds_validation_dialogue_context_when_recent_context_is_empty_after_summary_cutoff(self) -> None:
        observed = {'validation_dialogue_context': None}
        conversation = {
            'id': 'conv-validation-context-fallback-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validation context fallback'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_now_iso = self.server.chat_service._now_iso
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        self.server.chat_service._now_iso = lambda: '2026-03-26T10:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-future-cutoff-phase14',
            'conversation_id': 'conv-validation-context-fallback-phase14',
            'start_ts': '2026-03-25T08:00:00Z',
            'end_ts': '2026-03-26T12:00:00Z',
            'content': 'Résumé actif avec cutoff futur',
        }
        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'incertain',
                'proof_regime': 'source_explicite_requise',
                'uncertainty_posture': 'prudente',
                'judgment_posture': 'answer',
                'discursive_regime': 'simple',
                'resituation_level': 'none',
                'time_reference_mode': 'atemporal',
                'source_priority': [['tour_utilisateur']],
                'source_conflicts': [],
                'pipeline_directives_provisional': ['posture_answer'],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }

        def fake_build_validated_output(**kwargs):
            observed['validation_dialogue_context'] = kwargs.get('validation_dialogue_context')
            return self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'confirm',
                    'final_judgment_posture': 'answer',
                    'pipeline_directives_final': ['posture_answer'],
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )

        self.server.chat_service.validation_agent.build_validated_output = fake_build_validated_output
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(
            observed['validation_dialogue_context'],
            {
                'schema_version': 'v1',
                'messages': [
                    {
                        'role': 'user',
                        'content': 'Bonjour',
                        'timestamp': '2026-03-26T10:00:00Z',
                    }
                ],
            },
        )
        self.assertEqual(observed['validation_dialogue_context']['schema_version'], 'v1')
        self.assertTrue(observed['validation_dialogue_context']['messages'])
        self.assertEqual(observed['validation_dialogue_context']['messages'][-1]['role'], 'user')
        self.assertEqual(observed['validation_dialogue_context']['messages'][-1]['content'], 'Bonjour')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_recent_window_to_hermeneutic_insertion_point(self) -> None:
        observed = {'recent_window_input': None}
        conversation = {
            'id': 'conv-recent-window-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message pre-summary', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'user', 'content': 'Tour 1 user', 'timestamp': '2026-03-25T08:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 1 assistant', 'timestamp': '2026-03-25T08:01:00Z'},
                {'role': 'user', 'content': 'Tour 2 user', 'timestamp': '2026-03-25T09:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 2 assistant', 'timestamp': '2026-03-25T09:01:00Z'},
                {'role': 'user', 'content': 'Tour 3 user', 'timestamp': '2026-03-25T10:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 3 assistant', 'timestamp': '2026-03-25T10:01:00Z'},
                {'role': 'user', 'content': 'Tour 4 user', 'timestamp': '2026-03-25T11:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 4 assistant', 'timestamp': '2026-03-25T11:01:00Z'},
                {'role': 'user', 'content': 'Tour 5 user', 'timestamp': '2026-03-25T12:00:00Z'},
                {'role': 'assistant', 'content': 'Tour 5 assistant', 'timestamp': '2026-03-25T12:01:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent window'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T14:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-window-phase14',
            'conversation_id': 'conv-recent-window-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_window_input'] = kwargs.get('recent_window_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_window_input']['schema_version'], 'v1')
        self.assertEqual(observed['recent_window_input']['max_recent_turns'], 5)
        self.assertEqual(observed['recent_window_input']['turn_count'], 5)
        self.assertTrue(observed['recent_window_input']['has_in_progress_turn'])
        self.assertEqual(
            [turn['turn_status'] for turn in observed['recent_window_input']['turns']],
            ['complete', 'complete', 'complete', 'complete', 'in_progress'],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][0]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Tour 2 user',
                    'timestamp': '2026-03-25T09:00:00Z',
                },
                {
                    'role': 'assistant',
                    'content': 'Tour 2 assistant',
                    'timestamp': '2026-03-25T09:01:00Z',
                },
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][-1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T14:00:00Z',
                }
            ],
        )
        self.assertNotIn(
            'Tour 1 user',
            [
                message['content']
                for turn in observed['recent_window_input']['turns']
                for message in turn['messages']
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_recent_window_keeps_initial_assistant_without_fake_user_pair(self) -> None:
        observed = {'recent_window_input': None}
        conversation = {
            'id': 'conv-recent-window-initial-assistant-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [
                {'role': 'system', 'content': 'BACKEND SYSTEM PROMPT', 'timestamp': '2026-03-26T00:00:00Z'},
                {'role': 'user', 'content': 'Message pre-summary', 'timestamp': '2026-03-20T08:00:00Z'},
                {'role': 'assistant', 'content': 'Assistant post-summary initial', 'timestamp': '2026-03-25T09:00:00Z'},
                {'role': 'user', 'content': 'Question récente', 'timestamp': '2026-03-25T09:10:00Z'},
                {'role': 'assistant', 'content': 'Réponse récente', 'timestamp': '2026-03-25T09:11:00Z'},
            ],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok recent assistant only'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_get_active_summary = self.server.chat_service.conversations_prompt_window.get_active_summary
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_now_iso = self.server.chat_service._now_iso
        self.server.chat_service._now_iso = lambda: '2026-03-26T14:00:00Z'
        self.server.chat_service.conversations_prompt_window.get_active_summary = lambda *_args, **_kwargs: {
            'id': 'sum-recent-window-initial-assistant-phase14',
            'conversation_id': 'conv-recent-window-initial-assistant-phase14',
            'start_ts': '2026-03-18T10:00:00Z',
            'end_ts': '2026-03-24T18:00:00Z',
            'content': 'Résumé actif',
        }

        def fake_insertion(**kwargs):
            observed['recent_window_input'] = kwargs.get('recent_window_input')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service._now_iso = original_now_iso
            self.server.chat_service.conversations_prompt_window.get_active_summary = original_get_active_summary
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['recent_window_input']['turn_count'], 3)
        self.assertTrue(observed['recent_window_input']['has_in_progress_turn'])
        self.assertEqual(
            [turn['turn_status'] for turn in observed['recent_window_input']['turns']],
            ['assistant_only', 'complete', 'in_progress'],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][0]['messages'],
            [
                {
                    'role': 'assistant',
                    'content': 'Assistant post-summary initial',
                    'timestamp': '2026-03-25T09:00:00Z',
                }
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Question récente',
                    'timestamp': '2026-03-25T09:10:00Z',
                },
                {
                    'role': 'assistant',
                    'content': 'Réponse récente',
                    'timestamp': '2026-03-25T09:11:00Z',
                },
            ],
        )
        self.assertEqual(
            observed['recent_window_input']['turns'][-1]['messages'],
            [
                {
                    'role': 'user',
                    'content': 'Bonjour',
                    'timestamp': '2026-03-26T14:00:00Z',
                }
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_user_turn_input_and_signals_to_hermeneutic_insertion_point(self) -> None:
        observed = {'user_turn_input': None, 'user_turn_signals': None}
        conversation = {
            'id': 'conv-user-turn-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok user turn'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point

        def fake_insertion(**kwargs):
            observed['user_turn_input'] = kwargs.get('user_turn_input')
            observed['user_turn_signals'] = kwargs.get('user_turn_signals')
            return None

        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        try:
            response = self.client.post('/api/chat', json={'message': 'Quel est le meilleur ?'})
        finally:
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['user_turn_input']['schema_version'], 'v1')
        self.assertEqual(observed['user_turn_input']['geste_dialogique_dominant'], 'interrogation')
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['principe'], 'maximal_possible')
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['types_de_preuve_attendus'], [])
        self.assertEqual(observed['user_turn_input']['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(observed['user_turn_input']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(observed['user_turn_input']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
        self.assertTrue(observed['user_turn_signals']['present'])
        self.assertFalse(observed['user_turn_signals']['ambiguity_present'])
        self.assertTrue(observed['user_turn_signals']['underdetermination_present'])
        self.assertEqual(observed['user_turn_signals']['active_signal_families'], ['critere'])
        self.assertEqual(observed['user_turn_signals']['active_signal_families_count'], 1)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_runs_stimmung_agent_as_upstream_stage_without_seam_injection(self) -> None:
        observed = {'insertion_kwargs': None, 'events': []}
        conversation = {
            'id': 'conv-stimmung-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok stimmung stage'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_affective_turn_signal = self.server.chat_service.stimmung_agent.build_affective_turn_signal
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_build_affective_turn_signal(**_kwargs):
            return self.server.chat_service.stimmung_agent.StimmungAgentResult(
                signal={
                    'schema_version': 'v1',
                    'present': True,
                    'tones': [
                        {'tone': 'frustration', 'strength': 7},
                        {'tone': 'confusion', 'strength': 4},
                    ],
                    'dominant_tone': 'frustration',
                    'confidence': 0.82,
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )

        def fake_insertion(**kwargs):
            observed['insertion_kwargs'] = dict(kwargs)
            return None

        def fake_insert(event, **_kwargs):
            observed['events'].append(event)
            return True

        self.server.chat_service.stimmung_agent.build_affective_turn_signal = fake_build_affective_turn_signal
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': "C'est agaçant et je suis perdu"})
        finally:
            self.server.chat_service.stimmung_agent.build_affective_turn_signal = original_build_affective_turn_signal
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        stage_event = next(item for item in observed['events'] if item['stage'] == 'stimmung_agent')
        payload = stage_event['payload_json']
        self.assertEqual(stage_event['status'], 'ok')
        self.assertTrue(payload['present'])
        self.assertEqual(payload['dominant_tone'], 'frustration')
        self.assertEqual(payload['tones_count'], 2)
        self.assertEqual(
            payload['tones'],
            [
                {'tone': 'frustration', 'strength': 7},
                {'tone': 'confusion', 'strength': 4},
            ],
        )
        self.assertEqual(payload['confidence'], 0.82)
        self.assertEqual(payload['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(payload['decision_source'], 'primary')
        self.assertNotIn('user_msg', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('raw_output', payload)
        self.assertIsNotNone(observed['insertion_kwargs'])
        self.assertNotIn('affective_turn_signal', observed['insertion_kwargs'])
        self.assertIn('stimmung_input', observed['insertion_kwargs'])
        self.assertTrue(observed['insertion_kwargs']['stimmung_input']['present'])
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['dominant_tone'], 'frustration')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['stability'], 'emerging')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['shift_state'], 'steady')
        self.assertEqual(observed['insertion_kwargs']['stimmung_input']['turns_considered'], 1)
        self.assertIn('user_turn_input', observed['insertion_kwargs'])
        self.assertIn('user_turn_signals', observed['insertion_kwargs'])
        user_messages = [message for message in conversation['messages'] if message.get('role') == 'user']
        self.assertTrue(user_messages)
        self.assertEqual(
            user_messages[-1].get('meta', {}).get('affective_turn_signal'),
            {
                'schema_version': 'v1',
                'present': True,
                'tones': [
                    {'tone': 'frustration', 'strength': 7},
                    {'tone': 'confusion', 'strength': 4},
                ],
                'dominant_tone': 'frustration',
                'confidence': 0.82,
            },
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_exposes_canonical_web_input_and_reuses_single_web_pass(self) -> None:
        observed = {'web_input': None, 'prompt_messages': None, 'legacy_build_context_called': False}
        conversation = {
            'id': 'conv-web-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_payload = self.server.llm.build_payload
        def fake_build_context_payload(_user_msg, **kwargs):
            observed['web_requests_module'] = kwargs.get('requests_module')
            observed['web_llm_module'] = kwargs.get('llm_module')
            return {
                'enabled': True,
                'status': 'ok',
                'reason_code': None,
                'original_user_message': 'Bonjour',
                'query': 'query test',
                'results_count': 1,
                'explicit_url_detected': True,
                'explicit_url': 'https://example.com/article',
                'read_state': 'page_not_read_snippet_fallback',
                'primary_source_kind': 'explicit_url',
                'primary_read_attempted': True,
                'primary_read_status': 'empty',
                'primary_read_filter': 'raw',
                'primary_read_raw_fallback_used': True,
                'fallback_used': True,
                'collection_path': 'explicit_url_fallback_search',
                'runtime': {
                    'searxng_results': 5,
                    'crawl4ai_top_n': 2,
                    'crawl4ai_max_chars': 1500,
                },
                'sources': [
                    {
                        'rank': 1,
                        'title': 'Titre source',
                        'url': 'https://example.com/article',
                        'source_domain': 'example.com',
                        'search_snippet': 'Snippet source',
                        'used_in_prompt': True,
                        'used_content_kind': 'search_snippet',
                        'content_used': 'Snippet source',
                        'truncated': False,
                        'source_origin': 'search_result',
                        'is_primary_source': False,
                        'crawl_status': 'not_attempted',
                    }
                ],
                'context_block': 'WEB CONTEXT',
            }

        self.server.ws.build_context_payload = fake_build_context_payload

        def legacy_build_context_should_not_run(_user_msg):
            observed['legacy_build_context_called'] = True
            raise AssertionError('legacy build_context should not be called')

        def fake_insertion(**kwargs):
            observed['web_input'] = kwargs.get('web_input')
            return None

        def fake_build_payload(messages, _temperature, _top_p, max_tokens, stream=False):
            observed['prompt_messages'] = messages
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': messages,
                'max_tokens': max_tokens,
                'stream': stream,
            }

        self.server.ws.build_context = legacy_build_context_should_not_run
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.llm.build_payload = fake_build_payload
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'web_search': True})
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.llm.build_payload = original_build_payload
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertFalse(observed['legacy_build_context_called'])
        self.assertEqual(observed['web_input']['schema_version'], 'v1')
        self.assertTrue(observed['web_input']['enabled'])
        self.assertEqual(observed['web_input']['status'], 'ok')
        self.assertEqual(observed['web_input']['activation_mode'], 'manual')
        self.assertEqual(observed['web_input']['query'], 'query test')
        self.assertEqual(observed['web_input']['results_count'], 1)
        self.assertTrue(observed['web_input']['explicit_url_detected'])
        self.assertEqual(observed['web_input']['explicit_url'], 'https://example.com/article')
        self.assertEqual(observed['web_input']['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(observed['web_input']['primary_source_kind'], 'explicit_url')
        self.assertTrue(observed['web_input']['primary_read_attempted'])
        self.assertEqual(observed['web_input']['primary_read_status'], 'empty')
        self.assertEqual(observed['web_input']['primary_read_filter'], 'raw')
        self.assertTrue(observed['web_input']['primary_read_raw_fallback_used'])
        self.assertTrue(observed['web_input']['fallback_used'])
        self.assertEqual(observed['web_input']['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(observed['web_input']['runtime']['searxng_results'], 5)
        self.assertEqual(observed['web_input']['sources'][0]['source_domain'], 'example.com')
        self.assertTrue(observed['web_input']['sources'][0]['used_in_prompt'])
        self.assertEqual(observed['web_input']['sources'][0]['used_content_kind'], 'search_snippet')
        self.assertEqual(observed['web_input']['sources'][0]['source_origin'], 'search_result')
        self.assertFalse(observed['web_input']['sources'][0]['is_primary_source'])
        self.assertEqual(observed['web_input']['sources'][0]['crawl_status'], 'not_attempted')
        self.assertEqual(observed['web_input']['used_content_kinds'], ['search_snippet'])
        self.assertEqual(observed['web_input']['injected_chars'], len('Snippet source'))
        self.assertEqual(observed['web_input']['context_chars'], len('WEB CONTEXT'))
        self.assertEqual(
            observed['web_input']['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': 'https://example.com/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len('Snippet source'),
                    'truncated': False,
                }
            ],
        )
        self.assertEqual(observed['web_input']['context_block'], 'WEB CONTEXT')
        self.assertEqual(
            observed['prompt_messages'],
            [{'role': 'user', 'content': 'WEB CONTEXT\n\nQuestion : Bonjour'}],
        )
        self.assertIsInstance(observed['web_requests_module'], self.server._RequestsChatLogProxy)
        self.assertIsInstance(observed['web_llm_module'], self.server._LlmChatLogProxy)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_does_not_auto_activate_web_for_source_link_or_reference_requests_without_manual_flag(self) -> None:
        cases = (
            'Donne-moi la source de cette affirmation.',
            'As-tu un lien ?',
            'Cite la reference bibliographique exacte.',
        )

        for message in cases:
            with self.subTest(message=message):
                observed = {'web_input': None, 'prompt_messages': None, 'build_context_calls': 0}
                conversation = {
                    'id': 'conv-web-not-requested-source-phase14',
                    'created_at': '2026-03-26T00:00:00Z',
                    'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
                }

                class FakeResponse:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {'choices': [{'message': {'content': 'ok no auto web'}}]}

                def fake_requests_post(*_args, **_kwargs):
                    return FakeResponse()

                observed_state, restore = self._patch_chat_pipeline(
                    conversation=conversation,
                    requests_post=fake_requests_post,
                )
                original_build_context_payload = self.server.ws.build_context_payload
                original_build_context = self.server.ws.build_context
                original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
                original_build_payload = self.server.llm.build_payload
                original_build_prompt_messages = self.server.conv_store.build_prompt_messages

                def unexpected_build_context_payload(_user_msg, **_kwargs):
                    observed['build_context_calls'] += 1
                    raise AssertionError('auto web should not run on pre-node source/link/reference requests')

                def fake_insertion(**kwargs):
                    observed['web_input'] = kwargs.get('web_input')
                    return None

                def fake_build_payload(messages, _temperature, _top_p, max_tokens, stream=False):
                    observed['prompt_messages'] = messages
                    return {
                        'model': 'openrouter/runtime-main-model',
                        'messages': messages,
                        'max_tokens': max_tokens,
                        'stream': stream,
                    }

                self.server.ws.build_context_payload = unexpected_build_context_payload
                self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
                    AssertionError('legacy build_context should not be called')
                )
                self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
                self.server.llm.build_payload = fake_build_payload
                self.server.conv_store.build_prompt_messages = (
                    lambda conversation_arg, *_args, **_kwargs: [
                        {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                        {'role': 'user', 'content': message},
                    ]
                )
                try:
                    response = self.client.post(
                        '/api/chat',
                        json={'message': message, 'web_search': False},
                    )
                finally:
                    self.server.ws.build_context_payload = original_build_context_payload
                    self.server.ws.build_context = original_build_context
                    self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
                    self.server.llm.build_payload = original_build_payload
                    self.server.conv_store.build_prompt_messages = original_build_prompt_messages
                    restore()

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['ok'])
                self.assertEqual(observed['build_context_calls'], 0)
                self.assertFalse(observed['web_input']['enabled'])
                self.assertEqual(observed['web_input']['status'], 'skipped')
                self.assertEqual(observed['web_input']['activation_mode'], 'not_requested')
                self.assertEqual(observed['web_input']['reason_code'], 'not_applicable')
                self.assertEqual(
                    observed['prompt_messages'],
                    [
                        {'role': 'system', 'content': conversation['messages'][0]['content']},
                        {'role': 'user', 'content': message},
                    ],
                )
                self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_does_not_auto_activate_web_for_pure_verification_request_without_manual_flag(self) -> None:
        observed = {'web_input': None, 'prompt_messages': None, 'build_context_calls': 0}
        conversation = {
            'id': 'conv-web-auto-verify-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web auto verify'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_payload = self.server.llm.build_payload
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages

        def unexpected_build_context_payload(_user_msg, **_kwargs):
            observed['build_context_calls'] += 1
            raise AssertionError('auto web should not run on pure verification request in current design')

        def fake_insertion(**kwargs):
            observed['web_input'] = kwargs.get('web_input')
            return None

        def fake_build_payload(messages, _temperature, _top_p, max_tokens, stream=False):
            observed['prompt_messages'] = messages
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': messages,
                'max_tokens': max_tokens,
                'stream': stream,
            }

        self.server.ws.build_context_payload = unexpected_build_context_payload
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.llm.build_payload = fake_build_payload
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {'role': 'user', 'content': 'Tu peux verifier cette affirmation ?'},
            ]
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Tu peux verifier cette affirmation ?', 'web_search': False},
            )
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.llm.build_payload = original_build_payload
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['build_context_calls'], 0)
        self.assertFalse(observed['web_input']['enabled'])
        self.assertEqual(observed['web_input']['status'], 'skipped')
        self.assertEqual(observed['web_input']['activation_mode'], 'not_requested')
        self.assertEqual(observed['web_input']['reason_code'], 'not_applicable')
        self.assertEqual(
            observed['prompt_messages'],
            [
                {'role': 'system', 'content': conversation['messages'][0]['content']},
                {'role': 'user', 'content': 'Tu peux verifier cette affirmation ?'},
            ],
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_does_not_auto_activate_web_for_conversational_confirmations_without_manual_flag(self) -> None:
        messages = (
            "Tu peux confirmer que tu m'entends ?",
            'Peux-tu confirmer que tu as compris ?',
            'Merci de confirmer la reception.',
        )

        for message in messages:
            with self.subTest(message=message):
                observed = {'web_input': None, 'prompt_messages': None, 'build_context_calls': 0}
                conversation = {
                    'id': 'conv-web-confirm-phase14',
                    'created_at': '2026-03-26T00:00:00Z',
                    'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
                }

                class FakeResponse:
                    def raise_for_status(self):
                        return None

                    def json(self):
                        return {'choices': [{'message': {'content': 'ok confirm'}}]}

                def fake_requests_post(*_args, **_kwargs):
                    return FakeResponse()

                observed_state, restore = self._patch_chat_pipeline(
                    conversation=conversation,
                    requests_post=fake_requests_post,
                )
                original_build_context_payload = self.server.ws.build_context_payload
                original_build_context = self.server.ws.build_context
                original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
                original_build_payload = self.server.llm.build_payload
                original_build_prompt_messages = self.server.conv_store.build_prompt_messages

                def unexpected_build_context_payload(_user_msg, **_kwargs):
                    observed['build_context_calls'] += 1
                    raise AssertionError('auto web should not run on conversational confirmations')

                def fake_insertion(**kwargs):
                    observed['web_input'] = kwargs.get('web_input')
                    return None

                def fake_build_payload(messages, _temperature, _top_p, max_tokens, stream=False):
                    observed['prompt_messages'] = messages
                    return {
                        'model': 'openrouter/runtime-main-model',
                        'messages': messages,
                        'max_tokens': max_tokens,
                        'stream': stream,
                    }

                self.server.ws.build_context_payload = unexpected_build_context_payload
                self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
                    AssertionError('legacy build_context should not be called')
                )
                self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
                self.server.llm.build_payload = fake_build_payload
                self.server.conv_store.build_prompt_messages = (
                    lambda conversation_arg, *_args, **_kwargs: [
                        {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                        {'role': 'user', 'content': message},
                    ]
                )
                try:
                    response = self.client.post(
                        '/api/chat',
                        json={'message': message, 'web_search': False},
                    )
                finally:
                    self.server.ws.build_context_payload = original_build_context_payload
                    self.server.ws.build_context = original_build_context
                    self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
                    self.server.llm.build_payload = original_build_payload
                    self.server.conv_store.build_prompt_messages = original_build_prompt_messages
                    restore()

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['ok'])
                self.assertEqual(observed['build_context_calls'], 0)
                self.assertFalse(observed['web_input']['enabled'])
                self.assertEqual(observed['web_input']['status'], 'skipped')
                self.assertEqual(observed['web_input']['activation_mode'], 'not_requested')
                self.assertEqual(observed['web_input']['reason_code'], 'not_applicable')
                self.assertEqual(
                    observed['prompt_messages'],
                    [
                        {'role': 'system', 'content': conversation['messages'][0]['content']},
                        {'role': 'user', 'content': message},
                    ],
                )
                self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_does_not_auto_activate_web_for_clean_conceptual_turn_without_manual_flag(self) -> None:
        observed = {'web_input': None, 'prompt_messages': None, 'build_context_calls': 0}
        conversation = {
            'id': 'conv-web-not-requested-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok no auto web'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point
        original_build_payload = self.server.llm.build_payload
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages

        def unexpected_build_context_payload(_user_msg, **_kwargs):
            observed['build_context_calls'] += 1
            raise AssertionError('auto web should not run on cleaned conceptual turn')

        def fake_insertion(**kwargs):
            observed['web_input'] = kwargs.get('web_input')
            return None

        def fake_build_payload(messages, _temperature, _top_p, max_tokens, stream=False):
            observed['prompt_messages'] = messages
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': messages,
                'max_tokens': max_tokens,
                'stream': stream,
            }

        self.server.ws.build_context_payload = unexpected_build_context_payload
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = fake_insertion
        self.server.llm.build_payload = fake_build_payload
        self.server.conv_store.build_prompt_messages = (
            lambda conversation_arg, *_args, **_kwargs: [
                {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
                {
                    'role': 'user',
                    'content': (
                        "Comment comprendre le lien a l'autre quand ce passage demande de faire preuve "
                        "de patience dans une lecture atemporelle ?"
                    ),
                },
            ]
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': (
                        "Comment comprendre le lien a l'autre quand ce passage demande de faire preuve "
                        "de patience dans une lecture atemporelle ?"
                    ),
                    'web_search': False,
                },
            )
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            self.server.llm.build_payload = original_build_payload
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['build_context_calls'], 0)
        self.assertFalse(observed['web_input']['enabled'])
        self.assertEqual(observed['web_input']['status'], 'skipped')
        self.assertEqual(observed['web_input']['activation_mode'], 'not_requested')
        self.assertEqual(observed['web_input']['reason_code'], 'not_applicable')
        self.assertEqual(
            observed['prompt_messages'][1]['content'],
            "Comment comprendre le lien a l'autre quand ce passage demande de faire preuve de patience dans une lecture atemporelle ?",
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_manual_web_no_data_keeps_external_verification_path_honest(self) -> None:
        observed = {'web_input': None, 'primary_payload': None}
        conversation = {
            'id': 'conv-web-auto-no-data-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok no data'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insertion = self.server.chat_service._run_hermeneutic_node_insertion_point

        def fake_build_context_payload(_user_msg, **_kwargs):
            return {
                'enabled': True,
                'status': 'skipped',
                'reason_code': 'no_data',
                'original_user_message': 'Donne-moi la source de cette affirmation.',
                'query': 'source test',
                'results_count': 0,
                'runtime': {},
                'sources': [],
                'context_block': '',
            }

        def capture_insertion(**kwargs):
            observed['web_input'] = kwargs.get('web_input')
            result = original_insertion(**kwargs)
            observed['primary_payload'] = result['primary_payload']
            return result

        self.server.ws.build_context_payload = fake_build_context_payload
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_service._run_hermeneutic_node_insertion_point = capture_insertion
        try:
            response = self.client.post(
                '/api/chat',
                json={'message': 'Donne-moi la source de cette affirmation.', 'web_search': True},
            )
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_service._run_hermeneutic_node_insertion_point = original_insertion
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(observed['web_input']['activation_mode'], 'manual')
        self.assertEqual(observed['web_input']['status'], 'skipped')
        self.assertEqual(observed['web_input']['reason_code'], 'no_data')
        self.assertEqual(observed['primary_payload']['primary_verdict']['proof_regime'], 'verification_externe_requise')
        self.assertEqual(observed['primary_payload']['primary_verdict']['judgment_posture'], 'suspend')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_injects_runtime_derived_web_reading_guard_into_system_prompt(self) -> None:
        conversation = {
            'id': 'conv-web-guard-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web guard'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_build_prompt_messages = self.server.conv_store.build_prompt_messages
        self.server.ws.build_context_payload = lambda _user_msg, **_kwargs: {
            'enabled': True,
            'status': 'ok',
            'reason_code': None,
            'original_user_message': 'Bonjour',
            'query': 'query test',
            'results_count': 1,
            'explicit_url_detected': True,
            'explicit_url': 'https://example.com/article',
            'read_state': 'page_not_read_snippet_fallback',
            'primary_source_kind': 'explicit_url',
            'primary_read_attempted': True,
            'primary_read_status': 'empty',
            'primary_read_filter': 'raw',
            'primary_read_raw_fallback_used': True,
            'fallback_used': True,
            'collection_path': 'explicit_url_fallback_search',
            'runtime': {
                'searxng_results': 5,
                'crawl4ai_top_n': 2,
                'crawl4ai_max_chars': 1500,
            },
            'sources': [
                {
                    'rank': 1,
                    'title': 'Titre source',
                    'url': 'https://example.com/article',
                    'source_domain': 'example.com',
                    'search_snippet': 'Snippet source',
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'content_used': 'Snippet source',
                    'truncated': False,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'crawl_status': 'empty',
                }
            ],
            'context_block': 'WEB CONTEXT',
        }
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.conv_store.build_prompt_messages = lambda conversation_arg, *_args, **_kwargs: [
            {'role': 'system', 'content': conversation_arg['messages'][0]['content']},
            {'role': 'user', 'content': 'Bonjour'},
        ]
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'web_search': True})
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.conv_store.build_prompt_messages = original_build_prompt_messages
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        prompt_messages = observed_state['payload_messages']
        self.assertEqual(prompt_messages[0]['role'], 'system')
        self.assertIn('[GARDE DE LECTURE WEB]', prompt_messages[0]['content'])
        self.assertIn('[CONTRAT TEXTE BRUT]', prompt_messages[0]['content'])
        self.assertIn("n'utilise ni puces, ni listes numérotées", prompt_messages[0]['content'])
        self.assertIn("n'utilise pas de code fences", prompt_messages[0]['content'])
        self.assertIn('read_state: page_not_read_snippet_fallback.', prompt_messages[0]['content'])
        self.assertIn("La page cible n'a pas ete lue directement.", prompt_messages[0]['content'])
        self.assertIn("je l'ai sous les yeux", prompt_messages[0]['content'])
        self.assertEqual(prompt_messages[1]['role'], 'user')
        self.assertEqual(prompt_messages[1]['content'], 'WEB CONTEXT\n\nQuestion : Bonjour')

    def test_api_chat_passes_web_input_read_state_to_identity_write_callback(self) -> None:
        observed = {'identity_call': None}
        conversation = {
            'id': 'conv-web-memory-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web memory'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_record_identity = self.server.chat_service._record_identity_entries_for_mode
        self.server.ws.build_context_payload = lambda _user_msg, **_kwargs: {
            'enabled': True,
            'status': 'ok',
            'reason_code': None,
            'original_user_message': 'Bonjour',
            'query': 'query test',
            'results_count': 1,
            'explicit_url_detected': True,
            'explicit_url': 'https://example.com/article',
            'read_state': 'page_not_read_snippet_fallback',
            'primary_source_kind': 'explicit_url',
            'primary_read_attempted': True,
            'primary_read_status': 'empty',
            'primary_read_filter': 'raw',
            'primary_read_raw_fallback_used': True,
            'fallback_used': True,
            'collection_path': 'explicit_url_fallback_search',
            'runtime': {
                'searxng_results': 5,
                'crawl4ai_top_n': 2,
                'crawl4ai_max_chars': 1500,
            },
            'sources': [
                {
                    'rank': 1,
                    'title': 'Titre source',
                    'url': 'https://example.com/article',
                    'source_domain': 'example.com',
                    'search_snippet': 'Snippet source',
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'content_used': 'Snippet source',
                    'truncated': False,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'crawl_status': 'empty',
                }
            ],
            'context_block': 'WEB CONTEXT',
        }
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_service._record_identity_entries_for_mode = (
            lambda conversation_id, recent_turns, mode, **kwargs: observed.update(
                {
                    'identity_call': {
                        'conversation_id': conversation_id,
                        'recent_turns': list(recent_turns),
                        'mode': mode,
                        'web_input': kwargs.get('web_input'),
                    }
                }
            )
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'web_search': True})
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_service._record_identity_entries_for_mode = original_record_identity
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertIsNotNone(observed['identity_call'])
        self.assertEqual(observed['identity_call']['conversation_id'], 'conv-web-memory-phase14')
        self.assertEqual(observed['identity_call']['mode'], 'enforced_all')
        self.assertEqual(
            observed['identity_call']['web_input']['read_state'],
            'page_not_read_snippet_fallback',
        )
        self.assertTrue(observed['identity_call']['web_input']['explicit_url_detected'])
        self.assertEqual(
            observed['identity_call']['web_input']['sources'][0]['source_origin'],
            'explicit_url',
        )
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_hermeneutic_node_insertion_observability_payload(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-observability-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok observability'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        payload = event['payload_json']
        self.assertEqual(event['status'], 'ok')
        self.assertTrue(payload['insertion_point_reached'])
        self.assertEqual(payload['mode'], str(self.server.config.HERMENEUTIC_MODE))
        self.assertTrue(payload['inputs']['time']['present'])
        self.assertEqual(payload['inputs']['time']['timezone'], str(self.server.config.FRIDA_TIMEZONE))
        self.assertTrue(payload['inputs']['time']['day_part_class'])
        self.assertEqual(payload['inputs']['memory_retrieved']['retrieved_count'], 0)
        self.assertEqual(payload['inputs']['memory_arbitration']['status'], 'skipped')
        self.assertEqual(payload['inputs']['memory_arbitration']['decisions_count'], 0)
        self.assertEqual(payload['inputs']['summary']['status'], 'missing')
        self.assertFalse(payload['inputs']['identity']['frida']['mutable_present'])
        self.assertFalse(payload['inputs']['identity']['user']['mutable_present'])
        self.assertEqual(payload['inputs']['recent_context']['messages_count'], 1)
        self.assertEqual(payload['inputs']['recent_window']['turn_count'], 1)
        self.assertTrue(payload['inputs']['recent_window']['has_in_progress_turn'])
        self.assertEqual(payload['inputs']['recent_window']['max_recent_turns'], 5)
        self.assertTrue(payload['inputs']['user_turn']['present'])
        self.assertEqual(payload['inputs']['user_turn']['geste_dialogique_dominant'], 'adresse_relationnelle')
        self.assertEqual(
            payload['inputs']['user_turn']['regime_probatoire'],
            {
                'principe': 'maximal_possible',
                'types_de_preuve_attendus': [],
                'provenances': [],
                'regime_de_vigilance': 'standard',
            },
        )
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
        self.assertNotIn('content', payload['inputs']['user_turn'])
        self.assertTrue(payload['inputs']['user_turn_signals']['present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['ambiguity_present'])
        self.assertFalse(payload['inputs']['user_turn_signals']['underdetermination_present'])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families'], [])
        self.assertEqual(payload['inputs']['user_turn_signals']['active_signal_families_count'], 0)
        self.assertTrue(payload['inputs']['stimmung']['present'])
        self.assertEqual(payload['inputs']['stimmung']['dominant_tone'], 'neutralite')
        self.assertEqual(payload['inputs']['stimmung']['active_tones'], [{'tone': 'neutralite', 'strength': 3}])
        self.assertEqual(payload['inputs']['stimmung']['stability'], 'emerging')
        self.assertEqual(payload['inputs']['stimmung']['shift_state'], 'steady')
        self.assertEqual(payload['inputs']['stimmung']['turns_considered'], 1)
        self.assertFalse(payload['inputs']['web']['enabled'])
        self.assertEqual(payload['inputs']['web']['status'], 'skipped')
        self.assertEqual(payload['inputs']['web']['activation_mode'], 'not_requested')
        self.assertEqual(payload['inputs']['web']['reason_code'], 'not_applicable')
        self.assertEqual(payload['inputs']['web']['results_count'], 0)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_prompt_prepared_memory_prompt_injection_without_raw_content(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-prompt-injection-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok prompt injection'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        prompt_event = next(item for item in observed_events if item['stage'] == 'prompt_prepared')
        payload = prompt_event['payload_json']
        self.assertEqual(payload['prompt_kind'], 'chat_system_augmented')
        self.assertEqual(payload['messages_count'], 1)
        self.assertEqual(payload['memory_items_used'], 0)
        self.assertEqual(
            payload['memory_prompt_injection'],
            {
                'injected': False,
                'prompt_block_count': 0,
                'memory_traces_injected': False,
                'memory_traces_injected_count': 0,
                'injected_candidate_ids': [],
                'memory_context_injected': False,
                'memory_context_summary_count': 0,
                'context_hints_injected': False,
                'context_hints_injected_count': 0,
            },
        )
        self.assertNotIn('messages', payload)
        self.assertNotIn('prompt', payload)
        self.assertNotIn('content', payload)
        self.assertNotIn('memory_traces', payload)
        self.assertNotIn('context_hints', payload)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_web_observability_payload_without_raw_web_content(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-web-observability-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok web observability'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_build_context_payload = self.server.ws.build_context_payload
        original_build_context = self.server.ws.build_context
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.ws.build_context_payload = lambda _user_msg, **_kwargs: {
            'enabled': True,
            'status': 'ok',
            'reason_code': None,
            'original_user_message': 'Bonjour',
            'query': 'query test',
            'results_count': 2,
            'explicit_url_detected': True,
            'explicit_url': 'https://example.com/article',
            'read_state': 'page_not_read_snippet_fallback',
            'primary_source_kind': 'explicit_url',
            'primary_read_attempted': True,
            'primary_read_status': 'empty',
            'primary_read_filter': 'raw',
            'primary_read_raw_fallback_used': True,
            'fallback_used': True,
            'collection_path': 'explicit_url_fallback_search',
            'runtime': {
                'searxng_results': 5,
                'crawl4ai_top_n': 2,
                'crawl4ai_max_chars': 1500,
            },
            'used_content_kinds': ['search_snippet'],
            'injected_chars': len('Snippet fallback'),
            'context_chars': len('WEB CONTEXT'),
            'source_material_summary': [
                {
                    'rank': 1,
                    'url': 'https://example.com/article',
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                },
                {
                    'rank': 2,
                    'url': 'https://fallback.example/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len('Snippet fallback'),
                    'truncated': False,
                },
            ],
            'sources': [
                {
                    'rank': 1,
                    'title': 'URL explicite utilisateur',
                    'url': 'https://example.com/article',
                    'source_domain': 'example.com',
                    'search_snippet': '',
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'content_used': '',
                    'truncated': False,
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'crawl_status': 'empty',
                },
                {
                    'rank': 2,
                    'title': 'Titre fallback',
                    'url': 'https://fallback.example/article',
                    'source_domain': 'fallback.example',
                    'search_snippet': 'Snippet fallback',
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'content_used': 'Snippet fallback',
                    'truncated': False,
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'crawl_status': 'not_attempted',
                },
            ],
            'context_block': 'WEB CONTEXT',
        }
        self.server.ws.build_context = lambda _user_msg: (_ for _ in ()).throw(
            AssertionError('legacy build_context should not be called')
        )
        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'web_search': True})
        finally:
            self.server.ws.build_context_payload = original_build_context_payload
            self.server.ws.build_context = original_build_context
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])

        insertion_event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        web_payload = insertion_event['payload_json']['inputs']['web']
        self.assertTrue(web_payload['enabled'])
        self.assertEqual(web_payload['status'], 'ok')
        self.assertEqual(web_payload['activation_mode'], 'manual')
        self.assertEqual(web_payload['reason_code'], '')
        self.assertEqual(web_payload['results_count'], 2)
        self.assertTrue(web_payload['explicit_url_detected'])
        self.assertEqual(web_payload['explicit_url'], 'https://example.com/article')
        self.assertEqual(web_payload['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(web_payload['primary_read_status'], 'empty')
        self.assertEqual(web_payload['primary_read_filter'], 'raw')
        self.assertTrue(web_payload['primary_read_raw_fallback_used'])
        self.assertTrue(web_payload['fallback_used'])
        self.assertEqual(web_payload['collection_path'], 'explicit_url_fallback_search')
        self.assertEqual(web_payload['used_content_kinds'], ['search_snippet'])
        self.assertEqual(web_payload['injected_chars'], len('Snippet fallback'))
        self.assertEqual(web_payload['context_chars'], len('WEB CONTEXT'))
        self.assertEqual(
            web_payload['source_material_summary'],
            [
                {
                    'rank': 1,
                    'url': 'https://example.com/article',
                    'source_origin': 'explicit_url',
                    'is_primary_source': True,
                    'used_in_prompt': False,
                    'used_content_kind': 'none',
                    'crawl_status': 'empty',
                    'content_chars': 0,
                    'truncated': False,
                },
                {
                    'rank': 2,
                    'url': 'https://fallback.example/article',
                    'source_origin': 'search_result',
                    'is_primary_source': False,
                    'used_in_prompt': True,
                    'used_content_kind': 'search_snippet',
                    'crawl_status': 'not_attempted',
                    'content_chars': len('Snippet fallback'),
                    'truncated': False,
                },
            ],
        )
        self.assertNotIn('context_block', web_payload)
        self.assertNotIn('sources', web_payload)
        self.assertNotIn('Snippet fallback', str(web_payload))
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_primary_node_and_validation_agent_synthetic_log_events(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-hermeneutic-stages-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok hermeneutic stages'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'judgment_posture': 'clarify',
                'source_conflicts': [{'kind': 'memory_conflict'}, {'kind': 'web_conflict'}],
                'audit': {'fail_open': False, 'state_used': True, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'clarify',
                    'final_judgment_posture': 'clarify',
                    'pipeline_directives_final': ['posture_clarify'],
                },
                status='ok',
                model='openai/gpt-5.4-mini',
                decision_source='primary',
                reason_code=None,
            )
        )

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        stages = [item['stage'] for item in observed_events]
        self.assertIn('stimmung_agent', stages)
        self.assertIn('hermeneutic_node_insertion', stages)
        self.assertIn('primary_node', stages)
        self.assertIn('validation_agent', stages)

        insertion_event = next(item for item in observed_events if item['stage'] == 'hermeneutic_node_insertion')
        self.assertEqual(
            insertion_event['payload_json']['inputs']['user_turn']['regime_probatoire'],
            {
                'principe': 'maximal_possible',
                'types_de_preuve_attendus': [],
                'provenances': [],
                'regime_de_vigilance': 'standard',
            },
        )
        self.assertNotIn('content', insertion_event['payload_json']['inputs']['user_turn'])

        primary_event = next(item for item in observed_events if item['stage'] == 'primary_node')
        self.assertEqual(primary_event['status'], 'ok')
        self.assertEqual(
            primary_event['payload_json'],
            {
                'judgment_posture': 'clarify',
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'source_conflicts_count': 2,
                'fail_open': False,
                'state_used': True,
                'degraded_fields_count': 0,
            },
        )

        validation_event = next(item for item in observed_events if item['stage'] == 'validation_agent')
        self.assertEqual(validation_event['status'], 'ok')
        self.assertEqual(
            validation_event['payload_json'],
            {
                'dialogue_messages_count': 1,
                'primary_judgment_posture': 'clarify',
                'validation_decision': 'clarify',
                'final_judgment_posture': 'clarify',
                'pipeline_directives_final': ['posture_clarify'],
                'decision_source': 'primary',
                'model': 'openai/gpt-5.4-mini',
            },
        )

        for payload in (primary_event['payload_json'], validation_event['payload_json']):
            self.assertNotIn('primary_verdict', payload)
            self.assertNotIn('validated_output', payload)
            self.assertNotIn('validation_dialogue_context', payload)
            self.assertNotIn('justifications', payload)
            self.assertNotIn('canonical_inputs', payload)
            self.assertNotIn('prompt', payload)
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_emits_validation_agent_error_stage_without_raw_payload_dump(self) -> None:
        observed_events: list[dict] = []
        conversation = {
            'id': 'conv-validation-error-stage-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok validation error stage'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_primary_node = self.server.chat_service.primary_node.build_primary_node
        original_validation_agent = self.server.chat_service.validation_agent.build_validated_output
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event

        self.server.chat_service.primary_node.build_primary_node = lambda **_kwargs: {
            'primary_verdict': {
                'schema_version': 'v1',
                'epistemic_regime': 'ouvert',
                'proof_regime': 'source_explicite_requise',
                'judgment_posture': 'answer',
                'source_conflicts': [],
                'audit': {'fail_open': False, 'state_used': False, 'degraded_fields': []},
            },
            'node_state': {'schema_version': 'v1'},
        }
        self.server.chat_service.validation_agent.build_validated_output = lambda **_kwargs: (
            self.server.chat_service.validation_agent.ValidationAgentResult(
                validated_output={
                    'schema_version': 'v1',
                    'validation_decision': 'suspend',
                    'final_judgment_posture': 'suspend',
                    'pipeline_directives_final': ['posture_suspend', 'fallback_validation'],
                },
                status='error',
                model='openai/gpt-5.4-nano',
                decision_source='fail_open',
                reason_code='timeout',
            )
        )

        def fake_insert(event, **_kwargs):
            observed_events.append(event)
            return True

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour'})
        finally:
            self.server.chat_service.primary_node.build_primary_node = original_primary_node
            self.server.chat_service.validation_agent.build_validated_output = original_validation_agent
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        validation_event = next(item for item in observed_events if item['stage'] == 'validation_agent')
        self.assertEqual(validation_event['status'], 'error')
        self.assertEqual(
            validation_event['payload_json'],
            {
                'dialogue_messages_count': 1,
                'primary_judgment_posture': 'answer',
                'validation_decision': 'suspend',
                'final_judgment_posture': 'suspend',
                'pipeline_directives_final': ['posture_suspend', 'fallback_validation'],
                'decision_source': 'fail_open',
                'reason_code': 'timeout',
                'model': 'openai/gpt-5.4-nano',
            },
        )
        self.assertNotIn('validation_dialogue_context', validation_event['payload_json'])
        self.assertNotIn('validated_output', validation_event['payload_json'])
        self.assertNotIn('primary_verdict', validation_event['payload_json'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_api_chat_keeps_contract_invalid_raw_conversation_id_creates_new_conversation(self) -> None:
        observed = {'normalized_raw': None, 'new_conversation_calls': 0, 'load_called': False}
        conversation = {
            'id': 'conv-invalid-raw-phase14',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {'choices': [{'message': {'content': 'ok phase14'}}]}

        def fake_requests_post(*_args, **_kwargs):
            return FakeResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        original_normalize = self.server.conv_store.normalize_conversation_id
        original_new_conversation = self.server.conv_store.new_conversation
        original_load_conversation = self.server.conv_store.load_conversation
        self.server.conv_store.normalize_conversation_id = lambda raw: observed.update({'normalized_raw': raw}) or None
        self.server.conv_store.new_conversation = (
            lambda _system: observed.update({'new_conversation_calls': observed['new_conversation_calls'] + 1}) or conversation
        )

        def fake_load_conversation(*_args, **_kwargs):
            observed['load_called'] = True
            return None

        self.server.conv_store.load_conversation = fake_load_conversation
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'conversation_id': '@@bad@@'})
        finally:
            self.server.conv_store.normalize_conversation_id = original_normalize
            self.server.conv_store.new_conversation = original_new_conversation
            self.server.conv_store.load_conversation = original_load_conversation
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        self.assertEqual(response.get_json()['conversation_id'], 'conv-invalid-raw-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Id'), 'conv-invalid-raw-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Created-At'), '2026-03-26T00:00:00Z')
        self.assertTrue(response.headers.get('X-Conversation-Updated-At'))
        self.assertEqual(observed['normalized_raw'], '@@bad@@')
        self.assertEqual(observed['new_conversation_calls'], 1)
        self.assertFalse(observed['load_called'])
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)


if __name__ == '__main__':
    unittest.main()
