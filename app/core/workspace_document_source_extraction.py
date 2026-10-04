"""Complete workshop source reading. Plain text stays literal; binary formats
reuse the existing extractors' documented whitespace semantics after preflight.

Binary parsing happens in one fixed, resource-limited process. It receives only
source bytes and a fixed kind, never a path, command, URL or runtime secret.
"""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

from . import active_document_text_extraction as extraction
from .document_workshop_contract import DocumentWorkshopError
from .workspace_document_paths import _validate_segment

MAX_SOURCE_BYTES = 40 * 1024 * 1024
MAX_EXTRACTED_TEXT_BYTES = 40 * 1024 * 1024
MAX_ARCHIVE_EXPANDED_BYTES = 64 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 4096
_WORKER = str(Path(__file__).with_name("workspace_document_source_worker.py"))
_WORKER_REASONS = {
    21: "document_archive_invalid", 22: "document_source_limit",
    23: "document_extraction_incomplete", 24: "document_parse_error",
    25: "document_ocr_required", 26: "document_runtime_unavailable",
    27: "document_empty_text",
}


def extract_complete_source(content, *, filename, media_type=""):
    """Return the existing extraction value only after complete-source proof."""
    _validate_segment(filename)
    suffix = Path(filename).suffix.lower()
    kind = extraction.SUPPORTED_EXTENSIONS.get(suffix)
    if kind is None:
        raise DocumentWorkshopError("document_type_unsupported")
    if not isinstance(content, bytes) or not content:
        raise DocumentWorkshopError("document_empty_text")
    if len(content) > MAX_SOURCE_BYTES:
        raise DocumentWorkshopError("document_source_limit")
    if kind in {extraction.KIND_TXT, extraction.KIND_MD}:
        try:
            text = extraction._extract_utf_text(content)
        except (ValueError, UnicodeError):
            raise DocumentWorkshopError("document_parse_error") from None
        if "\x00" in text:
            raise DocumentWorkshopError("document_parse_error")
    else:
        try:
            process = subprocess.run(
                [sys.executable, "-I", "-B", _WORKER, kind], input=content,
                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                env={"PYTHONDONTWRITEBYTECODE": "1"}, close_fds=True, check=False,
            )
        except (OSError, ValueError):
            raise DocumentWorkshopError("document_source_processing_failed") from None
        if process.returncode:
            raise DocumentWorkshopError(_WORKER_REASONS.get(process.returncode, "document_source_processing_failed"))
        if len(process.stdout) > MAX_EXTRACTED_TEXT_BYTES:
            raise DocumentWorkshopError("document_source_limit")
        try:
            text = process.stdout.decode("utf-8", errors="strict")
        except UnicodeError:
            raise DocumentWorkshopError("document_source_processing_failed") from None
    if not text.strip():
        raise DocumentWorkshopError("document_empty_text")
    if len(text.encode("utf-8")) > MAX_EXTRACTED_TEXT_BYTES:
        raise DocumentWorkshopError("document_source_limit")
    return extraction._complete(
        filename=filename, media_type=extraction._normalize_media_type(media_type, filename),
        source_extension=suffix, parser=kind, byte_size=len(content), text=text,
    )
