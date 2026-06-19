from __future__ import annotations

import hashlib
from typing import Any, Mapping

from . import workspace_folder_export_generation
from . import workspace_folder_export_nextcloud_client as export_client
from . import workspace_folder_exports
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection


def store_workspace_folder_export_nextcloud_first(
    *,
    folder: Mapping[str, Any],
    request: Mapping[str, Any],
    exports_module: Any = workspace_folder_exports,
    export_generation_module: Any = workspace_folder_export_generation,
    nextcloud: Any | None = None,
    conversation_reader: Any | None = None,
    note_reader: Any | None = None,
    document_reader: Any | None = None,
    export_reader: Any | None = None,
    binary_dependency_checker: Any | None = None,
) -> dict[str, Any]:
    folder_id = workspace_folder_exports.normalize_workspace_folder_id(folder.get("id"))
    if not folder_id:
        return _failure(workspace_folder_exports.REASON_FOLDER_INVALID, status=400, store_state="blocked")
    if folder.get("deleted_at"):
        return _failure(workspace_folder_exports.REASON_FOLDER_DELETED, status=410, store_state="blocked")
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(workspace_folder_exports.REASON_FOLDER_NOT_LINKED, status=409, store_state="blocked")

    target_folder_name = _target_folder_name(folder)
    if not target_folder_name:
        return _failure(
            workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE,
            status=502,
            store_state="blocked",
        )

    payload = dict(request or {})
    payload["workspace_folder_id"] = folder_id
    generated = export_generation_module.generate_workspace_folder_export(
        payload,
        conversation_reader=conversation_reader,
        note_reader=note_reader,
        document_reader=document_reader,
        export_reader=export_reader,
        binary_dependency_checker=binary_dependency_checker,
    )
    if not generated.get("ok"):
        reason_code = _safe_reason(generated.get("reason_code"))
        return _failure(
            reason_code,
            status=_http_status_for_reason(reason_code),
            store_state="generation_failed",
            export_technical=generated.get("export_v1_technical", {}),
        )

    export_user = generated.get("export_v1_user") or {}
    export_technical = generated.get("export_v1_technical") or {}
    export_format = workspace_folder_exports.normalize_export_format(
        generated.get("export_format") or export_user.get("format")
    )
    title = workspace_folder_exports.sanitize_export_title(export_user.get("title"))
    target_name = workspace_folder_exports.sanitize_export_target_name(title, export_format)
    title_hash = workspace_folder_exports.title_hash_for_target(target_name)
    if not title or not target_name or not export_format:
        return _failure(
            workspace_folder_exports.REASON_NAME_INVALID,
            status=400,
            store_state="blocked",
            export_name_hash=title_hash,
        )

    try:
        existing_exports = exports_module.list_exports(
            folder_id,
            include_deleted=False,
            fail_closed=True,
        )
    except Exception:
        return _failure(
            workspace_folder_exports.REASON_LOOKUP_FAILED,
            status=503,
            store_state="lookup_failed",
            export_name_hash=title_hash,
        )
    validation = workspace_folder_exports.validate_export_title(
        title,
        export_format=export_format,
        existing_exports=existing_exports,
    )
    if not validation.get("ok"):
        reason_code = _safe_reason(validation.get("reason_code"))
        return _failure(
            reason_code,
            status=_http_status_for_reason(reason_code),
            store_state="blocked",
            export_name_hash=str(validation.get("title_hash") or title_hash),
        )

    artifact = _artifact_bytes(generated)
    if not artifact:
        return _failure(
            workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED,
            status=502,
            store_state="generation_failed",
            export_name_hash=title_hash,
        )

    try:
        client = _client(nextcloud)
        client.exports_status(target_folder_name)
        put_result = client.put_export(
            target_folder_name,
            target_name,
            artifact,
            media_type=generated.get("export_mime_type") or "",
        )
    except export_client.NextcloudExportClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            store_state="nextcloud_failed",
            http_status_class=exc.status_class,
            export_name_hash=title_hash,
        )

    export_id = workspace_folder_exports.normalize_export_id(export_user.get("export_id"))
    if not export_id:
        return _failure(
            workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED,
            status=502,
            store_state="generation_failed",
            export_name_hash=title_hash,
        )

    try:
        stored = exports_module.upsert_export(
            export_id=export_id,
            workspace_folder_id=folder_id,
            title=title,
            target_name=target_name,
            export_format=export_format,
            source_kind=export_technical.get("source_kind"),
            source_ref=export_technical.get("source_ref"),
            source_hash=export_technical.get("source_hash"),
            content_hash=export_technical.get("content_hash"),
            local_state=workspace_folder_exports.EXPORT_LOCAL_AVAILABLE,
            nextcloud_sync_state=workspace_folder_exports.EXPORT_NEXTCLOUD_LINKED,
            remote_export_ref=_remote_export_ref(export_id, title_hash),
            etag_value=put_result.etag_value,
            etag_hash=hash12(put_result.etag_value),
            byte_size=len(artifact),
            char_count=export_technical.get("counters", {}).get("char_count"),
            reason_code=workspace_folder_exports.REASON_STORE_OK,
        )
    except Exception:
        rollback = _rollback_remote_created_export(
            client,
            target_folder_name=target_folder_name,
            target_name=target_name,
            exports_module=exports_module,
            folder_id=folder_id,
        )
        return _failure(
            workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED,
            status=503,
            store_state="local_persistence_failed",
            export_name_hash=title_hash,
            rollback=rollback,
        )

    _log_event(
        exports_module,
        "exports_v1_store_ok",
        folder_id=folder_id,
        export_id=stored.get("id"),
        reason_code=workspace_folder_exports.REASON_STORE_OK,
        export_name_hash=title_hash,
        http_status_class=put_result.status_class,
    )
    return {
        "ok": True,
        "export": stored,
        "reason_code": workspace_folder_exports.REASON_STORE_OK,
        "status": 201,
        "export_nextcloud": _technical_nextcloud_payload(
            target_name,
            reason_code=workspace_folder_exports.REASON_STORE_OK,
            http_status_class=put_result.status_class,
            store_state="stored",
            etag_hash=hash12(put_result.etag_value),
        ),
    }


def runtime_secret_status() -> dict[str, Any]:
    return export_client.secret_status_from_env()


def hash12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12] if value else ""


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "") or folder_projection.sanitize_nextcloud_folder_name(
        folder.get("display_name")
    )


def _artifact_bytes(generated: Mapping[str, Any]) -> bytes:
    export_bytes = generated.get("export_bytes")
    if isinstance(export_bytes, bytes) and export_bytes:
        return export_bytes
    export_content = generated.get("export_content")
    if isinstance(export_content, str) and export_content:
        return export_content.encode("utf-8")
    return b""


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return export_client.NextcloudExportClient.from_env()


def _remote_export_ref(export_id: str, title_hash: str) -> str:
    short_id = str(export_id or "")[:8] or "redacted"
    name_hash = str(title_hash or "")[:12] or "redacted"
    return f"workspace-export:{short_id}:{name_hash}"


def _rollback_remote_created_export(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    exports_module: Any,
    folder_id: str,
) -> dict[str, Any]:
    try:
        result = client.delete_export(target_folder_name, target_name, missing_ok=True)
        reason_code = result.reason_code
        http_status_class = result.status_class
        ok = True
    except export_client.NextcloudExportClientError as exc:
        reason_code = exc.reason_code
        http_status_class = exc.status_class
        ok = False
    _log_event(
        exports_module,
        "exports_v1_store_compensation",
        level="warning",
        folder_id=folder_id,
        reason_code=reason_code,
        export_name_hash=workspace_folder_exports.title_hash_for_target(target_name),
        http_status_class=http_status_class,
    )
    return {
        "ok": ok,
        "reason_code": reason_code,
        "http_status_class": http_status_class,
    }


def _failure(
    reason_code: str,
    *,
    status: int,
    store_state: str,
    http_status_class: str = "none",
    export_name_hash: str = "",
    rollback: Mapping[str, Any] | None = None,
    export_technical: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": _safe_reason(reason_code),
        "status": int(status or 500),
        "export": {
            "status": _export_status_for_failure(reason_code),
            "reason_code": _safe_reason(reason_code),
        },
        "export_v1_technical": dict(export_technical or {}),
        "export_nextcloud": {
            "store_state": store_state,
            "reason_code": _safe_reason(reason_code),
            "export_name_hash": export_name_hash,
            "http_status_class": http_status_class,
            "rollback": dict(rollback or {}),
        },
    }


def _technical_nextcloud_payload(
    target_name: str,
    *,
    reason_code: str,
    http_status_class: str,
    store_state: str,
    etag_hash: str = "",
) -> dict[str, Any]:
    payload = {
        "store_state": store_state,
        "reason_code": _safe_reason(reason_code),
        "export_name_hash": workspace_folder_exports.title_hash_for_target(target_name),
        "http_status_class": http_status_class,
    }
    if etag_hash:
        payload["etag_hash"] = etag_hash
        payload["etag_present"] = True
    else:
        payload["etag_present"] = False
    return payload


def _export_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_exports.REASON_NAME_CONFLICT:
        return workspace_folder_exports.EXPORT_LOCAL_CONFLICT
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        workspace_folder_exports.REASON_FOLDER_INVALID,
        workspace_folder_exports.REASON_FOLDER_DELETED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING,
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE,
        workspace_folder_exports.REASON_LOOKUP_FAILED,
    }:
        return workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE
    if reason_code == workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED:
        return workspace_folder_exports.EXPORT_LOCAL_SYNC_ERROR
    return workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        workspace_folder_exports.REASON_FOLDER_DELETED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        workspace_folder_exports.REASON_NAME_CONFLICT,
        workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code in {
        workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING,
    }:
        return 404
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_INVALID,
        workspace_folder_exports.REASON_NAME_INVALID,
        workspace_folder_exports.REASON_SOURCE_MISSING,
        workspace_folder_exports.REASON_SOURCE_AMBIGUOUS,
        workspace_folder_exports.REASON_SOURCE_UNSUPPORTED,
        workspace_folder_exports.REASON_FORMAT_UNSUPPORTED,
    }:
        return 400
    if reason_code in {
        workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE,
        workspace_folder_exports.REASON_TOO_LARGE,
    }:
        return 413
    if reason_code in {
        workspace_folder_exports.REASON_LOOKUP_FAILED,
        workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED,
    }:
        return 503
    return 502


def _safe_reason(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if text in workspace_folder_exports.REASON_CODE_CATALOG:
        return text
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _log_event(exports_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(exports_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
