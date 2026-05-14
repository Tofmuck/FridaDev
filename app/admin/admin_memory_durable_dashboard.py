from __future__ import annotations

from datetime import datetime, timezone
import hashlib
from typing import Any, Callable

from observability.memory_arbiter_reason_codes import (
    compact_arbiter_reason_observability,
    compact_reason_code_counts_from_mapping,
)


def _to_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _utc_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    text = str(value or '').strip()
    return text or None


def _compact_excerpt(text: Any, *, max_chars: int = 140) -> str:
    raw = ' '.join(str(text or '').split())
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 3].rstrip() + '...'


def _text(value: Any) -> str:
    return str(value or '').strip()


def _sha256_12(value: Any) -> str:
    text = _text(value)
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _compact_arbiter_preview_item(item: Any) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {}
    candidate_content = _text(payload.get('candidate_content'))
    reason = _text(payload.get('reason'))
    return {
        'id': _text(payload.get('id')),
        'conversation_id': _text(payload.get('conversation_id')),
        'candidate_id': _text(payload.get('candidate_id')),
        'candidate_role': payload.get('candidate_role'),
        'candidate_ts': payload.get('candidate_ts'),
        'candidate_score': payload.get('candidate_score'),
        'candidate_content_chars': len(candidate_content),
        'candidate_content_sha256_12': _sha256_12(candidate_content),
        'keep': bool(payload.get('keep')),
        'semantic_relevance': payload.get('semantic_relevance'),
        'contextual_gain': payload.get('contextual_gain'),
        'redundant_with_recent': bool(payload.get('redundant_with_recent')),
        **compact_arbiter_reason_observability(reason),
        'model': payload.get('model'),
        'decision_source': payload.get('decision_source'),
        'created_ts': payload.get('created_ts'),
    }


def _read_durable_state(
    *,
    conn_factory: Callable[[], Any],
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS with_embedding,
                    COUNT(*) FILTER (WHERE summary_id IS NOT NULL)::int AS with_summary_id,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    COUNT(*) FILTER (WHERE role = 'user')::int AS user_count,
                    COUNT(*) FILTER (WHERE role = 'assistant')::int AS assistant_count,
                    COUNT(*) FILTER (WHERE role = 'summary')::int AS summary_count,
                    MAX(timestamp) AS latest_ts
                FROM traces
                '''
            )
            traces_row = cur.fetchone() or (0, 0, 0, 0, 0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS with_embedding,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    MAX(end_ts) AS latest_ts
                FROM summaries
                '''
            )
            summaries_row = cur.fetchone() or (0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE keep)::int AS kept_count,
                    COUNT(*) FILTER (WHERE NOT keep)::int AS rejected_count,
                    COUNT(*) FILTER (WHERE decision_source = 'fallback')::int AS fallback_count,
                    COUNT(*) FILTER (WHERE decision_source = 'llm')::int AS llm_count,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    MAX(created_ts) AS latest_ts
                FROM arbiter_decisions
                '''
            )
            arbiter_row = cur.fetchone() or (0, 0, 0, 0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    role,
                    lower(regexp_replace(trim(content), '\\s+', ' ', 'g')) AS normalized_content,
                    COUNT(*)::int AS occurrences
                FROM traces
                WHERE trim(content) <> ''
                GROUP BY role, lower(regexp_replace(trim(content), '\\s+', ' ', 'g'))
                HAVING COUNT(*) > 1
                ORDER BY occurrences DESC, normalized_content ASC
                LIMIT 5
                '''
            )
            duplicate_rows = cur.fetchall()

            cur.execute(
                '''
                SELECT reason, COUNT(*)::int AS occurrences
                FROM arbiter_decisions
                WHERE NOT keep
                GROUP BY reason
                ORDER BY COUNT(*) DESC, reason ASC
                '''
            )
            rejection_rows = cur.fetchall()

    return {
        'source_kind': 'durable_persistence',
        'traces': {
            'total': _to_int(traces_row[0]),
            'with_embedding': _to_int(traces_row[1]),
            'with_summary_id': _to_int(traces_row[2]),
            'conversations': _to_int(traces_row[3]),
            'by_role': {
                'user': _to_int(traces_row[4]),
                'assistant': _to_int(traces_row[5]),
                'summary': _to_int(traces_row[6]),
            },
            'latest_ts': _utc_iso(traces_row[7]),
            'duplicate_examples': [
                {
                    'role': str(row[0] or ''),
                    'occurrences': _to_int(row[2]),
                    'content_excerpt': _compact_excerpt(row[1]),
                }
                for row in duplicate_rows
            ],
        },
        'summaries': {
            'total': _to_int(summaries_row[0]),
            'with_embedding': _to_int(summaries_row[1]),
            'conversations': _to_int(summaries_row[2]),
            'latest_ts': _utc_iso(summaries_row[3]),
        },
        'arbiter_decisions': {
            'total': _to_int(arbiter_row[0]),
            'kept_count': _to_int(arbiter_row[1]),
            'rejected_count': _to_int(arbiter_row[2]),
            'fallback_count': _to_int(arbiter_row[3]),
            'llm_count': _to_int(arbiter_row[4]),
            'conversations': _to_int(arbiter_row[5]),
            'latest_ts': _utc_iso(arbiter_row[6]),
            'top_rejection_reason_code_counts': compact_reason_code_counts_from_mapping({
                str(row[0] or ''): _to_int(row[1])
                for row in rejection_rows
            }),
        },
    }


def _read_arbiter_persisted_preview(
    *,
    memory_store_module: Any,
    limit: int,
) -> dict[str, Any]:
    items = memory_store_module.get_arbiter_decisions(limit=limit)
    compact_items = [_compact_arbiter_preview_item(item) for item in items]
    return {
        'source_kind': 'durable_persistence',
        'items': compact_items,
        'count': len(compact_items),
    }
