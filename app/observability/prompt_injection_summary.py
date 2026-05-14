from __future__ import annotations

from typing import Any, Mapping, Sequence

from core import conversations_prompt_window


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def empty_memory_prompt_injection_summary() -> dict[str, Any]:
    return {
        'injected': False,
        'injection_class': 'none',
        'injection_lanes': [],
        'injection_lane_count': 0,
        'prompt_block_count': 0,
        'trace_memory_injected': False,
        'trace_memory_injected_count': 0,
        'summary_context_injected': False,
        'summary_context_injected_count': 0,
        'memory_traces_injected': False,
        'memory_traces_injected_count': 0,
        'injected_candidate_ids': [],
        'memory_context_injected': False,
        'memory_context_summary_count': 0,
        'context_hints_injected': False,
        'context_hints_injected_count': 0,
    }


def _unique_parent_summary_count(memory_traces: Sequence[Any]) -> int:
    seen_ids: set[str] = set()
    count = 0
    for trace in memory_traces:
        parent_summary = _mapping(_mapping(trace).get('parent_summary'))
        summary_id = str(parent_summary.get('id') or '').strip()
        if not summary_id or summary_id in seen_ids:
            continue
        seen_ids.add(summary_id)
        count += 1
    return count


def _active_summary_count(prompt_messages: Sequence[Any]) -> int:
    count = 0
    for message in prompt_messages:
        payload = _mapping(message)
        if str(payload.get('role') or '') != 'system':
            continue
        content = str(payload.get('content') or '')
        if conversations_prompt_window.is_active_summary_prompt_message(payload):
            count += 1
            continue
        if content.startswith(conversations_prompt_window.ACTIVE_SUMMARY_BLOCK_HEADER_PREFIXES):
            count += 1
    return count


def _memory_context_summary_count(prompt_messages: Sequence[Any], memory_traces: Sequence[Any]) -> int:
    trace_parent_count = _unique_parent_summary_count(memory_traces)
    if trace_parent_count:
        return trace_parent_count

    count = 0
    for message in prompt_messages:
        payload = _mapping(message)
        if str(payload.get('role') or '') != 'system':
            continue
        content = str(payload.get('content') or '')
        if not content.startswith(conversations_prompt_window.MEMORY_CONTEXT_BLOCK_HEADER_PREFIX):
            continue
        count += max(1, content.count(conversations_prompt_window.MEMORY_CONTEXT_BLOCK_HEADER_PREFIX))
    return count


def _injected_candidate_ids(memory_traces: Sequence[Any]) -> list[str]:
    seen: set[str] = set()
    candidate_ids: list[str] = []
    for trace in memory_traces:
        candidate_id = str(_mapping(trace).get('candidate_id') or '').strip()
        if not candidate_id or candidate_id in seen:
            continue
        seen.add(candidate_id)
        candidate_ids.append(candidate_id)
    return candidate_ids


def _injection_class(lanes: Sequence[str]) -> str:
    lane_list = list(lanes)
    if not lane_list:
        return 'none'
    if len(lane_list) > 1:
        return 'mixed'
    if lane_list[0] == 'context_hints':
        return 'hints_only'
    if lane_list[0] == 'summary_context':
        return 'summary_context_only'
    if lane_list[0] == 'trace_memory':
        return 'trace_memory_only'
    return lane_list[0]


def build_memory_prompt_injection_summary(
    prompt_messages: Sequence[Any],
    *,
    memory_traces: Sequence[Any] | None = None,
    context_hints: Sequence[Any] | None = None,
) -> dict[str, Any]:
    summary = empty_memory_prompt_injection_summary()
    traces_seq = _sequence(memory_traces)
    hints_seq = _sequence(context_hints)
    prompt_seq = _sequence(prompt_messages)
    active_summary_count = _active_summary_count(prompt_seq)

    for message in prompt_seq:
        payload = _mapping(message)
        if str(payload.get('role') or '') != 'system':
            continue
        content = str(payload.get('content') or '')
        if not summary['context_hints_injected'] and content.startswith(conversations_prompt_window.CONTEXT_HINTS_BLOCK_HEADER):
            summary['context_hints_injected'] = True
            summary['context_hints_injected_count'] = int(content.count(conversations_prompt_window.CONTEXT_HINTS_COUNT_MARKER))
            continue
        if not summary['memory_context_injected'] and content.startswith(conversations_prompt_window.MEMORY_CONTEXT_BLOCK_HEADER_PREFIX):
            summary['memory_context_injected'] = True
            summary['memory_context_summary_count'] = _memory_context_summary_count(prompt_seq, traces_seq)
            continue
        if not summary['memory_traces_injected'] and content.startswith(conversations_prompt_window.MEMORY_TRACES_BLOCK_HEADER):
            summary['memory_traces_injected'] = True
            summary['memory_traces_injected_count'] = len(traces_seq)
            summary['injected_candidate_ids'] = _injected_candidate_ids(traces_seq)

    summary['trace_memory_injected'] = bool(summary['memory_traces_injected'])
    summary['trace_memory_injected_count'] = int(summary['memory_traces_injected_count'])
    summary['summary_context_injected_count'] = int(active_summary_count) + int(
        summary['memory_context_summary_count']
    )
    summary['summary_context_injected'] = bool(summary['summary_context_injected_count'])

    lanes = []
    if summary['trace_memory_injected']:
        lanes.append('trace_memory')
    if summary['summary_context_injected']:
        lanes.append('summary_context')
    if summary['context_hints_injected']:
        lanes.append('context_hints')
    summary['injection_lanes'] = lanes
    summary['injection_lane_count'] = len(lanes)
    summary['injection_class'] = _injection_class(lanes)

    summary['prompt_block_count'] = int(
        bool(summary['context_hints_injected'])
        + bool(summary['summary_context_injected'])
        + bool(summary['memory_traces_injected'])
    )
    summary['injected'] = bool(summary['prompt_block_count'])

    if summary['context_hints_injected'] and summary['context_hints_injected_count'] == 0 and not hints_seq:
        summary['context_hints_injected'] = False
        if 'context_hints' in summary['injection_lanes']:
            summary['injection_lanes'] = [
                lane for lane in summary['injection_lanes'] if lane != 'context_hints'
            ]
            summary['injection_lane_count'] = len(summary['injection_lanes'])
            summary['injection_class'] = _injection_class(summary['injection_lanes'])
        summary['prompt_block_count'] = max(0, int(summary['prompt_block_count']) - 1)
        summary['injected'] = bool(summary['prompt_block_count'])

    return summary
