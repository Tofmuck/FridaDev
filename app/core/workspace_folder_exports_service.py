from __future__ import annotations

from typing import Any, Mapping, Tuple

from . import workspace_folder_export_conversation_store
from . import workspace_folder_export_nextcloud_runtime
from . import workspace_folder_export_generation
from . import workspace_folder_exports


REASON_FOLDER_NOT_FOUND = "workspace_folder_not_found"
REASON_FOLDER_DELETED = "workspace_folder_deleted"
REASON_FOLDER_ID_INVALID = "workspace_folder_id_invalid"
REASON_RUNTIME_UNAVAILABLE = "folder_export_runtime_unavailable"
PUBLIC_CREATE_UNPREPARED_SOURCE_KINDS = frozenset(
    {
        workspace_folder_exports.SOURCE_MESSAGE_SELECTION,
        workspace_folder_exports.SOURCE_FRIDA_RESPONSE,
    }
)


def create_workspace_folder_export_response(
    folder_id: str,
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
    workspace_folder_exports_module: Any = workspace_folder_exports,
    exports_nextcloud_runtime_module: Any = workspace_folder_export_nextcloud_runtime,
    export_generation_module: Any = workspace_folder_export_generation,
    conversation_store_module: Any | None = None,
    note_reader: Any | None = None,
    document_reader: Any | None = None,
    export_reader: Any | None = None,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error

    payload = dict(data or {})
    if "export_id" in payload:
        return {
            "ok": False,
            "error": _human_export_error(workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN),
            "reason_code": workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN,
            "workspace_folder_id": normalized,
            "export": {
                "status": _export_status_for_failure(
                    workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN
                ),
                "reason_code": workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN,
            },
            "export_v1_technical": {},
            "export_nextcloud": {
                "store_state": "blocked",
                "reason_code": workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN,
                "export_name_hash": "",
                "http_status_class": "none",
                "rollback": {},
            },
        }, 400
    public_source_kind = _public_source_kind(payload)
    if public_source_kind in PUBLIC_CREATE_UNPREPARED_SOURCE_KINDS:
        return {
            "ok": False,
            "error": _human_export_error(workspace_folder_exports.REASON_SOURCE_NOT_PREPARED),
            "reason_code": workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
            "workspace_folder_id": normalized,
            "export": {
                "status": _export_status_for_failure(workspace_folder_exports.REASON_SOURCE_NOT_PREPARED),
                "reason_code": workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
            },
            "export_v1_technical": {
                "reason_code": workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
                "source": {
                    "ok": False,
                    "reason_code": workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
                    "source_kind": public_source_kind,
                },
            },
            "export_nextcloud": {
                "store_state": "blocked",
                "reason_code": workspace_folder_exports.REASON_SOURCE_NOT_PREPARED,
                "export_name_hash": "",
                "http_status_class": "none",
                "rollback": {},
            },
        }, 400
    payload["workspace_folder_id"] = normalized
    runtime_result = exports_nextcloud_runtime_module.store_workspace_folder_export_nextcloud_first(
        folder=folder,
        request=payload,
        exports_module=workspace_folder_exports_module,
        export_generation_module=export_generation_module,
        conversation_reader=_conversation_reader(conversation_store_module),
        note_reader=note_reader,
        document_reader=document_reader,
        export_reader=export_reader,
    )
    if not runtime_result.get("ok"):
        reason_code = str(runtime_result.get("reason_code") or REASON_RUNTIME_UNAVAILABLE)
        return {
            "ok": False,
            "error": _human_export_error(reason_code),
            "reason_code": reason_code,
            "workspace_folder_id": normalized,
            "export": {
                "status": _export_status_for_failure(reason_code),
                "reason_code": reason_code,
            },
            "export_v1_technical": runtime_result.get("export_v1_technical", {}),
            "export_nextcloud": runtime_result.get("export_nextcloud", {}),
        }, int(runtime_result.get("status") or _http_status_for_reason(reason_code))

    export = runtime_result.get("export") or {}
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "export": workspace_folder_exports.apply_export_projection(export, folder=folder),
        "export_nextcloud": runtime_result.get("export_nextcloud", {}),
        "reason_code": workspace_folder_exports.REASON_STORE_OK,
    }, 201


def list_workspace_folder_exports_response(
    folder_id: str,
    *,
    workspace_folders_module: Any,
    workspace_folder_exports_module: Any = workspace_folder_exports,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error
    linked_error = _linked_folder_error(normalized, folder, list_response=True)
    if linked_error:
        return linked_error
    try:
        exports = workspace_folder_exports_module.list_exports(
            normalized,
            include_deleted=False,
            fail_closed=True,
        )
    except Exception:
        return _lookup_failure_response(normalized)

    projected = workspace_folder_exports.apply_export_list(exports, folder=folder)
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "exports": projected,
        "count": len(projected),
        "reason_code": workspace_folder_exports.REASON_LIST_OK,
    }, 200


def get_workspace_folder_export_response(
    folder_id: str,
    export_id: str,
    *,
    workspace_folders_module: Any,
    workspace_folder_exports_module: Any = workspace_folder_exports,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error
    linked_error = _linked_folder_error(normalized, folder, list_response=False)
    if linked_error:
        return linked_error
    normalized_export_id = workspace_folder_exports.normalize_export_id(export_id)
    if not normalized_export_id:
        return _export_not_found_response(normalized)
    try:
        export = workspace_folder_exports_module.get_export(
            normalized_export_id,
            fail_closed=True,
        )
    except Exception:
        return _lookup_failure_response(normalized, export_id=normalized_export_id)
    if not export:
        return _export_not_found_response(normalized)
    export_folder_id = workspace_folder_exports.normalize_workspace_folder_id(
        export.get("workspace_folder_id")
    )
    if export_folder_id != normalized:
        return _export_not_found_response(normalized)
    if workspace_folder_exports.is_deleted(export):
        return _export_deleted_response(normalized, export)

    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "export": workspace_folder_exports.apply_export_projection(export, folder=folder),
        "reason_code": workspace_folder_exports.REASON_LOOKUP_OK,
    }, 200


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
    try:
        folder = workspace_folders_module.get_workspace_folder(normalized, include_deleted=True)
    except TypeError:
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


def _linked_folder_error(
    folder_id: str,
    folder: Mapping[str, Any],
    *,
    list_response: bool,
) -> Tuple[dict[str, Any], int] | None:
    if str(folder.get("nextcloud_sync_state") or "") == "linked":
        return None
    payload = {
        "ok": False,
        "error": _human_export_error(workspace_folder_exports.REASON_FOLDER_NOT_LINKED),
        "reason_code": workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        "workspace_folder_id": folder_id,
        "export": {
            "status": _export_status_for_failure(workspace_folder_exports.REASON_FOLDER_NOT_LINKED),
            "reason_code": workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        },
    }
    if list_response:
        payload["exports"] = []
        payload["count"] = 0
    return payload, 409


def _lookup_failure_response(
    folder_id: str,
    *,
    export_id: str = "",
) -> Tuple[dict[str, Any], int]:
    payload = {
        "ok": False,
        "error": _human_export_error(workspace_folder_exports.REASON_LOOKUP_FAILED),
        "reason_code": workspace_folder_exports.REASON_LOOKUP_FAILED,
        "workspace_folder_id": folder_id,
        "export": {
            "status": _export_status_for_failure(workspace_folder_exports.REASON_LOOKUP_FAILED),
            "reason_code": workspace_folder_exports.REASON_LOOKUP_FAILED,
        },
    }
    if export_id:
        payload["export_ref"] = workspace_folder_exports.export_ref(export_id)
    else:
        payload["exports"] = []
        payload["count"] = 0
    return payload, 503


def _export_not_found_response(folder_id: str) -> Tuple[dict[str, Any], int]:
    return {
        "ok": False,
        "error": _human_export_error(workspace_folder_exports.REASON_EXPORT_NOT_FOUND),
        "reason_code": workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
        "workspace_folder_id": folder_id,
        "export": {
            "status": workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE,
            "reason_code": workspace_folder_exports.REASON_EXPORT_NOT_FOUND,
        },
    }, 404


def _export_deleted_response(
    folder_id: str,
    export: Mapping[str, Any],
) -> Tuple[dict[str, Any], int]:
    return {
        "ok": False,
        "error": _human_export_error(workspace_folder_exports.REASON_EXPORT_DELETED),
        "reason_code": workspace_folder_exports.REASON_EXPORT_DELETED,
        "workspace_folder_id": folder_id,
        "export": {
            "status": workspace_folder_exports.EXPORT_LOCAL_DELETED,
            "reason_code": workspace_folder_exports.REASON_EXPORT_DELETED,
            "export_ref": workspace_folder_exports.export_ref(export.get("id")),
        },
    }, 410


def _conversation_reader(conversation_store_module: Any | None):
    if conversation_store_module is None:
        return None

    def reader(payload: Mapping[str, Any]) -> dict[str, Any]:
        return workspace_folder_export_conversation_store.read_conversation_source(
            payload,
            conv_store_module=conversation_store_module,
        )

    return reader


def _public_source_kind(payload: Mapping[str, Any]) -> str:
    text = " ".join(str(payload.get("source_kind") or payload.get("source") or "").strip().split())
    return workspace_folder_exports.normalize_source_kind(text.lower().replace("-", "_"))


def _export_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_exports.REASON_NAME_CONFLICT:
        return workspace_folder_exports.EXPORT_LOCAL_CONFLICT
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        workspace_folder_exports.REASON_FOLDER_INVALID,
        workspace_folder_exports.REASON_FOLDER_DELETED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING,
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE,
        workspace_folder_exports.REASON_LOOKUP_FAILED,
    }:
        return workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE
    if reason_code == workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED:
        return workspace_folder_exports.EXPORT_LOCAL_SYNC_ERROR
    return workspace_folder_exports.EXPORT_LOCAL_UNAVAILABLE


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED,
        workspace_folder_exports.REASON_FOLDER_DELETED,
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION,
        workspace_folder_exports.REASON_NAME_CONFLICT,
        workspace_folder_exports.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code == workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING:
        return 404
    if reason_code == workspace_folder_exports.REASON_EXPORT_NOT_FOUND:
        return 404
    if reason_code == workspace_folder_exports.REASON_EXPORT_DELETED:
        return 410
    if reason_code in {
        workspace_folder_exports.REASON_FOLDER_INVALID,
        workspace_folder_exports.REASON_NAME_INVALID,
        workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN,
        workspace_folder_exports.REASON_SOURCE_MISSING,
        workspace_folder_exports.REASON_SOURCE_AMBIGUOUS,
        workspace_folder_exports.REASON_SOURCE_UNSUPPORTED,
        workspace_folder_exports.REASON_FORMAT_UNSUPPORTED,
    }:
        return 400
    if reason_code in {
        workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE,
        workspace_folder_exports.REASON_TOO_LARGE,
    }:
        return 413
    if reason_code in {
        workspace_folder_exports.REASON_LOOKUP_FAILED,
        workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED,
    }:
        return 503
    return 502


def _human_export_error(reason_code: str) -> str:
    return {
        workspace_folder_exports.REASON_FOLDER_NOT_LINKED: "dossier Frida non lie a Nextcloud",
        workspace_folder_exports.REASON_FOLDER_INVALID: "dossier Frida invalide",
        workspace_folder_exports.REASON_FOLDER_DELETED: "dossier Frida supprime",
        workspace_folder_exports.REASON_EXPORTS_TARGET_MISSING: "sous-dossier Exports introuvable",
        workspace_folder_exports.REASON_EXPORTS_TARGET_NOT_COLLECTION: "cible Exports incompatible",
        workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE: "cible Exports indisponible",
        workspace_folder_exports.REASON_NAME_INVALID: "nom d'export invalide",
        workspace_folder_exports.REASON_NAME_CONFLICT: "un export existe deja avec ce nom",
        workspace_folder_exports.REASON_CLIENT_EXPORT_ID_FORBIDDEN: "identifiant d'export reserve au serveur",
        workspace_folder_exports.REASON_SOURCE_MISSING: "source d'export manquante",
        workspace_folder_exports.REASON_SOURCE_AMBIGUOUS: "source d'export ambigue",
        workspace_folder_exports.REASON_SOURCE_UNSUPPORTED: "source d'export non supportee",
        workspace_folder_exports.REASON_SOURCE_UNAVAILABLE: "source d'export indisponible",
        workspace_folder_exports.REASON_SOURCE_NOT_PREPARED: "source d'export non preparee",
        workspace_folder_exports.REASON_SOURCE_READ_UNAVAILABLE: "lecture de source impossible",
        workspace_folder_exports.REASON_SOURCE_READ_TOO_LARGE: "source d'export trop volumineuse",
        workspace_folder_exports.REASON_FORMAT_UNSUPPORTED: "format d'export non supporte",
        workspace_folder_exports.REASON_DEPENDENCY_UNAVAILABLE: "moteur d'export indisponible",
        workspace_folder_exports.REASON_TOO_LARGE: "export trop volumineux",
        workspace_folder_exports.REASON_LOCAL_PERSISTENCE_FAILED: "persistance locale de l'export impossible",
        workspace_folder_exports.REASON_EXPORT_NOT_FOUND: "export introuvable",
        workspace_folder_exports.REASON_EXPORT_DELETED: "export supprime",
        workspace_folder_exports.REASON_CONTENT_ACCESS_NOT_PREPARED: "lecture de contenu export non preparee",
    }.get(reason_code, "creation d'export impossible")
