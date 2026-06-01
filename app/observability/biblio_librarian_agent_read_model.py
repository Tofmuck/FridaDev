from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence


_TOKEN_CHARS = set('abcdefghijklmnopqrstuvwxyz0123456789_-.:/')
_HEX_CHARS = set('0123456789abcdef')


def build_biblio_librarian_agent_summary(payload: Mapping[str, Any]) -> dict[str, Any]:
    agent_payload = _mapping(payload.get('librarian_agent'))
    if not agent_payload:
        return {
            'present': False,
            'status': 'not_observed',
            'model_called': False,
            'used_for_response': False,
            'product_response_changed': False,
            'deterministic_controller': True,
            'tool_execution_status': 'not_executed',
            'tool_call_event_count': 0,
            'selection_event_count': 0,
            'state_update_event_count': 0,
            'final_event_count': 0,
            'raw_content_included': False,
        }

    request_observation = _mapping(agent_payload.get('request_observation'))
    deterministic = _mapping(agent_payload.get('deterministic'))
    agent = _mapping(agent_payload.get('agent'))
    validation = _mapping(agent.get('validation'))
    validation_plan = _mapping(validation.get('plan'))
    model = _mapping(agent.get('model'))
    return {
        'present': bool(agent_payload.get('present')),
        'comparison_kind': _token(agent_payload.get('comparison_kind')),
        'status': _token(agent_payload.get('status')),
        'reason_code': _token(agent_payload.get('reason_code')),
        'mode': _token(agent_payload.get('mode')),
        'model_called': bool(agent_payload.get('model_called')),
        'candidate_plan_present': bool(agent_payload.get('candidate_plan_present')),
        'used_for_response': bool(agent_payload.get('used_for_response')),
        'product_response_changed': bool(agent_payload.get('product_response_changed')),
        'deterministic_controller': bool(agent_payload.get('deterministic_controller')),
        'fallback_deterministic': bool(agent_payload.get('fallback_deterministic')),
        'tool_execution_status': _token(agent_payload.get('tool_execution_status')) or 'not_executed',
        'tool_call_event_count': _to_int(agent_payload.get('tool_call_event_count')),
        'selection_event_count': _to_int(agent_payload.get('selection_event_count')),
        'state_update_event_count': _to_int(agent_payload.get('state_update_event_count')),
        'final_event_count': _to_int(agent_payload.get('final_event_count')),
        'agent_loop_executed': bool(agent_payload.get('agent_loop_executed')),
        'request_observation_present': bool(request_observation),
        'user_message_present': bool(request_observation.get('user_message_present')),
        'user_message_chars': _to_int(request_observation.get('user_message_chars')),
        'user_message_hash': _hash(request_observation.get('user_message_hash')),
        'recent_dialogue_count': _to_int(request_observation.get('recent_dialogue_count')),
        'bounded_recent_dialogue_count': _to_int(request_observation.get('bounded_recent_dialogue_count')),
        'recent_dialogue_hashes': _hashes(request_observation.get('recent_dialogue_hashes')),
        'biblio_state_present': bool(request_observation.get('biblio_state_present')),
        'deterministic_plan_present': bool(request_observation.get('deterministic_plan_present')),
        'deterministic_status': _token(deterministic.get('status')),
        'deterministic_reason_code': _token(deterministic.get('reason_code')),
        'deterministic_query_kind': _token(deterministic.get('query_kind')),
        'agent_status': _token(agent.get('status')),
        'agent_reason_code': _token(agent.get('reason_code')),
        'validation_status': _token(validation.get('status')),
        'validation_reason_code': _token(validation.get('reason_code')),
        'validation_tool_call_count': _to_int(validation.get('tool_call_count')),
        'validation_tool_names': _tokens(validation.get('tool_names')),
        'invalid_tool_names': _tokens(validation.get('invalid_tool_names')),
        'json_chars': _to_int(validation.get('json_chars')),
        'json_hash': _hash(validation.get('json_hash')),
        'candidate_plan_intent': _token(validation_plan.get('intent')),
        'candidate_plan_answer_mode': _token(validation_plan.get('answer_mode')),
        'candidate_plan_tool_call_count': _to_int(validation_plan.get('tool_call_count')),
        'candidate_plan_tool_names': _tokens(validation_plan.get('tool_names')),
        'model_status': _token(model.get('status')),
        'model_reason_code': _token(model.get('reason_code')),
        'model_effective': _token(model.get('model_effective'), max_chars=140),
        'finish_reason': _token(model.get('finish_reason')),
        'duration_ms': _to_int(model.get('duration_ms')),
        'status_code': _to_int(model.get('status_code')),
        'response_chars': _to_int(model.get('response_chars')),
        'attempt_count': _to_int(model.get('attempt_count')),
        'fallback_model_used': bool(model.get('fallback_model_used')),
        'primary_reason_code': _token(model.get('primary_reason_code')),
        'raw_content_included': False,
    }


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _to_int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _token(value: Any, *, max_chars: int = 120) -> str | None:
    text = str(value or '').strip()
    if not text:
        return None
    lowered = text.lower()
    if lowered != text:
        return f'sha256:{_sha256_12(text)}'
    if any(char not in _TOKEN_CHARS for char in lowered):
        return f'sha256:{_sha256_12(text)}'
    return lowered[:max_chars]


def _hash(value: Any) -> str | None:
    text = str(value or '').strip().lower()
    if len(text) == 12 and all(char in _HEX_CHARS for char in text):
        return text
    return None


def _hashes(value: Any) -> list[str]:
    hashes: list[str] = []
    for item in _sequence(value):
        digest = _hash(item)
        if digest:
            hashes.append(digest)
    return hashes


def _tokens(value: Any) -> list[str]:
    tokens: list[str] = []
    for item in _sequence(value):
        token = _token(item)
        if token:
            tokens.append(token)
    return tokens[:24]


def _sha256_12(value: Any) -> str:
    return hashlib.sha256(str(value or '').encode('utf-8')).hexdigest()[:12]
