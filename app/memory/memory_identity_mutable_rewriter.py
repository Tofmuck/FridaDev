from __future__ import annotations

import logging
from typing import Any, Mapping, Sequence

from observability import chat_turn_logger

logger = logging.getLogger('frida.identity_mutable_rewriter')

_SUBJECTS = ('llm', 'user')
_LEGACY_REASON_CODE = 'legacy_rewriter_retired'


def _string(value: Any) -> str:
    return str(value or '').strip()


def _current_content(item: Mapping[str, Any] | None) -> str:
    if not isinstance(item, Mapping):
        return ''
    return _string(item.get('content'))


def _subject_outcome(subject: str, *, old_len: int) -> dict[str, Any]:
    return {
        'subject': subject,
        'action': 'retired',
        'old_len': int(old_len),
        'new_len': None,
        'validation_ok': False,
        'reason_code': _LEGACY_REASON_CODE,
    }


def validate_rewriter_contract(raw: Any) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    del raw
    return {}, [_subject_outcome(subject, old_len=0) for subject in _SUBJECTS]


def refresh_mutable_identities(
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    load_llm_identity_fn: Any = None,
    load_user_identity_fn: Any = None,
) -> dict[str, Any]:
    del recent_turns, arbiter_module, load_llm_identity_fn, load_user_identity_fn
    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    current_by_subject = {
        subject: _current_content(get_mutable_identity(subject)) if callable(get_mutable_identity) else ''
        for subject in _SUBJECTS
    }
    outcomes = [
        _subject_outcome(subject, old_len=len(current_by_subject.get(subject, '')))
        for subject in _SUBJECTS
    ]
    summary = {
        'status': 'skipped',
        'reason_code': _LEGACY_REASON_CODE,
        'legacy_runtime_active': False,
        'outcomes': outcomes,
    }
    logger.info('identity_legacy_rewriter_retired')
    chat_turn_logger.emit_branch_skipped(
        reason_code=_LEGACY_REASON_CODE,
        reason_short='identity_legacy_rewriter_disabled',
    )
    return summary
