from __future__ import annotations

from typing import Any, Mapping, Sequence
from urllib.parse import urlparse


POLICY_KIND = 'local_web_confidence_observable_v0'
FALLBACK_DISABLED_REASON = 'external_fallback_disabled_lot7'
FALLBACK_STATE_FUTURE_ONLY = 'future_only'
FALLBACK_STATE_HUMAN_REVIEW_CANDIDATE = 'human_review_candidate'
FALLBACK_STATE_NOT_APPLICABLE = 'not_applicable'


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _reason_codes(codes: Sequence[str]) -> list[str]:
    deduped: list[str] = []
    for code in codes:
        text = str(code or '').strip()
        if text and text not in deduped:
            deduped.append(text)
    return deduped


def _clamp_score(score: float) -> float:
    return round(max(0.0, min(1.0, float(score))), 3)


def _level(score: float, *, enabled: bool) -> str:
    if not enabled:
        return 'unknown'
    if score >= 0.78:
        return 'high'
    if score >= 0.5:
        return 'medium'
    return 'low'


def _domain_from_url(url: Any) -> str:
    text = str(url or '').strip()
    if not text:
        return ''
    parsed = urlparse(text)
    return parsed.netloc.lower().removeprefix('www.')


def _unique_domains(summary: Sequence[Mapping[str, Any]]) -> list[str]:
    domains: list[str] = []
    for item in summary:
        domain = _domain_from_url(item.get('url'))
        if domain and domain not in domains:
            domains.append(domain)
    return domains


def _input_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    source_material = [
        _mapping(item)
        for item in _sequence(payload.get('source_material_summary'))
    ]
    crawl_summary = [
        _mapping(item)
        for item in _sequence(payload.get('crawl4ai_extraction_summary'))
    ]
    used_content_kinds = [
        str(value)
        for value in _sequence(payload.get('used_content_kinds'))
        if str(value or '')
    ]
    domains = _unique_domains(source_material)
    used_source_count = sum(1 for item in source_material if bool(item.get('used_in_prompt', False)))
    crawl_success_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'success')
    crawl_empty_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'empty')
    crawl_error_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'error')
    snippet_only_count = sum(
        1
        for item in source_material
        if bool(item.get('used_in_prompt', False))
        and str(item.get('used_content_kind') or '') == 'search_snippet'
    )
    return {
        'status': str(payload.get('status') or ''),
        'reason_code_present': bool(str(payload.get('reason_code') or '').strip()),
        'collection_path': str(payload.get('collection_path') or ''),
        'read_state': str(payload.get('read_state') or ''),
        'results_count': _to_int(payload.get('results_count')),
        'query_count': _to_int(payload.get('query_count')),
        'deduped_result_count': _to_int(payload.get('deduped_result_count')),
        'source_count': len(source_material),
        'used_source_count': used_source_count,
        'domain_count': len(domains),
        'used_content_kinds': used_content_kinds,
        'injected_chars': _to_int(payload.get('injected_chars')),
        'context_chars': _to_int(payload.get('context_chars')),
        'crawl_success_count': crawl_success_count,
        'crawl_empty_count': crawl_empty_count,
        'crawl_error_count': crawl_error_count,
        'snippet_only_count': snippet_only_count,
        'rerank_applied': bool(payload.get('rerank_applied', False)),
        'rerank_reason_code_count': sum(
            _to_int(value)
            for value in _mapping(payload.get('rerank_reason_counts')).values()
        ),
        'crawl4ai_fallback_used_count': _to_int(payload.get('crawl4ai_fallback_used_count')),
        'crawl4ai_query_hash_count': len(_sequence(payload.get('crawl4ai_query_sha256_12'))),
    }


def _score_explicit_url(summary: Mapping[str, Any]) -> tuple[float, list[str]]:
    read_state = str(summary.get('read_state') or '')
    used_content_kinds = set(summary.get('used_content_kinds') or [])
    reasons = ['confidence_signal_only']
    if read_state == 'page_read':
        reasons.append('explicit_url_page_read')
        score = 0.92
    elif read_state == 'page_partially_read':
        reasons.append('explicit_url_page_partially_read')
        score = 0.72
    elif read_state == 'page_not_read_snippet_fallback':
        reasons.append('explicit_url_not_read_snippet_fallback')
        score = 0.42
    elif read_state:
        reasons.append('explicit_url_not_read')
        score = 0.18
    else:
        reasons.append('explicit_url_read_state_missing')
        score = 0.2
    if 'crawl_markdown' in used_content_kinds:
        reasons.append('crawl_markdown_used')
    if 'search_snippet' in used_content_kinds:
        reasons.append('snippet_material_used')
    if int(summary.get('crawl4ai_fallback_used_count') or 0) > 0:
        reasons.append('bm25_fit_fallback_used')
    return score, reasons


def _score_search(summary: Mapping[str, Any]) -> tuple[float, list[str]]:
    reasons = ['confidence_signal_only']
    score = 0.25
    used_content_kinds = set(summary.get('used_content_kinds') or [])
    injected_chars = int(summary.get('injected_chars') or 0)
    crawl_success_count = int(summary.get('crawl_success_count') or 0)
    domain_count = int(summary.get('domain_count') or 0)

    if int(summary.get('used_source_count') or 0) > 0:
        score += 0.1
        reasons.append('prompt_material_used')
    else:
        score -= 0.1
        reasons.append('no_prompt_material')

    if crawl_success_count > 0:
        score += 0.22
        reasons.append('crawl_success_present')
    if 'crawl_markdown' in used_content_kinds:
        score += 0.18
        reasons.append('crawl_markdown_used')

    if injected_chars >= 800:
        score += 0.12
        reasons.append('substantial_injected_material')
    elif injected_chars > 0:
        score += 0.05
        reasons.append('some_injected_material')
    else:
        score -= 0.12
        reasons.append('no_injected_material')

    if domain_count >= 2:
        score += 0.08
        reasons.append('multi_domain_material')
    elif domain_count == 1:
        reasons.append('single_domain_material')

    if bool(summary.get('rerank_applied', False)):
        score += 0.03
        reasons.append('rerank_signal_present')

    if int(summary.get('crawl4ai_fallback_used_count') or 0) > 0:
        reasons.append('bm25_fit_fallback_used')

    snippet_only = used_content_kinds == {'search_snippet'} or (
        int(summary.get('snippet_only_count') or 0) > 0
        and 'crawl_markdown' not in used_content_kinds
    )
    if snippet_only:
        score = min(score, 0.45)
        reasons.append('snippet_only_material')

    if (int(summary.get('crawl_empty_count') or 0) + int(summary.get('crawl_error_count') or 0)) > 0:
        reasons.append('crawl_empty_or_error_present')
        if crawl_success_count == 0:
            score -= 0.12

    return score, reasons


def evaluate_web_confidence(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    enabled = bool(data.get('enabled', False))
    status = str(data.get('status') or '').strip().lower()
    summary = _input_summary(data)
    reasons: list[str]

    if not enabled:
        score = 0.0
        reasons = ['confidence_signal_only', 'web_not_enabled']
        fallback_state = FALLBACK_STATE_NOT_APPLICABLE
        fallback_reasons = [FALLBACK_DISABLED_REASON, 'web_not_enabled']
    elif status == 'error':
        score = 0.05
        reasons = ['confidence_signal_only', 'web_status_error']
        fallback_state = FALLBACK_STATE_HUMAN_REVIEW_CANDIDATE
        fallback_reasons = [FALLBACK_DISABLED_REASON, 'human_review_candidate_low_confidence']
    elif bool(data.get('explicit_url_detected', False)):
        score, reasons = _score_explicit_url(summary)
        if status == 'skipped' or int(summary.get('results_count') or 0) == 0:
            score = min(score, 0.18)
            reasons.append('no_data')
        fallback_state = FALLBACK_STATE_FUTURE_ONLY
        fallback_reasons = [FALLBACK_DISABLED_REASON]
        if score < 0.5:
            fallback_state = FALLBACK_STATE_HUMAN_REVIEW_CANDIDATE
            fallback_reasons.append('human_review_candidate_low_confidence')
    elif status == 'skipped' or int(summary.get('results_count') or 0) == 0:
        score = 0.12
        reasons = ['confidence_signal_only', 'no_data']
        fallback_state = FALLBACK_STATE_HUMAN_REVIEW_CANDIDATE
        fallback_reasons = [FALLBACK_DISABLED_REASON, 'human_review_candidate_low_confidence']
    else:
        score, reasons = _score_search(summary)
        fallback_state = FALLBACK_STATE_FUTURE_ONLY
        fallback_reasons = [FALLBACK_DISABLED_REASON]
        if score < 0.5:
            fallback_state = FALLBACK_STATE_HUMAN_REVIEW_CANDIDATE
            fallback_reasons.append('human_review_candidate_low_confidence')

    final_score = _clamp_score(score)
    return {
        'web_confidence_policy_kind': POLICY_KIND,
        'web_confidence_level': _level(final_score, enabled=enabled),
        'web_confidence_score': final_score,
        'web_confidence_reason_codes': _reason_codes(reasons),
        'web_confidence_inputs_summary': summary,
        'openrouter_fallback_state': fallback_state,
        'openrouter_fallback_used': False,
        'openrouter_fallback_reason_codes': _reason_codes(fallback_reasons),
    }
