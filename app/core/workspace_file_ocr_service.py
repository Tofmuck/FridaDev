from __future__ import annotations

"""Workspace-file OCR orchestration.

This module adapts the existing active-document OCR/extraction stack to
durable workspace files. It stores OCR output as an ordinary Markdown
``workspace_file`` derivative and never injects it automatically.
"""

from pathlib import Path
from typing import Any, Mapping, Tuple

from . import active_document_ocr_client
from . import active_document_text_extraction


REASON_FILE_MISSING = "workspace_file_missing"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
REASON_FOLDER_NOT_FOUND = "workspace_folder_not_found"
REASON_OCR_UNSUPPORTED = "workspace_file_ocr_unsupported"
REASON_OCR_FAILED = "workspace_file_ocr_failed"
REASON_OCR_TIMEOUT = "workspace_file_ocr_timeout"
REASON_OCR_EMPTY = "workspace_file_ocr_empty"
REASON_OCR_TOO_LARGE = "workspace_file_ocr_too_large"
REASON_OCR_TOO_MANY_PAGES = "workspace_file_ocr_too_many_pages"
REASON_UNREADABLE = "workspace_file_unreadable"
REASON_RUNTIME_UNAVAILABLE = "workspace_file_runtime_unavailable"
REASON_MARKDOWN_TOO_LARGE = "workspace_file_ocr_markdown_too_large"

WORKSPACE_OCR_MARKDOWN_MAX_BYTES = 5 * 1024 * 1024


def ocr_workspace_file_response(
    folder_id: str,
    file_id: str,
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
    extractor_module: Any = active_document_text_extraction,
    ocr_module: Any = active_document_ocr_client,
) -> Tuple[dict[str, Any], int]:
    normalized, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error
    source = _get_source_file(
        normalized,
        file_id,
        workspace_files_module=workspace_files_module,
    )
    if source is None:
        return _failure(REASON_FILE_MISSING, status_code=404)
    if not _is_ocr_compatible(source, workspace_files_module=workspace_files_module):
        _log(
            workspace_files_module,
            "ocr_refused",
            folder_id=normalized,
            file_id=file_id,
            media_kind=source.get("media_kind"),
            mime_type=source.get("mime_type"),
            byte_size=source.get("byte_size"),
            status=source.get("status"),
            reason_code=REASON_OCR_UNSUPPORTED,
        )
        return _failure(REASON_OCR_UNSUPPORTED, status_code=422, source=source)

    try:
        source_bytes = workspace_files_module.read_file_bytes(str(source.get("storage_key") or ""))
    except Exception as exc:
        _log(
            workspace_files_module,
            "ocr_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            media_kind=source.get("media_kind"),
            mime_type=source.get("mime_type"),
            byte_size=source.get("byte_size"),
            status=source.get("status"),
            reason_code=REASON_UNREADABLE,
            error_type=type(exc).__name__,
        )
        return _failure(REASON_UNREADABLE, status_code=409, source=source)

    try:
        ocr_result = _run_ocr(
            source_bytes,
            source=source,
            ocr_module=ocr_module,
        )
    except Exception as exc:
        _log(
            workspace_files_module,
            "ocr_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            media_kind=source.get("media_kind"),
            mime_type=source.get("mime_type"),
            byte_size=source.get("byte_size"),
            status=source.get("status"),
            reason_code=REASON_OCR_FAILED,
            error_type=type(exc).__name__,
        )
        return _failure(REASON_OCR_FAILED, status_code=422, source=source)
    if str(getattr(ocr_result, "status", "") or "") != str(getattr(ocr_module, "STATUS_COMPLETE", "complete")):
        reason = _map_ocr_reason(str(getattr(ocr_result, "reason_code", "") or ""))
        _log(
            workspace_files_module,
            "ocr_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            media_kind=source.get("media_kind"),
            mime_type=source.get("mime_type"),
            byte_size=source.get("byte_size"),
            status=source.get("status"),
            reason_code=reason,
            ocr_engine=getattr(ocr_result, "ocr_engine", ""),
            ocr_languages=getattr(ocr_result, "ocr_languages", ""),
            ocr_duration_ms=getattr(ocr_result, "ocr_duration_ms", 0),
        )
        return _failure(reason, status_code=422, source=source, ocr_result=ocr_result)

    extraction = extractor_module.extract_active_document_text(
        bytes(getattr(ocr_result, "ocr_pdf", b"") or b""),
        filename=_source_filename(source),
        media_type="application/pdf",
    )
    if str(getattr(extraction, "status", "") or "") != str(getattr(extractor_module, "STATUS_COMPLETE", "complete")):
        reason = REASON_OCR_EMPTY if str(getattr(extraction, "status", "") or "") == "empty" else REASON_OCR_FAILED
        _log(
            workspace_files_module,
            "ocr_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            media_kind=source.get("media_kind"),
            mime_type=source.get("mime_type"),
            byte_size=source.get("byte_size"),
            status=source.get("status"),
            reason_code=reason,
            ocr_engine=getattr(ocr_result, "ocr_engine", ""),
            ocr_languages=getattr(ocr_result, "ocr_languages", ""),
            ocr_duration_ms=getattr(ocr_result, "ocr_duration_ms", 0),
        )
        return _failure(reason, status_code=422, source=source, ocr_result=ocr_result)

    markdown = _ocr_markdown(
        source,
        text=str(getattr(extraction, "text", "") or ""),
        ocr_result=ocr_result,
    )
    markdown_bytes = markdown.encode("utf-8")
    metadata = _markdown_metadata(
        source,
        markdown=markdown,
        extractor_module=extractor_module,
    )
    existing = _find_existing_derivative(
        normalized,
        str(source.get("id") or ""),
        workspace_files_module=workspace_files_module,
    )
    if existing:
        derived = workspace_files_module.update_workspace_text_file(
            normalized,
            str(existing.get("id") or ""),
            content=markdown_bytes,
            metadata=metadata,
        )
    else:
        derived = workspace_files_module.store_uploaded_file(
            normalized,
            original_filename=_ocr_markdown_filename(_source_filename(source)),
            content=markdown_bytes,
            metadata=metadata,
        )
    if not derived:
        _log(
            workspace_files_module,
            "ocr_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            source_file_id=source.get("id"),
            reason_code=REASON_RUNTIME_UNAVAILABLE,
        )
        return _failure(REASON_RUNTIME_UNAVAILABLE, status_code=503, source=source)

    _log(
        workspace_files_module,
        "ocr_ok",
        folder_id=normalized,
        file_id=derived.get("id"),
        source_file_id=source.get("id"),
        media_kind=source.get("media_kind"),
        mime_type=source.get("mime_type"),
        byte_size=source.get("byte_size"),
        derived_byte_size=derived.get("byte_size"),
        sha256_12=derived.get("sha256_12"),
        ocr_engine=getattr(ocr_result, "ocr_engine", ""),
        ocr_languages=getattr(ocr_result, "ocr_languages", ""),
        ocr_duration_ms=getattr(ocr_result, "ocr_duration_ms", 0),
        reason_code="",
    )
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "source_file_id": str(source.get("id") or ""),
        "file": derived,
        "ocr": _content_free_ocr_result(ocr_result),
    }, 201 if not existing else 200


def get_ocr_markdown_response(
    folder_id: str,
    file_id: str,
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
) -> Tuple[dict[str, Any], int]:
    normalized, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error
    row = _get_source_file(normalized, file_id, workspace_files_module=workspace_files_module)
    if row is None:
        return _failure(REASON_FILE_MISSING, status_code=404)
    if not _is_editable_ocr_markdown(row):
        return _failure(REASON_OCR_UNSUPPORTED, status_code=422, source=row)
    try:
        content = workspace_files_module.read_file_bytes(str(row.get("storage_key") or "")).decode("utf-8")
    except Exception as exc:
        _log(
            workspace_files_module,
            "ocr_markdown_read_failed",
            level="warning",
            folder_id=normalized,
            file_id=file_id,
            reason_code=REASON_UNREADABLE,
            error_type=type(exc).__name__,
        )
        return _failure(REASON_UNREADABLE, status_code=409, source=row)
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "file": _public_file(row, workspace_files_module=workspace_files_module),
        "content": content,
    }, 200


def patch_ocr_markdown_response(
    folder_id: str,
    file_id: str,
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
    extractor_module: Any = active_document_text_extraction,
) -> Tuple[dict[str, Any], int]:
    normalized, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error
    row = _get_source_file(normalized, file_id, workspace_files_module=workspace_files_module)
    if row is None:
        return _failure(REASON_FILE_MISSING, status_code=404)
    if not _is_editable_ocr_markdown(row):
        return _failure(REASON_OCR_UNSUPPORTED, status_code=422, source=row)
    raw_content = data.get("content", "") if isinstance(data, Mapping) else ""
    content = "" if raw_content is None else str(raw_content)
    encoded = content.encode("utf-8")
    if len(encoded) > WORKSPACE_OCR_MARKDOWN_MAX_BYTES:
        return _failure(REASON_MARKDOWN_TOO_LARGE, status_code=413, source=row)
    extraction = extractor_module.extract_active_document_text(
        encoded,
        filename=_source_filename(row),
        media_type="text/markdown",
    )
    if str(getattr(extraction, "status", "") or "") != str(getattr(extractor_module, "STATUS_COMPLETE", "complete")):
        return _failure(REASON_UNREADABLE, status_code=422, source=row)
    updated = workspace_files_module.update_workspace_text_file(
        normalized,
        str(row.get("id") or ""),
        content=encoded,
        metadata={
            "text_chars": getattr(extraction, "chars", 0),
            "text_sha256_12": getattr(extraction, "sha256_12", ""),
            "status": workspace_files_module.STATUS_ACTIVE,
            "reason_code": "",
        },
    )
    if not updated:
        return _failure(REASON_RUNTIME_UNAVAILABLE, status_code=503, source=row)
    _log(
        workspace_files_module,
        "ocr_markdown_edit_ok",
        folder_id=normalized,
        file_id=file_id,
        source_file_id=row.get("source_file_id"),
        byte_size=updated.get("byte_size"),
        text_chars=updated.get("text_chars"),
        sha256_12=updated.get("sha256_12"),
        reason_code="",
    )
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "file": updated,
    }, 200


def _get_source_file(folder_id: str, file_id: str, *, workspace_files_module: Any) -> dict[str, Any] | None:
    normalizer = getattr(workspace_files_module, "normalize_workspace_file_id", None)
    normalized_file = normalizer(file_id) if callable(normalizer) else str(file_id or "")
    if not normalized_file:
        return None
    getter = getattr(workspace_files_module, "get_workspace_file_storage_row", None)
    if not callable(getter):
        return None
    row = getter(folder_id, normalized_file)
    return dict(row) if isinstance(row, Mapping) else None


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, Tuple[dict[str, Any], int] | None]:
    normalizer = getattr(workspace_folders_module, "normalize_workspace_folder_id", None)
    normalized = normalizer(folder_id) if callable(normalizer) else str(folder_id or "")
    if not normalized:
        return "", ({"ok": False, "error": "folder_id invalide", "reason_code": "workspace_folder_id_invalid"}, 400)
    getter = getattr(workspace_folders_module, "get_workspace_folder", None)
    folder = getter(normalized) if callable(getter) else None
    if not folder:
        return "", ({"ok": False, "error": "repertoire introuvable", "reason_code": REASON_FOLDER_NOT_FOUND}, 404)
    if isinstance(folder, Mapping) and folder.get("deleted_at"):
        return "", ({"ok": False, "error": "repertoire supprime", "reason_code": REASON_FOLDER_DELETED}, 410)
    return str(normalized), None


def _run_ocr(content: bytes, *, source: Mapping[str, Any], ocr_module: Any) -> Any:
    filename = _source_filename(source)
    if _is_image_source(source):
        image_ocr = getattr(ocr_module, "ocr_image_with_stirling", None)
        if not callable(image_ocr):
            raise RuntimeError("image_ocr_unavailable")
        return image_ocr(content, filename=filename, media_type=str(source.get("mime_type") or ""))
    return ocr_module.ocr_pdf_with_stirling(content, filename=filename)


def _is_ocr_compatible(source: Mapping[str, Any], *, workspace_files_module: Any) -> bool:
    if str(source.get("deleted_at") or ""):
        return False
    status = str(source.get("status") or getattr(workspace_files_module, "STATUS_ACTIVE", "active")).strip()
    if status not in {getattr(workspace_files_module, "STATUS_ACTIVE", "active"), getattr(workspace_files_module, "STATUS_OCR_REQUIRED", "ocr_required")}:
        return False
    return _is_image_source(source) or _is_pdf_source(source)


def _is_image_source(source: Mapping[str, Any]) -> bool:
    media_kind = str(source.get("media_kind") or "").strip().lower()
    mime_type = str(source.get("mime_type") or "").split(";", 1)[0].strip().lower()
    return media_kind == "image" and mime_type in {"image/png", "image/jpeg", "image/webp"}


def _is_pdf_source(source: Mapping[str, Any]) -> bool:
    mime_type = str(source.get("mime_type") or "").split(";", 1)[0].strip().lower()
    extension = str(source.get("source_extension") or "").strip().lower()
    return mime_type == "application/pdf" or extension == ".pdf"


def _is_editable_ocr_markdown(row: Mapping[str, Any]) -> bool:
    return (
        str(row.get("source_kind") or "") == "ocr_derived"
        and str(row.get("source_extension") or "").strip().lower() == ".md"
        and str(row.get("deleted_at") or "") == ""
    )


def _ocr_markdown(source: Mapping[str, Any], *, text: str, ocr_result: Any) -> str:
    filename = _source_filename(source)
    lines = [
        f"# OCR - {filename}",
        "",
        "> Extraction OCR imparfaite. Pour les manuscrits, captures et scans, ce texte doit etre relu/corrige.",
        f"> Source: {filename}",
        f"> Moteur: {getattr(ocr_result, 'ocr_engine', '') or 'ocr'}",
        f"> Langues: {getattr(ocr_result, 'ocr_languages', '') or 'non precisees'}",
        "",
        str(text or "").strip(),
        "",
    ]
    return "\n".join(lines)


def _markdown_metadata(source: Mapping[str, Any], *, markdown: str, extractor_module: Any) -> dict[str, Any]:
    filename = _ocr_markdown_filename(_source_filename(source))
    content = markdown.encode("utf-8")
    extraction = extractor_module.extract_active_document_text(
        content,
        filename=filename,
        media_type="text/markdown",
    )
    return {
        "display_name": filename,
        "content_kind": "document",
        "media_kind": "text",
        "mime_type": "text/markdown",
        "source_extension": ".md",
        "text_chars": getattr(extraction, "chars", len(markdown)),
        "text_sha256_12": getattr(extraction, "sha256_12", ""),
        "status": "active",
        "reason_code": "",
        "source_kind": "ocr_derived",
        "source_file_id": str(source.get("id") or ""),
    }


def _ocr_markdown_filename(filename: str) -> str:
    name = Path(str(filename or "fichier")).name or "fichier"
    stem = name.rsplit(".", 1)[0] if "." in name else name
    return f"{stem or 'fichier'}.ocr.md"


def _source_filename(source: Mapping[str, Any]) -> str:
    return str(source.get("display_name") or source.get("original_filename") or "fichier").strip() or "fichier"


def _find_existing_derivative(folder_id: str, source_file_id: str, *, workspace_files_module: Any) -> dict[str, Any] | None:
    finder = getattr(workspace_files_module, "find_ocr_derived_file", None)
    if not callable(finder):
        return None
    item = finder(folder_id, source_file_id)
    return dict(item) if isinstance(item, Mapping) else None


def _public_file(row: Mapping[str, Any], *, workspace_files_module: Any) -> dict[str, Any]:
    serializer = getattr(workspace_files_module, "serialize_workspace_file_row", None)
    if callable(serializer):
        item = serializer(row)
        if isinstance(item, Mapping):
            return dict(item)
    return {
        key: value
        for key, value in dict(row).items()
        if key not in {"storage_key", "sha256", "internal_path"}
    }


def _map_ocr_reason(reason_code: str) -> str:
    mapping = {
        "document_ocr_timeout": REASON_OCR_TIMEOUT,
        "document_ocr_empty": REASON_OCR_EMPTY,
        "document_ocr_too_large": REASON_OCR_TOO_LARGE,
        "document_ocr_too_many_pages": REASON_OCR_TOO_MANY_PAGES,
    }
    return mapping.get(str(reason_code or ""), REASON_OCR_FAILED)


def _content_free_ocr_result(ocr_result: Any) -> dict[str, Any]:
    data = ocr_result.to_dict() if hasattr(ocr_result, "to_dict") else dict(ocr_result or {})
    return {
        key: value
        for key, value in data.items()
        if key not in {"ocr_pdf", "text", "text_content", "content", "raw", "payload", "binary_content", "image_content"}
    }


def _failure(
    reason_code: str,
    *,
    status_code: int,
    source: Mapping[str, Any] | None = None,
    ocr_result: Any = None,
) -> Tuple[dict[str, Any], int]:
    payload: dict[str, Any] = {
        "ok": False,
        "error": _human_error(reason_code),
        "reason_code": reason_code,
    }
    if source:
        payload["file"] = {
            "id": str(source.get("id") or ""),
            "workspace_folder_id": str(source.get("workspace_folder_id") or ""),
            "display_name": str(source.get("display_name") or "fichier"),
            "media_kind": str(source.get("media_kind") or ""),
            "mime_type": str(source.get("mime_type") or ""),
            "byte_size": int(source.get("byte_size") or 0),
            "status": str(source.get("status") or ""),
            "reason_code": reason_code,
            "source_kind": str(source.get("source_kind") or ""),
            "source_file_id": str(source.get("source_file_id") or "") or None,
        }
    if ocr_result is not None:
        payload["ocr"] = _content_free_ocr_result(ocr_result)
    return payload, status_code


def _human_error(reason_code: str) -> str:
    labels = {
        REASON_FILE_MISSING: "fichier introuvable",
        REASON_FOLDER_DELETED: "repertoire supprime",
        REASON_FOLDER_NOT_FOUND: "repertoire introuvable",
        REASON_OCR_UNSUPPORTED: "OCR non disponible pour ce fichier",
        REASON_OCR_FAILED: "OCR impossible",
        REASON_OCR_TIMEOUT: "OCR trop long",
        REASON_OCR_EMPTY: "OCR sans texte lisible",
        REASON_OCR_TOO_LARGE: "fichier trop volumineux pour OCR",
        REASON_OCR_TOO_MANY_PAGES: "PDF trop long pour OCR",
        REASON_UNREADABLE: "lecture du fichier impossible",
        REASON_RUNTIME_UNAVAILABLE: "stockage fichier indisponible",
        REASON_MARKDOWN_TOO_LARGE: "Markdown OCR trop volumineux",
    }
    return labels.get(str(reason_code or ""), "OCR indisponible")


def _log(workspace_files_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(workspace_files_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
