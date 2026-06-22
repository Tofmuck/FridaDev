from __future__ import annotations

import re
from typing import Any, Mapping


_SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,159}$")
_SAFE_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")
_SAFE_LANE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,79}$")

_QUALIFIED_RAW_FLAGS = set(
    """
    raw_content_included raw_content_stored raw_error_message_included raw_error_message_stored
    raw_event_payloads_included raw_lane_content_included raw_log_included raw_message_included
    raw_policy_text_included raw_prompt_included raw_provider_payload_included raw_secret_included
    raw_webdav_payload_included
    """.split()
)

_MANIFEST_RAW_FLAGS = {
    "raw_prompt_included",
    "raw_message_included",
    "raw_content_included",
    "raw_lane_content_included",
    "raw_provider_payload_included",
    "raw_secret_included",
}

_DANGEROUS_EXACT_KEYS = set(
    """
    authorization base64 content cookie data_url dav etag header image_data_url message messages password
    path payload prompt provider_payload raw raw_payload secret text token url xml
    """.split()
)
_DANGEROUS_PAYLOAD_KEYS = {"provider_payload", "raw_payload", "request_payload", "response_payload"}

_MANIFEST_TOP_LEVEL_KEYS = set(
    """
    assistant_output_policy budgets conversation_id_present conversation_state final_response_lock hash_policy
    lane_statuses main_model_called messages provider raw_flags runtime_settings schema_version scope
    status_schema_version turn_id_present windows
    """.split()
)
_MANIFEST_MESSAGE_KEYS = set(
    """
    content_chars content_kind content_parts_count content_present estimated_tokens excluded
    exclusion_reason_code file_part_count image_part_count index logical_roles origin origin_stage
    provider_role raw_content_included text_part_count
    """.split()
)
_MANIFEST_LANE_STATUS_KEYS = set(
    """
    activation_mode budget content_chars context_hint_count context_injected enabled estimated_tokens
    excluded_count exclusion_reason_codes final_response_lock_present injected_count input_count
    invalid_requested_count media_kind_counts mode model_called origin over_limit_count passage_count
    query_kind raw_lane_content_included reason_code reason_codes selected source_count status
    """.split()
)
_RUNTIME_SETTINGS_KEYS = {"max_tokens", "model", "provider_family", "stream_requested", "temperature_present", "top_p_present"}
_ASSISTANT_OUTPUT_POLICY_KEYS = {"allow_code", "allow_structure", "present", "raw_policy_text_included"}
_FINAL_RESPONSE_LOCK_KEYS = {
    "content_chars",
    "content_present",
    "main_model_bypassed",
    "present",
    "priority_policy",
    "raw_content_included",
    "reason_code",
    "source",
}
_CONVERSATION_STATE_KEYS = {
    "conversation_id_present",
    "conversation_message_count",
    "conversation_state_kind",
    "turn_id_present",
    "workspace_folder_present",
}
_HASH_POLICY_KEYS = {"fingerprints_included", "policy", "short_stable_text_hashes_included", "stable_text_hashes_included"}
_BUDGETS_KEYS = {"prompt"}
_PROMPT_BUDGET_KEYS = {"content_chars_total", "estimated_prompt_tokens", "max_completion_tokens", "message_count"}
_WINDOWS_KEYS = {
    "agenda_recent_dialogue",
    "biblio_recent_dialogue",
    "conversation",
    "prompt_final",
    "recent_context",
    "recent_window",
}
_WINDOW_KEYS_BY_CONTEXT = {
    "agenda_recent_dialogue": {"message_count"},
    "biblio_recent_dialogue": {"message_count"},
    "conversation": {"assistant_message_count", "message_count", "user_message_count"},
    "prompt_final": {"message_count", "provider_role_sequence"},
    "recent_context": {"message_count"},
    "recent_window": {"has_in_progress_turn", "max_recent_turns", "turn_count"},
}
_MANIFEST_CONTEXT_KEYS = {
    "top": _MANIFEST_TOP_LEVEL_KEYS,
    "message": _MANIFEST_MESSAGE_KEYS,
    "lane_status": _MANIFEST_LANE_STATUS_KEYS,
    "raw_flags": _MANIFEST_RAW_FLAGS,
    "runtime_settings": _RUNTIME_SETTINGS_KEYS,
    "assistant_output_policy": _ASSISTANT_OUTPUT_POLICY_KEYS,
    "final_response_lock": _FINAL_RESPONSE_LOCK_KEYS,
    "conversation_state": _CONVERSATION_STATE_KEYS,
    "hash_policy": _HASH_POLICY_KEYS,
    "budgets": _BUDGETS_KEYS,
    "budget_prompt": _PROMPT_BUDGET_KEYS,
    "windows": _WINDOWS_KEYS,
}
_MANIFEST_SAFE_TEXT_KEYS = set(
    """
    activation_mode content_kind conversation_state_kind exclusion_reason_code mode model origin origin_stage
    policy priority_policy provider provider_family provider_role query_kind reason_code schema_version
    scope source status status_schema_version
    """.split()
)
_MANIFEST_TEXT_LIST_KEYS = {"exclusion_reason_codes", "logical_roles", "provider_role_sequence", "reason_codes"}
_MANIFEST_DYNAMIC_INT_MAP_KEYS = {"budget", "media_kind_counts"}

_GENERAL_TEXT_KEYS = set(
    """
    activation_mode error_class error_code final_status guarded_original_status mode model origin origin_stage
    policy priority_policy prompt_kind provider provider_caller provider_role query_kind reason_code reason_short
    retrieval_error_class retrieval_error_code retrieval_status schema_version scope source source_kind status
    status_schema_version write_effect write_mode
    """.split()
)
_GENERAL_TEXT_SUFFIXES = (
    "_class",
    "_code",
    "_effect",
    "_kind",
    "_mode",
    "_phase",
    "_policy",
    "_reason",
    "_schema_version",
    "_source",
    "_status",
    "_type",
    "_version",
)
_GENERAL_SCALAR_KEYS = set(
    """
    adobe_mode_active context_injected enabled final_response_lock_present has_in_progress_turn main_model_called
    model_called ok rejected_payload selected stream_requested truncated web_search_enabled web_search_requested
    """.split()
)
_GENERAL_CONTAINER_KEYS = {
    "actions_count",
    "by_provider_caller",
    "counts",
    "duration_ms",
    "issue_classes",
    "nested_counts",
    "providers",
    "raw_flags",
    "redaction",
    "status_schema",
}
_GENERAL_SAFE_TEXT_LIST_KEYS = {"issue_classes", "reason_codes"}


def _is_main_payload_manifest(payload: Mapping[str, Any]) -> bool:
    return str(payload.get("schema_version") or "").strip() == "main_payload_manifest_v1"


def _is_metric_like_key(key: str) -> bool:
    lower = key.lower()
    if lower in {"max_tokens", "temperature", "top_p"}:
        return True
    return lower.endswith(
        (
            "_bytes",
            "_chars",
            "_count",
            "_counts",
            "_duration_ms",
            "_hash",
            "_hashes",
            "_id",
            "_ids",
            "_included",
            "_index",
            "_limit",
            "_ms",
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


def _dangerous_value_class(key: str, value: Any) -> str:
    if not isinstance(value, str):
        return ""
    text = value.strip()
    if not text:
        return ""
    lower = text.lower()
    if key.lower() == "model" and bool(_SAFE_MODEL_RE.fullmatch(text) or _SAFE_CODE_RE.fullmatch(text)):
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


def _is_safe_code_text(value: Any, *, allow_empty: bool = True, allow_model: bool = False) -> bool:
    text = str(value or "").strip()
    if not text:
        return bool(allow_empty)
    if allow_model and _SAFE_MODEL_RE.fullmatch(text):
        return True
    return bool(_SAFE_CODE_RE.fullmatch(text))


def _is_safe_general_text_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_TEXT_KEYS or lower.endswith(_GENERAL_TEXT_SUFFIXES)


def _is_safe_general_text_value(key: str, value: Any) -> bool:
    return _is_safe_code_text(value, allow_empty=True, allow_model=key.lower() == "model")


def _is_safe_general_scalar_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_SCALAR_KEYS or _is_metric_like_key(lower)


def _is_safe_general_container_key(key: str) -> bool:
    lower = key.lower()
    return lower in _GENERAL_CONTAINER_KEYS or lower.endswith(("_counts", "_metrics", "_by_stage", "_by_provider_caller"))


def _is_safe_manifest_text_value(key: str, value: Any) -> bool:
    return _is_safe_code_text(value, allow_empty=True, allow_model=key.lower() == "model")


def _safe_dynamic_name(value: Any) -> bool:
    return bool(_SAFE_LANE_NAME_RE.fullmatch(str(value or "").strip()))


def _is_manifest_bool_key(key: str) -> bool:
    return key in {
        "allow_code",
        "allow_structure",
        "content_present",
        "context_injected",
        "conversation_id_present",
        "enabled",
        "excluded",
        "final_response_lock_present",
        "fingerprints_included",
        "has_in_progress_turn",
        "main_model_bypassed",
        "main_model_called",
        "model_called",
        "present",
        "raw_content_included",
        "raw_lane_content_included",
        "raw_policy_text_included",
        "selected",
        "short_stable_text_hashes_included",
        "stable_text_hashes_included",
        "stream_requested",
        "temperature_present",
        "top_p_present",
        "turn_id_present",
        "workspace_folder_present",
    }


def _is_manifest_number_key(key: str) -> bool:
    return key in {
        "assistant_message_count",
        "content_chars_total",
        "estimated_prompt_tokens",
        "index",
        "max_completion_tokens",
        "max_recent_turns",
        "max_tokens",
        "message_count",
        "turn_count",
        "user_message_count",
    } or _is_metric_like_key(key)


def _manifest_allowed_keys(context: str) -> set[str]:
    if context.startswith("window:"):
        return _WINDOW_KEYS_BY_CONTEXT.get(context.split(":", 1)[1], set())
    return _MANIFEST_CONTEXT_KEYS.get(context, set())


def _manifest_child_context(context: str, key: str) -> str:
    if context == "top" and key in {
        "assistant_output_policy",
        "budgets",
        "conversation_state",
        "final_response_lock",
        "hash_policy",
        "raw_flags",
        "runtime_settings",
        "windows",
    }:
        return key
    if context == "top" and key == "lane_statuses":
        return "lane_statuses"
    if context == "budgets" and key == "prompt":
        return "budget_prompt"
    if context == "windows" and key in _WINDOWS_KEYS:
        return f"window:{key}"
    if context == "lane_status" and key in _MANIFEST_DYNAMIC_INT_MAP_KEYS:
        return "manifest_dynamic_int_map"
    return ""
