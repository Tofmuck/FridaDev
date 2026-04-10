from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _canonical_candidate(candidate: Mapping[str, Any]) -> dict[str, Any]:
    source_candidate_ids = candidate.get("source_candidate_ids")
    if not isinstance(source_candidate_ids, Sequence) or isinstance(
        source_candidate_ids,
        (str, bytes, bytearray),
    ):
        source_candidate_ids = ()
    return {
        "candidate_id": _optional_str(candidate.get("candidate_id")),
        "source_candidate_ids": [
            text
            for text in (_optional_str(value) for value in source_candidate_ids)
            if text
        ],
        "source_kind": _optional_str(candidate.get("source_kind")) or "trace",
        "source_lane": _optional_str(candidate.get("source_lane")) or "global",
        "conversation_id": _optional_str(candidate.get("conversation_id")),
        "role": _optional_str(candidate.get("role")),
        "content": str(candidate.get("content") or ""),
        "timestamp_iso": _optional_str(candidate.get("timestamp_iso")),
        "retrieval_score": _float_or_zero(candidate.get("retrieval_score")),
        "semantic_score": _float_or_zero(candidate.get("semantic_score")),
        "summary_id": _optional_str(candidate.get("summary_id")),
        "parent_summary_present": bool(candidate.get("parent_summary_present", False)),
        "dedup_key": _optional_str(candidate.get("dedup_key")),
        "dedup_reason_code": _optional_str(candidate.get("dedup_reason_code")) or "none",
        "conversation_rank": _optional_int(candidate.get("conversation_rank")),
    }


def _retrieved_candidate_id(
    *,
    memory_retrieved: Mapping[str, Any],
    legacy_candidate_index: int | None,
) -> str | None:
    if legacy_candidate_index is None:
        return None
    traces = memory_retrieved.get("traces")
    if not isinstance(traces, Sequence):
        return None
    if legacy_candidate_index < 0 or legacy_candidate_index >= len(traces):
        return None
    trace = traces[legacy_candidate_index]
    if not isinstance(trace, Mapping):
        return None
    return _optional_str(trace.get("candidate_id"))


def _basket_candidate_by_id(
    *,
    basket_candidates: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    candidates: dict[str, dict[str, Any]] = {}
    for candidate in basket_candidates:
        if not isinstance(candidate, Mapping):
            continue
        candidate_id = _optional_str(candidate.get("candidate_id"))
        if not candidate_id:
            continue
        candidates[candidate_id] = _canonical_candidate(candidate)
    return candidates


def _canonical_decision(
    *,
    decision: Mapping[str, Any],
    memory_retrieved: Mapping[str, Any],
    basket_candidates_by_id: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    raw_candidate_id = _optional_str(decision.get("candidate_id"))
    legacy_candidate_index = _optional_int(raw_candidate_id)
    stable_candidate_id = raw_candidate_id
    legacy_candidate_id = None
    if stable_candidate_id not in basket_candidates_by_id:
        if legacy_candidate_index is not None:
            stable_candidate_id = _retrieved_candidate_id(
                memory_retrieved=memory_retrieved,
                legacy_candidate_index=legacy_candidate_index,
            )
            legacy_candidate_id = raw_candidate_id
        elif raw_candidate_id and raw_candidate_id != stable_candidate_id:
            legacy_candidate_id = raw_candidate_id
    basket_candidate = (
        basket_candidates_by_id.get(stable_candidate_id)
        if stable_candidate_id is not None
        else None
    )
    return {
        "candidate_id": stable_candidate_id,
        "retrieved_candidate_id": stable_candidate_id,
        "legacy_candidate_id": legacy_candidate_id,
        "legacy_candidate_index": legacy_candidate_index,
        "source_candidate_ids": list(basket_candidate.get("source_candidate_ids", ()))
        if isinstance(basket_candidate, Mapping)
        else [],
        "source_kind": _optional_str(basket_candidate.get("source_kind"))
        if isinstance(basket_candidate, Mapping)
        else None,
        "source_lane": _optional_str(basket_candidate.get("source_lane"))
        if isinstance(basket_candidate, Mapping)
        else None,
        "keep": bool(decision.get("keep", False)),
        "semantic_relevance": _float_or_zero(decision.get("semantic_relevance")),
        "contextual_gain": _float_or_zero(decision.get("contextual_gain")),
        "redundant_with_recent": bool(decision.get("redundant_with_recent", False)),
        "reason": str(decision.get("reason") or ""),
        "decision_source": str(decision.get("decision_source") or ""),
        "model": _optional_str(decision.get("model")),
    }


def build_memory_arbitration_input(
    *,
    memory_retrieved: Mapping[str, Any],
    raw_candidates_count: int,
    decisions: Sequence[Mapping[str, Any]],
    status: str,
    reason_code: str | None = None,
    basket_candidates: Sequence[Mapping[str, Any]] = (),
    injected_candidate_ids: Sequence[str] = (),
) -> dict[str, Any]:
    canonical_basket_candidates = [
        _canonical_candidate(candidate)
        for candidate in basket_candidates
        if isinstance(candidate, Mapping)
    ]
    basket_candidates_by_id = _basket_candidate_by_id(
        basket_candidates=canonical_basket_candidates,
    )
    canonical_decisions = [
        _canonical_decision(
            decision=decision,
            memory_retrieved=memory_retrieved,
            basket_candidates_by_id=basket_candidates_by_id,
        )
        for decision in decisions
    ]
    kept_count = sum(1 for decision in canonical_decisions if decision["keep"])
    rejected_count = sum(1 for decision in canonical_decisions if not decision["keep"])
    return {
        "schema_version": SCHEMA_VERSION,
        "status": str(status),
        "reason_code": _optional_str(reason_code),
        "raw_candidates_count": int(raw_candidates_count),
        "basket_candidates_count": len(canonical_basket_candidates),
        "basket_limit": 8,
        "basket_candidates": canonical_basket_candidates,
        "decisions_count": len(canonical_decisions),
        "kept_count": kept_count,
        "rejected_count": rejected_count,
        "injected_candidate_ids": [
            text
            for text in (_optional_str(candidate_id) for candidate_id in injected_candidate_ids)
            if text
        ],
        "decisions": canonical_decisions,
    }
