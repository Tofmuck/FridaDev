from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence
from urllib.parse import quote
import uuid

from observability import dashboard_analytics
from observability import dashboard_content_gate

RETENTION_DAYS = dashboard_analytics.RETENTION_DAYS
RECENT_GRANULARITY_DAYS = dashboard_analytics.RECENT_GRANULARITY_DAYS
CALCULATION_VERSION = dashboard_analytics.CALCULATION_VERSION

_DEFAULT_CONVERSATION_LIMIT = 50
_DEFAULT_TURN_LIMIT = 100
_MAX_LIMIT = 200
_MAX_CONTENT_GATE_EVENTS = 500
_NON_ADDITIVE_METRIC_SUFFIXES = ('_avg', '_p50', '_p95', '_median', '_rate')


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


def _empty_summary_health(*, status: str = 'degraded', reason_code: str = 'summary_health_unavailable') -> dict[str, Any]:
    return {
        'kind': 'dashboard_summary_health',
        'status': status,
        'reason_code': reason_code,
        'source_kind': 'durable_persistence',
        'summaries_total': 0,
        'summaries_with_text': 0,
        'summaries_with_embedding': 0,
        'traces_total': 0,
        'traces_with_summary_id': 0,
        'latest_summary_end_ts': None,
        'redaction': {'raw_content_included': False},
    }


def _read_summary_health(cur: Any) -> dict[str, Any]:
    try:
        cur.execute(
            '''
            SELECT
                'dashboard_summary_health' AS kind,
                (SELECT COUNT(*)::int FROM summaries) AS summaries_total,
                (
                    SELECT COUNT(*)::int
                    FROM summaries
                    WHERE NULLIF(btrim(content), '') IS NOT NULL
                ) AS summaries_with_text,
                (SELECT COUNT(*)::int FROM summaries WHERE embedding IS NOT NULL) AS summaries_with_embedding,
                (SELECT COUNT(*)::int FROM traces) AS traces_total,
                (SELECT COUNT(*)::int FROM traces WHERE summary_id IS NOT NULL) AS traces_with_summary_id,
                (SELECT MAX(end_ts) FROM summaries) AS latest_summary_end_ts
            '''
        )
        row = cur.fetchone()
    except Exception:
        return _empty_summary_health()
    if not row or str(row[0] or '') != 'dashboard_summary_health':
        return _empty_summary_health(reason_code='summary_health_row_missing')
    return {
        'kind': 'dashboard_summary_health',
        'status': 'ok',
        'reason_code': 'summary_health_read',
        'source_kind': 'durable_persistence',
        'summaries_total': _to_int(row[1]),
        'summaries_with_text': _to_int(row[2]),
        'summaries_with_embedding': _to_int(row[3]),
        'traces_total': _to_int(row[4]),
        'traces_with_summary_id': _to_int(row[5]),
        'latest_summary_end_ts': _iso(row[6]),
        'redaction': {'raw_content_included': False},
    }


def _merge_metric_value(target: dict[str, Any], key: str, value: Any) -> None:
    if key.startswith('_') or key.endswith(_NON_ADDITIVE_METRIC_SUFFIXES):
        return
    if isinstance(value, Mapping):
        current = target.setdefault(key, {})
        if isinstance(current, dict):
            for child_key, child_value in value.items():
                _merge_metric_value(current, str(child_key), child_value)
        return
    if isinstance(value, bool):
        target[key] = _to_int(target.get(key)) + (1 if value else 0)
        return
    if isinstance(value, int):
        target[key] = _to_int(target.get(key)) + value


def _aggregate_module_metrics(buckets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    modules: dict[str, dict[str, Any]] = {}
    for bucket in buckets:
        module_key = str(bucket.get('module_key') or '').strip()
        if not module_key:
            continue
        target = modules.setdefault(
            module_key,
            {
                'module_key': module_key,
                'turn_count': 0,
                'event_count': 0,
                'metrics': {},
            },
        )
        target['turn_count'] = _to_int(target.get('turn_count')) + _to_int(bucket.get('turn_count'))
        target['event_count'] = _to_int(target.get('event_count')) + _to_int(bucket.get('event_count'))
        metrics = _mapping(bucket.get('metrics'))
        for key, value in metrics.items():
            _merge_metric_value(target['metrics'], str(key), value)
    return dict(sorted(modules.items()))


def _provider_latency_summary(buckets: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    total_ms = 0
    count = 0
    bucket_p95_values: list[int] = []
    bucket_count = 0
    latest_bucket_avg_ms: int | None = None
    latest_bucket_p95_ms: int | None = None

    for bucket in sorted(buckets, key=lambda item: str(item.get('bucket_start') or '')):
        if str(bucket.get('module_key') or '') != 'providers':
            continue
        metrics = _mapping(bucket.get('metrics'))
        duration_total = _to_int(metrics.get('main_duration_ms_total'))
        duration_count = _to_int(metrics.get('main_duration_ms_count'))
        if duration_count > 0:
            total_ms += duration_total
            count += duration_count
            bucket_count += 1
            latest_bucket_avg_ms = int(round(duration_total / duration_count))
        p95 = metrics.get('main_duration_ms_p95')
        if p95 is not None:
            p95_int = _to_int(p95)
            bucket_p95_values.append(p95_int)
            latest_bucket_p95_ms = p95_int

    return {
        'kind': 'dashboard_provider_latency_summary',
        'label_fr': 'Latence modele principal',
        'source_kind': 'dashboard_metric_buckets.providers',
        'source_metrics': {
            'average': ('main_duration_ms_total', 'main_duration_ms_count'),
            'bucket_p95': 'main_duration_ms_p95',
        },
        'semantics_fr': (
            'La moyenne de fenetre est calculee depuis total/count des buckets providers. '
            'Les p50/p95 restent des valeurs par bucket; ils ne sont pas recomposes en p50/p95 de fenetre.'
        ),
        'main_duration_ms_avg': int(round(total_ms / count)) if count else None,
        'main_duration_ms_count': count,
        'bucket_count': bucket_count,
        'bucket_p95_ms_max': max(bucket_p95_values) if bucket_p95_values else None,
        'latest_bucket_avg_ms': latest_bucket_avg_ms,
        'latest_bucket_p95_ms': latest_bucket_p95_ms,
        'redaction': {'raw_content_included': False},
    }


def _pulse_from_modules(modules: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    pipeline = _mapping(_mapping(modules.get('pipeline')).get('metrics'))
    memory = _mapping(_mapping(modules.get('memory')).get('metrics'))
    web = _mapping(_mapping(modules.get('web')).get('metrics'))
    errors = _mapping(_mapping(modules.get('errors')).get('metrics'))
    persistence = _mapping(_mapping(modules.get('persistence')).get('metrics'))
    return {
        'label_fr': 'Pouls global',
        'turns_observed': _to_int(_mapping(modules.get('pipeline')).get('turn_count')),
        'classification_counts': _json_mapping(pipeline.get('classification_counts')),
        'responses_saved': _to_int(persistence.get('assistant_final_saved_count')),
        'memory_injected_total': _to_int(memory.get('injected_total')),
        'web_requested_turns': _to_int(web.get('requested_turns')),
        'web_injected_turns': _to_int(web.get('injected_turns')),
        'problems_count': _to_int(errors.get('error_count')) + _to_int(errors.get('fallback_count')),
    }


def read_dashboard_overview(
    params: Mapping[str, Any] | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    window = resolve_dashboard_window(params, now=now)
    module_catalog = dashboard_analytics.build_dashboard_module_catalog(include_future=True)
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                status = _read_materialization_status(cur)
                buckets = _read_metric_buckets(cur, window)
                summary_health = _read_summary_health(cur)
    except Exception as exc:
        logger_instance.error('dashboard_overview_read_failed err=%s', exc)
        return {
            'kind': 'dashboard_overview',
            'window': window,
            'pulse': {
                'label_fr': 'Pouls global',
                'turns_observed': 0,
                'classification_counts': {},
                'responses_saved': 0,
                'memory_injected_total': 0,
                'web_requested_turns': 0,
                'web_injected_turns': 0,
                'problems_count': 0,
            },
            'module_catalog': module_catalog,
            'module_totals': {},
            'metric_buckets': [],
            'latency': _provider_latency_summary([]),
            'summaries_health': _empty_summary_health(),
            'source': _source_status(window, None, degraded_reason=exc.__class__.__name__),
            'redaction': {'raw_content_included': False},
        }

    module_totals = _aggregate_module_metrics(buckets)
    return {
        'kind': 'dashboard_overview',
        'window': window,
        'pulse': _pulse_from_modules(module_totals),
        'module_catalog': module_catalog,
        'module_totals': module_totals,
        'metric_buckets': buckets,
        'latency': _provider_latency_summary(buckets),
        'summaries_health': summary_health,
        'source': _source_status(window, status),
        'redaction': {'raw_content_included': False},
    }


def _conversation_summary_from_facts(rows: Sequence[Sequence[Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    first = rows[0]
    conversation_id = str(first[0] or '')
    display_label = str(first[1] or '') or 'Conversation sans date'
    display_label_source = str(first[2] or '') or 'fallback'
    latest_ts = _iso(max(row[4] for row in rows if row[4] is not None)) if any(row[4] is not None for row in rows) else None
    first_ts = _iso(min(row[3] for row in rows if row[3] is not None)) if any(row[3] is not None for row in rows) else None
    classification_counts: dict[str, int] = {}
    memory_used_turns = 0
    web_requested_turns = 0
    web_injected_turns = 0
    documents_active_turns = 0
    documents_injected_total = 0
    documents_not_injected_total = 0
    error_count = 0
    fallback_count = 0
    last_turn_id = None
    for row in sorted(rows, key=lambda item: str(_iso(item[4]) or '')):
        classification = str(row[6] or 'legacy_incomplete')
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        last_turn_id = str(row[5] or '') or last_turn_id
        rag = _mapping(row[7])
        web = _mapping(row[8])
        documents = _mapping(row[9])
        errors = _mapping(row[10])
        if _to_int(rag.get('injected')) > 0 or _to_int(rag.get('retrieved')) > 0:
            memory_used_turns += 1
        if bool(web.get('requested')):
            web_requested_turns += 1
        if bool(web.get('injected')):
            web_injected_turns += 1
        if _to_int(documents.get('active_count')) > 0:
            documents_active_turns += 1
        documents_injected_total += _to_int(documents.get('injected_count'))
        documents_not_injected_total += _to_int(documents.get('not_injected_count'))
        error_count += _to_int(errors.get('error_count'))
        fallback_count += _to_int(errors.get('fallback_count'))
    return {
        'conversation_id': conversation_id,
        'display_label': display_label,
        'display_label_source': display_label_source,
        'first_ts': first_ts,
        'latest_ts': latest_ts,
        'turns_count': len(rows),
        'last_turn_id': last_turn_id,
        'classification_counts': dict(sorted(classification_counts.items())),
        'memory_used_turns': memory_used_turns,
        'web_requested_turns': web_requested_turns,
        'web_injected_turns': web_injected_turns,
        'documents_active_turns': documents_active_turns,
        'documents_injected_total': documents_injected_total,
        'documents_not_injected_total': documents_not_injected_total,
        'error_count': error_count,
        'fallback_count': fallback_count,
        'redaction': {'raw_content_included': False},
    }


def read_dashboard_conversations(
    params: Mapping[str, Any] | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    window = resolve_dashboard_window(params, now=now)
    limit, offset = _limit_offset(params, default_limit=_DEFAULT_CONVERSATION_LIMIT)
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                status = _read_materialization_status(cur)
                cur.execute(
                    '''
                    SELECT
                        f.conversation_id,
                        COALESCE(s.display_label, 'Conversation sans date') AS display_label,
                        COALESCE(s.display_label_source, 'fallback_missing_summary') AS display_label_source,
                        f.first_ts,
                        f.latest_ts,
                        f.turn_id,
                        f.classification,
                        f.rag_json,
                        f.web_json,
                        f.documents_json,
                        f.errors_json
                    FROM observability.dashboard_turn_facts AS f
                    LEFT JOIN observability.dashboard_conversation_summaries AS s
                      ON s.conversation_id = f.conversation_id
                    WHERE f.latest_ts >= %s::timestamptz
                      AND f.latest_ts < %s::timestamptz
                    ORDER BY f.conversation_id ASC, f.latest_ts ASC
                    ''',
                    (window['start'], window['end']),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger_instance.error('dashboard_conversations_read_failed err=%s', exc)
        return {
            'kind': 'dashboard_conversations',
            'window': window,
            'items': [],
            'count': 0,
            'total': 0,
            'limit': limit,
            'offset': offset,
            'next_offset': None,
            'source': _source_status(window, None, degraded_reason=exc.__class__.__name__),
            'redaction': {'raw_content_included': False},
        }

    grouped: dict[str, list[Sequence[Any]]] = {}
    for row in rows:
        grouped.setdefault(str(row[0] or ''), []).append(row)
    all_items = [
        _conversation_summary_from_facts(group_rows)
        for _, group_rows in sorted(grouped.items())
    ]
    all_items = sorted(all_items, key=lambda item: str(item.get('latest_ts') or ''), reverse=True)
    sliced = all_items[offset:offset + limit]
    next_offset = offset + len(sliced)
    if next_offset >= len(all_items):
        next_offset = None
    return {
        'kind': 'dashboard_conversations',
        'window': window,
        'items': sliced,
        'count': len(sliced),
        'total': len(all_items),
        'limit': limit,
        'offset': offset,
        'next_offset': next_offset,
        'source': _source_status(window, status),
        'redaction': {'raw_content_included': False},
    }


def _turn_fact_row(row: Sequence[Any]) -> dict[str, Any]:
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
        'node_state': _json_mapping(row[16]),
        'latencies': _json_mapping(row[17]),
        'errors': _json_mapping(row[18]),
        'stage_counts': _json_mapping(row[19]),
        'flags': _json_mapping(row[20]),
        'content_availability': _json_mapping(row[21]),
        'calculation_version': str(row[22] or ''),
        'materialized_ts': _iso(row[23]),
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


def read_dashboard_conversation_turns(
    conversation_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    conversation_id_s = str(conversation_id or '').strip()
    if not conversation_id_s:
        raise ValueError('conversation_id is required')
    window = resolve_dashboard_window(params, now=now)
    limit, offset = _limit_offset(params, default_limit=_DEFAULT_TURN_LIMIT)
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                status = _read_materialization_status(cur)
                cur.execute(
                    '''
                    SELECT COUNT(*)::int
                    FROM observability.dashboard_turn_facts
                    WHERE conversation_id = %s
                      AND latest_ts >= %s::timestamptz
                      AND latest_ts < %s::timestamptz
                    ''',
                    (conversation_id_s, window['start'], window['end']),
                )
                total = _to_int((cur.fetchone() or [0])[0])
                cur.execute(
                    _turn_fact_select_sql()
                    + '''
                    WHERE conversation_id = %s
                      AND latest_ts >= %s::timestamptz
                      AND latest_ts < %s::timestamptz
                    ORDER BY latest_ts DESC, turn_id DESC
                    LIMIT %s OFFSET %s
                    ''',
                    (conversation_id_s, window['start'], window['end'], limit, offset),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger_instance.error('dashboard_conversation_turns_read_failed err=%s', exc)
        return {
            'kind': 'dashboard_conversation_turns',
            'conversation_id': conversation_id_s,
            'window': window,
            'items': [],
            'count': 0,
            'total': 0,
            'limit': limit,
            'offset': offset,
            'next_offset': None,
            'source': _source_status(window, None, degraded_reason=exc.__class__.__name__),
            'redaction': {'raw_content_included': False},
        }

    items = [_turn_fact_row(row) for row in rows]
    next_offset = offset + len(items)
    if next_offset >= total:
        next_offset = None
    return {
        'kind': 'dashboard_conversation_turns',
        'conversation_id': conversation_id_s,
        'window': window,
        'items': items,
        'count': len(items),
        'total': total,
        'limit': limit,
        'offset': offset,
        'next_offset': next_offset,
        'source': _source_status(window, status),
        'redaction': {'raw_content_included': False},
    }


def _translated_inspection(fact: Mapping[str, Any]) -> list[dict[str, Any]]:
    modules = []
    for module in dashboard_analytics.observable_modules():
        reason_code = dashboard_analytics.resolve_module_turn_degradation_reason(
            module.module_key,
            fact,
        )
        modules.append(
            {
                'module_key': module.module_key,
                'label_fr': module.label_fr,
                'summary_fr': dashboard_analytics.summarize_module_turn(module.module_key, fact),
                'degradation_fr': (
                    dashboard_analytics.explain_module_degradation(
                        module.module_key,
                        reason_code=reason_code,
                    )
                    if reason_code
                    else None
                ),
                'raw_content_available': False,
                'proof_level': 'compact_summary',
                'content_status_fr': (
                    'Le contenu complet n est pas charge dans cette inspection; '
                    'seuls les faits compacts materialises sont utilises.'
                ),
            }
        )
    return modules


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


def _audit_content_gate_open(
    *,
    fact: Mapping[str, Any],
    payload: Mapping[str, Any],
    audit_fn: Callable[..., bool] | None,
    logger_instance: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    if audit_fn is None:
        return {
            'attempted': False,
            'stored': False,
            'reason_code': 'audit_fn_missing',
            'raw_content_included': False,
        }
    event = {
        'event_id': f"{fact.get('turn_id')}:dashboard_content_gate:{uuid.uuid4().hex[:12]}",
        'conversation_id': str(fact.get('conversation_id') or ''),
        'turn_id': str(fact.get('turn_id') or ''),
        'ts': (now or datetime.now(timezone.utc)).astimezone(timezone.utc).isoformat(),
        'stage': 'dashboard_content_gate',
        'status': 'ok',
        'duration_ms': None,
        'payload_json': dashboard_content_gate.audit_payload_for_content_gate(payload),
    }
    try:
        stored = bool(audit_fn(event))
    except Exception as exc:
        logger_instance.error('dashboard_content_gate_audit_failed err=%s', exc)
        stored = False
    return {
        'attempted': True,
        'stored': stored,
        'stage': 'dashboard_content_gate',
        'raw_content_included': False,
    }


def _classification_fr(value: Any) -> str:
    labels = {
        'complete': 'reussi',
        'degraded': 'degrade',
        'partial': 'partiel',
        'legacy_incomplete': 'historique incomplet',
    }
    return labels.get(str(value or '').strip().lower(), 'a verifier')


def _status_fr(value: Any) -> str:
    labels = {
        'ok': 'reussi',
        'success': 'reussi',
        'saved': 'sauvegarde',
        'complete': 'complet',
        'degraded': 'degrade',
        'partial': 'partiel',
        'legacy_incomplete': 'historique incomplet',
        'error': 'en erreur',
        'failed': 'en erreur',
        'skipped': 'ignore',
        'not_applicable': 'non utilise',
        'missing': 'non observe',
        'unknown': 'a verifier',
    }
    return labels.get(str(value or '').strip().lower(), 'a verifier')


def _yes_no(value: Any) -> str:
    return 'oui' if bool(value) else 'non'


_REASON_CODE_LABELS = {
    'assistant_final_not_saved': 'reponse finale non sauvegardee',
    'assistant_final_saved': 'reponse finale sauvegardee',
    'assistant_interrupted': 'reponse interrompue',
    'identity_block_absent': 'bloc identite absent',
    'memory_chain_snapshot_missing': 'chaine memoire non observee',
    'missing_assistant_final_persist': 'sauvegarde finale non observee',
    'missing_main_llm_call': 'appel du modele principal non observe',
    'missing_memory_chain_snapshot': 'chaine memoire non observee',
    'missing_secondary_provider_prepared': 'preparation d un modele secondaire non observee',
    'no_data': 'donnee absente',
    'not_applicable': 'module non utilise',
    'provider_missing': 'modele attendu non observe',
    'retrieve_error': 'recherche memoire en erreur',
    'runtime_error': 'erreur runtime',
    'timeout': 'delai depasse',
    'validation_error': 'validation en erreur',
    'validation_fail_open': 'validation ouverte par securite',
    'document_too_large_for_turn': 'document actif trop gros pour ce tour',
    'document_empty_text': 'document actif sans texte injectable',
}


def _reason_codes_fr(errors: Mapping[str, Any]) -> str:
    reason_counts = _mapping(errors.get('reason_code_counts'))
    if not reason_counts:
        return 'aucune cause compacte observee'
    parts: list[str] = []
    unknown_total = 0
    for reason, count in sorted(reason_counts.items(), key=lambda item: str(item[0])):
        amount = _to_int(count)
        label = _REASON_CODE_LABELS.get(str(reason or '').strip())
        if label:
            parts.append(f'{label}: {amount}')
        else:
            unknown_total += amount
    if unknown_total:
        parts.append(
            f'{unknown_total} cause(s) technique(s) compacte(s) non traduite(s); '
            'detail disponible dans les logs techniques'
        )
    return ', '.join(parts)


def _summary_parent_line(rag: Mapping[str, Any]) -> str:
    traces_with_summary_id = _to_int(rag.get('injected_traces_with_summary_id_count'))
    parent_injected_count = _to_int(rag.get('parent_summaries_injected_count'))
    legacy_parent_count = _to_int(rag.get('memory_context_summary_count'))
    parent_summaries = [
        _mapping(item)
        for item in (rag.get('parent_summaries_injected') or [])
        if isinstance(item, Mapping)
    ]
    if traces_with_summary_id <= 0 and parent_injected_count <= 0:
        if legacy_parent_count > 0:
            return (
                f'{legacy_parent_count} resume(s) parent(s) ont accompagne la memoire injectee, '
                'mais le lien trace -> summary_id -> fenetre du resume parent n est pas materialise '
                'dans ces faits compacts.'
            )
        return (
            'Aucune trace memoire injectee avec summary_id parent n est prouvee dans ces faits compacts.'
        )
    if parent_injected_count <= 0:
        return (
            f'{traces_with_summary_id} trace(s) memoire injectee(s) portent un summary_id, '
            'mais aucun resume parent injecte correspondant n est prouve dans ces faits compacts.'
        )

    windows: list[str] = []
    for item in parent_summaries[:3]:
        proof = str(item.get('summary_id_sha256_12') or item.get('summary_id') or 'id non materialise')
        start_ts = _iso(item.get('start_ts')) or str(item.get('start_ts') or '').strip() or 'debut inconnu'
        end_ts = _iso(item.get('end_ts')) or str(item.get('end_ts') or '').strip() or 'fin inconnue'
        linked = _to_int(item.get('linked_trace_count'))
        windows.append(f'{proof}: {start_ts} -> {end_ts}, {linked} trace(s) liee(s)')
    suffix = ''
    if len(parent_summaries) > 3:
        suffix = f'; {len(parent_summaries) - 3} resume(s) parent(s) supplementaire(s) non detaille(s)'
    detail = '; '.join(windows) if windows else 'fenetres non materialisees'
    return (
        f'{traces_with_summary_id} trace(s) memoire injectee(s) etaient liee(s) a un summary_id; '
        f'{parent_injected_count} resume(s) parent(s) correspondant(s) ont ete injecte(s) avec ces traces. '
        f'Fenetres: {detail}{suffix}.'
    )


def _first_present_int(mapping: Mapping[str, Any], *keys: str) -> tuple[int, bool]:
    for key in keys:
        if key in mapping:
            return _to_int(mapping.get(key)), True
    return 0, False


def _debug_links(fact: Mapping[str, Any]) -> list[dict[str, str]]:
    conversation_id = quote(str(fact.get('conversation_id') or ''), safe='')
    turn_id = quote(str(fact.get('turn_id') or ''), safe='')
    query = f'conversation_id={conversation_id}&turn_id={turn_id}'
    return [
        {'label_fr': 'Logs techniques', 'href': f'/log?{query}'},
        {'label_fr': 'Memory Admin', 'href': '/memory-admin'},
        {'label_fr': 'Hermeneutic Admin', 'href': '/hermeneutic-admin'},
        {'label_fr': 'Identity', 'href': '/identity'},
    ]


def _document_story_lines(documents: Mapping[str, Any]) -> list[str]:
    active_count = _to_int(documents.get('active_count'))
    injected_count = _to_int(documents.get('injected_count'))
    not_injected_count = _to_int(documents.get('not_injected_count'))
    if active_count <= 0:
        return ['Aucun document actif de conversation n est observe sur ce tour.']

    lines = [
        f'{active_count} document(s) actif(s) de conversation observe(s).',
        f'{injected_count} document(s) envoye(s) entiers au modele.',
        f'{not_injected_count} document(s) non envoye(s) dans ce tour.',
    ]
    for item in [
        _mapping(raw_item)
        for raw_item in (documents.get('documents') or [])
        if isinstance(raw_item, Mapping)
    ][:5]:
        filename = str(item.get('filename') or 'document')
        ext = str(item.get('source_extension') or '').strip()
        reason = str(item.get('reason_code') or '').strip()
        if item.get('injected'):
            status = 'envoye entier'
        elif reason == 'document_too_large_for_turn':
            status = 'non envoye: trop gros pour ce tour'
        elif reason:
            status = f'non envoye: {_REASON_CODE_LABELS.get(reason, "raison compacte disponible")}'
        else:
            status = 'non envoye'
        lines.append(
            f'{filename} ({ext or "type inconnu"}, {_to_int(item.get("byte_size"))} octets, '
            f'{_to_int(item.get("text_chars"))} caracteres): {status}.'
        )
    if active_count > 5:
        lines.append(f'{active_count - 5} document(s) supplementaire(s) non detaille(s).')
    lines.append('Aucun texte de document actif n est affiche dans cette inspection ordinaire.')
    return lines


def _turn_story(fact: Mapping[str, Any]) -> dict[str, Any]:
    rag = _mapping(fact.get('rag'))
    providers = _mapping(fact.get('providers'))
    main_provider = _mapping(providers.get('main'))
    secondary = _mapping(providers.get('secondary'))
    identity = _mapping(fact.get('identity'))
    hermeneutic = _mapping(fact.get('hermeneutic'))
    web = _mapping(fact.get('web'))
    documents = _mapping(fact.get('documents'))
    node_state = _mapping(fact.get('node_state'))
    persistence = _mapping(fact.get('persistence'))
    errors = _mapping(fact.get('errors'))
    flags = _mapping(fact.get('flags'))
    content_availability = _mapping(fact.get('content_availability'))
    classification = str(fact.get('classification') or 'legacy_incomplete')
    source_event_count = _to_int(fact.get('source_event_count'))

    context_parts: list[str] = []
    if identity.get('block_present'):
        context_parts.append(f"un bloc identite ({_to_int(identity.get('chars'))} caracteres observes)")
    else:
        context_parts.append('pas de bloc identite observe')
    if _to_int(rag.get('injected')) > 0:
        context_parts.append(f"{_to_int(rag.get('injected'))} element(s) memoire injecte(s)")
    else:
        context_parts.append('aucun element memoire injecte observe')
    summary_active = bool(rag.get('conversation_summary_active_present'))
    summary_in_prompt = bool(rag.get('conversation_summary_in_prompt'))
    summary_count = _to_int(rag.get('conversation_summary_count'))
    if summary_active and summary_in_prompt:
        context_parts.append('un resume actif de conversation injecte')
        summary_line = f'Resume de conversation present et injecte ({summary_count or 1} resume observe).'
    elif summary_active:
        context_parts.append('un resume actif de conversation non injecte')
        summary_line = 'Resume de conversation actif observe, mais non injecte dans le prompt principal.'
    elif rag.get('conversation_summary_event_present') is True:
        context_parts.append('aucun resume actif de conversation observe')
        summary_line = 'Aucun resume de conversation actif sur ce tour.'
    else:
        context_parts.append('etat du resume de conversation non materialise')
        summary_line = 'Etat du resume de conversation non materialise dans ces faits compacts.'
    parent_summary_line = _summary_parent_line(rag)
    if hermeneutic.get('block_present'):
        context_parts.append('un jugement hermeneutique observe')
    else:
        context_parts.append('pas de jugement hermeneutique observe')
    if web.get('injected'):
        context_parts.append('un contexte web injecte')
    else:
        context_parts.append('pas de contexte web injecte observe')
    if _to_int(documents.get('injected_count')) > 0:
        context_parts.append(f"{_to_int(documents.get('injected_count'))} document(s) actif(s) injecte(s) entier(s)")
    elif _to_int(documents.get('active_count')) > 0:
        context_parts.append('document actif observe mais non injecte')
    else:
        context_parts.append('pas de document actif observe')

    embeddings_requested, embeddings_requested_present = _first_present_int(
        rag,
        'embeddings_requested',
        'embedding_requested_count',
        'embeddings_requested_count',
    )
    embeddings_succeeded, embeddings_succeeded_present = _first_present_int(
        rag,
        'embeddings_succeeded',
        'embedding_success_count',
        'embeddings_success_count',
    )
    if embeddings_requested_present or embeddings_succeeded_present:
        embeddings_line = f'{embeddings_requested} embeddings demandes, {embeddings_succeeded} reussis.'
    else:
        embeddings_line = (
            'Aucun compteur embeddings n est disponible dans cette synthese; '
            'aucun vecteur ni bloc massif n est affiche.'
        )

    proof_lines = [
        (
            'Le tour est materialise depuis '
            f'{source_event_count} etape(s) compacte(s); le texte exact recu par Frida n est pas affiche ici.'
        ),
        (
            'Le contexte modele exact n est pas reconstructible depuis ces seuls faits compacts '
            'quand seuls presence, counts, longueurs ou hashes sont disponibles.'
        ),
        (
            'Le contenu complet n est pas precharge ici; il peut etre demande volontairement '
            'avec l action Afficher le contenu complet.'
        ),
    ]
    if content_availability:
        prompt_manifest_available = bool(content_availability.get('prompt_manifest_available'))
        proof_lines.append(
            'Manifeste de prompt disponible: '
            f'{_yes_no(prompt_manifest_available)}.'
        )
    if bool(flags.get('events_truncated')):
        proof_lines.append('La trace source du tour est signalee comme tronquee.')

    sections = [
        {
            'key': 'received',
            'label_fr': 'Ce que Frida a recu',
            'items': [
                'Une demande utilisateur est representee par ce tour.',
                'La lecture reste traduite et sans contenu brut: le texte exact de la demande n est pas affiche.',
            ],
        },
        {
            'key': 'pipeline',
            'label_fr': 'Parcours du tour',
            'items': [
                f"Etat du tour: {_classification_fr(classification)}.",
                f"Score de completude: {_to_int(fact.get('score'))}.",
                f"Etapes compactes observees: {source_event_count}.",
                f"Reponse finale sauvegardee: {_yes_no(persistence.get('assistant_final_saved'))}.",
                f"Reponse interrompue: {_yes_no(persistence.get('assistant_interrupted'))}.",
            ],
        },
        {
            'key': 'model_context',
            'label_fr': 'Ce que le modele a recu, en lecture traduite',
            'items': [
                'Composition compacte observee: ' + '; '.join(context_parts) + '.',
                f"Modele principal observe: {_yes_no(main_provider.get('present'))}; etat: {_status_fr(main_provider.get('status'))}.",
                f"Modeles secondaires consultes: {_to_int(sum(_to_int(_mapping(item).get('llm_call_events_count')) for item in secondary.values()))}.",
            ],
        },
        {
            'key': 'modules',
            'label_fr': 'Modules',
            'items': [
                (
                    f"Memoire: {_to_int(rag.get('retrieved'))} trouve(s), "
                    f"{_to_int(rag.get('basket'))} candidat(s), {_to_int(rag.get('kept'))} garde(s), "
                    f"{_to_int(rag.get('rejected'))} rejete(s), {_to_int(rag.get('injected'))} injecte(s)."
                ),
                summary_line,
                parent_summary_line,
                f"Identite: bloc present {_yes_no(identity.get('block_present'))}, etat {_status_fr(identity.get('status'))}.",
                f"Hermeneutique: jugement present {_yes_no(hermeneutic.get('block_present'))}, fallback {_yes_no(hermeneutic.get('fallback'))}.",
                (
                    f"Node state: relu {_yes_no(node_state.get('read_present'))}, "
                    f"lecture valide {_yes_no(node_state.get('read_valid'))}, "
                    f"ecriture tentee {_yes_no(node_state.get('write_attempted'))}, "
                    f"ecriture reussie {_yes_no(node_state.get('write_succeeded'))}."
                ),
                (
                    f"Web: demande {_yes_no(web.get('requested'))}, reussi {_yes_no(web.get('success'))}, "
                    f"injecte {_yes_no(web.get('injected'))}, resultats comptes {_to_int(web.get('results_count'))}."
                ),
                *_document_story_lines(documents),
                f"Persistence: etat {_status_fr(persistence.get('status'))}.",
            ],
        },
        {
            'key': 'problems',
            'label_fr': 'Problemes et degradations',
            'items': [
                f"Erreurs compactes: {_to_int(errors.get('error_count'))}.",
                f"Skips compacts: {_to_int(errors.get('skipped_count'))}.",
                f"Fallbacks compacts: {_to_int(errors.get('fallback_count'))}.",
                f"Causes compactes: {_reason_codes_fr(errors)}.",
            ],
        },
        {
            'key': 'massive_data',
            'label_fr': 'Donnees massives resumees',
            'items': [
                embeddings_line,
                'Les grands blocs, vecteurs, contenus complets des modeles, textes memoire, identite et web ne sont pas dumps dans cette inspection.',
            ],
        },
        {
            'key': 'proof_limits',
            'label_fr': 'Preuves et limites',
            'items': proof_lines,
        },
    ]
    return {
        'kind': 'dashboard_turn_story',
        'title_fr': 'Inspection traduite du tour',
        'summary_fr': (
            f"Tour {_classification_fr(classification)} avec {_to_int(errors.get('error_count'))} erreur(s) "
            f"et {_to_int(errors.get('fallback_count'))} fallback(s) compacts."
        ),
        'sections': sections,
        'debug_links': _debug_links(fact),
        'proof_level': 'translated_compact_inspection',
        'content_status_fr': (
            'Contenu complet non charge; utilisez Afficher le contenu complet pour verifier ce qui est '
            'disponible, partiel, seulement prouve par empreinte, ou non reconstructible.'
        ),
        'redaction': {'raw_content_included': False},
    }


def read_dashboard_turn_inspection(
    turn_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    now: datetime | None = None,
) -> dict[str, Any]:
    turn_id_s = str(turn_id or '').strip()
    if not turn_id_s:
        raise ValueError('turn_id is required')
    conversation_id_s = _params_get(params, 'conversation_id') or None
    window = resolve_dashboard_window(params, now=now)
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                status = _read_materialization_status(cur)
                where = ['turn_id = %s', 'latest_ts >= %s::timestamptz', 'latest_ts < %s::timestamptz']
                query_params: list[Any] = [turn_id_s, window['start'], window['end']]
                if conversation_id_s:
                    where.insert(0, 'conversation_id = %s')
                    query_params.insert(0, conversation_id_s)
                cur.execute(
                    _turn_fact_select_sql()
                    + f'''
                    WHERE {' AND '.join(where)}
                    ORDER BY latest_ts DESC, conversation_id ASC
                    LIMIT 2
                    ''',
                    tuple(query_params),
                )
                rows = cur.fetchall()
    except Exception as exc:
        logger_instance.error('dashboard_turn_inspection_read_failed err=%s', exc)
        return {
            'kind': 'dashboard_turn_inspection',
            'turn_id': turn_id_s,
            'conversation_id': conversation_id_s,
            'window': window,
            'item': None,
            'modules': [],
            'source': _source_status(window, None, degraded_reason=exc.__class__.__name__),
            'redaction': {'raw_content_included': False},
        }

    if not rows:
        raise LookupError('dashboard turn not found')
    if not conversation_id_s and len(rows) > 1:
        raise ValueError('conversation_id is required when turn_id is ambiguous')
    fact = _turn_fact_row(rows[0])
    return {
        'kind': 'dashboard_turn_inspection',
        'turn_id': turn_id_s,
        'conversation_id': fact['conversation_id'],
        'window': window,
        'item': fact,
        'modules': _translated_inspection(fact),
        'story': _turn_story(fact),
        'content_gate': dashboard_content_gate.content_gate_summary(fact),
        'source': _source_status(window, status),
        'redaction': {'raw_content_included': False},
    }


def read_dashboard_turn_content(
    turn_id: str,
    params: Mapping[str, Any] | None = None,
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
    audit_fn: Callable[..., bool] | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    turn_id_s = str(turn_id or '').strip()
    if not turn_id_s:
        raise ValueError('turn_id is required')
    conversation_id_s = _params_get(params, 'conversation_id') or None
    window = resolve_dashboard_window(params, now=now)
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                status = _read_materialization_status(cur)
                where = ['turn_id = %s', 'latest_ts >= %s::timestamptz', 'latest_ts < %s::timestamptz']
                query_params: list[Any] = [turn_id_s, window['start'], window['end']]
                if conversation_id_s:
                    where.insert(0, 'conversation_id = %s')
                    query_params.insert(0, conversation_id_s)
                cur.execute(
                    _turn_fact_select_sql()
                    + f'''
                    WHERE {' AND '.join(where)}
                    ORDER BY latest_ts DESC, conversation_id ASC
                    LIMIT 2
                    ''',
                    tuple(query_params),
                )
                rows = cur.fetchall()
                if not rows:
                    raise LookupError('dashboard turn not found')
                if not conversation_id_s and len(rows) > 1:
                    raise ValueError('conversation_id is required when turn_id is ambiguous')
                fact = _turn_fact_row(rows[0])
                events, events_truncated = _read_turn_events_for_content_gate(
                    cur,
                    conversation_id=str(fact.get('conversation_id') or ''),
                    turn_id=str(fact.get('turn_id') or ''),
                )
    except LookupError:
        raise
    except ValueError:
        raise
    except Exception as exc:
        logger_instance.error('dashboard_turn_content_gate_read_failed err=%s', exc)
        return {
            'kind': 'dashboard_turn_content_gate',
            'turn_id': turn_id_s,
            'conversation_id': conversation_id_s,
            'window': window,
            'availability': {
                'status': 'not_reconstructible',
                'status_fr': 'non reconstructible',
                'status_counts': {},
                'loaded_after_explicit_action': True,
                'preloaded': False,
                'events_truncated': False,
                'warning_fr': 'Lecture degradee: impossible de lire les evenements sources.',
            },
            'items': [],
            'source': _source_status(window, None, degraded_reason=exc.__class__.__name__),
            'audit': {'attempted': False, 'stored': False, 'reason_code': 'read_failed', 'raw_content_included': False},
            'redaction': {'raw_content_included': False, 'secret_blocked_count': 0},
        }

    payload = dashboard_content_gate.build_content_gate_payload(
        fact=fact,
        events=events,
        events_truncated=events_truncated,
    )
    payload['window'] = window
    payload['source'] = _source_status(window, status)
    payload['audit'] = _audit_content_gate_open(
        fact=fact,
        payload=payload,
        audit_fn=audit_fn,
        logger_instance=logger_instance,
        now=now,
    )
    return payload
