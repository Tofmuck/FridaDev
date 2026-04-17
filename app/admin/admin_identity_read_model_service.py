from __future__ import annotations

from typing import Any, Mapping, Tuple

import config
from memory import memory_identity_periodic_agent
from memory import memory_identity_periodic_scoring


READ_MODEL_VERSION = 'v2'
ACTIVE_IDENTITY_SOURCE = 'identity_mutables'
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
DEFAULT_LAYER_LIMIT = 20
MAX_LAYER_LIMIT = 100
GOVERNANCE_ROUTE = '/api/admin/identity/governance'
RUNTIME_REPRESENTATIONS_ROUTE = '/api/admin/identity/runtime-representations'
READ_SURFACE_STAGE = 'lot_b5_identity_operator_truth'
STAGING_STORAGE_KIND = 'identity_mutable_staging'


def _optional_text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _normalize_limit(raw_value: Any) -> int:
    try:
        limit = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_LAYER_LIMIT
    return max(1, min(limit, MAX_LAYER_LIMIT))


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _compact_promotions(values: Any) -> list[dict[str, Any]]:
    items = values if isinstance(values, list) else []
    compact: list[dict[str, Any]] = []
    for item in items:
        payload = _mapping(item)
        summary: dict[str, Any] = {}
        for key in (
            'subject',
            'operation_kind',
            'promotion_reason_code',
            'threshold_verdict',
        ):
            text = _optional_text(payload.get(key))
            if text:
                summary[key] = text
        try:
            strength = float(payload.get('strength'))
        except (TypeError, ValueError):
            strength = None
        if strength is not None:
            summary['strength'] = round(strength, 4)
        if summary:
            compact.append(summary)
    return compact


def _latest_periodic_agent_event(
    *,
    log_store_module: Any,
    conversation_id: str | None = None,
) -> Mapping[str, Any]:
    read_chat_log_events = getattr(log_store_module, 'read_chat_log_events', None)
    if not callable(read_chat_log_events):
        return {}
    try:
        payload = read_chat_log_events(
            limit=1,
            conversation_id=conversation_id,
            stage='identity_periodic_agent',
        )
    except Exception:
        return {}
    items = payload.get('items') if isinstance(payload, Mapping) else []
    if not isinstance(items, list) or not items:
        return {}
    return _mapping(items[0])


def _build_latest_agent_activity(
    *,
    log_store_module: Any,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    event = _latest_periodic_agent_event(
        log_store_module=log_store_module,
        conversation_id=conversation_id,
    )
    payload = _mapping(event.get('payload'))
    return {
        'present': bool(event),
        'conversation_id': _optional_text(event.get('conversation_id')),
        'turn_id': _optional_text(event.get('turn_id')),
        'ts': _optional_text(event.get('ts')),
        'status': _optional_text(event.get('status')),
        'reason_code': _optional_text(payload.get('reason_code')),
        'writes_applied': bool(payload.get('writes_applied')),
        'promotion_count': int(payload.get('promotion_count') or 0),
        'promotions': _compact_promotions(payload.get('promotions')),
        'rejection_reasons': dict(payload.get('rejection_reasons') or {}),
    }


def build_identity_runtime_regime() -> dict[str, Any]:
    return {
        'active_canon_layers': ['static', 'mutable'],
        'staging_storage_kind': STAGING_STORAGE_KIND,
        'staging_target_pairs': int(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
        'staging_not_injected': True,
        'mutable_budget': {
            'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
            'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
        },
        'scoring_thresholds': {
            'reject_below': float(memory_identity_periodic_scoring.REJECT_THRESHOLD),
            'accept_from': float(memory_identity_periodic_scoring.ACCEPT_THRESHOLD),
        },
        'promotion_to_static_enabled': True,
        'auto_canonization_suspends_on_double_saturation': True,
    }


def build_identity_staging_block(
    *,
    memory_store_module: Any,
    log_store_module: Any,
) -> dict[str, Any]:
    get_latest_state = getattr(memory_store_module, 'get_latest_identity_staging_state', None)
    staging_state = _mapping(get_latest_state()) if callable(get_latest_state) else {}
    conversation_id = _optional_text(staging_state.get('conversation_id'))
    buffer_target_pairs = int(
        staging_state.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS
    )
    latest_activity = (
        _build_latest_agent_activity(
            log_store_module=log_store_module,
            conversation_id=conversation_id,
        )
        if conversation_id
        else {
            'present': False,
            'conversation_id': None,
            'turn_id': None,
            'ts': None,
            'status': None,
            'reason_code': None,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'rejection_reasons': {},
        }
    )
    return {
        'storage_kind': STAGING_STORAGE_KIND,
        'scope_kind': 'conversation_scoped_latest',
        'present': bool(staging_state),
        'actively_injected': False,
        'conversation_id': conversation_id,
        'buffer_pairs_count': int(staging_state.get('buffer_pairs_count') or 0),
        'buffer_target_pairs': buffer_target_pairs,
        'buffer_frozen': bool(staging_state.get('buffer_frozen')),
        'last_agent_status': _optional_text(staging_state.get('last_agent_status')),
        'last_agent_reason': _optional_text(staging_state.get('last_agent_reason')),
        'last_agent_run_ts': _optional_text(staging_state.get('last_agent_run_ts')),
        'updated_ts': _optional_text(staging_state.get('updated_ts')),
        'auto_canonization_suspended': bool(staging_state.get('auto_canonization_suspended')),
        'latest_agent_activity': latest_activity,
    }


def _build_static_layer(
    active_side: Mapping[str, Any],
    *,
    static_snapshot: Mapping[str, Any],
) -> dict[str, Any]:
    payload = _mapping(active_side.get('static'))
    content = str(payload.get('content') or '')
    raw_content = str(static_snapshot.get('raw_content') or '')
    source = _optional_text(payload.get('source'))
    runtime_present = bool(content)
    return {
        'storage_kind': 'resource_path',
        'source_kind': str(static_snapshot.get('source_kind') or 'resource_path_content'),
        'stored': bool(raw_content),
        'loaded_for_runtime': runtime_present,
        'actively_injected': runtime_present,
        'content': content,
        'source': source,
        'resource_field': _optional_text(static_snapshot.get('resource_field')),
        'configured_path': _optional_text(static_snapshot.get('configured_path')),
        'resolution_kind': _optional_text(static_snapshot.get('resolution_kind')),
        'resolved_path': _optional_text(static_snapshot.get('resolved_path_str') or static_snapshot.get('resolved_path')),
        'editable_via': _optional_text(static_snapshot.get('editable_via')),
    }


def _build_mutable_layer(active_side: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(active_side.get('mutable'))
    content = str(payload.get('content') or '')
    present = bool(content)
    return {
        'storage_kind': ACTIVE_IDENTITY_SOURCE,
        'stored': present,
        'loaded_for_runtime': present,
        'actively_injected': present,
        'content': content,
        'source_trace_id': _optional_text(payload.get('source_trace_id')),
        'updated_by': _optional_text(payload.get('updated_by')),
        'update_reason': _optional_text(payload.get('update_reason')),
        'updated_ts': _optional_text(payload.get('updated_ts')),
    }


def _build_collection_layer(*, storage_kind: str, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    items = list(snapshot.get('items') or [])
    total_count = int(snapshot.get('total_count') or len(items))
    return {
        'storage_kind': storage_kind,
        'stored': total_count > 0,
        'loaded_for_runtime': False,
        'actively_injected': False,
        'total_count': total_count,
        'limit': int(snapshot.get('limit') or len(items) or DEFAULT_LAYER_LIMIT),
        'items': items,
    }


def _build_subject_block(
    *,
    subject: str,
    active_side: Mapping[str, Any],
    memory_store_module: Any,
    static_identity_content_module: Any,
    limit: int,
) -> dict[str, Any]:
    static_snapshot = static_identity_content_module.read_static_identity_snapshot(subject)
    return {
        'static': _build_static_layer(active_side, static_snapshot=static_snapshot.__dict__),
        'mutable': _build_mutable_layer(active_side),
        'legacy_fragments': _build_collection_layer(
            storage_kind='identities',
            snapshot=memory_store_module.list_identity_fragments(subject, limit=limit),
        ),
        'evidence': _build_collection_layer(
            storage_kind='identity_evidence',
            snapshot=memory_store_module.list_identity_evidence(subject, limit=limit),
        ),
        'conflicts': _build_collection_layer(
            storage_kind='identity_conflicts',
            snapshot=memory_store_module.list_identity_conflicts(subject, limit=limit),
        ),
    }


def identity_read_model_response(
    args: Mapping[str, Any],
    *,
    memory_store_module: Any,
    identity_module: Any,
    static_identity_content_module: Any,
    log_store_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    limit = _normalize_limit(args.get('limit', DEFAULT_LAYER_LIMIT))

    try:
        active_payload = identity_module.build_identity_input()
        _block, used_identity_ids = identity_module.build_identity_block()
    except Exception as exc:
        return (
            {
                'ok': False,
                'error': 'lecture identity unifiee indisponible',
                'error_code': 'identity_read_model_unavailable',
                'error_class': exc.__class__.__name__,
            },
            500,
        )

    try:
        active_payload_map = _mapping(active_payload)
        used_identity_ids_list = list(used_identity_ids or [])
        identity_staging = build_identity_staging_block(
            memory_store_module=memory_store_module,
            log_store_module=log_store_module,
        )
        subjects = {
            'llm': _build_subject_block(
                subject='llm',
                active_side=_mapping(active_payload_map.get('frida')),
                memory_store_module=memory_store_module,
                static_identity_content_module=static_identity_content_module,
                limit=limit,
            ),
            'user': _build_subject_block(
                subject='user',
                active_side=_mapping(active_payload_map.get('user')),
                memory_store_module=memory_store_module,
                static_identity_content_module=static_identity_content_module,
                limit=limit,
            ),
        }
    except Exception as exc:
        return (
            {
                'ok': False,
                'error': 'lecture identity unifiee indisponible',
                'error_code': 'identity_read_model_unavailable',
                'error_class': exc.__class__.__name__,
            },
            500,
        )

    return (
        {
            'ok': True,
            'read_model_version': READ_MODEL_VERSION,
            'active_runtime': {
                'active_identity_source': ACTIVE_IDENTITY_SOURCE,
                'active_prompt_contract': ACTIVE_PROMPT_CONTRACT,
                'identity_input_schema_version': str(active_payload_map.get('schema_version') or ''),
                'active_static_source': 'resource_path_content',
                'static_editable_via': '/api/admin/identity/static',
                'mutable_editable_via': '/api/admin/identity/mutable',
                'governance_read_via': GOVERNANCE_ROUTE,
                'governance_editable_via': GOVERNANCE_ROUTE,
                'runtime_representations_read_via': RUNTIME_REPRESENTATIONS_ROUTE,
                'used_identity_ids': used_identity_ids_list,
                'used_identity_ids_count': len(used_identity_ids_list),
                'legacy_drives_active_injection': False,
                'read_surface_stage': READ_SURFACE_STAGE,
                'identity_runtime_regime': build_identity_runtime_regime(),
            },
            'identity_staging': identity_staging,
            'subjects': subjects,
        },
        200,
    )
