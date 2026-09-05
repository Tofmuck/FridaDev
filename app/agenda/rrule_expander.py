from __future__ import annotations

import calendar
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


MAX_RECURRENCE_OCCURRENCES = 512

_SUPPORTED_FREQS = {'DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY'}
_SUPPORTED_RRULE_KEYS = {
    'FREQ',
    'COUNT',
    'UNTIL',
    'INTERVAL',
    'BYDAY',
    'BYMONTHDAY',
    'BYSETPOS',
    'BYMONTH',
}
_WEEKDAYS = {
    'MO': 0,
    'TU': 1,
    'WE': 2,
    'TH': 3,
    'FR': 4,
    'SA': 5,
    'SU': 6,
}


class IcsRecurrenceUnsupportedError(ValueError):
    pass


@dataclass(frozen=True)
class _ByDay:
    weekday: int
    ordinal: int | None = None


def expand_recurrence_starts(
    *,
    start_dt: datetime,
    duration: timedelta,
    rrule_value: str,
    window_start: datetime | None,
    window_end: datetime | None,
    max_occurrences: int = MAX_RECURRENCE_OCCURRENCES,
) -> list[datetime]:
    rule = _parse_rrule(rrule_value)
    freq = rule['FREQ']
    count = _positive_int(rule.get('COUNT', ''), field='COUNT') if rule.get('COUNT') else None
    interval = _positive_int(rule.get('INTERVAL', '1'), field='INTERVAL')
    until = _parse_ics_datetime_to_dt(rule.get('UNTIL', '')) if rule.get('UNTIL') else None
    byday = _parse_byday(rule.get('BYDAY', ''))
    bymonthday = _parse_int_list(rule.get('BYMONTHDAY', ''), field='BYMONTHDAY', minimum=-31, maximum=31)
    bysetpos = _parse_int_list(rule.get('BYSETPOS', ''), field='BYSETPOS', minimum=-366, maximum=366)
    bymonth = _parse_int_list(rule.get('BYMONTH', ''), field='BYMONTH', minimum=1, maximum=12)
    limit = int(max_occurrences)
    if limit <= 0:
        raise IcsRecurrenceUnsupportedError('recurrence expansion limit must be positive')
    if window_end is None and count is None and until is None:
        raise IcsRecurrenceUnsupportedError('recurrence expansion requires a bounded window or limit')

    occurrences: list[datetime] = []
    emitted_by_rule = 0
    for period_start in _period_starts(start_dt=start_dt, freq=freq, interval=interval, hard_limit=limit):
        candidates = _period_candidates(
            period_start=period_start,
            start_dt=start_dt,
            freq=freq,
            byday=byday,
            bymonthday=bymonthday,
            bysetpos=bysetpos,
            bymonth=bymonth,
        )
        for candidate in candidates:
            if candidate < start_dt:
                continue
            if until is not None and candidate > until:
                return occurrences
            emitted_by_rule += 1
            if _candidate_overlaps(candidate, duration=duration, window_start=window_start, window_end=window_end):
                occurrences.append(candidate)
            if count is not None and emitted_by_rule >= count:
                return occurrences
            if len(occurrences) >= limit:
                raise IcsRecurrenceUnsupportedError('recurrence expansion exceeded bounded limit')
        if _period_can_stop(period_start, freq=freq, window_end=window_end, until=until, count=count):
            return occurrences
    raise IcsRecurrenceUnsupportedError('recurrence expansion exceeded bounded limit')


def _parse_rrule(value: str) -> dict[str, str]:
    rule: dict[str, str] = {}
    for part in str(value or '').split(';'):
        if not part:
            continue
        if '=' not in part:
            raise IcsRecurrenceUnsupportedError('recurrence rule is malformed')
        key, raw_value = part.split('=', 1)
        key = key.strip().upper()
        if key not in _SUPPORTED_RRULE_KEYS:
            raise IcsRecurrenceUnsupportedError('recurrence rule part is not supported')
        rule[key] = raw_value.strip().upper()
    freq = rule.get('FREQ', '')
    if freq not in _SUPPORTED_FREQS:
        raise IcsRecurrenceUnsupportedError('recurrence frequency is not supported')
    return rule


def _period_starts(*, start_dt: datetime, freq: str, interval: int, hard_limit: int) -> Iterator[datetime]:
    cursor = start_dt
    for _index in range(max(hard_limit * 12, 512)):
        yield cursor
        try:
            cursor = _add_interval(cursor, freq=freq, interval=interval)
        except (OverflowError, ValueError):
            raise IcsRecurrenceUnsupportedError('recurrence expansion exceeds the calendar domain') from None


def _period_candidates(
    *,
    period_start: datetime,
    start_dt: datetime,
    freq: str,
    byday: tuple[_ByDay, ...],
    bymonthday: tuple[int, ...],
    bysetpos: tuple[int, ...],
    bymonth: tuple[int, ...],
) -> list[datetime]:
    if bysetpos and freq in {'DAILY', 'WEEKLY'}:
        raise IcsRecurrenceUnsupportedError('BYSETPOS is not supported for this frequency')
    if freq == 'DAILY':
        return _filter_candidates([period_start], byday=byday, bymonthday=bymonthday, bymonth=bymonth)
    if freq == 'WEEKLY':
        return _weekly_candidates(period_start, byday=byday, bymonthday=bymonthday, bymonth=bymonth)
    if freq == 'MONTHLY':
        return _monthly_candidates(
            year=period_start.year,
            month=period_start.month,
            time_source=start_dt,
            byday=byday,
            bymonthday=bymonthday,
            bysetpos=bysetpos,
            bymonth=bymonth,
        )
    if freq == 'YEARLY':
        return _yearly_candidates(
            year=period_start.year,
            time_source=start_dt,
            byday=byday,
            bymonthday=bymonthday,
            bysetpos=bysetpos,
            bymonth=bymonth,
        )
    raise IcsRecurrenceUnsupportedError('recurrence frequency is not supported')


def _weekly_candidates(
    period_start: datetime,
    *,
    byday: tuple[_ByDay, ...],
    bymonthday: tuple[int, ...],
    bymonth: tuple[int, ...],
) -> list[datetime]:
    if not byday:
        return _filter_candidates([period_start], byday=(), bymonthday=bymonthday, bymonth=bymonth)
    monday = period_start - timedelta(days=period_start.weekday())
    dates = [monday + timedelta(days=item.weekday) for item in byday if item.ordinal is None]
    if any(item.ordinal is not None for item in byday):
        raise IcsRecurrenceUnsupportedError('weekly ordinal BYDAY is not supported')
    return _filter_candidates(dates, byday=(), bymonthday=bymonthday, bymonth=bymonth)


def _monthly_candidates(
    *,
    year: int,
    month: int,
    time_source: datetime,
    byday: tuple[_ByDay, ...],
    bymonthday: tuple[int, ...],
    bysetpos: tuple[int, ...],
    bymonth: tuple[int, ...],
) -> list[datetime]:
    if bymonth and month not in bymonth:
        return []
    if bymonthday:
        candidates = [_date_for_monthday(year, month, day, time_source=time_source) for day in bymonthday]
    elif byday:
        candidates = _dates_for_byday(year, month, byday=byday, time_source=time_source)
    else:
        candidates = [_date_for_monthday(year, month, time_source.day, time_source=time_source)]
    candidates = [candidate for candidate in candidates if candidate is not None]
    return _apply_bysetpos(sorted(candidates), bysetpos)


def _yearly_candidates(
    *,
    year: int,
    time_source: datetime,
    byday: tuple[_ByDay, ...],
    bymonthday: tuple[int, ...],
    bysetpos: tuple[int, ...],
    bymonth: tuple[int, ...],
) -> list[datetime]:
    months = bymonth or (time_source.month,)
    candidates: list[datetime] = []
    for month in months:
        candidates.extend(
            _monthly_candidates(
                year=year,
                month=month,
                time_source=time_source,
                byday=byday,
                bymonthday=bymonthday,
                bysetpos=(),
                bymonth=(),
            )
        )
    return _apply_bysetpos(sorted(candidates), bysetpos)


def _dates_for_byday(
    year: int,
    month: int,
    *,
    byday: tuple[_ByDay, ...],
    time_source: datetime,
) -> list[datetime]:
    candidates: list[datetime] = []
    for item in byday:
        month_dates = _month_dates_for_weekday(year, month, item.weekday, time_source=time_source)
        if item.ordinal is None:
            candidates.extend(month_dates)
        elif item.ordinal > 0 and item.ordinal <= len(month_dates):
            candidates.append(month_dates[item.ordinal - 1])
        elif item.ordinal < 0 and abs(item.ordinal) <= len(month_dates):
            candidates.append(month_dates[item.ordinal])
    return candidates


def _month_dates_for_weekday(
    year: int,
    month: int,
    weekday: int,
    *,
    time_source: datetime,
) -> list[datetime]:
    dates: list[datetime] = []
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        candidate = time_source.replace(year=year, month=month, day=day)
        if candidate.weekday() == weekday:
            dates.append(candidate)
    return dates


def _date_for_monthday(year: int, month: int, day: int, *, time_source: datetime) -> datetime | None:
    month_length = calendar.monthrange(year, month)[1]
    if day == 0:
        raise IcsRecurrenceUnsupportedError('BYMONTHDAY cannot be zero')
    actual_day = day if day > 0 else month_length + day + 1
    if actual_day < 1 or actual_day > month_length:
        return None
    return time_source.replace(year=year, month=month, day=actual_day)


def _filter_candidates(
    candidates: list[datetime],
    *,
    byday: tuple[_ByDay, ...],
    bymonthday: tuple[int, ...],
    bymonth: tuple[int, ...],
) -> list[datetime]:
    filtered = candidates
    if bymonth:
        filtered = [candidate for candidate in filtered if candidate.month in bymonth]
    if bymonthday:
        allowed = set(bymonthday)
        filtered = [
            candidate
            for candidate in filtered
            if candidate.day in allowed or candidate.day - calendar.monthrange(candidate.year, candidate.month)[1] - 1 in allowed
        ]
    if byday:
        allowed_weekdays = {item.weekday for item in byday if item.ordinal is None}
        if len(allowed_weekdays) != len(byday):
            raise IcsRecurrenceUnsupportedError('ordinal BYDAY filter is not supported for this frequency')
        filtered = [candidate for candidate in filtered if candidate.weekday() in allowed_weekdays]
    return sorted(filtered)


def _apply_bysetpos(candidates: list[datetime], bysetpos: tuple[int, ...]) -> list[datetime]:
    if not bysetpos:
        return candidates
    selected: list[datetime] = []
    for position in bysetpos:
        if position == 0:
            raise IcsRecurrenceUnsupportedError('BYSETPOS cannot be zero')
        index = position - 1 if position > 0 else position
        if abs(position) <= len(candidates):
            selected.append(candidates[index])
    return sorted(set(selected))


def _candidate_overlaps(
    candidate: datetime,
    *,
    duration: timedelta,
    window_start: datetime | None,
    window_end: datetime | None,
) -> bool:
    if window_start is None or window_end is None:
        return True
    try:
        candidate_end = candidate + duration
    except (OverflowError, ValueError):
        raise IcsRecurrenceUnsupportedError('recurrence expansion exceeds the calendar domain') from None
    return candidate < window_end and candidate_end > window_start


def _period_can_stop(
    period_start: datetime,
    *,
    freq: str,
    window_end: datetime | None,
    until: datetime | None,
    count: int | None,
) -> bool:
    if count is not None:
        return False
    boundary = until or window_end
    if boundary is None:
        return False
    try:
        return period_start >= _period_boundary(boundary, freq=freq)
    except (OverflowError, ValueError):
        raise IcsRecurrenceUnsupportedError('recurrence expansion exceeds the calendar domain') from None


def _period_boundary(value: datetime, *, freq: str) -> datetime:
    if freq == 'DAILY':
        return value
    if freq == 'WEEKLY':
        return value + timedelta(days=7)
    if freq == 'MONTHLY':
        return _add_months(value, 1)
    if freq == 'YEARLY':
        return _add_months(value, 12)
    return value


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


def _parse_byday(value: str) -> tuple[_ByDay, ...]:
    if not value:
        return ()
    parsed: list[_ByDay] = []
    for item in str(value).split(','):
        byday_text = item.strip().upper()
        if len(byday_text) < 2:
            raise IcsRecurrenceUnsupportedError('BYDAY value is malformed')
        day_code = byday_text[-2:]
        if day_code not in _WEEKDAYS:
            raise IcsRecurrenceUnsupportedError('BYDAY weekday is not supported')
        ordinal_text = byday_text[:-2]
        try:
            ordinal = int(ordinal_text) if ordinal_text else None
        except ValueError as exc:
            raise IcsRecurrenceUnsupportedError('BYDAY ordinal is malformed') from exc
        if ordinal == 0:
            raise IcsRecurrenceUnsupportedError('BYDAY ordinal cannot be zero')
        parsed.append(_ByDay(weekday=_WEEKDAYS[day_code], ordinal=ordinal))
    return tuple(parsed)


def _parse_int_list(value: str, *, field: str, minimum: int, maximum: int) -> tuple[int, ...]:
    if not value:
        return ()
    parsed: list[int] = []
    for item in str(value).split(','):
        try:
            number = int(item.strip())
        except ValueError as exc:
            raise IcsRecurrenceUnsupportedError(f'recurrence {field} must be an integer list') from exc
        if number < minimum or number > maximum:
            raise IcsRecurrenceUnsupportedError(f'recurrence {field} is outside supported bounds')
        parsed.append(number)
    return tuple(parsed)


def _positive_int(value: str, *, field: str) -> int:
    try:
        parsed = int(str(value or ''))
    except ValueError as exc:
        raise IcsRecurrenceUnsupportedError(f'recurrence {field} must be an integer') from exc
    if parsed <= 0:
        raise IcsRecurrenceUnsupportedError(f'recurrence {field} must be positive')
    return parsed


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
