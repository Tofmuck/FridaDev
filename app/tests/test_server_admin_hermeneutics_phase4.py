from __future__ import annotations

import importlib
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class ServerAdminHermeneuticsPhase4Tests(unittest.TestCase):
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

    def test_hermeneutic_admin_route_serves_dedicated_static_page(self) -> None:
        response = self.client.get('/hermeneutic-admin')

        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('Hermeneutic admin', html)
        self.assertIn('href="admin.css"', html)
        self.assertIn('script src="hermeneutic_admin/main.js"', html)

    def test_identity_candidates_limit_fallback_and_sort_by_weight(self) -> None:
        observed = {'calls': []}
        original_get_identities = self.server.memory_store.get_identities

        def fake_get_identities(subject: str, top_n: int, status=None):
            observed['calls'].append((subject, top_n, status))
            if subject == 'user':
                return [
                    {'identity_id': 'u-low', 'weight': 0.2},
                    {'identity_id': 'u-high', 'weight': 0.9},
                ]
            return [
                {'identity_id': 'l-mid', 'weight': 0.5},
                {'identity_id': 'l-zero', 'weight': 0.0},
            ]

        self.server.memory_store.get_identities = fake_get_identities
        try:
            response = self.client.get('/api/admin/hermeneutics/identity-candidates?limit=oops&subject=all')
        finally:
            self.server.memory_store.get_identities = original_get_identities

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(
            observed['calls'],
            [('user', 200, None), ('llm', 200, None)],
        )
        self.assertEqual(
            [item['identity_id'] for item in data['items']],
            ['u-high', 'l-mid', 'u-low', 'l-zero'],
        )
        self.assertEqual(data['count'], 4)

    def test_identity_candidates_rejects_invalid_subject(self) -> None:
        response = self.client.get('/api/admin/hermeneutics/identity-candidates?subject=robot')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'subject invalide'},
        )

    def test_identity_candidates_rejects_invalid_status(self) -> None:
        response = self.client.get('/api/admin/hermeneutics/identity-candidates?status=pending')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'status invalide'},
        )

    def test_arbiter_decisions_trims_conversation_id(self) -> None:
        observed = {'limit': None, 'conversation_id': None}
        original_get_decisions = self.server.memory_store.get_arbiter_decisions

        def fake_get_arbiter_decisions(limit: int, conversation_id=None):
            observed['limit'] = limit
            observed['conversation_id'] = conversation_id
            return [{'decision_id': 'd1'}]

        self.server.memory_store.get_arbiter_decisions = fake_get_arbiter_decisions
        try:
            response = self.client.get(
                '/api/admin/hermeneutics/arbiter-decisions?limit=5&conversation_id=%20conv-42%20'
            )
        finally:
            self.server.memory_store.get_arbiter_decisions = original_get_decisions

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(observed['limit'], 5)
        self.assertEqual(observed['conversation_id'], 'conv-42')
        self.assertEqual(data['count'], 1)

    def test_identity_force_reject_requires_identity_id(self) -> None:
        response = self.client.post('/api/admin/hermeneutics/identity/force-reject', json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'identity_id manquant'},
        )

    def test_identity_force_reject_returns_404_when_identity_not_found(self) -> None:
        observed = {'args': None, 'log_called': False}
        original_set_override = self.server.memory_store.set_identity_override
        original_log_event = self.server.admin_logs.log_event

        def fake_set_identity_override(identity_id: str, action: str, *, reason: str, actor: str):
            observed['args'] = (identity_id, action, reason, actor)
            return False

        def fake_log_event(*_args, **_kwargs):
            observed['log_called'] = True

        self.server.memory_store.set_identity_override = fake_set_identity_override
        self.server.admin_logs.log_event = fake_log_event
        try:
            response = self.client.post(
                '/api/admin/hermeneutics/identity/force-reject',
                json={'identity_id': 'id-missing', 'reason': '  because  '},
            )
        finally:
            self.server.memory_store.set_identity_override = original_set_override
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'identity introuvable'},
        )
        self.assertEqual(
            observed['args'],
            ('id-missing', 'force_reject', 'because', 'admin'),
        )
        self.assertFalse(observed['log_called'])

    def test_identity_relabel_rejects_when_no_field_is_provided(self) -> None:
        response = self.client.post(
            '/api/admin/hermeneutics/identity/relabel',
            json={'identity_id': 'id-1'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'aucun champ a relabel'},
        )

    def test_identity_relabel_rejects_invalid_stability(self) -> None:
        response = self.client.post(
            '/api/admin/hermeneutics/identity/relabel',
            json={'identity_id': 'id-1', 'stability': 'permanent'},
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.get_json(),
            {'ok': False, 'error': 'stability invalide'},
        )

    def test_dashboard_computes_rates_and_alerts_with_contract_fallbacks(self) -> None:
        observed = {'window_days': None, 'log_limit': None}
        original_get_kpis = self.server.memory_store.get_hermeneutic_kpis
        original_get_runtime_metrics = self.server.arbiter.get_runtime_metrics
        original_read_logs = self.server.admin_logs.read_logs

        def fake_get_hermeneutic_kpis(*, window_days: int):
            observed['window_days'] = window_days
            return {
                'identity_accept_count': 4,
                'identity_defer_count': 2,
                'identity_reject_count': 1,
                'identity_override_count': 3,
                'arbiter_fallback_count': 5,
                'fallback_rate': 0.2,
            }

        def fake_get_runtime_metrics():
            return {
                'arbiter_parse_error_count': 2,
                'identity_parse_error_count': 1,
                'arbiter_call_count': 20,
                'identity_extractor_call_count': 10,
                'arbiter_fallback_count': 1,
            }

        def fake_read_logs(*, limit: int):
            observed['log_limit'] = limit
            return [
                {'event': 'stage_latency', 'stage': 'retrieve', 'duration_ms': 10},
                {'event': 'stage_latency', 'stage': 'retrieve', 'duration_ms': 30},
                {'event': 'stage_latency', 'stage': 'arbiter', 'duration_ms': 50},
                {'event': 'stage_latency', 'stage': 'identity_extractor', 'duration_ms': 20},
                {'event': 'other_event', 'stage': 'retrieve', 'duration_ms': 999},
            ]

        self.server.memory_store.get_hermeneutic_kpis = fake_get_hermeneutic_kpis
        self.server.arbiter.get_runtime_metrics = fake_get_runtime_metrics
        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/hermeneutics/dashboard?window_days=bad&log_limit=oops')
        finally:
            self.server.memory_store.get_hermeneutic_kpis = original_get_kpis
            self.server.arbiter.get_runtime_metrics = original_get_runtime_metrics
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(observed['window_days'], 7)
        self.assertEqual(observed['log_limit'], 5000)
        self.assertEqual(data['window_days'], 7)
        self.assertEqual(data['counters']['parse_error_count'], 3)
        self.assertEqual(data['rates']['parse_error_rate'], 0.1)
        self.assertEqual(data['rates']['runtime_fallback_rate'], 0.05)
        self.assertEqual(data['rates']['fallback_rate'], 0.2)
        self.assertIn('parse_error_rate_gt_5pct', data['alerts'])
        self.assertIn('fallback_rate_gt_10pct', data['alerts'])
        self.assertEqual(data['latency_ms']['retrieve']['count'], 2)
        self.assertEqual(data['latency_ms']['retrieve']['p50_ms'], 20.0)
        self.assertEqual(data['latency_ms']['retrieve']['p95_ms'], 29.0)

    def test_corrections_export_filters_events_invalid_timestamps_and_cutoff(self) -> None:
        observed = {'limit': None}
        original_read_logs = self.server.admin_logs.read_logs
        now = datetime.now(timezone.utc)
        recent_ts = (now - timedelta(days=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
        old_ts = (now - timedelta(days=12)).strftime('%Y-%m-%dT%H:%M:%SZ')

        def fake_read_logs(*, limit: int):
            observed['limit'] = limit
            return [
                {'event': 'identity_override', 'timestamp': recent_ts, 'id': 'keep-override'},
                {'event': 'identity_relabel', 'timestamp': recent_ts, 'id': 'keep-relabel'},
                {'event': 'identity_override', 'timestamp': old_ts, 'id': 'drop-old'},
                {'event': 'identity_override', 'timestamp': 'not-a-date', 'id': 'drop-invalid-ts'},
                {'event': 'other_event', 'timestamp': recent_ts, 'id': 'drop-event'},
            ]

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/hermeneutics/corrections-export?window_days=7&limit=500')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(observed['limit'], 500)
        self.assertEqual(data['window_days'], 7)
        self.assertEqual(data['count'], 2)
        self.assertEqual(
            [item['id'] for item in data['items']],
            ['keep-override', 'keep-relabel'],
        )

    def test_all_admin_hermeneutics_routes_are_protected_by_existing_admin_guard(self) -> None:
        original_token = self.server.config.FRIDA_ADMIN_TOKEN
        original_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_TOKEN = 'phase4-herm-token'
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        try:
            guarded_rules = []
            for rule in self.server.app.url_map.iter_rules():
                if not rule.rule.startswith('/api/admin/hermeneutics'):
                    continue
                methods = sorted(method for method in rule.methods if method in {'GET', 'POST'})
                for method in methods:
                    guarded_rules.append((method, rule.rule))

            self.assertTrue(guarded_rules)

            for method, path in guarded_rules:
                kwargs = {}
                if method == 'POST':
                    kwargs['json'] = {}
                response = self.client.open(path, method=method, **kwargs)
                self.assertEqual(
                    response.status_code,
                    401,
                    msg=f'expected admin guard on {method} {path}, got {response.status_code}',
                )
        finally:
            self.server.config.FRIDA_ADMIN_TOKEN = original_token
            self.server.config.FRIDA_ADMIN_LAN_ONLY = original_lan_only


if __name__ == '__main__':
    unittest.main()
