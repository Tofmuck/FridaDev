from __future__ import annotations

"""Notes V1 read/preparation orchestration.

The Markdown body is fetched from Nextcloud only after an explicit user action.
It is returned solely in the conversation payload for the current turn and is
never persisted locally or exposed in technical projections.
"""

import hashlib
from typing import Any, Mapping

from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection
from . import workspace_folder_note_nextcloud_client as note_client
from . import workspace_folder_notes


NOTE_READ_MAX_CHARS = 120_000
REMOTE_READ_MAX_BYTES = NOTE_READ_MAX_CHARS * 4 + 4096


def prepare_workspace_folder_note_for_conversation(
    folder: Mapping[str, Any],
    *,
    note_id: Any,
    notes_module: Any = workspace_folder_notes,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(folder.get("id"))
    normalized_note_id = workspace_folder_notes.normalize_note_id(note_id)
    if not folder_id or not normalized_note_id:
        return _failure(workspace_folder_notes.REASON_NOT_FOUND, status=404, read_state="blocked")

    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(
            workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
            status=409,
            read_state="blocked",
        )

    try:
        note = notes_module.get_note(normalized_note_id, fail_closed=True)
    except Exception:
        return _failure(
            workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
            read_state="lookup_failed",
        )
    if not _note_is_readable(note, folder_id):
        reason = _note_unreadable_reason(note, folder_id)
        return _failure(reason, status=_http_status_for_reason(reason), read_state="blocked")

    target_folder_name = _target_folder_name(folder)
    target_name = workspace_folder_notes.sanitize_note_target_name(
        note.get("target_name") or note.get("title")
    )
    if not target_folder_name or not target_name:
        return _failure(
            workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE,
            status=502,
            read_state="blocked",
        )

    client = _client(nextcloud)
    try:
        current = client.get_note_content(
            target_folder_name,
            target_name,
            max_bytes=REMOTE_READ_MAX_BYTES,
        )
    except note_client.NextcloudNoteClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            read_state="remote_read_failed",
            http_status_class=exc.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )

    markdown = str(current.markdown or "")
    if len(markdown) > NOTE_READ_MAX_CHARS:
        return _failure(
            workspace_folder_notes.REASON_TOO_LARGE,
            status=413,
            read_state="too_large",
            http_status_class=current.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )

    note_projection = workspace_folder_notes.apply_note_projection(note, folder=folder)
    conversation = {
        "read_state": "ready",
        "reason_code": workspace_folder_notes.REASON_READ_OK,
        "note_ref": workspace_folder_notes.note_ref(normalized_note_id),
        "folder_ref": workspace_folder_notes.folder_ref(folder_id),
        "markdown_char_count": len(markdown),
        "markdown_content": markdown,
        "injection_scope": "current_turn_only",
        "memory_rag_identity_summary": "not_used",
    }
    note_nextcloud = _technical_nextcloud_payload(
        target_name,
        reason_code=workspace_folder_notes.REASON_READ_OK,
        http_status_class=current.status_class,
        read_state="ready",
        etag_hash=hash12(current.etag_value),
    )
    _log_event(
        notes_module,
        "notes_v1_read_ready",
        folder_ref=workspace_folder_notes.folder_ref(folder_id),
        note_ref=workspace_folder_notes.note_ref(normalized_note_id),
        reason_code=workspace_folder_notes.REASON_READ_OK,
        note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        markdown_char_count=len(markdown),
        http_status_class=current.status_class,
    )
    return {
        "ok": True,
        "reason_code": workspace_folder_notes.REASON_READ_OK,
        "status": 200,
        "note": note_projection,
        "note_conversation": conversation,
        "note_nextcloud": note_nextcloud,
    }


def _note_is_readable(note: Mapping[str, Any] | None, folder_id: str) -> bool:
    if not note or workspace_folder_notes.is_deleted(note):
        return False
    if workspace_folder_notes.normalize_workspace_folder_id(note.get("workspace_folder_id")) != folder_id:
        return False
    if str(note.get("local_state") or "") != workspace_folder_notes.NOTE_LOCAL_AVAILABLE:
        return False
    if str(note.get("nextcloud_sync_state") or "") != workspace_folder_notes.NOTE_NEXTCLOUD_LINKED:
        return False
    return True


def _note_unreadable_reason(note: Mapping[str, Any] | None, folder_id: str) -> str:
    if not note or workspace_folder_notes.is_deleted(note):
        return workspace_folder_notes.REASON_NOT_FOUND
    if workspace_folder_notes.normalize_workspace_folder_id(note.get("workspace_folder_id")) != folder_id:
        return workspace_folder_notes.REASON_NOT_FOUND
    return workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED


def hash12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12] if value else ""


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    return str(folder.get("nextcloud_target_name") or "") or folder_projection.sanitize_nextcloud_folder_name(
        folder.get("display_name")
    )


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return note_client.NextcloudNoteClient.from_env()


def _failure(
    reason_code: str,
    *,
    status: int,
    read_state: str,
    http_status_class: str = "none",
    note_name_hash: str = "",
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": int(status or 500),
        "note": {},
        "note_conversation": {
            "read_state": read_state,
            "reason_code": reason_code,
            "markdown_char_count": 0,
            "injection_scope": "none",
            "memory_rag_identity_summary": "not_used",
        },
        "note_nextcloud": {
            "read_state": read_state,
            "reason_code": reason_code,
            "note_name_hash": note_name_hash,
            "http_status_class": http_status_class,
            "etag_present": False,
        },
    }


def _technical_nextcloud_payload(
    target_name: str,
    *,
    reason_code: str,
    http_status_class: str,
    read_state: str,
    etag_hash: str = "",
) -> dict[str, Any]:
    payload = {
        "read_state": read_state,
        "reason_code": reason_code,
        "note_name_hash": workspace_folder_notes.title_hash_for_target(target_name),
        "http_status_class": http_status_class,
    }
    if etag_hash:
        payload["etag_hash"] = etag_hash
        payload["etag_present"] = True
    else:
        payload["etag_present"] = False
    return payload


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
        workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code == workspace_folder_notes.REASON_NOT_FOUND:
        return 404
    if reason_code == workspace_folder_notes.REASON_TOO_LARGE:
        return 413
    if reason_code == workspace_folder_notes.REASON_LOOKUP_FAILED:
        return 503
    return 502


def _log_event(notes_module: Any, event: str, **fields: Any) -> None:
    log_func = getattr(notes_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, **fields)
