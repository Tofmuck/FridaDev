from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable, Dict, Mapping, Tuple
from urllib.parse import urlparse

from admin.admin_memory_durable_dashboard import (
    _read_arbiter_persisted_preview,
    _read_durable_state,
)
from admin.admin_memory_history_dashboard import (
    _mode_observation,
    _read_embeddings_summary,
    _read_injection_summary,
    _read_pre_arbiter_summary,
    _read_recent_turns,
    _read_retrieval_summary,
    _stage_latencies,
)
from memory import memory_pre_arbiter_basket


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


def _safe_mapping(value: Any) -> dict[str, Any]:
    if isinstance(value, Mapping):
        return dict(value)
    return {}


def _conn_factory(memory_store_module: Any, log_store_module: Any | None) -> Callable[[], Any]:
    factory = getattr(memory_store_module, '_conn', None)
    if callable(factory):
        return factory
    if log_store_module is not None:
        factory = getattr(log_store_module, '_conn', None)
        if callable(factory):
            return factory
    raise RuntimeError('memory admin connection factory unavailable')


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
