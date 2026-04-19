from __future__ import annotations

from typing import Any, Mapping, Sequence

from .source_priority import SOURCE_FAMILIES


CONFLICT_TYPES = (
    "conflit_factuel",
    "conflit_de_continuite_dialogique",
    "conflit_d_ancrage_de_source",
    "conflit_de_validite_temporelle",
)
CONFLICT_ISSUE = "review_required"
_CONTENT_SOURCE_FAMILIES = (
    "memoire",
    "contexte_recent",
    "identity",
    "resume",
    "web",
)
_SOURCE_ORDER = {family: index for index, family in enumerate(_CONTENT_SOURCE_FAMILIES)}
_FALLBACK_ANCHOR_FAMILIES = {"memoire", "resume", "web"}
_ANCHOR_SIGNAL_FAMILY = "ancrage_de_source"
_PROVENANCE_TO_SOURCE = {
    "dialogue_trace": "memoire",
    "dialogue_resume": "resume",
    "web": "web",
}


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


def _validated_source_priority(source_priority: Mapping[str, Any] | None) -> dict[str, int]:
    payload = _mapping(source_priority)
    seen: set[str] = set()
    rank_map: dict[str, int] = {}
    for rank_index, rank in enumerate(_sequence(payload.get("source_priority"))):
        families = _sequence(rank)
        if not families:
            raise ValueError("invalid_source_priority")
        for family_value in families:
            family = _text(family_value)
            if family not in SOURCE_FAMILIES or family in seen:
                raise ValueError("invalid_source_priority")
            seen.add(family)
            rank_map[family] = rank_index
    if seen != set(SOURCE_FAMILIES):
        raise ValueError("invalid_source_priority")
    return rank_map


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


def _validated_user_turn_signals(user_turn_signals: Mapping[str, Any] | None) -> Mapping[str, Any]:
    payload = _mapping(user_turn_signals)
    if not payload or payload.get("present") is not True:
        raise ValueError("invalid_user_turn_signals")
    if not isinstance(payload.get("active_signal_families"), Sequence) or isinstance(
        payload.get("active_signal_families"), (str, bytes, bytearray)
    ):
        raise ValueError("invalid_user_turn_signals")
    return payload


def _required_provenances(user_turn_input: Mapping[str, Any]) -> set[str]:
    regime = _mapping(user_turn_input.get("regime_probatoire"))
    return {_text(value) for value in _sequence(regime.get("provenances")) if _text(value)}


def _gesture(user_turn_input: Mapping[str, Any]) -> str:
    return _text(user_turn_input.get("geste_dialogique_dominant"))


def _memory_available(
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


def _identity_available(identity_input: Mapping[str, Any]) -> bool:
    for side_name in ("frida", "user"):
        side = _mapping(identity_input.get(side_name))
        static_block = _mapping(side.get("static"))
        if _text(static_block.get("content")):
            return True
        mutable_block = _mapping(side.get("mutable"))
        if _text(mutable_block.get("content")):
            return True
    return False


def _identity_static_available(identity_input: Mapping[str, Any]) -> bool:
    for side_name in ("frida", "user"):
        side = _mapping(identity_input.get(side_name))
        static_block = _mapping(side.get("static"))
        if _text(static_block.get("content")):
            return True
    return False


def _web_available(web_input: Mapping[str, Any]) -> bool:
    return _text(web_input.get("status")) == "ok" and _int_or_zero(web_input.get("results_count")) > 0


def _available_source_families(
    *,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
    summary_input: Mapping[str, Any],
    identity_input: Mapping[str, Any],
    recent_context_input: Mapping[str, Any],
    web_input: Mapping[str, Any],
) -> set[str]:
    available: set[str] = set()
    if _memory_available(memory_retrieved=memory_retrieved, memory_arbitration=memory_arbitration):
        available.add("memoire")
    if _summary_available(summary_input):
        available.add("resume")
    if _identity_available(identity_input):
        available.add("identity")
    if _recent_context_available(recent_context_input):
        available.add("contexte_recent")
    if _web_available(web_input):
        available.add("web")
    return available


def _anchor_candidate_families(
    *,
    user_turn_input: Mapping[str, Any],
    available_families: set[str],
    identity_input: Mapping[str, Any],
) -> set[str]:
    candidates = {
        family
        for provenance, family in _PROVENANCE_TO_SOURCE.items()
        if provenance in _required_provenances(user_turn_input) and family in available_families
    }
    if _gesture(user_turn_input) == "adresse_relationnelle" and _identity_static_available(identity_input):
        candidates.add("identity")
    if _gesture(user_turn_input) == "regulation" and "contexte_recent" in available_families:
        candidates.add("contexte_recent")
    if len(candidates) < 2:
        candidates |= available_families & _FALLBACK_ANCHOR_FAMILIES
    return candidates


def _best_ranked_families(
    *,
    rank_map: Mapping[str, int],
    families: set[str],
) -> list[str]:
    if not families:
        return []
    best_rank = min(rank_map[family] for family in families)
    return [
        family
        for family in _CONTENT_SOURCE_FAMILIES
        if family in families and rank_map[family] == best_rank
    ]


def _stable_unique_sources(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for family in sorted(values, key=lambda family: _SOURCE_ORDER[family]):
        if family not in seen:
            seen.add(family)
            ordered.append(family)
    return ordered


def _build_conflict(*, conflict_type: str, sources: Sequence[str]) -> dict[str, Any]:
    if conflict_type not in CONFLICT_TYPES:
        raise ValueError("invalid_conflict_type")
    stable_sources = _stable_unique_sources(sources)
    if len(stable_sources) < 2:
        raise ValueError("invalid_conflict_sources")
    return {
        "conflict_type": conflict_type,
        "sources": stable_sources,
        "issue": CONFLICT_ISSUE,
    }


def _anchor_conflict(
    *,
    rank_map: Mapping[str, int],
    user_turn_input: Mapping[str, Any],
    user_turn_signals: Mapping[str, Any],
    available_families: set[str],
    identity_input: Mapping[str, Any],
) -> dict[str, Any] | None:
    active_families = {
        _text(value)
        for value in _sequence(user_turn_signals.get("active_signal_families"))
        if _text(value)
    }
    if _ANCHOR_SIGNAL_FAMILY not in active_families:
        return None

    candidates = _anchor_candidate_families(
        user_turn_input=user_turn_input,
        available_families=available_families,
        identity_input=identity_input,
    )
    if len(candidates) < 2:
        return None

    best_families = _best_ranked_families(rank_map=rank_map, families=candidates)
    if len(best_families) < 2:
        return None

    return _build_conflict(
        conflict_type="conflit_d_ancrage_de_source",
        sources=best_families,
    )


def build_source_conflicts(
    *,
    source_priority: Mapping[str, Any] | None,
    user_turn_input: Mapping[str, Any] | None,
    user_turn_signals: Mapping[str, Any] | None,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, list[dict[str, Any]]]:
    rank_map = _validated_source_priority(source_priority)
    user_turn_payload = _validated_user_turn_input(user_turn_input)
    user_turn_signals_payload = _validated_user_turn_signals(user_turn_signals)

    available_families = _available_source_families(
        memory_retrieved=_mapping(memory_retrieved),
        memory_arbitration=_mapping(memory_arbitration),
        summary_input=_mapping(summary_input),
        identity_input=_mapping(identity_input),
        recent_context_input=_mapping(recent_context_input),
        web_input=_mapping(web_input),
    )

    conflicts: list[dict[str, Any]] = []
    anchor_conflict = _anchor_conflict(
        rank_map=rank_map,
        user_turn_input=user_turn_payload,
        user_turn_signals=user_turn_signals_payload,
        available_families=available_families,
        identity_input=_mapping(identity_input),
    )
    if anchor_conflict:
        conflicts.append(anchor_conflict)

    return {"source_conflicts": conflicts}
