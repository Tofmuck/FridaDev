from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from agenda import agent_contract
from agenda import family_calendar_policy
from agenda import pending_store
from agenda import product_methods
from agenda import proposal_execution
from agenda import write_execution
from agenda.response_rendering import AgendaFinalResponseLock


SOURCE_AGENDA_PENDING_RESPONSE = 'agenda_pending_proposal_response'
REASON_AGENDA_PENDING_FINAL = 'agenda_pending_final_response'


def build_proposal_response_lock(
    *,
    plan: agent_contract.AgendaAgentPlan,
    proposal_result: proposal_execution.AgendaProposalExecutionResult,
) -> AgendaFinalResponseLock | None:
    content = render_proposal_answer(plan=plan, proposal_result=proposal_result)
    if not content:
        return None
    meta = _message_meta(plan=plan, proposal_result=proposal_result)
    observability = _lock_observability(meta)
    return AgendaFinalResponseLock(
        ok=True,
        content=_compose_surface(plan.surface_intro, content, plan.surface_outro),
        source=SOURCE_AGENDA_PENDING_RESPONSE,
        reason_code=REASON_AGENDA_PENDING_FINAL,
        meta=meta,
        observability=observability,
    )


def render_proposal_answer(
    *,
    plan: agent_contract.AgendaAgentPlan,
    proposal_result: proposal_execution.AgendaProposalExecutionResult,
) -> str:
    reason = str(proposal_result.reason_code or '')
    if reason == proposal_execution.REASON_PENDING_CREATED:
        return _render_created(proposal_result)
    if reason == proposal_execution.REASON_PENDING_CANCELLED:
        return _render_cancelled(proposal_result)
    if reason in {proposal_execution.REASON_TARGET_AMBIGUOUS, proposal_execution.REASON_TARGET_NOT_VERIFIED}:
        return (
            "Je ne peux pas preparer cette proposition sans avoir verifie l'evenement cible. "
            "Dis-moi lequel viser, et je te preparerai une proposition sans rien modifier."
        )
    if reason == proposal_execution.REASON_PENDING_DRAFT_INVALID:
        return (
            "Je ne peux pas preparer une proposition fiable avec ces informations. "
            "Donne-moi les details manquants, et je te preparerai un brouillon sans rien modifier."
        )
    if reason == proposal_execution.REASON_PENDING_EXPIRED:
        return "Cette proposition est expiree. Je n'ai rien modifie dans ton agenda."
    if reason == proposal_execution.REASON_PENDING_NOT_FOUND:
        return "Je ne retrouve pas cette proposition en attente. Je n'ai rien modifie dans ton agenda."
    if reason == write_execution.REASON_WRITE_EXECUTED:
        return _render_write_executed(proposal_result)
    if reason == write_execution.REASON_WRITE_PRIVATE_DRAFT_MISSING:
        return (
            "Je n'ai plus le brouillon technique prive de cette proposition. "
            "Je n'ai rien modifie dans ton agenda; il faut refaire une proposition."
        )
    if reason == write_execution.REASON_WRITE_CLIENT_UNAVAILABLE:
        return (
            "L'ecriture dans l'agenda n'est pas encore activee ici. "
            "Je n'ai rien modifie dans ton agenda."
        )
    if reason == write_execution.REASON_WRITE_ETAG_MISSING:
        return (
            "Je n'ai pas une version verifiee assez recente de cet evenement. "
            "Je n'ai rien modifie; relis l'evenement puis refais une proposition."
        )
    if reason == write_execution.REASON_WRITE_UPDATE_PRESERVATION_REQUIRED:
        return (
            "Je ne peux pas encore modifier cet evenement sans risquer de perdre des details du calendrier. "
            "Je n'ai rien modifie dans ton agenda."
        )
    if reason == write_execution.REASON_WRITE_REINFORCED_REQUIRED:
        return "Cette suppression demande une confirmation renforcee. Je n'ai rien supprime dans ton agenda."
    if reason == write_execution.REASON_WRITE_FAMILY_REINFORCED_REQUIRED:
        return (
            "Ce calendrier est partage ou familial: il faut une confirmation explicite renforcee. "
            "Je n'ai rien modifie dans ton agenda."
        )
    if reason == write_execution.REASON_WRITE_UNVERIFIED_REINFORCED_REQUIRED:
        return (
            "Je ne suis pas assez sure du type de ce calendrier. "
            "Il faut une confirmation explicite renforcee; je n'ai rien modifie dans ton agenda."
        )
    if reason == write_execution.REASON_WRITE_CONFLICT:
        return (
            "Le calendrier a change depuis la proposition. "
            "Je n'ai rien modifie; relis l'evenement puis refais une proposition."
        )
    if reason in {write_execution.REASON_WRITE_TARGET_MISSING, write_execution.REASON_WRITE_CALENDAR_TARGET_MISSING}:
        return (
            "Il manque la cible technique verifiee pour executer cette confirmation. "
            "Je n'ai rien modifie dans ton agenda."
        )
    if reason == proposal_execution.REASON_CONFIRMATION_NOT_EXECUTABLE:
        return (
            "Je ne peux pas encore executer cette confirmation ici. "
            "Je n'ai rien cree, modifie ni supprime dans ton agenda."
        )
    if str(plan.product_method or '') in product_methods.CONFIRMED_MUTATION_METHODS:
        return (
            "L'ecriture dans l'agenda n'est pas encore activee ici. "
            "Je n'ai rien modifie dans ton agenda."
        )
    return ''


def _render_created(result: proposal_execution.AgendaProposalExecutionResult) -> str:
    reference = str(result.pending_action_id or '')
    expires = str(result.pending_expires_at or '')
    draft = dict(result.draft or {})
    if result.operation == pending_store.OPERATION_CREATE:
        lines = [
            "Je peux te preparer cette creation d'evenement :",
            *_creation_lines(draft),
            "Rien n'a encore ete ajoute au calendrier.",
            "Confirme-moi si tu veux que je le fasse.",
        ]
    elif result.operation == pending_store.OPERATION_UPDATE:
        lines = [
            "Je peux te preparer cette modification d'evenement :",
            *_update_lines(draft),
            "Rien n'a encore ete modifie dans le calendrier.",
            "Confirme-moi si tu veux que je le fasse.",
        ]
    elif result.operation == pending_store.OPERATION_DELETE:
        lines = [
            "Je peux te preparer cette suppression, mais elle demande une confirmation renforcee :",
            *_delete_lines(draft),
            "Rien n'a ete supprime du calendrier.",
            "Confirme explicitement si tu veux vraiment que je le fasse.",
        ]
    else:
        return ''
    if reference:
        lines.append(f"Reference de confirmation : {reference}.")
    if expires:
        lines.append(f"Expiration : {expires}.")
    if family_calendar_policy.draft_marks_family(draft) or family_calendar_policy.FAMILY_RISK_FLAG in result.risk_flags:
        lines.append("Ce calendrier est partage ou familial: je demanderai une confirmation explicite renforcee.")
    elif family_calendar_policy.UNVERIFIED_RISK_FLAG in result.risk_flags:
        lines.append(
            "Je ne suis pas encore assez sure du type de ce calendrier: "
            "je demanderai une confirmation explicite renforcee."
        )
    return "\n".join(lines)


def _render_write_executed(result: proposal_execution.AgendaProposalExecutionResult) -> str:
    draft = dict(result.draft or {})
    if result.operation == pending_store.OPERATION_CREATE:
        lines = ["C'est cree dans ton agenda.", *_creation_lines(draft)]
    elif result.operation == pending_store.OPERATION_UPDATE:
        lines = ["J'ai modifie le rendez-vous.", *_update_lines(draft)]
    elif result.operation == pending_store.OPERATION_DELETE:
        lines = ["C'est supprime de ton agenda.", *_delete_lines(draft)]
    else:
        return "C'est fait dans ton agenda."
    return "\n".join(line for line in lines if line)


def _creation_lines(draft: Mapping[str, Any]) -> list[str]:
    lines = []
    title = _text(draft.get('title')) or 'Evenement sans titre'
    lines.append(f"- Quoi : {title}")
    when = _time_range(draft)
    if when:
        lines.append(f"- Quand : {when}")
    calendar = _text(draft.get('calendar_id'))
    if calendar:
        lines.append(f"- Calendrier : {calendar}")
    location = _text(draft.get('location'))
    if location:
        lines.append(f"- Lieu : {location}")
    description = _text(draft.get('description'))
    if description:
        lines.append(f"- Note : {description}")
    return lines


def _update_lines(draft: Mapping[str, Any]) -> list[str]:
    lines = _target_lines(draft)
    change = _text(draft.get('change_summary'))
    if change:
        lines.append(f"- Changement : {change}")
    when = _time_range(draft)
    if when:
        lines.append(f"- Nouveau creneau : {when}")
    for label, key in (('Nouveau titre', 'title'), ('Nouveau lieu', 'location'), ('Nouvelle note', 'description')):
        value = _text(draft.get(key))
        if value:
            lines.append(f"- {label} : {value}")
    return lines or ["- Cible verifiee, changement a confirmer."]


def _delete_lines(draft: Mapping[str, Any]) -> list[str]:
    lines = _target_lines(draft)
    return lines or ["- Evenement cible verifie."]


def _target_lines(draft: Mapping[str, Any]) -> list[str]:
    target = dict(draft.get('target') or {})
    lines = []
    title = _text(target.get('title')) or 'Evenement sans titre'
    lines.append(f"- Cible : {title}")
    when = _time_range(target)
    if when:
        lines.append(f"- Creneau actuel : {when}")
    location = _text(target.get('location'))
    if location:
        lines.append(f"- Lieu actuel : {location}")
    return lines


def _time_range(value: Mapping[str, Any]) -> str:
    if bool(value.get('all_day')):
        return 'toute la journee'
    start = _parse_iso(value.get('start'), timezone_name=_text(value.get('timezone')))
    end = _parse_iso(value.get('end'), timezone_name=_text(value.get('timezone')))
    if start is None:
        return ''
    if end is None:
        return start.strftime('%H:%M')
    return f"{start.strftime('%H:%M')}-{end.strftime('%H:%M')}"


def _parse_iso(value: Any, *, timezone_name: str = ''):
    try:
        parsed = datetime.fromisoformat(str(value or '').replace('Z', '+00:00'))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(_display_timezone(timezone_name))


def _display_timezone(timezone_name: str):
    raw = str(timezone_name or '').strip()
    if not raw:
        return timezone.utc
    try:
        return ZoneInfo(raw)
    except (ZoneInfoNotFoundError, ValueError):
        return timezone.utc


def _text(value: Any) -> str:
    return str(value or '').strip()


def _render_cancelled(result: proposal_execution.AgendaProposalExecutionResult) -> str:
    reference = str(result.pending_action_id or '')
    suffix = f" ({reference})" if reference else ''
    return f"J'ai annule la proposition en attente{suffix}. Rien n'a ete modifie dans ton agenda."


def _message_meta(
    *,
    plan: agent_contract.AgendaAgentPlan,
    proposal_result: proposal_execution.AgendaProposalExecutionResult,
) -> dict[str, Any]:
    observation = dict(proposal_result.observation)
    return {
        'source': SOURCE_AGENDA_PENDING_RESPONSE,
        'reason_code': REASON_AGENDA_PENDING_FINAL,
        'agenda_schema_version': agent_contract.SCHEMA_VERSION,
        'agenda_product_method': str(plan.product_method or ''),
        'agenda_pending_action_id': str(observation.get('pending_action_id') or ''),
        'agenda_pending_action_hash': str(observation.get('pending_action_hash') or ''),
        'agenda_operation': str(observation.get('operation') or ''),
        'agenda_pending_status': str(observation.get('pending_status') or ''),
        'agenda_pending_expires_at': str(observation.get('pending_expires_at') or ''),
        'agenda_confirmation_level': str(observation.get('confirmation_level') or ''),
        'agenda_risk_flags': list(observation.get('risk_flags') or []),
        'agenda_caldav_access': bool(observation.get('caldav_access')),
        'agenda_nextcloud_access': bool(observation.get('nextcloud_access')),
        'agenda_secret_access': bool(observation.get('secret_access')),
        'agenda_mutation_attempted': bool(observation.get('mutation_attempted')),
        'agenda_final_lock_authorized': True,
        'agenda_final_lock_reason_code': REASON_AGENDA_PENDING_FINAL,
        'content_free_meta': True,
    }


def _lock_observability(meta: Mapping[str, Any]) -> dict[str, Any]:
    return {
        'agenda_product_method': str(meta.get('agenda_product_method') or ''),
        'agenda_pending_action_present': bool(meta.get('agenda_pending_action_id')),
        'agenda_pending_action_hash': str(meta.get('agenda_pending_action_hash') or ''),
        'agenda_operation': str(meta.get('agenda_operation') or ''),
        'agenda_pending_status': str(meta.get('agenda_pending_status') or ''),
        'agenda_confirmation_level': str(meta.get('agenda_confirmation_level') or ''),
        'agenda_risk_flags': list(meta.get('agenda_risk_flags') or []),
        'agenda_caldav_access': bool(meta.get('agenda_caldav_access')),
        'agenda_nextcloud_access': bool(meta.get('agenda_nextcloud_access')),
        'agenda_secret_access': bool(meta.get('agenda_secret_access')),
        'agenda_mutation_attempted': bool(meta.get('agenda_mutation_attempted')),
        'content_free': True,
    }


def _compose_surface(intro: str, content: str, outro: str) -> str:
    return "\n\n".join(
        part
        for part in (str(intro or '').strip(), str(content or '').strip(), str(outro or '').strip())
        if part
    )
