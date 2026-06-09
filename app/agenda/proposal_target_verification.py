from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agenda import agent_contract
from agenda import family_calendar_policy
from agenda import product_methods
from agenda import read_tools
from agenda.caldav_models import AgendaReadState, CalendarEvent, CalendarSummary, ReadToolValidationError


REASON_TARGET_NOT_VERIFIED = 'agenda_pending_target_not_verified'


@dataclass(frozen=True)
class ProposalTargetVerificationResult:
    event: CalendarEvent | None = None
    calendar: CalendarSummary | None = None
    attempted_tool_names: tuple[str, ...] = ()
    error_class: str = ''
    caldav_access: bool = False
    nextcloud_access: bool = False

    @property
    def verified(self) -> bool:
        return self.event is not None


def verify_target_event(
    plan: agent_contract.AgendaAgentPlan,
    *,
    client: Any,
    live_caldav: bool = False,
) -> ProposalTargetVerificationResult:
    target_event_id = target_event_id_for_plan(plan)
    if not target_event_id or client is None:
        return ProposalTargetVerificationResult(caldav_access=False, nextcloud_access=False)

    special = _verify_with_local_resolver(client, target_event_id)
    if special.event is not None or special.error_class:
        return special

    state = AgendaReadState()
    attempted: list[str] = []
    try:
        for call in plan.tool_calls:
            tool_name = str(call.tool_name or '')
            attempted.append(tool_name)
            if tool_name == product_methods.TOOL_CALENDAR_LIST:
                read_tools.calendar_list(client, state=state)
            elif tool_name == product_methods.TOOL_EVENT_QUERY_RANGE:
                _ensure_calendars(client, state)
                _query_range_for_call(client, state=state, params=call.params, plan=plan)
            elif tool_name == product_methods.TOOL_EVENT_SEARCH:
                _ensure_search_pool(client, state=state, params=call.params, plan=plan)
                read_tools.event_search(
                    state=state,
                    query=str(call.params.get('query') or ''),
                    calendar_id=str(call.params.get('calendar_id') or '') or None,
                    limit=int(call.params.get('limit') or 10),
                )
            elif tool_name == product_methods.TOOL_EVENT_GET:
                result = read_tools.event_get(state=state, event_id=target_event_id, client=client)
                event = next((item for item in result.items if isinstance(item, CalendarEvent)), None)
                return ProposalTargetVerificationResult(
                    event=event if event is not None and event.event_id == target_event_id else None,
                    calendar=state.calendars.get(event.calendar_id) if event is not None else None,
                    attempted_tool_names=tuple(attempted),
                    caldav_access=bool(live_caldav),
                    nextcloud_access=bool(live_caldav),
                )
            else:
                raise ReadToolValidationError('unsupported proposal target verification tool')
    except Exception as exc:
        return ProposalTargetVerificationResult(
            attempted_tool_names=tuple(attempted),
            error_class=exc.__class__.__name__,
            caldav_access=bool(live_caldav),
            nextcloud_access=bool(live_caldav),
        )
    return ProposalTargetVerificationResult(
        attempted_tool_names=tuple(attempted),
        caldav_access=bool(live_caldav),
        nextcloud_access=bool(live_caldav),
    )


def _verify_with_local_resolver(client: Any, event_id: str) -> ProposalTargetVerificationResult:
    getter = getattr(client, 'get_event_by_local_id', None)
    if not callable(getter):
        return ProposalTargetVerificationResult()
    try:
        event = getter(event_id)
    except Exception as exc:
        return ProposalTargetVerificationResult(
            attempted_tool_names=(product_methods.TOOL_EVENT_GET,),
            error_class=exc.__class__.__name__,
        )
    calendar = (
        family_calendar_policy.calendar_summary_from_client(client, event.calendar_id)
        if isinstance(event, CalendarEvent)
        else None
    )
    return ProposalTargetVerificationResult(
        event=event if isinstance(event, CalendarEvent) and event.event_id == event_id else None,
        calendar=calendar,
        attempted_tool_names=(product_methods.TOOL_EVENT_GET,),
    )


def target_event_id_for_plan(plan: agent_contract.AgendaAgentPlan) -> str:
    event_ids = [
        str(dict(call.params or {}).get('event_id') or '').strip()
        for call in plan.tool_calls
        if call.tool_name == product_methods.TOOL_EVENT_GET
    ]
    event_ids = [event_id for event_id in event_ids if event_id]
    return event_ids[0] if len(event_ids) == 1 else ''


def has_executable_target_verification_sequence(plan: agent_contract.AgendaAgentPlan) -> bool:
    if not target_event_id_for_plan(plan):
        return False
    tool_names = [str(call.tool_name or '') for call in plan.tool_calls]
    try:
        range_index = tool_names.index(product_methods.TOOL_EVENT_QUERY_RANGE)
        get_index = tool_names.index(product_methods.TOOL_EVENT_GET)
    except ValueError:
        return False
    return range_index < get_index


def _ensure_calendars(client: Any, state: AgendaReadState) -> None:
    if state.calendars:
        return
    read_tools.calendar_list(client, state=state)


def _query_range_for_call(
    client: Any,
    *,
    state: AgendaReadState,
    params: Mapping[str, Any],
    plan: agent_contract.AgendaAgentPlan,
) -> None:
    start = str(params.get('start') or plan.time_scope.get('start') or '')
    end = str(params.get('end') or plan.time_scope.get('end') or '')
    timezone_name = str(params.get('timezone') or plan.time_scope.get('timezone') or 'UTC')
    calendar_id = str(params.get('calendar_id') or '').strip()
    max_days = int(params.get('max_days') or read_tools.MAX_QUERY_RANGE_DAYS)
    if calendar_id:
        read_tools.event_query_range(
            client,
            state=state,
            calendar_id=calendar_id,
            start_iso=start,
            end_iso=end,
            timezone_name=timezone_name,
            max_days=max_days,
        )
        return
    for target_id in sorted(state.calendars):
        read_tools.event_query_range(
            client,
            state=state,
            calendar_id=target_id,
            start_iso=start,
            end_iso=end,
            timezone_name=timezone_name,
            max_days=max_days,
        )


def _ensure_search_pool(
    client: Any,
    *,
    state: AgendaReadState,
    params: Mapping[str, Any],
    plan: agent_contract.AgendaAgentPlan,
) -> None:
    if state.events:
        return
    _ensure_calendars(client, state)
    _query_range_for_call(
        client,
        state=state,
        params={
            'calendar_id': str(params.get('calendar_id') or '').strip(),
            'start': plan.time_scope.get('start') or '',
            'end': plan.time_scope.get('end') or '',
            'timezone': plan.time_scope.get('timezone') or 'UTC',
        },
        plan=plan,
    )
