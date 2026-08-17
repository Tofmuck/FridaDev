from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.dashboard_read_model_query import (
    _iso,
    _json_mapping,
    _mapping,
    _status_schema_from_flags,
    _to_int,
)

_NON_ADDITIVE_METRIC_SUFFIXES = ('_avg', '_p50', '_p95', '_median', '_rate')


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
    error_count = _to_int(errors.get('error_count'))
    failed_count = _to_int(errors.get('failed_count'))
    fallback_count = _to_int(errors.get('fallback_count'))
    attempt_failure_count = _to_int(errors.get('attempt_failure_count')) or error_count + failed_count
    problem_count = _to_int(errors.get('problem_count')) or attempt_failure_count + fallback_count
    non_problem_status_count = _to_int(errors.get('non_problem_status_count')) or sum(
        _to_int(errors.get(key))
        for key in (
            'skipped_count',
            'disabled_count',
            'not_selected_count',
            'not_configured_count',
            'not_applicable_count',
            'refused_count',
        )
    )
    return {
        'label_fr': 'Pouls global',
        'turns_observed': _to_int(_mapping(modules.get('pipeline')).get('turn_count')),
        'classification_counts': _json_mapping(pipeline.get('classification_counts')),
        'responses_saved': _to_int(persistence.get('assistant_final_saved_count')),
        'memory_injected_total': _to_int(memory.get('injected_total')),
        'web_requested_turns': _to_int(web.get('requested_turns')),
        'web_injected_turns': _to_int(web.get('injected_turns')),
        'problems_count': problem_count,
        'attempt_failures_count': attempt_failure_count,
        'error_count': error_count,
        'failed_count': failed_count,
        'fallback_count': fallback_count,
        'non_problem_status_count': non_problem_status_count,
        'status_counts': _json_mapping(errors.get('status_counts')),
        'status_schema_counts': _json_mapping(errors.get('status_schema_counts')),
        'v1_event_count': _to_int(errors.get('v1_event_count')),
        'legacy_event_count': _to_int(errors.get('legacy_event_count')),
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
    biblio_used_turns = 0
    biblio_passages_total = 0
    error_count = 0
    failed_count = 0
    fallback_count = 0
    last_turn_id = None
    status_schema_counts: dict[str, int] = {}
    status_schema_source_counts: dict[str, int] = {}
    v1_event_count = 0
    legacy_event_count = 0
    for row in sorted(rows, key=lambda item: str(_iso(item[4]) or '')):
        classification = str(row[6] or 'legacy_incomplete')
        classification_counts[classification] = classification_counts.get(classification, 0) + 1
        last_turn_id = str(row[5] or '') or last_turn_id
        rag = _mapping(row[7])
        web = _mapping(row[8])
        documents = _mapping(row[9])
        biblio = _mapping(row[10])
        errors = _mapping(row[11])
        flags = _mapping(row[12]) if len(row) > 12 else {}
        status_schema = _status_schema_from_flags(flags)
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
        if bool(biblio.get('used')):
            biblio_used_turns += 1
        biblio_passages_total += _to_int(biblio.get('passage_count'))
        error_count += _to_int(errors.get('error_count'))
        failed_count += _to_int(errors.get('failed_count'))
        fallback_count += _to_int(errors.get('fallback_count'))
        source_kind = str(status_schema.get('source_kind') or '').strip() or 'unknown'
        status_schema_source_counts[source_kind] = status_schema_source_counts.get(source_kind, 0) + 1
        for schema, count in _mapping(status_schema.get('schema_counts')).items():
            schema_key = str(schema or 'unknown').strip() or 'unknown'
            status_schema_counts[schema_key] = status_schema_counts.get(schema_key, 0) + _to_int(count)
        v1_event_count += _to_int(status_schema.get('v1_event_count'))
        legacy_event_count += _to_int(status_schema.get('legacy_event_count'))
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
        'biblio_used_turns': biblio_used_turns,
        'biblio_passages_total': biblio_passages_total,
        'error_count': error_count,
        'failed_count': failed_count,
        'attempt_failure_count': error_count + failed_count,
        'fallback_count': fallback_count,
        'problem_count': error_count + failed_count + fallback_count,
        'status_schema': {
            'source_kind_counts': dict(sorted(status_schema_source_counts.items())),
            'schema_counts': dict(sorted(status_schema_counts.items())),
            'v1_event_count': v1_event_count,
            'legacy_event_count': legacy_event_count,
            'historical_events_reclassified': False,
        },
        'redaction': {'raw_content_included': False},
    }


aggregate_module_metrics = _aggregate_module_metrics
build_conversation_summary = _conversation_summary_from_facts
