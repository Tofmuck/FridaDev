from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from core import assistant_turn_state
from core import assistant_output_contract
from core import chat_stream_control
from core.chat_assistant_finalization import (
    AssistantPersistAttempt,
    AssistantPersistTracker,
    append_assistant_message,
    append_and_persist_assistant,
    persist_assistant_attempt,
    persist_user_turn_after_error,
    rollback_assistant_attempt,
    run_chat_post_persistence_effects,
)
from core.chat_llm_provider_exchange import (
    ProviderStreamState,
    emit_provider_response_observability,
    iter_stream_provider_content,
    prepare_provider_call,
    read_non_stream_provider_response,
    require_main_model_secret,
)


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


def _persistence_failure_payload(result: Any) -> dict[str, Any]:
    return {
        'ok': False,
        'error': 'sauvegarde conversationnelle impossible',
        'reason': str(getattr(result, 'reason', '') or '').strip()
        or CONVERSATION_PERSIST_ERROR_CODE,
    }


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
    assistant_final_meta = assistant_turn_state.merge_assistant_message_meta(
        override.meta,
        assistant_turn_state.build_assistant_runtime_provenance_meta(
            response_origin=assistant_turn_state.ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK,
            web_context_injected_to_main_model=False,
        ),
    )

    def persist_and_record() -> tuple[bool, str | None, dict[str, Any] | None]:
        updated_at = now_iso_func()
        attempt = append_and_persist_assistant(
            conversation=conversation,
            content=text,
            timestamp=updated_at,
            meta=assistant_final_meta,
            persist_phase='assistant_final',
            conv_store_module=conv_store_module,
        )
        if not attempt.ok:
            rollback_assistant_attempt(conversation, attempt)
            return False, updated_at, _persistence_failure_payload(attempt)
        run_chat_post_persistence_effects(
            conversation=conversation,
            assistant_text=text,
            assistant_timestamp=attempt.updated_at,
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
        return True, attempt.updated_at, None

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
    web_context_injected_to_main_model: bool = False,
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

    assistant_final_meta = assistant_turn_state.merge_assistant_message_meta(
        assistant_response_meta,
        assistant_turn_state.build_assistant_runtime_provenance_meta(
            response_origin=assistant_turn_state.ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_MAIN_MODEL,
            web_context_injected_to_main_model=web_context_injected_to_main_model,
        ),
    )

    try:
        require_main_model_secret(runtime_settings_module=runtime_settings_module)
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

    prepared_call = prepare_provider_call(
        conversation=conversation,
        prompt_messages=prompt_messages,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream_req=stream_req,
        llm_module=llm_module,
        admin_logs_module=admin_logs_module,
    )

    try:
        if not stream_req:
            raw_text = read_non_stream_provider_response(
                prepared_call=prepared_call,
                conversation=conversation,
                prompt_messages=prompt_messages,
                requests_module=requests_module,
                llm_module=llm_module,
                admin_logs_module=admin_logs_module,
                config_module=config_module,
                logger=logger,
            )
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
            attempt = append_and_persist_assistant(
                conversation=conversation,
                content=text,
                timestamp=updated_at,
                meta=assistant_final_meta,
                persist_phase='assistant_final',
                conv_store_module=conv_store_module,
            )
            if not attempt.ok:
                return _json_result(_persistence_failure_payload(attempt), 503)
            run_chat_post_persistence_effects(
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
            provider_state = ProviderStreamState()
            stream_visible_output = ''
            terminal_final_text: str | None = None
            terminal_event = chat_stream_control.STREAM_TERMINAL_DONE
            terminal_error_code: str | None = None
            assistant_tracker = AssistantPersistTracker()
            assistant_has_envelope = bool(
                str(assistant_response_intro or "").strip() or str(assistant_response_outro or "").strip()
            )
            buffer_stream_output = assistant_output_contract.should_buffer_plain_text_stream(
                assistant_output_policy,
            ) or assistant_has_envelope

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

            try:
                for sanitized_content in iter_stream_provider_content(
                    prepared_call=prepared_call,
                    state=provider_state,
                    requests_module=requests_module,
                    llm_module=llm_module,
                    config_module=config_module,
                ):
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
                    model=prepared_call.call_model,
                    error_class=error_class,
                    error_code=terminal_error_code,
                    reason_code=LLM_UPSTREAM_REASON_CODE,
                )
            assistant_text = llm_module.sanitize_provider_text(''.join(assistant_chunks)).strip()
            final_updated_at: str | None = None
            persisted_updated_at: str | None = None
            persistence_ok = False
            try:
                emit_provider_response_observability(
                    prepared_call=prepared_call,
                    state=provider_state,
                    conversation=conversation,
                    llm_module=llm_module,
                    admin_logs_module=admin_logs_module,
                    logger=logger,
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
                        assistant_tracker.attempt = append_and_persist_assistant(
                            conversation=conversation,
                            content=assistant_text,
                            timestamp=final_updated_at,
                            meta=assistant_final_meta,
                            persist_phase='assistant_final',
                            conv_store_module=conv_store_module,
                            tracker=assistant_tracker,
                        )
                    else:
                        assistant_tracker.attempt = persist_user_turn_after_error(
                            conversation=conversation,
                            conv_store_module=conv_store_module,
                            updated_at=final_updated_at,
                        )
                elif terminal_event == chat_stream_control.STREAM_TERMINAL_ERROR:
                    assistant_tracker.attempt = append_and_persist_assistant(
                        conversation=conversation,
                        content='',
                        timestamp=final_updated_at,
                        meta=assistant_turn_state.build_interrupted_assistant_turn_meta(
                            terminal_error_code or 'stream_protocol_error',
                        ),
                        persist_phase='assistant_interrupted',
                        conv_store_module=conv_store_module,
                        tracker=assistant_tracker,
                    )
                if assistant_tracker.attempt is not None and assistant_tracker.attempt.ok:
                    persisted_updated_at = assistant_tracker.attempt.updated_at
                    persistence_ok = True
                else:
                    rollback_assistant_attempt(conversation, assistant_tracker.attempt)
                    terminal_event = chat_stream_control.STREAM_TERMINAL_ERROR
                    terminal_error_code = CONVERSATION_PERSIST_ERROR_CODE
                    final_updated_at = None
                    terminal_final_text = None
                    persist_reason = (
                        assistant_tracker.attempt.reason
                        if assistant_tracker.attempt is not None
                        else CONVERSATION_PERSIST_ERROR_CODE
                    )
                    logger.error(
                        'llm_stream_finalize_persist_error id=%s reason=%s',
                        conversation['id'],
                        persist_reason,
                    )
                    admin_logs_module.log_event(
                        'llm_stream_finalize_persist_error',
                        level='ERROR',
                        conversation_id=conversation['id'],
                        model=prepared_call.call_model,
                        error_code=terminal_error_code,
                        reason=persist_reason,
                    )
            except Exception as exc:
                rollback_assistant_attempt(conversation, assistant_tracker.attempt)
                assistant_tracker.attempt = None
                terminal_final_text = None
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
                    model=prepared_call.call_model,
                    error_class=error_class,
                    error_code=terminal_error_code,
                    reason_code='llm_stream_finalize_error',
                )
                if final_updated_at is None:
                    try:
                        final_updated_at = now_iso_func()
                    except Exception:
                        final_updated_at = None
                assistant_tracker.attempt = append_assistant_message(
                    conversation=conversation,
                    content='',
                    timestamp=final_updated_at,
                    meta=assistant_turn_state.build_interrupted_assistant_turn_meta(
                        terminal_error_code,
                    ),
                    conv_store_module=conv_store_module,
                    tracker=assistant_tracker,
                )
                try:
                    assistant_tracker.attempt = persist_assistant_attempt(
                        conversation=conversation,
                        attempt=assistant_tracker.attempt,
                        persist_phase='assistant_interrupted',
                        conv_store_module=conv_store_module,
                        tracker=assistant_tracker,
                    )
                    if assistant_tracker.attempt.ok:
                        persisted_updated_at = assistant_tracker.attempt.updated_at
                        persistence_ok = True
                    else:
                        rollback_assistant_attempt(conversation, assistant_tracker.attempt)
                        terminal_error_code = CONVERSATION_PERSIST_ERROR_CODE
                        final_updated_at = None
                        logger.error(
                            'llm_stream_finalize_persist_error id=%s reason=%s',
                            conversation['id'],
                            assistant_tracker.attempt.reason,
                        )
                        admin_logs_module.log_event(
                            'llm_stream_finalize_persist_error',
                            level='ERROR',
                            conversation_id=conversation['id'],
                            model=prepared_call.call_model,
                            error_code=terminal_error_code,
                            reason=assistant_tracker.attempt.reason,
                        )
                except Exception as persist_exc:
                    rollback_assistant_attempt(conversation, assistant_tracker.attempt)
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
                        model=prepared_call.call_model,
                        error_class=persist_error_class,
                        error_code=terminal_error_code,
                        reason_code=CONVERSATION_PERSIST_ERROR_CODE,
                    )
            if persistence_ok and terminal_event == chat_stream_control.STREAM_TERMINAL_DONE:
                completed_assistant_appended = bool(
                    assistant_tracker.attempt is not None
                    and assistant_tracker.attempt.appended
                    and assistant_tracker.attempt.ok
                )
                run_chat_post_persistence_effects(
                    conversation=conversation,
                    assistant_text=(
                        assistant_text
                        if completed_assistant_appended and assistant_text
                        else None
                    ),
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

        logger.info(
            'llm_call id=%s model=%s messages=%s stream=true',
            conversation['id'],
            prepared_call.call_model,
            len(prompt_messages),
        )
        admin_logs_module.log_event(
            'llm_call',
            conversation_id=conversation['id'],
            model=prepared_call.call_model,
            message_count=len(prompt_messages),
            stream=True,
            provider_caller='llm',
            provider_title=prepared_call.provider_title,
            **prepared_call.reasoning_observability,
        )
        return _stream_result(
            event_stream(),
            stream_headers,
        )

    except requests_module.exceptions.RequestException as exc:
        persist_user_turn_after_error(
            conversation=conversation,
            conv_store_module=conv_store_module,
        )
        error_class = _exception_class(exc)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=prepared_call.call_model,
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
        persist_user_turn_after_error(
            conversation=conversation,
            conv_store_module=conv_store_module,
        )
        error_class = _exception_class(exc)
        admin_logs_module.log_event(
            'llm_error',
            level='ERROR',
            conversation_id=conversation['id'],
            model=prepared_call.call_model,
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
