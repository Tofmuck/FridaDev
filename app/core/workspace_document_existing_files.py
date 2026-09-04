from __future__ import annotations

"""Controlled Documents V1 placement for existing workspace files.

This module is an operator-facing Lot 7 runner, not a user route. It copies
existing local workspace files into the already-linked Nextcloud Documents
target, persists the local link, and preserves the local source.
"""

from typing import Any, Mapping

from . import workspace_document_nextcloud_client as document_client
from . import workspace_document_existing_inventory as inventory
from . import workspace_document_nextcloud_runtime as document_runtime
from . import workspace_file_nextcloud_links_store as file_nextcloud_links
from . import workspace_folder_nextcloud_links_store as folder_nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection


def reconcile_existing_workspace_documents(
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any,
    nextcloud: Any | None = None,
    execute: bool = True,
) -> dict[str, Any]:
    """Copy active local-only workspace files into Documents when eligible."""

    result = _empty_result(execute=execute)
    try:
        folders = inventory.list_active_folders(workspace_folders_module)
    except inventory.WorkspaceDocumentExistingInventoryError as exc:
        inventory.record_inventory_failure(result, scope=exc.scope)
        _finalize_result(result)
        return result
    result["summary"]["active_folders"] = len(folders)

    client: Any | None = None
    for folder in folders:
        folder_id = str(folder.get("id") or "")
        folder_ref = document_runtime.hash12(folder_id)
        folder_linked = (
            str(folder.get("nextcloud_sync_state") or "")
            == folder_nextcloud_links.NEXTCLOUD_SYNC_LINKED
        )
        target_folder_name = _target_folder_name(folder)
        folder_summary = _folder_summary(folder_ref=folder_ref, linked=folder_linked)
        result["folders"].append(folder_summary)
        try:
            files = inventory.list_folder_files(workspace_files_module, folder_id)
        except inventory.WorkspaceDocumentExistingInventoryError as exc:
            inventory.record_inventory_failure(
                result,
                scope=exc.scope,
                folder_summary=folder_summary,
                folder_ref=folder_ref,
            )
            continue

        seen_targets: set[str] = set()
        for item in files:
            if item.get("deleted_at") or str(item.get("status") or "") == "deleted":
                continue
            result["summary"]["active_files"] += 1
            folder_summary["active_files"] += 1
            file_id = str(item.get("id") or "")
            file_ref = document_runtime.hash12(file_id)
            link_lookup = _get_link(workspace_files_module, file_id)
            if link_lookup["failed"]:
                result["summary"]["error_files"] += 1
                folder_summary["error_files"] += 1
                _record_event(
                    result,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    operation="link_lookup",
                    verdict="failed",
                    reason_code=document_client.REASON_LINK_LOOKUP_FAILED,
                )
                continue
            link = link_lookup["link"]
            if link and str(link.get("nextcloud_sync_state") or "") == file_nextcloud_links.NEXTCLOUD_FILE_SYNC_LINKED:
                result["summary"]["linked_files"] += 1
                folder_summary["linked_files"] += 1
                target_name = str(link.get("nextcloud_target_name") or "")
                if target_name:
                    seen_targets.add(target_name.casefold())
                _record_event(
                    result,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    operation="already_linked",
                    verdict="met",
                    reason_code=document_client.REASON_EXISTING_SOURCE_PRESERVED,
                    document_name_hash=link.get("nextcloud_name_hash") or "",
                )
                continue

            result["summary"]["local_only_files"] += 1
            folder_summary["local_only_files"] += 1
            if not folder_linked or not target_folder_name:
                result["summary"]["ineligible_files"] += 1
                folder_summary["ineligible_files"] += 1
                _record_event(
                    result,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    operation="eligibility",
                    verdict="not_applicable",
                    reason_code=document_client.REASON_FOLDER_NOT_LINKED,
                )
                continue

            target_name = document_runtime.sanitize_nextcloud_document_name(
                item.get("display_name") or item.get("original_filename"),
                item.get("source_extension"),
            )
            document_name_hash = document_runtime.hash12(target_name.casefold())
            if not target_name:
                _record_error(
                    result,
                    folder_summary,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    reason_code=document_client.REASON_NAME_INVALID,
                    document_name_hash="",
                )
                continue
            if target_name.casefold() in seen_targets:
                _record_conflict(
                    result,
                    folder_summary,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    reason_code=document_client.REASON_EXISTING_COPY_CONFLICT,
                    document_name_hash=document_name_hash,
                )
                continue
            result["summary"]["copy_required_files"] += 1
            folder_summary["copy_required_files"] += 1
            if not execute:
                _record_event(
                    result,
                    folder_ref=folder_ref,
                    file_ref=file_ref,
                    operation="inventory",
                    verdict="partial",
                    reason_code=document_client.REASON_EXISTING_COPY_REQUIRED,
                    document_name_hash=document_name_hash,
                )
                continue

            if client is None:
                try:
                    client = _client(nextcloud)
                except document_client.NextcloudDocumentClientError as exc:
                    _record_error(
                        result,
                        folder_summary,
                        folder_ref=folder_ref,
                        file_ref=file_ref,
                        reason_code=exc.reason_code,
                        document_name_hash=document_name_hash,
                    )
                    continue
            copied = _copy_existing_file(
                folder_id=folder_id,
                folder_ref=folder_ref,
                file_id=file_id,
                file_ref=file_ref,
                item=item,
                target_folder_name=target_folder_name,
                target_name=target_name,
                document_name_hash=document_name_hash,
                client=client,
                workspace_files_module=workspace_files_module,
            )
            _merge_copy_result(result, folder_summary, copied)
            if copied["verdict"] == "met":
                seen_targets.add(target_name.casefold())

    _finalize_result(result)
    return result


def _copy_existing_file(
    *,
    folder_id: str,
    folder_ref: str,
    file_id: str,
    file_ref: str,
    item: Mapping[str, Any],
    target_folder_name: str,
    target_name: str,
    document_name_hash: str,
    client: Any,
    workspace_files_module: Any,
) -> dict[str, Any]:
    try:
        documents_status = client.documents_status(target_folder_name)
    except document_client.NextcloudDocumentClientError as exc:
        return _copy_event(
            folder_ref,
            file_ref,
            verdict="failed",
            operation="documents_status",
            reason_code=exc.reason_code,
            document_name_hash=document_name_hash,
            http_status_class=exc.status_class,
        )

    try:
        client.document_status(target_folder_name, target_name)
        return _copy_event(
            folder_ref,
            file_ref,
            verdict="conflict",
            operation="target_status",
            reason_code=document_client.REASON_EXISTING_COPY_CONFLICT,
            document_name_hash=document_name_hash,
            http_status_class="2xx",
        )
    except document_client.NextcloudDocumentClientError as exc:
        if exc.reason_code != document_client.REASON_DOCUMENTS_TARGET_MISSING:
            return _copy_event(
                folder_ref,
                file_ref,
                verdict="failed",
                operation="target_status",
                reason_code=exc.reason_code,
                document_name_hash=document_name_hash,
                http_status_class=exc.status_class,
            )

    source = _source_bytes(
        workspace_files_module,
        folder_id=folder_id,
        file_id=file_id,
    )
    if not source["ok"]:
        return _copy_event(
            folder_ref,
            file_ref,
            verdict="failed",
            operation="source_read",
            reason_code=document_client.REASON_EXISTING_SOURCE_MISSING,
            document_name_hash=document_name_hash,
            http_status_class="none",
        )

    try:
        put_result = client.put_document(
            target_folder_name,
            target_name,
            source["content"],
            media_type=item.get("mime_type") or "",
        )
    except document_client.NextcloudDocumentClientError as exc:
        reason = (
            document_client.REASON_EXISTING_COPY_CONFLICT
            if exc.reason_code == document_client.REASON_NAME_CONFLICT
            else exc.reason_code
        )
        return _copy_event(
            folder_ref,
            file_ref,
            verdict="conflict" if reason == document_client.REASON_EXISTING_COPY_CONFLICT else "failed",
            operation="put",
            reason_code=reason,
            document_name_hash=document_name_hash,
            http_status_class=exc.status_class,
        )

    link = _persist_link(
        workspace_files_module,
        workspace_file_id=file_id,
        workspace_folder_id=folder_id,
        target_name=target_name,
        document_name_hash=document_name_hash,
    )
    if not link["ok"]:
        rollback = _rollback_remote_created(
            client,
            target_folder_name=target_folder_name,
            target_name=target_name,
            etag_value=put_result.etag_value,
        )
        event = _copy_event(
            folder_ref,
            file_ref,
            verdict="failed",
            operation="link_persistence",
            reason_code=document_client.REASON_LINK_PERSISTENCE_FAILED,
            document_name_hash=document_name_hash,
            http_status_class=put_result.status_class,
        )
        event["rollback"] = rollback
        return event

    event = _copy_event(
        folder_ref,
        file_ref,
        verdict="met",
        operation="copy",
        reason_code=document_client.REASON_EXISTING_COPY_OK,
        document_name_hash=document_name_hash,
        http_status_class=put_result.status_class,
    )
    event["source_preserved"] = True
    event["documents_status_class"] = documents_status.status_class
    event["link_state"] = link["state"]
    return event


def _source_bytes(workspace_files_module: Any, *, folder_id: str, file_id: str) -> dict[str, Any]:
    get_row = getattr(workspace_files_module, "get_workspace_file_storage_row", None)
    read_bytes = getattr(workspace_files_module, "read_file_bytes", None)
    if not callable(get_row) or not callable(read_bytes):
        return {"ok": False, "content": b""}
    try:
        row = get_row(folder_id, file_id)
        storage_key = str((row or {}).get("storage_key") or "")
        if not storage_key:
            return {"ok": False, "content": b""}
        return {"ok": True, "content": read_bytes(storage_key)}
    except Exception:
        return {"ok": False, "content": b""}


def _persist_link(
    workspace_files_module: Any,
    *,
    workspace_file_id: str,
    workspace_folder_id: str,
    target_name: str,
    document_name_hash: str,
) -> dict[str, Any]:
    upsert = getattr(workspace_files_module, "upsert_nextcloud_link", None)
    if not callable(upsert):
        return {"ok": False, "state": ""}
    try:
        link = upsert(
            workspace_file_id=workspace_file_id,
            workspace_folder_id=workspace_folder_id,
            nextcloud_sync_state=file_nextcloud_links.NEXTCLOUD_FILE_SYNC_LINKED,
            nextcloud_document_ref=f"workspace-file:{workspace_file_id[:8]}:{document_name_hash}",
            nextcloud_name_hash=document_name_hash,
            nextcloud_target_name=target_name,
            last_sync_reason_code=document_client.REASON_EXISTING_COPY_OK,
            last_sync_operation="reconcile",
        )
    except Exception:
        return {"ok": False, "state": ""}
    return {
        "ok": bool(link),
        "state": str((link or {}).get("nextcloud_sync_state") or ""),
    }


def _rollback_remote_created(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    etag_value: str,
) -> dict[str, Any]:
    if not str(etag_value or "").strip():
        reason_code = document_client.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED
        http_status_class = "none"
        ok = False
    else:
        try:
            result = client.delete_created_document_if_match(
                target_folder_name,
                target_name,
                etag_value=etag_value,
            )
            reason_code = result.reason_code
            http_status_class = result.status_class
            ok = reason_code in {
                document_client.REASON_REMOTE_COMPENSATION_OK,
                document_client.REASON_REMOTE_COMPENSATION_MISSING,
            }
        except document_client.NextcloudDocumentClientError as exc:
            reason_code = (
                exc.reason_code
                if exc.reason_code
                in {
                    document_client.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
                    document_client.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
                    document_client.REASON_REMOTE_COMPENSATION_FAILED,
                }
                else document_client.REASON_REMOTE_COMPENSATION_FAILED
            )
            http_status_class = exc.status_class
            ok = False
    return {
        "ok": ok,
        "reason_code": reason_code,
        "http_status_class": http_status_class,
        "state": document_runtime._remote_compensation_state(reason_code),
    }


def _get_link(workspace_files_module: Any, file_id: str) -> dict[str, Any]:
    get_link = getattr(workspace_files_module, "get_nextcloud_link", None)
    if not callable(get_link):
        return {"failed": False, "link": None}
    try:
        return {"failed": False, "link": get_link(file_id, fail_closed=True)}
    except TypeError:
        try:
            return {"failed": False, "link": get_link(file_id)}
        except Exception:
            return {"failed": True, "link": None}
    except Exception:
        return {"failed": True, "link": None}


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "") or folder_projection.sanitize_nextcloud_folder_name(
        folder.get("display_name")
    )


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return document_client.NextcloudDocumentClient.from_env()


def _empty_result(*, execute: bool) -> dict[str, Any]:
    return {
        "ok": True,
        "verdict": "met",
        "execute": bool(execute),
        "summary": {
            "active_folders": 0,
            "active_files": 0,
            "linked_files": 0,
            "local_only_files": 0,
            "copy_required_files": 0,
            "copied_files": 0,
            "conflict_files": 0,
            "error_files": 0,
            "ineligible_files": 0,
            "source_preserved_files": 0,
            "rollback_ok": 0,
            "rollback_failed": 0,
        },
        "folders": [],
        "events": [],
    }


def _folder_summary(*, folder_ref: str, linked: bool) -> dict[str, Any]:
    return {
        "folder_ref": folder_ref,
        "linked": bool(linked),
        "active_files": 0,
        "linked_files": 0,
        "local_only_files": 0,
        "copy_required_files": 0,
        "copied_files": 0,
        "conflict_files": 0,
        "error_files": 0,
        "ineligible_files": 0,
    }


def _copy_event(
    folder_ref: str,
    file_ref: str,
    *,
    verdict: str,
    operation: str,
    reason_code: str,
    document_name_hash: str,
    http_status_class: str,
) -> dict[str, Any]:
    return {
        "folder_ref": folder_ref,
        "file_ref": file_ref,
        "operation": operation,
        "verdict": verdict,
        "reason_code": reason_code,
        "document_name_hash": document_name_hash,
        "http_status_class": http_status_class,
        "source_preserved": True,
    }


def _merge_copy_result(result: dict[str, Any], folder_summary: dict[str, Any], event: dict[str, Any]) -> None:
    result["events"].append(event)
    verdict = event["verdict"]
    if verdict == "met":
        result["summary"]["copied_files"] += 1
        result["summary"]["source_preserved_files"] += 1
        folder_summary["copied_files"] += 1
    elif verdict == "conflict":
        result["summary"]["conflict_files"] += 1
        folder_summary["conflict_files"] += 1
    else:
        result["summary"]["error_files"] += 1
        folder_summary["error_files"] += 1
    rollback = event.get("rollback")
    if isinstance(rollback, Mapping):
        key = "rollback_ok" if rollback.get("ok") else "rollback_failed"
        result["summary"][key] += 1


def _record_event(
    result: dict[str, Any],
    *,
    folder_ref: str,
    file_ref: str,
    operation: str,
    verdict: str,
    reason_code: str,
    document_name_hash: Any = "",
) -> None:
    result["events"].append(
        {
            "folder_ref": folder_ref,
            "file_ref": file_ref,
            "operation": operation,
            "verdict": verdict,
            "reason_code": reason_code,
            "document_name_hash": str(document_name_hash or ""),
            "http_status_class": "none",
            "source_preserved": True,
        }
    )


def _record_conflict(
    result: dict[str, Any],
    folder_summary: dict[str, Any],
    *,
    folder_ref: str,
    file_ref: str,
    reason_code: str,
    document_name_hash: str,
) -> None:
    result["summary"]["conflict_files"] += 1
    folder_summary["conflict_files"] += 1
    _record_event(
        result,
        folder_ref=folder_ref,
        file_ref=file_ref,
        operation="target_status",
        verdict="conflict",
        reason_code=reason_code,
        document_name_hash=document_name_hash,
    )


def _record_error(
    result: dict[str, Any],
    folder_summary: dict[str, Any],
    *,
    folder_ref: str,
    file_ref: str,
    reason_code: str,
    document_name_hash: str,
) -> None:
    result["summary"]["error_files"] += 1
    folder_summary["error_files"] += 1
    _record_event(
        result,
        folder_ref=folder_ref,
        file_ref=file_ref,
        operation="validation",
        verdict="failed",
        reason_code=reason_code,
        document_name_hash=document_name_hash,
    )


def _finalize_result(result: dict[str, Any]) -> None:
    summary = result["summary"]
    if summary["error_files"] or summary["rollback_failed"]:
        result["ok"] = False
        result["verdict"] = "failed"
    elif summary["conflict_files"] or summary["ineligible_files"]:
        result["ok"] = True
        result["verdict"] = "partial"
    else:
        result["ok"] = True
        result["verdict"] = "met"
