from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from typing import Any, Mapping, Sequence

from agenda import pending_store


READ_MODEL_SCHEMA_VERSION = 'frida_agenda_observability_read_model_v1'
ADMIN_ROUTE = '/api/admin/agenda/observability'
MAX_RECENT_EVENTS = 100
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


def build_admin_observability(
    *,
    log_events: Sequence[Mapping[str, Any]] = (),
    conversation: Mapping[str, Any] | None = None,
    log_read_error: str = '',
) -> dict[str, Any]:
    """Build the Agenda admin read-model without copying calendar content."""
    event_summary = summarize_log_events(log_events)
    conversation_summary = summarize_conversation(conversation or {})
    return {
        'schema_version': READ_MODEL_SCHEMA_VERSION,
        'module': 'agenda',
        'admin_route': ADMIN_ROUTE,
        'source': 'chat_log_events_stage_agenda',
        'status': 'available' if not log_read_error else 'degraded',
        'log_read_error_class': _safe_token(log_read_error, max_chars=96),
        'event_summary': event_summary,
        'conversation_summary': conversation_summary,
        'coverage': {
            'read_observable': True,
            'proposal_observable': True,
            'confirmation_observable': True,
            'write_observable': True,
            'pending_store_observable': True,
            'live_smoke_jsonl_observable': False,
        },
        'boundaries': {
            'calendar_content_exposed': False,
            'technical_references_exposed': False,
            'credentials_exposed': False,
            'raw_payloads_exposed': False,
            'pending_drafts_exposed': False,
        },
        'content_free': True,
        'redacted': True,
    }


def summarize_log_events(log_events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    projected_payloads = [
        project_observability_payload(_mapping(event).get('payload') or _mapping(event).get('payload_json'))
        for event in log_events
    ]
    status_counts: Counter[str] = Counter()
    for event in log_events:
        status = _safe_token(_mapping(event).get('status'), max_chars=32) or 'unknown'
        status_counts[status] += 1

    return {
        'event_count': len(log_events),
        'status_counts': dict(sorted(status_counts.items())),
        'schema_versions': _unique_values(payload.get('schema_version') for payload in projected_payloads),
        'statuses': _unique_values(payload.get('status') for payload in projected_payloads),
        'reason_codes': _unique_values(payload.get('reason_code') for payload in projected_payloads),
        'product_methods': _unique_values(payload.get('product_method') for payload in projected_payloads),
        'tool_names': _unique_values(_flatten(payload.get('tool_names') for payload in projected_payloads)),
        'write_method_names': _unique_values(_flatten(payload.get('write_method_names') for payload in projected_payloads)),
        'operation_counts': _counter_from(projected_payloads, 'operation'),
        'pending_status_counts': _counter_from(projected_payloads, 'pending_action_status'),
        'confirmation_levels': _unique_values(payload.get('confirmation_level') for payload in projected_payloads),
        'risk_flags': _unique_values(_flatten(payload.get('risk_flags') for payload in projected_payloads)),
        'caldav_access_count': _bool_count(projected_payloads, 'caldav_access'),
        'nextcloud_access_count': _bool_count(projected_payloads, 'nextcloud_access'),
        'secret_access_count': _bool_count(projected_payloads, 'secret_access'),
        'mutation_attempted_count': _bool_count(projected_payloads, 'mutation_attempted'),
        'final_response_override_count': _bool_count(projected_payloads, 'final_response_override'),
        'content_free_event_count': _bool_count(projected_payloads, 'content_free'),
        'latest_ts': _latest_timestamp(log_events),
        'content_free': True,
        'redacted': True,
    }


def summarize_conversation(conversation: Mapping[str, Any]) -> dict[str, Any]:
    messages = [_mapping(message) for message in _sequence(conversation.get('messages'))]
    meta_summaries = [
        summary for summary in (project_message_meta(_mapping(message.get('meta'))) for message in messages)
        if summary
    ]
    pending_state = pending_store.read_state_from_conversation(conversation)
    pending_actions = [
        _project_pending_action(action)
        for action in pending_state.actions[: pending_store.MAX_ACTIONS]
    ]
    return {
        'message_count': len(messages),
        'agenda_meta_count': len(meta_summaries),
        'sources': _unique_values(summary.get('source') for summary in meta_summaries),
        'reason_codes': _unique_values(summary.get('reason_code') for summary in meta_summaries),
        'product_methods': _unique_values(summary.get('product_method') for summary in meta_summaries),
        'tool_names': _unique_values(_flatten(summary.get('tool_names') for summary in meta_summaries)),
        'operation_counts': _counter_from(meta_summaries, 'operation'),
        'pending_status_counts': _counter_from(pending_actions, 'status'),
        'confirmation_levels': _unique_values(action.get('confirmation_level') for action in pending_actions),
        'risk_flags': _unique_values(_flatten(action.get('risk_flags') for action in pending_actions)),
        'pending_action_count': len(pending_actions),
        'pending_actions': pending_actions,
        'caldav_access_count': _bool_count(meta_summaries, 'caldav_access'),
        'nextcloud_access_count': _bool_count(meta_summaries, 'nextcloud_access'),
        'secret_access_count': _bool_count(meta_summaries, 'secret_access'),
        'mutation_attempted_count': _bool_count(meta_summaries, 'mutation_attempted'),
        'final_response_override_count': _bool_count(meta_summaries, 'final_lock_authorized'),
        'content_free': True,
        'redacted': True,
    }


def project_message_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
    if not _has_agenda_meta(meta):
        return {}
    return {
        'source': _safe_token(meta.get('source'), max_chars=96),
        'reason_code': _safe_token(meta.get('reason_code'), max_chars=96),
        'schema_version': _safe_token(meta.get('agenda_schema_version'), max_chars=96),
        'product_method': _safe_token(meta.get('agenda_product_method'), max_chars=96),
        'tool_names': _safe_token_list(meta.get('agenda_tool_names')),
        'tool_count': _safe_int(meta.get('agenda_tool_count')),
        'calendar_count': _safe_int(meta.get('agenda_calendar_count')),
        'event_count': _safe_int(meta.get('agenda_event_count')),
        'calendar_hashes': _safe_token_list(meta.get('agenda_calendar_id_hashes')),
        'event_hashes': _safe_token_list(meta.get('agenda_event_id_hashes')),
        'pending_action_id': _safe_token(meta.get('agenda_pending_action_id'), max_chars=160),
        'pending_action_hash': _safe_token(meta.get('agenda_pending_action_hash'), max_chars=64),
        'pending_action_status': _safe_token(meta.get('agenda_pending_status'), max_chars=48),
        'pending_expires_at': _safe_timestamp(meta.get('agenda_pending_expires_at')),
        'operation': _safe_token(meta.get('agenda_operation'), max_chars=32),
        'confirmation_level': _safe_token(meta.get('agenda_confirmation_level'), max_chars=32),
        'risk_flags': _safe_token_list(meta.get('agenda_risk_flags')),
        'caldav_access': bool(meta.get('agenda_caldav_access')),
        'nextcloud_access': bool(meta.get('agenda_nextcloud_access')),
        'secret_access': bool(meta.get('agenda_secret_access')),
        'mutation_attempted': bool(meta.get('agenda_mutation_attempted')),
        'final_lock_authorized': bool(meta.get('agenda_final_lock_authorized')),
        'content_free_meta': bool(meta.get('content_free_meta')),
    }


def project_observability_payload(payload: Any) -> dict[str, Any]:
    data = _mapping(payload)
    if not data:
        return {}
    pending_execution = _mapping(data.get('pending_execution'))
    write_execution = _mapping(data.get('write_execution') or pending_execution.get('write_execution'))
    read_execution = _mapping(data.get('read_execution'))
    return {
        'schema_version': _safe_token(data.get('schema_version'), max_chars=96),
        'status': _first_token(data, 'status', 'read_execution_status', 'pending_execution_status', 'write_execution_status'),
        'reason_code': _first_token(data, 'reason_code', 'read_execution_reason_code', 'pending_execution_reason_code', 'write_execution_reason_code'),
        'mode': _safe_token(data.get('mode'), max_chars=32),
        'product_method': _safe_token(data.get('product_method'), max_chars=96),
        'tool_names': _safe_token_list(
            data.get('read_tool_names')
            or data.get('tool_names')
            or read_execution.get('tool_names')
            or pending_execution.get('tool_names')
        ),
        'tool_count': _safe_int(data.get('read_tool_count') or data.get('tool_count')),
        'write_method_names': _safe_token_list(
            data.get('write_method_names')
            or write_execution.get('method_names')
            or data.get('method_names')
        ),
        'operation': _safe_token(
            data.get('pending_operation') or data.get('operation') or write_execution.get('operation'),
            max_chars=32,
        ),
        'pending_action_id': _safe_token(data.get('pending_action_id'), max_chars=160),
        'pending_action_hash': _safe_token(data.get('pending_action_hash'), max_chars=64),
        'pending_action_status': _safe_token(
            data.get('pending_action_status') or pending_execution.get('pending_action_status'),
            max_chars=48,
        ),
        'pending_expires_at': _safe_timestamp(data.get('pending_expires_at')),
        'confirmation_level': _safe_token(data.get('confirmation_level'), max_chars=32),
        'risk_flags': _safe_token_list(data.get('risk_flags')),
        'calendar_hashes': _safe_token_list(data.get('calendar_hashes') or data.get('read_calendar_hashes')),
        'event_hashes': _safe_token_list(data.get('event_hashes') or data.get('read_event_hashes')),
        'caldav_access': bool(data.get('caldav_access') or read_execution.get('caldav_access') or write_execution.get('caldav_access')),
        'nextcloud_access': bool(data.get('nextcloud_access') or read_execution.get('nextcloud_access') or write_execution.get('nextcloud_access')),
        'secret_access': bool(data.get('secret_access') or write_execution.get('secret_access')),
        'mutation_attempted': bool(data.get('mutation_attempted') or write_execution.get('mutation_attempted')),
        'final_response_override': bool(data.get('final_response_override')),
        'content_free': bool(data.get('content_free', False) or read_execution.get('content_free') or write_execution.get('content_free')),
    }


def _project_pending_action(action: pending_store.AgendaPendingAction) -> dict[str, Any]:
    content_free = action.to_content_free_dict()
    return {
        'pending_action_id': _safe_token(content_free.get('pending_action_id'), max_chars=160),
        'action_hash': _safe_token(content_free.get('action_hash'), max_chars=64),
        'operation': _safe_token(content_free.get('operation'), max_chars=32),
        'confirmation_level': _safe_token(content_free.get('confirmation_level'), max_chars=32),
        'risk_flags': _safe_token_list(content_free.get('risk_flags')),
        'created_at': _safe_timestamp(content_free.get('created_at')),
        'expires_at': _safe_timestamp(content_free.get('expires_at')),
        'status': _safe_token(content_free.get('status'), max_chars=48),
        'draft_private': bool(content_free.get('draft_private')),
        'content_free': True,
    }


def _has_agenda_meta(meta: Mapping[str, Any]) -> bool:
    if pending_store.META_KEY in meta:
        return True
    source = str(meta.get('source') or '')
    if source.startswith('agenda_'):
        return True
    return any(str(key).startswith('agenda_') for key in meta.keys())


def _first_token(data: Mapping[str, Any], *keys: str) -> str:
    for key in keys:
        value = _safe_token(data.get(key), max_chars=96)
        if value:
            return value
    return ''


def _safe_token_list(value: Any) -> list[str]:
    return _unique_values(_sequence(value))


def _unique_values(values: Any) -> list[str]:
    out: list[str] = []
    for value in _iter_values(values):
        token = _safe_token(value, max_chars=160)
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


def _flatten(values: Any) -> list[Any]:
    out: list[Any] = []
    for value in values:
        if isinstance(value, (list, tuple, set)):
            out.extend(value)
        elif value:
            out.append(value)
    return out


def _counter_from(items: Sequence[Mapping[str, Any]], key: str) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        token = _safe_token(item.get(key), max_chars=96)
        if token:
            counter[token] += 1
    return dict(sorted(counter.items()))


def _bool_count(items: Sequence[Mapping[str, Any]], key: str) -> int:
    return sum(1 for item in items if bool(item.get(key)))


def _latest_timestamp(items: Sequence[Mapping[str, Any]]) -> str:
    timestamps = [_safe_timestamp(_mapping(item).get('ts')) for item in items]
    timestamps = [value for value in timestamps if value]
    return max(timestamps) if timestamps else ''


def _safe_token(value: Any, *, max_chars: int) -> str:
    text = str(value or '').strip()
    if not text or len(text) > max_chars:
        return ''
    lowered = text.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return ''
    if any(char not in _SAFE_TOKEN_CHARS for char in text):
        return ''
    return text


def _safe_timestamp(value: Any) -> str:
    text = str(value or '').strip()
    if not text or len(text) > 64:
        return ''
    if any(marker in text.lower() for marker in _SENSITIVE_MARKERS):
        return ''
    if any(char not in _SAFE_TIMESTAMP_CHARS for char in text):
        return ''
    return text


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, (list, tuple)):
        return value
    return ()
