from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from observability.main_payload_manifest_common import dedupe, mapping, safe_int, safe_str


_SAFE_PROVIDER_ROLES = {"system", "developer", "user", "assistant", "tool"}


def safe_role(value: Any) -> str:
    role = safe_str(value).lower()
    if role in _SAFE_PROVIDER_ROLES:
        return role
    return "unknown"


def capture_message_refs(prompt_messages: Sequence[Mapping[str, Any]]) -> frozenset[int]:
    return frozenset(id(message) for message in prompt_messages if isinstance(message, Mapping))


def message_sources_for_new_messages(
    prompt_messages: Sequence[Mapping[str, Any]],
    before_refs: Sequence[int] | frozenset[int],
    *,
    logical_roles: Sequence[str],
    origin: str,
    origin_stage: str,
    content_kind: str,
) -> dict[int, dict[str, Any]]:
    before = set(int(value) for value in before_refs or ())
    source = {
        "logical_roles": dedupe([str(role) for role in logical_roles]),
        "origin": safe_str(origin),
        "origin_stage": safe_str(origin_stage),
        "content_kind": safe_str(content_kind) or "tool_lane_context",
    }
    return {
        id(message): dict(source)
        for message in prompt_messages
        if isinstance(message, Mapping) and id(message) not in before
    }


def _message_source(
    message: Mapping[str, Any],
    *,
    index: int,
    message_sources: Mapping[Any, Any] | None,
) -> dict[str, Any]:
    sources = message_sources if isinstance(message_sources, Mapping) else {}
    for key in (id(message), str(id(message)), index, str(index)):
        value = sources.get(key)
        if isinstance(value, Mapping):
            roles = value.get("logical_roles")
            logical_roles = [safe_str(role) for role in roles or ()]
            return {
                "logical_roles": dedupe(logical_roles),
                "origin": safe_str(value.get("origin")),
                "origin_stage": safe_str(value.get("origin_stage")),
                "content_kind": safe_str(value.get("content_kind")) or "tool_lane_context",
            }
    return {}


def _text_parts(content: Any) -> list[str]:
    if isinstance(content, str):
        return [content]
    if not isinstance(content, Sequence) or isinstance(content, (bytes, bytearray)):
        return []
    parts: list[str] = []
    for item in content:
        if not isinstance(item, Mapping):
            continue
        if safe_str(item.get("type")).lower() == "text":
            parts.append(str(item.get("text") or ""))
    return parts


def _classification_text(content: Any) -> str:
    return "\n".join(_text_parts(content))[:4000]


def content_shape(content: Any) -> dict[str, Any]:
    if content is None:
        return _shape(False, 0, "empty", 0, 0, 0, 0)
    if isinstance(content, str):
        return _shape(bool(content), len(content), "text", 1 if content else 0, 1 if content else 0, 0, 0)
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
            item_type = safe_str(item.get("type")).lower()
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
        return _shape(parts_count > 0, text_chars, kind, parts_count, text_parts, image_parts, file_parts)
    return _shape(True, 0, "structured", 1, 0, 0, 0)


def _shape(
    present: bool,
    chars: int,
    kind: str,
    parts: int,
    text_parts: int,
    image_parts: int,
    file_parts: int,
) -> dict[str, Any]:
    return {
        "content_present": bool(present),
        "content_chars": int(chars),
        "content_kind": kind,
        "content_parts_count": int(parts),
        "text_part_count": int(text_parts),
        "image_part_count": int(image_parts),
        "file_part_count": int(file_parts),
    }


def _last_user_index(messages: Sequence[Mapping[str, Any]]) -> int | None:
    for index in range(len(messages) - 1, -1, -1):
        if safe_role(messages[index].get("role")) == "user":
            return index
    return None


def _web_lane_injected(web_runtime_payload: Mapping[str, Any] | None) -> bool:
    payload = mapping(web_runtime_payload)
    if safe_str(payload.get("activation_mode")).lower() not in {"manual", "auto"}:
        return False
    return bool(payload.get("context_injected") or str(payload.get("context_block") or ""))


def _classify_message(
    message: Mapping[str, Any],
    *,
    index: int,
    last_user_index: int | None,
    web_lane_injected: bool,
    assistant_output_policy_present: bool,
    identity_roles_present: Mapping[str, bool] | None,
    structured_source: Mapping[str, Any] | None,
) -> tuple[list[str], str, str, str]:
    if structured_source:
        return (
            list(structured_source.get("logical_roles") or ["tool_result"]),
            safe_str(structured_source.get("origin")) or "structured_prompt_lane",
            safe_str(structured_source.get("origin_stage")) or "late_lane_injection",
            safe_str(structured_source.get("content_kind")) or "tool_lane_context",
        )

    role = safe_role(message.get("role"))
    text = _classification_text(message.get("content"))
    upper = text.upper()

    if role == "developer":
        return ["developer_prompt"], "core.chat_prompt_context", "base_prompt", "instruction"
    if role == "system" and index == 0:
        roles = ["system_prompt", "time_reference"]
        identity_present = identity_roles_present if isinstance(identity_roles_present, Mapping) else {}
        if bool(identity_present.get("identity_stable")):
            roles.append("identity_stable")
        if bool(identity_present.get("identity_mutable")):
            roles.append("identity_mutable")
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
        if index == last_user_index and web_lane_injected:
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
    web_injected: bool,
    assistant_output_policy_present: bool,
    identity_roles_present: Mapping[str, bool] | None,
    message_sources: Mapping[Any, Any] | None,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
) -> dict[str, Any]:
    structured_source = _message_source(message, index=index, message_sources=message_sources)
    logical_roles, origin, origin_stage, fallback_content_kind = _classify_message(
        message,
        index=index,
        last_user_index=last_user_idx,
        web_lane_injected=web_injected,
        assistant_output_policy_present=assistant_output_policy_present,
        identity_roles_present=identity_roles_present,
        structured_source=structured_source,
    )
    shape = content_shape(message.get("content"))
    content_kind = shape["content_kind"] if shape["content_kind"] != "text" else fallback_content_kind
    return {
        "index": int(index),
        "provider_role": safe_role(message.get("role")),
        "logical_roles": dedupe(logical_roles),
        "origin": origin,
        "origin_stage": origin_stage,
        "content_kind": content_kind,
        "content_present": bool(shape["content_present"]),
        "content_chars": int(shape["content_chars"]),
        "estimated_tokens": _estimate_message_tokens(message, model=model, count_tokens_func=count_tokens_func),
        "excluded": False,
        "exclusion_reason_code": "",
        "content_parts_count": int(shape["content_parts_count"]),
        "text_part_count": int(shape["text_part_count"]),
        "image_part_count": int(shape["image_part_count"]),
        "file_part_count": int(shape["file_part_count"]),
        "raw_content_included": False,
    }


def build_messages_manifest(
    prompt_messages: Sequence[Mapping[str, Any]],
    *,
    web_runtime_payload: Mapping[str, Any] | None,
    assistant_output_policy: Any,
    identity_roles_present: Mapping[str, bool] | None,
    message_sources: Mapping[Any, Any] | None,
    model: str,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None,
) -> list[dict[str, Any]]:
    messages = [message for message in prompt_messages if isinstance(message, Mapping)]
    last_user_idx = _last_user_index(messages)
    web_injected = _web_lane_injected(web_runtime_payload)
    return [
        _message_entry(
            message,
            index=index,
            last_user_idx=last_user_idx,
            web_injected=web_injected,
            assistant_output_policy_present=assistant_output_policy is not None,
            identity_roles_present=identity_roles_present,
            message_sources=message_sources,
            model=model,
            count_tokens_func=count_tokens_func,
        )
        for index, message in enumerate(messages)
    ]


def build_prompt_budget(
    *,
    prompt_messages: Sequence[Mapping[str, Any]],
    runtime_main_model: str,
    estimated_prompt_tokens: int | None = None,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None = None,
    max_tokens: int,
    prompt_soft_token_limit: int | None = None,
) -> dict[str, Any]:
    messages = [dict(message) for message in prompt_messages if isinstance(message, Mapping)]
    total_chars = sum(safe_int(content_shape(message.get("content")).get("content_chars")) for message in messages)
    estimated_tokens = estimated_prompt_tokens
    if estimated_tokens is None and callable(count_tokens_func):
        try:
            estimated_tokens = max(0, int(count_tokens_func(messages, runtime_main_model) or 0))
        except Exception:
            estimated_tokens = None
    soft_limit = safe_int(prompt_soft_token_limit)
    soft_limit_configured = soft_limit > 0
    soft_limit_exceeded = bool(
        soft_limit_configured
        and estimated_tokens is not None
        and safe_int(estimated_tokens) > soft_limit
    )
    if not soft_limit_configured:
        soft_limit_reason_code = "not_configured"
    elif estimated_tokens is None:
        soft_limit_reason_code = "estimate_not_available"
    elif soft_limit_exceeded:
        soft_limit_reason_code = "over_soft_limit_no_truncation"
    else:
        soft_limit_reason_code = "within_soft_limit"
    return {
        "message_count": len(messages),
        "content_chars_total": total_chars,
        "estimated_prompt_tokens": estimated_tokens,
        "max_completion_tokens": safe_int(max_tokens),
        "soft_limit_configured": soft_limit_configured,
        "prompt_soft_token_limit": soft_limit,
        "prompt_soft_limit_exceeded": soft_limit_exceeded,
        "dialogue_messages_truncated": False,
        "excluded_count": 0,
        "truncated_count": 0,
        "soft_limit_stage": "prompt_final_manifest",
        "soft_limit_policy": "observability_only_no_prompt_exclusion",
        "soft_limit_reason_code": soft_limit_reason_code,
    }
