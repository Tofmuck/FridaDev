from __future__ import annotations

from datetime import datetime, timezone
from typing import Mapping

from agenda.caldav_models import CalendarEvent
from agenda.observability import sha256_12


def _unfold_ics_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in str(text or '').replace('\r\n', '\n').replace('\r', '\n').split('\n'):
        if not raw_line:
            continue
        if raw_line.startswith((' ', '\t')) and lines:
            lines[-1] = f'{lines[-1]}{raw_line[1:]}'
        else:
            lines.append(raw_line)
    return lines


def _split_property(line: str) -> tuple[str, str]:
    if ':' not in line:
        return line.strip().upper(), ''
    key, value = line.split(':', 1)
    name = key.split(';', 1)[0].strip().upper()
    return name, _unescape_text(value.strip())


def _unescape_text(value: str) -> str:
    return (
        str(value or '')
        .replace('\\n', '\n')
        .replace('\\N', '\n')
        .replace('\\,', ',')
        .replace('\\;', ';')
        .replace('\\\\', '\\')
    )


def _parse_ics_datetime(value: str) -> str:
    raw = str(value or '').strip()
    if not raw:
        return ''
    if raw.endswith('Z'):
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    elif 'T' in raw:
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    else:
        parsed = datetime.strptime(raw, '%Y%m%d').replace(tzinfo=timezone.utc)
    return parsed.isoformat().replace('+00:00', 'Z')


def parse_calendar_name(ics_text: str) -> str:
    for line in _unfold_ics_lines(ics_text):
        name, value = _split_property(line)
        if name == 'X-WR-CALNAME':
            return value
    return ''


def parse_family_calendar_flag(ics_text: str) -> bool:
    for line in _unfold_ics_lines(ics_text):
        name, value = _split_property(line)
        if name == 'X-FRIDA-RISK-FLAG' and value.strip().lower() == 'family_calendar':
            return True
    return False


def parse_ics_events(
    ics_text: str,
    *,
    calendar_id: str,
    timezone_name: str = 'UTC',
    default_etag: str = '',
    default_caldav_path: str = '',
) -> tuple[CalendarEvent, ...]:
    events: list[CalendarEvent] = []
    in_event = False
    current: dict[str, str] = {}
    for line in _unfold_ics_lines(ics_text):
        name, value = _split_property(line)
        if name == 'BEGIN' and value.upper() == 'VEVENT':
            in_event = True
            current = {}
            continue
        if name == 'END' and value.upper() == 'VEVENT':
            if in_event:
                event = _event_from_props(
                    current,
                    calendar_id=calendar_id,
                    timezone_name=timezone_name,
                    default_etag=default_etag,
                    default_caldav_path=default_caldav_path,
                )
                if event is not None:
                    events.append(event)
            in_event = False
            current = {}
            continue
        if in_event:
            current[name] = value
    return tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))


def _event_from_props(
    props: Mapping[str, str],
    *,
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
) -> CalendarEvent | None:
    uid = str(props.get('UID') or '').strip()
    start_iso = _parse_ics_datetime(str(props.get('DTSTART') or ''))
    end_iso = _parse_ics_datetime(str(props.get('DTEND') or ''))
    if not uid or not start_iso or not end_iso:
        return None
    event_id = f'evt_{sha256_12(f"{calendar_id}:{uid}")}'
    return CalendarEvent(
        event_id=event_id,
        calendar_id=str(calendar_id),
        uid=uid,
        summary=str(props.get('SUMMARY') or ''),
        location=str(props.get('LOCATION') or ''),
        description=str(props.get('DESCRIPTION') or ''),
        start_iso=start_iso,
        end_iso=end_iso,
        timezone=str(timezone_name or 'UTC'),
        etag=str(default_etag or ''),
        caldav_path=str(default_caldav_path or ''),
    )
