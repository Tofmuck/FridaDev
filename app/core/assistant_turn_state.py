from __future__ import annotations

from collections.abc import Mapping
from typing import Any


ASSISTANT_TURN_META_KEY = 'assistant_turn'
ASSISTANT_TURN_STATUS_INTERRUPTED = 'interrupted'
ASSISTANT_TURN_STATUS_DIALOGIC_PRESENCE = 'dialogic_presence'
ASSISTANT_RUNTIME_PROVENANCE_META_KEY = 'assistant_runtime_provenance'
ASSISTANT_RUNTIME_PROVENANCE_SCHEMA_VERSION = 'v1'
ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_MAIN_MODEL = 'main_model'
ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK = 'final_lock'
ASSISTANT_RUNTIME_PROVENANCE_MARKER_HEADER = '[PROVENANCE RUNTIME ASSISTANT v1]'


def build_interrupted_assistant_turn_meta(error_code: str | None = None) -> dict[str, dict[str, str]]:
    payload = {'status': ASSISTANT_TURN_STATUS_INTERRUPTED}
    error_code_norm = str(error_code or '').strip()
    if error_code_norm:
        payload['error_code'] = error_code_norm
    return {ASSISTANT_TURN_META_KEY: payload}


def build_dialogic_presence_assistant_turn_meta() -> dict[str, dict[str, str]]:
    return {
        ASSISTANT_TURN_META_KEY: {
            'status': ASSISTANT_TURN_STATUS_DIALOGIC_PRESENCE,
        }
    }


def build_assistant_runtime_provenance_meta(
    *,
    response_origin: str,
    web_context_injected_to_main_model: bool,
) -> dict[str, dict[str, Any]]:
    origin = str(response_origin or '').strip()
    if origin not in {
        ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_MAIN_MODEL,
        ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK,
    }:
        raise ValueError('invalid_assistant_runtime_provenance_origin')
    web_injected = bool(web_context_injected_to_main_model)
    if origin == ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK and web_injected:
        raise ValueError('final_lock_cannot_receive_main_model_web_context')
    return {
        ASSISTANT_RUNTIME_PROVENANCE_META_KEY: {
            'schema_version': ASSISTANT_RUNTIME_PROVENANCE_SCHEMA_VERSION,
            'response_origin': origin,
            'web_context_injected_to_main_model': web_injected,
        }
    }


def merge_assistant_message_meta(
    existing_meta: Mapping[str, Any] | None,
    runtime_provenance_meta: Mapping[str, Any],
) -> dict[str, Any]:
    merged = dict(existing_meta or {})
    merged.update(dict(runtime_provenance_meta))
    return merged


def get_assistant_runtime_provenance(
    message: Mapping[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(message, Mapping):
        return None
    if str(message.get('role') or '').strip().lower() != 'assistant':
        return None
    raw_meta = message.get('meta')
    if not isinstance(raw_meta, Mapping):
        return None
    raw_provenance = raw_meta.get(ASSISTANT_RUNTIME_PROVENANCE_META_KEY)
    if not isinstance(raw_provenance, Mapping):
        return None
    if set(raw_provenance) != {
        'schema_version',
        'response_origin',
        'web_context_injected_to_main_model',
    }:
        return None
    if str(raw_provenance.get('schema_version') or '') != ASSISTANT_RUNTIME_PROVENANCE_SCHEMA_VERSION:
        return None
    origin = str(raw_provenance.get('response_origin') or '').strip()
    if origin not in {
        ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_MAIN_MODEL,
        ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK,
    }:
        return None
    web_injected = raw_provenance.get('web_context_injected_to_main_model')
    if not isinstance(web_injected, bool):
        return None
    if origin == ASSISTANT_RUNTIME_PROVENANCE_ORIGIN_FINAL_LOCK and web_injected:
        return None
    return {
        'schema_version': ASSISTANT_RUNTIME_PROVENANCE_SCHEMA_VERSION,
        'response_origin': origin,
        'web_context_injected_to_main_model': web_injected,
    }


def build_assistant_runtime_provenance_prompt_marker(
    message: Mapping[str, Any] | None,
) -> dict[str, str] | None:
    provenance = get_assistant_runtime_provenance(message)
    if provenance is None:
        return None
    web_context = (
        'injected'
        if provenance['web_context_injected_to_main_model']
        else 'not_injected'
    )
    return {
        'role': 'system',
        'content': (
            f'{ASSISTANT_RUNTIME_PROVENANCE_MARKER_HEADER}\n'
            f"response_origin={provenance['response_origin']}; "
            f'web_context={web_context}.'
        ),
    }


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
    if not isinstance(message, Mapping):
        return False
    if str(message.get('role') or '').strip().lower() != 'assistant':
        return False
    state = get_assistant_turn_state(message)
    if state is None:
        return False
    return state.get('status') == ASSISTANT_TURN_STATUS_INTERRUPTED


def is_dialogic_presence_assistant_turn(message: Mapping[str, Any] | None) -> bool:
    if not isinstance(message, Mapping):
        return False
    if str(message.get('role') or '').strip().lower() != 'assistant':
        return False
    state = get_assistant_turn_state(message)
    if state is None:
        return False
    return state.get('status') == ASSISTANT_TURN_STATUS_DIALOGIC_PRESENCE
