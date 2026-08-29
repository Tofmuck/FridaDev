from __future__ import annotations

from typing import Any

from observability.observability_payload_guard_safe_code_policy import (
    _is_metric_like_key,
    _is_safe_class_text,
    _is_safe_code_text,
    _is_safe_extension_text,
    _is_safe_language_set_text,
    _is_safe_mime_text,
    _is_safe_timestamp_text,
    _is_safe_timezone_text,
    _is_safe_title_text,
)


_GENERAL_TEXT_KEYS = set(
    """
    activation_mode agent_schema_version arbiter_status attempt_decision_source
    answer_mode
    basket_candidate_id_sha256_12 basket_status candidate_id_sha256_12 canonization_stage collection_path confirmation_level crawl_cache_mode crawl_fallback_reason crawl_filter
    crawl_filter_requested crawl_fallback_status crawl_policy_kind crawl_policy_reason
    crawl_primary_status crawl_status day_part_class decision_source dedup_reason_code
    calendar_ambiguity content_hash draft_title_hash
    canonical_projection_version canonical_projection_contract_status stimmung_delivery_status stimmung_delivery_reason_code
    apply_reason_code apply_status dominant_tone error_class error_code epistemic_regime execution_status fallback_source
    final_judgment_posture final_output_regime final_status guarded_original_status
    validation_request_policy_version validation_transport validation_requested_model
    validation_attempt_decision_source validation_reasoning_effort_requested validation_reasoning_effort_effective
    failure_class recovery_action processing_state window_fingerprint next_window_progress
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
    shift_state source_first_product source_kind source_origin stability status status_schema_version stimmung_status summary_id summary_id_sha256_12 summary_usage used_content_kind
    surface_error_hash surface_intro_hash surface_outro_hash
    stream_terminal subject target_side target_verification_error_class time_ambiguity time_kind timezone
    timezone tone upstream_output_regime_proposed upstream_recommendation_posture
    updated_by updated_ts user_display_name_hash user_message_hash validation_decision validation_status web_confidence_level web_confidence_policy_kind web_discovery_external_error_kind
    web_discovery_external_provider web_discovery_provider web_discovery_provider_effective
    web_discovery_provider_requested web_evidence_policy_kind web_evidence_status
    web_evidence_url_request_policy web_pdf_read_reason_code web_pdf_read_status
    continuity_kind verdict window_end window_start write_effect write_error_class write_execution_reason_code write_execution_status write_mode
    content_sha256_12 decision document_id document_ref end_ts filename filename_ref media_kind media_type
    ocr_engine ocr_languages payload_order read_reason_code read_status source_extension start_ts text_sha256_12
    workspace_file_id workspace_folder_id
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
    attempt_current attempt_limit next_buffer_pairs_count writes_previously_applied
    hint_count identity_write mutable_authority max_items
    web_pdf_read_pages
    agent_json_validated ambiguous arbiter_followed_upstream available buffer_target_pairs caldav_access catalog_saved confirmation_required
    validation_reasoning_sent validation_reasoning_excluded validation_max_tokens_effective
    validation_temperature_sent validation_top_p_sent validation_provider_fallbacks_allowed validation_provider_require_parameters
    confidence content_free conversation_saved current_embedding_blocked current_embedding_calls
    current_embedding_reused dimensions draft_description_present draft_present draft_private embedding_calls_total fallback family_calendar
    has_in_progress_turn legacy_writer_disabled messages_saved mutable_len nextcloud_access now_iso_present
    node_state_read_present node_state_read_valid node_state_write_attempted node_state_write_changed
    node_state_sha256_12 node_state_write_succeeded main_llm_reasoning_hidden max_recent_turns messages_written
    open_conflict_skipped raw_candidates ranking_available rejected_candidates response_chars runtime_available same_content_skipped
    secret_access similarity_comparisons state_used stream_chunks strength
    active_document anythingllm final_response_override hermeneutic identity memory_rag ocr_active_documents
    in_prompt kept_candidates raw_catalogue_payload_included raw_locator_included raw_passage_included raw_query_included
    candidate_embedding_calls candidate_top_score cancelled conflicts_detected expired pending_action_present pending_cancelled pending_expired pending_execution_attempted pending_target_clear
    read_execution_attempted recent_has_in_progress_turn recent_max_turns redacted secret_included score_gap status_code summary summary_generation_observed target_clear top_score fallback_decisions
    user_display_name_present web workspace write_execution_attempted writes_applied
    active byte_size future_biblio_included image_height image_width ocr_applied ocr_duration_ms_total token_estimate
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
    "validation_request",
    "final_response",
    "draft_summary",
    "documents",
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
    "canonical_projection_included_families",
    "canonical_projection_omitted_families",
    "canonical_projection_no_data_families",
    "canonical_projection_redundant_families",
    "canonical_projection_optional_families",
    "canonical_projection_invalid_families",
    "canonical_projection_budget_exceeded_families",
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
    if lower in {"provider", "provider_title"}:
        return _is_safe_title_text(text)
    if lower == "filename":
        return len(text) <= 500 and not any(ord(char) < 32 for char in text)
    if lower == "media_type":
        return _is_safe_mime_text(text)
    if lower == "source_extension":
        return _is_safe_extension_text(text)
    if lower == "ocr_languages":
        return _is_safe_language_set_text(text)
    if lower == "timezone":
        return _is_safe_timezone_text(text)
    if lower in {"window_start", "window_end", "pending_expires_at", "updated_ts"}:
        return _is_safe_timestamp_text(text)
    if lower.endswith("_class") or lower.endswith("_language"):
        return _is_safe_class_text(text)
    return _is_safe_code_text(
        value,
        allow_empty=True,
        allow_model=lower in {"model", "provider_model", "validation_requested_model"},
    )


def _is_safe_general_scalar_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_SCALAR_KEYS or _is_metric_like_key(lower)


def _is_safe_general_container_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_CONTAINER_KEYS or lower.endswith(("_counts", "_metrics", "_by_stage", "_by_provider_caller"))
