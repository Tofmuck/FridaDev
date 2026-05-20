from __future__ import annotations

from typing import Any, Mapping, Tuple


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
    display_name = workspace_folders_module.sanitize_display_name(data.get("display_name") or data.get("name") or "")
    if not display_name:
        return {"ok": False, "error": "display_name requis", "reason_code": "workspace_folder_name_required"}, 400

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
        display_name = workspace_folders_module.sanitize_display_name(data.get("display_name") or data.get("name") or "")
        if not display_name:
            return {"ok": False, "error": "display_name requis", "reason_code": "workspace_folder_name_required"}, 400
        fields["display_name"] = display_name
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

    folder = workspace_folders_module.soft_delete_workspace_folder(normalized)
    if folder is None:
        return {"ok": False, "error": "repertoire introuvable", "reason_code": "workspace_folder_not_found"}, 404
    if workspace_files_module is not None:
        folder["files_deleted"] = workspace_files_module.delete_workspace_files_for_folder(normalized)
    return {"ok": True, "folder": folder}, 200
