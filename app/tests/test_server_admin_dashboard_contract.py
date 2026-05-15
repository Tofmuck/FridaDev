from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminDashboardContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_dashboard_static_page_route_returns_skeleton(self) -> None:
        response = self.client.get('/dashboard')

        self.assertEqual(response.status_code, 200)
        body = response.get_data(as_text=True)
        self.assertIn('Dashboard long terme', body)
        self.assertIn('dashboard/main.js', body)
        self.assertNotIn('/api/admin/dashboard/overview', body)

    def _assert_content_free(self, payload: dict) -> None:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        forbidden = (
            'RAW PROMPT MUST NOT LEAK',
            'RAW MESSAGE MUST NOT LEAK',
            'RAW MEMORY MUST NOT LEAK',
            'RAW QUERY MUST NOT LEAK',
            'RAW WEB CONTEXT MUST NOT LEAK',
            'secret-token',
            'postgres://',
        )
        for needle in forbidden:
            self.assertNotIn(needle, encoded)

    def test_dashboard_overview_route_returns_windowed_payload(self) -> None:
        observed = {'args': None}
        original = self.server.dashboard_read_model.read_dashboard_overview

        def fake_read_dashboard_overview(args, **_kwargs):
            observed['args'] = args
            return {
                'kind': 'dashboard_overview',
                'window': {'key': args.get('window'), 'start': '2026-05-14T00:00:00+00:00', 'end': '2026-05-15T00:00:00+00:00'},
                'pulse': {'label_fr': 'Pouls global', 'turns_observed': 2},
                'module_catalog': {'module_keys': ['pipeline', 'memory'], 'redaction': {'raw_content_stored': False}},
                'module_totals': {'pipeline': {'turn_count': 2, 'metrics': {'classification_counts': {'complete': 2}}}},
                'metric_buckets': [],
                'source': {'limits': {'event_limit_dependency': False, 'source_events_truncated': False}},
                'redaction': {'raw_content_included': False},
            }

        self.server.dashboard_read_model.read_dashboard_overview = fake_read_dashboard_overview
        try:
            response = self.client.get('/api/admin/dashboard/overview?window=24h')
        finally:
            self.server.dashboard_read_model.read_dashboard_overview = original

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['kind'], 'dashboard_overview')
        self.assertEqual(data['pulse']['turns_observed'], 2)
        self.assertFalse(data['source']['limits']['event_limit_dependency'])
        self.assertEqual(observed['args'].get('window'), '24h')
        self._assert_content_free(data)

    def test_dashboard_conversations_route_returns_comparison_payload(self) -> None:
        observed = {'args': None}
        original = self.server.dashboard_read_model.read_dashboard_conversations

        def fake_read_dashboard_conversations(args, **_kwargs):
            observed['args'] = args
            return {
                'kind': 'dashboard_conversations',
                'window': {'key': args.get('window')},
                'items': [{'conversation_id': 'conv-1', 'display_label': 'Conversation du 2026-05-15 12:00 UTC', 'turns_count': 3}],
                'count': 1,
                'total': 1,
                'limit': int(args.get('limit')),
                'offset': int(args.get('offset')),
                'next_offset': None,
                'source': {'limits': {'event_limit_dependency': False}},
                'redaction': {'raw_content_included': False},
            }

        self.server.dashboard_read_model.read_dashboard_conversations = fake_read_dashboard_conversations
        try:
            response = self.client.get('/api/admin/dashboard/conversations?window=7d&limit=10&offset=0')
        finally:
            self.server.dashboard_read_model.read_dashboard_conversations = original

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['items'][0]['display_label'], 'Conversation du 2026-05-15 12:00 UTC')
        self.assertEqual(observed['args'].get('window'), '7d')
        self.assertEqual(observed['args'].get('limit'), '10')
        self._assert_content_free(data)

    def test_dashboard_conversation_turns_route_returns_turn_payload(self) -> None:
        observed = {'conversation_id': None, 'args': None}
        original = self.server.dashboard_read_model.read_dashboard_conversation_turns

        def fake_read_dashboard_conversation_turns(conversation_id, args, **_kwargs):
            observed['conversation_id'] = conversation_id
            observed['args'] = args
            return {
                'kind': 'dashboard_conversation_turns',
                'conversation_id': conversation_id,
                'window': {'key': args.get('window')},
                'items': [{'conversation_id': conversation_id, 'turn_id': 'turn-1', 'classification': 'complete'}],
                'count': 1,
                'total': 1,
                'limit': 50,
                'offset': 0,
                'next_offset': None,
                'source': {'limits': {'event_limit_dependency': False}},
                'redaction': {'raw_content_included': False},
            }

        self.server.dashboard_read_model.read_dashboard_conversation_turns = fake_read_dashboard_conversation_turns
        try:
            response = self.client.get('/api/admin/dashboard/conversations/conv-1/turns?window=30d')
        finally:
            self.server.dashboard_read_model.read_dashboard_conversation_turns = original

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['items'][0]['turn_id'], 'turn-1')
        self.assertEqual(observed['conversation_id'], 'conv-1')
        self.assertEqual(observed['args'].get('window'), '30d')
        self._assert_content_free(data)

    def test_dashboard_turn_inspection_route_returns_translated_payload(self) -> None:
        observed = {'turn_id': None, 'args': None}
        original = self.server.dashboard_read_model.read_dashboard_turn_inspection

        def fake_read_dashboard_turn_inspection(turn_id, args, **_kwargs):
            observed['turn_id'] = turn_id
            observed['args'] = args
            return {
                'kind': 'dashboard_turn_inspection',
                'conversation_id': args.get('conversation_id'),
                'turn_id': turn_id,
                'window': {'key': args.get('window')},
                'item': {'conversation_id': args.get('conversation_id'), 'turn_id': turn_id, 'classification': 'complete'},
                'story': {
                    'kind': 'dashboard_turn_story',
                    'title_fr': 'Inspection traduite du tour',
                    'summary_fr': 'Tour reussi avec une lecture traduite.',
                    'sections': [
                        {'key': 'received', 'label_fr': 'Ce que Frida a recu', 'items': ['Lecture traduite sans contenu brut.']},
                    ],
                    'proof_level': 'translated_compact_inspection',
                    'content_status_fr': 'Contenu complet non charge; ouverture volontaire reservee au lot suivant.',
                    'redaction': {'raw_content_included': False},
                },
                'modules': [{'module_key': 'memory', 'label_fr': 'Memoire utilisee', 'summary_fr': 'La memoire a trouve 2 elements.', 'raw_content_available': False}],
                'source': {'limits': {'event_limit_dependency': False}},
                'redaction': {'raw_content_included': False},
            }

        self.server.dashboard_read_model.read_dashboard_turn_inspection = fake_read_dashboard_turn_inspection
        try:
            response = self.client.get('/api/admin/dashboard/turns/turn-1/inspection?conversation_id=conv-1&window=24h')
        finally:
            self.server.dashboard_read_model.read_dashboard_turn_inspection = original

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['story']['kind'], 'dashboard_turn_story')
        self.assertIn('Ce que Frida a recu', data['story']['sections'][0]['label_fr'])
        self.assertEqual(data['modules'][0]['label_fr'], 'Memoire utilisee')
        self.assertFalse(data['modules'][0]['raw_content_available'])
        self.assertEqual(observed['turn_id'], 'turn-1')
        self.assertEqual(observed['args'].get('conversation_id'), 'conv-1')
        self._assert_content_free(data)

    def test_dashboard_turn_content_route_is_explicit_and_audited(self) -> None:
        observed = {'turn_id': None, 'args': None, 'audit_fn': None}
        original = self.server.dashboard_read_model.read_dashboard_turn_content

        def fake_read_dashboard_turn_content(turn_id, args, **kwargs):
            observed['turn_id'] = turn_id
            observed['args'] = args
            observed['audit_fn'] = kwargs.get('audit_fn')
            return {
                'kind': 'dashboard_turn_content_gate',
                'conversation_id': args.get('conversation_id'),
                'turn_id': turn_id,
                'window': {'key': args.get('window')},
                'availability': {
                    'status': 'fingerprint_only',
                    'status_fr': 'empreinte seule disponible',
                    'loaded_after_explicit_action': True,
                    'preloaded': False,
                    'status_counts': {'fingerprint_only': 1},
                },
                'items': [
                    {
                        'key': 'main_model_payload',
                        'label_fr': 'Payload du modele principal',
                        'status': 'fingerprint_only',
                        'status_fr': 'empreinte seule disponible',
                        'content_text': None,
                        'explanation_fr': 'Seules les empreintes existent.',
                    }
                ],
                'audit': {'attempted': True, 'stored': True, 'raw_content_included': False},
                'redaction': {'raw_content_included': False, 'secret_blocked_count': 0},
            }

        self.server.dashboard_read_model.read_dashboard_turn_content = fake_read_dashboard_turn_content
        try:
            response = self.client.get('/api/admin/dashboard/turns/turn-1/content?conversation_id=conv-1&window=24h')
        finally:
            self.server.dashboard_read_model.read_dashboard_turn_content = original

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['kind'], 'dashboard_turn_content_gate')
        self.assertTrue(data['availability']['loaded_after_explicit_action'])
        self.assertFalse(data['availability']['preloaded'])
        self.assertEqual(data['items'][0]['status'], 'fingerprint_only')
        self.assertEqual(observed['turn_id'], 'turn-1')
        self.assertEqual(observed['args'].get('conversation_id'), 'conv-1')
        self.assertIsNotNone(observed['audit_fn'])
        self._assert_content_free(data)

    def test_dashboard_routes_map_read_model_errors(self) -> None:
        original = self.server.dashboard_read_model.read_dashboard_overview
        self.server.dashboard_read_model.read_dashboard_overview = (
            lambda *_args, **_kwargs: (_ for _ in ()).throw(ValueError('invalid dashboard window: broken'))
        )
        try:
            response = self.client.get('/api/admin/dashboard/overview?window=broken')
        finally:
            self.server.dashboard_read_model.read_dashboard_overview = original

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid dashboard window: broken'})

    def test_dashboard_turn_inspection_route_maps_not_found(self) -> None:
        original = self.server.dashboard_read_model.read_dashboard_turn_inspection
        self.server.dashboard_read_model.read_dashboard_turn_inspection = (
            lambda *_args, **_kwargs: (_ for _ in ()).throw(LookupError('dashboard turn not found'))
        )
        try:
            response = self.client.get('/api/admin/dashboard/turns/missing/inspection?conversation_id=conv-1')
        finally:
            self.server.dashboard_read_model.read_dashboard_turn_inspection = original

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'dashboard turn not found'})

    def test_dashboard_turn_content_route_maps_not_found(self) -> None:
        original = self.server.dashboard_read_model.read_dashboard_turn_content
        self.server.dashboard_read_model.read_dashboard_turn_content = (
            lambda *_args, **_kwargs: (_ for _ in ()).throw(LookupError('dashboard turn not found'))
        )
        try:
            response = self.client.get('/api/admin/dashboard/turns/missing/content?conversation_id=conv-1')
        finally:
            self.server.dashboard_read_model.read_dashboard_turn_content = original

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'dashboard turn not found'})

    def test_dashboard_route_available_without_admin_token_in_loopback_tests(self) -> None:
        original = self.server.dashboard_read_model.read_dashboard_overview
        self.server.dashboard_read_model.read_dashboard_overview = (
            lambda *_args, **_kwargs: {
                'kind': 'dashboard_overview',
                'window': {'key': '24h'},
                'pulse': {'turns_observed': 0},
                'module_catalog': {'module_keys': []},
                'module_totals': {},
                'metric_buckets': [],
                'source': {'limits': {'event_limit_dependency': False}},
                'redaction': {'raw_content_included': False},
            }
        )
        try:
            response = self.client.get('/api/admin/dashboard/overview')
        finally:
            self.server.dashboard_read_model.read_dashboard_overview = original

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
