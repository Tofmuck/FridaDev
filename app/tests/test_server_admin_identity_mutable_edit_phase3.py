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


class ServerAdminIdentityMutableEditPhase3Tests(unittest.TestCase):
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

    def test_identity_mutable_edit_route_updates_canonical_source_only(self) -> None:
        observed = {'upsert': [], 'clear': [], 'logs': []}
        current = {'llm': {'subject': 'llm', 'content': 'Frida reste sobre.'}}

        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_get_identities = self.server.memory_store.get_identities
        original_log_event = self.server.admin_logs.log_event

        def fake_get_mutable_identity(subject: str):
            item = current.get(subject)
            return dict(item) if item is not None else None

        def fake_upsert_mutable_identity(subject: str, content: str, **kwargs):
            observed['upsert'].append((subject, content, kwargs))
            current[subject] = {'subject': subject, 'content': content}
            return {'subject': subject, 'content': content, **kwargs}

        def fake_clear_mutable_identity(subject: str):
            observed['clear'].append(subject)
            previous = current.pop(subject, None)
            return dict(previous) if previous is not None else None

        def fake_log_event(event: str, **kwargs):
            observed['logs'].append((event, kwargs))

        self.server.memory_store.get_mutable_identity = fake_get_mutable_identity
        self.server.memory_store.upsert_mutable_identity = fake_upsert_mutable_identity
        self.server.memory_store.clear_mutable_identity = fake_clear_mutable_identity
        self.server.memory_store.get_identities = lambda *_args, **_kwargs: self.fail(
            'legacy get_identities must stay outside canonical mutable edit'
        )
        self.server.admin_logs.log_event = fake_log_event
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'llm',
                    'action': 'set',
                    'content': 'Frida reste sobre, concise et structuree.',
                    'reason': 'manual update',
                },
            )
        finally:
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.memory_store.get_identities = original_get_identities
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['subject'], 'llm')
        self.assertEqual(data['action'], 'set')
        self.assertTrue(data['changed'])
        self.assertTrue(data['stored_after'])
        self.assertEqual(data['active_identity_source'], 'identity_mutables')
        self.assertEqual(data['active_prompt_contract'], 'static + mutable narrative')
        self.assertEqual(data['identity_input_schema_version'], 'v2')
        self.assertTrue(data['identity_runtime_regime']['staging_not_injected'])
        self.assertEqual(data['identity_runtime_regime']['mutable_budget']['target_chars'], 3000)
        self.assertEqual(len(observed['upsert']), 1)
        self.assertEqual(observed['clear'], [])
        self.assertEqual(observed['logs'][0][0], 'identity_mutable_admin_edit')
        self.assertNotIn('content', observed['logs'][0][1])
        self.assertNotIn('reason', observed['logs'][0][1])

    def test_identity_mutable_edit_route_accepts_durable_technical_orientation(self) -> None:
        observed = {'upsert': [], 'clear': [], 'logs': []}
        current = {'user': {'subject': 'user', 'content': 'Utilisateur garde une orientation stable.'}}

        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_log_event = self.server.admin_logs.log_event

        def fake_get_mutable_identity(subject: str):
            item = current.get(subject)
            return dict(item) if item is not None else None

        def fake_upsert_mutable_identity(subject: str, content: str, **kwargs):
            observed['upsert'].append((subject, content, kwargs))
            current[subject] = {'subject': subject, 'content': content}
            return {'subject': subject, 'content': content, **kwargs}

        self.server.memory_store.get_mutable_identity = fake_get_mutable_identity
        self.server.memory_store.upsert_mutable_identity = fake_upsert_mutable_identity
        self.server.memory_store.clear_mutable_identity = lambda *_args, **_kwargs: self.fail('clear must not be used')
        self.server.admin_logs.log_event = lambda event, **kwargs: observed['logs'].append((event, kwargs))
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'user',
                    'action': 'set',
                    'content': 'Tof garde une attention stable aux architectures lisibles et aux structures techniques coherentes.',
                    'reason': 'orientation identitaire durable',
                },
            )
        finally:
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reason_code'], 'set_applied')
        self.assertEqual(len(observed['upsert']), 1)
        self.assertIn('architectures lisibles', observed['upsert'][0][1])

    def test_identity_mutable_edit_route_supports_clear(self) -> None:
        current = {'user': {'subject': 'user', 'content': 'Utilisateur garde une orientation stable.'}}
        observed = {'logs': []}
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_log_event = self.server.admin_logs.log_event

        self.server.memory_store.get_mutable_identity = lambda subject: dict(current[subject]) if subject in current else None
        self.server.memory_store.upsert_mutable_identity = lambda *_args, **_kwargs: self.fail('set must not be used for clear')

        def fake_clear_mutable_identity(subject: str):
            previous = current.pop(subject, None)
            return dict(previous) if previous is not None else None

        self.server.memory_store.clear_mutable_identity = fake_clear_mutable_identity
        self.server.admin_logs.log_event = lambda event, **kwargs: observed['logs'].append((event, kwargs))
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'user',
                    'action': 'clear',
                    'content': '',
                    'reason': 'obsolete',
                },
            )
        finally:
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['reason_code'], 'clear_applied')
        self.assertFalse(data['stored_after'])
        self.assertEqual(observed['logs'][0][1]['reason_code'], 'clear_applied')

    def test_identity_mutable_edit_route_rejects_invalid_payload_fail_closed(self) -> None:
        observed = {'upsert': False, 'clear': False, 'logs': []}
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_log_event = self.server.admin_logs.log_event

        self.server.memory_store.upsert_mutable_identity = lambda *_args, **_kwargs: observed.__setitem__('upsert', True)
        self.server.memory_store.clear_mutable_identity = lambda *_args, **_kwargs: observed.__setitem__('clear', True)
        self.server.admin_logs.log_event = lambda event, **kwargs: observed['logs'].append((event, kwargs))
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'llm',
                    'action': 'set',
                    'content': '',
                    'reason': '',
                },
            )
        finally:
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['validation_error'], 'contract_reason_missing')
        self.assertFalse(observed['upsert'])
        self.assertFalse(observed['clear'])
        self.assertEqual(observed['logs'][0][1]['validation_error'], 'contract_reason_missing')

    def test_identity_mutable_edit_route_rejects_prompt_like_content_in_english(self) -> None:
        observed = {'upsert': False, 'logs': []}
        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_log_event = self.server.admin_logs.log_event

        self.server.memory_store.get_mutable_identity = lambda subject: {'subject': subject, 'content': 'Frida reste sobre.'}
        self.server.memory_store.upsert_mutable_identity = lambda *_args, **_kwargs: observed.__setitem__('upsert', True)
        self.server.memory_store.clear_mutable_identity = lambda *_args, **_kwargs: self.fail('clear must not be called')
        self.server.admin_logs.log_event = lambda event, **kwargs: observed['logs'].append((event, kwargs))
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'llm',
                    'action': 'set',
                    'content': 'You must verify sources and cite each important point.',
                    'reason': 'probe only',
                },
            )
        finally:
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(
            data['validation_error'],
            'mutable_content_prompt_like_operator_instruction',
        )
        self.assertFalse(observed['upsert'])
        self.assertEqual(
            observed['logs'][0][1]['validation_error'],
            'mutable_content_prompt_like_operator_instruction',
        )

    def test_identity_mutable_edit_route_keeps_staging_visible_and_read_model_consistent(self) -> None:
        observed = {'upsert': [], 'logs': []}
        current = {
            'llm': {'subject': 'llm', 'content': 'Frida garde une voix sobre.'},
            'user': None,
        }
        staging_state = {
            'conversation_id': 'conv-stage-preserved',
            'buffer_pairs': [
                {
                    'user': {'role': 'user', 'content': 'Bonjour'},
                    'assistant': {'role': 'assistant', 'content': 'Salut'},
                }
            ],
            'buffer_pairs_count': 7,
            'buffer_target_pairs': 15,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'last_agent_status': 'buffering',
            'last_agent_reason': 'below_threshold',
            'last_agent_run_ts': '2026-04-18T09:00:00Z',
            'updated_ts': '2026-04-18T09:00:30Z',
        }
        updated_content = 'Frida garde une voix sobre, stable et precise.'

        original_get_mutable_identity = self.server.memory_store.get_mutable_identity
        original_upsert_mutable_identity = self.server.memory_store.upsert_mutable_identity
        original_clear_mutable_identity = self.server.memory_store.clear_mutable_identity
        original_get_latest_identity_staging_state = self.server.memory_store.get_latest_identity_staging_state
        original_append_identity_staging_pair = self.server.memory_store.append_identity_staging_pair
        original_mark_identity_staging_status = self.server.memory_store.mark_identity_staging_status
        original_clear_identity_staging_buffer = self.server.memory_store.clear_identity_staging_buffer
        original_build_identity_input = self.server.identity.build_identity_input
        original_build_identity_block = self.server.identity.build_identity_block
        original_list_identity_fragments = self.server.memory_store.list_identity_fragments
        original_list_identity_evidence = self.server.memory_store.list_identity_evidence
        original_list_identity_conflicts = self.server.memory_store.list_identity_conflicts
        original_read_static_identity_snapshot = self.server.static_identity_content.read_static_identity_snapshot
        original_read_chat_log_events = self.server.log_store.read_chat_log_events
        original_log_event = self.server.admin_logs.log_event

        def fake_get_mutable_identity(subject: str):
            item = current.get(subject)
            return dict(item) if isinstance(item, dict) else None

        def fake_upsert_mutable_identity(subject: str, content: str, **kwargs):
            observed['upsert'].append((subject, content, kwargs))
            current[subject] = {'subject': subject, 'content': content}
            return {'subject': subject, 'content': content, **kwargs}

        def fake_build_identity_input():
            return {
                'schema_version': 'v2',
                'frida': {
                    'static': {'content': 'Frida static canonique', 'source': 'data/identity/llm_identity.txt'},
                    'mutable': {
                        'content': str((current.get('llm') or {}).get('content') or ''),
                        'updated_by': 'operator',
                    },
                },
                'user': {
                    'static': {'content': 'User static canonique', 'source': 'data/identity/user_identity.txt'},
                    'mutable': {},
                },
            }

        def fake_read_static_identity_snapshot(subject: str):
            return self.server.static_identity_content.StaticIdentitySnapshot(
                subject=subject,
                resource_field='llm_identity_path' if subject == 'llm' else 'user_identity_path',
                configured_path=f'data/identity/{subject}_identity.txt',
                resolution_kind='absolute',
                resolved_path=Path(f'/tmp/{subject}_identity.txt'),
                content='Frida static canonique' if subject == 'llm' else 'User static canonique',
                raw_content='Frida static canonique' if subject == 'llm' else 'User static canonique',
            )

        self.server.memory_store.get_mutable_identity = fake_get_mutable_identity
        self.server.memory_store.upsert_mutable_identity = fake_upsert_mutable_identity
        self.server.memory_store.clear_mutable_identity = lambda *_args, **_kwargs: self.fail('clear must not be used')
        self.server.memory_store.get_latest_identity_staging_state = lambda: dict(staging_state)
        self.server.memory_store.append_identity_staging_pair = lambda *_args, **_kwargs: self.fail(
            'mutable edit must not append staging pairs'
        )
        self.server.memory_store.mark_identity_staging_status = lambda *_args, **_kwargs: self.fail(
            'mutable edit must not rewrite staging status'
        )
        self.server.memory_store.clear_identity_staging_buffer = lambda *_args, **_kwargs: self.fail(
            'mutable edit must not clear the staging buffer'
        )
        self.server.identity.build_identity_input = fake_build_identity_input
        self.server.identity.build_identity_block = lambda: ('ignored active block', [])
        self.server.memory_store.list_identity_fragments = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
        self.server.memory_store.list_identity_evidence = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
        self.server.memory_store.list_identity_conflicts = lambda *_args, **_kwargs: {'total_count': 0, 'limit': 20, 'items': []}
        self.server.static_identity_content.read_static_identity_snapshot = fake_read_static_identity_snapshot
        self.server.log_store.read_chat_log_events = lambda **_kwargs: {'items': []}
        self.server.admin_logs.log_event = lambda event, **kwargs: observed['logs'].append((event, kwargs))
        try:
            edit_response = self.client.post(
                '/api/admin/identity/mutable',
                json={
                    'subject': 'llm',
                    'action': 'set',
                    'content': updated_content,
                    'reason': 'operator alignment',
                },
            )
            read_model_response = self.client.get('/api/admin/identity/read-model')
        finally:
            self.server.memory_store.get_mutable_identity = original_get_mutable_identity
            self.server.memory_store.upsert_mutable_identity = original_upsert_mutable_identity
            self.server.memory_store.clear_mutable_identity = original_clear_mutable_identity
            self.server.memory_store.get_latest_identity_staging_state = original_get_latest_identity_staging_state
            self.server.memory_store.append_identity_staging_pair = original_append_identity_staging_pair
            self.server.memory_store.mark_identity_staging_status = original_mark_identity_staging_status
            self.server.memory_store.clear_identity_staging_buffer = original_clear_identity_staging_buffer
            self.server.identity.build_identity_input = original_build_identity_input
            self.server.identity.build_identity_block = original_build_identity_block
            self.server.memory_store.list_identity_fragments = original_list_identity_fragments
            self.server.memory_store.list_identity_evidence = original_list_identity_evidence
            self.server.memory_store.list_identity_conflicts = original_list_identity_conflicts
            self.server.static_identity_content.read_static_identity_snapshot = original_read_static_identity_snapshot
            self.server.log_store.read_chat_log_events = original_read_chat_log_events
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(edit_response.status_code, 200)
        edit_payload = edit_response.get_json()
        self.assertTrue(edit_payload['ok'])
        self.assertEqual(edit_payload['reason_code'], 'set_applied')
        self.assertEqual(edit_payload['identity_runtime_regime']['last_agent_status'], 'buffering')
        self.assertFalse(edit_payload['identity_runtime_regime']['auto_canonization_suspended'])
        self.assertEqual(len(observed['upsert']), 1)
        self.assertEqual(observed['upsert'][0][0], 'llm')
        self.assertEqual(observed['upsert'][0][1], updated_content)
        self.assertNotIn('content', observed['logs'][0][1])

        self.assertEqual(read_model_response.status_code, 200)
        read_model = read_model_response.get_json()
        self.assertTrue(read_model['ok'])
        self.assertEqual(read_model['active_runtime']['active_identity_source'], 'identity_mutables')
        self.assertTrue(read_model['active_runtime']['identity_runtime_regime']['staging_not_injected'])
        self.assertEqual(read_model['subjects']['llm']['mutable']['content'], updated_content)
        self.assertTrue(read_model['subjects']['llm']['mutable']['actively_injected'])
        self.assertEqual(read_model['identity_staging']['conversation_id'], 'conv-stage-preserved')
        self.assertEqual(read_model['identity_staging']['buffer_pairs_count'], 7)
        self.assertEqual(read_model['identity_staging']['buffer_target_pairs'], 15)
        self.assertEqual(read_model['identity_staging']['last_agent_status'], 'buffering')
        self.assertFalse(read_model['identity_staging']['actively_injected'])
        self.assertNotIn('buffer_pairs', read_model['identity_staging'])

    def test_identity_mutable_edit_route_is_available_without_admin_token(self) -> None:
        response = self.client.post(
            '/api/admin/identity/mutable',
            json={'subject': 'llm', 'action': 'clear', 'content': '', 'reason': 'cleanup'},
        )

        self.assertNotIn(response.status_code, {401, 403})


if __name__ == '__main__':
    unittest.main()
