from __future__ import annotations

from typing import Any, Mapping, Sequence


POLICY_KIND = 'local_web_evidence_failure_contract_v0'

STATUS_NOT_APPLICABLE = 'not_applicable'
STATUS_SUFFICIENT = 'sufficient'
STATUS_PARTIAL = 'partial'
STATUS_INSUFFICIENT = 'insufficient'

GUIDANCE_NO_EXTERNAL_FALLBACK = 'no_external_fallback'
GUIDANCE_CAN_ANSWER_WITH_CAVEAT = 'can_answer_with_caveat'
GUIDANCE_STATE_LIMITS_NATURALLY = 'state_evidence_limits_naturally'
GUIDANCE_MAY_PROPOSE_REFORMULATION = 'may_propose_reformulation_if_useful'
GUIDANCE_URL_REQUEST_ONLY_IF_RELEVANT = 'url_request_only_if_relevant'
GUIDANCE_DO_NOT_CLAIM_DIRECT_READ = 'do_not_claim_direct_read'
GUIDANCE_ACKNOWLEDGE_SOURCE_TENSION = 'acknowledge_source_tension_if_relevant'
GUIDANCE_CAN_ANSWER_NORMALLY = 'can_answer_normally_with_sources'

URL_REQUEST_POLICY_ONLY_IF_RELEVANT = 'only_if_relevant_not_default'


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


def _dedupe(values: Sequence[Any]) -> list[str]:
    result: list[str] = []
    for value in values:
        text = str(value or '').strip()
        if text and text not in result:
            result.append(text)
    return result


def _input_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    confidence_summary = _mapping(payload.get('web_confidence_inputs_summary'))
    source_material = [_mapping(item) for item in _sequence(payload.get('source_material_summary'))]
    crawl_summary = [_mapping(item) for item in _sequence(payload.get('crawl4ai_extraction_summary'))]
    used_content_kinds = _dedupe(_sequence(payload.get('used_content_kinds')))
    used_source_count = _to_int(confidence_summary.get('used_source_count'))
    if used_source_count == 0:
        used_source_count = sum(
            1
            for item in source_material
            if bool(item.get('used_in_prompt', False))
            and str(item.get('used_content_kind') or 'none') != 'none'
            and _to_int(item.get('content_chars')) > 0
        )
    crawl_success_count = _to_int(confidence_summary.get('crawl_success_count'))
    crawl_empty_count = _to_int(confidence_summary.get('crawl_empty_count'))
    crawl_error_count = _to_int(confidence_summary.get('crawl_error_count'))
    if not confidence_summary:
        crawl_success_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'success')
        crawl_empty_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'empty')
        crawl_error_count = sum(1 for item in crawl_summary if str(item.get('crawl_status') or '') == 'error')
    snippet_only_count = _to_int(confidence_summary.get('snippet_only_count'))
    if snippet_only_count == 0:
        snippet_only_count = sum(
            1
            for item in source_material
            if bool(item.get('used_in_prompt', False))
            and str(item.get('used_content_kind') or '') == 'search_snippet'
        )
    crawl_failed_used_source_count = _to_int(confidence_summary.get('crawl_failed_used_source_count'))
    if crawl_failed_used_source_count == 0:
        crawl_failed_used_source_count = sum(
            1
            for item in source_material
            if bool(item.get('used_in_prompt', False))
            and str(item.get('used_content_kind') or 'none') != 'none'
            and str(item.get('crawl_status') or '') in {'empty', 'error'}
        )
    return {
        'status': str(payload.get('status') or confidence_summary.get('status') or ''),
        'reason_code': str(payload.get('reason_code') or ''),
        'collection_path': str(payload.get('collection_path') or confidence_summary.get('collection_path') or ''),
        'read_state': str(payload.get('read_state') or confidence_summary.get('read_state') or ''),
        'results_count': _to_int(payload.get('results_count') or confidence_summary.get('results_count')),
        'used_source_count': used_source_count,
        'used_domain_count': _to_int(confidence_summary.get('used_domain_count')),
        'used_content_kinds': used_content_kinds,
        'injected_chars': _to_int(payload.get('injected_chars') or confidence_summary.get('injected_chars')),
        'context_chars': _to_int(payload.get('context_chars') or confidence_summary.get('context_chars')),
        'crawl_success_count': crawl_success_count,
        'crawl_empty_count': crawl_empty_count,
        'crawl_error_count': crawl_error_count,
        'crawl_failed_used_source_count': crawl_failed_used_source_count,
        'snippet_only_count': snippet_only_count,
        'profile_insufficient_evidence': bool(payload.get('profile_insufficient_evidence', False)),
        'profile_expected_material_used': bool(payload.get('profile_expected_material_used', False)),
        'profile_situated_material_used': bool(payload.get('profile_situated_material_used', False)),
        'profile_downrank_material_used': bool(payload.get('profile_downrank_material_used', False)),
        'web_confidence_level': str(payload.get('web_confidence_level') or ''),
        'web_confidence_score': payload.get('web_confidence_score'),
    }


def _profile_insufficient_reason_codes(payload: Mapping[str, Any]) -> list[str]:
    mapped: list[str] = []
    for code in _sequence(payload.get('profile_insufficient_evidence_reason_codes')):
        text = str(code or '').strip()
        if text == 'expected_authority_material_missing':
            mapped.append('expected_source_material_missing')
        elif text == 'situated_secondary_without_official_material':
            mapped.append('situated_secondary_without_official_material')
        elif text == 'snippet_only_profile_material':
            mapped.append('snippet_only_material')
        elif text == 'no_prompt_material':
            mapped.append('no_prompt_material')
        elif text:
            mapped.append(f'profile_{text}')
    return _dedupe(mapped)


def _explicit_url_status(summary: Mapping[str, Any]) -> tuple[str, list[str]]:
    read_state = str(summary.get('read_state') or '')
    if read_state == 'page_read':
        return STATUS_SUFFICIENT, ['explicit_url_page_read']
    if read_state == 'page_partially_read':
        return STATUS_PARTIAL, ['explicit_url_partial_read']
    if read_state == 'page_not_read_snippet_fallback':
        return STATUS_INSUFFICIENT, ['explicit_url_not_read_snippet_fallback']
    if read_state == 'page_not_read_crawl_empty':
        return STATUS_INSUFFICIENT, ['explicit_url_crawl_empty']
    if read_state == 'page_not_read_error':
        return STATUS_INSUFFICIENT, ['explicit_url_crawl_error']
    if read_state:
        return STATUS_INSUFFICIENT, ['explicit_url_not_read']
    return STATUS_INSUFFICIENT, ['explicit_url_read_state_missing']


def _search_status(payload: Mapping[str, Any], summary: Mapping[str, Any]) -> tuple[str, list[str]]:
    status = str(summary.get('status') or '').lower()
    reasons: list[str] = []
    if status == 'error':
        return STATUS_INSUFFICIENT, ['web_status_error']
    if status == 'skipped' or _to_int(summary.get('results_count')) == 0:
        return STATUS_INSUFFICIENT, ['no_results']
    if _to_int(summary.get('used_source_count')) == 0:
        return STATUS_INSUFFICIENT, ['results_found_but_not_read']

    used_content_kinds = set(_sequence(summary.get('used_content_kinds')))
    crawl_empty_or_error = (
        _to_int(summary.get('crawl_empty_count'))
        + _to_int(summary.get('crawl_error_count'))
    ) > 0
    if used_content_kinds == {'search_snippet'} or (
        _to_int(summary.get('snippet_only_count')) > 0
        and 'crawl_markdown' not in used_content_kinds
    ):
        reasons.append('snippet_only_material')
    if crawl_empty_or_error:
        reasons.append('crawl_empty_or_error_present')
        if _to_int(summary.get('crawl_failed_used_source_count')) > 0:
            reasons.append('crawl_failed_prompt_material_used')
        if _to_int(summary.get('crawl_success_count')) == 0:
            reasons.append('crawl_poor_or_absent')
    if bool(summary.get('profile_insufficient_evidence', False)):
        reasons.extend(_profile_insufficient_reason_codes(payload))
    if (
        bool(summary.get('profile_expected_material_used', False))
        and (
            bool(summary.get('profile_situated_material_used', False))
            or bool(summary.get('profile_downrank_material_used', False))
        )
    ):
        reasons.append('mixed_source_signals_visible')

    deduped_reasons = _dedupe(reasons)
    if any(
        code in deduped_reasons
        for code in (
            'expected_source_material_missing',
            'situated_secondary_without_official_material',
            'no_prompt_material',
            'snippet_only_material',
            'crawl_failed_prompt_material_used',
            'crawl_poor_or_absent',
        )
    ):
        return STATUS_PARTIAL, deduped_reasons
    return STATUS_SUFFICIENT, deduped_reasons or ['usable_web_material']


def _guidance_codes(status: str, reasons: Sequence[str]) -> list[str]:
    guidance = [GUIDANCE_NO_EXTERNAL_FALLBACK]
    if status == STATUS_SUFFICIENT:
        guidance.append(GUIDANCE_CAN_ANSWER_NORMALLY)
    elif status in {STATUS_PARTIAL, STATUS_INSUFFICIENT}:
        guidance.extend(
            [
                GUIDANCE_STATE_LIMITS_NATURALLY,
                GUIDANCE_CAN_ANSWER_WITH_CAVEAT,
                GUIDANCE_MAY_PROPOSE_REFORMULATION,
                GUIDANCE_URL_REQUEST_ONLY_IF_RELEVANT,
            ]
        )
    if any(str(reason).startswith('explicit_url_') and str(reason) != 'explicit_url_page_read' for reason in reasons):
        guidance.append(GUIDANCE_DO_NOT_CLAIM_DIRECT_READ)
    if 'mixed_source_signals_visible' in set(reasons):
        guidance.append(GUIDANCE_ACKNOWLEDGE_SOURCE_TENSION)
    return _dedupe(guidance)


def evaluate_web_evidence(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    enabled = bool(data.get('enabled', False))
    summary = _input_summary(data)
    if not enabled:
        status = STATUS_NOT_APPLICABLE
        reasons = ['web_not_enabled']
    elif bool(data.get('explicit_url_detected', False)):
        status, reasons = _explicit_url_status(summary)
        if str(summary.get('status') or '').lower() in {'error', 'skipped'} and 'no_results' not in reasons:
            reasons.append('no_results')
    else:
        status, reasons = _search_status(data, summary)

    reason_codes = _dedupe(reasons)
    guidance_codes = _guidance_codes(status, reason_codes)
    requires_caveat = status in {STATUS_PARTIAL, STATUS_INSUFFICIENT}
    return {
        'web_evidence_policy_kind': POLICY_KIND,
        'web_evidence_status': status,
        'web_evidence_reason_codes': reason_codes,
        'web_evidence_guidance_codes': guidance_codes,
        'web_evidence_inputs_summary': summary,
        'web_evidence_can_answer': status != STATUS_NOT_APPLICABLE,
        'web_evidence_requires_caveat': requires_caveat,
        'web_evidence_can_suggest_reformulation': requires_caveat,
        'web_evidence_url_request_policy': URL_REQUEST_POLICY_ONLY_IF_RELEVANT,
        'web_evidence_external_fallback_used': False,
    }
