from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any, Callable, Mapping, Sequence

from core import assistant_turn_state
from core import assistant_output_contract
from core import chat_stream_control


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


def _build_stream_headers(
    conversation: Mapping[str, Any],
    conversation_stream_headers_func: Callable[[Mapping[str, Any]], dict[str, str]] | None,
) -> dict[str, str]:
    if conversation_stream_headers_func is not None:
        return dict(conversation_stream_headers_func(conversation))
    return {
        'X-Conversation-Id': str(conversation['id']),
        'X-Conversation-Created-At': str(conversation['created_at']),
    }


CONVERSATION_PERSIST_ERROR_CODE = chat_stream_control.STREAM_ERROR_CONVERSATION_PERSIST_FAILED
LLM_UPSTREAM_ERROR_CODE = "upstream_error"
LLM_UPSTREAM_REASON_CODE = "llm_upstream_error"
LLM_INTERNAL_ERROR_CODE = "llm_internal_error"
LLM_STREAM_FINALIZE_ERROR_CODE = "stream_finalize_error"
LLM_RUNTIME_SECRET_ERROR_CODE = "llm_secret_resolution_error"
LLM_UPSTREAM_USER_MESSAGE = "Connexion au LLM impossible"
LLM_INTERNAL_USER_MESSAGE = "Erreur LLM interne"
LLM_CONFIG_USER_MESSAGE = "Configuration LLM indisponible"
POST_PERSISTENCE_AUX_ERROR_EVENT = "chat_post_persistence_aux_error"


def _exception_class(exc: BaseException) -> str:
    name = str(exc.__class__.__name__ or "").strip()
    return name if name.replace("_", "").isalnum() else "Exception"


def _llm_error_payload(
    *,
    message: str,
    error_code: str,
    reason_code: str,
    error_class: str,
) -> dict[str, Any]:
    return {
        "ok": False,
        "error": message,
        "error_code": error_code,
        "reason_code": reason_code,
        "error_class": error_class,
    }


@dataclass(frozen=True, repr=False)
class AssistantResponseOverride:
    content: str = field(repr=False, compare=False)
    source: str = ""
    reason_code: str = ""
    meta: Mapping[str, Any] | None = field(default=None, repr=False, compare=False)
    observability: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    def to_observability(self) -> dict[str, Any]:
        return {
            "source": str(self.source or "").strip(),
            "reason_code": str(self.reason_code or "").strip(),
            "content_present": bool(str(self.content or "")),
            "content_chars": len(str(self.content or "")),
            "meta_present": self.meta is not None,
            "observability": dict(self.observability or {}),
        }


def _save_result_ok(result: Any) -> bool:
    if result is None:
        return True
    return bool(getattr(result, 'ok', False))


def _save_result_reason(result: Any) -> str:
    reason = str(getattr(result, 'reason', '') or '').strip()
    return reason or CONVERSATION_PERSIST_ERROR_CODE


def _save_result_updated_at(result: Any, fallback: str | None) -> str | None:
    updated_at = str(getattr(result, 'updated_at', '') or '').strip()
    return updated_at or fallback


def _persistence_failure_payload(result: Any) -> dict[str, Any]:
    return {
        'ok': False,
        'error': 'sauvegarde conversationnelle impossible',
        'reason': _save_result_reason(result),
    }


def _mark_next_persist_phase(conv_store_module: Any, phase: str) -> None:
    marker = getattr(conv_store_module, 'mark_next_persist_phase', None)
    if callable(marker):
        marker(phase)


def _compose_assistant_response(
    content: str,
    *,
    intro: str = "",
    outro: str = "",
) -> str:
    parts = [
        text
        for text in (str(intro or "").strip(), str(content or "").strip(), str(outro or "").strip())
        if text
    ]
    return "\n\n".join(parts)


def _latest_completed_identity_pair(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    dialog_messages = [
        dict(message or {})
        for message in messages
        if str(message.get('role') or '').strip().lower() in {'user', 'assistant'}
    ]
    if not dialog_messages:
        return []
    assistant_message = dialog_messages[-1]
    if str(assistant_message.get('role') or '').strip().lower() != 'assistant':
        return []
    for candidate in reversed(dialog_messages[:-1]):
        if str(candidate.get('role') or '').strip().lower() == 'user':
            return [candidate, assistant_message]
    return []


def _run_chat_post_persistence_effects(
    *,
    conversation: dict[str, Any],
    assistant_text: str | None,
    assistant_timestamp: str | None,
    runtime_main_model: str,
    current_mode: str,
    identity_ids: Sequence[str],
    web_input: Mapping[str, Any] | None,
    memory_store_module: Any,
    token_utils_module: Any,
    admin_logs_module: Any,
    logger: Any,
    arbiter_module: Any,
    record_identity_entries_for_mode: Callable[..., None],
    mode_enforces_identity: Callable[[str], bool],
    traces_after_identity: bool,
) -> None:
    def record_assistant_text_observability() -> None:
        if assistant_text is None:
            return
        estimated_assistant_tokens = token_utils_module.estimate_tokens(
            [{'content': assistant_text}],
            runtime_main_model,
        )
        admin_logs_module.log_event(
            'AssistantText',
            conversation_id=conversation['id'],
            estimated_assistant_tokens=estimated_assistant_tokens,
            message_timestamp=assistant_timestamp,
        )

    def save_memory_traces() -> None:
        memory_store_module.save_new_traces(conversation)

    def record_identity_entries() -> None:
        completed_turn_pair = _latest_completed_identity_pair(conversation.get('messages', []))
        record_identity_entries_for_mode(
            conversation['id'],
            completed_turn_pair,
            mode=current_mode,
            web_input=web_input,
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

    def reactivate_identities() -> None:
        if not identity_ids or not mode_enforces_identity(current_mode):
            return
        memory_store_module.reactivate_identities(identity_ids)

    effects = {
        'assistant_text_observability': record_assistant_text_observability,
        'memory_traces': save_memory_traces,
        'identity_entries': record_identity_entries,
        'identity_reactivation': reactivate_identities,
    }
    if traces_after_identity:
        effect_order = (
            'assistant_text_observability',
            'identity_entries',
            'identity_reactivation',
            'memory_traces',
        )
    else:
        effect_order = (
            'assistant_text_observability',
            'memory_traces',
            'identity_entries',
            'identity_reactivation',
        )

    for effect_name in effect_order:
        try:
            effects[effect_name]()
        except Exception as exc:
            error_class = _exception_class(exc)[:80]
            try:
                logger.error(
                    'chat_post_persistence_aux_error effect=%s id=%s error_class=%s',
                    effect_name,
                    conversation['id'],
                    error_class,
                )
            except Exception:
                pass
            try:
                admin_logs_module.log_event(
                    POST_PERSISTENCE_AUX_ERROR_EVENT,
                    level='ERROR',
                    conversation_id=conversation['id'],
                    effect_name=effect_name,
                    error_class=error_class,
                    reason_code=POST_PERSISTENCE_AUX_ERROR_EVENT,
                )
            except Exception:
                pass


def _run_assistant_response_override(
    *,
    override: AssistantResponseOverride,
    conversation: dict[str, Any],
    runtime_main_model: str,
    stream_req: bool,
    current_mode: str,
    identity_ids: Sequence[str],
    web_input: Mapping[str, Any] | None,
    memory_store_module: Any,
    conv_store_module: Any,
    token_utils_module: Any,
    admin_logs_module: Any,
    logger: Any,
    arbiter_module: Any,
    now_iso_func: Callable[[], str],
    record_identity_entries_for_mode: Callable[..., None],
    mode_enforces_identity: Callable[[str], bool],
    conversation_headers_func: Callable[[Mapping[str, Any], str], dict[str, str]],
    conversation_stream_headers_func: Callable[[Mapping[str, Any]], dict[str, str]] | None = None,
) -> dict[str, Any]:
    text = str(override.content or "")
    source = str(override.source or "").strip()
    reason_code = str(override.reason_code or "").strip()
    override_observability = {
        key: value
        for key, value in override.to_observability().items()
        if key not in {"source", "reason_code"}
    }
    admin_logs_module.log_event(
        "assistant_response_override",
        conversation_id=conversation["id"],
        source=source,
        reason_code=reason_code,
        stream=stream_req,
        **override_observability,
    )

    def persist_and_record() -> tuple[bool, str | None, dict[str, Any] | None]:
        updated_at = now_iso_func()
        append_kwargs: dict[str, Any] = {"timestamp": updated_at}
        if override.meta is not None:
            append_kwargs["meta"] = dict(override.meta)
        conv_store_module.append_message(conversation, "assistant", text, **append_kwargs)
        _mark_next_persist_phase(conv_store_module, "assistant_final")
        save_result = conv_store_module.save_conversation(conversation, updated_at=updated_at)
        if not _save_result_ok(save_result):
            messages = conversation.get("messages")
            if isinstance(messages, list) and messages:
                last = messages[-1]
                if isinstance(last, dict) and last.get("role") == "assistant" and last.get("content") == text:
                    messages.pop()
            return False, updated_at, _persistence_failure_payload(save_result)
        persisted_at = _save_result_updated_at(save_result, updated_at)
        _run_chat_post_persistence_effects(
            conversation=conversation,
            assistant_text=text,
            assistant_timestamp=persisted_at,
            runtime_main_model=runtime_main_model,
            current_mode=current_mode,
            identity_ids=identity_ids,
            web_input=web_input,
            memory_store_module=memory_store_module,
            token_utils_module=token_utils_module,
            admin_logs_module=admin_logs_module,
            logger=logger,
            arbiter_module=arbiter_module,
            record_identity_entries_for_mode=record_identity_entries_for_mode,
            mode_enforces_identity=mode_enforces_identity,
            traces_after_identity=False,
        )
        return True, persisted_at, None

    if not stream_req:
        ok, updated_at, failure_payload = persist_and_record()
        if not ok:
            return _json_result(failure_payload or _persistence_failure_payload(None), 503)
        return _json_result(
            {
                "ok": True,
                "text": text,
                "conversation_id": conversation["id"],
                "created_at": conversation["created_at"],
                "updated_at": updated_at,
            },
            200,
            conversation_headers_func(conversation, str(updated_at or "")),
        )

    stream_headers = _build_stream_headers(conversation, conversation_stream_headers_func)

    def event_stream():
        ok, updated_at, _failure_payload = persist_and_record()
        if not ok:
            yield chat_stream_control.build_terminal_chunk(
                chat_stream_control.STREAM_TERMINAL_ERROR,
                error_code=CONVERSATION_PERSIST_ERROR_CODE,
                updated_at=None,
            )
            return
        if text:
            yield text
        yield chat_stream_control.build_terminal_chunk(
            chat_stream_control.STREAM_TERMINAL_DONE,
            updated_at=updated_at,
        )

    return _stream_result(event_stream(), stream_headers)


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
    assistant_output_policy: assistant_output_contract.AssistantOutputPolicy | None = None,
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
    conversation_stream_headers_func: Callable[[Mapping[str, Any]], dict[str, str]] | None = None,
    assistant_response_override: AssistantResponseOverride | None = None,
    assistant_response_meta: Mapping[str, Any] | None = None,
    assistant_response_intro: str = "",
    assistant_response_outro: str = "",
) -> dict[str, Any]:
    if assistant_response_override is not None and str(assistant_response_override.content or ""):
        return _run_assistant_response_override(
            override=assistant_response_override,
            conversation=conversation,
            runtime_main_model=runtime_main_model,
            stream_req=stream_req,
            current_mode=current_mode,
            identity_ids=identity_ids,
            web_input=web_input,
            memory_store_module=memory_store_module,
            conv_store_module=conv_store_module,
            token_utils_module=token_utils_module,
            admin_logs_module=admin_logs_module,
            logger=logger,
            arbiter_module=arbiter_module,
            now_iso_func=now_iso_func,
            record_identity_entries_for_mode=record_identity_entries_for_mode,
            mode_enforces_identity=mode_enforces_identity,
            conversation_headers_func=conversation_headers_func,
            conversation_stream_headers_func=conversation_stream_headers_func,
        )

    try:
        runtime_settings_module.get_runtime_secret_value('main_model', 'api_key')
    except (
        runtime_settings_module.RuntimeSettingsSecretRequiredError,
        runtime_settings_module.RuntimeSettingsSecretResolutionError,
    ) as exc:
        return _json_result(
            _llm_error_payload(
                message=LLM_CONFIG_USER_MESSAGE,
                error_code=LLM_RUNTIME_SECRET_ERROR_CODE,
                reason_code=LLM_RUNTIME_SECRET_ERROR_CODE,
                error_class=_exception_class(exc),
            ),
            500,
        )

    headers = llm_module.or_headers(caller='llm')
    payload = llm_module.build_payload(prompt_messages, temperature, top_p, max_tokens, stream=stream_req)
    call_model = str(payload['model'])
    provider_title = llm_module.resolve_provider_title('llm')
    reasoning_observability_builder = getattr(llm_module, 'main_llm_reasoning_observability_from_payload', None)
    reasoning_observability = (
        reasoning_observability_builder(payload)
        if callable(reasoning_observability_builder)
        else {}
    )
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
        **reasoning_observability,
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
                **reasoning_observability,
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
            raw_text = llm_module.extract_openrouter_text(obj)
            text = assistant_output_contract.normalize_assistant_output(
                raw_text,
                assistant_output_policy,
            )
            text = _compose_assistant_response(
                text,
                intro=assistant_response_intro,
                outro=assistant_response_outro,
            )
            updated_at = now_iso_func()
            append_kwargs: dict[str, Any] = {'timestamp': updated_at}
            if assistant_response_meta is not None:
                append_kwargs['meta'] = dict(assistant_response_meta)
            conv_store_module.append_message(conversation, 'assistant', text, **append_kwargs)
            _mark_next_persist_phase(conv_store_module, 'assistant_final')
            save_result = conv_store_module.save_conversation(conversation, updated_at=updated_at)
            if not _save_result_ok(save_result):
                return _json_result(_persistence_failure_payload(save_result), 503)
            _run_chat_post_persistence_effects(
                conversation=conversation,
                assistant_text=text,
                assistant_timestamp=updated_at,
                runtime_main_model=runtime_main_model,
                current_mode=current_mode,
                identity_ids=identity_ids,
                web_input=web_input,
                memory_store_module=memory_store_module,
                token_utils_module=token_utils_module,
                admin_logs_module=admin_logs_module,
                logger=logger,
                arbiter_module=arbiter_module,
                record_identity_entries_for_mode=record_identity_entries_for_mode,
                mode_enforces_identity=mode_enforces_identity,
                traces_after_identity=False,
            )
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

        stream_headers = _build_stream_headers(conversation, conversation_stream_headers_func)

        def event_stream():
            assistant_chunks: list[str] = []
            provider_metadata: dict[str, object] = {}
            provider_response_open = False
            stream_visible_output = ''
            terminal_final_text: str | None = None
            terminal_event = chat_stream_control.STREAM_TERMINAL_DONE
            terminal_error_code: str | None = None
            assistant_appended = False
            appended_assistant_content = ''
            appended_assistant_timestamp: str | None = None
            appended_assistant_meta: dict[str, Any] | None = None
            assistant_final_meta = dict(assistant_response_meta) if assistant_response_meta is not None else None
            assistant_has_envelope = bool(
                str(assistant_response_intro or "").strip() or str(assistant_response_outro or "").strip()
            )
            buffer_stream_output = assistant_output_contract.should_buffer_plain_text_stream(
                assistant_output_policy,
            ) or assistant_has_envelope

            def _rollback_appended_assistant() -> None:
                nonlocal assistant_appended, terminal_final_text
                nonlocal appended_assistant_content, appended_assistant_timestamp, appended_assistant_meta
                if not assistant_appended:
                    return
                messages = conversation.get('messages')
                if isinstance(messages, list) and messages:
                    last_message = messages[-1]
                    last_meta = last_message.get('meta') if isinstance(last_message, dict) else None
                    meta_matches = (
                        last_meta == appended_assistant_meta
                        if appended_assistant_meta is not None
                        else last_meta is None
                    )
                    if (
                        isinstance(last_message, dict)
                        and str(last_message.get('role') or '') == 'assistant'
                        and str(last_message.get('content') or '') == appended_assistant_content
                        and str(last_message.get('timestamp') or '') == str(appended_assistant_timestamp or '')
                        and meta_matches
                    ):
                        messages.pop()
                assistant_appended = False
                terminal_final_text = None
                appended_assistant_content = ''
                appended_assistant_timestamp = None
                appended_assistant_meta = None

            def _stream_plain_text_draft() -> str:
                nonlocal stream_visible_output
                draft_text = assistant_output_contract.normalize_assistant_output(
                    ''.join(assistant_chunks),
                    assistant_output_policy,
                )
                if not draft_text.startswith(stream_visible_output):
                    return ''
                delta = draft_text[len(stream_visible_output):]
                if delta:
                    stream_visible_output = draft_text
                return delta

            def _append_persisted_assistant_message(
                content: str,
                *,
                timestamp: str | None = None,
                meta: Mapping[str, Any] | None = None,
            ) -> None:
                nonlocal assistant_appended, appended_assistant_content
                nonlocal appended_assistant_timestamp, appended_assistant_meta
                append_kwargs: dict[str, Any] = {}
                if timestamp is not None:
                    append_kwargs['timestamp'] = timestamp
                if meta is None:
                    conv_store_module.append_message(
                        conversation,
                        'assistant',
                        content,
                        **append_kwargs,
                    )
                    appended_assistant_meta = None
                else:
                    conv_store_module.append_message(
                        conversation,
                        'assistant',
                        content,
                        meta=dict(meta),
                        **append_kwargs,
                    )
                    appended_assistant_meta = dict(meta)
                appended_assistant_content = content
                appended_assistant_timestamp = timestamp
                assistant_appended = True

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
                            sanitized_content = llm_module.sanitize_provider_text(content)
                            assistant_chunks.append(sanitized_content)
                            if not buffer_stream_output:
                                yield sanitized_content
                            elif not assistant_has_envelope:
                                draft_delta = _stream_plain_text_draft()
                                if draft_delta:
                                    yield draft_delta
            except requests_module.exceptions.RequestException as exc:
                terminal_event = chat_stream_control.STREAM_TERMINAL_ERROR
                terminal_error_code = LLM_UPSTREAM_ERROR_CODE
                error_class = _exception_class(exc)
                logger.error(
                    'llm_stream_error id=%s error_class=%s',
                    conversation['id'],
                    error_class,
                )
                admin_logs_module.log_event(
                    'llm_stream_error',
                    level='ERROR',
                    conversation_id=conversation['id'],
                    model=call_model,
                    error_class=error_class,
                    error_code=terminal_error_code,
                    reason_code=LLM_UPSTREAM_REASON_CODE,
                )
            assistant_text = llm_module.sanitize_provider_text(''.join(assistant_chunks)).strip()
            final_updated_at: str | None = None
            persisted_updated_at: str | None = None
            persistence_ok = False
            try:
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
                final_updated_at = now_iso_func()
                if terminal_event == chat_stream_control.STREAM_TERMINAL_DONE:
                    if buffer_stream_output:
                        assistant_text = assistant_output_contract.normalize_assistant_output(
                            assistant_text,
                            assistant_output_policy,
                        )
                        assistant_text = _compose_assistant_response(
                            assistant_text,
                            intro=assistant_response_intro,
                            outro=assistant_response_outro,
                        )
                        if assistant_text != stream_visible_output:
                            terminal_final_text = assistant_text
                    if assistant_text:
                        _append_persisted_assistant_message(
                            assistant_text,
                            timestamp=final_updated_at,
                            meta=assistant_final_meta,
                        )
                elif terminal_event == chat_stream_control.STREAM_TERMINAL_ERROR:
                    _append_persisted_assistant_message(
                        '',
                        timestamp=final_updated_at,
                        meta=assistant_turn_state.build_interrupted_assistant_turn_meta(
                            terminal_error_code or 'stream_protocol_error',
                        ),
                    )
                if terminal_event == chat_stream_control.STREAM_TERMINAL_DONE and assistant_appended:
                    persist_phase = 'assistant_final'
                elif terminal_event == chat_stream_control.STREAM_TERMINAL_ERROR:
                    persist_phase = 'assistant_interrupted'
                else:
                    persist_phase = 'user_turn'
                _mark_next_persist_phase(conv_store_module, persist_phase)
                save_result = conv_store_module.save_conversation(conversation, updated_at=final_updated_at)
                if _save_result_ok(save_result):
                    persisted_updated_at = _save_result_updated_at(save_result, final_updated_at)
                    persistence_ok = True
                else:
                    _rollback_appended_assistant()
                    terminal_event = chat_stream_control.STREAM_TERMINAL_ERROR
                    terminal_error_code = CONVERSATION_PERSIST_ERROR_CODE
                    final_updated_at = None
                    terminal_final_text = None
                    logger.error(
                        'llm_stream_finalize_persist_error id=%s reason=%s',
                        conversation['id'],
                        _save_result_reason(save_result),
                    )
                    admin_logs_module.log_event(
                        'llm_stream_finalize_persist_error',
                        level='ERROR',
                        conversation_id=conversation['id'],
                        model=call_model,
                        error_code=terminal_error_code,
                        reason=_save_result_reason(save_result),
                    )
            except Exception as exc:
                _rollback_appended_assistant()
                terminal_event = chat_stream_control.STREAM_TERMINAL_ERROR
                terminal_error_code = terminal_error_code or LLM_STREAM_FINALIZE_ERROR_CODE
                persistence_ok = False
                persisted_updated_at = None
                error_class = _exception_class(exc)
                logger.error(
                    'llm_stream_finalize_error id=%s error_class=%s',
                    conversation['id'],
                    error_class,
                )
                admin_logs_module.log_event(
                    'llm_stream_finalize_error',
                    level='ERROR',
                    conversation_id=conversation['id'],
                    model=call_model,
                    error_class=error_class,
                    error_code=terminal_error_code,
                    reason_code='llm_stream_finalize_error',
                )
                if final_updated_at is None:
                    try:
                        final_updated_at = now_iso_func()
                    except Exception:
                        final_updated_at = None
                _append_persisted_assistant_message(
                    '',
                    timestamp=final_updated_at,
                    meta=assistant_turn_state.build_interrupted_assistant_turn_meta(
                        terminal_error_code,
                    ),
                )
                try:
                    _mark_next_persist_phase(conv_store_module, 'assistant_interrupted')
                    if final_updated_at is None:
                        save_result = conv_store_module.save_conversation(conversation)
                    else:
                        save_result = conv_store_module.save_conversation(conversation, updated_at=final_updated_at)
                    if _save_result_ok(save_result):
                        persisted_updated_at = _save_result_updated_at(save_result, final_updated_at)
                        persistence_ok = True
                    else:
                        _rollback_appended_assistant()
                        terminal_error_code = CONVERSATION_PERSIST_ERROR_CODE
                        final_updated_at = None
                        logger.error(
                            'llm_stream_finalize_persist_error id=%s reason=%s',
                            conversation['id'],
                            _save_result_reason(save_result),
                        )
                        admin_logs_module.log_event(
                            'llm_stream_finalize_persist_error',
                            level='ERROR',
                            conversation_id=conversation['id'],
                            model=call_model,
                            error_code=terminal_error_code,
                            reason=_save_result_reason(save_result),
                        )
                except Exception as persist_exc:
                    _rollback_appended_assistant()
                    terminal_error_code = CONVERSATION_PERSIST_ERROR_CODE
                    final_updated_at = None
                    persist_error_class = _exception_class(persist_exc)
                    logger.error(
                        'llm_stream_finalize_persist_error id=%s error_class=%s',
                        conversation['id'],
                        persist_error_class,
                    )
                    admin_logs_module.log_event(
                        'llm_stream_finalize_persist_error',
                        level='ERROR',
                        conversation_id=conversation['id'],
                        model=call_model,
                        error_class=persist_error_class,
                        error_code=terminal_error_code,
                        reason_code=CONVERSATION_PERSIST_ERROR_CODE,
                    )
            if persistence_ok and terminal_event == chat_stream_control.STREAM_TERMINAL_DONE:
                _run_chat_post_persistence_effects(
                    conversation=conversation,
                    assistant_text=assistant_text if assistant_appended and assistant_text else None,
                    assistant_timestamp=persisted_updated_at or final_updated_at,
                    runtime_main_model=runtime_main_model,
                    current_mode=current_mode,
                    identity_ids=identity_ids,
                    web_input=web_input,
                    memory_store_module=memory_store_module,
                    token_utils_module=token_utils_module,
                    admin_logs_module=admin_logs_module,
                    logger=logger,
                    arbiter_module=arbiter_module,
                    record_identity_entries_for_mode=record_identity_entries_for_mode,
                    mode_enforces_identity=mode_enforces_identity,
                    traces_after_identity=True,
                )
            yield chat_stream_control.build_terminal_chunk(
                terminal_event,
                error_code=terminal_error_code,
                updated_at=persisted_updated_at if persistence_ok else None,
                final_text=terminal_final_text if persistence_ok else None,
            )

        logger.info('llm_call id=%s model=%s messages=%s stream=true', conversation['id'], call_model, len(prompt_messages))
        admin_logs_module.log_event(
            'llm_call',
            conversation_id=conversation['id'],
            model=call_model,
            message_count=len(prompt_messages),
            stream=True,
            provider_caller='llm',
            provider_title=provider_title,
            **reasoning_observability,
        )
        return _stream_result(
            event_stream(),
            stream_headers,
        )

    except requests_module.exceptions.RequestException as exc:
        _mark_next_persist_phase(conv_store_module, 'user_turn')
        conv_store_module.save_conversation(conversation)
        error_class = _exception_class(exc)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=call_model,
            error_class=error_class,
            error_code=LLM_UPSTREAM_ERROR_CODE,
            reason_code=LLM_UPSTREAM_REASON_CODE,
        )
        return _json_result(
            _llm_error_payload(
                message=LLM_UPSTREAM_USER_MESSAGE,
                error_code=LLM_UPSTREAM_ERROR_CODE,
                reason_code=LLM_UPSTREAM_REASON_CODE,
                error_class=error_class,
            ),
            502,
        )
    except Exception as exc:
        _mark_next_persist_phase(conv_store_module, 'user_turn')
        conv_store_module.save_conversation(conversation)
        error_class = _exception_class(exc)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=call_model,
            error_class=error_class,
            error_code=LLM_INTERNAL_ERROR_CODE,
            reason_code=LLM_INTERNAL_ERROR_CODE,
        )
        return _json_result(
            _llm_error_payload(
                message=LLM_INTERNAL_USER_MESSAGE,
                error_code=LLM_INTERNAL_ERROR_CODE,
                reason_code=LLM_INTERNAL_ERROR_CODE,
                error_class=error_class,
            ),
            500,
        )
