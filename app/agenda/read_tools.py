from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from agenda.caldav_models import (
    AgendaReadState,
    CalendarEvent,
    CalendarSummary,
    ReadToolResult,
    ReadToolValidationError,
)
from agenda.caldav_read_client import CalDavReadClient
from agenda.observability import build_tool_observation, sha256_12


MAX_QUERY_RANGE_DAYS = 31
MAX_SEARCH_POOL = 100


def calendar_list(
    client: CalDavReadClient,
    *,
    state: AgendaReadState | None = None,
) -> ReadToolResult:
    calendars = client.list_calendars()
    if state is not None:
        state.add_calendars(calendars)
    return ReadToolResult(
        status='ok',
        items=calendars,
        observation=build_tool_observation(
            tool_name='calendar_list',
            status='ok',
            calendars=calendars,
        ),
    )


def event_query_range(
    client: CalDavReadClient,
    *,
    state: AgendaReadState,
    calendar_id: str,
    start_iso: str,
    end_iso: str,
    timezone_name: str = 'UTC',
    max_days: int = MAX_QUERY_RANGE_DAYS,
) -> ReadToolResult:
    calendar = _require_calendar(state, calendar_id)
    start_dt = _parse_iso_required(start_iso, field='start_iso')
    end_dt = _parse_iso_required(end_iso, field='end_iso')
    if end_dt <= start_dt:
        raise ReadToolValidationError('event_query_range requires end_iso after start_iso')
    if (end_dt - start_dt).days > int(max_days):
        raise ReadToolValidationError(f'event_query_range exceeds max_days={int(max_days)}')
    events = tuple(
        event
        for event in client.query_calendar_events(
            calendar,
            start_iso=_to_utc_iso(start_dt),
            end_iso=_to_utc_iso(end_dt),
            timezone_name=timezone_name,
        )
        if _event_overlaps(event, start_dt=start_dt, end_dt=end_dt)
    )
    events = tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))
    state.add_events(events)
    return ReadToolResult(
        status='ok',
        items=events,
        observation=build_tool_observation(
            tool_name='event_query_range',
            status='ok',
            calendars=(calendar,),
            events=events,
            window_start=_to_utc_iso(start_dt),
            window_end=_to_utc_iso(end_dt),
            timezone=timezone_name,
        ),
    )


def event_get(
    *,
    state: AgendaReadState,
    event_id: str,
) -> ReadToolResult:
    event = state.events.get(str(event_id or ''))
    if event is None:
        raise ReadToolValidationError('event_get requires an event_id already present in read state')
    calendar = state.calendars.get(event.calendar_id)
    calendars = (calendar,) if calendar else ()
    return ReadToolResult(
        status='ok',
        items=(event,),
        observation=build_tool_observation(
            tool_name='event_get',
            status='ok',
            calendars=calendars,
            events=(event,),
            selected_event_id=event.event_id,
        ),
    )


def event_search(
    *,
    state: AgendaReadState,
    query: str,
    calendar_id: str | None = None,
    limit: int = 10,
    max_pool: int = MAX_SEARCH_POOL,
) -> ReadToolResult:
    normalized_query = str(query or '').strip().lower()
    if not normalized_query:
        raise ReadToolValidationError('event_search requires a non-empty query')
    if limit <= 0:
        raise ReadToolValidationError('event_search requires a positive limit')
    events = _events_for_search(state, calendar_id=calendar_id)
    if len(events) > int(max_pool):
        raise ReadToolValidationError(f'event_search exceeds max_pool={int(max_pool)}')
    matches = tuple(event for event in events if _event_matches(event, normalized_query))[: int(limit)]
    calendars = _calendars_for_events(state, matches)
    return ReadToolResult(
        status='ok',
        items=matches,
        observation=build_tool_observation(
            tool_name='event_search',
            status='ok',
            calendars=calendars,
            events=matches,
            query=query,
        ),
    )


def _require_calendar(state: AgendaReadState, calendar_id: str) -> CalendarSummary:
    calendar = state.calendars.get(str(calendar_id or ''))
    if calendar is None:
        raise ReadToolValidationError('calendar target is required and must exist in read state')
    return calendar


def _events_for_search(state: AgendaReadState, *, calendar_id: str | None) -> tuple[CalendarEvent, ...]:
    if calendar_id:
        _require_calendar(state, calendar_id)
        return state.events_for_calendar(calendar_id)
    return tuple(sorted(state.events.values(), key=lambda event: (event.start_iso, event.end_iso, event.event_id)))


def _calendars_for_events(state: AgendaReadState, events: Iterable[CalendarEvent]) -> tuple[CalendarSummary, ...]:
    seen: set[str] = set()
    calendars: list[CalendarSummary] = []
    for event in events:
        if event.calendar_id in seen:
            continue
        calendar = state.calendars.get(event.calendar_id)
        if calendar is not None:
            calendars.append(calendar)
            seen.add(event.calendar_id)
    return tuple(calendars)


def _event_matches(event: CalendarEvent, normalized_query: str) -> bool:
    haystack = ' '.join((event.summary, event.location, event.description)).lower()
    return normalized_query in haystack


def _event_overlaps(event: CalendarEvent, *, start_dt: datetime, end_dt: datetime) -> bool:
    event_start = _parse_iso_required(event.start_iso, field='event.start_iso')
    event_end = _parse_iso_required(event.end_iso, field='event.end_iso')
    return event_start < end_dt and event_end > start_dt


def _parse_iso_required(value: str, *, field: str) -> datetime:
    raw = str(value or '').strip()
    if not raw:
        raise ReadToolValidationError(f'{field} is required')
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ReadToolValidationError(f'{field} must be an explicit ISO timestamp') from exc
    if parsed.tzinfo is None:
        raise ReadToolValidationError(f'{field} must include timezone')
    return parsed.astimezone(timezone.utc)


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def local_reference_id(value: str) -> str:
    return sha256_12(value)
