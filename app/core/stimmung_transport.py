from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


PRIMARY_MODEL = 'google/gemini-3.1-flash-lite'
FALLBACK_MODEL = 'openai/gpt-5.4-nano'
PROVIDER_SCHEMA_NAME = 'stimmung_affective_turn_signal_v1'
PRIMARY_REQUEST_POLICY_VERSION = 'stimmung_request_gemini_3_1_flash_lite_strict_v2'
FALLBACK_REQUEST_POLICY_VERSION = 'stimmung_request_gpt_5_4_nano_fallback_strict_v2'
STANDARD_PROVIDER_ROUTING = {'allow_fallbacks': False, 'require_parameters': True}

_REQUEST_OBSERVABILITY_BASE_KEYS = {
    'stimmung_request_policy_version',
    'stimmung_transport',
    'stimmung_requested_model',
    'stimmung_attempt_decision_source',
    'stimmung_max_tokens_effective',
    'stimmung_timeout_s_effective',
    'stimmung_temperature_sent',
    'stimmung_top_p_sent',
    'stimmung_provider_routing_sent',
    'stimmung_provider_fallbacks_allowed',
    'stimmung_provider_require_parameters',
    'stimmung_response_format_sent',
    'stimmung_response_format_type',
    'stimmung_json_schema_name',
    'stimmung_json_schema_strict',
    'stimmung_json_schema_additional_properties',
}


@dataclass(frozen=True, repr=False)
class PreparedStimmungRequest:
    payload: dict[str, Any] = field(repr=False)
    timeout_s: int
    observability: dict[str, Any]


def _policy_version(*, model: str, decision_source: str) -> str:
    if decision_source == 'primary' and model == PRIMARY_MODEL:
        return PRIMARY_REQUEST_POLICY_VERSION
    if decision_source == 'fallback' and model == FALLBACK_MODEL:
        return FALLBACK_REQUEST_POLICY_VERSION
    return 'unknown'


def _request_observability(
    *,
    payload: Mapping[str, Any],
    decision_source: str,
    timeout_s: int,
) -> dict[str, Any]:
    model = str(payload.get('model') or '')
    policy_version = _policy_version(model=model, decision_source=decision_source)
    temperature_sent = 'temperature' in payload
    top_p_sent = 'top_p' in payload
    provider = payload.get('provider') if isinstance(payload.get('provider'), Mapping) else {}
    response_format = (
        payload.get('response_format')
        if isinstance(payload.get('response_format'), Mapping)
        else {}
    )
    json_schema = (
        response_format.get('json_schema')
        if isinstance(response_format.get('json_schema'), Mapping)
        else {}
    )
    schema = json_schema.get('schema') if isinstance(json_schema.get('schema'), Mapping) else {}
    result = {
        'stimmung_request_policy_version': policy_version,
        'stimmung_transport': 'standard',
        'stimmung_requested_model': model,
        'stimmung_attempt_decision_source': str(decision_source or 'unknown'),
        'stimmung_max_tokens_effective': int(payload.get('max_tokens') or 0),
        'stimmung_timeout_s_effective': int(timeout_s),
        'stimmung_temperature_sent': temperature_sent,
        'stimmung_top_p_sent': top_p_sent,
        'stimmung_provider_routing_sent': bool(provider),
        'stimmung_provider_fallbacks_allowed': provider.get('allow_fallbacks') if provider else None,
        'stimmung_provider_require_parameters': provider.get('require_parameters') if provider else None,
        'stimmung_response_format_sent': bool(response_format),
        'stimmung_response_format_type': str(response_format.get('type') or 'unknown'),
        'stimmung_json_schema_name': str(json_schema.get('name') or 'unknown'),
        'stimmung_json_schema_strict': json_schema.get('strict') if json_schema else None,
        'stimmung_json_schema_additional_properties': schema.get('additionalProperties') if schema else None,
    }
    if temperature_sent:
        result['stimmung_temperature_effective'] = float(payload['temperature'])
    if top_p_sent:
        result['stimmung_top_p_effective'] = float(payload['top_p'])
    if policy_version != 'unknown':
        validate_request_observability(result)
    return result


def validate_request_observability(value: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(value)
    version = str(payload.get('stimmung_request_policy_version') or '')
    expected = {
        PRIMARY_REQUEST_POLICY_VERSION: ('primary', PRIMARY_MODEL, True, True),
        FALLBACK_REQUEST_POLICY_VERSION: ('fallback', FALLBACK_MODEL, False, False),
    }.get(version)
    if expected is None:
        raise ValueError('unknown_stimmung_request_policy_version')
    source, model, temperature_sent, top_p_sent = expected
    expected_keys = set(_REQUEST_OBSERVABILITY_BASE_KEYS)
    if temperature_sent:
        expected_keys.add('stimmung_temperature_effective')
    if top_p_sent:
        expected_keys.add('stimmung_top_p_effective')
    if set(payload) != expected_keys:
        raise ValueError('invalid_stimmung_request_observability_fields')
    if (
        payload.get('stimmung_attempt_decision_source') != source
        or payload.get('stimmung_requested_model') != model
    ):
        raise ValueError('incoherent_stimmung_request_source_or_model')
    if payload.get('stimmung_transport') != 'standard':
        raise ValueError('invalid_stimmung_transport')
    for key in ('stimmung_max_tokens_effective', 'stimmung_timeout_s_effective'):
        if type(payload.get(key)) is not int or payload[key] <= 0:
            raise ValueError(f'incoherent_{key}')
    coherence = (
        ('stimmung_temperature_sent', temperature_sent),
        ('stimmung_top_p_sent', top_p_sent),
        ('stimmung_provider_routing_sent', True),
        ('stimmung_provider_fallbacks_allowed', False),
        ('stimmung_provider_require_parameters', True),
        ('stimmung_response_format_sent', True),
        ('stimmung_response_format_type', 'json_schema'),
        ('stimmung_json_schema_name', PROVIDER_SCHEMA_NAME),
        ('stimmung_json_schema_strict', True),
        ('stimmung_json_schema_additional_properties', False),
    )
    for key, expected_value in coherence:
        if payload.get(key) != expected_value or type(payload.get(key)) is not type(expected_value):
            raise ValueError(f'incoherent_{key}')
    if temperature_sent and type(payload.get('stimmung_temperature_effective')) is not float:
        raise ValueError('incoherent_stimmung_temperature_effective')
    if top_p_sent and type(payload.get('stimmung_top_p_effective')) is not float:
        raise ValueError('incoherent_stimmung_top_p_effective')
    return payload


def prepare_stimmung_request(
    *,
    model: str,
    decision_source: str,
    messages: Sequence[Mapping[str, str]],
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    response_format: Mapping[str, Any],
    llm_module: Any,
) -> PreparedStimmungRequest:
    payload: dict[str, Any] = {
        'model': str(model),
        'messages': list(messages),
        'max_tokens': int(max_tokens),
    }
    policy_version = _policy_version(model=str(model), decision_source=decision_source)
    if policy_version == PRIMARY_REQUEST_POLICY_VERSION:
        payload.update(
            temperature=float(temperature),
            top_p=float(top_p),
            provider=dict(STANDARD_PROVIDER_ROUTING),
            response_format=dict(response_format),
        )
    elif policy_version == FALLBACK_REQUEST_POLICY_VERSION:
        payload.update(
            provider=dict(STANDARD_PROVIDER_ROUTING),
            response_format=dict(response_format),
        )
    else:
        payload.update(temperature=float(temperature), top_p=float(top_p))
    observability = _request_observability(
        payload=payload,
        decision_source=decision_source,
        timeout_s=int(timeout_s),
    )
    return PreparedStimmungRequest(
        payload=llm_module.with_provider_attribution(payload, caller='stimmung_agent'),
        timeout_s=int(timeout_s),
        observability=observability,
    )
