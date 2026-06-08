from __future__ import annotations

import json
import unittest

from agenda import agent_contract, agent_runtime, chat_runtime, product_methods


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
        self.assertEqual(payload['schema_version'], 'frida_agenda_lot4_agent_v1')
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

    def test_active_runtime_validates_injected_json_agent_without_using_chat_response_or_caldav(self) -> None:
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
        self.assertEqual(fake.calls, 1)
        payload = result.observability_payload
        encoded = json.dumps(payload, sort_keys=True)
        self.assertTrue(payload['agent_json_validated'])
        self.assertTrue(payload['model_called'])
        self.assertEqual(payload['product_method'], product_methods.METHOD_READ_TODAY)
        self.assertEqual(payload['tool_names'], [product_methods.TOOL_EVENT_QUERY_RANGE])
        self.assertFalse(payload['caldav_access'])
        self.assertFalse(payload['nextcloud_access'])
        self.assertFalse(payload['secret_access'])
        self.assertFalse(payload['mutation_attempted'])
        self.assertFalse(payload['prompt_lane_injected'])
        self.assertFalse(payload['final_response_override'])
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded)
        self.assertNotIn('RAW INTENT MUST NOT LEAK', encoded)
        self.assertNotIn('RAW DIALOGUE MUST NOT LEAK', encoded)

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
