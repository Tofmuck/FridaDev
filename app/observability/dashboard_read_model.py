from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from observability import dashboard_analytics

RETENTION_DAYS = dashboard_analytics.RETENTION_DAYS
RECENT_GRANULARITY_DAYS = dashboard_analytics.RECENT_GRANULARITY_DAYS
CALCULATION_VERSION = dashboard_analytics.CALCULATION_VERSION

_DEFAULT_CONVERSATION_LIMIT = 50
_DEFAULT_TURN_LIMIT = 100
_MAX_LIMIT = 200
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


def _source_status(
    window: Mapping[str, Any],
    status: Mapping[str, Any] | None,
    *,
    degraded_reason: str | None = None,
) -> dict[str, Any]:
    materialization = dict(status or {})
    return {
        'kind': 'dashboard_source_status',
        'status': 'degraded' if degraded_reason else str(materialization.get('status') or 'empty'),
        'degraded_reason': degraded_reason,
        'window': dict(window),
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
    error_count = 0
    fallback_count = 0
    last_turn_id = None
    for row in sorted(rows, key=lambda item: str(_iso(item[4]) or '')):
        classification = str(row[6] or 'legacy_incomplete')
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        last_turn_id = str(row[5] or '') or last_turn_id
        rag = _mapping(row[7])
        web = _mapping(row[8])
        errors = _mapping(row[9])
        if _to_int(rag.get('injected')) > 0 or _to_int(rag.get('retrieved')) > 0:
            memory_used_turns += 1
        if bool(web.get('requested')):
            web_requested_turns += 1
        if bool(web.get('injected')):
            web_injected_turns += 1
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
        'node_state': _json_mapping(row[15]),
        'latencies': _json_mapping(row[16]),
        'errors': _json_mapping(row[17]),
        'stage_counts': _json_mapping(row[18]),
        'flags': _json_mapping(row[19]),
        'content_availability': _json_mapping(row[20]),
        'calculation_version': str(row[21] or ''),
        'materialized_ts': _iso(row[22]),
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


def _module_sentence(module_key: str, fact: Mapping[str, Any]) -> str:
    if module_key == 'pipeline':
        return f"Le tour est classe {fact.get('classification') or 'inconnu'} avec un score de {fact.get('score') or 0}."
    if module_key == 'persistence':
        persistence = _mapping(fact.get('persistence'))
        if persistence.get('assistant_final_saved'):
            return 'La reponse finale assistant est sauvegardee.'
        return 'La sauvegarde finale assistant n est pas confirmee.'
    if module_key == 'memory':
        rag = _mapping(fact.get('rag'))
        return (
            'La memoire a trouve '
            f"{_to_int(rag.get('retrieved'))} elements, en a garde {_to_int(rag.get('kept'))}, "
            f"et en a injecte {_to_int(rag.get('injected'))}."
        )
    if module_key == 'web':
        web = _mapping(fact.get('web'))
        if web.get('requested'):
            return f"La recherche web a ete demandee avec le statut {web.get('status') or 'inconnu'}."
        return 'La recherche web n a pas ete demandee pour ce tour.'
    if module_key == 'providers':
        main = _mapping(_mapping(fact.get('providers')).get('main'))
        if main.get('present'):
            return f"Le modele principal a ete consulte avec le statut {main.get('status') or 'inconnu'}."
        return 'L appel au modele principal n est pas observe.'
    if module_key == 'identity':
        identity = _mapping(fact.get('identity'))
        if identity.get('block_present'):
            return 'Le modele principal a recu un bloc identite.'
        return 'Aucun bloc identite n est observe dans les donnees compactes.'
    if module_key == 'hermeneutic':
        hermeneutic = _mapping(fact.get('hermeneutic'))
        if hermeneutic.get('block_present'):
            return 'Le jugement hermeneutique est present dans les donnees compactes.'
        return 'Le jugement hermeneutique n est pas observe dans les donnees compactes.'
    if module_key == 'node_state':
        node_state = _mapping(fact.get('node_state'))
        if node_state.get('read_present') or node_state.get('write_attempted'):
            return 'L etat du noeud a ete relu ou mis a jour pendant le tour.'
        return 'Aucune lecture ou ecriture du node_state n est observee.'
    if module_key == 'errors':
        errors = _mapping(fact.get('errors'))
        problems = _to_int(errors.get('error_count')) + _to_int(errors.get('fallback_count'))
        if problems:
            return f"{problems} probleme(s) compact(s) sont visibles sur ce tour."
        return 'Aucun probleme compact n est visible sur ce tour.'
    return 'Module observable declare, sans detail specialise pour ce tour.'


def _translated_inspection(fact: Mapping[str, Any]) -> list[dict[str, Any]]:
    modules = []
    for module in dashboard_analytics.observable_modules():
        reason_code = None
        if module.module_key == 'errors':
            reason_counts = _mapping(_mapping(fact.get('errors')).get('reason_code_counts'))
            reason_code = next(iter(reason_counts.keys()), None)
        modules.append(
            {
                'module_key': module.module_key,
                'label_fr': module.label_fr,
                'summary_fr': _module_sentence(module.module_key, fact),
                'degradation_fr': (
                    dashboard_analytics.explain_module_degradation(
                        module.module_key,
                        reason_code=reason_code,
                    )
                    if reason_code
                    else None
                ),
                'raw_content_available': False,
            }
        )
    return modules


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
        'source': _source_status(window, status),
        'redaction': {'raw_content_included': False},
    }
