from __future__ import annotations

from typing import Any, Mapping, Tuple

REASON_FOLDER_FILES_PRESERVED = "workspace_folder_files_preserved"
_CONFLICT_REASONS = {
    "workspace_folder_name_conflict_local",
    "workspace_folder_name_conflict_sanitized",
    "workspace_folder_name_conflict_case",
}
_VALIDATION_ERROR_MESSAGES = {
    "workspace_folder_name_required": "display_name requis",
    "workspace_folder_name_invalid": "nom de repertoire invalide",
    "workspace_folder_name_too_long": "nom de repertoire trop long",
    "workspace_folder_name_conflict_local": "un repertoire actif utilise deja ce nom",
    "workspace_folder_name_conflict_sanitized": "un repertoire actif utilise deja ce nom cible",
    "workspace_folder_name_conflict_case": "un repertoire actif utilise deja ce nom avec une casse differente",
}


def list_workspace_folders(
    _args: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
) -> dict[str, Any]:
    items = workspace_folders_module.list_workspace_folders()
    return {
        "ok": True,
        "items": items,
        "icon_keys": list(workspace_folders_module.WORKSPACE_FOLDER_ICON_KEYS),
    }


def create_workspace_folder(
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
) -> Tuple[dict[str, Any], int]:
    name_validation = _validate_display_name(
        workspace_folders_module,
        data.get("display_name") or data.get("name") or "",
    )
    if not name_validation.get("ok"):
        return _folder_name_error_response(name_validation)
    display_name = str(name_validation["display_name"])

    icon_key = workspace_folders_module.normalize_icon_key(data.get("icon_key"))
    if icon_key is None:
        return {"ok": False, "error": "icon_key invalide", "reason_code": "workspace_folder_icon_invalid"}, 400

    sort_order = workspace_folders_module.coerce_sort_order(data.get("sort_order"))
    if "sort_order" in data and sort_order is None:
        return {"ok": False, "error": "sort_order invalide", "reason_code": "workspace_folder_sort_order_invalid"}, 400
    folder = workspace_folders_module.create_workspace_folder(
        display_name=display_name,
        icon_key=icon_key,
        description=workspace_folders_module.sanitize_description(data.get("description") or ""),
        sort_order=sort_order,
    )
    if folder is None:
        return {"ok": False, "error": "creation repertoire impossible", "reason_code": "workspace_folder_create_failed"}, 500
    return {"ok": True, "folder": folder}, 201


def patch_workspace_folder(
    folder_id: str,
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
) -> Tuple[dict[str, Any], int]:
    normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    if not normalized:
        return {"ok": False, "error": "folder_id invalide", "reason_code": "workspace_folder_id_invalid"}, 400

    fields: dict[str, Any] = {}
    if "display_name" in data or "name" in data:
        name_validation = _validate_display_name(
            workspace_folders_module,
            data.get("display_name") or data.get("name") or "",
            current_folder_id=normalized,
        )
        if not name_validation.get("ok"):
            return _folder_name_error_response(name_validation)
        fields["display_name"] = str(name_validation["display_name"])
    if "icon_key" in data:
        icon_key = workspace_folders_module.normalize_icon_key(data.get("icon_key"))
        if icon_key is None:
            return {"ok": False, "error": "icon_key invalide", "reason_code": "workspace_folder_icon_invalid"}, 400
        fields["icon_key"] = icon_key
    if "description" in data:
        fields["description"] = workspace_folders_module.sanitize_description(data.get("description") or "")
    if "sort_order" in data:
        sort_order = workspace_folders_module.coerce_sort_order(data.get("sort_order"))
        if sort_order is None:
            return {"ok": False, "error": "sort_order invalide", "reason_code": "workspace_folder_sort_order_invalid"}, 400
        fields["sort_order"] = sort_order
    if not fields:
        return {"ok": False, "error": "aucun champ modifiable", "reason_code": "workspace_folder_patch_empty"}, 400

    folder = workspace_folders_module.update_workspace_folder(normalized, **fields)
    if folder is None:
        return {"ok": False, "error": "repertoire introuvable", "reason_code": "workspace_folder_not_found"}, 404
    return {"ok": True, "folder": folder}, 200


def delete_workspace_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
    workspace_files_module: Any = None,
) -> Tuple[dict[str, Any], int]:
    normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    if not normalized:
        return {"ok": False, "error": "folder_id invalide", "reason_code": "workspace_folder_id_invalid"}, 400

    existing = workspace_folders_module.get_workspace_folder(normalized)
    if existing is None:
        return {"ok": False, "error": "repertoire introuvable", "reason_code": "workspace_folder_not_found"}, 404

    folder = workspace_folders_module.soft_delete_workspace_folder(normalized)
    if folder is None:
        return {"ok": False, "error": "repertoire introuvable", "reason_code": "workspace_folder_not_found"}, 404
    file_delete = {
        "requested": 0,
        "deleted": 0,
        "failed": 0,
        "failed_file_ids": [],
        "reason_code": REASON_FOLDER_FILES_PRESERVED,
        "skipped": True,
    }
    folder["file_delete"] = file_delete
    folder["files_deleted"] = 0
    folder["files_preserved"] = True
    return {"ok": True, "folder": folder}, 200


def _validate_display_name(
    workspace_folders_module: Any,
    value: Any,
    *,
    current_folder_id: str | None = None,
) -> dict[str, Any]:
    validator = getattr(workspace_folders_module, "validate_workspace_folder_display_name", None)
    if callable(validator):
        return validator(value, current_folder_id=current_folder_id)

    display_name = workspace_folders_module.sanitize_display_name(value)
    if not display_name:
        return {"ok": False, "reason_code": "workspace_folder_name_required"}
    return {"ok": True, "display_name": display_name, "reason_code": ""}


def _folder_name_error_response(validation: Mapping[str, Any]) -> Tuple[dict[str, Any], int]:
    reason_code = str(validation.get("reason_code") or "workspace_folder_name_invalid")
    status = 409 if reason_code in _CONFLICT_REASONS else 400
    payload = {
        "ok": False,
        "error": _VALIDATION_ERROR_MESSAGES.get(reason_code, "nom de repertoire invalide"),
        "reason_code": reason_code,
        "nextcloud_sync_state": str(validation.get("nextcloud_sync_state") or "error"),
        "nextcloud_share_state": str(validation.get("nextcloud_share_state") or "unknown"),
        "nextcloud_reason_code": str(validation.get("nextcloud_reason_code") or reason_code),
    }
    name_hash = str(validation.get("nextcloud_name_hash") or "")
    if name_hash:
        payload["nextcloud_name_hash"] = name_hash
    return payload, status
