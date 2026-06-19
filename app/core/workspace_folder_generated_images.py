from __future__ import annotations

"""Generated Images V1 local read-model helpers.

This module deliberately has no provider, Nextcloud, route or UI behavior. It
models content-free metadata only; raw prompts, image bytes, base64 and data
URLs are never accepted as durable fields.
"""

import logging
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

from . import workspace_folder_generated_image_reason_codes
from . import workspace_folder_nextcloud_projection


GENERATED_IMAGE_LOCAL_AVAILABLE = "available"
GENERATED_IMAGE_LOCAL_SYNC_ERROR = "sync_error"
GENERATED_IMAGE_LOCAL_CONFLICT = "conflict"
GENERATED_IMAGE_LOCAL_DELETED = "deleted"
GENERATED_IMAGE_LOCAL_UNAVAILABLE = "unavailable"
GENERATED_IMAGE_LOCAL_STATES = (
    GENERATED_IMAGE_LOCAL_AVAILABLE,
    GENERATED_IMAGE_LOCAL_SYNC_ERROR,
    GENERATED_IMAGE_LOCAL_CONFLICT,
    GENERATED_IMAGE_LOCAL_DELETED,
    GENERATED_IMAGE_LOCAL_UNAVAILABLE,
)

GENERATED_IMAGE_NEXTCLOUD_LINKED = "linked"
GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR = "sync_error"
GENERATED_IMAGE_NEXTCLOUD_CONFLICT = "conflict"
GENERATED_IMAGE_NEXTCLOUD_DELETED = "deleted"
GENERATED_IMAGE_NEXTCLOUD_UNAVAILABLE = "unavailable"
GENERATED_IMAGE_NEXTCLOUD_STATES = (
    GENERATED_IMAGE_NEXTCLOUD_LINKED,
    GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR,
    GENERATED_IMAGE_NEXTCLOUD_CONFLICT,
    GENERATED_IMAGE_NEXTCLOUD_DELETED,
    GENERATED_IMAGE_NEXTCLOUD_UNAVAILABLE,
)

GENERATED_IMAGE_FORMAT_PNG = "png"
GENERATED_IMAGE_FORMAT_JPEG = "jpeg"
GENERATED_IMAGE_FORMAT_WEBP = "webp"
GENERATED_IMAGE_FORMATS = (
    GENERATED_IMAGE_FORMAT_PNG,
    GENERATED_IMAGE_FORMAT_JPEG,
    GENERATED_IMAGE_FORMAT_WEBP,
)
GENERATED_IMAGE_MIME_BY_FORMAT = {
    GENERATED_IMAGE_FORMAT_PNG: "image/png",
    GENERATED_IMAGE_FORMAT_JPEG: "image/jpeg",
    GENERATED_IMAGE_FORMAT_WEBP: "image/webp",
}
GENERATED_IMAGE_EXTENSION_BY_FORMAT = {
    GENERATED_IMAGE_FORMAT_PNG: ".png",
    GENERATED_IMAGE_FORMAT_JPEG: ".jpg",
    GENERATED_IMAGE_FORMAT_WEBP: ".webp",
}

PROMPT_LENGTH_BUCKETS = (
    "chars_001_to_250",
    "chars_251_to_500",
    "chars_501_to_1000",
    "chars_1001_to_1500",
    "chars_1501_to_2000",
)

DISPLAY_NAME_MAX_CHARS = 160
TARGET_NAME_INTERNAL_MAX_CHARS = 180
GENERATED_IMAGE_STATUS_LABELS = {
    GENERATED_IMAGE_LOCAL_AVAILABLE: "disponible",
    GENERATED_IMAGE_LOCAL_SYNC_ERROR: "erreur de synchronisation",
    GENERATED_IMAGE_LOCAL_CONFLICT: "conflit",
    GENERATED_IMAGE_LOCAL_DELETED: "supprimee",
    GENERATED_IMAGE_LOCAL_UNAVAILABLE: "indisponible",
}

globals().update(workspace_folder_generated_image_reason_codes.REASON_CODE_EXPORTS)
REASON_CODE_CATALOG = workspace_folder_generated_image_reason_codes.REASON_CODE_CATALOG

logger = logging.getLogger("frida.workspace_folder_generated_images")

_HASH12_RE = re.compile(r"^[0-9a-f]{12}$")
_HASH64_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_REASON_RE = re.compile(r"^[a-z0-9_]{3,120}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9:._-]{1,180}$")
_SAFE_TOKEN_RE = re.compile(r"^[A-Za-z0-9:._/+ -]{0,160}$")
_SAFE_TARGET_RE = re.compile(r"^generated-image-[0-9a-f-]{36}\.(png|jpg|webp)$")


def normalize_generated_image_id(value: Any) -> str:
    return uuid_text(value)


def normalize_workspace_folder_id(value: Any) -> str:
    return uuid_text(value)


def normalize_image_format(value: Any) -> str:
    text_value = text(value, 20).lower()
    if text_value in {"jpg", "jpeg"}:
        return GENERATED_IMAGE_FORMAT_JPEG
    if text_value in GENERATED_IMAGE_FORMATS:
        return text_value
    return ""


def normalize_mime_type(value: Any) -> str:
    mime = text(value, 80).lower().split(";", 1)[0].strip()
    return mime if mime in GENERATED_IMAGE_MIME_BY_FORMAT.values() else ""


def expected_mime_type(image_format: Any) -> str:
    return GENERATED_IMAGE_MIME_BY_FORMAT.get(normalize_image_format(image_format), "")


def extension_for_format(image_format: Any) -> str:
    return GENERATED_IMAGE_EXTENSION_BY_FORMAT.get(normalize_image_format(image_format), "")


def target_name_for_image_id(image_id: Any, image_format: Any) -> str:
    normalized = normalize_generated_image_id(image_id)
    extension = extension_for_format(image_format)
    if not normalized or not extension:
        return ""
    return f"generated-image-{normalized}{extension}"


def safe_target_name(value: Any) -> str:
    target = str(value or "").replace("\\", "/").split("/")[-1].strip()
    target = text(target, TARGET_NAME_INTERNAL_MAX_CHARS)
    if not target or not _SAFE_TARGET_RE.fullmatch(target):
        return ""
    return target


def target_ref_for_target(value: Any) -> str:
    target = safe_target_name(value)
    if not target:
        return ""
    return f"generated-image-target:{workspace_folder_nextcloud_projection.hash12(target)}"


def display_name_hash_for_value(value: Any) -> str:
    return workspace_folder_nextcloud_projection.hash12(sanitize_display_name(value).casefold())


def sanitize_display_name(value: Any) -> str:
    name = text(value, DISPLAY_NAME_MAX_CHARS)
    return name


def normalize_prompt_length_bucket(value: Any) -> str:
    bucket = text(value, 32)
    return bucket if bucket in PROMPT_LENGTH_BUCKETS else ""


def prompt_length_bucket_for_length(length: Any) -> str:
    size = safe_int(length)
    if size <= 0:
        return ""
    if size <= 250:
        return "chars_001_to_250"
    if size <= 500:
        return "chars_251_to_500"
    if size <= 1000:
        return "chars_501_to_1000"
    if size <= 1500:
        return "chars_1001_to_1500"
    if size <= 2000:
        return "chars_1501_to_2000"
    return ""


def apply_generated_image_projection(
    image: Mapping[str, Any] | None,
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from . import workspace_folder_generated_image_projection

    return workspace_folder_generated_image_projection.apply_generated_image_projection(
        image,
        folder=folder,
    )


def apply_generated_image_list(
    images: list[Mapping[str, Any]],
    *,
    folder: Mapping[str, Any] | None = None,
    include_deleted: bool = False,
) -> list[dict[str, Any]]:
    from . import workspace_folder_generated_image_projection

    return workspace_folder_generated_image_projection.apply_generated_image_list(
        images,
        folder=folder,
        include_deleted=include_deleted,
    )


def build_user_projection(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from . import workspace_folder_generated_image_projection

    return workspace_folder_generated_image_projection.build_user_projection(
        image,
        folder=folder,
    )


def build_technical_projection(
    image: Mapping[str, Any],
    *,
    folder: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    from . import workspace_folder_generated_image_projection

    return workspace_folder_generated_image_projection.build_technical_projection(
        image,
        folder=folder,
    )


def list_generated_images(
    workspace_folder_id: str,
    *,
    include_deleted: bool = False,
    fail_closed: bool = True,
) -> list[dict[str, Any]]:
    from . import workspace_folder_generated_images_store

    return workspace_folder_generated_images_store.list_generated_images(
        workspace_folder_id,
        include_deleted=include_deleted,
        db_conn_func=db_conn,
        logger=logger,
        fail_closed=fail_closed,
    )


def get_generated_image(
    generated_image_id: str,
    *,
    fail_closed: bool = True,
) -> Optional[dict[str, Any]]:
    from . import workspace_folder_generated_images_store

    return workspace_folder_generated_images_store.get_generated_image(
        generated_image_id,
        db_conn_func=db_conn,
        logger=logger,
        fail_closed=fail_closed,
    )


def upsert_generated_image(**fields: Any) -> dict[str, Any]:
    from . import workspace_folder_generated_images_store

    return workspace_folder_generated_images_store.upsert_generated_image(
        **fields,
        db_conn_func=db_conn,
        logger=logger,
    )


def tombstone_generated_image(
    generated_image_id: str,
    *,
    reason_code: str = REASON_DELETED,
) -> Optional[dict[str, Any]]:
    from . import workspace_folder_generated_images_store

    return workspace_folder_generated_images_store.tombstone_generated_image(
        generated_image_id,
        reason_code=reason_code,
        db_conn_func=db_conn,
        logger=logger,
    )


def log_content_free_event(event: str, level: str = "info", **fields: Any) -> None:
    log_method = getattr(logger, level, logger.info)
    log_method("workspace_folder_generated_image_%s", event, extra={"frida": fields})


def db_conn():
    import config
    import psycopg
    from admin import runtime_settings
    from . import runtime_db_bootstrap

    return runtime_db_bootstrap.connect_runtime_database(psycopg, config, runtime_settings)


def local_state(value: Any) -> str:
    text_value = text(value, 40)
    if text_value in GENERATED_IMAGE_LOCAL_STATES:
        return text_value
    return GENERATED_IMAGE_LOCAL_UNAVAILABLE


def nextcloud_state(value: Any) -> str:
    text_value = text(value, 40)
    if text_value in GENERATED_IMAGE_NEXTCLOUD_STATES:
        return text_value
    return GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR


def sync_label(value: Any) -> str:
    state = nextcloud_state(value)
    return {
        GENERATED_IMAGE_NEXTCLOUD_LINKED: "range Nextcloud",
        GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR: "synchronisation incomplete",
        GENERATED_IMAGE_NEXTCLOUD_CONFLICT: "conflit",
        GENERATED_IMAGE_NEXTCLOUD_DELETED: "supprime",
        GENERATED_IMAGE_NEXTCLOUD_UNAVAILABLE: "indisponible",
    }.get(state, "synchronisation incomplete")


def uuid_text(value: Any) -> str:
    if not value:
        return ""
    try:
        return str(uuid.UUID(str(value)))
    except (TypeError, ValueError):
        return ""


def hash12(value: Any) -> str:
    text_value = text(value, 12).lower()
    return text_value if _HASH12_RE.fullmatch(text_value) else ""


def hash64(value: Any) -> str:
    text_value = text(value, 64).lower()
    return text_value if _HASH64_RE.fullmatch(text_value) else ""


def safe_ref(value: Any) -> str:
    text_value = text(value, 180)
    return text_value if _SAFE_REF_RE.fullmatch(text_value or "") else ""


def safe_token(value: Any, *, max_chars: int = 80) -> str:
    text_value = text(value, max_chars)
    return text_value if _SAFE_TOKEN_RE.fullmatch(text_value) else ""


def safe_model_name(value: Any) -> str:
    return safe_token(value, max_chars=120)


def reason(value: Any, fallback: str) -> str:
    text_value = text(value, 120)
    if text_value in REASON_CODE_CATALOG and _SAFE_REASON_RE.fullmatch(text_value):
        return text_value
    return fallback or REASON_NEXTCLOUD_ERROR_REDACTED


def safe_int(value: Any) -> int:
    try:
        return max(0, int(value or 0))
    except (TypeError, ValueError):
        return 0


def text(value: Any, max_chars: int = 160) -> str:
    text_value = " ".join(str(value or "").strip().split())
    if max_chars > 0 and len(text_value) > max_chars:
        return text_value[:max_chars].rstrip()
    return text_value


def ts_to_iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        dt = value
    else:
        raw = str(value or "").strip()
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return raw
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
