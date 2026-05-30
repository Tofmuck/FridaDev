"""Runtime for the Biblio librarian consultation lane.

This module executes a structured Biblio query plan against the read-only
Catalogue client.  It may build prompt content for the main model, but its
observability projection is content-free by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueClient, CatalogueClientError, CatalogueResponse, short_doc_id
from .passage_extractor import (
    BiblioPassageExtractor,
    BiblioPassageRequest,
    BiblioPassageResult,
    DEFAULT_CONTEXT_WINDOW_CHARS,
    DEFAULT_MAX_PASSAGE_CHARS,
    MAX_CONTEXT_WINDOW_CHARS,
    STATUS_EXTRACTED,
)
from .prompt_lane import BiblioPromptLane, LANE_FOOTER, LANE_HEADER, build_biblio_prompt_lane
from .query_planner import (
    INTENT_EXTRACT_PASSAGE,
    INTENT_EXTRACT_RANGE,
    INTENT_LIST_CATALOG,
    INTENT_RESOLVE_WORK,
    INTENT_SEARCH_CATALOG,
    BiblioQueryPlan,
)
from .work_resolver import BiblioWorkResolution, BiblioWorkResolver


CONSULTATION_HEADER = "[CONSULTATION DE BIBLIOTHEQUE]"
CONSULTATION_FOOTER = "[/CONSULTATION DE BIBLIOTHEQUE]"

STATUS_LISTED = "listed"
STATUS_SEARCHED = "searched"
STATUS_EXTRACTED_OR_LANE = "extracted"
STATUS_NOT_FOUND = "not_found"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"

REASON_CATALOG_LISTED = "biblio_catalog_listed"
REASON_CATALOG_SEARCHED = "biblio_catalog_searched"
REASON_PASSAGE_LANE_READY = "biblio_passage_lane_ready"
REASON_PASSAGE_NOT_EXTRACTED = "biblio_passage_not_extracted"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_LIST_LIMIT = 5
DEFAULT_SEARCH_LIMIT = 8
DEFAULT_RANGE_WINDOW_CHARS = MAX_CONTEXT_WINDOW_CHARS
DEFAULT_RANGE_MAX_PASSAGE_CHARS = 7_000


@dataclass(frozen=True)
class BiblioConsultationMessage:
    message: dict[str, Any] | None = field(default=None, repr=False, compare=False)
    status: str = STATUS_SKIPPED
    reason_code: str = ""
    item_count: int = 0
    chars: int = 0
    doc_id_shorts: tuple[str, ...] = field(default_factory=tuple)

    def to_observability(self) -> dict[str, Any]:
        return {
            "present": self.message is not None,
            "status": self.status,
            "reason_code": self.reason_code,
            "item_count": self.item_count,
            "chars": self.chars,
            "doc_id_shorts": list(self.doc_id_shorts),
        }


@dataclass(frozen=True, repr=False)
class BiblioLibraryRuntimeResult:
    status: str
    reason_code: str
    query_kind: str
    client_responses: tuple[CatalogueResponse, ...] = field(default_factory=tuple, repr=False, compare=False)
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    work_resolution: BiblioWorkResolution | None = field(default=None, repr=False, compare=False)
    passage_result: BiblioPassageResult | None = field(default=None, repr=False, compare=False)
    prompt_lane: BiblioPromptLane | None = field(default=None, repr=False, compare=False)
    consultation_message: BiblioConsultationMessage | None = field(default=None, repr=False, compare=False)

    @property
    def prompt_message(self) -> dict[str, Any] | None:
        if self.prompt_lane and self.prompt_lane.message:
            return self.prompt_lane.message
        if self.consultation_message and self.consultation_message.message:
            return self.consultation_message.message
        return None

    def client_observability(self) -> list[dict[str, Any]]:
        items = [dict(response.to_observability()) for response in self.client_responses]
        if self.client_error is not None:
            items.append(dict(self.client_error.to_observability()))
        return items


def run_biblio_library_plan(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
    *,
    extractor_factory: Any = BiblioPassageExtractor,
    lane_builder: Any = build_biblio_prompt_lane,
    work_resolver_factory: Any = BiblioWorkResolver,
) -> BiblioLibraryRuntimeResult:
    if plan.intent == INTENT_LIST_CATALOG:
        return _list_catalog(client, plan)
    if plan.intent == INTENT_SEARCH_CATALOG:
        return _search_catalog(client, plan)
    if plan.intent in {INTENT_EXTRACT_PASSAGE, INTENT_EXTRACT_RANGE, INTENT_RESOLVE_WORK}:
        return _resolve_and_extract(
            client,
            plan,
            extractor_factory=extractor_factory,
            lane_builder=lane_builder,
            work_resolver_factory=work_resolver_factory,
        )
    consultation = _consultation_message(
        status=STATUS_SKIPPED,
        reason_code=plan.reason_code,
        lines=["Aucune consultation Catalogue n'a ete necessaire."],
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_SKIPPED,
        reason_code=plan.reason_code,
        query_kind=plan.query_kind,
        consultation_message=consultation,
    )


def _list_catalog(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    try:
        response = client.catalog(limit=plan.limit or DEFAULT_LIST_LIMIT, offset=0)
    except CatalogueClientError as exc:
        return _client_error(plan, exc)
    items = _catalog_items(response)[: plan.limit or DEFAULT_LIST_LIMIT]
    consultation = _catalog_consultation_message(
        status=STATUS_LISTED,
        reason_code=REASON_CATALOG_LISTED,
        heading="Premiers ouvrages disponibles:",
        items=items,
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_LISTED,
        reason_code=REASON_CATALOG_LISTED,
        query_kind=plan.query_kind,
        client_responses=(response,),
        consultation_message=consultation,
    )


def _search_catalog(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    responses: list[CatalogueResponse] = []
    try:
        response = client.catalog(q=plan.catalogue_query, limit=plan.limit or DEFAULT_SEARCH_LIMIT, offset=0)
        responses.append(response)
        items = _catalog_items(response)[: plan.limit or DEFAULT_SEARCH_LIMIT]
        if items:
            consultation = _catalog_consultation_message(
                status=STATUS_SEARCHED,
                reason_code=REASON_CATALOG_SEARCHED,
                heading="Candidats Catalogue trouves:",
                items=items,
            )
            return BiblioLibraryRuntimeResult(
                status=STATUS_SEARCHED,
                reason_code=REASON_CATALOG_SEARCHED,
                query_kind=plan.query_kind,
                client_responses=tuple(responses),
                consultation_message=consultation,
            )
        if plan.work_title:
            search_response = client.search(plan.work_title, limit=plan.limit or DEFAULT_SEARCH_LIMIT)
            responses.append(search_response)
            rows = _search_results(search_response)
            consultation = _search_consultation_message(rows)
            return BiblioLibraryRuntimeResult(
                status=STATUS_SEARCHED if rows else STATUS_NOT_FOUND,
                reason_code=REASON_CATALOG_SEARCHED if rows else REASON_PASSAGE_NOT_EXTRACTED,
                query_kind=plan.query_kind,
                client_responses=tuple(responses),
                consultation_message=consultation,
            )
    except CatalogueClientError as exc:
        return _client_error(plan, exc, responses=responses)

    consultation = _consultation_message(
        status=STATUS_NOT_FOUND,
        reason_code=REASON_PASSAGE_NOT_EXTRACTED,
        lines=["Catalogue consulte; aucun candidat fiable n'a ete trouve."],
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_NOT_FOUND,
        reason_code=REASON_PASSAGE_NOT_EXTRACTED,
        query_kind=plan.query_kind,
        client_responses=tuple(responses),
        consultation_message=consultation,
    )


def _resolve_and_extract(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
    *,
    extractor_factory: Any,
    lane_builder: Any,
    work_resolver_factory: Any,
) -> BiblioLibraryRuntimeResult:
    work_resolution = work_resolver_factory(client).resolve(plan)
    responses = list(work_resolution.client_responses)
    if work_resolution.client_error is not None:
        return BiblioLibraryRuntimeResult(
            status=STATUS_ERROR,
            reason_code=REASON_CATALOGUE_UNAVAILABLE,
            query_kind=plan.query_kind,
            client_responses=tuple(responses),
            client_error=work_resolution.client_error,
            work_resolution=work_resolution,
        )
    if work_resolution.resolve_request is None:
        consultation = _consultation_message(
            status=work_resolution.status,
            reason_code=work_resolution.reason_code,
            lines=["Catalogue consulte; resolution documentaire insuffisante."],
            doc_id_shorts=work_resolution.document_candidate_ids,
        )
        return BiblioLibraryRuntimeResult(
            status=work_resolution.status,
            reason_code=work_resolution.reason_code,
            query_kind=plan.query_kind,
            client_responses=tuple(responses),
            work_resolution=work_resolution,
            consultation_message=consultation,
        )

    request = BiblioPassageRequest(
        resolve_request=work_resolution.resolve_request,
        window_chars=DEFAULT_RANGE_WINDOW_CHARS if plan.intent == INTENT_EXTRACT_RANGE else DEFAULT_CONTEXT_WINDOW_CHARS,
        max_passage_chars=DEFAULT_RANGE_MAX_PASSAGE_CHARS
        if plan.intent == INTENT_EXTRACT_RANGE
        else DEFAULT_MAX_PASSAGE_CHARS,
    )
    passage_result = extractor_factory(client).extract(request)
    prompt_lane = lane_builder([passage_result])
    if passage_result.status == STATUS_EXTRACTED and prompt_lane.message:
        return BiblioLibraryRuntimeResult(
            status=STATUS_EXTRACTED_OR_LANE,
            reason_code=REASON_PASSAGE_LANE_READY,
            query_kind=plan.query_kind,
            client_responses=tuple(responses),
            work_resolution=work_resolution,
            passage_result=passage_result,
            prompt_lane=prompt_lane,
        )

    consultation = _consultation_message(
        status=passage_result.status,
        reason_code=passage_result.reason_code,
        lines=["Catalogue consulte; aucun passage n'a ete injecte."],
        doc_id_shorts=work_resolution.document_candidate_ids,
    )
    return BiblioLibraryRuntimeResult(
        status=passage_result.status,
        reason_code=passage_result.reason_code,
        query_kind=plan.query_kind,
        client_responses=tuple(responses),
        work_resolution=work_resolution,
        passage_result=passage_result,
        prompt_lane=prompt_lane,
        consultation_message=consultation,
    )


def _client_error(
    plan: BiblioQueryPlan,
    exc: CatalogueClientError,
    *,
    responses: Sequence[CatalogueResponse] = (),
) -> BiblioLibraryRuntimeResult:
    return BiblioLibraryRuntimeResult(
        status=STATUS_ERROR,
        reason_code=REASON_CATALOGUE_UNAVAILABLE,
        query_kind=plan.query_kind,
        client_responses=tuple(responses),
        client_error=exc,
    )


def _catalog_consultation_message(
    *,
    status: str,
    reason_code: str,
    heading: str,
    items: Sequence[Mapping[str, Any]],
) -> BiblioConsultationMessage:
    lines = [heading]
    doc_ids: list[str] = []
    for index, item in enumerate(items, 1):
        doc_id = _text(item.get("id") or item.get("document_id"))
        doc_short = short_doc_id(doc_id)
        doc_ids.append(doc_short)
        title = _display_title(item)
        author = _display_author(item)
        source = f"catalogue_doc={doc_short or 'unknown'}"
        details = f"{source}; titre={title or 'non renseigne'}"
        if author:
            details = f"{details}; auteur={author}"
        lines.append(f"{index}. {details}")
    return _consultation_message(
        status=status,
        reason_code=reason_code,
        lines=lines,
        doc_id_shorts=tuple(doc_id for doc_id in doc_ids if doc_id),
    )


def _search_consultation_message(rows: Sequence[Mapping[str, Any]]) -> BiblioConsultationMessage:
    doc_lines: list[str] = ["Recherche interne Catalogue effectuee:"]
    doc_ids: list[str] = []
    seen: set[str] = set()
    for row in rows:
        doc_id = _text(row.get("document_id"))
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        doc_short = short_doc_id(doc_id)
        doc_ids.append(doc_short)
        title = _neutralize(_text(row.get("title"))) or "document candidat"
        doc_lines.append(f"- catalogue_doc={doc_short}; titre={title}")
    if len(doc_lines) == 1:
        doc_lines.append("Aucun candidat interne fiable.")
    return _consultation_message(
        status=STATUS_SEARCHED if doc_ids else STATUS_NOT_FOUND,
        reason_code=REASON_CATALOG_SEARCHED if doc_ids else REASON_PASSAGE_NOT_EXTRACTED,
        lines=doc_lines,
        doc_id_shorts=tuple(doc_ids),
    )


def _consultation_message(
    *,
    status: str,
    reason_code: str,
    lines: Sequence[str],
    doc_id_shorts: Sequence[str] = (),
) -> BiblioConsultationMessage:
    body = [
        "Contrat d'interpretation:",
        "- Cette consultation provient de la bibliotheque persistante, a la demande.",
        "- Elle ne prouve pas que tout l'ouvrage ou tout le corpus a ete lu.",
        "- Ne confonds pas cette consultation avec les documents actifs, la memoire, le web, l'identite ou le resume.",
        f"Statut: {status}",
        f"Raison: {reason_code}",
        *_neutralized_lines(lines),
    ]
    content = "\n".join([CONSULTATION_HEADER, *body, CONSULTATION_FOOTER])
    return BiblioConsultationMessage(
        message={"role": "system", "content": content},
        status=status,
        reason_code=reason_code,
        item_count=len([line for line in lines if str(line).strip()]),
        chars=len(content),
        doc_id_shorts=tuple(doc_id_shorts),
    )


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


def _display_title(item: Mapping[str, Any]) -> str:
    return _neutralize(
        _text(item.get("human_canonical_title") or item.get("canonical_title") or item.get("title"))
    )


def _display_author(item: Mapping[str, Any]) -> str:
    return _neutralize(_text(item.get("human_authors") or item.get("authors")))


def _neutralized_lines(lines: Sequence[str]) -> list[str]:
    return [_neutralize(str(line or "")) for line in lines if str(line or "").strip()]


def _neutralize(value: str) -> str:
    text = str(value or "")
    replacements = {
        LANE_HEADER: "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]",
        LANE_FOOTER: "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]",
        CONSULTATION_HEADER: "[CONSULTATION DE BIBLIOTHEQUE neutralise]",
        CONSULTATION_FOOTER: "[/CONSULTATION DE BIBLIOTHEQUE neutralise]",
    }
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)
    return text


def _text(value: Any) -> str:
    return str(value or "").strip()
