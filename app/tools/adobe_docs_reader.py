from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re
import time
from typing import Any

import requests

import config
from tools import adobe_docs_sources


CRAWL4AI_FILTER_RAW = 'raw'
CRAWL4AI_CACHE_DISABLED = '0'

ADOBE_CRAWL_TIMEOUT_S = 20
ADOBE_MAX_RAW_CHARS_PER_PAGE = 300_000

STATUS_SUCCESS = 'success'
STATUS_EMPTY = 'empty'
STATUS_ERROR = 'error'
STATUS_TIMEOUT = 'timeout'
STATUS_INVALID_URL = 'invalid_url'

REASON_CRAWL_RAW_PRIMARY = 'crawl_raw_primary'
REASON_CRAWL_EMPTY = 'crawl_empty'
REASON_CRAWL_HTTP_ERROR = 'crawl_http_error'
REASON_CRAWL_UNSUCCESSFUL = 'crawl_unsuccessful'
REASON_CRAWL_TIMEOUT = 'crawl_timeout'
REASON_CRAWL_EXCEPTION = 'crawl_exception'
REASON_MARKDOWN_TRUNCATED = 'markdown_truncated'
REASON_INVALID_SOURCE_TYPE = 'invalid_source_type'
REASON_SOURCE_TYPE_MISMATCH = 'source_type_mismatch'

_HEADING_RE = re.compile(r'^\s{0,3}#{1,6}\s+\S+', re.MULTILINE)
_MARKDOWN_LINK_RE = re.compile(r'\[[^\]]+\]\([^)]+\)')


@dataclass(frozen=True, repr=False)
class AdobeDocsReadResult:
    status: str
    product: str
    source_type: str = ''
    canonical_url: str = ''
    markdown: str = ''
    chars: int = 0
    headings: int = 0
    link_count: int = 0
    elapsed_ms: int = 0
    filter_used: str = CRAWL4AI_FILTER_RAW
    cache_mode: str = CRAWL4AI_CACHE_DISABLED
    reason_code: str = ''
    reason_codes: tuple[str, ...] = ()
    error_class: str = ''
    url_sha256_12: str = ''
    markdown_truncated: bool = False

    def __repr__(self) -> str:
        return (
            "AdobeDocsReadResult("
            f"status={self.status!r}, product={self.product!r}, "
            f"source_type={self.source_type!r}, "
            f"chars={self.chars!r}, headings={self.headings!r}, link_count={self.link_count!r}, "
            f"elapsed_ms={self.elapsed_ms!r}, filter_used={self.filter_used!r}, "
            f"reason_code={self.reason_code!r}, reason_codes={self.reason_codes!r}, "
            f"error_class={self.error_class!r}, url_sha256_12={self.url_sha256_12!r}, "
            f"markdown_truncated={self.markdown_truncated!r})"
        )

    def as_content_free_dict(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'product': self.product,
            'source_type': self.source_type,
            'url_sha256_12': self.url_sha256_12,
            'chars': self.chars,
            'headings': self.headings,
            'link_count': self.link_count,
            'elapsed_ms': self.elapsed_ms,
            'filter_used': self.filter_used,
            'cache_mode': self.cache_mode,
            'reason_code': self.reason_code,
            'reason_codes': list(self.reason_codes),
            'error_class': self.error_class,
            'markdown_truncated': self.markdown_truncated,
        }


def read_adobe_url(
    url: str,
    product: str,
    source_type: str | None = None,
    *,
    requests_module: Any = requests,
    crawl4ai_base_url: str | None = None,
    crawl4ai_token: str | None = None,
    timeout_s: int = ADOBE_CRAWL_TIMEOUT_S,
    max_raw_chars: int = ADOBE_MAX_RAW_CHARS_PER_PAGE,
    logger_obj: Any | None = None,
) -> AdobeDocsReadResult:
    started = time.monotonic()
    validation = adobe_docs_sources.validate_adobe_url(url, product)
    if not validation.ok:
        result = _result(
            status=STATUS_INVALID_URL,
            product=validation.product,
            source_type='',
            canonical_url=validation.canonical_url,
            reason_code=validation.reason_code or STATUS_INVALID_URL,
            reason_codes=validation.reason_codes,
            elapsed_ms=_elapsed_ms(started),
        )
        _log_content_free(logger_obj, result)
        return result

    resolved_source_type = validation.source_type
    source_type_text = str(source_type or '').strip()
    if source_type_text:
        if source_type_text not in adobe_docs_sources.VALID_SOURCE_TYPES:
            result = _result(
                status=STATUS_INVALID_URL,
                product=validation.product,
                source_type=resolved_source_type,
                canonical_url=validation.canonical_url,
                reason_code=REASON_INVALID_SOURCE_TYPE,
                reason_codes=(*validation.reason_codes, REASON_INVALID_SOURCE_TYPE),
                elapsed_ms=_elapsed_ms(started),
            )
            _log_content_free(logger_obj, result)
            return result
        if source_type_text != resolved_source_type:
            result = _result(
                status=STATUS_INVALID_URL,
                product=validation.product,
                source_type=resolved_source_type,
                canonical_url=validation.canonical_url,
                reason_code=REASON_SOURCE_TYPE_MISMATCH,
                reason_codes=(*validation.reason_codes, REASON_SOURCE_TYPE_MISMATCH),
                elapsed_ms=_elapsed_ms(started),
            )
            _log_content_free(logger_obj, result)
            return result

    payload = {
        'url': validation.canonical_url,
        'f': CRAWL4AI_FILTER_RAW,
        'c': CRAWL4AI_CACHE_DISABLED,
    }
    headers = {'Content-Type': 'application/json'}
    token = _crawl4ai_token(crawl4ai_token)
    if token:
        headers['Authorization'] = f'Bearer {token}'

    response = None
    try:
        response = requests_module.post(
            f'{_crawl4ai_base_url(crawl4ai_base_url)}/md',
            json=payload,
            headers=headers,
            timeout=int(timeout_s or ADOBE_CRAWL_TIMEOUT_S),
        )
        response.raise_for_status()
        data = response.json()
    except Exception as exc:
        status = STATUS_TIMEOUT if _is_timeout_exception(exc) else STATUS_ERROR
        if status == STATUS_TIMEOUT:
            reason_code = REASON_CRAWL_TIMEOUT
        elif response is not None:
            reason_code = REASON_CRAWL_HTTP_ERROR
        else:
            reason_code = REASON_CRAWL_EXCEPTION
        result = _result(
            status=status,
            product=validation.product,
            source_type=resolved_source_type,
            canonical_url=validation.canonical_url,
            reason_code=reason_code,
            reason_codes=(*validation.reason_codes, reason_code),
            elapsed_ms=_elapsed_ms(started),
            error_class=exc.__class__.__name__,
        )
        _log_content_free(logger_obj, result)
        return result

    actual_filter = str(data.get('filter') or CRAWL4AI_FILTER_RAW)
    if not data.get('success'):
        result = _result(
            status=STATUS_ERROR,
            product=validation.product,
            source_type=resolved_source_type,
            canonical_url=validation.canonical_url,
            filter_used=actual_filter,
            reason_code=REASON_CRAWL_UNSUCCESSFUL,
            reason_codes=(*validation.reason_codes, REASON_CRAWL_UNSUCCESSFUL),
            elapsed_ms=_elapsed_ms(started),
            error_class='crawl_unsuccessful',
        )
        _log_content_free(logger_obj, result)
        return result

    markdown = str(data.get('markdown') or '').strip()
    if not markdown:
        result = _result(
            status=STATUS_EMPTY,
            product=validation.product,
            source_type=resolved_source_type,
            canonical_url=validation.canonical_url,
            filter_used=actual_filter,
            reason_code=REASON_CRAWL_EMPTY,
            reason_codes=(*validation.reason_codes, REASON_CRAWL_EMPTY),
            elapsed_ms=_elapsed_ms(started),
        )
        _log_content_free(logger_obj, result)
        return result

    reason_codes = list(validation.reason_codes)
    reason_codes.append(REASON_CRAWL_RAW_PRIMARY)
    markdown, markdown_truncated = _apply_raw_size_bound(markdown, max_raw_chars)
    if markdown_truncated:
        reason_codes.append(REASON_MARKDOWN_TRUNCATED)

    result = _result(
        status=STATUS_SUCCESS,
        product=validation.product,
        source_type=resolved_source_type,
        canonical_url=validation.canonical_url,
        markdown=markdown,
        filter_used=actual_filter,
        reason_codes=tuple(reason_codes),
        elapsed_ms=_elapsed_ms(started),
        markdown_truncated=markdown_truncated,
    )
    _log_content_free(logger_obj, result)
    return result


def _result(
    *,
    status: str,
    product: str,
    source_type: str,
    canonical_url: str,
    markdown: str = '',
    filter_used: str = CRAWL4AI_FILTER_RAW,
    reason_code: str = '',
    reason_codes: tuple[str, ...] = (),
    elapsed_ms: int = 0,
    error_class: str = '',
    markdown_truncated: bool = False,
) -> AdobeDocsReadResult:
    safe_markdown = str(markdown or '')
    return AdobeDocsReadResult(
        status=str(status or STATUS_ERROR),
        product=str(product or ''),
        source_type=str(source_type or ''),
        canonical_url=str(canonical_url or ''),
        markdown=safe_markdown,
        chars=len(safe_markdown),
        headings=_count_headings(safe_markdown),
        link_count=_count_links(safe_markdown),
        elapsed_ms=int(elapsed_ms or 0),
        filter_used=str(filter_used or CRAWL4AI_FILTER_RAW),
        reason_code=str(reason_code or ''),
        reason_codes=_dedupe_codes(reason_codes),
        error_class=str(error_class or ''),
        url_sha256_12=_sha256_12(canonical_url),
        markdown_truncated=bool(markdown_truncated),
    )


def _crawl4ai_base_url(value: str | None) -> str:
    return str(value or getattr(config, 'CRAWL4AI_URL', '') or 'http://127.0.0.1:11235').rstrip('/')


def _crawl4ai_token(value: str | None) -> str:
    if value is not None:
        return str(value or '').strip()
    return str(getattr(config, 'CRAWL4AI_TOKEN', '') or '').strip()


def _apply_raw_size_bound(markdown: str, max_raw_chars: int) -> tuple[str, bool]:
    try:
        limit = int(max_raw_chars or 0)
    except (TypeError, ValueError):
        limit = 0
    if limit <= 0 or len(markdown) <= limit:
        return markdown, False
    return markdown[:limit], True


def _count_headings(markdown: str) -> int:
    return len(_HEADING_RE.findall(str(markdown or '')))


def _count_links(markdown: str) -> int:
    return len(_MARKDOWN_LINK_RE.findall(str(markdown or '')))


def _sha256_12(value: str) -> str:
    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _dedupe_codes(codes: tuple[str, ...]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        text = str(code or '').strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _is_timeout_exception(exc: Exception) -> bool:
    if isinstance(exc, TimeoutError):
        return True
    requests_exceptions = getattr(requests, 'exceptions', None)
    timeout_cls = getattr(requests_exceptions, 'Timeout', None)
    if timeout_cls and isinstance(exc, timeout_cls):
        return True
    return 'timeout' in exc.__class__.__name__.lower()


def _log_content_free(logger_obj: Any | None, result: AdobeDocsReadResult) -> None:
    if logger_obj is None:
        return
    log = getattr(logger_obj, 'info', None)
    if not callable(log):
        return
    log(
        (
            'adobe_docs_reader status=%s product=%s source_type=%s '
            'url_sha256_12=%s chars=%s headings=%s link_count=%s '
            'elapsed_ms=%s filter=%s reason_code=%s'
        ),
        result.status,
        result.product,
        result.source_type,
        result.url_sha256_12,
        result.chars,
        result.headings,
        result.link_count,
        result.elapsed_ms,
        result.filter_used,
        result.reason_code,
    )
