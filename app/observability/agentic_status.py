from __future__ import annotations

from typing import Any


STATUS_SCHEMA_VERSION = 'agentic_v1'

STATUS_OK = 'ok'
STATUS_SKIPPED = 'skipped'
STATUS_DISABLED = 'disabled'
STATUS_NOT_SELECTED = 'not_selected'
STATUS_NOT_CONFIGURED = 'not_configured'
STATUS_NOT_APPLICABLE = 'not_applicable'
STATUS_REFUSED = 'refused'
STATUS_FAILED = 'failed'
STATUS_ERROR = 'error'

STATUS_V1_ALLOWED: tuple[str, ...] = (
    STATUS_OK,
    STATUS_SKIPPED,
    STATUS_DISABLED,
    STATUS_NOT_SELECTED,
    STATUS_NOT_CONFIGURED,
    STATUS_NOT_APPLICABLE,
    STATUS_REFUSED,
    STATUS_FAILED,
    STATUS_ERROR,
)
STATUS_V1_ALLOWED_SET = set(STATUS_V1_ALLOWED)

LEGACY_STATUSES = {
    STATUS_OK,
    STATUS_SKIPPED,
    STATUS_ERROR,
}
NON_PROBLEM_STATUSES = {
    STATUS_OK,
    STATUS_SKIPPED,
    STATUS_DISABLED,
    STATUS_NOT_SELECTED,
    STATUS_NOT_CONFIGURED,
    STATUS_NOT_APPLICABLE,
    STATUS_REFUSED,
}
ATTEMPT_FAILURE_STATUSES = {
    STATUS_FAILED,
    STATUS_ERROR,
}


def normalize_status(value: Any, *, default: str = STATUS_OK) -> str:
    status = str(value or '').strip().lower()
    if status in STATUS_V1_ALLOWED_SET:
        return status
    fallback = str(default or STATUS_OK).strip().lower()
    if fallback in STATUS_V1_ALLOWED_SET:
        return fallback
    return STATUS_OK


def is_valid_status(value: Any) -> bool:
    return str(value or '').strip().lower() in STATUS_V1_ALLOWED_SET


def is_non_problem_status(value: Any) -> bool:
    return normalize_status(value) in NON_PROBLEM_STATUSES


def is_problem_status(value: Any) -> bool:
    return normalize_status(value) in ATTEMPT_FAILURE_STATUSES


def projected_schema_version(*, payload: dict[str, Any] | None, status: Any) -> str:
    payload_obj = payload if isinstance(payload, dict) else {}
    explicit = str(payload_obj.get('status_schema_version') or '').strip()
    if explicit:
        return explicit
    status_norm = normalize_status(status)
    if status_norm not in LEGACY_STATUSES:
        return STATUS_SCHEMA_VERSION
    return 'legacy'
