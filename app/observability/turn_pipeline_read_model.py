from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from observability.turn_observability_checklist import build_turn_observability_checklist


SCHEMA_VERSION = '1'
_MAIN_PROVIDER_CALLER = 'llm'
_SECONDARY_PROVIDER_CALLERS = (
    ('stimmung', 'stimmung_agent', 'stimmung_prompt_prepared', 'stimmung_agent'),
    ('validation', 'validation_agent', 'validation_prompt_prepared', 'validation_agent'),
    ('web_reformulation', 'web_reformulation', 'web_reformulation_prompt_prepared', 'web_reformulation'),
)
_KNOWN_PROVIDER_CALLERS = {
    _MAIN_PROVIDER_CALLER,
    'stimmung_agent',
    'validation_agent',
    'web_reformulation',
}


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


def _stage(event: Mapping[str, Any]) -> str:
    return str(event.get('stage') or '').strip()


def _status(event: Mapping[str, Any]) -> str:
    return str(event.get('status') or '').strip().lower()


def _event_ts(event: Mapping[str, Any]) -> str | None:
    return _text(event.get('ts'))


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return str(event.get('ts') or ''), str(event.get('event_id') or '')


def _safe_events(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        [event for event in events if isinstance(event, Mapping)],
        key=_event_sort_key,
    )


def _events_for_stage(events: Sequence[Mapping[str, Any]], stage: str) -> list[Mapping[str, Any]]:
    return [event for event in events if _stage(event) == stage]


def _latest_stage_event(events: Sequence[Mapping[str, Any]], stage: str) -> Mapping[str, Any] | None:
    items = _events_for_stage(events, stage)
    return items[-1] if items else None


def _reason_code(payload: Mapping[str, Any]) -> str | None:
    for key in ('reason_code', 'error_code', 'error_class'):
        text = _text(payload.get(key))
        if text:
            return text
    return None


def _sha256_12_from_payload(payload: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _text(payload.get(key))
        if value:
            return value[:12]
    return None


def _sha256_12_text(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _normalize_provider_caller(value: Any) -> str:
    caller = str(value or '').strip().lower()
    if caller in _KNOWN_PROVIDER_CALLERS:
        return caller
    return 'unknown'


def _duration_ms(event: Mapping[str, Any] | None) -> int | None:
    if not event:
        return None
    value = event.get('duration_ms')
    if value is None:
        return None
    return _to_int(value)


def _stage_counts(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        stage = _stage(event)
        if not stage:
            continue
        counts[stage] = counts.get(stage, 0) + 1
    return dict(sorted(counts.items()))


def _checklist_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checklist = build_turn_observability_checklist(events)
    compact_items: list[dict[str, Any]] = []
    for item in checklist.get('items') or []:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get('status') or '').strip()
        if status not in {'missing', 'degraded'}:
            continue
        compact_items.append(
            {
                'key': str(item.get('key') or ''),
                'group': str(item.get('group') or ''),
                'status': status,
                'reason_code': str(item.get('reason_code') or 'unknown'),
                'stage': _text(item.get('stage')),
            }
        )
    return {
        'classification': str(checklist.get('classification') or 'legacy_incomplete'),
        'score': _to_int(checklist.get('score')),
        'status_counts': dict(_mapping(checklist.get('status_counts'))),
        'degraded_or_missing_items': compact_items[:12],
    }


def _persistence_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    persist_events = _events_for_stage(events, 'persist_response')
    assistant_final = [
        event for event in persist_events
        if _payload(event).get('persist_phase') == 'assistant_final'
    ]
    interrupted = [
        event for event in persist_events
        if _payload(event).get('persist_phase') == 'assistant_interrupted'
    ]
    selected = (
        assistant_final[-1]
        if assistant_final
        else (interrupted[-1] if interrupted else (persist_events[-1] if persist_events else None))
    )
    selected_payload = _payload(selected or {})
    assistant_final_saved = any(
        _status(event) == 'ok' and bool(_payload(event).get('conversation_saved'))
        for event in assistant_final
    )
    if assistant_final_saved:
        status = 'saved'
        reason = 'assistant_final_saved'
    elif interrupted:
        status = 'interrupted'
        reason = _reason_code(_payload(interrupted[-1])) or 'assistant_interrupted'
    elif assistant_final:
        status = 'not_saved'
        reason = _reason_code(selected_payload) or 'assistant_final_not_saved'
    else:
        status = 'missing'
        reason = 'missing_assistant_final_persist'
    return {
        'status': status,
        'assistant_final_present': bool(assistant_final),
        'assistant_final_saved': assistant_final_saved,
        'assistant_interrupted': bool(interrupted),
        'reason_code': reason,
        'events_count': len(persist_events),
        'messages_written': _to_int(selected_payload.get('messages_written')),
        'latest_ts': _event_ts(selected or {}),
    }


def _llm_call_summary(event: Mapping[str, Any] | None, *, provider_caller: str) -> dict[str, Any]:
    payload = _payload(event or {})
    return {
        'provider_caller': provider_caller,
        'present': bool(event),
        'status': _status(event or {}) if event else 'missing',
        'duration_ms': _duration_ms(event),
        'response_chars': _to_int(payload.get('response_chars')),
        'model': _text(payload.get('model')),
        'provider_title': _text(payload.get('provider_title')),
        'provider_model': _text(payload.get('provider_model')),
        'reason_code': _reason_code(payload),
        'latest_ts': _event_ts(event or {}),
    }


def _providers_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    llm_events = _events_for_stage(events, 'llm_call')
    main_events = [
        event for event in llm_events
        if _normalize_provider_caller(_payload(event).get('provider_caller')) == _MAIN_PROVIDER_CALLER
    ]
    unknown_count = sum(
        1 for event in llm_events
        if _normalize_provider_caller(_payload(event).get('provider_caller')) == 'unknown'
    )
    main = _llm_call_summary(main_events[-1] if main_events else None, provider_caller=_MAIN_PROVIDER_CALLER)
    if not main_events:
        main['reason_code'] = 'missing_main_llm_call'

    secondary: dict[str, dict[str, Any]] = {}
    for key, provider_caller, prepared_stage, result_stage in _SECONDARY_PROVIDER_CALLERS:
        prepared_events = _events_for_stage(events, prepared_stage)
        result_events = _events_for_stage(events, result_stage)
        caller_events = [
            event for event in llm_events
            if _normalize_provider_caller(_payload(event).get('provider_caller')) == provider_caller
        ]
        latest = (
            caller_events[-1]
            if caller_events
            else (result_events[-1] if result_events else (prepared_events[-1] if prepared_events else None))
        )
        status_values = {_status(event) for event in [*prepared_events, *result_events, *caller_events] if _status(event)}
        if 'error' in status_values:
            status = 'error'
        elif prepared_events or result_events or caller_events:
            status = 'ok'
        else:
            status = 'not_applicable'
        summary = _llm_call_summary(caller_events[-1] if caller_events else None, provider_caller=provider_caller)
        summary.update(
            {
                'status': status,
                'prepared_present': bool(prepared_events),
                'result_present': bool(result_events),
                'llm_call_present': bool(caller_events),
                'prepared_events_count': len(prepared_events),
                'result_events_count': len(result_events),
                'llm_call_events_count': len(caller_events),
                'reason_code': _reason_code(_payload(latest or {})),
                'latest_ts': _event_ts(latest or {}),
            }
        )
        secondary[key] = summary

    return {
        'main': main,
        'secondary': secondary,
        'unknown_llm_call_count': unknown_count,
    }


def _memory_lane_count(memory_payload: Mapping[str, Any], new_key: str, legacy_key: str) -> int:
    if new_key in memory_payload:
        return _to_int(memory_payload.get(new_key))
    return _to_int(memory_payload.get(legacy_key))


def _safe_parent_summary_items(value: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for raw_item in _sequence(value):
        item = _mapping(raw_item)
        summary_id = _text(item.get('summary_id')) or _text(item.get('id'))
        if not summary_id:
            continue
        items.append(
            {
                'summary_id': summary_id,
                'summary_id_sha256_12': _text(item.get('summary_id_sha256_12')) or _sha256_12_text(summary_id),
                'start_ts': _text(item.get('start_ts')),
                'end_ts': _text(item.get('end_ts')),
                'linked_trace_count': _to_int(item.get('linked_trace_count')) or 1,
            }
        )
    return items


def _injected_ids_from_memory_inputs(
    events: Sequence[Mapping[str, Any]],
    memory_payload: Mapping[str, Any],
) -> set[str]:
    injected_ids = {
        str(item).strip()
        for item in _sequence(memory_payload.get('injected_candidate_ids'))
        if str(item).strip()
    }
    if injected_ids:
        return injected_ids
    insertion = _latest_stage_event(events, 'hermeneutic_node_insertion')
    inputs = _mapping(_payload(insertion or {}).get('inputs'))
    arbitration = _mapping(inputs.get('memory_arbitration'))
    return {
        str(item).strip()
        for item in _sequence(arbitration.get('injected_candidate_ids'))
        if str(item).strip()
    }


def _parent_summary_fields(
    events: Sequence[Mapping[str, Any]],
    memory_payload: Mapping[str, Any],
) -> dict[str, Any]:
    direct_parent_summaries = _safe_parent_summary_items(memory_payload.get('parent_summaries_injected'))
    direct_traces_with_summary = _to_int(memory_payload.get('injected_traces_with_summary_id_count'))
    direct_traces_with_parent = _to_int(memory_payload.get('injected_traces_with_parent_summary_count'))
    memory_context_injected = bool(memory_payload.get('memory_context_injected')) or _to_int(
        memory_payload.get('memory_context_summary_count')
    ) > 0
    if direct_parent_summaries or direct_traces_with_summary or direct_traces_with_parent:
        return {
            'summary_parent_source_kind': 'prompt_prepared_memory_prompt_injection',
            'injected_traces_with_summary_id_count': direct_traces_with_summary,
            'injected_traces_with_parent_summary_count': direct_traces_with_parent,
            'parent_summaries_resolved_count': _to_int(
                memory_payload.get('parent_summaries_resolved_count')
            ) or len(direct_parent_summaries),
            'parent_summaries_injected_count': (
                _to_int(memory_payload.get('parent_summaries_injected_count'))
                or (len(direct_parent_summaries) if memory_context_injected else 0)
            ),
            'parent_summaries_injected': direct_parent_summaries if memory_context_injected else [],
        }

    insertion = _latest_stage_event(events, 'hermeneutic_node_insertion')
    inputs = _mapping(_payload(insertion or {}).get('inputs'))
    retrieved = _mapping(inputs.get('memory_retrieved'))
    traces = _sequence(retrieved.get('traces'))
    injected_ids = _injected_ids_from_memory_inputs(events, memory_payload)
    if not traces or not injected_ids:
        return {
            'summary_parent_source_kind': 'not_materialized',
            'injected_traces_with_summary_id_count': 0,
            'injected_traces_with_parent_summary_count': 0,
            'parent_summaries_resolved_count': 0,
            'parent_summaries_injected_count': 0,
            'parent_summaries_injected': [],
        }

    traces_with_summary_id = 0
    traces_with_parent_summary = 0
    parent_summaries_by_id: dict[str, dict[str, Any]] = {}
    for raw_trace in traces:
        trace = _mapping(raw_trace)
        candidate_id = _text(trace.get('candidate_id'))
        if not candidate_id or candidate_id not in injected_ids:
            continue
        if _text(trace.get('source_kind')) == 'summary':
            continue
        parent_summary = _mapping(trace.get('parent_summary'))
        summary_id = _text(trace.get('summary_id')) or _text(parent_summary.get('id'))
        if summary_id:
            traces_with_summary_id += 1
        if not parent_summary:
            continue
        parent_id = _text(parent_summary.get('id')) or summary_id
        if not parent_id:
            continue
        traces_with_parent_summary += 1
        item = parent_summaries_by_id.setdefault(
            parent_id,
            {
                'summary_id': parent_id,
                'summary_id_sha256_12': _sha256_12_text(parent_id),
                'start_ts': _text(parent_summary.get('start_ts')),
                'end_ts': _text(parent_summary.get('end_ts')),
                'linked_trace_count': 0,
            },
        )
        item['linked_trace_count'] = _to_int(item.get('linked_trace_count')) + 1
        if not item.get('start_ts') and parent_summary.get('start_ts'):
            item['start_ts'] = _text(parent_summary.get('start_ts'))
        if not item.get('end_ts') and parent_summary.get('end_ts'):
            item['end_ts'] = _text(parent_summary.get('end_ts'))

    parent_summaries = sorted(
        parent_summaries_by_id.values(),
        key=lambda item: str(item.get('summary_id') or ''),
    )
    return {
        'summary_parent_source_kind': 'hermeneutic_node_insertion_inputs',
        'injected_traces_with_summary_id_count': traces_with_summary_id,
        'injected_traces_with_parent_summary_count': traces_with_parent_summary,
        'parent_summaries_resolved_count': len(parent_summaries),
        'parent_summaries_injected_count': len(parent_summaries) if memory_context_injected else 0,
        'parent_summaries_injected': parent_summaries if memory_context_injected else [],
    }


def _embedding_counts(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    embedding_events = _events_for_stage(events, 'embedding')
    status_counts: dict[str, int] = {}
    source_kind_counts: dict[str, int] = {}
    dimension_counts: dict[str, int] = {}
    latest_ts: str | None = None

    for event in embedding_events:
        payload = _payload(event)
        status = _status(event) or 'unknown'
        status_counts[status] = status_counts.get(status, 0) + 1

        source_kind = _text(payload.get('source_kind')) or 'unknown'
        source_kind_counts[source_kind] = source_kind_counts.get(source_kind, 0) + 1

        dimensions = _to_int(payload.get('dimensions'))
        dimension_key = str(dimensions) if dimensions > 0 else 'unknown'
        dimension_counts[dimension_key] = dimension_counts.get(dimension_key, 0) + 1

        latest_ts = _event_ts(event) or latest_ts

    success_count = status_counts.get('ok', 0) + status_counts.get('success', 0)
    error_count = sum(
        count
        for status, count in status_counts.items()
        if status not in {'ok', 'success'}
    )
    return {
        'embeddings_source_kind': 'chat_log_events.embedding',
        'embeddings_requested_count': len(embedding_events),
        'embeddings_success_count': success_count,
        'embeddings_error_count': error_count,
        'embeddings_status_counts': dict(sorted(status_counts.items())),
        'embeddings_source_kind_counts': dict(sorted(source_kind_counts.items())),
        'embeddings_dimension_counts': dict(sorted(dimension_counts.items())),
        'embeddings_latest_ts': latest_ts,
    }


def _rag_summary(events: Sequence[Mapping[str, Any]], prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    embedding_counts = _embedding_counts(events)
    summaries_event = _latest_stage_event(events, 'summaries')
    summaries_payload = _payload(summaries_event or {})
    memory_payload = _mapping(prompt_payload.get('memory_prompt_injection'))
    summary_context_count = _memory_lane_count(
        memory_payload,
        'summary_context_injected_count',
        'memory_context_summary_count',
    )
    memory_context_summary_count = _to_int(memory_payload.get('memory_context_summary_count'))
    parent_summary_fields = _parent_summary_fields(events, memory_payload)
    active_summary_present = bool(summaries_payload.get('active_summary_present'))
    active_summary_in_prompt = bool(summaries_payload.get('in_prompt'))
    active_summary_count = (
        _to_int(summaries_payload.get('summary_count_used'))
        if summaries_event
        else max(0, summary_context_count - memory_context_summary_count)
    )
    summary_fields = {
        'conversation_summary_source_kind': 'summaries_event' if summaries_event else 'prompt_prepared_memory_prompt_injection',
        'conversation_summary_event_present': bool(summaries_event),
        'conversation_summary_status': _status(summaries_event or {}) if summaries_event else 'unknown',
        'conversation_summary_active_present': active_summary_present,
        'conversation_summary_in_prompt': active_summary_in_prompt,
        'conversation_summary_count': active_summary_count,
        'summary_context_injected': bool(memory_payload.get('summary_context_injected')) or summary_context_count > 0,
        'summary_context_injected_count': summary_context_count,
        'memory_context_summary_count': memory_context_summary_count,
        'summary_generation_observed': bool(summaries_payload.get('summary_generation_observed')),
        'summary_reason_code': _reason_code(summaries_payload),
        **parent_summary_fields,
    }
    snapshot_event = _latest_stage_event(events, 'memory_chain_snapshot')
    snapshot_payload = _payload(snapshot_event or {})
    if snapshot_payload:
        retrieval = _mapping(snapshot_payload.get('retrieval'))
        basket = _mapping(snapshot_payload.get('basket'))
        arbiter = _mapping(snapshot_payload.get('arbiter'))
        injection = _mapping(snapshot_payload.get('injection'))
        return {
            'source_kind': 'memory_chain_snapshot',
            'status': _text(retrieval.get('status')) or _status(snapshot_event or {}) or 'missing',
            'reason_code': (
                _reason_code(retrieval)
                or _reason_code(basket)
                or _reason_code(arbiter)
            ),
            'retrieved': _to_int(retrieval.get('retrieved_count')),
            'basket': _to_int(basket.get('basket_candidates_count')),
            'deduped_retrieved': _to_int(basket.get('deduped_retrieved_count')),
            'kept': _to_int(arbiter.get('kept_count')),
            'rejected': _to_int(arbiter.get('rejected_count')),
            'injected': _to_int(injection.get('injected_candidate_count')),
            'context_hints': _to_int(injection.get('context_hints_count')),
            'truncated': bool(snapshot_payload.get('truncated')),
            'legacy_reason_code': None,
            'latest_ts': _event_ts(snapshot_event or {}),
            **summary_fields,
            **embedding_counts,
        }

    retrieval = _mapping(prompt_payload.get('memory_retrieval'))
    injected_ids = _sequence(memory_payload.get('injected_candidate_ids'))
    trace_count = _memory_lane_count(memory_payload, 'trace_memory_injected_count', 'memory_traces_injected_count')
    hints_count = _to_int(memory_payload.get('context_hints_injected_count'))
    injected_count = len(injected_ids) if injected_ids else trace_count + summary_context_count
    return {
        'source_kind': 'prompt_prepared_legacy_fallback',
        'status': _text(retrieval.get('status')) or ('ok' if memory_payload else 'missing'),
        'reason_code': _reason_code(retrieval),
        'retrieved': _to_int(retrieval.get('top_k_returned')),
        'basket': None,
        'deduped_retrieved': None,
        'kept': None,
        'rejected': None,
        'injected': injected_count,
        'context_hints': hints_count,
        'truncated': False,
        'legacy_reason_code': 'missing_memory_chain_snapshot',
        'latest_ts': _event_ts(_latest_stage_event(events, 'prompt_prepared') or {}),
        **summary_fields,
        **embedding_counts,
    }


def _identity_summary(prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    fingerprint = _mapping(prompt_payload.get('identity_prompt_injection'))
    present = bool(fingerprint.get('injected')) or bool(fingerprint.get('identity_block_present'))
    status = 'present' if present else ('missing' if not fingerprint else 'absent')
    used_ids = fingerprint.get('used_identity_ids')
    used_count = (
        len(_sequence(used_ids))
        if used_ids is not None
        else _to_int(fingerprint.get('used_identity_ids_count'))
    )
    return {
        'source_kind': 'prompt_identity_fingerprint' if fingerprint else 'missing',
        'status': status,
        'block_present': bool(fingerprint.get('identity_block_present')),
        'injected': bool(fingerprint.get('injected')),
        'chars': _to_int(
            fingerprint.get('chars')
            or fingerprint.get('identity_block_chars')
            or fingerprint.get('identity_chars')
        ),
        'sha256_12': _sha256_12_from_payload(fingerprint, 'sha256_12', 'identity_block_sha256_12'),
        'used_identity_ids_count': used_count,
        'staging_included': bool(fingerprint.get('staging_included')),
        'reason_code': _reason_code(fingerprint),
    }


def _hermeneutic_summary(events: Sequence[Mapping[str, Any]], prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    fingerprint = _mapping(prompt_payload.get('hermeneutic_prompt_injection'))
    present = bool(fingerprint.get('present'))
    status = 'present' if present else ('missing' if not fingerprint else 'absent')
    primary = _latest_stage_event(events, 'primary_node')
    primary_payload = _payload(primary or {})
    node_state = {
        'primary_node_present': bool(primary),
        'read_present': bool(primary_payload.get('node_state_read_present')),
        'read_valid': bool(primary_payload.get('node_state_read_valid')),
        'read_reason_code': _text(primary_payload.get('node_state_read_reason_code')),
        'write_attempted': bool(primary_payload.get('node_state_write_attempted')),
        'write_succeeded': bool(primary_payload.get('node_state_write_succeeded')),
        'write_changed': bool(primary_payload.get('node_state_write_changed')),
        'write_reason_code': _text(primary_payload.get('node_state_write_reason_code')),
        'schema_version': _text(primary_payload.get('node_state_schema_version')),
        'sha256_12': _sha256_12_from_payload(primary_payload, 'node_state_sha256_12'),
        'fail_open': bool(primary_payload.get('fail_open')),
        'fallback_used': bool(primary_payload.get('fallback_used')),
        'reason_code': _reason_code(primary_payload),
    }
    return {
        'source_kind': 'prompt_hermeneutic_fingerprint' if fingerprint else 'missing',
        'status': status,
        'block_present': present,
        'chars': _to_int(fingerprint.get('chars')),
        'sha256_12': _sha256_12_from_payload(fingerprint, 'sha256_12'),
        'final_posture': _text(fingerprint.get('posture') or fingerprint.get('final_posture')),
        'epistemic_regime': _text(fingerprint.get('epistemic_regime')),
        'fallback': bool(fingerprint.get('fallback')),
        'reason_code': _reason_code(fingerprint),
        'node_state': node_state,
    }


def _web_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    turn_start = _latest_stage_event(events, 'turn_start')
    turn_payload = _payload(turn_start or {})
    web_events = _events_for_stage(events, 'web_search')
    latest = web_events[-1] if web_events else None
    payload = _payload(latest or {})
    requested = bool(turn_payload.get('web_search_enabled')) or any(
        bool(_payload(event).get('enabled')) for event in web_events
    )
    if latest:
        status = _status(latest)
        reason = _reason_code(payload)
    elif requested:
        status = 'missing'
        reason = 'missing_web_search_stage'
    else:
        status = 'not_applicable'
        reason = 'web_not_requested'
    injected_chars = _to_int(payload.get('injected_chars') or payload.get('context_chars'))
    legacy_query = _text(payload.get('query'))
    query_chars = _to_int(payload.get('query_chars')) or (len(legacy_query) if legacy_query else 0)
    return {
        'requested': requested,
        'event_present': bool(latest),
        'status': status,
        'success': status == 'ok',
        'skipped': status == 'skipped',
        'error': status == 'error',
        'reason_code': reason,
        'results_count': _to_int(payload.get('results_count')),
        'injected': bool(payload.get('context_injected')) or injected_chars > 0,
        'injected_chars': injected_chars,
        'query_present': bool(payload.get('query_present')) or bool(legacy_query),
        'query_chars': query_chars,
        'query_sha256_12': _sha256_12_from_payload(payload, 'query_sha256_12') or _sha256_12_text(legacy_query),
        'read_state': _text(payload.get('read_state')),
        'truncated': bool(payload.get('truncated')),
        'latest_ts': _event_ts(latest or {}),
    }


def _latencies_summary(events: Sequence[Mapping[str, Any]], providers: Mapping[str, Any]) -> dict[str, Any]:
    turn_end = _latest_stage_event(events, 'turn_end')
    turn_payload = _payload(turn_end or {})
    secondary = _mapping(providers.get('secondary'))
    secondary_duration = sum(
        _to_int(_mapping(item).get('duration_ms'))
        for item in secondary.values()
        if isinstance(item, Mapping)
    )
    return {
        'total_duration_ms': (
            _to_int(turn_payload.get('total_duration_ms'))
            if turn_payload.get('total_duration_ms') is not None
            else None
        ),
        'main_llm_duration_ms': _mapping(providers.get('main')).get('duration_ms'),
        'secondary_llm_duration_ms_total': secondary_duration,
        'observed_duration_ms_total': sum(
            _to_int(event.get('duration_ms'))
            for event in events
            if event.get('duration_ms') is not None
        ),
    }


def _errors_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_stage_status: dict[tuple[str, str, str], int] = {}
    reason_code_counts: dict[str, int] = {}
    fallback_count = 0
    for event in events:
        status = _status(event)
        payload = _payload(event)
        stage = _stage(event) or 'unknown'
        reason = _reason_code(payload) or 'unknown'
        if status in {'error', 'skipped'}:
            key = (stage, status, reason)
            by_stage_status[key] = by_stage_status.get(key, 0) + 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
        if bool(payload.get('fail_open')) or bool(payload.get('fallback_used')):
            fallback_count += 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
    stages = [
        {
            'stage': stage,
            'status': status,
            'reason_code': reason,
            'count': count,
        }
        for (stage, status, reason), count in sorted(by_stage_status.items())
    ]
    return {
        'error_count': sum(1 for event in events if _status(event) == 'error'),
        'skipped_count': sum(1 for event in events if _status(event) == 'skipped'),
        'fallback_count': fallback_count,
        'reason_code_counts': dict(sorted(reason_code_counts.items())),
        'stages': stages[:16],
    }


def build_turn_pipeline_item(
    events: Sequence[Mapping[str, Any]],
    *,
    events_total: int | None = None,
    events_truncated: bool = False,
) -> dict[str, Any]:
    """Build one content-free cockpit row for a chat turn.

    The projection is derived from existing chat log events and prompt
    fingerprints. It never includes raw event payloads.
    """
    safe_events = _safe_events(events)
    first = safe_events[0] if safe_events else {}
    latest = safe_events[-1] if safe_events else {}
    conversation_id = _text(first.get('conversation_id'))
    turn_id = _text(first.get('turn_id'))
    prompt_payload = _payload(_latest_stage_event(safe_events, 'prompt_prepared') or {})
    checklist = _checklist_summary(safe_events)
    providers = _providers_summary(safe_events)
    rag = _rag_summary(safe_events, prompt_payload)

    classification = str(checklist.get('classification') or 'legacy_incomplete')
    legacy_reason = None
    if classification == 'legacy_incomplete':
        legacy_reason = 'legacy_incomplete'
    elif rag.get('legacy_reason_code'):
        legacy_reason = str(rag.get('legacy_reason_code'))

    events_read = len(safe_events)
    total = events_read if events_total is None else _to_int(events_total)
    return {
        'kind': 'chat_turn_pipeline_item',
        'schema_version': SCHEMA_VERSION,
        'conversation_id': conversation_id,
        'turn_id': turn_id,
        'first_ts': _event_ts(first),
        'latest_ts': _event_ts(latest),
        'classification': classification,
        'score': checklist.get('score'),
        'checklist': checklist,
        'persistence': _persistence_summary(safe_events),
        'providers': providers,
        'rag': rag,
        'identity': _identity_summary(prompt_payload),
        'hermeneutic': _hermeneutic_summary(safe_events, prompt_payload),
        'web': _web_summary(safe_events),
        'latencies': _latencies_summary(safe_events, providers),
        'errors': _errors_summary(safe_events),
        'stage_counts': _stage_counts(safe_events),
        'flags': {
            'events_truncated': bool(events_truncated),
            'source_kind': 'chat_log_events',
            'legacy_reason_code': legacy_reason,
            'raw_event_payloads_included': False,
        },
        'source': {
            'events_total': total,
            'events_read': events_read,
            'events_truncated': bool(events_truncated),
            'source_kind': 'chat_log_events',
            'memory_chain_snapshot_present': bool(_latest_stage_event(safe_events, 'memory_chain_snapshot')),
        },
    }
