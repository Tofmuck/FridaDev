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


class ServerLogsPhase6Tests(unittest.TestCase):
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

    def test_admin_chat_logs_export_markdown_supports_conversation_scope(self) -> None:
        observed: dict[str, object] = {'kwargs': None}
        original_export = self.server.log_markdown_export.export_chat_logs_markdown

        def fake_export_chat_logs_markdown(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'scope': 'conversation',
                'conversation_id': 'conv-1',
                'turn_id': None,
                'events_count': 2,
                'markdown': '# Frida Chat Logs Export\n\n- scope: `conversation`\n',
            }

        self.server.log_markdown_export.export_chat_logs_markdown = fake_export_chat_logs_markdown
        try:
            response = self.client.get('/api/admin/logs/chat/export.md?conversation_id=conv-1')
        finally:
            self.server.log_markdown_export.export_chat_logs_markdown = original_export

        self.assertEqual(response.status_code, 200)
        self.assertIn('text/markdown', response.content_type)
        self.assertIn('charset=utf-8', response.content_type.lower())
        self.assertIn('attachment; filename="chat-logs-conv-1.md"', response.headers.get('Content-Disposition', ''))
        self.assertIn('# Frida Chat Logs Export', response.get_data(as_text=True))
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1', 'turn_id': None})

    def test_admin_chat_logs_export_markdown_supports_turn_scope(self) -> None:
        observed: dict[str, object] = {'kwargs': None}
        original_export = self.server.log_markdown_export.export_chat_logs_markdown

        def fake_export_chat_logs_markdown(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'scope': 'turn',
                'conversation_id': 'conv-1',
                'turn_id': 'turn-3',
                'events_count': 1,
                'markdown': '# Frida Chat Logs Export\n\n- scope: `turn`\n',
            }

        self.server.log_markdown_export.export_chat_logs_markdown = fake_export_chat_logs_markdown
        try:
            response = self.client.get('/api/admin/logs/chat/export.md?conversation_id=conv-1&turn_id=turn-3')
        finally:
            self.server.log_markdown_export.export_chat_logs_markdown = original_export

        self.assertEqual(response.status_code, 200)
        self.assertIn('attachment; filename="chat-logs-conv-1-turn-3.md"', response.headers.get('Content-Disposition', ''))
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1', 'turn_id': 'turn-3'})

    def test_admin_chat_logs_export_markdown_rejects_missing_conversation(self) -> None:
        response = self.client.get('/api/admin/logs/chat/export.md')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'conversation_id is required for markdown export'})

    def test_admin_chat_logs_export_markdown_respects_admin_token_guard(self) -> None:
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase6-token'

        response_missing = self.client.get('/api/admin/logs/chat/export.md?conversation_id=conv-1')
        self.assertEqual(response_missing.status_code, 401)

        original_export = self.server.log_markdown_export.export_chat_logs_markdown
        self.server.log_markdown_export.export_chat_logs_markdown = (
            lambda **_kwargs: {
                'scope': 'conversation',
                'conversation_id': 'conv-1',
                'turn_id': None,
                'events_count': 0,
                'markdown': '# Frida Chat Logs Export\n',
            }
        )
        try:
            response_ok = self.client.get(
                '/api/admin/logs/chat/export.md?conversation_id=conv-1',
                headers={'X-Admin-Token': 'phase6-token'},
            )
        finally:
            self.server.log_markdown_export.export_chat_logs_markdown = original_export

        self.assertEqual(response_ok.status_code, 200)
        self.assertIn('text/markdown', response_ok.content_type)


if __name__ == '__main__':
    unittest.main()
