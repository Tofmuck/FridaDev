from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping, Sequence

from core.hermeneutic_node.doctrine.epistemic_regime import build_epistemic_regime
from core.hermeneutic_node.doctrine.judgment_posture import build_judgment_posture
from core.hermeneutic_node.doctrine.output_regime import build_output_regime
from core.hermeneutic_node.doctrine.source_conflicts import build_source_conflicts
from core.hermeneutic_node.doctrine.source_priority import build_source_priority
from core.hermeneutic_node.runtime.node_state import (
    apply_output_regime_inertia,
    build_node_state,
    validate_node_state,
)


PRIMARY_VERDICT_SCHEMA_VERSION = "v1"
_DEFAULT_SOURCE_PRIORITY = [
    ["tour_utilisateur"],
    ["temps"],
    ["memoire", "contexte_recent", "identity"],
    ["resume"],
    ["web"],
    ["stimmung"],
]
_FALLBACK_EPISTEMIC = {
    "epistemic_regime": "suspendu",
    "proof_regime": "source_explicite_requise",
    "uncertainty_posture": "bloquante",
}
_FALLBACK_JUDGMENT_POSTURE = "suspend"
_FALLBACK_OUTPUT_REGIME = {
    "discursive_regime": "meta",
    "resituation_level": "none",
    "time_reference_mode": "atemporal",
}
_FALLBACK_SOURCE_CONFLICTS: list[dict[str, Any]] = []
_FALLBACK_DEGRADED_FIELDS = [
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
]


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text(value: Any) -> str:
    return str(value or "").strip()


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


def _pipeline_directives(
    *,
    judgment_posture: str,
    source_conflicts: Sequence[Mapping[str, Any]],
    fail_open: bool,
) -> list[str]:
    directives = [f"posture_{_text(judgment_posture)}"]
    if source_conflicts:
        directives.append("source_conflict_clarify")
    if fail_open:
        directives.append("fallback_primary_verdict")
    return _stable_unique(directives)


def _build_primary_verdict(
    *,
    epistemic_payload: Mapping[str, str],
    judgment_posture: str,
    output_regime: Mapping[str, str],
    source_priority: Sequence[Sequence[str]],
    source_conflicts: Sequence[Mapping[str, Any]],
    fail_open: bool,
    state_used: bool,
    degraded_fields: Sequence[str],
) -> dict[str, Any]:
    return {
        "schema_version": PRIMARY_VERDICT_SCHEMA_VERSION,
        "epistemic_regime": str(epistemic_payload["epistemic_regime"]),
        "proof_regime": str(epistemic_payload["proof_regime"]),
        "uncertainty_posture": str(epistemic_payload["uncertainty_posture"]),
        "judgment_posture": str(judgment_posture),
        "discursive_regime": str(output_regime["discursive_regime"]),
        "resituation_level": str(output_regime["resituation_level"]),
        "time_reference_mode": str(output_regime["time_reference_mode"]),
        "source_priority": [list(rank) for rank in source_priority],
        "source_conflicts": [dict(conflict) for conflict in source_conflicts],
        "pipeline_directives_provisional": _pipeline_directives(
            judgment_posture=judgment_posture,
            source_conflicts=source_conflicts,
            fail_open=fail_open,
        ),
        "audit": {
            "fail_open": bool(fail_open),
            "state_used": bool(state_used),
            "degraded_fields": _stable_unique(list(degraded_fields)),
        },
    }


def _usable_existing_node_state(
    *,
    conversation_id: str,
    existing_node_state: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    try:
        state = validate_node_state(existing_node_state)
    except ValueError:
        return None
    if state["conversation_id"] != conversation_id:
        return None
    return state


def _fallback_result(
    *,
    conversation_id: str,
    updated_at: str,
    usable_existing_node_state: Mapping[str, Any] | None,
) -> dict[str, Any]:
    fallback_node_state = build_node_state(
        conversation_id=conversation_id,
        updated_at=updated_at,
        judgment_posture=_FALLBACK_JUDGMENT_POSTURE,
        output_regime=_FALLBACK_OUTPUT_REGIME,
        existing_node_state=usable_existing_node_state,
    )
    fallback_primary_verdict = _build_primary_verdict(
        epistemic_payload=_FALLBACK_EPISTEMIC,
        judgment_posture=_FALLBACK_JUDGMENT_POSTURE,
        output_regime=_FALLBACK_OUTPUT_REGIME,
        source_priority=_DEFAULT_SOURCE_PRIORITY,
        source_conflicts=_FALLBACK_SOURCE_CONFLICTS,
        fail_open=True,
        state_used=False,
        degraded_fields=_FALLBACK_DEGRADED_FIELDS,
    )
    return {
        "primary_verdict": fallback_primary_verdict,
        "node_state": fallback_node_state,
    }


def build_primary_node(
    *,
    conversation_id: Any,
    updated_at: Any,
    time_input: Mapping[str, Any] | None = None,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
    existing_node_state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    conversation_id_value = _validated_conversation_id(conversation_id)
    updated_at_value = _validated_updated_at(updated_at)
    usable_existing_node_state = _usable_existing_node_state(
        conversation_id=conversation_id_value,
        existing_node_state=existing_node_state,
    )

    try:
        epistemic_payload = build_epistemic_regime(
            time_input=time_input,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            recent_window_input=recent_window_input,
            user_turn_input=user_turn_input,
            user_turn_signals=user_turn_signals,
            stimmung_input=stimmung_input,
            web_input=web_input,
        )
        judgment_payload = build_judgment_posture(
            user_turn_signals=user_turn_signals,
            epistemic_regime=epistemic_payload["epistemic_regime"],
            proof_regime=epistemic_payload["proof_regime"],
            uncertainty_posture=epistemic_payload["uncertainty_posture"],
        )
        source_priority_payload = build_source_priority(
            user_turn_input=user_turn_input,
            time_input=time_input,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            web_input=web_input,
        )
        source_conflicts_payload = build_source_conflicts(
            source_priority=source_priority_payload,
            user_turn_input=user_turn_input,
            user_turn_signals=user_turn_signals,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            web_input=web_input,
        )
        current_output_regime = build_output_regime(
            judgment_posture=judgment_payload["judgment_posture"],
            user_turn_input=user_turn_input,
        )
        inertia_payload = apply_output_regime_inertia(
            conversation_id=conversation_id_value,
            judgment_posture=judgment_payload["judgment_posture"],
            output_regime=current_output_regime,
            existing_node_state=usable_existing_node_state,
        )
        stabilized_output_regime = dict(inertia_payload["output_regime"])
        next_node_state = build_node_state(
            conversation_id=conversation_id_value,
            updated_at=updated_at_value,
            judgment_posture=judgment_payload["judgment_posture"],
            output_regime=stabilized_output_regime,
            existing_node_state=usable_existing_node_state,
        )
        primary_verdict = _build_primary_verdict(
            epistemic_payload=epistemic_payload,
            judgment_posture=judgment_payload["judgment_posture"],
            output_regime=stabilized_output_regime,
            source_priority=source_priority_payload["source_priority"],
            source_conflicts=source_conflicts_payload["source_conflicts"],
            fail_open=False,
            state_used=bool(inertia_payload["state_used"]),
            degraded_fields=[],
        )
        return {
            "primary_verdict": primary_verdict,
            "node_state": next_node_state,
        }
    except Exception:
        return _fallback_result(
            conversation_id=conversation_id_value,
            updated_at=updated_at_value,
            usable_existing_node_state=usable_existing_node_state,
        )
