from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Mapping, Optional

import psycopg

import config
from admin import runtime_settings
from . import runtime_db_bootstrap
from . import workspace_file_nextcloud_links_store
from . import workspace_file_ocr_store
from . import workspace_files_store


logger = logging.getLogger("frida.workspace_files")

STATUS_ACTIVE = workspace_files_store.STATUS_ACTIVE
STATUS_OCR_REQUIRED = workspace_files_store.STATUS_OCR_REQUIRED
STATUS_DELETED = workspace_files_store.STATUS_DELETED
STATUS_DISK_MISSING = workspace_files_store.STATUS_DISK_MISSING
MEDIA_KIND_TEXT = workspace_files_store.MEDIA_KIND_TEXT
MEDIA_KIND_IMAGE = workspace_files_store.MEDIA_KIND_IMAGE
CONTENT_KIND_DOCUMENT = workspace_files_store.CONTENT_KIND_DOCUMENT
CONTENT_KIND_IMAGE = workspace_files_store.CONTENT_KIND_IMAGE
SOURCE_KIND_UPLOAD = workspace_files_store.SOURCE_KIND_UPLOAD
SOURCE_KIND_OCR_DERIVED = workspace_files_store.SOURCE_KIND_OCR_DERIVED


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _storage_root() -> Path:
    return Path(str(getattr(config, "WORKSPACE_FILES_DIR", "") or Path(config.__file__).resolve().parent / "conv" / "_workspace_files"))


def normalize_workspace_file_id(value: Optional[str]) -> Optional[str]:
    return workspace_files_store.normalize_workspace_file_id(value)


def sanitize_display_name(value: Any) -> str:
    return workspace_files_store.sanitize_display_name(value)


def log_content_free_event(event: str, level: str = "info", **fields: Any) -> None:
    workspace_files_store.log_content_free_event(logger, event, level=level, **fields)


def list_workspace_files(folder_id: str) -> list[dict[str, Any]]:
    return workspace_files_store.list_workspace_files(
        folder_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def get_workspace_file_storage_row(folder_id: str, file_id: str) -> Optional[dict[str, Any]]:
    return workspace_file_ocr_store.get_workspace_file_storage_row(
        folder_id,
        file_id,
        db_conn_func=_db_conn,
    )


def find_ocr_derived_file(folder_id: str, source_file_id: str) -> Optional[dict[str, Any]]:
    return workspace_file_ocr_store.find_ocr_derived_file(
        folder_id,
        source_file_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
    )


def read_file_bytes(storage_key: str) -> bytes:
    return workspace_file_ocr_store.read_file_bytes(_storage_root(), storage_key)


def store_uploaded_file(
    folder_id: str,
    *,
    original_filename: str,
    content: bytes,
    metadata: Mapping[str, Any],
    file_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    return workspace_files_store.store_uploaded_file(
        folder_id,
        original_filename=original_filename,
        content=content,
        metadata=metadata,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
        file_id=file_id,
    )


def update_workspace_text_file(
    folder_id: str,
    file_id: str,
    *,
    content: bytes,
    metadata: Mapping[str, Any],
) -> Optional[dict[str, Any]]:
    return workspace_file_ocr_store.update_workspace_text_file(
        folder_id,
        file_id,
        content=content,
        metadata=metadata,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def delete_workspace_file(folder_id: str, file_id: str) -> Optional[dict[str, Any]]:
    return workspace_files_store.delete_workspace_file(
        folder_id,
        file_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def delete_workspace_files_for_folder(folder_id: str) -> dict[str, Any]:
    return workspace_files_store.delete_workspace_files_for_folder(
        folder_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def get_nextcloud_link(file_id: str) -> Optional[dict[str, Any]]:
    return workspace_file_nextcloud_links_store.get_link(
        file_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def upsert_nextcloud_link(
    *,
    workspace_file_id: str,
    workspace_folder_id: str,
    nextcloud_sync_state: str,
    nextcloud_document_ref: str,
    nextcloud_name_hash: str,
    nextcloud_target_name: str,
    last_sync_reason_code: str,
    last_sync_operation: str,
) -> dict[str, Any]:
    return workspace_file_nextcloud_links_store.upsert_link(
        workspace_file_id=workspace_file_id,
        workspace_folder_id=workspace_folder_id,
        nextcloud_sync_state=nextcloud_sync_state,
        nextcloud_document_ref=nextcloud_document_ref,
        nextcloud_name_hash=nextcloud_name_hash,
        nextcloud_target_name=nextcloud_target_name,
        last_sync_reason_code=last_sync_reason_code,
        last_sync_operation=last_sync_operation,
        db_conn_func=_db_conn,
        logger=logger,
    )


def mark_nextcloud_link_deleted(file_id: str, *, reason_code: str) -> Optional[dict[str, Any]]:
    return workspace_file_nextcloud_links_store.mark_deleted(
        file_id,
        reason_code=reason_code,
        db_conn_func=_db_conn,
        logger=logger,
    )
