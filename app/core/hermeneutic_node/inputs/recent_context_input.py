from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"
VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES = 5


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


def _canonical_dialogue_messages(
    *,
    messages: Sequence[Mapping[str, Any]],
    cutoff_ts: str | None,
) -> list[dict[str, Any]]:
    return [
        _canonical_message(message)
        for message in messages
        if str(message.get("role") or "") in {"user", "assistant"}
        and str(message.get("content") or "").strip()
        and _message_is_after_cutoff(message, cutoff_ts)
    ]


def _latest_role_index(
    messages: Sequence[Mapping[str, Any]],
    *,
    role: str,
    before_index: int | None = None,
) -> int | None:
    start = len(messages) if before_index is None else max(0, int(before_index))
    for idx in range(start - 1, -1, -1):
        if str(messages[idx].get("role") or "") == role:
            return idx
    return None


def _build_validation_dialogue_window(
    *,
    canonical_messages: Sequence[Mapping[str, Any]],
    max_messages: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    max_messages = max(0, int(max_messages))
    if not canonical_messages or max_messages <= 0:
        return [], {
            "source_message_count": len(canonical_messages),
            "truncated": bool(canonical_messages),
            "current_user_retained": False,
            "last_assistant_retained": False,
        }

    current_user_index = _latest_role_index(canonical_messages, role="user")
    last_assistant_index = _latest_role_index(
        canonical_messages,
        role="assistant",
        before_index=current_user_index,
    )
    if last_assistant_index is None:
        last_assistant_index = _latest_role_index(canonical_messages, role="assistant")

    selected_indices: list[int] = []
    for candidate in (current_user_index, last_assistant_index):
        if candidate is None or candidate in selected_indices:
            continue
        selected_indices.append(candidate)
        if len(selected_indices) >= max_messages:
            break

    for idx in range(len(canonical_messages) - 1, -1, -1):
        if idx in selected_indices:
            continue
        selected_indices.append(idx)
        if len(selected_indices) >= max_messages:
            break

    retained_indices = sorted(selected_indices)
    return (
        [dict(canonical_messages[idx]) for idx in retained_indices],
        {
            "source_message_count": len(canonical_messages),
            "truncated": len(canonical_messages) > len(retained_indices),
            "current_user_retained": current_user_index is not None and current_user_index in retained_indices,
            "last_assistant_retained": last_assistant_index is not None and last_assistant_index in retained_indices,
        },
    )


def build_recent_context_input(
    *,
    messages: Sequence[Mapping[str, Any]],
    summary_input_payload: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    cutoff_ts = _summary_cutoff_ts(summary_input_payload)
    canonical_messages = _canonical_dialogue_messages(messages=messages, cutoff_ts=cutoff_ts)
    return {
        "schema_version": SCHEMA_VERSION,
        "messages": canonical_messages,
    }


def build_validation_dialogue_context(
    *,
    messages: Sequence[Mapping[str, Any]],
    summary_input_payload: Mapping[str, Any] | None = None,
    max_messages: int = VALIDATION_DIALOGUE_CONTEXT_MAX_MESSAGES,
) -> dict[str, Any]:
    cutoff_ts = _summary_cutoff_ts(summary_input_payload)
    canonical_messages = _canonical_dialogue_messages(messages=messages, cutoff_ts=cutoff_ts)
    retained_messages, metadata = _build_validation_dialogue_window(
        canonical_messages=canonical_messages,
        max_messages=max_messages,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "messages": retained_messages,
        "source_message_count": int(metadata["source_message_count"]),
        "truncated": bool(metadata["truncated"]),
        "current_user_retained": bool(metadata["current_user_retained"]),
        "last_assistant_retained": bool(metadata["last_assistant_retained"]),
    }
