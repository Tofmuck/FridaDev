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
        'prompt_block_count': 0,
        'memory_traces_injected': False,
        'memory_traces_injected_count': 0,
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


def build_memory_prompt_injection_summary(
    prompt_messages: Sequence[Any],
    *,
    memory_traces: Sequence[Any] | None = None,
    context_hints: Sequence[Any] | None = None,
) -> dict[str, Any]:
    summary = empty_memory_prompt_injection_summary()
    traces_seq = _sequence(memory_traces)
    hints_seq = _sequence(context_hints)

    for message in _sequence(prompt_messages):
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
            summary['memory_context_summary_count'] = _unique_parent_summary_count(traces_seq)
            continue
        if not summary['memory_traces_injected'] and content.startswith(conversations_prompt_window.MEMORY_TRACES_BLOCK_HEADER):
            summary['memory_traces_injected'] = True
            summary['memory_traces_injected_count'] = len(traces_seq)

    summary['prompt_block_count'] = int(
        bool(summary['context_hints_injected'])
        + bool(summary['memory_context_injected'])
        + bool(summary['memory_traces_injected'])
    )
    summary['injected'] = bool(summary['prompt_block_count'])

    if summary['context_hints_injected'] and summary['context_hints_injected_count'] == 0 and not hints_seq:
        summary['context_hints_injected'] = False
        summary['prompt_block_count'] = max(0, int(summary['prompt_block_count']) - 1)
        summary['injected'] = bool(summary['prompt_block_count'])

    return summary
