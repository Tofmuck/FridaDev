from __future__ import annotations

from dataclasses import dataclass


TOOL_CALENDAR_LIST = 'calendar_list'
TOOL_EVENT_QUERY_RANGE = 'event_query_range'
TOOL_EVENT_GET = 'event_get'
TOOL_EVENT_SEARCH = 'event_search'

READ_ONLY_TOOLS = {
    TOOL_CALENDAR_LIST,
    TOOL_EVENT_QUERY_RANGE,
    TOOL_EVENT_GET,
    TOOL_EVENT_SEARCH,
}

METHOD_READ_TODAY = 'read_today'
METHOD_READ_TOMORROW = 'read_tomorrow'
METHOD_READ_EXPLICIT_DATE = 'read_explicit_date'
METHOD_READ_WEEK = 'read_week'
METHOD_SEARCH_EVENTS = 'search_events'
METHOD_FIND_NEXT_MATCHING_EVENT = 'find_next_matching_event'
METHOD_EVENT_DETAILS = 'event_details'
METHOD_SUMMARIZE_DAY = 'summarize_day'
METHOD_FIND_AVAILABILITY = 'find_availability'
METHOD_CLARIFY_AGENDA_REQUEST = 'clarify_agenda_request'
METHOD_DESCRIBE_AGENDA_CAPABILITIES = 'describe_agenda_capabilities'
METHOD_PROPOSE_CREATE_EVENT = 'propose_create_event'
METHOD_PROPOSE_UPDATE_EVENT = 'propose_update_event'
METHOD_PROPOSE_DELETE_EVENT = 'propose_delete_event'
METHOD_PROPOSE_FREE_SLOT = 'propose_free_slot'
METHOD_PROPOSE_RESCHEDULE = 'propose_reschedule'
METHOD_CONFIRM_CREATE_EVENT = 'confirm_create_event'
METHOD_CONFIRM_UPDATE_EVENT = 'confirm_update_event'
METHOD_CONFIRM_DELETE_EVENT = 'confirm_delete_event'
METHOD_CANCEL_PENDING_AGENDA_ACTION = 'cancel_pending_agenda_action'

FAMILY_READ = 'read'
FAMILY_CLARIFY = 'clarify'
FAMILY_PROPOSE = 'propose'
FAMILY_MUTATE = 'mutate'
FAMILY_CONTEXT = 'context'


@dataclass(frozen=True)
class AgendaProductMethod:
    name: str
    family: str
    mutation_kind: str = 'none'
    allowed_tools: frozenset[str] = frozenset()

    @property
    def is_mutation(self) -> bool:
        return self.family == FAMILY_MUTATE


_METHODS = {
    METHOD_READ_TODAY: AgendaProductMethod(
        METHOD_READ_TODAY,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_READ_TOMORROW: AgendaProductMethod(
        METHOD_READ_TOMORROW,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_READ_EXPLICIT_DATE: AgendaProductMethod(
        METHOD_READ_EXPLICIT_DATE,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_READ_WEEK: AgendaProductMethod(
        METHOD_READ_WEEK,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_SEARCH_EVENTS: AgendaProductMethod(
        METHOD_SEARCH_EVENTS,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_EVENT_QUERY_RANGE, TOOL_EVENT_SEARCH}),
    ),
    METHOD_FIND_NEXT_MATCHING_EVENT: AgendaProductMethod(
        METHOD_FIND_NEXT_MATCHING_EVENT,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_EVENT_QUERY_RANGE, TOOL_EVENT_SEARCH}),
    ),
    METHOD_EVENT_DETAILS: AgendaProductMethod(
        METHOD_EVENT_DETAILS,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_EVENT_GET, TOOL_EVENT_SEARCH}),
    ),
    METHOD_SUMMARIZE_DAY: AgendaProductMethod(
        METHOD_SUMMARIZE_DAY,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_FIND_AVAILABILITY: AgendaProductMethod(
        METHOD_FIND_AVAILABILITY,
        FAMILY_READ,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_CLARIFY_AGENDA_REQUEST: AgendaProductMethod(METHOD_CLARIFY_AGENDA_REQUEST, FAMILY_CLARIFY),
    METHOD_DESCRIBE_AGENDA_CAPABILITIES: AgendaProductMethod(METHOD_DESCRIBE_AGENDA_CAPABILITIES, FAMILY_CONTEXT),
    METHOD_PROPOSE_CREATE_EVENT: AgendaProductMethod(
        METHOD_PROPOSE_CREATE_EVENT,
        FAMILY_PROPOSE,
        mutation_kind='create',
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_PROPOSE_UPDATE_EVENT: AgendaProductMethod(
        METHOD_PROPOSE_UPDATE_EVENT,
        FAMILY_PROPOSE,
        mutation_kind='update',
        allowed_tools=frozenset({TOOL_EVENT_GET, TOOL_EVENT_SEARCH, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_PROPOSE_DELETE_EVENT: AgendaProductMethod(
        METHOD_PROPOSE_DELETE_EVENT,
        FAMILY_PROPOSE,
        mutation_kind='delete',
        allowed_tools=frozenset({TOOL_EVENT_GET, TOOL_EVENT_SEARCH, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_PROPOSE_FREE_SLOT: AgendaProductMethod(
        METHOD_PROPOSE_FREE_SLOT,
        FAMILY_PROPOSE,
        allowed_tools=frozenset({TOOL_CALENDAR_LIST, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_PROPOSE_RESCHEDULE: AgendaProductMethod(
        METHOD_PROPOSE_RESCHEDULE,
        FAMILY_PROPOSE,
        mutation_kind='update',
        allowed_tools=frozenset({TOOL_EVENT_GET, TOOL_EVENT_SEARCH, TOOL_EVENT_QUERY_RANGE}),
    ),
    METHOD_CONFIRM_CREATE_EVENT: AgendaProductMethod(METHOD_CONFIRM_CREATE_EVENT, FAMILY_MUTATE, mutation_kind='create'),
    METHOD_CONFIRM_UPDATE_EVENT: AgendaProductMethod(METHOD_CONFIRM_UPDATE_EVENT, FAMILY_MUTATE, mutation_kind='update'),
    METHOD_CONFIRM_DELETE_EVENT: AgendaProductMethod(METHOD_CONFIRM_DELETE_EVENT, FAMILY_MUTATE, mutation_kind='delete'),
    METHOD_CANCEL_PENDING_AGENDA_ACTION: AgendaProductMethod(METHOD_CANCEL_PENDING_AGENDA_ACTION, FAMILY_CONTEXT),
}

PRODUCT_METHODS = frozenset(_METHODS)
CONFIRMED_MUTATION_METHODS = frozenset(
    method.name for method in _METHODS.values() if method.is_mutation
)


def get_method(name: str) -> AgendaProductMethod | None:
    return _METHODS.get(str(name or '').strip())


def allowed_tools_for_method(name: str) -> frozenset[str]:
    method = get_method(name)
    return method.allowed_tools if method is not None else frozenset()
