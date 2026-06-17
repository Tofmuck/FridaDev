from __future__ import annotations

"""Fail-closed inventory access for Documents V1 existing-file reconciliation."""

from typing import Any

from . import workspace_document_nextcloud_client as document_client


class WorkspaceDocumentExistingInventoryError(RuntimeError):
    """Raised when existing-file inventory cannot be trusted."""

    def __init__(self, scope: str):
        super().__init__(document_client.REASON_EXISTING_INVENTORY_FAILED)
        self.reason_code = document_client.REASON_EXISTING_INVENTORY_FAILED
        self.scope = scope if scope in {"folders", "files"} else "unknown"


def list_active_folders(workspace_folders_module: Any) -> list[dict[str, Any]]:
    list_func = getattr(workspace_folders_module, "list_workspace_folders", None)
    if not callable(list_func):
        raise WorkspaceDocumentExistingInventoryError("folders")
    try:
        return [dict(item or {}) for item in list_func() or [] if not item.get("deleted_at")]
    except Exception:
        raise WorkspaceDocumentExistingInventoryError("folders") from None


def list_folder_files(workspace_files_module: Any, folder_id: str) -> list[dict[str, Any]]:
    list_func = getattr(workspace_files_module, "list_workspace_files", None)
    if not callable(list_func):
        raise WorkspaceDocumentExistingInventoryError("files")
    try:
        return [dict(item or {}) for item in list_func(folder_id) or []]
    except Exception:
        raise WorkspaceDocumentExistingInventoryError("files") from None


def record_inventory_failure(
    result: dict[str, Any],
    *,
    scope: str,
    folder_summary: dict[str, Any] | None = None,
    folder_ref: str = "",
) -> None:
    result["summary"]["error_files"] += 1
    if folder_summary is not None:
        folder_summary["error_files"] += 1
    result["events"].append(
        {
            "folder_ref": folder_ref,
            "file_ref": "",
            "operation": f"inventory_{scope}",
            "verdict": "failed",
            "reason_code": document_client.REASON_EXISTING_INVENTORY_FAILED,
            "document_name_hash": "",
            "http_status_class": "none",
            "source_preserved": True,
        }
    )
