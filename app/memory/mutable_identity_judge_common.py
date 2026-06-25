from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import config


WINDOW_PAIRS_COUNT = 5
MODEL_SLOT = 'identity_periodic_model'
CALLER = 'mutable_identity_judge'
JUDGE_WINDOW_MAX_CHARS = 32_000
JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT = 12_000

TECHNICAL_REASON_CODES = {
    'window_too_large',
    'judge_timeout',
    'judge_transport_error',
    'judge_invalid_json',
    'schema_invalid',
    'invalid_subject',
    'invalid_verdict',
    'invalid_operation',
    'empty_proposition',
    'proposition_too_long',
    'prompt_like_content',
    'non_declarative_content',
    'non_ontological_proposition',
    'invalid_subject_name',
    'impossible_mutation',
    'mutable_content_too_long',
    'runtime_safety_violation',
    'mutable_store_unavailable',
    'canonical_write_failed',
}

_CODE_RE = re.compile(r'^[A-Za-z0-9_:-]{1,80}$')
_RAW_ANNOTATION_KEYS = {
    'content',
    'text',
    'raw',
    'prompt',
    'message',
    'messages',
    'proposition',
    'excerpt',
    'preview',
}


def text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def content_text(value: Any) -> str:
    if value is None:
        return ''
    return str(value)


def mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def list_value(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


def identity_text(value: Any) -> str:
    if isinstance(value, Mapping):
        return text(value.get('content'))
    return text(value)


def normalize_message(value: Any, *, expected_role: str) -> dict[str, Any]:
    payload = mapping(value)
    role = text(payload.get('role')).lower()
    if role != expected_role:
        raise ValueError('window_pair_role_mismatch')
    normalized = {
        'role': expected_role,
        'content': content_text(payload.get('content')),
    }
    for optional_key in ('timestamp', 'temporal_source_guard', 'source_guard', 'source_id'):
        optional_value = text(payload.get(optional_key))
        if optional_value:
            normalized[optional_key] = optional_value
    return normalized


def normalize_pair(value: Any, *, index: int) -> dict[str, Any]:
    if isinstance(value, Mapping) and 'user' in value and 'assistant' in value:
        user_message = value.get('user')
        assistant_message = value.get('assistant')
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        items = list(value)
        if len(items) != 2:
            raise ValueError('window_pair_incomplete')
        user_message, assistant_message = items
    else:
        raise ValueError('window_pair_invalid')

    return {
        'id': f'pair_{index:02d}',
        'user': normalize_message(user_message, expected_role='user'),
        'assistant': normalize_message(assistant_message, expected_role='assistant'),
    }


def normalize_window_pairs(window_pairs: Sequence[Any]) -> list[dict[str, Any]]:
    pairs = list(window_pairs or [])
    if len(pairs) != WINDOW_PAIRS_COUNT:
        raise ValueError('window_pairs_count_invalid')
    return [normalize_pair(pair, index=index) for index, pair in enumerate(pairs, start=1)]


def compact_annotation_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        compact: dict[str, Any] = {}
        for raw_key, raw_item in value.items():
            key = text(raw_key)
            if not key or key.lower() in _RAW_ANNOTATION_KEYS:
                continue
            compact[key] = compact_annotation_value(raw_item)
        return compact
    if isinstance(value, list):
        return [compact_annotation_value(item) for item in value]
    if isinstance(value, tuple):
        return [compact_annotation_value(item) for item in value]
    if isinstance(value, bool) or value is None:
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return round(float(value), 6)
    text_value = text(value)
    if not text_value:
        return ''
    if _CODE_RE.fullmatch(text_value):
        return text_value
    return {
        'present': True,
        'chars': len(text_value),
    }


def normalized_identities(identities: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    source = mapping(identities)
    return {
        subject: {
            'static': identity_text(mapping(source.get(subject)).get('static')),
            'mutable_current': identity_text(mapping(source.get(subject)).get('mutable_current')),
        }
        for subject in ('llm', 'user')
    }


def normalized_budget(mutable_budget: Mapping[str, Any]) -> dict[str, int]:
    budget = mapping(mutable_budget)
    return {
        'target_chars': int(budget.get('target_chars') or config.IDENTITY_MUTABLE_TARGET_CHARS),
        'max_chars': int(budget.get('max_chars') or config.IDENTITY_MUTABLE_MAX_CHARS),
    }


def _runtime_payload_value(payload: Mapping[str, Any], field: str, default: Any) -> Any:
    field_payload = payload.get(field)
    if not isinstance(field_payload, Mapping):
        return default
    resolved = field_payload.get('value')
    if resolved in (None, ''):
        return default
    return resolved


def runtime_model_settings() -> dict[str, Any]:
    from admin import runtime_settings

    view = runtime_settings.get_identity_periodic_model_settings()
    payload = view.payload
    return {
        'model': text(_runtime_payload_value(payload, 'model', config.IDENTITY_PERIODIC_MODEL))
        or config.IDENTITY_PERIODIC_MODEL,
        'temperature': float(_runtime_payload_value(payload, 'temperature', config.IDENTITY_PERIODIC_TEMPERATURE)),
        'top_p': float(_runtime_payload_value(payload, 'top_p', config.IDENTITY_PERIODIC_TOP_P)),
        'max_tokens': int(_runtime_payload_value(payload, 'max_tokens', config.IDENTITY_PERIODIC_MAX_TOKENS)),
        'timeout_s': int(_runtime_payload_value(payload, 'timeout_s', config.IDENTITY_PERIODIC_TIMEOUT_S)),
    }
