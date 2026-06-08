from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping

from agenda.caldav_models import CalendarEvent, CalendarSummary


OBSERVATION_SCHEMA_VERSION = 'frida_agenda_read_tools_observation_v1'

FORBIDDEN_CONTENT_MARKERS = (
    'BEGIN:VCALENDAR',
    'BEGIN:VEVENT',
    'END:VEVENT',
    'UID:',
    'DTSTART:',
    'DTEND:',
    'SUMMARY:',
    'LOCATION:',
    'DESCRIPTION:',
    'Authorization',
    'app-password',
    'cookie',
)

FORBIDDEN_OBSERVATION_KEYS = {
    'uid',
    'etag',
    'url',
    'href',
    'caldav_path',
    'caldav_url',
    'ics',
    'raw_ics',
    'summary',
    'title',
    'location',
    'description',
    'attendee',
    'authorization',
    'cookie',
    'app_password',
}


def sha256_12(value: Any) -> str:
    return hashlib.sha256(str(value or '').encode('utf-8')).hexdigest()[:12]


def _calendar_hashes(calendars: Iterable[CalendarSummary]) -> list[str]:
    return [sha256_12(calendar.local_id) for calendar in calendars]


def _event_hashes(events: Iterable[CalendarEvent]) -> list[str]:
    return [sha256_12(event.event_id) for event in events]


def build_tool_observation(
    *,
    tool_name: str,
    status: str,
    calendars: Iterable[CalendarSummary] = (),
    events: Iterable[CalendarEvent] = (),
    window_start: str = '',
    window_end: str = '',
    timezone: str = '',
    reason_code: str = '',
    query: str = '',
    selected_event_id: str = '',
) -> dict[str, Any]:
    calendar_tuple = tuple(calendars)
    event_tuple = tuple(events)
    calendar_ids = tuple(calendar.local_id for calendar in calendar_tuple)
    return {
        'schema_version': OBSERVATION_SCHEMA_VERSION,
        'tool_name': str(tool_name),
        'status': str(status),
        'reason_code': str(reason_code or ''),
        'calendar_count': len(calendar_tuple),
        'calendar_id_hashes': _calendar_hashes(calendar_tuple),
        'event_count': len(event_tuple),
        'event_id_hashes': _event_hashes(event_tuple),
        'selected_event_hash': sha256_12(selected_event_id) if selected_event_id else '',
        'query_hash': sha256_12(query) if query else '',
        'window_start': str(window_start or ''),
        'window_end': str(window_end or ''),
        'timezone': str(timezone or ''),
        'family_calendar_present': any(calendar.family_calendar for calendar in calendar_tuple),
        'readonly': all(calendar.readonly for calendar in calendar_tuple) if calendar_tuple else True,
        'caldav_access': False,
        'nextcloud_access': False,
        'mutation_attempted': False,
        'content_free': True,
        'redacted': True,
        'calendar_ids_present': bool(calendar_ids),
    }


def observation_has_forbidden_shape(observation: Mapping[str, Any]) -> bool:
    def walk(value: Any) -> bool:
        if isinstance(value, Mapping):
            for key, item in value.items():
                if str(key).lower() in FORBIDDEN_OBSERVATION_KEYS:
                    return True
                if walk(item):
                    return True
            return False
        if isinstance(value, (list, tuple, set)):
            return any(walk(item) for item in value)
        text = str(value)
        return any(marker in text for marker in FORBIDDEN_CONTENT_MARKERS)

    return walk(observation)
