from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable

import psycopg

import config
from admin import runtime_settings
from core import runtime_db_bootstrap

logger = logging.getLogger('frida.log_store')

_STATUS_ALLOWED = {'ok', 'error', 'skipped'}
_REQUIRED_FIELDS = {'event_id', 'conversation_id', 'turn_id', 'ts', 'stage', 'status'}


def _conn() -> Any:
    return runtime_db_bootstrap.connect_runtime_database(
        psycopg,
        config,
        runtime_settings,
    )


def _validate_iso8601_filter(value: str | None, *, field_name: str) -> str | None:
    raw = str(value or '').strip()
    if not raw:
        return None
    normalized = raw[:-1] + '+00:00' if raw.endswith('Z') else raw
    try:
        datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise ValueError(f'invalid {field_name} timestamp: {raw}') from exc
    return raw


def init_log_storage(
    *,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> None:
    """Create dedicated observability schema/table/indexes for chat turn logs."""
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE SCHEMA IF NOT EXISTS observability;')
                cur.execute(
                    '''
                    CREATE TABLE IF NOT EXISTS observability.chat_log_events (
                        event_id        TEXT PRIMARY KEY,
                        conversation_id TEXT        NOT NULL,
                        turn_id         TEXT        NOT NULL,
                        ts              TIMESTAMPTZ NOT NULL,
                        stage           TEXT        NOT NULL,
                        status          TEXT        NOT NULL,
                        duration_ms     INTEGER,
                        payload_json    JSONB       NOT NULL DEFAULT '{}'::jsonb,
                        created_ts      TIMESTAMPTZ NOT NULL DEFAULT now(),
                        CHECK (status IN ('ok', 'error', 'skipped'))
                    );
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS chat_log_events_ts_idx
                    ON observability.chat_log_events (ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS chat_log_events_conversation_ts_idx
                    ON observability.chat_log_events (conversation_id, ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS chat_log_events_conversation_turn_ts_idx
                    ON observability.chat_log_events (conversation_id, turn_id, ts DESC);
                    '''
                )
                cur.execute(
                    '''
                    CREATE INDEX IF NOT EXISTS chat_log_events_status_ts_idx
                    ON observability.chat_log_events (status, ts DESC);
                    '''
                )
            conn.commit()
        logger_instance.info('log_storage_init ok')
    except Exception as exc:
        logger_instance.error('log_storage_init_failed err=%s', exc)


def insert_chat_log_event(
    event: dict[str, Any],
    *,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> bool:
    missing = sorted(_REQUIRED_FIELDS - set(event.keys()))
    if missing:
        raise ValueError(f'missing required chat log event fields: {", ".join(missing)}')

    event_id = str(event.get('event_id') or '').strip()
    if not event_id:
        raise ValueError('chat log event event_id must not be empty')

    conversation_id = str(event.get('conversation_id') or '').strip()
    if not conversation_id:
        raise ValueError('chat log event conversation_id must not be empty')

    turn_id = str(event.get('turn_id') or '').strip()
    if not turn_id:
        raise ValueError('chat log event turn_id must not be empty')

    stage = str(event.get('stage') or '').strip()
    if not stage:
        raise ValueError('chat log event stage must not be empty')

    status = str(event.get('status') or '').strip().lower()
    if status not in _STATUS_ALLOWED:
        raise ValueError(f'invalid chat log event status: {status}')

    duration_ms_raw = event.get('duration_ms')
    duration_ms = None if duration_ms_raw is None else int(duration_ms_raw)

    payload_json_raw = event.get('payload_json')
    if payload_json_raw is None:
        payload_json_raw = {}
    if not isinstance(payload_json_raw, dict):
        raise ValueError('chat log event payload_json must be an object')

    ts_raw = event.get('ts')
    if isinstance(ts_raw, datetime):
        ts = ts_raw.astimezone(timezone.utc).isoformat()
    else:
        ts = str(ts_raw or '').strip()
    if not ts:
        raise ValueError('chat log event ts must not be empty')

    rowcount = 0
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    INSERT INTO observability.chat_log_events (
                        event_id,
                        conversation_id,
                        turn_id,
                        ts,
                        stage,
                        status,
                        duration_ms,
                        payload_json
                    )
                    VALUES (%s, %s, %s, %s::timestamptz, %s, %s, %s, %s::jsonb)
                    ON CONFLICT (event_id) DO NOTHING
                    ''',
                    (
                        event_id,
                        conversation_id,
                        turn_id,
                        ts,
                        stage,
                        status,
                        duration_ms,
                        json.dumps(payload_json_raw, ensure_ascii=False),
                    ),
                )
                rowcount = int(cur.rowcount or 0)
            conn.commit()
    except Exception as exc:
        logger_instance.error('chat_log_event_insert_failed event_id=%s err=%s', event.get('event_id'), exc)
        return False

    if rowcount == 0:
        logger_instance.info('chat_log_event_duplicate event_id=%s', event.get('event_id'))
        return False
    return True


def read_chat_log_events(
    *,
    limit: int = 100,
    offset: int = 0,
    conversation_id: str | None = None,
    turn_id: str | None = None,
    stage: str | None = None,
    status: str | None = None,
    ts_from: str | None = None,
    ts_to: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read chat log events with simple offset pagination and optional filters."""
    limit_i = max(1, min(int(limit), 500))
    offset_i = max(0, int(offset))

    conversation_id_s = str(conversation_id or '').strip() or None
    turn_id_s = str(turn_id or '').strip() or None
    stage_s = str(stage or '').strip() or None

    status_s = str(status or '').strip().lower() or None
    if status_s and status_s not in _STATUS_ALLOWED:
        raise ValueError(f'invalid chat log status filter: {status_s}')

    ts_from_s = _validate_iso8601_filter(ts_from, field_name='ts_from')
    ts_to_s = _validate_iso8601_filter(ts_to, field_name='ts_to')

    where_clauses: list[str] = []
    where_params: list[Any] = []

    if conversation_id_s:
        where_clauses.append('conversation_id = %s')
        where_params.append(conversation_id_s)
    if turn_id_s:
        where_clauses.append('turn_id = %s')
        where_params.append(turn_id_s)
    if stage_s:
        where_clauses.append('stage = %s')
        where_params.append(stage_s)
    if status_s:
        where_clauses.append('status = %s')
        where_params.append(status_s)
    if ts_from_s:
        where_clauses.append('ts >= %s::timestamptz')
        where_params.append(ts_from_s)
    if ts_to_s:
        where_clauses.append('ts <= %s::timestamptz')
        where_params.append(ts_to_s)

    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

    items: list[dict[str, Any]] = []
    total = 0

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT COUNT(*)
                    FROM observability.chat_log_events
                    {where_sql}
                    ''',
                    tuple(where_params),
                )
                total = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    f'''
                    SELECT
                        event_id,
                        conversation_id,
                        turn_id,
                        ts,
                        stage,
                        status,
                        duration_ms,
                        payload_json
                    FROM observability.chat_log_events
                    {where_sql}
                    ORDER BY ts DESC, event_id DESC
                    LIMIT %s OFFSET %s
                    ''',
                    tuple(where_params + [limit_i, offset_i]),
                )
                rows = cur.fetchall()

        for row in rows:
            payload_json = row[7]
            if not isinstance(payload_json, dict):
                payload_json = {}
            items.append(
                {
                    'event_id': str(row[0] or ''),
                    'conversation_id': str(row[1] or ''),
                    'turn_id': str(row[2] or ''),
                    'ts': row[3].astimezone(timezone.utc).isoformat() if isinstance(row[3], datetime) else str(row[3]),
                    'stage': str(row[4] or ''),
                    'status': str(row[5] or ''),
                    'duration_ms': int(row[6]) if row[6] is not None else None,
                    'payload': payload_json,
                }
            )
    except Exception as exc:
        logger_instance.error('chat_log_events_read_failed err=%s', exc)
        return {
            'items': [],
            'count': 0,
            'total': 0,
            'limit': limit_i,
            'offset': offset_i,
            'next_offset': None,
            'filters': {
                'conversation_id': conversation_id_s,
                'turn_id': turn_id_s,
                'stage': stage_s,
                'status': status_s,
                'ts_from': ts_from_s,
                'ts_to': ts_to_s,
            },
        }

    next_offset = offset_i + len(items)
    if next_offset >= total:
        next_offset = None

    return {
        'items': items,
        'count': len(items),
        'total': total,
        'limit': limit_i,
        'offset': offset_i,
        'next_offset': next_offset,
        'filters': {
            'conversation_id': conversation_id_s,
            'turn_id': turn_id_s,
            'stage': stage_s,
            'status': status_s,
            'ts_from': ts_from_s,
            'ts_to': ts_to_s,
        },
    }
