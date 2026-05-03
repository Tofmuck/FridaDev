from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable, Optional

from psycopg.rows import dict_row
from psycopg.types.json import Json


TITLE_MAX_CHARS = 120
PREVIEW_MAX_CHARS = 180
DEFAULT_TITLE = "Nouvelle conversation"


@dataclass(frozen=True)
class ConversationSaveResult:
    ok: bool
    catalog_saved: bool
    messages_saved: bool
    updated_at: str
    message_count: int
    reason: str | None = None


def conversation_save_failure_reason(*, catalog_saved: bool, messages_saved: bool) -> str | None:
    if catalog_saved and messages_saved:
        return None
    if not catalog_saved and not messages_saved:
        return "catalog_and_messages_write_failed"
    if not catalog_saved:
        return "catalog_write_failed"
    return "messages_write_failed"


def collapse_ws(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def safe_title(raw: str, fallback: str = "", *, title_max_chars: int = TITLE_MAX_CHARS) -> str:
    title = collapse_ws(raw)
    if not title:
        title = fallback
    if len(title) > title_max_chars:
        title = title[:title_max_chars].rstrip()
    return title


def parse_iso_to_dt(raw: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def ts_to_iso(value: Any, *, now_iso_func: Callable[[], str]) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return now_iso_func()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def normalize_messages_for_storage(
    messages: Any,
    *,
    ts_to_iso_func: Callable[[Any], str],
    coerce_bool_func: Callable[[Any], bool],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    if not isinstance(messages, list):
        return out

    for raw in messages:
        if not isinstance(raw, dict):
            continue
        role = collapse_ws(str(raw.get("role") or "")).lower()
        if not role:
            continue

        content = str(raw.get("content") or "")
        msg = {
            "role": role,
            "content": content,
            "timestamp": ts_to_iso_func(raw.get("timestamp")),
            "embedded": coerce_bool_func(raw.get("embedded")),
        }
        summarized_by = str(raw.get("summarized_by") or "").strip()
        if summarized_by:
            msg["summarized_by"] = summarized_by
        if "meta" in raw and raw.get("meta") is not None:
            msg["meta"] = raw.get("meta")
        out.append(msg)
    return out


def normalize_conversation_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError):
        return None


def find_system_message(messages: Iterable[dict[str, Any]]) -> Optional[dict[str, Any]]:
    for msg in messages:
        if msg.get("role") == "system":
            return msg
    return None


def ensure_system_message(
    messages: list[dict[str, Any]],
    *,
    find_system_message_func: Callable[[Iterable[dict[str, Any]]], Optional[dict[str, Any]]],
    now_iso_func: Callable[[], str],
) -> dict[str, Any]:
    system_msg = find_system_message_func(messages)
    if system_msg is None:
        system_msg = {"role": "system", "content": "", "timestamp": now_iso_func()}
        messages.insert(0, system_msg)
    return system_msg


def normalize_conversation(
    data: Any,
    conversation_id: str,
    system_prompt: str,
    *,
    now_iso_func: Callable[[], str],
    safe_title_func: Callable[[str, str], str],
    find_system_message_func: Callable[[Iterable[dict[str, Any]]], Optional[dict[str, Any]]],
) -> dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    data.setdefault("id", conversation_id)
    data.setdefault("created_at", now_iso_func())
    data.setdefault("updated_at", now_iso_func())
    if "title" not in data:
        data["title"] = ""
    else:
        data["title"] = safe_title_func(str(data.get("title") or ""), "")
    messages = data.get("messages")
    if not isinstance(messages, list):
        messages = []
    data["messages"] = messages
    system_msg = find_system_message_func(messages)
    if system_msg is None:
        messages.insert(0, {"role": "system", "content": system_prompt or "", "timestamp": now_iso_func()})
    elif not system_msg.get("content") and system_prompt:
        system_msg["content"] = system_prompt
    return data


def load_json_conversation_file(
    path: Path,
    conversation_id: str,
    system_prompt: str,
    *,
    backup_on_error: bool,
    now_compact_func: Callable[[], str],
    normalize_conversation_func: Callable[[Any, str, str], dict[str, Any]],
    logger: Any,
    admin_log_event_func: Callable[..., Any],
) -> Optional[dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        backup = None
        if backup_on_error and path.exists():
            backup = path.with_suffix(f".corrupt-{now_compact_func()}.json")
            try:
                path.rename(backup)
            except OSError:
                backup = None

        logger.error(
            "conv_read_error id=%s path=%s backup=%s err=%s",
            conversation_id,
            path,
            backup,
            exc,
        )
        admin_log_event_func(
            "conv_read_error",
            level="ERROR",
            conversation_id=conversation_id,
            path=str(path),
            backup=str(backup) if backup else None,
            error=str(exc),
        )
        return None

    return normalize_conversation_func(data, conversation_id, system_prompt)


def infer_title_from_messages(
    messages: list[dict[str, Any]],
    *,
    collapse_ws_func: Callable[[str], str],
    safe_title_func: Callable[[str, str], str],
) -> str:
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = collapse_ws_func(str(msg.get("content") or ""))
        if content:
            return safe_title_func(content, "")
    return ""


def last_message_preview(
    messages: list[dict[str, Any]],
    *,
    collapse_ws_func: Callable[[str], str],
    preview_max_chars: int = PREVIEW_MAX_CHARS,
) -> str:
    for msg in reversed(messages):
        if msg.get("role") not in {"user", "assistant"}:
            continue
        content = collapse_ws_func(str(msg.get("content") or ""))
        if not content:
            continue
        if len(content) > preview_max_chars:
            return content[:preview_max_chars].rstrip() + "…"
        return content
    return ""


def conversation_metadata(
    conversation: dict[str, Any],
    *,
    safe_title_func: Callable[[str, str], str],
    ts_to_iso_func: Callable[[Any], str],
    now_iso_func: Callable[[], str],
    default_title: str,
    infer_title_from_messages_func: Callable[[list[dict[str, Any]]], str],
    last_message_preview_func: Callable[[list[dict[str, Any]]], str],
) -> dict[str, Any]:
    messages = conversation.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    explicit_title = safe_title_func(str(conversation.get("title") or ""), "")
    inferred_title = infer_title_from_messages_func(messages)
    title = explicit_title or inferred_title or default_title

    message_count = sum(1 for msg in messages if msg.get("role") in {"user", "assistant"})
    last_preview = last_message_preview_func(messages)

    created_at = ts_to_iso_func(conversation.get("created_at") or now_iso_func())
    updated_at = ts_to_iso_func(conversation.get("updated_at") or created_at)

    return {
        "id": conversation.get("id"),
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "message_count": int(message_count),
        "last_message_preview": last_preview,
    }


def serialize_catalog_row(
    row: dict[str, Any],
    *,
    safe_title_func: Callable[[str, str], str],
    ts_to_iso_func: Callable[[Any], str],
    default_title: str,
) -> dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "title": safe_title_func(str(row.get("title") or ""), default_title),
        "created_at": ts_to_iso_func(row.get("created_at")),
        "updated_at": ts_to_iso_func(row.get("updated_at")),
        "message_count": int(row.get("message_count") or 0),
        "last_message_preview": str(row.get("last_message_preview") or ""),
        "deleted_at": ts_to_iso_func(row.get("deleted_at")) if row.get("deleted_at") else None,
    }


def upsert_conversation_messages(
    conversation: dict[str, Any],
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    normalize_messages_for_storage_func: Callable[[Any], list[dict[str, Any]]],
    db_conn_func: Callable[[], Any],
    parse_iso_to_dt_func: Callable[[str], datetime],
    logger: Any,
) -> bool:
    conv_id = normalize_conversation_id_func(conversation.get("id"))
    if not conv_id:
        return False

    messages = normalize_messages_for_storage_func(conversation.get("messages", []))
    conversation["messages"] = messages

    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM conversation_messages WHERE conversation_id = %s::uuid",
                    (conv_id,),
                )
                if messages:
                    rows = []
                    for idx, msg in enumerate(messages):
                        meta = Json(msg["meta"]) if "meta" in msg else None
                        rows.append(
                            (
                                conv_id,
                                idx,
                                msg["role"],
                                msg["content"],
                                parse_iso_to_dt_func(msg["timestamp"]),
                                msg.get("summarized_by"),
                                bool(msg.get("embedded")),
                                meta,
                            )
                        )
                    cur.executemany(
                        """
                        INSERT INTO conversation_messages (
                            conversation_id,
                            seq,
                            role,
                            content,
                            timestamp,
                            summarized_by,
                            embedded,
                            meta
                        )
                        VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        rows,
                    )
            conn.commit()
        return True
    except Exception as exc:
        logger.warning("conv_messages_upsert_failed id=%s err=%s", conv_id, exc)
        return False


def conversation_message_row_count(
    conversation_id: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[int]:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return None
    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM conversation_messages WHERE conversation_id = %s::uuid",
                    (conv_id,),
                )
                row = cur.fetchone()
        return int((row or [0])[0] or 0)
    except Exception as exc:
        logger.warning("conv_messages_count_failed id=%s err=%s", conv_id, exc)
        return None


def load_messages_from_db(
    conversation_id: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    ts_to_iso_func: Callable[[Any], str],
    logger: Any,
) -> Optional[list[dict[str, Any]]]:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return None

    try:
        with db_conn_func() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT role, content, timestamp, summarized_by, embedded, meta
                    FROM conversation_messages
                    WHERE conversation_id = %s::uuid
                    ORDER BY seq ASC
                    """,
                    (conv_id,),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger.warning("conv_messages_read_failed id=%s err=%s", conv_id, exc)
        return None

    messages: list[dict[str, Any]] = []
    for row in rows:
        msg: dict[str, Any] = {
            "role": str(row.get("role") or "assistant"),
            "content": str(row.get("content") or ""),
            "timestamp": ts_to_iso_func(row.get("timestamp")),
            "embedded": bool(row.get("embedded")),
        }
        summarized_by = str(row.get("summarized_by") or "").strip()
        if summarized_by:
            msg["summarized_by"] = summarized_by
        if row.get("meta") is not None:
            msg["meta"] = row.get("meta")
        messages.append(msg)
    return messages


def build_conversation_from_catalog(
    summary: dict[str, Any],
    messages: list[dict[str, Any]],
    system_prompt: str,
    *,
    default_title: str,
    now_iso_func: Callable[[], str],
    normalize_conversation_func: Callable[[Any, str, str], dict[str, Any]],
) -> dict[str, Any]:
    data = {
        "id": summary.get("id"),
        "title": summary.get("title") or default_title,
        "created_at": summary.get("created_at") or now_iso_func(),
        "updated_at": summary.get("updated_at") or summary.get("created_at") or now_iso_func(),
        "messages": messages,
    }
    return normalize_conversation_func(data, str(summary.get("id") or ""), system_prompt)


def upsert_conversation_catalog(
    conversation: dict[str, Any],
    *,
    preserve_deleted: bool,
    conversation_metadata_func: Callable[[dict[str, Any]], dict[str, Any]],
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    parse_iso_to_dt_func: Callable[[str], datetime],
    serialize_catalog_row_func: Callable[[dict[str, Any]], dict[str, Any]],
    logger: Any,
) -> Optional[dict[str, Any]]:
    meta = conversation_metadata_func(conversation)
    conv_id = normalize_conversation_id_func(meta.get("id"))
    if not conv_id:
        return None

    try:
        with db_conn_func() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    INSERT INTO conversations (
                        id,
                        title,
                        created_at,
                        updated_at,
                        message_count,
                        last_message_preview,
                        deleted_at
                    )
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, NULL)
                    ON CONFLICT (id) DO UPDATE
                    SET
                        title = EXCLUDED.title,
                        created_at = LEAST(conversations.created_at, EXCLUDED.created_at),
                        updated_at = GREATEST(conversations.updated_at, EXCLUDED.updated_at),
                        message_count = EXCLUDED.message_count,
                        last_message_preview = EXCLUDED.last_message_preview,
                        deleted_at = CASE WHEN %s THEN conversations.deleted_at ELSE NULL END
                    RETURNING id, title, created_at, updated_at, message_count, last_message_preview, deleted_at
                    """,
                    (
                        conv_id,
                        meta["title"],
                        parse_iso_to_dt_func(meta["created_at"]),
                        parse_iso_to_dt_func(meta["updated_at"]),
                        meta["message_count"],
                        meta["last_message_preview"],
                        bool(preserve_deleted),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return serialize_catalog_row_func(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_upsert_failed id=%s err=%s", conv_id, exc)
        return None


def get_conversation_summary(
    conversation_id: str,
    *,
    include_deleted: bool,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    serialize_catalog_row_func: Callable[[dict[str, Any]], dict[str, Any]],
    logger: Any,
) -> Optional[dict[str, Any]]:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return None

    where = "" if include_deleted else "AND deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT id, title, created_at, updated_at, message_count, last_message_preview, deleted_at
                    FROM conversations
                    WHERE id = %s::uuid {where}
                    LIMIT 1
                    """,
                    (conv_id,),
                )
                row = cur.fetchone()
        return serialize_catalog_row_func(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_get_failed id=%s err=%s", conv_id, exc)
        return None


def load_conversation(
    conversation_id: str,
    system_prompt: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    get_conversation_summary_func: Callable[[str], Optional[dict[str, Any]]],
    load_messages_from_db_func: Callable[[str], Optional[list[dict[str, Any]]]],
    build_conversation_from_catalog_func: Callable[[dict[str, Any], list[dict[str, Any]], str], dict[str, Any]],
    logger: Any,
    admin_log_event_func: Callable[..., Any],
) -> Optional[dict[str, Any]]:
    conv_id = normalize_conversation_id_func(conversation_id) or conversation_id

    summary = get_conversation_summary_func(conv_id)
    if summary:
        db_messages = load_messages_from_db_func(conv_id)
        if db_messages is not None:
            conversation = build_conversation_from_catalog_func(summary, db_messages, system_prompt)
            logger.info("conv_read_db id=%s messages=%s", conv_id, len(conversation.get("messages", [])))
            admin_log_event_func(
                "conv_read_db",
                conversation_id=conv_id,
                message_count=len(conversation.get("messages", [])),
            )
            return conversation

    logger.info("conv_read_missing_db id=%s", conv_id)
    admin_log_event_func(
        "conv_read_missing_db",
        conversation_id=conv_id,
        message_count=0,
    )
    return None


def save_conversation(
    conversation: dict[str, Any],
    updated_at: Optional[str] = None,
    *,
    preserve_deleted: bool,
    now_iso_func: Callable[[], str],
    normalize_messages_for_storage_func: Callable[[Any], list[dict[str, Any]]],
    logger: Any,
    admin_log_event_func: Callable[..., Any],
    upsert_conversation_catalog_func: Callable[[dict[str, Any], bool], Optional[dict[str, Any]]],
    upsert_conversation_messages_func: Callable[[dict[str, Any]], bool],
) -> ConversationSaveResult:
    conversation["updated_at"] = updated_at or now_iso_func()
    conversation["messages"] = normalize_messages_for_storage_func(conversation.get("messages", []))
    conversation_id = str(conversation.get("id") or "")
    message_count = len(conversation.get("messages", []))

    logger.info(
        "conv_write_db id=%s messages=%s",
        conversation_id,
        message_count,
    )

    catalog_saved = False
    messages_saved = False
    try:
        catalog_saved = upsert_conversation_catalog_func(conversation, preserve_deleted) is not None
    except Exception as exc:
        logger.warning("conv_catalog_write_failed id=%s err_class=%s", conversation_id, exc.__class__.__name__)

    try:
        messages_saved = bool(upsert_conversation_messages_func(conversation))
    except Exception as exc:
        logger.warning("conv_messages_write_failed id=%s err_class=%s", conversation_id, exc.__class__.__name__)

    if not catalog_saved:
        logger.warning("conv_catalog_write_failed id=%s", conversation_id)
    if not messages_saved:
        logger.warning("conv_messages_write_failed id=%s", conversation_id)

    reason = conversation_save_failure_reason(
        catalog_saved=catalog_saved,
        messages_saved=messages_saved,
    )
    result = ConversationSaveResult(
        ok=reason is None,
        catalog_saved=catalog_saved,
        messages_saved=messages_saved,
        updated_at=str(conversation["updated_at"]),
        message_count=message_count,
        reason=reason,
    )
    admin_log_event_func(
        "conv_write",
        conversation_id=conversation_id,
        message_count=message_count,
        storage="db_only",
        status="ok" if result.ok else "error",
        catalog_saved=catalog_saved,
        messages_saved=messages_saved,
        reason=reason,
    )
    return result


def append_message(
    conversation: dict[str, Any],
    role: str,
    content: str,
    *,
    meta: Optional[dict[str, Any]] = None,
    timestamp: Optional[str] = None,
    now_iso_func: Callable[[], str],
) -> None:
    conversation.setdefault("messages", [])
    message = {"role": role, "content": content, "timestamp": timestamp or now_iso_func()}
    if meta is not None:
        message["meta"] = meta
    conversation["messages"].append(message)


def list_conversations(
    *,
    limit: int,
    offset: int,
    include_deleted: bool,
    db_conn_func: Callable[[], Any],
    serialize_catalog_row_func: Callable[[dict[str, Any]], dict[str, Any]],
    logger: Any,
) -> dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    where = "" if include_deleted else "WHERE deleted_at IS NULL"
    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute(f"SELECT COUNT(*) FROM conversations {where}")
                total = int(cur.fetchone()[0] or 0)

            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    f"""
                    SELECT id, title, created_at, updated_at, message_count, last_message_preview, deleted_at
                    FROM conversations
                    {where}
                    ORDER BY updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()

        items = [serialize_catalog_row_func(row) for row in rows]
        return {
            "items": items,
            "total": total,
            "limit": limit,
            "offset": offset,
        }
    except Exception as exc:
        logger.error("conv_catalog_list_failed err=%s", exc)
        return {
            "items": [],
            "total": 0,
            "limit": limit,
            "offset": offset,
        }


def read_conversation(
    conversation_id: str,
    system_prompt: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    get_conversation_summary_func: Callable[[str], Optional[dict[str, Any]]],
    load_messages_from_db_func: Callable[[str], Optional[list[dict[str, Any]]]],
    build_conversation_from_catalog_func: Callable[[dict[str, Any], list[dict[str, Any]], str], dict[str, Any]],
) -> Optional[dict[str, Any]]:
    conv_id = normalize_conversation_id_func(conversation_id) or conversation_id

    summary = get_conversation_summary_func(conv_id)
    if summary:
        db_messages = load_messages_from_db_func(conv_id)
        if db_messages is not None:
            return build_conversation_from_catalog_func(summary, db_messages, system_prompt)

    return None


def rename_conversation(
    conversation_id: str,
    title: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    safe_title_func: Callable[[str, str], str],
    get_conversation_summary_func: Callable[[str], Optional[dict[str, Any]]],
    read_conversation_func: Callable[[str, str], Optional[dict[str, Any]]],
    save_conversation_func: Callable[[dict[str, Any], Optional[str], bool], None],
    now_iso_func: Callable[[], str],
    db_conn_func: Callable[[], Any],
    serialize_catalog_row_func: Callable[[dict[str, Any]], dict[str, Any]],
    logger: Any,
) -> Optional[dict[str, Any]]:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return None

    safe = safe_title_func(title, "")
    if not safe:
        return None

    existing = get_conversation_summary_func(conv_id)
    preserve_deleted = bool(existing and existing.get("deleted_at"))

    conversation = read_conversation_func(conv_id, "")
    if conversation:
        conversation["title"] = safe
        save_conversation_func(conversation, now_iso_func(), preserve_deleted)

    try:
        with db_conn_func() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE conversations
                    SET title = %s,
                        updated_at = GREATEST(updated_at, now())
                    WHERE id = %s::uuid
                    RETURNING id, title, created_at, updated_at, message_count, last_message_preview, deleted_at
                    """,
                    (safe, conv_id),
                )
                row = cur.fetchone()
            conn.commit()
        return serialize_catalog_row_func(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_rename_failed id=%s err=%s", conv_id, exc)
        return None


def soft_delete_conversation(
    conversation_id: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    get_conversation_summary_func: Callable[[str], Optional[dict[str, Any]]],
    read_conversation_func: Callable[[str, str], Optional[dict[str, Any]]],
    upsert_conversation_catalog_func: Callable[[dict[str, Any], bool], Optional[dict[str, Any]]],
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> bool:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return False

    if get_conversation_summary_func(conv_id) is None:
        conversation = read_conversation_func(conv_id, "")
        if conversation:
            upsert_conversation_catalog_func(conversation, True)

    try:
        with db_conn_func() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE conversations
                    SET deleted_at = COALESCE(deleted_at, now()),
                        updated_at = GREATEST(updated_at, now())
                    WHERE id = %s::uuid
                    """,
                    (conv_id,),
                )
                affected = cur.rowcount
            conn.commit()
        return bool(affected)
    except Exception as exc:
        logger.warning("conv_catalog_soft_delete_failed id=%s err=%s", conv_id, exc)
        return False


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def new_conversation(
    system_prompt: str,
    conversation_id: Optional[str] = None,
    title: str = "",
    *,
    now_iso_func: Callable[[], str],
    safe_title_func: Callable[[str, str], str],
) -> dict[str, Any]:
    conv_id = conversation_id or str(uuid.uuid4())
    now = now_iso_func()
    conversation = {
        "id": conv_id,
        "title": safe_title_func(title, ""),
        "created_at": now,
        "updated_at": now,
        "messages": [
            {"role": "system", "content": system_prompt or "", "timestamp": now},
        ],
    }
    return conversation
