from __future__ import annotations

import re
from typing import Any, Callable, Mapping, Sequence

import config
from identity import mutable_identity_validation


_ALLOWED_SUBJECTS = ('llm', 'user')
_ALLOWED_OPERATION_KINDS = {'no_change', 'add', 'tighten', 'merge', 'raise_conflict'}
_SENTENCE_SPLIT_RE = re.compile(r'\n+|(?<=[.!?])\s+')
_UPDATED_BY = 'identity_periodic_agent'


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _split_propositions(text: str) -> list[str]:
    cleaned = _text(text)
    if not cleaned:
        return []
    parts = [_text(part) for part in _SENTENCE_SPLIT_RE.split(cleaned)]
    return [part for part in parts if part]


def _norm(value: Any) -> str:
    return re.sub(r'\s+', ' ', _text(value)).lower()


def _validate_meta(meta: Any, *, buffer_pairs_count: int, target_pairs: int) -> tuple[dict[str, Any] | None, str | None]:
    payload = _mapping(meta)
    if set(payload.keys()) != {'execution_status', 'buffer_pairs_count', 'window_complete'}:
        return None, 'contract_meta_keys_invalid'
    if _text(payload.get('execution_status')).lower() != 'complete':
        return None, 'contract_execution_status_invalid'
    if payload.get('window_complete') is not True:
        return None, 'contract_window_complete_invalid'
    try:
        reported_count = int(payload.get('buffer_pairs_count'))
    except (TypeError, ValueError):
        return None, 'contract_buffer_pairs_count_invalid'
    if reported_count != int(buffer_pairs_count) or reported_count < int(target_pairs):
        return None, 'contract_buffer_pairs_count_mismatch'
    return {
        'execution_status': 'complete',
        'buffer_pairs_count': reported_count,
        'window_complete': True,
    }, None


def _validate_operation(value: Any) -> tuple[dict[str, Any] | None, str | None]:
    payload = _mapping(value)
    kind = _text(payload.get('kind')).lower()
    if kind not in _ALLOWED_OPERATION_KINDS:
        return None, 'contract_operation_kind_invalid'
    proposition = _text(payload.get('proposition'))
    reason = _text(payload.get('reason'))
    if not reason:
        return None, 'contract_operation_reason_missing'
    if kind == 'no_change':
        if set(payload.keys()) != {'kind', 'proposition', 'reason'}:
            return None, 'contract_no_change_keys_invalid'
        if proposition:
            return None, 'contract_no_change_proposition_not_empty'
        return {
            'kind': kind,
            'proposition': '',
            'reason': reason,
        }, None
    if kind in {'add', 'raise_conflict'}:
        if set(payload.keys()) != {'kind', 'proposition', 'reason'}:
            return None, 'contract_operation_keys_invalid'
        if not proposition:
            return None, 'contract_operation_proposition_missing'
        return {
            'kind': kind,
            'proposition': proposition,
            'reason': reason,
        }, None
    if kind == 'tighten':
        if set(payload.keys()) != {'kind', 'target', 'proposition', 'reason'}:
            return None, 'contract_tighten_keys_invalid'
        target = _text(payload.get('target'))
        if not proposition or not target:
            return None, 'contract_tighten_target_missing'
        return {
            'kind': kind,
            'target': target,
            'proposition': proposition,
            'reason': reason,
        }, None
    if set(payload.keys()) != {'kind', 'targets', 'proposition', 'reason'}:
        return None, 'contract_merge_keys_invalid'
    targets = payload.get('targets')
    if not isinstance(targets, Sequence) or isinstance(targets, (str, bytes, bytearray)):
        return None, 'contract_merge_targets_invalid'
    normalized_targets = [_text(item) for item in list(targets)]
    normalized_targets = [item for item in normalized_targets if item]
    if len(normalized_targets) < 2 or not proposition:
        return None, 'contract_merge_targets_invalid'
    if len({_norm(item) for item in normalized_targets}) != len(normalized_targets):
        return None, 'contract_merge_targets_duplicated'
    return {
        'kind': kind,
        'targets': normalized_targets,
        'proposition': proposition,
        'reason': reason,
    }, None


def validate_periodic_agent_contract(
    payload: Any,
    *,
    buffer_pairs_count: int,
    target_pairs: int,
) -> tuple[dict[str, Any] | None, str | None]:
    contract = _mapping(payload)
    if set(contract.keys()) != {'llm', 'user', 'meta'}:
        return None, 'contract_top_level_keys_invalid'

    validated: dict[str, Any] = {}
    for subject in _ALLOWED_SUBJECTS:
        subject_block = _mapping(contract.get(subject))
        if set(subject_block.keys()) != {'operations'}:
            return None, f'contract_{subject}_keys_invalid'
        operations = subject_block.get('operations')
        if not isinstance(operations, Sequence) or isinstance(operations, (str, bytes, bytearray)):
            return None, f'contract_{subject}_operations_invalid'
        validated_operations: list[dict[str, Any]] = []
        for item in list(operations):
            validated_operation, reason_code = _validate_operation(item)
            if validated_operation is None:
                return None, reason_code
            validated_operations.append(validated_operation)
        if not validated_operations:
            validated_operations = [{'kind': 'no_change', 'proposition': '', 'reason': 'no operations'}]
        if any(op['kind'] == 'no_change' for op in validated_operations) and len(validated_operations) > 1:
            return None, f'contract_{subject}_no_change_mixed'
        validated[subject] = {'operations': validated_operations}

    validated_meta, meta_reason = _validate_meta(
        contract.get('meta'),
        buffer_pairs_count=buffer_pairs_count,
        target_pairs=target_pairs,
    )
    if validated_meta is None:
        return None, meta_reason
    validated['meta'] = validated_meta
    return validated, None


def _joined_content(lines: Sequence[str]) -> str:
    return '\n'.join(_text(line) for line in lines if _text(line))


def _find_unique_index(lines: Sequence[str], target: str) -> int | None:
    target_norm = _norm(target)
    matches = [index for index, line in enumerate(lines) if _norm(line) == target_norm]
    if len(matches) != 1:
        return None
    return matches[0]


def _validation_reason_for_text(text: str) -> str | None:
    validation = mutable_identity_validation.validate_mutable_identity_content(text)
    if validation.ok:
        return None
    return validation.reason_code


def _subject_outcome(*, subject: str, action: str, reason_code: str, old_len: int, new_len: int) -> dict[str, Any]:
    return {
        'subject': subject,
        'action': action,
        'reason_code': reason_code,
        'old_len': old_len,
        'new_len': new_len,
    }


def _apply_subject_operations(
    *,
    subject: str,
    operations: Sequence[Mapping[str, Any]],
    static_content: str,
    current_content: str,
) -> tuple[str, list[dict[str, Any]], str | None]:
    original_lines = _split_propositions(current_content)
    next_lines = list(original_lines)
    static_norms = {_norm(item) for item in _split_propositions(static_content)}
    outcomes: list[dict[str, Any]] = []

    for operation in operations:
        kind = str(operation['kind'])
        proposition = _text(operation.get('proposition'))
        proposition_norm = _norm(proposition)
        current_norms = {_norm(item) for item in next_lines}
        if kind == 'no_change':
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='no_change',
                    old_len=len(current_content),
                    new_len=len(current_content),
                )
            )
            continue
        if kind == 'raise_conflict':
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='raise_conflict',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        if proposition_norm in static_norms:
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='covered_by_static',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        if kind == 'add':
            if proposition_norm in current_norms:
                outcomes.append(
                    _subject_outcome(
                        subject=subject,
                        action='no_change',
                        reason_code='already_present',
                        old_len=len(current_content),
                        new_len=len(_joined_content(next_lines)),
                    )
                )
                continue
            next_lines.append(proposition)
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='rewrite',
                    reason_code='add_applied',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        if kind == 'tighten':
            target_index = _find_unique_index(next_lines, str(operation['target']))
            if target_index is None:
                outcomes.append(
                    _subject_outcome(
                        subject=subject,
                        action='no_change',
                        reason_code='tighten_target_missing',
                        old_len=len(current_content),
                        new_len=len(_joined_content(next_lines)),
                    )
                )
                continue
            target_norm = _norm(next_lines[target_index])
            if proposition_norm != target_norm and proposition_norm in current_norms:
                outcomes.append(
                    _subject_outcome(
                        subject=subject,
                        action='no_change',
                        reason_code='tighten_duplicate',
                        old_len=len(current_content),
                        new_len=len(_joined_content(next_lines)),
                    )
                )
                continue
            next_lines[target_index] = proposition
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='rewrite',
                    reason_code='tighten_applied',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        target_indexes: list[int] = []
        for target in operation['targets']:
            found_index = _find_unique_index(next_lines, target)
            if found_index is None:
                target_indexes = []
                break
            target_indexes.append(found_index)
        if len(target_indexes) < 2:
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='merge_targets_missing',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        unique_target_indexes = sorted(set(target_indexes))
        if len(unique_target_indexes) < 2:
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='merge_targets_missing',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        if proposition_norm not in {_norm(next_lines[index]) for index in unique_target_indexes} and proposition_norm in current_norms:
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='merge_duplicate',
                    old_len=len(current_content),
                    new_len=len(_joined_content(next_lines)),
                )
            )
            continue
        merged_lines = [line for index, line in enumerate(next_lines) if index not in unique_target_indexes]
        insert_at = unique_target_indexes[0]
        merged_lines.insert(insert_at, proposition)
        next_lines = merged_lines
        outcomes.append(
            _subject_outcome(
                subject=subject,
                action='rewrite',
                reason_code='merge_applied',
                old_len=len(current_content),
                new_len=len(_joined_content(next_lines)),
            )
        )

    next_content = _joined_content(next_lines)
    validation_reason = _validation_reason_for_text(next_content)
    if validation_reason:
        return current_content, [
            _subject_outcome(
                subject=subject,
                action='no_change',
                reason_code=validation_reason,
                old_len=len(current_content),
                new_len=len(current_content),
            )
        ], validation_reason
    if len(next_content) > int(config.IDENTITY_MUTABLE_MAX_CHARS):
        return current_content, [
            _subject_outcome(
                subject=subject,
                action='no_change',
                reason_code='mutable_content_too_long',
                old_len=len(current_content),
                new_len=len(current_content),
            )
        ], 'mutable_content_too_long'
    return next_content, outcomes, None


def apply_periodic_agent_contract(
    contract: Mapping[str, Any],
    *,
    memory_store_module: Any,
    load_llm_identity_fn: Callable[[], str],
    load_user_identity_fn: Callable[[], str],
) -> dict[str, Any]:
    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    upsert_mutable_identity = getattr(memory_store_module, 'upsert_mutable_identity', None)
    if not callable(get_mutable_identity) or not callable(upsert_mutable_identity):
        return {
            'status': 'skipped',
            'reason_code': 'mutable_store_unavailable',
            'outcomes': [],
            'writes_applied': False,
        }

    static_by_subject = {
        'llm': _text(load_llm_identity_fn()),
        'user': _text(load_user_identity_fn()),
    }
    current_by_subject = {
        subject: _text(_mapping(get_mutable_identity(subject)).get('content'))
        for subject in _ALLOWED_SUBJECTS
    }
    next_by_subject = dict(current_by_subject)
    all_outcomes: list[dict[str, Any]] = []
    writes_applied = False

    for subject in _ALLOWED_SUBJECTS:
        next_content, outcomes, rejection_reason = _apply_subject_operations(
            subject=subject,
            operations=list(_mapping(contract.get(subject)).get('operations') or []),
            static_content=static_by_subject[subject],
            current_content=current_by_subject[subject],
        )
        all_outcomes.extend(outcomes)
        if rejection_reason:
            next_by_subject[subject] = current_by_subject[subject]
            continue
        next_by_subject[subject] = next_content

    for subject in _ALLOWED_SUBJECTS:
        if next_by_subject[subject] == current_by_subject[subject]:
            continue
        upsert_mutable_identity(
            subject,
            next_by_subject[subject],
            updated_by=_UPDATED_BY,
            update_reason='periodic_agent',
        )
        writes_applied = True

    return {
        'status': 'ok',
        'reason_code': 'applied' if writes_applied else 'completed_no_change',
        'outcomes': all_outcomes,
        'writes_applied': writes_applied,
    }
