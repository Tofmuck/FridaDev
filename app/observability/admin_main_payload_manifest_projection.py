from __future__ import annotations

import re
from typing import Any, Mapping


SCHEMA_VERSION = 'main_payload_manifest_v1'

_MAX_MAPPING_KEYS = 32
_MAX_LIST_ITEMS = 8
_MAX_DEPTH = 5
_REDACTED = '[redacted]'

_SAFE_CODE_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,159}$')
_SAFE_MODEL_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$')

_SAFE_TEXT_KEYS = {
    'activation_mode',
    'content_kind',
    'conversation_state_kind',
    'exclusion_reason_code',
    'hash_policy',
    'mode',
    'model',
    'origin',
    'origin_stage',
    'policy',
    'priority_policy',
    'provider',
    'provider_family',
    'provider_role',
    'query_kind',
    'reason_code',
    'schema_version',
    'scope',
    'source',
    'status',
}

_SAFE_TEXT_LIST_KEYS = {
    'exclusion_reason_codes',
    'logical_roles',
    'provider_role_sequence',
    'reason_codes',
}

_TOP_LEVEL_KEYS = {
    'assistant_output_policy',
    'budgets',
    'conversation_id_present',
    'conversation_state',
    'final_response_lock',
    'hash_policy',
    'lane_statuses',
    'main_model_called',
    'messages',
    'provider',
    'raw_flags',
    'runtime_settings',
    'schema_version',
    'scope',
    'turn_id_present',
    'windows',
}

_MESSAGE_KEYS = {
    'content_chars',
    'content_kind',
    'content_parts_count',
    'content_present',
    'estimated_tokens',
    'excluded',
    'exclusion_reason_code',
    'file_part_count',
    'image_part_count',
    'index',
    'logical_roles',
    'origin',
    'origin_stage',
    'provider_role',
    'raw_content_included',
    'text_part_count',
}

_LANE_STATUS_KEYS = {
    'activation_mode',
    'budget',
    'content_chars',
    'context_hint_count',
    'context_injected',
    'enabled',
    'estimated_tokens',
    'excluded_count',
    'exclusion_reason_codes',
    'final_response_lock_present',
    'injected_count',
    'input_count',
    'invalid_requested_count',
    'media_kind_counts',
    'mode',
    'model_called',
    'origin',
    'over_limit_count',
    'passage_count',
    'query_kind',
    'raw_lane_content_included',
    'reason_code',
    'reason_codes',
    'selected',
    'source_count',
    'status',
}

_DANGEROUS_VALUE_PARTS = (
    'api-key',
    'api_key',
    'authorization',
    'bearer',
    'caldav',
    'cookie',
    'credential',
    'etag',
    'password',
    'secret',
    'token',
    'webdav',
)


def is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get('schema_version') or '').strip() == SCHEMA_VERSION


def _safe_key(key: Any) -> str:
    return str(key or '').strip()


def _looks_dangerous_text(value: str, *, allow_model_path: bool = False) -> bool:
    lower = value.lower()
    if '://' in lower or lower.startswith(('http:', 'https:', 'www.')):
        return True
    if any(part in lower for part in _DANGEROUS_VALUE_PARTS):
        return True
    if lower.startswith(('begin:', '<?xml', 'dav:', 'xml:')) or '</' in lower:
        return True
    if any(char in value for char in ('@', '\\', '?', '#', '&', '=', '<', '>', '\r', '\n', ':')):
        return True
    if '/' in value and not allow_model_path:
        return True
    return False


def _is_safe_text_value(key: str, value: Any) -> bool:
    text = str(value or '').strip()
    lower = str(key or '').strip().lower()
    if lower == 'model':
        return not _looks_dangerous_text(text, allow_model_path=True) and bool(
            _SAFE_CODE_RE.fullmatch(text) or _SAFE_MODEL_RE.fullmatch(text)
        )
    if _looks_dangerous_text(text):
        return False
    return bool(_SAFE_CODE_RE.fullmatch(text))


def _project_string(key: str, value: Any, stats: dict[str, int]) -> str:
    if key.lower() in _SAFE_TEXT_KEYS and _is_safe_text_value(key, value):
        return str(value).strip()
    stats['redacted_values'] += 1
    return _REDACTED


def _project_list(key: str, values: list[Any], stats: dict[str, int], depth: int) -> Any:
    if depth >= _MAX_DEPTH:
        stats['redacted_values'] += len(values)
        return {'items_count': len(values), 'redacted_items_count': len(values)}
    projected: list[Any] = []
    redacted = 0
    for value in values[:_MAX_LIST_ITEMS]:
        before = stats['redacted_values']
        if isinstance(value, str) and key.lower() in _SAFE_TEXT_LIST_KEYS:
            if _is_safe_text_value(key, value):
                projected.append(value.strip())
            else:
                stats['redacted_values'] += 1
                projected.append(_REDACTED)
        else:
            projected.append(_project_value(key, value, stats, depth + 1))
        if stats['redacted_values'] > before:
            redacted += 1
    truncated = max(0, len(values) - _MAX_LIST_ITEMS)
    if truncated:
        stats['redacted_values'] += truncated
    if redacted or truncated:
        return {'items_count': len(values), 'preview': projected, 'redacted_items_count': redacted + truncated}
    return projected


def _project_mapping(
    payload: Mapping[str, Any],
    stats: dict[str, int],
    depth: int,
    *,
    allowed_keys: set[str] | None = None,
) -> dict[str, Any]:
    if depth >= _MAX_DEPTH:
        stats['redacted_keys'] += len(payload)
        return {'keys_count': len(payload), 'redacted_keys_count': len(payload)}
    projected: dict[str, Any] = {}
    keys = sorted(_safe_key(key) for key in payload.keys())
    for key in keys[:_MAX_MAPPING_KEYS]:
        if not key:
            stats['redacted_keys'] += 1
            continue
        lower = key.lower()
        if allowed_keys is not None and lower not in allowed_keys:
            stats['redacted_keys'] += 1
            continue
        projected[key] = _project_value(key, payload.get(key), stats, depth + 1)
    remaining = max(0, len(keys) - _MAX_MAPPING_KEYS)
    if remaining:
        stats['redacted_keys'] += remaining
        projected['truncated_keys_count'] = remaining
    return projected


def _project_messages(values: Any, stats: dict[str, int], depth: int) -> Any:
    if not isinstance(values, list):
        stats['redacted_values'] += 1
        return {'items_count': 0, 'redacted_items_count': 1}
    return _project_list_of_mappings(values, stats, depth, allowed_keys=_MESSAGE_KEYS)


def _project_lane_statuses(values: Any, stats: dict[str, int], depth: int) -> Any:
    if not isinstance(values, Mapping):
        stats['redacted_values'] += 1
        return {'keys_count': 0, 'redacted_keys_count': 1}
    projected: dict[str, Any] = {}
    for key in sorted(_safe_key(key) for key in values.keys())[:_MAX_MAPPING_KEYS]:
        if not key or _looks_dangerous_text(key):
            stats['redacted_keys'] += 1
            continue
        value = values.get(key)
        if isinstance(value, Mapping):
            projected[key] = _project_mapping(value, stats, depth + 1, allowed_keys=_LANE_STATUS_KEYS)
        else:
            stats['redacted_values'] += 1
            projected[key] = _REDACTED
    return projected


def _project_list_of_mappings(
    values: list[Any],
    stats: dict[str, int],
    depth: int,
    *,
    allowed_keys: set[str],
) -> Any:
    projected: list[Any] = []
    redacted = 0
    for value in values[:_MAX_LIST_ITEMS]:
        if isinstance(value, Mapping):
            projected.append(_project_mapping(value, stats, depth + 1, allowed_keys=allowed_keys))
        else:
            stats['redacted_values'] += 1
            redacted += 1
            projected.append(_REDACTED)
    truncated = max(0, len(values) - _MAX_LIST_ITEMS)
    if truncated:
        stats['redacted_values'] += truncated
    if redacted or truncated:
        return {'items_count': len(values), 'preview': projected, 'redacted_items_count': redacted + truncated}
    return projected


def _project_value(key: str, value: Any, stats: dict[str, int], depth: int) -> Any:
    lower = key.lower()
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int) or isinstance(value, float):
        return value
    if isinstance(value, str):
        return _project_string(lower, value, stats)
    if isinstance(value, list):
        return _project_list(lower, value, stats, depth)
    if isinstance(value, Mapping):
        return _project_mapping(value, stats, depth)
    stats['redacted_values'] += 1
    return _REDACTED


def project_payload(payload: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, int]]:
    stats = {'redacted_keys': 0, 'redacted_values': 0}
    projected: dict[str, Any] = {}
    keys = sorted(_safe_key(key) for key in payload.keys())
    for key in keys[:_MAX_MAPPING_KEYS]:
        if not key:
            stats['redacted_keys'] += 1
            continue
        lower = key.lower()
        if lower not in _TOP_LEVEL_KEYS:
            stats['redacted_keys'] += 1
            continue
        value = payload.get(key)
        if lower == 'messages':
            projected[key] = _project_messages(value, stats, 1)
        elif lower == 'lane_statuses':
            projected[key] = _project_lane_statuses(value, stats, 1)
        else:
            projected[key] = _project_value(lower, value, stats, 1)
    remaining = max(0, len(keys) - _MAX_MAPPING_KEYS)
    if remaining:
        stats['redacted_keys'] += remaining
        projected['truncated_keys_count'] = remaining
    return projected, stats
