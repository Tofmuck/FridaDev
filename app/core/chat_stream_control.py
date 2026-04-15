from __future__ import annotations

import json
from typing import Any


STREAM_CONTROL_PREFIX = '\x1e'
STREAM_CONTROL_KIND = 'frida-stream-control'
STREAM_TERMINAL_DONE = 'done'
STREAM_TERMINAL_ERROR = 'error'
STREAM_TERMINAL_EVENTS = frozenset({STREAM_TERMINAL_DONE, STREAM_TERMINAL_ERROR})


def build_terminal_chunk(
    event: str,
    *,
    error_code: str | None = None,
    updated_at: str | None = None,
) -> str:
    event_norm = str(event or '').strip().lower()
    if event_norm not in STREAM_TERMINAL_EVENTS:
        raise ValueError(f'unsupported stream terminal event: {event!r}')
    payload: dict[str, Any] = {
        'kind': STREAM_CONTROL_KIND,
        'event': event_norm,
    }
    error_code_norm = str(error_code or '').strip()
    if event_norm == STREAM_TERMINAL_ERROR and error_code_norm:
        payload['error_code'] = error_code_norm
    updated_at_norm = str(updated_at or '').strip()
    if updated_at_norm:
        payload['updated_at'] = updated_at_norm
    return f'{STREAM_CONTROL_PREFIX}{json.dumps(payload, ensure_ascii=True, separators=(",", ":"))}\n'


def parse_terminal_chunk(chunk: str | bytes | bytearray | None) -> dict[str, str] | None:
    if chunk is None:
        return None
    if isinstance(chunk, (bytes, bytearray)):
        text = bytes(chunk).decode('utf-8', errors='ignore')
    else:
        text = str(chunk)
    if not text.startswith(STREAM_CONTROL_PREFIX) or not text.endswith('\n'):
        return None
    try:
        payload = json.loads(text[len(STREAM_CONTROL_PREFIX):-1])
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    if str(payload.get('kind') or '') != STREAM_CONTROL_KIND:
        return None
    event = str(payload.get('event') or '').strip().lower()
    if event not in STREAM_TERMINAL_EVENTS:
        return None
    terminal = {'event': event}
    error_code = str(payload.get('error_code') or '').strip()
    if error_code:
        terminal['error_code'] = error_code
    updated_at = str(payload.get('updated_at') or '').strip()
    if updated_at:
        terminal['updated_at'] = updated_at
    return terminal


def split_text_and_terminal(raw_text: str | bytes | bytearray) -> tuple[str, dict[str, str] | None]:
    if isinstance(raw_text, (bytes, bytearray)):
        text = bytes(raw_text).decode('utf-8', errors='ignore')
    else:
        text = str(raw_text)
    marker_index = text.rfind(STREAM_CONTROL_PREFIX)
    if marker_index < 0:
        return text, None
    terminal = parse_terminal_chunk(text[marker_index:])
    if terminal is None:
        return text, None
    return text[:marker_index], terminal
