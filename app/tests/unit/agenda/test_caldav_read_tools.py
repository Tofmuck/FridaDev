from __future__ import annotations

import importlib
import os
import sys
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from agenda import caldav_read_client, ics_reader, read_tools
from agenda.caldav_models import (
    AgendaReadState,
    CalDavResponse,
    CalDavTransportUnavailable,
    CalendarEvent,
    ReadToolValidationError,
)
from agenda.observability import observation_has_forbidden_shape


FIXTURE_DIR = APP_DIR / 'docs' / 'states' / 'baselines' / 'agenda-fixtures'
PRIMARY_ICS = (FIXTURE_DIR / 'anonymous-primary-calendar.ics').read_text(encoding='utf-8')
SHARED_ICS = (FIXTURE_DIR / 'anonymous-shared-calendar.ics').read_text(encoding='utf-8')


CALENDAR_PROPFIND_XML = """<?xml version="1.0" encoding="UTF-8"?>
<d:multistatus xmlns:d="DAV:" xmlns:cs="http://calendarserver.org/ns/">
  <d:response>
    <d:href>/remote.php/dav/calendars/tof/fixture-primary/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Fixture Primary Calendar</d:displayname>
        <cs:calendar-color>#1166aa</cs:calendar-color>
        <d:current-user-privilege-set>
          <d:privilege><d:read/></d:privilege>
          <d:privilege><d:write/></d:privilege>
        </d:current-user-privilege-set>
      </d:prop>
    </d:propstat>
  </d:response>
  <d:response>
    <d:href>/remote.php/dav/calendars/tof/fixture-shared/</d:href>
    <d:propstat>
      <d:prop>
        <d:displayname>Fixture Shared Calendar</d:displayname>
        <cs:calendar-color>#aa6611</cs:calendar-color>
        <x-frida-risk-flag>family_calendar</x-frida-risk-flag>
        <d:current-user-privilege-set>
          <d:privilege><d:read/></d:privilege>
        </d:current-user-privilege-set>
      </d:prop>
    </d:propstat>
  </d:response>
</d:multistatus>
"""


class FakeReadTransport:
    def __init__(self) -> None:
        self.calls = []

    def __call__(self, request):
        self.calls.append(request)
        if request.kind == 'calendar_list':
            return CalDavResponse(status_code=207, text=CALENDAR_PROPFIND_XML)
        if request.kind == 'event_query_range':
            if 'fixture-shared' in request.url:
                return CalDavResponse(status_code=207, text=SHARED_ICS)
            return CalDavResponse(status_code=207, text=PRIMARY_ICS)
        if request.kind == 'event_get':
            return CalDavResponse(status_code=200, text=PRIMARY_ICS)
        raise AssertionError(f'unexpected request kind: {request.kind}')


class AgendaCalDavReadToolsTests(unittest.TestCase):
    def _client_and_state(self) -> tuple[caldav_read_client.CalDavReadClient, AgendaReadState, FakeReadTransport]:
        transport = FakeReadTransport()
        client = caldav_read_client.CalDavReadClient(
            transport=transport,
            base_url='https://caldav.invalid/',
        )
        state = AgendaReadState()
        read_tools.calendar_list(client, state=state)
        return client, state, transport

    def test_parse_anonymous_ics_fixture_events_without_network(self) -> None:
        events = ics_reader.parse_ics_events(PRIMARY_ICS, calendar_id='fixture_primary')

        self.assertEqual(ics_reader.parse_calendar_name(PRIMARY_ICS), 'Fixture Primary Calendar')
        self.assertFalse(ics_reader.parse_family_calendar_flag(PRIMARY_ICS))
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].start_iso, '2026-06-09T07:00:00Z')
        self.assertLess(events[0].start_iso, events[1].start_iso)
        self.assertEqual(events[0].summary, 'Fixture Focus Block')

    def test_calendar_list_returns_two_anonymous_calendars_with_content_free_observation(self) -> None:
        transport = FakeReadTransport()
        client = caldav_read_client.CalDavReadClient(transport=transport)
        state = AgendaReadState()

        result = read_tools.calendar_list(client, state=state)

        self.assertEqual([request.kind for request in transport.calls], ['calendar_list'])
        self.assertEqual(result.status, 'ok')
        self.assertEqual(len(result.items), 2)
        self.assertEqual({calendar.display_name for calendar in result.items}, {
            'Fixture Primary Calendar',
            'Fixture Shared Calendar',
        })
        shared = [calendar for calendar in result.items if calendar.display_name == 'Fixture Shared Calendar'][0]
        self.assertTrue(shared.family_calendar)
        self.assertTrue(shared.readonly)
        self.assertEqual(len(state.calendars), 2)
        self.assertEqual(result.observation['calendar_count'], 2)
        self.assertTrue(result.observation['content_free'])
        self.assertFalse(observation_has_forbidden_shape(result.observation))
        self.assertNotIn('/remote.php/dav/calendars/tof/fixture-primary/', repr(result.observation))

    def test_event_query_range_returns_sorted_events_and_content_free_observation(self) -> None:
        client, state, transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')

        result = read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-09T00:00:00Z',
            end_iso='2026-06-10T00:00:00Z',
            timezone_name='UTC',
        )

        self.assertEqual(transport.calls[-1].method, 'REPORT')
        self.assertIn('time-range', transport.calls[-1].body)
        self.assertEqual(len(result.items), 2)
        self.assertLess(result.items[0].start_iso, result.items[1].start_iso)
        self.assertEqual(result.items[0].summary, 'Fixture Focus Block')
        self.assertEqual(result.observation['tool_name'], 'event_query_range')
        self.assertEqual(result.observation['event_count'], 2)
        self.assertTrue(result.observation['content_free'])
        self.assertContentFreeObservation(result.observation)

    def test_event_query_range_rejects_missing_inverted_too_large_or_unknown_windows(self) -> None:
        client, state, _transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        cases = (
            {'calendar_id': primary_id, 'start_iso': '', 'end_iso': '2026-06-10T00:00:00Z'},
            {'calendar_id': primary_id, 'start_iso': '2026-06-10T00:00:00Z', 'end_iso': '2026-06-09T00:00:00Z'},
            {'calendar_id': primary_id, 'start_iso': '2026-06-01T00:00:00Z', 'end_iso': '2026-08-01T00:00:00Z'},
            {'calendar_id': 'missing-calendar', 'start_iso': '2026-06-09T00:00:00Z', 'end_iso': '2026-06-10T00:00:00Z'},
        )

        for kwargs in cases:
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ReadToolValidationError):
                    read_tools.event_query_range(client, state=state, timezone_name='UTC', **kwargs)

    def test_event_get_returns_only_known_event_without_uid_etag_or_url_in_observation(self) -> None:
        client, state, _transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        query_result = read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-09T00:00:00Z',
            end_iso='2026-06-10T00:00:00Z',
        )
        known_event = query_result.items[0]

        get_result = read_tools.event_get(state=state, event_id=known_event.event_id)

        self.assertEqual(get_result.items, (known_event,))
        self.assertEqual(get_result.observation['tool_name'], 'event_get')
        self.assertEqual(get_result.observation['selected_event_hash'], read_tools.local_reference_id(known_event.event_id))
        self.assertContentFreeObservation(get_result.observation)
        with self.assertRaises(ReadToolValidationError):
            read_tools.event_get(state=state, event_id='evt_missing')

    def test_read_client_constructs_get_with_fake_transport_only(self) -> None:
        transport = FakeReadTransport()
        client = caldav_read_client.CalDavReadClient(
            transport=transport,
            base_url='https://caldav.invalid/',
        )
        event = CalendarEvent(
            event_id='evt_fixture_known',
            calendar_id='fixture_primary',
            uid='fixture-primary-001@example.invalid',
            summary='Fixture Focus Block',
            location='Fixture Location Alpha',
            description='Synthetic fixture event. No personal data.',
            start_iso='2026-06-09T07:00:00Z',
            end_iso='2026-06-09T08:00:00Z',
            etag='"fixture-etag-001"',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/fixture-primary-001.ics',
        )

        refreshed = client.get_event(event)

        self.assertEqual(transport.calls[-1].kind, 'event_get')
        self.assertEqual(transport.calls[-1].method, 'GET')
        self.assertEqual(refreshed.uid, event.uid)
        self.assertEqual(refreshed.summary, event.summary)

    def test_event_search_is_local_bounded_and_does_not_call_transport_again(self) -> None:
        client, state, transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-09T00:00:00Z',
            end_iso='2026-06-10T00:00:00Z',
        )
        call_count = len(transport.calls)

        result = read_tools.event_search(state=state, query='focus', calendar_id=primary_id, limit=5)

        self.assertEqual(len(transport.calls), call_count)
        self.assertEqual(len(result.items), 1)
        self.assertEqual(result.items[0].summary, 'Fixture Focus Block')
        self.assertEqual(result.observation['event_count'], 1)
        self.assertTrue(result.observation['query_hash'])
        self.assertNotIn('focus', repr(result.observation).lower())
        self.assertContentFreeObservation(result.observation)

    def test_event_search_rejects_unbounded_pool(self) -> None:
        client, state, _transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-09T00:00:00Z',
            end_iso='2026-06-10T00:00:00Z',
        )

        with self.assertRaises(ReadToolValidationError):
            read_tools.event_search(state=state, query='fixture', max_pool=1)

    def test_observations_never_include_raw_ics_uid_etag_url_authorization_or_app_password(self) -> None:
        client, state, _transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        query_result = read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-09T00:00:00Z',
            end_iso='2026-06-10T00:00:00Z',
        )
        observations = [
            query_result.observation,
            read_tools.event_get(state=state, event_id=query_result.items[0].event_id).observation,
            read_tools.event_search(state=state, query='fixture', limit=2).observation,
        ]
        forbidden = (
            'BEGIN:VEVENT',
            'fixture-primary-001@example.invalid',
            'Fixture Focus Block',
            'Fixture Location Alpha',
            '/remote.php/dav/calendars/tof/fixture-primary/',
            'Authorization',
            'app-password',
        )

        for observation in observations:
            rendered = repr(observation)
            for marker in forbidden:
                self.assertNotIn(marker, rendered)
            self.assertFalse(observation_has_forbidden_shape(observation))

    def test_client_without_transport_refuses_networkless_operation(self) -> None:
        client = caldav_read_client.CalDavReadClient(transport=None)

        with self.assertRaises(CalDavTransportUnavailable):
            client.list_calendars()

    def test_agenda_modules_do_not_read_runtime_secret_on_import(self) -> None:
        with mock.patch.object(os, 'getenv', side_effect=AssertionError('secret env read is forbidden')):
            import agenda.caldav_read_client as read_client_module
            import agenda.ics_reader as ics_reader_module
            import agenda.observability as observability_module
            import agenda.read_tools as read_tools_module

            importlib.reload(observability_module)
            importlib.reload(ics_reader_module)
            importlib.reload(read_client_module)
            importlib.reload(read_tools_module)

    def test_agenda_files_stay_below_600_lines_and_no_generic_helpers(self) -> None:
        agenda_dir = APP_DIR / 'agenda'
        forbidden_names = {'utils.py', 'helpers.py'}
        for path in agenda_dir.glob('*.py'):
            self.assertNotIn(path.name, forbidden_names)
            line_count = len(path.read_text(encoding='utf-8').splitlines())
            self.assertLess(line_count, 600, path)

    def _calendar_id_by_name(self, state: AgendaReadState, display_name: str) -> str:
        for calendar in state.calendars.values():
            if calendar.display_name == display_name:
                return calendar.local_id
        raise AssertionError(f'missing calendar {display_name}')

    def assertContentFreeObservation(self, observation: dict) -> None:
        self.assertTrue(observation['content_free'])
        self.assertFalse(observation_has_forbidden_shape(observation))
        rendered = repr(observation)
        self.assertNotIn('BEGIN:VCALENDAR', rendered)
        self.assertNotIn('SUMMARY:', rendered)
        self.assertNotIn('LOCATION:', rendered)
        self.assertNotIn('DESCRIPTION:', rendered)
        self.assertNotIn('UID:', rendered)


if __name__ == '__main__':
    unittest.main()
