from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Optional

from . import workspace_folder_notes

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


class WorkspaceFolderNotePersistenceError(RuntimeError):
    """Raised when Notes V1 local read-model persistence fails."""


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_folder_notes (
            id                       UUID PRIMARY KEY,
            workspace_folder_id      UUID        NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
            title                    TEXT        NOT NULL DEFAULT '',
            title_hash               TEXT        NOT NULL DEFAULT '',
            target_name              TEXT        NOT NULL DEFAULT '',
            local_state              TEXT        NOT NULL DEFAULT 'available',
            nextcloud_sync_state     TEXT        NOT NULL DEFAULT 'linked',
            remote_note_ref          TEXT        NOT NULL DEFAULT '',
            etag_value               TEXT        NOT NULL DEFAULT '',
            etag_hash                TEXT        NOT NULL DEFAULT '',
            markdown_char_count      INTEGER     NOT NULL DEFAULT 0,
            reason_code              TEXT        NOT NULL DEFAULT '',
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at               TIMESTAMPTZ,
            CONSTRAINT workspace_folder_notes_local_state_chk
                CHECK (local_state IN ('available', 'sync_error', 'conflict', 'deleted', 'unavailable')),
            CONSTRAINT workspace_folder_notes_nextcloud_state_chk
                CHECK (nextcloud_sync_state IN ('linked', 'sync_error', 'deleted'))
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS workspace_folder_id UUID;",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS title TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS title_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS target_name TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS local_state TEXT NOT NULL DEFAULT 'available';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'linked';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS remote_note_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS etag_value TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS etag_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS markdown_char_count INTEGER NOT NULL DEFAULT 0;",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_notes ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ;",
    ):
        cur.execute(column_sql)
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_notes_folder_active_idx
        ON workspace_folder_notes (workspace_folder_id, deleted_at, updated_at DESC);
        """
    )
    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS workspace_folder_notes_folder_title_active_idx
        ON workspace_folder_notes (workspace_folder_id, title_hash)
        WHERE deleted_at IS NULL;
        """
    )
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_notes_state_idx
        ON workspace_folder_notes (local_state, nextcloud_sync_state, deleted_at);
        """
    )


def serialize_note_row(row: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    note_id = workspace_folder_notes.normalize_note_id(row.get("id"))
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(row.get("workspace_folder_id"))
    if not note_id or not folder_id:
        return None
    return {
        "id": note_id,
        "workspace_folder_id": folder_id,
        "title": workspace_folder_notes.sanitize_note_title(row.get("title")),
        "title_hash": _hash12(row.get("title_hash")),
        "target_name": _target_name(row.get("target_name")),
        "local_state": _local_state(row.get("local_state")),
        "nextcloud_sync_state": _nextcloud_state(row.get("nextcloud_sync_state")),
        "remote_note_ref": _remote_ref(row.get("remote_note_ref")),
        "etag_value": _text(row.get("etag_value"), 512),
        "etag_hash": _hash12(row.get("etag_hash")),
        "markdown_char_count": _safe_int(row.get("markdown_char_count")),
        "reason_code": _reason(row.get("reason_code")),
        "created_at": workspace_folder_notes._ts_to_iso(row.get("created_at")),
        "updated_at": workspace_folder_notes._ts_to_iso(row.get("updated_at")),
        "deleted_at": workspace_folder_notes._ts_to_iso(row.get("deleted_at")),
    }


def list_notes(
    workspace_folder_id: str,
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(workspace_folder_id)
    if not folder_id:
        return []
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                deleted_sql = "" if include_deleted else "AND deleted_at IS NULL"
                cur.execute(
                    f"""
                    SELECT id, workspace_folder_id, title, title_hash, target_name,
                           local_state, nextcloud_sync_state, remote_note_ref,
                           etag_value, etag_hash, markdown_char_count, reason_code,
                           created_at, updated_at, deleted_at
                    FROM workspace_folder_notes
                    WHERE workspace_folder_id = %s::uuid {deleted_sql}
                    ORDER BY updated_at DESC, created_at DESC
                    """,
                    (folder_id,),
                )
                rows = cur.fetchall()
        return [note for note in (serialize_note_row(row) for row in rows) if note]
    except Exception as exc:
        _log(logger, "list_failed", folder_id=folder_id, error_type=type(exc).__name__)
        return []


def get_note(
    note_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_notes.normalize_note_id(note_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT id, workspace_folder_id, title, title_hash, target_name,
                           local_state, nextcloud_sync_state, remote_note_ref,
                           etag_value, etag_hash, markdown_char_count, reason_code,
                           created_at, updated_at, deleted_at
                    FROM workspace_folder_notes
                    WHERE id = %s::uuid
                    """,
                    (normalized,),
                )
                return serialize_note_row(cur.fetchone())
    except Exception as exc:
        _log(logger, "get_failed", note_id=normalized, error_type=type(exc).__name__)
        return None


def upsert_note(
    *,
    note_id: str,
    workspace_folder_id: str,
    title: str,
    target_name: str,
    local_state: str = workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
    nextcloud_sync_state: str = workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
    remote_note_ref: str = "",
    etag_value: str = "",
    etag_hash: str = "",
    markdown_char_count: int = 0,
    reason_code: str = workspace_folder_notes.REASON_CREATE_OK,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    normalized_note_id = workspace_folder_notes.normalize_note_id(note_id)
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(workspace_folder_id)
    if not normalized_note_id or not folder_id:
        raise WorkspaceFolderNotePersistenceError(workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED)
    title_value = workspace_folder_notes.sanitize_note_title(title)
    target = _target_name(target_name)
    title_hash = workspace_folder_notes.title_hash_for_target(target)
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_folder_notes (
                        id, workspace_folder_id, title, title_hash, target_name,
                        local_state, nextcloud_sync_state, remote_note_ref,
                        etag_value, etag_hash, markdown_char_count, reason_code,
                        created_at, updated_at, deleted_at
                    )
                    VALUES (
                        %s::uuid, %s::uuid, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s, %s,
                        now(), now(), NULL
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        workspace_folder_id = EXCLUDED.workspace_folder_id,
                        title = EXCLUDED.title,
                        title_hash = EXCLUDED.title_hash,
                        target_name = EXCLUDED.target_name,
                        local_state = EXCLUDED.local_state,
                        nextcloud_sync_state = EXCLUDED.nextcloud_sync_state,
                        remote_note_ref = EXCLUDED.remote_note_ref,
                        etag_value = EXCLUDED.etag_value,
                        etag_hash = EXCLUDED.etag_hash,
                        markdown_char_count = EXCLUDED.markdown_char_count,
                        reason_code = EXCLUDED.reason_code,
                        updated_at = now(),
                        deleted_at = NULL
                    RETURNING id, workspace_folder_id, title, title_hash, target_name,
                              local_state, nextcloud_sync_state, remote_note_ref,
                              etag_value, etag_hash, markdown_char_count, reason_code,
                              created_at, updated_at, deleted_at
                    """,
                    (
                        normalized_note_id,
                        folder_id,
                        title_value,
                        title_hash,
                        target,
                        _local_state(local_state),
                        _nextcloud_state(nextcloud_sync_state),
                        _remote_ref(remote_note_ref),
                        _text(etag_value, 512),
                        _hash12(etag_hash),
                        _safe_int(markdown_char_count),
                        _reason(reason_code),
                    ),
                )
                row = serialize_note_row(cur.fetchone())
            conn.commit()
        if not row:
            raise WorkspaceFolderNotePersistenceError(workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED)
        return row
    except WorkspaceFolderNotePersistenceError:
        raise
    except Exception as exc:
        _log(logger, "upsert_failed", note_id=normalized_note_id, error_type=type(exc).__name__)
        raise WorkspaceFolderNotePersistenceError(workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED) from None


def tombstone_note(
    note_id: str,
    *,
    reason_code: str = workspace_folder_notes.REASON_NOT_FOUND,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_notes.normalize_note_id(note_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_folder_notes
                    SET local_state = 'deleted',
                        nextcloud_sync_state = 'deleted',
                        reason_code = %s,
                        updated_at = now(),
                        deleted_at = COALESCE(deleted_at, now())
                    WHERE id = %s::uuid
                    RETURNING id, workspace_folder_id, title, title_hash, target_name,
                              local_state, nextcloud_sync_state, remote_note_ref,
                              etag_value, etag_hash, markdown_char_count, reason_code,
                              created_at, updated_at, deleted_at
                    """,
                    (_reason(reason_code), normalized),
                )
                row = serialize_note_row(cur.fetchone())
            conn.commit()
        return row
    except Exception as exc:
        _log(logger, "tombstone_failed", note_id=normalized, error_type=type(exc).__name__)
        return None


def _target_name(value: Any) -> str:
    target = workspace_folder_notes.sanitize_note_target_name(value)
    if target:
        return target
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    return " ".join(text.split())[: workspace_folder_notes.NOTE_TARGET_MAX_CHARS]


def _local_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in workspace_folder_notes.NOTE_LOCAL_STATES else workspace_folder_notes.NOTE_LOCAL_UNAVAILABLE


def _nextcloud_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in workspace_folder_notes.NOTE_NEXTCLOUD_STATES else workspace_folder_notes.NOTE_NEXTCLOUD_SYNC_ERROR


def _hash12(value: Any) -> str:
    text = _text(value, 12).lower()
    return text if len(text) == 12 and all(char in "0123456789abcdef" for char in text) else ""


def _remote_ref(value: Any) -> str:
    text = _text(value, 180)
    return text if re.fullmatch(r"[A-Za-z0-9:._-]{1,180}", text or "") else ""


def _reason(value: Any) -> str:
    text = _text(value, 120)
    if text in workspace_folder_notes.REASON_CODE_CATALOG:
        return text
    return workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED


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


def _log(logger: Any, event: str, **fields: Any) -> None:
    if logger is None:
        return
    logger.warning("workspace_folder_note_%s", event, extra={"frida": fields})
