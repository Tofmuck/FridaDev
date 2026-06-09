from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from agenda import read_tools
from agenda.caldav_models import (
    AgendaReadState,
    CalendarEvent,
    ReadToolResult,
    ReadToolValidationError,
)
from agenda.caldav_read_client import CalDavReadClient
from agenda.observability import build_tool_observation


DEFAULT_HORIZON_DAYS = 365
MAX_HORIZON_DAYS = 365
MAX_WINDOW_DAYS = 31

REASON_MATCH_FOUND = 'agenda_next_matching_found'
REASON_NO_MATCH = 'agenda_next_matching_not_found'
REASON_QUERY_MISSING = 'agenda_next_matching_query_missing'
REASON_START_MISSING = 'agenda_next_matching_start_missing'


@dataclass(frozen=True)
class NextMatchingPolicy:
    horizon_days: int = DEFAULT_HORIZON_DAYS
    window_days: int = MAX_WINDOW_DAYS

    @property
    def capped_horizon_days(self) -> int:
        return max(1, min(int(self.horizon_days or DEFAULT_HORIZON_DAYS), MAX_HORIZON_DAYS))

    @property
    def capped_window_days(self) -> int:
        return max(1, min(int(self.window_days or MAX_WINDOW_DAYS), MAX_WINDOW_DAYS))


def find_next_matching_event(
    client: CalDavReadClient,
    *,
    state: AgendaReadState,
    query: str,
    start_iso: str,
    timezone_name: str = 'UTC',
    calendar_id: str = '',
    policy: NextMatchingPolicy | None = None,
) -> ReadToolResult:
    normalized_query = read_tools.normalize_search_query(query)
    if not normalized_query:
        raise ReadToolValidationError(REASON_QUERY_MISSING)
    start_dt = _parse_iso_required(start_iso, field='start_iso')
    search_policy = policy or NextMatchingPolicy()
    _ensure_calendars(client, state)
    target_calendar_ids = _target_calendar_ids(state, calendar_id=calendar_id)

    horizon_end = start_dt + timedelta(days=search_policy.capped_horizon_days)
    window_delta = timedelta(days=search_policy.capped_window_days)
    current_start = start_dt
    windows_read = 0
    matched_events: tuple[CalendarEvent, ...] = ()
    matched_calendars = ()

    while current_start < horizon_end:
        current_end = min(current_start + window_delta, horizon_end)
        windows_read += 1
        window_events: list[CalendarEvent] = []
        for target_id in target_calendar_ids:
            result = read_tools.event_query_range(
                client,
                state=state,
                calendar_id=target_id,
                start_iso=_to_utc_iso(current_start),
                end_iso=_to_utc_iso(current_end),
                timezone_name=timezone_name,
                max_days=MAX_WINDOW_DAYS,
            )
            window_events.extend(item for item in result.items if isinstance(item, CalendarEvent))
        future_matches = [
            event
            for event in window_events
            if _event_starts_at_or_after(event, start_dt) and read_tools.event_matches_query(event, normalized_query)
        ]
        if future_matches:
            matched_events = tuple(
                sorted(future_matches, key=lambda event: (event.start_iso, event.end_iso, event.event_id))
            )
            matched_calendars = _calendars_for_events(state, matched_events)
            break
        current_start = current_end

    selected_events = matched_events[:1]
    reason_code = REASON_MATCH_FOUND if selected_events else REASON_NO_MATCH
    return ReadToolResult(
        status='ok',
        items=selected_events,
        observation={
            **build_tool_observation(
                tool_name='find_next_matching_event',
                status='ok',
                calendars=matched_calendars,
                events=selected_events,
                query=query,
                window_start=_to_utc_iso(start_dt),
                window_end=_to_utc_iso(horizon_end),
                timezone=timezone_name,
                reason_code=reason_code,
            ),
            'windows_read': windows_read,
            'horizon_days': search_policy.capped_horizon_days,
            'window_days': search_policy.capped_window_days,
            'content_free': True,
            'redacted': True,
        },
    )


def query_from_tool_calls(tool_calls: tuple[Any, ...]) -> str:
    for call in tool_calls:
        if str(getattr(call, 'tool_name', '') or '') != 'event_search':
            continue
        params = getattr(call, 'params', {}) or {}
        if isinstance(params, Mapping):
            query = str(params.get('query') or '').strip()
            if query:
                return query
    return ''


def calendar_id_from_tool_calls(tool_calls: tuple[Any, ...]) -> str:
    for call in tool_calls:
        params = getattr(call, 'params', {}) or {}
        if not isinstance(params, Mapping):
            continue
        calendar_id = str(params.get('calendar_id') or '').strip()
        if calendar_id:
            return calendar_id
    return ''


def _ensure_calendars(client: CalDavReadClient, state: AgendaReadState) -> None:
    if state.calendars:
        return
    read_tools.calendar_list(client, state=state)


def _target_calendar_ids(state: AgendaReadState, *, calendar_id: str = '') -> tuple[str, ...]:
    target = str(calendar_id or '').strip()
    if target:
        if target not in state.calendars:
            raise ReadToolValidationError('calendar target is required and must exist in read state')
        return (target,)
    return tuple(sorted(state.calendars))


def _calendars_for_events(state: AgendaReadState, events: tuple[CalendarEvent, ...]) -> tuple:
    seen: set[str] = set()
    calendars = []
    for event in events:
        if event.calendar_id in seen:
            continue
        calendar = state.calendars.get(event.calendar_id)
        if calendar is not None:
            calendars.append(calendar)
            seen.add(event.calendar_id)
    return tuple(calendars)


def _event_starts_at_or_after(event: CalendarEvent, start_dt: datetime) -> bool:
    event_start = _parse_iso_required(event.start_iso, field='event.start_iso')
    return event_start >= start_dt


def _parse_iso_required(value: str, *, field: str) -> datetime:
    raw = str(value or '').strip()
    if not raw:
        raise ReadToolValidationError(REASON_START_MISSING if field == 'start_iso' else f'{field} is required')
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ReadToolValidationError(f'{field} must be an explicit ISO timestamp') from exc
    if parsed.tzinfo is None:
        raise ReadToolValidationError(f'{field} must include timezone')
    return parsed.astimezone(timezone.utc)


def _to_utc_iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
