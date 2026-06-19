from __future__ import annotations

from typing import Any, Callable, Mapping, Optional

from . import workspace_folder_generated_images
from . import workspace_folder_generated_images_schema
from . import workspace_folder_nextcloud_projection

try:  # pragma: no cover - local test hosts may stub psycopg.
    from psycopg.rows import dict_row
except Exception:  # pragma: no cover
    dict_row = None


class WorkspaceFolderGeneratedImagePersistenceError(RuntimeError):
    """Raised when Generated Images V1 local read-model persistence fails."""


class WorkspaceFolderGeneratedImageLookupError(RuntimeError):
    """Raised when Generated Images V1 local read-model lookup cannot be trusted."""

    reason_code = workspace_folder_generated_images.REASON_LOOKUP_FAILED

    def __init__(
        self,
        operation: str,
        *,
        generated_image_id: str = "",
        workspace_folder_id: str = "",
    ) -> None:
        super().__init__(self.reason_code)
        self.operation = _safe_lookup_operation(operation)
        self.generated_image_id = workspace_folder_generated_images.normalize_generated_image_id(
            generated_image_id
        )
        self.workspace_folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
            workspace_folder_id
        )


def _cursor(conn: Any):
    if dict_row is None:
        return conn.cursor()
    return conn.cursor(row_factory=dict_row)


def ensure_schema(cur: Any) -> None:
    workspace_folder_generated_images_schema.ensure_schema(cur)


def serialize_generated_image_row(row: Mapping[str, Any] | None) -> Optional[dict[str, Any]]:
    if not row:
        return None
    image_id = workspace_folder_generated_images.normalize_generated_image_id(row.get("id"))
    folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
        row.get("workspace_folder_id")
    )
    if not image_id or not folder_id:
        return None
    display_name = workspace_folder_generated_images.sanitize_display_name(
        row.get("display_name")
    )
    target_name = workspace_folder_generated_images.safe_target_name(
        row.get("target_name_internal")
    )
    target_ref = workspace_folder_generated_images.safe_ref(row.get("target_ref"))
    if target_name and not target_ref:
        target_ref = workspace_folder_generated_images.target_ref_for_target(target_name)
    content_hash = workspace_folder_generated_images.hash64(row.get("content_hash"))
    content_hash_short = workspace_folder_generated_images.hash12(row.get("content_hash_short"))
    if content_hash and not content_hash_short:
        content_hash_short = content_hash[:12]
    etag_value = workspace_folder_generated_images.text(row.get("etag_value"), 512)
    etag_hash = workspace_folder_generated_images.hash12(row.get("etag_hash"))
    if etag_value and not etag_hash:
        etag_hash = workspace_folder_nextcloud_projection.hash12(etag_value)
    image_format = workspace_folder_generated_images.normalize_image_format(
        row.get("image_format")
    )
    return {
        "id": image_id,
        "workspace_folder_id": folder_id,
        "display_name": display_name,
        "display_name_hash": workspace_folder_generated_images.hash12(
            row.get("display_name_hash")
        )
        or workspace_folder_generated_images.display_name_hash_for_value(display_name),
        "target_name_internal": target_name,
        "target_ref": target_ref,
        "mime_type": workspace_folder_generated_images.normalize_mime_type(row.get("mime_type")),
        "image_format": image_format,
        "byte_size": workspace_folder_generated_images.safe_int(row.get("byte_size")),
        "width": workspace_folder_generated_images.safe_int(row.get("width")),
        "height": workspace_folder_generated_images.safe_int(row.get("height")),
        "content_hash": content_hash,
        "content_hash_short": content_hash_short,
        "generator_key": workspace_folder_generated_images.safe_token(
            row.get("generator_key"),
            max_chars=80,
        ),
        "provider_model": workspace_folder_generated_images.safe_model_name(
            row.get("provider_model")
        ),
        "aspect_ratio": workspace_folder_generated_images.safe_token(
            row.get("aspect_ratio"),
            max_chars=40,
        ),
        "image_size": workspace_folder_generated_images.safe_token(
            row.get("image_size"),
            max_chars=40,
        ),
        "prompt_present": bool(row.get("prompt_present")),
        "prompt_length_bucket": workspace_folder_generated_images.normalize_prompt_length_bucket(
            row.get("prompt_length_bucket")
        ),
        "local_state": workspace_folder_generated_images.local_state(row.get("local_state")),
        "nextcloud_sync_state": workspace_folder_generated_images.nextcloud_state(
            row.get("nextcloud_sync_state")
        ),
        "etag_value": etag_value,
        "etag_hash": etag_hash,
        "last_reason_code": workspace_folder_generated_images.reason(
            row.get("last_reason_code"),
            "",
        ),
        "created_at": workspace_folder_generated_images.ts_to_iso(row.get("created_at")),
        "updated_at": workspace_folder_generated_images.ts_to_iso(row.get("updated_at")),
        "deleted_at": workspace_folder_generated_images.ts_to_iso(row.get("deleted_at")),
    }


def list_generated_images(
    workspace_folder_id: str,
    *,
    include_deleted: bool = False,
    db_conn_func: Callable[[], Any],
    logger: Any,
    fail_closed: bool = True,
) -> list[dict[str, Any]]:
    folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
        workspace_folder_id
    )
    if not folder_id:
        return []
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                deleted_sql = "" if include_deleted else "AND deleted_at IS NULL"
                cur.execute(
                    f"""
                    SELECT id, workspace_folder_id, display_name, display_name_hash,
                           target_name_internal, target_ref, mime_type, image_format,
                           byte_size, width, height, content_hash, content_hash_short,
                           generator_key, provider_model, aspect_ratio, image_size,
                           prompt_present, prompt_length_bucket, local_state,
                           nextcloud_sync_state, etag_value, etag_hash,
                           last_reason_code, created_at, updated_at, deleted_at
                    FROM workspace_folder_generated_images
                    WHERE workspace_folder_id = %s::uuid {deleted_sql}
                    ORDER BY updated_at DESC, created_at DESC
                    """,
                    (folder_id,),
                )
                rows = cur.fetchall()
        return [
            image
            for image in (serialize_generated_image_row(row) for row in rows)
            if image
        ]
    except Exception as exc:
        _log_lookup_failure(
            logger,
            "list_failed",
            workspace_folder_id=folder_id,
            error_type=type(exc).__name__,
        )
        if fail_closed:
            raise WorkspaceFolderGeneratedImageLookupError(
                "list",
                workspace_folder_id=folder_id,
            ) from None
        return []


def get_generated_image(
    generated_image_id: str,
    *,
    db_conn_func: Callable[[], Any],
    logger: Any,
    fail_closed: bool = True,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_generated_images.normalize_generated_image_id(
        generated_image_id
    )
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    SELECT id, workspace_folder_id, display_name, display_name_hash,
                           target_name_internal, target_ref, mime_type, image_format,
                           byte_size, width, height, content_hash, content_hash_short,
                           generator_key, provider_model, aspect_ratio, image_size,
                           prompt_present, prompt_length_bucket, local_state,
                           nextcloud_sync_state, etag_value, etag_hash,
                           last_reason_code, created_at, updated_at, deleted_at
                    FROM workspace_folder_generated_images
                    WHERE id = %s::uuid
                    """,
                    (normalized,),
                )
                return serialize_generated_image_row(cur.fetchone())
    except Exception as exc:
        _log_lookup_failure(
            logger,
            "get_failed",
            generated_image_id=normalized,
            error_type=type(exc).__name__,
        )
        if fail_closed:
            raise WorkspaceFolderGeneratedImageLookupError(
                "get",
                generated_image_id=normalized,
            ) from None
        return None


def upsert_generated_image(
    *,
    generated_image_id: str,
    workspace_folder_id: str,
    display_name: str,
    target_name_internal: str,
    mime_type: str,
    image_format: str,
    byte_size: int = 0,
    width: int = 0,
    height: int = 0,
    content_hash: str = "",
    content_hash_short: str = "",
    generator_key: str = "",
    provider_model: str = "",
    aspect_ratio: str = "",
    image_size: str = "",
    prompt_present: bool = False,
    prompt_length_bucket: str = "",
    local_state: str = workspace_folder_generated_images.GENERATED_IMAGE_LOCAL_AVAILABLE,
    nextcloud_sync_state: str = (
        workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR
    ),
    remote_proof: bool = False,
    etag_value: str = "",
    etag_hash: str = "",
    last_reason_code: str = (
        workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED
    ),
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> dict[str, Any]:
    normalized_image_id = workspace_folder_generated_images.normalize_generated_image_id(
        generated_image_id
    )
    folder_id = workspace_folder_generated_images.normalize_workspace_folder_id(
        workspace_folder_id
    )
    fmt = workspace_folder_generated_images.normalize_image_format(image_format)
    mime = workspace_folder_generated_images.normalize_mime_type(mime_type)
    target = workspace_folder_generated_images.safe_target_name(target_name_internal)
    if not normalized_image_id or not folder_id or not fmt or not mime or not target:
        raise WorkspaceFolderGeneratedImagePersistenceError(
            workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED
        )
    if not target.endswith(workspace_folder_generated_images.extension_for_format(fmt)):
        raise WorkspaceFolderGeneratedImagePersistenceError(
            workspace_folder_generated_images.REASON_NAME_INVALID
        )
    if mime != workspace_folder_generated_images.expected_mime_type(fmt):
        raise WorkspaceFolderGeneratedImagePersistenceError(
            workspace_folder_generated_images.REASON_MIME_INVALID
        )
    target_ref = workspace_folder_generated_images.target_ref_for_target(target)
    if not target_ref:
        raise WorkspaceFolderGeneratedImagePersistenceError(
            workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED
        )
    sync_state = _nextcloud_state_for_persistence(nextcloud_sync_state, remote_proof=remote_proof)
    reason_code = _reason_for_persistence(last_reason_code, sync_state)
    display = workspace_folder_generated_images.sanitize_display_name(display_name)
    display_hash = workspace_folder_generated_images.display_name_hash_for_value(display)
    content_hash_value = workspace_folder_generated_images.hash64(content_hash)
    content_hash_short_value = workspace_folder_generated_images.hash12(content_hash_short)
    if content_hash_value and not content_hash_short_value:
        content_hash_short_value = content_hash_value[:12]
    etag_raw = workspace_folder_generated_images.text(etag_value, 512)
    etag_hash_value = workspace_folder_generated_images.hash12(etag_hash)
    if etag_raw and not etag_hash_value:
        etag_hash_value = workspace_folder_nextcloud_projection.hash12(etag_raw)
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    INSERT INTO workspace_folder_generated_images (
                        id, workspace_folder_id, display_name, display_name_hash,
                        target_name_internal, target_ref, mime_type, image_format,
                        byte_size, width, height, content_hash, content_hash_short,
                        generator_key, provider_model, aspect_ratio, image_size,
                        prompt_present, prompt_length_bucket, local_state,
                        nextcloud_sync_state, etag_value, etag_hash,
                        last_reason_code, created_at, updated_at, deleted_at
                    )
                    VALUES (
                        %s::uuid, %s::uuid, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s,
                        %s, %s, %s,
                        %s, now(), now(), NULL
                    )
                    ON CONFLICT (id) DO UPDATE SET
                        workspace_folder_id = EXCLUDED.workspace_folder_id,
                        display_name = EXCLUDED.display_name,
                        display_name_hash = EXCLUDED.display_name_hash,
                        target_name_internal = EXCLUDED.target_name_internal,
                        target_ref = EXCLUDED.target_ref,
                        mime_type = EXCLUDED.mime_type,
                        image_format = EXCLUDED.image_format,
                        byte_size = EXCLUDED.byte_size,
                        width = EXCLUDED.width,
                        height = EXCLUDED.height,
                        content_hash = EXCLUDED.content_hash,
                        content_hash_short = EXCLUDED.content_hash_short,
                        generator_key = EXCLUDED.generator_key,
                        provider_model = EXCLUDED.provider_model,
                        aspect_ratio = EXCLUDED.aspect_ratio,
                        image_size = EXCLUDED.image_size,
                        prompt_present = EXCLUDED.prompt_present,
                        prompt_length_bucket = EXCLUDED.prompt_length_bucket,
                        local_state = EXCLUDED.local_state,
                        nextcloud_sync_state = EXCLUDED.nextcloud_sync_state,
                        etag_value = EXCLUDED.etag_value,
                        etag_hash = EXCLUDED.etag_hash,
                        last_reason_code = EXCLUDED.last_reason_code,
                        updated_at = now(),
                        deleted_at = NULL
                    RETURNING id, workspace_folder_id, display_name, display_name_hash,
                              target_name_internal, target_ref, mime_type, image_format,
                              byte_size, width, height, content_hash, content_hash_short,
                              generator_key, provider_model, aspect_ratio, image_size,
                              prompt_present, prompt_length_bucket, local_state,
                              nextcloud_sync_state, etag_value, etag_hash,
                              last_reason_code, created_at, updated_at, deleted_at
                    """,
                    (
                        normalized_image_id,
                        folder_id,
                        display,
                        display_hash,
                        target,
                        target_ref,
                        mime,
                        fmt,
                        workspace_folder_generated_images.safe_int(byte_size),
                        workspace_folder_generated_images.safe_int(width),
                        workspace_folder_generated_images.safe_int(height),
                        content_hash_value,
                        content_hash_short_value,
                        workspace_folder_generated_images.safe_token(
                            generator_key,
                            max_chars=80,
                        ),
                        workspace_folder_generated_images.safe_model_name(provider_model),
                        workspace_folder_generated_images.safe_token(
                            aspect_ratio,
                            max_chars=40,
                        ),
                        workspace_folder_generated_images.safe_token(
                            image_size,
                            max_chars=40,
                        ),
                        bool(prompt_present),
                        workspace_folder_generated_images.normalize_prompt_length_bucket(
                            prompt_length_bucket
                        ),
                        workspace_folder_generated_images.local_state(local_state),
                        sync_state,
                        etag_raw,
                        etag_hash_value,
                        reason_code,
                    ),
                )
                row = serialize_generated_image_row(cur.fetchone())
            conn.commit()
        if not row:
            raise WorkspaceFolderGeneratedImagePersistenceError(
                workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED
            )
        return row
    except WorkspaceFolderGeneratedImagePersistenceError:
        raise
    except Exception as exc:
        _log(
            logger,
            "upsert_failed",
            generated_image_id=normalized_image_id,
            error_type=type(exc).__name__,
        )
        raise WorkspaceFolderGeneratedImagePersistenceError(
            workspace_folder_generated_images.REASON_LOCAL_PERSISTENCE_FAILED
        ) from None


def tombstone_generated_image(
    generated_image_id: str,
    *,
    reason_code: str = workspace_folder_generated_images.REASON_DELETED,
    db_conn_func: Callable[[], Any],
    logger: Any,
) -> Optional[dict[str, Any]]:
    normalized = workspace_folder_generated_images.normalize_generated_image_id(
        generated_image_id
    )
    if not normalized:
        return None
    try:
        with db_conn_func() as conn:
            with _cursor(conn) as cur:
                cur.execute(
                    """
                    UPDATE workspace_folder_generated_images
                    SET local_state = 'deleted',
                        nextcloud_sync_state = 'deleted',
                        last_reason_code = %s,
                        updated_at = now(),
                        deleted_at = COALESCE(deleted_at, now())
                    WHERE id = %s::uuid
                    RETURNING id, workspace_folder_id, display_name, display_name_hash,
                              target_name_internal, target_ref, mime_type, image_format,
                              byte_size, width, height, content_hash, content_hash_short,
                              generator_key, provider_model, aspect_ratio, image_size,
                              prompt_present, prompt_length_bucket, local_state,
                              nextcloud_sync_state, etag_value, etag_hash,
                              last_reason_code, created_at, updated_at, deleted_at
                    """,
                    (
                        workspace_folder_generated_images.reason(
                            reason_code,
                            workspace_folder_generated_images.REASON_DELETED,
                        ),
                        normalized,
                    ),
                )
                row = serialize_generated_image_row(cur.fetchone())
            conn.commit()
        return row
    except Exception as exc:
        _log(
            logger,
            "tombstone_failed",
            generated_image_id=normalized,
            error_type=type(exc).__name__,
        )
        return None


def _nextcloud_state_for_persistence(value: Any, *, remote_proof: bool) -> str:
    state = workspace_folder_generated_images.nextcloud_state(value)
    if state == workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED:
        return state if remote_proof else (
            workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_SYNC_ERROR
        )
    return state


def _reason_for_persistence(value: Any, sync_state: str) -> str:
    fallback = (
        workspace_folder_generated_images.REASON_STORE_OK
        if sync_state == workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED
        else workspace_folder_generated_images.REASON_NEXTCLOUD_ERROR_REDACTED
    )
    if (
        sync_state != workspace_folder_generated_images.GENERATED_IMAGE_NEXTCLOUD_LINKED
        and value == workspace_folder_generated_images.REASON_STORE_OK
    ):
        return fallback
    return workspace_folder_generated_images.reason(value, fallback)


def _safe_lookup_operation(value: Any) -> str:
    text_value = workspace_folder_generated_images.text(value, 24)
    return text_value if text_value in {"list", "get"} else "lookup"


def _log_lookup_failure(
    logger: Any,
    event: str,
    *,
    workspace_folder_id: str = "",
    generated_image_id: str = "",
    error_type: str = "",
) -> None:
    _log(
        logger,
        event,
        reason_code=workspace_folder_generated_images.REASON_LOOKUP_FAILED,
        workspace_folder_id=workspace_folder_generated_images.normalize_workspace_folder_id(
            workspace_folder_id
        ),
        generated_image_id=workspace_folder_generated_images.normalize_generated_image_id(
            generated_image_id
        ),
        error_type=workspace_folder_generated_images.text(error_type, 80),
    )


def _log(logger: Any, event: str, **fields: Any) -> None:
    if logger is None:
        return
    logger.warning("workspace_folder_generated_image_%s", event, extra={"frida": fields})
