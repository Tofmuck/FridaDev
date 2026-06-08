from __future__ import annotations

import calendar
from datetime import datetime, timedelta, timezone
from typing import Mapping

from agenda.caldav_models import CalendarEvent
from agenda.observability import sha256_12


MAX_RECURRENCE_OCCURRENCES = 512
SUPPORTED_FREQS = {'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'}
SUPPORTED_RRULE_KEYS = {'FREQ', 'COUNT', 'UNTIL', 'INTERVAL'}


class IcsRecurrenceUnsupportedError(ValueError):
    pass


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
    parsed = _parse_ics_datetime_to_dt(value)
    return _to_utc_iso(parsed) if parsed is not None else ''


def _parse_ics_datetime_to_dt(value: str) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    if raw.endswith('Z'):
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    elif 'T' in raw:
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%S').replace(tzinfo=timezone.utc)
    else:
        parsed = datetime.strptime(raw, '%Y%m%d').replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_iso_datetime(value: str) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


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
    window_start_iso: str = '',
    window_end_iso: str = '',
    max_occurrences: int = MAX_RECURRENCE_OCCURRENCES,
) -> tuple[CalendarEvent, ...]:
    components: list[dict[str, tuple[str, ...]]] = []
    in_event = False
    current: dict[str, list[str]] = {}
    for line in _unfold_ics_lines(ics_text):
        name, value = _split_property(line)
        if name == 'BEGIN' and value.upper() == 'VEVENT':
            in_event = True
            current = {}
            continue
        if name == 'END' and value.upper() == 'VEVENT':
            if in_event:
                components.append({key: tuple(values) for key, values in current.items()})
            in_event = False
            current = {}
            continue
        if in_event:
            current.setdefault(name, []).append(value)
    events = _events_from_components(
        components,
        calendar_id=calendar_id,
        timezone_name=timezone_name,
        default_etag=default_etag,
        default_caldav_path=default_caldav_path,
        window_start_iso=window_start_iso,
        window_end_iso=window_end_iso,
        max_occurrences=max_occurrences,
    )
    return tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))


def _events_from_components(
    components: list[Mapping[str, tuple[str, ...]]],
    *,
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    window_start_iso: str,
    window_end_iso: str,
    max_occurrences: int,
) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    overrides: dict[str, dict[datetime, Mapping[str, tuple[str, ...]]]] = {}
    override_keys: set[tuple[str, datetime]] = set()
    masters: list[Mapping[str, tuple[str, ...]]] = []
    standalone: list[Mapping[str, tuple[str, ...]]] = []
    window_start = _parse_iso_datetime(window_start_iso)
    window_end = _parse_iso_datetime(window_end_iso)

    for props in components:
        uid = _first(props, 'UID')
        recurrence_id = _parse_ics_datetime_to_dt(_first(props, 'RECURRENCE-ID'))
        if recurrence_id is not None and uid:
            overrides.setdefault(uid, {})[recurrence_id] = props
            continue
        if _first(props, 'RRULE'):
            masters.append(props)
            continue
        standalone.append(props)

    for props in standalone:
        event = _event_from_props(
            props,
            calendar_id=calendar_id,
            timezone_name=timezone_name,
            default_etag=default_etag,
            default_caldav_path=default_caldav_path,
        )
        if event is not None and _event_is_in_window(event, window_start=window_start, window_end=window_end):
            events.append(event)

    for props in masters:
        recurring_events, consumed_keys = _events_from_recurring_props(
            props,
            overrides=overrides.get(_first(props, 'UID'), {}),
            calendar_id=calendar_id,
            timezone_name=timezone_name,
            default_etag=default_etag,
            default_caldav_path=default_caldav_path,
            window_start=window_start,
            window_end=window_end,
            max_occurrences=max_occurrences,
        )
        events.extend(recurring_events)
        override_keys.update(consumed_keys)

    for uid, uid_overrides in overrides.items():
        for recurrence_id, props in uid_overrides.items():
            if (uid, recurrence_id) in override_keys:
                continue
            event = _event_from_props(
                props,
                calendar_id=calendar_id,
                timezone_name=timezone_name,
                default_etag=default_etag,
                default_caldav_path=default_caldav_path,
                event_id_seed=f'recurrence:{_to_utc_iso(recurrence_id)}',
            )
            if event is not None and _event_is_in_window(event, window_start=window_start, window_end=window_end):
                events.append(event)

    return events


def _event_from_props(
    props: Mapping[str, tuple[str, ...]],
    *,
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    event_id_seed: str = '',
) -> CalendarEvent | None:
    uid = _first(props, 'UID')
    start_dt = _parse_ics_datetime_to_dt(_first(props, 'DTSTART'))
    end_dt = _parse_ics_datetime_to_dt(_first(props, 'DTEND'))
    if not uid or start_dt is None or end_dt is None:
        return None
    return _event_from_datetimes(
        props,
        calendar_id=calendar_id,
        uid=uid,
        start_dt=start_dt,
        end_dt=end_dt,
        timezone_name=timezone_name,
        default_etag=default_etag,
        default_caldav_path=default_caldav_path,
        event_id_seed=event_id_seed,
    )


def _event_from_datetimes(
    props: Mapping[str, tuple[str, ...]],
    *,
    calendar_id: str,
    uid: str,
    start_dt: datetime,
    end_dt: datetime,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    event_id_seed: str,
) -> CalendarEvent:
    event_id_source = f'{calendar_id}:{uid}:{event_id_seed}' if event_id_seed else f'{calendar_id}:{uid}'
    event_id = f'evt_{sha256_12(event_id_source)}'
    return CalendarEvent(
        event_id=event_id,
        calendar_id=str(calendar_id),
        uid=uid,
        summary=_first(props, 'SUMMARY'),
        location=_first(props, 'LOCATION'),
        description=_first(props, 'DESCRIPTION'),
        start_iso=_to_utc_iso(start_dt),
        end_iso=_to_utc_iso(end_dt),
        timezone=str(timezone_name or 'UTC'),
        etag=str(default_etag or ''),
        caldav_path=str(default_caldav_path or ''),
    )


def _events_from_recurring_props(
    props: Mapping[str, tuple[str, ...]],
    *,
    overrides: Mapping[datetime, Mapping[str, tuple[str, ...]]],
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    window_start: datetime | None,
    window_end: datetime | None,
    max_occurrences: int,
) -> tuple[list[CalendarEvent], set[tuple[str, datetime]]]:
    uid = _first(props, 'UID')
    start_dt = _parse_ics_datetime_to_dt(_first(props, 'DTSTART'))
    end_dt = _parse_ics_datetime_to_dt(_first(props, 'DTEND'))
    if not uid or start_dt is None or end_dt is None:
        return [], set()
    duration = end_dt - start_dt
    exdates = _exdates_from_props(props)
    events: list[CalendarEvent] = []
    consumed: set[tuple[str, datetime]] = set()
    for occurrence_start in _expand_recurrence_starts(
        start_dt=start_dt,
        duration=duration,
        rrule_value=_first(props, 'RRULE'),
        window_start=window_start,
        window_end=window_end,
        max_occurrences=max_occurrences,
    ):
        if occurrence_start in exdates:
            continue
        override = overrides.get(occurrence_start)
        if override is not None:
            override_event = _event_from_props(
                override,
                calendar_id=calendar_id,
                timezone_name=timezone_name,
                default_etag=default_etag,
                default_caldav_path=default_caldav_path,
                event_id_seed=f'recurrence:{_to_utc_iso(occurrence_start)}',
            )
            if override_event is not None and _event_is_in_window(
                override_event,
                window_start=window_start,
                window_end=window_end,
            ):
                events.append(override_event)
                consumed.add((uid, occurrence_start))
            continue
        occurrence_end = occurrence_start + duration
        event = _event_from_datetimes(
            props,
            calendar_id=calendar_id,
            uid=uid,
            start_dt=occurrence_start,
            end_dt=occurrence_end,
            timezone_name=timezone_name,
            default_etag=default_etag,
            default_caldav_path=default_caldav_path,
            event_id_seed=f'recurrence:{_to_utc_iso(occurrence_start)}',
        )
        if _event_is_in_window(event, window_start=window_start, window_end=window_end):
            events.append(event)
    return events, consumed


def _expand_recurrence_starts(
    *,
    start_dt: datetime,
    duration: timedelta,
    rrule_value: str,
    window_start: datetime | None,
    window_end: datetime | None,
    max_occurrences: int,
) -> list[datetime]:
    rule = _parse_rrule(rrule_value)
    freq = rule['FREQ']
    count = _positive_int(rule.get('COUNT', ''), field='COUNT') if rule.get('COUNT') else None
    interval = _positive_int(rule.get('INTERVAL', '1'), field='INTERVAL')
    until = _parse_ics_datetime_to_dt(rule.get('UNTIL', '')) if rule.get('UNTIL') else None
    limit = int(max_occurrences)
    if limit <= 0:
        raise IcsRecurrenceUnsupportedError('recurrence expansion limit must be positive')

    occurrences: list[datetime] = []
    cursor = start_dt
    generated_by_rule = 0
    window_floor = window_start - duration if window_start is not None else None
    while generated_by_rule < limit:
        if count is not None and generated_by_rule >= count:
            break
        if until is not None and cursor > until:
            break
        generated_by_rule += 1
        if _recurrence_start_is_needed(cursor, window_floor=window_floor, window_end=window_end):
            occurrences.append(cursor)
        if window_end is not None and cursor >= window_end:
            break
        cursor = _add_interval(cursor, freq=freq, interval=interval)
    if generated_by_rule >= limit and (window_end is None or cursor < window_end):
        raise IcsRecurrenceUnsupportedError('recurrence expansion exceeded bounded limit')
    return occurrences


def _parse_rrule(value: str) -> dict[str, str]:
    rule: dict[str, str] = {}
    for part in str(value or '').split(';'):
        if not part:
            continue
        if '=' not in part:
            raise IcsRecurrenceUnsupportedError('recurrence rule is malformed')
        key, raw_value = part.split('=', 1)
        key = key.strip().upper()
        if key not in SUPPORTED_RRULE_KEYS:
            raise IcsRecurrenceUnsupportedError('recurrence rule part is not supported')
        rule[key] = raw_value.strip().upper()
    freq = rule.get('FREQ', '')
    if freq not in SUPPORTED_FREQS:
        raise IcsRecurrenceUnsupportedError('recurrence frequency is not supported')
    return rule


def _positive_int(value: str, *, field: str) -> int:
    try:
        parsed = int(str(value or ''))
    except ValueError as exc:
        raise IcsRecurrenceUnsupportedError(f'recurrence {field} must be an integer') from exc
    if parsed <= 0:
        raise IcsRecurrenceUnsupportedError(f'recurrence {field} must be positive')
    return parsed


def _add_interval(value: datetime, *, freq: str, interval: int) -> datetime:
    if freq == 'DAILY':
        return value + timedelta(days=interval)
    if freq == 'WEEKLY':
        return value + timedelta(weeks=interval)
    if freq == 'MONTHLY':
        return _add_months(value, interval)
    if freq == 'YEARLY':
        return _add_months(value, interval * 12)
    raise IcsRecurrenceUnsupportedError('recurrence frequency is not supported')


def _add_months(value: datetime, months: int) -> datetime:
    month_index = value.month - 1 + int(months)
    year = value.year + month_index // 12
    month = month_index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


def _recurrence_start_is_needed(
    value: datetime,
    *,
    window_floor: datetime | None,
    window_end: datetime | None,
) -> bool:
    if window_floor is not None and value < window_floor:
        return False
    if window_end is not None and value >= window_end:
        return False
    return True


def _exdates_from_props(props: Mapping[str, tuple[str, ...]]) -> set[datetime]:
    exdates: set[datetime] = set()
    for value in props.get('EXDATE', ()):
        for item in str(value or '').split(','):
            parsed = _parse_ics_datetime_to_dt(item)
            if parsed is not None:
                exdates.add(parsed)
    return exdates


def _event_is_in_window(
    event: CalendarEvent,
    *,
    window_start: datetime | None,
    window_end: datetime | None,
) -> bool:
    if window_start is None or window_end is None:
        return True
    event_start = _parse_iso_datetime(event.start_iso)
    event_end = _parse_iso_datetime(event.end_iso)
    if event_start is None or event_end is None:
        return False
    return event_start < window_end and event_end > window_start


def _first(props: Mapping[str, tuple[str, ...]], name: str) -> str:
    values = props.get(name, ())
    return str(values[0]).strip() if values else ''
