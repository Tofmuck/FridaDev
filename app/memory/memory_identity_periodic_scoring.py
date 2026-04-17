from __future__ import annotations

import math
import re
import unicodedata
from typing import Any, Mapping, Sequence


BUFFER_TARGET_PAIRS = 15
REJECT_THRESHOLD = 0.35
ACCEPT_THRESHOLD = 0.60

_TOKEN_RE = re.compile(r"[a-z0-9']+")
_STOPWORDS = {
    'a',
    'about',
    'alors',
    'and',
    'au',
    'aux',
    'avec',
    'ce',
    'ces',
    'cette',
    'comme',
    'dans',
    'de',
    'des',
    'du',
    'elle',
    'elles',
    'en',
    'est',
    'et',
    'for',
    'frida',
    'he',
    'i',
    'il',
    'ils',
    'je',
    'la',
    'le',
    'les',
    'mais',
    'me',
    'mes',
    'mon',
    'ne',
    'of',
    'on',
    'or',
    'ou',
    'par',
    'pas',
    'plus',
    'pour',
    'que',
    'qui',
    'sa',
    'ses',
    'she',
    'sur',
    'the',
    'their',
    'to',
    'tof',
    'tu',
    'un',
    'une',
    'user',
    'vous',
    'we',
    'with',
}


def _text(value: Any) -> str:
    return str(value or '').strip()


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _normalize_ascii(text: str) -> str:
    normalized = unicodedata.normalize('NFKD', _text(text))
    ascii_text = normalized.encode('ascii', 'ignore').decode('ascii')
    return re.sub(r'\s+', ' ', ascii_text).strip().lower()


def _meaningful_tokens(text: str) -> list[str]:
    raw_tokens = _TOKEN_RE.findall(_normalize_ascii(text))
    filtered = [token for token in raw_tokens if len(token) >= 3 and token not in _STOPWORDS]
    if filtered:
        return filtered
    return [token for token in raw_tokens if len(token) >= 2]


def _candidate_texts(operation: Mapping[str, Any]) -> list[str]:
    payload = _mapping(operation)
    kind = _text(payload.get('kind')).lower()
    texts = [_text(payload.get('proposition'))]
    if kind == 'tighten':
        texts.append(_text(payload.get('target')))
    elif kind == 'merge':
        targets = payload.get('targets')
        if isinstance(targets, Sequence) and not isinstance(targets, (str, bytes, bytearray)):
            texts.extend(_text(item) for item in list(targets))
    return [item for item in texts if item]


def _pair_blob(pair: Mapping[str, Any]) -> str:
    payload = _mapping(pair)
    user = _mapping(payload.get('user'))
    assistant = _mapping(payload.get('assistant'))
    return ' '.join(
        part
        for part in [
            _text(user.get('content')),
            _text(assistant.get('content')),
        ]
        if part
    )


def _pair_supports_candidate(
    *,
    pair_blob_norm: str,
    pair_tokens: set[str],
    candidate_text: str,
) -> bool:
    candidate_norm = _normalize_ascii(candidate_text)
    if candidate_norm and candidate_norm in pair_blob_norm:
        return True

    candidate_tokens = set(_meaningful_tokens(candidate_text))
    if not candidate_tokens:
        return False

    overlap = candidate_tokens.intersection(pair_tokens)
    required_overlap = 1 if len(candidate_tokens) <= 2 else max(2, math.ceil(len(candidate_tokens) * 0.4))
    return len(overlap) >= min(len(candidate_tokens), required_overlap)


def threshold_verdict(strength: float) -> str:
    if strength < REJECT_THRESHOLD:
        return 'rejected'
    if strength < ACCEPT_THRESHOLD:
        return 'deferred'
    return 'accepted'


def score_operation(
    operation: Mapping[str, Any],
    *,
    buffer_pairs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    buffer_size = max(1, int(len(list(buffer_pairs))))
    candidate_texts = _candidate_texts(operation)
    if not candidate_texts:
        return {
            'support_pairs': 0,
            'last_occurrence_distance': buffer_size,
            'frequency_norm': 0.0,
            'recency_norm': 0.0,
            'strength': 0.0,
            'threshold_verdict': 'not_scored',
        }

    support_indexes: list[int] = []
    for index, pair in enumerate(list(buffer_pairs)):
        pair_blob = _pair_blob(_mapping(pair))
        pair_blob_norm = _normalize_ascii(pair_blob)
        pair_tokens = set(_meaningful_tokens(pair_blob))
        if any(
            _pair_supports_candidate(
                pair_blob_norm=pair_blob_norm,
                pair_tokens=pair_tokens,
                candidate_text=text,
            )
            for text in candidate_texts
        ):
            support_indexes.append(index)

    support_pairs = len(support_indexes)
    frequency_norm = support_pairs / float(buffer_size)
    if support_indexes:
        last_occurrence_distance = (buffer_size - 1) - support_indexes[-1]
        recency_norm = 1.0 if buffer_size == 1 else 1 - (last_occurrence_distance / float(buffer_size - 1))
    else:
        last_occurrence_distance = buffer_size
        recency_norm = 0.0
    strength = (0.7 * frequency_norm) + (0.3 * recency_norm)
    return {
        'support_pairs': int(support_pairs),
        'last_occurrence_distance': int(last_occurrence_distance),
        'frequency_norm': round(float(frequency_norm), 4),
        'recency_norm': round(float(recency_norm), 4),
        'strength': round(float(strength), 4),
        'threshold_verdict': threshold_verdict(float(strength)),
    }
