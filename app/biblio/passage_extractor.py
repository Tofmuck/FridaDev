"""Bounded passage extraction for native Biblio / Frida Catalogue.

Lot 4 stays above the GET-only catalogue client and the document resolver.  It
may hold a passage internally on success, but its observability projection is
strictly content-free.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueInvalidParameter,
    CatalogueNotFound,
    CatalogueResponse,
)
from .document_resolver import (
    BiblioDocumentResolver,
    BiblioResolutionResult,
    BiblioResolveRequest,
    LocatorCandidate,
    STATUS_AMBIGUOUS,
    STATUS_CATALOGUE_UNAVAILABLE,
    STATUS_INVALID_REQUEST,
    STATUS_NOT_FOUND,
    STATUS_RESOLVED,
)


STATUS_EXTRACTED = "extracted"
STATUS_EMPTY = "empty"
STATUS_TOO_LONG = "too_long"
STATUS_INCOHERENT_CATALOGUE = "incoherent_catalogue"

REASON_PASSAGE_EXTRACTED = "passage_extracted"
REASON_LOCATOR_REQUIRED = "locator_required_for_passage"
REASON_LOCATOR_CONTEXT_TARGET_MISSING = "locator_context_target_missing"
REASON_RANGE_EXTRACTION_NOT_SUPPORTED = "range_extraction_not_supported"
REASON_RANGE_EXTRACTED = "range_extracted"
REASON_PASSAGE_NOT_FOUND = "passage_not_found"
REASON_PASSAGE_EMPTY = "passage_empty"
REASON_PASSAGE_TOO_LONG = "passage_too_long"
REASON_INCOHERENT_CATALOGUE_RESPONSE = "incoherent_catalogue_response"
REASON_INVALID_PASSAGE_PARAMETER = "invalid_passage_parameter"
REASON_INVALID_CATALOGUE_REQUEST = "invalid_catalogue_request"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_CONTEXT_WINDOW_CHARS = 700
MIN_CONTEXT_WINDOW_CHARS = 80
MAX_CONTEXT_WINDOW_CHARS = 2_000
DEFAULT_MAX_PASSAGE_CHARS = 4_000
MIN_MAX_PASSAGE_CHARS = 80
MAX_MAX_PASSAGE_CHARS = 8_000
MIN_CHAR_OFFSET = 0
MAX_CHAR_OFFSET = 1_000_000
MAX_RANGE_PARAGRAPHS = 40


@dataclass(frozen=True)
class BiblioPassageRequest:
    resolve_request: BiblioResolveRequest = field(default_factory=BiblioResolveRequest)
    char_offset: int = MIN_CHAR_OFFSET
    window_chars: int = DEFAULT_CONTEXT_WINDOW_CHARS
    max_passage_chars: int = DEFAULT_MAX_PASSAGE_CHARS


@dataclass(frozen=True)
class BiblioPassageResult:
    status: str
    reason_code: str
    resolution: BiblioResolutionResult | None = None
    passage: str = ""
    doc_id_short: str = ""
    passage_chars: int = 0
    passage_hash: str = ""
    char_offset: int = 0
    window_chars: int = 0
    max_passage_chars: int = 0
    excerpt_start: int | None = None
    excerpt_end: int | None = None
    text_length: int | None = None
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "resolution": self.resolution.to_observability() if self.resolution else None,
            "doc_id_short": self.doc_id_short,
            "passage_present": self.status == STATUS_EXTRACTED and bool(self.passage),
            "passage_chars": self.passage_chars,
            "passage_hash": self.passage_hash,
            "char_offset": self.char_offset,
            "window_chars": self.window_chars,
            "max_passage_chars": self.max_passage_chars,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "text_length": self.text_length,
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
        }


@dataclass(frozen=True)
class _ExtractionOptions:
    char_offset: int
    window_chars: int
    max_passage_chars: int


class _InvalidPassageParameter(Exception):
    pass


class BiblioPassageExtractor:
    def __init__(
        self,
        client: CatalogueClient,
        *,
        resolver: BiblioDocumentResolver | None = None,
    ) -> None:
        self._client = client
        self._resolver = resolver if resolver is not None else BiblioDocumentResolver(client)

    def extract(self, request: BiblioPassageRequest) -> BiblioPassageResult:
        try:
            options = _extraction_options(request)
        except _InvalidPassageParameter:
            return BiblioPassageResult(
                status=STATUS_INVALID_REQUEST,
                reason_code=REASON_INVALID_PASSAGE_PARAMETER,
            )

        resolution = self._resolver.resolve(request.resolve_request)
        if resolution.status != STATUS_RESOLVED:
            return _from_resolution(resolution, options)
        if not resolution.document or not resolution.locator:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_LOCATOR_REQUIRED,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short if resolution.document else "",
            )
        if resolution.locator_end:
            return self._extract_range(resolution, options)

        target = _context_target(resolution.locator)
        if target is None:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_LOCATOR_CONTEXT_TARGET_MISSING,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=resolution.locator,
            )

        try:
            response = self._context(resolution.document.document_id, target, options)
        except CatalogueNotFound:
            return _result(
                STATUS_NOT_FOUND,
                REASON_PASSAGE_NOT_FOUND,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=resolution.locator,
            )
        except CatalogueInvalidParameter:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_INVALID_CATALOGUE_REQUEST,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=resolution.locator,
            )
        except CatalogueClientError:
            return _result(
                STATUS_CATALOGUE_UNAVAILABLE,
                REASON_CATALOGUE_UNAVAILABLE,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=resolution.locator,
            )

        return _from_context_response(response, resolution, options)

    def _extract_range(
        self,
        resolution: BiblioResolutionResult,
        options: _ExtractionOptions,
    ) -> BiblioPassageResult:
        if not resolution.document or not resolution.locator or not resolution.locator_end:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_RANGE_EXTRACTION_NOT_SUPPORTED,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short if resolution.document else "",
                locator=resolution.locator,
            )

        start = resolution.locator
        end = resolution.locator_end
        paragraph_targets = _range_paragraph_targets(start, end)
        if not paragraph_targets:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_RANGE_EXTRACTION_NOT_SUPPORTED,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=start,
            )

        excerpts: list[str] = []
        range_options = _ExtractionOptions(
            char_offset=0,
            window_chars=max(options.window_chars, MAX_CONTEXT_WINDOW_CHARS),
            max_passage_chars=options.max_passage_chars,
        )
        try:
            for target in paragraph_targets:
                response = self._context(resolution.document.document_id, target, range_options)
                payload = response.payload
                payload_doc_id = _text(payload.get("document_id"))
                if payload_doc_id != resolution.document.document_id:
                    return _result(
                        STATUS_INCOHERENT_CATALOGUE,
                        REASON_INCOHERENT_CATALOGUE_RESPONSE,
                        options=options,
                        resolution=resolution,
                        doc_id_short=resolution.document.doc_id_short,
                        locator=start,
                        payload=payload,
                    )
                passage = _passage_text(payload)
                if passage is None:
                    return _result(
                        STATUS_INCOHERENT_CATALOGUE,
                        REASON_INCOHERENT_CATALOGUE_RESPONSE,
                        options=options,
                        resolution=resolution,
                        doc_id_short=resolution.document.doc_id_short,
                        locator=start,
                        payload=payload,
                    )
                if passage.strip():
                    candidate_excerpts = [*excerpts, passage]
                    candidate_passage = "\n\n".join(candidate_excerpts)
                    if len(candidate_passage) > options.max_passage_chars:
                        return _result(
                            STATUS_TOO_LONG,
                            REASON_PASSAGE_TOO_LONG,
                            options=options,
                            resolution=resolution,
                            doc_id_short=resolution.document.doc_id_short,
                            locator=start,
                            passage_chars=len(candidate_passage),
                            passage_hash=_short_hash(candidate_passage),
                        )
                    excerpts = candidate_excerpts
        except CatalogueNotFound:
            return _result(
                STATUS_NOT_FOUND,
                REASON_PASSAGE_NOT_FOUND,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=start,
            )
        except CatalogueInvalidParameter:
            return _result(
                STATUS_INVALID_REQUEST,
                REASON_INVALID_CATALOGUE_REQUEST,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=start,
            )
        except CatalogueClientError:
            return _result(
                STATUS_CATALOGUE_UNAVAILABLE,
                REASON_CATALOGUE_UNAVAILABLE,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=start,
            )

        passage = "\n\n".join(excerpts)
        if not passage.strip():
            return _result(
                STATUS_EMPTY,
                REASON_PASSAGE_EMPTY,
                options=options,
                resolution=resolution,
                doc_id_short=resolution.document.doc_id_short,
                locator=start,
                passage_chars=len(passage),
                passage_hash=_short_hash(passage),
            )

        return _result(
            STATUS_EXTRACTED,
            REASON_RANGE_EXTRACTED,
            options=options,
            resolution=resolution,
            doc_id_short=resolution.document.doc_id_short,
            locator=start,
            passage=passage,
            passage_chars=len(passage),
            passage_hash=_short_hash(passage),
            payload={
                "document_id": resolution.document.document_id,
                "page_no": start.page_no,
                "para_no": start.para_no,
                "paragraph_id": start.paragraph_id,
                "excerpt_start": 0,
                "excerpt_end": len(passage),
                "text_length": len(passage),
            },
        )

    def _context(
        self,
        doc_id: str,
        target: Mapping[str, int],
        options: _ExtractionOptions,
    ) -> CatalogueResponse:
        if "paragraph_id" in target:
            return self._client.context(
                doc_id,
                paragraph_id=target["paragraph_id"],
                char_offset=options.char_offset,
                window_chars=options.window_chars,
            )
        return self._client.context(
            doc_id,
            page_no=target["page_no"],
            para_no=target["para_no"],
            char_offset=options.char_offset,
            window_chars=options.window_chars,
        )


def _from_resolution(
    resolution: BiblioResolutionResult,
    options: _ExtractionOptions,
) -> BiblioPassageResult:
    status = resolution.status if resolution.status in _NON_EXTRACTABLE_STATUSES else STATUS_INVALID_REQUEST
    return _result(
        status,
        resolution.reason_code,
        options=options,
        resolution=resolution,
        doc_id_short=resolution.document.doc_id_short if resolution.document else "",
        locator=resolution.locator,
    )


_NON_EXTRACTABLE_STATUSES = {
    STATUS_AMBIGUOUS,
    STATUS_NOT_FOUND,
    STATUS_INVALID_REQUEST,
    STATUS_CATALOGUE_UNAVAILABLE,
}


def _from_context_response(
    response: CatalogueResponse,
    resolution: BiblioResolutionResult,
    options: _ExtractionOptions,
) -> BiblioPassageResult:
    document = resolution.document
    locator = resolution.locator
    if not document or not locator:
        return _result(
            STATUS_INCOHERENT_CATALOGUE,
            REASON_INCOHERENT_CATALOGUE_RESPONSE,
            options=options,
            resolution=resolution,
        )

    payload = response.payload
    payload_doc_id = _text(payload.get("document_id"))
    if payload_doc_id != document.document_id:
        return _result(
            STATUS_INCOHERENT_CATALOGUE,
            REASON_INCOHERENT_CATALOGUE_RESPONSE,
            options=options,
            resolution=resolution,
            doc_id_short=document.doc_id_short,
            locator=locator,
            payload=payload,
        )

    passage = _passage_text(payload)
    if passage is None:
        return _result(
            STATUS_INCOHERENT_CATALOGUE,
            REASON_INCOHERENT_CATALOGUE_RESPONSE,
            options=options,
            resolution=resolution,
            doc_id_short=document.doc_id_short,
            locator=locator,
            payload=payload,
        )
    passage_chars = len(passage)
    passage_hash = _short_hash(passage) if passage else ""
    if not passage.strip():
        return _result(
            STATUS_EMPTY,
            REASON_PASSAGE_EMPTY,
            options=options,
            resolution=resolution,
            doc_id_short=document.doc_id_short,
            locator=locator,
            payload=payload,
            passage_chars=passage_chars,
            passage_hash=passage_hash,
        )
    if passage_chars > options.max_passage_chars:
        return _result(
            STATUS_TOO_LONG,
            REASON_PASSAGE_TOO_LONG,
            options=options,
            resolution=resolution,
            doc_id_short=document.doc_id_short,
            locator=locator,
            payload=payload,
            passage_chars=passage_chars,
            passage_hash=passage_hash,
        )
    return _result(
        STATUS_EXTRACTED,
        REASON_PASSAGE_EXTRACTED,
        options=options,
        resolution=resolution,
        doc_id_short=document.doc_id_short,
        locator=locator,
        payload=payload,
        passage=passage,
        passage_chars=passage_chars,
        passage_hash=passage_hash,
    )


def _result(
    status: str,
    reason_code: str,
    *,
    options: _ExtractionOptions,
    resolution: BiblioResolutionResult | None = None,
    doc_id_short: str = "",
    locator: LocatorCandidate | None = None,
    payload: Mapping[str, Any] | None = None,
    passage: str = "",
    passage_chars: int = 0,
    passage_hash: str = "",
) -> BiblioPassageResult:
    data = payload or {}
    return BiblioPassageResult(
        status=status,
        reason_code=reason_code,
        resolution=resolution,
        passage=passage,
        doc_id_short=doc_id_short,
        passage_chars=passage_chars or (len(passage) if passage else 0),
        passage_hash=passage_hash,
        char_offset=options.char_offset,
        window_chars=options.window_chars,
        max_passage_chars=options.max_passage_chars,
        excerpt_start=_optional_int(data.get("excerpt_start")),
        excerpt_end=_optional_int(data.get("excerpt_end")),
        text_length=_optional_int(data.get("text_length")),
        page_no=_optional_int(data.get("page_no")) if data else (locator.page_no if locator else None),
        para_no=_optional_int(data.get("para_no")) if data else (locator.para_no if locator else None),
        paragraph_id=_optional_int(data.get("paragraph_id")) if data else (locator.paragraph_id if locator else None),
    )


def _context_target(locator: LocatorCandidate) -> dict[str, int] | None:
    if type(locator.paragraph_id) is int:
        return {"paragraph_id": locator.paragraph_id}
    if type(locator.page_no) is int and type(locator.para_no) is int:
        return {"page_no": locator.page_no, "para_no": locator.para_no}
    return None


def _range_paragraph_targets(start: LocatorCandidate, end: LocatorCandidate) -> list[dict[str, int]]:
    if start.document_id != end.document_id:
        return []
    if start.page_no is None or end.page_no is None or start.para_no is None or end.para_no is None:
        return []
    if start.page_no != end.page_no:
        return []
    if end.para_no < start.para_no:
        return []
    paragraph_count = end.para_no - start.para_no + 1
    if paragraph_count < 1 or paragraph_count > MAX_RANGE_PARAGRAPHS:
        return []
    return [{"page_no": start.page_no, "para_no": para_no} for para_no in range(start.para_no, end.para_no + 1)]


def _passage_text(payload: Mapping[str, Any]) -> str | None:
    for key in ("excerpt", "text", "context"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _extraction_options(request: BiblioPassageRequest) -> _ExtractionOptions:
    return _ExtractionOptions(
        char_offset=_bounded_int(
            request.char_offset,
            name="char_offset",
            minimum=MIN_CHAR_OFFSET,
            maximum=MAX_CHAR_OFFSET,
        ),
        window_chars=_bounded_int(
            request.window_chars,
            name="window_chars",
            minimum=MIN_CONTEXT_WINDOW_CHARS,
            maximum=MAX_CONTEXT_WINDOW_CHARS,
        ),
        max_passage_chars=_bounded_int(
            request.max_passage_chars,
            name="max_passage_chars",
            minimum=MIN_MAX_PASSAGE_CHARS,
            maximum=MAX_MAX_PASSAGE_CHARS,
        ),
    )


def _bounded_int(value: Any, *, name: str, minimum: int, maximum: int) -> int:
    integer = _strict_int_parameter(value, name=name)
    if integer < minimum or integer > maximum:
        raise _InvalidPassageParameter(f"{name}_out_of_range")
    return integer


def _strict_int_parameter(value: Any, *, name: str) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise _InvalidPassageParameter(f"{name}_must_be_integer")


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]
