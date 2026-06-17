from __future__ import annotations

"""Bounded visual PDF checks shared by active and folder documents."""

from dataclasses import dataclass
from typing import Any, Callable, Optional

from . import active_document_ocr_client


STATUS_OK = "ok"
STATUS_ERROR = "error"
REASON_VISUAL_PDF_TOO_MANY_PAGES = "pdf_visual_too_many_pages"
REASON_VISUAL_PDF_PAGE_COUNT_FAILED = "pdf_visual_page_count_failed"
DEFAULT_MAX_PDF_VISUAL_PAGES = active_document_ocr_client.DEFAULT_MAX_PAGES


@dataclass(frozen=True)
class VisualPdfLimitResult:
    status: str
    reason_code: str
    page_count: int
    max_pages: int

    @property
    def ok(self) -> bool:
        return self.status == STATUS_OK


def check_pdf_visual_pages(
    content: bytes,
    *,
    max_pages: int = DEFAULT_MAX_PDF_VISUAL_PAGES,
    pdf_reader_factory: Optional[Callable[[Any], Any]] = None,
) -> VisualPdfLimitResult:
    limit = _positive_int(max_pages, DEFAULT_MAX_PDF_VISUAL_PAGES)
    try:
        page_count = active_document_ocr_client.count_pdf_pages(
            bytes(content or b""),
            pdf_reader_factory=pdf_reader_factory,
        )
    except Exception:
        return VisualPdfLimitResult(
            status=STATUS_ERROR,
            reason_code=REASON_VISUAL_PDF_PAGE_COUNT_FAILED,
            page_count=0,
            max_pages=limit,
        )
    if page_count > limit:
        return VisualPdfLimitResult(
            status=STATUS_ERROR,
            reason_code=REASON_VISUAL_PDF_TOO_MANY_PAGES,
            page_count=page_count,
            max_pages=limit,
        )
    return VisualPdfLimitResult(
        status=STATUS_OK,
        reason_code="",
        page_count=page_count,
        max_pages=limit,
    )


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default
