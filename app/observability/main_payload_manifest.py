from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence


SCHEMA_VERSION = "main_payload_manifest_v1"
SCOPE = "main_chat"
OBSERVABILITY_STAGE = "main_payload_manifest"

STATUS_OK = "ok"
STATUS_DISABLED = "disabled"
STATUS_NOT_SELECTED = "not_selected"
STATUS_NOT_CONFIGURED = "not_configured"
STATUS_NOT_APPLICABLE = "not_applicable"
STATUS_FAILED = "failed"
STATUS_ERROR = "error"

RAW_FLAGS = {
    "raw_prompt_included": False,
    "raw_message_included": False,
    "raw_content_included": False,
    "raw_lane_content_included": False,
    "raw_provider_payload_included": False,
    "raw_secret_included": False,
}

_SAFE_PROVIDER_ROLES = {
    "system",
    "developer",
    "user",
    "assistant",
    "tool",
}


def _mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _safe_bool(value: Any) -> bool:
    return bool(value)


def _safe_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _safe_role(value: Any) -> str:
    role = _safe_str(value).lower()
    if role in _SAFE_PROVIDER_ROLES:
        return role
    return "unknown"


def _safe_status(value: Any, *, fallback: str = STATUS_NOT_APPLICABLE) -> str:
    status = _safe_str(value).lower()
    if status in {
        STATUS_OK,
        "skipped",
        STATUS_DISABLED,
        STATUS_NOT_SELECTED,
        STATUS_NOT_CONFIGURED,
        STATUS_NOT_APPLICABLE,
        "refused",
        STATUS_FAILED,
        STATUS_ERROR,
    }:
        return status
    if status in {"empty", "missing", "not_requested"}:
        return STATUS_NOT_SELECTED
    if status in {"available", "ready", "authorized", "used"}:
        return STATUS_OK
    return fallback


def _dedupe(values: Sequence[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        item = _safe_str(value)
        if item and item not in seen:
            result.append(item)
            seen.add(item)
    return result


def _safe_count_from_sequence(value: Any) -> int:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return len(value)
    return 0


def _text_parts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, Sequence) or isinstance(content, (bytes, bytearray)):
        return []
    parts: list[str] = []
    for item in content:
        if not isinstance(item, Mapping):
            continue
        item_type = _safe_str(item.get("type")).lower()
        if item_type == "text":
            parts.append(str(item.get("text") or ""))
    return parts


def _classification_text(content: Any) -> str:
    return "\n".join(_text_parts(content))[:4000]


def _content_shape(content: Any) -> dict[str, Any]:
    if content is None:
        return {
            "content_present": False,
            "content_chars": 0,
            "content_kind": "empty",
            "content_parts_count": 0,
            "text_part_count": 0,
            "image_part_count": 0,
            "file_part_count": 0,
        }

    if isinstance(content, str):
        return {
            "content_present": bool(content),
            "content_chars": len(content),
            "content_kind": "text",
            "content_parts_count": 1 if content else 0,
            "text_part_count": 1 if content else 0,
            "image_part_count": 0,
            "file_part_count": 0,
        }

    if isinstance(content, Sequence) and not isinstance(content, (bytes, bytearray)):
        text_chars = 0
        text_parts = 0
        image_parts = 0
        file_parts = 0
        other_parts = 0
        for item in content:
            if not isinstance(item, Mapping):
                other_parts += 1
                continue
            item_type = _safe_str(item.get("type")).lower()
            if item_type == "text":
                text_parts += 1
                text_chars += len(str(item.get("text") or ""))
            elif item_type in {"image_url", "input_image"}:
                image_parts += 1
            elif item_type in {"file", "input_file", "document"}:
                file_parts += 1
            else:
                other_parts += 1
        parts_count = text_parts + image_parts + file_parts + other_parts
        if image_parts or file_parts:
            kind = "multimodal"
        elif text_parts:
            kind = "text_parts"
        else:
            kind = "structured"
        return {
            "content_present": parts_count > 0,
            "content_chars": text_chars,
            "content_kind": kind,
            "content_parts_count": parts_count,
            "text_part_count": text_parts,
            "image_part_count": image_parts,
            "file_part_count": file_parts,
        }

    return {
        "content_present": True,
        "content_chars": 0,
        "content_kind": "structured",
        "content_parts_count": 1,
        "text_part_count": 0,
        "image_part_count": 0,
        "file_part_count": 0,
    }


def _last_user_index(messages: Sequence[Mapping[str, Any]]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        if _safe_role(messages[index].get("role")) == "user":
            return index
    return None


def _web_lane_active(web_runtime_payload: Mapping[str, Any] | None) -> bool:
    payload = _mapping(web_runtime_payload)
    return _safe_str(payload.get("activation_mode")).lower() in {"manual", "auto"}


def _classify_message(
    message: Mapping[str, Any],
    *,
    index: int,
    last_user_index: int | None,
    web_lane_active: bool,
    assistant_output_policy_present: bool,
) -> tuple[list[str], str, str, str]:
    role = _safe_role(message.get("role"))
    text = _classification_text(message.get("content"))
    upper = text.upper()

    if "[NOTES DE DOSSIER" in upper:
        return ["note_lane"], "core.workspace_folder_notes_prompt_lane", "late_note_lane", "tool_lane_context"
    if "[DOCUMENTS ACTIFS" in upper:
        return ["document_lane"], "core.active_document_prompt_lane", "late_document_lane", "tool_lane_context"
    if "PASSAGES DE BIBLIOTHEQUE" in upper or "PASSAGES BIBLIO" in upper:
        return ["biblio_lane"], "biblio.chat_runtime", "late_biblio_lane", "tool_lane_context"
    if "[ADOBE DOCS" in upper:
        return ["adobe_lane"], "core.adobe_docs_prompt_lane", "late_adobe_lane", "tool_lane_context"

    if role == "developer":
        return ["developer_prompt"], "core.chat_prompt_context", "base_prompt", "instruction"
    if role == "system" and index == 0:
        roles = ["system_prompt", "time_reference", "identity_stable", "identity_mutable"]
        if assistant_output_policy_present:
            roles.append("assistant_output_policy")
        if "JUGEMENT HERMENEUTIQUE" in upper:
            roles.append("hermeneutic_node")
        return roles, "core.chat_prompt_context", "base_prompt_with_guards", "system_instruction"
    if role == "system" and "RESUME" in upper:
        return ["summary"], "core.conversations_prompt_window", "prompt_window", "summary"
    if role == "system" and ("INDICES CONTEXTUELS" in upper or "CONTEXTE DU SOUVENIR" in upper):
        return ["context_hints", "memory"], "core.conversations_prompt_window", "prompt_window", "memory_context"
    if role == "system":
        return ["time_reference"], "core.conversations_prompt_window", "prompt_window", "system_context"

    if role == "user":
        roles = ["user_turn"]
        origin = "conversation_history"
        origin_stage = "prompt_window"
        content_kind = "dialogue"
        if index == last_user_index:
            origin = "current_user_turn"
            origin_stage = "final_user_turn"
        if index == last_user_index and web_lane_active:
            roles.append("web_lane")
            origin = "mixed_user_turn_and_web_context"
            origin_stage = "web_late_injection"
            content_kind = "dialogue_with_tool_lane_context"
        return roles, origin, origin_stage, content_kind

    if role == "assistant":
        return ["assistant_turn"], "conversation_history", "prompt_window", "dialogue"
    if role == "tool":
        return ["tool_result"], "tool_runtime", "prompt_window", "tool_result"
    return ["unknown"], "unknown", "unknown", "unknown"


def _estimate_message_tokens(
    message: Mapping[str, Any],
    *,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
) -> int | None:
    if not callable(count_tokens_func):
        return None
    try:
        value = count_tokens_func([dict(message)], model)
    except Exception:
        return None
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return None


def _message_entry(
    message: Mapping[str, Any],
    *,
    index: int,
    last_user_idx: int | None,
    web_active: bool,
    assistant_output_policy_present: bool,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
) -> dict[str, Any]:
    role = _safe_role(message.get("role"))
    logical_roles, origin, origin_stage, fallback_content_kind = _classify_message(
        message,
        index=index,
        last_user_index=last_user_idx,
        web_lane_active=web_active,
        assistant_output_policy_present=assistant_output_policy_present,
    )
    shape = _content_shape(message.get("content"))
    content_kind = shape["content_kind"] if shape["content_kind"] != "text" else fallback_content_kind
    return {
        "index": int(index),
        "provider_role": role,
        "logical_roles": _dedupe(logical_roles),
        "origin": origin,
        "origin_stage": origin_stage,
        "content_kind": content_kind,
        "content_present": bool(shape["content_present"]),
        "content_chars": int(shape["content_chars"]),
        "estimated_tokens": _estimate_message_tokens(
            message,
            model=model,
            count_tokens_func=count_tokens_func,
        ),
        "excluded": False,
        "exclusion_reason_code": "",
        "content_parts_count": int(shape["content_parts_count"]),
        "text_part_count": int(shape["text_part_count"]),
        "image_part_count": int(shape["image_part_count"]),
        "file_part_count": int(shape["file_part_count"]),
        "raw_content_included": False,
    }


def _messages_manifest(
    prompt_messages: Sequence[Mapping[str, Any]],
    *,
    web_runtime_payload: Mapping[str, Any] | None,
    assistant_output_policy: Any,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
) -> list[dict[str, Any]]:
    messages = [message for message in prompt_messages if isinstance(message, Mapping)]
    last_user_idx = _last_user_index(messages)
    web_active = _web_lane_active(web_runtime_payload)
    assistant_output_policy_present = assistant_output_policy is not None
    return [
        _message_entry(
            message,
            index=index,
            last_user_idx=last_user_idx,
            web_active=web_active,
            assistant_output_policy_present=assistant_output_policy_present,
            model=model,
            count_tokens_func=count_tokens_func,
        )
        for index, message in enumerate(messages)
    ]


def _base_lane(
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
        "status": _safe_status(status, fallback=STATUS_NOT_APPLICABLE),
        "reason_code": _safe_str(reason_code),
        "selected": bool(selected),
        "enabled": enabled,
        "input_count": int(input_count),
        "injected_count": int(injected_count),
        "excluded_count": int(excluded_count),
        "content_chars": int(content_chars),
        "estimated_tokens": estimated_tokens,
        "origin": _safe_str(origin),
        "raw_lane_content_included": False,
    }
    if budget:
        payload["budget"] = {str(key): _safe_int(value) for key, value in budget.items()}
    if extra:
        for key, value in extra.items():
            payload[str(key)] = value
    return payload


def _summary_lane(summary_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(summary_payload)
    summary = _mapping(payload.get("summary"))
    available = _safe_str(payload.get("status")) == "available" and bool(summary)
    return _base_lane(
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
    payload = _mapping(identity_payload)
    frida = _mapping(payload.get("frida"))
    user = _mapping(payload.get("user"))
    sides = (frida, user)
    static_chars = 0
    mutable_chars = 0
    static_count = 0
    mutable_count = 0
    for side in sides:
        static = _mapping(side.get("static"))
        mutable = _mapping(side.get("mutable"))
        static_content = str(static.get("content") or "")
        mutable_content = str(mutable.get("content") or "")
        if static_content:
            static_count += 1
            static_chars += len(static_content)
        if mutable_content:
            mutable_count += 1
            mutable_chars += len(mutable_content)
    stable = _base_lane(
        status=STATUS_OK if static_count else STATUS_NOT_SELECTED,
        reason_code="" if static_count else "identity_stable_empty",
        selected=bool(static_count),
        enabled=True,
        input_count=2,
        injected_count=static_count,
        content_chars=static_chars,
        origin="memory.identity_input",
    )
    mutable = _base_lane(
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


def _memory_lane(memory_traces: Sequence[Any] | None, context_hints: Sequence[Any] | None) -> dict[str, Any]:
    traces = tuple(memory_traces or ())
    hints = tuple(context_hints or ())
    trace_chars = 0
    for trace in traces:
        if isinstance(trace, Mapping):
            trace_chars += len(str(trace.get("content") or trace.get("text") or ""))
        else:
            trace_chars += len(str(trace or ""))
    return _base_lane(
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
    hint_chars = sum(len(str(hint or "")) for hint in hints)
    return _base_lane(
        status=STATUS_OK if hints else STATUS_NOT_SELECTED,
        reason_code="" if hints else "context_hints_empty",
        selected=bool(hints),
        enabled=True,
        input_count=len(hints),
        injected_count=1 if hints else 0,
        content_chars=hint_chars,
        origin="core.chat_memory_flow",
    )


def _web_lane(web_runtime_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    payload = _mapping(web_runtime_payload)
    enabled = bool(payload.get("enabled", payload.get("search_enabled", False)))
    selected = _web_lane_active(payload)
    injected = bool(payload.get("context_injected"))
    if selected:
        status = _safe_status(payload.get("status"), fallback=STATUS_OK)
    elif not enabled:
        status = STATUS_DISABLED
    else:
        status = STATUS_NOT_SELECTED
    return _base_lane(
        status=status,
        reason_code=_safe_str(payload.get("reason_code")),
        selected=selected,
        enabled=enabled,
        input_count=_safe_int(payload.get("results_count")),
        injected_count=1 if injected else 0,
        excluded_count=max(0, _safe_int(payload.get("results_count")) - (1 if injected else 0)),
        content_chars=_safe_int(payload.get("context_chars")),
        origin="core.chat_prompt_context",
        extra={
            "activation_mode": _safe_str(payload.get("activation_mode")) or "off",
            "context_injected": injected,
        },
    )


def _notes_lane(lane: Any) -> dict[str, Any]:
    as_dict = getattr(lane, "as_content_free_dict", None)
    lane_payload = as_dict() if callable(as_dict) else {}
    decisions = tuple(getattr(lane, "decisions", ()) or ())
    requested_count = _safe_int(getattr(lane, "requested_count", 0))
    injected_count = _safe_int(getattr(lane, "injected_count", 0))
    not_injected_count = _safe_int(getattr(lane, "not_injected_count", 0))
    read_status = _safe_str(getattr(lane, "read_status", ""))
    selected = bool(requested_count or decisions)
    status = _safe_status(read_status or (STATUS_OK if injected_count else STATUS_NOT_SELECTED))
    chars = sum(
        _safe_int(getattr(decision, "markdown_char_count", 0))
        for decision in decisions
        if bool(getattr(decision, "injected", False))
    )
    return _base_lane(
        status=status if selected else STATUS_NOT_SELECTED,
        reason_code=_safe_str(getattr(lane, "read_reason_code", "")) or ("" if selected else "notes_not_selected"),
        selected=selected,
        enabled=True,
        input_count=max(requested_count, len(decisions)),
        injected_count=injected_count,
        excluded_count=not_injected_count,
        content_chars=chars,
        origin="core.workspace_folder_notes_prompt_lane",
        budget={
            "max_notes_injected_per_turn": _safe_int(lane_payload.get("max_notes_injected_per_turn")),
            "max_notes_total_chars_per_turn": _safe_int(lane_payload.get("max_notes_total_chars_per_turn")),
        },
        extra={
            "invalid_requested_count": _safe_int(getattr(lane, "invalid_requested_count", 0)),
            "over_limit_count": _safe_int(getattr(lane, "over_limit_count", 0)),
        },
    )


def _document_lane(lane: Any) -> dict[str, Any]:
    decisions = tuple(getattr(lane, "decisions", ()) or ())
    injected_count = _safe_int(getattr(lane, "injected_count", 0))
    not_injected_count = _safe_int(getattr(lane, "not_injected_count", 0))
    read_status = _safe_str(getattr(lane, "read_status", ""))
    selected = bool(decisions)
    chars = sum(
        _safe_int(getattr(decision, "text_chars", 0))
        for decision in decisions
        if bool(getattr(decision, "injected", False))
    )
    media_kind_counts: dict[str, int] = {}
    reason_codes: list[str] = []
    for decision in decisions:
        media_kind = _safe_str(getattr(decision, "media_kind", "")) or "unknown"
        media_kind_counts[media_kind] = media_kind_counts.get(media_kind, 0) + 1
        reason = _safe_str(getattr(decision, "reason_code", ""))
        if reason:
            reason_codes.append(reason)
    return _base_lane(
        status=_safe_status(read_status or (STATUS_OK if selected else STATUS_NOT_SELECTED)),
        reason_code=_safe_str(getattr(lane, "read_reason_code", "")) or ("" if selected else "documents_not_selected"),
        selected=selected,
        enabled=True,
        input_count=len(decisions),
        injected_count=injected_count,
        excluded_count=not_injected_count,
        content_chars=chars,
        origin="core.active_document_prompt_lane",
        extra={
            "media_kind_counts": media_kind_counts,
            "exclusion_reason_codes": _dedupe(reason_codes),
        },
    )


def _biblio_lane(result: Any) -> dict[str, Any]:
    payload = _mapping(getattr(result, "observability_payload", {}))
    enabled = bool(getattr(result, "enabled", payload.get("enabled", False)))
    used = bool(getattr(result, "used", payload.get("used", False)))
    query_kind = _safe_str(getattr(result, "query_kind", payload.get("query_kind")))
    prompt_lane = getattr(result, "prompt_lane", None)
    prompt_message = getattr(result, "prompt_message", None)
    decisions = tuple(getattr(prompt_lane, "decisions", ()) or ())
    passage_count = _safe_int(getattr(prompt_lane, "passage_count", 0))
    lane_chars = _safe_int(getattr(prompt_lane, "chars", 0))
    selected = bool(enabled and (used or query_kind and query_kind != "not_requested" or prompt_message is not None))
    status = _safe_status(payload.get("status") or ("ok" if selected else "disabled" if not enabled else "not_selected"))
    return _base_lane(
        status=status,
        reason_code=_safe_str(getattr(result, "reason_code", payload.get("reason_code"))),
        selected=selected,
        enabled=enabled,
        input_count=len(decisions) or passage_count,
        injected_count=1 if prompt_message is not None else 0,
        excluded_count=max(0, len(decisions) - passage_count) if decisions else 0,
        content_chars=lane_chars,
        origin="biblio.chat_runtime",
        budget={
            "max_passages": _safe_int(getattr(prompt_lane, "max_passages", 0)),
            "max_total_chars": _safe_int(getattr(prompt_lane, "max_total_chars", 0)),
        },
        extra={
            "query_kind": query_kind or "not_requested",
            "final_response_lock_present": bool(getattr(result, "final_response_lock", None)),
        },
    )


def _agenda_lane(result: Any) -> dict[str, Any]:
    payload = _mapping(getattr(result, "observability_payload", {}))
    enabled = bool(getattr(result, "enabled", payload.get("enabled", False)))
    used = bool(getattr(result, "used", payload.get("used", False)))
    selected = bool(enabled and (used or _safe_str(payload.get("mode")) not in {"", "off"}))
    status = _safe_status(getattr(result, "status", payload.get("status")) or ("disabled" if not enabled else "not_selected"))
    return _base_lane(
        status=status,
        reason_code=_safe_str(getattr(result, "reason_code", payload.get("reason_code"))),
        selected=selected,
        enabled=enabled,
        input_count=_safe_int(payload.get("tool_count")),
        injected_count=0,
        excluded_count=0,
        content_chars=0,
        origin="agenda.chat_runtime",
        extra={
            "mode": _safe_str(payload.get("mode")) or "off",
            "model_called": bool(payload.get("model_called")),
            "final_response_lock_present": bool(getattr(result, "final_response_lock", None)),
        },
    )


def _adobe_lane(lane: Any, adobe_context: Any = None) -> dict[str, Any]:
    as_dict = getattr(lane, "as_content_free_dict", None)
    payload = as_dict() if callable(as_dict) else {}
    active = bool(getattr(adobe_context, "active", False) or getattr(lane, "messages", ()))
    status_raw = _safe_str(payload.get("status") or getattr(lane, "status", ""))
    status = STATUS_NOT_SELECTED if status_raw in {"", "not_requested"} else _safe_status(status_raw, fallback=STATUS_OK)
    messages = tuple(getattr(lane, "messages", ()) or ())
    return _base_lane(
        status=status if active else STATUS_NOT_SELECTED,
        reason_code="adobe_not_requested" if not active else "",
        selected=active,
        enabled=True,
        input_count=_safe_int(payload.get("source_count")),
        injected_count=len(messages),
        excluded_count=0,
        content_chars=_safe_int(payload.get("injected_chars")),
        origin="core.adobe_docs_prompt_lane",
        extra={
            "source_count": _safe_int(payload.get("source_count")),
            "passage_count": _safe_int(payload.get("passage_count")),
            "reason_codes": _dedupe([str(code) for code in payload.get("reason_codes", []) or []]),
        },
    )


def _simple_presence_lane(
    *,
    present: bool,
    origin: str,
    reason_absent: str,
    content_chars: int = 0,
    input_count: int = 1,
) -> dict[str, Any]:
    return _base_lane(
        status=STATUS_OK if present else STATUS_NOT_SELECTED,
        reason_code="" if present else reason_absent,
        selected=present,
        enabled=True,
        input_count=input_count if present else 0,
        injected_count=1 if present else 0,
        content_chars=content_chars if present else 0,
        origin=origin,
    )


def _lane_statuses(
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
    hermeneutic_chars = len(str(hermeneutic_judgment_block or ""))
    return {
        "system_prompt": _simple_presence_lane(
            present=True,
            origin="core.chat_prompt_context",
            reason_absent="system_prompt_missing",
        ),
        "developer_prompt": _base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="developer_role_not_used_by_current_provider_flow",
            selected=False,
            enabled=False,
            origin="core.chat_prompt_context",
        ),
        "time_reference": _simple_presence_lane(
            present=True,
            origin="core.chat_turn_runtime_inputs",
            reason_absent="time_reference_missing",
        ),
        "identity_stable": identity_stable,
        "identity_mutable": identity_mutable,
        "summary": _summary_lane(summary_payload),
        "memory": _memory_lane(memory_traces, context_hints),
        "context_hints": _context_hints_lane(context_hints),
        "hermeneutic_node": _simple_presence_lane(
            present=bool(hermeneutic_judgment_block),
            origin="core.hermeneutic_node.runtime",
            reason_absent="hermeneutic_node_not_injected",
            content_chars=hermeneutic_chars,
        ),
        "web_lane": _web_lane(web_runtime_payload),
        "note_lane": _notes_lane(workspace_notes_lane),
        "document_lane": _document_lane(active_document_lane),
        "biblio_lane": _biblio_lane(biblio_result),
        "agenda_lane": _agenda_lane(agenda_result),
        "adobe_lane": _adobe_lane(adobe_lane, adobe_context),
        "export_lane": _base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="exports_are_reuse_sources_not_prompt_lane_v1",
            selected=False,
            enabled=False,
            origin="core.workspace_folder_exports",
        ),
        "image_lane": _base_lane(
            status=STATUS_NOT_APPLICABLE,
            reason_code="generated_images_are_not_main_prompt_lane_v1",
            selected=False,
            enabled=False,
            origin="core.generated_images",
        ),
        "assistant_output_policy": _simple_presence_lane(
            present=assistant_output_policy is not None,
            origin="core.assistant_output_contract",
            reason_absent="assistant_output_policy_missing",
        ),
        "final_response_lock": _simple_presence_lane(
            present=assistant_response_override is not None,
            origin="core.chat_service",
            reason_absent="final_response_lock_absent",
            content_chars=_final_lock_content_chars(assistant_response_override),
        ),
    }


def _messages_windows(
    *,
    messages: Sequence[Mapping[str, Any]],
    conversation: Mapping[str, Any] | None,
    recent_context_payload: Mapping[str, Any] | None,
    recent_window_payload: Mapping[str, Any] | None,
    biblio_recent_dialogue: Sequence[Any] | None,
    agenda_recent_dialogue: Sequence[Any] | None,
) -> dict[str, Any]:
    manifest_messages = [message for message in messages if isinstance(message, Mapping)]
    conversation_messages = tuple(_mapping(conversation).get("messages") or ())
    recent_context = _mapping(recent_context_payload)
    recent_window = _mapping(recent_window_payload)
    provider_role_sequence = [_safe_role(message.get("role")) for message in manifest_messages]
    return {
        "prompt_final": {
            "message_count": len(manifest_messages),
            "provider_role_sequence": provider_role_sequence,
        },
        "conversation": {
            "message_count": len(conversation_messages),
            "user_message_count": sum(1 for message in conversation_messages if _mapping(message).get("role") == "user"),
            "assistant_message_count": sum(
                1 for message in conversation_messages if _mapping(message).get("role") == "assistant"
            ),
        },
        "recent_context": {
            "message_count": _safe_count_from_sequence(recent_context.get("messages")),
        },
        "recent_window": {
            "turn_count": _safe_int(recent_window.get("turn_count")),
            "max_recent_turns": _safe_int(recent_window.get("max_recent_turns")),
            "has_in_progress_turn": bool(recent_window.get("has_in_progress_turn")),
        },
        "biblio_recent_dialogue": {
            "message_count": _safe_count_from_sequence(biblio_recent_dialogue),
        },
        "agenda_recent_dialogue": {
            "message_count": _safe_count_from_sequence(agenda_recent_dialogue),
        },
    }


def _prompt_budget(
    *,
    prompt_messages: Sequence[Mapping[str, Any]],
    runtime_main_model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
    max_tokens: int,
) -> dict[str, Any]:
    messages = [dict(message) for message in prompt_messages if isinstance(message, Mapping)]
    total_chars = sum(_safe_int(_content_shape(message.get("content")).get("content_chars")) for message in messages)
    estimated_tokens = None
    if callable(count_tokens_func):
        try:
            estimated_tokens = max(0, int(count_tokens_func(messages, runtime_main_model) or 0))
        except Exception:
            estimated_tokens = None
    return {
        "message_count": len(messages),
        "content_chars_total": total_chars,
        "estimated_prompt_tokens": estimated_tokens,
        "max_completion_tokens": _safe_int(max_tokens),
    }


def _runtime_settings_payload(
    *,
    runtime_main_model: str,
    temperature: Any,
    top_p: Any,
    max_tokens: Any,
    stream_req: Any,
) -> dict[str, Any]:
    return {
        "provider_family": "openrouter",
        "model": _safe_str(runtime_main_model),
        "temperature_present": temperature is not None,
        "top_p_present": top_p is not None,
        "max_tokens": _safe_int(max_tokens),
        "stream_requested": bool(stream_req),
    }


def _assistant_output_policy_payload(policy: Any) -> dict[str, Any]:
    return {
        "present": policy is not None,
        "allow_structure": bool(getattr(policy, "allow_structure", False)),
        "allow_code": bool(getattr(policy, "allow_code", False)),
        "raw_policy_text_included": False,
    }


def _final_lock_content_chars(assistant_response_override: Any) -> int:
    if assistant_response_override is None:
        return 0
    return len(str(getattr(assistant_response_override, "content", "") or ""))


def _override_observability(assistant_response_override: Any) -> dict[str, Any]:
    builder = getattr(assistant_response_override, "to_observability", None)
    if callable(builder):
        try:
            payload = builder()
        except Exception:
            payload = {}
    else:
        payload = {}
    if not isinstance(payload, Mapping):
        payload = {}
    return dict(payload)


def _final_response_lock_payload(assistant_response_override: Any) -> dict[str, Any]:
    if assistant_response_override is None:
        return {
            "present": False,
            "main_model_bypassed": False,
            "source": "",
            "reason_code": "",
            "priority_policy": "agenda_over_biblio",
            "content_present": False,
            "content_chars": 0,
            "raw_content_included": False,
        }
    observation = _override_observability(assistant_response_override)
    return {
        "present": True,
        "main_model_bypassed": True,
        "source": _safe_str(getattr(assistant_response_override, "source", "")),
        "reason_code": _safe_str(getattr(assistant_response_override, "reason_code", "")),
        "priority_policy": "agenda_over_biblio",
        "content_present": bool(observation.get("content_present", True)),
        "content_chars": _safe_int(observation.get("content_chars")) or _final_lock_content_chars(assistant_response_override),
        "raw_content_included": False,
    }


def _hash_policy_payload() -> dict[str, Any]:
    return {
        "stable_text_hashes_included": False,
        "short_stable_text_hashes_included": False,
        "fingerprints_included": False,
        "policy": "no_stable_hash_on_sensitive_text",
    }


def _conversation_state(conversation: Mapping[str, Any] | None, turn_id: str | None) -> dict[str, Any]:
    payload = _mapping(conversation)
    messages = payload.get("messages")
    message_count = len(messages) if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes)) else 0
    conversation_id_present = bool(_safe_str(payload.get("id")))
    return {
        "conversation_id_present": conversation_id_present,
        "turn_id_present": bool(_safe_str(turn_id)),
        "conversation_state_kind": "conversation_id_present" if conversation_id_present else "pending_or_new_without_id",
        "conversation_message_count": message_count,
        "workspace_folder_present": bool(_safe_str(payload.get("workspace_folder_id"))),
    }


def build_main_payload_manifest(
    *,
    conversation: Mapping[str, Any] | None,
    prompt_messages: Sequence[Mapping[str, Any]],
    runtime_main_model: str,
    temperature: Any,
    top_p: Any,
    max_tokens: Any,
    stream_req: Any,
    assistant_output_policy: Any,
    assistant_response_override: Any,
    turn_id: str | None = None,
    summary_payload: Mapping[str, Any] | None = None,
    identity_payload: Mapping[str, Any] | None = None,
    recent_context_payload: Mapping[str, Any] | None = None,
    recent_window_payload: Mapping[str, Any] | None = None,
    memory_traces: Sequence[Any] | None = None,
    context_hints: Sequence[Any] | None = None,
    web_runtime_payload: Mapping[str, Any] | None = None,
    workspace_notes_lane: Any = None,
    active_document_lane: Any = None,
    biblio_result: Any = None,
    agenda_result: Any = None,
    adobe_context: Any = None,
    adobe_lane: Any = None,
    hermeneutic_judgment_block: str | None = None,
    biblio_recent_dialogue: Sequence[Any] | None = None,
    agenda_recent_dialogue: Sequence[Any] | None = None,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None = None,
) -> dict[str, Any]:
    messages = [message for message in prompt_messages if isinstance(message, Mapping)]
    manifest_messages = _messages_manifest(
        messages,
        web_runtime_payload=web_runtime_payload,
        assistant_output_policy=assistant_output_policy,
        model=runtime_main_model,
        count_tokens_func=count_tokens_func,
    )
    final_response_lock = _final_response_lock_payload(assistant_response_override)
    conversation_state = _conversation_state(conversation, turn_id)
    return {
        "schema_version": SCHEMA_VERSION,
        "scope": SCOPE,
        "main_model_called": not bool(final_response_lock["main_model_bypassed"]),
        "conversation_id_present": bool(conversation_state["conversation_id_present"]),
        "turn_id_present": bool(conversation_state["turn_id_present"]),
        "provider": "openrouter",
        "runtime_settings": _runtime_settings_payload(
            runtime_main_model=runtime_main_model,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            stream_req=stream_req,
        ),
        "assistant_output_policy": _assistant_output_policy_payload(assistant_output_policy),
        "final_response_lock": final_response_lock,
        "messages": manifest_messages,
        "lane_statuses": _lane_statuses(
            summary_payload=summary_payload,
            identity_payload=identity_payload,
            memory_traces=memory_traces,
            context_hints=context_hints,
            web_runtime_payload=web_runtime_payload,
            workspace_notes_lane=workspace_notes_lane,
            active_document_lane=active_document_lane,
            biblio_result=biblio_result,
            agenda_result=agenda_result,
            adobe_context=adobe_context,
            adobe_lane=adobe_lane,
            hermeneutic_judgment_block=hermeneutic_judgment_block,
            assistant_output_policy=assistant_output_policy,
            assistant_response_override=assistant_response_override,
        ),
        "windows": _messages_windows(
            messages=messages,
            conversation=conversation,
            recent_context_payload=recent_context_payload,
            recent_window_payload=recent_window_payload,
            biblio_recent_dialogue=biblio_recent_dialogue,
            agenda_recent_dialogue=agenda_recent_dialogue,
        ),
        "budgets": {
            "prompt": _prompt_budget(
                prompt_messages=messages,
                runtime_main_model=runtime_main_model,
                count_tokens_func=count_tokens_func,
                max_tokens=_safe_int(max_tokens),
            ),
        },
        "conversation_state": conversation_state,
        "raw_flags": dict(RAW_FLAGS),
        "hash_policy": _hash_policy_payload(),
    }


def emit_main_payload_manifest(
    manifest: Mapping[str, Any],
    *,
    chat_turn_logger_module: Any,
) -> bool:
    payload = dict(manifest)
    setter = getattr(chat_turn_logger_module, "set_state", None)
    if callable(setter):
        setter("main_payload_manifest", payload)
    emitter = getattr(chat_turn_logger_module, "emit", None)
    if not callable(emitter):
        return False
    return bool(
        emitter(
            OBSERVABILITY_STAGE,
            status=STATUS_OK,
            payload=payload,
        )
    )
