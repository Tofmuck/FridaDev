from __future__ import annotations

from typing import Any, Mapping, Sequence


SOURCE_FAMILIES = (
    "tour_utilisateur",
    "temps",
    "memoire",
    "contexte_recent",
    "identity",
    "resume",
    "web",
    "stimmung",
)

_SOURCE_ORDER = {family: index for index, family in enumerate(SOURCE_FAMILIES)}
_BASE_RANKS = {
    "tour_utilisateur": 0,
    "temps": 1,
    "memoire": 3,
    "contexte_recent": 3,
    "identity": 3,
    "resume": 4,
    "web": 5,
    "stimmung": 6,
}
_CURRENT_FACT_TEMPORAL_SCOPES = {"immediate", "actuelle", "prospective"}
_STATIC_PRIORITY_GESTURES = {"adresse_relationnelle"}
_RECENT_CONTEXT_GESTURES = {"regulation"}


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


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validated_user_turn_input(user_turn_input: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(user_turn_input)
    if _text(payload.get("schema_version")) != "v1":
        raise ValueError("invalid_user_turn_input")
    if not _text(payload.get("geste_dialogique_dominant")):
        raise ValueError("invalid_user_turn_input")
    if not _mapping(payload.get("regime_probatoire")):
        raise ValueError("invalid_user_turn_input")
    if not _mapping(payload.get("qualification_temporelle")):
        raise ValueError("invalid_user_turn_input")
    return payload


def _validated_time_input(time_input: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(time_input)
    if _text(payload.get("schema_version")) != "v1":
        raise ValueError("invalid_time_input")
    if not _text(payload.get("now_local_iso")):
        raise ValueError("invalid_time_input")
    if not _text(payload.get("timezone")):
        raise ValueError("invalid_time_input")
    return payload


def _gesture(user_turn_input: Mapping[str, Any]) -> str:
    return _text(user_turn_input.get("geste_dialogique_dominant"))


def _regime_probatoire(user_turn_input: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(user_turn_input.get("regime_probatoire"))


def _qualification_temporelle(user_turn_input: Mapping[str, Any]) -> Mapping[str, Any]:
    return _mapping(user_turn_input.get("qualification_temporelle"))


def _required_provenances(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _regime_probatoire(user_turn_input)
    return {_text(value) for value in _sequence(regime.get("provenances")) if _text(value)}


def _requested_proof_types(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _regime_probatoire(user_turn_input)
    return {_text(value) for value in _sequence(regime.get("types_de_preuve_attendus")) if _text(value)}


def _temporal_scope(user_turn_input: Mapping[str, Any]) -> str:
    return _text(_qualification_temporelle(user_turn_input).get("portee_temporelle"))


def _temporal_anchor(user_turn_input: Mapping[str, Any]) -> str:
    return _text(_qualification_temporelle(user_turn_input).get("ancrage_temporel"))


def _memory_support_available(
    *,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
) -> bool:
    arbitration = _mapping(memory_arbitration)
    if arbitration:
        if _text(arbitration.get("status")) == "error":
            return False
        return _int_or_zero(arbitration.get("kept_count")) > 0
    return _int_or_zero(_mapping(memory_retrieved).get("retrieved_count")) > 0


def _summary_available(summary_input: Mapping[str, Any]) -> bool:
    return _text(summary_input.get("status")) == "available" and bool(_mapping(summary_input.get("summary")))


def _recent_context_available(recent_context_input: Mapping[str, Any]) -> bool:
    return len(_sequence(recent_context_input.get("messages"))) > 0


def _identity_static_present(identity_input: Mapping[str, Any]) -> bool:
    for side_name in ("frida", "user"):
        side = _mapping(identity_input.get(side_name))
        static_block = _mapping(side.get("static"))
        if _text(static_block.get("content")):
            return True
    return False


def _identity_mutable_present(identity_input: Mapping[str, Any]) -> bool:
    for side_name in ("frida", "user"):
        side = _mapping(identity_input.get(side_name))
        mutable_block = _mapping(side.get("mutable"))
        if _text(mutable_block.get("content")):
            return True
    return False


def _web_priority_requested(
    *,
    user_turn_input: Mapping[str, Any],
) -> bool:
    provenances = _required_provenances(user_turn_input)
    proof_types = _requested_proof_types(user_turn_input)
    temporal_scope = _temporal_scope(user_turn_input)

    if "web" in provenances:
        return True
    if "scientifique" in proof_types:
        return True
    if "factuelle" in proof_types and temporal_scope in _CURRENT_FACT_TEMPORAL_SCOPES:
        return True
    return False


def _promote(rank_map: dict[str, int], family: str, target_rank: int) -> None:
    rank_map[family] = min(rank_map[family], target_rank)


def _group_priority(rank_map: Mapping[str, int]) -> list[list[str]]:
    ordered_families = sorted(
        SOURCE_FAMILIES,
        key=lambda family: (int(rank_map[family]), _SOURCE_ORDER[family]),
    )
    grouped: list[list[str]] = []
    previous_rank: int | None = None
    for family in ordered_families:
        family_rank = int(rank_map[family])
        if previous_rank != family_rank:
            grouped.append([family])
            previous_rank = family_rank
        else:
            grouped[-1].append(family)
    return grouped


def build_source_priority(
    *,
    user_turn_input: Mapping[str, Any] | None,
    time_input: Mapping[str, Any] | None,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, list[list[str]]]:
    user_turn_payload = _validated_user_turn_input(user_turn_input)
    _validated_time_input(time_input)

    memory_retrieved_payload = _mapping(memory_retrieved)
    memory_arbitration_payload = _mapping(memory_arbitration)
    summary_payload = _mapping(summary_input)
    identity_payload = _mapping(identity_input)
    recent_context_payload = _mapping(recent_context_input)
    rank_map = dict(_BASE_RANKS)

    if _web_priority_requested(user_turn_input=user_turn_payload):
        _promote(rank_map, "web", 2)

    if (
        (
            "dialogue_trace" in _required_provenances(user_turn_payload)
            or _temporal_anchor(user_turn_payload) == "dialogue_trace"
        )
        and _memory_support_available(
            memory_retrieved=memory_retrieved_payload,
            memory_arbitration=memory_arbitration_payload,
        )
    ):
        _promote(rank_map, "memoire", 2)

    if _gesture(user_turn_payload) in _RECENT_CONTEXT_GESTURES and _recent_context_available(recent_context_payload):
        _promote(rank_map, "contexte_recent", 2)

    if _gesture(user_turn_payload) in _STATIC_PRIORITY_GESTURES and _identity_static_present(identity_payload):
        _promote(rank_map, "identity", 2)
    elif _identity_mutable_present(identity_payload):
        rank_map["identity"] = max(rank_map["identity"], _BASE_RANKS["identity"])

    if (
        (
            "dialogue_resume" in _required_provenances(user_turn_payload)
            or _temporal_anchor(user_turn_payload) == "dialogue_resume"
        )
        and _summary_available(summary_payload)
        and not _memory_support_available(
            memory_retrieved=memory_retrieved_payload,
            memory_arbitration=memory_arbitration_payload,
        )
        and not _recent_context_available(recent_context_payload)
    ):
        _promote(rank_map, "resume", 3)

    return {"source_priority": _group_priority(rank_map)}
