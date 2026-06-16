from __future__ import annotations

import hashlib
import re
import unicodedata
from typing import Any, Callable


DISPLAY_NAME_MAX_CHARS = 80
NEXTCLOUD_LOGICAL_ROOT = "/Frida"
NEXTCLOUD_SYNC_UNKNOWN = "unknown"
NEXTCLOUD_SYNC_PENDING = "pending"
NEXTCLOUD_SYNC_LINKED = "linked"
NEXTCLOUD_SYNC_CONFLICT = "conflict"
NEXTCLOUD_SYNC_ERROR = "error"
NEXTCLOUD_SYNC_DELETED = "deleted"
NEXTCLOUD_SHARE_UNKNOWN = "unknown"
NEXTCLOUD_SHARE_EXPECTED = "expected"
NEXTCLOUD_SHARE_CONFIRMED = "confirmed"
NEXTCLOUD_SHARE_ERROR = "error"
REASON_FOLDER_NAME_INVALID = "workspace_folder_name_invalid"
REASON_FOLDER_SYNC_PENDING = "workspace_folder_sync_pending"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
_TARGET_DASH_CHARS = set('/\\:*?"<>|')
_TARGET_ALLOWED_PUNCTUATION = set("._-")


def _collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def sanitize_nextcloud_folder_name(value: Any) -> str:
    raw = unicodedata.normalize("NFKC", _collapse_ws(value))
    if not raw:
        return ""

    parts: list[str] = []
    last_dash = False
    for char in raw:
        if char.isalnum() or char in _TARGET_ALLOWED_PUNCTUATION:
            parts.append(char)
            last_dash = False
            continue
        if char.isspace() or char in _TARGET_DASH_CHARS or unicodedata.category(char).startswith("P"):
            if not last_dash:
                parts.append("-")
                last_dash = True
            continue
        if unicodedata.category(char).startswith("C"):
            continue
        if not last_dash:
            parts.append("-")
            last_dash = True

    target = re.sub(r"-{2,}", "-", "".join(parts)).strip(" ._-")
    if len(target) > DISPLAY_NAME_MAX_CHARS:
        target = target[:DISPLAY_NAME_MAX_CHARS].rstrip(" ._-")
    return target


def nextcloud_folder_name_key(value: Any) -> str:
    return sanitize_nextcloud_folder_name(value).casefold()


def hash12(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def build_nextcloud_folder_projection(
    *,
    folder_id: Any,
    display_name: Any,
    deleted_at: Any = None,
    normalize_folder_id_func: Callable[[str], str | None] | None = None,
) -> dict[str, Any]:
    folder_raw = str(folder_id or "")
    folder_uuid = normalize_folder_id_func(folder_raw) if callable(normalize_folder_id_func) else None
    short_id = (folder_uuid or folder_raw.strip() or "unknown")[:8]
    target_name = sanitize_nextcloud_folder_name(display_name)
    target_key = target_name.casefold()
    name_hash = hash12(target_key)
    local_status = "deleted" if deleted_at else "active"
    if deleted_at:
        sync_state = NEXTCLOUD_SYNC_DELETED
        share_state = NEXTCLOUD_SHARE_UNKNOWN
        reason_code = REASON_FOLDER_DELETED
    elif not target_name:
        sync_state = NEXTCLOUD_SYNC_ERROR
        share_state = NEXTCLOUD_SHARE_UNKNOWN
        reason_code = REASON_FOLDER_NAME_INVALID
    else:
        sync_state = NEXTCLOUD_SYNC_PENDING
        share_state = NEXTCLOUD_SHARE_EXPECTED
        reason_code = REASON_FOLDER_SYNC_PENDING
    directory_ref = f"workspace-folder:{short_id}:{name_hash or 'invalid'}"
    return {
        "local_status": local_status,
        "nextcloud_logical_root": NEXTCLOUD_LOGICAL_ROOT,
        "nextcloud_target_name": target_name,
        "nextcloud_logical_path": f"{NEXTCLOUD_LOGICAL_ROOT}/{target_name}" if target_name else NEXTCLOUD_LOGICAL_ROOT,
        "nextcloud_directory_ref": directory_ref,
        "nextcloud_name_hash": name_hash,
        "nextcloud_sync_state": sync_state,
        "nextcloud_share_state": share_state,
        "nextcloud_reason_code": reason_code,
        "nextcloud_live_checked": False,
    }
