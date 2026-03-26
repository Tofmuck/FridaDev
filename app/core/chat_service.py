from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Mapping

from core import chat_memory_flow
from core import chat_prompt_context
from core import chat_session_flow


# Phase 4 bis - Cartographie locale des responsabilités de ce module:
# 1) Session/conversation + headers HTTP: delegue a core.chat_session_flow
# 2) Contexte/prompt: prompts backend + temporalite + identite + injection web
# 3) Memoire/arbitrage: delegue a core.chat_memory_flow
# 4) Appel LLM: sync + stream, persistance conversation, gestion erreurs


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _json_result(payload: Dict[str, Any], status: int, headers: Dict[str, str] | None = None) -> Dict[str, Any]:
    return {
        'kind': 'json',
        'payload': payload,
        'status': int(status),
        'headers': headers or {},
    }


def _stream_result(stream: Any, headers: Dict[str, str]) -> Dict[str, Any]:
    return {
        'kind': 'stream',
        'stream': stream,
        'headers': headers,
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

    try:
        runtime_settings_module.get_runtime_secret_value('main_model', 'api_key')
    except (
        runtime_settings_module.RuntimeSettingsSecretRequiredError,
        runtime_settings_module.RuntimeSettingsSecretResolutionError,
    ) as exc:
        return _json_result({'ok': False, 'error': str(exc)}, 500)

    headers = llm_module.or_headers(caller='llm')
    payload = llm_module.build_payload(prompt_messages, temperature, top_p, max_tokens, stream=stream_req)
    call_model = str(payload['model'])
    url = f'{config_module.OR_BASE}/chat/completions'

    admin_logs_module.log_event(
        'llm_payload',
        conversation_id=conversation['id'],
        model=call_model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream=stream_req,
        message_count=len(prompt_messages),
    )

    try:
        if not stream_req:
            logger.info('llm_call id=%s model=%s messages=%s', conversation['id'], call_model, len(prompt_messages))
            admin_logs_module.log_event(
                'llm_call',
                conversation_id=conversation['id'],
                model=call_model,
                message_count=len(prompt_messages),
                stream=False,
            )
            response = requests_module.post(url, json=payload, headers=headers, timeout=config_module.TIMEOUT_S)
            response.raise_for_status()
            obj = response.json()
            text = llm_module._sanitize_encoding(obj['choices'][0]['message']['content'])
            updated_at = _now_iso()
            conv_store_module.append_message(conversation, 'assistant', text, timestamp=updated_at)
            assistant_tokens = token_utils_module.count_tokens([{'content': text}], runtime_main_model)
            admin_logs_module.log_event(
                'AssistantText',
                conversation_id=conversation['id'],
                assistant_tokens=assistant_tokens,
                message_timestamp=updated_at,
            )
            memory_store_module.save_new_traces(conversation)
            recent_2 = [
                message
                for message in conversation.get('messages', [])
                if message.get('role') in {'user', 'assistant'}
            ][-2:]
            _record_identity_entries_for_mode(
                conversation['id'],
                recent_2,
                current_mode,
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
            if identity_ids and chat_memory_flow.mode_enforces_identity(current_mode):
                memory_store_module.reactivate_identities(identity_ids)
            conv_store_module.save_conversation(conversation, updated_at=updated_at)
            return _json_result(
                {
                    'ok': True,
                    'text': text,
                    'conversation_id': conversation['id'],
                    'created_at': conversation['created_at'],
                    'updated_at': updated_at,
                },
                200,
                chat_session_flow.conversation_headers(conversation, updated_at),
            )

        response_updated_at = _now_iso()

        def event_stream():
            assistant_chunks: list[str] = []
            try:
                with requests_module.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=config_module.TIMEOUT_S,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    response.encoding = response.encoding or 'utf-8'
                    for line in response.iter_lines(decode_unicode=True, delimiter='\n'):
                        if not line or not line.startswith('data:'):
                            continue
                        data_str = line[5:].strip()
                        if data_str == '[DONE]':
                            break
                        try:
                            chunk = json.loads(data_str)
                        except json.JSONDecodeError:
                            continue
                        delta = chunk.get('choices', [{}])[0].get('delta', {})
                        content = delta.get('content')
                        if content:
                            assistant_chunks.append(content)
                            yield llm_module._sanitize_encoding(content)
            except requests_module.exceptions.RequestException as exc:
                logger.error('llm_stream_error id=%s err=%s', conversation['id'], exc)
                admin_logs_module.log_event(
                    'llm_stream_error',
                    level='ERROR',
                    conversation_id=conversation['id'],
                    model=call_model,
                    error=str(exc),
                )
            finally:
                assistant_text = llm_module._sanitize_encoding(''.join(assistant_chunks)).strip()
                if assistant_text:
                    conv_store_module.append_message(
                        conversation,
                        'assistant',
                        assistant_text,
                        timestamp=response_updated_at,
                    )
                    assistant_tokens = token_utils_module.count_tokens([{'content': assistant_text}], runtime_main_model)
                    admin_logs_module.log_event(
                        'AssistantText',
                        conversation_id=conversation['id'],
                        assistant_tokens=assistant_tokens,
                        message_timestamp=response_updated_at,
                    )
                memory_store_module.save_new_traces(conversation)
                recent_2 = [
                    message
                    for message in conversation.get('messages', [])
                    if message.get('role') in {'user', 'assistant'}
                ][-2:]
                _record_identity_entries_for_mode(
                    conversation['id'],
                    recent_2,
                    current_mode,
                    arbiter_module=arbiter_module,
                    memory_store_module=memory_store_module,
                    admin_logs_module=admin_logs_module,
                )
                if identity_ids and chat_memory_flow.mode_enforces_identity(current_mode):
                    memory_store_module.reactivate_identities(identity_ids)
                conv_store_module.save_conversation(conversation, updated_at=response_updated_at)

        logger.info('llm_call id=%s model=%s messages=%s stream=true', conversation['id'], call_model, len(prompt_messages))
        admin_logs_module.log_event(
            'llm_call',
            conversation_id=conversation['id'],
            model=call_model,
            message_count=len(prompt_messages),
            stream=True,
        )
        return _stream_result(
            event_stream(),
            chat_session_flow.conversation_headers(conversation, response_updated_at),
        )

    except requests_module.exceptions.RequestException as exc:
        conv_store_module.save_conversation(conversation)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=call_model,
            error=str(exc),
        )
        return _json_result({'ok': False, 'error': f'Connexion au LLM: {exc}'}, 502)
    except Exception as exc:
        conv_store_module.save_conversation(conversation)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=call_model,
            error=str(exc),
        )
        return _json_result({'ok': False, 'error': f'Erreur: {exc}'}, 500)
