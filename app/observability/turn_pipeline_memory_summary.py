from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.turn_pipeline_summary_support import (
    _event_ts,
    _events_for_stage,
    _latest_stage_event,
    _mapping,
    _payload,
    _reason_code,
    _sequence,
    _sha256_12_text,
    _status,
    _text,
    _to_int,
)


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


def build_memory_rag_summary(events: Sequence[Mapping[str, Any]], prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
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
