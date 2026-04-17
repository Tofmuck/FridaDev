from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Any, Callable, Mapping, Sequence

import config
from identity import mutable_identity_validation
from memory import memory_identity_periodic_scoring


_ALLOWED_SUBJECTS = ('llm', 'user')
_ALLOWED_OPERATION_KINDS = {'no_change', 'add', 'tighten', 'merge', 'raise_conflict'}
_SENTENCE_SPLIT_RE = re.compile(r'\n+|(?<=[.!?])\s+')
_UPDATED_BY = 'identity_periodic_agent'
_PROMOTION_UPDATE_REASON = 'periodic_agent_promotion'
_STATIC_TARGET_CHARS = 3000
_RECENT_ADMIN_GUARD_HOURS = 24


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


def _parse_ts(value: Any) -> datetime | None:
    raw = _text(value)
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_recent_admin_mutable_update(current_item: Mapping[str, Any]) -> bool:
    if _text(current_item.get('updated_by')) != 'admin_identity_mutable_edit':
        return False
    updated_ts = _parse_ts(current_item.get('updated_ts') or current_item.get('created_ts'))
    if updated_ts is None:
        return False
    return updated_ts >= (datetime.now(timezone.utc) - timedelta(hours=_RECENT_ADMIN_GUARD_HOURS))


def _is_recent_static_operator_edit(static_snapshot: Mapping[str, Any]) -> bool:
    if _text(static_snapshot.get('updated_by')) != 'admin_identity_static_edit':
        return False
    updated_ts = _parse_ts(static_snapshot.get('updated_ts'))
    if updated_ts is None:
        return False
    return updated_ts >= (datetime.now(timezone.utc) - timedelta(hours=_RECENT_ADMIN_GUARD_HOURS))


def _subject_outcome(
    *,
    subject: str,
    action: str,
    reason_code: str,
    old_len: int,
    new_len: int,
    **extra: Any,
) -> dict[str, Any]:
    payload = {
        'subject': subject,
        'action': action,
        'reason_code': reason_code,
        'old_len': old_len,
        'new_len': new_len,
    }
    payload.update(extra)
    return payload


def _score_fields(score: Mapping[str, Any], *, operation_kind: str) -> dict[str, Any]:
    verdict = _text(score.get('threshold_verdict')) or 'not_scored'
    return {
        'operation_kind': operation_kind,
        'threshold_verdict': verdict,
        'support_pairs': int(score.get('support_pairs') or 0),
        'last_occurrence_distance': int(score.get('last_occurrence_distance') or 0),
        'frequency_norm': float(score.get('frequency_norm') or 0.0),
        'recency_norm': float(score.get('recency_norm') or 0.0),
        'strength': float(score.get('strength') or 0.0),
    }


def _abort_success_outcomes_for_all_or_nothing(
    outcomes: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    aborted: list[dict[str, Any]] = []
    for outcome in outcomes:
        payload = _mapping(outcome)
        subject = _text(payload.get('subject'))
        action = _text(payload.get('action')) or 'no_change'
        reason_code = _text(payload.get('reason_code'))
        old_len = int(payload.get('old_len') or 0)
        extra = {
            key: value
            for key, value in payload.items()
            if key not in {'subject', 'action', 'reason_code', 'old_len', 'new_len'}
        }
        if action == 'rewrite' or reason_code.endswith('_applied'):
            aborted.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='not_committed_due_to_peer_rejection',
                    old_len=old_len,
                    new_len=old_len,
                    **extra,
                )
            )
            continue
        aborted.append(
            _subject_outcome(
                subject=subject,
                action=action,
                reason_code=reason_code or 'no_change',
                old_len=old_len,
                new_len=int(payload.get('new_len') or old_len),
                **extra,
            )
        )
    return aborted


def _build_static_snapshot(
    subject: str,
    *,
    read_static_identity_snapshot_fn: Callable[[str], Any] | None,
    load_static_identity_fn: Callable[[], str],
) -> dict[str, Any]:
    if callable(read_static_identity_snapshot_fn):
        try:
            snapshot = read_static_identity_snapshot_fn(subject)
        except Exception:
            snapshot = None
        if snapshot is not None:
            content = _text(getattr(snapshot, 'content', ''))
            raw_content = str(getattr(snapshot, 'raw_content', content))
            return {
                'content': content,
                'raw_content': raw_content,
                'resolved_path': getattr(snapshot, 'resolved_path', None),
                'updated_by': _text(getattr(snapshot, 'updated_by', '')),
                'update_reason': _text(getattr(snapshot, 'update_reason', '')),
                'updated_ts': _text(getattr(snapshot, 'updated_ts', '')),
            }
    content = _text(load_static_identity_fn())
    return {
        'content': content,
        'raw_content': content,
        'resolved_path': None,
        'updated_by': '',
        'update_reason': '',
        'updated_ts': '',
    }


def _evaluate_subject_operations(
    *,
    subject: str,
    operations: Sequence[Mapping[str, Any]],
    buffer_pairs: Sequence[Mapping[str, Any]],
    current_item: Mapping[str, Any],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    accepted: list[dict[str, Any]] = []
    outcomes: list[dict[str, Any]] = []
    rejection_reason: str | None = None
    mutable_guard_active = _is_recent_admin_mutable_update(current_item)
    current_content = _text(current_item.get('content'))

    for operation in operations:
        payload = dict(_mapping(operation))
        kind = _text(payload.get('kind')).lower()
        score = memory_identity_periodic_scoring.score_operation(
            payload,
            buffer_pairs=buffer_pairs,
        )
        score_fields = _score_fields(score, operation_kind=kind)
        verdict = _text(score.get('threshold_verdict')) or 'not_scored'

        if kind == 'no_change':
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='no_change',
                    old_len=len(current_content),
                    new_len=len(current_content),
                    **score_fields,
                )
            )
            continue

        if kind == 'raise_conflict':
            reason_code = 'strength_below_threshold' if verdict == 'rejected' else 'raise_conflict_open'
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code=reason_code,
                    old_len=len(current_content),
                    new_len=len(current_content),
                    **score_fields,
                )
            )
            continue

        if mutable_guard_active and kind in {'tighten', 'merge'}:
            rejection_reason = 'recent_admin_mutable_guard'
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='recent_admin_mutable_guard',
                    old_len=len(current_content),
                    new_len=len(current_content),
                    **score_fields,
                )
            )
            continue

        if verdict == 'rejected':
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='strength_below_threshold',
                    old_len=len(current_content),
                    new_len=len(current_content),
                    **score_fields,
                )
            )
            continue

        if verdict == 'deferred':
            outcomes.append(
                _subject_outcome(
                    subject=subject,
                    action='no_change',
                    reason_code='strength_deferred',
                    old_len=len(current_content),
                    new_len=len(current_content),
                    **score_fields,
                )
            )
            continue

        payload['score'] = dict(score_fields)
        accepted.append(payload)

    return accepted, outcomes, rejection_reason


def _candidate_sort_key(candidate: Mapping[str, Any]) -> tuple[float, int, float, int]:
    return (
        -float(candidate.get('strength') or 0.0),
        -int(candidate.get('support_pairs') or 0),
        -float(candidate.get('recency_norm') or 0.0),
        -len(_text(candidate.get('proposition'))),
    )


def _plan_subject_promotion(
    *,
    subject: str,
    current_mutable_content: str,
    next_mutable_content: str,
    static_snapshot: Mapping[str, Any],
    accepted_operations: Sequence[Mapping[str, Any]],
) -> tuple[str, str, list[dict[str, Any]], str | None, bool]:
    mutable_target_chars = int(config.IDENTITY_MUTABLE_TARGET_CHARS)
    static_content = _text(static_snapshot.get('content'))
    if len(next_mutable_content) <= mutable_target_chars:
        return next_mutable_content, static_content, [], None, False

    if _is_recent_static_operator_edit(static_snapshot):
        return next_mutable_content, static_content, [], 'static_recent_operator_edit_guard', True

    next_mutable_lines = _split_propositions(next_mutable_content)
    promoted_mutable_lines = list(next_mutable_lines)
    promoted_static_lines = _split_propositions(static_content)
    static_norms = {_norm(item) for item in promoted_static_lines}
    candidates: list[dict[str, Any]] = []

    for operation in accepted_operations:
        kind = _text(operation.get('kind')).lower()
        if kind not in {'add', 'tighten', 'merge'}:
            continue
        proposition = _text(operation.get('proposition'))
        if not proposition:
            continue
        line_index = _find_unique_index(promoted_mutable_lines, proposition)
        if line_index is None:
            continue
        score_payload = _mapping(operation.get('score'))
        candidates.append(
            {
                'subject': subject,
                'operation_kind': kind,
                'proposition': proposition,
                'line_index': line_index,
                **_score_fields(score_payload, operation_kind=kind),
            }
        )

    if not candidates:
        return next_mutable_content, static_content, [], 'mutable_saturated_no_promotion_candidate', False

    promotions: list[dict[str, Any]] = []
    for candidate in sorted(candidates, key=_candidate_sort_key):
        current_promoted_mutable = _joined_content(promoted_mutable_lines)
        if len(current_promoted_mutable) <= mutable_target_chars:
            break
        proposition = _text(candidate.get('proposition'))
        line_index = _find_unique_index(promoted_mutable_lines, proposition)
        if line_index is None:
            continue

        old_mutable_len = len(current_promoted_mutable)
        old_static_len = len(_joined_content(promoted_static_lines))
        proposition_norm = _norm(proposition)
        if proposition_norm in static_norms:
            promoted_mutable_lines.pop(line_index)
            promotions.append(
                {
                    'subject': subject,
                    'operation_kind': _text(candidate.get('operation_kind')),
                    'promotion_reason_code': 'deduplicated_with_static',
                    'mutable_old_len': old_mutable_len,
                    'mutable_new_len': len(_joined_content(promoted_mutable_lines)),
                    'static_old_len': old_static_len,
                    'static_new_len': old_static_len,
                    **_score_fields(candidate, operation_kind=_text(candidate.get('operation_kind'))),
                }
            )
            continue

        tentative_static_lines = list(promoted_static_lines) + [proposition]
        tentative_static_content = _joined_content(tentative_static_lines)
        if len(tentative_static_content) > _STATIC_TARGET_CHARS:
            return next_mutable_content, static_content, [], 'double_saturation', True

        promoted_mutable_lines.pop(line_index)
        promoted_static_lines.append(proposition)
        static_norms.add(proposition_norm)
        promotions.append(
            {
                'subject': subject,
                'operation_kind': _text(candidate.get('operation_kind')),
                'promotion_reason_code': 'promoted_to_static',
                'mutable_old_len': old_mutable_len,
                'mutable_new_len': len(_joined_content(promoted_mutable_lines)),
                'static_old_len': old_static_len,
                'static_new_len': len(tentative_static_content),
                **_score_fields(candidate, operation_kind=_text(candidate.get('operation_kind'))),
            }
        )

    promoted_mutable_content = _joined_content(promoted_mutable_lines)
    promoted_static_content = _joined_content(promoted_static_lines)
    if len(promoted_mutable_content) > mutable_target_chars:
        rejection_reason = 'double_saturation' if len(promoted_static_content) >= _STATIC_TARGET_CHARS else 'mutable_saturated_unresolved'
        return next_mutable_content, static_content, [], rejection_reason, rejection_reason == 'double_saturation'
    return promoted_mutable_content, promoted_static_content, promotions, None, False


def _restore_mutable_identity(
    *,
    subject: str,
    original_item: Mapping[str, Any],
    upsert_mutable_identity: Callable[..., Any],
    clear_mutable_identity: Callable[[str], Any] | None,
) -> None:
    original_content = _text(original_item.get('content'))
    if original_content:
        upsert_mutable_identity(
            subject,
            original_content,
            source_trace_id=original_item.get('source_trace_id'),
            updated_by=_text(original_item.get('updated_by')) or 'system',
            update_reason=_text(original_item.get('update_reason')),
        )
        return
    if callable(clear_mutable_identity):
        clear_mutable_identity(subject)


def _write_static_identity_content(
    write_static_identity_content_fn: Callable[..., Any] | None,
    *,
    subject: str,
    content: str,
    updated_by: str,
    update_reason: str,
    updated_ts: str | None = None,
) -> None:
    if not callable(write_static_identity_content_fn):
        raise RuntimeError('static_writer_unavailable')
    try:
        write_static_identity_content_fn(
            subject,
            content,
            updated_by=updated_by,
            update_reason=update_reason,
            updated_ts=updated_ts,
        )
    except TypeError as exc:
        if 'unexpected keyword' not in str(exc) and 'positional arguments' not in str(exc):
            raise
        write_static_identity_content_fn(subject, content)


def _apply_canonical_writes_with_rollback(
    *,
    next_static_by_subject: Mapping[str, str],
    current_static_by_subject: Mapping[str, Mapping[str, Any]],
    next_mutable_by_subject: Mapping[str, str],
    current_mutable_by_subject: Mapping[str, Mapping[str, Any]],
    upsert_mutable_identity: Callable[..., Any],
    clear_mutable_identity: Callable[[str], Any] | None,
    write_static_identity_content_fn: Callable[[str, str], Any] | None,
    promoted_subjects: set[str],
) -> bool:
    applied_static_subjects: list[str] = []
    applied_mutable_subjects: list[str] = []
    writes_applied = False
    try:
        for subject in _ALLOWED_SUBJECTS:
            next_static_content = _text(next_static_by_subject.get(subject))
            current_static_content = _text(_mapping(current_static_by_subject.get(subject)).get('content'))
            if next_static_content == current_static_content:
                continue
            _write_static_identity_content(
                write_static_identity_content_fn,
                subject=subject,
                content=next_static_content,
                updated_by=_UPDATED_BY,
                update_reason=_PROMOTION_UPDATE_REASON if subject in promoted_subjects else 'periodic_agent',
            )
            applied_static_subjects.append(subject)
            writes_applied = True

        for subject in _ALLOWED_SUBJECTS:
            current_item = _mapping(current_mutable_by_subject.get(subject))
            current_content = _text(current_item.get('content'))
            next_content = _text(next_mutable_by_subject.get(subject))
            if next_content == current_content:
                continue
            if next_content:
                upsert_mutable_identity(
                    subject,
                    next_content,
                    source_trace_id=current_item.get('source_trace_id'),
                    updated_by=_UPDATED_BY,
                    update_reason=_PROMOTION_UPDATE_REASON if subject in promoted_subjects else 'periodic_agent',
                )
            else:
                if not callable(clear_mutable_identity):
                    raise RuntimeError('clear_mutable_identity_unavailable')
                clear_mutable_identity(subject)
            applied_mutable_subjects.append(subject)
            writes_applied = True
    except Exception:
        for subject in reversed(applied_mutable_subjects):
            _restore_mutable_identity(
                subject=subject,
                original_item=_mapping(current_mutable_by_subject.get(subject)),
                upsert_mutable_identity=upsert_mutable_identity,
                clear_mutable_identity=clear_mutable_identity,
            )
        if callable(write_static_identity_content_fn):
            for subject in reversed(applied_static_subjects):
                original_static = _mapping(current_static_by_subject.get(subject))
                _write_static_identity_content(
                    write_static_identity_content_fn,
                    subject=subject,
                    content=str(original_static.get('raw_content') or original_static.get('content') or ''),
                    updated_by=_text(original_static.get('updated_by')) or 'system',
                    update_reason=_text(original_static.get('update_reason')),
                    updated_ts=_text(original_static.get('updated_ts')) or None,
                )
        raise
    return writes_applied


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
        score_payload = _mapping(operation.get('score'))
        score_fields = _score_fields(score_payload, operation_kind=kind)
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
                    **score_fields,
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
                    **score_fields,
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
                    **score_fields,
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
                        **score_fields,
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
                    **score_fields,
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
                        **score_fields,
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
                        **score_fields,
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
                    **score_fields,
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
                    **score_fields,
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
                    **score_fields,
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
                    **score_fields,
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
                **score_fields,
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
    buffer_pairs: Sequence[Mapping[str, Any]],
    memory_store_module: Any,
    load_llm_identity_fn: Callable[[], str],
    load_user_identity_fn: Callable[[], str],
    read_static_identity_snapshot_fn: Callable[[str], Any] | None = None,
    write_static_identity_content_fn: Callable[[str, str], Any] | None = None,
) -> dict[str, Any]:
    get_mutable_identity = getattr(memory_store_module, 'get_mutable_identity', None)
    upsert_mutable_identity = getattr(memory_store_module, 'upsert_mutable_identity', None)
    clear_mutable_identity = getattr(memory_store_module, 'clear_mutable_identity', None)
    if not callable(get_mutable_identity) or not callable(upsert_mutable_identity):
        return {
            'status': 'skipped',
            'reason_code': 'mutable_store_unavailable',
            'outcomes': [],
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'auto_canonization_suspended': False,
        }

    static_snapshots_by_subject = {
        'llm': _build_static_snapshot(
            'llm',
            read_static_identity_snapshot_fn=read_static_identity_snapshot_fn,
            load_static_identity_fn=load_llm_identity_fn,
        ),
        'user': _build_static_snapshot(
            'user',
            read_static_identity_snapshot_fn=read_static_identity_snapshot_fn,
            load_static_identity_fn=load_user_identity_fn,
        ),
    }
    static_by_subject = {
        subject: _text(_mapping(static_snapshots_by_subject.get(subject)).get('content'))
        for subject in _ALLOWED_SUBJECTS
    }
    current_items_by_subject = {
        subject: _mapping(get_mutable_identity(subject))
        for subject in _ALLOWED_SUBJECTS
    }
    current_by_subject = {
        subject: _text(_mapping(current_items_by_subject.get(subject)).get('content'))
        for subject in _ALLOWED_SUBJECTS
    }
    next_by_subject = dict(current_by_subject)
    next_static_by_subject = dict(static_by_subject)
    all_outcomes: list[dict[str, Any]] = []
    rejection_reasons: dict[str, str] = {}
    accepted_operations_by_subject: dict[str, list[dict[str, Any]]] = {subject: [] for subject in _ALLOWED_SUBJECTS}
    promotions: list[dict[str, Any]] = []
    auto_canonization_suspended = False

    for subject in _ALLOWED_SUBJECTS:
        accepted_operations, gating_outcomes, gating_rejection = _evaluate_subject_operations(
            subject=subject,
            operations=list(_mapping(contract.get(subject)).get('operations') or []),
            buffer_pairs=buffer_pairs,
            current_item=_mapping(current_items_by_subject.get(subject)),
        )
        all_outcomes.extend(gating_outcomes)
        if gating_rejection:
            rejection_reasons[subject] = str(gating_rejection)
            continue

        next_content, outcomes, rejection_reason = _apply_subject_operations(
            subject=subject,
            operations=accepted_operations,
            static_content=static_by_subject[subject],
            current_content=current_by_subject[subject],
        )
        all_outcomes.extend(outcomes)
        if rejection_reason:
            rejection_reasons[subject] = str(rejection_reason)
            continue
        next_by_subject[subject] = next_content
        accepted_operations_by_subject[subject] = list(accepted_operations)

    for subject in _ALLOWED_SUBJECTS:
        if subject in rejection_reasons:
            continue
        promoted_mutable, promoted_static, subject_promotions, rejection_reason, suspended = _plan_subject_promotion(
            subject=subject,
            current_mutable_content=current_by_subject[subject],
            next_mutable_content=next_by_subject[subject],
            static_snapshot=_mapping(static_snapshots_by_subject.get(subject)),
            accepted_operations=accepted_operations_by_subject.get(subject) or [],
        )
        if rejection_reason:
            rejection_reasons[subject] = str(rejection_reason)
            auto_canonization_suspended = auto_canonization_suspended or bool(suspended)
            continue
        next_by_subject[subject] = promoted_mutable
        next_static_by_subject[subject] = promoted_static
        promotions.extend(subject_promotions)

    if rejection_reasons:
        aborted_outcomes = _abort_success_outcomes_for_all_or_nothing(all_outcomes)
        reason_code = 'all_or_nothing_rejected'
        if auto_canonization_suspended:
            reason_code = next(iter(rejection_reasons.values()), 'double_saturation')
        return {
            'status': 'skipped',
            'reason_code': reason_code,
            'rejection_reasons': dict(rejection_reasons),
            'outcomes': aborted_outcomes,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'auto_canonization_suspended': bool(auto_canonization_suspended),
        }

    promoted_subjects = {str(item.get('subject') or '') for item in promotions if str(item.get('subject') or '').strip()}
    try:
        writes_applied = _apply_canonical_writes_with_rollback(
            next_static_by_subject=next_static_by_subject,
            current_static_by_subject=static_snapshots_by_subject,
            next_mutable_by_subject=next_by_subject,
            current_mutable_by_subject=current_items_by_subject,
            upsert_mutable_identity=upsert_mutable_identity,
            clear_mutable_identity=clear_mutable_identity,
            write_static_identity_content_fn=write_static_identity_content_fn,
            promoted_subjects=promoted_subjects,
        )
    except Exception:
        return {
            'status': 'skipped',
            'reason_code': 'canonical_write_failed',
            'outcomes': _abort_success_outcomes_for_all_or_nothing(all_outcomes),
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'auto_canonization_suspended': False,
        }

    return {
        'status': 'ok',
        'reason_code': 'applied' if writes_applied else 'completed_no_change',
        'outcomes': all_outcomes,
        'writes_applied': writes_applied,
        'promotion_count': len(promotions),
        'promotions': promotions,
        'auto_canonization_suspended': False,
    }
