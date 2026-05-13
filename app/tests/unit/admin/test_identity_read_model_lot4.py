from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_read_model_service


class _MemoryStore:
    def get_latest_identity_staging_state(self) -> dict[str, object]:
        return {}

    def get_latest_mutable_identity_audit(self, subject: str) -> dict[str, object] | None:
        if subject != 'llm':
            return None
        return {
            'audit_id': '00000000-0000-0000-0000-000000000044',
            'subject': 'llm',
            'mutation_kind': 'clear',
            'actor': 'admin_identity_mutable_edit',
            'reason_code': 'clear_applied',
            'old_chars': 74,
            'new_chars': 0,
            'old_sha256_12': 'a1b2c3d4e5f6',
            'new_sha256_12': None,
            'source_trace_id': '00000000-0000-0000-0000-000000000011',
            'created_ts': '2026-05-13T15:00:00+00:00',
        }

    def list_identity_fragments(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {'total_count': 0, 'limit': 20, 'items': []}

    def list_identity_evidence(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {'total_count': 0, 'limit': 20, 'items': []}

    def list_identity_conflicts(self, *_args: Any, **_kwargs: Any) -> dict[str, object]:
        return {'total_count': 0, 'limit': 20, 'items': []}


class _IdentityModule:
    def build_identity_input(self) -> dict[str, object]:
        return {
            'schema_version': 'v2',
            'frida': {'static': {'content': ''}, 'mutable': {}},
            'user': {'static': {'content': ''}, 'mutable': {}},
        }

    def build_identity_block(self) -> tuple[str, list[str]]:
        return '', []


class _StaticIdentityContent:
    def read_static_identity_snapshot(self, subject: str) -> SimpleNamespace:
        return SimpleNamespace(
            subject=subject,
            resource_field='llm_identity_path' if subject == 'llm' else 'user_identity_path',
            configured_path=f'data/identity/{subject}_identity.txt',
            resolution_kind='absolute',
            resolved_path=Path(f'/tmp/{subject}_identity.txt'),
            content='',
            raw_content='',
        )


class _LogStore:
    def read_chat_log_events(self, **_kwargs: object) -> dict[str, object]:
        return {'items': []}


class IdentityReadModelLot4Tests(unittest.TestCase):
    def test_mutable_layer_exposes_last_audit_for_absent_mutable_without_raw_content(self) -> None:
        payload, status = admin_identity_read_model_service.identity_read_model_response(
            {},
            memory_store_module=_MemoryStore(),
            identity_module=_IdentityModule(),
            static_identity_content_module=_StaticIdentityContent(),
            log_store_module=_LogStore(),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])

        llm_mutable = payload['subjects']['llm']['mutable']
        self.assertFalse(llm_mutable['stored'])
        self.assertFalse(llm_mutable['actively_injected'])
        llm_audit = llm_mutable['last_mutation_audit']
        admin_reason = 'obsolete mutable parce que contexte humain libre'
        self.assertTrue(llm_audit['present'])
        self.assertFalse(llm_audit['actively_injected'])
        self.assertEqual(llm_audit['storage_kind'], 'identity_mutable_audit')
        self.assertEqual(llm_audit['mutation_kind'], 'clear')
        self.assertEqual(llm_audit['actor'], 'admin_identity_mutable_edit')
        self.assertEqual(llm_audit['reason_code'], 'clear_applied')
        self.assertEqual(llm_audit['old_chars'], 74)
        self.assertEqual(llm_audit['new_chars'], 0)
        self.assertEqual(llm_audit['old_sha256_12'], 'a1b2c3d4e5f6')
        self.assertIsNone(llm_audit['new_sha256_12'])
        self.assertNotIn('content', llm_audit)
        self.assertNotIn('prompt', llm_audit)
        self.assertNotIn('messages', llm_audit)
        self.assertNotIn('admin_reason', llm_audit)
        self.assertNotIn(admin_reason, repr(llm_audit))

        user_audit = payload['subjects']['user']['mutable']['last_mutation_audit']
        self.assertFalse(user_audit['present'])
        self.assertEqual(user_audit['storage_kind'], 'identity_mutable_audit')
        self.assertFalse(user_audit['actively_injected'])
        self.assertIsNone(user_audit['mutation_kind'])


if __name__ == '__main__':
    unittest.main()
