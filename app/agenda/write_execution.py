from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agenda import agent_contract
from agenda import family_calendar_policy
from agenda import ics_writer
from agenda import pending_drafts
from agenda import pending_store
from agenda import product_methods
from agenda.caldav_write_client import CalDavWriteError, CalDavWriteValidationError, CalDavWriteResult


STATUS_OK = 'ok'
STATUS_BLOCKED = 'blocked'
STATUS_ERROR = 'error'

REASON_WRITE_EXECUTED = 'agenda_write_executed'
REASON_WRITE_CLIENT_UNAVAILABLE = 'agenda_write_client_unavailable'
REASON_WRITE_PRIVATE_DRAFT_MISSING = 'agenda_write_private_draft_missing'
REASON_WRITE_OPERATION_MISMATCH = 'agenda_write_operation_mismatch'
REASON_WRITE_REINFORCED_REQUIRED = 'agenda_write_reinforced_confirmation_required'
REASON_WRITE_FAMILY_REINFORCED_REQUIRED = family_calendar_policy.REASON_FAMILY_REINFORCED_REQUIRED
REASON_WRITE_UNVERIFIED_REINFORCED_REQUIRED = family_calendar_policy.REASON_UNVERIFIED_REINFORCED_REQUIRED
REASON_WRITE_TARGET_MISSING = 'agenda_write_target_missing'
REASON_WRITE_CALENDAR_TARGET_MISSING = 'agenda_write_calendar_target_missing'
REASON_WRITE_ETAG_MISSING = 'agenda_write_etag_missing'
REASON_WRITE_UPDATE_PRESERVATION_REQUIRED = 'agenda_write_update_preservation_required'
REASON_WRITE_CONFLICT = 'agenda_write_conflict'
REASON_WRITE_FAILED = 'agenda_write_failed'
REASON_PENDING_NOT_FOUND = 'agenda_pending_action_not_found'
REASON_PENDING_EXPIRED = 'agenda_pending_action_expired'


@dataclass(frozen=True)
class AgendaWriteExecutionResult:
    status: str
    reason_code: str
    operation: str = ''
    state: pending_store.AgendaPendingState | None = field(default=None, repr=False, compare=False)
    action: pending_store.AgendaPendingAction | None = field(default=None, repr=False, compare=False)
    draft: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    method_names: tuple[str, ...] = ()
    http_status_codes: tuple[int, ...] = ()
    pending_action_id: str = ''
    pending_action_hash: str = ''
    pending_status: str = ''
    calendar_id: str = ''
    event_reference: str = ''
    etag_present: bool = False
    mutation_attempted: bool = False
    caldav_access: bool = False
    nextcloud_access: bool = False
    secret_access: bool = False
    error_class: str = ''

    @property
    def observation(self) -> dict[str, Any]:
        return {
            'schema_version': 'frida_agenda_write_execution_v1',
            'status': self.status,
            'reason_code': self.reason_code,
            'operation': self.operation,
            'method_names': list(self.method_names),
            'http_status_codes': list(self.http_status_codes),
            'pending_action_id': self.pending_action_id,
            'pending_action_hash': self.pending_action_hash,
            'pending_status': self.pending_status,
            'calendar_hash': agent_contract.sha256_12(self.calendar_id),
            'event_hash': agent_contract.sha256_12(self.event_reference),
            'etag_present': bool(self.etag_present),
            'mutation_attempted': bool(self.mutation_attempted),
            'caldav_access': bool(self.caldav_access),
            'nextcloud_access': bool(self.nextcloud_access),
            'secret_access': bool(self.secret_access),
            'error_class': self.error_class,
            'content_free': True,
            'redacted': True,
        }


def execute_confirmed_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    conversation_state: pending_store.AgendaPendingState | Mapping[str, Any] | None,
    now_iso: str,
    write_client: Any = None,
    uid_factory: Callable[[], str] | None = None,
    live_caldav: bool = False,
) -> AgendaWriteExecutionResult:
    state = _state_from_input(conversation_state)
    method = product_methods.get_method(plan.product_method)
    if method is None or method.family != product_methods.FAMILY_MUTATE:
        return _blocked(state=state, reason_code=REASON_WRITE_OPERATION_MISMATCH)
    current_state, action = pending_store.find_pending_action(
        state,
        str(plan.mutation.get('pending_action_id') or ''),
        now_iso=now_iso,
    )
    operation = method.mutation_kind
    if action is None:
        return _blocked(state=current_state, reason_code=REASON_PENDING_NOT_FOUND, operation=operation)
    if action.status == pending_store.STATUS_EXPIRED:
        return _blocked(state=current_state, reason_code=REASON_PENDING_EXPIRED, operation=operation, action=action)
    if action.status != pending_store.STATUS_PENDING:
        return _blocked(state=current_state, reason_code=REASON_PENDING_NOT_FOUND, operation=operation, action=action)
    if action.operation != operation:
        return _blocked(state=current_state, reason_code=REASON_WRITE_OPERATION_MISMATCH, operation=operation, action=action)
    draft = pending_store.private_draft_for_action(action)
    if not _valid_private_draft(draft, operation=operation):
        return _blocked(
            state=current_state,
            reason_code=REASON_WRITE_PRIVATE_DRAFT_MISSING,
            operation=operation,
            action=action,
        )
    classification = _sensitive_calendar_classification(action=action, draft=draft)
    if _reinforced_missing(plan, action=action, operation=operation, classification=classification):
        return _blocked(
            state=current_state,
            reason_code=_reinforced_reason(classification),
            operation=operation,
            action=action,
            draft=draft,
        )
    if operation == pending_store.OPERATION_DELETE and action.confirmation_level != pending_store.CONFIRMATION_REINFORCED:
        return _blocked(state=current_state, reason_code=REASON_WRITE_REINFORCED_REQUIRED, operation=operation, action=action, draft=draft)
    if operation == pending_store.OPERATION_DELETE and str(plan.mutation.get('confirmation_level') or '') != pending_store.CONFIRMATION_REINFORCED:
        return _blocked(state=current_state, reason_code=REASON_WRITE_REINFORCED_REQUIRED, operation=operation, action=action, draft=draft)
    if write_client is None:
        return _blocked(
            state=current_state,
            reason_code=REASON_WRITE_CLIENT_UNAVAILABLE,
            operation=operation,
            action=action,
            draft=draft,
        )
    try:
        write_result = _execute_write(
            operation=operation,
            draft=draft,
            write_client=write_client,
            now_iso=now_iso,
            uid_factory=uid_factory,
        )
    except CalDavWriteValidationError as exc:
        return _blocked(
            state=current_state,
            reason_code=exc.reason_code,
            operation=operation,
            action=action,
            draft=draft,
            error_class=exc.__class__.__name__,
        )
    except CalDavWriteError as exc:
        reason = REASON_WRITE_CONFLICT if exc.reason_code == REASON_WRITE_CONFLICT else exc.reason_code or REASON_WRITE_FAILED
        return _blocked(
            state=current_state,
            reason_code=reason,
            operation=operation,
            action=action,
            draft=draft,
            method_names=(exc.method,),
            http_status_codes=(exc.status_code,),
            mutation_attempted=True,
            caldav_access=True,
            nextcloud_access=bool(live_caldav),
            secret_access=bool(live_caldav),
            error_class=exc.__class__.__name__,
        )
    except Exception as exc:
        return _blocked(
            state=current_state,
            reason_code=REASON_WRITE_FAILED,
            operation=operation,
            action=action,
            draft=draft,
            error_class=exc.__class__.__name__,
        )
    next_state, executed = pending_store.mark_pending_action_executed(
        current_state,
        action.pending_action_id,
        now_iso=now_iso,
    )
    return AgendaWriteExecutionResult(
        status=STATUS_OK,
        reason_code=REASON_WRITE_EXECUTED,
        operation=operation,
        state=next_state,
        action=executed or action,
        draft=draft,
        method_names=(write_result.method,),
        http_status_codes=(write_result.status_code,),
        pending_action_id=action.pending_action_id,
        pending_action_hash=action.action_hash,
        pending_status=pending_store.STATUS_EXECUTED,
        calendar_id=write_result.calendar_id,
        event_reference=write_result.event_reference,
        etag_present=write_result.etag_present,
        mutation_attempted=True,
        caldav_access=True,
        nextcloud_access=bool(live_caldav),
        secret_access=bool(live_caldav),
    )


def _execute_write(
    *,
    operation: str,
    draft: Mapping[str, Any],
    write_client: Any,
    now_iso: str,
    uid_factory: Callable[[], str] | None,
) -> CalDavWriteResult:
    if operation == pending_store.OPERATION_CREATE:
        uid = _new_uid(uid_factory)
        ics_text = ics_writer.build_event_ics(draft, uid=uid, now_iso=now_iso)
        return write_client.put_new_event(
            calendar_id=str(draft.get('calendar_id') or ''),
            uid=uid,
            ics_text=ics_text,
        )
    target = _target(draft)
    technical_ref = _technical_ref(target)
    uid = str(technical_ref.get('uid') or '')
    caldav_path = str(technical_ref.get('caldav_path') or '')
    etag = str(technical_ref.get('etag') or '')
    if operation == pending_store.OPERATION_UPDATE:
        if not uid or not caldav_path:
            raise CalDavWriteValidationError(REASON_WRITE_TARGET_MISSING)
        if not etag:
            raise CalDavWriteValidationError(REASON_WRITE_ETAG_MISSING)
        raise CalDavWriteValidationError(REASON_WRITE_UPDATE_PRESERVATION_REQUIRED)
    if operation == pending_store.OPERATION_DELETE:
        if not caldav_path:
            raise CalDavWriteValidationError(REASON_WRITE_TARGET_MISSING)
        if not etag:
            raise CalDavWriteValidationError(REASON_WRITE_ETAG_MISSING)
        return write_client.delete_event(
            caldav_path=caldav_path,
            etag=etag,
            calendar_id=str(target.get('calendar_id') or draft.get('calendar_id') or ''),
            event_reference=str(target.get('event_id') or uid),
        )
    raise CalDavWriteValidationError(REASON_WRITE_OPERATION_MISMATCH)


def _blocked(
    *,
    state: pending_store.AgendaPendingState,
    reason_code: str,
    operation: str = '',
    action: pending_store.AgendaPendingAction | None = None,
    draft: Mapping[str, Any] | None = None,
    method_names: tuple[str, ...] = (),
    http_status_codes: tuple[int, ...] = (),
    mutation_attempted: bool = False,
    caldav_access: bool = False,
    nextcloud_access: bool = False,
    secret_access: bool = False,
    error_class: str = '',
) -> AgendaWriteExecutionResult:
    return AgendaWriteExecutionResult(
        status=STATUS_BLOCKED,
        reason_code=reason_code,
        operation=operation or (action.operation if action is not None else ''),
        state=state,
        action=action,
        draft=dict(draft or {}),
        method_names=tuple(method_names),
        http_status_codes=tuple(http_status_codes),
        pending_action_id=action.pending_action_id if action is not None else '',
        pending_action_hash=action.action_hash if action is not None else '',
        pending_status=action.status if action is not None else '',
        mutation_attempted=bool(mutation_attempted),
        caldav_access=bool(caldav_access),
        nextcloud_access=bool(nextcloud_access),
        secret_access=bool(secret_access),
        error_class=error_class,
    )


def _state_from_input(value: pending_store.AgendaPendingState | Mapping[str, Any] | None) -> pending_store.AgendaPendingState:
    if isinstance(value, pending_store.AgendaPendingState):
        return value
    return pending_store.AgendaPendingState.from_mapping(value or {})


def _valid_private_draft(draft: Mapping[str, Any], *, operation: str) -> bool:
    if not draft or draft.get('schema_version') != pending_drafts.PRIVATE_DRAFT_SCHEMA_VERSION:
        return False
    return str(draft.get('operation') or '') == operation


def _reinforced_missing(
    plan: agent_contract.AgendaAgentPlan,
    *,
    action: pending_store.AgendaPendingAction,
    operation: str,
    classification: str,
) -> bool:
    if not family_calendar_policy.requires_reinforced(operation, classification=classification):
        return False
    return (
        action.confirmation_level != pending_store.CONFIRMATION_REINFORCED
        or str(plan.mutation.get('confirmation_level') or '') != pending_store.CONFIRMATION_REINFORCED
    )


def _sensitive_calendar_classification(
    *,
    action: pending_store.AgendaPendingAction,
    draft: Mapping[str, Any],
) -> str:
    if family_calendar_policy.FAMILY_RISK_FLAG in action.risk_flags:
        return family_calendar_policy.CLASSIFICATION_FAMILY
    if family_calendar_policy.UNVERIFIED_RISK_FLAG in action.risk_flags:
        return family_calendar_policy.CLASSIFICATION_UNKNOWN
    return family_calendar_policy.draft_calendar_classification(draft)


def _reinforced_reason(classification: str) -> str:
    if family_calendar_policy.normalize_classification(classification) == family_calendar_policy.CLASSIFICATION_UNKNOWN:
        return REASON_WRITE_UNVERIFIED_REINFORCED_REQUIRED
    return REASON_WRITE_FAMILY_REINFORCED_REQUIRED


def _target(draft: Mapping[str, Any]) -> dict[str, Any]:
    return dict(draft.get('target') or {})


def _technical_ref(target: Mapping[str, Any]) -> dict[str, Any]:
    return dict(target.get('technical_ref') or {})


def _new_uid(uid_factory: Callable[[], str] | None) -> str:
    if uid_factory is not None:
        candidate = str(uid_factory() or '').strip()
        if candidate:
            return candidate
    return f'frida-agenda-{uuid.uuid4().hex[:16]}@fridadev.local'
