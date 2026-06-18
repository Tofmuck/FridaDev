from __future__ import annotations

"""Notes V1 append orchestration.

Append reads and writes the remote Markdown body, but the body remains in memory
only for this operation. It is never persisted locally or exposed in technical
payloads.
"""

import hashlib
from typing import Any, Mapping

from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection
from . import workspace_folder_note_nextcloud_client as note_client
from . import workspace_folder_notes


REASON_APPEND_EMPTY = "folder_note_append_empty"
REASON_ETAG_MISSING = note_client.REASON_ETAG_MISSING
REASON_REMOTE_READ_FAILED = note_client.REASON_REMOTE_READ_FAILED
REASON_REMOTE_WRITE_FAILED = note_client.REASON_REMOTE_WRITE_FAILED

NOTE_APPEND_MAX_CHARS = 20_000
NOTE_TOTAL_MAX_CHARS = 120_000
REMOTE_READ_MAX_BYTES = NOTE_TOTAL_MAX_CHARS * 4 + 4096
APPEND_SEPARATOR = "\n\n---\n\n"


def append_workspace_folder_note(
    folder: Mapping[str, Any],
    *,
    note_id: Any,
    markdown: Any,
    notes_module: Any = workspace_folder_notes,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(folder.get("id"))
    normalized_note_id = workspace_folder_notes.normalize_note_id(note_id)
    if not folder_id or not normalized_note_id:
        return _failure(workspace_folder_notes.REASON_NOT_FOUND, status=404, append_state="blocked")

    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(
            workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
            status=409,
            append_state="blocked",
        )

    append_text = str(markdown or "")
    if not append_text.strip():
        return _failure(REASON_APPEND_EMPTY, status=400, append_state="blocked")
    if len(append_text) > NOTE_APPEND_MAX_CHARS:
        return _failure(
            workspace_folder_notes.REASON_APPEND_TOO_LARGE,
            status=413,
            append_state="blocked",
        )

    try:
        note = notes_module.get_note(normalized_note_id, fail_closed=True)
    except Exception:
        return _failure(
            workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
            append_state="lookup_failed",
        )
    if not _note_is_appendable(note, folder_id):
        reason = workspace_folder_notes.REASON_NOT_FOUND
        if note and not workspace_folder_notes.is_deleted(note):
            reason = workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED
        return _failure(reason, status=_http_status_for_reason(reason), append_state="blocked")

    target_folder_name = _target_folder_name(folder)
    target_name = workspace_folder_notes.sanitize_note_target_name(
        note.get("target_name") or note.get("title")
    )
    if not target_folder_name or not target_name:
        return _failure(
            workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE,
            status=502,
            append_state="blocked",
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
            append_state="remote_read_failed",
            http_status_class=exc.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )
    if not current.etag_value:
        return _failure(
            REASON_ETAG_MISSING,
            status=502,
            append_state="etag_missing",
            http_status_class=current.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )
    if len(current.markdown) > NOTE_TOTAL_MAX_CHARS:
        return _failure(
            workspace_folder_notes.REASON_TOO_LARGE,
            status=413,
            append_state="blocked",
            http_status_class=current.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )

    appended_markdown = _append_markdown(current.markdown, append_text)
    if len(appended_markdown) > NOTE_TOTAL_MAX_CHARS:
        return _failure(
            workspace_folder_notes.REASON_TOO_LARGE,
            status=413,
            append_state="blocked",
            http_status_class=current.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )

    try:
        put_result = client.put_note_if_match(
            target_folder_name,
            target_name,
            appended_markdown.encode("utf-8"),
            etag_value=current.etag_value,
        )
    except note_client.NextcloudNoteClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            append_state="remote_write_failed",
            http_status_class=exc.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        )
    if not put_result.etag_value:
        return _failure(
            REASON_ETAG_MISSING,
            status=502,
            append_state="remote_write_etag_missing",
            http_status_class=put_result.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
            rollback={
                "ok": False,
                "reason_code": workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED,
                "http_status_class": "none",
            },
        )

    try:
        stored = notes_module.upsert_note(
            note_id=normalized_note_id,
            workspace_folder_id=folder_id,
            title=str(note.get("title") or ""),
            target_name=target_name,
            local_state=workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
            nextcloud_sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
            remote_note_ref=str(note.get("remote_note_ref") or ""),
            etag_value=put_result.etag_value,
            etag_hash=hash12(put_result.etag_value),
            markdown_char_count=len(appended_markdown),
            reason_code=workspace_folder_notes.REASON_APPEND_OK,
        )
    except Exception:
        rollback = _restore_previous_remote_content(
            client,
            target_folder_name=target_folder_name,
            target_name=target_name,
            previous_markdown=current.markdown,
            etag_value=put_result.etag_value,
            notes_module=notes_module,
            folder_id=folder_id,
        )
        return _failure(
            workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED,
            status=503,
            append_state="local_persistence_failed",
            http_status_class=put_result.status_class,
            note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
            rollback=rollback,
        )

    _log_event(
        notes_module,
        "notes_v1_append_ok",
        folder_ref=workspace_folder_notes.folder_ref(folder_id),
        note_ref=workspace_folder_notes.note_ref(normalized_note_id),
        reason_code=workspace_folder_notes.REASON_APPEND_OK,
        note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        http_status_class=put_result.status_class,
    )
    return {
        "ok": True,
        "note": stored,
        "reason_code": workspace_folder_notes.REASON_APPEND_OK,
        "status": 200,
        "note_nextcloud": _technical_nextcloud_payload(
            target_name,
            reason_code=workspace_folder_notes.REASON_APPEND_OK,
            http_status_class=put_result.status_class,
            append_state="appended",
            etag_hash=hash12(put_result.etag_value),
        ),
    }


def _note_is_appendable(note: Mapping[str, Any] | None, folder_id: str) -> bool:
    if not note or workspace_folder_notes.is_deleted(note):
        return False
    if workspace_folder_notes.normalize_workspace_folder_id(note.get("workspace_folder_id")) != folder_id:
        return False
    if str(note.get("local_state") or "") != workspace_folder_notes.NOTE_LOCAL_AVAILABLE:
        return False
    if str(note.get("nextcloud_sync_state") or "") != workspace_folder_notes.NOTE_NEXTCLOUD_LINKED:
        return False
    return True


def _append_markdown(current: str, addition: str) -> str:
    base = str(current or "")
    if not base.strip():
        return str(addition or "")
    return f"{base}{APPEND_SEPARATOR}{addition}"


def _restore_previous_remote_content(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    previous_markdown: str,
    etag_value: str,
    notes_module: Any,
    folder_id: str,
) -> dict[str, Any]:
    try:
        result = client.put_note_if_match(
            target_folder_name,
            target_name,
            str(previous_markdown or "").encode("utf-8"),
            etag_value=etag_value,
        )
        reason_code = workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK
        http_status_class = result.status_class
        ok = True
    except note_client.NextcloudNoteClientError as exc:
        reason_code = workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED
        http_status_class = exc.status_class
        ok = False
    _log_event(
        notes_module,
        "notes_v1_append_compensation",
        level="warning",
        folder_ref=workspace_folder_notes.folder_ref(folder_id),
        reason_code=reason_code,
        note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        http_status_class=http_status_class,
    )
    return {
        "ok": ok,
        "reason_code": reason_code,
        "http_status_class": http_status_class,
    }


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
    append_state: str,
    http_status_class: str = "none",
    note_name_hash: str = "",
    rollback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": int(status or 500),
        "note_nextcloud": {
            "append_state": append_state,
            "reason_code": reason_code,
            "note_name_hash": note_name_hash,
            "http_status_class": http_status_class,
            "rollback": dict(rollback or {}),
        },
    }


def _technical_nextcloud_payload(
    target_name: str,
    *,
    reason_code: str,
    http_status_class: str,
    append_state: str,
    etag_hash: str = "",
) -> dict[str, Any]:
    payload = {
        "append_state": append_state,
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
        workspace_folder_notes.REASON_VERSION_CONFLICT,
        workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code == workspace_folder_notes.REASON_NOT_FOUND:
        return 404
    if reason_code in {REASON_APPEND_EMPTY, workspace_folder_notes.REASON_NAME_INVALID}:
        return 400
    if reason_code in {
        workspace_folder_notes.REASON_APPEND_TOO_LARGE,
        workspace_folder_notes.REASON_TOO_LARGE,
    }:
        return 413
    if reason_code in {
        workspace_folder_notes.REASON_LOOKUP_FAILED,
        workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED,
    }:
        return 503
    return 502


def _log_event(notes_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(notes_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
