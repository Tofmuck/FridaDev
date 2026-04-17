from __future__ import annotations

from typing import Any, Mapping, Sequence

import config
from identity import identity
from memory import memory_identity_periodic_apply
from observability import chat_turn_logger


BUFFER_TARGET_PAIRS = 15


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _subject_identity_payload(
    *,
    subject: str,
    memory_store_module: Any,
) -> dict[str, Any]:
    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    if callable(get_mutable_identity):
        mutable = _mapping(get_mutable_identity(subject))
    else:
        mutable = {}
    return {
        'static': identity.load_llm_identity() if subject == 'llm' else identity.load_user_identity(),
        'mutable_current': _text(mutable.get('content')),
    }


def _build_agent_payload(
    *,
    staging_state: Mapping[str, Any],
    memory_store_module: Any,
) -> dict[str, Any]:
    buffer_pairs = list(staging_state.get('buffer_pairs') or [])
    return {
        'buffer_pairs': buffer_pairs,
        'buffer_pairs_count': int(staging_state.get('buffer_pairs_count') or len(buffer_pairs)),
        'buffer_target_pairs': int(staging_state.get('buffer_target_pairs') or BUFFER_TARGET_PAIRS),
        'identities': {
            'llm': _subject_identity_payload(subject='llm', memory_store_module=memory_store_module),
            'user': _subject_identity_payload(subject='user', memory_store_module=memory_store_module),
        },
        'mutable_budget': {
            'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
            'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
        },
    }


def _emit_periodic_agent_event(
    *,
    status: str,
    reason_code: str,
    summary: Mapping[str, Any],
) -> None:
    chat_turn_logger.emit(
        'identity_periodic_agent',
        status=status,
        reason_code=reason_code,
        payload={
            'buffer_pairs_count': int(summary.get('buffer_pairs_count') or 0),
            'buffer_target_pairs': int(summary.get('buffer_target_pairs') or BUFFER_TARGET_PAIRS),
            'buffer_cleared': bool(summary.get('buffer_cleared')),
            'writes_applied': bool(summary.get('writes_applied')),
            'last_agent_status': _text(summary.get('last_agent_status')),
            'outcomes': list(summary.get('outcomes') or []),
        },
        prompt_kind='identity_periodic_agent',
    )


def stage_identity_turn_pair(
    conversation_id: str,
    turn_pair: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
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
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='skipped', reason_code='staging_store_unavailable', summary=summary)
        return summary

    staging_state = append_pair(
        conversation_id,
        turn_pair,
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
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='error', reason_code='staging_append_failed', summary=summary)
        return summary

    buffer_pairs_count = int(staging_state.get('buffer_pairs_count') or 0)
    buffer_target_pairs = int(staging_state.get('buffer_target_pairs') or BUFFER_TARGET_PAIRS)
    if buffer_pairs_count < buffer_target_pairs:
        return {
            'status': 'buffering',
            'reason_code': 'below_threshold',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': _text(staging_state.get('last_agent_status')) or 'buffering',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': [],
        }

    mark_status(
        conversation_id,
        status='running',
        reason='threshold_reached',
        touch_run_ts=True,
    )
    staging_state = get_staging_state(conversation_id) or staging_state
    payload = _build_agent_payload(
        staging_state=staging_state,
        memory_store_module=memory_store_module,
    )
    run_agent = getattr(arbiter_module, 'run_identity_periodic_agent', None)
    if not callable(run_agent):
        mark_status(conversation_id, status='agent_unavailable', reason='run_identity_periodic_agent_missing', touch_run_ts=False)
        summary = {
            'status': 'skipped',
            'reason_code': 'agent_unavailable',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': 'agent_unavailable',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='skipped', reason_code='agent_unavailable', summary=summary)
        return summary

    try:
        contract_payload = run_agent(payload)
    except Exception as exc:
        mark_status(conversation_id, status='agent_call_error', reason=exc.__class__.__name__, touch_run_ts=False)
        summary = {
            'status': 'skipped',
            'reason_code': 'agent_call_error',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': 'agent_call_error',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='error', reason_code='agent_call_error', summary=summary)
        return summary

    if not isinstance(contract_payload, Mapping):
        mark_status(conversation_id, status='agent_call_failed', reason='empty_or_invalid_json', touch_run_ts=False)
        summary = {
            'status': 'skipped',
            'reason_code': 'agent_call_failed',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': 'agent_call_failed',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='skipped', reason_code='agent_call_failed', summary=summary)
        return summary

    validated_contract, validation_reason = memory_identity_periodic_apply.validate_periodic_agent_contract(
        contract_payload,
        buffer_pairs_count=buffer_pairs_count,
        target_pairs=buffer_target_pairs,
    )
    if validated_contract is None:
        mark_status(conversation_id, status='contract_invalid', reason=validation_reason or 'contract_invalid', touch_run_ts=False)
        summary = {
            'status': 'skipped',
            'reason_code': validation_reason or 'contract_invalid',
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': 'contract_invalid',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': [],
        }
        _emit_periodic_agent_event(status='skipped', reason_code=validation_reason or 'contract_invalid', summary=summary)
        return summary

    apply_summary = memory_identity_periodic_apply.apply_periodic_agent_contract(
        validated_contract,
        memory_store_module=memory_store_module,
        load_llm_identity_fn=identity.load_llm_identity,
        load_user_identity_fn=identity.load_user_identity,
    )
    if str(apply_summary.get('status') or '') != 'ok':
        mark_status(
            conversation_id,
            status='apply_failed',
            reason=str(apply_summary.get('reason_code') or 'apply_failed'),
            touch_run_ts=False,
        )
        summary = {
            'status': str(apply_summary.get('status') or 'skipped'),
            'reason_code': str(apply_summary.get('reason_code') or 'apply_failed'),
            'buffer_pairs_count': buffer_pairs_count,
            'buffer_target_pairs': buffer_target_pairs,
            'last_agent_status': 'apply_failed',
            'buffer_cleared': False,
            'writes_applied': False,
            'outcomes': list(apply_summary.get('outcomes') or []),
        }
        _emit_periodic_agent_event(
            status='error',
            reason_code=str(summary['reason_code']),
            summary=summary,
        )
        return summary

    completion_status = 'applied' if bool(apply_summary.get('writes_applied')) else 'completed_no_change'
    clear_buffer(
        conversation_id,
        status=completion_status,
        reason=str(apply_summary.get('reason_code') or completion_status),
    )
    summary = {
        'status': str(apply_summary.get('status') or 'ok'),
        'reason_code': str(apply_summary.get('reason_code') or completion_status),
        'buffer_pairs_count': buffer_pairs_count,
        'buffer_target_pairs': buffer_target_pairs,
        'last_agent_status': completion_status,
        'buffer_cleared': True,
        'writes_applied': bool(apply_summary.get('writes_applied')),
        'outcomes': list(apply_summary.get('outcomes') or []),
    }
    _emit_periodic_agent_event(status='ok', reason_code=str(summary['reason_code']), summary=summary)
    return summary
