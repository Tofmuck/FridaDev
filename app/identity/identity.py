#!/usr/bin/env python3
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import config
from admin import runtime_settings
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core import token_utils
from identity import active_identity_projection
from identity import static_identity_content
from identity import static_identity_paths
from observability import chat_turn_logger
from observability import identity_observability

logger = logging.getLogger('frida.identity')


@dataclass(frozen=True)
class _DynamicSelection:
    entries: list[dict[str, Any]]
    lines: list[str]
    ids: list[str]


@dataclass(frozen=True)
class _IdentityRuntimeSelection:
    block: str
    used_identity_ids: list[str]
    frida_mutable: dict[str, Any]
    user_mutable: dict[str, Any]


def _runtime_main_model_name() -> str:
    view = runtime_settings.get_main_model_settings()
    return str(view.payload['model']['value'])


def _static_subject_for_field(field: str) -> str | None:
    if field == 'llm_identity_path':
        return 'llm'
    if field == 'user_identity_path':
        return 'user'
    return None


def load_llm_identity() -> str:
    return static_identity_content.read_static_identity_text('llm')


def load_user_identity() -> str:
    return static_identity_content.read_static_identity_text('user')


def _safe_static_identity_source(field: str) -> str | None:
    subject = _static_subject_for_field(field)
    if not subject:
        return None
    try:
        snapshot = static_identity_content.resolve_active_static_identity(subject)
        return snapshot.configured_path or None
    except Exception as exc:
        logger.warning('identity_resource_path_error field=%s err=%s', field, exc)
        return None


def _get_identities(subject: str, top_n: int) -> list[dict[str, Any]]:
    try:
        from memory import memory_store

        return memory_store.get_identities(subject, top_n=top_n, status='accepted')
    except Exception as exc:
        logger.warning('identity_get_identities_error subject=%s err=%s', subject, exc)
        return []


def _get_mutable_identity(subject: str) -> dict[str, Any] | None:
    try:
        from memory import memory_store

        return memory_store.get_mutable_identity(subject)
    except Exception as exc:
        logger.warning('identity_get_mutable_identity_error subject=%s err=%s', subject, exc)
        return None


def _parse_ts(value: Any) -> datetime:
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or '').strip()
        if not raw:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)
        raw = raw.replace('Z', '+00:00')
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return datetime(1970, 1, 1, tzinfo=timezone.utc)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        return token_utils.estimate_tokens([{'content': text}], _runtime_main_model_name())
    except Exception as exc:
        logger.warning('identity_token_estimate_error err=%s', exc)
        return max(1, len(text.split()))


def _truncate_to_words(text: str, max_words: int) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text
    return ' '.join(words[:max(1, max_words)])


def _stability_rank(value: str) -> int:
    return {
        'durable': 0,
        'episodic': 1,
        'unknown': 2,
    }.get(str(value or 'unknown'), 3)


def _recurrence_rank(value: str) -> int:
    return {
        'habitual': 0,
        'repeated': 1,
        'first_seen': 2,
        'unknown': 3,
    }.get(str(value or 'unknown'), 4)


def _should_exclude_unknown(entry: dict[str, Any]) -> bool:
    if str(entry.get('override_state') or 'none') == 'force_accept':
        return False
    stability = str(entry.get('stability') or 'unknown')
    recurrence = str(entry.get('recurrence') or 'unknown')
    return stability == 'unknown' or recurrence == 'unknown'


def _entry_sort_key(entry: dict[str, Any]) -> tuple[int, int, float, float]:
    stability = _stability_rank(str(entry.get('stability') or 'unknown'))
    recurrence = _recurrence_rank(str(entry.get('recurrence') or 'unknown'))
    confidence = -float(entry.get('confidence') or 0.0)
    recency_ts = _parse_ts(entry.get('last_seen_ts') or entry.get('created_ts')).timestamp()
    recency = -recency_ts
    return stability, recurrence, confidence, recency


def _format_identity_line(entry: dict[str, Any]) -> str:
    content = str(entry.get('content') or '').strip()
    if not content:
        return ''
    stability = str(entry.get('stability') or 'unknown')
    recurrence = str(entry.get('recurrence') or 'unknown')
    confidence = float(entry.get('confidence') or 0.0)
    return (
        f"- [stability={stability}; recurrence={recurrence}; confidence={confidence:.2f}] "
        f"{content}"
    )


def _select_ranked_entries(subject: str) -> list[dict[str, Any]]:
    pool_size = max(1, config.IDENTITY_TOP_N * 4)
    entries = _get_identities(subject, pool_size)
    eligible = [
        entry for entry in entries
        if not _should_exclude_unknown(entry)
        and str(entry.get('content') or '').strip()
    ]
    eligible.sort(key=_entry_sort_key)
    return eligible


def _select_effective_dynamic_entries(subject: str, max_tokens: int) -> _DynamicSelection:
    if max_tokens <= 0:
        return _DynamicSelection(entries=[], lines=[], ids=[])

    entries: list[dict[str, Any]] = []
    lines: list[str] = []
    ids: list[str] = []
    spent_tokens = 0

    for entry in _select_ranked_entries(subject):
        if len(lines) >= max(1, config.IDENTITY_TOP_N):
            break
        line = _format_identity_line(entry)
        if not line:
            continue
        line_tokens = _estimate_tokens(line)
        if spent_tokens + line_tokens > max_tokens:
            continue
        entries.append(entry)
        lines.append(line)
        if entry.get('id'):
            ids.append(str(entry['id']))
        spent_tokens += line_tokens

    return _DynamicSelection(entries=entries, lines=lines, ids=ids)


def _build_dynamic_lines(subject: str, max_tokens: int) -> tuple[list[str], list[str]]:
    selection = _select_effective_dynamic_entries(subject, max_tokens)
    return selection.lines, selection.ids


def _compose_section(title: str, static_text: str, dynamic_lines: list[str]) -> str:
    parts = []
    if static_text:
        parts.append(static_text)
    if dynamic_lines:
        parts.append('\n'.join(dynamic_lines))
    if not parts:
        return ''
    return f'[{title}]\n' + '\n\n'.join(parts)


def _build_identity_block_text(
    *,
    llm_static: str,
    user_static: str,
    llm_dynamic_lines: list[str],
    user_dynamic_lines: list[str],
) -> str:
    sections = [
        _compose_section('IDENTITÉ DU MODÈLE', llm_static, llm_dynamic_lines),
        _compose_section("IDENTITÉ DE L'UTILISATEUR", user_static, user_dynamic_lines),
    ]
    return '\n\n'.join(section for section in sections if section)


def _truncate_static_identity_texts(
    *,
    llm_static: str,
    user_static: str,
    max_tokens: int,
) -> tuple[str, str]:
    if max_tokens <= 0:
        return '', ''

    llm_words = llm_static.split()
    user_words = user_static.split()
    total_words = len(llm_words) + len(user_words)
    current_static_block = _build_identity_block_text(
        llm_static=llm_static,
        user_static=user_static,
        llm_dynamic_lines=[],
        user_dynamic_lines=[],
    )
    if _estimate_tokens(current_static_block) <= max_tokens:
        return llm_static, user_static
    if total_words == 0:
        return '', ''

    current_token_estimate = max(1, _estimate_tokens(current_static_block))
    word_budget = max(1, int(total_words * (max_tokens / current_token_estimate)))

    def _allocate(max_words: int) -> tuple[str, str]:
        llm_budget = min(len(llm_words), round(max_words * (len(llm_words) / total_words)))
        user_budget = min(len(user_words), max_words - llm_budget)

        if llm_words and llm_budget == 0:
            llm_budget = 1
        if user_words and user_budget == 0 and llm_budget < max_words:
            user_budget = 1

        while llm_budget + user_budget > max_words:
            if llm_budget >= user_budget and llm_budget > 0:
                llm_budget -= 1
            elif user_budget > 0:
                user_budget -= 1
            else:
                break

        return (
            _truncate_to_words(llm_static, llm_budget) if llm_budget > 0 else '',
            _truncate_to_words(user_static, user_budget) if user_budget > 0 else '',
        )

    llm_truncated, user_truncated = _allocate(word_budget)
    while word_budget > 0:
        truncated_static_block = _build_identity_block_text(
            llm_static=llm_truncated,
            user_static=user_truncated,
            llm_dynamic_lines=[],
            user_dynamic_lines=[],
        )
        if _estimate_tokens(truncated_static_block) <= max_tokens:
            return llm_truncated, user_truncated
        word_budget = max(0, word_budget - max(1, word_budget // 10))
        llm_truncated, user_truncated = _allocate(word_budget)

    return '', ''


def _emit_static_identity_read(*, target_side: str, static_text: str) -> None:
    if not chat_turn_logger.is_active():
        return
    side = 'frida' if str(target_side) == 'frida' else 'user'
    cleaned = str(static_text or '').strip()
    selected_count = 1 if cleaned else 0
    chat_turn_logger.emit(
        'identities_read',
        status='ok',
        payload=identity_observability.build_identities_read_payload(
            target_side=side,
            source_kind='static',
            selected_count=selected_count,
            content_values=[cleaned] if cleaned else [],
        ),
    )


def _resolve_identity_runtime_selection(
    *,
    llm_static: str,
    user_static: str,
) -> _IdentityRuntimeSelection:
    projection = active_identity_projection.resolve_active_identity_projection(
        llm_static=llm_static,
        user_static=user_static,
        get_mutable_identity_fn=_get_mutable_identity,
    )
    return _IdentityRuntimeSelection(
        block=projection.block,
        used_identity_ids=projection.used_identity_ids,
        frida_mutable=projection.frida_mutable,
        user_mutable=projection.user_mutable,
    )


def build_identity_block() -> tuple[str, list[str]]:
    """
    Build identity block injected at the top of system prompt.
    Returns (block_text, used_identity_ids).
    """
    llm_static = load_llm_identity()
    user_static = load_user_identity()
    _emit_static_identity_read(target_side='frida', static_text=llm_static)
    _emit_static_identity_read(target_side='user', static_text=user_static)
    selection = _resolve_identity_runtime_selection(
        llm_static=llm_static,
        user_static=user_static,
    )
    return selection.block, selection.used_identity_ids


def build_identity_input() -> dict[str, Any]:
    llm_static = load_llm_identity()
    user_static = load_user_identity()
    selection = _resolve_identity_runtime_selection(
        llm_static=llm_static,
        user_static=user_static,
    )
    return canonical_identity_input.build_identity_input(
        frida_static_content=llm_static,
        frida_static_source=_safe_static_identity_source('llm_identity_path'),
        frida_mutable=selection.frida_mutable,
        user_static_content=user_static,
        user_static_source=_safe_static_identity_source('user_identity_path'),
        user_mutable=selection.user_mutable,
    )
