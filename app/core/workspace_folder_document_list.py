from __future__ import annotations

"""Documents V1 folder list assembly.

This module keeps link lookup and content-free enrichment out of the HTTP layer.
It never calls Nextcloud: it only reads the local workspace file registry and the
local workspace_file -> Nextcloud link state when available.
"""

import uuid
from typing import Any, Mapping

from . import workspace_folder_documents


REASON_LINK_LOOKUP_FAILED = "folder_document_link_lookup_failed"


def list_workspace_folder_documents(
    folder: Mapping[str, Any],
    *,
    workspace_files_module: Any,
) -> list[dict[str, Any]]:
    folder_id = str(folder.get("id") or "")
    items = workspace_files_module.list_workspace_files(folder_id)
    enriched = [
        _attach_content_free_nextcloud_link(item, workspace_files_module=workspace_files_module)
        for item in items
    ]
    return workspace_folder_documents.apply_document_v1_list(enriched, folder=folder)


def _attach_content_free_nextcloud_link(
    item: Mapping[str, Any],
    *,
    workspace_files_module: Any,
) -> dict[str, Any]:
    payload = dict(item or {})
    file_id = str(payload.get("id") or "")
    get_link = getattr(workspace_files_module, "get_nextcloud_link", None)
    if not file_id or not callable(get_link):
        return payload
    try:
        link = get_link(file_id, fail_closed=True)
    except Exception:
        _log_link_lookup_failed(workspace_files_module, payload)
        payload["document_nextcloud_link"] = {
            "lookup_state": "failed",
            "reason_code": REASON_LINK_LOOKUP_FAILED,
        }
        return payload
    if not link:
        return payload
    payload["document_nextcloud_link"] = {
        "lookup_state": "ok",
        "nextcloud_sync_state": link.get("nextcloud_sync_state"),
        "nextcloud_document_ref": link.get("nextcloud_document_ref"),
        "nextcloud_name_hash": link.get("nextcloud_name_hash"),
        "last_sync_reason_code": link.get("last_sync_reason_code"),
        "last_sync_operation": link.get("last_sync_operation"),
        "last_sync_at": link.get("last_sync_at"),
    }
    return payload


def _log_link_lookup_failed(workspace_files_module: Any, item: Mapping[str, Any]) -> None:
    log_func = getattr(workspace_files_module, "log_content_free_event", None)
    if not callable(log_func):
        return
    log_func(
        "documents_v1_list_link_lookup_failed",
        folder_id=_safe_uuid(item.get("workspace_folder_id")),
        file_id=_safe_uuid(item.get("id")),
        reason_code=REASON_LINK_LOOKUP_FAILED,
    )


def _safe_uuid(value: Any) -> str:
    try:
        return str(uuid.UUID(str(value or "").strip()))
    except (TypeError, ValueError):
        return ""
