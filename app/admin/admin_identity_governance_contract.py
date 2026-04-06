from __future__ import annotations

from typing import Any, Mapping

from identity import identity_governance


REASON_MAX_CHARS = 240


def text(value: Any) -> str:
    return str(value or '').strip()


def updates_mapping(value: Any) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return {str(key): raw_value for key, raw_value in value.items()}


def is_known_key(key: str) -> bool:
    return key in {item.key for item in identity_governance.list_item_specs()}


def is_editable_key(key: str) -> bool:
    return key in set(identity_governance.EDITABLE_KEYS)


def patch_payload(updates: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(key): {'value': value}
        for key, value in updates.items()
    }


def response_payload(
    *,
    ok: bool,
    reason_code: str,
    validation_ok: bool,
    validation_error: str | None,
    changed_keys: list[str],
    editable_via: str,
    source_of_truth: str,
    error: str | None = None,
    failed_checks: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        'ok': bool(ok),
        'governance_version': identity_governance.GOVERNANCE_VERSION,
        'reason_code': reason_code,
        'validation_ok': bool(validation_ok),
        'validation_error': validation_error,
        'changed_keys': list(changed_keys),
        'changed_count': len(changed_keys),
        'editable_via': editable_via,
        'source_of_truth': source_of_truth,
    }
    if error:
        payload['error'] = error
    if failed_checks:
        payload['failed_checks'] = list(failed_checks)
    return payload
