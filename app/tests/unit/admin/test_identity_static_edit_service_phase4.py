from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_static_edit_service
from identity import static_identity_content
from identity import static_identity_paths


class IdentityStaticEditServicePhase4Tests(unittest.TestCase):
    def test_service_module_stays_below_repo_size_limit(self) -> None:
        service_path = APP_DIR / 'admin' / 'admin_identity_static_edit_service.py'
        with service_path.open('r', encoding='utf-8') as handle:
            line_count = sum(1 for _ in handle)
        self.assertLess(line_count, 500)

    def test_set_valid_updates_active_resource_and_logs_without_raw_content(self) -> None:
        observed_logs: list[tuple[str, dict[str, object]]] = []
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            llm_file = tmp_path / 'app' / 'data' / 'identity' / 'llm.txt'
            llm_file.parent.mkdir(parents=True)
            llm_file.write_text('Frida initiale', encoding='utf-8')
            original_get_resources = static_identity_content.runtime_settings.get_resources_settings

            def fake_get_resources_settings():
                from admin import runtime_settings

                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(llm_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(llm_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                payload, status = admin_identity_static_edit_service.identity_static_edit_response(
                    {
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Frida statique revisee',
                        'reason': 'correction operateur',
                    },
                    static_identity_content_module=static_identity_content,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))
                    ),
                )
                stored_text = llm_file.read_text(encoding='utf-8')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertTrue(payload['changed'])
        self.assertEqual(payload['reason_code'], 'set_applied')
        self.assertEqual(payload['resource_field'], 'llm_identity_path')
        self.assertEqual(payload['resolution_kind'], 'absolute')
        self.assertEqual(stored_text, 'Frida statique revisee')
        event_name, event_payload = observed_logs[0]
        self.assertEqual(event_name, 'identity_static_admin_edit')
        self.assertNotIn('content', event_payload)
        self.assertNotIn('reason', event_payload)

    def test_clear_valid_empties_resource_without_deleting_file(self) -> None:
        observed_logs: list[tuple[str, dict[str, object]]] = []
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            user_file.parent.mkdir(parents=True)
            user_file.write_text('Utilisateur initial', encoding='utf-8')
            original_get_resources = static_identity_content.runtime_settings.get_resources_settings

            def fake_get_resources_settings():
                from admin import runtime_settings

                return runtime_settings.RuntimeSectionView(
                    section='resources',
                    payload=runtime_settings.normalize_stored_payload(
                        'resources',
                        {
                            'llm_identity_path': {'value': str(user_file), 'origin': 'db'},
                            'user_identity_path': {'value': str(user_file), 'origin': 'db'},
                        },
                    ),
                    source='db',
                    source_reason='db_row',
                )

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                payload, status = admin_identity_static_edit_service.identity_static_edit_response(
                    {
                        'subject': 'user',
                        'action': 'clear',
                        'content': '',
                        'reason': 'obsolete',
                    },
                    static_identity_content_module=static_identity_content,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))
                    ),
                )
                exists_after = user_file.exists()
                stored_text = user_file.read_text(encoding='utf-8')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(status, 200)
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['reason_code'], 'clear_applied')
        self.assertFalse(payload['stored_after'])
        self.assertTrue(exists_after)
        self.assertEqual(stored_text, '')
        self.assertEqual(observed_logs[0][1]['reason_code'], 'clear_applied')

    def test_unresolved_resource_fails_closed_without_raw_content(self) -> None:
        observed_logs: list[tuple[str, dict[str, object]]] = []

        class UnresolvedStaticModule:
            @staticmethod
            def resource_field_for_subject(subject: str) -> str:
                return 'llm_identity_path' if subject == 'llm' else 'user_identity_path'

            @staticmethod
            def read_static_identity_snapshot(_subject: str):
                raise RuntimeError('unresolved')

            @staticmethod
            def write_static_identity_content(_subject: str, _content: str):
                raise AssertionError('write must not be called when resource is unresolved')

        payload, status = admin_identity_static_edit_service.identity_static_edit_response(
            {
                'subject': 'llm',
                'action': 'set',
                'content': 'Frida',
                'reason': 'manual correction',
            },
            static_identity_content_module=UnresolvedStaticModule(),
            admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))),
        )

        self.assertEqual(status, 409)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'static_resource_unresolved')
        self.assertEqual(payload['resource_field'], 'llm_identity_path')
        self.assertNotIn('content', observed_logs[0][1])

    def test_existing_resource_outside_allowed_roots_fails_closed_without_raw_content(self) -> None:
        observed_logs: list[tuple[str, dict[str, object]]] = []

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            outside_file = tmp_path / 'outside.txt'
            outside_file.write_text('Hors perimetre', encoding='utf-8')
            original_get_resources = static_identity_content.runtime_settings.get_resources_settings
            try:
                from admin import runtime_settings

                def fake_get_resources_settings():
                    return runtime_settings.RuntimeSectionView(
                        section='resources',
                        payload=runtime_settings.normalize_stored_payload(
                            'resources',
                            {
                                'llm_identity_path': {'value': str(outside_file), 'origin': 'db'},
                                'user_identity_path': {'value': str(outside_file), 'origin': 'db'},
                            },
                        ),
                        source='db',
                        source_reason='db_row',
                    )

                static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
                payload, status = admin_identity_static_edit_service.identity_static_edit_response(
                    {
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Ne doit pas passer',
                        'reason': 'manual correction',
                    },
                    static_identity_content_module=static_identity_content,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))
                    ),
                )
                stored_text = outside_file.read_text(encoding='utf-8')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources

        self.assertEqual(status, 409)
        self.assertFalse(payload['ok'])
        self.assertEqual(payload['validation_error'], 'static_resource_outside_allowed_roots')
        self.assertEqual(stored_text, 'Hors perimetre')
        self.assertNotIn('content', observed_logs[0][1])

    def test_clear_and_set_noop_semantics_follow_raw_file_content_not_trimmed_view(self) -> None:
        observed_logs: list[tuple[str, dict[str, object]]] = []
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            allowed_dir = tmp_path / 'app' / 'data' / 'identity'
            allowed_dir.mkdir(parents=True)
            llm_file = allowed_dir / 'llm.txt'
            user_file = allowed_dir / 'user.txt'
            llm_file.write_text('Frida\n', encoding='utf-8')
            user_file.write_text('\n', encoding='utf-8')
            original_get_resources = static_identity_content.runtime_settings.get_resources_settings

            def fake_get_resources_settings():
                from admin import runtime_settings

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

            static_identity_content.runtime_settings.get_resources_settings = fake_get_resources_settings
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                clear_payload, clear_status = admin_identity_static_edit_service.identity_static_edit_response(
                    {
                        'subject': 'user',
                        'action': 'clear',
                        'content': '',
                        'reason': 'cleanup',
                    },
                    static_identity_content_module=static_identity_content,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))
                    ),
                )
                set_payload, set_status = admin_identity_static_edit_service.identity_static_edit_response(
                    {
                        'subject': 'llm',
                        'action': 'set',
                        'content': 'Frida',
                        'reason': 'normalize',
                    },
                    static_identity_content_module=static_identity_content,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: observed_logs.append((event, kwargs))
                    ),
                )
                user_text = user_file.read_text(encoding='utf-8')
                llm_text = llm_file.read_text(encoding='utf-8')
            finally:
                static_identity_content.runtime_settings.get_resources_settings = original_get_resources
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(clear_status, 200)
        self.assertEqual(clear_payload['reason_code'], 'clear_applied')
        self.assertTrue(clear_payload['changed'])
        self.assertEqual(clear_payload['old_len'], 1)
        self.assertEqual(user_text, '')
        self.assertEqual(set_status, 200)
        self.assertEqual(set_payload['reason_code'], 'set_applied')
        self.assertTrue(set_payload['changed'])
        self.assertEqual(set_payload['old_len'], 6)
        self.assertEqual(set_payload['new_len'], 5)
        self.assertEqual(llm_text, 'Frida')
        self.assertTrue(all('content' not in payload for _, payload in observed_logs))


if __name__ == '__main__':
    unittest.main()
