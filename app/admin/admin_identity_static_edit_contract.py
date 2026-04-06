from __future__ import annotations

from typing import Any

from identity import static_identity_content


ACTIVE_STATIC_SOURCE = static_identity_content.ACTIVE_STATIC_SOURCE
ACTIVE_PROMPT_CONTRACT = 'static + mutable narrative'
IDENTITY_INPUT_SCHEMA_VERSION = 'v2'
STATIC_SOURCE_KIND = static_identity_content.STATIC_STORAGE_KIND
EDIT_UPDATED_BY = 'admin_identity_static_edit'
EDITABLE_VIA = static_identity_content.STATIC_EDIT_ROUTE
REASON_MAX_CHARS = 240
_ALLOWED_SUBJECTS = {'llm', 'user'}
_ALLOWED_ACTIONS = {'set', 'clear'}


def text(value: Any) -> str:
    return str(value or '').strip()


def raw_content(value: Any) -> str:
    if value is None:
        return ''
    return str(value)


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
    resource_field: str,
    resolution_kind: str,
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
        'active_static_source': ACTIVE_STATIC_SOURCE,
        'static_source_kind': STATIC_SOURCE_KIND,
        'resource_field': resource_field,
        'resolution_kind': resolution_kind,
        'editable_via': EDITABLE_VIA,
        'active_prompt_contract': ACTIVE_PROMPT_CONTRACT,
        'identity_input_schema_version': IDENTITY_INPUT_SCHEMA_VERSION,
    }
    if error:
        payload['error'] = error
        payload['error_code'] = validation_error or reason_code
    return payload
