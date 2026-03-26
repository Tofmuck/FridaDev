from __future__ import annotations

from datetime import datetime, timezone
from math import ceil, floor
from typing import Any, Dict, List, Mapping, Tuple


def _percentile(values: List[float], p: float) -> float:
    if not values:
        return 0.0
    vals = sorted(values)
    rank = max(0.0, min(1.0, p)) * (len(vals) - 1)
    lo = int(floor(rank))
    hi = int(ceil(rank))
    if lo == hi:
        return float(vals[lo])
    weight = rank - lo
    return float(vals[lo] * (1.0 - weight) + vals[hi] * weight)


def _compute_stage_latencies(log_entries: List[Dict[str, Any]]) -> Dict[str, Dict[str, float]]:
    buckets: Dict[str, List[float]] = {
        'retrieve': [],
        'arbiter': [],
        'identity_extractor': [],
    }
    for entry in log_entries:
        if entry.get('event') != 'stage_latency':
            continue
        stage = str(entry.get('stage') or '').strip()
        if stage not in buckets:
            continue
        try:
            duration = float(entry.get('duration_ms') or 0.0)
        except (TypeError, ValueError):
            continue
        if duration < 0:
            continue
        buckets[stage].append(duration)

    out: Dict[str, Dict[str, float]] = {}
    for stage, values in buckets.items():
        out[stage] = {
            'count': int(len(values)),
            'p50_ms': round(_percentile(values, 0.50), 3),
            'p95_ms': round(_percentile(values, 0.95), 3),
        }
    return out


def identity_candidates_response(
    args: Mapping[str, Any],
    *,
    memory_store_module: Any,
) -> Tuple[Dict[str, Any], int]:
    raw_limit = args.get('limit', '200')
    try:
        limit = max(1, min(int(raw_limit), 1000))
    except ValueError:
        limit = 200

    raw_subject = str(args.get('subject', 'all') or 'all').strip().lower()
    if raw_subject in {'user', 'llm'}:
        subjects = [raw_subject]
    elif raw_subject in {'all', ''}:
        subjects = ['user', 'llm']
    else:
        return {'ok': False, 'error': 'subject invalide'}, 400

    raw_status = str(args.get('status', 'all') or 'all').strip().lower()
    if raw_status in {'all', ''}:
        status = None
    elif raw_status in {'accepted', 'deferred', 'rejected'}:
        status = raw_status
    else:
        return {'ok': False, 'error': 'status invalide'}, 400

    entries = []
    for subject in subjects:
        entries.extend(memory_store_module.get_identities(subject, top_n=limit, status=status))

    entries.sort(key=lambda e: float(e.get('weight') or 0.0), reverse=True)
    entries = entries[:limit]
    return {'ok': True, 'items': entries, 'count': len(entries)}, 200


def arbiter_decisions_response(
    args: Mapping[str, Any],
    *,
    memory_store_module: Any,
) -> Tuple[Dict[str, Any], int]:
    raw_limit = args.get('limit', '200')
    try:
        limit = max(1, min(int(raw_limit), 1000))
    except ValueError:
        limit = 200

    conversation_id = str(args.get('conversation_id', '') or '').strip() or None
    decisions = memory_store_module.get_arbiter_decisions(limit=limit, conversation_id=conversation_id)
    return {'ok': True, 'items': decisions, 'count': len(decisions)}, 200


def _identity_override_response(
    *,
    action: str,
    override_state: str,
    data: Mapping[str, Any],
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[Dict[str, Any], int]:
    identity_id = str(data.get('identity_id') or '').strip()
    reason = str(data.get('reason') or '').strip()
    actor = str(data.get('actor') or 'admin').strip() or 'admin'
    if not identity_id:
        return {'ok': False, 'error': 'identity_id manquant'}, 400

    ok = memory_store_module.set_identity_override(
        identity_id,
        action,
        reason=reason,
        actor=actor,
    )
    if not ok:
        return {'ok': False, 'error': 'identity introuvable'}, 404

    admin_logs_module.log_event(
        'identity_override',
        action=action,
        identity_id=identity_id,
        actor=actor,
    )
    return {'ok': True, 'identity_id': identity_id, 'override_state': override_state}, 200


def identity_force_accept_response(
    data: Mapping[str, Any],
    *,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[Dict[str, Any], int]:
    return _identity_override_response(
        action='force_accept',
        override_state='force_accept',
        data=data,
        memory_store_module=memory_store_module,
        admin_logs_module=admin_logs_module,
    )


def identity_force_reject_response(
    data: Mapping[str, Any],
    *,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[Dict[str, Any], int]:
    return _identity_override_response(
        action='force_reject',
        override_state='force_reject',
        data=data,
        memory_store_module=memory_store_module,
        admin_logs_module=admin_logs_module,
    )


def identity_relabel_response(
    data: Mapping[str, Any],
    *,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> Tuple[Dict[str, Any], int]:
    identity_id = str(data.get('identity_id') or '').strip()
    if not identity_id:
        return {'ok': False, 'error': 'identity_id manquant'}, 400

    stability = data.get('stability')
    utterance_mode = data.get('utterance_mode')
    scope = data.get('scope')
    reason = str(data.get('reason') or '').strip()
    actor = str(data.get('actor') or 'admin').strip() or 'admin'

    allowed_stability = {'durable', 'episodic', 'unknown'}
    allowed_utterance_mode = {
        'self_description',
        'projection',
        'role_play',
        'irony',
        'speculation',
        'unknown',
    }
    allowed_scope = {'user', 'llm', 'situation', 'mixed', 'unknown'}

    if stability is not None and str(stability).strip() not in allowed_stability:
        return {'ok': False, 'error': 'stability invalide'}, 400
    if utterance_mode is not None and str(utterance_mode).strip() not in allowed_utterance_mode:
        return {'ok': False, 'error': 'utterance_mode invalide'}, 400
    if scope is not None and str(scope).strip() not in allowed_scope:
        return {'ok': False, 'error': 'scope invalide'}, 400
    if stability is None and utterance_mode is None and scope is None:
        return {'ok': False, 'error': 'aucun champ a relabel'}, 400

    ok = memory_store_module.relabel_identity(
        identity_id,
        stability=str(stability).strip() if stability is not None else None,
        utterance_mode=str(utterance_mode).strip() if utterance_mode is not None else None,
        scope=str(scope).strip() if scope is not None else None,
        reason=reason,
        actor=actor,
    )
    if not ok:
        return {'ok': False, 'error': 'identity introuvable'}, 404

    admin_logs_module.log_event(
        'identity_relabel',
        identity_id=identity_id,
        actor=actor,
        stability=stability,
        utterance_mode=utterance_mode,
        scope=scope,
    )
    return {'ok': True, 'identity_id': identity_id}, 200


def dashboard_response(
    args: Mapping[str, Any],
    *,
    memory_store_module: Any,
    arbiter_module: Any,
    admin_logs_module: Any,
    config_module: Any,
) -> Tuple[Dict[str, Any], int]:
    raw_window_days = args.get('window_days', '7')
    raw_log_limit = args.get('log_limit', '5000')

    try:
        window_days = max(1, min(int(raw_window_days), 365))
    except ValueError:
        window_days = 7

    try:
        log_limit = max(100, min(int(raw_log_limit), 10000))
    except ValueError:
        log_limit = 5000

    kpis = memory_store_module.get_hermeneutic_kpis(window_days=window_days)
    runtime_metrics = arbiter_module.get_runtime_metrics()

    parse_error_count = int(runtime_metrics.get('arbiter_parse_error_count', 0)) + int(
        runtime_metrics.get('identity_parse_error_count', 0)
    )
    parse_denominator = int(runtime_metrics.get('arbiter_call_count', 0)) + int(
        runtime_metrics.get('identity_extractor_call_count', 0)
    )
    parse_error_rate = (float(parse_error_count) / parse_denominator) if parse_denominator > 0 else 0.0

    runtime_fallback_rate = (
        float(runtime_metrics.get('arbiter_fallback_count', 0))
        / int(runtime_metrics.get('arbiter_call_count', 1) or 1)
    )

    log_entries = admin_logs_module.read_logs(limit=log_limit)
    stage_latencies = _compute_stage_latencies(log_entries)

    fallback_rate = max(float(kpis.get('fallback_rate', 0.0)), runtime_fallback_rate)

    alerts: List[str] = []
    if parse_error_rate > 0.05:
        alerts.append('parse_error_rate_gt_5pct')
    if fallback_rate > 0.10:
        alerts.append('fallback_rate_gt_10pct')

    counters = {
        'identity_accept_count': int(kpis.get('identity_accept_count', 0)),
        'identity_defer_count': int(kpis.get('identity_defer_count', 0)),
        'identity_reject_count': int(kpis.get('identity_reject_count', 0)),
        'identity_override_count': int(kpis.get('identity_override_count', 0)),
        'arbiter_fallback_count': int(kpis.get('arbiter_fallback_count', 0)),
        'parse_error_count': parse_error_count,
    }

    return (
        {
            'ok': True,
            'mode': config_module.HERMENEUTIC_MODE,
            'window_days': window_days,
            'counters': counters,
            'rates': {
                'parse_error_rate': round(parse_error_rate, 6),
                'fallback_rate': round(fallback_rate, 6),
                'runtime_fallback_rate': round(runtime_fallback_rate, 6),
            },
            'latency_ms': stage_latencies,
            'runtime_metrics': runtime_metrics,
            'alerts': alerts,
        },
        200,
    )


def corrections_export_response(
    args: Mapping[str, Any],
    *,
    admin_logs_module: Any,
) -> Tuple[Dict[str, Any], int]:
    raw_window_days = args.get('window_days', '7')
    raw_limit = args.get('limit', '5000')

    try:
        window_days = max(1, min(int(raw_window_days), 365))
    except ValueError:
        window_days = 7

    try:
        limit = max(100, min(int(raw_limit), 20000))
    except ValueError:
        limit = 5000

    cutoff = datetime.now(timezone.utc).timestamp() - (window_days * 86400)
    entries = []
    for item in admin_logs_module.read_logs(limit=limit):
        event = str(item.get('event') or '')
        if event not in {'identity_override', 'identity_relabel'}:
            continue

        ts_raw = str(item.get('timestamp') or '').strip()
        try:
            ts_epoch = datetime.fromisoformat(ts_raw.replace('Z', '+00:00')).timestamp()
        except ValueError:
            continue
        if ts_epoch < cutoff:
            continue

        entries.append(item)

    return {
        'ok': True,
        'window_days': window_days,
        'count': len(entries),
        'items': entries,
    }, 200
