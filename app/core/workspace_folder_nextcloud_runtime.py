from __future__ import annotations

import uuid
from typing import Any, Callable

from . import workspace_folder_nextcloud_client as nextcloud_client
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as nextcloud_projection
from . import workspace_folder_standard_subfolders
from . import workspace_folders_store


def create_workspace_folder_nextcloud_first(
    *,
    display_name: str,
    icon_key: str,
    description: str,
    sort_order: int | None,
    db_conn_func: Callable[[], Any],
    logger: Any,
    client: Any | None = None,
    folder_id: str | None = None,
) -> dict[str, Any]:
    existing = workspace_folders_store.list_workspace_folders(
        include_deleted=False,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    validation = workspace_folders_store.validate_workspace_folder_name(
        display_name,
        existing_folders=existing,
    )
    if not validation.get("ok"):
        return _validation_error(validation)

    target_name = str(validation.get("nextcloud_target_name") or "")
    try:
        nextcloud = _client(client)
        nextcloud.create_folder(target_name)
    except nextcloud_client.NextcloudFolderClientError as exc:
        return _nextcloud_error(exc, operation="create")

    standards = workspace_folder_standard_subfolders.ensure_standard_subfolders(
        nextcloud=nextcloud,
        parent_name=target_name,
        nextcloud_name_hash=str(validation.get("nextcloud_name_hash") or ""),
    )
    if not standards["ok"]:
        rollback = _rollback_created_folder(nextcloud, target_name, logger=logger)
        payload = workspace_folder_standard_subfolders.standard_failure_payload(standards)
        payload["rollback_reason_code"] = rollback
        payload["last_sync_operation"] = "create"
        return payload

    normalized_id = workspace_folders_store.normalize_workspace_folder_id(folder_id) or str(uuid.uuid4())
    folder = workspace_folders_store.create_workspace_folder(
        display_name=str(validation["display_name"]),
        icon_key=icon_key,
        description=description,
        sort_order=sort_order,
        folder_id=normalized_id,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    if folder is None:
        rollback = _rollback_created_folder(nextcloud, target_name, logger=logger)
        return _local_persistence_error(rollback)

    try:
        _upsert_link(
            workspace_folder_id=normalized_id,
            target_name=target_name,
            reason_code=nextcloud_client.REASON_CREATE_OK,
            operation="create",
            db_conn_func=db_conn_func,
            logger=logger,
        )
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        local_compensation = _tombstone_created_folder(
            normalized_id,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        rollback = _rollback_created_folder(nextcloud, target_name, logger=logger)
        return _local_persistence_error(rollback, local_compensation_status=local_compensation)

    linked = workspace_folders_store.get_workspace_folder(normalized_id, db_conn_func=db_conn_func, logger=logger)
    if linked is None:
        local_compensation = _tombstone_created_folder(
            normalized_id,
            db_conn_func=db_conn_func,
            logger=logger,
        )
        rollback = _rollback_created_folder(nextcloud, target_name, logger=logger)
        return _local_persistence_error(rollback, local_compensation_status=local_compensation)
    return {"ok": True, "folder": linked, "reason_code": nextcloud_client.REASON_CREATE_OK}


def rename_workspace_folder_nextcloud_first(
    folder_id: str,
    *,
    display_name: str,
    icon_key: str | None = None,
    description: str | None = None,
    sort_order: int | None = None,
    db_conn_func: Callable[[], Any],
    logger: Any,
    client: Any | None = None,
) -> dict[str, Any]:
    normalized = workspace_folders_store.normalize_workspace_folder_id(folder_id)
    if not normalized:
        return _error("workspace_folder_id_invalid", status=400)

    existing_folder = workspace_folders_store.get_workspace_folder(normalized, db_conn_func=db_conn_func, logger=logger)
    if existing_folder is None:
        return _error("workspace_folder_not_found", status=404)
    if existing_folder.get("nextcloud_sync_state") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _error(nextcloud_client.REASON_TARGET_MISSING, status=409, sync_state=nextcloud_links.NEXTCLOUD_SYNC_ERROR)

    existing = workspace_folders_store.list_workspace_folders(
        include_deleted=False,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    validation = workspace_folders_store.validate_workspace_folder_name(
        display_name,
        existing_folders=existing,
        current_folder_id=normalized,
    )
    if not validation.get("ok"):
        return _validation_error(validation)

    old_target_name = workspace_folders_store.sanitize_nextcloud_folder_name(existing_folder.get("display_name"))
    new_target_name = str(validation.get("nextcloud_target_name") or "")
    moved = old_target_name != new_target_name

    try:
        nextcloud = _client(client)
    except nextcloud_client.NextcloudFolderClientError as exc:
        return _nextcloud_error(exc, operation="rename")
    if moved:
        try:
            pending = nextcloud_links.mark_link_rename_pending(
                workspace_folder_id=normalized,
                expected_nextcloud_folder_ref=str(
                    existing_folder.get("nextcloud_folder_ref") or ""
                ),
                expected_nextcloud_name_hash=str(
                    existing_folder.get("nextcloud_name_hash") or ""
                ),
                db_conn_func=db_conn_func,
                logger=logger,
            )
        except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
            return _local_persistence_error(nextcloud_client.REASON_ROLLBACK_OK)
        if pending is None:
            return _local_persistence_error(nextcloud_client.REASON_ROLLBACK_OK)

    try:
        if moved:
            nextcloud.move_folder(old_target_name, new_target_name)
    except nextcloud_client.NextcloudFolderClientError as exc:
        if moved and exc.http_status > 0:
            _restore_old_link(normalized, old_target_name, db_conn_func=db_conn_func, logger=logger)
        return _nextcloud_error(exc, operation="rename")

    try:
        _upsert_link(
            workspace_folder_id=normalized,
            target_name=new_target_name,
            reason_code=nextcloud_client.REASON_RENAME_OK,
            operation="rename",
            db_conn_func=db_conn_func,
            logger=logger,
        )
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        rollback = _rollback_renamed_folder(nextcloud, new_target_name, old_target_name, moved=moved, logger=logger)
        if rollback == nextcloud_client.REASON_ROLLBACK_OK:
            _restore_old_link(normalized, old_target_name, db_conn_func=db_conn_func, logger=logger)
        return _local_persistence_error(rollback)

    fields: dict[str, Any] = {"display_name": str(validation["display_name"])}
    if icon_key is not None:
        fields["icon_key"] = icon_key
    if description is not None:
        fields["description"] = description
    if sort_order is not None:
        fields["sort_order"] = sort_order

    updated = workspace_folders_store.update_workspace_folder(
        normalized,
        db_conn_func=db_conn_func,
        logger=logger,
        **fields,
    )
    if updated is None:
        rollback = _rollback_renamed_folder(nextcloud, new_target_name, old_target_name, moved=moved, logger=logger)
        if rollback == nextcloud_client.REASON_ROLLBACK_OK:
            _restore_old_link(normalized, old_target_name, db_conn_func=db_conn_func, logger=logger)
        return _local_persistence_error(rollback)
    return {"ok": True, "folder": updated, "reason_code": nextcloud_client.REASON_RENAME_OK}


def runtime_secret_status() -> dict[str, Any]:
    return nextcloud_client.secret_status_from_env()


def _client(client: Any | None) -> Any:
    return client if client is not None else nextcloud_client.NextcloudFolderClient.from_env()


def _upsert_link(
    *,
    workspace_folder_id: str,
    target_name: str,
    reason_code: str,
    operation: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> None:
    target_key = target_name.casefold()
    name_hash = nextcloud_projection.hash12(target_key)
    folder_uuid = workspace_folders_store.normalize_workspace_folder_id(workspace_folder_id) or str(workspace_folder_id)
    folder_ref = f"workspace-folder:{folder_uuid[:8]}:{name_hash or 'invalid'}"
    nextcloud_links.upsert_link(
        workspace_folder_id=folder_uuid,
        nextcloud_sync_state=nextcloud_links.NEXTCLOUD_SYNC_LINKED,
        nextcloud_folder_ref=folder_ref,
        nextcloud_name_hash=name_hash,
        last_sync_reason_code=reason_code,
        last_sync_operation=operation,
        nextcloud_share_state=nextcloud_links.NEXTCLOUD_SHARE_EXPECTED,
        db_conn_func=db_conn_func,
        logger=logger,
    )


def _restore_old_link(
    folder_id: str,
    old_target_name: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> None:
    try:
        _upsert_link(
            workspace_folder_id=folder_id,
            target_name=old_target_name,
            reason_code=nextcloud_client.REASON_ROLLBACK_OK,
            operation="rename",
            db_conn_func=db_conn_func,
            logger=logger,
        )
    except nextcloud_links.WorkspaceFolderNextcloudLinkPersistenceError:
        logger.warning(
            "workspace_folder_nextcloud_link_restore_failed id=%s reason_code=%s",
            folder_id,
            nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
        )


def _rollback_created_folder(nextcloud: Any, target_name: str, *, logger: Any) -> str:
    # A collection can already contain descendants. Depth-0 status and the
    # MKCOL response do not prove exclusive ownership of the whole subtree.
    _ = (nextcloud, target_name, logger)
    return nextcloud_client.REASON_ROLLBACK_OWNERSHIP_UNVERIFIED


def _tombstone_created_folder(
    folder_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> str:
    tombstoned = workspace_folders_store.soft_delete_workspace_folder(
        folder_id,
        db_conn_func=db_conn_func,
        logger=logger,
    )
    if tombstoned is not None:
        return "done"
    logger.warning(
        "workspace_folder_local_compensation_failed id=%s reason_code=%s",
        folder_id,
        nextcloud_client.REASON_LOCAL_COMPENSATION_FAILED,
    )
    return "failed"


def _rollback_renamed_folder(
    nextcloud: Any,
    new_target_name: str,
    old_target_name: str,
    *,
    moved: bool,
    logger: Any,
) -> str:
    if not moved:
        return nextcloud_client.REASON_ROLLBACK_OK
    try:
        nextcloud.move_folder(new_target_name, old_target_name)
        return nextcloud_client.REASON_ROLLBACK_OK
    except nextcloud_client.NextcloudFolderClientError:
        logger.warning(
            "workspace_folder_nextcloud_rename_rollback_failed reason_code=%s",
            nextcloud_client.REASON_ROLLBACK_FAILED,
        )
        return nextcloud_client.REASON_ROLLBACK_FAILED


def _validation_error(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "ok": False,
        "status": 409 if "conflict" in str(validation.get("reason_code") or "") else 400,
        "reason_code": str(validation.get("reason_code") or "workspace_folder_name_invalid"),
        "nextcloud_reason_code": str(validation.get("nextcloud_reason_code") or validation.get("reason_code") or ""),
        "nextcloud_sync_state": str(validation.get("nextcloud_sync_state") or nextcloud_links.NEXTCLOUD_SYNC_ERROR),
        "nextcloud_share_state": str(validation.get("nextcloud_share_state") or nextcloud_links.NEXTCLOUD_SHARE_UNKNOWN),
        "nextcloud_name_hash": str(validation.get("nextcloud_name_hash") or ""),
        "error": "nom de repertoire invalide",
    }


def _nextcloud_error(exc: nextcloud_client.NextcloudFolderClientError, *, operation: str) -> dict[str, Any]:
    status = 409 if exc.reason_code == nextcloud_client.REASON_CONFLICT else 502
    return _error(
        exc.reason_code,
        status=status,
        sync_state=nextcloud_links.NEXTCLOUD_SYNC_CONFLICT
        if exc.reason_code == nextcloud_client.REASON_CONFLICT
        else nextcloud_links.NEXTCLOUD_SYNC_ERROR,
        operation=operation,
    )


def _local_persistence_error(
    rollback_reason_code: str,
    *,
    local_compensation_status: str = "not_needed",
) -> dict[str, Any]:
    payload = _error(
        nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
        status=500,
        sync_state=nextcloud_links.NEXTCLOUD_SYNC_ERROR,
        rollback_reason_code=rollback_reason_code,
    )
    if local_compensation_status != "not_needed":
        payload["local_compensation_status"] = local_compensation_status
    if local_compensation_status == "failed":
        payload["local_compensation_reason_code"] = nextcloud_client.REASON_LOCAL_COMPENSATION_FAILED
    return payload


def _error(
    reason_code: str,
    *,
    status: int,
    sync_state: str = nextcloud_links.NEXTCLOUD_SYNC_ERROR,
    operation: str = "",
    rollback_reason_code: str = "",
) -> dict[str, Any]:
    payload = {
        "ok": False,
        "status": int(status),
        "error": _message_for_reason(reason_code),
        "reason_code": reason_code,
        "nextcloud_reason_code": reason_code,
        "nextcloud_sync_state": sync_state,
        "nextcloud_share_state": nextcloud_links.NEXTCLOUD_SHARE_ERROR,
    }
    if operation:
        payload["last_sync_operation"] = operation
    if rollback_reason_code:
        payload["rollback_reason_code"] = rollback_reason_code
    return payload


def _message_for_reason(reason_code: str) -> str:
    if reason_code == nextcloud_client.REASON_CONFLICT:
        return "conflit Nextcloud sur ce nom"
    if reason_code == nextcloud_client.REASON_AUTH_FAILED:
        return "authentification Nextcloud impossible"
    if reason_code == nextcloud_client.REASON_TARGET_MISSING:
        return "dossier Nextcloud cible introuvable"
    if reason_code == nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED:
        return "synchronisation locale incomplete"
    return "operation Nextcloud impossible"
