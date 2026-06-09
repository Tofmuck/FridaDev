from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def build_event_ics(
    draft: Mapping[str, Any],
    *,
    uid: str,
    now_iso: str,
) -> str:
    event = _event_values(draft)
    timestamp = _ics_utc_timestamp(now_iso) or _ics_utc_timestamp(datetime.now(timezone.utc).isoformat())
    lines = [
        'BEGIN:VCALENDAR',
        'VERSION:2.0',
        'PRODID:-//FridaDev//Frida Agenda//EN',
        'CALSCALE:GREGORIAN',
        'BEGIN:VEVENT',
        f'UID:{_escape_text(uid)}',
        f'DTSTAMP:{timestamp}',
        f'CREATED:{timestamp}',
        f'LAST-MODIFIED:{timestamp}',
        *_time_lines(event),
        f'SUMMARY:{_escape_text(event["title"])}',
    ]
    if event['location']:
        lines.append(f'LOCATION:{_escape_text(event["location"])}')
    if event['description']:
        lines.append(f'DESCRIPTION:{_escape_text(event["description"])}')
    lines.extend(['END:VEVENT', 'END:VCALENDAR', ''])
    return '\r\n'.join(lines)


def _event_values(draft: Mapping[str, Any]) -> dict[str, Any]:
    target = _mapping(draft.get('target'))
    return {
        'title': _text(draft.get('title')) or _text(target.get('title')) or 'Evenement',
        'location': _text(draft.get('location')) or _text(target.get('location')),
        'description': _text(draft.get('description')) or _text(target.get('description')),
        'start': _text(draft.get('start')) or _text(target.get('start')),
        'end': _text(draft.get('end')) or _text(target.get('end')),
        'timezone': _text(draft.get('timezone')) or _text(target.get('timezone')) or 'UTC',
        'all_day': bool(draft.get('all_day')) if draft.get('all_day') is not None else bool(target.get('all_day')),
    }


def _time_lines(event: Mapping[str, Any]) -> list[str]:
    if bool(event.get('all_day')):
        return [
            f'DTSTART;VALUE=DATE:{_local_date(event.get("start"), event.get("timezone"))}',
            f'DTEND;VALUE=DATE:{_local_date(event.get("end"), event.get("timezone"))}',
        ]
    start = _ics_utc_timestamp(str(event.get('start') or ''))
    end = _ics_utc_timestamp(str(event.get('end') or ''))
    return [f'DTSTART:{start}', f'DTEND:{end}']


def _ics_utc_timestamp(value: str) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return ''
    return parsed.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _local_date(value: Any, timezone_name: Any) -> str:
    parsed = _parse_iso(str(value or ''))
    if parsed is None:
        return ''
    return parsed.astimezone(_zoneinfo(timezone_name)).strftime('%Y%m%d')


def _parse_iso(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def _zoneinfo(value: Any):
    raw = str(value or '').strip()
    if not raw:
        return timezone.utc
    try:
        return ZoneInfo(raw)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def _escape_text(value: Any) -> str:
    return (
        str(value or '')
        .replace('\\', '\\\\')
        .replace('\n', '\\n')
        .replace('\r', '')
        .replace(';', '\\;')
        .replace(',', '\\,')
    )


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or '').strip()
