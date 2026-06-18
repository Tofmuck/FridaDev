from __future__ import annotations

"""Notes V1 local read-model projections.

This module has no Nextcloud transport and no Markdown body persistence. Titles
are allowed in user-facing projections; technical projections stay content-free.
"""

import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from . import workspace_folder_nextcloud_projection


NOTE_LOCAL_AVAILABLE = "available"
NOTE_LOCAL_SYNC_ERROR = "sync_error"
NOTE_LOCAL_CONFLICT = "conflict"
NOTE_LOCAL_DELETED = "deleted"
NOTE_LOCAL_UNAVAILABLE = "unavailable"
NOTE_LOCAL_STATES = (
    NOTE_LOCAL_AVAILABLE,
    NOTE_LOCAL_SYNC_ERROR,
    NOTE_LOCAL_CONFLICT,
    NOTE_LOCAL_DELETED,
    NOTE_LOCAL_UNAVAILABLE,
)

NOTE_NEXTCLOUD_LINKED = "linked"
NOTE_NEXTCLOUD_SYNC_ERROR = "sync_error"
NOTE_NEXTCLOUD_DELETED = "deleted"
NOTE_NEXTCLOUD_STATES = (
    NOTE_NEXTCLOUD_LINKED,
    NOTE_NEXTCLOUD_SYNC_ERROR,
    NOTE_NEXTCLOUD_DELETED,
)

REASON_FOLDER_NOT_LINKED = "folder_note_folder_not_linked"
REASON_NOTES_TARGET_MISSING = "folder_note_notes_target_missing"
REASON_NOTES_TARGET_NOT_COLLECTION = "folder_note_notes_target_not_collection"
REASON_NOTES_TARGET_UNAVAILABLE = "folder_note_notes_target_unavailable"
REASON_NAME_INVALID = "folder_note_name_invalid"
REASON_NAME_CONFLICT = "folder_note_name_conflict"
REASON_CREATE_OK = "folder_note_create_ok"
REASON_APPEND_OK = "folder_note_append_ok"
REASON_LIST_OK = "folder_note_list_ok"
REASON_LOOKUP_OK = "folder_note_lookup_ok"
REASON_LOOKUP_AMBIGUOUS = "folder_note_lookup_ambiguous"
REASON_LOOKUP_FAILED = "folder_note_lookup_failed"
REASON_NOT_FOUND = "folder_note_not_found"
REASON_TOO_LARGE = "folder_note_too_large"
REASON_APPEND_TOO_LARGE = "folder_note_append_too_large"
REASON_VERSION_CONFLICT = "folder_note_version_conflict"
REASON_LOCAL_PERSISTENCE_FAILED = "folder_note_local_persistence_failed"
REASON_REMOTE_COMPENSATION_OK = "folder_note_remote_compensation_ok"
REASON_REMOTE_COMPENSATION_FAILED = "folder_note_remote_compensation_failed"
REASON_NEXTCLOUD_ERROR_REDACTED = "folder_note_nextcloud_error_redacted"

REASON_CODE_CATALOG = frozenset(
    {
        REASON_FOLDER_NOT_LINKED,
        REASON_NOTES_TARGET_MISSING,
        REASON_NOTES_TARGET_NOT_COLLECTION,
        REASON_NOTES_TARGET_UNAVAILABLE,
        REASON_NAME_INVALID,
        REASON_NAME_CONFLICT,
        REASON_CREATE_OK,
        REASON_APPEND_OK,
        REASON_LIST_OK,
        REASON_LOOKUP_OK,
        REASON_LOOKUP_AMBIGUOUS,
        REASON_LOOKUP_FAILED,
        REASON_NOT_FOUND,
        REASON_TOO_LARGE,
        REASON_APPEND_TOO_LARGE,
        REASON_VERSION_CONFLICT,
        REASON_LOCAL_PERSISTENCE_FAILED,
        REASON_REMOTE_COMPENSATION_OK,
        REASON_REMOTE_COMPENSATION_FAILED,
        REASON_NEXTCLOUD_ERROR_REDACTED,
    }
)

TITLE_MAX_CHARS = 160
NOTE_TARGET_MAX_CHARS = 180
NOTE_MARKDOWN_EXTENSION = ".md"
NOTE_STATUS_LABELS = {
    NOTE_LOCAL_AVAILABLE: "disponible",
    NOTE_LOCAL_SYNC_ERROR: "erreur de synchronisation",
    NOTE_LOCAL_CONFLICT: "conflit",
    NOTE_LOCAL_DELETED: "supprimee",
    NOTE_LOCAL_UNAVAILABLE: "indisponible",
}

_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")
_SAFE_REASON_RE = re.compile(r"^[a-z0-9_]{3,120}$")
_FORBIDDEN_PAYLOAD_KEYS = {
    "markdown_body",
    "body",
    "content",
    "text",
    "raw",
    "payload",
    "etag_value",
    "etag",
    "target_name",
    "remote_note_ref",
    "dav_url",
    "url",
    "href",
    "xml",
    "secret",
    "token",
    "cookie",
    "authorization",
    "app_password",
    "app-password",
}


def normalize_note_id(value: Any) -> str:
    return _uuid_text(value)


def normalize_workspace_folder_id(value: Any) -> str:
    return _uuid_text(value)


def sanitize_note_title(value: Any) -> str:
    title = _collapse_ws(value)
    if len(title) > TITLE_MAX_CHARS:
        title = title[:TITLE_MAX_CHARS].rstrip()
    return title


def sanitize_note_target_name(value: Any) -> str:
    title = sanitize_note_title(value)
    if not title:
        return ""
    if title.casefold().endswith(NOTE_MARKDOWN_EXTENSION):
        title = title[: -len(NOTE_MARKDOWN_EXTENSION)].rstrip(" ._-")
    base = workspace_folder_nextcloud_projection.sanitize_nextcloud_folder_name(title)
    if not base:
        return ""
    target = f"{base}{NOTE_MARKDOWN_EXTENSION}"
    if len(target) > NOTE_TARGET_MAX_CHARS:
        stem_limit = NOTE_TARGET_MAX_CHARS - len(NOTE_MARKDOWN_EXTENSION)
        target = f"{base[:stem_limit].rstrip(' ._-')}{NOTE_MARKDOWN_EXTENSION}"
    return target


def title_hash_for_target(target_name: Any) -> str:
    target = _collapse_ws(target_name).casefold()
    return workspace_folder_nextcloud_projection.hash12(target)


def validate_note_title(
    value: Any,
    *,
    existing_notes: list[Mapping[str, Any]] | None = None,
    current_note_id: str | None = None,
) -> dict[str, Any]:
    title = sanitize_note_title(value)
    target_name = sanitize_note_target_name(title)
    if not title or not target_name:
        return {
            "ok": False,
            "reason_code": REASON_NAME_INVALID,
            "title": title,
            "target_name": target_name,
            "title_hash": title_hash_for_target(target_name),
        }

    note_id = normalize_note_id(current_note_id)
    title_hash = title_hash_for_target(target_name)
    target_key = target_name.casefold()
    for note in existing_notes or []:
        if note.get("deleted_at") or _local_state(note.get("local_state")) == NOTE_LOCAL_DELETED:
            continue
        existing_id = normalize_note_id(note.get("id"))
        if note_id and existing_id == note_id:
            continue
        existing_target = _target_name(note.get("target_name") or note.get("note_target_name"))
        existing_hash = _hash12(note.get("title_hash"))
        if existing_hash == title_hash or existing_target.casefold() == target_key:
            return {
                "ok": False,
                "reason_code": REASON_NAME_CONFLICT,
                "title": title,
                "target_name": target_name,
                "title_hash": title_hash,
            }

    return {
        "ok": True,
        "reason_code": "",
        "title": title,
        "target_name": target_name,
        "title_hash": title_hash,
    }


def apply_note_projection(
    note: Mapping[str, Any] | None,
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not note:
        return {}
    payload = _strip_forbidden(note)
    payload["note_v1_user"] = build_user_projection(note, folder=folder)
    payload["note_v1_technical"] = build_technical_projection(note, folder=folder)
    return payload


def apply_note_list(
    notes: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    items = []
    for note in notes:
        if not include_deleted and is_deleted(note):
            continue
        items.append(apply_note_projection(note, folder=folder))
    return items


def build_user_projection(
    note: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = note_state(note, folder=folder)
    return {
        "note_id": normalize_note_id(note.get("id")),
        "note_ref": note_ref(note.get("id")),
        "workspace_folder_id": normalize_workspace_folder_id(note.get("workspace_folder_id")),
        "title": sanitize_note_title(note.get("title")),
        "status": state["status"],
        "status_label": NOTE_STATUS_LABELS.get(state["status"], "indisponible"),
        "nextcloud_sync_state": _nextcloud_state(note.get("nextcloud_sync_state")),
        "sync_label": _sync_label(note.get("nextcloud_sync_state")),
        "markdown_char_count": _safe_int(note.get("markdown_char_count")),
        "reason_code": state["reason_code"],
        "created_at": _ts_to_iso(note.get("created_at")),
        "updated_at": _ts_to_iso(note.get("updated_at")),
        "deleted_at": _ts_to_iso(note.get("deleted_at")),
    }


def build_technical_projection(
    note: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = note_state(note, folder=folder)
    etag_hash = _hash12(note.get("etag_hash"))
    etag_present = bool(_text(note.get("etag_value")) or etag_hash)
    return {
        "note_ref": note_ref(note.get("id")),
        "folder_ref": folder_ref(note.get("workspace_folder_id")),
        "title_hash": _hash12(note.get("title_hash"))
        or title_hash_for_target(note.get("target_name") or note.get("title")),
        "etag_hash": etag_hash,
        "etag_present": etag_present,
        "status": state["status"],
        "nextcloud_sync_state": _nextcloud_state(note.get("nextcloud_sync_state")),
        "reason_code": state["reason_code"],
        "counters": {
            "markdown_char_count": _safe_int(note.get("markdown_char_count")),
        },
    }


def note_state(
    note: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if folder is not None:
        folder_state = _text(folder.get("nextcloud_sync_state"))
        if folder.get("deleted_at") or folder_state != "linked":
            return {"status": NOTE_LOCAL_UNAVAILABLE, "reason_code": REASON_FOLDER_NOT_LINKED}
    if is_deleted(note):
        return {"status": NOTE_LOCAL_DELETED, "reason_code": _reason(note.get("reason_code"), REASON_NOT_FOUND)}
    state = _local_state(note.get("local_state"))
    reason = _reason(note.get("reason_code"), "")
    if state == NOTE_LOCAL_AVAILABLE:
        return {"status": state, "reason_code": reason or REASON_LIST_OK}
    if state == NOTE_LOCAL_CONFLICT:
        return {"status": state, "reason_code": reason or REASON_NAME_CONFLICT}
    if state == NOTE_LOCAL_SYNC_ERROR:
        return {"status": state, "reason_code": reason or REASON_NEXTCLOUD_ERROR_REDACTED}
    return {"status": state, "reason_code": reason or REASON_NOT_FOUND}


def is_deleted(note: Mapping[str, Any]) -> bool:
    return bool(note.get("deleted_at")) or _local_state(note.get("local_state")) == NOTE_LOCAL_DELETED


def note_ref(value: Any) -> str:
    return _entity_ref("workspace-note", value)


def folder_ref(value: Any) -> str:
    return _entity_ref("workspace-folder", value)


def _entity_ref(prefix: str, value: Any) -> str:
    raw = _text(value, 160)
    normalized = _uuid_text(raw)
    short = normalized[:8] if normalized else "redacted"
    digest = workspace_folder_nextcloud_projection.hash12(raw or "unknown")
    return f"{prefix}:{short}:{digest}"


def _strip_forbidden(note: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in dict(note).items():
        if str(key).lower() in _FORBIDDEN_PAYLOAD_KEYS:
            continue
        payload[str(key)] = value
    return payload


def _local_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in NOTE_LOCAL_STATES else NOTE_LOCAL_UNAVAILABLE


def _nextcloud_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in NOTE_NEXTCLOUD_STATES else NOTE_NEXTCLOUD_SYNC_ERROR


def _sync_label(value: Any) -> str:
    state = _nextcloud_state(value)
    return {
        NOTE_NEXTCLOUD_LINKED: "rangee Nextcloud",
        NOTE_NEXTCLOUD_SYNC_ERROR: "synchronisation incomplete",
        NOTE_NEXTCLOUD_DELETED: "supprimee",
    }.get(state, "synchronisation incomplete")


def _uuid_text(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return ""


def _target_name(value: Any) -> str:
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    return _collapse_ws(text)[:NOTE_TARGET_MAX_CHARS]


def _hash12(value: Any) -> str:
    text = _text(value, 12).lower()
    return text if _HASH12_RE.fullmatch(text) else ""


def _reason(value: Any, fallback: str) -> str:
    text = _text(value, 120)
    if text in REASON_CODE_CATALOG and _SAFE_REASON_RE.fullmatch(text):
        return text
    return fallback or REASON_NEXTCLOUD_ERROR_REDACTED


def _safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def _text(value: Any, max_chars: int = 160) -> str:
    text = _collapse_ws(value)
    if max_chars > 0 and len(text) > max_chars:
        return text[:max_chars].rstrip()
    return text


def _collapse_ws(value: Any) -> str:
    return " ".join(str(value or "").strip().split())


def _ts_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
