from __future__ import annotations

import hashlib
import uuid
from typing import Any, Mapping

from . import workspace_folder_note_nextcloud_client as note_client
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection
from . import workspace_folder_notes


def create_workspace_note_nextcloud_first(
    *,
    folder: Mapping[str, Any],
    title: str,
    markdown: str,
    notes_module: Any,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    folder_id = str(folder.get("id") or "")
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(
            workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
            status=409,
            create_state="blocked",
        )

    target_folder_name = _target_folder_name(folder)
    if not target_folder_name:
        return _failure(
            workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE,
            status=502,
            create_state="blocked",
        )

    markdown_text = str(markdown or "")
    if len(markdown_text) > workspace_folder_notes.NOTE_CREATE_MARKDOWN_MAX_CHARS:
        return _failure(
            workspace_folder_notes.REASON_TOO_LARGE,
            status=413,
            create_state="blocked",
        )

    try:
        existing_notes = notes_module.list_notes(folder_id, include_deleted=False, fail_closed=True)
    except Exception:
        return _failure(
            workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
            create_state="lookup_failed",
        )

    validation = workspace_folder_notes.validate_note_title(title, existing_notes=existing_notes)
    if not validation.get("ok"):
        return _failure(
            str(validation.get("reason_code") or workspace_folder_notes.REASON_NAME_INVALID),
            status=_http_status_for_reason(str(validation.get("reason_code") or "")),
            create_state="blocked",
            note_name_hash=str(validation.get("title_hash") or ""),
        )

    target_name = str(validation["target_name"])
    title_value = str(validation["title"])
    title_hash = str(validation["title_hash"])

    try:
        client = _client(nextcloud)
        client.notes_status(target_folder_name)
        put_result = client.put_note(
            target_folder_name,
            target_name,
            markdown_text.encode("utf-8"),
        )
    except note_client.NextcloudNoteClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            create_state="nextcloud_failed",
            http_status_class=exc.status_class,
            note_name_hash=title_hash,
        )

    note_id = str(uuid.uuid4())
    try:
        stored = notes_module.upsert_note(
            note_id=note_id,
            workspace_folder_id=folder_id,
            title=title_value,
            target_name=target_name,
            local_state=workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
            nextcloud_sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
            remote_note_ref=_remote_note_ref(note_id, title_hash),
            etag_value=put_result.etag_value,
            etag_hash=hash12(put_result.etag_value),
            markdown_char_count=len(markdown_text),
            reason_code=workspace_folder_notes.REASON_CREATE_OK,
        )
    except Exception:
        rollback = _rollback_remote_created_note(
            client,
            target_folder_name=target_folder_name,
            target_name=target_name,
            etag_value=put_result.etag_value,
            notes_module=notes_module,
            folder_id=folder_id,
        )
        return _failure(
            workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED,
            status=503,
            create_state="local_persistence_failed",
            note_name_hash=title_hash,
            rollback=rollback,
        )

    _log_event(
        notes_module,
        "notes_v1_create_ok",
        folder_id=folder_id,
        note_id=stored.get("id"),
        reason_code=workspace_folder_notes.REASON_CREATE_OK,
        note_name_hash=title_hash,
        http_status_class=put_result.status_class,
    )
    return {
        "ok": True,
        "note": stored,
        "reason_code": workspace_folder_notes.REASON_CREATE_OK,
        "status": 201,
        "note_nextcloud": _technical_nextcloud_payload(
            target_name,
            reason_code=workspace_folder_notes.REASON_CREATE_OK,
            http_status_class=put_result.status_class,
            create_state="stored",
            etag_hash=hash12(put_result.etag_value),
        ),
    }


def runtime_secret_status() -> dict[str, Any]:
    return note_client.secret_status_from_env()


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


def _remote_note_ref(note_id: str, title_hash: str) -> str:
    short_id = str(note_id or "")[:8] or "redacted"
    name_hash = str(title_hash or "")[:12] or "redacted"
    return f"workspace-note:{short_id}:{name_hash}"


def _rollback_remote_created_note(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    etag_value: str,
    notes_module: Any,
    folder_id: str,
) -> dict[str, Any]:
    if not str(etag_value or "").strip():
        reason_code = workspace_folder_notes.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED
        http_status_class = "none"
        ok = False
    else:
        try:
            result = client.delete_created_note_if_match(
                target_folder_name,
                target_name,
                etag_value=etag_value,
            )
            reason_code = result.reason_code
            http_status_class = result.status_class
            ok = reason_code in {
                workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK,
                workspace_folder_notes.REASON_REMOTE_COMPENSATION_MISSING,
            }
        except note_client.NextcloudNoteClientError as exc:
            reason_code = (
                exc.reason_code
                if exc.reason_code
                in {
                    workspace_folder_notes.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
                    workspace_folder_notes.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
                    workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED,
                }
                else workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED
            )
            http_status_class = exc.status_class
            ok = False
    _log_event(
        notes_module,
        "notes_v1_create_compensation",
        level="warning",
        folder_id=folder_id,
        reason_code=reason_code,
        note_name_hash=workspace_folder_notes.title_hash_for_target(target_name),
        http_status_class=http_status_class,
    )
    return {
        "ok": ok,
        "reason_code": reason_code,
        "http_status_class": http_status_class,
        "state": _remote_compensation_state(reason_code),
    }


def _remote_compensation_state(reason_code: str) -> str:
    return {
        workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK: "deleted",
        workspace_folder_notes.REASON_REMOTE_COMPENSATION_MISSING: "missing",
        workspace_folder_notes.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED: "precondition_failed",
        workspace_folder_notes.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED: "ownership_unverified",
    }.get(reason_code, "failed")


def _failure(
    reason_code: str,
    *,
    status: int,
    create_state: str,
    http_status_class: str = "none",
    note_name_hash: str = "",
    rollback: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": int(status or 500),
        "note_nextcloud": {
            "create_state": create_state,
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
    create_state: str,
    etag_hash: str = "",
) -> dict[str, Any]:
    payload = {
        "create_state": create_state,
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
        workspace_folder_notes.REASON_NAME_CONFLICT,
        workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION,
    }:
        return 409
    if reason_code == workspace_folder_notes.REASON_NOTES_TARGET_MISSING:
        return 404
    if reason_code == workspace_folder_notes.REASON_NAME_INVALID:
        return 400
    if reason_code == workspace_folder_notes.REASON_TOO_LARGE:
        return 413
    if reason_code == workspace_folder_notes.REASON_LOOKUP_FAILED:
        return 503
    return 502


def _log_event(notes_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(notes_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
