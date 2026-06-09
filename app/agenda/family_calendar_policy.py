from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from agenda.caldav_models import CalendarSummary


FAMILY_RISK_FLAG = 'family_calendar'
REASON_FAMILY_REINFORCED_REQUIRED = 'agenda_family_calendar_reinforced_confirmation_required'


def plan_marks_family(calendar_scope: Mapping[str, Any]) -> bool:
    return bool(calendar_scope.get('family_calendar'))


def draft_marks_family(draft: Mapping[str, Any]) -> bool:
    target = _mapping(draft.get('target'))
    return bool(draft.get('family_calendar') or target.get('family_calendar'))


def risk_flags_with_family(risk_flags: Iterable[str], *, family_calendar: bool) -> tuple[str, ...]:
    flags: list[str] = []
    for flag in risk_flags:
        value = str(flag or '').strip()
        if value and value not in flags:
            flags.append(value)
    if family_calendar and FAMILY_RISK_FLAG not in flags:
        flags.append(FAMILY_RISK_FLAG)
    return tuple(flags[:12])


def requires_reinforced(operation: str, *, family_calendar: bool) -> bool:
    return bool(family_calendar and operation in {'create', 'delete'})


def with_family_marker(draft: Mapping[str, Any], *, family_calendar: bool) -> dict[str, Any]:
    next_draft = dict(draft)
    next_draft['family_calendar'] = bool(family_calendar)
    target = _mapping(next_draft.get('target'))
    if target:
        target['family_calendar'] = bool(family_calendar)
        next_draft['target'] = target
    return next_draft


def calendar_summary_from_client(client: Any, calendar_id: str) -> CalendarSummary | None:
    local_id = str(calendar_id or '').strip()
    if not local_id:
        return None
    getter = getattr(client, 'calendar_by_local_id', None)
    if callable(getter):
        candidate = getter(local_id)
        return candidate if isinstance(candidate, CalendarSummary) else None
    lister = getattr(client, 'list_calendars', None)
    if not callable(lister):
        return None
    for calendar in lister() or ():
        if isinstance(calendar, CalendarSummary) and calendar.local_id == local_id:
            return calendar
    return None


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}
