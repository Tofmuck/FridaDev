from __future__ import annotations

from datetime import datetime
from typing import Any, Callable

from observability import chat_turn_logger


def _preview_items(values: list[str], *, max_items: int = 3, max_chars: int = 120) -> tuple[list[str], bool]:
    preview: list[str] = []
    for value in values[:max_items]:
        text = str(value or '').strip().replace('\n', ' ')
        if len(text) > max_chars:
            text = text[: max_chars - 1].rstrip() + '…'
        preview.append(text)
    return preview, len(values) > max_items


def get_identities(
    subject: str,
    top_n: int | None = None,
    status: str | None = 'accepted',
    *,
    conn_factory: Callable[[], Any],
    default_top_n: int,
    logger: Any,
) -> list[dict[str, Any]]:
    """
    Return top-N identities for a subject, sorted by weight.
    By default, only accepted identities are returned.
    """
    if top_n is None:
        top_n = default_top_n
    try:
        with conn_factory() as conn:
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
        out = [
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
        if chat_turn_logger.is_active():
            side = 'frida' if str(subject) == 'llm' else 'user'
            keys, keys_truncated = _preview_items([entry['id'] for entry in out], max_chars=64)
            previews, previews_truncated = _preview_items([entry['content'] for entry in out])
            selected_count = len(out)
            requested_top_n = max(0, int(top_n))
            chat_turn_logger.emit(
                'identities_read',
                status='ok',
                payload={
                    'target_side': side,
                    'frida_count': selected_count if side == 'frida' else 0,
                    'user_count': selected_count if side == 'user' else 0,
                    'selected_count': selected_count,
                    'truncated': bool(
                        selected_count >= requested_top_n
                        or keys_truncated
                        or previews_truncated
                    ),
                    'keys': keys,
                    'preview': previews,
                },
            )
        return out
    except Exception as exc:
        chat_turn_logger.emit(
            'identities_read',
            status='error',
            error_code='upstream_error',
            payload={
                'target_side': 'frida' if str(subject) == 'llm' else 'user',
                'frida_count': 0,
                'user_count': 0,
                'selected_count': 0,
                'error_class': exc.__class__.__name__,
            },
        )
        logger.error('get_identities_error subject=%s err=%s', subject, exc)
        return []


def get_recent_context_hints(
    max_items: int | None = None,
    max_age_days: int | None = None,
    min_confidence: float | None = None,
    *,
    conn_factory: Callable[[], Any],
    default_max_items: int,
    default_max_age_days: int,
    default_min_confidence: float,
    logger: Any,
) -> list[dict[str, Any]]:
    """
    Return non-durable context hints from recent episodic/situation evidence.
    This reads evidence only and never promotes content into durable identity.
    """
    if max_items is None:
        max_items = default_max_items
    if max_age_days is None:
        max_age_days = default_max_age_days
    if min_confidence is None:
        min_confidence = default_min_confidence

    max_items = max(0, int(max_items))
    if max_items == 0:
        return []

    fetch_limit = max(5, max_items * 8)

    try:
        with conn_factory() as conn:
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

        hints: list[dict[str, Any]] = []
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

        if chat_turn_logger.is_active():
            previews, previews_truncated = _preview_items([hint['content'] for hint in hints])
            keys, keys_truncated = _preview_items([hint['conversation_id'] for hint in hints], max_chars=64)
            chat_turn_logger.emit(
                'identities_read',
                status='ok',
                payload={
                    'target_side': 'user',
                    'frida_count': 0,
                    'user_count': len(hints),
                    'selected_count': len(hints),
                    'truncated': bool(
                        len(hints) >= max_items
                        or previews_truncated
                        or keys_truncated
                    ),
                    'keys': keys,
                    'preview': previews,
                },
            )
        return hints
    except Exception as exc:
        chat_turn_logger.emit(
            'identities_read',
            status='error',
            error_code='upstream_error',
            payload={
                'target_side': 'user',
                'frida_count': 0,
                'user_count': 0,
                'selected_count': 0,
                'error_class': exc.__class__.__name__,
            },
        )
        logger.error("get_recent_context_hints_error err=%s", exc)
        return []
