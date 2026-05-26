from __future__ import annotations

import re
from typing import Any, Sequence


_ALLOWED_SUBJECTS = {'llm', 'user'}
_REF_RE = re.compile(r'^(llm|user)_(\d{2})$')
_SENTENCE_SPLIT_RE = re.compile(r'\n+|(?<=[.!?])\s+')


def text(value: Any) -> str:
    return str(value or '').strip()


def split_propositions(content: str) -> list[str]:
    cleaned = text(content)
    if not cleaned:
        return []
    return [item for item in (text(part) for part in _SENTENCE_SPLIT_RE.split(cleaned)) if item]


def proposition_ref(subject: str, index: int) -> str:
    normalized_subject = text(subject).lower()
    if normalized_subject not in _ALLOWED_SUBJECTS:
        return ''
    return f'{normalized_subject}_{index + 1:02d}'


def build_proposition_refs(subject: str, content: str) -> list[dict[str, str]]:
    return [
        {
            'ref': proposition_ref(subject, index),
            'text': line,
        }
        for index, line in enumerate(split_propositions(content))
    ]


def resolve_ref_index(*, subject: str, ref: str, lines: Sequence[str]) -> tuple[int | None, str]:
    normalized_subject = text(subject).lower()
    normalized_ref = text(ref).lower()
    match = _REF_RE.fullmatch(normalized_ref)
    if normalized_subject not in _ALLOWED_SUBJECTS or match is None or match.group(1) != normalized_subject:
        return None, 'target_ref_invalid'
    index = int(match.group(2)) - 1
    if index < 0 or index >= len(lines):
        return None, 'target_not_found'
    return index, ''
