from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ASSISTANT_TURN_META_KEY = 'assistant_turn'
ASSISTANT_TURN_STATUS_INTERRUPTED = 'interrupted'


def build_interrupted_assistant_turn_meta(error_code: str | None = None) -> dict[str, dict[str, str]]:
    payload = {'status': ASSISTANT_TURN_STATUS_INTERRUPTED}
    error_code_norm = str(error_code or '').strip()
    if error_code_norm:
        payload['error_code'] = error_code_norm
    return {ASSISTANT_TURN_META_KEY: payload}


def get_assistant_turn_state(message: Mapping[str, Any] | None) -> dict[str, str] | None:
    if not isinstance(message, Mapping):
        return None
    raw_meta = message.get('meta')
    if not isinstance(raw_meta, Mapping):
        return None
    raw_turn = raw_meta.get(ASSISTANT_TURN_META_KEY)
    if not isinstance(raw_turn, Mapping):
        return None
    status = str(raw_turn.get('status') or '').strip().lower()
    if not status:
        return None
    state = {'status': status}
    error_code = str(raw_turn.get('error_code') or '').strip()
    if error_code:
        state['error_code'] = error_code
    return state


def is_interrupted_assistant_turn(message: Mapping[str, Any] | None) -> bool:
    state = get_assistant_turn_state(message)
    if state is None:
        return False
    return state.get('status') == ASSISTANT_TURN_STATUS_INTERRUPTED
