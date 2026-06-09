from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping

from agenda import agent_contract
from agenda import pending_drafts
from agenda import pending_store
from agenda import product_methods
from agenda import proposal_target_verification
from agenda import write_execution
from agenda.caldav_models import CalendarEvent


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
REASON_TARGET_NOT_VERIFIED = proposal_target_verification.REASON_TARGET_NOT_VERIFIED
REASON_PENDING_DRAFT_INVALID = pending_drafts.REASON_PENDING_DRAFT_INVALID


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
    draft: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    verified_event: CalendarEvent | None = field(default=None, repr=False, compare=False)
    target_verification_tool_names: tuple[str, ...] = ()
    target_verification_error_class: str = ''
    write_observation: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @property
    def observation(self) -> dict[str, Any]:
        draft_summary = pending_drafts.content_free_draft_summary(self.draft) if self.draft else {}
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
            'draft_private': bool(self.draft),
            'draft_summary': draft_summary,
            'target_verification_tool_names': list(self.target_verification_tool_names),
            'target_verification_error_class': self.target_verification_error_class,
            'caldav_access': bool(self.caldav_access),
            'nextcloud_access': bool(self.nextcloud_access),
            'secret_access': bool(self.secret_access),
            'mutation_attempted': bool(self.mutation_attempted),
            'write_execution': dict(self.write_observation or {}),
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


def plan_needs_target_verification(plan: agent_contract.AgendaAgentPlan) -> bool:
    method = product_methods.get_method(str(getattr(plan, 'product_method', '') or ''))
    return bool(
        method is not None
        and method.family == product_methods.FAMILY_PROPOSE
        and method.mutation_kind in {pending_store.OPERATION_UPDATE, pending_store.OPERATION_DELETE}
    )


def plan_can_attempt_target_verification(
    plan: agent_contract.AgendaAgentPlan,
    *,
    injected_client: bool = False,
) -> bool:
    if not plan_needs_target_verification(plan):
        return False
    if injected_client:
        return bool(proposal_target_verification.target_event_id_for_plan(plan))
    return proposal_target_verification.has_executable_target_verification_sequence(plan)


def execute_pending_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    conversation_state: pending_store.AgendaPendingState | Mapping[str, Any] | None,
    now_iso: str,
    id_factory: Callable[[], str] | None = None,
    read_client: Any = None,
    live_caldav: bool = False,
    write_client: Any = None,
    live_write_caldav: bool = False,
    uid_factory: Callable[[], str] | None = None,
) -> AgendaProposalExecutionResult:
    state = _state_from_input(conversation_state)
    method = product_methods.get_method(plan.product_method)
    if method is None:
        return _blocked(plan, state=state, reason_code=REASON_NOT_PENDING_METHOD)
    if method.family == product_methods.FAMILY_PROPOSE:
        return _execute_proposal(
            plan,
            method=method,
            state=state,
            now_iso=now_iso,
            id_factory=id_factory,
            read_client=read_client,
            live_caldav=live_caldav,
        )
    if method.family == product_methods.FAMILY_MUTATE:
        return _execute_confirmation(
            plan,
            method=method,
            state=state,
            now_iso=now_iso,
            write_client=write_client,
            live_write_caldav=live_write_caldav,
            uid_factory=uid_factory,
        )
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
    read_client: Any,
    live_caldav: bool,
) -> AgendaProposalExecutionResult:
    operation = method.mutation_kind
    if operation not in pending_store.OPERATIONS:
        return _blocked(plan, state=state, reason_code=REASON_NOT_PENDING_METHOD)
    verification = _verified_target_for_proposal(
        plan,
        operation=operation,
        read_client=read_client,
        live_caldav=live_caldav,
    )
    verified_event = verification.event
    target_clear = operation == pending_store.OPERATION_CREATE or verified_event is not None
    if operation in {pending_store.OPERATION_UPDATE, pending_store.OPERATION_DELETE} and verified_event is None:
        return _blocked(
            plan,
            state=pending_store.expire_pending_actions(state, now_iso=now_iso),
            reason_code=REASON_TARGET_NOT_VERIFIED,
            operation=operation,
            target_clear=False,
            caldav_access=verification.caldav_access,
            nextcloud_access=verification.nextcloud_access,
            secret_access=bool(verification.caldav_access),
            target_verification_tool_names=verification.attempted_tool_names,
            target_verification_error_class=verification.error_class,
        )
    risk_flags = _risk_flags(plan)
    confirmation_level = _confirmation_level(plan=plan, operation=operation, risk_flags=risk_flags)
    draft = pending_drafts.build_private_pending_draft(
        plan,
        operation=operation,
        verified_event=verified_event,
    )
    if isinstance(draft, str):
        return _blocked(
            plan,
            state=pending_store.expire_pending_actions(state, now_iso=now_iso),
            reason_code=draft,
            operation=operation,
            target_clear=target_clear,
        )
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
        draft=draft,
        verified_event=verified_event,
        caldav_access=verification.caldav_access,
        nextcloud_access=verification.nextcloud_access,
        secret_access=bool(verification.caldav_access),
        target_verification_tool_names=verification.attempted_tool_names,
        target_verification_error_class=verification.error_class,
    )


def _execute_confirmation(
    plan: agent_contract.AgendaAgentPlan,
    *,
    method: product_methods.AgendaProductMethod,
    state: pending_store.AgendaPendingState,
    now_iso: str,
    write_client: Any,
    live_write_caldav: bool,
    uid_factory: Callable[[], str] | None,
) -> AgendaProposalExecutionResult:
    del method
    write_result = write_execution.execute_confirmed_plan(
        plan,
        conversation_state=state,
        now_iso=now_iso,
        write_client=write_client,
        live_caldav=live_write_caldav,
        uid_factory=uid_factory,
    )
    return _from_write_result(plan, write_result)


def _from_write_result(
    plan: agent_contract.AgendaAgentPlan,
    write_result: write_execution.AgendaWriteExecutionResult,
) -> AgendaProposalExecutionResult:
    action = write_result.action
    return AgendaProposalExecutionResult(
        status=write_result.status,
        reason_code=write_result.reason_code,
        product_method=str(plan.product_method or ''),
        operation=write_result.operation,
        confirmation_level=action.confirmation_level if action is not None else '',
        risk_flags=action.risk_flags if action is not None else (),
        pending_action_id=write_result.pending_action_id,
        pending_action_hash=write_result.pending_action_hash,
        pending_expires_at=action.expires_at if action is not None else '',
        pending_status=write_result.pending_status,
        state=write_result.state,
        mutation_attempted=write_result.mutation_attempted,
        caldav_access=write_result.caldav_access,
        nextcloud_access=write_result.nextcloud_access,
        secret_access=write_result.secret_access,
        target_clear=(
            write_result.operation in {
                pending_store.OPERATION_CREATE,
                pending_store.OPERATION_UPDATE,
                pending_store.OPERATION_DELETE,
            }
            and write_result.reason_code
            not in {
                write_execution.REASON_WRITE_PRIVATE_DRAFT_MISSING,
                write_execution.REASON_WRITE_TARGET_MISSING,
                write_execution.REASON_WRITE_CALENDAR_TARGET_MISSING,
            }
        ),
        expired=write_result.reason_code == write_execution.REASON_PENDING_EXPIRED,
        draft=write_result.draft,
        write_observation=write_result.observation,
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
    caldav_access: bool = False,
    nextcloud_access: bool = False,
    secret_access: bool = False,
    target_verification_tool_names: tuple[str, ...] = (),
    target_verification_error_class: str = '',
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
        caldav_access=bool(caldav_access),
        nextcloud_access=bool(nextcloud_access),
        secret_access=bool(secret_access),
        target_verification_tool_names=tuple(target_verification_tool_names),
        target_verification_error_class=target_verification_error_class,
    )


def _state_from_input(value: pending_store.AgendaPendingState | Mapping[str, Any] | None) -> pending_store.AgendaPendingState:
    if isinstance(value, pending_store.AgendaPendingState):
        return value
    return pending_store.AgendaPendingState.from_mapping(value or {})


def _verified_target_for_proposal(
    plan: agent_contract.AgendaAgentPlan,
    *,
    operation: str,
    read_client: Any,
    live_caldav: bool,
) -> proposal_target_verification.ProposalTargetVerificationResult:
    if operation == pending_store.OPERATION_CREATE:
        return proposal_target_verification.ProposalTargetVerificationResult()
    return proposal_target_verification.verify_target_event(
        plan,
        client=read_client,
        live_caldav=live_caldav,
    )


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
