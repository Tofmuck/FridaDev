from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

import requests

from admin import runtime_settings
from core import llm_client
from core import prompt_loader
from observability import chat_turn_logger
from . import hard_guards
from . import validation_contract
from . import validation_messages
from . import validation_transport

logger = logging.getLogger('frida.validation_agent')

SCHEMA_VERSION = validation_contract.SCHEMA_VERSION
PRIMARY_MODEL = validation_transport.PRIMARY_MODEL
FALLBACK_MODEL = validation_contract.FALLBACK_MODEL
PROMPT_PATH = "prompts/validation_agent.txt"
REQUEST_TIMEOUT_S = validation_transport.REQUEST_TIMEOUT_S
MAX_RESPONSE_TOKENS = validation_messages.MAX_RESPONSE_TOKENS
MAX_VALIDATION_CONTEXT_MESSAGES = validation_messages.MAX_VALIDATION_CONTEXT_MESSAGES
MAX_VALIDATION_CONTEXT_MESSAGE_CHARS = validation_messages.MAX_VALIDATION_CONTEXT_MESSAGE_CHARS
MAX_VALIDATION_CONTEXT_JSON_CHARS = validation_messages.MAX_VALIDATION_CONTEXT_JSON_CHARS
MAX_JUSTIFICATIONS_JSON_CHARS = validation_messages.MAX_JUSTIFICATIONS_JSON_CHARS
MAX_CANONICAL_INPUTS_JSON_CHARS = validation_messages.MAX_CANONICAL_INPUTS_JSON_CHARS
RUNTIME_SETTINGS_SECTION = "validation_agent_model"

ALLOWED_VALIDATION_DECISIONS = ("confirm", "challenge", "clarify", "suspend")
ALLOWED_PRIMARY_JUDGMENT_POSTURES = validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES
ALLOWED_FINAL_OUTPUT_REGIMES = validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES
ValidationAgentResult = validation_contract.ValidationAgentResult
_ValidationJsonError = validation_contract.ValidationJsonError
_ValidationPayloadError = validation_contract.ValidationPayloadError


_emit_validation_prompt_prepared = validation_messages.emit_validation_prompt_prepared
_validation_time_reference = validation_messages.validation_time_reference
_compacted_validation_dialogue_context = validation_messages.compacted_validation_dialogue_context


_validated_primary_verdict = validation_contract.validate_primary_verdict
_validated_support_mapping = validation_contract.validate_support_mapping
_validated_validation_dialogue_context = validation_contract.validate_validation_dialogue_context
_safe_json_loads = validation_contract.safe_json_loads
_validated_model_verdict = validation_contract.validate_model_verdict
_normalized_arbiter_verdict = validation_contract.normalize_arbiter_verdict
_build_validated_output_payload = validation_contract.build_validated_output_payload
_build_fail_open_result = validation_contract.build_fail_open_result


def _load_system_prompt() -> str:
    return prompt_loader.read_prompt_text(PROMPT_PATH)


def _bounded_response_max_tokens(value: Any) -> int:
    try:
        candidate = int(value)
    except (TypeError, ValueError):
        return MAX_RESPONSE_TOKENS
    if candidate <= 0:
        return MAX_RESPONSE_TOKENS
    return min(candidate, MAX_RESPONSE_TOKENS)


def _runtime_model_settings() -> dict[str, Any]:
    view = runtime_settings.get_validation_agent_model_settings()
    return {
        "primary_model": str(view.payload["primary_model"]["value"]),
        "fallback_model": str(view.payload["fallback_model"]["value"]),
        "timeout_s": int(view.payload["timeout_s"]["value"]),
        "temperature": float(view.payload["temperature"]["value"]),
        "top_p": float(view.payload["top_p"]["value"]),
        "max_tokens": _bounded_response_max_tokens(view.payload["max_tokens"]["value"]),
        "reasoning_effort": str(view.payload["reasoning_effort"]["value"]),
    }


_build_messages = validation_messages.build_messages
_build_messages_with_projection = validation_messages.build_messages_with_projection


def _request_reason_code(exc: Exception, requests_module: Any) -> str:
    exceptions = getattr(requests_module, "exceptions", None)
    timeout_cls = getattr(exceptions, "Timeout", None)
    request_cls = getattr(exceptions, "RequestException", None)
    if timeout_cls is not None and isinstance(exc, timeout_cls):
        return "timeout"
    if request_cls is not None and isinstance(exc, request_cls):
        return "http_error"
    return "upstream_error"


def _call_model(
    *,
    model: str,
    decision_source: str,
    system_prompt: str,
    primary_verdict: Mapping[str, Any],
    justifications: Mapping[str, Any],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    reasoning_effort: str,
    hard_guard_payload: Mapping[str, Any],
    allowed_postures: Sequence[str],
    requests_module: Any,
) -> tuple[dict[str, str], dict[str, Any]]:
    messages, canonical_projection = _build_messages_with_projection(
        system_prompt=system_prompt,
        primary_verdict=primary_verdict,
        justifications=justifications,
        validation_dialogue_context=validation_dialogue_context,
        canonical_inputs=canonical_inputs,
        hard_guard_payload=hard_guard_payload,
    )
    prepared_request = validation_transport.prepare_validation_request(
        model=model,
        decision_source=decision_source,
        messages=messages,
        timeout_s=timeout_s,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        reasoning_effort=reasoning_effort,
        llm_module=llm_client,
    )
    _emit_validation_prompt_prepared(
        model=model,
        decision_source=decision_source,
        messages=messages,
        validation_dialogue_context=validation_dialogue_context,
        canonical_inputs=canonical_inputs,
        canonical_projection=canonical_projection,
        hard_guard_payload=hard_guard_payload,
        request_observability=prepared_request.observability,
    )
    provider_response = validation_transport.request_provider_response(
        prepared_request=prepared_request,
        requests_module=requests_module,
        llm_module=llm_client,
        logger=logger,
    )
    return (
        _validated_model_verdict(
            _safe_json_loads(provider_response.text),
            allowed_postures=allowed_postures,
        ),
        provider_response.provider_metadata,
    )


def _run_model_fallback(
    *,
    primary_verdict: Mapping[str, Any],
    justifications: Mapping[str, Any],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
    hard_guard_decision: hard_guards.HardGuardDecision,
    system_prompt: str,
    runtime_model_settings: Mapping[str, Any],
    requests_module: Any,
) -> ValidationAgentResult:
    last_reason_code = "upstream_error"
    for model, decision_source in (
        (runtime_model_settings["primary_model"], "primary"),
        (runtime_model_settings["fallback_model"], "fallback"),
    ):
        try:
            verdict_payload, provider_metadata = _call_model(
                model=model,
                decision_source=decision_source,
                system_prompt=system_prompt,
                primary_verdict=primary_verdict,
                justifications=justifications,
                validation_dialogue_context=validation_dialogue_context,
                canonical_inputs=canonical_inputs,
                timeout_s=runtime_model_settings["timeout_s"],
                temperature=runtime_model_settings["temperature"],
                top_p=runtime_model_settings["top_p"],
                max_tokens=runtime_model_settings["max_tokens"],
                reasoning_effort=runtime_model_settings["reasoning_effort"],
                hard_guard_payload=hard_guard_decision.prompt_payload(),
                allowed_postures=hard_guard_decision.allowed_postures,
                requests_module=requests_module,
            )
            normalized_verdict = _normalized_arbiter_verdict(
                final_judgment_posture=verdict_payload["final_judgment_posture"],
                final_output_regime=verdict_payload["final_output_regime"],
                arbiter_reason=verdict_payload["arbiter_reason"],
            )
            return ValidationAgentResult(
                validated_output=_build_validated_output_payload(
                    primary_verdict=primary_verdict,
                    final_judgment_posture=normalized_verdict["final_judgment_posture"],
                    final_output_regime=normalized_verdict["final_output_regime"],
                    arbiter_reason=normalized_verdict["arbiter_reason"],
                    fail_open=False,
                    applied_hard_guards=hard_guard_decision.applied_hard_guards,
                    hard_guard_effect=hard_guard_decision.effect,
                ),
                status="ok",
                model=model,
                decision_source=decision_source,
                reason_code=None,
                provider_metadata=provider_metadata,
            )
        except _ValidationJsonError as exc:
            last_reason_code = str(exc) or "invalid_json"
        except _ValidationPayloadError as exc:
            last_reason_code = str(exc) or "validation_error"
        except Exception as exc:
            last_reason_code = _request_reason_code(exc, requests_module)

    return _build_fail_open_result(
        primary_verdict=primary_verdict,
        reason_code=last_reason_code,
        model=str(runtime_model_settings["fallback_model"]),
        applied_hard_guards=hard_guard_decision.applied_hard_guards,
        hard_guard_effect=hard_guard_decision.effect,
    )


def build_validated_output(
    *,
    primary_verdict: Any,
    justifications: Any,
    validation_dialogue_context: Any,
    canonical_inputs: Any,
    requests_module: Any = requests,
) -> ValidationAgentResult:
    runtime_model_settings = _runtime_model_settings()
    primary_verdict_payload = _validated_primary_verdict(primary_verdict)
    justifications_payload = _validated_support_mapping(
        justifications,
        error_code="invalid_justifications",
        allow_empty=True,
    )
    validation_dialogue_context_payload = _validated_validation_dialogue_context(validation_dialogue_context)
    canonical_inputs_payload = _validated_support_mapping(
        canonical_inputs,
        error_code="invalid_canonical_inputs",
        allow_empty=True,
    )
    hard_guard_decision = hard_guards.evaluate_hard_guards(
        primary_verdict=primary_verdict_payload,
        canonical_inputs=canonical_inputs_payload,
    )

    system_prompt = _load_system_prompt()
    if not system_prompt:
        return _build_fail_open_result(
            primary_verdict=primary_verdict_payload,
            reason_code="prompt_missing",
            model=runtime_model_settings["primary_model"],
            applied_hard_guards=hard_guard_decision.applied_hard_guards,
            hard_guard_effect=hard_guard_decision.effect,
        )

    return _run_model_fallback(
        primary_verdict=primary_verdict_payload,
        justifications=justifications_payload,
        validation_dialogue_context=validation_dialogue_context_payload,
        canonical_inputs=canonical_inputs_payload,
        hard_guard_decision=hard_guard_decision,
        system_prompt=system_prompt,
        runtime_model_settings=runtime_model_settings,
        requests_module=requests_module,
    )
