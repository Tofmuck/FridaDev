from __future__ import annotations

from dataclasses import dataclass
import inspect
import time
from typing import Any, Mapping, Sequence

import config as default_config
from core import assistant_turn_state
from core.hermeneutic_node.inputs import memory_arbitration_input
from core.hermeneutic_node.inputs import memory_retrieved_input
from identity import identity_governance
from memory import hermeneutics_policy
from memory import memory_identity_periodic_agent
from memory import memory_pre_arbiter_basket
from observability import chat_turn_logger
from observability import identity_observability
from observability import memory_chain_snapshot


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


def _call_memory_arbiter(
    arbiter_module: Any,
    traces: Sequence[Mapping[str, Any]],
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    now_iso: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    call = arbiter_module.filter_traces_with_diagnostics
    try:
        signature = inspect.signature(call)
    except (TypeError, ValueError):
        return call(traces, recent_turns, now_iso=now_iso)
    params = signature.parameters
    supports_kwargs = any(
        parameter.kind == inspect.Parameter.VAR_KEYWORD
        for parameter in params.values()
    )
    if supports_kwargs or 'now_iso' in params:
        return call(traces, recent_turns, now_iso=now_iso)
    return call(traces, recent_turns)


def _run_periodic_identity_agent(
    conversation_id: str,
    turn_pair: Sequence[Mapping[str, Any]],
    *,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
    enforce_writes: bool,
) -> dict[str, Any]:
    staging_t0 = time.perf_counter()
    try:
        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            conversation_id,
            turn_pair,
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            enforce_writes=enforce_writes,
            turn_id=chat_turn_logger.current_turn_id(),
        )
    except Exception as exc:
        summary = {
            'status': 'skipped',
            'reason_code': 'mutable_judge_flow_error',
            'buffer_pairs_count': 0,
            'buffer_target_pairs': memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            'last_agent_status': 'mutable_judge_flow_error',
            'buffer_cleared': False,
            'buffer_frozen': False,
            'auto_canonization_suspended': False,
            'writes_applied': False,
            'promotion_count': 0,
            'promotions': [],
            'outcomes': [],
            'rejection_reasons': {},
            'legacy_writer_disabled': False,
        }
        admin_logs_module.log_event(
            'mutable_identity_judge_apply',
            conversation_id=conversation_id,
            status='skipped',
            reason_code='mutable_judge_flow_error',
            buffer_pairs_count=0,
            buffer_target_pairs=memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            buffer_cleared=False,
            buffer_frozen=False,
            auto_canonization_suspended=False,
            writes_applied=False,
            promotion_count=0,
            promotions=[],
            rejection_reasons={},
            outcomes=[],
            error_class=exc.__class__.__name__,
            legacy_writer_disabled=False,
            runtime_pipeline='mutable_identity_judge_v2_add_only',
            write_mode='enforced' if enforce_writes else 'shadow',
        )
    else:
        size_fields = {
            key: summary.get(key)
            for key in (
                'window_chars',
                'payload_chars',
                'estimated_prompt_tokens',
                'max_window_chars',
                'max_estimated_prompt_tokens',
            )
            if summary.get(key) is not None
        }
        admin_logs_module.log_event(
            'mutable_identity_judge_apply',
            conversation_id=conversation_id,
            status=str(summary.get('status') or 'ok'),
            reason_code=str(summary.get('reason_code') or ''),
            buffer_pairs_count=int(summary.get('buffer_pairs_count') or 0),
            buffer_target_pairs=int(
                summary.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS
            ),
            buffer_cleared=bool(summary.get('buffer_cleared')),
            buffer_frozen=bool(summary.get('buffer_frozen')),
            auto_canonization_suspended=bool(summary.get('auto_canonization_suspended')),
            writes_applied=bool(summary.get('writes_applied')),
            promotion_count=int(summary.get('promotion_count') or 0),
            promotions=list(summary.get('promotions') or []),
            rejection_reasons=dict(summary.get('rejection_reasons') or {}),
            last_agent_status=str(summary.get('last_agent_status') or ''),
            outcomes=list(summary.get('outcomes') or []),
            legacy_writer_disabled=bool(summary.get('legacy_writer_disabled')),
            runtime_pipeline=str(summary.get('runtime_pipeline') or 'mutable_identity_judge_v2_add_only'),
            write_mode=str(summary.get('write_mode') or ('enforced' if enforce_writes else 'shadow')),
            judge_status=str(summary.get('judge_status') or ''),
            judge_reason_code=str(summary.get('judge_reason_code') or ''),
            apply_status=str(summary.get('apply_status') or ''),
            apply_reason_code=str(summary.get('apply_reason_code') or ''),
            score_first_writer_enabled=bool(summary.get('score_first_writer_enabled')),
            verdict_counts=dict(summary.get('verdict_counts') or {}),
            **size_fields,
        )
    _log_stage_latency(
        conversation_id,
        'mutable_identity_judge_runtime',
        staging_t0,
        admin_logs_module=admin_logs_module,
    )
    return summary


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


@dataclass
class RetrievalOutcome:
    traces: list[dict[str, Any]]
    status: str
    reason_code: str | None = None
    error_code: str | None = None
    error_class: str | None = None
    top_k_requested: int | None = None
    top_k_returned: int = 0


def _retrieval_outcome_from_result(result: Any, *, top_k_requested: int | None) -> RetrievalOutcome:
    if isinstance(result, Mapping):
        raw_traces = result.get('traces')
        status_value = result.get('status')
        ok_value = result.get('ok')
        reason_code = result.get('reason_code')
        error_code = result.get('error_code')
        error_class = result.get('error_class')
        result_top_k = result.get('top_k_requested')
    else:
        raw_traces = getattr(result, 'traces', result)
        status_value = getattr(result, 'status', None)
        ok_value = getattr(result, 'ok', None)
        reason_code = getattr(result, 'reason_code', None)
        error_code = getattr(result, 'error_code', None)
        error_class = getattr(result, 'error_class', None)
        result_top_k = getattr(result, 'top_k_requested', None)

    traces = [dict(trace) for trace in list(raw_traces or [])]
    status = str(status_value or '').strip().lower()
    if not status:
        status = 'error' if ok_value is False else 'ok'
    if status not in {'ok', 'error'}:
        status = 'error' if ok_value is False else 'ok'
    if status == 'error' and not str(reason_code or '').strip():
        reason_code = 'retrieve_error'
    elif status == 'ok' and not traces and not str(reason_code or '').strip():
        reason_code = 'no_data'

    resolved_top_k = _safe_int(result_top_k)
    if resolved_top_k is None:
        resolved_top_k = top_k_requested
    return RetrievalOutcome(
        traces=traces,
        status=status,
        reason_code=str(reason_code or '').strip() or None,
        error_code=str(error_code or '').strip() or None,
        error_class=str(error_class or '').strip() or None,
        top_k_requested=resolved_top_k,
        top_k_returned=len(traces),
    )


def _retrieve_raw_traces(
    *,
    memory_store_module: Any,
    user_msg: str,
    top_k_requested: int | None,
) -> RetrievalOutcome:
    retrieve_for_arbiter_with_status = getattr(memory_store_module, 'retrieve_for_arbiter_with_status', None)
    if callable(retrieve_for_arbiter_with_status):
        return _retrieval_outcome_from_result(
            retrieve_for_arbiter_with_status(user_msg),
            top_k_requested=top_k_requested,
        )
    retrieve_for_arbiter = getattr(memory_store_module, 'retrieve_for_arbiter', None)
    if callable(retrieve_for_arbiter):
        return _retrieval_outcome_from_result(
            retrieve_for_arbiter(user_msg),
            top_k_requested=top_k_requested,
        )
    retrieve_with_status = getattr(memory_store_module, 'retrieve_with_status', None)
    if callable(retrieve_with_status):
        return _retrieval_outcome_from_result(
            retrieve_with_status(user_msg),
            top_k_requested=top_k_requested,
        )
    return _retrieval_outcome_from_result(
        memory_store_module.retrieve(user_msg),
        top_k_requested=top_k_requested,
    )


def _retrieval_observability_payload(outcome: RetrievalOutcome) -> dict[str, Any]:
    return {
        'status': outcome.status,
        'reason_code': outcome.reason_code,
        'error_code': outcome.error_code,
        'error_class': outcome.error_class,
        'top_k_requested': outcome.top_k_requested,
        'top_k_returned': outcome.top_k_returned,
    }


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
    now_iso: str | None = None,
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
    retrieval_outcome = _retrieve_raw_traces(
        memory_store_module=memory_store_module,
        user_msg=user_msg,
        top_k_requested=top_k_requested,
    )
    raw_traces = retrieval_outcome.traces
    chat_turn_logger.set_state('memory_retrieval', _retrieval_observability_payload(retrieval_outcome))
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
            top_k_requested=retrieval_outcome.top_k_requested,
            traces=retrieved_candidates,
            status=retrieval_outcome.status,
            reason_code=retrieval_outcome.reason_code,
            error_code=retrieval_outcome.error_code,
            error_class=retrieval_outcome.error_class,
        )
        pre_arbiter_basket = memory_pre_arbiter_basket.build_pre_arbiter_basket(
            memory_retrieved=memory_retrieved,
            retrieved_candidates=retrieved_candidates,
            internal_traces=raw_traces,
        )
        memory_traces = memory_pre_arbiter_basket.select_prompt_candidates(pre_arbiter_basket)
        filtered_traces: list[dict[str, Any]] = []
        arbiter_decisions: list[dict[str, Any]] = []

        if _mode_runs_arbiter(current_mode):
            arbiter_t0 = time.perf_counter()
            filtered_traces, arbiter_decisions = _call_memory_arbiter(
                arbiter_module,
                pre_arbiter_basket.prompt_candidates,
                recent_turns,
                now_iso=now_iso,
            )
            _log_stage_latency(
                conversation_id,
                'arbiter',
                arbiter_t0,
                admin_logs_module=admin_logs_module,
            )

            try:
                memory_store_module.record_arbiter_decisions(
                    conversation_id,
                    pre_arbiter_basket.prompt_candidates,
                    arbiter_decisions,
                    mode=current_mode,
                )
            except TypeError:
                # Compatibility with legacy test doubles that still expose the old signature.
                memory_store_module.record_arbiter_decisions(
                    conversation_id,
                    pre_arbiter_basket.prompt_candidates,
                    arbiter_decisions,
                )
            admin_logs_module.log_event(
                'memory_arbitrated',
                conversation_id=conversation_id,
                raw=len(raw_traces),
                kept=len(filtered_traces),
                decisions=len(arbiter_decisions),
            )
            if _mode_enforces_memory(current_mode):
                memory_traces = memory_pre_arbiter_basket.select_prompt_candidates(
                    pre_arbiter_basket,
                    decisions=arbiter_decisions,
                )
                memory_source = 'arbiter_enforced'
            else:
                memory_source = 'pre_arbiter_basket_shadow'
            memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
                memory_retrieved=memory_retrieved,
                raw_candidates_count=len(raw_traces),
                decisions=arbiter_decisions,
                status='available',
                basket_candidates=pre_arbiter_basket.candidates,
                injected_candidate_ids=[
                    str(trace.get('candidate_id') or '')
                    for trace in memory_traces
                    if str(trace.get('candidate_id') or '').strip()
                ],
            )
        else:
            memory_source = 'pre_arbiter_basket_mode_off'
            chat_turn_logger.emit(
                'arbiter',
                status='skipped',
                reason_code='mode_off',
                payload={
                    'raw_candidates': len(raw_traces),
                    'basket_candidates': len(pre_arbiter_basket.candidates),
                    'kept_candidates': len(memory_traces),
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
                basket_candidates=pre_arbiter_basket.candidates,
                injected_candidate_ids=[
                    str(trace.get('candidate_id') or '')
                    for trace in memory_traces
                    if str(trace.get('candidate_id') or '').strip()
                ],
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
        retrieval_reason_code = (
            'retrieve_error'
            if retrieval_outcome.status == 'error'
            else (retrieval_outcome.reason_code or 'no_data')
        )
        retrieval_reason_short = (
            'memory_retrieve_failed'
            if retrieval_reason_code == 'retrieve_error'
            else 'arbiter_no_traces'
        )
        chat_turn_logger.emit(
            'arbiter',
            status='skipped',
            reason_code=retrieval_reason_code,
            payload={
                'raw_candidates': 0,
                'kept_candidates': 0,
                'mode': current_mode,
                'retrieval_status': retrieval_outcome.status,
                'retrieval_error_code': retrieval_outcome.error_code,
                'retrieval_error_class': retrieval_outcome.error_class,
            },
        )
        chat_turn_logger.emit_branch_skipped(
            reason_code=retrieval_reason_code,
            reason_short=retrieval_reason_short,
        )
        memory_traces = []
        memory_retrieved = memory_retrieved_input.build_memory_retrieved_input(
            retrieval_query=user_msg,
            top_k_requested=retrieval_outcome.top_k_requested,
            traces=[],
            status=retrieval_outcome.status,
            reason_code=retrieval_reason_code,
            error_code=retrieval_outcome.error_code,
            error_class=retrieval_outcome.error_class,
        )
        memory_arbitration = memory_arbitration_input.build_memory_arbitration_input(
            memory_retrieved=memory_retrieved,
            raw_candidates_count=0,
            decisions=[],
            status='skipped',
            reason_code=retrieval_reason_code,
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
    memory_chain_snapshot.emit_memory_chain_snapshot(
        current_mode=current_mode,
        memory_retrieved=memory_retrieved,
        memory_arbitration=memory_arbitration,
        memory_traces=memory_traces,
        context_hints=list(context_hints or []),
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
    turn_pair: Sequence[Mapping[str, Any]],
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

    dialogic_turn_pair = [dict(turn or {}) for turn in list(turn_pair or [])]
    identity_turn_pair = [dict(turn) for turn in dialogic_turn_pair]
    for turn in identity_turn_pair:
        if assistant_turn_state.is_dialogic_presence_assistant_turn(turn):
            turn['content'] = ''

    extract_t0 = time.perf_counter()
    context_extractor = getattr(arbiter_module, 'extract_dialogic_context_hints', None)
    context_result = (
        context_extractor(dialogic_turn_pair)
        if callable(context_extractor)
        else {
            'status': 'failed',
            'reason_code': 'dialogic_context_extractor_unavailable',
            'hints': [],
        }
    )
    _log_stage_latency(
        conversation_id,
        'dialogic_context_hint_extractor',
        extract_t0,
        admin_logs_module=admin_logs_module,
    )
    if isinstance(context_result, Mapping):
        context_status = str(context_result.get('status') or 'failed')
        context_reason_code = str(context_result.get('reason_code') or 'dialogic_context_unknown')
        context_hints = list(context_result.get('hints') or [])
        context_schema_version = str(context_result.get('schema_version') or '')
        context_prompt_kind = str(context_result.get('prompt_kind') or '')
    else:
        context_status = 'failed'
        context_reason_code = 'dialogic_context_result_invalid'
        context_hints = []
        context_schema_version = ''
        context_prompt_kind = ''

    persistence_result = {'status': 'not_selected', 'reason_code': 'dialogic_context_no_hint', 'persisted_count': 0}
    if context_status == 'ok' and context_hints:
        persistence_result = memory_store_module.record_dialogic_context_hints(
            conversation_id,
            context_hints,
        )
    persisted_count = int(persistence_result.get('persisted_count') or 0)
    final_context_status = context_status
    final_context_reason = context_reason_code
    if str(persistence_result.get('status') or '') == 'failed':
        final_context_status = 'failed'
        final_context_reason = str(persistence_result.get('reason_code') or 'dialogic_context_persistence_failed')
    chat_turn_logger.emit(
        'dialogic_context_hint_extractor',
        status=final_context_status,
        reason_code=final_context_reason,
        prompt_kind=context_prompt_kind or None,
        payload={
            'schema_version': context_schema_version,
            'subject': 'dialogue',
            'reason_code': final_context_reason,
            'hint_count': len(context_hints),
            'persisted_count': persisted_count,
            'write_mode': 'temporary_dialogic_context',
            'write_effect': 'prompt_context_only',
            'identity_write': False,
            'mutable_authority': False,
            'max_items': 4,
        },
    )
    buffered_turn_pair = [dict(turn) for turn in identity_turn_pair]

    if mode_enforces_identity(mode):
        periodic_summary = _run_periodic_identity_agent(
            conversation_id,
            buffered_turn_pair,
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
            enforce_writes=True,
        )
        admin_logs_module.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='record_dialogic_context_and_mutable_judge',
            context_hint_count=len(context_hints),
            context_hint_persisted_count=persisted_count,
            context_hint_status=final_context_status,
            context_hint_reason_code=final_context_reason,
            legacy_identity_writes=0,
            staging_status=str(periodic_summary.get('status') or ''),
            staging_reason_code=str(periodic_summary.get('reason_code') or ''),
            buffer_pairs_count=int(periodic_summary.get('buffer_pairs_count') or 0),
            buffer_target_pairs=int(
                periodic_summary.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS
            ),
            canonical_write_applied=bool(periodic_summary.get('writes_applied')),
            buffer_cleared=bool(periodic_summary.get('buffer_cleared')),
            buffer_frozen=bool(periodic_summary.get('buffer_frozen')),
            auto_canonization_suspended=bool(periodic_summary.get('auto_canonization_suspended')),
            promotion_count=int(periodic_summary.get('promotion_count') or 0),
            promotions=list(periodic_summary.get('promotions') or []),
            rejection_reasons=dict(periodic_summary.get('rejection_reasons') or {}),
            legacy_writer_disabled=bool(periodic_summary.get('legacy_writer_disabled')),
            runtime_pipeline=str(periodic_summary.get('runtime_pipeline') or 'mutable_identity_judge_v2_add_only'),
            write_mode=str(periodic_summary.get('write_mode') or 'enforced'),
        )
        return

    periodic_summary = _run_periodic_identity_agent(
        conversation_id,
        buffered_turn_pair,
        arbiter_module=arbiter_module,
        memory_store_module=memory_store_module,
        admin_logs_module=admin_logs_module,
        enforce_writes=False,
    )
    admin_logs_module.log_event(
        'identity_mode_apply',
        conversation_id=conversation_id,
        mode=mode,
        action='record_dialogic_context_and_shadow_mutable_judge',
        context_hint_count=len(context_hints),
        context_hint_persisted_count=persisted_count,
        context_hint_status=final_context_status,
        context_hint_reason_code=final_context_reason,
        legacy_identity_writes=0,
        staging_status=str(periodic_summary.get('status') or ''),
        staging_reason_code=str(periodic_summary.get('reason_code') or ''),
        buffer_pairs_count=int(periodic_summary.get('buffer_pairs_count') or 0),
        buffer_target_pairs=int(
            periodic_summary.get('buffer_target_pairs') or memory_identity_periodic_agent.BUFFER_TARGET_PAIRS
        ),
        canonical_write_applied=False,
        buffer_cleared=bool(periodic_summary.get('buffer_cleared')),
        buffer_frozen=bool(periodic_summary.get('buffer_frozen')),
        auto_canonization_suspended=bool(periodic_summary.get('auto_canonization_suspended')),
        legacy_writer_disabled=bool(periodic_summary.get('legacy_writer_disabled')),
        runtime_pipeline=str(periodic_summary.get('runtime_pipeline') or 'mutable_identity_judge_v2_add_only'),
        write_mode='shadow',
    )
