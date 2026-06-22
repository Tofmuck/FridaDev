from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


NEXTCLOUD_FILE_SYNC_LINKED = "linked"
NEXTCLOUD_FILE_SYNC_ERROR = "sync_error"
NEXTCLOUD_FILE_SYNC_DELETED = "deleted"
NEXTCLOUD_FILE_SYNC_STATES = (
    NEXTCLOUD_FILE_SYNC_LINKED,
    NEXTCLOUD_FILE_SYNC_ERROR,
    NEXTCLOUD_FILE_SYNC_DELETED,
)

NEXTCLOUD_FILE_OPERATIONS = ("upload", "delete", "reconcile", "observe")

REASON_LINK_PERSISTENCE_FAILED = "folder_document_link_persistence_failed"
REASON_LINK_LOOKUP_FAILED = "folder_document_link_lookup_failed"
REASON_LINK_MISSING = "folder_document_link_missing"
REASON_LINK_MARK_FAILED = "folder_document_link_mark_failed"
REASON_DELETE_OK = "folder_document_delete_ok"
REASON_REMOTE_DELETE_FAILED = "folder_document_remote_delete_failed"
REASON_LOCAL_DELETE_FAILED = "folder_document_local_delete_failed"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_document_nextcloud_error_redacted"

_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")
_DOCUMENT_REF_RE = re.compile(r"^[A-Za-z0-9:._-]{1,180}$")


class WorkspaceFileNextcloudLinkPersistenceError(RuntimeError):
    """Raised when local document link persistence fails fail-closed."""


class WorkspaceFileNextcloudLinkLookupError(RuntimeError):
    """Raised when document link lookup fails and callers must fail closed."""


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


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


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_file_nextcloud_links (
            workspace_file_id        UUID PRIMARY KEY REFERENCES workspace_files(id) ON DELETE CASCADE,
            workspace_folder_id      UUID        NOT NULL REFERENCES workspace_folders(id) ON DELETE CASCADE,
            nextcloud_sync_state     TEXT        NOT NULL DEFAULT 'linked',
            nextcloud_document_ref   TEXT        NOT NULL DEFAULT '',
            nextcloud_name_hash      TEXT        NOT NULL DEFAULT '',
            nextcloud_target_name    TEXT        NOT NULL DEFAULT '',
            last_sync_at             TIMESTAMPTZ,
            last_sync_reason_code    TEXT        NOT NULL DEFAULT '',
            last_sync_operation      TEXT,
            created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT workspace_file_nextcloud_links_sync_state_chk
                CHECK (nextcloud_sync_state IN ('linked', 'sync_error', 'deleted')),
            CONSTRAINT workspace_file_nextcloud_links_operation_chk
                CHECK (last_sync_operation IS NULL OR last_sync_operation IN ('upload', 'delete', 'reconcile', 'observe'))
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS workspace_folder_id UUID;",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'linked';",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_document_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_name_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_target_name TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_operation TEXT;",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_file_nextcloud_links ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
    ):
        cur.execute(column_sql)


def get_link(
    workspace_file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
    fail_closed: bool = False,
) -> Optional[dict[str, Any]]:
    normalized = normalize_workspace_file_id(workspace_file_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT workspace_file_id, workspace_folder_id, nextcloud_sync_state,
                           nextcloud_document_ref, nextcloud_name_hash, nextcloud_target_name,
                           last_sync_at, last_sync_reason_code, last_sync_operation,
                           created_at, updated_at
                    FROM workspace_file_nextcloud_links
                    WHERE workspace_file_id = %s::uuid
                    """,
                    (normalized,),
                )
                return serialize_link_row(cur.fetchone())
    except Exception as exc:
        _log(logger, "document_link_get_failed", file_id=normalized, error_type=type(exc).__name__)
        if fail_closed:
            raise WorkspaceFileNextcloudLinkLookupError(REASON_LINK_LOOKUP_FAILED) from None
        return None


def upsert_link(
    *,
    workspace_file_id: str,
    workspace_folder_id: str,
    nextcloud_sync_state: str,
    nextcloud_document_ref: str,
    nextcloud_name_hash: str,
    nextcloud_target_name: str,
    last_sync_reason_code: str,
    last_sync_operation: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    file_id = normalize_workspace_file_id(workspace_file_id)
    folder_id = normalize_workspace_folder_id(workspace_folder_id)
    if not file_id or not folder_id:
        raise WorkspaceFileNextcloudLinkPersistenceError(REASON_LINK_PERSISTENCE_FAILED) from None
    state = _sync_state(nextcloud_sync_state)
    operation = _operation(last_sync_operation)
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_file_nextcloud_links (
                        workspace_file_id, workspace_folder_id, nextcloud_sync_state,
                        nextcloud_document_ref, nextcloud_name_hash, nextcloud_target_name,
                        last_sync_at, last_sync_reason_code, last_sync_operation,
                        created_at, updated_at
                    )
                    VALUES (
                        %s::uuid, %s::uuid, %s,
                        %s, %s, %s,
                        now(), %s, %s,
                        now(), now()
                    )
                    ON CONFLICT (workspace_file_id) DO UPDATE SET
                        workspace_folder_id = EXCLUDED.workspace_folder_id,
                        nextcloud_sync_state = EXCLUDED.nextcloud_sync_state,
                        nextcloud_document_ref = EXCLUDED.nextcloud_document_ref,
                        nextcloud_name_hash = EXCLUDED.nextcloud_name_hash,
                        nextcloud_target_name = EXCLUDED.nextcloud_target_name,
                        last_sync_at = EXCLUDED.last_sync_at,
                        last_sync_reason_code = EXCLUDED.last_sync_reason_code,
                        last_sync_operation = EXCLUDED.last_sync_operation,
                        updated_at = now()
                    RETURNING workspace_file_id, workspace_folder_id, nextcloud_sync_state,
                              nextcloud_document_ref, nextcloud_name_hash, nextcloud_target_name,
                              last_sync_at, last_sync_reason_code, last_sync_operation,
                              created_at, updated_at
                    """,
                    (
                        file_id,
                        folder_id,
                        state,
                        _document_ref(nextcloud_document_ref),
                        _hash12(nextcloud_name_hash),
                        _target_name(nextcloud_target_name),
                        _reason(last_sync_reason_code),
                        operation or None,
                    ),
                )
                row = serialize_link_row(cur.fetchone())
                if not row:
                    raise WorkspaceFileNextcloudLinkPersistenceError(REASON_LINK_PERSISTENCE_FAILED) from None
                return row
    except WorkspaceFileNextcloudLinkPersistenceError:
        raise
    except Exception as exc:
        _log(logger, "document_link_upsert_failed", file_id=file_id, error_type=type(exc).__name__)
        raise WorkspaceFileNextcloudLinkPersistenceError(REASON_LINK_PERSISTENCE_FAILED) from None


def mark_deleted(
    workspace_file_id: str,
    *,
    reason_code: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = normalize_workspace_file_id(workspace_file_id)
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_file_nextcloud_links
                    SET nextcloud_sync_state = 'deleted',
                        last_sync_at = now(),
                        last_sync_reason_code = %s,
                        last_sync_operation = 'delete',
                        updated_at = now()
                    WHERE workspace_file_id = %s::uuid
                    RETURNING workspace_file_id, workspace_folder_id, nextcloud_sync_state,
                              nextcloud_document_ref, nextcloud_name_hash, nextcloud_target_name,
                              last_sync_at, last_sync_reason_code, last_sync_operation,
                              created_at, updated_at
                    """,
                    (_reason(reason_code), normalized),
                )
                return serialize_link_row(cur.fetchone())
    except Exception as exc:
        _log(logger, "document_link_mark_deleted_failed", file_id=normalized, error_type=type(exc).__name__)
        return None


def serialize_link_row(row: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    return {
        "workspace_file_id": normalize_workspace_file_id(str(row.get("workspace_file_id") or "")) or "",
        "workspace_folder_id": normalize_workspace_folder_id(str(row.get("workspace_folder_id") or "")) or "",
        "nextcloud_sync_state": _sync_state(row.get("nextcloud_sync_state")),
        "nextcloud_document_ref": _document_ref(row.get("nextcloud_document_ref")),
        "nextcloud_name_hash": _hash12(row.get("nextcloud_name_hash")),
        "nextcloud_target_name": _target_name(row.get("nextcloud_target_name")),
        "last_sync_at": _ts_to_iso(row.get("last_sync_at")),
        "last_sync_reason_code": _reason(row.get("last_sync_reason_code")),
        "last_sync_operation": _operation(row.get("last_sync_operation")),
        "created_at": _ts_to_iso(row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("updated_at")),
    }


def _sync_state(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text if text in NEXTCLOUD_FILE_SYNC_STATES else NEXTCLOUD_FILE_SYNC_ERROR


def _operation(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text if text in NEXTCLOUD_FILE_OPERATIONS else ""


def _hash12(value: Any) -> str:
    text = " ".join(str(value or "").strip().lower().split())
    return text if _HASH12_RE.fullmatch(text) else ""


def _document_ref(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    return text[:180] if _DOCUMENT_REF_RE.fullmatch(text) else ""


def _target_name(value: Any) -> str:
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    text = " ".join(text.split())
    return text[:220]


def _reason(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if re.fullmatch(r"[a-z0-9_]{1,120}", text or ""):
        return text
    return REASON_NEXTCLOUD_ERROR_REDACTED


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


def _log(logger: Any, event: str, **fields: Any) -> None:
    if logger is None:
        return
    logger.warning("workspace_file_nextcloud_link_%s", event, extra={"frida": fields})
