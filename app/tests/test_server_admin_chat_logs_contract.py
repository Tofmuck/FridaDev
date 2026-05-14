from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


class ServerAdminChatLogsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self._original_admin_token = self.server.config.FRIDA_ADMIN_TOKEN
        self._original_admin_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY

    def tearDown(self) -> None:
        self.server.config.FRIDA_ADMIN_TOKEN = self._original_admin_token
        self.server.config.FRIDA_ADMIN_LAN_ONLY = self._original_admin_lan_only

    def test_admin_chat_logs_route_returns_paginated_payload(self) -> None:
        observed = {'kwargs': None}
        original_read = self.server.log_store.read_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'items': [
                    {
                        'event_id': 'evt-1',
                        'conversation_id': 'conv-1',
                        'turn_id': 'turn-1',
                        'ts': '2026-03-27T12:00:00+00:00',
                        'stage': 'turn_start',
                        'status': 'ok',
                        'duration_ms': None,
                        'payload': {'web_search_enabled': False},
                    }
                ],
                'count': 1,
                'total': 4,
                'limit': 1,
                'offset': 0,
                'next_offset': 1,
                'filters': {
                    'conversation_id': 'conv-1',
                    'turn_id': 'turn-1',
                    'stage': 'turn_start',
                    'status': 'ok',
                    'ts_from': '2026-03-27T11:00:00Z',
                    'ts_to': '2026-03-27T13:00:00Z',
                },
            }

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            response = self.client.get(
                '/api/admin/logs/chat?limit=1&offset=0'
                '&conversation_id=conv-1&turn_id=turn-1&stage=turn_start&status=ok'
                '&ts_from=2026-03-27T11:00:00Z&ts_to=2026-03-27T13:00:00Z'
            )
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['total'], 4)
        self.assertEqual(data['limit'], 1)
        self.assertEqual(data['offset'], 0)
        self.assertEqual(data['next_offset'], 1)
        self.assertEqual(data['filters']['conversation_id'], 'conv-1')
        self.assertEqual(data['items'][0]['event_id'], 'evt-1')
        self.assertEqual(observed['kwargs']['limit'], 1)
        self.assertEqual(observed['kwargs']['offset'], 0)
        self.assertEqual(observed['kwargs']['conversation_id'], 'conv-1')
        self.assertEqual(observed['kwargs']['turn_id'], 'turn-1')
        self.assertEqual(observed['kwargs']['stage'], 'turn_start')
        self.assertEqual(observed['kwargs']['status'], 'ok')
        self.assertEqual(observed['kwargs']['ts_from'], '2026-03-27T11:00:00Z')
        self.assertEqual(observed['kwargs']['ts_to'], '2026-03-27T13:00:00Z')

    def test_admin_chat_logs_metadata_route_returns_selector_payload(self) -> None:
        observed = {'kwargs': None}
        original_read_metadata = self.server.log_store.read_chat_log_metadata

        def fake_read_chat_log_metadata(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'selected_conversation_id': 'conv-1',
                'conversations': [
                    {
                        'conversation_id': 'conv-1',
                        'last_ts': '2026-03-27T12:01:00+00:00',
                        'events_count': 2,
                    },
                    {
                        'conversation_id': 'conv-2',
                        'last_ts': '2026-03-27T11:58:00+00:00',
                        'events_count': 1,
                    },
                ],
                'turns': [
                    {
                        'turn_id': 'turn-1',
                        'last_ts': '2026-03-27T12:01:00+00:00',
                        'events_count': 2,
                    }
                ],
            }

        self.server.log_store.read_chat_log_metadata = fake_read_chat_log_metadata
        try:
            response = self.client.get('/api/admin/logs/chat/metadata?conversation_id=conv-1')
        finally:
            self.server.log_store.read_chat_log_metadata = original_read_metadata

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['selected_conversation_id'], 'conv-1')
        self.assertEqual(len(data['conversations']), 2)
        self.assertEqual(data['conversations'][0]['conversation_id'], 'conv-1')
        self.assertEqual(data['turns'][0]['turn_id'], 'turn-1')
        self.assertEqual(observed['kwargs'], {'conversation_id': 'conv-1'})

    def test_admin_chat_logs_metadata_route_is_available_without_admin_token(self) -> None:
        original_read_metadata = self.server.log_store.read_chat_log_metadata
        self.server.log_store.read_chat_log_metadata = (
            lambda **_kwargs: {
                'selected_conversation_id': None,
                'conversations': [],
                'turns': [],
            }
        )
        try:
            response_ok = self.client.get('/api/admin/logs/chat/metadata')
        finally:
            self.server.log_store.read_chat_log_metadata = original_read_metadata

        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.get_json()['ok'])

    def test_admin_chat_log_turns_route_returns_pipeline_payload(self) -> None:
        observed = {'kwargs': None}
        original_read_turns = self.server.log_store.read_chat_turn_pipeline

        def fake_read_chat_turn_pipeline(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'kind': 'chat_turn_pipeline_read_model',
                'schema_version': '1',
                'items': [
                    {
                        'kind': 'chat_turn_pipeline_item',
                        'schema_version': '1',
                        'conversation_id': 'conv-1',
                        'turn_id': 'turn-1',
                        'classification': 'complete',
                        'score': 100,
                        'persistence': {'status': 'saved'},
                        'providers': {'main': {'provider_caller': 'llm', 'status': 'ok'}},
                        'rag': {'source_kind': 'memory_chain_snapshot', 'retrieved': 2, 'injected': 1},
                        'identity': {'status': 'present', 'chars': 12, 'sha256_12': 'a' * 12},
                        'hermeneutic': {'status': 'present'},
                        'web': {'requested': False, 'status': 'not_applicable'},
                        'flags': {'raw_event_payloads_included': False, 'events_truncated': False},
                    }
                ],
                'count': 1,
                'total': 3,
                'limit': 1,
                'offset': 0,
                'next_offset': 1,
                'filters': {
                    'conversation_id': 'conv-1',
                    'turn_id': None,
                    'ts_from': '2026-05-14T00:00:00Z',
                    'ts_to': '2026-05-15T00:00:00Z',
                },
                'source': {'source_kind': 'chat_log_events', 'turns_truncated': True},
                'redaction': {'raw_event_payloads_included': False},
            }

        self.server.log_store.read_chat_turn_pipeline = fake_read_chat_turn_pipeline
        try:
            response = self.client.get(
                '/api/admin/logs/chat/turns'
                '?limit=1&offset=0&conversation_id=conv-1'
                '&ts_from=2026-05-14T00:00:00Z&ts_to=2026-05-15T00:00:00Z'
            )
        finally:
            self.server.log_store.read_chat_turn_pipeline = original_read_turns

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['kind'], 'chat_turn_pipeline_read_model')
        self.assertEqual(data['count'], 1)
        self.assertEqual(data['total'], 3)
        self.assertEqual(data['next_offset'], 1)
        self.assertEqual(data['items'][0]['classification'], 'complete')
        self.assertEqual(data['items'][0]['persistence']['status'], 'saved')
        self.assertFalse(data['items'][0]['flags']['raw_event_payloads_included'])
        self.assertEqual(observed['kwargs']['limit'], 1)
        self.assertEqual(observed['kwargs']['offset'], 0)
        self.assertEqual(observed['kwargs']['conversation_id'], 'conv-1')
        self.assertIsNone(observed['kwargs']['turn_id'])
        self.assertEqual(observed['kwargs']['ts_from'], '2026-05-14T00:00:00Z')
        self.assertEqual(observed['kwargs']['ts_to'], '2026-05-15T00:00:00Z')

    def test_admin_chat_log_turns_route_rejects_invalid_pagination(self) -> None:
        response = self.client.get('/api/admin/logs/chat/turns?limit=bad&offset=0')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid pagination parameters'})

    def test_admin_chat_logs_metrics_route_returns_compact_snapshot(self) -> None:
        observed = {'kwargs': None}
        original_read_metrics = self.server.log_store.read_full_turn_metrics_snapshot

        def fake_read_full_turn_metrics_snapshot(**kwargs):
            observed['kwargs'] = kwargs
            return {
                'kind': 'full_turn_metrics_snapshot',
                'events_count': 12,
                'turns_observed_count': 2,
                'checklist': {'classification_counts': {'complete': 1, 'degraded': 1}},
                'llm_call_provider_metrics': {'main_llm_call_count': 2, 'secondary_llm_call_count': 1},
                'web': {'requested_turns': 1},
                'node_state': {'read_hit_count': 1},
                'errors_by_stage': {},
                'filters': {
                    'ts_from': '2026-05-14T00:00:00Z',
                    'ts_to': '2026-05-15T00:00:00Z',
                    'event_limit': 50,
                },
                'source': {'events_total': 12, 'events_read': 12, 'events_truncated': False},
            }

        self.server.log_store.read_full_turn_metrics_snapshot = fake_read_full_turn_metrics_snapshot
        try:
            response = self.client.get(
                '/api/admin/logs/chat/metrics'
                '?ts_from=2026-05-14T00:00:00Z&ts_to=2026-05-15T00:00:00Z&event_limit=50'
            )
        finally:
            self.server.log_store.read_full_turn_metrics_snapshot = original_read_metrics

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['ok'])
        self.assertEqual(data['kind'], 'full_turn_metrics_snapshot')
        self.assertEqual(data['turns_observed_count'], 2)
        self.assertEqual(data['checklist']['classification_counts']['complete'], 1)
        self.assertEqual(data['llm_call_provider_metrics']['main_llm_call_count'], 2)
        self.assertEqual(data['web']['requested_turns'], 1)
        self.assertEqual(data['node_state']['read_hit_count'], 1)
        self.assertEqual(observed['kwargs']['ts_from'], '2026-05-14T00:00:00Z')
        self.assertEqual(observed['kwargs']['ts_to'], '2026-05-15T00:00:00Z')
        self.assertEqual(observed['kwargs']['event_limit'], 50)

    def test_admin_chat_logs_metrics_route_rejects_invalid_event_limit(self) -> None:
        response = self.client.get('/api/admin/logs/chat/metrics?event_limit=bad')

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid event_limit parameter'})

    def test_admin_chat_logs_route_rejects_invalid_pagination(self) -> None:
        response = self.client.get('/api/admin/logs/chat?limit=abc&offset=0')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid pagination parameters'})

    def test_admin_chat_logs_route_rejects_invalid_status_filter(self) -> None:
        original_read = self.server.log_store.read_chat_log_events
        self.server.log_store.read_chat_log_events = (
            lambda **_kwargs: (_ for _ in ()).throw(ValueError('invalid chat log status filter: broken'))
        )
        try:
            response = self.client.get('/api/admin/logs/chat?status=broken')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid chat log status filter: broken'})

    def test_admin_chat_logs_route_rejects_invalid_ts_from(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_from=not-a-date')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid ts_from timestamp: not-a-date'})

    def test_admin_chat_logs_route_rejects_invalid_ts_to(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_to=not-a-date')
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json(), {'ok': False, 'error': 'invalid ts_to timestamp: not-a-date'})

    def test_admin_chat_logs_route_is_available_without_admin_token(self) -> None:
        original_read = self.server.log_store.read_chat_log_events
        self.server.log_store.read_chat_log_events = (
            lambda **_kwargs: {
                'items': [],
                'count': 0,
                'total': 0,
                'limit': 1,
                'offset': 0,
                'next_offset': None,
                'filters': {
                    'conversation_id': None,
                    'turn_id': None,
                    'stage': None,
                    'status': None,
                    'ts_from': None,
                    'ts_to': None,
                },
            }
        )
        try:
            response_ok = self.client.get('/api/admin/logs/chat?limit=1')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response_ok.status_code, 200)
        self.assertTrue(response_ok.get_json()['ok'])


if __name__ == '__main__':
    unittest.main()
