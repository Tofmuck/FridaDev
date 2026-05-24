from __future__ import annotations

"""Bounded PDF reader for web URLs.

This module is deliberately small: it downloads a PDF in memory, extracts text
through the active-document extractor, and returns compact metadata for the web
pipeline. It does not OCR, store, index, or cache downloaded files.
"""

import io
import ipaddress
import socket
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import requests

from core import active_document_text_extraction


DEFAULT_TIMEOUT_S = 12
DEFAULT_MAX_BYTES = 15 * 1024 * 1024
DEFAULT_MAX_PAGES = 25
DEFAULT_MAX_CHARS = 25_000
PDF_FILTER = "pdf"

STATUS_SKIPPED = "skipped"
STATUS_SUCCESS = "success"
STATUS_EMPTY = "empty"
STATUS_ERROR = "error"

REASON_NOT_PDF = "web_pdf_not_detected"
REASON_DOWNLOAD_FAILED = "web_pdf_download_failed"
REASON_TOO_LARGE = "web_pdf_too_large"
REASON_TOO_MANY_PAGES = "web_pdf_too_many_pages"
REASON_EMPTY_TEXT = "web_pdf_empty_text"
REASON_EXTRACTION_FAILED = "web_pdf_extraction_failed"
REASON_READ_SUCCESS = "web_pdf_read_success"
REASON_READ_TRUNCATED = "web_pdf_read_truncated"
REASON_URL_BLOCKED_INTERNAL = "web_pdf_url_blocked_internal"

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTS = {
    "localhost",
    "localhost.localdomain",
    "host.docker.internal",
    "gateway.docker.internal",
}
_BLOCKED_HOST_SUFFIXES = (
    ".localhost",
    ".local",
    ".internal",
    ".docker",
)
_REDIRECT_STATUSES = {301, 302, 303, 307, 308}


@dataclass(frozen=True)
class WebPdfReadResult:
    url: str = field(repr=False)
    status: str
    reason_code: str
    attempted: bool
    detected: bool
    media_type: str = ""
    text: str = field(default="", repr=False)
    bytes_read: int = 0
    pages: int = 0
    chars: int = 0
    elapsed_ms: int = 0
    truncated: bool = False
    error_class: str = ""

    def to_observability(self) -> dict[str, Any]:
        return {
            "web_pdf_read_attempted": self.attempted,
            "web_pdf_read_detected": self.detected,
            "web_pdf_read_status": self.status,
            "web_pdf_read_reason_code": self.reason_code,
            "web_pdf_read_pages": self.pages,
            "web_pdf_read_bytes": self.bytes_read,
            "web_pdf_read_chars": self.chars,
            "web_pdf_read_elapsed_ms": self.elapsed_ms,
            "web_pdf_read_truncated": self.truncated,
            "web_pdf_read_error_class": self.error_class,
        }

    def to_crawl_like_result(self) -> dict[str, Any]:
        crawl_status = self.status if self.status in {STATUS_SUCCESS, STATUS_EMPTY} else STATUS_ERROR
        return {
            "status": crawl_status,
            "markdown": self.text if self.status == STATUS_SUCCESS else "",
            "error_class": self.error_class or None,
            "filter": PDF_FILTER,
            "crawl_filter_used": PDF_FILTER,
            "crawl_filter_requested": PDF_FILTER,
            "crawl_policy_kind": "web_pdf_reader",
            "crawl_policy_reason": self.reason_code,
            "crawl_cache_mode": "none",
            "crawl_query_sha256_12": "",
            "crawl_query_chars": 0,
            "crawl_fallback_used": False,
            "crawl_fallback_reason": "",
            "crawl_primary_status": crawl_status,
            "crawl_fallback_status": "",
            "crawl_markdown_chars": self.chars,
            "crawl_max_chars": DEFAULT_MAX_CHARS,
            **self.to_observability(),
        }


def is_pdf_url_candidate(url: str) -> bool:
    parsed = urlparse(str(url or "").strip())
    return parsed.scheme in {"http", "https"} and Path(parsed.path).suffix.lower() == ".pdf"


def read_pdf_url(
    url: str,
    *,
    requests_module: Any = requests,
    timeout_s: int = DEFAULT_TIMEOUT_S,
    max_bytes: int = DEFAULT_MAX_BYTES,
    max_pages: int = DEFAULT_MAX_PAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    probe_content_type: bool = True,
) -> WebPdfReadResult:
    start = time.monotonic()
    normalized_url = str(url or "").strip()
    if not normalized_url:
        return _result(
            normalized_url,
            status=STATUS_SKIPPED,
            reason_code=REASON_NOT_PDF,
            attempted=False,
            detected=False,
            start=start,
        )

    blocked_reason = _blocked_url_reason(normalized_url)
    if blocked_reason:
        return _result(
            normalized_url,
            status=STATUS_ERROR,
            reason_code=blocked_reason,
            attempted=False,
            detected=False,
            start=start,
        )

    url_candidate = is_pdf_url_candidate(normalized_url)
    head_media_type = ""
    head_length = 0
    head_blocked_reason = ""
    if probe_content_type or url_candidate:
        head_media_type, head_length, head_blocked_reason = _probe_pdf_headers(
            normalized_url,
            requests_module=requests_module,
            timeout_s=timeout_s,
        )
    if head_blocked_reason:
        return _result(
            normalized_url,
            status=STATUS_ERROR,
            reason_code=head_blocked_reason,
            attempted=True,
            detected=url_candidate,
            media_type=head_media_type,
            bytes_read=head_length,
            start=start,
        )

    detected = url_candidate or _is_pdf_media_type(head_media_type)
    if not detected:
        return _result(
            normalized_url,
            status=STATUS_SKIPPED,
            reason_code=REASON_NOT_PDF,
            attempted=False,
            detected=False,
            media_type=head_media_type,
            start=start,
        )
    if head_length > int(max_bytes or DEFAULT_MAX_BYTES):
        return _result(
            normalized_url,
            status=STATUS_ERROR,
            reason_code=REASON_TOO_LARGE,
            attempted=True,
            detected=True,
            media_type=head_media_type,
            bytes_read=head_length,
            start=start,
        )

    download = _download_pdf(
        normalized_url,
        requests_module=requests_module,
        timeout_s=timeout_s,
        max_bytes=max_bytes,
    )
    if download["status"] != STATUS_SUCCESS:
        return _result(
            normalized_url,
            status=STATUS_ERROR,
            reason_code=str(download["reason_code"]),
            attempted=True,
            detected=True,
            media_type=str(download.get("media_type") or head_media_type),
            bytes_read=int(download.get("bytes_read") or 0),
            error_class=str(download.get("error_class") or ""),
            start=start,
        )

    media_type = str(download.get("media_type") or head_media_type or "application/pdf")
    data = bytes(download.get("content") or b"")
    return read_pdf_bytes(
        data,
        url=normalized_url,
        media_type=media_type,
        max_pages=max_pages,
        max_chars=max_chars,
        start=start,
    )


def read_pdf_bytes(
    content: bytes,
    *,
    url: str = "",
    media_type: str = "application/pdf",
    max_pages: int = DEFAULT_MAX_PAGES,
    max_chars: int = DEFAULT_MAX_CHARS,
    start: float | None = None,
) -> WebPdfReadResult:
    started = time.monotonic() if start is None else start
    data = bytes(content or b"")
    page_count = 0
    try:
        page_count = _pdf_page_count(data)
        if page_count > int(max_pages or DEFAULT_MAX_PAGES):
            return _result(
                url,
                status=STATUS_ERROR,
                reason_code=REASON_TOO_MANY_PAGES,
                attempted=True,
                detected=True,
                media_type=media_type,
                bytes_read=len(data),
                pages=page_count,
                start=started,
            )
        extraction = active_document_text_extraction.extract_active_document_text(
            data,
            filename=_filename_from_url(url),
            media_type=media_type,
        )
    except Exception as exc:
        return _result(
            url,
            status=STATUS_ERROR,
            reason_code=REASON_EXTRACTION_FAILED,
            attempted=True,
            detected=True,
            media_type=media_type,
            bytes_read=len(data),
            pages=page_count,
            error_class=exc.__class__.__name__,
            start=started,
        )

    text = str(extraction.text or "")
    if extraction.status != active_document_text_extraction.STATUS_COMPLETE or not text:
        return _result(
            url,
            status=STATUS_EMPTY,
            reason_code=str(extraction.reason_code or REASON_EMPTY_TEXT),
            attempted=True,
            detected=True,
            media_type=media_type,
            bytes_read=len(data),
            pages=page_count,
            start=started,
        )

    max_text_chars = int(max_chars or DEFAULT_MAX_CHARS)
    truncated = len(text) > max_text_chars
    if truncated:
        text = text[:max_text_chars] + "\n[...contenu tronqué]"
    return _result(
        url,
        status=STATUS_SUCCESS,
        reason_code=REASON_READ_TRUNCATED if truncated else REASON_READ_SUCCESS,
        attempted=True,
        detected=True,
        media_type=media_type,
        text=text,
        bytes_read=len(data),
        pages=page_count,
        chars=len(text),
        truncated=truncated,
        start=started,
    )


def _probe_pdf_headers(
    url: str,
    *,
    requests_module: Any,
    timeout_s: int,
) -> tuple[str, int, str]:
    head = getattr(requests_module, "head", None)
    if head is None:
        return "", 0, ""
    try:
        response = _request_public_url(
            head,
            url,
            timeout_s=timeout_s,
            max_redirects=3,
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        headers = getattr(response, "headers", {}) or {}
        return _media_type(headers), _content_length(headers), ""
    except _WebPdfUrlBlocked as exc:
        return "", 0, exc.reason_code
    except Exception:
        return "", 0, ""


def _download_pdf(
    url: str,
    *,
    requests_module: Any,
    timeout_s: int,
    max_bytes: int,
) -> dict[str, Any]:
    try:
        response = _request_public_url(
            requests_module.get,
            url,
            timeout_s=timeout_s,
            max_redirects=3,
            headers={"Accept": "application/pdf"},
            stream=True,
        )
        if hasattr(response, "raise_for_status"):
            response.raise_for_status()
        headers = getattr(response, "headers", {}) or {}
        media_type = _media_type(headers)
        length = _content_length(headers)
        if length > int(max_bytes or DEFAULT_MAX_BYTES):
            return {
                "status": STATUS_ERROR,
                "reason_code": REASON_TOO_LARGE,
                "media_type": media_type,
                "bytes_read": length,
            }

        chunks: list[bytes] = []
        total = 0
        if hasattr(response, "iter_content"):
            iterator = response.iter_content(chunk_size=64 * 1024)
        else:
            iterator = (bytes(getattr(response, "content", b"") or b""),)
        for chunk in iterator:
            data = bytes(chunk or b"")
            if not data:
                continue
            total += len(data)
            if total > int(max_bytes or DEFAULT_MAX_BYTES):
                return {
                    "status": STATUS_ERROR,
                    "reason_code": REASON_TOO_LARGE,
                    "media_type": media_type,
                    "bytes_read": total,
                }
            chunks.append(data)
        return {
            "status": STATUS_SUCCESS,
            "reason_code": "",
            "media_type": media_type,
            "bytes_read": total,
            "content": b"".join(chunks),
        }
    except _WebPdfUrlBlocked as exc:
        return {
            "status": STATUS_ERROR,
            "reason_code": exc.reason_code,
            "bytes_read": 0,
            "error_class": exc.__class__.__name__,
        }
    except Exception as exc:
        return {
            "status": STATUS_ERROR,
            "reason_code": REASON_DOWNLOAD_FAILED,
            "bytes_read": 0,
            "error_class": exc.__class__.__name__,
        }


def _pdf_page_count(data: bytes) -> int:
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover - dependency covered by runtime image.
        raise RuntimeError("pypdf_unavailable") from exc

    reader = PdfReader(io.BytesIO(data))
    if bool(getattr(reader, "is_encrypted", False)):
        raise ValueError("encrypted_pdf")
    return len(list(getattr(reader, "pages", []) or []))


def _filename_from_url(url: str) -> str:
    path = urlparse(str(url or "")).path
    filename = Path(path).name.strip()
    return filename or "web-document.pdf"


def _media_type(headers: Any) -> str:
    try:
        raw = headers.get("Content-Type") or headers.get("content-type") or ""
    except AttributeError:
        raw = ""
    return str(raw).split(";", 1)[0].strip().lower()


def _content_length(headers: Any) -> int:
    try:
        raw = headers.get("Content-Length") or headers.get("content-length") or ""
        return int(raw or 0)
    except (TypeError, ValueError, AttributeError):
        return 0


class _WebPdfUrlBlocked(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


def _request_public_url(
    request_callable: Any,
    url: str,
    *,
    timeout_s: int,
    max_redirects: int,
    **kwargs: Any,
) -> Any:
    current_url = str(url or "")
    redirects_remaining = max(0, int(max_redirects or 0))
    while True:
        blocked_reason = _blocked_url_reason(current_url)
        if blocked_reason:
            raise _WebPdfUrlBlocked(blocked_reason)
        response = request_callable(
            current_url,
            allow_redirects=False,
            timeout=timeout_s,
            **kwargs,
        )
        redirect_url = _redirect_url(current_url, response)
        if not redirect_url:
            return response
        if redirects_remaining <= 0:
            raise requests.TooManyRedirects("web_pdf_redirect_limit")
        redirects_remaining -= 1
        current_url = redirect_url


def _redirect_url(current_url: str, response: Any) -> str:
    try:
        status_code = int(getattr(response, "status_code", 0) or 0)
    except (TypeError, ValueError):
        status_code = 0
    if status_code not in _REDIRECT_STATUSES:
        return ""
    headers = getattr(response, "headers", {}) or {}
    try:
        location = headers.get("Location") or headers.get("location") or ""
    except AttributeError:
        location = ""
    if not str(location or "").strip():
        return ""
    return urljoin(str(current_url or ""), str(location or "").strip())


def _blocked_url_reason(url: str) -> str:
    parsed = urlparse(str(url or "").strip())
    if parsed.scheme not in _ALLOWED_SCHEMES:
        return REASON_URL_BLOCKED_INTERNAL

    host = str(parsed.hostname or "").strip().lower().rstrip(".")
    if not host:
        return REASON_URL_BLOCKED_INTERNAL
    if host in _BLOCKED_HOSTS or any(host.endswith(suffix) for suffix in _BLOCKED_HOST_SUFFIXES):
        return REASON_URL_BLOCKED_INTERNAL

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        if "." not in host:
            return REASON_URL_BLOCKED_INTERNAL
        return _blocked_hostname_reason(host)
    return REASON_URL_BLOCKED_INTERNAL if _is_blocked_ip(address) else ""


def _blocked_hostname_reason(host: str) -> str:
    try:
        infos = socket.getaddrinfo(host, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return ""
    except Exception:
        return REASON_URL_BLOCKED_INTERNAL
    resolved: list[str] = []
    for info in infos or []:
        try:
            resolved.append(str(info[4][0]))
        except (IndexError, TypeError):
            continue
    if not resolved:
        return REASON_URL_BLOCKED_INTERNAL
    for value in resolved:
        try:
            if _is_blocked_ip(ipaddress.ip_address(value)):
                return REASON_URL_BLOCKED_INTERNAL
        except ValueError:
            return REASON_URL_BLOCKED_INTERNAL
    return ""


def _is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return (
        address.is_loopback
        or address.is_private
        or address.is_link_local
        or address.is_multicast
        or address.is_unspecified
        or address.is_reserved
        or not address.is_global
    )


def _is_pdf_media_type(media_type: str) -> bool:
    return str(media_type or "").split(";", 1)[0].strip().lower() == "application/pdf"


def _elapsed_ms(start: float) -> int:
    return max(0, int((time.monotonic() - start) * 1000))


def _result(
    url: str,
    *,
    status: str,
    reason_code: str,
    attempted: bool,
    detected: bool,
    start: float,
    media_type: str = "",
    text: str = "",
    bytes_read: int = 0,
    pages: int = 0,
    chars: int = 0,
    truncated: bool = False,
    error_class: str = "",
) -> WebPdfReadResult:
    return WebPdfReadResult(
        url=str(url or ""),
        status=str(status or STATUS_ERROR),
        reason_code=str(reason_code or ""),
        attempted=bool(attempted),
        detected=bool(detected),
        media_type=str(media_type or ""),
        text=str(text or ""),
        bytes_read=int(bytes_read or 0),
        pages=int(pages or 0),
        chars=int(chars or len(str(text or ""))),
        elapsed_ms=_elapsed_ms(start),
        truncated=bool(truncated),
        error_class=str(error_class or ""),
    )
