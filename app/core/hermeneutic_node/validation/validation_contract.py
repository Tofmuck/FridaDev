from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from . import hard_guards


SCHEMA_VERSION = "v1"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
ALLOWED_PRIMARY_JUDGMENT_POSTURES = ("answer", "clarify", "suspend")
ALLOWED_FINAL_OUTPUT_REGIMES = ("meta", "simple", "presence")
MAX_VALIDATION_CONTEXT_MESSAGES = canonical_recent_context_input.VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES
LEGACY_MAX_CANONICAL_INPUTS_JSON_CHARS = 700
LEGACY_CANONICAL_PROJECTION_VERSION = "validation_canonical_inputs_v1"
MAX_CANONICAL_INPUTS_JSON_CHARS = 3840
CANONICAL_PROJECTION_VERSION = "validation_canonical_inputs_v2"
CANONICAL_FAMILY_ORDER = (
    "time_input",
    "memory_retrieved",
    "memory_arbitration",
    "summary_input",
    "identity_input",
    "recent_context_input",
    "recent_window_input",
    "user_turn_input",
    "user_turn_signals",
    "stimmung_input",
    "web_input",
)
STIMMUNG_DELIVERY_STATUSES = ("full", "absent")
STIMMUNG_DELIVERY_REASON_CODES = (
    "included",
    "signal_not_present",
    "invalid_signal",
    "contract_budget_exceeded",
)
CANONICAL_FAMILY_DISPOSITIONS = (
    "included",
    "no_data",
    "redundant_elsewhere",
    "optional_not_requested",
    "invalid_input",
    "contract_budget_exceeded",
)
CANONICAL_PROJECTION_CONTRACT_STATUSES = (
    "historical_v1",
    "current_v2",
)
_V2_METADATA_FAMILY_LISTS = (
    ("canonical_projection_included_families", "included"),
    ("canonical_projection_no_data_families", "no_data"),
    ("canonical_projection_redundant_families", "redundant_elsewhere"),
    ("canonical_projection_optional_families", "optional_not_requested"),
    ("canonical_projection_invalid_families", "invalid_input"),
    ("canonical_projection_budget_exceeded_families", "contract_budget_exceeded"),
)

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
_ALLOWED_PRIMARY_AUDIT_FAIL_OPEN_KEYS = _ALLOWED_PRIMARY_AUDIT_KEYS | {
    "fallback_used",
    "fallback_source",
    "node_stage",
    "reason_code",
    "error_class",
}
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
_VALIDATED_OUTPUT_REQUIRED_KEYS = {
    "schema_version",
    "validation_decision",
    "final_judgment_posture",
    "final_output_regime",
    "pipeline_directives_final",
    "arbiter_followed_upstream",
    "advisory_recommendations_followed",
    "advisory_recommendations_overridden",
    "applied_hard_guards",
    "arbiter_reason",
}
_VALIDATION_DECISIONS = {"confirm", "challenge", "clarify", "suspend"}
_ADVISORY_TRACE_CODES = {
    "upstream_recommendation_posture",
    "upstream_output_regime_proposed",
}
_FAIL_OPEN_REASON_CODES = {
    "http_error",
    "invalid_json",
    "prompt_missing",
    "timeout",
    "upstream_error",
    "validation_error",
}


@dataclass(frozen=True)
class ValidationAgentResult:
    validated_output: dict[str, Any]
    status: str
    model: str
    decision_source: str
    reason_code: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class ValidationJsonError(ValueError):
    pass


class ValidationPayloadError(ValueError):
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


def validate_canonical_projection_metadata(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    version = _text(payload.get("canonical_projection_version"))
    if version == LEGACY_CANONICAL_PROJECTION_VERSION:
        expected_budget = LEGACY_MAX_CANONICAL_INPUTS_JSON_CHARS
        contract_status = "historical_v1"
    elif version == CANONICAL_PROJECTION_VERSION:
        expected_budget = MAX_CANONICAL_INPUTS_JSON_CHARS
        contract_status = "current_v2"
    else:
        raise ValueError("unknown_canonical_projection_version")

    chars = payload.get("canonical_projection_chars")
    budget_chars = payload.get("canonical_projection_budget_chars")
    if (
        isinstance(chars, bool)
        or not isinstance(chars, int)
        or isinstance(budget_chars, bool)
        or not isinstance(budget_chars, int)
        or chars < 0
        or budget_chars != expected_budget
        or chars > budget_chars
    ):
        raise ValueError("invalid_canonical_projection_budget")

    included = payload.get("canonical_projection_included_families")
    omitted = payload.get("canonical_projection_omitted_families")
    if not isinstance(included, list) or not isinstance(omitted, list):
        raise ValueError("invalid_canonical_projection_families")
    if any(
        not isinstance(item, str) or item not in CANONICAL_FAMILY_ORDER
        for item in [*included, *omitted]
    ):
        raise ValueError("invalid_canonical_projection_families")
    if len(set(included)) != len(included) or len(set(omitted)) != len(omitted):
        raise ValueError("invalid_canonical_projection_families")
    if set(included) & set(omitted):
        raise ValueError("invalid_canonical_projection_families")
    if included != sorted(included, key=CANONICAL_FAMILY_ORDER.index):
        raise ValueError("invalid_canonical_projection_family_order")
    if omitted != sorted(omitted, key=CANONICAL_FAMILY_ORDER.index):
        raise ValueError("invalid_canonical_projection_family_order")

    family_lists: dict[str, list[str]] = {}
    if version == CANONICAL_PROJECTION_VERSION:
        if _text(payload.get("canonical_projection_contract_status")) != contract_status:
            raise ValueError("invalid_canonical_projection_contract_status")
        disposition_by_family: dict[str, str] = {}
        for key, disposition in _V2_METADATA_FAMILY_LISTS:
            values = payload.get(key)
            if not isinstance(values, list):
                raise ValueError("invalid_canonical_projection_families")
            if any(
                not isinstance(item, str) or item not in CANONICAL_FAMILY_ORDER
                for item in values
            ):
                raise ValueError("invalid_canonical_projection_families")
            if len(set(values)) != len(values):
                raise ValueError("invalid_canonical_projection_families")
            if values != sorted(values, key=CANONICAL_FAMILY_ORDER.index):
                raise ValueError("invalid_canonical_projection_family_order")
            for family in values:
                if family in disposition_by_family:
                    raise ValueError("invalid_canonical_projection_families")
                disposition_by_family[family] = disposition
            family_lists[key] = list(values)
        if set(disposition_by_family) != set(CANONICAL_FAMILY_ORDER):
            raise ValueError("incomplete_canonical_projection_families")
        if family_lists["canonical_projection_included_families"] != list(included):
            raise ValueError("inconsistent_canonical_projection_families")
        derived_omitted = [
            family
            for family in CANONICAL_FAMILY_ORDER
            if disposition_by_family[family] != "included"
        ]
        if derived_omitted != list(omitted):
            raise ValueError("inconsistent_canonical_projection_families")
    else:
        family_lists = {key: [] for key, _disposition in _V2_METADATA_FAMILY_LISTS}

    status = _text(payload.get("stimmung_delivery_status"))
    reason_code = _text(payload.get("stimmung_delivery_reason_code"))
    if status not in STIMMUNG_DELIVERY_STATUSES:
        raise ValueError("invalid_stimmung_delivery_status")
    if reason_code not in STIMMUNG_DELIVERY_REASON_CODES:
        raise ValueError("invalid_stimmung_delivery_reason_code")
    if status == "full":
        if reason_code != "included" or "stimmung_input" not in included or "stimmung_input" in omitted:
            raise ValueError("inconsistent_stimmung_delivery")
    elif (
        reason_code == "included"
        or "stimmung_input" in included
        or (
            reason_code in {"invalid_signal", "contract_budget_exceeded"}
            and "stimmung_input" not in omitted
        )
    ):
        raise ValueError("inconsistent_stimmung_delivery")
    if version == CANONICAL_PROJECTION_VERSION and status == "absent":
        if reason_code == "signal_not_present":
            expected_list = "canonical_projection_no_data_families"
        elif reason_code == "invalid_signal":
            expected_list = "canonical_projection_invalid_families"
        else:
            expected_list = "canonical_projection_budget_exceeded_families"
        if "stimmung_input" not in family_lists[expected_list]:
            raise ValueError("inconsistent_stimmung_delivery")
    if payload.get("raw_content_included") is not False:
        raise ValueError("invalid_canonical_projection_raw_content")

    return {
        "canonical_projection_version": version,
        "canonical_projection_contract_status": contract_status,
        "canonical_projection_chars": chars,
        "canonical_projection_budget_chars": budget_chars,
        "canonical_projection_included_families": list(included),
        "canonical_projection_omitted_families": list(omitted),
        "canonical_projection_no_data_families": family_lists[
            "canonical_projection_no_data_families"
        ],
        "canonical_projection_redundant_families": family_lists[
            "canonical_projection_redundant_families"
        ],
        "canonical_projection_optional_families": family_lists[
            "canonical_projection_optional_families"
        ],
        "canonical_projection_invalid_families": family_lists[
            "canonical_projection_invalid_families"
        ],
        "canonical_projection_budget_exceeded_families": family_lists[
            "canonical_projection_budget_exceeded_families"
        ],
        "canonical_projection_unspecified_families": (
            list(omitted) if version == LEGACY_CANONICAL_PROJECTION_VERSION else []
        ),
        "stimmung_delivery_status": status,
        "stimmung_delivery_reason_code": reason_code,
        "raw_content_included": False,
    }


def _compact_text(value: Any, *, max_chars: int) -> str:
    text = " ".join(str(value or "").split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


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


def validate_primary_verdict(value: Any) -> dict[str, Any]:
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
    audit_keys = set(audit_payload.keys())
    if audit_keys != _ALLOWED_PRIMARY_AUDIT_KEYS and audit_keys != _ALLOWED_PRIMARY_AUDIT_FAIL_OPEN_KEYS:
        raise ValueError("invalid_primary_verdict")
    if not isinstance(audit_payload.get("fail_open"), bool):
        raise ValueError("invalid_primary_verdict")
    if not isinstance(audit_payload.get("state_used"), bool):
        raise ValueError("invalid_primary_verdict")
    if audit_keys == _ALLOWED_PRIMARY_AUDIT_FAIL_OPEN_KEYS:
        if not bool(audit_payload.get("fail_open")):
            raise ValueError("invalid_primary_verdict")
        for field_name in ("fallback_source", "node_stage", "reason_code", "error_class"):
            if not _text(audit_payload.get(field_name)):
                raise ValueError("invalid_primary_verdict")

    upstream_advisory_payload = _validated_upstream_advisory(
        payload.get("upstream_advisory"),
        fallback_judgment_posture=judgment_posture,
        fallback_output_regime=_text(payload.get("discursive_regime")),
        fallback_constraint_present=bool(payload.get("source_conflicts")),
    )

    result = {
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
    if audit_keys == _ALLOWED_PRIMARY_AUDIT_FAIL_OPEN_KEYS:
        result["audit"].update(
            {
                "fallback_used": bool(audit_payload.get("fallback_used")),
                "fallback_source": _text(audit_payload.get("fallback_source")),
                "node_stage": _text(audit_payload.get("node_stage")),
                "reason_code": _text(audit_payload.get("reason_code")),
                "error_class": _text(audit_payload.get("error_class")),
            }
        )
    return result


def validate_support_mapping(value: Any, *, error_code: str, allow_empty: bool) -> dict[str, Any]:
    payload = _mapping(value)
    if not isinstance(value, Mapping):
        raise ValueError(error_code)
    if not allow_empty and not payload:
        raise ValueError(error_code)
    if "schema_version" in payload and _text(payload.get("schema_version")) not in {"", SCHEMA_VERSION}:
        raise ValueError(error_code)
    return dict(payload)


def validate_validation_dialogue_context(value: Any) -> dict[str, Any]:
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


def safe_json_loads(raw: Any) -> dict[str, Any]:
    try:
        payload = json.loads(_extract_json_blob(raw))
    except json.JSONDecodeError as exc:
        raise ValidationJsonError("invalid_json") from exc
    if not isinstance(payload, dict):
        raise ValidationJsonError("invalid_json")
    return payload


def validate_model_verdict(
    value: Any,
    *,
    allowed_postures: Sequence[str] = ALLOWED_PRIMARY_JUDGMENT_POSTURES,
) -> dict[str, str]:
    payload = _mapping(value)
    if set(payload.keys()) != _ALLOWED_MODEL_PAYLOAD_KEYS:
        raise ValidationPayloadError("validation_error")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise ValidationPayloadError("validation_error")

    final_judgment_posture = _text(payload.get("final_judgment_posture"))
    if final_judgment_posture not in allowed_postures:
        raise ValidationPayloadError("validation_error")

    final_output_regime = _text(payload.get("final_output_regime"))
    if final_output_regime not in ALLOWED_FINAL_OUTPUT_REGIMES:
        raise ValidationPayloadError("validation_error")
    if final_output_regime == "presence" and final_judgment_posture != "answer":
        raise ValidationPayloadError("validation_error")

    arbiter_reason = _compact_text(_text(payload.get("arbiter_reason")), max_chars=160)
    if not arbiter_reason:
        raise ValidationPayloadError("validation_error")

    return {
        "schema_version": SCHEMA_VERSION,
        "final_judgment_posture": final_judgment_posture,
        "final_output_regime": final_output_regime,
        "arbiter_reason": arbiter_reason,
    }


def _validate_bounded_code_list(
    value: Any,
    *,
    allowed: set[str] | None = None,
    max_items: int = 12,
) -> list[str]:
    if not isinstance(value, list) or len(value) > max_items:
        raise ValidationPayloadError("validation_error")
    if any(
        not isinstance(item, str)
        or not item
        or len(item) > 80
        or (allowed is not None and item not in allowed)
        for item in value
    ):
        raise ValidationPayloadError("validation_error")
    if len(set(value)) != len(value):
        raise ValidationPayloadError("validation_error")
    return list(value)


def validate_validated_output_payload(value: Any, *, fail_open: bool) -> dict[str, Any]:
    payload = _mapping(value)
    allowed_keys = _VALIDATED_OUTPUT_REQUIRED_KEYS | {"hard_guard_effect"}
    if not _VALIDATED_OUTPUT_REQUIRED_KEYS.issubset(payload) or not set(payload).issubset(allowed_keys):
        raise ValidationPayloadError("validation_error")
    if _text(payload.get("schema_version")) != SCHEMA_VERSION:
        raise ValidationPayloadError("validation_error")
    posture = _text(payload.get("final_judgment_posture"))
    regime = _text(payload.get("final_output_regime"))
    if posture not in ALLOWED_PRIMARY_JUDGMENT_POSTURES or regime not in ALLOWED_FINAL_OUTPUT_REGIMES:
        raise ValidationPayloadError("validation_error")
    if regime == "presence" and posture != "answer":
        raise ValidationPayloadError("validation_error")
    if _text(payload.get("validation_decision")) not in _VALIDATION_DECISIONS:
        raise ValidationPayloadError("validation_error")
    directives = _validate_bounded_code_list(payload.get("pipeline_directives_final"), max_items=3)
    expected_directives = [f"posture_{posture}", f"regime_{regime}"]
    if fail_open:
        expected_directives.append("fallback_validation")
    if directives != expected_directives:
        raise ValidationPayloadError("validation_error")
    followed = _validate_bounded_code_list(
        payload.get("advisory_recommendations_followed"), allowed=_ADVISORY_TRACE_CODES,
    )
    overridden = _validate_bounded_code_list(
        payload.get("advisory_recommendations_overridden"), allowed=_ADVISORY_TRACE_CODES,
    )
    if set(followed) & set(overridden):
        raise ValidationPayloadError("validation_error")
    followed_upstream = payload.get("arbiter_followed_upstream")
    if type(followed_upstream) is not bool or followed_upstream != (bool(followed) and not overridden):
        raise ValidationPayloadError("validation_error")
    _validate_bounded_code_list(payload.get("applied_hard_guards"))
    reason = _text(payload.get("arbiter_reason"))
    if not reason or len(reason) > 160:
        raise ValidationPayloadError("validation_error")
    hard_guard_effect = _text(payload.get("hard_guard_effect"))
    if hard_guard_effect and hard_guard_effect not in {
        hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN,
        hard_guards.HARD_GUARD_EFFECT_CAVEAT_REQUIRED,
    }:
        raise ValidationPayloadError("validation_error")
    if hard_guard_effect == hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN and posture == "answer":
        raise ValidationPayloadError("validation_error")
    return dict(payload)


def validate_agent_result(value: Any) -> ValidationAgentResult:
    if not isinstance(value, ValidationAgentResult):
        raise ValidationPayloadError("validation_error")
    if value.status == "ok":
        if value.decision_source not in {"primary", "fallback"} or value.reason_code is not None:
            raise ValidationPayloadError("validation_error")
        validate_validated_output_payload(value.validated_output, fail_open=False)
    elif value.status == "error":
        if value.decision_source != "fail_open" or value.reason_code not in _FAIL_OPEN_REASON_CODES:
            raise ValidationPayloadError("validation_error")
        if value.provider_metadata:
            raise ValidationPayloadError("validation_error")
        if value.validated_output:
            validate_validated_output_payload(value.validated_output, fail_open=True)
    else:
        raise ValidationPayloadError("validation_error")
    if not isinstance(value.model, str) or not value.model.strip() or len(value.model) > 160:
        raise ValidationPayloadError("validation_error")
    if not isinstance(value.provider_metadata, dict):
        raise ValidationPayloadError("validation_error")
    return value


def normalize_arbiter_verdict(
    *,
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_reason: str,
) -> dict[str, str]:
    return {
        "final_judgment_posture": _text(final_judgment_posture),
        "final_output_regime": _text(final_output_regime),
        "arbiter_reason": _compact_text(_text(arbiter_reason), max_chars=160),
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


def build_validated_output_payload(
    *,
    primary_verdict: Mapping[str, Any],
    final_judgment_posture: str,
    final_output_regime: str,
    arbiter_reason: str,
    fail_open: bool,
    applied_hard_guards: Sequence[str],
    hard_guard_effect: str | None = None,
) -> dict[str, Any]:
    upstream_advisory = _upstream_advisory(primary_verdict)
    upstream_recommendation_posture = _text(upstream_advisory.get("recommended_judgment_posture"))
    upstream_output_regime_proposed = _text(upstream_advisory.get("proposed_output_regime"))
    arbiter_followed_upstream, followed, overridden = _advisory_trace(
        primary_verdict=primary_verdict,
        final_judgment_posture=final_judgment_posture,
        final_output_regime=final_output_regime,
    )
    payload = {
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
    if _text(hard_guard_effect):
        payload["hard_guard_effect"] = _text(hard_guard_effect)
    return payload


def _build_fail_open_validated_output(
    *,
    primary_verdict: Mapping[str, Any],
    reason_code: str,
    applied_hard_guards: Sequence[str],
    hard_guard_effect: str | None,
) -> dict[str, Any]:
    if _text(hard_guard_effect) != hard_guards.HARD_GUARD_EFFECT_ANSWER_FORBIDDEN:
        return {}
    return build_validated_output_payload(
        primary_verdict=primary_verdict,
        final_judgment_posture="suspend",
        final_output_regime="simple",
        arbiter_reason=f"validation fail-open ({_text(reason_code) or 'upstream_error'})",
        fail_open=True,
        applied_hard_guards=applied_hard_guards,
        hard_guard_effect=hard_guard_effect,
    )


def build_fail_open_result(
    *,
    primary_verdict: Mapping[str, Any],
    reason_code: str,
    model: str,
    applied_hard_guards: Sequence[str],
    hard_guard_effect: str | None,
) -> ValidationAgentResult:
    return ValidationAgentResult(
        validated_output=_build_fail_open_validated_output(
            primary_verdict=primary_verdict,
            reason_code=reason_code,
            applied_hard_guards=applied_hard_guards,
            hard_guard_effect=hard_guard_effect,
        ),
        status="error",
        model=str(model or FALLBACK_MODEL),
        decision_source="fail_open",
        reason_code=str(reason_code or "upstream_error"),
    )
