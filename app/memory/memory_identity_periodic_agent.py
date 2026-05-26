from __future__ import annotations

from typing import Any, Mapping, Sequence

from memory import mutable_identity_runtime
from observability import chat_turn_logger


BUFFER_TARGET_PAIRS = 5


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _normalize_message(value: Any, *, expected_role: str) -> dict[str, Any] | None:
    payload = _mapping(value)
    role = _text(payload.get('role')).lower()
    if role != expected_role:
        return None
    normalized = {
        'role': expected_role,
        'content': _text(payload.get('content')),
    }
    timestamp = _text(payload.get('timestamp'))
    if timestamp:
        normalized['timestamp'] = timestamp
    return normalized


def _normalize_complete_turn_pair(turn_pair: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]] | None:
    if isinstance(turn_pair, (str, bytes, bytearray)):
        return None
    items = list(turn_pair or [])
    if len(items) != 2:
        return None
    user = _normalize_message(items[0], expected_role='user')
    assistant = _normalize_message(items[1], expected_role='assistant')
    if user is None or assistant is None:
        return None
    return [user, assistant]


def _completed_summary_state(apply_summary: Mapping[str, Any]) -> tuple[str, str]:
    reason_code = _text(apply_summary.get('reason_code'))
    if bool(apply_summary.get('writes_applied')):
        return 'applied', reason_code or 'applied'

    return 'completed_no_change', reason_code or 'completed_no_change'


def _emit_periodic_agent_event(
    *,
    status: str,
    reason_code: str,
    summary: Mapping[str, Any],
) -> None:
    event_reason_code = _text(summary.get('reason_code')) or _text(reason_code)
    chat_turn_logger.emit(
        'mutable_identity_judge',
        status=status,
        reason_code=event_reason_code,
        payload={
            'reason_code': event_reason_code,
            'runtime_pipeline': _text(summary.get('runtime_pipeline')) or mutable_identity_runtime.PIPELINE_NAME,
            'prompt_kind': _text(summary.get('prompt_kind')) or 'mutable_identity_judge_v2',
            'buffer_pairs_count': int(summary.get('buffer_pairs_count') or 0),
            'buffer_target_pairs': int(summary.get('buffer_target_pairs') or BUFFER_TARGET_PAIRS),
            'buffer_cleared': bool(summary.get('buffer_cleared')),
            'buffer_frozen': bool(summary.get('buffer_frozen')),
            'auto_canonization_suspended': bool(summary.get('auto_canonization_suspended')),
            'writes_applied': bool(summary.get('writes_applied')),
            'write_mode': _text(summary.get('write_mode')),
            'shadow_mode': bool(summary.get('shadow_mode')),
            'score_first_writer_enabled': bool(summary.get('score_first_writer_enabled')),
            'promotion_count': int(summary.get('promotion_count') or 0),
            'promotions': list(summary.get('promotions') or []),
            'last_agent_status': _text(summary.get('last_agent_status')),
            'outcomes': list(summary.get('outcomes') or []),
            'rejection_reasons': dict(summary.get('rejection_reasons') or {}),
            'legacy_writer_disabled': bool(summary.get('legacy_writer_disabled')),
            'legacy_writer_disabled_reason': _text(summary.get('legacy_writer_disabled_reason')),
            'judge_status': _text(summary.get('judge_status')),
            'judge_reason_code': _text(summary.get('judge_reason_code')),
            'apply_status': _text(summary.get('apply_status')),
            'apply_reason_code': _text(summary.get('apply_reason_code')),
            'verdict_counts': dict(summary.get('verdict_counts') or {}),
            'verdict_count': int(summary.get('verdict_count') or 0),
            'subjects_seen': list(summary.get('subjects_seen') or []),
            'subjects_touched': list(summary.get('subjects_touched') or []),
            'continuity_kinds': list(summary.get('continuity_kinds') or []),
            'reason_codes': list(summary.get('reason_codes') or []),
            'source_refs_count': int(summary.get('source_refs_count') or 0),
            'guard_notes_count': int(summary.get('guard_notes_count') or 0),
            'applied_count': int(summary.get('applied_count') or 0),
            'skipped_count': int(summary.get('skipped_count') or 0),
            'failed_count': int(summary.get('failed_count') or 0),
            **{
                key: summary.get(key)
                for key in (
                    'window_chars',
                    'payload_chars',
                    'estimated_prompt_tokens',
                    'max_window_chars',
                    'max_estimated_prompt_tokens',
                )
                if summary.get(key) is not None
            },
            **{
                key: summary.get(key)
                for key in (
                    'validation_reason',
                    'invalid_verdict_index',
                    'invalid_subject',
                    'invalid_verdict',
                    'invalid_reason_code',
                    'invalid_proposition_chars',
                    'invalid_source_refs_count',
                    'invalid_guard_notes_count',
                    'http_status',
                    'error_class',
                )
                if summary.get(key) is not None
            },
        },
        prompt_kind='mutable_identity_judge_v2',
    )


def stage_identity_turn_pair(
    conversation_id: str,
    turn_pair: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    enforce_writes: bool = True,
) -> dict[str, Any]:
    append_pair = getattr(memory_store_module, 'append_identity_staging_pair', None)
    get_staging_state = getattr(memory_store_module, 'get_identity_staging_state', None)
    mark_status = getattr(memory_store_module, 'mark_identity_staging_status', None)
    clear_buffer = getattr(memory_store_module, 'clear_identity_staging_buffer', None)
    if not callable(append_pair) or not callable(get_staging_state) or not callable(mark_status) or not callable(clear_buffer):
        summary = {
            'status': 'skipped',
            'reason_code': 'staging_store_unavailable',
            'buffer_pairs_count': 0,
            'buffer_target_pairs': BUFFER_TARGET_PAIRS,
            'last_agent_status': 'store_unavailable',
            'buffer_cleared': False,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': False,
        }
        _emit_periodic_agent_event(status='skipped', reason_code='staging_store_unavailable', summary=summary)
        return summary

    normalized_turn_pair = _normalize_complete_turn_pair(turn_pair)
    if normalized_turn_pair is None:
        summary = {
            'status': 'skipped',
            'reason_code': 'incomplete_turn_pair',
            'buffer_pairs_count': 0,
            'buffer_target_pairs': BUFFER_TARGET_PAIRS,
            'last_agent_status': 'incomplete_turn_pair',
            'buffer_cleared': False,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': False,
        }
        _emit_periodic_agent_event(status='skipped', reason_code='incomplete_turn_pair', summary=summary)
        return summary

    staging_state = append_pair(
        conversation_id,
        normalized_turn_pair,
        target_pairs=BUFFER_TARGET_PAIRS,
    )
    if not isinstance(staging_state, Mapping):
        summary = {
            'status': 'skipped',
            'reason_code': 'staging_append_failed',
            'buffer_pairs_count': 0,
            'buffer_target_pairs': BUFFER_TARGET_PAIRS,
            'last_agent_status': 'staging_append_failed',
            'buffer_cleared': False,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': False,
        }
        _emit_periodic_agent_event(status='error', reason_code='staging_append_failed', summary=summary)
        return summary

    buffer_pairs_count = int(staging_state.get('buffer_pairs_count') or 0)
    buffer_target_pairs = int(staging_state.get('buffer_target_pairs') or BUFFER_TARGET_PAIRS)
    buffer_frozen = bool(staging_state.get('buffer_frozen'))
    auto_canonization_suspended = bool(staging_state.get('auto_canonization_suspended'))
    if buffer_pairs_count < buffer_target_pairs:
        return {
            'status': 'buffering',
            'reason_code': 'below_threshold',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': _text(staging_state.get('last_agent_status')) or 'buffering',
            'buffer_cleared': False,
            'buffer_frozen': buffer_frozen,
            'auto_canonization_suspended': auto_canonization_suspended,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': False,
        }

    mark_status(
        conversation_id,
        status='running',
        reason='threshold_reached',
        touch_run_ts=True,
    )
    staging_state = get_staging_state(conversation_id) or staging_state
    runtime_summary = mutable_identity_runtime.run_mutable_identity_window(
        staging_state=staging_state,
        arbiter_module=arbiter_module,
        memory_store_module=memory_store_module,
        enforce_writes=bool(enforce_writes),
    )

    if _text(runtime_summary.get('status')) != 'ok':
        last_status = _text(runtime_summary.get('last_agent_status')) or 'judge_failed'
        reason_code = _text(runtime_summary.get('reason_code')) or 'judge_failed'
        mark_status(
            conversation_id,
            status=last_status,
            reason=reason_code,
            touch_run_ts=False,
        )
        summary = {
            **dict(runtime_summary),
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'buffer_cleared': False,
            'buffer_frozen': buffer_frozen,
            'auto_canonization_suspended': auto_canonization_suspended,
        }
        _emit_periodic_agent_event(status='skipped', reason_code=reason_code, summary=summary)
        return summary

    completion_status = _text(runtime_summary.get('last_agent_status')) or 'completed_no_change'
    completion_reason = _text(runtime_summary.get('reason_code')) or completion_status
    clear_buffer(
        conversation_id,
        status=completion_status,
        reason=completion_reason,
        auto_canonization_suspended=auto_canonization_suspended,
    )
    summary = {
        **dict(runtime_summary),
        'status': _text(runtime_summary.get('status')) or 'ok',
        'reason_code': completion_reason,
        'buffer_pairs_count': buffer_pairs_count,
        'buffer_target_pairs': buffer_target_pairs,
        'last_agent_status': completion_status,
        'buffer_cleared': True,
        'buffer_frozen': buffer_frozen,
        'auto_canonization_suspended': auto_canonization_suspended,
    }
    _emit_periodic_agent_event(status='ok', reason_code=str(summary['reason_code']), summary=summary)
    return summary
