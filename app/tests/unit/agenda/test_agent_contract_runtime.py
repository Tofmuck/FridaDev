from __future__ import annotations

import json
import unittest

from agenda import agent_openrouter, time_windows
from agenda import agent_contract as contract
from agenda import agent_runtime, product_methods


RAW_USER = 'RAW USER AGENDA REQUEST MUST NOT LEAK'
RAW_QUERY = 'RAW QUERY MUST NOT LEAK'
RAW_SURFACE = 'RAW SURFACE MUST NOT LEAK'
CANONICAL_WINDOWS_PARIS = {
    'today': {
        'start': '2026-06-07T22:00:00Z',
        'end': '2026-06-08T22:00:00Z',
        'timezone': 'Europe/Paris',
        'local_date': '2026-06-08',
    },
    'tomorrow': {
        'start': '2026-06-08T22:00:00Z',
        'end': '2026-06-09T22:00:00Z',
        'timezone': 'Europe/Paris',
        'local_date': '2026-06-09',
    },
}


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

    def test_read_only_methods_require_at_least_one_executable_tool_call(self) -> None:
        validation = contract.validate_agent_payload(_valid_payload(tool_calls=[]))

        self.assertEqual(validation.status, contract.STATUS_REJECTED)
        self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)
        self.assertNotIn('Je ne vois rien', json.dumps(validation.to_observability(), sort_keys=True))

    def test_canonical_time_windows_are_computed_from_frida_timezone(self) -> None:
        windows = time_windows.build_canonical_time_windows(
            now_iso='2026-06-08T10:00:00Z',
            timezone_name='Europe/Paris',
        )

        self.assertEqual(windows['today']['start'], '2026-06-07T22:00:00Z')
        self.assertEqual(windows['today']['end'], '2026-06-08T22:00:00Z')
        self.assertEqual(windows['tomorrow']['start'], '2026-06-08T22:00:00Z')
        self.assertEqual(windows['tomorrow']['end'], '2026-06-09T22:00:00Z')

    def test_agent_payload_includes_canonical_time_windows(self) -> None:
        request = _request(
            settings=contract.AgendaAgentSettings(
                mode=contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            canonical_time_windows=CANONICAL_WINDOWS_PARIS,
        )

        messages = agent_openrouter.build_agenda_agent_messages(request)
        user_payload = json.loads(messages[1]['content'])

        self.assertEqual(user_payload['canonical_time_windows']['today']['start'], '2026-06-07T22:00:00Z')
        self.assertEqual(user_payload['canonical_time_windows']['tomorrow']['end'], '2026-06-09T22:00:00Z')
        self.assertNotIn('RAW USER', messages[0]['content'])

    def test_agent_prompt_instructs_search_events_as_range_then_search(self) -> None:
        request = _request(
            settings=contract.AgendaAgentSettings(
                mode=contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            canonical_time_windows=CANONICAL_WINDOWS_PARIS,
        )

        system_message = agent_openrouter.build_agenda_agent_messages(request)[0]['content']

        self.assertIn('event_query_range', system_message)
        self.assertIn('event_search', system_message)
        self.assertIn('ne mets jamais start, end ou timezone dans les params event_search', system_message)

    def test_search_events_accepts_bounded_range_then_local_search(self) -> None:
        validation = contract.validate_agent_payload(
            _valid_payload(
                product_method=product_methods.METHOD_SEARCH_EVENTS,
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': {
                            'start': '2026-06-08T00:00:00Z',
                            'end': '2026-06-09T00:00:00Z',
                            'timezone': 'Europe/Paris',
                        },
                        'call_id': 'range-1',
                    },
                    {
                        'tool_name': product_methods.TOOL_EVENT_SEARCH,
                        'method': 'GET',
                        'params': {'query': 'docteur demain', 'limit': 5},
                        'call_id': 'search-1',
                    },
                ],
            )
        )

        self.assertEqual(validation.status, contract.STATUS_VALIDATED)
        self.assertEqual(
            validation.tool_names,
            (product_methods.TOOL_EVENT_QUERY_RANGE, product_methods.TOOL_EVENT_SEARCH),
        )

    def test_openrouter_tool_params_schema_is_strict_provider_compatible(self) -> None:
        response_format = agent_openrouter.build_agenda_agent_response_format(max_tool_calls=4)
        params_schema = (
            response_format['json_schema']['schema']['properties']['tool_calls']['items']
            ['properties']['params']
        )

        self.assertEqual(params_schema['required'], sorted(params_schema['properties'].keys()))
        for field_schema in params_schema['properties'].values():
            field_types = field_schema.get('type')
            self.assertIsInstance(field_types, list)
            self.assertIn('null', field_types)

    def test_nullable_openrouter_tool_params_are_ignored_by_validator(self) -> None:
        nullable_params = {
            'calendar_id': None,
            'event_id': None,
            'start': '2026-06-08T00:00:00Z',
            'end': '2026-06-09T00:00:00Z',
            'timezone': 'Europe/Paris',
            'query': None,
            'max_days': None,
            'limit': None,
        }

        validation = contract.validate_agent_payload(
            _valid_payload(
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': nullable_params,
                        'call_id': 'call-1',
                    }
                ],
            )
        )

        self.assertEqual(validation.status, contract.STATUS_VALIDATED)
        self.assertEqual(validation.reason_code, contract.REASON_VALIDATED)
        self.assertEqual(
            validation.plan.tool_calls[0].params,
            {
                'start': '2026-06-08T00:00:00Z',
                'end': '2026-06-09T00:00:00Z',
                'timezone': 'Europe/Paris',
            },
        )

    def test_read_today_requires_canonical_today_window_when_context_is_present(self) -> None:
        canonical_payload = _payload_with_window(
            product_method=product_methods.METHOD_READ_TODAY,
            start='2026-06-07T22:00:00Z',
            end='2026-06-08T22:00:00Z',
        )
        raw_utc_payload = _payload_with_window(
            product_method=product_methods.METHOD_READ_TODAY,
            start='2026-06-08T00:00:00Z',
            end='2026-06-09T00:00:00Z',
        )

        self.assertEqual(
            contract.validate_agent_payload(
                canonical_payload,
                canonical_time_windows=CANONICAL_WINDOWS_PARIS,
            ).status,
            contract.STATUS_VALIDATED,
        )
        rejected = contract.validate_agent_payload(
            raw_utc_payload,
            canonical_time_windows=CANONICAL_WINDOWS_PARIS,
        )
        encoded = json.dumps(rejected.to_observability(), sort_keys=True)
        self.assertEqual(rejected.status, contract.STATUS_REJECTED)
        self.assertEqual(rejected.reason_code, contract.REASON_TIME_WINDOW_MISMATCH)
        self.assertNotIn('2026-06-08T00:00:00Z', encoded)

    def test_read_tomorrow_requires_canonical_tomorrow_window_when_context_is_present(self) -> None:
        canonical_payload = _payload_with_window(
            product_method=product_methods.METHOD_READ_TOMORROW,
            start='2026-06-08T22:00:00Z',
            end='2026-06-09T22:00:00Z',
        )
        raw_utc_payload = _payload_with_window(
            product_method=product_methods.METHOD_READ_TOMORROW,
            start='2026-06-09T00:00:00Z',
            end='2026-06-10T00:00:00Z',
        )

        self.assertEqual(
            contract.validate_agent_payload(
                canonical_payload,
                canonical_time_windows=CANONICAL_WINDOWS_PARIS,
            ).status,
            contract.STATUS_VALIDATED,
        )
        rejected = contract.validate_agent_payload(
            raw_utc_payload,
            canonical_time_windows=CANONICAL_WINDOWS_PARIS,
        )
        encoded = json.dumps(rejected.to_observability(), sort_keys=True)
        self.assertEqual(rejected.status, contract.STATUS_REJECTED)
        self.assertEqual(rejected.reason_code, contract.REASON_TIME_WINDOW_MISMATCH)
        self.assertNotIn('2026-06-09T00:00:00Z', encoded)

    def test_tool_param_values_reject_raw_caldav_uid_and_secret_shapes_content_free(self) -> None:
        raw_url = 'https://cloud.frida-system.fr/remote.php/dav/calendars/tof/Famille/'
        raw_path = '/remote.php/dav/calendars/tof/Famille/'
        raw_uid = 'abc123@example.invalid'
        raw_query = 'Authorization bearer token should-not-leak'
        cases = [
            _valid_payload(
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': {
                            'calendar_id': raw_url,
                            'start': '2026-06-08T00:00:00Z',
                            'end': '2026-06-09T00:00:00Z',
                            'timezone': 'Europe/Paris',
                        },
                        'call_id': 'call-1',
                    }
                ],
            ),
            _valid_payload(
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': {
                            'calendar_id': raw_path,
                            'start': '2026-06-08T00:00:00Z',
                            'end': '2026-06-09T00:00:00Z',
                            'timezone': 'Europe/Paris',
                        },
                        'call_id': 'call-1',
                    }
                ],
            ),
            _valid_payload(
                product_method=product_methods.METHOD_EVENT_DETAILS,
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': raw_uid},
                        'call_id': 'call-1',
                    }
                ],
            ),
            _valid_payload(
                product_method=product_methods.METHOD_SEARCH_EVENTS,
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_SEARCH,
                        'method': 'GET',
                        'params': {'query': raw_query, 'limit': 5},
                        'call_id': 'call-1',
                    }
                ],
            ),
        ]
        for payload in cases:
            with self.subTest(payload=payload['tool_calls'][0]['params']):
                validation = contract.validate_agent_payload(payload)
                observation = json.dumps(validation.to_observability(), sort_keys=True)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)
                self.assertNotIn(raw_url, observation)
                self.assertNotIn(raw_path, observation)
                self.assertNotIn(raw_uid, observation)
                self.assertNotIn(raw_query, observation)

    def test_tool_param_values_reject_case_insensitive_technical_markers_content_free(self) -> None:
        raw_ics = 'begin:VEVENT summary: secret appointment'
        raw_summary = 'summary: rendez-vous'
        raw_auth = 'authorization bearer token'
        cases = (raw_ics, raw_summary, raw_auth)
        for raw_query in cases:
            with self.subTest(raw_query=raw_query):
                validation = contract.validate_agent_payload(
                    _valid_payload(
                        product_method=product_methods.METHOD_SEARCH_EVENTS,
                        tool_calls=[
                            {
                                'tool_name': product_methods.TOOL_EVENT_SEARCH,
                                'method': 'GET',
                                'params': {'query': raw_query, 'limit': 5},
                                'call_id': 'call-1',
                            }
                        ],
                    )
                )
                observation = json.dumps(validation.to_observability(), sort_keys=True)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)
                self.assertNotIn(raw_query, observation)

    def test_tool_param_values_reject_remaining_ics_markers_content_free(self) -> None:
        cases = (
            'rrule:FREQ=DAILY',
            'dtstart:20260608T100000Z',
            'last-modified:20260608T100000Z',
        )
        for raw_query in cases:
            with self.subTest(raw_query=raw_query):
                validation = contract.validate_agent_payload(
                    _valid_payload(
                        product_method=product_methods.METHOD_SEARCH_EVENTS,
                        tool_calls=[
                            {
                                'tool_name': product_methods.TOOL_EVENT_SEARCH,
                                'method': 'GET',
                                'params': {'query': raw_query, 'limit': 5},
                                'call_id': 'call-1',
                            }
                        ],
                    )
                )
                observation = json.dumps(validation.to_observability(), sort_keys=True)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)
                self.assertNotIn(raw_query, observation)

    def test_event_id_rejects_uid_like_values_but_keeps_local_short_ids(self) -> None:
        for raw_event_id in (
            'uid:abc123',
            'UID:abc123',
            'uid=abc123',
            'recurrence-id:abc123',
            'rrule:abc123',
        ):
            with self.subTest(raw_event_id=raw_event_id):
                validation = contract.validate_agent_payload(
                    _valid_payload(
                        product_method=product_methods.METHOD_EVENT_DETAILS,
                        tool_calls=[
                            {
                                'tool_name': product_methods.TOOL_EVENT_GET,
                                'method': 'GET',
                                'params': {'event_id': raw_event_id},
                                'call_id': 'call-1',
                            }
                        ],
                    )
                )
                observation = json.dumps(validation.to_observability(), sort_keys=True)
                self.assertEqual(validation.status, contract.STATUS_REJECTED)
                self.assertEqual(validation.reason_code, contract.REASON_TOOL_NOT_EXECUTABLE)
                self.assertNotIn(raw_event_id, observation)

        self.assertEqual(_event_details_validation('event-1').status, contract.STATUS_VALIDATED)

    def test_ordinary_vernacular_event_search_query_remains_valid(self) -> None:
        for query in ('docteur demain', 'rendez-vous docteur', 'réunion association'):
            with self.subTest(query=query):
                validation = contract.validate_agent_payload(
                    _valid_payload(
                        product_method=product_methods.METHOD_SEARCH_EVENTS,
                        tool_calls=[
                            {
                                'tool_name': product_methods.TOOL_EVENT_SEARCH,
                                'method': 'GET',
                                'params': {'query': query, 'limit': 5},
                                'call_id': 'call-1',
                            }
                        ],
                    )
                )
                self.assertEqual(validation.status, contract.STATUS_VALIDATED)

    def test_local_short_event_id_remains_valid_for_known_state_references(self) -> None:
        validation = _event_details_validation('event-1')

        self.assertEqual(validation.status, contract.STATUS_VALIDATED)
        self.assertEqual(validation.reason_code, contract.REASON_VALIDATED)

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

    def test_read_only_methods_reject_incoherent_mutation_kind_even_when_not_requested(self) -> None:
        incoherent = _valid_payload(
            mutation={
                'requested': False,
                'kind': 'create',
                'confirmation_required': False,
                'confirmation_level': 'none',
                'pending_action_id': '',
            }
        )
        validation = contract.validate_agent_payload(incoherent)

        self.assertEqual(validation.status, contract.STATUS_REJECTED)
        self.assertEqual(validation.reason_code, contract.REASON_MUTATION_METHOD_MISMATCH)
        self.assertNotIn('create', json.dumps(validation.to_observability(), sort_keys=True))
        self.assertEqual(contract.validate_agent_payload(_valid_payload()).status, contract.STATUS_VALIDATED)

    def test_propose_and_confirm_mutation_methods_keep_strict_confirmation_contract(self) -> None:
        proposed_create = _valid_payload(
            product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
            tool_calls=[],
            draft=_create_draft(),
            mutation={
                'requested': False,
                'kind': 'create',
                'confirmation_required': False,
                'confirmation_level': 'none',
                'pending_action_id': '',
            },
            answer_mode='proposal',
        )
        confirmed_create = _valid_payload(
            product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
            tool_calls=[],
            mutation={
                'requested': True,
                'kind': 'create',
                'confirmation_required': True,
                'confirmation_level': 'simple',
                'pending_action_id': 'pending-create-1',
            },
            answer_mode='mutation_pending_confirmation',
        )
        missing_pending = {
            **confirmed_create,
            'mutation': {**confirmed_create['mutation'], 'pending_action_id': ''},
        }

        self.assertEqual(contract.validate_agent_payload(proposed_create).status, contract.STATUS_VALIDATED)
        self.assertEqual(contract.validate_agent_payload(confirmed_create).status, contract.STATUS_VALIDATED)
        self.assertEqual(
            contract.validate_agent_payload(missing_pending).reason_code,
            contract.REASON_MUTATION_REQUIRES_CONFIRMATION,
        )

    def test_proposed_create_requires_structured_draft_and_observes_it_content_free(self) -> None:
        missing = contract.validate_agent_payload(
            _valid_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                tool_calls=[],
                mutation={
                    'requested': False,
                    'kind': 'create',
                    'confirmation_required': False,
                    'confirmation_level': 'none',
                    'pending_action_id': '',
                },
                answer_mode='proposal',
            )
        )
        self.assertEqual(missing.status, contract.STATUS_REJECTED)
        self.assertEqual(missing.reason_code, contract.REASON_DRAFT_INVALID)

        raw_title = 'Fixture Agenda Proposal'
        valid = contract.validate_agent_payload(
            _valid_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                tool_calls=[],
                draft=_create_draft(title=raw_title),
                mutation={
                    'requested': False,
                    'kind': 'create',
                    'confirmation_required': False,
                    'confirmation_level': 'none',
                    'pending_action_id': '',
                },
                answer_mode='proposal',
            )
        )
        observed = json.dumps(valid.to_observability(), sort_keys=True)
        self.assertEqual(valid.status, contract.STATUS_VALIDATED)
        self.assertNotIn(raw_title, observed)
        self.assertNotIn('Fixture Room', observed)

    def test_cancel_pending_action_accepts_only_safe_pending_id_without_mutation(self) -> None:
        valid_cancel = _valid_payload(
            product_method=product_methods.METHOD_CANCEL_PENDING_AGENDA_ACTION,
            tool_calls=[],
            mutation={
                'requested': False,
                'kind': 'none',
                'confirmation_required': False,
                'confirmation_level': 'none',
                'pending_action_id': 'agenda-pending-create-1',
            },
            answer_mode='mutation_refused',
        )
        missing_pending = {
            **valid_cancel,
            'mutation': {**valid_cancel['mutation'], 'pending_action_id': ''},
        }
        unsafe_pending = {
            **valid_cancel,
            'mutation': {**valid_cancel['mutation'], 'pending_action_id': 'uid:abc123'},
        }
        incoherent_cancel = {
            **valid_cancel,
            'mutation': {**valid_cancel['mutation'], 'kind': 'delete', 'confirmation_required': True},
        }

        self.assertEqual(contract.validate_agent_payload(valid_cancel).status, contract.STATUS_VALIDATED)
        self.assertEqual(
            contract.validate_agent_payload(missing_pending).reason_code,
            contract.REASON_MUTATION_METHOD_MISMATCH,
        )
        self.assertEqual(contract.validate_agent_payload(unsafe_pending).reason_code, contract.REASON_SCHEMA_INVALID)
        self.assertEqual(
            contract.validate_agent_payload(incoherent_cancel).reason_code,
            contract.REASON_MUTATION_METHOD_MISMATCH,
        )

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


def _request(
    *,
    settings: contract.AgendaAgentSettings,
    canonical_time_windows=None,
) -> contract.AgendaAgentRequest:
    return contract.AgendaAgentRequest(
        user_message=RAW_USER,
        recent_dialogue=({'role': 'assistant', 'content': 'RAW DIALOGUE MUST NOT LEAK'},),
        now_iso='2026-06-08T12:00:00Z',
        timezone='Europe/Paris',
        canonical_time_windows=canonical_time_windows,
        settings=settings,
    )


def _event_details_validation(event_id: str):
    return contract.validate_agent_payload(
        _valid_payload(
            product_method=product_methods.METHOD_EVENT_DETAILS,
            tool_calls=[
                {
                    'tool_name': product_methods.TOOL_EVENT_GET,
                    'method': 'GET',
                    'params': {'event_id': event_id},
                    'call_id': 'call-1',
                }
            ],
        )
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
        'draft': _empty_draft(),
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


def _empty_draft() -> dict:
    return {
        'title': None,
        'location': None,
        'description': None,
        'calendar_id': None,
        'start': None,
        'end': None,
        'timezone': None,
        'all_day': None,
        'target_event_id': None,
        'change_summary': None,
    }


def _create_draft(*, title: str = 'Fixture Agenda Proposal') -> dict:
    draft = _empty_draft()
    draft.update(
        {
            'title': title,
            'location': 'Fixture Room',
            'description': 'Synthetic pending draft.',
            'calendar_id': 'primary',
            'start': '2026-06-09T08:00:00Z',
            'end': '2026-06-09T09:00:00Z',
            'timezone': 'Europe/Paris',
            'all_day': False,
        }
    )
    return draft


def _payload_with_window(*, product_method: str, start: str, end: str) -> dict:
    return _valid_payload(
        product_method=product_method,
        time_scope={
            'kind': 'day',
            'start': start,
            'end': end,
            'timezone': 'Europe/Paris',
            'ambiguity': 'none',
        },
        tool_calls=[
            {
                'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                'method': 'GET',
                'params': {
                    'calendar_id': 'primary',
                    'start': start,
                    'end': end,
                    'timezone': 'Europe/Paris',
                },
                'call_id': 'call-1',
            }
        ],
    )


if __name__ == '__main__':
    unittest.main()
