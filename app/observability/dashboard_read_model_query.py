from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from observability import dashboard_analytics

RETENTION_DAYS = dashboard_analytics.RETENTION_DAYS
RECENT_GRANULARITY_DAYS = dashboard_analytics.RECENT_GRANULARITY_DAYS
CALCULATION_VERSION = dashboard_analytics.CALCULATION_VERSION

_MAX_LIMIT = 200
_MAX_CONTENT_GATE_EVENTS = 500


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat()
    text = str(value or '').strip()
    return text or None


def _parse_ts(value: Any, *, field_name: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or '').strip()
        if not text:
            raise ValueError(f'{field_name} is required')
        try:
            parsed = datetime.fromisoformat(text[:-1] + '+00:00' if text.endswith('Z') else text)
        except ValueError as exc:
            raise ValueError(f'invalid {field_name} timestamp: {text}') from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _parse_optional_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    try:
        return _parse_ts(value, field_name='timestamp')
    except ValueError:
        return None


def _now_utc(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc)


def _params_get(params: Mapping[str, Any] | None, key: str, default: str = '') -> str:
    if not params:
        return default
    value = params.get(key, default)
    if isinstance(value, (list, tuple)):
        value = value[0] if value else default
    return str(value or default).strip()


def resolve_dashboard_window(
    params: Mapping[str, Any] | None = None,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    now_dt = _now_utc(now)
    explicit_from = _params_get(params, 'ts_from')
    explicit_to = _params_get(params, 'ts_to')
    raw_window = _params_get(params, 'window', '24h').lower() or '24h'

    if explicit_from or explicit_to:
        if not explicit_from or not explicit_to:
            raise ValueError('ts_from and ts_to are required together for custom dashboard windows')
        start = _parse_ts(explicit_from, field_name='ts_from')
        end = _parse_ts(explicit_to, field_name='ts_to')
        window_key = 'custom'
        label_fr = 'Fenetre personnalisee'
    elif raw_window == '24h':
        end = now_dt
        start = end - timedelta(hours=24)
        window_key = '24h'
        label_fr = '24 h'
    elif raw_window == '7d':
        end = now_dt
        start = end - timedelta(days=7)
        window_key = '7d'
        label_fr = '7 j'
    elif raw_window == '30d':
        end = now_dt
        start = end - timedelta(days=30)
        window_key = '30d'
        label_fr = '30 j'
    elif raw_window == '90d':
        end = now_dt
        start = end - timedelta(days=RETENTION_DAYS)
        window_key = '90d'
        label_fr = '90 jours'
    elif raw_window == 'today':
        start = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        end = now_dt
        window_key = 'today'
        label_fr = 'Aujourd hui'
    elif raw_window == 'yesterday':
        today = now_dt.replace(hour=0, minute=0, second=0, microsecond=0)
        start = today - timedelta(days=1)
        end = today
        window_key = 'yesterday'
        label_fr = 'Hier'
    elif raw_window == 'custom':
        raise ValueError('ts_from and ts_to are required for custom dashboard windows')
    else:
        raise ValueError(f'invalid dashboard window: {raw_window}')

    if start >= end:
        raise ValueError('ts_from must be before ts_to')
    retention_start = now_dt - timedelta(days=RETENTION_DAYS)
    if start < retention_start - timedelta(seconds=1):
        raise ValueError('dashboard window exceeds 90 days retention')

    duration_seconds = max(0, int((end - start).total_seconds()))
    granularity = 'hour' if duration_seconds <= RECENT_GRANULARITY_DAYS * 24 * 60 * 60 else 'day'
    return {
        'kind': 'dashboard_window',
        'key': window_key,
        'label_fr': label_fr,
        'start': start.isoformat(),
        'end': end.isoformat(),
        'granularity': granularity,
        'retention_days': RETENTION_DAYS,
        'recent_granularity_days': RECENT_GRANULARITY_DAYS,
    }


def _limit_offset(
    params: Mapping[str, Any] | None,
    *,
    default_limit: int,
) -> tuple[int, int]:
    raw_limit = _params_get(params, 'limit', str(default_limit))
    raw_offset = _params_get(params, 'offset', '0')
    try:
        limit = int(raw_limit)
        offset = int(raw_offset)
    except ValueError as exc:
        raise ValueError('invalid pagination parameters') from exc
    if limit <= 0 or offset < 0:
        raise ValueError('invalid pagination parameters')
    return min(limit, _MAX_LIMIT), offset


def _json_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _status_schema_from_flags(flags: Mapping[str, Any]) -> dict[str, Any]:
    status_schema = _mapping(flags.get('status_schema'))
    if not status_schema:
        return {}
    return {
        'source_kind': status_schema.get('source_kind') or 'unknown',
        'schema_counts': _json_mapping(status_schema.get('schema_counts')),
        'v1_event_count': _to_int(status_schema.get('v1_event_count')),
        'legacy_event_count': _to_int(status_schema.get('legacy_event_count')),
        'historical_events_reclassified': bool(status_schema.get('historical_events_reclassified', False)),
    }


def _window_coverage(
    window: Mapping[str, Any],
    materialization: Mapping[str, Any],
) -> dict[str, Any]:
    requested_start = _parse_optional_ts(window.get('start'))
    requested_end = _parse_optional_ts(window.get('end'))
    materialized_start = _parse_optional_ts(materialization.get('window_start'))
    materialized_end = _parse_optional_ts(materialization.get('window_end'))
    coverage = {
        'status': 'absent',
        'complete': False,
        'reason_code': 'materialization_window_missing',
        'requested_window_start': _iso(requested_start),
        'requested_window_end': _iso(requested_end),
        'materialized_window_start': _iso(materialized_start),
        'materialized_window_end': _iso(materialized_end),
        'overlap_start': None,
        'overlap_end': None,
    }
    if not requested_start or not requested_end or not materialized_start or not materialized_end:
        return coverage

    if materialized_start <= requested_start and materialized_end >= requested_end:
        coverage.update(
            {
                'status': 'complete',
                'complete': True,
                'reason_code': 'materialization_covers_requested_window',
                'overlap_start': _iso(requested_start),
                'overlap_end': _iso(requested_end),
            }
        )
        return coverage

    overlap_start = max(requested_start, materialized_start)
    overlap_end = min(requested_end, materialized_end)
    if overlap_start < overlap_end:
        coverage.update(
            {
                'status': 'partial',
                'reason_code': 'materialization_partially_covers_requested_window',
                'overlap_start': _iso(overlap_start),
                'overlap_end': _iso(overlap_end),
            }
        )
        return coverage

    coverage['reason_code'] = 'materialization_does_not_cover_requested_window'
    return coverage


def _operator_source_status(
    materialization: Mapping[str, Any],
    coverage: Mapping[str, Any],
    *,
    degraded_reason: str | None,
) -> str:
    if degraded_reason:
        return 'degraded'
    coverage_status = str(coverage.get('status') or 'absent')
    if coverage_status == 'absent':
        return 'not_materialized'
    if coverage_status == 'partial':
        return 'partially_materialized'
    materialization_status = str(materialization.get('status') or 'empty')
    if materialization_status != 'ok':
        return materialization_status
    if bool(materialization.get('source_events_truncated')) or bool(materialization.get('event_limit_dependency')):
        return 'degraded'
    return 'ok'


def _source_status(
    window: Mapping[str, Any],
    status: Mapping[str, Any] | None,
    *,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    materialization = dict(status or {})
    coverage = _window_coverage(window, materialization)
    return {
        'kind': 'dashboard_source_status',
        'status': _operator_source_status(
            materialization,
            coverage,
            degraded_reason=degraded_reason,
        ),
        'degraded_reason': degraded_reason,
        'window': dict(window),
        'coverage': coverage,
        'materialization': {
            'materializer_key': materialization.get('materializer_key') or 'dashboard_long_term_observability',
            'status': materialization.get('status') or 'empty',
            'calculation_version': materialization.get('calculation_version') or CALCULATION_VERSION,
            'window_start': materialization.get('window_start'),
            'window_end': materialization.get('window_end'),
            'last_event_id': materialization.get('last_event_id'),
            'last_event_ts': materialization.get('last_event_ts'),
            'lag_seconds': materialization.get('lag_seconds'),
            'updated_ts': materialization.get('updated_ts'),
            'backfill_status': materialization.get('backfill_status') or 'unknown',
            'error_count': _to_int(materialization.get('error_count')),
            'last_error_code': materialization.get('last_error_code'),
            'last_error_chars': _to_int(materialization.get('last_error_chars')),
            'last_error_sha256_12': materialization.get('last_error_sha256_12'),
        },
        'limits': {
            'retention_days': RETENTION_DAYS,
            'recent_granularity_days': RECENT_GRANULARITY_DAYS,
            'source_events_truncated': bool(materialization.get('source_events_truncated', False)),
            'event_limit_dependency': bool(materialization.get('event_limit_dependency', False)),
            'raw_content_included': False,
        },
    }


def _read_materialization_status(cur: Any) -> dict[str, Any] | None:
    cur.execute(
        '''
        SELECT
            materializer_key,
            calculation_version,
            status,
            window_start,
            window_end,
            retention_days,
            recent_granularity_days,
            old_granularity,
            source_events_count,
            source_events_truncated,
            event_limit_dependency,
            last_event_id,
            last_event_ts,
            lag_seconds,
            turns_materialized_count,
            conversations_materialized_count,
            buckets_materialized_count,
            error_count,
            last_error_code,
            last_error_chars,
            last_error_sha256_12,
            backfill_status,
            updated_ts
        FROM observability.dashboard_materialization_status
        ORDER BY updated_ts DESC
        LIMIT 1
        '''
    )
    row = cur.fetchone()
    if not row:
        return None
    return {
        'materializer_key': str(row[0] or ''),
        'calculation_version': str(row[1] or ''),
        'status': str(row[2] or ''),
        'window_start': _iso(row[3]),
        'window_end': _iso(row[4]),
        'retention_days': _to_int(row[5]),
        'recent_granularity_days': _to_int(row[6]),
        'old_granularity': str(row[7] or ''),
        'source_events_count': _to_int(row[8]),
        'source_events_truncated': bool(row[9]),
        'event_limit_dependency': bool(row[10]),
        'last_event_id': row[11],
        'last_event_ts': _iso(row[12]),
        'lag_seconds': _to_int(row[13]) if row[13] is not None else None,
        'turns_materialized_count': _to_int(row[14]),
        'conversations_materialized_count': _to_int(row[15]),
        'buckets_materialized_count': _to_int(row[16]),
        'error_count': _to_int(row[17]),
        'last_error_code': row[18],
        'last_error_chars': _to_int(row[19]),
        'last_error_sha256_12': row[20],
        'backfill_status': str(row[21] or ''),
        'updated_ts': _iso(row[22]),
    }


def _bucket_row(row: Sequence[Any]) -> dict[str, Any]:
    return {
        'granularity': str(row[0] or ''),
        'bucket_start': _iso(row[1]),
        'bucket_end': _iso(row[2]),
        'module_key': str(row[3] or ''),
        'turn_count': _to_int(row[4]),
        'event_count': _to_int(row[5]),
        'metrics': _json_mapping(row[6]),
        'calculation_version': str(row[7] or ''),
        'materialized_ts': _iso(row[8]),
    }


def _read_metric_buckets(cur: Any, window: Mapping[str, Any]) -> list[dict[str, Any]]:
    cur.execute(
        '''
        SELECT
            granularity,
            bucket_start,
            bucket_end,
            module_key,
            turn_count,
            event_count,
            metrics_json,
            calculation_version,
            materialized_ts
        FROM observability.dashboard_metric_buckets
        WHERE granularity = %s
          AND bucket_start >= %s::timestamptz
          AND bucket_start < %s::timestamptz
        ORDER BY bucket_start ASC, module_key ASC
        ''',
        (window['granularity'], window['start'], window['end']),
    )
    return [_bucket_row(row) for row in cur.fetchall()]


def _turn_fact_row(row: Sequence[Any]) -> dict[str, Any]:
    if len(row) == 24:
        row = (*row[:16], {}, *row[16:])
    flags = _json_mapping(row[21])
    return {
        'conversation_id': str(row[0] or ''),
        'turn_id': str(row[1] or ''),
        'first_ts': _iso(row[2]),
        'latest_ts': _iso(row[3]),
        'classification': str(row[4] or 'legacy_incomplete'),
        'score': _to_int(row[5]),
        'source_event_count': _to_int(row[6]),
        'source_first_event_id': row[7],
        'source_latest_event_id': row[8],
        'persistence': _json_mapping(row[9]),
        'providers': _json_mapping(row[10]),
        'rag': _json_mapping(row[11]),
        'identity': _json_mapping(row[12]),
        'hermeneutic': _json_mapping(row[13]),
        'web': _json_mapping(row[14]),
        'documents': _json_mapping(row[15]),
        'biblio': _json_mapping(row[16]),
        'node_state': _json_mapping(row[17]),
        'latencies': _json_mapping(row[18]),
        'errors': _json_mapping(row[19]),
        'status_schema': _status_schema_from_flags(flags),
        'stage_counts': _json_mapping(row[20]),
        'flags': flags,
        'content_availability': _json_mapping(row[22]),
        'calculation_version': str(row[23] or ''),
        'materialized_ts': _iso(row[24]),
        'redaction': {'raw_content_included': False},
    }


def _turn_fact_select_sql() -> str:
    return '''
        SELECT
            conversation_id,
            turn_id,
            first_ts,
            latest_ts,
            classification,
            score,
            source_event_count,
            source_first_event_id,
            source_latest_event_id,
            persistence_json,
            providers_json,
            rag_json,
            identity_json,
            hermeneutic_json,
            web_json,
            documents_json,
            biblio_json,
            node_state_json,
            latencies_json,
            errors_json,
            stage_counts_json,
            flags_json,
            content_availability_json,
            calculation_version,
            materialized_ts
        FROM observability.dashboard_turn_facts
    '''


def _read_turn_events_for_content_gate(
    cur: Any,
    *,
    conversation_id: str,
    turn_id: str,
) -> tuple[list[dict[str, Any]], bool]:
    cur.execute(
        '''
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
        WHERE conversation_id = %s
          AND turn_id = %s
        ORDER BY ts ASC, event_id ASC
        LIMIT %s
        ''',
        (conversation_id, turn_id, _MAX_CONTENT_GATE_EVENTS + 1),
    )
    rows = cur.fetchall()
    events_truncated = len(rows) > _MAX_CONTENT_GATE_EVENTS
    events: list[dict[str, Any]] = []
    for row in rows[:_MAX_CONTENT_GATE_EVENTS]:
        payload_json = row[7]
        if not isinstance(payload_json, Mapping):
            payload_json = {}
        events.append(
            {
                'event_id': str(row[0] or ''),
                'conversation_id': str(row[1] or ''),
                'turn_id': str(row[2] or ''),
                'ts': _iso(row[3]),
                'stage': str(row[4] or ''),
                'status': str(row[5] or ''),
                'duration_ms': int(row[6]) if row[6] is not None else None,
                'payload': dict(payload_json),
            }
        )
    return events, events_truncated


build_source_status = _source_status
turn_fact_from_row = _turn_fact_row
