from __future__ import annotations

from typing import Any, Mapping

from observability.observability_payload_guard_safe_code_policy import (
    _is_metric_like_key,
    _is_safe_code_text,
    _is_safe_lane_name,
)


_MANIFEST_RAW_FLAGS = {
    "raw_prompt_included",
    "raw_message_included",
    "raw_content_included",
    "raw_lane_content_included",
    "raw_capsule_content_included",
    "raw_provider_payload_included",
    "raw_secret_included",
}

_MANIFEST_TOP_LEVEL_KEYS = set(
    """
    assistant_output_policy budgets conversation_id_present conversation_state final_response_lock hash_policy
    lane_conflicts lane_statuses main_model_called messages provider raw_flags runtime_settings schema_version scope
    status_schema_version turn_id_present windows continuity_capsule
    """.split()
)
_MANIFEST_MESSAGE_KEYS = set(
    """
    content_chars content_kind content_parts_count content_present estimated_tokens excluded
    exclusion_reason_code file_part_count image_part_count index logical_roles origin origin_stage
    provider_role raw_content_included text_part_count
    """.split()
)
_MANIFEST_LANE_STATUS_KEYS = set(
    """
    activation_mode budget content_chars context_hint_count context_injected enabled estimated_tokens
    excluded_count exclusion_reason_codes final_response_lock_present injected_count input_count
    invalid_requested_count media_kind_counts mode model_called origin over_limit_count passage_count
    priority_policy query_kind raw_lane_content_included reason_code reason_codes selected source_count status
    final_response_lock_selected final_response_lock_suppressed version raw_capsule_content_included fingerprint_included
    """.split()
)
_RUNTIME_SETTINGS_KEYS = {"max_tokens", "model", "provider_family", "stream_requested", "temperature_present", "top_p_present"}
_ASSISTANT_OUTPUT_POLICY_KEYS = {"allow_code", "allow_structure", "present", "raw_policy_text_included"}
_FINAL_RESPONSE_LOCK_KEYS = {
    "content_chars",
    "content_present",
    "main_model_bypassed",
    "present",
    "priority_policy",
    "raw_content_included",
    "reason_code",
    "source",
}
_LANE_CONFLICT_KEYS = {
    "agenda_lock_present",
    "agenda_selected",
    "biblio_lock_present",
    "biblio_selected",
    "candidate_count",
    "candidate_sources",
    "conflict_present",
    "implicit_injection_detected",
    "main_model_bypassed",
    "message_lane_block_count",
    "message_lane_status_mismatch_count",
    "priority_policy",
    "raw_content_included",
    "reason_code",
    "selected_lane_count",
    "selected_source",
    "status",
    "suppressed_count",
    "suppressed_source",
}
_CONVERSATION_STATE_KEYS = {
    "conversation_id_present",
    "conversation_message_count",
    "conversation_state_kind",
    "turn_id_present",
    "workspace_folder_present",
}
_HASH_POLICY_KEYS = {"fingerprints_included", "policy", "short_stable_text_hashes_included", "stable_text_hashes_included"}
_CONTINUITY_CAPSULE_KEYS = {
    "content_chars",
    "enabled",
    "fingerprint_included",
    "injected_count",
    "max_chars",
    "present",
    "raw_capsule_content_included",
    "raw_content_included",
    "raw_prompt_included",
    "reason_code",
    "status",
    "version",
}
_BUDGETS_KEYS = {"prompt"}
_PROMPT_BUDGET_KEYS = {
    "content_chars_total",
    "dialogue_messages_truncated",
    "estimated_prompt_tokens",
    "excluded_count",
    "max_completion_tokens",
    "message_count",
    "prompt_soft_limit_exceeded",
    "prompt_soft_token_limit",
    "soft_limit_configured",
    "soft_limit_policy",
    "soft_limit_reason_code",
    "soft_limit_stage",
    "truncated_count",
}
_WINDOWS_KEYS = {
    "agenda_recent_dialogue",
    "biblio_recent_dialogue",
    "conversation",
    "hermeneutic_node",
    "identity_staging",
    "memory",
    "prompt_final",
    "recent_context",
    "recent_window",
    "summary",
}
_WINDOW_COMMON_KEYS = {
    "enabled",
    "origin_stage",
    "raw_content_included",
    "reason_code",
    "selected",
    "source",
    "status",
}
_WINDOW_KEYS_BY_CONTEXT = {
    "agenda_recent_dialogue": _WINDOW_COMMON_KEYS
    | {"content_chars", "final_response_lock_present", "max_messages", "message_count", "model_called"},
    "biblio_recent_dialogue": _WINDOW_COMMON_KEYS
    | {"content_chars", "final_response_lock_present", "max_messages", "message_count"},
    "conversation": _WINDOW_COMMON_KEYS
    | {"assistant_message_count", "content_chars", "message_count", "user_message_count"},
    "hermeneutic_node": _WINDOW_COMMON_KEYS
    | {
        "judgment_block_chars",
        "judgment_block_present",
        "primary_payload_present",
        "validated_result_present",
    },
    "identity_staging": _WINDOW_COMMON_KEYS
    | {"canonization_stage", "canonized_into_prompt", "staging_scope"},
    "memory": _WINDOW_COMMON_KEYS
    | {
        "arbiter_controls_injection",
        "arbiter_decisions_count",
        "arbiter_kept_count",
        "arbiter_observed_count",
        "arbiter_rejected_count",
        "basket_candidates_count",
        "content_chars",
        "context_hint_count",
        "current_mode",
        "injection_source",
        "prompt_injected_count",
        "retrieval_reason_code",
        "retrieval_status",
        "retrieved_count",
        "top_k_requested",
    },
    "prompt_final": _WINDOW_COMMON_KEYS
    | {"content_chars", "estimated_tokens", "message_count", "provider_role_sequence"},
    "recent_context": _WINDOW_COMMON_KEYS
    | {"assistant_message_count", "content_chars", "message_count", "user_message_count"},
    "recent_window": _WINDOW_COMMON_KEYS
    | {
        "assistant_only_turn_count",
        "complete_turn_count",
        "content_chars",
        "has_in_progress_turn",
        "in_progress_turn_count",
        "max_recent_turns",
        "message_count",
        "turn_count",
    },
    "summary": _WINDOW_COMMON_KEYS
    | {
        "content_chars",
        "period_end_present",
        "period_start_present",
        "summary_present",
        "voice_continuity_reason_code",
        "voice_continuity_status",
    },
}
_MANIFEST_CONTEXT_KEYS = {
    "top": _MANIFEST_TOP_LEVEL_KEYS,
    "message": _MANIFEST_MESSAGE_KEYS,
    "lane_status": _MANIFEST_LANE_STATUS_KEYS,
    "raw_flags": _MANIFEST_RAW_FLAGS,
    "runtime_settings": _RUNTIME_SETTINGS_KEYS,
    "assistant_output_policy": _ASSISTANT_OUTPUT_POLICY_KEYS,
    "final_response_lock": _FINAL_RESPONSE_LOCK_KEYS,
    "lane_conflicts": _LANE_CONFLICT_KEYS,
    "conversation_state": _CONVERSATION_STATE_KEYS,
    "hash_policy": _HASH_POLICY_KEYS,
    "continuity_capsule": _CONTINUITY_CAPSULE_KEYS,
    "budgets": _BUDGETS_KEYS,
    "budget_prompt": _PROMPT_BUDGET_KEYS,
    "windows": _WINDOWS_KEYS,
}
_MANIFEST_SAFE_TEXT_KEYS = set(
    """
    activation_mode canonization_stage content_kind conversation_state_kind current_mode
    exclusion_reason_code injection_source mode model origin origin_stage policy priority_policy
    provider provider_family provider_role query_kind reason_code retrieval_reason_code retrieval_status
    schema_version scope selected_source soft_limit_policy soft_limit_reason_code soft_limit_stage source staging_scope suppressed_source
    status status_schema_version voice_continuity_reason_code voice_continuity_status version
    """.split()
)
_MANIFEST_TEXT_LIST_KEYS = {
    "candidate_sources",
    "exclusion_reason_codes",
    "logical_roles",
    "provider_role_sequence",
    "reason_codes",
}
_MANIFEST_DYNAMIC_INT_MAP_KEYS = {"budget", "media_kind_counts"}


def _is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("schema_version") or "").strip() == "main_payload_manifest_v1"


def _is_safe_manifest_text_value(key: str, value: Any) -> bool:
    return _is_safe_code_text(value, allow_empty=True, allow_model=key.lower() == "model")


def _safe_dynamic_name(value: Any) -> bool:
    return _is_safe_lane_name(value)


def _is_manifest_bool_key(key: str) -> bool:
    return key in {
        "allow_code",
        "allow_structure",
        "content_present",
        "context_injected",
        "arbiter_controls_injection",
        "agenda_lock_present",
        "agenda_selected",
        "biblio_lock_present",
        "biblio_selected",
        "canonized_into_prompt",
        "conversation_id_present",
        "dialogue_messages_truncated",
        "enabled",
        "excluded",
        "conflict_present",
        "final_response_lock_present",
        "final_response_lock_selected",
        "final_response_lock_suppressed",
        "fingerprint_included",
        "fingerprints_included",
        "has_in_progress_turn",
        "implicit_injection_detected",
        "judgment_block_present",
        "main_model_bypassed",
        "main_model_called",
        "model_called",
        "period_end_present",
        "period_start_present",
        "present",
        "primary_payload_present",
        "raw_content_included",
        "raw_capsule_content_included",
        "raw_lane_content_included",
        "raw_policy_text_included",
        "selected",
        "short_stable_text_hashes_included",
        "soft_limit_configured",
        "stable_text_hashes_included",
        "stream_requested",
        "summary_present",
        "temperature_present",
        "top_p_present",
        "turn_id_present",
        "prompt_soft_limit_exceeded",
        "validated_result_present",
        "workspace_folder_present",
    }


def _is_manifest_number_key(key: str) -> bool:
    return key in {
        "assistant_message_count",
        "content_chars_total",
        "estimated_prompt_tokens",
        "index",
        "max_completion_tokens",
        "max_messages",
        "max_recent_turns",
        "max_tokens",
        "message_count",
        "top_k_requested",
        "turn_count",
        "user_message_count",
    } or _is_metric_like_key(key)


def _manifest_allowed_keys(context: str) -> set[str]:
    if context.startswith("window:"):
        return _WINDOW_KEYS_BY_CONTEXT.get(context.split(":", 1)[1], set())
    return _MANIFEST_CONTEXT_KEYS.get(context, set())


def _manifest_child_context(context: str, key: str) -> str:
    if context == "top" and key in {
        "assistant_output_policy",
        "budgets",
        "conversation_state",
        "continuity_capsule",
        "final_response_lock",
        "hash_policy",
        "lane_conflicts",
        "raw_flags",
        "runtime_settings",
        "windows",
    }:
        return key
    if context == "top" and key == "lane_statuses":
        return "lane_statuses"
    if context == "budgets" and key == "prompt":
        return "budget_prompt"
    if context == "windows" and key in _WINDOWS_KEYS:
        return f"window:{key}"
    if context == "lane_status" and key in _MANIFEST_DYNAMIC_INT_MAP_KEYS:
        return "manifest_dynamic_int_map"
    return ""
