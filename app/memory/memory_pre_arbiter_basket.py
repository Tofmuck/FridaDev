from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from difflib import SequenceMatcher
import hashlib
import re
from typing import Any, Mapping, Sequence

from memory import memory_traces_summaries


PRE_ARBITER_MAX_CANDIDATES = 8

_ROLE_PRIORITY = {
    'user': 2,
    'assistant': 1,
    'summary': 0,
}
_DEDUP_REASON_PRIORITY = {
    'none': 0,
    'lexical_near_duplicate': 1,
    'same_conversation_same_idea': 2,
    'trace_summary_collision': 3,
    'exact_duplicate': 4,
}
_TOKEN_RE = re.compile(r'[a-z0-9]+')


@dataclass(frozen=True)
class PreArbiterBasket:
    candidates: list[dict[str, Any]]
    prompt_candidates: list[dict[str, Any]]


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _float_or_zero(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _timestamp_sort_value(value: Any) -> float:
    text = _optional_str(value)
    if not text:
        return 0.0
    try:
        return datetime.fromisoformat(text.replace('Z', '+00:00')).timestamp()
    except ValueError:
        return 0.0


def _content_norm(text: Any) -> str:
    normalized = memory_traces_summaries._normalize_lexical_text(str(text or ''))
    normalized = re.sub(r'[^a-z0-9]+', ' ', normalized)
    return re.sub(r'\s+', ' ', normalized).strip()


def _token_set(text: Any) -> set[str]:
    return {token for token in _TOKEN_RE.findall(_content_norm(text)) if token}


def _sequence_ratio(left: str, right: str) -> float:
    if not left or not right:
        return 0.0
    return SequenceMatcher(None, left, right).ratio()


def _token_jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def _role_priority(role: Any) -> int:
    return _ROLE_PRIORITY.get(_optional_str(role) or '', -1)


def _representative_rank(item: Mapping[str, Any]) -> tuple[float, int, int, float]:
    return (
        _float_or_zero(item.get('retrieval_score')),
        _role_priority(item.get('role')),
        1 if bool(item.get('parent_summary_present')) else 0,
        _timestamp_sort_value(item.get('timestamp_iso')),
    )


def _dedup_key(source_kind: str, role: str | None, content_norm: str) -> str:
    slug_tokens = content_norm.split()[:10]
    slug = '-'.join(slug_tokens)[:80] if slug_tokens else 'empty'
    digest = hashlib.sha1(
        f'{source_kind}|{role or "unknown"}|{content_norm}'.encode('utf-8')
    ).hexdigest()[:8]
    return f'{source_kind}:{role or "unknown"}:{slug}:{digest}'


def _canonical_source_candidate_ids(
    representative_id: str,
    source_candidate_ids: Sequence[str],
) -> list[str]:
    seen: set[str] = set()
    ordered = [representative_id]
    seen.add(representative_id)
    for candidate_id in source_candidate_ids:
        text = _optional_str(candidate_id)
        if not text or text in seen:
            continue
        ordered.append(text)
        seen.add(text)
    return ordered


def _source_kind(item: Mapping[str, Any]) -> str:
    explicit = _optional_str(item.get('source_kind'))
    if explicit:
        return explicit
    if _optional_str(item.get('role')) == 'summary':
        return 'summary'
    return 'trace'


def _is_summary_candidate(item: Mapping[str, Any]) -> bool:
    return _source_kind(item) == 'summary'


def _summary_covers_trace(summary: Mapping[str, Any], trace: Mapping[str, Any]) -> bool:
    if _optional_str(summary.get('conversation_id')) != _optional_str(trace.get('conversation_id')):
        return False
    summary_id = _optional_str(summary.get('summary_id'))
    trace_summary_id = _optional_str(trace.get('summary_id'))
    if summary_id and trace_summary_id and summary_id == trace_summary_id:
        return True

    trace_ts = _timestamp_sort_value(trace.get('timestamp_iso'))
    if trace_ts == 0.0:
        return False
    start_ts = _timestamp_sort_value(summary.get('start_ts'))
    end_ts = _timestamp_sort_value(summary.get('end_ts') or summary.get('timestamp_iso'))
    if start_ts == 0.0 and end_ts == 0.0:
        return False
    if start_ts and trace_ts < start_ts:
        return False
    if end_ts and trace_ts > end_ts:
        return False
    return True


def _trace_summary_collision(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if _source_kind(left) == _source_kind(right):
        return False
    summary = left if _is_summary_candidate(left) else right
    trace = right if summary is left else left
    return _summary_covers_trace(summary, trace)


def _same_conversation_same_idea(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if _is_summary_candidate(left) or _is_summary_candidate(right):
        return False
    if _optional_str(left.get('conversation_id')) != _optional_str(right.get('conversation_id')):
        return False
    left_norm = str(left.get('_content_norm') or '')
    right_norm = str(right.get('_content_norm') or '')
    if not left_norm or not right_norm:
        return False
    left_tokens = set(left.get('_tokens') or ())
    right_tokens = set(right.get('_tokens') or ())
    if not left_tokens or not right_tokens:
        return False
    smaller_tokens, larger_tokens = (
        (left_tokens, right_tokens)
        if len(left_tokens) <= len(right_tokens)
        else (right_tokens, left_tokens)
    )
    smaller_norm, larger_norm = (
        (left_norm, right_norm)
        if len(left_norm) <= len(right_norm)
        else (right_norm, left_norm)
    )
    if len(smaller_tokens) < 3:
        return False
    extra_tokens = larger_tokens - smaller_tokens
    if smaller_tokens <= larger_tokens and smaller_norm in larger_norm and len(extra_tokens) <= 2:
        return True
    return False


def _lexical_near_duplicate(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    if _is_summary_candidate(left) or _is_summary_candidate(right):
        return False
    left_norm = str(left.get('_content_norm') or '')
    right_norm = str(right.get('_content_norm') or '')
    if not left_norm or not right_norm or left_norm == right_norm:
        return False

    same_role = _optional_str(left.get('role')) == _optional_str(right.get('role'))
    same_conversation = _optional_str(left.get('conversation_id')) == _optional_str(right.get('conversation_id'))
    if not same_role and not same_conversation:
        return False

    left_tokens = set(left.get('_tokens') or ())
    right_tokens = set(right.get('_tokens') or ())
    if min(len(left_tokens), len(right_tokens)) < 3:
        return False

    ratio = _sequence_ratio(left_norm, right_norm)
    jaccard = _token_jaccard(left_tokens, right_tokens)
    if ratio >= 0.96 and jaccard >= 0.70:
        return True
    if jaccard >= 0.85 and (
        left_norm in right_norm
        or right_norm in left_norm
        or ratio >= 0.90
    ):
        return True
    return False


def _match_reason(candidate: Mapping[str, Any], group: Mapping[str, Any]) -> str | None:
    candidate_members = candidate.get('_members') if isinstance(candidate, Mapping) else None
    group_members = group.get('_members') if isinstance(group, Mapping) else None
    if not isinstance(candidate_members, Sequence):
        candidate_members = [candidate]
    if not isinstance(group_members, Sequence):
        group_members = [group]

    for left in candidate_members:
        for right in group_members:
            if not isinstance(left, Mapping) or not isinstance(right, Mapping):
                continue
            if _trace_summary_collision(left, right):
                return 'trace_summary_collision'
    for left in candidate_members:
        for right in group_members:
            if not isinstance(left, Mapping) or not isinstance(right, Mapping):
                continue
            if str(left.get('_content_norm') or '') == str(right.get('_content_norm') or ''):
                return 'exact_duplicate'
    for left in candidate_members:
        for right in group_members:
            if not isinstance(left, Mapping) or not isinstance(right, Mapping):
                continue
            if _same_conversation_same_idea(left, right):
                return 'same_conversation_same_idea'
    for left in candidate_members:
        for right in group_members:
            if not isinstance(left, Mapping) or not isinstance(right, Mapping):
                continue
            if _lexical_near_duplicate(left, right):
                return 'lexical_near_duplicate'
    return None


def _merge_reason(current: str, new_reason: str) -> str:
    if _DEDUP_REASON_PRIORITY.get(new_reason, 0) >= _DEDUP_REASON_PRIORITY.get(current, 0):
        return new_reason
    return current


def _build_source_item(
    *,
    canonical_trace: Mapping[str, Any],
    retrieved_trace: Mapping[str, Any],
    internal_trace: Mapping[str, Any],
) -> dict[str, Any]:
    source_kind = _source_kind(canonical_trace)
    source_lane = _optional_str(canonical_trace.get('source_lane') or retrieved_trace.get('source_lane'))
    if not source_lane:
        source_lane = 'summaries' if source_kind == 'summary' else 'global'
    candidate_id = _optional_str(canonical_trace.get('candidate_id')) or 'cand-missing'
    role = _optional_str(canonical_trace.get('role'))
    content = str(canonical_trace.get('content') or '')
    start_ts = _optional_str(canonical_trace.get('start_ts') or retrieved_trace.get('start_ts'))
    end_ts = _optional_str(canonical_trace.get('end_ts') or retrieved_trace.get('end_ts'))
    timestamp_iso = _optional_str(
        canonical_trace.get('timestamp_iso')
        or retrieved_trace.get('timestamp_iso')
        or retrieved_trace.get('timestamp')
        or end_ts
    )
    parent_summary = None
    if source_kind != 'summary':
        parent_summary = canonical_trace.get('parent_summary') or retrieved_trace.get('parent_summary')
    retrieval_score = _float_or_zero(canonical_trace.get('retrieval_score'))
    semantic_score = _float_or_zero(internal_trace.get('semantic_score'))
    if semantic_score == 0.0 and 'semantic_score' not in internal_trace:
        semantic_score = _float_or_zero(
            internal_trace.get('retrieval_score', internal_trace.get('score', retrieval_score))
        )

    prompt_candidate = dict(retrieved_trace)
    prompt_candidate.update(
        {
            'candidate_id': candidate_id,
            'source_candidate_ids': [candidate_id],
            'source_kind': source_kind,
            'source_lane': source_lane,
            'conversation_id': _optional_str(canonical_trace.get('conversation_id')),
            'role': role,
            'content': content,
            'timestamp': timestamp_iso,
            'timestamp_iso': timestamp_iso,
            'start_ts': start_ts,
            'end_ts': end_ts,
            'retrieval_score': retrieval_score,
            'semantic_score': semantic_score,
            'summary_id': _optional_str(canonical_trace.get('summary_id')),
            'parent_summary': parent_summary,
            'parent_summary_present': bool(parent_summary) if source_kind != 'summary' else False,
            'dedup_reason_code': 'none',
        }
    )

    return {
        'candidate_id': candidate_id,
        'conversation_id': _optional_str(canonical_trace.get('conversation_id')),
        'role': role,
        'content': content,
        'timestamp_iso': timestamp_iso,
        'start_ts': start_ts,
        'end_ts': end_ts,
        'retrieval_score': retrieval_score,
        'semantic_score': semantic_score,
        'summary_id': _optional_str(canonical_trace.get('summary_id')),
        'parent_summary_present': bool(parent_summary) if source_kind != 'summary' else False,
        'source_kind': source_kind,
        'source_lane': source_lane,
        'source_candidate_ids': [candidate_id],
        'prompt_candidate': prompt_candidate,
        '_content_norm': _content_norm(content),
        '_tokens': _token_set(content),
    }


def _best_member(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return dict(max(members, key=_representative_rank))


def _select_group_representative(group: dict[str, Any]) -> dict[str, Any]:
    members = [
        member
        for member in group.get('_members', ())
        if isinstance(member, Mapping)
    ]
    if not members:
        return group

    trace_members = [member for member in members if _source_kind(member) == 'trace']
    summary_members = [member for member in members if _source_kind(member) == 'summary']

    if trace_members and summary_members:
        best_trace = _best_member(trace_members)
        best_summary = _best_member(summary_members)
        if (
            len(trace_members) >= 2
            and _float_or_zero(best_summary.get('retrieval_score'))
            >= _float_or_zero(best_trace.get('retrieval_score'))
        ):
            representative = best_summary
        else:
            representative = best_trace
    else:
        representative = _best_member(members)

    selected = dict(representative)
    selected['source_candidate_ids'] = list(group.get('source_candidate_ids', ()))
    selected['dedup_reason_code'] = str(group.get('dedup_reason_code') or 'none')
    selected['_members'] = [dict(member) for member in members]
    return selected


def _merge_source_item(
    group: dict[str, Any],
    incoming: Mapping[str, Any],
    *,
    reason_code: str,
) -> dict[str, Any]:
    updated = dict(group)
    updated_members = [dict(member) for member in updated.get('_members', ())]
    incoming_members = incoming.get('_members') if isinstance(incoming, Mapping) else None
    if isinstance(incoming_members, Sequence):
        updated_members.extend(
            dict(member)
            for member in incoming_members
            if isinstance(member, Mapping)
        )
    else:
        updated_members.append(dict(incoming))
    updated['_members'] = updated_members
    source_candidate_ids = list(updated.get('source_candidate_ids', ()))
    for candidate_id in list(group.get('source_candidate_ids', ())) + list(incoming.get('source_candidate_ids', ())):
        text = _optional_str(candidate_id)
        if text and text not in source_candidate_ids:
            source_candidate_ids.append(text)
    updated['source_candidate_ids'] = source_candidate_ids
    updated['dedup_reason_code'] = _merge_reason(
        str(group.get('dedup_reason_code') or 'none'),
        reason_code,
    )
    return _select_group_representative(updated)


def _finalize_group(group: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    representative_id = _optional_str(group.get('candidate_id')) or 'cand-missing'
    source_candidate_ids = _canonical_source_candidate_ids(
        representative_id,
        group.get('source_candidate_ids', ()),
    )
    dedup_key = _dedup_key(
        str(group.get('source_kind') or 'trace'),
        _optional_str(group.get('role')),
        str(group.get('_content_norm') or ''),
    )
    candidate = {
        'candidate_id': representative_id,
        'source_candidate_ids': source_candidate_ids,
        'source_kind': str(group.get('source_kind') or 'trace'),
        'source_lane': str(group.get('source_lane') or 'global'),
        'conversation_id': _optional_str(group.get('conversation_id')),
        'role': _optional_str(group.get('role')),
        'content': str(group.get('content') or ''),
        'timestamp_iso': _optional_str(group.get('timestamp_iso')),
        'start_ts': _optional_str(group.get('start_ts')),
        'end_ts': _optional_str(group.get('end_ts')),
        'retrieval_score': _float_or_zero(group.get('retrieval_score')),
        'semantic_score': _float_or_zero(group.get('semantic_score')),
        'summary_id': _optional_str(group.get('summary_id')),
        'parent_summary_present': bool(group.get('parent_summary_present', False)),
        'dedup_key': dedup_key,
        'dedup_reason_code': str(group.get('dedup_reason_code') or 'none'),
    }
    prompt_candidate = dict(group.get('prompt_candidate') or {})
    prompt_candidate.update(candidate)
    prompt_candidate['timestamp'] = candidate['timestamp_iso']
    prompt_candidate['parent_summary'] = group.get('prompt_candidate', {}).get('parent_summary')
    return candidate, prompt_candidate


def _assign_conversation_rank(candidates: list[dict[str, Any]]) -> None:
    ranks: dict[str, int] = {}
    for candidate in candidates:
        conversation_id = _optional_str(candidate.get('conversation_id')) or ''
        ranks[conversation_id] = ranks.get(conversation_id, 0) + 1
        candidate['conversation_rank'] = ranks[conversation_id]


def build_pre_arbiter_basket(
    *,
    memory_retrieved: Mapping[str, Any],
    retrieved_candidates: Sequence[Mapping[str, Any]],
    internal_traces: Sequence[Mapping[str, Any]],
    max_candidates: int = PRE_ARBITER_MAX_CANDIDATES,
) -> PreArbiterBasket:
    canonical_traces = memory_retrieved.get('traces')
    if not isinstance(canonical_traces, Sequence):
        return PreArbiterBasket(candidates=[], prompt_candidates=[])

    source_items: list[dict[str, Any]] = []
    for index, canonical_trace in enumerate(canonical_traces):
        if not isinstance(canonical_trace, Mapping):
            continue
        retrieved_trace = retrieved_candidates[index] if index < len(retrieved_candidates) else {}
        internal_trace = internal_traces[index] if index < len(internal_traces) else {}
        source_items.append(
            _build_source_item(
                canonical_trace=canonical_trace,
                retrieved_trace=retrieved_trace if isinstance(retrieved_trace, Mapping) else {},
                internal_trace=internal_trace if isinstance(internal_trace, Mapping) else {},
            )
        )

    groups: list[dict[str, Any]] = []
    for item in source_items:
        matches: list[tuple[int, str]] = []
        for index, group in enumerate(groups):
            reason_code = _match_reason(item, group)
            if not reason_code:
                continue
            matches.append((index, reason_code))
        if not matches:
            base = dict(item)
            base['dedup_reason_code'] = 'none'
            base['_members'] = [dict(item)]
            groups.append(base)
            continue

        primary_index, primary_reason = matches[0]
        primary_group = _merge_source_item(groups[primary_index], item, reason_code=primary_reason)
        for secondary_index, secondary_reason in reversed(matches[1:]):
            primary_group = _merge_source_item(
                primary_group,
                groups[secondary_index],
                reason_code=secondary_reason,
            )
            del groups[secondary_index]
        groups[primary_index] = primary_group

    groups.sort(key=_representative_rank, reverse=True)
    limit = max(0, int(max_candidates))
    finalized = [_finalize_group(group) for group in groups[:limit]]
    candidates = [candidate for candidate, _prompt in finalized]
    prompt_candidates = [prompt for _candidate, prompt in finalized]
    _assign_conversation_rank(candidates)
    _assign_conversation_rank(prompt_candidates)
    return PreArbiterBasket(
        candidates=candidates,
        prompt_candidates=prompt_candidates,
    )


def select_prompt_candidates(
    basket: PreArbiterBasket,
    *,
    decisions: Sequence[Mapping[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    if decisions is None:
        return [dict(candidate) for candidate in basket.prompt_candidates]

    kept_candidate_ids = {
        _optional_str(decision.get('candidate_id'))
        for decision in decisions
        if bool(decision.get('keep', False))
    }
    kept_candidate_ids.discard(None)
    return [
        dict(candidate)
        for candidate in basket.prompt_candidates
        if _optional_str(candidate.get('candidate_id')) in kept_candidate_ids
    ]
