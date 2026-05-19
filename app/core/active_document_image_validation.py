from __future__ import annotations

"""Image upload validation for active conversation documents.

Lot 1 accepts images as conversation-scoped active document state only. It does
not decide provider injection; that remains the responsibility of the future
multimodal prompt lane.
"""

import hashlib
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any


STATUS_COMPLETE = "complete"
STATUS_NOT_IMAGE = "not_image"
STATUS_UNSUPPORTED = "unsupported"
STATUS_TOO_LARGE = "too_large"
STATUS_TOO_SMALL = "too_small"
STATUS_DIMENSIONS_UNSUPPORTED = "dimensions_unsupported"
STATUS_PARSE_ERROR = "parse_error"

REASON_EMPTY_FILE = "image_empty_file"
REASON_TYPE_UNSUPPORTED = "image_type_unsupported"
REASON_GIF_UNSUPPORTED_V0 = "image_gif_unsupported_v0"
REASON_EXTENSION_MISMATCH = "image_extension_mismatch"
REASON_MIME_MISMATCH = "image_mime_mismatch"
REASON_PARSE_ERROR = "image_parse_error"
REASON_TOO_LARGE = "image_too_large"
REASON_TOO_SMALL_FOR_PROVIDER = "image_too_small_for_provider"
REASON_DIMENSIONS_UNSUPPORTED = "image_dimensions_unsupported"

ACTIVE_IMAGE_SOURCE_MAX_BYTES = 32 * 1024 * 1024
ACTIVE_IMAGE_MIN_WIDTH = 32
ACTIVE_IMAGE_MIN_HEIGHT = 32
ACTIVE_IMAGE_MAX_WIDTH = 16_000
ACTIVE_IMAGE_MAX_HEIGHT = 16_000
ACTIVE_IMAGE_MAX_PIXELS = 100_000_000

V0_IMAGE_MIME_BY_EXTENSION = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}
V0_IMAGE_MIME_TYPES = tuple(sorted(set(V0_IMAGE_MIME_BY_EXTENSION.values())))
OPENROUTER_IMAGE_MIME_TYPES = (*V0_IMAGE_MIME_TYPES, "image/gif")
_GENERIC_DECLARED_MIME_TYPES = {"", "application/octet-stream", "binary/octet-stream"}
_KNOWN_IMAGE_EXTENSIONS = (*V0_IMAGE_MIME_BY_EXTENSION.keys(), ".gif")


@dataclass(frozen=True)
class ImageSniff:
    media_type: str
    width: int
    height: int
    parser: str


@dataclass(frozen=True)
class ActiveImageUploadValidation:
    status: str
    reason_code: str
    is_image_candidate: bool
    filename: str
    media_type: str
    source_extension: str
    byte_size: int
    image_width: int = 0
    image_height: int = 0
    content_sha256_12: str = ""
    parser: str = "image-sniff"

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "media_type": self.media_type,
            "source_extension": self.source_extension,
            "byte_size": self.byte_size,
            "bytes": self.byte_size,
            "status": self.status,
            "reason_code": self.reason_code,
            "media_kind": "image",
            "image_width": self.image_width,
            "image_height": self.image_height,
            "content_sha256_12": self.content_sha256_12,
            "parser": self.parser,
        }


def validate_active_image_upload(
    content: bytes,
    *,
    filename: str,
    declared_media_type: str = "",
) -> ActiveImageUploadValidation:
    """Validate a potential active image upload without returning raw bytes."""

    data = bytes(content or b"")
    safe_filename = str(filename or "image").strip() or "image"
    declared = _normalize_media_type(declared_media_type)
    extension = _normalize_extension(safe_filename)
    sniff = sniff_image(data)
    candidate = _is_image_candidate(extension, declared, sniff)
    base = {
        "filename": safe_filename,
        "media_type": declared,
        "source_extension": extension,
        "byte_size": len(data),
        "content_sha256_12": _sha256_12(data),
    }
    if not candidate:
        return ActiveImageUploadValidation(
            status=STATUS_NOT_IMAGE,
            reason_code="",
            is_image_candidate=False,
            **base,
        )
    if not data:
        return _failure(STATUS_PARSE_ERROR, REASON_EMPTY_FILE, **base)
    if len(data) > ACTIVE_IMAGE_SOURCE_MAX_BYTES:
        return _failure(STATUS_TOO_LARGE, REASON_TOO_LARGE, **base)
    if extension == ".gif" or declared == "image/gif" or (sniff and sniff.media_type == "image/gif"):
        return _failure(
            STATUS_UNSUPPORTED,
            REASON_GIF_UNSUPPORTED_V0,
            sniff=sniff,
            media_type=declared or "image/gif",
            **{key: value for key, value in base.items() if key != "media_type"},
        )
    if extension not in V0_IMAGE_MIME_BY_EXTENSION:
        return _failure(STATUS_UNSUPPORTED, REASON_TYPE_UNSUPPORTED, **base)
    if sniff is None:
        return _failure(STATUS_PARSE_ERROR, REASON_PARSE_ERROR, **base)
    if sniff.media_type not in V0_IMAGE_MIME_TYPES:
        return _failure(STATUS_UNSUPPORTED, REASON_TYPE_UNSUPPORTED, sniff=sniff, **base)
    expected_media_type = V0_IMAGE_MIME_BY_EXTENSION[extension]
    if sniff.media_type != expected_media_type:
        return _failure(STATUS_UNSUPPORTED, REASON_EXTENSION_MISMATCH, sniff=sniff, **base)
    if declared not in _GENERIC_DECLARED_MIME_TYPES and declared != sniff.media_type:
        return _failure(STATUS_UNSUPPORTED, REASON_MIME_MISMATCH, sniff=sniff, **base)
    if sniff.width < ACTIVE_IMAGE_MIN_WIDTH or sniff.height < ACTIVE_IMAGE_MIN_HEIGHT:
        return _failure(STATUS_TOO_SMALL, REASON_TOO_SMALL_FOR_PROVIDER, sniff=sniff, **base)
    if (
        sniff.width > ACTIVE_IMAGE_MAX_WIDTH
        or sniff.height > ACTIVE_IMAGE_MAX_HEIGHT
        or sniff.width * sniff.height > ACTIVE_IMAGE_MAX_PIXELS
    ):
        return _failure(STATUS_DIMENSIONS_UNSUPPORTED, REASON_DIMENSIONS_UNSUPPORTED, sniff=sniff, **base)
    return ActiveImageUploadValidation(
        status=STATUS_COMPLETE,
        reason_code="",
        is_image_candidate=True,
        image_width=sniff.width,
        image_height=sniff.height,
        parser=sniff.parser,
        media_type=sniff.media_type,
        **{key: value for key, value in base.items() if key != "media_type"},
    )


def sniff_image(data: bytes) -> ImageSniff | None:
    if not data:
        return None
    return _sniff_png(data) or _sniff_jpeg(data) or _sniff_webp(data) or _sniff_gif(data)


def _failure(
    status: str,
    reason_code: str,
    *,
    sniff: ImageSniff | None = None,
    **kwargs: Any,
) -> ActiveImageUploadValidation:
    media_type = kwargs.get("media_type")
    return ActiveImageUploadValidation(
        status=status,
        reason_code=reason_code,
        is_image_candidate=True,
        filename=str(kwargs.get("filename") or "image"),
        media_type=str((sniff.media_type if sniff else media_type) or ""),
        source_extension=str(kwargs.get("source_extension") or ""),
        byte_size=int(kwargs.get("byte_size") or 0),
        image_width=int(sniff.width if sniff else 0),
        image_height=int(sniff.height if sniff else 0),
        content_sha256_12=str(kwargs.get("content_sha256_12") or ""),
        parser=str(sniff.parser if sniff else "image-sniff"),
    )


def _is_image_candidate(extension: str, declared_media_type: str, sniff: ImageSniff | None) -> bool:
    return (
        extension in _KNOWN_IMAGE_EXTENSIONS
        or declared_media_type.startswith("image/")
        or sniff is not None
    )


def _normalize_media_type(value: str) -> str:
    return str(value or "").split(";", 1)[0].strip().lower()


def _normalize_extension(filename: str) -> str:
    return Path(str(filename or "")).suffix.strip().lower()


def _sha256_12(data: bytes) -> str:
    if not data:
        return ""
    return hashlib.sha256(data).hexdigest()[:12]


def _sniff_png(data: bytes) -> ImageSniff | None:
    if len(data) < 24 or not data.startswith(b"\x89PNG\r\n\x1a\n") or data[12:16] != b"IHDR":
        return None
    width = int.from_bytes(data[16:20], "big")
    height = int.from_bytes(data[20:24], "big")
    if width <= 0 or height <= 0:
        return None
    return ImageSniff("image/png", width, height, "png")


def _sniff_gif(data: bytes) -> ImageSniff | None:
    if len(data) < 10 or data[:6] not in (b"GIF87a", b"GIF89a"):
        return None
    width = int.from_bytes(data[6:8], "little")
    height = int.from_bytes(data[8:10], "little")
    if width <= 0 or height <= 0:
        return None
    return ImageSniff("image/gif", width, height, "gif")


def _sniff_webp(data: bytes) -> ImageSniff | None:
    if len(data) < 30 or data[:4] != b"RIFF" or data[8:12] != b"WEBP":
        return None
    chunk = data[12:16]
    if chunk == b"VP8X":
        width = _read_uint24_le(data[24:27]) + 1
        height = _read_uint24_le(data[27:30]) + 1
        return ImageSniff("image/webp", width, height, "webp-vp8x")
    if chunk == b"VP8L" and len(data) >= 25 and data[20] == 0x2F:
        bits = int.from_bytes(data[21:25], "little")
        width = (bits & 0x3FFF) + 1
        height = ((bits >> 14) & 0x3FFF) + 1
        return ImageSniff("image/webp", width, height, "webp-vp8l")
    if chunk == b"VP8 " and len(data) >= 30 and data[23:26] == b"\x9d\x01\x2a":
        width = struct.unpack("<H", data[26:28])[0] & 0x3FFF
        height = struct.unpack("<H", data[28:30])[0] & 0x3FFF
        if width > 0 and height > 0:
            return ImageSniff("image/webp", width, height, "webp-vp8")
    return None


def _sniff_jpeg(data: bytes) -> ImageSniff | None:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        return None
    index = 2
    limit = min(len(data), 1024 * 1024)
    sof_markers = {
        0xC0,
        0xC1,
        0xC2,
        0xC3,
        0xC5,
        0xC6,
        0xC7,
        0xC9,
        0xCA,
        0xCB,
        0xCD,
        0xCE,
        0xCF,
    }
    while index + 9 < limit:
        if data[index] != 0xFF:
            next_marker = data.find(b"\xff", index + 1, limit)
            if next_marker < 0:
                return None
            index = next_marker
            continue
        while index < limit and data[index] == 0xFF:
            index += 1
        if index >= limit:
            return None
        marker = data[index]
        index += 1
        if marker in {0x01} or 0xD0 <= marker <= 0xD9:
            continue
        if index + 2 > limit:
            return None
        segment_length = int.from_bytes(data[index:index + 2], "big")
        if segment_length < 2 or index + segment_length > limit:
            return None
        if marker in sof_markers and segment_length >= 7:
            height = int.from_bytes(data[index + 3:index + 5], "big")
            width = int.from_bytes(data[index + 5:index + 7], "big")
            if width > 0 and height > 0:
                return ImageSniff("image/jpeg", width, height, "jpeg")
            return None
        index += segment_length
    return None


def _read_uint24_le(data: bytes) -> int:
    if len(data) != 3:
        return 0
    return data[0] | (data[1] << 8) | (data[2] << 16)
