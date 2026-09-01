from __future__ import annotations

import re
from typing import Any, Mapping

from observability import admin_main_payload_manifest_projection


SCHEMA_VERSION = 'admin_log_event_projection_v1'
PROJECTION_MODE = 'content_free'

_MAX_MAPPING_KEYS = 32
_MAX_LIST_ITEMS = 8
_MAX_DEPTH = 4
_REDACTED = '[redacted]'

_SAFE_CODE_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,159}$')
_SAFE_MODEL_RE = re.compile(r'^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$')
_TOKEN_LIKE_SAFE_CODE_RE = re.compile(
    r'^(?:'
    r'sk[-_](?:live[-_]|or[-_])?[a-z0-9][a-z0-9_.-]{5,}'
    r'|ghp_[a-z0-9][a-z0-9_]{11,}'
    r'|hf_[a-z0-9][a-z0-9_]{11,}'
    r'|xoxb-[a-z0-9][a-z0-9_.-]{5,}'
    r')$',
    re.IGNORECASE,
)
_LEGACY_ADMIN_CORE_KEYS = {'timestamp', 'event', 'level'}
_LEGACY_ADMIN_SAFE_EVENT_RE = re.compile(r'^[A-Za-z0-9_.-]{1,160}$')
_LEGACY_ADMIN_SAFE_TIMESTAMP_RE = re.compile(r'^[0-9TZ:+.\-]{1,64}$')
_LEGACY_ADMIN_SAFE_LEVELS = {'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'}

_QUALIFIED_RAW_FLAGS = {
    'raw_event_payloads_included',
    'raw_log_included',
    'raw_content_included',
    'raw_prompt_included',
    'raw_provider_payload_included',
    'raw_message_included',
    'raw_lane_content_included',
    'raw_policy_text_included',
    'raw_secret_included',
    'raw_webdav_payload_included',
    'raw_error_message_included',
    'raw_error_message_stored',
    'raw_content_stored',
}

_SAFE_TEXT_KEYS = {
    'activity_runtime_authority',
    'admin_route',
    'apply_reason_code',
    'apply_status',
    'classification',
    'continuity_kind',
    'decision_source',
    'enunciation_effect',
    'enunciation_reason_code',
    'enunciation_source',
    'error_class',
    'error_code',
    'event_family',
    'epistemic_effect',
    'epistemic_reason_code',
    'epistemic_source',
    'final_output_regime',
    'final_status',
    'final_judgment_posture',
    'identity_schema_version',
    'injection_class',
    'judge_reason_code',
    'judge_status',
    'model',
    'mode',
    'operation_kind',
    'origin',
    'origin_stage',
    'persist_phase',
    'policy',
    'product_method',
    'projected_judgment_posture',
    'prompt_kind',
    'provider',
    'provider_caller',
    'provider_role',
    'priority_policy',
    'reason_code',
    'runtime_pipeline',
    'schema_version',
    'source_kind',
    'scope',
    'source',
    'status',
    'status_schema_version',
    'validation_decision',
    'validation_request_policy_version',
    'validation_transport',
    'validation_requested_model',
    'validation_attempt_decision_source',
    'validation_reasoning_effort_requested',
    'validation_reasoning_effort_effective',
    'validation_response_format_type',
    'validation_json_schema_name',
    'stimmung_request_policy_version',
    'stimmung_transport',
    'stimmung_requested_model',
    'stimmung_attempt_decision_source',
    'stimmung_response_format_type',
    'stimmung_json_schema_name',
    'verdict',
    'uncertainty_posture',
    'write_mode',
}

_SAFE_TEXT_SUFFIXES = (
    '_class',
    '_code',
    '_kind',
    '_mode',
    '_phase',
    '_schema_version',
    '_source',
    '_status',
    '_type',
    '_version',
)

_SAFE_TEXT_LIST_KEYS = {
    'active_signal_families',
    'advisory_recommendations_followed',
    'advisory_recommendations_overridden',
    'applied_hard_guards',
    'canonical_projection_included_families',
    'canonical_projection_omitted_families',
    'canonical_projection_no_data_families',
    'canonical_projection_redundant_families',
    'canonical_projection_optional_families',
    'canonical_projection_invalid_families',
    'canonical_projection_budget_exceeded_families',
    'degraded_fields',
    'pipeline_directives_final',
    'logical_roles',
    'provider_role_sequence',
    'read_tool_names',
    'reason_codes',
}

_SAFE_CONTAINER_KEYS = {
    'fallback_fail_open',
    'identity_prompt_injection',
    'llm_call_provider_metrics',
    'memory_prompt_injection',
    'node_state',
    'node_state_read',
    'node_state_write',
    'providers',
    'validation_request',
    'stimmung_request',
    'rag',
    'redaction',
    'source',
    'status_schema',
    'web',
}

_BLOCKED_EXACT_KEYS = {
    'authorization',
    'bearer',
    'body',
    'caldav_path',
    'canonical_inputs',
    'content',
    'context',
    'context_block',
    'cookie',
    'dav_path',
    'description',
    'etag',
    'exception',
    'headers',
    'href',
    'ics',
    'location',
    'message',
    'message_short',
    'messages',
    'password',
    'payload',
    'payload_json',
    'prompt',
    'provider_payload',
    'query',
    'raw',
    'raw_ics',
    'request_payload',
    'response_payload',
    'secret',
    'text',
    'title',
    'token',
    'uid',
    'uri',
    'url',
    'xml',
}

_BLOCKED_KEY_PARTS = (
    'authorization',
    'bearer',
    'cookie',
    'dav',
    'etag',
    'header',
    'password',
    'secret',
    'token',
    'webdav',
)
_SAFE_TOKEN_METRIC_KEYS = {
    'validation_max_tokens_effective',
    'stimmung_max_tokens_effective',
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


def _base_redaction() -> dict[str, Any]:
    return {
        'schema_version': SCHEMA_VERSION,
        'projection_mode': PROJECTION_MODE,
        'raw_event_payloads_included': False,
        'raw_content_included': False,
        'raw_prompt_included': False,
        'raw_provider_payload_included': False,
        'raw_webdav_payload_included': False,
        'raw_error_message_included': False,
        'source_payload_keys_count': 0,
        'projected_payload_keys_count': 0,
        'redacted_payload_keys_count': 0,
        'redacted_payload_values_count': 0,
    }


def _safe_key(key: Any) -> str:
    return str(key or '').strip()


def _is_qualified_raw_flag(key: str) -> bool:
    return key in _QUALIFIED_RAW_FLAGS


def _is_blocked_key(key: str) -> bool:
    lower = key.lower()
    if lower in _SAFE_TOKEN_METRIC_KEYS:
        return False
    if _is_qualified_raw_flag(lower):
        return False
    if lower in _BLOCKED_EXACT_KEYS:
        return True
    if lower.startswith('raw_'):
        return True
    if lower.endswith('_text'):
        return True
    for part in _BLOCKED_KEY_PARTS:
        if part in lower:
            return True
    if 'payload' in lower and lower not in {'payload_chars', 'payload_bytes'}:
        return True
    return False


def _is_safe_text_key(key: str) -> bool:
    lower = key.lower()
    if lower in _SAFE_TEXT_KEYS:
        return True
    return lower.endswith(_SAFE_TEXT_SUFFIXES)


def _looks_dangerous_text(value: str, *, allow_model_path: bool = False) -> bool:
    lower = value.lower()
    if _TOKEN_LIKE_SAFE_CODE_RE.fullmatch(value.strip()):
        return True
    if '://' in lower:
        return True
    if lower.startswith(('http:', 'https:', 'www.')):
        return True
    if any(part in lower for part in _DANGEROUS_VALUE_PARTS):
        return True
    if lower.startswith(('begin:', '<?xml')) or '</' in lower:
        return True
    if lower.startswith(('dav:', 'xml:')):
        return True
    if any(char in value for char in ('@', '\\', '?', '#', '&', '=', '<', '>', '\r', '\n', ':')):
        return True
    if '/' in value and not allow_model_path:
        return True
    return False


def _is_safe_model_value(value: str) -> bool:
    if _looks_dangerous_text(value, allow_model_path=True):
        return False
    return bool(_SAFE_CODE_RE.fullmatch(value) or _SAFE_MODEL_RE.fullmatch(value))


def _is_safe_text_value(key: str, value: Any) -> bool:
    text = str(value or '').strip()
    lower = str(key or '').strip().lower()
    if lower in {'model', 'validation_requested_model', 'stimmung_requested_model'}:
        return _is_safe_model_value(text)
    if lower in {'provider', 'provider_title'}:
        return bool(text) and len(text) <= 120 and not _looks_dangerous_text(text)
    if _looks_dangerous_text(text):
        return False
    return bool(_SAFE_CODE_RE.fullmatch(text))


def _project_string(key: str, value: Any, stats: dict[str, int]) -> str:
    if _is_safe_text_key(key) and _is_safe_text_value(key, value):
        return str(value).strip()
    stats['redacted_values'] += 1
    return _REDACTED


def _project_list(key: str, values: list[Any], stats: dict[str, int], depth: int) -> Any:
    if depth >= _MAX_DEPTH:
        stats['redacted_values'] += len(values)
        return {
            'items_count': len(values),
            'redacted_items_count': len(values),
        }

    projected: list[Any] = []
    redacted_items = 0
    for value in values[:_MAX_LIST_ITEMS]:
        before = stats['redacted_values']
        if isinstance(value, str) and key in _SAFE_TEXT_LIST_KEYS:
            if _is_safe_text_value(key, value):
                projected.append(value.strip())
            else:
                stats['redacted_values'] += 1
                projected.append(_REDACTED)
        elif isinstance(value, str):
            projected.append(_project_string(key, value, stats))
        else:
            projected.append(_project_value(key, value, stats, depth + 1))
        if stats['redacted_values'] > before:
            redacted_items += 1

    truncated_items = max(0, len(values) - _MAX_LIST_ITEMS)
    if truncated_items:
        stats['redacted_values'] += truncated_items
    if redacted_items or truncated_items:
        return {
            'items_count': len(values),
            'preview': projected,
            'redacted_items_count': redacted_items + truncated_items,
        }
    return projected


def _project_mapping(payload: Mapping[str, Any], stats: dict[str, int], depth: int) -> dict[str, Any]:
    if depth >= _MAX_DEPTH:
        redacted = len(payload)
        stats['redacted_keys'] += redacted
        return {
            'keys_count': redacted,
            'redacted_keys_count': redacted,
        }

    projected: dict[str, Any] = {}
    keys = sorted(_safe_key(key) for key in payload.keys())
    for key in keys[:_MAX_MAPPING_KEYS]:
        if not key:
            stats['redacted_keys'] += 1
            continue
        lower = key.lower()
        if _is_qualified_raw_flag(lower):
            projected[lower] = False
            continue
        if _is_blocked_key(key):
            stats['redacted_keys'] += 1
            continue
        value = payload.get(key)
        if (
            isinstance(value, Mapping)
            and lower not in _SAFE_CONTAINER_KEYS
            and not lower.endswith(('_counts', '_by_stage', '_metrics'))
        ):
            projected[key] = {
                'keys_count': len(value),
                'content_minimized': True,
            }
            continue
        projected[key] = _project_value(key, value, stats, depth + 1)

    remaining = max(0, len(keys) - _MAX_MAPPING_KEYS)
    if remaining:
        stats['redacted_keys'] += remaining
        projected['truncated_keys_count'] = remaining
    return projected


def _project_value(key: str, value: Any, stats: dict[str, int], depth: int) -> Any:
    if value is None or isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return value
    if isinstance(value, str):
        return _project_string(key, value, stats)
    if isinstance(value, list):
        return _project_list(key, value, stats, depth)
    if isinstance(value, Mapping):
        return _project_mapping(value, stats, depth)
    stats['redacted_values'] += 1
    return _REDACTED


def project_payload(payload: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    source = payload if isinstance(payload, Mapping) else {}
    if admin_main_payload_manifest_projection.is_main_payload_manifest(source):
        projected, stats = admin_main_payload_manifest_projection.project_payload(source)
    else:
        stats = {'redacted_keys': 0, 'redacted_values': 0}
        projected = _project_mapping(source, stats, 0)
    redaction = _base_redaction()
    redaction.update(
        {
            'source_payload_keys_count': len(source),
            'projected_payload_keys_count': len(projected),
            'redacted_payload_keys_count': stats['redacted_keys'],
            'redacted_payload_values_count': stats['redacted_values'],
        }
    )
    return projected, redaction


def project_event_item(item: Mapping[str, Any]) -> dict[str, Any]:
    existing_projection = item.get('payload_projection')
    if isinstance(existing_projection, Mapping) and existing_projection.get('schema_version') == SCHEMA_VERSION:
        return dict(item)

    projected = dict(item)
    payload, redaction = project_payload(item.get('payload'))
    projected['payload'] = payload
    existing_redaction = item.get('redaction') if isinstance(item.get('redaction'), Mapping) else {}
    projected['redaction'] = {
        **dict(existing_redaction),
        **redaction,
    }
    projected['payload_projection'] = {
        'schema_version': SCHEMA_VERSION,
        'mode': PROJECTION_MODE,
        'content_free': True,
    }
    return projected


def project_event_items(items: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    source_items = items if isinstance(items, list) else []
    projected_items: list[dict[str, Any]] = []
    aggregate = _base_redaction()
    for item in source_items:
        if not isinstance(item, Mapping):
            continue
        projected = project_event_item(item)
        projected_items.append(projected)
        redaction = projected.get('redaction') if isinstance(projected.get('redaction'), Mapping) else {}
        aggregate['source_payload_keys_count'] += int(redaction.get('source_payload_keys_count') or 0)
        aggregate['projected_payload_keys_count'] += int(redaction.get('projected_payload_keys_count') or 0)
        aggregate['redacted_payload_keys_count'] += int(redaction.get('redacted_payload_keys_count') or 0)
        aggregate['redacted_payload_values_count'] += int(redaction.get('redacted_payload_values_count') or 0)
    aggregate['items_count'] = len(projected_items)
    return projected_items, aggregate


def _content_free_legacy_admin_event(value: Any) -> str:
    text = str(value or '').strip()
    if _LEGACY_ADMIN_SAFE_EVENT_RE.fullmatch(text):
        return text
    return 'redacted_event'


def _content_free_legacy_admin_level(value: Any) -> str:
    text = str(value or '').strip().upper()
    if text == 'WARN':
        return 'WARNING'
    if text in _LEGACY_ADMIN_SAFE_LEVELS:
        return text
    return 'INFO'


def _content_free_legacy_admin_timestamp(value: Any) -> str:
    text = str(value or '').strip()
    if _LEGACY_ADMIN_SAFE_TIMESTAMP_RE.fullmatch(text):
        return text
    return ''


def project_legacy_admin_log_entries(entries: Any) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    source_entries = entries if isinstance(entries, list) else []
    for entry in source_entries:
        if not isinstance(entry, Mapping):
            continue
        payload = {key: value for key, value in entry.items() if str(key) not in _LEGACY_ADMIN_CORE_KEYS}
        normalized.append(
            {
                'timestamp': _content_free_legacy_admin_timestamp(entry.get('timestamp')),
                'event': _content_free_legacy_admin_event(entry.get('event')),
                'level': _content_free_legacy_admin_level(entry.get('level')),
                'payload': payload,
                'legacy_admin_log': True,
            }
        )
    return project_event_items(normalized)


def project_event_listing(listing: Mapping[str, Any]) -> dict[str, Any]:
    projected = dict(listing)
    items, redaction = project_event_items(projected.get('items'))
    projected['items'] = items
    projected['redaction'] = redaction
    return projected
