from __future__ import annotations

"""Notes V1 lookup orchestration.

Lookup uses only the local Notes read-model. It never reads Markdown bodies and
never calls Nextcloud/WebDAV.
"""

from typing import Any, Mapping

from . import workspace_folder_nextcloud_links_store as folder_links
from . import workspace_folder_notes


LOOKUP_MODE_NOTE_ID = "note_id"
LOOKUP_MODE_TITLE = "title"


def lookup_workspace_folder_note(
    folder: Mapping[str, Any],
    *,
    notes_module: Any = workspace_folder_notes,
    note_id: Any = "",
    title: Any = "",
) -> dict[str, Any]:
    folder_id = workspace_folder_notes.normalize_workspace_folder_id(folder.get("id"))
    if not folder_id:
        return _result(
            ok=False,
            reason_code="workspace_folder_id_invalid",
            status=400,
            mode="unknown",
        )

    if str(folder.get("nextcloud_sync_state") or "") != folder_links.NEXTCLOUD_SYNC_LINKED:
        _log_event(
            notes_module,
            "lookup_blocked",
            folder_ref=workspace_folder_notes.folder_ref(folder_id),
            reason_code=workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
        )
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
            status=409,
            mode=_lookup_mode(note_id=note_id, title=title),
        )

    normalized_note_id = workspace_folder_notes.normalize_note_id(note_id)
    if note_id:
        if not normalized_note_id:
            return _not_found(mode=LOOKUP_MODE_NOTE_ID)
        return _lookup_by_id(
            folder,
            folder_id=folder_id,
            note_id=normalized_note_id,
            notes_module=notes_module,
        )

    return _lookup_by_title(
        folder,
        folder_id=folder_id,
        title=title,
        notes_module=notes_module,
    )


def _lookup_by_id(
    folder: Mapping[str, Any],
    *,
    folder_id: str,
    note_id: str,
    notes_module: Any,
) -> dict[str, Any]:
    try:
        note = notes_module.get_note(note_id, fail_closed=True)
    except Exception:
        _log_event(
            notes_module,
            "lookup_failed",
            folder_ref=workspace_folder_notes.folder_ref(folder_id),
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
            mode=LOOKUP_MODE_NOTE_ID,
        )
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
            mode=LOOKUP_MODE_NOTE_ID,
        )
    if not _note_matches_folder(note, folder_id):
        return _not_found(mode=LOOKUP_MODE_NOTE_ID)
    return _found(note, folder=folder, mode=LOOKUP_MODE_NOTE_ID)


def _lookup_by_title(
    folder: Mapping[str, Any],
    *,
    folder_id: str,
    title: Any,
    notes_module: Any,
) -> dict[str, Any]:
    wanted_title = workspace_folder_notes.sanitize_note_title(title)
    wanted_target = workspace_folder_notes.sanitize_note_target_name(wanted_title)
    if not wanted_title or not wanted_target:
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_NAME_INVALID,
            status=400,
            mode=LOOKUP_MODE_TITLE,
        )
    wanted_hash = workspace_folder_notes.title_hash_for_target(wanted_target)
    try:
        notes = notes_module.list_notes(folder_id, include_deleted=False, fail_closed=True)
    except Exception:
        _log_event(
            notes_module,
            "lookup_failed",
            folder_ref=workspace_folder_notes.folder_ref(folder_id),
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
            mode=LOOKUP_MODE_TITLE,
        )
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_LOOKUP_FAILED,
            status=503,
            mode=LOOKUP_MODE_TITLE,
        )

    matches: list[Mapping[str, Any]] = []
    for note in notes or []:
        if not _note_matches_folder(note, folder_id):
            continue
        note_title = workspace_folder_notes.sanitize_note_title(note.get("title"))
        note_target = workspace_folder_notes.sanitize_note_target_name(
            note.get("target_name") or note_title
        )
        note_hash = str(note.get("title_hash") or "")
        if (
            note_title.casefold() == wanted_title.casefold()
            or note_target.casefold() == wanted_target.casefold()
            or note_hash == wanted_hash
        ):
            matches.append(note)

    unique_matches = _unique_notes(matches)
    if not unique_matches:
        return _not_found(mode=LOOKUP_MODE_TITLE)
    if len(unique_matches) > 1:
        return _result(
            ok=False,
            reason_code=workspace_folder_notes.REASON_LOOKUP_AMBIGUOUS,
            status=409,
            mode=LOOKUP_MODE_TITLE,
            matched_count=len(unique_matches),
        )
    return _found(unique_matches[0], folder=folder, mode=LOOKUP_MODE_TITLE)


def _note_matches_folder(note: Mapping[str, Any] | None, folder_id: str) -> bool:
    if not note or workspace_folder_notes.is_deleted(note):
        return False
    return workspace_folder_notes.normalize_workspace_folder_id(
        note.get("workspace_folder_id")
    ) == folder_id


def _unique_notes(notes: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    seen: set[str] = set()
    result: list[Mapping[str, Any]] = []
    for note in notes:
        note_id = workspace_folder_notes.normalize_note_id(note.get("id"))
        key = note_id or workspace_folder_notes.note_ref(note.get("id"))
        if key in seen:
            continue
        seen.add(key)
        result.append(note)
    return result


def _found(note: Mapping[str, Any], *, folder: Mapping[str, Any], mode: str) -> dict[str, Any]:
    return _result(
        ok=True,
        reason_code=workspace_folder_notes.REASON_LOOKUP_OK,
        status=200,
        mode=mode,
        note=workspace_folder_notes.apply_note_projection(note, folder=folder),
        matched_count=1,
    )


def _not_found(*, mode: str) -> dict[str, Any]:
    return _result(
        ok=False,
        reason_code=workspace_folder_notes.REASON_NOT_FOUND,
        status=404,
        mode=mode,
    )


def _result(
    *,
    ok: bool,
    reason_code: str,
    status: int,
    mode: str,
    note: dict[str, Any] | None = None,
    matched_count: int = 0,
) -> dict[str, Any]:
    return {
        "ok": bool(ok),
        "reason_code": str(reason_code or workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED),
        "status": int(status or 500),
        "note": dict(note or {}),
        "lookup": {
            "mode": str(mode or "unknown"),
            "matched_count": max(0, int(matched_count or 0)),
        },
    }


def _lookup_mode(*, note_id: Any, title: Any) -> str:
    if note_id:
        return LOOKUP_MODE_NOTE_ID
    if title:
        return LOOKUP_MODE_TITLE
    return "unknown"


def _log_event(notes_module: Any, event: str, **fields: Any) -> None:
    log_func = getattr(notes_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, **fields)
