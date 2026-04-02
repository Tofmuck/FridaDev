from __future__ import annotations

from typing import Any, Mapping, Sequence

from .judgment_posture import JUDGMENT_POSTURES


DISCURSIVE_REGIMES = (
    "meta",
    "simple",
    "cadre",
    "comparatif",
    "continuite",
)
RESITUATION_LEVELS = (
    "none",
    "light",
    "explicit",
    "strong",
)
TIME_REFERENCE_MODES = (
    "immediate_now",
    "dialogue_relative",
    "anchored_past",
    "prospective",
    "atemporal",
)

_GESTURES = (
    "exposition",
    "interrogation",
    "orientation",
    "positionnement",
    "regulation",
    "adresse_relationnelle",
)
_TEMPORAL_SCOPES = (
    "atemporale",
    "immediate",
    "actuelle",
    "passee",
    "prospective",
)
_TEMPORAL_ANCHORS = (
    "now",
    "non_ancre",
    "dialogue_trace",
    "dialogue_resume",
    "historique_externe",
    "projection",
    "mixte",
)
_DIALOGIC_PROVENANCES = {"dialogue_trace", "dialogue_resume"}
_DIALOGIC_ANCHORS = {"dialogue_trace", "dialogue_resume"}


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _validate_choice(*, value: str, allowed: Sequence[str], field_name: str) -> str:
    normalized = _text(value)
    if normalized not in allowed:
        raise ValueError(f"invalid_{field_name}")
    return normalized


def _validated_user_turn_input(user_turn_input: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(user_turn_input)
    if _text(payload.get("schema_version")) != "v1":
        raise ValueError("invalid_user_turn_input")

    _validate_choice(
        value=payload.get("geste_dialogique_dominant"),
        allowed=_GESTURES,
        field_name="user_turn_input",
    )

    regime = _mapping(payload.get("regime_probatoire"))
    qualification = _mapping(payload.get("qualification_temporelle"))
    if not regime or not qualification:
        raise ValueError("invalid_user_turn_input")

    provenances = regime.get("provenances")
    if not isinstance(provenances, Sequence) or isinstance(provenances, (str, bytes, bytearray)):
        raise ValueError("invalid_user_turn_input")

    _validate_choice(
        value=qualification.get("portee_temporelle"),
        allowed=_TEMPORAL_SCOPES,
        field_name="user_turn_input",
    )
    _validate_choice(
        value=qualification.get("ancrage_temporel"),
        allowed=_TEMPORAL_ANCHORS,
        field_name="user_turn_input",
    )
    return payload


def _gesture(user_turn_input: Mapping[str, Any]) -> str:
    return _text(user_turn_input.get("geste_dialogique_dominant"))


def _regime_probatoire(user_turn_input: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(user_turn_input.get("regime_probatoire"))


def _qualification_temporelle(user_turn_input: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(user_turn_input.get("qualification_temporelle"))


def _required_provenances(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _regime_probatoire(user_turn_input)
    return {
        _text(value)
        for value in _sequence(regime.get("provenances"))
        if _text(value)
    }


def _temporal_scope(user_turn_input: Mapping[str, Any]) -> str:
    return _text(_qualification_temporelle(user_turn_input).get("portee_temporelle"))


def _temporal_anchor(user_turn_input: Mapping[str, Any]) -> str:
    return _text(_qualification_temporelle(user_turn_input).get("ancrage_temporel"))


def _is_dialogic_turn(user_turn_input: Mapping[str, Any]) -> bool:
    if _required_provenances(user_turn_input) & _DIALOGIC_PROVENANCES:
        return True
    return _temporal_anchor(user_turn_input) in _DIALOGIC_ANCHORS


def _discursive_regime(
    *,
    judgment_posture: str,
    user_turn_input: Mapping[str, Any],
) -> str:
    if judgment_posture != "answer":
        return "meta"
    if _gesture(user_turn_input) == "regulation":
        return "cadre"
    if _is_dialogic_turn(user_turn_input):
        return "continuite"
    return "simple"


def _resituation_level(user_turn_input: Mapping[str, Any]) -> str:
    if _gesture(user_turn_input) == "regulation":
        return "explicit"
    if _is_dialogic_turn(user_turn_input):
        return "light"
    return "none"


def _time_reference_mode(user_turn_input: Mapping[str, Any]) -> str:
    temporal_scope = _temporal_scope(user_turn_input)
    temporal_anchor = _temporal_anchor(user_turn_input)

    if temporal_scope == "prospective" or temporal_anchor == "projection":
        return "prospective"
    if temporal_anchor == "now" and temporal_scope in {"immediate", "actuelle"}:
        return "immediate_now"
    if _is_dialogic_turn(user_turn_input):
        return "dialogue_relative"
    if temporal_scope == "passee" or temporal_anchor == "historique_externe":
        return "anchored_past"
    return "atemporal"


def _build_result(
    *,
    discursive_regime: str,
    resituation_level: str,
    time_reference_mode: str,
) -> dict[str, str]:
    result = {
        "discursive_regime": _validate_choice(
            value=discursive_regime,
            allowed=DISCURSIVE_REGIMES,
            field_name="discursive_regime",
        ),
        "resituation_level": _validate_choice(
            value=resituation_level,
            allowed=RESITUATION_LEVELS,
            field_name="resituation_level",
        ),
        "time_reference_mode": _validate_choice(
            value=time_reference_mode,
            allowed=TIME_REFERENCE_MODES,
            field_name="time_reference_mode",
        ),
    }
    return result


def build_output_regime(
    *,
    judgment_posture: str,
    user_turn_input: Mapping[str, Any] | None,
) -> dict[str, str]:
    posture = _validate_choice(
        value=judgment_posture,
        allowed=JUDGMENT_POSTURES,
        field_name="judgment_posture",
    )
    user_turn_payload = _validated_user_turn_input(user_turn_input)

    return _build_result(
        discursive_regime=_discursive_regime(
            judgment_posture=posture,
            user_turn_input=user_turn_payload,
        ),
        resituation_level=_resituation_level(user_turn_payload),
        time_reference_mode=_time_reference_mode(user_turn_payload),
    )
