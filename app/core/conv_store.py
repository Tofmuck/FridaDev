from __future__ import annotations

"""Conversation store transition facade.

This module is intentionally kept as the single import surface during the
structural refactor. Public symbols listed in ``__all__`` must remain stable
until extractions are completed.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, Optional

import psycopg

from . import conversations_prompt_window
from . import conversations_store
from . import runtime_db_bootstrap
from .token_utils import count_tokens
import config
from admin import admin_logs, runtime_settings

CONV_DIR = Path(__file__).resolve().parent.parent / "conv"

logger = logging.getLogger("frida.conv")

TITLE_MAX_CHARS = 120
PREVIEW_MAX_CHARS = 180
DEFAULT_TITLE = "Nouvelle conversation"

__all__ = (
    "CONV_DIR",
    "ensure_conv_dir",
    "normalize_conversation_id",
    "new_conversation",
    "conversation_path",
    "load_conversation",
    "save_conversation",
    "append_message",
    "init_catalog_db",
    "init_messages_db",
    "upsert_conversation_catalog",
    "sync_catalog_from_json_files",
    "sync_messages_from_json_files",
    "get_storage_counts",
    "list_conversations",
    "get_conversation_summary",
    "read_conversation",
    "rename_conversation",
    "soft_delete_conversation",
    "delta_t_label",
    "build_prompt_messages",
    "delete_conversation",
)

# --- Infra and helpers (includes test-coupled compatibility points) ---


def _db_conn():
    # Transition compatibility: tests patch this helper directly.
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _runtime_database_view() -> runtime_settings.RuntimeSectionView:
    return runtime_db_bootstrap.runtime_database_view(runtime_settings)


def _runtime_database_backend() -> str:
    return runtime_db_bootstrap.runtime_database_backend(runtime_settings)


def _bootstrap_database_dsn() -> str:
    # Transition compatibility: phase4 DB tests patch this helper directly.
    return runtime_db_bootstrap.bootstrap_database_dsn(config, runtime_settings)


def _collapse_ws(value: str) -> str:
    return conversations_store.collapse_ws(value)


def _safe_title(raw: str, fallback: str = "") -> str:
    return conversations_store.safe_title(raw, fallback, title_max_chars=TITLE_MAX_CHARS)


def _parse_iso_to_dt(raw: str) -> datetime:
    return conversations_store.parse_iso_to_dt(raw)


def _ts_to_iso(value: Any) -> str:
    return conversations_store.ts_to_iso(value, now_iso_func=_now_iso)


def _coerce_bool(value: Any) -> bool:
    return conversations_store.coerce_bool(value)


def _normalize_messages_for_storage(messages: Any) -> list[dict[str, Any]]:
    return conversations_store.normalize_messages_for_storage(
        messages,
        ts_to_iso_func=_ts_to_iso,
        coerce_bool_func=_coerce_bool,
    )


def _load_json_conversation_file(
    path: Path,
    conversation_id: str,
    system_prompt: str,
    *,
    backup_on_error: bool = False,
) -> Optional[dict[str, Any]]:
    return conversations_store.load_json_conversation_file(
        path,
        conversation_id,
        system_prompt,
        backup_on_error=backup_on_error,
        now_compact_func=_now_compact,
        normalize_conversation_func=_normalize_conversation,
        logger=logger,
        admin_log_event_func=admin_logs.log_event,
    )


# --- Conversation store facade (public contracts kept stable) ---

def ensure_conv_dir() -> None:
    CONV_DIR.mkdir(parents=True, exist_ok=True)


def normalize_conversation_id(value: Optional[str]) -> Optional[str]:
    return conversations_store.normalize_conversation_id(value)


def new_conversation(
    system_prompt: str,
    conversation_id: Optional[str] = None,
    title: str = "",
) -> dict[str, Any]:
    return conversations_store.new_conversation(
        system_prompt,
        conversation_id=conversation_id,
        title=title,
        now_iso_func=_now_iso,
        safe_title_func=_safe_title,
    )


def conversation_path(conversation_id: str) -> Path:
    return CONV_DIR / f"{conversation_id}.json"


def load_conversation(conversation_id: str, system_prompt: str) -> Optional[dict[str, Any]]:
    return conversations_store.load_conversation(
        conversation_id,
        system_prompt,
        normalize_conversation_id_func=normalize_conversation_id,
        get_conversation_summary_func=lambda conv_id: get_conversation_summary(conv_id, include_deleted=True),
        load_messages_from_db_func=_load_messages_from_db,
        build_conversation_from_catalog_func=_build_conversation_from_catalog,
        logger=logger,
        admin_log_event_func=admin_logs.log_event,
    )


def save_conversation(
    conversation: dict[str, Any],
    updated_at: Optional[str] = None,
    *,
    preserve_deleted: bool = False,
) -> None:
    conversations_store.save_conversation(
        conversation,
        updated_at,
        preserve_deleted=preserve_deleted,
        now_iso_func=_now_iso,
        normalize_messages_for_storage_func=_normalize_messages_for_storage,
        logger=logger,
        admin_log_event_func=admin_logs.log_event,
        upsert_conversation_catalog_func=lambda conv, preserve: upsert_conversation_catalog(
            conv,
            preserve_deleted=preserve,
        ),
        upsert_conversation_messages_func=_upsert_conversation_messages,
    )


def append_message(
    conversation: dict[str, Any],
    role: str,
    content: str,
    *,
    meta: Optional[dict[str, Any]] = None,
    timestamp: Optional[str] = None,
) -> None:
    conversations_store.append_message(
        conversation,
        role,
        content,
        meta=meta,
        timestamp=timestamp,
        now_iso_func=_now_iso,
    )



def _infer_title_from_messages(messages: list[dict[str, Any]]) -> str:
    return conversations_store.infer_title_from_messages(
        messages,
        collapse_ws_func=_collapse_ws,
        safe_title_func=_safe_title,
    )


def _last_message_preview(messages: list[dict[str, Any]]) -> str:
    return conversations_store.last_message_preview(
        messages,
        collapse_ws_func=_collapse_ws,
        preview_max_chars=PREVIEW_MAX_CHARS,
    )


def _conversation_metadata(conversation: dict[str, Any]) -> dict[str, Any]:
    return conversations_store.conversation_metadata(
        conversation,
        safe_title_func=_safe_title,
        ts_to_iso_func=_ts_to_iso,
        now_iso_func=_now_iso,
        default_title=DEFAULT_TITLE,
        infer_title_from_messages_func=_infer_title_from_messages,
        last_message_preview_func=_last_message_preview,
    )


def _serialize_catalog_row(row: dict[str, Any]) -> dict[str, Any]:
    return conversations_store.serialize_catalog_row(
        row,
        safe_title_func=_safe_title,
        ts_to_iso_func=_ts_to_iso,
        default_title=DEFAULT_TITLE,
    )


# --- Conversation catalog and message storage (DB-first path) ---

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


def _upsert_conversation_messages(conversation: dict[str, Any]) -> bool:
    return conversations_store.upsert_conversation_messages(
        conversation,
        normalize_conversation_id_func=normalize_conversation_id,
        normalize_messages_for_storage_func=_normalize_messages_for_storage,
        db_conn_func=_db_conn,
        parse_iso_to_dt_func=_parse_iso_to_dt,
        logger=logger,
    )


def _conversation_message_row_count(conversation_id: str) -> Optional[int]:
    return conversations_store.conversation_message_row_count(
        conversation_id,
        normalize_conversation_id_func=normalize_conversation_id,
        db_conn_func=_db_conn,
        logger=logger,
    )


def _load_messages_from_db(conversation_id: str) -> Optional[list[dict[str, Any]]]:
    return conversations_store.load_messages_from_db(
        conversation_id,
        normalize_conversation_id_func=normalize_conversation_id,
        db_conn_func=_db_conn,
        ts_to_iso_func=_ts_to_iso,
        logger=logger,
    )


def _build_conversation_from_catalog(
    summary: dict[str, Any],
    messages: list[dict[str, Any]],
    system_prompt: str,
) -> dict[str, Any]:
    return conversations_store.build_conversation_from_catalog(
        summary,
        messages,
        system_prompt,
        default_title=DEFAULT_TITLE,
        now_iso_func=_now_iso,
        normalize_conversation_func=_normalize_conversation,
    )


def upsert_conversation_catalog(
    conversation: dict[str, Any],
    *,
    preserve_deleted: bool = False,
) -> Optional[dict[str, Any]]:
    return conversations_store.upsert_conversation_catalog(
        conversation,
        preserve_deleted=preserve_deleted,
        conversation_metadata_func=_conversation_metadata,
        normalize_conversation_id_func=normalize_conversation_id,
        db_conn_func=_db_conn,
        parse_iso_to_dt_func=_parse_iso_to_dt,
        serialize_catalog_row_func=_serialize_catalog_row,
        logger=logger,
    )


def sync_catalog_from_json_files(max_files: int = 5000) -> tuple[int, int]:
    # Legacy sync subset kept intentionally as explicit operator tooling.
    # Runtime chat/conversation flows are DB-only and do not call these helpers.
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
) -> dict[str, int]:
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


def get_storage_counts(max_files: int = 0) -> dict[str, int]:
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
) -> dict[str, Any]:
    return conversations_store.list_conversations(
        limit=limit,
        offset=offset,
        include_deleted=include_deleted,
        db_conn_func=_db_conn,
        serialize_catalog_row_func=_serialize_catalog_row,
        logger=logger,
    )


def get_conversation_summary(conversation_id: str, *, include_deleted: bool = False) -> Optional[dict[str, Any]]:
    return conversations_store.get_conversation_summary(
        conversation_id,
        include_deleted=include_deleted,
        normalize_conversation_id_func=normalize_conversation_id,
        db_conn_func=_db_conn,
        serialize_catalog_row_func=_serialize_catalog_row,
        logger=logger,
    )


def read_conversation(conversation_id: str, system_prompt: str) -> Optional[dict[str, Any]]:
    return conversations_store.read_conversation(
        conversation_id,
        system_prompt,
        normalize_conversation_id_func=normalize_conversation_id,
        get_conversation_summary_func=lambda conv_id: get_conversation_summary(conv_id, include_deleted=True),
        load_messages_from_db_func=_load_messages_from_db,
        build_conversation_from_catalog_func=_build_conversation_from_catalog,
    )


def rename_conversation(conversation_id: str, title: str) -> Optional[dict[str, Any]]:
    return conversations_store.rename_conversation(
        conversation_id,
        title,
        normalize_conversation_id_func=normalize_conversation_id,
        safe_title_func=_safe_title,
        get_conversation_summary_func=lambda conv_id: get_conversation_summary(conv_id, include_deleted=True),
        read_conversation_func=read_conversation,
        save_conversation_func=lambda conversation, updated_at, preserve_deleted: save_conversation(
            conversation,
            updated_at=updated_at,
            preserve_deleted=preserve_deleted,
        ),
        now_iso_func=_now_iso,
        db_conn_func=_db_conn,
        serialize_catalog_row_func=_serialize_catalog_row,
        logger=logger,
    )


def soft_delete_conversation(conversation_id: str) -> bool:
    return conversations_store.soft_delete_conversation(
        conversation_id,
        normalize_conversation_id_func=normalize_conversation_id,
        get_conversation_summary_func=lambda conv_id: get_conversation_summary(conv_id, include_deleted=True),
        read_conversation_func=read_conversation,
        upsert_conversation_catalog_func=lambda conversation, preserve_deleted: upsert_conversation_catalog(
            conversation,
            preserve_deleted=preserve_deleted,
        ),
        db_conn_func=_db_conn,
        logger=logger,
    )


# --- Prompt window and temporal labels (delegated to conversations_prompt_window) ---

def delta_t_label(ts_msg: str, ts_now: str) -> str:
    """Retourne un label Delta-T lisible entre deux timestamps ISO."""
    return conversations_prompt_window.delta_t_label(
        ts_msg,
        ts_now,
        timezone_name=config.FRIDA_TIMEZONE,
    )



def _silence_label(ts_before: str, ts_after: str) -> str:
    """Retourne un marqueur de silence entre deux messages consecutifs.

    Transition compatibility: unit tests assert exact rendered strings.
    """
    return conversations_prompt_window.silence_label(ts_before, ts_after)

def _make_summary_message(summary: dict[str, Any]) -> dict[str, str]:
    return conversations_prompt_window.make_summary_message(summary)


def _get_active_summary(conversation_id: Optional[str]) -> Optional[dict[str, Any]]:
    return conversations_prompt_window.get_active_summary(
        conversation_id,
        normalize_conversation_id_func=normalize_conversation_id,
        db_conn_func=_db_conn,
        ts_to_iso_func=_ts_to_iso,
        logger=logger,
    )


def _make_memory_context_message(summaries: list[dict[str, Any]]) -> Optional[dict[str, str]]:
    return conversations_prompt_window.make_memory_context_message(summaries)


def _summary_cutoff_iso(summary: Optional[dict[str, Any]]) -> Optional[str]:
    return conversations_prompt_window.summary_cutoff_iso(
        summary,
        ts_to_iso_func=_ts_to_iso,
    )


def _message_is_after_summary(msg: dict[str, Any], cutoff_iso: Optional[str]) -> bool:
    return conversations_prompt_window.message_is_after_summary(
        msg,
        cutoff_iso,
        parse_iso_to_dt_func=_parse_iso_to_dt,
    )


def _make_memory_message(traces: list[dict[str, Any]], ts_now: str) -> Optional[dict[str, str]]:
    return conversations_prompt_window.make_memory_message(
        traces,
        ts_now,
        delta_t_label_func=delta_t_label,
    )


def _make_context_hints_message(
    hints: list[dict[str, Any]],
    ts_now: str,
    model: str,
) -> Optional[dict[str, str]]:
    return conversations_prompt_window.make_context_hints_message(
        hints,
        ts_now,
        model,
        delta_t_label_func=delta_t_label,
        count_tokens_func=count_tokens,
        context_hints_max_tokens=config.CONTEXT_HINTS_MAX_TOKENS,
        context_hints_max_items=config.CONTEXT_HINTS_MAX_ITEMS,
    )

def build_prompt_messages(
    conversation: dict[str, Any],
    model: str,
    now: Optional[str] = None,
    memory_traces: Optional[list[dict[str, Any]]] = None,
    context_hints: Optional[list[dict[str, Any]]] = None,
) -> list[dict[str, str]]:
    return conversations_prompt_window.build_prompt_messages(
        conversation,
        model,
        now=now,
        memory_traces=memory_traces,
        context_hints=context_hints,
        ensure_system_message_func=_ensure_system_message,
        get_active_summary_func=_get_active_summary,
        summary_cutoff_iso_func=_summary_cutoff_iso,
        message_is_after_summary_func=_message_is_after_summary,
        make_summary_message_func=_make_summary_message,
        make_context_hints_message_func=_make_context_hints_message,
        make_memory_context_message_func=_make_memory_context_message,
        make_memory_message_func=_make_memory_message,
        count_tokens_func=count_tokens,
        max_tokens=config.MAX_TOKENS,
        now_iso_func=_now_iso,
        logger=logger,
        admin_log_event_func=admin_logs.log_event,
        silence_label_func=_silence_label,
        delta_t_label_func=delta_t_label,
    )


# --- Maintenance and lifecycle (destructive path) ---

def delete_conversation(conversation_id: str) -> bool:
    conv_id = normalize_conversation_id(conversation_id)
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
) -> dict[str, Any]:
    return conversations_store.normalize_conversation(
        data,
        conversation_id,
        system_prompt,
        now_iso_func=_now_iso,
        safe_title_func=_safe_title,
        find_system_message_func=_find_system_message,
    )


def _find_system_message(messages: Iterable[dict[str, Any]]) -> Optional[dict[str, Any]]:
    return conversations_store.find_system_message(messages)


def _ensure_system_message(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return conversations_store.ensure_system_message(
        messages,
        find_system_message_func=_find_system_message,
        now_iso_func=_now_iso,
    )


def _now_iso() -> str:
    return conversations_store.now_iso()


def _now_compact() -> str:
    return conversations_store.now_compact()
