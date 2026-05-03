from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable


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


def _reason_key(reason: Any, *, max_chars: int = 72) -> str:
    raw = ' '.join(str(reason or '').split())
    if not raw:
        return 'unspecified'
    compact = raw.split('|', 1)[0].strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + '...'


def _compact_excerpt(text: Any, *, max_chars: int = 140) -> str:
    raw = ' '.join(str(text or '').split())
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 3].rstrip() + '...'


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
                LIMIT 5
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
            'top_rejection_reasons': {
                _reason_key(row[0]): _to_int(row[1])
                for row in rejection_rows
            },
        },
    }


def _read_arbiter_persisted_preview(
    *,
    memory_store_module: Any,
    limit: int,
) -> dict[str, Any]:
    items = memory_store_module.get_arbiter_decisions(limit=limit)
    return {
        'source_kind': 'durable_persistence',
        'items': items,
        'count': len(items),
    }
