from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from core import chat_stream_control


CONVERSATION_PERSIST_ERROR_CODE = (
    chat_stream_control.STREAM_ERROR_CONVERSATION_PERSIST_FAILED
)
POST_PERSISTENCE_AUX_ERROR_EVENT = 'chat_post_persistence_aux_error'


@dataclass(frozen=True, repr=False)
class AssistantPersistAttempt:
    ok: bool
    updated_at: str | None
    reason: str
    content: str = field(repr=False)
    timestamp: str | None
    meta: Mapping[str, Any] | None = field(default=None, repr=False)
    appended: bool = False


@dataclass(repr=False)
class AssistantPersistTracker:
    attempt: AssistantPersistAttempt | None = None


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


def _mark_next_persist_phase(conv_store_module: Any, phase: str) -> None:
    marker = getattr(conv_store_module, 'mark_next_persist_phase', None)
    if callable(marker):
        marker(phase)


def _persist_conversation(
    *,
    conversation: dict[str, Any],
    conv_store_module: Any,
    persist_phase: str,
    updated_at: str | None,
) -> tuple[bool, str | None, str]:
    _mark_next_persist_phase(conv_store_module, persist_phase)
    if updated_at is None:
        save_result = conv_store_module.save_conversation(conversation)
    else:
        save_result = conv_store_module.save_conversation(
            conversation,
            updated_at=updated_at,
        )
    return (
        _save_result_ok(save_result),
        _save_result_updated_at(save_result, updated_at),
        _save_result_reason(save_result),
    )


def append_and_persist_assistant(
    *,
    conversation: dict[str, Any],
    content: str,
    timestamp: str | None,
    meta: Mapping[str, Any] | None,
    persist_phase: str,
    conv_store_module: Any,
    tracker: AssistantPersistTracker | None = None,
) -> AssistantPersistAttempt:
    attempt = append_assistant_message(
        conversation=conversation,
        content=content,
        timestamp=timestamp,
        meta=meta,
        conv_store_module=conv_store_module,
        tracker=tracker,
    )
    return persist_assistant_attempt(
        conversation=conversation,
        attempt=attempt,
        persist_phase=persist_phase,
        conv_store_module=conv_store_module,
        tracker=tracker,
    )


def append_assistant_message(
    *,
    conversation: dict[str, Any],
    content: str,
    timestamp: str | None,
    meta: Mapping[str, Any] | None,
    conv_store_module: Any,
    tracker: AssistantPersistTracker | None = None,
) -> AssistantPersistAttempt:
    append_kwargs: dict[str, Any] = {}
    if timestamp is not None:
        append_kwargs['timestamp'] = timestamp
    persisted_meta: dict[str, Any] | None = None
    if meta is not None:
        persisted_meta = dict(meta)
        append_kwargs['meta'] = persisted_meta
    conv_store_module.append_message(
        conversation,
        'assistant',
        content,
        **append_kwargs,
    )
    provisional_attempt = AssistantPersistAttempt(
        ok=False,
        updated_at=timestamp,
        reason=CONVERSATION_PERSIST_ERROR_CODE,
        content=content,
        timestamp=timestamp,
        meta=persisted_meta,
        appended=True,
    )
    if tracker is not None:
        tracker.attempt = provisional_attempt
    return provisional_attempt


def persist_assistant_attempt(
    *,
    conversation: dict[str, Any],
    attempt: AssistantPersistAttempt,
    persist_phase: str,
    conv_store_module: Any,
    tracker: AssistantPersistTracker | None = None,
) -> AssistantPersistAttempt:
    ok, persisted_at, reason = _persist_conversation(
        conversation=conversation,
        conv_store_module=conv_store_module,
        persist_phase=persist_phase,
        updated_at=attempt.timestamp,
    )
    persisted_attempt = AssistantPersistAttempt(
        ok=ok,
        updated_at=persisted_at,
        reason=reason,
        content=attempt.content,
        timestamp=attempt.timestamp,
        meta=attempt.meta,
        appended=attempt.appended,
    )
    if tracker is not None:
        tracker.attempt = persisted_attempt
    return persisted_attempt


def persist_user_turn_after_error(
    *,
    conversation: dict[str, Any],
    conv_store_module: Any,
    updated_at: str | None = None,
) -> AssistantPersistAttempt:
    ok, persisted_at, reason = _persist_conversation(
        conversation=conversation,
        conv_store_module=conv_store_module,
        persist_phase='user_turn',
        updated_at=updated_at,
    )
    return AssistantPersistAttempt(
        ok=ok,
        updated_at=persisted_at,
        reason=reason,
        content='',
        timestamp=updated_at,
        appended=False,
    )


def rollback_assistant_attempt(
    conversation: dict[str, Any],
    attempt: AssistantPersistAttempt | None,
) -> None:
    if attempt is None or not attempt.appended:
        return
    messages = conversation.get('messages')
    if not isinstance(messages, list) or not messages:
        return
    last_message = messages[-1]
    if not isinstance(last_message, dict):
        return
    last_meta = last_message.get('meta')
    meta_matches = last_meta == attempt.meta if attempt.meta is not None else last_meta is None
    if (
        str(last_message.get('role') or '') == 'assistant'
        and str(last_message.get('content') or '') == attempt.content
        and str(last_message.get('timestamp') or '') == str(attempt.timestamp or '')
        and meta_matches
    ):
        messages.pop()


def _exception_class(exc: BaseException) -> str:
    name = str(exc.__class__.__name__ or '').strip()
    return name if name.replace('_', '').isalnum() else 'Exception'


def _latest_completed_identity_pair(
    messages: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
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


def run_chat_post_persistence_effects(
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
        completed_turn_pair = _latest_completed_identity_pair(
            conversation.get('messages', [])
        )
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
