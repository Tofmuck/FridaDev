from __future__ import annotations

"""Generated Images V1 in-memory image validation.

The validator accepts the provider data URL only as a transient transport shape.
It returns bytes for the immediate Nextcloud PUT, never for durable storage or
technical projection.
"""

import base64
import binascii
import hashlib
import re
from dataclasses import dataclass
from typing import Any

from . import active_document_image_validation
from . import workspace_folder_generated_images


V1_IMAGE_DATA_URL_MAX_CHARS = 22_000_000
V1_IMAGE_MAX_BYTES = 15 * 1024 * 1024
V1_IMAGE_MIN_WIDTH = 32
V1_IMAGE_MIN_HEIGHT = 32
V1_IMAGE_MAX_SIDE = 16_000
V1_IMAGE_MAX_PIXELS = 100_000_000

_DATA_URL_RE = re.compile(r"^data:([^;,]+);base64,(.*)$", re.DOTALL)
_FORMAT_BY_MIME = {
    "image/png": workspace_folder_generated_images.GENERATED_IMAGE_FORMAT_PNG,
    "image/jpeg": workspace_folder_generated_images.GENERATED_IMAGE_FORMAT_JPEG,
    "image/webp": workspace_folder_generated_images.GENERATED_IMAGE_FORMAT_WEBP,
}


@dataclass(frozen=True)
class GeneratedImageValidationResult:
    ok: bool
    reason_code: str
    image_bytes: bytes = b""
    mime_type: str = ""
    image_format: str = ""
    byte_size: int = 0
    width: int = 0
    height: int = 0
    content_hash: str = ""
    content_hash_short: str = ""


def validate_generated_image_data_url(data_url: Any) -> GeneratedImageValidationResult:
    text = str(data_url or "").strip()
    if not text:
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_INVALID)
    if len(text) > V1_IMAGE_DATA_URL_MAX_CHARS:
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_TOO_LARGE)

    match = _DATA_URL_RE.fullmatch(text)
    if not match:
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_INVALID)

    declared_mime = str(match.group(1) or "").strip().lower()
    normalized_mime = workspace_folder_generated_images.normalize_mime_type(declared_mime)
    if not normalized_mime:
        if declared_mime.startswith("image/"):
            return _failure(workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED)
        return _failure(workspace_folder_generated_images.REASON_MIME_INVALID)

    try:
        image_bytes = base64.b64decode(match.group(2), validate=True)
    except (binascii.Error, ValueError):
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_INVALID)

    if not image_bytes:
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_INVALID)
    sniff = active_document_image_validation.sniff_image(image_bytes)
    if sniff is None:
        return _failure(workspace_folder_generated_images.REASON_MIME_INVALID)
    if sniff.media_type != normalized_mime:
        return _failure(workspace_folder_generated_images.REASON_MIME_INVALID)
    return _validate_image_bytes(image_bytes, sniff=sniff)


def validate_generated_image_bytes(
    image_bytes: bytes,
    *,
    expected_mime_type: Any = "",
) -> GeneratedImageValidationResult:
    content = bytes(image_bytes or b"")
    sniff = active_document_image_validation.sniff_image(content)
    if sniff is None:
        return _failure(workspace_folder_generated_images.REASON_MIME_INVALID)
    expected = workspace_folder_generated_images.normalize_mime_type(expected_mime_type)
    if expected and sniff.media_type != expected:
        return _failure(workspace_folder_generated_images.REASON_MIME_INVALID)
    return _validate_image_bytes(content, sniff=sniff)


def _validate_image_bytes(image_bytes: bytes, *, sniff: Any) -> GeneratedImageValidationResult:
    if not image_bytes:
        return _failure(workspace_folder_generated_images.REASON_DATA_URL_INVALID)
    if len(image_bytes) > V1_IMAGE_MAX_BYTES:
        return _failure(workspace_folder_generated_images.REASON_TOO_LARGE)
    if sniff.media_type not in _FORMAT_BY_MIME:
        return _failure(workspace_folder_generated_images.REASON_FORMAT_UNSUPPORTED)
    if (
        sniff.width < V1_IMAGE_MIN_WIDTH
        or sniff.height < V1_IMAGE_MIN_HEIGHT
        or sniff.width > V1_IMAGE_MAX_SIDE
        or sniff.height > V1_IMAGE_MAX_SIDE
        or sniff.width * sniff.height > V1_IMAGE_MAX_PIXELS
    ):
        return _failure(workspace_folder_generated_images.REASON_DIMENSIONS_INVALID)

    content_hash = hashlib.sha256(image_bytes).hexdigest()
    return GeneratedImageValidationResult(
        True,
        workspace_folder_generated_images.REASON_CREATE_OK,
        image_bytes=image_bytes,
        mime_type=sniff.media_type,
        image_format=_FORMAT_BY_MIME[sniff.media_type],
        byte_size=len(image_bytes),
        width=sniff.width,
        height=sniff.height,
        content_hash=content_hash,
        content_hash_short=content_hash[:12],
    )


def _failure(reason_code: str) -> GeneratedImageValidationResult:
    return GeneratedImageValidationResult(False, reason_code)
