from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Mapping

from agenda import agent_contract
from agenda import product_methods
from agenda.caldav_models import CalendarEvent


SOURCE_AGENDA_READONLY_RESPONSE = 'agenda_readonly_response'
REASON_AGENDA_READONLY_FINAL = 'agenda_readonly_final_response'


@dataclass(frozen=True)
class AgendaFinalResponseLock:
    ok: bool
    content: str = field(default='', repr=False, compare=False)
    source: str = SOURCE_AGENDA_READONLY_RESPONSE
    reason_code: str = REASON_AGENDA_READONLY_FINAL
    meta: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    observability: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def to_message_meta(self) -> dict[str, Any]:
        return dict(self.meta)

    def to_observability(self) -> dict[str, Any]:
        payload = {
            'status': 'authorized' if self.ok else 'blocked',
            'source': self.source,
            'reason_code': self.reason_code,
            'content_present': bool(self.content),
            'content_chars': len(self.content),
            'content_hash': agent_contract.sha256_12(self.content),
            'content_free': True,
        }
        payload.update(dict(self.observability or {}))
        return payload


def build_final_response_lock(
    *,
    plan: agent_contract.AgendaAgentPlan,
    execution_result: Any,
) -> AgendaFinalResponseLock | None:
    if str(getattr(execution_result, 'status', '') or '') != 'ok':
        return None
    content = render_readonly_answer(plan=plan, execution_result=execution_result)
    if not content:
        return None
    meta = _message_meta(plan=plan, execution_result=execution_result)
    observability = _lock_observability(meta)
    return AgendaFinalResponseLock(
        ok=True,
        content=_compose_surface(plan.surface_intro, content, plan.surface_outro),
        meta=meta,
        observability=observability,
    )


def render_readonly_answer(
    *,
    plan: agent_contract.AgendaAgentPlan,
    execution_result: Any,
) -> str:
    events = tuple(getattr(execution_result, 'events', ()) or ())
    method = str(plan.product_method or '')
    if method == product_methods.METHOD_EVENT_DETAILS:
        return _render_event_details(events)
    if method == product_methods.METHOD_SEARCH_EVENTS:
        return _render_search_events(events)
    if method == product_methods.METHOD_READ_TOMORROW:
        return _render_window_events(events, empty="Je ne vois rien dans ton agenda demain.")
    if method == product_methods.METHOD_READ_TODAY:
        return _render_window_events(events, empty="Je ne vois rien dans ton agenda aujourd'hui.")
    if method in {
        product_methods.METHOD_READ_EXPLICIT_DATE,
        product_methods.METHOD_READ_WEEK,
        product_methods.METHOD_SUMMARIZE_DAY,
        product_methods.METHOD_FIND_AVAILABILITY,
    }:
        return _render_window_events(events, empty="Je ne vois rien dans cette fenetre d'agenda.")
    return ''


def _render_window_events(events: tuple[CalendarEvent, ...], *, empty: str) -> str:
    if not events:
        return empty
    lines = ["Voila ce que je vois dans ton agenda :"]
    for event in events[:10]:
        lines.append(_event_line(event))
    if len(events) > 10:
        lines.append(f"Et {len(events) - 10} autre(s) evenement(s) dans la fenetre.")
    return "\n".join(lines)


def _render_search_events(events: tuple[CalendarEvent, ...]) -> str:
    if not events:
        return "Je n'ai pas trouve d'evenement correspondant dans la fenetre lue."
    if len(events) == 1:
        return "J'ai trouve un evenement correspondant :\n" + _event_line(events[0])
    lines = ["J'ai trouve plusieurs evenements correspondants :"]
    for event in events[:10]:
        lines.append(_event_line(event))
    if len(events) > 10:
        lines.append(f"Et {len(events) - 10} autre(s) resultat(s).")
    return "\n".join(lines)


def _render_event_details(events: tuple[CalendarEvent, ...]) -> str:
    if not events:
        return "Je n'ai pas retrouve cet evenement dans l'etat Agenda courant."
    if len(events) > 1:
        lines = ["J'ai trouve plusieurs evenements possibles :"]
        for event in events[:5]:
            lines.append(_event_line(event))
        lines.append("Dis-moi lequel tu veux ouvrir.")
        return "\n".join(lines)
    event = events[0]
    lines = ["Voici le detail que j'ai retrouve :", _event_line(event)]
    location = str(event.location or '').strip()
    description = str(event.description or '').strip()
    if location:
        lines.append(f"Lieu : {location}")
    if description:
        lines.append(description)
    return "\n".join(lines)


def _event_line(event: CalendarEvent) -> str:
    label = _time_label(event)
    summary = str(event.summary or '').strip() or 'Evenement sans titre'
    location = str(event.location or '').strip()
    suffix = f" ({location})" if location else ''
    if label:
        return f"- {label} - {summary}{suffix}"
    return f"- {summary}{suffix}"


def _time_label(event: CalendarEvent) -> str:
    start = _parse_iso(event.start_iso)
    end = _parse_iso(event.end_iso)
    if start is None:
        return ''
    if end is None:
        return start.strftime('%H:%M')
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def _parse_iso(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    except ValueError:
        return None


def _compose_surface(intro: str, content: str, outro: str) -> str:
    return "\n\n".join(
        part
        for part in (str(intro or '').strip(), str(content or '').strip(), str(outro or '').strip())
        if part
    )


def _message_meta(*, plan: agent_contract.AgendaAgentPlan, execution_result: Any) -> dict[str, Any]:
    observation = dict(getattr(execution_result, 'observation', {}) or {})
    return {
        'source': SOURCE_AGENDA_READONLY_RESPONSE,
        'reason_code': REASON_AGENDA_READONLY_FINAL,
        'agenda_schema_version': agent_contract.SCHEMA_VERSION,
        'agenda_product_method': str(plan.product_method or ''),
        'agenda_tool_names': list(observation.get('tool_names') or []),
        'agenda_tool_count': int(observation.get('tool_count') or 0),
        'agenda_calendar_count': int(observation.get('calendar_count') or 0),
        'agenda_event_count': int(observation.get('event_count') or 0),
        'agenda_calendar_id_hashes': list(observation.get('calendar_id_hashes') or []),
        'agenda_event_id_hashes': list(observation.get('event_id_hashes') or []),
        'agenda_caldav_access': bool(observation.get('caldav_access')),
        'agenda_nextcloud_access': bool(observation.get('nextcloud_access')),
        'agenda_mutation_attempted': False,
        'agenda_final_lock_authorized': True,
        'agenda_final_lock_reason_code': REASON_AGENDA_READONLY_FINAL,
        'content_free_meta': True,
    }


def _lock_observability(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'agenda_product_method': str(meta.get('agenda_product_method') or ''),
        'agenda_tool_names': list(meta.get('agenda_tool_names') or []),
        'agenda_tool_count': int(meta.get('agenda_tool_count') or 0),
        'agenda_event_count': int(meta.get('agenda_event_count') or 0),
        'agenda_calendar_count': int(meta.get('agenda_calendar_count') or 0),
        'agenda_caldav_access': bool(meta.get('agenda_caldav_access')),
        'agenda_nextcloud_access': bool(meta.get('agenda_nextcloud_access')),
        'agenda_mutation_attempted': False,
        'content_free': True,
    }
