from __future__ import annotations

import logging
import math
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import psycopg
import requests

import config
from admin import runtime_settings
from core import runtime_db_bootstrap
from memory import hermeneutics_policy as policy

logger = logging.getLogger('kiki.memory_store')


# Connection

def _conn():
    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _runtime_database_view() -> runtime_settings.RuntimeSectionView:
    return runtime_db_bootstrap.runtime_database_view(runtime_settings)


def _runtime_database_backend() -> str:
    return runtime_db_bootstrap.runtime_database_backend(runtime_settings)


def _bootstrap_database_dsn() -> str:
    return runtime_db_bootstrap.bootstrap_database_dsn(config, runtime_settings)


def _normalize_identity_content(content: str) -> str:
    return re.sub(r'\s+', ' ', (content or '').strip().lower())


def _trace_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _runtime_embedding_view() -> runtime_settings.RuntimeSectionView:
    return runtime_settings.get_embedding_settings()


def _runtime_embedding_value(field: str) -> Any:
    view = _runtime_embedding_view()
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return payload['value']

    env_bundle = runtime_settings.build_env_seed_bundle('embedding')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return fallback['value']

    raise KeyError(f'missing embedding runtime value: {field}')


def _runtime_embedding_token() -> str:
    secret = runtime_settings.get_runtime_secret_value('embedding', 'token')
    return str(secret.value)


# Schema initialization

def init_db() -> None:
    """Create tables/indexes if absent. Never crash app startup when DB is unavailable."""
    embed_dim = int(_runtime_embedding_value('dimensions'))
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE EXTENSION IF NOT EXISTS vector;')
                cur.execute('CREATE EXTENSION IF NOT EXISTS pgcrypto;')

                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS traces (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id TEXT        NOT NULL,
                        role            TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        timestamp       TIMESTAMPTZ,
                        embedding       vector({embed_dim}),
                        summary_id      TEXT
                    );
                    '''
                )

                cur.execute(
                    f'''
                    CREATE TABLE IF NOT EXISTS summaries (
                        id              UUID PRIMARY KEY,
                        conversation_id TEXT        NOT NULL,
                        start_ts        TIMESTAMPTZ,
                        end_ts          TIMESTAMPTZ,
                        content         TEXT        NOT NULL,
                        embedding       vector({embed_dim})
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identities (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        subject         TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        weight          FLOAT       DEFAULT 1.0,
                        created_ts      TIMESTAMPTZ DEFAULT now(),
                        last_seen_ts    TIMESTAMPTZ DEFAULT now(),
                        source_trace_id UUID
                    );
                    '''
                )

                # identities migration (idempotent)
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS conversation_id TEXT;")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS stability TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS utterance_mode TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS recurrence TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS scope TEXT DEFAULT 'unknown';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS evidence_kind TEXT DEFAULT 'weak';")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS confidence FLOAT DEFAULT 0.0;")
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS status TEXT DEFAULT 'accepted';")
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS content_norm TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS last_reason TEXT;')
                cur.execute("ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_state TEXT DEFAULT 'none';")
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_reason TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_actor TEXT;')
                cur.execute('ALTER TABLE identities ADD COLUMN IF NOT EXISTS override_ts TIMESTAMPTZ;')

                cur.execute(
                    """
                    UPDATE identities
                    SET content_norm = lower(regexp_replace(trim(content), '\\s+', ' ', 'g'))
                    WHERE content_norm IS NULL
                    """
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identity_evidence (
                        id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id TEXT,
                        subject         TEXT        NOT NULL,
                        content         TEXT        NOT NULL,
                        content_norm    TEXT,
                        stability       TEXT        DEFAULT 'unknown',
                        utterance_mode  TEXT        DEFAULT 'unknown',
                        recurrence      TEXT        DEFAULT 'unknown',
                        scope           TEXT        DEFAULT 'unknown',
                        evidence_kind   TEXT        DEFAULT 'weak',
                        confidence      FLOAT       DEFAULT 0.0,
                        status          TEXT        DEFAULT 'accepted',
                        reason          TEXT,
                        source_trace_id UUID,
                        created_ts      TIMESTAMPTZ DEFAULT now()
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS arbiter_decisions (
                        id                    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        conversation_id       TEXT        NOT NULL,
                        candidate_id          TEXT        NOT NULL,
                        candidate_role        TEXT,
                        candidate_content     TEXT,
                        candidate_ts          TIMESTAMPTZ,
                        candidate_score       FLOAT,
                        keep                  BOOLEAN     NOT NULL,
                        semantic_relevance    FLOAT       DEFAULT 0.0,
                        contextual_gain       FLOAT       DEFAULT 0.0,
                        redundant_with_recent BOOLEAN     DEFAULT FALSE,
                        reason                TEXT,
                        model                 TEXT,
                        decision_source       TEXT        DEFAULT 'llm',
                        created_ts            TIMESTAMPTZ DEFAULT now()
                    );
                    '''
                )

                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS identity_conflicts (
                        id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                        identity_id_a        UUID NOT NULL,
                        identity_id_b        UUID NOT NULL,
                        confidence_conflict  FLOAT DEFAULT 0.0,
                        reason               TEXT,
                        resolved_state       TEXT DEFAULT 'open',
                        created_ts           TIMESTAMPTZ DEFAULT now(),
                        resolved_ts          TIMESTAMPTZ
                    );
                    '''
                )

                # embedding indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS traces_embedding_hnsw
                    ON traces USING hnsw (embedding vector_cosine_ops);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS summaries_embedding_hnsw
                    ON summaries USING hnsw (embedding vector_cosine_ops);
                    '''
                )

                # identities indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_subject_weight_idx
                    ON identities (subject, weight DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_status_idx
                    ON identities (status);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_content_norm_idx
                    ON identities (content_norm);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identities_created_ts_idx
                    ON identities (created_ts DESC);
                    '''
                )

                # evidence indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_conversation_created_idx
                    ON identity_evidence (conversation_id, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_status_idx
                    ON identity_evidence (status);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_evidence_content_norm_idx
                    ON identity_evidence (content_norm);
                    '''
                )

                # arbiter indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS arbiter_decisions_conversation_created_idx
                    ON arbiter_decisions (conversation_id, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS arbiter_decisions_keep_idx
                    ON arbiter_decisions (keep);
                    '''
                )

                # conflict indexes
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_conflicts_open_idx
                    ON identity_conflicts (resolved_state, created_ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS identity_conflicts_pair_idx
                    ON identity_conflicts (identity_id_a, identity_id_b);
                    '''
                )

            conn.commit()
        logger.info('memory_db_init ok')
    except Exception as exc:
        logger.error('memory_db_init_failed err=%s', exc)


# Embedding

def embed(text: str, mode: str = 'passage') -> List[float]:
    """
    Call OVH embedding service.
    mode='passage' for stored docs, mode='query' for retrieval requests.
    """
    prefix = 'query: ' if mode == 'query' else 'passage: '
    endpoint = str(_runtime_embedding_value('endpoint')).rstrip('/')
    model = str(_runtime_embedding_value('model') or '').strip()
    r = requests.post(
        f'{endpoint}/embed',
        headers={
            'X-Embed-Token': _runtime_embedding_token(),
            'Content-Type': 'application/json',
        },
        json={
            'inputs': [f'{prefix}{text}'],
            'model': model,
        },
        timeout=(5, 120),
    )
    r.raise_for_status()
    return r.json()[0]


# Trace persistence

def _trace_exists_for_message(conversation_id: str, message: Dict[str, Any]) -> bool:
    role = str(message.get('role') or '').strip()
    content = str(message.get('content') or '')
    timestamp = message.get('timestamp')
    if not conversation_id or not role or not content:
        return False

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                if timestamp:
                    cur.execute(
                        '''
                        SELECT 1
                        FROM traces
                        WHERE conversation_id = %s
                          AND role = %s
                          AND content = %s
                          AND timestamp = %s::timestamptz
                        LIMIT 1
                        ''',
                        (conversation_id, role, content, timestamp),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT 1
                        FROM traces
                        WHERE conversation_id = %s
                          AND role = %s
                          AND content = %s
                          AND timestamp IS NULL
                        LIMIT 1
                        ''',
                        (conversation_id, role, content),
                    )
                return cur.fetchone() is not None
    except Exception as exc:
        logger.warning('trace_exists_check_failed conv=%s err=%s', conversation_id, exc)
        return False

def save_new_traces(conversation: Dict[str, Any]) -> None:
    """
    Embed and persist user/assistant messages not yet marked as embedded.
    Never raises: conversation save must not depend on this.
    """
    conv_id = conversation.get('id', '')
    to_embed = [
        m
        for m in conversation.get('messages', [])
        if m.get('role') in {'user', 'assistant'} and not m.get('embedded')
    ]
    if not to_embed:
        return

    for m in to_embed:
        if _trace_exists_for_message(conv_id, m):
            m['embedded'] = True
            logger.info(
                'trace_exists_skip conv=%s role=%s ts=%s',
                conv_id,
                m.get('role'),
                m.get('timestamp'),
            )
            continue

        try:
            vec = embed(m['content'], mode='passage')
        except Exception as exc:
            logger.warning('embed_skip role=%s err=%s', m.get('role'), exc)
            vec = None

        try:
            with _conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        INSERT INTO traces
                            (conversation_id, role, content, timestamp, embedding, summary_id)
                        VALUES (%s, %s, %s, %s, %s::vector, %s)
                        ''',
                        (
                            conv_id,
                            m['role'],
                            m['content'],
                            m.get('timestamp'),
                            str(vec) if vec is not None else None,
                            m.get('summarized_by'),
                        ),
                    )
                conn.commit()
            m['embedded'] = True
        except Exception as exc:
            logger.error('save_trace_error conv=%s err=%s', conv_id, exc)


# Retrieval

def retrieve(query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
    """
    Embed query and return top_k nearest traces (cosine similarity).
    Return [] on error to avoid blocking response pipeline.
    """
    if top_k is None:
        top_k = int(_runtime_embedding_value('top_k'))

    try:
        q_vec = embed(query, mode='query')
    except Exception as exc:
        logger.warning('retrieve_embed_failed err=%s', exc)
        return []

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT conversation_id, role, content, timestamp, summary_id,
                           1 - (embedding <=> %s::vector) AS score
                    FROM   traces
                    WHERE  embedding IS NOT NULL
                    ORDER  BY embedding <=> %s::vector
                    LIMIT  %s
                    ''',
                    (str(q_vec), str(q_vec), top_k),
                )
                rows = cur.fetchall()
        return [
            {
                'conversation_id': r[0],
                'role': r[1],
                'content': r[2],
                'timestamp': str(r[3]) if r[3] else None,
                'summary_id': str(r[4]) if r[4] else None,
                'score': float(r[5]),
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error('retrieve_error err=%s', exc)
        return []


# Summary persistence

def save_summary(conversation_id: str, summary: Dict[str, Any]) -> None:
    """
    Persist a summary into `summaries`.
    Embedding failure does not prevent text persistence.
    """
    content = summary.get('content', '')
    try:
        vec = embed(content, mode='passage')
    except Exception as exc:
        logger.warning('summary_embed_skip err=%s', exc)
        vec = None

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO summaries
                        (id, conversation_id, start_ts, end_ts, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO NOTHING
                    ''',
                    (
                        summary['id'],
                        conversation_id,
                        summary.get('start_ts') or None,
                        summary.get('end_ts') or None,
                        content,
                        str(vec) if vec is not None else None,
                    ),
                )
            conn.commit()
        logger.info('summary_saved conv=%s summary_id=%s', conversation_id, summary['id'][:8])
    except Exception as exc:
        logger.error('save_summary_error conv=%s err=%s', conversation_id, exc)


# Update trace summary_id

def update_traces_summary_id(
    conversation_id: str,
    summary_id: str,
    start_ts: Optional[str],
    end_ts: Optional[str],
) -> None:
    """
    Set summary_id on traces covered by [start_ts, end_ts] where summary_id is still NULL.
    """
    if not start_ts or not end_ts:
        return
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE traces
                    SET    summary_id = %s
                    WHERE  conversation_id = %s
                      AND  timestamp >= %s::timestamptz
                      AND  timestamp <= %s::timestamptz
                      AND  summary_id IS NULL
                    ''',
                    (summary_id, conversation_id, start_ts, end_ts),
                )
            conn.commit()
        logger.debug('traces_summary_id_updated conv=%s summary_id=%s', conversation_id, summary_id[:8])
    except Exception as exc:
        logger.error('update_traces_summary_id_error conv=%s err=%s', conversation_id, exc)


# Parent summary for a trace

def get_summary_for_trace(trace: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Return parent summary for a trace:
    - by summary_id when available,
    - otherwise by time overlap on same conversation_id.
    """
    summary_id = trace.get('summary_id')
    conv_id = trace.get('conversation_id')
    ts = trace.get('timestamp')

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                if summary_id:
                    cur.execute(
                        '''
                        SELECT id, conversation_id, start_ts, end_ts, content
                        FROM   summaries
                        WHERE  id = %s
                        ''',
                        (summary_id,),
                    )
                elif conv_id and ts:
                    cur.execute(
                        '''
                        SELECT id, conversation_id, start_ts, end_ts, content
                        FROM   summaries
                        WHERE  conversation_id = %s
                          AND  start_ts <= %s::timestamptz
                          AND  end_ts   >= %s::timestamptz
                        ORDER  BY end_ts DESC
                        LIMIT  1
                        ''',
                        (conv_id, ts, ts),
                    )
                else:
                    return None
                row = cur.fetchone()
        if not row:
            return None
        return {
            'id': str(row[0]),
            'conversation_id': row[1],
            'start_ts': str(row[2]) if row[2] else None,
            'end_ts': str(row[3]) if row[3] else None,
            'content': row[4],
        }
    except Exception as exc:
        logger.warning('get_summary_for_trace_error err=%s', exc)
        return None


def enrich_traces_with_summaries(traces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Add trace['parent_summary'] for each trace with internal cache to avoid redundant DB calls.
    """
    cache: Dict[str, Optional[Dict[str, Any]]] = {}
    for trace in traces:
        summary_id = trace.get('summary_id')
        cache_key = summary_id or f"{trace.get('conversation_id')}@{trace.get('timestamp')}"
        if cache_key not in cache:
            cache[cache_key] = get_summary_for_trace(trace)
        trace['parent_summary'] = cache[cache_key]
    return traces


# Identity retrieval

def get_identities(
    subject: str,
    top_n: Optional[int] = None,
    status: Optional[str] = 'accepted',
) -> List[Dict[str, Any]]:
    """
    Return top-N identities for a subject, sorted by weight.
    By default, only accepted identities are returned.
    """
    if top_n is None:
        top_n = config.IDENTITY_TOP_N
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                if status is None:
                    cur.execute(
                        '''
                        SELECT id, subject, content, weight, created_ts, last_seen_ts, source_trace_id,
                               stability, utterance_mode, recurrence, scope, evidence_kind, confidence,
                               status, content_norm, last_reason, conversation_id, override_state,
                               override_reason, override_actor, override_ts
                        FROM   identities
                        WHERE  subject = %s
                        ORDER  BY weight DESC
                        LIMIT  %s
                        ''',
                        (subject, top_n),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT id, subject, content, weight, created_ts, last_seen_ts, source_trace_id,
                               stability, utterance_mode, recurrence, scope, evidence_kind, confidence,
                               status, content_norm, last_reason, conversation_id, override_state,
                               override_reason, override_actor, override_ts
                        FROM   identities
                        WHERE  subject = %s
                          AND  status = %s
                        ORDER  BY weight DESC
                        LIMIT  %s
                        ''',
                        (subject, status, top_n),
                    )
                rows = cur.fetchall()
        return [
            {
                'id': str(r[0]),
                'subject': r[1],
                'content': r[2],
                'weight': float(r[3]),
                'created_ts': str(r[4]) if r[4] else None,
                'last_seen_ts': str(r[5]) if r[5] else None,
                'source_trace_id': str(r[6]) if r[6] else None,
                'stability': r[7],
                'utterance_mode': r[8],
                'recurrence': r[9],
                'scope': r[10],
                'evidence_kind': r[11],
                'confidence': float(r[12] or 0.0),
                'status': r[13],
                'content_norm': r[14],
                'last_reason': r[15],
                'conversation_id': r[16],
                'override_state': r[17],
                'override_reason': r[18],
                'override_actor': r[19],
                'override_ts': str(r[20]) if r[20] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error('get_identities_error subject=%s err=%s', subject, exc)
        return []


def get_recent_context_hints(
    max_items: Optional[int] = None,
    max_age_days: Optional[int] = None,
    min_confidence: Optional[float] = None,
) -> List[Dict[str, Any]]:
    """
    Return non-durable context hints from recent episodic/situation evidence.
    This reads evidence only and never promotes content into durable identity.
    """
    if max_items is None:
        max_items = config.CONTEXT_HINTS_MAX_ITEMS
    if max_age_days is None:
        max_age_days = config.CONTEXT_HINTS_MAX_AGE_DAYS
    if min_confidence is None:
        min_confidence = config.CONTEXT_HINTS_MIN_CONFIDENCE

    max_items = max(0, int(max_items))
    if max_items == 0:
        return []

    fetch_limit = max(5, max_items * 8)

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        conversation_id,
                        content,
                        content_norm,
                        created_ts,
                        confidence,
                        scope,
                        stability,
                        utterance_mode,
                        (
                            COALESCE(confidence, 0.0)
                            * (1.0 / (1.0 + GREATEST(EXTRACT(EPOCH FROM (now() - created_ts)) / 3600.0, 0.0)))
                        ) AS score
                    FROM identity_evidence
                    WHERE subject = %s
                      AND created_ts >= (now() - make_interval(days => %s))
                      AND (stability = %s OR scope = %s)
                      AND COALESCE(confidence, 0.0) >= %s
                      AND COALESCE(utterance_mode, %s) NOT IN (%s, %s, %s)
                      AND COALESCE(status, %s) IN (%s, %s)
                    ORDER BY score DESC, created_ts DESC
                    LIMIT %s
                    """,
                    (
                        "user",
                        max(1, int(max_age_days)),
                        "episodic",
                        "situation",
                        float(min_confidence),
                        "unknown",
                        "irony",
                        "role_play",
                        "unknown",
                        "accepted",
                        "accepted",
                        "deferred",
                        fetch_limit,
                    ),
                )
                rows = cur.fetchall()

        hints: List[Dict[str, Any]] = []
        seen_norm: set[str] = set()
        for row in rows:
            content = str(row[1] or "").strip()
            if not content:
                continue
            norm = str(row[2] or "").strip()
            if norm and norm in seen_norm:
                continue
            if norm:
                seen_norm.add(norm)

            hints.append(
                {
                    "conversation_id": str(row[0] or ""),
                    "content": content,
                    "timestamp": row[3].isoformat() if isinstance(row[3], datetime) else "",
                    "confidence": float(row[4] or 0.0),
                    "scope": str(row[5] or "user"),
                    "stability": str(row[6] or "unknown"),
                    "utterance_mode": str(row[7] or "unknown"),
                    "score": float(row[8] or 0.0),
                }
            )
            if len(hints) >= max_items:
                break

        return hints
    except Exception as exc:
        logger.error("get_recent_context_hints_error err=%s", exc)
        return []



def get_hermeneutic_kpis(window_days: int = 7) -> Dict[str, Any]:
    window_days = max(1, min(int(window_days), 365))
    out: Dict[str, Any] = {
        'window_days': window_days,
        'identity_accept_count': 0,
        'identity_defer_count': 0,
        'identity_reject_count': 0,
        'identity_override_count': 0,
        'arbiter_fallback_count': 0,
        'arbiter_decision_count': 0,
        'fallback_rate': 0.0,
    }

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT status, COUNT(*)
                    FROM identity_evidence
                    WHERE created_ts >= (now() - make_interval(days => %s))
                    GROUP BY status
                    ''',
                    (window_days,),
                )
                for status, count in cur.fetchall():
                    status_s = str(status or '').strip().lower()
                    if status_s == 'accepted':
                        out['identity_accept_count'] = int(count or 0)
                    elif status_s == 'deferred':
                        out['identity_defer_count'] = int(count or 0)
                    elif status_s == 'rejected':
                        out['identity_reject_count'] = int(count or 0)

                cur.execute(
                    '''
                    SELECT COUNT(*)
                    FROM identities
                    WHERE override_ts IS NOT NULL
                      AND override_ts >= (now() - make_interval(days => %s))
                    ''',
                    (window_days,),
                )
                out['identity_override_count'] = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    '''
                    SELECT
                        COUNT(*) AS total,
                        COUNT(*) FILTER (WHERE decision_source = 'fallback') AS fallback
                    FROM arbiter_decisions
                    WHERE created_ts >= (now() - make_interval(days => %s))
                    ''',
                    (window_days,),
                )
                total, fallback = cur.fetchone() or (0, 0)
                total_i = int(total or 0)
                fallback_i = int(fallback or 0)
                out['arbiter_decision_count'] = total_i
                out['arbiter_fallback_count'] = fallback_i
                out['fallback_rate'] = (float(fallback_i) / total_i) if total_i > 0 else 0.0

        return out
    except Exception as exc:
        logger.error('get_hermeneutic_kpis_error err=%s', exc)
        return out


def get_arbiter_decisions(
    limit: int = 200,
    conversation_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                if conversation_id:
                    cur.execute(
                        '''
                        SELECT
                            id,
                            conversation_id,
                            candidate_id,
                            candidate_role,
                            candidate_content,
                            candidate_ts,
                            candidate_score,
                            keep,
                            semantic_relevance,
                            contextual_gain,
                            redundant_with_recent,
                            reason,
                            model,
                            decision_source,
                            created_ts
                        FROM arbiter_decisions
                        WHERE conversation_id = %s
                        ORDER BY created_ts DESC
                        LIMIT %s
                        ''',
                        (conversation_id, limit),
                    )
                else:
                    cur.execute(
                        '''
                        SELECT
                            id,
                            conversation_id,
                            candidate_id,
                            candidate_role,
                            candidate_content,
                            candidate_ts,
                            candidate_score,
                            keep,
                            semantic_relevance,
                            contextual_gain,
                            redundant_with_recent,
                            reason,
                            model,
                            decision_source,
                            created_ts
                        FROM arbiter_decisions
                        ORDER BY created_ts DESC
                        LIMIT %s
                        ''',
                        (limit,),
                    )
                rows = cur.fetchall()

        return [
            {
                'id': str(r[0]),
                'conversation_id': str(r[1] or ''),
                'candidate_id': str(r[2] or ''),
                'candidate_role': r[3],
                'candidate_content': r[4],
                'candidate_ts': str(r[5]) if r[5] else None,
                'candidate_score': float(r[6] or 0.0),
                'keep': bool(r[7]),
                'semantic_relevance': float(r[8] or 0.0),
                'contextual_gain': float(r[9] or 0.0),
                'redundant_with_recent': bool(r[10]),
                'reason': r[11],
                'model': r[12],
                'decision_source': r[13],
                'created_ts': str(r[14]) if r[14] else None,
            }
            for r in rows
        ]
    except Exception as exc:
        logger.error('get_arbiter_decisions_error err=%s', exc)
        return []


def set_identity_override(
    identity_id: str,
    override_state: str,
    *,
    reason: str = '',
    actor: str = 'admin',
) -> bool:
    override_state = str(override_state or 'none').strip().lower()
    if override_state not in {'none', 'force_accept', 'force_reject'}:
        return False

    status = None
    if override_state == 'force_accept':
        status = 'accepted'
    elif override_state == 'force_reject':
        status = 'rejected'

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        '''
                        UPDATE identities
                        SET
                            override_state = %s,
                            override_reason = %s,
                            override_actor = %s,
                            override_ts = now(),
                            status = %s,
                            last_reason = %s
                        WHERE id = %s::uuid
                        ''',
                        (
                            override_state,
                            reason[:500] if reason else None,
                            actor[:120] if actor else None,
                            status,
                            f'override:{override_state}:{reason}'[:500] if reason else f'override:{override_state}',
                            identity_id,
                        ),
                    )
                else:
                    cur.execute(
                        '''
                        UPDATE identities
                        SET
                            override_state = %s,
                            override_reason = %s,
                            override_actor = %s,
                            override_ts = now(),
                            last_reason = %s
                        WHERE id = %s::uuid
                        ''',
                        (
                            override_state,
                            reason[:500] if reason else None,
                            actor[:120] if actor else None,
                            f'override:{override_state}:{reason}'[:500] if reason else f'override:{override_state}',
                            identity_id,
                        ),
                    )
                updated = cur.rowcount > 0
            conn.commit()
        return updated
    except Exception as exc:
        logger.error('set_identity_override_error id=%s err=%s', identity_id, exc)
        return False


def relabel_identity(
    identity_id: str,
    *,
    stability: Optional[str] = None,
    utterance_mode: Optional[str] = None,
    scope: Optional[str] = None,
    reason: str = '',
    actor: str = 'admin',
) -> bool:
    allowed_stability = {'durable', 'episodic', 'unknown'}
    allowed_utterance_mode = {
        'self_description',
        'projection',
        'role_play',
        'irony',
        'speculation',
        'unknown',
    }
    allowed_scope = {'user', 'llm', 'situation', 'mixed', 'unknown'}

    fields: List[str] = []
    values: List[Any] = []

    if stability is not None:
        stability = str(stability).strip()
        if stability not in allowed_stability:
            return False
        fields.append('stability = %s')
        values.append(stability)

    if utterance_mode is not None:
        utterance_mode = str(utterance_mode).strip()
        if utterance_mode not in allowed_utterance_mode:
            return False
        fields.append('utterance_mode = %s')
        values.append(utterance_mode)

    if scope is not None:
        scope = str(scope).strip()
        if scope not in allowed_scope:
            return False
        fields.append('scope = %s')
        values.append(scope)

    if not fields:
        return False

    fields.extend([
        'override_reason = %s',
        'override_actor = %s',
        'override_ts = now()',
        'last_reason = %s',
    ])
    values.extend([
        reason[:500] if reason else None,
        actor[:120] if actor else None,
        f'override:relabel:{reason}'[:500] if reason else 'override:relabel',
    ])
    values.append(identity_id)

    query = f"UPDATE identities SET {', '.join(fields)} WHERE id = %s::uuid"

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                updated = cur.rowcount > 0
            conn.commit()
        return updated
    except Exception as exc:
        logger.error('relabel_identity_error id=%s err=%s', identity_id, exc)
        return False



# Arbiter decision persistence

def record_arbiter_decisions(
    conversation_id: str,
    traces: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    *,
    effective_model: str | None = None,
) -> None:
    if not conversation_id or not decisions:
        return

    try:
        fallback_arbiter_model = str(effective_model or '').strip() or None
        with _conn() as conn:
            with conn.cursor() as cur:
                for decision in decisions:
                    candidate_id = str(decision.get('candidate_id', '')).strip()
                    if not candidate_id.isdigit():
                        continue
                    idx = int(candidate_id)
                    trace = traces[idx] if 0 <= idx < len(traces) else {}
                    decision_model = str(decision.get('model') or '').strip()
                    if not decision_model and fallback_arbiter_model:
                        decision_model = fallback_arbiter_model

                    cur.execute(
                        '''
                        INSERT INTO arbiter_decisions (
                            conversation_id,
                            candidate_id,
                            candidate_role,
                            candidate_content,
                            candidate_ts,
                            candidate_score,
                            keep,
                            semantic_relevance,
                            contextual_gain,
                            redundant_with_recent,
                            reason,
                            model,
                            decision_source
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            conversation_id,
                            candidate_id,
                            trace.get('role'),
                            trace.get('content'),
                            trace.get('timestamp'),
                            _trace_float(trace.get('score')),
                            bool(decision.get('keep', False)),
                            _trace_float(decision.get('semantic_relevance')),
                            _trace_float(decision.get('contextual_gain')),
                            bool(decision.get('redundant_with_recent', False)),
                            str(decision.get('reason', ''))[:500],
                            decision_model,
                            str(decision.get('decision_source', 'llm'))[:32],
                        ),
                    )
            conn.commit()
        logger.info('arbiter_decisions_saved conv=%s count=%s', conversation_id, len(decisions))
    except Exception as exc:
        logger.error('record_arbiter_decisions_error conv=%s err=%s', conversation_id, exc)


# Identity evidence persistence

def record_identity_evidence(
    conversation_id: str,
    entries: List[Dict[str, Any]],
    source_trace_id: Optional[str] = None,
) -> None:
    if not entries:
        return

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                for entry in entries:
                    content = str(entry.get('content', '')).strip()
                    subject = str(entry.get('subject', '')).strip()
                    if subject not in {'user', 'llm'} or not content:
                        continue

                    cur.execute(
                        '''
                        INSERT INTO identity_evidence (
                            conversation_id,
                            subject,
                            content,
                            content_norm,
                            stability,
                            utterance_mode,
                            recurrence,
                            scope,
                            evidence_kind,
                            confidence,
                            status,
                            reason,
                            source_trace_id
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ''',
                        (
                            conversation_id,
                            subject,
                            content,
                            _normalize_identity_content(content),
                            str(entry.get('stability', 'unknown')),
                            str(entry.get('utterance_mode', 'unknown')),
                            str(entry.get('recurrence', 'unknown')),
                            str(entry.get('scope', 'unknown')),
                            str(entry.get('evidence_kind', 'weak')),
                            _trace_float(entry.get('confidence')),
                            str(entry.get('status', 'accepted')),
                            str(entry.get('reason', ''))[:500],
                            source_trace_id,
                        ),
                    )
            conn.commit()
        logger.info('identity_evidence_saved conv=%s count=%s', conversation_id, len(entries))
    except Exception as exc:
        logger.error('record_identity_evidence_error conv=%s err=%s', conversation_id, exc)


# Identity row upsert

def add_identity(
    subject: str,
    content: str,
    source_trace_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    *,
    stability: str = 'unknown',
    utterance_mode: str = 'unknown',
    recurrence: str = 'unknown',
    scope: str = 'unknown',
    evidence_kind: str = 'weak',
    confidence: float = 0.0,
    status: str = 'accepted',
    reason: str = '',
) -> Optional[str]:
    """Insert or update a normalized identity entry with metadata."""
    subject = str(subject or '').strip()
    content = str(content or '').strip()
    if subject not in {'user', 'llm'} or not content:
        return None

    content_norm = _normalize_identity_content(content)
    confidence_f = _trace_float(confidence)

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, override_state
                    FROM identities
                    WHERE subject = %s AND content_norm = %s
                    ORDER BY last_seen_ts DESC
                    LIMIT 1
                    ''',
                    (subject, content_norm),
                )
                row = cur.fetchone()

                if row:
                    identity_id = str(row[0])
                    override_state = str(row[1] or 'none')

                    if override_state == 'force_reject':
                        effective_status = 'rejected'
                    elif override_state == 'force_accept':
                        effective_status = 'accepted'
                    else:
                        effective_status = status

                    cur.execute(
                        '''
                        UPDATE identities
                        SET
                            weight = LEAST(weight * 1.1, 2.5),
                            last_seen_ts = now(),
                            conversation_id = COALESCE(%s, conversation_id),
                            source_trace_id = COALESCE(%s, source_trace_id),
                            stability = CASE WHEN %s <> 'unknown' THEN %s ELSE stability END,
                            utterance_mode = CASE WHEN %s <> 'unknown' THEN %s ELSE utterance_mode END,
                            recurrence = CASE WHEN %s <> 'unknown' THEN %s ELSE recurrence END,
                            scope = CASE WHEN %s <> 'unknown' THEN %s ELSE scope END,
                            evidence_kind = CASE WHEN %s <> 'weak' THEN %s ELSE evidence_kind END,
                            confidence = GREATEST(confidence, %s),
                            status = %s,
                            last_reason = CASE WHEN %s <> '' THEN %s ELSE last_reason END
                        WHERE id = %s
                        ''',
                        (
                            conversation_id,
                            source_trace_id,
                            stability,
                            stability,
                            utterance_mode,
                            utterance_mode,
                            recurrence,
                            recurrence,
                            scope,
                            scope,
                            evidence_kind,
                            evidence_kind,
                            confidence_f,
                            effective_status,
                            reason,
                            reason,
                            identity_id,
                        ),
                    )
                else:
                    cur.execute(
                        '''
                        INSERT INTO identities (
                            conversation_id,
                            subject,
                            content,
                            content_norm,
                            weight,
                            source_trace_id,
                            stability,
                            utterance_mode,
                            recurrence,
                            scope,
                            evidence_kind,
                            confidence,
                            status,
                            last_reason
                        )
                        VALUES (
                            %s, %s, %s, %s, 1.0, %s,
                            %s, %s, %s, %s, %s, %s, %s, %s
                        )
                        RETURNING id
                        ''',
                        (
                            conversation_id,
                            subject,
                            content,
                            content_norm,
                            source_trace_id,
                            stability,
                            utterance_mode,
                            recurrence,
                            scope,
                            evidence_kind,
                            confidence_f,
                            status,
                            reason,
                        ),
                    )
                    identity_id = str(cur.fetchone()[0])
            conn.commit()
        logger.info('identity_saved subject=%s content=%.60s status=%s', subject, content, status)
        return identity_id
    except Exception as exc:
        logger.error('add_identity_error subject=%s err=%s', subject, exc)
        return None


# Contradictions and conflicts

def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _embedding_similarity_safe(text_a: str, text_b: str) -> Optional[float]:
    try:
        vec_a = embed(text_a, mode='passage')
        vec_b = embed(text_b, mode='passage')
        return _cosine_similarity(vec_a, vec_b)
    except Exception as exc:
        logger.warning('conflict_embedding_similarity_error err=%s', exc)
        return None


def _ordered_pair(id_a: str, id_b: str) -> Tuple[str, str]:
    return (id_a, id_b) if id_a <= id_b else (id_b, id_a)


def _conflict_already_open(cur: psycopg.Cursor, id_a: str, id_b: str) -> bool:
    id_left, id_right = _ordered_pair(id_a, id_b)
    cur.execute(
        '''
        SELECT 1
        FROM identity_conflicts
        WHERE identity_id_a = %s
          AND identity_id_b = %s
          AND resolved_state = 'open'
        LIMIT 1
        ''',
        (id_left, id_right),
    )
    return cur.fetchone() is not None


def _insert_conflict(
    cur: psycopg.Cursor,
    id_a: str,
    id_b: str,
    confidence_conflict: float,
    reason: str,
) -> None:
    id_left, id_right = _ordered_pair(id_a, id_b)
    cur.execute(
        '''
        INSERT INTO identity_conflicts (
            identity_id_a,
            identity_id_b,
            confidence_conflict,
            reason,
            resolved_state
        )
        VALUES (%s, %s, %s, %s, 'open')
        ''',
        (id_left, id_right, confidence_conflict, reason[:500]),
    )


def _has_open_strong_conflict(subject: str, content_norm: str) -> bool:
    if not subject or not content_norm:
        return False
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT 1
                    FROM identity_conflicts ic
                    JOIN identities ia ON ia.id = ic.identity_id_a
                    JOIN identities ib ON ib.id = ic.identity_id_b
                    WHERE ic.resolved_state = 'open'
                      AND ic.confidence_conflict >= 0.8
                      AND (
                          (ia.subject = %s AND ia.content_norm = %s AND ia.status IN ('accepted', 'deferred'))
                          OR
                          (ib.subject = %s AND ib.content_norm = %s AND ib.status IN ('accepted', 'deferred'))
                      )
                    LIMIT 1
                    ''',
                    (subject, content_norm, subject, content_norm),
                )
                return cur.fetchone() is not None
    except Exception as exc:
        logger.warning('has_open_strong_conflict_error subject=%s err=%s', subject, exc)
        return False


def detect_and_record_conflicts(identity_id: str) -> None:
    if not identity_id:
        return

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id, subject, content, content_norm, status, created_ts, COALESCE(override_state, 'none')
                    FROM identities
                    WHERE id = %s
                    ''',
                    (identity_id,),
                )
                me = cur.fetchone()
                if not me:
                    return

                me_id = str(me[0])
                me_subject = str(me[1] or '')
                me_content = str(me[2] or '')
                me_content_norm = str(me[3] or '')
                me_status = str(me[4] or 'accepted')
                me_created = me[5]
                me_override = str(me[6] or 'none')

                if me_status == 'rejected' or not me_subject or not me_content_norm:
                    return

                cur.execute(
                    '''
                    SELECT id, content, content_norm, status, created_ts, COALESCE(override_state, 'none')
                    FROM identities
                    WHERE subject = %s
                      AND id <> %s::uuid
                      AND status IN ('accepted', 'deferred')
                    ORDER BY created_ts DESC
                    LIMIT 50
                    ''',
                    (me_subject, me_id),
                )
                others = cur.fetchall()

                for other in others:
                    other_id = str(other[0])
                    other_content = str(other[1] or '')
                    other_content_norm = str(other[2] or '')
                    other_status = str(other[3] or 'accepted')
                    other_created = other[4]
                    other_override = str(other[5] or 'none')

                    if not other_content_norm or other_content_norm == me_content_norm:
                        continue

                    if _conflict_already_open(cur, me_id, other_id):
                        continue

                    semantic_similarity = _embedding_similarity_safe(me_content, other_content)
                    contradictory, confidence_conflict, reason = policy.is_contradictory(
                        me_content,
                        other_content,
                        semantic_similarity=semantic_similarity,
                    )
                    if not contradictory:
                        continue

                    _insert_conflict(cur, me_id, other_id, confidence_conflict, reason)

                    action = policy.conflict_resolution_action(confidence_conflict)
                    if action == 'defer_older':
                        # strong conflict: defer older statement by default (unless force_accept)
                        target_id = None
                        if other_created <= me_created and other_override != 'force_accept':
                            target_id = other_id
                        elif me_override != 'force_accept':
                            target_id = me_id
                        elif other_override != 'force_accept':
                            target_id = other_id

                        if target_id:
                            cur.execute(
                                '''
                                UPDATE identities
                                SET
                                    status = 'deferred',
                                    weight = weight * 0.9,
                                    last_reason = %s
                                WHERE id = %s::uuid
                                  AND COALESCE(override_state, 'none') <> 'force_accept'
                                ''',
                                (f'policy:strong_conflict:{reason}'[:500], target_id),
                            )
                    elif action == 'downweight_both':
                        # weak conflict: slight down-weight + flag reason
                        for candidate_id, candidate_override in (
                            (me_id, me_override),
                            (other_id, other_override),
                        ):
                            if candidate_override == 'force_accept':
                                continue
                            cur.execute(
                                '''
                                UPDATE identities
                                SET
                                    weight = weight * 0.9,
                                    last_reason = %s
                                WHERE id = %s::uuid
                                ''',
                                (f'policy:weak_conflict:{reason}'[:500], candidate_id),
                            )

            conn.commit()
    except Exception as exc:
        logger.error('detect_and_record_conflicts_error id=%s err=%s', identity_id, exc)


# Defer policy

def _list_recent_evidence(subject: str, content_norm: str, window_days: int) -> List[Dict[str, Any]]:
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT conversation_id, created_ts, confidence, utterance_mode, status
                    FROM identity_evidence
                    WHERE subject = %s
                      AND content_norm = %s
                      AND created_ts >= (now() - make_interval(days => %s))
                    ORDER BY created_ts ASC
                    ''',
                    (subject, content_norm, max(1, window_days)),
                )
                rows = cur.fetchall()
        return [
            {
                'conversation_id': r[0],
                'created_ts': r[1],
                'confidence': float(r[2] or 0.0),
                'utterance_mode': r[3] or 'unknown',
                'status': r[4] or 'accepted',
            }
            for r in rows
        ]
    except Exception as exc:
        logger.warning('list_recent_evidence_error subject=%s err=%s', subject, exc)
        return []


def _apply_defer_policy_for_content(subject: str, content_norm: str) -> None:
    if not subject or not content_norm:
        return

    events_rows = _list_recent_evidence(subject, content_norm, config.IDENTITY_RECURRENCE_WINDOW_DAYS)
    events = policy.build_evidence_events(events_rows)

    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT id
                    FROM identities
                    WHERE subject = %s
                      AND content_norm = %s
                      AND status = 'deferred'
                    ''',
                    (subject, content_norm),
                )
                deferred_ids = [str(r[0]) for r in cur.fetchall()]
                if not deferred_ids:
                    return

                if policy.should_reject_deferred_from_evidence(events):
                    cur.execute(
                        '''
                        UPDATE identities
                        SET status = 'rejected',
                            last_reason = 'policy:defer_reject_irony_or_roleplay'
                        WHERE subject = %s
                          AND content_norm = %s
                          AND status = 'deferred'
                          AND COALESCE(override_state, 'none') <> 'force_accept'
                        ''',
                        (subject, content_norm),
                    )
                    conn.commit()
                    return

                stats = policy.compute_recurrence_stats(
                    events,
                    min_time_gap_hours=config.IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS,
                )
                has_strong_conflict = _has_open_strong_conflict(subject, content_norm)
                can_promote = policy.should_promote_deferred(
                    stats=stats,
                    min_recurrence_for_durable=config.IDENTITY_MIN_RECURRENCE_FOR_DURABLE,
                    min_distinct_conversations=config.IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS,
                    min_confidence=config.IDENTITY_MIN_CONFIDENCE,
                    has_strong_conflict=has_strong_conflict,
                )

                if can_promote:
                    cur.execute(
                        '''
                        UPDATE identities
                        SET status = 'accepted',
                            last_reason = 'policy:defer_promoted'
                        WHERE subject = %s
                          AND content_norm = %s
                          AND status = 'deferred'
                          AND COALESCE(override_state, 'none') <> 'force_reject'
                        ''',
                        (subject, content_norm),
                    )
                    conn.commit()
                    return

                # Expire deferred when the window elapsed without enough recurrence.
                cur.execute(
                    '''
                    UPDATE identities
                    SET status = 'rejected',
                        last_reason = 'policy:defer_expired_without_recurrence'
                    WHERE subject = %s
                      AND content_norm = %s
                      AND status = 'deferred'
                      AND created_ts < (now() - make_interval(days => %s))
                      AND COALESCE(override_state, 'none') NOT IN ('force_accept', 'force_reject')
                    ''',
                    (
                        subject,
                        content_norm,
                        max(1, config.IDENTITY_RECURRENCE_WINDOW_DAYS),
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger.error('apply_defer_policy_error subject=%s err=%s', subject, exc)


def _expire_stale_deferred_global() -> None:
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    UPDATE identities
                    SET status = 'rejected',
                        last_reason = 'policy:defer_expired_global'
                    WHERE status = 'deferred'
                      AND created_ts < (now() - make_interval(days => %s))
                      AND COALESCE(override_state, 'none') NOT IN ('force_accept', 'force_reject')
                    ''',
                    (max(1, config.IDENTITY_RECURRENCE_WINDOW_DAYS),),
                )
            conn.commit()
    except Exception as exc:
        logger.warning('expire_stale_deferred_global_error err=%s', exc)


def preview_identity_entries(entries: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Evaluate extractor outputs with hermeneutic policy without writing identities."""
    if not entries:
        return []

    processed: List[Dict[str, Any]] = []
    for entry in entries:
        subject = str(entry.get('subject', '')).strip()
        content = str(entry.get('content', '')).strip()
        if subject not in {'user', 'llm'} or not content:
            continue

        decision = policy.should_accept_identity(
            entry,
            min_confidence=config.IDENTITY_MIN_CONFIDENCE,
            defer_min_confidence=config.IDENTITY_DEFER_MIN_CONFIDENCE,
        )
        status = decision['status']
        policy_reason = decision['reason']

        llm_reason = str(entry.get('reason', '')).strip()
        merged_reason = f'llm:{llm_reason} | policy:{policy_reason}' if llm_reason else f'policy:{policy_reason}'

        processed.append(
            {
                'subject': subject,
                'content': content,
                'stability': str(entry.get('stability', 'unknown')),
                'utterance_mode': str(entry.get('utterance_mode', 'unknown')),
                'recurrence': str(entry.get('recurrence', 'unknown')),
                'scope': str(entry.get('scope', 'unknown')),
                'evidence_kind': str(entry.get('evidence_kind', 'weak')),
                'confidence': _trace_float(entry.get('confidence')),
                'status': status,
                'reason': merged_reason,
            }
        )

    return processed


def persist_identity_entries(
    conversation_id: str,
    entries: List[Dict[str, Any]],
    source_trace_id: Optional[str] = None,
) -> None:
    """Persist extractor outputs into evidence + identities with defer/promote/reject policy."""
    processed = preview_identity_entries(entries)
    if not processed:
        return

    record_identity_evidence(conversation_id, processed, source_trace_id=source_trace_id)

    impacted_keys: set[Tuple[str, str]] = set()

    for entry in processed:
        identity_id = add_identity(
            entry['subject'],
            entry['content'],
            source_trace_id=source_trace_id,
            conversation_id=conversation_id,
            stability=entry['stability'],
            utterance_mode=entry['utterance_mode'],
            recurrence=entry['recurrence'],
            scope=entry['scope'],
            evidence_kind=entry['evidence_kind'],
            confidence=entry['confidence'],
            status=entry['status'],
            reason=entry['reason'],
        )
        if identity_id:
            detect_and_record_conflicts(identity_id)

        impacted_keys.add((entry['subject'], _normalize_identity_content(entry['content'])))

    for subject, content_norm in impacted_keys:
        _apply_defer_policy_for_content(subject, content_norm)

    _expire_stale_deferred_global()


# Identity dynamics

def decay_identities() -> None:
    """Apply decay factor to all identity entries."""
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE identities SET weight = weight * %s WHERE weight > 0.01',
                    (config.IDENTITY_DECAY_FACTOR,),
                )
            conn.commit()
        logger.debug('identity_decay_applied factor=%s', config.IDENTITY_DECAY_FACTOR)
    except Exception as exc:
        logger.error('decay_identities_error err=%s', exc)


def reactivate_identities(identity_ids: List[str]) -> None:
    """Boost weights for identity entries actually injected in prompt."""
    if not identity_ids:
        return
    try:
        with _conn() as conn:
            with conn.cursor() as cur:
                for iid in identity_ids:
                    cur.execute(
                        '''
                        UPDATE identities
                        SET    weight       = LEAST(weight * 1.1, 2.0),
                               last_seen_ts = now()
                        WHERE  id = %s
                        ''',
                        (iid,),
                    )
            conn.commit()
    except Exception as exc:
        logger.error('reactivate_identities_error err=%s', exc)
