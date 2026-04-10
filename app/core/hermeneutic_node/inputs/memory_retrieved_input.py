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


def _source_kind(trace: Mapping[str, Any]) -> str:
    explicit = _optional_str(trace.get("source_kind"))
    if explicit:
        return explicit
    if _optional_str(trace.get("role")) == "summary" and _optional_str(trace.get("summary_id")):
        return "summary"
    return "trace"


def _source_lane(trace: Mapping[str, Any], *, source_kind: str) -> str:
    explicit = _optional_str(trace.get("source_lane"))
    if explicit:
        return explicit
    if source_kind == "summary":
        return "summaries"
    return "global"


def _candidate_id(trace: Mapping[str, Any]) -> str:
    source_kind = _source_kind(trace)
    summary_id = _optional_str(trace.get("summary_id"))
    if source_kind == "summary" and summary_id:
        return f"summary:{summary_id}"
    fingerprint = {
        "conversation_id": _optional_str(trace.get("conversation_id")),
        "role": _optional_str(trace.get("role")),
        "content": str(trace.get("content") or ""),
        "timestamp_iso": _optional_str(trace.get("timestamp") or trace.get("timestamp_iso")),
        "summary_id": summary_id,
    }
    digest = hashlib.sha1(
        json.dumps(fingerprint, sort_keys=True, ensure_ascii=True).encode("utf-8")
    ).hexdigest()[:16]
    return f"cand-{digest}"


def _canonical_trace(trace: Mapping[str, Any]) -> dict[str, Any]:
    source_kind = _source_kind(trace)
    start_ts = _optional_str(trace.get("start_ts"))
    end_ts = _optional_str(trace.get("end_ts"))
    timestamp_iso = (
        end_ts
        if source_kind == "summary"
        else _optional_str(trace.get("timestamp") or trace.get("timestamp_iso"))
    )
    parent_summary = None if source_kind == "summary" else _canonical_parent_summary(trace.get("parent_summary"))
    return {
        "candidate_id": _candidate_id(trace),
        "source_kind": source_kind,
        "source_lane": _source_lane(trace, source_kind=source_kind),
        "conversation_id": _optional_str(trace.get("conversation_id")),
        "role": _optional_str(trace.get("role")),
        "content": str(trace.get("content") or ""),
        "timestamp_iso": timestamp_iso,
        "start_ts": start_ts,
        "end_ts": end_ts,
        "retrieval_score": float(trace.get("retrieval_score", trace.get("score")) or 0.0),
        "summary_id": _optional_str(trace.get("summary_id")),
        "parent_summary": parent_summary,
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
