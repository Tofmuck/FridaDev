from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

import psycopg

import config
from admin import runtime_settings
from core import runtime_db_bootstrap
from observability import dashboard_analytics
from observability.full_turn_metrics_snapshot import build_full_turn_metrics_snapshot
from observability.turn_pipeline_read_model import build_turn_pipeline_item
from observability.turn_observability_checklist import build_turn_observability_checklist

logger = logging.getLogger('frida.log_store')

_STATUS_ALLOWED = {'ok', 'error', 'skipped'}
_REQUIRED_FIELDS = {'event_id', 'conversation_id', 'turn_id', 'ts', 'stage', 'status'}
_LLM_CALL_MAIN_PROVIDER_CALLER = 'llm'
_LLM_CALL_SECONDARY_PROVIDER_CALLERS = (
    'stimmung_agent',
    'validation_agent',
    'web_reformulation',
)
_LLM_CALL_KNOWN_PROVIDER_CALLERS = (
    _LLM_CALL_MAIN_PROVIDER_CALLER,
    *_LLM_CALL_SECONDARY_PROVIDER_CALLERS,
)
_LLM_CALL_AGGREGATE_PROVIDER_CALLERS = (
    *_LLM_CALL_KNOWN_PROVIDER_CALLERS,
    'unknown',
)


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


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _utc_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    text = str(value or '').strip()
    return text or None


def normalize_llm_call_provider_caller(value: Any) -> str:
    caller = str(value or '').strip().lower()
    if caller in _LLM_CALL_KNOWN_PROVIDER_CALLERS:
        return caller
    return 'unknown'


def _empty_llm_call_provider_bucket(provider_caller: str) -> dict[str, Any]:
    return {
        'provider_caller': provider_caller,
        'total_count': 0,
        'ok_count': 0,
        'error_count': 0,
        'skipped_count': 0,
        'unknown_status_count': 0,
        'duration_ms_total': 0,
        'duration_ms_count': 0,
        'avg_duration_ms': None,
        'response_chars_total': 0,
        'latest_ts': None,
    }


def _llm_call_metric_row_value(row: Mapping[str, Any] | Sequence[Any], key: str, index: int) -> Any:
    if isinstance(row, Mapping):
        return row.get(key)
    try:
        return row[index]
    except (IndexError, TypeError):
        return None


def build_llm_call_provider_metrics(rows: Sequence[Mapping[str, Any] | Sequence[Any]]) -> dict[str, Any]:
    """Build content-free llm_call metrics grouped by provider_caller.

    Legacy rows without a known provider_caller are intentionally grouped under
    ``unknown`` so they cannot be mistaken for the main runtime LLM.
    """
    by_provider_caller = {
        caller: _empty_llm_call_provider_bucket(caller)
        for caller in _LLM_CALL_AGGREGATE_PROVIDER_CALLERS
    }

    for row in rows:
        provider_caller = normalize_llm_call_provider_caller(
            _llm_call_metric_row_value(row, 'provider_caller', 0)
        )
        status = str(_llm_call_metric_row_value(row, 'status', 1) or '').strip().lower()
        calls_count = _to_int(_llm_call_metric_row_value(row, 'calls_count', 2))
        duration_ms_total = _to_int(_llm_call_metric_row_value(row, 'duration_ms_total', 3))
        duration_ms_count = _to_int(_llm_call_metric_row_value(row, 'duration_ms_count', 4))
        response_chars_total = _to_int(_llm_call_metric_row_value(row, 'response_chars_total', 5))
        latest_ts = _utc_iso(_llm_call_metric_row_value(row, 'latest_ts', 6))

        bucket = by_provider_caller[provider_caller]
        bucket['total_count'] += calls_count
        if status in _STATUS_ALLOWED:
            bucket[f'{status}_count'] += calls_count
        else:
            bucket['unknown_status_count'] += calls_count
        bucket['duration_ms_total'] += duration_ms_total
        bucket['duration_ms_count'] += duration_ms_count
        bucket['response_chars_total'] += response_chars_total
        if latest_ts and (not bucket['latest_ts'] or latest_ts > str(bucket['latest_ts'])):
            bucket['latest_ts'] = latest_ts

    total_llm_call_count = sum(
        int(bucket['total_count'])
        for bucket in by_provider_caller.values()
    )
    secondary_llm_call_count = sum(
        int(by_provider_caller[caller]['total_count'])
        for caller in _LLM_CALL_SECONDARY_PROVIDER_CALLERS
    )

    for bucket in by_provider_caller.values():
        duration_count = int(bucket['duration_ms_count'])
        if duration_count > 0:
            bucket['avg_duration_ms'] = round(
                float(bucket['duration_ms_total']) / float(duration_count),
                3,
            )

    return {
        'main_provider_caller': _LLM_CALL_MAIN_PROVIDER_CALLER,
        'secondary_provider_callers': list(_LLM_CALL_SECONDARY_PROVIDER_CALLERS),
        'known_provider_callers': list(_LLM_CALL_KNOWN_PROVIDER_CALLERS),
        'by_provider_caller': by_provider_caller,
        'total_llm_call_count': total_llm_call_count,
        'main_llm_call_count': int(by_provider_caller[_LLM_CALL_MAIN_PROVIDER_CALLER]['total_count']),
        'secondary_llm_call_count': secondary_llm_call_count,
        'unknown_llm_call_count': int(by_provider_caller['unknown']['total_count']),
    }


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
                dashboard_analytics.execute_dashboard_analytics_schema(cur)
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


def read_llm_call_provider_metrics(
    *,
    ts_from: str | None = None,
    ts_to: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read content-free llm_call counts grouped by provider_caller."""
    ts_from_s = _validate_iso8601_filter(ts_from, field_name='ts_from')
    ts_to_s = _validate_iso8601_filter(ts_to, field_name='ts_to')

    where_clauses: list[str] = ["stage = 'llm_call'"]
    where_params: list[Any] = []
    if ts_from_s:
        where_clauses.append('ts >= %s::timestamptz')
        where_params.append(ts_from_s)
    if ts_to_s:
        where_clauses.append('ts <= %s::timestamptz')
        where_params.append(ts_to_s)
    where_sql = ' AND '.join(where_clauses)

    rows: list[tuple[Any, ...]] = []
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    WITH llm_calls AS (
                        SELECT
                            COALESCE(NULLIF(payload_json->>'provider_caller', ''), '') AS provider_caller,
                            status,
                            duration_ms,
                            CASE
                                WHEN COALESCE(payload_json->>'response_chars', '') ~ '^[0-9]+$'
                                THEN (payload_json->>'response_chars')::bigint
                                ELSE 0
                            END AS response_chars,
                            ts
                        FROM observability.chat_log_events
                        WHERE {where_sql}
                    )
                    SELECT
                        provider_caller,
                        status,
                        COUNT(*)::int AS calls_count,
                        COALESCE(SUM(duration_ms), 0)::bigint AS duration_ms_total,
                        COUNT(duration_ms)::int AS duration_ms_count,
                        COALESCE(SUM(response_chars), 0)::bigint AS response_chars_total,
                        MAX(ts) AS latest_ts
                    FROM llm_calls
                    GROUP BY provider_caller, status
                    ORDER BY provider_caller ASC, status ASC
                    ''',
                    tuple(where_params),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger_instance.error('llm_call_provider_metrics_read_failed err=%s', exc)
        result = build_llm_call_provider_metrics([])
        result['filters'] = {
            'ts_from': ts_from_s,
            'ts_to': ts_to_s,
        }
        return result

    result = build_llm_call_provider_metrics(rows)
    result['filters'] = {
        'ts_from': ts_from_s,
        'ts_to': ts_to_s,
    }
    return result


def read_turn_observability_checklist(
    *,
    conversation_id: str,
    turn_id: str,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read one turn's compact observability completeness checklist."""
    conversation_id_s = str(conversation_id or '').strip()
    turn_id_s = str(turn_id or '').strip()
    if not conversation_id_s:
        raise ValueError('conversation_id is required')
    if not turn_id_s:
        raise ValueError('turn_id is required')

    try:
        events_result = read_chat_log_events(
            limit=500,
            conversation_id=conversation_id_s,
            turn_id=turn_id_s,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
    except Exception as exc:
        logger_instance.error(
            'turn_observability_checklist_read_failed conversation_id=%s turn_id=%s err=%s',
            conversation_id_s,
            turn_id_s,
            exc,
        )
        raise

    checklist = build_turn_observability_checklist(events_result.get('items') or [])
    checklist['filters'] = {
        'conversation_id': conversation_id_s,
        'turn_id': turn_id_s,
    }
    checklist['source'] = {
        'events_total': _to_int(events_result.get('total')),
        'events_read': _to_int(events_result.get('count')),
        'events_truncated': _to_int(events_result.get('total')) > _to_int(events_result.get('count')),
    }
    return checklist


def read_chat_turn_pipeline(
    *,
    conversation_id: str | None = None,
    turn_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
    ts_from: str | None = None,
    ts_to: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read compact content-free cockpit rows grouped by chat turn."""
    limit_i = max(1, min(int(limit), 100))
    offset_i = max(0, int(offset))
    conversation_id_s = str(conversation_id or '').strip() or None
    turn_id_s = str(turn_id or '').strip() or None
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
    if ts_from_s:
        where_clauses.append('ts >= %s::timestamptz')
        where_params.append(ts_from_s)
    if ts_to_s:
        where_clauses.append('ts <= %s::timestamptz')
        where_params.append(ts_to_s)
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

    turn_groups: list[dict[str, Any]] = []
    total = 0
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    SELECT COUNT(*)::int
                    FROM (
                        SELECT conversation_id, turn_id
                        FROM observability.chat_log_events
                        {where_sql}
                        GROUP BY conversation_id, turn_id
                    ) AS grouped_turns
                    ''',
                    tuple(where_params),
                )
                total = int((cur.fetchone() or [0])[0] or 0)

                cur.execute(
                    f'''
                    SELECT
                        conversation_id,
                        turn_id,
                        MIN(ts) AS first_ts,
                        MAX(ts) AS latest_ts,
                        COUNT(*)::int AS events_count
                    FROM observability.chat_log_events
                    {where_sql}
                    GROUP BY conversation_id, turn_id
                    ORDER BY MAX(ts) DESC, conversation_id DESC, turn_id DESC
                    LIMIT %s OFFSET %s
                    ''',
                    tuple(where_params + [limit_i, offset_i]),
                )
                for row in cur.fetchall():
                    first_ts = row[2]
                    latest_ts = row[3]
                    turn_groups.append(
                        {
                            'conversation_id': str(row[0] or ''),
                            'turn_id': str(row[1] or ''),
                            'first_ts': _utc_iso(first_ts),
                            'latest_ts': _utc_iso(latest_ts),
                            'events_count': int(row[4] or 0),
                        }
                    )
    except Exception as exc:
        logger_instance.error('chat_turn_pipeline_read_failed err=%s', exc)
        return {
            'kind': 'chat_turn_pipeline_read_model',
            'schema_version': '1',
            'items': [],
            'count': 0,
            'total': 0,
            'limit': limit_i,
            'offset': offset_i,
            'next_offset': None,
            'filters': {
                'conversation_id': conversation_id_s,
                'turn_id': turn_id_s,
                'ts_from': ts_from_s,
                'ts_to': ts_to_s,
            },
            'source': {
                'source_kind': 'chat_log_events',
                'turns_truncated': False,
                'read_error': True,
            },
            'redaction': {
                'raw_event_payloads_included': False,
            },
        }

    items: list[dict[str, Any]] = []
    for group in turn_groups:
        events_result = read_chat_log_events(
            limit=500,
            conversation_id=group['conversation_id'],
            turn_id=group['turn_id'],
            ts_from=ts_from_s,
            ts_to=ts_to_s,
            conn_factory=conn_factory,
            logger_instance=logger_instance,
        )
        item = build_turn_pipeline_item(
            events_result.get('items') or [],
            events_total=_to_int(events_result.get('total')),
            events_truncated=_to_int(events_result.get('total')) > _to_int(events_result.get('count')),
        )
        if not item.get('first_ts'):
            item['first_ts'] = group['first_ts']
        if not item.get('latest_ts'):
            item['latest_ts'] = group['latest_ts']
        items.append(item)

    next_offset = offset_i + len(items)
    if next_offset >= total:
        next_offset = None

    return {
        'kind': 'chat_turn_pipeline_read_model',
        'schema_version': '1',
        'items': items,
        'count': len(items),
        'total': total,
        'limit': limit_i,
        'offset': offset_i,
        'next_offset': next_offset,
        'filters': {
            'conversation_id': conversation_id_s,
            'turn_id': turn_id_s,
            'ts_from': ts_from_s,
            'ts_to': ts_to_s,
        },
        'source': {
            'source_kind': 'chat_log_events',
            'turns_truncated': total > len(items) + offset_i,
            'per_turn_event_limit': 500,
        },
        'redaction': {
            'raw_event_payloads_included': False,
        },
    }


def read_full_turn_metrics_snapshot(
    *,
    ts_from: str | None = None,
    ts_to: str | None = None,
    event_limit: int = 2000,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read content-free aggregate metrics for future full-turn dashboards."""
    ts_from_s = _validate_iso8601_filter(ts_from, field_name='ts_from')
    ts_to_s = _validate_iso8601_filter(ts_to, field_name='ts_to')
    event_limit_i = max(1, min(int(event_limit), 5000))

    where_clauses: list[str] = []
    where_params: list[Any] = []
    if ts_from_s:
        where_clauses.append('ts >= %s::timestamptz')
        where_params.append(ts_from_s)
    if ts_to_s:
        where_clauses.append('ts <= %s::timestamptz')
        where_params.append(ts_to_s)
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ''

    events: list[dict[str, Any]] = []
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
                    LIMIT %s
                    ''',
                    tuple(where_params + [event_limit_i]),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger_instance.error('full_turn_metrics_snapshot_read_failed err=%s', exc)
        snapshot = build_full_turn_metrics_snapshot(
            [],
            llm_call_provider_metrics=build_llm_call_provider_metrics([]),
        )
        snapshot['filters'] = {
            'ts_from': ts_from_s,
            'ts_to': ts_to_s,
            'event_limit': event_limit_i,
        }
        snapshot['source'] = {
            'events_total': 0,
            'events_read': 0,
            'events_truncated': False,
            'read_error': True,
        }
        return snapshot

    for row in rows:
        payload_json = row[7]
        if not isinstance(payload_json, dict):
            payload_json = {}
        events.append(
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

    llm_metrics = build_llm_call_provider_metrics(
        [
            (
                event.get('payload', {}).get('provider_caller'),
                event.get('status'),
                1,
                _to_int(event.get('duration_ms')),
                1 if event.get('duration_ms') is not None else 0,
                _to_int(event.get('payload', {}).get('response_chars')),
                event.get('ts'),
            )
            for event in events
            if event.get('stage') == 'llm_call'
        ]
    )
    snapshot = build_full_turn_metrics_snapshot(
        events,
        llm_call_provider_metrics=llm_metrics,
    )
    snapshot['filters'] = {
        'ts_from': ts_from_s,
        'ts_to': ts_to_s,
        'event_limit': event_limit_i,
    }
    snapshot['source'] = {
        'events_total': total,
        'events_read': len(events),
        'events_truncated': total > len(events),
    }
    return snapshot


def read_chat_log_metadata(
    *,
    conversation_id: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    """Read dedicated metadata for selector lists (conversation and turn)."""
    conversation_id_s = str(conversation_id or '').strip() or None
    conversations: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT
                        conversation_id,
                        MAX(ts) AS last_ts,
                        COUNT(*)::int AS events_count
                    FROM observability.chat_log_events
                    GROUP BY conversation_id
                    ORDER BY MAX(ts) DESC, conversation_id DESC
                    ''',
                    (),
                )
                for row in cur.fetchall():
                    conv_id = str(row[0] or '').strip()
                    if not conv_id:
                        continue
                    last_ts = row[1]
                    conversations.append(
                        {
                            'conversation_id': conv_id,
                            'last_ts': (
                                last_ts.astimezone(timezone.utc).isoformat()
                                if isinstance(last_ts, datetime)
                                else str(last_ts or '')
                            ),
                            'events_count': int(row[2] or 0),
                        }
                    )

                if conversation_id_s:
                    cur.execute(
                        '''
                        SELECT
                            turn_id,
                            MAX(ts) AS last_ts,
                            COUNT(*)::int AS events_count
                        FROM observability.chat_log_events
                        WHERE conversation_id = %s
                        GROUP BY turn_id
                        ORDER BY MAX(ts) DESC, turn_id DESC
                        ''',
                        (conversation_id_s,),
                    )
                    for row in cur.fetchall():
                        turn_id_value = str(row[0] or '').strip()
                        if not turn_id_value:
                            continue
                        last_ts = row[1]
                        turns.append(
                            {
                                'turn_id': turn_id_value,
                                'last_ts': (
                                    last_ts.astimezone(timezone.utc).isoformat()
                                    if isinstance(last_ts, datetime)
                                    else str(last_ts or '')
                                ),
                                'events_count': int(row[2] or 0),
                            }
                        )
    except Exception as exc:
        logger_instance.error(
            'chat_log_metadata_read_failed conversation_id=%s err=%s',
            conversation_id_s,
            exc,
        )
        raise RuntimeError('chat log metadata read failed') from exc

    return {
        'selected_conversation_id': conversation_id_s,
        'conversations': conversations,
        'turns': turns,
    }


def delete_chat_log_events(
    *,
    conversation_id: str | None = None,
    turn_id: str | None = None,
    conn_factory: Callable[[], Any] = _conn,
    logger_instance: Any = logger,
) -> dict[str, Any]:
    conversation_id_s = str(conversation_id or '').strip() or None
    turn_id_s = str(turn_id or '').strip() or None

    if conversation_id_s is None and turn_id_s is None:
        raise ValueError('all_logs deletion is not supported in MVP')
    if conversation_id_s is None and turn_id_s is not None:
        raise ValueError('turn_logs deletion requires conversation_id')

    where_clauses = ['conversation_id = %s']
    where_params: list[Any] = [conversation_id_s]
    scope = 'conversation_logs'
    if turn_id_s:
        where_clauses.append('turn_id = %s')
        where_params.append(turn_id_s)
        scope = 'turn_logs'

    where_sql = ' AND '.join(where_clauses)
    deleted_count = 0
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f'''
                    DELETE FROM observability.chat_log_events
                    WHERE {where_sql}
                    ''',
                    tuple(where_params),
                )
                deleted_count = int(cur.rowcount or 0)
            conn.commit()
    except Exception as exc:
        logger_instance.error(
            'chat_log_events_delete_failed scope=%s conversation_id=%s turn_id=%s err=%s',
            scope,
            conversation_id_s,
            turn_id_s,
            exc,
        )
        raise RuntimeError('chat log deletion failed') from exc

    return {
        'scope': scope,
        'conversation_id': conversation_id_s,
        'turn_id': turn_id_s,
        'deleted_count': deleted_count,
    }
