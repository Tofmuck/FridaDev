"""Document resolver for native Biblio / Frida Catalogue.

Lot 3 stays above the GET-only catalogue client.  It resolves document and
locator references into compact, content-free statuses; it never extracts
passages, calls context, writes to Catalogue, or touches chat state.
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


STATUS_RESOLVED = "resolved"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NOT_FOUND = "not_found"
STATUS_INVALID_REQUEST = "invalid_request"
STATUS_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

REASON_DOCUMENT_RESOLVED = "document_resolved"
REASON_DOCUMENT_AND_LOCATOR_RESOLVED = "document_and_locator_resolved"
REASON_DOCUMENT_AND_LOCATOR_RANGE_RESOLVED = "document_and_locator_range_resolved"
REASON_EMPTY_REQUEST = "empty_request"
REASON_LOCATOR_REQUIRES_DOCUMENT = "locator_requires_document"
REASON_LOCATOR_RANGE_REQUIRES_START = "locator_range_requires_start"
REASON_DOCUMENT_NOT_FOUND = "document_not_found"
REASON_LOCATOR_NOT_FOUND = "locator_not_found"
REASON_AMBIGUOUS_DOCUMENT = "ambiguous_document"
REASON_AMBIGUOUS_LOCATOR = "ambiguous_locator"
REASON_DOCUMENT_CANDIDATE_LIMIT = "document_candidate_limit"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"
REASON_INVALID_CATALOGUE_REQUEST = "invalid_catalogue_request"

DOCUMENT_QUERY_LIMIT = 20
LOCATOR_QUERY_LIMIT = 20
SAFE_LOCATOR_KINDS = {"chapter", "milestone", "page", "paragraph", "stephanus"}


@dataclass(frozen=True)
class BiblioResolveRequest:
    document_id: str = ""
    title: str = ""
    document_title: str = ""
    work_title: str = ""
    author: str = ""
    locator: str = ""
    locator_end: str = ""
    locator_kind: str = "stephanus"
    locator_anchor_page: int | None = None
    locator_anchor_para: int | None = None


@dataclass(frozen=True)
class DocumentCandidate:
    document_id: str
    doc_id_short: str
    title: str = ""
    canonical_title: str = ""
    authors: str = ""
    metadata_status: str = ""
    match_reasons: tuple[str, ...] = field(default_factory=tuple)

    def to_observability(self) -> dict[str, Any]:
        return {
            "doc_id_short": self.doc_id_short,
            "metadata_status": self.metadata_status,
            "match_reasons": list(self.match_reasons),
        }


@dataclass(frozen=True)
class LocatorCandidate:
    document_id: str
    doc_id_short: str
    kind: str
    label: str
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    order_index: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "doc_id_short": self.doc_id_short,
            "kind": _observable_locator_kind(self.kind),
            "label": _compact_text_signal(self.label),
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "order_index": self.order_index,
        }


@dataclass(frozen=True)
class BiblioResolutionResult:
    status: str
    reason_code: str
    document: DocumentCandidate | None = None
    document_candidates: tuple[DocumentCandidate, ...] = field(default_factory=tuple)
    locator: LocatorCandidate | None = None
    locator_end: LocatorCandidate | None = None
    locator_candidates: tuple[LocatorCandidate, ...] = field(default_factory=tuple)
    requested_locator_kind: str = ""
    requested_locator: str = ""
    requested_locator_end: str = ""
    locator_anchor_page: int | None = None
    locator_anchor_para: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "document": self.document.to_observability() if self.document else None,
            "document_candidate_count": len(self.document_candidates),
            "document_candidate_ids": [candidate.doc_id_short for candidate in self.document_candidates],
            "locator": self.locator.to_observability() if self.locator else None,
            "locator_end": self.locator_end.to_observability() if self.locator_end else None,
            "locator_candidate_count": len(self.locator_candidates),
            "requested_locator_kind": _observable_locator_kind(self.requested_locator_kind),
            "requested_locator": _compact_text_signal(self.requested_locator),
            "requested_locator_end": _compact_text_signal(self.requested_locator_end),
            "locator_anchor_page": self.locator_anchor_page,
            "locator_anchor_para": self.locator_anchor_para,
        }


class BiblioDocumentResolver:
    def __init__(self, client: CatalogueClient) -> None:
        self._client = client

    def resolve(self, request: BiblioResolveRequest) -> BiblioResolutionResult:
        clean = _clean_request(request)
        if not _has_any_request_value(clean):
            return _result(clean, STATUS_INVALID_REQUEST, REASON_EMPTY_REQUEST)
        if clean.locator_end and not clean.locator:
            return _result(clean, STATUS_INVALID_REQUEST, REASON_LOCATOR_RANGE_REQUIRES_START)
        if _has_locator(clean) and not _has_document_signal(clean):
            return _result(clean, STATUS_INVALID_REQUEST, REASON_LOCATOR_REQUIRES_DOCUMENT)

        document_result = self._resolve_document(clean)
        if document_result.status != STATUS_RESOLVED or not document_result.document:
            return document_result
        if not _has_locator(clean):
            return document_result

        locator_result = self._resolve_locator(clean, document_result.document)
        if locator_result.status != STATUS_RESOLVED:
            return locator_result
        return BiblioResolutionResult(
            status=STATUS_RESOLVED,
            reason_code=REASON_DOCUMENT_AND_LOCATOR_RANGE_RESOLVED
            if clean.locator_end
            else REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
            document=document_result.document,
            locator=locator_result.locator,
            locator_end=locator_result.locator_end,
            locator_candidates=locator_result.locator_candidates,
            requested_locator_kind=clean.locator_kind,
            requested_locator=clean.locator,
            requested_locator_end=clean.locator_end,
            locator_anchor_page=clean.locator_anchor_page,
            locator_anchor_para=clean.locator_anchor_para,
        )

    def _resolve_document(self, request: BiblioResolveRequest) -> BiblioResolutionResult:
        if request.document_id:
            return self._resolve_document_by_id(request)

        query = _document_query(request) or request.author
        try:
            response = self._client.catalog(q=query, limit=DOCUMENT_QUERY_LIMIT, offset=0)
        except CatalogueClientError as exc:
            return _client_error_result(request, exc, REASON_DOCUMENT_NOT_FOUND)

        items = _catalog_items(response)
        if not items:
            return _result(request, STATUS_NOT_FOUND, REASON_DOCUMENT_NOT_FOUND)

        candidates = tuple(
            candidate
            for candidate in (_document_candidate_from_mapping(item, request) for item in items)
            if candidate is not None and _matches_document_request(candidate, request)
        )
        if not candidates:
            return _result(request, STATUS_NOT_FOUND, REASON_DOCUMENT_NOT_FOUND)

        total = _payload_int(response.payload, "total")
        if total is not None and total > len(items):
            return _result(
                request,
                STATUS_AMBIGUOUS,
                REASON_DOCUMENT_CANDIDATE_LIMIT,
                document_candidates=candidates,
            )
        if len(candidates) > 1:
            return _result(
                request,
                STATUS_AMBIGUOUS,
                REASON_AMBIGUOUS_DOCUMENT,
                document_candidates=candidates,
            )
        return _result(
            request,
            STATUS_RESOLVED,
            REASON_DOCUMENT_RESOLVED,
            document=candidates[0],
            document_candidates=candidates,
        )

    def _resolve_document_by_id(self, request: BiblioResolveRequest) -> BiblioResolutionResult:
        metadata_payload: Mapping[str, Any] | None = None
        try:
            metadata = self._client.metadata(request.document_id)
            metadata_payload = metadata.payload
        except CatalogueClientError as exc:
            return _client_error_result(request, exc, REASON_DOCUMENT_NOT_FOUND)

        candidate = _document_candidate_from_metadata(metadata_payload, request)
        if not candidate:
            return _result(request, STATUS_NOT_FOUND, REASON_DOCUMENT_NOT_FOUND)
        return _result(
            request,
            STATUS_RESOLVED,
            REASON_DOCUMENT_RESOLVED,
            document=candidate,
            document_candidates=(candidate,),
        )

    def _resolve_locator(
        self,
        request: BiblioResolveRequest,
        document: DocumentCandidate,
    ) -> BiblioResolutionResult:
        start = self._locate_one(request, document, request.locator)
        if start.status != STATUS_RESOLVED:
            return start
        if not request.locator_end:
            return start

        end = self._locate_one(request, document, request.locator_end)
        if end.status != STATUS_RESOLVED:
            return end
        return BiblioResolutionResult(
            status=STATUS_RESOLVED,
            reason_code=REASON_DOCUMENT_AND_LOCATOR_RANGE_RESOLVED,
            document=document,
            locator=start.locator,
            locator_end=end.locator,
            locator_candidates=start.locator_candidates + end.locator_candidates,
            requested_locator_kind=request.locator_kind,
            requested_locator=request.locator,
            requested_locator_end=request.locator_end,
            locator_anchor_page=request.locator_anchor_page,
            locator_anchor_para=request.locator_anchor_para,
        )

    def _locate_one(
        self,
        request: BiblioResolveRequest,
        document: DocumentCandidate,
        label: str,
    ) -> BiblioResolutionResult:
        try:
            response = self._client.locate(
                document.document_id,
                label,
                kind=request.locator_kind,
                limit=LOCATOR_QUERY_LIMIT,
            )
        except CatalogueClientError as exc:
            return _client_error_result(request, exc, REASON_LOCATOR_NOT_FOUND, document=document)

        candidates = _locator_candidates(response.payload, document)
        if not candidates:
            return _result(request, STATUS_NOT_FOUND, REASON_LOCATOR_NOT_FOUND, document=document)

        anchored = _anchored_locator_candidate(candidates, request)
        if anchored is not None:
            return _result(
                request,
                STATUS_RESOLVED,
                REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
                document=document,
                locator=anchored,
                locator_candidates=candidates,
            )

        match_count = _payload_int(response.payload, "match_count")
        if (match_count is not None and match_count > 1) or len(candidates) > 1:
            return _result(
                request,
                STATUS_AMBIGUOUS,
                REASON_AMBIGUOUS_LOCATOR,
                document=document,
                locator_candidates=candidates,
            )

        return _result(
            request,
            STATUS_RESOLVED,
            REASON_DOCUMENT_AND_LOCATOR_RESOLVED,
            document=document,
            locator=candidates[0],
            locator_candidates=candidates,
        )


def _clean_request(request: BiblioResolveRequest) -> BiblioResolveRequest:
    return BiblioResolveRequest(
        document_id=str(request.document_id or "").strip(),
        title=str(request.title or "").strip(),
        document_title=str(request.document_title or "").strip(),
        work_title=str(request.work_title or "").strip(),
        author=str(request.author or "").strip(),
        locator=str(request.locator or "").strip(),
        locator_end=str(request.locator_end or "").strip(),
        locator_kind=str(request.locator_kind or "stephanus").strip().lower() or "stephanus",
        locator_anchor_page=_positive_optional_int(request.locator_anchor_page),
        locator_anchor_para=_positive_optional_int(request.locator_anchor_para),
    )


def _has_any_request_value(request: BiblioResolveRequest) -> bool:
    return any(
        [
            request.document_id,
            request.title,
            request.document_title,
            request.work_title,
            request.author,
            request.locator,
            request.locator_end,
        ]
    )


def _has_document_signal(request: BiblioResolveRequest) -> bool:
    return bool(request.document_id or request.title or request.document_title or request.work_title or request.author)


def _has_locator(request: BiblioResolveRequest) -> bool:
    return bool(request.locator or request.locator_end)


def _result(
    request: BiblioResolveRequest,
    status: str,
    reason_code: str,
    *,
    document: DocumentCandidate | None = None,
    document_candidates: Sequence[DocumentCandidate] = (),
    locator: LocatorCandidate | None = None,
    locator_end: LocatorCandidate | None = None,
    locator_candidates: Sequence[LocatorCandidate] = (),
) -> BiblioResolutionResult:
    return BiblioResolutionResult(
        status=status,
        reason_code=reason_code,
        document=document,
        document_candidates=tuple(document_candidates),
        locator=locator,
        locator_end=locator_end,
        locator_candidates=tuple(locator_candidates),
        requested_locator_kind=request.locator_kind,
        requested_locator=request.locator,
        requested_locator_end=request.locator_end,
        locator_anchor_page=request.locator_anchor_page,
        locator_anchor_para=request.locator_anchor_para,
    )


def _client_error_result(
    request: BiblioResolveRequest,
    exc: CatalogueClientError,
    not_found_reason: str,
    *,
    document: DocumentCandidate | None = None,
) -> BiblioResolutionResult:
    if isinstance(exc, CatalogueNotFound):
        return _result(request, STATUS_NOT_FOUND, not_found_reason, document=document)
    if isinstance(exc, CatalogueInvalidParameter):
        return _result(request, STATUS_INVALID_REQUEST, REASON_INVALID_CATALOGUE_REQUEST, document=document)
    return _result(request, STATUS_CATALOGUE_UNAVAILABLE, REASON_CATALOGUE_UNAVAILABLE, document=document)


def _catalog_items(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    items = response.payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _document_candidate_from_mapping(
    item: Mapping[str, Any],
    request: BiblioResolveRequest,
) -> DocumentCandidate | None:
    doc_id = _text(item.get("id") or item.get("document_id"))
    if not doc_id:
        return None

    title = _text(item.get("title"))
    canonical_title = _text(item.get("human_canonical_title") or item.get("canonical_title"))
    authors = _text(item.get("human_authors") or item.get("authors"))
    metadata_status = _text(item.get("human_metadata_status") or item.get("metadata_status"))
    return DocumentCandidate(
        document_id=doc_id,
        doc_id_short=_short_doc_id(doc_id),
        title=title,
        canonical_title=canonical_title,
        authors=authors,
        metadata_status=metadata_status,
        match_reasons=_match_reasons(title, canonical_title, authors, request),
    )


def _document_candidate_from_detail(
    document_payload: Mapping[str, Any],
    metadata_payload: Mapping[str, Any] | None,
    request: BiblioResolveRequest,
) -> DocumentCandidate | None:
    document = document_payload.get("document")
    if not isinstance(document, Mapping):
        document = document_payload

    human = metadata_payload.get("human_metadata") if isinstance(metadata_payload, Mapping) else None
    if not isinstance(human, Mapping):
        human = {}
    metadata_document = metadata_payload.get("document") if isinstance(metadata_payload, Mapping) else None
    if not isinstance(metadata_document, Mapping):
        metadata_document = {}

    doc_id = _text(document.get("id") or metadata_document.get("id") or request.document_id)
    if not doc_id:
        return None

    title = _text(document.get("title") or metadata_document.get("title"))
    canonical_title = _text(human.get("canonical_title"))
    authors = _text(human.get("authors"))
    metadata_status = _text(
        metadata_payload.get("metadata_status") if isinstance(metadata_payload, Mapping) else ""
    ) or _text(human.get("metadata_status"))
    return DocumentCandidate(
        document_id=doc_id,
        doc_id_short=_short_doc_id(doc_id),
        title=title,
        canonical_title=canonical_title,
        authors=authors,
        metadata_status=metadata_status,
        match_reasons=_match_reasons(title, canonical_title, authors, request),
    )


def _document_candidate_from_metadata(
    metadata_payload: Mapping[str, Any] | None,
    request: BiblioResolveRequest,
) -> DocumentCandidate | None:
    if not isinstance(metadata_payload, Mapping):
        return None
    human = metadata_payload.get("human_metadata")
    if not isinstance(human, Mapping):
        human = {}
    document = metadata_payload.get("document")
    if not isinstance(document, Mapping):
        document = {}

    doc_id = _text(document.get("id") or request.document_id)
    if not doc_id:
        return None

    title = _text(document.get("title"))
    canonical_title = _text(human.get("canonical_title"))
    authors = _text(human.get("authors"))
    metadata_status = _text(metadata_payload.get("metadata_status")) or _text(human.get("metadata_status"))
    return DocumentCandidate(
        document_id=doc_id,
        doc_id_short=_short_doc_id(doc_id),
        title=title,
        canonical_title=canonical_title,
        authors=authors,
        metadata_status=metadata_status,
        match_reasons=_match_reasons(title, canonical_title, authors, request),
    )


def _matches_document_request(candidate: DocumentCandidate, request: BiblioResolveRequest) -> bool:
    haystack = " ".join([candidate.title, candidate.canonical_title, candidate.authors]).lower()
    document_query = _document_query(request)
    if document_query and document_query.lower() not in haystack:
        return False
    if request.author and request.author.lower() not in candidate.authors.lower():
        return False
    return True


def _match_reasons(
    title: str,
    canonical_title: str,
    authors: str,
    request: BiblioResolveRequest,
) -> tuple[str, ...]:
    reasons: list[str] = []
    title_query = _document_query(request).lower()
    work_query = request.work_title.lower()
    author_query = request.author.lower()
    if title_query:
        if title_query in canonical_title.lower():
            reasons.append("human_title")
        elif title_query in title.lower():
            reasons.append("source_title")
        elif title_query in authors.lower():
            reasons.append("human_author")
    if work_query:
        if work_query in canonical_title.lower():
            reasons.append("work_title_hint")
        elif work_query in title.lower():
            reasons.append("work_title_hint")
    if author_query and author_query in authors.lower():
        reasons.append("human_author")
    return tuple(dict.fromkeys(reasons))


def _document_query(request: BiblioResolveRequest) -> str:
    return str(request.document_title or request.title or "").strip()


def _locator_candidates(
    payload: Mapping[str, Any],
    document: DocumentCandidate,
) -> tuple[LocatorCandidate, ...]:
    raw_items: list[Mapping[str, Any]] = []
    best = payload.get("best")
    if isinstance(best, Mapping):
        raw_items.append(best)
    alternatives = payload.get("alternatives")
    if isinstance(alternatives, list):
        raw_items.extend(item for item in alternatives if isinstance(item, Mapping))
    for key in ("items", "matches", "results"):
        value = payload.get(key)
        if isinstance(value, list):
            raw_items.extend(item for item in value if isinstance(item, Mapping))

    if not raw_items and payload.get("label"):
        raw_items.append(payload)

    candidates: list[LocatorCandidate] = []
    seen: set[tuple[Any, ...]] = set()
    for item in raw_items:
        candidate = _locator_candidate_from_mapping(item, document, payload)
        if not candidate:
            continue
        key = (
            candidate.document_id,
            candidate.kind,
            candidate.label,
            candidate.page_no,
            candidate.para_no,
            candidate.paragraph_id,
        )
        if key in seen:
            continue
        seen.add(key)
        candidates.append(candidate)
    return tuple(candidates)


def _locator_candidate_from_mapping(
    item: Mapping[str, Any],
    document: DocumentCandidate,
    payload: Mapping[str, Any],
) -> LocatorCandidate | None:
    label = _text(item.get("label") or payload.get("label"))
    kind = _text(item.get("kind") or payload.get("kind"))
    if not label:
        return None
    return LocatorCandidate(
        document_id=document.document_id,
        doc_id_short=document.doc_id_short,
        kind=kind,
        label=label,
        page_no=_optional_int(item.get("page_no")),
        para_no=_optional_int(item.get("para_no")),
        paragraph_id=_optional_int(item.get("paragraph_id")),
        order_index=_optional_int(item.get("order_index")),
    )


def _anchored_locator_candidate(
    candidates: Sequence[LocatorCandidate],
    request: BiblioResolveRequest,
) -> LocatorCandidate | None:
    if request.locator_anchor_page is None:
        return None
    scored: list[tuple[int, LocatorCandidate]] = []
    for candidate in candidates:
        if candidate.page_no is None:
            continue
        para_score = 0
        if request.locator_anchor_para is not None and candidate.para_no is not None:
            para_score = abs(candidate.para_no - request.locator_anchor_para)
        score = abs(candidate.page_no - request.locator_anchor_page) * 100_000 + para_score
        scored.append((score, candidate))
    if not scored:
        return None
    scored.sort(key=lambda item: item[0])
    if len(scored) > 1 and scored[0][0] == scored[1][0]:
        return None
    return scored[0][1]


def _payload_int(payload: Mapping[str, Any], key: str) -> int | None:
    value = payload.get(key)
    if type(value) is int:
        return value
    return None


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _positive_optional_int(value: Any) -> int | None:
    integer = _optional_int(value)
    if integer is None or integer < 1:
        return None
    return integer


def _text(value: Any) -> str:
    return str(value or "").strip()


def _short_doc_id(doc_id: str) -> str:
    return doc_id[:8]


def _observable_locator_kind(kind: str) -> str:
    normalized = _text(kind).lower()
    if normalized in SAFE_LOCATOR_KINDS:
        return normalized
    return "custom" if normalized else ""


def _compact_text_signal(value: str) -> dict[str, Any]:
    text = _text(value)
    if not text:
        return {"present": False, "length": 0, "hash": ""}
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    return {"present": True, "length": len(text), "hash": digest}
