"""Document opening and table-of-contents consultation for Biblio.

This module keeps catalogue/document overview handling separate from the
passage search runtime.  It may prepare product prompt lines with catalogue
titles or chapter titles, but it only returns compact endpoint observations for
operator/admin surfaces.
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
from .prompt_lane import LANE_FOOTER, LANE_HEADER
from .query_planner import BiblioQueryPlan


STATUS_OPENED = "opened"
STATUS_TOC_LISTED = "toc_listed"
STATUS_TOC_SUMMARY = "toc_summary"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_ERROR = "error"

REASON_DOCUMENT_OPENED = "biblio_document_opened"
REASON_DOCUMENT_NOT_FOUND = "biblio_document_not_found"
REASON_DOCUMENT_AMBIGUOUS = "biblio_document_ambiguous"
REASON_TOC_LISTED = "biblio_table_of_contents_listed"
REASON_TOC_SUMMARY = "biblio_table_of_contents_summary"
REASON_TOC_NOT_FOUND = "biblio_table_of_contents_not_found"
REASON_CATALOGUE_UNAVAILABLE = "catalogue_unavailable"

DEFAULT_DOCUMENT_LOOKUP_LIMIT = 8
DEFAULT_TOC_LIMIT = 500
MAX_COMPLETE_CATALOGUE_ITEMS = 100


@dataclass(frozen=True, repr=False)
class BiblioCatalogueConsultationResult:
    status: str
    reason_code: str
    endpoint_observations: tuple[CatalogueEndpointObservation, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    client_error: CatalogueClientError | None = field(default=None, repr=False, compare=False)
    lines: tuple[str, ...] = field(default_factory=tuple, repr=False, compare=False)
    document_ids: tuple[str, ...] = field(default_factory=tuple, repr=False, compare=False)
    doc_id_shorts: tuple[str, ...] = field(default_factory=tuple)
    total_count: int | None = None
    displayed_count: int | None = None
    truncated: bool = False


def run_biblio_open_document(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
) -> BiblioCatalogueConsultationResult:
    try:
        response = client.catalog(q=_catalogue_query(plan) or None, limit=plan.limit or DEFAULT_DOCUMENT_LOOKUP_LIMIT, offset=0)
    except CatalogueClientError as exc:
        return _client_error(exc)

    observations = (observe_catalogue_response(response),)
    items = _catalog_items(response)
    if not items:
        return BiblioCatalogueConsultationResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_DOCUMENT_NOT_FOUND,
            endpoint_observations=observations,
            lines=("Aucun document Catalogue correspondant n'a ete trouve.",),
        )
    if len(items) > 1:
        return _document_candidates_result(
            status=STATUS_AMBIGUOUS,
            reason_code=REASON_DOCUMENT_AMBIGUOUS,
            heading="Plusieurs documents Catalogue correspondent:",
            items=items,
            endpoint_observations=observations,
        )

    item = items[0]
    doc_id = _text(item.get("id") or item.get("document_id"))
    return BiblioCatalogueConsultationResult(
        status=STATUS_OPENED,
        reason_code=REASON_DOCUMENT_OPENED,
        endpoint_observations=observations,
        lines=("Document Catalogue trouve:", *_document_summary_lines(item)),
        document_ids=tuple(filter(None, [doc_id])),
        doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        total_count=1,
        displayed_count=1,
        truncated=False,
    )


def run_biblio_table_of_contents(
    client: CatalogueClient,
    plan: BiblioQueryPlan,
) -> BiblioCatalogueConsultationResult:
    if plan.document_id:
        return _table_of_contents_for_document_id(client, plan.document_id)

    endpoint_observations: list[CatalogueEndpointObservation] = []
    try:
        response = client.catalog(q=_catalogue_query(plan) or None, limit=plan.limit or DEFAULT_DOCUMENT_LOOKUP_LIMIT, offset=0)
        endpoint_observations.append(observe_catalogue_response(response))
    except CatalogueClientError as exc:
        return _client_error(exc)

    items = _catalog_items(response)
    if not items:
        return BiblioCatalogueConsultationResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            endpoint_observations=tuple(endpoint_observations),
            lines=("Aucun document Catalogue correspondant n'a ete trouve pour la table des matieres.",),
        )
    if len(items) > 1:
        return _document_candidates_result(
            status=STATUS_AMBIGUOUS,
            reason_code=REASON_DOCUMENT_AMBIGUOUS,
            heading="Plusieurs documents Catalogue correspondent a la demande de table des matieres:",
            items=items,
            endpoint_observations=tuple(endpoint_observations),
        )

    selected = items[0]
    doc_id = _text(selected.get("id") or selected.get("document_id"))
    chapter_count = _optional_int(selected.get("chapter_count")) or 0
    if not doc_id or chapter_count <= 0:
        return BiblioCatalogueConsultationResult(
            status=STATUS_NOT_FOUND,
            reason_code=REASON_TOC_NOT_FOUND,
            endpoint_observations=tuple(endpoint_observations),
            lines=(
                "Document trouve, mais aucune table des matieres structuree n'est signalee par Catalogue.",
                *_document_summary_lines(selected),
            ),
            document_ids=tuple(filter(None, [doc_id])),
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=chapter_count,
            displayed_count=0,
            truncated=False,
        )

    try:
        chapters_response = client.chapters(doc_id, limit=DEFAULT_TOC_LIMIT, offset=0)
        endpoint_observations.append(observe_catalogue_response(chapters_response))
    except CatalogueClientError as exc:
        return BiblioCatalogueConsultationResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            endpoint_observations=tuple(endpoint_observations),
            client_error=exc,
            lines=(
                "Table des matieres signalee par Catalogue, mais le detail n'a pas pu etre lu via la route chapitres.",
                f"Chapitres signales: {chapter_count}.",
                *_document_summary_lines(selected),
            ),
            document_ids=tuple(filter(None, [doc_id])),
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=chapter_count,
            displayed_count=0,
            truncated=True,
        )

    chapters = _chapters(chapters_response)
    total = _optional_int(chapters_response.payload.get("total")) or len(chapters)
    truncated = bool(chapters_response.payload.get("truncated")) or total > len(chapters)
    if not chapters:
        return BiblioCatalogueConsultationResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            endpoint_observations=tuple(endpoint_observations),
            lines=(
                "Route chapitres consultee, mais aucune entree exploitable n'a ete retournee.",
                f"Chapitres signales: {chapter_count}.",
                *_document_summary_lines(selected),
            ),
            document_ids=tuple(filter(None, [doc_id])),
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=total or chapter_count,
            displayed_count=0,
            truncated=truncated,
        )

    lines = [
        (
            f"Table des matieres disponible: {total} entrees. Liste complete affichee."
            if not truncated
            else f"Table des matieres disponible: {total} entrees. Affichage des {len(chapters)} premieres."
        ),
        *_document_summary_lines(selected),
        *_chapter_lines(chapters),
    ]
    return BiblioCatalogueConsultationResult(
        status=STATUS_TOC_LISTED,
        reason_code=REASON_TOC_LISTED,
        endpoint_observations=tuple(endpoint_observations),
        lines=tuple(lines),
        document_ids=tuple(filter(None, [doc_id])),
        doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        total_count=total,
        displayed_count=len(chapters),
        truncated=truncated,
    )


def _table_of_contents_for_document_id(
    client: CatalogueClient,
    doc_id: str,
) -> BiblioCatalogueConsultationResult:
    endpoint_observations: list[CatalogueEndpointObservation] = []
    try:
        chapters_response = client.chapters(doc_id, limit=DEFAULT_TOC_LIMIT, offset=0)
        endpoint_observations.append(observe_catalogue_response(chapters_response))
    except CatalogueClientError as exc:
        return BiblioCatalogueConsultationResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            endpoint_observations=tuple(endpoint_observations),
            client_error=exc,
            lines=("Document courant resolu, mais la route chapitres n'a pas pu etre lue.",),
            document_ids=tuple(filter(None, [doc_id])),
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=0,
            displayed_count=0,
            truncated=True,
        )

    chapters = _chapters(chapters_response)
    total = _optional_int(chapters_response.payload.get("total")) or len(chapters)
    truncated = bool(chapters_response.payload.get("truncated")) or total > len(chapters)
    if not chapters:
        return BiblioCatalogueConsultationResult(
            status=STATUS_TOC_SUMMARY,
            reason_code=REASON_TOC_SUMMARY,
            endpoint_observations=tuple(endpoint_observations),
            lines=("Document courant resolu, mais aucune entree de table des matieres n'a ete retournee.",),
            document_ids=tuple(filter(None, [doc_id])),
            doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
            total_count=total,
            displayed_count=0,
            truncated=truncated,
        )

    lines = [
        (
            f"Table des matieres disponible: {total} entrees. Liste complete affichee."
            if not truncated
            else f"Table des matieres disponible: {total} entrees. Affichage des {len(chapters)} premieres."
        ),
        f"catalogue_doc={short_doc_id(doc_id) or 'unknown'}",
        *_chapter_lines(chapters),
    ]
    return BiblioCatalogueConsultationResult(
        status=STATUS_TOC_LISTED,
        reason_code=REASON_TOC_LISTED,
        endpoint_observations=tuple(endpoint_observations),
        lines=tuple(lines),
        document_ids=tuple(filter(None, [doc_id])),
        doc_id_shorts=tuple(filter(None, [short_doc_id(doc_id)])),
        total_count=total,
        displayed_count=len(chapters),
        truncated=truncated,
    )


def _client_error(exc: CatalogueClientError) -> BiblioCatalogueConsultationResult:
    return BiblioCatalogueConsultationResult(
        status=STATUS_ERROR,
        reason_code=REASON_CATALOGUE_UNAVAILABLE,
        client_error=exc,
    )


def _document_candidates_result(
    *,
    status: str,
    reason_code: str,
    heading: str,
    items: Sequence[Mapping[str, Any]],
    endpoint_observations: tuple[CatalogueEndpointObservation, ...],
) -> BiblioCatalogueConsultationResult:
    displayed = items[:MAX_COMPLETE_CATALOGUE_ITEMS]
    doc_ids: list[str] = []
    lines = [heading]
    for index, item in enumerate(displayed, 1):
        doc_id = _text(item.get("id") or item.get("document_id"))
        doc_ids.append(short_doc_id(doc_id))
        lines.append(f"{index}. {'; '.join(_document_summary_lines(item))}")
    return BiblioCatalogueConsultationResult(
        status=status,
        reason_code=reason_code,
        endpoint_observations=endpoint_observations,
        lines=tuple(lines),
        doc_id_shorts=tuple(doc_id for doc_id in doc_ids if doc_id),
        total_count=len(items),
        displayed_count=len(displayed),
        truncated=len(items) > len(displayed),
    )


def _catalogue_query(plan: BiblioQueryPlan) -> str:
    return _text(plan.catalogue_query or plan.document_title or plan.work_title or plan.author)


def _catalog_items(response: CatalogueResponse) -> list[Mapping[str, Any]]:
    items = response.payload.get("items")
    if not isinstance(items, list):
        return []
    return [item for item in items if isinstance(item, Mapping)]


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


def _neutralize(value: str) -> str:
    text = str(value or "")
    replacements = {
        LANE_HEADER: "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]",
        LANE_FOOTER: "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]",
        "[CONSULTATION DE BIBLIOTHEQUE]": "[CONSULTATION DE BIBLIOTHEQUE neutralise]",
        "[/CONSULTATION DE BIBLIOTHEQUE]": "[/CONSULTATION DE BIBLIOTHEQUE neutralise]",
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
