"""Resolve internal works into Catalogue document and locator hints.

Catalogue currently stores physical documents and searchable paragraphs.  This
layer bridges natural requests such as "Theetete de Platon 126b" by using
catalog metadata plus content search only as an internal anchor.  Its public
projection stays content-free.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
import re
from typing import Any, Mapping, Sequence
import unicodedata

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueEndpointObservation,
    CatalogueResponse,
    observe_catalogue_response,
    short_doc_id,
)
from .document_resolver import BiblioResolveRequest
from .query_planner import BiblioQueryPlan


STATUS_RESOLVED = "resolved"
STATUS_SEARCHED = "searched"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

REASON_WORK_RESOLVED = "biblio_work_resolved"
REASON_WORK_SEARCHED = "biblio_work_searched"
REASON_WORK_NOT_FOUND = "biblio_work_not_found"
REASON_WORK_AMBIGUOUS = "biblio_work_ambiguous"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DOCUMENT_QUERY_LIMIT = 20
WORK_SEARCH_LIMIT = 20


@dataclass(frozen=True)
class BiblioWorkResolution:
    status: str
    reason_code: str
    resolve_request: BiblioResolveRequest | None = None
    endpoint_observations: tuple[CatalogueEndpointObservation, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    document_candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    search_result_count: int = 0
    catalog_result_count: int = 0
    anchor_doc_id_short: str = ""
    anchor_page: int | None = None
    anchor_para: int | None = None
    documentary_target: str = ""
    work_hint_present: bool = False
    document_hint_present: bool = False

    def to_observability(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "document_candidate_ids": list(self.document_candidate_ids),
            "document_candidate_count": len(self.document_candidate_ids),
            "search_result_count": self.search_result_count,
            "catalog_result_count": self.catalog_result_count,
            "anchor_doc_id_short": self.anchor_doc_id_short,
            "anchor_page": self.anchor_page,
            "anchor_para": self.anchor_para,
            "documentary_target": self.documentary_target,
            "work_hint_present": self.work_hint_present,
            "document_hint_present": self.document_hint_present,
        }


class BiblioWorkResolver:
    def __init__(self, client: CatalogueClient) -> None:
        self._client = client

    def resolve(self, plan: BiblioQueryPlan) -> BiblioWorkResolution:
        endpoint_observations: list[CatalogueEndpointObservation] = []
        try:
            catalog_items: list[Mapping[str, Any]] = []
            if plan.document_title or plan.author:
                for query in _candidate_queries(plan.document_title_variants, plan.document_title, plan.author):
                    catalog_response = self._client.catalog(
                        q=query,
                        limit=DOCUMENT_QUERY_LIMIT,
                        offset=0,
                    )
                    endpoint_observations.append(observe_catalogue_response(catalog_response))
                    catalog_items = _catalog_items(catalog_response)
                    if catalog_items:
                        break

            chapter_rows: list[Mapping[str, Any]] = []
            resolved_doc_id = plan.document_id or _single_catalog_document_id(catalog_items)
            if plan.work_title and resolved_doc_id:
                chapters_response = self._client.chapters(resolved_doc_id, limit=500, offset=0)
                endpoint_observations.append(observe_catalogue_response(chapters_response))
                chapter_rows = _matching_chapters(
                    chapters_response,
                    _candidate_queries(plan.work_title_variants, plan.work_title),
                )

            chapter_search_rows: list[Mapping[str, Any]] = []
            chapter_search_doc_id = ""
            if plan.work_title and not resolved_doc_id:
                chapter_queries = _candidate_queries(plan.work_title_variants, plan.work_title)
                for query in chapter_queries:
                    chapter_search_response = self._client.search_chapters(query, limit=WORK_SEARCH_LIMIT)
                    endpoint_observations.append(observe_catalogue_response(chapter_search_response))
                    chapter_search_rows = _chapter_search_results(chapter_search_response)
                    if chapter_search_rows:
                        chapter_search_doc_id = _committed_chapter_search_document_id(
                            chapter_search_rows,
                            chapter_queries,
                        )
                        break
                if chapter_search_doc_id:
                    resolved_doc_id = chapter_search_doc_id

            search_rows: list[Mapping[str, Any]] = []
            structural_work_match = bool(chapter_rows) or bool(chapter_search_doc_id)
            if plan.work_title and (plan.locator or plan.locator_end or not structural_work_match):
                for query in _candidate_queries(plan.work_title_variants, plan.work_title):
                    search_response = self._client.search(query, limit=WORK_SEARCH_LIMIT)
                    endpoint_observations.append(observe_catalogue_response(search_response))
                    search_rows = _search_results(search_response)
                    if search_rows:
                        break

        except CatalogueClientError as exc:
            return BiblioWorkResolution(
                status=STATUS_CATALOGUE_UNAVAILABLE,
                reason_code=REASON_CATALOGUE_UNAVAILABLE,
                endpoint_observations=tuple(endpoint_observations),
                client_error=exc,
                documentary_target=_documentary_target(plan),
                work_hint_present=bool(plan.work_title),
                document_hint_present=bool(plan.document_title or plan.author or plan.document_id),
            )

        anchor = _select_anchor(search_rows, catalog_items)
        candidate_ids = _candidate_ids(catalog_items, search_rows, chapter_search_rows)
        if not (plan.document_id or plan.document_title or plan.author or plan.work_title):
            return BiblioWorkResolution(
                status=STATUS_NOT_FOUND,
                reason_code=REASON_WORK_NOT_FOUND,
                endpoint_observations=tuple(endpoint_observations),
                document_candidate_ids=candidate_ids,
                search_result_count=len(search_rows),
                catalog_result_count=len(catalog_items),
                documentary_target=_documentary_target(plan),
                work_hint_present=bool(plan.work_title),
                document_hint_present=bool(plan.document_title or plan.author or plan.document_id),
            )

        anchor_document_id = plan.document_id or _committed_anchor_document_id(anchor, catalog_items)
        if not anchor_document_id and chapter_rows:
            anchor_document_id = resolved_doc_id or ""
        if not anchor_document_id and chapter_search_doc_id:
            anchor_document_id = chapter_search_doc_id
        request = BiblioResolveRequest(
            document_id=anchor_document_id,
            title=plan.document_title or ("" if anchor_document_id else plan.work_title),
            document_title=plan.document_title,
            work_title=plan.work_title,
            author=plan.author,
            locator=plan.locator,
            locator_end=plan.locator_end,
            locator_kind=plan.locator_kind,
            locator_anchor_page=anchor.page_no if anchor else None,
            locator_anchor_para=anchor.para_no if anchor else None,
        )
        status = STATUS_RESOLVED if (request.document_id or request.title or request.author) else STATUS_SEARCHED
        reason = REASON_WORK_RESOLVED if status == STATUS_RESOLVED else REASON_WORK_SEARCHED
        return BiblioWorkResolution(
            status=status,
            reason_code=reason,
            resolve_request=request,
            endpoint_observations=tuple(endpoint_observations),
            document_candidate_ids=candidate_ids,
            search_result_count=len(search_rows),
            catalog_result_count=len(catalog_items),
            anchor_doc_id_short=short_doc_id(anchor.document_id) if anchor else "",
            anchor_page=anchor.page_no if anchor else None,
            anchor_para=anchor.para_no if anchor else None,
            documentary_target=_documentary_target(plan),
            work_hint_present=bool(plan.work_title),
            document_hint_present=bool(plan.document_title or plan.author or plan.document_id),
        )


@dataclass(frozen=True)
class _Anchor:
    document_id: str
    page_no: int | None = None
    para_no: int | None = None


def _catalog_items(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    items = response.payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _matching_chapters(
    response: CatalogueResponse,
    queries: Sequence[str],
) -> list[Mapping[str, Any]]:
    chapters = response.payload.get("chapters")
    if not isinstance(chapters, list):
        return []
    query_token_sequences = tuple(
        dict.fromkeys(
            _normalized_word_sequence(query)
            for query in queries
            if _normalized_word_sequence(query)
        )
    )
    if not query_token_sequences:
        return []
    matched: list[Mapping[str, Any]] = []
    for chapter in chapters:
        if not isinstance(chapter, Mapping):
            continue
        title_tokens = _normalized_word_sequence(chapter.get("title"))
        if not title_tokens:
            continue
        if any(_chapter_tokens_match(title_tokens, query_tokens) for query_tokens in query_token_sequences):
            matched.append(chapter)
    return matched


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


def _chapter_search_results(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    results = response.payload.get("results")
    if not isinstance(results, list):
        return []
    return [item for item in results if isinstance(item, Mapping)]


def _select_anchor(
    search_rows: Sequence[Mapping[str, Any]],
    catalog_items: Sequence[Mapping[str, Any]],
) -> _Anchor | None:
    if not search_rows:
        return None
    catalog_doc_ids = {_text(item.get("id") or item.get("document_id")) for item in catalog_items}
    catalog_doc_ids.discard("")
    rows = [
        row
        for row in search_rows
        if not catalog_doc_ids or _text(row.get("document_id")) in catalog_doc_ids
    ]
    if not rows:
        return None

    counts = Counter(_text(row.get("document_id")) for row in rows if _text(row.get("document_id")))
    if not counts:
        return None
    ranked = counts.most_common(2)
    if len(ranked) > 1 and ranked[0][1] == ranked[1][1]:
        return None
    doc_id = ranked[0][0]
    for row in rows:
        if _text(row.get("document_id")) == doc_id:
            return _Anchor(
                document_id=doc_id,
                page_no=_optional_int(row.get("page_no")),
                para_no=_optional_int(row.get("para_no")),
            )
    return None


def _candidate_ids(
    catalog_items: Sequence[Mapping[str, Any]],
    search_rows: Sequence[Mapping[str, Any]],
    chapter_search_rows: Sequence[Mapping[str, Any]],
) -> tuple[str, ...]:
    ids: list[str] = []
    for item in catalog_items:
        doc_id = _text(item.get("id") or item.get("document_id"))
        if doc_id:
            ids.append(short_doc_id(doc_id))
    for row in search_rows:
        doc_id = _text(row.get("document_id"))
        if doc_id:
            ids.append(short_doc_id(doc_id))
    for row in chapter_search_rows:
        doc_id = _text(row.get("document_id"))
        if doc_id:
            ids.append(short_doc_id(doc_id))
    return tuple(dict.fromkeys(ids))


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _normalized_work_key(value: Any) -> str:
    text = unicodedata.normalize("NFKD", _text(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text.casefold())
    return " ".join(text.split())


def _normalized_word_sequence(value: Any) -> tuple[str, ...]:
    normalized = _normalized_work_key(value)
    if not normalized:
        return ()
    return tuple(normalized.split())


def _chapter_tokens_match(title_tokens: Sequence[str], query_tokens: Sequence[str]) -> bool:
    if not title_tokens or not query_tokens:
        return False
    query_length = len(query_tokens)
    if query_length == 1:
        return query_tokens[0] in title_tokens
    if query_length > len(title_tokens):
        return False
    for start in range(len(title_tokens) - query_length + 1):
        if tuple(title_tokens[start : start + query_length]) == tuple(query_tokens):
            return True
    return False


def _text(value: Any) -> str:
    return str(value or "").strip()


def _committed_chapter_search_document_id(
    rows: Sequence[Mapping[str, Any]],
    queries: Sequence[str],
) -> str:
    query_token_sequences = tuple(
        dict.fromkeys(
            _normalized_word_sequence(query)
            for query in queries
            if _normalized_word_sequence(query)
        )
    )
    if not query_token_sequences:
        return ""
    matched_rows = [
        row
        for row in rows
        if _chapter_search_row_matches_query(row, query_token_sequences)
    ]
    if not matched_rows:
        return ""
    return _single_row_document_id(matched_rows)


def _chapter_search_row_matches_query(
    row: Mapping[str, Any],
    query_token_sequences: Sequence[Sequence[str]],
) -> bool:
    title_tokens = _normalized_word_sequence(row.get("chapter_title") or row.get("title"))
    if not title_tokens:
        return False
    return any(_chapter_search_tokens_match(title_tokens, query_tokens) for query_tokens in query_token_sequences)


def _chapter_search_tokens_match(title_tokens: Sequence[str], query_tokens: Sequence[str]) -> bool:
    if not title_tokens or not query_tokens:
        return False
    if len(query_tokens) == 1:
        return len(title_tokens) == 1 and title_tokens[0] == query_tokens[0]
    return _chapter_tokens_match(title_tokens, query_tokens)


def _single_row_document_id(rows: Sequence[Mapping[str, Any]]) -> str:
    doc_ids = tuple(
        dict.fromkeys(
            _text(row.get("document_id"))
            for row in rows
            if _text(row.get("document_id"))
        )
    )
    if len(doc_ids) == 1:
        return doc_ids[0]
    return ""


def _documentary_target(plan: BiblioQueryPlan) -> str:
    if plan.document_id:
        return "document_id"
    if plan.work_title and (plan.document_title or plan.author):
        return "work_in_document"
    if plan.work_title:
        return "work"
    if plan.document_title and plan.author:
        return "document_with_author"
    if plan.document_title:
        return "document_or_volume"
    if plan.author:
        return "author_or_corpus"
    return ""


def _committed_anchor_document_id(
    anchor: _Anchor | None,
    catalog_items: Sequence[Mapping[str, Any]],
) -> str:
    if anchor is None or not anchor.document_id:
        return ""
    if not catalog_items:
        return anchor.document_id
    catalog_doc_ids = {
        _text(item.get("id") or item.get("document_id"))
        for item in catalog_items
        if _text(item.get("id") or item.get("document_id"))
    }
    if len(catalog_doc_ids) == 1 and anchor.document_id in catalog_doc_ids:
        return anchor.document_id
    return ""


def _single_catalog_document_id(catalog_items: Sequence[Mapping[str, Any]]) -> str:
    catalog_doc_ids = tuple(
        dict.fromkeys(
            _text(item.get("id") or item.get("document_id"))
            for item in catalog_items
            if _text(item.get("id") or item.get("document_id"))
        )
    )
    if len(catalog_doc_ids) == 1:
        return catalog_doc_ids[0]
    return ""
