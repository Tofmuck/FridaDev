from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Any, Iterable, Mapping

import requests

from tools import adobe_docs_links
from tools import adobe_docs_passages
from tools import adobe_docs_reader
from tools import adobe_docs_sources


SPECIALIZATION_PROFILE_ADOBE = 'adobe'

STATUS_NOT_REQUESTED = 'not_requested'
STATUS_SUCCESS = 'success'
STATUS_PARTIAL = 'partial'
STATUS_INSUFFICIENT = 'insufficient'
STATUS_ERROR = 'error'

ERROR_ADOBE_PRODUCT_REQUIRED = 'adobe_product_required'
ERROR_ADOBE_PRODUCT_INVALID = 'adobe_product_invalid'

REASON_ADOBE_PROFILE_OWNS_RETRIEVAL = 'adobe_profile_owns_retrieval'
REASON_ADOBE_NOT_REQUESTED = 'adobe_not_requested'
REASON_ADOBE_PRODUCT_REQUIRED = ERROR_ADOBE_PRODUCT_REQUIRED
REASON_ADOBE_PRODUCT_INVALID = ERROR_ADOBE_PRODUCT_INVALID
REASON_ADOBE_PIPELINE_EXCEPTION = 'adobe_pipeline_exception'
REASON_ADOBE_READ_ERROR = 'adobe_read_error'
REASON_ADOBE_READ_PARTIAL = 'adobe_read_partial'
REASON_ADOBE_NO_PASSAGE_SELECTED = 'adobe_no_passage_selected'

DEFAULT_SEED_URL_LIMIT = 3
DEFAULT_FOLLOW_LINK_LIMIT = 4
DEFAULT_CRAWL_PAGE_LIMIT = 5
DEFAULT_PASSAGE_COUNT = 6
DEFAULT_PROMPT_BUDGET_CHARS = 5000


@dataclass(frozen=True, repr=False)
class AdobeDocsRequest:
    active: bool
    product: str = ''
    reason_code: str = ''
    error_code: str = ''
    web_search_requested: bool = False

    def __repr__(self) -> str:
        return (
            "AdobeDocsRequest("
            f"active={self.active!r}, product={self.product!r}, "
            f"reason_code={self.reason_code!r}, error_code={self.error_code!r}, "
            f"web_search_requested={self.web_search_requested!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'active': self.active,
            'product': self.product,
            'reason_code': self.reason_code,
            'error_code': self.error_code,
            'web_search_requested': self.web_search_requested,
        }


@dataclass(frozen=True, repr=False)
class AdobeDocsSourceReference:
    product: str
    source_type: str
    canonical_url: str
    url_sha256_12: str

    def __repr__(self) -> str:
        return (
            "AdobeDocsSourceReference("
            f"product={self.product!r}, source_type={self.source_type!r}, "
            f"url_sha256_12={self.url_sha256_12!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'product': self.product,
            'source_type': self.source_type,
            'url_sha256_12': self.url_sha256_12,
        }


@dataclass(frozen=True, repr=False)
class AdobeDocsContext:
    active: bool
    product: str = ''
    status: str = STATUS_NOT_REQUESTED
    evidence: str = adobe_docs_passages.EVIDENCE_INSUFFICIENT
    passages: tuple[adobe_docs_passages.AdobePassage, ...] = ()
    sources: tuple[AdobeDocsSourceReference, ...] = ()
    seed_count: int = 0
    crawled_page_count: int = 0
    link_candidate_count: int = 0
    ranked_link_count: int = 0
    selected_passage_count: int = 0
    injected_chars: int = 0
    elapsed_ms: int = 0
    source_types: tuple[str, ...] = ()
    url_sha256_12: tuple[str, ...] = ()
    read_statuses: tuple[str, ...] = ()
    read_elapsed_ms: tuple[int, ...] = ()
    read_chars: tuple[int, ...] = ()
    read_headings: tuple[int, ...] = ()
    read_link_counts: tuple[int, ...] = ()
    reason_codes: tuple[str, ...] = ()
    error_classes: tuple[str, ...] = ()

    def __repr__(self) -> str:
        return (
            "AdobeDocsContext("
            f"active={self.active!r}, product={self.product!r}, status={self.status!r}, "
            f"evidence={self.evidence!r}, seed_count={self.seed_count!r}, "
            f"crawled_page_count={self.crawled_page_count!r}, "
            f"link_candidate_count={self.link_candidate_count!r}, "
            f"selected_passage_count={self.selected_passage_count!r}, "
            f"injected_chars={self.injected_chars!r}, elapsed_ms={self.elapsed_ms!r}, "
            f"source_types={self.source_types!r}, url_hash_count={len(self.url_sha256_12)!r}, "
            f"reason_codes={self.reason_codes!r}, error_classes={self.error_classes!r})"
        )

    def as_content_free_dict(self) -> dict[str, object]:
        return {
            'active': self.active,
            'product': self.product,
            'status': self.status,
            'evidence': self.evidence,
            'seed_count': self.seed_count,
            'crawled_page_count': self.crawled_page_count,
            'link_candidate_count': self.link_candidate_count,
            'ranked_link_count': self.ranked_link_count,
            'selected_passage_count': self.selected_passage_count,
            'injected_chars': self.injected_chars,
            'elapsed_ms': self.elapsed_ms,
            'source_types': list(self.source_types),
            'url_sha256_12': list(self.url_sha256_12),
            'read_statuses': list(self.read_statuses),
            'read_elapsed_ms': list(self.read_elapsed_ms),
            'read_chars': list(self.read_chars),
            'read_headings': list(self.read_headings),
            'read_link_counts': list(self.read_link_counts),
            'reason_codes': list(self.reason_codes),
            'error_classes': list(self.error_classes),
            'sources': [source.as_content_free_dict() for source in self.sources],
        }


def resolve_adobe_request(payload: Mapping[str, Any] | None) -> AdobeDocsRequest:
    data = payload if isinstance(payload, Mapping) else {}
    profile = str(data.get('specialization_profile') or '').strip().lower()
    web_search_requested = bool(data.get('web_search'))
    if profile != SPECIALIZATION_PROFILE_ADOBE:
        return AdobeDocsRequest(
            active=False,
            reason_code=REASON_ADOBE_NOT_REQUESTED,
            web_search_requested=web_search_requested,
        )

    product = str(data.get('adobe_product') or '').strip().lower()
    if not product:
        return AdobeDocsRequest(
            active=True,
            reason_code=REASON_ADOBE_PRODUCT_REQUIRED,
            error_code=ERROR_ADOBE_PRODUCT_REQUIRED,
            web_search_requested=web_search_requested,
        )
    try:
        normalized_product = adobe_docs_sources.validate_product(product)
    except ValueError:
        return AdobeDocsRequest(
            active=True,
            product=product,
            reason_code=REASON_ADOBE_PRODUCT_INVALID,
            error_code=ERROR_ADOBE_PRODUCT_INVALID,
            web_search_requested=web_search_requested,
        )
    return AdobeDocsRequest(
        active=True,
        product=normalized_product,
        reason_code=REASON_ADOBE_PROFILE_OWNS_RETRIEVAL,
        web_search_requested=web_search_requested,
    )


def not_requested_context() -> AdobeDocsContext:
    return AdobeDocsContext(
        active=False,
        status=STATUS_NOT_REQUESTED,
        reason_codes=(REASON_ADOBE_NOT_REQUESTED,),
    )


def error_context(
    *,
    product: str,
    reason_code: str,
    error_class: str = '',
) -> AdobeDocsContext:
    return AdobeDocsContext(
        active=True,
        product=str(product or ''),
        status=STATUS_ERROR,
        evidence=adobe_docs_passages.EVIDENCE_INSUFFICIENT,
        reason_codes=_dedupe_codes((REASON_ADOBE_PROFILE_OWNS_RETRIEVAL, reason_code)),
        error_classes=_dedupe_codes((error_class,)),
    )


def build_adobe_context(
    question: str,
    product: str,
    *,
    requests_module: Any = requests,
    reader_module: Any = adobe_docs_reader,
    links_module: Any = adobe_docs_links,
    passages_module: Any = adobe_docs_passages,
    sources_module: Any = adobe_docs_sources,
    seed_url_limit: int = DEFAULT_SEED_URL_LIMIT,
    follow_link_limit: int = DEFAULT_FOLLOW_LINK_LIMIT,
    crawl_page_limit: int = DEFAULT_CRAWL_PAGE_LIMIT,
    passage_count: int = DEFAULT_PASSAGE_COUNT,
    prompt_budget_chars: int = DEFAULT_PROMPT_BUDGET_CHARS,
) -> AdobeDocsContext:
    started = time.monotonic()
    try:
        normalized_product = sources_module.validate_product(product)
    except ValueError:
        return error_context(
            product=str(product or ''),
            reason_code=REASON_ADOBE_PRODUCT_INVALID,
            error_class='ValueError',
        )

    page_limit = _safe_positive_int(crawl_page_limit, DEFAULT_CRAWL_PAGE_LIMIT)
    read_results: list[Any] = []
    read_urls: set[str] = set()
    reason_codes: list[str] = [REASON_ADOBE_PROFILE_OWNS_RETRIEVAL]
    error_classes: list[str] = []

    seeds = tuple(sources_module.sources_for_product(normalized_product))[
        : _safe_positive_int(seed_url_limit, DEFAULT_SEED_URL_LIMIT)
    ]
    for source in seeds:
        if len(read_results) >= page_limit:
            break
        result = reader_module.read_adobe_url(
            source.url,
            normalized_product,
            source.source_type,
            requests_module=requests_module,
        )
        read_results.append(result)
        read_urls.add(str(getattr(result, 'canonical_url', '') or source.url))
        reason_codes.extend(_sequence(getattr(result, 'reason_codes', ())))
        if getattr(result, 'error_class', ''):
            error_classes.append(str(getattr(result, 'error_class') or ''))

    extracted_links = []
    for result in read_results:
        if str(getattr(result, 'status', '') or '') != adobe_docs_reader.STATUS_SUCCESS:
            continue
        extracted_links.extend(
            links_module.extract_adobe_links(
                str(getattr(result, 'markdown', '') or ''),
                str(getattr(result, 'canonical_url', '') or ''),
                normalized_product,
            )
        )

    ranked_links = links_module.rank_adobe_links(
        str(question or ''),
        extracted_links,
        normalized_product,
        limit=_safe_positive_int(follow_link_limit, DEFAULT_FOLLOW_LINK_LIMIT),
    )
    for link in ranked_links:
        if len(read_results) >= page_limit:
            break
        canonical_url = str(getattr(link, 'canonical_url', '') or '')
        if not canonical_url or canonical_url in read_urls:
            continue
        result = reader_module.read_adobe_url(
            canonical_url,
            normalized_product,
            str(getattr(link, 'source_type', '') or ''),
            requests_module=requests_module,
        )
        read_results.append(result)
        read_urls.add(str(getattr(result, 'canonical_url', '') or canonical_url))
        reason_codes.extend(_sequence(getattr(result, 'reason_codes', ())))
        if getattr(result, 'error_class', ''):
            error_classes.append(str(getattr(result, 'error_class') or ''))

    selection = passages_module.select_adobe_passages(
        str(question or ''),
        read_results,
        passage_count=_safe_positive_int(passage_count, DEFAULT_PASSAGE_COUNT),
        prompt_budget_chars=_safe_positive_int(prompt_budget_chars, DEFAULT_PROMPT_BUDGET_CHARS),
    )
    reason_codes.extend(_sequence(getattr(selection, 'reason_codes', ())))

    success_count = sum(1 for result in read_results if str(getattr(result, 'status', '') or '') == adobe_docs_reader.STATUS_SUCCESS)
    if success_count <= 0:
        status = STATUS_ERROR
        evidence = adobe_docs_passages.EVIDENCE_INSUFFICIENT
        reason_codes.append(REASON_ADOBE_READ_ERROR)
    else:
        evidence = str(getattr(selection, 'evidence', '') or adobe_docs_passages.EVIDENCE_INSUFFICIENT)
        if evidence == adobe_docs_passages.EVIDENCE_SUFFICIENT:
            status = STATUS_SUCCESS
        elif evidence == adobe_docs_passages.EVIDENCE_PARTIAL:
            status = STATUS_PARTIAL
            reason_codes.append(REASON_ADOBE_READ_PARTIAL)
        else:
            status = STATUS_INSUFFICIENT
            reason_codes.append(REASON_ADOBE_NO_PASSAGE_SELECTED)

    source_refs = _source_refs_from_passages_or_reads(selection.passages, read_results)
    return AdobeDocsContext(
        active=True,
        product=normalized_product,
        status=status,
        evidence=evidence,
        passages=tuple(selection.passages),
        sources=tuple(source_refs),
        seed_count=len(seeds),
        crawled_page_count=len(read_results),
        link_candidate_count=len(extracted_links),
        ranked_link_count=len(ranked_links),
        selected_passage_count=int(getattr(selection, 'selected_count', 0) or 0),
        injected_chars=int(getattr(selection, 'total_chars', 0) or 0),
        elapsed_ms=_elapsed_ms(started),
        source_types=_dedupe_codes(_source_types_from_refs(source_refs)),
        url_sha256_12=_dedupe_codes(ref.url_sha256_12 for ref in source_refs),
        read_statuses=tuple(str(getattr(result, 'status', '') or '') for result in read_results),
        read_elapsed_ms=tuple(_safe_non_negative_int(getattr(result, 'elapsed_ms', 0)) for result in read_results),
        read_chars=tuple(_safe_non_negative_int(getattr(result, 'chars', 0)) for result in read_results),
        read_headings=tuple(_safe_non_negative_int(getattr(result, 'headings', 0)) for result in read_results),
        read_link_counts=tuple(_safe_non_negative_int(getattr(result, 'link_count', 0)) for result in read_results),
        reason_codes=_dedupe_codes(reason_codes),
        error_classes=_dedupe_codes(error_classes),
    )


def _source_refs_from_passages_or_reads(passages: Iterable[Any], read_results: Iterable[Any]) -> list[AdobeDocsSourceReference]:
    refs: list[AdobeDocsSourceReference] = []
    seen: set[str] = set()
    for passage in passages:
        canonical_url = str(getattr(passage, 'canonical_url', '') or '')
        if not canonical_url or canonical_url in seen:
            continue
        seen.add(canonical_url)
        refs.append(
            AdobeDocsSourceReference(
                product=str(getattr(passage, 'product', '') or ''),
                source_type=str(getattr(passage, 'source_type', '') or ''),
                canonical_url=canonical_url,
                url_sha256_12=str(getattr(passage, 'url_sha256_12', '') or _sha256_12(canonical_url)),
            )
        )
    if refs:
        return refs
    for result in read_results:
        canonical_url = str(getattr(result, 'canonical_url', '') or '')
        if not canonical_url or canonical_url in seen:
            continue
        seen.add(canonical_url)
        refs.append(
            AdobeDocsSourceReference(
                product=str(getattr(result, 'product', '') or ''),
                source_type=str(getattr(result, 'source_type', '') or ''),
                canonical_url=canonical_url,
                url_sha256_12=str(getattr(result, 'url_sha256_12', '') or _sha256_12(canonical_url)),
            )
        )
    return refs


def _source_types_from_refs(refs: Iterable[AdobeDocsSourceReference]) -> tuple[str, ...]:
    return tuple(ref.source_type for ref in refs if ref.source_type)


def _safe_positive_int(value: int, default: int) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        parsed = 0
    return parsed if parsed > 0 else default


def _safe_non_negative_int(value: Any) -> int:
    try:
        parsed = int(value or 0)
    except (TypeError, ValueError):
        return 0
    return max(0, parsed)


def _sequence(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple, set)):
        return tuple(str(item or '') for item in value if str(item or ''))
    text = str(value or '').strip()
    return (text,) if text else ()


def _sha256_12(value: str) -> str:
    import hashlib

    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.monotonic() - started) * 1000))


def _dedupe_codes(codes: Iterable[str]) -> tuple[str, ...]:
    seen: set[str] = set()
    result: list[str] = []
    for code in codes:
        text = str(code or '').strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return tuple(result)
