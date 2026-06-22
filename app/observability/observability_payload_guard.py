from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


SCHEMA_VERSION = "observability_payload_guard_v1"
REASON_CODE = "observability_payload_rejected"

_MAX_DEPTH = 8
_SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,159}$")
_SAFE_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")

_QUALIFIED_RAW_FLAGS = {
    "raw_content_included",
    "raw_content_stored",
    "raw_error_message_included",
    "raw_error_message_stored",
    "raw_event_payloads_included",
    "raw_lane_content_included",
    "raw_log_included",
    "raw_message_included",
    "raw_policy_text_included",
    "raw_prompt_included",
    "raw_provider_payload_included",
    "raw_secret_included",
    "raw_webdav_payload_included",
}

_DANGEROUS_EXACT_KEYS = {
    "authorization",
    "base64",
    "content",
    "cookie",
    "data_url",
    "dav",
    "etag",
    "header",
    "image_data_url",
    "message",
    "messages",
    "password",
    "path",
    "payload",
    "prompt",
    "provider_payload",
    "raw",
    "raw_payload",
    "secret",
    "text",
    "token",
    "url",
    "xml",
}

_DANGEROUS_PAYLOAD_KEYS = {
    "provider_payload",
    "raw_payload",
    "request_payload",
    "response_payload",
}

_MANIFEST_TOP_LEVEL_KEYS = {
    "assistant_output_policy",
    "budgets",
    "conversation_id_present",
    "conversation_state",
    "final_response_lock",
    "hash_policy",
    "lane_statuses",
    "main_model_called",
    "messages",
    "provider",
    "raw_flags",
    "runtime_settings",
    "schema_version",
    "scope",
    "status_schema_version",
    "turn_id_present",
    "windows",
}

_MANIFEST_MESSAGE_KEYS = {
    "content_chars",
    "content_kind",
    "content_parts_count",
    "content_present",
    "estimated_tokens",
    "excluded",
    "exclusion_reason_code",
    "file_part_count",
    "image_part_count",
    "index",
    "logical_roles",
    "origin",
    "origin_stage",
    "provider_role",
    "raw_content_included",
    "text_part_count",
}

_MANIFEST_LANE_STATUS_KEYS = {
    "activation_mode",
    "budget",
    "content_chars",
    "context_hint_count",
    "context_injected",
    "enabled",
    "estimated_tokens",
    "excluded_count",
    "exclusion_reason_codes",
    "final_response_lock_present",
    "injected_count",
    "input_count",
    "invalid_requested_count",
    "media_kind_counts",
    "mode",
    "model_called",
    "origin",
    "over_limit_count",
    "passage_count",
    "query_kind",
    "raw_lane_content_included",
    "reason_code",
    "reason_codes",
    "selected",
    "source_count",
    "status",
}

_MANIFEST_NESTED_MAPPING_KEYS = {
    "assistant_output_policy",
    "budget",
    "budgets",
    "conversation_state",
    "final_response_lock",
    "hash_policy",
    "lane_statuses",
    "media_kind_counts",
    "prompt",
    "raw_flags",
    "recent_context",
    "recent_window",
    "runtime_settings",
    "windows",
}


@dataclass(frozen=True)
class PayloadGuardDecision:
    accepted: bool
    payload: dict[str, Any]


def _safe_key(key: Any) -> str:
    return str(key or "").strip()


def _safe_class(value: str) -> str:
    text = str(value or "").strip().lower()
    return text if _SAFE_CODE_RE.fullmatch(text) else "unknown"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


def _is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("schema_version") or "").strip() == "main_payload_manifest_v1"


def _is_metric_like_key(key: str) -> bool:
    lower = key.lower()
    return lower.endswith(
        (
            "_bytes",
            "_chars",
            "_count",
            "_counts",
            "_hash",
            "_hashes",
            "_id",
            "_ids",
            "_included",
            "_index",
            "_present",
            "_ref",
            "_refs",
            "_sha256_12",
            "_tokens",
        )
    )


def _dangerous_key_class(key: str) -> str:
    lower = key.lower()
    if lower in _QUALIFIED_RAW_FLAGS:
        return ""
    if lower in _DANGEROUS_EXACT_KEYS:
        return f"{lower}_key"
    if lower in _DANGEROUS_PAYLOAD_KEYS:
        return "payload_key"
    if lower.startswith("raw_"):
        return "raw_key"
    if "api_key" in lower or "api-key" in lower:
        return "credential_key"
    if lower.endswith(("_password", "_secret", "_cookie", "_authorization", "_header")):
        return "credential_key"
    if lower.endswith("_token") and not lower.endswith("_tokens"):
        return "credential_key"
    if "payload" in lower and not _is_metric_like_key(lower) and lower not in {"payload_kind"}:
        return "payload_key"
    if "dav" in lower and not _is_metric_like_key(lower):
        return "dav_key"
    if "xml" in lower and not _is_metric_like_key(lower):
        return "xml_key"
    if "etag" in lower and not lower.endswith(("_hash", "_present")):
        return "etag_key"
    if lower.endswith("_url") and not lower.endswith(("_url_hash", "_url_sha256_12")):
        return "url_key"
    if lower.endswith("_path") and not lower.endswith(("_path_hash", "_path_count")):
        return "path_key"
    return ""


def _looks_like_model_path(key: str, value: str) -> bool:
    if key.lower() != "model":
        return False
    return bool(_SAFE_MODEL_RE.fullmatch(value) or _SAFE_CODE_RE.fullmatch(value))


def _dangerous_value_class(key: str, value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    lower = text.lower()
    if _looks_like_model_path(key, text):
        return ""
    if lower.startswith("data:") or "base64," in lower:
        return "data_url_value"
    if _BASE64_RE.fullmatch(text):
        return "base64_value"
    if "://" in lower or lower.startswith(("http:", "https:", "www.")):
        return "url_value"
    if lower.startswith(("dav:", "xml:", "<?xml")) or "</" in lower:
        return "xml_or_dav_value"
    if lower.startswith("/") or lower.startswith("\\\\") or lower.startswith("~"):
        return "path_value"
    if any(marker in lower for marker in ("authorization:", "bearer ", "set-cookie:", "cookie:")):
        return "credential_value"
    if any(marker in lower for marker in ("api_key=", "api-key=", "password=", "secret=", "token=")):
        return "credential_value"
    if lower.startswith("etag:") or lower.startswith("if-match:") or lower.startswith("if-none-match:"):
        return "etag_value"
    if any(part in lower for part in ("webdav", "caldav")):
        return "dav_value"
    if any(char in text for char in ("\r", "\n", "<", ">")):
        return "raw_text_value"
    return ""


def _add_issue(issues: dict[str, int], issue_class: str) -> None:
    issue = _safe_class(issue_class)
    issues[issue] = issues.get(issue, 0) + 1


def _inspect_manifest_mapping(payload: Mapping[str, Any], issues: dict[str, int], depth: int, context: str) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    allowed_keys = _manifest_allowed_keys(context)
    for raw_key, value in payload.items():
        key = _safe_key(raw_key)
        lower = key.lower()
        if not key:
            _add_issue(issues, "manifest_unexpected_key")
            continue
        if context == "lane_statuses":
            if isinstance(value, Mapping):
                _inspect_manifest_mapping(value, issues, depth + 1, "lane_status")
            else:
                _add_issue(issues, "manifest_unexpected_value")
            continue
        if allowed_keys and lower not in allowed_keys:
            _add_issue(issues, "manifest_unexpected_key")
            continue
        if not allowed_keys:
            key_issue = _dangerous_key_class(lower)
            if key_issue and lower not in _MANIFEST_NESTED_MAPPING_KEYS:
                _add_issue(issues, key_issue)
                continue
        if lower in _QUALIFIED_RAW_FLAGS and value is not False:
            _add_issue(issues, "raw_flag_true")
            continue
        if isinstance(value, Mapping):
            _inspect_manifest_mapping(value, issues, depth + 1, lower)
        elif isinstance(value, list):
            _inspect_manifest_list(lower, value, issues, depth + 1)
        else:
            issue = _dangerous_value_class(lower, value)
            if issue:
                _add_issue(issues, issue)


def _manifest_allowed_keys(context: str) -> set[str]:
    if context == "top":
        return _MANIFEST_TOP_LEVEL_KEYS
    if context == "message":
        return _MANIFEST_MESSAGE_KEYS
    if context == "lane_status":
        return _MANIFEST_LANE_STATUS_KEYS
    if context == "raw_flags":
        return _QUALIFIED_RAW_FLAGS
    if context == "lane_statuses":
        return set()
    return set()


def _inspect_manifest_list(key: str, values: list[Any], issues: dict[str, int], depth: int) -> None:
    if depth > _MAX_DEPTH:
        _add_issue(issues, "max_depth_exceeded")
        return
    item_context = "message" if key == "messages" else "nested"
    for value in values:
        if isinstance(value, Mapping):
            _inspect_manifest_mapping(value, issues, depth + 1, item_context)
            continue
        if isinstance(value, list):
            _inspect_manifest_list(key, value, issues, depth + 1)
            continue
        issue = _dangerous_value_class(key, value)
        if issue:
            _add_issue(issues, issue)


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
            _inspect_general(child, issues, key=child_key, depth=depth + 1)
        return
    if isinstance(value, list):
        for item in value:
            _inspect_general(item, issues, key=key, depth=depth + 1)
        return
    issue = _dangerous_value_class(key, value)
    if issue:
        _add_issue(issues, issue)


def _build_rejection_payload(issues: dict[str, int]) -> dict[str, Any]:
    issue_count = sum(issues.values())
    classes = sorted(issues)
    return {
        "schema_version": SCHEMA_VERSION,
        "reason_code": REASON_CODE,
        "rejected_payload": True,
        "issue_count": issue_count,
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
