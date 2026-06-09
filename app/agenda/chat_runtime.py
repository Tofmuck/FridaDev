from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agenda import (
    agent_contract,
    agent_openrouter,
    agent_runtime,
    caldav_transport,
    pending_store,
    proposal_execution,
    proposal_rendering,
    read_execution,
    response_rendering,
    runtime_config,
    time_windows,
)


AGENDA_PAYLOAD_KEY = 'agenda_enabled'
REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED = 'agenda_runtime_not_implemented'
REASON_TOGGLE_OFF = 'agenda_toggle_off'


def normalize_agenda_enabled(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    normalized = str(value or '').strip().lower()
    return normalized in {'1', 'true', 'yes', 'on', 'enabled', 'active'}


@dataclass(frozen=True)
class AgendaChatResult:
    enabled: bool
    used: bool
    status: str
    reason_code: str
    observability_payload: dict[str, Any]
    final_response_lock: Any = field(default=None, repr=False, compare=False)
    read_execution_result: Any = field(default=None, repr=False, compare=False)
    proposal_execution_result: Any = field(default=None, repr=False, compare=False)
    pending_state: Any = field(default=None, repr=False, compare=False)


def build_lot1_observability_payload(
    *,
    enabled: bool,
    status: str,
    reason_code: str,
) -> dict[str, Any]:
    return {
        'schema_version': 'frida_agenda_lot1_noop_v1',
        'enabled': bool(enabled),
        'used': False,
        'status': str(status or 'not_implemented'),
        'reason_code': str(reason_code or REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED),
        'runtime_available': False,
        'caldav_access': False,
        'nextcloud_access': False,
        'secret_access': False,
        'mutation_attempted': False,
        'content_free': True,
    }


def build_lot4_observability_payload(
    *,
    enabled: bool,
    status: str,
    reason_code: str,
    mode: str,
    agent_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    observation = dict(agent_observation or {})
    plan_observation = {}
    validation = observation.get('validation')
    if isinstance(validation, Mapping):
        plan = validation.get('plan')
        if isinstance(plan, Mapping):
            plan_observation = dict(plan)
    return {
        'schema_version': 'frida_agenda_lot4_agent_v1',
        'agent_schema_version': agent_contract.SCHEMA_VERSION,
        'enabled': bool(enabled),
        'used': False,
        'status': str(status or ''),
        'reason_code': str(reason_code or ''),
        'mode': str(mode or agent_contract.MODE_OFF),
        'runtime_available': True,
        'agent_json_validated': bool(plan_observation),
        'validated_plan_present': bool(observation.get('validated_plan_present')),
        'product_method': str(plan_observation.get('product_method') or ''),
        'tool_names': list(plan_observation.get('tool_names') or []),
        'tool_count': int(plan_observation.get('tool_count') or 0),
        'mutation_requested': bool(plan_observation.get('mutation_requested')),
        'mutation_kind': str(plan_observation.get('mutation_kind') or ''),
        'confirmation_required': bool(plan_observation.get('confirmation_required')),
        'confirmation_level': str(plan_observation.get('confirmation_level') or ''),
        'model_called': bool(observation.get('model_called')),
        'fallback_deterministic': bool(observation.get('fallback_deterministic', True)),
        'caldav_access': False,
        'nextcloud_access': False,
        'secret_access': False,
        'mutation_attempted': False,
        'prompt_lane_injected': False,
        'final_response_override': False,
        'content_free': True,
        'agent': observation,
    }


def build_lot5_observability_payload(
    *,
    enabled: bool,
    status: str,
    reason_code: str,
    mode: str,
    agent_observation: Mapping[str, Any] | None = None,
    execution_observation: Mapping[str, Any] | None = None,
    final_lock_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_lot4_observability_payload(
        enabled=enabled,
        status=status,
        reason_code=reason_code,
        mode=mode,
        agent_observation=agent_observation,
    )
    execution = dict(execution_observation or {})
    final_lock = dict(final_lock_observation or {})
    payload.update(
        {
            'schema_version': 'frida_agenda_lot5_readonly_v1',
            'used': bool(final_lock.get('content_present')),
            'read_execution_attempted': bool(execution),
            'read_execution_status': str(execution.get('status') or ''),
            'read_execution_reason_code': str(execution.get('reason_code') or ''),
            'read_tool_names': list(execution.get('tool_names') or []),
            'read_tool_count': int(execution.get('tool_count') or 0),
            'read_calendar_count': int(execution.get('calendar_count') or 0),
            'read_event_count': int(execution.get('event_count') or 0),
            'read_calendar_id_hashes': list(execution.get('calendar_id_hashes') or []),
            'read_event_id_hashes': list(execution.get('event_id_hashes') or []),
            'error_class': str(execution.get('error_class') or ''),
            'caldav_access': bool(execution.get('caldav_access')),
            'nextcloud_access': bool(execution.get('nextcloud_access')),
            'secret_access': bool(execution.get('caldav_access')),
            'mutation_attempted': False,
            'final_response_override': bool(final_lock.get('content_present')),
            'final_response': final_lock,
            'read_execution': execution,
        }
    )
    payload['content_free'] = True
    return payload


def build_lot6_observability_payload(
    *,
    enabled: bool,
    status: str,
    reason_code: str,
    mode: str,
    agent_observation: Mapping[str, Any] | None = None,
    proposal_observation: Mapping[str, Any] | None = None,
    final_lock_observation: Mapping[str, Any] | None = None,
    pending_state_observation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_lot4_observability_payload(
        enabled=enabled,
        status=status,
        reason_code=reason_code,
        mode=mode,
        agent_observation=agent_observation,
    )
    proposal = dict(proposal_observation or {})
    final_lock = dict(final_lock_observation or {})
    pending_state_payload = dict(pending_state_observation or {})
    write = dict(proposal.get('write_execution') or {})
    payload.update(
        {
            'schema_version': (
                'frida_agenda_lot7a_confirmed_write_v1'
                if write
                else 'frida_agenda_lot6_pending_v1'
            ),
            'used': bool(final_lock.get('content_present')),
            'pending_execution_attempted': bool(proposal),
            'pending_execution_status': str(proposal.get('status') or ''),
            'pending_execution_reason_code': str(proposal.get('reason_code') or ''),
            'pending_action_id': str(proposal.get('pending_action_id') or ''),
            'pending_action_hash': str(proposal.get('pending_action_hash') or ''),
            'pending_operation': str(proposal.get('operation') or ''),
            'pending_status': str(proposal.get('pending_status') or ''),
            'pending_expires_at': str(proposal.get('pending_expires_at') or ''),
            'pending_confirmation_level': str(proposal.get('confirmation_level') or ''),
            'pending_risk_flags': list(proposal.get('risk_flags') or []),
            'pending_target_clear': bool(proposal.get('target_clear')),
            'pending_cancelled': bool(proposal.get('cancelled')),
            'pending_expired': bool(proposal.get('expired')),
            'pending_state': pending_state_payload,
            'read_execution_attempted': False,
            'read_execution_status': '',
            'read_execution_reason_code': '',
            'read_tool_names': [],
            'read_tool_count': 0,
            'read_calendar_count': 0,
            'read_event_count': 0,
            'read_calendar_id_hashes': [],
            'read_event_id_hashes': [],
            'error_class': '',
            'write_execution_attempted': bool(write),
            'write_execution_status': str(write.get('status') or ''),
            'write_execution_reason_code': str(write.get('reason_code') or ''),
            'write_method_names': list(write.get('method_names') or []),
            'write_http_status_codes': list(write.get('http_status_codes') or []),
            'write_error_class': str(write.get('error_class') or ''),
            'caldav_access': bool(proposal.get('caldav_access')),
            'nextcloud_access': bool(proposal.get('nextcloud_access')),
            'secret_access': bool(proposal.get('secret_access')),
            'mutation_attempted': bool(proposal.get('mutation_attempted')),
            'final_response_override': bool(final_lock.get('content_present')),
            'final_response': final_lock,
            'pending_execution': proposal,
        }
    )
    payload['content_free'] = True
    return payload


def run_agenda_chat_turn(
    data: Mapping[str, Any],
    *,
    user_msg: str,
    conversation_id: Any = None,
    now_iso: str = '',
    recent_dialogue: tuple[dict[str, Any], ...] = (),
    config_module: Any = None,
    runtime_settings_module: Any = None,
    settings_override: agent_contract.AgendaAgentSettings | None = None,
    agent_model_client: Any = None,
    read_client: Any = None,
    write_client: Any = None,
    conversation_state: Any = None,
    pending_id_factory: Any = None,
    write_uid_factory: Any = None,
    llm_module: Any = None,
    requests_module: Any = None,
) -> AgendaChatResult:
    del conversation_id
    enabled = normalize_agenda_enabled(data.get(AGENDA_PAYLOAD_KEY) if isinstance(data, Mapping) else None)
    if not enabled:
        payload = build_lot4_observability_payload(
            enabled=False,
            status='disabled',
            reason_code=REASON_TOGGLE_OFF,
            mode=agent_contract.MODE_OFF,
        )
        return AgendaChatResult(
            enabled=False,
            used=False,
            status='disabled',
            reason_code=REASON_TOGGLE_OFF,
            observability_payload=payload,
        )

    settings = settings_override or agent_contract.AgendaAgentSettings.from_runtime_settings(
        runtime_settings_module=runtime_settings_module,
    )
    timezone = str(getattr(config_module, 'FRIDA_TIMEZONE', '') or 'UTC')
    canonical_time_windows = time_windows.build_canonical_time_windows(
        now_iso=str(now_iso or ''),
        timezone_name=timezone,
    )
    pending_state = _pending_state_from_input(conversation_state)
    request = agent_contract.AgendaAgentRequest(
        user_message=str(user_msg or ''),
        recent_dialogue=tuple(recent_dialogue or ()),
        user_display_name=agent_contract.USER_DISPLAY_NAME_V1,
        now_iso=str(now_iso or ''),
        timezone=timezone,
        canonical_time_windows=canonical_time_windows,
        agenda_state=pending_state.to_agent_state(now_iso=str(now_iso or '')),
        settings=settings,
    )
    model_client = agent_model_client or _default_agent_model_client(
        settings=settings,
        runtime_settings_module=runtime_settings_module,
        llm_module=llm_module,
        requests_module=requests_module,
        config_module=config_module,
    )
    result = agent_runtime.AgendaJsonAgent(model_client).run(request)
    execution_result = None
    proposal_result = None
    final_lock = None
    if result.validated_plan is not None and result.status == agent_runtime.STATUS_ACTIVE_READY:
        if proposal_execution.plan_needs_pending_store(result.validated_plan):
            proposal_client, proposal_live_caldav = _resolve_proposal_read_client(
                settings=settings,
                plan=result.validated_plan,
                injected_client=read_client,
                runtime_settings_module=runtime_settings_module,
                requests_module=requests_module,
                config_module=config_module,
            )
            proposal_result = proposal_execution.execute_pending_plan(
                result.validated_plan,
                conversation_state=pending_state,
                now_iso=str(now_iso or ''),
                id_factory=pending_id_factory,
                read_client=proposal_client,
                live_caldav=proposal_live_caldav,
                write_client=write_client,
                live_write_caldav=False,
                uid_factory=write_uid_factory,
            )
            pending_state = proposal_result.state or pending_state
            final_lock = proposal_rendering.build_proposal_response_lock(
                plan=result.validated_plan,
                proposal_result=proposal_result,
            )
        elif read_execution.plan_needs_read_client(result.validated_plan):
            resolved_client, live_caldav = _resolve_read_client(
                settings=settings,
                injected_client=read_client,
                runtime_settings_module=runtime_settings_module,
                requests_module=requests_module,
                config_module=config_module,
            )
            execution_result = read_execution.execute_readonly_plan(
                result.validated_plan,
                client=resolved_client,
                live_caldav=live_caldav,
                now_iso=str(now_iso or ''),
            )
            final_lock = response_rendering.build_final_response_lock(
                plan=result.validated_plan,
                execution_result=execution_result,
            )
        else:
            execution_result = read_execution.execute_readonly_plan(
                result.validated_plan,
                client=None,
                live_caldav=False,
            )
    execution_observation = (
        execution_result.observation if execution_result is not None else None
    )
    proposal_observation = (
        proposal_result.observation if proposal_result is not None else None
    )
    final_lock_observation = final_lock.to_observability() if final_lock is not None else None
    if proposal_result is not None:
        payload = build_lot6_observability_payload(
            enabled=True,
            status=result.status,
            reason_code=result.reason_code,
            mode=result.mode,
            agent_observation=result.to_observability(),
            proposal_observation=proposal_observation,
            final_lock_observation=final_lock_observation,
            pending_state_observation=pending_state.to_observability(now_iso=str(now_iso or '')),
        )
    else:
        payload = build_lot5_observability_payload(
            enabled=True,
            status=result.status,
            reason_code=result.reason_code,
            mode=result.mode,
            agent_observation=result.to_observability(),
            execution_observation=execution_observation,
            final_lock_observation=final_lock_observation,
        )
    return AgendaChatResult(
        enabled=True,
        used=bool(final_lock is not None and final_lock.ok and final_lock.content),
        status=result.status,
        reason_code=result.reason_code,
        observability_payload=payload,
        final_response_lock=final_lock,
        read_execution_result=execution_result,
        proposal_execution_result=proposal_result,
        pending_state=pending_state,
    )


def final_response_lock_for_result(result: Any) -> Any:
    return getattr(result, 'final_response_lock', None)


def read_agenda_conversation_state(conversation: Mapping[str, Any]) -> pending_store.AgendaPendingState:
    return pending_store.read_state_from_conversation(conversation)


def attach_agenda_conversation_state(conversation: dict[str, Any], result: Any) -> bool:
    proposal_result = getattr(result, 'proposal_execution_result', None)
    if proposal_result is None:
        return False
    state = getattr(result, 'pending_state', None)
    if state is None:
        return False
    return pending_store.attach_state_to_latest_user_message(conversation, state)


def _pending_state_from_input(value: Any) -> pending_store.AgendaPendingState:
    if isinstance(value, pending_store.AgendaPendingState):
        return value
    return pending_store.AgendaPendingState.from_mapping(value or {})


def _default_agent_model_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    runtime_settings_module: Any = None,
    llm_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> Any:
    if settings.normalized_mode() != agent_contract.MODE_ACTIVE:
        return None
    if not settings.caldav_secret_configured:
        return None
    post = getattr(requests_module, 'post', None)
    if not callable(post) or llm_module is None or runtime_settings_module is None:
        return None
    return agent_openrouter.OpenRouterAgendaAgentClient(
        llm_module=llm_module,
        runtime_settings_module=runtime_settings_module,
        requests_post=post,
        config_module=config_module,
    )


def _resolve_read_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    injected_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> tuple[Any, bool]:
    if injected_client is not None:
        return injected_client, False
    if settings.normalized_mode() != agent_contract.MODE_ACTIVE:
        return None, False
    if not settings.caldav_secret_configured:
        return None, False
    if runtime_settings_module is None or requests_module is None:
        return None, False
    secret_reader = getattr(runtime_settings_module, 'get_runtime_secret_value', None)
    if not callable(secret_reader):
        return None, False
    try:
        secret = secret_reader(
            runtime_config.AGENDA_AGENT_SECTION,
            runtime_config.CALDAV_APP_PASSWORD_FIELD,
        )
    except Exception:
        return None, False
    app_password = str(getattr(secret, 'value', '') or '')
    if not app_password:
        return None, False
    return (
        caldav_transport.build_live_caldav_read_client(
            account=settings.caldav_account,
            app_password=app_password,
            requests_module=requests_module,
            config_module=config_module,
        ),
        True,
    )


def _resolve_proposal_read_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    plan: agent_contract.AgendaAgentPlan,
    injected_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> tuple[Any, bool]:
    if not proposal_execution.plan_can_attempt_target_verification(
        plan,
        injected_client=injected_client is not None,
    ) and not (
        injected_client is not None
        and proposal_execution.plan_can_attempt_calendar_classification(plan)
    ):
        return None, False
    return _resolve_read_client(
        settings=settings,
        injected_client=injected_client,
        runtime_settings_module=runtime_settings_module,
        requests_module=requests_module,
        config_module=config_module,
    )
