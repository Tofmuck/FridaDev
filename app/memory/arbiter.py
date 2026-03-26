from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Tuple

import requests

import config
from admin import runtime_settings
from core.llm_client import _sanitize_encoding, or_headers

logger = logging.getLogger('kiki.arbiter')


def _runtime_arbiter_model_name() -> str:
    view = runtime_settings.get_arbiter_model_settings()
    return str(view.payload['model']['value'])

_ALLOWED_STABILITY = {'durable', 'episodic', 'unknown'}
_ALLOWED_UTTERANCE_MODE = {
    'self_description',
    'projection',
    'role_play',
    'irony',
    'speculation',
    'unknown',
}
_ALLOWED_RECURRENCE = {'first_seen', 'repeated', 'habitual', 'unknown'}
_ALLOWED_SCOPE = {'user', 'llm', 'situation', 'mixed', 'unknown'}
_ALLOWED_EVIDENCE_KIND = {'explicit', 'inferred', 'weak'}

_METRICS: Dict[str, int] = {
    'arbiter_call_count': 0,
    'identity_extractor_call_count': 0,
    'arbiter_parse_error_count': 0,
    'identity_parse_error_count': 0,
    'arbiter_fallback_count': 0,
}

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


def _inc_metric(name: str) -> int:
    _METRICS[name] = _METRICS.get(name, 0) + 1
    return _METRICS[name]



def get_runtime_metrics() -> Dict[str, int]:
    return dict(_METRICS)


def _load_prompt(path_str: str, label: str) -> str:
    path = Path(__file__).resolve().parent.parent / path_str
    try:
        return path.read_text(encoding='utf-8').strip()
    except Exception as exc:
        logger.error('%s_prompt_load_error path=%s err=%s', label, path, exc)
        return ''


def _extract_json_blob(raw: str) -> str:
    text = raw.strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text


def _safe_json_loads(raw: str) -> Dict[str, Any]:
    obj = json.loads(_extract_json_blob(raw))
    if not isinstance(obj, dict):
        raise ValueError('JSON root must be an object')
    return obj


def _as_float_01(value: Any) -> float:
    f = float(value)
    if f < 0.0 or f > 1.0:
        raise ValueError('value out of [0,1] range')
    return f


def _trace_score(trace: Dict[str, Any]) -> float:
    try:
        return float(trace.get('score') or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _append_reason(decision: Dict[str, Any], suffix: str) -> None:
    base = str(decision.get('reason') or '').strip()
    decision['reason'] = f'{base} | {suffix}' if base else suffix


def _tokenize_lexical(text: str) -> set[str]:
    tokens = {t.lower() for t in _LEXICAL_TOKEN_RE.findall(text or '') if len(t) >= 3}
    return {t for t in tokens if t not in _LEXICAL_STOPWORDS}


def _max_lexical_similarity(content: str, recent_turns: List[Dict[str, Any]]) -> float:
    source = _tokenize_lexical(content)
    if not source:
        return 0.0

    best = 0.0
    for turn in recent_turns:
        other = _tokenize_lexical(str(turn.get('content') or ''))
        if not other:
            continue
        inter = len(source & other)
        if inter == 0:
            continue
        union = len(source | other)
        score = (inter / union) if union else 0.0
        if score > best:
            best = score
    return best


def _is_circumstantial_memory(content: str) -> bool:
    normalized = str(content or '').lower()
    return any(marker in normalized for marker in _CIRCUMSTANTIAL_MARKERS)


def _build_fallback_decisions(
    traces: List[Dict[str, Any]],
    keep_idx: int,
    reason: str,
    model: str,
) -> List[Dict[str, Any]]:
    decisions: List[Dict[str, Any]] = []
    threshold = config.ARBITER_MIN_SEMANTIC_RELEVANCE
    for i, trace in enumerate(traces):
        semantic = max(0.0, min(1.0, _trace_score(trace)))
        keep = i == keep_idx and semantic >= threshold
        decisions.append(
            {
                'candidate_id': str(i),
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


def _deterministic_fallback(
    traces: List[Dict[str, Any]],
    reason: str,
    model: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not traces:
        return [], []

    keep_idx = max(range(len(traces)), key=lambda idx: _trace_score(traces[idx]))
    best = traces[keep_idx]
    best_score = _trace_score(best)
    threshold = config.ARBITER_MIN_SEMANTIC_RELEVANCE
    kept = [best] if best_score >= threshold else []

    fallback_count = _inc_metric('arbiter_fallback_count')
    logger.warning(
        'arbiter_fallback reason=%s kept=%s best_score=%.3f threshold=%.3f fallback_count=%s',
        reason,
        len(kept),
        best_score,
        threshold,
        fallback_count,
    )
    decisions = _build_fallback_decisions(traces, keep_idx=keep_idx, reason=reason, model=model)
    return kept, decisions


def _validate_arbiter_output(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_decisions = data.get('decisions')
    if raw_decisions is None:
        # Backward compatibility: old schema {"ids": ["0", "1"]}
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
        if not candidate_id.isdigit() or not isinstance(keep, bool):
            continue

        try:
            semantic_relevance = _as_float_01(item.get('semantic_relevance'))
            contextual_gain = _as_float_01(item.get('contextual_gain'))
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


def filter_traces_with_diagnostics(
    traces: List[Dict[str, Any]],
    recent_turns: List[Dict[str, Any]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _inc_metric('arbiter_call_count')
    """
    Return (kept_traces, decisions_for_logging).
    decisions_for_logging always references candidate_id indexes from `traces`.
    """
    if not traces:
        return [], []

    arbiter_model = _runtime_arbiter_model_name()
    system_prompt = _load_prompt(config.ARBITER_PROMPT_PATH, 'arbiter')
    if not system_prompt:
        return _deterministic_fallback(traces, 'prompt_missing', arbiter_model)

    recent_text = '\n'.join(
        f"{t.get('role', '?').upper()}: {t.get('content', '')}"
        for t in recent_turns[-10:]
    )

    candidates = [
        {
            'id': str(i),
            'role': t.get('role', '?'),
            'content': t.get('content', ''),
            'ts': (t.get('timestamp') or '')[:19],
            'score': round(_trace_score(t), 6),
        }
        for i, t in enumerate(traces)
    ]

    user_content = (
        f'=== Recent context ===\\n{recent_text}\\n\\n'
        f'=== Candidate memories ===\\n{json.dumps(candidates, ensure_ascii=False, indent=2)}'
    )

    payload = {
        'model': arbiter_model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content},
        ],
        'temperature': 0.0,
        'top_p': 1.0,
        'max_tokens': 600,
    }

    try:
        response = requests.post(
            f'{config.OR_BASE}/chat/completions',
            json=payload,
            headers=or_headers(caller='arbiter'),
            timeout=config.ARBITER_TIMEOUT_S,
        )
        response.raise_for_status()
        raw = _sanitize_encoding(response.json()['choices'][0]['message']['content']).strip()
        result = _safe_json_loads(raw)
        decisions = _validate_arbiter_output(result)
    except requests.exceptions.Timeout:
        logger.warning('arbiter_timeout model=%s', arbiter_model)
        return _deterministic_fallback(traces, 'timeout', arbiter_model)
    except Exception as exc:
        parse_count = _inc_metric('arbiter_parse_error_count')
        logger.error('arbiter_parse_or_runtime_error err=%s parse_error_count=%s', exc, parse_count)
        return _deterministic_fallback(traces, 'parse_or_runtime_error', arbiter_model)

    decisions_by_id: Dict[int, Dict[str, Any]] = {}
    for decision in decisions:
        idx = int(decision['candidate_id'])
        if idx < 0 or idx >= len(traces):
            continue
        if idx in decisions_by_id:
            # Prefer explicit keep=true when duplicated.
            if decision['keep'] and not decisions_by_id[idx]['keep']:
                decisions_by_id[idx] = decision
        else:
            decisions_by_id[idx] = decision

    completed_decisions: List[Dict[str, Any]] = []
    for idx, trace in enumerate(traces):
        if idx in decisions_by_id:
            d = dict(decisions_by_id[idx])
        else:
            d = {
                'candidate_id': str(idx),
                'keep': False,
                'semantic_relevance': max(0.0, min(1.0, _trace_score(trace))),
                'contextual_gain': 0.0,
                'redundant_with_recent': False,
                'reason': 'missing_from_llm_output',
                'decision_source': 'llm',
            }
        completed_decisions.append(d)

    selected_candidates: List[tuple[float, int]] = []
    for d in completed_decisions:
        candidate_idx = int(d['candidate_id'])
        trace_content = str(traces[candidate_idx].get('content') or '')
        if not d['keep']:
            continue
        if d['redundant_with_recent']:
            d['keep'] = False
            _append_reason(d, 'redundant_with_recent')
            continue

        lexical_similarity = _max_lexical_similarity(trace_content, recent_turns)
        low_gain_cutoff = max(float(config.ARBITER_MIN_CONTEXTUAL_GAIN), 0.45)
        if lexical_similarity >= 0.72 and d['contextual_gain'] < low_gain_cutoff:
            d['keep'] = False
            d['redundant_with_recent'] = True
            _append_reason(
                d,
                f'lexical_near_duplicate_low_context_gain(sim={lexical_similarity:.2f})',
            )
            continue

        if _is_circumstantial_memory(trace_content):
            utility_score = (float(d['semantic_relevance']) * 0.4) + (float(d['contextual_gain']) * 0.6)
            if utility_score < 0.62:
                penalized_gain = max(0.0, float(d['contextual_gain']) - 0.18)
                if penalized_gain < d['contextual_gain']:
                    d['contextual_gain'] = penalized_gain
                    _append_reason(d, 'circumstantial_penalty_applied')
                if d['contextual_gain'] < config.ARBITER_MIN_CONTEXTUAL_GAIN:
                    d['keep'] = False
                    _append_reason(d, 'circumstantial_low_response_utility')
                    continue

        if d['semantic_relevance'] < config.ARBITER_MIN_SEMANTIC_RELEVANCE:
            d['keep'] = False
            _append_reason(d, 'below_semantic_threshold')
            continue
        if d['contextual_gain'] < config.ARBITER_MIN_CONTEXTUAL_GAIN:
            d['keep'] = False
            _append_reason(d, 'below_contextual_gain_threshold')
            continue

        blended_score = (d['semantic_relevance'] + d['contextual_gain']) / 2.0
        selected_candidates.append((blended_score, candidate_idx))

    selected_candidates.sort(key=lambda x: x[0], reverse=True)

    max_kept = max(0, config.ARBITER_MAX_KEPT_TRACES)
    chosen: set[int] = set()
    kept: List[Dict[str, Any]] = []
    for _, idx in selected_candidates:
        if idx in chosen:
            continue
        chosen.add(idx)
        kept.append(traces[idx])
        if len(kept) >= max_kept:
            break

    for d in completed_decisions:
        idx = int(d['candidate_id'])
        d['keep'] = idx in chosen
        d['model'] = arbiter_model

    logger.info(
        'arbiter_done raw=%s parsed=%s kept=%s rejected=%s model=%s',
        len(traces),
        len(completed_decisions),
        len(kept),
        len(traces) - len(kept),
        arbiter_model,
    )
    return kept, completed_decisions


def filter_traces(
    traces: List[Dict[str, Any]],
    recent_turns: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Compatibility wrapper returning only kept traces."""
    kept, _ = filter_traces_with_diagnostics(traces, recent_turns)
    return kept


def _validate_identity_output(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    raw_entries = data.get('entries')
    if not isinstance(raw_entries, list):
        raise ValueError("'entries' must be a list")

    validated: List[Dict[str, Any]] = []
    for entry in raw_entries:
        if not isinstance(entry, dict):
            continue

        subject = str(entry.get('subject', '')).strip()
        content = str(entry.get('content', '')).strip()
        if subject not in {'user', 'llm'} or not content:
            continue

        stability = str(entry.get('stability', '')).strip()
        utterance_mode = str(entry.get('utterance_mode', '')).strip()
        recurrence = str(entry.get('recurrence', '')).strip()
        scope = str(entry.get('scope', '')).strip()
        evidence_kind = str(entry.get('evidence_kind', '')).strip()

        if stability not in _ALLOWED_STABILITY:
            continue
        if utterance_mode not in _ALLOWED_UTTERANCE_MODE:
            continue
        if recurrence not in _ALLOWED_RECURRENCE:
            continue
        if scope not in _ALLOWED_SCOPE:
            continue
        if evidence_kind not in _ALLOWED_EVIDENCE_KIND:
            continue

        try:
            confidence = _as_float_01(entry.get('confidence'))
        except Exception:
            continue

        reason = str(entry.get('reason', '')).strip()[:500]

        validated.append(
            {
                'subject': subject,
                'content': content,
                'stability': stability,
                'utterance_mode': utterance_mode,
                'recurrence': recurrence,
                'scope': scope,
                'evidence_kind': evidence_kind,
                'confidence': confidence,
                'reason': reason,
            }
        )

    return validated


def extract_identities(recent_turns: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    _inc_metric('identity_extractor_call_count')
    """
    Extract identity candidates from recent turns using strict JSON schema.
    Returns [] on any runtime/parse failure to avoid breaking user response flow.
    """
    if not recent_turns:
        return []

    arbiter_model = _runtime_arbiter_model_name()
    system_prompt = _load_prompt(config.IDENTITY_EXTRACTOR_PROMPT_PATH, 'identity_extractor')
    if not system_prompt:
        return []

    dialogue = '\n'.join(
        f"{t.get('role', '?').upper()}: {t.get('content', '')}"
        for t in recent_turns
    )
    payload = {
        'model': arbiter_model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'Here is the dialogue:\\n\\n{dialogue}'},
        ],
        'temperature': 0.0,
        'top_p': 1.0,
        'max_tokens': 700,
    }

    try:
        response = requests.post(
            f'{config.OR_BASE}/chat/completions',
            json=payload,
            headers=or_headers(caller='arbiter'),
            timeout=config.ARBITER_TIMEOUT_S,
        )
        response.raise_for_status()
        raw = _sanitize_encoding(response.json()['choices'][0]['message']['content']).strip()
        result = _safe_json_loads(raw)
        entries = _validate_identity_output(result)
        logger.info('identity_extracted count=%s', len(entries))
        return entries
    except requests.exceptions.Timeout:
        logger.warning('identity_extractor_timeout model=%s', arbiter_model)
        return []
    except Exception as exc:
        parse_count = _inc_metric('identity_parse_error_count')
        logger.error('identity_extractor_error err=%s parse_error_count=%s', exc, parse_count)
        return []
