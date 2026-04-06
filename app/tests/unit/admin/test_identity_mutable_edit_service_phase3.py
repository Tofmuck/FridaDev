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

from admin import admin_identity_mutable_edit_service


class _MutableStore:
    def __init__(self, initial: dict[str, str] | None = None) -> None:
        self.state = dict(initial or {})
        self.upsert_calls: list[tuple[str, str, str, str]] = []
        self.clear_calls: list[str] = []

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        content = self.state.get(subject, '')
        if not content:
            return None
        return {'subject': subject, 'content': content}

    def upsert_mutable_identity(
        self,
        subject: str,
        content: str,
        source_trace_id: str | None = None,
        *,
        updated_by: str = 'system',
        update_reason: str = '',
    ) -> dict[str, Any] | None:
        self.upsert_calls.append((subject, content, updated_by, update_reason))
        self.state[subject] = content
        return {
            'subject': subject,
            'content': content,
            'source_trace_id': source_trace_id,
            'updated_by': updated_by,
            'update_reason': update_reason,
        }

    def clear_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        self.clear_calls.append(subject)
        previous = self.state.pop(subject, '')
        if not previous:
            return None
        return {'subject': subject, 'content': previous}


class IdentityMutableEditServicePhase3Tests(unittest.TestCase):
    def test_set_valid_updates_canonical_mutable_and_logs_without_raw_content(self) -> None:
        store = _MutableStore({'llm': 'Frida reste sobre.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'llm',
                'action': 'set',
                'content': 'Frida reste sobre, concise et structuree.',
                'reason': 'correction operateur',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['changed'])
        self.assertEqual(payload['reason_code'], 'set_applied')
        self.assertTrue(payload['stored_after'])
        self.assertEqual(payload['active_identity_source'], 'identity_mutables')
        self.assertEqual(store.state['llm'], 'Frida reste sobre, concise et structuree.')
        self.assertEqual(store.upsert_calls[0][2], 'admin_identity_mutable_edit')
        event_name, event_payload = observed_logs[0]
        self.assertEqual(event_name, 'identity_mutable_admin_edit')
        self.assertNotIn('content', event_payload)
        self.assertNotIn('reason', event_payload)
        self.assertEqual(event_payload['reason_code'], 'set_applied')

    def test_clear_valid_removes_canonical_mutable(self) -> None:
        store = _MutableStore({'user': 'Utilisateur prefere la clarte.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'user',
                'action': 'clear',
                'content': '',
                'reason': 'obsolete mutable',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['changed'])
        self.assertEqual(payload['reason_code'], 'clear_applied')
        self.assertFalse(payload['stored_after'])
        self.assertNotIn('user', store.state)
        self.assertEqual(store.clear_calls, ['user'])
        self.assertEqual(observed_logs[0][1]['reason_code'], 'clear_applied')

    def test_rejects_content_above_hard_cap_without_write(self) -> None:
        store = _MutableStore({'llm': 'Frida reste sobre.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'llm',
                'action': 'set',
                'content': 'x' * 1651,
                'reason': 'too long',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 400)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'mutable_content_too_long')
        self.assertEqual(store.state['llm'], 'Frida reste sobre.')
        self.assertEqual(store.upsert_calls, [])
        self.assertEqual(observed_logs[0][1]['new_len'], 1651)
        self.assertNotIn('content', observed_logs[0][1])


if __name__ == '__main__':
    unittest.main()
