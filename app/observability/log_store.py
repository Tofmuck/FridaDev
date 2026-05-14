from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any, Callable, Mapping, Sequence

import psycopg

import config
from admin import runtime_settings
from core import runtime_db_bootstrap

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
_TURN_CHECKLIST_ITEM_STATUSES = (
    'ok',
    'degraded',
    'missing',
    'not_applicable',
)
_TURN_CHECKLIST_SCORE_WEIGHTS = {
    'ok': 1.0,
    'degraded': 0.5,
    'missing': 0.0,
}
_TURN_CHECKLIST_LEGACY_CRITICAL_ITEMS = {
    'turn_start',
    'prompt_prepared',
    'turn_end',
}


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


def _event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = event.get('payload')
    if not isinstance(payload, Mapping):
        payload = event.get('payload_json')
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _event_stage(event: Mapping[str, Any]) -> str:
    return str(event.get('stage') or '').strip()


def _event_status(event: Mapping[str, Any]) -> str:
    return str(event.get('status') or '').strip().lower()


def _payload_text(payload: Mapping[str, Any], key: str) -> str | None:
    text = str(payload.get(key) or '').strip()
    return text or None


def _compact_reason_from_event(event: Mapping[str, Any]) -> str | None:
    payload = _event_payload(event)
    for key in ('reason_code', 'error_code', 'error_class'):
        text = _payload_text(payload, key)
        if text:
            return text
    return None


def _checklist_item(
    key: str,
    group: str,
    status: str,
    reason_code: str,
    *,
    stage: str | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status_s = status if status in _TURN_CHECKLIST_ITEM_STATUSES else 'degraded'
    item: dict[str, Any] = {
        'key': key,
        'group': group,
        'status': status_s,
        'reason_code': str(reason_code or 'unknown'),
    }
    if stage:
        item['stage'] = stage
    compact_evidence = {
        str(k): v
        for k, v in dict(evidence or {}).items()
        if v is not None and isinstance(v, (bool, int, float, str, list, dict))
    }
    if compact_evidence:
        item['evidence'] = compact_evidence
    return item


def _events_by_stage(events: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        stage = _event_stage(event)
        if not stage:
            continue
        grouped.setdefault(stage, []).append(event)
    return grouped


def _stage_counts(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, int]:
    return {
        stage: len(items)
        for stage, items in sorted(grouped.items())
    }


def _latest_stage_event(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    stage: str,
) -> Mapping[str, Any] | None:
    items = list(grouped.get(stage) or [])
    if not items:
        return None
    return items[-1]


def _stage_presence_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
    group: str,
    stage: str,
) -> dict[str, Any]:
    events = list(grouped.get(stage) or [])
    if not events:
        return _checklist_item(key, group, 'missing', 'missing_stage', stage=stage)
    statuses = {_event_status(event) for event in events}
    if 'ok' in statuses:
        return _checklist_item(
            key,
            group,
            'ok',
            'observed',
            stage=stage,
            evidence={'stage_count': len(events)},
        )
    reason = _compact_reason_from_event(events[-1]) or 'stage_not_ok'
    return _checklist_item(
        key,
        group,
        'degraded',
        reason,
        stage=stage,
        evidence={'stage_count': len(events), 'stage_statuses': sorted(statuses)},
    )


def _prompt_fingerprint_item(
    prompt_payload: Mapping[str, Any],
    *,
    key: str,
    field: str,
    empty_reason: str,
    degraded_when_absent: bool = True,
) -> dict[str, Any]:
    fingerprint = prompt_payload.get(field)
    if isinstance(fingerprint, Mapping):
        evidence: dict[str, Any] = {'fingerprint_present': True}
        if 'present' in fingerprint:
            evidence['block_present'] = bool(fingerprint.get('present'))
            if not bool(fingerprint.get('present')) and field == 'hermeneutic_prompt_injection':
                return _checklist_item(
                    key,
                    'prompt_fingerprints',
                    'degraded',
                    'hermeneutic_block_absent',
                    stage='prompt_prepared',
                    evidence=evidence,
                )
        return _checklist_item(
            key,
            'prompt_fingerprints',
            'ok',
            'observed',
            stage='prompt_prepared',
            evidence=evidence,
        )
    if degraded_when_absent:
        return _checklist_item(
            key,
            'prompt_fingerprints',
            'degraded',
            empty_reason,
            stage='prompt_prepared',
        )
    return _checklist_item(
        key,
        'prompt_fingerprints',
        'not_applicable',
        empty_reason,
        stage='prompt_prepared',
    )


def _llm_call_main_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    llm_events = list(grouped.get('llm_call') or [])
    main_events = [
        event
        for event in llm_events
        if normalize_llm_call_provider_caller(_event_payload(event).get('provider_caller')) == 'llm'
    ]
    if not main_events:
        unknown_count = sum(
            1
            for event in llm_events
            if normalize_llm_call_provider_caller(_event_payload(event).get('provider_caller')) == 'unknown'
        )
        return _checklist_item(
            'llm_call_main',
            'funnel',
            'missing',
            'missing_main_llm_call',
            stage='llm_call',
            evidence={'unknown_llm_call_count': unknown_count, 'llm_call_count': len(llm_events)},
        )
    statuses = {_event_status(event) for event in main_events}
    if 'ok' in statuses:
        return _checklist_item(
            'llm_call_main',
            'funnel',
            'ok',
            'observed',
            stage='llm_call',
            evidence={'main_llm_call_count': len(main_events)},
        )
    return _checklist_item(
        'llm_call_main',
        'funnel',
        'degraded',
        _compact_reason_from_event(main_events[-1]) or 'main_llm_call_not_ok',
        stage='llm_call',
        evidence={'main_llm_call_count': len(main_events), 'stage_statuses': sorted(statuses)},
    )


def _persist_assistant_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    persist_events = list(grouped.get('persist_response') or [])
    assistant_final = [
        event
        for event in persist_events
        if _event_payload(event).get('persist_phase') == 'assistant_final'
    ]
    if assistant_final:
        ok_saved = [
            event
            for event in assistant_final
            if _event_status(event) == 'ok' and bool(_event_payload(event).get('conversation_saved'))
        ]
        if ok_saved:
            return _checklist_item(
                'persist_response_assistant_final',
                'funnel',
                'ok',
                'assistant_final_saved',
                stage='persist_response',
                evidence={'assistant_final_count': len(assistant_final)},
            )
        return _checklist_item(
            'persist_response_assistant_final',
            'funnel',
            'degraded',
            _compact_reason_from_event(assistant_final[-1]) or 'assistant_final_not_saved',
            stage='persist_response',
            evidence={'assistant_final_count': len(assistant_final)},
        )
    interrupted = [
        event
        for event in persist_events
        if _event_payload(event).get('persist_phase') == 'assistant_interrupted'
    ]
    if interrupted:
        return _checklist_item(
            'persist_response_assistant_final',
            'funnel',
            'degraded',
            'assistant_interrupted',
            stage='persist_response',
            evidence={'assistant_interrupted_count': len(interrupted)},
        )
    return _checklist_item(
        'persist_response_assistant_final',
        'funnel',
        'missing',
        'missing_assistant_final_persist',
        stage='persist_response',
        evidence={'persist_response_count': len(persist_events)},
    )


def _web_observability_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    turn_start = _latest_stage_event(grouped, 'turn_start')
    turn_payload = _event_payload(turn_start or {})
    web_requested = bool(turn_payload.get('web_search_enabled'))
    web_events = list(grouped.get('web_search') or [])
    if not web_requested and not web_events:
        return _checklist_item(
            'web_search',
            'web',
            'not_applicable',
            'web_not_requested',
            stage='web_search',
            evidence={'web_requested': False},
        )
    if web_requested and not web_events:
        return _checklist_item(
            'web_search',
            'web',
            'missing',
            'missing_web_search_stage',
            stage='web_search',
            evidence={'web_requested': True},
        )

    latest = web_events[-1]
    payload = _event_payload(latest)
    status = _event_status(latest)
    evidence = {
        'web_requested': web_requested,
        'web_event_count': len(web_events),
        'context_injected': bool(payload.get('context_injected')),
        'results_count': _to_int(payload.get('results_count')),
        'read_state': _payload_text(payload, 'read_state'),
    }
    if not web_requested:
        return _checklist_item(
            'web_search',
            'web',
            'not_applicable',
            _payload_text(payload, 'reason_code') or 'web_not_requested',
            stage='web_search',
            evidence=evidence,
        )
    if status == 'ok':
        return _checklist_item('web_search', 'web', 'ok', 'observed', stage='web_search', evidence=evidence)
    if status == 'skipped' and _payload_text(payload, 'reason_code'):
        return _checklist_item('web_search', 'web', 'ok', 'observed_skipped', stage='web_search', evidence=evidence)
    return _checklist_item(
        'web_search',
        'web',
        'degraded',
        _compact_reason_from_event(latest) or 'web_search_not_ok',
        stage='web_search',
        evidence=evidence,
    )


def _secondary_provider_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
    prepared_stage: str,
    result_stage: str,
    expected: bool,
    provider_caller: str,
) -> dict[str, Any]:
    prepared_events = list(grouped.get(prepared_stage) or [])
    result_events = list(grouped.get(result_stage) or [])
    caller_events = [
        event
        for event in grouped.get('llm_call') or []
        if normalize_llm_call_provider_caller(_event_payload(event).get('provider_caller')) == provider_caller
    ]
    if not expected and caller_events:
        expected = True
    if not expected and not prepared_events and not result_events and not caller_events:
        return _checklist_item(
            key,
            'secondary_providers',
            'not_applicable',
            'not_called',
            evidence={'prepared_count': 0, 'result_count': 0, 'llm_call_count': 0},
        )
    if not prepared_events and not result_events and not caller_events:
        return _checklist_item(
            key,
            'secondary_providers',
            'degraded',
            'missing_secondary_provider_stage',
            evidence={'prepared_stage': prepared_stage, 'result_stage': result_stage},
        )
    events = prepared_events + result_events + caller_events
    statuses = {_event_status(event) for event in events}
    if 'error' in statuses:
        return _checklist_item(
            key,
            'secondary_providers',
            'degraded',
            _compact_reason_from_event(events[-1]) or 'secondary_provider_error',
            evidence={
                'prepared_count': len(prepared_events),
                'result_count': len(result_events),
                'llm_call_count': len(caller_events),
                'stage_statuses': sorted(statuses),
            },
        )
    return _checklist_item(
        key,
        'secondary_providers',
        'ok',
        'observed',
        evidence={
            'prepared_count': len(prepared_events),
            'result_count': len(result_events),
            'llm_call_count': len(caller_events),
        },
    )


def _node_state_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    expected: bool,
) -> dict[str, Any]:
    primary_events = list(grouped.get('primary_node') or [])
    if not primary_events:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded' if expected else 'not_applicable',
            'missing_primary_node' if expected else 'primary_node_not_observed',
            stage='primary_node',
        )
    payload = _event_payload(primary_events[-1])
    has_node_state_fields = any(
        key.startswith('node_state_')
        for key in payload.keys()
    )
    evidence = {
        'primary_node_count': len(primary_events),
        'node_state_read_present': bool(payload.get('node_state_read_present')),
        'node_state_read_valid': bool(payload.get('node_state_read_valid')),
        'node_state_write_attempted': bool(payload.get('node_state_write_attempted')),
        'node_state_write_succeeded': bool(payload.get('node_state_write_succeeded')),
        'node_state_write_changed': bool(payload.get('node_state_write_changed')),
        'node_state_schema_version': _payload_text(payload, 'node_state_schema_version'),
        'fail_open': bool(payload.get('fail_open')),
    }
    if not has_node_state_fields:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            'legacy_node_state_unobserved',
            stage='primary_node',
            evidence=evidence,
        )
    if bool(payload.get('fail_open')):
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'reason_code') or 'primary_node_fail_open',
            stage='primary_node',
            evidence=evidence,
        )
    if payload.get('node_state_read_valid') is False:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'node_state_read_reason_code') or 'node_state_read_invalid',
            stage='primary_node',
            evidence=evidence,
        )
    if bool(payload.get('node_state_write_attempted')) and not bool(payload.get('node_state_write_succeeded')):
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'node_state_write_reason_code') or 'node_state_write_failed',
            stage='primary_node',
            evidence=evidence,
        )
    return _checklist_item(
        'node_state',
        'node_state',
        'ok',
        'observed',
        stage='primary_node',
        evidence=evidence,
    )


def _stage_health_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    error_stages: list[str] = []
    skipped_without_reason: list[str] = []
    for stage, events in grouped.items():
        for event in events:
            status = _event_status(event)
            payload = _event_payload(event)
            if status == 'error':
                error_stages.append(stage)
            if status == 'skipped' and not _payload_text(payload, 'reason_code'):
                skipped_without_reason.append(stage)
    if error_stages:
        return _checklist_item(
            'stage_errors',
            'status',
            'degraded',
            'stage_error_present',
            evidence={
                'error_count': len(error_stages),
                'error_stages': sorted(set(error_stages))[:8],
            },
        )
    if skipped_without_reason:
        return _checklist_item(
            'stage_errors',
            'status',
            'degraded',
            'skipped_without_reason_code',
            evidence={
                'skipped_without_reason_count': len(skipped_without_reason),
                'skipped_stages': sorted(set(skipped_without_reason))[:8],
            },
        )
    return _checklist_item('stage_errors', 'status', 'ok', 'observed')


def build_turn_observability_checklist(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a content-free completeness checklist for one chat turn.

    This is a derived operator view over existing chat_log_events. It must not
    copy raw payload contents; every item is reduced to statuses, counts,
    booleans and compact reason codes.
    """
    safe_events = [event for event in events if isinstance(event, Mapping)]
    grouped = _events_by_stage(safe_events)
    stage_counts = _stage_counts(grouped)
    prompt_event = _latest_stage_event(grouped, 'prompt_prepared')
    prompt_payload = _event_payload(prompt_event or {})

    hermeneutic_expected = any(
        stage in grouped
        for stage in (
            'hermeneutic_node_insertion',
            'primary_node',
            'stimmung_agent',
            'stimmung_prompt_prepared',
            'validation_agent',
            'validation_prompt_prepared',
        )
    ) or isinstance(prompt_payload.get('hermeneutic_prompt_injection'), Mapping)

    memory_payload = prompt_payload.get('memory_prompt_injection')
    memory_retrieval = prompt_payload.get('memory_retrieval')
    memory_absent_but_explained = (
        isinstance(memory_retrieval, Mapping)
        and str(memory_retrieval.get('reason_code') or '').strip() in {'no_data', 'not_applicable'}
    )

    items = [
        _stage_presence_item(grouped, key='turn_start', group='funnel', stage='turn_start'),
        _stage_presence_item(grouped, key='prompt_prepared', group='funnel', stage='prompt_prepared'),
        _llm_call_main_item(grouped),
        _persist_assistant_item(grouped),
        _stage_presence_item(grouped, key='turn_end', group='funnel', stage='turn_end'),
        _prompt_fingerprint_item(
            prompt_payload,
            key='identity_prompt_injection',
            field='identity_prompt_injection',
            empty_reason='missing_identity_prompt_fingerprint',
        ),
        (
            _prompt_fingerprint_item(
                prompt_payload,
                key='memory_prompt_injection',
                field='memory_prompt_injection',
                empty_reason='missing_memory_prompt_fingerprint',
            )
            if isinstance(memory_payload, Mapping) or not memory_absent_but_explained
            else _checklist_item(
                'memory_prompt_injection',
                'prompt_fingerprints',
                'not_applicable',
                'no_memory_data',
                stage='prompt_prepared',
                evidence={'memory_retrieval_reason_code': 'no_data'},
            )
        ),
        _prompt_fingerprint_item(
            prompt_payload,
            key='hermeneutic_prompt_injection',
            field='hermeneutic_prompt_injection',
            empty_reason='missing_hermeneutic_prompt_fingerprint',
            degraded_when_absent=hermeneutic_expected,
        ),
        _secondary_provider_item(
            grouped,
            key='stimmung_agent',
            prepared_stage='stimmung_prompt_prepared',
            result_stage='stimmung_agent',
            expected=hermeneutic_expected,
            provider_caller='stimmung_agent',
        ),
        _secondary_provider_item(
            grouped,
            key='validation_agent',
            prepared_stage='validation_prompt_prepared',
            result_stage='validation_agent',
            expected=hermeneutic_expected,
            provider_caller='validation_agent',
        ),
        _secondary_provider_item(
            grouped,
            key='web_reformulation',
            prepared_stage='web_reformulation_prompt_prepared',
            result_stage='web_reformulation',
            expected=False,
            provider_caller='web_reformulation',
        ),
        _web_observability_item(grouped),
        _node_state_item(grouped, expected=hermeneutic_expected),
        _stage_health_item(grouped),
    ]

    status_counts = {
        status: sum(1 for item in items if item.get('status') == status)
        for status in _TURN_CHECKLIST_ITEM_STATUSES
    }
    applicable_items = [
        item for item in items
        if item.get('status') != 'not_applicable'
    ]
    if not safe_events:
        score = 0
    elif applicable_items:
        weighted_score = sum(
            _TURN_CHECKLIST_SCORE_WEIGHTS.get(str(item.get('status')), 0.0)
            for item in applicable_items
        )
        score = int(round(100 * weighted_score / len(applicable_items)))
    else:
        score = 0

    missing_keys = {
        str(item.get('key'))
        for item in items
        if item.get('status') == 'missing'
    }
    degraded_count = int(status_counts.get('degraded') or 0)
    if not safe_events or missing_keys.intersection(_TURN_CHECKLIST_LEGACY_CRITICAL_ITEMS):
        classification = 'legacy_incomplete'
    elif missing_keys:
        classification = 'partial'
    elif degraded_count:
        classification = 'degraded'
    else:
        classification = 'complete'

    conversation_id = None
    turn_id = None
    for event in safe_events:
        if conversation_id is None:
            conversation_id = str(event.get('conversation_id') or '').strip() or None
        if turn_id is None:
            turn_id = str(event.get('turn_id') or '').strip() or None
        if conversation_id and turn_id:
            break

    return {
        'kind': 'turn_observability_checklist',
        'conversation_id': conversation_id,
        'turn_id': turn_id,
        'events_count': len(safe_events),
        'stage_counts': stage_counts,
        'score': score,
        'classification': classification,
        'status_counts': status_counts,
        'items': items,
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
