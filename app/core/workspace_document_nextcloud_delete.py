from __future__ import annotations

from typing import Any, Mapping

from . import workspace_document_nextcloud_client as document_client
from . import workspace_file_nextcloud_links_store as file_nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection


def prepare_workspace_document_delete_nextcloud_first(
    *,
    folder: Mapping[str, Any],
    file_id: str,
    workspace_files_module: Any,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    link = _get_nextcloud_link(workspace_files_module, file_id)
    if not link:
        return {
            "ok": True,
            "remote_delete_required": False,
            "reason_code": document_client.REASON_DELETE_OK,
            "status": 200,
            "document_nextcloud": {
                "delete_state": "local_only",
                "reason_code": document_client.REASON_DELETE_OK,
                "http_status_class": "none",
            },
        }
    if str(link.get("nextcloud_sync_state") or "") == file_nextcloud_links.NEXTCLOUD_FILE_SYNC_DELETED:
        return {
            "ok": True,
            "remote_delete_required": False,
            "reason_code": document_client.REASON_DELETE_OK,
            "status": 200,
            "document_nextcloud": {
                "delete_state": "already_deleted",
                "reason_code": document_client.REASON_DELETE_OK,
                "document_name_hash": link.get("nextcloud_name_hash") or "",
                "http_status_class": "none",
            },
        }

    target_folder_name = _target_folder_name(folder)
    target_name = str(link.get("nextcloud_target_name") or "")
    if not target_folder_name or not target_name:
        return _delete_failure(
            document_client.REASON_LINK_MISSING,
            status=409,
            document_name_hash=link.get("nextcloud_name_hash") or "",
            delete_state="blocked",
        )

    try:
        client = nextcloud or document_client.NextcloudDocumentClient.from_env()
        result = client.delete_document(target_folder_name, target_name, missing_ok=True)
    except document_client.NextcloudDocumentClientError as exc:
        _log_event(
            workspace_files_module,
            "documents_v1_delete_remote_failed",
            level="warning",
            folder_id=str(folder.get("id") or ""),
            file_id=file_id,
            reason_code=exc.reason_code,
            document_name_hash=link.get("nextcloud_name_hash") or "",
            http_status_class=exc.status_class,
        )
        return _delete_failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            http_status_class=exc.status_class,
            document_name_hash=link.get("nextcloud_name_hash") or "",
            delete_state="remote_failed",
        )

    return {
        "ok": True,
        "remote_delete_required": True,
        "reason_code": document_client.REASON_DELETE_OK,
        "status": 200,
        "document_nextcloud": {
            "delete_state": "remote_deleted",
            "reason_code": document_client.REASON_DELETE_OK,
            "document_name_hash": link.get("nextcloud_name_hash") or "",
            "http_status_class": result.status_class,
        },
    }


def complete_workspace_document_delete(
    *,
    file_id: str,
    workspace_files_module: Any,
) -> dict[str, Any]:
    marker = getattr(workspace_files_module, "mark_nextcloud_link_deleted", None)
    if not callable(marker):
        return {"ok": True, "reason_code": document_client.REASON_DELETE_OK}
    marked = marker(file_id, reason_code=document_client.REASON_DELETE_OK)
    return {
        "ok": bool(marked),
        "reason_code": document_client.REASON_DELETE_OK
        if marked
        else document_client.REASON_LOCAL_DELETE_FAILED,
    }


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "") or folder_projection.sanitize_nextcloud_folder_name(
        folder.get("display_name")
    )


def _get_nextcloud_link(workspace_files_module: Any, file_id: str) -> dict[str, Any] | None:
    getter = getattr(workspace_files_module, "get_nextcloud_link", None)
    if not callable(getter):
        return None
    try:
        return getter(file_id)
    except Exception:
        return None


def _delete_failure(
    reason_code: str,
    *,
    status: int,
    delete_state: str,
    http_status_class: str = "none",
    document_name_hash: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": int(status or 500),
        "document_nextcloud": {
            "delete_state": delete_state,
            "reason_code": reason_code,
            "document_name_hash": document_name_hash,
            "http_status_class": http_status_class,
        },
    }


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        document_client.REASON_DOCUMENTS_TARGET_CONFLICT,
        document_client.REASON_DOCUMENTS_TARGET_NOT_COLLECTION,
        document_client.REASON_LINK_MISSING,
        document_client.REASON_NAME_CONFLICT,
    }:
        return 409
    if reason_code in {document_client.REASON_DOCUMENTS_TARGET_MISSING}:
        return 404
    return 502


def _log_event(workspace_files_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(workspace_files_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
