from __future__ import annotations

"""Strict reader for reusing an existing Exports V1 artifact as a text source."""

from typing import Any, Callable, Mapping

from . import workspace_folder_export_generation
from . import workspace_folder_export_nextcloud_client as export_client
from . import workspace_folder_export_sources
from . import workspace_folder_exports
from . import workspace_folder_nextcloud_links_store as nextcloud_links


SOURCE_EXPORT_TEXT_FORMATS = frozenset(
    {
        workspace_folder_exports.EXPORT_FORMAT_MARKDOWN,
        workspace_folder_exports.EXPORT_FORMAT_TEXT,
    }
)
SOURCE_EXPORT_MAX_BYTES = workspace_folder_export_generation.GENERATED_ARTIFACT_MAX_BYTES
SOURCE_EXPORT_MAX_CHARS = workspace_folder_export_sources.SOURCE_TEXT_MAX_CHARS

Reader = Callable[[Mapping[str, Any]], Mapping[str, Any]]


def build_export_source_reader(
    *,
    folder: Mapping[str, Any],
    workspace_folder_exports_module: Any = workspace_folder_exports,
    nextcloud: Any | None = None,
) -> Reader:
    folder_snapshot = dict(folder or {})

    def reader(payload: Mapping[str, Any]) -> dict[str, Any]:
        return read_export_source(
            payload,
            folder=folder_snapshot,
            workspace_folder_exports_module=workspace_folder_exports_module,
            nextcloud=nextcloud,
        )

    return reader


def read_export_source(
    payload: Mapping[str, Any],
    *,
    folder: Mapping[str, Any],
    workspace_folder_exports_module: Any = workspace_folder_exports,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    source_export_id = workspace_folder_exports.normalize_export_id(
        payload.get("source_export_id") or payload.get("workspace_export_id") or payload.get("source_id")
    )
    if not source_export_id:
        return _failure(workspace_folder_exports.REASON_SOURCE_MISSING)

    folder_id = workspace_folder_exports.normalize_workspace_folder_id(folder.get("id"))
    request_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
        payload.get("workspace_folder_id")
    )
    if not folder_id or not request_folder_id or folder_id != request_folder_id:
        return _failure(workspace_folder_exports.REASON_FOLDER_INVALID)
    if folder.get("deleted_at"):
        return _failure(workspace_folder_exports.REASON_FOLDER_DELETED)
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(workspace_folder_exports.REASON_FOLDER_NOT_LINKED)

    target_folder_name = _target_folder_name(folder)
    if not target_folder_name:
        return _failure(workspace_folder_exports.REASON_NAME_INVALID)

    try:
        source_export = workspace_folder_exports_module.get_export(
            source_export_id,
            fail_closed=True,
        )
    except Exception:
        return _failure(workspace_folder_exports.REASON_LOOKUP_FAILED)
    if not source_export:
        return _failure(workspace_folder_exports.REASON_EXPORT_NOT_FOUND)

    validation = _validate_source_export(source_export, folder_id=folder_id)
    if validation:
        return _failure(validation)

    export_format = workspace_folder_exports.normalize_export_format(
        source_export.get("export_format") or source_export.get("format")
    )
    target_name = _target_name(source_export, export_format=export_format)
    if not target_name:
        return _failure(workspace_folder_exports.REASON_NAME_INVALID)

    try:
        read = _client(nextcloud).read_export(
            target_folder_name,
            target_name,
            max_bytes=SOURCE_EXPORT_MAX_BYTES,
        )
    except export_client.NextcloudExportClientError as exc:
        return _failure(_source_read_reason(exc.reason_code))

    try:
        content = bytes(read.content or b"").decode("utf-8")
    except UnicodeDecodeError:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)
    if len(content) > SOURCE_EXPORT_MAX_CHARS:
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE)
    if not content.strip():
        return _failure(workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE)

    return {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_REUSE_OK,
        "export_content": content,
        "source_export_id": source_export_id,
        "source_format": export_format,
        "byte_size": len(read.content or b""),
        "char_count": len(content),
    }


def _validate_source_export(export: Mapping[str, Any], *, folder_id: str) -> str:
    export_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
        export.get("workspace_folder_id")
    )
    if export_folder_id != folder_id:
        return workspace_folder_exports.REASON_EXPORT_NOT_FOUND
    if workspace_folder_exports.is_deleted(export):
        return workspace_folder_exports.REASON_EXPORT_DELETED
    if workspace_folder_exports._local_state(export.get("local_state")) != (
        workspace_folder_exports.EXPORT_LOCAL_AVAILABLE
    ):
        return workspace_folder_exports.REASON_EXPORT_NOT_LINKED
    if workspace_folder_exports._nextcloud_state(export.get("nextcloud_sync_state")) != (
        workspace_folder_exports.EXPORT_NEXTCLOUD_LINKED
    ):
        return workspace_folder_exports.REASON_EXPORT_NOT_LINKED
    export_format = workspace_folder_exports.normalize_export_format(
        export.get("export_format") or export.get("format")
    )
    if export_format not in SOURCE_EXPORT_TEXT_FORMATS:
        return workspace_folder_exports.REASON_SOURCE_FORMAT_UNSUPPORTED
    return ""


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return workspace_folder_exports._text(folder.get("nextcloud_target_name"), 180)


def _target_name(export: Mapping[str, Any], *, export_format: str) -> str:
    target = workspace_folder_exports._text(export.get("target_name"), 220)
    if not target or not export_format:
        return ""
    if workspace_folder_exports.sanitize_export_target_name(target, export_format) != target:
        return ""
    return target


def _client(nextcloud: Any | None):
    return nextcloud or export_client.NextcloudExportClient.from_env()


def _source_read_reason(reason_code: str) -> str:
    if reason_code in {
        workspace_folder_exports.REASON_TOO_LARGE,
        workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE,
    }:
        return workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE
    if reason_code in workspace_folder_exports.REASON_CODE_CATALOG:
        return workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE
    return workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE


def _failure(reason_code: str) -> dict[str, Any]:
    safe_reason = reason_code if reason_code in workspace_folder_exports.REASON_CODE_CATALOG else (
        workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE
    )
    return {
        "ok": False,
        "reason_code": safe_reason,
    }
