from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from observability.dashboard_observable_modules import ObservableModule, observable_modules
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


def _add_bucket_fact(
    bucket: dict[str, Any],
    fact: Mapping[str, Any],
    module: ObservableModule,
) -> None:
    metrics = bucket.setdefault('metrics', {})
    if not isinstance(metrics, dict):
        metrics = {}
        bucket['metrics'] = metrics

    bucket['turn_count'] = _to_int(bucket.get('turn_count')) + 1
    bucket['event_count'] = _to_int(bucket.get('event_count')) + _to_int(fact.get('source_event_count'))

    if module.bucket_metrics_reducer:
        module.bucket_metrics_reducer(metrics, fact)


def _finalize_bucket(bucket: dict[str, Any], module: ObservableModule | None) -> dict[str, Any]:
    metrics = bucket.get('metrics')
    if not isinstance(metrics, dict):
        return bucket
    if module and module.bucket_metrics_finalizer:
        module.bucket_metrics_finalizer(metrics)
    return bucket


def build_dashboard_metric_buckets(
    turn_facts: Sequence[Mapping[str, Any]],
    *,
    now: datetime | None = None,
    recent_granularity_days: int = RECENT_GRANULARITY_DAYS,
    extra_modules: Sequence[ObservableModule] = (),
) -> list[dict[str, Any]]:
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    recent_start = now_dt - timedelta(days=max(1, int(recent_granularity_days)))
    buckets: dict[tuple[str, str, str], dict[str, Any]] = {}
    modules = observable_modules(extra_modules=extra_modules)
    module_by_key = {module.module_key: module for module in modules}
    for fact in turn_facts:
        latest = _latest_ts(fact)
        if latest is None:
            continue
        granularities = ['day']
        if latest >= recent_start:
            granularities.insert(0, 'hour')
        for granularity in granularities:
            start = _bucket_start(latest, granularity)
            for module in modules:
                bucket = _bucket_for(
                    buckets,
                    granularity=granularity,
                    bucket_start=start,
                    module_key=module.module_key,
                )
                _add_bucket_fact(bucket, fact, module)

    return [
        _finalize_bucket(
            bucket,
            module_by_key.get(str(bucket.get('module_key') or '')),
        )
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
    filter_events_to_window: bool = True,
) -> dict[str, Any]:
    """Build the long-term dashboard analytics projection without event limits."""
    now_dt = (now or datetime.now(timezone.utc)).astimezone(timezone.utc)
    start = window_start or _retention_start(now_dt, retention_days)
    end = window_end or now_dt
    if filter_events_to_window:
        safe_events = [
            event for event in _safe_events(events)
            if (parsed := _parse_ts(event.get('ts'))) is not None and start <= parsed < end
        ]
    else:
        safe_events = _safe_events(events)
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
