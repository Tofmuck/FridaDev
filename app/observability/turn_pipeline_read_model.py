from __future__ import annotations

from typing import Any, Mapping, Sequence

from core.hermeneutic_node.doctrine import epistemic_regime as epistemic_doctrine
from core.hermeneutic_node.doctrine import judgment_posture as judgment_doctrine
from core.hermeneutic_node.validation import validation_contract, validation_transport
from core import stimmung_transport
from observability import agentic_status
from observability.turn_observability_checklist import build_turn_observability_checklist
from observability.turn_pipeline_biblio_summary import build_biblio_summary
from observability.turn_pipeline_documents_summary import build_documents_summary
from observability.turn_pipeline_memory_summary import build_memory_rag_summary
from observability.turn_pipeline_summary_support import (
    _duration_ms,
    _event_ts,
    _events_for_stage,
    _latest_stage_event,
    _mapping,
    _payload,
    _reason_code,
    _safe_events,
    _sequence,
    _sha256_12_from_payload,
    _stage,
    _status,
    _text,
    _to_bool,
    _to_float,
    _to_int,
)
from observability.turn_pipeline_web_summary import build_web_summary


SCHEMA_VERSION = '1'
_MAIN_PROVIDER_CALLER = 'llm'
_SECONDARY_PROVIDER_CALLERS = (
    ('stimmung', 'stimmung_agent', 'stimmung_prompt_prepared', 'stimmung_agent'),
    ('validation', 'validation_agent', 'validation_prompt_prepared', 'validation_agent'),
    ('web_reformulation', 'web_reformulation', 'web_reformulation_prompt_prepared', 'web_reformulation'),
    ('web_discovery', 'web_discovery', 'web_discovery_prompt_prepared', 'web_discovery'),
)
_SECONDARY_PROVIDER_STATUS_PRECEDENCE = (
    agentic_status.STATUS_ERROR,
    agentic_status.STATUS_FAILED,
    agentic_status.STATUS_REFUSED,
    agentic_status.STATUS_NOT_CONFIGURED,
    agentic_status.STATUS_DISABLED,
    agentic_status.STATUS_NOT_SELECTED,
    agentic_status.STATUS_NOT_APPLICABLE,
    agentic_status.STATUS_SKIPPED,
    agentic_status.STATUS_OK,
)
_KNOWN_PROVIDER_CALLERS = {
    _MAIN_PROVIDER_CALLER,
    'stimmung_agent',
    'validation_agent',
    'web_reformulation',
    'web_discovery',
}


def _status_schema_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    schema_counts: dict[str, int] = {}
    legacy_count = 0
    v1_count = 0
    for event in events:
        payload = _payload(event)
        schema = str(event.get('status_schema_version') or '').strip()
        if not schema:
            schema = agentic_status.projected_schema_version(
                payload=dict(payload),
                status=event.get('status_v1') or event.get('status'),
            )
        schema_counts[schema] = schema_counts.get(schema, 0) + 1
        if schema == agentic_status.STATUS_SCHEMA_VERSION:
            v1_count += 1
        else:
            legacy_count += 1
    if v1_count and legacy_count:
        source_kind = 'mixed_v1_and_legacy'
    elif v1_count:
        source_kind = 'agentic_v1'
    elif legacy_count:
        source_kind = 'legacy'
    else:
        source_kind = 'empty'
    return {
        'source_kind': source_kind,
        'schema_counts': dict(sorted(schema_counts.items())),
        'v1_event_count': v1_count,
        'legacy_event_count': legacy_count,
        'historical_events_reclassified': False,
    }


def _normalize_provider_caller(value: Any) -> str:
    caller = str(value or '').strip().lower()
    if caller in _KNOWN_PROVIDER_CALLERS:
        return caller
    return 'unknown'


def _stage_counts(events: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        stage = _stage(event)
        if not stage:
            continue
        counts[stage] = counts.get(stage, 0) + 1
    return dict(sorted(counts.items()))


def _checklist_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    checklist = build_turn_observability_checklist(events)
    compact_items: list[dict[str, Any]] = []
    for item in checklist.get('items') or []:
        if not isinstance(item, Mapping):
            continue
        status = str(item.get('status') or '').strip()
        if status not in {'missing', 'degraded'}:
            continue
        compact_items.append(
            {
                'key': str(item.get('key') or ''),
                'group': str(item.get('group') or ''),
                'status': status,
                'reason_code': str(item.get('reason_code') or 'unknown'),
                'stage': _text(item.get('stage')),
            }
        )
    return {
        'classification': str(checklist.get('classification') or 'legacy_incomplete'),
        'score': _to_int(checklist.get('score')),
        'status_counts': dict(_mapping(checklist.get('status_counts'))),
        'degraded_or_missing_items': compact_items[:12],
    }


def _persistence_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    persist_events = _events_for_stage(events, 'persist_response')
    assistant_final = [
        event for event in persist_events
        if _payload(event).get('persist_phase') == 'assistant_final'
    ]
    interrupted = [
        event for event in persist_events
        if _payload(event).get('persist_phase') == 'assistant_interrupted'
    ]
    selected = (
        assistant_final[-1]
        if assistant_final
        else (interrupted[-1] if interrupted else (persist_events[-1] if persist_events else None))
    )
    selected_payload = _payload(selected or {})
    assistant_final_saved = any(
        _status(event) == 'ok' and bool(_payload(event).get('conversation_saved'))
        for event in assistant_final
    )
    if assistant_final_saved:
        status = 'saved'
        reason = 'assistant_final_saved'
    elif interrupted:
        status = 'interrupted'
        reason = _reason_code(_payload(interrupted[-1])) or 'assistant_interrupted'
    elif assistant_final:
        status = 'not_saved'
        reason = _reason_code(selected_payload) or 'assistant_final_not_saved'
    else:
        status = 'missing'
        reason = 'missing_assistant_final_persist'
    return {
        'status': status,
        'assistant_final_present': bool(assistant_final),
        'assistant_final_saved': assistant_final_saved,
        'assistant_interrupted': bool(interrupted),
        'reason_code': reason,
        'events_count': len(persist_events),
        'messages_written': _to_int(selected_payload.get('messages_written')),
        'latest_ts': _event_ts(selected or {}),
    }


def _llm_call_summary(event: Mapping[str, Any] | None, *, provider_caller: str) -> dict[str, Any]:
    payload = _payload(event or {})
    return {
        'provider_caller': provider_caller,
        'present': bool(event),
        'status': _status(event or {}) if event else 'missing',
        'duration_ms': _duration_ms(event),
        'response_chars': _to_int(payload.get('response_chars')),
        'model': _text(payload.get('model')),
        'provider_title': _text(payload.get('provider_title')),
        'provider': _text(payload.get('provider')),
        'provider_model': _text(payload.get('provider_model')),
        'reason_code': _reason_code(payload),
        'latest_ts': _event_ts(event or {}),
    }


def _validation_request_summary(
    prepared_event: Mapping[str, Any] | None,
    caller_summary: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _payload(prepared_event or {})
    request_payload = _mapping(payload.get('validation_request'))
    if not request_payload.get('validation_request_policy_version'):
        return {
            'authoritative': False,
            'status': 'unknown',
            'reason_code': 'historical_request_policy_unobserved',
            'requested_model': '',
            'observed_model': _text(caller_summary.get('provider_model')),
            'observed_provider': _text(caller_summary.get('provider')),
        }
    candidate = dict(request_payload)
    candidate.setdefault('validation_requested_model', _text((prepared_event or {}).get('model')))
    candidate.setdefault(
        'validation_attempt_decision_source',
        _text(payload.get('attempt_decision_source')),
    )
    try:
        validated = validation_transport.validate_request_observability(candidate)
    except ValueError as exc:
        return {
            'authoritative': False,
            'status': 'unknown',
            'reason_code': str(exc.args[0]) if exc.args else 'invalid_validation_request_observability',
            'requested_model': _text(candidate.get('validation_requested_model')),
            'observed_model': _text(caller_summary.get('provider_model')),
            'observed_provider': _text(caller_summary.get('provider')),
        }
    return {
        'authoritative': True,
        'status': 'prepared',
        'reason_code': 'observed_effective_request',
        'policy_version': validated['validation_request_policy_version'],
        'transport': validated['validation_transport'],
        'decision_source': validated['validation_attempt_decision_source'],
        'requested_model': validated['validation_requested_model'],
        'observed_model': _text(caller_summary.get('provider_model')),
        'observed_provider': _text(caller_summary.get('provider')),
        'reasoning_effort_requested': validated['validation_reasoning_effort_requested'],
        'reasoning_effort_effective': validated['validation_reasoning_effort_effective'],
        'reasoning_sent': validated['validation_reasoning_sent'],
        'reasoning_excluded': validated['validation_reasoning_excluded'],
        'max_tokens_effective': validated['validation_max_tokens_effective'],
        'temperature_sent': validated['validation_temperature_sent'],
        'top_p_sent': validated['validation_top_p_sent'],
        'provider_routing_sent': validated['validation_provider_routing_sent'],
        'provider_fallbacks_allowed': validated.get('validation_provider_fallbacks_allowed'),
        'provider_require_parameters': validated.get('validation_provider_require_parameters'),
        'response_format_sent': validated.get('validation_response_format_sent'),
        'response_format_type': validated.get('validation_response_format_type'),
        'json_schema_name': validated.get('validation_json_schema_name'),
        'json_schema_strict': validated.get('validation_json_schema_strict'),
        'json_schema_additional_properties': validated.get('validation_json_schema_additional_properties'),
    }


def _stimmung_request_summary(
    prepared_event: Mapping[str, Any] | None,
    caller_summary: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _payload(prepared_event or {})
    request_payload = _mapping(payload.get('stimmung_request'))
    if not request_payload.get('stimmung_request_policy_version'):
        return {
            'authoritative': False,
            'status': 'unknown',
            'reason_code': 'historical_request_policy_unobserved',
            'requested_model': '',
            'observed_model': _text(caller_summary.get('provider_model')),
            'observed_provider': _text(caller_summary.get('provider')),
        }
    try:
        validated = stimmung_transport.validate_request_observability(request_payload)
    except ValueError as exc:
        return {
            'authoritative': False,
            'status': 'unknown',
            'reason_code': str(exc.args[0]) if exc.args else 'invalid_stimmung_request_observability',
            'requested_model': _text(request_payload.get('stimmung_requested_model')),
            'observed_model': _text(caller_summary.get('provider_model')),
            'observed_provider': _text(caller_summary.get('provider')),
        }
    return {
        'authoritative': True,
        'status': 'prepared',
        'reason_code': 'observed_effective_request',
        'policy_version': validated['stimmung_request_policy_version'],
        'transport': validated['stimmung_transport'],
        'decision_source': validated['stimmung_attempt_decision_source'],
        'requested_model': validated['stimmung_requested_model'],
        'observed_model': _text(caller_summary.get('provider_model')),
        'observed_provider': _text(caller_summary.get('provider')),
        'max_tokens_effective': validated['stimmung_max_tokens_effective'],
        'timeout_s_effective': validated['stimmung_timeout_s_effective'],
        'temperature_sent': validated['stimmung_temperature_sent'],
        'temperature_effective': validated.get('stimmung_temperature_effective'),
        'top_p_sent': validated['stimmung_top_p_sent'],
        'top_p_effective': validated.get('stimmung_top_p_effective'),
        'provider_routing_sent': validated['stimmung_provider_routing_sent'],
        'provider_fallbacks_allowed': validated['stimmung_provider_fallbacks_allowed'],
        'provider_require_parameters': validated['stimmung_provider_require_parameters'],
        'response_format_sent': validated['stimmung_response_format_sent'],
        'response_format_type': validated['stimmung_response_format_type'],
        'json_schema_name': validated['stimmung_json_schema_name'],
        'json_schema_strict': validated['stimmung_json_schema_strict'],
        'json_schema_additional_properties': validated['stimmung_json_schema_additional_properties'],
    }


def _secondary_provider_status(status_values: set[str], *, event_present: bool) -> str:
    if not event_present:
        return agentic_status.STATUS_NOT_APPLICABLE
    normalized = {
        agentic_status.normalize_status(status)
        for status in status_values
        if str(status or '').strip()
    }
    for status in _SECONDARY_PROVIDER_STATUS_PRECEDENCE:
        if status in normalized:
            return status
    return agentic_status.STATUS_OK


def _validation_canonical_projection_summary(
    event: Mapping[str, Any] | None,
) -> dict[str, Any]:
    payload = _payload(event or {})
    try:
        projection = validation_contract.validate_canonical_projection_metadata(payload)
    except ValueError as exc:
        validation_error = str(exc.args[0]) if exc.args else 'invalid_canonical_projection_metadata'
        contract_status = (
            'unknown_version'
            if validation_error == 'unknown_canonical_projection_version'
            else 'incomplete_or_incoherent'
        )
        reason_code = (
            validation_error
            if contract_status == 'unknown_version'
            else 'invalid_canonical_projection_metadata'
        )
        return {
            'source_kind': 'validation_prompt_prepared' if event else 'missing',
            'authoritative': False,
            'contract_status': contract_status,
            'projection_version': _text(payload.get('canonical_projection_version')),
            'stimmung_delivery_status': 'unknown',
            'stimmung_delivery_reason_code': reason_code or 'invalid_canonical_projection_metadata',
            'chars': 0,
            'budget_chars': 0,
            'included_families': [],
            'omitted_families': [],
            'no_data_families': [],
            'redundant_families': [],
            'optional_families': [],
            'invalid_families': [],
            'budget_exceeded_families': [],
            'unspecified_families': [],
        }
    return {
        'source_kind': 'validation_prompt_prepared',
        'authoritative': True,
        'contract_status': projection['canonical_projection_contract_status'],
        'projection_version': projection['canonical_projection_version'],
        'stimmung_delivery_status': projection['stimmung_delivery_status'],
        'stimmung_delivery_reason_code': projection['stimmung_delivery_reason_code'],
        'chars': projection['canonical_projection_chars'],
        'budget_chars': projection['canonical_projection_budget_chars'],
        'included_families': projection['canonical_projection_included_families'],
        'omitted_families': projection['canonical_projection_omitted_families'],
        'no_data_families': projection['canonical_projection_no_data_families'],
        'redundant_families': projection['canonical_projection_redundant_families'],
        'optional_families': projection['canonical_projection_optional_families'],
        'invalid_families': projection['canonical_projection_invalid_families'],
        'budget_exceeded_families': projection[
            'canonical_projection_budget_exceeded_families'
        ],
        'unspecified_families': projection['canonical_projection_unspecified_families'],
    }


def _providers_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    llm_events = _events_for_stage(events, 'llm_call')
    main_events = [
        event for event in llm_events
        if _normalize_provider_caller(_payload(event).get('provider_caller')) == _MAIN_PROVIDER_CALLER
    ]
    unknown_count = sum(
        1 for event in llm_events
        if _normalize_provider_caller(_payload(event).get('provider_caller')) == 'unknown'
    )
    main = _llm_call_summary(main_events[-1] if main_events else None, provider_caller=_MAIN_PROVIDER_CALLER)
    if not main_events:
        main['reason_code'] = 'missing_main_llm_call'

    secondary: dict[str, dict[str, Any]] = {}
    for key, provider_caller, prepared_stage, result_stage in _SECONDARY_PROVIDER_CALLERS:
        prepared_events = _events_for_stage(events, prepared_stage)
        result_events = _events_for_stage(events, result_stage)
        caller_events = [
            event for event in llm_events
            if _normalize_provider_caller(_payload(event).get('provider_caller')) == provider_caller
        ]
        latest = (
            caller_events[-1]
            if caller_events
            else (result_events[-1] if result_events else (prepared_events[-1] if prepared_events else None))
        )
        status_values = {_status(event) for event in [*prepared_events, *result_events, *caller_events] if _status(event)}
        event_present = bool(prepared_events or result_events or caller_events)
        status = _secondary_provider_status(status_values, event_present=event_present)
        summary = _llm_call_summary(caller_events[-1] if caller_events else None, provider_caller=provider_caller)
        summary.update(
            {
                'status': status,
                'prepared_present': bool(prepared_events),
                'result_present': bool(result_events),
                'llm_call_present': bool(caller_events),
                'prepared_events_count': len(prepared_events),
                'result_events_count': len(result_events),
                'llm_call_events_count': len(caller_events),
                'reason_code': _reason_code(_payload(latest or {})),
                'latest_ts': _event_ts(latest or {}),
            }
        )
        if key == 'validation':
            prepared_payload = _payload(prepared_events[-1] if prepared_events else {})
            summary['canonical_projection'] = _validation_canonical_projection_summary(
                prepared_events[-1] if prepared_events else None
            )
            summary['attempt_decision_source'] = _text(
                prepared_payload.get('attempt_decision_source')
            )
            summary['validation_status'] = _text(prepared_payload.get('validation_status'))
            summary['request'] = _validation_request_summary(
                prepared_events[-1] if prepared_events else None,
                summary,
            )
        elif key == 'stimmung':
            prepared_payload = _payload(prepared_events[-1] if prepared_events else {})
            summary['attempt_decision_source'] = _text(
                prepared_payload.get('attempt_decision_source')
            )
            summary['stimmung_status'] = _text(prepared_payload.get('stimmung_status'))
            summary['request'] = _stimmung_request_summary(
                prepared_events[-1] if prepared_events else None,
                summary,
            )
        secondary[key] = summary

    return {
        'main': main,
        'secondary': secondary,
        'unknown_llm_call_count': unknown_count,
    }


def _identity_summary(prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    fingerprint = _mapping(prompt_payload.get('identity_prompt_injection'))
    present = bool(fingerprint.get('injected')) or bool(fingerprint.get('identity_block_present'))
    status = 'present' if present else ('missing' if not fingerprint else 'absent')
    used_ids = fingerprint.get('used_identity_ids')
    used_count = (
        len(_sequence(used_ids))
        if used_ids is not None
        else _to_int(fingerprint.get('used_identity_ids_count'))
    )
    return {
        'source_kind': 'prompt_identity_fingerprint' if fingerprint else 'missing',
        'status': status,
        'block_present': bool(fingerprint.get('identity_block_present')),
        'injected': bool(fingerprint.get('injected')),
        'chars': _to_int(
            fingerprint.get('chars')
            or fingerprint.get('identity_block_chars')
            or fingerprint.get('identity_chars')
        ),
        'used_identity_ids_count': used_count,
        'staging_included': bool(fingerprint.get('staging_included')),
        'reason_code': _reason_code(fingerprint),
    }


def _dialogic_effects_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    values = {
        'epistemic_effect': _text(payload.get('epistemic_effect')),
        'epistemic_source': _text(payload.get('epistemic_source')),
        'epistemic_reason_code': _text(payload.get('epistemic_reason_code')),
        'enunciation_effect': _text(payload.get('enunciation_effect')),
        'enunciation_source': _text(payload.get('enunciation_source')),
        'enunciation_reason_code': _text(payload.get('enunciation_reason_code')),
    }
    if not all(values.values()):
        return {
            'authoritative': False,
            'status': 'unknown',
            **{key: 'unknown' for key in values},
        }

    fail_open = (
        values['epistemic_effect'] == 'unknown'
        and values['epistemic_source'] == 'fail_open'
        and values['enunciation_effect'] == 'unknown'
        and values['enunciation_source'] == 'fail_open'
        and values['epistemic_reason_code'] == values['enunciation_reason_code']
        and values['epistemic_reason_code'] in epistemic_doctrine.EPISTEMIC_FAIL_OPEN_REASON_CODES
    )
    epistemic_reasons_by_effect = epistemic_doctrine.EPISTEMIC_REASON_CODES_BY_EFFECT
    enunciation_success = (
        values['enunciation_effect'] == 'delicate_expression'
        and values['enunciation_source'] == 'stimmung'
        and values['enunciation_reason_code'] == 'affective_transition'
        or values['enunciation_effect'] == 'none'
        and (
            values['enunciation_source'] == 'not_applicable'
            and values['enunciation_reason_code'] == 'stimmung_absent'
            or values['enunciation_source'] == 'stimmung'
            and values['enunciation_reason_code'] in {'stimmung_stable', 'stimmung_no_transition'}
        )
    )
    success = (
        values['epistemic_effect'] in epistemic_reasons_by_effect
        and values['epistemic_source'] == 'epistemic_inputs'
        and values['epistemic_reason_code'] in epistemic_reasons_by_effect[values['epistemic_effect']]
        and values['enunciation_effect'] in judgment_doctrine.ENUNCIATION_EFFECTS
        and values['enunciation_source'] in judgment_doctrine.ENUNCIATION_SOURCES
        and values['enunciation_reason_code'] in judgment_doctrine.ENUNCIATION_REASON_CODES
        and enunciation_success
    )
    if not (fail_open or success):
        return {
            'authoritative': False,
            'status': 'unknown',
            **{key: 'unknown' for key in values},
        }
    return {
        'authoritative': True,
        'status': 'fail_open' if fail_open else 'success',
        **values,
    }


def _hermeneutic_summary(events: Sequence[Mapping[str, Any]], prompt_payload: Mapping[str, Any]) -> dict[str, Any]:
    fingerprint = _mapping(prompt_payload.get('hermeneutic_prompt_injection'))
    present = bool(fingerprint.get('present'))
    status = 'present' if present else ('missing' if not fingerprint else 'absent')
    primary = _latest_stage_event(events, 'primary_node')
    primary_payload = _payload(primary or {})
    validation = _latest_stage_event(events, 'validation_agent')
    effect_payload = _payload(validation or {}) if validation else primary_payload
    node_state = {
        'primary_node_present': bool(primary),
        'read_present': bool(primary_payload.get('node_state_read_present')),
        'read_valid': bool(primary_payload.get('node_state_read_valid')),
        'read_reason_code': _text(primary_payload.get('node_state_read_reason_code')),
        'write_attempted': bool(primary_payload.get('node_state_write_attempted')),
        'write_succeeded': bool(primary_payload.get('node_state_write_succeeded')),
        'write_changed': bool(primary_payload.get('node_state_write_changed')),
        'write_reason_code': _text(primary_payload.get('node_state_write_reason_code')),
        'schema_version': _text(primary_payload.get('node_state_schema_version')),
        'sha256_12': _sha256_12_from_payload(primary_payload, 'node_state_sha256_12'),
        'fail_open': bool(primary_payload.get('fail_open')),
        'fallback_used': bool(primary_payload.get('fallback_used')),
        'reason_code': _reason_code(primary_payload),
    }
    return {
        'source_kind': 'prompt_hermeneutic_fingerprint' if fingerprint else 'missing',
        'status': status,
        'block_present': present,
        'chars': _to_int(fingerprint.get('chars')),
        'sha256_12': _sha256_12_from_payload(fingerprint, 'sha256_12'),
        'final_posture': _text(fingerprint.get('posture') or fingerprint.get('final_posture')),
        'epistemic_regime': _text(fingerprint.get('epistemic_regime')),
        'fallback': bool(fingerprint.get('fallback')),
        'reason_code': _reason_code(fingerprint),
        'dialogic_effects': _dialogic_effects_summary(effect_payload),
        'node_state': node_state,
    }


def _latencies_summary(events: Sequence[Mapping[str, Any]], providers: Mapping[str, Any]) -> dict[str, Any]:
    turn_end = _latest_stage_event(events, 'turn_end')
    turn_payload = _payload(turn_end or {})
    secondary = _mapping(providers.get('secondary'))
    secondary_duration = sum(
        _to_int(_mapping(item).get('duration_ms'))
        for item in secondary.values()
        if isinstance(item, Mapping)
    )
    return {
        'total_duration_ms': (
            _to_int(turn_payload.get('total_duration_ms'))
            if turn_payload.get('total_duration_ms') is not None
            else None
        ),
        'main_llm_duration_ms': _mapping(providers.get('main')).get('duration_ms'),
        'secondary_llm_duration_ms_total': secondary_duration,
        'observed_duration_ms_total': sum(
            _to_int(event.get('duration_ms'))
            for event in events
            if event.get('duration_ms') is not None
        ),
    }


def _errors_summary(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_stage_status: dict[tuple[str, str, str], int] = {}
    problem_by_stage_status: dict[tuple[str, str, str], int] = {}
    non_problem_by_stage_status: dict[tuple[str, str, str], int] = {}
    reason_code_counts: dict[str, int] = {}
    problem_reason_code_counts: dict[str, int] = {}
    non_problem_reason_code_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}
    fallback_count = 0
    error_count = 0
    failed_count = 0
    refused_count = 0
    not_applicable_count = 0
    not_selected_count = 0
    not_configured_count = 0
    disabled_count = 0
    skipped_count = 0
    for event in events:
        status = _status(event)
        payload = _payload(event)
        stage = _stage(event) or 'unknown'
        reason = _reason_code(payload) or 'unknown'
        status_counts[status] = status_counts.get(status, 0) + 1
        if status == agentic_status.STATUS_ERROR:
            error_count += 1
        elif status == agentic_status.STATUS_FAILED:
            failed_count += 1
        elif status == agentic_status.STATUS_REFUSED:
            refused_count += 1
        elif status == agentic_status.STATUS_NOT_APPLICABLE:
            not_applicable_count += 1
        elif status == agentic_status.STATUS_NOT_SELECTED:
            not_selected_count += 1
        elif status == agentic_status.STATUS_NOT_CONFIGURED:
            not_configured_count += 1
        elif status == agentic_status.STATUS_DISABLED:
            disabled_count += 1
        elif status == agentic_status.STATUS_SKIPPED:
            skipped_count += 1

        if status in agentic_status.ATTEMPT_FAILURE_STATUSES:
            key = (stage, status, reason)
            by_stage_status[key] = by_stage_status.get(key, 0) + 1
            problem_by_stage_status[key] = problem_by_stage_status.get(key, 0) + 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
            problem_reason_code_counts[reason] = problem_reason_code_counts.get(reason, 0) + 1
        elif status != agentic_status.STATUS_OK:
            key = (stage, status, reason)
            by_stage_status[key] = by_stage_status.get(key, 0) + 1
            non_problem_by_stage_status[key] = non_problem_by_stage_status.get(key, 0) + 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
            non_problem_reason_code_counts[reason] = non_problem_reason_code_counts.get(reason, 0) + 1
        if bool(payload.get('fail_open')) or bool(payload.get('fallback_used')):
            fallback_count += 1
            reason_code_counts[reason] = reason_code_counts.get(reason, 0) + 1
            problem_reason_code_counts[reason] = problem_reason_code_counts.get(reason, 0) + 1
            key = (stage, 'fallback', reason)
            problem_by_stage_status[key] = problem_by_stage_status.get(key, 0) + 1
    stages = [
        {
            'stage': stage,
            'status': status,
            'reason_code': reason,
            'count': count,
        }
        for (stage, status, reason), count in sorted(by_stage_status.items())
    ]
    problem_stages = [
        {
            'stage': stage,
            'status': status,
            'reason_code': reason,
            'count': count,
        }
        for (stage, status, reason), count in sorted(problem_by_stage_status.items())
    ]
    non_problem_stages = [
        {
            'stage': stage,
            'status': status,
            'reason_code': reason,
            'count': count,
        }
        for (stage, status, reason), count in sorted(non_problem_by_stage_status.items())
    ]
    attempt_failure_count = error_count + failed_count
    non_problem_status_count = (
        refused_count
        + not_applicable_count
        + not_selected_count
        + not_configured_count
        + disabled_count
        + skipped_count
    )
    return {
        'error_count': error_count,
        'failed_count': failed_count,
        'attempt_failure_count': attempt_failure_count,
        'problem_count': attempt_failure_count + fallback_count,
        'refused_count': refused_count,
        'not_applicable_count': not_applicable_count,
        'not_selected_count': not_selected_count,
        'not_configured_count': not_configured_count,
        'disabled_count': disabled_count,
        'skipped_count': skipped_count,
        'non_problem_status_count': non_problem_status_count,
        'fallback_count': fallback_count,
        'status_counts': dict(sorted(status_counts.items())),
        'reason_code_counts': dict(sorted(reason_code_counts.items())),
        'problem_reason_code_counts': dict(sorted(problem_reason_code_counts.items())),
        'non_problem_reason_code_counts': dict(sorted(non_problem_reason_code_counts.items())),
        'stages': stages[:16],
        'problem_stages': problem_stages[:16],
        'non_problem_stages': non_problem_stages[:16],
    }


def build_turn_pipeline_item(
    events: Sequence[Mapping[str, Any]],
    *,
    events_total: int | None = None,
    events_truncated: bool = False,
) -> dict[str, Any]:
    """Build one content-free cockpit row for a chat turn.

    The projection is derived from existing chat log events and prompt
    fingerprints. It never includes raw event payloads.
    """
    safe_events = _safe_events(events)
    first = safe_events[0] if safe_events else {}
    latest = safe_events[-1] if safe_events else {}
    conversation_id = _text(first.get('conversation_id'))
    turn_id = _text(first.get('turn_id'))
    prompt_payload = _payload(_latest_stage_event(safe_events, 'prompt_prepared') or {})
    checklist = _checklist_summary(safe_events)
    providers = _providers_summary(safe_events)
    rag = build_memory_rag_summary(safe_events, prompt_payload)

    classification = str(checklist.get('classification') or 'legacy_incomplete')
    legacy_reason = None
    if classification == 'legacy_incomplete':
        legacy_reason = 'legacy_incomplete'
    elif rag.get('legacy_reason_code'):
        legacy_reason = str(rag.get('legacy_reason_code'))

    events_read = len(safe_events)
    total = events_read if events_total is None else _to_int(events_total)
    return {
        'kind': 'chat_turn_pipeline_item',
        'schema_version': SCHEMA_VERSION,
        'conversation_id': conversation_id,
        'turn_id': turn_id,
        'first_ts': _event_ts(first),
        'latest_ts': _event_ts(latest),
        'classification': classification,
        'score': checklist.get('score'),
        'checklist': checklist,
        'persistence': _persistence_summary(safe_events),
        'providers': providers,
        'rag': rag,
        'identity': _identity_summary(prompt_payload),
        'hermeneutic': _hermeneutic_summary(safe_events, prompt_payload),
        'web': build_web_summary(safe_events),
        'documents': build_documents_summary(safe_events),
        'biblio': build_biblio_summary(safe_events),
        'latencies': _latencies_summary(safe_events, providers),
        'errors': _errors_summary(safe_events),
        'status_schema': _status_schema_summary(safe_events),
        'stage_counts': _stage_counts(safe_events),
        'flags': {
            'events_truncated': bool(events_truncated),
            'source_kind': 'chat_log_events',
            'legacy_reason_code': legacy_reason,
            'raw_event_payloads_included': False,
        },
        'source': {
            'events_total': total,
            'events_read': events_read,
            'events_truncated': bool(events_truncated),
            'source_kind': 'chat_log_events',
            'memory_chain_snapshot_present': bool(_latest_stage_event(safe_events, 'memory_chain_snapshot')),
        },
    }
