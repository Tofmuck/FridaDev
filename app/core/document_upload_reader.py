from __future__ import annotations

"""Bounded byte reader shared by the two document upload services."""

from typing import Any


UPLOAD_READ_CHUNK_BYTES = 64 * 1024


class DocumentUploadTooLargeError(Exception):
    def __init__(self, *, max_bytes: int, observed_bytes: int) -> None:
        super().__init__("document upload exceeds byte limit")
        self.max_bytes = int(max_bytes)
        self.observed_bytes = int(observed_bytes)


def read_document_upload_bytes(file_obj: Any, *, max_bytes: int) -> bytes:
    """Read at most ``max_bytes + 1`` and never return an oversized prefix."""

    byte_limit = int(max_bytes)
    if byte_limit < 0:
        raise ValueError("max_bytes must be non-negative")

    observed_limit = byte_limit + 1
    chunks: list[bytes] = []
    observed_bytes = 0
    while observed_bytes < observed_limit:
        read_size = min(UPLOAD_READ_CHUNK_BYTES, observed_limit - observed_bytes)
        chunk = bytes(file_obj.read(read_size) or b"")
        if not chunk:
            break
        if len(chunk) > read_size:
            raise DocumentUploadTooLargeError(
                max_bytes=byte_limit,
                observed_bytes=observed_limit,
            )
        chunks.append(chunk)
        observed_bytes += len(chunk)
        if observed_bytes > byte_limit:
            raise DocumentUploadTooLargeError(
                max_bytes=byte_limit,
                observed_bytes=observed_bytes,
            )
    return b"".join(chunks)
