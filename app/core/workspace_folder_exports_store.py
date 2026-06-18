from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Optional

from . import workspace_folder_exports

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


class WorkspaceFolderExportPersistenceError(RuntimeError):
    """Raised when Exports V1 local read-model persistence fails."""


class WorkspaceFolderExportLookupError(RuntimeError):
    """Raised when Exports V1 local read-model lookup cannot be trusted."""

    reason_code = workspace_folder_exports.REASON_LOOKUP_FAILED

    def __init__(
        self,
        operation: str,
        *,
        export_id: str = "",
        workspace_folder_id: str = "",
    ) -> None:
        super().__init__(self.reason_code)
        self.operation = _safe_lookup_operation(operation)
        self.export_id = workspace_folder_exports.normalize_export_id(export_id)
        self.workspace_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
            workspace_folder_id
        )


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_folder_exports (
            id                       UUID PRIMARY KEY,
            workspace_folder_id      UUID        NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
            title                    TEXT        NOT NULL DEFAULT '',
            title_hash               TEXT        NOT NULL DEFAULT '',
            target_name              TEXT        NOT NULL DEFAULT '',
            export_format            TEXT        NOT NULL DEFAULT 'md',
            source_kind              TEXT        NOT NULL DEFAULT 'conversation',
            source_ref               TEXT        NOT NULL DEFAULT '',
            source_hash              TEXT        NOT NULL DEFAULT '',
            content_hash             TEXT        NOT NULL DEFAULT '',
            local_state              TEXT        NOT NULL DEFAULT 'available',
            nextcloud_sync_state     TEXT        NOT NULL DEFAULT 'linked',
            remote_export_ref        TEXT        NOT NULL DEFAULT '',
            etag_value               TEXT        NOT NULL DEFAULT '',
            etag_hash                TEXT        NOT NULL DEFAULT '',
            byte_size                BIGINT      NOT NULL DEFAULT 0,
            char_count               INTEGER     NOT NULL DEFAULT 0,
            reason_code              TEXT        NOT NULL DEFAULT '',
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at               TIMESTAMPTZ,
            CONSTRAINT workspace_folder_exports_local_state_chk
                CHECK (local_state IN ('available', 'sync_error', 'conflict', 'deleted', 'unavailable')),
            CONSTRAINT workspace_folder_exports_nextcloud_state_chk
                CHECK (nextcloud_sync_state IN ('linked', 'sync_error', 'deleted')),
            CONSTRAINT workspace_folder_exports_format_chk
                CHECK (export_format IN ('md', 'txt', 'docx', 'pdf')),
            CONSTRAINT workspace_folder_exports_source_kind_chk
                CHECK (source_kind IN ('conversation', 'message_selection', 'frida_response', 'note', 'document', 'export'))
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS workspace_folder_id UUID;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS title_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS target_name TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS export_format TEXT NOT NULL DEFAULT 'md';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_kind TEXT NOT NULL DEFAULT 'conversation';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS source_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS content_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS local_state TEXT NOT NULL DEFAULT 'available';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'linked';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS remote_export_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS etag_value TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS etag_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS byte_size BIGINT NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS char_count INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_exports ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
    ):
        cur.execute(column_sql)
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_folder_active_idx
        ON workspace_folder_exports (workspace_folder_id, deleted_at, updated_at DESC);
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_folder_exports_folder_title_format_active_idx
        ON workspace_folder_exports (workspace_folder_id, title_hash, export_format)
        WHERE deleted_at IS NULL;
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_state_idx
        ON workspace_folder_exports (local_state, nextcloud_sync_state, deleted_at);
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_exports_source_idx
        ON workspace_folder_exports (workspace_folder_id, source_kind, source_hash);
        """
    )


def serialize_export_row(row: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    export_id = workspace_folder_exports.normalize_export_id(row.get("id"))
    folder_id = workspace_folder_exports.normalize_workspace_folder_id(row.get("workspace_folder_id"))
    if not export_id or not folder_id:
        return None
    export_format = workspace_folder_exports.normalize_export_format(row.get("export_format"))
    etag_value = _text(row.get("etag_value"), 512)
    etag_hash = _hash12(row.get("etag_hash"))
    if etag_value and not etag_hash:
        etag_hash = workspace_folder_exports.workspace_folder_nextcloud_projection.hash12(etag_value)
    return {
        "id": export_id,
        "workspace_folder_id": folder_id,
        "title": workspace_folder_exports.sanitize_export_title(row.get("title")),
        "title_hash": _hash12(row.get("title_hash")),
        "target_name": _target_name(row.get("target_name"), export_format=export_format),
        "export_format": export_format,
        "source_kind": workspace_folder_exports.normalize_source_kind(row.get("source_kind")),
        "source_ref": _safe_ref(row.get("source_ref")),
        "source_hash": _hash12(row.get("source_hash")),
        "content_hash": _hash12(row.get("content_hash")),
        "local_state": _local_state(row.get("local_state")),
        "nextcloud_sync_state": _nextcloud_state(row.get("nextcloud_sync_state")),
        "remote_export_ref": _safe_ref(row.get("remote_export_ref")),
        "etag_value": etag_value,
        "etag_hash": etag_hash,
        "byte_size": _safe_int(row.get("byte_size")),
        "char_count": _safe_int(row.get("char_count")),
        "reason_code": _reason(row.get("reason_code")),
        "created_at": workspace_folder_exports._ts_to_iso(row.get("created_at")),
        "updated_at": workspace_folder_exports._ts_to_iso(row.get("updated_at")),
        "deleted_at": workspace_folder_exports._ts_to_iso(row.get("deleted_at")),
    }


def list_exports(
    workspace_folder_id: str,
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
    fail_closed: bool = True,
) -> list[dict[str, Any]]:
    folder_id = workspace_folder_exports.normalize_workspace_folder_id(workspace_folder_id)
    if not folder_id:
        return []
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                deleted_sql = "" if include_deleted else "AND deleted_at IS NULL"
                cur.execute(
                    f"""
                    SELECT id, workspace_folder_id, title, title_hash, target_name,
                           export_format, source_kind, source_ref, source_hash, content_hash,
                           local_state, nextcloud_sync_state, remote_export_ref,
                           etag_value, etag_hash, byte_size, char_count, reason_code,
                           created_at, updated_at, deleted_at
                    FROM workspace_folder_exports
                    WHERE workspace_folder_id = %s::uuid {deleted_sql}
                    ORDER BY updated_at DESC, created_at DESC
                    """,
                    (folder_id,),
                )
                rows = cur.fetchall()
        return [export for export in (serialize_export_row(row) for row in rows) if export]
    except Exception as exc:
        _log_lookup_failure(
            logger,
            "list_failed",
            workspace_folder_id=folder_id,
            error_type=type(exc).__name__,
        )
        if fail_closed:
            raise WorkspaceFolderExportLookupError(
                "list", workspace_folder_id=folder_id
            ) from None
        return []


def get_export(
    export_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
    fail_closed: bool = True,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_exports.normalize_export_id(export_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT id, workspace_folder_id, title, title_hash, target_name,
                           export_format, source_kind, source_ref, source_hash, content_hash,
                           local_state, nextcloud_sync_state, remote_export_ref,
                           etag_value, etag_hash, byte_size, char_count, reason_code,
                           created_at, updated_at, deleted_at
                    FROM workspace_folder_exports
                    WHERE id = %s::uuid
                    """,
                    (normalized,),
                )
                return serialize_export_row(cur.fetchone())
    except Exception as exc:
        _log_lookup_failure(
            logger,
            "get_failed",
            export_id=normalized,
            error_type=type(exc).__name__,
        )
        if fail_closed:
            raise WorkspaceFolderExportLookupError("get", export_id=normalized) from None
        return None


def upsert_export(
    *,
    export_id: str,
    workspace_folder_id: str,
    title: str,
    target_name: str,
    export_format: str,
    source_kind: str,
    source_ref: str = "",
    source_hash: str = "",
    content_hash: str = "",
    local_state: str = workspace_folder_exports.EXPORT_LOCAL_AVAILABLE,
    nextcloud_sync_state: str = workspace_folder_exports.EXPORT_NEXTCLOUD_LINKED,
    remote_export_ref: str = "",
    etag_value: str = "",
    etag_hash: str = "",
    byte_size: int = 0,
    char_count: int = 0,
    reason_code: str = workspace_folder_exports.REASON_CREATE_OK,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    normalized_export_id = workspace_folder_exports.normalize_export_id(export_id)
    folder_id = workspace_folder_exports.normalize_workspace_folder_id(workspace_folder_id)
    fmt = workspace_folder_exports.normalize_export_format(export_format)
    source = workspace_folder_exports.normalize_source_kind(source_kind)
    if not normalized_export_id or not folder_id or not fmt or not source:
        raise WorkspaceFolderExportPersistenceError(
            workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED
        )
    title_value = workspace_folder_exports.sanitize_export_title(title)
    target = _target_name(target_name or title_value, export_format=fmt)
    if not title_value or not target:
        raise WorkspaceFolderExportPersistenceError(workspace_folder_exports.REASON_NAME_INVALID)
    title_hash = workspace_folder_exports.title_hash_for_target(target)
    etag_raw = _text(etag_value, 512)
    etag_hash_value = _hash12(etag_hash)
    if etag_raw and not etag_hash_value:
        etag_hash_value = workspace_folder_exports.workspace_folder_nextcloud_projection.hash12(
            etag_raw
        )
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_folder_exports (
                        id, workspace_folder_id, title, title_hash, target_name,
                        export_format, source_kind, source_ref, source_hash, content_hash,
                        local_state, nextcloud_sync_state, remote_export_ref,
                        etag_value, etag_hash, byte_size, char_count, reason_code,
                        created_at, updated_at, deleted_at
                    )
                    VALUES (
                        %s::uuid, %s::uuid, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        now(), now(), NULL
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        workspace_folder_id = EXCLUDED.workspace_folder_id,
                        title = EXCLUDED.title,
                        title_hash = EXCLUDED.title_hash,
                        target_name = EXCLUDED.target_name,
                        export_format = EXCLUDED.export_format,
                        source_kind = EXCLUDED.source_kind,
                        source_ref = EXCLUDED.source_ref,
                        source_hash = EXCLUDED.source_hash,
                        content_hash = EXCLUDED.content_hash,
                        local_state = EXCLUDED.local_state,
                        nextcloud_sync_state = EXCLUDED.nextcloud_sync_state,
                        remote_export_ref = EXCLUDED.remote_export_ref,
                        etag_value = EXCLUDED.etag_value,
                        etag_hash = EXCLUDED.etag_hash,
                        byte_size = EXCLUDED.byte_size,
                        char_count = EXCLUDED.char_count,
                        reason_code = EXCLUDED.reason_code,
                        updated_at = now(),
                        deleted_at = NULL
                    RETURNING id, workspace_folder_id, title, title_hash, target_name,
                              export_format, source_kind, source_ref, source_hash, content_hash,
                              local_state, nextcloud_sync_state, remote_export_ref,
                              etag_value, etag_hash, byte_size, char_count, reason_code,
                              created_at, updated_at, deleted_at
                    """,
                    (
                        normalized_export_id,
                        folder_id,
                        title_value,
                        title_hash,
                        target,
                        fmt,
                        source,
                        _safe_ref(source_ref),
                        _hash12(source_hash),
                        _hash12(content_hash),
                        _local_state(local_state),
                        _nextcloud_state(nextcloud_sync_state),
                        _safe_ref(remote_export_ref),
                        etag_raw,
                        etag_hash_value,
                        _safe_int(byte_size),
                        _safe_int(char_count),
                        _reason(reason_code),
                    ),
                )
                row = serialize_export_row(cur.fetchone())
            conn.commit()
        if not row:
            raise WorkspaceFolderExportPersistenceError(
                workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED
            )
        return row
    except WorkspaceFolderExportPersistenceError:
        raise
    except Exception as exc:
        _log(
            logger,
            "upsert_failed",
            export_id=normalized_export_id,
            error_type=type(exc).__name__,
        )
        raise WorkspaceFolderExportPersistenceError(
            workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED
        ) from None


def tombstone_export(
    export_id: str,
    *,
    reason_code: str = workspace_folder_exports.REASON_SOURCE_UNAVAILABLE,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_exports.normalize_export_id(export_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_folder_exports
                    SET local_state = 'deleted',
                        nextcloud_sync_state = 'deleted',
                        reason_code = %s,
                        updated_at = now(),
                        deleted_at = COALESCE(deleted_at, now())
                    WHERE id = %s::uuid
                    RETURNING id, workspace_folder_id, title, title_hash, target_name,
                              export_format, source_kind, source_ref, source_hash, content_hash,
                              local_state, nextcloud_sync_state, remote_export_ref,
                              etag_value, etag_hash, byte_size, char_count, reason_code,
                              created_at, updated_at, deleted_at
                    """,
                    (_reason(reason_code), normalized),
                )
                row = serialize_export_row(cur.fetchone())
            conn.commit()
        return row
    except Exception as exc:
        _log(logger, "tombstone_failed", export_id=normalized, error_type=type(exc).__name__)
        return None


def _target_name(value: Any, *, export_format: str) -> str:
    target = workspace_folder_exports.sanitize_export_target_name(value, export_format)
    if target:
        return target
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    return " ".join(text.split())[: workspace_folder_exports.EXPORT_TARGET_MAX_CHARS]


def _local_state(value: Any) -> str:
    text = _text(value, 40)
    return (
        text
        if text in workspace_folder_exports.EXPORT_LOCAL_STATES
        else workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE
    )


def _nextcloud_state(value: Any) -> str:
    text = _text(value, 40)
    return (
        text
        if text in workspace_folder_exports.EXPORT_NEXTCLOUD_STATES
        else workspace_folder_exports.EXPORT_NEXTCLOUD_SYNC_ERROR
    )


def _hash12(value: Any) -> str:
    text = _text(value, 12).lower()
    return text if len(text) == 12 and all(char in "0123456789abcdef" for char in text) else ""


def _safe_ref(value: Any) -> str:
    text = _text(value, 180)
    return text if re.fullmatch(r"[A-Za-z0-9:._-]{1,180}", text or "") else ""


def _reason(value: Any) -> str:
    text = _text(value, 120)
    if not text:
        return ""
    if text in workspace_folder_exports.REASON_CODE_CATALOG:
        return text
    return workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _text(value: Any, max_chars: int = 160) -> str:
    text = " ".join(str(value or "").strip().split())
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _safe_lookup_operation(value: Any) -> str:
    text = _text(value, 24)
    return text if text in {"list", "get"} else "lookup"


def _log_lookup_failure(
    logger: Any,
    event: str,
    *,
    workspace_folder_id: str = "",
    export_id: str = "",
    error_type: str = "",
) -> None:
    _log(
        logger,
        event,
        reason_code=workspace_folder_exports.REASON_LOOKUP_FAILED,
        workspace_folder_id=workspace_folder_exports.normalize_workspace_folder_id(
            workspace_folder_id
        ),
        export_id=workspace_folder_exports.normalize_export_id(export_id),
        error_type=_text(error_type, 80),
    )


def _log(logger: Any, event: str, **fields: Any) -> None:
    if logger is None:
        return
    logger.warning("workspace_folder_export_%s", event, extra={"frida": fields})
