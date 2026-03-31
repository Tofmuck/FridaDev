from __future__ import annotations

from typing import Any, Mapping, Sequence


SCHEMA_VERSION = "v1"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _canonical_dynamic_entry(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "id": _optional_str(entry.get("id")),
        "content": str(entry.get("content") or ""),
        "stability": str(entry.get("stability") or "unknown"),
        "recurrence": str(entry.get("recurrence") or "unknown"),
        "confidence": _float_or_zero(entry.get("confidence")),
        "last_seen_ts": _optional_str(entry.get("last_seen_ts")) or _optional_str(entry.get("created_ts")),
        "scope": str(entry.get("scope") or "unknown"),
    }


def _canonical_side(
    *,
    static_content: str,
    static_source: str | None,
    dynamic_entries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "static": {
            "content": str(static_content or ""),
            "source": _optional_str(static_source),
        },
        "dynamic": [_canonical_dynamic_entry(entry) for entry in dynamic_entries],
    }


def build_identity_input(
    *,
    frida_static_content: str = "",
    frida_static_source: str | None = None,
    frida_dynamic_entries: Sequence[Mapping[str, Any]] = (),
    user_static_content: str = "",
    user_static_source: str | None = None,
    user_dynamic_entries: Sequence[Mapping[str, Any]] = (),
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "frida": _canonical_side(
            static_content=frida_static_content,
            static_source=frida_static_source,
            dynamic_entries=frida_dynamic_entries,
        ),
        "user": _canonical_side(
            static_content=user_static_content,
            static_source=user_static_source,
            dynamic_entries=user_dynamic_entries,
        ),
    }
