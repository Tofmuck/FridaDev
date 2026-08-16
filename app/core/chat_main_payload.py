from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping

from biblio import chat_runtime as biblio_chat_runtime
from core import active_document_prompt_lane
from core import adobe_docs_prompt_lane
from core import chat_prompt_context
from core import continuity_capsule
from core import workspace_folder_notes_prompt_lane
from core.chat_agent_lane_orchestration import (
    _emit_adobe_prompt_lane_observability,
    _emit_workspace_folder_notes_prompt_observability,
    resolve_agent_lane_assistant_output,
)
from observability import active_documents_observability
from observability import chat_turn_logger
from observability import main_payload_manifest


@dataclass(frozen=True)
class PreparedMainPayload:
    prompt_messages: list[dict[str, Any]]
    assistant_response_override: Any
    assistant_response_meta: Mapping[str, Any] | None
    assistant_response_envelope: Mapping[str, Any]
    web_context_injected_to_main_model: bool


def prepare_main_payload(
    *,
    conversation: dict[str, Any],
    user_msg: str,
    runtime_main_model: str,
    now_iso_value: str,
    memory_traces: list[Any],
    context_hints: list[Any],
    web_runtime_payload: Mapping[str, Any],
    web_search_module: Any,
    admin_logs_module: Any,
    document_prompt_read: Any,
    workspace_notes_read: Any,
    biblio_result: Any,
    agenda_result: Any,
    adobe_request: Any,
    adobe_context: Any,
    validated_result: Any,
    assistant_output_policy: Any,
    hermeneutic_node_runtime: Mapping[str, Any],
    hermeneutic_judgment_block: str,
    biblio_recent_dialogue: Any,
    agenda_recent_dialogue: Any,
    summary_payload: Mapping[str, Any],
    identity_payload: Mapping[str, Any],
    recent_context_payload: Mapping[str, Any],
    recent_window_payload: Mapping[str, Any],
    current_mode: str,
    memory_retrieved: Any,
    memory_arbitration: Any,
    temperature: float,
    top_p: float,
    max_tokens: int,
    stream_req: bool,
    config_module: Any,
    count_tokens_func: Callable[[Any, str], int],
    active_document_prompt_max_tokens: int,
    record_active_document_prompt_decisions_func: Callable[..., None],
    workspace_file_selections_module: Any,
    logger: Any,
    conv_store_module: Any,
) -> PreparedMainPayload:
    prompt_messages = conv_store_module.build_prompt_messages(
        conversation,
        runtime_main_model,
        now=now_iso_value,
        memory_traces=memory_traces or None,
        context_hints=context_hints or None,
    )
    payload_message_sources: dict[int, dict[str, Any]] = {}

    web_context_injected_to_main_model = False
    if str(web_runtime_payload.get('activation_mode') or '') in {'manual', 'auto'}:
        web_injection_result = chat_prompt_context.inject_web_context(
            prompt_messages,
            user_msg=user_msg,
            conversation_id=conversation['id'],
            web_search_module=web_search_module,
            admin_logs_module=admin_logs_module,
            web_context_payload=web_runtime_payload,
        )
        web_context_injected_to_main_model = bool(
            web_injection_result.get('main_prompt_context_injected')
        )
    notes_before_refs = main_payload_manifest.capture_message_refs(prompt_messages)
    workspace_notes_lane = workspace_folder_notes_prompt_lane.inject_workspace_folder_notes_prompt_lane(
        prompt_messages,
        workspace_notes_read.note_reads,
        read_status=workspace_notes_read.status,
        read_reason_code=workspace_notes_read.reason_code,
        requested_count=workspace_notes_read.requested_count,
        invalid_requested_count=workspace_notes_read.invalid_requested_count,
        over_limit_count=workspace_notes_read.over_limit_count,
    )
    payload_message_sources.update(
        main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            notes_before_refs,
            logical_roles=('note_lane',),
            origin='core.workspace_folder_notes_prompt_lane',
            origin_stage='late_note_lane',
            content_kind='tool_lane_context',
        )
    )
    _emit_workspace_folder_notes_prompt_observability(workspace_notes_lane)
    documents_before_refs = main_payload_manifest.capture_message_refs(prompt_messages)
    active_document_lane = active_document_prompt_lane.inject_active_document_prompt_lane(
        prompt_messages,
        document_prompt_read.documents,
        model=runtime_main_model,
        count_tokens_func=count_tokens_func,
        max_tokens=active_document_prompt_max_tokens,
        read_status=document_prompt_read.status,
        read_reason_code=document_prompt_read.reason_code,
    )
    payload_message_sources.update(
        main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            documents_before_refs,
            logical_roles=('document_lane',),
            origin='core.active_document_prompt_lane',
            origin_stage='late_document_lane',
            content_kind='tool_lane_context',
        )
    )
    record_active_document_prompt_decisions_func(
        conversation=conversation,
        lane=active_document_lane,
        turn_id=chat_turn_logger.current_turn_id(),
        workspace_file_selections_module=workspace_file_selections_module,
        logger=logger,
    )
    active_documents_observability.emit_prompt_decision_event(
        active_document_lane,
        chat_turn_logger_module=chat_turn_logger,
    )
    biblio_before_refs = main_payload_manifest.capture_message_refs(prompt_messages)
    biblio_chat_runtime.inject_biblio_prompt_lane(
        prompt_messages,
        biblio_result,
    )
    payload_message_sources.update(
        main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            biblio_before_refs,
            logical_roles=('biblio_lane',),
            origin='biblio.chat_runtime',
            origin_stage='late_biblio_lane',
            content_kind='tool_lane_context',
        )
    )
    agent_lane_assistant_output = resolve_agent_lane_assistant_output(
        biblio_result=biblio_result,
        agenda_result=agenda_result,
        validated_result=validated_result,
    )
    assistant_response_override = agent_lane_assistant_output.assistant_response_override
    biblio_assistant_response_meta = agent_lane_assistant_output.assistant_response_meta
    biblio_assistant_response_envelope = agent_lane_assistant_output.assistant_response_envelope
    adobe_before_refs = main_payload_manifest.capture_message_refs(prompt_messages)
    adobe_lane = adobe_docs_prompt_lane.inject_adobe_prompt_lane(
        prompt_messages,
        adobe_context,
    )
    payload_message_sources.update(
        main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            adobe_before_refs,
            logical_roles=('adobe_lane',),
            origin='core.adobe_docs_prompt_lane',
            origin_stage='late_adobe_lane',
            content_kind='tool_lane_context',
        )
    )
    if adobe_request.active:
        _emit_adobe_prompt_lane_observability(adobe_lane)
    continuity_capsule_result = continuity_capsule.resolve_continuity_capsule(
        config_module=config_module,
        final_response_lock_present=assistant_response_override is not None,
    )
    continuity_before_refs = main_payload_manifest.capture_message_refs(prompt_messages)
    continuity_capsule.inject_continuity_capsule(prompt_messages, continuity_capsule_result)
    payload_message_sources.update(
        main_payload_manifest.message_sources_for_new_messages(
            prompt_messages,
            continuity_before_refs,
            logical_roles=(continuity_capsule.LOGICAL_ROLE,),
            origin=continuity_capsule.ORIGIN,
            origin_stage=continuity_capsule.ORIGIN_STAGE,
            content_kind=continuity_capsule.CONTENT_KIND,
        )
    )
    payload_manifest = main_payload_manifest.build_main_payload_manifest(
        conversation=conversation,
        prompt_messages=prompt_messages,
        runtime_main_model=runtime_main_model,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        stream_req=stream_req,
        assistant_output_policy=assistant_output_policy,
        assistant_response_override=assistant_response_override,
        turn_id=chat_turn_logger.current_turn_id(),
        summary_payload=summary_payload,
        identity_payload=identity_payload,
        recent_context_payload=recent_context_payload,
        recent_window_payload=recent_window_payload,
        current_mode=current_mode,
        memory_retrieved=memory_retrieved,
        memory_arbitration=memory_arbitration,
        memory_traces=memory_traces,
        context_hints=context_hints,
        web_runtime_payload=web_runtime_payload,
        workspace_notes_lane=workspace_notes_lane,
        active_document_lane=active_document_lane,
        biblio_result=biblio_result,
        agenda_result=agenda_result,
        adobe_context=adobe_context,
        adobe_lane=adobe_lane,
        hermeneutic_node_runtime=hermeneutic_node_runtime,
        hermeneutic_judgment_block=hermeneutic_judgment_block,
        biblio_recent_dialogue=biblio_recent_dialogue,
        agenda_recent_dialogue=agenda_recent_dialogue,
        message_sources=payload_message_sources,
        count_tokens_func=count_tokens_func,
        prompt_soft_token_limit=getattr(config_module, 'MAX_TOKENS', None),
        continuity_capsule_result=continuity_capsule_result,
    )
    main_payload_manifest.emit_main_payload_manifest(
        payload_manifest,
        chat_turn_logger_module=chat_turn_logger,
    )
    return PreparedMainPayload(
        prompt_messages=prompt_messages,
        assistant_response_override=assistant_response_override,
        assistant_response_meta=biblio_assistant_response_meta,
        assistant_response_envelope=biblio_assistant_response_envelope,
        web_context_injected_to_main_model=web_context_injected_to_main_model,
    )
