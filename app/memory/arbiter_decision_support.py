from __future__ import annotations

import re
from typing import Any, Dict, List, Tuple


_LEXICAL_TOKEN_RE = re.compile(r"[A-Za-zÀ-ÖØ-öø-ÿ0-9']+")
_LEXICAL_STOPWORDS = {
    'a', 'au', 'aux', 'avec', 'ce', 'ces', 'cette', 'comme', 'dans', 'de', 'des', 'du',
    'elle', 'en', 'et', 'est', 'il', 'ils', 'je', 'la', 'le', 'les', 'leur', 'lui', 'ma',
    'mais', 'me', 'mes', 'mon', 'ne', 'nous', 'on', 'ou', 'par', 'pas', 'pour', 'que', 'qui',
    'se', 'ses', 'son', 'sur', 'ta', 'te', 'tes', 'toi', 'ton', 'tu', 'un', 'une', 'vous',
    'i', 'you', 'he', 'she', 'we', 'they', 'is', 'are', 'was', 'were', 'the', 'this', 'that',
    'to', 'of', 'in', 'on', 'for', 'and', 'or', 'it',
}
_CIRCUMSTANTIAL_MARKERS = (
    'ce soir',
    'ce matin',
    'cet apres-midi',
    'cet après-midi',
    "aujourd'hui",
    "aujourd’hui",
    'hier',
    'demain',
    'maintenant',
    'en ce moment',
    'cette semaine',
    'week-end',
    'weekend',
    'tonight',
    'today',
    'yesterday',
    'tomorrow',
    'right now',
    'this week',
)


def as_float_01(value: Any) -> float:
    resolved = float(value)
    if resolved < 0.0 or resolved > 1.0:
        raise ValueError('value out of [0,1] range')
    return resolved


def trace_retrieval_score(trace: Dict[str, Any]) -> float:
    try:
        value = trace.get('retrieval_score', trace.get('score'))
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def trace_semantic_score(trace: Dict[str, Any]) -> float:
    try:
        if 'semantic_score' in trace:
            return float(trace.get('semantic_score') or 0.0)
        return trace_retrieval_score(trace)
    except (TypeError, ValueError):
        return 0.0


def trace_candidate_id(trace: Dict[str, Any], fallback_index: int) -> str:
    candidate_id = str(trace.get('candidate_id') or '').strip()
    return candidate_id or str(fallback_index)


def trace_timestamp(trace: Dict[str, Any]) -> str:
    return str(trace.get('timestamp_iso') or trace.get('timestamp') or '').strip()


def append_reason(decision: Dict[str, Any], suffix: str) -> None:
    base = str(decision.get('reason') or '').strip()
    decision['reason'] = f'{base} | {suffix}' if base else suffix


def tokenize_lexical(text: str) -> set[str]:
    tokens = {token.lower() for token in _LEXICAL_TOKEN_RE.findall(text or '') if len(token) >= 3}
    return {token for token in tokens if token not in _LEXICAL_STOPWORDS}


def max_lexical_similarity(content: str, recent_turns: List[Dict[str, Any]]) -> float:
    source = tokenize_lexical(content)
    if not source:
        return 0.0

    best = 0.0
    for turn in recent_turns:
        other = tokenize_lexical(str(turn.get('content') or ''))
        if not other:
            continue
        intersection = len(source & other)
        if intersection == 0:
            continue
        union = len(source | other)
        score = (intersection / union) if union else 0.0
        if score > best:
            best = score
    return best


def is_circumstantial_memory(content: str) -> bool:
    normalized = str(content or '').lower()
    return any(marker in normalized for marker in _CIRCUMSTANTIAL_MARKERS)


def build_fallback_decisions(
    traces: List[Dict[str, Any]],
    keep_candidate_id: str,
    reason: str,
    model: str,
    *,
    min_semantic_relevance: float,
) -> List[Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    for index, trace in enumerate(traces):
        candidate_id = trace_candidate_id(trace, index)
        semantic = max(0.0, min(1.0, trace_semantic_score(trace)))
        keep = candidate_id == keep_candidate_id and semantic >= min_semantic_relevance
        decisions.append(
            {
                'candidate_id': candidate_id,
                'keep': keep,
                'semantic_relevance': semantic,
                'contextual_gain': semantic if keep else 0.0,
                'redundant_with_recent': False,
                'reason': f'fallback:{reason}',
                'model': model,
                'decision_source': 'fallback',
            }
        )
    return decisions


def validate_arbiter_output(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_decisions = data.get('decisions')
    if raw_decisions is None:
        raw_ids = data.get('ids')
        if not isinstance(raw_ids, list):
            raise ValueError("missing 'decisions' list")
        raw_decisions = [
            {
                'candidate_id': str(candidate_id),
                'keep': True,
                'semantic_relevance': 1.0,
                'contextual_gain': 1.0,
                'redundant_with_recent': False,
                'reason': 'legacy_ids_format',
            }
            for candidate_id in raw_ids
        ]

    if not isinstance(raw_decisions, list):
        raise ValueError("'decisions' must be a list")

    validated: List[Dict[str, Any]] = []
    for item in raw_decisions:
        if not isinstance(item, dict):
            continue

        candidate_id = str(item.get('candidate_id', '')).strip()
        keep = item.get('keep')
        if not candidate_id or not isinstance(keep, bool):
            continue

        try:
            semantic_relevance = as_float_01(item.get('semantic_relevance'))
            contextual_gain = as_float_01(item.get('contextual_gain'))
        except Exception:
            continue

        redundant_with_recent = item.get('redundant_with_recent', False)
        if not isinstance(redundant_with_recent, bool):
            redundant_with_recent = False

        reason = str(item.get('reason', '')).strip()[:500]
        validated.append(
            {
                'candidate_id': candidate_id,
                'keep': keep,
                'semantic_relevance': semantic_relevance,
                'contextual_gain': contextual_gain,
                'redundant_with_recent': redundant_with_recent,
                'reason': reason,
                'decision_source': 'llm',
            }
        )

    return validated


def complete_and_select_decisions(
    traces: List[Dict[str, Any]],
    decisions: List[Dict[str, Any]],
    *,
    recent_turns: List[Dict[str, Any]],
    model: str,
    min_semantic_relevance: float,
    min_contextual_gain: float,
    max_kept_traces: int,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    trace_by_candidate_id = {
        trace_candidate_id(trace, index): trace
        for index, trace in enumerate(traces)
    }
    ordered_candidate_ids = [
        trace_candidate_id(trace, index)
        for index, trace in enumerate(traces)
    ]
    decisions_by_id: Dict[str, Dict[str, Any]] = {}
    for decision in decisions:
        candidate_id = str(decision['candidate_id'])
        if candidate_id not in trace_by_candidate_id:
            continue
        if candidate_id in decisions_by_id:
            if decision['keep'] and not decisions_by_id[candidate_id]['keep']:
                decisions_by_id[candidate_id] = decision
        else:
            decisions_by_id[candidate_id] = decision

    completed_decisions: List[Dict[str, Any]] = []
    for index, trace in enumerate(traces):
        candidate_id = ordered_candidate_ids[index]
        if candidate_id in decisions_by_id:
            decision = dict(decisions_by_id[candidate_id])
        else:
            decision = {
                'candidate_id': candidate_id,
                'keep': False,
                'semantic_relevance': max(0.0, min(1.0, trace_semantic_score(trace))),
                'contextual_gain': 0.0,
                'redundant_with_recent': False,
                'reason': 'missing_from_llm_output',
                'decision_source': 'llm',
            }
        completed_decisions.append(decision)

    selected_candidates: List[tuple[float, str]] = []
    for decision in completed_decisions:
        candidate_id = str(decision['candidate_id'])
        trace = trace_by_candidate_id.get(candidate_id)
        if trace is None:
            continue
        trace_content = str(trace.get('content') or '')
        if not decision['keep']:
            continue
        if decision['redundant_with_recent']:
            decision['keep'] = False
            append_reason(decision, 'redundant_with_recent')
            continue

        lexical_similarity = max_lexical_similarity(trace_content, recent_turns)
        low_gain_cutoff = max(float(min_contextual_gain), 0.45)
        if lexical_similarity >= 0.72 and decision['contextual_gain'] < low_gain_cutoff:
            decision['keep'] = False
            decision['redundant_with_recent'] = True
            append_reason(
                decision,
                f'lexical_near_duplicate_low_context_gain(sim={lexical_similarity:.2f})',
            )
            continue

        if is_circumstantial_memory(trace_content):
            utility_score = (
                float(decision['semantic_relevance']) * 0.4
                + float(decision['contextual_gain']) * 0.6
            )
            if utility_score < 0.62:
                penalized_gain = max(0.0, float(decision['contextual_gain']) - 0.18)
                if penalized_gain < decision['contextual_gain']:
                    decision['contextual_gain'] = penalized_gain
                    append_reason(decision, 'circumstantial_penalty_applied')
                if decision['contextual_gain'] < min_contextual_gain:
                    decision['keep'] = False
                    append_reason(decision, 'circumstantial_low_response_utility')
                    continue

        if decision['semantic_relevance'] < min_semantic_relevance:
            decision['keep'] = False
            append_reason(decision, 'below_semantic_threshold')
            continue
        if decision['contextual_gain'] < min_contextual_gain:
            decision['keep'] = False
            append_reason(decision, 'below_contextual_gain_threshold')
            continue

        blended_score = (
            decision['semantic_relevance'] + decision['contextual_gain']
        ) / 2.0
        selected_candidates.append((blended_score, candidate_id))

    selected_candidates.sort(key=lambda candidate: candidate[0], reverse=True)

    max_kept = max(0, max_kept_traces)
    chosen: set[str] = set()
    kept: List[Dict[str, Any]] = []
    for _, candidate_id in selected_candidates:
        if candidate_id in chosen:
            continue
        chosen.add(candidate_id)
        kept.append(trace_by_candidate_id[candidate_id])
        if len(kept) >= max_kept:
            break

    for decision in completed_decisions:
        candidate_id = str(decision['candidate_id'])
        decision['keep'] = candidate_id in chosen
        decision['model'] = model

    return kept, completed_decisions
