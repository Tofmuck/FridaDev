from __future__ import annotations

from typing import Any, Mapping

import config
from identity import identity
from memory import mutable_identity_apply
from memory import mutable_identity_judge_v2


PIPELINE_NAME = 'mutable_identity_judge_v2_add_only'
WRITER_ACTOR = 'mutable_identity_judge_apply'
SHADOW_REASON_CODE = 'shadow_completed'


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return list(value)
    return []


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


def _build_judge_input(
    *,
    staging_state: Mapping[str, Any],
    memory_store_module: Any,
) -> dict[str, Any]:
    buffer_pairs = list(staging_state.get('buffer_pairs') or [])
    return mutable_identity_judge_v2.build_judge_input(
        window_pairs=buffer_pairs,
        identities={
            'llm': _subject_identity_payload(subject='llm', memory_store_module=memory_store_module),
            'user': _subject_identity_payload(subject='user', memory_store_module=memory_store_module),
        },
        mutable_budget={
            'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
            'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
        },
        source_annotations={
            'staging': {
                'buffer_pairs_count': int(staging_state.get('buffer_pairs_count') or len(buffer_pairs)),
                'buffer_target_pairs': int(staging_state.get('buffer_target_pairs') or 5),
                'buffer_frozen': bool(staging_state.get('buffer_frozen')),
                'auto_canonization_suspended': bool(staging_state.get('auto_canonization_suspended')),
                'last_agent_status': _text(staging_state.get('last_agent_status')),
            }
        },
    )


def _empty_observability(reason_code: str) -> dict[str, Any]:
    return {
        'status': 'skipped',
        'reason_code': reason_code,
        'schema_version': mutable_identity_judge_v2.SCHEMA_VERSION,
        'prompt_kind': mutable_identity_judge_v2.PROMPT_KIND,
        'window_pairs_count': 0,
        'window_complete': False,
        'verdict_count': 0,
        'verdict_counts': {},
        'subjects_seen': [],
        'subjects_touched': [],
        'continuity_kinds': [],
        'reason_codes': [],
        'source_refs_count': 0,
        'guard_notes_count': 0,
    }


def _completion_from_apply(apply_summary: Mapping[str, Any]) -> tuple[str, str]:
    reason_code = _text(apply_summary.get('reason_code'))
    if bool(apply_summary.get('writes_applied')):
        return 'applied', reason_code or 'applied'

    return 'completed_no_change', reason_code or 'completed_no_change'


def _size_fields(observability: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: observability.get(key)
        for key in (
            'window_chars',
            'payload_chars',
            'estimated_prompt_tokens',
            'max_window_chars',
            'max_estimated_prompt_tokens',
        )
        if observability.get(key) is not None
    }


def _validation_fields(observability: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: observability.get(key)
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
        if observability.get(key) is not None
    }


def _summary(
    *,
    status: str,
    reason_code: str,
    last_agent_status: str,
    judge_observability: Mapping[str, Any],
    apply_summary: Mapping[str, Any] | None = None,
    enforce_writes: bool,
) -> dict[str, Any]:
    apply_payload = _mapping(apply_summary)
    return {
        'status': status,
        'reason_code': reason_code,
        'last_agent_status': last_agent_status,
        'runtime_pipeline': PIPELINE_NAME,
        'prompt_kind': mutable_identity_judge_v2.PROMPT_KIND,
        'score_first_writer_enabled': False,
        'legacy_writer_disabled': True,
        'legacy_writer_disabled_reason': 'score_first_writer_retired_from_active_path',
        'write_mode': 'enforced' if enforce_writes else 'shadow',
        'shadow_mode': not enforce_writes,
        'writes_applied': bool(apply_payload.get('writes_applied')),
        'promotion_count': 0,
        'promotions': [],
        'outcomes': list(apply_payload.get('outcomes') or []),
        'rejection_reasons': {},
        'judge_status': _text(judge_observability.get('status')) or ('ok' if status == 'ok' else 'skipped'),
        'judge_reason_code': _text(judge_observability.get('reason_code')) or reason_code,
        'apply_status': _text(apply_payload.get('status')),
        'apply_reason_code': _text(apply_payload.get('reason_code')),
        'verdict_counts': dict(judge_observability.get('verdict_counts') or {}),
        'verdict_count': int(judge_observability.get('verdict_count') or 0),
        'subjects_seen': list(judge_observability.get('subjects_seen') or []),
        'subjects_touched': list(judge_observability.get('subjects_touched') or []),
        'continuity_kinds': list(judge_observability.get('continuity_kinds') or []),
        'reason_codes': list(judge_observability.get('reason_codes') or []),
        'source_refs_count': int(judge_observability.get('source_refs_count') or 0),
        'guard_notes_count': int(judge_observability.get('guard_notes_count') or 0),
        'applied_count': int(apply_payload.get('applied_count') or 0),
        'skipped_count': int(apply_payload.get('skipped_count') or 0),
        'failed_count': int(apply_payload.get('failed_count') or 0),
        **_size_fields(judge_observability),
        **_validation_fields(judge_observability),
    }


def run_mutable_identity_window(
    *,
    staging_state: Mapping[str, Any],
    arbiter_module: Any,
    memory_store_module: Any,
    enforce_writes: bool,
    window_fingerprint: str | None = None,
) -> dict[str, Any]:
    try:
        judge_input = _build_judge_input(
            staging_state=staging_state,
            memory_store_module=memory_store_module,
        )
    except Exception as exc:
        return _summary(
            status='skipped',
            reason_code='runtime_safety_violation',
            last_agent_status='judge_input_invalid',
            judge_observability={**_empty_observability('runtime_safety_violation'), 'error_class': exc.__class__.__name__},
            enforce_writes=enforce_writes,
        )

    run_judge = getattr(arbiter_module, 'run_mutable_identity_judge', None)
    if not callable(run_judge):
        run_judge = mutable_identity_judge_v2.run_mutable_identity_judge_v2

    try:
        judge_result = run_judge(judge_input)
    except Exception as exc:
        return _summary(
            status='skipped',
            reason_code='judge_transport_error',
            last_agent_status='judge_call_error',
            judge_observability={**_empty_observability('judge_transport_error'), 'error_class': exc.__class__.__name__},
            enforce_writes=enforce_writes,
        )

    judge_payload = _mapping(judge_result)
    judge_observability = _mapping(judge_payload.get('observability')) or _empty_observability(
        _text(judge_payload.get('reason_code')) or 'schema_invalid'
    )
    if _text(judge_payload.get('status')) != 'ok':
        reason = _text(judge_payload.get('reason_code')) or 'schema_invalid'
        return _summary(
            status='skipped',
            reason_code=reason,
            last_agent_status=reason,
            judge_observability=judge_observability,
            enforce_writes=enforce_writes,
        )

    contract = _mapping(judge_payload.get('contract'))
    if not contract:
        return _summary(
            status='skipped',
            reason_code='schema_invalid',
            last_agent_status='schema_invalid',
            judge_observability=judge_observability,
            enforce_writes=enforce_writes,
        )

    if not enforce_writes:
        return _summary(
            status='ok',
            reason_code=SHADOW_REASON_CODE,
            last_agent_status=SHADOW_REASON_CODE,
            judge_observability=judge_observability,
            enforce_writes=False,
        )

    try:
        apply_summary = mutable_identity_apply.apply_mutable_judge_contract(
            contract,
            memory_store_module=memory_store_module,
            static_identity_by_subject={
                'llm': _text(_mapping(_mapping(judge_input.get('identities')).get('llm')).get('static')),
                'user': _text(_mapping(_mapping(judge_input.get('identities')).get('user')).get('static')),
            },
            staging_conversation_id=_text(staging_state.get('conversation_id')) or None,
            staging_window_fingerprint=_text(window_fingerprint) or None,
        )
    except Exception:
        return _summary(
            status='skipped',
            reason_code='canonical_write_failed',
            last_agent_status='apply_failed',
            judge_observability=judge_observability,
            apply_summary={
                'status': 'skipped',
                'reason_code': 'canonical_write_failed',
                'writes_applied': False,
                'applied_count': 0,
                'skipped_count': 0,
                'failed_count': 1,
                'outcomes': [],
            },
            enforce_writes=True,
        )
    if _text(apply_summary.get('status')) != 'ok':
        return _summary(
            status='skipped',
            reason_code=_text(apply_summary.get('reason_code')) or 'canonical_write_failed',
            last_agent_status='apply_failed',
            judge_observability=judge_observability,
            apply_summary=apply_summary,
            enforce_writes=True,
        )

    completion_status, completion_reason = _completion_from_apply(apply_summary)
    return _summary(
        status='ok',
        reason_code=completion_reason,
        last_agent_status=completion_status,
        judge_observability=judge_observability,
        apply_summary=apply_summary,
        enforce_writes=True,
    )
