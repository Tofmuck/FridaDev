from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from core import assistant_output_contract
from core import chat_llm_flow
from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow
from core import conversations_prompt_window
from core import stimmung_agent
from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.validation import validation_agent
from core.hermeneutic_node.inputs import time_input as canonical_time_input
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core.hermeneutic_node.inputs import recent_context_input
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input
from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from core.hermeneutic_node.inputs import summary_input
from core.hermeneutic_node.inputs import user_turn_input as canonical_user_turn_input
from core.hermeneutic_node.inputs import web_input as canonical_web_input
from observability import chat_turn_logger
from observability import hermeneutic_node_logger


# Phase 4 bis - Cartographie locale des responsabilités de ce module:
# 1) Session/conversation + headers HTTP: delegue a core.chat_session_flow
# 2) Contexte/prompt: prompts backend + temporalite + identite + injection web
# 3) Memoire/arbitrage: delegue a core.chat_memory_flow
# 4) Appel LLM: delegue a core.chat_llm_flow


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _json_result(payload: dict[str, Any], status: int, headers: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        'kind': 'json',
        'payload': payload,
        'status': int(status),
        'headers': headers or {},
    }


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: list[dict[str, Any]],
    mode: str,
    *,
    web_input: Mapping[str, Any] | None = None,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> None:
    chat_memory_flow.record_identity_entries_for_mode(
        conversation_id,
        recent_turns,
        mode=mode,
        web_input=web_input,
        arbiter_module=arbiter_module,
        memory_store_module=memory_store_module,
        admin_logs_module=admin_logs_module,
    )


def _resolve_time_input(
    *,
    now_iso: str,
    config_module: Any,
) -> dict[str, Any]:
    return canonical_time_input.build_time_input(
        now_utc_iso=now_iso,
        timezone_name=str(config_module.FRIDA_TIMEZONE),
    )


def _resolve_summary_input(
    *,
    conversation_id: str | None,
    conv_store_module: Any,
) -> dict[str, Any]:
    db_conn_func = getattr(conv_store_module, '_db_conn', None)
    ts_to_iso_func = getattr(conv_store_module, '_ts_to_iso', None)
    conv_logger = getattr(conv_store_module, 'logger', None)
    if not callable(db_conn_func) or not callable(ts_to_iso_func) or conv_logger is None:
        return summary_input.build_summary_input(
            active_summary=None,
            conversation_id=conversation_id,
        )
    try:
        active_summary = conversations_prompt_window.get_active_summary(
            conversation_id,
            normalize_conversation_id_func=lambda value: str(value) if value else None,
            db_conn_func=db_conn_func,
            ts_to_iso_func=ts_to_iso_func,
            logger=conv_logger,
        )
    except Exception:
        active_summary = None
    return summary_input.build_summary_input(
        active_summary=active_summary,
        conversation_id=conversation_id,
    )


def _resolve_identity_input(
    *,
    identity_module: Any,
) -> dict[str, Any]:
    build_identity_payload = getattr(identity_module, 'build_identity_input', None)
    if not callable(build_identity_payload):
        return canonical_identity_input.build_identity_input()
    try:
        return build_identity_payload()
    except Exception:
        return canonical_identity_input.build_identity_input()


def _resolve_recent_context_input(
    *,
    conversation: Mapping[str, Any],
    summary_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return recent_context_input.build_recent_context_input(
        messages=conversation.get('messages', []),
        summary_input_payload=summary_payload,
    )


def _resolve_validation_dialogue_context(
    *,
    conversation: Mapping[str, Any],
    recent_context_payload: Mapping[str, Any] | None,
    user_msg: str,
    now_iso: str,
) -> dict[str, Any]:
    base_messages = _mapping(recent_context_payload).get('messages')
    if isinstance(base_messages, list) and base_messages:
        return recent_context_input.build_validation_dialogue_context(
            messages=base_messages,
            summary_input_payload=None,
        )

    rebuilt_payload = recent_context_input.build_validation_dialogue_context(
        messages=conversation.get('messages', []),
        summary_input_payload=None,
    )
    rebuilt_messages = _mapping(rebuilt_payload).get('messages')
    if isinstance(rebuilt_messages, list) and rebuilt_messages:
        return rebuilt_payload

    return recent_context_input.build_validation_dialogue_context(
        messages=[
            {
                'role': 'user',
                'content': str(user_msg or ''),
                'timestamp': str(now_iso or '').strip() or None,
            }
        ],
        summary_input_payload=None,
    )


def _resolve_recent_window_input(
    *,
    recent_context_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    return canonical_recent_window_input.build_recent_window_input(
        recent_context_input_payload=recent_context_payload,
    )


def _resolve_user_turn_runtime_inputs(
    *,
    user_msg: str,
    recent_window_payload: Mapping[str, Any] | None,
    time_payload: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    bundle = canonical_user_turn_input.build_user_turn_bundle(
        user_message=user_msg,
        recent_window_input_payload=recent_window_payload,
        time_input_payload=time_payload,
    )
    return (
        dict(bundle.get("user_turn") or {}),
        dict(bundle.get("user_turn_signals") or {}),
    )


def _store_latest_user_affective_turn_signal(
    *,
    conversation: Mapping[str, Any],
    signal: Mapping[str, Any] | None,
) -> None:
    messages = conversation.get("messages")
    if not isinstance(messages, list):
        return

    canonical_signal = dict(signal or {})
    if not canonical_signal:
        return

    for message in reversed(messages):
        if not isinstance(message, dict):
            continue
        if str(message.get("role") or "") != "user":
            continue
        meta = dict(message.get("meta") or {})
        meta[canonical_stimmung_input.SIGNAL_META_KEY] = canonical_signal
        message["meta"] = meta
        return


def _resolve_web_runtime_payload(
    *,
    user_msg: str,
    web_search_on: bool,
    web_search_module: Any,
    requests_module: Any,
    llm_module: Any,
) -> dict[str, Any]:
    activation_mode = 'manual' if web_search_on else 'not_requested'

    if activation_mode == 'not_requested':
        chat_turn_logger.emit(
            'web_search',
            status='skipped',
            reason_code='not_applicable',
            payload={
                'enabled': False,
                'activation_mode': 'not_requested',
                'query_preview': '',
                'results_count': 0,
                'context_injected': False,
                'truncated': False,
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code='not_applicable',
            reason_short='web_search_not_requested',
        )
        return {
            'enabled': False,
            'status': 'skipped',
            'activation_mode': 'not_requested',
            'reason_code': 'not_applicable',
            'original_user_message': str(user_msg or ''),
            'query': None,
            'results_count': 0,
            'runtime': {},
            'sources': [],
            'context_block': '',
        }
    build_context_payload = getattr(web_search_module, 'build_context_payload', None)
    if callable(build_context_payload):
        payload = dict(
            build_context_payload(
                user_msg,
                requests_module=requests_module,
                llm_module=llm_module,
            )
        )
        payload['activation_mode'] = activation_mode
        return payload

    ctx, query, n_results = web_search_module.build_context(
        user_msg,
        requests_module=requests_module,
        llm_module=llm_module,
    )
    return {
        'enabled': True,
        'status': 'ok' if ctx else 'skipped',
        'activation_mode': activation_mode,
        'reason_code': None if ctx else 'no_data',
        'original_user_message': str(user_msg or ''),
        'query': str(query or ''),
        'results_count': int(n_results),
        'runtime': {},
        'sources': [],
        'context_block': str(ctx or ''),
    }


def _run_stimmung_agent_stage(
    *,
    user_msg: str,
    recent_window_payload: Mapping[str, Any] | None,
    requests_module: Any,
) -> dict[str, Any]:
    result = stimmung_agent.build_affective_turn_signal(
        user_msg=user_msg,
        recent_window_input_payload=recent_window_payload,
        requests_module=requests_module,
    )
    signal = dict(result.signal or {})
    tones = []
    for item in signal.get('tones', []):
        tone_payload = dict(item or {})
        tone = str(tone_payload.get('tone') or '').strip()
        strength = tone_payload.get('strength')
        if tone and isinstance(strength, int):
            tones.append({'tone': tone, 'strength': strength})

    payload = {
        'present': bool(signal.get('present', False)),
        'dominant_tone': signal.get('dominant_tone'),
        'tones_count': len(tones),
        'tones': tones,
        'confidence': float(signal.get('confidence') or 0.0),
        'decision_source': str(result.decision_source or ''),
    }
    if result.reason_code:
        payload['reason_code'] = str(result.reason_code)

    chat_turn_logger.emit(
        'stimmung_agent',
        status=str(result.status or 'ok'),
        payload=payload,
        model=str(result.model or ''),
    )
    return signal


def _run_hermeneutic_node_insertion_point(
    *,
    conversation: Mapping[str, Any],
    user_msg: str,
    now_iso: str,
    time_input: Mapping[str, Any] | None = None,
    current_mode: str,
    memory_traces: list[dict[str, Any]],
    context_hints: list[dict[str, Any]],
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
    requests_module: Any,
) -> dict[str, Any]:
    """Bounded runtime seam for primary verdict and validated downstream wiring."""
    hermeneutic_node_logger.emit_hermeneutic_node_insertion(
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
    )
    primary_payload = primary_node.build_primary_node(
        conversation_id=conversation.get('id'),
        updated_at=now_iso,
        time_input=time_input,
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
    )
    hermeneutic_node_logger.emit_primary_node(
        primary_payload=primary_payload,
    )
    validation_dialogue_context = _resolve_validation_dialogue_context(
        conversation=conversation,
        recent_context_payload=recent_context_input,
        user_msg=user_msg,
        now_iso=now_iso,
    )
    validated_result = validation_agent.build_validated_output(
        primary_verdict=primary_payload['primary_verdict'],
        justifications={},
        validation_dialogue_context=validation_dialogue_context,
        canonical_inputs={
            'time_input': _mapping(time_input),
            'memory_retrieved': _mapping(memory_retrieved),
            'memory_arbitration': _mapping(memory_arbitration),
            'summary_input': _mapping(summary_input),
            'identity_input': _mapping(identity_input),
            'recent_context_input': _mapping(recent_context_input),
            'recent_window_input': _mapping(recent_window_input),
            'user_turn_input': _mapping(user_turn_input),
            'user_turn_signals': _mapping(user_turn_signals),
            'stimmung_input': _mapping(stimmung_input),
            'web_input': _mapping(web_input),
        },
        requests_module=requests_module,
    )
    hermeneutic_node_logger.emit_validation_agent(
        validation_dialogue_context=validation_dialogue_context,
        primary_payload=primary_payload,
        validated_result=validated_result,
    )
    return {
        'primary_payload': primary_payload,
        'validated_result': validated_result,
    }


def chat_response(
    data: Mapping[str, Any],
    *,
    prompt_loader_module: Any,
    conv_store_module: Any,
    memory_store_module: Any,
    runtime_settings_module: Any,
    summarizer_module: Any,
    identity_module: Any,
    admin_logs_module: Any,
    llm_module: Any,
    requests_module: Any,
    token_utils_module: Any,
    arbiter_module: Any,
    web_search_module: Any,
    config_module: Any,
    logger: Any,
) -> dict[str, Any]:
    system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(prompt_loader_module)
    session, session_error = chat_session_flow.resolve_chat_session(
        data,
        system_prompt=system_prompt,
        conv_store_module=conv_store_module,
        memory_store_module=memory_store_module,
        logger=logger,
    )
    if session_error is not None:
        payload, status = session_error
        return _json_result(payload, status)

    user_msg = str(session['user_msg'])
    conversation = session['conversation']
    stream_req = bool(session['stream_req'])
    web_search_on = bool(session['web_search_on'])
    input_mode = str(session['input_mode'])

    runtime_main_view = runtime_settings_module.get_main_model_settings()
    runtime_main_payload = runtime_main_view.payload
    runtime_main_model = str(runtime_main_payload['model']['value'])
    temperature = float(runtime_main_payload['temperature']['value'])
    top_p = float(runtime_main_payload['top_p']['value'])
    runtime_response_max_tokens = int(runtime_main_payload['response_max_tokens']['value'])
    max_tokens = int(data.get('max_tokens') or runtime_response_max_tokens)

    user_timestamp = _now_iso()
    estimated_user_tokens = token_utils_module.estimate_tokens([{'content': user_msg}], runtime_main_model)
    admin_logs_module.log_event(
        'UserMessage',
        conversation_id=conversation['id'],
        estimated_user_tokens=estimated_user_tokens,
        message_timestamp=user_timestamp,
    )
    user_message_meta = {'input_mode': 'voice'} if input_mode == 'voice' else None
    conv_store_module.append_message(
        conversation,
        'user',
        user_msg,
        meta=user_message_meta,
        timestamp=user_timestamp,
    )

    chat_turn_logger.set_state('summary_generation_observed', False)
    if summarizer_module.maybe_summarize(conversation, runtime_main_model):
        conv_store_module.save_conversation(conversation)
        admin_logs_module.log_event('summary_generated', conversation_id=conversation['id'])
        chat_turn_logger.set_state('summary_generation_observed', True)

    now_iso_value = user_timestamp
    time_payload = _resolve_time_input(
        now_iso=now_iso_value,
        config_module=config_module,
    )
    augmented_system, identity_ids = chat_prompt_context.build_augmented_system(
        system_prompt=system_prompt,
        hermeneutical_prompt=hermeneutical_prompt,
        config_module=config_module,
        identity_module=identity_module,
        now_iso=now_iso_value,
    )
    chat_prompt_context.apply_augmented_system(conversation, augmented_system)

    prepared_memory_context = chat_memory_flow.prepare_memory_context(
        conversation=conversation,
        user_msg=user_msg,
        config_module=config_module,
        memory_store_module=memory_store_module,
        arbiter_module=arbiter_module,
        admin_logs_module=admin_logs_module,
    )
    current_mode, memory_traces, context_hints = prepared_memory_context
    summary_payload = _resolve_summary_input(
        conversation_id=conversation.get('id'),
        conv_store_module=conv_store_module,
    )
    identity_payload = _resolve_identity_input(identity_module=identity_module)
    recent_context_payload = _resolve_recent_context_input(
        conversation=conversation,
        summary_payload=summary_payload,
    )
    recent_window_payload = _resolve_recent_window_input(
        recent_context_payload=recent_context_payload,
    )
    user_turn_payload, user_turn_signals_payload = _resolve_user_turn_runtime_inputs(
        user_msg=user_msg,
        recent_window_payload=recent_window_payload,
        time_payload=time_payload,
    )
    affective_turn_signal = _run_stimmung_agent_stage(
        user_msg=user_msg,
        recent_window_payload=recent_window_payload,
        requests_module=requests_module,
    )
    _store_latest_user_affective_turn_signal(
        conversation=conversation,
        signal=affective_turn_signal,
    )
    stimmung_payload = canonical_stimmung_input.build_stimmung_input(
        messages=conversation.get("messages", []),
    )
    web_runtime_payload = _resolve_web_runtime_payload(
        user_msg=user_msg,
        web_search_on=web_search_on,
        web_search_module=web_search_module,
        requests_module=requests_module,
        llm_module=llm_module,
    )
    web_payload = canonical_web_input.build_web_input_from_runtime_payload(web_runtime_payload)

    hermeneutic_node_runtime = _run_hermeneutic_node_insertion_point(
        conversation=conversation,
        user_msg=user_msg,
        now_iso=now_iso_value,
        time_input=time_payload,
        current_mode=current_mode,
        memory_traces=memory_traces,
        context_hints=context_hints,
        memory_retrieved=getattr(prepared_memory_context, 'memory_retrieved', None),
        memory_arbitration=getattr(prepared_memory_context, 'memory_arbitration', None),
        summary_input=summary_payload,
        identity_input=identity_payload,
        recent_context_input=recent_context_payload,
        recent_window_input=recent_window_payload,
        user_turn_input=user_turn_payload,
        user_turn_signals=user_turn_signals_payload,
        stimmung_input=stimmung_payload,
        web_input=web_payload,
        requests_module=requests_module,
    )
    hermeneutic_judgment_block = chat_prompt_context.build_hermeneutic_judgment_block(
        validated_output=getattr(
            _mapping(hermeneutic_node_runtime).get('validated_result'),
            'validated_output',
            None,
        ),
    )
    augmented_system = chat_prompt_context.inject_hermeneutic_judgment_block(
        augmented_system,
        hermeneutic_judgment_block,
    )
    voice_transcription_guard_block = chat_prompt_context.build_voice_transcription_guard_block(
        input_mode=input_mode,
    )
    augmented_system = chat_prompt_context.inject_voice_transcription_guard_block(
        augmented_system,
        voice_transcription_guard_block,
    )
    direct_identity_revelation_guard_block = chat_prompt_context.build_direct_identity_revelation_guard_block(
        user_msg=user_msg,
        user_turn_input=user_turn_payload,
        user_turn_signals=user_turn_signals_payload,
    )
    augmented_system = chat_prompt_context.inject_direct_identity_revelation_guard_block(
        augmented_system,
        direct_identity_revelation_guard_block,
    )
    web_reading_guard_block = chat_prompt_context.build_web_reading_guard_block(
        web_input=web_payload,
    )
    augmented_system = chat_prompt_context.inject_web_reading_guard_block(
        augmented_system,
        web_reading_guard_block,
    )
    assistant_output_policy = assistant_output_contract.resolve_assistant_output_policy(user_msg)
    plain_text_guard_block = chat_prompt_context.build_plain_text_guard_block(
        user_msg=user_msg,
        output_policy=assistant_output_policy,
    )
    augmented_system = chat_prompt_context.inject_plain_text_guard_block(
        augmented_system,
        plain_text_guard_block,
    )
    chat_prompt_context.apply_augmented_system(conversation, augmented_system)

    prompt_messages = conv_store_module.build_prompt_messages(
        conversation,
        runtime_main_model,
        now=now_iso_value,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )

    if str(web_runtime_payload.get('activation_mode') or '') in {'manual', 'auto'}:
        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg=user_msg,
            conversation_id=conversation['id'],
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
            web_context_payload=web_runtime_payload,
        )
    return chat_llm_flow.run_llm_exchange(
        conversation=conversation,
        prompt_messages=prompt_messages,
        runtime_main_model=runtime_main_model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream_req=stream_req,
        current_mode=current_mode,
        identity_ids=identity_ids,
        runtime_settings_module=runtime_settings_module,
        memory_store_module=memory_store_module,
        conv_store_module=conv_store_module,
        assistant_output_policy=assistant_output_policy,
        llm_module=llm_module,
        requests_module=requests_module,
        token_utils_module=token_utils_module,
        admin_logs_module=admin_logs_module,
        config_module=config_module,
        logger=logger,
        arbiter_module=arbiter_module,
        web_input=web_payload,
        now_iso_func=_now_iso,
        record_identity_entries_for_mode=_record_identity_entries_for_mode,
        mode_enforces_identity=chat_memory_flow.mode_enforces_identity,
        conversation_headers_func=chat_session_flow.conversation_headers,
        conversation_stream_headers_func=chat_session_flow.conversation_stream_headers,
    )
