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
        self.assertEqual(len(observed['upsert']), 1)
        self.assertEqual(observed['clear'], [])
        self.assertEqual(observed['logs'][0][0], 'identity_mutable_admin_edit')
        self.assertNotIn('content', observed['logs'][0][1])
        self.assertNotIn('reason', observed['logs'][0][1])

    def test_identity_mutable_edit_route_supports_clear(self) -> None:
        current = {'user': {'subject': 'user', 'content': 'Utilisateur prefere la clarte.'}}
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

    def test_identity_mutable_edit_route_is_guarded_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase3-identity-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            response = self.client.post(
                '/api/admin/identity/mutable',
                json={'subject': 'llm', 'action': 'clear', 'content': '', 'reason': 'cleanup'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only

        self.assertEqual(response.status_code, 401)


if __name__ == '__main__':
    unittest.main()
