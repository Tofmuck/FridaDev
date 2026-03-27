from __future__ import annotations

from typing import Any, Callable


def _trace_exists_for_message(
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
) -> None:
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
        if _trace_exists_for_message(
            conv_id,
            m,
            conn_factory=conn_factory,
            logger=logger,
        ):
            m['embedded'] = True
            logger.info(
                'trace_exists_skip conv=%s role=%s ts=%s',
                conv_id,
                m.get('role'),
                m.get('timestamp'),
            )
            continue

        try:
            vec = embed_fn(m['content'], mode='passage')
        except Exception as exc:
            logger.warning('embed_skip role=%s err=%s', m.get('role'), exc)
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


def retrieve(
    query: str,
    top_k: int | None = None,
    *,
    runtime_embedding_value_fn: Callable[[str], Any],
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> list[dict[str, Any]]:
    """
    Embed query and return top_k nearest traces (cosine similarity).
    Return [] on error to avoid blocking response pipeline.
    """
    if top_k is None:
        top_k = int(runtime_embedding_value_fn('top_k'))

    try:
        q_vec = embed_fn(query, mode='query')
    except Exception as exc:
        logger.warning('retrieve_embed_failed err=%s', exc)
        return []

    try:
        with conn_factory() as conn:
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


def save_summary(
    conversation_id: str,
    summary: dict[str, Any],
    *,
    conn_factory: Callable[[], Any],
    embed_fn: Callable[..., list[float]],
    logger: Any,
) -> None:
    """
    Persist a summary into `summaries`.
    Embedding failure does not prevent text persistence.
    """
    content = summary.get('content', '')
    try:
        vec = embed_fn(content, mode='passage')
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


def update_traces_summary_id(
    conversation_id: str,
    summary_id: str,
    start_ts: str | None,
    end_ts: str | None,
    *,
    conn_factory: Callable[[], Any],
    logger: Any,
) -> None:
    """
    Set summary_id on traces covered by [start_ts, end_ts] where summary_id is still NULL.
    """
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
    """
    Return parent summary for a trace:
    - by summary_id when available,
    - otherwise by time overlap on same conversation_id.
    """
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
    """
    Add trace['parent_summary'] for each trace with internal cache to avoid redundant DB calls.
    """
    cache: dict[str, dict[str, Any] | None] = {}
    for trace in traces:
        summary_id = trace.get('summary_id')
        cache_key = summary_id or f"{trace.get('conversation_id')}@{trace.get('timestamp')}"
        if cache_key not in cache:
            cache[cache_key] = get_summary_for_trace_fn(trace)
        trace['parent_summary'] = cache[cache_key]
    return traces
