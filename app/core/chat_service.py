from __future__ import annotations

import json
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Mapping
from zoneinfo import ZoneInfo


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
    now_iso: Callable[[], str],
    log_stage_latency: Callable[[str, str, float], float],
    hermeneutic_mode: Callable[[], str],
    mode_runs_arbiter: Callable[[str], bool],
    mode_enforces_memory: Callable[[str], bool],
    mode_enforces_identity: Callable[[str], bool],
    record_identity_entries_for_mode: Callable[[str, List[Dict[str, Any]], str], None],
) -> Dict[str, Any]:
    user_msg = (data.get('message') or '').strip()
    system_prompt = prompt_loader_module.get_main_system_prompt()
    hermeneutical_prompt = prompt_loader_module.get_main_hermeneutical_prompt()
    conversation_id_raw = data.get('conversation_id')
    stream_req = bool(data.get('stream'))
    web_search_on = bool(data.get('web_search'))

    if not user_msg:
        return _json_result({'ok': False, 'error': 'message vide'}, 400)

    conversation_id = conv_store_module.normalize_conversation_id(conversation_id_raw)
    if conversation_id:
        conversation = conv_store_module.load_conversation(conversation_id, system_prompt)
        if not conversation:
            return _json_result({'ok': False, 'error': 'conversation introuvable'}, 404)
    else:
        if conversation_id_raw:
            logger.info('conv_id_invalid raw=%s', conversation_id_raw)
        conversation = conv_store_module.new_conversation(system_prompt)
        conv_store_module.save_conversation(conversation)
        logger.info(
            'conv_created id=%s path=%s',
            conversation['id'],
            conv_store_module.conversation_path(conversation['id']),
        )
        memory_store_module.decay_identities()

    runtime_main_view = runtime_settings_module.get_main_model_settings()
    runtime_main_payload = runtime_main_view.payload
    runtime_main_model = str(runtime_main_payload['model']['value'])
    temperature = float(runtime_main_payload['temperature']['value'])
    top_p = float(runtime_main_payload['top_p']['value'])
    runtime_response_max_tokens = int(runtime_main_payload['response_max_tokens']['value'])
    max_tokens = int(data.get('max_tokens') or runtime_response_max_tokens)

    user_timestamp = now_iso()
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
    tz_paris = ZoneInfo(config_module.FRIDA_TIMEZONE)
    now_paris = datetime.now(tz_paris)
    now_fmt = now_paris.strftime('%A %d %B %Y à %H:%M') + f" (heure de Paris, UTC{now_paris.strftime('%z')[:3]})"
    id_block, identity_ids = identity_module.build_identity_block()
    delta_rule = (
        '[RÉFÉRENCE TEMPORELLE]\n'
        f"Nous sommes le {now_fmt}. C'est ton 'maintenant'.\n"
        "Les messages ci-dessous sont horodatés relativement à ce maintenant (ex : 'il y a 2 jours').\n"
        'Les marqueurs [— silence de X —] indiquent une interruption de la conversation. '
        "Tu n'as pas à les mentionner, mais tu peux en tenir compte dans ton ton si c'est pertinent.\n"
        "Ne mentionne jamais spontanément la date ou l'heure dans tes réponses, "
        'sauf si on te le demande explicitement.'
    )
    parts = [p for p in [system_prompt, hermeneutical_prompt, delta_rule, id_block] if p]
    augmented_system = '\n\n'.join(parts)
    if conversation['messages'] and conversation['messages'][0]['role'] == 'system':
        conversation['messages'][0]['content'] = augmented_system

    current_mode = hermeneutic_mode()
    admin_logs_module.log_event(
        'hermeneutic_mode',
        conversation_id=conversation['id'],
        mode=current_mode,
    )

    retrieve_t0 = time.perf_counter()
    raw_traces = memory_store_module.retrieve(user_msg)
    log_stage_latency(conversation['id'], 'retrieve', retrieve_t0)

    recent_turns = [
        message
        for message in conversation.get('messages', [])
        if message.get('role') in {'user', 'assistant'}
    ][-10:]

    if raw_traces:
        admin_logs_module.log_event('memory_retrieved', conversation_id=conversation['id'], count=len(raw_traces))

        memory_traces = list(raw_traces)
        filtered_traces: List[Dict[str, Any]] = []
        arbiter_decisions: List[Dict[str, Any]] = []

        if mode_runs_arbiter(current_mode):
            arbiter_t0 = time.perf_counter()
            filtered_traces, arbiter_decisions = arbiter_module.filter_traces_with_diagnostics(raw_traces, recent_turns)
            log_stage_latency(conversation['id'], 'arbiter', arbiter_t0)

            memory_store_module.record_arbiter_decisions(conversation['id'], raw_traces, arbiter_decisions)
            admin_logs_module.log_event(
                'memory_arbitrated',
                conversation_id=conversation['id'],
                raw=len(raw_traces),
                kept=len(filtered_traces),
                decisions=len(arbiter_decisions),
            )

            if mode_enforces_memory(current_mode):
                memory_traces = filtered_traces
                memory_source = 'arbiter_enforced'
            else:
                memory_source = 'raw_shadow_non_blocking'
        else:
            memory_source = 'raw_mode_off'

        admin_logs_module.log_event(
            'memory_mode_apply',
            conversation_id=conversation['id'],
            mode=current_mode,
            source=memory_source,
            raw=len(raw_traces),
            selected=len(memory_traces),
            filtered=len(filtered_traces),
        )

        if memory_traces:
            memory_traces = memory_store_module.enrich_traces_with_summaries(memory_traces)
    else:
        memory_traces = []

    context_hints = memory_store_module.get_recent_context_hints(
        max_items=config_module.CONTEXT_HINTS_MAX_ITEMS,
        max_age_days=config_module.CONTEXT_HINTS_MAX_AGE_DAYS,
        min_confidence=config_module.CONTEXT_HINTS_MIN_CONFIDENCE,
    )
    if context_hints:
        admin_logs_module.log_event(
            'context_hints_selected',
            conversation_id=conversation['id'],
            count=len(context_hints),
        )

    prompt_messages = conv_store_module.build_prompt_messages(
        conversation,
        runtime_main_model,
        now=now_iso_value,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )

    if web_search_on:
        ctx, search_query, n_results, has_tm = web_search_module.build_context(user_msg)
        if ctx:
            for index in range(len(prompt_messages) - 1, -1, -1):
                if prompt_messages[index].get('role') == 'user':
                    prompt_messages[index] = {
                        'role': 'user',
                        'content': ctx + '\n\nQuestion : ' + prompt_messages[index]['content'],
                    }
                    break
            admin_logs_module.log_event(
                'web_search',
                conversation_id=conversation['id'],
                query=search_query,
                original=user_msg,
                results=n_results,
                ticketmaster=has_tm,
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
            updated_at = now_iso()
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
            record_identity_entries_for_mode(conversation['id'], recent_2, current_mode)
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
                {
                    'X-Conversation-Id': conversation['id'],
                    'X-Conversation-Created-At': conversation['created_at'],
                    'X-Conversation-Updated-At': updated_at,
                },
            )

        response_updated_at = now_iso()

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
                record_identity_entries_for_mode(conversation['id'], recent_2, current_mode)
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
            {
                'X-Conversation-Id': conversation['id'],
                'X-Conversation-Created-At': conversation['created_at'],
                'X-Conversation-Updated-At': response_updated_at,
            },
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
