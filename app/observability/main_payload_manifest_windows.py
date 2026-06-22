from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from observability.main_payload_manifest_common import (
    STATUS_ERROR,
    STATUS_NOT_AVAILABLE,
    STATUS_NOT_SELECTED,
    STATUS_OK,
    count_from_sequence,
    mapping,
    safe_int,
    safe_status,
    safe_str,
)
from observability.main_payload_manifest_messages import content_shape, safe_role


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


def _window_base(
    *,
    status: str,
    source: str,
    origin_stage: str,
    reason_code: str = "",
    selected: bool = False,
    enabled: bool | None = None,
) -> dict[str, Any]:
    payload = {
        "status": safe_status(status, fallback=STATUS_NOT_AVAILABLE),
        "reason_code": safe_str(reason_code),
        "source": safe_str(source),
        "origin_stage": safe_str(origin_stage),
        "selected": bool(selected),
        "raw_content_included": False,
    }
    if enabled is not None:
        payload["enabled"] = bool(enabled)
    return payload


def _selected_window(
    *,
    count: int,
    source: str,
    origin_stage: str,
    reason_absent: str,
    enabled: bool | None = None,
) -> dict[str, Any]:
    selected = count > 0
    return _window_base(
        status=STATUS_OK if selected else STATUS_NOT_SELECTED,
        reason_code="" if selected else reason_absent,
        selected=selected,
        enabled=enabled,
        source=source,
        origin_stage=origin_stage,
    )


def _messages(value: Any) -> tuple[Mapping[str, Any], ...]:
    return tuple(item for item in _sequence(value) if isinstance(item, Mapping))


def _message_count_by_role(messages: Sequence[Mapping[str, Any]], role: str) -> int:
    return sum(1 for message in messages if safe_role(message.get("role")) == role)


def _messages_content_chars(messages: Sequence[Mapping[str, Any]]) -> int:
    return sum(safe_int(content_shape(message.get("content")).get("content_chars")) for message in messages)


def _turn_status_count(turns: Sequence[Mapping[str, Any]], status: str) -> int:
    return sum(1 for turn in turns if safe_str(turn.get("turn_status")) == status)


def _memory_content_chars(memory_traces: Sequence[Any] | None) -> int:
    total = 0
    for trace in _sequence(memory_traces):
        if isinstance(trace, Mapping):
            total += len(str(trace.get("content") or trace.get("text") or ""))
        else:
            total += len(str(trace or ""))
    return total


def _memory_injection_source(current_mode: str) -> tuple[str, bool]:
    mode = safe_str(current_mode) or "unknown"
    if mode == "enforced_all":
        return "arbiter_enforced", True
    if mode == "off":
        return "pre_arbiter_basket_mode_off", False
    if mode in {"shadow", "enforced_identities"}:
        return "pre_arbiter_basket_shadow", False
    return "unknown", False


def _summary_window(summary_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = mapping(summary_payload)
    summary = mapping(payload.get("summary"))
    available = safe_str(payload.get("status")) == "available" and bool(summary)
    out = _window_base(
        status=STATUS_OK if available else STATUS_NOT_SELECTED,
        reason_code="" if available else "summary_missing",
        selected=available,
        enabled=True,
        source="core.hermeneutic_node.inputs.summary_input",
        origin_stage="summary_input",
    )
    out.update(
        {
            "summary_present": available,
            "content_chars": len(str(summary.get("content") or "")) if available else 0,
            "period_start_present": bool(safe_str(summary.get("start_ts"))),
            "period_end_present": bool(safe_str(summary.get("end_ts"))),
            "voice_continuity_status": STATUS_NOT_AVAILABLE,
            "voice_continuity_reason_code": "summary_style_not_scored",
        }
    )
    return out


def _memory_window(
    *,
    current_mode: str | None,
    memory_retrieved: Mapping[str, Any] | None,
    memory_arbitration: Mapping[str, Any] | None,
    memory_traces: Sequence[Any] | None,
    context_hints: Sequence[Any] | None,
) -> dict[str, Any]:
    retrieved = mapping(memory_retrieved)
    arbitration = mapping(memory_arbitration)
    prompt_injected_count = count_from_sequence(memory_traces)
    context_hint_count = count_from_sequence(context_hints)
    retrieved_count = safe_int(retrieved.get("retrieved_count"))
    arbitration_decisions = safe_int(arbitration.get("decisions_count"))
    retrieval_status = safe_str(retrieved.get("status")) or "missing"
    status = STATUS_ERROR if retrieval_status == STATUS_ERROR else STATUS_OK if prompt_injected_count else STATUS_NOT_SELECTED
    reason_code = ""
    if status == STATUS_NOT_SELECTED:
        reason_code = safe_str(retrieved.get("reason_code")) or "memory_empty"
    elif status == STATUS_ERROR:
        reason_code = safe_str(retrieved.get("reason_code")) or "retrieve_error"
    injection_source, arbiter_controls_injection = _memory_injection_source(safe_str(current_mode))
    out = _window_base(
        status=status,
        reason_code=reason_code,
        selected=bool(prompt_injected_count),
        enabled=True,
        source="core.chat_memory_flow.prepare_memory_context",
        origin_stage="memory_context",
    )
    out.update(
        {
            "current_mode": safe_str(current_mode) or "unknown",
            "retrieval_status": retrieval_status,
            "retrieval_reason_code": safe_str(retrieved.get("reason_code")),
            "top_k_requested": safe_int(retrieved.get("top_k_requested")),
            "retrieved_count": retrieved_count,
            "basket_candidates_count": safe_int(arbitration.get("basket_candidates_count")),
            "arbiter_decisions_count": arbitration_decisions,
            "arbiter_kept_count": safe_int(arbitration.get("kept_count")),
            "arbiter_rejected_count": safe_int(arbitration.get("rejected_count")),
            "arbiter_observed_count": arbitration_decisions,
            "prompt_injected_count": prompt_injected_count,
            "context_hint_count": context_hint_count,
            "injection_source": injection_source,
            "arbiter_controls_injection": arbiter_controls_injection,
            "content_chars": _memory_content_chars(memory_traces),
        }
    )
    return out


def _hermeneutic_node_window(
    *,
    hermeneutic_node_runtime: Mapping[str, Any] | None,
    hermeneutic_judgment_block: str | None,
) -> dict[str, Any]:
    runtime = mapping(hermeneutic_node_runtime)
    primary_present = isinstance(runtime.get("primary_payload"), Mapping)
    validated_present = runtime.get("validated_result") is not None
    judgment_block_present = bool(safe_str(hermeneutic_judgment_block))
    selected = primary_present or validated_present or judgment_block_present
    out = _window_base(
        status=STATUS_OK if selected else STATUS_NOT_SELECTED,
        reason_code="" if selected else "hermeneutic_node_not_injected",
        selected=selected,
        enabled=True,
        source="core.chat_service._run_hermeneutic_node_insertion_point",
        origin_stage="hermeneutic_node_runtime",
    )
    out.update(
        {
            "primary_payload_present": primary_present,
            "validated_result_present": validated_present,
            "judgment_block_present": judgment_block_present,
            "judgment_block_chars": len(str(hermeneutic_judgment_block or "")),
        }
    )
    return out


def _identity_staging_window() -> dict[str, Any]:
    out = _window_base(
        status=STATUS_NOT_AVAILABLE,
        reason_code="staging_runs_after_assistant_turn",
        selected=False,
        enabled=True,
        source="memory.memory_identity_periodic_agent",
        origin_stage="post_response_identity_runtime",
    )
    out.update(
        {
            "staging_scope": "conversation_scoped",
            "canonization_stage": "post_response",
            "canonized_into_prompt": False,
        }
    )
    return out


def _prompt_final_window(
    *,
    messages: Sequence[Mapping[str, Any]],
    estimated_tokens: int | None,
) -> dict[str, Any]:
    manifest_messages = [message for message in messages if isinstance(message, Mapping)]
    out = _selected_window(
        count=len(manifest_messages),
        source="core.chat_service",
        origin_stage="final_prompt_after_late_injections",
        reason_absent="prompt_messages_empty",
    )
    out.update(
        {
            "message_count": len(manifest_messages),
            "provider_role_sequence": [safe_role(message.get("role")) for message in manifest_messages],
            "content_chars": _messages_content_chars(manifest_messages),
            "estimated_tokens": estimated_tokens,
        }
    )
    return out


def build_context_windows(
    *,
    messages: Sequence[Mapping[str, Any]],
    conversation: Mapping[str, Any] | None,
    recent_context_payload: Mapping[str, Any] | None,
    recent_window_payload: Mapping[str, Any] | None,
    summary_payload: Mapping[str, Any] | None,
    current_mode: str | None,
    memory_retrieved: Mapping[str, Any] | None,
    memory_arbitration: Mapping[str, Any] | None,
    memory_traces: Sequence[Any] | None,
    context_hints: Sequence[Any] | None,
    hermeneutic_node_runtime: Mapping[str, Any] | None,
    hermeneutic_judgment_block: str | None,
    biblio_result: Any,
    agenda_result: Any,
    biblio_recent_dialogue: Sequence[Any] | None,
    agenda_recent_dialogue: Sequence[Any] | None,
    runtime_main_model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
    prompt_estimated_tokens: int | None = None,
) -> dict[str, Any]:
    manifest_messages = [message for message in messages if isinstance(message, Mapping)]
    conversation_messages = _messages(mapping(conversation).get("messages"))
    recent_context_messages = _messages(mapping(recent_context_payload).get("messages"))
    recent_window = mapping(recent_window_payload)
    recent_turns = _messages(recent_window.get("turns"))
    biblio_recent = _messages(biblio_recent_dialogue)
    agenda_recent = _messages(agenda_recent_dialogue)

    conversation_window = _selected_window(
        count=len(conversation_messages),
        source="core.conversations_store",
        origin_stage="conversation_history",
        reason_absent="conversation_history_empty",
    )
    conversation_window.update(
        {
            "message_count": len(conversation_messages),
            "user_message_count": _message_count_by_role(conversation_messages, "user"),
            "assistant_message_count": _message_count_by_role(conversation_messages, "assistant"),
            "content_chars": _messages_content_chars(conversation_messages),
        }
    )

    recent_context_window = _selected_window(
        count=len(recent_context_messages),
        source="core.hermeneutic_node.inputs.recent_context_input",
        origin_stage="recent_context_input",
        reason_absent="recent_context_empty",
    )
    recent_context_window.update(
        {
            "message_count": len(recent_context_messages),
            "user_message_count": _message_count_by_role(recent_context_messages, "user"),
            "assistant_message_count": _message_count_by_role(recent_context_messages, "assistant"),
            "content_chars": _messages_content_chars(recent_context_messages),
        }
    )

    recent_window_payload_out = _selected_window(
        count=len(recent_turns),
        source="core.hermeneutic_node.inputs.recent_window_input",
        origin_stage="recent_window_input",
        reason_absent="recent_window_empty",
    )
    recent_window_payload_out.update(
        {
            "turn_count": safe_int(recent_window.get("turn_count")),
            "max_recent_turns": safe_int(recent_window.get("max_recent_turns")),
            "has_in_progress_turn": bool(recent_window.get("has_in_progress_turn")),
            "complete_turn_count": _turn_status_count(recent_turns, "complete"),
            "in_progress_turn_count": _turn_status_count(recent_turns, "in_progress"),
            "assistant_only_turn_count": _turn_status_count(recent_turns, "assistant_only"),
            "message_count": sum(count_from_sequence(turn.get("messages")) for turn in recent_turns),
            "content_chars": sum(_messages_content_chars(_messages(turn.get("messages"))) for turn in recent_turns),
        }
    )

    biblio_window = _selected_window(
        count=len(biblio_recent),
        source="biblio.chat_runtime",
        origin_stage="biblio_recent_dialogue",
        reason_absent="biblio_recent_dialogue_empty",
        enabled=bool(getattr(biblio_result, "enabled", False)),
    )
    biblio_window.update(
        {
            "message_count": len(biblio_recent),
            "max_messages": 8,
            "content_chars": _messages_content_chars(biblio_recent),
            "final_response_lock_present": bool(getattr(biblio_result, "final_response_lock", None)),
        }
    )

    agenda_window = _selected_window(
        count=len(agenda_recent),
        source="agenda.chat_runtime",
        origin_stage="agenda_recent_dialogue",
        reason_absent="agenda_recent_dialogue_empty",
        enabled=bool(getattr(agenda_result, "enabled", False)),
    )
    agenda_payload = mapping(getattr(agenda_result, "observability_payload", {}))
    agenda_window.update(
        {
            "message_count": len(agenda_recent),
            "max_messages": 8,
            "content_chars": _messages_content_chars(agenda_recent),
            "model_called": bool(agenda_payload.get("model_called")),
            "final_response_lock_present": bool(getattr(agenda_result, "final_response_lock", None)),
        }
    )

    return {
        "prompt_final": _prompt_final_window(
            messages=manifest_messages,
            estimated_tokens=prompt_estimated_tokens,
        ),
        "conversation": conversation_window,
        "recent_context": recent_context_window,
        "recent_window": recent_window_payload_out,
        "summary": _summary_window(summary_payload),
        "memory": _memory_window(
            current_mode=current_mode,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            memory_traces=memory_traces,
            context_hints=context_hints,
        ),
        "hermeneutic_node": _hermeneutic_node_window(
            hermeneutic_node_runtime=hermeneutic_node_runtime,
            hermeneutic_judgment_block=hermeneutic_judgment_block,
        ),
        "identity_staging": _identity_staging_window(),
        "biblio_recent_dialogue": biblio_window,
        "agenda_recent_dialogue": agenda_window,
    }
