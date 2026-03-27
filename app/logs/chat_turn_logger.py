from __future__ import annotations

import logging
import time
import uuid
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from logs import log_store

logger = logging.getLogger('frida.chat_turn_logger')

_PREVIEW_MAX_ITEMS = 3
_PREVIEW_MAX_CHARS = 120
_PENDING_CONVERSATION_ID = '__pending__'


@dataclass
class TurnContext:
    turn_id: str
    conversation_id: str
    started_at: float
    seq: int = 0
    state: dict[str, Any] = field(default_factory=dict)


_CURRENT_TURN: ContextVar[TurnContext | None] = ContextVar('frida_chat_turn_logger_ctx', default=None)


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _normalize_text(value: Any, *, max_chars: int = _PREVIEW_MAX_CHARS) -> str:
    text = str(value or '').strip().replace('\n', ' ')
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + '…'


def _sanitize_payload(payload: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key == 'truncated' and 'preview' in payload:
            # Preserve computed truncation from preview sanitization.
            continue
        if key == 'preview' and isinstance(value, list):
            out[key] = [_normalize_text(item) for item in value[:_PREVIEW_MAX_ITEMS]]
            out['truncated'] = bool(payload.get('truncated', False) or len(value) > _PREVIEW_MAX_ITEMS)
            continue
        if key == 'keys' and isinstance(value, list):
            out[key] = [_normalize_text(item, max_chars=64) for item in value[:_PREVIEW_MAX_ITEMS]]
            continue
        if key.endswith('_preview'):
            out[key] = _normalize_text(value)
            continue
        out[key] = value
    return out


def _current() -> TurnContext | None:
    return _CURRENT_TURN.get()


def _emit_now(
    ctx: TurnContext,
    *,
    stage: str,
    status: str,
    payload: dict[str, Any] | None,
    duration_ms: float | None,
    model: str | None,
    prompt_kind: str | None,
    reason_code: str | None,
    error_code: str | None,
) -> bool:
    payload_json = _sanitize_payload(dict(payload or {}))
    status_norm = str(status or 'ok').strip().lower()

    if model:
        payload_json['model'] = str(model)
    if prompt_kind:
        payload_json['prompt_kind'] = str(prompt_kind)

    if status_norm == 'skipped':
        reason = str(reason_code or payload_json.get('reason_code') or '').strip() or 'not_applicable'
        payload_json['reason_code'] = reason
    if status_norm == 'error' and error_code:
        payload_json['error_code'] = str(error_code)

    ctx.seq += 1
    event = {
        'event_id': f'{ctx.turn_id}:{ctx.seq:04d}:{stage}',
        'conversation_id': ctx.conversation_id,
        'turn_id': ctx.turn_id,
        'ts': _now_iso(),
        'stage': str(stage),
        'status': status_norm,
        'duration_ms': int(round(float(duration_ms))) if duration_ms is not None else None,
        'payload_json': payload_json,
    }

    try:
        return bool(log_store.insert_chat_log_event(event))
    except Exception as exc:
        logger.warning('chat_turn_log_emit_failed stage=%s err=%s', stage, exc)
        return False


def _flush_pending_events(ctx: TurnContext) -> None:
    pending_turn_start = ctx.state.pop('_pending_turn_start_payload', None)
    if isinstance(pending_turn_start, dict):
        _emit_now(
            ctx,
            stage='turn_start',
            status='ok',
            payload=pending_turn_start,
            duration_ms=None,
            model=None,
            prompt_kind=None,
            reason_code=None,
            error_code=None,
        )

    pending_events = ctx.state.pop('_pending_events', [])
    if not isinstance(pending_events, list):
        return
    for entry in pending_events:
        if not isinstance(entry, dict):
            continue
        _emit_now(
            ctx,
            stage=str(entry.get('stage') or ''),
            status=str(entry.get('status') or 'ok'),
            payload=entry.get('payload'),
            duration_ms=entry.get('duration_ms'),
            model=entry.get('model'),
            prompt_kind=entry.get('prompt_kind'),
            reason_code=entry.get('reason_code'),
            error_code=entry.get('error_code'),
        )


def is_active() -> bool:
    return _current() is not None


def begin_turn(*, conversation_id: str | None, user_msg: str, web_search_enabled: bool) -> Token:
    conv_id = str(conversation_id or '').strip() or _PENDING_CONVERSATION_ID
    ctx = TurnContext(
        turn_id=f'turn-{uuid.uuid4()}',
        conversation_id=conv_id,
        started_at=time.perf_counter(),
    )
    token = _CURRENT_TURN.set(ctx)
    turn_start_payload = {
        'web_search_enabled': bool(web_search_enabled),
        'user_msg_chars': len(str(user_msg or '')),
    }
    if conv_id == _PENDING_CONVERSATION_ID:
        ctx.state['_pending_turn_start_payload'] = turn_start_payload
    else:
        _emit_now(
            ctx,
            stage='turn_start',
            status='ok',
            payload=turn_start_payload,
            duration_ms=None,
            model=None,
            prompt_kind=None,
            reason_code=None,
            error_code=None,
        )
    return token


def end_turn(token: Token, *, final_status: str = 'ok') -> None:
    try:
        finish_turn(final_status=final_status)
    finally:
        _CURRENT_TURN.reset(token)


def update_conversation_id(conversation_id: str | None) -> None:
    ctx = _current()
    if ctx is None:
        return
    conv_id = str(conversation_id or '').strip()
    if conv_id:
        was_pending = ctx.conversation_id == _PENDING_CONVERSATION_ID
        ctx.conversation_id = conv_id
        if was_pending:
            _flush_pending_events(ctx)


def get_state(key: str, default: Any = None) -> Any:
    ctx = _current()
    if ctx is None:
        return default
    return ctx.state.get(key, default)


def set_state(key: str, value: Any) -> None:
    ctx = _current()
    if ctx is None:
        return
    ctx.state[key] = value


def emit(
    stage: str,
    *,
    status: str = 'ok',
    payload: dict[str, Any] | None = None,
    duration_ms: float | None = None,
    model: str | None = None,
    prompt_kind: str | None = None,
    reason_code: str | None = None,
    error_code: str | None = None,
) -> bool:
    ctx = _current()
    if ctx is None:
        return False

    if ctx.conversation_id == _PENDING_CONVERSATION_ID and str(stage) != 'turn_start':
        pending_events = ctx.state.setdefault('_pending_events', [])
        if isinstance(pending_events, list):
            pending_events.append(
                {
                    'stage': str(stage),
                    'status': str(status or 'ok'),
                    'payload': dict(payload or {}),
                    'duration_ms': duration_ms,
                    'model': model,
                    'prompt_kind': prompt_kind,
                    'reason_code': reason_code,
                    'error_code': error_code,
                }
            )
            return True
        return False

    return _emit_now(
        ctx,
        stage=str(stage),
        status=str(status or 'ok'),
        payload=payload,
        duration_ms=duration_ms,
        model=model,
        prompt_kind=prompt_kind,
        reason_code=reason_code,
        error_code=error_code,
    )


def emit_error(*, error_code: str, error_class: str, message_short: str) -> bool:
    return emit(
        'error',
        status='error',
        error_code=error_code,
        payload={
            'error_code': error_code,
            'error_class': _normalize_text(error_class, max_chars=80),
            'message_short': _normalize_text(message_short, max_chars=160),
        },
    )


def emit_branch_skipped(*, reason_code: str, reason_short: str) -> bool:
    return emit(
        'branch_skipped',
        status='skipped',
        reason_code=reason_code,
        payload={
            'reason_code': reason_code,
            'reason_short': _normalize_text(reason_short, max_chars=160),
        },
    )


def finish_turn(*, final_status: str) -> bool:
    ctx = _current()
    if ctx is None:
        return False
    if ctx.conversation_id == _PENDING_CONVERSATION_ID:
        # Fallback id for early failures where no conversation id was ever resolved.
        ctx.conversation_id = f'orphan:{ctx.turn_id}'
        _flush_pending_events(ctx)

    final_status_norm = str(final_status or 'ok').strip().lower()
    turn_end_status = 'error' if final_status_norm == 'error' else 'ok'
    total_ms = max(0.0, (time.perf_counter() - ctx.started_at) * 1000.0)
    return emit(
        'turn_end',
        status=turn_end_status,
        duration_ms=total_ms,
        payload={
            'total_duration_ms': int(round(total_ms)),
            'final_status': final_status_norm,
        },
    )
