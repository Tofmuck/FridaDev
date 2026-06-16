from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as nextcloud_projection

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


DISPLAY_NAME_MAX_CHARS = 80
DESCRIPTION_MAX_CHARS = 240
SORT_ORDER_STEP = 1000
DEFAULT_ICON_KEY = "folder"
NEXTCLOUD_LOGICAL_ROOT = nextcloud_projection.NEXTCLOUD_LOGICAL_ROOT
NEXTCLOUD_SYNC_LOCAL_ONLY = nextcloud_links.NEXTCLOUD_SYNC_LOCAL_ONLY
NEXTCLOUD_SYNC_PENDING = nextcloud_links.NEXTCLOUD_SYNC_PENDING
NEXTCLOUD_SYNC_LINKED = nextcloud_links.NEXTCLOUD_SYNC_LINKED
NEXTCLOUD_SYNC_CONFLICT = nextcloud_links.NEXTCLOUD_SYNC_CONFLICT
NEXTCLOUD_SYNC_ERROR = nextcloud_links.NEXTCLOUD_SYNC_ERROR
NEXTCLOUD_SYNC_DELETED = nextcloud_links.NEXTCLOUD_SYNC_DELETED
NEXTCLOUD_SHARE_UNKNOWN = nextcloud_links.NEXTCLOUD_SHARE_UNKNOWN
NEXTCLOUD_SHARE_EXPECTED = nextcloud_links.NEXTCLOUD_SHARE_EXPECTED
NEXTCLOUD_SHARE_CONFIRMED = nextcloud_links.NEXTCLOUD_SHARE_CONFIRMED
NEXTCLOUD_SHARE_ERROR = nextcloud_links.NEXTCLOUD_SHARE_ERROR
REASON_FOLDER_NAME_REQUIRED = "workspace_folder_name_required"
REASON_FOLDER_NAME_INVALID = nextcloud_projection.REASON_FOLDER_NAME_INVALID
REASON_FOLDER_NAME_TOO_LONG = "workspace_folder_name_too_long"
REASON_FOLDER_NAME_CONFLICT_LOCAL = "workspace_folder_name_conflict_local"
REASON_FOLDER_NAME_CONFLICT_SANITIZED = "workspace_folder_name_conflict_sanitized"
REASON_FOLDER_NAME_CONFLICT_CASE = "workspace_folder_name_conflict_case"
REASON_FOLDER_SYNC_LOCAL_ONLY = nextcloud_links.REASON_FOLDER_SYNC_LOCAL_ONLY
REASON_FOLDER_SYNC_PENDING = nextcloud_projection.REASON_FOLDER_SYNC_PENDING
REASON_FOLDER_DELETED = nextcloud_projection.REASON_FOLDER_DELETED
WORKSPACE_FOLDER_ICON_KEYS = (
    "book",
    "feather",
    "star",
    "leaf",
    "folder",
    "moon",
    "circle",
    "fragment",
    "archive",
    "search",
    "note",
    "image",
    "map",
    "dialog",
    "spark",
)


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def normalize_workspace_folder_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def normalize_icon_key(value: Any) -> Optional[str]:
    icon_key = str(value or DEFAULT_ICON_KEY).strip().lower()
    if icon_key in WORKSPACE_FOLDER_ICON_KEYS:
        return icon_key
    return None


def sanitize_display_name(value: Any) -> str:
    display_name = collapse_ws(value)
    if len(display_name) > DISPLAY_NAME_MAX_CHARS:
        display_name = display_name[:DISPLAY_NAME_MAX_CHARS].rstrip()
    return display_name


def sanitize_description(value: Any) -> str:
    description = collapse_ws(value)
    if len(description) > DESCRIPTION_MAX_CHARS:
        description = description[:DESCRIPTION_MAX_CHARS].rstrip()
    return description


def sanitize_nextcloud_folder_name(value: Any) -> str:
    return nextcloud_projection.sanitize_nextcloud_folder_name(value)


def nextcloud_folder_name_key(value: Any) -> str:
    return nextcloud_projection.nextcloud_folder_name_key(value)


def build_nextcloud_folder_projection(
    *,
    folder_id: Any,
    display_name: Any,
    deleted_at: Any = None,
) -> dict[str, Any]:
    return nextcloud_projection.build_nextcloud_folder_projection(
        folder_id=folder_id,
        display_name=display_name,
        deleted_at=deleted_at,
        normalize_folder_id_func=normalize_workspace_folder_id,
    )


def validate_workspace_folder_name(
    value: Any,
    *,
    existing_folders: Optional[list[dict[str, Any]]] = None,
    current_folder_id: Optional[str] = None,
) -> dict[str, Any]:
    raw_name = collapse_ws(value)
    if not raw_name:
        return _folder_name_validation_error(REASON_FOLDER_NAME_REQUIRED, raw_name)
    if len(raw_name) > DISPLAY_NAME_MAX_CHARS:
        return _folder_name_validation_error(REASON_FOLDER_NAME_TOO_LONG, raw_name)

    target_name = sanitize_nextcloud_folder_name(raw_name)
    if not target_name:
        return _folder_name_validation_error(REASON_FOLDER_NAME_INVALID, raw_name)

    current = normalize_workspace_folder_id(current_folder_id)
    raw_key = raw_name.casefold()
    target_key = target_name.casefold()
    for folder in existing_folders or []:
        folder_id = normalize_workspace_folder_id(str(folder.get("id") or ""))
        if current and folder_id == current:
            continue
        if folder.get("deleted_at"):
            continue
        other_name = collapse_ws(folder.get("display_name"))
        if not other_name:
            continue
        if raw_name == other_name:
            return _folder_name_validation_error(REASON_FOLDER_NAME_CONFLICT_LOCAL, raw_name, target_name)
        if raw_key == other_name.casefold():
            return _folder_name_validation_error(REASON_FOLDER_NAME_CONFLICT_CASE, raw_name, target_name)
        if target_key == nextcloud_folder_name_key(other_name):
            return _folder_name_validation_error(REASON_FOLDER_NAME_CONFLICT_SANITIZED, raw_name, target_name)

    return {
        "ok": True,
        "display_name": raw_name,
        "nextcloud_target_name": target_name,
        "nextcloud_name_hash": nextcloud_projection.hash12(target_key),
        "reason_code": "",
    }


def _folder_name_validation_error(
    reason_code: str,
    display_name: str,
    target_name: str = "",
) -> dict[str, Any]:
    target = target_name or sanitize_nextcloud_folder_name(display_name)
    sync_state = NEXTCLOUD_SYNC_CONFLICT if "conflict" in reason_code else NEXTCLOUD_SYNC_ERROR
    return {
        "ok": False,
        "display_name": display_name,
        "nextcloud_target_name": target,
        "nextcloud_name_hash": nextcloud_projection.hash12(target.casefold()),
        "nextcloud_sync_state": sync_state,
        "nextcloud_share_state": NEXTCLOUD_SHARE_EXPECTED if sync_state == NEXTCLOUD_SYNC_CONFLICT else NEXTCLOUD_SHARE_UNKNOWN,
        "nextcloud_reason_code": reason_code,
        "reason_code": reason_code,
    }


def coerce_sort_order(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return max(0, min(int(value), 2_000_000_000))
    except (TypeError, ValueError):
        return None


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


def serialize_workspace_folder_row(row: dict[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    deleted_at = _ts_to_iso(row.get("deleted_at"))
    payload = {
        "id": str(row.get("id")),
        "display_name": sanitize_display_name(row.get("display_name")),
        "icon_key": normalize_icon_key(row.get("icon_key")) or DEFAULT_ICON_KEY,
        "description": sanitize_description(row.get("description")),
        "sort_order": int(row.get("sort_order") or 0),
        "created_at": _ts_to_iso(row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("updated_at")),
        "deleted_at": deleted_at,
    }
    payload.update(
        build_nextcloud_folder_projection(
            folder_id=payload["id"],
            display_name=payload["display_name"],
            deleted_at=deleted_at,
        )
    )
    return nextcloud_links.apply_link_projection(
        payload,
        nextcloud_links.serialize_link_row(row),
    )


def _workspace_folder_select_columns() -> str:
    return """
        folders.id,
        folders.display_name,
        folders.icon_key,
        folders.description,
        folders.sort_order,
        folders.created_at,
        folders.updated_at,
        folders.deleted_at,
        links.workspace_folder_id AS link_workspace_folder_id,
        links.nextcloud_sync_state AS link_nextcloud_sync_state,
        links.nextcloud_folder_ref AS link_nextcloud_folder_ref,
        links.nextcloud_name_hash AS link_nextcloud_name_hash,
        links.last_sync_at AS link_last_sync_at,
        links.last_sync_reason_code AS link_last_sync_reason_code,
        links.last_sync_operation AS link_last_sync_operation,
        links.nextcloud_share_state AS link_nextcloud_share_state,
        links.created_at AS link_created_at,
        links.updated_at AS link_updated_at
    """


def list_workspace_folders(
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    where = "" if include_deleted else "WHERE folders.deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    f"""
                    SELECT {_workspace_folder_select_columns()}
                    FROM workspace_folders folders
                    LEFT JOIN workspace_folder_nextcloud_links links
                      ON links.workspace_folder_id = folders.id
                    {where}
                    ORDER BY folders.sort_order ASC, folders.created_at ASC, folders.display_name ASC
                    """
                )
                rows = cur.fetchall()
        return [item for item in (serialize_workspace_folder_row(row) for row in rows) if item]
    except Exception as exc:
        logger.warning("workspace_folders_list_failed err=%s", exc)
        return []


def get_workspace_folder(
    folder_id: str,
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = normalize_workspace_folder_id(folder_id)
    if not normalized:
        return None
    where = "" if include_deleted else "AND folders.deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    f"""
                    SELECT {_workspace_folder_select_columns()}
                    FROM workspace_folders folders
                    LEFT JOIN workspace_folder_nextcloud_links links
                      ON links.workspace_folder_id = folders.id
                    WHERE folders.id = %s::uuid {where}
                    LIMIT 1
                    """,
                    (normalized,),
                )
                row = cur.fetchone()
        return serialize_workspace_folder_row(row)
    except Exception as exc:
        logger.warning("workspace_folder_get_failed id=%s err=%s", normalized, exc)
        return None


def next_sort_order(
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> int:
    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COALESCE(MAX(sort_order), 0) + %s FROM workspace_folders", (SORT_ORDER_STEP,))
                row = cur.fetchone()
        return int((row or [SORT_ORDER_STEP])[0] or SORT_ORDER_STEP)
    except Exception as exc:
        logger.warning("workspace_folder_next_sort_order_failed err=%s", exc)
        return SORT_ORDER_STEP


def create_workspace_folder(
    *,
    display_name: str,
    icon_key: str = DEFAULT_ICON_KEY,
    description: str = "",
    sort_order: Optional[int] = None,
    folder_id: Optional[str] = None,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized_id = normalize_workspace_folder_id(folder_id) or str(uuid.uuid4())
    safe_icon = normalize_icon_key(icon_key) or DEFAULT_ICON_KEY
    safe_description = sanitize_description(description)
    existing_folders = list_workspace_folders(include_deleted=False, db_conn_func=db_conn_func, logger=logger)
    name_validation = validate_workspace_folder_name(display_name, existing_folders=existing_folders)
    if not name_validation.get("ok"):
        logger.warning("workspace_folder_create_rejected reason_code=%s", name_validation.get("reason_code"))
        return None
    safe_name = str(name_validation["display_name"])
    safe_sort_order = sort_order if sort_order is not None else next_sort_order(db_conn_func=db_conn_func, logger=logger)

    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_folders (
                        id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    )
                    VALUES (%s::uuid, %s, %s, %s, %s, now(), now(), NULL)
                    RETURNING id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    """,
                    (normalized_id, safe_name, safe_icon, safe_description, int(safe_sort_order)),
                )
                row = cur.fetchone()
            conn.commit()
        return serialize_workspace_folder_row(row)
    except Exception as exc:
        logger.warning("workspace_folder_create_failed err=%s", exc)
        return None


def update_workspace_folder(
    folder_id: str,
    *,
    display_name: Optional[str] = None,
    icon_key: Optional[str] = None,
    description: Optional[str] = None,
    sort_order: Optional[int] = None,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = normalize_workspace_folder_id(folder_id)
    if not normalized:
        return None

    assignments: list[str] = []
    params: list[Any] = []
    if display_name is not None:
        existing_folders = list_workspace_folders(include_deleted=False, db_conn_func=db_conn_func, logger=logger)
        name_validation = validate_workspace_folder_name(
            display_name,
            existing_folders=existing_folders,
            current_folder_id=normalized,
        )
        if not name_validation.get("ok"):
            logger.warning(
                "workspace_folder_update_rejected id=%s reason_code=%s",
                normalized,
                name_validation.get("reason_code"),
            )
            return None
        assignments.append("display_name = %s")
        params.append(str(name_validation["display_name"]))
    if icon_key is not None:
        assignments.append("icon_key = %s")
        params.append(normalize_icon_key(icon_key) or DEFAULT_ICON_KEY)
    if description is not None:
        assignments.append("description = %s")
        params.append(sanitize_description(description))
    if sort_order is not None:
        assignments.append("sort_order = %s")
        params.append(int(sort_order))
    if not assignments:
        return get_workspace_folder(normalized, db_conn_func=db_conn_func, logger=logger)

    assignments.append("updated_at = now()")
    params.append(normalized)

    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    f"""
                    UPDATE workspace_folders
                    SET {", ".join(assignments)}
                    WHERE id = %s::uuid
                      AND deleted_at IS NULL
                    RETURNING id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    """,
                    tuple(params),
                )
                row = cur.fetchone()
            conn.commit()
        if row is None:
            return None
        refreshed = get_workspace_folder(normalized, db_conn_func=db_conn_func, logger=logger)
        return refreshed or serialize_workspace_folder_row(row)
    except Exception as exc:
        logger.warning("workspace_folder_update_failed id=%s err=%s", normalized, exc)
        return None


def soft_delete_workspace_folder(
    folder_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = normalize_workspace_folder_id(folder_id)
    if not normalized:
        return None

    try:
        with db_conn_func() as conn:
            moved_count = 0
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_folders
                    SET deleted_at = COALESCE(deleted_at, now()),
                        updated_at = now()
                    WHERE id = %s::uuid
                      AND deleted_at IS NULL
                    RETURNING id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    """,
                    (normalized,),
                )
                row = cur.fetchone()
                if not row:
                    conn.commit()
                    return None
                cur.execute(
                    """
                    UPDATE conversations
                    SET workspace_folder_id = NULL,
                        updated_at = GREATEST(updated_at, now())
                    WHERE workspace_folder_id = %s::uuid
                    """,
                    (normalized,),
                )
                moved_count = int(getattr(cur, "rowcount", 0) or 0)
                nextcloud_links.mark_link_deleted_in_cursor(cur, normalized)
            conn.commit()
        folder = serialize_workspace_folder_row(row)
        if folder is not None:
            folder["conversations_moved_out"] = moved_count
        return folder
    except Exception as exc:
        logger.warning("workspace_folder_soft_delete_failed id=%s err=%s", normalized, exc)
        return None
