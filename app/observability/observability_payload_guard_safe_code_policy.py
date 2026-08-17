from __future__ import annotations

import re
from typing import Any


_SAFE_CODE_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,159}$")
_SAFE_CLASS_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,159}$")
_SAFE_MODEL_RE = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,79}/[a-z0-9][a-z0-9_.-]{0,119}$")
_SAFE_TITLE_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ./_-]{0,159}$")
_SAFE_TIMEZONE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_./+-]{0,79}$")
_SAFE_MIME_RE = re.compile(r"^[a-z0-9][a-z0-9.+-]{0,80}/[a-z0-9][a-z0-9.+-]{0,80}$")
_SAFE_EXTENSION_RE = re.compile(r"^\.?[a-z0-9][a-z0-9.+-]{0,15}$")
_SAFE_LANGUAGE_SET_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9+_.-]{0,119}$")
_SAFE_TIMESTAMP_CHARS = set("0123456789T:+-.Z")
_BASE64_RE = re.compile(r"^[A-Za-z0-9+/]{96,}={0,2}$")
_SAFE_LANE_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_]{0,79}$")
_TOKEN_LIKE_SAFE_CODE_RE = re.compile(
    r"^(?:"
    r"sk[-_](?:live[-_]|or[-_])?[a-z0-9][a-z0-9_.-]{5,}"
    r"|ghp_[a-z0-9][a-z0-9_]{11,}"
    r"|hf_[a-z0-9][a-z0-9_]{11,}"
    r"|xoxb-[a-z0-9][a-z0-9_.-]{5,}"
    r")$",
    re.IGNORECASE,
)

_QUALIFIED_RAW_FLAGS = set(
    """
    raw_content_included raw_content_stored raw_error_message_included raw_error_message_stored
    raw_event_payloads_included raw_lane_content_included raw_log_included raw_message_included
    raw_passage_included raw_policy_text_included raw_prompt_included
    raw_provider_payload_included raw_query_included raw_catalogue_payload_included
    raw_locator_included raw_secret_included raw_webdav_payload_included raw_capsule_content_included
    """.split()
)

_DANGEROUS_EXACT_KEYS = set(
    """
    authorization base64 content cookie data_url dav etag header image_data_url message messages password
    path payload prompt provider_payload raw raw_payload secret text token url xml
    """.split()
)
_DANGEROUS_PAYLOAD_KEYS = {"provider_payload", "raw_payload", "request_payload", "response_payload"}


def _is_metric_like_key(key: str) -> bool:
    lower = key.lower()
    if lower in {"max_tokens", "raw_candidates", "temperature", "top_p"}:
        return True
    return lower.endswith(
        (
            "_bytes",
            "_budget",
            "_chars",
            "_chars_total",
            "_count",
            "_counts",
            "_duration_ms",
            "_hash",
            "_hashes",
            "_id",
            "_ids",
            "_included",
            "_injected",
            "_index",
            "_len",
            "_limit",
            "_ms",
            "_present",
            "_ref",
            "_refs",
            "_seen",
            "_sha256_12",
            "_target_s",
            "_truncated",
            "_exceeded",
            "_tokens",
            "_used",
        )
    )


def _dangerous_key_class(key: str) -> str:
    lower = key.lower()
    if lower in {
        "identity_block_sha256_12",
        "update_reason_sha256_12",
    }:
        return "identity_text_hash_key"
    if lower in _QUALIFIED_RAW_FLAGS:
        return ""
    if lower in _DANGEROUS_EXACT_KEYS:
        return f"{lower}_key"
    if lower in _DANGEROUS_PAYLOAD_KEYS:
        return "payload_key"
    if lower == "collection_path":
        return ""
    if lower.startswith("raw_") and not _is_metric_like_key(lower):
        return "raw_key"
    if "api_key" in lower or "api-key" in lower:
        return "credential_key"
    if lower.endswith(("_password", "_secret", "_cookie", "_authorization", "_header")):
        return "credential_key"
    if lower.endswith("_token") and not lower.endswith("_tokens"):
        return "credential_key"
    if (
        "payload" in lower
        and not _is_metric_like_key(lower)
        and lower not in {"main_llm_payload", "payload_kind", "payload_order", "rejected_payload", "secondary_provider_payload"}
    ):
        return "payload_key"
    if lower == "caldav_access":
        return ""
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
    if _TOKEN_LIKE_SAFE_CODE_RE.fullmatch(text):
        return "token_like_value"
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
    if _TOKEN_LIKE_SAFE_CODE_RE.fullmatch(text):
        return False
    if allow_model and _SAFE_MODEL_RE.fullmatch(text):
        return True
    return bool(_SAFE_CODE_RE.fullmatch(text))


def _is_safe_class_text(value: Any) -> bool:
    return bool(_SAFE_CLASS_RE.fullmatch(str(value or "").strip()))


def _is_safe_title_text(value: Any) -> bool:
    return bool(_SAFE_TITLE_RE.fullmatch(str(value or "").strip()))


def _is_safe_mime_text(value: Any) -> bool:
    return bool(_SAFE_MIME_RE.fullmatch(str(value or "").strip().lower()))


def _is_safe_extension_text(value: Any) -> bool:
    return bool(_SAFE_EXTENSION_RE.fullmatch(str(value or "").strip().lower()))


def _is_safe_language_set_text(value: Any) -> bool:
    return bool(_SAFE_LANGUAGE_SET_RE.fullmatch(str(value or "").strip()))


def _is_safe_timezone_text(value: Any) -> bool:
    return bool(_SAFE_TIMEZONE_RE.fullmatch(str(value or "").strip()))


def _is_safe_timestamp_text(value: Any) -> bool:
    return all(char in _SAFE_TIMESTAMP_CHARS for char in str(value or "").strip())


def _is_safe_lane_name(value: Any) -> bool:
    return bool(_SAFE_LANE_NAME_RE.fullmatch(str(value or "").strip()))
