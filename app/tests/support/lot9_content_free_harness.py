from __future__ import annotations

import json
import re
from typing import Any, Mapping, Sequence


SYNTHETIC_RAW_SENTINEL = 'LOT9_ARTIFICIAL_RAW_CONTENT_SENTINEL'

OBSERVABILITY_MATRIX = (
    {
        'case_id': 'accepted_compact_status',
        'accepted': True,
        'payload': {
            'status': 'ok',
            'reason_code': 'completed',
            'items_count': 2,
            'content_free': True,
            'raw_content_included': False,
        },
    },
    {
        'case_id': 'accepted_error_codes',
        'accepted': True,
        'payload': {
            'status': 'error',
            'reason_code': 'upstream_error',
            'error_code': 'upstream_error',
            'error_class': 'TimeoutError',
            'raw_error_message_included': False,
        },
    },
    {
        'case_id': 'refused_content_key',
        'accepted': False,
        'payload': {
            'status': 'ok',
            'content': SYNTHETIC_RAW_SENTINEL,
        },
    },
    {
        'case_id': 'refused_unknown_field',
        'accepted': False,
        'payload': {
            'status': 'ok',
            'future_free_text': SYNTHETIC_RAW_SENTINEL,
        },
    },
    {
        'case_id': 'refused_invalid_type',
        'accepted': False,
        'payload': {
            'status': {'value': 'ok'},
        },
    },
    {
        'case_id': 'refused_raw_value_under_code_key',
        'accepted': False,
        'payload': {
            'status': 'error',
            'reason_code': f'raw narrative {SYNTHETIC_RAW_SENTINEL}',
        },
    },
)


SMOKE_SCHEMA_VERSION = 'lot9_smoke_v1'
_ROOT_KEYS = frozenset(
    {
        'schema_version',
        'case_id',
        'status',
        'reason_code',
        'checks',
        'counts',
        'identifiers',
    }
)
_SAFE_CODE = re.compile(r'^[A-Za-z0-9_.:-]{1,160}$')
_SAFE_STATUS = frozenset({'pass', 'fail', 'error', 'skipped'})
_FORBIDDEN_KEY_PARTS = frozenset(
    {
        'content',
        'exception',
        'markdown',
        'message',
        'payload',
        'prompt',
        'query',
        'raw',
        'secret',
        'token',
        'url',
    }
)
_FORBIDDEN_VALUE_PARTS = (
    '://',
    'www.',
    'bearer ',
    'begin private key',
    SYNTHETIC_RAW_SENTINEL.lower(),
)


def _is_safe_code(value: Any) -> bool:
    text = str(value or '')
    lowered = text.lower()
    return bool(_SAFE_CODE.fullmatch(text)) and not any(part in lowered for part in _FORBIDDEN_VALUE_PARTS)


def _assert_safe_key(key: Any) -> str:
    text = str(key or '')
    lowered_parts = {part for part in re.split(r'[^a-z0-9]+', text.lower()) if part}
    if not _SAFE_CODE.fullmatch(text) or lowered_parts & _FORBIDDEN_KEY_PARTS:
        raise ValueError('forbidden smoke key')
    return text


def validate_smoke_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError('smoke record must be an object')
    unknown = set(record) - _ROOT_KEYS
    missing = {'schema_version', 'case_id', 'status', 'reason_code', 'checks'} - set(record)
    if unknown or missing:
        raise ValueError('smoke record schema mismatch')
    if record.get('schema_version') != SMOKE_SCHEMA_VERSION:
        raise ValueError('smoke schema version mismatch')
    if not _is_safe_code(record.get('case_id')):
        raise ValueError('unsafe smoke case id')
    if record.get('status') not in _SAFE_STATUS:
        raise ValueError('unsafe smoke status')
    if not _is_safe_code(record.get('reason_code')):
        raise ValueError('unsafe smoke reason code')

    checks = record.get('checks')
    if not isinstance(checks, Mapping) or not checks:
        raise ValueError('smoke checks must be a non-empty object')
    normalized_checks = {}
    for key, value in checks.items():
        normalized_key = _assert_safe_key(key)
        if not isinstance(value, bool):
            raise ValueError('smoke checks must be boolean')
        normalized_checks[normalized_key] = value

    counts = record.get('counts', {})
    if not isinstance(counts, Mapping):
        raise ValueError('smoke counts must be an object')
    normalized_counts = {}
    for key, value in counts.items():
        normalized_key = _assert_safe_key(key)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError('smoke counts must be non-negative integers')
        normalized_counts[normalized_key] = value

    identifiers = record.get('identifiers', ())
    if not isinstance(identifiers, Sequence) or isinstance(identifiers, (str, bytes, bytearray)):
        raise ValueError('smoke identifiers must be a list')
    normalized_identifiers = []
    for identifier in identifiers:
        if not _is_safe_code(identifier):
            raise ValueError('unsafe smoke identifier')
        normalized_identifiers.append(str(identifier))

    return {
        'schema_version': SMOKE_SCHEMA_VERSION,
        'case_id': str(record['case_id']),
        'status': str(record['status']),
        'reason_code': str(record['reason_code']),
        'checks': dict(sorted(normalized_checks.items())),
        'counts': dict(sorted(normalized_counts.items())),
        'identifiers': sorted(normalized_identifiers),
    }


def parse_smoke_jsonl(text: str) -> tuple[dict[str, Any], ...]:
    lines = str(text or '').splitlines()
    if not lines or any(not line.strip() for line in lines):
        raise ValueError('smoke JSONL requires non-empty lines')
    records = []
    for line in lines:
        try:
            decoded = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError('smoke JSONL is not parseable') from exc
        records.append(validate_smoke_record(decoded))
    return tuple(records)


def encode_smoke_jsonl(records: Sequence[Mapping[str, Any]]) -> str:
    normalized = [validate_smoke_record(record) for record in records]
    if not normalized:
        raise ValueError('smoke JSONL requires records')
    return '\n'.join(
        json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        for record in normalized
    )
