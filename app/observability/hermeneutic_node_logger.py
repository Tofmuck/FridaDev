from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability import chat_turn_logger


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _bool_str(value: Any) -> bool:
    return bool(str(value or '').strip())


def _summarize_time(now_iso: str) -> dict[str, Any]:
    return {
        'present': _bool_str(now_iso),
    }


def _summarize_memory_retrieved(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'retrieved_count': int(data.get('retrieved_count') or 0),
    }


def _summarize_memory_arbitration(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or 'missing'),
        'decisions_count': int(data.get('decisions_count') or 0),
        'kept_count': int(data.get('kept_count') or 0),
        'rejected_count': int(data.get('rejected_count') or 0),
    }


def _summarize_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or 'missing'),
    }


def _side_summary(side_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    side = _mapping(side_payload)
    static_payload = _mapping(side.get('static'))
    return {
        'static_present': _bool_str(static_payload.get('content')),
        'dynamic_count': len(_sequence(side.get('dynamic'))),
    }


def _summarize_identity(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'frida': _side_summary(data.get('frida')),
        'user': _side_summary(data.get('user')),
    }


def _summarize_recent_context(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'messages_count': len(_sequence(data.get('messages'))),
    }


def _summarize_web(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'enabled': bool(data.get('enabled', False)),
        'status': str(data.get('status') or 'missing'),
        'results_count': int(data.get('results_count') or 0),
    }


def build_hermeneutic_node_insertion_payload(
    *,
    now_iso: str,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'insertion_point_reached': True,
        'mode': str(current_mode or ''),
        'inputs': {
            'time': _summarize_time(now_iso),
            'memory_retrieved': _summarize_memory_retrieved(memory_retrieved),
            'memory_arbitration': _summarize_memory_arbitration(memory_arbitration),
            'summary': _summarize_summary(summary_input),
            'identity': _summarize_identity(identity_input),
            'recent_context': _summarize_recent_context(recent_context_input),
            'web': _summarize_web(web_input),
        },
    }


def emit_hermeneutic_node_insertion(
    *,
    now_iso: str,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> bool:
    return chat_turn_logger.emit(
        'hermeneutic_node_insertion',
        status='ok',
        payload=build_hermeneutic_node_insertion_payload(
            now_iso=now_iso,
            current_mode=current_mode,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            web_input=web_input,
        ),
    )
