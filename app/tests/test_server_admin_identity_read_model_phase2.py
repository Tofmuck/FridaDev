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


class ServerAdminIdentityReadModelPhase2Tests(unittest.TestCase):
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

    def test_identity_read_model_route_exposes_unified_contract_without_using_legacy_injection_truth(self) -> None:
        observed = {
            'fragments': [],
            'evidence': [],
            'conflicts': [],
        }
        original_build_identity_input = self.server.identity.build_identity_input
        original_build_identity_block = self.server.identity.build_identity_block
        original_list_identity_fragments = self.server.memory_store.list_identity_fragments
        original_list_identity_evidence = self.server.memory_store.list_identity_evidence
        original_list_identity_conflicts = self.server.memory_store.list_identity_conflicts
        original_get_identities = self.server.memory_store.get_identities
        original_get_latest_identity_staging_state = self.server.memory_store.get_latest_identity_staging_state
        original_read_static_identity_snapshot = self.server.static_identity_content.read_static_identity_snapshot
        original_read_chat_log_events = self.server.log_store.read_chat_log_events

        def fake_list_identity_fragments(subject: str, limit: int | None = None):
            observed['fragments'].append((subject, limit))
            return {
                'total_count': 1,
                'limit': limit,
                'items': [
                    {
                        'identity_id': f'{subject}-legacy-1',
                        'content': f'{subject} legacy fragment',
                        'status': 'accepted',
                    }
                ],
            }

        def fake_list_identity_evidence(subject: str, limit: int | None = None):
            observed['evidence'].append((subject, limit))
            return {
                'total_count': 1,
                'limit': limit,
                'items': [
                    {
                        'evidence_id': f'{subject}-evidence-1',
                        'content': f'{subject} evidence entry',
                        'status': 'accepted',
                    }
                ],
            }

        def fake_list_identity_conflicts(subject: str, limit: int | None = None):
            observed['conflicts'].append((subject, limit))
            return {
                'total_count': 1,
                'limit': limit,
                'items': [
                    {
                        'conflict_id': f'{subject}-conflict-1',
                        'content_a': f'{subject} conflict a',
                        'content_b': f'{subject} conflict b',
                        'resolved_state': 'open',
                    }
                ],
            }

        self.server.identity.build_identity_input = lambda: {
            'schema_version': 'v2',
            'frida': {
                'static': {'content': 'Frida static canonique', 'source': 'data/identity/llm_identity.txt'},
                'mutable': {
                    'content': 'Frida mutable canonique',
                    'source_trace_id': '11111111-1111-1111-1111-111111111111',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-04-06T09:00:00Z',
                },
            },
            'user': {
                'static': {'content': 'User static canonique', 'source': 'data/identity/user_identity.txt'},
                'mutable': {
                    'content': 'User mutable canonique',
                    'source_trace_id': '22222222-2222-2222-2222-222222222222',
                    'updated_by': 'identity_periodic_agent',
                    'update_reason': 'periodic_agent',
                    'updated_ts': '2026-04-06T10:00:00Z',
                },
            },
        }
        self.server.identity.build_identity_block = lambda: ('ignored active block', [])
        self.server.memory_store.list_identity_fragments = fake_list_identity_fragments
        self.server.memory_store.list_identity_evidence = fake_list_identity_evidence
        self.server.memory_store.list_identity_conflicts = fake_list_identity_conflicts
        self.server.memory_store.get_latest_identity_staging_state = lambda: {
            'conversation_id': 'conv-stage-1',
            'buffer_pairs': [],
            'buffer_pairs_count': 4,
            'buffer_target_pairs': 15,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'last_agent_status': 'buffering',
            'last_agent_reason': 'below_threshold',
            'last_agent_run_ts': '2026-04-16T10:00:00Z',
            'updated_ts': '2026-04-16T10:00:30Z',
        }
        self.server.static_identity_content.read_static_identity_snapshot = lambda subject: self.server.static_identity_content.StaticIdentitySnapshot(
            subject=subject,
            resource_field='llm_identity_path' if subject == 'llm' else 'user_identity_path',
            configured_path=f'data/identity/{subject}_identity.txt',
            resolution_kind='absolute',
            resolved_path=Path(f'/tmp/{subject}_identity.txt'),
            content='Frida static canonique' if subject == 'llm' else 'User static canonique',
            raw_content='Frida static canonique' if subject == 'llm' else 'User static canonique',
        )
        self.server.log_store.read_chat_log_events = lambda **_kwargs: {
            'items': [
                {
                    'event_id': 'evt-stage-1',
                    'conversation_id': 'conv-stage-1',
                    'turn_id': 'turn-15',
                    'ts': '2026-04-16T10:00:31Z',
                    'stage': 'identity_periodic_agent',
                    'status': 'ok',
                    'payload': {
                        'reason_code': 'completed_with_open_tension',
                        'writes_applied': False,
                        'promotion_count': 1,
                        'outcomes': [
                            {
                                'subject': 'user',
                                'action': 'raise_conflict',
                                'reason_code': 'raise_conflict',
                                'threshold_verdict': 'accepted',
                                'strength': 0.7333,
                            }
                        ],
                        'promotions': [
                            {
                                'subject': 'llm',
                                'operation_kind': 'add',
                                'promotion_reason_code': 'promoted_to_static',
                                'threshold_verdict': 'accepted',
                                'strength': 0.9,
                            }
                        ],
                        'rejection_reasons': {},
                    },
                }
            ],
        }
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities should not define active runtime truth for the unified read model'
        )
        try:
            response = self.client.get('/api/admin/identity/read-model?limit=oops')
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.list_identity_fragments = original_list_identity_fragments
            self.server.memory_store.list_identity_evidence = original_list_identity_evidence
            self.server.memory_store.list_identity_conflicts = original_list_identity_conflicts
            self.server.memory_store.get_identities = original_get_identities
            self.server.memory_store.get_latest_identity_staging_state = original_get_latest_identity_staging_state
            self.server.static_identity_content.read_static_identity_snapshot = original_read_static_identity_snapshot
            self.server.log_store.read_chat_log_events = original_read_chat_log_events

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['read_model_version'], 'v2')
        self.assertEqual(data['active_runtime']['active_identity_source'], 'identity_mutables')
        self.assertEqual(data['active_runtime']['active_static_source'], 'resource_path_content')
        self.assertEqual(data['active_runtime']['active_prompt_contract'], 'static + mutable narrative')
        self.assertEqual(data['active_runtime']['identity_input_schema_version'], 'v2')
        self.assertEqual(data['active_runtime']['used_identity_ids'], [])
        self.assertEqual(data['active_runtime']['used_identity_ids_count'], 0)
        self.assertEqual(data['active_runtime']['static_editable_via'], '/api/admin/identity/static')
        self.assertEqual(data['active_runtime']['mutable_editable_via'], '/api/admin/identity/mutable')
        self.assertEqual(data['active_runtime']['governance_read_via'], '/api/admin/identity/governance')
        self.assertEqual(data['active_runtime']['governance_editable_via'], '/api/admin/identity/governance')
        self.assertEqual(
            data['active_runtime']['runtime_representations_read_via'],
            '/api/admin/identity/runtime-representations',
        )
        self.assertEqual(data['active_runtime']['legacy_identity_pipeline_status'], 'legacy_diagnostic_only')
        self.assertEqual(data['active_runtime']['legacy_identity_pipeline_recorded_via'], 'persist_identity_entries')
        self.assertEqual(
            data['active_runtime']['legacy_identity_pipeline_storage'],
            'identities + identity_evidence + identity_conflicts',
        )
        self.assertFalse(data['active_runtime']['legacy_drives_active_injection'])
        self.assertEqual(data['active_runtime']['read_surface_stage'], 'lot_b5_identity_operator_truth')
        self.assertTrue(data['active_runtime']['identity_runtime_regime']['staging_not_injected'])
        self.assertEqual(data['active_runtime']['identity_runtime_regime']['mutable_budget']['target_chars'], 3000)
        self.assertEqual(data['identity_staging']['storage_kind'], 'identity_mutable_staging')
        self.assertEqual(data['identity_staging']['scope_kind'], 'conversation_scoped_latest')
        self.assertFalse(data['identity_staging']['actively_injected'])
        self.assertEqual(data['identity_staging']['buffer_pairs_count'], 4)
        self.assertEqual(data['identity_staging']['buffer_target_pairs'], 15)
        self.assertEqual(data['identity_staging']['last_agent_status'], 'buffering')
        self.assertEqual(
            data['identity_staging']['latest_agent_activity']['reason_code'],
            'completed_with_open_tension',
        )
        self.assertEqual(data['identity_staging']['latest_agent_activity']['promotion_count'], 1)
        self.assertEqual(data['identity_staging']['latest_agent_activity']['open_tension_count'], 1)
        self.assertEqual(
            data['identity_staging']['latest_agent_activity']['open_tensions_storage_kind'],
            'identity_periodic_agent_latest_activity',
        )
        self.assertEqual(
            data['identity_staging']['latest_agent_activity']['open_tensions_scope_kind'],
            'conversation_scoped_latest',
        )
        self.assertFalse(data['identity_staging']['latest_agent_activity']['open_tensions_actively_injected'])
        self.assertEqual(
            data['identity_staging']['latest_agent_activity']['open_tensions'][0]['action'],
            'raise_conflict',
        )
        self.assertEqual(
            data['identity_staging']['latest_agent_activity']['open_tensions'][0]['reason_code'],
            'raise_conflict',
        )
        self.assertEqual(observed['fragments'], [('llm', 20), ('user', 20)])
        self.assertEqual(observed['evidence'], [('llm', 20), ('user', 20)])
        self.assertEqual(observed['conflicts'], [('llm', 20), ('user', 20)])
        self.assertEqual(data['subjects']['llm']['static']['content'], 'Frida static canonique')
        self.assertTrue(data['subjects']['llm']['static']['loaded_for_runtime'])
        self.assertTrue(data['subjects']['llm']['static']['actively_injected'])
        self.assertEqual(data['subjects']['llm']['static']['resource_field'], 'llm_identity_path')
        self.assertEqual(data['subjects']['llm']['static']['configured_path'], 'data/identity/llm_identity.txt')
        self.assertEqual(data['subjects']['llm']['static']['resolution_kind'], 'absolute')
        self.assertEqual(data['subjects']['llm']['static']['editable_via'], '/api/admin/identity/static')
        self.assertEqual(data['subjects']['llm']['mutable']['content'], 'Frida mutable canonique')
        self.assertTrue(data['subjects']['llm']['mutable']['actively_injected'])
        self.assertFalse(data['subjects']['llm']['legacy_fragments']['actively_injected'])
        self.assertEqual(data['subjects']['llm']['legacy_fragments']['storage_kind'], 'identities')
        self.assertEqual(data['subjects']['llm']['legacy_fragments']['classification'], 'legacy_diagnostic_only')
        self.assertEqual(data['subjects']['llm']['legacy_fragments']['runtime_authority'], 'historical_only')
        self.assertEqual(data['subjects']['llm']['evidence']['storage_kind'], 'identity_evidence')
        self.assertEqual(data['subjects']['llm']['evidence']['classification'], 'legacy_diagnostic_only')
        self.assertEqual(data['subjects']['llm']['evidence']['runtime_authority'], 'historical_only')
        self.assertEqual(data['subjects']['llm']['conflicts']['storage_kind'], 'identity_conflicts')
        self.assertEqual(data['subjects']['llm']['conflicts']['classification'], 'legacy_diagnostic_only')
        self.assertEqual(data['subjects']['llm']['conflicts']['runtime_authority'], 'historical_only')
        self.assertEqual(data['subjects']['user']['mutable']['content'], 'User mutable canonique')

    def test_identity_read_model_static_layer_distinguishes_raw_storage_from_runtime_trimmed_content(self) -> None:
        original_build_identity_input = self.server.identity.build_identity_input
        original_build_identity_block = self.server.identity.build_identity_block
        original_list_identity_fragments = self.server.memory_store.list_identity_fragments
        original_list_identity_evidence = self.server.memory_store.list_identity_evidence
        original_list_identity_conflicts = self.server.memory_store.list_identity_conflicts
        original_read_static_identity_snapshot = self.server.static_identity_content.read_static_identity_snapshot
        try:
            self.server.identity.build_identity_input = lambda: {
                'schema_version': 'v2',
                'frida': {'static': {'content': '', 'source': 'data/identity/llm_identity.txt'}, 'mutable': {}},
                'user': {'static': {'content': '', 'source': 'data/identity/user_identity.txt'}, 'mutable': {}},
            }
            self.server.identity.build_identity_block = lambda: ('ignored', [])
            self.server.memory_store.list_identity_fragments = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
            self.server.memory_store.list_identity_evidence = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
            self.server.memory_store.list_identity_conflicts = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
            self.server.static_identity_content.read_static_identity_snapshot = lambda subject: self.server.static_identity_content.StaticIdentitySnapshot(
                subject=subject,
                resource_field='llm_identity_path' if subject == 'llm' else 'user_identity_path',
                configured_path=f'data/identity/{subject}_identity.txt',
                resolution_kind='host_state_mirror',
                resolved_path=Path(f'/tmp/{subject}_identity.txt'),
                content='',
                raw_content='\n',
                within_allowed_roots=True,
            )
            response = self.client.get('/api/admin/identity/read-model')
        finally:
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.list_identity_fragments = original_list_identity_fragments
            self.server.memory_store.list_identity_evidence = original_list_identity_evidence
            self.server.memory_store.list_identity_conflicts = original_list_identity_conflicts
            self.server.static_identity_content.read_static_identity_snapshot = original_read_static_identity_snapshot

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['subjects']['llm']['static']['stored'])
        self.assertFalse(data['subjects']['llm']['static']['loaded_for_runtime'])
        self.assertFalse(data['subjects']['llm']['static']['actively_injected'])

    def test_identity_read_model_route_is_available_without_admin_token(self) -> None:
        response = self.client.get('/api/admin/identity/read-model')
        self.assertNotIn(response.status_code, {401, 403})


if __name__ == '__main__':
    unittest.main()
