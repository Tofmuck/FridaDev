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


class ServerAdminIdentitySurfacePhase6Tests(unittest.TestCase):
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

    def test_identity_runtime_representations_route_exposes_structured_identity_and_injected_text(self) -> None:
        original_build_identity_input = self.server.identity.build_identity_input
        original_build_identity_block = self.server.identity.build_identity_block
        original_get_latest_identity_staging_state = self.server.memory_store.get_latest_identity_staging_state
        original_read_chat_log_events = self.server.log_store.read_chat_log_events
        self.server.identity.build_identity_input = lambda: {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': 'Frida statique', 'source': 'data/identity/llm_identity.txt'},
                'mutable': {'content': 'Frida mutable', 'updated_by': 'identity_periodic_agent'},
            },
            'user': {
                'static': {'content': 'User statique', 'source': 'data/identity/user_identity.txt'},
                'mutable': {'content': 'User mutable', 'updated_by': 'identity_periodic_agent'},
            },
        }
        self.server.identity.build_identity_block = lambda: (
            "[IDENTITY]\n[STATIQUE]\nFrida statique\n[MUTABLE]\nFrida mutable",
            ['legacy-1'],
        )
        self.server.memory_store.get_latest_identity_staging_state = lambda: {
            'conversation_id': 'conv-stage-2',
            'buffer_pairs_count': 15,
            'buffer_target_pairs': 15,
            'buffer_frozen': True,
            'auto_canonization_suspended': True,
            'last_agent_status': 'auto_canonization_suspended',
            'last_agent_reason': 'double_saturation',
            'last_agent_run_ts': '2026-04-16T11:00:00Z',
            'updated_ts': '2026-04-16T11:00:01Z',
        }
        self.server.log_store.read_chat_log_events = lambda **_kwargs: {
            'items': [
                {
                    'event_id': 'evt-stage-2',
                    'conversation_id': 'conv-stage-2',
                    'turn_id': 'turn-30',
                    'ts': '2026-04-16T11:00:01Z',
                    'stage': 'identity_periodic_agent',
                    'status': 'skipped',
                    'payload': {
                        'reason_code': 'double_saturation',
                        'writes_applied': False,
                        'promotion_count': 0,
                        'promotions': [],
                        'outcomes': [
                            {
                                'subject': 'user',
                                'action': 'raise_conflict',
                                'reason_code': 'raise_conflict_open',
                                'threshold_verdict': 'deferred',
                                'strength': 0.5,
                            }
                        ],
                        'rejection_reasons': {'llm': 'double_saturation'},
                    },
                }
            ],
        }
        try:
            response = self.client.get('/api/admin/identity/runtime-representations')
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.get_latest_identity_staging_state = original_get_latest_identity_staging_state
            self.server.log_store.read_chat_log_events = original_read_chat_log_events

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['representations_version'], 'v2')
        self.assertEqual(payload['read_via'], '/api/admin/identity/runtime-representations')
        self.assertEqual(payload['active_prompt_contract'], 'static + mutable narrative')
        self.assertEqual(payload['identity_input_schema_version'], 'v2')
        self.assertTrue(payload['same_identity_basis'])
        self.assertEqual(payload['active_canon']['source_kind'], 'static + mutable')
        self.assertFalse(payload['active_canon']['staging_included'])
        self.assertTrue(payload['identity_staging']['present'])
        self.assertFalse(payload['identity_staging']['actively_injected'])
        self.assertEqual(payload['identity_staging']['scope_kind'], 'conversation_scoped_latest')
        self.assertEqual(payload['identity_staging']['conversation_id'], 'conv-stage-2')
        self.assertTrue(payload['identity_staging']['auto_canonization_suspended'])
        self.assertEqual(payload['identity_staging']['latest_agent_activity']['reason_code'], 'double_saturation')
        self.assertEqual(payload['identity_staging']['latest_agent_activity']['open_tension_count'], 1)
        self.assertEqual(
            payload['identity_staging']['latest_agent_activity']['open_tensions_storage_kind'],
            'identity_periodic_agent_latest_activity',
        )
        self.assertTrue(payload['structured_identity']['present'])
        self.assertEqual(payload['structured_identity']['technical_name'], 'identity_input')
        self.assertEqual(payload['structured_identity']['role'], 'hermeneutic_judgment')
        self.assertFalse(payload['structured_identity']['staging_included'])
        self.assertEqual(payload['structured_identity']['data']['frida']['static']['content'], 'Frida statique')
        self.assertEqual(payload['structured_identity']['data']['user']['mutable']['content'], 'User mutable')
        self.assertNotIn('staging', payload['structured_identity']['data']['frida'])
        self.assertTrue(payload['injected_identity_text']['present'])
        self.assertEqual(payload['injected_identity_text']['technical_name'], 'identity_block')
        self.assertEqual(payload['injected_identity_text']['role'], 'final_model_system_prompt')
        self.assertFalse(payload['injected_identity_text']['staging_included'])
        self.assertIn('Frida mutable', payload['injected_identity_text']['content'])
        self.assertEqual(payload['used_identity_ids'], ['legacy-1'])
        self.assertEqual(payload['used_identity_ids_count'], 1)

    def test_identity_page_route_exists(self) -> None:
        response = self.client.get('/identity')
        try:
            self.assertEqual(response.status_code, 200)
            source = response.get_data(as_text=True)
            self.assertIn('<title>Identity</title>', source)
            self.assertIn('Pilotage canonique actif', source)
            self.assertIn('Repere runtime compile utile au pilotage', source)
            self.assertIn('Voir le detail diagnostique', source)
            self.assertIn('href="/hermeneutic-admin#hermeneutic-identity-runtime-title"', source)
            self.assertIn('Pilotage systeme distinct', source)
            self.assertIn('Diagnostics / historique', source)
            self.assertIn('id="identityDiagnosticsDisclosure"', source)
            self.assertIn('Replie par defaut', source)
            self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-current-state-title"'))
            self.assertLess(source.index('id="identity-pilotage-title"'), source.index('id="identity-runtime-summary-title"'))
            self.assertLess(source.index('id="identity-governance-title"'), source.index('id="identity-diagnostics-title"'))
            self.assertLess(source.index('id="identityLlmStaticCard"'), source.index('id="identityUserMutableCard"'))
            self.assertNotIn('id="identityStructuredRepresentation"', source)
            self.assertNotIn('id="identityInjectedRepresentation"', source)
        finally:
            response.close()

    def test_identity_runtime_representations_route_is_available_without_admin_token(self) -> None:
        response = self.client.get('/api/admin/identity/runtime-representations')
        self.assertNotIn(response.status_code, {401, 403})


if __name__ == '__main__':
    unittest.main()
