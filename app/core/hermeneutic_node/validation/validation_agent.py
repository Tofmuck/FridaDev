from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

import requests

import config
from core import llm_client
from core import prompt_loader


SCHEMA_VERSION = "v1"
PRIMARY_MODEL = "openai/gpt-5.4-mini"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
PROMPT_PATH = "prompts/validation_agent.txt"
REQUEST_TIMEOUT_S = 10
MAX_RESPONSE_TOKENS = 80
MAX_VALIDATION_CONTEXT_MESSAGES = 8
MAX_VALIDATION_CONTEXT_MESSAGE_CHARS = 420
MAX_VALIDATION_CONTEXT_JSON_CHARS = 4200
MAX_PRIMARY_VERDICT_JSON_CHARS = 1000
MAX_JUSTIFICATIONS_JSON_CHARS = 700
MAX_CANONICAL_INPUTS_JSON_CHARS = 700

ALLOWED_VALIDATION_DECISIONS = ("confirm", "challenge", "clarify", "suspend")
ALLOWED_PRIMARY_JUDGMENT_POSTURES = ("answer", "clarify", "suspend")

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
    "pipeline_directives_provisional",
    "audit",
}
_ALLOWED_PRIMARY_AUDIT_KEYS = {"fail_open", "state_used", "degraded_fields"}
_ALLOWED_MODEL_PAYLOAD_KEYS = {"schema_version", "validation_decision"}
_FINAL_POSTURE_BY_PRIMARY_AND_DECISION = {
    "answer": {
        "confirm": "answer",
        "challenge": "answer",
        "clarify": "clarify",
        "suspend": "suspend",
    },
    "clarify": {
        "confirm": "clarify",
        "challenge": "clarify",
        "clarify": "clarify",
        "suspend": "suspend",
    },
    "suspend": {
        "confirm": "suspend",
        "challenge": "suspend",
        "clarify": "clarify",
        "suspend": "suspend",
    },
}
@dataclass(frozen=True)
class ValidationAgentResult:
    validated_output: dict[str, Any]
    status: str
    model: str
    decision_source: str
    reason_code: str | None = None


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
            "message_count": len(raw_messages),
            "retained_message_count": len(retained_messages),
            "messages": retained_messages,
            "truncated": bool(len(raw_messages) > len(retained_messages) or content_truncated),
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
    if set(payload.keys()) != _ALLOWED_PRIMARY_VERDICT_KEYS:
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
def _validated_support_mapping(value: Any, *, error_code: str, allow_empty: bool) -> dict[str, Any]:
    payload = _mapping(value)
    if not isinstance(value, Mapping):
        raise ValueError(error_code)
    if not allow_empty and not payload:
        raise ValueError(error_code)
    if "schema_version" in payload and _text(payload.get("schema_version")) not in {"", SCHEMA_VERSION}:
        raise ValueError(error_code)
    return dict(payload)
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
def _extract_response_text(response: Any) -> str:
    try:
        return llm_client._sanitize_encoding(response.json()["choices"][0]["message"]["content"]).strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise _ValidationJsonError("invalid_json") from exc
def _validated_model_decision(value: Any) -> dict[str, str]:
    payload = _mapping(value)
    if set(payload.keys()) != _ALLOWED_MODEL_PAYLOAD_KEYS:
        raise _ValidationPayloadError("validation_error")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise _ValidationPayloadError("validation_error")

    validation_decision = _text(payload.get("validation_decision"))
    if validation_decision not in ALLOWED_VALIDATION_DECISIONS:
        raise _ValidationPayloadError("validation_error")

    return {
        "schema_version": SCHEMA_VERSION,
        "validation_decision": validation_decision,
    }
def _build_fail_open_validated_output() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_decision": "suspend",
        "final_judgment_posture": "suspend",
        "pipeline_directives_final": ["posture_suspend", "fallback_validation"],
    }
def _build_fail_open_result(*, reason_code: str, model: str) -> ValidationAgentResult:
    return ValidationAgentResult(
        validated_output=_build_fail_open_validated_output(),
        status="error",
        model=str(model or FALLBACK_MODEL),
        decision_source="fail_open",
        reason_code=str(reason_code or "upstream_error"),
    )
def _load_system_prompt() -> str:
    return prompt_loader.read_prompt_text(PROMPT_PATH)
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
                "validation_dialogue_context (matiere hermeneutique principale de la relecture):\n"
                f"{compacted_validation_dialogue_context}\n\n"
                "primary_verdict (support structure amont, non terminal):\n"
                f"{compacted_primary_verdict}\n\n"
                "justifications (artefact frere, hors primary_verdict):\n"
                f"{compacted_justifications}\n\n"
                "canonical_inputs (supports de relecture contextuelle):\n"
                f"{compacted_canonical_inputs}\n\n"
                "Tache:\n"
                "- decide seulement validation_decision\n"
                "- n'invente pas final_judgment_posture\n"
                "- n'invente pas pipeline_directives_final\n"
                "- reponds en JSON strict uniquement\n"
                '- schema attendu: {"schema_version":"v1","validation_decision":"confirm|challenge|clarify|suspend"}'
            ),
        },
    ]
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
    requests_module: Any,
) -> dict[str, str]:
    response = requests_module.post(
        f"{config.OR_BASE}/chat/completions",
        json={
            "model": model,
            "messages": _build_messages(
                system_prompt=system_prompt,
                primary_verdict=primary_verdict,
                justifications=justifications,
                validation_dialogue_context=validation_dialogue_context,
                canonical_inputs=canonical_inputs,
            ),
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": MAX_RESPONSE_TOKENS,
        },
        headers=llm_client.or_headers(caller="llm"),
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    return _validated_model_decision(_safe_json_loads(_extract_response_text(response)))
def _resolved_final_judgment_posture(*, primary_judgment_posture: str, validation_decision: str) -> str:
    return _FINAL_POSTURE_BY_PRIMARY_AND_DECISION[primary_judgment_posture][validation_decision]
def _pipeline_directives_final(*, final_judgment_posture: str, fail_open: bool) -> list[str]:
    directives = [f"posture_{final_judgment_posture}"]
    if fail_open:
        directives.append("fallback_validation")
    return _stable_unique(directives)
def _build_validated_output_payload(*, validation_decision: str, final_judgment_posture: str, fail_open: bool) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "validation_decision": validation_decision,
        "final_judgment_posture": final_judgment_posture,
        "pipeline_directives_final": _pipeline_directives_final(
            final_judgment_posture=final_judgment_posture,
            fail_open=fail_open,
        ),
    }
def build_validated_output(
    *,
    primary_verdict: Any,
    justifications: Any,
    validation_dialogue_context: Any,
    canonical_inputs: Any,
    requests_module: Any = requests,
) -> ValidationAgentResult:
    primary_verdict_payload = _validated_primary_verdict(primary_verdict)
    justifications_payload = _validated_support_mapping(
        justifications,
        error_code="invalid_justifications",
        allow_empty=True,
    )
    validation_dialogue_context_payload = _validated_support_mapping(
        validation_dialogue_context,
        error_code="invalid_validation_dialogue_context",
        allow_empty=False,
    )
    canonical_inputs_payload = _validated_support_mapping(
        canonical_inputs,
        error_code="invalid_canonical_inputs",
        allow_empty=True,
    )

    system_prompt = _load_system_prompt()
    if not system_prompt:
        return _build_fail_open_result(reason_code="prompt_missing", model=PRIMARY_MODEL)

    last_reason_code = "upstream_error"
    for model, decision_source in (
        (PRIMARY_MODEL, "primary"),
        (FALLBACK_MODEL, "fallback"),
    ):
        try:
            decision_payload = _call_model(
                model=model,
                system_prompt=system_prompt,
                primary_verdict=primary_verdict_payload,
                justifications=justifications_payload,
                validation_dialogue_context=validation_dialogue_context_payload,
                canonical_inputs=canonical_inputs_payload,
                requests_module=requests_module,
            )
            final_judgment_posture = _resolved_final_judgment_posture(
                primary_judgment_posture=primary_verdict_payload["judgment_posture"],
                validation_decision=decision_payload["validation_decision"],
            )
            return ValidationAgentResult(
                validated_output=_build_validated_output_payload(
                    validation_decision=decision_payload["validation_decision"],
                    final_judgment_posture=final_judgment_posture,
                    fail_open=False,
                ),
                status="ok",
                model=model,
                decision_source=decision_source,
                reason_code=None,
            )
        except _ValidationJsonError as exc:
            last_reason_code = str(exc) or "invalid_json"
        except _ValidationPayloadError as exc:
            last_reason_code = str(exc) or "validation_error"
        except Exception as exc:
            last_reason_code = _request_reason_code(exc, requests_module)

    return _build_fail_open_result(reason_code=last_reason_code, model=FALLBACK_MODEL)
