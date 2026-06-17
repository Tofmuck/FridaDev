from __future__ import annotations

from typing import Any, Mapping, Tuple

from . import active_document_image_validation
from . import active_document_text_extraction
from . import active_document_upload_service
from . import workspace_folder_documents


UPLOAD_FIELD = active_document_upload_service.UPLOAD_FIELD
WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH = active_document_upload_service.ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH

REASON_FILE_MISSING = "workspace_file_missing"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
REASON_FOLDER_NOT_FOUND = "workspace_folder_not_found"
REASON_TOO_LARGE = "workspace_file_too_large"
REASON_TYPE_UNSUPPORTED = "workspace_file_type_unsupported"
REASON_UNREADABLE = "workspace_file_unreadable"
REASON_OCR_REQUIRED = "workspace_file_ocr_required"
REASON_RUNTIME_UNAVAILABLE = "workspace_file_runtime_unavailable"


def upload_body_size_guard_response(content_length: Any) -> Tuple[dict[str, Any], int] | None:
    try:
        body_size = int(content_length or 0)
    except (TypeError, ValueError):
        body_size = 0
    if body_size <= WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH:
        return None
    return {
        "ok": False,
        "error": _human_workspace_file_error(REASON_TOO_LARGE),
        "reason_code": REASON_TOO_LARGE,
        "file": {
            "status": "too_large",
            "reason_code": REASON_TOO_LARGE,
            "byte_size": body_size,
            "max_body_bytes": WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH,
        },
    }, 413


def list_workspace_files_response(
    folder_id: str,
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(folder_id, workspace_folders_module=workspace_folders_module)
    if error:
        return error
    items = workspace_folder_documents.apply_document_v1_list(
        workspace_files_module.list_workspace_files(normalized),
        folder=folder,
    )
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "items": items,
    }, 200


def upload_workspace_file_response(
    folder_id: str,
    files: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
    extractor_module: Any = active_document_text_extraction,
    image_validator_module: Any = active_document_image_validation,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(folder_id, workspace_folders_module=workspace_folders_module)
    if error:
        return error

    file_obj = _first_upload_file(files)
    if file_obj is None:
        return {"ok": False, "error": "fichier requis", "reason_code": REASON_FILE_MISSING}, 400

    filename = str(getattr(file_obj, "filename", "") or "fichier").strip() or "fichier"
    media_type = str(getattr(file_obj, "mimetype", "") or "").strip()
    try:
        content = bytes(file_obj.read() or b"")
    except Exception:
        _log_workspace_file_event(
            workspace_files_module,
            "upload_failed",
            folder_id=normalized,
            mime_type=media_type,
            reason_code=REASON_UNREADABLE,
            status="parse_error",
        )
        return _workspace_file_failure(
            REASON_UNREADABLE,
            filename=filename,
            media_type=media_type,
            status="parse_error",
            status_code=400,
        )

    if len(content) > WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH:
        _log_workspace_file_event(
            workspace_files_module,
            "upload_failed",
            folder_id=normalized,
            mime_type=media_type,
            byte_size=len(content),
            reason_code=REASON_TOO_LARGE,
            status="too_large",
        )
        return _workspace_file_failure(
            REASON_TOO_LARGE,
            filename=filename,
            media_type=media_type,
            status="too_large",
            status_code=413,
            extra={"byte_size": len(content), "max_body_bytes": WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH},
        )

    metadata, validation_error = _workspace_upload_metadata(
        content,
        filename=filename,
        media_type=media_type,
        extractor_module=extractor_module,
        image_validator_module=image_validator_module,
        workspace_files_module=workspace_files_module,
    )
    if validation_error:
        payload, _status = validation_error
        file_meta = payload.get("file") if isinstance(payload, Mapping) else {}
        _log_workspace_file_event(
            workspace_files_module,
            "upload_failed",
            folder_id=normalized,
            mime_type=file_meta.get("media_type") if isinstance(file_meta, Mapping) else media_type,
            byte_size=file_meta.get("byte_size") if isinstance(file_meta, Mapping) else len(content),
            reason_code=payload.get("reason_code") if isinstance(payload, Mapping) else "",
            status=file_meta.get("status") if isinstance(file_meta, Mapping) else "",
        )
        return validation_error

    stored = workspace_files_module.store_uploaded_file(
        normalized,
        original_filename=filename,
        content=content,
        metadata=metadata,
    )
    if not stored:
        _log_workspace_file_event(
            workspace_files_module,
            "upload_failed",
            folder_id=normalized,
            mime_type=metadata.get("mime_type"),
            media_kind=metadata.get("media_kind"),
            content_kind=metadata.get("content_kind"),
            byte_size=len(content),
            reason_code=REASON_RUNTIME_UNAVAILABLE,
            status=metadata.get("status"),
        )
        return {
            "ok": False,
            "error": _human_workspace_file_error(REASON_RUNTIME_UNAVAILABLE),
            "reason_code": REASON_RUNTIME_UNAVAILABLE,
        }, 503
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "file": workspace_folder_documents.apply_document_v1_projection(stored, folder=folder),
    }, 201


def delete_workspace_file_response(
    folder_id: str,
    file_id: str,
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(folder_id, workspace_folders_module=workspace_folders_module)
    if error:
        return error
    file_norm = workspace_files_module.normalize_workspace_file_id(file_id)
    if not file_norm:
        return {"ok": False, "error": "file_id invalide", "reason_code": REASON_FILE_MISSING}, 400
    deleted = workspace_files_module.delete_workspace_file(normalized, file_norm)
    if deleted is None:
        return {"ok": False, "error": "fichier introuvable", "reason_code": REASON_FILE_MISSING}, 404
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "file": workspace_folder_documents.apply_document_v1_projection(deleted, folder=folder),
    }, 200


def _log_workspace_file_event(workspace_files_module: Any, event: str, **fields: Any) -> None:
    log_func = getattr(workspace_files_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, **fields)


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, dict[str, Any], Tuple[dict[str, Any], int] | None]:
    normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    if not normalized:
        return "", {}, ({"ok": False, "error": "folder_id invalide", "reason_code": "workspace_folder_id_invalid"}, 400)
    folder = workspace_folders_module.get_workspace_folder(normalized)
    if not folder:
        return "", {}, ({"ok": False, "error": "repertoire introuvable", "reason_code": REASON_FOLDER_NOT_FOUND}, 404)
    if folder.get("deleted_at"):
        return "", {}, ({"ok": False, "error": "repertoire supprime", "reason_code": REASON_FOLDER_DELETED}, 410)
    return normalized, dict(folder), None


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


def _workspace_upload_metadata(
    content: bytes,
    *,
    filename: str,
    media_type: str,
    extractor_module: Any,
    image_validator_module: Any,
    workspace_files_module: Any,
) -> tuple[dict[str, Any], Tuple[dict[str, Any], int] | None]:
    image_validation = image_validator_module.validate_active_image_upload(
        content,
        filename=filename,
        declared_media_type=media_type,
    )
    if image_validation.is_image_candidate:
        if image_validation.status != image_validator_module.STATUS_COMPLETE:
            reason = _map_image_reason(image_validation.reason_code)
            return {}, _workspace_file_failure(
                reason,
                filename=filename,
                media_type=image_validation.media_type or media_type,
                status=image_validation.status,
                status_code=422,
                extra=_content_free_dict(image_validation),
            )
        return {
            "display_name": workspace_files_module.sanitize_display_name(image_validation.filename),
            "content_kind": workspace_files_module.CONTENT_KIND_IMAGE,
            "media_kind": workspace_files_module.MEDIA_KIND_IMAGE,
            "mime_type": image_validation.media_type,
            "source_extension": image_validation.source_extension,
            "image_width": image_validation.image_width,
            "image_height": image_validation.image_height,
            "status": workspace_files_module.STATUS_ACTIVE,
            "reason_code": "",
            "source_kind": workspace_files_module.SOURCE_KIND_UPLOAD,
        }, None

    extraction = extractor_module.extract_active_document_text(
        content,
        filename=filename,
        media_type=media_type,
    )
    if extraction.status == extractor_module.STATUS_COMPLETE:
        return {
            "display_name": workspace_files_module.sanitize_display_name(extraction.filename),
            "content_kind": workspace_files_module.CONTENT_KIND_DOCUMENT,
            "media_kind": workspace_files_module.MEDIA_KIND_TEXT,
            "mime_type": extraction.media_type,
            "source_extension": extraction.source_extension,
            "text_chars": extraction.chars,
            "text_sha256_12": extraction.sha256_12,
            "status": workspace_files_module.STATUS_ACTIVE,
            "reason_code": "",
            "source_kind": workspace_files_module.SOURCE_KIND_UPLOAD,
        }, None

    if extraction.status == extractor_module.STATUS_OCR_REQUIRED:
        return {
            "display_name": workspace_files_module.sanitize_display_name(extraction.filename),
            "content_kind": workspace_files_module.CONTENT_KIND_DOCUMENT,
            "media_kind": workspace_files_module.MEDIA_KIND_TEXT,
            "mime_type": extraction.media_type,
            "source_extension": extraction.source_extension,
            "text_chars": 0,
            "text_sha256_12": "",
            "status": workspace_files_module.STATUS_OCR_REQUIRED,
            "reason_code": REASON_OCR_REQUIRED,
            "source_kind": workspace_files_module.SOURCE_KIND_UPLOAD,
        }, None

    reason = _map_text_reason(extraction.reason_code)
    return {}, _workspace_file_failure(
        reason,
        filename=filename,
        media_type=extraction.media_type or media_type,
        status=extraction.status,
        status_code=422,
        extra=_content_free_dict(extraction),
    )


def _content_free_dict(value: Any) -> dict[str, Any]:
    data = value.to_dict() if hasattr(value, "to_dict") else dict(value or {})
    return {
        key: item
        for key, item in data.items()
        if key not in {"text", "text_content", "content", "raw", "payload", "binary_content", "image_content"}
    }


def _workspace_file_failure(
    reason_code: str,
    *,
    filename: str,
    media_type: str,
    status: str,
    status_code: int,
    extra: Mapping[str, Any] | None = None,
) -> Tuple[dict[str, Any], int]:
    file_meta = {
        "filename": filename,
        "media_type": media_type,
        "status": status,
        "reason_code": reason_code,
    }
    for key, value in (extra or {}).items():
        if key not in {"text", "text_content", "content", "raw", "payload", "binary_content", "image_content"}:
            file_meta[key] = value
    file_meta["reason_code"] = reason_code
    return {
        "ok": False,
        "error": _human_workspace_file_error(reason_code),
        "reason_code": reason_code,
        "file": file_meta,
    }, status_code


def _map_image_reason(reason_code: str) -> str:
    if reason_code == "image_too_large":
        return REASON_TOO_LARGE
    if reason_code in {"image_parse_error", "image_empty_file", "image_dimensions_unsupported", "image_too_small_for_provider"}:
        return REASON_UNREADABLE
    return REASON_TYPE_UNSUPPORTED


def _map_text_reason(reason_code: str) -> str:
    if reason_code == "document_type_unsupported":
        return REASON_TYPE_UNSUPPORTED
    if reason_code == "document_ocr_required":
        return REASON_OCR_REQUIRED
    return REASON_UNREADABLE


def _human_workspace_file_error(reason_code: str) -> str:
    labels = {
        REASON_FILE_MISSING: "fichier introuvable",
        REASON_FOLDER_DELETED: "repertoire supprime",
        REASON_FOLDER_NOT_FOUND: "repertoire introuvable",
        REASON_TOO_LARGE: "fichier trop volumineux",
        REASON_TYPE_UNSUPPORTED: "format non pris en charge",
        REASON_UNREADABLE: "lecture du fichier impossible",
        REASON_OCR_REQUIRED: "OCR requis pour ce fichier",
        REASON_RUNTIME_UNAVAILABLE: "stockage fichier indisponible",
    }
    return labels.get(str(reason_code or ""), "fichier non stockable")
