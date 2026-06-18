from __future__ import annotations

"""Conversation-store acquisition for Exports V1 sources."""

from typing import Any, Mapping

from . import workspace_folder_exports


def read_conversation_source(
    payload: Mapping[str, Any] | None,
    *,
    conv_store_module: Any | None = None,
) -> dict[str, Any]:
    data = dict(payload or {})
    store = conv_store_module or _default_conv_store()
    raw_id = data.get("conversation_id") or data.get("source_id")
    if not raw_id:
        return _failure(workspace_folder_exports.REASON_SOURCE_MISSING)

    try:
        conversation_id = store.normalize_conversation_id(raw_id)
    except Exception:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)
    if not conversation_id:
        return _failure(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE)

    try:
        summary = store.get_conversation_summary(conversation_id, include_deleted=True)
    except Exception:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)
    if not isinstance(summary, Mapping):
        return _failure(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE)
    if summary.get("deleted_at"):
        return _failure(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE)

    try:
        conversation = store.read_conversation(conversation_id, "")
    except Exception:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)
    if not isinstance(conversation, Mapping):
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)

    messages = conversation.get("messages")
    if not isinstance(messages, list):
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)

    exportable_messages = [message for message in messages if _message_role(message) in {"user", "assistant"}]
    expected_count = _safe_int(summary.get("message_count"))
    exportable_count = len(exportable_messages)
    if expected_count > exportable_count:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)

    return {
        "ok": True,
        "conversation_id": conversation_id,
        "title": str(summary.get("title") or conversation.get("title") or "").strip(),
        "messages": exportable_messages,
    }


def _default_conv_store():
    from . import conv_store

    return conv_store


def _failure(reason_code: str) -> dict[str, Any]:
    return {"ok": False, "reason_code": reason_code}


def _message_role(message: Any) -> str:
    if not isinstance(message, Mapping):
        return ""
    return str(message.get("role") or "").strip().lower()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0
