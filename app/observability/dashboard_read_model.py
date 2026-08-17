from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence
import uuid

from observability import dashboard_analytics
from observability import dashboard_content_gate
from observability.dashboard_read_model_inspection import (
    _document_story_lines,
    _translated_inspection,
    _turn_story,
)
from observability.dashboard_read_model_overview import (
    _aggregate_module_metrics,
    _conversation_summary_from_facts,
    _empty_summary_health,
    _provider_latency_summary,
    _pulse_from_modules,
    _read_summary_health,
)
from observability.dashboard_read_model_query import (
    CALCULATION_VERSION,
    RECENT_GRANULARITY_DAYS,
    RETENTION_DAYS,
    _MAX_CONTENT_GATE_EVENTS,
    _limit_offset,
    _params_get,
    _read_materialization_status,
    _read_metric_buckets,
    _read_turn_events_for_content_gate,
    _source_status,
    _to_int,
    _turn_fact_row,
    _turn_fact_select_sql,
    resolve_dashboard_window,
)

_DEFAULT_CONVERSATION_LIMIT = 50
_DEFAULT_TURN_LIMIT = 100


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
        logger_instance.error(
            'dashboard_overview_read_failed reason=dashboard_overview_read_exception err_class=%s',
            exc.__class__.__name__,
        )
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
                        f.biblio_json,
                        f.errors_json,
                        f.flags_json
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
        logger_instance.error(
            'dashboard_conversations_read_failed reason=dashboard_conversations_read_exception err_class=%s',
            exc.__class__.__name__,
        )
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
        logger_instance.error(
            'dashboard_conversation_turns_read_failed reason=dashboard_conversation_turns_read_exception err_class=%s',
            exc.__class__.__name__,
        )
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
        logger_instance.error(
            'dashboard_content_gate_audit_failed reason=dashboard_content_gate_audit_exception err_class=%s',
            exc.__class__.__name__,
        )
        stored = False
    return {
        'attempted': True,
        'stored': stored,
        'stage': 'dashboard_content_gate',
        'raw_content_included': False,
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
        logger_instance.error(
            'dashboard_turn_inspection_read_failed reason=dashboard_turn_inspection_read_exception err_class=%s',
            exc.__class__.__name__,
        )
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
        logger_instance.error(
            'dashboard_turn_content_gate_read_failed reason=dashboard_turn_content_gate_read_exception err_class=%s',
            exc.__class__.__name__,
        )
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
