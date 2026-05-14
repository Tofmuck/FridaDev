from __future__ import annotations

import hashlib
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
LEGACY_IDENTITY_PIPELINE_STATUS = 'legacy_diagnostic_only'
LEGACY_IDENTITY_PIPELINE_RECORDED_VIA = 'persist_identity_entries'
LEGACY_IDENTITY_PIPELINE_STORAGE = 'identities + identity_evidence + identity_conflicts'
OPEN_TENSIONS_STORAGE_KIND = 'identity_periodic_agent_latest_activity'
OPEN_TENSIONS_SCOPE_KIND = 'conversation_scoped_latest'
MUTABLE_AUDIT_STORAGE_KIND = 'identity_mutable_audit'
TERMINAL_STAGING_REASONS = {
    'applied',
    'completed_no_change',
    'completed_with_open_tension',
}


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


def _sha256_12(text: Any) -> str | None:
    raw = str(text or '')
    if not raw:
        return None
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:12]


def _text_stats(text: Any, *, prefix: str) -> dict[str, Any]:
    raw = str(text or '')
    return {
        f'{prefix}_chars': len(raw),
        f'{prefix}_sha256_12': _sha256_12(raw),
    }


def _free_text_reason_marker(text: Any, *, marker: str) -> str:
    return marker if _optional_text(text) else ''


LEGACY_RAW_TEXT_KEYS = {
    'content',
    'content_norm',
    'last_reason',
    'override_reason',
    'reason',
    'content_a',
    'content_b',
}


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
    target.setdefault(f'{prefix}_chars', 0)
    target.setdefault(f'{prefix}_sha256_12', None)


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
    target.setdefault(f'{stats_prefix}_chars', 0)
    target.setdefault(f'{stats_prefix}_sha256_12', None)


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


def _compact_open_tensions(values: Any) -> list[dict[str, Any]]:
    items = values if isinstance(values, list) else []
    compact: list[dict[str, Any]] = []
    for item in items:
        payload = _mapping(item)
        action = _optional_text(payload.get('action'))
        reason_code = _optional_text(payload.get('reason_code'))
        if action != 'raise_conflict' and reason_code not in {'raise_conflict', 'raise_conflict_open'}:
            continue
        summary: dict[str, Any] = {}
        for key in ('subject', 'action', 'reason_code', 'threshold_verdict'):
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
    open_tensions = _compact_open_tensions(payload.get('outcomes'))
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
        'open_tension_count': len(open_tensions),
        'open_tensions_storage_kind': OPEN_TENSIONS_STORAGE_KIND,
        'open_tensions_scope_kind': OPEN_TENSIONS_SCOPE_KIND,
        'open_tensions_actively_injected': False,
        'open_tensions': open_tensions,
    }


def _empty_latest_agent_activity() -> dict[str, Any]:
    return {
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
        'open_tension_count': 0,
        'open_tensions_storage_kind': OPEN_TENSIONS_STORAGE_KIND,
        'open_tensions_scope_kind': OPEN_TENSIONS_SCOPE_KIND,
        'open_tensions_actively_injected': False,
        'open_tensions': [],
    }


def _clean_current_agent_reason(staging_state: Mapping[str, Any]) -> str | None:
    status = _optional_text(staging_state.get('last_agent_status'))
    reason = _optional_text(staging_state.get('last_agent_reason'))
    if status == 'buffering' and reason in TERMINAL_STAGING_REASONS:
        return None
    return reason


def _build_current_buffer_state(staging_state: Mapping[str, Any]) -> dict[str, Any]:
    if not staging_state:
        return {
            'present': False,
            'conversation_id': None,
            'status': None,
            'reason_code': None,
            'pairs_count': 0,
            'target_pairs': int(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
            'frozen': False,
            'updated_ts': None,
            'auto_canonization_suspended': False,
        }

    pairs_count = int(staging_state.get('buffer_pairs_count') or 0)
    target_pairs = int(staging_state.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS)
    frozen = bool(staging_state.get('buffer_frozen'))
    status = _optional_text(staging_state.get('last_agent_status'))
    reason = _clean_current_agent_reason(staging_state)
    if status == 'buffering':
        reason = 'threshold_reached' if frozen else 'below_threshold'
    return {
        'present': True,
        'conversation_id': _optional_text(staging_state.get('conversation_id')),
        'status': status or ('frozen' if frozen else 'buffering' if pairs_count else 'empty'),
        'reason_code': reason,
        'pairs_count': pairs_count,
        'target_pairs': target_pairs,
        'frozen': frozen,
        'updated_ts': _optional_text(staging_state.get('updated_ts')),
        'auto_canonization_suspended': bool(staging_state.get('auto_canonization_suspended')),
    }


def _build_last_completed_agent(
    *,
    staging_state: Mapping[str, Any],
    latest_activity: Mapping[str, Any],
) -> dict[str, Any]:
    legacy_status = _optional_text(staging_state.get('last_agent_status'))
    legacy_reason = _optional_text(staging_state.get('last_agent_reason'))
    legacy_run_ts = _optional_text(staging_state.get('last_agent_run_ts'))
    activity_reason = _optional_text(latest_activity.get('reason_code'))
    reason_code = activity_reason
    if not reason_code and legacy_reason in TERMINAL_STAGING_REASONS:
        reason_code = legacy_reason
    status = _optional_text(latest_activity.get('status'))
    if not status and legacy_status in TERMINAL_STAGING_REASONS:
        status = legacy_status
    if not status and reason_code:
        status = 'ok'
    ts = _optional_text(latest_activity.get('ts')) or legacy_run_ts
    return {
        'present': bool(latest_activity.get('present') or reason_code or ts),
        'conversation_id': _optional_text(latest_activity.get('conversation_id'))
        or _optional_text(staging_state.get('conversation_id')),
        'turn_id': _optional_text(latest_activity.get('turn_id')),
        'status': status,
        'reason_code': reason_code,
        'run_ts': ts,
        'writes_applied': bool(latest_activity.get('writes_applied')),
        'promotion_count': int(latest_activity.get('promotion_count') or 0),
        'open_tension_count': int(latest_activity.get('open_tension_count') or 0),
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
        else _empty_latest_agent_activity()
    )
    current_buffer = _build_current_buffer_state(staging_state)
    last_completed_agent = _build_last_completed_agent(
        staging_state=staging_state,
        latest_activity=latest_activity,
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
        'last_agent_reason': _clean_current_agent_reason(staging_state),
        'last_agent_run_ts': _optional_text(staging_state.get('last_agent_run_ts')),
        'current_buffer': current_buffer,
        'last_completed_agent': last_completed_agent,
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


def _build_latest_mutable_audit(
    *,
    memory_store_module: Any,
    subject: str,
) -> dict[str, Any]:
    get_latest_audit = getattr(memory_store_module, 'get_latest_mutable_identity_audit', None)
    audit = _mapping(get_latest_audit(subject)) if callable(get_latest_audit) else {}
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
            'old_sha256_12': None,
            'new_sha256_12': None,
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
        'old_sha256_12': _optional_text(audit.get('old_sha256_12')),
        'new_sha256_12': _optional_text(audit.get('new_sha256_12')),
        'source_trace_id': _optional_text(audit.get('source_trace_id')),
        'created_ts': _optional_text(audit.get('created_ts')),
    }


def _build_mutable_layer(
    active_side: Mapping[str, Any],
    *,
    memory_store_module: Any,
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
            memory_store_module=memory_store_module,
            subject=subject,
        ),
    }


def _build_collection_layer(*, storage_kind: str, snapshot: Mapping[str, Any]) -> dict[str, Any]:
    items = _compact_legacy_items(storage_kind, list(snapshot.get('items') or []))
    total_count = int(snapshot.get('total_count') or len(items))
    return {
        'storage_kind': storage_kind,
        'classification': LEGACY_IDENTITY_PIPELINE_STATUS,
        'runtime_authority': 'historical_only',
        'projection_version': 'identity_legacy_content_minimized_v1',
        'content_minimized': True,
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
        'mutable': _build_mutable_layer(
            active_side,
            memory_store_module=memory_store_module,
            subject=subject,
        ),
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
                'legacy_identity_pipeline_status': LEGACY_IDENTITY_PIPELINE_STATUS,
                'legacy_identity_pipeline_recorded_via': LEGACY_IDENTITY_PIPELINE_RECORDED_VIA,
                'legacy_identity_pipeline_storage': LEGACY_IDENTITY_PIPELINE_STORAGE,
                'read_surface_stage': READ_SURFACE_STAGE,
                'identity_runtime_regime': build_identity_runtime_regime(),
            },
            'identity_staging': identity_staging,
            'subjects': subjects,
        },
        200,
    )
