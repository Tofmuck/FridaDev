from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "main_payload_manifest_v1"
SCOPE = "main_chat"
OBSERVABILITY_STAGE = "main_payload_manifest"

STATUS_OK = "ok"
STATUS_DISABLED = "disabled"
STATUS_NOT_SELECTED = "not_selected"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_NOT_AVAILABLE = "not_available"
STATUS_NOT_INSTRUMENTED = "not_instrumented"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

RAW_FLAGS = {
    "raw_prompt_included": False,
    "raw_message_included": False,
    "raw_content_included": False,
    "raw_lane_content_included": False,
    "raw_provider_payload_included": False,
    "raw_secret_included": False,
}


def mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def safe_str(value: Any) -> str:
    return str(value or "").strip()


def safe_status(value: Any, *, fallback: str = STATUS_NOT_APPLICABLE) -> str:
    status = safe_str(value).lower()
    if status in {
        STATUS_OK,
        "skipped",
        STATUS_DISABLED,
        STATUS_NOT_SELECTED,
        STATUS_NOT_CONFIGURED,
        STATUS_NOT_APPLICABLE,
        STATUS_NOT_AVAILABLE,
        STATUS_NOT_INSTRUMENTED,
        "refused",
        STATUS_FAILED,
        STATUS_ERROR,
    }:
        return status
    if status in {"empty", "missing", "not_requested"}:
        return STATUS_NOT_SELECTED
    if status in {"available", "ready", "authorized", "used"}:
        return STATUS_OK
    return fallback


def dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = safe_str(value)
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def count_from_sequence(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0
