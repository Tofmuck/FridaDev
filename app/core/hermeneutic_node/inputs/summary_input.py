from __future__ import annotations

from typing import Any, Mapping


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def build_summary_input(
    *,
    active_summary: Mapping[str, Any] | None,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    if not isinstance(active_summary, Mapping):
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "missing",
            "summary": None,
        }

    return {
        "schema_version": SCHEMA_VERSION,
        "status": "available",
        "summary": {
            "id": _optional_str(active_summary.get("id")),
            "conversation_id": _optional_str(active_summary.get("conversation_id")) or _optional_str(conversation_id),
            "start_ts": _optional_str(active_summary.get("start_ts")),
            "end_ts": _optional_str(active_summary.get("end_ts")),
            "content": str(active_summary.get("content") or ""),
        },
    }
