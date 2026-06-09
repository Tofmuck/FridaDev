from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from agenda.caldav_models import CalendarSummary


FAMILY_RISK_FLAG = 'family_calendar'
UNVERIFIED_RISK_FLAG = 'calendar_scope_unverified'
CLASSIFICATION_FAMILY = 'family'
CLASSIFICATION_NON_FAMILY = 'non_family'
CLASSIFICATION_UNKNOWN = 'unknown'
REASON_FAMILY_REINFORCED_REQUIRED = 'agenda_family_calendar_reinforced_confirmation_required'
REASON_UNVERIFIED_REINFORCED_REQUIRED = 'agenda_calendar_scope_unverified_reinforced_confirmation_required'


def plan_marks_family(calendar_scope: Mapping[str, Any]) -> bool:
    return bool(calendar_scope.get('family_calendar'))


def draft_marks_family(draft: Mapping[str, Any]) -> bool:
    return draft_calendar_classification(draft) == CLASSIFICATION_FAMILY


def draft_calendar_classification(draft: Mapping[str, Any]) -> str:
    target = _mapping(draft.get('target'))
    for value in (target.get('family_calendar_classification'), draft.get('family_calendar_classification')):
        normalized = normalize_classification(value)
        if normalized != CLASSIFICATION_UNKNOWN:
            return normalized
    if bool(draft.get('family_calendar') or target.get('family_calendar')):
        return CLASSIFICATION_FAMILY
    if bool(draft.get('calendar_scope_unverified') or target.get('calendar_scope_unverified')):
        return CLASSIFICATION_UNKNOWN
    return CLASSIFICATION_UNKNOWN


def risk_flags_with_family(risk_flags: Iterable[str], *, family_calendar: bool) -> tuple[str, ...]:
    return risk_flags_with_classification(
        risk_flags,
        classification=CLASSIFICATION_FAMILY if family_calendar else CLASSIFICATION_NON_FAMILY,
    )


def risk_flags_with_classification(risk_flags: Iterable[str], *, classification: str) -> tuple[str, ...]:
    flags: list[str] = []
    for flag in risk_flags:
        value = str(flag or '').strip()
        if value and value not in flags:
            flags.append(value)
    normalized = normalize_classification(classification)
    if normalized == CLASSIFICATION_FAMILY and FAMILY_RISK_FLAG not in flags:
        flags.append(FAMILY_RISK_FLAG)
    if normalized == CLASSIFICATION_UNKNOWN and UNVERIFIED_RISK_FLAG not in flags:
        flags.append(UNVERIFIED_RISK_FLAG)
    return tuple(flags[:12])


def requires_reinforced(operation: str, *, family_calendar: bool = False, classification: str = '') -> bool:
    normalized = CLASSIFICATION_FAMILY if family_calendar else normalize_classification(classification)
    return bool(normalized in {CLASSIFICATION_FAMILY, CLASSIFICATION_UNKNOWN} and operation in {'create', 'delete'})


def with_family_marker(draft: Mapping[str, Any], *, family_calendar: bool) -> dict[str, Any]:
    return with_classification_marker(
        draft,
        classification=CLASSIFICATION_FAMILY if family_calendar else CLASSIFICATION_NON_FAMILY,
    )


def with_classification_marker(draft: Mapping[str, Any], *, classification: str) -> dict[str, Any]:
    normalized = normalize_classification(classification)
    next_draft = dict(draft)
    next_draft['family_calendar'] = normalized == CLASSIFICATION_FAMILY
    next_draft['family_calendar_classification'] = normalized
    next_draft['calendar_scope_unverified'] = normalized == CLASSIFICATION_UNKNOWN
    target = _mapping(next_draft.get('target'))
    if target:
        target['family_calendar'] = normalized == CLASSIFICATION_FAMILY
        target['family_calendar_classification'] = normalized
        target['calendar_scope_unverified'] = normalized == CLASSIFICATION_UNKNOWN
        next_draft['target'] = target
    return next_draft


def classification_from_plan(calendar_scope: Mapping[str, Any]) -> str:
    return CLASSIFICATION_FAMILY if plan_marks_family(calendar_scope) else CLASSIFICATION_UNKNOWN


def classification_from_summary(calendar: CalendarSummary | None) -> str:
    if calendar is None:
        return CLASSIFICATION_UNKNOWN
    if bool(calendar.family_calendar):
        return CLASSIFICATION_FAMILY
    return normalize_classification(getattr(calendar, 'family_calendar_classification', CLASSIFICATION_UNKNOWN))


def normalize_classification(value: Any) -> str:
    normalized = str(value or '').strip().lower()
    if normalized in {CLASSIFICATION_FAMILY, 'family_calendar', 'shared', 'shared_family'}:
        return CLASSIFICATION_FAMILY
    if normalized in {CLASSIFICATION_NON_FAMILY, 'nonfamily', 'non_family_calendar', 'private'}:
        return CLASSIFICATION_NON_FAMILY
    return CLASSIFICATION_UNKNOWN


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
