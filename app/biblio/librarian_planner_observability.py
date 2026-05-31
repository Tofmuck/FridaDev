"""Content-free observation helpers for the Biblio librarian planner."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


def safe_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "endpoint_kind",
        "status_code",
        "duration_ms",
        "result_count",
        "total_count",
        "displayed_count",
        "truncated",
        "doc_id_short",
        "doc_id_shorts",
        "query_chars",
        "query_hash",
        "locator_chars",
        "locator_hash",
        "content_chars",
        "content_hash",
        "positions",
        "error_class",
        "budget_exhausted",
        "clarification_count",
        "max_clarifications",
    }
    return {key: value for key, value in observation.items() if key in allowed}


def field_values(items: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    return [str(item.get(key) or "") for item in items if str(item.get(key) or "")]


def collect_doc_id_shorts(items: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in items:
        if item.get("doc_id_short"):
            values.append(str(item["doc_id_short"]))
        value = item.get("doc_id_shorts")
        if isinstance(value, list):
            values.extend(str(part) for part in value if str(part or ""))
    return values


def collect_positions(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for item in items:
        value = item.get("positions")
        if isinstance(value, list):
            positions.extend(dict(position) for position in value if isinstance(position, Mapping))
    return positions[:12]


def unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def safe_tool_name(value: Any) -> str:
    return str(value or "").strip()


def safe_token(value: Any, *, max_chars: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-.:/" for char in text):
        return "invalid_token"
    return text[:max_chars]


def int_value(value: Any) -> int | None:
    return value if type(value) is int else None


def strict_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def clean(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }
