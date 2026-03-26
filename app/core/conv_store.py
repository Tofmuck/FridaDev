from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from . import runtime_db_bootstrap
from .token_utils import count_tokens
import config
from admin import admin_logs, runtime_settings

CONV_DIR = Path(__file__).resolve().parent.parent / "conv"

logger = logging.getLogger("kiki.conv")

TITLE_MAX_CHARS = 120
PREVIEW_MAX_CHARS = 180
DEFAULT_TITLE = "Nouvelle conversation"


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _runtime_database_view() -> runtime_settings.RuntimeSectionView:
    return runtime_db_bootstrap.runtime_database_view(runtime_settings)


def _runtime_database_backend() -> str:
    return runtime_db_bootstrap.runtime_database_backend(runtime_settings)


def _bootstrap_database_dsn() -> str:
    return runtime_db_bootstrap.bootstrap_database_dsn(config, runtime_settings)


def _collapse_ws(value: str) -> str:
    return " ".join(str(value or "").strip().split())


def _safe_title(raw: str, fallback: str = "") -> str:
    title = _collapse_ws(raw)
    if not title:
        title = fallback
    if len(title) > TITLE_MAX_CHARS:
        title = title[:TITLE_MAX_CHARS].rstrip()
    return title


def _parse_iso_to_dt(raw: str) -> datetime:
    try:
        dt = datetime.fromisoformat(str(raw or "").replace("Z", "+00:00"))
    except ValueError:
        dt = datetime.now(timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _ts_to_iso(value: Any) -> str:
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except Exception:
            return _now_iso()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def _normalize_messages_for_storage(messages: Any) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    if not isinstance(messages, list):
        return out

    for raw in messages:
        if not isinstance(raw, dict):
            continue
        role = _collapse_ws(str(raw.get("role") or "")).lower()
        if not role:
            continue

        content = str(raw.get("content") or "")
        msg = {
            "role": role,
            "content": content,
            "timestamp": _ts_to_iso(raw.get("timestamp") or _now_iso()),
            "embedded": _coerce_bool(raw.get("embedded")),
        }
        summarized_by = str(raw.get("summarized_by") or "").strip()
        if summarized_by:
            msg["summarized_by"] = summarized_by
        if "meta" in raw and raw.get("meta") is not None:
            msg["meta"] = raw.get("meta")
        out.append(msg)
    return out


def _load_json_conversation_file(
    path: Path,
    conversation_id: str,
    system_prompt: str,
    *,
    backup_on_error: bool = False,
) -> Optional[Dict[str, Any]]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:
        backup = None
        if backup_on_error and path.exists():
            backup = path.with_suffix(f".corrupt-{_now_compact()}.json")
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
        admin_logs.log_event(
            "conv_read_error",
            level="ERROR",
            conversation_id=conversation_id,
            path=str(path),
            backup=str(backup) if backup else None,
            error=str(exc),
        )
        return None

    return _normalize_conversation(data, conversation_id, system_prompt)


def ensure_conv_dir() -> None:
    CONV_DIR.mkdir(parents=True, exist_ok=True)


def normalize_conversation_id(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, TypeError):
        return None


def new_conversation(
    system_prompt: str,
    conversation_id: Optional[str] = None,
    title: str = "",
) -> Dict[str, Any]:
    conv_id = conversation_id or str(uuid.uuid4())
    now = _now_iso()
    conversation = {
        "id": conv_id,
        "title": _safe_title(title, fallback=""),
        "created_at": now,
        "updated_at": now,
        "messages": [
            {"role": "system", "content": system_prompt or "", "timestamp": now},
        ],
    }
    return conversation


def conversation_path(conversation_id: str) -> Path:
    return CONV_DIR / f"{conversation_id}.json"


def load_conversation(conversation_id: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    conv_id = normalize_conversation_id(conversation_id) or conversation_id

    summary = get_conversation_summary(conv_id, include_deleted=True)
    if summary:
        db_messages = _load_messages_from_db(conv_id)
        if db_messages is not None:
            conversation = _build_conversation_from_catalog(summary, db_messages, system_prompt)
            logger.info("conv_read_db id=%s messages=%s", conv_id, len(conversation.get("messages", [])))
            admin_logs.log_event(
                "conv_read_db",
                conversation_id=conv_id,
                message_count=len(conversation.get("messages", [])),
            )
            return conversation

    logger.info("conv_read_missing_db id=%s", conv_id)
    admin_logs.log_event(
        "conv_read_missing_db",
        conversation_id=conv_id,
        message_count=0,
    )
    return None


def save_conversation(
    conversation: Dict[str, Any],
    updated_at: Optional[str] = None,
    *,
    preserve_deleted: bool = False,
) -> None:
    conversation["updated_at"] = updated_at or _now_iso()
    conversation["messages"] = _normalize_messages_for_storage(conversation.get("messages", []))

    logger.info(
        "conv_write_db id=%s messages=%s",
        conversation["id"],
        len(conversation.get("messages", [])),
    )
    admin_logs.log_event(
        "conv_write",
        conversation_id=conversation["id"],
        message_count=len(conversation.get("messages", [])),
        storage="db_only",
    )

    upsert_conversation_catalog(conversation, preserve_deleted=preserve_deleted)
    if not _upsert_conversation_messages(conversation):
        logger.warning("conv_messages_write_failed id=%s", conversation.get("id"))


def append_message(
    conversation: Dict[str, Any],
    role: str,
    content: str,
    *,
    meta: Optional[Dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> None:
    conversation.setdefault("messages", [])
    message = {"role": role, "content": content, "timestamp": timestamp or _now_iso()}
    if meta is not None:
        message["meta"] = meta
    conversation["messages"].append(message)



def _infer_title_from_messages(messages: List[Dict[str, Any]]) -> str:
    for msg in messages:
        if msg.get("role") != "user":
            continue
        content = _collapse_ws(str(msg.get("content") or ""))
        if content:
            return _safe_title(content, fallback="")
    return ""


def _last_message_preview(messages: List[Dict[str, Any]]) -> str:
    for msg in reversed(messages):
        if msg.get("role") not in {"user", "assistant"}:
            continue
        content = _collapse_ws(str(msg.get("content") or ""))
        if not content:
            continue
        if len(content) > PREVIEW_MAX_CHARS:
            return content[:PREVIEW_MAX_CHARS].rstrip() + "…"
        return content
    return ""


def _conversation_metadata(conversation: Dict[str, Any]) -> Dict[str, Any]:
    messages = conversation.get("messages", [])
    if not isinstance(messages, list):
        messages = []

    explicit_title = _safe_title(str(conversation.get("title") or ""), fallback="")
    inferred_title = _infer_title_from_messages(messages)
    title = explicit_title or inferred_title or DEFAULT_TITLE

    message_count = sum(1 for msg in messages if msg.get("role") in {"user", "assistant"})
    last_preview = _last_message_preview(messages)

    created_at = _ts_to_iso(conversation.get("created_at") or _now_iso())
    updated_at = _ts_to_iso(conversation.get("updated_at") or created_at)

    return {
        "id": conversation.get("id"),
        "title": title,
        "created_at": created_at,
        "updated_at": updated_at,
        "message_count": int(message_count),
        "last_message_preview": last_preview,
    }


def _serialize_catalog_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "id": str(row.get("id")),
        "title": _safe_title(str(row.get("title") or ""), fallback=DEFAULT_TITLE),
        "created_at": _ts_to_iso(row.get("created_at")),
        "updated_at": _ts_to_iso(row.get("updated_at")),
        "message_count": int(row.get("message_count") or 0),
        "last_message_preview": str(row.get("last_message_preview") or ""),
        "deleted_at": _ts_to_iso(row.get("deleted_at")) if row.get("deleted_at") else None,
    }


def init_catalog_db() -> None:
    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversations (
                        id                   UUID PRIMARY KEY,
                        title                TEXT        NOT NULL DEFAULT 'Nouvelle conversation',
                        created_at           TIMESTAMPTZ NOT NULL,
                        updated_at           TIMESTAMPTZ NOT NULL,
                        message_count        INTEGER     NOT NULL DEFAULT 0,
                        last_message_preview TEXT        NOT NULL DEFAULT '',
                        deleted_at           TIMESTAMPTZ
                    );
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS conversations_updated_idx
                    ON conversations (updated_at DESC);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS conversations_deleted_idx
                    ON conversations (deleted_at);
                    """
                )
            conn.commit()
        logger.info("conv_catalog_init_ok")
    except Exception as exc:
        logger.error("conv_catalog_init_failed err=%s", exc)


def init_messages_db() -> None:
    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS conversation_messages (
                        conversation_id UUID        NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        seq             INTEGER     NOT NULL,
                        role            TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        timestamp       TIMESTAMPTZ NOT NULL,
                        summarized_by   TEXT,
                        embedded        BOOLEAN     NOT NULL DEFAULT FALSE,
                        meta            JSONB,
                        PRIMARY KEY (conversation_id, seq)
                    );
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE conversation_messages
                    ADD COLUMN IF NOT EXISTS summarized_by TEXT;
                    """
                )
                cur.execute(
                    """
                    ALTER TABLE conversation_messages
                    ADD COLUMN IF NOT EXISTS embedded BOOLEAN NOT NULL DEFAULT FALSE;
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS conversation_messages_conv_ts_idx
                    ON conversation_messages (conversation_id, timestamp DESC);
                    """
                )
            conn.commit()
        logger.info("conv_messages_init_ok")
    except Exception as exc:
        logger.error("conv_messages_init_failed err=%s", exc)


def _upsert_conversation_messages(conversation: Dict[str, Any]) -> bool:
    conv_id = normalize_conversation_id(conversation.get("id"))
    if not conv_id:
        return False

    messages = _normalize_messages_for_storage(conversation.get("messages", []))
    conversation["messages"] = messages

    try:
        with _db_conn() as conn:
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
                                _parse_iso_to_dt(msg["timestamp"]),
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


def _conversation_message_row_count(conversation_id: str) -> Optional[int]:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return None
    try:
        with _db_conn() as conn:
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


def _load_messages_from_db(conversation_id: str) -> Optional[List[Dict[str, Any]]]:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return None

    try:
        with _db_conn() as conn:
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

    messages: List[Dict[str, Any]] = []
    for row in rows:
        msg: Dict[str, Any] = {
            "role": str(row.get("role") or "assistant"),
            "content": str(row.get("content") or ""),
            "timestamp": _ts_to_iso(row.get("timestamp")),
            "embedded": bool(row.get("embedded")),
        }
        summarized_by = str(row.get("summarized_by") or "").strip()
        if summarized_by:
            msg["summarized_by"] = summarized_by
        if row.get("meta") is not None:
            msg["meta"] = row.get("meta")
        messages.append(msg)
    return messages


def _build_conversation_from_catalog(
    summary: Dict[str, Any],
    messages: List[Dict[str, Any]],
    system_prompt: str,
) -> Dict[str, Any]:
    data = {
        "id": summary.get("id"),
        "title": summary.get("title") or DEFAULT_TITLE,
        "created_at": summary.get("created_at") or _now_iso(),
        "updated_at": summary.get("updated_at") or summary.get("created_at") or _now_iso(),
        "messages": messages,
    }
    return _normalize_conversation(data, str(summary.get("id") or ""), system_prompt)


def upsert_conversation_catalog(
    conversation: Dict[str, Any],
    *,
    preserve_deleted: bool = False,
) -> Optional[Dict[str, Any]]:
    meta = _conversation_metadata(conversation)
    conv_id = normalize_conversation_id(meta.get("id"))
    if not conv_id:
        return None

    try:
        with _db_conn() as conn:
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
                        _parse_iso_to_dt(meta["created_at"]),
                        _parse_iso_to_dt(meta["updated_at"]),
                        meta["message_count"],
                        meta["last_message_preview"],
                        bool(preserve_deleted),
                    ),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_catalog_row(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_upsert_failed id=%s err=%s", conv_id, exc)
        return None


def sync_catalog_from_json_files(max_files: int = 5000) -> Tuple[int, int]:
    ensure_conv_dir()
    synced = 0
    skipped = 0

    files = sorted(
        CONV_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if max_files > 0:
        files = files[:max_files]

    for path in files:
        conv_id = normalize_conversation_id(path.stem)
        if not conv_id:
            skipped += 1
            continue

        conversation = _load_json_conversation_file(path, conv_id, "")
        if not conversation:
            skipped += 1
            continue

        if upsert_conversation_catalog(conversation, preserve_deleted=True):
            synced += 1
        else:
            skipped += 1

    logger.info("conv_catalog_sync done synced=%s skipped=%s", synced, skipped)
    return synced, skipped


def sync_messages_from_json_files(
    max_files: int = 5000,
    *,
    force: bool = False,
) -> Dict[str, int]:
    ensure_conv_dir()
    stats = {
        "processed": 0,
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "json_messages": 0,
        "db_messages_after": 0,
    }

    files = sorted(
        CONV_DIR.glob("*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if max_files > 0:
        files = files[:max_files]

    for path in files:
        conv_id = normalize_conversation_id(path.stem)
        if not conv_id:
            stats["skipped"] += 1
            continue

        conversation = _load_json_conversation_file(path, conv_id, "")
        if not conversation:
            stats["failed"] += 1
            continue

        stats["processed"] += 1
        messages = _normalize_messages_for_storage(conversation.get("messages", []))
        conversation["messages"] = messages
        stats["json_messages"] += len(messages)

        existing_count = _conversation_message_row_count(conv_id)
        if not force and existing_count and existing_count > 0:
            stats["skipped"] += 1
            stats["db_messages_after"] += existing_count
            continue

        existing_summary = get_conversation_summary(conv_id, include_deleted=True)
        preserve_deleted = bool(existing_summary and existing_summary.get("deleted_at"))
        if upsert_conversation_catalog(conversation, preserve_deleted=preserve_deleted) is None:
            stats["failed"] += 1
            continue

        if _upsert_conversation_messages(conversation):
            stats["migrated"] += 1
            after_count = _conversation_message_row_count(conv_id)
            if after_count is not None:
                stats["db_messages_after"] += after_count
        else:
            stats["failed"] += 1

    logger.info(
        "conv_messages_sync done processed=%s migrated=%s skipped=%s failed=%s json_messages=%s db_messages_after=%s force=%s",
        stats["processed"],
        stats["migrated"],
        stats["skipped"],
        stats["failed"],
        stats["json_messages"],
        stats["db_messages_after"],
        force,
    )
    return stats


def get_storage_counts(max_files: int = 0) -> Dict[str, int]:
    ensure_conv_dir()

    files = sorted(CONV_DIR.glob("*.json"), key=lambda p: p.name)
    if max_files > 0:
        files = files[:max_files]

    json_conversations = 0
    json_messages = 0
    for path in files:
        conv_id = normalize_conversation_id(path.stem)
        if not conv_id:
            continue
        conversation = _load_json_conversation_file(path, conv_id, "")
        if not conversation:
            continue
        json_conversations += 1
        json_messages += len(_normalize_messages_for_storage(conversation.get("messages", [])))

    db_conversations = -1
    db_message_rows = -1
    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM conversations")
                db_conversations = int(cur.fetchone()[0] or 0)
                cur.execute("SELECT COUNT(*) FROM conversation_messages")
                db_message_rows = int(cur.fetchone()[0] or 0)
    except Exception as exc:
        logger.warning("conv_storage_counts_db_failed err=%s", exc)

    return {
        "json_conversations": json_conversations,
        "json_messages": json_messages,
        "db_conversations": db_conversations,
        "db_message_rows": db_message_rows,
    }


def list_conversations(
    limit: int = 100,
    offset: int = 0,
    *,
    include_deleted: bool = False,
) -> Dict[str, Any]:
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    where = "" if include_deleted else "WHERE deleted_at IS NULL"
    try:
        with _db_conn() as conn:
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

        items = [_serialize_catalog_row(row) for row in rows]
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


def get_conversation_summary(conversation_id: str, *, include_deleted: bool = False) -> Optional[Dict[str, Any]]:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return None

    where = "" if include_deleted else "AND deleted_at IS NULL"
    try:
        with _db_conn() as conn:
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
        return _serialize_catalog_row(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_get_failed id=%s err=%s", conv_id, exc)
        return None


def read_conversation(conversation_id: str, system_prompt: str) -> Optional[Dict[str, Any]]:
    conv_id = normalize_conversation_id(conversation_id) or conversation_id

    summary = get_conversation_summary(conv_id, include_deleted=True)
    if summary:
        db_messages = _load_messages_from_db(conv_id)
        if db_messages is not None:
            return _build_conversation_from_catalog(summary, db_messages, system_prompt)

    return None


def rename_conversation(conversation_id: str, title: str) -> Optional[Dict[str, Any]]:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return None

    safe_title = _safe_title(title, fallback="")
    if not safe_title:
        return None

    existing = get_conversation_summary(conv_id, include_deleted=True)
    preserve_deleted = bool(existing and existing.get("deleted_at"))

    conversation = read_conversation(conv_id, "")
    if conversation:
        conversation["title"] = safe_title
        save_conversation(conversation, updated_at=_now_iso(), preserve_deleted=preserve_deleted)

    try:
        with _db_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    UPDATE conversations
                    SET title = %s,
                        updated_at = GREATEST(updated_at, now())
                    WHERE id = %s::uuid
                    RETURNING id, title, created_at, updated_at, message_count, last_message_preview, deleted_at
                    """,
                    (safe_title, conv_id),
                )
                row = cur.fetchone()
            conn.commit()
        return _serialize_catalog_row(row) if row else None
    except Exception as exc:
        logger.warning("conv_catalog_rename_failed id=%s err=%s", conv_id, exc)
        return None


def soft_delete_conversation(conversation_id: str) -> bool:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return False

    if get_conversation_summary(conv_id, include_deleted=True) is None:
        conversation = read_conversation(conv_id, "")
        if conversation:
            upsert_conversation_catalog(conversation, preserve_deleted=True)

    try:
        with _db_conn() as conn:
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


def delta_t_label(ts_msg: str, ts_now: str) -> str:
    """Retourne un label Delta-T lisible entre deux timestamps ISO."""
    try:
        from zoneinfo import ZoneInfo
        dt_msg = datetime.fromisoformat(ts_msg.replace("Z", "+00:00"))
        dt_now = datetime.fromisoformat(ts_now.replace("Z", "+00:00"))
        secs   = int((dt_now - dt_msg).total_seconds())

        if secs < 60:  return "à l'instant"
        if secs < 3600:
            m = secs // 60
            return f"il y a {m} minute{'s' if m > 1 else ''}"

        # Comparaison calendaire en heure locale
        try:
            tz = ZoneInfo(config.FRIDA_TIMEZONE)
        except Exception:
            tz = timezone.utc
        local_msg = dt_msg.astimezone(tz)
        local_now = dt_now.astimezone(tz)
        heure = f"{local_msg.hour}h" + (f"{local_msg.minute:02d}" if local_msg.minute else "")

        if local_msg.date() == local_now.date():
            return f"aujourd'hui à {heure}"
        if local_msg.date() == (local_now - timedelta(days=1)).date():
            return f"hier à {heure}"

        if secs < 86400 * 7:  d  = secs // 86400;       return f"il y a {d} jour{'s' if d > 1 else ''}"
        if secs < 86400 * 30: w  = secs // (86400 * 7); return f"il y a {w} semaine{'s' if w > 1 else ''}"
        if secs < 86400 * 365: mo = secs // (86400*30); return f"il y a {mo} mois"
        yr = secs // (86400 * 365); return f"il y a {yr} an{'s' if yr > 1 else ''}"
    except Exception:
        return ""



def _silence_label(ts_before: str, ts_after: str) -> str:
    """Retourne un marqueur de silence entre deux messages consécutifs."""
    try:
        dt_before = datetime.fromisoformat(ts_before.replace("Z", "+00:00"))
        dt_after  = datetime.fromisoformat(ts_after.replace("Z", "+00:00"))
        secs = int((dt_after - dt_before).total_seconds())
        if secs <    60: return "[— silence de quelques secondes —]"
        if secs <  3600: m = secs // 60;              return f"[— silence de {m} minute{'s' if m > 1 else ''} —]"
        if secs < 86400: h = secs // 3600;            return f"[— silence de {h} heure{'s' if h > 1 else ''} —]"
        if secs < 86400 * 2: return "[— silence d'un jour —]"
        if secs < 86400 * 7: d = secs // 86400;      return f"[— silence de {d} jours —]"
        if secs < 86400 * 30: w = secs // (86400*7); return f"[— silence de {w} semaine{'s' if w > 1 else ''} —]"
        mo = secs // (86400 * 30); return f"[— silence de {mo} mois —]"
    except Exception:
        return ""

def _make_summary_message(summary: Dict[str, Any]) -> Dict[str, str]:
    start = (summary.get("start_ts") or "")[:10]
    end   = (summary.get("end_ts")   or "")[:10]
    if start and end and start != end:
        period = f"du {start} au {end}"
    elif start:
        period = f"du {start}"
    else:
        period = ""
    header = f"[Résumé de la période {period}]" if period else "[Résumé]"
    return {"role": "system", "content": f"{header}\n{summary['content']}"}


def _get_active_summary(conversation_id: Optional[str]) -> Optional[Dict[str, Any]]:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return None

    try:
        with _db_conn() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, start_ts, end_ts, content
                    FROM summaries
                    WHERE conversation_id = %s
                    ORDER BY
                        COALESCE(end_ts, start_ts) DESC NULLS LAST,
                        end_ts DESC NULLS LAST,
                        start_ts DESC NULLS LAST,
                        id DESC
                    LIMIT 1
                    """,
                    (conv_id,),
                )
                row = cur.fetchone()
    except Exception as exc:
        logger.warning("conv_active_summary_read_failed id=%s err=%s", conv_id, exc)
        return None

    if not row:
        return None

    return {
        "id": str(row.get("id") or ""),
        "start_ts": _ts_to_iso(row.get("start_ts")) if row.get("start_ts") else None,
        "end_ts": _ts_to_iso(row.get("end_ts")) if row.get("end_ts") else None,
        "content": str(row.get("content") or ""),
    }


def _make_memory_context_message(summaries: List[Dict[str, Any]]) -> Optional[Dict[str, str]]:
    """Formate les résumés parents des traces mémoire en un slot contexte."""
    if not summaries:
        return None
    lines = []
    for s in summaries:
        start = (s.get("start_ts") or "")[:10]
        end   = (s.get("end_ts")   or "")[:10]
        if start and end and start != end:
            period = f"du {start} au {end}"
        elif start:
            period = f"du {start}"
        else:
            period = ""
        header = f"[Contexte du souvenir — résumé {period}]" if period else "[Contexte du souvenir]"
        lines.append(f"{header}\n{s['content']}")
    return {"role": "system", "content": "\n\n".join(lines)}


def _summary_cutoff_iso(summary: Optional[Dict[str, Any]]) -> Optional[str]:
    if not summary:
        return None
    cutoff = summary.get("end_ts") or summary.get("start_ts")
    if not cutoff:
        return None
    try:
        return _ts_to_iso(cutoff)
    except Exception:
        return None


def _message_is_after_summary(msg: Dict[str, Any], cutoff_iso: Optional[str]) -> bool:
    if not cutoff_iso:
        return True
    ts = msg.get("timestamp")
    if not ts:
        return True
    try:
        return _parse_iso_to_dt(ts) > _parse_iso_to_dt(cutoff_iso)
    except Exception:
        return True


def _make_memory_message(traces: List[Dict[str, Any]], ts_now: str) -> Optional[Dict[str, str]]:
    """Formate les traces mémoire en un slot système avec Delta-T."""
    if not traces:
        return None
    lines = ["[Mémoire — souvenirs pertinents]"]
    for t in traces:
        role  = "Utilisateur" if t.get("role") == "user" else "Assistant"
        ts    = t.get("timestamp") or ""
        label = delta_t_label(ts, ts_now) if ts else ""
        prefix = f"[{label}] " if label else ""
        lines.append(f"{prefix}{role} : {t['content']}")
    return {"role": "system", "content": "\n".join(lines)}


def _make_context_hints_message(
    hints: List[Dict[str, Any]],
    ts_now: str,
    model: str,
) -> Optional[Dict[str, str]]:
    """Format non-durable context hints with dedicated token budget."""
    if not hints:
        return None

    lines = ["[Indices contextuels recents]"]
    kept = 0
    for hint in hints:
        content = str(hint.get("content") or "").strip()
        if not content:
            continue
        ts_hint = str(hint.get("timestamp") or "")
        label = delta_t_label(ts_hint, ts_now) if ts_hint else ""
        scope = str(hint.get("scope") or "user")
        kind = "Situation" if scope == "situation" else "Utilisateur"
        confidence = float(hint.get("confidence") or 0.0)
        prefix = f"[{label}] " if label else ""
        line = f"- {prefix}{kind}: {content} (confidence: {confidence:.2f})"

        trial = "\n".join(lines + [line])
        trial_tokens = count_tokens([{"role": "system", "content": trial}], model)
        if trial_tokens > config.CONTEXT_HINTS_MAX_TOKENS:
            continue

        lines.append(line)
        kept += 1
        if kept >= config.CONTEXT_HINTS_MAX_ITEMS:
            break

    if kept == 0:
        return None
    return {"role": "system", "content": "\n".join(lines)}

def build_prompt_messages(
    conversation: Dict[str, Any],
    model: str,
    now: Optional[str] = None,
    memory_traces: Optional[List[Dict[str, Any]]] = None,
    context_hints: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, str]]:
    messages = conversation.get("messages", [])
    system_msg = _ensure_system_message(messages)

    # Le resume actif est desormais relu depuis SQL.
    active_summary = _get_active_summary(conversation.get("id"))
    active_summary_cutoff = _summary_cutoff_iso(active_summary)

    # Les candidats sont reconstruits depuis les timestamps persists.
    # Si un resume actif existe, on ne garde que les tours strictement posterieurs
    # a la fin de ce resume.
    if active_summary:
        candidates = [
            m for m in messages
            if m.get("role") in {"user", "assistant"} and _message_is_after_summary(m, active_summary_cutoff)
        ]
    else:
        candidates = [m for m in messages if m.get("role") in {"user", "assistant"}]

    # Préfixe fixe : system → résumé actif → mémoire RAG
    ts_now = now or _now_iso()
    prefix: List[Dict[str, Any]] = [system_msg]
    if active_summary:
        prefix.append(_make_summary_message(active_summary))
    if context_hints:
        # Place context hints after active summary and before RAG memory.
        ctx_hints_msg = _make_context_hints_message(context_hints, ts_now, model)
        if ctx_hints_msg:
            prefix.append(ctx_hints_msg)
    if memory_traces:
        # Résumés parents distincts (dédupliqués par id)
        seen_ids: set = set()
        parent_summaries: List[Dict[str, Any]] = []
        for t in memory_traces:
            ps = t.get("parent_summary")
            if ps and ps.get("id") not in seen_ids:
                seen_ids.add(ps["id"])
                parent_summaries.append(ps)
        ctx_msg = _make_memory_context_message(parent_summaries)
        if ctx_msg:
            prefix.append(ctx_msg)
        mem_msg = _make_memory_message(memory_traces, ts_now)
        if mem_msg:
            prefix.append(mem_msg)

    # Fenêtre glissante sur les candidats
    selected_reversed: List[Dict[str, Any]] = []
    for msg in reversed(candidates):
        trial = prefix + list(reversed(selected_reversed + [msg]))
        tokens = count_tokens(trial, model)
        if tokens > config.MAX_TOKENS:
            break
        selected_reversed.append(msg)
    selected = list(reversed(selected_reversed))

    prompt_messages = prefix + selected
    total_tokens = count_tokens(prompt_messages, model)
    logger.info(
        "token_window id=%s tokens=%s messages=%s summary=%s",
        conversation.get("id"),
        total_tokens,
        len(prompt_messages),
        active_summary["id"][:8] if active_summary else "none",
    )
    admin_logs.log_event(
        "token_window",
        conversation_id=conversation.get("id"),
        tokens=total_tokens,
        message_count=len(prompt_messages),
        summary_id=active_summary["id"] if active_summary else None,
    )

    result = []
    prev_ts: Optional[str] = None
    for msg in prompt_messages:
        role    = msg["role"]
        content = msg["content"]
        ts_msg  = msg.get("timestamp", "")
        if role in {"user", "assistant"}:
            if prev_ts and ts_msg:
                silence = _silence_label(prev_ts, ts_msg)
                if silence:
                    result.append({"role": "system", "content": silence})
            label = delta_t_label(ts_msg, ts_now) if ts_msg else ""
            if label:
                content = f"[{label}] {content}"
            prev_ts = ts_msg
        result.append({"role": role, "content": content})
    return result


def delete_conversation(conversation_id: str) -> bool:
    conv_id = normalize_conversation_id(conversation_id)
    if not conv_id:
        return False

    deleted: Dict[str, int] = {
        "identity_conflicts": 0,
        "identities": 0,
        "identity_evidence": 0,
        "arbiter_decisions": 0,
        "traces": 0,
        "summaries": 0,
        "conversations": 0,
    }

    try:
        with _db_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id::text
                    FROM identities
                    WHERE conversation_id = %s
                    """,
                    (conv_id,),
                )
                identity_ids = [str(row[0]) for row in cur.fetchall()]

                if identity_ids:
                    cur.execute(
                        """
                        DELETE FROM identity_conflicts
                        WHERE identity_id_a = ANY(%s::uuid[])
                           OR identity_id_b = ANY(%s::uuid[])
                        """,
                        (identity_ids, identity_ids),
                    )
                    deleted["identity_conflicts"] = cur.rowcount

                cur.execute(
                    "DELETE FROM identity_evidence WHERE conversation_id = %s",
                    (conv_id,),
                )
                deleted["identity_evidence"] = cur.rowcount

                cur.execute(
                    "DELETE FROM arbiter_decisions WHERE conversation_id = %s",
                    (conv_id,),
                )
                deleted["arbiter_decisions"] = cur.rowcount

                cur.execute(
                    "DELETE FROM traces WHERE conversation_id = %s",
                    (conv_id,),
                )
                deleted["traces"] = cur.rowcount

                cur.execute(
                    "DELETE FROM summaries WHERE conversation_id = %s",
                    (conv_id,),
                )
                deleted["summaries"] = cur.rowcount

                cur.execute(
                    "DELETE FROM identities WHERE conversation_id = %s",
                    (conv_id,),
                )
                deleted["identities"] = cur.rowcount

                cur.execute(
                    "DELETE FROM conversations WHERE id = %s::uuid",
                    (conv_id,),
                )
                deleted["conversations"] = cur.rowcount

            conn.commit()
    except Exception as exc:
        logger.error("conv_delete_db_failed id=%s err=%s", conv_id, exc)
        admin_logs.log_event(
            "conv_delete_db_failed",
            level="ERROR",
            conversation_id=conv_id,
            error=str(exc),
        )
        return False

    total_deleted = sum(int(v or 0) for v in deleted.values())
    ok = total_deleted > 0
    logger.info("conv_delete_db id=%s deleted=%s ok=%s", conv_id, deleted, ok)
    admin_logs.log_event(
        "conv_delete_db",
        conversation_id=conv_id,
        deleted=deleted,
        ok=ok,
    )
    return ok


def _normalize_conversation(
    data: Any, conversation_id: str, system_prompt: str
) -> Dict[str, Any]:
    if not isinstance(data, dict):
        data = {}
    data.setdefault("id", conversation_id)
    data.setdefault("created_at", _now_iso())
    data.setdefault("updated_at", _now_iso())
    if "title" not in data:
        data["title"] = ""
    else:
        data["title"] = _safe_title(str(data.get("title") or ""), fallback="")
    messages = data.get("messages")
    if not isinstance(messages, list):
        messages = []
    data["messages"] = messages
    system_msg = _find_system_message(messages)
    if system_msg is None:
        messages.insert(
            0, {"role": "system", "content": system_prompt or "", "timestamp": _now_iso()}
        )
    elif not system_msg.get("content") and system_prompt:
        system_msg["content"] = system_prompt
    return data


def _find_system_message(messages: Iterable[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for msg in messages:
        if msg.get("role") == "system":
            return msg
    return None


def _ensure_system_message(messages: List[Dict[str, Any]]) -> Dict[str, Any]:
    system_msg = _find_system_message(messages)
    if system_msg is None:
        system_msg = {"role": "system", "content": "", "timestamp": _now_iso()}
        messages.insert(0, system_msg)
    return system_msg


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _now_compact() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
