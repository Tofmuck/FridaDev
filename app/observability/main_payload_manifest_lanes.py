from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.main_payload_manifest_common import (
    STATUS_DISABLED,
    STATUS_NOT_APPLICABLE,
    STATUS_NOT_SELECTED,
    STATUS_OK,
    dedupe,
    mapping,
    safe_int,
    safe_status,
    safe_str,
)


def base_lane(
    *,
    status: str,
    reason_code: str = "",
    selected: bool = False,
    enabled: bool | None = None,
    input_count: int = 0,
    injected_count: int = 0,
    excluded_count: int = 0,
    content_chars: int = 0,
    estimated_tokens: int | None = None,
    origin: str = "",
    budget: Mapping[str, Any] | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": safe_status(status),
        "reason_code": safe_str(reason_code),
        "selected": bool(selected),
        "enabled": enabled,
        "input_count": int(input_count),
        "injected_count": int(injected_count),
        "excluded_count": int(excluded_count),
        "content_chars": int(content_chars),
        "estimated_tokens": estimated_tokens,
        "origin": safe_str(origin),
        "raw_lane_content_included": False,
    }
    if budget:
        payload["budget"] = {str(key): safe_int(value) for key, value in budget.items()}
    if extra:
        for key, value in extra.items():
            payload[str(key)] = value
    return payload


def _summary_lane(summary_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = mapping(summary_payload)
    summary = mapping(payload.get("summary"))
    available = safe_str(payload.get("status")) == "available" and bool(summary)
    return base_lane(
        status=STATUS_OK if available else STATUS_NOT_SELECTED,
        reason_code="" if available else "summary_missing",
        selected=available,
        enabled=True,
        input_count=1 if available else 0,
        injected_count=1 if available else 0,
        content_chars=len(str(summary.get("content") or "")) if available else 0,
        origin="core.conversations_prompt_window",
    )


def _identity_lanes(identity_payload: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    payload = mapping(identity_payload)
    frida = mapping(payload.get("frida"))
    user = mapping(payload.get("user"))
    static_chars = 0
    mutable_chars = 0
    static_count = 0
    mutable_count = 0
    for side in (frida, user):
        static_content = str(mapping(side.get("static")).get("content") or "")
        mutable_content = str(mapping(side.get("mutable")).get("content") or "")
        if static_content:
            static_count += 1
            static_chars += len(static_content)
        if mutable_content:
            mutable_count += 1
            mutable_chars += len(mutable_content)
    stable = base_lane(
        status=STATUS_OK if static_count else STATUS_NOT_SELECTED,
        reason_code="" if static_count else "identity_stable_empty",
        selected=bool(static_count),
        enabled=True,
        input_count=2,
        injected_count=static_count,
        content_chars=static_chars,
        origin="memory.identity_input",
    )
    mutable = base_lane(
        status=STATUS_OK if mutable_count else STATUS_NOT_SELECTED,
        reason_code="" if mutable_count else "identity_mutable_empty",
        selected=bool(mutable_count),
        enabled=True,
        input_count=2,
        injected_count=mutable_count,
        content_chars=mutable_chars,
        origin="memory.identity_input",
    )
    return stable, mutable


def identity_roles_present(lane_statuses: Mapping[str, Any]) -> dict[str, bool]:
    stable = mapping(lane_statuses.get("identity_stable"))
    mutable = mapping(lane_statuses.get("identity_mutable"))
    return {
        "identity_stable": bool(stable.get("selected")),
        "identity_mutable": bool(mutable.get("selected")),
    }


def _memory_lane(memory_traces: Sequence[Any] | None, context_hints: Sequence[Any] | None) -> dict[str, Any]:
    traces = tuple(memory_traces or ())
    hints = tuple(context_hints or ())
    trace_chars = 0
    for trace in traces:
        if isinstance(trace, Mapping):
            trace_chars += len(str(trace.get("content") or trace.get("text") or ""))
        else:
            trace_chars += len(str(trace or ""))
    return base_lane(
        status=STATUS_OK if traces else STATUS_NOT_SELECTED,
        reason_code="" if traces else "memory_empty",
        selected=bool(traces),
        enabled=True,
        input_count=len(traces),
        injected_count=1 if traces else 0,
        content_chars=trace_chars,
        origin="core.chat_memory_flow",
        extra={"context_hint_count": len(hints)},
    )


def _context_hints_lane(context_hints: Sequence[Any] | None) -> dict[str, Any]:
    hints = tuple(context_hints or ())
    return base_lane(
        status=STATUS_OK if hints else STATUS_NOT_SELECTED,
        reason_code="" if hints else "context_hints_empty",
        selected=bool(hints),
        enabled=True,
        input_count=len(hints),
        injected_count=1 if hints else 0,
        content_chars=sum(len(str(hint or "")) for hint in hints),
        origin="core.chat_memory_flow",
    )


def _web_lane(web_runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = mapping(web_runtime_payload)
    enabled = bool(payload.get("enabled", payload.get("search_enabled", False)))
    selected = safe_str(payload.get("activation_mode")).lower() in {"manual", "auto"}
    injected = bool(payload.get("context_injected") or str(payload.get("context_block") or ""))
    if selected:
        status = safe_status(payload.get("status"), fallback=STATUS_OK)
    elif not enabled:
        status = STATUS_DISABLED
    else:
        status = STATUS_NOT_SELECTED
    return base_lane(
        status=status,
        reason_code=safe_str(payload.get("reason_code")),
        selected=selected,
        enabled=enabled,
        input_count=safe_int(payload.get("results_count")),
        injected_count=1 if injected else 0,
        excluded_count=max(0, safe_int(payload.get("results_count")) - (1 if injected else 0)),
        content_chars=safe_int(payload.get("context_chars")) or len(str(payload.get("context_block") or "")),
        origin="core.chat_prompt_context",
        extra={"activation_mode": safe_str(payload.get("activation_mode")) or "off", "context_injected": injected},
    )


def _notes_lane(lane: Any) -> dict[str, Any]:
    lane_payload = lane.as_content_free_dict() if callable(getattr(lane, "as_content_free_dict", None)) else {}
    decisions = tuple(getattr(lane, "decisions", ()) or ())
    requested_count = safe_int(getattr(lane, "requested_count", 0))
    injected_count = safe_int(getattr(lane, "injected_count", 0))
    not_injected_count = safe_int(getattr(lane, "not_injected_count", 0))
    selected = bool(requested_count or decisions)
    chars = sum(
        safe_int(getattr(decision, "markdown_char_count", 0))
        for decision in decisions
        if bool(getattr(decision, "injected", False))
    )
    return base_lane(
        status=safe_status(getattr(lane, "read_status", "") or (STATUS_OK if injected_count else STATUS_NOT_SELECTED))
        if selected
        else STATUS_NOT_SELECTED,
        reason_code=safe_str(getattr(lane, "read_reason_code", "")) or ("" if selected else "notes_not_selected"),
        selected=selected,
        enabled=True,
        input_count=max(requested_count, len(decisions)),
        injected_count=injected_count,
        excluded_count=not_injected_count,
        content_chars=chars,
        origin="core.workspace_folder_notes_prompt_lane",
        budget={
            "max_notes_injected_per_turn": safe_int(lane_payload.get("max_notes_injected_per_turn")),
            "max_notes_total_chars_per_turn": safe_int(lane_payload.get("max_notes_total_chars_per_turn")),
        },
        extra={
            "invalid_requested_count": safe_int(getattr(lane, "invalid_requested_count", 0)),
            "over_limit_count": safe_int(getattr(lane, "over_limit_count", 0)),
        },
    )


def _document_lane(lane: Any) -> dict[str, Any]:
    decisions = tuple(getattr(lane, "decisions", ()) or ())
    injected_count = safe_int(getattr(lane, "injected_count", 0))
    reason_codes: list[str] = []
    media_kind_counts: dict[str, int] = {}
    for decision in decisions:
        media_kind = safe_str(getattr(decision, "media_kind", "")) or "unknown"
        media_kind_counts[media_kind] = media_kind_counts.get(media_kind, 0) + 1
        reason = safe_str(getattr(decision, "reason_code", ""))
        if reason:
            reason_codes.append(reason)
    return base_lane(
        status=safe_status(getattr(lane, "read_status", "") or (STATUS_OK if decisions else STATUS_NOT_SELECTED)),
        reason_code=safe_str(getattr(lane, "read_reason_code", "")) or ("" if decisions else "documents_not_selected"),
        selected=bool(decisions),
        enabled=True,
        input_count=len(decisions),
        injected_count=injected_count,
        excluded_count=safe_int(getattr(lane, "not_injected_count", 0)),
        content_chars=sum(
            safe_int(getattr(decision, "text_chars", 0))
            for decision in decisions
            if bool(getattr(decision, "injected", False))
        ),
        origin="core.active_document_prompt_lane",
        extra={"media_kind_counts": media_kind_counts, "exclusion_reason_codes": dedupe(reason_codes)},
    )


def _biblio_lane(result: Any) -> dict[str, Any]:
    payload = mapping(getattr(result, "observability_payload", {}))
    enabled = bool(getattr(result, "enabled", payload.get("enabled", False)))
    used = bool(getattr(result, "used", payload.get("used", False)))
    query_kind = safe_str(getattr(result, "query_kind", payload.get("query_kind")))
    prompt_lane = getattr(result, "prompt_lane", None)
    prompt_message = getattr(result, "prompt_message", None)
    decisions = tuple(getattr(prompt_lane, "decisions", ()) or ())
    passage_count = safe_int(getattr(prompt_lane, "passage_count", 0))
    selected = bool(enabled and (used or query_kind and query_kind != "not_requested" or prompt_message is not None))
    return base_lane(
        status=safe_status(payload.get("status") or ("ok" if selected else "disabled" if not enabled else "not_selected")),
        reason_code=safe_str(getattr(result, "reason_code", payload.get("reason_code"))),
        selected=selected,
        enabled=enabled,
        input_count=len(decisions) or passage_count,
        injected_count=1 if prompt_message is not None else 0,
        excluded_count=max(0, len(decisions) - passage_count) if decisions else 0,
        content_chars=safe_int(getattr(prompt_lane, "chars", 0)),
        origin="biblio.chat_runtime",
        budget={
            "max_passages": safe_int(getattr(prompt_lane, "max_passages", 0)),
            "max_total_chars": safe_int(getattr(prompt_lane, "max_total_chars", 0)),
        },
        extra={"query_kind": query_kind or "not_requested", "final_response_lock_present": bool(getattr(result, "final_response_lock", None))},
    )


def _agenda_lane(result: Any) -> dict[str, Any]:
    payload = mapping(getattr(result, "observability_payload", {}))
    enabled = bool(getattr(result, "enabled", payload.get("enabled", False)))
    used = bool(getattr(result, "used", payload.get("used", False)))
    selected = bool(enabled and (used or safe_str(payload.get("mode")) not in {"", "off"}))
    return base_lane(
        status=safe_status(getattr(result, "status", payload.get("status")) or ("disabled" if not enabled else "not_selected")),
        reason_code=safe_str(getattr(result, "reason_code", payload.get("reason_code"))),
        selected=selected,
        enabled=enabled,
        input_count=safe_int(payload.get("tool_count")),
        injected_count=0,
        content_chars=0,
        origin="agenda.chat_runtime",
        extra={
            "mode": safe_str(payload.get("mode")) or "off",
            "model_called": bool(payload.get("model_called")),
            "final_response_lock_present": bool(getattr(result, "final_response_lock", None)),
        },
    )


def _adobe_lane(lane: Any, adobe_context: Any = None) -> dict[str, Any]:
    payload = lane.as_content_free_dict() if callable(getattr(lane, "as_content_free_dict", None)) else {}
    active = bool(getattr(adobe_context, "active", False) or getattr(lane, "messages", ()))
    status_raw = safe_str(payload.get("status") or getattr(lane, "status", ""))
    status = STATUS_NOT_SELECTED if status_raw in {"", "not_requested"} else safe_status(status_raw, fallback=STATUS_OK)
    messages = tuple(getattr(lane, "messages", ()) or ())
    return base_lane(
        status=status if active else STATUS_NOT_SELECTED,
        reason_code="adobe_not_requested" if not active else "",
        selected=active,
        enabled=True,
        input_count=safe_int(payload.get("source_count")),
        injected_count=len(messages),
        content_chars=safe_int(payload.get("injected_chars")),
        origin="core.adobe_docs_prompt_lane",
        extra={
            "source_count": safe_int(payload.get("source_count")),
            "passage_count": safe_int(payload.get("passage_count")),
            "reason_codes": dedupe([str(code) for code in payload.get("reason_codes", []) or []]),
        },
    )


def _presence_lane(*, present: bool, origin: str, reason_absent: str, content_chars: int = 0) -> dict[str, Any]:
    return base_lane(
        status=STATUS_OK if present else STATUS_NOT_SELECTED,
        reason_code="" if present else reason_absent,
        selected=present,
        enabled=True,
        input_count=1 if present else 0,
        injected_count=1 if present else 0,
        content_chars=content_chars if present else 0,
        origin=origin,
    )


def build_lane_statuses(
    *,
    summary_payload: Mapping[str, Any] | None,
    identity_payload: Mapping[str, Any] | None,
    memory_traces: Sequence[Any] | None,
    context_hints: Sequence[Any] | None,
    web_runtime_payload: Mapping[str, Any] | None,
    workspace_notes_lane: Any,
    active_document_lane: Any,
    biblio_result: Any,
    agenda_result: Any,
    adobe_context: Any,
    adobe_lane: Any,
    hermeneutic_judgment_block: str | None,
    assistant_output_policy: Any,
    assistant_response_override: Any,
) -> dict[str, Any]:
    identity_stable, identity_mutable = _identity_lanes(identity_payload)
    return {
        "system_prompt": _presence_lane(present=True, origin="core.chat_prompt_context", reason_absent="system_prompt_missing"),
        "developer_prompt": base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="developer_role_not_used_by_current_provider_flow",
            selected=False,
            enabled=False,
            origin="core.chat_prompt_context",
        ),
        "time_reference": _presence_lane(present=True, origin="core.chat_turn_runtime_inputs", reason_absent="time_reference_missing"),
        "identity_stable": identity_stable,
        "identity_mutable": identity_mutable,
        "summary": _summary_lane(summary_payload),
        "memory": _memory_lane(memory_traces, context_hints),
        "context_hints": _context_hints_lane(context_hints),
        "hermeneutic_node": _presence_lane(
            present=bool(hermeneutic_judgment_block),
            origin="core.hermeneutic_node.runtime",
            reason_absent="hermeneutic_node_not_injected",
            content_chars=len(str(hermeneutic_judgment_block or "")),
        ),
        "web_lane": _web_lane(web_runtime_payload),
        "note_lane": _notes_lane(workspace_notes_lane),
        "document_lane": _document_lane(active_document_lane),
        "biblio_lane": _biblio_lane(biblio_result),
        "agenda_lane": _agenda_lane(agenda_result),
        "adobe_lane": _adobe_lane(adobe_lane, adobe_context),
        "export_lane": base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="exports_are_reuse_sources_not_prompt_lane_v1",
            selected=False,
            enabled=False,
            origin="core.workspace_folder_exports",
        ),
        "image_lane": base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="generated_images_are_not_main_prompt_lane_v1",
            selected=False,
            enabled=False,
            origin="core.generated_images",
        ),
        "assistant_output_policy": _presence_lane(
            present=assistant_output_policy is not None,
            origin="core.assistant_output_contract",
            reason_absent="assistant_output_policy_missing",
        ),
        "final_response_lock": _presence_lane(
            present=assistant_response_override is not None,
            origin="core.chat_service",
            reason_absent="final_response_lock_absent",
            content_chars=len(str(getattr(assistant_response_override, "content", "") or "")) if assistant_response_override else 0,
        ),
    }
