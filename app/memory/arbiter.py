from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Mapping, Tuple

import requests

import config
from admin import runtime_settings
from core import llm_client
from core.hermeneutic_node.inputs import time_input
from memory import arbiter_decision_support
from memory import identity_temporal_guard
from memory import mutable_identity_judge_v2

logger = logging.getLogger('frida.arbiter')


def _runtime_payload_value(payload: Mapping[str, Any], field: str, default: Any) -> Any:
    field_payload = payload.get(field)
    if not isinstance(field_payload, Mapping):
        return default
    resolved = field_payload.get('value')
    if resolved in (None, ''):
        return default
    return resolved


def _runtime_memory_arbiter_settings() -> dict[str, Any]:
    view = runtime_settings.get_memory_arbiter_model_settings()
    payload = view.payload

    return {
        'model': str(_runtime_payload_value(payload, 'model', config.MEMORY_ARBITER_MODEL)).strip()
        or config.MEMORY_ARBITER_MODEL,
        'temperature': float(_runtime_payload_value(payload, 'temperature', config.MEMORY_ARBITER_TEMPERATURE)),
        'top_p': float(_runtime_payload_value(payload, 'top_p', config.MEMORY_ARBITER_TOP_P)),
        'max_tokens': int(_runtime_payload_value(payload, 'max_tokens', config.MEMORY_ARBITER_MAX_TOKENS)),
        'timeout_s': int(_runtime_payload_value(payload, 'timeout_s', config.MEMORY_ARBITER_TIMEOUT_S)),
    }


def _runtime_identity_extractor_settings() -> dict[str, Any]:
    view = runtime_settings.get_identity_extractor_model_settings()
    payload = view.payload
    return {
        'model': str(_runtime_payload_value(payload, 'model', config.IDENTITY_EXTRACTOR_MODEL)).strip()
        or config.IDENTITY_EXTRACTOR_MODEL,
        'temperature': float(_runtime_payload_value(payload, 'temperature', config.IDENTITY_EXTRACTOR_TEMPERATURE)),
        'top_p': float(_runtime_payload_value(payload, 'top_p', config.IDENTITY_EXTRACTOR_TOP_P)),
        'max_tokens': int(_runtime_payload_value(payload, 'max_tokens', config.IDENTITY_EXTRACTOR_MAX_TOKENS)),
        'timeout_s': int(_runtime_payload_value(payload, 'timeout_s', config.IDENTITY_EXTRACTOR_TIMEOUT_S)),
    }


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
    'identity_legacy_rewriter_disabled_count': 0,
    'arbiter_parse_error_count': 0,
    'identity_parse_error_count': 0,
    'arbiter_fallback_count': 0,
}

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


_as_float_01 = arbiter_decision_support.as_float_01
_trace_retrieval_score = arbiter_decision_support.trace_retrieval_score
_trace_semantic_score = arbiter_decision_support.trace_semantic_score
_trace_candidate_id = arbiter_decision_support.trace_candidate_id
_trace_timestamp = arbiter_decision_support.trace_timestamp


def _temporal_reference(now_iso: str | None) -> dict[str, str]:
    now_value = str(now_iso or '').strip()
    if not now_value:
        return {}
    timezone_name = str(config.FRIDA_TIMEZONE)
    try:
        payload = time_input.build_time_input(
            now_utc_iso=now_value,
            timezone_name=timezone_name,
        )
    except Exception:
        return {
            'now_utc_iso': now_value,
            'timezone': timezone_name,
        }
    return {
        'now_utc_iso': str(payload.get('now_utc_iso') or now_value),
        'timezone': str(payload.get('timezone') or timezone_name),
        'now_local_iso': str(payload.get('now_local_iso') or ''),
        'local_date': str(payload.get('local_date') or ''),
        'local_time': str(payload.get('local_time') or ''),
    }


def _temporal_label(timestamp: str, *, now_iso: str | None) -> str:
    ts_value = str(timestamp or '').strip()
    now_value = str(now_iso or '').strip()
    if not ts_value or not now_value:
        return ''
    return time_input.render_delta_label(
        ts_value,
        now_value,
        timezone_name=str(config.FRIDA_TIMEZONE),
    )


def _format_recent_turn_for_arbiter(turn: Dict[str, Any], *, now_iso: str | None) -> str:
    role = str(turn.get('role') or '?').upper()
    content = str(turn.get('content') or '')
    label = _temporal_label(str(turn.get('timestamp') or turn.get('timestamp_iso') or ''), now_iso=now_iso)
    prefix = f'[{label}] ' if label else ''
    return f"{prefix}{role}: {content}"


_append_reason = arbiter_decision_support.append_reason
_tokenize_lexical = arbiter_decision_support.tokenize_lexical
_max_lexical_similarity = arbiter_decision_support.max_lexical_similarity
_is_circumstantial_memory = arbiter_decision_support.is_circumstantial_memory


def _build_fallback_decisions(
    traces: List[Dict[str, Any]],
    keep_candidate_id: str,
    reason: str,
    model: str,
) -> List[Dict[str, Any]]:
    return arbiter_decision_support.build_fallback_decisions(
        traces,
        keep_candidate_id,
        reason,
        model,
        min_semantic_relevance=config.ARBITER_MIN_SEMANTIC_RELEVANCE,
    )


def _deterministic_fallback(
    traces: List[Dict[str, Any]],
    reason: str,
    model: str,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    if not traces:
        return [], []

    keep_idx = max(range(len(traces)), key=lambda idx: _trace_semantic_score(traces[idx]))
    best = traces[keep_idx]
    keep_candidate_id = _trace_candidate_id(best, keep_idx)
    best_semantic_score = _trace_semantic_score(best)
    best_retrieval_score = _trace_retrieval_score(best)
    threshold = config.ARBITER_MIN_SEMANTIC_RELEVANCE
    kept = [best] if best_semantic_score >= threshold else []

    fallback_count = _inc_metric('arbiter_fallback_count')
    logger.warning(
        'arbiter_fallback reason=%s kept=%s best_semantic_score=%.3f best_retrieval_score=%.3f threshold=%.3f fallback_count=%s',
        reason,
        len(kept),
        best_semantic_score,
        best_retrieval_score,
        threshold,
        fallback_count,
    )
    decisions = _build_fallback_decisions(
        traces,
        keep_candidate_id=keep_candidate_id,
        reason=reason,
        model=model,
    )
    return kept, decisions


def _validate_arbiter_output(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    return arbiter_decision_support.validate_arbiter_output(data)


def filter_traces_with_diagnostics(
    traces: List[Dict[str, Any]],
    recent_turns: List[Dict[str, Any]],
    *,
    now_iso: str | None = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    _inc_metric('arbiter_call_count')
    """
    Return (kept_traces, decisions_for_logging).
    decisions_for_logging references stable candidate_id values when available.
    """
    if not traces:
        return [], []

    arbiter_settings = _runtime_memory_arbiter_settings()
    arbiter_model = str(arbiter_settings['model'])
    system_prompt = _load_prompt(config.ARBITER_PROMPT_PATH, 'arbiter')
    if not system_prompt:
        return _deterministic_fallback(traces, 'prompt_missing', arbiter_model)

    recent_text = '\n'.join(
        _format_recent_turn_for_arbiter(t, now_iso=now_iso)
        for t in recent_turns[-10:]
    )

    candidates = []
    for i, t in enumerate(traces):
        candidate = {
            'candidate_id': _trace_candidate_id(t, i),
            'source_kind': str(t.get('source_kind') or 'trace'),
            'source_lane': str(t.get('source_lane') or 'global'),
            'role': t.get('role', '?'),
            'content': t.get('content', ''),
            'timestamp_iso': _trace_timestamp(t)[:25],
            'retrieval_score': round(_trace_retrieval_score(t), 6),
            'semantic_score': round(_trace_semantic_score(t), 6),
        }
        temporal_label = _temporal_label(_trace_timestamp(t), now_iso=now_iso)
        if temporal_label:
            candidate['temporal_label'] = temporal_label
        candidates.append(candidate)

    temporal_reference = _temporal_reference(now_iso)
    temporal_section = (
        f'=== Temporal reference ===\\n{json.dumps(temporal_reference, ensure_ascii=False, indent=2)}\\n\\n'
        if temporal_reference
        else ''
    )
    user_content = (
        f'{temporal_section}'
        f'=== Recent context ===\\n{recent_text}\\n\\n'
        f'=== Candidate memories ===\\n{json.dumps(candidates, ensure_ascii=False, indent=2)}'
    )

    payload = {
        'model': arbiter_model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content},
        ],
        'temperature': float(arbiter_settings['temperature']),
        'top_p': float(arbiter_settings['top_p']),
        'max_tokens': int(arbiter_settings['max_tokens']),
    }
    payload = llm_client.with_provider_attribution(payload, caller='arbiter')

    try:
        response = requests.post(
            llm_client.or_chat_completions_url(),
            json=payload,
            headers=llm_client.or_headers(caller='arbiter'),
            timeout=int(arbiter_settings['timeout_s']),
        )
        response.raise_for_status()
        response_payload = llm_client.read_openrouter_response_payload(response)
        llm_client.log_provider_metadata(
            logger,
            'arbiter_provider_response',
            llm_client.extract_openrouter_provider_metadata(
                response_payload,
                requested_model=arbiter_model,
            ),
        )
        raw = llm_client.extract_openrouter_text(response_payload)
        result = _safe_json_loads(raw)
        decisions = _validate_arbiter_output(result)
    except requests.exceptions.Timeout:
        logger.warning('arbiter_timeout model=%s', arbiter_model)
        return _deterministic_fallback(traces, 'timeout', arbiter_model)
    except requests.exceptions.RequestException as exc:
        parse_count = _inc_metric('arbiter_parse_error_count')
        logger.error(
            'arbiter_parse_or_runtime_error reason=provider_transport_error '
            'err_class=%s parse_error_count=%s',
            exc.__class__.__name__,
            parse_count,
        )
        return _deterministic_fallback(traces, 'parse_or_runtime_error', arbiter_model)
    except Exception as exc:
        parse_count = _inc_metric('arbiter_parse_error_count')
        logger.error('arbiter_parse_or_runtime_error err=%s parse_error_count=%s', exc, parse_count)
        return _deterministic_fallback(traces, 'parse_or_runtime_error', arbiter_model)

    kept, completed_decisions = arbiter_decision_support.complete_and_select_decisions(
        traces,
        decisions,
        recent_turns=recent_turns,
        model=arbiter_model,
        min_semantic_relevance=config.ARBITER_MIN_SEMANTIC_RELEVANCE,
        min_contextual_gain=config.ARBITER_MIN_CONTEXTUAL_GAIN,
        max_kept_traces=config.ARBITER_MAX_KEPT_TRACES,
    )

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
    *,
    now_iso: str | None = None,
) -> List[Dict[str, Any]]:
    """Compatibility wrapper returning only kept traces."""
    kept, _ = filter_traces_with_diagnostics(traces, recent_turns, now_iso=now_iso)
    return kept


def _validate_identity_output(
    data: Dict[str, Any],
    *,
    source_summary: Mapping[str, Any] | None = None,
) -> List[Dict[str, Any]]:
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
        if identity_temporal_guard.has_weak_relative_temporal_marker(content):
            continue
        if not identity_temporal_guard.subject_has_admissible_source(source_summary, subject):
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

    identity_settings = _runtime_identity_extractor_settings()
    identity_model = str(identity_settings['model'])
    system_prompt = _load_prompt(config.IDENTITY_EXTRACTOR_PROMPT_PATH, 'identity_extractor')
    if not system_prompt:
        return []

    admissible_turns, source_summary = identity_temporal_guard.admissible_turns_with_source_summary(
        recent_turns
    )
    dialogue = '\n'.join(
        f"{t.get('role', '?').upper()}: {t.get('content', '')}"
        for t in admissible_turns
    )
    temporal_policy = (
        "Temporal identity policy:\n"
        "- Relative claims such as aujourd'hui, hier, depuis hier, en ce moment, "
        "right now or currently are weak situational signals.\n"
        "- Source turns containing those weak signals are removed from the admissible identity dialogue.\n"
        "- Do not extract them as identity entries; prefer no entry.\n\n"
        f"Temporal source summary:\n{json.dumps(source_summary, ensure_ascii=False, indent=2)}\n\n"
    )
    payload = {
        'model': identity_model,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': f'{temporal_policy}Here is the admissible dialogue:\\n\\n{dialogue}'},
        ],
        'temperature': float(identity_settings['temperature']),
        'top_p': float(identity_settings['top_p']),
        'max_tokens': int(identity_settings['max_tokens']),
    }
    payload = llm_client.with_provider_attribution(payload, caller='identity_extractor')

    try:
        response = requests.post(
            llm_client.or_chat_completions_url(),
            json=payload,
            headers=llm_client.or_headers(caller='identity_extractor'),
            timeout=int(identity_settings['timeout_s']),
        )
        response.raise_for_status()
        response_payload = llm_client.read_openrouter_response_payload(response)
        llm_client.log_provider_metadata(
            logger,
            'identity_extractor_provider_response',
            llm_client.extract_openrouter_provider_metadata(
                response_payload,
                requested_model=identity_model,
            ),
        )
        raw = llm_client.extract_openrouter_text(response_payload)
        result = _safe_json_loads(raw)
        entries = _validate_identity_output(result, source_summary=source_summary)
        logger.info('identity_extracted count=%s', len(entries))
        return entries
    except requests.exceptions.Timeout:
        logger.warning('identity_extractor_timeout model=%s', identity_model)
        return []
    except requests.exceptions.RequestException as exc:
        parse_count = _inc_metric('identity_parse_error_count')
        logger.error(
            'identity_extractor_error reason=provider_transport_error '
            'err_class=%s parse_error_count=%s',
            exc.__class__.__name__,
            parse_count,
        )
        return []
    except Exception as exc:
        parse_count = _inc_metric('identity_parse_error_count')
        logger.error('identity_extractor_error err=%s parse_error_count=%s', exc, parse_count)
        return []


def rewrite_identity_mutables(payload_input: Dict[str, Any]) -> Dict[str, Any] | None:
    _inc_metric('identity_legacy_rewriter_disabled_count')
    if isinstance(payload_input, dict):
        logger.info('identity_legacy_rewriter_retired payload_keys=%s', sorted(payload_input.keys()))
    else:
        logger.info('identity_legacy_rewriter_retired payload_type=%s', payload_input.__class__.__name__)
    return None


def run_identity_periodic_agent(payload_input: Dict[str, Any]) -> Dict[str, Any]:
    logger.info(
        'identity_periodic_agent_disabled reason=legacy_pre_refactor_removed payload_type=%s',
        payload_input.__class__.__name__,
    )
    return {
        'status': 'skipped',
        'reason_code': 'legacy_identity_periodic_agent_disabled',
        'runtime_pipeline': 'mutable_identity_judge_v2_add_only',
        'prompt_kind': 'identity_periodic_agent_legacy_disabled',
        'legacy_writer_disabled': True,
        'legacy_writer_disabled_reason': 'score_first_writer_removed_in_lot6',
        'writes_applied': False,
        'promotion_count': 0,
        'promotions': [],
        'outcomes': [],
        'rejection_reasons': {},
    }


def run_mutable_identity_judge(payload_input: Dict[str, Any]) -> Dict[str, Any]:
    return mutable_identity_judge_v2.run_mutable_identity_judge_v2(payload_input)
