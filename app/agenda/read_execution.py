from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agenda import agent_contract
from agenda import next_matching_search
from agenda import product_methods
from agenda import read_tools
from agenda.caldav_models import (
    AgendaReadState,
    CalDavReadError,
    CalDavTransportUnavailable,
    CalendarEvent,
    CalendarSummary,
    ReadToolValidationError,
)
from agenda.caldav_read_client import CalDavReadClient
from agenda.observability import sha256_12


STATUS_OK = 'ok'
STATUS_SKIPPED = 'skipped'
STATUS_ERROR = 'error'

REASON_EXECUTED = 'agenda_readonly_executed'
REASON_NOT_READ_METHOD = 'agenda_readonly_method_not_read'
REASON_NO_TOOL_CALLS = 'agenda_readonly_no_tool_calls'
REASON_CLIENT_UNAVAILABLE = 'agenda_readonly_client_unavailable'
REASON_CLIENT_RESOLUTION_ERROR = 'agenda_readonly_client_resolution_error'
REASON_TOOL_ERROR = 'agenda_readonly_tool_error'
REASON_TOOL_UNSUPPORTED = 'agenda_readonly_tool_unsupported'
REASON_CALENDAR_SCOPE_UNRESOLVED = 'agenda_readonly_calendar_scope_unresolved'
REASON_REQUIRED_READ_MISSING = 'agenda_readonly_required_read_missing'
REASON_REQUIRED_READ_NOT_PROVEN = 'agenda_readonly_required_read_not_proven'
REASON_NO_CALENDAR_RESOLVED = 'agenda_readonly_no_calendar_resolved'


def plan_needs_read_client(plan: agent_contract.AgendaAgentPlan) -> bool:
    method = product_methods.get_method(str(getattr(plan, 'product_method', '') or ''))
    return bool(method is not None and method.family == product_methods.FAMILY_READ and plan.tool_calls)


@dataclass(frozen=True)
class AgendaReadExecutionResult:
    status: str
    reason_code: str
    product_method: str = ''
    calendars: tuple[CalendarSummary, ...] = ()
    events: tuple[CalendarEvent, ...] = ()
    tool_observations: tuple[Mapping[str, Any], ...] = field(default_factory=tuple)
    caldav_access: bool = False
    nextcloud_access: bool = False
    mutation_attempted: bool = False
    error_class: str = ''
    attempted_tool_names: tuple[str, ...] = ()
    empty_result_proven: bool = False

    @property
    def observation(self) -> dict[str, Any]:
        calendar_ids = tuple(calendar.local_id for calendar in self.calendars)
        event_ids = tuple(event.event_id for event in self.events)
        tool_names = list(self.attempted_tool_names)
        if not tool_names:
            tool_names = [
                str(observation.get('tool_name') or '')
                for observation in self.tool_observations
                if isinstance(observation, Mapping)
            ]
        return {
            'schema_version': 'frida_agenda_read_execution_v1',
            'status': self.status,
            'reason_code': self.reason_code,
            'product_method': self.product_method,
            'tool_names': tool_names,
            'tool_count': len(tool_names),
            'calendar_count': len(calendar_ids),
            'calendar_id_hashes': [sha256_12(calendar_id) for calendar_id in calendar_ids],
            'event_count': len(event_ids),
            'event_id_hashes': [sha256_12(event_id) for event_id in event_ids],
            'caldav_access': bool(self.caldav_access),
            'nextcloud_access': bool(self.nextcloud_access),
            'mutation_attempted': bool(self.mutation_attempted),
            'error_class': self.error_class,
            'empty_result_proven': bool(self.empty_result_proven),
            'content_free': True,
            'redacted': True,
        }


def execute_readonly_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    client: CalDavReadClient | None,
    live_caldav: bool = False,
    now_iso: str = '',
) -> AgendaReadExecutionResult:
    method = product_methods.get_method(plan.product_method)
    if method is None or method.family != product_methods.FAMILY_READ:
        return AgendaReadExecutionResult(
            status=STATUS_SKIPPED,
            reason_code=REASON_NOT_READ_METHOD,
            product_method=str(plan.product_method or ''),
        )
    if not plan.tool_calls:
        return AgendaReadExecutionResult(
            status=STATUS_SKIPPED,
            reason_code=REASON_NO_TOOL_CALLS,
            product_method=str(plan.product_method or ''),
        )
    if client is None:
        return AgendaReadExecutionResult(
            status=STATUS_SKIPPED,
            reason_code=REASON_CLIENT_UNAVAILABLE,
            product_method=str(plan.product_method or ''),
        )
    required_tools = product_methods.required_tools_for_method(plan.product_method)
    planned_tools = {str(call.tool_name or '') for call in plan.tool_calls}
    if not required_tools.issubset(planned_tools):
        return AgendaReadExecutionResult(
            status=STATUS_ERROR,
            reason_code=REASON_REQUIRED_READ_MISSING,
            product_method=str(plan.product_method or ''),
            attempted_tool_names=tuple(str(call.tool_name or '') for call in plan.tool_calls),
        )

    state = AgendaReadState()
    observations: list[Mapping[str, Any]] = []
    attempted_tool_names: list[str] = []
    selected_events: tuple[CalendarEvent, ...] = ()
    selected_events_locked = False
    try:
        if plan.product_method == product_methods.METHOD_FIND_NEXT_MATCHING_EVENT:
            attempted_tool_names = [
                product_methods.TOOL_EVENT_QUERY_RANGE,
                product_methods.TOOL_EVENT_SEARCH,
            ]
            query = next_matching_search.query_from_tool_calls(plan.tool_calls)
            calendar_id = next_matching_search.calendar_id_from_tool_calls(plan.tool_calls)
            _ensure_calendars(client, state)
            if not state.calendars:
                raise _read_tool_validation_error(REASON_NO_CALENDAR_RESOLVED)
            if _plan_has_explicit_calendar_scope(plan):
                if not _calendar_id_allowed_by_plan_scope(plan, calendar_id=calendar_id, state=state):
                    raise _read_tool_validation_error(REASON_CALENDAR_SCOPE_UNRESOLVED)
            start_iso = str(now_iso or plan.time_scope.get('start') or '')
            result = next_matching_search.find_next_matching_event(
                client,
                state=state,
                query=query,
                start_iso=start_iso,
                timezone_name=str(plan.time_scope.get('timezone') or 'UTC'),
                calendar_id=calendar_id,
            )
            observations.append(dict(result.observation))
            selected_events = tuple(item for item in result.items if isinstance(item, CalendarEvent))
            calendars = tuple(sorted(state.calendars.values(), key=lambda calendar: calendar.local_id))
            return AgendaReadExecutionResult(
                status=STATUS_OK,
                reason_code=REASON_EXECUTED,
                product_method=plan.product_method,
                calendars=calendars,
                events=selected_events,
                tool_observations=tuple(observations),
                caldav_access=bool(live_caldav),
                nextcloud_access=bool(live_caldav),
                mutation_attempted=False,
                attempted_tool_names=tuple(attempted_tool_names),
                empty_result_proven=(
                    not selected_events
                    and _empty_result_is_proven(plan, observations=observations)
                ),
            )
        for call in plan.tool_calls:
            attempted_tool_names.append(str(call.tool_name or ''))
            result = _execute_tool_call(
                call,
                client=client,
                state=state,
                plan=plan,
                observations=observations,
            )
            observations.append(dict(result.observation))
            if str(call.tool_name or '') == product_methods.TOOL_EVENT_SEARCH:
                selected_events = tuple(item for item in result.items if isinstance(item, CalendarEvent))
                selected_events_locked = True
            elif result.items and isinstance(result.items[0], CalendarEvent):
                selected_events = tuple(item for item in result.items if isinstance(item, CalendarEvent))
        if not selected_events and not selected_events_locked:
            selected_events = tuple(sorted(state.events.values(), key=lambda event: (event.start_iso, event.end_iso)))
        empty_result_proven = (
            not selected_events
            and _empty_result_is_proven(plan, observations=observations)
        )
        if not selected_events and not empty_result_proven:
            raise _read_tool_validation_error(REASON_REQUIRED_READ_NOT_PROVEN)
        calendars = tuple(sorted(state.calendars.values(), key=lambda calendar: calendar.local_id))
        return AgendaReadExecutionResult(
            status=STATUS_OK,
            reason_code=REASON_EXECUTED,
            product_method=plan.product_method,
            calendars=calendars,
            events=selected_events,
            tool_observations=tuple(observations),
            caldav_access=bool(live_caldav),
            nextcloud_access=bool(live_caldav),
            mutation_attempted=False,
            attempted_tool_names=tuple(attempted_tool_names),
            empty_result_proven=empty_result_proven,
        )
    except (ReadToolValidationError, CalDavReadError, CalDavTransportUnavailable) as exc:
        return AgendaReadExecutionResult(
            status=STATUS_ERROR,
            reason_code=getattr(exc, 'reason_code', REASON_TOOL_ERROR),
            product_method=plan.product_method,
            calendars=tuple(sorted(state.calendars.values(), key=lambda calendar: calendar.local_id)),
            events=tuple(sorted(state.events.values(), key=lambda event: (event.start_iso, event.end_iso))),
            tool_observations=tuple(observations),
            caldav_access=bool(live_caldav),
            nextcloud_access=bool(live_caldav),
            mutation_attempted=False,
            error_class=exc.__class__.__name__,
            attempted_tool_names=tuple(attempted_tool_names),
        )


def client_resolution_error_result(
    plan: agent_contract.AgendaAgentPlan,
    *,
    error_class: str = '',
) -> AgendaReadExecutionResult:
    return AgendaReadExecutionResult(
        status=STATUS_ERROR,
        reason_code=REASON_CLIENT_RESOLUTION_ERROR,
        product_method=str(plan.product_method or ''),
        caldav_access=False,
        nextcloud_access=False,
        mutation_attempted=False,
        error_class=str(error_class or ''),
        attempted_tool_names=tuple(str(call.tool_name or '') for call in plan.tool_calls),
    )


def _execute_tool_call(
    call: agent_contract.AgendaToolCall,
    *,
    client: CalDavReadClient,
    state: AgendaReadState,
    plan: agent_contract.AgendaAgentPlan,
    observations: list[Mapping[str, Any]],
):
    tool_name = str(call.tool_name or '')
    params = dict(call.params or {})
    if tool_name == product_methods.TOOL_CALENDAR_LIST:
        return read_tools.calendar_list(client, state=state)
    if tool_name == product_methods.TOOL_EVENT_QUERY_RANGE:
        _ensure_calendars(client, state)
        return _query_range_for_call(client, state=state, params=params, plan=plan)
    if tool_name == product_methods.TOOL_EVENT_SEARCH:
        range_result = _ensure_search_pool(client, state=state, params=params, plan=plan)
        if range_result is not None:
            observations.append(dict(range_result.observation))
        return read_tools.event_search(
            state=state,
            query=str(params.get('query') or ''),
            calendar_id=str(params.get('calendar_id') or '') or None,
            limit=int(params.get('limit') or 10),
        )
    if tool_name == product_methods.TOOL_EVENT_GET:
        return read_tools.event_get(
            state=state,
            event_id=str(params.get('event_id') or ''),
            client=client,
        )
    raise ReadToolValidationError(REASON_TOOL_UNSUPPORTED)


def _ensure_calendars(client: CalDavReadClient, state: AgendaReadState) -> None:
    if state.calendars:
        return
    read_tools.calendar_list(client, state=state)


def _query_range_for_call(
    client: CalDavReadClient,
    *,
    state: AgendaReadState,
    params: Mapping[str, Any],
    plan: agent_contract.AgendaAgentPlan,
):
    if not state.calendars:
        raise _read_tool_validation_error(REASON_NO_CALENDAR_RESOLVED)
    start = str(params.get('start') or plan.time_scope.get('start') or '')
    end = str(params.get('end') or plan.time_scope.get('end') or '')
    timezone_name = str(params.get('timezone') or plan.time_scope.get('timezone') or 'UTC')
    start = _timezone_aware_iso(start, timezone_name=timezone_name)
    end = _timezone_aware_iso(end, timezone_name=timezone_name)
    max_days = int(params.get('max_days') or read_tools.MAX_QUERY_RANGE_DAYS)
    calendar_id = str(params.get('calendar_id') or '').strip()
    if calendar_id and _calendar_id_allowed_by_plan_scope(plan, calendar_id=calendar_id, state=state):
        return read_tools.event_query_range(
            client,
            state=state,
            calendar_id=calendar_id,
            start_iso=start,
            end_iso=end,
            timezone_name=timezone_name,
            max_days=max_days,
        )
    if _plan_has_explicit_calendar_scope(plan):
        raise _read_tool_validation_error(REASON_CALENDAR_SCOPE_UNRESOLVED)

    observations = []
    events: list[CalendarEvent] = []
    for target_id in sorted(state.calendars):
        result = read_tools.event_query_range(
            client,
            state=state,
            calendar_id=target_id,
            start_iso=start,
            end_iso=end,
            timezone_name=timezone_name,
            max_days=max_days,
        )
        observations.append(dict(result.observation))
        events.extend(item for item in result.items if isinstance(item, CalendarEvent))
    merged_events = tuple(sorted(events, key=lambda event: (event.start_iso, event.end_iso, event.event_id)))
    state.add_events(merged_events)
    return _MergedToolResult(
        items=merged_events,
        observation=_merge_observations('event_query_range', observations),
    )


def _plan_has_explicit_calendar_scope(plan: agent_contract.AgendaAgentPlan) -> bool:
    return any(str(item or '').strip() for item in (plan.calendar_scope.get('calendar_ids') or ()))


def _calendar_id_allowed_by_plan_scope(
    plan: agent_contract.AgendaAgentPlan,
    *,
    calendar_id: str,
    state: AgendaReadState,
) -> bool:
    target = str(calendar_id or '').strip()
    if not target or target not in state.calendars:
        return False
    scoped_ids = {str(item or '').strip() for item in (plan.calendar_scope.get('calendar_ids') or ())}
    scoped_ids.discard('')
    return not scoped_ids or target in scoped_ids


def _ensure_search_pool(
    client: CalDavReadClient,
    *,
    state: AgendaReadState,
    params: Mapping[str, Any],
    plan: agent_contract.AgendaAgentPlan,
) -> Any:
    if state.events:
        return None
    _ensure_calendars(client, state)
    start = str(plan.time_scope.get('start') or '')
    end = str(plan.time_scope.get('end') or '')
    if not start or not end:
        return None
    calendar_id = str(params.get('calendar_id') or '').strip()
    return _query_range_for_call(
        client,
        state=state,
        params={
            'calendar_id': calendar_id,
            'start': start,
            'end': end,
            'timezone': plan.time_scope.get('timezone') or 'UTC',
        },
        plan=plan,
    )


def _timezone_aware_iso(value: str, *, timezone_name: str) -> str:
    raw = str(value or '').strip()
    if not raw:
        return raw
    try:
        parsed = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return raw
    if parsed.tzinfo is not None:
        return raw
    try:
        zone = ZoneInfo(str(timezone_name or '').strip() or 'UTC')
    except (ZoneInfoNotFoundError, ValueError):
        zone = timezone.utc
    return parsed.replace(tzinfo=zone).isoformat()


@dataclass(frozen=True)
class _MergedToolResult:
    items: tuple[CalendarEvent, ...]
    observation: Mapping[str, Any]


def _merge_observations(tool_name: str, observations: list[Mapping[str, Any]]) -> dict[str, Any]:
    calendar_hashes: list[str] = []
    event_hashes: list[str] = []
    family_calendar_present = False
    readonly = True
    window_starts: set[str] = set()
    window_ends: set[str] = set()
    timezones: set[str] = set()
    for observation in observations:
        calendar_hashes.extend(str(item) for item in observation.get('calendar_id_hashes') or [])
        event_hashes.extend(str(item) for item in observation.get('event_id_hashes') or [])
        family_calendar_present = family_calendar_present or bool(observation.get('family_calendar_present'))
        readonly = readonly and bool(observation.get('readonly', True))
        window_starts.add(str(observation.get('window_start') or ''))
        window_ends.add(str(observation.get('window_end') or ''))
        timezones.add(str(observation.get('timezone') or ''))
    return {
        'schema_version': 'frida_agenda_read_tools_observation_v1',
        'tool_name': tool_name,
        'status': 'ok',
        'reason_code': 'merged_calendar_range',
        'calendar_count': len(set(calendar_hashes)),
        'calendar_id_hashes': sorted(set(calendar_hashes)),
        'event_count': len(set(event_hashes)),
        'event_id_hashes': sorted(set(event_hashes)),
        'family_calendar_present': family_calendar_present,
        'window_start': window_starts.pop() if len(window_starts) == 1 else '',
        'window_end': window_ends.pop() if len(window_ends) == 1 else '',
        'timezone': timezones.pop() if len(timezones) == 1 else '',
        'readonly': readonly,
        'caldav_access': False,
        'nextcloud_access': False,
        'mutation_attempted': False,
        'content_free': True,
        'redacted': True,
    }


def _read_tool_validation_error(reason_code: str) -> ReadToolValidationError:
    error = ReadToolValidationError(str(reason_code or REASON_TOOL_ERROR))
    error.reason_code = str(reason_code or REASON_TOOL_ERROR)
    return error


def _empty_result_is_proven(
    plan: agent_contract.AgendaAgentPlan,
    *,
    observations: list[Mapping[str, Any]],
) -> bool:
    if plan.product_method == product_methods.METHOD_FIND_NEXT_MATCHING_EVENT:
        return any(
            str(observation.get('tool_name') or '') == 'find_next_matching_event'
            and str(observation.get('status') or '') == STATUS_OK
            and int(observation.get('windows_read') or 0) > 0
            for observation in observations
        )
    range_observations = tuple(
        observation
        for observation in observations
        if str(observation.get('tool_name') or '') == product_methods.TOOL_EVENT_QUERY_RANGE
        and str(observation.get('status') or '') == STATUS_OK
    )
    if not range_observations:
        return False
    scope_start = _normalized_utc_iso(
        str(plan.time_scope.get('start') or ''),
        timezone_name=str(plan.time_scope.get('timezone') or 'UTC'),
    )
    scope_end = _normalized_utc_iso(
        str(plan.time_scope.get('end') or ''),
        timezone_name=str(plan.time_scope.get('timezone') or 'UTC'),
    )
    if not scope_start or not scope_end:
        return False
    return any(
        str(observation.get('window_start') or '') == scope_start
        and str(observation.get('window_end') or '') == scope_end
        and int(observation.get('calendar_count') or 0) > 0
        for observation in range_observations
    )


def _normalized_utc_iso(value: str, *, timezone_name: str) -> str:
    aware = _timezone_aware_iso(value, timezone_name=timezone_name)
    if not aware:
        return ''
    try:
        parsed = datetime.fromisoformat(aware.replace('Z', '+00:00'))
    except ValueError:
        return ''
    if parsed.tzinfo is None:
        return ''
    return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
