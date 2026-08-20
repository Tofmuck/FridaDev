from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, Sequence

from memory import mutable_identity_runtime
from observability import chat_turn_logger


BUFFER_TARGET_PAIRS = 5
FAILURE_ATTEMPT_LIMIT = 2

_TRANSIENT_REASONS = {
    'judge_timeout',
    'judge_transport_error',
}
_DETERMINISTIC_INPUT_REASONS = {
    'runtime_safety_violation',
    'window_too_large',
}
_WRITE_RECOVERY_REASONS = {
    'canonical_write_failed',
    'mutable_store_unavailable',
    'staging_finalize_failed',
}
_FINALIZATION_RECOVERY_STATUSES = {
    'finalization_recovery_applied': True,
    'finalization_recovery_no_change': False,
}


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


def _window_fingerprint(staging_state: Mapping[str, Any]) -> str:
    serialized = json.dumps(
        list(staging_state.get('buffer_pairs') or []),
        ensure_ascii=False,
        sort_keys=True,
        separators=(',', ':'),
    )
    return hashlib.sha256(serialized.encode('utf-8')).hexdigest()[:12]


def _failure_class(reason_code: str, summary: Mapping[str, Any] | None = None) -> str:
    reason = _text(reason_code)
    if reason in _TRANSIENT_REASONS:
        http_status = int(_mapping(summary).get('http_status') or 0)
        if 400 <= http_status < 500 and http_status not in {408, 409, 425, 429}:
            return 'deterministic_contract'
        return 'transient'
    if reason in _DETERMINISTIC_INPUT_REASONS:
        return 'deterministic_input'
    if reason in _WRITE_RECOVERY_REASONS:
        return 'write_recovery'
    return 'deterministic_contract'


def _failure_processing_state(failure_class: str) -> str:
    if failure_class == 'deterministic_input':
        return 'judge_not_called'
    if failure_class == 'write_recovery':
        return 'write_failed'
    return 'judge_failed'


def _policy_fields(
    *,
    failure_class: str,
    recovery_action: str,
    processing_state: str,
    attempt_current: int,
    window_fingerprint: str,
    next_window_progress: str,
    next_buffer_pairs_count: int,
) -> dict[str, Any]:
    return {
        'failure_class': failure_class,
        'recovery_action': recovery_action,
        'processing_state': processing_state,
        'attempt_current': max(0, int(attempt_current)),
        'attempt_limit': FAILURE_ATTEMPT_LIMIT,
        'window_fingerprint': _text(window_fingerprint),
        'next_window_progress': next_window_progress,
        'next_buffer_pairs_count': max(0, int(next_buffer_pairs_count)),
    }


def _write_recovery_is_verified(summary: Mapping[str, Any]) -> bool:
    add_outcomes = [
        _mapping(item)
        for item in list(summary.get('outcomes') or [])
        if _text(_mapping(item).get('verdict')) == 'add'
    ]
    return bool(add_outcomes) and all(
        _text(item.get('status')) == 'skipped'
        and _text(item.get('reason_code')) == 'already_covered_by_mutable'
        for item in add_outcomes
    )


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
            'failure_class': _text(summary.get('failure_class')),
            'recovery_action': _text(summary.get('recovery_action')),
            'processing_state': _text(summary.get('processing_state')),
            'attempt_current': int(summary.get('attempt_current') or 0),
            'attempt_limit': int(summary.get('attempt_limit') or FAILURE_ATTEMPT_LIMIT),
            'window_fingerprint': _text(summary.get('window_fingerprint')),
            'next_window_progress': _text(summary.get('next_window_progress')),
            'next_buffer_pairs_count': int(summary.get('next_buffer_pairs_count') or 0),
            'writes_previously_applied': bool(summary.get('writes_previously_applied')),
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

    pair_appended = bool(staging_state.get('pair_appended', True))
    attempt_current = 1 if pair_appended else FAILURE_ATTEMPT_LIMIT
    next_pair = None if pair_appended else normalized_turn_pair
    next_pairs_count = 0 if pair_appended else 1
    fingerprint = _window_fingerprint(staging_state)
    previous_status = _text(staging_state.get('last_agent_status'))
    previous_reason = _text(staging_state.get('last_agent_reason'))

    if not pair_appended and previous_status in _FINALIZATION_RECOVERY_STATUSES:
        cleared_state = clear_buffer(
            conversation_id,
            status='staging_finalize_recovered',
            reason='staging_finalize_recovered',
            auto_canonization_suspended=auto_canonization_suspended,
            next_pair=next_pair,
        )
        if isinstance(cleared_state, Mapping):
            summary = {
                'status': 'ok',
                'reason_code': 'staging_finalize_recovered',
                'buffer_pairs_count': buffer_pairs_count,
                'buffer_target_pairs': buffer_target_pairs,
                'last_agent_status': 'staging_finalize_recovered',
                'buffer_cleared': True,
                'buffer_frozen': buffer_frozen,
                'auto_canonization_suspended': auto_canonization_suspended,
                'writes_applied': False,
                'writes_previously_applied': bool(_FINALIZATION_RECOVERY_STATUSES[previous_status]),
                'promotion_count': 0,
                'promotions': [],
                'outcomes': [],
                'rejection_reasons': {},
                'legacy_writer_disabled': True,
                'judge_status': 'not_called',
                'apply_status': 'not_called',
                **_policy_fields(
                    failure_class='',
                    recovery_action='completed',
                    processing_state='completed',
                    attempt_current=attempt_current,
                    window_fingerprint=fingerprint,
                    next_window_progress='current_pair_staged',
                    next_buffer_pairs_count=int(cleared_state.get('buffer_pairs_count') or next_pairs_count),
                ),
            }
            _emit_periodic_agent_event(status='ok', reason_code='staging_finalize_recovered', summary=summary)
            return summary

        mark_status(
            conversation_id,
            status=previous_status,
            reason=previous_reason or 'staging_finalize_failed',
            touch_run_ts=False,
        )
        summary = {
            'status': 'skipped',
            'reason_code': 'staging_finalize_failed',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': previous_status,
            'buffer_cleared': False,
            'buffer_frozen': buffer_frozen,
            'auto_canonization_suspended': auto_canonization_suspended,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': True,
            'judge_status': 'not_called',
            'apply_status': 'not_called',
            **_policy_fields(
                failure_class='write_recovery',
                recovery_action='apply_recovery',
                processing_state='write_failed',
                attempt_current=attempt_current,
                window_fingerprint=fingerprint,
                next_window_progress='blocked_write_recovery',
                next_buffer_pairs_count=buffer_pairs_count,
            ),
        }
        _emit_periodic_agent_event(status='skipped', reason_code='staging_finalize_failed', summary=summary)
        return summary

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
        reason_code = _text(runtime_summary.get('reason_code')) or 'judge_failed'
        failure_class = _failure_class(reason_code, runtime_summary)
        processing_state = _failure_processing_state(failure_class)
        terminal = failure_class == 'deterministic_input' or attempt_current >= FAILURE_ATTEMPT_LIMIT
        if terminal:
            cleared_state = clear_buffer(
                conversation_id,
                status='terminal_discarded',
                reason=reason_code,
                auto_canonization_suspended=auto_canonization_suspended,
                next_pair=next_pair,
            )
            if isinstance(cleared_state, Mapping):
                summary = {
                    **dict(runtime_summary),
                    'status': 'skipped',
                    'reason_code': reason_code,
                    'last_agent_status': 'terminal_discarded',
                    'buffer_pairs_count': buffer_pairs_count,
                    'buffer_target_pairs': buffer_target_pairs,
                    'buffer_cleared': True,
                    'buffer_frozen': buffer_frozen,
                    'auto_canonization_suspended': auto_canonization_suspended,
                    **_policy_fields(
                        failure_class=failure_class,
                        recovery_action='terminal_consume_without_write',
                        processing_state=processing_state,
                        attempt_current=attempt_current,
                        window_fingerprint=fingerprint,
                        next_window_progress=(
                            'current_pair_staged' if next_pair is not None else 'ready_for_next_window'
                        ),
                        next_buffer_pairs_count=int(cleared_state.get('buffer_pairs_count') or 0),
                    ),
                }
                _emit_periodic_agent_event(status='skipped', reason_code=reason_code, summary=summary)
                return summary

            mark_status(
                conversation_id,
                status='terminal_discard_failed',
                reason='staging_finalize_failed',
                touch_run_ts=False,
            )
            summary = {
                **dict(runtime_summary),
                'status': 'skipped',
                'reason_code': 'staging_finalize_failed',
                'last_agent_status': 'terminal_discard_failed',
                'buffer_pairs_count': buffer_pairs_count,
                'buffer_target_pairs': buffer_target_pairs,
                'buffer_cleared': False,
                'buffer_frozen': buffer_frozen,
                'auto_canonization_suspended': auto_canonization_suspended,
                **_policy_fields(
                    failure_class='write_recovery',
                    recovery_action='apply_recovery',
                    processing_state='write_failed',
                    attempt_current=attempt_current,
                    window_fingerprint=fingerprint,
                    next_window_progress='blocked_write_recovery',
                    next_buffer_pairs_count=buffer_pairs_count,
                ),
            }
            _emit_periodic_agent_event(status='skipped', reason_code='staging_finalize_failed', summary=summary)
            return summary

        last_status = 'write_recovery_pending' if failure_class == 'write_recovery' else 'retry_pending'
        mark_status(
            conversation_id,
            status=last_status,
            reason=reason_code,
            touch_run_ts=False,
        )
        summary = {
            **dict(runtime_summary),
            'last_agent_status': last_status,
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'buffer_cleared': False,
            'buffer_frozen': buffer_frozen,
            'auto_canonization_suspended': auto_canonization_suspended,
            **_policy_fields(
                failure_class=failure_class,
                recovery_action='apply_recovery' if failure_class == 'write_recovery' else 'retry_preserve',
                processing_state=processing_state,
                attempt_current=attempt_current,
                window_fingerprint=fingerprint,
                next_window_progress=(
                    'blocked_write_recovery' if failure_class == 'write_recovery' else 'blocked_retry_pending'
                ),
                next_buffer_pairs_count=buffer_pairs_count,
            ),
        }
        _emit_periodic_agent_event(status='skipped', reason_code=reason_code, summary=summary)
        return summary

    completion_status = _text(runtime_summary.get('last_agent_status')) or 'completed_no_change'
    completion_reason = _text(runtime_summary.get('reason_code')) or completion_status
    if not pair_appended and previous_status == 'write_recovery_pending' and not bool(
        runtime_summary.get('writes_applied')
    ):
        if _write_recovery_is_verified(runtime_summary):
            completion_status = 'write_recovery_completed'
            completion_reason = 'write_recovery_completed'
        else:
            cleared_state = clear_buffer(
                conversation_id,
                status='terminal_discarded',
                reason='write_recovery_unverified',
                auto_canonization_suspended=auto_canonization_suspended,
                next_pair=next_pair,
            )
            if isinstance(cleared_state, Mapping):
                summary = {
                    **dict(runtime_summary),
                    'status': 'skipped',
                    'reason_code': 'write_recovery_unverified',
                    'last_agent_status': 'terminal_discarded',
                    'buffer_pairs_count': buffer_pairs_count,
                    'buffer_target_pairs': buffer_target_pairs,
                    'buffer_cleared': True,
                    'buffer_frozen': buffer_frozen,
                    'auto_canonization_suspended': auto_canonization_suspended,
                    **_policy_fields(
                        failure_class='write_recovery',
                        recovery_action='terminal_consume_without_write',
                        processing_state='write_failed',
                        attempt_current=attempt_current,
                        window_fingerprint=fingerprint,
                        next_window_progress='current_pair_staged',
                        next_buffer_pairs_count=int(cleared_state.get('buffer_pairs_count') or 0),
                    ),
                }
                _emit_periodic_agent_event(
                    status='skipped',
                    reason_code='write_recovery_unverified',
                    summary=summary,
                )
                return summary
            mark_status(
                conversation_id,
                status='terminal_discard_failed',
                reason='staging_finalize_failed',
                touch_run_ts=False,
            )
            summary = {
                **dict(runtime_summary),
                'status': 'skipped',
                'reason_code': 'staging_finalize_failed',
                'last_agent_status': 'terminal_discard_failed',
                'buffer_pairs_count': buffer_pairs_count,
                'buffer_target_pairs': buffer_target_pairs,
                'buffer_cleared': False,
                'buffer_frozen': buffer_frozen,
                'auto_canonization_suspended': auto_canonization_suspended,
                **_policy_fields(
                    failure_class='write_recovery',
                    recovery_action='apply_recovery',
                    processing_state='write_failed',
                    attempt_current=attempt_current,
                    window_fingerprint=fingerprint,
                    next_window_progress='blocked_write_recovery',
                    next_buffer_pairs_count=buffer_pairs_count,
                ),
            }
            _emit_periodic_agent_event(status='skipped', reason_code='staging_finalize_failed', summary=summary)
            return summary

    cleared_state = clear_buffer(
        conversation_id,
        status=completion_status,
        reason=completion_reason,
        auto_canonization_suspended=auto_canonization_suspended,
        next_pair=next_pair,
    )
    if not isinstance(cleared_state, Mapping):
        finalization_status = (
            'finalization_recovery_applied'
            if bool(runtime_summary.get('writes_applied')) or completion_status == 'write_recovery_completed'
            else 'finalization_recovery_no_change'
        )
        mark_status(
            conversation_id,
            status=finalization_status,
            reason='staging_finalize_failed',
            touch_run_ts=False,
        )
        summary = {
            **dict(runtime_summary),
            'status': 'skipped',
            'reason_code': 'staging_finalize_failed',
            'last_agent_status': finalization_status,
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'buffer_cleared': False,
            'buffer_frozen': buffer_frozen,
            'auto_canonization_suspended': auto_canonization_suspended,
            **_policy_fields(
                failure_class='write_recovery',
                recovery_action='apply_recovery',
                processing_state='write_failed',
                attempt_current=attempt_current,
                window_fingerprint=fingerprint,
                next_window_progress='blocked_write_recovery',
                next_buffer_pairs_count=buffer_pairs_count,
            ),
        }
        _emit_periodic_agent_event(status='skipped', reason_code='staging_finalize_failed', summary=summary)
        return summary

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
        **_policy_fields(
            failure_class='',
            recovery_action='completed',
            processing_state='completed',
            attempt_current=attempt_current,
            window_fingerprint=fingerprint,
            next_window_progress=(
                'current_pair_staged' if next_pair is not None else 'ready_for_next_window'
            ),
            next_buffer_pairs_count=int(cleared_state.get('buffer_pairs_count') or 0),
        ),
    }
    _emit_periodic_agent_event(status='ok', reason_code=str(summary['reason_code']), summary=summary)
    return summary
