from __future__ import annotations

"""Exports V1 local read-model projections.

Exports keep metadata only. User projections may show the export title; technical
projections stay content-free and never expose generated content, raw remote
targets, raw ETags, paths, URLs, XML, payloads, or secrets.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from . import workspace_folder_export_refs
from . import workspace_folder_export_reason_codes
from . import workspace_folder_nextcloud_projection


EXPORT_LOCAL_AVAILABLE = "available"
EXPORT_LOCAL_SYNC_ERROR = "sync_error"
EXPORT_LOCAL_CONFLICT = "conflict"
EXPORT_LOCAL_DELETED = "deleted"
EXPORT_LOCAL_UNAVAILABLE = "unavailable"
EXPORT_LOCAL_STATES = (
    EXPORT_LOCAL_AVAILABLE,
    EXPORT_LOCAL_SYNC_ERROR,
    EXPORT_LOCAL_CONFLICT,
    EXPORT_LOCAL_DELETED,
    EXPORT_LOCAL_UNAVAILABLE,
)

EXPORT_NEXTCLOUD_LINKED = "linked"
EXPORT_NEXTCLOUD_SYNC_ERROR = "sync_error"
EXPORT_NEXTCLOUD_DELETED = "deleted"
EXPORT_NEXTCLOUD_STATES = (
    EXPORT_NEXTCLOUD_LINKED,
    EXPORT_NEXTCLOUD_SYNC_ERROR,
    EXPORT_NEXTCLOUD_DELETED,
)

EXPORT_FORMAT_MARKDOWN = "md"
EXPORT_FORMAT_TEXT = "txt"
EXPORT_FORMAT_DOCX = "docx"
EXPORT_FORMAT_PDF = "pdf"
EXPORT_FORMATS = (
    EXPORT_FORMAT_MARKDOWN,
    EXPORT_FORMAT_TEXT,
    EXPORT_FORMAT_DOCX,
    EXPORT_FORMAT_PDF,
)
EXPORT_FORMAT_EXTENSIONS = {
    EXPORT_FORMAT_MARKDOWN: ".md",
    EXPORT_FORMAT_TEXT: ".txt",
    EXPORT_FORMAT_DOCX: ".docx",
    EXPORT_FORMAT_PDF: ".pdf",
}

SOURCE_CONVERSATION = "conversation"
SOURCE_MESSAGE_SELECTION = "message_selection"
SOURCE_FRIDA_RESPONSE = "frida_response"
SOURCE_NOTE = "note"
SOURCE_DOCUMENT = "document"
SOURCE_EXPORT = "export"
EXPORT_SOURCE_KINDS = (
    SOURCE_CONVERSATION,
    SOURCE_MESSAGE_SELECTION,
    SOURCE_FRIDA_RESPONSE,
    SOURCE_NOTE,
    SOURCE_DOCUMENT,
    SOURCE_EXPORT,
)

globals().update(workspace_folder_export_reason_codes.REASON_CODE_EXPORTS)
REASON_CODE_CATALOG = workspace_folder_export_reason_codes.REASON_CODE_CATALOG

TITLE_MAX_CHARS = 160
EXPORT_TARGET_MAX_CHARS = 180
EXPORT_STATUS_LABELS = {
    EXPORT_LOCAL_AVAILABLE: "disponible",
    EXPORT_LOCAL_SYNC_ERROR: "erreur de synchronisation",
    EXPORT_LOCAL_CONFLICT: "conflit",
    EXPORT_LOCAL_DELETED: "supprime",
    EXPORT_LOCAL_UNAVAILABLE: "indisponible",
}

logger = logging.getLogger("frida.workspace_folder_exports")

_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")
_SAFE_REASON_RE = re.compile(r"^[a-z0-9_]{3,120}$")
_FORBIDDEN_PAYLOAD_KEYS = {
    "body",
    "content",
    "export_content",
    "file_content",
    "markdown_content",
    "text_content",
    "raw",
    "payload",
    "payload_body",
    "etag",
    "etag_value",
    "target_name",
    "remote_export_ref",
    "dav_path",
    "dav_url",
    "path",
    "url",
    "href",
    "xml",
    "secret",
    "token",
    "cookie",
    "authorization",
    "app_password",
    "app-password",
    "storage_key",
}


def normalize_export_id(value: Any) -> str:
    return _uuid_text(value)


def normalize_workspace_folder_id(value: Any) -> str:
    return _uuid_text(value)


def normalize_export_format(value: Any) -> str:
    text = _text(value, 24).lower().lstrip(".")
    aliases = {"markdown": EXPORT_FORMAT_MARKDOWN, "text": EXPORT_FORMAT_TEXT}
    text = aliases.get(text, text)
    return text if text in EXPORT_FORMATS else ""


def normalize_source_kind(value: Any) -> str:
    text = _text(value, 40)
    return text if text in EXPORT_SOURCE_KINDS else ""


def sanitize_export_title(value: Any) -> str:
    title = _collapse_ws(value)
    if len(title) > TITLE_MAX_CHARS:
        title = title[:TITLE_MAX_CHARS].rstrip()
    return title


def sanitize_export_target_name(value: Any, export_format: Any = EXPORT_FORMAT_MARKDOWN) -> str:
    fmt = normalize_export_format(export_format) or EXPORT_FORMAT_MARKDOWN
    extension = EXPORT_FORMAT_EXTENSIONS[fmt]
    raw = str(value or "").replace("\\", "/").split("/")[-1].strip()
    title = sanitize_export_title(raw)
    if not title:
        return ""
    for known_extension in EXPORT_FORMAT_EXTENSIONS.values():
        if title.casefold().endswith(known_extension):
            title = title[: -len(known_extension)].rstrip(" ._-")
            break
    base = workspace_folder_nextcloud_projection.sanitize_nextcloud_folder_name(title)
    if not base:
        return ""
    target = f"{base}{extension}"
    if len(target) > EXPORT_TARGET_MAX_CHARS:
        stem_limit = EXPORT_TARGET_MAX_CHARS - len(extension)
        target = f"{base[:stem_limit].rstrip(' ._-')}{extension}"
    return target


def title_hash_for_target(target_name: Any) -> str:
    target = _collapse_ws(target_name).casefold()
    return workspace_folder_nextcloud_projection.hash12(target)


def validate_export_title(
    value: Any,
    *,
    export_format: str = EXPORT_FORMAT_MARKDOWN,
    existing_exports: list[Mapping[str, Any]] | None = None,
    current_export_id: str | None = None,
) -> dict[str, Any]:
    fmt = normalize_export_format(export_format)
    title = sanitize_export_title(value)
    target_name = sanitize_export_target_name(title, fmt)
    if not title or not target_name or not fmt:
        return {
            "ok": False,
            "reason_code": REASON_NAME_INVALID,
            "title": title,
            "target_name": target_name,
            "title_hash": title_hash_for_target(target_name),
            "format": fmt,
        }

    export_id = normalize_export_id(current_export_id)
    title_hash = title_hash_for_target(target_name)
    target_key = target_name.casefold()
    for export in existing_exports or []:
        if export.get("deleted_at") or _local_state(export.get("local_state")) == EXPORT_LOCAL_DELETED:
            continue
        existing_id = normalize_export_id(export.get("id"))
        if export_id and existing_id == export_id:
            continue
        existing_format = normalize_export_format(export.get("export_format") or export.get("format"))
        existing_target = _target_name(export.get("target_name"), fmt=existing_format or fmt)
        existing_hash = _hash12(export.get("title_hash"))
        if existing_format == fmt and (existing_hash == title_hash or existing_target.casefold() == target_key):
            return {
                "ok": False,
                "reason_code": REASON_NAME_CONFLICT,
                "title": title,
                "target_name": target_name,
                "title_hash": title_hash,
                "format": fmt,
            }

    return {
        "ok": True,
        "reason_code": "",
        "title": title,
        "target_name": target_name,
        "title_hash": title_hash,
        "format": fmt,
    }


def apply_export_projection(
    export: Mapping[str, Any] | None,
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not export:
        return {}
    payload = _strip_forbidden(export)
    payload["export_v1_user"] = build_user_projection(export, folder=folder)
    payload["export_v1_technical"] = build_technical_projection(export, folder=folder)
    return payload


def apply_export_list(
    exports: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    items = []
    for export in exports:
        if not include_deleted and is_deleted(export):
            continue
        items.append(apply_export_projection(export, folder=folder))
    return items


def build_user_projection(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = export_state(export, folder=folder)
    return {
        "export_id": normalize_export_id(export.get("id")),
        "export_ref": export_ref(export.get("id")),
        "workspace_folder_id": normalize_workspace_folder_id(export.get("workspace_folder_id")),
        "title": sanitize_export_title(export.get("title")),
        "format": normalize_export_format(export.get("export_format") or export.get("format")),
        "source_kind": normalize_source_kind(export.get("source_kind")),
        "status": state["status"],
        "status_label": EXPORT_STATUS_LABELS.get(state["status"], "indisponible"),
        "nextcloud_sync_state": _nextcloud_state(export.get("nextcloud_sync_state")),
        "sync_label": _sync_label(export.get("nextcloud_sync_state")),
        "byte_size": _safe_int(export.get("byte_size")),
        "char_count": _safe_int(export.get("char_count")),
        "reason_code": state["reason_code"],
        "created_at": _ts_to_iso(export.get("created_at")),
        "updated_at": _ts_to_iso(export.get("updated_at")),
        "deleted_at": _ts_to_iso(export.get("deleted_at")),
    }


def build_technical_projection(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = export_state(export, folder=folder)
    etag_hash = _hash12(export.get("etag_hash"))
    etag_present = bool(_text(export.get("etag_value")) or etag_hash)
    return {
        "export_ref": export_ref(export.get("id")),
        "folder_ref": folder_ref(export.get("workspace_folder_id")),
        "title_hash": _hash12(export.get("title_hash"))
        or title_hash_for_target(export.get("target_name") or export.get("title")),
        "format": normalize_export_format(export.get("export_format") or export.get("format")),
        "source_kind": normalize_source_kind(export.get("source_kind")) or "unknown",
        "source_ref": workspace_folder_export_refs.safe_source_ref(export.get("source_ref")),
        "source_hash": _hash12(export.get("source_hash")),
        "content_hash": _hash12(export.get("content_hash")),
        "etag_hash": etag_hash,
        "etag_present": etag_present,
        "status": state["status"],
        "nextcloud_sync_state": _nextcloud_state(export.get("nextcloud_sync_state")),
        "reason_code": state["reason_code"],
        "counters": {
            "byte_size": _safe_int(export.get("byte_size")),
            "char_count": _safe_int(export.get("char_count")),
        },
    }


def export_state(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if folder is not None:
        folder_state = _text(folder.get("nextcloud_sync_state"))
        if folder.get("deleted_at"):
            return {"status": EXPORT_LOCAL_UNAVAILABLE, "reason_code": REASON_FOLDER_DELETED}
        if folder_state != "linked":
            return {"status": EXPORT_LOCAL_UNAVAILABLE, "reason_code": REASON_FOLDER_NOT_LINKED}
    if is_deleted(export):
        return {
            "status": EXPORT_LOCAL_DELETED,
            "reason_code": _reason(export.get("reason_code"), REASON_SOURCE_UNAVAILABLE),
        }
    state = _local_state(export.get("local_state"))
    reason = _reason(export.get("reason_code"), "")
    if state == EXPORT_LOCAL_AVAILABLE:
        return {"status": state, "reason_code": reason or REASON_LIST_OK}
    if state == EXPORT_LOCAL_CONFLICT:
        return {"status": state, "reason_code": reason or REASON_NAME_CONFLICT}
    if state == EXPORT_LOCAL_SYNC_ERROR:
        return {"status": state, "reason_code": reason or REASON_NEXTCLOUD_ERROR_REDACTED}
    return {"status": state, "reason_code": reason or REASON_SOURCE_UNAVAILABLE}


def is_deleted(export: Mapping[str, Any]) -> bool:
    return bool(export.get("deleted_at")) or _local_state(export.get("local_state")) == EXPORT_LOCAL_DELETED


def export_ref(value: Any) -> str:
    return _entity_ref("workspace-export", value)


def folder_ref(value: Any) -> str:
    return _entity_ref("workspace-folder", value)


def list_exports(
    workspace_folder_id: str,
    *,
    include_deleted: bool = False,
    fail_closed: bool = True,
) -> list[dict[str, Any]]:
    from . import workspace_folder_exports_store

    return workspace_folder_exports_store.list_exports(
        workspace_folder_id,
        include_deleted=include_deleted,
        db_conn_func=_db_conn,
        logger=logger,
        fail_closed=fail_closed,
    )


def get_export(export_id: str, *, fail_closed: bool = True) -> Optional[dict[str, Any]]:
    from . import workspace_folder_exports_store

    return workspace_folder_exports_store.get_export(
        export_id,
        db_conn_func=_db_conn,
        logger=logger,
        fail_closed=fail_closed,
    )


def upsert_export(**fields: Any) -> dict[str, Any]:
    from . import workspace_folder_exports_store

    return workspace_folder_exports_store.upsert_export(
        **fields,
        db_conn_func=_db_conn,
        logger=logger,
    )


def tombstone_export(export_id: str, *, reason_code: str = REASON_SOURCE_UNAVAILABLE) -> Optional[dict[str, Any]]:
    from . import workspace_folder_exports_store

    return workspace_folder_exports_store.tombstone_export(
        export_id,
        reason_code=reason_code,
        db_conn_func=_db_conn,
        logger=logger,
    )


def log_content_free_event(event: str, level: str = "info", **fields: Any) -> None:
    log_method = getattr(logger, level, logger.info)
    log_method("workspace_folder_export_%s", event, extra={"frida": fields})


def _entity_ref(prefix: str, value: Any) -> str:
    raw = _text(value, 160)
    normalized = _uuid_text(raw)
    short = normalized[:8] if normalized else "redacted"
    digest = workspace_folder_nextcloud_projection.hash12(raw or "unknown")
    return f"{prefix}:{short}:{digest}"


def _db_conn():
    import config
    import psycopg
    from admin import runtime_settings
    from . import runtime_db_bootstrap

    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def _strip_forbidden(export: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in dict(export).items():
        if str(key).lower() in _FORBIDDEN_PAYLOAD_KEYS:
            continue
        payload[str(key)] = value
    return payload


def _local_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in EXPORT_LOCAL_STATES else EXPORT_LOCAL_UNAVAILABLE


def _nextcloud_state(value: Any) -> str:
    text = _text(value, 40)
    return text if text in EXPORT_NEXTCLOUD_STATES else EXPORT_NEXTCLOUD_SYNC_ERROR


def _sync_label(value: Any) -> str:
    state = _nextcloud_state(value)
    return {
        EXPORT_NEXTCLOUD_LINKED: "range Nextcloud",
        EXPORT_NEXTCLOUD_SYNC_ERROR: "synchronisation incomplete",
        EXPORT_NEXTCLOUD_DELETED: "supprime",
    }.get(state, "synchronisation incomplete")


def _target_name(value: Any, *, fmt: str = EXPORT_FORMAT_MARKDOWN) -> str:
    target = sanitize_export_target_name(value, fmt)
    if target:
        return target
    text = str(value or "").replace("\\", "/").split("/")[-1].strip()
    return _collapse_ws(text)[:EXPORT_TARGET_MAX_CHARS]


def _uuid_text(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return ""


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
