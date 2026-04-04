from __future__ import annotations

import json
from typing import Any, Callable, Mapping, Sequence


def _json_result(payload: dict[str, Any], status: int, headers: dict[str, str] | None = None) -> dict[str, Any]:
    return {
        'kind': 'json',
        'payload': payload,
        'status': int(status),
        'headers': headers or {},
    }


def _stream_result(stream: Any, headers: dict[str, str]) -> dict[str, Any]:
    return {
        'kind': 'stream',
        'stream': stream,
        'headers': headers,
    }


def run_llm_exchange(
    *,
    conversation: dict[str, Any],
    prompt_messages: list[dict[str, Any]],
    runtime_main_model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream_req: bool,
    current_mode: str,
    identity_ids: Sequence[str],
    web_input: Mapping[str, Any] | None,
    runtime_settings_module: Any,
    memory_store_module: Any,
    conv_store_module: Any,
    llm_module: Any,
    requests_module: Any,
    token_utils_module: Any,
    admin_logs_module: Any,
    config_module: Any,
    logger: Any,
    arbiter_module: Any,
    now_iso_func: Callable[[], str],
    record_identity_entries_for_mode: Callable[..., None],
    mode_enforces_identity: Callable[[str], bool],
    conversation_headers_func: Callable[[Mapping[str, Any], str], dict[str, str]],
) -> dict[str, Any]:
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
    provider_title = llm_module.resolve_provider_title('llm')
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
        provider_caller='llm',
        provider_title=provider_title,
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
                provider_caller='llm',
                provider_title=provider_title,
            )
            response = requests_module.post(url, json=payload, headers=headers, timeout=config_module.TIMEOUT_S)
            response.raise_for_status()
            obj = llm_module.read_openrouter_response_payload(response)
            provider_fields = llm_module.build_provider_observability_fields(
                caller='llm',
                provider_metadata=llm_module.extract_openrouter_provider_metadata(
                    obj,
                    requested_model=call_model,
                ),
            )
            llm_module.log_provider_metadata(logger, 'llm_provider_response', provider_fields)
            admin_logs_module.log_event(
                'llm_provider_response',
                conversation_id=conversation['id'],
                **provider_fields,
            )
            text = llm_module.extract_openrouter_text(obj)
            updated_at = now_iso_func()
            conv_store_module.append_message(conversation, 'assistant', text, timestamp=updated_at)
            estimated_assistant_tokens = token_utils_module.estimate_tokens([{'content': text}], runtime_main_model)
            admin_logs_module.log_event(
                'AssistantText',
                conversation_id=conversation['id'],
                estimated_assistant_tokens=estimated_assistant_tokens,
                message_timestamp=updated_at,
            )
            memory_store_module.save_new_traces(conversation)
            recent_2 = [
                message
                for message in conversation.get('messages', [])
                if message.get('role') in {'user', 'assistant'}
            ][-2:]
            record_identity_entries_for_mode(
                conversation['id'],
                recent_2,
                current_mode,
                web_input=web_input,
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
            if identity_ids and mode_enforces_identity(current_mode):
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
                conversation_headers_func(conversation, updated_at),
            )

        response_updated_at = now_iso_func()

        def event_stream():
            assistant_chunks: list[str] = []
            provider_metadata: dict[str, object] = {}
            provider_response_open = False
            try:
                with requests_module.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=config_module.TIMEOUT_S,
                    stream=True,
                ) as response:
                    response.raise_for_status()
                    provider_response_open = True
                    provider_metadata = llm_module.extract_openrouter_provider_metadata(
                        {},
                        requested_model=call_model,
                    )
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
                        provider_metadata = llm_module.merge_openrouter_provider_metadata(
                            provider_metadata,
                            chunk,
                            requested_model=call_model,
                        )
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
                if provider_response_open:
                    provider_fields = llm_module.build_provider_observability_fields(
                        caller='llm',
                        provider_metadata=provider_metadata,
                    )
                    llm_module.log_provider_metadata(logger, 'llm_provider_response', provider_fields)
                    admin_logs_module.log_event(
                        'llm_provider_response',
                        conversation_id=conversation['id'],
                        **provider_fields,
                    )
                assistant_text = llm_module._sanitize_encoding(''.join(assistant_chunks)).strip()
                if assistant_text:
                    conv_store_module.append_message(
                        conversation,
                        'assistant',
                        assistant_text,
                        timestamp=response_updated_at,
                    )
                    estimated_assistant_tokens = token_utils_module.estimate_tokens(
                        [{'content': assistant_text}],
                        runtime_main_model,
                    )
                    admin_logs_module.log_event(
                        'AssistantText',
                        conversation_id=conversation['id'],
                        estimated_assistant_tokens=estimated_assistant_tokens,
                        message_timestamp=response_updated_at,
                    )
                memory_store_module.save_new_traces(conversation)
                recent_2 = [
                    message
                    for message in conversation.get('messages', [])
                    if message.get('role') in {'user', 'assistant'}
                ][-2:]
                record_identity_entries_for_mode(
                    conversation['id'],
                    recent_2,
                    current_mode,
                    web_input=web_input,
                    arbiter_module=arbiter_module,
                    memory_store_module=memory_store_module,
                    admin_logs_module=admin_logs_module,
                )
                if identity_ids and mode_enforces_identity(current_mode):
                    memory_store_module.reactivate_identities(identity_ids)
                conv_store_module.save_conversation(conversation, updated_at=response_updated_at)

        logger.info('llm_call id=%s model=%s messages=%s stream=true', conversation['id'], call_model, len(prompt_messages))
        admin_logs_module.log_event(
            'llm_call',
            conversation_id=conversation['id'],
            model=call_model,
            message_count=len(prompt_messages),
            stream=True,
            provider_caller='llm',
            provider_title=provider_title,
        )
        return _stream_result(
            event_stream(),
            conversation_headers_func(conversation, response_updated_at),
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
