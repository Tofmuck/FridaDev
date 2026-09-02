from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
import re
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.doctrine import epistemic_regime as epistemic_doctrine
from core.hermeneutic_node.doctrine import judgment_posture as judgment_doctrine
from core.hermeneutic_node.doctrine import output_regime as output_doctrine
from core.hermeneutic_node.doctrine import source_conflicts as source_conflicts_doctrine
from core.hermeneutic_node.doctrine import source_priority as source_priority_doctrine
from core.hermeneutic_node.inputs import recent_context_input as canonical_recent_context_input
from core.hermeneutic_node.inputs import user_turn_input as canonical_user_turn_input
from . import hard_guards


SCHEMA_VERSION = "v1"
PROVIDER_SCHEMA_NAME = "validation_agent_verdict_v1"
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
    "epistemic_effect",
    "enunciation_directive",
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
_PRIMARY_CONFLICT_KEYS = {"conflict_type", "sources", "issue"}
_RUNTIME_CONFLICT_TYPES = {"conflit_d_ancrage_de_source"}
_RUNTIME_CONFLICT_SOURCES = set(source_conflicts_doctrine._CONTENT_SOURCE_FAMILIES)
_RUNTIME_SIGNAL_FAMILIES = set(canonical_user_turn_input._SIGNAL_FAMILY_ORDER)
_PRIMARY_DEGRADED_FIELDS = _ALLOWED_PRIMARY_VERDICT_KEYS - {
    "schema_version",
    "upstream_advisory",
    "audit",
}
_PRIMARY_ERROR_CLASS_MAX_CHARS = 80
_RUNTIME_TIMESTAMP_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")

MODEL_VERDICT_REQUIRED_KEYS = (
    "schema_version",
    "final_judgment_posture",
    "final_output_regime",
    "arbiter_reason",
)
_ALLOWED_MODEL_PAYLOAD_KEYS = set(MODEL_VERDICT_REQUIRED_KEYS)
_VALIDATED_OUTPUT_REQUIRED_KEYS = {
    "schema_version",
    "validation_decision",
    "final_judgment_posture",
    "final_output_regime",
    "pipeline_directives_final",
    "epistemic_effect",
    "enunciation_directive",
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


def provider_response_format() -> dict[str, Any]:
    return {
        "type": "json_schema",
        "json_schema": {
            "name": PROVIDER_SCHEMA_NAME,
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": list(MODEL_VERDICT_REQUIRED_KEYS),
                "properties": {
                    "schema_version": {"type": "string", "enum": [SCHEMA_VERSION]},
                    "final_judgment_posture": {
                        "type": "string",
                        "enum": list(ALLOWED_PRIMARY_JUDGMENT_POSTURES),
                    },
                    "final_output_regime": {
                        "type": "string",
                        "enum": list(ALLOWED_FINAL_OUTPUT_REGIMES),
                    },
                    "arbiter_reason": {"type": "string"},
                },
            },
        },
    }


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


def _validated_string_list(
    value: Any,
    *,
    error_code: str,
    allowed_values: Sequence[str] | set[str] | None = None,
    max_items: int | None = None,
) -> list[str]:
    if not isinstance(value, list):
        raise ValueError(error_code)
    if max_items is not None and len(value) > max_items:
        raise ValueError(error_code)

    normalized: list[str] = []
    for item in value:
        if not isinstance(item, str):
            raise ValueError(error_code)
        text_value = _text(item)
        if not text_value or (
            allowed_values is not None and text_value not in allowed_values
        ):
            raise ValueError(error_code)
        normalized.append(text_value)
    if len(set(normalized)) != len(normalized):
        raise ValueError(error_code)
    return normalized


def _validated_source_priority(value: Any) -> list[list[str]]:
    source_families = set(source_priority_doctrine.SOURCE_FAMILIES)
    if not isinstance(value, list) or not value or len(value) > len(source_families):
        raise ValueError("invalid_primary_verdict")

    validated: list[list[str]] = []
    seen: set[str] = set()
    for rank in value:
        if not isinstance(rank, list) or not rank:
            raise ValueError("invalid_primary_verdict")
        normalized_rank = _validated_string_list(
            rank,
            error_code="invalid_primary_verdict",
            allowed_values=source_families,
            max_items=len(source_families),
        )
        if seen.intersection(normalized_rank):
            raise ValueError("invalid_primary_verdict")
        seen.update(normalized_rank)
        validated.append(normalized_rank)
    if seen != source_families:
        raise ValueError("invalid_primary_verdict")
    return validated


def _validated_source_conflicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) > len(_RUNTIME_CONFLICT_TYPES):
        raise ValueError("invalid_primary_verdict")

    conflicts: list[dict[str, Any]] = []
    seen_types: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping) or set(item) != _PRIMARY_CONFLICT_KEYS:
            raise ValueError("invalid_primary_verdict")
        conflict_type = _text(item.get("conflict_type"))
        if conflict_type not in _RUNTIME_CONFLICT_TYPES or conflict_type in seen_types:
            raise ValueError("invalid_primary_verdict")
        sources = _validated_string_list(
            item.get("sources"),
            error_code="invalid_primary_verdict",
            allowed_values=_RUNTIME_CONFLICT_SOURCES,
            max_items=len(_RUNTIME_CONFLICT_SOURCES),
        )
        if (
            len(sources) < 2
            or _text(item.get("issue")) != source_conflicts_doctrine.CONFLICT_ISSUE
        ):
            raise ValueError("invalid_primary_verdict")
        seen_types.add(conflict_type)
        conflicts.append(
            {
                "conflict_type": conflict_type,
                "sources": sources,
                "issue": source_conflicts_doctrine.CONFLICT_ISSUE,
            }
        )
    return conflicts


def _valid_primary_error_class(value: Any) -> bool:
    error_class = _text(value)
    return (
        bool(error_class)
        and len(error_class) <= _PRIMARY_ERROR_CLASS_MAX_CHARS
        and all(char.isalnum() or char == "_" for char in error_class)
    )


def _validated_effect_mapping(
    value: Any,
    *,
    allowed_effects: Sequence[str],
    allowed_sources: Sequence[str],
    allowed_reason_codes: Sequence[str],
    error_code: str,
) -> dict[str, str]:
    payload = _mapping(value)
    if set(payload) != {"effect", "source", "reason_code"}:
        raise ValueError(error_code)
    effect = _text(payload.get("effect"))
    source = _text(payload.get("source"))
    reason_code = _text(payload.get("reason_code"))
    if (
        effect not in allowed_effects
        or source not in allowed_sources
        or reason_code not in allowed_reason_codes
    ):
        raise ValueError(error_code)
    return {
        "effect": effect,
        "source": source,
        "reason_code": reason_code,
    }


def _validated_epistemic_effect(value: Any, *, error_code: str) -> dict[str, str]:
    result = _validated_effect_mapping(
        value,
        allowed_effects=(*epistemic_doctrine.EPISTEMIC_REGIMES, "unknown"),
        allowed_sources=epistemic_doctrine.EPISTEMIC_EFFECT_SOURCES,
        allowed_reason_codes=epistemic_doctrine.EPISTEMIC_EFFECT_REASON_CODES,
        error_code=error_code,
    )
    allowed_reasons_by_effect = {
        **epistemic_doctrine.EPISTEMIC_REASON_CODES_BY_EFFECT,
        "unknown": epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES,
    }
    if result["reason_code"] not in allowed_reasons_by_effect[result["effect"]]:
        raise ValueError(error_code)
    if (result["effect"] == "unknown") != (result["source"] == "fail_open"):
        raise ValueError(error_code)
    return result


def _validated_enunciation_directive(value: Any, *, error_code: str) -> dict[str, str]:
    result = _validated_effect_mapping(
        value,
        allowed_effects=judgment_doctrine.ENUNCIATION_EFFECTS,
        allowed_sources=judgment_doctrine.ENUNCIATION_SOURCES,
        allowed_reason_codes=judgment_doctrine.ENUNCIATION_REASON_CODES,
        error_code=error_code,
    )
    if result["effect"] == "unknown":
        if (
            result["source"] != "fail_open"
            or result["reason_code"] not in epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES
        ):
            raise ValueError(error_code)
    elif result["effect"] == "delicate_expression":
        if result != {
            "effect": "delicate_expression",
            "source": "stimmung",
            "reason_code": "affective_transition",
        }:
            raise ValueError(error_code)
    elif not (
        result == {
            "effect": "none",
            "source": "not_applicable",
            "reason_code": "stimmung_absent",
        }
        or result["effect"] == "none"
        and result["source"] == "stimmung"
        and result["reason_code"] in {"stimmung_stable", "stimmung_no_transition"}
    ):
        raise ValueError(error_code)
    return result


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
    if proposed_output_regime not in output_doctrine.DISCURSIVE_REGIMES:
        raise ValueError("invalid_primary_verdict")

    active_signal_families = (
        _validated_string_list(
            payload.get("active_signal_families"),
            error_code="invalid_primary_verdict",
            allowed_values=_RUNTIME_SIGNAL_FAMILIES,
            max_items=len(_RUNTIME_SIGNAL_FAMILIES),
        )
        if payload.get("active_signal_families") != []
        else []
    )
    active_signal_families_count = payload.get("active_signal_families_count")
    if (
        isinstance(active_signal_families_count, bool)
        or not isinstance(active_signal_families_count, int)
        or active_signal_families_count != len(active_signal_families)
    ):
        raise ValueError("invalid_primary_verdict")
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

    closed_fields = {
        "epistemic_regime": epistemic_doctrine.EPISTEMIC_REGIMES,
        "proof_regime": epistemic_doctrine.PROOF_REGIMES,
        "uncertainty_posture": epistemic_doctrine.UNCERTAINTY_POSTURES,
        "discursive_regime": output_doctrine.DISCURSIVE_REGIMES,
        "resituation_level": output_doctrine.RESITUATION_LEVELS,
        "time_reference_mode": output_doctrine.TIME_REFERENCE_MODES,
    }
    for field_name, allowed_values in closed_fields.items():
        if _text(payload.get(field_name)) not in allowed_values:
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
        if audit_payload.get("fallback_used") is not True:
            raise ValueError("invalid_primary_verdict")
        if _text(audit_payload.get("fallback_source")) != "primary_node":
            raise ValueError("invalid_primary_verdict")
        if _text(audit_payload.get("node_stage")) != "primary_node":
            raise ValueError("invalid_primary_verdict")
        if (
            _text(audit_payload.get("reason_code"))
            not in epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES
        ):
            raise ValueError("invalid_primary_verdict")
        if not _valid_primary_error_class(audit_payload.get("error_class")):
            raise ValueError("invalid_primary_verdict")

    epistemic_effect = _validated_epistemic_effect(
        payload.get("epistemic_effect"),
        error_code="invalid_primary_verdict",
    )
    enunciation_directive = _validated_enunciation_directive(
        payload.get("enunciation_directive"),
        error_code="invalid_primary_verdict",
    )
    fail_open = bool(audit_payload.get("fail_open"))
    if fail_open:
        fallback_reason = _text(audit_payload.get("reason_code"))
        for effect_payload in (epistemic_effect, enunciation_directive):
            if effect_payload != {
                "effect": "unknown",
                "source": "fail_open",
                "reason_code": fallback_reason,
            }:
                raise ValueError("invalid_primary_verdict")
        if (
            judgment_posture != "suspend"
            or _text(payload.get("discursive_regime")) != "meta"
        ):
            raise ValueError("invalid_primary_verdict")
    else:
        if (
            epistemic_effect["effect"] != _text(payload.get("epistemic_regime"))
            or epistemic_effect["source"] != "epistemic_inputs"
            or enunciation_directive["source"] == "fail_open"
            or enunciation_directive["effect"] == "unknown"
        ):
            raise ValueError("invalid_primary_verdict")

    source_priority = _validated_source_priority(payload.get("source_priority"))
    source_conflicts = _validated_source_conflicts(payload.get("source_conflicts"))
    if fail_open and source_conflicts:
        raise ValueError("invalid_primary_verdict")

    upstream_advisory_payload = _validated_upstream_advisory(
        payload.get("upstream_advisory"),
        fallback_judgment_posture=judgment_posture,
        fallback_output_regime=_text(payload.get("discursive_regime")),
        fallback_constraint_present=bool(source_conflicts),
    )
    if (
        upstream_advisory_payload["recommended_judgment_posture"] != judgment_posture
        or upstream_advisory_payload["proposed_output_regime"]
        != _text(payload.get("discursive_regime"))
        or upstream_advisory_payload["constraint_present"] != bool(source_conflicts)
        or fail_open and upstream_advisory_payload["active_signal_families"]
    ):
        raise ValueError("invalid_primary_verdict")

    expected_pipeline_directives = [f"posture_{judgment_posture}"]
    if fail_open:
        expected_pipeline_directives.append("fallback_primary_verdict")
    pipeline_directives = _validated_string_list(
        payload.get("pipeline_directives_provisional"),
        error_code="invalid_primary_verdict",
        allowed_values=set(expected_pipeline_directives),
        max_items=len(expected_pipeline_directives),
    )
    if pipeline_directives != expected_pipeline_directives:
        raise ValueError("invalid_primary_verdict")

    degraded_fields = (
        _validated_string_list(
            audit_payload.get("degraded_fields"),
            error_code="invalid_primary_verdict",
            allowed_values=_PRIMARY_DEGRADED_FIELDS,
            max_items=len(_PRIMARY_DEGRADED_FIELDS),
        )
        if audit_payload.get("degraded_fields") != []
        else []
    )
    if bool(degraded_fields) != fail_open:
        raise ValueError("invalid_primary_verdict")

    result = {
        "schema_version": SCHEMA_VERSION,
        "epistemic_regime": _text(payload.get("epistemic_regime")),
        "proof_regime": _text(payload.get("proof_regime")),
        "uncertainty_posture": _text(payload.get("uncertainty_posture")),
        "epistemic_effect": epistemic_effect,
        "enunciation_directive": enunciation_directive,
        "judgment_posture": judgment_posture,
        "discursive_regime": _text(payload.get("discursive_regime")),
        "resituation_level": _text(payload.get("resituation_level")),
        "time_reference_mode": _text(payload.get("time_reference_mode")),
        "source_priority": source_priority,
        "source_conflicts": source_conflicts,
        "upstream_advisory": upstream_advisory_payload,
        "pipeline_directives_provisional": pipeline_directives,
        "audit": {
            "fail_open": bool(audit_payload.get("fail_open")),
            "state_used": bool(audit_payload.get("state_used")),
            "degraded_fields": degraded_fields,
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

    for message in retained_messages:
        timestamp = message.get("timestamp")
        if timestamp is None:
            continue
        if not isinstance(timestamp, str) or not _RUNTIME_TIMESTAMP_RE.fullmatch(timestamp):
            raise ValueError("invalid_validation_dialogue_context")
        try:
            datetime.strptime(timestamp, "%Y-%m-%dT%H:%M:%SZ")
        except ValueError as exc:
            raise ValueError("invalid_validation_dialogue_context") from exc

    return normalized_payload


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
    try:
        epistemic_effect = _validated_epistemic_effect(
            payload.get("epistemic_effect"),
            error_code="validation_error",
        )
        enunciation_directive = _validated_enunciation_directive(
            payload.get("enunciation_directive"),
            error_code="validation_error",
        )
    except ValueError as exc:
        raise ValidationPayloadError("validation_error") from exc
    if fail_open:
        if not all(
            effect_payload["effect"] == "unknown"
            and effect_payload["source"] == "fail_open"
            for effect_payload in (epistemic_effect, enunciation_directive)
        ):
            raise ValidationPayloadError("validation_error")
    else:
        inherited_primary_fail_open = (
            epistemic_effect["effect"] == "unknown"
            and epistemic_effect["source"] == "fail_open"
            and enunciation_directive["effect"] == "unknown"
            and enunciation_directive["source"] == "fail_open"
            and epistemic_effect["reason_code"] == enunciation_directive["reason_code"]
        )
        nominal_effects = (
            epistemic_effect["source"] == "epistemic_inputs"
            and enunciation_directive["source"] != "fail_open"
        )
        if not (inherited_primary_fail_open or nominal_effects):
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
    fail_open_reason_code: str | None = None,
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
        "epistemic_effect": (
            {
                "effect": "unknown",
                "source": "fail_open",
                "reason_code": _text(fail_open_reason_code) or "upstream_error",
            }
            if fail_open
            else _validated_epistemic_effect(
                primary_verdict.get("epistemic_effect"),
                error_code="invalid_primary_verdict",
            )
        ),
        "enunciation_directive": (
            {
                "effect": "unknown",
                "source": "fail_open",
                "reason_code": _text(fail_open_reason_code) or "upstream_error",
            }
            if fail_open
            else _validated_enunciation_directive(
                primary_verdict.get("enunciation_directive"),
                error_code="invalid_primary_verdict",
            )
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
        fail_open_reason_code=reason_code,
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
