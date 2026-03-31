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


def _canonical_decision(
    *,
    decision: Mapping[str, Any],
    memory_retrieved: Mapping[str, Any],
) -> dict[str, Any]:
    legacy_candidate_id = _optional_str(decision.get("candidate_id"))
    legacy_candidate_index = _optional_int(legacy_candidate_id)
    return {
        "retrieved_candidate_id": _retrieved_candidate_id(
            memory_retrieved=memory_retrieved,
            legacy_candidate_index=legacy_candidate_index,
        ),
        "legacy_candidate_id": legacy_candidate_id,
        "legacy_candidate_index": legacy_candidate_index,
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
) -> dict[str, Any]:
    canonical_decisions = [
        _canonical_decision(
            decision=decision,
            memory_retrieved=memory_retrieved,
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
        "decisions_count": len(canonical_decisions),
        "kept_count": kept_count,
        "rejected_count": rejected_count,
        "decisions": canonical_decisions,
    }
