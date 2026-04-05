from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class ServerLogsPhase3Tests(unittest.TestCase):
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
        self._original_admin_token = self.server.config.FRIDA_ADMIN_TOKEN
        self._original_admin_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY

    def tearDown(self) -> None:
        self.server.config.FRIDA_ADMIN_TOKEN = self._original_admin_token
        self.server.config.FRIDA_ADMIN_LAN_ONLY = self._original_admin_lan_only

    def test_admin_chat_logs_route_returns_paginated_payload(self) -> None:
        observed = {'kwargs': None}
        original_read = self.server.log_store.read_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'items': [
                    {
                        'event_id': 'evt-1',
                        'conversation_id': 'conv-1',
                        'turn_id': 'turn-1',
                        'ts': '2026-03-27T12:00:00+00:00',
                        'stage': 'turn_start',
                        'status': 'ok',
                        'duration_ms': None,
                        'payload': {'web_search_enabled': False},
                    }
                ],
                'count': 1,
                'total': 4,
                'limit': 1,
                'offset': 0,
                'next_offset': 1,
                'filters': {
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'stage': 'turn_start',
                    'status': 'ok',
                    'ts_from': '2026-03-27T11:00:00Z',
                    'ts_to': '2026-03-27T13:00:00Z',
                },
            }

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            response = self.client.get(
                '/api/admin/logs/chat?limit=1&offset=0'
                '&conversation_id=conv-1&turn_id=turn-1&stage=turn_start&status=ok'
                '&ts_from=2026-03-27T11:00:00Z&ts_to=2026-03-27T13:00:00Z'
            )
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['total'], 4)
        self.assertEqual(data['limit'], 1)
        self.assertEqual(data['offset'], 0)
        self.assertEqual(data['next_offset'], 1)
        self.assertEqual(data['filters']['conversation_id'], 'conv-1')
        self.assertEqual(data['items'][0]['event_id'], 'evt-1')
        self.assertEqual(observed['kwargs']['limit'], 1)
        self.assertEqual(observed['kwargs']['offset'], 0)
        self.assertEqual(observed['kwargs']['conversation_id'], 'conv-1')
        self.assertEqual(observed['kwargs']['turn_id'], 'turn-1')
        self.assertEqual(observed['kwargs']['stage'], 'turn_start')
        self.assertEqual(observed['kwargs']['status'], 'ok')
        self.assertEqual(observed['kwargs']['ts_from'], '2026-03-27T11:00:00Z')
        self.assertEqual(observed['kwargs']['ts_to'], '2026-03-27T13:00:00Z')

    def test_admin_chat_logs_metadata_route_returns_selector_payload(self) -> None:
        observed = {'kwargs': None}
        original_read_metadata = self.server.log_store.read_chat_log_metadata

        def fake_read_chat_log_metadata(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'selected_conversation_id': 'conv-1',
                'conversations': [
                    {
                        'conversation_id': 'conv-1',
                        'last_ts': '2026-03-27T12:01:00+00:00',
                        'events_count': 2,
                    },
                    {
                        'conversation_id': 'conv-2',
                        'last_ts': '2026-03-27T11:58:00+00:00',
                        'events_count': 1,
                    },
                ],
                'turns': [
                    {
                        'turn_id': 'turn-1',
                        'last_ts': '2026-03-27T12:01:00+00:00',
                        'events_count': 2,
                    }
                ],
            }

        self.server.log_store.read_chat_log_metadata = fake_read_chat_log_metadata
        try:
            response = self.client.get('/api/admin/logs/chat/metadata?conversation_id=conv-1')
        finally:
            self.server.log_store.read_chat_log_metadata = original_read_metadata

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['selected_conversation_id'], 'conv-1')
        self.assertEqual(len(data['conversations']), 2)
        self.assertEqual(data['conversations'][0]['conversation_id'], 'conv-1')
        self.assertEqual(data['turns'][0]['turn_id'], 'turn-1')
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1'})

    def test_admin_chat_logs_metadata_route_respects_admin_token_guard(self) -> None:
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase3-token'

        response_missing = self.client.get('/api/admin/logs/chat/metadata')
        self.assertEqual(response_missing.status_code, 401)

        original_read_metadata = self.server.log_store.read_chat_log_metadata
        self.server.log_store.read_chat_log_metadata = (
            lambda **_kwargs: {
                'selected_conversation_id': None,
                'conversations': [],
                'turns': [],
            }
        )
        try:
            response_ok = self.client.get(
                '/api/admin/logs/chat/metadata',
                headers={'X-Admin-Token': 'phase3-token'},
            )
        finally:
            self.server.log_store.read_chat_log_metadata = original_read_metadata

        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.get_json()['ok'])

    def test_admin_chat_logs_route_rejects_invalid_pagination(self) -> None:
        response = self.client.get('/api/admin/logs/chat?limit=abc&offset=0')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid pagination parameters'})

    def test_admin_chat_logs_route_rejects_invalid_status_filter(self) -> None:
        original_read = self.server.log_store.read_chat_log_events
        self.server.log_store.read_chat_log_events = (
            lambda **_kwargs: (_ for _ in ()).throw(ValueError('invalid chat log status filter: broken'))
        )
        try:
            response = self.client.get('/api/admin/logs/chat?status=broken')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid chat log status filter: broken'})

    def test_admin_chat_logs_route_rejects_invalid_ts_from(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_from=not-a-date')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid ts_from timestamp: not-a-date'})

    def test_admin_chat_logs_route_rejects_invalid_ts_to(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_to=not-a-date')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid ts_to timestamp: not-a-date'})

    def test_admin_chat_logs_route_respects_admin_token_guard(self) -> None:
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase3-token'

        response_missing = self.client.get('/api/admin/logs/chat?limit=1')
        self.assertEqual(response_missing.status_code, 401)

        original_read = self.server.log_store.read_chat_log_events
        self.server.log_store.read_chat_log_events = (
            lambda **_kwargs: {
                'items': [],
                'count': 0,
                'total': 0,
                'limit': 1,
                'offset': 0,
                'next_offset': None,
                'filters': {
                    'conversation_id': None,
                    'turn_id': None,
                    'stage': None,
                    'status': None,
                    'ts_from': None,
                    'ts_to': None,
                },
            }
        )
        try:
            response_ok = self.client.get('/api/admin/logs/chat?limit=1', headers={'X-Admin-Token': 'phase3-token'})
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.get_json()['ok'])

    def test_llm_proxy_emits_prompt_prepared_with_expected_prompt_kind(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-prompt-kind',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._LlmChatLogProxy(
                base_module=SimpleNamespace(
                    build_payload=lambda messages, temperature, top_p, max_tokens, stream=False: {
                        'model': 'openrouter/runtime-main-model',
                        'messages': messages,
                        'temperature': temperature,
                        'top_p': top_p,
                        'max_tokens': max_tokens,
                        'stream': stream,
                    }
                ),
                token_utils_module=SimpleNamespace(estimate_tokens=lambda _messages, _model: 321),
            )
            payload = proxy.build_payload(
                [{'role': 'user', 'content': 'bonjour'}],
                0.7,
                0.9,
                400,
                stream=False,
            )
            self.assertEqual(payload['model'], 'openrouter/runtime-main-model')
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        prompt_events = [event for event in observed if event.get('stage') == 'prompt_prepared']
        self.assertEqual(len(prompt_events), 1)
        prompt_payload = prompt_events[0]['payload_json']
        self.assertEqual(prompt_payload.get('prompt_kind'), 'chat_system_augmented')
        self.assertIn(prompt_payload.get('prompt_kind'), {'chat_system_augmented', 'chat_web_reformulation'})
        self.assertEqual(prompt_payload.get('messages_count'), 1)
        self.assertEqual(prompt_payload.get('estimated_prompt_tokens'), 321)
        self.assertNotIn('messages', prompt_payload)
        self.assertNotIn('prompt', prompt_payload)
        self.assertNotIn('content', prompt_payload)

    def test_requests_proxy_non_stream_llm_call_keeps_response_chars(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        class FakeJsonResponse:
            def json(self) -> dict[str, object]:
                return {
                    'id': 'gen-sync',
                    'model': 'openrouter/runtime-main-model',
                    'usage': {
                        'prompt_tokens': 12,
                        'completion_tokens': 5,
                        'total_tokens': 17,
                    },
                    'choices': [
                        {'message': {'content': 'reponse finale'}},
                    ]
                }

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-llm-json',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._RequestsChatLogProxy(
                base_module=SimpleNamespace(post=lambda *_args, **_kwargs: FakeJsonResponse()),
            )
            proxy.post(
                'https://openrouter.example/chat/completions',
                json={'model': 'openrouter/runtime-main-model'},
                headers={'X-OpenRouter-Title': 'FridaDev/LLM'},
                timeout=30,
                stream=False,
            )
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        llm_events = [event for event in observed if event.get('stage') == 'llm_call']
        self.assertEqual(len(llm_events), 1)
        payload = llm_events[0]['payload_json']
        self.assertEqual(payload.get('mode'), 'json')
        self.assertEqual(payload.get('response_chars'), len('reponse finale'))
        self.assertEqual(payload.get('model'), 'openrouter/runtime-main-model')
        self.assertEqual(payload.get('provider_caller'), 'llm')
        self.assertEqual(payload.get('provider_title'), 'FridaDev/LLM')
        self.assertEqual(payload.get('provider_generation_id'), 'gen-sync')
        self.assertEqual(payload.get('provider_prompt_tokens'), 12)
        self.assertEqual(payload.get('provider_completion_tokens'), 5)
        self.assertEqual(payload.get('provider_total_tokens'), 17)
        self.assertNotIn('content', payload)
        self.assertNotIn('response_text', payload)

    def test_requests_proxy_non_stream_validation_agent_uses_title_fallback_for_provider_identity(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        class FakeJsonResponse:
            def json(self) -> dict[str, object]:
                return {
                    'id': 'gen-validation',
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {
                        'prompt_tokens': 10,
                        'completion_tokens': 2,
                        'total_tokens': 12,
                    },
                    'choices': [
                        {'message': {'content': 'ok'}},
                    ],
                }

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-validation-json',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._RequestsChatLogProxy(
                base_module=SimpleNamespace(post=lambda *_args, **_kwargs: FakeJsonResponse()),
            )
            proxy.post(
                'https://openrouter.example/chat/completions',
                json={'model': 'openai/gpt-5.4-mini'},
                headers={'X-Title': 'FridaDev/ValidationAgent'},
                timeout=30,
                stream=False,
            )
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        llm_events = [event for event in observed if event.get('stage') == 'llm_call']
        self.assertEqual(len(llm_events), 1)
        payload = llm_events[0]['payload_json']
        self.assertEqual(payload.get('provider_caller'), 'validation_agent')
        self.assertEqual(payload.get('provider_title'), 'FridaDev/ValidationAgent')
        self.assertEqual(payload.get('provider_generation_id'), 'gen-validation')
        self.assertEqual(payload.get('provider_total_tokens'), 12)

    def test_requests_proxy_non_stream_web_reformulation_uses_dedicated_provider_identity(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        class FakeJsonResponse:
            def json(self) -> dict[str, object]:
                return {
                    'id': 'gen-web-reformulation',
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {
                        'prompt_tokens': 9,
                        'completion_tokens': 3,
                        'total_tokens': 12,
                    },
                    'choices': [
                        {'message': {'content': 'requete reformulee'}},
                    ],
                }

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-web-reformulation-json',
            user_msg='bonjour',
            web_search_enabled=True,
        )
        try:
            proxy = self.server._RequestsChatLogProxy(
                base_module=SimpleNamespace(post=lambda *_args, **_kwargs: FakeJsonResponse()),
            )
            proxy.post(
                'https://openrouter.example/chat/completions',
                json={'model': 'openai/gpt-5.4-mini'},
                headers=self.server.llm.or_headers(caller='web_reformulation'),
                timeout=30,
                stream=False,
            )
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        llm_events = [event for event in observed if event.get('stage') == 'llm_call']
        self.assertEqual(len(llm_events), 1)
        payload = llm_events[0]['payload_json']
        self.assertEqual(payload.get('provider_caller'), 'web_reformulation')
        self.assertEqual(payload.get('provider_title'), self.server.config.OR_TITLE_WEB_REFORMULATION)
        self.assertEqual(payload.get('provider_generation_id'), 'gen-web-reformulation')
        self.assertEqual(payload.get('provider_total_tokens'), 12)

    def test_requests_proxy_strips_internal_caller_header_before_upstream_request(self) -> None:
        observed: list[dict[str, object]] = []
        forwarded_headers: dict[str, object] = {}
        original_insert = self.server.log_store.insert_chat_log_event

        class FakeJsonResponse:
            def json(self) -> dict[str, object]:
                return {
                    'id': 'gen-stimmung',
                    'model': 'openai/gpt-5.4-mini',
                    'usage': {
                        'prompt_tokens': 11,
                        'completion_tokens': 3,
                        'total_tokens': 14,
                    },
                    'choices': [
                        {'message': {'content': 'ok'}},
                    ],
                }

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        def fake_post(*_args, **kwargs):
            forwarded_headers.update(dict(kwargs.get('headers') or {}))
            return FakeJsonResponse()

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-stimmung-json',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._RequestsChatLogProxy(
                base_module=SimpleNamespace(post=fake_post),
            )
            proxy.post(
                'https://openrouter.example/chat/completions',
                json={'model': 'openai/gpt-5.4-mini'},
                headers={
                    self.server.llm.INTERNAL_PROVIDER_CALLER_HEADER: 'stimmung_agent',
                    'X-Title': 'FridaDev/StimmungAgent',
                },
                timeout=30,
                stream=False,
            )
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        self.assertNotIn(self.server.llm.INTERNAL_PROVIDER_CALLER_HEADER, forwarded_headers)
        llm_events = [event for event in observed if event.get('stage') == 'llm_call']
        self.assertEqual(len(llm_events), 1)
        payload = llm_events[0]['payload_json']
        self.assertEqual(payload.get('provider_caller'), 'stimmung_agent')
        self.assertEqual(payload.get('provider_title'), 'FridaDev/StimmungAgent')

    def test_api_chat_stream_emits_llm_call_with_final_response_chars(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event
        original_chat_response = self.server.chat_service.chat_response

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        def fake_chat_response(*_args: object, **_kwargs: object) -> dict[str, object]:
            self.server.chat_turn_logger.set_state(
                'llm_stream_call_meta',
                {
                    'model': 'openrouter/runtime-main-model',
                    'timeout_s': 45,
                    'started_at': self.server.time.perf_counter() - 0.01,
                    'provider_caller': 'llm',
                    'provider_title': 'FridaDev/LLM',
                },
            )
            self.server.chat_turn_logger.set_state(
                'llm_provider_response_meta',
                {
                    'provider_caller': 'llm',
                    'provider_title': 'FridaDev/LLM',
                    'provider_generation_id': 'gen-stream',
                    'provider_model': 'openrouter/runtime-main-model',
                    'provider_prompt_tokens': 40,
                    'provider_completion_tokens': 2,
                    'provider_total_tokens': 42,
                },
            )

            def fake_stream():
                yield 'ab'
                yield 'cdef'

            return {
                'kind': 'stream',
                'stream': fake_stream(),
                'headers': {},
            }

        self.server.log_store.insert_chat_log_event = fake_insert
        self.server.chat_service.chat_response = fake_chat_response
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'bonjour',
                    'stream': True,
                    'conversation_id': 'conv-llm-stream',
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_data(as_text=True), 'abcdef')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert
            self.server.chat_service.chat_response = original_chat_response

        stream_llm_events = [
            event
            for event in observed
            if event.get('stage') == 'llm_call' and event['payload_json'].get('mode') == 'stream'
        ]
        self.assertEqual(len(stream_llm_events), 1)
        payload = stream_llm_events[0]['payload_json']
        self.assertEqual(payload.get('model'), 'openrouter/runtime-main-model')
        self.assertEqual(payload.get('timeout_s'), 45)
        self.assertEqual(payload.get('response_chars'), 6)
        self.assertEqual(payload.get('stream_chunks'), 2)
        self.assertEqual(payload.get('provider_caller'), 'llm')
        self.assertEqual(payload.get('provider_title'), 'FridaDev/LLM')
        self.assertEqual(payload.get('provider_generation_id'), 'gen-stream')
        self.assertEqual(payload.get('provider_prompt_tokens'), 40)
        self.assertEqual(payload.get('provider_completion_tokens'), 2)
        self.assertEqual(payload.get('provider_total_tokens'), 42)
        self.assertNotIn('content', payload)
        self.assertNotIn('response_text', payload)

    def test_api_chat_stream_counts_utf8_chars_when_multibyte_is_split_across_byte_chunks(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event
        original_chat_response = self.server.chat_service.chat_response

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        def fake_chat_response(*_args: object, **_kwargs: object) -> dict[str, object]:
            self.server.chat_turn_logger.set_state(
                'llm_stream_call_meta',
                {
                    'model': 'openrouter/runtime-main-model',
                    'timeout_s': 45,
                    'started_at': self.server.time.perf_counter() - 0.01,
                    'provider_caller': 'llm',
                    'provider_title': 'FridaDev/LLM',
                },
            )

            def fake_stream():
                # "é" is UTF-8 C3 A9, intentionally split across two chunks.
                yield b'ab\xc3'
                yield b'\xa9cd'

            return {
                'kind': 'stream',
                'stream': fake_stream(),
                'headers': {},
            }

        self.server.log_store.insert_chat_log_event = fake_insert
        self.server.chat_service.chat_response = fake_chat_response
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'bonjour',
                    'stream': True,
                    'conversation_id': 'conv-llm-stream-bytes',
                },
            )
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.get_data(as_text=True), 'abécd')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert
            self.server.chat_service.chat_response = original_chat_response

        stream_llm_events = [
            event
            for event in observed
            if event.get('stage') == 'llm_call' and event['payload_json'].get('mode') == 'stream'
        ]
        self.assertEqual(len(stream_llm_events), 1)
        payload = stream_llm_events[0]['payload_json']
        self.assertEqual(payload.get('response_chars'), 5)
        self.assertEqual(payload.get('stream_chunks'), 2)
        self.assertEqual(payload.get('provider_caller'), 'llm')
        self.assertEqual(payload.get('provider_title'), 'FridaDev/LLM')
        self.assertNotIn('content', payload)
        self.assertNotIn('response_text', payload)

    def test_build_prompt_messages_logs_summaries_as_prompt_injection_usage(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-summaries-used',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._ConvStoreChatLogProxy(
                base_module=SimpleNamespace(
                    build_prompt_messages=lambda conversation, model, **kwargs: [
                        {'role': 'system', 'content': '[Résumé actif] Memoire courte utile'},
                        {'role': 'user', 'content': 'bonjour'},
                    ]
                ),
                token_utils_module=SimpleNamespace(estimate_tokens=lambda _messages, _model: 42),
            )
            prompt_messages = proxy.build_prompt_messages(
                {'id': 'conv-summaries-used', 'messages': []},
                'openrouter/runtime-main-model',
                memory_traces=[],
            )
            self.assertEqual(len(prompt_messages), 2)
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        summaries_events = [event for event in observed if event.get('stage') == 'summaries']
        context_events = [event for event in observed if event.get('stage') == 'context_build']
        self.assertEqual(len(summaries_events), 1)
        self.assertEqual(len(context_events), 1)
        self.assertEqual(context_events[0]['payload_json'].get('estimated_context_tokens'), 42)
        self.assertNotIn('context_tokens', context_events[0]['payload_json'])
        summary_event = summaries_events[0]
        self.assertEqual(summary_event.get('status'), 'ok')
        payload = summary_event['payload_json']
        self.assertTrue(payload.get('active_summary_present'))
        self.assertEqual(payload.get('summary_count_used'), 1)
        self.assertEqual(payload.get('summary_usage'), 'prompt_injection')
        self.assertTrue(payload.get('in_prompt'))
        self.assertFalse(payload.get('summary_generation_observed'))
        self.assertNotIn('summary', payload)
        self.assertNotIn('summary_content', payload)
        self.assertNotIn('content', payload)
        self.assertNotIn('messages', payload)

    def test_build_prompt_messages_logs_summaries_skipped_when_no_active_summary(self) -> None:
        observed: list[dict[str, object]] = []
        original_insert = self.server.log_store.insert_chat_log_event

        def fake_insert(event: dict[str, object], **_kwargs: object) -> bool:
            observed.append(event)
            return True

        self.server.log_store.insert_chat_log_event = fake_insert
        token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-summaries-none',
            user_msg='bonjour',
            web_search_enabled=False,
        )
        try:
            proxy = self.server._ConvStoreChatLogProxy(
                base_module=SimpleNamespace(
                    build_prompt_messages=lambda conversation, model, **kwargs: [
                        {'role': 'system', 'content': '[Instruction] sans resume actif'},
                        {'role': 'user', 'content': 'bonjour'},
                    ]
                ),
                token_utils_module=SimpleNamespace(estimate_tokens=lambda _messages, _model: 7),
            )
            proxy.build_prompt_messages(
                {'id': 'conv-summaries-none', 'messages': []},
                'openrouter/runtime-main-model',
                memory_traces=[],
            )
            self.server.chat_turn_logger.end_turn(token, final_status='ok')
        finally:
            self.server.log_store.insert_chat_log_event = original_insert

        summaries_events = [event for event in observed if event.get('stage') == 'summaries']
        self.assertEqual(len(summaries_events), 1)
        summary_event = summaries_events[0]
        self.assertEqual(summary_event.get('status'), 'skipped')
        payload = summary_event['payload_json']
        self.assertFalse(payload.get('active_summary_present'))
        self.assertEqual(payload.get('summary_count_used'), 0)
        self.assertEqual(payload.get('summary_usage'), 'prompt_injection')
        self.assertFalse(payload.get('in_prompt'))
        self.assertFalse(payload.get('summary_generation_observed'))
        self.assertEqual(payload.get('reason_code'), 'no_data')

        branch_skipped_events = [event for event in observed if event.get('stage') == 'branch_skipped']
        self.assertEqual(len(branch_skipped_events), 1)
        self.assertEqual(branch_skipped_events[0]['payload_json'].get('reason_code'), 'no_data')
        self.assertEqual(
            branch_skipped_events[0]['payload_json'].get('reason_short'),
            'no_active_summary_in_prompt',
        )


if __name__ == '__main__':
    unittest.main()
