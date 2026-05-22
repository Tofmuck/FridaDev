from __future__ import annotations

"""Content-free logging helpers for workspace folder files."""

from typing import Any, Mapping


_LOG_FIELD_MAX_CHARS = 180
_CONTENT_FREE_LOG_FIELDS = {
    "conversation_id",
    "folder_id",
    "file_id",
    "selection_count",
    "selection_status",
    "selected",
    "injected",
    "media_kind",
    "content_kind",
    "mime_type",
    "byte_size",
    "image_width",
    "image_height",
    "sha256_12",
    "status",
    "reason_code",
    "requested",
    "deleted",
    "failed",
    "error_type",
}


def _collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _compact_log_value(value: Any) -> str:
    if value is None:
        return ""
    text = _collapse_ws(value)
    if len(text) > _LOG_FIELD_MAX_CHARS:
        text = text[:_LOG_FIELD_MAX_CHARS].rstrip()
    return text


def content_free_log_fields(fields: Mapping[str, Any]) -> dict[str, str]:
    return {
        key: safe_value
        for key, value in fields.items()
        if key in _CONTENT_FREE_LOG_FIELDS
        for safe_value in (_compact_log_value(value),)
        if safe_value
    }


def log_content_free_event(logger: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(logger, level, None)
    if not callable(log_func):
        return
    event_name = "".join(ch if ch.isalnum() or ch == "_" else "_" for ch in str(event or "event").lower())
    payload = content_free_log_fields(fields)
    details = " ".join(f"{key}={value}" for key, value in sorted(payload.items()))
    if details:
        log_func("workspace_files_%s %s", event_name, details)
    else:
        log_func("workspace_files_%s", event_name)
