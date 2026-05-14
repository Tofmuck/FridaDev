from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.turn_observability_checklist import build_turn_observability_checklist


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = event.get('payload')
    if not isinstance(payload, Mapping):
        payload = event.get('payload_json')
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _stage(event: Mapping[str, Any]) -> str:
    return str(event.get('stage') or '').strip()


def _status(event: Mapping[str, Any]) -> str:
    return str(event.get('status') or '').strip().lower()


def _turn_key(event: Mapping[str, Any]) -> tuple[str, str]:
    conversation_id = str(event.get('conversation_id') or 'unknown_conversation').strip()
    turn_id = str(event.get('turn_id') or 'unknown_turn').strip()
    return conversation_id or 'unknown_conversation', turn_id or 'unknown_turn'


def _event_sort_key(event: Mapping[str, Any]) -> tuple[str, str]:
    return str(event.get('ts') or ''), str(event.get('event_id') or '')


def _safe_events(events: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return sorted(
        [event for event in events if isinstance(event, Mapping)],
        key=_event_sort_key,
    )


def _group_by_turn(events: Sequence[Mapping[str, Any]]) -> dict[tuple[str, str], list[Mapping[str, Any]]]:
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for event in events:
        grouped.setdefault(_turn_key(event), []).append(event)
    return grouped


def _latest_stage_payload(events: Sequence[Mapping[str, Any]], stage: str) -> dict[str, Any]:
    latest: Mapping[str, Any] | None = None
    for event in events:
        if _stage(event) == stage:
            latest = event
    return _payload(latest or {})


def _inc(mapping: dict[str, int], key: Any, amount: int = 1) -> None:
    normalized = str(key or 'unknown').strip() or 'unknown'
    mapping[normalized] = int(mapping.get(normalized, 0)) + int(amount)


def _empty_prompt_lane_metrics() -> dict[str, Any]:
    return {
        'trace_memory': {'turns_injected': 0, 'items_injected_total': 0},
        'summary_context': {'turns_injected': 0, 'items_injected_total': 0},
        'context_hints': {'turns_injected': 0, 'items_injected_total': 0},
        'identity_block': {'turns_present': 0, 'chars_total': 0},
        'hermeneutic_block': {'turns_present': 0, 'chars_total': 0},
        'turns_with_any_lane': 0,
        'turns_with_mixed_lanes': 0,
    }


def _memory_lane_count(memory_payload: Mapping[str, Any], new_key: str, legacy_key: str) -> int:
    return _to_int(memory_payload.get(new_key) if new_key in memory_payload else memory_payload.get(legacy_key))


def _add_prompt_lane_metrics(metrics: dict[str, Any], prompt_payload: Mapping[str, Any]) -> None:
    memory_payload = prompt_payload.get('memory_prompt_injection')
    if not isinstance(memory_payload, Mapping):
        memory_payload = {}
    identity_payload = prompt_payload.get('identity_prompt_injection')
    if not isinstance(identity_payload, Mapping):
        identity_payload = {}
    hermeneutic_payload = prompt_payload.get('hermeneutic_prompt_injection')
    if not isinstance(hermeneutic_payload, Mapping):
        hermeneutic_payload = {}

    lane_hits = 0
    trace_count = _memory_lane_count(memory_payload, 'trace_memory_injected_count', 'memory_traces_injected_count')
    summary_count = _memory_lane_count(memory_payload, 'summary_context_injected_count', 'memory_context_summary_count')
    hints_count = _to_int(memory_payload.get('context_hints_injected_count'))

    if bool(memory_payload.get('trace_memory_injected')) or bool(memory_payload.get('memory_traces_injected')) or trace_count > 0:
        metrics['trace_memory']['turns_injected'] += 1
        metrics['trace_memory']['items_injected_total'] += trace_count
        lane_hits += 1
    if bool(memory_payload.get('summary_context_injected')) or bool(memory_payload.get('memory_context_injected')) or summary_count > 0:
        metrics['summary_context']['turns_injected'] += 1
        metrics['summary_context']['items_injected_total'] += summary_count
        lane_hits += 1
    if bool(memory_payload.get('context_hints_injected')) or hints_count > 0:
        metrics['context_hints']['turns_injected'] += 1
        metrics['context_hints']['items_injected_total'] += hints_count
        lane_hits += 1
    if bool(identity_payload.get('injected')) or bool(identity_payload.get('identity_block_present')):
        metrics['identity_block']['turns_present'] += 1
        metrics['identity_block']['chars_total'] += _to_int(
            identity_payload.get('chars')
            or identity_payload.get('identity_block_chars')
            or identity_payload.get('identity_chars')
        )
        lane_hits += 1
    if bool(hermeneutic_payload.get('present')):
        metrics['hermeneutic_block']['turns_present'] += 1
        metrics['hermeneutic_block']['chars_total'] += _to_int(hermeneutic_payload.get('chars'))
        lane_hits += 1

    if lane_hits > 0:
        metrics['turns_with_any_lane'] += 1
    if lane_hits > 1:
        metrics['turns_with_mixed_lanes'] += 1


def _empty_rag_funnel_metrics() -> dict[str, Any]:
    return {
        'turns_with_snapshot': 0,
        'retrieved_turns': 0,
        'retrieved_candidates_total': 0,
        'basketed_turns': 0,
        'basketed_candidates_total': 0,
        'deduped_retrieved_total': 0,
        'kept_turns': 0,
        'kept_candidates_total': 0,
        'injected_turns': 0,
        'injected_candidates_total': 0,
        'prompt_fallback_turns': 0,
    }


def _add_rag_funnel_metrics(
    metrics: dict[str, Any],
    *,
    snapshot_payload: Mapping[str, Any],
    prompt_payload: Mapping[str, Any],
) -> None:
    if snapshot_payload:
        metrics['turns_with_snapshot'] += 1
        retrieval = snapshot_payload.get('retrieval')
        basket = snapshot_payload.get('basket')
        arbiter = snapshot_payload.get('arbiter')
        injection = snapshot_payload.get('injection')
        retrieval = retrieval if isinstance(retrieval, Mapping) else {}
        basket = basket if isinstance(basket, Mapping) else {}
        arbiter = arbiter if isinstance(arbiter, Mapping) else {}
        injection = injection if isinstance(injection, Mapping) else {}

        retrieved_count = _to_int(retrieval.get('retrieved_count'))
        basket_count = _to_int(basket.get('basket_candidates_count'))
        kept_count = _to_int(arbiter.get('kept_count'))
        injected_count = _to_int(injection.get('injected_candidate_count'))
        metrics['retrieved_candidates_total'] += retrieved_count
        metrics['basketed_candidates_total'] += basket_count
        metrics['deduped_retrieved_total'] += _to_int(basket.get('deduped_retrieved_count'))
        metrics['kept_candidates_total'] += kept_count
        metrics['injected_candidates_total'] += injected_count
        if retrieved_count > 0:
            metrics['retrieved_turns'] += 1
        if basket_count > 0:
            metrics['basketed_turns'] += 1
        if kept_count > 0:
            metrics['kept_turns'] += 1
        if injected_count > 0:
            metrics['injected_turns'] += 1
        return

    memory_retrieval = prompt_payload.get('memory_retrieval')
    memory_payload = prompt_payload.get('memory_prompt_injection')
    memory_retrieval = memory_retrieval if isinstance(memory_retrieval, Mapping) else {}
    memory_payload = memory_payload if isinstance(memory_payload, Mapping) else {}
    retrieved_count = _to_int(memory_retrieval.get('top_k_returned'))
    injected_ids = memory_payload.get('injected_candidate_ids')
    injected_count = len(injected_ids) if isinstance(injected_ids, Sequence) and not isinstance(injected_ids, (str, bytes)) else 0
    if retrieved_count or injected_count:
        metrics['prompt_fallback_turns'] += 1
    if retrieved_count > 0:
        metrics['retrieved_turns'] += 1
        metrics['retrieved_candidates_total'] += retrieved_count
    if injected_count > 0:
        metrics['injected_turns'] += 1
        metrics['injected_candidates_total'] += injected_count


def _empty_node_state_metrics() -> dict[str, Any]:
    return {
        'primary_node_events': 0,
        'read_observed_count': 0,
        'read_hit_count': 0,
        'read_miss_count': 0,
        'read_invalid_count': 0,
        'read_hit_rate': None,
        'invalid_rate': None,
        'write_attempted_count': 0,
        'write_changed_count': 0,
        'write_unchanged_count': 0,
        'write_failed_count': 0,
        'write_skipped_count': 0,
    }


def _add_node_state_metrics(metrics: dict[str, Any], primary_payload: Mapping[str, Any]) -> None:
    if not primary_payload:
        return
    metrics['primary_node_events'] += 1
    has_read = any(key.startswith('node_state_read_') for key in primary_payload)
    if has_read:
        metrics['read_observed_count'] += 1
        read_present = bool(primary_payload.get('node_state_read_present'))
        read_valid = bool(primary_payload.get('node_state_read_valid'))
        if read_present and read_valid:
            metrics['read_hit_count'] += 1
        elif read_present and not read_valid:
            metrics['read_invalid_count'] += 1
        else:
            metrics['read_miss_count'] += 1

    if bool(primary_payload.get('node_state_write_attempted')):
        metrics['write_attempted_count'] += 1
        if not bool(primary_payload.get('node_state_write_succeeded')):
            metrics['write_failed_count'] += 1
        elif bool(primary_payload.get('node_state_write_changed')):
            metrics['write_changed_count'] += 1
        else:
            metrics['write_unchanged_count'] += 1
    elif any(key.startswith('node_state_write_') for key in primary_payload):
        metrics['write_skipped_count'] += 1


def _finalize_node_state_metrics(metrics: dict[str, Any]) -> None:
    read_count = _to_int(metrics.get('read_observed_count'))
    if read_count > 0:
        metrics['read_hit_rate'] = round(float(metrics['read_hit_count']) / float(read_count), 4)
        metrics['invalid_rate'] = round(float(metrics['read_invalid_count']) / float(read_count), 4)


def _empty_web_metrics() -> dict[str, Any]:
    return {
        'requested_turns': 0,
        'not_requested_turns': 0,
        'events_count': 0,
        'successful_count': 0,
        'skipped_count': 0,
        'error_count': 0,
        'injected_turns': 0,
        'injected_chars_total': 0,
        'read_state_counts': {},
    }


def _add_web_metrics(metrics: dict[str, Any], events: Sequence[Mapping[str, Any]]) -> None:
    turn_start_payload = _latest_stage_payload(events, 'turn_start')
    web_events = [event for event in events if _stage(event) == 'web_search']
    requested = bool(turn_start_payload.get('web_search_enabled')) or any(
        bool(_payload(event).get('enabled')) for event in web_events
    )
    if requested:
        metrics['requested_turns'] += 1
    else:
        metrics['not_requested_turns'] += 1
    injected_this_turn = False
    for event in web_events:
        metrics['events_count'] += 1
        status = _status(event)
        if status == 'ok':
            metrics['successful_count'] += 1
        elif status == 'skipped':
            metrics['skipped_count'] += 1
        elif status == 'error':
            metrics['error_count'] += 1
        payload = _payload(event)
        metrics['injected_chars_total'] += _to_int(payload.get('injected_chars'))
        if bool(payload.get('context_injected')) or _to_int(payload.get('injected_chars')) > 0:
            injected_this_turn = True
        read_state = _text(payload.get('read_state'))
        if read_state:
            _inc(metrics['read_state_counts'], read_state)
    if injected_this_turn:
        metrics['injected_turns'] += 1


def _empty_fallback_metrics() -> dict[str, Any]:
    return {
        'total_count': 0,
        'by_reason_code': {},
        'by_stage': {},
    }


def _reason_code(payload: Mapping[str, Any]) -> str:
    return (
        _text(payload.get('reason_code'))
        or _text(payload.get('error_code'))
        or _text(payload.get('error_class'))
        or 'unknown'
    )


def _add_status_and_fallback_metrics(
    *,
    events: Sequence[Mapping[str, Any]],
    fallback_metrics: dict[str, Any],
    errors_by_stage: dict[str, int],
    skipped_by_stage: dict[str, int],
) -> None:
    for event in events:
        stage = _stage(event)
        payload = _payload(event)
        status = _status(event)
        if status == 'error':
            _inc(errors_by_stage, stage)
        if status == 'skipped':
            _inc(skipped_by_stage, stage)
        if bool(payload.get('fail_open')) or bool(payload.get('fallback_used')):
            reason_code = _reason_code(payload)
            fallback_metrics['total_count'] += 1
            _inc(fallback_metrics['by_reason_code'], reason_code)
            _inc(fallback_metrics['by_stage'], stage)


def _checklist_distribution(turns: Mapping[tuple[str, str], Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    classification_counts: dict[str, int] = {}
    status_counts_total: dict[str, int] = {}
    scores: list[int] = []
    for events in turns.values():
        checklist = build_turn_observability_checklist(list(events))
        classification = _text(checklist.get('classification')) or 'unknown'
        _inc(classification_counts, classification)
        scores.append(_to_int(checklist.get('score')))
        status_counts = checklist.get('status_counts')
        if isinstance(status_counts, Mapping):
            for key, value in status_counts.items():
                _inc(status_counts_total, key, _to_int(value))
    score_count = len(scores)
    return {
        'classification_counts': classification_counts,
        'item_status_counts': status_counts_total,
        'score_count': score_count,
        'score_avg': round(sum(scores) / score_count, 3) if score_count else None,
        'score_min': min(scores) if scores else None,
        'score_max': max(scores) if scores else None,
    }


def build_full_turn_metrics_snapshot(
    events: Sequence[Mapping[str, Any]],
    *,
    llm_call_provider_metrics: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build future-dashboard metrics from existing compact chat log events.

    This is a derived read, not a runtime event. It never copies raw event
    payloads; every aggregate is reduced to counters, booleans, rates and
    compact reason/status labels.
    """
    safe_events = _safe_events(events)
    turns = _group_by_turn(safe_events)
    prompt_lanes = _empty_prompt_lane_metrics()
    rag_funnel = _empty_rag_funnel_metrics()
    node_state = _empty_node_state_metrics()
    web = _empty_web_metrics()
    fallback_fail_open = _empty_fallback_metrics()
    errors_by_stage: dict[str, int] = {}
    skipped_by_stage: dict[str, int] = {}

    for turn_events in turns.values():
        prompt_payload = _latest_stage_payload(turn_events, 'prompt_prepared')
        snapshot_payload = _latest_stage_payload(turn_events, 'memory_chain_snapshot')
        primary_payload = _latest_stage_payload(turn_events, 'primary_node')
        _add_prompt_lane_metrics(prompt_lanes, prompt_payload)
        _add_rag_funnel_metrics(
            rag_funnel,
            snapshot_payload=snapshot_payload,
            prompt_payload=prompt_payload,
        )
        _add_node_state_metrics(node_state, primary_payload)
        _add_web_metrics(web, turn_events)

    _add_status_and_fallback_metrics(
        events=safe_events,
        fallback_metrics=fallback_fail_open,
        errors_by_stage=errors_by_stage,
        skipped_by_stage=skipped_by_stage,
    )
    _finalize_node_state_metrics(node_state)

    return {
        'kind': 'full_turn_metrics_snapshot',
        'schema_version': '1',
        'events_count': len(safe_events),
        'turns_observed_count': len(turns),
        'checklist': _checklist_distribution(turns),
        'llm_call_provider_metrics': dict(llm_call_provider_metrics or {}),
        'fallback_fail_open': fallback_fail_open,
        'prompt_lanes': prompt_lanes,
        'rag_funnel': rag_funnel,
        'node_state': node_state,
        'web': web,
        'errors_by_stage': errors_by_stage,
        'skipped_by_stage': skipped_by_stage,
        'redaction': {
            'raw_event_payloads_included': False,
            'derived_from_chat_log_events': True,
        },
    }
