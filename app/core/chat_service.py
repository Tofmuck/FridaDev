from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from core import assistant_output_contract
from core import adobe_docs_prompt_lane
from core import active_conversation_documents
from core import active_document_prompt_lane
from core import workspace_folder_notes
from core import workspace_folder_notes_prompt_lane
from core import workspace_folder_notes_read
from core import workspace_folders
from core import workspace_file_selections
from core import chat_llm_flow
from core.chat_document_prompt_reads import (
    ActiveDocumentsPromptRead,
    _active_documents_for_prompt,
    _merge_document_prompt_reads,
    _workspace_files_for_prompt,
)
from core.chat_hermeneutic_node_state import (
    _build_final_hermeneutic_node_state,
    _existing_node_state_from_read,
    _read_hermeneutic_node_state,
    _skipped_hermeneutic_node_state_write,
    _write_hermeneutic_node_state,
)
from core.chat_main_payload import PreparedMainPayload, prepare_main_payload
from core.chat_agent_lane_orchestration import (
    AgentLaneAssistantOutput,
    _agenda_assistant_response_override,
    _biblio_assistant_response_envelope,
    _biblio_assistant_response_meta,
    _biblio_assistant_response_override,
    _emit_adobe_docs_observability,
    _emit_adobe_prompt_lane_observability,
    _emit_agenda_observability,
    _emit_biblio_observability,
    _emit_workspace_folder_notes_prompt_observability,
    _hermeneutic_presence_assistant_response_override,
    resolve_agent_lane_assistant_output,
)
from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow
from core import chat_turn_runtime_inputs
from core import continuity_capsule
from core import conversations_prompt_window
from core import prompt_loader
from core import stimmung_agent
from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.validation import validation_agent
from core.hermeneutic_node.inputs import stimmung_input as canonical_stimmung_input
from core.hermeneutic_node.inputs import web_input as canonical_web_input
from agenda import chat_runtime as agenda_chat_runtime
from biblio import chat_runtime as biblio_chat_runtime
from observability import active_documents_observability
from observability import chat_turn_logger
from observability import hermeneutic_node_logger
from observability import main_payload_manifest
from tools import adobe_docs_pipeline


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


def _prompt_token_counter(token_utils_module: Any):
    counter = getattr(token_utils_module, 'estimate_tokens', None)
    if callable(counter):
        return counter
    return lambda _messages, _model: 0


def _active_document_prompt_max_tokens(config_module: Any) -> int:
    value = getattr(config_module, 'ACTIVE_DOCUMENT_PROMPT_MAX_TOKENS', 0)
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _record_active_document_prompt_decisions(
    *,
    conversation: Mapping[str, Any],
    lane: Any,
    turn_id: str,
    active_documents_module: Any = active_conversation_documents,
    workspace_file_selections_module: Any = workspace_file_selections,
    logger: Any = None,
) -> None:
    conversation_id = _text(conversation.get('id'))
    if not conversation_id:
        return
    decisions = getattr(lane, 'decisions', ()) or ()
    if not decisions:
        return

    injected_writer = getattr(active_documents_module, 'record_document_injected', None)
    excluded_writer = getattr(active_documents_module, 'record_document_excluded', None)
    workspace_injected_writer = getattr(workspace_file_selections_module, 'record_selection_injected', None)
    workspace_excluded_writer = getattr(workspace_file_selections_module, 'record_selection_excluded', None)
    for decision in decisions:
        document_id = _text(getattr(decision, 'document_id', ''))
        if not document_id:
            continue
        try:
            if _text(getattr(decision, 'source', '')) == 'workspace_file_selection':
                file_id = _text(getattr(decision, 'workspace_file_id', '')) or document_id
                if bool(getattr(decision, 'injected', False)):
                    if callable(workspace_injected_writer):
                        workspace_injected_writer(conversation_id, file_id, turn_id=turn_id)
                    continue
                if callable(workspace_excluded_writer):
                    workspace_excluded_writer(
                        conversation_id,
                        file_id,
                        turn_id=turn_id,
                        reason_code=_text(getattr(decision, 'reason_code', '')) or 'workspace_file_unreadable',
                    )
                continue
            if bool(getattr(decision, 'injected', False)):
                if callable(injected_writer):
                    injected_writer(conversation_id, document_id, turn_id=turn_id)
                continue
            if callable(excluded_writer):
                excluded_writer(
                    conversation_id,
                    document_id,
                    turn_id=turn_id,
                    reason_code=_text(getattr(decision, 'reason_code', '')) or 'document_runtime_unavailable',
                )
        except Exception as exc:
            if logger is not None:
                logger.warning('active_document_prompt_decision_record_failed doc=%s err=%s', document_id, exc)


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
_resolve_web_runtime_payload_skipped_by_adobe = chat_turn_runtime_inputs.resolve_web_runtime_payload_skipped_by_adobe
_run_stimmung_agent_stage = chat_turn_runtime_inputs.run_stimmung_agent_stage
_build_stimmung_input = chat_turn_runtime_inputs.build_stimmung_input
_build_web_input_from_runtime_payload = chat_turn_runtime_inputs.build_web_input_from_runtime_payload


_BIBLIO_RECENT_DIALOGUE_META_SOURCES = {
    'biblio_rendered_answer',
    'biblio_read_passages_response',
}

_BIBLIO_RECENT_DIALOGUE_META_KEYS = (
    'source',
    'reason_code',
    'biblio_exact_text_rendered',
    'biblio_exact_text_chars',
    'biblio_exact_text_hash',
    'biblio_render_mode',
    'biblio_answer_status',
    'biblio_query_kind',
    'biblio_final_lock_authorized',
    'biblio_final_lock_reason_code',
    'biblio_read_passages_mode',
    'biblio_read_passages_reason_code',
    'biblio_read_passages_count',
    'biblio_read_passages_chars',
    'biblio_read_passages_hashes',
    'biblio_surface_intro_present',
    'biblio_surface_intro_chars',
    'biblio_surface_intro_hash',
    'biblio_surface_outro_present',
    'biblio_surface_outro_chars',
    'biblio_surface_outro_hash',
    'biblio_surface_empty_reason_codes',
)


def _biblio_recent_dialogue_meta(meta: Mapping[str, Any]) -> dict[str, Any] | None:
    source = str(meta.get('source') or '')
    if source not in _BIBLIO_RECENT_DIALOGUE_META_SOURCES:
        return None
    copied = {
        key: meta.get(key)
        for key in _BIBLIO_RECENT_DIALOGUE_META_KEYS
        if key in meta
    }
    return copied or None


def _biblio_recent_dialogue(conversation: Mapping[str, Any], user_msg: str) -> tuple[dict[str, Any], ...]:
    messages = conversation.get('messages')
    if not isinstance(messages, list):
        return ()
    selected: list[dict[str, Any]] = []
    for raw_message in messages[-12:]:
        if not isinstance(raw_message, Mapping):
            continue
        role = str(raw_message.get('role') or '').strip()
        if role not in {'user', 'assistant'}:
            continue
        content = str(raw_message.get('content') or '')
        if role == 'user' and content == user_msg and raw_message is messages[-1]:
            continue
        turn: dict[str, Any] = {'role': role, 'content': content}
        meta = raw_message.get('meta')
        if isinstance(meta, Mapping):
            biblio_meta = _biblio_recent_dialogue_meta(meta)
            if biblio_meta is not None:
                turn['meta'] = biblio_meta
        selected.append(turn)
    return tuple(selected[-8:])


def _agenda_recent_dialogue(conversation: Mapping[str, Any], user_msg: str) -> tuple[dict[str, Any], ...]:
    messages = conversation.get('messages')
    if not isinstance(messages, list):
        return ()
    selected: list[dict[str, Any]] = []
    for raw_message in messages[-12:]:
        if not isinstance(raw_message, Mapping):
            continue
        role = str(raw_message.get('role') or '').strip()
        if role not in {'user', 'assistant'}:
            continue
        content = str(raw_message.get('content') or '')
        if role == 'user' and content == user_msg and raw_message is messages[-1]:
            continue
        selected.append({'role': role, 'content': content})
    return tuple(selected[-8:])


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
    workspace_file_selections_module: Any = workspace_file_selections,
    workspace_folders_module: Any = workspace_folders,
    workspace_folder_notes_module: Any = workspace_folder_notes,
    workspace_folder_notes_read_module: Any = workspace_folder_notes_read,
) -> dict[str, Any]:
    adobe_request = adobe_docs_pipeline.resolve_adobe_request(data)
    if adobe_request.error_code:
        chat_turn_logger.emit(
            'adobe_docs',
            status='error',
            reason_code=adobe_request.error_code,
            payload=adobe_request.as_content_free_dict(),
        )
        return _json_result({'ok': False, 'error': adobe_request.error_code}, 400)

    system_prompt, hermeneutical_prompt = chat_prompt_context.resolve_backend_prompts(prompt_loader_module)
    try:
        system_prompt = prompt_loader.require_usable_prompt_text(
            system_prompt,
            prompt_id='main_system',
        )
        hermeneutical_prompt = prompt_loader.require_usable_prompt_text(
            hermeneutical_prompt,
            prompt_id='main_hermeneutical',
        )
    except prompt_loader.RequiredPromptUnavailable as exc:
        return _json_result(
            {
                'ok': False,
                'error': 'service temporairement indisponible',
                'reason_code': 'critical_prompt_unavailable',
                'prompt_id': exc.prompt_id,
            },
            503,
        )
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
        now_iso=now_iso_value,
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
    if adobe_request.active:
        web_runtime_payload = _resolve_web_runtime_payload_skipped_by_adobe(
            user_msg=user_msg,
            web_search_requested=web_search_on,
        )
    else:
        web_runtime_payload = _resolve_web_runtime_payload(
            user_msg=user_msg,
            web_search_on=web_search_on,
            web_search_module=web_search_module,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso_value,
        )
    web_payload = _build_web_input_from_runtime_payload(web_runtime_payload)

    adobe_context = adobe_docs_pipeline.not_requested_context()
    if adobe_request.active:
        try:
            adobe_context = adobe_docs_pipeline.build_adobe_context(
                user_msg,
                adobe_request.product,
                requests_module=requests_module,
            )
        except Exception as exc:
            adobe_context = adobe_docs_pipeline.error_context(
                product=adobe_request.product,
                reason_code=adobe_docs_pipeline.REASON_ADOBE_PIPELINE_EXCEPTION,
                error_class=exc.__class__.__name__,
            )
        _emit_adobe_docs_observability(
            conversation_id=conversation['id'],
            adobe_context=adobe_context,
            admin_logs_module=admin_logs_module,
        )

    biblio_state = biblio_chat_runtime.read_biblio_conversation_state(conversation)
    biblio_recent_dialogue = _biblio_recent_dialogue(conversation, user_msg)
    biblio_result = biblio_chat_runtime.run_biblio_chat_turn(
        data,
        user_msg=user_msg,
        conversation_id=conversation.get('id'),
        conversation_state=biblio_state,
        recent_dialogue=biblio_recent_dialogue,
        now_iso=now_iso_value,
        config_module=config_module,
    )
    biblio_chat_runtime.attach_biblio_conversation_state(conversation, biblio_result)
    _emit_biblio_observability(biblio_result)

    agenda_result = None
    agenda_enabled = agenda_chat_runtime.normalize_agenda_enabled(data.get('agenda_enabled'))
    agenda_recent_dialogue = ()
    if agenda_enabled:
        agenda_state = agenda_chat_runtime.read_agenda_conversation_state(conversation)
        agenda_recent_dialogue = _agenda_recent_dialogue(conversation, user_msg)
        agenda_result = agenda_chat_runtime.run_agenda_chat_turn(
            data,
            user_msg=user_msg,
            conversation_id=conversation.get('id'),
            conversation_state=agenda_state,
            recent_dialogue=agenda_recent_dialogue,
            now_iso=now_iso_value,
            config_module=config_module,
            runtime_settings_module=runtime_settings_module,
            llm_module=llm_module,
            requests_module=requests_module,
        )
        agenda_chat_runtime.attach_agenda_conversation_state(conversation, agenda_result)
        _emit_agenda_observability(agenda_result)
    else:
        disabled_result_builder = getattr(agenda_chat_runtime, 'build_disabled_observability_result', None)
        if callable(disabled_result_builder):
            agenda_result = disabled_result_builder()
            _emit_agenda_observability(agenda_result)

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
    web_evidence_guard_block = chat_prompt_context.build_web_evidence_guard_block(
        web_input=web_payload,
    )
    augmented_system = chat_prompt_context.inject_web_evidence_guard_block(
        augmented_system,
        web_evidence_guard_block,
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

    active_documents_read = _active_documents_for_prompt(
        conversation=conversation,
        logger=logger,
    )
    workspace_files_read = _workspace_files_for_prompt(
        conversation=conversation,
        workspace_file_selections_module=workspace_file_selections_module,
        logger=logger,
    )
    document_prompt_read = _merge_document_prompt_reads(
        active_documents_read,
        workspace_files_read,
    )
    workspace_notes_read = workspace_folder_notes_prompt_lane.read_workspace_folder_notes_for_prompt(
        data=data,
        conversation=conversation,
        workspace_folders_module=workspace_folders_module,
        workspace_folder_notes_module=workspace_folder_notes_module,
        workspace_folder_notes_read_module=workspace_folder_notes_read_module,
        logger=logger,
    )
    prepared_main_payload = prepare_main_payload(
        conversation=conversation,
        user_msg=user_msg,
        runtime_main_model=runtime_main_model,
        now_iso_value=now_iso_value,
        memory_traces=memory_traces,
        context_hints=context_hints,
        web_runtime_payload=web_runtime_payload,
        web_search_module=web_search_module,
        admin_logs_module=admin_logs_module,
        document_prompt_read=document_prompt_read,
        workspace_notes_read=workspace_notes_read,
        biblio_result=biblio_result,
        agenda_result=agenda_result,
        adobe_request=adobe_request,
        adobe_context=adobe_context,
        validated_result=validated_result,
        assistant_output_policy=assistant_output_policy,
        hermeneutic_node_runtime=hermeneutic_node_runtime,
        hermeneutic_judgment_block=hermeneutic_judgment_block,
        biblio_recent_dialogue=biblio_recent_dialogue,
        agenda_recent_dialogue=agenda_recent_dialogue,
        summary_payload=summary_payload,
        identity_payload=identity_payload,
        recent_context_payload=recent_context_payload,
        recent_window_payload=recent_window_payload,
        current_mode=current_mode,
        memory_retrieved=getattr(prepared_memory_context, 'memory_retrieved', None),
        memory_arbitration=getattr(prepared_memory_context, 'memory_arbitration', None),
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream_req=stream_req,
        config_module=config_module,
        count_tokens_func=_prompt_token_counter(token_utils_module),
        active_document_prompt_max_tokens=_active_document_prompt_max_tokens(config_module),
        record_active_document_prompt_decisions_func=_record_active_document_prompt_decisions,
        workspace_file_selections_module=workspace_file_selections_module,
        logger=logger,
        conv_store_module=conv_store_module,
    )
    prompt_messages = prepared_main_payload.prompt_messages
    assistant_response_override = prepared_main_payload.assistant_response_override
    biblio_assistant_response_meta = prepared_main_payload.assistant_response_meta
    biblio_assistant_response_envelope = prepared_main_payload.assistant_response_envelope
    web_context_injected_to_main_model = (
        prepared_main_payload.web_context_injected_to_main_model
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
        assistant_response_override=assistant_response_override,
        assistant_response_meta=biblio_assistant_response_meta,
        web_context_injected_to_main_model=web_context_injected_to_main_model,
        assistant_response_intro=biblio_assistant_response_envelope.get('surface_intro', ''),
        assistant_response_outro=biblio_assistant_response_envelope.get('surface_outro', ''),
    )
