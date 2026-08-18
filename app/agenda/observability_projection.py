from __future__ import annotations

from collections.abc import Iterable
from typing import Any, Mapping, Sequence

from agenda import pending_store


MAX_VALUES = 24

_SAFE_TOKEN_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-')
_SAFE_TIMESTAMP_CHARS = set('0123456789T:+-.Z')
_SENSITIVE_MARKERS = (
    'begin:vcalendar',
    'begin:vevent',
    'end:vevent',
    'summary:',
    'location:',
    'description:',
    'uid:',
    'etag:',
    'rrule:',
    'dtstart:',
    'dtend:',
    'http://',
    'https://',
    '/remote.php/',
    'authorization',
    'cookie',
    'bearer',
    'token',
    'app-password',
    'app_password',
    'raw_ics',
)


def project_message_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    if not _has_agenda_meta(meta):
        return {}
    return {
        'source': safe_token(meta.get('source'), max_chars=96),
        'reason_code': safe_token(meta.get('reason_code'), max_chars=96),
        'schema_version': safe_token(meta.get('agenda_schema_version'), max_chars=96),
        'product_method': safe_token(meta.get('agenda_product_method'), max_chars=96),
        'tool_names': safe_token_list(meta.get('agenda_tool_names')),
        'tool_count': safe_int(meta.get('agenda_tool_count')),
        'calendar_count': safe_int(meta.get('agenda_calendar_count')),
        'event_count': safe_int(meta.get('agenda_event_count')),
        'calendar_hashes': safe_token_list(meta.get('agenda_calendar_id_hashes')),
        'event_hashes': safe_token_list(meta.get('agenda_event_id_hashes')),
        'pending_action_id': safe_token(meta.get('agenda_pending_action_id'), max_chars=160),
        'pending_action_hash': safe_token(meta.get('agenda_pending_action_hash'), max_chars=64),
        'pending_action_status': safe_token(meta.get('agenda_pending_status'), max_chars=48),
        'pending_expires_at': safe_timestamp(meta.get('agenda_pending_expires_at')),
        'operation': safe_token(meta.get('agenda_operation'), max_chars=32),
        'confirmation_level': safe_token(meta.get('agenda_confirmation_level'), max_chars=32),
        'risk_flags': safe_token_list(meta.get('agenda_risk_flags')),
        'caldav_access': bool(meta.get('agenda_caldav_access')),
        'nextcloud_access': bool(meta.get('agenda_nextcloud_access')),
        'secret_access': bool(meta.get('agenda_secret_access')),
        'mutation_attempted': bool(meta.get('agenda_mutation_attempted')),
        'final_lock_authorized': bool(meta.get('agenda_final_lock_authorized')),
        'content_free_meta': bool(meta.get('content_free_meta')),
    }


def project_observability_payload(payload: Any) -> dict[str, Any]:
    data = mapping(payload)
    if not data:
        return {}
    pending_execution = mapping(data.get('pending_execution'))
    write_execution = mapping(data.get('write_execution') or pending_execution.get('write_execution'))
    read_execution = mapping(data.get('read_execution'))
    status, reason_code = _project_execution_status_and_reason(
        data,
        read_execution=read_execution,
        pending_execution=pending_execution,
        write_execution=write_execution,
    )
    return {
        'schema_version': safe_token(data.get('schema_version'), max_chars=96),
        'status': status,
        'reason_code': reason_code,
        'mode': safe_token(data.get('mode'), max_chars=32),
        'product_method': safe_token(data.get('product_method'), max_chars=96),
        'tool_names': safe_token_list(
            data.get('read_tool_names')
            or data.get('tool_names')
            or read_execution.get('tool_names')
            or pending_execution.get('tool_names')
        ),
        'tool_count': safe_int(data.get('read_tool_count') or data.get('tool_count')),
        'write_method_names': safe_token_list(
            data.get('write_method_names')
            or write_execution.get('method_names')
            or data.get('method_names')
        ),
        'operation': safe_token(
            data.get('pending_operation') or data.get('operation') or write_execution.get('operation'),
            max_chars=32,
        ),
        'pending_action_id': safe_token(data.get('pending_action_id'), max_chars=160),
        'pending_action_hash': safe_token(data.get('pending_action_hash'), max_chars=64),
        'pending_action_status': safe_token(
            data.get('pending_action_status') or pending_execution.get('pending_action_status'),
            max_chars=48,
        ),
        'pending_expires_at': safe_timestamp(data.get('pending_expires_at')),
        'confirmation_level': safe_token(data.get('confirmation_level'), max_chars=32),
        'risk_flags': safe_token_list(data.get('risk_flags')),
        'calendar_hashes': safe_token_list(data.get('calendar_hashes') or data.get('read_calendar_hashes')),
        'event_hashes': safe_token_list(data.get('event_hashes') or data.get('read_event_hashes')),
        'caldav_access': bool(data.get('caldav_access') or read_execution.get('caldav_access') or write_execution.get('caldav_access')),
        'nextcloud_access': bool(data.get('nextcloud_access') or read_execution.get('nextcloud_access') or write_execution.get('nextcloud_access')),
        'secret_access': bool(data.get('secret_access') or write_execution.get('secret_access')),
        'mutation_attempted': bool(data.get('mutation_attempted') or write_execution.get('mutation_attempted')),
        'final_response_override': bool(data.get('final_response_override')),
        'content_free': bool(data.get('content_free', False) or read_execution.get('content_free') or write_execution.get('content_free')),
    }


def _project_execution_status_and_reason(
    data: Mapping[str, Any],
    *,
    read_execution: Mapping[str, Any],
    pending_execution: Mapping[str, Any],
    write_execution: Mapping[str, Any],
) -> tuple[str, str]:
    for status, reason_code in (
        (
            safe_token(data.get('read_execution_status') or read_execution.get('status'), max_chars=96),
            safe_token(data.get('read_execution_reason_code') or read_execution.get('reason_code'), max_chars=96),
        ),
        (
            safe_token(data.get('pending_execution_status') or pending_execution.get('status'), max_chars=96),
            safe_token(data.get('pending_execution_reason_code') or pending_execution.get('reason_code'), max_chars=96),
        ),
        (
            safe_token(data.get('write_execution_status') or write_execution.get('status'), max_chars=96),
            safe_token(data.get('write_execution_reason_code') or write_execution.get('reason_code'), max_chars=96),
        ),
    ):
        if status in {'error', 'failed'}:
            return status, reason_code
    return (
        _first_token(data, 'status', 'read_execution_status', 'pending_execution_status', 'write_execution_status'),
        _first_token(data, 'reason_code', 'read_execution_reason_code', 'pending_execution_reason_code', 'write_execution_reason_code'),
    )


def _has_agenda_meta(meta: Mapping[str, Any]) -> bool:
    if pending_store.META_KEY in meta:
        return True
    source = str(meta.get('source') or '')
    if source.startswith('agenda_'):
        return True
    return any(str(key).startswith('agenda_') for key in meta.keys())


def _first_token(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = safe_token(data.get(key), max_chars=96)
        if value:
            return value
    return ''


def safe_token_list(value: Any) -> list[str]:
    return unique_values(sequence(value))


def unique_values(values: Any) -> list[str]:
    out: list[str] = []
    for value in _iter_values(values):
        token = safe_token(value, max_chars=160)
        if token and token not in out:
            out.append(token)
        if len(out) >= MAX_VALUES:
            break
    return out


def _iter_values(values: Any) -> Iterable[Any]:
    if isinstance(values, (str, bytes)) or isinstance(values, Mapping):
        return (values,)
    try:
        iter(values)
    except TypeError:
        return (values,)
    return values


def safe_token(value: Any, *, max_chars: int) -> str:
    text = str(value or '').strip()
    if not text or len(text) > max_chars:
        return ''
    lowered = text.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return ''
    if any(char not in _SAFE_TOKEN_CHARS for char in text):
        return ''
    return text


def safe_timestamp(value: Any) -> str:
    text = str(value or '').strip()
    if not text or len(text) > 64:
        return ''
    if any(marker in text.lower() for marker in _SENSITIVE_MARKERS):
        return ''
    if any(char not in _SAFE_TIMESTAMP_CHARS for char in text):
        return ''
    return text


def safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, (list, tuple)):
        return value
    return ()
