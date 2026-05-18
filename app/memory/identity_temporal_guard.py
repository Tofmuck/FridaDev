from __future__ import annotations

import re
from typing import Any, Mapping, Sequence


WEAK_RELATIVE_TEMPORAL_IDENTITY_MARKERS = (
    "aujourd'hui",
    'aujourdhui',
    'hier',
    'depuis hier',
    'en ce moment',
    'actuellement',
    'maintenant',
    'today',
    'yesterday',
    'since yesterday',
    'right now',
    'currently',
)


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _normalized(value: Any) -> str:
    return re.sub(r'\s+', ' ', _text(value).lower().replace('’', "'"))


def has_weak_relative_temporal_marker(value: Any) -> bool:
    normalized = _normalized(value)
    return any(
        re.search(rf'(?<![\w]){re.escape(marker)}(?![\w])', normalized)
        for marker in WEAK_RELATIVE_TEMPORAL_IDENTITY_MARKERS
    )


def _subject_for_role(role: Any) -> str:
    role_value = _text(role).lower()
    if role_value == 'user':
        return 'user'
    if role_value in {'assistant', 'llm'}:
        return 'llm'
    return ''


def empty_source_summary() -> dict[str, dict[str, int]]:
    return {
        'llm': {'admissible_source_count': 0, 'weak_relative_source_count': 0},
        'user': {'admissible_source_count': 0, 'weak_relative_source_count': 0},
    }


def _record_source(
    summary: dict[str, dict[str, int]],
    *,
    subject: str,
    content: str,
) -> bool:
    if subject not in summary or not content:
        return False
    if has_weak_relative_temporal_marker(content):
        summary[subject]['weak_relative_source_count'] += 1
        return False
    summary[subject]['admissible_source_count'] += 1
    return True


def admissible_turns_with_source_summary(
    turns: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    summary = empty_source_summary()
    admissible: list[dict[str, Any]] = []
    for turn in list(turns or []):
        payload = dict(turn or {})
        subject = _subject_for_role(payload.get('role'))
        content = _text(payload.get('content'))
        if _record_source(summary, subject=subject, content=content):
            admissible.append(payload)
    return admissible, summary


def sanitized_buffer_pairs_with_source_summary(
    buffer_pairs: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, dict[str, int]]]:
    summary = empty_source_summary()
    sanitized_pairs: list[dict[str, Any]] = []
    for pair in list(buffer_pairs or []):
        pair_payload = _mapping(pair)
        sanitized_pair: dict[str, Any] = {}
        for role_key, subject in (('user', 'user'), ('assistant', 'llm')):
            message = dict(_mapping(pair_payload.get(role_key)))
            content = _text(message.get('content'))
            if _record_source(summary, subject=subject, content=content):
                sanitized_pair[role_key] = message
                continue
            if content:
                message['content'] = ''
                message['temporal_source_guard'] = 'weak_relative_temporal_claim_removed'
            sanitized_pair[role_key] = message
        sanitized_pairs.append(sanitized_pair)
    return sanitized_pairs, summary


def subject_has_admissible_source(
    source_summary: Mapping[str, Any] | None,
    subject: str,
) -> bool:
    if not isinstance(source_summary, Mapping):
        return True
    subject_summary = _mapping(source_summary.get(subject))
    try:
        return int(subject_summary.get('admissible_source_count') or 0) > 0
    except (TypeError, ValueError):
        return False


def rejection_reason_for_subject(
    source_summary: Mapping[str, Any] | None,
    subject: str,
) -> str:
    subject_summary = _mapping((source_summary or {}).get(subject))
    try:
        weak_count = int(subject_summary.get('weak_relative_source_count') or 0)
    except (TypeError, ValueError):
        weak_count = 0
    if weak_count > 0:
        return 'weak relative temporal identity source rejected'
    return 'identity source missing'
