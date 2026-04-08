from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class ServerLogsPhase4Tests(unittest.TestCase):
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

    def test_admin_chat_logs_delete_route_supports_conversation_scope(self) -> None:
        observed = {'kwargs': None}
        original_delete = self.server.log_store.delete_chat_log_events

        def fake_delete_chat_log_events(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'scope': 'conversation_logs',
                'conversation_id': 'conv-1',
                'turn_id': None,
                'deleted_count': 4,
            }

        self.server.log_store.delete_chat_log_events = fake_delete_chat_log_events
        try:
            response = self.client.delete('/api/admin/logs/chat?conversation_id=conv-1')
        finally:
            self.server.log_store.delete_chat_log_events = original_delete

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['scope'], 'conversation_logs')
        self.assertEqual(data['conversation_id'], 'conv-1')
        self.assertIsNone(data['turn_id'])
        self.assertEqual(data['deleted_count'], 4)
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1', 'turn_id': None})

    def test_admin_chat_logs_delete_route_supports_turn_scope(self) -> None:
        observed = {'kwargs': None}
        original_delete = self.server.log_store.delete_chat_log_events

        def fake_delete_chat_log_events(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'scope': 'turn_logs',
                'conversation_id': 'conv-1',
                'turn_id': 'turn-1',
                'deleted_count': 1,
            }

        self.server.log_store.delete_chat_log_events = fake_delete_chat_log_events
        try:
            response = self.client.delete('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
        finally:
            self.server.log_store.delete_chat_log_events = original_delete

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['scope'], 'turn_logs')
        self.assertEqual(data['conversation_id'], 'conv-1')
        self.assertEqual(data['turn_id'], 'turn-1')
        self.assertEqual(data['deleted_count'], 1)
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1', 'turn_id': 'turn-1'})

    def test_admin_chat_logs_delete_route_rejects_all_logs_scope(self) -> None:
        original_delete = self.server.log_store.delete_chat_log_events
        self.server.log_store.delete_chat_log_events = (
            lambda **_kwargs: (_ for _ in ()).throw(ValueError('all_logs deletion is not supported in MVP'))
        )
        try:
            response = self.client.delete('/api/admin/logs/chat')
        finally:
            self.server.log_store.delete_chat_log_events = original_delete

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'all_logs deletion is not supported in MVP'})

    def test_admin_chat_logs_delete_route_rejects_turn_without_conversation(self) -> None:
        original_delete = self.server.log_store.delete_chat_log_events
        self.server.log_store.delete_chat_log_events = (
            lambda **_kwargs: (_ for _ in ()).throw(ValueError('turn_logs deletion requires conversation_id'))
        )
        try:
            response = self.client.delete('/api/admin/logs/chat?turn_id=turn-only')
        finally:
            self.server.log_store.delete_chat_log_events = original_delete

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'turn_logs deletion requires conversation_id'})

    def test_admin_chat_logs_delete_route_is_available_without_admin_token(self) -> None:
        original_delete = self.server.log_store.delete_chat_log_events
        self.server.log_store.delete_chat_log_events = (
            lambda **_kwargs: {
                'scope': 'conversation_logs',
                'conversation_id': 'conv-1',
                'turn_id': None,
                'deleted_count': 0,
            }
        )
        try:
            response_ok = self.client.delete('/api/admin/logs/chat?conversation_id=conv-1')
        finally:
            self.server.log_store.delete_chat_log_events = original_delete

        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.get_json()['ok'])

    def test_admin_chat_logs_non_reconstruction_after_delete_until_new_event(self) -> None:
        state = {
            'items': [
                {
                    'event_id': 'evt-1',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'ts': '2026-03-27T12:00:00+00:00',
                    'stage': 'turn_start',
                    'status': 'ok',
                    'duration_ms': None,
                    'payload': {'marker': 'before-delete-1'},
                },
                {
                    'event_id': 'evt-2',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'ts': '2026-03-27T12:01:00+00:00',
                    'stage': 'turn_end',
                    'status': 'ok',
                    'duration_ms': 15,
                    'payload': {'marker': 'before-delete-2'},
                },
            ]
        }
        original_read = self.server.log_store.read_chat_log_events
        original_delete = self.server.log_store.delete_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            conversation_id = kwargs.get('conversation_id')
            turn_id = kwargs.get('turn_id')
            filtered = [
                item
                for item in state['items']
                if (conversation_id is None or item['conversation_id'] == conversation_id)
                and (turn_id is None or item['turn_id'] == turn_id)
            ]
            return {
                'items': filtered,
                'count': len(filtered),
                'total': len(filtered),
                'limit': kwargs.get('limit', 100),
                'offset': kwargs.get('offset', 0),
                'next_offset': None,
                'filters': {
                    'conversation_id': conversation_id,
                    'turn_id': turn_id,
                    'stage': kwargs.get('stage'),
                    'status': kwargs.get('status'),
                    'ts_from': kwargs.get('ts_from'),
                    'ts_to': kwargs.get('ts_to'),
                },
            }

        def fake_delete_chat_log_events(**kwargs):
            conversation_id = kwargs.get('conversation_id')
            turn_id = kwargs.get('turn_id')
            if not conversation_id:
                raise ValueError('all_logs deletion is not supported in MVP')
            before = len(state['items'])
            state['items'] = [
                item
                for item in state['items']
                if not (
                    item['conversation_id'] == conversation_id
                    and (turn_id is None or item['turn_id'] == turn_id)
                )
            ]
            return {
                'scope': 'turn_logs' if turn_id else 'conversation_logs',
                'conversation_id': conversation_id,
                'turn_id': turn_id,
                'deleted_count': before - len(state['items']),
            }

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        self.server.log_store.delete_chat_log_events = fake_delete_chat_log_events
        try:
            before = self.client.get('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
            self.assertEqual(before.status_code, 200)
            self.assertEqual(before.get_json()['count'], 2)

            deleted = self.client.delete('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
            self.assertEqual(deleted.status_code, 200)
            self.assertEqual(deleted.get_json()['deleted_count'], 2)

            after_once = self.client.get('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
            self.assertEqual(after_once.status_code, 200)
            self.assertEqual(after_once.get_json()['count'], 0)
            self.assertEqual(after_once.get_json()['items'], [])

            after_twice = self.client.get('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
            self.assertEqual(after_twice.status_code, 200)
            self.assertEqual(after_twice.get_json()['count'], 0)
            self.assertEqual(after_twice.get_json()['items'], [])

            # Simulate a fresh runtime event: logs can reappear only through new writes.
            state['items'].append(
                {
                    'event_id': 'evt-3',
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'ts': '2026-03-27T12:02:00+00:00',
                    'stage': 'turn_start',
                    'status': 'ok',
                    'duration_ms': None,
                    'payload': {'marker': 'new-runtime-event'},
                }
            )
            after_new_event = self.client.get('/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-1')
            self.assertEqual(after_new_event.status_code, 200)
            self.assertEqual(after_new_event.get_json()['count'], 1)
            self.assertEqual(after_new_event.get_json()['items'][0]['event_id'], 'evt-3')
        finally:
            self.server.log_store.read_chat_log_events = original_read
            self.server.log_store.delete_chat_log_events = original_delete


if __name__ == '__main__':
    unittest.main()
