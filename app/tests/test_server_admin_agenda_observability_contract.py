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

from agenda import observability_read_model
from tests.support.server_test_bootstrap import load_server_module_for_tests


FORBIDDEN_VALUES = (
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


if __name__ == '__main__':
    unittest.main()
