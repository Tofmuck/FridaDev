from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Mapping, Sequence

import config as default_config
from core.hermeneutic_node.inputs import memory_arbitration_input
from core.hermeneutic_node.inputs import memory_retrieved_input
from identity import identity_governance
from memory import hermeneutics_policy
from memory import memory_identity_mutable_rewriter
from observability import chat_turn_logger
from observability import identity_observability


_HERMENEUTIC_MODE_OFF = 'off'
_HERMENEUTIC_MODE_SHADOW = 'shadow'
_HERMENEUTIC_MODE_ENFORCED_IDENTITIES = 'enforced_identities'
_HERMENEUTIC_MODE_ENFORCED_ALL = 'enforced_all'


def resolve_hermeneutic_mode(config_module: Any) -> str:
    mode = str(config_module.HERMENEUTIC_MODE or _HERMENEUTIC_MODE_SHADOW).strip().lower()
    if mode == 'enforced':
        return _HERMENEUTIC_MODE_ENFORCED_ALL
    return mode


def mode_enforces_identity(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _mode_runs_arbiter(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_SHADOW,
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _mode_enforces_memory(mode: str) -> bool:
    return mode == _HERMENEUTIC_MODE_ENFORCED_ALL


def _mode_runs_identity(mode: str) -> bool:
    return mode in {
        _HERMENEUTIC_MODE_SHADOW,
        _HERMENEUTIC_MODE_ENFORCED_IDENTITIES,
        _HERMENEUTIC_MODE_ENFORCED_ALL,
    }


def _empty_identity_actions() -> dict[str, int]:
    return {'add': 0, 'update': 0, 'override': 0, 'reject': 0, 'defer': 0}


def _governed_config_value(config_module: Any, key: str) -> Any:
    if config_module is not default_config:
        return getattr(config_module, key)
    return identity_governance.governed_value_for_runtime(
        key,
        config_module=config_module,
    )


def _emit_identity_write_skipped_by_side(
    *,
    reason_code: str,
    reason_short: str,
    mode: str,
    write_mode: str,
    write_effect: str,
    side_entry_counts: dict[str, int] | None = None,
) -> None:
    side_counts = dict(side_entry_counts or {})
    for side in ('frida', 'user'):
        entry_count = int(side_counts.get(side, 0))
        chat_turn_logger.emit(
            'identity_write',
            status='skipped',
            reason_code=reason_code,
            payload=identity_observability.build_identity_write_payload(
                target_side=side,
                mode=mode,
                write_mode=write_mode,
                write_effect=write_effect,
                persisted_count=0,
                evidence_count=entry_count,
                observed_count=entry_count,
                retained_count=0,
                actions_count=_empty_identity_actions(),
                observed_values=(),
                content_present=entry_count > 0,
            ),
        )
    chat_turn_logger.emit_branch_skipped(
        reason_code=reason_code,
        reason_short=reason_short,
    )


def _guard_filtered_summary(
    filtered_entries: Sequence[Mapping[str, Any]],
) -> tuple[dict[str, int], dict[str, list[str]]]:
    return identity_observability.summarize_guard_filtered_entries(filtered_entries)


def _sanitize_recent_turns_for_mutable_rewriter(
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    web_input: Mapping[str, Any] | None,
) -> list[dict[str, Any]]:
    sanitized: list[dict[str, Any]] = []
    for turn in recent_turns:
        canonical_turn = dict(turn or {})
        role = str(canonical_turn.get('role') or '').strip().lower()
        content = str(canonical_turn.get('content') or '').strip()
        if role == 'assistant' and content:
            reason = hermeneutics_policy.unsupported_web_reading_claim_reason(
                {'subject': 'llm', 'content': content},
                web_input=web_input,
            )
            if reason:
                canonical_turn['content'] = ''
        if str(canonical_turn.get('content') or '').strip():
            sanitized.append(canonical_turn)
    return sanitized


def _log_stage_latency(
    conversation_id: str,
    stage: str,
    started_at: float,
    *,
    admin_logs_module: Any,
) -> float:
    duration_ms = max(0.0, (time.perf_counter() - started_at) * 1000.0)
    admin_logs_module.log_event(
        'stage_latency',
        conversation_id=conversation_id,
        stage=stage,
        duration_ms=round(duration_ms, 3),
    )
    return duration_ms


def _refresh_mutable_identities(
    conversation_id: str,
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> None:
    rewrite_t0 = time.perf_counter()
    try:
        summary = memory_identity_mutable_rewriter.refresh_mutable_identities(
            recent_turns,
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
        )
    except Exception as exc:
        summary = {
            'status': 'skipped',
            'reason_code': 'rewriter_flow_error',
            'outcomes': [],
        }
        admin_logs_module.log_event(
            'identity_mutable_rewrite_apply',
            conversation_id=conversation_id,
            status='skipped',
            reason_code='rewriter_flow_error',
            outcomes=[],
        )
        chat_turn_logger.emit(
            'identity_mutable_rewrite',
            status='skipped',
            reason_code='rewriter_flow_error',
            payload={
                'request_status': 'skipped',
                'reason_code': 'rewriter_flow_error',
                'outcomes': [],
                'error_class': exc.__class__.__name__,
            },
            prompt_kind='identity_mutable_rewriter',
        )
    else:
        admin_logs_module.log_event(
            'identity_mutable_rewrite_apply',
            conversation_id=conversation_id,
            status=str(summary.get('status') or 'ok'),
            reason_code=str(summary.get('reason_code') or ''),
            outcomes=list(summary.get('outcomes') or []),
        )
    _log_stage_latency(
        conversation_id,
        'identity_mutable_rewriter',
        rewrite_t0,
        admin_logs_module=admin_logs_module,
    )


def _safe_int(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _resolve_retrieval_top_k_requested(*, memory_store_module: Any, config_module: Any) -> int | None:
    runtime_embedding_value = getattr(memory_store_module, '_runtime_embedding_value', None)
    if callable(runtime_embedding_value):
        resolved = _safe_int(runtime_embedding_value('top_k'))
        if resolved is not None:
            return resolved
    return _safe_int(getattr(config_module, 'MEMORY_TOP_K', None))


def _retrieve_raw_traces(*, memory_store_module: Any, user_msg: str) -> list[dict[str, Any]]:
    retrieve_for_arbiter = getattr(memory_store_module, 'retrieve_for_arbiter', None)
    if callable(retrieve_for_arbiter):
        return list(retrieve_for_arbiter(user_msg))
    return list(memory_store_module.retrieve(user_msg))


def _enrich_retrieved_candidates(
    *,
    memory_store_module: Any,
    traces: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    if not traces:
        return []
    return memory_store_module.enrich_traces_with_summaries([dict(trace) for trace in traces])


@dataclass
class PreparedMemoryContext:
    current_mode: str
    memory_traces: list[dict[str, Any]]
    context_hints: list[dict[str, Any]]
    memory_retrieved: dict[str, Any]
    memory_arbitration: dict[str, Any]

    def __iter__(self):
        yield self.current_mode
        yield self.memory_traces
        yield self.context_hints


def prepare_memory_context(
    *,
    conversation: Mapping[str, Any],
    user_msg: str,
    config_module: Any,
    memory_store_module: Any,
    arbiter_module: Any,
    admin_logs_module: Any,
) -> PreparedMemoryContext:
    conversation_id = str(conversation['id'])
    current_mode = resolve_hermeneutic_mode(config_module)
    admin_logs_module.log_event(
        'hermeneutic_mode',
        conversation_id=conversation_id,
        mode=current_mode,
    )

    top_k_requested = _resolve_retrieval_top_k_requested(
        memory_store_module=memory_store_module,
        config_module=config_module,
    )
    retrieve_t0 = time.perf_counter()
    raw_traces = _retrieve_raw_traces(memory_store_module=memory_store_module, user_msg=user_msg)
    _log_stage_latency(
        conversation_id,
        'retrieve',
        retrieve_t0,
        admin_logs_module=admin_logs_module,
    )

    recent_turns = [
        message
        for message in conversation.get('messages', [])
        if message.get('role') in {'user', 'assistant'}
    ][-10:]

    if raw_traces:
        admin_logs_module.log_event('memory_retrieved', conversation_id=conversation_id, count=len(raw_traces))

        retrieved_candidates = _enrich_retrieved_candidates(
            memory_store_module=memory_store_module,
            traces=raw_traces,
        )
        memory_retrieved = memory_retrieved_input.build_memory_retrieved_input(
            retrieval_query=user_msg,
            top_k_requested=top_k_requested,
            traces=retrieved_candidates,
        )
        memory_traces = list(retrieved_candidates)
        filtered_traces: list[dict[str, Any]] = []
        arbiter_decisions: list[dict[str, Any]] = []

        if _mode_runs_arbiter(current_mode):
            arbiter_t0 = time.perf_counter()
            filtered_traces, arbiter_decisions = arbiter_module.filter_traces_with_diagnostics(raw_traces, recent_turns)
            _log_stage_latency(
                conversation_id,
                'arbiter',
                arbiter_t0,
                admin_logs_module=admin_logs_module,
            )

            try:
                memory_store_module.record_arbiter_decisions(
                    conversation_id,
                    raw_traces,
                    arbiter_decisions,
                    mode=current_mode,
                )
            except TypeError:
                # Compatibility with legacy test doubles that still expose the old signature.
                memory_store_module.record_arbiter_decisions(conversation_id, raw_traces, arbiter_decisions)
            admin_logs_module.log_event(
                'memory_arbitrated',
                conversation_id=conversation_id,
                raw=len(raw_traces),
                kept=len(filtered_traces),
                decisions=len(arbiter_decisions),
            )
            memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
                memory_retrieved=memory_retrieved,
                raw_candidates_count=len(raw_traces),
                decisions=arbiter_decisions,
                status='available',
            )

            if _mode_enforces_memory(current_mode):
                memory_traces = _enrich_retrieved_candidates(
                    memory_store_module=memory_store_module,
                    traces=filtered_traces,
                )
                memory_source = 'arbiter_enforced'
            else:
                memory_source = 'raw_shadow_non_blocking'
        else:
            memory_source = 'raw_mode_off'
            chat_turn_logger.emit(
                'arbiter',
                status='skipped',
                reason_code='mode_off',
                payload={
                    'raw_candidates': len(raw_traces),
                    'kept_candidates': len(raw_traces),
                    'mode': current_mode,
                },
            )
            chat_turn_logger.emit_branch_skipped(
                reason_code='mode_off',
                reason_short='arbiter_disabled_for_mode',
            )
            memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
                memory_retrieved=memory_retrieved,
                raw_candidates_count=len(raw_traces),
                decisions=[],
                status='skipped',
                reason_code='mode_off',
            )

        admin_logs_module.log_event(
            'memory_mode_apply',
            conversation_id=conversation_id,
            mode=current_mode,
            source=memory_source,
            raw=len(raw_traces),
            selected=len(memory_traces),
            filtered=len(filtered_traces),
        )
    else:
        chat_turn_logger.emit(
            'arbiter',
            status='skipped',
            reason_code='no_data',
            payload={
                'raw_candidates': 0,
                'kept_candidates': 0,
                'mode': current_mode,
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code='no_data',
            reason_short='arbiter_no_traces',
        )
        memory_traces = []
        memory_retrieved = memory_retrieved_input.build_memory_retrieved_input(
            retrieval_query=user_msg,
            top_k_requested=top_k_requested,
            traces=[],
        )
        memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
            memory_retrieved=memory_retrieved,
            raw_candidates_count=0,
            decisions=[],
            status='skipped',
            reason_code='no_data',
        )

    context_hints = memory_store_module.get_recent_context_hints(
        max_items=_governed_config_value(config_module, 'CONTEXT_HINTS_MAX_ITEMS'),
        max_age_days=_governed_config_value(config_module, 'CONTEXT_HINTS_MAX_AGE_DAYS'),
        min_confidence=_governed_config_value(config_module, 'CONTEXT_HINTS_MIN_CONFIDENCE'),
    )
    if context_hints:
        admin_logs_module.log_event(
            'context_hints_selected',
            conversation_id=conversation_id,
            count=len(context_hints),
        )

    return PreparedMemoryContext(
        current_mode=current_mode,
        memory_traces=memory_traces,
        context_hints=list(context_hints or []),
        memory_retrieved=memory_retrieved,
        memory_arbitration=memory_arbitration,
    )


def record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    web_input: Mapping[str, Any] | None = None,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> None:
    if not _mode_runs_identity(mode):
        _emit_identity_write_skipped_by_side(
            reason_code='mode_off',
            reason_short='identity_write_disabled_for_mode',
            mode=mode,
            write_mode='disabled',
            write_effect='none',
        )
        admin_logs_module.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='skip_mode_off',
            entries=0,
        )
        return

    extract_t0 = time.perf_counter()
    id_entries = arbiter_module.extract_identities(recent_turns)
    _log_stage_latency(
        conversation_id,
        'identity_extractor',
        extract_t0,
        admin_logs_module=admin_logs_module,
    )
    filtered_entries, guard_filtered_entries = hermeneutics_policy.filter_unsupported_web_reading_identities(
        id_entries,
        web_input=web_input,
    )
    guard_filtered_count = len(guard_filtered_entries)
    guard_counts_by_side, guard_reason_codes_by_side = _guard_filtered_summary(guard_filtered_entries)
    mutable_rewriter_turns = _sanitize_recent_turns_for_mutable_rewriter(
        recent_turns,
        web_input=web_input,
    )

    if mode_enforces_identity(mode):
        memory_store_module.persist_identity_entries(conversation_id, filtered_entries)
        _refresh_mutable_identities(
            conversation_id,
            mutable_rewriter_turns,
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        admin_logs_module.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='persist_enforced',
            entries=len(filtered_entries),
            extracted_entries=len(id_entries),
            guard_filtered_count=guard_filtered_count,
            guard_filtered_by_side=guard_counts_by_side,
            guard_reason_codes_by_side=guard_reason_codes_by_side,
        )
        return

    preview_entries = memory_store_module.preview_identity_entries(filtered_entries)
    memory_store_module.record_identity_evidence(conversation_id, preview_entries)
    side_counts = {'frida': 0, 'user': 0}
    for entry in preview_entries:
        subject = str(entry.get('subject') or '').strip().lower()
        if subject == 'llm':
            side_counts['frida'] += 1
        elif subject == 'user':
            side_counts['user'] += 1
    _emit_identity_write_skipped_by_side(
        reason_code='not_applicable',
        reason_short='identity_write_shadow_mode',
        mode=mode,
        write_mode='shadow',
        write_effect='evidence_only',
        side_entry_counts=side_counts,
    )
    admin_logs_module.log_event(
        'identity_mode_apply',
        conversation_id=conversation_id,
        mode=mode,
        action='record_evidence_shadow',
        entries=len(preview_entries),
        extracted_entries=len(id_entries),
        guard_filtered_count=guard_filtered_count,
        guard_filtered_by_side=guard_counts_by_side,
        guard_reason_codes_by_side=guard_reason_codes_by_side,
    )
