from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


_TOKEN_LIKE_SAFE_CODE_SENTINEL = 'ghp_artificiallot71abcdef'


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

    def _assert_admin_error_content_free(
        self,
        response,
        *,
        status_code: int,
        error: str,
        error_code: str,
        reason_code: str,
        forbidden: tuple[str, ...] = (),
    ) -> None:
        self.assertEqual(response.status_code, status_code)
        data = response.get_json()
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertFalse(data['ok'])
        self.assertEqual(data['error'], error)
        self.assertEqual(data['error_code'], error_code)
        self.assertEqual(data['reason_code'], reason_code)
        for marker in forbidden:
            self.assertNotIn(marker, encoded)

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
        self.assertEqual(observed['kwargs']['payload_projection'], 'admin')
        self.assertTrue(observed['kwargs']['fail_closed'])
        self.assertFalse(data['redaction']['raw_event_payloads_included'])
        self.assertFalse(data['items'][0]['redaction']['raw_event_payloads_included'])
        self.assertEqual(data['items'][0]['payload']['web_search_enabled'], False)

    def test_admin_chat_logs_route_projects_payload_content_free(self) -> None:
        original_read = self.server.log_store.read_chat_log_events
        dangerous_values = (
            'RAW USER MESSAGE SENTINEL 5A',
            'RAW PROMPT SENTINEL 5A',
            'RAW PROVIDER PAYLOAD SENTINEL 5A',
            'Authorization: Bearer RAW_TOKEN_SENTINEL_5A',
            'RAW EXCEPTION SENTINEL 5A',
            'RAW FIELD SENTINEL 5A',
            'BEGIN:VEVENT RAW DAV XML SENTINEL 5A',
            'https://logs.example.internal/path',
            'https://provider.example/call',
            'bearer-token-like',
            '/private/admin/logs/source',
        )

        def fake_read_chat_log_events(**kwargs):
            self.assertEqual(kwargs.get('payload_projection'), 'admin')
            self.assertTrue(kwargs.get('fail_closed'))
            return {
                'items': [
                    {
                        'event_id': 'evt-raw-admin',
                        'conversation_id': 'conv-raw-admin',
                        'turn_id': 'turn-raw-admin',
                        'ts': '2026-06-21T12:00:00+00:00',
                        'stage': 'llm_call',
                        'status': 'error',
                        'status_v1': 'error',
                        'status_schema_version': 'agentic_v1',
                        'legacy_status': False,
                        'duration_ms': 42,
                        'payload': {
                            'status_schema_version': 'agentic_v1',
                            'reason_code': 'provider_timeout',
                            'error_code': 'upstream_error',
                            'model': 'openai/gpt-5.4-mini',
                            'prompt_kind': 'chat_system_augmented',
                            'response_chars': 16,
                            'message': dangerous_values[0],
                            'prompt': dangerous_values[1],
                            'provider_payload': {'body': dangerous_values[2]},
                            'authorization': dangerous_values[3],
                            'error': dangerous_values[4],
                            'raw': dangerous_values[5],
                            'raw_content_included': True,
                            'caldav_xml': dangerous_values[6],
                        },
                    },
                    {
                        'event_id': 'evt-legacy-admin',
                        'conversation_id': 'conv-raw-admin',
                        'turn_id': 'turn-legacy-admin',
                        'ts': '2026-06-21T11:59:00+00:00',
                        'stage': 'branch_skipped',
                        'status': 'skipped',
                        'status_v1': 'skipped',
                        'status_schema_version': 'legacy',
                        'legacy_status': True,
                        'duration_ms': None,
                        'payload': {'reason_code': 'legacy_skip', 'message': dangerous_values[0]},
                    },
                    {
                        'event_id': 'evt-allowlist-admin',
                        'conversation_id': 'conv-raw-admin',
                        'turn_id': 'turn-allowlist-admin',
                        'ts': '2026-06-21T11:58:00+00:00',
                        'stage': 'llm_call',
                        'status': 'error',
                        'status_v1': 'error',
                        'status_schema_version': 'agentic_v1',
                        'legacy_status': False,
                        'duration_ms': 43,
                        'payload': {
                            'status_schema_version': 'agentic_v1',
                            'reason_code': dangerous_values[7],
                            'provider_caller': dangerous_values[8],
                            'error_code': dangerous_values[9],
                            'runtime_source': dangerous_values[10],
                            'model': 'openai/gpt-5.4-mini',
                            'prompt_kind': 'chat_system_augmented',
                        },
                    },
                    {
                        'event_id': 'evt-tokenlike-admin',
                        'conversation_id': 'conv-raw-admin',
                        'turn_id': 'turn-tokenlike-admin',
                        'ts': '2026-06-21T11:57:00+00:00',
                        'stage': 'llm_call',
                        'status': 'error',
                        'status_v1': 'error',
                        'status_schema_version': 'agentic_v1',
                        'legacy_status': False,
                        'duration_ms': 44,
                        'payload': {
                            'status_schema_version': 'agentic_v1',
                            'reason_code': _TOKEN_LIKE_SAFE_CODE_SENTINEL,
                            'error_code': 'upstream_error',
                            'model': 'openai/gpt-5.4-mini',
                            'prompt_kind': 'chat_system_augmented',
                        },
                    },
                ],
                'count': 4,
                'total': 4,
                'limit': kwargs.get('limit', 100),
                'offset': kwargs.get('offset', 0),
                'next_offset': None,
                'filters': {
                    'conversation_id': kwargs.get('conversation_id'),
                    'turn_id': kwargs.get('turn_id'),
                    'stage': kwargs.get('stage'),
                    'status': kwargs.get('status'),
                    'ts_from': kwargs.get('ts_from'),
                    'ts_to': kwargs.get('ts_to'),
                },
            }

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            response = self.client.get('/api/admin/logs/chat?conversation_id=conv-raw-admin')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertTrue(data['ok'])
        for marker in dangerous_values:
            self.assertNotIn(marker, encoded)
        self.assertNotIn(_TOKEN_LIKE_SAFE_CODE_SENTINEL, encoded)
        self.assertFalse(data['redaction']['raw_event_payloads_included'])
        self.assertFalse(data['redaction']['raw_content_included'])
        self.assertFalse(data['redaction']['raw_prompt_included'])
        self.assertFalse(data['redaction']['raw_provider_payload_included'])
        self.assertFalse(data['redaction']['raw_webdav_payload_included'])
        self.assertFalse(data['redaction']['raw_error_message_included'])
        self.assertEqual(data['items'][0]['payload']['reason_code'], 'provider_timeout')
        self.assertEqual(data['items'][0]['payload']['error_code'], 'upstream_error')
        self.assertEqual(data['items'][0]['payload']['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(data['items'][0]['payload']['prompt_kind'], 'chat_system_augmented')
        self.assertEqual(data['items'][0]['payload']['response_chars'], 16)
        self.assertFalse(data['items'][0]['payload']['raw_content_included'])
        self.assertNotIn('raw', data['items'][0]['payload'])
        self.assertEqual(data['items'][0]['status_schema_version'], 'agentic_v1')
        self.assertFalse(data['items'][0]['legacy_status'])
        self.assertEqual(data['items'][1]['status_schema_version'], 'legacy')
        self.assertTrue(data['items'][1]['legacy_status'])
        self.assertEqual(data['items'][2]['payload']['reason_code'], '[redacted]')
        self.assertEqual(data['items'][2]['payload']['provider_caller'], '[redacted]')
        self.assertEqual(data['items'][2]['payload']['error_code'], '[redacted]')
        self.assertEqual(data['items'][2]['payload']['runtime_source'], '[redacted]')
        self.assertEqual(data['items'][2]['payload']['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(data['items'][2]['payload']['prompt_kind'], 'chat_system_augmented')
        self.assertEqual(data['items'][3]['payload']['reason_code'], '[redacted]')
        self.assertEqual(data['items'][3]['payload']['error_code'], 'upstream_error')

    def test_legacy_admin_logs_route_projects_payload_content_free(self) -> None:
        original_read = self.server.admin_logs.read_logs
        observed = {'limit': None, 'fail_closed': None}
        dangerous_values = (
            'RAW USER MESSAGE SENTINEL LEGACY',
            'RAW PROMPT SENTINEL LEGACY',
            'RAW PROVIDER PAYLOAD SENTINEL LEGACY',
            'Authorization: Bearer RAW_TOKEN_SENTINEL_LEGACY',
            'RAW EXCEPTION SENTINEL LEGACY',
            'RAW FIELD SENTINEL LEGACY',
            'BEGIN:VEVENT RAW DAV XML SENTINEL LEGACY',
            'https://logs.example.internal/path',
            'https://provider.example/call',
            'bearer-token-like',
            '/private/admin/logs/source',
        )

        def fake_read_logs(limit=200, *, fail_closed=False):
            observed['limit'] = limit
            observed['fail_closed'] = fail_closed
            return [
                {
                    'timestamp': '2026-06-21T12:00:00+00:00',
                    'event': 'llm_call',
                    'level': 'ERROR',
                    'status_schema_version': 'agentic_v1',
                    'reason_code': 'provider_timeout',
                    'error_code': 'upstream_error',
                    'model': 'openai/gpt-5.4-mini',
                    'prompt_kind': 'chat_system_augmented',
                    'message': dangerous_values[0],
                    'prompt': dangerous_values[1],
                    'provider_payload': {'body': dangerous_values[2]},
                    'authorization': dangerous_values[3],
                    'error': dangerous_values[4],
                    'raw': dangerous_values[5],
                    'raw_content_included': True,
                    'caldav_xml': dangerous_values[6],
                    'source': dangerous_values[7],
                    'provider_caller': dangerous_values[8],
                    'write_mode': dangerous_values[9],
                    'runtime_source': dangerous_values[10],
                }
            ]

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/logs?limit=1')
        finally:
            self.server.admin_logs.read_logs = original_read

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertTrue(data['ok'])
        self.assertEqual(data['count'], 1)
        self.assertEqual(observed['limit'], 1)
        self.assertTrue(observed['fail_closed'])
        for marker in dangerous_values:
            self.assertNotIn(marker, encoded)
        self.assertEqual(data['payload_projection_schema'], 'admin_log_event_projection_v1')
        self.assertFalse(data['redaction']['raw_event_payloads_included'])
        self.assertFalse(data['redaction']['raw_content_included'])
        self.assertFalse(data['redaction']['raw_prompt_included'])
        self.assertFalse(data['redaction']['raw_provider_payload_included'])
        self.assertFalse(data['redaction']['raw_webdav_payload_included'])
        self.assertFalse(data['redaction']['raw_error_message_included'])
        item = data['logs'][0]
        self.assertTrue(item['legacy_admin_log'])
        self.assertEqual(item['event'], 'llm_call')
        self.assertEqual(item['level'], 'ERROR')
        self.assertEqual(item['payload']['reason_code'], 'provider_timeout')
        self.assertEqual(item['payload']['error_code'], 'upstream_error')
        self.assertEqual(item['payload']['model'], 'openai/gpt-5.4-mini')
        self.assertEqual(item['payload']['prompt_kind'], 'chat_system_augmented')
        self.assertEqual(item['payload']['source'], '[redacted]')
        self.assertEqual(item['payload']['provider_caller'], '[redacted]')
        self.assertEqual(item['payload']['write_mode'], '[redacted]')
        self.assertEqual(item['payload']['runtime_source'], '[redacted]')
        self.assertFalse(item['payload']['raw_content_included'])
        self.assertNotIn('raw', item['payload'])
        self.assertNotIn('message', item)
        self.assertNotIn('error', item)

    def test_legacy_admin_logs_route_fail_closed_without_raw_exception(self) -> None:
        original_read = self.server.admin_logs.read_logs

        def fake_read_logs(**_kwargs):
            raise RuntimeError('RAW LEGACY LOG READ SENTINEL')

        self.server.admin_logs.read_logs = fake_read_logs
        try:
            response = self.client.get('/api/admin/logs?limit=1')
        finally:
            self.server.admin_logs.read_logs = original_read

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertFalse(data['ok'])
        self.assertEqual(data['reason_code'], 'admin_logs_read_failed')
        self.assertNotIn('RAW LEGACY LOG READ SENTINEL', encoded)

    def test_admin_chat_logs_route_fail_closed_without_raw_exception(self) -> None:
        original_read = self.server.log_store.read_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            self.assertTrue(kwargs.get('fail_closed'))
            raise RuntimeError('RAW CHAT LOG READ SENTINEL')

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            response = self.client.get('/api/admin/logs/chat?limit=1')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 500)
        data = response.get_json()
        encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self.assertFalse(data['ok'])
        self.assertEqual(data['reason_code'], 'chat_log_events_read_failed')
        self.assertNotIn('RAW CHAT LOG READ SENTINEL', encoded)

    def test_admin_chat_log_auxiliary_reads_fail_closed_without_raw_exception(self) -> None:
        cases = (
            (
                'read_chat_log_metadata',
                '/api/admin/logs/chat/metadata',
                'chat_log_metadata_read_failed',
            ),
            (
                'read_chat_turn_pipeline',
                '/api/admin/logs/chat/turns',
                'chat_log_turns_read_failed',
            ),
            (
                'read_full_turn_metrics_snapshot',
                '/api/admin/logs/chat/metrics',
                'chat_log_metrics_read_failed',
            ),
        )
        for attr_name, route, reason_code in cases:
            with self.subTest(route=route):
                original = getattr(self.server.log_store, attr_name)

                def fake_read(**_kwargs):
                    raise RuntimeError(f'RAW AUXILIARY LOG READ SENTINEL {reason_code}')

                setattr(self.server.log_store, attr_name, fake_read)
                try:
                    response = self.client.get(route)
                finally:
                    setattr(self.server.log_store, attr_name, original)

                self.assertEqual(response.status_code, 500)
                data = response.get_json()
                encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
                self.assertFalse(data['ok'])
                self.assertEqual(data['reason_code'], reason_code)
                self.assertNotIn('RAW AUXILIARY LOG READ SENTINEL', encoded)

    def test_admin_chat_log_turns_and_metrics_fail_closed_on_real_read_error(self) -> None:
        original_conn = self.server.log_store._conn

        class Boom:
            def __enter__(self) -> 'Boom':
                raise RuntimeError('RAW ROUTE DB BOOM SENTINEL')

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

        def bad_conn() -> Boom:
            return Boom()

        self.server.log_store._conn = bad_conn
        try:
            cases = (
                ('/api/admin/logs/chat/turns', 'chat_log_turns_read_failed'),
                ('/api/admin/logs/chat/metrics', 'chat_log_metrics_read_failed'),
            )
            for route, reason_code in cases:
                with self.subTest(route=route):
                    response = self.client.get(route)
                    self.assertEqual(response.status_code, 500)
                    data = response.get_json()
                    encoded = json.dumps(data, ensure_ascii=False, sort_keys=True)
                    self.assertFalse(data['ok'])
                    self.assertEqual(data['reason_code'], reason_code)
                    self.assertNotIn('RAW ROUTE DB BOOM SENTINEL', encoded)
        finally:
            self.server.log_store._conn = original_conn

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
        self.assertTrue(observed['kwargs']['fail_closed'])
        self.assertIs(observed['kwargs']['conn_factory'], self.server.log_store._conn)

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
        self.assertTrue(observed['kwargs']['fail_closed'])
        self.assertIs(observed['kwargs']['conn_factory'], self.server.log_store._conn)

    def test_admin_biblio_observability_route_is_content_free_and_read_only(self) -> None:
        original_base_url = getattr(self.server.config, 'BIBLIO_CATALOGUE_BASE_URL', None)
        original_timeout = getattr(self.server.config, 'BIBLIO_CATALOGUE_TIMEOUT_S', None)
        self.server.config.BIBLIO_CATALOGUE_BASE_URL = (
            'https://human-user:human-secret@catalogue.example.test:9443/doc-api?token=hidden#frag'
        )
        self.server.config.BIBLIO_CATALOGUE_TIMEOUT_S = 13
        try:
            response = self.client.get('/api/admin/biblio/observability')
        finally:
            if original_base_url is None:
                delattr(self.server.config, 'BIBLIO_CATALOGUE_BASE_URL')
            else:
                self.server.config.BIBLIO_CATALOGUE_BASE_URL = original_base_url
            if original_timeout is None:
                delattr(self.server.config, 'BIBLIO_CATALOGUE_TIMEOUT_S')
            else:
                self.server.config.BIBLIO_CATALOGUE_TIMEOUT_S = original_timeout

        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        encoded = str(data)
        self.assertTrue(data['ok'])
        self.assertEqual(data['kind'], 'biblio_admin_observability')
        self.assertEqual(data['config']['catalogue_base_url'], 'https://catalogue.example.test:9443/doc-api')
        self.assertEqual(data['config']['timeout_s'], 13)
        self.assertTrue(data['config']['get_only'])
        self.assertTrue(data['module_state']['chat_wired'])
        self.assertTrue(data['module_state']['frontend_wired'])
        self.assertTrue(data['module_state']['toggle_wired'])
        self.assertFalse(data['module_state']['db_write'])
        self.assertFalse(data['module_state']['automatic_catalogue_call'])
        self.assertFalse(data['redaction']['raw_content_included'])
        self.assertNotIn('human-secret', encoded)
        self.assertNotIn('token=hidden', encoded)

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
        forbidden = (
            'ARTIFICIAL_ADMIN_STATUS_SECRET',
            'https://example.invalid/private',
            '/private/admin/status',
            'provider payload raw',
        )
        self.server.log_store.read_chat_log_events = (
            lambda **_kwargs: (_ for _ in ()).throw(
                ValueError(
                    'invalid chat log status filter: '
                    'https://example.invalid/private?to'
                    'ken=ARTIFICIAL_ADMIN_STATUS_SECRET '
                    '/private/admin/status provider payload raw'
                )
            )
        )
        try:
            response = self.client.get('/api/admin/logs/chat?status=broken')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self._assert_admin_error_content_free(
            response,
            status_code=400,
            error='requete admin invalide',
            error_code='admin_bad_request',
            reason_code='admin_chat_logs_bad_request',
            forbidden=forbidden,
        )

    def test_admin_chat_logs_route_rejects_invalid_ts_from(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_from=not-a-date')
        self._assert_admin_error_content_free(
            response,
            status_code=400,
            error='requete admin invalide',
            error_code='admin_bad_request',
            reason_code='admin_chat_logs_bad_request',
            forbidden=('not-a-date',),
        )

    def test_admin_chat_logs_route_rejects_invalid_ts_to(self) -> None:
        response = self.client.get('/api/admin/logs/chat?ts_to=not-a-date')
        self._assert_admin_error_content_free(
            response,
            status_code=400,
            error='requete admin invalide',
            error_code='admin_bad_request',
            reason_code='admin_chat_logs_bad_request',
            forbidden=('not-a-date',),
        )

    def test_admin_chat_log_auxiliary_value_errors_are_content_free(self) -> None:
        forbidden = (
            'ARTIFICIAL_ADMIN_AUX_SECRET',
            'https://example.invalid/private',
            '/private/admin/aux',
        )
        cases = (
            (
                'read_chat_log_metadata',
                '/api/admin/logs/chat/metadata',
                'admin_chat_logs_metadata_bad_request',
            ),
            (
                'read_chat_turn_pipeline',
                '/api/admin/logs/chat/turns',
                'admin_chat_log_turns_bad_request',
            ),
            (
                'read_full_turn_metrics_snapshot',
                '/api/admin/logs/chat/metrics',
                'admin_chat_log_metrics_bad_request',
            ),
        )
        for attr_name, route, reason_code in cases:
            with self.subTest(route=route):
                original = getattr(self.server.log_store, attr_name)

                def fake_read(**_kwargs):
                    raise ValueError(
                        'invalid admin auxiliary value: '
                        'https://example.invalid/private?to'
                        'ken=ARTIFICIAL_ADMIN_AUX_SECRET /private/admin/aux'
                    )

                setattr(self.server.log_store, attr_name, fake_read)
                try:
                    response = self.client.get(route)
                finally:
                    setattr(self.server.log_store, attr_name, original)

                self._assert_admin_error_content_free(
                    response,
                    status_code=400,
                    error='requete admin invalide',
                    error_code='admin_bad_request',
                    reason_code=reason_code,
                    forbidden=forbidden,
                )

    def test_admin_chat_log_delete_and_export_value_errors_are_content_free(self) -> None:
        forbidden = (
            'ARTIFICIAL_ADMIN_EXPORT_SECRET',
            'https://example.invalid/private',
            '/private/admin/export',
        )
        cases = (
            (
                self.server.log_store,
                'delete_chat_log_events',
                'delete',
                '/api/admin/logs/chat?conversation_id=conv-1',
                'admin_chat_logs_delete_bad_request',
            ),
            (
                self.server.log_markdown_export,
                'export_chat_logs_markdown',
                'get',
                '/api/admin/logs/chat/export.md?conversation_id=conv-1',
                'admin_chat_logs_export_bad_request',
            ),
        )
        for target, attr_name, method, route, reason_code in cases:
            with self.subTest(route=route):
                original = getattr(target, attr_name)

                def fake_call(**_kwargs):
                    raise ValueError(
                        'invalid admin export value: '
                        'https://example.invalid/private?to'
                        'ken=ARTIFICIAL_ADMIN_EXPORT_SECRET /private/admin/export'
                    )

                setattr(target, attr_name, fake_call)
                try:
                    response = getattr(self.client, method)(route)
                finally:
                    setattr(target, attr_name, original)

                self._assert_admin_error_content_free(
                    response,
                    status_code=400,
                    error='requete admin invalide',
                    error_code='admin_bad_request',
                    reason_code=reason_code,
                    forbidden=forbidden,
                )

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
