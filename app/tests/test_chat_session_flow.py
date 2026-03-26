from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_session_flow


class ChatSessionFlowTests(unittest.TestCase):
    def test_resolve_chat_session_rejects_empty_message(self) -> None:
        conv_store = SimpleNamespace(
            normalize_conversation_id=lambda _raw: None,
            load_conversation=lambda *_args, **_kwargs: None,
            new_conversation=lambda _system: {},
            save_conversation=lambda *_args, **_kwargs: None,
            conversation_path=lambda _id: 'conv/placeholder.json',
        )
        memory_store = SimpleNamespace(decay_identities=lambda: None)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        session, error = chat_session_flow.resolve_chat_session(
            {'message': '   '},
            system_prompt='SYSTEM',
            conv_store_module=conv_store,
            memory_store_module=memory_store,
            logger=logger,
        )

        self.assertIsNone(session)
        self.assertEqual(error, ({'ok': False, 'error': 'message vide'}, 400))

    def test_resolve_chat_session_returns_404_when_conversation_is_missing(self) -> None:
        observed = {'new_called': False}

        def fake_new_conversation(_system):
            observed['new_called'] = True
            return {'id': 'should-not-be-created'}

        conv_store = SimpleNamespace(
            normalize_conversation_id=lambda _raw: 'conv-missing',
            load_conversation=lambda *_args, **_kwargs: None,
            new_conversation=fake_new_conversation,
            save_conversation=lambda *_args, **_kwargs: None,
            conversation_path=lambda _id: 'conv/placeholder.json',
        )
        memory_store = SimpleNamespace(decay_identities=lambda: None)
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None)

        session, error = chat_session_flow.resolve_chat_session(
            {'message': 'Bonjour', 'conversation_id': 'conv-missing'},
            system_prompt='SYSTEM',
            conv_store_module=conv_store,
            memory_store_module=memory_store,
            logger=logger,
        )

        self.assertIsNone(session)
        self.assertEqual(error, ({'ok': False, 'error': 'conversation introuvable'}, 404))
        self.assertFalse(observed['new_called'])

    def test_resolve_chat_session_keeps_invalid_raw_contract_and_creates_conversation(self) -> None:
        observed = {
            'saved': False,
            'decay_called': False,
            'log_messages': [],
        }

        conversation = {
            'id': 'conv-new-session',
            'created_at': '2026-03-26T00:00:00Z',
            'messages': [],
        }

        conv_store = SimpleNamespace(
            normalize_conversation_id=lambda _raw: None,
            load_conversation=lambda *_args, **_kwargs: None,
            new_conversation=lambda _system: conversation,
            save_conversation=lambda *_args, **_kwargs: observed.update({'saved': True}),
            conversation_path=lambda _id: 'conv/conv-new-session.json',
        )
        memory_store = SimpleNamespace(
            decay_identities=lambda: observed.update({'decay_called': True}),
        )
        logger = SimpleNamespace(
            info=lambda msg, *args: observed['log_messages'].append(msg % args if args else msg),
        )

        session, error = chat_session_flow.resolve_chat_session(
            {
                'message': 'Bonjour',
                'conversation_id': '@@bad@@',
                'stream': 1,
                'web_search': 0,
            },
            system_prompt='SYSTEM',
            conv_store_module=conv_store,
            memory_store_module=memory_store,
            logger=logger,
        )

        self.assertIsNone(error)
        self.assertIsNotNone(session)
        self.assertEqual(session['user_msg'], 'Bonjour')
        self.assertEqual(session['conversation']['id'], 'conv-new-session')
        self.assertTrue(session['stream_req'])
        self.assertFalse(session['web_search_on'])
        self.assertTrue(observed['saved'])
        self.assertTrue(observed['decay_called'])
        self.assertTrue(any('conv_id_invalid raw=@@bad@@' in message for message in observed['log_messages']))
        self.assertTrue(any('conv_created id=conv-new-session' in message for message in observed['log_messages']))

    def test_conversation_headers_returns_expected_contract(self) -> None:
        headers = chat_session_flow.conversation_headers(
            {
                'id': 'conv-headers',
                'created_at': '2026-03-26T00:00:00Z',
            },
            '2026-03-26T00:10:00Z',
        )

        self.assertEqual(
            headers,
            {
                'X-Conversation-Id': 'conv-headers',
                'X-Conversation-Created-At': '2026-03-26T00:00:00Z',
                'X-Conversation-Updated-At': '2026-03-26T00:10:00Z',
            },
        )


if __name__ == '__main__':
    unittest.main()
