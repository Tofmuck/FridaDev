from __future__ import annotations

import hashlib
from typing import Any

from observability.memory_arbiter_reason_codes import compact_arbiter_reason_observability


def _text(value: Any) -> str:
    return str(value or '').strip()


def _sha256_12(value: Any) -> str:
    text = _text(value)
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def compact_arbiter_decision_item(item: Any) -> dict[str, Any]:
    payload = item if isinstance(item, dict) else {}
    candidate_content = _text(payload.get('candidate_content'))
    reason = _text(payload.get('reason'))
    return {
        'id': _text(payload.get('id')),
        'conversation_id': _text(payload.get('conversation_id')),
        'candidate_id': _text(payload.get('candidate_id')),
        'candidate_role': payload.get('candidate_role'),
        'candidate_ts': payload.get('candidate_ts'),
        'candidate_score': payload.get('candidate_score'),
        'candidate_content_chars': len(candidate_content),
        'candidate_content_sha256_12': _sha256_12(candidate_content),
        'keep': bool(payload.get('keep')),
        'semantic_relevance': payload.get('semantic_relevance'),
        'contextual_gain': payload.get('contextual_gain'),
        'redundant_with_recent': bool(payload.get('redundant_with_recent')),
        **compact_arbiter_reason_observability(reason),
        'model': payload.get('model'),
        'decision_source': payload.get('decision_source'),
        'created_ts': payload.get('created_ts'),
    }


def compact_arbiter_decision_items(items: Any) -> list[dict[str, Any]]:
    return [compact_arbiter_decision_item(item) for item in (items if isinstance(items, list) else [])]
