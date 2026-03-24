from __future__ import annotations

import importlib
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from core import conv_store
from memory import memory_store


class ServerAdminSettingsPhase5Tests(unittest.TestCase):
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
        runtime_settings.invalidate_runtime_settings_cache()
        self._tmpdir = tempfile.TemporaryDirectory()
        self._original_log_path = self.server.admin_logs.LOG_PATH
        self._original_bootstrap_done = self.server.admin_logs._BOOTSTRAP_DONE
        temp_log_path = Path(self._tmpdir.name) / 'admin.log.jsonl'
        admin_logs.LOG_PATH = temp_log_path
        admin_logs._BOOTSTRAP_DONE = True
        self.server.admin_logs.LOG_PATH = temp_log_path
        self.server.admin_logs._BOOTSTRAP_DONE = True
        self.client = self.server.app.test_client()

    def tearDown(self) -> None:
        admin_logs.LOG_PATH = self._original_log_path
        admin_logs._BOOTSTRAP_DONE = self._original_bootstrap_done
        self.server.admin_logs.LOG_PATH = self._original_log_path
        self.server.admin_logs._BOOTSTRAP_DONE = self._original_bootstrap_done
        self._tmpdir.cleanup()

    def test_get_admin_settings_returns_aggregated_sections_with_redacted_secrets(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            if section == 'main_model':
                payload = {
                    'model': {'value': 'openrouter/test-runtime-model', 'is_secret': False, 'origin': 'db'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                }
                return runtime_settings.RuntimeSectionView(
                    section=section,
                    payload=payload,
                    source='db',
                    source_reason='db_row',
                )
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={'placeholder': {'value': section, 'is_secret': False, 'origin': 'env_seed'}},
                source='env',
                source_reason='empty_table',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(set(data['sections'].keys()), set(runtime_settings.list_sections()))
        self.assertEqual(
            data['sections']['main_model']['payload']['model']['value'],
            'openrouter/test-runtime-model',
        )
        self.assertEqual(
            data['sections']['main_model']['payload']['api_key'],
            {'is_secret': True, 'is_set': True, 'origin': 'db'},
        )

    def test_get_admin_settings_main_model_returns_single_section_with_redacted_secrets(self) -> None:
        original_get_section = self.server.runtime_settings.get_runtime_section_for_api

        def fake_get_runtime_section_for_api(section: str):
            self.assertEqual(section, 'main_model')
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/main-model-route', 'is_secret': False, 'origin': 'db'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'db'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.get_runtime_section_for_api = fake_get_runtime_section_for_api
        try:
            response = self.client.get('/api/admin/settings/main-model')
        finally:
            self.server.runtime_settings.get_runtime_section_for_api = original_get_section

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'main_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/main-model-route')
        self.assertEqual(
            data['payload']['api_key'],
            {'is_secret': True, 'is_set': True, 'origin': 'db'},
        )

    def test_get_admin_settings_is_protected_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase5-admin-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            unauthorized = self.client.get('/api/admin/settings')
            authorized = self.client.get(
                '/api/admin/settings',
                headers={'X-Admin-Token': 'phase5-admin-token'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)

    def test_patch_admin_settings_main_model_updates_section(self) -> None:
        observed = {'section': None, 'payload': None, 'updated_by': None}
        original_update = self.server.runtime_settings.update_runtime_section

        def fake_update_runtime_section(section, patch_payload, *, updated_by='admin_api', fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            observed['updated_by'] = updated_by
            return runtime_settings.RuntimeSectionView(
                section=section,
                payload={
                    'model': {'value': 'openrouter/patched-main-model', 'is_secret': False, 'origin': 'admin_ui'},
                    'api_key': {'is_secret': True, 'is_set': True, 'origin': 'env_seed'},
                },
                source='db',
                source_reason='db_row',
            )

        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        try:
            response = self.client.patch(
                '/api/admin/settings/main-model',
                json={
                    'updated_by': 'phase5-admin',
                    'payload': {
                        'model': {'value': 'openrouter/patched-main-model'},
                        'temperature': {'value': 0.4},
                    },
                },
            )
        finally:
            self.server.runtime_settings.update_runtime_section = original_update

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'main_model')
        self.assertEqual(observed['updated_by'], 'phase5-admin')
        self.assertEqual(
            observed['payload'],
            {
                'model': {'value': 'openrouter/patched-main-model'},
                'temperature': {'value': 0.4},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['section'], 'main_model')
        self.assertEqual(data['payload']['model']['value'], 'openrouter/patched-main-model')
        self.assertEqual(data['payload']['api_key'], {'is_secret': True, 'is_set': True, 'origin': 'env_seed'})

    def test_patch_admin_settings_main_model_rejects_invalid_payload(self) -> None:
        response = self.client.patch(
            '/api/admin/settings/main-model',
            json={'payload': {'api_key': {'value': 'sk-secret'}}},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('secret updates are not supported yet', data['error'])


if __name__ == '__main__':
    unittest.main()
