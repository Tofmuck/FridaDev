from __future__ import annotations

from typing import Any, Callable, Mapping, Sequence

from observability.main_payload_manifest_common import (
    OBSERVABILITY_STAGE,
    RAW_FLAGS,
    SCHEMA_VERSION,
    SCOPE,
    STATUS_OK,
    mapping,
    safe_int,
    safe_str,
)
from observability.main_payload_manifest_lanes import build_lane_statuses, identity_roles_present
from observability.main_payload_manifest_messages import (
    build_messages_manifest,
    build_messages_windows,
    build_prompt_budget,
    capture_message_refs,
    message_sources_for_new_messages,
)


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
        "model": safe_str(runtime_main_model),
        "temperature_present": temperature is not None,
        "top_p_present": top_p is not None,
        "max_tokens": safe_int(max_tokens),
        "stream_requested": bool(stream_req),
    }


def _assistant_output_policy_payload(policy: Any) -> dict[str, Any]:
    return {
        "present": policy is not None,
        "allow_structure": bool(getattr(policy, "allow_structure", False)),
        "allow_code": bool(getattr(policy, "allow_code", False)),
        "raw_policy_text_included": False,
    }


def _override_observability(assistant_response_override: Any) -> dict[str, Any]:
    builder = getattr(assistant_response_override, "to_observability", None)
    if callable(builder):
        try:
            payload = builder()
        except Exception:
            payload = {}
    else:
        payload = {}
    return dict(payload) if isinstance(payload, Mapping) else {}


def _final_lock_content_chars(assistant_response_override: Any) -> int:
    if assistant_response_override is None:
        return 0
    return len(str(getattr(assistant_response_override, "content", "") or ""))


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
        "source": safe_str(getattr(assistant_response_override, "source", "")),
        "reason_code": safe_str(getattr(assistant_response_override, "reason_code", "")),
        "priority_policy": "agenda_over_biblio",
        "content_present": bool(observation.get("content_present", True)),
        "content_chars": safe_int(observation.get("content_chars")) or _final_lock_content_chars(assistant_response_override),
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
    payload = mapping(conversation)
    messages = payload.get("messages")
    message_count = len(messages) if isinstance(messages, Sequence) and not isinstance(messages, (str, bytes)) else 0
    conversation_id_present = bool(safe_str(payload.get("id")))
    return {
        "conversation_id_present": conversation_id_present,
        "turn_id_present": bool(safe_str(turn_id)),
        "conversation_state_kind": "conversation_id_present" if conversation_id_present else "pending_or_new_without_id",
        "conversation_message_count": message_count,
        "workspace_folder_present": bool(safe_str(payload.get("workspace_folder_id"))),
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
    message_sources: Mapping[Any, Any] | None = None,
    count_tokens_func: Callable[[list[dict[str, Any]], str], int] | None = None,
) -> dict[str, Any]:
    messages = [message for message in prompt_messages if isinstance(message, Mapping)]
    final_response_lock = _final_response_lock_payload(assistant_response_override)
    conversation_state = _conversation_state(conversation, turn_id)
    lane_statuses = build_lane_statuses(
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
    )
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
        "messages": build_messages_manifest(
            messages,
            web_runtime_payload=web_runtime_payload,
            assistant_output_policy=assistant_output_policy,
            identity_roles_present=identity_roles_present(lane_statuses),
            message_sources=message_sources,
            model=runtime_main_model,
            count_tokens_func=count_tokens_func,
        ),
        "lane_statuses": lane_statuses,
        "windows": build_messages_windows(
            messages=messages,
            conversation=conversation,
            recent_context_payload=recent_context_payload,
            recent_window_payload=recent_window_payload,
            biblio_recent_dialogue=biblio_recent_dialogue,
            agenda_recent_dialogue=agenda_recent_dialogue,
        ),
        "budgets": {
            "prompt": build_prompt_budget(
                prompt_messages=messages,
                runtime_main_model=runtime_main_model,
                count_tokens_func=count_tokens_func,
                max_tokens=safe_int(max_tokens),
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
    return bool(emitter(OBSERVABILITY_STAGE, status=STATUS_OK, payload=payload))
