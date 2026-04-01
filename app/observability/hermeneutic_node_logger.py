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


def _summarize_time(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'timezone': str(data.get('timezone') or ''),
        'day_part_class': str(data.get('day_part_class') or ''),
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


def _summarize_recent_window(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'turn_count': int(data.get('turn_count') or 0),
        'has_in_progress_turn': bool(data.get('has_in_progress_turn', False)),
        'max_recent_turns': int(data.get('max_recent_turns') or 0),
    }


def _summarize_user_turn(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    regime = _mapping(data.get('regime_probatoire'))
    temporal = _mapping(data.get('qualification_temporelle'))
    return {
        'present': bool(data),
        'geste_dialogique_dominant': str(data.get('geste_dialogique_dominant') or ''),
        'regime_probatoire': {
            'principe': str(regime.get('principe') or ''),
            'types_de_preuve_attendus': [str(value) for value in _sequence(regime.get('types_de_preuve_attendus')) if str(value)],
            'regime_de_vigilance': str(regime.get('regime_de_vigilance') or ''),
        },
        'qualification_temporelle': {
            'portee_temporelle': str(temporal.get('portee_temporelle') or ''),
            'ancrage_temporel': str(temporal.get('ancrage_temporel') or ''),
        },
    }


def _summarize_user_turn_signals(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    active_families = [str(value) for value in _sequence(data.get('active_signal_families')) if str(value)]
    return {
        'present': bool(data.get('present', bool(data))),
        'ambiguity_present': bool(data.get('ambiguity_present', False)),
        'underdetermination_present': bool(data.get('underdetermination_present', False)),
        'active_signal_families': active_families,
        'active_signal_families_count': int(data.get('active_signal_families_count') or len(active_families)),
    }


def _summarize_stimmung(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    active_tones = []
    for item in _sequence(data.get("active_tones")):
        tone_payload = _mapping(item)
        tone = str(tone_payload.get("tone") or "").strip()
        strength = tone_payload.get("strength")
        if tone and isinstance(strength, int):
            active_tones.append({"tone": tone, "strength": strength})
    return {
        "present": bool(data.get("present", bool(data))),
        "dominant_tone": data.get("dominant_tone"),
        "active_tones": active_tones,
        "stability": str(data.get("stability") or ""),
        "shift_state": str(data.get("shift_state") or ""),
        "turns_considered": int(data.get("turns_considered") or 0),
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
    time_input: Mapping[str, Any] | None = None,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'insertion_point_reached': True,
        'mode': str(current_mode or ''),
        'inputs': {
            'time': _summarize_time(time_input),
            'memory_retrieved': _summarize_memory_retrieved(memory_retrieved),
            'memory_arbitration': _summarize_memory_arbitration(memory_arbitration),
            'summary': _summarize_summary(summary_input),
            'identity': _summarize_identity(identity_input),
            'recent_context': _summarize_recent_context(recent_context_input),
            'recent_window': _summarize_recent_window(recent_window_input),
            'user_turn': _summarize_user_turn(user_turn_input),
            'user_turn_signals': _summarize_user_turn_signals(user_turn_signals),
            'stimmung': _summarize_stimmung(stimmung_input),
            'web': _summarize_web(web_input),
        },
    }


def emit_hermeneutic_node_insertion(
    *,
    time_input: Mapping[str, Any] | None = None,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> bool:
    return chat_turn_logger.emit(
        'hermeneutic_node_insertion',
        status='ok',
        payload=build_hermeneutic_node_insertion_payload(
            time_input=time_input,
            current_mode=current_mode,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            recent_window_input=recent_window_input,
            user_turn_input=user_turn_input,
            user_turn_signals=user_turn_signals,
            stimmung_input=stimmung_input,
            web_input=web_input,
        ),
    )
