from __future__ import annotations

from typing import Any, Callable

from core import assistant_turn_state


def message_is_trace_eligible(message: dict[str, Any]) -> bool:
    role = str(message.get('role') or '').strip()
    if role not in {'user', 'assistant'}:
        return False
    if message.get('embedded'):
        return False
    if not str(message.get('content') or '').strip():
        return False
    if role == 'assistant':
        if assistant_turn_state.is_interrupted_assistant_turn(message):
            return False
        if assistant_turn_state.is_dialogic_presence_assistant_turn(message):
            return False
    return True


def trace_exists_for_message(
    conversation_id: str,
    message: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> bool:
    role = str(message.get('role') or '').strip()
    content = str(message.get('content') or '')
    timestamp = message.get('timestamp')
    if not conversation_id or not role or not content:
        return False

    try:
        with conn_factory() as conn:
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


def save_new_traces(
    conversation: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
    message_is_trace_eligible_fn: Callable[[dict[str, Any]], bool],
    trace_exists_for_message_fn: Callable[..., bool],
    embed_with_purpose_fn: Callable[..., list[float]],
) -> None:
    """
    Embed and persist user/assistant messages not yet marked as embedded.
    Never raises: conversation save must not depend on this.
    """
    conv_id = conversation.get('id', '')
    to_embed = [
        message
        for message in conversation.get('messages', [])
        if message_is_trace_eligible_fn(message)
    ]
    if not to_embed:
        return

    for message in to_embed:
        if trace_exists_for_message_fn(
            conv_id,
            message,
            conn_factory=conn_factory,
            logger=logger,
        ):
            message['embedded'] = True
            logger.info(
                'trace_exists_skip conv=%s role=%s ts=%s',
                conv_id,
                message.get('role'),
                message.get('timestamp'),
            )
            continue

        try:
            purpose = 'trace_user' if str(message.get('role')) == 'user' else 'trace_assistant'
            vec = embed_with_purpose_fn(
                embed_fn,
                message['content'],
                mode='passage',
                purpose=purpose,
            )
        except Exception as exc:
            logger.warning('embed_skip role=%s err=%s', message.get('role'), exc)
            vec = None

        try:
            with conn_factory() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        '''
                        INSERT INTO traces
                            (conversation_id, role, content, timestamp, embedding, summary_id)
                        VALUES (%s, %s, %s, %s, %s::vector, %s)
                        ''',
                        (
                            conv_id,
                            message['role'],
                            message['content'],
                            message.get('timestamp'),
                            str(vec) if vec is not None else None,
                            message.get('summarized_by'),
                        ),
                    )
                conn.commit()
            message['embedded'] = True
        except Exception as exc:
            logger.error('save_trace_error conv=%s err=%s', conv_id, exc)


def save_summary(
    conversation_id: str,
    summary: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
    embed_with_purpose_fn: Callable[..., list[float]],
) -> bool:
    """
    Persist a summary into `summaries`.
    Embedding failure does not prevent text persistence.
    Return True only after the text write commits, False when it fails.
    """
    content = summary.get('content', '')
    try:
        vec = embed_with_purpose_fn(
            embed_fn,
            content,
            mode='passage',
            purpose='summary',
        )
    except Exception as exc:
        logger.warning('summary_embed_skip err=%s', exc)
        vec = None

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO summaries
                        (id, conversation_id, start_ts, end_ts, content, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s::vector)
                    ON CONFLICT (id) DO NOTHING
                    RETURNING id
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
                inserted = cur.fetchone()
                if inserted is None:
                    cur.execute(
                        '''
                        SELECT 1
                        FROM summaries
                        WHERE id = %s
                          AND conversation_id = %s
                          AND start_ts IS NOT DISTINCT FROM %s::timestamptz
                          AND end_ts IS NOT DISTINCT FROM %s::timestamptz
                          AND content = %s
                        ''',
                        (
                            summary['id'],
                            conversation_id,
                            summary.get('start_ts') or None,
                            summary.get('end_ts') or None,
                            content,
                        ),
                    )
                    if cur.fetchone() is None:
                        logger.error(
                            'save_summary_conflict_mismatch conv=%s summary_id=%s',
                            conversation_id,
                            summary['id'][:8],
                        )
                        return False
            conn.commit()
        logger.info('summary_saved conv=%s summary_id=%s', conversation_id, summary['id'][:8])
        return True
    except Exception as exc:
        logger.error('save_summary_error conv=%s err=%s', conversation_id, exc)
        return False


def update_traces_summary_id(
    conversation_id: str,
    summary_id: str,
    start_ts: str | None,
    end_ts: str | None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> None:
    """Set summary_id on uncovered traces inside the summary time interval."""
    if not start_ts or not end_ts:
        return
    try:
        with conn_factory() as conn:
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


def get_summary_for_trace(
    trace: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> dict[str, Any] | None:
    """Return the parent summary by explicit id or conversation time overlap."""
    if str(trace.get('source_kind') or '') == 'summary' or str(trace.get('role') or '') == 'summary':
        return None
    summary_id = trace.get('summary_id')
    conv_id = trace.get('conversation_id')
    ts = trace.get('timestamp')

    try:
        with conn_factory() as conn:
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


def enrich_traces_with_summaries(
    traces: list[dict[str, Any]],
    *,
    get_summary_for_trace_fn: Callable[[dict[str, Any]], dict[str, Any] | None],
) -> list[dict[str, Any]]:
    """Attach parent summaries with a per-call cache for repeated summary keys."""
    cache: dict[str, dict[str, Any] | None] = {}
    for trace in traces:
        if str(trace.get('source_kind') or '') == 'summary' or str(trace.get('role') or '') == 'summary':
            trace['parent_summary'] = None
            continue
        summary_id = trace.get('summary_id')
        cache_key = summary_id or f"{trace.get('conversation_id')}@{trace.get('timestamp')}"
        if cache_key not in cache:
            cache[cache_key] = get_summary_for_trace_fn(trace)
        trace['parent_summary'] = cache[cache_key]
    return traces
