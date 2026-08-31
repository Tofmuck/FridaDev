from __future__ import annotations

from typing import Any, Mapping, Sequence
from urllib.parse import urlparse

from core.hermeneutic_node.doctrine import epistemic_regime as epistemic_doctrine
from observability import chat_turn_logger


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _text(value: Any) -> str:
    return str(value or "").strip()


def _source_domain(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        parsed = urlparse(text if "://" in text else f"//{text}")
    except Exception:
        return ""
    return str(parsed.netloc or "").split("@")[-1].split(":")[0].lower()[:160]


def _redact_url_fields(payload: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(payload)
    url = str(source.pop("url", "") or "")
    source["source_domain"] = str(source.get("source_domain") or _source_domain(url) or "")
    source["url_present"] = bool(url)
    source["url_chars"] = len(url)
    source["url_included"] = False
    return source


def _bool_str(value: Any) -> bool:
    return bool(str(value or '').strip())


def _summarize_time(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'timezone': str(data.get('timezone') or ''),
        'day_part_class': str(data.get('day_part_class') or ''),
    }


def _summarize_memory_retrieved(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or ('ok' if data else 'missing')),
        'reason_code': str(data.get('reason_code') or ''),
        'error_code': str(data.get('error_code') or ''),
        'error_class': str(data.get('error_class') or ''),
        'retrieved_count': int(data.get('retrieved_count') or 0),
    }


def _summarize_memory_arbitration(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or 'missing'),
        'reason_code': str(data.get('reason_code') or ''),
        'decisions_count': int(data.get('decisions_count') or 0),
        'kept_count': int(data.get('kept_count') or 0),
        'rejected_count': int(data.get('rejected_count') or 0),
    }


def _summarize_summary(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'status': str(data.get('status') or 'missing'),
    }


def _side_summary(side_payload: Mapping[str, Any] | None) -> dict[str, Any]:
    side = _mapping(side_payload)
    static_payload = _mapping(side.get('static'))
    mutable_payload = _mapping(side.get('mutable'))
    mutable_content = _text(mutable_payload.get('content'))
    return {
        'static_present': _bool_str(static_payload.get('content')),
        'mutable_present': bool(mutable_content),
        'mutable_len': len(mutable_content),
    }


def _summarize_identity(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'frida': _side_summary(data.get('frida')),
        'user': _side_summary(data.get('user')),
    }


def _summarize_recent_context(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'messages_count': len(_sequence(data.get('messages'))),
    }


def _summarize_recent_window(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    return {
        'present': bool(data),
        'turn_count': int(data.get('turn_count') or 0),
        'has_in_progress_turn': bool(data.get('has_in_progress_turn', False)),
        'max_recent_turns': int(data.get('max_recent_turns') or 0),
    }


def _summarize_user_turn(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    regime = _mapping(data.get('regime_probatoire'))
    temporal = _mapping(data.get('qualification_temporelle'))
    return {
        'present': bool(data),
        'geste_dialogique_dominant': str(data.get('geste_dialogique_dominant') or ''),
        'regime_probatoire': {
            'principe': str(regime.get('principe') or ''),
            'types_de_preuve_attendus': [str(value) for value in _sequence(regime.get('types_de_preuve_attendus')) if str(value)],
            'provenances': [str(value) for value in _sequence(regime.get('provenances')) if str(value)],
            'regime_de_vigilance': str(regime.get('regime_de_vigilance') or ''),
        },
        'qualification_temporelle': {
            'portee_temporelle': str(temporal.get('portee_temporelle') or ''),
            'ancrage_temporel': str(temporal.get('ancrage_temporel') or ''),
        },
    }


def _summarize_user_turn_signals(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    active_families = [str(value) for value in _sequence(data.get('active_signal_families')) if str(value)]
    return {
        'present': bool(data.get('present', bool(data))),
        'ambiguity_present': bool(data.get('ambiguity_present', False)),
        'underdetermination_present': bool(data.get('underdetermination_present', False)),
        'active_signal_families': active_families,
        'active_signal_families_count': int(data.get('active_signal_families_count') or len(active_families)),
    }


def _summarize_stimmung(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    active_tones = []
    for item in _sequence(data.get("active_tones")):
        tone_payload = _mapping(item)
        tone = str(tone_payload.get("tone") or "").strip()
        strength = tone_payload.get("strength")
        if tone and isinstance(strength, int):
            active_tones.append({"tone": tone, "strength": strength})
    return {
        "present": bool(data.get("present", bool(data))),
        "dominant_tone": data.get("dominant_tone"),
        "active_tones": active_tones,
        "stability": str(data.get("stability") or ""),
        "shift_state": str(data.get("shift_state") or ""),
        "turns_considered": int(data.get("turns_considered") or 0),
    }


def _summarize_web(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = _mapping(payload)
    query_plan = _mapping(data.get('query_plan'))
    source_first = _mapping(data.get('source_first'))
    profile_policy = _mapping(data.get('profile_policy'))
    searxng_params = _mapping(data.get('searxng_profile_params'))
    web_discovery = _mapping(data.get('web_discovery'))
    reranking = _mapping(data.get('reranking'))
    web_confidence = _mapping(data.get('web_confidence'))
    web_evidence = _mapping(data.get('web_evidence'))
    openrouter_fallback = _mapping(data.get('openrouter_fallback'))
    source_material_summary = []
    for item in _sequence(data.get('source_material_summary')):
        source = _mapping(item)
        source_material_summary.append(
            _redact_url_fields(
                {
                    'rank': int(source.get('rank') or 0),
                    'url': str(source.get('url') or ''),
                    'source_origin': str(source.get('source_origin') or 'search_result'),
                    'is_primary_source': bool(source.get('is_primary_source', False)),
                    'used_in_prompt': bool(source.get('used_in_prompt', False)),
                    'used_content_kind': str(source.get('used_content_kind') or 'none'),
                    'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                    'content_chars': int(source.get('content_chars') or 0),
                    'truncated': bool(source.get('truncated', False)),
                }
            )
        )
    crawl4ai_extraction_summary = []
    for item in _sequence(data.get('crawl4ai_extraction_summary')):
        source = _mapping(item)
        crawl_query_hash_present = bool(str(source.get('crawl_query_sha256_12') or '').strip())
        crawl4ai_extraction_summary.append(
            _redact_url_fields(
                {
                    'rank': int(source.get('rank') or 0),
                    'url': str(source.get('url') or ''),
                    'source_origin': str(source.get('source_origin') or 'search_result'),
                    'is_primary_source': bool(source.get('is_primary_source', False)),
                    'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                    'crawl_filter': str(source.get('crawl_filter') or ''),
                    'crawl_filter_requested': str(source.get('crawl_filter_requested') or ''),
                    'crawl_policy_kind': str(source.get('crawl_policy_kind') or ''),
                    'crawl_policy_reason': str(source.get('crawl_policy_reason') or ''),
                    'crawl_cache_mode': str(source.get('crawl_cache_mode') or ''),
                    'crawl_query_hash_present': crawl_query_hash_present,
                    'crawl_query_hash_included': False,
                    'crawl_query_chars': int(source.get('crawl_query_chars') or 0),
                    'crawl_fallback_used': bool(source.get('crawl_fallback_used', False)),
                    'crawl_fallback_reason': str(source.get('crawl_fallback_reason') or ''),
                    'crawl_primary_status': str(source.get('crawl_primary_status') or ''),
                    'crawl_fallback_status': str(source.get('crawl_fallback_status') or ''),
                    'crawl_markdown_chars': int(source.get('crawl_markdown_chars') or 0),
                    'crawl_max_chars': int(source.get('crawl_max_chars') or 0),
                    'used_content_kind': str(source.get('used_content_kind') or 'none'),
                    'content_chars': int(source.get('content_chars') or 0),
                    'truncated': bool(source.get('truncated', False)),
                }
            )
        )
    return {
        'present': bool(data),
        'enabled': bool(data.get('enabled', False)),
        'status': str(data.get('status') or 'missing'),
        'activation_mode': str(
            data.get('activation_mode')
            or ('manual' if bool(data.get('enabled', False)) else 'not_requested')
        ),
        'reason_code': str(data.get('reason_code') or ''),
        'search_profile': str(data.get('search_profile') or ''),
        'query_plan_kind': str(data.get('query_plan_kind') or query_plan.get('query_plan_kind') or ''),
        'query_count': int(data.get('query_count') or query_plan.get('query_count') or 0),
        'secondary_query_count': int(
            data.get('secondary_query_count') or query_plan.get('secondary_query_count') or 0
        ),
        'deduped_result_count': int(data.get('deduped_result_count') or query_plan.get('deduped_result_count') or 0),
        'source_first_policy_kind': str(
            data.get('source_first_policy_kind')
            or source_first.get('source_first_policy_kind')
            or ''
        ),
        'source_first_active': bool(
            data.get('source_first_active', source_first.get('source_first_active', False))
        ),
        'source_first_authority': str(
            data.get('source_first_authority')
            or source_first.get('source_first_authority')
            or ''
        ),
        'source_first_product': str(
            data.get('source_first_product')
            or source_first.get('source_first_product')
            or ''
        ),
        'source_first_probable_domains': [
            str(value)
            for value in _sequence(
                data.get('source_first_probable_domains')
                or source_first.get('source_first_probable_domains')
            )
            if str(value)
        ],
        'source_first_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('source_first_reason_codes')
                or source_first.get('source_first_reason_codes')
            )
            if str(value)
        ],
        'profile_policy_kind': str(
            data.get('profile_policy_kind') or profile_policy.get('profile_policy_kind') or ''
        ),
        'profile_policy_mode': str(
            data.get('profile_policy_mode') or profile_policy.get('profile_policy_mode') or ''
        ),
        'profile_expected_domains': [
            str(value)
            for value in _sequence(data.get('profile_expected_domains') or profile_policy.get('profile_expected_domains'))
            if str(value)
        ],
        'profile_secondary_domains': [
            str(value)
            for value in _sequence(data.get('profile_secondary_domains') or profile_policy.get('profile_secondary_domains'))
            if str(value)
        ],
        'profile_downrank_domains': [
            str(value)
            for value in _sequence(data.get('profile_downrank_domains') or profile_policy.get('profile_downrank_domains'))
            if str(value)
        ],
        'profile_situated_secondary_domains': [
            str(value)
            for value in _sequence(
                data.get('profile_situated_secondary_domains')
                or profile_policy.get('profile_situated_secondary_domains')
            )
            if str(value)
        ],
        'profile_policy_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('profile_policy_reason_codes')
                or profile_policy.get('profile_policy_reason_codes')
            )
            if str(value)
        ],
        'profile_crawl_top_n_budget': int(
            data.get('profile_crawl_top_n_budget') or profile_policy.get('profile_crawl_top_n_budget') or 0
        ),
        'profile_crawl_max_chars_budget': int(
            data.get('profile_crawl_max_chars_budget') or profile_policy.get('profile_crawl_max_chars_budget') or 0
        ),
        'profile_manual_latency_target_s': int(
            data.get('profile_manual_latency_target_s') or profile_policy.get('profile_manual_latency_target_s') or 0
        ),
        'profile_source_evidence_policy_kind': str(
            data.get('profile_source_evidence_policy_kind')
            or profile_policy.get('profile_source_evidence_policy_kind')
            or ''
        ),
        'profile_expected_source_present': bool(
            data.get('profile_expected_source_present', profile_policy.get('profile_expected_source_present', False))
        ),
        'profile_expected_material_used': bool(
            data.get('profile_expected_material_used', profile_policy.get('profile_expected_material_used', False))
        ),
        'profile_secondary_source_present': bool(
            data.get('profile_secondary_source_present', profile_policy.get('profile_secondary_source_present', False))
        ),
        'profile_secondary_material_used': bool(
            data.get('profile_secondary_material_used', profile_policy.get('profile_secondary_material_used', False))
        ),
        'profile_situated_source_present': bool(
            data.get('profile_situated_source_present', profile_policy.get('profile_situated_source_present', False))
        ),
        'profile_situated_material_used': bool(
            data.get('profile_situated_material_used', profile_policy.get('profile_situated_material_used', False))
        ),
        'profile_downrank_source_present': bool(
            data.get('profile_downrank_source_present', profile_policy.get('profile_downrank_source_present', False))
        ),
        'profile_downrank_material_used': bool(
            data.get('profile_downrank_material_used', profile_policy.get('profile_downrank_material_used', False))
        ),
        'profile_insufficient_evidence': bool(
            data.get('profile_insufficient_evidence', profile_policy.get('profile_insufficient_evidence', False))
        ),
        'profile_insufficient_evidence_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('profile_insufficient_evidence_reason_codes')
                or profile_policy.get('profile_insufficient_evidence_reason_codes')
            )
            if str(value)
        ],
        'profile_source_domain_counts': dict(
            _mapping(data.get('profile_source_domain_counts') or profile_policy.get('profile_source_domain_counts'))
        ),
        'searxng_profile_params_kind': str(
            data.get('searxng_profile_params_kind')
            or searxng_params.get('searxng_profile_params_kind')
            or ''
        ),
        'searxng_profile_params_policy': str(
            data.get('searxng_profile_params_policy')
            or searxng_params.get('searxng_profile_params_policy')
            or ''
        ),
        'searxng_categories': [
            str(value)
            for value in _sequence(data.get('searxng_categories') or searxng_params.get('searxng_categories'))
            if str(value)
        ],
        'searxng_engines': [
            str(value)
            for value in _sequence(data.get('searxng_engines') or searxng_params.get('searxng_engines'))
            if str(value)
        ],
        'searxng_time_range': str(
            data.get('searxng_time_range') or searxng_params.get('searxng_time_range') or ''
        ),
        'searxng_language': str(data.get('searxng_language') or searxng_params.get('searxng_language') or ''),
        'searxng_safesearch': str(
            data.get('searxng_safesearch') or searxng_params.get('searxng_safesearch') or ''
        ),
        'searxng_params_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('searxng_params_reason_codes')
                or searxng_params.get('searxng_params_reason_codes')
            )
            if str(value)
        ],
        'searxng_hard_parameters': [
            str(value)
            for value in _sequence(
                data.get('searxng_hard_parameters')
                or searxng_params.get('searxng_hard_parameters')
            )
            if str(value)
        ],
        'searxng_soft_signal_policy': str(
            data.get('searxng_soft_signal_policy')
            or searxng_params.get('searxng_soft_signal_policy')
            or ''
        ),
        'web_discovery_provider': str(
            data.get('web_discovery_provider')
            or web_discovery.get('web_discovery_provider')
            or ''
        ),
        'web_discovery_provider_requested': str(
            data.get('web_discovery_provider_requested')
            or web_discovery.get('web_discovery_provider_requested')
            or ''
        ),
        'web_discovery_provider_effective': str(
            data.get('web_discovery_provider_effective')
            or web_discovery.get('web_discovery_provider_effective')
            or ''
        ),
        'web_discovery_external_used': bool(
            data.get('web_discovery_external_used', web_discovery.get('web_discovery_external_used', False))
        ),
        'web_discovery_external_provider': str(
            data.get('web_discovery_external_provider')
            or web_discovery.get('web_discovery_external_provider')
            or ''
        ),
        'web_discovery_external_error_kind': str(
            data.get('web_discovery_external_error_kind')
            or web_discovery.get('web_discovery_external_error_kind')
            or ''
        ),
        'web_discovery_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('web_discovery_reason_codes')
                or web_discovery.get('web_discovery_reason_codes')
            )
            if str(value)
        ],
        'rerank_applied': bool(data.get('rerank_applied', reranking.get('rerank_applied', False))),
        'rerank_policy': str(data.get('rerank_policy') or reranking.get('rerank_policy') or ''),
        'rerank_input_count': int(data.get('rerank_input_count') or reranking.get('rerank_input_count') or 0),
        'rerank_output_count': int(data.get('rerank_output_count') or reranking.get('rerank_output_count') or 0),
        'rerank_profile': str(data.get('rerank_profile') or reranking.get('rerank_profile') or ''),
        'rerank_top_domains_before': [
            str(value)
            for value in _sequence(data.get('rerank_top_domains_before') or reranking.get('rerank_top_domains_before'))
            if str(value)
        ],
        'rerank_top_domains_after': [
            str(value)
            for value in _sequence(data.get('rerank_top_domains_after') or reranking.get('rerank_top_domains_after'))
            if str(value)
        ],
        'rerank_reason_counts': dict(
            _mapping(data.get('rerank_reason_counts') or reranking.get('rerank_reason_counts'))
        ),
        'rerank_promoted_count': int(
            data.get('rerank_promoted_count') or reranking.get('rerank_promoted_count') or 0
        ),
        'rerank_downranked_count': int(
            data.get('rerank_downranked_count') or reranking.get('rerank_downranked_count') or 0
        ),
        'results_count': int(data.get('results_count') or 0),
        'explicit_url_detected': bool(data.get('explicit_url_detected', False)),
        'explicit_url_chars': len(str(data.get('explicit_url') or '')),
        'explicit_url_included': False,
        'read_state': str(data.get('read_state') or ''),
        'primary_source_kind': str(data.get('primary_source_kind') or ''),
        'primary_read_attempted': bool(data.get('primary_read_attempted', False)),
        'primary_read_status': str(data.get('primary_read_status') or ''),
        'primary_read_filter': str(data.get('primary_read_filter') or ''),
        'primary_read_raw_fallback_used': bool(data.get('primary_read_raw_fallback_used', False)),
        'fallback_used': bool(data.get('fallback_used', False)),
        'collection_path': str(data.get('collection_path') or ''),
        'used_content_kinds': [str(value) for value in _sequence(data.get('used_content_kinds')) if str(value)],
        'injected_chars': int(data.get('injected_chars') or 0),
        'context_chars': int(data.get('context_chars') or 0),
        'source_material_summary': source_material_summary,
        'crawl4ai_extraction_summary': crawl4ai_extraction_summary,
        'crawl4ai_policy_kinds': [str(value) for value in _sequence(data.get('crawl4ai_policy_kinds')) if str(value)],
        'crawl4ai_filter_counts': dict(_mapping(data.get('crawl4ai_filter_counts'))),
        'crawl4ai_cache_modes': dict(_mapping(data.get('crawl4ai_cache_modes'))),
        'crawl4ai_fallback_used_count': int(data.get('crawl4ai_fallback_used_count') or 0),
        'crawl4ai_query_hash_count': len(
            [str(value) for value in _sequence(data.get('crawl4ai_query_sha256_12')) if str(value)]
        ),
        'crawl4ai_query_hashes_included': False,
        'web_confidence_policy_kind': str(
            data.get('web_confidence_policy_kind')
            or web_confidence.get('web_confidence_policy_kind')
            or ''
        ),
        'web_confidence_level': str(
            data.get('web_confidence_level')
            or web_confidence.get('web_confidence_level')
            or ''
        ),
        'web_confidence_score': data.get('web_confidence_score', web_confidence.get('web_confidence_score')),
        'web_confidence_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('web_confidence_reason_codes')
                or web_confidence.get('web_confidence_reason_codes')
            )
            if str(value)
        ],
        'web_confidence_inputs_summary': dict(
            _mapping(
                data.get('web_confidence_inputs_summary')
                or web_confidence.get('web_confidence_inputs_summary')
            )
        ),
        'web_evidence_policy_kind': str(
            data.get('web_evidence_policy_kind')
            or web_evidence.get('web_evidence_policy_kind')
            or ''
        ),
        'web_evidence_status': str(
            data.get('web_evidence_status')
            or web_evidence.get('web_evidence_status')
            or ''
        ),
        'web_evidence_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('web_evidence_reason_codes')
                or web_evidence.get('web_evidence_reason_codes')
            )
            if str(value)
        ],
        'web_evidence_guidance_codes': [
            str(value)
            for value in _sequence(
                data.get('web_evidence_guidance_codes')
                or web_evidence.get('web_evidence_guidance_codes')
            )
            if str(value)
        ],
        'web_evidence_inputs_summary': dict(
            _mapping(
                data.get('web_evidence_inputs_summary')
                or web_evidence.get('web_evidence_inputs_summary')
            )
        ),
        'web_evidence_can_answer': bool(
            data.get('web_evidence_can_answer', web_evidence.get('web_evidence_can_answer', False))
        ),
        'web_evidence_requires_caveat': bool(
            data.get('web_evidence_requires_caveat', web_evidence.get('web_evidence_requires_caveat', False))
        ),
        'web_evidence_can_suggest_reformulation': bool(
            data.get(
                'web_evidence_can_suggest_reformulation',
                web_evidence.get('web_evidence_can_suggest_reformulation', False),
            )
        ),
        'web_evidence_url_request_policy': str(
            data.get('web_evidence_url_request_policy')
            or web_evidence.get('web_evidence_url_request_policy')
            or ''
        ),
        'web_evidence_external_fallback_used': bool(
            data.get(
                'web_evidence_external_fallback_used',
                web_evidence.get('web_evidence_external_fallback_used', False),
            )
        ),
        'openrouter_fallback_state': str(
            data.get('openrouter_fallback_state')
            or openrouter_fallback.get('openrouter_fallback_state')
            or ''
        ),
        'openrouter_fallback_used': bool(
            data.get('openrouter_fallback_used', openrouter_fallback.get('openrouter_fallback_used', False))
        ),
        'openrouter_fallback_reason_codes': [
            str(value)
            for value in _sequence(
                data.get('openrouter_fallback_reason_codes')
                or openrouter_fallback.get('openrouter_fallback_reason_codes')
            )
            if str(value)
        ],
    }


def _dialogic_effect_fields(
    *,
    epistemic_effect: Any,
    enunciation_directive: Any,
    fail_open: bool,
    fail_open_reason_code: str,
    expected_epistemic_regime: str = "",
) -> dict[str, str]:
    epistemic = _mapping(epistemic_effect)
    enunciation = _mapping(enunciation_directive)
    epistemic_values = {
        "effect": _text(epistemic.get("effect")),
        "source": _text(epistemic.get("source")),
        "reason_code": _text(epistemic.get("reason_code")),
    }
    enunciation_values = {
        "effect": _text(enunciation.get("effect")),
        "source": _text(enunciation.get("source")),
        "reason_code": _text(enunciation.get("reason_code")),
    }
    paired_fail_open = (
        epistemic_values["effect"] == "unknown"
        and epistemic_values["source"] == "fail_open"
        and enunciation_values["effect"] == "unknown"
        and enunciation_values["source"] == "fail_open"
        and epistemic_values["reason_code"] == enunciation_values["reason_code"]
        and epistemic_values["reason_code"] in epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES
    )
    expected_regime = _text(expected_epistemic_regime)
    nominal_epistemic = (
        epistemic_values["effect"] in epistemic_doctrine.EPISTEMIC_REASON_CODES_BY_EFFECT
        and epistemic_values["source"] == "epistemic_inputs"
        and epistemic_values["reason_code"]
        in epistemic_doctrine.EPISTEMIC_REASON_CODES_BY_EFFECT[epistemic_values["effect"]]
        and (not expected_regime or epistemic_values["effect"] == expected_regime)
    )
    nominal_enunciation = (
        enunciation_values == {
            "effect": "delicate_expression",
            "source": "stimmung",
            "reason_code": "affective_transition",
        }
        or enunciation_values == {
            "effect": "none",
            "source": "not_applicable",
            "reason_code": "stimmung_absent",
        }
        or enunciation_values["effect"] == "none"
        and enunciation_values["source"] == "stimmung"
        and enunciation_values["reason_code"] in {"stimmung_stable", "stimmung_no_transition"}
    )
    if (paired_fail_open and fail_open) or (nominal_epistemic and nominal_enunciation):
        return {
            "epistemic_effect": epistemic_values["effect"],
            "epistemic_source": epistemic_values["source"],
            "epistemic_reason_code": epistemic_values["reason_code"],
            "enunciation_effect": enunciation_values["effect"],
            "enunciation_source": enunciation_values["source"],
            "enunciation_reason_code": enunciation_values["reason_code"],
        }

    if fail_open and _text(fail_open_reason_code) in epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES:
        reason_code = _text(fail_open_reason_code) or "unknown_error"
        return {
            "epistemic_effect": "unknown",
            "epistemic_source": "fail_open",
            "epistemic_reason_code": reason_code,
            "enunciation_effect": "unknown",
            "enunciation_source": "fail_open",
            "enunciation_reason_code": reason_code,
        }

    return {
        "epistemic_effect": "unknown",
        "epistemic_source": "unknown",
        "epistemic_reason_code": "legacy_incomplete",
        "enunciation_effect": "unknown",
        "enunciation_source": "unknown",
        "enunciation_reason_code": "legacy_incomplete",
    }


def _effects_claim_fail_open(epistemic_effect: Any, enunciation_directive: Any) -> bool:
    epistemic = _mapping(epistemic_effect)
    enunciation = _mapping(enunciation_directive)
    return (
        _text(epistemic.get("effect")) == "unknown"
        and _text(epistemic.get("source")) == "fail_open"
        and _text(enunciation.get("effect")) == "unknown"
        and _text(enunciation.get("source")) == "fail_open"
        and _text(epistemic.get("reason_code")) == _text(enunciation.get("reason_code"))
    )


def build_primary_node_payload(
    *,
    primary_payload: Mapping[str, Any] | None,
    node_state_persistence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    upstream_advisory = _mapping(primary_verdict.get("upstream_advisory"))
    audit = _mapping(primary_verdict.get("audit"))
    degraded_fields = [value for value in (_text(item) for item in _sequence(audit.get("degraded_fields"))) if value]
    fail_open = bool(audit.get("fail_open", False))
    effect_fields = _dialogic_effect_fields(
        epistemic_effect=primary_verdict.get("epistemic_effect"),
        enunciation_directive=primary_verdict.get("enunciation_directive"),
        fail_open=fail_open,
        fail_open_reason_code=_text(audit.get("reason_code")),
        expected_epistemic_regime=_text(primary_verdict.get("epistemic_regime")),
    )
    payload = {
        "upstream_recommendation_posture": _text(
            upstream_advisory.get("recommended_judgment_posture") or primary_verdict.get("judgment_posture")
        ),
        "upstream_output_regime_proposed": _text(
            upstream_advisory.get("proposed_output_regime") or primary_verdict.get("discursive_regime")
        ),
        "upstream_active_signal_families": [
            value
            for value in (
                _text(item)
                for item in _sequence(
                    upstream_advisory.get("active_signal_families")
                )
            )
            if value
        ],
        "upstream_constraint_present": bool(
            upstream_advisory.get("constraint_present", bool(_sequence(primary_verdict.get("source_conflicts"))))
        ),
        "epistemic_regime": _text(primary_verdict.get("epistemic_regime")),
        "proof_regime": _text(primary_verdict.get("proof_regime")),
        "uncertainty_posture": _text(primary_verdict.get("uncertainty_posture")),
        **effect_fields,
        "source_conflicts_count": len(_sequence(primary_verdict.get("source_conflicts"))),
        "fail_open": bool(audit.get("fail_open", False)),
        "state_used": bool(audit.get("state_used", False)),
        "degraded_fields_count": len(degraded_fields),
    }
    if fail_open or bool(audit.get("fallback_used", False)):
        payload.update(
            {
                "fallback_used": bool(audit.get("fallback_used", fail_open)),
                "fallback_source": _text(audit.get("fallback_source")) or "primary_node",
                "node_stage": _text(audit.get("node_stage")) or "primary_node",
                "reason_code": _text(audit.get("reason_code")) or "unknown_error",
                "error_class": _text(audit.get("error_class")) or "unknown_error",
            }
        )
    state_persistence = _mapping(node_state_persistence)
    if state_persistence:
        payload.update(
            {
                "node_state_read_present": bool(state_persistence.get("node_state_read_present", False)),
                "node_state_read_valid": bool(state_persistence.get("node_state_read_valid", False)),
                "node_state_read_reason_code": _text(state_persistence.get("node_state_read_reason_code")),
                "node_state_write_attempted": bool(
                    state_persistence.get("node_state_write_attempted", False)
                ),
                "node_state_write_succeeded": bool(
                    state_persistence.get("node_state_write_succeeded", False)
                ),
                "node_state_write_changed": bool(state_persistence.get("node_state_write_changed", False)),
                "node_state_write_reason_code": _text(state_persistence.get("node_state_write_reason_code")),
                "node_state_schema_version": _text(state_persistence.get("node_state_schema_version")),
                "node_state_sha256_12": _text(state_persistence.get("node_state_sha256_12")),
            }
        )
    return payload


def emit_primary_node(
    *,
    primary_payload: Mapping[str, Any] | None,
    node_state_persistence: Mapping[str, Any] | None = None,
) -> bool:
    payload = build_primary_node_payload(
        primary_payload=primary_payload,
        node_state_persistence=node_state_persistence,
    )
    return chat_turn_logger.emit(
        "primary_node",
        status="error" if payload["fail_open"] else "ok",
        payload=payload,
    )


def build_node_state_persistence_payload(
    *,
    read_result: Mapping[str, Any] | None,
    write_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    read_payload = _mapping(read_result)
    write_payload = _mapping(write_result)
    schema_version = _text(write_payload.get("schema_version") or read_payload.get("schema_version"))
    state_hash = _text(write_payload.get("state_sha256_12") or read_payload.get("state_sha256_12"))
    return {
        "node_state_read_present": bool(read_payload.get("present", False)),
        "node_state_read_valid": bool(read_payload.get("valid", False)),
        "node_state_read_reason_code": _text(read_payload.get("reason_code")) or "not_attempted",
        "node_state_write_attempted": bool(write_payload.get("attempted", False)),
        "node_state_write_succeeded": bool(write_payload.get("written", False)),
        "node_state_write_changed": bool(write_payload.get("changed", False)),
        "node_state_write_reason_code": _text(write_payload.get("reason_code")) or "not_attempted",
        "node_state_schema_version": schema_version,
        "node_state_sha256_12": state_hash,
    }


def build_validation_agent_payload(
    *,
    validation_dialogue_context: Mapping[str, Any] | None,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> dict[str, Any]:
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    upstream_advisory = _mapping(primary_verdict.get("upstream_advisory"))
    validated_output = _mapping(getattr(validated_result, "validated_output", None))
    validation_context_payload = _mapping(validation_dialogue_context)
    directives = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("pipeline_directives_final")))
        if value
    ]
    followed = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("advisory_recommendations_followed")))
        if value
    ]
    overridden = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("advisory_recommendations_overridden")))
        if value
    ]
    applied_hard_guards = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("applied_hard_guards")))
        if value
    ]
    status = _text(getattr(validated_result, "status", ""))
    reason_code = _text(getattr(validated_result, "reason_code", ""))
    inherited_fail_open = _effects_claim_fail_open(
        validated_output.get("epistemic_effect"),
        validated_output.get("enunciation_directive"),
    )
    effect_fields = _dialogic_effect_fields(
        epistemic_effect=validated_output.get("epistemic_effect"),
        enunciation_directive=validated_output.get("enunciation_directive"),
        fail_open=(
            status == "error"
            or _text(getattr(validated_result, "decision_source", "")) == "fail_open"
            or inherited_fail_open
        ),
        fail_open_reason_code=reason_code,
    )
    payload = {
        "dialogue_messages_count": len(_sequence(validation_context_payload.get("messages"))),
        "dialogue_truncated": bool(validation_context_payload.get("truncated", False)),
        "current_user_retained": bool(validation_context_payload.get("current_user_retained", False)),
        "last_assistant_retained": bool(validation_context_payload.get("last_assistant_retained", False)),
        "upstream_recommendation_posture": _text(
            upstream_advisory.get("recommended_judgment_posture") or primary_verdict.get("judgment_posture")
        ),
        "upstream_output_regime_proposed": _text(
            upstream_advisory.get("proposed_output_regime") or primary_verdict.get("discursive_regime")
        ),
        "upstream_active_signal_families": [
            value
            for value in (
                _text(item)
                for item in _sequence(
                    upstream_advisory.get("active_signal_families")
                )
            )
            if value
        ],
        "upstream_constraint_present": bool(
            upstream_advisory.get("constraint_present", bool(_sequence(primary_verdict.get("source_conflicts"))))
        ),
        "validation_decision": _text(validated_output.get("validation_decision")),
        "final_judgment_posture": _text(validated_output.get("final_judgment_posture")),
        "final_output_regime": _text(validated_output.get("final_output_regime")),
        "arbiter_followed_upstream": bool(validated_output.get("arbiter_followed_upstream", False)),
        "advisory_recommendations_followed": followed,
        "advisory_recommendations_overridden": overridden,
        "applied_hard_guards": applied_hard_guards,
        "arbiter_reason_present": bool(_text(validated_output.get("arbiter_reason"))),
        "arbiter_reason_chars": len(_text(validated_output.get("arbiter_reason"))),
        "arbiter_reason_included": False,
        "projected_judgment_posture": _text(validated_output.get("final_judgment_posture")),
        "pipeline_directives_final": directives,
        "decision_source": _text(getattr(validated_result, "decision_source", "")),
        **effect_fields,
    }
    hard_guard_effect = _text(validated_output.get("hard_guard_effect"))
    if hard_guard_effect:
        payload["hard_guard_effect"] = hard_guard_effect
    if reason_code:
        payload["reason_code"] = reason_code
    return payload


def emit_validation_agent(
    *,
    validation_dialogue_context: Mapping[str, Any] | None,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> bool:
    status = _text(getattr(validated_result, "status", "")) or "ok"
    if status not in {"ok", "error", "skipped"}:
        status = "ok"
    return chat_turn_logger.emit(
        "validation_agent",
        status=status,
        payload=build_validation_agent_payload(
            validation_dialogue_context=validation_dialogue_context,
            primary_payload=primary_payload,
            validated_result=validated_result,
        ),
        model=_text(getattr(validated_result, "model", "")) or None,
    )


def empty_hermeneutic_prompt_injection_payload() -> dict[str, Any]:
    return {
        "present": False,
        "chars": 0,
        "fingerprint_present": False,
        "fingerprint_included": False,
        "prompt_block_hash_included": False,
        "raw_content_included": False,
        "final_judgment_posture": "",
        "final_output_regime": "",
        "epistemic_regime": "",
        "directives_count": 0,
        "source": "not_injected",
        "fallback": False,
        "reason_code": "",
        "epistemic_effect": "unknown",
        "epistemic_source": "unknown",
        "epistemic_reason_code": "legacy_incomplete",
        "enunciation_effect": "unknown",
        "enunciation_source": "unknown",
        "enunciation_reason_code": "legacy_incomplete",
    }


def build_hermeneutic_prompt_injection_payload(
    *,
    hermeneutic_judgment_block: Any,
    primary_payload: Mapping[str, Any] | None,
    validated_result: Any,
) -> dict[str, Any]:
    block = str(hermeneutic_judgment_block or "")
    primary_verdict = _mapping(_mapping(primary_payload).get("primary_verdict"))
    validated_output = _mapping(getattr(validated_result, "validated_output", None))
    directives = [
        value
        for value in (_text(item) for item in _sequence(validated_output.get("pipeline_directives_final")))
        if value
    ]
    status = _text(getattr(validated_result, "status", ""))
    decision_source = _text(getattr(validated_result, "decision_source", ""))
    reason_code = _text(getattr(validated_result, "reason_code", ""))
    fallback = bool(status and status != "ok") or decision_source in {"fallback", "fail_open"} or bool(reason_code)
    inherited_fail_open = _effects_claim_fail_open(
        validated_output.get("epistemic_effect"),
        validated_output.get("enunciation_directive"),
    )
    effect_fields = _dialogic_effect_fields(
        epistemic_effect=validated_output.get("epistemic_effect"),
        enunciation_directive=validated_output.get("enunciation_directive"),
        fail_open=status == "error" or decision_source == "fail_open" or inherited_fail_open,
        fail_open_reason_code=reason_code,
    )

    payload = empty_hermeneutic_prompt_injection_payload()
    payload.update(
        {
            "present": bool(block.strip()),
            "chars": len(block),
            "fingerprint_present": False,
            "fingerprint_included": False,
            "prompt_block_hash_included": False,
            "raw_content_included": False,
            "final_judgment_posture": _text(validated_output.get("final_judgment_posture")),
            "final_output_regime": _text(validated_output.get("final_output_regime")),
            "epistemic_regime": _text(primary_verdict.get("epistemic_regime")),
            "directives_count": len(directives),
            "source": decision_source or ("validation_agent" if validated_output else "not_injected"),
            "fallback": fallback,
            "reason_code": reason_code,
            **effect_fields,
        }
    )
    return payload


def _provider_message_stats(messages: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    role_counts: dict[str, int] = {}
    system_prompt_chars = 0
    current_user_chars = 0
    input_chars_total = 0
    for message in messages:
        message_payload = _mapping(message)
        role = _text(message_payload.get("role")) or "unknown"
        content_chars = len(str(message_payload.get("content") or ""))
        input_chars_total += content_chars
        role_counts[role] = role_counts.get(role, 0) + 1
        if role == "system":
            system_prompt_chars += content_chars
        if role == "user":
            current_user_chars += content_chars
    return {
        "messages_count": len(messages),
        "message_role_counts": role_counts,
        "system_prompt_present": system_prompt_chars > 0,
        "system_prompt_chars": system_prompt_chars,
        "current_user_present": current_user_chars > 0,
        "current_user_chars": current_user_chars,
        "input_chars_total": input_chars_total,
    }


def _recent_window_stats(payload: Mapping[str, Any] | None, *, context_window_turns: int) -> dict[str, Any]:
    data = _mapping(payload)
    turns = list(_sequence(data.get("turns")))
    turn_count_raw = data.get("turn_count")
    try:
        turn_count = int(turn_count_raw)
    except (TypeError, ValueError):
        turn_count = len(turns)
    turns_with_messages_count = 0
    for turn in turns:
        if _sequence(_mapping(turn).get("messages")):
            turns_with_messages_count += 1
    return {
        "recent_window_present": bool(data),
        "recent_turn_count": max(0, turn_count),
        "recent_turns_with_messages_count": turns_with_messages_count,
        "recent_has_in_progress_turn": bool(data.get("has_in_progress_turn", False)),
        "recent_max_turns": int(data.get("max_recent_turns") or context_window_turns or 0),
    }


def build_stimmung_prompt_prepared_payload(
    *,
    decision_source: str,
    messages: Sequence[Mapping[str, Any]],
    recent_window_input_payload: Mapping[str, Any] | None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout_s: int,
    context_window_turns: int,
) -> dict[str, Any]:
    payload = {
        "schema_version": "v1",
        "payload_kind": "secondary_stimmung_agent_provider",
        "provider_caller": "stimmung_agent",
        "secondary_provider_payload": True,
        "main_llm_payload": False,
        "stimmung_status": "prepared",
        "attempt_decision_source": _text(decision_source) or "unknown",
        "sampling": {
            "temperature": float(temperature),
            "top_p": float(top_p),
            "max_tokens": int(max_tokens),
            "timeout_s": int(timeout_s),
        },
        "fail_open": False,
        "reason_code": "",
    }
    payload.update(_provider_message_stats(messages))
    payload.update(
        _recent_window_stats(
            recent_window_input_payload,
            context_window_turns=context_window_turns,
        )
    )
    return payload


def emit_stimmung_prompt_prepared(
    *,
    model: str,
    decision_source: str,
    messages: Sequence[Mapping[str, Any]],
    recent_window_input_payload: Mapping[str, Any] | None,
    temperature: float,
    top_p: float,
    max_tokens: int,
    timeout_s: int,
    context_window_turns: int,
) -> bool:
    return chat_turn_logger.emit(
        "stimmung_prompt_prepared",
        status="ok",
        model=_text(model) or None,
        prompt_kind="stimmung_agent_secondary",
        payload=build_stimmung_prompt_prepared_payload(
            decision_source=decision_source,
            messages=messages,
            recent_window_input_payload=recent_window_input_payload,
            temperature=temperature,
            top_p=top_p,
            max_tokens=max_tokens,
            timeout_s=timeout_s,
            context_window_turns=context_window_turns,
        ),
    )


def build_hermeneutic_node_insertion_payload(
    *,
    time_input: Mapping[str, Any] | None = None,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        'insertion_point_reached': True,
        'mode': str(current_mode or ''),
        'inputs': {
            'time': _summarize_time(time_input),
            'memory_retrieved': _summarize_memory_retrieved(memory_retrieved),
            'memory_arbitration': _summarize_memory_arbitration(memory_arbitration),
            'summary': _summarize_summary(summary_input),
            'identity': _summarize_identity(identity_input),
            'recent_context': _summarize_recent_context(recent_context_input),
            'recent_window': _summarize_recent_window(recent_window_input),
            'user_turn': _summarize_user_turn(user_turn_input),
            'user_turn_signals': _summarize_user_turn_signals(user_turn_signals),
            'stimmung': _summarize_stimmung(stimmung_input),
            'web': _summarize_web(web_input),
        },
    }


def emit_hermeneutic_node_insertion(
    *,
    time_input: Mapping[str, Any] | None = None,
    current_mode: str,
    memory_retrieved: Mapping[str, Any] | None = None,
    memory_arbitration: Mapping[str, Any] | None = None,
    summary_input: Mapping[str, Any] | None = None,
    identity_input: Mapping[str, Any] | None = None,
    recent_context_input: Mapping[str, Any] | None = None,
    recent_window_input: Mapping[str, Any] | None = None,
    user_turn_input: Mapping[str, Any] | None = None,
    user_turn_signals: Mapping[str, Any] | None = None,
    stimmung_input: Mapping[str, Any] | None = None,
    web_input: Mapping[str, Any] | None = None,
) -> bool:
    return chat_turn_logger.emit(
        'hermeneutic_node_insertion',
        status='ok',
        payload=build_hermeneutic_node_insertion_payload(
            time_input=time_input,
            current_mode=current_mode,
            memory_retrieved=memory_retrieved,
            memory_arbitration=memory_arbitration,
            summary_input=summary_input,
            identity_input=identity_input,
            recent_context_input=recent_context_input,
            recent_window_input=recent_window_input,
            user_turn_input=user_turn_input,
            user_turn_signals=user_turn_signals,
            stimmung_input=stimmung_input,
            web_input=web_input,
        ),
    )
