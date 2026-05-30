"""Resolve internal works into Catalogue document and locator hints.

Catalogue currently stores physical documents and searchable paragraphs.  This
layer bridges natural requests such as "Theetete de Platon 126b" by using
catalog metadata plus content search only as an internal anchor.  Its public
projection stays content-free.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueClient, CatalogueClientError, CatalogueResponse, short_doc_id
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
    client_responses: tuple[CatalogueResponse, ...] = field(default_factory=tuple, repr=False, compare=False)
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    document_candidate_ids: tuple[str, ...] = field(default_factory=tuple)
    search_result_count: int = 0
    catalog_result_count: int = 0
    anchor_doc_id_short: str = ""
    anchor_page: int | None = None
    anchor_para: int | None = None

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
        }


class BiblioWorkResolver:
    def __init__(self, client: CatalogueClient) -> None:
        self._client = client

    def resolve(self, plan: BiblioQueryPlan) -> BiblioWorkResolution:
        responses: list[CatalogueResponse] = []
        try:
            catalog_items: list[Mapping[str, Any]] = []
            if plan.document_title or plan.author:
                catalog_response = self._client.catalog(
                    q=plan.document_title or plan.author,
                    limit=DOCUMENT_QUERY_LIMIT,
                    offset=0,
                )
                responses.append(catalog_response)
                catalog_items = _catalog_items(catalog_response)

            search_rows: list[Mapping[str, Any]] = []
            if plan.work_title:
                search_response = self._client.search(plan.work_title, limit=WORK_SEARCH_LIMIT)
                responses.append(search_response)
                search_rows = _search_results(search_response)

        except CatalogueClientError as exc:
            return BiblioWorkResolution(
                status=STATUS_CATALOGUE_UNAVAILABLE,
                reason_code=REASON_CATALOGUE_UNAVAILABLE,
                client_responses=tuple(responses),
                client_error=exc,
            )

        anchor = _select_anchor(search_rows, catalog_items)
        candidate_ids = _candidate_ids(catalog_items, search_rows)
        if not (plan.document_id or plan.document_title or plan.author or plan.work_title):
            return BiblioWorkResolution(
                status=STATUS_NOT_FOUND,
                reason_code=REASON_WORK_NOT_FOUND,
                client_responses=tuple(responses),
                document_candidate_ids=candidate_ids,
                search_result_count=len(search_rows),
                catalog_result_count=len(catalog_items),
            )

        request = BiblioResolveRequest(
            document_id=plan.document_id or (anchor.document_id if anchor and not (plan.document_title or plan.author) else ""),
            title=plan.document_title or ("" if anchor else plan.work_title),
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
            client_responses=tuple(responses),
            document_candidate_ids=candidate_ids,
            search_result_count=len(search_rows),
            catalog_result_count=len(catalog_items),
            anchor_doc_id_short=short_doc_id(anchor.document_id) if anchor else "",
            anchor_page=anchor.page_no if anchor else None,
            anchor_para=anchor.para_no if anchor else None,
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


def _search_results(response: CatalogueResponse) -> list[Mapping[str, Any]]:
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
    return tuple(dict.fromkeys(ids))


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _text(value: Any) -> str:
    return str(value or "").strip()
