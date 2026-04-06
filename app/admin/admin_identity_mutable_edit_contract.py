from __future__ import annotations

from typing import Any, Mapping

import config


ACTIVE_IDENTITY_SOURCE = 'identity_mutables'
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
IDENTITY_INPUT_SCHEMA_VERSION = 'v2'
EDIT_UPDATED_BY = 'admin_identity_mutable_edit'
REASON_MAX_CHARS = 240
_ALLOWED_SUBJECTS = {'llm', 'user'}
_ALLOWED_ACTIONS = {'set', 'clear'}


def text(value: Any) -> str:
    return str(value or '').strip()


def current_content(item: Mapping[str, Any] | None) -> str:
    if not isinstance(item, Mapping):
        return ''
    return text(item.get('content'))


def normalize_subject(value: Any) -> str:
    normalized = text(value).lower()
    if normalized not in _ALLOWED_SUBJECTS:
        return ''
    return normalized


def normalize_action(value: Any) -> str:
    normalized = text(value).lower()
    if normalized not in _ALLOWED_ACTIONS:
        return ''
    return normalized


def budget_payload() -> dict[str, int]:
    return {
        'target_chars': int(config.IDENTITY_MUTABLE_TARGET_CHARS),
        'max_chars': int(config.IDENTITY_MUTABLE_MAX_CHARS),
    }


def response_payload(
    *,
    ok: bool,
    subject: str,
    action: str,
    old_len: int,
    new_len: int,
    changed: bool,
    stored_after: bool,
    validation_ok: bool,
    reason_code: str,
    validation_error: str | None = None,
    error: str | None = None,
) -> dict[str, Any]:
    payload = {
        'ok': bool(ok),
        'subject': subject,
        'action': action,
        'old_len': int(old_len),
        'new_len': int(new_len),
        'changed': bool(changed),
        'stored_after': bool(stored_after),
        'validation_ok': bool(validation_ok),
        'validation_error': validation_error,
        'reason_code': reason_code,
        'active_identity_source': ACTIVE_IDENTITY_SOURCE,
        'active_prompt_contract': ACTIVE_PROMPT_CONTRACT,
        'identity_input_schema_version': IDENTITY_INPUT_SCHEMA_VERSION,
        'mutable_budget': budget_payload(),
    }
    if error:
        payload['error'] = error
        payload['error_code'] = validation_error or reason_code
    return payload
