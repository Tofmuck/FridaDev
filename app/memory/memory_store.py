from __future__ import annotations

"""Public memory facade.

This module stays the stable import surface for callers (`from memory import memory_store`)
while implementation blocks live in dedicated pipeline-first modules.
"""

import logging
import re
import time
from typing import Any, Optional, Sequence
from urllib.parse import urlparse

import psycopg
import requests

import config
from admin import runtime_settings
from core import runtime_db_bootstrap
from identity import identity_governance
from observability import chat_turn_logger
from observability import log_store
from memory import memory_arbiter_audit
from memory import hermeneutics_policy as policy
from memory import memory_context_read
from memory import memory_identity_dynamics
from memory import memory_identity_staging
from memory import memory_identity_read_model
from memory import memory_identity_mutables
from memory import memory_identity_write
from memory import memory_store_infra
from memory import memory_traces_summaries

logger = logging.getLogger('frida.memory_store')

__all__ = [
    'init_db',
    'embed',
    'save_new_traces',
    'retrieve',
    'save_summary',
    'update_traces_summary_id',
    'get_summary_for_trace',
    'enrich_traces_with_summaries',
    'get_mutable_identity',
    'list_mutable_identities',
    'upsert_mutable_identity',
    'clear_mutable_identity',
    'get_identity_staging_state',
    'append_identity_staging_pair',
    'mark_identity_staging_status',
    'clear_identity_staging_buffer',
    'list_identity_fragments',
    'list_identity_evidence',
    'list_identity_conflicts',
    'get_identities',
    'get_recent_context_hints',
    'get_hermeneutic_kpis',
    'get_arbiter_decisions',
    'record_arbiter_decisions',
    'set_identity_override',
    'relabel_identity',
    'record_identity_evidence',
    'add_identity',
    'detect_and_record_conflicts',
    'preview_identity_entries',
    'persist_identity_entries',
    'decay_identities',
    'reactivate_identities',
]


# Infra + private compatibility hooks used by legacy tests/monkeypatches.

def _conn():
    return memory_store_infra.connect_runtime_database(
        psycopg_module=psycopg,
        config_module=config,
        runtime_settings_module=runtime_settings,
        runtime_db_bootstrap_module=runtime_db_bootstrap,
    )


def _runtime_database_view() -> runtime_settings.RuntimeSectionView:
    return memory_store_infra.runtime_database_view(
        runtime_settings_module=runtime_settings,
        runtime_db_bootstrap_module=runtime_db_bootstrap,
    )


def _runtime_database_backend() -> str:
    return memory_store_infra.runtime_database_backend(
        runtime_settings_module=runtime_settings,
        runtime_db_bootstrap_module=runtime_db_bootstrap,
    )


def _bootstrap_database_dsn() -> str:
    return memory_store_infra.bootstrap_database_dsn(
        config_module=config,
        runtime_settings_module=runtime_settings,
        runtime_db_bootstrap_module=runtime_db_bootstrap,
    )


def _normalize_identity_content(content: str) -> str:
    return re.sub(r'\s+', ' ', (content or '').strip().lower())


def _trace_float(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _runtime_embedding_view() -> runtime_settings.RuntimeSectionView:
    return memory_store_infra.runtime_embedding_view(
        runtime_settings_module=runtime_settings,
    )


def _runtime_embedding_value(field: str) -> Any:
    return memory_store_infra.runtime_embedding_value(
        field,
        runtime_settings_module=runtime_settings,
    )


def _runtime_embedding_token() -> str:
    return memory_store_infra.runtime_embedding_token(
        runtime_settings_module=runtime_settings,
    )


# Schema initialization

def init_db() -> None:
    memory_store_infra.init_db(
        conn_factory=_conn,
        runtime_embedding_value_fn=_runtime_embedding_value,
        logger=logger,
    )
    log_store.init_log_storage(conn_factory=_conn)


# Embedding

def _normalize_embedding_source_kind(*, purpose: str | None, mode: str) -> str:
    normalized = str(purpose or '').strip().lower()
    if normalized in {
        'query',
        'trace_user',
        'trace_assistant',
        'summary',
        'identity_conflict_current',
        'identity_conflict_candidate',
    }:
        return normalized
    if str(mode).strip().lower() == 'query':
        return 'query'
    return 'unknown'


def embed(text: str, mode: str = 'passage', purpose: str | None = None) -> list[float]:
    started_at = time.perf_counter()
    provider = 'unknown'
    dimensions = 0
    source_kind = _normalize_embedding_source_kind(purpose=purpose, mode=mode)
    try:
        endpoint = str(_runtime_embedding_value('endpoint') or '')
        provider = urlparse(endpoint).netloc or endpoint
        dimensions = int(_runtime_embedding_value('dimensions'))
        vector = memory_store_infra.embed(
            text,
            mode=mode,
            runtime_embedding_value_fn=_runtime_embedding_value,
            runtime_embedding_token_fn=_runtime_embedding_token,
            requests_module=requests,
        )
    except Exception as exc:
        chat_turn_logger.emit(
            'embedding',
            status='error',
            duration_ms=(time.perf_counter() - started_at) * 1000.0,
            error_code='upstream_error',
            payload={
                'mode': mode,
                'source_kind': source_kind,
                'provider': provider,
                'dimensions': dimensions,
                'error_class': exc.__class__.__name__,
            },
        )
        raise

    chat_turn_logger.emit(
        'embedding',
        status='ok',
        duration_ms=(time.perf_counter() - started_at) * 1000.0,
        payload={
            'mode': mode,
            'source_kind': source_kind,
            'provider': provider,
            'dimensions': dimensions,
        },
    )
    return vector


# Trace persistence

def _trace_exists_for_message(conversation_id: str, message: dict[str, Any]) -> bool:
    return memory_traces_summaries._trace_exists_for_message(
        conversation_id,
        message,
        conn_factory=_conn,
        logger=logger,
    )

def save_new_traces(conversation: dict[str, Any]) -> None:
    memory_traces_summaries.save_new_traces(
        conversation,
        conn_factory=_conn,
        embed_fn=embed,
        logger=logger,
    )


# Retrieval

def retrieve(query: str, top_k: Optional[int] = None) -> list[dict[str, Any]]:
    return memory_traces_summaries.retrieve(
        query,
        top_k=top_k,
        runtime_embedding_value_fn=_runtime_embedding_value,
        conn_factory=_conn,
        embed_fn=embed,
        logger=logger,
    )


def retrieve_for_arbiter(query: str, top_k: Optional[int] = None) -> list[dict[str, Any]]:
    return memory_traces_summaries.retrieve(
        query,
        top_k=top_k,
        include_internal_scores=True,
        include_summary_candidates=True,
        runtime_embedding_value_fn=_runtime_embedding_value,
        conn_factory=_conn,
        embed_fn=embed,
        logger=logger,
    )


# Summary persistence

def save_summary(conversation_id: str, summary: dict[str, Any]) -> None:
    memory_traces_summaries.save_summary(
        conversation_id,
        summary,
        conn_factory=_conn,
        embed_fn=embed,
        logger=logger,
    )


# Update trace summary_id

def update_traces_summary_id(
    conversation_id: str,
    summary_id: str,
    start_ts: Optional[str],
    end_ts: Optional[str],
) -> None:
    memory_traces_summaries.update_traces_summary_id(
        conversation_id,
        summary_id,
        start_ts,
        end_ts,
        conn_factory=_conn,
        logger=logger,
    )


# Parent summary for a trace

def get_summary_for_trace(trace: dict[str, Any]) -> Optional[dict[str, Any]]:
    return memory_traces_summaries.get_summary_for_trace(
        trace,
        conn_factory=_conn,
        logger=logger,
    )


def enrich_traces_with_summaries(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return memory_traces_summaries.enrich_traces_with_summaries(
        traces,
        get_summary_for_trace_fn=get_summary_for_trace,
    )


# Identity retrieval

def get_mutable_identity(subject: str) -> dict[str, Any] | None:
    return memory_identity_mutables.get_mutable_identity(
        subject,
        conn_factory=_conn,
        logger=logger,
    )


def list_mutable_identities() -> list[dict[str, Any]]:
    return memory_identity_mutables.list_mutable_identities(
        conn_factory=_conn,
        logger=logger,
    )


def upsert_mutable_identity(
    subject: str,
    content: str,
    source_trace_id: Optional[str] = None,
    *,
    updated_by: str = 'system',
    update_reason: str = '',
) -> dict[str, Any] | None:
    return memory_identity_mutables.upsert_mutable_identity(
        subject,
        content,
        source_trace_id=source_trace_id,
        updated_by=updated_by,
        update_reason=update_reason,
        conn_factory=_conn,
        logger=logger,
    )


def clear_mutable_identity(subject: str) -> dict[str, Any] | None:
    return memory_identity_mutables.clear_mutable_identity(
        subject,
        conn_factory=_conn,
        logger=logger,
    )


def get_identity_staging_state(conversation_id: str) -> dict[str, Any] | None:
    return memory_identity_staging.get_identity_staging_state(
        conversation_id,
        conn_factory=_conn,
        logger=logger,
    )


def append_identity_staging_pair(
    conversation_id: str,
    pair: Any,
    *,
    target_pairs: int = 15,
) -> dict[str, Any] | None:
    return memory_identity_staging.append_identity_staging_pair(
        conversation_id,
        pair,
        target_pairs=target_pairs,
        conn_factory=_conn,
        logger=logger,
    )


def mark_identity_staging_status(
    conversation_id: str,
    *,
    status: str,
    reason: str = '',
    touch_run_ts: bool = False,
    auto_canonization_suspended: bool | None = None,
) -> dict[str, Any] | None:
    return memory_identity_staging.mark_identity_staging_status(
        conversation_id,
        status=status,
        reason=reason,
        touch_run_ts=touch_run_ts,
        auto_canonization_suspended=auto_canonization_suspended,
        conn_factory=_conn,
        logger=logger,
    )


def clear_identity_staging_buffer(
    conversation_id: str,
    *,
    status: str,
    reason: str = '',
    auto_canonization_suspended: bool = False,
) -> dict[str, Any] | None:
    return memory_identity_staging.clear_identity_staging_buffer(
        conversation_id,
        status=status,
        reason=reason,
        auto_canonization_suspended=auto_canonization_suspended,
        conn_factory=_conn,
        logger=logger,
    )


def list_identity_fragments(subject: str, limit: Optional[int] = None) -> dict[str, Any]:
    return memory_identity_read_model.list_identity_fragments(
        subject,
        limit=limit,
        conn_factory=_conn,
        logger=logger,
    )


def list_identity_evidence(subject: str, limit: Optional[int] = None) -> dict[str, Any]:
    return memory_identity_read_model.list_identity_evidence(
        subject,
        limit=limit,
        conn_factory=_conn,
        logger=logger,
    )


def list_identity_conflicts(subject: str, limit: Optional[int] = None) -> dict[str, Any]:
    return memory_identity_read_model.list_identity_conflicts(
        subject,
        limit=limit,
        conn_factory=_conn,
        logger=logger,
    )


# Legacy fragment retrieval

def get_identities(
    subject: str,
    top_n: Optional[int] = None,
    status: Optional[str] = 'accepted',
) -> list[dict[str, Any]]:
    return memory_context_read.get_identities(
        subject,
        top_n=top_n,
        status=status,
        conn_factory=_conn,
        default_top_n=config.IDENTITY_TOP_N,
        logger=logger,
    )


def get_recent_context_hints(
    max_items: Optional[int] = None,
    max_age_days: Optional[int] = None,
    min_confidence: Optional[float] = None,
) -> list[dict[str, Any]]:
    return memory_context_read.get_recent_context_hints(
        max_items=max_items,
        max_age_days=max_age_days,
        min_confidence=min_confidence,
        conn_factory=_conn,
        default_max_items=identity_governance.context_hints_max_items(),
        default_max_age_days=identity_governance.context_hints_max_age_days(),
        default_min_confidence=identity_governance.context_hints_min_confidence(),
        logger=logger,
    )



def get_hermeneutic_kpis(window_days: int = 7) -> dict[str, Any]:
    return memory_arbiter_audit.get_hermeneutic_kpis(
        window_days=window_days,
        conn_factory=_conn,
        logger=logger,
    )


def get_arbiter_decisions(
    limit: int = 200,
    conversation_id: Optional[str] = None,
) -> list[dict[str, Any]]:
    return memory_arbiter_audit.get_arbiter_decisions(
        limit=limit,
        conversation_id=conversation_id,
        conn_factory=_conn,
        logger=logger,
    )


def set_identity_override(
    identity_id: str,
    override_state: str,
    *,
    reason: str = '',
    actor: str = 'admin',
) -> bool:
    return memory_identity_write.set_identity_override(
        identity_id,
        override_state,
        reason=reason,
        actor=actor,
        conn_factory=_conn,
        logger=logger,
    )


def relabel_identity(
    identity_id: str,
    *,
    stability: Optional[str] = None,
    utterance_mode: Optional[str] = None,
    scope: Optional[str] = None,
    reason: str = '',
    actor: str = 'admin',
) -> bool:
    return memory_identity_write.relabel_identity(
        identity_id,
        stability=stability,
        utterance_mode=utterance_mode,
        scope=scope,
        reason=reason,
        actor=actor,
        conn_factory=_conn,
        logger=logger,
    )



# Arbiter decision persistence

def record_arbiter_decisions(
    conversation_id: str,
    traces: list[dict[str, Any]],
    decisions: list[dict[str, Any]],
    *,
    effective_model: str | None = None,
    mode: str | None = None,
) -> None:
    memory_arbiter_audit.record_arbiter_decisions(
        conversation_id,
        traces,
        decisions,
        effective_model=effective_model,
        mode=mode,
        conn_factory=_conn,
        trace_float_fn=_trace_float,
        logger=logger,
    )


# Identity evidence persistence

def record_identity_evidence(
    conversation_id: str,
    entries: list[dict[str, Any]],
    source_trace_id: Optional[str] = None,
) -> None:
    memory_identity_write.record_identity_evidence(
        conversation_id,
        entries,
        source_trace_id=source_trace_id,
        conn_factory=_conn,
        normalize_identity_content_fn=_normalize_identity_content,
        trace_float_fn=_trace_float,
        logger=logger,
    )


# Identity row upsert

def add_identity(
    subject: str,
    content: str,
    source_trace_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    *,
    stability: str = 'unknown',
    utterance_mode: str = 'unknown',
    recurrence: str = 'unknown',
    scope: str = 'unknown',
    evidence_kind: str = 'weak',
    confidence: float = 0.0,
    status: str = 'accepted',
    reason: str = '',
) -> Optional[str]:
    return memory_identity_write.add_identity(
        subject,
        content,
        source_trace_id=source_trace_id,
        conversation_id=conversation_id,
        stability=stability,
        utterance_mode=utterance_mode,
        recurrence=recurrence,
        scope=scope,
        evidence_kind=evidence_kind,
        confidence=confidence,
        status=status,
        reason=reason,
        conn_factory=_conn,
        normalize_identity_content_fn=_normalize_identity_content,
        trace_float_fn=_trace_float,
        logger=logger,
    )


# Contradictions and conflicts

def _cosine_similarity(vec_a: Sequence[float], vec_b: Sequence[float]) -> float:
    return memory_identity_dynamics._cosine_similarity(vec_a, vec_b)


def _embedding_similarity_safe(
    vec_a: Sequence[float] | None,
    vec_b: Sequence[float] | None,
) -> Optional[float]:
    return memory_identity_dynamics._embedding_similarity_safe(
        vec_a,
        vec_b,
        cosine_similarity_fn=_cosine_similarity,
        logger=logger,
    )


def _embed_identity_conflict_vector(text: str, *, purpose: str) -> Optional[list[float]]:
    return memory_identity_dynamics._embed_identity_conflict_vector(
        text,
        purpose=purpose,
        embed_fn=embed,
        logger=logger,
    )


def _ordered_pair(id_a: str, id_b: str) -> tuple[str, str]:
    return memory_identity_dynamics._ordered_pair(id_a, id_b)


def _conflict_already_open(cur: Any, id_a: str, id_b: str) -> bool:
    return memory_identity_dynamics._conflict_already_open(
        cur,
        id_a,
        id_b,
        ordered_pair_fn=_ordered_pair,
    )


def _insert_conflict(
    cur: Any,
    id_a: str,
    id_b: str,
    confidence_conflict: float,
    reason: str,
) -> None:
    memory_identity_dynamics._insert_conflict(
        cur,
        id_a,
        id_b,
        confidence_conflict,
        reason,
        ordered_pair_fn=_ordered_pair,
    )


def _has_open_strong_conflict(subject: str, content_norm: str) -> bool:
    return memory_identity_dynamics._has_open_strong_conflict(
        subject,
        content_norm,
        conn_factory=_conn,
        logger=logger,
    )


def detect_and_record_conflicts(identity_id: str) -> None:
    memory_identity_dynamics.detect_and_record_conflicts(
        identity_id,
        conn_factory=_conn,
        policy_module=policy,
        logger=logger,
        conflict_already_open_fn=_conflict_already_open,
        embed_identity_conflict_vector_fn=_embed_identity_conflict_vector,
        embedding_similarity_safe_fn=_embedding_similarity_safe,
        insert_conflict_fn=_insert_conflict,
    )


# Defer policy

def _list_recent_evidence(subject: str, content_norm: str, window_days: int) -> list[dict[str, Any]]:
    return memory_identity_dynamics._list_recent_evidence(
        subject,
        content_norm,
        window_days,
        conn_factory=_conn,
        logger=logger,
    )


def _apply_defer_policy_for_content(subject: str, content_norm: str) -> None:
    memory_identity_dynamics._apply_defer_policy_for_content(
        subject,
        content_norm,
        conn_factory=_conn,
        policy_module=policy,
        config_module=config,
        logger=logger,
        list_recent_evidence_fn=_list_recent_evidence,
        has_open_strong_conflict_fn=_has_open_strong_conflict,
    )


def _expire_stale_deferred_global() -> None:
    memory_identity_dynamics._expire_stale_deferred_global(
        conn_factory=_conn,
        config_module=config,
        logger=logger,
    )


def preview_identity_entries(entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return memory_identity_dynamics.preview_identity_entries(
        entries,
        policy_module=policy,
        config_module=config,
        trace_float_fn=_trace_float,
    )


def persist_identity_entries(
    conversation_id: str,
    entries: list[dict[str, Any]],
    source_trace_id: Optional[str] = None,
) -> None:
    memory_identity_dynamics.persist_identity_entries(
        conversation_id,
        entries,
        source_trace_id=source_trace_id,
        preview_identity_entries_fn=preview_identity_entries,
        record_identity_evidence_fn=record_identity_evidence,
        add_identity_fn=add_identity,
        detect_and_record_conflicts_fn=detect_and_record_conflicts,
        normalize_identity_content_fn=_normalize_identity_content,
        apply_defer_policy_for_content_fn=_apply_defer_policy_for_content,
        expire_stale_deferred_global_fn=_expire_stale_deferred_global,
    )


# Identity dynamics

def decay_identities() -> None:
    memory_identity_dynamics.decay_identities(
        conn_factory=_conn,
        decay_factor=config.IDENTITY_DECAY_FACTOR,
        logger=logger,
    )


def reactivate_identities(identity_ids: list[str]) -> None:
    memory_identity_dynamics.reactivate_identities(
        identity_ids,
        conn_factory=_conn,
        logger=logger,
    )
