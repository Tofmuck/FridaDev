from __future__ import annotations

import hashlib
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from observability import workspace_files_observability

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


DISPLAY_NAME_MAX_CHARS = 180
ORIGINAL_FILENAME_MAX_CHARS = 240
STATUS_ACTIVE = "active"
STATUS_OCR_REQUIRED = "ocr_required"
STATUS_DELETED = "deleted"
STATUS_DISK_MISSING = "disk_missing"
MEDIA_KIND_TEXT = "text"
MEDIA_KIND_IMAGE = "image"
CONTENT_KIND_DOCUMENT = "document"
CONTENT_KIND_IMAGE = "image"
SOURCE_KIND_UPLOAD = "upload"

REASON_WORKSPACE_FILE_DELETED = "workspace_file_deleted"
REASON_WORKSPACE_FILE_DISK_MISSING = "workspace_file_disk_missing"
REASON_WORKSPACE_FILE_DB_MISSING = "workspace_file_db_missing"
REASON_WORKSPACE_FOLDER_FILE_DELETE_FAILED = "workspace_folder_file_delete_failed"


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def content_free_log_fields(fields: Mapping[str, Any]) -> dict[str, str]:
    return workspace_files_observability.content_free_log_fields(fields)


def log_content_free_event(logger: Any, event: str, level: str = "info", **fields: Any) -> None:
    workspace_files_observability.log_content_free_event(logger, event, level=level, **fields)


def normalize_workspace_file_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def normalize_workspace_folder_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def sanitize_display_name(value: Any) -> str:
    name = Path(str(value or "fichier")).name.strip() or "fichier"
    name = collapse_ws(name)
    if len(name) > DISPLAY_NAME_MAX_CHARS:
        name = name[:DISPLAY_NAME_MAX_CHARS].rstrip()
    return name or "fichier"


def sanitize_original_filename(value: Any) -> str:
    name = Path(str(value or "fichier")).name.strip() or "fichier"
    name = collapse_ws(name)
    if len(name) > ORIGINAL_FILENAME_MAX_CHARS:
        name = name[:ORIGINAL_FILENAME_MAX_CHARS].rstrip()
    return name or "fichier"


def normalize_source_extension(value: Any) -> str:
    raw = str(value or "").strip().lower()
    if not raw:
        return ""
    suffix = raw if raw.startswith(".") else f".{raw}"
    if len(suffix) > 16:
        return ""
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789.")
    if any(ch not in allowed for ch in suffix):
        return ""
    return suffix


def storage_key_for(folder_id: str, file_id: str, source_extension: str = "") -> str:
    folder = normalize_workspace_folder_id(folder_id)
    file = normalize_workspace_file_id(file_id)
    if not folder or not file:
        raise ValueError("invalid_workspace_file_storage_key")
    extension = normalize_source_extension(source_extension)
    return f"{folder}/{file}{extension}"


def workspace_file_path(storage_root: Path, storage_key: str) -> Path:
    root = Path(storage_root).resolve()
    relative = Path(str(storage_key or ""))
    if relative.is_absolute() or not relative.parts or ".." in relative.parts:
        raise ValueError("invalid_workspace_file_storage_key")
    return root / relative


def write_file_bytes(storage_root: Path, storage_key: str, content: bytes) -> Path:
    path = workspace_file_path(storage_root, storage_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    tmp.write_bytes(bytes(content or b""))
    tmp.replace(path)
    return path


def delete_file_bytes(storage_root: Path, storage_key: str) -> bool:
    path = workspace_file_path(storage_root, storage_key)
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return True


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(bytes(data or b"")).hexdigest()


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _safe_text(value: Any, max_chars: int) -> str:
    text = str(value or "").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _ts_to_iso(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def serialize_workspace_file_row(
    row: Mapping[str, Any] | None,
    *,
    storage_root: Path | None = None,
    include_disk_status: bool = False,
) -> Optional[dict[str, Any]]:
    if not row:
        return None

    deleted_at = _ts_to_iso(row.get("deleted_at"))
    status = str(row.get("status") or STATUS_ACTIVE).strip() or STATUS_ACTIVE
    reason_code = str(row.get("reason_code") or "").strip()
    storage_key = str(row.get("storage_key") or "").strip()
    if deleted_at:
        status = STATUS_DELETED
        reason_code = reason_code or REASON_WORKSPACE_FILE_DELETED
    elif include_disk_status and storage_root is not None and storage_key:
        try:
            if not workspace_file_path(storage_root, storage_key).exists():
                status = STATUS_DISK_MISSING
                reason_code = REASON_WORKSPACE_FILE_DISK_MISSING
        except Exception:
            status = STATUS_DISK_MISSING
            reason_code = REASON_WORKSPACE_FILE_DISK_MISSING

    return {
        "id": str(row.get("id") or ""),
        "workspace_folder_id": str(row.get("workspace_folder_id") or ""),
        "display_name": sanitize_display_name(row.get("display_name")),
        "original_filename": sanitize_original_filename(row.get("original_filename")),
        "content_kind": _safe_text(row.get("content_kind") or CONTENT_KIND_DOCUMENT, 40),
        "media_kind": _safe_text(row.get("media_kind") or MEDIA_KIND_TEXT, 40),
        "mime_type": _safe_text(row.get("mime_type"), 120),
        "source_extension": normalize_source_extension(row.get("source_extension")),
        "byte_size": _safe_int(row.get("byte_size")),
        "sha256_12": _safe_text(row.get("sha256_12"), 12),
        "text_chars": _safe_int(row.get("text_chars")),
        "text_sha256_12": _safe_text(row.get("text_sha256_12"), 12),
        "image_width": _safe_int(row.get("image_width")),
        "image_height": _safe_int(row.get("image_height")),
        "status": status,
        "reason_code": reason_code,
        "source_kind": _safe_text(row.get("source_kind") or SOURCE_KIND_UPLOAD, 40),
        "source_file_id": str(row.get("source_file_id") or "") or None,
        "created_at": _ts_to_iso(row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("updated_at")),
        "deleted_at": deleted_at,
    }


def list_workspace_files(
    folder_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> list[dict[str, Any]]:
    normalized = normalize_workspace_folder_id(folder_id)
    if not normalized:
        return []
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT
                        id, workspace_folder_id, display_name, original_filename, storage_key,
                        content_kind, media_kind, mime_type, source_extension, byte_size,
                        sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                        status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                    FROM workspace_files
                    WHERE workspace_folder_id = %s::uuid
                      AND deleted_at IS NULL
                    ORDER BY created_at DESC, display_name ASC
                    """,
                    (normalized,),
                )
                rows = cur.fetchall()
        items = [
            item
            for item in (
                serialize_workspace_file_row(row, storage_root=storage_root, include_disk_status=True)
                for row in rows
            )
            if item
        ]
        missing_count = sum(1 for item in items if item.get("status") == STATUS_DISK_MISSING)
        if missing_count:
            log_content_free_event(
                logger,
                "list_disk_missing",
                level="warning",
                folder_id=normalized,
                requested=len(items),
                failed=missing_count,
                reason_code=REASON_WORKSPACE_FILE_DISK_MISSING,
            )
        return items
    except Exception as exc:
        log_content_free_event(
            logger,
            "list_failed",
            level="warning",
            folder_id=normalized,
            reason_code=REASON_WORKSPACE_FILE_DB_MISSING,
            error_type=type(exc).__name__,
        )
        return []


def store_uploaded_file(
    folder_id: str,
    *,
    original_filename: str,
    content: bytes,
    metadata: Mapping[str, Any],
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
    file_id: Optional[str] = None,
) -> Optional[dict[str, Any]]:
    normalized_folder = normalize_workspace_folder_id(folder_id)
    normalized_file = normalize_workspace_file_id(file_id) if file_id else str(uuid.uuid4())
    if not normalized_folder or not normalized_file:
        return None

    data = bytes(content or b"")
    source_extension = normalize_source_extension(metadata.get("source_extension") or Path(original_filename).suffix)
    storage_key = storage_key_for(normalized_folder, normalized_file, source_extension)
    digest = _sha256_hex(data)
    display_name = sanitize_display_name(metadata.get("display_name") or original_filename)
    original = sanitize_original_filename(original_filename)
    row_values = (
        normalized_file,
        normalized_folder,
        display_name,
        original,
        storage_key,
        _safe_text(metadata.get("content_kind") or CONTENT_KIND_DOCUMENT, 40),
        _safe_text(metadata.get("media_kind") or MEDIA_KIND_TEXT, 40),
        _safe_text(metadata.get("mime_type"), 120),
        source_extension,
        len(data),
        digest,
        digest[:12],
        _safe_int(metadata.get("text_chars")),
        _safe_text(metadata.get("text_sha256_12"), 12),
        _safe_int(metadata.get("image_width")),
        _safe_int(metadata.get("image_height")),
        _safe_text(metadata.get("status") or STATUS_ACTIVE, 40),
        _safe_text(metadata.get("reason_code"), 80),
        _safe_text(metadata.get("source_kind") or SOURCE_KIND_UPLOAD, 40),
        metadata.get("source_file_id") or None,
    )

    try:
        write_file_bytes(storage_root, storage_key, data)
    except Exception as exc:
        log_content_free_event(
            logger,
            "upload_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            media_kind=metadata.get("media_kind"),
            content_kind=metadata.get("content_kind"),
            mime_type=metadata.get("mime_type"),
            byte_size=len(data),
            status=metadata.get("status"),
            reason_code="workspace_file_unreadable",
            error_type=type(exc).__name__,
        )
        return None

    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_files (
                        id, workspace_folder_id, display_name, original_filename, storage_key,
                        content_kind, media_kind, mime_type, source_extension, byte_size,
                        sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                        status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                    )
                    VALUES (
                        %s::uuid, %s::uuid, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s::uuid, now(), now(), NULL
                    )
                    RETURNING
                        id, workspace_folder_id, display_name, original_filename, storage_key,
                        content_kind, media_kind, mime_type, source_extension, byte_size,
                        sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                        status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                    """,
                    row_values,
                )
                row = cur.fetchone()
            conn.commit()
        item = serialize_workspace_file_row(row, storage_root=storage_root, include_disk_status=True)
        if item is not None:
            log_content_free_event(
                logger,
                "upload_ok",
                folder_id=normalized_folder,
                file_id=normalized_file,
                media_kind=item.get("media_kind"),
                content_kind=item.get("content_kind"),
                mime_type=item.get("mime_type"),
                byte_size=item.get("byte_size"),
                image_width=item.get("image_width"),
                image_height=item.get("image_height"),
                sha256_12=item.get("sha256_12"),
                status=item.get("status"),
                reason_code=item.get("reason_code"),
            )
        return item
    except Exception as exc:
        try:
            delete_file_bytes(storage_root, storage_key)
        except Exception:
            pass
        log_content_free_event(
            logger,
            "upload_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            media_kind=metadata.get("media_kind"),
            content_kind=metadata.get("content_kind"),
            mime_type=metadata.get("mime_type"),
            byte_size=len(data),
            status=metadata.get("status"),
            reason_code=REASON_WORKSPACE_FILE_DB_MISSING,
            error_type=type(exc).__name__,
        )
        return None


def delete_workspace_file(
    folder_id: str,
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized_folder = normalize_workspace_folder_id(folder_id)
    normalized_file = normalize_workspace_file_id(file_id)
    if not normalized_folder or not normalized_file:
        return None

    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT id, workspace_folder_id, storage_key
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
            log_content_free_event(
                logger,
                "delete_missing",
                level="warning",
                folder_id=normalized_folder,
                file_id=normalized_file,
                reason_code="workspace_file_missing",
            )
            return None
        raw_storage_key = row.get("storage_key") if isinstance(row, Mapping) else row[2]
        storage_key = str(raw_storage_key or "")
        delete_file_bytes(storage_root, storage_key)
    except Exception as exc:
        log_content_free_event(
            logger,
            "delete_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            reason_code=REASON_WORKSPACE_FILE_DISK_MISSING,
            error_type=type(exc).__name__,
        )
        return None

    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_files
                    SET deleted_at = COALESCE(deleted_at, now()),
                        updated_at = now(),
                        status = %s,
                        reason_code = %s
                    WHERE id = %s::uuid
                      AND workspace_folder_id = %s::uuid
                    RETURNING
                        id, workspace_folder_id, display_name, original_filename, storage_key,
                        content_kind, media_kind, mime_type, source_extension, byte_size,
                        sha256, sha256_12, text_chars, text_sha256_12, image_width, image_height,
                        status, reason_code, source_kind, source_file_id, created_at, updated_at, deleted_at
                    """,
                    (STATUS_DELETED, REASON_WORKSPACE_FILE_DELETED, normalized_file, normalized_folder),
                )
                updated = cur.fetchone()
                cur.execute(
                    """
                    UPDATE workspace_file_selections
                    SET deleted_at = COALESCE(deleted_at, now()),
                        updated_at = now(),
                        last_excluded_reason_code = %s
                    WHERE workspace_file_id = %s::uuid
                      AND deleted_at IS NULL
                    """,
                    (REASON_WORKSPACE_FILE_DELETED, normalized_file),
                )
            conn.commit()
        deleted = serialize_workspace_file_row(updated, storage_root=storage_root, include_disk_status=False)
        if deleted is not None:
            deleted["disk_deleted"] = True
            log_content_free_event(
                logger,
                "delete_ok",
                folder_id=normalized_folder,
                file_id=normalized_file,
                media_kind=deleted.get("media_kind"),
                content_kind=deleted.get("content_kind"),
                mime_type=deleted.get("mime_type"),
                byte_size=deleted.get("byte_size"),
                image_width=deleted.get("image_width"),
                image_height=deleted.get("image_height"),
                sha256_12=deleted.get("sha256_12"),
                status=deleted.get("status"),
                reason_code=deleted.get("reason_code"),
            )
        return deleted
    except Exception as exc:
        log_content_free_event(
            logger,
            "delete_failed",
            level="warning",
            folder_id=normalized_folder,
            file_id=normalized_file,
            reason_code=REASON_WORKSPACE_FILE_DB_MISSING,
            error_type=type(exc).__name__,
        )
        return None


def delete_workspace_files_for_folder(
    folder_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> dict[str, Any]:
    normalized = normalize_workspace_folder_id(folder_id)
    if not normalized:
        return {"requested": 0, "deleted": 0, "failed": 0, "failed_file_ids": [], "reason_code": ""}
    active_ids: list[str] = []
    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text
                    FROM workspace_files
                    WHERE workspace_folder_id = %s::uuid
                      AND deleted_at IS NULL
                    """,
                    (normalized,),
                )
                active_ids = [str(row[0]) for row in cur.fetchall()]
    except Exception as exc:
        log_content_free_event(
            logger,
            "folder_delete_scan_failed",
            level="warning",
            folder_id=normalized,
            requested=0,
            deleted=0,
            failed=1,
            reason_code=REASON_WORKSPACE_FILE_DB_MISSING,
            error_type=type(exc).__name__,
        )
        return {
            "requested": 0,
            "deleted": 0,
            "failed": 1,
            "failed_file_ids": [],
            "reason_code": REASON_WORKSPACE_FILE_DB_MISSING,
        }

    deleted = 0
    failed_ids: list[str] = []
    for file_id in active_ids:
        if delete_workspace_file(
            normalized,
            file_id,
            db_conn_func=db_conn_func,
            storage_root=storage_root,
            logger=logger,
        ):
            deleted += 1
        else:
            failed_ids.append(file_id)
    failed = len(failed_ids)
    reason_code = "" if failed == 0 else REASON_WORKSPACE_FOLDER_FILE_DELETE_FAILED
    log_content_free_event(
        logger,
        "folder_delete_summary",
        level="warning" if failed else "info",
        folder_id=normalized,
        requested=len(active_ids),
        deleted=deleted,
        failed=failed,
        reason_code=reason_code,
    )
    return {
        "requested": len(active_ids),
        "deleted": deleted,
        "failed": failed,
        "failed_file_ids": failed_ids,
        "reason_code": reason_code,
    }
