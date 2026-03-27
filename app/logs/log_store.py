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
