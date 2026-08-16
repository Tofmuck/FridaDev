from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from agenda import chat_runtime as agenda_chat_runtime
from biblio import chat_runtime as biblio_chat_runtime
from biblio import observability as biblio_observability
from core import assistant_turn_state
from core import chat_llm_flow
from observability import chat_turn_logger


_DIALOGIC_PRESENCE_TEXT = '...'


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _emit_adobe_docs_observability(
    *,
    conversation_id: str,
    adobe_context: Any,
    admin_logs_module: Any,
) -> None:
    payload_builder = getattr(adobe_context, 'as_content_free_dict', None)
    payload = payload_builder() if callable(payload_builder) else {}
    if not isinstance(payload, Mapping):
        payload = {}
    status = str(payload.get('status') or getattr(adobe_context, 'status', '') or 'error')
    event_status = 'error' if status == 'error' else 'ok'
    reason_codes = payload.get('reason_codes') if isinstance(payload.get('reason_codes'), list) else []
    reason_code = str(reason_codes[0]) if reason_codes else ''
    chat_turn_logger.set_state('adobe_docs', dict(payload))
    chat_turn_logger.emit(
        'adobe_docs',
        status=event_status,
        reason_code=reason_code or None,
        payload=dict(payload),
    )
    try:
        admin_logs_module.log_event(
            'adobe_docs',
            conversation_id=conversation_id,
            **dict(payload),
        )
    except Exception:
        return


def _emit_adobe_prompt_lane_observability(lane: Any) -> None:
    payload_builder = getattr(lane, 'as_content_free_dict', None)
    payload = payload_builder() if callable(payload_builder) else {}
    if not isinstance(payload, Mapping):
        payload = {}
    chat_turn_logger.set_state('adobe_prompt_lane', dict(payload))
    status = str(payload.get('status') or 'not_requested')
    chat_turn_logger.emit(
        'adobe_prompt_lane',
        status='error' if status == 'error' else 'ok',
        payload=dict(payload),
    )


def _emit_biblio_observability(result: Any) -> None:
    payload = getattr(result, 'observability_payload', None)
    if not isinstance(payload, Mapping):
        return
    clean_payload = dict(payload)
    chat_turn_logger.set_state('biblio', clean_payload)
    biblio_observability.emit_biblio_event(
        clean_payload,
        chat_turn_logger_module=chat_turn_logger,
    )


def _emit_agenda_observability(result: Any) -> None:
    payload = getattr(result, 'observability_payload', None)
    if not isinstance(payload, Mapping):
        return
    clean_payload = dict(payload)
    chat_turn_logger.set_state('agenda', clean_payload)
    chat_turn_logger.emit(
        'agenda',
        status=agenda_chat_runtime.observability_status_for_payload(clean_payload),
        reason_code=str(clean_payload.get('reason_code') or '') or None,
        payload=clean_payload,
    )


def _emit_workspace_folder_notes_prompt_observability(lane: Any) -> None:
    payload_builder = getattr(lane, 'as_content_free_dict', None)
    payload = payload_builder() if callable(payload_builder) else {}
    if not isinstance(payload, Mapping):
        payload = {}
    if not payload.get('requested_count') and not payload.get('invalid_requested_count'):
        return
    clean_payload = dict(payload)
    status = str(clean_payload.get('status') or 'empty')
    chat_turn_logger.set_state('workspace_folder_notes_prompt_lane', clean_payload)
    chat_turn_logger.emit(
        'workspace_folder_notes_prompt_lane',
        status='error' if status == 'error' else 'ok',
        reason_code=str(clean_payload.get('reason_code') or '') or None,
        payload=clean_payload,
    )


def _biblio_assistant_response_override(result: Any) -> chat_llm_flow.AssistantResponseOverride | None:
    lock_reader = getattr(biblio_chat_runtime, 'final_response_lock_for_result', None)
    lock = lock_reader(result) if callable(lock_reader) else getattr(result, 'final_response_lock', None)
    if lock is None or not bool(getattr(lock, 'ok', False)):
        return None
    content = str(getattr(lock, 'content', '') or '')
    if not content:
        return None
    meta_builder = getattr(lock, 'to_message_meta', None)
    observability_builder = getattr(lock, 'to_observability', None)
    return chat_llm_flow.AssistantResponseOverride(
        content=content,
        source=str(getattr(lock, 'source', '') or ''),
        reason_code=str(getattr(lock, 'reason_code', '') or ''),
        meta=meta_builder() if callable(meta_builder) else None,
        observability=observability_builder() if callable(observability_builder) else {},
    )


def _agenda_assistant_response_override(result: Any) -> chat_llm_flow.AssistantResponseOverride | None:
    lock_reader = getattr(agenda_chat_runtime, 'final_response_lock_for_result', None)
    lock = lock_reader(result) if callable(lock_reader) else getattr(result, 'final_response_lock', None)
    if lock is None or not bool(getattr(lock, 'ok', False)):
        return None
    content = str(getattr(lock, 'content', '') or '')
    if not content:
        return None
    meta_builder = getattr(lock, 'to_message_meta', None)
    observability_builder = getattr(lock, 'to_observability', None)
    return chat_llm_flow.AssistantResponseOverride(
        content=content,
        source=str(getattr(lock, 'source', '') or ''),
        reason_code=str(getattr(lock, 'reason_code', '') or ''),
        meta=meta_builder() if callable(meta_builder) else None,
        observability=observability_builder() if callable(observability_builder) else {},
    )


def _hermeneutic_presence_assistant_response_override(
    result: Any,
) -> chat_llm_flow.AssistantResponseOverride | None:
    if _text(getattr(result, 'status', '')) != 'ok':
        return None
    validated_output = _mapping(getattr(result, 'validated_output', None))
    if _text(validated_output.get('final_judgment_posture')) != 'answer':
        return None
    if _text(validated_output.get('final_output_regime')) != 'presence':
        return None
    return chat_llm_flow.AssistantResponseOverride(
        content=_DIALOGIC_PRESENCE_TEXT,
        source='hermeneutic_presence',
        reason_code='validated_dialogic_presence',
        meta=assistant_turn_state.build_dialogic_presence_assistant_turn_meta(),
    )


def _biblio_assistant_response_meta(result: Any) -> dict[str, Any] | None:
    meta_builder = getattr(biblio_chat_runtime, 'assistant_response_meta_for_result', None)
    meta = meta_builder(result) if callable(meta_builder) else None
    return dict(meta) if isinstance(meta, Mapping) else None


def _biblio_assistant_response_envelope(result: Any) -> dict[str, str]:
    envelope_builder = getattr(biblio_chat_runtime, 'assistant_response_envelope_for_result', None)
    envelope = envelope_builder(result) if callable(envelope_builder) else None
    if not isinstance(envelope, Mapping):
        return {}
    return {
        'surface_intro': str(envelope.get('surface_intro') or ''),
        'surface_outro': str(envelope.get('surface_outro') or ''),
    }


@dataclass(frozen=True)
class AgentLaneAssistantOutput:
    assistant_response_override: chat_llm_flow.AssistantResponseOverride | None
    assistant_response_meta: dict[str, Any] | None
    assistant_response_envelope: dict[str, str]


def resolve_agent_lane_assistant_output(
    *,
    biblio_result: Any,
    agenda_result: Any,
    validated_result: Any,
) -> AgentLaneAssistantOutput:
    biblio_override = _biblio_assistant_response_override(biblio_result)
    agenda_override = _agenda_assistant_response_override(agenda_result)
    presence_override = _hermeneutic_presence_assistant_response_override(validated_result)
    biblio_meta = _biblio_assistant_response_meta(biblio_result)
    biblio_envelope = _biblio_assistant_response_envelope(biblio_result)
    return AgentLaneAssistantOutput(
        assistant_response_override=agenda_override or biblio_override or presence_override,
        assistant_response_meta=biblio_meta,
        assistant_response_envelope=biblio_envelope,
    )
