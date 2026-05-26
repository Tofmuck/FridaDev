from __future__ import annotations

from typing import Any, Mapping

from memory import memory_identity_periodic_agent


OPEN_TENSIONS_STORAGE_KIND = 'mutable_identity_judge_latest_activity'
OPEN_TENSIONS_SCOPE_KIND = 'conversation_scoped_latest'


def _optional_text(value: Any) -> str | None:
    text = str(value or '').strip()
    return text or None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
        ):
            text = _optional_text(payload.get(key))
            if text:
                summary[key] = text
        if summary:
            compact.append(summary)
    return compact


def _compact_outcome_item(item: Any) -> dict[str, Any]:
    payload = _mapping(item)
    summary: dict[str, Any] = {'content_minimized': True}
    for key in (
        'subject',
        'action',
        'verdict',
        'status',
        'reason_code',
        'continuity_kind',
    ):
        text = _optional_text(payload.get(key))
        if text:
            summary[key] = text
    for key in (
        'source_refs_count',
        'guard_notes_count',
        'target_count',
        'max_chars',
    ):
        value = _optional_int(payload.get(key))
        if value is not None:
            summary[key] = value
    for source_key, target_key in (
        ('old_chars', 'old_chars'),
        ('new_chars', 'new_chars'),
        ('old_len', 'old_chars'),
        ('new_len', 'new_chars'),
    ):
        value = _optional_int(payload.get(source_key))
        if value is not None:
            summary.setdefault(target_key, value)
    for key in (
        'old_sha256_12',
        'new_sha256_12',
        'target_sha256_12',
    ):
        text = _optional_text(payload.get(key))
        if text:
            summary[key] = text
    targets = payload.get('target_sha256_12s')
    if isinstance(targets, list):
        summary['target_sha256_12s'] = [_optional_text(item) for item in targets if _optional_text(item)]
    return summary


def _compact_outcomes(values: Any) -> list[dict[str, Any]]:
    items = values if isinstance(values, list) else []
    return [_compact_outcome_item(item) for item in items]


def _compact_open_tensions(values: Any) -> list[dict[str, Any]]:
    items = values if isinstance(values, list) else []
    compact: list[dict[str, Any]] = []
    for item in items:
        payload = _mapping(item)
        action = _optional_text(payload.get('action'))
        verdict = _optional_text(payload.get('verdict'))
        reason_code = _optional_text(payload.get('reason_code'))
        if (
            action != 'raise_conflict'
            and verdict != 'raise_tension'
            and reason_code not in {
                'raise_conflict',
                'raise_conflict_open',
                'relation_tension_open',
                'contradiction_open',
            }
        ):
            continue
        summary: dict[str, Any] = {}
        for key in (
            'subject',
            'action',
            'verdict',
            'status',
            'reason_code',
            'continuity_kind',
        ):
            text = _optional_text(payload.get(key))
            if text:
                summary[key] = text
        for key in ('source_refs_count', 'guard_notes_count', 'old_chars', 'new_chars'):
            value = _optional_int(payload.get(key))
            if value is not None:
                summary[key] = value
        for key in ('old_sha256_12', 'new_sha256_12'):
            text = _optional_text(payload.get(key))
            if text:
                summary[key] = text
        if summary:
            summary['content_minimized'] = True
            compact.append(summary)
    return compact


def empty_latest_agent_activity() -> dict[str, Any]:
    return {
        'present': False,
        'stage': None,
        'activity_runtime_authority': None,
        'conversation_id': None,
        'turn_id': None,
        'ts': None,
        'status': None,
        'reason_code': None,
        'runtime_pipeline': None,
        'prompt_kind': None,
        'write_mode': None,
        'writes_applied': False,
        'promotion_count': 0,
        'promotions': [],
        'rejection_reasons': {},
        'buffer_pairs_count': 0,
        'buffer_target_pairs': int(memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
        'buffer_cleared': False,
        'buffer_frozen': False,
        'judge_status': None,
        'judge_reason_code': None,
        'validation_reason': None,
        'invalid_verdict_index': None,
        'invalid_subject': None,
        'invalid_verdict': None,
        'invalid_reason_code': None,
        'invalid_proposition_chars': None,
        'invalid_source_refs_count': None,
        'invalid_guard_notes_count': None,
        'apply_status': None,
        'apply_reason_code': None,
        'verdict_count': 0,
        'verdict_counts': {},
        'subjects_seen': [],
        'subjects_touched': [],
        'continuity_kinds': [],
        'reason_codes': [],
        'source_refs_count': 0,
        'guard_notes_count': 0,
        'applied_count': 0,
        'skipped_count': 0,
        'failed_count': 0,
        'outcome_count': 0,
        'outcome_summaries': [],
        'open_tension_count': 0,
        'open_tensions_storage_kind': OPEN_TENSIONS_STORAGE_KIND,
        'open_tensions_scope_kind': OPEN_TENSIONS_SCOPE_KIND,
        'open_tensions_actively_injected': False,
        'open_tensions': [],
        'content_minimized': True,
    }


def latest_agent_activity(event: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(event.get('payload'))
    stage = _optional_text(event.get('stage'))
    open_tensions = _compact_open_tensions(payload.get('outcomes'))
    outcome_summaries = _compact_outcomes(payload.get('outcomes'))
    activity = {
        'present': bool(event),
        'stage': stage,
        'activity_runtime_authority': (
            'active_mutable_identity_judge_v2_add_only'
            if stage == 'mutable_identity_judge'
            else 'legacy_pre_refactor_fallback'
            if stage == 'identity_periodic_agent'
            else None
        ),
        'conversation_id': _optional_text(event.get('conversation_id')),
        'turn_id': _optional_text(event.get('turn_id')),
        'ts': _optional_text(event.get('ts')),
        'status': _optional_text(event.get('status')),
        'reason_code': _optional_text(payload.get('reason_code')),
        'runtime_pipeline': _optional_text(payload.get('runtime_pipeline')),
        'prompt_kind': _optional_text(payload.get('prompt_kind')),
        'write_mode': _optional_text(payload.get('write_mode')),
        'writes_applied': bool(payload.get('writes_applied')),
        'promotion_count': int(payload.get('promotion_count') or 0),
        'promotions': _compact_promotions(payload.get('promotions')),
        'rejection_reasons': dict(payload.get('rejection_reasons') or {}),
        'buffer_pairs_count': int(payload.get('buffer_pairs_count') or 0),
        'buffer_target_pairs': int(payload.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS),
        'buffer_cleared': bool(payload.get('buffer_cleared')),
        'buffer_frozen': bool(payload.get('buffer_frozen')),
        'judge_status': _optional_text(payload.get('judge_status')),
        'judge_reason_code': _optional_text(payload.get('judge_reason_code')),
        'apply_status': _optional_text(payload.get('apply_status')),
        'apply_reason_code': _optional_text(payload.get('apply_reason_code')),
        'verdict_count': int(payload.get('verdict_count') or 0),
        'verdict_counts': dict(payload.get('verdict_counts') or {}),
        'subjects_seen': list(payload.get('subjects_seen') or []),
        'subjects_touched': list(payload.get('subjects_touched') or []),
        'continuity_kinds': list(payload.get('continuity_kinds') or []),
        'reason_codes': list(payload.get('reason_codes') or []),
        'source_refs_count': int(payload.get('source_refs_count') or 0),
        'guard_notes_count': int(payload.get('guard_notes_count') or 0),
        'applied_count': int(payload.get('applied_count') or 0),
        'skipped_count': int(payload.get('skipped_count') or 0),
        'failed_count': int(payload.get('failed_count') or 0),
        'outcome_count': len(outcome_summaries),
        'outcome_summaries': outcome_summaries,
        'open_tension_count': len(open_tensions),
        'open_tensions_storage_kind': OPEN_TENSIONS_STORAGE_KIND,
        'open_tensions_scope_kind': OPEN_TENSIONS_SCOPE_KIND,
        'open_tensions_actively_injected': False,
        'open_tensions': open_tensions,
        'content_minimized': True,
    }
    for key in (
        'window_chars',
        'payload_chars',
        'estimated_prompt_tokens',
        'max_window_chars',
        'max_estimated_prompt_tokens',
        'invalid_verdict_index',
        'invalid_proposition_chars',
        'invalid_source_refs_count',
        'invalid_guard_notes_count',
        'http_status',
    ):
        value = _optional_int(payload.get(key))
        if value is not None:
            activity[key] = value
    for key in (
        'validation_reason',
        'invalid_subject',
        'invalid_verdict',
        'invalid_reason_code',
        'error_class',
    ):
        text = _optional_text(payload.get(key))
        if text:
            activity[key] = text
    return activity
