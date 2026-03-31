from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _parse_iso_datetime(raw: str) -> datetime:
    dt_value = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=timezone.utc)
    return dt_value


def _summary_cutoff_ts(summary_input_payload: Mapping[str, Any] | None) -> str | None:
    if not isinstance(summary_input_payload, Mapping):
        return None
    if str(summary_input_payload.get("status") or "") != "available":
        return None
    summary = summary_input_payload.get("summary")
    if not isinstance(summary, Mapping):
        return None
    return _optional_str(summary.get("end_ts")) or _optional_str(summary.get("start_ts"))


def _message_is_after_cutoff(message: Mapping[str, Any], cutoff_ts: str | None) -> bool:
    if not cutoff_ts:
        return True
    timestamp = _optional_str(message.get("timestamp"))
    if not timestamp:
        return True
    try:
        return _parse_iso_datetime(timestamp) > _parse_iso_datetime(cutoff_ts)
    except Exception:
        return True


def _canonical_message(message: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": str(message.get("role") or ""),
        "content": str(message.get("content") or ""),
        "timestamp": _optional_str(message.get("timestamp")),
    }


def build_recent_context_input(
    *,
    messages: Sequence[Mapping[str, Any]],
    summary_input_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cutoff_ts = _summary_cutoff_ts(summary_input_payload)
    canonical_messages = [
        _canonical_message(message)
        for message in messages
        if str(message.get("role") or "") in {"user", "assistant"}
        and _message_is_after_cutoff(message, cutoff_ts)
    ]
    return {
        "schema_version": SCHEMA_VERSION,
        "messages": canonical_messages,
    }
