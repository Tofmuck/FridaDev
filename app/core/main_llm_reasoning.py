from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


SUPPORTED_REASONING_EFFORTS: tuple[str, ...] = ('none', 'low', 'medium', 'high')
DEFAULT_REASONING_EFFORT = 'high'
REASONING_POLICY_KIND = 'gpt51_openrouter_reasoning_effort_v1'

_SUPPORTED_MODEL_IDS: tuple[str, ...] = (
    'gpt-5.1',
    'gpt-5.1-2025-11-13',
    'openai/gpt-5.1',
    'openai/gpt-5.1-2025-11-13',
)


@dataclass(frozen=True)
class MainLlmReasoningResolution:
    requested_effort: str
    effective_effort: str
    supported: bool
    sent: bool
    policy_kind: str = REASONING_POLICY_KIND
    hidden: bool = True
    reason_code: str = 'reasoning_effort_sent'


def normalize_reasoning_effort(value: Any, *, default: str = DEFAULT_REASONING_EFFORT) -> str:
    effort = str(value or '').strip().lower()
    if effort in SUPPORTED_REASONING_EFFORTS:
        return effort
    return default


def model_supports_reasoning_effort(model: Any) -> bool:
    model_key = str(model or '').strip().lower()
    return model_key in _SUPPORTED_MODEL_IDS


def runtime_payload_reasoning_effort(payload: Mapping[str, Any] | None) -> str:
    data = payload if isinstance(payload, Mapping) else {}
    field_payload = data.get('reasoning_effort')
    if isinstance(field_payload, Mapping):
        return normalize_reasoning_effort(field_payload.get('value'))
    return DEFAULT_REASONING_EFFORT


def resolve_main_llm_reasoning(
    *,
    model: Any,
    runtime_payload: Mapping[str, Any] | None,
) -> MainLlmReasoningResolution:
    requested = runtime_payload_reasoning_effort(runtime_payload)
    supported = model_supports_reasoning_effort(model)
    if not supported:
        return MainLlmReasoningResolution(
            requested_effort=requested,
            effective_effort='not_sent',
            supported=False,
            sent=False,
            reason_code='model_not_reasoning_effort_compatible',
        )
    return MainLlmReasoningResolution(
        requested_effort=requested,
        effective_effort=requested,
        supported=True,
        sent=True,
    )


def reasoning_request_payload(resolution: MainLlmReasoningResolution) -> dict[str, Any] | None:
    if not resolution.sent or resolution.effective_effort not in SUPPORTED_REASONING_EFFORTS:
        return None
    return {
        'effort': resolution.effective_effort,
        'exclude': True,
    }


def reasoning_observability_fields(resolution: MainLlmReasoningResolution) -> dict[str, Any]:
    return {
        'main_llm_reasoning_effort_requested': resolution.requested_effort,
        'main_llm_reasoning_effort_effective': resolution.effective_effort,
        'main_llm_reasoning_policy_kind': resolution.policy_kind,
        'main_llm_reasoning_hidden': resolution.hidden,
        'main_llm_reasoning_reason_code': resolution.reason_code,
    }
