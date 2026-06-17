from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from . import workspace_folder_nextcloud_client as nextcloud_client
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as nextcloud_projection
from . import workspace_folders_store


STANDARD_SUBFOLDERS = ("Documents", "Notes", "Exports", "Images")


def ensure_standard_subfolders(
    *,
    nextcloud: Any,
    parent_name: str,
    folder_ref: str = "",
    nextcloud_name_hash: str = "",
) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    for standard_name in STANDARD_SUBFOLDERS:
        try:
            status = _folder_status(nextcloud, parent_name, standard_name)
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDER_EXISTING",
                    verdict="met",
                    operation="status_existing",
                    reason_code=nextcloud_client.REASON_STANDARD_SUBFOLDER_EXISTING_OK,
                    standard_subfolder=standard_name,
                    folder_ref=folder_ref,
                    nextcloud_name_hash=nextcloud_name_hash,
                    http_status_class=status.status_class,
                )
            )
            continue
        except nextcloud_client.NextcloudFolderClientError as exc:
            if exc.reason_code != nextcloud_client.REASON_TARGET_MISSING:
                records.append(
                    _record(
                        "LOT11_STANDARD_SUBFOLDER_STATUS_ERROR",
                        verdict="failed",
                        operation="conflict" if exc.reason_code == nextcloud_client.REASON_CONFLICT else "status_existing",
                        reason_code=_standard_reason(exc.reason_code),
                        standard_subfolder=standard_name,
                        folder_ref=folder_ref,
                        nextcloud_name_hash=nextcloud_name_hash,
                        http_status_class=exc.status_class,
                    )
                )
                continue

        try:
            created = _create_folder(nextcloud, parent_name, standard_name)
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDER_CREATED",
                    verdict="met",
                    operation="create_missing",
                    reason_code=nextcloud_client.REASON_STANDARD_SUBFOLDER_CREATED_OK,
                    standard_subfolder=standard_name,
                    folder_ref=folder_ref,
                    nextcloud_name_hash=nextcloud_name_hash,
                    http_status_class=created.status_class,
                )
            )
        except nextcloud_client.NextcloudFolderClientError as exc:
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDER_CREATE_ERROR",
                    verdict="failed",
                    operation="create_missing",
                    reason_code=_standard_reason(exc.reason_code),
                    standard_subfolder=standard_name,
                    folder_ref=folder_ref,
                    nextcloud_name_hash=nextcloud_name_hash,
                    http_status_class=exc.status_class,
                )
            )

    counts = _counts(records)
    ok = counts["failed"] == 0
    return {
        "ok": ok,
        "reason_code": nextcloud_client.REASON_STANDARD_SUBFOLDERS_OK
        if ok
        else _first_failure_reason(records),
        "records": records,
        "counts": counts,
        "standard_subfolders": list(STANDARD_SUBFOLDERS),
    }


def ensure_standard_subfolders_for_linked_folders(
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
    client: Any | None = None,
) -> dict[str, Any]:
    folders = workspace_folders_store.list_workspace_folders(
        include_deleted=False,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    linked = [
        folder
        for folder in folders
        if str(folder.get("nextcloud_sync_state") or "") == nextcloud_links.NEXTCLOUD_SYNC_LINKED
    ]
    records = [
        _record(
            "LOT11_INVENTORY_LINKED_FOLDERS",
            verdict="met" if linked else "not_applicable",
            operation="inventory",
            reason_code=nextcloud_client.REASON_STANDARD_SUBFOLDERS_OK,
            counts_before=_folder_counts(folders),
        )
    ]
    if not linked:
        return _summary(records, folders)

    try:
        nextcloud = _client(client)
    except nextcloud_client.NextcloudFolderClientError as exc:
        for folder in linked:
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDER_CLIENT_ERROR",
                    verdict="failed",
                    operation="status_existing",
                    reason_code=_standard_reason(exc.reason_code),
                    folder_ref=_folder_ref(folder),
                    nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                    http_status_class=exc.status_class,
                )
            )
        return _summary(records, folders)

    for folder in linked:
        target_name = str(folder.get("nextcloud_target_name") or "")
        if not target_name:
            _safe_mark_state(
                folder,
                nextcloud_links.NEXTCLOUD_SYNC_ERROR,
                "workspace_folder_name_invalid",
                db_conn_func=db_conn_func,
                logger=logger,
            )
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDER_INVALID_TARGET",
                    verdict="failed",
                    operation="conflict",
                    reason_code="workspace_folder_name_invalid",
                    folder_ref=_folder_ref(folder),
                    nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                )
            )
            continue

        result = ensure_standard_subfolders(
            nextcloud=nextcloud,
            parent_name=target_name,
            folder_ref=_folder_ref(folder),
            nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
        )
        records.extend(result["records"])
        if not result["ok"]:
            _safe_mark_state(
                folder,
                _state_for_reason(str(result.get("reason_code") or "")),
                str(result.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED),
                db_conn_func=db_conn_func,
                logger=logger,
            )

    return _summary(records, folders)


def standard_failure_payload(result: Mapping[str, Any]) -> dict[str, Any]:
    reason_code = str(result.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED)
    return {
        "ok": False,
        "status": 409 if "conflict" in reason_code else 502,
        "error": "creation des sous-dossiers standards impossible",
        "reason_code": reason_code,
        "nextcloud_reason_code": reason_code,
        "nextcloud_sync_state": _state_for_reason(reason_code),
        "nextcloud_share_state": nextcloud_links.NEXTCLOUD_SHARE_ERROR,
        "standard_subfolder_counts": dict(result.get("counts") or {}),
    }


def _folder_status(nextcloud: Any, parent_name: str, standard_name: str) -> nextcloud_client.NextcloudFolderResponse:
    status_path = getattr(nextcloud, "folder_status_path", None)
    if callable(status_path):
        return status_path(parent_name, standard_name)
    raise nextcloud_client.NextcloudFolderClientError(nextcloud_client.REASON_UNAVAILABLE)


def _create_folder(nextcloud: Any, parent_name: str, standard_name: str) -> nextcloud_client.NextcloudFolderResponse:
    create_path = getattr(nextcloud, "create_folder_path", None)
    if callable(create_path):
        return create_path(parent_name, standard_name)
    raise nextcloud_client.NextcloudFolderClientError(nextcloud_client.REASON_UNAVAILABLE)


def _standard_reason(reason_code: str) -> str:
    if reason_code == nextcloud_client.REASON_CONFLICT:
        return nextcloud_client.REASON_STANDARD_SUBFOLDER_CONFLICT
    if reason_code == nextcloud_client.REASON_AUTH_FAILED:
        return nextcloud_client.REASON_STANDARD_SUBFOLDERS_AUTH_FAILED
    if reason_code == nextcloud_client.REASON_UNAVAILABLE:
        return nextcloud_client.REASON_STANDARD_SUBFOLDERS_UNAVAILABLE
    return nextcloud_client.REASON_ERROR_REDACTED


def _state_for_reason(reason_code: str) -> str:
    if "conflict" in reason_code:
        return nextcloud_links.NEXTCLOUD_SYNC_CONFLICT
    return nextcloud_links.NEXTCLOUD_SYNC_ERROR


def _safe_mark_state(
    folder: Mapping[str, Any],
    sync_state: str,
    reason_code: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    folder_id = workspace_folders_store.normalize_workspace_folder_id(str(folder.get("id") or ""))
    if not folder_id:
        return False
    target_name = str(folder.get("nextcloud_target_name") or "")
    name_hash = nextcloud_projection.hash12(target_name.casefold())
    folder_ref = f"workspace-folder:{folder_id[:8]}:{name_hash or 'invalid'}"
    try:
        nextcloud_links.upsert_link(
            workspace_folder_id=folder_id,
            nextcloud_sync_state=sync_state,
            nextcloud_folder_ref=folder_ref,
            nextcloud_name_hash=name_hash,
            last_sync_reason_code=reason_code,
            last_sync_operation="observe",
            nextcloud_share_state=nextcloud_links.NEXTCLOUD_SHARE_ERROR,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        return True
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        logger.warning(
            "workspace_folder_standard_subfolders_state_failed folder_ref=%s reason_code=%s",
            _folder_ref(folder),
            nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
        )
        return False


def _record(
    case_id: str,
    *,
    verdict: str,
    operation: str,
    reason_code: str,
    standard_subfolder: str = "",
    folder_ref: str = "",
    nextcloud_name_hash: str = "",
    http_status_class: str = "none",
    counts_before: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "case_id": case_id,
        "verdict": verdict,
        "timestamp_utc": _now(),
        "operation": operation,
        "http_status_class": http_status_class,
        "reason_code": reason_code,
        "secret_exposed": False,
        "user_content_touched": False,
        "files_moved": False,
        "nextcloud_delete": False,
        "content_free_scan": True,
    }
    if standard_subfolder in STANDARD_SUBFOLDERS:
        payload["standard_subfolder"] = standard_subfolder
    if folder_ref:
        payload["folder_ref"] = folder_ref
    if _is_hash12(nextcloud_name_hash):
        payload["nextcloud_name_hash"] = nextcloud_name_hash
    if counts_before is not None:
        payload["counts_before"] = counts_before
    return payload


def _counts(records: list[Mapping[str, Any]]) -> dict[str, int]:
    verdicts = Counter(str(record.get("verdict") or "") for record in records)
    operations = Counter(str(record.get("operation") or "") for record in records)
    return {
        "inspected": len(records),
        "existing": int(operations.get("status_existing", 0)),
        "created": int(operations.get("create_missing", 0)),
        "failed": int(verdicts.get("failed", 0)),
    }


def _folder_counts(folders: list[Mapping[str, Any]]) -> dict[str, int]:
    sync_counts = Counter(str(folder.get("nextcloud_sync_state") or "unknown") for folder in folders)
    return {
        "active": len(folders),
        "linked": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_LINKED, 0)),
        "errors": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_ERROR, 0)),
        "conflict": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_CONFLICT, 0)),
    }


def _summary(records: list[dict[str, Any]], folders: list[Mapping[str, Any]]) -> dict[str, Any]:
    ok = not any(record.get("verdict") == "failed" for record in records)
    return {
        "ok": ok,
        "reason_code": nextcloud_client.REASON_STANDARD_SUBFOLDERS_OK
        if ok
        else _first_failure_reason(records),
        "records": records,
        "counts": _counts(records),
        "folder_counts": _folder_counts(folders),
        "standard_subfolders": list(STANDARD_SUBFOLDERS),
    }


def _first_failure_reason(records: list[Mapping[str, Any]]) -> str:
    for record in records:
        if record.get("verdict") == "failed":
            return str(record.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED)
    return nextcloud_client.REASON_ERROR_REDACTED


def _folder_ref(folder: Mapping[str, Any]) -> str:
    folder_id = workspace_folders_store.normalize_workspace_folder_id(str(folder.get("id") or ""))
    if not folder_id:
        return "workspace-folder:invalid"
    name_hash = str(folder.get("nextcloud_name_hash") or "")
    return f"workspace-folder:{folder_id[:8]}:{name_hash if _is_hash12(name_hash) else 'invalid'}"


def _client(client: Any | None) -> Any:
    return client if client is not None else nextcloud_client.NextcloudFolderClient.from_env()


def _is_hash12(value: str) -> bool:
    return len(value) == 12 and all(char in "0123456789abcdef" for char in value)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
