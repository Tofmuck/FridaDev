from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.hermeneutic_node.validation import validation_contract, validation_transport
from core import stimmung_transport
from observability import agentic_status


_LLM_CALL_MAIN_PROVIDER_CALLER = 'llm'
_LLM_CALL_SECONDARY_PROVIDER_CALLERS = (
    'stimmung_agent',
    'validation_agent',
    'web_reformulation',
    'web_discovery',
)
_LLM_CALL_KNOWN_PROVIDER_CALLERS = (
    _LLM_CALL_MAIN_PROVIDER_CALLER,
    *_LLM_CALL_SECONDARY_PROVIDER_CALLERS,
)
_ITEM_STATUSES = (
    'ok',
    'degraded',
    'missing',
    'not_applicable',
    'disabled',
    'not_selected',
    'not_configured',
    'refused',
    'failed',
)
_SCORE_WEIGHTS = {
    'ok': 1.0,
    'degraded': 0.5,
    'failed': 0.5,
    'missing': 0.0,
}
_SCORE_EXCLUDED_ITEM_STATUSES = {
    'not_applicable',
    'disabled',
    'not_selected',
    'not_configured',
    'refused',
}
_LEGACY_CRITICAL_ITEMS = {
    'turn_start',
    'prompt_prepared',
    'turn_end',
}


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _normalize_provider_caller(value: Any) -> str:
    caller = str(value or '').strip().lower()
    if caller in _LLM_CALL_KNOWN_PROVIDER_CALLERS:
        return caller
    return 'unknown'


def _event_payload(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = event.get('payload')
    if not isinstance(payload, Mapping):
        payload = event.get('payload_json')
    if isinstance(payload, Mapping):
        return dict(payload)
    return {}


def _event_stage(event: Mapping[str, Any]) -> str:
    return str(event.get('stage') or '').strip()


def _event_status(event: Mapping[str, Any]) -> str:
    return agentic_status.normalize_status(event.get('status_v1') or event.get('status'))


def _payload_text(payload: Mapping[str, Any], key: str) -> str | None:
    text = str(payload.get(key) or '').strip()
    return text or None


def _compact_reason_from_event(event: Mapping[str, Any]) -> str | None:
    payload = _event_payload(event)
    for key in ('reason_code', 'error_code', 'error_class'):
        text = _payload_text(payload, key)
        if text:
            return text
    return None


def _event_item_status(event: Mapping[str, Any]) -> str:
    status = _event_status(event)
    if status == agentic_status.STATUS_ERROR:
        return 'degraded'
    if status == agentic_status.STATUS_FAILED:
        return 'failed'
    if status in _ITEM_STATUSES:
        return status
    return 'degraded'


def _all_events_non_problem(events: Sequence[Mapping[str, Any]]) -> bool:
    return all(agentic_status.is_non_problem_status(_event_status(event)) for event in events)


def _checklist_item(
    key: str,
    group: str,
    status: str,
    reason_code: str,
    *,
    stage: str | None = None,
    evidence: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    status_s = status if status in _ITEM_STATUSES else 'degraded'
    item: dict[str, Any] = {
        'key': key,
        'group': group,
        'status': status_s,
        'reason_code': str(reason_code or 'unknown'),
    }
    if stage:
        item['stage'] = stage
    compact_evidence = {
        str(k): v
        for k, v in dict(evidence or {}).items()
        if v is not None and isinstance(v, (bool, int, float, str, list, dict))
    }
    if compact_evidence:
        item['evidence'] = compact_evidence
    return item


def _events_by_stage(events: Sequence[Mapping[str, Any]]) -> dict[str, list[Mapping[str, Any]]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for event in events:
        stage = _event_stage(event)
        if not stage:
            continue
        grouped.setdefault(stage, []).append(event)
    return grouped


def _stage_counts(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, int]:
    return {
        stage: len(items)
        for stage, items in sorted(grouped.items())
    }


def _latest_stage_event(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    stage: str,
) -> Mapping[str, Any] | None:
    items = list(grouped.get(stage) or [])
    if not items:
        return None
    return items[-1]


def _stage_presence_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
    group: str,
    stage: str,
) -> dict[str, Any]:
    events = list(grouped.get(stage) or [])
    if not events:
        return _checklist_item(key, group, 'missing', 'missing_stage', stage=stage)
    statuses = {_event_status(event) for event in events}
    if 'ok' in statuses:
        return _checklist_item(
            key,
            group,
            'ok',
            'observed',
            stage=stage,
            evidence={'stage_count': len(events)},
        )
    if _all_events_non_problem(events):
        latest = events[-1]
        item_status = _event_item_status(latest)
        reason = _compact_reason_from_event(latest) or f'{stage}_{item_status}'
        return _checklist_item(
            key,
            group,
            item_status,
            reason,
            stage=stage,
            evidence={'stage_count': len(events), 'stage_statuses': sorted(statuses)},
        )
    reason = _compact_reason_from_event(events[-1]) or 'stage_not_ok'
    return _checklist_item(
        key,
        group,
        'degraded',
        reason,
        stage=stage,
        evidence={'stage_count': len(events), 'stage_statuses': sorted(statuses)},
    )


def _identity_fingerprint_item(prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    fingerprint = prompt_payload.get('identity_prompt_injection')
    if not isinstance(fingerprint, Mapping):
        return _checklist_item(
            'identity_prompt_injection',
            'prompt_fingerprints',
            'degraded',
            'missing_identity_prompt_fingerprint',
            stage='prompt_prepared',
        )
    injected = bool(fingerprint.get('injected'))
    block_present = bool(fingerprint.get('identity_block_present'))
    evidence = {
        'fingerprint_present': True,
        'injected': injected,
        'identity_block_present': block_present,
    }
    if not (injected or block_present):
        return _checklist_item(
            'identity_prompt_injection',
            'prompt_fingerprints',
            'degraded',
            'identity_block_absent',
            stage='prompt_prepared',
            evidence=evidence,
        )
    return _checklist_item(
        'identity_prompt_injection',
        'prompt_fingerprints',
        'ok',
        'observed',
        stage='prompt_prepared',
        evidence=evidence,
    )


def _prompt_fingerprint_item(
    prompt_payload: Mapping[str, Any],
    *,
    key: str,
    field: str,
    empty_reason: str,
    degraded_when_absent: bool = True,
) -> dict[str, Any]:
    fingerprint = prompt_payload.get(field)
    if isinstance(fingerprint, Mapping):
        evidence: dict[str, Any] = {'fingerprint_present': True}
        if 'present' in fingerprint:
            evidence['block_present'] = bool(fingerprint.get('present'))
            if not bool(fingerprint.get('present')) and field == 'hermeneutic_prompt_injection':
                return _checklist_item(
                    key,
                    'prompt_fingerprints',
                    'degraded',
                    'hermeneutic_block_absent',
                    stage='prompt_prepared',
                    evidence=evidence,
                )
        return _checklist_item(
            key,
            'prompt_fingerprints',
            'ok',
            'observed',
            stage='prompt_prepared',
            evidence=evidence,
        )
    if degraded_when_absent:
        return _checklist_item(
            key,
            'prompt_fingerprints',
            'degraded',
            empty_reason,
            stage='prompt_prepared',
        )
    return _checklist_item(
        key,
        'prompt_fingerprints',
        'not_applicable',
        empty_reason,
        stage='prompt_prepared',
    )


def _llm_call_main_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    llm_events = list(grouped.get('llm_call') or [])
    main_events = [
        event
        for event in llm_events
        if _normalize_provider_caller(_event_payload(event).get('provider_caller')) == 'llm'
    ]
    if not main_events:
        unknown_count = sum(
            1
            for event in llm_events
            if _normalize_provider_caller(_event_payload(event).get('provider_caller')) == 'unknown'
        )
        return _checklist_item(
            'llm_call_main',
            'funnel',
            'missing',
            'missing_main_llm_call',
            stage='llm_call',
            evidence={'unknown_llm_call_count': unknown_count, 'llm_call_count': len(llm_events)},
        )
    statuses = {_event_status(event) for event in main_events}
    if 'ok' in statuses:
        return _checklist_item(
            'llm_call_main',
            'funnel',
            'ok',
            'observed',
            stage='llm_call',
            evidence={'main_llm_call_count': len(main_events)},
        )
    if _all_events_non_problem(main_events):
        latest = main_events[-1]
        return _checklist_item(
            'llm_call_main',
            'funnel',
            _event_item_status(latest),
            _compact_reason_from_event(latest) or 'main_llm_call_not_selected',
            stage='llm_call',
            evidence={'main_llm_call_count': len(main_events), 'stage_statuses': sorted(statuses)},
        )
    return _checklist_item(
        'llm_call_main',
        'funnel',
        'degraded',
        _compact_reason_from_event(main_events[-1]) or 'main_llm_call_not_ok',
        stage='llm_call',
        evidence={'main_llm_call_count': len(main_events), 'stage_statuses': sorted(statuses)},
    )


def _persist_assistant_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    persist_events = list(grouped.get('persist_response') or [])
    assistant_final = [
        event
        for event in persist_events
        if _event_payload(event).get('persist_phase') == 'assistant_final'
    ]
    if assistant_final:
        ok_saved = [
            event
            for event in assistant_final
            if _event_status(event) == 'ok' and bool(_event_payload(event).get('conversation_saved'))
        ]
        if ok_saved:
            return _checklist_item(
                'persist_response_assistant_final',
                'funnel',
                'ok',
                'assistant_final_saved',
                stage='persist_response',
                evidence={'assistant_final_count': len(assistant_final)},
            )
        if _all_events_non_problem(assistant_final):
            latest = assistant_final[-1]
            return _checklist_item(
                'persist_response_assistant_final',
                'funnel',
                _event_item_status(latest),
                _compact_reason_from_event(latest) or 'assistant_final_not_applicable',
                stage='persist_response',
                evidence={'assistant_final_count': len(assistant_final)},
            )
        return _checklist_item(
            'persist_response_assistant_final',
            'funnel',
            'degraded',
            _compact_reason_from_event(assistant_final[-1]) or 'assistant_final_not_saved',
            stage='persist_response',
            evidence={'assistant_final_count': len(assistant_final)},
        )
    interrupted = [
        event
        for event in persist_events
        if _event_payload(event).get('persist_phase') == 'assistant_interrupted'
    ]
    if interrupted:
        return _checklist_item(
            'persist_response_assistant_final',
            'funnel',
            'degraded',
            'assistant_interrupted',
            stage='persist_response',
            evidence={'assistant_interrupted_count': len(interrupted)},
        )
    return _checklist_item(
        'persist_response_assistant_final',
        'funnel',
        'missing',
        'missing_assistant_final_persist',
        stage='persist_response',
        evidence={'persist_response_count': len(persist_events)},
    )


def _web_observability_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    turn_start = _latest_stage_event(grouped, 'turn_start')
    turn_payload = _event_payload(turn_start or {})
    web_requested = bool(turn_payload.get('web_search_enabled'))
    web_events = list(grouped.get('web_search') or [])
    if not web_requested and not web_events:
        return _checklist_item(
            'web_search',
            'web',
            'not_applicable',
            'web_not_requested',
            stage='web_search',
            evidence={'web_requested': False},
        )
    if web_requested and not web_events:
        return _checklist_item(
            'web_search',
            'web',
            'missing',
            'missing_web_search_stage',
            stage='web_search',
            evidence={'web_requested': True},
        )

    latest = web_events[-1]
    payload = _event_payload(latest)
    status = _event_status(latest)
    evidence = {
        'web_requested': web_requested,
        'web_event_count': len(web_events),
        'context_injected': bool(payload.get('context_injected')),
        'search_profile': _payload_text(payload, 'search_profile'),
        'query_plan_kind': _payload_text(payload, 'query_plan_kind'),
        'query_count': _to_int(payload.get('query_count')),
        'secondary_query_count': _to_int(payload.get('secondary_query_count')),
        'deduped_result_count': _to_int(payload.get('deduped_result_count')),
        'source_first_policy_kind': _payload_text(payload, 'source_first_policy_kind'),
        'source_first_active': bool(payload.get('source_first_active', False)),
        'source_first_authority': _payload_text(payload, 'source_first_authority'),
        'source_first_product': _payload_text(payload, 'source_first_product'),
        'source_first_probable_domains': [
            str(value)
            for value in payload.get('source_first_probable_domains') or []
            if str(value or '')
        ],
        'source_first_reason_codes': [
            str(value)
            for value in payload.get('source_first_reason_codes') or []
            if str(value or '')
        ],
        'profile_policy_kind': _payload_text(payload, 'profile_policy_kind'),
        'profile_policy_mode': _payload_text(payload, 'profile_policy_mode'),
        'profile_expected_domains': [
            str(value)
            for value in payload.get('profile_expected_domains') or []
            if str(value or '')
        ],
        'profile_secondary_domains': [
            str(value)
            for value in payload.get('profile_secondary_domains') or []
            if str(value or '')
        ],
        'profile_downrank_domains': [
            str(value)
            for value in payload.get('profile_downrank_domains') or []
            if str(value or '')
        ],
        'profile_situated_secondary_domains': [
            str(value)
            for value in payload.get('profile_situated_secondary_domains') or []
            if str(value or '')
        ],
        'profile_policy_reason_codes': [
            str(value)
            for value in payload.get('profile_policy_reason_codes') or []
            if str(value or '')
        ],
        'profile_crawl_top_n_budget': _to_int(payload.get('profile_crawl_top_n_budget')),
        'profile_crawl_max_chars_budget': _to_int(payload.get('profile_crawl_max_chars_budget')),
        'profile_manual_latency_target_s': _to_int(payload.get('profile_manual_latency_target_s')),
        'profile_source_evidence_policy_kind': _payload_text(payload, 'profile_source_evidence_policy_kind'),
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
            str(value)
            for value in payload.get('profile_insufficient_evidence_reason_codes') or []
            if str(value or '')
        ],
        'profile_source_domain_counts': dict(payload.get('profile_source_domain_counts') or {}),
        'searxng_profile_params_kind': _payload_text(payload, 'searxng_profile_params_kind'),
        'searxng_profile_params_policy': _payload_text(payload, 'searxng_profile_params_policy'),
        'searxng_categories': [
            str(value)
            for value in payload.get('searxng_categories') or []
            if str(value or '')
        ],
        'searxng_engines': [
            str(value)
            for value in payload.get('searxng_engines') or []
            if str(value or '')
        ],
        'searxng_time_range': _payload_text(payload, 'searxng_time_range'),
        'searxng_language': _payload_text(payload, 'searxng_language'),
        'searxng_safesearch': _payload_text(payload, 'searxng_safesearch'),
        'searxng_params_reason_codes': [
            str(value)
            for value in payload.get('searxng_params_reason_codes') or []
            if str(value or '')
        ],
        'searxng_hard_parameters': [
            str(value)
            for value in payload.get('searxng_hard_parameters') or []
            if str(value or '')
        ],
        'searxng_soft_signal_policy': _payload_text(payload, 'searxng_soft_signal_policy'),
        'web_discovery_provider': _payload_text(payload, 'web_discovery_provider'),
        'web_discovery_provider_requested': _payload_text(payload, 'web_discovery_provider_requested'),
        'web_discovery_provider_effective': _payload_text(payload, 'web_discovery_provider_effective'),
        'web_discovery_external_used': bool(payload.get('web_discovery_external_used', False)),
        'web_discovery_external_provider': _payload_text(payload, 'web_discovery_external_provider'),
        'web_discovery_external_error_kind': _payload_text(payload, 'web_discovery_external_error_kind'),
        'web_discovery_reason_codes': [
            str(value)
            for value in payload.get('web_discovery_reason_codes') or []
            if str(value or '')
        ],
        'rerank_applied': bool(payload.get('rerank_applied', False)),
        'rerank_policy': _payload_text(payload, 'rerank_policy'),
        'rerank_input_count': _to_int(payload.get('rerank_input_count')),
        'rerank_output_count': _to_int(payload.get('rerank_output_count')),
        'rerank_profile': _payload_text(payload, 'rerank_profile'),
        'rerank_promoted_count': _to_int(payload.get('rerank_promoted_count')),
        'rerank_downranked_count': _to_int(payload.get('rerank_downranked_count')),
        'crawl4ai_policy_kinds': [
            str(value)
            for value in payload.get('crawl4ai_policy_kinds') or []
            if str(value or '')
        ],
        'crawl4ai_filter_counts': dict(payload.get('crawl4ai_filter_counts') or {}),
        'crawl4ai_cache_modes': dict(payload.get('crawl4ai_cache_modes') or {}),
        'crawl4ai_fallback_used_count': _to_int(payload.get('crawl4ai_fallback_used_count')),
        'web_confidence_policy_kind': _payload_text(payload, 'web_confidence_policy_kind'),
        'web_confidence_level': _payload_text(payload, 'web_confidence_level'),
        'web_confidence_score': payload.get('web_confidence_score'),
        'web_confidence_reason_codes': [
            str(value)
            for value in payload.get('web_confidence_reason_codes') or []
            if str(value or '')
        ],
        'web_evidence_policy_kind': _payload_text(payload, 'web_evidence_policy_kind'),
        'web_evidence_status': _payload_text(payload, 'web_evidence_status'),
        'web_evidence_reason_codes': [
            str(value)
            for value in payload.get('web_evidence_reason_codes') or []
            if str(value or '')
        ],
        'web_evidence_guidance_codes': [
            str(value)
            for value in payload.get('web_evidence_guidance_codes') or []
            if str(value or '')
        ],
        'web_evidence_can_answer': bool(payload.get('web_evidence_can_answer', False)),
        'web_evidence_requires_caveat': bool(payload.get('web_evidence_requires_caveat', False)),
        'web_evidence_can_suggest_reformulation': bool(
            payload.get('web_evidence_can_suggest_reformulation', False)
        ),
        'web_evidence_url_request_policy': _payload_text(payload, 'web_evidence_url_request_policy'),
        'web_evidence_external_fallback_used': bool(payload.get('web_evidence_external_fallback_used', False)),
        'openrouter_fallback_state': _payload_text(payload, 'openrouter_fallback_state'),
        'openrouter_fallback_used': bool(payload.get('openrouter_fallback_used', False)),
        'openrouter_fallback_reason_codes': [
            str(value)
            for value in payload.get('openrouter_fallback_reason_codes') or []
            if str(value or '')
        ],
        'results_count': _to_int(payload.get('results_count')),
        'read_state': _payload_text(payload, 'read_state'),
    }
    if not web_requested:
        return _checklist_item(
            'web_search',
            'web',
            'not_applicable',
            _payload_text(payload, 'reason_code') or 'web_not_requested',
            stage='web_search',
            evidence=evidence,
        )
    if status == 'ok':
        return _checklist_item('web_search', 'web', 'ok', 'observed', stage='web_search', evidence=evidence)
    if status == 'skipped' and _payload_text(payload, 'reason_code'):
        return _checklist_item('web_search', 'web', 'ok', 'observed_skipped', stage='web_search', evidence=evidence)
    if agentic_status.is_non_problem_status(status):
        return _checklist_item(
            'web_search',
            'web',
            _event_item_status(latest),
            _compact_reason_from_event(latest) or 'web_search_not_selected',
            stage='web_search',
            evidence=evidence,
        )
    return _checklist_item(
        'web_search',
        'web',
        'degraded',
        _compact_reason_from_event(latest) or 'web_search_not_ok',
        stage='web_search',
        evidence=evidence,
    )


def _secondary_provider_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    key: str,
    prepared_stage: str,
    result_stage: str,
    expected: bool,
    provider_caller: str,
    require_prepared: bool = True,
) -> dict[str, Any]:
    prepared_events = list(grouped.get(prepared_stage) or [])
    result_events = list(grouped.get(result_stage) or [])
    caller_events = [
        event
        for event in grouped.get('llm_call') or []
        if _normalize_provider_caller(_event_payload(event).get('provider_caller')) == provider_caller
    ]
    called = bool(result_events or caller_events)
    if not expected and not prepared_events and not called:
        return _checklist_item(
            key,
            'secondary_providers',
            'not_applicable',
            'not_called',
            evidence={'prepared_count': 0, 'result_count': 0, 'llm_call_count': 0},
        )
    if require_prepared and not prepared_events:
        return _checklist_item(
            key,
            'secondary_providers',
            'degraded',
            'missing_secondary_provider_prepared',
            evidence={
                'prepared_stage': prepared_stage,
                'result_stage': result_stage,
                'result_count': len(result_events),
                'llm_call_count': len(caller_events),
            },
        )
    if provider_caller == 'validation_agent' and prepared_events:
        prepared_payload = _event_payload(prepared_events[-1])
        request_payload = prepared_payload.get('validation_request')
        if isinstance(request_payload, Mapping) and request_payload.get('validation_request_policy_version'):
            try:
                validation_transport.validate_request_observability(request_payload)
            except ValueError as exc:
                return _checklist_item(
                    key,
                    'secondary_providers',
                    'degraded',
                    str(exc.args[0]) if exc.args else 'invalid_validation_request_observability',
                    stage=prepared_stage,
                    evidence={
                        'prepared_count': len(prepared_events),
                        'result_count': len(result_events),
                        'llm_call_count': len(caller_events),
                    },
                )
        projection_claimed = any(
            key in prepared_payload
            for key in (
                'canonical_projection_version',
                'stimmung_delivery_status',
                'stimmung_delivery_reason_code',
            )
        )
        if projection_claimed:
            try:
                projection = validation_contract.validate_canonical_projection_metadata(
                    prepared_payload
                )
            except ValueError:
                return _checklist_item(
                    key,
                    'secondary_providers',
                    'degraded',
                    'invalid_canonical_projection_metadata',
                    stage=prepared_stage,
                    evidence={
                        'prepared_count': len(prepared_events),
                        'result_count': len(result_events),
                        'llm_call_count': len(caller_events),
                    },
                )
            if projection['canonical_projection_budget_exceeded_families']:
                return _checklist_item(
                    key,
                    'secondary_providers',
                    'degraded',
                    'canonical_projection_budget_insufficient',
                    stage=prepared_stage,
                    evidence={
                        'prepared_count': len(prepared_events),
                        'result_count': len(result_events),
                        'llm_call_count': len(caller_events),
                        'budget_exceeded_families_count': len(
                            projection['canonical_projection_budget_exceeded_families']
                        ),
                    },
                )
            if projection['canonical_projection_invalid_families']:
                return _checklist_item(
                    key,
                    'secondary_providers',
                    'degraded',
                    'invalid_canonical_projection_family',
                    stage=prepared_stage,
                    evidence={
                        'prepared_count': len(prepared_events),
                        'result_count': len(result_events),
                        'llm_call_count': len(caller_events),
                        'invalid_families_count': len(
                            projection['canonical_projection_invalid_families']
                        ),
                    },
                )
    if provider_caller == 'stimmung_agent' and prepared_events:
        prepared_payload = _event_payload(prepared_events[-1])
        request_payload = prepared_payload.get('stimmung_request')
        if isinstance(request_payload, Mapping) and request_payload.get('stimmung_request_policy_version'):
            try:
                stimmung_transport.validate_request_observability(request_payload)
            except ValueError as exc:
                return _checklist_item(
                    key,
                    'secondary_providers',
                    'degraded',
                    str(exc.args[0]) if exc.args else 'invalid_stimmung_request_observability',
                    stage=prepared_stage,
                    evidence={
                        'prepared_count': len(prepared_events),
                        'result_count': len(result_events),
                        'llm_call_count': len(caller_events),
                    },
                )
    events = prepared_events + result_events + caller_events
    statuses = {_event_status(event) for event in events}
    if any(status in {agentic_status.STATUS_ERROR, agentic_status.STATUS_FAILED} for status in statuses):
        return _checklist_item(
            key,
            'secondary_providers',
            'degraded',
            _compact_reason_from_event(events[-1]) or 'secondary_provider_error',
            evidence={
                'prepared_count': len(prepared_events),
                'result_count': len(result_events),
                'llm_call_count': len(caller_events),
                'stage_statuses': sorted(statuses),
            },
        )
    if _all_events_non_problem(events) and 'ok' not in statuses:
        latest = events[-1]
        return _checklist_item(
            key,
            'secondary_providers',
            _event_item_status(latest),
            _compact_reason_from_event(latest) or 'secondary_provider_not_selected',
            evidence={
                'prepared_count': len(prepared_events),
                'result_count': len(result_events),
                'llm_call_count': len(caller_events),
                'stage_statuses': sorted(statuses),
            },
        )
    return _checklist_item(
        key,
        'secondary_providers',
        'ok',
        'observed',
        evidence={
            'prepared_count': len(prepared_events),
            'result_count': len(result_events),
            'llm_call_count': len(caller_events),
        },
    )


def _node_state_item(
    grouped: Mapping[str, Sequence[Mapping[str, Any]]],
    *,
    expected: bool,
) -> dict[str, Any]:
    primary_events = list(grouped.get('primary_node') or [])
    if not primary_events:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded' if expected else 'not_applicable',
            'missing_primary_node' if expected else 'primary_node_not_observed',
            stage='primary_node',
        )
    payload = _event_payload(primary_events[-1])
    has_node_state_fields = any(
        key.startswith('node_state_')
        for key in payload.keys()
    )
    evidence = {
        'primary_node_count': len(primary_events),
        'node_state_read_present': bool(payload.get('node_state_read_present')),
        'node_state_read_valid': bool(payload.get('node_state_read_valid')),
        'node_state_write_attempted': bool(payload.get('node_state_write_attempted')),
        'node_state_write_succeeded': bool(payload.get('node_state_write_succeeded')),
        'node_state_write_changed': bool(payload.get('node_state_write_changed')),
        'node_state_schema_version': _payload_text(payload, 'node_state_schema_version'),
        'fail_open': bool(payload.get('fail_open')),
    }
    if not has_node_state_fields:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            'legacy_node_state_unobserved',
            stage='primary_node',
            evidence=evidence,
        )
    if bool(payload.get('fail_open')):
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'reason_code') or 'primary_node_fail_open',
            stage='primary_node',
            evidence=evidence,
        )
    if payload.get('node_state_read_valid') is False:
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'node_state_read_reason_code') or 'node_state_read_invalid',
            stage='primary_node',
            evidence=evidence,
        )
    if bool(payload.get('node_state_write_attempted')) and not bool(payload.get('node_state_write_succeeded')):
        return _checklist_item(
            'node_state',
            'node_state',
            'degraded',
            _payload_text(payload, 'node_state_write_reason_code') or 'node_state_write_failed',
            stage='primary_node',
            evidence=evidence,
        )
    return _checklist_item(
        'node_state',
        'node_state',
        'ok',
        'observed',
        stage='primary_node',
        evidence=evidence,
    )


def _stage_health_item(grouped: Mapping[str, Sequence[Mapping[str, Any]]]) -> dict[str, Any]:
    error_stages: list[str] = []
    skipped_without_reason: list[str] = []
    for stage, events in grouped.items():
        for event in events:
            status = _event_status(event)
            payload = _event_payload(event)
            if status == agentic_status.STATUS_ERROR:
                error_stages.append(stage)
            if status == agentic_status.STATUS_FAILED:
                error_stages.append(stage)
            if status == 'skipped' and not _payload_text(payload, 'reason_code'):
                skipped_without_reason.append(stage)
    if error_stages:
        return _checklist_item(
            'stage_errors',
            'status',
            'degraded',
            'stage_error_present',
            evidence={
                'error_count': len(error_stages),
                'error_stages': sorted(set(error_stages))[:8],
            },
        )
    if skipped_without_reason:
        return _checklist_item(
            'stage_errors',
            'status',
            'degraded',
            'skipped_without_reason_code',
            evidence={
                'skipped_without_reason_count': len(skipped_without_reason),
                'skipped_stages': sorted(set(skipped_without_reason))[:8],
            },
        )
    return _checklist_item('stage_errors', 'status', 'ok', 'observed')


def build_turn_observability_checklist(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Build a content-free completeness checklist for one chat turn.

    This is a derived operator view over existing chat_log_events. It must not
    copy raw payload contents; every item is reduced to statuses, counts,
    booleans and compact reason codes.
    """
    safe_events = [event for event in events if isinstance(event, Mapping)]
    grouped = _events_by_stage(safe_events)
    stage_counts = _stage_counts(grouped)
    prompt_event = _latest_stage_event(grouped, 'prompt_prepared')
    prompt_payload = _event_payload(prompt_event or {})

    hermeneutic_expected = any(
        stage in grouped
        for stage in (
            'hermeneutic_node_insertion',
            'primary_node',
            'stimmung_agent',
            'stimmung_prompt_prepared',
            'validation_agent',
            'validation_prompt_prepared',
        )
    ) or isinstance(prompt_payload.get('hermeneutic_prompt_injection'), Mapping)

    memory_payload = prompt_payload.get('memory_prompt_injection')
    memory_retrieval = prompt_payload.get('memory_retrieval')
    memory_absent_but_explained = (
        isinstance(memory_retrieval, Mapping)
        and str(memory_retrieval.get('reason_code') or '').strip() in {'no_data', 'not_applicable'}
    )

    items = [
        _stage_presence_item(grouped, key='turn_start', group='funnel', stage='turn_start'),
        _stage_presence_item(grouped, key='prompt_prepared', group='funnel', stage='prompt_prepared'),
        _llm_call_main_item(grouped),
        _persist_assistant_item(grouped),
        _stage_presence_item(grouped, key='turn_end', group='funnel', stage='turn_end'),
        _identity_fingerprint_item(prompt_payload),
        (
            _prompt_fingerprint_item(
                prompt_payload,
                key='memory_prompt_injection',
                field='memory_prompt_injection',
                empty_reason='missing_memory_prompt_fingerprint',
            )
            if isinstance(memory_payload, Mapping) or not memory_absent_but_explained
            else _checklist_item(
                'memory_prompt_injection',
                'prompt_fingerprints',
                'not_applicable',
                'no_memory_data',
                stage='prompt_prepared',
                evidence={'memory_retrieval_reason_code': 'no_data'},
            )
        ),
        _prompt_fingerprint_item(
            prompt_payload,
            key='hermeneutic_prompt_injection',
            field='hermeneutic_prompt_injection',
            empty_reason='missing_hermeneutic_prompt_fingerprint',
            degraded_when_absent=hermeneutic_expected,
        ),
        _secondary_provider_item(
            grouped,
            key='stimmung_agent',
            prepared_stage='stimmung_prompt_prepared',
            result_stage='stimmung_agent',
            expected=hermeneutic_expected,
            provider_caller='stimmung_agent',
        ),
        _secondary_provider_item(
            grouped,
            key='validation_agent',
            prepared_stage='validation_prompt_prepared',
            result_stage='validation_agent',
            expected=hermeneutic_expected,
            provider_caller='validation_agent',
        ),
        _secondary_provider_item(
            grouped,
            key='web_reformulation',
            prepared_stage='web_reformulation_prompt_prepared',
            result_stage='web_reformulation',
            expected=False,
            provider_caller='web_reformulation',
        ),
        _secondary_provider_item(
            grouped,
            key='web_discovery',
            prepared_stage='web_discovery_prompt_prepared',
            result_stage='web_discovery',
            expected=False,
            provider_caller='web_discovery',
            require_prepared=False,
        ),
        _web_observability_item(grouped),
        _node_state_item(grouped, expected=hermeneutic_expected),
        _stage_health_item(grouped),
    ]

    status_counts = {
        status: sum(1 for item in items if item.get('status') == status)
        for status in _ITEM_STATUSES
    }
    applicable_items = [
        item for item in items
        if item.get('status') not in _SCORE_EXCLUDED_ITEM_STATUSES
    ]
    if not safe_events:
        score = 0
    elif applicable_items:
        weighted_score = sum(
            _SCORE_WEIGHTS.get(str(item.get('status')), 0.0)
            for item in applicable_items
        )
        score = int(round(100 * weighted_score / len(applicable_items)))
    else:
        score = 0

    missing_keys = {
        str(item.get('key'))
        for item in items
        if item.get('status') == 'missing'
    }
    degraded_count = int(status_counts.get('degraded') or 0) + int(status_counts.get('failed') or 0)
    if not safe_events or missing_keys.intersection(_LEGACY_CRITICAL_ITEMS):
        classification = 'legacy_incomplete'
    elif missing_keys:
        classification = 'partial'
    elif degraded_count:
        classification = 'degraded'
    else:
        classification = 'complete'

    conversation_id = None
    turn_id = None
    for event in safe_events:
        if conversation_id is None:
            conversation_id = str(event.get('conversation_id') or '').strip() or None
        if turn_id is None:
            turn_id = str(event.get('turn_id') or '').strip() or None
        if conversation_id and turn_id:
            break

    return {
        'kind': 'turn_observability_checklist',
        'conversation_id': conversation_id,
        'turn_id': turn_id,
        'events_count': len(safe_events),
        'stage_counts': stage_counts,
        'score': score,
        'classification': classification,
        'status_counts': status_counts,
        'items': items,
    }
