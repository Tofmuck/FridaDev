from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Optional

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


NEXTCLOUD_SYNC_LOCAL_ONLY = "local_only"
NEXTCLOUD_SYNC_PENDING = "sync_pending"
NEXTCLOUD_SYNC_LINKED = "linked"
NEXTCLOUD_SYNC_ERROR = "sync_error"
NEXTCLOUD_SYNC_CONFLICT = "conflict"
NEXTCLOUD_SYNC_DELETED = "deleted"
NEXTCLOUD_SYNC_STATES = (
    NEXTCLOUD_SYNC_LOCAL_ONLY,
    NEXTCLOUD_SYNC_PENDING,
    NEXTCLOUD_SYNC_LINKED,
    NEXTCLOUD_SYNC_ERROR,
    NEXTCLOUD_SYNC_CONFLICT,
    NEXTCLOUD_SYNC_DELETED,
)
LEGACY_SYNC_STATE_MAP = {
    "unknown": NEXTCLOUD_SYNC_LOCAL_ONLY,
    "pending": NEXTCLOUD_SYNC_PENDING,
    "error": NEXTCLOUD_SYNC_ERROR,
}

NEXTCLOUD_SHARE_UNKNOWN = "unknown"
NEXTCLOUD_SHARE_EXPECTED = "expected"
NEXTCLOUD_SHARE_CONFIRMED = "confirmed"
NEXTCLOUD_SHARE_ERROR = "error"
NEXTCLOUD_SHARE_STATES = (
    NEXTCLOUD_SHARE_UNKNOWN,
    NEXTCLOUD_SHARE_EXPECTED,
    NEXTCLOUD_SHARE_CONFIRMED,
    NEXTCLOUD_SHARE_ERROR,
)

NEXTCLOUD_OPERATIONS = ("create", "rename", "delete", "reconcile", "observe")

REASON_FOLDER_SYNC_LOCAL_ONLY = "workspace_folder_sync_local_only"
REASON_FOLDER_SYNC_PENDING = "workspace_folder_sync_pending"
REASON_FOLDER_SYNC_LINKED = "workspace_folder_sync_linked"
REASON_FOLDER_SYNC_CONFLICT = "workspace_folder_sync_conflict"
REASON_FOLDER_SYNC_ERROR = "workspace_folder_sync_error"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
REASON_NEXTCLOUD_ERROR_REDACTED = "workspace_folder_nextcloud_error_redacted"

DEFAULT_REASON_BY_STATE = {
    NEXTCLOUD_SYNC_LOCAL_ONLY: REASON_FOLDER_SYNC_LOCAL_ONLY,
    NEXTCLOUD_SYNC_PENDING: REASON_FOLDER_SYNC_PENDING,
    NEXTCLOUD_SYNC_LINKED: REASON_FOLDER_SYNC_LINKED,
    NEXTCLOUD_SYNC_CONFLICT: REASON_FOLDER_SYNC_CONFLICT,
    NEXTCLOUD_SYNC_ERROR: REASON_FOLDER_SYNC_ERROR,
    NEXTCLOUD_SYNC_DELETED: REASON_FOLDER_DELETED,
}

REASON_CODE_CATALOG = frozenset(
    {
        *DEFAULT_REASON_BY_STATE.values(),
        "workspace_folder_name_required",
        "workspace_folder_name_invalid",
        "workspace_folder_name_too_long",
        "workspace_folder_name_conflict_local",
        "workspace_folder_name_conflict_sanitized",
        "workspace_folder_name_conflict_case",
        "workspace_folder_name_conflict_nextcloud",
        "workspace_folder_permission_denied",
        "workspace_folder_target_missing",
        "workspace_folder_target_exists",
        "workspace_folder_delete_refused",
        "workspace_folder_files_preserved",
        "workspace_folder_live_unavailable",
        "workspace_folder_sauron_required",
        REASON_NEXTCLOUD_ERROR_REDACTED,
    }
)

_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")
_FOLDER_REF_RE = re.compile(r"^[A-Za-z0-9:._-]{1,160}$")


class WorkspaceFolderNextcloudLinkPersistenceError(RuntimeError):
    """Raised when local Nextcloud link persistence fails fail-closed."""


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def normalize_workspace_folder_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _text(value: Any, max_chars: int = 160) -> str:
    text = " ".join(str(value or "").strip().split())
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


def normalize_sync_state(value: Any, *, fallback: str = NEXTCLOUD_SYNC_LOCAL_ONLY) -> str:
    text = _text(value, 40)
    text = LEGACY_SYNC_STATE_MAP.get(text, text)
    return text if text in NEXTCLOUD_SYNC_STATES else fallback


def normalize_share_state(value: Any, *, fallback: str = NEXTCLOUD_SHARE_UNKNOWN) -> str:
    text = _text(value, 40)
    return text if text in NEXTCLOUD_SHARE_STATES else fallback


def normalize_operation(value: Any) -> str:
    text = _text(value, 40)
    return text if text in NEXTCLOUD_OPERATIONS else ""


def normalize_name_hash(value: Any) -> str:
    text = _text(value, 12).lower()
    return text if _HASH12_RE.fullmatch(text) else ""


def normalize_folder_ref(value: Any) -> str:
    text = _text(value, 160)
    return text if _FOLDER_REF_RE.fullmatch(text) else ""


def normalize_reason_code(value: Any, *, sync_state: str = NEXTCLOUD_SYNC_LOCAL_ONLY) -> str:
    text = _text(value, 120)
    if text in REASON_CODE_CATALOG:
        return text
    return DEFAULT_REASON_BY_STATE.get(sync_state, REASON_NEXTCLOUD_ERROR_REDACTED)


def ensure_schema(cur: Any) -> None:
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS workspace_folder_nextcloud_links (
            workspace_folder_id       UUID PRIMARY KEY REFERENCES workspace_folders(id) ON DELETE CASCADE,
            nextcloud_sync_state      TEXT        NOT NULL DEFAULT 'local_only',
            nextcloud_folder_ref      TEXT        NOT NULL DEFAULT '',
            nextcloud_name_hash       TEXT        NOT NULL DEFAULT '',
            last_sync_at              TIMESTAMPTZ,
            last_sync_reason_code     TEXT        NOT NULL DEFAULT '',
            last_sync_operation       TEXT,
            nextcloud_share_state     TEXT        NOT NULL DEFAULT 'unknown',
            created_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT workspace_folder_nextcloud_links_sync_state_chk
                CHECK (nextcloud_sync_state IN ('local_only', 'sync_pending', 'linked', 'sync_error', 'conflict', 'deleted')),
            CONSTRAINT workspace_folder_nextcloud_links_share_state_chk
                CHECK (nextcloud_share_state IN ('unknown', 'expected', 'confirmed', 'error')),
            CONSTRAINT workspace_folder_nextcloud_links_operation_chk
                CHECK (last_sync_operation IS NULL OR last_sync_operation IN ('create', 'rename', 'delete', 'reconcile', 'observe'))
        );
        """
    )
    for column_sql in (
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_sync_state TEXT NOT NULL DEFAULT 'local_only';",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_folder_ref TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_name_hash TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_at TIMESTAMPTZ;",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_reason_code TEXT NOT NULL DEFAULT '';",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS last_sync_operation TEXT;",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS nextcloud_share_state TEXT NOT NULL DEFAULT 'unknown';",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT now();",
        "ALTER TABLE workspace_folder_nextcloud_links ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT now();",
    ):
        cur.execute(column_sql)
    cur.execute(
        """
        CREATE INDEX IF NOT EXISTS workspace_folder_nextcloud_links_sync_state_idx
        ON workspace_folder_nextcloud_links (nextcloud_sync_state, updated_at DESC);
        """
    )


def serialize_link_row(row: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    folder_id = normalize_workspace_folder_id(
        row.get("link_workspace_folder_id") or row.get("workspace_folder_id")
    )
    if not folder_id:
        return None
    sync_state = normalize_sync_state(
        row.get("link_nextcloud_sync_state") or row.get("nextcloud_sync_state")
    )
    share_state = normalize_share_state(
        row.get("link_nextcloud_share_state") or row.get("nextcloud_share_state")
    )
    reason_code = normalize_reason_code(
        row.get("link_last_sync_reason_code") or row.get("last_sync_reason_code"),
        sync_state=sync_state,
    )
    return {
        "workspace_folder_id": folder_id,
        "nextcloud_sync_state": sync_state,
        "nextcloud_folder_ref": normalize_folder_ref(
            row.get("link_nextcloud_folder_ref") or row.get("nextcloud_folder_ref")
        ),
        "nextcloud_name_hash": normalize_name_hash(
            row.get("link_nextcloud_name_hash") or row.get("nextcloud_name_hash")
        ),
        "last_sync_at": _ts_to_iso(row.get("link_last_sync_at") or row.get("last_sync_at")),
        "last_sync_reason_code": reason_code,
        "last_sync_operation": normalize_operation(
            row.get("link_last_sync_operation") or row.get("last_sync_operation")
        ),
        "nextcloud_share_state": share_state,
        "created_at": _ts_to_iso(row.get("link_created_at") or row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("link_updated_at") or row.get("updated_at")),
    }


def apply_link_projection(base: Mapping[str, Any], link: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = dict(base)
    if payload.get("deleted_at"):
        sync_state = NEXTCLOUD_SYNC_DELETED
        payload["nextcloud_sync_state"] = sync_state
        payload["nextcloud_share_state"] = NEXTCLOUD_SHARE_UNKNOWN
        payload["nextcloud_reason_code"] = REASON_FOLDER_DELETED
        payload["last_sync_reason_code"] = REASON_FOLDER_DELETED
        payload["last_sync_operation"] = "delete"
        payload["nextcloud_live_checked"] = False
        payload["nextcloud_folder_ref"] = payload.get("nextcloud_directory_ref", "")
        return payload

    if not link:
        sync_state = NEXTCLOUD_SYNC_LOCAL_ONLY
        payload["nextcloud_sync_state"] = sync_state
        payload["nextcloud_share_state"] = NEXTCLOUD_SHARE_EXPECTED
        payload["nextcloud_reason_code"] = REASON_FOLDER_SYNC_LOCAL_ONLY
        payload["last_sync_reason_code"] = REASON_FOLDER_SYNC_LOCAL_ONLY
        payload["last_sync_operation"] = ""
        payload["nextcloud_live_checked"] = False
        payload["nextcloud_folder_ref"] = payload.get("nextcloud_directory_ref", "")
        return payload

    sync_state = normalize_sync_state(link.get("nextcloud_sync_state"))
    folder_ref = normalize_folder_ref(link.get("nextcloud_folder_ref")) or str(payload.get("nextcloud_directory_ref") or "")
    name_hash = normalize_name_hash(link.get("nextcloud_name_hash")) or str(payload.get("nextcloud_name_hash") or "")
    reason_code = normalize_reason_code(link.get("last_sync_reason_code"), sync_state=sync_state)
    payload.update(
        {
            "nextcloud_sync_state": sync_state,
            "nextcloud_share_state": normalize_share_state(link.get("nextcloud_share_state")),
            "nextcloud_reason_code": reason_code,
            "nextcloud_folder_ref": folder_ref,
            "nextcloud_directory_ref": folder_ref,
            "nextcloud_name_hash": name_hash,
            "last_sync_at": link.get("last_sync_at"),
            "last_sync_reason_code": reason_code,
            "last_sync_operation": normalize_operation(link.get("last_sync_operation")),
            "nextcloud_live_checked": sync_state == NEXTCLOUD_SYNC_LINKED,
        }
    )
    return payload


def mark_link_deleted_in_cursor(cur: Any, folder_id: str) -> None:
    cur.execute(
        """
        UPDATE workspace_folder_nextcloud_links
        SET nextcloud_sync_state = 'deleted',
            nextcloud_share_state = 'unknown',
            last_sync_at = now(),
            last_sync_reason_code = %s,
            last_sync_operation = 'delete',
            updated_at = now()
        WHERE workspace_folder_id = %s::uuid
        """,
        (REASON_FOLDER_DELETED, folder_id),
    )


def upsert_link(
    *,
    workspace_folder_id: str,
    nextcloud_sync_state: str,
    nextcloud_folder_ref: str = "",
    nextcloud_name_hash: str = "",
    last_sync_reason_code: str = "",
    last_sync_operation: str = "",
    nextcloud_share_state: str = NEXTCLOUD_SHARE_UNKNOWN,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    folder_id = normalize_workspace_folder_id(workspace_folder_id)
    if not folder_id:
        raise WorkspaceFolderNextcloudLinkPersistenceError("workspace_folder_id_invalid")
    sync_state = normalize_sync_state(nextcloud_sync_state)
    share_state = normalize_share_state(nextcloud_share_state)
    operation = normalize_operation(last_sync_operation) or None
    reason_code = normalize_reason_code(last_sync_reason_code, sync_state=sync_state)
    folder_ref = normalize_folder_ref(nextcloud_folder_ref)
    name_hash = normalize_name_hash(nextcloud_name_hash)
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_folder_nextcloud_links (
                        workspace_folder_id, nextcloud_sync_state, nextcloud_folder_ref,
                        nextcloud_name_hash, last_sync_at, last_sync_reason_code,
                        last_sync_operation, nextcloud_share_state, created_at, updated_at
                    )
                    VALUES (%s::uuid, %s, %s, %s, now(), %s, %s, %s, now(), now())
                    ON CONFLICT (workspace_folder_id) DO UPDATE
                    SET nextcloud_sync_state = EXCLUDED.nextcloud_sync_state,
                        nextcloud_folder_ref = EXCLUDED.nextcloud_folder_ref,
                        nextcloud_name_hash = EXCLUDED.nextcloud_name_hash,
                        last_sync_at = EXCLUDED.last_sync_at,
                        last_sync_reason_code = EXCLUDED.last_sync_reason_code,
                        last_sync_operation = EXCLUDED.last_sync_operation,
                        nextcloud_share_state = EXCLUDED.nextcloud_share_state,
                        updated_at = now()
                    RETURNING
                        workspace_folder_id AS link_workspace_folder_id,
                        nextcloud_sync_state AS link_nextcloud_sync_state,
                        nextcloud_folder_ref AS link_nextcloud_folder_ref,
                        nextcloud_name_hash AS link_nextcloud_name_hash,
                        last_sync_at AS link_last_sync_at,
                        last_sync_reason_code AS link_last_sync_reason_code,
                        last_sync_operation AS link_last_sync_operation,
                        nextcloud_share_state AS link_nextcloud_share_state,
                        created_at AS link_created_at,
                        updated_at AS link_updated_at
                    """,
                    (folder_id, sync_state, folder_ref, name_hash, reason_code, operation, share_state),
                )
                row = cur.fetchone()
            conn.commit()
        return serialize_link_row(row)
    except Exception as exc:
        logger.warning(
            "workspace_folder_nextcloud_link_upsert_failed id=%s reason_code=%s",
            folder_id,
            REASON_NEXTCLOUD_ERROR_REDACTED,
        )
        raise WorkspaceFolderNextcloudLinkPersistenceError(REASON_NEXTCLOUD_ERROR_REDACTED) from exc
