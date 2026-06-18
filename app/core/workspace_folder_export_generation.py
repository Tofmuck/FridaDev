from __future__ import annotations

"""Fake/local Markdown and TXT generation for Exports V1."""

import uuid
from typing import Any, Mapping

from . import workspace_folder_export_refs
from . import workspace_folder_exports
from .workspace_folder_export_markdown_text import render_markdown_export, render_txt_export
from .workspace_folder_export_sources import (
    Reader,
    acquire_export_source,
)


GENERATED_ARTIFACT_MAX_BYTES = 25 * 1024 * 1024
SUPPORTED_FAKE_LOCAL_FORMATS = frozenset(
    {
        workspace_folder_exports.EXPORT_FORMAT_MARKDOWN,
        workspace_folder_exports.EXPORT_FORMAT_TEXT,
    }
)


def generate_workspace_folder_export(
    request: Mapping[str, Any] | None,
    *,
    note_reader: Reader | None = None,
    document_reader: Reader | None = None,
    export_reader: Reader | None = None,
) -> dict[str, Any]:
    payload = dict(request or {})
    export_format = workspace_folder_exports.normalize_export_format(
        payload.get("export_format") or payload.get("format")
    )
    if export_format not in SUPPORTED_FAKE_LOCAL_FORMATS:
        return _failure(workspace_folder_exports.REASON_FORMAT_UNSUPPORTED, export_format=export_format)

    source = acquire_export_source(
        payload,
        note_reader=note_reader,
        document_reader=document_reader,
        export_reader=export_reader,
    )
    if not source.ok:
        return _failure(source.reason_code, export_format=export_format, source=source.content_free_projection())

    title = workspace_folder_exports.sanitize_export_title(payload.get("title") or source.title)
    target_name = workspace_folder_exports.sanitize_export_target_name(title, export_format)
    if not title or not target_name:
        return _failure(
            workspace_folder_exports.REASON_NAME_INVALID,
            export_format=export_format,
            source=source.content_free_projection(),
        )

    export_content = _render(export_format, source, title=title)
    byte_size = len(export_content.encode("utf-8"))
    if byte_size > GENERATED_ARTIFACT_MAX_BYTES:
        return _failure(
            workspace_folder_exports.REASON_TOO_LARGE,
            export_format=export_format,
            source=source.content_free_projection(),
        )

    record = _record(payload, source, export_format, title, target_name, export_content, byte_size)
    projection = workspace_folder_exports.apply_export_projection(record)
    return {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_CREATE_OK,
        "export_format": export_format,
        "export_content": export_content,
        "export_v1_user": projection["export_v1_user"],
        "export_v1_technical": projection["export_v1_technical"],
        "export_v1_metadata": projection,
        "source": source.content_free_projection(),
    }


def _render(export_format: str, source, *, title: str) -> str:
    if export_format == workspace_folder_exports.EXPORT_FORMAT_MARKDOWN:
        return render_markdown_export(source, title=title)
    return render_txt_export(source, title=title)


def _record(
    payload: Mapping[str, Any],
    source,
    export_format: str,
    title: str,
    target_name: str,
    export_content: str,
    byte_size: int,
) -> dict[str, Any]:
    return {
        "id": workspace_folder_exports.normalize_export_id(payload.get("export_id"))
        or str(uuid.uuid4()),
        "workspace_folder_id": workspace_folder_exports.normalize_workspace_folder_id(
            payload.get("workspace_folder_id")
        ),
        "title": title,
        "title_hash": workspace_folder_exports.title_hash_for_target(target_name),
        "target_name": target_name,
        "export_format": export_format,
        "source_kind": source.source_kind,
        "source_ref": source.source_ref,
        "source_hash": source.source_hash,
        "content_hash": workspace_folder_export_refs.hash12(export_content),
        "local_state": workspace_folder_exports.EXPORT_LOCAL_AVAILABLE,
        "nextcloud_sync_state": workspace_folder_exports.EXPORT_NEXTCLOUD_SYNC_ERROR,
        "remote_export_ref": "",
        "etag_value": "",
        "etag_hash": "",
        "byte_size": byte_size,
        "char_count": len(export_content),
        "reason_code": workspace_folder_exports.REASON_CREATE_OK,
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
    }


def _failure(
    reason_code: str,
    *,
    export_format: str = "",
    source: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": _safe_reason(reason_code),
        "export_format": export_format,
        "export_content": "",
        "export_v1_technical": {
            "reason_code": _safe_reason(reason_code),
            "format": export_format,
            "source": dict(source or {}),
        },
    }


def _safe_reason(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if text in workspace_folder_exports.REASON_CODE_CATALOG:
        return text
    return workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED
