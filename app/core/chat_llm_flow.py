from __future__ import annotations

import json
from typing import Any, Callable, Dict, List, Mapping, Sequence


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


def run_llm_exchange(
    *,
    conversation: Dict[str, Any],
    prompt_messages: List[Dict[str, Any]],
    runtime_main_model: str,
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream_req: bool,
    current_mode: str,
    identity_ids: Sequence[str],
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
    conversation_headers_func: Callable[[Mapping[str, Any], str], Dict[str, str]],
) -> Dict[str, Any]:
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
            updated_at = now_iso_func()
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
            record_identity_entries_for_mode(
                conversation['id'],
                recent_2,
                current_mode,
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
                record_identity_entries_for_mode(
                    conversation['id'],
                    recent_2,
                    current_mode,
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
