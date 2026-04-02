from __future__ import annotations

from typing import Any, Mapping, Sequence

from .epistemic_regime import EPISTEMIC_REGIMES, PROOF_REGIMES, UNCERTAINTY_POSTURES


JUDGMENT_POSTURES = (
    "answer",
    "clarify",
    "suspend",
)

_SUSPENDING_EPISTEMIC_REGIMES = {
    "contradictoire",
    "a_verifier",
    "suspendu",
}
_SUSPENDING_PROOF_REGIMES = {
    "verification_externe_requise",
    "arbitrage_requis",
}
_SUSPENDING_UNCERTAINTY_POSTURES = {"bloquante"}
_CLARIFY_SIGNAL_FAMILIES = {
    "referent",
    "visee",
    "critere",
    "portee",
    "ancrage_de_source",
    "coherence",
}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str:
    return str(value or "").strip()


def _validate_choice(*, value: str, allowed: Sequence[str], field_name: str) -> str:
    normalized = _text(value)
    if normalized not in allowed:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _validated_user_turn_signals(user_turn_signals: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(user_turn_signals)
    if not payload or payload.get("present") is not True:
        raise ValueError("invalid_user_turn_signals")
    return payload


def _clarification_needed(user_turn_signals: Mapping[str, Any]) -> bool:
    payload = _validated_user_turn_signals(user_turn_signals)

    active_families = {
        _text(value)
        for value in _sequence(payload.get("active_signal_families"))
        if _text(value)
    } & _CLARIFY_SIGNAL_FAMILIES
    if active_families:
        return True
    if bool(payload.get("ambiguity_present")):
        return True
    if bool(payload.get("underdetermination_present")):
        return True
    return False


def _build_result(judgment_posture: str) -> dict[str, str]:
    posture = _validate_choice(
        value=judgment_posture,
        allowed=JUDGMENT_POSTURES,
        field_name="judgment_posture",
    )
    return {"judgment_posture": posture}


def build_judgment_posture(
    *,
    user_turn_signals: Mapping[str, Any] | None = None,
    epistemic_regime: str,
    proof_regime: str,
    uncertainty_posture: str,
) -> dict[str, str]:
    epistemic_value = _validate_choice(
        value=epistemic_regime,
        allowed=EPISTEMIC_REGIMES,
        field_name="epistemic_regime",
    )
    proof_value = _validate_choice(
        value=proof_regime,
        allowed=PROOF_REGIMES,
        field_name="proof_regime",
    )
    uncertainty_value = _validate_choice(
        value=uncertainty_posture,
        allowed=UNCERTAINTY_POSTURES,
        field_name="uncertainty_posture",
    )
    user_turn_signals_payload = _validated_user_turn_signals(user_turn_signals)

    if (
        epistemic_value in _SUSPENDING_EPISTEMIC_REGIMES
        or proof_value in _SUSPENDING_PROOF_REGIMES
        or uncertainty_value in _SUSPENDING_UNCERTAINTY_POSTURES
    ):
        return _build_result("suspend")

    if _clarification_needed(user_turn_signals_payload):
        return _build_result("clarify")

    return _build_result("answer")
