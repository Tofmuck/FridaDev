from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import runtime_settings
from core import conv_store
from memory import memory_store


class ServerAdminIdentityGovernancePhase5Tests(unittest.TestCase):
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

    def _governance_view(self, overrides: dict[str, object] | None = None):
        payload = runtime_settings.build_env_seed_bundle('identity_governance').payload
        normalized = runtime_settings.normalize_stored_payload(
            'identity_governance',
            payload,
            default_origin='env_seed',
        )
        for key, value in (overrides or {}).items():
            normalized[key] = {'value': value, 'is_secret': False, 'origin': 'db'}
        return runtime_settings.RuntimeSectionView(
            section='identity_governance',
            payload=normalized,
            source='db',
            source_reason='db_row',
        )

    def test_identity_governance_routes_expose_distinct_contract_and_compact_update_audit(self) -> None:
        observed_logs = []
        current_payload = self._governance_view({'CONTEXT_HINTS_MAX_ITEMS': 2})
        original_get_runtime_section = self.server.runtime_settings.get_runtime_section
        original_get_identity_governance_settings = self.server.runtime_settings.get_identity_governance_settings
        original_validate_runtime_section = self.server.runtime_settings.validate_runtime_section
        original_update_runtime_section = self.server.runtime_settings.update_runtime_section
        original_log_event = self.server.admin_logs.log_event
        original_build_identity_input = self.server.identity.build_identity_input

        def fake_get_runtime_section(section: str, *, fetcher=None):
            self.assertEqual(section, 'identity_governance')
            return current_payload

        def fake_get_identity_governance_settings(*, fetcher=None):
            return current_payload

        def fake_validate_runtime_section(section: str, patch_payload=None, *, fetcher=None):
            self.assertEqual(section, 'identity_governance')
            next_value = patch_payload['CONTEXT_HINTS_MAX_ITEMS']['value']
            return {
                'section': section,
                'source': 'candidate',
                'source_reason': 'validate_payload',
                'valid': isinstance(next_value, int) and next_value >= 1,
                'checks': [
                    {
                        'name': 'CONTEXT_HINTS_MAX_ITEMS',
                        'ok': isinstance(next_value, int) and next_value >= 1,
                        'detail': 'CONTEXT_HINTS_MAX_ITEMS must be >= 1',
                    }
                ],
            }

        def fake_update_runtime_section(section: str, patch_payload, *, updated_by='admin_api', fetcher=None):
            self.assertEqual(section, 'identity_governance')
            self.assertEqual(updated_by, 'identity_governance_admin')
            current_payload.payload['CONTEXT_HINTS_MAX_ITEMS'] = {
                'value': patch_payload['CONTEXT_HINTS_MAX_ITEMS']['value'],
                'is_secret': False,
                'origin': 'admin_ui',
            }
            return current_payload

        self.server.runtime_settings.get_runtime_section = fake_get_runtime_section
        self.server.runtime_settings.get_identity_governance_settings = fake_get_identity_governance_settings
        self.server.runtime_settings.validate_runtime_section = fake_validate_runtime_section
        self.server.runtime_settings.update_runtime_section = fake_update_runtime_section
        self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
        self.server.identity.build_identity_input = lambda: {'schema_version': 'v2'}
        try:
            read_response = self.client.get('/api/admin/identity/governance')
            write_response = self.client.post(
                '/api/admin/identity/governance',
                json={
                    'updates': {'CONTEXT_HINTS_MAX_ITEMS': 3},
                    'reason': 'raise visible context hints',
                },
            )
        finally:
            self.server.runtime_settings.get_runtime_section = original_get_runtime_section
            self.server.runtime_settings.get_identity_governance_settings = original_get_identity_governance_settings
            self.server.runtime_settings.validate_runtime_section = original_validate_runtime_section
            self.server.runtime_settings.update_runtime_section = original_update_runtime_section
            self.server.admin_logs.log_event = original_log_event
            self.server.identity.build_identity_input = original_build_identity_input

        self.assertEqual(read_response.status_code, 200)
        read_payload = read_response.get_json()
        self.assertTrue(read_payload['ok'])
        self.assertEqual(read_payload['governance_version'], 'v1')
        self.assertIn('items', read_payload)
        self.assertIn('active_prompt_contract', read_payload)
        self.assertEqual(write_response.status_code, 200)
        write_payload = write_response.get_json()
        self.assertTrue(write_payload['ok'])
        self.assertEqual(write_payload['changed_keys'], ['CONTEXT_HINTS_MAX_ITEMS'])
        self.assertEqual(observed_logs[0][0], 'identity_governance_admin_edit')
        self.assertNotIn('content', observed_logs[0][1])

    def test_identity_governance_route_rejects_readonly_legacy_knob_fail_closed(self) -> None:
        original_build_identity_input = self.server.identity.build_identity_input
        self.server.identity.build_identity_input = lambda: {'schema_version': 'v2'}
        try:
            response = self.client.post(
                '/api/admin/identity/governance',
                json={
                    'updates': {'IDENTITY_TOP_N': 7},
                    'reason': 'should fail',
                },
            )
        finally:
            self.server.identity.build_identity_input = original_build_identity_input

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'governance_key_readonly')

    def test_identity_governance_route_maps_store_unavailable_to_http_500(self) -> None:
        current_payload = self._governance_view({'CONTEXT_HINTS_MAX_ITEMS': 2})
        observed_logs = []
        original_get_runtime_section = self.server.runtime_settings.get_runtime_section
        original_get_identity_governance_settings = self.server.runtime_settings.get_identity_governance_settings
        original_validate_runtime_section = self.server.runtime_settings.validate_runtime_section
        original_update_runtime_section = self.server.runtime_settings.update_runtime_section
        original_log_event = self.server.admin_logs.log_event
        original_build_identity_input = self.server.identity.build_identity_input

        def fake_get_runtime_section(section: str, *, fetcher=None):
            self.assertEqual(section, 'identity_governance')
            return current_payload

        def fake_get_identity_governance_settings(*, fetcher=None):
            return current_payload

        def fake_validate_runtime_section(section: str, patch_payload=None, *, fetcher=None):
            self.assertEqual(section, 'identity_governance')
            return {
                'section': section,
                'source': 'candidate',
                'source_reason': 'validate_payload',
                'valid': True,
                'checks': [{'name': 'CONTEXT_HINTS_MAX_ITEMS', 'ok': True, 'detail': 'ok'}],
            }

        def failing_update_runtime_section(section: str, patch_payload, *, updated_by='admin_api', fetcher=None):
            self.assertEqual(section, 'identity_governance')
            raise self.server.runtime_settings.RuntimeSettingsDbUnavailableError('db unavailable for governance patch')

        self.server.runtime_settings.get_runtime_section = fake_get_runtime_section
        self.server.runtime_settings.get_identity_governance_settings = fake_get_identity_governance_settings
        self.server.runtime_settings.validate_runtime_section = fake_validate_runtime_section
        self.server.runtime_settings.update_runtime_section = failing_update_runtime_section
        self.server.admin_logs.log_event = lambda event, **kwargs: observed_logs.append((event, kwargs))
        self.server.identity.build_identity_input = lambda: {'schema_version': 'v2'}
        try:
            response = self.client.post(
                '/api/admin/identity/governance',
                json={
                    'updates': {'CONTEXT_HINTS_MAX_ITEMS': 3},
                    'reason': 'store unavailable test',
                },
            )
        finally:
            self.server.runtime_settings.get_runtime_section = original_get_runtime_section
            self.server.runtime_settings.get_identity_governance_settings = original_get_identity_governance_settings
            self.server.runtime_settings.validate_runtime_section = original_validate_runtime_section
            self.server.runtime_settings.update_runtime_section = original_update_runtime_section
            self.server.admin_logs.log_event = original_log_event
            self.server.identity.build_identity_input = original_build_identity_input

        self.assertEqual(response.status_code, 500)
        payload = response.get_json()
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['reason_code'], 'governance_store_unavailable')
        self.assertEqual(payload['validation_error'], 'governance_store_unavailable')
        self.assertEqual(observed_logs[0][0], 'identity_governance_admin_edit')
        self.assertNotIn('content', observed_logs[0][1])

    def test_identity_governance_routes_are_guarded_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase5-governance-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            get_response = self.client.get('/api/admin/identity/governance')
            post_response = self.client.post(
                '/api/admin/identity/governance',
                json={'updates': {'CONTEXT_HINTS_MAX_ITEMS': 3}, 'reason': 'guard'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(post_response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
