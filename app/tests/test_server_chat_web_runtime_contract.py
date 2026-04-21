from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatWebRuntimeContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=requests_post,
        )

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
        self.assertEqual(observed['primary_payload']['primary_verdict']['judgment_posture'], 'answer')
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


if __name__ == '__main__':
    unittest.main()
