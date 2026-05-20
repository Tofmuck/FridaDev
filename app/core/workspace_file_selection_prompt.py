from __future__ import annotations

"""Prompt-time conversion for selected workspace files."""

from pathlib import Path
from typing import Any, Callable, Mapping

from . import active_document_text_extraction
from . import workspace_file_selections_store as selections_store
from . import workspace_files_store


def list_selected_files_for_prompt(
    conversation_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
    extractor_module: Any = active_document_text_extraction,
) -> list[dict[str, Any]]:
    conv_id = selections_store._normalize_uuid(conversation_id)
    if not conv_id:
        return []
    documents: list[dict[str, Any]] = []
    for row in selections_store._read_selection_rows(conv_id, db_conn_func=db_conn_func):
        selection = selections_store._serialize_selection_row(row, storage_root=storage_root, include_disk_status=True)
        if not selection:
            continue
        reason_code = selections_store._text(selection.get("reason_code"), 120)
        if reason_code:
            documents.append(_non_injectable_prompt_document(selection, reason_code=reason_code))
            _log_prompt_exclusion(logger, selection, reason_code=reason_code)
            continue
        if selections_store._text(row.get("file_status"), 80) == workspace_files_store.STATUS_OCR_REQUIRED:
            documents.append(
                _non_injectable_prompt_document(selection, reason_code=selections_store.REASON_OCR_REQUIRED)
            )
            _log_prompt_exclusion(logger, selection, reason_code=selections_store.REASON_OCR_REQUIRED)
            continue
        documents.append(
            _injectable_prompt_document(
                row,
                selection=selection,
                storage_root=storage_root,
                logger=logger,
                extractor_module=extractor_module,
            )
        )
    return documents


def _injectable_prompt_document(
    row: Mapping[str, Any],
    *,
    selection: Mapping[str, Any],
    storage_root: Path,
    logger: Any,
    extractor_module: Any,
) -> dict[str, Any]:
    file_item = dict(selection.get("file") or {})
    storage_key = selections_store._text(row.get("storage_key"), 500)
    try:
        data = workspace_files_store.workspace_file_path(storage_root, storage_key).read_bytes()
    except Exception:
        _log_prompt_exclusion(logger, selection, reason_code=selections_store.REASON_DISK_MISSING)
        return _non_injectable_prompt_document(selection, reason_code=selections_store.REASON_DISK_MISSING)

    if selections_store._text(file_item.get("media_kind"), 40) == workspace_files_store.MEDIA_KIND_IMAGE:
        return {
            **_base_prompt_document(selection),
            "media_kind": workspace_files_store.MEDIA_KIND_IMAGE,
            "content_sha256_12": selections_store._text(file_item.get("sha256_12"), 12),
            "image_width": selections_store._safe_int(file_item.get("image_width")),
            "image_height": selections_store._safe_int(file_item.get("image_height")),
            "image_content": data,
            "injectable": True,
        }

    extraction = extractor_module.extract_active_document_text(
        data,
        filename=selections_store._text(file_item.get("display_name"), 500) or "fichier",
        media_type=selections_store._text(file_item.get("mime_type"), 120),
    )
    if extraction.status != extractor_module.STATUS_COMPLETE:
        reason = _map_extraction_reason(extraction.reason_code, extractor_module=extractor_module)
        _log_prompt_exclusion(logger, selection, reason_code=reason)
        return _non_injectable_prompt_document(selection, reason_code=reason)

    extracted = extraction.to_dict()
    return {
        **_base_prompt_document(selection),
        "media_kind": workspace_files_store.MEDIA_KIND_TEXT,
        "text_chars": selections_store._safe_int(extracted.get("text_chars")),
        "token_estimate": selections_store._safe_int(extracted.get("token_estimate")),
        "text_sha256_12": selections_store._text(extracted.get("text_sha256_12"), 12),
        "text_content": str(extracted.get("text") or ""),
        "injectable": True,
    }


def _map_extraction_reason(reason_code: str, *, extractor_module: Any) -> str:
    reason = selections_store._text(reason_code, 120)
    if reason == getattr(extractor_module, "REASON_OCR_REQUIRED", "document_ocr_required"):
        return selections_store.REASON_OCR_REQUIRED
    if reason == getattr(extractor_module, "REASON_UNSUPPORTED", "document_type_unsupported"):
        return selections_store.REASON_TYPE_UNSUPPORTED
    return selections_store.REASON_UNREADABLE


def _base_prompt_document(selection: Mapping[str, Any]) -> dict[str, Any]:
    file_item = dict(selection.get("file") or {})
    return {
        "source": selections_store.SOURCE,
        "document_id": selections_store._text(selection.get("workspace_file_id"), 120),
        "workspace_file_id": selections_store._text(selection.get("workspace_file_id"), 120),
        "workspace_folder_id": selections_store._text(selection.get("workspace_folder_id"), 120),
        "conversation_id": selections_store._text(selection.get("conversation_id"), 120),
        "filename": selections_store._text(file_item.get("display_name"), 500) or "fichier",
        "media_type": selections_store._text(file_item.get("mime_type"), 120),
        "source_extension": selections_store._text(file_item.get("source_extension"), 40),
        "byte_size": selections_store._safe_int(file_item.get("byte_size")),
        "text_chars": selections_store._safe_int(file_item.get("text_chars")),
        "text_sha256_12": selections_store._text(file_item.get("text_sha256_12"), 12),
        "content_sha256_12": selections_store._text(file_item.get("sha256_12"), 12),
        "image_width": selections_store._safe_int(file_item.get("image_width")),
        "image_height": selections_store._safe_int(file_item.get("image_height")),
        "created_at": selections_store._text(selection.get("selected_at"), 80),
        "selection_status": selections_store._text(selection.get("selection_status"), 80),
    }


def _non_injectable_prompt_document(selection: Mapping[str, Any], *, reason_code: str) -> dict[str, Any]:
    return {
        **_base_prompt_document(selection),
        "media_kind": selections_store._text((selection.get("file") or {}).get("media_kind"), 40)
        or workspace_files_store.MEDIA_KIND_TEXT,
        "injectable": False,
        "reason_code": selections_store._text(reason_code, 120) or selections_store.REASON_UNREADABLE,
    }


def _log_prompt_exclusion(logger: Any, selection: Mapping[str, Any], *, reason_code: str) -> None:
    file_item = dict(selection.get("file") or {})
    workspace_files_store.log_content_free_event(
        logger,
        "selection_prompt_excluded",
        level="warning",
        conversation_id=selection.get("conversation_id"),
        folder_id=selection.get("workspace_folder_id"),
        file_id=selection.get("workspace_file_id"),
        media_kind=file_item.get("media_kind"),
        content_kind=file_item.get("content_kind"),
        mime_type=file_item.get("mime_type"),
        byte_size=file_item.get("byte_size"),
        image_width=file_item.get("image_width"),
        image_height=file_item.get("image_height"),
        sha256_12=file_item.get("sha256_12"),
        selection_status=selection.get("selection_status"),
        reason_code=reason_code,
    )
