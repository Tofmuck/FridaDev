from __future__ import annotations

import re
from typing import Any, Mapping


KNOWN_SUBJECT_NAMES = {
    'llm': {'Frida'},
    'user': {'Tof', 'Amandine'},
}
DEFAULT_ACTIVE_SUBJECT_NAMES = {
    'llm': {'Frida'},
    'user': {'Tof'},
}

ONTOLOGICAL_PROPOSITION_RE = re.compile(
    r'^(?P<name>[A-ZÀ-ÖØ-Þ][A-Za-zÀ-ÖØ-öø-ÿ-]{1,60})\s+'
    r'(?P<verb>est|tient|refuse|reconna(?:i|î)t|traite|exige)\b.+\.$'
)


def _text(value: Any) -> str:
    if value is None:
        return ''
    return str(value).strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _contains_name(text: str, name: str) -> bool:
    if not text or not name:
        return False
    return re.search(rf'(?<!\w){re.escape(name)}(?!\w)', text) is not None


def _subject_identity_texts(source: Mapping[str, Any], subject: str) -> list[str]:
    payload = _mapping(source.get(subject))
    return [
        _text(payload.get('static')),
        _text(payload.get('mutable_current')),
    ]


def active_identity_names_by_subject(
    *,
    subjects: set[str],
    identities: Mapping[str, Any] | None = None,
    static_identity_by_subject: Mapping[str, Any] | None = None,
) -> dict[str, set[str]]:
    identity_source = _mapping(identities or {})
    static_source = _mapping(static_identity_by_subject or {})
    names_by_subject: dict[str, set[str]] = {}
    for subject in sorted(subjects):
        texts = _subject_identity_texts(identity_source, subject)
        texts.append(_text(static_source.get(subject)))
        detected = {
            name
            for name in KNOWN_SUBJECT_NAMES.get(subject, set())
            if any(_contains_name(text, name) for text in texts)
        }
        names_by_subject[subject] = detected or set(DEFAULT_ACTIVE_SUBJECT_NAMES.get(subject, set()))
    return names_by_subject
