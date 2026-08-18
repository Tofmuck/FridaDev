from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence

from agenda import observability_projection, pending_store


READ_MODEL_SCHEMA_VERSION = 'frida_agenda_observability_read_model_v1'
ADMIN_ROUTE = '/api/admin/agenda/observability'
MAX_RECENT_EVENTS = 100
MAX_VALUES = observability_projection.MAX_VALUES

# Compatibility exports for the existing Agenda golden boundary.
project_message_meta = observability_projection.project_message_meta
project_observability_payload = observability_projection.project_observability_payload
_mapping = observability_projection.mapping
_safe_timestamp = observability_projection.safe_timestamp
_safe_token = observability_projection.safe_token
_safe_token_list = observability_projection.safe_token_list
_sequence = observability_projection.sequence
_unique_values = observability_projection.unique_values


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
        project_observability_payload(
            _mapping(event).get('payload') or _mapping(event).get('payload_json')
        )
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
        summary
        for summary in (
            project_message_meta(_mapping(message.get('meta')))
            for message in messages
        )
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
