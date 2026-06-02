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
from .prompt_lane import (
    BiblioPromptLane,
    LANE_FOOTER,
    LANE_HEADER,
    TRUTH_CLARIFICATION_REQUIRED,
    TRUTH_CONTEXTUAL_APPROXIMATION,
    TRUTH_EXACT_PASSAGE,
    TRUTH_PLAUSIBLE_CANDIDATE,
    build_biblio_prompt_lane,
)
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
from .table_of_contents_runtime import (
    REASON_DOCUMENT_AMBIGUOUS,
    REASON_DOCUMENT_NOT_FOUND,
    REASON_DOCUMENT_OPENED,
    REASON_TOC_LISTED,
    REASON_TOC_NOT_FOUND,
    REASON_TOC_SUMMARY,
    STATUS_AMBIGUOUS,
    STATUS_NOT_FOUND,
    STATUS_OPENED,
    STATUS_TOC_LISTED,
    STATUS_TOC_SUMMARY,
    BiblioCatalogueConsultationResult,
    run_biblio_open_document,
    run_biblio_table_of_contents,
)
from .work_resolver import BiblioWorkResolution, BiblioWorkResolver


CONSULTATION_HEADER = "[CONSULTATION DE BIBLIOTHEQUE]"
CONSULTATION_FOOTER = "[/CONSULTATION DE BIBLIOTHEQUE]"

STATUS_LISTED = "listed"
STATUS_RESOLVED = "resolved"
STATUS_EXTRACTED_OR_LANE = "extracted"
STATUS_SKIPPED = "skipped"
STATUS_ERROR = "error"

REASON_CATALOG_LISTED = "biblio_catalog_listed"
REASON_DOCUMENTARY_RESOLUTION_READY = "biblio_documentary_resolution_ready"
REASON_PASSAGE_LANE_READY = "biblio_passage_lane_ready"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_LIST_LIMIT = 100
MAX_COMPLETE_CATALOGUE_ITEMS = 100
DEFAULT_RANGE_WINDOW_CHARS = MAX_CONTEXT_WINDOW_CHARS
DEFAULT_RANGE_MAX_PASSAGE_CHARS = 7_000


@dataclass(frozen=True)
class BiblioConsultationMessage:
    message: dict[str, Any] | None = field(default=None, repr=False, compare=False)
    status: str = STATUS_SKIPPED
    reason_code: str = ""
    product_truth: str = ""
    documentary_target: str = ""
    item_count: int = 0
    chars: int = 0
    doc_id_shorts: tuple[str, ...] = field(default_factory=tuple)
    total_count: int | None = None
    displayed_count: int | None = None
    truncated: bool = False
    passage_count: int = 0
    hashes: tuple[str, ...] = field(default_factory=tuple)

    def to_observability(self) -> dict[str, Any]:
        return {
            "present": self.message is not None,
            "status": self.status,
            "reason_code": self.reason_code,
            "product_truth": self.product_truth,
            "documentary_target": self.documentary_target,
            "item_count": self.item_count,
            "chars": self.chars,
            "doc_id_shorts": list(self.doc_id_shorts),
            "total_count": self.total_count,
            "displayed_count": self.displayed_count,
            "truncated": self.truncated,
            "passage_count": self.passage_count,
            "hashes": list(self.hashes),
        }


@dataclass(frozen=True, repr=False)
class BiblioLibraryRuntimeResult:
    status: str
    reason_code: str
    query_kind: str
    product_truth: str = ""
    documentary_target: str = ""
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
    document_ids: tuple[str, ...] = field(default_factory=tuple, repr=False, compare=False)

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
    if plan.intent == INTENT_RESOLVE_WORK:
        return _resolve_work(client, plan, work_resolver_factory=work_resolver_factory)
    if plan.intent in {INTENT_EXTRACT_PASSAGE, INTENT_EXTRACT_RANGE}:
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
        documentary_target=_documentary_target(plan, None),
    )
    return BiblioLibraryRuntimeResult(
        status=STATUS_SKIPPED,
        reason_code=plan.reason_code,
        query_kind=plan.query_kind,
        consultation_message=consultation,
        documentary_target=_documentary_target(plan, None),
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
        documentary_target=_documentary_target(plan, None),
    )


def _open_document(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    return _catalogue_consultation_result(plan, run_biblio_open_document(client, plan))


def _show_table_of_contents(client: CatalogueClient, plan: BiblioQueryPlan) -> BiblioLibraryRuntimeResult:
    return _catalogue_consultation_result(plan, run_biblio_table_of_contents(client, plan))


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
    product_truth = _context_product_truth(context_result)
    prompt_lane = lane_builder(passage_results, product_truth=product_truth)
    if prompt_lane.message:
        return BiblioLibraryRuntimeResult(
            status=context_result.status,
            reason_code=context_result.reason_code,
            query_kind=plan.query_kind,
            product_truth=product_truth,
            documentary_target=_documentary_target(plan, None),
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
            product_truth=product_truth,
            documentary_target=_documentary_target(plan, None),
            endpoint_observations=endpoint_observations,
            client_error=context_result.client_error,
            context_result=context_result,
        )

    consultation = _context_consultation_message(context_result, product_truth=product_truth)
    return BiblioLibraryRuntimeResult(
        status=context_result.status,
        reason_code=context_result.reason_code,
        query_kind=plan.query_kind,
        product_truth=product_truth,
        documentary_target=_documentary_target(plan, None),
        endpoint_observations=endpoint_observations,
        context_result=context_result,
        consultation_message=consultation,
    )


def _resolve_work(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
    *,
    work_resolver_factory: Any,
) -> BiblioLibraryRuntimeResult:
    work_resolution = work_resolver_factory(client).resolve(plan)
    endpoint_observations = tuple(work_resolution.endpoint_observations)
    documentary_target = _documentary_target(plan, work_resolution)
    if work_resolution.client_error is not None:
        return BiblioLibraryRuntimeResult(
            status=STATUS_ERROR,
            reason_code=REASON_CATALOGUE_UNAVAILABLE,
            query_kind=plan.query_kind,
            product_truth=TRUTH_CLARIFICATION_REQUIRED,
            documentary_target=documentary_target,
            endpoint_observations=endpoint_observations,
            client_error=work_resolution.client_error,
            work_resolution=work_resolution,
        )

    if work_resolution.resolve_request is not None:
        consultation = _consultation_message(
            status=STATUS_RESOLVED,
            reason_code=REASON_DOCUMENTARY_RESOLUTION_READY,
            product_truth="",
            documentary_target=documentary_target,
            lines=_work_resolution_lines(work_resolution, documentary_target=documentary_target),
            doc_id_shorts=_document_shorts_from_work_resolution(work_resolution),
        )
        document_ids = ()
        if work_resolution.resolve_request.document_id:
            document_ids = (work_resolution.resolve_request.document_id,)
        return BiblioLibraryRuntimeResult(
            status=STATUS_RESOLVED,
            reason_code=REASON_DOCUMENTARY_RESOLUTION_READY,
            query_kind=plan.query_kind,
            product_truth="",
            documentary_target=documentary_target,
            endpoint_observations=endpoint_observations,
            work_resolution=work_resolution,
            consultation_message=consultation,
            document_ids=document_ids,
        )

    consultation = _consultation_message(
        status=work_resolution.status,
        reason_code=work_resolution.reason_code,
        product_truth=TRUTH_CLARIFICATION_REQUIRED,
        documentary_target=documentary_target,
        lines=["Resolution documentaire insuffisante; une clarification est necessaire."],
        doc_id_shorts=work_resolution.document_candidate_ids,
    )
    return BiblioLibraryRuntimeResult(
        status=work_resolution.status,
        reason_code=work_resolution.reason_code,
        query_kind=plan.query_kind,
        product_truth=TRUTH_CLARIFICATION_REQUIRED,
        documentary_target=documentary_target,
        endpoint_observations=endpoint_observations,
        work_resolution=work_resolution,
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
            product_truth=TRUTH_CLARIFICATION_REQUIRED,
            documentary_target=_documentary_target(plan, work_resolution),
            endpoint_observations=tuple(endpoint_observations),
            client_error=work_resolution.client_error,
            work_resolution=work_resolution,
        )
    if work_resolution.resolve_request is None:
        consultation = _consultation_message(
            status=work_resolution.status,
            reason_code=work_resolution.reason_code,
            product_truth=TRUTH_CLARIFICATION_REQUIRED,
            documentary_target=_documentary_target(plan, work_resolution),
            lines=["Catalogue consulte; resolution documentaire insuffisante."],
            doc_id_shorts=work_resolution.document_candidate_ids,
        )
        return BiblioLibraryRuntimeResult(
            status=work_resolution.status,
            reason_code=work_resolution.reason_code,
            query_kind=plan.query_kind,
            product_truth=TRUTH_CLARIFICATION_REQUIRED,
            documentary_target=_documentary_target(plan, work_resolution),
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
    prompt_lane = lane_builder([passage_result], product_truth=TRUTH_EXACT_PASSAGE)
    if passage_result.status == STATUS_EXTRACTED and prompt_lane.message:
        return BiblioLibraryRuntimeResult(
            status=STATUS_EXTRACTED_OR_LANE,
            reason_code=REASON_PASSAGE_LANE_READY,
            query_kind=plan.query_kind,
            product_truth=TRUTH_EXACT_PASSAGE,
            documentary_target=_documentary_target(plan, work_resolution),
            endpoint_observations=tuple(endpoint_observations),
            work_resolution=work_resolution,
            passage_result=passage_result,
            passage_results=(passage_result,),
            prompt_lane=prompt_lane,
        )

    consultation = _consultation_message(
        status=passage_result.status,
        reason_code=passage_result.reason_code,
        product_truth=TRUTH_CLARIFICATION_REQUIRED,
        documentary_target=_documentary_target(plan, work_resolution),
        lines=["Catalogue consulte; aucun passage n'a ete injecte."],
        doc_id_shorts=work_resolution.document_candidate_ids,
    )
    return BiblioLibraryRuntimeResult(
        status=passage_result.status,
        reason_code=passage_result.reason_code,
        query_kind=plan.query_kind,
        product_truth=TRUTH_CLARIFICATION_REQUIRED,
        documentary_target=_documentary_target(plan, work_resolution),
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
        product_truth=TRUTH_CLARIFICATION_REQUIRED,
        documentary_target=_documentary_target(plan, None),
        endpoint_observations=tuple(endpoint_observations),
        client_error=exc,
    )


def _catalogue_consultation_result(
    plan: BiblioQueryPlan,
    result: BiblioCatalogueConsultationResult,
) -> BiblioLibraryRuntimeResult:
    consultation = _consultation_message(
        status=result.status,
        reason_code=result.reason_code,
        documentary_target=_documentary_target(plan, None),
        lines=result.lines,
        doc_id_shorts=result.doc_id_shorts,
        total_count=result.total_count,
        displayed_count=result.displayed_count,
        truncated=result.truncated,
    )
    return BiblioLibraryRuntimeResult(
        status=result.status,
        reason_code=result.reason_code,
        query_kind=plan.query_kind,
        documentary_target=_documentary_target(plan, None),
        endpoint_observations=result.endpoint_observations,
        client_error=result.client_error,
        consultation_message=consultation,
        document_ids=tuple(str(item or "").strip() for item in result.document_ids if str(item or "").strip()),
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
        documentary_target="document_catalogue",
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
    product_truth: str = "",
    documentary_target: str = "",
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
        *([f"Niveau de resolution: {_truth_label(product_truth)}"] if _truth_label(product_truth) else []),
        *([f"Cible documentaire: {_documentary_target_label(documentary_target)}"] if _documentary_target_label(documentary_target) else []),
        *_neutralized_lines(lines),
    ]
    content = "\n".join([CONSULTATION_HEADER, *body, CONSULTATION_FOOTER])
    return BiblioConsultationMessage(
        message={"role": "system", "content": content},
        status=status,
        reason_code=reason_code,
        product_truth=product_truth,
        documentary_target=documentary_target,
        item_count=len([line for line in lines if str(line).strip()]),
        chars=len(content),
        doc_id_shorts=tuple(doc_id_shorts),
        total_count=total_count,
        displayed_count=displayed_count,
        truncated=truncated,
    )


def _context_consultation_message(
    context_result: BiblioPassageContextSearchResult,
    *,
    product_truth: str,
) -> BiblioConsultationMessage:
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
        product_truth=product_truth,
        documentary_target="work_search" if observed.get("candidate_count") else "",
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


def _context_product_truth(context_result: BiblioPassageContextSearchResult) -> str:
    if context_result.status == STATUS_EXTRACTED and bool(context_result.passage):
        return TRUTH_CONTEXTUAL_APPROXIMATION
    if context_result.status == STATUS_AMBIGUOUS and bool(context_result.passage_results):
        return TRUTH_PLAUSIBLE_CANDIDATE
    if context_result.status in {STATUS_NOT_FOUND, STATUS_AMBIGUOUS, STATUS_ERROR}:
        return TRUTH_CLARIFICATION_REQUIRED
    return ""


def _documentary_target(plan: BiblioQueryPlan, work_resolution: BiblioWorkResolution | None) -> str:
    if work_resolution is not None and work_resolution.documentary_target:
        return work_resolution.documentary_target
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


def _documentary_target_label(value: str) -> str:
    return {
        "document_id": "document explicite",
        "work_in_document": "oeuvre interne dans document/corpus",
        "work": "oeuvre",
        "document_with_author": "document ou corpus avec auteur",
        "document_or_volume": "document ou volume",
        "author_or_corpus": "auteur ou corpus",
        "document_catalogue": "document catalogue",
        "work_search": "recherche de passage dans une oeuvre",
    }.get(str(value or "").strip(), "")


def _truth_label(value: str) -> str:
    return {
        TRUTH_EXACT_PASSAGE: "passage exact",
        TRUTH_PLAUSIBLE_CANDIDATE: "candidat plausible",
        TRUTH_CONTEXTUAL_APPROXIMATION: "approximation contextuelle",
        TRUTH_CLARIFICATION_REQUIRED: "clarification necessaire",
    }.get(str(value or "").strip(), "")


def _work_resolution_lines(
    work_resolution: BiblioWorkResolution,
    *,
    documentary_target: str,
) -> list[str]:
    lines = ["Resolution documentaire effectuee."]
    if documentary_target == "work_in_document":
        lines.append("Une oeuvre interne a ete reperee dans un document ou corpus Catalogue.")
    elif documentary_target == "work":
        lines.append("Une oeuvre a ete reperee dans le Catalogue.")
    elif documentary_target:
        lines.append("Une cible documentaire a ete reperee dans le Catalogue.")
    lines.append("Aucun passage exact n'a ete extrait a ce stade.")
    if work_resolution.anchor_doc_id_short:
        lines.append("Un ancrage documentaire borne est disponible pour la suite.")
    return lines


def _document_shorts_from_work_resolution(work_resolution: BiblioWorkResolution) -> tuple[str, ...]:
    ids: list[str] = []
    if work_resolution.resolve_request is not None and work_resolution.resolve_request.document_id:
        ids.append(short_doc_id(work_resolution.resolve_request.document_id))
    ids.extend(item for item in work_resolution.document_candidate_ids if item)
    return tuple(dict.fromkeys(ids))
