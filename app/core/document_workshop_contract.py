"""Inactive workshop M0 bounds. No renderer, transaction or product wiring."""
from __future__ import annotations

DOCUMENT_MODEL = "openai/gpt-5.1"
DOCUMENT_OUTPUT_TOKENS = 24_000
DOCUMENT_CONTEXT_TOKENS = 400_000
MAX_DOCUMENT_WORDS = 10_000
MAX_DOCUMENT_CODEPOINTS = 75_000
MAX_WRITER_PAGES = 20
PREPARATION_INACTIVITY_SECONDS = 120
DOCUMENT_PROFILE = "frida_document_v1"
DOCUMENT_LAYOUT = ("A4", 12, 1.5, 2.5)
DOCUMENT_EXTENSIONS = {"markdown": ".md", "docx": ".docx", "pdf": ".pdf"}
# Technical JSON envelope bound already specified by roadmap §9.3; not a
# substitute for the independent word/codepoint/page bounds, and never truncates.
MAX_CANONICAL_JSON_BYTES = 1_048_576


class DocumentWorkshopError(ValueError):
    """Content-free internal failure; never accepts an upstream exception/text."""

    def __init__(self, reason_code: str):
        super().__init__(reason_code)
        self.reason_code = reason_code


def validate_writer_page_count(page_count: object) -> int:
    """Validate only the type and limit of a *final Writer* layout observation.

    This cannot establish its provenance or the success of a binary render.
    M8–M10 must supply and bind that evidence to the final bytes/revision.
    Markdown and source admission do not call this function.
    """
    if type(page_count) is not int or page_count < 1:
        raise DocumentWorkshopError("document_page_evidence_invalid")
    if page_count > MAX_WRITER_PAGES:
        raise DocumentWorkshopError("document_page_limit")
    return page_count
