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


class _MutableStoreWithStagingGuard(_MutableStore):
    def append_identity_staging_pair(self, *_args: Any, **_kwargs: Any) -> None:
        raise AssertionError('admin mutable edit must not write into identity staging')

    def mark_identity_staging_status(self, *_args: Any, **_kwargs: Any) -> None:
        raise AssertionError('admin mutable edit must not touch identity staging metadata')

    def clear_identity_staging_buffer(self, *_args: Any, **_kwargs: Any) -> None:
        raise AssertionError('admin mutable edit must not clear identity staging')


class IdentityMutableEditServicePhase3Tests(unittest.TestCase):
    def test_service_module_stays_below_repo_size_limit(self) -> None:
        service_path = APP_DIR / 'admin' / 'admin_identity_mutable_edit_service.py'
        with service_path.open('r', encoding='utf-8') as handle:
            line_count = sum(1 for _ in handle)
        self.assertLess(line_count, 500)

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

    def test_set_valid_accepts_narrative_technical_interest(self) -> None:
        store = _MutableStore({'user': 'Utilisateur prefere la clarte.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'user',
                'action': 'set',
                'content': 'Tof aime discuter du runtime, des pipelines et des architectures complexes.',
                'reason': 'interet durable',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['reason_code'], 'set_applied')
        self.assertIn('runtime', store.state['user'])
        self.assertEqual(observed_logs[0][1]['reason_code'], 'set_applied')

    def test_set_valid_keeps_admin_edit_on_canonical_mutable_not_staging(self) -> None:
        store = _MutableStoreWithStagingGuard({'llm': 'Frida reste sobre.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'llm',
                'action': 'set',
                'content': 'Frida reste sobre, concise et stable.',
                'reason': 'correction operateur',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(store.state['llm'], 'Frida reste sobre, concise et stable.')
        self.assertEqual(store.upsert_calls[0][2], 'admin_identity_mutable_edit')
        self.assertEqual(observed_logs[0][1]['reason_code'], 'set_applied')

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
                'content': 'x' * 3301,
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
        self.assertEqual(observed_logs[0][1]['new_len'], 3301)
        self.assertNotIn('content', observed_logs[0][1])

    def test_rejects_prompt_like_content_in_english_without_write(self) -> None:
        store = _MutableStore({'llm': 'Frida reste sobre.'})
        observed_logs: list[tuple[str, dict[str, Any]]] = []
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs)))

        payload, status = admin_identity_mutable_edit_service.identity_mutable_edit_response(
            {
                'subject': 'llm',
                'action': 'set',
                'content': 'You must verify sources and cite each important point.',
                'reason': 'probe only',
            },
            memory_store_module=store,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(status, 400)
        self.assertFalse(payload['ok'])
        self.assertEqual(
            payload['validation_error'],
            'mutable_content_prompt_like_operator_instruction',
        )
        self.assertEqual(store.state['llm'], 'Frida reste sobre.')
        self.assertEqual(store.upsert_calls, [])
        self.assertEqual(
            observed_logs[0][1]['validation_error'],
            'mutable_content_prompt_like_operator_instruction',
        )
        self.assertNotIn('content', observed_logs[0][1])


if __name__ == '__main__':
    unittest.main()
