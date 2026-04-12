from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Sequence, Tuple
from urllib.parse import urlparse

from admin import admin_stage_latency_summary
from memory import memory_pre_arbiter_basket

_RECENT_TURN_STAGES = (
    'embedding',
    'memory_retrieve',
    'summaries',
    'arbiter',
    'hermeneutic_node_insertion',
    'prompt_prepared',
    'branch_skipped',
)


def _to_int(value: Any, fallback: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _to_float(value: Any, fallback: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _utc_iso(value: Any) -> str | None:
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    text = str(value or '').strip()
    return text or None


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _safe_sequence(value: Any) -> list[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return list(value)
    return []


def _reason_key(reason: Any, *, max_chars: int = 72) -> str:
    raw = ' '.join(str(reason or '').split())
    if not raw:
        return 'unspecified'
    compact = raw.split('|', 1)[0].strip()
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 3].rstrip() + '...'


def _compact_excerpt(text: Any, *, max_chars: int = 140) -> str:
    raw = ' '.join(str(text or '').split())
    if len(raw) <= max_chars:
        return raw
    return raw[: max_chars - 3].rstrip() + '...'


def _conn_factory(memory_store_module: Any, log_store_module: Any | None) -> Callable[[], Any]:
    factory = getattr(memory_store_module, '_conn', None)
    if callable(factory):
        return factory
    if log_store_module is not None:
        factory = getattr(log_store_module, '_conn', None)
        if callable(factory):
            return factory
    raise RuntimeError('memory admin connection factory unavailable')


def _read_durable_state(
    *,
    conn_factory: Callable[[], Any],
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS with_embedding,
                    COUNT(*) FILTER (WHERE summary_id IS NOT NULL)::int AS with_summary_id,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    COUNT(*) FILTER (WHERE role = 'user')::int AS user_count,
                    COUNT(*) FILTER (WHERE role = 'assistant')::int AS assistant_count,
                    COUNT(*) FILTER (WHERE role = 'summary')::int AS summary_count,
                    MAX(timestamp) AS latest_ts
                FROM traces
                '''
            )
            traces_row = cur.fetchone() or (0, 0, 0, 0, 0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE embedding IS NOT NULL)::int AS with_embedding,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    MAX(end_ts) AS latest_ts
                FROM summaries
                '''
            )
            summaries_row = cur.fetchone() or (0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS total,
                    COUNT(*) FILTER (WHERE keep)::int AS kept_count,
                    COUNT(*) FILTER (WHERE NOT keep)::int AS rejected_count,
                    COUNT(*) FILTER (WHERE decision_source = 'fallback')::int AS fallback_count,
                    COUNT(*) FILTER (WHERE decision_source = 'llm')::int AS llm_count,
                    COUNT(DISTINCT conversation_id)::int AS conversations,
                    MAX(created_ts) AS latest_ts
                FROM arbiter_decisions
                '''
            )
            arbiter_row = cur.fetchone() or (0, 0, 0, 0, 0, 0, None)

            cur.execute(
                '''
                SELECT
                    role,
                    lower(regexp_replace(trim(content), '\\s+', ' ', 'g')) AS normalized_content,
                    COUNT(*)::int AS occurrences
                FROM traces
                WHERE trim(content) <> ''
                GROUP BY role, lower(regexp_replace(trim(content), '\\s+', ' ', 'g'))
                HAVING COUNT(*) > 1
                ORDER BY occurrences DESC, normalized_content ASC
                LIMIT 5
                '''
            )
            duplicate_rows = cur.fetchall()

            cur.execute(
                '''
                SELECT reason, COUNT(*)::int AS occurrences
                FROM arbiter_decisions
                WHERE NOT keep
                GROUP BY reason
                ORDER BY COUNT(*) DESC, reason ASC
                LIMIT 5
                '''
            )
            rejection_rows = cur.fetchall()

    return {
        'source_kind': 'durable_persistence',
        'traces': {
            'total': _to_int(traces_row[0]),
            'with_embedding': _to_int(traces_row[1]),
            'with_summary_id': _to_int(traces_row[2]),
            'conversations': _to_int(traces_row[3]),
            'by_role': {
                'user': _to_int(traces_row[4]),
                'assistant': _to_int(traces_row[5]),
                'summary': _to_int(traces_row[6]),
            },
            'latest_ts': _utc_iso(traces_row[7]),
            'duplicate_examples': [
                {
                    'role': str(row[0] or ''),
                    'occurrences': _to_int(row[2]),
                    'content_excerpt': _compact_excerpt(row[1]),
                }
                for row in duplicate_rows
            ],
        },
        'summaries': {
            'total': _to_int(summaries_row[0]),
            'with_embedding': _to_int(summaries_row[1]),
            'conversations': _to_int(summaries_row[2]),
            'latest_ts': _utc_iso(summaries_row[3]),
        },
        'arbiter_decisions': {
            'total': _to_int(arbiter_row[0]),
            'kept_count': _to_int(arbiter_row[1]),
            'rejected_count': _to_int(arbiter_row[2]),
            'fallback_count': _to_int(arbiter_row[3]),
            'llm_count': _to_int(arbiter_row[4]),
            'conversations': _to_int(arbiter_row[5]),
            'latest_ts': _utc_iso(arbiter_row[6]),
            'top_rejection_reasons': {
                _reason_key(row[0]): _to_int(row[1])
                for row in rejection_rows
            },
        },
    }


def _read_retrieval_summary(
    *,
    conn_factory: Callable[[], Any],
    window_days: int,
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS events_count,
                    COUNT(DISTINCT conversation_id || '::' || turn_id)::int AS turns_observed,
                    MAX(ts) AS latest_ts,
                    AVG(NULLIF(payload_json->>'top_k_requested', '')::double precision) AS avg_top_k_requested,
                    AVG(NULLIF(payload_json->>'top_k_returned', '')::double precision) AS avg_top_k_returned,
                    AVG(NULLIF(payload_json->>'dense_candidates_count', '')::double precision) AS avg_dense_candidates,
                    AVG(NULLIF(payload_json->>'lexical_candidates_count', '')::double precision) AS avg_lexical_candidates,
                    AVG(NULLIF(payload_json->>'summary_candidates_count', '')::double precision) AS avg_summary_candidates
                FROM observability.chat_log_events
                WHERE stage = 'memory_retrieve'
                  AND ts >= (now() - make_interval(days => %s))
                ''',
                (window_days,),
            )
            row = cur.fetchone() or (0, 0, None, None, None, None, None, None)

    return {
        'config_source_kind': 'calculated_aggregate',
        'activity_source_kind': 'historical_logs',
        'recent_activity': {
            'window_days': window_days,
            'events_count': _to_int(row[0]),
            'turns_observed': _to_int(row[1]),
            'latest_ts': _utc_iso(row[2]),
            'avg_top_k_requested': round(_to_float(row[3]), 3),
            'avg_top_k_returned': round(_to_float(row[4]), 3),
            'avg_dense_candidates': round(_to_float(row[5]), 3),
            'avg_lexical_candidates': round(_to_float(row[6]), 3),
            'avg_summary_candidates': round(_to_float(row[7]), 3),
        },
    }


def _read_embeddings_summary(
    *,
    conn_factory: Callable[[], Any],
    window_days: int,
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COALESCE(NULLIF(payload_json->>'source_kind', ''), 'unknown') AS source_kind,
                    COUNT(*)::int AS events_count,
                    MAX(ts) AS latest_ts
                FROM observability.chat_log_events
                WHERE stage = 'embedding'
                  AND ts >= (now() - make_interval(days => %s))
                GROUP BY source_kind
                ORDER BY events_count DESC, source_kind ASC
                ''',
                (window_days,),
            )
            rows = cur.fetchall()

    total = sum(_to_int(row[1]) for row in rows)
    latest_ts = None
    for row in rows:
        candidate = _utc_iso(row[2])
        if candidate and (latest_ts is None or candidate > latest_ts):
            latest_ts = candidate

    return {
        'settings_source_kind': 'calculated_aggregate',
        'activity_source_kind': 'historical_logs',
        'recent_activity': {
            'window_days': window_days,
            'total_events': total,
            'latest_ts': latest_ts,
            'by_source_kind': {
                str(row[0] or 'unknown'): _to_int(row[1])
                for row in rows
            },
        },
    }


def _read_pre_arbiter_summary(
    *,
    conn_factory: Callable[[], Any],
    window_days: int,
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS events_count,
                    COUNT(DISTINCT conversation_id || '::' || turn_id)::int AS turns_observed,
                    MAX(ts) AS latest_ts,
                    AVG(NULLIF(payload_json->'inputs'->'memory_arbitration'->>'raw_candidates_count', '')::double precision) AS avg_raw_candidates,
                    AVG(NULLIF(payload_json->'inputs'->'memory_arbitration'->>'basket_candidates_count', '')::double precision) AS avg_basket_candidates,
                    AVG(NULLIF(payload_json->'inputs'->'memory_arbitration'->>'decisions_count', '')::double precision) AS avg_decisions,
                    AVG(NULLIF(payload_json->'inputs'->'memory_arbitration'->>'kept_count', '')::double precision) AS avg_kept,
                    AVG(NULLIF(payload_json->'inputs'->'memory_arbitration'->>'rejected_count', '')::double precision) AS avg_rejected
                FROM observability.chat_log_events
                WHERE stage = 'hermeneutic_node_insertion'
                  AND ts >= (now() - make_interval(days => %s))
                ''',
                (window_days,),
            )
            summary_row = cur.fetchone() or (0, 0, None, None, None, None, None, None)

            cur.execute(
                '''
                SELECT
                    COALESCE(NULLIF(payload_json->>'decision_source', ''), 'unknown') AS decision_source,
                    COUNT(*)::int AS events_count
                FROM observability.chat_log_events
                WHERE stage = 'arbiter'
                  AND ts >= (now() - make_interval(days => %s))
                GROUP BY decision_source
                ORDER BY events_count DESC, decision_source ASC
                ''',
                (window_days,),
            )
            decision_rows = cur.fetchall()

    return {
        'contract_source_kind': 'calculated_aggregate',
        'recent_activity_source_kind': 'historical_logs',
        'contract': {
            'basket_limit': memory_pre_arbiter_basket.PRE_ARBITER_MAX_CANDIDATES,
            'dedup_reason_codes': [
                'exact_duplicate',
                'lexical_near_duplicate',
                'same_conversation_same_idea',
                'trace_summary_collision',
            ],
            'contract_doc_path': 'app/docs/states/specs/memory-rag-pre-arbiter-basket-contract.md',
        },
        'recent_activity': {
            'window_days': window_days,
            'events_count': _to_int(summary_row[0]),
            'turns_observed': _to_int(summary_row[1]),
            'latest_ts': _utc_iso(summary_row[2]),
            'avg_raw_candidates': round(_to_float(summary_row[3]), 3),
            'avg_basket_candidates': round(_to_float(summary_row[4]), 3),
            'avg_decisions': round(_to_float(summary_row[5]), 3),
            'avg_kept': round(_to_float(summary_row[6]), 3),
            'avg_rejected': round(_to_float(summary_row[7]), 3),
            'decision_source_counts': {
                str(row[0] or 'unknown'): _to_int(row[1])
                for row in decision_rows
            },
        },
    }


def _read_injection_summary(
    *,
    conn_factory: Callable[[], Any],
    window_days: int,
) -> dict[str, Any]:
    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                '''
                SELECT
                    COUNT(*)::int AS events_count,
                    COUNT(*) FILTER (
                        WHERE COALESCE(payload_json->'memory_prompt_injection'->>'injected', 'false') = 'true'
                    )::int AS injected_turns,
                    MAX(ts) AS latest_ts,
                    AVG(NULLIF(payload_json->'memory_prompt_injection'->>'memory_traces_injected_count', '')::double precision) AS avg_trace_count,
                    AVG(NULLIF(payload_json->'memory_prompt_injection'->>'memory_context_summary_count', '')::double precision) AS avg_summary_count,
                    AVG(NULLIF(payload_json->'memory_prompt_injection'->>'context_hints_injected_count', '')::double precision) AS avg_hint_count
                FROM observability.chat_log_events
                WHERE stage = 'prompt_prepared'
                  AND ts >= (now() - make_interval(days => %s))
                ''',
                (window_days,),
            )
            summary_row = cur.fetchone() or (0, 0, None, None, None, None)

            cur.execute(
                '''
                SELECT payload_json->'memory_prompt_injection'
                FROM observability.chat_log_events
                WHERE stage = 'prompt_prepared'
                  AND COALESCE(payload_json->'memory_prompt_injection'->>'injected', 'false') = 'true'
                ORDER BY ts DESC, event_id DESC
                LIMIT 1
                '''
            )
            latest_row = cur.fetchone()

    latest_payload = _safe_mapping(latest_row[0]) if latest_row else {}
    return {
        'source_kind': 'historical_logs',
        'recent_activity': {
            'window_days': window_days,
            'events_count': _to_int(summary_row[0]),
            'injected_turns': _to_int(summary_row[1]),
            'latest_ts': _utc_iso(summary_row[2]),
            'avg_memory_traces_injected_count': round(_to_float(summary_row[3]), 3),
            'avg_memory_context_summary_count': round(_to_float(summary_row[4]), 3),
            'avg_context_hints_injected_count': round(_to_float(summary_row[5]), 3),
            'latest_injected_candidate_ids': [
                str(item).strip()
                for item in _safe_sequence(latest_payload.get('injected_candidate_ids'))
                if str(item).strip()
            ],
        },
    }


def _event_summary_from_payload(stage: str, payload: Mapping[str, Any]) -> dict[str, Any]:
    data = _safe_mapping(payload)
    if stage == 'embedding':
        return {
            'source_kind': str(data.get('source_kind') or ''),
            'mode': str(data.get('mode') or ''),
            'provider': str(data.get('provider') or ''),
            'dimensions': _to_int(data.get('dimensions')),
        }
    if stage == 'memory_retrieve':
        return {
            'top_k_requested': _to_int(data.get('top_k_requested')),
            'top_k_returned': _to_int(data.get('top_k_returned')),
            'dense_candidates_count': _to_int(data.get('dense_candidates_count')),
            'lexical_candidates_count': _to_int(data.get('lexical_candidates_count')),
            'summary_candidates_count': _to_int(data.get('summary_candidates_count')),
        }
    if stage == 'summaries':
        return {
            'active_summary_present': bool(data.get('active_summary_present')),
            'summary_count_used': _to_int(data.get('summary_count_used')),
            'summary_usage': str(data.get('summary_usage') or ''),
            'in_prompt': bool(data.get('in_prompt')),
            'summary_generation_observed': bool(data.get('summary_generation_observed')),
        }
    if stage == 'arbiter':
        return {
            'raw_candidates': _to_int(data.get('raw_candidates')),
            'kept_candidates': _to_int(data.get('kept_candidates')),
            'rejected_candidates': _to_int(data.get('rejected_candidates')),
            'decision_source': str(data.get('decision_source') or ''),
            'fallback_used': bool(data.get('fallback_used')),
            'model': str(data.get('model') or ''),
        }
    if stage == 'prompt_prepared':
        injection = _safe_mapping(data.get('memory_prompt_injection'))
        return {
            'injected': bool(injection.get('injected')),
            'memory_traces_injected_count': _to_int(injection.get('memory_traces_injected_count')),
            'memory_context_summary_count': _to_int(injection.get('memory_context_summary_count')),
            'context_hints_injected_count': _to_int(injection.get('context_hints_injected_count')),
            'injected_candidate_ids': [
                str(item).strip()
                for item in _safe_sequence(injection.get('injected_candidate_ids'))
                if str(item).strip()
            ],
        }
    if stage == 'hermeneutic_node_insertion':
        inputs = _safe_mapping(data.get('inputs'))
        retrieved = _safe_mapping(inputs.get('memory_retrieved'))
        arbitration = _safe_mapping(inputs.get('memory_arbitration'))
        return {
            'retrieved_count': _to_int(retrieved.get('retrieved_count')),
            'basket_candidates_count': _to_int(arbitration.get('basket_candidates_count')),
            'decisions_count': _to_int(arbitration.get('decisions_count')),
            'kept_count': _to_int(arbitration.get('kept_count')),
            'rejected_count': _to_int(arbitration.get('rejected_count')),
            'status': str(arbitration.get('status') or ''),
            'injected_candidate_ids': [
                str(item).strip()
                for item in _safe_sequence(arbitration.get('injected_candidate_ids'))
                if str(item).strip()
            ],
        }
    if stage == 'branch_skipped':
        return {
            'reason_code': str(data.get('reason_code') or ''),
            'reason_short': str(data.get('reason_short') or ''),
        }
    return {}


def _read_recent_turns(
    *,
    conn_factory: Callable[[], Any],
    turn_limit: int,
) -> dict[str, Any]:
    stages = _RECENT_TURN_STAGES
    placeholders = ', '.join(['%s'] * len(stages))
    sample_limit = max(turn_limit * 8, 64)

    with conn_factory() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f'''
                SELECT conversation_id, turn_id, ts, stage, status, payload_json
                FROM observability.chat_log_events
                WHERE stage IN ({placeholders})
                ORDER BY ts DESC, event_id DESC
                LIMIT %s
                ''',
                (*stages, sample_limit),
            )
            rows = cur.fetchall()

    turns: list[dict[str, Any]] = []
    turns_by_key: dict[str, dict[str, Any]] = {}
    for conversation_id, turn_id, ts, stage, status, payload_json in rows:
        key = f'{conversation_id}::{turn_id}'
        if key not in turns_by_key:
            if len(turns) >= turn_limit:
                continue
            turn_payload = {
                'conversation_id': str(conversation_id or ''),
                'turn_id': str(turn_id or ''),
                'latest_ts': _utc_iso(ts),
                'stages': {},
            }
            turns_by_key[key] = turn_payload
            turns.append(turn_payload)
        turn_payload = turns_by_key[key]
        stage_key = str(stage or '').strip()
        if stage_key in turn_payload['stages']:
            continue
        turn_payload['stages'][stage_key] = {
            'status': str(status or ''),
            'payload': _event_summary_from_payload(stage_key, _safe_mapping(payload_json)),
        }

    return {
        'source_kind': 'historical_logs',
        'items': turns,
    }


def _read_arbiter_persisted_preview(
    *,
    memory_store_module: Any,
    limit: int,
) -> dict[str, Any]:
    items = memory_store_module.get_arbiter_decisions(limit=limit)
    return {
        'source_kind': 'durable_persistence',
        'items': items,
        'count': len(items),
    }


def _embedding_settings_summary(runtime_settings_module: Any) -> dict[str, Any]:
    view = runtime_settings_module.get_embedding_settings()
    payload = _safe_mapping(view.payload)
    endpoint = str(_safe_mapping(payload.get('endpoint')).get('value') or '')
    return {
        'model': str(_safe_mapping(payload.get('model')).get('value') or ''),
        'endpoint_host': urlparse(endpoint).netloc or endpoint,
        'dimensions': _to_int(_safe_mapping(payload.get('dimensions')).get('value')),
        'top_k': _to_int(_safe_mapping(payload.get('top_k')).get('value')),
        'token_configured': bool(_safe_mapping(payload.get('token')).get('is_set')),
    }


def _arbiter_settings_summary(runtime_settings_module: Any, config_module: Any) -> dict[str, Any]:
    view = runtime_settings_module.get_arbiter_model_settings()
    payload = _safe_mapping(view.payload)
    return {
        'model': str(_safe_mapping(payload.get('model')).get('value') or ''),
        'timeout_s': _to_int(_safe_mapping(payload.get('timeout_s')).get('value')),
        'min_semantic_relevance': _to_float(getattr(config_module, 'ARBITER_MIN_SEMANTIC_RELEVANCE', 0.0)),
        'min_contextual_gain': _to_float(getattr(config_module, 'ARBITER_MIN_CONTEXTUAL_GAIN', 0.0)),
        'max_kept_traces': _to_int(getattr(config_module, 'ARBITER_MAX_KEPT_TRACES', 0)),
        'reranker_status': 'no_go_for_now',
        'reranker_decision_doc': 'app/docs/states/project/memory-rag-reranker-decision-2026-04-11.md',
    }


def _mode_observation(current_mode: str, admin_logs_module: Any) -> dict[str, Any]:
    summarize = getattr(admin_logs_module, 'summarize_hermeneutic_mode_observation', None)
    if callable(summarize):
        return summarize(current_mode)
    return {
        'source': 'unavailable',
        'semantics': 'current_mode_observed_segment_not_exact_switch',
        'current_mode_observed': False,
        'observed_since': None,
        'last_observed_at': None,
        'observation_count': 0,
        'previous_mode': None,
        'previous_mode_last_observed_at': None,
        'latest_observed_mode': None,
        'latest_observed_at': None,
        'exact_switch_known': False,
    }


def _stage_latencies(admin_logs_module: Any) -> dict[str, Any]:
    logs = admin_logs_module.read_logs(limit=5000)
    return admin_stage_latency_summary.compute_stage_latencies(logs)


def _section_with_fallback(
    *,
    label: str,
    builder: Callable[[], dict[str, Any]],
    default: dict[str, Any],
    read_errors: list[dict[str, str]],
) -> dict[str, Any]:
    try:
        return builder()
    except Exception as exc:
        read_errors.append(
            {
                'section': label,
                'error_class': exc.__class__.__name__,
                'message': str(exc),
            }
        )
        return default


def dashboard_response(
    args: Mapping[str, Any],
    *,
    memory_store_module: Any,
    arbiter_module: Any,
    admin_logs_module: Any,
    runtime_settings_module: Any,
    config_module: Any,
    log_store_module: Any | None = None,
) -> Tuple[Dict[str, Any], int]:
    raw_window_days = args.get('window_days', '7')
    raw_turn_limit = args.get('turn_limit', '8')
    raw_preview_limit = args.get('preview_limit', '12')

    try:
        window_days = max(1, min(int(raw_window_days), 365))
    except ValueError:
        return {'ok': False, 'error': 'window_days invalide'}, 400

    try:
        turn_limit = max(1, min(int(raw_turn_limit), 20))
    except ValueError:
        return {'ok': False, 'error': 'turn_limit invalide'}, 400

    try:
        preview_limit = max(1, min(int(raw_preview_limit), 25))
    except ValueError:
        return {'ok': False, 'error': 'preview_limit invalide'}, 400

    conn_factory = _conn_factory(memory_store_module, log_store_module)
    current_mode = str(config_module.HERMENEUTIC_MODE or '').strip().lower()
    read_errors: list[dict[str, str]] = []

    durable_state = _section_with_fallback(
        label='durable_state',
        builder=lambda: _read_durable_state(conn_factory=conn_factory),
        default={
            'source_kind': 'durable_persistence',
            'traces': {},
            'summaries': {},
            'arbiter_decisions': {},
        },
        read_errors=read_errors,
    )
    retrieval = _section_with_fallback(
        label='retrieval',
        builder=lambda: _read_retrieval_summary(conn_factory=conn_factory, window_days=window_days),
        default={
            'config_source_kind': 'calculated_aggregate',
            'activity_source_kind': 'historical_logs',
            'recent_activity': {},
        },
        read_errors=read_errors,
    )
    embeddings = _section_with_fallback(
        label='embeddings',
        builder=lambda: _read_embeddings_summary(conn_factory=conn_factory, window_days=window_days),
        default={
            'settings_source_kind': 'calculated_aggregate',
            'activity_source_kind': 'historical_logs',
            'recent_activity': {},
        },
        read_errors=read_errors,
    )
    pre_arbiter_basket = _section_with_fallback(
        label='pre_arbiter_basket',
        builder=lambda: _read_pre_arbiter_summary(conn_factory=conn_factory, window_days=window_days),
        default={
            'contract_source_kind': 'calculated_aggregate',
            'recent_activity_source_kind': 'historical_logs',
            'contract': {},
            'recent_activity': {},
        },
        read_errors=read_errors,
    )
    injection = _section_with_fallback(
        label='injection',
        builder=lambda: _read_injection_summary(conn_factory=conn_factory, window_days=window_days),
        default={
            'source_kind': 'historical_logs',
            'recent_activity': {},
        },
        read_errors=read_errors,
    )
    recent_turns = _section_with_fallback(
        label='recent_turns',
        builder=lambda: _read_recent_turns(conn_factory=conn_factory, turn_limit=turn_limit),
        default={
            'source_kind': 'historical_logs',
            'items': [],
        },
        read_errors=read_errors,
    )
    arbiter_preview = _section_with_fallback(
        label='arbiter_preview',
        builder=lambda: _read_arbiter_persisted_preview(
            memory_store_module=memory_store_module,
            limit=preview_limit,
        ),
        default={
            'source_kind': 'durable_persistence',
            'items': [],
            'count': 0,
        },
        read_errors=read_errors,
    )

    retrieval['config'] = {
        'top_k': _embedding_settings_summary(runtime_settings_module)['top_k'],
        'basket_limit': memory_pre_arbiter_basket.PRE_ARBITER_MAX_CANDIDATES,
        'summary_lane_live': _to_int(_safe_mapping(durable_state.get('summaries')).get('total')) > 0,
    }

    embeddings['settings'] = _embedding_settings_summary(runtime_settings_module)

    arbiter = {
        'settings_source_kind': 'calculated_aggregate',
        'runtime_source_kind': 'runtime_process_local',
        'durable_source_kind': 'durable_persistence',
        'admin_logs_source_kind': 'historical_logs',
        'settings': _arbiter_settings_summary(runtime_settings_module, config_module),
        'mode_observation': _mode_observation(current_mode, admin_logs_module),
        'runtime_metrics': arbiter_module.get_runtime_metrics(),
        'latency_ms': _stage_latencies(admin_logs_module),
        'persisted_summary': _safe_mapping(durable_state.get('arbiter_decisions')),
        'preview': arbiter_preview,
    }

    return (
        {
            'ok': True,
            'surface': {
                'name': 'Memory Admin',
                'route': '/memory-admin',
                'api_route': '/api/admin/memory/dashboard',
                'generated_at': _utc_now_iso(),
                'reranker_decision': 'no_go_for_now',
                'reranker_decision_doc': 'app/docs/states/project/memory-rag-reranker-decision-2026-04-11.md',
            },
            'overview': {
                'mode': current_mode,
                'window_days': window_days,
                'turn_limit': turn_limit,
                'summary': (
                    'Surface dediee a l observabilite memoire/RAG, distincte de /admin et '
                    '/hermeneutic-admin, avec separation explicite entre durable, agrege, '
                    'runtime process-local et logs.'
                ),
                'notes': [
                    'Pas de reranker actif: decision documentaire no-go for now.',
                    'Le detail timeline brut reste sur /log.',
                    'Le detail identity et pipeline hermeneutique reste sur /hermeneutic-admin.',
                ],
            },
            'scope': {
                'dedicated_surface': True,
                'kept_elsewhere': [
                    {
                        'label': 'Logs applicatifs',
                        'route': '/log',
                        'reason': 'timeline brute, filtres, export et suppression scopes',
                    },
                    {
                        'label': 'Hermeneutic admin',
                        'route': '/hermeneutic-admin',
                        'reason': 'detail identity et pipeline hermeneutique tour par tour',
                    },
                    {
                        'label': 'Identity',
                        'route': '/identity',
                        'reason': 'pilotage canonique des couches identitaires',
                    },
                ],
            },
            'sources_legend': [
                {
                    'key': 'durable_persistence',
                    'label': 'Persistance durable',
                    'description': 'Etat en base: tables traces, summaries et arbiter_decisions.',
                },
                {
                    'key': 'calculated_aggregate',
                    'label': 'Agregat calcule',
                    'description': 'Synthese derivee de settings runtime, regroupements SQL et contracts documentaires.',
                },
                {
                    'key': 'runtime_process_local',
                    'label': 'Runtime process-local',
                    'description': 'Compteurs en memoire du process Python courant, non historises durablement.',
                },
                {
                    'key': 'historical_logs',
                    'label': 'Historique logs',
                    'description': 'Evenements historises dans observability.chat_log_events ou admin_logs.',
                },
            ],
            'durable_state': durable_state,
            'retrieval': retrieval,
            'embeddings': embeddings,
            'pre_arbiter_basket': pre_arbiter_basket,
            'arbiter': arbiter,
            'injection': injection,
            'recent_turns': recent_turns,
            'read_errors': read_errors,
        },
        200,
    )
