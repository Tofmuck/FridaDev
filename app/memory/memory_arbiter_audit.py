from __future__ import annotations

from typing import Any, Callable

from observability import chat_turn_logger


def _compact_reason_key(reason: Any, *, max_chars: int = 72) -> str:
    text = str(reason or '').strip()
    if not text:
        return 'unspecified'
    primary = text.split('|', 1)[0].strip()
    normalized = ' '.join(primary.split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 3].rstrip() + '...'


def _rejection_reason_counts(decisions: list[dict[str, Any]], *, limit: int = 5) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        if bool(decision.get('keep', False)):
            continue
        key = _compact_reason_key(decision.get('reason'))
        counts[key] = counts.get(key, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in ordered[:limit]}


def _decision_source_counts(decisions: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for decision in decisions:
        source = str(decision.get('decision_source') or '').strip().lower() or 'unknown'
        counts[source] = counts.get(source, 0) + 1
    ordered = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    return {key: value for key, value in ordered}


def _resolve_arbiter_model(
    decisions: list[dict[str, Any]],
    *,
    effective_model: str | None,
) -> str:
    fallback_model = str(effective_model or '').strip()
    if fallback_model:
        return fallback_model
    for decision in decisions:
        candidate_model = str(decision.get('model') or '').strip()
        if candidate_model:
            return candidate_model
    return 'unknown'


def _resolve_decision_source(decision_source_counts: dict[str, int]) -> str:
    if not decision_source_counts:
        return 'unknown'
    if len(decision_source_counts) == 1:
        return next(iter(decision_source_counts.keys()))
    return 'mixed'


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
    mode: str | None = None,
    conn_factory: Callable[[], Any],
    trace_float_fn: Callable[[Any], float],
    logger: Any,
) -> None:
    if not conversation_id or not decisions:
        return

    arbiter_model = _resolve_arbiter_model(decisions, effective_model=effective_model)
    kept_candidates = sum(1 for decision in decisions if bool(decision.get('keep', False)))
    rejected_candidates = max(0, len(traces) - kept_candidates)
    decision_source_counts = _decision_source_counts(decisions)
    decision_source = _resolve_decision_source(decision_source_counts)
    fallback_decisions = int(decision_source_counts.get('fallback', 0))
    rejection_reason_counts = _rejection_reason_counts(decisions)

    try:
        fallback_arbiter_model = arbiter_model if arbiter_model != 'unknown' else None
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
        payload: dict[str, Any] = {
            'raw_candidates': len(traces),
            'kept_candidates': kept_candidates,
            'rejected_candidates': rejected_candidates,
            'mode': str(mode or 'unknown'),
            'model': arbiter_model,
            'decision_source': decision_source,
            'fallback_used': bool(fallback_decisions > 0),
        }
        if rejection_reason_counts:
            payload['rejection_reason_counts'] = rejection_reason_counts
        if fallback_decisions > 0:
            payload['fallback_decisions'] = fallback_decisions

        chat_turn_logger.emit(
            'arbiter',
            status='ok',
            payload=payload,
        )
        logger.info('arbiter_decisions_saved conv=%s count=%s', conversation_id, len(decisions))
    except Exception as exc:
        chat_turn_logger.emit(
            'arbiter',
            status='error',
            error_code='upstream_error',
            payload={
                'raw_candidates': len(traces),
                'kept_candidates': 0,
                'rejected_candidates': len(traces),
                'mode': str(mode or 'unknown'),
                'model': arbiter_model,
                'decision_source': decision_source,
                'fallback_used': bool(fallback_decisions > 0),
                'error_class': exc.__class__.__name__,
            },
        )
        logger.error('record_arbiter_decisions_error conv=%s err=%s', conversation_id, exc)
