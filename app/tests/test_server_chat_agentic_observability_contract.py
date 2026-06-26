from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / 'web').exists() and (parent / 'server.py').exists():
            return parent
    raise RuntimeError('Unable to resolve APP_DIR from test path')


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

import server


class ServerChatAgenticObservabilityContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = server.app.test_client()

    def _patch_chat_response(self, result: dict[str, Any]) -> tuple[list[dict[str, Any]], Any]:
        observed_events: list[dict[str, Any]] = []
        originals = {
            'chat_response': server.chat_service.chat_response,
            'insert': server.chat_turn_logger.log_store.insert_chat_log_event,
            'dashboard': server.dashboard_materialization_runtime.schedule_recent_dashboard_analytics_materialization,
        }

        def fake_chat_response(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            return result

        def fake_insert(event: dict[str, Any], **_kwargs: Any) -> bool:
            observed_events.append(event)
            return True

        server.chat_service.chat_response = fake_chat_response
        server.chat_turn_logger.log_store.insert_chat_log_event = fake_insert
        server.dashboard_materialization_runtime.schedule_recent_dashboard_analytics_materialization = (
            lambda **_kwargs: None
        )

        def restore() -> None:
            server.chat_service.chat_response = originals['chat_response']
            server.chat_turn_logger.log_store.insert_chat_log_event = originals['insert']
            server.dashboard_materialization_runtime.schedule_recent_dashboard_analytics_materialization = (
                originals['dashboard']
            )

        return observed_events, restore

    def test_chat_4xx_product_refusal_is_not_logged_as_error(self) -> None:
        observed_events, restore = self._patch_chat_response(
            {
                'kind': 'json',
                'status': 400,
                'payload': {
                    'ok': False,
                    'reason_code': 'not_applicable',
                    'error': 'redacted product refusal',
                },
                'headers': {},
            }
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'hello'})
        finally:
            restore()

        self.assertEqual(response.status_code, 400)
        stages = {event['stage']: event for event in observed_events}
        self.assertEqual(stages['chat_response']['status'], 'not_applicable')
        self.assertEqual(stages['chat_response']['payload_json']['reason_code'], 'not_applicable')
        self.assertEqual(stages['chat_response']['payload_json']['reason_short_chars'], len('chat status 400'))
        self.assertFalse(stages['chat_response']['payload_json']['reason_short_included'])
        self.assertNotIn('reason_short', stages['chat_response']['payload_json'])
        self.assertFalse(stages['chat_response']['payload_json'].get('rejected_payload', False))
        self.assertEqual(stages['turn_end']['status'], 'not_applicable')
        self.assertNotIn('error', {event['status'] for event in observed_events})
        serialized = json.dumps(observed_events, sort_keys=True)
        self.assertNotIn('redacted product refusal', serialized)
        self.assertNotIn('chat status 400', serialized)
        self.assertNotIn('hello', serialized)

    def test_chat_5xx_response_remains_error(self) -> None:
        observed_events, restore = self._patch_chat_response(
            {
                'kind': 'json',
                'status': 503,
                'payload': {
                    'ok': False,
                    'error': 'redacted upstream failure',
                },
                'headers': {},
            }
        )
        try:
            response = self.client.post('/api/chat', json={'message': 'hello'})
        finally:
            restore()

        self.assertEqual(response.status_code, 503)
        stages = {event['stage']: event for event in observed_events}
        self.assertEqual(stages['error']['status'], 'error')
        self.assertEqual(stages['error']['payload_json']['error_code'], 'upstream_error')
        self.assertEqual(stages['turn_end']['status'], 'error')
        serialized = json.dumps(observed_events, sort_keys=True)
        self.assertNotIn('redacted upstream failure', serialized)
        self.assertNotIn('hello', serialized)


if __name__ == '__main__':
    unittest.main()
