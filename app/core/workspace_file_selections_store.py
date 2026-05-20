from __future__ import annotations

"""Conversation-scoped selection of persistent workspace files.

Selections make durable workspace files available to the active document prompt
lane for one conversation. This module never stores extracted text in the
conversation history, Memory, Identity, Summary, Biblio, or RAG.
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping, Optional

from . import workspace_files_store

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


SOURCE = "workspace_file_selection"
STATUS_SELECTED = "selected"
STATUS_STALE = "stale"
REASON_NOT_SELECTED = "workspace_file_not_selected"
REASON_MISSING = "workspace_file_missing"
REASON_DELETED = "workspace_file_deleted"
REASON_DISK_MISSING = "workspace_file_disk_missing"
REASON_TOO_LARGE = "workspace_file_too_large"
REASON_TYPE_UNSUPPORTED = "workspace_file_type_unsupported"
REASON_UNREADABLE = "workspace_file_unreadable"
REASON_OCR_REQUIRED = "workspace_file_ocr_required"
REASON_MODEL_UNSUPPORTED = "workspace_file_model_unsupported"
REASON_SELECTION_STALE = "workspace_selection_stale"
REASON_RUNTIME_UNAVAILABLE = "workspace_file_runtime_unavailable"


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def _normalize_uuid(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return None


def _text(value: Any, max_chars: int = 500) -> str:
    text = str(value or "").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _ts_to_iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return ""
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _serialize_selection_row(
    row: Mapping[str, Any] | None,
    *,
    storage_root: Path | None = None,
    include_disk_status: bool = False,
) -> Optional[dict[str, Any]]:
    if not row:
        return None

    file_id = _text(row.get("workspace_file_id") or row.get("file_id"), 120)
    folder_id = _text(row.get("workspace_folder_id"), 120)
    conv_folder_id = _text(row.get("conversation_workspace_folder_id"), 120)
    reason_code = _selection_reason(row, storage_root=storage_root, include_disk_status=include_disk_status)
    selection_status = STATUS_STALE if reason_code else STATUS_SELECTED
    file_item = workspace_files_store.serialize_workspace_file_row(
        {
            "id": file_id,
            "workspace_folder_id": folder_id,
            "display_name": row.get("display_name"),
            "original_filename": row.get("original_filename"),
            "storage_key": row.get("storage_key"),
            "content_kind": row.get("content_kind"),
            "media_kind": row.get("media_kind"),
            "mime_type": row.get("mime_type"),
            "source_extension": row.get("source_extension"),
            "byte_size": row.get("byte_size"),
            "sha256": row.get("sha256"),
            "sha256_12": row.get("sha256_12"),
            "text_chars": row.get("text_chars"),
            "text_sha256_12": row.get("text_sha256_12"),
            "image_width": row.get("image_width"),
            "image_height": row.get("image_height"),
            "status": row.get("file_status"),
            "reason_code": row.get("file_reason_code"),
            "source_kind": row.get("source_kind"),
            "source_file_id": row.get("source_file_id"),
            "created_at": row.get("file_created_at"),
            "updated_at": row.get("file_updated_at"),
            "deleted_at": row.get("file_deleted_at"),
        },
        storage_root=storage_root,
        include_disk_status=include_disk_status,
    )
    if file_item is None:
        file_item = {
            "id": file_id,
            "workspace_folder_id": folder_id,
            "display_name": "fichier",
            "media_kind": "text",
            "mime_type": "",
            "byte_size": 0,
            "status": "missing",
            "reason_code": reason_code or REASON_MISSING,
        }
    if reason_code:
        file_item["status"] = STATUS_STALE
        file_item["reason_code"] = reason_code

    return {
        "conversation_id": _text(row.get("conversation_id"), 120),
        "workspace_file_id": file_id,
        "workspace_folder_id": folder_id,
        "conversation_workspace_folder_id": conv_folder_id or None,
        "selected": selection_status == STATUS_SELECTED,
        "selection_status": selection_status,
        "reason_code": reason_code,
        "selected_at": _ts_to_iso(row.get("selected_at")),
        "updated_at": _ts_to_iso(row.get("selection_updated_at") or row.get("updated_at")),
        "last_injected_turn_id": _text(row.get("last_injected_turn_id"), 160),
        "last_excluded_turn_id": _text(row.get("last_excluded_turn_id"), 160),
        "last_excluded_reason_code": _text(row.get("last_excluded_reason_code"), 120),
        "file": file_item,
    }


def _selection_reason(
    row: Mapping[str, Any],
    *,
    storage_root: Path | None,
    include_disk_status: bool,
) -> str:
    if not row.get("workspace_file_id"):
        return REASON_MISSING
    if row.get("conversation_deleted_at"):
        return REASON_SELECTION_STALE
    conv_folder_id = _text(row.get("conversation_workspace_folder_id"), 120)
    folder_id = _text(row.get("workspace_folder_id"), 120)
    if not conv_folder_id or not folder_id or conv_folder_id != folder_id:
        return REASON_SELECTION_STALE
    if row.get("file_deleted_at"):
        return REASON_DELETED
    file_status = _text(row.get("file_status"), 80)
    if file_status == workspace_files_store.STATUS_DELETED:
        return REASON_DELETED
    if file_status == workspace_files_store.STATUS_DISK_MISSING:
        return REASON_DISK_MISSING
    if include_disk_status and storage_root is not None:
        try:
            storage_key = _text(row.get("storage_key"), 500)
            if storage_key and not workspace_files_store.workspace_file_path(storage_root, storage_key).exists():
                return REASON_DISK_MISSING
        except Exception:
            return REASON_DISK_MISSING
    return ""


def list_workspace_file_selections(
    conversation_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> list[dict[str, Any]]:
    conv_id = _normalize_uuid(conversation_id)
    if not conv_id:
        return []
    rows = _read_selection_rows(conv_id, db_conn_func=db_conn_func)
    items = [
        item
        for item in (
            _serialize_selection_row(row, storage_root=storage_root, include_disk_status=True)
            for row in rows
        )
        if item
    ]
    stale_count = sum(1 for item in items if item.get("selection_status") == STATUS_STALE)
    if stale_count:
        workspace_files_store.log_content_free_event(
            logger,
            "selection_stale",
            level="warning",
            conversation_id=conv_id,
            selection_count=len(items),
            failed=stale_count,
            reason_code=REASON_SELECTION_STALE,
        )
    return items


def select_workspace_file(
    conversation_id: str,
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
    logger: Any,
) -> dict[str, Any]:
    conv_id = _normalize_uuid(conversation_id)
    normalized_file = _normalize_uuid(file_id)
    if not conv_id or not normalized_file:
        return {"ok": False, "reason_code": REASON_MISSING}

    with db_conn_func() as conn:
        with _cursor(conn) as cur:
            cur.execute(
                """
                SELECT workspace_folder_id::text AS workspace_folder_id, deleted_at
                FROM conversations
                WHERE id = %s::uuid
                LIMIT 1
                """,
                (conv_id,),
            )
            conversation = cur.fetchone()
            if not conversation or conversation.get("deleted_at"):
                return {"ok": False, "reason_code": REASON_SELECTION_STALE}
            conv_folder = _text(conversation.get("workspace_folder_id"), 120)
            if not conv_folder:
                return {"ok": False, "reason_code": REASON_SELECTION_STALE}

            cur.execute(
                """
                SELECT id::text AS id, workspace_folder_id::text AS workspace_folder_id, deleted_at, status
                FROM workspace_files
                WHERE id = %s::uuid
                LIMIT 1
                """,
                (normalized_file,),
            )
            file_row = cur.fetchone()
            reason = _select_file_reason(file_row, conversation_folder_id=conv_folder)
            if reason:
                return {"ok": False, "reason_code": reason}

            cur.execute(
                """
                INSERT INTO workspace_file_selections (
                    conversation_id,
                    workspace_file_id,
                    selected_at,
                    updated_at,
                    deleted_at,
                    last_injected_turn_id,
                    last_excluded_turn_id,
                    last_excluded_reason_code
                )
                VALUES (%s::uuid, %s::uuid, now(), now(), NULL, '', '', '')
                ON CONFLICT (conversation_id, workspace_file_id)
                DO UPDATE SET
                    selected_at = CASE
                        WHEN workspace_file_selections.deleted_at IS NULL
                        THEN workspace_file_selections.selected_at
                        ELSE now()
                    END,
                    updated_at = now(),
                    deleted_at = NULL,
                    last_excluded_turn_id = '',
                    last_excluded_reason_code = ''
                """,
                (conv_id, normalized_file),
            )
        conn.commit()

    selection = get_workspace_file_selection(
        conv_id,
        normalized_file,
        db_conn_func=db_conn_func,
        storage_root=storage_root,
    )
    workspace_files_store.log_content_free_event(
        logger,
        "selection_ok",
        conversation_id=conv_id,
        file_id=normalized_file,
        folder_id=selection.get("workspace_folder_id") if selection else "",
        selection_status=selection.get("selection_status") if selection else STATUS_SELECTED,
        selected=True,
    )
    return {"ok": True, "selection": selection}


def _select_file_reason(file_row: Mapping[str, Any] | None, *, conversation_folder_id: str) -> str:
    if not file_row:
        return REASON_MISSING
    if file_row.get("deleted_at") or _text(file_row.get("status"), 80) == workspace_files_store.STATUS_DELETED:
        return REASON_DELETED
    if _text(file_row.get("workspace_folder_id"), 120) != conversation_folder_id:
        return REASON_SELECTION_STALE
    return ""


def deselect_workspace_file(
    conversation_id: str,
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    conv_id = _normalize_uuid(conversation_id)
    normalized_file = _normalize_uuid(file_id)
    if not conv_id or not normalized_file:
        return False
    with db_conn_func() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workspace_file_selections
                SET deleted_at = COALESCE(deleted_at, now()),
                    updated_at = now(),
                    last_excluded_turn_id = '',
                    last_excluded_reason_code = %s
                WHERE conversation_id = %s::uuid
                  AND workspace_file_id = %s::uuid
                  AND deleted_at IS NULL
                """,
                (REASON_NOT_SELECTED, conv_id, normalized_file),
            )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    if changed:
        workspace_files_store.log_content_free_event(
            logger,
            "selection_removed",
            conversation_id=conv_id,
            file_id=normalized_file,
            selected=False,
            reason_code=REASON_NOT_SELECTED,
        )
    return changed > 0


def clear_stale_selections_for_conversation(
    conversation_id: str,
    *,
    workspace_folder_id: Optional[str],
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> int:
    conv_id = _normalize_uuid(conversation_id)
    folder_id = _normalize_uuid(workspace_folder_id) if workspace_folder_id else None
    if not conv_id:
        return 0
    with db_conn_func() as conn:
        with conn.cursor() as cur:
            if folder_id is None:
                cur.execute(
                    """
                    UPDATE workspace_file_selections
                    SET deleted_at = COALESCE(deleted_at, now()),
                        updated_at = now(),
                        last_excluded_reason_code = %s
                    WHERE conversation_id = %s::uuid
                      AND deleted_at IS NULL
                    """,
                    (REASON_SELECTION_STALE, conv_id),
                )
            else:
                cur.execute(
                    """
                    UPDATE workspace_file_selections s
                    SET deleted_at = COALESCE(s.deleted_at, now()),
                        updated_at = now(),
                        last_excluded_reason_code = %s
                    FROM workspace_files f
                    WHERE s.workspace_file_id = f.id
                      AND s.conversation_id = %s::uuid
                      AND s.deleted_at IS NULL
                      AND (f.deleted_at IS NOT NULL OR f.workspace_folder_id <> %s::uuid)
                    """,
                    (REASON_SELECTION_STALE, conv_id, folder_id),
                )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    if changed:
        workspace_files_store.log_content_free_event(
            logger,
            "selection_stale_cleared",
            conversation_id=conv_id,
            folder_id=folder_id or "",
            deleted=changed,
            reason_code=REASON_SELECTION_STALE,
        )
    return changed


def mark_workspace_file_deleted(
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> int:
    normalized_file = _normalize_uuid(file_id)
    if not normalized_file:
        return 0
    with db_conn_func() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE workspace_file_selections
                SET deleted_at = COALESCE(deleted_at, now()),
                    updated_at = now(),
                    last_excluded_reason_code = %s
                WHERE workspace_file_id = %s::uuid
                  AND deleted_at IS NULL
                """,
                (REASON_DELETED, normalized_file),
            )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    if changed:
        workspace_files_store.log_content_free_event(
            logger,
            "selection_file_deleted",
            file_id=normalized_file,
            deleted=changed,
            reason_code=REASON_DELETED,
        )
    return changed


def get_workspace_file_selection(
    conversation_id: str,
    file_id: str,
    *,
    db_conn_func: Callable[[], Any],
    storage_root: Path,
) -> Optional[dict[str, Any]]:
    conv_id = _normalize_uuid(conversation_id)
    normalized_file = _normalize_uuid(file_id)
    if not conv_id or not normalized_file:
        return None
    rows = _read_selection_rows(conv_id, file_id=normalized_file, db_conn_func=db_conn_func)
    if not rows:
        return None
    return _serialize_selection_row(rows[0], storage_root=storage_root, include_disk_status=True)


def record_selection_injected(
    conversation_id: str,
    file_id: str,
    *,
    turn_id: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    return _record_selection_decision(
        conversation_id,
        file_id,
        turn_id=turn_id,
        injected=True,
        reason_code="",
        db_conn_func=db_conn_func,
        logger=logger,
    )


def record_selection_excluded(
    conversation_id: str,
    file_id: str,
    *,
    turn_id: str,
    reason_code: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    return _record_selection_decision(
        conversation_id,
        file_id,
        turn_id=turn_id,
        injected=False,
        reason_code=_text(reason_code, 120) or REASON_UNREADABLE,
        db_conn_func=db_conn_func,
        logger=logger,
    )


def _record_selection_decision(
    conversation_id: str,
    file_id: str,
    *,
    turn_id: str,
    injected: bool,
    reason_code: str,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    conv_id = _normalize_uuid(conversation_id)
    normalized_file = _normalize_uuid(file_id)
    if not conv_id or not normalized_file:
        return False
    with db_conn_func() as conn:
        with conn.cursor() as cur:
            if injected:
                cur.execute(
                    """
                    UPDATE workspace_file_selections
                    SET last_injected_turn_id = %s,
                        last_excluded_turn_id = '',
                        last_excluded_reason_code = '',
                        updated_at = now()
                    WHERE conversation_id = %s::uuid
                      AND workspace_file_id = %s::uuid
                      AND deleted_at IS NULL
                    """,
                    (_text(turn_id, 160), conv_id, normalized_file),
                )
            else:
                cur.execute(
                    """
                    UPDATE workspace_file_selections
                    SET last_excluded_turn_id = %s,
                        last_excluded_reason_code = %s,
                        updated_at = now()
                    WHERE conversation_id = %s::uuid
                      AND workspace_file_id = %s::uuid
                      AND deleted_at IS NULL
                    """,
                    (_text(turn_id, 160), reason_code, conv_id, normalized_file),
                )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    if changed:
        workspace_files_store.log_content_free_event(
            logger,
            "selection_injected" if injected else "selection_excluded",
            conversation_id=conv_id,
            file_id=normalized_file,
            injected=injected,
            reason_code=reason_code,
        )
    return changed > 0


def _read_selection_rows(
    conversation_id: str,
    *,
    db_conn_func: Callable[[], Any],
    file_id: str | None = None,
) -> list[Mapping[str, Any]]:
    params: tuple[Any, ...]
    file_filter = ""
    params = (conversation_id,)
    if file_id:
        file_filter = "AND s.workspace_file_id = %s::uuid"
        params = (conversation_id, file_id)
    with db_conn_func() as conn:
        with _cursor(conn) as cur:
            cur.execute(
                f"""
                SELECT
                    s.conversation_id::text AS conversation_id,
                    s.workspace_file_id::text AS workspace_file_id,
                    s.selected_at,
                    s.updated_at AS selection_updated_at,
                    s.deleted_at AS selection_deleted_at,
                    s.last_injected_turn_id,
                    s.last_excluded_turn_id,
                    s.last_excluded_reason_code,
                    c.workspace_folder_id::text AS conversation_workspace_folder_id,
                    c.deleted_at AS conversation_deleted_at,
                    f.workspace_folder_id::text AS workspace_folder_id,
                    f.display_name,
                    f.original_filename,
                    f.storage_key,
                    f.content_kind,
                    f.media_kind,
                    f.mime_type,
                    f.source_extension,
                    f.byte_size,
                    f.sha256,
                    f.sha256_12,
                    f.text_chars,
                    f.text_sha256_12,
                    f.image_width,
                    f.image_height,
                    f.status AS file_status,
                    f.reason_code AS file_reason_code,
                    f.source_kind,
                    f.source_file_id::text AS source_file_id,
                    f.created_at AS file_created_at,
                    f.updated_at AS file_updated_at,
                    f.deleted_at AS file_deleted_at
                FROM workspace_file_selections s
                LEFT JOIN conversations c ON c.id = s.conversation_id
                LEFT JOIN workspace_files f ON f.id = s.workspace_file_id
                WHERE s.conversation_id = %s::uuid
                  AND s.deleted_at IS NULL
                  {file_filter}
                ORDER BY s.selected_at ASC, f.display_name ASC
                """,
                params,
            )
            rows = cur.fetchall()
    return [dict(row) for row in rows]
