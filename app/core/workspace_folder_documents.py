from __future__ import annotations

"""Documents V1 read-model projections over workspace files.

This module has no persistence and no Nextcloud transport. It separates the
user-facing projection, where a file display name is allowed, from technical
content-free projections used by logs, JSONL and observability.
"""

import hashlib
import re
import uuid
from typing import Any, Mapping


DOCUMENT_STATUS_AVAILABLE = "available"
DOCUMENT_STATUS_PREPARING = "preparing"
DOCUMENT_STATUS_READABLE = "readable"
DOCUMENT_STATUS_NOT_INJECTED = "not_injected"
DOCUMENT_STATUS_PDF_TEXT = "pdf_text"
DOCUMENT_STATUS_PDF_VISUAL_REQUIRED = "pdf_visual_required"
DOCUMENT_STATUS_VISUAL_READY = "visual_ready"
DOCUMENT_STATUS_TOO_LARGE = "too_large"
DOCUMENT_STATUS_UNSUPPORTED = "unsupported"
DOCUMENT_STATUS_ERROR = "error"
DOCUMENT_STATUS_DELETED = "deleted"
DOCUMENT_STATUS_UNAVAILABLE = "unavailable"

READINESS_READY = "ready"
READINESS_PENDING = "pending"
READINESS_BLOCKED = "blocked"
READINESS_VISUAL = "visual"
READINESS_UNAVAILABLE = "unavailable"

REASON_FOLDER_NOT_LINKED = "folder_document_folder_not_linked"
REASON_LIST_OK = "folder_document_list_ok"
REASON_TEXT_READY = "folder_document_text_ready"
REASON_PDF_TEXT_READY = "folder_document_pdf_text_ready"
REASON_PDF_VISUAL_REQUIRED = "folder_document_pdf_visual_required"
REASON_PDF_VISUAL_READY = "folder_document_pdf_visual_ready"
REASON_TOO_LARGE = "folder_document_too_large"
REASON_TYPE_UNSUPPORTED = "folder_document_type_unsupported"
REASON_PARSE_ERROR = "folder_document_parse_error"
REASON_RUNTIME_UNAVAILABLE = "folder_document_runtime_unavailable"
REASON_CONTENT_REDACTED = "folder_document_content_redacted"
REASON_SELECTED = "folder_document_selected"

FOLDER_SYNC_LINKED = "linked"
UNKNOWN = "unknown"

_SAFE_REASON_RE = re.compile(r"^[a-z0-9_]{3,120}$")
_SAFE_REASON_PREFIXES = (
    "folder_document_",
    "workspace_file_",
    "workspace_selection_",
)

_TECHNICAL_FORBIDDEN_KEYS = {
    "display_name",
    "original_filename",
    "filename",
    "storage_key",
    "internal_path",
    "path",
    "url",
    "dav_url",
    "href",
    "xml",
    "text",
    "text_content",
    "content",
    "raw",
    "payload",
    "binary_content",
    "image_content",
    "file_content",
    "secret",
    "token",
    "cookie",
    "authorization",
    "app_password",
    "app-password",
}
_ALLOWED_CONTENT_KINDS = {"document", "image"}
_ALLOWED_MEDIA_KINDS = {"text", "image"}
_ALLOWED_MIME_TYPES = {
    "application/pdf",
    "application/vnd.oasis.opendocument.text",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "image/gif",
    "image/jpeg",
    "image/png",
    "image/webp",
    "text/markdown",
    "text/plain",
}
_ALLOWED_SOURCE_EXTENSIONS = {
    ".docx",
    ".gif",
    ".jpeg",
    ".jpg",
    ".markdown",
    ".md",
    ".odt",
    ".pdf",
    ".png",
    ".txt",
    ".webp",
}
_ALLOWED_DOCUMENT_STATUSES = {
    DOCUMENT_STATUS_AVAILABLE,
    DOCUMENT_STATUS_PREPARING,
    DOCUMENT_STATUS_READABLE,
    DOCUMENT_STATUS_NOT_INJECTED,
    DOCUMENT_STATUS_PDF_TEXT,
    DOCUMENT_STATUS_PDF_VISUAL_REQUIRED,
    DOCUMENT_STATUS_VISUAL_READY,
    DOCUMENT_STATUS_TOO_LARGE,
    DOCUMENT_STATUS_UNSUPPORTED,
    DOCUMENT_STATUS_ERROR,
    DOCUMENT_STATUS_DELETED,
    DOCUMENT_STATUS_UNAVAILABLE,
}
_ALLOWED_READINESS = {
    READINESS_READY,
    READINESS_PENDING,
    READINESS_BLOCKED,
    READINESS_VISUAL,
    READINESS_UNAVAILABLE,
}


def apply_document_v1_projection(
    file_item: Mapping[str, Any] | None,
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    item = dict(file_item or {})
    if not item:
        return item
    user_projection = build_user_projection(item, folder=folder)
    technical_projection = build_technical_projection(item, folder=folder)
    item["document_v1_user"] = user_projection
    item["document_v1_technical"] = technical_projection
    item["document_v1_status"] = user_projection["document_status"]
    item["document_v1_readiness"] = user_projection["readiness"]
    item["document_v1_reason_code"] = user_projection["reason_code"]
    return item


def apply_document_v1_list(
    items: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    return [apply_document_v1_projection(item, folder=folder) for item in items]


def apply_selection_document_v1_projection(selection: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(selection or {})
    file_item = payload.get("file")
    if isinstance(file_item, Mapping):
        payload["file"] = apply_document_v1_projection(file_item)
    payload["document_v1_usage"] = build_usage_projection(payload)
    return payload


def build_user_projection(
    file_item: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = document_state(file_item, folder=folder)
    return {
        "document_id": _text(file_item.get("id"), 120),
        "workspace_file_id": _text(file_item.get("id"), 120),
        "workspace_folder_id": _text(file_item.get("workspace_folder_id"), 120),
        "display_name": _display_name(file_item),
        "content_kind": _text(file_item.get("content_kind"), 40) or "document",
        "media_kind": _text(file_item.get("media_kind"), 40) or "text",
        "mime_type": _text(file_item.get("mime_type"), 120),
        "source_extension": _text(file_item.get("source_extension"), 24),
        "byte_size": _safe_int(file_item.get("byte_size")),
        "document_status": state["document_status"],
        "readiness": state["readiness"],
        "reason_code": state["reason_code"],
        "created_at": _text(file_item.get("created_at"), 80),
        "updated_at": _text(file_item.get("updated_at"), 80),
        "deleted_at": _text(file_item.get("deleted_at"), 80),
    }


def build_technical_projection(
    file_item: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = document_state(file_item, folder=folder)
    payload = {
        "document_ref": _document_ref(file_item),
        "workspace_file_id": _safe_identifier(file_item.get("id")),
        "workspace_folder_id": _safe_identifier(file_item.get("workspace_folder_id")),
        "name_hash": _hash12(_display_name(file_item).casefold()),
        "content_kind": _normalized_content_kind(file_item.get("content_kind")),
        "media_kind": _normalized_media_kind(file_item.get("media_kind")),
        "mime_type": _normalized_mime_type(file_item.get("mime_type")),
        "source_extension": _normalized_source_extension(file_item.get("source_extension")),
        "byte_size": _safe_int(file_item.get("byte_size")),
        "sha256_12": _short_hash(file_item.get("sha256_12")),
        "text_sha256_12": _short_hash(file_item.get("text_sha256_12")),
        "image_width": _safe_int(file_item.get("image_width")),
        "image_height": _safe_int(file_item.get("image_height")),
        "document_status": _normalized_document_status(state["document_status"]),
        "readiness": _normalized_readiness(state["readiness"]),
        "reason_code": _safe_reason_code(state["reason_code"]),
    }
    return _content_free_projection(payload)


def build_usage_projection(selection: Mapping[str, Any]) -> dict[str, Any]:
    selected = bool(selection.get("selected"))
    selection_status = _text(selection.get("selection_status"), 80) or "unknown"
    reason = _safe_reason_code(selection.get("reason_code"), fallback="")
    return {
        "source": "workspace_file_selection",
        "conversation_id": _text(selection.get("conversation_id"), 120),
        "workspace_file_id": _text(selection.get("workspace_file_id"), 120),
        "workspace_folder_id": _text(selection.get("workspace_folder_id"), 120),
        "selected": selected,
        "usage_status": "selected" if selected and selection_status == "selected" else DOCUMENT_STATUS_NOT_INJECTED,
        "selection_status": selection_status,
        "reason_code": reason or (REASON_SELECTED if selected else REASON_CONTENT_REDACTED),
        "last_injected_turn_id": _text(selection.get("last_injected_turn_id"), 160),
        "last_excluded_turn_id": _text(selection.get("last_excluded_turn_id"), 160),
        "last_excluded_reason_code": _text(selection.get("last_excluded_reason_code"), 120),
    }


def document_state(
    file_item: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if folder is not None and _text(folder.get("nextcloud_sync_state"), 80) != FOLDER_SYNC_LINKED:
        return _state(DOCUMENT_STATUS_UNAVAILABLE, READINESS_BLOCKED, REASON_FOLDER_NOT_LINKED)

    status = _text(file_item.get("status"), 80)
    reason = _text(file_item.get("reason_code"), 120)
    if file_item.get("deleted_at") or status == "deleted":
        return _state(
            DOCUMENT_STATUS_DELETED,
            READINESS_UNAVAILABLE,
            _safe_reason_code(reason or "workspace_file_deleted"),
        )
    if status == "disk_missing":
        return _state(DOCUMENT_STATUS_UNAVAILABLE, READINESS_UNAVAILABLE, REASON_RUNTIME_UNAVAILABLE)
    if status in {"too_large", "workspace_file_too_large"} or reason == "workspace_file_too_large":
        return _state(DOCUMENT_STATUS_TOO_LARGE, READINESS_BLOCKED, REASON_TOO_LARGE)
    if status == "parse_error" or reason == "workspace_file_unreadable":
        return _state(DOCUMENT_STATUS_ERROR, READINESS_BLOCKED, REASON_PARSE_ERROR)
    if status == "unsupported" or reason == "workspace_file_type_unsupported":
        return _state(DOCUMENT_STATUS_UNSUPPORTED, READINESS_BLOCKED, REASON_TYPE_UNSUPPORTED)
    if status == "ocr_required":
        if _is_pdf(file_item):
            return _state(DOCUMENT_STATUS_PDF_VISUAL_REQUIRED, READINESS_VISUAL, REASON_PDF_VISUAL_REQUIRED)
        return _state(DOCUMENT_STATUS_UNAVAILABLE, READINESS_BLOCKED, REASON_RUNTIME_UNAVAILABLE)

    if _normalized_media_kind(file_item.get("media_kind")) == "image":
        return _state(DOCUMENT_STATUS_VISUAL_READY, READINESS_VISUAL, REASON_PDF_VISUAL_READY)
    if _is_pdf(file_item) and _safe_int(file_item.get("text_chars")) > 0:
        return _state(DOCUMENT_STATUS_PDF_TEXT, READINESS_READY, REASON_PDF_TEXT_READY)
    if _safe_int(file_item.get("text_chars")) > 0 or _text(file_item.get("text_sha256_12"), 12):
        return _state(DOCUMENT_STATUS_READABLE, READINESS_READY, REASON_TEXT_READY)
    return _state(DOCUMENT_STATUS_AVAILABLE, READINESS_PENDING, REASON_LIST_OK)


def _state(document_status: str, readiness: str, reason_code: str) -> dict[str, str]:
    return {
        "document_status": document_status,
        "readiness": readiness,
        "reason_code": reason_code,
    }


def _is_pdf(file_item: Mapping[str, Any]) -> bool:
    mime_type = _normalized_mime_type(file_item.get("mime_type"))
    extension = _normalized_source_extension(file_item.get("source_extension"))
    return mime_type == "application/pdf" or extension == ".pdf"


def _document_ref(file_item: Mapping[str, Any]) -> str:
    file_id = _safe_identifier(file_item.get("id"))
    if not file_id:
        return f"workspace-file:redacted:{_hash12(file_item.get('id'))}"
    digest = _short_hash(file_item.get("sha256_12")) or _hash12(file_id)
    return f"workspace-file:{file_id[:8]}:{digest}"


def _content_free_projection(payload: Mapping[str, Any]) -> dict[str, Any]:
    safe: dict[str, Any] = {}
    for key, value in payload.items():
        normalized = str(key or "").strip()
        if normalized.lower() in _TECHNICAL_FORBIDDEN_KEYS:
            continue
        safe[normalized] = value
    return safe


def _safe_reason_code(value: Any, *, fallback: str = REASON_CONTENT_REDACTED) -> str:
    reason = _text(value, 120)
    if not reason:
        return fallback
    if _SAFE_REASON_RE.fullmatch(reason) and reason.startswith(_SAFE_REASON_PREFIXES):
        return reason
    return fallback


def _safe_identifier(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value or "").strip()))
    except (TypeError, ValueError):
        return ""


def _normalized_content_kind(value: Any) -> str:
    text = _text(value, 40).casefold()
    return text if text in _ALLOWED_CONTENT_KINDS else UNKNOWN


def _normalized_media_kind(value: Any) -> str:
    text = _text(value, 40).casefold()
    return text if text in _ALLOWED_MEDIA_KINDS else UNKNOWN


def _normalized_mime_type(value: Any) -> str:
    text = _text(value, 120).casefold()
    return text if text in _ALLOWED_MIME_TYPES else UNKNOWN


def _normalized_source_extension(value: Any) -> str:
    text = _text(value, 24).casefold()
    if text and not text.startswith("."):
        text = f".{text}"
    return text if text in _ALLOWED_SOURCE_EXTENSIONS else ""


def _normalized_document_status(value: Any) -> str:
    text = _text(value, 80)
    return text if text in _ALLOWED_DOCUMENT_STATUSES else DOCUMENT_STATUS_ERROR


def _normalized_readiness(value: Any) -> str:
    text = _text(value, 80)
    return text if text in _ALLOWED_READINESS else READINESS_BLOCKED


def _display_name(file_item: Mapping[str, Any]) -> str:
    return _text(file_item.get("display_name"), 180) or "fichier"


def _short_hash(value: Any) -> str:
    text = _text(value, 12)
    if len(text) == 12 and all(ch in "0123456789abcdef" for ch in text.lower()):
        return text.lower()
    return ""


def _hash12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _text(value: Any, max_chars: int) -> str:
    text = str(value or "").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text
