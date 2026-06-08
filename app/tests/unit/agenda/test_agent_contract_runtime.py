from __future__ import annotations

import json
import unittest

from agenda import agent_contract as contract
from agenda import agent_runtime, product_methods


RAW_USER = 'RAW USER AGENDA REQUEST MUST NOT LEAK'
RAW_QUERY = 'RAW QUERY MUST NOT LEAK'
RAW_SURFACE = 'RAW SURFACE MUST NOT LEAK'


class AgendaAgentContractRuntimeTests(unittest.TestCase):
    def test_valid_read_plan_is_accepted_without_exposing_raw_content_in_observation(self) -> None:
        payload = _valid_payload(intent=RAW_USER, surface_intro=RAW_SURFACE)
        validation = contract.validate_agent_payload(payload)

        self.assertEqual(validation.status, contract.STATUS_VALIDATED)
        self.assertEqual(validation.reason_code, contract.REASON_VALIDATED)
        observed = validation.to_observability()
        encoded = json.dumps(observed, sort_keys=True)
        self.assertIn(product_methods.TOOL_EVENT_QUERY_RANGE, observed['tool_names'])
        self.assertNotIn(RAW_USER, encoded)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_SURFACE, encoded)

    def test_invalid_json_absent_free_text_and_truncated_outputs_are_rejected_cleanly(self) -> None:
        cases = [
            ('', '', contract.REASON_JSON_ABSENT),
            ('voici un plan', '', contract.REASON_JSON_FREE_TEXT),
            ('{bad-json', '', contract.REASON_JSON_INVALID),
            (json.dumps(_valid_payload()), 'length', contract.REASON_JSON_TRUNCATED),
        ]
        for raw, finish_reason, reason in cases:
            with self.subTest(reason=reason):
                validation = contract.parse_and_validate_agent_json(raw, finish_reason=finish_reason)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, reason)
                if raw:
                    self.assertNotIn(raw, json.dumps(validation.to_observability(), sort_keys=True))

    def test_schema_surface_method_tool_and_method_guards_are_strict(self) -> None:
        base = _valid_payload()
        cases = [
            ({**base, 'schema_version': 'other'}, contract.REASON_SCHEMA_VERSION),
            ({**base, 'surface_intro': None}, contract.REASON_SCHEMA_INVALID),
            ({**base, 'surface_outro': None}, contract.REASON_SCHEMA_INVALID),
            ({**base, 'product_method': 'unknown_method'}, contract.REASON_PRODUCT_METHOD_UNKNOWN),
            (
                {
                    **base,
                    'tool_calls': [
                        {
                            'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                            'method': 'POST',
                            'params': {'start': '2026-06-08T00:00:00Z', 'end': '2026-06-09T00:00:00Z'},
                            'call_id': 'call-1',
                        }
                    ],
                },
                contract.REASON_METHOD_FORBIDDEN,
            ),
            (
                {**base, 'tool_calls': [{'tool_name': 'made_up_tool', 'method': 'GET', 'params': {}, 'call_id': ''}]},
                contract.REASON_TOOL_UNKNOWN,
            ),
            (
                {
                    **base,
                    'tool_calls': [
                        {
                            'tool_name': product_methods.TOOL_EVENT_GET,
                            'method': 'GET',
                            'params': {'event_id': 'event-1'},
                            'call_id': '',
                        }
                    ],
                },
                contract.REASON_TOOL_FORBIDDEN,
            ),
            (
                {
                    **base,
                    'tool_calls': [
                        {
                            'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                            'method': 'GET',
                            'params': {
                                'start': '2026-06-08T00:00:00Z',
                                'end': '2026-06-09T00:00:00Z',
                                'caldav_path': '/remote.php/dav/raw',
                            },
                            'call_id': '',
                        }
                    ],
                },
                contract.REASON_TOOL_NOT_EXECUTABLE,
            ),
        ]
        for payload, reason in cases:
            with self.subTest(reason=reason):
                validation = contract.validate_agent_payload(payload)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, reason)

    def test_mutation_and_delete_payloads_require_human_confirmation_contract(self) -> None:
        delete_without_reinforced = _valid_payload(
            product_method=product_methods.METHOD_PROPOSE_DELETE_EVENT,
            tool_calls=[],
            mutation={
                'requested': False,
                'kind': 'delete',
                'confirmation_required': True,
                'confirmation_level': 'simple',
                'pending_action_id': '',
            },
            answer_mode='mutation_refused',
        )
        self.assertEqual(
            contract.validate_agent_payload(delete_without_reinforced).reason_code,
            contract.REASON_DELETION_REQUIRES_REINFORCED_CONFIRMATION,
        )

        delete_refusal = {
            **delete_without_reinforced,
            'mutation': {
                **delete_without_reinforced['mutation'],
                'confirmation_level': 'reinforced',
            },
        }
        self.assertEqual(contract.validate_agent_payload(delete_refusal).status, contract.STATUS_VALIDATED)

        confirmed_delete = _valid_payload(
            product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
            tool_calls=[],
            calendar_scope={
                'calendar_ids': ['family'],
                'family_calendar': True,
                'ambiguity': 'none',
            },
            mutation={
                'requested': True,
                'kind': 'delete',
                'confirmation_required': True,
                'confirmation_level': 'reinforced',
                'pending_action_id': 'pending-delete-1',
            },
            risk_flags=['family_calendar'],
            answer_mode='mutation_pending_confirmation',
        )
        self.assertEqual(contract.validate_agent_payload(confirmed_delete).status, contract.STATUS_VALIDATED)

    def test_agent_runtime_off_active_invalid_and_secret_guards(self) -> None:
        fake = _FakeModelClient(_valid_payload())
        off_result = agent_runtime.AgendaJsonAgent(fake).run(
            _request(settings=contract.AgendaAgentSettings(mode=contract.MODE_OFF))
        )
        self.assertEqual(off_result.reason_code, agent_runtime.REASON_MODE_OFF)
        self.assertEqual(fake.calls, 0)

        unsupported = agent_runtime.AgendaJsonAgent(fake).run(
            _request(settings=contract.AgendaAgentSettings(mode='shadow', caldav_secret_configured=True))
        )
        self.assertEqual(unsupported.reason_code, agent_runtime.REASON_MODE_UNSUPPORTED)
        self.assertEqual(fake.calls, 0)

        missing_secret = agent_runtime.AgendaJsonAgent(fake).run(
            _request(settings=contract.AgendaAgentSettings(mode=contract.MODE_ACTIVE))
        )
        self.assertEqual(missing_secret.reason_code, agent_runtime.REASON_SECRET_NOT_CONFIGURED)
        self.assertEqual(fake.calls, 0)

        active = agent_runtime.AgendaJsonAgent(fake).run(
            _request(settings=contract.AgendaAgentSettings(mode=contract.MODE_ACTIVE, caldav_secret_configured=True))
        )
        self.assertEqual(active.status, agent_runtime.STATUS_ACTIVE_READY)
        self.assertEqual(active.reason_code, agent_runtime.REASON_ACTIVE_VALIDATED)
        self.assertTrue(active.model_called)
        self.assertFalse(active.used_for_response)
        self.assertEqual(fake.calls, 1)
        observed = active.to_observability()
        encoded = json.dumps(observed, sort_keys=True)
        self.assertFalse(observed['caldav_access'])
        self.assertFalse(observed['nextcloud_access'])
        self.assertFalse(observed['secret_access'])
        self.assertFalse(observed['mutation_attempted'])
        self.assertNotIn(RAW_USER, encoded)
        self.assertNotIn(RAW_QUERY, encoded)


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


def _request(*, settings: contract.AgendaAgentSettings) -> contract.AgendaAgentRequest:
    return contract.AgendaAgentRequest(
        user_message=RAW_USER,
        recent_dialogue=({'role': 'assistant', 'content': 'RAW DIALOGUE MUST NOT LEAK'},),
        now_iso='2026-06-08T12:00:00Z',
        timezone='Europe/Paris',
        settings=settings,
    )


def _valid_payload(**overrides) -> dict:
    payload = {
        'schema_version': contract.SCHEMA_VERSION,
        'product_method': product_methods.METHOD_READ_TODAY,
        'intent': 'read requested agenda range',
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
