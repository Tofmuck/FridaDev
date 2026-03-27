from __future__ import annotations

import time
from typing import Any, Mapping, Sequence


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


def prepare_memory_context(
    *,
    conversation: Mapping[str, Any],
    user_msg: str,
    config_module: Any,
    memory_store_module: Any,
    arbiter_module: Any,
    admin_logs_module: Any,
) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    conversation_id = str(conversation['id'])
    current_mode = resolve_hermeneutic_mode(config_module)
    admin_logs_module.log_event(
        'hermeneutic_mode',
        conversation_id=conversation_id,
        mode=current_mode,
    )

    retrieve_t0 = time.perf_counter()
    raw_traces = memory_store_module.retrieve(user_msg)
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

        memory_traces = list(raw_traces)
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

            memory_store_module.record_arbiter_decisions(conversation_id, raw_traces, arbiter_decisions)
            admin_logs_module.log_event(
                'memory_arbitrated',
                conversation_id=conversation_id,
                raw=len(raw_traces),
                kept=len(filtered_traces),
                decisions=len(arbiter_decisions),
            )

            if _mode_enforces_memory(current_mode):
                memory_traces = filtered_traces
                memory_source = 'arbiter_enforced'
            else:
                memory_source = 'raw_shadow_non_blocking'
        else:
            memory_source = 'raw_mode_off'

        admin_logs_module.log_event(
            'memory_mode_apply',
            conversation_id=conversation_id,
            mode=current_mode,
            source=memory_source,
            raw=len(raw_traces),
            selected=len(memory_traces),
            filtered=len(filtered_traces),
        )

        if memory_traces:
            memory_traces = memory_store_module.enrich_traces_with_summaries(memory_traces)
    else:
        memory_traces = []

    context_hints = memory_store_module.get_recent_context_hints(
        max_items=config_module.CONTEXT_HINTS_MAX_ITEMS,
        max_age_days=config_module.CONTEXT_HINTS_MAX_AGE_DAYS,
        min_confidence=config_module.CONTEXT_HINTS_MIN_CONFIDENCE,
    )
    if context_hints:
        admin_logs_module.log_event(
            'context_hints_selected',
            conversation_id=conversation_id,
            count=len(context_hints),
        )

    return current_mode, memory_traces, list(context_hints or [])


def record_identity_entries_for_mode(
    conversation_id: str,
    recent_turns: Sequence[Mapping[str, Any]],
    *,
    mode: str,
    arbiter_module: Any,
    memory_store_module: Any,
    admin_logs_module: Any,
) -> None:
    if not _mode_runs_identity(mode):
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

    if mode_enforces_identity(mode):
        memory_store_module.persist_identity_entries(conversation_id, id_entries)
        admin_logs_module.log_event(
            'identity_mode_apply',
            conversation_id=conversation_id,
            mode=mode,
            action='persist_enforced',
            entries=len(id_entries),
        )
        return

    preview_entries = memory_store_module.preview_identity_entries(id_entries)
    memory_store_module.record_identity_evidence(conversation_id, preview_entries)
    admin_logs_module.log_event(
        'identity_mode_apply',
        conversation_id=conversation_id,
        mode=mode,
        action='record_evidence_shadow',
        entries=len(preview_entries),
    )
