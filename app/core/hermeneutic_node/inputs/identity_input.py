from __future__ import annotations

from typing import Any, Mapping


SCHEMA_VERSION = "v2"


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _canonical_mutable(entry: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(entry)
    return {
        "content": str(payload.get("content") or ""),
        "source_trace_id": _optional_str(payload.get("source_trace_id")),
        "updated_by": _optional_str(payload.get("updated_by")),
        "update_reason": _optional_str(payload.get("update_reason")),
        "updated_ts": _optional_str(payload.get("updated_ts")) or _optional_str(payload.get("created_ts")),
    }


def _canonical_side(
    *,
    static_content: str,
    static_source: str | None,
    mutable: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return {
        "static": {
            "content": str(static_content or ""),
            "source": _optional_str(static_source),
        },
        "mutable": _canonical_mutable(mutable),
    }


def build_identity_input(
    *,
    frida_static_content: str = "",
    frida_static_source: str | None = None,
    frida_mutable: Mapping[str, Any] | None = None,
    user_static_content: str = "",
    user_static_source: str | None = None,
    user_mutable: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "frida": _canonical_side(
            static_content=frida_static_content,
            static_source=frida_static_source,
            mutable=frida_mutable,
        ),
        "user": _canonical_side(
            static_content=user_static_content,
            static_source=user_static_source,
            mutable=user_mutable,
        ),
    }
