from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional


def ensure_conv_dir(*, conv_dir: Path) -> None:
    conv_dir.mkdir(parents=True, exist_ok=True)


def conversation_path(conversation_id: str, *, conv_dir: Path) -> Path:
    return conv_dir / f"{conversation_id}.json"


def init_catalog_db(
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> None:
    try:
        with db_conn_func() as conn:
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


def init_messages_db(
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> None:
    try:
        with db_conn_func() as conn:
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


def sync_catalog_json_inventory(
    max_files: int = 5000,
    *,
    conv_dir: Path,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    load_json_conversation_file_func: Callable[[Path, str], Optional[dict[str, Any]]],
    upsert_conversation_catalog_func: Callable[[dict[str, Any], bool], Optional[dict[str, Any]]],
    logger: Any,
) -> tuple[int, int]:
    # Legacy sync subset kept intentionally as explicit operator tooling.
    # Runtime chat/conversation flows are DB-only and do not call these helpers.
    ensure_conv_dir(conv_dir=conv_dir)
    synced = 0
    skipped = 0

    files = sorted(
        conv_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if max_files > 0:
        files = files[:max_files]

    for path in files:
        conv_id = normalize_conversation_id_func(path.stem)
        if not conv_id:
            skipped += 1
            continue

        conversation = load_json_conversation_file_func(path, conv_id)
        if not conversation:
            skipped += 1
            continue

        if upsert_conversation_catalog_func(conversation, True):
            synced += 1
        else:
            skipped += 1

    logger.info("conv_catalog_sync done synced=%s skipped=%s", synced, skipped)
    return synced, skipped


def sync_messages_json_inventory(
    max_files: int = 5000,
    *,
    force: bool = False,
    conv_dir: Path,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    load_json_conversation_file_func: Callable[[Path, str], Optional[dict[str, Any]]],
    normalize_messages_for_storage_func: Callable[[Any], list[dict[str, Any]]],
    conversation_message_row_count_func: Callable[[str], Optional[int]],
    get_conversation_summary_func: Callable[[str, bool], Optional[dict[str, Any]]],
    upsert_conversation_catalog_func: Callable[[dict[str, Any], bool], Optional[dict[str, Any]]],
    upsert_conversation_messages_func: Callable[[dict[str, Any]], bool],
    logger: Any,
) -> dict[str, int]:
    ensure_conv_dir(conv_dir=conv_dir)
    stats = {
        "processed": 0,
        "migrated": 0,
        "skipped": 0,
        "failed": 0,
        "json_messages": 0,
        "db_messages_after": 0,
    }

    files = sorted(
        conv_dir.glob("*.json"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if max_files > 0:
        files = files[:max_files]

    for path in files:
        conv_id = normalize_conversation_id_func(path.stem)
        if not conv_id:
            stats["skipped"] += 1
            continue

        conversation = load_json_conversation_file_func(path, conv_id)
        if not conversation:
            stats["failed"] += 1
            continue

        stats["processed"] += 1
        messages = normalize_messages_for_storage_func(conversation.get("messages", []))
        conversation["messages"] = messages
        stats["json_messages"] += len(messages)

        existing_count = conversation_message_row_count_func(conv_id)
        if not force and existing_count and existing_count > 0:
            stats["skipped"] += 1
            stats["db_messages_after"] += existing_count
            continue

        existing_summary = get_conversation_summary_func(conv_id, True)
        preserve_deleted = bool(existing_summary and existing_summary.get("deleted_at"))
        if upsert_conversation_catalog_func(conversation, preserve_deleted) is None:
            stats["failed"] += 1
            continue

        if upsert_conversation_messages_func(conversation):
            stats["migrated"] += 1
            after_count = conversation_message_row_count_func(conv_id)
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


def compute_storage_counts(
    max_files: int = 0,
    *,
    conv_dir: Path,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    load_json_conversation_file_func: Callable[[Path, str], Optional[dict[str, Any]]],
    normalize_messages_for_storage_func: Callable[[Any], list[dict[str, Any]]],
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, int]:
    ensure_conv_dir(conv_dir=conv_dir)

    files = sorted(conv_dir.glob("*.json"), key=lambda path: path.name)
    if max_files > 0:
        files = files[:max_files]

    json_conversations = 0
    json_messages = 0
    for path in files:
        conv_id = normalize_conversation_id_func(path.stem)
        if not conv_id:
            continue
        conversation = load_json_conversation_file_func(path, conv_id)
        if not conversation:
            continue
        json_conversations += 1
        json_messages += len(normalize_messages_for_storage_func(conversation.get("messages", [])))

    db_conversations = -1
    db_message_rows = -1
    try:
        with db_conn_func() as conn:
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


def delete_conversation(
    conversation_id: str,
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    logger: Any,
    admin_log_event_func: Callable[..., Any],
) -> bool:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return False

    deleted: dict[str, int] = {
        "identity_conflicts": 0,
        "identities": 0,
        "identity_evidence": 0,
        "arbiter_decisions": 0,
        "traces": 0,
        "summaries": 0,
        "conversations": 0,
    }

    try:
        with db_conn_func() as conn:
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
        admin_log_event_func(
            "conv_delete_db_failed",
            level="ERROR",
            conversation_id=conv_id,
            error=str(exc),
        )
        return False

    total_deleted = sum(int(value or 0) for value in deleted.values())
    ok = total_deleted > 0
    logger.info("conv_delete_db id=%s deleted=%s ok=%s", conv_id, deleted, ok)
    admin_log_event_func(
        "conv_delete_db",
        conversation_id=conv_id,
        deleted=deleted,
        ok=ok,
    )
    return ok
