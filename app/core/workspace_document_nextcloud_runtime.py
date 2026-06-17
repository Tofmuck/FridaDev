from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from pathlib import PurePosixPath
from typing import Any, Mapping

from . import workspace_document_nextcloud_client as document_client
from . import workspace_file_nextcloud_links_store as file_nextcloud_links
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection
from .workspace_document_nextcloud_delete import (
    complete_workspace_document_delete,
    prepare_workspace_document_delete_nextcloud_first,
)


MAX_DOCUMENT_TARGET_NAME_CHARS = 180
_FORBIDDEN_FILENAME_CHARS = set('/\\:*?"<>|')
_ALLOWED_EXTENSION_RE = re.compile(r"^\.[A-Za-z0-9]{1,15}$")


def store_workspace_document_nextcloud_first(
    *,
    folder: Mapping[str, Any],
    content: bytes,
    original_filename: str,
    metadata: Mapping[str, Any],
    workspace_files_module: Any,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    folder_id = str(folder.get("id") or "")
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(
            document_client.REASON_FOLDER_NOT_LINKED,
            status=409,
            upload_state="blocked",
        )

    target_folder_name = _target_folder_name(folder)
    if not target_folder_name:
        return _failure(
            document_client.REASON_DOCUMENTS_TARGET_UNAVAILABLE,
            status=502,
            upload_state="blocked",
        )

    target_name = sanitize_nextcloud_document_name(
        metadata.get("display_name") or original_filename,
        metadata.get("source_extension"),
    )
    if not target_name:
        return _failure(document_client.REASON_NAME_INVALID, status=400, upload_state="blocked")

    conflict = _local_name_conflict(
        workspace_files_module,
        folder_id=folder_id,
        target_name=target_name,
    )
    if conflict:
        return _failure(document_client.REASON_NAME_CONFLICT, status=409, upload_state="blocked")

    try:
        client = _client(nextcloud)
        client.documents_status(target_folder_name)
        put_result = client.put_document(
            target_folder_name,
            target_name,
            bytes(content or b""),
            media_type=metadata.get("mime_type") or "",
        )
    except document_client.NextcloudDocumentClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            http_status_class=exc.status_class,
            upload_state="nextcloud_failed",
        )

    workspace_file_id = str(uuid.uuid4())
    stored = _store_local(
        workspace_files_module,
        folder_id=folder_id,
        file_id=workspace_file_id,
        original_filename=original_filename,
        content=content,
        metadata=metadata,
    )
    if stored:
        link = _persist_nextcloud_link(
            workspace_files_module,
            workspace_file_id=str(stored.get("id") or workspace_file_id),
            workspace_folder_id=folder_id,
            target_name=target_name,
        )
        if not link:
            remote_rollback = _rollback_remote_created_document(
                client,
                target_folder_name=target_folder_name,
                target_name=target_name,
                workspace_files_module=workspace_files_module,
                folder_id=folder_id,
            )
            local_rollback = _delete_local_created_file(
                workspace_files_module,
                folder_id=folder_id,
                file_id=str(stored.get("id") or workspace_file_id),
            )
            _log_event(
                workspace_files_module,
                "documents_v1_link_persistence_failed",
                level="warning",
                folder_id=folder_id,
                file_id=str(stored.get("id") or workspace_file_id),
                reason_code=document_client.REASON_LINK_PERSISTENCE_FAILED,
                document_name_hash=hash12(target_name.casefold()),
                remote_rollback_ok=bool(remote_rollback.get("ok")),
                local_rollback_ok=bool(local_rollback.get("ok")),
            )
            return _failure(
                document_client.REASON_LINK_PERSISTENCE_FAILED,
                status=503,
                upload_state="link_persistence_failed",
                document_name_hash=hash12(target_name.casefold()),
                rollback={
                    "remote": remote_rollback,
                    "local": local_rollback,
                },
            )
        _log_event(
            workspace_files_module,
            "documents_v1_upload_ok",
            folder_id=folder_id,
            file_id=stored.get("id"),
            reason_code=document_client.REASON_UPLOAD_OK,
            document_name_hash=hash12(target_name.casefold()),
            http_status_class=put_result.status_class,
        )
        return {
            "ok": True,
            "file": stored,
            "reason_code": document_client.REASON_UPLOAD_OK,
            "status": 201,
            "document_nextcloud": _technical_nextcloud_payload(
                target_name,
                reason_code=document_client.REASON_UPLOAD_OK,
                http_status_class=put_result.status_class,
                upload_state="stored",
                document_link_state=link.get("nextcloud_sync_state") or file_nextcloud_links.NEXTCLOUD_FILE_SYNC_LINKED,
            ),
        }

    rollback = _rollback_remote_created_document(
        client,
        target_folder_name=target_folder_name,
        target_name=target_name,
        workspace_files_module=workspace_files_module,
        folder_id=folder_id,
    )
    return _failure(
        document_client.REASON_LOCAL_PERSISTENCE_FAILED,
        status=503,
        upload_state="local_persistence_failed",
        document_name_hash=hash12(target_name.casefold()),
        rollback=rollback,
    )


def sanitize_nextcloud_document_name(value: Any, source_extension: Any) -> str:
    raw = str(value or "").replace("\\", "/").strip()
    raw = PurePosixPath(raw).name
    raw = unicodedata.normalize("NFKC", " ".join(raw.split()))
    extension = _normalize_extension(source_extension) or _normalize_extension(PurePosixPath(raw).suffix)
    if not raw or not extension:
        return ""

    stem = raw[: -len(PurePosixPath(raw).suffix)] if PurePosixPath(raw).suffix else raw
    stem_parts: list[str] = []
    last_dash = False
    for char in stem:
        category = unicodedata.category(char)
        if char.isalnum() or char in {" ", ".", "_", "-"}:
            stem_parts.append(char)
            last_dash = False
            continue
        if char in _FORBIDDEN_FILENAME_CHARS or category.startswith(("C", "P", "S")):
            if not last_dash:
                stem_parts.append("-")
                last_dash = True
            continue
        if not last_dash:
            stem_parts.append("-")
            last_dash = True

    stem_clean = re.sub(r"\s+", " ", "".join(stem_parts)).strip(" ._-")
    stem_clean = re.sub(r"-{2,}", "-", stem_clean).strip(" ._-")
    if not stem_clean:
        return ""
    max_stem = MAX_DOCUMENT_TARGET_NAME_CHARS - len(extension)
    if max_stem <= 0:
        return ""
    if len(stem_clean) > max_stem:
        stem_clean = stem_clean[:max_stem].rstrip(" ._-")
    if not stem_clean:
        return ""
    return f"{stem_clean}{extension.lower()}"


def hash12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "") or folder_projection.sanitize_nextcloud_folder_name(
        folder.get("display_name")
    )


def _local_name_conflict(workspace_files_module: Any, *, folder_id: str, target_name: str) -> bool:
    list_func = getattr(workspace_files_module, "list_workspace_files", None)
    if not callable(list_func):
        return False
    target_key = target_name.casefold()
    for item in list_func(folder_id) or []:
        if item.get("deleted_at"):
            continue
        existing_name = sanitize_nextcloud_document_name(
            item.get("display_name") or item.get("original_filename"),
            item.get("source_extension"),
        )
        if existing_name and existing_name.casefold() == target_key:
            return True
    return False


def _store_local(
    workspace_files_module: Any,
    *,
    folder_id: str,
    file_id: str,
    original_filename: str,
    content: bytes,
    metadata: Mapping[str, Any],
) -> dict[str, Any] | None:
    store = getattr(workspace_files_module, "store_uploaded_file", None)
    if not callable(store):
        return None
    try:
        return store(
            folder_id,
            original_filename=original_filename,
            content=bytes(content or b""),
            metadata=metadata,
            file_id=file_id,
        )
    except Exception:
        return None


def _persist_nextcloud_link(
    workspace_files_module: Any,
    *,
    workspace_file_id: str,
    workspace_folder_id: str,
    target_name: str,
) -> dict[str, Any] | None:
    upsert = getattr(workspace_files_module, "upsert_nextcloud_link", None)
    if not callable(upsert):
        return None
    try:
        name_hash = hash12(target_name.casefold())
        return upsert(
            workspace_file_id=workspace_file_id,
            workspace_folder_id=workspace_folder_id,
            nextcloud_sync_state=file_nextcloud_links.NEXTCLOUD_FILE_SYNC_LINKED,
            nextcloud_document_ref=f"workspace-file:{workspace_file_id[:8]}:{name_hash}",
            nextcloud_name_hash=name_hash,
            nextcloud_target_name=target_name,
            last_sync_reason_code=document_client.REASON_UPLOAD_OK,
            last_sync_operation="upload",
        )
    except Exception:
        return None


def _delete_local_created_file(
    workspace_files_module: Any,
    *,
    folder_id: str,
    file_id: str,
) -> dict[str, Any]:
    delete = getattr(workspace_files_module, "delete_workspace_file", None)
    if not callable(delete):
        return {"ok": False, "reason_code": document_client.REASON_LOCAL_DELETE_FAILED}
    try:
        deleted = delete(folder_id, file_id)
    except Exception:
        deleted = None
    return {
        "ok": bool(deleted),
        "reason_code": document_client.REASON_DELETE_OK
        if deleted
        else document_client.REASON_LOCAL_DELETE_FAILED,
    }


def _rollback_remote_created_document(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    workspace_files_module: Any,
    folder_id: str,
) -> dict[str, Any]:
    try:
        result = client.delete_document(target_folder_name, target_name, missing_ok=True)
        reason_code = result.reason_code
        http_status_class = result.status_class
        ok = True
    except document_client.NextcloudDocumentClientError as exc:
        reason_code = exc.reason_code
        http_status_class = exc.status_class
        ok = False
    _log_event(
        workspace_files_module,
        "documents_v1_upload_compensation",
        level="warning",
        folder_id=folder_id,
        reason_code=reason_code,
        document_name_hash=hash12(target_name.casefold()),
        http_status_class=http_status_class,
    )
    return {
        "ok": ok,
        "reason_code": reason_code,
        "http_status_class": http_status_class,
    }


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return document_client.NextcloudDocumentClient.from_env()


def _failure(
    reason_code: str,
    *,
    status: int,
    upload_state: str,
    http_status_class: str = "none",
    document_name_hash: str = "",
    rollback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": int(status or 500),
        "document_nextcloud": {
            "upload_state": upload_state,
            "reason_code": reason_code,
            "document_name_hash": document_name_hash,
            "http_status_class": http_status_class,
            "rollback": dict(rollback or {}),
        },
    }


def _technical_nextcloud_payload(
    target_name: str,
    *,
    reason_code: str,
    http_status_class: str,
    upload_state: str,
    document_link_state: str = "",
) -> dict[str, Any]:
    payload = {
        "upload_state": upload_state,
        "reason_code": reason_code,
        "document_name_hash": hash12(str(target_name or "").casefold()),
        "http_status_class": http_status_class,
    }
    if document_link_state:
        payload["document_link_state"] = document_link_state
    return payload


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        document_client.REASON_FOLDER_NOT_LINKED,
        document_client.REASON_DOCUMENTS_TARGET_CONFLICT,
        document_client.REASON_DOCUMENTS_TARGET_NOT_COLLECTION,
        document_client.REASON_NAME_CONFLICT,
    }:
        return 409
    if reason_code in {document_client.REASON_DOCUMENTS_TARGET_MISSING}:
        return 404
    if reason_code in {document_client.REASON_NAME_INVALID}:
        return 400
    return 502


def _normalize_extension(value: Any) -> str:
    text = str(value or "").strip().lower()
    if text and not text.startswith("."):
        text = f".{text}"
    return text if _ALLOWED_EXTENSION_RE.fullmatch(text) else ""


def _log_event(workspace_files_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(workspace_files_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
