from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Optional

import psycopg

import config
from admin import runtime_settings
from . import runtime_db_bootstrap
from . import workspace_file_selection_prompt
from . import workspace_file_selections_store


logger = logging.getLogger("frida.workspace_files")

SOURCE = workspace_file_selections_store.SOURCE
REASON_NOT_SELECTED = workspace_file_selections_store.REASON_NOT_SELECTED
REASON_MISSING = workspace_file_selections_store.REASON_MISSING
REASON_DELETED = workspace_file_selections_store.REASON_DELETED
REASON_DISK_MISSING = workspace_file_selections_store.REASON_DISK_MISSING
REASON_TOO_LARGE = workspace_file_selections_store.REASON_TOO_LARGE
REASON_TYPE_UNSUPPORTED = workspace_file_selections_store.REASON_TYPE_UNSUPPORTED
REASON_UNREADABLE = workspace_file_selections_store.REASON_UNREADABLE
REASON_OCR_REQUIRED = workspace_file_selections_store.REASON_OCR_REQUIRED
REASON_MODEL_UNSUPPORTED = workspace_file_selections_store.REASON_MODEL_UNSUPPORTED
REASON_SELECTION_STALE = workspace_file_selections_store.REASON_SELECTION_STALE
REASON_RUNTIME_UNAVAILABLE = workspace_file_selections_store.REASON_RUNTIME_UNAVAILABLE


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _storage_root() -> Path:
    return Path(
        str(
            getattr(config, "WORKSPACE_FILES_DIR", "")
            or Path(config.__file__).resolve().parent / "conv" / "_workspace_files"
        )
    )


def list_workspace_file_selections(conversation_id: str) -> list[dict[str, Any]]:
    return workspace_file_selections_store.list_workspace_file_selections(
        conversation_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def select_workspace_file(conversation_id: str, file_id: str) -> dict[str, Any]:
    return workspace_file_selections_store.select_workspace_file(
        conversation_id,
        file_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def deselect_workspace_file(conversation_id: str, file_id: str) -> bool:
    return workspace_file_selections_store.deselect_workspace_file(
        conversation_id,
        file_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def clear_stale_selections_for_conversation(
    conversation_id: str,
    *,
    workspace_folder_id: Optional[str],
) -> int:
    return workspace_file_selections_store.clear_stale_selections_for_conversation(
        conversation_id,
        workspace_folder_id=workspace_folder_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def mark_workspace_file_deleted(file_id: str) -> int:
    return workspace_file_selections_store.mark_workspace_file_deleted(
        file_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def list_selected_files_for_prompt(conversation_id: str) -> list[dict[str, Any]]:
    return workspace_file_selection_prompt.list_selected_files_for_prompt(
        conversation_id,
        db_conn_func=_db_conn,
        storage_root=_storage_root(),
        logger=logger,
    )


def record_selection_injected(conversation_id: str, file_id: str, *, turn_id: str) -> bool:
    return workspace_file_selections_store.record_selection_injected(
        conversation_id,
        file_id,
        turn_id=turn_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def record_selection_excluded(
    conversation_id: str,
    file_id: str,
    *,
    turn_id: str,
    reason_code: str,
) -> bool:
    return workspace_file_selections_store.record_selection_excluded(
        conversation_id,
        file_id,
        turn_id=turn_id,
        reason_code=reason_code,
        db_conn_func=_db_conn,
        logger=logger,
    )
