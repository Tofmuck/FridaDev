from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from core import assistant_output_contract
from core import active_conversation_documents
from core import active_document_prompt_lane
from core import chat_llm_flow
from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow
from core import chat_turn_runtime_inputs
from core import conversations_prompt_window
from core import stimmung_agent
from core.hermeneutic_node.runtime import node_state as runtime_node_state
from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.validation import validation_agent
from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from core.hermeneutic_node.inputs import web_input as canonical_web_input
from observability import chat_turn_logger
from observability import hermeneutic_node_logger


# Phase 4 bis - Cartographie locale des responsabilités de ce module:
# 1) Session/conversation + headers HTTP: delegue a core.chat_session_flow
# 2) Contexte/prompt: prompts backend + temporalite + identite + injection web
# 3) Memoire/arbitrage: delegue a core.chat_memory_flow
# 4) Appel LLM: delegue a core.chat_llm_flow
# 5) Inputs runtime/signaux amont du tour: delegue a core.chat_turn_runtime_inputs


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


def _text(value: Any) -> str:
    return str(value or '').strip()


def _active_documents_for_prompt(
    *,
    conversation: Mapping[str, Any],
    active_documents_module: Any = active_conversation_documents,
    logger: Any = None,
) -> list[dict[str, Any]]:
    conversation_id = _text(conversation.get('id'))
    if not conversation_id:
        return []
    reader = getattr(active_documents_module, 'list_active_documents_for_prompt', None)
    if not callable(reader):
        return []
    try:
        raw_documents = reader(conversation_id)
    except Exception as exc:
        if logger is not None:
            logger.warning('active_documents_prompt_read_failed id=%s err=%s', conversation_id, exc)
        return []
    documents: list[dict[str, Any]] = []
    for item in raw_documents or []:
        if isinstance(item, Mapping):
            documents.append(dict(item))
    return documents


def _prompt_token_counter(token_utils_module: Any):
    counter = getattr(token_utils_module, 'estimate_tokens', None)
    if callable(counter):
        return counter
    return lambda _messages, _model: 0


def _active_document_prompt_max_tokens(config_module: Any) -> int:
    value = getattr(
        config_module,
        'ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS',
        getattr(config_module, 'MAX_TOKENS', 0),
    )
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


_FINAL_ANSWER_OUTPUT_REGIME = {
    'discursive_regime': 'simple',
    'resituation_level': 'none',
    'time_reference_mode': 'atemporal',
}
_FINAL_NON_ANSWER_OUTPUT_REGIME = {
    'discursive_regime': 'meta',
    'resituation_level': 'none',
    'time_reference_mode': 'atemporal',
}


def _read_hermeneutic_node_state(
    *,
    memory_store_module: Any,
    conversation_id: str,
) -> dict[str, Any]:
    reader = getattr(memory_store_module, 'read_hermeneutic_node_state', None)
    if not callable(reader):
        return {
            'state': None,
            'present': False,
            'valid': False,
            'reason_code': 'reader_unavailable',
            'schema_version': '',
            'state_sha256_12': '',
        }
    try:
        result = reader(conversation_id)
    except Exception as exc:
        return {
            'state': None,
            'present': False,
            'valid': False,
            'reason_code': 'read_error',
            'schema_version': '',
            'state_sha256_12': '',
            'error_class': exc.__class__.__name__,
        }
    return _mapping(result)


def _existing_node_state_from_read(read_result: Mapping[str, Any] | None) -> dict[str, Any] | None:
    payload = _mapping(read_result)
    if not bool(payload.get('valid', False)):
        return None
    state = _mapping(payload.get('state'))
    return state or None


def _skipped_hermeneutic_node_state_write(reason_code: str) -> dict[str, Any]:
    return {
        'attempted': False,
        'written': False,
        'changed': False,
        'reason_code': _text(reason_code) or 'not_applicable',
        'schema_version': '',
        'state_sha256_12': '',
    }


def _write_hermeneutic_node_state(
    *,
    memory_store_module: Any,
    conversation_id: str,
    node_state_payload: Mapping[str, Any] | None,
) -> dict[str, Any]:
    writer = getattr(memory_store_module, 'write_hermeneutic_node_state', None)
    if not callable(writer):
        return {
            'attempted': False,
            'written': False,
            'changed': False,
            'reason_code': 'writer_unavailable',
            'schema_version': '',
            'state_sha256_12': '',
        }
    try:
        result = writer(conversation_id, node_state_payload)
    except Exception as exc:
        return {
            'attempted': True,
            'written': False,
            'changed': False,
            'reason_code': 'write_error',
            'schema_version': '',
            'state_sha256_12': '',
            'error_class': exc.__class__.__name__,
        }
    return _mapping(result)


def _build_final_hermeneutic_node_state(
    *,
    conversation_id: str,
    now_iso: str,
    validated_result: Any,
    existing_node_state: Mapping[str, Any] | None,
) -> tuple[dict[str, Any] | None, str]:
    validated_output = _mapping(getattr(validated_result, 'validated_output', None))
    if not validated_output:
        return None, 'validated_output_missing'

    final_judgment_posture = _text(validated_output.get('final_judgment_posture'))
    final_output_regime = _text(validated_output.get('final_output_regime'))
    if final_judgment_posture == 'answer':
        if final_output_regime != 'simple':
            return None, 'unsupported_final_output_regime'
        output_regime = _FINAL_ANSWER_OUTPUT_REGIME
    elif final_judgment_posture in {'clarify', 'suspend'}:
        output_regime = _FINAL_NON_ANSWER_OUTPUT_REGIME
    else:
        return None, 'invalid_final_judgment_posture'

    try:
        state = runtime_node_state.build_node_state(
            conversation_id=conversation_id,
            updated_at=now_iso,
            judgment_posture=final_judgment_posture,
            output_regime=output_regime,
            existing_node_state=existing_node_state,
        )
    except Exception:
        return None, 'invalid_validated_node_state'
    return state, ''


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


_resolve_time_input = chat_turn_runtime_inputs.resolve_time_input
_resolve_summary_input = chat_turn_runtime_inputs.resolve_summary_input
_resolve_identity_input = chat_turn_runtime_inputs.resolve_identity_input
_resolve_recent_context_input = chat_turn_runtime_inputs.resolve_recent_context_input
_resolve_validation_dialogue_context = chat_turn_runtime_inputs.resolve_validation_dialogue_context
_resolve_recent_window_input = chat_turn_runtime_inputs.resolve_recent_window_input
_resolve_user_turn_runtime_inputs = chat_turn_runtime_inputs.resolve_user_turn_runtime_inputs
_store_latest_user_affective_turn_signal = chat_turn_runtime_inputs.store_latest_user_affective_turn_signal
_resolve_web_runtime_payload = chat_turn_runtime_inputs.resolve_web_runtime_payload
_run_stimmung_agent_stage = chat_turn_runtime_inputs.run_stimmung_agent_stage
_build_stimmung_input = chat_turn_runtime_inputs.build_stimmung_input
_build_web_input_from_runtime_payload = chat_turn_runtime_inputs.build_web_input_from_runtime_payload


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
    memory_store_module: Any = None,
    requests_module: Any = None,
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
    conversation_id = str(conversation.get('id') or '')
    node_state_read = _read_hermeneutic_node_state(
        memory_store_module=memory_store_module,
        conversation_id=conversation_id,
    )
    existing_node_state = _existing_node_state_from_read(node_state_read)
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
        existing_node_state=existing_node_state,
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
    final_node_state, skip_write_reason = _build_final_hermeneutic_node_state(
        conversation_id=conversation_id,
        now_iso=now_iso,
        validated_result=validated_result,
        existing_node_state=existing_node_state,
    )
    if final_node_state is None:
        node_state_write = _skipped_hermeneutic_node_state_write(skip_write_reason)
    else:
        node_state_write = _write_hermeneutic_node_state(
            memory_store_module=memory_store_module,
            conversation_id=conversation_id,
            node_state_payload=final_node_state,
        )
    node_state_persistence = hermeneutic_node_logger.build_node_state_persistence_payload(
        read_result=node_state_read,
        write_result=node_state_write,
    )
    hermeneutic_node_logger.emit_primary_node(
        primary_payload=primary_payload,
        node_state_persistence=node_state_persistence,
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
        mark_persist_phase = getattr(conv_store_module, 'mark_next_persist_phase', None)
        if callable(mark_persist_phase):
            mark_persist_phase('summary')
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
    stimmung_payload = _build_stimmung_input(conversation=conversation)
    web_runtime_payload = _resolve_web_runtime_payload(
        user_msg=user_msg,
        web_search_on=web_search_on,
        web_search_module=web_search_module,
        requests_module=requests_module,
        llm_module=llm_module,
    )
    web_payload = _build_web_input_from_runtime_payload(web_runtime_payload)

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
        memory_store_module=memory_store_module,
        requests_module=requests_module,
    )
    hermeneutic_node_runtime_payload = _mapping(hermeneutic_node_runtime)
    validated_result = hermeneutic_node_runtime_payload.get('validated_result')
    primary_payload = _mapping(hermeneutic_node_runtime_payload.get('primary_payload'))
    hermeneutic_judgment_block = chat_prompt_context.build_hermeneutic_judgment_block(
        validated_output=getattr(validated_result, 'validated_output', None),
    )
    chat_turn_logger.set_state(
        'hermeneutic_prompt_injection',
        hermeneutic_node_logger.build_hermeneutic_prompt_injection_payload(
            hermeneutic_judgment_block=hermeneutic_judgment_block,
            primary_payload=primary_payload,
            validated_result=validated_result,
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

    active_documents_for_prompt = _active_documents_for_prompt(
        conversation=conversation,
        logger=logger,
    )
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
    active_document_prompt_lane.inject_active_document_prompt_lane(
        prompt_messages,
        active_documents_for_prompt,
        model=runtime_main_model,
        count_tokens_func=_prompt_token_counter(token_utils_module),
        max_tokens=_active_document_prompt_max_tokens(config_module),
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
