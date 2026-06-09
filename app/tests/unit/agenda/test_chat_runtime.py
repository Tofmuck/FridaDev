from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from agenda import (
    agent_contract,
    agent_runtime,
    caldav_write_client,
    chat_runtime,
    pending_store,
    product_methods,
    proposal_execution,
    read_execution,
    response_rendering,
    write_execution,
)
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
        self.assertNotIn('07:00-08:00', lock.content)
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

    def test_active_runtime_rejects_raw_utc_day_when_frida_timezone_requires_canonical_window(self) -> None:
        fake_model = _FakeModelClient(_valid_payload(intent='RAW INTENT MUST NOT LEAK'))
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            now_iso='2026-06-08T10:00:00Z',
            config_module=SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris'),
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
        )

        self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
        self.assertEqual(result.reason_code, agent_contract.REASON_TIME_WINDOW_MISMATCH)
        self.assertFalse(result.used)
        self.assertIsNone(result.read_execution_result)
        self.assertEqual(read_client.calls, [])
        self.assertEqual(fake_model.last_request.canonical_time_windows['today']['start'], '2026-06-07T22:00:00Z')
        self.assertEqual(fake_model.last_request.canonical_time_windows['tomorrow']['end'], '2026-06-09T22:00:00Z')
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('2026-06-08T00:00:00Z', encoded_payload)
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded_payload)

    def test_active_runtime_uses_canonical_window_for_all_day_events(self) -> None:
        fake_model = _FakeModelClient(
            _payload_with_window(
                product_method=product_methods.METHOD_READ_TODAY,
                start='2026-06-07T22:00:00Z',
                end='2026-06-08T22:00:00Z',
            )
        )
        read_client = _AllDayReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            now_iso='2026-06-08T10:00:00Z',
            config_module=SimpleNamespace(FRIDA_TIMEZONE='Europe/Paris'),
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
        )

        self.assertTrue(result.used)
        self.assertEqual(read_client.query_ranges, [('2026-06-07T22:00:00Z', '2026-06-08T22:00:00Z', 'Europe/Paris')])
        self.assertIn('Toute la journee', result.final_response_lock.content)
        self.assertNotIn('02:00-02:00', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture All Day Block', encoded_payload)

    def test_active_runtime_rejects_read_plan_without_tools_before_empty_agenda_answer(self) -> None:
        fake_model = _FakeModelClient(_valid_payload(tool_calls=[]))
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda',
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
        )

        self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
        self.assertEqual(result.reason_code, agent_contract.REASON_TOOL_NOT_EXECUTABLE)
        self.assertFalse(result.used)
        self.assertIsNone(result.final_response_lock)
        self.assertIsNone(result.read_execution_result)
        self.assertEqual(read_client.calls, [])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertFalse(result.observability_payload['final_response_override'])
        self.assertFalse(result.observability_payload['secret_access'])
        self.assertNotIn('Je ne vois rien', encoded_payload)

    def test_read_execution_defense_in_depth_rejects_read_plan_without_tools(self) -> None:
        plan = agent_contract.AgendaAgentPlan(
            product_method=product_methods.METHOD_READ_TODAY,
            intent='read agenda',
            calendar_scope={'calendar_ids': ['primary'], 'family_calendar': False, 'ambiguity': 'none'},
            time_scope={
                'kind': 'day',
                'start': '2026-06-08T00:00:00Z',
                'end': '2026-06-09T00:00:00Z',
                'timezone': 'Europe/Paris',
                'ambiguity': 'none',
            },
            tool_calls=(),
            draft=_empty_draft(),
            mutation={
                'requested': False,
                'kind': 'none',
                'confirmation_required': False,
                'confirmation_level': 'none',
                'pending_action_id': '',
            },
            answer_mode='agenda_summary',
            risk_flags=(),
            fallback_reason='',
            surface_intro='',
            surface_outro='',
        )
        read_client = _FakeReadClient()

        execution = read_execution.execute_readonly_plan(plan, client=read_client)

        self.assertEqual(execution.status, 'skipped')
        self.assertEqual(execution.reason_code, 'agenda_readonly_no_tool_calls')
        self.assertEqual(read_client.calls, [])
        self.assertIsNone(response_rendering.build_final_response_lock(plan=plan, execution_result=execution))

    def test_active_runtime_does_not_resolve_secret_for_clarification_plan(self) -> None:
        fake_model = _FakeModelClient(
            _valid_payload(
                product_method=product_methods.METHOD_CLARIFY_AGENDA_REQUEST,
                tool_calls=[],
                answer_mode='clarify',
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Quelle date ?',
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
        )

        self.assertEqual(result.status, agent_runtime.STATUS_ACTIVE_READY)
        self.assertEqual(result.read_execution_result.reason_code, 'agenda_readonly_method_not_read')
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertFalse(result.used)
        self.assertIsNone(result.final_response_lock)
        self.assertFalse(result.observability_payload['secret_access'])
        self.assertFalse(result.observability_payload['caldav_access'])

    def test_active_runtime_marks_secret_access_only_when_secret_is_resolved(self) -> None:
        fake_model = _FakeModelClient(
            _valid_payload(
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': {
                            'start': '2026-06-08T00:00:00Z',
                            'end': '2026-06-09T00:00:00Z',
                            'timezone': 'Europe/Paris',
                        },
                        'call_id': 'call-1',
                    }
                ]
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda',
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
        )

        self.assertTrue(result.used)
        self.assertEqual(runtime_settings.secret_reads, 1)
        self.assertEqual([call['method'] for call in requests_module.calls], ['PROPFIND', 'REPORT'])
        self.assertTrue(result.observability_payload['secret_access'])
        self.assertTrue(result.observability_payload['caldav_access'])
        self.assertTrue(result.observability_payload['nextcloud_access'])
        self.assertIn('09:00-10:00', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('fixture-secret-value', encoded_payload)
        self.assertNotIn('Authorization', encoded_payload)

    def test_active_runtime_records_attempted_read_tool_and_error_class_on_caldav_error(self) -> None:
        fake_model = _FakeModelClient(
            _valid_payload(
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_QUERY_RANGE,
                        'method': 'GET',
                        'params': {
                            'start': '2026-06-08T00:00:00Z',
                            'end': '2026-06-09T00:00:00Z',
                            'timezone': 'Europe/Paris',
                        },
                        'call_id': 'call-1',
                    }
                ]
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _UnauthorizedRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Lis mon agenda',
            now_iso='2026-06-08T00:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
        )

        self.assertFalse(result.used)
        self.assertEqual(result.observability_payload['read_execution_status'], 'error')
        self.assertEqual(result.observability_payload['read_execution_reason_code'], 'caldav_unauthorized')
        self.assertEqual(result.observability_payload['read_tool_count'], 1)
        self.assertEqual(result.observability_payload['read_tool_names'], [product_methods.TOOL_EVENT_QUERY_RANGE])
        self.assertEqual(result.observability_payload['error_class'], 'CalDavReadError')
        self.assertTrue(result.observability_payload['caldav_access'])
        self.assertTrue(result.observability_payload['nextcloud_access'])
        self.assertTrue(result.observability_payload['secret_access'])
        self.assertFalse(result.observability_payload['final_response_override'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('fixture-secret-value', encoded_payload)
        self.assertNotIn('Authorization', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_active_runtime_executes_search_events_as_bounded_range_then_local_search(self) -> None:
        fake_model = _FakeModelClient(
            _valid_payload(
                product_method=product_methods.METHOD_SEARCH_EVENTS,
                answer_mode='agenda_summary',
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
                        'params': {
                            'query': 'Focus',
                            'limit': 5,
                        },
                        'call_id': 'search-1',
                    },
                ],
            )
        )
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Cherche focus dans mon agenda',
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
        self.assertEqual(result.observability_payload['read_execution_status'], 'ok')
        self.assertEqual(result.observability_payload['read_tool_count'], 2)
        self.assertEqual(
            result.observability_payload['read_tool_names'],
            [product_methods.TOOL_EVENT_QUERY_RANGE, product_methods.TOOL_EVENT_SEARCH],
        )
        self.assertIn("J'ai trouve un evenement correspondant", result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Focus', encoded_payload)
        self.assertNotIn('Fixture Focus Block', encoded_payload)

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

    def test_propose_create_creates_pending_action_without_caldav_or_secret_access(self) -> None:
        raw_intent = 'RAW EVENT DETAILS MUST NOT LEAK'
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                intent=raw_intent,
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-create-1',
        )

        self.assertTrue(result.used)
        self.assertIsNone(result.read_execution_result)
        self.assertIsNotNone(result.proposal_execution_result)
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_CREATED)
        self.assertEqual(result.proposal_execution_result.operation, 'create')
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertEqual(read_client.calls, [])
        self.assertEqual(len(result.pending_state.actions), 1)
        action = result.pending_state.actions[0]
        self.assertEqual(action.pending_action_id, 'agenda-pending-create-1')
        self.assertEqual(action.operation, 'create')
        self.assertEqual(action.confirmation_level, 'simple')
        lock = result.final_response_lock
        self.assertIn('Fixture Agenda Proposal', lock.content)
        self.assertIn('Fixture Room', lock.content)
        self.assertIn('Reference de confirmation : agenda-pending-create-1', lock.content)
        self.assertIn('Confirme-moi', lock.content)
        self.assertNotIn("J'ai ajoute", lock.content)
        meta = lock.to_message_meta()
        self.assertEqual(meta['agenda_pending_action_id'], 'agenda-pending-create-1')
        self.assertEqual(meta['agenda_operation'], 'create')
        self.assertFalse(meta['agenda_mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertEqual(result.observability_payload['schema_version'], 'frida_agenda_lot6_pending_v1')
        self.assertFalse(result.observability_payload['caldav_access'])
        self.assertFalse(result.observability_payload['nextcloud_access'])
        self.assertFalse(result.observability_payload['secret_access'])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertTrue(result.observability_payload['final_response_override'])
        self.assertNotIn('fixture-secret-value', encoded_payload)
        self.assertNotIn(raw_intent, encoded_payload)
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded_payload)
        self.assertNotIn('Fixture Agenda Proposal', encoded_payload)
        self.assertNotIn('Fixture Room', encoded_payload)
        self.assertNotIn('Synthetic pending draft', encoded_payload)

    def test_propose_create_family_calendar_from_agent_scope_requires_reinforced_pending_action(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                confirmation_level='reinforced',
                calendar_scope={
                    'calendar_ids': ['family'],
                    'family_calendar': True,
                    'ambiguity': 'none',
                },
                risk_flags=['family_calendar'],
                draft={
                    **_default_proposal_draft('create'),
                    'calendar_id': 'family',
                },
            )
        )

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute ca au calendrier familial',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            pending_id_factory=lambda: 'agenda-pending-family-create-json',
        )

        self.assertTrue(result.used)
        action = result.pending_state.actions[0]
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_REINFORCED)
        self.assertIn('family_calendar', action.risk_flags)
        self.assertIn('partage ou familial', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Agenda Proposal', encoded_payload)
        self.assertNotIn('Fixture Room', encoded_payload)

    def test_propose_create_family_calendar_from_known_calendar_summary_upgrades_confirmation(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                confirmation_level='simple',
            )
        )
        read_client = _FakeReadClient(family_calendar=True)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute cet evenement',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-family-create-known-calendar',
        )

        self.assertTrue(result.used)
        action = result.pending_state.actions[0]
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_REINFORCED)
        self.assertIn('family_calendar', action.risk_flags)
        self.assertIn('partage ou familial', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['caldav_access'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Agenda Proposal', encoded_payload)
        self.assertNotIn('Fixture Room', encoded_payload)

    def test_propose_create_unknown_calendar_scope_without_read_client_is_fail_closed_reinforced(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                confirmation_level='simple',
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute cet evenement',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
            pending_id_factory=lambda: 'agenda-pending-create-unknown-no-client',
        )

        self.assertTrue(result.used)
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertEqual(requests_module.calls, [])
        action = result.pending_state.actions[0]
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_REINFORCED)
        self.assertIn('calendar_scope_unverified', action.risk_flags)
        self.assertNotIn('family_calendar', action.risk_flags)
        self.assertIn('type de ce calendrier', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['mutation_attempted'])

    def test_propose_create_unclassified_calendar_summary_is_fail_closed_reinforced(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                confirmation_level='simple',
            )
        )
        read_client = _FakeReadClient(family_calendar=False, family_calendar_classification='unknown')

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute cet evenement',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-create-unclassified-calendar',
        )

        self.assertTrue(result.used)
        action = result.pending_state.actions[0]
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_REINFORCED)
        self.assertIn('calendar_scope_unverified', action.risk_flags)
        self.assertNotIn('family_calendar', action.risk_flags)
        self.assertFalse(result.observability_payload['caldav_access'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Agenda Proposal', encoded_payload)

    def test_propose_create_explicit_non_family_calendar_keeps_simple_confirmation(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                confirmation_level='simple',
            )
        )
        read_client = _FakeReadClient(family_calendar=False, family_calendar_classification='non_family')

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute cet evenement',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-create-known-non-family',
        )

        self.assertTrue(result.used)
        action = result.pending_state.actions[0]
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_SIMPLE)
        self.assertNotIn('calendar_scope_unverified', action.risk_flags)
        self.assertNotIn('family_calendar', action.risk_flags)

    def test_propose_create_without_structured_draft_is_rejected_before_pending_action(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                operation='create',
                draft=_empty_draft(),
            )
        )

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Ajoute un rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            pending_id_factory=lambda: 'agenda-pending-create-missing-draft',
        )

        self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
        self.assertEqual(result.reason_code, agent_contract.REASON_DRAFT_INVALID)
        self.assertFalse(result.used)
        self.assertIsNone(result.proposal_execution_result)
        self.assertFalse(result.observability_payload['mutation_attempted'])

    def test_propose_update_requires_clear_local_event_target_and_creates_pending_action(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
            )
        )
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Deplace ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-update-1',
        )

        self.assertTrue(result.used)
        self.assertEqual(result.proposal_execution_result.operation, 'update')
        self.assertEqual(read_client.calls, ['get_event_by_local_id'])
        self.assertTrue(result.proposal_execution_result.target_clear)
        self.assertEqual(result.pending_state.actions[0].operation, 'update')
        self.assertIn('modification', result.final_response_lock.content)
        self.assertIn('Fixture Focus Block', result.final_response_lock.content)
        self.assertIn('Deplacer le creneau propose', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['caldav_access'])
        self.assertEqual(result.observability_payload['pending_operation'], 'update')
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('Fixture Location Alpha', encoded_payload)
        self.assertNotIn('fixture-event-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_propose_update_with_only_change_summary_is_rejected_before_pending_action(self) -> None:
        draft = _empty_draft()
        draft['change_summary'] = 'Fixture summary only'
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
                draft=draft,
            )
        )
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Modifie ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-update-summary-only',
        )

        self.assertEqual(result.status, agent_runtime.STATUS_FALLBACK)
        self.assertEqual(result.reason_code, agent_contract.REASON_DRAFT_INVALID)
        self.assertFalse(result.used)
        self.assertEqual(read_client.calls, [])
        self.assertEqual(result.pending_state.actions, ())
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture summary only', encoded_payload)

    def test_propose_update_runtime_caldav_fake_transport_verifies_target_before_pending_action(self) -> None:
        event_id = _live_fixture_event_id()
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
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
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': event_id},
                        'call_id': 'target-1',
                    },
                ],
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Deplace ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
            pending_id_factory=lambda: 'agenda-pending-update-caldav-1',
        )

        self.assertTrue(result.used)
        self.assertEqual(runtime_settings.secret_reads, 1)
        self.assertEqual([call['method'] for call in requests_module.calls], ['PROPFIND', 'REPORT', 'GET'])
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_CREATED)
        self.assertTrue(result.proposal_execution_result.target_clear)
        self.assertTrue(result.observability_payload['caldav_access'])
        self.assertTrue(result.observability_payload['nextcloud_access'])
        self.assertTrue(result.observability_payload['secret_access'])
        self.assertEqual(result.observability_payload['pending_operation'], 'update')
        private_draft = pending_store.private_draft_for_action(result.pending_state.actions[0])
        self.assertIn('BEGIN:VCALENDAR', private_draft['target']['technical_ref']['source_ics'])
        self.assertIn('Fixture Local Time Block', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('fixture-secret-value', encoded_payload)
        self.assertNotIn('Fixture Local Time Block', encoded_payload)
        self.assertNotIn('Fixture Location Alpha', encoded_payload)
        self.assertNotIn('fixture-local-time-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('BEGIN:VCALENDAR', encoded_payload)

    def test_propose_update_runtime_caldav_fake_transport_allows_search_before_target_get(self) -> None:
        event_id = _live_fixture_event_id()
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
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
                        'params': {'query': 'Local'},
                        'call_id': 'search-1',
                    },
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': event_id},
                        'call_id': 'target-1',
                    },
                ],
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Deplace ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
            pending_id_factory=lambda: 'agenda-pending-update-caldav-search-1',
        )

        self.assertEqual(runtime_settings.secret_reads, 1)
        self.assertEqual([call['method'] for call in requests_module.calls], ['PROPFIND', 'REPORT', 'GET'])
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_CREATED)
        self.assertTrue(result.proposal_execution_result.target_clear)
        self.assertTrue(result.observability_payload['caldav_access'])

    def test_propose_update_without_clear_target_does_not_create_pending_action(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
                tool_calls=[],
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Deplace ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            pending_id_factory=lambda: 'agenda-pending-update-ambiguous',
        )

        self.assertTrue(result.used)
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_TARGET_NOT_VERIFIED)
        self.assertFalse(result.proposal_execution_result.target_clear)
        self.assertEqual(result.pending_state.actions, ())
        self.assertIn('verifie', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['mutation_attempted'])

    def test_propose_update_declared_event_get_without_verified_read_is_rejected(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_UPDATE_EVENT,
                operation='update',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Deplace ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
            pending_id_factory=lambda: 'agenda-pending-update-unverified',
        )

        self.assertTrue(result.used)
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertEqual(requests_module.calls, [])
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_TARGET_NOT_VERIFIED)
        self.assertEqual(result.pending_state.actions, ())
        self.assertFalse(result.observability_payload['caldav_access'])
        self.assertFalse(result.observability_payload['secret_access'])
        self.assertFalse(result.observability_payload['mutation_attempted'])

    def test_propose_delete_creates_reinforced_pending_action_without_calendar_mutation(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_DELETE_EVENT,
                operation='delete',
                confirmation_level='reinforced',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
            )
        )
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Supprime ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-delete-1',
        )

        self.assertTrue(result.used)
        self.assertEqual(read_client.calls, ['get_event_by_local_id'])
        self.assertEqual(result.pending_state.actions[0].operation, 'delete')
        self.assertEqual(result.pending_state.actions[0].confirmation_level, 'reinforced')
        self.assertTrue(result.proposal_execution_result.target_clear)
        self.assertIn('Fixture Focus Block', result.final_response_lock.content)
        self.assertIn('confirmation renforcee', result.final_response_lock.content)
        self.assertIn("Rien n'a ete supprime", result.final_response_lock.content)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_propose_delete_family_calendar_preserves_reinforced_risk_flag(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_DELETE_EVENT,
                operation='delete',
                confirmation_level='reinforced',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
            )
        )
        read_client = _FakeReadClient(family_calendar=True)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Supprime ce rendez-vous familial',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            read_client=read_client,
            pending_id_factory=lambda: 'agenda-pending-family-delete-1',
        )

        self.assertTrue(result.used)
        action = result.pending_state.actions[0]
        self.assertEqual(action.operation, 'delete')
        self.assertEqual(action.confirmation_level, pending_store.CONFIRMATION_REINFORCED)
        self.assertIn('family_calendar', action.risk_flags)
        self.assertIn('partage ou familial', result.final_response_lock.content)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-event-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_propose_delete_declared_event_get_without_verified_read_is_rejected(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_DELETE_EVENT,
                operation='delete',
                confirmation_level='reinforced',
                tool_calls=[
                    {
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-1'},
                        'call_id': 'target-1',
                    }
                ],
            )
        )

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Supprime ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=fake_model,
            pending_id_factory=lambda: 'agenda-pending-delete-unverified',
        )

        self.assertTrue(result.used)
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_TARGET_NOT_VERIFIED)
        self.assertEqual(result.pending_state.actions, ())
        self.assertFalse(result.observability_payload['mutation_attempted'])

    def test_propose_delete_runtime_caldav_fake_transport_keeps_missing_target_refused(self) -> None:
        fake_model = _FakeModelClient(
            _proposal_payload(
                product_method=product_methods.METHOD_PROPOSE_DELETE_EVENT,
                operation='delete',
                confirmation_level='reinforced',
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
                        'tool_name': product_methods.TOOL_EVENT_GET,
                        'method': 'GET',
                        'params': {'event_id': 'event-missing'},
                        'call_id': 'target-1',
                    },
                ],
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        requests_module = _FakeRequestsModule()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Supprime ce rendez-vous',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            requests_module=requests_module,
            pending_id_factory=lambda: 'agenda-pending-delete-missing',
        )

        self.assertTrue(result.used)
        self.assertEqual([call['method'] for call in requests_module.calls], ['PROPFIND', 'REPORT'])
        self.assertEqual(result.proposal_execution_result.reason_code, proposal_execution.REASON_TARGET_NOT_VERIFIED)
        self.assertEqual(result.pending_state.actions, ())
        self.assertTrue(result.observability_payload['caldav_access'])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('fixture-secret-value', encoded_payload)
        self.assertNotIn('Fixture Local Time Block', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_create_event_executes_pending_draft_with_fake_write_transport(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            draft=_private_create_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-create-1',
        )
        transport = _FakeCalDavWriteTransport()
        write_client = caldav_write_client.CalDavWriteClient(
            transport=transport,
            calendar_paths={'primary': '/remote.php/dav/calendars/tof/fixture-primary/'},
        )
        fake_model = _FakeModelClient(
            _confirm_payload(
                product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                operation='create',
                pending_action_id='agenda-pending-create-1',
            )
        )
        runtime_settings = _SecretCountingRuntimeSettings(value='fixture-secret-value')
        read_client = _FakeReadClient()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            runtime_settings_module=runtime_settings,
            agent_model_client=fake_model,
            read_client=read_client,
            write_client=write_client,
            write_uid_factory=lambda: 'fixture-created-uid@example.invalid',
        )

        self.assertTrue(result.used)
        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertEqual(read_client.calls, [])
        self.assertEqual([call['method'] for call in transport.calls], ['PUT'])
        self.assertEqual(transport.calls[0]['headers'].get('If-None-Match'), '*')
        self.assertIn('BEGIN:VEVENT', transport.calls[0]['body'])
        self.assertIn('Fixture Confirm Create', transport.calls[0]['body'])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_EXECUTED)
        self.assertEqual(result.pending_state.actions[0].draft, {})
        self.assertNotIn('agenda-pending-create-1', pending_store._PRIVATE_DRAFTS)
        self.assertTrue(result.observability_payload['mutation_attempted'])
        self.assertTrue(result.observability_payload['caldav_access'])
        self.assertFalse(result.observability_payload['nextcloud_access'])
        self.assertFalse(result.observability_payload['secret_access'])
        self.assertIn("C'est cree", result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        encoded_meta = json.dumps(result.final_response_lock.to_message_meta(), sort_keys=True)
        for forbidden in (
            'BEGIN:VEVENT',
            'Fixture Confirm Create',
            'Fixture Confirm Room',
            'fixture-created-uid@example.invalid',
            '/remote.php/dav',
            'Authorization',
            'fixture-secret-value',
        ):
            self.assertNotIn(forbidden, encoded_payload)
            self.assertNotIn(forbidden, encoded_meta)

    def test_confirm_create_family_calendar_requires_reinforced_confirmation_before_put(self) -> None:
        draft = _private_create_draft()
        draft['family_calendar'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            risk_flags=('family_calendar',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-family-create-simple',
        )
        transport = _FakeCalDavWriteTransport()
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-family-create-simple',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(
                transport=transport,
                calendar_paths={'primary': '/remote.php/dav/calendars/tof/fixture-primary/'},
            ),
        )

        self.assertEqual(
            result.proposal_execution_result.reason_code,
            write_execution.REASON_WRITE_FAMILY_REINFORCED_REQUIRED,
        )
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('calendrier est partage ou familial', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Confirm Create', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_create_unverified_calendar_scope_requires_reinforced_before_put(self) -> None:
        draft = _private_create_draft()
        draft['family_calendar'] = False
        draft['family_calendar_classification'] = 'unknown'
        draft['calendar_scope_unverified'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            risk_flags=('calendar_scope_unverified',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-unverified-create-simple',
        )
        transport = _FakeCalDavWriteTransport()

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-unverified-create-simple',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(
                transport=transport,
                calendar_paths={'primary': '/remote.php/dav/calendars/tof/fixture-primary/'},
            ),
        )

        self.assertEqual(
            result.proposal_execution_result.reason_code,
            write_execution.REASON_WRITE_UNVERIFIED_REINFORCED_REQUIRED,
        )
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('type de ce calendrier', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Confirm Create', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_create_family_calendar_reinforced_executes_fake_put(self) -> None:
        draft = _private_create_draft()
        draft['family_calendar'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='reinforced',
            risk_flags=('family_calendar',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-family-create-reinforced',
        )
        transport = _FakeCalDavWriteTransport()
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme explicitement',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-family-create-reinforced',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(
                transport=transport,
                calendar_paths={'primary': '/remote.php/dav/calendars/tof/fixture-primary/'},
            ),
            write_uid_factory=lambda: 'fixture-family-created-uid@example.invalid',
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        self.assertEqual([call['method'] for call in transport.calls], ['PUT'])
        self.assertTrue(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Confirm Create', encoded_payload)
        self.assertNotIn('fixture-family-created-uid@example.invalid', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_update_event_preserves_source_ics_and_executes_fake_put(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=_private_update_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-1',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)
        write_client = caldav_write_client.CalDavWriteClient(transport=transport)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-1',
                )
            ),
            write_client=write_client,
        )

        self.assertTrue(result.used)
        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        self.assertEqual([call['method'] for call in transport.calls], ['PUT'])
        self.assertEqual(transport.calls[0]['headers'].get('If-Match'), 'fixture-etag-001')
        body = str(transport.calls[0]['body'])
        self.assertIn('UID:fixture-event-001@example.invalid', body)
        self.assertIn('SUMMARY:Fixture Updated Title', body)
        self.assertIn('DTSTART:20260609T080000Z', body)
        self.assertIn('X-FRIDA-KEEP:preserve-me', body)
        self.assertIn('BEGIN:VALARM', body)
        self.assertIn('ATTENDEE;CN=Fixture Attendee:mailto:fixture-attendee@example.invalid', body)
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_EXECUTED)
        self.assertTrue(result.observability_payload['mutation_attempted'])
        self.assertIn("J'ai modifie", result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        encoded_meta = json.dumps(result.final_response_lock.to_message_meta(), sort_keys=True)
        self.assertNotIn('Fixture Updated Title', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)
        self.assertNotIn('Fixture Updated Title', encoded_meta)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_meta)
        self.assertNotIn('fixture-etag-001', encoded_meta)
        self.assertNotIn('/remote.php/dav', encoded_meta)
        self.assertNotIn('BEGIN:VEVENT', encoded_meta)

    def test_confirm_update_title_only_preserves_time_location_description_and_unknown_properties(self) -> None:
        draft = _private_update_draft()
        draft['start'] = ''
        draft['end'] = ''
        draft['title'] = 'Fixture Title Only'
        draft['location'] = ''
        draft['description'] = ''
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-title-only',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-title-only',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        body = str(transport.calls[0]['body'])
        self.assertIn('SUMMARY:Fixture Title Only', body)
        self.assertIn('DTSTART:20260608T070000Z', body)
        self.assertIn('DTEND:20260608T080000Z', body)
        self.assertIn('LOCATION:Fixture Location Alpha', body)
        self.assertIn('DESCRIPTION:Fixture description\\, no personal data.', body)
        self.assertIn('X-FRIDA-KEEP:preserve-me', body)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Title Only', encoded_payload)
        self.assertNotIn('Fixture Location Alpha', encoded_payload)

    def test_confirm_update_time_only_preserves_title_location_and_description(self) -> None:
        draft = _private_update_draft()
        draft['start'] = '2026-06-08T09:00:00Z'
        draft['end'] = '2026-06-08T10:00:00Z'
        draft['title'] = ''
        draft['location'] = ''
        draft['description'] = ''
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-time-only',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-time-only',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        body = str(transport.calls[0]['body'])
        self.assertIn('DTSTART:20260608T090000Z', body)
        self.assertIn('DTEND:20260608T100000Z', body)
        self.assertIn('SUMMARY:Fixture Focus Block', body)
        self.assertIn('LOCATION:Fixture Location Alpha', body)
        self.assertIn('DESCRIPTION:Fixture description\\, no personal data.', body)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('Fixture Location Alpha', encoded_payload)

    def test_confirm_update_description_preserves_alarm_description(self) -> None:
        draft = _private_update_draft()
        draft['start'] = ''
        draft['end'] = ''
        draft['title'] = ''
        draft['location'] = ''
        draft['description'] = 'Fixture Updated Description'
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-description-only',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-description-only',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        body = str(transport.calls[0]['body'])
        self.assertIn('DESCRIPTION:Fixture Updated Description', body)
        self.assertIn('BEGIN:VALARM', body)
        self.assertIn('DESCRIPTION:Fixture alarm', body)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Updated Description', encoded_payload)
        self.assertNotIn('Fixture alarm', encoded_payload)

    def test_confirm_update_without_etag_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['target']['technical_ref']['etag'] = ''
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-no-etag',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)
        write_client = caldav_write_client.CalDavWriteClient(transport=transport)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-no-etag',
                )
            ),
            write_client=write_client,
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ETAG_MISSING)
        self.assertEqual(transport.calls, [])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_PENDING)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Updated Title', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_update_without_source_ics_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['target']['technical_ref']['source_ics'] = ''
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-no-source-ics',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-no-source-ics',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ICS_SOURCE_MISSING)
        self.assertEqual(transport.calls, [])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_PENDING)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('version source verifiee', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)

    def test_confirm_update_multivevent_source_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['target']['technical_ref']['source_ics'] = _MULTI_EVENT_SOURCE_UPDATE_ICS
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-multivevent',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-multivevent',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ICS_COMPONENT_AMBIGUOUS)
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('series@example.invalid', encoded_payload)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_update_recurring_source_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['target']['technical_ref']['source_ics'] = _RECURRING_SOURCE_UPDATE_ICS
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-recurring',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-recurring',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ICS_COMPONENT_AMBIGUOUS)
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('recurrence', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('RRULE', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)

    def test_confirm_update_override_source_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['target']['technical_ref']['source_ics'] = _OVERRIDE_SOURCE_UPDATE_ICS
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-override',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-override',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ICS_COMPONENT_AMBIGUOUS)
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('RECURRENCE-ID', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)

    def test_confirm_update_legacy_change_summary_only_refuses_before_put(self) -> None:
        draft = _private_update_draft()
        draft['start'] = ''
        draft['end'] = ''
        draft['title'] = ''
        draft['location'] = ''
        draft['description'] = ''
        draft['change_summary'] = 'Fixture change summary only'
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-noop',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-noop',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ICS_NOOP)
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('changement executable', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture change summary only', encoded_payload)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)

    def test_confirm_update_conflict_is_content_free_and_keeps_pending_action(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='update',
            confirmation_level='simple',
            draft=_private_update_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-update-conflict',
        )
        transport = _FakeCalDavWriteTransport(status_code=412)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la modification',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_UPDATE_EVENT,
                    operation='update',
                    pending_action_id='agenda-pending-update-conflict',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_CONFLICT)
        self.assertEqual([call['method'] for call in transport.calls], ['PUT'])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_PENDING)
        self.assertTrue(result.observability_payload['mutation_attempted'])
        self.assertIn('calendrier a change', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Updated Title', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)
        self.assertNotIn('BEGIN:VEVENT', encoded_payload)

    def test_caldav_write_client_refuses_existing_writes_without_etag(self) -> None:
        transport = _FakeCalDavWriteTransport(status_code=204)
        write_client = caldav_write_client.CalDavWriteClient(transport=transport)

        with self.assertRaises(caldav_write_client.CalDavWriteValidationError) as update_error:
            write_client.put_existing_event(
                caldav_path='/remote.php/dav/calendars/tof/fixture-primary/event-1.ics',
                ics_text='BEGIN:VCALENDAR\r\nEND:VCALENDAR\r\n',
                etag='',
            )
        with self.assertRaises(caldav_write_client.CalDavWriteValidationError) as delete_error:
            write_client.delete_event(
                caldav_path='/remote.php/dav/calendars/tof/fixture-primary/event-1.ics',
                etag='',
            )

        self.assertEqual(update_error.exception.reason_code, write_execution.REASON_WRITE_ETAG_MISSING)
        self.assertEqual(delete_error.exception.reason_code, write_execution.REASON_WRITE_ETAG_MISSING)
        self.assertEqual(transport.calls, [])

    def test_confirm_delete_event_requires_reinforced_pending_action_and_executes_delete(self) -> None:
        simple_state, _simple = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='simple',
            draft=_private_delete_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-delete-simple',
        )
        simple_transport = _FakeCalDavWriteTransport()
        simple_result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=simple_state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-simple',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=simple_transport),
        )
        self.assertEqual(simple_result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_REINFORCED_REQUIRED)
        self.assertEqual(simple_transport.calls, [])
        self.assertFalse(simple_result.observability_payload['mutation_attempted'])

        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            draft=_private_delete_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-delete-1',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)
        write_client = caldav_write_client.CalDavWriteClient(transport=transport)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme vraiment la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-1',
                    confirmation_level='reinforced',
                )
            ),
            write_client=write_client,
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        self.assertEqual([call['method'] for call in transport.calls], ['DELETE'])
        self.assertEqual(transport.calls[0]['headers'].get('If-Match'), 'fixture-etag-001')
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_EXECUTED)
        self.assertTrue(result.observability_payload['mutation_attempted'])
        self.assertIn("C'est supprime", result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_family_calendar_simple_is_refused_before_delete(self) -> None:
        draft = _private_delete_draft()
        draft['family_calendar'] = True
        draft['target']['family_calendar'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='simple',
            risk_flags=('family_calendar',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-family-delete-simple',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-family-delete-simple',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(
            result.proposal_execution_result.reason_code,
            write_execution.REASON_WRITE_FAMILY_REINFORCED_REQUIRED,
        )
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('calendrier est partage ou familial', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_unverified_calendar_scope_simple_is_refused_before_delete(self) -> None:
        draft = _private_delete_draft()
        draft['family_calendar'] = False
        draft['family_calendar_classification'] = 'unknown'
        draft['calendar_scope_unverified'] = True
        draft['target']['family_calendar'] = False
        draft['target']['family_calendar_classification'] = 'unknown'
        draft['target']['calendar_scope_unverified'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='simple',
            risk_flags=('calendar_scope_unverified',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-unverified-delete-simple',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-unverified-delete-simple',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(
            result.proposal_execution_result.reason_code,
            write_execution.REASON_WRITE_UNVERIFIED_REINFORCED_REQUIRED,
        )
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        self.assertIn('type de ce calendrier', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_family_calendar_reinforced_executes_fake_delete(self) -> None:
        draft = _private_delete_draft()
        draft['family_calendar'] = True
        draft['target']['family_calendar'] = True
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            risk_flags=('family_calendar',),
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-family-delete-reinforced',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme vraiment la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-family-delete-reinforced',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_EXECUTED)
        self.assertEqual([call['method'] for call in transport.calls], ['DELETE'])
        self.assertTrue(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-event-001@example.invalid', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_without_etag_refuses_before_delete(self) -> None:
        draft = _private_delete_draft()
        draft['target']['technical_ref']['etag'] = ''
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-delete-no-etag',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme vraiment la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-no-etag',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_ETAG_MISSING)
        self.assertEqual(transport.calls, [])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_PENDING)
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_conflict_is_content_free_and_keeps_pending_action(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            draft=_private_delete_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-delete-conflict',
        )
        transport = _FakeCalDavWriteTransport(status_code=412)
        write_client = caldav_write_client.CalDavWriteClient(transport=transport)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme vraiment la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-conflict',
                    confirmation_level='reinforced',
                )
            ),
            write_client=write_client,
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_CONFLICT)
        self.assertEqual([call['method'] for call in transport.calls], ['DELETE'])
        self.assertEqual(result.pending_state.actions[0].status, pending_store.STATUS_PENDING)
        self.assertTrue(result.observability_payload['mutation_attempted'])
        self.assertIn('calendrier a change', result.final_response_lock.content)
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('Fixture Focus Block', encoded_payload)
        self.assertNotIn('fixture-etag-001', encoded_payload)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_delete_without_private_technical_target_refuses_before_write(self) -> None:
        draft = _private_delete_draft()
        draft['target'] = {'event_id': 'event-1', 'calendar_id': 'primary', 'technical_ref': {}}
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            draft=draft,
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-delete-no-target',
        )
        transport = _FakeCalDavWriteTransport(status_code=204)

        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme vraiment la suppression',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-no-target',
                    confirmation_level='reinforced',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )

        self.assertEqual(result.proposal_execution_result.reason_code, write_execution.REASON_WRITE_TARGET_MISSING)
        self.assertEqual(transport.calls, [])
        self.assertFalse(result.observability_payload['pending_target_clear'])
        self.assertFalse(result.observability_payload['mutation_attempted'])
        encoded_payload = json.dumps(result.observability_payload, sort_keys=True)
        self.assertNotIn('/remote.php/dav', encoded_payload)

    def test_confirm_with_missing_private_draft_or_missing_client_refuses_before_write(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            draft=_private_create_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-create-lost',
        )
        pending_store._PRIVATE_DRAFTS.pop('agenda-pending-create-lost', None)
        restored = pending_store.AgendaPendingState.from_mapping(state.to_dict())
        transport = _FakeCalDavWriteTransport()
        missing_draft = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=restored,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-create-lost',
                )
            ),
            write_client=caldav_write_client.CalDavWriteClient(transport=transport),
        )
        self.assertEqual(missing_draft.proposal_execution_result.reason_code, write_execution.REASON_WRITE_PRIVATE_DRAFT_MISSING)
        self.assertEqual(transport.calls, [])
        self.assertFalse(missing_draft.observability_payload['mutation_attempted'])
        self.assertIn('refaire une proposition', missing_draft.final_response_lock.content)

        configured_state, _configured = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            draft=_private_create_draft(),
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-create-no-client',
        )
        no_client = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:05:00Z',
            conversation_state=configured_state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-create-no-client',
                )
            ),
        )
        self.assertEqual(no_client.proposal_execution_result.reason_code, write_execution.REASON_WRITE_CLIENT_UNAVAILABLE)
        self.assertFalse(no_client.observability_payload['mutation_attempted'])
        self.assertFalse(no_client.observability_payload['caldav_access'])
        self.assertIn("L'ecriture dans l'agenda n'est pas encore activee ici", no_client.final_response_lock.content)
        for technical_word in ('client', 'injecte', 'transport fake', 'CalDAV write', 'lot'):
            self.assertNotIn(technical_word, no_client.final_response_lock.content)

    def test_expired_or_cancelled_pending_action_cannot_be_executed(self) -> None:
        state, _action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='delete',
            confirmation_level='reinforced',
            draft={'schema_version': 'fixture', 'content_free': True},
            now_iso='2026-06-08T12:00:00Z',
            ttl_seconds=1,
            id_factory=lambda: 'agenda-pending-delete-1',
        )
        expired_confirm = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:01:00Z',
            conversation_state=state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_DELETE_EVENT,
                    operation='delete',
                    pending_action_id='agenda-pending-delete-1',
                    confirmation_level='reinforced',
                )
            ),
        )

        self.assertEqual(expired_confirm.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_EXPIRED)
        self.assertIn('expiree', expired_confirm.final_response_lock.content)
        self.assertFalse(expired_confirm.observability_payload['mutation_attempted'])
        self.assertEqual(expired_confirm.pending_state.actions[0].draft, {})
        self.assertNotIn('agenda-pending-delete-1', pending_store._PRIVATE_DRAFTS)

        fresh_state, _fresh_action = pending_store.create_pending_action(
            pending_store.AgendaPendingState.empty(conversation_id='conv-agenda'),
            operation='create',
            confirmation_level='simple',
            draft={'schema_version': 'fixture', 'content_free': True},
            now_iso='2026-06-08T12:00:00Z',
            id_factory=lambda: 'agenda-pending-create-2',
        )
        cancelled = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Annule',
            now_iso='2026-06-08T12:01:00Z',
            conversation_state=fresh_state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(_cancel_payload('agenda-pending-create-2')),
        )
        self.assertEqual(cancelled.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_CANCELLED)
        self.assertEqual(cancelled.pending_state.actions[0].status, pending_store.STATUS_CANCELLED)
        self.assertEqual(cancelled.pending_state.actions[0].draft, {})
        self.assertNotIn('agenda-pending-create-2', pending_store._PRIVATE_DRAFTS)

        confirm_cancelled = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='Je confirme',
            now_iso='2026-06-08T12:02:00Z',
            conversation_state=cancelled.pending_state,
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _confirm_payload(
                    product_method=product_methods.METHOD_CONFIRM_CREATE_EVENT,
                    operation='create',
                    pending_action_id='agenda-pending-create-2',
                )
            ),
        )
        self.assertEqual(confirm_cancelled.proposal_execution_result.reason_code, proposal_execution.REASON_PENDING_NOT_FOUND)
        self.assertFalse(confirm_cancelled.observability_payload['mutation_attempted'])

    def test_private_drafts_are_forgotten_when_pending_action_is_truncated(self) -> None:
        state = pending_store.AgendaPendingState.empty(conversation_id='conv-agenda')
        for index in range(pending_store.MAX_ACTIONS + 1):
            state, _action = pending_store.create_pending_action(
                state,
                operation='create',
                confirmation_level='simple',
                draft={'schema_version': 'fixture', 'title': f'Fixture {index}'},
                now_iso='2026-06-08T12:00:00Z',
                id_factory=lambda index=index: f'agenda-pending-create-{index}',
            )

        self.assertEqual(len(state.actions), pending_store.MAX_ACTIONS)
        self.assertNotIn('agenda-pending-create-0', [action.pending_action_id for action in state.actions])
        self.assertNotIn('agenda-pending-create-0', pending_store._PRIVATE_DRAFTS)
        self.assertIn('agenda-pending-create-12', pending_store._PRIVATE_DRAFTS)

    def test_agenda_pending_state_is_attached_to_latest_user_message_content_free(self) -> None:
        conversation = {
            'id': 'conv-agenda',
            'messages': [{'role': 'user', 'content': 'RAW USER MESSAGE MUST NOT LEAK'}],
        }
        result = chat_runtime.run_agenda_chat_turn(
            {'agenda_enabled': True},
            user_msg='RAW USER MESSAGE MUST NOT LEAK',
            now_iso='2026-06-08T12:00:00Z',
            settings_override=agent_contract.AgendaAgentSettings(
                mode=agent_contract.MODE_ACTIVE,
                caldav_secret_configured=True,
            ),
            agent_model_client=_FakeModelClient(
                _proposal_payload(
                    product_method=product_methods.METHOD_PROPOSE_CREATE_EVENT,
                    operation='create',
                    intent='RAW EVENT DETAILS MUST NOT LEAK',
                )
            ),
            pending_id_factory=lambda: 'agenda-pending-create-1',
        )

        self.assertTrue(chat_runtime.attach_agenda_conversation_state(conversation, result))
        loaded = chat_runtime.read_agenda_conversation_state(conversation)
        self.assertEqual(loaded.actions[0].pending_action_id, 'agenda-pending-create-1')
        encoded_meta = json.dumps(conversation['messages'][0]['meta'], sort_keys=True)
        self.assertNotIn('RAW EVENT DETAILS MUST NOT LEAK', encoded_meta)
        self.assertNotIn('RAW USER MESSAGE MUST NOT LEAK', encoded_meta)
        self.assertNotIn('Fixture Agenda Proposal', encoded_meta)
        self.assertNotIn('Fixture Room', encoded_meta)
        self.assertNotIn('Synthetic pending draft', encoded_meta)


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
    def __init__(self, *, family_calendar: bool = False, family_calendar_classification: str | None = None) -> None:
        self.calls: list[str] = []
        classification = family_calendar_classification
        if classification is None:
            classification = 'family' if family_calendar else 'non_family'
        self._calendar = CalendarSummary(
            local_id='primary',
            display_name='Fixture Primary Calendar',
            permissions=('read',),
            color='#1166aa',
            enabled=True,
            readonly=True,
            family_calendar=family_calendar,
            family_calendar_classification=classification,
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/',
        )
        self._event = CalendarEvent(
            event_id='event-1',
            calendar_id='primary',
            uid='fixture-event-001@example.invalid',
            summary='Fixture Focus Block',
            location='Fixture Location Alpha',
            description='Fixture description, no personal data.',
            start_iso='2026-06-08T07:00:00Z',
            end_iso='2026-06-08T08:00:00Z',
            timezone='Europe/Paris',
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

    def get_event_by_local_id(self, event_id):
        self.calls.append('get_event_by_local_id')
        return self._event if str(event_id or '') == self._event.event_id else None

    def calendar_by_local_id(self, calendar_id):
        return self._calendar if str(calendar_id or '') == self._calendar.local_id else None


class _AllDayReadClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.query_ranges: list[tuple[str, str, str]] = []
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
            event_id='event-all-day',
            calendar_id='primary',
            uid='fixture-all-day-001@example.invalid',
            summary='Fixture All Day Block',
            location='Fixture Location Day',
            description='Fixture description, no personal data.',
            start_iso='2026-06-07T22:00:00Z',
            end_iso='2026-06-08T22:00:00Z',
            timezone='Europe/Paris',
            etag='fixture-etag-all-day',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/event-all-day.ics',
            all_day=True,
        )

    def list_calendars(self):
        self.calls.append('list_calendars')
        return (self._calendar,)

    def query_calendar_events(self, calendar, *, start_iso, end_iso, timezone_name='UTC'):
        del calendar
        self.calls.append('query_calendar_events')
        self.query_ranges.append((start_iso, end_iso, timezone_name))
        return (self._event,)

    def get_event(self, event):
        del event
        self.calls.append('get_event')
        return self._event

    def get_event_by_local_id(self, event_id):
        self.calls.append('get_event_by_local_id')
        return self._event if str(event_id or '') == self._event.event_id else None


class _SecretCountingRuntimeSettings:
    def __init__(self, *, value: str = '') -> None:
        self.value = value
        self.secret_reads = 0

    def get_runtime_secret_value(self, section, field):
        self.secret_reads += 1
        return type(
            'RuntimeSecretValueFixture',
            (),
            {'section': section, 'field': field, 'value': self.value},
        )()


class _FakeHttpResponse:
    def __init__(self, *, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class _FakeRequestsModule:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def request(self, method, url, *, headers, data, timeout):
        self.calls.append(
            {
                'method': str(method),
                'url_hash': agent_contract.sha256_12(str(url)),
                'auth_present': str(bool(headers.get('Authorization'))),
                'data_present': str(bool(data)),
                'timeout': str(timeout),
            }
        )
        if method == 'PROPFIND':
            return _FakeHttpResponse(status_code=207, text=_CALENDAR_PROPFIND_XML)
        if method == 'REPORT':
            return _FakeHttpResponse(status_code=207, text=_PRIMARY_REPORT_XML)
        if method == 'GET':
            return _FakeHttpResponse(status_code=200, text=_PRIMARY_ICS)
        raise AssertionError(f'unexpected method: {method}')


class _FakeCalDavWriteTransport:
    def __init__(self, *, status_code: int = 201) -> None:
        self.status_code = status_code
        self.calls: list[dict[str, object]] = []

    def __call__(self, request):
        self.calls.append(
            {
                'method': request.method,
                'url_hash': agent_contract.sha256_12(request.url),
                'headers': dict(request.headers),
                'body': request.body,
            }
        )
        return caldav_write_client.CalDavResponse(status_code=self.status_code, text='')


class _UnauthorizedRequestsModule:
    def request(self, method, url, *, headers, data, timeout):
        del url, headers, data, timeout
        return _FakeHttpResponse(status_code=401, text='RAW BODY MUST NOT LEAK')


_CALENDAR_PROPFIND_XML = """<?xml version="1.0" encoding="UTF-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">
  <d:response>
    <d:href>/remote.php/dav/calendars/tof/fixture-primary/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Fixture Primary Calendar</d:displayname>
        <cs:calendar-color>#1166aa</cs:calendar-color>
        <d:current-user-privilege-set>
          <d:privilege><d:read/></d:privilege>
        </d:current-user-privilege-set>
      </d:prop>
    </d:propstat>
  </d:response>
</d:multistatus>
"""


_PRIMARY_ICS = """BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:Fixture Primary Calendar
BEGIN:VEVENT
UID:fixture-local-time-001@example.invalid
DTSTART:20260608T070000Z
DTEND:20260608T080000Z
SUMMARY:Fixture Local Time Block
LOCATION:Fixture Location Alpha
DESCRIPTION:Synthetic fixture event. No personal data.
END:VEVENT
END:VCALENDAR
"""


_PRIMARY_REPORT_XML = f"""<?xml version="1.0" encoding="UTF-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:cal="urn:ietf:params:xml:ns:caldav">
  <d:response>
    <d:href>/remote.php/dav/calendars/tof/fixture-primary/event-1.ics</d:href>
    <d:propstat>
      <d:prop>
        <d:getetag>fixture-etag-001</d:getetag>
        <cal:calendar-data>{_PRIMARY_ICS}</cal:calendar-data>
      </d:prop>
    </d:propstat>
  </d:response>
</d:multistatus>
"""


_SOURCE_UPDATE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Fixture Agenda//EN
BEGIN:VEVENT
UID:fixture-event-001@example.invalid
DTSTAMP:20260608T060000Z
DTSTART:20260608T070000Z
DTEND:20260608T080000Z
SUMMARY:Fixture Focus Block
LOCATION:Fixture Location Alpha
DESCRIPTION:Fixture description\\, no personal data.
ATTENDEE;CN=Fixture Attendee:mailto:fixture-attendee@example.invalid
X-FRIDA-KEEP:preserve-me
BEGIN:VALARM
ACTION:DISPLAY
DESCRIPTION:Fixture alarm
TRIGGER:-PT10M
END:VALARM
END:VEVENT
END:VCALENDAR
"""


_RECURRING_SOURCE_UPDATE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Fixture Agenda//EN
BEGIN:VEVENT
UID:fixture-event-001@example.invalid
DTSTAMP:20260608T060000Z
DTSTART:20260608T070000Z
DTEND:20260608T080000Z
SUMMARY:Fixture Focus Block
RRULE:FREQ=WEEKLY;COUNT=2
END:VEVENT
END:VCALENDAR
"""


_OVERRIDE_SOURCE_UPDATE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Fixture Agenda//EN
BEGIN:VEVENT
UID:fixture-event-001@example.invalid
RECURRENCE-ID:20260610T070000Z
DTSTART:20260610T090000Z
DTEND:20260610T100000Z
SUMMARY:Fixture Override Block
END:VEVENT
END:VCALENDAR
"""


_MULTI_EVENT_SOURCE_UPDATE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:series@example.invalid
DTSTART:20260609T070000Z
DTEND:20260609T080000Z
SUMMARY:Master
RRULE:FREQ=DAILY;COUNT=2
END:VEVENT
BEGIN:VEVENT
UID:series@example.invalid
RECURRENCE-ID:20260610T070000Z
DTSTART:20260610T090000Z
DTEND:20260610T100000Z
SUMMARY:Override
END:VEVENT
END:VCALENDAR
"""


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


def _live_fixture_calendar_id() -> str:
    return f"cal_{agent_contract.sha256_12('/remote.php/dav/calendars/tof/fixture-primary/')}"


def _live_fixture_event_id() -> str:
    return f"evt_{agent_contract.sha256_12(f'{_live_fixture_calendar_id()}:fixture-local-time-001@example.invalid')}"


def _proposal_payload(
    *,
    product_method: str,
    operation: str,
    intent: str = 'prepare agenda proposal',
    confirmation_level: str = 'simple',
    tool_calls=None,
    draft=None,
    calendar_scope=None,
    risk_flags=None,
) -> dict:
    return _valid_payload(
        product_method=product_method,
        intent=intent,
        calendar_scope=dict(calendar_scope) if calendar_scope is not None else {
            'calendar_ids': ['primary'],
            'family_calendar': False,
            'ambiguity': 'none',
        },
        tool_calls=list(tool_calls or []),
        draft=dict(draft if draft is not None else _default_proposal_draft(operation)),
        mutation={
            'requested': False,
            'kind': operation,
            'confirmation_required': True,
            'confirmation_level': confirmation_level,
            'pending_action_id': '',
        },
        answer_mode='proposal',
        risk_flags=list(risk_flags or []),
    )


def _private_create_draft() -> dict:
    return {
        'schema_version': 'frida_agenda_pending_draft_private_v1',
        'product_method': product_methods.METHOD_PROPOSE_CREATE_EVENT,
        'operation': 'create',
        'calendar_id': 'primary',
        'timezone': 'Europe/Paris',
        'start': '2026-06-09T08:00:00Z',
        'end': '2026-06-09T09:00:00Z',
        'all_day': False,
        'title': 'Fixture Confirm Create',
        'location': 'Fixture Confirm Room',
        'description': 'Synthetic confirmed create draft.',
        'change_summary': '',
        'family_calendar': False,
        'family_calendar_classification': 'non_family',
        'calendar_scope_unverified': False,
        'target': {},
    }


def _private_update_draft() -> dict:
    draft = _private_create_draft()
    draft.update(
        {
            'product_method': product_methods.METHOD_PROPOSE_UPDATE_EVENT,
            'operation': 'update',
            'calendar_id': 'primary',
            'title': 'Fixture Updated Title',
            'location': '',
            'description': '',
            'change_summary': 'Fixture update change',
            'target': _private_target(),
        }
    )
    return draft


def _private_delete_draft() -> dict:
    return {
        'schema_version': 'frida_agenda_pending_draft_private_v1',
        'product_method': product_methods.METHOD_PROPOSE_DELETE_EVENT,
        'operation': 'delete',
        'calendar_id': 'primary',
        'timezone': 'Europe/Paris',
        'start': '2026-06-08T07:00:00Z',
        'end': '2026-06-08T08:00:00Z',
        'all_day': False,
        'title': '',
        'location': '',
        'description': '',
        'change_summary': 'Fixture delete change',
        'family_calendar': False,
        'family_calendar_classification': 'non_family',
        'calendar_scope_unverified': False,
        'target': _private_target(),
    }


def _private_target() -> dict:
    return {
        'event_id': 'event-1',
        'calendar_id': 'primary',
        'timezone': 'Europe/Paris',
        'start': '2026-06-08T07:00:00Z',
        'end': '2026-06-08T08:00:00Z',
        'all_day': False,
        'title': 'Fixture Focus Block',
        'location': 'Fixture Location Alpha',
        'description': 'Fixture description, no personal data.',
        'family_calendar': False,
        'family_calendar_classification': 'non_family',
        'calendar_scope_unverified': False,
        'technical_ref': {
            'uid': 'fixture-event-001@example.invalid',
            'etag': 'fixture-etag-001',
            'caldav_path': '/remote.php/dav/calendars/tof/fixture-primary/event-1.ics',
            'source_ics': _SOURCE_UPDATE_ICS,
        },
    }


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


def _default_proposal_draft(operation: str) -> dict:
    draft = _empty_draft()
    if operation == 'create':
        draft.update(
            {
                'title': 'Fixture Agenda Proposal',
                'calendar_id': 'primary',
                'start': '2026-06-09T08:00:00Z',
                'end': '2026-06-09T09:00:00Z',
                'timezone': 'Europe/Paris',
                'all_day': False,
                'location': 'Fixture Room',
                'description': 'Synthetic pending draft.',
            }
        )
    elif operation == 'update':
        draft.update(
            {
                'change_summary': 'Deplacer le creneau propose',
                'start': '2026-06-09T08:00:00Z',
                'end': '2026-06-09T09:00:00Z',
                'timezone': 'Europe/Paris',
            }
        )
    elif operation == 'delete':
        draft.update({'change_summary': 'Suppression demandee'})
    return draft


def _confirm_payload(
    *,
    product_method: str,
    operation: str,
    pending_action_id: str,
    confirmation_level: str = 'simple',
) -> dict:
    return _valid_payload(
        product_method=product_method,
        tool_calls=[],
        mutation={
            'requested': True,
            'kind': operation,
            'confirmation_required': True,
            'confirmation_level': confirmation_level,
            'pending_action_id': pending_action_id,
        },
        answer_mode='mutation_pending_confirmation',
    )


def _cancel_payload(pending_action_id: str) -> dict:
    return _valid_payload(
        product_method=product_methods.METHOD_CANCEL_PENDING_AGENDA_ACTION,
        tool_calls=[],
        mutation={
            'requested': False,
            'kind': 'none',
            'confirmation_required': False,
            'confirmation_level': 'none',
            'pending_action_id': pending_action_id,
        },
        answer_mode='mutation_refused',
    )


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
