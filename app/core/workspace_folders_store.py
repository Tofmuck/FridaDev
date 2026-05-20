from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


DISPLAY_NAME_MAX_CHARS = 80
DESCRIPTION_MAX_CHARS = 240
SORT_ORDER_STEP = 1000
DEFAULT_ICON_KEY = "folder"
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
    return {
        "id": str(row.get("id")),
        "display_name": sanitize_display_name(row.get("display_name")),
        "icon_key": normalize_icon_key(row.get("icon_key")) or DEFAULT_ICON_KEY,
        "description": sanitize_description(row.get("description")),
        "sort_order": int(row.get("sort_order") or 0),
        "created_at": _ts_to_iso(row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("updated_at")),
        "deleted_at": _ts_to_iso(row.get("deleted_at")),
    }


def list_workspace_folders(
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    where = "" if include_deleted else "WHERE deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    f"""
                    SELECT id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    FROM workspace_folders
                    {where}
                    ORDER BY sort_order ASC, created_at ASC, display_name ASC
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
    where = "" if include_deleted else "AND deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    f"""
                    SELECT id, display_name, icon_key, description, sort_order, created_at, updated_at, deleted_at
                    FROM workspace_folders
                    WHERE id = %s::uuid {where}
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
    safe_name = sanitize_display_name(display_name)
    safe_icon = normalize_icon_key(icon_key) or DEFAULT_ICON_KEY
    safe_description = sanitize_description(description)
    safe_sort_order = sort_order if sort_order is not None else next_sort_order(db_conn_func=db_conn_func, logger=logger)
    if not safe_name:
        return None

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
        assignments.append("display_name = %s")
        params.append(sanitize_display_name(display_name))
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
        return serialize_workspace_folder_row(row)
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
            conn.commit()
        folder = serialize_workspace_folder_row(row)
        if folder is not None:
            folder["conversations_moved_out"] = moved_count
        return folder
    except Exception as exc:
        logger.warning("workspace_folder_soft_delete_failed id=%s err=%s", normalized, exc)
        return None
