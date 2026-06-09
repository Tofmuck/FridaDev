from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agenda.caldav_models import CalendarEvent
from agenda.observability import sha256_12
from agenda.rrule_expander import (
    MAX_RECURRENCE_OCCURRENCES,
    IcsRecurrenceUnsupportedError,
    expand_recurrence_starts,
)


@dataclass(frozen=True)
class _IcsProperty:
    value: str
    params: Mapping[str, str]


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
    name, _params, value = _split_property_parts(line)
    return name, value


def _split_property_parts(line: str) -> tuple[str, dict[str, str], str]:
    if ':' not in line:
        return line.strip().upper(), {}, ''
    key, value = line.split(':', 1)
    parts = key.split(';')
    name = parts[0].strip().upper()
    params: dict[str, str] = {}
    for part in parts[1:]:
        if '=' not in part:
            continue
        param_name, raw_param_value = part.split('=', 1)
        params[param_name.strip().upper()] = raw_param_value.strip().strip('"')
    return name, params, _unescape_text(value.strip())


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


def _parse_ics_datetime_to_dt(
    value: str,
    *,
    params: Mapping[str, str] | None = None,
    default_timezone_name: str = 'UTC',
    normalize_utc: bool = True,
) -> datetime | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    if raw.endswith('Z'):
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%SZ').replace(tzinfo=timezone.utc)
    elif 'T' in raw:
        parsed = datetime.strptime(raw, '%Y%m%dT%H%M%S').replace(
            tzinfo=_property_timezone(params, default_timezone_name=default_timezone_name)
        )
    else:
        parsed = datetime.strptime(raw, '%Y%m%d').replace(
            tzinfo=_property_timezone(params, default_timezone_name=default_timezone_name)
        )
    return parsed.astimezone(timezone.utc) if normalize_utc else parsed


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
    source_ics: str = '',
    window_start_iso: str = '',
    window_end_iso: str = '',
    max_occurrences: int = MAX_RECURRENCE_OCCURRENCES,
) -> tuple[CalendarEvent, ...]:
    components: list[dict[str, tuple[_IcsProperty, ...]]] = []
    in_event = False
    current: dict[str, list[_IcsProperty]] = {}
    for line in _unfold_ics_lines(ics_text):
        name, params, value = _split_property_parts(line)
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
            current.setdefault(name, []).append(_IcsProperty(value=value, params=params))
    events = _events_from_components(
        components,
        calendar_id=calendar_id,
        timezone_name=timezone_name,
        default_etag=default_etag,
        default_caldav_path=default_caldav_path,
        source_ics=source_ics or str(ics_text or ''),
        window_start_iso=window_start_iso,
        window_end_iso=window_end_iso,
        max_occurrences=max_occurrences,
    )
    return tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))


def _events_from_components(
    components: list[Mapping[str, tuple[_IcsProperty, ...]]],
    *,
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    source_ics: str,
    window_start_iso: str,
    window_end_iso: str,
    max_occurrences: int,
) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []
    overrides: dict[str, dict[datetime, Mapping[str, tuple[_IcsProperty, ...]]]] = {}
    override_keys: set[tuple[str, datetime]] = set()
    masters: list[Mapping[str, tuple[_IcsProperty, ...]]] = []
    standalone: list[Mapping[str, tuple[_IcsProperty, ...]]] = []
    window_start = _parse_iso_datetime(window_start_iso)
    window_end = _parse_iso_datetime(window_end_iso)

    for props in components:
        uid = _first(props, 'UID')
        recurrence_id = _parse_ics_property_datetime_to_dt(
            _first_prop(props, 'RECURRENCE-ID'),
            default_timezone_name=timezone_name,
            normalize_utc=False,
        )
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
            source_ics=source_ics,
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
            source_ics=source_ics,
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
                source_ics=source_ics,
                event_id_seed=f'recurrence:{_to_utc_iso(recurrence_id)}',
            )
            if event is not None and _event_is_in_window(event, window_start=window_start, window_end=window_end):
                events.append(event)

    return events


def _event_from_props(
    props: Mapping[str, tuple[_IcsProperty, ...]],
    *,
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    source_ics: str,
    event_id_seed: str = '',
) -> CalendarEvent | None:
    uid = _first(props, 'UID')
    start_prop = _first_prop(props, 'DTSTART')
    end_prop = _first_prop(props, 'DTEND')
    start_dt = _parse_ics_property_datetime_to_dt(start_prop, default_timezone_name=timezone_name)
    end_dt = _parse_ics_property_datetime_to_dt(end_prop, default_timezone_name=timezone_name)
    if not uid or start_dt is None or end_dt is None:
        return None
    return _event_from_datetimes(
        props,
        calendar_id=calendar_id,
        uid=uid,
        start_dt=start_dt,
        end_dt=end_dt,
        timezone_name=_event_timezone_name(start_prop, default_timezone_name=timezone_name),
        default_etag=default_etag,
        default_caldav_path=default_caldav_path,
        source_ics=source_ics,
        event_id_seed=event_id_seed,
        all_day=_property_is_all_day(start_prop),
    )


def _event_from_datetimes(
    props: Mapping[str, tuple[_IcsProperty, ...]],
    *,
    calendar_id: str,
    uid: str,
    start_dt: datetime,
    end_dt: datetime,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    source_ics: str,
    event_id_seed: str,
    all_day: bool = False,
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
        all_day=bool(all_day),
        source_ics=str(source_ics or ''),
    )


def _events_from_recurring_props(
    props: Mapping[str, tuple[_IcsProperty, ...]],
    *,
    overrides: Mapping[datetime, Mapping[str, tuple[_IcsProperty, ...]]],
    calendar_id: str,
    timezone_name: str,
    default_etag: str,
    default_caldav_path: str,
    source_ics: str,
    window_start: datetime | None,
    window_end: datetime | None,
    max_occurrences: int,
) -> tuple[list[CalendarEvent], set[tuple[str, datetime]]]:
    uid = _first(props, 'UID')
    start_prop = _first_prop(props, 'DTSTART')
    end_prop = _first_prop(props, 'DTEND')
    start_dt = _parse_ics_property_datetime_to_dt(
        start_prop,
        default_timezone_name=timezone_name,
        normalize_utc=False,
    )
    end_dt = _parse_ics_property_datetime_to_dt(
        end_prop,
        default_timezone_name=timezone_name,
        normalize_utc=False,
    )
    if not uid or start_dt is None or end_dt is None:
        return [], set()
    duration = end_dt - start_dt
    event_timezone_name = _event_timezone_name(start_prop, default_timezone_name=timezone_name)
    all_day = _property_is_all_day(start_prop)
    exdates = _exdates_from_props(props, default_timezone_name=event_timezone_name)
    events: list[CalendarEvent] = []
    consumed: set[tuple[str, datetime]] = set()
    for occurrence_start in expand_recurrence_starts(
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
                source_ics=source_ics,
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
            timezone_name=event_timezone_name,
            default_etag=default_etag,
            default_caldav_path=default_caldav_path,
            source_ics=source_ics,
            event_id_seed=f'recurrence:{_to_utc_iso(occurrence_start)}',
            all_day=all_day,
        )
        if _event_is_in_window(event, window_start=window_start, window_end=window_end):
            events.append(event)
    return events, consumed


def _exdates_from_props(
    props: Mapping[str, tuple[_IcsProperty, ...]],
    *,
    default_timezone_name: str,
) -> set[datetime]:
    exdates: set[datetime] = set()
    for prop in props.get('EXDATE', ()):
        for item in str(prop.value or '').split(','):
            parsed = _parse_ics_datetime_to_dt(
                item,
                params=prop.params,
                default_timezone_name=default_timezone_name,
                normalize_utc=False,
            )
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


def _first(props: Mapping[str, tuple[_IcsProperty, ...]], name: str) -> str:
    prop = _first_prop(props, name)
    return str(prop.value).strip() if prop is not None else ''


def _first_prop(props: Mapping[str, tuple[_IcsProperty, ...]], name: str) -> _IcsProperty | None:
    values = props.get(name, ())
    return values[0] if values else None


def _parse_ics_property_datetime_to_dt(
    prop: _IcsProperty | None,
    *,
    default_timezone_name: str,
    normalize_utc: bool = True,
) -> datetime | None:
    if prop is None:
        return None
    return _parse_ics_datetime_to_dt(
        prop.value,
        params=prop.params,
        default_timezone_name=default_timezone_name,
        normalize_utc=normalize_utc,
    )


def _property_is_all_day(prop: _IcsProperty | None) -> bool:
    if prop is None:
        return False
    return str(prop.params.get('VALUE', '') or '').strip().upper() == 'DATE' or 'T' not in str(prop.value or '')


def _event_timezone_name(prop: _IcsProperty | None, *, default_timezone_name: str) -> str:
    tzid = str((prop.params if prop is not None else {}).get('TZID', '') or '').strip()
    return tzid or str(default_timezone_name or 'UTC')


def _property_timezone(params: Mapping[str, str] | None, *, default_timezone_name: str):
    timezone_name = str((params or {}).get('TZID', '') or default_timezone_name or 'UTC').strip()
    if not timezone_name:
        return timezone.utc
    try:
        return ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc
