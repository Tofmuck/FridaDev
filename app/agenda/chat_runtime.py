from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from agenda import agent_contract, agent_runtime


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
    request = agent_contract.AgendaAgentRequest(
        user_message=str(user_msg or ''),
        recent_dialogue=tuple(recent_dialogue or ()),
        now_iso=str(now_iso or ''),
        timezone=timezone,
        settings=settings,
    )
    result = agent_runtime.AgendaJsonAgent(agent_model_client).run(request)
    payload = build_lot4_observability_payload(
        enabled=True,
        status=result.status,
        reason_code=result.reason_code,
        mode=result.mode,
        agent_observation=result.to_observability(),
    )
    return AgendaChatResult(
        enabled=True,
        used=False,
        status=result.status,
        reason_code=result.reason_code,
        observability_payload=payload,
    )
