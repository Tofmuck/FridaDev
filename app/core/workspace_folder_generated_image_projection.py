from __future__ import annotations

"""Generated Images V1 user and technical projections."""

from typing import Any, Mapping

from . import workspace_folder_generated_images
from . import workspace_folder_nextcloud_projection


_FORBIDDEN_PAYLOAD_KEYS = {
    "prompt",
    "prompt_text",
    "prompt_summary",
    "prompt_hash",
    "image_bytes",
    "bytes",
    "base64",
    "data_url",
    "image_data_url",
    "payload",
    "provider_payload",
    "webdav_payload",
    "content_hash",
    "etag",
    "etag_value",
    "target_name_internal",
    "target_name",
    "dav_path",
    "dav_url",
    "path",
    "url",
    "href",
    "xml",
    "secret",
    "token",
    "cookie",
    "authorization",
    "app_password",
    "app-password",
}


def apply_generated_image_projection(
    image: Mapping[str, Any] | None,
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    if not image:
        return {}
    payload = _strip_forbidden(image)
    payload["generated_image_v1_user"] = build_user_projection(image, folder=folder)
    payload["generated_image_v1_technical"] = build_technical_projection(image, folder=folder)
    return payload


def apply_generated_image_list(
    images: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    items = []
    for image in images:
        if not include_deleted and is_deleted(image):
            continue
        items.append(apply_generated_image_projection(image, folder=folder))
    return items


def build_user_projection(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = generated_image_state(image, folder=folder)
    actions = build_user_actions(image, folder=folder)
    return {
        "image_id": workspace_folder_generated_images.normalize_generated_image_id(
            image.get("id")
        ),
        "image_ref": image_ref(image.get("id")),
        "workspace_folder_id": workspace_folder_generated_images.normalize_workspace_folder_id(
            image.get("workspace_folder_id")
        ),
        "display_name": workspace_folder_generated_images.sanitize_display_name(
            image.get("display_name")
        ),
        "format": workspace_folder_generated_images.normalize_image_format(
            image.get("image_format") or image.get("format")
        ),
        "mime_type": workspace_folder_generated_images.normalize_mime_type(
            image.get("mime_type")
        ),
        "byte_size": workspace_folder_generated_images.safe_int(image.get("byte_size")),
        "width": workspace_folder_generated_images.safe_int(image.get("width")),
        "height": workspace_folder_generated_images.safe_int(image.get("height")),
        "generator_key": workspace_folder_generated_images.safe_token(
            image.get("generator_key"),
            max_chars=80,
        ),
        "provider_model": workspace_folder_generated_images.safe_model_name(
            image.get("provider_model")
        ),
        "aspect_ratio": workspace_folder_generated_images.safe_token(
            image.get("aspect_ratio"),
            max_chars=40,
        ),
        "image_size": workspace_folder_generated_images.safe_token(
            image.get("image_size"),
            max_chars=40,
        ),
        "status": state["status"],
        "status_label": workspace_folder_generated_images.GENERATED_IMAGE_STATUS_LABELS.get(
            state["status"],
            "indisponible",
        ),
        "nextcloud_sync_state": workspace_folder_generated_images.nextcloud_state(
            image.get("nextcloud_sync_state")
        ),
        "sync_label": workspace_folder_generated_images.sync_label(
            image.get("nextcloud_sync_state")
        ),
        "reason_code": state["reason_code"],
        "created_at": workspace_folder_generated_images.ts_to_iso(image.get("created_at")),
        "updated_at": workspace_folder_generated_images.ts_to_iso(image.get("updated_at")),
        "deleted_at": workspace_folder_generated_images.ts_to_iso(image.get("deleted_at")),
        "can_download": actions["can_download"],
        "can_open": actions["can_open"],
        "can_delete": actions["can_delete"],
        "actions": actions,
    }


def build_technical_projection(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    state = generated_image_state(image, folder=folder)
    etag_hash = workspace_folder_generated_images.hash12(image.get("etag_hash"))
    etag_present = bool(workspace_folder_generated_images.text(image.get("etag_value")) or etag_hash)
    target_ref = workspace_folder_generated_images.safe_target_ref(image.get("target_ref"))
    if not target_ref:
        target_ref = workspace_folder_generated_images.target_ref_for_target(
            image.get("target_name_internal")
        )
    return {
        "image_ref": image_ref(image.get("id")),
        "folder_ref": folder_ref(image.get("workspace_folder_id")),
        "target_ref": target_ref,
        "display_name_hash": workspace_folder_generated_images.hash12(
            image.get("display_name_hash")
        ),
        "format": workspace_folder_generated_images.normalize_image_format(
            image.get("image_format") or image.get("format")
        ),
        "mime_type": workspace_folder_generated_images.normalize_mime_type(
            image.get("mime_type")
        ),
        "content_hash_short": workspace_folder_generated_images.hash12(
            image.get("content_hash_short")
        ),
        "etag_hash": etag_hash,
        "etag_present": etag_present,
        "generator_key": workspace_folder_generated_images.safe_token(
            image.get("generator_key"),
            max_chars=80,
        ),
        "provider_model": workspace_folder_generated_images.safe_model_name(
            image.get("provider_model")
        ),
        "aspect_ratio": workspace_folder_generated_images.safe_token(
            image.get("aspect_ratio"),
            max_chars=40,
        ),
        "image_size": workspace_folder_generated_images.safe_token(
            image.get("image_size"),
            max_chars=40,
        ),
        "prompt_present": bool(image.get("prompt_present")),
        "prompt_length_bucket": workspace_folder_generated_images.normalize_prompt_length_bucket(
            image.get("prompt_length_bucket")
        ),
        "status": state["status"],
        "nextcloud_sync_state": workspace_folder_generated_images.nextcloud_state(
            image.get("nextcloud_sync_state")
        ),
        "reason_code": state["reason_code"],
        "counters": {
            "byte_size": workspace_folder_generated_images.safe_int(image.get("byte_size")),
            "width": workspace_folder_generated_images.safe_int(image.get("width")),
            "height": workspace_folder_generated_images.safe_int(image.get("height")),
        },
    }


def build_user_actions(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    reason_code = ""
    if is_deleted(image):
        reason_code = workspace_folder_generated_images.REASON_DELETED
    elif folder is not None and folder.get("deleted_at"):
        reason_code = workspace_folder_generated_images.REASON_FOLDER_DELETED
    elif (
        folder is not None
        and workspace_folder_generated_images.text(folder.get("nextcloud_sync_state")) != "linked"
    ):
        reason_code = workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED
    elif workspace_folder_generated_images.local_state(image.get("local_state")) != (
        workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_AVAILABLE
    ):
        reason_code = workspace_folder_generated_images.REASON_NOT_LINKED
    elif workspace_folder_generated_images.nextcloud_state(image.get("nextcloud_sync_state")) != (
        workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED
    ):
        reason_code = workspace_folder_generated_images.REASON_NOT_LINKED
    elif not workspace_folder_generated_images.safe_target_name(image.get("target_name_internal")):
        reason_code = workspace_folder_generated_images.REASON_NAME_INVALID
    elif not workspace_folder_generated_images.normalize_image_format(image.get("image_format")):
        reason_code = workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED
    can_access = not reason_code
    return {
        "can_download": can_access,
        "can_open": can_access,
        "can_delete": can_access,
        "download_reason_code": (
            workspace_folder_generated_images.REASON_DOWNLOAD_OK if can_access else reason_code
        ),
        "open_reason_code": (
            workspace_folder_generated_images.REASON_OPEN_OK if can_access else reason_code
        ),
        "delete_reason_code": (
            workspace_folder_generated_images.REASON_DELETE_OK if can_access else reason_code
        ),
    }


def generated_image_state(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, str]:
    if folder is not None:
        folder_state = workspace_folder_generated_images.text(folder.get("nextcloud_sync_state"))
        if folder.get("deleted_at"):
            return {
                "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE,
                "reason_code": workspace_folder_generated_images.REASON_FOLDER_DELETED,
            }
        if folder_state != "linked":
            return {
                "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE,
                "reason_code": workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
            }
    if is_deleted(image):
        return {
            "status": workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_DELETED,
            "reason_code": workspace_folder_generated_images.reason(
                image.get("last_reason_code"),
                workspace_folder_generated_images.REASON_DELETED,
            ),
        }
    state = workspace_folder_generated_images.local_state(image.get("local_state"))
    reason = workspace_folder_generated_images.reason(image.get("last_reason_code"), "")
    if state == workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_AVAILABLE:
        return {
            "status": state,
            "reason_code": reason or workspace_folder_generated_images.REASON_LIST_OK,
        }
    if state == workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_CONFLICT:
        return {
            "status": state,
            "reason_code": reason or workspace_folder_generated_images.REASON_NAME_CONFLICT,
        }
    if state == workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_SYNC_ERROR:
        return {
            "status": state,
            "reason_code": reason
            or workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED,
        }
    return {
        "status": state,
        "reason_code": reason or workspace_folder_generated_images.REASON_NOT_FOUND,
    }


def is_deleted(image: Mapping[str, Any]) -> bool:
    return bool(image.get("deleted_at")) or workspace_folder_generated_images.local_state(
        image.get("local_state")
    ) == workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_DELETED


def image_ref(value: Any) -> str:
    return _entity_ref("workspace-generated-image", value)


def folder_ref(value: Any) -> str:
    return _entity_ref("workspace-folder", value)


def _entity_ref(prefix: str, value: Any) -> str:
    raw = workspace_folder_generated_images.text(value, 160)
    normalized = workspace_folder_generated_images.uuid_text(raw)
    short = normalized[:8] if normalized else "redacted"
    digest = workspace_folder_nextcloud_projection.hash12(raw or "unknown")
    return f"{prefix}:{short}:{digest}"


def _strip_forbidden(image: Mapping[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    for key, value in dict(image).items():
        if str(key).lower() in _FORBIDDEN_PAYLOAD_KEYS:
            continue
        payload[str(key)] = value
    return payload
