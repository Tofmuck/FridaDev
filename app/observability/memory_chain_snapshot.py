from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from observability import chat_turn_logger
from observability.memory_arbiter_reason_codes import compact_arbiter_reason_observability


SCHEMA_VERSION = "v1"
MAX_RECORDED_CANDIDATES = 24


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


def _float_or_none(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _rounded_score(value: Any) -> float | None:
    score = _float_or_none(value)
    if score is None:
        return None
    return round(score, 3)


def _score_bucket(value: Any) -> str:
    score = _float_or_none(value)
    if score is None:
        return "unknown"
    if score >= 0.8:
        return "high"
    if score >= 0.5:
        return "medium"
    if score > 0.0:
        return "low"
    return "zero"


def _sha256_12(value: Any) -> str:
    text = _text(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _candidate_ref(candidate_id: Any) -> dict[str, str]:
    text = _text(candidate_id)
    return {
        "candidate_id": text,
        "candidate_id_sha256_12": _sha256_12(text),
    }


def _source_candidate_ids(candidate: Mapping[str, Any]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in _sequence(candidate.get("source_candidate_ids")):
        text = _text(value)
        if text and text not in seen:
            seen.add(text)
            out.append(text)
    candidate_id = _text(candidate.get("candidate_id"))
    if candidate_id and candidate_id not in seen:
        out.insert(0, candidate_id)
    return out


def _count_by_key(items: Sequence[Any], key: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        payload = _mapping(item)
        label = _text(payload.get(key)) or "unknown"
        counts[label] = counts.get(label, 0) + 1
    return dict(sorted(counts.items()))


def _decision_status(decision: Mapping[str, Any] | None, *, arbitration_status: str, reason_code: str) -> str:
    if decision:
        return "keep" if bool(decision.get("keep", False)) else "drop"
    if arbitration_status == "skipped":
        return f"skipped:{reason_code or 'unspecified'}"
    return "no_decision"


def _injection_class(
    *,
    memory_traces: Sequence[Any],
    context_hints: Sequence[Any],
) -> str:
    traces = [_mapping(item) for item in memory_traces if isinstance(item, Mapping)]
    if traces:
        source_kinds = {
            _text(trace.get("source_kind"))
            or ("summary" if _text(trace.get("role")) == "summary" else "trace")
            for trace in traces
        }
        if source_kinds and source_kinds <= {"summary"}:
            return "summary_only"
        return "trace_memory"
    if context_hints:
        return "hints_only"
    return "none"


def _build_indexes(
    memory_arbitration: Mapping[str, Any],
) -> tuple[dict[str, Mapping[str, Any]], dict[str, str], dict[str, Mapping[str, Any]]]:
    basket_by_id: dict[str, Mapping[str, Any]] = {}
    source_to_basket_id: dict[str, str] = {}
    for candidate in _sequence(memory_arbitration.get("basket_candidates")):
        payload = _mapping(candidate)
        candidate_id = _text(payload.get("candidate_id"))
        if not candidate_id:
            continue
        basket_by_id[candidate_id] = payload
        for source_candidate_id in _source_candidate_ids(payload):
            source_to_basket_id[source_candidate_id] = candidate_id

    decisions_by_id: dict[str, Mapping[str, Any]] = {}
    for decision in _sequence(memory_arbitration.get("decisions")):
        payload = _mapping(decision)
        candidate_id = _text(payload.get("candidate_id"))
        if candidate_id:
            decisions_by_id[candidate_id] = payload
    return basket_by_id, source_to_basket_id, decisions_by_id


def _retrieved_candidate_snapshot(
    *,
    trace: Mapping[str, Any],
    rank: int,
    basket_by_id: Mapping[str, Mapping[str, Any]],
    source_to_basket_id: Mapping[str, str],
    decisions_by_id: Mapping[str, Mapping[str, Any]],
    injected_candidate_ids: set[str],
    arbitration_status: str,
    arbitration_reason_code: str,
) -> dict[str, Any]:
    candidate_id = _text(trace.get("candidate_id"))
    basket_candidate_id = source_to_basket_id.get(candidate_id, "")
    basket_candidate = basket_by_id.get(basket_candidate_id, {})
    decision = decisions_by_id.get(basket_candidate_id)
    if not basket_candidate_id:
        basket_status = "not_basketed"
        pre_arbiter_reason_code = "pre_arbiter_limit_or_invalid"
    elif basket_candidate_id == candidate_id:
        basket_status = "basket_representative"
        pre_arbiter_reason_code = _text(basket_candidate.get("dedup_reason_code")) or "none"
    else:
        basket_status = "deduped_into_basket"
        pre_arbiter_reason_code = _text(basket_candidate.get("dedup_reason_code")) or "deduped"

    if candidate_id in injected_candidate_ids:
        prompt_injection_status = "direct"
    elif basket_candidate_id and basket_candidate_id in injected_candidate_ids:
        prompt_injection_status = "via_basket_representative"
    else:
        prompt_injection_status = "not_injected"

    out = {
        **_candidate_ref(candidate_id),
        "retrieval_rank": rank,
        "source_kind": _text(trace.get("source_kind")) or "trace",
        "source_lane": _text(trace.get("source_lane")) or "global",
        "retrieval_score": _rounded_score(trace.get("retrieval_score")),
        "retrieval_score_bucket": _score_bucket(trace.get("retrieval_score")),
        "basket_status": basket_status,
        "pre_arbiter_reason_code": pre_arbiter_reason_code,
        "arbiter_status": _decision_status(
            decision,
            arbitration_status=arbitration_status,
            reason_code=arbitration_reason_code,
        ),
        "prompt_injection_status": prompt_injection_status,
    }
    if basket_candidate_id and basket_candidate_id != candidate_id:
        out["basket_candidate_id"] = basket_candidate_id
        out["basket_candidate_id_sha256_12"] = _sha256_12(basket_candidate_id)
    return out


def _basket_candidate_snapshot(
    *,
    candidate: Mapping[str, Any],
    rank: int,
    decisions_by_id: Mapping[str, Mapping[str, Any]],
    injected_candidate_ids: set[str],
    arbitration_status: str,
    arbitration_reason_code: str,
) -> dict[str, Any]:
    candidate_id = _text(candidate.get("candidate_id"))
    decision = decisions_by_id.get(candidate_id)
    source_candidate_ids = _source_candidate_ids(candidate)
    out = {
        **_candidate_ref(candidate_id),
        "basket_rank": rank,
        "source_candidate_count": len(source_candidate_ids),
        "source_candidate_id_sha256_12": [_sha256_12(value) for value in source_candidate_ids[:8]],
        "source_kind": _text(candidate.get("source_kind")) or "trace",
        "source_lane": _text(candidate.get("source_lane")) or "global",
        "retrieval_score": _rounded_score(candidate.get("retrieval_score")),
        "retrieval_score_bucket": _score_bucket(candidate.get("retrieval_score")),
        "dedup_reason_code": _text(candidate.get("dedup_reason_code")) or "none",
        "arbiter_status": _decision_status(
            decision,
            arbitration_status=arbitration_status,
            reason_code=arbitration_reason_code,
        ),
        "prompt_injection_status": "direct" if candidate_id in injected_candidate_ids else "not_injected",
    }
    if decision:
        out.update(
            {
                "decision_source": _text(decision.get("decision_source")) or "unknown",
                "semantic_relevance": _rounded_score(decision.get("semantic_relevance")),
                "contextual_gain": _rounded_score(decision.get("contextual_gain")),
                "redundant_with_recent": bool(decision.get("redundant_with_recent", False)),
                **compact_arbiter_reason_observability(decision.get("reason")),
            }
        )
    return out


def build_memory_chain_snapshot_payload(
    *,
    current_mode: str,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
    memory_traces: Sequence[Any] | None,
    context_hints: Sequence[Any] | None,
) -> dict[str, Any]:
    retrieved_traces = [
        _mapping(trace)
        for trace in _sequence(memory_retrieved.get("traces"))
        if isinstance(trace, Mapping)
    ]
    basket_candidates = [
        _mapping(candidate)
        for candidate in _sequence(memory_arbitration.get("basket_candidates"))
        if isinstance(candidate, Mapping)
    ]
    decisions = [
        _mapping(decision)
        for decision in _sequence(memory_arbitration.get("decisions"))
        if isinstance(decision, Mapping)
    ]
    injected_candidate_ids = {
        _text(candidate_id)
        for candidate_id in _sequence(memory_arbitration.get("injected_candidate_ids"))
        if _text(candidate_id)
    }
    traces_for_prompt = list(_sequence(memory_traces))
    hints_for_prompt = list(_sequence(context_hints))
    basket_by_id, source_to_basket_id, decisions_by_id = _build_indexes(memory_arbitration)
    arbitration_status = _text(memory_arbitration.get("status")) or "missing"
    arbitration_reason_code = _text(memory_arbitration.get("reason_code"))

    retrieved_snapshots = [
        _retrieved_candidate_snapshot(
            trace=trace,
            rank=index,
            basket_by_id=basket_by_id,
            source_to_basket_id=source_to_basket_id,
            decisions_by_id=decisions_by_id,
            injected_candidate_ids=injected_candidate_ids,
            arbitration_status=arbitration_status,
            arbitration_reason_code=arbitration_reason_code,
        )
        for index, trace in enumerate(retrieved_traces[:MAX_RECORDED_CANDIDATES], start=1)
    ]
    basket_snapshots = [
        _basket_candidate_snapshot(
            candidate=candidate,
            rank=index,
            decisions_by_id=decisions_by_id,
            injected_candidate_ids=injected_candidate_ids,
            arbitration_status=arbitration_status,
            arbitration_reason_code=arbitration_reason_code,
        )
        for index, candidate in enumerate(basket_candidates[:MAX_RECORDED_CANDIDATES], start=1)
    ]

    candidate_status_counts = _count_by_key(retrieved_snapshots, "prompt_injection_status")
    basket_status_counts = _count_by_key(retrieved_snapshots, "basket_status")
    arbiter_status_counts = _count_by_key(basket_snapshots, "arbiter_status")
    deduped_count = int(basket_status_counts.get("deduped_into_basket", 0))
    not_basketed_count = int(basket_status_counts.get("not_basketed", 0))

    return {
        "schema_version": SCHEMA_VERSION,
        "mode": _text(current_mode),
        "retrieval": {
            "status": _text(memory_retrieved.get("status")) or "missing",
            "reason_code": _text(memory_retrieved.get("reason_code")),
            "error_code": _text(memory_retrieved.get("error_code")),
            "error_class": _text(memory_retrieved.get("error_class")),
            "top_k_requested": memory_retrieved.get("top_k_requested"),
            "retrieved_count": _int_or_zero(memory_retrieved.get("retrieved_count") or len(retrieved_traces)),
            "source_kind_counts": _count_by_key(retrieved_traces, "source_kind"),
            "source_lane_counts": _count_by_key(retrieved_traces, "source_lane"),
        },
        "basket": {
            "status": arbitration_status,
            "reason_code": arbitration_reason_code,
            "basket_candidates_count": _int_or_zero(
                memory_arbitration.get("basket_candidates_count") or len(basket_candidates)
            ),
            "deduped_retrieved_count": deduped_count,
            "not_basketed_count": not_basketed_count,
            "basket_status_counts": basket_status_counts,
        },
        "arbiter": {
            "status": arbitration_status,
            "reason_code": arbitration_reason_code,
            "decisions_count": _int_or_zero(memory_arbitration.get("decisions_count") or len(decisions)),
            "kept_count": _int_or_zero(memory_arbitration.get("kept_count")),
            "rejected_count": _int_or_zero(memory_arbitration.get("rejected_count")),
            "arbiter_status_counts": arbiter_status_counts,
            "decision_source_counts": _count_by_key(decisions, "decision_source"),
        },
        "injection": {
            "injection_class": _injection_class(
                memory_traces=traces_for_prompt,
                context_hints=hints_for_prompt,
            ),
            "injected_candidate_count": len(injected_candidate_ids),
            "injected_candidate_id_sha256_12": [
                _sha256_12(value) for value in sorted(injected_candidate_ids)[:8]
            ],
            "context_hints_count": len(hints_for_prompt),
            "candidate_status_counts": candidate_status_counts,
        },
        "retrieved_candidates": retrieved_snapshots,
        "basket_candidates": basket_snapshots,
        "truncated": bool(
            len(retrieved_traces) > MAX_RECORDED_CANDIDATES
            or len(basket_candidates) > MAX_RECORDED_CANDIDATES
        ),
    }


def emit_memory_chain_snapshot(
    *,
    current_mode: str,
    memory_retrieved: Mapping[str, Any],
    memory_arbitration: Mapping[str, Any],
    memory_traces: Sequence[Any] | None,
    context_hints: Sequence[Any] | None,
) -> bool:
    payload = build_memory_chain_snapshot_payload(
        current_mode=current_mode,
        memory_retrieved=memory_retrieved,
        memory_arbitration=memory_arbitration,
        memory_traces=memory_traces,
        context_hints=context_hints,
    )
    retrieval = _mapping(payload.get("retrieval"))
    status = "error" if _text(retrieval.get("status")) == "error" else "ok"
    return chat_turn_logger.emit(
        "memory_chain_snapshot",
        status=status,
        reason_code=_text(retrieval.get("reason_code")) or None,
        error_code=_text(retrieval.get("error_code")) or None,
        payload=payload,
    )
