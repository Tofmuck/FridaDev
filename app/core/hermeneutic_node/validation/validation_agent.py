from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Mapping, Sequence

import requests

from admin import runtime_settings
from core import llm_client
from core import prompt_loader
from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input

logger = logging.getLogger('frida.validation_agent')

SCHEMA_VERSION = "v1"
PRIMARY_MODEL = "openai/gpt-5.4-mini"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
PROMPT_PATH = "prompts/validation_agent.txt"
REQUEST_TIMEOUT_S = 10
MAX_RESPONSE_TOKENS = 80
MAX_VALIDATION_CONTEXT_MESSAGES = canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES
MAX_VALIDATION_CONTEXT_MESSAGE_CHARS = 420
MAX_VALIDATION_CONTEXT_JSON_CHARS = 4200
MAX_PRIMARY_VERDICT_JSON_CHARS = 1000
MAX_JUSTIFICATIONS_JSON_CHARS = 700
MAX_CANONICAL_INPUTS_JSON_CHARS = 700
RUNTIME_SETTINGS_SECTION = "validation_agent_model"

ALLOWED_VALIDATION_DECISIONS = ("confirm", "challenge", "clarify", "suspend")
ALLOWED_PRIMARY_JUDGMENT_POSTURES = ("answer", "clarify", "suspend")
ALLOWED_FINAL_OUTPUT_REGIMES = ("meta", "simple")

_ALLOWED_PRIMARY_VERDICT_KEYS = {
    "schema_version",
    "epistemic_regime",
    "proof_regime",
    "uncertainty_posture",
    "judgment_posture",
    "discursive_regime",
    "resituation_level",
    "time_reference_mode",
    "source_priority",
    "source_conflicts",
    "upstream_advisory",
    "pipeline_directives_provisional",
    "audit",
}
_ALLOWED_PRIMARY_AUDIT_KEYS = {"fail_open", "state_used", "degraded_fields"}
_ALLOWED_UPSTREAM_ADVISORY_KEYS = {
    "schema_version",
    "recommended_judgment_posture",
    "proposed_output_regime",
    "active_signal_families",
    "active_signal_families_count",
    "constraint_present",
}
_ALLOWED_MODEL_PAYLOAD_KEYS = {
    "schema_version",
    "final_judgment_posture",
    "final_output_regime",
    "arbiter_reason",
}


@dataclass(frozen=True)
class ValidationAgentResult:
    validated_output: dict[str, Any]
    status: str
    model: str
    decision_source: str
    reason_code: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class _ValidationJsonError(ValueError):
    pass


class _ValidationPayloadError(ValueError):
    pass


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _stable_unique(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        normalized = _text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        ordered.append(normalized)
    return ordered


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _compact_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


def _bounded_json_preview(value: Any, *, max_chars: int) -> str:
    raw = _compact_json(value)
    if len(raw) <= max_chars:
        return raw

    preview_chars = max(32, max_chars - 48)
    bounded = _compact_json({"truncated": True, "preview": _compact_text(raw, max_chars=preview_chars)})
    while len(bounded) > max_chars and preview_chars > 16:
        preview_chars -= 16
        bounded = _compact_json({"truncated": True, "preview": _compact_text(raw, max_chars=preview_chars)})
    return bounded


def _compacted_validation_dialogue_context(value: Any) -> str:
    payload = _mapping(value)
    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list):
        return _bounded_json_preview(payload, max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS)

    retained_messages: list[dict[str, Any]] = []
    content_truncated = False
    for item in raw_messages[-MAX_VALIDATION_CONTEXT_MESSAGES:]:
        message_payload = _mapping(item)
        role = _text(message_payload.get("role"))
        if role not in {"user", "assistant"}:
            continue
        raw_content = _text(message_payload.get("content"))
        content = _compact_text(raw_content, max_chars=MAX_VALIDATION_CONTEXT_MESSAGE_CHARS)
        content_truncated = content_truncated or raw_content != content
        retained_messages.append(
            {
                "role": role,
                "timestamp": _text(message_payload.get("timestamp")) or None,
                "content": content,
            }
        )

    return _bounded_json_preview(
        {
            "schema_version": _text(payload.get("schema_version")) or SCHEMA_VERSION,
            "message_count": int(payload.get("source_message_count") or len(raw_messages)),
            "retained_message_count": len(retained_messages),
            "current_user_retained": bool(
                payload.get(
                    "current_user_retained",
                    bool(retained_messages and _text(retained_messages[-1].get("role")) == "user"),
                )
            ),
            "last_assistant_retained": bool(
                payload.get(
                    "last_assistant_retained",
                    any(_text(item.get("role")) == "assistant" for item in retained_messages),
                )
            ),
            "messages": retained_messages,
            "truncated": bool(payload.get("truncated", False) or content_truncated),
        },
        max_chars=MAX_VALIDATION_CONTEXT_JSON_CHARS,
    )


def _validated_string_list(value: Any, *, error_code: str) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error_code)

    normalized: list[str] = []
    for item in value:
        text_value = _text(item)
        if not text_value:
            raise ValueError(error_code)
        normalized.append(text_value)
    return _stable_unique(normalized)


def _validated_source_priority(value: Any) -> list[list[str]]:
    if not isinstance(value, list):
        raise ValueError("invalid_primary_verdict")

    validated: list[list[str]] = []
    for rank in value:
        if not isinstance(rank, list):
            raise ValueError("invalid_primary_verdict")
        normalized_rank = _validated_string_list(rank, error_code="invalid_primary_verdict")
        validated.append(normalized_rank)
    return validated


def _validated_source_conflicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise ValueError("invalid_primary_verdict")

    conflicts: list[dict[str, Any]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_primary_verdict")
        conflicts.append(dict(item))
    return conflicts


def _validated_primary_verdict(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    payload_keys = set(payload.keys())
    if payload_keys != _ALLOWED_PRIMARY_VERDICT_KEYS and payload_keys != (
        _ALLOWED_PRIMARY_VERDICT_KEYS - {"upstream_advisory"}
    ):
        raise ValueError("invalid_primary_verdict")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise ValueError("invalid_primary_verdict")

    judgment_posture = _text(payload.get("judgment_posture"))
    if judgment_posture not in ALLOWED_PRIMARY_JUDGMENT_POSTURES:
        raise ValueError("invalid_primary_verdict")

    for field_name in (
        "epistemic_regime",
        "proof_regime",
        "uncertainty_posture",
        "discursive_regime",
        "resituation_level",
        "time_reference_mode",
    ):
        if not _text(payload.get(field_name)):
            raise ValueError("invalid_primary_verdict")

    audit_payload = _mapping(payload.get("audit"))
    if set(audit_payload.keys()) != _ALLOWED_PRIMARY_AUDIT_KEYS:
        raise ValueError("invalid_primary_verdict")
    if not isinstance(audit_payload.get("fail_open"), bool):
        raise ValueError("invalid_primary_verdict")
    if not isinstance(audit_payload.get("state_used"), bool):
        raise ValueError("invalid_primary_verdict")

    upstream_advisory_payload = _validated_upstream_advisory(
        payload.get("upstream_advisory"),
        fallback_judgment_posture=judgment_posture,
        fallback_output_regime=_text(payload.get("discursive_regime")),
        fallback_constraint_present=bool(payload.get("source_conflicts")),
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "epistemic_regime": _text(payload.get("epistemic_regime")),
        "proof_regime": _text(payload.get("proof_regime")),
        "uncertainty_posture": _text(payload.get("uncertainty_posture")),
        "judgment_posture": judgment_posture,
        "discursive_regime": _text(payload.get("discursive_regime")),
        "resituation_level": _text(payload.get("resituation_level")),
        "time_reference_mode": _text(payload.get("time_reference_mode")),
        "source_priority": _validated_source_priority(payload.get("source_priority")),
        "source_conflicts": _validated_source_conflicts(payload.get("source_conflicts")),
        "upstream_advisory": upstream_advisory_payload,
        "pipeline_directives_provisional": _validated_string_list(
            payload.get("pipeline_directives_provisional"),
            error_code="invalid_primary_verdict",
        ),
        "audit": {
            "fail_open": bool(audit_payload.get("fail_open")),
            "state_used": bool(audit_payload.get("state_used")),
            "degraded_fields": _validated_string_list(
                audit_payload.get("degraded_fields"),
                error_code="invalid_primary_verdict",
            )
            if audit_payload.get("degraded_fields") != []
            else [],
        },
    }


def _validated_upstream_advisory(
    value: Any,
    *,
    fallback_judgment_posture: str,
    fallback_output_regime: str,
    fallback_constraint_present: bool,
) -> dict[str, Any]:
    payload = _mapping(value)
    if not payload:
        return {
            "schema_version": SCHEMA_VERSION,
            "recommended_judgment_posture": fallback_judgment_posture,
            "proposed_output_regime": fallback_output_regime,
            "active_signal_families": [],
            "active_signal_families_count": 0,
            "constraint_present": bool(fallback_constraint_present),
        }

    if set(payload.keys()) != _ALLOWED_UPSTREAM_ADVISORY_KEYS:
        raise ValueError("invalid_primary_verdict")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise ValueError("invalid_primary_verdict")

    recommended_judgment_posture = _text(payload.get("recommended_judgment_posture"))
    if recommended_judgment_posture not in ALLOWED_PRIMARY_JUDGMENT_POSTURES:
        raise ValueError("invalid_primary_verdict")

    proposed_output_regime = _text(payload.get("proposed_output_regime"))
    if not proposed_output_regime:
        raise ValueError("invalid_primary_verdict")

    active_signal_families = (
        _validated_string_list(
            payload.get("active_signal_families"),
            error_code="invalid_primary_verdict",
        )
        if payload.get("active_signal_families") != []
        else []
    )
    if not isinstance(payload.get("constraint_present"), bool):
        raise ValueError("invalid_primary_verdict")

    return {
        "schema_version": SCHEMA_VERSION,
        "recommended_judgment_posture": recommended_judgment_posture,
        "proposed_output_regime": proposed_output_regime,
        "active_signal_families": active_signal_families,
        "active_signal_families_count": len(active_signal_families),
        "constraint_present": bool(payload.get("constraint_present")),
    }


def _upstream_advisory(primary_verdict: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = _mapping(primary_verdict.get("upstream_advisory"))
    if payload:
        return payload
    return {
        "recommended_judgment_posture": _text(primary_verdict.get("judgment_posture")),
        "proposed_output_regime": _text(primary_verdict.get("discursive_regime")),
        "active_signal_families": [],
        "active_signal_families_count": 0,
        "constraint_present": bool(primary_verdict.get("source_conflicts")),
    }


def _validated_support_mapping(value: Any, *, error_code: str, allow_empty: bool) -> dict[str, Any]:
    payload = _mapping(value)
    if not isinstance(value, Mapping):
        raise ValueError(error_code)
    if not allow_empty and not payload:
        raise ValueError(error_code)
    if "schema_version" in payload and _text(payload.get("schema_version")) not in {"", SCHEMA_VERSION}:
        raise ValueError(error_code)
    return dict(payload)


def _validated_validation_dialogue_context(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    if not isinstance(value, Mapping):
        raise ValueError("invalid_validation_dialogue_context")
    if "schema_version" in payload and _text(payload.get("schema_version")) not in {"", SCHEMA_VERSION}:
        raise ValueError("invalid_validation_dialogue_context")

    raw_messages = payload.get("messages")
    if not isinstance(raw_messages, list) or not raw_messages:
        raise ValueError("invalid_validation_dialogue_context")

    normalized_payload = canonical_recent_context_input.build_validation_dialogue_context(
        messages=raw_messages,
        summary_input_payload=None,
        max_messages=MAX_VALIDATION_CONTEXT_MESSAGES,
    )
    retained_messages = normalized_payload.get("messages") or []
    if not retained_messages:
        raise ValueError("invalid_validation_dialogue_context")

    validated_payload = dict(payload)
    validated_payload.update(normalized_payload)
    if "schema_version" in validated_payload:
        validated_payload["schema_version"] = _text(validated_payload.get("schema_version")) or SCHEMA_VERSION
    return validated_payload


def _extract_json_blob(raw: Any) -> str:
    text = str(raw or "").strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text


def _safe_json_loads(raw: Any) -> dict[str, Any]:
    try:
        payload = json.loads(_extract_json_blob(raw))
    except json.JSONDecodeError as exc:
        raise _ValidationJsonError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise _ValidationJsonError("invalid_json")
    return payload


def _validated_model_verdict(value: Any) -> dict[str, str]:
    payload = _mapping(value)
    if set(payload.keys()) != _ALLOWED_MODEL_PAYLOAD_KEYS:
        raise _ValidationPayloadError("validation_error")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise _ValidationPayloadError("validation_error")

    final_judgment_posture = _text(payload.get("final_judgment_posture"))
    if final_judgment_posture not in ALLOWED_PRIMARY_JUDGMENT_POSTURES:
        raise _ValidationPayloadError("validation_error")

    final_output_regime = _text(payload.get("final_output_regime"))
    if final_output_regime not in ALLOWED_FINAL_OUTPUT_REGIMES:
        raise _ValidationPayloadError("validation_error")

    arbiter_reason = _compact_text(_text(payload.get("arbiter_reason")), max_chars=160)
    if not arbiter_reason:
        raise _ValidationPayloadError("validation_error")

    return {
        "schema_version": SCHEMA_VERSION,
        "final_judgment_posture": final_judgment_posture,
        "final_output_regime": final_output_regime,
        "arbiter_reason": arbiter_reason,
    }


def _legacy_validation_decision(
    *,
    upstream_recommendation_posture: str,
    upstream_output_regime_proposed: str,
    final_judgment_posture: str,
    final_output_regime: str,
) -> str:
    if final_judgment_posture == "suspend":
        return "suspend"
    if final_judgment_posture == "clarify":
        return "clarify"
    if final_judgment_posture != upstream_recommendation_posture:
        return "challenge"
    if final_output_regime != upstream_output_regime_proposed:
        return "challenge"
    return "confirm"


def _advisory_trace(
    *,
    primary_verdict: Mapping[str, Any],
    final_judgment_posture: str,
    final_output_regime: str,
) -> tuple[bool, list[str], list[str]]:
    followed: list[str] = []
    overridden: list[str] = []
    upstream_advisory = _upstream_advisory(primary_verdict)
    upstream_recommendation_posture = _text(upstream_advisory.get("recommended_judgment_posture"))
    upstream_output_regime_proposed = _text(upstream_advisory.get("proposed_output_regime"))

    if upstream_recommendation_posture:
        target = followed if upstream_recommendation_posture == final_judgment_posture else overridden
        target.append("upstream_recommendation_posture")
    if upstream_output_regime_proposed:
        target = followed if upstream_output_regime_proposed == final_output_regime else overridden
        target.append("upstream_output_regime_proposed")

    return (not overridden and bool(followed), followed, overridden)


def _pipeline_directives_final(
    *,
    final_judgment_posture: str,
    final_output_regime: str,
    fail_open: bool,
) -> list[str]:
    directives = [f"posture_{final_judgment_posture}", f"regime_{final_output_regime}"]
    if fail_open:
        directives.append("fallback_validation")
    return _stable_unique(directives)


def _build_validated_output_payload(
    *,
    primary_verdict: Mapping[str, Any],
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_reason: str,
    fail_open: bool,
    applied_hard_guards: Sequence[str],
) -> dict[str, Any]:
    upstream_advisory = _upstream_advisory(primary_verdict)
    upstream_recommendation_posture = _text(upstream_advisory.get("recommended_judgment_posture"))
    upstream_output_regime_proposed = _text(upstream_advisory.get("proposed_output_regime"))
    arbiter_followed_upstream, followed, overridden = _advisory_trace(
        primary_verdict=primary_verdict,
        final_judgment_posture=final_judgment_posture,
        final_output_regime=final_output_regime,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_decision": _legacy_validation_decision(
            upstream_recommendation_posture=upstream_recommendation_posture,
            upstream_output_regime_proposed=upstream_output_regime_proposed,
            final_judgment_posture=final_judgment_posture,
            final_output_regime=final_output_regime,
        ),
        "final_judgment_posture": final_judgment_posture,
        "final_output_regime": final_output_regime,
        "pipeline_directives_final": _pipeline_directives_final(
            final_judgment_posture=final_judgment_posture,
            final_output_regime=final_output_regime,
            fail_open=fail_open,
        ),
        "arbiter_followed_upstream": arbiter_followed_upstream,
        "advisory_recommendations_followed": _stable_unique(followed),
        "advisory_recommendations_overridden": _stable_unique(overridden),
        "applied_hard_guards": _stable_unique(applied_hard_guards),
        "arbiter_reason": _compact_text(arbiter_reason, max_chars=160),
    }


def _build_fail_open_validated_output(
    *,
    primary_verdict: Mapping[str, Any],
    reason_code: str,
) -> dict[str, Any]:
    return _build_validated_output_payload(
        primary_verdict=primary_verdict,
        final_judgment_posture="suspend",
        final_output_regime="simple",
        arbiter_reason=f"validation fail-open ({_text(reason_code) or 'upstream_error'})",
        fail_open=True,
        applied_hard_guards=[],
    )


def _build_fail_open_result(
    *,
    primary_verdict: Mapping[str, Any],
    reason_code: str,
    model: str,
) -> ValidationAgentResult:
    return ValidationAgentResult(
        validated_output=_build_fail_open_validated_output(
            primary_verdict=primary_verdict,
            reason_code=reason_code,
        ),
        status="error",
        model=str(model or FALLBACK_MODEL),
        decision_source="fail_open",
        reason_code=str(reason_code or "upstream_error"),
    )


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
    }


def _build_messages(
    *,
    system_prompt: str,
    primary_verdict: Mapping[str, Any],
    justifications: Mapping[str, Any],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
) -> list[dict[str, str]]:
    compacted_validation_dialogue_context = _compacted_validation_dialogue_context(validation_dialogue_context)
    compacted_primary_verdict = _bounded_json_preview(primary_verdict, max_chars=MAX_PRIMARY_VERDICT_JSON_CHARS)
    compacted_justifications = _bounded_json_preview(justifications, max_chars=MAX_JUSTIFICATIONS_JSON_CHARS)
    compacted_canonical_inputs = _bounded_json_preview(canonical_inputs, max_chars=MAX_CANONICAL_INPUTS_JSON_CHARS)
    return [
        {"role": "system", "content": str(system_prompt or "")},
        {
            "role": "user",
            "content": (
                "validation_dialogue_context (matiere hermeneutique principale, fenetre dialogique locale canonisee):\n"
                f"{compacted_validation_dialogue_context}\n\n"
                "primary_verdict (recommendation structuree amont, secondaire et non terminale):\n"
                f"{compacted_primary_verdict}\n\n"
                "justifications (support secondaire frere, hors primary_verdict):\n"
                f"{compacted_justifications}\n\n"
                "canonical_inputs (supports secondaires de relecture contextuelle):\n"
                f"{compacted_canonical_inputs}\n\n"
                "Tache:\n"
                "- decide final_judgment_posture\n"
                "- decide final_output_regime\n"
                "- privilegie la lecture la plus naturelle du tour, la continuite dialogique locale et la reponse simple\n"
                "- si answer reste possible, privilegie final_output_regime = simple\n"
                "- reserve meta aux cas ou une reprise meta est reellement necessaire\n"
                "- validation_decision legacy sera derivee downstream: ne l'invente pas\n"
                "- reponds en JSON strict uniquement\n"
                '- schema attendu: {"schema_version":"v1","final_judgment_posture":"answer|clarify|suspend","final_output_regime":"simple|meta","arbiter_reason":"raison_courte_lisible"}'
            ),
        },
    ]


def _normalized_arbiter_verdict(
    *,
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_reason: str,
) -> dict[str, str]:
    normalized_posture = _text(final_judgment_posture)
    normalized_output_regime = _text(final_output_regime)
    normalized_reason = _compact_text(_text(arbiter_reason), max_chars=160)
    return {
        "final_judgment_posture": normalized_posture,
        "final_output_regime": normalized_output_regime,
        "arbiter_reason": normalized_reason,
    }


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
    system_prompt: str,
    primary_verdict: Mapping[str, Any],
    justifications: Mapping[str, Any],
    validation_dialogue_context: Mapping[str, Any],
    canonical_inputs: Mapping[str, Any],
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    requests_module: Any,
) -> tuple[dict[str, str], dict[str, Any]]:
    response = requests_module.post(
        llm_client.or_chat_completions_url(),
        json={
            "model": model,
            "messages": _build_messages(
                system_prompt=system_prompt,
                primary_verdict=primary_verdict,
                justifications=justifications,
                validation_dialogue_context=validation_dialogue_context,
                canonical_inputs=canonical_inputs,
            ),
            "temperature": temperature,
            "top_p": top_p,
            "max_tokens": _bounded_response_max_tokens(max_tokens),
        },
        headers=llm_client.or_headers(caller="validation_agent"),
        timeout=timeout_s,
    )
    response.raise_for_status()
    response_payload = llm_client.read_openrouter_response_payload(response)
    provider_metadata = llm_client.extract_openrouter_provider_metadata(
        response_payload,
        requested_model=model,
    )
    llm_client.log_provider_metadata(logger, 'validation_agent_provider_response', provider_metadata)
    return (
        _validated_model_verdict(_safe_json_loads(llm_client.extract_openrouter_text(response_payload))),
        provider_metadata,
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

    system_prompt = _load_system_prompt()
    if not system_prompt:
        return _build_fail_open_result(
            primary_verdict=primary_verdict_payload,
            reason_code="prompt_missing",
            model=runtime_model_settings["primary_model"],
        )

    last_reason_code = "upstream_error"
    for model, decision_source in (
        (runtime_model_settings["primary_model"], "primary"),
        (runtime_model_settings["fallback_model"], "fallback"),
    ):
        try:
            verdict_payload, provider_metadata = _call_model(
                model=model,
                system_prompt=system_prompt,
                primary_verdict=primary_verdict_payload,
                justifications=justifications_payload,
                validation_dialogue_context=validation_dialogue_context_payload,
                canonical_inputs=canonical_inputs_payload,
                timeout_s=runtime_model_settings["timeout_s"],
                temperature=runtime_model_settings["temperature"],
                top_p=runtime_model_settings["top_p"],
                max_tokens=runtime_model_settings["max_tokens"],
                requests_module=requests_module,
            )
            normalized_verdict = _normalized_arbiter_verdict(
                final_judgment_posture=verdict_payload["final_judgment_posture"],
                final_output_regime=verdict_payload["final_output_regime"],
                arbiter_reason=verdict_payload["arbiter_reason"],
            )
            return ValidationAgentResult(
                validated_output=_build_validated_output_payload(
                    primary_verdict=primary_verdict_payload,
                    final_judgment_posture=normalized_verdict["final_judgment_posture"],
                    final_output_regime=normalized_verdict["final_output_regime"],
                    arbiter_reason=normalized_verdict["arbiter_reason"],
                    fail_open=False,
                    applied_hard_guards=[],
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
        primary_verdict=primary_verdict_payload,
        reason_code=last_reason_code,
        model=runtime_model_settings["fallback_model"],
    )
