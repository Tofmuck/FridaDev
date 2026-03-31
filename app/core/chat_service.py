from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

from core import chat_llm_flow
from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow
from core import conversations_prompt_window
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core.hermeneutic_node.inputs import summary_input


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


def _record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: list[dict[str, Any]],
    mode: str,
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> None:
    chat_memory_flow.record_identity_entries_for_mode(
        conversation_id,
        recent_turns,
        mode=mode,
        arbiter_module=arbiter_module,
        memory_store_module=memory_store_module,
        admin_logs_module=admin_logs_module,
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


def _run_hermeneutic_node_insertion_point(
    *,
    conversation: Mapping[str, Any],
    user_msg: str,
    now_iso: str,
    current_mode: str,
    memory_traces: list[dict[str, Any]],
    context_hints: list[dict[str, Any]],
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
) -> None:
    """Fixed runtime seam reserved for the future hermeneutic node."""
    return None


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

    runtime_main_view = runtime_settings_module.get_main_model_settings()
    runtime_main_payload = runtime_main_view.payload
    runtime_main_model = str(runtime_main_payload['model']['value'])
    temperature = float(runtime_main_payload['temperature']['value'])
    top_p = float(runtime_main_payload['top_p']['value'])
    runtime_response_max_tokens = int(runtime_main_payload['response_max_tokens']['value'])
    max_tokens = int(data.get('max_tokens') or runtime_response_max_tokens)

    user_timestamp = _now_iso()
    user_tokens = token_utils_module.count_tokens([{'content': user_msg}], runtime_main_model)
    admin_logs_module.log_event(
        'UserMessage',
        conversation_id=conversation['id'],
        user_tokens=user_tokens,
        message_timestamp=user_timestamp,
    )
    conv_store_module.append_message(conversation, 'user', user_msg, timestamp=user_timestamp)

    if summarizer_module.maybe_summarize(conversation, runtime_main_model):
        conv_store_module.save_conversation(conversation)
        admin_logs_module.log_event('summary_generated', conversation_id=conversation['id'])

    now_iso_value = user_timestamp
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

    _run_hermeneutic_node_insertion_point(
        conversation=conversation,
        user_msg=user_msg,
        now_iso=now_iso_value,
        current_mode=current_mode,
        memory_traces=memory_traces,
        context_hints=context_hints,
        memory_retrieved=getattr(prepared_memory_context, 'memory_retrieved', None),
        memory_arbitration=getattr(prepared_memory_context, 'memory_arbitration', None),
        summary_input=summary_payload,
        identity_input=identity_payload,
    )

    prompt_messages = conv_store_module.build_prompt_messages(
        conversation,
        runtime_main_model,
        now=now_iso_value,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )

    if web_search_on:
        chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg=user_msg,
            conversation_id=conversation['id'],
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
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
        llm_module=llm_module,
        requests_module=requests_module,
        token_utils_module=token_utils_module,
        admin_logs_module=admin_logs_module,
        config_module=config_module,
        logger=logger,
        arbiter_module=arbiter_module,
        now_iso_func=_now_iso,
        record_identity_entries_for_mode=_record_identity_entries_for_mode,
        mode_enforces_identity=chat_memory_flow.mode_enforces_identity,
        conversation_headers_func=chat_session_flow.conversation_headers,
    )
