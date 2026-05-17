from __future__ import annotations

"""Bounded OCR client for scanned active conversation document PDFs.

The client is intentionally not wired to upload activation in this lot. It only
turns a PDF that already needs OCR into an OCRized PDF plus compact metadata, or
returns a content-free refusal/failure reason.
"""

import io
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional

import requests

try:  # pragma: no cover - fallback only matters in unusual import layouts.
    import config as default_config
except Exception:  # pragma: no cover
    default_config = None  # type: ignore[assignment]


STATUS_COMPLETE = "complete"
STATUS_ERROR = "error"

REASON_OCR_FAILED = "document_ocr_failed"
REASON_OCR_TIMEOUT = "document_ocr_timeout"
REASON_OCR_EMPTY = "document_ocr_empty"
REASON_OCR_TOO_LARGE = "document_ocr_too_large"
REASON_OCR_TOO_MANY_PAGES = "document_ocr_too_many_pages"

DEFAULT_OCR_URL = "http://platform-stirling-pdf:8080/pdf/api/v1/misc/ocr-pdf"
DEFAULT_TIMEOUT_S = 180
DEFAULT_LANGUAGES = "fra+eng+deu"
DEFAULT_MAX_PAGES = 25
DEFAULT_MAX_BYTES = 25 * 1024 * 1024
OCR_ENGINE = "stirling-pdf"


@dataclass(frozen=True)
class ActiveDocumentOcrConfig:
    url: str
    timeout_s: int
    languages: str
    max_pages: int
    max_bytes: int


@dataclass(frozen=True)
class ActiveDocumentOcrResult:
    status: str
    reason_code: str
    ocr_pdf: bytes
    source_bytes: int
    page_count: int
    ocr_engine: str
    ocr_languages: str
    ocr_duration_ms: int
    content_type: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "source_bytes": self.source_bytes,
            "page_count": self.page_count,
            "ocr_applied": self.status == STATUS_COMPLETE,
            "ocr_engine": self.ocr_engine,
            "ocr_languages": self.ocr_languages,
            "ocr_duration_ms": self.ocr_duration_ms,
            "content_type": self.content_type,
            "warnings": list(self.warnings),
        }


def get_active_document_ocr_config(config_module: Any = None) -> ActiveDocumentOcrConfig:
    source = config_module if config_module is not None else default_config
    return ActiveDocumentOcrConfig(
        url=str(getattr(source, "ACTIVE_DOCUMENT_OCR_URL", DEFAULT_OCR_URL) or DEFAULT_OCR_URL).strip(),
        timeout_s=_positive_int(getattr(source, "ACTIVE_DOCUMENT_OCR_TIMEOUT_S", DEFAULT_TIMEOUT_S), DEFAULT_TIMEOUT_S),
        languages=str(getattr(source, "ACTIVE_DOCUMENT_OCR_LANGUAGES", DEFAULT_LANGUAGES) or DEFAULT_LANGUAGES).strip()
        or DEFAULT_LANGUAGES,
        max_pages=_positive_int(getattr(source, "ACTIVE_DOCUMENT_OCR_MAX_PAGES", DEFAULT_MAX_PAGES), DEFAULT_MAX_PAGES),
        max_bytes=_positive_int(getattr(source, "ACTIVE_DOCUMENT_OCR_MAX_BYTES", DEFAULT_MAX_BYTES), DEFAULT_MAX_BYTES),
    )


def ocr_pdf_with_stirling(
    content: bytes,
    *,
    filename: str = "document.pdf",
    config_module: Any = None,
    requests_module: Any = requests,
    pdf_reader_factory: Optional[Callable[[io.BytesIO], Any]] = None,
    monotonic: Callable[[], float] = time.monotonic,
) -> ActiveDocumentOcrResult:
    """OCR a scanned PDF through Stirling and return only compact metadata.

    The result does not parse or activate the OCRized PDF. Lot 3 will feed the
    returned PDF back into the existing text extractor and only activate on a
    final ``complete`` extraction.
    """

    data = bytes(content or b"")
    settings = get_active_document_ocr_config(config_module)
    if len(data) > settings.max_bytes:
        return _failure(
            reason_code=REASON_OCR_TOO_LARGE,
            source_bytes=len(data),
            page_count=0,
            settings=settings,
            warnings=(f"max_bytes={settings.max_bytes}",),
        )

    try:
        page_count = _count_pdf_pages(data, pdf_reader_factory=pdf_reader_factory)
    except Exception as exc:
        return _failure(
            reason_code=REASON_OCR_FAILED,
            source_bytes=len(data),
            page_count=0,
            settings=settings,
            warnings=(type(exc).__name__,),
        )
    if page_count > settings.max_pages:
        return _failure(
            reason_code=REASON_OCR_TOO_MANY_PAGES,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            warnings=(f"max_pages={settings.max_pages}",),
        )

    started = monotonic()
    try:
        response = requests_module.post(
            settings.url,
            files={"fileInput": (_safe_filename(filename), data, "application/pdf")},
            data=_stirling_form_data(settings.languages),
            timeout=settings.timeout_s,
        )
    except _timeout_exception(requests_module):
        return _failure(
            reason_code=REASON_OCR_TIMEOUT,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            duration_ms=_duration_ms(started, monotonic),
        )
    except _request_exception(requests_module) as exc:
        return _failure(
            reason_code=REASON_OCR_FAILED,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            duration_ms=_duration_ms(started, monotonic),
            warnings=(type(exc).__name__,),
        )

    duration_ms = _duration_ms(started, monotonic)
    status_code = int(getattr(response, "status_code", 0) or 0)
    if status_code >= 400 or status_code <= 0:
        return _failure(
            reason_code=REASON_OCR_FAILED,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            duration_ms=duration_ms,
            warnings=(f"http_status={status_code}",),
        )

    content_type = _response_content_type(response)
    if content_type != "application/pdf":
        return _failure(
            reason_code=REASON_OCR_FAILED,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            duration_ms=duration_ms,
            content_type=content_type,
            warnings=("non_pdf_response",),
        )

    ocr_pdf = bytes(getattr(response, "content", b"") or b"")
    if not ocr_pdf:
        return _failure(
            reason_code=REASON_OCR_EMPTY,
            source_bytes=len(data),
            page_count=page_count,
            settings=settings,
            duration_ms=duration_ms,
            content_type=content_type,
        )

    return ActiveDocumentOcrResult(
        status=STATUS_COMPLETE,
        reason_code="",
        ocr_pdf=ocr_pdf,
        source_bytes=len(data),
        page_count=page_count,
        ocr_engine=OCR_ENGINE,
        ocr_languages=settings.languages,
        ocr_duration_ms=duration_ms,
        content_type=content_type,
    )


def _count_pdf_pages(
    data: bytes,
    *,
    pdf_reader_factory: Optional[Callable[[io.BytesIO], Any]] = None,
) -> int:
    reader_factory = pdf_reader_factory
    if reader_factory is None:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - dependency is present in runtime images.
            raise RuntimeError("pypdf_unavailable") from exc
        reader_factory = PdfReader

    reader = reader_factory(io.BytesIO(data))
    if bool(getattr(reader, "is_encrypted", False)):
        raise ValueError("encrypted_pdf")
    return len(list(getattr(reader, "pages", []) or []))


def _failure(
    *,
    reason_code: str,
    source_bytes: int,
    page_count: int,
    settings: ActiveDocumentOcrConfig,
    duration_ms: int = 0,
    content_type: str = "",
    warnings: tuple[str, ...] = (),
) -> ActiveDocumentOcrResult:
    return ActiveDocumentOcrResult(
        status=STATUS_ERROR,
        reason_code=reason_code,
        ocr_pdf=b"",
        source_bytes=source_bytes,
        page_count=page_count,
        ocr_engine=OCR_ENGINE,
        ocr_languages=settings.languages,
        ocr_duration_ms=duration_ms,
        content_type=content_type,
        warnings=tuple(str(item) for item in warnings if item),
    )


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _safe_filename(filename: str) -> str:
    cleaned = str(filename or "document.pdf").strip().split("/")[-1].split("\\")[-1]
    return cleaned or "document.pdf"


def _stirling_form_data(languages: str) -> list[tuple[str, str]]:
    parts = [
        item.strip()
        for item in str(languages or DEFAULT_LANGUAGES).replace(",", "+").split("+")
        if item.strip()
    ]
    return [
        *[("languages", item) for item in parts],
        ("ocrType", "force-ocr"),
        ("ocrRenderType", "sandwich"),
    ]


def _response_content_type(response: Any) -> str:
    headers = getattr(response, "headers", {}) or {}
    getter = getattr(headers, "get", None)
    raw = getter("content-type", "") if callable(getter) else ""
    if not raw and callable(getter):
        raw = getter("Content-Type", "")
    return str(raw or "").split(";", 1)[0].strip().lower()


def _timeout_exception(requests_module: Any) -> type[BaseException]:
    exceptions = getattr(requests_module, "exceptions", requests.exceptions)
    candidate = getattr(exceptions, "Timeout", requests.exceptions.Timeout)
    return candidate if isinstance(candidate, type) else requests.exceptions.Timeout


def _request_exception(requests_module: Any) -> type[BaseException]:
    exceptions = getattr(requests_module, "exceptions", requests.exceptions)
    candidate = getattr(exceptions, "RequestException", requests.exceptions.RequestException)
    return candidate if isinstance(candidate, type) else requests.exceptions.RequestException


def _duration_ms(started: float, monotonic: Callable[[], float]) -> int:
    elapsed = max(0.0, monotonic() - started)
    return int(round(elapsed * 1000))
