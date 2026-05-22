"""DB/disk helpers for workspace OCR derivatives."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from . import workspace_files_store


def get_workspace_file_storage_row(
    folder_id: str,
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
) -> Optional[dict[str, Any]]:
    normalized_folder = workspace_files_store.normalize_workspace_folder_id(folder_id)
    normalized_file = workspace_files_store.normalize_workspace_file_id(file_id)
    if not normalized_folder or not normalized_file:
        return None
    with db_conn_func() as conn:
        with workspace_files_store._cursor(conn) as cur:
            cur.execute(
                """
                SELECT
                    id, workspace_folder_id, display_name, original_filename, storage_key,
                    content_kind, media_kind, mime_type, source_extension, byte_size,
                    sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                    status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                FROM workspace_files
                WHERE id = %s::uuid
                  AND workspace_folder_id = %s::uuid
                  AND deleted_at IS NULL
                LIMIT 1
                """,
                (normalized_file, normalized_folder),
            )
            row = cur.fetchone()
    return dict(row) if row else None


def find_ocr_derived_file(
    folder_id: str,
    source_file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
) -> Optional[dict[str, Any]]:
    normalized_folder = workspace_files_store.normalize_workspace_folder_id(folder_id)
    normalized_source = workspace_files_store.normalize_workspace_file_id(source_file_id)
    if not normalized_folder or not normalized_source:
        return None
    with db_conn_func() as conn:
        with workspace_files_store._cursor(conn) as cur:
            cur.execute(
                """
                SELECT
                    id, workspace_folder_id, display_name, original_filename, storage_key,
                    content_kind, media_kind, mime_type, source_extension, byte_size,
                    sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                    status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                FROM workspace_files
                WHERE workspace_folder_id = %s::uuid
                  AND source_file_id = %s::uuid
                  AND source_kind = %s
                  AND deleted_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (normalized_folder, normalized_source, workspace_files_store.SOURCE_KIND_OCR_DERIVED),
            )
            row = cur.fetchone()
    return workspace_files_store.serialize_workspace_file_row(row, storage_root=storage_root, include_disk_status=True) if row else None


def read_file_bytes(storage_root: Path, storage_key: str) -> bytes:
    return workspace_files_store.workspace_file_path(storage_root, storage_key).read_bytes()


def update_workspace_text_file(
    folder_id: str,
    file_id: str,
    *,
    content: bytes,
    metadata: Mapping[str, Any],
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized_folder = workspace_files_store.normalize_workspace_folder_id(folder_id)
    normalized_file = workspace_files_store.normalize_workspace_file_id(file_id)
    if not normalized_folder or not normalized_file:
        return None
    data = bytes(content or b"")
    digest = workspace_files_store._sha256_hex(data)
    storage_key = ""
    old_content: bytes | None = None
    try:
        with db_conn_func() as conn:
            with workspace_files_store._cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT storage_key
                    FROM workspace_files
                    WHERE id = %s::uuid
                      AND workspace_folder_id = %s::uuid
                      AND deleted_at IS NULL
                    LIMIT 1
                    """,
                    (normalized_file, normalized_folder),
                )
                row = cur.fetchone()
        if not row:
            workspace_files_store.log_content_free_event(
                logger,
                "edit_missing",
                level="warning",
                folder_id=normalized_folder,
                file_id=normalized_file,
                reason_code="workspace_file_missing",
            )
            return None
        raw_storage_key = row.get("storage_key") if isinstance(row, Mapping) else row[0]
        storage_key = str(raw_storage_key or "")
        try:
            old_content = read_file_bytes(storage_root, storage_key)
        except Exception:
            old_content = None
        workspace_files_store.write_file_bytes(storage_root, storage_key, data)
    except Exception as exc:
        workspace_files_store.log_content_free_event(
            logger,
            "edit_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            byte_size=len(data),
            reason_code=workspace_files_store.REASON_WORKSPACE_FILE_DISK_MISSING,
            error_type=type(exc).__name__,
        )
        return None

    try:
        with db_conn_func() as conn:
            with workspace_files_store._cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_files
                    SET byte_size = %s,
                        sha256 = %s,
                        sha256_12 = %s,
                        text_chars = %s,
                        text_sha256_12 = %s,
                        status = %s,
                        reason_code = %s,
                        updated_at = now()
                    WHERE id = %s::uuid
                      AND workspace_folder_id = %s::uuid
                      AND deleted_at IS NULL
                    RETURNING
                        id, workspace_folder_id, display_name, original_filename, storage_key,
                        content_kind, media_kind, mime_type, source_extension, byte_size,
                        sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                        status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                    """,
                    (
                        len(data),
                        digest,
                        digest[:12],
                        workspace_files_store._safe_int(metadata.get("text_chars")),
                        workspace_files_store._safe_text(metadata.get("text_sha256_12"), 12),
                        workspace_files_store._safe_text(metadata.get("status") or workspace_files_store.STATUS_ACTIVE, 40),
                        workspace_files_store._safe_text(metadata.get("reason_code"), 80),
                        normalized_file,
                        normalized_folder,
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        item = workspace_files_store.serialize_workspace_file_row(row, storage_root=storage_root, include_disk_status=True)
        if item is not None:
            workspace_files_store.log_content_free_event(
                logger,
                "edit_ok",
                folder_id=normalized_folder,
                file_id=normalized_file,
                media_kind=item.get("media_kind"),
                content_kind=item.get("content_kind"),
                mime_type=item.get("mime_type"),
                byte_size=item.get("byte_size"),
                sha256_12=item.get("sha256_12"),
                status=item.get("status"),
                reason_code=item.get("reason_code"),
            )
        return item
    except Exception as exc:
        if old_content is not None and storage_key:
            try:
                workspace_files_store.write_file_bytes(storage_root, storage_key, old_content)
            except Exception:
                pass
        workspace_files_store.log_content_free_event(
            logger,
            "edit_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            byte_size=len(data),
            reason_code=workspace_files_store.REASON_WORKSPACE_FILE_DB_MISSING,
            error_type=type(exc).__name__,
        )
        return None
