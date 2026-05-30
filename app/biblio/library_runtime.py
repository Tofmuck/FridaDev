"""Runtime for the Biblio librarian consultation lane.

This module executes a structured Biblio query plan against the read-only
Catalogue client.  It may build prompt content for the main model, but its
observability projection is content-free by construction.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import (
    CatalogueClient,
    CatalogueClientError,
    CatalogueEndpointObservation,
    CatalogueResponse,
    observe_catalogue_response,
    short_doc_id,
)
from .passage_extractor import (
    BiblioPassageExtractor,
    BiblioPassageRequest,
    BiblioPassageResult,
    DEFAULT_CONTEXT_WINDOW_CHARS,
    DEFAULT_MAX_PASSAGE_CHARS,
    MAX_CONTEXT_WINDOW_CHARS,
    STATUS_EXTRACTED,
)
from .passage_context_search import (
    BiblioPassageContextSearcher,
    BiblioPassageContextSearchResult,
    STATUS_CATALOGUE_UNAVAILABLE as CONTEXT_STATUS_CATALOGUE_UNAVAILABLE,
)
from .prompt_lane import BiblioPromptLane, LANE_FOOTER, LANE_HEADER, build_biblio_prompt_lane
from .query_planner import (
    INTENT_EXTRACT_PASSAGE,
    INTENT_EXTRACT_RANGE,
    INTENT_LIST_CATALOG,
    INTENT_OPEN_DOCUMENT,
    INTENT_RESOLVE_WORK,
    INTENT_SEARCH_CATALOG,
    INTENT_SHOW_TABLE_OF_CONTENTS,
    BiblioQueryPlan,
)
from .work_resolver import BiblioWorkResolution, BiblioWorkResolver


CONSULTATION_HEADER = "[CONSULTATION DE BIBLIOTHEQUE]"
CONSULTATION_FOOTER = "[/CONSULTATION DE BIBLIOTHEQUE]"

STATUS_LISTED = "listed"
STATUS_OPENED = "opened"
STATUS_TOC_LISTED = "toc_listed"
STATUS_TOC_SUMMARY = "toc_summary"
STATUS_EXTRACTED_OR_LANE = "extracted"
STATUS_SKIPPED = "skipped"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_ERROR = "error"

REASON_CATALOG_LISTED = "biblio_catalog_listed"
REASON_DOCUMENT_OPENED = "biblio_document_opened"
REASON_DOCUMENT_NOT_FOUND = "biblio_document_not_found"
REASON_DOCUMENT_AMBIGUOUS = "biblio_document_ambiguous"
REASON_TOC_LISTED = "biblio_table_of_contents_listed"
REASON_TOC_SUMMARY = "biblio_table_of_contents_summary"
REASON_TOC_NOT_FOUND = "biblio_table_of_contents_not_found"
REASON_TOC_DETAIL_ROUTE_SKIPPED = "biblio_table_of_contents_detail_route_skipped"
REASON_PASSAGE_LANE_READY = "biblio_passage_lane_ready"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_LIST_LIMIT = 100
MAX_COMPLETE_CATALOGUE_ITEMS = 100
MAX_TOC_ITEMS = 100
MAX_DOCUMENT_OVERVIEW_PARAGRAPHS = 5_000
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
    total_count: int | None = None
    displayed_count: int | None = None
    truncated: bool = False

    def to_observability(self) -> dict[str, Any]:
        return {
            "present": self.message is not None,
            "status": self.status,
            "reason_code": self.reason_code,
            "item_count": self.item_count,
            "chars": self.chars,
            "doc_id_shorts": list(self.doc_id_shorts),
            "total_count": self.total_count,
            "displayed_count": self.displayed_count,
            "truncated": self.truncated,
        }


@dataclass(frozen=True, repr=False)
class BiblioLibraryRuntimeResult:
    status: str
    reason_code: str
    query_kind: str
    endpoint_observations: tuple[CatalogueEndpointObservation, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    work_resolution: BiblioWorkResolution | None = field(default=None, repr=False, compare=False)
    context_result: BiblioPassageContextSearchResult | None = field(default=None, repr=False, compare=False)
    passage_result: BiblioPassageResult | None = field(default=None, repr=False, compare=False)
    passage_results: tuple[BiblioPassageResult, ...] = field(default_factory=tuple, repr=False, compare=False)
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
        items = [dict(observation.to_observability()) for observation in self.endpoint_observations]
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
    context_searcher_factory: Any = BiblioPassageContextSearcher,
) -> BiblioLibraryRuntimeResult:
    if plan.intent == INTENT_LIST_CATALOG:
        return _list_catalog(client, plan)
    if plan.intent == INTENT_OPEN_DOCUMENT:
        return _open_document(client, plan)
    if plan.intent == INTENT_SHOW_TABLE_OF_CONTENTS:
        return _show_table_of_contents(client, plan)
    if plan.intent == INTENT_SEARCH_CATALOG:
        return _search_passages(
            client,
            plan,
            lane_builder=lane_builder,
            context_searcher_factory=context_searcher_factory,
        )
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
        limit = _list_limit(plan.limit)
        response = client.catalog(limit=limit, offset=0)
    except CatalogueClientError as exc:
        return _client_error(plan, exc)
    items = _catalog_items(response)
    total = _catalog_total(response, fallback=len(items))
    truncated = total > len(items)
    heading = (
        f"Catalogue disponible: {total} ouvrages. Liste complete affichee."
        if not truncated
        else f"Catalogue disponible: {total} ouvrages. Affichage des {len(items)} premiers; demande la suite pour continuer."
    )
    consultation = _catalog_consultation_message(
        status=STATUS_LISTED,
        reason_code=REASON_CATALOG_LISTED,
        heading=heading,
        items=items,
        total_count=total,
        displayed_count=len(items),
        truncated=truncated,
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_LISTED,
        reason_code=REASON_CATALOG_LISTED,
        query_kind=plan.query_kind,
        endpoint_observations=(observe_catalogue_response(response),),
        consultation_message=consultation,
    )


def _open_document(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    return _catalogue_document_summary(
        client,
        plan,
        status=STATUS_OPENED,
        reason_code=REASON_DOCUMENT_OPENED,
        not_found_reason=REASON_DOCUMENT_NOT_FOUND,
        ambiguous_reason=REASON_DOCUMENT_AMBIGUOUS,
        heading="Document Catalogue trouve:",
    )


def _show_table_of_contents(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    query = _catalogue_query(plan)
    endpoint_observations: list[CatalogueEndpointObservation] = []
    try:
        response = client.catalog(q=query or None, limit=plan.limit or 8, offset=0)
        endpoint_observations.append(observe_catalogue_response(response))
    except CatalogueClientError as exc:
        return _client_error(plan, exc)

    items = _catalog_items(response)
    if not items:
        consultation = _consultation_message(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            lines=["Aucun document Catalogue correspondant n'a ete trouve pour la table des matieres."],
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    selected = items[0]
    if len(items) > 1:
        consultation = _document_candidates_message(
            status=STATUS_AMBIGUOUS,
            reason_code=REASON_DOCUMENT_AMBIGUOUS,
            heading="Plusieurs documents Catalogue correspondent a la demande de table des matieres:",
            items=items,
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_AMBIGUOUS,
            reason_code=REASON_DOCUMENT_AMBIGUOUS,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    chapter_count = _optional_int(selected.get("chapter_count")) or 0
    paragraph_count = _optional_int(selected.get("paragraph_count")) or 0
    doc_id = _text(selected.get("id") or selected.get("document_id"))
    if chapter_count <= 0:
        consultation = _consultation_message(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            lines=[
                "Document trouve, mais aucune table des matieres structuree n'est signalee par Catalogue.",
                *_document_summary_lines(selected),
            ],
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    if paragraph_count > MAX_DOCUMENT_OVERVIEW_PARAGRAPHS:
        consultation = _consultation_message(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_DETAIL_ROUTE_SKIPPED,
            lines=[
                "Table des matieres signalee par Catalogue, mais la route detaillee actuelle passe par une vue document trop lourde pour une consultation bornee.",
                f"Chapitres signales: {chapter_count}.",
                "Correctif plateforme requis: GET leger de chapitres/table des matieres.",
                *_document_summary_lines(selected),
            ],
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=chapter_count,
            displayed_count=0,
            truncated=True,
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_DETAIL_ROUTE_SKIPPED,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    try:
        overview = client.document(doc_id)
        endpoint_observations.append(observe_catalogue_response(overview))
    except CatalogueClientError as exc:
        consultation = _consultation_message(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            lines=[
                "Table des matieres signalee par Catalogue, mais le detail n'a pas pu etre lu via la route document actuelle.",
                f"Chapitres signales: {chapter_count}.",
                *_document_summary_lines(selected),
            ],
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=chapter_count,
            displayed_count=0,
            truncated=True,
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            client_error=exc,
            consultation_message=consultation,
        )

    chapters = _chapters(overview)
    if not chapters:
        consultation = _consultation_message(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            lines=[
                "Document lu, mais aucune entree de table des matieres exploitable n'a ete retournee.",
                f"Chapitres signales: {chapter_count}.",
                *_document_summary_lines(selected),
            ],
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=chapter_count,
            displayed_count=0,
            truncated=True,
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    displayed = chapters[:MAX_TOC_ITEMS]
    truncated = len(chapters) > len(displayed)
    lines = [
        (
            f"Table des matieres disponible: {len(chapters)} entrees. Liste complete affichee."
            if not truncated
            else f"Table des matieres disponible: {len(chapters)} entrees. Affichage des {len(displayed)} premieres."
        ),
        *_document_summary_lines(selected),
        *_chapter_lines(displayed),
    ]
    consultation = _consultation_message(
        status=STATUS_TOC_LISTED,
        reason_code=REASON_TOC_LISTED,
        lines=lines,
        doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        total_count=len(chapters),
        displayed_count=len(displayed),
        truncated=truncated,
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_TOC_LISTED,
        reason_code=REASON_TOC_LISTED,
        query_kind=plan.query_kind,
        endpoint_observations=tuple(endpoint_observations),
        consultation_message=consultation,
    )


def _search_passages(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
    *,
    lane_builder: Any,
    context_searcher_factory: Any,
) -> BiblioLibraryRuntimeResult:
    context_result = context_searcher_factory(client).search(plan)
    endpoint_observations = _context_endpoint_observations(context_result)
    passage_results = tuple(context_result.passage_results)
    prompt_lane = lane_builder(passage_results)
    if prompt_lane.message:
        return BiblioLibraryRuntimeResult(
            status=context_result.status,
            reason_code=context_result.reason_code,
            query_kind=plan.query_kind,
            endpoint_observations=endpoint_observations,
            client_error=context_result.client_error,
            context_result=context_result,
            passage_result=passage_results[0] if len(passage_results) == 1 else None,
            passage_results=passage_results,
            prompt_lane=prompt_lane,
        )

    if context_result.status == CONTEXT_STATUS_CATALOGUE_UNAVAILABLE:
        return BiblioLibraryRuntimeResult(
            status=STATUS_ERROR,
            reason_code=REASON_CATALOGUE_UNAVAILABLE,
            query_kind=plan.query_kind,
            endpoint_observations=endpoint_observations,
            client_error=context_result.client_error,
            context_result=context_result,
        )

    consultation = _context_consultation_message(context_result)
    return BiblioLibraryRuntimeResult(
        status=context_result.status,
        reason_code=context_result.reason_code,
        query_kind=plan.query_kind,
        endpoint_observations=endpoint_observations,
        context_result=context_result,
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
    endpoint_observations = list(work_resolution.endpoint_observations)
    if work_resolution.client_error is not None:
        return BiblioLibraryRuntimeResult(
            status=STATUS_ERROR,
            reason_code=REASON_CATALOGUE_UNAVAILABLE,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
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
            endpoint_observations=tuple(endpoint_observations),
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
            endpoint_observations=tuple(endpoint_observations),
            work_resolution=work_resolution,
            passage_result=passage_result,
            passage_results=(passage_result,),
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
        endpoint_observations=tuple(endpoint_observations),
        work_resolution=work_resolution,
        passage_result=passage_result,
        passage_results=(passage_result,) if passage_result.status == STATUS_EXTRACTED else (),
        prompt_lane=prompt_lane,
        consultation_message=consultation,
    )


def _client_error(
    plan: BiblioQueryPlan,
    exc: CatalogueClientError,
    *,
    endpoint_observations: Sequence[CatalogueEndpointObservation] = (),
) -> BiblioLibraryRuntimeResult:
    return BiblioLibraryRuntimeResult(
        status=STATUS_ERROR,
        reason_code=REASON_CATALOGUE_UNAVAILABLE,
        query_kind=plan.query_kind,
        endpoint_observations=tuple(endpoint_observations),
        client_error=exc,
    )


def _catalog_consultation_message(
    *,
    status: str,
    reason_code: str,
    heading: str,
    items: Sequence[Mapping[str, Any]],
    total_count: int | None = None,
    displayed_count: int | None = None,
    truncated: bool = False,
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
        total_count=total_count,
        displayed_count=displayed_count,
        truncated=truncated,
    )


def _consultation_message(
    *,
    status: str,
    reason_code: str,
    lines: Sequence[str],
    doc_id_shorts: Sequence[str] = (),
    total_count: int | None = None,
    displayed_count: int | None = None,
    truncated: bool = False,
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
        total_count=total_count,
        displayed_count=displayed_count,
        truncated=truncated,
    )


def _catalogue_document_summary(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
    *,
    status: str,
    reason_code: str,
    not_found_reason: str,
    ambiguous_reason: str,
    heading: str,
) -> BiblioLibraryRuntimeResult:
    query = _catalogue_query(plan)
    endpoint_observations: list[CatalogueEndpointObservation] = []
    try:
        response = client.catalog(q=query or None, limit=plan.limit or 8, offset=0)
        endpoint_observations.append(observe_catalogue_response(response))
    except CatalogueClientError as exc:
        return _client_error(plan, exc)

    items = _catalog_items(response)
    if not items:
        consultation = _consultation_message(
            status=STATUS_NOT_FOUND,
            reason_code=not_found_reason,
            lines=["Aucun document Catalogue correspondant n'a ete trouve."],
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_NOT_FOUND,
            reason_code=not_found_reason,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )
    if len(items) > 1:
        consultation = _document_candidates_message(
            status=STATUS_AMBIGUOUS,
            reason_code=ambiguous_reason,
            heading="Plusieurs documents Catalogue correspondent:",
            items=items,
        )
        return BiblioLibraryRuntimeResult(
            status=STATUS_AMBIGUOUS,
            reason_code=ambiguous_reason,
            query_kind=plan.query_kind,
            endpoint_observations=tuple(endpoint_observations),
            consultation_message=consultation,
        )

    item = items[0]
    doc_id = _text(item.get("id") or item.get("document_id"))
    consultation = _consultation_message(
        status=status,
        reason_code=reason_code,
        lines=[heading, *_document_summary_lines(item)],
        doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        total_count=1,
        displayed_count=1,
        truncated=False,
    )
    return BiblioLibraryRuntimeResult(
        status=status,
        reason_code=reason_code,
        query_kind=plan.query_kind,
        endpoint_observations=tuple(endpoint_observations),
        consultation_message=consultation,
    )


def _document_candidates_message(
    *,
    status: str,
    reason_code: str,
    heading: str,
    items: Sequence[Mapping[str, Any]],
) -> BiblioConsultationMessage:
    lines = [heading]
    doc_ids: list[str] = []
    for index, item in enumerate(items[:MAX_COMPLETE_CATALOGUE_ITEMS], 1):
        doc_id = _text(item.get("id") or item.get("document_id"))
        doc_ids.append(short_doc_id(doc_id))
        lines.append(f"{index}. {'; '.join(_document_summary_lines(item))}")
    return _consultation_message(
        status=status,
        reason_code=reason_code,
        lines=lines,
        doc_id_shorts=tuple(doc_id for doc_id in doc_ids if doc_id),
        total_count=len(items),
        displayed_count=min(len(items), MAX_COMPLETE_CATALOGUE_ITEMS),
        truncated=len(items) > MAX_COMPLETE_CATALOGUE_ITEMS,
    )


def _context_consultation_message(context_result: BiblioPassageContextSearchResult) -> BiblioConsultationMessage:
    observed = context_result.to_observability()
    doc_ids = tuple(str(item or "") for item in observed.get("candidate_search", {}).get("doc_id_shorts", []) if item)
    lines = [
        "Recherche de passages effectuee.",
        f"Candidats: {int(observed.get('candidate_count') or 0)}",
        f"Contextes consultes: {int(observed.get('context_call_count') or 0)}",
        f"Passages retenus: {int(observed.get('passage_result_count') or 0)}",
        "Aucun passage n'a ete injecte.",
    ]
    return _consultation_message(
        status=context_result.status,
        reason_code=context_result.reason_code,
        lines=lines,
        doc_id_shorts=doc_ids,
    )


def _context_endpoint_observations(
    context_result: BiblioPassageContextSearchResult,
) -> tuple[CatalogueEndpointObservation, ...]:
    observations: list[CatalogueEndpointObservation] = []
    if context_result.candidate_result is not None:
        observations.extend(context_result.candidate_result.endpoint_observations)
    observations.extend(context_result.context_observations)
    return tuple(observations)


def _catalog_items(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    items = response.payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


def _catalog_total(response: CatalogueResponse, *, fallback: int) -> int:
    total = response.payload.get("total")
    return total if type(total) is int else fallback


def _list_limit(value: int) -> int:
    if type(value) is int and value > 0:
        return min(max(value, 1), MAX_COMPLETE_CATALOGUE_ITEMS)
    return DEFAULT_LIST_LIMIT


def _catalogue_query(plan: BiblioQueryPlan) -> str:
    return _text(plan.catalogue_query or plan.document_title or plan.work_title or plan.author)


def _document_summary_lines(item: Mapping[str, Any]) -> list[str]:
    doc_id = _text(item.get("id") or item.get("document_id"))
    fields = [f"catalogue_doc={short_doc_id(doc_id) or 'unknown'}"]
    title = _display_title(item)
    author = _display_author(item)
    if title:
        fields.append(f"titre={title}")
    if author:
        fields.append(f"auteur={author}")
    for label, key in (
        ("pages", "page_count"),
        ("paragraphes", "paragraph_count"),
        ("chapitres", "chapter_count"),
        ("milestones", "milestone_total"),
        ("stephanus", "stephanus_count"),
    ):
        value = _optional_int(item.get(key))
        if value is not None:
            fields.append(f"{label}={value}")
    toc_source = _text(item.get("toc_source"))
    if toc_source and toc_source != "none":
        fields.append("table_des_matieres=signalee")
    return fields


def _chapters(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    chapters = response.payload.get("chapters")
    if not isinstance(chapters, list):
        return []
    return [chapter for chapter in chapters if isinstance(chapter, Mapping)]


def _chapter_lines(chapters: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for chapter in chapters:
        number = _optional_int(chapter.get("chapter_no"))
        title = _neutralize(_text(chapter.get("title")))
        unit_no = _optional_int(chapter.get("unit_no"))
        source = _neutralize(_text(chapter.get("source")))
        parts = [f"chapitre={number}" if number is not None else "chapitre=unknown"]
        if title:
            parts.append(f"titre={title}")
        if unit_no is not None:
            parts.append(f"unit={unit_no}")
        if source and source != "none":
            parts.append(f"source={source}")
        lines.append("; ".join(parts))
    return lines


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


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None
