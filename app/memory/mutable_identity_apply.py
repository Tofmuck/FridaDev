from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

import config
from memory import mutable_identity_judge_v2


ACTOR = 'mutable_identity_judge_apply'
UPDATE_REASON = 'mutable_judge_add'
AUDIT_REASON_CODE = 'mutable_judge_add'
_ALLOWED_SUBJECTS = {'llm', 'user'}
_PROMPT_LIKE_RE = re.compile(
    r'(ignore\s+previous|system\s+prompt|developer\s+message|follow\s+these\s+instructions|'
    r'tu\s+dois\s+repondre|tu\s+dois\s+répondre|reponds\s+comme|réponds\s+comme)',
    re.IGNORECASE,
)


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


def _split_propositions(text: str) -> list[str]:
    return [_text(line) for line in str(text or '').splitlines() if _text(line)]


def _joined_content(lines: Sequence[str]) -> str:
    return '\n'.join(_text(line) for line in lines if _text(line))


def _norm(value: Any) -> str:
    return re.sub(r'\s+', ' ', _text(value)).lower()


def _content_fields(old_content: str, new_content: str) -> dict[str, Any]:
    return {
        'old_chars': len(old_content),
        'new_chars': len(new_content),
    }


def _outcome(
    *,
    subject: str,
    verdict: str,
    status: str,
    reason_code: str,
    continuity_kind: str,
    old_content: str,
    new_content: str,
    source_refs_count: int,
    guard_notes_count: int,
    proposition: str = '',
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        'subject': subject,
        'verdict': verdict,
        'status': status,
        'reason_code': reason_code,
        'continuity_kind': continuity_kind,
        'source_refs_count': source_refs_count,
        'guard_notes_count': guard_notes_count,
        **_content_fields(old_content, new_content),
    }
    if proposition:
        payload['proposition_chars'] = len(proposition)
    payload.update(extra)
    return payload


def _validate_proposition_text(proposition: str) -> str:
    text = _text(proposition)
    if not text:
        return 'empty_proposition'
    if len(text) > int(config.IDENTITY_MUTABLE_MAX_CHARS):
        return 'proposition_too_long'
    if '\n' in text or _PROMPT_LIKE_RE.search(text):
        return 'prompt_like_content'
    if text.endswith('?'):
        return 'non_declarative_content'
    return ''


def _non_add_outcome(item: Mapping[str, Any], current_content: str) -> dict[str, Any]:
    return _outcome(
        subject=_text(item.get('subject')),
        verdict=_text(item.get('verdict')) or 'no_change',
        status='skipped',
        reason_code=_text(item.get('reason_code')) or 'no_mutable_identity_signal',
        continuity_kind=_text(item.get('continuity_kind')) or 'none',
        old_content=current_content,
        new_content=current_content,
        source_refs_count=len(_list(item.get('source_refs'))),
        guard_notes_count=len(_list(item.get('guard_notes'))),
    )


def _apply_add_verdict(
    *,
    item: Mapping[str, Any],
    current_content: str,
    current_lines: Sequence[str],
    static_content: str,
) -> tuple[list[str] | None, dict[str, Any]]:
    subject = _text(item.get('subject'))
    proposition = _text(item.get('proposition'))
    continuity_kind = _text(item.get('continuity_kind'))
    source_refs_count = len(_list(item.get('source_refs')))
    guard_notes_count = len(_list(item.get('guard_notes')))
    lines = list(current_lines)
    validation_reason = _validate_proposition_text(proposition)
    if validation_reason:
        return None, _outcome(
            subject=subject,
            verdict='add',
            status='failed',
            reason_code=validation_reason,
            continuity_kind=continuity_kind,
            old_content=current_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
        )

    proposition_norm = _norm(proposition)
    if proposition_norm in {_norm(line) for line in lines}:
        return lines, _outcome(
            subject=subject,
            verdict='add',
            status='skipped',
            reason_code='already_covered_by_mutable',
            continuity_kind=continuity_kind,
            old_content=current_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
        )
    static_norms = {_norm(line) for line in _split_propositions(static_content)}
    whole_static_norm = _norm(static_content)
    if proposition_norm and (proposition_norm == whole_static_norm or proposition_norm in static_norms):
        return lines, _outcome(
            subject=subject,
            verdict='add',
            status='skipped',
            reason_code='already_covered_by_static',
            continuity_kind=continuity_kind,
            old_content=current_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
        )

    lines.append(proposition)
    return lines, _outcome(
        subject=subject,
        verdict='add',
        status='applied',
        reason_code='add_applied',
        continuity_kind=continuity_kind,
        old_content=current_content,
        new_content=_joined_content(lines),
        source_refs_count=source_refs_count,
        guard_notes_count=guard_notes_count,
        proposition=proposition,
    )


def _subject_plan(
    *,
    verdicts: Sequence[Mapping[str, Any]],
    current_content: str,
    static_content: str,
) -> tuple[str | None, list[dict[str, Any]]]:
    lines = _split_propositions(current_content)
    outcomes: list[dict[str, Any]] = []
    for item in verdicts:
        if _text(item.get('verdict')) != 'add':
            outcomes.append(_non_add_outcome(item, _joined_content(lines)))
            continue
        next_lines, outcome = _apply_add_verdict(
            item=item,
            current_content=current_content,
            current_lines=lines,
            static_content=static_content,
        )
        outcomes.append(outcome)
        if next_lines is None:
            return None, outcomes
        lines = next_lines
    return _joined_content(lines), outcomes


def _empty_summary(reason_code: str) -> dict[str, Any]:
    return {
        'status': 'skipped',
        'reason_code': reason_code,
        'writes_applied': False,
        'applied_count': 0,
        'skipped_count': 0,
        'failed_count': 0,
        'outcomes': [],
        'subjects_touched': [],
        'audit_storage': 'identity_mutable_audit',
    }


def apply_mutable_judge_contract(
    contract: Mapping[str, Any],
    *,
    memory_store_module: Any,
    static_identity_by_subject: Mapping[str, str] | None = None,
    staging_conversation_id: str | None = None,
    staging_window_fingerprint: str | None = None,
) -> dict[str, Any]:
    active_names = mutable_identity_judge_v2.active_identity_names_by_subject(
        static_identity_by_subject=static_identity_by_subject or {}
    )
    validated_contract, validation_reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(
        contract,
        active_names_by_subject=active_names,
    )
    if validated_contract is None:
        return _empty_summary(validation_reason or 'schema_invalid')

    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    apply_subject_updates = getattr(memory_store_module, 'apply_mutable_identity_subject_updates', None)
    if not callable(get_mutable_identity) or not callable(apply_subject_updates):
        return _empty_summary('mutable_store_unavailable')

    verdicts_by_subject: dict[str, list[Mapping[str, Any]]] = {subject: [] for subject in sorted(_ALLOWED_SUBJECTS)}
    for item in _list(validated_contract.get('verdicts')):
        payload = _mapping(item)
        subject = _text(payload.get('subject'))
        if subject in verdicts_by_subject:
            verdicts_by_subject[subject].append(payload)

    static_by_subject = {
        subject: _text(_mapping(static_identity_by_subject or {}).get(subject))
        for subject in sorted(_ALLOWED_SUBJECTS)
    }
    current_by_subject: dict[str, str] = {}
    next_by_subject: dict[str, str] = {}
    outcomes: list[dict[str, Any]] = []
    max_content_chars = int(config.IDENTITY_MUTABLE_MAX_CHARS)

    for subject in sorted(_ALLOWED_SUBJECTS):
        current_item = _mapping(get_mutable_identity(subject))
        current_content = _text(current_item.get('content'))
        current_by_subject[subject] = current_content
        next_content, subject_outcomes = _subject_plan(
            verdicts=verdicts_by_subject.get(subject) or [],
            current_content=current_content,
            static_content=static_by_subject.get(subject, ''),
        )
        outcomes.extend(subject_outcomes)
        if next_content is None:
            return {
                **_empty_summary('impossible_mutation'),
                'skipped_count': len([item for item in outcomes if item.get('status') == 'skipped']),
                'failed_count': len([item for item in outcomes if item.get('status') == 'failed']),
                'outcomes': outcomes,
                'subjects_touched': sorted({str(item.get('subject') or '') for item in outcomes if item.get('status') == 'failed'}),
            }
        if len(next_content) > max_content_chars:
            outcomes.append(
                _outcome(
                    subject=subject,
                    verdict='add',
                    status='failed',
                    reason_code='mutable_content_too_long',
                    continuity_kind='none',
                    old_content=current_content,
                    new_content=next_content,
                    source_refs_count=0,
                    guard_notes_count=0,
                    max_chars=max_content_chars,
                )
            )
            return {
                **_empty_summary('mutable_content_too_long'),
                'failed_count': 1,
                'outcomes': outcomes,
                'subjects_touched': [subject],
            }
        next_by_subject[subject] = next_content

    subject_updates: list[dict[str, Any]] = []
    for subject in sorted(_ALLOWED_SUBJECTS):
        if next_by_subject.get(subject, '') == current_by_subject.get(subject, ''):
            continue
        subject_updates.append(
            {
                'subject': subject,
                'mutation_kind': 'set',
                'content': next_by_subject[subject],
                'source_trace_id': None,
                'updated_by': ACTOR,
                'update_reason': UPDATE_REASON,
                'audit_reason_code': AUDIT_REASON_CODE,
            }
        )

    try:
        persistence_kwargs: dict[str, Any] = {}
        if subject_updates and _text(staging_conversation_id) and _text(staging_window_fingerprint):
            persistence_kwargs = {
                'staging_conversation_id': _text(staging_conversation_id),
                'staging_window_fingerprint': _text(staging_window_fingerprint),
            }
        result = apply_subject_updates(
            subject_updates,
            **persistence_kwargs,
        )
        if result is None or len(result) != len(subject_updates) or any(item is None for item in result):
            raise RuntimeError('canonical_write_failed')
        writes_applied = bool(subject_updates)
    except Exception:
        return {
            **_empty_summary('canonical_write_failed'),
            'skipped_count': len([item for item in outcomes if item.get('status') == 'skipped']),
            'failed_count': max(1, len([item for item in outcomes if item.get('status') == 'failed'])),
            'outcomes': outcomes,
            'subjects_touched': sorted(
                subject
                for subject, content in next_by_subject.items()
                if content != current_by_subject.get(subject, '')
            ),
        }

    applied_count = len([item for item in outcomes if item.get('status') == 'applied'])
    skipped_count = len([item for item in outcomes if item.get('status') == 'skipped'])
    failed_count = len([item for item in outcomes if item.get('status') == 'failed'])
    return {
        'status': 'ok',
        'reason_code': 'applied' if writes_applied else 'completed_no_change',
        'writes_applied': writes_applied,
        'applied_count': applied_count,
        'skipped_count': skipped_count,
        'failed_count': failed_count,
        'outcomes': outcomes,
        'subjects_touched': sorted({str(item.get('subject') or '') for item in outcomes if item.get('status') == 'applied'}),
        'audit_storage': 'identity_mutable_audit',
    }
