from __future__ import annotations

from typing import Any, Callable


def get_hermeneutic_kpis(
    window_days: int = 7,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    window_days = max(1, min(int(window_days), 365))
    out: dict[str, Any] = {
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
        with conn_factory() as conn:
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
    conversation_id: str | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    limit = max(1, min(int(limit), 1000))
    try:
        with conn_factory() as conn:
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


def record_arbiter_decisions(
    conversation_id: str,
    traces: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    *,
    effective_model: str | None = None,
    conn_factory: Callable[[], Any],
    trace_float_fn: Callable[[Any], float],
    logger: Any,
) -> None:
    if not conversation_id or not decisions:
        return

    try:
        fallback_arbiter_model = str(effective_model or '').strip() or None
        with conn_factory() as conn:
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
                            trace_float_fn(trace.get('score')),
                            bool(decision.get('keep', False)),
                            trace_float_fn(decision.get('semantic_relevance')),
                            trace_float_fn(decision.get('contextual_gain')),
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
