from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path
from types import SimpleNamespace


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
                original_insert = (
                    self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event
                )
                events = []

                def fail_agenda_turn(*_args, **_kwargs):
                    raise AssertionError('agenda runtime must not run when agenda_enabled is absent or false')

                def fake_insert(event: dict, **_kwargs) -> bool:
                    events.append(dict(event))
                    return True

                self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = fail_agenda_turn
                self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
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
                    self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = original_insert
                    restore()

                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.get_json()['ok'])
                prompt_text = '\n'.join(message['content'] for message in observed_state['payload_messages'])
                self.assertNotIn('AGENDA', prompt_text.upper())
                self.assertNotIn('BEGIN:VEVENT', prompt_text)
                agenda_events = [event for event in events if event.get('stage') == 'agenda']
                self.assertEqual(len(agenda_events), 1)
                agenda_event = agenda_events[0]
                agenda_payload = agenda_event['payload_json']
                self.assertEqual(agenda_event['status'], 'disabled')
                self.assertEqual(agenda_payload['status_schema_version'], 'agentic_v1')
                self.assertEqual(agenda_payload['status'], 'disabled')
                self.assertEqual(agenda_payload['reason_code'], 'agenda_toggle_off')
                self.assertFalse(agenda_payload['enabled'])
                self.assertFalse(agenda_payload['caldav_access'])
                self.assertFalse(agenda_payload['secret_access'])
                self.assertFalse(agenda_payload['mutation_attempted'])
                event_dump = json.dumps(events, sort_keys=True)
                self.assertNotIn('Bonjour', event_dump)
                self.assertNotIn('BEGIN:VEVENT', event_dump)

    def test_agenda_true_with_runtime_off_is_observed_as_content_free_noop_without_prompt_lane(self) -> None:
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
        self.assertEqual(agenda_payload['schema_version'], 'frida_agenda_lot5_readonly_v1')
        self.assertEqual(agenda_payload['agent_schema_version'], 'frida_agenda_agent_v1')
        self.assertTrue(agenda_payload['enabled'])
        self.assertFalse(agenda_payload['used'])
        self.assertTrue(agenda_payload['runtime_available'])
        self.assertEqual(agenda_payload['mode'], 'off')
        self.assertFalse(agenda_payload['agent_json_validated'])
        self.assertFalse(agenda_payload['caldav_access'])
        self.assertFalse(agenda_payload['nextcloud_access'])
        self.assertFalse(agenda_payload['secret_access'])
        self.assertFalse(agenda_payload['mutation_attempted'])
        self.assertFalse(agenda_payload['prompt_lane_injected'])
        self.assertFalse(agenda_payload['final_response_override'])
        self.assertTrue(agenda_payload['content_free'])
        prompt_text = '\n'.join(message['content'] for message in observed_state['payload_messages'])
        self.assertNotIn('BEGIN:VEVENT', prompt_text)
        self.assertNotIn('Fixture Focus Block', repr(events))
        self.assertNotIn('Est-ce que tu peux lire mon agenda demain ?', repr(agenda_payload))

    def test_agenda_active_missing_secret_fallback_is_not_observed_as_ok(self) -> None:
        conversation = {
            'id': 'conv-agenda-secret-missing',
            'created_at': '2026-06-08T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        _observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_settings = self.server.runtime_settings.get_agenda_agent_settings
        original_insert = self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event
        events = []

        def active_missing_secret_settings(*_args, **_kwargs):
            return self.server.runtime_settings.RuntimeSectionView(
                section='agenda_agent',
                payload={
                    'mode': {'value': 'active', 'origin': 'test'},
                    'caldav_account': {'value': 'tof', 'origin': 'test'},
                    'caldav_app_password': {
                        'is_secret': True,
                        'is_set': False,
                        'origin': 'missing',
                    },
                },
                source='db',
                source_reason='test_active_missing_secret',
            )

        def fake_insert(event: dict, **_kwargs) -> bool:
            events.append(dict(event))
            return True

        self.server.runtime_settings.get_agenda_agent_settings = active_missing_secret_settings
        self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'RAW AGENDA SECRET TEST MESSAGE MUST NOT LEAK',
                    'agenda_enabled': True,
                    'web_search': False,
                },
            )
        finally:
            self.server.runtime_settings.get_agenda_agent_settings = original_settings
            self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        agenda_events = [event for event in events if event.get('stage') == 'agenda']
        self.assertEqual(len(agenda_events), 1)
        agenda_event = agenda_events[0]
        agenda_payload = agenda_event['payload_json']
        self.assertEqual(agenda_event['status'], 'not_configured')
        self.assertEqual(agenda_payload['reason_code'], 'agenda_agent_secret_not_configured')
        self.assertEqual(agenda_payload['status'], 'fallback')
        self.assertEqual(agenda_payload['status_schema_version'], 'agentic_v1')
        self.assertFalse(agenda_payload['caldav_access'])
        self.assertFalse(agenda_payload['secret_access'])
        self.assertFalse(agenda_payload['mutation_attempted'])
        self.assertNotIn('RAW AGENDA SECRET TEST MESSAGE', json.dumps(events, sort_keys=True))

    def test_agenda_runtime_failure_remains_error_observability(self) -> None:
        conversation = {
            'id': 'conv-agenda-failure',
            'created_at': '2026-06-08T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        _observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_agenda_turn = self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn
        original_insert = self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event
        events = []

        def fake_agenda_turn(*_args, **_kwargs):
            return SimpleNamespace(
                enabled=True,
                used=False,
                status='error',
                reason_code='agenda_runtime_error',
                observability_payload={
                    'schema_version': 'frida_agenda_lot5_readonly_v1',
                    'enabled': True,
                    'used': False,
                    'status': 'error',
                    'reason_code': 'agenda_runtime_error',
                    'mode': 'active',
                    'caldav_access': False,
                    'secret_access': False,
                    'mutation_attempted': False,
                    'content_free': True,
                },
            )

        def fake_insert(event: dict, **_kwargs) -> bool:
            events.append(dict(event))
            return True

        self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = fake_agenda_turn
        self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'Lis mon agenda aujourd hui',
                    'agenda_enabled': True,
                    'web_search': False,
                },
            )
        finally:
            self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = original_agenda_turn
            self.server.chat_service.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            restore()

        self.assertEqual(response.status_code, 200)
        agenda_events = [event for event in events if event.get('stage') == 'agenda']
        self.assertEqual(len(agenda_events), 1)
        self.assertEqual(agenda_events[0]['status'], 'error')
        self.assertEqual(
            agenda_events[0]['payload_json'].get('status_schema_version'),
            'agentic_v1',
        )
        self.assertNotIn('Lis mon agenda aujourd hui', json.dumps(events, sort_keys=True))

    def test_agenda_final_response_override_persists_as_normal_assistant_message(self) -> None:
        conversation = {
            'id': 'conv-agenda-final',
            'created_at': '2026-06-08T00:00:00Z',
            'messages': [{'role': 'system', 'content': 'BACKEND SYSTEM PROMPT'}],
        }
        observed_state, restore = self._patch_chat_pipeline(conversation=conversation)
        original_agenda_turn = self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn
        original_emit = self.server.chat_service.chat_turn_logger.emit
        events = []

        def fake_agenda_turn(*_args, **_kwargs):
            lock = _FakeAgendaFinalLock('Voila ce que je vois dans ton agenda :\n- 09:00-10:00 - Fixture Focus Block')
            return SimpleNamespace(
                enabled=True,
                used=True,
                status='active_ready',
                reason_code='agenda_agent_active_validated',
                observability_payload={
                    'schema_version': 'frida_agenda_lot5_readonly_v1',
                    'enabled': True,
                    'used': True,
                    'mode': 'active',
                    'runtime_available': True,
                    'agent_json_validated': True,
                    'read_execution_status': 'ok',
                    'read_event_count': 1,
                    'caldav_access': False,
                    'nextcloud_access': False,
                    'secret_access': False,
                    'mutation_attempted': False,
                    'final_response_override': True,
                    'content_free': True,
                },
                final_response_lock=lock,
            )

        self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = fake_agenda_turn
        self.server.chat_service.chat_turn_logger.emit = (
            lambda event, **kwargs: events.append((event, kwargs))
        )
        try:
            response = self.client.post(
                '/api/chat',
                json={
                    'message': 'Lis mon agenda aujourd hui',
                    'agenda_enabled': True,
                    'web_search': False,
                },
            )
        finally:
            self.server.chat_service.agenda_chat_runtime.run_agenda_chat_turn = original_agenda_turn
            self.server.chat_service.chat_turn_logger.emit = original_emit
            restore()

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['text'], 'Voila ce que je vois dans ton agenda :\n- 09:00-10:00 - Fixture Focus Block')
        assistant_messages = [
            message for message in conversation['messages'] if message.get('role') == 'assistant'
        ]
        self.assertEqual(len(assistant_messages), 1)
        assistant_message = assistant_messages[0]
        self.assertEqual(assistant_message['content'], payload['text'])
        self.assertIn('timestamp', assistant_message)
        self.assertEqual(assistant_message['meta']['source'], 'agenda_readonly_response')
        self.assertTrue(assistant_message['meta']['content_free_meta'])
        self.assertEqual(len(observed_state['save_new_traces_calls']), 1)
        self.assertEqual(observed_state['save_new_traces_calls'][0][-1], assistant_message)
        agenda_events = [item for event, item in events if event == 'agenda']
        self.assertEqual(len(agenda_events), 1)
        self.assertNotIn('Fixture Focus Block', repr(agenda_events))
        self.assertNotIn('BEGIN:VEVENT', repr(events))
        override_events = [item for event, item in events if event == 'assistant_response_override']
        self.assertEqual(len(override_events), 0)


class _FakeAgendaFinalLock:
    ok = True
    source = 'agenda_readonly_response'
    reason_code = 'agenda_readonly_final_response'

    def __init__(self, content: str) -> None:
        self.content = content

    def to_message_meta(self):
        return {
            'source': self.source,
            'reason_code': self.reason_code,
            'agenda_schema_version': 'frida_agenda_agent_v1',
            'agenda_product_method': 'read_today',
            'agenda_tool_names': ['event_query_range'],
            'agenda_tool_count': 1,
            'agenda_event_count': 1,
            'agenda_calendar_count': 1,
            'agenda_event_id_hashes': ['eventhash12'],
            'agenda_calendar_id_hashes': ['calhash12'],
            'agenda_caldav_access': False,
            'agenda_nextcloud_access': False,
            'agenda_mutation_attempted': False,
            'agenda_final_lock_authorized': True,
            'agenda_final_lock_reason_code': self.reason_code,
            'content_free_meta': True,
        }

    def to_observability(self):
        return {
            'source': self.source,
            'reason_code': self.reason_code,
            'content_present': True,
            'content_chars': len(self.content),
            'content_hash': 'contenthash12',
            'content_free': True,
        }


if __name__ == '__main__':
    unittest.main()
