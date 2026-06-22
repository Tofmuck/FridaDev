from __future__ import annotations

"""Fake/local export generation for Exports V1."""

import hashlib
import uuid
from typing import Any, Mapping

from . import workspace_folder_export_refs
from . import workspace_folder_exports
from .workspace_folder_export_docx_pdf import (
    DependencyChecker,
    render_binary_export,
)
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
        workspace_folder_exports.EXPORT_FORMAT_DOCX,
        workspace_folder_exports.EXPORT_FORMAT_PDF,
    }
)


def generate_workspace_folder_export(
    request: Mapping[str, Any] | None,
    *,
    conversation_reader: Reader | None = None,
    note_reader: Reader | None = None,
    document_reader: Reader | None = None,
    export_reader: Reader | None = None,
    binary_dependency_checker: DependencyChecker | None = None,
) -> dict[str, Any]:
    payload = dict(request or {})
    export_format = workspace_folder_exports.normalize_export_format(
        payload.get("export_format") or payload.get("format")
    )
    if export_format not in SUPPORTED_FAKE_LOCAL_FORMATS:
        return _failure(workspace_folder_exports.REASON_FORMAT_UNSUPPORTED, export_format=export_format)

    workspace_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
        payload.get("workspace_folder_id")
    )
    if not workspace_folder_id:
        return _failure(workspace_folder_exports.REASON_FOLDER_INVALID, export_format=export_format)

    source = acquire_export_source(
        payload,
        conversation_reader=conversation_reader,
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

    rendered = _render(
        export_format,
        source,
        title=title,
        binary_dependency_checker=binary_dependency_checker,
    )
    if not rendered["ok"]:
        return _failure(
            rendered["reason_code"],
            export_format=export_format,
            source=source.content_free_projection(),
        )

    export_content = rendered["export_content"]
    export_bytes = rendered["export_bytes"]
    byte_size = len(export_bytes) if export_bytes else len(export_content.encode("utf-8"))
    if byte_size > GENERATED_ARTIFACT_MAX_BYTES:
        return _failure(
            workspace_folder_exports.REASON_TOO_LARGE,
            export_format=export_format,
            source=source.content_free_projection(),
        )

    record = _record(
        payload,
        source,
        export_format,
        title,
        target_name,
        content_hash=_content_hash(export_bytes or export_content),
        byte_size=byte_size,
        char_count=source.char_count if export_bytes else len(export_content),
    )
    projection = workspace_folder_exports.apply_export_projection(record)
    return {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_CREATE_OK,
        "export_format": export_format,
        "export_content": export_content,
        "export_bytes": export_bytes,
        "export_mime_type": rendered["mime_type"],
        "export_v1_user": projection["export_v1_user"],
        "export_v1_technical": projection["export_v1_technical"],
        "export_v1_metadata": projection,
        "source": source.content_free_projection(),
    }


def _render(
    export_format: str,
    source,
    *,
    title: str,
    binary_dependency_checker: DependencyChecker | None = None,
) -> dict[str, Any]:
    if export_format == workspace_folder_exports.EXPORT_FORMAT_MARKDOWN:
        return _rendered_text(render_markdown_export(source, title=title))
    if export_format == workspace_folder_exports.EXPORT_FORMAT_TEXT:
        return _rendered_text(render_txt_export(source, title=title))
    binary = render_binary_export(
        export_format,
        source,
        title=title,
        dependency_checker=binary_dependency_checker,
    )
    if not binary.ok:
        return {
            "ok": False,
            "reason_code": binary.reason_code,
            "export_content": "",
            "export_bytes": b"",
            "mime_type": "",
        }
    return {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_CREATE_OK,
        "export_content": "",
        "export_bytes": binary.content_bytes,
        "mime_type": binary.mime_type,
    }


def _rendered_text(export_content: str) -> dict[str, Any]:
    return {
        "ok": True,
        "reason_code": workspace_folder_exports.REASON_CREATE_OK,
        "export_content": export_content,
        "export_bytes": b"",
        "mime_type": "text/plain; charset=utf-8",
    }


def _record(
    payload: Mapping[str, Any],
    source,
    export_format: str,
    title: str,
    target_name: str,
    *,
    content_hash: str,
    byte_size: int,
    char_count: int,
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
        "content_hash": content_hash,
        "local_state": workspace_folder_exports.EXPORT_LOCAL_AVAILABLE,
        "nextcloud_sync_state": workspace_folder_exports.EXPORT_NEXTCLOUD_SYNC_ERROR,
        "remote_export_ref": "",
        "etag_value": "",
        "etag_hash": "",
        "byte_size": byte_size,
        "char_count": char_count,
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
        "export_bytes": b"",
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


def _content_hash(value: str | bytes) -> str:
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()[:12]
    return workspace_folder_export_refs.hash12(value)
