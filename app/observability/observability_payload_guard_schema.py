from __future__ import annotations

import re
from typing import Any, Mapping


_SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,159}$")
_SAFE_CLASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,159}$")
_SAFE_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$")
_SAFE_TITLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./_-]{0,159}$")
_SAFE_TIMEZONE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_./+-]{0,79}$")
_SAFE_TIMESTAMP_CHARS = set("0123456789T:+-.Z")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")
_SAFE_LANE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,79}$")

_QUALIFIED_RAW_FLAGS = set(
    """
    raw_content_included raw_content_stored raw_error_message_included raw_error_message_stored
    raw_event_payloads_included raw_lane_content_included raw_log_included raw_message_included
    raw_passage_included raw_policy_text_included raw_prompt_included
    raw_provider_payload_included raw_query_included raw_catalogue_payload_included
    raw_locator_included raw_secret_included raw_webdav_payload_included raw_capsule_content_included
    """.split()
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

_GENERAL_TEXT_KEYS = set(
    """
    activation_mode agent_schema_version arbiter_status attempt_decision_source
    answer_mode
    basket_candidate_id_sha256_12 basket_status candidate_id_sha256_12 canonization_stage collection_path confirmation_level crawl_cache_mode crawl_fallback_reason crawl_filter
    crawl_filter_requested crawl_fallback_status crawl_policy_kind crawl_policy_reason
    crawl_primary_status crawl_status day_part_class decision_source dedup_reason_code
    calendar_ambiguity content_hash draft_title_hash
    apply_reason_code apply_status dominant_tone error_class error_code epistemic_regime execution_status fallback_source
    final_judgment_posture final_output_regime final_status guarded_original_status
    geste_dialogique_dominant hard_guard_effect injection_class
    fallback_reason finish_reason
    main_llm_reasoning_effort_effective main_llm_reasoning_effort_requested
    intent_hash json_hash kind main_llm_reasoning_policy_kind main_llm_reasoning_reason_code
    judge_reason_code judge_status last_agent_status legacy_writer_disabled_reason method_family
    mode model module_key mutation_kind node_stage node_state_read_reason_code node_state_schema_version
    node_state_write_reason_code node_state_sha256_12 openrouter_fallback_state origin origin_stage payload_kind policy
    operation pending_action_hash pending_action_id pending_confirmation_level pending_execution_reason_code pending_execution_status
    pending_expires_at pending_operation pending_status persistence_mode
    persist_phase
    primary_read_filter primary_read_status primary_source_kind profile_policy_kind
    profile_policy_mode profile_source_evidence_policy_kind prompt_kind provider provider_caller
    ancrage_temporel portee_temporelle provider_generation_id provider_model provider_role provider_title product_case_id product_method
    product_truth projected_judgment_posture
    proof_regime principe query_kind query_plan_kind query_preview read_state reason_code reason_short
    read_execution_reason_code read_execution_status regime_de_vigilance runtime_pipeline
    reason_sha256_12 retrieval_error_class retrieval_error_code retrieval_status rerank_profile rerank_policy
    schema_version scope search_profile searxng_language searxng_profile_params_kind
    searxng_profile_params_policy searxng_safesearch searxng_time_range
    searxng_soft_signal_policy source source_domain source_first_authority source_first_policy_kind
    shift_state source_first_product source_kind source_origin stability status status_schema_version summary_id_sha256_12 summary_usage used_content_kind
    surface_error_hash surface_intro_hash surface_outro_hash
    subject target_side target_verification_error_class time_ambiguity time_kind timezone
    timezone tone upstream_output_regime_proposed upstream_recommendation_posture
    updated_by updated_ts user_display_name_hash user_message_hash validation_decision validation_status web_confidence_level web_confidence_policy_kind web_discovery_external_error_kind
    web_discovery_external_provider web_discovery_provider web_discovery_provider_effective
    web_discovery_provider_requested web_evidence_policy_kind web_evidence_status
    web_evidence_url_request_policy web_pdf_read_reason_code web_pdf_read_status
    continuity_kind verdict window_end window_start write_effect write_error_class write_execution_reason_code write_execution_status write_mode
    """.split()
)
_GENERAL_SCALAR_KEYS = set(
    """
    adobe_mode_active chars context_injected crawl_fallback_used crawl4ai_query_hash_count
    crawl4ai_query_hashes_included current_user_hash_included current_user_present
    current_user_retained enabled explicit_url_chars explicit_url_detected explicit_url_included
    auto_canonization_suspended buffer_cleared buffer_frozen fail_open fallback_deterministic fallback_used final_response_lock final_response_lock_present
    has_in_progress_turn injected insertion_point_reached is_primary_source last_assistant_retained
    invalid_status_redacted
    main_llm_payload main_model_called model_called mutation_attempted mutation_requested ok
    present primary_read_attempted primary_read_raw_fallback_used prompt_lane_injected
    openrouter_fallback_used primary_query_hash_included primary_read_attempted
    primary_read_raw_fallback_used provider_title_chars provider_title_included provider_title_present
    profile_insufficient_evidence query_hash_included rank reason_code_present rejected_payload
    rerank_applied secondary_provider_payload secondary_query_hash_count secondary_query_hashes_included
    score_first_writer_enabled selected shadow_mode source_first_active
    stream_requested system_prompt_hash_included system_prompt_present timeout_s top_k_requested top_k_returned truncated turns_considered used
    used_for_response used_in_prompt validated validated_plan_present
    web_discovery_external_used
    web_confidence_score web_evidence_can_answer web_evidence_can_suggest_reformulation
    web_evidence_external_fallback_used web_evidence_requires_caveat web_search_enabled
    web_search_requested
    agent_json_validated ambiguous arbiter_followed_upstream available buffer_target_pairs caldav_access catalog_saved confirmation_required
    confidence content_free conversation_saved draft_description_present draft_present draft_private fallback family_calendar
    has_in_progress_turn legacy_writer_disabled messages_saved mutable_len nextcloud_access now_iso_present
    node_state_read_present node_state_read_valid node_state_write_attempted node_state_write_changed
    node_state_sha256_12 node_state_write_succeeded main_llm_reasoning_hidden max_recent_turns messages_written
    raw_candidates ranking_available rejected_candidates response_chars runtime_available secret_access state_used strength
    active_document anythingllm final_response_override hermeneutic identity memory_rag ocr_active_documents
    in_prompt kept_candidates raw_catalogue_payload_included raw_locator_included raw_passage_included raw_query_included
    candidate_top_score cancelled expired pending_action_present pending_cancelled pending_expired pending_execution_attempted pending_target_clear
    read_execution_attempted redacted secret_included score_gap status_code summary summary_generation_observed target_clear top_score fallback_decisions
    user_display_name_present web workspace write_execution_attempted writes_applied
    """.split()
)
_GENERAL_CONTAINER_KEYS = {
    "active_tones",
    "agent",
    "actions_count",
    "advisory_recommendations_followed",
    "advisory_recommendations_overridden",
    "applied_hard_guards",
    "arbiter",
    "basket",
    "basket_candidates",
    "by_provider_caller",
    "canonical_inputs",
    "client",
    "counts",
    "boundaries",
    "crawl4ai_cache_modes",
    "crawl4ai_extraction_summary",
    "crawl4ai_filter_counts",
    "confidence",
    "duration_ms",
    "extractor",
    "frida",
    "hard_guard",
    "hermeneutic_prompt_injection",
    "identity",
    "identity_prompt_injection",
    "injection",
    "inputs",
    "issue_classes",
    "items",
    "lane",
    "librarian_agent",
    "llm",
    "message_role_counts",
    "model",
    "memory_arbitration",
    "memory_chain_snapshot",
    "memory_prompt_injection",
    "memory_retrieval",
    "memory_retrieved",
    "nested_counts",
    "passage_search",
    "parent_summaries_injected",
    "outcomes",
    "pending_execution",
    "pending_state",
    "plan",
    "promotions",
    "primary_node",
    "provider_messages",
    "providers",
    "qualification_temporelle",
    "recent_context",
    "recent_window",
    "read_execution",
    "write_execution",
    "profile_source_domain_counts",
    "raw_flags",
    "reason_code_counts",
    "rejection_reasons",
    "redaction",
    "regime_probatoire",
    "resolver",
    "retrieval",
    "retrieved_candidates",
    "rerank_reason_counts",
    "sampling",
    "source_material_summary",
    "state",
    "state_transition",
    "static",
    "stimmung",
    "subjects",
    "summary",
    "theme_query_signal",
    "time",
    "tones",
    "status_schema",
    "tool_names",
    "user",
    "user_turn",
    "user_turn_signals",
    "validation_dialogue_context",
    "request",
    "validation",
    "final_response",
    "draft_summary",
    "mutable",
    "web",
    "web_confidence_inputs_summary",
    "web_evidence_inputs_summary",
    "web_pdf_read_status_counts",
    "web_pdf_read_summary",
    "work_query_signal",
}
_GENERAL_SAFE_TEXT_LIST_KEYS = {
    "active_signal_families",
    "advisory_recommendations_followed",
    "advisory_recommendations_overridden",
    "applied_hard_guards",
    "candidate_id_hashes",
    "doc_id_shorts",
    "crawl4ai_policy_kinds",
    "endpoint_kinds",
    "hashes",
    "injected_candidate_id_hashes",
    "injected_candidate_ids",
    "injected_candidate_id_sha256_12",
    "injection_lanes",
    "input_keys",
    "issue_classes",
    "canonical_time_window_keys",
    "draft_field_names",
    "openrouter_fallback_reason_codes",
    "pipeline_directives_final",
    "positions",
    "profile_downrank_domains",
    "profile_expected_domains",
    "profile_insufficient_evidence_reason_codes",
    "profile_policy_reason_codes",
    "profile_secondary_domains",
    "profile_situated_secondary_domains",
    "reason_codes",
    "calendar_id_hashes",
    "continuity_kinds",
    "event_id_hashes",
    "pending_action_hashes",
    "read_calendar_id_hashes",
    "read_event_id_hashes",
    "read_tool_names",
    "rerank_top_domains_after",
    "rerank_top_domains_before",
    "searxng_categories",
    "searxng_engines",
    "searxng_hard_parameters",
    "searxng_params_reason_codes",
    "selection_reason_codes",
    "source_first_probable_domains",
    "source_first_reason_codes",
    "subjects_seen",
    "subjects_touched",
    "source_candidate_id_sha256_12",
    "pending_risk_flags",
    "recent_turn_hashes",
    "risk_flags",
    "target_verification_tool_names",
    "tool_names",
    "types_de_preuve_attendus",
    "upstream_active_signal_families",
    "used_content_kinds",
    "provenances",
    "web_confidence_reason_codes",
    "web_discovery_reason_codes",
    "web_evidence_guidance_codes",
    "web_evidence_reason_codes",
    "web_pdf_read_reason_codes",
    "write_http_status_codes",
    "write_method_names",
}


def _is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("schema_version") or "").strip() == "main_payload_manifest_v1"


def _is_metric_like_key(key: str) -> bool:
    lower = key.lower()
    if lower in {"max_tokens", "raw_candidates", "temperature", "top_p"}:
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
            "_injected",
            "_index",
            "_len",
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
    if lower in {
        "identity_block_sha256_12",
        "update_reason_sha256_12",
    }:
        return "identity_text_hash_key"
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
    if lower == "caldav_access":
        return ""
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
    if lower == "provider_title":
        return bool(_SAFE_TITLE_RE.fullmatch(text))
    if lower == "timezone":
        return bool(_SAFE_TIMEZONE_RE.fullmatch(text))
    if lower in {"window_start", "window_end", "pending_expires_at", "updated_ts"}:
        return all(char in _SAFE_TIMESTAMP_CHARS for char in text)
    if lower.endswith("_class") or lower.endswith("_language"):
        return bool(_SAFE_CLASS_RE.fullmatch(text))
    return _is_safe_code_text(value, allow_empty=True, allow_model=lower in {"model", "provider_model"})


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
