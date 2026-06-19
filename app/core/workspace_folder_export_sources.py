from __future__ import annotations

"""Explicit source acquisition for Exports V1 fake/local generation."""

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from . import workspace_folder_export_refs
from . import workspace_folder_exports


SOURCE_TEXT_MAX_CHARS = 120_000
EXPORTABLE_MESSAGE_ROLES = frozenset({"user", "assistant"})

_ROLE_LABELS = {
    "user": "Utilisateur",
    "assistant": "Frida",
}
_SOURCE_REF_PREFIX = {
    workspace_folder_exports.SOURCE_CONVERSATION: "conversation",
    workspace_folder_exports.SOURCE_MESSAGE_SELECTION: "message-selection",
    workspace_folder_exports.SOURCE_FRIDA_RESPONSE: "frida-response",
    workspace_folder_exports.SOURCE_NOTE: "workspace-note",
    workspace_folder_exports.SOURCE_DOCUMENT: "workspace-file",
    workspace_folder_exports.SOURCE_EXPORT: "workspace-export",
}
_KIND_ALIASES = {
    "message-selection": workspace_folder_exports.SOURCE_MESSAGE_SELECTION,
    "frida-response": workspace_folder_exports.SOURCE_FRIDA_RESPONSE,
    "workspace-note": workspace_folder_exports.SOURCE_NOTE,
    "workspace-file": workspace_folder_exports.SOURCE_DOCUMENT,
    "workspace-export": workspace_folder_exports.SOURCE_EXPORT,
}

Reader = Callable[[Mapping[str, Any]], Mapping[str, Any]]


@dataclass(frozen=True)
class ExportSource:
    ok: bool
    reason_code: str
    source_kind: str = ""
    source_ref: str = ""
    source_hash: str = ""
    title: str = ""
    content: str = ""
    char_count: int = 0
    counters: Mapping[str, int] | None = None

    def content_free_projection(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "reason_code": self.reason_code,
            "source_kind": self.source_kind,
            "source_ref": self.source_ref,
            "source_hash": self.source_hash,
            "char_count": self.char_count,
            "counters": dict(self.counters or {}),
        }


def acquire_export_source(
    request: Mapping[str, Any] | None,
    *,
    conversation_reader: Reader | None = None,
    note_reader: Reader | None = None,
    document_reader: Reader | None = None,
    export_reader: Reader | None = None,
) -> ExportSource:
    payload = dict(request or {})
    source_kind = _source_kind(payload.get("source_kind") or payload.get("source"))
    if not source_kind:
        return _reject(workspace_folder_exports.REASON_SOURCE_MISSING)
    if not _is_explicit(payload):
        return _reject(
            workspace_folder_exports.REASON_SOURCE_AMBIGUOUS,
            source_kind=source_kind,
            source_seed=payload.get("source_id") or source_kind,
        )

    if source_kind == workspace_folder_exports.SOURCE_CONVERSATION:
        return _conversation_source(payload, conversation_reader=conversation_reader)
    if source_kind == workspace_folder_exports.SOURCE_MESSAGE_SELECTION:
        return _message_selection_source(payload)
    if source_kind == workspace_folder_exports.SOURCE_FRIDA_RESPONSE:
        return _frida_response_source(payload)
    if source_kind == workspace_folder_exports.SOURCE_NOTE:
        return _reader_source(
            payload,
            source_kind=source_kind,
            reader=note_reader,
            id_keys=("note_id", "workspace_note_id", "source_id"),
            content_paths=(
                ("note_conversation", "markdown_content"),
                ("markdown_content",),
                ("content",),
            ),
        )
    if source_kind == workspace_folder_exports.SOURCE_DOCUMENT:
        return _reader_source(
            payload,
            source_kind=source_kind,
            reader=document_reader,
            id_keys=("document_id", "workspace_file_id", "source_id"),
            content_paths=(
                ("document_conversation", "text_content"),
                ("text_content",),
                ("content",),
            ),
            missing_reader_reason=workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
        )
    if source_kind == workspace_folder_exports.SOURCE_EXPORT:
        return _reader_source(
            payload,
            source_kind=source_kind,
            reader=export_reader,
            id_keys=("export_id", "workspace_export_id", "source_id"),
            content_paths=(("export_content",), ("content",)),
        )
    return _reject(workspace_folder_exports.REASON_SOURCE_UNSUPPORTED, source_kind=source_kind)


def _conversation_source(
    payload: Mapping[str, Any],
    *,
    conversation_reader: Reader | None = None,
) -> ExportSource:
    if conversation_reader is not None:
        return _conversation_store_source(payload, conversation_reader=conversation_reader)
    messages = _messages(payload)
    if not messages:
        return _conversation_store_source(payload, conversation_reader=conversation_reader)
    exportable = _exportable_messages(messages)
    if not exportable:
        return _reject(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_CONVERSATION)
    content = _render_messages(exportable)
    return _bounded_source(
        workspace_folder_exports.SOURCE_CONVERSATION,
        payload.get("conversation_id") or payload.get("source_id") or "conversation",
        payload.get("title") or "Conversation",
        content,
        counters={"message_count": len(exportable)},
    )


def _conversation_store_source(
    payload: Mapping[str, Any],
    *,
    conversation_reader: Reader | None = None,
) -> ExportSource:
    source_id = _clean_text(payload.get("conversation_id") or payload.get("source_id"))
    if not source_id:
        return _reject(workspace_folder_exports.REASON_SOURCE_MISSING, source_kind=workspace_folder_exports.SOURCE_CONVERSATION)
    reader = conversation_reader or _default_conversation_reader
    try:
        result = dict(reader(payload) or {})
    except Exception:
        return _reject(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_CONVERSATION, source_seed=source_id)
    if result.get("ok") is False:
        return _reject(_safe_reason(result.get("reason_code")), source_kind=workspace_folder_exports.SOURCE_CONVERSATION, source_seed=source_id)
    messages = _messages(result)
    exportable = _exportable_messages(messages)
    if not exportable:
        return _reject(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_CONVERSATION, source_seed=source_id)
    content = _render_messages(exportable)
    return _bounded_source(
        workspace_folder_exports.SOURCE_CONVERSATION,
        result.get("conversation_id") or source_id,
        result.get("title") or payload.get("title") or "Conversation",
        content,
        counters={"message_count": len(exportable)},
    )


def _message_selection_source(payload: Mapping[str, Any]) -> ExportSource:
    selected_ids = [_clean_text(value) for value in _sequence(payload.get("selected_message_ids"))]
    selected_ids = [value for value in selected_ids if value]
    if not selected_ids:
        return _reject(workspace_folder_exports.REASON_SOURCE_MISSING, source_kind=workspace_folder_exports.SOURCE_MESSAGE_SELECTION)
    if len(set(selected_ids)) != len(selected_ids):
        return _reject(workspace_folder_exports.REASON_SOURCE_AMBIGUOUS, source_kind=workspace_folder_exports.SOURCE_MESSAGE_SELECTION)

    exportable = _exportable_messages(_messages(payload))
    by_id: dict[str, dict[str, str]] = {}
    duplicated = False
    for message in exportable:
        message_id = message["id"]
        if message_id in by_id:
            duplicated = True
        by_id[message_id] = message
    if duplicated:
        return _reject(workspace_folder_exports.REASON_SOURCE_AMBIGUOUS, source_kind=workspace_folder_exports.SOURCE_MESSAGE_SELECTION)
    if any(message_id not in by_id for message_id in selected_ids):
        return _reject(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_MESSAGE_SELECTION)
    selected = [message for message in exportable if message["id"] in set(selected_ids)]
    if len(selected) != len(selected_ids):
        return _reject(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_MESSAGE_SELECTION)
    content = _render_messages(selected)
    return _bounded_source(
        workspace_folder_exports.SOURCE_MESSAGE_SELECTION,
        payload.get("selection_id") or ",".join(selected_ids),
        payload.get("title") or "Selection de messages",
        content,
        counters={"message_count": len(selected)},
    )


def _frida_response_source(payload: Mapping[str, Any]) -> ExportSource:
    response_id = _clean_text(
        payload.get("response_message_id") or payload.get("message_id") or payload.get("source_id")
    )
    if not response_id:
        return _reject(workspace_folder_exports.REASON_SOURCE_MISSING, source_kind=workspace_folder_exports.SOURCE_FRIDA_RESPONSE)
    matches = [
        message
        for message in _exportable_messages(_messages(payload))
        if message["id"] == response_id and message["role"] == "assistant"
    ]
    if len(matches) > 1:
        return _reject(workspace_folder_exports.REASON_SOURCE_AMBIGUOUS, source_kind=workspace_folder_exports.SOURCE_FRIDA_RESPONSE)
    if not matches:
        return _reject(workspace_folder_exports.REASON_SOURCE_UNAVAILABLE, source_kind=workspace_folder_exports.SOURCE_FRIDA_RESPONSE)
    return _bounded_source(
        workspace_folder_exports.SOURCE_FRIDA_RESPONSE,
        response_id,
        payload.get("title") or "Reponse de Frida",
        matches[0]["content"],
        counters={"message_count": 1},
    )


def _reader_source(
    payload: Mapping[str, Any],
    *,
    source_kind: str,
    reader: Reader | None,
    id_keys: tuple[str, ...],
    content_paths: tuple[tuple[str, ...], ...],
    missing_reader_reason: str = workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE,
) -> ExportSource:
    source_id = _first_text(payload, id_keys)
    if not source_id:
        return _reject(workspace_folder_exports.REASON_SOURCE_MISSING, source_kind=source_kind)
    if reader is None:
        return _reject(missing_reader_reason, source_kind=source_kind, source_seed=source_id)
    try:
        result = dict(reader(payload) or {})
    except Exception:
        return _reject(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE, source_kind=source_kind, source_seed=source_id)
    if result.get("ok") is False:
        return _reject(_safe_reason(result.get("reason_code")), source_kind=source_kind, source_seed=source_id)
    content = _first_path_text(result, content_paths)
    if not content:
        return _reject(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE, source_kind=source_kind, source_seed=source_id)
    return _bounded_source(
        source_kind,
        source_id,
        result.get("title") or payload.get("title") or _default_title(source_kind),
        content,
        counters={"source_count": 1},
    )


def _bounded_source(
    source_kind: str,
    source_seed: Any,
    title: Any,
    content: Any,
    *,
    counters: Mapping[str, int] | None = None,
) -> ExportSource:
    text = str(content or "")
    if len(text) > SOURCE_TEXT_MAX_CHARS:
        return _reject(
            workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE,
            source_kind=source_kind,
            source_seed=source_seed,
            counters={"char_count": len(text), **dict(counters or {})},
        )
    return ExportSource(
        ok=True,
        reason_code=workspace_folder_exports.REASON_LOOKUP_OK,
        source_kind=source_kind,
        source_ref=_source_ref(source_kind, source_seed),
        source_hash=workspace_folder_export_refs.hash12(text),
        title=workspace_folder_exports.sanitize_export_title(title) or _default_title(source_kind),
        content=text,
        char_count=len(text),
        counters={"char_count": len(text), **dict(counters or {})},
    )


def _reject(
    reason_code: str,
    *,
    source_kind: str = "",
    source_seed: Any = "",
    counters: Mapping[str, int] | None = None,
) -> ExportSource:
    kind = _source_kind(source_kind)
    return ExportSource(
        ok=False,
        reason_code=_safe_reason(reason_code),
        source_kind=kind,
        source_ref=_source_ref(kind, source_seed) if kind else "",
        counters=dict(counters or {}),
    )


def _messages(payload: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [dict(message) for message in _sequence(payload.get("messages") or payload.get("conversation_messages"))]


def _exportable_messages(messages: list[Mapping[str, Any]]) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for index, message in enumerate(messages):
        role = _clean_text(message.get("role")).lower()
        if role not in EXPORTABLE_MESSAGE_ROLES:
            continue
        content = _clean_multiline(message.get("content") or message.get("text"))
        if not content:
            continue
        message_id = _clean_text(message.get("id") or message.get("message_id") or f"message-{index}")
        items.append({"id": message_id, "role": role, "content": content})
    return items


def _render_messages(messages: list[dict[str, str]]) -> str:
    return "\n\n".join(
        f"## {_ROLE_LABELS[message['role']]}\n\n{message['content']}" for message in messages
    )


def _source_kind(value: Any) -> str:
    text = _clean_text(value).lower().replace("-", "_")
    text = _KIND_ALIASES.get(_clean_text(value).lower(), text)
    return workspace_folder_exports.normalize_source_kind(text)


def _source_ref(source_kind: str, source_seed: Any) -> str:
    prefix = _SOURCE_REF_PREFIX.get(source_kind, "")
    return workspace_folder_export_refs.build_source_ref(prefix, source_seed)


def _default_conversation_reader(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    from . import workspace_folder_export_conversation_store

    return workspace_folder_export_conversation_store.read_conversation_source(payload)


def _is_explicit(payload: Mapping[str, Any]) -> bool:
    return any(
        payload.get(key) is True
        for key in ("explicit", "explicit_source", "user_explicit", "user_action_confirmed")
    )


def _sequence(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return []


def _first_text(payload: Mapping[str, Any], keys: tuple[str, ...]) -> str:
    for key in keys:
        text = _clean_text(payload.get(key))
        if text:
            return text
    return ""


def _first_path_text(payload: Mapping[str, Any], paths: tuple[tuple[str, ...], ...]) -> str:
    for path in paths:
        value: Any = payload
        for key in path:
            if not isinstance(value, Mapping):
                value = None
                break
            value = value.get(key)
        text = _clean_multiline(value)
        if text:
            return text
    return ""


def _safe_reason(value: Any) -> str:
    text = _clean_text(value)
    if text in workspace_folder_exports.REASON_CODE_CATALOG:
        return text
    return workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE


def _default_title(source_kind: str) -> str:
    return {
        workspace_folder_exports.SOURCE_CONVERSATION: "Conversation",
        workspace_folder_exports.SOURCE_MESSAGE_SELECTION: "Selection de messages",
        workspace_folder_exports.SOURCE_FRIDA_RESPONSE: "Reponse de Frida",
        workspace_folder_exports.SOURCE_NOTE: "Note Markdown",
        workspace_folder_exports.SOURCE_DOCUMENT: "Document",
        workspace_folder_exports.SOURCE_EXPORT: "Export existant",
    }.get(source_kind, "Export")


def _clean_text(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _clean_multiline(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n").strip()
    return "\n".join(line.rstrip() for line in text.splitlines()).strip()
