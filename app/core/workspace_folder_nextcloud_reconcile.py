from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from . import workspace_folder_nextcloud_client as nextcloud_client
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as nextcloud_projection
from . import workspace_folder_standard_subfolders
from . import workspace_folders_store


REASON_RECONCILE_EXISTING_OK = "workspace_folder_nextcloud_reconcile_existing_ok"
REASON_RECONCILE_CREATED_OK = "workspace_folder_nextcloud_reconcile_created_ok"
REASON_RECONCILE_ALREADY_LINKED_OK = "workspace_folder_nextcloud_reconcile_already_linked_ok"
REASON_RECONCILE_NO_ACTIVE_FOLDERS = "workspace_folder_nextcloud_reconcile_no_active_folders"
REASON_RECONCILE_EXAMPLE_ABSENT = "workspace_folder_nextcloud_reconcile_example_absent"

EXAMPLE_KEYS = {
    "philosophie": ("philosophie",),
    "conflit_lycee": ("conflit lycee", "conflit lycée"),
}


def reconcile_existing_workspace_folders(
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
    client: Any | None = None,
) -> dict[str, Any]:
    before = workspace_folders_store.list_workspace_folders(
        include_deleted=False,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    records = [_inventory_record(before)]
    if not before:
        records.append(
            _record(
                "LOT9_FINAL_STATE",
                verdict="not_applicable",
                operation="final_state",
                reason_code=REASON_RECONCILE_NO_ACTIVE_FOLDERS,
                counts_after=_counts(before),
                examples=_example_status(before),
            )
        )
        return _summary(records, before, before)

    target_counts = Counter(str(folder.get("nextcloud_target_name") or "").casefold() for folder in before)
    try:
        nextcloud = _client(client)
    except nextcloud_client.NextcloudFolderClientError as exc:
        for folder in before:
            records.append(_record_error(folder, exc, operation="status_existing"))
        after = workspace_folders_store.list_workspace_folders(
            include_deleted=False,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        records.append(
            _record(
                "LOT9_FINAL_STATE",
                verdict="failed",
                operation="final_state",
                reason_code=nextcloud_client.REASON_UNAVAILABLE,
                counts_after=_counts(after),
                examples=_example_status(after),
            )
        )
        return _summary(records, before, after)

    for folder in before:
        records.extend(
            _reconcile_one(
                folder,
                target_counts=target_counts,
                nextcloud=nextcloud,
                db_conn_func=db_conn_func,
                logger=logger,
            )
        )

    after = workspace_folders_store.list_workspace_folders(
        include_deleted=False,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    final_verdict = (
        "met"
        if not any(record.get("verdict") in {"failed", "partial"} for record in records)
        else "partial"
    )
    records.append(
        _record(
            "LOT9_FINAL_STATE",
            verdict=final_verdict,
            operation="final_state",
            reason_code=REASON_RECONCILE_EXISTING_OK if final_verdict == "met" else nextcloud_client.REASON_ERROR_REDACTED,
            counts_after=_counts(after),
            examples=_example_status(after),
        )
    )
    return _summary(records, before, after)


def _reconcile_one(
    folder: Mapping[str, Any],
    *,
    target_counts: Counter[str],
    nextcloud: Any,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    folder_ref = _folder_ref(folder)
    target_name = str(folder.get("nextcloud_target_name") or "")
    target_key = target_name.casefold()
    sync_state = str(folder.get("nextcloud_sync_state") or nextcloud_links.NEXTCLOUD_SYNC_LOCAL_ONLY)

    if not target_name:
        state_persisted = _safe_upsert_state(
            folder,
            nextcloud_links.NEXTCLOUD_SYNC_ERROR,
            "workspace_folder_name_invalid",
            db_conn_func=db_conn_func,
            logger=logger,
        )
        return [
            _record(
                "LOT9_FOLDER_INVALID_TARGET",
                verdict="failed",
                operation="conflict",
                reason_code="workspace_folder_name_invalid",
                folder_ref=folder_ref,
                local_persistence_failed=not state_persisted,
            )
        ]

    if target_counts.get(target_key, 0) > 1:
        state_persisted = _safe_upsert_state(
            folder,
            nextcloud_links.NEXTCLOUD_SYNC_CONFLICT,
            "workspace_folder_name_conflict_sanitized",
            db_conn_func=db_conn_func,
            logger=logger,
        )
        return [
            _record(
                "LOT9_FOLDER_TARGET_COLLISION",
                verdict="failed",
                operation="conflict",
                reason_code="workspace_folder_name_conflict_sanitized",
                folder_ref=folder_ref,
                nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                local_persistence_failed=not state_persisted,
            )
        ]

    try:
        status = nextcloud.folder_status(target_name)
        standards = workspace_folder_standard_subfolders.ensure_standard_subfolders(
            nextcloud=nextcloud,
            parent_name=target_name,
            folder_ref=folder_ref,
            nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
        )
        if not standards["ok"]:
            state_persisted = _safe_upsert_state(
                folder,
                _state_for_standard_reason(str(standards.get("reason_code") or "")),
                str(standards.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED),
                db_conn_func=db_conn_func,
                logger=logger,
            )
            records = list(standards["records"])
            records.append(
                _record(
                    "LOT11_STANDARD_SUBFOLDERS_FAILED",
                    verdict="failed",
                    operation="conflict" if "conflict" in str(standards.get("reason_code") or "") else "status_existing",
                    reason_code=str(standards.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED),
                    folder_ref=folder_ref,
                    nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                    http_status_class="none",
                    local_persistence_failed=not state_persisted,
                )
            )
            return records
        if sync_state == nextcloud_links.NEXTCLOUD_SYNC_LINKED:
            return list(standards["records"]) + [
                _record(
                    "LOT9_STATUS_LINKED_FOLDER",
                    verdict="met",
                    operation="status_existing",
                    reason_code=REASON_RECONCILE_ALREADY_LINKED_OK,
                    folder_ref=folder_ref,
                    nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                    http_status_class=status.status_class,
                )
            ]
        state_persisted = _safe_upsert_state(
            folder,
            nextcloud_links.NEXTCLOUD_SYNC_LINKED,
            REASON_RECONCILE_EXISTING_OK,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        if not state_persisted:
            return list(standards["records"]) + [
                _record(
                    "LOT9_LINK_EXISTING_TARGET_FAILED",
                    verdict="failed",
                    operation="link_existing",
                    reason_code=nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
                    folder_ref=folder_ref,
                    nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                    http_status_class=status.status_class,
                    local_persistence_failed=True,
                )
            ]
        return list(standards["records"]) + [
            _record(
                "LOT9_LINK_EXISTING_TARGET",
                verdict="met",
                operation="link_existing",
                reason_code=REASON_RECONCILE_EXISTING_OK,
                folder_ref=folder_ref,
                nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                http_status_class=status.status_class,
            )
        ]
    except nextcloud_client.NextcloudFolderClientError as exc:
        if exc.reason_code != nextcloud_client.REASON_TARGET_MISSING:
            return [_handle_status_error(folder, exc, logger=logger, db_conn_func=db_conn_func)]

    if sync_state == nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        state_persisted = _safe_upsert_state(
            folder,
            nextcloud_links.NEXTCLOUD_SYNC_ERROR,
            nextcloud_client.REASON_TARGET_MISSING,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        return [
            _record(
                "LOT9_LINKED_TARGET_MISSING",
                verdict="failed",
                operation="status_existing",
                reason_code=nextcloud_client.REASON_TARGET_MISSING,
                folder_ref=folder_ref,
                nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                http_status_class="4xx",
                local_persistence_failed=not state_persisted,
            )
        ]

    try:
        created = nextcloud.create_folder(target_name)
    except nextcloud_client.NextcloudFolderClientError as exc:
        return [_handle_status_error(folder, exc, logger=logger, db_conn_func=db_conn_func, operation="create_missing")]

    standards = workspace_folder_standard_subfolders.ensure_standard_subfolders(
        nextcloud=nextcloud,
        parent_name=target_name,
        folder_ref=folder_ref,
        nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
    )
    if not standards["ok"]:
        rollback = _rollback_created_target(nextcloud, target_name, logger=logger)
        return list(standards["records"]) + [
            _record(
                "LOT11_STANDARD_SUBFOLDERS_CREATE_FAILED_ROLLBACK",
                verdict="failed" if rollback != nextcloud_client.REASON_ROLLBACK_OK else "partial",
                operation="create_missing",
                reason_code=str(standards.get("reason_code") or nextcloud_client.REASON_ERROR_REDACTED),
                folder_ref=folder_ref,
                nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                http_status_class=created.status_class,
                rollback_reason_code=rollback,
            )
        ]

    try:
        _upsert_state(
            folder,
            nextcloud_links.NEXTCLOUD_SYNC_LINKED,
            REASON_RECONCILE_CREATED_OK,
            db_conn_func=db_conn_func,
            logger=logger,
        )
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        rollback = _rollback_created_target(nextcloud, target_name, logger=logger)
        return list(standards["records"]) + [
            _record(
                "LOT9_CREATE_LINK_FAILED_ROLLBACK",
                verdict="failed" if rollback != nextcloud_client.REASON_ROLLBACK_OK else "partial",
                operation="create_missing",
                reason_code=nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
                folder_ref=folder_ref,
                nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
                http_status_class=created.status_class,
                rollback_reason_code=rollback,
            )
        ]

    return list(standards["records"]) + [
        _record(
            "LOT9_CREATE_MISSING_TARGET",
            verdict="met",
            operation="create_missing",
            reason_code=REASON_RECONCILE_CREATED_OK,
            folder_ref=folder_ref,
            nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
            http_status_class=created.status_class,
        )
    ]


def _handle_status_error(
    folder: Mapping[str, Any],
    exc: nextcloud_client.NextcloudFolderClientError,
    *,
    logger: Any,
    db_conn_func: Callable[[], Any],
    operation: str = "status_existing",
) -> dict[str, Any]:
    state = (
        nextcloud_links.NEXTCLOUD_SYNC_CONFLICT
        if exc.reason_code == nextcloud_client.REASON_CONFLICT
        else nextcloud_links.NEXTCLOUD_SYNC_ERROR
    )
    state_persisted = _safe_upsert_state(folder, state, exc.reason_code, db_conn_func=db_conn_func, logger=logger)
    return _record(
        "LOT9_NEXTCLOUD_STATUS_ERROR",
        verdict="failed",
        operation=operation,
        reason_code=exc.reason_code,
        folder_ref=_folder_ref(folder),
        nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
        http_status_class=exc.status_class,
        local_persistence_failed=not state_persisted,
    )


def _safe_upsert_state(
    folder: Mapping[str, Any],
    sync_state: str,
    reason_code: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    try:
        _upsert_state(
            folder,
            sync_state,
            reason_code,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        return True
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        logger.warning(
            "workspace_folder_reconcile_link_state_failed folder_ref=%s reason_code=%s",
            _folder_ref(folder),
            nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
        )
        return False


def _upsert_state(
    folder: Mapping[str, Any],
    sync_state: str,
    reason_code: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> None:
    folder_id = workspace_folders_store.normalize_workspace_folder_id(str(folder.get("id") or ""))
    if not folder_id:
        raise nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError(nextcloud_links.REASON_NEXTCLOUD_ERROR_REDACTED)
    target_name = str(folder.get("nextcloud_target_name") or "")
    target_key = target_name.casefold()
    name_hash = nextcloud_projection.hash12(target_key)
    folder_ref = f"workspace-folder:{folder_id[:8]}:{name_hash or 'invalid'}"
    share_state = (
        nextcloud_links.NEXTCLOUD_SHARE_EXPECTED
        if sync_state in {nextcloud_links.NEXTCLOUD_SYNC_LINKED, nextcloud_links.NEXTCLOUD_SYNC_CONFLICT}
        else nextcloud_links.NEXTCLOUD_SHARE_ERROR
    )
    nextcloud_links.upsert_link(
        workspace_folder_id=folder_id,
        nextcloud_sync_state=sync_state,
        nextcloud_folder_ref=folder_ref,
        nextcloud_name_hash=name_hash,
        last_sync_reason_code=reason_code,
        last_sync_operation="reconcile",
        nextcloud_share_state=share_state,
        db_conn_func=db_conn_func,
        logger=logger,
    )


def _rollback_created_target(nextcloud: Any, target_name: str, *, logger: Any) -> str:
    # Reconciliation cannot prove that the collection subtree is still the
    # one created by this attempt, so automatic recursive deletion is unsafe.
    _ = (nextcloud, target_name, logger)
    return nextcloud_client.REASON_ROLLBACK_OWNERSHIP_UNVERIFIED


def _client(client: Any | None) -> Any:
    return client if client is not None else nextcloud_client.NextcloudFolderClient.from_env()


def _state_for_standard_reason(reason_code: str) -> str:
    if "conflict" in reason_code:
        return nextcloud_links.NEXTCLOUD_SYNC_CONFLICT
    return nextcloud_links.NEXTCLOUD_SYNC_ERROR


def _inventory_record(folders: list[Mapping[str, Any]]) -> dict[str, Any]:
    reason = REASON_RECONCILE_EXISTING_OK if folders else REASON_RECONCILE_NO_ACTIVE_FOLDERS
    return _record(
        "LOT9_INVENTORY_ACTIVE_FOLDERS",
        verdict="met" if folders else "not_applicable",
        operation="inventory",
        reason_code=reason,
        counts_before=_counts(folders),
        examples=_example_status(folders),
    )


def _record_error(
    folder: Mapping[str, Any],
    exc: nextcloud_client.NextcloudFolderClientError,
    *,
    operation: str,
) -> dict[str, Any]:
    return _record(
        "LOT9_NEXTCLOUD_CLIENT_ERROR",
        verdict="failed",
        operation=operation,
        reason_code=exc.reason_code,
        folder_ref=_folder_ref(folder),
        nextcloud_name_hash=str(folder.get("nextcloud_name_hash") or ""),
        http_status_class=exc.status_class,
    )


def _record(
    case_id: str,
    *,
    verdict: str,
    operation: str,
    reason_code: str,
    folder_ref: str = "",
    nextcloud_name_hash: str = "",
    http_status_class: str = "none",
    counts_before: dict[str, Any] | None = None,
    counts_after: dict[str, Any] | None = None,
    examples: dict[str, str] | None = None,
    rollback_reason_code: str = "",
    local_persistence_failed: bool = False,
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
        "nextcloud_delete": rollback_reason_code == nextcloud_client.REASON_ROLLBACK_OK,
        "content_free_scan": True,
    }
    if folder_ref:
        payload["folder_ref"] = folder_ref
    if _is_hash12(nextcloud_name_hash):
        payload["nextcloud_name_hash"] = nextcloud_name_hash
    if counts_before is not None:
        payload["counts_before"] = counts_before
    if counts_after is not None:
        payload["counts_after"] = counts_after
    if examples is not None:
        payload["examples"] = examples
    if rollback_reason_code:
        payload["rollback_reason_code"] = rollback_reason_code
    if local_persistence_failed:
        payload["local_persistence_failed"] = True
    return payload


def _summary(records: list[dict[str, Any]], before: list[Mapping[str, Any]], after: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "ok": not any(record.get("verdict") in {"failed", "partial"} for record in records),
        "records": records,
        "counts_before": _counts(before),
        "counts_after": _counts(after),
        "examples": _example_status(after or before),
    }


def _counts(folders: list[Mapping[str, Any]]) -> dict[str, int]:
    sync_counts = Counter(str(folder.get("nextcloud_sync_state") or "unknown") for folder in folders)
    return {
        "active": len(folders),
        "linked": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_LINKED, 0)),
        "local_only": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_LOCAL_ONLY, 0)),
        "conflict": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_CONFLICT, 0)),
        "errors": int(sync_counts.get(nextcloud_links.NEXTCLOUD_SYNC_ERROR, 0)),
    }


def _example_status(folders: list[Mapping[str, Any]]) -> dict[str, str]:
    statuses = {key: "expected_example_absent" for key in EXAMPLE_KEYS}
    for folder in folders:
        display_key = workspace_folders_store.collapse_ws(folder.get("display_name")).casefold()
        for example_key, aliases in EXAMPLE_KEYS.items():
            if display_key not in aliases:
                continue
            sync_state = str(folder.get("nextcloud_sync_state") or "")
            if sync_state == nextcloud_links.NEXTCLOUD_SYNC_LINKED:
                statuses[example_key] = "present_reconciled"
            elif sync_state in {nextcloud_links.NEXTCLOUD_SYNC_CONFLICT, nextcloud_links.NEXTCLOUD_SYNC_ERROR}:
                statuses[example_key] = "present_no_go"
            else:
                statuses[example_key] = "present_pending"
    return statuses


def _folder_ref(folder: Mapping[str, Any]) -> str:
    folder_id = workspace_folders_store.normalize_workspace_folder_id(str(folder.get("id") or ""))
    if not folder_id:
        return "workspace-folder:invalid"
    name_hash = str(folder.get("nextcloud_name_hash") or "")
    return f"workspace-folder:{folder_id[:8]}:{name_hash if _is_hash12(name_hash) else 'invalid'}"


def _is_hash12(value: str) -> bool:
    return len(value) == 12 and all(char in "0123456789abcdef" for char in value)


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
