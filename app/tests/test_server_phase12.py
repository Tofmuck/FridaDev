from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline


class ServerPhase12Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = server_chat_pipeline.load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_api_chat_uses_runtime_response_max_tokens_when_request_override_is_absent(self) -> None:
        observed = {'prompt_message_contents': []}
        conversation = {"id": "conv-phase12", "created_at": "2026-03-25T00:00:00Z", "messages": []}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "reponse test"}}]}

        def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['max_tokens'] = max_tokens
            observed['stream'] = stream
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': [],
                'max_tokens': max_tokens,
                'stream': stream,
            }

        def fake_build_prompt_messages(conversation_arg, *_args, **_kwargs):
            observed['prompt_message_contents'].append(
                [str(message.get('content') or '') for message in conversation_arg.get('messages', [])]
            )
            return [{"role": "user", "content": "Bonjour"}]

        _observed_state, restore = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=lambda *args, **kwargs: FakeResponse(),
            build_prompt_messages=fake_build_prompt_messages,
            build_payload=fake_build_payload,
            conversation_path='conv/conv-phase12.json',
            runtime_api_key='sk-phase12',
        )
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
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(legacy_response.status_code, 200)
        self.assertEqual(observed['max_tokens'], 2048)
        self.assertFalse(observed['stream'])
        self.assertTrue(observed['prompt_message_contents'])
        for prompt_contents in observed['prompt_message_contents']:
            self.assertNotIn('LEGACY_HISTORY_SHOULD_BE_IGNORED', '\n'.join(prompt_contents))

    def test_api_chat_keeps_request_max_tokens_override_over_runtime_default(self) -> None:
        observed = {}
        conversation = {"id": "conv-phase12", "created_at": "2026-03-25T00:00:00Z", "messages": []}

        class FakeResponse:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "reponse test"}}]}

        def fake_build_payload(_messages, _temperature, _top_p, max_tokens, stream=False):
            observed['max_tokens'] = max_tokens
            observed['stream'] = stream
            return {
                'model': 'openrouter/runtime-main-model',
                'messages': [],
                'max_tokens': max_tokens,
                'stream': stream,
            }

        _observed_state, restore = server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=lambda *args, **kwargs: FakeResponse(),
            build_payload=fake_build_payload,
            conversation_path='conv/conv-phase12.json',
            runtime_api_key='sk-phase12',
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'Bonjour', 'max_tokens': 512})
        finally:
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['max_tokens'], 512)
        self.assertFalse(observed['stream'])


if __name__ == '__main__':
    unittest.main()
