from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agenda import (
    agent_contract,
    client_resolution,
    pending_store,
    proposal_execution,
    proposal_rendering,
    read_execution,
    response_rendering,
)


@dataclass(frozen=True)
class AgendaExecutionAdapterResult:
    read_execution_result: Any = field(default=None, repr=False, compare=False)
    proposal_execution_result: Any = field(default=None, repr=False, compare=False)
    final_response_lock: Any = field(default=None, repr=False, compare=False)
    pending_state: pending_store.AgendaPendingState | None = field(
        default=None,
        repr=False,
        compare=False,
    )


def execute_read_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    settings: agent_contract.AgendaAgentSettings,
    injected_read_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
    now_iso: str = '',
) -> AgendaExecutionAdapterResult:
    resolution = client_resolution.resolve_read_client(
        settings=settings,
        injected_client=injected_read_client,
        runtime_settings_module=runtime_settings_module,
        requests_module=requests_module,
        config_module=config_module,
    )
    if resolution.is_error:
        execution_result = read_execution.client_resolution_error_result(
            plan,
            error_class=resolution.error_class,
        )
    else:
        execution_result = read_execution.execute_readonly_plan(
            plan,
            client=resolution.client,
            live_caldav=resolution.live_caldav,
            now_iso=str(now_iso or ''),
        )
    return AgendaExecutionAdapterResult(
        read_execution_result=execution_result,
        final_response_lock=response_rendering.build_final_response_lock(
            plan=plan,
            execution_result=execution_result,
        ),
    )


def execute_proposal_plan(
    plan: agent_contract.AgendaAgentPlan,
    *,
    settings: agent_contract.AgendaAgentSettings,
    pending_state: pending_store.AgendaPendingState,
    now_iso: str,
    injected_read_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
    pending_id_factory: Any = None,
    write_client: Any = None,
    write_uid_factory: Any = None,
) -> AgendaExecutionAdapterResult:
    resolution = client_resolution.resolve_proposal_read_client(
        settings=settings,
        plan=plan,
        injected_client=injected_read_client,
        runtime_settings_module=runtime_settings_module,
        requests_module=requests_module,
        config_module=config_module,
    )
    if resolution.is_error:
        proposal_result = proposal_execution.client_resolution_error_result(
            plan,
            conversation_state=pending_state,
            now_iso=str(now_iso or ''),
            error_class=resolution.error_class,
        )
    else:
        proposal_result = proposal_execution.execute_pending_plan(
            plan,
            conversation_state=pending_state,
            now_iso=str(now_iso or ''),
            id_factory=pending_id_factory,
            read_client=resolution.client,
            live_caldav=resolution.live_caldav,
            write_client=write_client,
            live_write_caldav=False,
            uid_factory=write_uid_factory,
        )
    next_pending_state = proposal_result.state or pending_state
    return AgendaExecutionAdapterResult(
        proposal_execution_result=proposal_result,
        final_response_lock=proposal_rendering.build_proposal_response_lock(
            plan=plan,
            proposal_result=proposal_result,
        ),
        pending_state=next_pending_state,
    )


def execute_context_plan(
    plan: agent_contract.AgendaAgentPlan,
) -> AgendaExecutionAdapterResult:
    final_lock = response_rendering.build_context_response_lock(plan=plan)
    execution_result = None
    if final_lock is None:
        execution_result = read_execution.execute_readonly_plan(
            plan,
            client=None,
            live_caldav=False,
        )
    return AgendaExecutionAdapterResult(
        read_execution_result=execution_result,
        final_response_lock=final_lock,
    )
