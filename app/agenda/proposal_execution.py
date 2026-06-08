from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agenda import agent_contract
from agenda import pending_store
from agenda import product_methods


STATUS_OK = 'ok'
STATUS_BLOCKED = 'blocked'
STATUS_SKIPPED = 'skipped'

REASON_PENDING_CREATED = 'agenda_pending_action_created'
REASON_NOT_PENDING_METHOD = 'agenda_pending_method_not_supported'
REASON_TARGET_AMBIGUOUS = 'agenda_pending_target_ambiguous'
REASON_PENDING_CANCELLED = 'agenda_pending_action_cancelled'
REASON_PENDING_NOT_FOUND = 'agenda_pending_action_not_found'
REASON_PENDING_EXPIRED = 'agenda_pending_action_expired'
REASON_CONFIRMATION_NOT_EXECUTABLE = 'agenda_pending_confirmation_not_executable_lot7'


@dataclass(frozen=True)
class AgendaProposalExecutionResult:
    status: str
    reason_code: str
    product_method: str = ''
    operation: str = ''
    confirmation_level: str = ''
    risk_flags: tuple[str, ...] = ()
    pending_action_id: str = ''
    pending_action_hash: str = ''
    pending_expires_at: str = ''
    pending_status: str = ''
    state: pending_store.AgendaPendingState | None = field(default=None, repr=False, compare=False)
    mutation_attempted: bool = False
    caldav_access: bool = False
    nextcloud_access: bool = False
    secret_access: bool = False
    target_clear: bool = False
    cancelled: bool = False
    expired: bool = False

    @property
    def observation(self) -> dict[str, Any]:
        return {
            'schema_version': 'frida_agenda_proposal_execution_v1',
            'status': self.status,
            'reason_code': self.reason_code,
            'product_method': self.product_method,
            'operation': self.operation,
            'confirmation_level': self.confirmation_level,
            'risk_flags': list(self.risk_flags),
            'pending_action_id': self.pending_action_id,
            'pending_action_hash': self.pending_action_hash,
            'pending_expires_at': self.pending_expires_at,
            'pending_status': self.pending_status,
            'target_clear': bool(self.target_clear),
            'cancelled': bool(self.cancelled),
            'expired': bool(self.expired),
            'caldav_access': False,
            'nextcloud_access': False,
            'secret_access': False,
            'mutation_attempted': False,
            'content_free': True,
            'redacted': True,
        }


def plan_needs_pending_store(plan: agent_contract.AgendaAgentPlan) -> bool:
    method = product_methods.get_method(str(getattr(plan, 'product_method', '') or ''))
    return bool(
        method is not None
        and method.family in {
            product_methods.FAMILY_PROPOSE,
            product_methods.FAMILY_MUTATE,
            product_methods.FAMILY_CONTEXT,
        }
    )


def execute_pending_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    conversation_state: pending_store.AgendaPendingState | Mapping[str, Any] | None,
    now_iso: str,
    id_factory: Callable[[], str] | None = None,
) -> AgendaProposalExecutionResult:
    state = _state_from_input(conversation_state)
    method = product_methods.get_method(plan.product_method)
    if method is None:
        return _blocked(plan, state=state, reason_code=REASON_NOT_PENDING_METHOD)
    if method.family == product_methods.FAMILY_PROPOSE:
        return _execute_proposal(plan, method=method, state=state, now_iso=now_iso, id_factory=id_factory)
    if method.family == product_methods.FAMILY_MUTATE:
        return _refuse_confirmation(plan, method=method, state=state, now_iso=now_iso)
    if method.name == product_methods.METHOD_CANCEL_PENDING_AGENDA_ACTION:
        return _cancel_pending(plan, state=state, now_iso=now_iso)
    return _blocked(plan, state=state, reason_code=REASON_NOT_PENDING_METHOD)


def _execute_proposal(
    plan: agent_contract.AgendaAgentPlan,
    *,
    method: product_methods.AgendaProductMethod,
    state: pending_store.AgendaPendingState,
    now_iso: str,
    id_factory: Callable[[], str] | None,
) -> AgendaProposalExecutionResult:
    operation = method.mutation_kind
    if operation not in pending_store.OPERATIONS:
        return _blocked(plan, state=state, reason_code=REASON_NOT_PENDING_METHOD)
    target_clear = _target_clear_for_proposal(plan, operation=operation)
    if operation in {pending_store.OPERATION_UPDATE, pending_store.OPERATION_DELETE} and not target_clear:
        return _blocked(
            plan,
            state=pending_store.expire_pending_actions(state, now_iso=now_iso),
            reason_code=REASON_TARGET_AMBIGUOUS,
            operation=operation,
            target_clear=False,
        )
    risk_flags = _risk_flags(plan)
    confirmation_level = _confirmation_level(plan=plan, operation=operation, risk_flags=risk_flags)
    draft = pending_store.build_content_free_draft(plan, operation=operation)
    next_state, action = pending_store.create_pending_action(
        state,
        operation=operation,
        confirmation_level=confirmation_level,
        risk_flags=risk_flags,
        draft=draft,
        now_iso=now_iso,
        id_factory=id_factory,
    )
    return AgendaProposalExecutionResult(
        status=STATUS_OK,
        reason_code=REASON_PENDING_CREATED,
        product_method=plan.product_method,
        operation=operation,
        confirmation_level=confirmation_level,
        risk_flags=action.risk_flags,
        pending_action_id=action.pending_action_id,
        pending_action_hash=action.action_hash,
        pending_expires_at=action.expires_at,
        pending_status=action.status,
        state=next_state,
        target_clear=target_clear,
    )


def _refuse_confirmation(
    plan: agent_contract.AgendaAgentPlan,
    *,
    method: product_methods.AgendaProductMethod,
    state: pending_store.AgendaPendingState,
    now_iso: str,
) -> AgendaProposalExecutionResult:
    pending_id = str(plan.mutation.get('pending_action_id') or '')
    current_state, action = pending_store.find_pending_action(state, pending_id, now_iso=now_iso)
    operation = method.mutation_kind
    if action is None:
        return _blocked(plan, state=current_state, reason_code=REASON_PENDING_NOT_FOUND, operation=operation)
    if action.status == pending_store.STATUS_EXPIRED:
        return _blocked(
            plan,
            state=current_state,
            reason_code=REASON_PENDING_EXPIRED,
            operation=operation,
            action=action,
            expired=True,
        )
    if action.status == pending_store.STATUS_CANCELLED:
        return _blocked(plan, state=current_state, reason_code=REASON_PENDING_NOT_FOUND, operation=operation, action=action)
    return _blocked(
        plan,
        state=current_state,
        reason_code=REASON_CONFIRMATION_NOT_EXECUTABLE,
        operation=operation,
        action=action,
        target_clear=True,
    )


def _cancel_pending(
    plan: agent_contract.AgendaAgentPlan,
    *,
    state: pending_store.AgendaPendingState,
    now_iso: str,
) -> AgendaProposalExecutionResult:
    pending_id = str(plan.mutation.get('pending_action_id') or '')
    next_state, action = pending_store.cancel_pending_action(state, pending_id, now_iso=now_iso)
    if action is None:
        return _blocked(plan, state=next_state, reason_code=REASON_PENDING_NOT_FOUND)
    return AgendaProposalExecutionResult(
        status=STATUS_OK,
        reason_code=REASON_PENDING_CANCELLED,
        product_method=plan.product_method,
        operation=action.operation,
        confirmation_level=action.confirmation_level,
        risk_flags=action.risk_flags,
        pending_action_id=action.pending_action_id,
        pending_action_hash=action.action_hash,
        pending_expires_at=action.expires_at,
        pending_status=action.status,
        state=next_state,
        cancelled=True,
    )


def _blocked(
    plan: agent_contract.AgendaAgentPlan,
    *,
    state: pending_store.AgendaPendingState,
    reason_code: str,
    operation: str = '',
    action: pending_store.AgendaPendingAction | None = None,
    target_clear: bool = False,
    expired: bool = False,
) -> AgendaProposalExecutionResult:
    return AgendaProposalExecutionResult(
        status=STATUS_BLOCKED,
        reason_code=reason_code,
        product_method=str(plan.product_method or ''),
        operation=operation or (action.operation if action is not None else ''),
        confirmation_level=action.confirmation_level if action is not None else '',
        risk_flags=action.risk_flags if action is not None else _risk_flags(plan),
        pending_action_id=action.pending_action_id if action is not None else '',
        pending_action_hash=action.action_hash if action is not None else '',
        pending_expires_at=action.expires_at if action is not None else '',
        pending_status=action.status if action is not None else '',
        state=state,
        target_clear=target_clear,
        expired=expired,
    )


def _state_from_input(value: pending_store.AgendaPendingState | Mapping[str, Any] | None) -> pending_store.AgendaPendingState:
    if isinstance(value, pending_store.AgendaPendingState):
        return value
    return pending_store.AgendaPendingState.from_mapping(value or {})


def _target_clear_for_proposal(plan: agent_contract.AgendaAgentPlan, *, operation: str) -> bool:
    if operation == pending_store.OPERATION_CREATE:
        return True
    event_get_calls = [
        call
        for call in plan.tool_calls
        if call.tool_name == product_methods.TOOL_EVENT_GET and str(dict(call.params or {}).get('event_id') or '')
    ]
    return len(event_get_calls) == 1


def _confirmation_level(
    *,
    plan: agent_contract.AgendaAgentPlan,
    operation: str,
    risk_flags: tuple[str, ...],
) -> str:
    if operation == pending_store.OPERATION_DELETE or 'family_calendar' in risk_flags:
        return pending_store.CONFIRMATION_REINFORCED
    level = str(plan.mutation.get('confirmation_level') or '')
    if level in {pending_store.CONFIRMATION_SIMPLE, pending_store.CONFIRMATION_REINFORCED}:
        return level
    return pending_store.CONFIRMATION_SIMPLE


def _risk_flags(plan: agent_contract.AgendaAgentPlan) -> tuple[str, ...]:
    flags = list(plan.risk_flags or ())
    if bool(plan.calendar_scope.get('family_calendar')) and 'family_calendar' not in flags:
        flags.append('family_calendar')
    return tuple(str(flag or '') for flag in flags if str(flag or '').strip())[:12]
