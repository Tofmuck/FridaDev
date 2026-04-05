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


def _text(value: Any) -> str:
    return str(value or "").strip()


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
    mutable_payload = _mapping(side.get('mutable'))
    mutable_content = _text(mutable_payload.get('content'))
    return {
        'static_present': _bool_str(static_payload.get('content')),
        'mutable_present': bool(mutable_content),
        'mutable_len': len(mutable_content),
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
    source_material_summary = []
    for item in _sequence(data.get('source_material_summary')):
        source = _mapping(item)
        source_material_summary.append(
            {
                'rank': int(source.get('rank') or 0),
                'url': str(source.get('url') or ''),
                'source_origin': str(source.get('source_origin') or 'search_result'),
                'is_primary_source': bool(source.get('is_primary_source', False)),
                'used_in_prompt': bool(source.get('used_in_prompt', False)),
                'used_content_kind': str(source.get('used_content_kind') or 'none'),
                'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                'content_chars': int(source.get('content_chars') or 0),
                'truncated': bool(source.get('truncated', False)),
            }
        )
    return {
        'present': bool(data),
        'enabled': bool(data.get('enabled', False)),
        'status': str(data.get('status') or 'missing'),
        'results_count': int(data.get('results_count') or 0),
        'explicit_url_detected': bool(data.get('explicit_url_detected', False)),
        'explicit_url': str(data.get('explicit_url') or ''),
        'read_state': str(data.get('read_state') or ''),
        'primary_source_kind': str(data.get('primary_source_kind') or ''),
        'primary_read_attempted': bool(data.get('primary_read_attempted', False)),
        'primary_read_status': str(data.get('primary_read_status') or ''),
        'primary_read_filter': str(data.get('primary_read_filter') or ''),
        'primary_read_raw_fallback_used': bool(data.get('primary_read_raw_fallback_used', False)),
        'fallback_used': bool(data.get('fallback_used', False)),
        'collection_path': str(data.get('collection_path') or ''),
        'used_content_kinds': [str(value) for value in _sequence(data.get('used_content_kinds')) if str(value)],
        'injected_chars': int(data.get('injected_chars') or 0),
        'context_chars': int(data.get('context_chars') or 0),
        'source_material_summary': source_material_summary,
    }


def build_primary_node_payload(
    *,
    primary_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    audit = _mapping(primary_verdict.get("audit"))
    degraded_fields = [value for value in (_text(item) for item in _sequence(audit.get("degraded_fields"))) if value]
    return {
        "judgment_posture": _text(primary_verdict.get("judgment_posture")),
        "epistemic_regime": _text(primary_verdict.get("epistemic_regime")),
        "proof_regime": _text(primary_verdict.get("proof_regime")),
        "source_conflicts_count": len(_sequence(primary_verdict.get("source_conflicts"))),
        "fail_open": bool(audit.get("fail_open", False)),
        "state_used": bool(audit.get("state_used", False)),
        "degraded_fields_count": len(degraded_fields),
    }


def emit_primary_node(
    *,
    primary_payload: Mapping[str, Any] | None,
) -> bool:
    payload = build_primary_node_payload(primary_payload=primary_payload)
    return chat_turn_logger.emit(
        "primary_node",
        status="error" if payload["fail_open"] else "ok",
        payload=payload,
    )


def build_validation_agent_payload(
    *,
    validation_dialogue_context: Mapping[str, Any] | None,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> dict[str, Any]:
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    validated_output = _mapping(getattr(validated_result, "validated_output", None))
    directives = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("pipeline_directives_final")))
        if value
    ]
    payload = {
        "dialogue_messages_count": len(_sequence(_mapping(validation_dialogue_context).get("messages"))),
        "primary_judgment_posture": _text(primary_verdict.get("judgment_posture")),
        "validation_decision": _text(validated_output.get("validation_decision")),
        "final_judgment_posture": _text(validated_output.get("final_judgment_posture")),
        "pipeline_directives_final": directives,
        "decision_source": _text(getattr(validated_result, "decision_source", "")),
    }
    reason_code = _text(getattr(validated_result, "reason_code", ""))
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def emit_validation_agent(
    *,
    validation_dialogue_context: Mapping[str, Any] | None,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> bool:
    status = _text(getattr(validated_result, "status", "")) or "ok"
    if status not in {"ok", "error", "skipped"}:
        status = "ok"
    return chat_turn_logger.emit(
        "validation_agent",
        status=status,
        payload=build_validation_agent_payload(
            validation_dialogue_context=validation_dialogue_context,
            primary_payload=primary_payload,
            validated_result=validated_result,
        ),
        model=_text(getattr(validated_result, "model", "")) or None,
    )


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
