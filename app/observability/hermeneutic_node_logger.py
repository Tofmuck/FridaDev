from __future__ import annotations

import hashlib
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


def _sha256_12(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


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
        'status': str(data.get('status') or ('ok' if data else 'missing')),
        'reason_code': str(data.get('reason_code') or ''),
        'error_code': str(data.get('error_code') or ''),
        'error_class': str(data.get('error_class') or ''),
        'retrieved_count': int(data.get('retrieved_count') or 0),
    }


def _summarize_memory_arbitration(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or 'missing'),
        'reason_code': str(data.get('reason_code') or ''),
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
            'provenances': [str(value) for value in _sequence(regime.get('provenances')) if str(value)],
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
        'activation_mode': str(
            data.get('activation_mode')
            or ('manual' if bool(data.get('enabled', False)) else 'not_requested')
        ),
        'reason_code': str(data.get('reason_code') or ''),
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
    upstream_advisory = _mapping(primary_verdict.get("upstream_advisory"))
    audit = _mapping(primary_verdict.get("audit"))
    degraded_fields = [value for value in (_text(item) for item in _sequence(audit.get("degraded_fields"))) if value]
    fail_open = bool(audit.get("fail_open", False))
    payload = {
        "upstream_recommendation_posture": _text(
            upstream_advisory.get("recommended_judgment_posture") or primary_verdict.get("judgment_posture")
        ),
        "upstream_output_regime_proposed": _text(
            upstream_advisory.get("proposed_output_regime") or primary_verdict.get("discursive_regime")
        ),
        "upstream_active_signal_families": [
            value
            for value in (
                _text(item)
                for item in _sequence(
                    upstream_advisory.get("active_signal_families")
                )
            )
            if value
        ],
        "upstream_constraint_present": bool(
            upstream_advisory.get("constraint_present", bool(_sequence(primary_verdict.get("source_conflicts"))))
        ),
        "epistemic_regime": _text(primary_verdict.get("epistemic_regime")),
        "proof_regime": _text(primary_verdict.get("proof_regime")),
        "source_conflicts_count": len(_sequence(primary_verdict.get("source_conflicts"))),
        "fail_open": bool(audit.get("fail_open", False)),
        "state_used": bool(audit.get("state_used", False)),
        "degraded_fields_count": len(degraded_fields),
    }
    if fail_open or bool(audit.get("fallback_used", False)):
        payload.update(
            {
                "fallback_used": bool(audit.get("fallback_used", fail_open)),
                "fallback_source": _text(audit.get("fallback_source")) or "primary_node",
                "node_stage": _text(audit.get("node_stage")) or "primary_node",
                "reason_code": _text(audit.get("reason_code")) or "unknown_error",
                "error_class": _text(audit.get("error_class")) or "unknown_error",
            }
        )
    return payload


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
    upstream_advisory = _mapping(primary_verdict.get("upstream_advisory"))
    validated_output = _mapping(getattr(validated_result, "validated_output", None))
    validation_context_payload = _mapping(validation_dialogue_context)
    directives = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("pipeline_directives_final")))
        if value
    ]
    followed = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("advisory_recommendations_followed")))
        if value
    ]
    overridden = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("advisory_recommendations_overridden")))
        if value
    ]
    applied_hard_guards = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("applied_hard_guards")))
        if value
    ]
    payload = {
        "dialogue_messages_count": len(_sequence(validation_context_payload.get("messages"))),
        "dialogue_truncated": bool(validation_context_payload.get("truncated", False)),
        "current_user_retained": bool(validation_context_payload.get("current_user_retained", False)),
        "last_assistant_retained": bool(validation_context_payload.get("last_assistant_retained", False)),
        "upstream_recommendation_posture": _text(
            upstream_advisory.get("recommended_judgment_posture") or primary_verdict.get("judgment_posture")
        ),
        "upstream_output_regime_proposed": _text(
            upstream_advisory.get("proposed_output_regime") or primary_verdict.get("discursive_regime")
        ),
        "upstream_active_signal_families": [
            value
            for value in (
                _text(item)
                for item in _sequence(
                    upstream_advisory.get("active_signal_families")
                )
            )
            if value
        ],
        "upstream_constraint_present": bool(
            upstream_advisory.get("constraint_present", bool(_sequence(primary_verdict.get("source_conflicts"))))
        ),
        "validation_decision": _text(validated_output.get("validation_decision")),
        "final_judgment_posture": _text(validated_output.get("final_judgment_posture")),
        "final_output_regime": _text(validated_output.get("final_output_regime")),
        "arbiter_followed_upstream": bool(validated_output.get("arbiter_followed_upstream", False)),
        "advisory_recommendations_followed": followed,
        "advisory_recommendations_overridden": overridden,
        "applied_hard_guards": applied_hard_guards,
        "arbiter_reason": _text(validated_output.get("arbiter_reason")),
        "projected_judgment_posture": _text(validated_output.get("final_judgment_posture")),
        "pipeline_directives_final": directives,
        "decision_source": _text(getattr(validated_result, "decision_source", "")),
    }
    hard_guard_effect = _text(validated_output.get("hard_guard_effect"))
    if hard_guard_effect:
        payload["hard_guard_effect"] = hard_guard_effect
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


def empty_hermeneutic_prompt_injection_payload() -> dict[str, Any]:
    return {
        "present": False,
        "chars": 0,
        "sha256_12": "",
        "final_judgment_posture": "",
        "final_output_regime": "",
        "epistemic_regime": "",
        "directives_count": 0,
        "source": "not_injected",
        "fallback": False,
        "reason_code": "",
    }


def build_hermeneutic_prompt_injection_payload(
    *,
    hermeneutic_judgment_block: Any,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> dict[str, Any]:
    block = str(hermeneutic_judgment_block or "")
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    validated_output = _mapping(getattr(validated_result, "validated_output", None))
    directives = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("pipeline_directives_final")))
        if value
    ]
    status = _text(getattr(validated_result, "status", ""))
    decision_source = _text(getattr(validated_result, "decision_source", ""))
    reason_code = _text(getattr(validated_result, "reason_code", ""))
    fallback = bool(status and status != "ok") or decision_source in {"fallback", "fail_open"} or bool(reason_code)

    payload = empty_hermeneutic_prompt_injection_payload()
    payload.update(
        {
            "present": bool(block.strip()),
            "chars": len(block),
            "sha256_12": _sha256_12(block),
            "final_judgment_posture": _text(validated_output.get("final_judgment_posture")),
            "final_output_regime": _text(validated_output.get("final_output_regime")),
            "epistemic_regime": _text(primary_verdict.get("epistemic_regime")),
            "directives_count": len(directives),
            "source": decision_source or ("validation_agent" if validated_output else "not_injected"),
            "fallback": fallback,
            "reason_code": reason_code,
        }
    )
    return payload


def _provider_message_stats(messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    system_prompt_chars = 0
    current_user_chars = 0
    input_chars_total = 0
    for message in messages:
        message_payload = _mapping(message)
        role = _text(message_payload.get("role")) or "unknown"
        content_chars = len(str(message_payload.get("content") or ""))
        input_chars_total += content_chars
        role_counts[role] = role_counts.get(role, 0) + 1
        if role == "system":
            system_prompt_chars += content_chars
        if role == "user":
            current_user_chars += content_chars
    return {
        "messages_count": len(messages),
        "message_role_counts": role_counts,
        "system_prompt_present": system_prompt_chars > 0,
        "system_prompt_chars": system_prompt_chars,
        "current_user_present": current_user_chars > 0,
        "current_user_chars": current_user_chars,
        "input_chars_total": input_chars_total,
    }


def _recent_window_stats(payload: Mapping[str, Any] | None, *, context_window_turns: int) -> dict[str, Any]:
    data = _mapping(payload)
    turns = list(_sequence(data.get("turns")))
    turn_count_raw = data.get("turn_count")
    try:
        turn_count = int(turn_count_raw)
    except (TypeError, ValueError):
        turn_count = len(turns)
    turns_with_messages_count = 0
    for turn in turns:
        if _sequence(_mapping(turn).get("messages")):
            turns_with_messages_count += 1
    return {
        "recent_window_present": bool(data),
        "recent_turn_count": max(0, turn_count),
        "recent_turns_with_messages_count": turns_with_messages_count,
        "recent_has_in_progress_turn": bool(data.get("has_in_progress_turn", False)),
        "recent_max_turns": int(data.get("max_recent_turns") or context_window_turns or 0),
    }


def build_stimmung_prompt_prepared_payload(
    *,
    decision_source: str,
    messages: Sequence[Mapping[str, Any]],
    recent_window_input_payload: Mapping[str, Any] | None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout_s: int,
    context_window_turns: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v1",
        "payload_kind": "secondary_stimmung_agent_provider",
        "provider_caller": "stimmung_agent",
        "secondary_provider_payload": True,
        "main_llm_payload": False,
        "stimmung_status": "prepared",
        "attempt_decision_source": _text(decision_source) or "unknown",
        "sampling": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
            "timeout_s": int(timeout_s),
        },
        "fail_open": False,
        "reason_code": "",
    }
    payload.update(_provider_message_stats(messages))
    payload.update(
        _recent_window_stats(
            recent_window_input_payload,
            context_window_turns=context_window_turns,
        )
    )
    return payload


def emit_stimmung_prompt_prepared(
    *,
    model: str,
    decision_source: str,
    messages: Sequence[Mapping[str, Any]],
    recent_window_input_payload: Mapping[str, Any] | None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout_s: int,
    context_window_turns: int,
) -> bool:
    return chat_turn_logger.emit(
        "stimmung_prompt_prepared",
        status="ok",
        model=_text(model) or None,
        prompt_kind="stimmung_agent_secondary",
        payload=build_stimmung_prompt_prepared_payload(
            decision_source=decision_source,
            messages=messages,
            recent_window_input_payload=recent_window_input_payload,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            context_window_turns=context_window_turns,
        ),
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
