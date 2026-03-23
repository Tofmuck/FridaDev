from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple


NEGATION_HINTS = {
    'ne',
    'not',
    "don't",
    "doesn't",
    'jamais',
    'aucun',
    'sans',
    'plus',
    'pas',
}


@dataclass
class EvidenceEvent:
    conversation_id: str
    created_ts: datetime
    confidence: float
    utterance_mode: str


def _tokenize(text: str) -> List[str]:
    return [tok for tok in re.findall(r"[a-zA-ZÀ-ÿ0-9']+", (text or '').lower()) if len(tok) > 2]


def lexical_contradiction_score(text_a: str, text_b: str) -> float:
    a = (text_a or '').lower().strip()
    b = (text_b or '').lower().strip()
    if not a or not b:
        return 0.0

    tokens_a = set(_tokenize(a))
    tokens_b = set(_tokenize(b))
    overlap = tokens_a & tokens_b
    if not overlap:
        return 0.0

    overlap_ratio = len(overlap) / max(1, min(len(tokens_a), len(tokens_b)))

    neg_a = any(h in a for h in NEGATION_HINTS)
    neg_b = any(h in b for h in NEGATION_HINTS)
    opposite_negation = neg_a ^ neg_b

    cue_score = 0.0
    if opposite_negation:
        cue_score = max(cue_score, 0.75)

    polarity_pairs = [
        ('aime', "n'aime"),
        ('prefere', 'deteste'),
        ('likes', 'dislikes'),
        ('want', "don't want"),
    ]
    for left, right in polarity_pairs:
        if (left in a and right in b) or (left in b and right in a):
            cue_score = max(cue_score, 0.8)

    if cue_score == 0.0:
        return 0.0

    return max(0.0, min(1.0, cue_score + (0.2 * overlap_ratio)))


def is_contradictory(
    text_a: str,
    text_b: str,
    semantic_similarity: Optional[float] = None,
) -> Tuple[bool, float, str]:
    lexical = lexical_contradiction_score(text_a, text_b)
    semantic = max(0.0, min(1.0, semantic_similarity or 0.0))

    if semantic_similarity is None:
        confidence = lexical
    else:
        confidence = max(lexical, (0.7 * lexical) + (0.3 * semantic))

    contradictory = (lexical >= 0.75) or (lexical >= 0.55 and semantic >= 0.4)
    reason = f'lexical={lexical:.3f};semantic={semantic:.3f}'
    return contradictory, max(0.0, min(1.0, confidence)), reason


def decide_identity_status(
    entry: Mapping[str, Any],
    *,
    min_confidence: float,
    defer_min_confidence: float,
) -> Tuple[str, str]:
    confidence = float(entry.get('confidence') or 0.0)
    stability = str(entry.get('stability') or 'unknown')
    recurrence = str(entry.get('recurrence') or 'unknown')
    scope = str(entry.get('scope') or 'unknown')
    utterance_mode = str(entry.get('utterance_mode') or 'unknown')

    if utterance_mode in {'irony', 'role_play'}:
        return 'rejected', f'utterance_mode={utterance_mode}'

    if confidence < defer_min_confidence:
        return 'rejected', f'confidence<{defer_min_confidence:.2f}'

    if stability == 'durable' and recurrence == 'first_seen':
        return 'deferred', 'durable_first_seen'

    if scope == 'mixed':
        return 'deferred', 'mixed_scope'

    if confidence < min_confidence:
        return 'deferred', f'confidence<{min_confidence:.2f}'

    return 'accepted', 'confidence_and_form_ok'


def should_accept_identity(
    entry: Mapping[str, Any],
    history: Optional[Sequence[EvidenceEvent]] = None,
    *,
    min_confidence: float,
    defer_min_confidence: float,
) -> Dict[str, str]:
    status, reason = decide_identity_status(
        entry,
        min_confidence=min_confidence,
        defer_min_confidence=defer_min_confidence,
    )

    if status == 'accepted' and history and str(entry.get('stability') or 'unknown') == 'durable':
        stats = compute_recurrence_stats(history, min_time_gap_hours=0)
        if int(stats.get('selected_count') or 0) <= 1:
            status = 'deferred'
            reason = 'durable_requires_more_evidence'

    return {'status': status, 'reason': reason}


def build_evidence_events(rows: Iterable[Mapping[str, Any]]) -> List[EvidenceEvent]:
    events: List[EvidenceEvent] = []
    for row in rows:
        ts = row.get('created_ts')
        if not isinstance(ts, datetime):
            continue
        events.append(
            EvidenceEvent(
                conversation_id=str(row.get('conversation_id') or ''),
                created_ts=ts,
                confidence=float(row.get('confidence') or 0.0),
                utterance_mode=str(row.get('utterance_mode') or 'unknown'),
            )
        )
    events.sort(key=lambda e: e.created_ts)
    return events


def compute_recurrence_stats(
    events: Sequence[EvidenceEvent],
    *,
    min_time_gap_hours: int,
) -> Dict[str, Any]:
    selected: List[EvidenceEvent] = []
    seen_conversations: set[str] = set()
    min_gap = timedelta(hours=max(0, min_time_gap_hours))

    for event in events:
        conv = event.conversation_id or f'__missing__{event.created_ts.isoformat()}'
        if conv in seen_conversations:
            continue
        if selected and (event.created_ts - selected[-1].created_ts) < min_gap:
            continue
        seen_conversations.add(conv)
        selected.append(event)

    avg_conf = (
        sum(e.confidence for e in selected) / len(selected)
        if selected
        else 0.0
    )
    return {
        'selected_count': len(selected),
        'distinct_conversations': len(seen_conversations),
        'avg_confidence': avg_conf,
        'latest_ts': selected[-1].created_ts if selected else None,
    }


def should_promote_deferred(
    *,
    stats: Mapping[str, Any],
    min_recurrence_for_durable: int,
    min_distinct_conversations: int,
    min_confidence: float,
    has_strong_conflict: bool,
) -> bool:
    if has_strong_conflict:
        return False
    return (
        int(stats.get('selected_count') or 0) >= max(1, min_recurrence_for_durable)
        and int(stats.get('distinct_conversations') or 0) >= max(1, min_distinct_conversations)
        and float(stats.get('avg_confidence') or 0.0) >= min_confidence
    )


def should_reject_deferred_from_evidence(events: Sequence[EvidenceEvent]) -> bool:
    if not events:
        return False
    latest = events[-1]
    return latest.utterance_mode in {'irony', 'role_play'}


def conflict_resolution_action(confidence_conflict: float) -> str:
    if confidence_conflict >= 0.8:
        return 'defer_older'
    if confidence_conflict >= 0.6:
        return 'downweight_both'
    return 'ignore'
