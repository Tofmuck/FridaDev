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

from agenda import agent_contract, caldav_read_client, ics_reader, product_methods, read_tools, response_rendering
from agenda.caldav_models import (
    AgendaReadState,
    CalDavReadError,
    CalDavResponse,
    CalDavTransportUnavailable,
    CalendarEvent,
    CalendarSummary,
    ReadToolValidationError,
)
from agenda.observability import observation_has_forbidden_shape


FIXTURE_DIR = APP_DIR / 'docs' / 'states' / 'baselines' / 'agenda-fixtures'
PRIMARY_ICS = (FIXTURE_DIR / 'anonymous-primary-calendar.ics').read_text(encoding='utf-8')
SHARED_ICS = (FIXTURE_DIR / 'anonymous-shared-calendar.ics').read_text(encoding='utf-8')

RECURRENCE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
X-WR-CALNAME:Fixture Recurrence Calendar
BEGIN:VEVENT
UID:fixture-recurring-001@example.invalid
DTSTART:20260601T070000Z
DTEND:20260601T073000Z
RRULE:FREQ=DAILY;COUNT=10
EXDATE:20260603T070000Z
SUMMARY:Fixture Daily Check
LOCATION:Fixture Location Gamma
DESCRIPTION:Synthetic recurring fixture event. No personal data.
END:VEVENT
BEGIN:VEVENT
UID:fixture-recurring-001@example.invalid
RECURRENCE-ID:20260604T070000Z
DTSTART:20260604T090000Z
DTEND:20260604T093000Z
SUMMARY:Fixture Daily Check Moved
LOCATION:Fixture Location Delta
DESCRIPTION:Synthetic recurring override. No personal data.
END:VEVENT
END:VCALENDAR
"""


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
    def __init__(
        self,
        *,
        report_text: str | None = None,
        event_get_text: str | None = None,
        status_by_kind: dict[str, int] | None = None,
        body_by_kind: dict[str, str] | None = None,
    ) -> None:
        self.calls = []
        self.report_text = report_text
        self.event_get_text = event_get_text
        self.status_by_kind = status_by_kind or {}
        self.body_by_kind = body_by_kind or {}

    def __call__(self, request):
        self.calls.append(request)
        status_code = self.status_by_kind.get(request.kind)
        body = self.body_by_kind.get(request.kind)
        if request.kind == 'calendar_list':
            return CalDavResponse(status_code=status_code or 207, text=body or CALENDAR_PROPFIND_XML)
        if request.kind == 'event_query_range':
            if body is not None:
                return CalDavResponse(status_code=status_code or 207, text=body)
            if self.report_text is not None:
                return CalDavResponse(status_code=status_code or 207, text=self.report_text)
            if 'fixture-shared' in request.url:
                return CalDavResponse(status_code=status_code or 207, text=SHARED_ICS)
            return CalDavResponse(status_code=status_code or 207, text=PRIMARY_ICS)
        if request.kind == 'event_get':
            return CalDavResponse(status_code=status_code or 200, text=body or self.event_get_text or PRIMARY_ICS)
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

    def test_parse_ics_events_preserves_tzid_for_local_time_rendering(self) -> None:
        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:fixture-tzid-001@example.invalid
DTSTART;TZID=Europe/Paris:20260608T090000
DTEND;TZID=Europe/Paris:20260608T100000
SUMMARY:Fixture TZID Block
LOCATION:Fixture Location TZ
DESCRIPTION:Synthetic fixture event. No personal data.
END:VEVENT
END:VCALENDAR
"""

        events = ics_reader.parse_ics_events(
            ics_text,
            calendar_id='fixture_primary',
            timezone_name='UTC',
        )
        rendered = response_rendering.render_readonly_answer(
            plan=self._read_today_plan(),
            execution_result=_ExecutionResultFixture(events),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start_iso, '2026-06-08T07:00:00Z')
        self.assertEqual(events[0].end_iso, '2026-06-08T08:00:00Z')
        self.assertEqual(events[0].timezone, 'Europe/Paris')
        self.assertFalse(events[0].all_day)
        self.assertIn('09:00-10:00', rendered)
        self.assertNotIn('11:00-12:00', rendered)

    def test_parse_ics_events_renders_value_date_as_all_day(self) -> None:
        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:fixture-all-day-001@example.invalid
DTSTART;VALUE=DATE:20260608
DTEND;VALUE=DATE:20260609
SUMMARY:Fixture All Day Block
LOCATION:Fixture Location Day
DESCRIPTION:Synthetic fixture event. No personal data.
END:VEVENT
END:VCALENDAR
"""

        events = ics_reader.parse_ics_events(
            ics_text,
            calendar_id='fixture_primary',
            timezone_name='Europe/Paris',
        )
        rendered = response_rendering.render_readonly_answer(
            plan=self._read_today_plan(),
            execution_result=_ExecutionResultFixture(events),
        )

        self.assertEqual(len(events), 1)
        self.assertTrue(events[0].all_day)
        self.assertEqual(events[0].start_iso, '2026-06-07T22:00:00Z')
        self.assertEqual(events[0].end_iso, '2026-06-08T22:00:00Z')
        self.assertIn('Toute la journee', rendered)
        self.assertNotIn('02:00-02:00', rendered)

    def test_utc_event_still_renders_in_requested_timezone(self) -> None:
        ics_text = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:fixture-utc-001@example.invalid
DTSTART:20260608T070000Z
DTEND:20260608T080000Z
SUMMARY:Fixture UTC Block
LOCATION:Fixture Location UTC
DESCRIPTION:Synthetic fixture event. No personal data.
END:VEVENT
END:VCALENDAR
"""

        events = ics_reader.parse_ics_events(
            ics_text,
            calendar_id='fixture_primary',
            timezone_name='Europe/Paris',
        )
        rendered = response_rendering.render_readonly_answer(
            plan=self._read_today_plan(),
            execution_result=_ExecutionResultFixture(events),
        )

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].start_iso, '2026-06-08T07:00:00Z')
        self.assertEqual(events[0].timezone, 'Europe/Paris')
        self.assertIn('09:00-10:00', rendered)
        self.assertNotIn('07:00-08:00', rendered)

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

    def test_event_query_range_expands_bounded_recurrences_and_overrides(self) -> None:
        transport = FakeReadTransport(report_text=RECURRENCE_ICS)
        client = caldav_read_client.CalDavReadClient(transport=transport)
        state = AgendaReadState()
        read_tools.calendar_list(client, state=state)
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')

        result = read_tools.event_query_range(
            client,
            state=state,
            calendar_id=primary_id,
            start_iso='2026-06-02T00:00:00Z',
            end_iso='2026-06-05T00:00:00Z',
        )

        self.assertEqual([event.start_iso for event in result.items], [
            '2026-06-02T07:00:00Z',
            '2026-06-04T09:00:00Z',
        ])
        self.assertEqual(len({event.event_id for event in result.items}), 2)
        self.assertEqual(result.items[1].summary, 'Fixture Daily Check Moved')
        self.assertNotIn('2026-06-03T07:00:00Z', [event.start_iso for event in result.items])
        self.assertContentFreeObservation(result.observation)

    def test_parse_ics_events_supports_basic_rrule_frequencies(self) -> None:
        cases = (
            ('DAILY', '20260601T070000Z', '20260601T073000Z', '2026-06-02T07:00:00Z'),
            ('WEEKLY', '20260601T070000Z', '20260601T073000Z', '2026-06-08T07:00:00Z'),
            ('MONTHLY', '20260601T070000Z', '20260601T073000Z', '2026-07-01T07:00:00Z'),
            ('YEARLY', '20260601T070000Z', '20260601T073000Z', '2027-06-01T07:00:00Z'),
        )

        for freq, start, end, expected_second_start in cases:
            with self.subTest(freq=freq):
                events = ics_reader.parse_ics_events(
                    self._recurrence_ics(freq=freq, start=start, end=end),
                    calendar_id='fixture_recurrence',
                    window_start_iso='2026-06-01T00:00:00Z',
                    window_end_iso='2028-01-01T00:00:00Z',
                )
                self.assertGreaterEqual(len(events), 2)
                self.assertEqual(events[1].start_iso, expected_second_start)
                self.assertEqual(len({event.event_id for event in events[:2]}), 2)

    def test_parse_ics_events_supports_realistic_byday_and_bymonth_rules(self) -> None:
        cases = (
            (
                'weekly_byday_monday',
                'FREQ=WEEKLY;COUNT=2;BYDAY=MO',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-06-16T00:00:00Z',
                ['2026-06-01T07:00:00Z', '2026-06-08T07:00:00Z'],
            ),
            (
                'weekly_byday_monday_wednesday',
                'FREQ=WEEKLY;COUNT=4;BYDAY=MO,WE',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-06-11T00:00:00Z',
                [
                    '2026-06-01T07:00:00Z',
                    '2026-06-03T07:00:00Z',
                    '2026-06-08T07:00:00Z',
                    '2026-06-10T07:00:00Z',
                ],
            ),
            (
                'monthly_bymonthday',
                'FREQ=MONTHLY;COUNT=2;BYMONTHDAY=15',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-08-01T00:00:00Z',
                ['2026-06-15T07:00:00Z', '2026-07-15T07:00:00Z'],
            ),
            (
                'monthly_byday',
                'FREQ=MONTHLY;COUNT=3;BYDAY=MO',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-07-01T00:00:00Z',
                ['2026-06-01T07:00:00Z', '2026-06-08T07:00:00Z', '2026-06-15T07:00:00Z'],
            ),
            (
                'monthly_byday_bysetpos',
                'FREQ=MONTHLY;COUNT=2;BYDAY=MO;BYSETPOS=1',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-08-01T00:00:00Z',
                ['2026-06-01T07:00:00Z', '2026-07-06T07:00:00Z'],
            ),
            (
                'yearly_bymonth_bymonthday',
                'FREQ=YEARLY;COUNT=2;BYMONTH=6;BYMONTHDAY=15',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2028-01-01T00:00:00Z',
                ['2026-06-15T07:00:00Z', '2027-06-15T07:00:00Z'],
            ),
            (
                'weekly_interval',
                'FREQ=WEEKLY;COUNT=2;INTERVAL=2;BYDAY=MO',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-06-22T00:00:00Z',
                ['2026-06-01T07:00:00Z', '2026-06-15T07:00:00Z'],
            ),
            (
                'weekly_until',
                'FREQ=WEEKLY;UNTIL=20260615T070000Z;BYDAY=MO',
                '20260601T070000Z',
                '20260601T073000Z',
                '2026-06-01T00:00:00Z',
                '2026-06-30T00:00:00Z',
                ['2026-06-01T07:00:00Z', '2026-06-08T07:00:00Z', '2026-06-15T07:00:00Z'],
            ),
        )

        for label, rule, start, end, window_start, window_end, expected_starts in cases:
            with self.subTest(label=label):
                events = ics_reader.parse_ics_events(
                    self._recurrence_ics(freq=label, start=start, end=end, rule=rule),
                    calendar_id='fixture_recurrence',
                    window_start_iso=window_start,
                    window_end_iso=window_end,
                )
                self.assertEqual([event.start_iso for event in events], expected_starts)
                self.assertEqual(len({event.event_id for event in events}), len(events))
                self.assertTrue(all(window_start <= event.start_iso < window_end for event in events))

    def test_unsupported_recurrence_rule_fails_without_raw_payload(self) -> None:
        cases = (
            ('unsupported_part', 'FREQ=DAILY;COUNT=2;BYHOUR=7'),
            ('unsupported_bysetpos_frequency', 'FREQ=WEEKLY;COUNT=2;BYDAY=MO,WE;BYSETPOS=1'),
        )
        for label, rule in cases:
            with self.subTest(label=label):
                with self.assertRaises(ics_reader.IcsRecurrenceUnsupportedError) as raised:
                    ics_reader.parse_ics_events(
                        self._recurrence_ics(
                            freq=label,
                            start='20260601T070000Z',
                            end='20260601T073000Z',
                            rule=rule,
                        ),
                        calendar_id='fixture_recurrence',
                        window_start_iso='2026-06-01T00:00:00Z',
                        window_end_iso='2026-06-03T00:00:00Z',
                    )
                self.assertNotIn('BEGIN:VEVENT', str(raised.exception))
                self.assertNotIn('fixture-recurring', str(raised.exception))

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

    def test_event_get_uses_fake_transport_get_when_caldav_path_is_known(self) -> None:
        client, state, transport = self._client_and_state()
        primary_id = self._calendar_id_by_name(state, 'Fixture Primary Calendar')
        event = CalendarEvent(
            event_id='evt_5d91a151b0b7',
            calendar_id=primary_id,
            uid='fixture-primary-001@example.invalid',
            summary='Fixture Focus Block',
            location='Fixture Location Alpha',
            description='Synthetic fixture event. No personal data.',
            start_iso='2026-06-09T07:00:00Z',
            end_iso='2026-06-09T08:00:00Z',
            etag='"fixture-etag-001"',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/fixture-primary-001.ics',
        )
        state.add_events((event,))

        get_result = read_tools.event_get(
            state=state,
            event_id=event.event_id,
            client=client,
        )

        self.assertEqual(transport.calls[-1].kind, 'event_get')
        self.assertEqual(transport.calls[-1].method, 'GET')
        self.assertEqual(get_result.observation['reason_code'], 'caldav_get')
        self.assertContentFreeObservation(get_result.observation)

    def test_event_get_with_client_rejects_missing_caldav_path(self) -> None:
        client, state, _transport = self._client_and_state()
        event = CalendarEvent(
            event_id='evt_fixture_without_path',
            calendar_id=next(iter(state.calendars)),
            uid='fixture-without-path@example.invalid',
            summary='Fixture Missing Path',
            location='Fixture Location',
            description='Synthetic fixture event. No personal data.',
            start_iso='2026-06-09T07:00:00Z',
            end_iso='2026-06-09T08:00:00Z',
        )
        state.add_events((event,))

        with self.assertRaises(ReadToolValidationError):
            read_tools.event_get(state=state, event_id=event.event_id, client=client)

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

    def test_read_client_rejects_http_statuses_with_content_free_error(self) -> None:
        raw_body = 'RAW SERVER BODY BEGIN:VEVENT UID:fixture-leak SUMMARY:should-not-leak'
        for status_code in (401, 403, 404, 500):
            with self.subTest(status_code=status_code):
                transport = FakeReadTransport(
                    status_by_kind={'calendar_list': status_code},
                    body_by_kind={'calendar_list': raw_body},
                )
                client = caldav_read_client.CalDavReadClient(transport=transport)

                with self.assertRaises(CalDavReadError) as raised:
                    client.list_calendars()

                rendered = str(raised.exception)
                self.assertNotIn(raw_body, rendered)
                self.assertNotIn('BEGIN:VEVENT', rendered)
                self.assertContentFreeObservation(raised.exception.to_observation())

    def test_read_client_get_requires_http_200_without_body_leak(self) -> None:
        raw_body = 'RAW SERVER BODY LOCATION:should-not-leak app-password'
        transport = FakeReadTransport(
            status_by_kind={'event_get': 404},
            body_by_kind={'event_get': raw_body},
        )
        client = caldav_read_client.CalDavReadClient(transport=transport)
        event = CalendarEvent(
            event_id='evt_fixture_known',
            calendar_id='fixture_primary',
            uid='fixture-primary-001@example.invalid',
            summary='Fixture Focus Block',
            location='Fixture Location Alpha',
            description='Synthetic fixture event. No personal data.',
            start_iso='2026-06-09T07:00:00Z',
            end_iso='2026-06-09T08:00:00Z',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/fixture-primary-001.ics',
        )

        with self.assertRaises(CalDavReadError) as raised:
            client.get_event(event)

        rendered = str(raised.exception)
        self.assertNotIn(raw_body, rendered)
        self.assertNotIn('app-password', rendered)
        self.assertContentFreeObservation(raised.exception.to_observation())

    def test_read_client_report_requires_http_207_without_body_leak(self) -> None:
        raw_body = 'RAW REPORT BODY UID:fixture-leak LOCATION:should-not-leak'
        transport = FakeReadTransport(
            status_by_kind={'event_query_range': 500},
            body_by_kind={'event_query_range': raw_body},
        )
        client = caldav_read_client.CalDavReadClient(transport=transport)
        calendar = CalendarSummary(
            local_id='cal_fixture_primary',
            display_name='Fixture Primary Calendar',
            caldav_path='/remote.php/dav/calendars/tof/fixture-primary/',
        )

        with self.assertRaises(CalDavReadError) as raised:
            client.query_calendar_events(
                calendar,
                start_iso='2026-06-09T00:00:00Z',
                end_iso='2026-06-10T00:00:00Z',
            )

        rendered = str(raised.exception)
        self.assertNotIn(raw_body, rendered)
        self.assertNotIn('LOCATION:', rendered)
        self.assertContentFreeObservation(raised.exception.to_observation())

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
            import agenda.rrule_expander as rrule_expander_module

            importlib.reload(observability_module)
            importlib.reload(rrule_expander_module)
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

    def _recurrence_ics(
        self,
        *,
        freq: str,
        start: str,
        end: str,
        extra_rule: str = '',
        rule: str = '',
    ) -> str:
        rule = rule or f'FREQ={freq};COUNT=2;INTERVAL=1'
        if extra_rule:
            rule = f'{rule};{extra_rule}'
        return f"""BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:fixture-recurring-{freq.lower()}@example.invalid
DTSTART:{start}
DTEND:{end}
RRULE:{rule}
SUMMARY:Fixture Recurrence {freq}
LOCATION:Fixture Location
DESCRIPTION:Synthetic fixture event. No personal data.
END:VEVENT
END:VCALENDAR
"""

    def _read_today_plan(self) -> agent_contract.AgendaAgentPlan:
        return agent_contract.AgendaAgentPlan(
            product_method=product_methods.METHOD_READ_TODAY,
            intent='read agenda day',
            calendar_scope={'calendar_ids': ['fixture_primary'], 'family_calendar': False, 'ambiguity': 'none'},
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

    def assertContentFreeObservation(self, observation: dict) -> None:
        self.assertTrue(observation['content_free'])
        self.assertFalse(observation_has_forbidden_shape(observation))
        rendered = repr(observation)
        self.assertNotIn('BEGIN:VCALENDAR', rendered)
        self.assertNotIn('SUMMARY:', rendered)
        self.assertNotIn('LOCATION:', rendered)
        self.assertNotIn('DESCRIPTION:', rendered)
        self.assertNotIn('UID:', rendered)


class _ExecutionResultFixture:
    def __init__(self, events: tuple[CalendarEvent, ...]) -> None:
        self.status = 'ok'
        self.events = tuple(events)
        self.observation = {'content_free': True}


if __name__ == '__main__':
    unittest.main()
