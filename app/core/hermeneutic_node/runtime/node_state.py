from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.doctrine.judgment_posture import JUDGMENT_POSTURES
from core.hermeneutic_node.doctrine.output_regime import (
    DISCURSIVE_REGIMES,
    RESITUATION_LEVELS,
    TIME_REFERENCE_MODES,
)


NODE_STATE_SCHEMA_VERSION = "v1"
_NODE_STATE_REQUIRED_FIELDS = (
    "schema_version",
    "conversation_id",
    "updated_at",
    "last_judgment_posture",
)
_NODE_STATE_OPTIONAL_FIELDS = ("last_answer_output_regime",)
_NODE_STATE_ALLOWED_FIELDS = set(_NODE_STATE_REQUIRED_FIELDS) | set(_NODE_STATE_OPTIONAL_FIELDS)
_OUTPUT_REGIME_FIELDS = (
    "discursive_regime",
    "resituation_level",
    "time_reference_mode",
)
_INERTIA_FALLBACK_REGIME = {
    "discursive_regime": "simple",
    "resituation_level": "none",
    "time_reference_mode": "atemporal",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value: Any) -> str:
    return str(value or "").strip()


def _validate_choice(*, value: str, allowed: Sequence[str], field_name: str) -> str:
    normalized = _text(value)
    if normalized not in allowed:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _validated_conversation_id(conversation_id: Any) -> str:
    value = _text(conversation_id)
    if not value:
        raise ValueError("invalid_conversation_id")
    return value


def _validated_updated_at(updated_at: Any) -> str:
    value = _text(updated_at)
    if not value:
        raise ValueError("invalid_updated_at")
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_updated_at") from exc
    return value


def _validated_judgment_posture(judgment_posture: Any) -> str:
    return _validate_choice(
        value=judgment_posture,
        allowed=JUDGMENT_POSTURES,
        field_name="judgment_posture",
    )


def _validated_output_regime(
    output_regime: Mapping[str, Any] | None,
    *,
    allow_meta: bool,
) -> dict[str, str]:
    payload = _mapping(output_regime)
    if set(payload) != set(_OUTPUT_REGIME_FIELDS):
        raise ValueError("invalid_output_regime")

    result = {
        "discursive_regime": _validate_choice(
            value=payload.get("discursive_regime"),
            allowed=DISCURSIVE_REGIMES,
            field_name="output_regime",
        ),
        "resituation_level": _validate_choice(
            value=payload.get("resituation_level"),
            allowed=RESITUATION_LEVELS,
            field_name="output_regime",
        ),
        "time_reference_mode": _validate_choice(
            value=payload.get("time_reference_mode"),
            allowed=TIME_REFERENCE_MODES,
            field_name="output_regime",
        ),
    }
    if not allow_meta and result["discursive_regime"] == "meta":
        raise ValueError("invalid_output_regime")
    return result


def _validated_current_output_regime(
    *,
    judgment_posture: str,
    output_regime: Mapping[str, Any] | None,
) -> dict[str, str]:
    allow_meta = judgment_posture != "answer"
    result = _validated_output_regime(
        output_regime,
        allow_meta=allow_meta,
    )
    if allow_meta and result["discursive_regime"] != "meta":
        raise ValueError("invalid_output_regime")
    return result


def _validated_node_state(
    node_state: Mapping[str, Any] | None,
    *,
    field_name: str,
) -> dict[str, Any] | None:
    if node_state is None:
        return None

    try:
        payload = _mapping(node_state)
        if not payload:
            raise ValueError("invalid")
        if set(payload) - _NODE_STATE_ALLOWED_FIELDS:
            raise ValueError("invalid")
        if not set(_NODE_STATE_REQUIRED_FIELDS).issubset(set(payload)):
            raise ValueError("invalid")
        if _text(payload.get("schema_version")) != NODE_STATE_SCHEMA_VERSION:
            raise ValueError("invalid")

        conversation_id = _validated_conversation_id(payload.get("conversation_id"))
        updated_at = _validated_updated_at(payload.get("updated_at"))
        last_judgment_posture = _validated_judgment_posture(payload.get("last_judgment_posture"))

        if "last_answer_output_regime" not in payload or payload.get("last_answer_output_regime") is None:
            last_answer_output_regime = None
        else:
            last_answer_output_regime = _validated_output_regime(
                payload.get("last_answer_output_regime"),
                allow_meta=False,
            )

        if last_judgment_posture == "answer" and last_answer_output_regime is None:
            raise ValueError("invalid")

        return {
            "schema_version": NODE_STATE_SCHEMA_VERSION,
            "conversation_id": conversation_id,
            "updated_at": updated_at,
            "last_judgment_posture": last_judgment_posture,
            "last_answer_output_regime": last_answer_output_regime,
        }
    except ValueError as exc:
        raise ValueError(f"invalid_{field_name}") from exc


def validate_node_state(node_state: Mapping[str, Any] | None) -> dict[str, Any]:
    validated = _validated_node_state(node_state, field_name="node_state")
    if validated is None:
        raise ValueError("invalid_node_state")
    return validated


def _is_inertia_candidate(output_regime: Mapping[str, str]) -> bool:
    return dict(output_regime) == _INERTIA_FALLBACK_REGIME


def apply_output_regime_inertia(
    *,
    conversation_id: Any,
    judgment_posture: str,
    output_regime: Mapping[str, Any] | None,
    existing_node_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    conversation_id_value = _validated_conversation_id(conversation_id)
    posture = _validated_judgment_posture(judgment_posture)
    current_output_regime = _validated_current_output_regime(
        judgment_posture=posture,
        output_regime=output_regime,
    )
    existing_state = _validated_node_state(existing_node_state, field_name="existing_node_state")

    if posture != "answer":
        return {
            "output_regime": current_output_regime,
            "state_used": False,
        }
    if existing_state is not None and existing_state["conversation_id"] != conversation_id_value:
        raise ValueError("invalid_existing_node_state")
    if existing_state is None or existing_state["last_answer_output_regime"] is None:
        return {
            "output_regime": current_output_regime,
            "state_used": False,
        }
    if not _is_inertia_candidate(current_output_regime):
        return {
            "output_regime": current_output_regime,
            "state_used": False,
        }

    previous_output_regime = dict(existing_state["last_answer_output_regime"])
    if previous_output_regime == current_output_regime:
        return {
            "output_regime": current_output_regime,
            "state_used": False,
        }
    return {
        "output_regime": previous_output_regime,
        "state_used": True,
    }


def build_node_state(
    *,
    conversation_id: Any,
    updated_at: Any,
    judgment_posture: str,
    output_regime: Mapping[str, Any] | None,
    existing_node_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    conversation_id_value = _validated_conversation_id(conversation_id)
    updated_at_value = _validated_updated_at(updated_at)
    posture = _validated_judgment_posture(judgment_posture)
    current_output_regime = _validated_current_output_regime(
        judgment_posture=posture,
        output_regime=output_regime,
    )
    existing_state = _validated_node_state(existing_node_state, field_name="existing_node_state")

    if existing_state is not None and existing_state["conversation_id"] != conversation_id_value:
        raise ValueError("invalid_existing_node_state")

    if posture == "answer":
        last_answer_output_regime = dict(current_output_regime)
    elif existing_state is not None:
        last_answer_output_regime = existing_state["last_answer_output_regime"]
    else:
        last_answer_output_regime = None

    return {
        "schema_version": NODE_STATE_SCHEMA_VERSION,
        "conversation_id": conversation_id_value,
        "updated_at": updated_at_value,
        "last_judgment_posture": posture,
        "last_answer_output_regime": last_answer_output_regime,
    }
