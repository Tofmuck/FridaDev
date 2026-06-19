from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from . import workspace_folder_export_generation
from . import workspace_folder_export_nextcloud_client as export_client
from . import workspace_folder_exports
from . import workspace_folder_nextcloud_links_store as nextcloud_links


DOWNLOAD_MAX_BYTES = workspace_folder_export_generation.GENERATED_ARTIFACT_MAX_BYTES

_MEDIA_TYPES = {
    workspace_folder_exports.EXPORT_FORMAT_MARKDOWN: "text/markdown; charset=utf-8",
    workspace_folder_exports.EXPORT_FORMAT_TEXT: "text/plain; charset=utf-8",
    workspace_folder_exports.EXPORT_FORMAT_DOCX: (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    ),
    workspace_folder_exports.EXPORT_FORMAT_PDF: "application/pdf",
}


@dataclass(frozen=True)
class ExportContentResponse:
    ok: bool
    status: int
    reason_code: str
    content: bytes = b""
    media_type: str = "application/octet-stream"
    headers: Mapping[str, str] | None = None
    payload: Mapping[str, Any] | None = None


def download_workspace_folder_export_response(
    folder_id: str,
    export_id: str,
    *,
    workspace_folders_module: Any,
    workspace_folder_exports_module: Any = workspace_folder_exports,
    nextcloud: Any | None = None,
    disposition: str = "attachment",
) -> ExportContentResponse:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error is not None:
        return error
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _error(
            workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
            status=409,
            folder_id=normalized,
        )

    export, error = _resolve_export(
        normalized,
        export_id,
        workspace_folder_exports_module=workspace_folder_exports_module,
    )
    if error is not None:
        return error

    target_folder_name = _target_folder_name(folder)
    export_format = workspace_folder_exports.normalize_export_format(
        export.get("export_format") or export.get("format")
    )
    target_name = _target_name(export, export_format=export_format)
    if not target_folder_name or not target_name or not export_format:
        return _error(
            workspace_folder_exports.REASON_NAME_INVALID,
            status=400,
            folder_id=normalized,
            export_id=export.get("id"),
        )

    try:
        client = _client(nextcloud)
        read = client.read_export(
            target_folder_name,
            target_name,
            max_bytes=DOWNLOAD_MAX_BYTES,
        )
    except export_client.NextcloudExportClientError as exc:
        return _error(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            folder_id=normalized,
            export_id=export.get("id"),
            http_status_class=exc.status_class,
        )

    _log_event(
        workspace_folder_exports_module,
        "exports_v1_download_ok",
        folder_id=normalized,
        export_id=export.get("id"),
        reason_code=workspace_folder_exports.REASON_DOWNLOAD_OK,
        http_status_class=read.status_class,
        export_name_hash=workspace_folder_exports.title_hash_for_target(target_name),
    )
    return ExportContentResponse(
        ok=True,
        status=200,
        reason_code=workspace_folder_exports.REASON_DOWNLOAD_OK,
        content=read.content,
        media_type=_media_type(export_format),
        headers={
            "Content-Type": _media_type(export_format),
            "Content-Length": str(len(read.content)),
            "Content-Disposition": _content_disposition(
                export,
                export_format=export_format,
                disposition=disposition,
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frida-Reason-Code": workspace_folder_exports.REASON_DOWNLOAD_OK,
        },
    )


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, dict[str, Any], ExportContentResponse | None]:
    try:
        normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    except Exception:
        return "", {}, _error(
            workspace_folder_exports.REASON_LOOKUP_FAILED,
            status=503,
        )
    if not normalized:
        return "", {}, _error("workspace_folder_id_invalid", status=400)
    try:
        try:
            folder = workspace_folders_module.get_workspace_folder(normalized, include_deleted=True)
        except TypeError:
            folder = workspace_folders_module.get_workspace_folder(normalized)
    except Exception:
        return "", {}, _error(
            workspace_folder_exports.REASON_LOOKUP_FAILED,
            status=503,
            folder_id=normalized,
        )
    if not folder:
        return "", {}, _error("workspace_folder_not_found", status=404)
    if folder.get("deleted_at"):
        return "", {}, _error("workspace_folder_deleted", status=410, folder_id=normalized)
    return normalized, dict(folder), None


def _resolve_export(
    folder_id: str,
    export_id: str,
    *,
    workspace_folder_exports_module: Any,
) -> tuple[dict[str, Any], ExportContentResponse | None]:
    normalized_export_id = workspace_folder_exports.normalize_export_id(export_id)
    if not normalized_export_id:
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
            status=404,
            folder_id=folder_id,
        )
    try:
        export = workspace_folder_exports_module.get_export(
            normalized_export_id,
            fail_closed=True,
        )
    except Exception:
        return {}, _error(
            workspace_folder_exports.REASON_LOOKUP_FAILED,
            status=503,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    if not export:
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
            status=404,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    export_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
        export.get("workspace_folder_id")
    )
    if export_folder_id != folder_id:
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
            status=404,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    if workspace_folder_exports.is_deleted(export):
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_DELETED,
            status=410,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    if workspace_folder_exports._local_state(export.get("local_state")) != (
        workspace_folder_exports.EXPORT_LOCAL_AVAILABLE
    ):
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_NOT_LINKED,
            status=409,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    if workspace_folder_exports._nextcloud_state(export.get("nextcloud_sync_state")) != (
        workspace_folder_exports.EXPORT_NEXTCLOUD_LINKED
    ):
        return {}, _error(
            workspace_folder_exports.REASON_EXPORT_NOT_LINKED,
            status=409,
            folder_id=folder_id,
            export_id=normalized_export_id,
        )
    return dict(export), None


def _error(
    reason_code: str,
    *,
    status: int,
    folder_id: str = "",
    export_id: str = "",
    http_status_class: str = "none",
) -> ExportContentResponse:
    safe_reason = _safe_reason(reason_code)
    payload = {
        "ok": False,
        "error": _human_error(safe_reason),
        "reason_code": safe_reason,
        "workspace_folder_id": workspace_folder_exports.normalize_workspace_folder_id(folder_id),
        "export": {
            "status": _export_status_for_failure(safe_reason),
            "reason_code": safe_reason,
        },
        "export_v1_technical": {
            "reason_code": safe_reason,
            "export_ref": workspace_folder_exports.export_ref(export_id) if export_id else "",
            "folder_ref": workspace_folder_exports.folder_ref(folder_id) if folder_id else "",
            "http_status_class": http_status_class,
        },
    }
    if export_id:
        payload["export"]["export_ref"] = workspace_folder_exports.export_ref(export_id)
    return ExportContentResponse(
        ok=False,
        status=int(status or 500),
        reason_code=safe_reason,
        payload=payload,
    )


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "").strip()


def _target_name(export: Mapping[str, Any], *, export_format: str) -> str:
    raw = str(export.get("target_name") or "").strip()
    if not raw:
        return ""
    sanitized = workspace_folder_exports.sanitize_export_target_name(raw, export_format)
    return raw if raw == sanitized else ""


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return export_client.NextcloudExportClient.from_env()


def _media_type(export_format: str) -> str:
    return _MEDIA_TYPES.get(export_format, "application/octet-stream")


def _content_disposition(
    export: Mapping[str, Any],
    *,
    export_format: str,
    disposition: str,
) -> str:
    mode = "inline" if str(disposition or "").strip().lower() == "inline" else "attachment"
    target = _target_name(export, export_format=export_format)
    fallback = f"export{workspace_folder_exports.EXPORT_FORMAT_EXTENSIONS.get(export_format, '')}"
    filename = _ascii_filename(target or fallback, fallback=fallback)
    return f'{mode}; filename="{filename}"'


def _ascii_filename(value: str, *, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    fallback_token = re.sub(r"[^A-Za-z0-9._-]+", "-", fallback).strip("-._")
    return (token or fallback_token or "export")[:180]


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        workspace_folder_exports.REASON_EXPORT_NOT_LINKED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code in {
        workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
        workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING,
    }:
        return 404
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_INVALID,
        workspace_folder_exports.REASON_NAME_INVALID,
    }:
        return 400
    if reason_code == workspace_folder_exports.REASON_EXPORT_DELETED:
        return 410
    if reason_code == workspace_folder_exports.REASON_TOO_LARGE:
        return 413
    if reason_code in {
        workspace_folder_exports.REASON_LOOKUP_FAILED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE,
    }:
        return 503
    return 502


def _export_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_exports.REASON_EXPORT_DELETED:
        return workspace_folder_exports.EXPORT_LOCAL_DELETED
    return workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE


def _human_error(reason_code: str) -> str:
    return {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED: "dossier Frida non lie a Nextcloud",
        workspace_folder_exports.REASON_FOLDER_INVALID: "dossier Frida invalide",
        workspace_folder_exports.REASON_FOLDER_DELETED: "dossier Frida supprime",
        workspace_folder_exports.REASON_EXPORT_NOT_FOUND: "export introuvable",
        workspace_folder_exports.REASON_EXPORT_DELETED: "export supprime",
        workspace_folder_exports.REASON_EXPORT_NOT_LINKED: "export non lie a Nextcloud",
        workspace_folder_exports.REASON_NAME_INVALID: "nom d'export invalide",
        workspace_folder_exports.REASON_TOO_LARGE: "export trop volumineux",
        workspace_folder_exports.REASON_LOOKUP_FAILED: "recherche d'export impossible",
        workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE: "export distant indisponible",
        workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED: "lecture d'export impossible",
    }.get(reason_code, "lecture d'export impossible")


def _safe_reason(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if text in workspace_folder_exports.REASON_CODE_CATALOG:
        return text
    if text in {"workspace_folder_id_invalid", "workspace_folder_not_found", "workspace_folder_deleted"}:
        return text
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _log_event(exports_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(exports_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
