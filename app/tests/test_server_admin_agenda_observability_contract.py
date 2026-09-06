from __future__ import annotations

import json
import sys
import types
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - local host may not have repo deps.
    sys.modules['psycopg'] = types.ModuleType('psycopg')
    rows_module = types.ModuleType('psycopg.rows')
    rows_module.dict_row = object()
    sys.modules['psycopg.rows'] = rows_module
    types_module = types.ModuleType('psycopg.types')
    json_module = types.ModuleType('psycopg.types.json')
    json_module.Json = lambda value: value
    sys.modules['psycopg.types'] = types_module
    sys.modules['psycopg.types.json'] = json_module

from agenda import agent_contract, chat_runtime, observability_read_model
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.support.agenda_runtime_golden import (
    FakeAgendaModelClient,
    propose_create_payload,
)


FORBIDDEN_VALUES = (
    'SYNTHETIC-USER-CONTENT',
    'SYNTHETIC-AGENDA-TITLE',
    'SYNTHETIC-AGENDA-LOCATION',
    'SYNTHETIC-AGENDA-DESCRIPTION',
    'Fixture Private Title',
    'Fixture Private Location',
    'Fixture Private Description',
    'uid:fixture-private',
    'etag-fixture-private',
    '/remote.php/dav/calendars/tof/private/event.ics',
    'BEGIN:VEVENT',
    'Authorization: Bearer fixture',
    'Cookie: fixture',
    'fixture-app-password',
)


class ServerAdminAgendaObservabilityContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()

    def test_admin_agenda_observability_is_content_free(self) -> None:
        original_read = self.server.log_store.read_chat_log_events

        def fake_read_chat_log_events(**kwargs):
            self.assertEqual(kwargs.get('stage'), 'agenda')
            return {
                'items': [
                    {
                        'stage': 'agenda',
                        'status': 'ok',
                        'ts': '2026-06-09T15:40:00Z',
                        'payload': {
                            'schema_version': 'frida_agenda_lot5_readonly_v1',
                            'status': 'ok',
                            'reason_code': 'agenda_readonly_ok',
                            'product_method': 'read_today',
                            'read_tool_names': ['event_query_range'],
                            'read_event_count': 1,
                            'caldav_access': True,
                            'nextcloud_access': True,
                            'secret_access': True,
                            'mutation_attempted': False,
                            'final_response_override': True,
                            'title': 'Fixture Private Title',
                            'location': 'Fixture Private Location',
                            'description': 'Fixture Private Description',
                            'uid': 'uid:fixture-private',
                            'etag': 'etag-fixture-private',
                            'caldav_path': '/remote.php/dav/calendars/tof/private/event.ics',
                            'raw_ics': 'BEGIN:VEVENT',
                            'authorization': 'Authorization: Bearer fixture',
                            'cookie': 'Cookie: fixture',
                            'app_password': 'fixture-app-password',
                            'content_free': True,
                        },
                    },
                ],
            }

        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        try:
            response = self.client.get('/api/admin/agenda/observability')
        finally:
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload['ok'])
        self.assertEqual(payload['schema_version'], observability_read_model.READ_MODEL_SCHEMA_VERSION)
        self.assertEqual(payload['admin_route'], observability_read_model.ADMIN_ROUTE)
        self.assertTrue(payload['content_free'])
        self.assertTrue(payload['redacted'])
        self.assertEqual(payload['event_summary']['event_count'], 1)
        self.assertEqual(payload['event_summary']['tool_names'], ['event_query_range'])
        self.assertEqual(payload['event_summary']['caldav_access_count'], 1)
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for marker in FORBIDDEN_VALUES:
            self.assertNotIn(marker, encoded)

    def test_admin_agenda_observability_rejects_invalid_limit(self) -> None:
        response = self.client.get('/api/admin/agenda/observability?limit=not-an-int')
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.get_json()['ok'])

    def test_admin_agenda_observability_projects_pending_writer_fields(self) -> None:
        agent_payload = propose_create_payload()
        agent_payload['calendar_scope'] = {
            'calendar_ids': ['family'],
            'family_calendar': True,
            'ambiguity': 'none',
        }
        agent_payload['draft']['calendar_id'] = 'family'
        agent_payload['mutation']['confirmation_level'] = 'reinforced'
        agent_payload['risk_flags'] = ['family_calendar']
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='SYNTHETIC-USER-CONTENT',
            now_iso='2026-06-08T00:00:00Z',
            config_module=types.SimpleNamespace(FRIDA_TIMEZONE='UTC'),
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=FakeAgendaModelClient(agent_payload),
            pending_id_factory=lambda: 'agenda-pending-route',
        )
        stored_events = []
        original_insert = self.server.chat_turn_logger.log_store.insert_chat_log_event
        original_read = self.server.log_store.read_chat_log_events

        def fake_insert_chat_log_event(event):
            stored_events.append(dict(event))
            return True

        def fake_read_chat_log_events(**kwargs):
            self.assertEqual(kwargs.get('stage'), 'agenda')
            return {'items': [event for event in stored_events if event.get('stage') == 'agenda']}

        self.server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert_chat_log_event
        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        turn_token = self.server.chat_turn_logger.begin_turn(
            conversation_id='conv-agenda-observability-route',
            user_msg='SYNTHETIC-USER-CONTENT',
            web_search_enabled=False,
        )
        try:
            self.server.chat_service._emit_agenda_observability(result)
            response = self.client.get('/api/admin/agenda/observability')
        finally:
            self.server.chat_turn_logger.end_turn(turn_token, final_status='ok')
            self.server.chat_turn_logger.log_store.insert_chat_log_event = original_insert
            self.server.log_store.read_chat_log_events = original_read

        self.assertEqual(response.status_code, 200)
        agenda_events = [event for event in stored_events if event.get('stage') == 'agenda']
        self.assertEqual(len(agenda_events), 1)
        self.assertEqual(agenda_events[0]['status'], 'ok')
        self.assertEqual(agenda_events[0]['payload_json']['pending_status'], 'pending')
        self.assertEqual(
            agenda_events[0]['payload_json']['pending_confirmation_level'],
            'reinforced',
        )
        self.assertEqual(
            agenda_events[0]['payload_json']['pending_risk_flags'],
            ['family_calendar'],
        )
        payload = response.get_json()
        summary = payload['event_summary']
        self.assertEqual(summary['pending_status_counts'], {'pending': 1})
        self.assertEqual(summary['confirmation_levels'], ['reinforced'])
        self.assertEqual(summary['risk_flags'], ['family_calendar'])
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
        for marker in FORBIDDEN_VALUES:
            self.assertNotIn(marker, encoded)


if __name__ == '__main__':
    unittest.main()
