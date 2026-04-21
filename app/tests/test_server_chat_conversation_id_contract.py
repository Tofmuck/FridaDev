from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerChatConversationIdContractTests(unittest.TestCase):
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
