from __future__ import annotations

from typing import Any, Mapping, Tuple


REASON_FILE_MISSING = "workspace_file_missing"
REASON_SELECTION_STALE = "workspace_selection_stale"
REASON_RUNTIME_UNAVAILABLE = "workspace_file_runtime_unavailable"


def list_workspace_file_selections_response(
    conversation_id: str,
    *,
    conv_store_module: Any,
    workspace_file_selections_module: Any,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error
    return {
        "ok": True,
        "conversation_id": conv_id,
        "items": workspace_file_selections_module.list_workspace_file_selections(conv_id),
    }, 200


def select_workspace_file_response(
    conversation_id: str,
    data: Mapping[str, Any],
    *,
    conv_store_module: Any,
    workspace_file_selections_module: Any,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error
    file_id = _selection_file_id(data)
    if not file_id:
        return {"ok": False, "error": "file_id requis", "reason_code": REASON_FILE_MISSING}, 400
    result = workspace_file_selections_module.select_workspace_file(conv_id, file_id)
    if not result.get("ok"):
        reason_code = str(result.get("reason_code") or REASON_SELECTION_STALE)
        status = 404 if reason_code == REASON_FILE_MISSING else 409
        return {"ok": False, "error": _human_error(reason_code), "reason_code": reason_code}, status
    return {"ok": True, "conversation_id": conv_id, "selection": result.get("selection")}, 201


def deselect_workspace_file_response(
    conversation_id: str,
    file_id: str,
    *,
    conv_store_module: Any,
    workspace_file_selections_module: Any,
) -> Tuple[dict[str, Any], int]:
    conv_id, error = _resolve_conversation(conversation_id, conv_store_module=conv_store_module)
    if error:
        return error
    normalized = str(file_id or "").strip()
    if not normalized:
        return {"ok": False, "error": "file_id requis", "reason_code": REASON_FILE_MISSING}, 400
    removed = workspace_file_selections_module.deselect_workspace_file(conv_id, normalized)
    if not removed:
        return {"ok": False, "error": "selection introuvable", "reason_code": REASON_FILE_MISSING}, 404
    return {
        "ok": True,
        "conversation_id": conv_id,
        "workspace_file_id": normalized,
        "selected": False,
        "reason_code": "workspace_file_not_selected",
    }, 200


def _resolve_conversation(
    conversation_id: str,
    *,
    conv_store_module: Any,
) -> tuple[str, Tuple[dict[str, Any], int] | None]:
    conv_id = conv_store_module.normalize_conversation_id(conversation_id)
    if not conv_id:
        return "", ({"ok": False, "error": "conversation_id invalide"}, 400)
    summary = conv_store_module.get_conversation_summary(conv_id, include_deleted=True)
    if not summary:
        return "", ({"ok": False, "error": "conversation introuvable"}, 404)
    if summary.get("deleted_at"):
        return "", ({"ok": False, "error": "conversation supprimee", "reason_code": REASON_SELECTION_STALE}, 410)
    return conv_id, None


def _selection_file_id(data: Mapping[str, Any]) -> str:
    if "file_id" in data:
        return str(data.get("file_id") or "").strip()
    if "workspace_file_id" in data:
        return str(data.get("workspace_file_id") or "").strip()
    return ""


def _human_error(reason_code: str) -> str:
    return {
        REASON_FILE_MISSING: "fichier introuvable",
        REASON_SELECTION_STALE: "selection impossible pour cette conversation",
        REASON_RUNTIME_UNAVAILABLE: "selection indisponible",
    }.get(reason_code, "selection impossible")
