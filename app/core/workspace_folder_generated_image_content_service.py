from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from . import workspace_folder_generated_image_nextcloud_client as image_client
from . import workspace_folder_generated_image_projection as image_projection
from . import workspace_folder_generated_image_validation
from . import workspace_folder_generated_images
from . import workspace_folder_nextcloud_projection as folder_projection


IMAGE_CONTENT_MAX_BYTES = workspace_folder_generated_image_validation.V1_IMAGE_MAX_BYTES


@dataclass(frozen=True)
class GeneratedImageContentResponse:
    ok: bool
    status: int
    reason_code: str
    content: bytes = b""
    media_type: str = "application/octet-stream"
    headers: Mapping[str, str] | None = None
    payload: Mapping[str, Any] | None = None


def download_workspace_folder_generated_image_response(
    folder_id: str,
    image_id: str,
    *,
    workspace_folders_module: Any,
    generated_images_module: Any = workspace_folder_generated_images,
    nextcloud: Any | None = None,
    disposition: str = "attachment",
) -> GeneratedImageContentResponse:
    folder_id, folder, image, error = _resolve_target(
        folder_id,
        image_id,
        workspace_folders_module=workspace_folders_module,
        generated_images_module=generated_images_module,
    )
    if error is not None:
        return error

    target_name = _target_name(image)
    expected_mime = workspace_folder_generated_images.expected_mime_type(image.get("image_format"))
    try:
        read = _client(nextcloud).read_image(
            _target_folder_name(folder),
            target_name,
            max_bytes=IMAGE_CONTENT_MAX_BYTES,
        )
    except image_client.NextcloudGeneratedImageClientError as exc:
        return _error(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            folder_id=folder_id,
            image_id=image.get("id"),
            target_ref=_target_ref(image),
            http_status_class=exc.status_class,
        )

    validation = _validate_remote_content(read, expected_mime=expected_mime)
    if not validation.ok:
        return _error(
            validation.reason_code,
            status=_http_status_for_reason(validation.reason_code),
            folder_id=folder_id,
            image_id=image.get("id"),
            target_ref=_target_ref(image),
            http_status_class=read.status_class,
        )

    reason_code = (
        workspace_folder_generated_images.REASON_OPEN_OK
        if str(disposition or "").strip().lower() == "inline"
        else workspace_folder_generated_images.REASON_DOWNLOAD_OK
    )
    _log_event(
        generated_images_module,
        "content_read_ok",
        folder_id=folder_id,
        image_id=image.get("id"),
        reason_code=reason_code,
        target_ref=_target_ref(image),
        http_status_class=read.status_class,
    )
    return GeneratedImageContentResponse(
        ok=True,
        status=200,
        reason_code=reason_code,
        content=read.content,
        media_type=validation.mime_type,
        headers={
            "Content-Type": validation.mime_type,
            "Content-Length": str(len(read.content)),
            "Content-Disposition": _content_disposition(
                image,
                image_format=validation.image_format,
                disposition=disposition,
            ),
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "X-Frida-Reason-Code": reason_code,
        },
    )


def delete_workspace_folder_generated_image_response(
    folder_id: str,
    image_id: str,
    *,
    workspace_folders_module: Any,
    generated_images_module: Any = workspace_folder_generated_images,
    nextcloud: Any | None = None,
) -> tuple[dict[str, Any], int]:
    folder_id, folder, image, error = _resolve_target(
        folder_id,
        image_id,
        workspace_folders_module=workspace_folders_module,
        generated_images_module=generated_images_module,
    )
    if error is not None:
        return dict(error.payload or {}), error.status

    image_id = workspace_folder_generated_images.normalize_generated_image_id(image.get("id"))
    target_name = _target_name(image)
    target_ref = _target_ref(image)
    try:
        delete = _client(nextcloud).delete_image(
            _target_folder_name(folder),
            target_name,
            missing_ok=True,
        )
    except image_client.NextcloudGeneratedImageClientError as exc:
        payload = _error(
            workspace_folder_generated_images.REASON_DELETE_FAILED_REDACTED,
            status=_http_status_for_reason(
                workspace_folder_generated_images.REASON_DELETE_FAILED_REDACTED
            ),
            folder_id=folder_id,
            image_id=image_id,
            target_ref=target_ref,
            http_status_class=exc.status_class,
        ).payload
        return dict(payload or {}), _http_status_for_reason(
            workspace_folder_generated_images.REASON_DELETE_FAILED_REDACTED
        )

    remote_already_missing = delete.http_status == 404
    success_reason = (
        workspace_folder_generated_images.REASON_REMOTE_ALREADY_MISSING
        if remote_already_missing
        else workspace_folder_generated_images.REASON_DELETE_OK
    )
    failure_state = (
        "remote_already_missing_local_tombstone_failed"
        if remote_already_missing
        else "remote_deleted_local_tombstone_failed"
    )
    try:
        tombstone = generated_images_module.tombstone_generated_image(
            image_id,
            expected_workspace_folder_id=folder_id,
            expected_target_name_internal=target_name,
            expected_target_ref=target_ref,
            reason_code=success_reason,
        )
        if not tombstone:
            raise LookupError("generated_image_tombstone_precondition_failed")
    except Exception:
        _log_event(
            generated_images_module,
            "delete_tombstone_failed",
            level="warning",
            folder_id=folder_id,
            image_id=image_id,
            reason_code=workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
            target_ref=target_ref,
            http_status_class=delete.status_class,
        )
        payload = _error(
            workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
            status=503,
            folder_id=folder_id,
            image_id=image_id,
            target_ref=target_ref,
            http_status_class=delete.status_class,
        ).payload
        result = dict(payload or {})
        result["generated_image_delete"] = {
            "delete_state": failure_state,
            "reason_code": workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
            "target_ref": target_ref,
            "http_status_class": delete.status_class,
        }
        return result, 503

    _log_event(
        generated_images_module,
        "delete_ok",
        folder_id=folder_id,
        image_id=image_id,
        reason_code=success_reason,
        target_ref=target_ref,
        http_status_class=delete.status_class,
    )
    projected = (
        generated_images_module.apply_generated_image_projection(tombstone, folder=folder)
        if tombstone
        else {}
    )
    return {
        "ok": True,
        "workspace_folder_id": folder_id,
        "generated_image": projected,
        "generated_image_delete": {
            "delete_state": "remote_already_missing" if remote_already_missing else "deleted",
            "reason_code": success_reason,
            "target_ref": target_ref,
            "http_status_class": delete.status_class,
        },
        "reason_code": success_reason,
    }, 200


def _resolve_target(
    folder_id: str,
    image_id: str,
    *,
    workspace_folders_module: Any,
    generated_images_module: Any,
) -> tuple[str, dict[str, Any], dict[str, Any], GeneratedImageContentResponse | None]:
    normalized_folder, folder, error = _resolve_existing_folder(
        folder_id,
        workspace_folders_module=workspace_folders_module,
    )
    if error is not None:
        return normalized_folder, folder, {}, error
    if str(folder.get("nextcloud_sync_state") or "") != "linked":
        return normalized_folder, folder, {}, _error(
            workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
            status=409,
            folder_id=normalized_folder,
        )

    image, error = _resolve_image(
        normalized_folder,
        image_id,
        generated_images_module=generated_images_module,
    )
    if error is not None:
        return normalized_folder, folder, image, error

    target_name = _target_name(image)
    image_format = workspace_folder_generated_images.normalize_image_format(
        image.get("image_format") or image.get("format")
    )
    extension = workspace_folder_generated_images.extension_for_format(image_format)
    expected_mime = workspace_folder_generated_images.expected_mime_type(image_format)
    if not target_name or (extension and not target_name.endswith(extension)):
        return normalized_folder, folder, image, _error(
            workspace_folder_generated_images.REASON_NAME_INVALID,
            status=400,
            folder_id=normalized_folder,
            image_id=image.get("id"),
            target_ref=_target_ref(image),
        )
    if not image_format:
        return normalized_folder, folder, image, _error(
            workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED,
            status=400,
            folder_id=normalized_folder,
            image_id=image.get("id"),
            target_ref=_target_ref(image),
        )
    if not expected_mime or workspace_folder_generated_images.normalize_mime_type(
        image.get("mime_type")
    ) != expected_mime:
        return normalized_folder, folder, image, _error(
            workspace_folder_generated_images.REASON_MIME_INVALID,
            status=400,
            folder_id=normalized_folder,
            image_id=image.get("id"),
            target_ref=_target_ref(image),
        )
    return normalized_folder, folder, image, None


def _resolve_existing_folder(
    folder_id: str,
    *,
    workspace_folders_module: Any,
) -> tuple[str, dict[str, Any], GeneratedImageContentResponse | None]:
    try:
        normalized = workspace_folders_module.normalize_workspace_folder_id(folder_id)
    except Exception:
        return "", {}, _error(
            workspace_folder_generated_images.REASON_LOOKUP_FAILED,
            status=503,
        )
    if not normalized:
        return "", {}, _error(
            workspace_folder_generated_images.REASON_FOLDER_INVALID,
            status=400,
        )
    try:
        try:
            folder = workspace_folders_module.get_workspace_folder(normalized, include_deleted=True)
        except TypeError:
            folder = workspace_folders_module.get_workspace_folder(normalized)
    except Exception:
        return normalized, {}, _error(
            workspace_folder_generated_images.REASON_LOOKUP_FAILED,
            status=503,
            folder_id=normalized,
        )
    if not folder:
        return normalized, {}, _error("workspace_folder_not_found", status=404, folder_id=normalized)
    if folder.get("deleted_at"):
        return normalized, dict(folder), _error(
            workspace_folder_generated_images.REASON_FOLDER_DELETED,
            status=410,
            folder_id=normalized,
        )
    return normalized, dict(folder), None


def _resolve_image(
    folder_id: str,
    image_id: str,
    *,
    generated_images_module: Any,
) -> tuple[dict[str, Any], GeneratedImageContentResponse | None]:
    normalized_image_id = workspace_folder_generated_images.normalize_generated_image_id(image_id)
    if not normalized_image_id:
        return {}, _error(
            workspace_folder_generated_images.REASON_IMAGE_ID_INVALID,
            status=400,
            folder_id=folder_id,
        )
    try:
        image = generated_images_module.get_generated_image(
            normalized_image_id,
            fail_closed=True,
        )
    except Exception:
        return {}, _error(
            workspace_folder_generated_images.REASON_LOOKUP_FAILED,
            status=503,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    if not image:
        return {}, _error(
            workspace_folder_generated_images.REASON_NOT_FOUND,
            status=404,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    image_folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
        image.get("workspace_folder_id")
    )
    if image_folder_id != folder_id:
        return dict(image), _error(
            workspace_folder_generated_images.REASON_NOT_FOUND,
            status=404,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    if image_projection.is_deleted(image):
        return dict(image), _error(
            workspace_folder_generated_images.REASON_DELETED,
            status=410,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    if workspace_folder_generated_images.local_state(image.get("local_state")) != (
        workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_AVAILABLE
    ):
        return dict(image), _error(
            workspace_folder_generated_images.REASON_NOT_LINKED,
            status=409,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    if workspace_folder_generated_images.nextcloud_state(image.get("nextcloud_sync_state")) != (
        workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED
    ):
        return dict(image), _error(
            workspace_folder_generated_images.REASON_NOT_LINKED,
            status=409,
            folder_id=folder_id,
            image_id=normalized_image_id,
        )
    return dict(image), None


def _validate_remote_content(
    read: Any,
    *,
    expected_mime: str,
) -> workspace_folder_generated_image_validation.GeneratedImageValidationResult:
    remote_header = workspace_folder_generated_images.normalize_mime_type(
        getattr(read, "media_type", "")
    )
    if remote_header and remote_header != expected_mime:
        return workspace_folder_generated_image_validation.GeneratedImageValidationResult(
            False,
            workspace_folder_generated_images.REASON_MIME_INVALID,
        )
    validation = workspace_folder_generated_image_validation.validate_generated_image_bytes(
        getattr(read, "content", b""),
        expected_mime_type=expected_mime,
    )
    if not validation.ok:
        return validation
    if validation.mime_type != expected_mime:
        return workspace_folder_generated_image_validation.GeneratedImageValidationResult(
            False,
            workspace_folder_generated_images.REASON_MIME_INVALID,
        )
    return validation


def _error(
    reason_code: str,
    *,
    status: int,
    folder_id: str = "",
    image_id: str = "",
    target_ref: str = "",
    http_status_class: str = "none",
) -> GeneratedImageContentResponse:
    safe_reason = _safe_reason(reason_code)
    safe_folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(folder_id)
    payload = {
        "ok": False,
        "error": _human_error(safe_reason),
        "reason_code": safe_reason,
        "workspace_folder_id": safe_folder_id,
        "generated_image": {
            "status": _image_status_for_failure(safe_reason),
            "reason_code": safe_reason,
        },
        "generated_image_v1_technical": {
            "reason_code": safe_reason,
            "image_ref": (
                image_projection.image_ref(image_id) if image_id else ""
            ),
            "folder_ref": (
                image_projection.folder_ref(folder_id) if folder_id else ""
            ),
            "target_ref": workspace_folder_generated_images.safe_target_ref(target_ref),
            "http_status_class": http_status_class,
        },
    }
    if image_id:
        payload["generated_image"]["image_ref"] = image_projection.image_ref(image_id)
    return GeneratedImageContentResponse(
        ok=False,
        status=int(status or 500),
        reason_code=safe_reason,
        payload=payload,
    )


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    target = str(folder.get("nextcloud_target_name") or "").strip()
    if target:
        return target
    return folder_projection.sanitize_nextcloud_folder_name(folder.get("display_name"))


def _target_name(image: Mapping[str, Any]) -> str:
    return workspace_folder_generated_images.safe_target_name(image.get("target_name_internal"))


def _target_ref(image: Mapping[str, Any]) -> str:
    ref = workspace_folder_generated_images.safe_target_ref(image.get("target_ref"))
    if ref:
        return ref
    return workspace_folder_generated_images.target_ref_for_target(image.get("target_name_internal"))


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return image_client.NextcloudGeneratedImageClient.from_env()


def _content_disposition(
    image: Mapping[str, Any],
    *,
    image_format: str,
    disposition: str,
) -> str:
    mode = "inline" if str(disposition or "").strip().lower() == "inline" else "attachment"
    extension = workspace_folder_generated_images.extension_for_format(image_format) or ".img"
    display = workspace_folder_generated_images.sanitize_display_name(image.get("display_name"))
    filename = _ascii_filename(display, fallback=f"generated-image{extension}")
    if not filename.lower().endswith(extension):
        filename = f"{filename}{extension}"
    return f'{mode}; filename="{filename[:180]}"'


def _ascii_filename(value: str, *, fallback: str) -> str:
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", str(value or "")).strip("-._")
    fallback_token = re.sub(r"[^A-Za-z0-9._-]+", "-", fallback).strip("-._")
    return (token or fallback_token or "generated-image")[:170]


def _http_status_for_reason(reason_code: str) -> int:
    if reason_code in {
        workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
        workspace_folder_generated_images.REASON_NOT_LINKED,
        workspace_folder_generated_images.REASON_IMAGES_TARGET_NOT_COLLECTION,
        workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED,
    }:
        return 409
    if reason_code in {
        workspace_folder_generated_images.REASON_NOT_FOUND,
        workspace_folder_generated_images.REASON_IMAGES_TARGET_MISSING,
    }:
        return 404
    if reason_code in {
        workspace_folder_generated_images.REASON_FOLDER_INVALID,
        workspace_folder_generated_images.REASON_IMAGE_ID_INVALID,
        workspace_folder_generated_images.REASON_NAME_INVALID,
        workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED,
        workspace_folder_generated_images.REASON_MIME_INVALID,
        workspace_folder_generated_images.REASON_DIMENSIONS_INVALID,
    }:
        return 400
    if reason_code in {
        workspace_folder_generated_images.REASON_DELETED,
        workspace_folder_generated_images.REASON_FOLDER_DELETED,
    }:
        return 410
    if reason_code == workspace_folder_generated_images.REASON_TOO_LARGE:
        return 413
    if reason_code in {
        workspace_folder_generated_images.REASON_LOOKUP_FAILED,
        workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE,
        workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
    }:
        return 503
    return 502


def _image_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_generated_images.REASON_DELETED:
        return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_DELETED
    return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE


def _human_error(reason_code: str) -> str:
    return {
        workspace_folder_generated_images.REASON_FOLDER_INVALID: "dossier Frida invalide",
        workspace_folder_generated_images.REASON_FOLDER_DELETED: "dossier Frida supprime",
        workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED: (
            "dossier Frida non lie a Nextcloud"
        ),
        workspace_folder_generated_images.REASON_IMAGE_ID_INVALID: "image generee invalide",
        workspace_folder_generated_images.REASON_NOT_FOUND: "image generee introuvable",
        workspace_folder_generated_images.REASON_DELETED: "image generee supprimee",
        workspace_folder_generated_images.REASON_NOT_LINKED: "image generee non liee a Nextcloud",
        workspace_folder_generated_images.REASON_NAME_INVALID: "cible image invalide",
        workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED: "format image non supporte",
        workspace_folder_generated_images.REASON_MIME_INVALID: "type image invalide",
        workspace_folder_generated_images.REASON_TOO_LARGE: "image trop volumineuse",
        workspace_folder_generated_images.REASON_LOOKUP_FAILED: "recherche image impossible",
        workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE: (
            "image distante indisponible"
        ),
        workspace_folder_generated_images.REASON_DELETE_FAILED_REDACTED: (
            "suppression image impossible"
        ),
        workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED: (
            "suppression distante faite, etat local non mis a jour"
        ),
        workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED: (
            "acces image impossible"
        ),
    }.get(reason_code, "acces image impossible")


def _safe_reason(value: Any) -> str:
    text = " ".join(str(value or "").strip().split())
    if text in workspace_folder_generated_images.REASON_CODE_CATALOG:
        return text
    if text == "workspace_folder_not_found":
        return text
    return workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED


def _log_event(images_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(images_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
