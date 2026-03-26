from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from core import chat_llm_flow
from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow


# Phase 4 bis - Cartographie locale des responsabilités de ce module:
# 1) Session/conversation + headers HTTP: delegue a core.chat_session_flow
# 2) Contexte/prompt: prompts backend + temporalite + identite + injection web
# 3) Memoire/arbitrage: delegue a core.chat_memory_flow
# 4) Appel LLM: delegue a core.chat_llm_flow


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _json_result(payload: Dict[str, Any], status: int, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    return {
        'kind': 'json',
        'payload': payload,
        'status': int(status),
        'headers': headers or {},
    }


def _record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: List[Dict[str, Any]],
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
) -> Dict[str, Any]:
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
    )
    chat_prompt_context.apply_augmented_system(conversation, augmented_system)

    current_mode, memory_traces, context_hints = chat_memory_flow.prepare_memory_context(
        conversation=conversation,
        user_msg=user_msg,
        config_module=config_module,
        memory_store_module=memory_store_module,
        arbiter_module=arbiter_module,
        admin_logs_module=admin_logs_module,
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
