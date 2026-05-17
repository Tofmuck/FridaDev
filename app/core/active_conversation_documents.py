from __future__ import annotations

"""Server-side active document state scoped to one conversation.

This module intentionally lives in ``core``: active conversation documents are
short-lived conversation state, not Memory/RAG, Identity, Summary, or Biblio.
Parsing, prompt injection, HTTP endpoints, and dashboard projections are handled
by later lots.
"""

import hashlib
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import psycopg
from psycopg.rows import dict_row

import config
from admin import runtime_settings
from . import runtime_db_bootstrap

logger = logging.getLogger("frida.active_documents")

ACTIVE_DOCUMENTS_SOURCE = "active_conversation_documents"
ACTIVE_STATUS = "active"
INACTIVE_STATUS = "inactive"
DEFAULT_REMOVE_REASON = "manual_remove"


@dataclass(frozen=True)
class ActiveDocumentMetadata:
    document_id: str
    conversation_id: str
    filename: str
    media_type: str
    source_extension: str
    byte_size: int
    text_chars: int
    text_sha256_12: str
    token_estimate: int
    status: str
    active: bool
    created_at: str
    deactivated_at: str
    last_injected_turn_id: str
    last_excluded_turn_id: str
    last_excluded_reason_code: str
    ocr_applied: bool = False
    ocr_engine: str = ""
    ocr_languages: str = ""
    ocr_duration_ms: int = 0
    source: str = ACTIVE_DOCUMENTS_SOURCE

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "conversation_id": self.conversation_id,
            "filename": self.filename,
            "media_type": self.media_type,
            "source_extension": self.source_extension,
            "byte_size": self.byte_size,
            "text_chars": self.text_chars,
            "text_sha256_12": self.text_sha256_12,
            "token_estimate": self.token_estimate,
            "status": self.status,
            "active": self.active,
            "created_at": self.created_at,
            "deactivated_at": self.deactivated_at,
            "last_injected_turn_id": self.last_injected_turn_id,
            "last_excluded_turn_id": self.last_excluded_turn_id,
            "last_excluded_reason_code": self.last_excluded_reason_code,
            "ocr_applied": self.ocr_applied,
            "ocr_engine": self.ocr_engine,
            "ocr_languages": self.ocr_languages,
            "ocr_duration_ms": self.ocr_duration_ms,
            "source": self.source,
        }


@dataclass(frozen=True)
class ActiveDocumentPromptPayload:
    metadata: ActiveDocumentMetadata
    text_content: str

    def to_dict(self) -> dict[str, Any]:
        payload = self.metadata.to_dict()
        payload["text_content"] = self.text_content
        return payload


def _db_conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _normalize_uuid(value: Any) -> Optional[str]:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return str(uuid.UUID(raw))
    except (TypeError, ValueError):
        return None


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _ts_to_iso(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        dt = value
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    raw = str(value).strip()
    if not raw:
        return ""
    return raw


def _safe_text(value: Any, max_chars: int = 500) -> str:
    text = str(value or "").strip()
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars]
    return text


def _safe_int(value: Any) -> int:
    try:
        number = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, number)


def _safe_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    raw = str(value or "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _sha256_12(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _metadata_from_row(row: dict[str, Any]) -> ActiveDocumentMetadata:
    status = str(row.get("status") or "").strip() or INACTIVE_STATUS
    deactivated_at = row.get("deactivated_at")
    return ActiveDocumentMetadata(
        document_id=str(row.get("document_id") or ""),
        conversation_id=str(row.get("conversation_id") or ""),
        filename=str(row.get("filename") or ""),
        media_type=str(row.get("media_type") or ""),
        source_extension=str(row.get("source_extension") or ""),
        byte_size=_safe_int(row.get("byte_size")),
        text_chars=_safe_int(row.get("text_chars")),
        text_sha256_12=str(row.get("text_sha256_12") or ""),
        token_estimate=_safe_int(row.get("token_estimate")),
        status=status,
        active=status == ACTIVE_STATUS and not deactivated_at,
        created_at=_ts_to_iso(row.get("created_at")),
        deactivated_at=_ts_to_iso(deactivated_at),
        last_injected_turn_id=str(row.get("last_injected_turn_id") or ""),
        last_excluded_turn_id=str(row.get("last_excluded_turn_id") or ""),
        last_excluded_reason_code=str(row.get("last_excluded_reason_code") or ""),
        ocr_applied=_safe_bool(row.get("ocr_applied")),
        ocr_engine=str(row.get("ocr_engine") or ""),
        ocr_languages=str(row.get("ocr_languages") or ""),
        ocr_duration_ms=_safe_int(row.get("ocr_duration_ms")),
    )


def _prompt_payload_from_row(row: dict[str, Any]) -> ActiveDocumentPromptPayload:
    return ActiveDocumentPromptPayload(
        metadata=_metadata_from_row(row),
        text_content=str(row.get("text_content") or ""),
    )


def init_db(
    *,
    conn_factory: Optional[Callable[[], Any]] = None,
    logger_instance: Any = logger,
) -> bool:
    """Create the short-term active document table.

    The table references the conversation catalog and cascades on hard
    conversation deletion. Manual remove is still a soft deactivation so the
    state can be observed content-free until cleanup.
    """

    get_conn = conn_factory or _db_conn
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    CREATE TABLE IF NOT EXISTS active_conversation_documents (
                        document_id                UUID PRIMARY KEY,
                        conversation_id            UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                        filename                   TEXT NOT NULL,
                        media_type                 TEXT NOT NULL DEFAULT '',
                        source_extension           TEXT NOT NULL DEFAULT '',
                        byte_size                  INTEGER NOT NULL DEFAULT 0,
                        text_chars                 INTEGER NOT NULL DEFAULT 0,
                        text_sha256_12             TEXT NOT NULL DEFAULT '',
                        token_estimate             INTEGER NOT NULL DEFAULT 0,
                        status                     TEXT NOT NULL DEFAULT 'active',
                        text_content               TEXT NOT NULL,
                        created_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
                        deactivated_at             TIMESTAMPTZ,
                        last_injected_turn_id      TEXT,
                        last_excluded_turn_id      TEXT,
                        last_excluded_reason_code  TEXT,
                        ocr_applied                BOOLEAN NOT NULL DEFAULT FALSE,
                        ocr_engine                 TEXT NOT NULL DEFAULT '',
                        ocr_languages              TEXT NOT NULL DEFAULT '',
                        ocr_duration_ms            INTEGER NOT NULL DEFAULT 0
                    );
                    """
                )
                for column_sql in (
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS media_type TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS source_extension TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS byte_size INTEGER NOT NULL DEFAULT 0;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS text_chars INTEGER NOT NULL DEFAULT 0;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS text_sha256_12 TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS token_estimate INTEGER NOT NULL DEFAULT 0;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'active';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS text_content TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS deactivated_at TIMESTAMPTZ;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS last_injected_turn_id TEXT;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS last_excluded_turn_id TEXT;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS last_excluded_reason_code TEXT;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS ocr_applied BOOLEAN NOT NULL DEFAULT FALSE;",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS ocr_engine TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS ocr_languages TEXT NOT NULL DEFAULT '';",
                    "ALTER TABLE active_conversation_documents ADD COLUMN IF NOT EXISTS ocr_duration_ms INTEGER NOT NULL DEFAULT 0;",
                ):
                    cur.execute(column_sql)
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS active_conversation_documents_conv_active_idx
                    ON active_conversation_documents (conversation_id, deactivated_at, created_at DESC);
                    """
                )
                cur.execute(
                    """
                    CREATE INDEX IF NOT EXISTS active_conversation_documents_conv_status_idx
                    ON active_conversation_documents (conversation_id, status);
                    """
                )
            conn.commit()
        logger_instance.info("active_documents_init_ok")
        return True
    except Exception as exc:  # pragma: no cover - defensive runtime logging
        logger_instance.error("active_documents_init_failed err=%s", exc)
        return False


def activate_document(
    conversation_id: str,
    *,
    filename: str,
    text_content: str,
    media_type: str = "",
    source_extension: str = "",
    byte_size: int = 0,
    token_estimate: int = 0,
    ocr_applied: bool = False,
    ocr_engine: str = "",
    ocr_languages: str = "",
    ocr_duration_ms: int = 0,
    document_id: Optional[str] = None,
    conn_factory: Optional[Callable[[], Any]] = None,
    now_func: Callable[[], datetime] = _now_utc,
) -> Optional[dict[str, Any]]:
    conv_id = _normalize_uuid(conversation_id)
    if not conv_id:
        return None
    doc_id = _normalize_uuid(document_id) if document_id else str(uuid.uuid4())
    if not doc_id:
        return None

    text = str(text_content or "")
    created_at = now_func()
    row_values = (
        doc_id,
        conv_id,
        _safe_text(filename, 500),
        _safe_text(media_type, 120),
        _safe_text(source_extension, 40).lower(),
        _safe_int(byte_size),
        len(text),
        _sha256_12(text),
        _safe_int(token_estimate),
        ACTIVE_STATUS,
        text,
        created_at,
        _safe_bool(ocr_applied),
        _safe_text(ocr_engine, 120),
        _safe_text(ocr_languages, 120),
        _safe_int(ocr_duration_ms),
    )
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO active_conversation_documents (
                    document_id,
                    conversation_id,
                    filename,
                    media_type,
                    source_extension,
                    byte_size,
                    text_chars,
                    text_sha256_12,
                    token_estimate,
                    status,
                    text_content,
                    created_at,
                    ocr_applied,
                    ocr_engine,
                    ocr_languages,
                    ocr_duration_ms
                )
                VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING
                    document_id::text AS document_id,
                    conversation_id::text AS conversation_id,
                    filename,
                    media_type,
                    source_extension,
                    byte_size,
                    text_chars,
                    text_sha256_12,
                    token_estimate,
                    status,
                    created_at,
                    deactivated_at,
                    last_injected_turn_id,
                    last_excluded_turn_id,
                    last_excluded_reason_code,
                    ocr_applied,
                    ocr_engine,
                    ocr_languages,
                    ocr_duration_ms;
                """,
                row_values,
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        return None
    return _metadata_from_row(dict(row)).to_dict()


def list_active_documents(
    conversation_id: str,
    *,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> list[dict[str, Any]]:
    conv_id = _normalize_uuid(conversation_id)
    if not conv_id:
        return []
    rows = _read_active_document_rows(
        conv_id,
        include_text=False,
        conn_factory=conn_factory,
    )
    return [_metadata_from_row(dict(row)).to_dict() for row in rows]


def list_active_documents_for_prompt(
    conversation_id: str,
    *,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> list[dict[str, Any]]:
    """Return active documents with text for prompt construction only."""

    conv_id = _normalize_uuid(conversation_id)
    if not conv_id:
        return []
    rows = _read_active_document_rows(
        conv_id,
        include_text=True,
        conn_factory=conn_factory,
    )
    return [_prompt_payload_from_row(dict(row)).to_dict() for row in rows]


def get_active_document_for_prompt(
    conversation_id: str,
    document_id: str,
    *,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> Optional[dict[str, Any]]:
    conv_id = _normalize_uuid(conversation_id)
    doc_id = _normalize_uuid(document_id)
    if not conv_id or not doc_id:
        return None
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT
                    document_id::text AS document_id,
                    conversation_id::text AS conversation_id,
                    filename,
                    media_type,
                    source_extension,
                    byte_size,
                    text_chars,
                    text_sha256_12,
                    token_estimate,
                    status,
                    text_content,
                    created_at,
                    deactivated_at,
                    last_injected_turn_id,
                    last_excluded_turn_id,
                    last_excluded_reason_code,
                    ocr_applied,
                    ocr_engine,
                    ocr_languages,
                    ocr_duration_ms
                FROM active_conversation_documents
                WHERE conversation_id = %s::uuid
                  AND document_id = %s::uuid
                  AND status = 'active'
                  AND deactivated_at IS NULL
                """,
                (conv_id, doc_id),
            )
            row = cur.fetchone()
    if not row:
        return None
    return _prompt_payload_from_row(dict(row)).to_dict()


def record_document_injected(
    conversation_id: str,
    document_id: str,
    *,
    turn_id: str,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> bool:
    conv_id = _normalize_uuid(conversation_id)
    doc_id = _normalize_uuid(document_id)
    if not conv_id or not doc_id:
        return False
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE active_conversation_documents
                SET last_injected_turn_id = %s,
                    last_excluded_turn_id = '',
                    last_excluded_reason_code = ''
                WHERE conversation_id = %s::uuid
                  AND document_id = %s::uuid
                  AND status = 'active'
                  AND deactivated_at IS NULL
                """,
                (str(turn_id or ""), conv_id, doc_id),
            )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    return changed > 0


def record_document_excluded(
    conversation_id: str,
    document_id: str,
    *,
    turn_id: str,
    reason_code: str,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> bool:
    conv_id = _normalize_uuid(conversation_id)
    doc_id = _normalize_uuid(document_id)
    if not conv_id or not doc_id:
        return False
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE active_conversation_documents
                SET last_excluded_turn_id = %s,
                    last_excluded_reason_code = %s
                WHERE conversation_id = %s::uuid
                  AND document_id = %s::uuid
                  AND status = 'active'
                  AND deactivated_at IS NULL
                """,
                (
                    str(turn_id or ""),
                    _safe_text(reason_code, 120) or "document_runtime_unavailable",
                    conv_id,
                    doc_id,
                ),
            )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    return changed > 0


def deactivate_document(
    conversation_id: str,
    document_id: str,
    *,
    reason_code: str = DEFAULT_REMOVE_REASON,
    conn_factory: Optional[Callable[[], Any]] = None,
    now_func: Callable[[], datetime] = _now_utc,
) -> bool:
    conv_id = _normalize_uuid(conversation_id)
    doc_id = _normalize_uuid(document_id)
    if not conv_id or not doc_id:
        return False
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE active_conversation_documents
                SET status = %s,
                    deactivated_at = %s,
                    last_excluded_reason_code = %s
                WHERE conversation_id = %s::uuid
                  AND document_id = %s::uuid
                  AND status = 'active'
                  AND deactivated_at IS NULL
                """,
                (
                    INACTIVE_STATUS,
                    now_func(),
                    _safe_text(reason_code, 120) or DEFAULT_REMOVE_REASON,
                    conv_id,
                    doc_id,
                ),
            )
            changed = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    return changed > 0


def delete_conversation_documents(
    conversation_id: str,
    *,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> int:
    conv_id = _normalize_uuid(conversation_id)
    if not conv_id:
        return 0
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM active_conversation_documents
                WHERE conversation_id = %s::uuid
                """,
                (conv_id,),
            )
            deleted = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    return deleted


def purge_deactivated_documents(
    *,
    older_than: datetime,
    conversation_id: Optional[str] = None,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> int:
    conv_id = _normalize_uuid(conversation_id) if conversation_id else None
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor() as cur:
            if conv_id:
                cur.execute(
                    """
                    DELETE FROM active_conversation_documents
                    WHERE conversation_id = %s::uuid
                      AND deactivated_at IS NOT NULL
                      AND deactivated_at < %s
                    """,
                    (conv_id, older_than),
                )
            else:
                cur.execute(
                    """
                    DELETE FROM active_conversation_documents
                    WHERE deactivated_at IS NOT NULL
                      AND deactivated_at < %s
                    """,
                    (older_than,),
                )
            deleted = int(getattr(cur, "rowcount", 0) or 0)
        conn.commit()
    return deleted


def _read_active_document_rows(
    conversation_id: str,
    *,
    include_text: bool,
    conn_factory: Optional[Callable[[], Any]] = None,
) -> list[dict[str, Any]]:
    text_column = ", text_content" if include_text else ""
    get_conn = conn_factory or _db_conn
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                f"""
                SELECT
                    document_id::text AS document_id,
                    conversation_id::text AS conversation_id,
                    filename,
                    media_type,
                    source_extension,
                    byte_size,
                    text_chars,
                    text_sha256_12,
                    token_estimate,
                    status{text_column},
                    created_at,
                    deactivated_at,
                    last_injected_turn_id,
                    last_excluded_turn_id,
                    last_excluded_reason_code,
                    ocr_applied,
                    ocr_engine,
                    ocr_languages,
                    ocr_duration_ms
                FROM active_conversation_documents
                WHERE conversation_id = %s::uuid
                  AND status = 'active'
                  AND deactivated_at IS NULL
                ORDER BY created_at ASC, filename ASC
                """,
                (conversation_id,),
            )
            rows = cur.fetchall()
    return [dict(row) for row in rows]
