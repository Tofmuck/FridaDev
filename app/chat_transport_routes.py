import codecs
from typing import Any, Callable

from flask import Flask


def register_chat_route(
    app: Flask,
    *,
    get_request: Callable[[], Any],
    get_finish_chat_turn: Callable[[], Callable[..., None]],
    chat_service_module: Any,
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
    logger_obj: Any,
    workspace_file_selections_module: Any,
    workspace_folders_module: Any,
    workspace_folder_notes_module: Any,
    workspace_folder_notes_read_module: Any,
    chat_turn_logger_module: Any,
    chat_stream_control_module: Any,
    conv_store_chat_log_proxy_class: type,
    llm_chat_log_proxy_class: type,
    requests_chat_log_proxy_class: type,
    admin_logs_chat_log_proxy_class: type,
    classify_chat_response_status: Callable[[int, Any], tuple[str, str]],
    response_class: type,
    stream_with_context_func: Callable[..., Any],
    jsonify_func: Callable[..., Any],
    time_module: Any,
) -> Callable[[], Any]:
    def api_chat():
        current_request = get_request()
        data = current_request.get_json(force=True, silent=True) or {}
        user_msg = str(data.get('message') or '')
        web_search_on = bool(data.get('web_search'))
        conversation_id_hint = conv_store_module.normalize_conversation_id(data.get('conversation_id'))
        turn_token = chat_turn_logger_module.begin_turn(
            conversation_id=conversation_id_hint,
            user_msg=user_msg,
            web_search_enabled=web_search_on,
        )

        conv_proxy = conv_store_chat_log_proxy_class(conv_store_module, token_utils_module)
        llm_proxy = llm_chat_log_proxy_class(llm_module, token_utils_module)
        requests_proxy = requests_chat_log_proxy_class(requests_module)
        admin_logs_proxy = admin_logs_chat_log_proxy_class(admin_logs_module)

        try:
            result = chat_service_module.chat_response(
                data,
                prompt_loader_module=prompt_loader_module,
                conv_store_module=conv_proxy,
                memory_store_module=memory_store_module,
                runtime_settings_module=runtime_settings_module,
                summarizer_module=summarizer_module,
                identity_module=identity_module,
                admin_logs_module=admin_logs_proxy,
                llm_module=llm_proxy,
                requests_module=requests_proxy,
                token_utils_module=token_utils_module,
                arbiter_module=arbiter_module,
                web_search_module=web_search_module,
                config_module=config_module,
                logger=logger_obj,
                workspace_file_selections_module=workspace_file_selections_module,
                workspace_folders_module=workspace_folders_module,
                workspace_folder_notes_module=workspace_folder_notes_module,
                workspace_folder_notes_read_module=workspace_folder_notes_read_module,
            )
        except Exception as exc:
            chat_turn_logger_module.emit_error(
                error_code='upstream_error',
                error_class=exc.__class__.__name__,
                message_short='chat route unhandled error',
            )
            finish_chat_turn = get_finish_chat_turn()
            finish_chat_turn(turn_token, final_status='error')
            raise

        if result['kind'] == 'stream':
            def _stream_with_turn_finalize():
                final_status = 'ok'
                stream_response_chars = 0
                stream_chunk_count = 0
                llm_call_error_class: str | None = None
                llm_call_error_code: str | None = None
                stream_terminal_event: str | None = None
                stream_terminal_seen = False
                utf8_decoder = codecs.getincrementaldecoder('utf-8')('ignore')

                def _mark_stream_error(*, error_code: str, error_class: str, message_short: str) -> str | None:
                    nonlocal final_status, llm_call_error_class, llm_call_error_code
                    nonlocal stream_terminal_event, stream_terminal_seen
                    final_status = 'error'
                    llm_call_error_class = error_class
                    llm_call_error_code = error_code
                    chat_turn_logger_module.emit_error(
                        error_code=error_code,
                        error_class=error_class,
                        message_short=message_short,
                    )
                    if stream_terminal_seen:
                        return None
                    stream_terminal_seen = True
                    stream_terminal_event = chat_stream_control_module.STREAM_TERMINAL_ERROR
                    return chat_stream_control_module.build_terminal_chunk(
                        chat_stream_control_module.STREAM_TERMINAL_ERROR,
                        error_code=error_code,
                    )

                try:
                    for chunk in result['stream']:
                        terminal = chat_stream_control_module.parse_terminal_chunk(chunk)
                        if terminal is not None:
                            if stream_terminal_seen:
                                final_status = 'error'
                                llm_call_error_class = 'multiple_stream_terminal'
                                llm_call_error_code = 'stream_protocol_error'
                                raise RuntimeError('multiple stream terminals emitted')
                            stream_terminal_seen = True
                            stream_terminal_event = terminal.get('event')
                            if stream_terminal_event == chat_stream_control_module.STREAM_TERMINAL_ERROR:
                                final_status = 'error'
                                llm_call_error_class = 'stream_terminal_error'
                                llm_call_error_code = terminal.get('error_code') or 'stream_protocol_error'
                            yield chunk
                            continue
                        if stream_terminal_seen:
                            final_status = 'error'
                            llm_call_error_class = 'content_after_stream_terminal'
                            llm_call_error_code = 'stream_protocol_error'
                            raise RuntimeError('content emitted after stream terminal')
                        if isinstance(chunk, (bytes, bytearray)):
                            stream_response_chars += len(utf8_decoder.decode(bytes(chunk), final=False))
                        else:
                            stream_response_chars += len(str(chunk or ''))
                        stream_chunk_count += 1
                        yield chunk
                    if not stream_terminal_seen:
                        terminal_chunk = _mark_stream_error(
                            error_code='stream_protocol_error',
                            error_class='missing_stream_terminal',
                            message_short='stream ended without terminal',
                        )
                        if terminal_chunk is not None:
                            yield terminal_chunk
                except Exception as exc:
                    terminal_chunk = _mark_stream_error(
                        error_code=llm_call_error_code or 'stream_finalize_error',
                        error_class=exc.__class__.__name__,
                        message_short='llm stream finalize error',
                    )
                    if terminal_chunk is not None:
                        yield terminal_chunk
                finally:
                    stream_meta = chat_turn_logger_module.get_state('llm_stream_call_meta', {}) or {}
                    stream_started_at = stream_meta.get('started_at')
                    if isinstance(stream_started_at, (int, float)):
                        llm_call_duration_ms = max(0.0, (time_module.perf_counter() - float(stream_started_at)) * 1000.0)
                    else:
                        llm_call_duration_ms = None

                    # Flush pending UTF-8 continuation bytes to keep response_chars accurate
                    # when a multi-byte character spans two streamed byte chunks.
                    stream_response_chars += len(utf8_decoder.decode(b'', final=True))
                    if not stream_terminal_seen:
                        final_status = 'error'
                        llm_call_error_class = llm_call_error_class or 'missing_stream_terminal'
                        llm_call_error_code = llm_call_error_code or 'stream_protocol_error'

                    llm_payload = {
                        'mode': 'stream',
                        'timeout_s': stream_meta.get('timeout_s'),
                        'response_chars': stream_response_chars,
                        'stream_chunks': stream_chunk_count,
                    }
                    if stream_terminal_event:
                        llm_payload['stream_terminal'] = stream_terminal_event
                    provider_meta = chat_turn_logger_module.get_state('llm_provider_response_meta', {}) or {}
                    if isinstance(provider_meta, dict):
                        llm_payload.update(provider_meta)
                    for key in ('provider_caller', 'provider_title'):
                        if key not in llm_payload and stream_meta.get(key):
                            llm_payload[key] = stream_meta.get(key)
                    llm_status = 'error' if final_status == 'error' else 'ok'
                    if llm_call_error_class:
                        llm_payload['error_class'] = llm_call_error_class
                    if llm_call_error_code:
                        llm_payload['error_code'] = llm_call_error_code
                    chat_turn_logger_module.emit(
                        'llm_call',
                        status=llm_status,
                        model=str(stream_meta.get('model') or ''),
                        duration_ms=llm_call_duration_ms,
                        error_code=llm_call_error_code if final_status == 'error' else None,
                        payload=llm_payload,
                    )
                    chat_turn_logger_module.set_state('llm_stream_call_meta', None)
                    chat_turn_logger_module.set_state('llm_provider_response_meta', None)
                    finish_chat_turn = get_finish_chat_turn()
                    finish_chat_turn(turn_token, final_status=final_status)

            response = response_class(
                stream_with_context_func(_stream_with_turn_finalize()),
                content_type='text/plain; charset=utf-8',
            )
            for key, value in result['headers'].items():
                response.headers[key] = value
            return response

        status_code = int(result['status'])
        result_payload = result['payload'] if isinstance(result.get('payload'), dict) else {}
        final_status, final_reason_code = classify_chat_response_status(status_code, result_payload)
        if final_status == 'error':
            chat_turn_logger_module.emit_error(
                error_code=final_reason_code or 'upstream_error',
                error_class='chat_response_error',
                message_short=f'chat status {status_code}',
            )
        elif final_status != 'ok':
            chat_turn_logger_module.emit_refusal(
                reason_code=final_reason_code or final_status,
                reason_short=f'chat status {status_code}',
                status=final_status,
            )

        response = jsonify_func(result['payload'])
        response.status_code = status_code
        for key, value in result['headers'].items():
            response.headers[key] = value
        finish_chat_turn = get_finish_chat_turn()
        finish_chat_turn(turn_token, final_status=final_status)
        return response

    app.add_url_rule(
        '/api/chat',
        endpoint='api_chat',
        view_func=api_chat,
        methods=['POST'],
    )
    return api_chat
