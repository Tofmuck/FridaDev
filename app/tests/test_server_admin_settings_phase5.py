from __future__ import annotations

import logging
import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from identity import static_identity_paths
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminSettingsPhase5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

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

    def test_post_admin_settings_resources_validate_rejects_existing_file_outside_allowed_roots(self) -> None:
        original_app_root = static_identity_paths.APP_ROOT
        original_repo_root = static_identity_paths.REPO_ROOT
        original_host_state_root = static_identity_paths.HOST_STATE_ROOT

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            allowed_user_file = tmp_path / 'app' / 'data' / 'identity' / 'user.txt'
            outside_file = tmp_path / 'outside.txt'
            allowed_user_file.parent.mkdir(parents=True)
            allowed_user_file.write_text('user identity allowed', encoding='utf-8')
            outside_file.write_text('outside identity path', encoding='utf-8')
            static_identity_paths.APP_ROOT = tmp_path / 'app'
            static_identity_paths.REPO_ROOT = tmp_path
            static_identity_paths.HOST_STATE_ROOT = tmp_path / 'state'
            try:
                response = self.client.post(
                    '/api/admin/settings/resources/validate',
                    json={
                        'payload': {
                            'llm_identity_path': {'value': str(outside_file)},
                            'user_identity_path': {'value': str(allowed_user_file)},
                        },
                    },
                )
            finally:
                static_identity_paths.APP_ROOT = original_app_root
                static_identity_paths.REPO_ROOT = original_repo_root
                static_identity_paths.HOST_STATE_ROOT = original_host_state_root

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertFalse(data['valid'])
        checks = {check['name']: check for check in data['checks']}
        self.assertFalse(checks['llm_identity_path']['ok'])
        self.assertTrue(checks['user_identity_path']['ok'])
        self.assertIn('resolution=absolute_outside_allowed_roots', checks['llm_identity_path']['detail'])
        self.assertIn('within_allowed_roots=False', checks['llm_identity_path']['detail'])

    def test_admin_logs_route_keeps_legacy_contract(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        observed = {'limit': None}

        def fake_read_logs(limit=200):
            observed['limit'] = limit
            return [{'event': 'legacy-log', 'level': 'INFO'}]

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/logs?limit=5')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['limit'], 5)
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'ok': True,
                'logs': [{'event': 'legacy-log', 'level': 'INFO'}],
            },
        )

    def test_admin_restart_route_keeps_legacy_contract(self) -> None:
        original_restart = self.server.admin_actions.restart_runtime_async
        observed = {'target': None}

        def fake_restart_runtime_async(target):
            observed['target'] = target

        self.server.admin_actions.restart_runtime_async = fake_restart_runtime_async
        try:
            response = self.client.post('/api/admin/restart')
        finally:
            self.server.admin_actions.restart_runtime_async = original_restart

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['target'], 'FridaDev')
        data = response.get_json()
        self.assertEqual(
            data,
            {
                'ok': True,
                'target': 'FridaDev',
                'mode': 'container_self_exit',
            },
        )

    def test_hermeneutics_and_settings_routes_stay_separated(self) -> None:
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}

        settings_routes = {
            route for route in routes
            if route.startswith('/api/admin/settings')
        }
        hermeneutics_routes = {
            route for route in routes
            if route.startswith('/api/admin/hermeneutics')
        }
        identity_routes = {
            route for route in routes
            if route.startswith('/api/admin/identity')
        }

        self.assertEqual(
            hermeneutics_routes,
            {
                '/api/admin/hermeneutics/identity-candidates',
                '/api/admin/hermeneutics/arbiter-decisions',
                '/api/admin/hermeneutics/identity/force-accept',
                '/api/admin/hermeneutics/identity/force-reject',
                '/api/admin/hermeneutics/identity/relabel',
                '/api/admin/hermeneutics/dashboard',
                '/api/admin/hermeneutics/corrections-export',
            },
        )
        self.assertEqual(
            identity_routes,
            {
                '/api/admin/identity/read-model',
                '/api/admin/identity/runtime-representations',
                '/api/admin/identity/mutable',
                '/api/admin/identity/static',
                '/api/admin/identity/governance',
            },
        )
        self.assertTrue(settings_routes)
        self.assertTrue(hermeneutics_routes)
        self.assertTrue(identity_routes)
        self.assertTrue(settings_routes.isdisjoint(hermeneutics_routes))
        self.assertTrue(settings_routes.isdisjoint(identity_routes))
        self.assertTrue(hermeneutics_routes.isdisjoint(identity_routes))
        self.assertFalse(any('hermeneutics' in route for route in settings_routes))
        self.assertFalse(any('/settings' in route for route in hermeneutics_routes))

    def test_admin_resources_ui_keeps_paths_as_resource_references(self) -> None:
        source = (APP_DIR / 'web' / 'admin.js').read_text(encoding='utf-8')
        self.assertIn('LLM static resource path', source)
        self.assertIn('User static resource path', source)
        self.assertIn("Reference de ressource du statique actif cote modele.", source)
        self.assertIn("Reference de ressource du statique actif cote utilisateur.", source)
        self.assertIn("Le contenu s'edite depuis Hermeneutic admin.", source)

    def test_all_admin_settings_validate_routes_are_registered(self) -> None:
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn('/api/admin/settings/main-model/validate', routes)
        self.assertIn('/api/admin/settings/arbiter-model/validate', routes)
        self.assertIn('/api/admin/settings/summary-model/validate', routes)
        self.assertIn('/api/admin/settings/stimmung-agent-model/validate', routes)
        self.assertIn('/api/admin/settings/validation-agent-model/validate', routes)
        self.assertIn('/api/admin/settings/embedding/validate', routes)
        self.assertIn('/api/admin/settings/database/validate', routes)
        self.assertIn('/api/admin/settings/services/validate', routes)
        self.assertIn('/api/admin/settings/resources/validate', routes)

    def test_post_admin_settings_validate_uses_runtime_validation_result(self) -> None:
        observed = {'section': None, 'payload': None}
        original_validate = self.server.runtime_settings.validate_runtime_section

        def fake_validate_runtime_section(section, patch_payload=None, *, fetcher=None):
            observed['section'] = section
            observed['payload'] = patch_payload
            return {
                'section': section,
                'valid': True,
                'source': 'candidate',
                'source_reason': 'validate_payload',
                'checks': [
                    {'name': 'endpoint', 'ok': True, 'detail': 'endpoint=https://embed.next.example'},
                    {'name': 'dimensions', 'ok': True, 'detail': 'dimensions=384'},
                ],
            }

        self.server.runtime_settings.validate_runtime_section = fake_validate_runtime_section
        try:
            response = self.client.post(
                '/api/admin/settings/embedding/validate',
                json={
                    'payload': {
                        'endpoint': {'value': 'https://embed.next.example'},
                        'dimensions': {'value': 384},
                    },
                },
            )
        finally:
            self.server.runtime_settings.validate_runtime_section = original_validate

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['section'], 'embedding')
        self.assertEqual(
            observed['payload'],
            {
                'endpoint': {'value': 'https://embed.next.example'},
                'dimensions': {'value': 384},
            },
        )
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertTrue(data['valid'])
        self.assertEqual(data['section'], 'embedding')
        self.assertEqual(data['source'], 'candidate')
        self.assertEqual(data['source_reason'], 'validate_payload')
        self.assertEqual(len(data['checks']), 2)

    def test_post_admin_settings_validate_rejects_invalid_payload(self) -> None:
        response = self.client.post(
            '/api/admin/settings/main-model/validate',
            json={'payload': {'api_key': {'value': 'sk-secret'}}},
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertIn('ambiguous secret patch payload', data['error'])

    def test_post_admin_settings_validate_rejects_non_mapping_payload(self) -> None:
        response = self.client.post(
            '/api/admin/settings/main-model/validate',
            data='[]',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 400)
        data = response.get_json()
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], 'validation payload must be a mapping')

    def test_post_admin_settings_validate_encrypt_error_does_not_echo_secret_value(self) -> None:
        class CaptureHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.messages = []

            def emit(self, record):
                self.messages.append(record.getMessage())

        secret_value = 'embed-secret-should-not-leak-from-validate-error'
        original_encrypt = self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value
        capture = CaptureHandler()
        target_loggers = (
            logging.getLogger(),
            logging.getLogger('frida.server'),
            logging.getLogger('frida.adminlog'),
        )
        for logger in target_loggers:
            logger.addHandler(capture)

        def fake_encrypt_runtime_secret_value(value: str) -> str:
            raise self.server.runtime_settings.runtime_secrets.RuntimeSettingsCryptoEngineError(
                f'validate crypto failure on {value}'
            )

        self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = fake_encrypt_runtime_secret_value
        try:
            response = self.client.post(
                '/api/admin/settings/embedding/validate',
                json={'payload': {'token': {'replace_value': secret_value}}},
            )
        finally:
            self.server.runtime_settings.runtime_secrets.encrypt_runtime_secret_value = original_encrypt
            for logger in target_loggers:
                logger.removeHandler(capture)

        self.assertEqual(response.status_code, 400)
        body = response.get_data(as_text=True)
        self.assertIn('failed to encrypt secret for embedding.token', body)
        self.assertNotIn(secret_value, body)
        if self.server.admin_logs.LOG_PATH.exists():
            admin_log_text = self.server.admin_logs.LOG_PATH.read_text(encoding='utf-8')
            self.assertNotIn(secret_value, admin_log_text)
        self.assertFalse(
            any(secret_value in message for message in capture.messages),
            msg=f'secret leaked to log records: {capture.messages!r}',
        )


if __name__ == '__main__':
    unittest.main()
