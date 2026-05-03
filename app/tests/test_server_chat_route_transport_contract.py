from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_stream_control
from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatRouteTransportContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _split_stream_body(self, response) -> tuple[str, dict[str, str] | None]:
        return chat_stream_control.split_text_and_terminal(response.get_data())

    def _patch_chat_pipeline(self, *, conversation: dict, requests_post, **kwargs):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=requests_post,
            **kwargs,
        )

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
        observed = {'save_calls': [], 'save_attempts': 0}

        def raising_first_save(*_args, **kwargs):
            if not kwargs.get('updated_at'):
                return None
            observed['save_attempts'] += 1
            if observed['save_attempts'] == 1:
                raise RuntimeError('finalize boom')
            observed['save_calls'].append({'kwargs': dict(kwargs)})

        self.server.conv_store.save_conversation = raising_first_save
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
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
                'updated_at': observed['save_calls'][-1]['kwargs'].get('updated_at'),
            },
        )
        assistant_message = conversation['messages'][-1]
        self.assertEqual(assistant_message.get('role'), 'assistant')
        self.assertEqual(assistant_message.get('content'), '')
        self.assertEqual(
            assistant_message.get('timestamp'),
            observed['save_calls'][-1]['kwargs'].get('updated_at'),
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
        self.assertEqual(observed['save_attempts'], 2)
        self.assertTrue(observed['save_calls'][-1]['kwargs'].get('updated_at'))
        self.assertEqual(observed_state['save_new_traces_calls'], [])

    def test_api_chat_stream_persistence_failure_emits_error_terminal_without_updated_at(self) -> None:
        conversation = {
            'id': 'conv-stream-persist-error-phase14',
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
            return FakeStreamResponse()

        observed_state, restore = self._patch_chat_pipeline(
            conversation=conversation,
            requests_post=fake_requests_post,
            save_conversation_result=lambda _conversation, **kwargs: SimpleNamespace(
                ok=False,
                catalog_saved=True,
                messages_saved=False,
                updated_at=kwargs.get('updated_at'),
                message_count=len(_conversation.get('messages', [])),
                reason='messages_write_failed',
            ),
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'stream': True}, buffered=True)
        finally:
            restore()

        text, terminal = self._split_stream_body(response)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(text, '')
        self.assertEqual(
            terminal,
            {
                'event': 'error',
                'error_code': 'conversation_persist_failed',
            },
        )
        self.assertNotIn('updated_at', terminal)
        self.assertEqual(conversation['messages'][-1]['role'], 'user')
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


if __name__ == '__main__':
    unittest.main()
