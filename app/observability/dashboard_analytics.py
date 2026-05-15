from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping, Sequence

from observability.turn_pipeline_read_model import build_turn_pipeline_item


SCHEMA_VERSION = '1'
CALCULATION_VERSION = 'dashboard_analytics_v1'
RETENTION_DAYS = 90
RECENT_GRANULARITY_DAYS = 30
_DAY_SECONDS = 24 * 60 * 60


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _to_float(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _payload(event: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = event.get('payload')
    if not isinstance(payload, Mapping):
        payload = event.get('payload_json')
    return _mapping(payload)


def _parse_ts(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        parsed = value
    else:
        text = str(value or '').strip()
        if not text:
            return None
        try:
            parsed = datetime.fromisoformat(text[:-1] + '+00:00' if text.endswith('Z') else text)
        except ValueError:
            return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _iso(value: datetime | None) -> str | None:
    if not value:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return str(event.get('ts') or ''), str(event.get('event_id') or '')


def _safe_events(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        [event for event in events if isinstance(event, Mapping)],
        key=_event_sort_key,
    )


def _turn_key(event: Mapping[str, Any]) -> tuple[str, str]:
    conversation_id = str(event.get('conversation_id') or '').strip()
    turn_id = str(event.get('turn_id') or '').strip()
    return conversation_id, turn_id


def _group_events_by_turn(
    events: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, str], list[Mapping[str, Any]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for event in events:
        key = _turn_key(event)
        if not key[0] or not key[1]:
            continue
        grouped.setdefault(key, []).append(event)
    return grouped


def _inc(mapping: dict[str, int], key: Any, amount: int = 1) -> None:
    normalized = str(key or 'unknown').strip() or 'unknown'
    mapping[normalized] = int(mapping.get(normalized, 0)) + int(amount)


def _latest_ts(fact: Mapping[str, Any]) -> datetime | None:
    return _parse_ts(fact.get('latest_ts'))


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _sha256_12(value: Any) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _bucket_start(value: datetime, granularity: str) -> datetime:
    value = value.astimezone(timezone.utc)
    if granularity == 'hour':
        return value.replace(minute=0, second=0, microsecond=0)
    return value.replace(hour=0, minute=0, second=0, microsecond=0)


def _bucket_end(start: datetime, granularity: str) -> datetime:
    if granularity == 'hour':
        return start + timedelta(hours=1)
    return start + timedelta(days=1)


def _percentile(values: Sequence[int], percentile: float) -> int | None:
    safe = sorted(int(value) for value in values if value is not None)
    if not safe:
        return None
    if len(safe) == 1:
        return safe[0]
    position = (len(safe) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(safe) - 1)
    weight = position - lower
    return int(round(safe[lower] * (1 - weight) + safe[upper] * weight))


def _event_to_read_model_item(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = _payload(event)
    return {
        'event_id': str(event.get('event_id') or ''),
        'conversation_id': str(event.get('conversation_id') or ''),
        'turn_id': str(event.get('turn_id') or ''),
        'ts': _iso(_parse_ts(event.get('ts'))) or str(event.get('ts') or ''),
        'stage': str(event.get('stage') or ''),
        'status': str(event.get('status') or ''),
        'duration_ms': event.get('duration_ms'),
        'payload': dict(payload),
    }


def build_dashboard_turn_fact(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build one persistent, content-free analytics fact from one turn's events."""
    safe_events = _safe_events(events)
    if not safe_events:
        raise ValueError('cannot build dashboard turn fact without events')

    read_model_events = [_event_to_read_model_item(event) for event in safe_events]
    item = build_turn_pipeline_item(
        read_model_events,
        events_total=len(read_model_events),
        events_truncated=False,
    )
    event_ids = [
        str(event.get('event_id') or '').strip()
        for event in safe_events
        if str(event.get('event_id') or '').strip()
    ]
    first = safe_events[0]
    latest = safe_events[-1]
    hermeneutic = dict(_mapping(item.get('hermeneutic')))
    node_state = dict(_mapping(hermeneutic.get('node_state')))
    content_availability = {
        'content_comprehension_status': 'compact_only',
        'prompt_manifest_available': False,
        'full_content_gate_available': False,
        'reason_code': 'content_artifacts_not_materialized_lot2',
    }

    return {
        'kind': 'dashboard_turn_fact',
        'schema_version': SCHEMA_VERSION,
        'calculation_version': CALCULATION_VERSION,
        'conversation_id': str(item.get('conversation_id') or first.get('conversation_id') or ''),
        'turn_id': str(item.get('turn_id') or first.get('turn_id') or ''),
        'first_ts': item.get('first_ts') or _iso(_parse_ts(first.get('ts'))),
        'latest_ts': item.get('latest_ts') or _iso(_parse_ts(latest.get('ts'))),
        'classification': str(item.get('classification') or 'legacy_incomplete'),
        'score': _to_int(item.get('score')),
        'source_event_ids': event_ids,
        'source_first_event_id': event_ids[0] if event_ids else None,
        'source_latest_event_id': event_ids[-1] if event_ids else None,
        'source_event_count': len(safe_events),
        'persistence': dict(_mapping(item.get('persistence'))),
        'providers': dict(_mapping(item.get('providers'))),
        'rag': dict(_mapping(item.get('rag'))),
        'identity': dict(_mapping(item.get('identity'))),
        'hermeneutic': hermeneutic,
        'web': dict(_mapping(item.get('web'))),
        'node_state': node_state,
        'latencies': dict(_mapping(item.get('latencies'))),
        'errors': dict(_mapping(item.get('errors'))),
        'stage_counts': dict(_mapping(item.get('stage_counts'))),
        'flags': dict(_mapping(item.get('flags'))),
        'content_availability': content_availability,
        'redaction': {
            'raw_event_payloads_included': False,
            'raw_content_stored': False,
            'derived_from_chat_log_events': True,
        },
    }


def _conversation_display_label(latest_ts: str | None) -> tuple[str, str]:
    parsed = _parse_ts(latest_ts)
    if not parsed:
        return 'Conversation sans date', 'fallback_no_title_no_date'
    return (
        f"Conversation du {parsed.strftime('%Y-%m-%d %H:%M')} UTC",
        'fallback_datetime',
    )


def build_dashboard_conversation_summaries(
    turn_facts: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for fact in turn_facts:
        conversation_id = str(fact.get('conversation_id') or '').strip()
        if conversation_id:
            grouped.setdefault(conversation_id, []).append(fact)

    summaries: list[dict[str, Any]] = []
    for conversation_id, facts in sorted(grouped.items()):
        ordered = sorted(facts, key=lambda fact: str(fact.get('latest_ts') or ''))
        first = ordered[0]
        latest = ordered[-1]
        classification_counts: dict[str, int] = {}
        persistence_counts: dict[str, int] = {}
        modules_involved: dict[str, int] = {}
        error_count = 0
        fallback_count = 0
        memory_used_turns = 0
        web_requested_turns = 0
        web_success_turns = 0
        web_injected_turns = 0
        last_problem_reason_code: str | None = None

        for fact in ordered:
            _inc(classification_counts, fact.get('classification'))
            persistence = _mapping(fact.get('persistence'))
            _inc(persistence_counts, persistence.get('status'))
            rag = _mapping(fact.get('rag'))
            web = _mapping(fact.get('web'))
            errors = _mapping(fact.get('errors'))

            if _to_int(rag.get('injected')) > 0 or _to_int(rag.get('retrieved')) > 0:
                memory_used_turns += 1
                _inc(modules_involved, 'memory')
            if bool(web.get('requested')):
                web_requested_turns += 1
                _inc(modules_involved, 'web')
            if bool(web.get('success')):
                web_success_turns += 1
            if bool(web.get('injected')):
                web_injected_turns += 1

            current_errors = _to_int(errors.get('error_count'))
            current_fallbacks = _to_int(errors.get('fallback_count'))
            error_count += current_errors
            fallback_count += current_fallbacks
            if current_errors or current_fallbacks:
                stages = _sequence(errors.get('stages'))
                if stages:
                    latest_stage = _mapping(stages[-1])
                    last_problem_reason_code = _text(latest_stage.get('reason_code')) or last_problem_reason_code

        display_label, display_label_source = _conversation_display_label(
            str(latest.get('latest_ts') or '')
        )
        summaries.append(
            {
                'kind': 'dashboard_conversation_summary',
                'schema_version': SCHEMA_VERSION,
                'calculation_version': CALCULATION_VERSION,
                'conversation_id': conversation_id,
                'display_label': display_label,
                'display_label_source': display_label_source,
                'first_ts': first.get('first_ts'),
                'latest_ts': latest.get('latest_ts'),
                'turns_count': len(ordered),
                'last_turn_id': latest.get('turn_id'),
                'last_classification': latest.get('classification'),
                'classification_counts': dict(sorted(classification_counts.items())),
                'persistence_counts': dict(sorted(persistence_counts.items())),
                'modules_involved': dict(sorted(modules_involved.items())),
                'memory_used_turns': memory_used_turns,
                'web_requested_turns': web_requested_turns,
                'web_success_turns': web_success_turns,
                'web_injected_turns': web_injected_turns,
                'error_count': error_count,
                'fallback_count': fallback_count,
                'last_problem_reason_code': last_problem_reason_code,
                'source': {
                    'source_kind': 'dashboard_turn_facts',
                    'turns_count': len(ordered),
                },
                'redaction': {
                    'raw_content_stored': False,
                },
            }
        )
    return summaries


def _bucket_key(granularity: str, bucket_start: datetime, module_key: str) -> tuple[str, str, str]:
    return granularity, _iso(bucket_start) or '', module_key


def _empty_bucket(
    *,
    granularity: str,
    bucket_start: datetime,
    module_key: str,
) -> dict[str, Any]:
    return {
        'kind': 'dashboard_metric_bucket',
        'schema_version': SCHEMA_VERSION,
        'calculation_version': CALCULATION_VERSION,
        'granularity': granularity,
        'bucket_start': _iso(bucket_start),
        'bucket_end': _iso(_bucket_end(bucket_start, granularity)),
        'module_key': module_key,
        'turn_count': 0,
        'event_count': 0,
        'metrics': {},
        'redaction': {
            'raw_content_stored': False,
        },
    }


def _bucket_for(
    buckets: dict[tuple[str, str, str], dict[str, Any]],
    *,
    granularity: str,
    bucket_start: datetime,
    module_key: str,
) -> dict[str, Any]:
    key = _bucket_key(granularity, bucket_start, module_key)
    if key not in buckets:
        buckets[key] = _empty_bucket(
            granularity=granularity,
            bucket_start=bucket_start,
            module_key=module_key,
        )
    return buckets[key]


def _add_metric_count(metrics: dict[str, Any], key: str, amount: int = 1) -> None:
    metrics[key] = _to_int(metrics.get(key)) + int(amount)


def _add_metric_label(metrics: dict[str, Any], group_key: str, label: Any, amount: int = 1) -> None:
    group = metrics.setdefault(group_key, {})
    if isinstance(group, dict):
        _inc(group, label, amount)


def _add_provider_metrics(metrics: dict[str, Any], fact: Mapping[str, Any]) -> None:
    providers = _mapping(fact.get('providers'))
    main = _mapping(providers.get('main'))
    secondary = _mapping(providers.get('secondary'))
    _add_metric_count(metrics, 'main_call_present_count', 1 if bool(main.get('present')) else 0)
    _add_metric_label(metrics, 'main_status_counts', main.get('status'))
    _add_metric_count(metrics, 'main_response_chars_total', _to_int(main.get('response_chars')))
    duration = main.get('duration_ms')
    if duration is not None:
        values = metrics.setdefault('_main_duration_ms_values', [])
        if isinstance(values, list):
            values.append(_to_int(duration))
        _add_metric_count(metrics, 'main_duration_ms_total', _to_int(duration))
        _add_metric_count(metrics, 'main_duration_ms_count')
    secondary_call_count = 0
    for item in secondary.values():
        summary = _mapping(item)
        secondary_call_count += _to_int(summary.get('llm_call_events_count'))
        _add_metric_label(metrics, 'secondary_status_counts', summary.get('status'))
    _add_metric_count(metrics, 'secondary_llm_call_count', secondary_call_count)


def _add_bucket_fact(bucket: dict[str, Any], fact: Mapping[str, Any]) -> None:
    module_key = str(bucket.get('module_key') or '')
    metrics = bucket.setdefault('metrics', {})
    if not isinstance(metrics, dict):
        metrics = {}
        bucket['metrics'] = metrics

    bucket['turn_count'] = _to_int(bucket.get('turn_count')) + 1
    bucket['event_count'] = _to_int(bucket.get('event_count')) + _to_int(fact.get('source_event_count'))

    if module_key == 'pipeline':
        _add_metric_label(metrics, 'classification_counts', fact.get('classification'))
        _add_metric_count(metrics, 'score_total', _to_int(fact.get('score')))
        _add_metric_count(metrics, 'score_count')
        flags = _mapping(fact.get('flags'))
        if bool(flags.get('events_truncated')):
            _add_metric_count(metrics, 'events_truncated_turns')
        return

    if module_key == 'persistence':
        persistence = _mapping(fact.get('persistence'))
        _add_metric_label(metrics, 'status_counts', persistence.get('status'))
        _add_metric_count(metrics, 'assistant_final_present_count', 1 if persistence.get('assistant_final_present') else 0)
        _add_metric_count(metrics, 'assistant_final_saved_count', 1 if persistence.get('assistant_final_saved') else 0)
        _add_metric_count(metrics, 'assistant_interrupted_count', 1 if persistence.get('assistant_interrupted') else 0)
        return

    if module_key == 'memory':
        rag = _mapping(fact.get('rag'))
        _add_metric_label(metrics, 'source_kind_counts', rag.get('source_kind'))
        _add_metric_count(metrics, 'retrieved_total', _to_int(rag.get('retrieved')))
        _add_metric_count(metrics, 'basket_total', _to_int(rag.get('basket')))
        _add_metric_count(metrics, 'kept_total', _to_int(rag.get('kept')))
        _add_metric_count(metrics, 'rejected_total', _to_int(rag.get('rejected')))
        _add_metric_count(metrics, 'injected_total', _to_int(rag.get('injected')))
        _add_metric_count(metrics, 'context_hints_total', _to_int(rag.get('context_hints')))
        _add_metric_count(metrics, 'snapshot_present_turns', 1 if rag.get('source_kind') == 'memory_chain_snapshot' else 0)
        _add_metric_count(metrics, 'legacy_fallback_turns', 1 if rag.get('legacy_reason_code') else 0)
        return

    if module_key == 'web':
        web = _mapping(fact.get('web'))
        _add_metric_label(metrics, 'status_counts', web.get('status'))
        _add_metric_count(metrics, 'requested_turns', 1 if web.get('requested') else 0)
        _add_metric_count(metrics, 'success_turns', 1 if web.get('success') else 0)
        _add_metric_count(metrics, 'skipped_turns', 1 if web.get('skipped') else 0)
        _add_metric_count(metrics, 'error_turns', 1 if web.get('error') else 0)
        _add_metric_count(metrics, 'injected_turns', 1 if web.get('injected') else 0)
        _add_metric_count(metrics, 'results_total', _to_int(web.get('results_count')))
        _add_metric_count(metrics, 'injected_chars_total', _to_int(web.get('injected_chars')))
        return

    if module_key == 'providers':
        _add_provider_metrics(metrics, fact)
        return

    if module_key == 'identity':
        identity = _mapping(fact.get('identity'))
        _add_metric_label(metrics, 'status_counts', identity.get('status'))
        _add_metric_count(metrics, 'block_present_turns', 1 if identity.get('block_present') else 0)
        _add_metric_count(metrics, 'chars_total', _to_int(identity.get('chars')))
        return

    if module_key == 'hermeneutic':
        hermeneutic = _mapping(fact.get('hermeneutic'))
        _add_metric_label(metrics, 'status_counts', hermeneutic.get('status'))
        _add_metric_count(metrics, 'block_present_turns', 1 if hermeneutic.get('block_present') else 0)
        _add_metric_count(metrics, 'fallback_turns', 1 if hermeneutic.get('fallback') else 0)
        return

    if module_key == 'node_state':
        node_state = _mapping(fact.get('node_state'))
        _add_metric_count(metrics, 'read_present_count', 1 if node_state.get('read_present') else 0)
        _add_metric_count(metrics, 'read_valid_count', 1 if node_state.get('read_valid') else 0)
        _add_metric_count(metrics, 'write_attempted_count', 1 if node_state.get('write_attempted') else 0)
        _add_metric_count(metrics, 'write_succeeded_count', 1 if node_state.get('write_succeeded') else 0)
        _add_metric_count(metrics, 'write_changed_count', 1 if node_state.get('write_changed') else 0)
        _add_metric_count(metrics, 'fail_open_count', 1 if node_state.get('fail_open') else 0)
        return

    if module_key == 'errors':
        errors = _mapping(fact.get('errors'))
        _add_metric_count(metrics, 'error_count', _to_int(errors.get('error_count')))
        _add_metric_count(metrics, 'skipped_count', _to_int(errors.get('skipped_count')))
        _add_metric_count(metrics, 'fallback_count', _to_int(errors.get('fallback_count')))
        reason_counts = _mapping(errors.get('reason_code_counts'))
        for reason, count in reason_counts.items():
            _add_metric_label(metrics, 'reason_code_counts', reason, _to_int(count))


def _finalize_bucket(bucket: dict[str, Any]) -> dict[str, Any]:
    metrics = bucket.get('metrics')
    if not isinstance(metrics, dict):
        return bucket
    score_count = _to_int(metrics.get('score_count'))
    if score_count:
        metrics['score_avg'] = round(_to_float(metrics.get('score_total')) / float(score_count), 3)
    duration_values = metrics.pop('_main_duration_ms_values', None)
    if isinstance(duration_values, list):
        metrics['main_duration_ms_p50'] = _percentile(duration_values, 0.50)
        metrics['main_duration_ms_p95'] = _percentile(duration_values, 0.95)
    return bucket


def build_dashboard_metric_buckets(
    turn_facts: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
) -> list[dict[str, Any]]:
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    recent_start = now_dt - timedelta(days=max(1, int(recent_granularity_days)))
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    modules = (
        'pipeline',
        'persistence',
        'memory',
        'web',
        'providers',
        'identity',
        'hermeneutic',
        'node_state',
        'errors',
    )
    for fact in turn_facts:
        latest = _latest_ts(fact)
        if latest is None:
            continue
        granularities = ['day']
        if latest >= recent_start:
            granularities.insert(0, 'hour')
        for granularity in granularities:
            start = _bucket_start(latest, granularity)
            for module_key in modules:
                bucket = _bucket_for(
                    buckets,
                    granularity=granularity,
                    bucket_start=start,
                    module_key=module_key,
                )
                _add_bucket_fact(bucket, fact)

    return [
        _finalize_bucket(bucket)
        for bucket in sorted(
            buckets.values(),
            key=lambda item: (
                str(item.get('granularity') or ''),
                str(item.get('bucket_start') or ''),
                str(item.get('module_key') or ''),
            ),
        )
    ]


def _retention_start(now: datetime, retention_days: int) -> datetime:
    return now.astimezone(timezone.utc) - timedelta(days=max(1, int(retention_days)))


def build_dashboard_materialization_status(
    *,
    events: Sequence[Mapping[str, Any]],
    turn_facts: Sequence[Mapping[str, Any]],
    conversation_summaries: Sequence[Mapping[str, Any]],
    metric_buckets: Sequence[Mapping[str, Any]],
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    retention_days: int = RETENTION_DAYS,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
    error: Exception | None = None,
) -> dict[str, Any]:
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = window_start or _retention_start(now_dt, retention_days)
    end = window_end or now_dt
    safe_events = _safe_events(events)
    latest = safe_events[-1] if safe_events else {}
    latest_ts = _parse_ts(latest.get('ts')) if latest else None
    lag_seconds = None
    if latest_ts:
        lag_seconds = max(0, int((now_dt - latest_ts).total_seconds()))
    status = 'error' if error else ('ok' if safe_events else 'empty')
    error_text = str(error or '').strip()
    return {
        'kind': 'dashboard_materialization_status',
        'schema_version': SCHEMA_VERSION,
        'materializer_key': 'dashboard_long_term_observability',
        'calculation_version': CALCULATION_VERSION,
        'status': status,
        'window_start': _iso(start),
        'window_end': _iso(end),
        'retention_days': int(retention_days),
        'recent_granularity_days': int(recent_granularity_days),
        'old_granularity': 'day',
        'source_events_count': len(safe_events),
        'source_events_truncated': False,
        'event_limit_dependency': False,
        'last_event_id': str(latest.get('event_id') or '') if latest else None,
        'last_event_ts': _iso(latest_ts),
        'lag_seconds': lag_seconds,
        'turns_materialized_count': len(turn_facts),
        'conversations_materialized_count': len(conversation_summaries),
        'buckets_materialized_count': len(metric_buckets),
        'error_count': 1 if error else 0,
        'last_error_code': error.__class__.__name__ if error else None,
        'last_error_chars': len(error_text) if error_text else 0,
        'last_error_sha256_12': _sha256_12(error_text),
        'backfill_status': (
            'retention_window_materialized'
            if start <= _retention_start(now_dt, retention_days) + timedelta(seconds=1)
            else 'custom_window_materialized'
        ),
        'updated_ts': _iso(now_dt),
        'redaction': {
            'raw_content_stored': False,
            'raw_error_message_stored': False,
        },
    }


def build_dashboard_analytics(
    events: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    window_start: datetime | None = None,
    window_end: datetime | None = None,
    retention_days: int = RETENTION_DAYS,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
) -> dict[str, Any]:
    """Build the long-term dashboard analytics projection without event limits."""
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = window_start or _retention_start(now_dt, retention_days)
    end = window_end or now_dt
    safe_events = [
        event for event in _safe_events(events)
        if (parsed := _parse_ts(event.get('ts'))) is not None and start <= parsed < end
    ]
    turn_facts = [
        build_dashboard_turn_fact(turn_events)
        for turn_events in _group_events_by_turn(safe_events).values()
    ]
    turn_facts = sorted(
        turn_facts,
        key=lambda fact: (str(fact.get('latest_ts') or ''), str(fact.get('conversation_id') or ''), str(fact.get('turn_id') or '')),
    )
    conversation_summaries = build_dashboard_conversation_summaries(turn_facts)
    metric_buckets = build_dashboard_metric_buckets(
        turn_facts,
        now=now_dt,
        recent_granularity_days=recent_granularity_days,
    )
    materialization_status = build_dashboard_materialization_status(
        events=safe_events,
        turn_facts=turn_facts,
        conversation_summaries=conversation_summaries,
        metric_buckets=metric_buckets,
        now=now_dt,
        window_start=start,
        window_end=end,
        retention_days=retention_days,
        recent_granularity_days=recent_granularity_days,
    )
    return {
        'kind': 'dashboard_analytics_materialization',
        'schema_version': SCHEMA_VERSION,
        'calculation_version': CALCULATION_VERSION,
        'window': {
            'start': _iso(start),
            'end': _iso(end),
            'retention_days': int(retention_days),
            'recent_granularity_days': int(recent_granularity_days),
            'old_granularity': 'day',
        },
        'turn_facts': turn_facts,
        'conversation_summaries': conversation_summaries,
        'metric_buckets': metric_buckets,
        'materialization_status': materialization_status,
        'redaction': {
            'raw_content_stored': False,
            'raw_event_payloads_included': False,
        },
    }


def execute_dashboard_analytics_schema(cur: Any) -> None:
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_turn_facts (
            conversation_id             TEXT        NOT NULL,
            turn_id                     TEXT        NOT NULL,
            first_ts                    TIMESTAMPTZ NOT NULL,
            latest_ts                   TIMESTAMPTZ NOT NULL,
            classification              TEXT        NOT NULL,
            score                       INTEGER,
            source_event_ids            JSONB       NOT NULL DEFAULT '[]'::jsonb,
            source_event_count          INTEGER     NOT NULL DEFAULT 0,
            source_first_event_id       TEXT,
            source_latest_event_id      TEXT,
            persistence_json            JSONB       NOT NULL DEFAULT '{}'::jsonb,
            providers_json              JSONB       NOT NULL DEFAULT '{}'::jsonb,
            rag_json                    JSONB       NOT NULL DEFAULT '{}'::jsonb,
            identity_json               JSONB       NOT NULL DEFAULT '{}'::jsonb,
            hermeneutic_json            JSONB       NOT NULL DEFAULT '{}'::jsonb,
            web_json                    JSONB       NOT NULL DEFAULT '{}'::jsonb,
            node_state_json             JSONB       NOT NULL DEFAULT '{}'::jsonb,
            latencies_json              JSONB       NOT NULL DEFAULT '{}'::jsonb,
            errors_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            stage_counts_json           JSONB       NOT NULL DEFAULT '{}'::jsonb,
            flags_json                  JSONB       NOT NULL DEFAULT '{}'::jsonb,
            content_availability_json   JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            raw_event_payloads_included BOOLEAN     NOT NULL DEFAULT false,
            PRIMARY KEY (conversation_id, turn_id),
            CHECK (raw_event_payloads_included = false)
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_turn_facts_latest_ts_idx
        ON observability.dashboard_turn_facts (latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_turn_facts_conversation_latest_ts_idx
        ON observability.dashboard_turn_facts (conversation_id, latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_conversation_summaries (
            conversation_id             TEXT        PRIMARY KEY,
            display_label               TEXT        NOT NULL,
            display_label_source        TEXT        NOT NULL,
            first_ts                    TIMESTAMPTZ,
            latest_ts                   TIMESTAMPTZ,
            turns_count                 INTEGER     NOT NULL DEFAULT 0,
            last_turn_id                TEXT,
            last_classification         TEXT,
            classification_counts_json  JSONB       NOT NULL DEFAULT '{}'::jsonb,
            persistence_counts_json     JSONB       NOT NULL DEFAULT '{}'::jsonb,
            modules_involved_json       JSONB       NOT NULL DEFAULT '{}'::jsonb,
            memory_used_turns           INTEGER     NOT NULL DEFAULT 0,
            web_requested_turns         INTEGER     NOT NULL DEFAULT 0,
            web_success_turns           INTEGER     NOT NULL DEFAULT 0,
            web_injected_turns          INTEGER     NOT NULL DEFAULT 0,
            error_count                 INTEGER     NOT NULL DEFAULT 0,
            fallback_count              INTEGER     NOT NULL DEFAULT 0,
            last_problem_reason_code    TEXT,
            source_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_conversation_summaries_latest_ts_idx
        ON observability.dashboard_conversation_summaries (latest_ts DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_metric_buckets (
            granularity                 TEXT        NOT NULL,
            bucket_start                TIMESTAMPTZ NOT NULL,
            bucket_end                  TIMESTAMPTZ NOT NULL,
            module_key                  TEXT        NOT NULL,
            turn_count                  INTEGER     NOT NULL DEFAULT 0,
            event_count                 INTEGER     NOT NULL DEFAULT 0,
            metrics_json                JSONB       NOT NULL DEFAULT '{}'::jsonb,
            calculation_version         TEXT        NOT NULL,
            materialized_ts             TIMESTAMPTZ NOT NULL DEFAULT now(),
            PRIMARY KEY (granularity, bucket_start, module_key),
            CHECK (granularity IN ('hour', 'day'))
        );
        '''
    )
    cur.execute(
        '''
        CREATE INDEX IF NOT EXISTS dashboard_metric_buckets_module_window_idx
        ON observability.dashboard_metric_buckets (module_key, granularity, bucket_start DESC);
        '''
    )
    cur.execute(
        '''
        CREATE TABLE IF NOT EXISTS observability.dashboard_materialization_status (
            materializer_key            TEXT        PRIMARY KEY,
            calculation_version         TEXT        NOT NULL,
            status                      TEXT        NOT NULL,
            window_start                TIMESTAMPTZ,
            window_end                  TIMESTAMPTZ,
            retention_days              INTEGER     NOT NULL,
            recent_granularity_days     INTEGER     NOT NULL,
            old_granularity             TEXT        NOT NULL,
            source_events_count         BIGINT      NOT NULL DEFAULT 0,
            source_events_truncated     BOOLEAN     NOT NULL DEFAULT false,
            event_limit_dependency      BOOLEAN     NOT NULL DEFAULT false,
            last_event_id               TEXT,
            last_event_ts               TIMESTAMPTZ,
            lag_seconds                 BIGINT,
            turns_materialized_count    INTEGER     NOT NULL DEFAULT 0,
            conversations_materialized_count INTEGER NOT NULL DEFAULT 0,
            buckets_materialized_count  INTEGER     NOT NULL DEFAULT 0,
            error_count                 INTEGER     NOT NULL DEFAULT 0,
            last_error_code             TEXT,
            last_error_chars            INTEGER     NOT NULL DEFAULT 0,
            last_error_sha256_12        TEXT,
            backfill_status             TEXT        NOT NULL,
            status_json                 JSONB       NOT NULL DEFAULT '{}'::jsonb,
            updated_ts                  TIMESTAMPTZ NOT NULL DEFAULT now(),
            CHECK (source_events_truncated = false),
            CHECK (event_limit_dependency = false)
        );
        '''
    )


def init_dashboard_analytics_storage(
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> None:
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                cur.execute('CREATE SCHEMA IF NOT EXISTS observability;')
                execute_dashboard_analytics_schema(cur)
            conn.commit()
        logger_instance.info('dashboard_analytics_storage_init ok')
    except Exception as exc:
        logger_instance.error('dashboard_analytics_storage_init_failed err=%s', exc)


def persist_dashboard_analytics(
    analytics: Mapping[str, Any],
    *,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> dict[str, Any]:
    turn_facts = list(_sequence(analytics.get('turn_facts')))
    conversation_summaries = list(_sequence(analytics.get('conversation_summaries')))
    metric_buckets = list(_sequence(analytics.get('metric_buckets')))
    status = _mapping(analytics.get('materialization_status'))
    window = _mapping(analytics.get('window'))
    window_start = window.get('start')
    window_end = window.get('end')
    conversation_ids = sorted(
        {
            str(summary.get('conversation_id') or '').strip()
            for summary in conversation_summaries
            if str(summary.get('conversation_id') or '').strip()
        }
    )

    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
                if window_start and window_end:
                    cur.execute(
                        '''
                        DELETE FROM observability.dashboard_turn_facts
                        WHERE latest_ts >= %s::timestamptz
                          AND latest_ts < %s::timestamptz
                        ''',
                        (window_start, window_end),
                    )
                    cur.execute(
                        '''
                        DELETE FROM observability.dashboard_metric_buckets
                        WHERE bucket_start >= date_trunc('day', %s::timestamptz)
                          AND bucket_start < %s::timestamptz
                        ''',
                        (window_start, window_end),
                    )
                    if status.get('backfill_status') == 'retention_window_materialized':
                        cur.execute(
                            'DELETE FROM observability.dashboard_conversation_summaries',
                            (),
                        )
                    elif conversation_ids:
                        cur.execute(
                            '''
                            DELETE FROM observability.dashboard_conversation_summaries
                            WHERE conversation_id = ANY(%s)
                            ''',
                            (conversation_ids,),
                        )

                for fact in turn_facts:
                    cur.execute(
                        '''
                        INSERT INTO observability.dashboard_turn_facts (
                            conversation_id, turn_id, first_ts, latest_ts,
                            classification, score, source_event_ids, source_event_count,
                            source_first_event_id, source_latest_event_id,
                            persistence_json, providers_json, rag_json, identity_json,
                            hermeneutic_json, web_json, node_state_json, latencies_json,
                            errors_json, stage_counts_json, flags_json,
                            content_availability_json, calculation_version,
                            raw_event_payloads_included, materialized_ts
                        )
                        VALUES (
                            %s, %s, %s::timestamptz, %s::timestamptz,
                            %s, %s, %s::jsonb, %s,
                            %s, %s,
                            %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s::jsonb, %s::jsonb,
                            %s::jsonb, %s,
                            false, now()
                        )
                        ON CONFLICT (conversation_id, turn_id) DO UPDATE SET
                            first_ts = EXCLUDED.first_ts,
                            latest_ts = EXCLUDED.latest_ts,
                            classification = EXCLUDED.classification,
                            score = EXCLUDED.score,
                            source_event_ids = EXCLUDED.source_event_ids,
                            source_event_count = EXCLUDED.source_event_count,
                            source_first_event_id = EXCLUDED.source_first_event_id,
                            source_latest_event_id = EXCLUDED.source_latest_event_id,
                            persistence_json = EXCLUDED.persistence_json,
                            providers_json = EXCLUDED.providers_json,
                            rag_json = EXCLUDED.rag_json,
                            identity_json = EXCLUDED.identity_json,
                            hermeneutic_json = EXCLUDED.hermeneutic_json,
                            web_json = EXCLUDED.web_json,
                            node_state_json = EXCLUDED.node_state_json,
                            latencies_json = EXCLUDED.latencies_json,
                            errors_json = EXCLUDED.errors_json,
                            stage_counts_json = EXCLUDED.stage_counts_json,
                            flags_json = EXCLUDED.flags_json,
                            content_availability_json = EXCLUDED.content_availability_json,
                            calculation_version = EXCLUDED.calculation_version,
                            raw_event_payloads_included = false,
                            materialized_ts = now()
                        ''',
                        (
                            fact.get('conversation_id'),
                            fact.get('turn_id'),
                            fact.get('first_ts'),
                            fact.get('latest_ts'),
                            fact.get('classification'),
                            fact.get('score'),
                            _json(fact.get('source_event_ids') or []),
                            _to_int(fact.get('source_event_count')),
                            fact.get('source_first_event_id'),
                            fact.get('source_latest_event_id'),
                            _json(fact.get('persistence') or {}),
                            _json(fact.get('providers') or {}),
                            _json(fact.get('rag') or {}),
                            _json(fact.get('identity') or {}),
                            _json(fact.get('hermeneutic') or {}),
                            _json(fact.get('web') or {}),
                            _json(fact.get('node_state') or {}),
                            _json(fact.get('latencies') or {}),
                            _json(fact.get('errors') or {}),
                            _json(fact.get('stage_counts') or {}),
                            _json(fact.get('flags') or {}),
                            _json(fact.get('content_availability') or {}),
                            fact.get('calculation_version') or CALCULATION_VERSION,
                        ),
                    )

                for summary in conversation_summaries:
                    cur.execute(
                        '''
                        INSERT INTO observability.dashboard_conversation_summaries (
                            conversation_id, display_label, display_label_source,
                            first_ts, latest_ts, turns_count, last_turn_id,
                            last_classification, classification_counts_json,
                            persistence_counts_json, modules_involved_json,
                            memory_used_turns, web_requested_turns, web_success_turns,
                            web_injected_turns, error_count, fallback_count,
                            last_problem_reason_code, source_json, calculation_version,
                            materialized_ts
                        )
                        VALUES (
                            %s, %s, %s,
                            %s::timestamptz, %s::timestamptz, %s, %s,
                            %s, %s::jsonb,
                            %s::jsonb, %s::jsonb,
                            %s, %s, %s,
                            %s, %s, %s,
                            %s, %s::jsonb, %s,
                            now()
                        )
                        ON CONFLICT (conversation_id) DO UPDATE SET
                            display_label = EXCLUDED.display_label,
                            display_label_source = EXCLUDED.display_label_source,
                            first_ts = EXCLUDED.first_ts,
                            latest_ts = EXCLUDED.latest_ts,
                            turns_count = EXCLUDED.turns_count,
                            last_turn_id = EXCLUDED.last_turn_id,
                            last_classification = EXCLUDED.last_classification,
                            classification_counts_json = EXCLUDED.classification_counts_json,
                            persistence_counts_json = EXCLUDED.persistence_counts_json,
                            modules_involved_json = EXCLUDED.modules_involved_json,
                            memory_used_turns = EXCLUDED.memory_used_turns,
                            web_requested_turns = EXCLUDED.web_requested_turns,
                            web_success_turns = EXCLUDED.web_success_turns,
                            web_injected_turns = EXCLUDED.web_injected_turns,
                            error_count = EXCLUDED.error_count,
                            fallback_count = EXCLUDED.fallback_count,
                            last_problem_reason_code = EXCLUDED.last_problem_reason_code,
                            source_json = EXCLUDED.source_json,
                            calculation_version = EXCLUDED.calculation_version,
                            materialized_ts = now()
                        ''',
                        (
                            summary.get('conversation_id'),
                            summary.get('display_label'),
                            summary.get('display_label_source'),
                            summary.get('first_ts'),
                            summary.get('latest_ts'),
                            _to_int(summary.get('turns_count')),
                            summary.get('last_turn_id'),
                            summary.get('last_classification'),
                            _json(summary.get('classification_counts') or {}),
                            _json(summary.get('persistence_counts') or {}),
                            _json(summary.get('modules_involved') or {}),
                            _to_int(summary.get('memory_used_turns')),
                            _to_int(summary.get('web_requested_turns')),
                            _to_int(summary.get('web_success_turns')),
                            _to_int(summary.get('web_injected_turns')),
                            _to_int(summary.get('error_count')),
                            _to_int(summary.get('fallback_count')),
                            summary.get('last_problem_reason_code'),
                            _json(summary.get('source') or {}),
                            summary.get('calculation_version') or CALCULATION_VERSION,
                        ),
                    )

                for bucket in metric_buckets:
                    cur.execute(
                        '''
                        INSERT INTO observability.dashboard_metric_buckets (
                            granularity, bucket_start, bucket_end, module_key,
                            turn_count, event_count, metrics_json,
                            calculation_version, materialized_ts
                        )
                        VALUES (%s, %s::timestamptz, %s::timestamptz, %s, %s, %s, %s::jsonb, %s, now())
                        ON CONFLICT (granularity, bucket_start, module_key) DO UPDATE SET
                            bucket_end = EXCLUDED.bucket_end,
                            turn_count = EXCLUDED.turn_count,
                            event_count = EXCLUDED.event_count,
                            metrics_json = EXCLUDED.metrics_json,
                            calculation_version = EXCLUDED.calculation_version,
                            materialized_ts = now()
                        ''',
                        (
                            bucket.get('granularity'),
                            bucket.get('bucket_start'),
                            bucket.get('bucket_end'),
                            bucket.get('module_key'),
                            _to_int(bucket.get('turn_count')),
                            _to_int(bucket.get('event_count')),
                            _json(bucket.get('metrics') or {}),
                            bucket.get('calculation_version') or CALCULATION_VERSION,
                        ),
                    )

                cur.execute(
                    '''
                    INSERT INTO observability.dashboard_materialization_status (
                        materializer_key, calculation_version, status,
                        window_start, window_end, retention_days, recent_granularity_days,
                        old_granularity, source_events_count, source_events_truncated,
                        event_limit_dependency, last_event_id, last_event_ts, lag_seconds,
                        turns_materialized_count, conversations_materialized_count,
                        buckets_materialized_count, error_count, last_error_code,
                        last_error_chars, last_error_sha256_12, backfill_status,
                        status_json, updated_ts
                    )
                    VALUES (
                        %s, %s, %s,
                        %s::timestamptz, %s::timestamptz, %s, %s,
                        %s, %s, false,
                        false, %s, %s::timestamptz, %s,
                        %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s::jsonb, %s::timestamptz
                    )
                    ON CONFLICT (materializer_key) DO UPDATE SET
                        calculation_version = EXCLUDED.calculation_version,
                        status = EXCLUDED.status,
                        window_start = EXCLUDED.window_start,
                        window_end = EXCLUDED.window_end,
                        retention_days = EXCLUDED.retention_days,
                        recent_granularity_days = EXCLUDED.recent_granularity_days,
                        old_granularity = EXCLUDED.old_granularity,
                        source_events_count = EXCLUDED.source_events_count,
                        source_events_truncated = false,
                        event_limit_dependency = false,
                        last_event_id = EXCLUDED.last_event_id,
                        last_event_ts = EXCLUDED.last_event_ts,
                        lag_seconds = EXCLUDED.lag_seconds,
                        turns_materialized_count = EXCLUDED.turns_materialized_count,
                        conversations_materialized_count = EXCLUDED.conversations_materialized_count,
                        buckets_materialized_count = EXCLUDED.buckets_materialized_count,
                        error_count = EXCLUDED.error_count,
                        last_error_code = EXCLUDED.last_error_code,
                        last_error_chars = EXCLUDED.last_error_chars,
                        last_error_sha256_12 = EXCLUDED.last_error_sha256_12,
                        backfill_status = EXCLUDED.backfill_status,
                        status_json = EXCLUDED.status_json,
                        updated_ts = EXCLUDED.updated_ts
                    ''',
                    (
                        status.get('materializer_key') or 'dashboard_long_term_observability',
                        status.get('calculation_version') or CALCULATION_VERSION,
                        status.get('status') or 'unknown',
                        status.get('window_start'),
                        status.get('window_end'),
                        _to_int(status.get('retention_days')) or RETENTION_DAYS,
                        _to_int(status.get('recent_granularity_days')) or RECENT_GRANULARITY_DAYS,
                        status.get('old_granularity') or 'day',
                        _to_int(status.get('source_events_count')),
                        status.get('last_event_id'),
                        status.get('last_event_ts'),
                        status.get('lag_seconds'),
                        _to_int(status.get('turns_materialized_count')),
                        _to_int(status.get('conversations_materialized_count')),
                        _to_int(status.get('buckets_materialized_count')),
                        _to_int(status.get('error_count')),
                        status.get('last_error_code'),
                        _to_int(status.get('last_error_chars')),
                        status.get('last_error_sha256_12'),
                        status.get('backfill_status') or 'unknown',
                        _json(status),
                        status.get('updated_ts'),
                    ),
                )
            conn.commit()
    except Exception as exc:
        logger_instance.error('dashboard_analytics_persist_failed err=%s', exc)
        raise

    return {
        'ok': True,
        'turn_facts_written': len(turn_facts),
        'conversation_summaries_written': len(conversation_summaries),
        'metric_buckets_written': len(metric_buckets),
        'materialization_status_written': bool(status),
    }


def _row_to_event(row: Sequence[Any]) -> dict[str, Any]:
    payload_json = row[7]
    if not isinstance(payload_json, dict):
        payload_json = {}
    return {
        'event_id': str(row[0] or ''),
        'conversation_id': str(row[1] or ''),
        'turn_id': str(row[2] or ''),
        'ts': _iso(_parse_ts(row[3])) if row[3] is not None else '',
        'stage': str(row[4] or ''),
        'status': str(row[5] or ''),
        'duration_ms': int(row[6]) if row[6] is not None else None,
        'payload_json': payload_json,
    }


def materialize_dashboard_analytics_window(
    *,
    ts_from: str | None = None,
    ts_to: str | None = None,
    now: datetime | None = None,
    retention_days: int = RETENTION_DAYS,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
    conn_factory: Callable[[], Any],
    logger_instance: Any,
) -> dict[str, Any]:
    """Read compact events for the chosen window, build and persist analytics.

    This intentionally has no event_limit parameter. Historical backfill remains
    an explicit caller decision; the default window is the current retention
    horizon.
    """
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = _parse_ts(ts_from) if ts_from else _retention_start(now_dt, retention_days)
    end = _parse_ts(ts_to) if ts_to else now_dt
    if start is None:
        raise ValueError(f'invalid ts_from timestamp: {ts_from}')
    if end is None:
        raise ValueError(f'invalid ts_to timestamp: {ts_to}')
    if start >= end:
        raise ValueError('ts_from must be before ts_to')

    rows: list[Sequence[Any]] = []
    try:
        with conn_factory() as conn:
            with conn.cursor() as cur:
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
                    WHERE ts >= %s::timestamptz
                      AND ts < %s::timestamptz
                    ORDER BY ts ASC, event_id ASC
                    ''',
                    (_iso(start), _iso(end)),
                )
                rows = cur.fetchall()
    except Exception as exc:
        status = build_dashboard_materialization_status(
            events=[],
            turn_facts=[],
            conversation_summaries=[],
            metric_buckets=[],
            now=now_dt,
            window_start=start,
            window_end=end,
            retention_days=retention_days,
            recent_granularity_days=recent_granularity_days,
            error=exc,
        )
        analytics = {
            'kind': 'dashboard_analytics_materialization',
            'schema_version': SCHEMA_VERSION,
            'calculation_version': CALCULATION_VERSION,
            'window': {
                'start': _iso(start),
                'end': _iso(end),
                'retention_days': int(retention_days),
                'recent_granularity_days': int(recent_granularity_days),
                'old_granularity': 'day',
            },
            'turn_facts': [],
            'conversation_summaries': [],
            'metric_buckets': [],
            'materialization_status': status,
            'redaction': {
                'raw_content_stored': False,
                'raw_event_payloads_included': False,
            },
        }
        try:
            persist_dashboard_analytics(
                analytics,
                conn_factory=conn_factory,
                logger_instance=logger_instance,
            )
        except Exception:
            pass
        logger_instance.error('dashboard_analytics_materialize_read_failed err=%s', exc)
        return analytics

    analytics = build_dashboard_analytics(
        [_row_to_event(row) for row in rows],
        now=now_dt,
        window_start=start,
        window_end=end,
        retention_days=retention_days,
        recent_granularity_days=recent_granularity_days,
    )
    persist_result = persist_dashboard_analytics(
        analytics,
        conn_factory=conn_factory,
        logger_instance=logger_instance,
    )
    analytics['persist'] = persist_result
    return analytics
