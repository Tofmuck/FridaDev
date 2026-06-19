from __future__ import annotations

"""Exports V1 user and technical projections."""

from typing import Any, Mapping

from . import workspace_folder_export_refs
from . import workspace_folder_nextcloud_projection
from . import workspace_folder_exports


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
    actions = build_user_actions(export, folder=folder)
    return {
        "export_id": workspace_folder_exports.normalize_export_id(export.get("id")),
        "export_ref": export_ref(export.get("id")),
        "workspace_folder_id": workspace_folder_exports.normalize_workspace_folder_id(
            export.get("workspace_folder_id")
        ),
        "title": workspace_folder_exports.sanitize_export_title(export.get("title")),
        "format": workspace_folder_exports.normalize_export_format(
            export.get("export_format") or export.get("format")
        ),
        "source_kind": workspace_folder_exports.normalize_source_kind(export.get("source_kind")),
        "status": state["status"],
        "status_label": workspace_folder_exports.EXPORT_STATUS_LABELS.get(
            state["status"],
            "indisponible",
        ),
        "nextcloud_sync_state": workspace_folder_exports._nextcloud_state(
            export.get("nextcloud_sync_state")
        ),
        "sync_label": workspace_folder_exports._sync_label(export.get("nextcloud_sync_state")),
        "byte_size": workspace_folder_exports._safe_int(export.get("byte_size")),
        "char_count": workspace_folder_exports._safe_int(export.get("char_count")),
        "reason_code": state["reason_code"],
        "created_at": workspace_folder_exports._ts_to_iso(export.get("created_at")),
        "updated_at": workspace_folder_exports._ts_to_iso(export.get("updated_at")),
        "deleted_at": workspace_folder_exports._ts_to_iso(export.get("deleted_at")),
        "can_download": actions["can_download"],
        "can_open": actions["can_open"],
        "can_reuse_as_source": actions["can_reuse_as_source"],
        "actions": actions,
    }


def build_technical_projection(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = export_state(export, folder=folder)
    etag_hash = workspace_folder_exports._hash12(export.get("etag_hash"))
    etag_present = bool(workspace_folder_exports._text(export.get("etag_value")) or etag_hash)
    return {
        "export_ref": export_ref(export.get("id")),
        "folder_ref": folder_ref(export.get("workspace_folder_id")),
        "title_hash": workspace_folder_exports._hash12(export.get("title_hash"))
        or workspace_folder_exports.title_hash_for_target(export.get("target_name") or export.get("title")),
        "format": workspace_folder_exports.normalize_export_format(
            export.get("export_format") or export.get("format")
        ),
        "source_kind": workspace_folder_exports.normalize_source_kind(export.get("source_kind")) or "unknown",
        "source_ref": workspace_folder_export_refs.safe_source_ref(export.get("source_ref")),
        "source_hash": workspace_folder_exports._hash12(export.get("source_hash")),
        "content_hash": workspace_folder_exports._hash12(export.get("content_hash")),
        "etag_hash": etag_hash,
        "etag_present": etag_present,
        "status": state["status"],
        "nextcloud_sync_state": workspace_folder_exports._nextcloud_state(
            export.get("nextcloud_sync_state")
        ),
        "reason_code": state["reason_code"],
        "counters": {
            "byte_size": workspace_folder_exports._safe_int(export.get("byte_size")),
            "char_count": workspace_folder_exports._safe_int(export.get("char_count")),
        },
    }


def build_user_actions(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reason_code = workspace_folder_exports.REASON_CONTENT_ACCESS_NOT_PREPARED
    if is_deleted(export):
        reason_code = workspace_folder_exports.REASON_EXPORT_DELETED
    elif folder is not None and folder.get("deleted_at"):
        reason_code = workspace_folder_exports.REASON_FOLDER_DELETED
    elif (
        folder is not None
        and workspace_folder_exports._text(folder.get("nextcloud_sync_state")) != "linked"
    ):
        reason_code = workspace_folder_exports.REASON_FOLDER_NOT_LINKED
    return {
        "can_download": False,
        "can_open": False,
        "can_reuse_as_source": False,
        "download_reason_code": reason_code,
        "open_reason_code": reason_code,
        "reuse_as_source_reason_code": reason_code,
    }


def export_state(
    export: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if folder is not None:
        folder_state = workspace_folder_exports._text(folder.get("nextcloud_sync_state"))
        if folder.get("deleted_at"):
            return {
                "status": workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE,
                "reason_code": workspace_folder_exports.REASON_FOLDER_DELETED,
            }
        if folder_state != "linked":
            return {
                "status": workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE,
                "reason_code": workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
            }
    if is_deleted(export):
        return {
            "status": workspace_folder_exports.EXPORT_LOCAL_DELETED,
            "reason_code": workspace_folder_exports._reason(
                export.get("reason_code"),
                workspace_folder_exports.REASON_SOURCE_UNAVAILABLE,
            ),
        }
    state = workspace_folder_exports._local_state(export.get("local_state"))
    reason = workspace_folder_exports._reason(export.get("reason_code"), "")
    if state == workspace_folder_exports.EXPORT_LOCAL_AVAILABLE:
        return {"status": state, "reason_code": reason or workspace_folder_exports.REASON_LIST_OK}
    if state == workspace_folder_exports.EXPORT_LOCAL_CONFLICT:
        return {
            "status": state,
            "reason_code": reason or workspace_folder_exports.REASON_NAME_CONFLICT,
        }
    if state == workspace_folder_exports.EXPORT_LOCAL_SYNC_ERROR:
        return {
            "status": state,
            "reason_code": reason or workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED,
        }
    return {"status": state, "reason_code": reason or workspace_folder_exports.REASON_SOURCE_UNAVAILABLE}


def is_deleted(export: Mapping[str, Any]) -> bool:
    return bool(export.get("deleted_at")) or workspace_folder_exports._local_state(
        export.get("local_state")
    ) == workspace_folder_exports.EXPORT_LOCAL_DELETED


def export_ref(value: Any) -> str:
    return _entity_ref("workspace-export", value)


def folder_ref(value: Any) -> str:
    return _entity_ref("workspace-folder", value)


def _entity_ref(prefix: str, value: Any) -> str:
    raw = workspace_folder_exports._text(value, 160)
    normalized = workspace_folder_exports._uuid_text(raw)
    short = normalized[:8] if normalized else "redacted"
    digest = workspace_folder_nextcloud_projection.hash12(raw or "unknown")
    return f"{prefix}:{short}:{digest}"


def _strip_forbidden(export: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in dict(export).items():
        if str(key).lower() in _FORBIDDEN_PAYLOAD_KEYS:
            continue
        payload[str(key)] = value
    return payload
