from __future__ import annotations

import logging
from typing import Any, Callable, Mapping, Sequence

import config
from identity import identity as static_identity
from observability import chat_turn_logger

logger = logging.getLogger('frida.identity_mutable_rewriter')

_SUBJECTS = ('llm', 'user')
_ALLOWED_ACTIONS = {'no_change', 'rewrite'}
_REWRITER_UPDATED_BY = 'identity_mutable_rewriter'


def _string(value: Any) -> str:
    return str(value or '').strip()


def _current_content(item: Mapping[str, Any] | None) -> str:
    if not isinstance(item, Mapping):
        return ''
    return _string(item.get('content'))


def _subject_outcome(
    subject: str,
    *,
    action: str,
    old_len: int,
    new_len: int | None,
    validation_ok: bool,
    reason_code: str,
) -> dict[str, Any]:
    return {
        'subject': subject,
        'action': action,
        'old_len': int(old_len),
        'new_len': int(new_len) if new_len is not None else None,
        'validation_ok': bool(validation_ok),
        'reason_code': str(reason_code),
    }


def _emit_rewriter_summary(summary: Mapping[str, Any]) -> None:
    status = str(summary.get('status') or 'ok')
    reason_code = str(summary.get('reason_code') or '')
    chat_turn_logger.emit(
        'identity_mutable_rewrite',
        status=status,
        reason_code=reason_code if status == 'skipped' else None,
        payload={
            'request_status': status,
            'reason_code': reason_code,
            'outcomes': list(summary.get('outcomes') or []),
        },
        prompt_kind='identity_mutable_rewriter',
    )


def _build_rewriter_payload(
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    load_llm_identity_fn: Callable[[], str],
    load_user_identity_fn: Callable[[], str],
    memory_store_module: Any,
) -> dict[str, Any]:
    llm_mutable = memory_store_module.get_mutable_identity('llm') or {}
    user_mutable = memory_store_module.get_mutable_identity('user') or {}
    return {
        'mutable_budget': {
            'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
            'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
        },
        'recent_turns': [
            {
                'role': _string(turn.get('role')),
                'content': _string(turn.get('content')),
            }
            for turn in recent_turns
            if _string(turn.get('content'))
        ],
        'identities': {
            'llm': {
                'static': _string(load_llm_identity_fn()),
                'mutable_current': _current_content(llm_mutable),
            },
            'user': {
                'static': _string(load_user_identity_fn()),
                'mutable_current': _current_content(user_mutable),
            },
        },
    }


def _validate_subject_contract(subject: str, raw: Any) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    if not isinstance(raw, dict):
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_subject_not_object'}

    required_keys = {'action', 'content', 'reason'}
    present_keys = set(raw.keys())
    missing_keys = sorted(required_keys - present_keys)
    if missing_keys:
        if 'action' in missing_keys:
            reason_code = 'contract_action_missing'
        elif 'content' in missing_keys:
            reason_code = 'contract_content_missing'
        else:
            reason_code = 'contract_reason_missing'
        return None, {'action': 'rejected', 'content': '', 'reason_code': reason_code}

    unexpected_keys = sorted(present_keys - required_keys)
    if unexpected_keys:
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_subject_extra_keys'}

    action = _string(raw.get('action')).lower()
    content = _string(raw.get('content'))
    reason = _string(raw.get('reason'))

    if action not in _ALLOWED_ACTIONS:
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_action_invalid'}
    if not reason:
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_reason_missing'}
    if len(reason) > 240:
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_reason_too_long'}
    if action == 'no_change' and content:
        return None, {'action': 'rejected', 'content': content, 'reason_code': 'contract_no_change_has_content'}
    if action == 'rewrite' and not content:
        return None, {'action': 'rejected', 'content': '', 'reason_code': 'contract_rewrite_missing_content'}
    if action == 'rewrite' and len(content) > int(config.IDENTITY_MUTABLE_MAX_CHARS):
        return None, {'action': 'rejected', 'content': content, 'reason_code': 'mutable_content_too_long'}

    return {
        'subject': subject,
        'action': action,
        'content': content,
        'reason': reason,
    }, None


def validate_rewriter_contract(raw: Any) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(raw, dict):
        rejections = [
            _subject_outcome(
                subject,
                action='rejected',
                old_len=0,
                new_len=None,
                validation_ok=False,
                reason_code='contract_root_not_object',
            )
            for subject in _SUBJECTS
        ]
        return {}, rejections

    top_keys = set(raw.keys())
    expected_keys = set(_SUBJECTS)
    if top_keys != expected_keys:
        rejections = [
            _subject_outcome(
                subject,
                action='rejected',
                old_len=0,
                new_len=None,
                validation_ok=False,
                reason_code='contract_subject_keys_invalid',
            )
            for subject in _SUBJECTS
        ]
        return {}, rejections

    validated: dict[str, dict[str, Any]] = {}
    rejections: list[dict[str, Any]] = []
    for subject in _SUBJECTS:
        normalized, error = _validate_subject_contract(subject, raw.get(subject))
        if normalized is not None:
            validated[subject] = normalized
            continue
        rejections.append(
            _subject_outcome(
                subject,
                action='rejected',
                old_len=0,
                new_len=len(_string((error or {}).get('content')) or ''),
                validation_ok=False,
                reason_code=str((error or {}).get('reason_code') or 'contract_invalid'),
            )
        )
    return validated, rejections


def _reject_all_with_existing_lengths(
    current_by_subject: Mapping[str, str],
    *,
    reason_code: str,
) -> dict[str, Any]:
    outcomes = [
        _subject_outcome(
            subject,
            action='rejected',
            old_len=len(current_by_subject.get(subject, '')),
            new_len=None,
            validation_ok=False,
            reason_code=reason_code,
        )
        for subject in _SUBJECTS
    ]
    summary = {
        'status': 'skipped',
        'reason_code': reason_code,
        'outcomes': outcomes,
    }
    _emit_rewriter_summary(summary)
    return summary


def refresh_mutable_identities(
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    load_llm_identity_fn: Callable[[], str] | None = None,
    load_user_identity_fn: Callable[[], str] | None = None,
) -> dict[str, Any]:
    load_llm_identity = load_llm_identity_fn or static_identity.load_llm_identity
    load_user_identity = load_user_identity_fn or static_identity.load_user_identity
    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    upsert_mutable_identity = getattr(memory_store_module, 'upsert_mutable_identity', None)

    if not callable(get_mutable_identity) or not callable(upsert_mutable_identity):
        empty_current = {subject: '' for subject in _SUBJECTS}
        return _reject_all_with_existing_lengths(empty_current, reason_code='mutable_store_unavailable')

    current_by_subject = {
        subject: _current_content(get_mutable_identity(subject))
        for subject in _SUBJECTS
    }
    if not recent_turns:
        return _reject_all_with_existing_lengths(current_by_subject, reason_code='no_recent_turns')

    rewrite_fn = getattr(arbiter_module, 'rewrite_identity_mutables', None)
    if not callable(rewrite_fn):
        return _reject_all_with_existing_lengths(current_by_subject, reason_code='rewriter_unavailable')

    payload = _build_rewriter_payload(
        recent_turns,
        load_llm_identity_fn=load_llm_identity,
        load_user_identity_fn=load_user_identity,
        memory_store_module=memory_store_module,
    )

    try:
        raw_contract = rewrite_fn(payload)
    except Exception as exc:
        logger.error(
            'identity_mutable_rewriter_call_error error_class=%s',
            exc.__class__.__name__,
        )
        return _reject_all_with_existing_lengths(current_by_subject, reason_code='rewriter_call_error')

    if raw_contract is None:
        return _reject_all_with_existing_lengths(current_by_subject, reason_code='rewriter_no_result')

    validated, rejected_outcomes = validate_rewriter_contract(raw_contract)
    outcomes: list[dict[str, Any]] = []
    for item in rejected_outcomes:
        subject = str(item.get('subject') or '')
        outcomes.append(
            {
                **item,
                'old_len': len(current_by_subject.get(subject, '')),
            }
        )

    for subject in _SUBJECTS:
        if subject not in validated:
            continue
        current_content = current_by_subject.get(subject, '')
        old_len = len(current_content)
        action = str(validated[subject]['action'])
        candidate_content = _string(validated[subject].get('content'))
        if action == 'no_change':
            outcomes.append(
                _subject_outcome(
                    subject,
                    action='no_change',
                    old_len=old_len,
                    new_len=old_len,
                    validation_ok=True,
                    reason_code='no_change',
                )
            )
            continue
        if candidate_content == current_content:
            outcomes.append(
                _subject_outcome(
                    subject,
                    action='no_change',
                    old_len=old_len,
                    new_len=old_len,
                    validation_ok=True,
                    reason_code='unchanged',
                )
            )
            continue
        updated = upsert_mutable_identity(
            subject,
            candidate_content,
            updated_by=_REWRITER_UPDATED_BY,
            update_reason=str(validated[subject].get('reason') or '')[:500],
        )
        if updated is None:
            outcomes.append(
                _subject_outcome(
                    subject,
                    action='rejected',
                    old_len=old_len,
                    new_len=len(candidate_content),
                    validation_ok=False,
                    reason_code='upsert_failed',
                )
            )
            continue
        outcomes.append(
            _subject_outcome(
                subject,
                action='rewrite',
                old_len=old_len,
                new_len=len(candidate_content),
                validation_ok=True,
                reason_code='rewrite_applied',
            )
        )

    ordered_outcomes = sorted(
        outcomes,
        key=lambda item: _SUBJECTS.index(str(item.get('subject') or 'llm')),
    )
    summary = {
        'status': 'ok',
        'reason_code': 'processed',
        'outcomes': ordered_outcomes,
    }
    _emit_rewriter_summary(summary)
    return summary
