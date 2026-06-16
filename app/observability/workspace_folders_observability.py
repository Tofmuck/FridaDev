from __future__ import annotations

"""Content-free observability read-model for Frida V1 workspace folders."""

import hashlib
import re
from typing import Any, Mapping


OBSERVABILITY_KIND = "frida_v1_workspace_folder"
_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")

REASON_LIST_OK = "workspace_folder_list_ok"
REASON_CREATE_OK = "workspace_folder_create_ok"
REASON_RENAME_OK = "workspace_folder_rename_ok"
REASON_DELETE_OK = "workspace_folder_delete_ok"
REASON_PERMISSION_DENIED = "workspace_folder_permission_denied"
REASON_TARGET_MISSING = "workspace_folder_target_missing"
REASON_TARGET_EXISTS = "workspace_folder_target_exists"
REASON_DELETE_REFUSED = "workspace_folder_delete_refused"
REASON_NEXTCLOUD_ERROR_REDACTED = "workspace_folder_nextcloud_error_redacted"

SYNC_STATES = ("local_only", "sync_pending", "linked", "sync_error", "conflict", "deleted")
SHARE_STATES = ("unknown", "expected", "confirmed", "error")
LOCAL_STATUSES = ("active", "deleted")

SUCCESS_REASON_BY_OPERATION = {
    "list": REASON_LIST_OK,
    "create": REASON_CREATE_OK,
    "rename": REASON_RENAME_OK,
    "delete": REASON_DELETE_OK,
}

REASON_CODE_CATALOG = frozenset(
    {
        REASON_LIST_OK,
        REASON_CREATE_OK,
        REASON_RENAME_OK,
        REASON_DELETE_OK,
        "workspace_folder_name_required",
        "workspace_folder_name_invalid",
        "workspace_folder_name_too_long",
        "workspace_folder_name_conflict_local",
        "workspace_folder_name_conflict_sanitized",
        "workspace_folder_name_conflict_case",
        "workspace_folder_name_conflict_nextcloud",
        REASON_PERMISSION_DENIED,
        REASON_TARGET_MISSING,
        REASON_TARGET_EXISTS,
        REASON_DELETE_REFUSED,
        REASON_NEXTCLOUD_ERROR_REDACTED,
        "workspace_folder_sync_local_only",
        "workspace_folder_sync_unknown",
        "workspace_folder_sync_pending",
        "workspace_folder_sync_linked",
        "workspace_folder_sync_conflict",
        "workspace_folder_sync_error",
        "workspace_folder_deleted",
        "workspace_folder_share_unknown",
        "workspace_folder_share_expected",
        "workspace_folder_share_confirmed",
        "workspace_folder_share_error",
        "workspace_folder_delete_confirmation_required",
        "workspace_folder_files_preserved",
        "workspace_folder_live_unavailable",
        "workspace_folder_sauron_required",
        "workspace_folder_icon_invalid",
        "workspace_folder_sort_order_invalid",
        "workspace_folder_create_failed",
        "workspace_folder_id_invalid",
        "workspace_folder_patch_empty",
        "workspace_folder_not_found",
    }
)


def _text(value: Any, *, max_chars: int = 120) -> str:
    text = " ".join(str(value or "").strip().split())
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _to_bool(value: Any) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _to_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _hash12(value: Any) -> str:
    text = _text(value, max_chars=500)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _safe_hash12(value: Any) -> str:
    text = _text(value, max_chars=120).lower()
    return text if _HASH12_RE.fullmatch(text) else ""


def _safe_reason_code(
    value: Any,
    *,
    fallback: str = REASON_NEXTCLOUD_ERROR_REDACTED,
    allow_empty: bool = False,
) -> str:
    text = _text(value, max_chars=120)
    if not text and allow_empty:
        return ""
    return text if text in REASON_CODE_CATALOG else fallback


def _safe_operation(value: Any) -> str:
    text = _text(value, max_chars=40)
    return text if text in SUCCESS_REASON_BY_OPERATION else "unknown"


def _status_for(http_status: int, reason_code: str) -> str:
    if 200 <= http_status < 300:
        return "ok"
    if http_status == 409 or "conflict" in reason_code:
        return "conflict"
    return "error"


def _http_status_class(http_status: int) -> str:
    if http_status <= 0:
        return "none"
    return f"{http_status // 100}xx"


def _safe_state(value: Any, allowed: tuple[str, ...], fallback: str) -> str:
    text = _text(value, max_chars=40)
    return text if text in allowed else fallback


def _count_by(items: list[Mapping[str, Any]], field: str, allowed: tuple[str, ...]) -> dict[str, int]:
    counts = {key: 0 for key in allowed}
    for item in items:
        value = _safe_state(item.get(field), allowed, allowed[0])
        counts[value] = int(counts.get(value, 0)) + 1
    return {key: value for key, value in counts.items() if value}


def reason_code_catalog() -> list[str]:
    return sorted(REASON_CODE_CATALOG)


def build_workspace_folder_observation(
    operation: str,
    payload: Mapping[str, Any] | None,
    *,
    http_status: int = 200,
    reason_code: str | None = None,
) -> dict[str, Any]:
    payload = payload or {}
    operation_name = _safe_operation(operation)
    success_reason = SUCCESS_REASON_BY_OPERATION.get(operation_name, REASON_NEXTCLOUD_ERROR_REDACTED)
    raw_reason = _text(reason_code or payload.get("reason_code"), max_chars=120)
    if raw_reason:
        observed_reason = _safe_reason_code(raw_reason)
    elif 200 <= http_status < 300:
        observed_reason = success_reason
    else:
        observed_reason = REASON_NEXTCLOUD_ERROR_REDACTED

    items = [item for item in payload.get("items", []) if isinstance(item, Mapping)]
    folder = payload.get("folder") if isinstance(payload.get("folder"), Mapping) else {}
    observation: dict[str, Any] = {
        "kind": OBSERVABILITY_KIND,
        "operation": operation_name,
        "status": _status_for(http_status, observed_reason),
        "status_class": _http_status_class(http_status),
        "reason_code": observed_reason,
        "content_free": True,
        "raw_content_included": False,
        "server_path_included": False,
        "remote_url_included": False,
        "secret_included": False,
    }

    if items:
        observation["folder_count"] = len(items)
        observation["sync_state_counts"] = _count_by(items, "nextcloud_sync_state", SYNC_STATES)
        observation["share_state_counts"] = _count_by(items, "nextcloud_share_state", SHARE_STATES)
        observation["local_status_counts"] = _count_by(items, "local_status", LOCAL_STATUSES)
        reason_counts: dict[str, int] = {}
        for item in items:
            item_reason = _safe_reason_code(item.get("nextcloud_reason_code"), allow_empty=True)
            if item_reason:
                reason_counts[item_reason] = int(reason_counts.get(item_reason, 0)) + 1
        if reason_counts:
            observation["reason_code_counts"] = dict(sorted(reason_counts.items()))

    if folder:
        observation.update(_folder_observation_fields(folder))

    if operation_name == "delete" and folder:
        file_delete = folder.get("file_delete") if isinstance(folder.get("file_delete"), Mapping) else {}
        observation.update(
            {
                "files_preserved": _to_bool(folder.get("files_preserved")),
                "files_deleted": _to_int(folder.get("files_deleted")),
                "file_delete_requested": _to_int(file_delete.get("requested")),
                "file_delete_failed": _to_int(file_delete.get("failed")),
                "file_reason_code": _safe_reason_code(file_delete.get("reason_code"), allow_empty=True),
                "conversations_moved_out": _to_int(folder.get("conversations_moved_out")),
            }
        )

    error_hash = _hash12(payload.get("error")) if http_status >= 400 else ""
    if error_hash:
        observation["error_ref"] = error_hash
    return observation


def _folder_observation_fields(folder: Mapping[str, Any]) -> dict[str, Any]:
    fields = {
        "folder_ref": _hash12(folder.get("id")),
        "local_status": _safe_state(folder.get("local_status"), LOCAL_STATUSES, "active"),
        "nextcloud_sync_state": _safe_state(folder.get("nextcloud_sync_state"), SYNC_STATES, "local_only"),
        "nextcloud_share_state": _safe_state(folder.get("nextcloud_share_state"), SHARE_STATES, "unknown"),
        "nextcloud_reason_code": _safe_reason_code(folder.get("nextcloud_reason_code"), allow_empty=True),
        "nextcloud_live_checked": _to_bool(folder.get("nextcloud_live_checked")),
    }
    name_hash = _safe_hash12(folder.get("nextcloud_name_hash"))
    if name_hash:
        fields["nextcloud_name_hash"] = name_hash
    return fields


def log_workspace_folder_observation(logger: Any, observation: Mapping[str, Any]) -> None:
    log_func = getattr(logger, "info", None)
    if not callable(log_func):
        return
    fields = {
        key: value
        for key, value in observation.items()
        if key
        in {
            "operation",
            "status",
            "status_class",
            "reason_code",
            "folder_ref",
            "folder_count",
            "local_status",
            "nextcloud_sync_state",
            "nextcloud_share_state",
            "nextcloud_reason_code",
            "files_preserved",
            "files_deleted",
            "file_delete_requested",
            "file_delete_failed",
            "file_reason_code",
            "conversations_moved_out",
        }
    }
    details = " ".join(f"{key}={_text(value)}" for key, value in sorted(fields.items()) if _text(value))
    if details:
        log_func("workspace_folder_observation %s", details)
    else:
        log_func("workspace_folder_observation")
