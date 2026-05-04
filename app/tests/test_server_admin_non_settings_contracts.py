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

if __name__ == '__main__':
    unittest.main()
