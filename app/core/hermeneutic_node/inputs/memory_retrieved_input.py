from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _canonical_parent_summary(parent_summary: Mapping[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(parent_summary, Mapping):
        return None
    return {
        "id": _optional_str(parent_summary.get("id")),
        "conversation_id": _optional_str(parent_summary.get("conversation_id")),
        "start_ts": _optional_str(parent_summary.get("start_ts")),
        "end_ts": _optional_str(parent_summary.get("end_ts")),
        "content": str(parent_summary.get("content") or ""),
    }


def _candidate_id(trace: Mapping[str, Any]) -> str:
    fingerprint = {
        "conversation_id": _optional_str(trace.get("conversation_id")),
        "role": _optional_str(trace.get("role")),
        "content": str(trace.get("content") or ""),
        "timestamp_iso": _optional_str(trace.get("timestamp") or trace.get("timestamp_iso")),
        "summary_id": _optional_str(trace.get("summary_id")),
    }
    digest = hashlib.sha1(
        json.dumps(fingerprint, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"cand-{digest}"


def _canonical_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": _candidate_id(trace),
        "conversation_id": _optional_str(trace.get("conversation_id")),
        "role": _optional_str(trace.get("role")),
        "content": str(trace.get("content") or ""),
        "timestamp_iso": _optional_str(trace.get("timestamp") or trace.get("timestamp_iso")),
        "retrieval_score": float(trace.get("retrieval_score", trace.get("score")) or 0.0),
        "summary_id": _optional_str(trace.get("summary_id")),
        "parent_summary": _canonical_parent_summary(trace.get("parent_summary")),
    }


def build_memory_retrieved_input(
    *,
    retrieval_query: str,
    top_k_requested: int | None,
    traces: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    canonical_traces = [_canonical_trace(trace) for trace in traces]
    return {
        "schema_version": SCHEMA_VERSION,
        "retrieval_query": str(retrieval_query),
        "top_k_requested": int(top_k_requested) if top_k_requested is not None else None,
        "retrieved_count": len(canonical_traces),
        "traces": canonical_traces,
    }
