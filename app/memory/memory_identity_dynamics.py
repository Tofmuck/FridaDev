from __future__ import annotations

import math
from typing import Any, Callable, Sequence

from observability import chat_turn_logger


def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return max(0.0, min(1.0, dot / (norm_a * norm_b)))


def _embedding_similarity_safe(
    text_a: str,
    text_b: str,
    *,
    embed_fn: Callable[..., list[float]],
    cosine_similarity_fn: Callable[[Sequence[float], Sequence[float]], float],
    logger: Any,
) -> float | None:
    try:
        vec_a = embed_fn(text_a, mode='passage')
        vec_b = embed_fn(text_b, mode='passage')
        return cosine_similarity_fn(vec_a, vec_b)
    except Exception as exc:
        logger.warning('conflict_embedding_similarity_error err=%s', exc)
        return None


def _ordered_pair(id_a: str, id_b: str) -> tuple[str, str]:
    return (id_a, id_b) if id_a <= id_b else (id_b, id_a)


def _conflict_already_open(
    cur: Any,
    id_a: str,
    id_b: str,
    *,
    ordered_pair_fn: Callable[[str, str], tuple[str, str]],
) -> bool:
    id_left, id_right = ordered_pair_fn(id_a, id_b)
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
    cur: Any,
    id_a: str,
    id_b: str,
    confidence_conflict: float,
    reason: str,
    *,
    ordered_pair_fn: Callable[[str, str], tuple[str, str]],
) -> None:
    id_left, id_right = ordered_pair_fn(id_a, id_b)
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


def _has_open_strong_conflict(
    subject: str,
    content_norm: str,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> bool:
    if not subject or not content_norm:
        return False
    try:
        with conn_factory() as conn:
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


def detect_and_record_conflicts(
    identity_id: str,
    *,
    conn_factory: Callable[[], Any],
    policy_module: Any,
    logger: Any,
    conflict_already_open_fn: Callable[[Any, str, str], bool],
    embedding_similarity_safe_fn: Callable[[str, str], float | None],
    insert_conflict_fn: Callable[[Any, str, str, float, str], None],
) -> None:
    if not identity_id:
        return

    try:
        with conn_factory() as conn:
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
                    other_created = other[4]
                    other_override = str(other[5] or 'none')

                    if not other_content_norm or other_content_norm == me_content_norm:
                        continue

                    if conflict_already_open_fn(cur, me_id, other_id):
                        continue

                    semantic_similarity = embedding_similarity_safe_fn(me_content, other_content)
                    contradictory, confidence_conflict, reason = policy_module.is_contradictory(
                        me_content,
                        other_content,
                        semantic_similarity=semantic_similarity,
                    )
                    if not contradictory:
                        continue

                    insert_conflict_fn(cur, me_id, other_id, confidence_conflict, reason)

                    action = policy_module.conflict_resolution_action(confidence_conflict)
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


def _list_recent_evidence(
    subject: str,
    content_norm: str,
    window_days: int,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> list[dict[str, Any]]:
    try:
        with conn_factory() as conn:
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


def _apply_defer_policy_for_content(
    subject: str,
    content_norm: str,
    *,
    conn_factory: Callable[[], Any],
    policy_module: Any,
    config_module: Any,
    logger: Any,
    list_recent_evidence_fn: Callable[[str, str, int], list[dict[str, Any]]],
    has_open_strong_conflict_fn: Callable[[str, str], bool],
) -> None:
    if not subject or not content_norm:
        return

    events_rows = list_recent_evidence_fn(subject, content_norm, config_module.IDENTITY_RECURRENCE_WINDOW_DAYS)
    events = policy_module.build_evidence_events(events_rows)

    try:
        with conn_factory() as conn:
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

                if policy_module.should_reject_deferred_from_evidence(events):
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

                stats = policy_module.compute_recurrence_stats(
                    events,
                    min_time_gap_hours=config_module.IDENTITY_PROMOTION_MIN_TIME_GAP_HOURS,
                )
                has_strong_conflict = has_open_strong_conflict_fn(subject, content_norm)
                can_promote = policy_module.should_promote_deferred(
                    stats=stats,
                    min_recurrence_for_durable=config_module.IDENTITY_MIN_RECURRENCE_FOR_DURABLE,
                    min_distinct_conversations=config_module.IDENTITY_PROMOTION_MIN_DISTINCT_CONVERSATIONS,
                    min_confidence=config_module.IDENTITY_MIN_CONFIDENCE,
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
                        max(1, config_module.IDENTITY_RECURRENCE_WINDOW_DAYS),
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger.error('apply_defer_policy_error subject=%s err=%s', subject, exc)


def _expire_stale_deferred_global(
    *,
    conn_factory: Callable[[], Any],
    config_module: Any,
    logger: Any,
) -> None:
    try:
        with conn_factory() as conn:
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
                    (max(1, config_module.IDENTITY_RECURRENCE_WINDOW_DAYS),),
                )
            conn.commit()
    except Exception as exc:
        logger.warning('expire_stale_deferred_global_error err=%s', exc)


def preview_identity_entries(
    entries: list[dict[str, Any]],
    *,
    policy_module: Any,
    config_module: Any,
    trace_float_fn: Callable[[Any], float],
) -> list[dict[str, Any]]:
    """Evaluate extractor outputs with hermeneutic policy without writing identities."""
    if not entries:
        return []

    processed: list[dict[str, Any]] = []
    for entry in entries:
        subject = str(entry.get('subject', '')).strip()
        content = str(entry.get('content', '')).strip()
        if subject not in {'user', 'llm'} or not content:
            continue

        decision = policy_module.should_accept_identity(
            entry,
            min_confidence=config_module.IDENTITY_MIN_CONFIDENCE,
            defer_min_confidence=config_module.IDENTITY_DEFER_MIN_CONFIDENCE,
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
                'confidence': trace_float_fn(entry.get('confidence')),
                'status': status,
                'reason': merged_reason,
            }
        )

    return processed


def persist_identity_entries(
    conversation_id: str,
    entries: list[dict[str, Any]],
    source_trace_id: str | None = None,
    *,
    preview_identity_entries_fn: Callable[[list[dict[str, Any]]], list[dict[str, Any]]],
    record_identity_evidence_fn: Callable[[str, list[dict[str, Any]], str | None], None],
    add_identity_fn: Callable[..., str | None],
    detect_and_record_conflicts_fn: Callable[[str], None],
    normalize_identity_content_fn: Callable[[str], str],
    apply_defer_policy_for_content_fn: Callable[[str, str], None],
    expire_stale_deferred_global_fn: Callable[[], None],
) -> None:
    """Persist extractor outputs into evidence + identities with defer/promote/reject policy."""
    processed = preview_identity_entries_fn(entries)
    if not processed:
        chat_turn_logger.emit(
            'identity_write',
            status='skipped',
            reason_code='no_data',
            payload={
                'target_side': 'frida',
                'retained_count': 0,
                'actions_count': {'add': 0, 'update': 0, 'override': 0, 'reject': 0, 'defer': 0},
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code='no_data',
            reason_short='identity_write_no_entries',
        )
        return

    record_identity_evidence_fn(conversation_id, processed, source_trace_id)

    impacted_keys: set[tuple[str, str]] = set()
    side_counters: dict[str, dict[str, Any]] = {
        'frida': {'retained_count': 0, 'actions_count': {'add': 0, 'update': 0, 'override': 0, 'reject': 0, 'defer': 0}, 'preview': []},
        'user': {'retained_count': 0, 'actions_count': {'add': 0, 'update': 0, 'override': 0, 'reject': 0, 'defer': 0}, 'preview': []},
    }

    for entry in processed:
        side = 'frida' if str(entry.get('subject') or '') == 'llm' else 'user'
        identity_id = add_identity_fn(
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
            detect_and_record_conflicts_fn(identity_id)

        impacted_keys.add((entry['subject'], normalize_identity_content_fn(entry['content'])))

        status = str(entry.get('status') or 'accepted')
        if status == 'accepted':
            side_counters[side]['actions_count']['add'] += 1
            side_counters[side]['retained_count'] += 1
        elif status == 'deferred':
            side_counters[side]['actions_count']['defer'] += 1
            side_counters[side]['retained_count'] += 1
        elif status == 'rejected':
            side_counters[side]['actions_count']['reject'] += 1
        else:
            side_counters[side]['actions_count']['update'] += 1
            side_counters[side]['retained_count'] += 1

        if len(side_counters[side]['preview']) < 3:
            side_counters[side]['preview'].append(str(entry.get('content') or ''))

    for subject, content_norm in impacted_keys:
        apply_defer_policy_for_content_fn(subject, content_norm)

    expire_stale_deferred_global_fn()

    for side, summary in side_counters.items():
        has_activity = summary['retained_count'] > 0 or any(int(count) > 0 for count in summary['actions_count'].values())
        if not has_activity:
            continue
        chat_turn_logger.emit(
            'identity_write',
            status='ok',
            payload={
                'target_side': side,
                'retained_count': int(summary['retained_count']),
                'actions_count': dict(summary['actions_count']),
                'preview': list(summary['preview']),
                'truncated': len(summary['preview']) >= 3 and len(processed) > 3,
            },
        )


def decay_identities(
    *,
    conn_factory: Callable[[], Any],
    decay_factor: float,
    logger: Any,
) -> None:
    """Apply decay factor to all identity entries."""
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    'UPDATE identities SET weight = weight * %s WHERE weight > 0.01',
                    (decay_factor,),
                )
            conn.commit()
        logger.debug('identity_decay_applied factor=%s', decay_factor)
    except Exception as exc:
        logger.error('decay_identities_error err=%s', exc)


def reactivate_identities(
    identity_ids: list[str],
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> None:
    """Boost weights for identity entries actually injected in prompt."""
    if not identity_ids:
        return
    try:
        with conn_factory() as conn:
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
