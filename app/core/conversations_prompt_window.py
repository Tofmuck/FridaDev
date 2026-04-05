from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Optional

from psycopg.rows import dict_row

from core.hermeneutic_node.inputs import time_input

CONTEXT_HINTS_BLOCK_HEADER = "[Indices contextuels recents]"
CONTEXT_HINTS_COUNT_MARKER = "(confidence: "
MEMORY_CONTEXT_BLOCK_HEADER_PREFIX = "[Contexte du souvenir"
MEMORY_TRACES_BLOCK_HEADER = "[Mémoire — souvenirs pertinents]"


def delta_t_label(ts_msg: str, ts_now: str, *, timezone_name: str) -> str:
    """Retourne un label Delta-T lisible entre deux timestamps ISO."""
    return time_input.render_delta_label(
        ts_msg,
        ts_now,
        timezone_name=timezone_name,
    )


def silence_label(ts_before: str, ts_after: str) -> str:
    """Retourne un marqueur de silence entre deux messages consecutifs."""
    return time_input.render_silence_label(ts_before, ts_after)


def make_summary_message(summary: dict[str, Any]) -> dict[str, str]:
    start = (summary.get("start_ts") or "")[:10]
    end = (summary.get("end_ts") or "")[:10]
    if start and end and start != end:
        period = f"du {start} au {end}"
    elif start:
        period = f"du {start}"
    else:
        period = ""
    header = f"[Résumé de la période {period}]" if period else "[Résumé]"
    return {"role": "system", "content": f"{header}\n{summary['content']}"}


def get_active_summary(
    conversation_id: Optional[str],
    *,
    normalize_conversation_id_func: Callable[[Optional[str]], Optional[str]],
    db_conn_func: Callable[[], Any],
    ts_to_iso_func: Callable[[Any], str],
    logger: Any,
) -> Optional[dict[str, Any]]:
    conv_id = normalize_conversation_id_func(conversation_id)
    if not conv_id:
        return None

    try:
        with db_conn_func() as conn:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT id, start_ts, end_ts, content
                    FROM summaries
                    WHERE conversation_id = %s
                    ORDER BY
                        COALESCE(end_ts, start_ts) DESC NULLS LAST,
                        end_ts DESC NULLS LAST,
                        start_ts DESC NULLS LAST,
                        id DESC
                    LIMIT 1
                    """,
                    (conv_id,),
                )
                row = cur.fetchone()
    except Exception as exc:
        logger.warning("conv_active_summary_read_failed id=%s err=%s", conv_id, exc)
        return None

    if not row:
        return None

    return {
        "id": str(row.get("id") or ""),
        "conversation_id": conv_id,
        "start_ts": ts_to_iso_func(row.get("start_ts")) if row.get("start_ts") else None,
        "end_ts": ts_to_iso_func(row.get("end_ts")) if row.get("end_ts") else None,
        "content": str(row.get("content") or ""),
    }


def make_memory_context_message(summaries: list[dict[str, Any]]) -> Optional[dict[str, str]]:
    """Formate les résumés parents des traces mémoire en un slot contexte."""
    if not summaries:
        return None
    lines = []
    for summary in summaries:
        start = (summary.get("start_ts") or "")[:10]
        end = (summary.get("end_ts") or "")[:10]
        if start and end and start != end:
            period = f"du {start} au {end}"
        elif start:
            period = f"du {start}"
        else:
            period = ""
        header = f"{MEMORY_CONTEXT_BLOCK_HEADER_PREFIX} — résumé {period}]" if period else f"{MEMORY_CONTEXT_BLOCK_HEADER_PREFIX}]"
        lines.append(f"{header}\n{summary['content']}")
    return {"role": "system", "content": "\n\n".join(lines)}


def summary_cutoff_iso(
    summary: Optional[dict[str, Any]],
    *,
    ts_to_iso_func: Callable[[Any], str],
) -> Optional[str]:
    if not summary:
        return None
    cutoff = summary.get("end_ts") or summary.get("start_ts")
    if not cutoff:
        return None
    try:
        return ts_to_iso_func(cutoff)
    except Exception:
        return None


def message_is_after_summary(
    msg: dict[str, Any],
    cutoff_iso: Optional[str],
    *,
    parse_iso_to_dt_func: Callable[[str], datetime],
) -> bool:
    if not cutoff_iso:
        return True
    ts = msg.get("timestamp")
    if not ts:
        return True
    try:
        return parse_iso_to_dt_func(ts) > parse_iso_to_dt_func(cutoff_iso)
    except Exception:
        return True


def make_memory_message(
    traces: list[dict[str, Any]],
    ts_now: str,
    *,
    delta_t_label_func: Callable[[str, str], str],
) -> Optional[dict[str, str]]:
    """Formate les traces mémoire en un slot système avec Delta-T."""
    if not traces:
        return None
    lines = [MEMORY_TRACES_BLOCK_HEADER]
    for trace in traces:
        role = "Utilisateur" if trace.get("role") == "user" else "Assistant"
        ts = trace.get("timestamp") or ""
        label = delta_t_label_func(ts, ts_now) if ts else ""
        prefix = f"[{label}] " if label else ""
        lines.append(f"{prefix}{role} : {trace['content']}")
    return {"role": "system", "content": "\n".join(lines)}


def make_context_hints_message(
    hints: list[dict[str, Any]],
    ts_now: str,
    model: str,
    *,
    delta_t_label_func: Callable[[str, str], str],
    count_tokens_func: Callable[[list[dict[str, str]], str], int],
    context_hints_max_tokens: int,
    context_hints_max_items: int,
) -> Optional[dict[str, str]]:
    """Format non-durable context hints with dedicated token budget."""
    if not hints:
        return None

    lines = [CONTEXT_HINTS_BLOCK_HEADER]
    kept = 0
    for hint in hints:
        content = str(hint.get("content") or "").strip()
        if not content:
            continue
        ts_hint = str(hint.get("timestamp") or "")
        label = delta_t_label_func(ts_hint, ts_now) if ts_hint else ""
        scope = str(hint.get("scope") or "user")
        kind = "Situation" if scope == "situation" else "Utilisateur"
        confidence = float(hint.get("confidence") or 0.0)
        prefix = f"[{label}] " if label else ""
        line = f"- {prefix}{kind}: {content} (confidence: {confidence:.2f})"

        trial = "\n".join(lines + [line])
        estimated_trial_tokens = count_tokens_func([{"role": "system", "content": trial}], model)
        if estimated_trial_tokens > context_hints_max_tokens:
            continue

        lines.append(line)
        kept += 1
        if kept >= context_hints_max_items:
            break

    if kept == 0:
        return None
    return {"role": "system", "content": "\n".join(lines)}


def build_prompt_messages(
    conversation: dict[str, Any],
    model: str,
    *,
    now: Optional[str] = None,
    memory_traces: Optional[list[dict[str, Any]]] = None,
    context_hints: Optional[list[dict[str, Any]]] = None,
    ensure_system_message_func: Callable[[list[dict[str, Any]]], dict[str, Any]],
    get_active_summary_func: Callable[[Optional[str]], Optional[dict[str, Any]]],
    summary_cutoff_iso_func: Callable[[Optional[dict[str, Any]]], Optional[str]],
    message_is_after_summary_func: Callable[[dict[str, Any], Optional[str]], bool],
    make_summary_message_func: Callable[[dict[str, Any]], dict[str, str]],
    make_context_hints_message_func: Callable[[list[dict[str, Any]], str, str], Optional[dict[str, str]]],
    make_memory_context_message_func: Callable[[list[dict[str, Any]]], Optional[dict[str, str]]],
    make_memory_message_func: Callable[[list[dict[str, Any]], str], Optional[dict[str, str]]],
    count_tokens_func: Callable[[list[dict[str, Any]], str], int],
    max_tokens: int,
    now_iso_func: Callable[[], str],
    logger: Any,
    admin_log_event_func: Callable[..., Any],
    silence_label_func: Callable[[str, str], str],
    delta_t_label_func: Callable[[str, str], str],
) -> list[dict[str, str]]:
    messages = conversation.get("messages", [])
    system_msg = ensure_system_message_func(messages)

    active_summary = get_active_summary_func(conversation.get("id"))
    active_summary_cutoff = summary_cutoff_iso_func(active_summary)

    if active_summary:
        candidates = [
            m
            for m in messages
            if m.get("role") in {"user", "assistant"}
            and message_is_after_summary_func(m, active_summary_cutoff)
        ]
    else:
        candidates = [m for m in messages if m.get("role") in {"user", "assistant"}]

    ts_now = now or now_iso_func()
    prefix: list[dict[str, Any]] = [system_msg]
    if active_summary:
        prefix.append(make_summary_message_func(active_summary))
    if context_hints:
        ctx_hints_msg = make_context_hints_message_func(context_hints, ts_now, model)
        if ctx_hints_msg:
            prefix.append(ctx_hints_msg)
    if memory_traces:
        seen_ids: set[str] = set()
        parent_summaries: list[dict[str, Any]] = []
        for trace in memory_traces:
            parent_summary = trace.get("parent_summary")
            if parent_summary and parent_summary.get("id") not in seen_ids:
                seen_ids.add(parent_summary["id"])
                parent_summaries.append(parent_summary)
        ctx_msg = make_memory_context_message_func(parent_summaries)
        if ctx_msg:
            prefix.append(ctx_msg)
        mem_msg = make_memory_message_func(memory_traces, ts_now)
        if mem_msg:
            prefix.append(mem_msg)

    selected_reversed: list[dict[str, Any]] = []
    for msg in reversed(candidates):
        trial = prefix + list(reversed(selected_reversed + [msg]))
        estimated_trial_tokens = count_tokens_func(trial, model)
        if estimated_trial_tokens > max_tokens:
            break
        selected_reversed.append(msg)
    selected = list(reversed(selected_reversed))

    prompt_messages = prefix + selected
    estimated_prompt_window_tokens = count_tokens_func(prompt_messages, model)
    logger.info(
        "token_window id=%s estimated_tokens=%s messages=%s summary=%s",
        conversation.get("id"),
        estimated_prompt_window_tokens,
        len(prompt_messages),
        active_summary["id"][:8] if active_summary else "none",
    )
    admin_log_event_func(
        "token_window",
        conversation_id=conversation.get("id"),
        estimated_prompt_window_tokens=estimated_prompt_window_tokens,
        message_count=len(prompt_messages),
        summary_id=active_summary["id"] if active_summary else None,
    )

    result: list[dict[str, str]] = []
    prev_ts: Optional[str] = None
    for msg in prompt_messages:
        role = str(msg["role"])
        content = str(msg["content"])
        ts_msg = str(msg.get("timestamp", ""))
        if role in {"user", "assistant"}:
            if prev_ts and ts_msg:
                silence = silence_label_func(prev_ts, ts_msg)
                if silence:
                    result.append({"role": "system", "content": silence})
            label = delta_t_label_func(ts_msg, ts_now) if ts_msg else ""
            if label:
                content = f"[{label}] {content}"
            prev_ts = ts_msg
        result.append({"role": role, "content": content})
    return result
