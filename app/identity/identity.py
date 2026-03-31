#!/usr/bin/env python3
from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import config
from admin import runtime_settings
from core.hermeneutic_node.inputs import identity_input as canonical_identity_input
from core import token_utils
from observability import chat_turn_logger

logger = logging.getLogger('frida.identity')


def _runtime_main_model_name() -> str:
    view = runtime_settings.get_main_model_settings()
    return str(view.payload['model']['value'])


def _runtime_resource_path(field: str) -> str:
    view = runtime_settings.get_resources_settings()
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return str(payload['value'])

    env_bundle = runtime_settings.build_env_seed_bundle('resources')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return str(fallback['value'])

    raise KeyError(f'missing resources runtime value: {field}')


def _load_file(path_str: str) -> str:
    path = Path(path_str)
    if not path.is_absolute():
        path = Path(__file__).resolve().parent.parent / path
    if not path.exists():
        return ''
    try:
        return path.read_text(encoding='utf-8').strip()
    except Exception as exc:
        logger.warning('identity_load_error path=%s err=%s', path, exc)
        return ''


def load_llm_identity() -> str:
    return _load_file(_runtime_resource_path('llm_identity_path'))


def load_user_identity() -> str:
    return _load_file(_runtime_resource_path('user_identity_path'))


def _safe_static_identity_source(field: str) -> str | None:
    try:
        return _runtime_resource_path(field)
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


def _count_tokens(text: str) -> int:
    if not text:
        return 0
    try:
        return token_utils.count_tokens([{'content': text}], _runtime_main_model_name())
    except Exception as exc:
        logger.warning('identity_token_count_error err=%s', exc)
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


def _selected_dynamic_entries(subject: str) -> list[dict[str, Any]]:
    return _select_ranked_entries(subject)[: max(1, config.IDENTITY_TOP_N)]


def _build_dynamic_lines(subject: str, max_tokens: int) -> tuple[list[str], list[str]]:
    if max_tokens <= 0:
        return [], []

    lines: list[str] = []
    ids: list[str] = []
    spent_tokens = 0

    for entry in _select_ranked_entries(subject):
        if len(lines) >= max(1, config.IDENTITY_TOP_N):
            break
        line = _format_identity_line(entry)
        if not line:
            continue
        line_tokens = _count_tokens(line)
        if spent_tokens + line_tokens > max_tokens:
            continue
        lines.append(line)
        if entry.get('id'):
            ids.append(str(entry['id']))
        spent_tokens += line_tokens

    return lines, ids


def _compose_section(title: str, static_text: str, dynamic_lines: list[str]) -> str:
    parts = []
    if static_text:
        parts.append(static_text)
    if dynamic_lines:
        parts.append('\n'.join(dynamic_lines))
    if not parts:
        return ''
    return f'[{title}]\n' + '\n\n'.join(parts)


def _emit_static_identity_read(*, target_side: str, static_text: str) -> None:
    if not chat_turn_logger.is_active():
        return
    side = 'frida' if str(target_side) == 'frida' else 'user'
    cleaned = str(static_text or '').strip()
    selected_count = 1 if cleaned else 0
    chat_turn_logger.emit(
        'identities_read',
        status='ok',
        payload={
            'target_side': side,
            'source_kind': 'static',
            'frida_count': selected_count if side == 'frida' else 0,
            'user_count': selected_count if side == 'user' else 0,
            'selected_count': selected_count,
            'truncated': bool(cleaned and len(cleaned) > 120),
            'keys': [f'static_{side}_identity'] if cleaned else [],
            'preview': [cleaned] if cleaned else [],
        },
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

    static_sections = [
        _compose_section('IDENTITÉ DU MODÈLE', llm_static, []),
        _compose_section("IDENTITÉ DE L'UTILISATEUR", user_static, []),
    ]
    static_block = '\n\n'.join(section for section in static_sections if section)

    budget = max(1, config.IDENTITY_MAX_TOKENS)
    static_tokens = _count_tokens(static_block)
    remaining_tokens = max(0, budget - static_tokens)

    active_subjects = 2
    per_subject_budget = remaining_tokens // active_subjects if remaining_tokens > 0 else 0

    llm_lines, llm_ids = _build_dynamic_lines('llm', per_subject_budget)
    user_lines, user_ids = _build_dynamic_lines('user', per_subject_budget)

    # If only one side has dynamic candidates, give it the whole remaining budget.
    if remaining_tokens > 0 and llm_lines and not user_lines:
        llm_lines, llm_ids = _build_dynamic_lines('llm', remaining_tokens)
    elif remaining_tokens > 0 and user_lines and not llm_lines:
        user_lines, user_ids = _build_dynamic_lines('user', remaining_tokens)

    sections = [
        _compose_section('IDENTITÉ DU MODÈLE', llm_static, llm_lines),
        _compose_section("IDENTITÉ DE L'UTILISATEUR", user_static, user_lines),
    ]
    block = '\n\n'.join(section for section in sections if section)

    # Hard guardrail on identity budget.
    if _count_tokens(block) > budget:
        block = static_block
    if _count_tokens(block) > budget:
        block = _truncate_to_words(block, budget)

    return block, llm_ids + user_ids


def build_identity_input() -> dict[str, Any]:
    return canonical_identity_input.build_identity_input(
        frida_static_content=load_llm_identity(),
        frida_static_source=_safe_static_identity_source('llm_identity_path'),
        frida_dynamic_entries=_selected_dynamic_entries('llm'),
        user_static_content=load_user_identity(),
        user_static_source=_safe_static_identity_source('user_identity_path'),
        user_dynamic_entries=_selected_dynamic_entries('user'),
    )
