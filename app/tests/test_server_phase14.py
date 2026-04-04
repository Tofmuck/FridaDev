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

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post):
        originals = []
        observed = {'save_calls': []}

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
            lambda conv, role, content, timestamp=None: conv['messages'].append(
                {'role': role, 'content': content, 'timestamp': timestamp}
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
                'schema_version': 'v1',
                'frida': {'static': {'content': '', 'source': None}, 'dynamic': []},
                'user': {'static': {'content': '', 'source': None}, 'dynamic': []},
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
        patch_attr(self.server.memory_store, 'save_new_traces', lambda *_args, **_kwargs: None)
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
        observed = {'stream_kw': None}
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
                yield 'data: [DONE]'

        def fake_requests_post(*_args, **kwargs):
            observed['stream_kw'] = kwargs.get('stream')
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content_type, 'text/plain; charset=utf-8')
        self.assertEqual(response.headers.get('X-Conversation-Id'), 'conv-stream-phase14')
        self.assertEqual(response.headers.get('X-Conversation-Created-At'), '2026-03-26T00:00:00Z')
        self.assertTrue(response.headers.get('X-Conversation-Updated-At'))
        self.assertEqual(response.get_data(as_text=True), 'Bonjour')
        self.assertTrue(observed['stream_kw'])
        self.assertEqual(
            observed_state['save_calls'][-1]['kwargs'].get('updated_at'),
            response.headers.get('X-Conversation-Updated-At'),
        )

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
            'schema_version': 'v1',
            'frida': {
                'static': {'content': 'Frida statique', 'source': '/runtime/llm_identity.txt'},
                'dynamic': [
                    {
                        'id': 'frida-dyn-1',
                        'content': 'Frida aime les raisonnements structurés',
                        'stability': 'durable',
                        'recurrence': 'habitual',
                        'confidence': 0.91,
                        'last_seen_ts': '2026-03-24T12:00:00Z',
                        'scope': 'llm',
                    }
                ],
            },
            'user': {
                'static': {'content': 'Utilisateur statique', 'source': '/runtime/user_identity.txt'},
                'dynamic': [
                    {
                        'id': 'user-dyn-1',
                        'content': 'Utilisateur prefere les réponses concises',
                        'stability': 'durable',
                        'recurrence': 'repeated',
                        'confidence': 0.88,
                        'last_seen_ts': '2026-03-25T09:30:00Z',
                        'scope': 'user',
                    }
                ],
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
        self.assertEqual(observed['identity_input']['schema_version'], 'v1')
        self.assertEqual(observed['identity_input']['frida']['static']['content'], 'Frida statique')
        self.assertEqual(observed['identity_input']['frida']['dynamic'][0]['id'], 'frida-dyn-1')
        self.assertEqual(observed['identity_input']['frida']['dynamic'][0]['scope'], 'llm')
        self.assertEqual(observed['identity_input']['user']['static']['content'], 'Utilisateur statique')
        self.assertEqual(observed['identity_input']['user']['dynamic'][0]['id'], 'user-dyn-1')
        self.assertEqual(observed['identity_input']['user']['dynamic'][0]['scope'], 'user')
        self.assertGreaterEqual(len(observed_state['save_calls']), 2)

    def test_identity_input_uses_same_effective_dynamic_selection_as_prompt_block(self) -> None:
        identity = self.server.identity
        originals = {
            'load_llm_identity': identity.load_llm_identity,
            'load_user_identity': identity.load_user_identity,
            '_safe_static_identity_source': identity._safe_static_identity_source,
            '_select_ranked_entries': identity._select_ranked_entries,
            '_estimate_tokens': identity._estimate_tokens,
            'identity_top_n': identity.config.IDENTITY_TOP_N,
            'identity_max_tokens': identity.config.IDENTITY_MAX_TOKENS,
        }
        ranked_entries = {
            'llm': [
                {
                    'id': 'frida-kept',
                    'content': 'Frida dynamique retenue',
                    'stability': 'durable',
                    'recurrence': 'habitual',
                    'confidence': 0.95,
                    'last_seen_ts': '2026-03-24T12:00:00Z',
                    'scope': 'llm',
                },
                {
                    'id': 'frida-dropped',
                    'content': 'Frida dynamique hors budget',
                    'stability': 'durable',
                    'recurrence': 'repeated',
                    'confidence': 0.90,
                    'last_seen_ts': '2026-03-23T10:00:00Z',
                    'scope': 'llm',
                },
            ],
            'user': [
                {
                    'id': 'user-kept',
                    'content': 'User dynamique retenue',
                    'stability': 'durable',
                    'recurrence': 'repeated',
                    'confidence': 0.88,
                    'last_seen_ts': '2026-03-25T09:30:00Z',
                    'scope': 'user',
                },
                {
                    'id': 'user-dropped',
                    'content': 'User dynamique hors budget',
                    'stability': 'durable',
                    'recurrence': 'repeated',
                    'confidence': 0.83,
                    'last_seen_ts': '2026-03-22T09:30:00Z',
                    'scope': 'user',
                },
            ],
        }

        identity.load_llm_identity = lambda: ''
        identity.load_user_identity = lambda: ''
        identity._safe_static_identity_source = lambda _field: None
        identity._select_ranked_entries = lambda subject: list(ranked_entries[subject])
        identity.config.IDENTITY_TOP_N = 2
        identity.config.IDENTITY_MAX_TOKENS = 4

        def fake_estimate_tokens(text: str) -> int:
            if not text:
                return 0
            if text.startswith('- ['):
                return 2
            return 0

        identity._estimate_tokens = fake_estimate_tokens
        try:
            block, used_ids = identity.build_identity_block()
            payload = identity.build_identity_input()
        finally:
            identity.load_llm_identity = originals['load_llm_identity']
            identity.load_user_identity = originals['load_user_identity']
            identity._safe_static_identity_source = originals['_safe_static_identity_source']
            identity._select_ranked_entries = originals['_select_ranked_entries']
            identity._estimate_tokens = originals['_estimate_tokens']
            identity.config.IDENTITY_TOP_N = originals['identity_top_n']
            identity.config.IDENTITY_MAX_TOKENS = originals['identity_max_tokens']

        self.assertIn('Frida dynamique retenue', block)
        self.assertNotIn('Frida dynamique hors budget', block)
        self.assertIn('User dynamique retenue', block)
        self.assertNotIn('User dynamique hors budget', block)
        self.assertEqual(used_ids, ['frida-kept', 'user-kept'])
        self.assertEqual(
            [entry['id'] for entry in payload['frida']['dynamic']],
            ['frida-kept'],
        )
        self.assertEqual(
            [entry['id'] for entry in payload['user']['dynamic']],
            ['user-kept'],
        )

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
        self.server.ws.build_context_payload = lambda _user_msg: {
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
        self.assertEqual(observed['web_input']['query'], 'query test')
        self.assertEqual(observed['web_input']['results_count'], 1)
        self.assertTrue(observed['web_input']['explicit_url_detected'])
        self.assertEqual(observed['web_input']['explicit_url'], 'https://example.com/article')
        self.assertEqual(observed['web_input']['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(observed['web_input']['primary_source_kind'], 'explicit_url')
        self.assertTrue(observed['web_input']['primary_read_attempted'])
        self.assertEqual(observed['web_input']['primary_read_status'], 'empty')
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
        self.server.ws.build_context_payload = lambda _user_msg: {
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
        self.server.ws.build_context_payload = lambda _user_msg: {
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
        self.assertEqual(payload['inputs']['identity']['frida']['dynamic_count'], 0)
        self.assertEqual(payload['inputs']['identity']['user']['dynamic_count'], 0)
        self.assertEqual(payload['inputs']['recent_context']['messages_count'], 1)
        self.assertEqual(payload['inputs']['recent_window']['turn_count'], 1)
        self.assertTrue(payload['inputs']['recent_window']['has_in_progress_turn'])
        self.assertEqual(payload['inputs']['recent_window']['max_recent_turns'], 5)
        self.assertTrue(payload['inputs']['user_turn']['present'])
        self.assertEqual(payload['inputs']['user_turn']['geste_dialogique_dominant'], 'adresse_relationnelle')
        self.assertEqual(payload['inputs']['user_turn']['regime_probatoire']['principe'], 'maximal_possible')
        self.assertEqual(payload['inputs']['user_turn']['regime_probatoire']['types_de_preuve_attendus'], [])
        self.assertEqual(payload['inputs']['user_turn']['regime_probatoire']['regime_de_vigilance'], 'standard')
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['portee_temporelle'], 'atemporale')
        self.assertEqual(payload['inputs']['user_turn']['qualification_temporelle']['ancrage_temporel'], 'non_ancre')
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
        self.assertEqual(payload['inputs']['web']['results_count'], 0)
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

        self.server.ws.build_context_payload = lambda _user_msg: {
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
        self.assertEqual(web_payload['results_count'], 2)
        self.assertTrue(web_payload['explicit_url_detected'])
        self.assertEqual(web_payload['explicit_url'], 'https://example.com/article')
        self.assertEqual(web_payload['read_state'], 'page_not_read_snippet_fallback')
        self.assertEqual(web_payload['primary_read_status'], 'empty')
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
