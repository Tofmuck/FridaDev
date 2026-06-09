from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


REASON_ICS_SOURCE_MISSING = 'agenda_write_ics_source_missing'
REASON_ICS_PRESERVATION_REQUIRED = 'agenda_write_update_preservation_required'


class IcsPatchError(ValueError):
    def __init__(self, reason_code: str) -> None:
        self.reason_code = str(reason_code or REASON_ICS_PRESERVATION_REQUIRED)
        super().__init__(self.reason_code)


def patch_event_ics(source_ics: str, draft: Mapping[str, Any], *, now_iso: str = '') -> str:
    del now_iso
    lines = _unfold_ics_lines(source_ics)
    if not lines:
        raise IcsPatchError(REASON_ICS_SOURCE_MISSING)
    bounds = _event_bounds(lines)
    if bounds is None:
        raise IcsPatchError(REASON_ICS_PRESERVATION_REQUIRED)
    event_start, event_end = bounds
    event_lines = list(lines[event_start + 1:event_end])

    time_lines = _time_lines_for_update(draft)
    if time_lines:
        event_lines = _replace_property_group(event_lines, {'DTSTART', 'DTEND'}, time_lines)

    for name, value in (
        ('SUMMARY', _text(draft.get('title'))),
        ('LOCATION', _text(draft.get('location'))),
        ('DESCRIPTION', _text(draft.get('description'))),
    ):
        if value:
            event_lines = _replace_property_group(event_lines, {name}, [f'{name}:{_escape_text(value)}'])

    patched = [*lines[:event_start + 1], *event_lines, *lines[event_end:]]
    return '\r\n'.join(patched) + '\r\n'


def _time_lines_for_update(draft: Mapping[str, Any]) -> list[str]:
    target = _mapping(draft.get('target'))
    requested_start = _text(draft.get('start'))
    requested_end = _text(draft.get('end'))
    if not requested_start and not requested_end:
        return []
    start = requested_start or _text(target.get('start'))
    end = requested_end or _text(target.get('end'))
    timezone_name = _text(draft.get('timezone')) or _text(target.get('timezone')) or 'UTC'
    all_day = bool(draft.get('all_day')) if draft.get('all_day') is not None else bool(target.get('all_day'))
    if all_day:
        start_date = _local_date(start, timezone_name)
        end_date = _local_date(end, timezone_name)
        if not start_date or not end_date:
            raise IcsPatchError(REASON_ICS_PRESERVATION_REQUIRED)
        return [f'DTSTART;VALUE=DATE:{start_date}', f'DTEND;VALUE=DATE:{end_date}']
    start_stamp = _ics_utc_timestamp(start)
    end_stamp = _ics_utc_timestamp(end)
    if not start_stamp or not end_stamp:
        raise IcsPatchError(REASON_ICS_PRESERVATION_REQUIRED)
    return [f'DTSTART:{start_stamp}', f'DTEND:{end_stamp}']


def _replace_property_group(event_lines: list[str], names: set[str], replacement_lines: list[str]) -> list[str]:
    indices = _matching_top_level_indices(event_lines, names)
    insert_at = min(indices) if indices else len(event_lines)
    removed = set(indices)
    adjusted_insert_at = sum(1 for index in range(insert_at) if index not in removed)
    retained = [line for index, line in enumerate(event_lines) if index not in removed]
    return [*retained[:adjusted_insert_at], *replacement_lines, *retained[adjusted_insert_at:]]


def _matching_top_level_indices(event_lines: list[str], names: set[str]) -> list[int]:
    indices: list[int] = []
    nested_depth = 0
    for index, line in enumerate(event_lines):
        name, _value = _split_property(line)
        if name == 'BEGIN':
            nested_depth += 1
            continue
        if name == 'END' and nested_depth > 0:
            nested_depth -= 1
            continue
        if nested_depth == 0 and name in names:
            indices.append(index)
    return indices


def _event_bounds(lines: list[str]) -> tuple[int, int] | None:
    start = -1
    for index, line in enumerate(lines):
        name, value = _split_property(line)
        if name == 'BEGIN' and value.upper() == 'VEVENT':
            start = index
            continue
        if start >= 0 and name == 'END' and value.upper() == 'VEVENT':
            return start, index
    return None


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
    return key.split(';', 1)[0].strip().upper(), value.strip()


def _ics_utc_timestamp(value: str) -> str:
    parsed = _parse_iso(value)
    if parsed is None:
        return ''
    return parsed.astimezone(timezone.utc).strftime('%Y%m%dT%H%M%SZ')


def _local_date(value: str, timezone_name: str) -> str:
    parsed = _parse_iso(value)
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


def _zoneinfo(value: str):
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
