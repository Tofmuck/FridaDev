from __future__ import annotations

import re
from typing import Any, Mapping


_SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,159}$")
_SAFE_CLASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,159}$")
_SAFE_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")
_SAFE_LANE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,79}$")

_QUALIFIED_RAW_FLAGS = set(
    """
    raw_content_included raw_content_stored raw_error_message_included raw_error_message_stored
    raw_event_payloads_included raw_lane_content_included raw_log_included raw_message_included
    raw_policy_text_included raw_prompt_included raw_provider_payload_included raw_secret_included
    raw_webdav_payload_included
    """.split()
)

_MANIFEST_RAW_FLAGS = {
    "raw_prompt_included",
    "raw_message_included",
    "raw_content_included",
    "raw_lane_content_included",
    "raw_provider_payload_included",
    "raw_secret_included",
}

_DANGEROUS_EXACT_KEYS = set(
    """
    authorization base64 content cookie data_url dav etag header image_data_url message messages password
    path payload prompt provider_payload raw raw_payload secret text token url xml
    """.split()
)
_DANGEROUS_PAYLOAD_KEYS = {"provider_payload", "raw_payload", "request_payload", "response_payload"}

_MANIFEST_TOP_LEVEL_KEYS = set(
    """
    assistant_output_policy budgets conversation_id_present conversation_state final_response_lock hash_policy
    lane_statuses main_model_called messages provider raw_flags runtime_settings schema_version scope
    status_schema_version turn_id_present windows
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
    query_kind raw_lane_content_included reason_code reason_codes selected source_count status
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
_CONVERSATION_STATE_KEYS = {
    "conversation_id_present",
    "conversation_message_count",
    "conversation_state_kind",
    "turn_id_present",
    "workspace_folder_present",
}
_HASH_POLICY_KEYS = {"fingerprints_included", "policy", "short_stable_text_hashes_included", "stable_text_hashes_included"}
_BUDGETS_KEYS = {"prompt"}
_PROMPT_BUDGET_KEYS = {"content_chars_total", "estimated_prompt_tokens", "max_completion_tokens", "message_count"}
_WINDOWS_KEYS = {
    "agenda_recent_dialogue",
    "biblio_recent_dialogue",
    "conversation",
    "prompt_final",
    "recent_context",
    "recent_window",
}
_WINDOW_KEYS_BY_CONTEXT = {
    "agenda_recent_dialogue": {"message_count"},
    "biblio_recent_dialogue": {"message_count"},
    "conversation": {"assistant_message_count", "message_count", "user_message_count"},
    "prompt_final": {"message_count", "provider_role_sequence"},
    "recent_context": {"message_count"},
    "recent_window": {"has_in_progress_turn", "max_recent_turns", "turn_count"},
}
_MANIFEST_CONTEXT_KEYS = {
    "top": _MANIFEST_TOP_LEVEL_KEYS,
    "message": _MANIFEST_MESSAGE_KEYS,
    "lane_status": _MANIFEST_LANE_STATUS_KEYS,
    "raw_flags": _MANIFEST_RAW_FLAGS,
    "runtime_settings": _RUNTIME_SETTINGS_KEYS,
    "assistant_output_policy": _ASSISTANT_OUTPUT_POLICY_KEYS,
    "final_response_lock": _FINAL_RESPONSE_LOCK_KEYS,
    "conversation_state": _CONVERSATION_STATE_KEYS,
    "hash_policy": _HASH_POLICY_KEYS,
    "budgets": _BUDGETS_KEYS,
    "budget_prompt": _PROMPT_BUDGET_KEYS,
    "windows": _WINDOWS_KEYS,
}
_MANIFEST_SAFE_TEXT_KEYS = set(
    """
    activation_mode content_kind conversation_state_kind exclusion_reason_code mode model origin origin_stage
    policy priority_policy provider provider_family provider_role query_kind reason_code schema_version
    scope source status status_schema_version
    """.split()
)
_MANIFEST_TEXT_LIST_KEYS = {"exclusion_reason_codes", "logical_roles", "provider_role_sequence", "reason_codes"}
_MANIFEST_DYNAMIC_INT_MAP_KEYS = {"budget", "media_kind_counts"}

_GENERAL_TEXT_KEYS = set(
    """
    activation_mode collection_path crawl_cache_mode crawl_fallback_reason crawl_filter
    crawl_filter_requested crawl_fallback_status crawl_policy_kind crawl_policy_reason
    crawl_primary_status crawl_status error_class error_code final_status guarded_original_status
    mode model openrouter_fallback_state origin origin_stage payload_kind policy
    primary_read_filter primary_read_status primary_source_kind profile_policy_kind
    profile_policy_mode profile_source_evidence_policy_kind prompt_kind provider provider_caller
    provider_role query_kind query_plan_kind query_preview read_state reason_code reason_short
    retrieval_error_class retrieval_error_code retrieval_status rerank_profile rerank_policy
    schema_version scope search_profile searxng_language searxng_profile_params_kind
    searxng_profile_params_policy searxng_safesearch searxng_time_range
    searxng_soft_signal_policy source source_domain source_first_authority source_first_policy_kind
    source_first_product source_kind source_origin status status_schema_version used_content_kind
    web_confidence_level web_confidence_policy_kind web_discovery_external_error_kind
    web_discovery_external_provider web_discovery_provider web_discovery_provider_effective
    web_discovery_provider_requested web_evidence_policy_kind web_evidence_status
    web_evidence_url_request_policy web_pdf_read_reason_code web_pdf_read_status
    write_effect write_mode
    """.split()
)
_GENERAL_SCALAR_KEYS = set(
    """
    adobe_mode_active chars context_injected crawl_fallback_used crawl4ai_query_hash_count
    crawl4ai_query_hashes_included current_user_hash_included current_user_present enabled
    explicit_url_chars explicit_url_detected explicit_url_included fallback_used final_response_lock_present
    has_in_progress_turn is_primary_source main_llm_payload main_model_called model_called ok
    openrouter_fallback_used primary_query_hash_included primary_read_attempted
    primary_read_raw_fallback_used provider_title_chars provider_title_included provider_title_present
    profile_insufficient_evidence query_hash_included rank reason_code_present rejected_payload
    rerank_applied secondary_provider_payload secondary_query_hash_count secondary_query_hashes_included
    selected source_first_active
    stream_requested system_prompt_hash_included system_prompt_present timeout_s truncated used_in_prompt
    web_discovery_external_used
    web_confidence_score web_evidence_can_answer web_evidence_can_suggest_reformulation
    web_evidence_external_fallback_used web_evidence_requires_caveat web_search_enabled
    web_search_requested
    """.split()
)
_GENERAL_CONTAINER_KEYS = {
    "actions_count",
    "by_provider_caller",
    "counts",
    "crawl4ai_cache_modes",
    "crawl4ai_extraction_summary",
    "crawl4ai_filter_counts",
    "duration_ms",
    "issue_classes",
    "message_role_counts",
    "nested_counts",
    "providers",
    "profile_source_domain_counts",
    "raw_flags",
    "redaction",
    "rerank_reason_counts",
    "sampling",
    "source_material_summary",
    "status_schema",
    "web_confidence_inputs_summary",
    "web_evidence_inputs_summary",
    "web_pdf_read_status_counts",
    "web_pdf_read_summary",
}
_GENERAL_SAFE_TEXT_LIST_KEYS = {
    "crawl4ai_policy_kinds",
    "issue_classes",
    "openrouter_fallback_reason_codes",
    "profile_downrank_domains",
    "profile_expected_domains",
    "profile_insufficient_evidence_reason_codes",
    "profile_policy_reason_codes",
    "profile_secondary_domains",
    "profile_situated_secondary_domains",
    "reason_codes",
    "rerank_top_domains_after",
    "rerank_top_domains_before",
    "searxng_categories",
    "searxng_engines",
    "searxng_hard_parameters",
    "searxng_params_reason_codes",
    "source_first_probable_domains",
    "source_first_reason_codes",
    "used_content_kinds",
    "web_confidence_reason_codes",
    "web_discovery_reason_codes",
    "web_evidence_guidance_codes",
    "web_evidence_reason_codes",
    "web_pdf_read_reason_codes",
}


def _is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("schema_version") or "").strip() == "main_payload_manifest_v1"


def _is_metric_like_key(key: str) -> bool:
    lower = key.lower()
    if lower in {"max_tokens", "temperature", "top_p"}:
        return True
    return lower.endswith(
        (
            "_bytes",
            "_budget",
            "_chars",
            "_chars_total",
            "_count",
            "_counts",
            "_duration_ms",
            "_hash",
            "_hashes",
            "_id",
            "_ids",
            "_included",
            "_index",
            "_limit",
            "_ms",
            "_present",
            "_ref",
            "_refs",
            "_seen",
            "_sha256_12",
            "_target_s",
            "_truncated",
            "_exceeded",
            "_tokens",
            "_used",
        )
    )


def _dangerous_key_class(key: str) -> str:
    lower = key.lower()
    if lower in _QUALIFIED_RAW_FLAGS:
        return ""
    if lower in _DANGEROUS_EXACT_KEYS:
        return f"{lower}_key"
    if lower in _DANGEROUS_PAYLOAD_KEYS:
        return "payload_key"
    if lower == "collection_path":
        return ""
    if lower.startswith("raw_") and not _is_metric_like_key(lower):
        return "raw_key"
    if "api_key" in lower or "api-key" in lower:
        return "credential_key"
    if lower.endswith(("_password", "_secret", "_cookie", "_authorization", "_header")):
        return "credential_key"
    if lower.endswith("_token") and not lower.endswith("_tokens"):
        return "credential_key"
    if (
        "payload" in lower
        and not _is_metric_like_key(lower)
        and lower not in {"main_llm_payload", "payload_kind", "rejected_payload", "secondary_provider_payload"}
    ):
        return "payload_key"
    if "dav" in lower and not _is_metric_like_key(lower):
        return "dav_key"
    if "xml" in lower and not _is_metric_like_key(lower):
        return "xml_key"
    if "etag" in lower and not lower.endswith(("_hash", "_present")):
        return "etag_key"
    if lower.endswith("_url") and not lower.endswith(("_url_hash", "_url_sha256_12")):
        return "url_key"
    if lower.endswith("_path") and not lower.endswith(("_path_hash", "_path_count")):
        return "path_key"
    return ""


def _dangerous_value_class(key: str, value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    lower = text.lower()
    if key.lower() == "model" and bool(_SAFE_MODEL_RE.fullmatch(text) or _SAFE_CODE_RE.fullmatch(text)):
        return ""
    if lower.startswith("data:") or "base64," in lower:
        return "data_url_value"
    if _BASE64_RE.fullmatch(text):
        return "base64_value"
    if "://" in lower or lower.startswith(("http:", "https:", "www.")):
        return "url_value"
    if lower.startswith(("dav:", "xml:", "<?xml")) or "</" in lower:
        return "xml_or_dav_value"
    if lower.startswith("/") or lower.startswith("\\\\") or lower.startswith("~"):
        return "path_value"
    if any(marker in lower for marker in ("authorization:", "bearer ", "set-cookie:", "cookie:")):
        return "credential_value"
    if any(marker in lower for marker in ("api_key=", "api-key=", "password=", "secret=", "token=")):
        return "credential_value"
    if lower.startswith("etag:") or lower.startswith("if-match:") or lower.startswith("if-none-match:"):
        return "etag_value"
    if any(part in lower for part in ("webdav", "caldav")):
        return "dav_value"
    if any(char in text for char in ("\r", "\n", "<", ">")):
        return "raw_text_value"
    return ""


def _is_safe_code_text(value: Any, *, allow_empty: bool = True, allow_model: bool = False) -> bool:
    text = str(value or "").strip()
    if not text:
        return bool(allow_empty)
    if allow_model and _SAFE_MODEL_RE.fullmatch(text):
        return True
    return bool(_SAFE_CODE_RE.fullmatch(text))


def _is_safe_general_text_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_TEXT_KEYS


def _is_safe_general_text_value(key: str, value: Any) -> bool:
    lower = key.lower()
    text = str(value or "").strip()
    if lower.endswith("_preview"):
        return text == ""
    if not text:
        return True
    if lower.endswith("_class") or lower.endswith("_language"):
        return bool(_SAFE_CLASS_RE.fullmatch(text))
    return _is_safe_code_text(value, allow_empty=True, allow_model=lower == "model")


def _is_safe_general_scalar_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_SCALAR_KEYS or _is_metric_like_key(lower)


def _is_safe_general_container_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_CONTAINER_KEYS or lower.endswith(("_counts", "_metrics", "_by_stage", "_by_provider_caller"))


def _is_safe_manifest_text_value(key: str, value: Any) -> bool:
    return _is_safe_code_text(value, allow_empty=True, allow_model=key.lower() == "model")


def _safe_dynamic_name(value: Any) -> bool:
    return bool(_SAFE_LANE_NAME_RE.fullmatch(str(value or "").strip()))


def _is_manifest_bool_key(key: str) -> bool:
    return key in {
        "allow_code",
        "allow_structure",
        "content_present",
        "context_injected",
        "conversation_id_present",
        "enabled",
        "excluded",
        "final_response_lock_present",
        "fingerprints_included",
        "has_in_progress_turn",
        "main_model_bypassed",
        "main_model_called",
        "model_called",
        "present",
        "raw_content_included",
        "raw_lane_content_included",
        "raw_policy_text_included",
        "selected",
        "short_stable_text_hashes_included",
        "stable_text_hashes_included",
        "stream_requested",
        "temperature_present",
        "top_p_present",
        "turn_id_present",
        "workspace_folder_present",
    }


def _is_manifest_number_key(key: str) -> bool:
    return key in {
        "assistant_message_count",
        "content_chars_total",
        "estimated_prompt_tokens",
        "index",
        "max_completion_tokens",
        "max_recent_turns",
        "max_tokens",
        "message_count",
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
        "final_response_lock",
        "hash_policy",
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
