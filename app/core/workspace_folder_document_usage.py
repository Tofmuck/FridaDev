from __future__ import annotations

"""Conversation usage projection for Documents V1 workspace files."""

import re
from typing import Any, Mapping


DOCUMENT_STATUS_NOT_INJECTED = "not_injected"
DOCUMENT_STATUS_READABLE = "readable"
DOCUMENT_STATUS_PDF_VISUAL_REQUIRED = "pdf_visual_required"
DOCUMENT_STATUS_VISUAL_READY = "visual_ready"
DOCUMENT_STATUS_TOO_LARGE = "too_large"
DOCUMENT_STATUS_UNSUPPORTED = "unsupported"
DOCUMENT_STATUS_UNAVAILABLE = "unavailable"

READINESS_READY = "ready"
READINESS_PENDING = "pending"
READINESS_BLOCKED = "blocked"
READINESS_VISUAL = "visual"

REASON_TEXT_READY = "folder_document_text_ready"
REASON_PDF_VISUAL_REQUIRED = "folder_document_pdf_visual_required"
REASON_PDF_VISUAL_READY = "folder_document_pdf_visual_ready"
REASON_TOO_LARGE = "folder_document_too_large"
REASON_TYPE_UNSUPPORTED = "folder_document_type_unsupported"
REASON_RUNTIME_UNAVAILABLE = "folder_document_runtime_unavailable"
REASON_CONTENT_REDACTED = "folder_document_content_redacted"
REASON_SELECTED = "folder_document_selected"

_SAFE_REASON_RE = re.compile(r"^[a-z0-9_]{3,120}$")
_SAFE_REASON_PREFIXES = (
    "folder_document_",
    "workspace_file_",
    "workspace_selection_",
)


def build_usage_projection(selection: Mapping[str, Any]) -> dict[str, Any]:
    selected = bool(selection.get("selected"))
    selection_status = _text(selection.get("selection_status"), 80) or "unknown"
    reason = _safe_reason_code(selection.get("reason_code"), fallback="")
    last_excluded_reason = _safe_reason_code(selection.get("last_excluded_reason_code"), fallback="")
    usage_status = DOCUMENT_STATUS_NOT_INJECTED
    readiness = READINESS_BLOCKED
    usage_reason = reason or REASON_CONTENT_REDACTED
    if selected and selection_status == "selected":
        usage_status = "selected"
        readiness = READINESS_PENDING
        usage_reason = REASON_SELECTED
    if selected and _text(selection.get("last_injected_turn_id"), 160):
        if _is_visual_selection(selection):
            usage_status = DOCUMENT_STATUS_VISUAL_READY
            readiness = READINESS_VISUAL
            usage_reason = REASON_PDF_VISUAL_READY
        else:
            usage_status = DOCUMENT_STATUS_READABLE
            readiness = READINESS_READY
            usage_reason = REASON_TEXT_READY
    elif last_excluded_reason:
        usage_reason = last_excluded_reason
        readiness = READINESS_BLOCKED
        if last_excluded_reason in {
            REASON_PDF_VISUAL_REQUIRED,
            "workspace_file_model_unsupported",
            "workspace_file_pdf_visual_model_unsupported",
        }:
            usage_status = DOCUMENT_STATUS_PDF_VISUAL_REQUIRED
            readiness = READINESS_VISUAL
        elif last_excluded_reason in {
            "workspace_file_too_large",
            "workspace_file_pdf_visual_too_large",
            "folder_document_too_many_pages",
            REASON_TOO_LARGE,
        }:
            usage_status = DOCUMENT_STATUS_TOO_LARGE
        elif last_excluded_reason in {
            "workspace_file_missing",
            "workspace_file_deleted",
            "workspace_file_disk_missing",
            "workspace_file_unreadable",
            "workspace_file_pdf_visual_bytes_missing",
            "workspace_file_pdf_visual_page_count_failed",
            REASON_RUNTIME_UNAVAILABLE,
        }:
            usage_status = DOCUMENT_STATUS_UNAVAILABLE
        elif last_excluded_reason in {"workspace_file_type_unsupported", REASON_TYPE_UNSUPPORTED}:
            usage_status = DOCUMENT_STATUS_UNSUPPORTED
    return {
        "source": "workspace_file_selection",
        "conversation_id": _text(selection.get("conversation_id"), 120),
        "workspace_file_id": _text(selection.get("workspace_file_id"), 120),
        "workspace_folder_id": _text(selection.get("workspace_folder_id"), 120),
        "selected": selected,
        "usage_status": usage_status,
        "readiness": readiness,
        "selection_status": selection_status,
        "reason_code": usage_reason,
        "last_injected_turn_id": _text(selection.get("last_injected_turn_id"), 160),
        "last_excluded_turn_id": _text(selection.get("last_excluded_turn_id"), 160),
        "last_excluded_reason_code": last_excluded_reason,
    }


def _is_visual_selection(selection: Mapping[str, Any]) -> bool:
    file_item = selection.get("file")
    if not isinstance(file_item, Mapping):
        return False
    media_kind = _text(file_item.get("media_kind"), 40)
    if media_kind == "image":
        return True
    mime_type = _text(file_item.get("mime_type"), 120).casefold()
    extension = _text(file_item.get("source_extension"), 40).casefold()
    status = _text(file_item.get("status"), 80)
    if (mime_type == "application/pdf" or extension == ".pdf") and status == "ocr_required":
        return True
    return False


def _safe_reason_code(value: Any, *, fallback: str = REASON_CONTENT_REDACTED) -> str:
    reason = _text(value, 120)
    if not reason:
        return fallback
    if _SAFE_REASON_RE.fullmatch(reason) and reason.startswith(_SAFE_REASON_PREFIXES):
        return reason
    return fallback


def _text(value: Any, max_chars: int) -> str:
    text = str(value or "").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text
