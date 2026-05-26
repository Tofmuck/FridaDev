from __future__ import annotations

import hashlib
import re
from typing import Any, Mapping, Sequence

import config
from memory import mutable_identity_refs
from memory import mutable_identity_judge


ACTOR = 'mutable_identity_judge_apply'
UPDATE_REASON = 'mutable_judge_persist'
_ALLOWED_SUBJECTS = {'llm', 'user'}
_PERSIST_OPERATIONS = {'add', 'tighten', 'merge', 'clear_obsolete'}
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


def _short_hash(value: Any) -> str | None:
    text = _text(value)
    if not text:
        return None
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _split_propositions(text: str) -> list[str]:
    return mutable_identity_refs.split_propositions(text)


def _joined_content(lines: Sequence[str]) -> str:
    return '\n'.join(_text(line) for line in lines if _text(line))


def _norm(value: Any) -> str:
    return re.sub(r'\s+', ' ', _text(value)).lower()


def _find_unique_index_with_reason(lines: Sequence[str], target: str) -> tuple[int | None, str]:
    target_norm = _norm(target)
    if not target_norm:
        return None, 'invalid_target'
    matches = [index for index, line in enumerate(lines) if _norm(line) == target_norm]
    if not matches:
        return None, 'target_not_found'
    if len(matches) != 1:
        return None, 'target_ambiguous'
    return matches[0], ''


def _content_fields(old_content: str, new_content: str) -> dict[str, Any]:
    return {
        'old_chars': len(old_content),
        'new_chars': len(new_content),
        'old_sha256_12': _short_hash(old_content),
        'new_sha256_12': _short_hash(new_content),
    }


def _target_fields(item: Mapping[str, Any]) -> dict[str, Any]:
    target = _text(item.get('target'))
    targets = [_text(value) for value in _list(item.get('targets')) if _text(value)]
    target_ref = _text(item.get('target_ref')).lower()
    target_refs = [_text(value).lower() for value in _list(item.get('target_refs')) if _text(value)]
    payload: dict[str, Any] = {}
    if target:
        payload['target_sha256_12'] = _short_hash(target)
    if targets:
        payload['target_count'] = len(targets)
        payload['target_sha256_12s'] = [_short_hash(value) for value in targets]
    if target_ref:
        payload['target_ref'] = target_ref
    if target_refs:
        payload['target_refs_count'] = len(target_refs)
        payload['target_refs'] = target_refs
    return payload


def _resolve_single_target_index(
    *,
    subject: str,
    current_lines: Sequence[str],
    current_origins: Sequence[int | None],
    original_lines: Sequence[str],
    item: Mapping[str, Any],
) -> tuple[int | None, str]:
    target_ref = _text(item.get('target_ref')).lower()
    if target_ref:
        original_index, reason = mutable_identity_refs.resolve_ref_index(
            subject=subject,
            ref=target_ref,
            lines=original_lines,
        )
        if reason or original_index is None:
            return None, reason or 'target_ref_invalid'
        matches = [index for index, origin in enumerate(current_origins) if origin == original_index]
        if not matches:
            return None, 'target_already_mutated'
        if len(matches) != 1:
            return None, 'target_ambiguous'
        return matches[0], ''
    return _find_unique_index_with_reason(current_lines, _text(item.get('target')))


def _resolve_target_indexes(
    *,
    subject: str,
    current_lines: Sequence[str],
    current_origins: Sequence[int | None],
    original_lines: Sequence[str],
    item: Mapping[str, Any],
) -> tuple[list[int] | None, str]:
    target_refs = [_text(value).lower() for value in _list(item.get('target_refs')) if _text(value)]
    if target_refs:
        indexes: list[int] = []
        for target_ref in target_refs:
            original_index, reason = mutable_identity_refs.resolve_ref_index(
                subject=subject,
                ref=target_ref,
                lines=original_lines,
            )
            if reason or original_index is None:
                return None, reason or 'target_ref_invalid'
            matches = [index for index, origin in enumerate(current_origins) if origin == original_index]
            if not matches:
                return None, 'target_already_mutated'
            if len(matches) != 1:
                return None, 'target_ambiguous'
            indexes.append(matches[0])
    else:
        indexes = []
        for target in [_text(value) for value in _list(item.get('targets'))]:
            found_index, reason = _find_unique_index_with_reason(current_lines, target)
            if reason or found_index is None:
                return None, reason or 'invalid_target'
            indexes.append(found_index)
    unique_indexes = sorted(set(indexes))
    if len(unique_indexes) != len(indexes):
        return None, 'target_ambiguous'
    if len(unique_indexes) < 2:
        return None, 'invalid_target'
    return unique_indexes, ''


def _outcome(
    *,
    subject: str,
    verdict: str,
    operation: str,
    status: str,
    reason_code: str,
    continuity_kind: str,
    old_content: str,
    new_content: str,
    source_refs_count: int,
    guard_notes_count: int,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        'subject': subject,
        'verdict': verdict,
        'operation': operation,
        'status': status,
        'reason_code': reason_code,
        'continuity_kind': continuity_kind,
        'source_refs_count': source_refs_count,
        'guard_notes_count': guard_notes_count,
        **_content_fields(old_content, new_content),
    }
    payload.update(extra)
    return payload


def _non_persist_outcome(item: Mapping[str, Any], current_content: str) -> dict[str, Any]:
    return _outcome(
        subject=_text(item.get('subject')),
        verdict=_text(item.get('verdict')),
        operation='',
        status='skipped',
        reason_code=_text(item.get('reason_code')) or _text(item.get('verdict')) or 'no_change',
        continuity_kind=_text(item.get('continuity_kind')) or 'none',
        old_content=current_content,
        new_content=current_content,
        source_refs_count=len(_list(item.get('source_refs'))),
        guard_notes_count=len(_list(item.get('guard_notes'))),
    )


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


def _operation_audit_reason(operation_kinds: Sequence[str]) -> str:
    unique = sorted({_text(item) for item in operation_kinds if _text(item)})
    if len(unique) == 1:
        return f'mutable_judge_{unique[0]}'
    return 'mutable_judge_multi'


def _apply_operation_to_lines(
    *,
    item: Mapping[str, Any],
    original_content: str,
    current_lines: Sequence[str],
    current_origins: Sequence[int | None],
    original_lines: Sequence[str],
) -> tuple[list[str] | None, list[int | None] | None, dict[str, Any]]:
    subject = _text(item.get('subject'))
    operation = _text(item.get('operation'))
    reason_code = _text(item.get('reason_code'))
    continuity_kind = _text(item.get('continuity_kind'))
    source_refs_count = len(_list(item.get('source_refs')))
    guard_notes_count = len(_list(item.get('guard_notes')))
    lines = list(current_lines)
    origins = list(current_origins)
    current_content = _joined_content(lines)

    if operation not in _PERSIST_OPERATIONS:
        return None, None, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='failed',
            reason_code='invalid_operation',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
            **_target_fields(item),
        )
    if not mutable_identity_judge.persist_reason_code_matches_operation(operation, reason_code):
        return None, None, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='failed',
            reason_code='invalid_operation',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
            **_target_fields(item),
        )

    proposition = _text(item.get('proposition'))
    if operation in {'add', 'tighten', 'merge'}:
        validation_reason = _validate_proposition_text(proposition)
        if validation_reason:
            return None, None, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='failed',
                reason_code=validation_reason,
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
                **_target_fields(item),
            )

    if operation == 'add':
        if _norm(proposition) in {_norm(line) for line in lines}:
            return lines, origins, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='skipped',
                reason_code='already_present',
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
            )
        lines.append(proposition)
        origins.append(None)
        return lines, origins, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='applied',
            reason_code='add_applied',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=_joined_content(lines),
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
        )

    if operation == 'tighten':
        target_index, target_reason = _resolve_single_target_index(
            subject=subject,
            current_lines=lines,
            current_origins=origins,
            original_lines=original_lines,
            item=item,
        )
        if target_index is None:
            return None, None, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='failed',
                reason_code=target_reason or 'invalid_target',
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
                **_target_fields(item),
            )
        proposition_norm = _norm(proposition)
        target_norm = _norm(lines[target_index])
        if proposition_norm != target_norm and proposition_norm in {_norm(line) for line in lines}:
            return None, None, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='failed',
                reason_code='impossible_mutation',
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
                **_target_fields(item),
            )
        lines[target_index] = proposition
        return lines, origins, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='applied',
            reason_code='tighten_applied',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=_joined_content(lines),
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
            **_target_fields(item),
        )

    if operation == 'merge':
        unique_indexes, target_reason = _resolve_target_indexes(
            subject=subject,
            current_lines=lines,
            current_origins=origins,
            original_lines=original_lines,
            item=item,
        )
        if unique_indexes is None:
            return None, None, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='failed',
                reason_code=target_reason or 'invalid_target',
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
                **_target_fields(item),
            )
        target_norms = {_norm(lines[index]) for index in unique_indexes}
        if _norm(proposition) not in target_norms and _norm(proposition) in {_norm(line) for line in lines}:
            return None, None, _outcome(
                subject=subject,
                verdict='persist',
                operation=operation,
                status='failed',
                reason_code='impossible_mutation',
                continuity_kind=continuity_kind,
                old_content=original_content,
                new_content=current_content,
                source_refs_count=source_refs_count,
                guard_notes_count=guard_notes_count,
                **_target_fields(item),
            )
        next_lines = [line for index, line in enumerate(lines) if index not in unique_indexes]
        next_origins = [origin for index, origin in enumerate(origins) if index not in unique_indexes]
        next_lines.insert(unique_indexes[0], proposition)
        next_origins.insert(unique_indexes[0], None)
        return next_lines, next_origins, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='applied',
            reason_code='merge_applied',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=_joined_content(next_lines),
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
            **_target_fields(item),
        )

    target_index, target_reason = _resolve_single_target_index(
        subject=subject,
        current_lines=lines,
        current_origins=origins,
        original_lines=original_lines,
        item=item,
    )
    if target_index is None:
        return None, None, _outcome(
            subject=subject,
            verdict='persist',
            operation=operation,
            status='failed',
            reason_code=target_reason or 'invalid_target',
            continuity_kind=continuity_kind,
            old_content=original_content,
            new_content=current_content,
            source_refs_count=source_refs_count,
            guard_notes_count=guard_notes_count,
            **_target_fields(item),
        )
    del lines[target_index]
    del origins[target_index]
    return lines, origins, _outcome(
        subject=subject,
        verdict='persist',
        operation=operation,
        status='applied',
        reason_code='clear_obsolete_applied',
        continuity_kind=continuity_kind,
        old_content=original_content,
        new_content=_joined_content(lines),
        source_refs_count=source_refs_count,
        guard_notes_count=guard_notes_count,
        **_target_fields(item),
    )


def _subject_plan(
    *,
    subject: str,
    verdicts: Sequence[Mapping[str, Any]],
    current_content: str,
) -> tuple[str | None, list[dict[str, Any]]]:
    original_lines = _split_propositions(current_content)
    lines = list(original_lines)
    origins: list[int | None] = list(range(len(original_lines)))
    outcomes: list[dict[str, Any]] = []
    for item in verdicts:
        if _text(item.get('verdict')) != 'persist':
            outcomes.append(_non_persist_outcome(item, _joined_content(lines)))
            continue
        next_lines, next_origins, outcome = _apply_operation_to_lines(
            item=item,
            original_content=current_content,
            current_lines=lines,
            current_origins=origins,
            original_lines=original_lines,
        )
        outcomes.append(outcome)
        if next_lines is None or next_origins is None:
            return None, outcomes
        lines = next_lines
        origins = next_origins
    return _joined_content(lines), outcomes


def apply_mutable_judge_contract(
    contract: Mapping[str, Any],
    *,
    memory_store_module: Any,
) -> dict[str, Any]:
    validated_contract, validation_reason = mutable_identity_judge.validate_mutable_judge_contract(contract)
    if validated_contract is None:
        return {
            'status': 'skipped',
            'reason_code': validation_reason or 'schema_invalid',
            'writes_applied': False,
            'applied_count': 0,
            'skipped_count': 0,
            'failed_count': 0,
            'outcomes': [],
            'subjects_touched': [],
            'operation_kinds': [],
            'audit_storage': 'identity_mutable_audit',
        }

    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    apply_subject_updates = getattr(memory_store_module, 'apply_mutable_identity_subject_updates', None)
    if not callable(get_mutable_identity) or not callable(apply_subject_updates):
        return {
            'status': 'skipped',
            'reason_code': 'mutable_store_unavailable',
            'writes_applied': False,
            'applied_count': 0,
            'skipped_count': 0,
            'failed_count': 0,
            'outcomes': [],
            'subjects_touched': [],
            'operation_kinds': [],
            'audit_storage': 'identity_mutable_audit',
        }

    verdicts_by_subject: dict[str, list[Mapping[str, Any]]] = {subject: [] for subject in sorted(_ALLOWED_SUBJECTS)}
    for item in _list(validated_contract.get('verdicts')):
        payload = _mapping(item)
        verdicts_by_subject[_text(payload.get('subject'))].append(payload)

    current_by_subject: dict[str, str] = {}
    next_by_subject: dict[str, str] = {}
    outcomes: list[dict[str, Any]] = []
    operations_by_subject: dict[str, list[str]] = {subject: [] for subject in sorted(_ALLOWED_SUBJECTS)}
    max_content_chars = int(config.IDENTITY_MUTABLE_MAX_CHARS)

    for subject in sorted(_ALLOWED_SUBJECTS):
        current_item = _mapping(get_mutable_identity(subject))
        current_content = _text(current_item.get('content'))
        current_by_subject[subject] = current_content
        next_content, subject_outcomes = _subject_plan(
            subject=subject,
            verdicts=verdicts_by_subject.get(subject) or [],
            current_content=current_content,
        )
        outcomes.extend(subject_outcomes)
        operations_by_subject[subject] = [
            _text(item.get('operation'))
            for item in verdicts_by_subject.get(subject) or []
            if _text(item.get('verdict')) == 'persist' and _text(item.get('operation'))
        ]
        if next_content is None:
            return {
                'status': 'skipped',
                'reason_code': 'impossible_mutation',
                'writes_applied': False,
                'applied_count': 0,
                'skipped_count': len([item for item in outcomes if item.get('status') == 'skipped']),
                'failed_count': len([item for item in outcomes if item.get('status') == 'failed']),
                'outcomes': outcomes,
                'subjects_touched': sorted({str(item.get('subject') or '') for item in outcomes if item.get('status') == 'failed'}),
                'operation_kinds': sorted({str(item.get('operation') or '') for item in outcomes if item.get('operation')}),
                'audit_storage': 'identity_mutable_audit',
            }
        if len(next_content) > max_content_chars:
            outcomes.append(
                _outcome(
                    subject=subject,
                    verdict='persist',
                    operation='',
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
                'status': 'skipped',
                'reason_code': 'mutable_content_too_long',
                'writes_applied': False,
                'applied_count': 0,
                'skipped_count': len([item for item in outcomes if item.get('status') == 'skipped']),
                'failed_count': len([item for item in outcomes if item.get('status') == 'failed']),
                'outcomes': outcomes,
                'subjects_touched': [subject],
                'operation_kinds': sorted({operation for values in operations_by_subject.values() for operation in values}),
                'audit_storage': 'identity_mutable_audit',
            }
        next_by_subject[subject] = next_content

    subject_updates: list[dict[str, Any]] = []
    for subject in sorted(_ALLOWED_SUBJECTS):
        if next_by_subject.get(subject, '') == current_by_subject.get(subject, ''):
            continue
        operation_kinds = operations_by_subject.get(subject) or ['persist']
        if next_by_subject.get(subject):
            subject_updates.append(
                {
                    'subject': subject,
                    'mutation_kind': 'set',
                    'content': next_by_subject[subject],
                    'source_trace_id': None,
                    'updated_by': ACTOR,
                    'update_reason': UPDATE_REASON,
                    'audit_reason_code': _operation_audit_reason(operation_kinds),
                }
            )
        else:
            subject_updates.append(
                {
                    'subject': subject,
                    'mutation_kind': 'clear',
                    'content': '',
                    'source_trace_id': None,
                    'updated_by': ACTOR,
                    'update_reason': UPDATE_REASON,
                    'audit_reason_code': _operation_audit_reason(operation_kinds),
                }
            )

    try:
        result = apply_subject_updates(subject_updates)
        if result is None or len(result) != len(subject_updates) or any(item is None for item in result):
            raise RuntimeError('canonical_write_failed')
        writes_applied = bool(subject_updates)
    except Exception:
        return {
            'status': 'skipped',
            'reason_code': 'canonical_write_failed',
            'writes_applied': False,
            'applied_count': 0,
            'skipped_count': len([item for item in outcomes if item.get('status') == 'skipped']),
            'failed_count': max(1, len([item for item in outcomes if item.get('status') == 'failed'])),
            'outcomes': outcomes,
            'subjects_touched': sorted({subject for subject, content in next_by_subject.items() if content != current_by_subject.get(subject, '')}),
            'operation_kinds': sorted({operation for values in operations_by_subject.values() for operation in values}),
            'audit_storage': 'identity_mutable_audit',
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
        'operation_kinds': sorted({str(item.get('operation') or '') for item in outcomes if item.get('operation')}),
        'audit_storage': 'identity_mutable_audit',
    }
