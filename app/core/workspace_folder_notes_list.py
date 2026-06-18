from __future__ import annotations

"""Notes V1 folder list orchestration.

The list is served from the local Notes read-model only. It must not call
Nextcloud/WebDAV or read Markdown bodies.
"""

from typing import Any, Mapping

from . import workspace_folder_nextcloud_links_store as folder_links
from . import workspace_folder_notes


def list_workspace_folder_notes(
    folder: Mapping[str, Any],
    *,
    notes_module: Any = workspace_folder_notes,
) -> dict[str, Any]:
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(folder.get("id"))
    if not folder_id:
        return _result(
            ok=False,
            reason_code="workspace_folder_id_invalid",
            status=400,
        )

    if str(folder.get("nextcloud_sync_state") or "") != folder_links.NEXTCLOUD_SYNC_LINKED:
        _log_event(
            notes_module,
            "list_blocked",
            folder_ref=workspace_folder_notes.folder_ref(folder_id),
            reason_code=workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
        )
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
            status=409,
        )

    try:
        notes = notes_module.list_notes(folder_id, include_deleted=False, fail_closed=True)
    except Exception:
        _log_event(
            notes_module,
            "list_lookup_failed",
            folder_ref=workspace_folder_notes.folder_ref(folder_id),
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
        )
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
        )

    items = workspace_folder_notes.apply_note_list(
        list(notes or []),
        folder=folder,
        include_deleted=False,
    )
    _log_event(
        notes_module,
        "list_ok",
        folder_ref=workspace_folder_notes.folder_ref(folder_id),
        reason_code=workspace_folder_notes.REASON_LIST_OK,
        count=len(items),
    )
    return _result(
        ok=True,
        reason_code=workspace_folder_notes.REASON_LIST_OK,
        status=200,
        items=items,
    )


def _result(
    *,
    ok: bool,
    reason_code: str,
    status: int,
    items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    payload_items = list(items or [])
    return {
        "ok": bool(ok),
        "reason_code": str(reason_code or workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED),
        "status": int(status or 500),
        "items": payload_items,
        "count": len(payload_items),
    }


def _log_event(notes_module: Any, event: str, **fields: Any) -> None:
    log_func = getattr(notes_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, **fields)
