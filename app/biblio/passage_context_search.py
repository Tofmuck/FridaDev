"""Bounded context validation for Biblio passage candidates.

Lot 3 treats Lot 2 candidates as provisional.  It validates a small top-N via
``/context`` before returning an extracted passage or an explicit ambiguity.
Observability stays content-free; raw passage text is kept only on an
``extracted`` result.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueEndpointObservation,
    CatalogueInvalidParameter,
    CatalogueNotFound,
    CatalogueResponse,
    observe_catalogue_response,
)
from .passage_candidate_search import (
    BiblioPassageCandidate,
    BiblioPassageCandidateSearchResult,
    BiblioPassageCandidateSearcher,
    STATUS_CATALOGUE_UNAVAILABLE as CANDIDATES_CATALOGUE_UNAVAILABLE,
    STATUS_INVALID_REQUEST as CANDIDATES_INVALID_REQUEST,
)
from .passage_extractor import DEFAULT_CONTEXT_WINDOW_CHARS, DEFAULT_MAX_PASSAGE_CHARS
from .query_planner import BiblioQueryPlan


STATUS_EXTRACTED = "extracted"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NOT_FOUND = "not_found"
STATUS_INVALID_REQUEST = "invalid_request"
STATUS_INCOHERENT_CATALOGUE = "incoherent_catalogue"
STATUS_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"
STATUS_TOO_LONG = "too_long"

REASON_CONTEXT_EXTRACTED = "biblio_context_passage_extracted"
REASON_CONTEXT_AMBIGUOUS = "biblio_context_candidates_ambiguous"
REASON_CONTEXT_NOT_FOUND = "biblio_context_not_found"
REASON_CONTEXT_INVALID_REQUEST = "biblio_context_invalid_request"
REASON_CONTEXT_INCOHERENT = "biblio_context_incoherent_catalogue"
REASON_CONTEXT_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"
REASON_CONTEXT_TOO_LONG = "biblio_context_passage_too_long"

DEFAULT_MAX_CONTEXT_CANDIDATES = 3
MIN_MAX_CONTEXT_CANDIDATES = 1
MAX_MAX_CONTEXT_CANDIDATES = 5
MIN_CONTEXT_WINDOW_CHARS = 80
MAX_CONTEXT_WINDOW_CHARS = 2_000
MIN_MAX_PASSAGE_CHARS = 80
MAX_MAX_PASSAGE_CHARS = 8_000


@dataclass(frozen=True)
class BiblioPassageContextSearchRequest:
    plan: BiblioQueryPlan = field(repr=False, compare=False)
    candidate_result: BiblioPassageCandidateSearchResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    max_context_candidates: int = DEFAULT_MAX_CONTEXT_CANDIDATES
    char_offset: int = 0
    window_chars: int = DEFAULT_CONTEXT_WINDOW_CHARS
    max_passage_chars: int = DEFAULT_MAX_PASSAGE_CHARS


@dataclass(frozen=True)
class BiblioPassageContextDecision:
    status: str
    reason_code: str
    doc_id_short: str = ""
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    candidate_score: float = 0.0
    candidate_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    context_chars: int = 0
    context_hash: str = ""
    excerpt_start: int | None = None
    excerpt_end: int | None = None
    text_length: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "doc_id_short": self.doc_id_short,
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "candidate_score": round(float(self.candidate_score), 3),
            "candidate_reason_codes": list(self.candidate_reason_codes),
            "context_chars": self.context_chars,
            "context_hash": self.context_hash,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "text_length": self.text_length,
        }


@dataclass(frozen=True, repr=False)
class BiblioPassageContextSearchResult:
    status: str
    reason_code: str
    candidate_result: BiblioPassageCandidateSearchResult | None = field(
        default=None,
        repr=False,
        compare=False,
    )
    context_observations: tuple[CatalogueEndpointObservation, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    decisions: tuple[BiblioPassageContextDecision, ...] = field(default_factory=tuple)
    passage: str = field(default="", repr=False, compare=False)
    passage_chars: int = 0
    passage_hash: str = ""
    doc_id_short: str = ""
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    excerpt_start: int | None = None
    excerpt_end: int | None = None
    text_length: int | None = None
    max_context_candidates: int = DEFAULT_MAX_CONTEXT_CANDIDATES

    def to_observability(self) -> dict[str, Any]:
        candidate_observability = (
            self.candidate_result.to_observability() if self.candidate_result is not None else {}
        )
        endpoint_count = int(candidate_observability.get("endpoint_count") or 0) + len(self.context_observations)
        if self.client_error is not None:
            endpoint_count += 1
        endpoint_kinds = set(candidate_observability.get("endpoint_kinds") or [])
        endpoint_kinds.update(
            str(observation.endpoint_kind or "")
            for observation in self.context_observations
            if str(observation.endpoint_kind or "")
        )
        if self.client_error is not None and self.client_error.endpoint_kind:
            endpoint_kinds.add(self.client_error.endpoint_kind)
        plausible_count = sum(1 for decision in self.decisions if decision.status == STATUS_EXTRACTED)
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "candidate_count": len(self.candidate_result.candidates) if self.candidate_result else 0,
            "context_call_count": len(self.context_observations),
            "plausible_context_count": plausible_count,
            "max_context_candidates": self.max_context_candidates,
            "passage_present": self.status == STATUS_EXTRACTED and bool(self.passage),
            "passage_chars": self.passage_chars,
            "passage_hash": self.passage_hash,
            "doc_id_short": self.doc_id_short,
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "excerpt_start": self.excerpt_start,
            "excerpt_end": self.excerpt_end,
            "text_length": self.text_length,
            "endpoint_count": endpoint_count,
            "endpoint_kinds": sorted(endpoint_kinds),
            "candidate_search": candidate_observability,
            "decisions": [decision.to_observability() for decision in self.decisions],
            "client_error": self.client_error.to_observability() if self.client_error else None,
        }


@dataclass(frozen=True)
class _ContextOptions:
    max_context_candidates: int
    char_offset: int
    window_chars: int
    max_passage_chars: int


class _InvalidContextSearchParameter(Exception):
    pass


class BiblioPassageContextSearcher:
    def __init__(
        self,
        client: CatalogueClient,
        *,
        candidate_searcher: BiblioPassageCandidateSearcher | None = None,
    ) -> None:
        self._client = client
        self._candidate_searcher = candidate_searcher if candidate_searcher is not None else BiblioPassageCandidateSearcher(client)

    def search(
        self,
        plan_or_request: BiblioQueryPlan | BiblioPassageContextSearchRequest,
    ) -> BiblioPassageContextSearchResult:
        request = _coerce_request(plan_or_request)
        try:
            options = _context_options(request)
        except _InvalidContextSearchParameter:
            return BiblioPassageContextSearchResult(
                status=STATUS_INVALID_REQUEST,
                reason_code=REASON_CONTEXT_INVALID_REQUEST,
            )

        candidate_result = request.candidate_result or self._candidate_searcher.search(request.plan)
        if candidate_result.status == CANDIDATES_CATALOGUE_UNAVAILABLE:
            return BiblioPassageContextSearchResult(
                status=STATUS_CATALOGUE_UNAVAILABLE,
                reason_code=REASON_CONTEXT_CATALOGUE_UNAVAILABLE,
                candidate_result=candidate_result,
                client_error=candidate_result.client_error,
                max_context_candidates=options.max_context_candidates,
            )
        if candidate_result.status == CANDIDATES_INVALID_REQUEST:
            return BiblioPassageContextSearchResult(
                status=STATUS_INVALID_REQUEST,
                reason_code=REASON_CONTEXT_INVALID_REQUEST,
                candidate_result=candidate_result,
                max_context_candidates=options.max_context_candidates,
            )
        if not candidate_result.candidates:
            return BiblioPassageContextSearchResult(
                status=STATUS_NOT_FOUND,
                reason_code=REASON_CONTEXT_NOT_FOUND,
                candidate_result=candidate_result,
                max_context_candidates=options.max_context_candidates,
            )

        context_observations: list[CatalogueEndpointObservation] = []
        decisions: list[BiblioPassageContextDecision] = []
        extracted: list[tuple[BiblioPassageCandidate, str, Mapping[str, Any]]] = []
        too_long_count = 0

        for candidate in candidate_result.candidates[: options.max_context_candidates]:
            target = _candidate_context_target(candidate)
            if target is None:
                decisions.append(_decision(candidate, STATUS_INVALID_REQUEST, REASON_CONTEXT_INVALID_REQUEST))
                continue
            try:
                response = self._context(candidate, target, options)
                context_observations.append(observe_catalogue_response(response))
            except CatalogueNotFound:
                decisions.append(_decision(candidate, STATUS_NOT_FOUND, REASON_CONTEXT_NOT_FOUND))
                continue
            except CatalogueInvalidParameter:
                decisions.append(_decision(candidate, STATUS_INVALID_REQUEST, REASON_CONTEXT_INVALID_REQUEST))
                continue
            except CatalogueClientError as exc:
                return BiblioPassageContextSearchResult(
                    status=STATUS_CATALOGUE_UNAVAILABLE,
                    reason_code=REASON_CONTEXT_CATALOGUE_UNAVAILABLE,
                    candidate_result=candidate_result,
                    context_observations=tuple(context_observations),
                    client_error=exc,
                    decisions=tuple(decisions),
                    max_context_candidates=options.max_context_candidates,
                )

            coherent = _coherent_context(candidate, response.payload)
            if coherent is not None:
                return BiblioPassageContextSearchResult(
                    status=STATUS_INCOHERENT_CATALOGUE,
                    reason_code=REASON_CONTEXT_INCOHERENT,
                    candidate_result=candidate_result,
                    context_observations=tuple(context_observations),
                    decisions=(*decisions, coherent),
                    max_context_candidates=options.max_context_candidates,
                )

            passage = _passage_text(response.payload)
            if passage is None:
                return BiblioPassageContextSearchResult(
                    status=STATUS_INCOHERENT_CATALOGUE,
                    reason_code=REASON_CONTEXT_INCOHERENT,
                    candidate_result=candidate_result,
                    context_observations=tuple(context_observations),
                    decisions=(
                        *decisions,
                        _decision(candidate, STATUS_INCOHERENT_CATALOGUE, REASON_CONTEXT_INCOHERENT),
                    ),
                    max_context_candidates=options.max_context_candidates,
                )
            if not passage.strip():
                decisions.append(_decision(candidate, STATUS_NOT_FOUND, REASON_CONTEXT_NOT_FOUND, payload=response.payload))
                continue
            if len(passage) > options.max_passage_chars:
                too_long_count += 1
                decisions.append(
                    _decision(
                        candidate,
                        STATUS_TOO_LONG,
                        REASON_CONTEXT_TOO_LONG,
                        payload=response.payload,
                        passage=passage,
                    )
                )
                continue

            decisions.append(
                _decision(
                    candidate,
                    STATUS_EXTRACTED,
                    REASON_CONTEXT_EXTRACTED,
                    payload=response.payload,
                    passage=passage,
                )
            )
            extracted.append((candidate, passage, response.payload))

        if len(extracted) == 1:
            candidate, passage, payload = extracted[0]
            return _extracted_result(
                candidate_result=candidate_result,
                context_observations=tuple(context_observations),
                decisions=tuple(decisions),
                candidate=candidate,
                payload=payload,
                passage=passage,
                options=options,
            )
        if len(extracted) > 1:
            return BiblioPassageContextSearchResult(
                status=STATUS_AMBIGUOUS,
                reason_code=REASON_CONTEXT_AMBIGUOUS,
                candidate_result=candidate_result,
                context_observations=tuple(context_observations),
                decisions=tuple(decisions),
                max_context_candidates=options.max_context_candidates,
            )
        if too_long_count:
            return BiblioPassageContextSearchResult(
                status=STATUS_TOO_LONG,
                reason_code=REASON_CONTEXT_TOO_LONG,
                candidate_result=candidate_result,
                context_observations=tuple(context_observations),
                decisions=tuple(decisions),
                max_context_candidates=options.max_context_candidates,
            )
        return BiblioPassageContextSearchResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_CONTEXT_NOT_FOUND,
            candidate_result=candidate_result,
            context_observations=tuple(context_observations),
            decisions=tuple(decisions),
            max_context_candidates=options.max_context_candidates,
        )

    def _context(
        self,
        candidate: BiblioPassageCandidate,
        target: Mapping[str, int],
        options: _ContextOptions,
    ) -> CatalogueResponse:
        if "paragraph_id" in target:
            return self._client.context(
                candidate.document_id,
                paragraph_id=target["paragraph_id"],
                char_offset=options.char_offset,
                window_chars=options.window_chars,
            )
        return self._client.context(
            candidate.document_id,
            page_no=target["page_no"],
            para_no=target["para_no"],
            char_offset=options.char_offset,
            window_chars=options.window_chars,
        )


def _coerce_request(
    value: BiblioQueryPlan | BiblioPassageContextSearchRequest,
) -> BiblioPassageContextSearchRequest:
    if isinstance(value, BiblioPassageContextSearchRequest):
        return value
    return BiblioPassageContextSearchRequest(plan=value)


def _context_options(request: BiblioPassageContextSearchRequest) -> _ContextOptions:
    return _ContextOptions(
        max_context_candidates=_bounded_int(
            request.max_context_candidates,
            minimum=MIN_MAX_CONTEXT_CANDIDATES,
            maximum=MAX_MAX_CONTEXT_CANDIDATES,
        ),
        char_offset=_bounded_int(request.char_offset, minimum=0, maximum=1_000_000),
        window_chars=_bounded_int(
            request.window_chars,
            minimum=MIN_CONTEXT_WINDOW_CHARS,
            maximum=MAX_CONTEXT_WINDOW_CHARS,
        ),
        max_passage_chars=_bounded_int(
            request.max_passage_chars,
            minimum=MIN_MAX_PASSAGE_CHARS,
            maximum=MAX_MAX_PASSAGE_CHARS,
        ),
    )


def _candidate_context_target(candidate: BiblioPassageCandidate) -> dict[str, int] | None:
    if type(candidate.paragraph_id) is int:
        return {"paragraph_id": candidate.paragraph_id}
    if type(candidate.page_no) is int and type(candidate.para_no) is int:
        return {"page_no": candidate.page_no, "para_no": candidate.para_no}
    return None


def _coherent_context(
    candidate: BiblioPassageCandidate,
    payload: Mapping[str, Any],
) -> BiblioPassageContextDecision | None:
    payload_doc_id = _text(payload.get("document_id"))
    if not payload_doc_id or payload_doc_id != candidate.document_id:
        return _decision(candidate, STATUS_INCOHERENT_CATALOGUE, REASON_CONTEXT_INCOHERENT, payload=payload)
    return None


def _extracted_result(
    *,
    candidate_result: BiblioPassageCandidateSearchResult,
    context_observations: tuple[CatalogueEndpointObservation, ...],
    decisions: tuple[BiblioPassageContextDecision, ...],
    candidate: BiblioPassageCandidate,
    payload: Mapping[str, Any],
    passage: str,
    options: _ContextOptions,
) -> BiblioPassageContextSearchResult:
    passage_hash = _short_hash(passage)
    return BiblioPassageContextSearchResult(
        status=STATUS_EXTRACTED,
        reason_code=REASON_CONTEXT_EXTRACTED,
        candidate_result=candidate_result,
        context_observations=context_observations,
        decisions=decisions,
        passage=passage,
        passage_chars=len(passage),
        passage_hash=passage_hash,
        doc_id_short=candidate.doc_id_short,
        page_no=_optional_int(payload.get("page_no")) if payload else candidate.page_no,
        para_no=_optional_int(payload.get("para_no")) if payload else candidate.para_no,
        paragraph_id=_optional_int(payload.get("paragraph_id")) if payload else candidate.paragraph_id,
        excerpt_start=_optional_int(payload.get("excerpt_start")),
        excerpt_end=_optional_int(payload.get("excerpt_end")),
        text_length=_optional_int(payload.get("text_length")),
        max_context_candidates=options.max_context_candidates,
    )


def _decision(
    candidate: BiblioPassageCandidate,
    status: str,
    reason_code: str,
    *,
    payload: Mapping[str, Any] | None = None,
    passage: str = "",
) -> BiblioPassageContextDecision:
    data = payload or {}
    passage_chars = len(passage) if passage else 0
    return BiblioPassageContextDecision(
        status=status,
        reason_code=reason_code,
        doc_id_short=candidate.doc_id_short,
        page_no=_optional_int(data.get("page_no")) if data else candidate.page_no,
        para_no=_optional_int(data.get("para_no")) if data else candidate.para_no,
        paragraph_id=_optional_int(data.get("paragraph_id")) if data else candidate.paragraph_id,
        candidate_score=candidate.score,
        candidate_reason_codes=candidate.reason_codes,
        context_chars=passage_chars,
        context_hash=_short_hash(passage) if passage else "",
        excerpt_start=_optional_int(data.get("excerpt_start")),
        excerpt_end=_optional_int(data.get("excerpt_end")),
        text_length=_optional_int(data.get("text_length")),
    )


def _passage_text(payload: Mapping[str, Any]) -> str | None:
    for key in ("excerpt", "text", "context"):
        value = payload.get(key)
        if isinstance(value, str):
            return value
    return None


def _bounded_int(value: Any, *, minimum: int, maximum: int) -> int:
    if type(value) is int:
        integer = value
    elif isinstance(value, str) and value.isdecimal():
        integer = int(value)
    else:
        raise _InvalidContextSearchParameter()
    if integer < minimum or integer > maximum:
        raise _InvalidContextSearchParameter()
    return integer


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _short_hash(value: str) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
