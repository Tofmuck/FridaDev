from __future__ import annotations

from typing import Any

from admin import admin_identity_mutable_edit_contract as contract


def log_compact_edit(
    admin_logs_module: Any,
    *,
    subject: str,
    action: str,
    old_len: int,
    new_len: int,
    changed: bool,
    stored_after: bool,
    validation_ok: bool,
    validation_error: str | None,
    reason_code: str,
    reason_len: int,
) -> None:
    log_event = getattr(admin_logs_module, 'log_event', None)
    if not callable(log_event):
        return
    log_event(
        'identity_mutable_admin_edit',
        subject=subject,
        action=action,
        old_len=int(old_len),
        new_len=int(new_len),
        changed=bool(changed),
        stored_after=bool(stored_after),
        validation_ok=bool(validation_ok),
        validation_error=validation_error,
        reason_code=reason_code,
        reason_len=int(reason_len),
        active_identity_source=contract.ACTIVE_IDENTITY_SOURCE,
        active_prompt_contract=contract.ACTIVE_PROMPT_CONTRACT,
        identity_input_schema_version=contract.IDENTITY_INPUT_SCHEMA_VERSION,
    )
