from __future__ import annotations

"""HTTP-facing service for active conversation document uploads.

This module bridges Flask request objects to the active document state and text
extractor. It intentionally returns content-free payloads: the extracted text is
stored server-side for the prompt lane, but never returned to the chat UI.
"""

from typing import Any, Mapping, Tuple

from . import active_conversation_documents
from . import active_document_text_extraction
from observability import active_documents_observability


UPLOAD_FIELD = "file"


def list_active_documents_response(
    conversation_id: str,
    *,
    conv_store_module: Any,
    active_documents_module: Any = active_conversation_documents,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_existing_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error

    items = active_documents_module.list_active_documents(conv_id)
    return {"ok": True, "conversation_id": conv_id, "items": items}, 200


def upload_active_document_response(
    conversation_id: str,
    files: Mapping[str, Any],
    *,
    conv_store_module: Any,
    active_documents_module: Any = active_conversation_documents,
    extractor_module: Any = active_document_text_extraction,
    admin_logs_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_existing_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error

    file_obj = _first_upload_file(files)
    if file_obj is None:
        return {
            "ok": False,
            "error": "fichier requis",
            "reason_code": "document_file_missing",
        }, 400

    filename = str(getattr(file_obj, "filename", "") or "document").strip() or "document"
    media_type = str(getattr(file_obj, "mimetype", "") or "").strip()
    try:
        content = bytes(file_obj.read() or b"")
    except Exception:
        active_documents_observability.log_activation_failure(
            admin_logs_module,
            conversation_id=conv_id,
            extraction={
                "filename": filename,
                "media_type": media_type,
                "status": "parse_error",
                "reason_code": "document_parse_error",
            },
        )
        return {
            "ok": False,
            "error": "lecture du fichier impossible",
            "reason_code": "document_parse_error",
            "document": {
                "filename": filename,
                "media_type": media_type,
                "status": "parse_error",
                "reason_code": "document_parse_error",
            },
        }, 400

    extraction = extractor_module.extract_active_document_text(
        content,
        filename=filename,
        media_type=media_type,
    )
    extraction_meta = _content_free_extraction(extraction)
    if extraction.status != extractor_module.STATUS_COMPLETE:
        active_documents_observability.log_activation_failure(
            admin_logs_module,
            conversation_id=conv_id,
            extraction=extraction_meta,
        )
        return {
            "ok": False,
            "error": _human_upload_error(extraction.reason_code),
            "reason_code": extraction.reason_code,
            "document": extraction_meta,
        }, 422

    document = active_documents_module.activate_document(
        conv_id,
        filename=extraction.filename,
        text_content=extraction.text,
        media_type=extraction.media_type,
        source_extension=extraction.source_extension,
        byte_size=extraction.bytes,
        token_estimate=extraction.token_estimate,
    )
    if not document:
        return {
            "ok": False,
            "error": "activation du document impossible",
            "reason_code": "document_runtime_unavailable",
        }, 503

    active_documents_observability.log_activation_success(
        admin_logs_module,
        conversation_id=conv_id,
        document=document,
    )
    return {"ok": True, "conversation_id": conv_id, "document": document}, 201


def remove_active_document_response(
    conversation_id: str,
    document_id: str,
    *,
    conv_store_module: Any,
    active_documents_module: Any = active_conversation_documents,
    admin_logs_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_existing_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error

    removed = active_documents_module.deactivate_document(
        conv_id,
        str(document_id or ""),
        reason_code=active_documents_module.DEFAULT_REMOVE_REASON,
    )
    if not removed:
        return {
            "ok": False,
            "error": "document actif introuvable",
            "reason_code": "document_not_found",
        }, 404
    active_documents_observability.log_manual_remove(
        admin_logs_module,
        conversation_id=conv_id,
        document_id=str(document_id or ""),
        reason_code=active_documents_module.DEFAULT_REMOVE_REASON,
    )
    return {"ok": True, "conversation_id": conv_id, "document_id": str(document_id or "")}, 200


def _resolve_existing_conversation(
    conversation_id: str,
    *,
    conv_store_module: Any,
) -> Tuple[str, Tuple[dict[str, Any], int] | None]:
    conv_id = conv_store_module.normalize_conversation_id(conversation_id)
    if not conv_id:
        return "", ({"ok": False, "error": "conversation_id invalide"}, 400)

    if not conv_store_module.read_conversation(conv_id, ""):
        return "", ({"ok": False, "error": "conversation introuvable"}, 404)
    return conv_id, None


def _first_upload_file(files: Mapping[str, Any]) -> Any | None:
    if not files:
        return None
    getlist = getattr(files, "getlist", None)
    if callable(getlist):
        values = [item for item in getlist(UPLOAD_FIELD) if item is not None]
        if values:
            return values[0]
    getter = getattr(files, "get", None)
    if callable(getter):
        return getter(UPLOAD_FIELD)
    return None


def _content_free_extraction(extraction: Any) -> dict[str, Any]:
    data = extraction.to_dict() if hasattr(extraction, "to_dict") else dict(extraction or {})
    data.pop("text", None)
    return {
        key: value
        for key, value in data.items()
        if key not in {"text_content", "content", "raw", "payload"}
    }


def _human_upload_error(reason_code: str) -> str:
    labels = {
        "document_type_unsupported": "format non pris en charge",
        "document_parse_error": "lecture du fichier impossible",
        "document_empty_text": "aucun texte lisible dans ce fichier",
        "document_ocr_required": "ce PDF demande un OCR, hors scope de ce chantier",
        "document_runtime_unavailable": "lecteur de fichier indisponible",
    }
    return labels.get(str(reason_code or ""), "document non activable")
