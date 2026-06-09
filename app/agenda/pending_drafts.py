from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from agenda import agent_contract
from agenda import product_methods
from agenda.caldav_models import CalendarEvent


PRIVATE_DRAFT_SCHEMA_VERSION = 'frida_agenda_pending_draft_private_v1'

REASON_PENDING_DRAFT_INVALID = 'agenda_pending_draft_invalid'


def build_private_pending_draft(
    plan: agent_contract.AgendaAgentPlan,
    *,
    operation: str,
    verified_event: CalendarEvent | None = None,
) -> dict[str, Any] | str:
    draft = dict(plan.draft or {})
    if operation == 'create':
        return _create_draft(plan, draft)
    if operation == 'update':
        if verified_event is None:
            return REASON_PENDING_DRAFT_INVALID
        return _update_draft(plan, draft, verified_event=verified_event)
    if operation == 'delete':
        if verified_event is None:
            return REASON_PENDING_DRAFT_INVALID
        return _delete_draft(plan, draft, verified_event=verified_event)
    return REASON_PENDING_DRAFT_INVALID


def content_free_draft_summary(draft: Mapping[str, Any]) -> dict[str, Any]:
    target = _mapping(draft.get('target'))
    return {
        'schema_version': 'frida_agenda_pending_draft_summary_v1',
        'draft_schema_version': str(draft.get('schema_version') or ''),
        'operation': str(draft.get('operation') or ''),
        'product_method': str(draft.get('product_method') or ''),
        'calendar_id_hash': agent_contract.sha256_12(draft.get('calendar_id')),
        'target_event_id_hash': agent_contract.sha256_12(target.get('event_id')),
        'target_present': bool(target),
        'start_present': bool(draft.get('start')),
        'end_present': bool(draft.get('end')),
        'all_day': bool(draft.get('all_day')),
        'title_hash': agent_contract.sha256_12(draft.get('title')),
        'title_chars': len(str(draft.get('title') or '')),
        'location_present': bool(draft.get('location')),
        'description_present': bool(draft.get('description')),
        'change_summary_hash': agent_contract.sha256_12(draft.get('change_summary')),
        'change_summary_chars': len(str(draft.get('change_summary') or '')),
        'family_calendar': bool(draft.get('family_calendar') or target.get('family_calendar')),
        'calendar_scope_unverified': bool(draft.get('calendar_scope_unverified') or target.get('calendar_scope_unverified')),
        'technical_ref_present': bool(_mapping(target.get('technical_ref'))),
        'content_free': True,
    }


def _create_draft(plan: agent_contract.AgendaAgentPlan, draft: Mapping[str, Any]) -> dict[str, Any] | str:
    calendar_id = _calendar_id(draft, plan.calendar_scope)
    title = _text(draft.get('title'))
    start = _text(draft.get('start'))
    end = _text(draft.get('end'))
    timezone = _text(draft.get('timezone')) or _text(plan.time_scope.get('timezone'))
    if not title or not calendar_id or not start or not end or not timezone:
        return REASON_PENDING_DRAFT_INVALID
    return _base(plan, operation='create') | {
        'calendar_id': calendar_id,
        'timezone': timezone,
        'start': start,
        'end': end,
        'all_day': bool(draft.get('all_day')),
        'title': title,
        'location': _text(draft.get('location')),
        'description': _text(draft.get('description')),
        'change_summary': '',
        'family_calendar': bool(plan.calendar_scope.get('family_calendar')),
        'family_calendar_classification': 'family' if bool(plan.calendar_scope.get('family_calendar')) else 'unknown',
        'calendar_scope_unverified': not bool(plan.calendar_scope.get('family_calendar')),
        'target': {},
    }


def _update_draft(
    plan: agent_contract.AgendaAgentPlan,
    draft: Mapping[str, Any],
    *,
    verified_event: CalendarEvent,
) -> dict[str, Any] | str:
    change_summary = _text(draft.get('change_summary'))
    target = _event_target(verified_event)
    if not target:
        return REASON_PENDING_DRAFT_INVALID
    next_values = {
        'calendar_id': _text(draft.get('calendar_id')) or verified_event.calendar_id,
        'timezone': _text(draft.get('timezone')) or verified_event.timezone,
        'start': _text(draft.get('start')),
        'end': _text(draft.get('end')),
        'all_day': bool(draft.get('all_day')) if draft.get('all_day') is not None else verified_event.all_day,
        'title': _text(draft.get('title')),
        'location': _text(draft.get('location')),
        'description': _text(draft.get('description')),
        'change_summary': change_summary,
    }
    if not any(_text(next_values.get(key)) for key in ('start', 'end', 'title', 'location', 'description', 'change_summary')):
        return REASON_PENDING_DRAFT_INVALID
    return _base(plan, operation='update') | next_values | {
        'family_calendar': bool(plan.calendar_scope.get('family_calendar')),
        'family_calendar_classification': 'family' if bool(plan.calendar_scope.get('family_calendar')) else 'unknown',
        'calendar_scope_unverified': not bool(plan.calendar_scope.get('family_calendar')),
        'target': target,
    }


def _delete_draft(
    plan: agent_contract.AgendaAgentPlan,
    draft: Mapping[str, Any],
    *,
    verified_event: CalendarEvent,
) -> dict[str, Any] | str:
    target = _event_target(verified_event)
    if not target:
        return REASON_PENDING_DRAFT_INVALID
    return _base(plan, operation='delete') | {
        'calendar_id': verified_event.calendar_id,
        'timezone': verified_event.timezone,
        'start': verified_event.start_iso,
        'end': verified_event.end_iso,
        'all_day': bool(verified_event.all_day),
        'title': '',
        'location': '',
        'description': '',
        'change_summary': _text(draft.get('change_summary')),
        'family_calendar': bool(plan.calendar_scope.get('family_calendar')),
        'family_calendar_classification': 'family' if bool(plan.calendar_scope.get('family_calendar')) else 'unknown',
        'calendar_scope_unverified': not bool(plan.calendar_scope.get('family_calendar')),
        'target': target,
    }


def _base(plan: agent_contract.AgendaAgentPlan, *, operation: str) -> dict[str, Any]:
    return {
        'schema_version': PRIVATE_DRAFT_SCHEMA_VERSION,
        'product_method': str(plan.product_method or ''),
        'operation': operation,
    }


def _event_target(event: CalendarEvent) -> dict[str, Any]:
    if not event.event_id or not event.calendar_id:
        return {}
    target = {
        'event_id': event.event_id,
        'calendar_id': event.calendar_id,
        'timezone': event.timezone,
        'start': event.start_iso,
        'end': event.end_iso,
        'all_day': bool(event.all_day),
        'title': event.summary,
        'location': event.location,
        'description': event.description,
        'family_calendar': False,
        'family_calendar_classification': 'unknown',
        'calendar_scope_unverified': True,
        'technical_ref': {
            'uid': event.uid,
            'etag': event.etag,
            'caldav_path': event.caldav_path,
        },
    }
    return target


def _calendar_id(draft: Mapping[str, Any], calendar_scope: Mapping[str, Any]) -> str:
    explicit = _text(draft.get('calendar_id'))
    if explicit:
        return explicit
    ids = calendar_scope.get('calendar_ids') or ()
    if isinstance(ids, (str, bytes)):
        return ''
    values = [_text(item) for item in ids if _text(item)]
    return values[0] if len(values) == 1 else ''


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _text(value: Any) -> str:
    return str(value or '').strip()
