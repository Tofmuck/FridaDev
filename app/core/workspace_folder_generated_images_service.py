from __future__ import annotations

from typing import Any, Mapping, Tuple

from . import workspace_folder_generated_image_nextcloud_runtime
from . import workspace_folder_generated_images


REASON_FOLDER_NOT_FOUND = "workspace_folder_not_found"
REASON_FOLDER_DELETED = workspace_folder_generated_images.REASON_FOLDER_DELETED
REASON_FOLDER_ID_INVALID = workspace_folder_generated_images.REASON_FOLDER_INVALID
REASON_RUNTIME_UNAVAILABLE = "folder_generated_image_runtime_unavailable"
_CLIENT_IMAGE_ID_KEYS = frozenset({"image_id", "generated_image_id"})


def create_workspace_folder_generated_image_response(
    folder_id: str,
    data: Mapping[str, Any],
    *,
    workspace_folders_module: Any,
    generated_images_module: Any = workspace_folder_generated_images,
    generated_images_runtime_module: Any = workspace_folder_generated_image_nextcloud_runtime,
) -> Tuple[dict[str, Any], int]:
    normalized, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error:
        return error

    payload = dict(data or {})
    if "workspace_folder_id" in payload:
        return _blocked_create_response(
            normalized,
            workspace_folder_generated_images.REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN,
        )
    if any(key in payload for key in _CLIENT_IMAGE_ID_KEYS):
        return _blocked_create_response(
            normalized,
            workspace_folder_generated_images.REASON_CLIENT_IMAGE_ID_FORBIDDEN,
        )
    if str(folder.get("nextcloud_sync_state") or "") != "linked":
        return _blocked_create_response(
            normalized,
            workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
        )

    runtime_result = generated_images_runtime_module.store_workspace_folder_generated_image_nextcloud_first(
        folder=folder,
        request=payload,
        images_module=generated_images_module,
    )
    if not runtime_result.get("ok"):
        reason_code = str(runtime_result.get("reason_code") or REASON_RUNTIME_UNAVAILABLE)
        return {
            "ok": False,
            "error": _human_image_error(reason_code),
            "reason_code": reason_code,
            "workspace_folder_id": normalized,
            "generated_image": runtime_result.get(
                "generated_image",
                {
                    "status": _image_status_for_failure(reason_code),
                    "reason_code": reason_code,
                },
            ),
            "generated_image_v1_technical": runtime_result.get(
                "generated_image_v1_technical",
                {},
            ),
            "generated_image_nextcloud": runtime_result.get("generated_image_nextcloud", {}),
        }, int(runtime_result.get("status") or _http_status_for_reason(reason_code))

    image = runtime_result.get("generated_image") or {}
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "generated_image": generated_images_module.apply_generated_image_projection(
            image,
            folder=folder,
        ),
        "generated_image_nextcloud": runtime_result.get("generated_image_nextcloud", {}),
        "reason_code": workspace_folder_generated_images.REASON_STORE_OK,
    }, 201


def list_workspace_folder_generated_images_response(
    folder_id: str,
    *,
    workspace_folders_module: Any,
    generated_images_module: Any = workspace_folder_generated_images,
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
        images = generated_images_module.list_generated_images(
            normalized,
            include_deleted=False,
            fail_closed=True,
        )
    except Exception:
        return _lookup_failure_response(normalized, list_response=True)

    projected = generated_images_module.apply_generated_image_list(
        images,
        folder=folder,
    )
    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "generated_images": projected,
        "count": len(projected),
        "reason_code": workspace_folder_generated_images.REASON_LIST_OK,
    }, 200


def get_workspace_folder_generated_image_response(
    folder_id: str,
    image_id: str,
    *,
    workspace_folders_module: Any,
    generated_images_module: Any = workspace_folder_generated_images,
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

    normalized_image_id = workspace_folder_generated_images.normalize_generated_image_id(image_id)
    if not normalized_image_id:
        return _image_id_invalid_response(normalized)
    try:
        image = generated_images_module.get_generated_image(
            normalized_image_id,
            fail_closed=True,
        )
    except Exception:
        return _lookup_failure_response(normalized, image_id=normalized_image_id)
    if not image:
        return _image_not_found_response(normalized)
    image_folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
        image.get("workspace_folder_id")
    )
    if image_folder_id != normalized:
        return _image_not_found_response(normalized)
    if _is_deleted_image(image):
        return _image_deleted_response(normalized, image)

    return {
        "ok": True,
        "workspace_folder_id": normalized,
        "generated_image": generated_images_module.apply_generated_image_projection(
            image,
            folder=folder,
        ),
        "reason_code": workspace_folder_generated_images.REASON_LOOKUP_OK,
    }, 200


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, dict[str, Any], Tuple[dict[str, Any], int] | None]:
    try:
        normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    except Exception:
        return "", {}, _lookup_failure_response("")
    if not normalized:
        return "", {}, (
            {
                "ok": False,
                "error": "dossier Frida invalide",
                "reason_code": REASON_FOLDER_ID_INVALID,
            },
            400,
        )
    try:
        try:
            folder = workspace_folders_module.get_workspace_folder(normalized, include_deleted=True)
        except TypeError:
            folder = workspace_folders_module.get_workspace_folder(normalized)
    except Exception:
        return "", {}, _lookup_failure_response(normalized)
    if not folder:
        return "", {}, (
            {
                "ok": False,
                "error": "dossier Frida introuvable",
                "reason_code": REASON_FOLDER_NOT_FOUND,
                "workspace_folder_id": normalized,
            },
            404,
        )
    if folder.get("deleted_at"):
        return "", {}, (
            {
                "ok": False,
                "error": "dossier Frida supprime",
                "reason_code": REASON_FOLDER_DELETED,
                "workspace_folder_id": normalized,
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
        "error": _human_image_error(workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED),
        "reason_code": workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": _image_status_for_failure(
                workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED
            ),
            "reason_code": workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
        },
    }
    if list_response:
        payload["generated_images"] = []
        payload["count"] = 0
    return payload, 409


def _blocked_create_response(folder_id: str, reason_code: str) -> Tuple[dict[str, Any], int]:
    return {
        "ok": False,
        "error": _human_image_error(reason_code),
        "reason_code": reason_code,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": _image_status_for_failure(reason_code),
            "reason_code": reason_code,
        },
        "generated_image_v1_technical": {"reason_code": reason_code},
        "generated_image_nextcloud": {
            "store_state": "blocked",
            "reason_code": reason_code,
            "target_ref": "",
            "http_status_class": "none",
            "rollback": {},
        },
    }, _http_status_for_reason(reason_code)


def _lookup_failure_response(
    folder_id: str,
    *,
    image_id: str = "",
    list_response: bool = False,
) -> Tuple[dict[str, Any], int]:
    reason_code = workspace_folder_generated_images.REASON_LOOKUP_FAILED
    payload = {
        "ok": False,
        "error": _human_image_error(reason_code),
        "reason_code": reason_code,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": _image_status_for_failure(reason_code),
            "reason_code": reason_code,
        },
    }
    if image_id:
        payload["generated_image_ref"] = workspace_folder_generated_images.build_technical_projection(
            {"id": image_id}
        ).get("image_ref", "")
    if list_response:
        payload["generated_images"] = []
        payload["count"] = 0
    return payload, 503


def _image_id_invalid_response(folder_id: str) -> Tuple[dict[str, Any], int]:
    reason_code = workspace_folder_generated_images.REASON_IMAGE_ID_INVALID
    return {
        "ok": False,
        "error": _human_image_error(reason_code),
        "reason_code": reason_code,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE,
            "reason_code": reason_code,
        },
    }, 400


def _image_not_found_response(folder_id: str) -> Tuple[dict[str, Any], int]:
    reason_code = workspace_folder_generated_images.REASON_NOT_FOUND
    return {
        "ok": False,
        "error": _human_image_error(reason_code),
        "reason_code": reason_code,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE,
            "reason_code": reason_code,
        },
    }, 404


def _image_deleted_response(
    folder_id: str,
    image: Mapping[str, Any],
) -> Tuple[dict[str, Any], int]:
    reason_code = workspace_folder_generated_images.REASON_DELETED
    return {
        "ok": False,
        "error": _human_image_error(reason_code),
        "reason_code": reason_code,
        "workspace_folder_id": folder_id,
        "generated_image": {
            "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_DELETED,
            "reason_code": reason_code,
            "image_ref": workspace_folder_generated_images.build_technical_projection(
                image
            ).get("image_ref", ""),
        },
    }, 410


def _is_deleted_image(image: Mapping[str, Any]) -> bool:
    return bool(image.get("deleted_at")) or workspace_folder_generated_images.local_state(
        image.get("local_state")
    ) == workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_DELETED


def _image_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_generated_images.REASON_NAME_CONFLICT:
        return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_CONFLICT
    if reason_code == workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED:
        return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_SYNC_ERROR
    return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
        workspace_folder_generated_images.REASON_FOLDER_NOT_ELIGIBLE,
        workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION,
        workspace_folder_generated_images.REASON_NAME_CONFLICT,
        workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code == workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING:
        return 404
    if reason_code == workspace_folder_generated_images.REASON_FOLDER_DELETED:
        return 410
    if reason_code in {
        workspace_folder_generated_images.REASON_FOLDER_INVALID,
        workspace_folder_generated_images.REASON_IMAGE_ID_INVALID,
        workspace_folder_generated_images.REASON_CLIENT_IMAGE_ID_FORBIDDEN,
        workspace_folder_generated_images.REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN,
        workspace_folder_generated_images.REASON_PROMPT_MISSING,
        workspace_folder_generated_images.REASON_GENERATOR_UNSUPPORTED,
        workspace_folder_generated_images.REASON_ASPECT_RATIO_UNSUPPORTED,
        workspace_folder_generated_images.REASON_SIZE_UNSUPPORTED,
        workspace_folder_generated_images.REASON_DATA_URL_INVALID,
        workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED,
        workspace_folder_generated_images.REASON_MIME_INVALID,
        workspace_folder_generated_images.REASON_DIMENSIONS_INVALID,
        workspace_folder_generated_images.REASON_NAME_INVALID,
    }:
        return 400
    if reason_code in {
        workspace_folder_generated_images.REASON_PROMPT_TOO_LARGE,
        workspace_folder_generated_images.REASON_DATA_URL_TOO_LARGE,
        workspace_folder_generated_images.REASON_TOO_LARGE,
    }:
        return 413
    if reason_code == workspace_folder_generated_images.REASON_PROVIDER_TIMEOUT:
        return 504
    if reason_code in {
        workspace_folder_generated_images.REASON_LOOKUP_FAILED,
        workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
    }:
        return 503
    return 502


def _human_image_error(reason_code: str) -> str:
    return {
        workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED: "dossier Frida non lie a Nextcloud",
        workspace_folder_generated_images.REASON_FOLDER_INVALID: "dossier Frida invalide",
        workspace_folder_generated_images.REASON_FOLDER_DELETED: "dossier Frida supprime",
        workspace_folder_generated_images.REASON_CLIENT_IMAGE_ID_FORBIDDEN: "identifiant d'image reserve au serveur",
        workspace_folder_generated_images.REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN: "dossier Frida defini par la route",
        workspace_folder_generated_images.REASON_PROMPT_MISSING: "prompt image manquant",
        workspace_folder_generated_images.REASON_PROMPT_TOO_LARGE: "prompt image trop long",
        workspace_folder_generated_images.REASON_GENERATOR_UNSUPPORTED: "generateur image non supporte",
        workspace_folder_generated_images.REASON_ASPECT_RATIO_UNSUPPORTED: "ratio image non supporte",
        workspace_folder_generated_images.REASON_SIZE_UNSUPPORTED: "taille image non supportee",
        workspace_folder_generated_images.REASON_PROVIDER_TIMEOUT: "generation image expiree",
        workspace_folder_generated_images.REASON_PROVIDER_ERROR_REDACTED: "generation image indisponible",
        workspace_folder_generated_images.REASON_PROVIDER_NO_IMAGE: "provider sans image exploitable",
        workspace_folder_generated_images.REASON_PROVIDER_PAYLOAD_INVALID: "reponse provider invalide",
        workspace_folder_generated_images.REASON_DATA_URL_INVALID: "image provider invalide",
        workspace_folder_generated_images.REASON_DATA_URL_TOO_LARGE: "image provider trop volumineuse",
        workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED: "format image non supporte",
        workspace_folder_generated_images.REASON_MIME_INVALID: "type image invalide",
        workspace_folder_generated_images.REASON_TOO_LARGE: "image trop volumineuse",
        workspace_folder_generated_images.REASON_DIMENSIONS_INVALID: "dimensions image invalides",
        workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING: "sous-dossier Images introuvable",
        workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION: "cible Images incompatible",
        workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE: "cible Images indisponible",
        workspace_folder_generated_images.REASON_NAME_CONFLICT: "image deja presente avec cette cible",
        workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED: "persistance locale de l'image impossible",
        workspace_folder_generated_images.REASON_LOOKUP_FAILED: "read-model images indisponible",
        workspace_folder_generated_images.REASON_IMAGE_ID_INVALID: "identifiant d'image invalide",
        workspace_folder_generated_images.REASON_NOT_FOUND: "image generee introuvable",
        workspace_folder_generated_images.REASON_DELETED: "image generee supprimee",
        workspace_folder_generated_images.REASON_ACCESS_NOT_PREPARED: "acces image non prepare",
    }.get(reason_code, "creation d'image impossible")
