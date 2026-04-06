from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import conv_store
from memory import memory_store


class ServerAdminIdentityStaticEditPhase4Tests(unittest.TestCase):
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
        self._original_admin_allowed_cidrs = self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS
        self.server.config.FRIDA_ADMIN_TOKEN = ''
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS = ''

    def tearDown(self) -> None:
        self.server.config.FRIDA_ADMIN_TOKEN = self._original_admin_token
        self.server.config.FRIDA_ADMIN_LAN_ONLY = self._original_admin_lan_only
        self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS = self._original_admin_allowed_cidrs

    def test_identity_static_edit_route_updates_active_resource_content(self) -> None:
        observed_logs = []
        originals = {
            'get_resources_settings': self.server.runtime_settings.get_resources_settings,
            'log_event': self.server.admin_logs.log_event,
            '_get_mutable_identity': self.server.identity._get_mutable_identity,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'llm.txt'
            user_file = tmp_path / 'user.txt'
            llm_file.write_text('Frida initiale', encoding='utf-8')
            user_file.write_text('Utilisateur initial', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            self.server.runtime_settings.get_resources_settings = fake_get_resources_settings
            self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
            self.server.identity._get_mutable_identity = lambda _subject: None
            try:
                response = self.client.post(
                    '/api/admin/identity/static',
                    json={
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Frida statique revisee\n',
                        'reason': 'correction operateur',
                    },
                )
                runtime_payload = self.server.identity.build_identity_input()
                stored_text = llm_file.read_text(encoding='utf-8')
            finally:
                self.server.runtime_settings.get_resources_settings = originals['get_resources_settings']
                self.server.admin_logs.log_event = originals['log_event']
                self.server.identity._get_mutable_identity = originals['_get_mutable_identity']

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reason_code'], 'set_applied')
        self.assertEqual(data['active_static_source'], 'resource_path_content')
        self.assertEqual(data['resource_field'], 'llm_identity_path')
        self.assertEqual(stored_text, 'Frida statique revisee\n')
        self.assertEqual(runtime_payload['frida']['static']['content'], 'Frida statique revisee')
        self.assertEqual(runtime_payload['user']['static']['content'], 'Utilisateur initial')
        self.assertEqual(observed_logs[0][0], 'identity_static_admin_edit')
        self.assertNotIn('content', observed_logs[0][1])
        self.assertNotIn('reason', observed_logs[0][1])

    def test_identity_static_edit_route_supports_clear_without_deleting_resource(self) -> None:
        observed_logs = []
        originals = {
            'get_resources_settings': self.server.runtime_settings.get_resources_settings,
            'log_event': self.server.admin_logs.log_event,
            '_get_mutable_identity': self.server.identity._get_mutable_identity,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'llm.txt'
            user_file = tmp_path / 'user.txt'
            llm_file.write_text('Frida initiale', encoding='utf-8')
            user_file.write_text('Utilisateur initial', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            self.server.runtime_settings.get_resources_settings = fake_get_resources_settings
            self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
            self.server.identity._get_mutable_identity = lambda _subject: None
            try:
                response = self.client.post(
                    '/api/admin/identity/static',
                    json={
                        'subject': 'user',
                        'action': 'clear',
                        'content': '',
                        'reason': 'obsolete',
                    },
                )
                runtime_payload = self.server.identity.build_identity_input()
                exists_after = user_file.exists()
                stored_text = user_file.read_text(encoding='utf-8')
            finally:
                self.server.runtime_settings.get_resources_settings = originals['get_resources_settings']
                self.server.admin_logs.log_event = originals['log_event']
                self.server.identity._get_mutable_identity = originals['_get_mutable_identity']

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reason_code'], 'clear_applied')
        self.assertTrue(exists_after)
        self.assertEqual(stored_text, '')
        self.assertEqual(runtime_payload['user']['static']['content'], '')
        self.assertEqual(observed_logs[0][1]['reason_code'], 'clear_applied')

    def test_identity_static_edit_route_rejects_invalid_payload_fail_closed(self) -> None:
        observed_logs = []
        originals = {
            'get_resources_settings': self.server.runtime_settings.get_resources_settings,
            'log_event': self.server.admin_logs.log_event,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'llm.txt'
            user_file = tmp_path / 'user.txt'
            llm_file.write_text('Frida initiale', encoding='utf-8')
            user_file.write_text('Utilisateur initial', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            self.server.runtime_settings.get_resources_settings = fake_get_resources_settings
            self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
            try:
                response = self.client.post(
                    '/api/admin/identity/static',
                    json={
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Frida changee',
                        'reason': '',
                    },
                )
                stored_text = llm_file.read_text(encoding='utf-8')
            finally:
                self.server.runtime_settings.get_resources_settings = originals['get_resources_settings']
                self.server.admin_logs.log_event = originals['log_event']

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['validation_error'], 'contract_reason_missing')
        self.assertEqual(stored_text, 'Frida initiale')
        self.assertEqual(observed_logs[0][1]['validation_error'], 'contract_reason_missing')

    def test_identity_static_edit_route_fails_closed_when_runtime_resource_is_unresolved(self) -> None:
        observed_logs = []
        originals = {
            'get_resources_settings': self.server.runtime_settings.get_resources_settings,
            'log_event': self.server.admin_logs.log_event,
        }

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            unresolved_path = tmp_path / 'missing-llm.txt'
            user_file = tmp_path / 'user.txt'
            user_file.write_text('Utilisateur initial', encoding='utf-8')

            def fake_get_resources_settings():
                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(unresolved_path), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            self.server.runtime_settings.get_resources_settings = fake_get_resources_settings
            self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
            try:
                response = self.client.post(
                    '/api/admin/identity/static',
                    json={
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Frida changee',
                        'reason': 'manual correction',
                    },
                )
            finally:
                self.server.runtime_settings.get_resources_settings = originals['get_resources_settings']
                self.server.admin_logs.log_event = originals['log_event']

        self.assertEqual(response.status_code, 409)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['validation_error'], 'static_resource_unresolved')
        self.assertEqual(data['resource_field'], 'llm_identity_path')
        self.assertFalse(unresolved_path.exists())
        self.assertNotIn('content', observed_logs[0][1])

    def test_identity_static_edit_route_is_guarded_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase4-identity-static-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            response = self.client.post(
                '/api/admin/identity/static',
                json={'subject': 'llm', 'action': 'clear', 'content': '', 'reason': 'cleanup'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
