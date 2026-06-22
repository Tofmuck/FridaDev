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
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.apply_export_projection(export, folder=folder)


def apply_export_list(
    exports: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.apply_export_list(
        exports,
        folder=folder,
        include_deleted=include_deleted,
    )


def build_user_projection(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.build_user_projection(export, folder=folder)


def build_technical_projection(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.build_technical_projection(export, folder=folder)


def export_state(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.export_state(export, folder=folder)


def is_deleted(export: Mapping[str, Any]) -> bool:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.is_deleted(export)


def export_ref(value: Any) -> str:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.export_ref(value)


def folder_ref(value: Any) -> str:
    from . import workspace_folder_export_projection

    return workspace_folder_export_projection.folder_ref(value)


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


def _db_conn():
    import config
    import psycopg
    from admin import runtime_settings
    from . import runtime_db_bootstrap

    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


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
