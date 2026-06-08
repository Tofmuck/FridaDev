from __future__ import annotations

import json
import unittest
from types import SimpleNamespace

from agenda import agent_contract, agent_runtime, chat_runtime, product_methods, read_execution, response_rendering
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
            return _FakeHttpResponse(status_code=207, text=_PRIMARY_ICS)
        raise AssertionError(f'unexpected method: {method}')


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
