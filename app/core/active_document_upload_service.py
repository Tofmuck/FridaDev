from __future__ import annotations

"""HTTP-facing service for active conversation document uploads.

This module bridges Flask request objects to the active document state and text
extractor. It intentionally returns content-free payloads: the extracted text is
stored server-side for the prompt lane, but never returned to the chat UI.
"""

from typing import Any, Mapping, Tuple

from . import active_conversation_documents
from . import active_document_image_validation
from . import active_document_ocr_client
from . import active_document_text_extraction
from . import active_document_visual_limits
from . import document_upload_reader
from observability import active_documents_observability


UPLOAD_FIELD = "file"
ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH = 40 * 1024 * 1024
REASON_UPLOAD_BODY_TOO_LARGE = "active_document_upload_too_large"
REASON_FILE_TOO_MANY_PAGES_FOR_PROVIDER_PAYLOAD = "file_too_many_pages_for_provider_payload"
REASON_FILE_PAGE_COUNT_FAILED = "file_page_count_failed"


def upload_body_size_guard_response(content_length: Any) -> Tuple[dict[str, Any], int] | None:
    """Reject obviously oversized multipart bodies before Flask parses files."""

    try:
        body_size = int(content_length)
    except (TypeError, ValueError):
        return None
    if body_size <= ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH:
        return None
    return upload_body_too_large_response(body_size)


def upload_body_too_large_response(content_length: Any = None) -> Tuple[dict[str, Any], int]:
    document = {
        "status": "too_large",
        "reason_code": REASON_UPLOAD_BODY_TOO_LARGE,
        "max_body_bytes": ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH,
    }
    try:
        body_size = int(content_length)
    except (TypeError, ValueError):
        body_size = None
    if body_size is not None and body_size >= 0:
        document["byte_size"] = body_size
    return {
        "ok": False,
        "error": _human_upload_error(REASON_UPLOAD_BODY_TOO_LARGE),
        "reason_code": REASON_UPLOAD_BODY_TOO_LARGE,
        "document": document,
    }, 413


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
    ocr_module: Any = active_document_ocr_client,
    visual_limits_module: Any = active_document_visual_limits,
    admin_logs_module: Any = None,
    pdf_visual_fallback_enabled: bool = True,
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
        content = document_upload_reader.read_document_upload_bytes(
            file_obj,
            max_bytes=ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH,
        )
    except document_upload_reader.DocumentUploadTooLargeError as exc:
        failure = {
            "filename": filename,
            "media_type": media_type,
            "status": "too_large",
            "reason_code": REASON_UPLOAD_BODY_TOO_LARGE,
            "byte_size": exc.observed_bytes,
            "max_file_bytes": exc.max_bytes,
        }
        active_documents_observability.log_activation_failure(
            admin_logs_module,
            conversation_id=conv_id,
            extraction=failure,
        )
        return {
            "ok": False,
            "error": _human_upload_error(REASON_UPLOAD_BODY_TOO_LARGE),
            "reason_code": REASON_UPLOAD_BODY_TOO_LARGE,
            "document": failure,
        }, 413
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

    image_validation = active_document_image_validation.validate_active_image_upload(
        content,
        filename=filename,
        declared_media_type=media_type,
    )
    if image_validation.is_image_candidate:
        return _upload_image_response(
            conv_id,
            content,
            image_validation=image_validation,
            active_documents_module=active_documents_module,
            admin_logs_module=admin_logs_module,
        )

    ocr_success_meta: dict[str, Any] = {}
    extraction = extractor_module.extract_active_document_text(
        content,
        filename=filename,
        media_type=media_type,
    )
    if _should_attempt_ocr(extraction, extractor_module):
        if pdf_visual_fallback_enabled and _is_pdf_visual_candidate(extraction, filename=filename, media_type=media_type):
            return _upload_pdf_visual_response(
                conv_id,
                content,
                extraction=extraction,
                active_documents_module=active_documents_module,
                visual_limits_module=visual_limits_module,
                admin_logs_module=admin_logs_module,
            )
        extraction, ocr_failure_meta, ocr_success_meta = _extract_after_ocr(
            content,
            filename=filename,
            media_type=media_type,
            initial_extraction=extraction,
            extractor_module=extractor_module,
            ocr_module=ocr_module,
        )
        if ocr_failure_meta is not None:
            active_documents_observability.log_activation_failure(
                admin_logs_module,
                conversation_id=conv_id,
                extraction=ocr_failure_meta,
            )
            return {
                "ok": False,
                "error": _human_upload_error(str(ocr_failure_meta.get("reason_code") or "")),
                "reason_code": str(ocr_failure_meta.get("reason_code") or ""),
                "document": ocr_failure_meta,
            }, 422

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
        byte_size=len(content),
        token_estimate=extraction.token_estimate,
        **_activation_ocr_kwargs(ocr_success_meta),
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


def _upload_image_response(
    conversation_id: str,
    content: bytes,
    *,
    image_validation: Any,
    active_documents_module: Any,
    admin_logs_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    image_meta = image_validation.to_dict()
    if image_validation.status != active_document_image_validation.STATUS_COMPLETE:
        active_documents_observability.log_activation_failure(
            admin_logs_module,
            conversation_id=conversation_id,
            extraction=image_meta,
        )
        return {
            "ok": False,
            "error": _human_upload_error(image_validation.reason_code),
            "reason_code": image_validation.reason_code,
            "document": image_meta,
        }, 422

    document = active_documents_module.activate_image_document(
        conversation_id,
        filename=image_validation.filename,
        image_content=content,
        media_type=image_validation.media_type,
        source_extension=image_validation.source_extension,
        byte_size=image_validation.byte_size,
        image_width=image_validation.image_width,
        image_height=image_validation.image_height,
        content_sha256_12=image_validation.content_sha256_12,
    )
    if not document:
        return {
            "ok": False,
            "error": "activation de l'image impossible",
            "reason_code": "image_runtime_unavailable",
        }, 503

    active_documents_observability.log_activation_success(
        admin_logs_module,
        conversation_id=conversation_id,
        document=document,
    )
    return {"ok": True, "conversation_id": conversation_id, "document": document}, 201


def _upload_pdf_visual_response(
    conversation_id: str,
    content: bytes,
    *,
    extraction: Any,
    active_documents_module: Any,
    visual_limits_module: Any,
    admin_logs_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    visual_page_check = visual_limits_module.check_pdf_visual_pages(content)
    if not getattr(visual_page_check, "ok", False):
        reason_code = _upload_visual_page_reason(getattr(visual_page_check, "reason_code", ""))
        failure = _content_free_extraction(extraction)
        failure.update(
            {
                "status": "too_large" if reason_code == REASON_FILE_TOO_MANY_PAGES_FOR_PROVIDER_PAYLOAD else "parse_error",
                "reason_code": reason_code,
                "byte_size": len(content),
                "page_count": _safe_int(getattr(visual_page_check, "page_count", 0)),
                "max_pages": _safe_int(getattr(visual_page_check, "max_pages", 0)),
                "media_kind": "file",
                "visual_fallback": True,
            }
        )
        active_documents_observability.log_activation_failure(
            admin_logs_module,
            conversation_id=conversation_id,
            extraction=failure,
        )
        return {
            "ok": False,
            "error": _human_upload_error(reason_code),
            "reason_code": reason_code,
            "document": failure,
        }, 422

    document = active_documents_module.activate_file_document(
        conversation_id,
        filename=str(getattr(extraction, "filename", "") or "document.pdf"),
        file_content=content,
        media_type=str(getattr(extraction, "media_type", "") or "application/pdf"),
        source_extension=str(getattr(extraction, "source_extension", "") or ".pdf"),
        byte_size=len(content),
    )
    if not document:
        return {
            "ok": False,
            "error": "activation du PDF visuel impossible",
            "reason_code": "file_runtime_unavailable",
        }, 503

    active_documents_observability.log_activation_success(
        admin_logs_module,
        conversation_id=conversation_id,
        document=document,
    )
    return {"ok": True, "conversation_id": conversation_id, "document": document}, 201


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


def _should_attempt_ocr(extraction: Any, extractor_module: Any) -> bool:
    return (
        str(getattr(extraction, "status", "") or "") == str(getattr(extractor_module, "STATUS_OCR_REQUIRED", ""))
        and str(getattr(extraction, "reason_code", "") or "") == str(getattr(extractor_module, "REASON_OCR_REQUIRED", ""))
    )


def _is_pdf_visual_candidate(extraction: Any, *, filename: str, media_type: str) -> bool:
    source_extension = str(getattr(extraction, "source_extension", "") or "").strip().lower()
    extracted_media_type = str(getattr(extraction, "media_type", "") or "").strip().lower()
    parser = str(getattr(extraction, "parser", "") or "").strip().lower()
    name = str(getattr(extraction, "filename", "") or filename or "").strip().lower()
    declared_media_type = str(media_type or "").strip().lower()
    return (
        source_extension == ".pdf"
        or extracted_media_type == "application/pdf"
        or declared_media_type == "application/pdf"
        or parser == "pdf"
        or name.endswith(".pdf")
    )


def _extract_after_ocr(
    content: bytes,
    *,
    filename: str,
    media_type: str,
    initial_extraction: Any,
    extractor_module: Any,
    ocr_module: Any,
) -> tuple[Any, dict[str, Any] | None, dict[str, Any]]:
    try:
        ocr_result = ocr_module.ocr_pdf_with_stirling(
            content,
            filename=filename,
        )
    except Exception as exc:
        failure = _content_free_extraction(initial_extraction)
        failure.update(
            {
                "status": "ocr_failed",
                "reason_code": "document_ocr_failed",
                "warnings": [type(exc).__name__],
            }
        )
        return initial_extraction, failure, {}
    ocr_meta = _content_free_ocr_result(ocr_result)
    if str(getattr(ocr_result, "status", "") or "") != str(getattr(ocr_module, "STATUS_COMPLETE", "complete")):
        failure = _content_free_extraction(initial_extraction)
        failure.update(ocr_meta)
        failure["status"] = "ocr_failed"
        failure["reason_code"] = str(getattr(ocr_result, "reason_code", "") or "document_ocr_failed")
        return initial_extraction, failure, {}

    final_extraction = extractor_module.extract_active_document_text(
        bytes(getattr(ocr_result, "ocr_pdf", b"") or b""),
        filename=filename,
        media_type="application/pdf",
    )
    if final_extraction.status == extractor_module.STATUS_COMPLETE:
        return final_extraction, None, ocr_meta

    failure = _content_free_extraction(final_extraction)
    failure.update(ocr_meta)
    failure["filename"] = getattr(initial_extraction, "filename", filename) or filename
    failure["media_type"] = getattr(initial_extraction, "media_type", media_type) or media_type
    failure["source_extension"] = getattr(initial_extraction, "source_extension", ".pdf") or ".pdf"
    failure["bytes"] = len(content)
    failure["byte_size"] = len(content)
    failure["status"] = "ocr_failed"
    failure["reason_code"] = _ocr_final_extraction_reason(final_extraction)
    return final_extraction, failure, {}


def _content_free_ocr_result(ocr_result: Any) -> dict[str, Any]:
    if hasattr(ocr_result, "to_dict"):
        data = ocr_result.to_dict()
    else:
        data = dict(ocr_result or {})
    return {
        key: value
        for key, value in data.items()
        if key not in {"ocr_pdf", "text", "text_content", "content", "raw", "payload"}
    }


def _ocr_final_extraction_reason(final_extraction: Any) -> str:
    reason = str(getattr(final_extraction, "reason_code", "") or "")
    status = str(getattr(final_extraction, "status", "") or "")
    if reason == "document_empty_text" or status == "empty":
        return "document_ocr_empty"
    return "document_ocr_failed"


def _activation_ocr_kwargs(ocr_meta: Mapping[str, Any] | None) -> dict[str, Any]:
    if not ocr_meta:
        return {}
    return {
        "ocr_applied": bool(ocr_meta.get("ocr_applied", True)),
        "ocr_engine": str(ocr_meta.get("ocr_engine") or ""),
        "ocr_languages": str(ocr_meta.get("ocr_languages") or ""),
        "ocr_duration_ms": _safe_int(ocr_meta.get("ocr_duration_ms")),
    }


def _upload_visual_page_reason(reason_code: str) -> str:
    if str(reason_code or "") == active_document_visual_limits.REASON_VISUAL_PDF_TOO_MANY_PAGES:
        return REASON_FILE_TOO_MANY_PAGES_FOR_PROVIDER_PAYLOAD
    return REASON_FILE_PAGE_COUNT_FAILED


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _human_upload_error(reason_code: str) -> str:
    labels = {
        "document_type_unsupported": "format non pris en charge",
        "document_parse_error": "lecture du fichier impossible",
        "document_empty_text": "aucun texte lisible dans ce fichier",
        "document_ocr_required": "OCR requis pour ce PDF",
        "document_ocr_failed": "OCR impossible",
        "document_ocr_timeout": "OCR trop long",
        "document_ocr_empty": "OCR sans texte lisible",
        "document_ocr_too_large": "PDF trop volumineux pour l'OCR de conversation",
        "document_ocr_too_many_pages": "PDF trop long pour l'OCR de conversation",
        "document_runtime_unavailable": "lecteur de fichier indisponible",
        "active_document_upload_too_large": "upload trop volumineux",
        "file_too_many_pages_for_provider_payload": "PDF trop long pour la lecture visuelle de conversation",
        "file_page_count_failed": "nombre de pages PDF non verifiable",
        "file_runtime_unavailable": "lecteur PDF visuel indisponible",
        "image_empty_file": "image vide",
        "image_type_unsupported": "format image non pris en charge",
        "image_gif_unsupported_v0": "GIF hors V0 pour les images actives",
        "image_extension_mismatch": "extension image incoherente",
        "image_mime_mismatch": "type MIME image incoherent",
        "image_parse_error": "image illisible",
        "image_too_large": "image trop volumineuse",
        "image_too_small_for_provider": "image trop petite",
        "image_dimensions_unsupported": "dimensions image non prises en charge",
        "image_runtime_unavailable": "lecteur image indisponible",
    }
    return labels.get(str(reason_code or ""), "document non activable")
