"""Content-free passage candidate search for Biblio thematic requests.

Lot 2 stops at ``/search`` results.  It aggregates and ranks paragraph
positions that a later lot may pass to ``/context``; it never stores OCR text,
Catalogue payloads, prompt content, or raw query strings in observability.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueClient, CatalogueClientError, CatalogueResponse, short_doc_id
from .query_normalizer import fold_text
from .query_planner import BiblioQueryPlan


STATUS_CANDIDATES_FOUND = "candidates_found"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_INVALID_REQUEST = "invalid_request"
STATUS_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

REASON_CANDIDATES_FOUND = "biblio_passage_candidates_found"
REASON_CANDIDATES_NOT_FOUND = "biblio_passage_candidates_not_found"
REASON_CANDIDATES_AMBIGUOUS = "biblio_passage_candidates_ambiguous"
REASON_INVALID_REQUEST = "biblio_passage_candidate_search_invalid_request"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_SEARCH_LIMIT = 20
DEFAULT_MAX_QUERY_VARIANTS = 10
DEFAULT_MAX_CANDIDATES = 8

_ROLE_THEME = "theme"
_ROLE_CATALOGUE = "catalogue"
_ROLE_WORK = "work"


@dataclass(frozen=True)
class BiblioPassageCandidateSearchRequest:
    plan: BiblioQueryPlan = field(repr=False, compare=False)
    search_limit: int = DEFAULT_SEARCH_LIMIT
    max_query_variants: int = DEFAULT_MAX_QUERY_VARIANTS
    max_candidates: int = DEFAULT_MAX_CANDIDATES


@dataclass(frozen=True)
class BiblioPassageCandidate:
    document_id: str = field(repr=False, compare=False)
    doc_id_short: str
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    score: float = 0.0
    hit_count: int = 0
    query_variant_count: int = 0
    query_hashes: tuple[str, ...] = field(default_factory=tuple)
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    first_rank: int | None = None

    def to_observability(self) -> dict[str, Any]:
        return {
            "doc_id_short": self.doc_id_short,
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "score": round(float(self.score), 3),
            "hit_count": self.hit_count,
            "query_variant_count": self.query_variant_count,
            "query_hashes": list(self.query_hashes),
            "reason_codes": list(self.reason_codes),
            "first_rank": self.first_rank,
        }


@dataclass(frozen=True, repr=False)
class BiblioPassageCandidateSearchResult:
    status: str
    reason_code: str
    candidates: tuple[BiblioPassageCandidate, ...] = field(default_factory=tuple)
    query_hashes: tuple[str, ...] = field(default_factory=tuple)
    client_responses: tuple[CatalogueResponse, ...] = field(default_factory=tuple, repr=False, compare=False)
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    skipped_row_count: int = 0
    total_candidate_count: int = 0
    ambiguous: bool = False

    def to_observability(self) -> dict[str, Any]:
        top_score = self.candidates[0].score if self.candidates else 0.0
        doc_id_shorts = tuple(dict.fromkeys(candidate.doc_id_short for candidate in self.candidates if candidate.doc_id_short))
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "candidate_count": len(self.candidates),
            "total_candidate_count": self.total_candidate_count,
            "skipped_row_count": self.skipped_row_count,
            "ambiguous": self.ambiguous,
            "top_score": round(float(top_score), 3),
            "query_variant_count": len(self.query_hashes),
            "query_hashes": list(self.query_hashes),
            "endpoint_count": len(self.client_responses) + (1 if self.client_error else 0),
            "endpoint_kinds": _endpoint_kinds(self.client_responses, self.client_error),
            "doc_id_shorts": list(doc_id_shorts),
            "candidates": [candidate.to_observability() for candidate in self.candidates],
            "client_error": self.client_error.to_observability() if self.client_error else None,
        }


class BiblioPassageCandidateSearcher:
    def __init__(self, client: CatalogueClient) -> None:
        self._client = client

    def search(
        self,
        plan_or_request: BiblioQueryPlan | BiblioPassageCandidateSearchRequest,
    ) -> BiblioPassageCandidateSearchResult:
        request = _coerce_request(plan_or_request)
        query_specs = _query_specs(request)
        if not request.plan.should_consult or not query_specs:
            return BiblioPassageCandidateSearchResult(
                status=STATUS_INVALID_REQUEST,
                reason_code=REASON_INVALID_REQUEST,
            )

        responses: list[CatalogueResponse] = []
        aggregates: dict[tuple[Any, ...], _CandidateAggregate] = {}
        work_positions: dict[str, list[tuple[int | None, int | None]]] = {}
        skipped_rows = 0
        try:
            for spec in query_specs:
                response = self._client.search(spec.query, limit=request.search_limit)
                responses.append(response)
                rows = _search_results(response)
                for row in rows:
                    position = _row_position(row)
                    if position is None:
                        skipped_rows += 1
                        continue
                    doc_id, page_no, para_no, paragraph_id, rank = position
                    if _ROLE_WORK in spec.roles:
                        work_positions.setdefault(doc_id, []).append((page_no, para_no))
                    if not spec.produces_candidates:
                        continue
                    key = _candidate_key(doc_id, page_no, para_no, paragraph_id)
                    aggregate = aggregates.setdefault(
                        key,
                        _CandidateAggregate(
                            document_id=doc_id,
                            page_no=page_no,
                            para_no=para_no,
                            paragraph_id=paragraph_id,
                        ),
                    )
                    aggregate.add_hit(spec, rank=rank)
        except CatalogueClientError as exc:
            return BiblioPassageCandidateSearchResult(
                status=STATUS_CATALOGUE_UNAVAILABLE,
                reason_code=REASON_CATALOGUE_UNAVAILABLE,
                client_responses=tuple(responses),
                client_error=exc,
                skipped_row_count=skipped_rows,
            )

        if not aggregates:
            return BiblioPassageCandidateSearchResult(
                status=STATUS_NOT_FOUND,
                reason_code=REASON_CANDIDATES_NOT_FOUND,
                query_hashes=tuple(_query_hashes(query_specs)),
                client_responses=tuple(responses),
                skipped_row_count=skipped_rows,
            )

        all_candidates = _ranked_candidates(aggregates.values(), work_positions)
        returned = tuple(all_candidates[: request.max_candidates])
        ambiguous = len(all_candidates) > 1 and all_candidates[0].score == all_candidates[1].score
        return BiblioPassageCandidateSearchResult(
            status=STATUS_AMBIGUOUS if ambiguous else STATUS_CANDIDATES_FOUND,
            reason_code=REASON_CANDIDATES_AMBIGUOUS if ambiguous else REASON_CANDIDATES_FOUND,
            candidates=returned,
            query_hashes=tuple(_query_hashes(query_specs)),
            client_responses=tuple(responses),
            skipped_row_count=skipped_rows,
            total_candidate_count=len(all_candidates),
            ambiguous=ambiguous,
        )


@dataclass(frozen=True)
class _QuerySpec:
    query: str = field(repr=False, compare=False)
    query_hash: str
    roles: tuple[str, ...]
    produces_candidates: bool
    exact_theme: bool = False
    folded_theme_match: bool = False


@dataclass
class _CandidateAggregate:
    document_id: str
    page_no: int | None
    para_no: int | None
    paragraph_id: int | None
    base_score: float = 0.0
    hit_count: int = 0
    query_hashes: list[str] = field(default_factory=list)
    reason_codes: set[str] = field(default_factory=set)
    first_rank: int | None = None

    def add_hit(self, spec: _QuerySpec, *, rank: int | None) -> None:
        self.hit_count += 1
        if spec.query_hash not in self.query_hashes:
            self.query_hashes.append(spec.query_hash)
        self.reason_codes.add("search_hit")
        if _ROLE_THEME in spec.roles:
            self.base_score += 20
            self.reason_codes.add("theme_hit")
        elif _ROLE_CATALOGUE in spec.roles:
            self.base_score += 14
            self.reason_codes.add("catalogue_hit")
        else:
            self.base_score += 10
            self.reason_codes.add("work_hit")
        if spec.exact_theme:
            self.base_score += 6
            self.reason_codes.add("exact_theme_variant")
        elif spec.folded_theme_match:
            self.base_score += 4
            self.reason_codes.add("folded_theme_variant")
        if self.hit_count > 1:
            self.base_score += 3
            self.reason_codes.add("multi_variant_hit")
        if rank is not None:
            self.first_rank = rank if self.first_rank is None else min(self.first_rank, rank)
            if rank <= 3:
                self.base_score += 3
                self.reason_codes.add("high_search_rank")

    def to_candidate(self, work_positions: Mapping[str, Sequence[tuple[int | None, int | None]]]) -> BiblioPassageCandidate:
        score = self.base_score
        reasons = set(self.reason_codes)
        if self.document_id in work_positions:
            score += 10
            reasons.add("work_document_match")
            if _near_work_position(self.page_no, self.para_no, work_positions[self.document_id]):
                score += 4
                reasons.add("work_theme_proximity")
        return BiblioPassageCandidate(
            document_id=self.document_id,
            doc_id_short=short_doc_id(self.document_id),
            page_no=self.page_no,
            para_no=self.para_no,
            paragraph_id=self.paragraph_id,
            score=score,
            hit_count=self.hit_count,
            query_variant_count=len(self.query_hashes),
            query_hashes=tuple(self.query_hashes[:8]),
            reason_codes=tuple(sorted(reasons)),
            first_rank=self.first_rank,
        )


def _coerce_request(
    value: BiblioQueryPlan | BiblioPassageCandidateSearchRequest,
) -> BiblioPassageCandidateSearchRequest:
    if isinstance(value, BiblioPassageCandidateSearchRequest):
        return value
    return BiblioPassageCandidateSearchRequest(plan=value)


def _query_specs(request: BiblioPassageCandidateSearchRequest) -> tuple[_QuerySpec, ...]:
    plan = request.plan
    specs_by_query: dict[str, set[str]] = {}
    if plan.theme_query:
        _add_queries(specs_by_query, _ROLE_THEME, plan.theme_query_variants, plan.theme_query)
    else:
        _add_queries(specs_by_query, _ROLE_CATALOGUE, plan.catalogue_query_variants, plan.catalogue_query)
    _add_queries(
        specs_by_query,
        _ROLE_WORK,
        plan.work_title_variants,
        plan.work_title,
        plan.document_title_variants,
        plan.document_title,
    )

    has_direct_candidate_query = any(
        roles.intersection({_ROLE_THEME, _ROLE_CATALOGUE}) for roles in specs_by_query.values()
    )
    specs: list[_QuerySpec] = []
    theme = str(plan.theme_query or "")
    folded_theme = fold_text(theme)
    for query, roles in specs_by_query.items():
        produces_candidates = bool(roles.intersection({_ROLE_THEME, _ROLE_CATALOGUE})) or not has_direct_candidate_query
        specs.append(
            _QuerySpec(
                query=query,
                query_hash=_sha256_12(query),
                roles=tuple(sorted(roles)),
                produces_candidates=produces_candidates,
                exact_theme=bool(theme and query == theme),
                folded_theme_match=bool(folded_theme and fold_text(query) == folded_theme),
            )
        )
    return tuple(specs[: request.max_query_variants])


def _add_queries(target: dict[str, set[str]], role: str, *groups: Any) -> None:
    for query in _candidate_queries(*groups):
        target.setdefault(query, set()).add(role)


def _candidate_queries(*groups: Any) -> tuple[str, ...]:
    queries: list[str] = []
    for group in groups:
        if isinstance(group, str):
            items = (group,)
        elif isinstance(group, Sequence):
            items = tuple(str(item or "") for item in group)
        else:
            items = ()
        for item in items:
            text = str(item or "").strip()
            if text and text not in queries:
                queries.append(text)
    return tuple(queries)


def _search_results(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    results = response.payload.get("results")
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, Mapping)]


def _row_position(row: Mapping[str, Any]) -> tuple[str, int | None, int | None, int | None, int | None] | None:
    doc_id = str(row.get("document_id") or "").strip()
    if not doc_id:
        return None
    page_no = _optional_int(row.get("page_no"))
    para_no = _optional_int(row.get("para_no"))
    paragraph_id = _optional_int(row.get("paragraph_id"))
    if paragraph_id is None and (page_no is None or para_no is None):
        return None
    return doc_id, page_no, para_no, paragraph_id, _optional_int(row.get("rank"))


def _candidate_key(
    document_id: str,
    page_no: int | None,
    para_no: int | None,
    paragraph_id: int | None,
) -> tuple[Any, ...]:
    return document_id, page_no, para_no, paragraph_id


def _ranked_candidates(
    aggregates: Sequence[_CandidateAggregate],
    work_positions: Mapping[str, Sequence[tuple[int | None, int | None]]],
) -> list[BiblioPassageCandidate]:
    candidates = [aggregate.to_candidate(work_positions) for aggregate in aggregates]
    return sorted(
        candidates,
        key=lambda candidate: (
            -candidate.score,
            candidate.doc_id_short,
            candidate.page_no or 0,
            candidate.para_no or 0,
            candidate.paragraph_id or 0,
        ),
    )


def _near_work_position(
    page_no: int | None,
    para_no: int | None,
    positions: Sequence[tuple[int | None, int | None]],
) -> bool:
    if page_no is None:
        return False
    for work_page, work_para in positions:
        if work_page is None:
            continue
        if abs(work_page - page_no) <= 3:
            return True
        if work_para is not None and para_no is not None and work_page == page_no and abs(work_para - para_no) <= 8:
            return True
    return False


def _endpoint_kinds(
    responses: Sequence[CatalogueResponse],
    error: CatalogueClientError | None,
) -> list[str]:
    kinds = [str(response.endpoint_kind or "") for response in responses if str(response.endpoint_kind or "")]
    if error is not None and error.endpoint_kind:
        kinds.append(error.endpoint_kind)
    return sorted(set(kinds))


def _query_hashes(specs: Sequence[_QuerySpec]) -> list[str]:
    return list(dict.fromkeys(spec.query_hash for spec in specs if spec.query_hash))


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
