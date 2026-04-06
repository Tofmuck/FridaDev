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
        try:
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn('Hermeneutic admin', html)
            self.assertIn('href="admin.css"', html)
            self.assertIn('script src="hermeneutic_admin/render_identity_read_model.js"', html)
            self.assertIn('script src="hermeneutic_admin/render_identity_static_editor.js"', html)
            self.assertIn('script src="hermeneutic_admin/render_identity_mutable_editor.js"', html)
            self.assertIn('script src="hermeneutic_admin/main.js"', html)
        finally:
            response.close()

    def test_identity_candidates_limit_fallback_sort_by_weight_and_mark_legacy_surface(self) -> None:
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
        self.assertTrue(data['legacy_only'])
        self.assertTrue(data['evidence_only'])
        self.assertFalse(data['drives_active_injection'])
        self.assertEqual(data['active_identity_source'], 'identity_mutables')
        self.assertEqual(data['active_prompt_contract'], 'static + mutable narrative')
        self.assertTrue(data['legacy_mutators_disabled'])

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

    def test_identity_force_accept_is_disabled_as_legacy_control(self) -> None:
        observed = {'override_called': False, 'log_called': False}
        original_set_override = self.server.memory_store.set_identity_override
        original_log_event = self.server.admin_logs.log_event

        def fake_set_identity_override(*_args, **_kwargs):
            observed['override_called'] = True
            return True

        def fake_log_event(*_args, **_kwargs):
            observed['log_called'] = True

        self.server.memory_store.set_identity_override = fake_set_identity_override
        self.server.admin_logs.log_event = fake_log_event
        try:
            response = self.client.post(
                '/api/admin/hermeneutics/identity/force-accept',
                json={'identity_id': 'id-1', 'reason': '  because  '},
            )
        finally:
            self.server.memory_store.set_identity_override = original_set_override
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'controle identity legacy desactive',
                'error_code': 'legacy_identity_control_disabled',
                'control': 'force_accept',
                'legacy_only': True,
                'evidence_only': True,
                'drives_active_injection': False,
                'active_identity_source': 'identity_mutables',
                'active_prompt_contract': 'static + mutable narrative',
            },
        )
        self.assertFalse(observed['override_called'])
        self.assertFalse(observed['log_called'])

    def test_identity_force_reject_is_disabled_as_legacy_control(self) -> None:
        observed = {'override_called': False, 'log_called': False}
        original_set_override = self.server.memory_store.set_identity_override
        original_log_event = self.server.admin_logs.log_event

        def fake_set_identity_override(*_args, **_kwargs):
            observed['override_called'] = True
            return True

        def fake_log_event(*_args, **_kwargs):
            observed['log_called'] = True

        self.server.memory_store.set_identity_override = fake_set_identity_override
        self.server.admin_logs.log_event = fake_log_event
        try:
            response = self.client.post(
                '/api/admin/hermeneutics/identity/force-reject',
                json={'identity_id': 'id-1', 'reason': '  because  '},
            )
        finally:
            self.server.memory_store.set_identity_override = original_set_override
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'controle identity legacy desactive',
                'error_code': 'legacy_identity_control_disabled',
                'control': 'force_reject',
                'legacy_only': True,
                'evidence_only': True,
                'drives_active_injection': False,
                'active_identity_source': 'identity_mutables',
                'active_prompt_contract': 'static + mutable narrative',
            },
        )
        self.assertFalse(observed['override_called'])
        self.assertFalse(observed['log_called'])

    def test_identity_relabel_is_disabled_as_legacy_control(self) -> None:
        observed = {'relabel_called': False, 'log_called': False}
        original_relabel_identity = self.server.memory_store.relabel_identity
        original_log_event = self.server.admin_logs.log_event

        def fake_relabel_identity(*_args, **_kwargs):
            observed['relabel_called'] = True
            return True

        def fake_log_event(*_args, **_kwargs):
            observed['log_called'] = True

        self.server.memory_store.relabel_identity = fake_relabel_identity
        self.server.admin_logs.log_event = fake_log_event
        try:
            response = self.client.post(
                '/api/admin/hermeneutics/identity/relabel',
                json={'identity_id': 'id-1', 'stability': 'durable'},
            )
        finally:
            self.server.memory_store.relabel_identity = original_relabel_identity
            self.server.admin_logs.log_event = original_log_event

        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.get_json(),
            {
                'ok': False,
                'error': 'controle identity legacy desactive',
                'error_code': 'legacy_identity_control_disabled',
                'control': 'relabel',
                'legacy_only': True,
                'evidence_only': True,
                'drives_active_injection': False,
                'active_identity_source': 'identity_mutables',
                'active_prompt_contract': 'static + mutable narrative',
            },
        )
        self.assertFalse(observed['relabel_called'])
        self.assertFalse(observed['log_called'])

    def test_identity_relabel_route_stays_guarded_even_when_disabled(self) -> None:
        response = self.client.post(
            '/api/admin/hermeneutics/identity/relabel',
            json={'identity_id': 'id-1'},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.get_json()['error_code'], 'legacy_identity_control_disabled')

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
                {
                    'event': 'identity_mutable_admin_edit',
                    'timestamp': recent_ts,
                    'id': 'keep-mutable-edit',
                    'subject': 'llm',
                    'reason_code': 'set_applied',
                    'new_len': 42,
                },
                {
                    'event': 'identity_static_admin_edit',
                    'timestamp': recent_ts,
                    'id': 'keep-static-edit',
                    'subject': 'user',
                    'reason_code': 'clear_applied',
                    'new_len': 0,
                    'resource_field': 'user_identity_path',
                },
                {
                    'event': 'identity_governance_admin_edit',
                    'timestamp': recent_ts,
                    'id': 'keep-governance-edit',
                    'changed_keys': ['CONTEXT_HINTS_MAX_ITEMS'],
                    'reason_code': 'update_applied',
                },
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
        self.assertEqual(data['count'], 5)
        self.assertEqual(
            [item['id'] for item in data['items']],
            ['keep-override', 'keep-relabel', 'keep-mutable-edit', 'keep-static-edit', 'keep-governance-edit'],
        )
        mutable_item = next(item for item in data['items'] if item['event'] == 'identity_mutable_admin_edit')
        self.assertEqual(mutable_item['subject'], 'llm')
        self.assertEqual(mutable_item['reason_code'], 'set_applied')
        self.assertNotIn('content', mutable_item)
        static_item = next(item for item in data['items'] if item['event'] == 'identity_static_admin_edit')
        self.assertEqual(static_item['subject'], 'user')
        self.assertEqual(static_item['resource_field'], 'user_identity_path')
        self.assertNotIn('content', static_item)
        governance_item = next(item for item in data['items'] if item['event'] == 'identity_governance_admin_edit')
        self.assertEqual(governance_item['changed_keys'], ['CONTEXT_HINTS_MAX_ITEMS'])
        self.assertNotIn('content', governance_item)

    def test_corrections_export_keeps_identity_mutable_admin_edit_visible(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        self.server.admin_logs.read_logs = lambda *, limit: [
            {
                'event': 'identity_mutable_admin_edit',
                'timestamp': recent_ts,
                'id': 'mutable-only',
                'subject': 'user',
                'action': 'clear',
                'reason_code': 'clear_applied',
                'old_len': 31,
                'new_len': 0,
            }
        ]
        try:
            response = self.client.get('/api/admin/hermeneutics/corrections-export?window_days=7&limit=500')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['count'], 1)
        self.assertEqual([item['event'] for item in data['items']], ['identity_mutable_admin_edit'])
        self.assertNotIn('content', data['items'][0])

    def test_corrections_export_keeps_identity_static_admin_edit_visible(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        self.server.admin_logs.read_logs = lambda *, limit: [
            {
                'event': 'identity_static_admin_edit',
                'timestamp': recent_ts,
                'id': 'static-only',
                'subject': 'llm',
                'action': 'set',
                'reason_code': 'set_applied',
                'old_len': 12,
                'new_len': 30,
                'resource_field': 'llm_identity_path',
                'resolution_kind': 'absolute',
            }
        ]
        try:
            response = self.client.get('/api/admin/hermeneutics/corrections-export?window_days=7&limit=500')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['count'], 1)
        self.assertEqual([item['event'] for item in data['items']], ['identity_static_admin_edit'])
        self.assertEqual(data['items'][0]['resource_field'], 'llm_identity_path')
        self.assertNotIn('content', data['items'][0])

    def test_corrections_export_keeps_identity_governance_admin_edit_visible(self) -> None:
        original_read_logs = self.server.admin_logs.read_logs
        recent_ts = (datetime.now(timezone.utc) - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')

        self.server.admin_logs.read_logs = lambda *, limit: [
            {
                'event': 'identity_governance_admin_edit',
                'timestamp': recent_ts,
                'id': 'governance-only',
                'changed_keys': ['CONTEXT_HINTS_MAX_ITEMS'],
                'reason_code': 'update_applied',
            }
        ]
        try:
            response = self.client.get('/api/admin/hermeneutics/corrections-export?window_days=7&limit=500')
        finally:
            self.server.admin_logs.read_logs = original_read_logs

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertEqual(data['count'], 1)
        self.assertEqual([item['event'] for item in data['items']], ['identity_governance_admin_edit'])
        self.assertEqual(data['items'][0]['changed_keys'], ['CONTEXT_HINTS_MAX_ITEMS'])

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
