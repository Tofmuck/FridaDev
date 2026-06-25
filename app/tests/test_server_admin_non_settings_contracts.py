from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_logs, runtime_settings
from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminNonSettingsContractsTests(unittest.TestCase):
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

    def test_admin_logs_route_keeps_legacy_contract(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        observed = {'limit': None, 'fail_closed': None}

        def fake_read_logs(limit=200, *, fail_closed=False):
            observed['limit'] = limit
            observed['fail_closed'] = fail_closed
            return [{'event': 'legacy-log', 'level': 'INFO', 'reason_code': 'admin_check'}]

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/logs?limit=5')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        self.assertEqual(observed['limit'], 5)
        self.assertTrue(observed['fail_closed'])
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(len(data['logs']), 1)
        self.assertEqual(data['logs'][0]['event'], 'legacy-log')
        self.assertEqual(data['logs'][0]['level'], 'INFO')
        self.assertEqual(data['logs'][0]['payload']['reason_code'], 'admin_check')
        self.assertFalse(data['redaction']['raw_event_payloads_included'])

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

    def test_admin_guard_allows_loopback_proof_calls(self) -> None:
        response = self.client.get(
            '/api/admin/logs?limit=1',
            environ_overrides={'REMOTE_ADDR': '127.0.0.1'},
        )

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])

    def test_admin_guard_allows_trusted_proxy_remote_user(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.18.0.2'}
        try:
            response = self.client.get(
                '/api/admin/logs?limit=1',
                headers={'Remote-User': 'operator'},
                environ_overrides={'REMOTE_ADDR': '172.18.0.2'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])

    def test_admin_guard_rejects_direct_non_proxy_calls(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.18.0.2'}
        try:
            response = self.client.get(
                '/api/admin/logs?limit=1',
                environ_overrides={'REMOTE_ADDR': '172.18.0.44'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'admin access denied'})

    def test_admin_guard_rejects_lateral_forged_remote_user(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        self.server._trusted_admin_proxy_ips = lambda: {'172.18.0.2'}
        try:
            response = self.client.get(
                '/api/admin/logs?limit=1',
                headers={'Remote-User': 'operator'},
                environ_overrides={'REMOTE_ADDR': '172.18.0.44'},
            )
        finally:
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'admin access denied'})

    def test_admin_guard_rejects_token_without_trusted_proxy(self) -> None:
        original_trusted_proxy_ips = self.server._trusted_admin_proxy_ips
        original_admin_token = self.server.config.FRIDA_ADMIN_TOKEN
        self.server._trusted_admin_proxy_ips = lambda: {'172.18.0.2'}
        self.server.config.FRIDA_ADMIN_TOKEN = 'legacy-test-marker'
        try:
            response = self.client.get(
                '/api/admin/logs?limit=1',
                headers={'X-Admin-Token': 'legacy-test-marker'},
                environ_overrides={'REMOTE_ADDR': '172.18.0.44'},
            )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_admin_token
            self.server._trusted_admin_proxy_ips = original_trusted_proxy_ips

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'admin access denied'})

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
        source = (APP_DIR / 'web' / 'admin_settings_catalog.js').read_text(encoding='utf-8')
        self.assertIn('LLM static resource path', source)
        self.assertIn('User static resource path', source)
        self.assertIn("Reference de ressource du statique actif cote modele.", source)
        self.assertIn("Reference de ressource du statique actif cote utilisateur.", source)
        self.assertIn("Le contenu s'edite depuis Hermeneutic admin.", source)

    def test_admin_guard_does_not_reintroduce_legacy_token_knobs(self) -> None:
        server_source = (APP_DIR / 'server.py').read_text(encoding='utf-8')
        guard_source = server_source.split('_TRUSTED_ADMIN_PROXY_HOSTS', 1)[1]
        guard_source = guard_source.split('def _assistant_message_count', 1)[0]

        for marker in (
            'FRIDA_ADMIN_TOKEN',
            'FRIDA_ADMIN_LAN_ONLY',
            'FRIDA_ADMIN_ALLOWED_CIDRS',
            'X-Admin-Token',
        ):
            self.assertNotIn(marker, guard_source)

        self.assertIn("_TRUSTED_ADMIN_IDENTITY_HEADERS = ('Remote-User',)", guard_source)
        self.assertIn('if _is_loopback_ip(client_ip):', guard_source)
        self.assertIn('trusted_proxy_ips = _trusted_admin_proxy_ips()', guard_source)
        self.assertIn("'missing_proxy_identity'", guard_source)

    def test_env_examples_do_not_advertise_legacy_admin_knobs(self) -> None:
        env_example = (APP_DIR / '.env.example').read_text(encoding='utf-8')
        config_example = (APP_DIR / 'config.example.py').read_text(encoding='utf-8')

        for marker in (
            'FRIDA_ADMIN_TOKEN=',
            'FRIDA_ADMIN_LAN_ONLY=',
            'FRIDA_ADMIN_ALLOWED_CIDRS=',
        ):
            self.assertNotIn(marker, env_example)
            self.assertNotIn(marker, config_example)

        self.assertIn('No application-level human admin token', config_example)
        self.assertIn('Remote-User', config_example)

if __name__ == '__main__':
    unittest.main()
