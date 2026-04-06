from __future__ import annotations

from typing import Any, Mapping


def log_compact_edit(
    admin_logs_module: Any,
    *,
    changed_keys: list[str],
    old_values: Mapping[str, Any],
    new_values: Mapping[str, Any],
    validation_ok: bool,
    validation_error: str | None,
    reason_code: str,
    reason_len: int,
    source_of_truth: str,
) -> None:
    admin_logs_module.log_event(
        'identity_governance_admin_edit',
        changed_keys=list(changed_keys),
        changed_count=len(changed_keys),
        old_values={str(key): value for key, value in old_values.items()},
        new_values={str(key): value for key, value in new_values.items()},
        validation_ok=bool(validation_ok),
        validation_error=validation_error,
        reason_code=reason_code,
        reason_len=int(reason_len),
        source_of_truth=source_of_truth,
    )
