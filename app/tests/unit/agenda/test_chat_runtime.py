from __future__ import annotations

import json
import unittest

from agenda import agent_contract, agent_runtime, chat_runtime, product_methods
from agenda.caldav_models import CalendarEvent, CalendarSummary


class AgendaChatRuntimeLot1Tests(unittest.TestCase):
    def test_normalize_agenda_enabled_matches_frontend_payload_contract(self) -> None:
        self.assertFalse(chat_runtime.normalize_agenda_enabled(None))
        self.assertFalse(chat_runtime.normalize_agenda_enabled(False))
        self.assertFalse(chat_runtime.normalize_agenda_enabled('off'))
        self.assertTrue(chat_runtime.normalize_agenda_enabled(True))
        self.assertTrue(chat_runtime.normalize_agenda_enabled('1'))
        self.assertTrue(chat_runtime.normalize_agenda_enabled('enabled'))

    def test_enabled_turn_with_default_runtime_off_is_content_free_noop_without_caldav_or_secret_access(self) -> None:
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda demain',
            conversation_id='conv-agenda',
            now_iso='2026-06-08T00:00:00Z',
        )

        self.assertTrue(result.enabled)
        self.assertFalse(result.used)
        self.assertEqual(result.status, agent_runtime.STATUS_SKIPPED)
        self.assertEqual(result.reason_code, agent_runtime.REASON_MODE_OFF)
        payload = result.observability_payload
        self.assertEqual(payload['schema_version'], 'frida_agenda_lot5_readonly_v1')
        self.assertEqual(payload['agent_schema_version'], agent_contract.SCHEMA_VERSION)
        self.assertTrue(payload['runtime_available'])
        self.assertEqual(payload['mode'], agent_contract.MODE_OFF)
        self.assertFalse(payload['caldav_access'])
        self.assertFalse(payload['nextcloud_access'])
        self.assertFalse(payload['secret_access'])
        self.assertFalse(payload['mutation_attempted'])
        self.assertFalse(payload['prompt_lane_injected'])
        self.assertFalse(payload['final_response_override'])
        self.assertTrue(payload['content_free'])
        self.assertNotIn('Lis mon agenda demain', repr(payload))

    def test_disabled_turn_returns_local_disabled_noop(self) -> None:
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': False},
            user_msg='Ignore Agenda',
        )

        self.assertFalse(result.enabled)
        self.assertFalse(result.used)
        self.assertEqual(result.status, 'disabled')
        self.assertEqual(result.reason_code, 'agenda_toggle_off')
        self.assertFalse(result.observability_payload['caldav_access'])

    def test_active_runtime_validates_injected_json_agent_without_caldav_when_read_client_missing(self) -> None:
        fake = _FakeModelClient(_valid_payload(intent='RAW INTENT MUST NOT LEAK'))
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            recent_dialogue=({'role': 'assistant', 'content': 'RAW DIALOGUE MUST NOT LEAK'},),
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake,
        )

        self.assertEqual(result.status, agent_runtime.STATUS_ACTIVE_READY)
        self.assertEqual(result.reason_code, agent_runtime.REASON_ACTIVE_VALIDATED)
        self.assertFalse(result.used)
        self.assertIsNone(result.final_response_lock)
        self.assertIsNotNone(result.read_execution_result)
        self.assertEqual(fake.calls, 1)
        payload = result.observability_payload
        encoded = json.dumps(payload, sort_keys=True)
        self.assertEqual(payload['schema_version'], 'frida_agenda_lot5_readonly_v1')
        self.assertTrue(payload['agent_json_validated'])
        self.assertTrue(payload['model_called'])
        self.assertEqual(payload['product_method'], product_methods.METHOD_READ_TODAY)
        self.assertEqual(payload['tool_names'], [product_methods.TOOL_EVENT_QUERY_RANGE])
        self.assertTrue(payload['read_execution_attempted'])
        self.assertEqual(payload['read_execution_status'], 'skipped')
        self.assertEqual(payload['read_execution_reason_code'], 'agenda_readonly_client_unavailable')
        self.assertFalse(payload['caldav_access'])
        self.assertFalse(payload['nextcloud_access'])
        self.assertFalse(payload['secret_access'])
        self.assertFalse(payload['mutation_attempted'])
        self.assertFalse(payload['prompt_lane_injected'])
        self.assertFalse(payload['final_response_override'])
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded)
        self.assertNotIn('RAW INTENT MUST NOT LEAK', encoded)
        self.assertNotIn('RAW DIALOGUE MUST NOT LEAK', encoded)

    def test_active_runtime_executes_readonly_plan_with_injected_client_and_final_response_lock(self) -> None:
        fake_model = _FakeModelClient(_valid_payload(intent='RAW INTENT MUST NOT LEAK'))
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
        )

        self.assertTrue(result.used)
        self.assertEqual(read_client.calls, ['list_calendars', 'query_calendar_events'])
        lock = result.final_response_lock
        self.assertIsNotNone(lock)
        self.assertTrue(lock.ok)
        self.assertIn('Fixture Focus Block', lock.content)
        self.assertIn('09:00-10:00', lock.content)
        meta = lock.to_message_meta()
        self.assertEqual(meta['source'], 'agenda_readonly_response')
        self.assertEqual(meta['agenda_product_method'], product_methods.METHOD_READ_TODAY)
        self.assertEqual(meta['agenda_event_count'], 1)
        self.assertFalse(meta['agenda_caldav_access'])
        self.assertFalse(meta['agenda_mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertTrue(result.observability_payload['final_response_override'])
        self.assertEqual(result.observability_payload['read_execution_status'], 'ok')
        self.assertEqual(result.observability_payload['read_event_count'], 1)
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded_payload)
        self.assertNotIn('RAW INTENT MUST NOT LEAK', encoded_payload)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-event-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_active_runtime_invalid_json_falls_back_cleanly(self) -> None:
        fake = _FakeTextModelClient('{not-json')
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake,
        )

        self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
        self.assertEqual(result.reason_code, agent_contract.REASON_JSON_INVALID)
        self.assertFalse(result.used)
        self.assertFalse(result.observability_payload['agent_json_validated'])

    def test_removed_shadow_and_candidate_modes_are_not_reintroduced(self) -> None:
        for mode in ('shadow', 'candidate'):
            with self.subTest(mode=mode):
                fake = _FakeModelClient(_valid_payload())
                result = chat_runtime.run_agenda_chat_turn(
                    {'agenda_enabled': True},
                    user_msg='Lis mon agenda',
                    settings_override=agent_contract.AgendaAgentSettings(
                        mode=mode,
                        caldav_secret_configured=True,
                    ),
                    agent_model_client=fake,
                )
                self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
                self.assertEqual(result.reason_code, agent_runtime.REASON_MODE_UNSUPPORTED)
                self.assertEqual(fake.calls, 0)


class _FakeModelClient:
    def __init__(self, payload: dict) -> None:
        self.payload = payload
        self.calls = 0

    def complete(self, request, *, settings):
        self.calls += 1
        self.last_request = request
        self.last_settings = settings
        return agent_runtime.AgendaAgentModelResponse(
            status='ok',
            reason_code='fake_ok',
            content=json.dumps(self.payload),
            attempt_count=1,
        )


class _FakeTextModelClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls = 0

    def complete(self, request, *, settings):
        del request, settings
        self.calls += 1
        return agent_runtime.AgendaAgentModelResponse(
            status='ok',
            reason_code='fake_ok',
            content=self.content,
            attempt_count=1,
        )


class _FakeReadClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self._calendar = CalendarSummary(
            local_id='primary',
            display_name='Fixture Primary Calendar',
            permissions=('read',),
            color='#1166aa',
            enabled=True,
            readonly=True,
            family_calendar=False,
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/',
        )
        self._event = CalendarEvent(
            event_id='event-1',
            calendar_id='primary',
            uid='fixture-event-001@example.invalid',
            summary='Fixture Focus Block',
            location='Fixture Location Alpha',
            description='Fixture description, no personal data.',
            start_iso='2026-06-08T09:00:00Z',
            end_iso='2026-06-08T10:00:00Z',
            timezone='UTC',
            etag='fixture-etag-001',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/event-1.ics',
        )

    def list_calendars(self):
        self.calls.append('list_calendars')
        return (self._calendar,)

    def query_calendar_events(self, calendar, *, start_iso, end_iso, timezone_name='UTC'):
        del calendar, start_iso, end_iso, timezone_name
        self.calls.append('query_calendar_events')
        return (self._event,)

    def get_event(self, event):
        del event
        self.calls.append('get_event')
        return self._event


def _valid_payload(**overrides) -> dict:
    payload = {
        'schema_version': agent_contract.SCHEMA_VERSION,
        'product_method': product_methods.METHOD_READ_TODAY,
        'intent': 'read agenda day',
        'calendar_scope': {
            'calendar_ids': ['primary'],
            'family_calendar': False,
            'ambiguity': 'none',
        },
        'time_scope': {
            'kind': 'day',
            'start': '2026-06-08T00:00:00Z',
            'end': '2026-06-09T00:00:00Z',
            'timezone': 'Europe/Paris',
            'ambiguity': 'none',
        },
        'tool_calls': [
            {
                'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                'method': 'GET',
                'params': {
                    'calendar_id': 'primary',
                    'start': '2026-06-08T00:00:00Z',
                    'end': '2026-06-09T00:00:00Z',
                    'timezone': 'Europe/Paris',
                },
                'call_id': 'call-1',
            }
        ],
        'mutation': {
            'requested': False,
            'kind': 'none',
            'confirmation_required': False,
            'confirmation_level': 'none',
            'pending_action_id': '',
        },
        'answer_mode': 'agenda_summary',
        'risk_flags': [],
        'fallback_reason': '',
        'surface_intro': '',
        'surface_outro': '',
    }
    payload.update(overrides)
    return payload


if __name__ == '__main__':
    unittest.main()
