from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from observability.observability_payload_guard_schema import (
    _GENERAL_SAFE_TEXT_LIST_KEYS,
    _MANIFEST_DYNAMIC_INT_MAP_KEYS,
    _MANIFEST_SAFE_TEXT_KEYS,
    _MANIFEST_TEXT_LIST_KEYS,
    _QUALIFIED_RAW_FLAGS,
    _dangerous_key_class,
    _dangerous_value_class,
    _is_main_payload_manifest,
    _is_manifest_bool_key,
    _is_manifest_number_key,
    _is_safe_general_container_key,
    _is_safe_general_scalar_key,
    _is_safe_general_text_key,
    _is_safe_general_text_value,
    _is_safe_manifest_text_value,
    _manifest_allowed_keys,
    _manifest_child_context,
    _safe_dynamic_name,
)


SCHEMA_VERSION = "observability_payload_guard_v1"
REASON_CODE = "observability_payload_rejected"

_MAX_DEPTH = 8


@dataclass(frozen=True)
class PayloadGuardDecision:
    accepted: bool
    payload: dict[str, Any]


def _safe_key(key: Any) -> str:
    return str(key or "").strip()


def _safe_class(value: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return "unknown"
    allowed = set("abcdefghijklmnopqrstuvwxyz0123456789_.-")
    return text if text[0].isalnum() and len(text) <= 160 and all(char in allowed for char in text) else "unknown"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _add_issue(issues: dict[str, int], issue_class: str) -> None:
    issue = _safe_class(issue_class)
    issues[issue] = issues.get(issue, 0) + 1


def _inspect_manifest_scalar(key: str, value: Any, issues: dict[str, int]) -> None:
    if key in _QUALIFIED_RAW_FLAGS:
        if value is not False:
            _add_issue(issues, "raw_flag_true")
        return
    issue = _dangerous_value_class(key, value)
    if issue:
        _add_issue(issues, issue)
        return
    if value is None:
        if key not in {"enabled", "estimated_prompt_tokens", "estimated_tokens"}:
            _add_issue(issues, "manifest_unexpected_value")
        return
    if isinstance(value, bool):
        if not _is_manifest_bool_key(key):
            _add_issue(issues, "manifest_unexpected_value")
        return
    if isinstance(value, (int, float)):
        if not _is_manifest_number_key(key):
            _add_issue(issues, "manifest_unexpected_value")
        return
    if isinstance(value, str):
        if key not in _MANIFEST_SAFE_TEXT_KEYS or not _is_safe_manifest_text_value(key, value):
            _add_issue(issues, "manifest_unexpected_value")
        return
    _add_issue(issues, "manifest_unexpected_value")


def _inspect_manifest_text_list(key: str, values: list[Any], issues: dict[str, int]) -> None:
    if key not in _MANIFEST_TEXT_LIST_KEYS:
        _add_issue(issues, "manifest_unexpected_value")
        return
    for value in values:
        if not isinstance(value, str) or not _is_safe_manifest_text_value(key, value):
            _add_issue(issues, "manifest_unexpected_value")


def _inspect_manifest_list(key: str, values: list[Any], issues: dict[str, int], depth: int, context: str) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    if context == "top" and key == "messages":
        for value in values:
            if isinstance(value, Mapping):
                _inspect_manifest_mapping(value, issues, depth + 1, "message")
            else:
                _add_issue(issues, "manifest_unexpected_value")
        return
    if key in _MANIFEST_TEXT_LIST_KEYS:
        _inspect_manifest_text_list(key, values, issues)
        return
    _add_issue(issues, "manifest_unexpected_value")


def _inspect_manifest_dynamic_int_map(payload: Mapping[str, Any], issues: dict[str, int]) -> None:
    for raw_key, value in payload.items():
        if not _safe_dynamic_name(raw_key) or not isinstance(value, int):
            _add_issue(issues, "manifest_unexpected_value")


def _inspect_manifest_mapping(payload: Mapping[str, Any], issues: dict[str, int], depth: int, context: str) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    if context == "manifest_dynamic_int_map":
        _inspect_manifest_dynamic_int_map(payload, issues)
        return

    allowed_keys = _manifest_allowed_keys(context)
    if context not in {"lane_statuses"} and not allowed_keys:
        _add_issue(issues, "manifest_unexpected_key")
        return

    for raw_key, value in payload.items():
        key = _safe_key(raw_key)
        lower = key.lower()
        if not key:
            _add_issue(issues, "manifest_unexpected_key")
            continue
        if context == "lane_statuses":
            if not _safe_dynamic_name(lower):
                _add_issue(issues, "manifest_unexpected_key")
                continue
            if isinstance(value, Mapping):
                _inspect_manifest_mapping(value, issues, depth + 1, "lane_status")
            else:
                _add_issue(issues, "manifest_unexpected_value")
            continue
        if lower not in allowed_keys:
            _add_issue(issues, "manifest_unexpected_key")
            continue
        if lower in _QUALIFIED_RAW_FLAGS and value is not False:
            _add_issue(issues, "raw_flag_true")
            continue
        if isinstance(value, Mapping):
            child_context = _manifest_child_context(context, lower)
            if not child_context:
                _add_issue(issues, "manifest_unexpected_value")
                continue
            _inspect_manifest_mapping(value, issues, depth + 1, child_context)
        elif isinstance(value, list):
            _inspect_manifest_list(lower, value, issues, depth + 1, context)
        else:
            _inspect_manifest_scalar(lower, value, issues)


def _inspect_general_scalar(key: str, value: Any, issues: dict[str, int]) -> None:
    issue = _dangerous_value_class(key, value)
    if issue:
        _add_issue(issues, issue)
        return
    if value is None:
        if not _is_safe_general_scalar_key(key):
            _add_issue(issues, "unknown_scalar_key")
        return
    if isinstance(value, bool):
        if not _is_safe_general_scalar_key(key):
            _add_issue(issues, "unknown_scalar_key")
        return
    if isinstance(value, (int, float)):
        if not _is_safe_general_scalar_key(key):
            _add_issue(issues, "unknown_scalar_key")
        return
    if isinstance(value, str):
        if not _is_safe_general_text_key(key):
            _add_issue(issues, "unknown_string_key")
            return
        if not _is_safe_general_text_value(key, value):
            _add_issue(issues, "unsafe_string_value")
        return
    _add_issue(issues, "unknown_value_type")


def _inspect_general_list(key: str, values: list[Any], issues: dict[str, int], depth: int) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    if key in _GENERAL_SAFE_TEXT_LIST_KEYS:
        for value in values:
            if not isinstance(value, str) or not _is_safe_general_text_value(key, value):
                _add_issue(issues, "unknown_list_value")
        return
    if not _is_safe_general_container_key(key):
        _add_issue(issues, "unknown_list_key")
    for value in values:
        if isinstance(value, Mapping):
            _inspect_general(value, issues, key=key, depth=depth + 1)
        elif isinstance(value, list):
            _inspect_general_list(key, value, issues, depth + 1)
        else:
            _inspect_general_scalar(key, value, issues)


def _inspect_general(value: Any, issues: dict[str, int], *, key: str = "", depth: int = 0) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            child_key = _safe_key(raw_key)
            lower = child_key.lower()
            if not child_key:
                _add_issue(issues, "empty_key")
                continue
            if lower in _QUALIFIED_RAW_FLAGS:
                if child is not False:
                    _add_issue(issues, "raw_flag_true")
                continue
            key_issue = _dangerous_key_class(child_key)
            if key_issue:
                _add_issue(issues, key_issue)
                continue
            if isinstance(child, Mapping):
                if not _is_safe_general_container_key(lower):
                    _add_issue(issues, "unknown_mapping_key")
                _inspect_general(child, issues, key=child_key, depth=depth + 1)
            elif isinstance(child, list):
                if lower not in _GENERAL_SAFE_TEXT_LIST_KEYS and not _is_safe_general_container_key(lower):
                    _add_issue(issues, "unknown_list_key")
                _inspect_general_list(lower, child, issues, depth + 1)
            else:
                _inspect_general_scalar(lower, child, issues)
        return
    if isinstance(value, list):
        _inspect_general_list(key.lower(), value, issues, depth + 1)
        return
    _inspect_general_scalar(key.lower(), value, issues)


def _build_rejection_payload(issues: dict[str, int]) -> dict[str, Any]:
    classes = sorted(issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "reason_code": REASON_CODE,
        "rejected_payload": True,
        "issue_count": sum(issues.values()),
        "issue_classes": classes,
        "issue_class_count": len(classes),
        "raw_event_payloads_included": False,
        "raw_content_included": False,
        "raw_prompt_included": False,
        "raw_message_included": False,
        "raw_lane_content_included": False,
        "raw_provider_payload_included": False,
        "raw_secret_included": False,
    }


def guard_payload(payload: Mapping[str, Any] | None) -> PayloadGuardDecision:
    source = _mapping(payload)
    issues: dict[str, int] = {}
    if _is_main_payload_manifest(source):
        _inspect_manifest_mapping(source, issues, 0, "top")
    else:
        _inspect_general(source, issues)
    if not issues:
        return PayloadGuardDecision(accepted=True, payload=dict(source))
    return PayloadGuardDecision(accepted=False, payload=_build_rejection_payload(issues))


def is_guard_rejection_payload(payload: Mapping[str, Any] | None) -> bool:
    source = _mapping(payload)
    return (
        source.get("schema_version") == SCHEMA_VERSION
        and source.get("reason_code") == REASON_CODE
        and bool(source.get("rejected_payload"))
    )
