from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - local host may not have repo deps.
    sys.modules['psycopg'] = types.ModuleType('psycopg')
    rows_module = types.ModuleType('psycopg.rows')
    rows_module.dict_row = object()
    sys.modules['psycopg.rows'] = rows_module
    types_module = types.ModuleType('psycopg.types')
    json_module = types.ModuleType('psycopg.types.json')
    json_module.Json = lambda value: value
    sys.modules['psycopg.types'] = types_module
    sys.modules['psycopg.types.json'] = json_module

from tests.support import server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


class _FakeResponse:
    text = 'ok agenda noop'

    def raise_for_status(self):
        return None

    def json(self):
        return {'choices': [{'message': {'content': self.text}}]}


def _build_prompt_messages(conversation, *_args, **_kwargs):
    user_messages = [message for message in conversation.get('messages', []) if message.get('role') == 'user']
    user_content = user_messages[-1]['content'] if user_messages else 'Question'
    return [
        {'role': 'system', 'content': conversation['messages'][0]['content']},
        {'role': 'user', 'content': user_content},
    ]


class ServerChatAgendaContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def _patch_chat_pipeline(self, *, conversation: dict):
        return server_chat_pipeline.patch_server_chat_pipeline(
            self.server,
            conversation=conversation,
            requests_post=lambda *_args, **_kwargs: _FakeResponse(),
            build_prompt_messages=_build_prompt_messages,
        )

    def test_agenda_absent_or_false_is_strict_noop(self) -> None:
        for payload in ({}, {'agenda_enabled': False}):
            with self.subTest(payload=payload):
                conversation = {
                    'id': 'conv-agenda-disabled',
                    'created_at': '2026-06-08T00:00:00Z',
                    'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
                }
                observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
                original_agenda_turn = self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn
                original_emit = self.server.chat_service.chat_turn_logger.emit
                events = []

                def fail_agenda_turn(*_args, **_kwargs):
                    raise AssertionError('agenda runtime must not run when agenda_enabled is absent or false')

                self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = fail_agenda_turn
                self.server.chat_service.chat_turn_logger.emit = (
                    lambda event, **kwargs: events.append((event, kwargs))
                )
                try:
                    response = self.client.post(
                        '/api/chat',
                        json={
                            'message': 'Bonjour',
                            'web_search': False,
                            **payload,
                        },
                    )
                finally:
                    self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = original_agenda_turn
                    self.server.chat_service.chat_turn_logger.emit = original_emit
                    restore()

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['ok'])
                prompt_text = '\n'.join(message['content'] for message in observed_state['payload_messages'])
                self.assertNotIn('AGENDA', prompt_text.upper())
                self.assertNotIn('BEGIN:VEVENT', prompt_text)
                self.assertFalse([event for event in events if event[0] == 'agenda'])

    def test_agenda_true_is_observed_as_content_free_noop_without_prompt_lane(self) -> None:
        conversation = {
            'id': 'conv-agenda-enabled',
            'created_at': '2026-06-08T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_emit = self.server.chat_service.chat_turn_logger.emit
        events = []
        self.server.chat_service.chat_turn_logger.emit = (
            lambda event, **kwargs: events.append((event, kwargs))
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'Est-ce que tu peux lire mon agenda demain ?',
                    'agenda_enabled': True,
                    'web_search': False,
                },
            )
        finally:
            self.server.chat_service.chat_turn_logger.emit = original_emit
            restore()

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])
        agenda_events = [payload for event, payload in events if event == 'agenda']
        self.assertEqual(len(agenda_events), 1)
        agenda_payload = agenda_events[0]['payload']
        self.assertEqual(agenda_payload['schema_version'], 'frida_agenda_lot1_noop_v1')
        self.assertTrue(agenda_payload['enabled'])
        self.assertFalse(agenda_payload['used'])
        self.assertFalse(agenda_payload['runtime_available'])
        self.assertFalse(agenda_payload['caldav_access'])
        self.assertFalse(agenda_payload['nextcloud_access'])
        self.assertFalse(agenda_payload['secret_access'])
        self.assertFalse(agenda_payload['mutation_attempted'])
        self.assertTrue(agenda_payload['content_free'])
        prompt_text = '\n'.join(message['content'] for message in observed_state['payload_messages'])
        self.assertNotIn('BEGIN:VEVENT', prompt_text)
        self.assertNotIn('Fixture Focus Block', repr(events))
        self.assertNotIn('Est-ce que tu peux lire mon agenda demain ?', repr(agenda_payload))


if __name__ == '__main__':
    unittest.main()
