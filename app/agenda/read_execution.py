from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from agenda import agent_contract
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
REASON_TOOL_ERROR = 'agenda_readonly_tool_error'
REASON_TOOL_UNSUPPORTED = 'agenda_readonly_tool_unsupported'


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

    @property
    def observation(self) -> dict[str, Any]:
        calendar_ids = tuple(calendar.local_id for calendar in self.calendars)
        event_ids = tuple(event.event_id for event in self.events)
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
            'content_free': True,
            'redacted': True,
        }


def execute_readonly_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    client: CalDavReadClient | None,
    live_caldav: bool = False,
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

    state = AgendaReadState()
    observations: list[Mapping[str, Any]] = []
    selected_events: tuple[CalendarEvent, ...] = ()
    try:
        for call in plan.tool_calls:
            result = _execute_tool_call(call, client=client, state=state, plan=plan)
            observations.append(dict(result.observation))
            if result.items and isinstance(result.items[0], CalendarEvent):
                selected_events = tuple(item for item in result.items if isinstance(item, CalendarEvent))
        if not selected_events:
            selected_events = tuple(sorted(state.events.values(), key=lambda event: (event.start_iso, event.end_iso)))
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
        )


def _execute_tool_call(
    call: agent_contract.AgendaToolCall,
    *,
    client: CalDavReadClient,
    state: AgendaReadState,
    plan: agent_contract.AgendaAgentPlan,
):
    tool_name = str(call.tool_name or '')
    params = dict(call.params or {})
    if tool_name == product_methods.TOOL_CALENDAR_LIST:
        return read_tools.calendar_list(client, state=state)
    if tool_name == product_methods.TOOL_EVENT_QUERY_RANGE:
        _ensure_calendars(client, state)
        return _query_range_for_call(client, state=state, params=params, plan=plan)
    if tool_name == product_methods.TOOL_EVENT_SEARCH:
        _ensure_search_pool(client, state=state, params=params, plan=plan)
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
    start = str(params.get('start') or plan.time_scope.get('start') or '')
    end = str(params.get('end') or plan.time_scope.get('end') or '')
    timezone_name = str(params.get('timezone') or plan.time_scope.get('timezone') or 'UTC')
    max_days = int(params.get('max_days') or read_tools.MAX_QUERY_RANGE_DAYS)
    calendar_id = str(params.get('calendar_id') or '').strip()
    if calendar_id:
        return read_tools.event_query_range(
            client,
            state=state,
            calendar_id=calendar_id,
            start_iso=start,
            end_iso=end,
            timezone_name=timezone_name,
            max_days=max_days,
        )

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


def _ensure_search_pool(
    client: CalDavReadClient,
    *,
    state: AgendaReadState,
    params: Mapping[str, Any],
    plan: agent_contract.AgendaAgentPlan,
) -> None:
    if state.events:
        return
    _ensure_calendars(client, state)
    start = str(plan.time_scope.get('start') or '')
    end = str(plan.time_scope.get('end') or '')
    if not start or not end:
        return
    calendar_id = str(params.get('calendar_id') or '').strip()
    _query_range_for_call(
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


@dataclass(frozen=True)
class _MergedToolResult:
    items: tuple[CalendarEvent, ...]
    observation: Mapping[str, Any]


def _merge_observations(tool_name: str, observations: list[Mapping[str, Any]]) -> dict[str, Any]:
    calendar_hashes: list[str] = []
    event_hashes: list[str] = []
    family_calendar_present = False
    readonly = True
    for observation in observations:
        calendar_hashes.extend(str(item) for item in observation.get('calendar_id_hashes') or [])
        event_hashes.extend(str(item) for item in observation.get('event_id_hashes') or [])
        family_calendar_present = family_calendar_present or bool(observation.get('family_calendar_present'))
        readonly = readonly and bool(observation.get('readonly', True))
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
        'readonly': readonly,
        'caldav_access': False,
        'nextcloud_access': False,
        'mutation_attempted': False,
        'content_free': True,
        'redacted': True,
    }
