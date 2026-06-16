from __future__ import annotations

import logging
from typing import Any, Optional

import psycopg

import config
from admin import runtime_settings
from . import runtime_db_bootstrap
from . import workspace_folder_nextcloud_runtime
from . import workspace_folder_nextcloud_links_store
from . import workspace_folders_store


logger = logging.getLogger("frida.workspace_folders")

WORKSPACE_FOLDER_ICON_KEYS = workspace_folders_store.WORKSPACE_FOLDER_ICON_KEYS
DEFAULT_ICON_KEY = workspace_folders_store.DEFAULT_ICON_KEY
NEXTCLOUD_LOGICAL_ROOT = workspace_folders_store.NEXTCLOUD_LOGICAL_ROOT
NEXTCLOUD_SYNC_STATES = (
    workspace_folders_store.NEXTCLOUD_SYNC_LOCAL_ONLY,
    workspace_folders_store.NEXTCLOUD_SYNC_PENDING,
    workspace_folders_store.NEXTCLOUD_SYNC_LINKED,
    workspace_folders_store.NEXTCLOUD_SYNC_ERROR,
    workspace_folders_store.NEXTCLOUD_SYNC_CONFLICT,
    workspace_folders_store.NEXTCLOUD_SYNC_DELETED,
)
NEXTCLOUD_SHARE_STATES = (
    workspace_folders_store.NEXTCLOUD_SHARE_UNKNOWN,
    workspace_folders_store.NEXTCLOUD_SHARE_EXPECTED,
    workspace_folders_store.NEXTCLOUD_SHARE_CONFIRMED,
    workspace_folders_store.NEXTCLOUD_SHARE_ERROR,
)


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def normalize_workspace_folder_id(value: Optional[str]) -> Optional[str]:
    return workspace_folders_store.normalize_workspace_folder_id(value)


def normalize_icon_key(value: Any) -> Optional[str]:
    return workspace_folders_store.normalize_icon_key(value)


def sanitize_display_name(value: Any) -> str:
    return workspace_folders_store.sanitize_display_name(value)


def sanitize_description(value: Any) -> str:
    return workspace_folders_store.sanitize_description(value)


def sanitize_nextcloud_folder_name(value: Any) -> str:
    return workspace_folders_store.sanitize_nextcloud_folder_name(value)


def nextcloud_folder_name_key(value: Any) -> str:
    return workspace_folders_store.nextcloud_folder_name_key(value)


def validate_workspace_folder_display_name(
    value: Any,
    *,
    current_folder_id: Optional[str] = None,
) -> dict[str, Any]:
    return workspace_folders_store.validate_workspace_folder_name(
        value,
        existing_folders=list_workspace_folders(include_deleted=False),
        current_folder_id=current_folder_id,
    )


def coerce_sort_order(value: Any) -> Optional[int]:
    return workspace_folders_store.coerce_sort_order(value)


def list_workspace_folders(*, include_deleted: bool = False) -> list[dict[str, Any]]:
    return workspace_folders_store.list_workspace_folders(
        include_deleted=include_deleted,
        db_conn_func=_db_conn,
        logger=logger,
    )


def get_workspace_folder(folder_id: str, *, include_deleted: bool = False) -> Optional[dict[str, Any]]:
    return workspace_folders_store.get_workspace_folder(
        folder_id,
        include_deleted=include_deleted,
        db_conn_func=_db_conn,
        logger=logger,
    )


def create_workspace_folder(
    *,
    display_name: str,
    icon_key: str = DEFAULT_ICON_KEY,
    description: str = "",
    sort_order: Optional[int] = None,
    folder_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    return workspace_folders_store.create_workspace_folder(
        display_name=display_name,
        icon_key=icon_key,
        description=description,
        sort_order=sort_order,
        folder_id=folder_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def create_workspace_folder_nextcloud_first(
    *,
    display_name: str,
    icon_key: str = DEFAULT_ICON_KEY,
    description: str = "",
    sort_order: Optional[int] = None,
    folder_id: Optional[str] = None,
) -> dict[str, Any]:
    return workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
        display_name=display_name,
        icon_key=icon_key,
        description=description,
        sort_order=sort_order,
        folder_id=folder_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def update_workspace_folder(
    folder_id: str,
    *,
    display_name: Optional[str] = None,
    icon_key: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> Optional[dict[str, Any]]:
    return workspace_folders_store.update_workspace_folder(
        folder_id,
        display_name=display_name,
        icon_key=icon_key,
        description=description,
        sort_order=sort_order,
        db_conn_func=_db_conn,
        logger=logger,
    )


def rename_workspace_folder_nextcloud_first(
    folder_id: str,
    *,
    display_name: str,
    icon_key: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
) -> dict[str, Any]:
    return workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
        folder_id,
        display_name=display_name,
        icon_key=icon_key,
        description=description,
        sort_order=sort_order,
        db_conn_func=_db_conn,
        logger=logger,
    )


def soft_delete_workspace_folder(folder_id: str) -> Optional[dict[str, Any]]:
    return workspace_folders_store.soft_delete_workspace_folder(
        folder_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def runtime_nextcloud_secret_status() -> dict[str, Any]:
    return workspace_folder_nextcloud_runtime.runtime_secret_status()


def upsert_workspace_folder_nextcloud_link(
    *,
    workspace_folder_id: str,
    nextcloud_sync_state: str,
    nextcloud_folder_ref: str = "",
    nextcloud_name_hash: str = "",
    last_sync_reason_code: str = "",
    last_sync_operation: str = "",
    nextcloud_share_state: str = workspace_folder_nextcloud_links_store.NEXTCLOUD_SHARE_UNKNOWN,
) -> Optional[dict[str, Any]]:
    return workspace_folder_nextcloud_links_store.upsert_link(
        workspace_folder_id=workspace_folder_id,
        nextcloud_sync_state=nextcloud_sync_state,
        nextcloud_folder_ref=nextcloud_folder_ref,
        nextcloud_name_hash=nextcloud_name_hash,
        last_sync_reason_code=last_sync_reason_code,
        last_sync_operation=last_sync_operation,
        nextcloud_share_state=nextcloud_share_state,
        db_conn_func=_db_conn,
        logger=logger,
    )
