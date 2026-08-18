"""Mechanical extraction from an already resolved native Biblio passage.

This boundary consumes a resolved document/locator pair and only reads
Catalogue context or page endpoints.  Document and locator search stay in the
public passage extractor facade and its resolver.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueInvalidParameter,
    CatalogueNotFound,
    CatalogueResponse,
)
from .document_resolver import (
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
STATUS_SEGMENT_EXTRACTED = "segment_extracted"
STATUS_EMPTY = "empty"
STATUS_TOO_LONG = "too_long"
STATUS_INCOHERENT_CATALOGUE = "incoherent_catalogue"

REASON_PASSAGE_EXTRACTED = "passage_extracted"
REASON_LOCATOR_REQUIRED = "locator_required_for_passage"
REASON_LOCATOR_CONTEXT_TARGET_MISSING = "locator_context_target_missing"
REASON_RANGE_EXTRACTION_NOT_SUPPORTED = "range_extraction_not_supported"
REASON_RANGE_EXTRACTED = "range_extracted"
REASON_RANGE_SEGMENT_EXTRACTED = "range_segment_extracted"
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
MAX_RANGE_PAGES = 12


@dataclass(frozen=True)
class BiblioCanonicalIntervalHint:
    kind: str = "point"
    mode: str = "single_locator"
    state: str = "complete"
    start_page_no: int | None = None
    start_para_no: int | None = None
    start_paragraph_id: int | None = None
    end_page_no: int | None = None
    end_para_no: int | None = None
    end_paragraph_id: int | None = None
    requested_end_page_no: int | None = None
    requested_end_para_no: int | None = None
    requested_end_paragraph_id: int | None = None
    next_page_no: int | None = None
    next_para_no: int | None = None
    next_paragraph_id: int | None = None
    page_span: int | None = None
    paragraph_span: int | None = None

    def to_observability(self) -> dict[str, Any]:
        observed = {
            "kind": str(self.kind or "").strip(),
            "mode": str(self.mode or "").strip(),
            "state": str(self.state or "").strip(),
            "start_page_no": self.start_page_no,
            "start_para_no": self.start_para_no,
            "start_paragraph_id": self.start_paragraph_id,
            "end_page_no": self.end_page_no,
            "end_para_no": self.end_para_no,
            "end_paragraph_id": self.end_paragraph_id,
            "requested_end_page_no": self.requested_end_page_no,
            "requested_end_para_no": self.requested_end_para_no,
            "requested_end_paragraph_id": self.requested_end_paragraph_id,
            "next_page_no": self.next_page_no,
            "next_para_no": self.next_para_no,
            "next_paragraph_id": self.next_paragraph_id,
            "page_span": self.page_span,
            "paragraph_span": self.paragraph_span,
        }
        return {key: value for key, value in observed.items() if value not in ("", None)}


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
    interval_hint: BiblioCanonicalIntervalHint | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "resolution": self.resolution.to_observability() if self.resolution else None,
            "doc_id_short": self.doc_id_short,
            "passage_present": self.status in _EXTRACTED_STATUSES and bool(self.passage),
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
            "interval_hint": self.interval_hint.to_observability() if self.interval_hint else None,
        }


_EXTRACTED_STATUSES = {STATUS_EXTRACTED, STATUS_SEGMENT_EXTRACTED}


@dataclass(frozen=True)
class PassageExtractionOptions:
    char_offset: int
    window_chars: int
    max_passage_chars: int


class InvalidPassageParameter(Exception):
    pass


class ResolvedPassageExtractor:
    def __init__(self, client: CatalogueClient) -> None:
        self._client = client

    def extract(
        self,
        resolution: BiblioResolutionResult,
        options: PassageExtractionOptions,
    ) -> BiblioPassageResult:
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
        options: PassageExtractionOptions,
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
        if paragraph_targets:
            return self._extract_same_page_range(resolution, options, start, paragraph_targets)

        page_numbers = _range_page_numbers(start, end)
        if page_numbers:
            return self._extract_multi_page_range(resolution, options, start, end, page_numbers)

        return _result(
            STATUS_INVALID_REQUEST,
            REASON_RANGE_EXTRACTION_NOT_SUPPORTED,
            options=options,
            resolution=resolution,
            doc_id_short=resolution.document.doc_id_short,
            locator=start,
        )

    def _extract_same_page_range(
        self,
        resolution: BiblioResolutionResult,
        options: PassageExtractionOptions,
        start: LocatorCandidate,
        paragraph_targets: list[dict[str, int]],
    ) -> BiblioPassageResult:
        excerpts: list[str] = []
        included_targets: list[dict[str, int]] = []
        range_options = PassageExtractionOptions(
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
                    observed_target = _target_from_payload(payload, fallback=target)
                    candidate_excerpts = [*excerpts, passage]
                    candidate_passage = "\n\n".join(candidate_excerpts)
                    if len(candidate_passage) > options.max_passage_chars:
                        if excerpts and included_targets:
                            segment_passage = "\n\n".join(excerpts)
                            return _result(
                                STATUS_SEGMENT_EXTRACTED,
                                REASON_RANGE_SEGMENT_EXTRACTED,
                                options=options,
                                resolution=resolution,
                                doc_id_short=resolution.document.doc_id_short,
                                locator=start,
                                passage=segment_passage,
                                passage_chars=len(segment_passage),
                                passage_hash=_short_hash(segment_passage),
                                payload=_payload_for_target(
                                    resolution.document.document_id,
                                    included_targets[0],
                                    segment_passage,
                                ),
                                interval_hint=_range_segment_interval_hint(
                                    mode="same_page_range_segment",
                                    start=start,
                                    segment_end=included_targets[-1],
                                    requested_end=resolution.locator_end,
                                    next_target=observed_target,
                                    page_span=_page_span(included_targets),
                                    paragraph_span=len(included_targets),
                                ),
                            )
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
                    included_targets.append(observed_target)
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
            interval_hint=_range_interval_hint(
                mode="same_page_range",
                start=start,
                end=resolution.locator_end,
                page_span=1,
                paragraph_span=len(paragraph_targets),
            ),
        )

    def _extract_multi_page_range(
        self,
        resolution: BiblioResolutionResult,
        options: PassageExtractionOptions,
        start: LocatorCandidate,
        end: LocatorCandidate,
        page_numbers: list[int],
    ) -> BiblioPassageResult:
        excerpts: list[str] = []
        included_targets: list[dict[str, int]] = []
        selected_paragraph_count = 0
        try:
            for page_no in page_numbers:
                response = self._page(resolution.document.document_id, page_no)
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
                if _optional_int(payload.get("page_no")) != page_no:
                    return _result(
                        STATUS_INCOHERENT_CATALOGUE,
                        REASON_INCOHERENT_CATALOGUE_RESPONSE,
                        options=options,
                        resolution=resolution,
                        doc_id_short=resolution.document.doc_id_short,
                        locator=start,
                        payload=payload,
                    )

                page_paragraphs = _page_paragraphs(payload, page_no=page_no, start=start, end=end)
                if page_paragraphs is None:
                    return _result(
                        STATUS_INCOHERENT_CATALOGUE,
                        REASON_INCOHERENT_CATALOGUE_RESPONSE,
                        options=options,
                        resolution=resolution,
                        doc_id_short=resolution.document.doc_id_short,
                        locator=start,
                        payload=payload,
                    )

                selected_paragraph_count += len(page_paragraphs)
                if selected_paragraph_count > MAX_RANGE_PARAGRAPHS:
                    return _result(
                        STATUS_INVALID_REQUEST,
                        REASON_RANGE_EXTRACTION_NOT_SUPPORTED,
                        options=options,
                        resolution=resolution,
                        doc_id_short=resolution.document.doc_id_short,
                        locator=start,
                    )

                for paragraph in page_paragraphs:
                    text = _text(paragraph.get("text"))
                    if text.strip():
                        candidate_excerpts = [*excerpts, text]
                        candidate_passage = "\n\n".join(candidate_excerpts)
                        if len(candidate_passage) > options.max_passage_chars:
                            if excerpts and included_targets:
                                segment_passage = "\n\n".join(excerpts)
                                return _result(
                                    STATUS_SEGMENT_EXTRACTED,
                                    REASON_RANGE_SEGMENT_EXTRACTED,
                                    options=options,
                                    resolution=resolution,
                                    doc_id_short=resolution.document.doc_id_short,
                                    locator=start,
                                    passage=segment_passage,
                                    passage_chars=len(segment_passage),
                                    passage_hash=_short_hash(segment_passage),
                                    payload=_payload_for_target(
                                        resolution.document.document_id,
                                        included_targets[0],
                                        segment_passage,
                                    ),
                                    interval_hint=_range_segment_interval_hint(
                                        mode="multi_page_range_segment",
                                        start=start,
                                        segment_end=included_targets[-1],
                                        requested_end=end,
                                        next_target=_target_from_paragraph(paragraph),
                                        page_span=_page_span(included_targets),
                                        paragraph_span=len(included_targets),
                                    ),
                                )
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
                        included_targets.append(_target_from_paragraph(paragraph))
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
            interval_hint=_range_interval_hint(
                mode="multi_page_range",
                start=start,
                end=end,
                page_span=len(page_numbers),
                paragraph_span=selected_paragraph_count,
            ),
        )

    def _context(
        self,
        doc_id: str,
        target: Mapping[str, int],
        options: PassageExtractionOptions,
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

    def _page(self, doc_id: str, page_no: int) -> CatalogueResponse:
        return self._client.page(doc_id, page_no)


def passage_result_from_resolution(
    resolution: BiblioResolutionResult,
    options: PassageExtractionOptions,
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
    options: PassageExtractionOptions,
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
    options: PassageExtractionOptions,
    resolution: BiblioResolutionResult | None = None,
    doc_id_short: str = "",
    locator: LocatorCandidate | None = None,
    payload: Mapping[str, Any] | None = None,
    passage: str = "",
    passage_chars: int = 0,
    passage_hash: str = "",
    interval_hint: BiblioCanonicalIntervalHint | None = None,
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
        interval_hint=interval_hint or _point_interval_hint(locator),
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


def _range_page_numbers(start: LocatorCandidate, end: LocatorCandidate) -> list[int]:
    if start.document_id != end.document_id:
        return []
    if start.page_no is None or end.page_no is None or start.para_no is None or end.para_no is None:
        return []
    if start.page_no == end.page_no:
        return []
    if start.order_index is not None and end.order_index is not None and end.order_index < start.order_index:
        return []
    if end.page_no < start.page_no:
        return []
    page_count = end.page_no - start.page_no + 1
    if page_count < 2 or page_count > MAX_RANGE_PAGES:
        return []
    return list(range(start.page_no, end.page_no + 1))


def _page_paragraphs(
    payload: Mapping[str, Any],
    *,
    page_no: int,
    start: LocatorCandidate,
    end: LocatorCandidate,
) -> list[dict[str, Any]] | None:
    raw_paragraphs = payload.get("paragraphs")
    if not isinstance(raw_paragraphs, list):
        return None

    selected: list[dict[str, Any]] = []
    start_found = page_no != start.page_no
    end_found = page_no != end.page_no
    for row in raw_paragraphs:
        if not isinstance(row, Mapping):
            continue
        para_no = _optional_int(row.get("para_no"))
        if para_no is None:
            continue
        text = str(row.get("text") or "")
        if page_no == start.page_no and para_no == start.para_no:
            start_found = True
        if page_no == end.page_no and para_no == end.para_no:
            end_found = True
        if page_no == start.page_no and para_no < start.para_no:
            continue
        if page_no == end.page_no and para_no > end.para_no:
            continue
        selected.append(
            {
                "page_no": page_no,
                "para_no": para_no,
                "paragraph_id": _optional_int(row.get("paragraph_id")),
                "text": text,
            }
        )

    if not start_found or not end_found:
        return None
    return selected


def _passage_text(payload: Mapping[str, Any]) -> str | None:
    for key in ("excerpt", "text", "context"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def passage_extraction_options(request: BiblioPassageRequest) -> PassageExtractionOptions:
    return PassageExtractionOptions(
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
        raise InvalidPassageParameter(f"{name}_out_of_range")
    return integer


def _strict_int_parameter(value: Any, *, name: str) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    raise InvalidPassageParameter(f"{name}_must_be_integer")


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _short_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _point_interval_hint(locator: LocatorCandidate | None) -> BiblioCanonicalIntervalHint | None:
    if locator is None:
        return None
    if locator.page_no is None and locator.para_no is None and locator.paragraph_id is None:
        return None
    return BiblioCanonicalIntervalHint(
        kind="point",
        mode="single_locator",
        start_page_no=locator.page_no,
        start_para_no=locator.para_no,
        start_paragraph_id=locator.paragraph_id,
    )


def _range_interval_hint(
    *,
    mode: str,
    start: LocatorCandidate,
    end: LocatorCandidate,
    page_span: int,
    paragraph_span: int,
) -> BiblioCanonicalIntervalHint:
    return BiblioCanonicalIntervalHint(
        kind="range",
        mode=mode,
        state="complete",
        start_page_no=start.page_no,
        start_para_no=start.para_no,
        start_paragraph_id=start.paragraph_id,
        end_page_no=end.page_no,
        end_para_no=end.para_no,
        end_paragraph_id=end.paragraph_id,
        page_span=page_span,
        paragraph_span=paragraph_span,
    )


def _range_segment_interval_hint(
    *,
    mode: str,
    start: LocatorCandidate,
    segment_end: Mapping[str, int],
    requested_end: LocatorCandidate,
    next_target: Mapping[str, int],
    page_span: int,
    paragraph_span: int,
) -> BiblioCanonicalIntervalHint:
    return BiblioCanonicalIntervalHint(
        kind="range",
        mode=mode,
        state="segment",
        start_page_no=start.page_no,
        start_para_no=start.para_no,
        start_paragraph_id=start.paragraph_id,
        end_page_no=_optional_int(segment_end.get("page_no")),
        end_para_no=_optional_int(segment_end.get("para_no")),
        end_paragraph_id=_optional_int(segment_end.get("paragraph_id")),
        requested_end_page_no=requested_end.page_no,
        requested_end_para_no=requested_end.para_no,
        requested_end_paragraph_id=requested_end.paragraph_id,
        next_page_no=_optional_int(next_target.get("page_no")),
        next_para_no=_optional_int(next_target.get("para_no")),
        next_paragraph_id=_optional_int(next_target.get("paragraph_id")),
        page_span=page_span,
        paragraph_span=paragraph_span,
    )


def _target_from_payload(payload: Mapping[str, Any], *, fallback: Mapping[str, int]) -> dict[str, int]:
    target = {
        "page_no": _optional_int(payload.get("page_no")) or _optional_int(fallback.get("page_no")),
        "para_no": _optional_int(payload.get("para_no")) or _optional_int(fallback.get("para_no")),
        "paragraph_id": _optional_int(payload.get("paragraph_id")) or _optional_int(fallback.get("paragraph_id")),
    }
    return {key: value for key, value in target.items() if value is not None}


def _target_from_paragraph(paragraph: Mapping[str, Any]) -> dict[str, int]:
    target = {
        "page_no": _optional_int(paragraph.get("page_no")),
        "para_no": _optional_int(paragraph.get("para_no")),
        "paragraph_id": _optional_int(paragraph.get("paragraph_id")),
    }
    return {key: value for key, value in target.items() if value is not None}


def _payload_for_target(document_id: str, target: Mapping[str, int], passage: str) -> dict[str, Any]:
    return {
        "document_id": document_id,
        "page_no": _optional_int(target.get("page_no")),
        "para_no": _optional_int(target.get("para_no")),
        "paragraph_id": _optional_int(target.get("paragraph_id")),
        "excerpt_start": 0,
        "excerpt_end": len(passage),
        "text_length": len(passage),
    }


def _page_span(targets: Sequence[Mapping[str, int]]) -> int:
    pages = {
        page
        for page in (_optional_int(target.get("page_no")) for target in targets)
        if page is not None
    }
    return len(pages)
