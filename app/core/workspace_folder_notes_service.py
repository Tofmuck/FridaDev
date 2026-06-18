from __future__ import annotations

from typing import Any, Mapping, Tuple

from . import workspace_folder_note_nextcloud_runtime
from . import workspace_folder_notes


REASON_FOLDER_NOT_FOUND = "workspace_folder_not_found"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
REASON_FOLDER_ID_INVALID = "workspace_folder_id_invalid"
REASON_RUNTIME_UNAVAILABLE = "folder_note_runtime_unavailable"


def create_workspace_folder_note_response(
    folder_id: str,
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
    workspace_folder_notes_module: Any = workspace_folder_notes,
    notes_nextcloud_runtime_module: Any = workspace_folder_note_nextcloud_runtime,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error

    title = workspace_folder_notes.sanitize_note_title((data or {}).get("title"))
    markdown_value = (data or {}).get("markdown")
    if markdown_value is None:
        markdown = ""
    elif isinstance(markdown_value, str):
        markdown = markdown_value
    else:
        markdown = str(markdown_value)

    validation = workspace_folder_notes.validate_note_title(
        title,
        existing_notes=[],
    )
    if not validation.get("ok"):
        reason_code = str(validation.get("reason_code") or workspace_folder_notes.REASON_NAME_INVALID)
        return _note_failure(reason_code, status=_http_status_for_reason(reason_code))

    runtime_result = notes_nextcloud_runtime_module.create_workspace_note_nextcloud_first(
        folder=folder,
        title=title,
        markdown=markdown,
        notes_module=workspace_folder_notes_module,
    )
    if not runtime_result.get("ok"):
        reason_code = str(runtime_result.get("reason_code") or REASON_RUNTIME_UNAVAILABLE)
        return {
            "ok": False,
            "error": _human_note_error(reason_code),
            "reason_code": reason_code,
            "note": {
                "status": _note_status_for_failure(reason_code),
                "reason_code": reason_code,
            },
            "note_nextcloud": runtime_result.get("note_nextcloud", {}),
        }, int(runtime_result.get("status") or _http_status_for_reason(reason_code))

    note = runtime_result.get("note") or {}
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "note": workspace_folder_notes.apply_note_projection(note, folder=folder),
        "note_nextcloud": runtime_result.get("note_nextcloud", {}),
    }, 201


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, dict[str, Any], Tuple[dict[str, Any], int] | None]:
    normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    if not normalized:
        return "", {}, (
            {
                "ok": False,
                "error": "folder_id invalide",
                "reason_code": REASON_FOLDER_ID_INVALID,
            },
            400,
        )
    folder = workspace_folders_module.get_workspace_folder(normalized)
    if not folder:
        return "", {}, (
            {
                "ok": False,
                "error": "repertoire introuvable",
                "reason_code": REASON_FOLDER_NOT_FOUND,
            },
            404,
        )
    if folder.get("deleted_at"):
        return "", {}, (
            {
                "ok": False,
                "error": "repertoire supprime",
                "reason_code": REASON_FOLDER_DELETED,
            },
            410,
        )
    return normalized, dict(folder), None


def _note_failure(reason_code: str, *, status: int) -> Tuple[dict[str, Any], int]:
    return {
        "ok": False,
        "error": _human_note_error(reason_code),
        "reason_code": reason_code,
        "note": {
            "status": _note_status_for_failure(reason_code),
            "reason_code": reason_code,
        },
    }, int(status or 400)


def _note_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_notes.REASON_NAME_CONFLICT:
        return workspace_folder_notes.NOTE_LOCAL_CONFLICT
    if reason_code in {
        workspace_folder_notes.REASON_FOLDER_NOT_LINKED,
        workspace_folder_notes.REASON_NOTES_TARGET_MISSING,
        workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION,
        workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE,
        workspace_folder_notes.REASON_LOOKUP_FAILED,
    }:
        return workspace_folder_notes.NOTE_LOCAL_UNAVAILABLE
    if reason_code == workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED:
        return workspace_folder_notes.NOTE_LOCAL_SYNC_ERROR
    return workspace_folder_notes.NOTE_LOCAL_UNAVAILABLE


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


def _human_note_error(reason_code: str) -> str:
    return {
        workspace_folder_notes.REASON_FOLDER_NOT_LINKED: "dossier Frida non lie a Nextcloud",
        workspace_folder_notes.REASON_NOTES_TARGET_MISSING: "sous-dossier Notes introuvable",
        workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION: "cible Notes incompatible",
        workspace_folder_notes.REASON_NOTES_TARGET_UNAVAILABLE: "cible Notes indisponible",
        workspace_folder_notes.REASON_NAME_INVALID: "titre de note invalide",
        workspace_folder_notes.REASON_NAME_CONFLICT: "une note existe deja avec ce titre",
        workspace_folder_notes.REASON_TOO_LARGE: "note trop volumineuse",
        workspace_folder_notes.REASON_LOOKUP_FAILED: "lecture locale des notes indisponible",
        workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED: "persistance locale de la note impossible",
    }.get(reason_code, "creation de note impossible")
