from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

from . import workspace_folder_generated_image_nextcloud_client as image_client
from . import workspace_folder_generated_image_provider
from . import workspace_folder_generated_image_validation
from . import workspace_folder_generated_images
from . import workspace_folder_nextcloud_links_store as nextcloud_links
from . import workspace_folder_nextcloud_projection as folder_projection


_CLIENT_IMAGE_ID_KEYS = frozenset({"image_id", "generated_image_id"})


def store_workspace_folder_generated_image_nextcloud_first(
    *,
    folder: Mapping[str, Any],
    request: Mapping[str, Any],
    images_module: Any = workspace_folder_generated_images,
    provider_module: Any = workspace_folder_generated_image_provider,
    validation_module: Any = workspace_folder_generated_image_validation,
    nextcloud: Any | None = None,
) -> dict[str, Any]:
    folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(folder.get("id"))
    if not folder_id:
        return _failure(
            workspace_folder_generated_images.REASON_FOLDER_INVALID,
            status=400,
            store_state="blocked",
        )
    if folder.get("deleted_at"):
        return _failure(
            workspace_folder_generated_images.REASON_FOLDER_DELETED,
            status=410,
            store_state="blocked",
        )
    if str(folder.get("nextcloud_sync_state") or "") != nextcloud_links.NEXTCLOUD_SYNC_LINKED:
        return _failure(
            workspace_folder_generated_images.REASON_FOLDER_NOT_LINKED,
            status=409,
            store_state="blocked",
        )

    payload = dict(request or {})
    if "workspace_folder_id" in payload:
        return _failure(
            workspace_folder_generated_images.REASON_CLIENT_WORKSPACE_FOLDER_ID_FORBIDDEN,
            status=400,
            store_state="blocked",
        )
    if any(key in payload for key in _CLIENT_IMAGE_ID_KEYS):
        return _failure(
            workspace_folder_generated_images.REASON_CLIENT_IMAGE_ID_FORBIDDEN,
            status=400,
            store_state="blocked",
        )

    target_folder_name = _target_folder_name(folder)
    if not target_folder_name:
        return _failure(
            workspace_folder_generated_images.REASON_IMAGES_TARGET_UNAVAILABLE,
            status=502,
            store_state="blocked",
        )

    provider_result = provider_module.generate_generated_image_data_url(payload)
    if not provider_result.ok:
        reason_code = _safe_reason(provider_result.reason_code)
        return _failure(
            reason_code,
            status=_http_status_for_reason(reason_code, fallback=provider_result.status),
            store_state="provider_failed",
            provider={
                "reason_code": reason_code,
                "generator_key": _safe_token(provider_result.generator_key, max_chars=80),
                "provider_model": _safe_token(provider_result.provider_model, max_chars=120),
                "aspect_ratio": _safe_token(provider_result.aspect_ratio, max_chars=40),
                "image_size": _safe_token(provider_result.image_size, max_chars=40),
                "data_url_chars": _safe_int(provider_result.data_url_chars),
            },
        )

    validation = validation_module.validate_generated_image_data_url(provider_result.data_url)
    if not validation.ok:
        reason_code = _safe_reason(validation.reason_code)
        return _failure(
            reason_code,
            status=_http_status_for_reason(reason_code),
            store_state="validation_failed",
            provider=_provider_technical(provider_result),
        )

    image_id = str(uuid.uuid4())
    target_name = workspace_folder_generated_images.target_name_for_image_id(
        image_id,
        validation.image_format,
    )
    target_ref = workspace_folder_generated_images.target_ref_for_target(target_name)
    if not target_name or not target_ref:
        return _failure(
            workspace_folder_generated_images.REASON_NAME_INVALID,
            status=400,
            store_state="blocked",
            target_ref=target_ref,
            provider=_provider_technical(provider_result),
        )

    try:
        client = _client(nextcloud)
        client.images_status(target_folder_name)
        put_result = client.put_image(
            target_folder_name,
            target_name,
            validation.image_bytes,
            media_type=validation.mime_type,
        )
    except image_client.NextcloudGeneratedImageClientError as exc:
        return _failure(
            exc.reason_code,
            status=_http_status_for_reason(exc.reason_code),
            store_state="nextcloud_failed",
            http_status_class=exc.status_class,
            target_ref=target_ref,
            provider=_provider_technical(provider_result),
            validation=_validation_technical(validation),
        )

    display_name = _display_name(payload)
    try:
        stored = images_module.upsert_generated_image(
            generated_image_id=image_id,
            workspace_folder_id=folder_id,
            display_name=display_name,
            target_name_internal=target_name,
            mime_type=validation.mime_type,
            image_format=validation.image_format,
            byte_size=validation.byte_size,
            width=validation.width,
            height=validation.height,
            content_hash=validation.content_hash,
            content_hash_short=validation.content_hash_short,
            generator_key=provider_result.generator_key,
            provider_model=provider_result.provider_model,
            aspect_ratio=provider_result.aspect_ratio,
            image_size=provider_result.image_size,
            prompt_present=provider_result.prompt_length > 0,
            prompt_length_bucket=workspace_folder_generated_images.prompt_length_bucket_for_length(
                provider_result.prompt_length
            ),
            local_state=workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_AVAILABLE,
            nextcloud_sync_state=workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED,
            remote_proof=True,
            etag_value=put_result.etag_value,
            etag_hash=hash12(put_result.etag_value),
            last_reason_code=workspace_folder_generated_images.REASON_STORE_OK,
        )
    except Exception:
        rollback = _rollback_remote_created_image(
            client,
            target_folder_name=target_folder_name,
            target_name=target_name,
            etag_value=put_result.etag_value,
            images_module=images_module,
            folder_id=folder_id,
        )
        return _failure(
            workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED,
            status=503,
            store_state="local_persistence_failed",
            target_ref=target_ref,
            rollback=rollback,
            provider=_provider_technical(provider_result),
            validation=_validation_technical(validation),
        )

    _log_event(
        images_module,
        "generated_images_v1_store_ok",
        folder_id=folder_id,
        image_id=stored.get("id"),
        reason_code=workspace_folder_generated_images.REASON_STORE_OK,
        target_ref=target_ref,
        http_status_class=put_result.status_class,
    )
    return {
        "ok": True,
        "generated_image": stored,
        "reason_code": workspace_folder_generated_images.REASON_STORE_OK,
        "status": 201,
        "generated_image_nextcloud": _technical_nextcloud_payload(
            target_ref=target_ref,
            reason_code=workspace_folder_generated_images.REASON_STORE_OK,
            http_status_class=put_result.status_class,
            store_state="stored",
            etag_hash=hash12(put_result.etag_value),
            provider=_provider_technical(provider_result),
            validation=_validation_technical(validation),
        ),
    }


def runtime_secret_status() -> dict[str, Any]:
    return {
        "nextcloud": image_client.secret_status_from_env(),
        "provider": workspace_folder_generated_image_provider.runtime_secret_status(),
    }


def hash12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12] if value else ""


def _target_folder_name(folder: Mapping[str, Any]) -> str:
    target = str(folder.get("nextcloud_target_name") or "").strip()
    if target:
        return target
    return folder_projection.sanitize_nextcloud_folder_name(folder.get("display_name"))


def _client(nextcloud: Any | None) -> Any:
    if nextcloud is not None:
        return nextcloud
    return image_client.NextcloudGeneratedImageClient.from_env()


def _display_name(payload: Mapping[str, Any]) -> str:
    raw = payload.get("display_name")
    if raw is None:
        raw = payload.get("title")
    display = workspace_folder_generated_images.sanitize_display_name(raw)
    if display:
        return display
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"Image generee {now}"


def _rollback_remote_created_image(
    client: Any,
    *,
    target_folder_name: str,
    target_name: str,
    etag_value: str,
    images_module: Any,
    folder_id: str,
) -> dict[str, Any]:
    target_ref = workspace_folder_generated_images.target_ref_for_target(target_name)
    if not str(etag_value or "").strip():
        reason_code = workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED
        http_status_class = "none"
        ok = False
    else:
        try:
            result = client.delete_created_image_if_match(
                target_folder_name,
                target_name,
                etag_value=etag_value,
            )
            reason_code = result.reason_code
            http_status_class = result.status_class
            ok = reason_code in {
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK,
                workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_MISSING,
            }
        except image_client.NextcloudGeneratedImageClientError as exc:
            reason_code = (
                exc.reason_code
                if exc.reason_code
                in {
                    workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED,
                    workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED,
                    workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED,
                }
                else workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_FAILED
            )
            http_status_class = exc.status_class
            ok = False
    _log_event(
        images_module,
        "generated_images_v1_store_compensation",
        level="warning",
        folder_id=folder_id,
        reason_code=reason_code,
        target_ref=target_ref,
        http_status_class=http_status_class,
    )
    return {
        "ok": ok,
        "reason_code": _safe_reason(reason_code),
        "http_status_class": http_status_class,
        "target_ref": target_ref,
        "state": _remote_compensation_state(reason_code),
    }


def _remote_compensation_state(reason_code: str) -> str:
    return {
        workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OK: "deleted",
        workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_MISSING: "missing",
        workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_PRECONDITION_FAILED: "precondition_failed",
        workspace_folder_generated_images.REASON_REMOTE_COMPENSATION_OWNERSHIP_UNVERIFIED: "ownership_unverified",
    }.get(reason_code, "failed")


def _failure(
    reason_code: str,
    *,
    status: int,
    store_state: str,
    http_status_class: str = "none",
    target_ref: str = "",
    rollback: Mapping[str, Any] | None = None,
    provider: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    safe_reason = _safe_reason(reason_code)
    return {
        "ok": False,
        "reason_code": safe_reason,
        "status": int(status or 500),
        "generated_image": {
            "status": _image_status_for_failure(safe_reason),
            "reason_code": safe_reason,
        },
        "generated_image_v1_technical": {
            "reason_code": safe_reason,
            "provider": dict(provider or {}),
            "validation": dict(validation or {}),
        },
        "generated_image_nextcloud": {
            "store_state": store_state,
            "reason_code": safe_reason,
            "target_ref": workspace_folder_generated_images.safe_target_ref(target_ref),
            "http_status_class": http_status_class,
            "rollback": dict(rollback or {}),
        },
    }


def _technical_nextcloud_payload(
    *,
    target_ref: str,
    reason_code: str,
    http_status_class: str,
    store_state: str,
    etag_hash: str = "",
    provider: Mapping[str, Any] | None = None,
    validation: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "store_state": store_state,
        "reason_code": _safe_reason(reason_code),
        "target_ref": workspace_folder_generated_images.safe_target_ref(target_ref),
        "http_status_class": http_status_class,
        "provider": dict(provider or {}),
        "validation": dict(validation or {}),
    }
    if etag_hash:
        payload["etag_hash"] = etag_hash
        payload["etag_present"] = True
    else:
        payload["etag_present"] = False
    return payload


def _provider_technical(result: Any) -> dict[str, Any]:
    return {
        "generator_key": _safe_token(getattr(result, "generator_key", ""), max_chars=80),
        "provider_model": _safe_token(getattr(result, "provider_model", ""), max_chars=120),
        "aspect_ratio": _safe_token(getattr(result, "aspect_ratio", ""), max_chars=40),
        "image_size": _safe_token(getattr(result, "image_size", ""), max_chars=40),
        "prompt_present": _safe_int(getattr(result, "prompt_length", 0)) > 0,
        "prompt_length_bucket": workspace_folder_generated_images.prompt_length_bucket_for_length(
            getattr(result, "prompt_length", 0)
        ),
        "data_url_chars": _safe_int(getattr(result, "data_url_chars", 0)),
    }


def _validation_technical(result: Any) -> dict[str, Any]:
    return {
        "mime_type": workspace_folder_generated_images.normalize_mime_type(
            getattr(result, "mime_type", "")
        ),
        "format": workspace_folder_generated_images.normalize_image_format(
            getattr(result, "image_format", "")
        ),
        "content_hash_short": workspace_folder_generated_images.hash12(
            getattr(result, "content_hash_short", "")
        ),
        "counters": {
            "byte_size": _safe_int(getattr(result, "byte_size", 0)),
            "width": _safe_int(getattr(result, "width", 0)),
            "height": _safe_int(getattr(result, "height", 0)),
        },
    }


def _image_status_for_failure(reason_code: str) -> str:
    if reason_code == workspace_folder_generated_images.REASON_NAME_CONFLICT:
        return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_CONFLICT
    if reason_code == workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED:
        return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_SYNC_ERROR
    return workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_UNAVAILABLE


def _http_status_for_reason(reason_code: str, *, fallback: int = 502) -> int:
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
    if reason_code == workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED:
        return 503
    return int(fallback or 502)


def _safe_reason(value: Any) -> str:
    return workspace_folder_generated_images.reason(
        value,
        workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED,
    )


def _safe_token(value: Any, *, max_chars: int) -> str:
    return workspace_folder_generated_images.safe_token(value, max_chars=max_chars)


def _safe_int(value: Any) -> int:
    return workspace_folder_generated_images.safe_int(value)


def _log_event(images_module: Any, event: str, level: str = "info", **fields: Any) -> None:
    log_func = getattr(images_module, "log_content_free_event", None)
    if callable(log_func):
        log_func(event, level=level, **fields)
