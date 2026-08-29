from __future__ import annotations

import json
from typing import Any, Mapping

from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from . import validation_contract
from . import validation_canonical_family_projection


MAX_CANONICAL_INPUTS_JSON_CHARS = validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS
CANONICAL_PROJECTION_VERSION = validation_contract.CANONICAL_PROJECTION_VERSION
CANONICAL_FAMILY_ORDER = validation_contract.CANONICAL_FAMILY_ORDER
_STIMMUNG_DELIVERY_STATUSES = set(validation_contract.STIMMUNG_DELIVERY_STATUSES)
_STIMMUNG_DELIVERY_REASONS = set(validation_contract.STIMMUNG_DELIVERY_REASON_CODES)
_STIMMUNG_STABILITIES = {"emerging", "stable", "volatile"}
_STIMMUNG_SHIFT_STATES = {"steady", "candidate_shift", "shifted"}
_FAMILY_DISPOSITIONS = set(validation_contract.CANONICAL_FAMILY_DISPOSITIONS)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


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
    family_dispositions: Mapping[str, str],
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
        "family_dispositions": dict(family_dispositions),
        "families": dict(families),
    }


def validate_validation_canonical_projection(value: Any) -> dict[str, Any]:
    payload = _mapping(value)
    if set(payload.keys()) != {
        "projection_version",
        "stimmung_delivery",
        "family_dispositions",
        "families",
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
    dispositions_payload = payload.get("family_dispositions")
    if not isinstance(families_payload, Mapping) or not isinstance(dispositions_payload, Mapping):
        raise ValueError("invalid_canonical_projection_families")
    families = dict(families_payload)
    dispositions = dict(dispositions_payload)
    if any(family not in CANONICAL_FAMILY_ORDER for family in families):
        raise ValueError("invalid_canonical_projection_families")
    if set(dispositions) != set(CANONICAL_FAMILY_ORDER):
        raise ValueError("invalid_canonical_projection_families")
    if any(disposition not in _FAMILY_DISPOSITIONS for disposition in dispositions.values()):
        raise ValueError("invalid_canonical_projection_families")
    for family in CANONICAL_FAMILY_ORDER:
        included = dispositions[family] == "included"
        if included != (family in families):
            raise ValueError("inconsistent_canonical_projection_family")
        if family in families and family != "stimmung_input":
            families[family] = validation_canonical_family_projection.validate_projected_family(
                family,
                families[family],
            )

    if status == "full":
        stimmung, stimmung_reason = _normalized_stimmung_projection(
            families.get("stimmung_input")
        )
        if reason_code != "included" or stimmung_reason != "included" or stimmung is None:
            raise ValueError("inconsistent_stimmung_delivery")
        if dispositions.get("stimmung_input") != "included":
            raise ValueError("inconsistent_stimmung_delivery")
        families["stimmung_input"] = stimmung
    else:
        expected_disposition = {
            "signal_not_present": "no_data",
            "invalid_signal": "invalid_input",
            "contract_budget_exceeded": "contract_budget_exceeded",
        }.get(str(reason_code))
        if (
            reason_code == "included"
            or "stimmung_input" in families
            or dispositions.get("stimmung_input") != expected_disposition
        ):
            raise ValueError("inconsistent_stimmung_delivery")

    return _envelope(
        families=families,
        family_dispositions={family: dispositions[family] for family in CANONICAL_FAMILY_ORDER},
        stimmung_status=status,
        stimmung_reason_code=reason_code,
    )


def project_validation_canonical_inputs(
    canonical_inputs: Mapping[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Build Validation's compact, whole-family v2 projection."""

    source = _mapping(canonical_inputs)
    selected: dict[str, Any] = {}
    dispositions: dict[str, str] = {}
    stimmung, stimmung_reason = _normalized_stimmung_projection(source.get("stimmung_input"))
    stimmung_status = "full" if stimmung is not None else "absent"

    if stimmung is not None:
        selected["stimmung_input"] = stimmung
        dispositions["stimmung_input"] = "included"
    elif stimmung_reason == "invalid_signal":
        dispositions["stimmung_input"] = "invalid_input"
    else:
        dispositions["stimmung_input"] = "no_data"

    for family in CANONICAL_FAMILY_ORDER:
        if family == "stimmung_input":
            continue
        projected, disposition = validation_canonical_family_projection.project_family(
            family,
            source.get(family),
        )
        dispositions[family] = disposition
        if projected is not None:
            selected[family] = projected

    selected = {
        family: selected[family]
        for family in CANONICAL_FAMILY_ORDER
        if family in selected
    }
    dispositions = {
        family: dispositions[family]
        for family in CANONICAL_FAMILY_ORDER
    }

    projection = validate_validation_canonical_projection(
        _envelope(
            families=selected,
            family_dispositions=dispositions,
            stimmung_status=stimmung_status,
            stimmung_reason_code=stimmung_reason,
        )
    )
    material = _compact_json(projection)
    if len(material) > MAX_CANONICAL_INPUTS_JSON_CHARS:
        dispositions = {
            family: (
                "contract_budget_exceeded"
                if disposition == "included"
                else disposition
            )
            for family, disposition in dispositions.items()
        }
        if stimmung_status == "full":
            stimmung_status = "absent"
            stimmung_reason = "contract_budget_exceeded"
        projection = validate_validation_canonical_projection(
            _envelope(
                families={},
                family_dispositions=dispositions,
                stimmung_status=stimmung_status,
                stimmung_reason_code=stimmung_reason,
            )
        )
        material = _compact_json(projection)
        if len(material) > MAX_CANONICAL_INPUTS_JSON_CHARS:
            raise ValueError("canonical_projection_budget_exceeded")
    included = [
        family for family in CANONICAL_FAMILY_ORDER
        if projection["family_dispositions"][family] == "included"
    ]
    omitted = [family for family in CANONICAL_FAMILY_ORDER if family not in included]
    disposition_lists = {
        disposition: [
            family for family in CANONICAL_FAMILY_ORDER
            if projection["family_dispositions"][family] == disposition
        ]
        for disposition in validation_contract.CANONICAL_FAMILY_DISPOSITIONS
    }
    metadata = {
        "canonical_projection_version": CANONICAL_PROJECTION_VERSION,
        "canonical_projection_contract_status": "current_v2",
        "canonical_projection_chars": len(material),
        "canonical_projection_budget_chars": MAX_CANONICAL_INPUTS_JSON_CHARS,
        "canonical_projection_included_families": included,
        "canonical_projection_omitted_families": list(omitted),
        "canonical_projection_no_data_families": disposition_lists["no_data"],
        "canonical_projection_redundant_families": disposition_lists["redundant_elsewhere"],
        "canonical_projection_optional_families": disposition_lists["optional_not_requested"],
        "canonical_projection_invalid_families": disposition_lists["invalid_input"],
        "canonical_projection_budget_exceeded_families": disposition_lists[
            "contract_budget_exceeded"
        ],
        "stimmung_delivery_status": stimmung_status,
        "stimmung_delivery_reason_code": stimmung_reason,
        "raw_content_included": False,
    }
    return material, validation_contract.validate_canonical_projection_metadata(metadata)
