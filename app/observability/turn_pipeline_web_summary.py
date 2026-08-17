from __future__ import annotations

from typing import Any, Mapping, Sequence

from observability.turn_pipeline_summary_support import (
    _event_ts,
    _events_for_stage,
    _latest_stage_event,
    _mapping,
    _payload,
    _reason_code,
    _sequence,
    _status,
    _text,
    _to_int,
)


def build_web_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    turn_start = _latest_stage_event(events, 'turn_start')
    turn_payload = _payload(turn_start or {})
    web_events = _events_for_stage(events, 'web_search')
    latest = web_events[-1] if web_events else None
    payload = _payload(latest or {})
    requested = bool(turn_payload.get('web_search_enabled')) or any(
        bool(_payload(event).get('enabled')) for event in web_events
    )
    if latest:
        status = _status(latest)
        reason = _reason_code(payload)
    elif requested:
        status = 'missing'
        reason = 'missing_web_search_stage'
    else:
        status = 'not_applicable'
        reason = 'web_not_requested'
    injected_chars = _to_int(payload.get('injected_chars') or payload.get('context_chars'))
    legacy_query = _text(payload.get('query'))
    query_chars = _to_int(payload.get('query_chars')) or (len(legacy_query) if legacy_query else 0)
    return {
        'requested': requested,
        'event_present': bool(latest),
        'status': status,
        'success': status == 'ok',
        'skipped': status == 'skipped',
        'error': status == 'error',
        'reason_code': reason,
        'search_profile': _text(payload.get('search_profile')),
        'query_plan_kind': _text(payload.get('query_plan_kind')),
        'query_count': _to_int(payload.get('query_count')),
        'secondary_query_count': _to_int(payload.get('secondary_query_count')),
        'deduped_result_count': _to_int(payload.get('deduped_result_count')),
        'source_first_policy_kind': _text(payload.get('source_first_policy_kind')),
        'source_first_active': bool(payload.get('source_first_active', False)),
        'source_first_authority': _text(payload.get('source_first_authority')),
        'source_first_product': _text(payload.get('source_first_product')),
        'source_first_probable_domains': [
            _text(value)
            for value in payload.get('source_first_probable_domains') or []
            if _text(value)
        ],
        'source_first_reason_codes': [
            _text(value)
            for value in payload.get('source_first_reason_codes') or []
            if _text(value)
        ],
        'profile_policy_kind': _text(payload.get('profile_policy_kind')),
        'profile_policy_mode': _text(payload.get('profile_policy_mode')),
        'profile_expected_domains': [
            _text(value)
            for value in payload.get('profile_expected_domains') or []
            if _text(value)
        ],
        'profile_secondary_domains': [
            _text(value)
            for value in payload.get('profile_secondary_domains') or []
            if _text(value)
        ],
        'profile_downrank_domains': [
            _text(value)
            for value in payload.get('profile_downrank_domains') or []
            if _text(value)
        ],
        'profile_situated_secondary_domains': [
            _text(value)
            for value in payload.get('profile_situated_secondary_domains') or []
            if _text(value)
        ],
        'profile_policy_reason_codes': [
            _text(value)
            for value in payload.get('profile_policy_reason_codes') or []
            if _text(value)
        ],
        'profile_crawl_top_n_budget': _to_int(payload.get('profile_crawl_top_n_budget')),
        'profile_crawl_max_chars_budget': _to_int(payload.get('profile_crawl_max_chars_budget')),
        'profile_manual_latency_target_s': _to_int(payload.get('profile_manual_latency_target_s')),
        'profile_source_evidence_policy_kind': _text(payload.get('profile_source_evidence_policy_kind')),
        'profile_expected_source_present': bool(payload.get('profile_expected_source_present', False)),
        'profile_expected_material_used': bool(payload.get('profile_expected_material_used', False)),
        'profile_secondary_source_present': bool(payload.get('profile_secondary_source_present', False)),
        'profile_secondary_material_used': bool(payload.get('profile_secondary_material_used', False)),
        'profile_situated_source_present': bool(payload.get('profile_situated_source_present', False)),
        'profile_situated_material_used': bool(payload.get('profile_situated_material_used', False)),
        'profile_downrank_source_present': bool(payload.get('profile_downrank_source_present', False)),
        'profile_downrank_material_used': bool(payload.get('profile_downrank_material_used', False)),
        'profile_insufficient_evidence': bool(payload.get('profile_insufficient_evidence', False)),
        'profile_insufficient_evidence_reason_codes': [
            _text(value)
            for value in payload.get('profile_insufficient_evidence_reason_codes') or []
            if _text(value)
        ],
        'profile_source_domain_counts': dict(_mapping(payload.get('profile_source_domain_counts'))),
        'searxng_profile_params_kind': _text(payload.get('searxng_profile_params_kind')),
        'searxng_profile_params_policy': _text(payload.get('searxng_profile_params_policy')),
        'searxng_categories': [
            _text(value)
            for value in payload.get('searxng_categories') or []
            if _text(value)
        ],
        'searxng_engines': [
            _text(value)
            for value in payload.get('searxng_engines') or []
            if _text(value)
        ],
        'searxng_time_range': _text(payload.get('searxng_time_range')),
        'searxng_language': _text(payload.get('searxng_language')),
        'searxng_safesearch': _text(payload.get('searxng_safesearch')),
        'searxng_params_reason_codes': [
            _text(value)
            for value in payload.get('searxng_params_reason_codes') or []
            if _text(value)
        ],
        'searxng_hard_parameters': [
            _text(value)
            for value in payload.get('searxng_hard_parameters') or []
            if _text(value)
        ],
        'searxng_soft_signal_policy': _text(payload.get('searxng_soft_signal_policy')),
        'web_discovery_provider': _text(payload.get('web_discovery_provider')),
        'web_discovery_provider_requested': _text(payload.get('web_discovery_provider_requested')),
        'web_discovery_provider_effective': _text(payload.get('web_discovery_provider_effective')),
        'web_discovery_external_used': bool(payload.get('web_discovery_external_used', False)),
        'web_discovery_external_provider': _text(payload.get('web_discovery_external_provider')),
        'web_discovery_external_error_kind': _text(payload.get('web_discovery_external_error_kind')),
        'web_discovery_reason_codes': [
            _text(value)
            for value in payload.get('web_discovery_reason_codes') or []
            if _text(value)
        ],
        'rerank_applied': bool(payload.get('rerank_applied', False)),
        'rerank_policy': _text(payload.get('rerank_policy')),
        'rerank_input_count': _to_int(payload.get('rerank_input_count')),
        'rerank_output_count': _to_int(payload.get('rerank_output_count')),
        'rerank_profile': _text(payload.get('rerank_profile')),
        'rerank_top_domains_before': [
            _text(value)
            for value in payload.get('rerank_top_domains_before') or []
            if _text(value)
        ],
        'rerank_top_domains_after': [
            _text(value)
            for value in payload.get('rerank_top_domains_after') or []
            if _text(value)
        ],
        'rerank_reason_counts': dict(_mapping(payload.get('rerank_reason_counts'))),
        'rerank_promoted_count': _to_int(payload.get('rerank_promoted_count')),
        'rerank_downranked_count': _to_int(payload.get('rerank_downranked_count')),
        'crawl4ai_policy_kinds': [
            _text(value)
            for value in payload.get('crawl4ai_policy_kinds') or []
            if _text(value)
        ],
        'crawl4ai_filter_counts': dict(_mapping(payload.get('crawl4ai_filter_counts'))),
        'crawl4ai_cache_modes': dict(_mapping(payload.get('crawl4ai_cache_modes'))),
        'crawl4ai_fallback_used_count': _to_int(payload.get('crawl4ai_fallback_used_count')),
        'crawl4ai_query_count': len([
            value
            for value in payload.get('crawl4ai_query_sha256_12') or []
            if _text(value)
        ]),
        'crawl4ai_extraction_summary': [
            {
                'rank': _to_int(source.get('rank')),
                'url_present': bool(str(source.get('url') or '').strip()),
                'url_chars': len(str(source.get('url') or '').strip()),
                'source_origin': str(source.get('source_origin') or 'search_result'),
                'is_primary_source': bool(source.get('is_primary_source', False)),
                'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                'crawl_filter': str(source.get('crawl_filter') or ''),
                'crawl_policy_kind': str(source.get('crawl_policy_kind') or ''),
                'crawl_policy_reason': str(source.get('crawl_policy_reason') or ''),
                'crawl_cache_mode': str(source.get('crawl_cache_mode') or ''),
                'crawl_query_chars': _to_int(source.get('crawl_query_chars')),
                'crawl_fallback_used': bool(source.get('crawl_fallback_used', False)),
                'crawl_fallback_reason': str(source.get('crawl_fallback_reason') or ''),
                'crawl_primary_status': str(source.get('crawl_primary_status') or ''),
                'crawl_fallback_status': str(source.get('crawl_fallback_status') or ''),
                'crawl_markdown_chars': _to_int(source.get('crawl_markdown_chars')),
                'crawl_max_chars': _to_int(source.get('crawl_max_chars')),
                'used_content_kind': str(source.get('used_content_kind') or 'none'),
                'content_chars': _to_int(source.get('content_chars')),
                'truncated': bool(source.get('truncated', False)),
            }
            for source in (_mapping(item) for item in _sequence(payload.get('crawl4ai_extraction_summary')))
        ],
        'web_confidence_policy_kind': _text(payload.get('web_confidence_policy_kind')),
        'web_confidence_level': _text(payload.get('web_confidence_level')),
        'web_confidence_score': payload.get('web_confidence_score'),
        'web_confidence_reason_codes': [
            _text(value)
            for value in payload.get('web_confidence_reason_codes') or []
            if _text(value)
        ],
        'web_confidence_inputs_summary': dict(_mapping(payload.get('web_confidence_inputs_summary'))),
        'web_evidence_policy_kind': _text(payload.get('web_evidence_policy_kind')),
        'web_evidence_status': _text(payload.get('web_evidence_status')),
        'web_evidence_reason_codes': [
            _text(value)
            for value in payload.get('web_evidence_reason_codes') or []
            if _text(value)
        ],
        'web_evidence_guidance_codes': [
            _text(value)
            for value in payload.get('web_evidence_guidance_codes') or []
            if _text(value)
        ],
        'web_evidence_inputs_summary': dict(_mapping(payload.get('web_evidence_inputs_summary'))),
        'web_evidence_can_answer': bool(payload.get('web_evidence_can_answer', False)),
        'web_evidence_requires_caveat': bool(payload.get('web_evidence_requires_caveat', False)),
        'web_evidence_can_suggest_reformulation': bool(
            payload.get('web_evidence_can_suggest_reformulation', False)
        ),
        'web_evidence_url_request_policy': _text(payload.get('web_evidence_url_request_policy')),
        'web_evidence_external_fallback_used': bool(payload.get('web_evidence_external_fallback_used', False)),
        'openrouter_fallback_state': _text(payload.get('openrouter_fallback_state')),
        'openrouter_fallback_used': bool(payload.get('openrouter_fallback_used', False)),
        'openrouter_fallback_reason_codes': [
            _text(value)
            for value in payload.get('openrouter_fallback_reason_codes') or []
            if _text(value)
        ],
        'results_count': _to_int(payload.get('results_count')),
        'injected': bool(payload.get('context_injected')) or injected_chars > 0,
        'injected_chars': injected_chars,
        'query_present': bool(payload.get('query_present')) or bool(legacy_query),
        'query_chars': query_chars,
        'read_state': _text(payload.get('read_state')),
        'truncated': bool(payload.get('truncated')),
        'latest_ts': _event_ts(latest or {}),
    }
