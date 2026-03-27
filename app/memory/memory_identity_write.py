from __future__ import annotations

from typing import Any, Callable


def set_identity_override(
    identity_id: str,
    override_state: str,
    *,
    reason: str = '',
    actor: str = 'admin',
    conn_factory: Callable[[], Any],
    logger: Any,
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
        with conn_factory() as conn:
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
    stability: str | None = None,
    utterance_mode: str | None = None,
    scope: str | None = None,
    reason: str = '',
    actor: str = 'admin',
    conn_factory: Callable[[], Any],
    logger: Any,
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

    fields: list[str] = []
    values: list[Any] = []

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
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(query, tuple(values))
                updated = cur.rowcount > 0
            conn.commit()
        return updated
    except Exception as exc:
        logger.error('relabel_identity_error id=%s err=%s', identity_id, exc)
        return False


def record_identity_evidence(
    conversation_id: str,
    entries: list[dict[str, Any]],
    source_trace_id: str | None = None,
    *,
    conn_factory: Callable[[], Any],
    normalize_identity_content_fn: Callable[[str], str],
    trace_float_fn: Callable[[Any], float],
    logger: Any,
) -> None:
    if not entries:
        return

    try:
        with conn_factory() as conn:
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
                            normalize_identity_content_fn(content),
                            str(entry.get('stability', 'unknown')),
                            str(entry.get('utterance_mode', 'unknown')),
                            str(entry.get('recurrence', 'unknown')),
                            str(entry.get('scope', 'unknown')),
                            str(entry.get('evidence_kind', 'weak')),
                            trace_float_fn(entry.get('confidence')),
                            str(entry.get('status', 'accepted')),
                            str(entry.get('reason', ''))[:500],
                            source_trace_id,
                        ),
                    )
            conn.commit()
        logger.info('identity_evidence_saved conv=%s count=%s', conversation_id, len(entries))
    except Exception as exc:
        logger.error('record_identity_evidence_error conv=%s err=%s', conversation_id, exc)


def add_identity(
    subject: str,
    content: str,
    source_trace_id: str | None = None,
    conversation_id: str | None = None,
    *,
    stability: str = 'unknown',
    utterance_mode: str = 'unknown',
    recurrence: str = 'unknown',
    scope: str = 'unknown',
    evidence_kind: str = 'weak',
    confidence: float = 0.0,
    status: str = 'accepted',
    reason: str = '',
    conn_factory: Callable[[], Any],
    normalize_identity_content_fn: Callable[[str], str],
    trace_float_fn: Callable[[Any], float],
    logger: Any,
) -> str | None:
    """Insert or update a normalized identity entry with metadata."""
    subject = str(subject or '').strip()
    content = str(content or '').strip()
    if subject not in {'user', 'llm'} or not content:
        return None

    content_norm = normalize_identity_content_fn(content)
    confidence_f = trace_float_fn(confidence)

    try:
        with conn_factory() as conn:
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
