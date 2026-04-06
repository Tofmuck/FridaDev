from __future__ import annotations

from typing import Any, Mapping, Tuple


READ_MODEL_VERSION = 'v1'
ACTIVE_IDENTITY_SOURCE = 'identity_mutables'
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
DEFAULT_LAYER_LIMIT = 20
MAX_LAYER_LIMIT = 100
GOVERNANCE_ROUTE = '/api/admin/identity/governance'


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
                'used_identity_ids': used_identity_ids_list,
                'used_identity_ids_count': len(used_identity_ids_list),
                'legacy_drives_active_injection': False,
                'read_surface_stage': 'lot_5_governance_visible',
            },
            'subjects': subjects,
        },
        200,
    )
