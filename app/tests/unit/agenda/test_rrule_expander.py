from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from agenda import agent_contract, product_methods, read_execution, rrule_expander
from agenda.caldav_models import CalDavResponse
from agenda.caldav_read_client import CalDavReadClient


_CALENDAR_PROPFIND_XML = """<?xml version="1.0" encoding="UTF-8"?>
<d:multistatus xmlns:d="DAV:">
  <d:response>
    <d:href>/synthetic-calendar/</d:href>
    <d:propstat><d:prop><d:displayname>Synthetic Calendar</d:displayname></d:prop></d:propstat>
  </d:response>
</d:multistatus>
"""

_OUT_OF_DOMAIN_RECURRENCE_ICS = """BEGIN:VCALENDAR
VERSION:2.0
BEGIN:VEVENT
UID:synthetic-recurrence@example.invalid
DTSTART:99990101T090000Z
DTEND:99990101T100000Z
RRULE:FREQ=YEARLY;COUNT=2;INTERVAL=2
SUMMARY:Synthetic recurrence
END:VEVENT
END:VCALENDAR
"""


class RRuleExpanderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.start = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
        self.duration = timedelta(hours=1)

    def test_extreme_yearly_count_returns_first_occurrence_without_advancing_period(self) -> None:
        with mock.patch.object(
            rrule_expander,
            '_add_interval',
            wraps=rrule_expander._add_interval,
        ) as add_interval:
            occurrences = self._expand(
                rule='FREQ=YEARLY;COUNT=1;INTERVAL=2',
                window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                window_end=datetime(2026, 1, 2, tzinfo=timezone.utc),
            )

        self.assertEqual(occurrences, [self.start])
        self.assertEqual(add_interval.call_count, 0)

    def test_until_and_short_window_stop_period_iteration_independently(self) -> None:
        cases = (
            (
                'until',
                'FREQ=DAILY;UNTIL=20260101T090000Z',
                None,
                None,
                0,
            ),
            (
                'window',
                'FREQ=DAILY',
                datetime(2026, 1, 1, tzinfo=timezone.utc),
                datetime(2026, 1, 2, tzinfo=timezone.utc),
                1,
            ),
        )
        for label, rule, window_start, window_end, expected_advances in cases:
            with self.subTest(label=label):
                with mock.patch.object(
                    rrule_expander,
                    '_add_interval',
                    wraps=rrule_expander._add_interval,
                ) as add_interval:
                    occurrences = self._expand(
                        rule=rule,
                        window_start=window_start,
                        window_end=window_end,
                    )

                self.assertEqual(occurrences, [self.start])
                self.assertEqual(add_interval.call_count, expected_advances)

    def test_count_exhausted_before_window_returns_empty_without_scanning_window(self) -> None:
        with mock.patch.object(
            rrule_expander,
            '_add_interval',
            wraps=rrule_expander._add_interval,
        ) as add_interval:
            occurrences = self._expand(
                rule='FREQ=DAILY;COUNT=2',
                window_start=datetime(2030, 1, 1, tzinfo=timezone.utc),
                window_end=datetime(2030, 1, 2, tzinfo=timezone.utc),
            )

        self.assertEqual(occurrences, [])
        self.assertEqual(add_interval.call_count, 1)

    def test_count_tracks_filtered_leap_day_occurrences_not_yearly_periods(self) -> None:
        occurrences = rrule_expander.expand_recurrence_starts(
            start_dt=datetime(2023, 1, 1, 9, tzinfo=timezone.utc),
            duration=self.duration,
            rrule_value='FREQ=YEARLY;COUNT=2;BYMONTH=2;BYMONTHDAY=29',
            window_start=datetime(2023, 1, 1, tzinfo=timezone.utc),
            window_end=datetime(2029, 1, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(
            occurrences,
            [
                datetime(2024, 2, 29, 9, tzinfo=timezone.utc),
                datetime(2028, 2, 29, 9, tzinfo=timezone.utc),
            ],
        )

    def test_occurrence_limit_still_raises_at_512_matches(self) -> None:
        with self.assertRaisesRegex(
            rrule_expander.IcsRecurrenceUnsupportedError,
            'recurrence expansion exceeded bounded limit',
        ):
            self._expand(
                rule='FREQ=DAILY',
                window_start=datetime(2026, 1, 1, tzinfo=timezone.utc),
                window_end=datetime(2028, 1, 1, tzinfo=timezone.utc),
            )

    def test_calendar_domain_exhaustion_uses_closed_recurrence_error(self) -> None:
        with self.assertRaisesRegex(
            rrule_expander.IcsRecurrenceUnsupportedError,
            'recurrence expansion exceeds the calendar domain',
        ):
            rrule_expander.expand_recurrence_starts(
                start_dt=datetime(9999, 1, 1, 9, tzinfo=timezone.utc),
                duration=self.duration,
                rrule_value='FREQ=YEARLY;COUNT=2;INTERVAL=2',
                window_start=None,
                window_end=None,
            )

    def test_calendar_domain_window_boundary_uses_closed_recurrence_error(self) -> None:
        with self.assertRaisesRegex(
            rrule_expander.IcsRecurrenceUnsupportedError,
            'recurrence expansion exceeds the calendar domain',
        ):
            rrule_expander.expand_recurrence_starts(
                start_dt=datetime(9999, 1, 1, 9, tzinfo=timezone.utc),
                duration=self.duration,
                rrule_value='FREQ=YEARLY',
                window_start=datetime(9999, 1, 1, tzinfo=timezone.utc),
                window_end=datetime(9999, 1, 2, tzinfo=timezone.utc),
            )

    def test_calendar_domain_occurrence_end_uses_closed_recurrence_error(self) -> None:
        with self.assertRaisesRegex(
            rrule_expander.IcsRecurrenceUnsupportedError,
            'recurrence expansion exceeds the calendar domain',
        ):
            rrule_expander.expand_recurrence_starts(
                start_dt=datetime(9998, 12, 31, 23, 30, tzinfo=timezone.utc),
                duration=self.duration,
                rrule_value='FREQ=YEARLY;COUNT=2',
                window_start=datetime(9998, 1, 1, tzinfo=timezone.utc),
                window_end=datetime.max.replace(tzinfo=timezone.utc),
            )

    def test_agenda_read_execution_classifies_calendar_domain_exhaustion(self) -> None:
        def transport(request):
            if request.kind == 'calendar_list':
                return CalDavResponse(status_code=207, text=_CALENDAR_PROPFIND_XML)
            if request.kind == 'event_query_range':
                return CalDavResponse(status_code=207, text=_OUT_OF_DOMAIN_RECURRENCE_ICS)
            raise AssertionError(f'unexpected request kind: {request.kind}')

        execution = read_execution.execute_readonly_plan(
            self._read_plan(),
            client=CalDavReadClient(transport=transport),
            live_caldav=True,
        )

        self.assertEqual(execution.status, read_execution.STATUS_ERROR)
        self.assertEqual(execution.reason_code, read_execution.REASON_TOOL_ERROR)
        self.assertEqual(execution.error_class, 'IcsRecurrenceUnsupportedError')
        self.assertTrue(execution.caldav_access)
        self.assertFalse(execution.mutation_attempted)

    def _expand(
        self,
        *,
        rule: str,
        window_start: datetime | None,
        window_end: datetime | None,
    ) -> list[datetime]:
        return rrule_expander.expand_recurrence_starts(
            start_dt=self.start,
            duration=self.duration,
            rrule_value=rule,
            window_start=window_start,
            window_end=window_end,
        )

    def _read_plan(self) -> agent_contract.AgendaAgentPlan:
        return agent_contract.AgendaAgentPlan(
            product_method=product_methods.METHOD_READ_EXPLICIT_DATE,
            intent='read synthetic recurrence',
            calendar_scope={'calendar_ids': [], 'family_calendar': False, 'ambiguity': 'none'},
            time_scope={
                'kind': 'day',
                'start': '9999-01-01T00:00:00Z',
                'end': '9999-01-02T00:00:00Z',
                'timezone': 'UTC',
                'ambiguity': 'none',
            },
            tool_calls=(
                agent_contract.AgendaToolCall(
                    tool_name=product_methods.TOOL_EVENT_QUERY_RANGE,
                    method='GET',
                    params={
                        'calendar_id': '',
                        'start': '9999-01-01T00:00:00Z',
                        'end': '9999-01-02T00:00:00Z',
                        'timezone': 'UTC',
                    },
                ),
            ),
            draft={},
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
            surface_error='Je n ai pas pu relire cette recurrence.',
            surface_outro='',
        )


if __name__ == '__main__':
    unittest.main()
