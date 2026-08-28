from __future__ import annotations

import json
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from . import validation_contract


MAX_CANONICAL_INPUTS_JSON_CHARS = validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS
CANONICAL_PROJECTION_VERSION = validation_contract.CANONICAL_PROJECTION_VERSION
CANONICAL_FAMILY_ORDER = validation_contract.CANONICAL_FAMILY_ORDER
_STIMMUNG_DELIVERY_STATUSES = set(validation_contract.STIMMUNG_DELIVERY_STATUSES)
_STIMMUNG_DELIVERY_REASONS = set(validation_contract.STIMMUNG_DELIVERY_REASON_CODES)
_STIMMUNG_STABILITIES = {"emerging", "stable", "volatile"}
_STIMMUNG_SHIFT_STATES = {"steady", "candidate_shift", "shifted"}


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _normalized_stimmung_projection(value: Any) -> tuple[dict[str, Any] | None, str]:
    payload = _mapping(value)
    expected_keys = {
        "schema_version",
        "present",
        "dominant_tone",
        "active_tones",
        "stability",
        "shift_state",
        "turns_considered",
    }
    if not payload:
        return None, "signal_not_present"
    if set(payload.keys()) != expected_keys:
        return None, "invalid_signal"
    if payload.get("schema_version") != canonical_stimmung_input.SCHEMA_VERSION:
        return None, "invalid_signal"

    present = payload.get("present")
    if present is False:
        valid_missing = (
            payload.get("dominant_tone") is None
            and payload.get("active_tones") == []
            and payload.get("stability") == ""
            and payload.get("shift_state") == ""
            and payload.get("turns_considered") == 0
        )
        return (None, "signal_not_present") if valid_missing else (None, "invalid_signal")
    if present is not True:
        return None, "invalid_signal"

    dominant_tone = payload.get("dominant_tone")
    active_tones = payload.get("active_tones")
    turns_considered = payload.get("turns_considered")
    if dominant_tone not in canonical_stimmung_input.ALLOWED_TONES:
        return None, "invalid_signal"
    if (
        not isinstance(active_tones, list)
        or not 1 <= len(active_tones) <= canonical_stimmung_input.ACTIVE_TONES_LIMIT
    ):
        return None, "invalid_signal"
    if isinstance(turns_considered, bool) or not isinstance(turns_considered, int):
        return None, "invalid_signal"
    if not 1 <= turns_considered <= canonical_stimmung_input.MAX_SIGNAL_TURNS:
        return None, "invalid_signal"
    if payload.get("stability") not in _STIMMUNG_STABILITIES:
        return None, "invalid_signal"
    if payload.get("shift_state") not in _STIMMUNG_SHIFT_STATES:
        return None, "invalid_signal"

    normalized_tones: list[dict[str, Any]] = []
    seen_tones: set[str] = set()
    for item in active_tones:
        tone_payload = _mapping(item)
        if set(tone_payload.keys()) != {"tone", "strength"}:
            return None, "invalid_signal"
        tone = tone_payload.get("tone")
        strength = tone_payload.get("strength")
        if tone not in canonical_stimmung_input.ALLOWED_TONES or tone in seen_tones:
            return None, "invalid_signal"
        if (
            isinstance(strength, bool)
            or not isinstance(strength, int)
            or not 1 <= strength <= 10
        ):
            return None, "invalid_signal"
        seen_tones.add(tone)
        normalized_tones.append({"tone": tone, "strength": strength})
    if dominant_tone not in seen_tones:
        return None, "invalid_signal"

    return {
        "schema_version": canonical_stimmung_input.SCHEMA_VERSION,
        "present": True,
        "dominant_tone": dominant_tone,
        "active_tones": normalized_tones,
        "stability": payload.get("stability"),
        "shift_state": payload.get("shift_state"),
        "turns_considered": turns_considered,
    }, "included"


def _envelope(
    *,
    families: Mapping[str, Any],
    omitted_families: Sequence[str],
    stimmung_status: str,
    stimmung_reason_code: str,
) -> dict[str, Any]:
    if stimmung_status not in _STIMMUNG_DELIVERY_STATUSES:
        raise ValueError("invalid_stimmung_delivery_status")
    if stimmung_reason_code not in _STIMMUNG_DELIVERY_REASONS:
        raise ValueError("invalid_stimmung_delivery_reason_code")
    return {
        "projection_version": CANONICAL_PROJECTION_VERSION,
        "stimmung_delivery": {
            "status": stimmung_status,
            "reason_code": stimmung_reason_code,
        },
        "families": dict(families),
        "omitted_families": list(omitted_families),
    }


def validate_validation_canonical_projection(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    if set(payload.keys()) != {
        "projection_version",
        "stimmung_delivery",
        "families",
        "omitted_families",
    }:
        raise ValueError("invalid_canonical_projection_structure")
    if payload.get("projection_version") != CANONICAL_PROJECTION_VERSION:
        raise ValueError("invalid_canonical_projection_version")

    delivery = _mapping(payload.get("stimmung_delivery"))
    if set(delivery.keys()) != {"status", "reason_code"}:
        raise ValueError("invalid_stimmung_delivery_structure")
    status = delivery.get("status")
    reason_code = delivery.get("reason_code")
    if status not in _STIMMUNG_DELIVERY_STATUSES:
        raise ValueError("invalid_stimmung_delivery_status")
    if reason_code not in _STIMMUNG_DELIVERY_REASONS:
        raise ValueError("invalid_stimmung_delivery_reason_code")

    families_payload = payload.get("families")
    omitted_payload = payload.get("omitted_families")
    if not isinstance(families_payload, Mapping) or not isinstance(omitted_payload, list):
        raise ValueError("invalid_canonical_projection_families")
    families = dict(families_payload)
    if any(family not in CANONICAL_FAMILY_ORDER for family in families):
        raise ValueError("invalid_canonical_projection_families")
    if any(
        not isinstance(item, str) or item not in CANONICAL_FAMILY_ORDER
        for item in omitted_payload
    ):
        raise ValueError("invalid_canonical_projection_families")
    if len(set(omitted_payload)) != len(omitted_payload):
        raise ValueError("invalid_canonical_projection_families")
    if list(omitted_payload) != sorted(omitted_payload, key=CANONICAL_FAMILY_ORDER.index):
        raise ValueError("invalid_canonical_projection_family_order")
    if set(families) & set(omitted_payload):
        raise ValueError("invalid_canonical_projection_families")
    if any(not isinstance(family_payload, Mapping) for family_payload in families.values()):
        raise ValueError("invalid_canonical_projection_families")

    if status == "full":
        stimmung, stimmung_reason = _normalized_stimmung_projection(
            families.get("stimmung_input")
        )
        if reason_code != "included" or stimmung_reason != "included" or stimmung is None:
            raise ValueError("inconsistent_stimmung_delivery")
        families["stimmung_input"] = stimmung
    elif (
        reason_code == "included"
        or "stimmung_input" in families
        or (
            reason_code in {"invalid_signal", "contract_budget_exceeded"}
            and "stimmung_input" not in omitted_payload
        )
    ):
        raise ValueError("inconsistent_stimmung_delivery")

    return _envelope(
        families=families,
        omitted_families=omitted_payload,
        stimmung_status=status,
        stimmung_reason_code=reason_code,
    )


def project_validation_canonical_inputs(
    canonical_inputs: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Project whole canonical families into Validation's fixed 700-char budget."""

    source = _mapping(canonical_inputs)
    present_families = [
        family
        for family in CANONICAL_FAMILY_ORDER
        if bool(_mapping(source.get(family)))
    ]
    selected: dict[str, Any] = {}
    omitted = list(present_families)
    stimmung, stimmung_reason = _normalized_stimmung_projection(source.get("stimmung_input"))
    stimmung_status = "full" if stimmung is not None else "absent"

    if stimmung is not None:
        selected["stimmung_input"] = stimmung
        omitted = [family for family in omitted if family != "stimmung_input"]
        required = _envelope(
            families=selected,
            omitted_families=omitted,
            stimmung_status="full",
            stimmung_reason_code="included",
        )
        if len(_compact_json(required)) > MAX_CANONICAL_INPUTS_JSON_CHARS:
            selected.clear()
            if "stimmung_input" not in omitted:
                omitted.append("stimmung_input")
                omitted.sort(key=CANONICAL_FAMILY_ORDER.index)
            stimmung_status = "absent"
            stimmung_reason = "contract_budget_exceeded"

    for family in CANONICAL_FAMILY_ORDER:
        if family == "stimmung_input" or family not in omitted:
            continue
        family_payload = _mapping(source.get(family))
        if not family_payload:
            continue
        candidate_selected = {**selected, family: dict(family_payload)}
        candidate_omitted = [item for item in omitted if item != family]
        candidate = _envelope(
            families=candidate_selected,
            omitted_families=candidate_omitted,
            stimmung_status=stimmung_status,
            stimmung_reason_code=stimmung_reason,
        )
        if len(_compact_json(candidate)) <= MAX_CANONICAL_INPUTS_JSON_CHARS:
            selected = candidate_selected
            omitted = candidate_omitted

    projection = validate_validation_canonical_projection(
        _envelope(
            families=selected,
            omitted_families=omitted,
            stimmung_status=stimmung_status,
            stimmung_reason_code=stimmung_reason,
        )
    )
    material = _compact_json(projection)
    if len(material) > MAX_CANONICAL_INPUTS_JSON_CHARS:
        raise ValueError("canonical_projection_budget_exceeded")
    metadata = {
        "canonical_projection_version": CANONICAL_PROJECTION_VERSION,
        "canonical_projection_chars": len(material),
        "canonical_projection_budget_chars": MAX_CANONICAL_INPUTS_JSON_CHARS,
        "canonical_projection_included_families": list(selected.keys()),
        "canonical_projection_omitted_families": list(omitted),
        "stimmung_delivery_status": stimmung_status,
        "stimmung_delivery_reason_code": stimmung_reason,
        "raw_content_included": False,
    }
    return material, validation_contract.validate_canonical_projection_metadata(metadata)
