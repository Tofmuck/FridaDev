from __future__ import annotations

from typing import Any, Mapping


ACTIVE_IDENTITY_SOURCE = 'identity_mutables'
DEFAULT_LAYER_LIMIT = 20
LEGACY_IDENTITY_PIPELINE_STATUS = 'legacy_inactive_historical'
LEGACY_LAYER_CLASSIFICATION = 'legacy_diagnostic_only'
MUTABLE_AUDIT_STORAGE_KIND = 'identity_mutable_audit'
LEGACY_PROJECTION_VERSION = 'identity_legacy_content_minimized_v2'
LEGACY_RAW_TEXT_KEYS = {
    'content',
    'content_norm',
    'last_reason',
    'override_reason',
    'reason',
    'content_a',
    'content_b',
}


def _optional_text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _text_stats(text: Any, *, prefix: str) -> dict[str, Any]:
    raw = str(text or '')
    return {
        f'{prefix}_present': bool(raw),
        f'{prefix}_chars': len(raw),
    }


def _free_text_reason_marker(text: Any, *, marker: str) -> str:
    return marker if _optional_text(text) else ''


def _without_legacy_raw_text(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {str(key): value for key, value in payload.items() if str(key) not in LEGACY_RAW_TEXT_KEYS}


def _ensure_text_projection(
    target: dict[str, Any],
    source: Mapping[str, Any],
    *,
    raw_key: str,
    prefix: str,
) -> None:
    if raw_key in source:
        target.update(_text_stats(source.get(raw_key), prefix=prefix))
        return
    target.setdefault(f'{prefix}_present', False)
    target.setdefault(f'{prefix}_chars', 0)


def _ensure_reason_projection(
    target: dict[str, Any],
    source: Mapping[str, Any],
    *,
    raw_key: str,
    code_key: str,
    stats_prefix: str,
    marker: str = 'text_reason_present',
) -> None:
    if raw_key in source:
        target.setdefault(code_key, _free_text_reason_marker(source.get(raw_key), marker=marker))
        target.update(_text_stats(source.get(raw_key), prefix=stats_prefix))
        return
    target.setdefault(code_key, '')
    target.setdefault(f'{stats_prefix}_present', False)
    target.setdefault(f'{stats_prefix}_chars', 0)


def _compact_legacy_fragment_item(item: Any) -> dict[str, Any]:
    payload = _mapping(item)
    compact = _without_legacy_raw_text(payload)
    _ensure_text_projection(compact, payload, raw_key='content', prefix='content')
    _ensure_text_projection(compact, payload, raw_key='content_norm', prefix='content_norm')
    _ensure_reason_projection(
        compact,
        payload,
        raw_key='last_reason',
        code_key='last_reason_code',
        stats_prefix='last_reason',
    )
    _ensure_reason_projection(
        compact,
        payload,
        raw_key='override_reason',
        code_key='override_note_code',
        stats_prefix='override_note',
        marker='override_note_present',
    )
    compact['content_minimized'] = True
    return compact


def _compact_legacy_evidence_item(item: Any) -> dict[str, Any]:
    payload = _mapping(item)
    compact = _without_legacy_raw_text(payload)
    _ensure_text_projection(compact, payload, raw_key='content', prefix='content')
    _ensure_text_projection(compact, payload, raw_key='content_norm', prefix='content_norm')
    _ensure_reason_projection(
        compact,
        payload,
        raw_key='reason',
        code_key='reason_code',
        stats_prefix='reason',
    )
    compact['content_minimized'] = True
    return compact


def _compact_legacy_conflict_item(item: Any) -> dict[str, Any]:
    payload = _mapping(item)
    compact = _without_legacy_raw_text(payload)
    _ensure_reason_projection(
        compact,
        payload,
        raw_key='reason',
        code_key='reason_code',
        stats_prefix='reason',
    )
    _ensure_text_projection(compact, payload, raw_key='content_a', prefix='content_a')
    _ensure_text_projection(compact, payload, raw_key='content_b', prefix='content_b')
    compact['identity_pair_count'] = 2
    compact['content_minimized'] = True
    return compact


def _compact_legacy_items(storage_kind: str, items: list[Any]) -> list[dict[str, Any]]:
    if storage_kind == 'identities':
        return [_compact_legacy_fragment_item(item) for item in items]
    if storage_kind == 'identity_evidence':
        return [_compact_legacy_evidence_item(item) for item in items]
    if storage_kind == 'identity_conflicts':
        return [_compact_legacy_conflict_item(item) for item in items]
    return [_without_legacy_raw_text(_mapping(item)) for item in items]


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


def _build_latest_mutable_audit(
    *,
    audit: Mapping[str, Any],
    subject: str,
) -> dict[str, Any]:
    if not audit:
        return {
            'present': False,
            'storage_kind': MUTABLE_AUDIT_STORAGE_KIND,
            'actively_injected': False,
            'subject': subject,
            'mutation_kind': None,
            'actor': None,
            'reason_code': None,
            'old_chars': 0,
            'new_chars': 0,
            'source_trace_id': None,
            'created_ts': None,
        }
    return {
        'present': True,
        'storage_kind': MUTABLE_AUDIT_STORAGE_KIND,
        'actively_injected': False,
        'subject': _optional_text(audit.get('subject')) or subject,
        'mutation_kind': _optional_text(audit.get('mutation_kind')),
        'actor': _optional_text(audit.get('actor')),
        'reason_code': _optional_text(audit.get('reason_code')),
        'old_chars': int(audit.get('old_chars') or 0),
        'new_chars': int(audit.get('new_chars') or 0),
        'source_trace_id': _optional_text(audit.get('source_trace_id')),
        'created_ts': _optional_text(audit.get('created_ts')),
    }


def _build_mutable_layer(
    active_side: Mapping[str, Any],
    *,
    mutable_audit: Mapping[str, Any],
    subject: str,
) -> dict[str, Any]:
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
        'last_mutation_audit': _build_latest_mutable_audit(
            audit=mutable_audit,
            subject=subject,
        ),
    }


def _build_collection_layer(*, storage_kind: str, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    items = _compact_legacy_items(storage_kind, list(snapshot.get('items') or []))
    total_count = int(snapshot.get('total_count') or len(items))
    return {
        'storage_kind': storage_kind,
        'classification': LEGACY_LAYER_CLASSIFICATION,
        'runtime_authority': 'historical_only',
        'projection_version': LEGACY_PROJECTION_VERSION,
        'content_minimized': True,
        'stored': total_count > 0,
        'loaded_for_runtime': False,
        'actively_injected': False,
        'total_count': total_count,
        'limit': int(snapshot.get('limit') or len(items) or DEFAULT_LAYER_LIMIT),
        'items': items,
    }


def build_subject_block(
    *,
    subject: str,
    active_side: Mapping[str, Any],
    static_snapshot: Mapping[str, Any],
    mutable_audit: Mapping[str, Any],
    legacy_fragments: Mapping[str, Any],
    evidence: Mapping[str, Any],
    conflicts: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        'static': _build_static_layer(active_side, static_snapshot=static_snapshot),
        'mutable': _build_mutable_layer(
            active_side,
            mutable_audit=mutable_audit,
            subject=subject,
        ),
        'legacy_fragments': _build_collection_layer(
            storage_kind='identities',
            snapshot=legacy_fragments,
        ),
        'evidence': _build_collection_layer(
            storage_kind='identity_evidence',
            snapshot=evidence,
        ),
        'conflicts': _build_collection_layer(
            storage_kind='identity_conflicts',
            snapshot=conflicts,
        ),
    }


def build_dialogic_context_block(
    *,
    evidence: Mapping[str, Any],
    latest_activity: Mapping[str, Any],
    runtime: Mapping[str, Any],
) -> dict[str, Any]:
    items = [_compact_legacy_evidence_item(item) for item in list(evidence.get('items') or [])]
    activity_payload = _mapping(latest_activity.get('payload'))
    return {
        'classification': 'temporary_dialogic_context',
        'runtime_authority': 'prompt_context_only',
        'storage_kind': 'identity_evidence_compatible_storage',
        'logical_subject': 'dialogue',
        'identity_writer': False,
        'mutable_authority': False,
        'active_caller': 'dialogic_context_hint_extractor',
        'legacy_setting_slot': 'identity_extractor_model',
        'stored': int(evidence.get('total_count') or len(items)) > 0,
        'total_count': int(evidence.get('total_count') or len(items)),
        'limit': int(evidence.get('limit') or len(items) or DEFAULT_LAYER_LIMIT),
        'items': items,
        'content_minimized': True,
        'latest_activity': {
            'present': bool(latest_activity),
            'status': _optional_text(latest_activity.get('status')),
            'reason_code': _optional_text(activity_payload.get('reason_code')),
            'hint_count': int(activity_payload.get('hint_count') or 0),
            'persisted_count': int(activity_payload.get('persisted_count') or 0),
            'prompt_kind': _optional_text(activity_payload.get('prompt_kind')),
            'raw_content_included': False,
        },
        'runtime': dict(runtime),
    }
