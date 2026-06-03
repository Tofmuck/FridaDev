"""Bounded runtime executor for deterministic Biblio navigation dialogue plans."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .catalogue_client import CatalogueEndpointObservation
from .library_runtime import BiblioConsultationMessage, CONSULTATION_FOOTER, CONSULTATION_HEADER
from . import librarian_dialogue_planner as dialogue
from . import librarian_planner
from . import librarian_runtime_projection
from . import librarian_tools


STATUS_CLARIFICATION_REQUIRED = "clarification_required"
STATUS_NAVIGATION_EXECUTED = "navigation_executed"
DEFAULT_MAX_CONTEXT_CHARS = 14_000
DEFAULT_PAGE_SNIPPET_MAX_CHARS = 2_500
DEFAULT_CONTEXT_SNIPPET_MAX_CHARS = 2_700


@dataclass(frozen=True, repr=False)
class BiblioNavigationRuntimeResult:
    status: str
    reason_code: str
    query_kind: str
    endpoint_observations: tuple[CatalogueEndpointObservation, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    consultation_message: BiblioConsultationMessage | None = field(default=None, repr=False, compare=False)
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None = field(default=None, repr=False, compare=False)
    state_anchor: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    document_ids: tuple[str, ...] = field(default_factory=tuple, repr=False, compare=False)

    def client_observability(self) -> list[dict[str, Any]]:
        return librarian_runtime_projection.endpoint_client_observability(self.endpoint_observations)


def run_biblio_navigation_plan(
    client: Any,
    planning_result: dialogue.BiblioDialoguePlanningResult,
) -> BiblioNavigationRuntimeResult:
    query_kind = planning_result.intent.query_kind or "navigation"
    if planning_result.status != dialogue.STATUS_PLANNED or not planning_result.plan.tool_calls:
        consultation = _clarification_message(planning_result)
        return BiblioNavigationRuntimeResult(
            status=planning_result.status or STATUS_CLARIFICATION_REQUIRED,
            reason_code=planning_result.reason_code,
            query_kind=query_kind,
            consultation_message=consultation,
        )
    if client is None:
        consultation = _clarification_message(planning_result)
        return BiblioNavigationRuntimeResult(
            status=STATUS_CLARIFICATION_REQUIRED,
            reason_code=planning_result.reason_code,
            query_kind=query_kind,
            consultation_message=consultation,
        )

    registry = librarian_tools.build_librarian_tool_registry(client)
    loop_result = librarian_planner.BiblioLibrarianPlanner(registry).run(
        librarian_planner.BiblioLibrarianLoopRequest(
            plan=planning_result.plan,
            options=librarian_planner.BiblioLibrarianLoopOptions(
                max_steps=max(1, len(planning_result.plan.tool_calls) + 1),
                max_tool_calls=max(1, len(planning_result.plan.tool_calls)),
                max_total_duration_ms=8_000,
                max_clarifications=1,
                max_context_chars=DEFAULT_MAX_CONTEXT_CHARS,
            ),
        )
    )
    tool_results = librarian_runtime_projection.loop_tool_results(loop_result)
    consultation = _executed_message(planning_result, loop_result, tool_results)
    document_ids = librarian_runtime_projection.tool_results_document_ids(tool_results)
    return BiblioNavigationRuntimeResult(
        status=_runtime_status(loop_result.status),
        reason_code=planning_result.reason_code
        if loop_result.status == librarian_planner.STATUS_TOOL_EXECUTED
        else loop_result.reason_code,
        query_kind=query_kind,
        endpoint_observations=librarian_runtime_projection.tool_result_endpoint_observations(tool_results),
        consultation_message=consultation,
        loop_result=loop_result,
        state_anchor=librarian_runtime_projection.state_anchor_from_tool_results(
            tool_results,
            status=STATUS_NAVIGATION_EXECUTED,
        ),
        document_ids=document_ids,
    )


def _runtime_status(loop_status: str) -> str:
    if loop_status == librarian_planner.STATUS_TOOL_EXECUTED:
        return STATUS_NAVIGATION_EXECUTED
    if loop_status == librarian_planner.STATUS_NEEDS_CLARIFICATION:
        return STATUS_CLARIFICATION_REQUIRED
    return loop_status or STATUS_CLARIFICATION_REQUIRED


def _clarification_message(
    planning_result: dialogue.BiblioDialoguePlanningResult,
) -> BiblioConsultationMessage:
    lines = [
        "Navigation documentaire demandee.",
        f"Statut: {planning_result.status}",
        f"Raison: {planning_result.reason_code}",
    ]
    if planning_result.tool_required:
        lines.append(f"Primitive requise: {planning_result.tool_required}")
    lines.append("Consigne: clarifier ou reformuler sans inventer de lecture documentaire.")
    return _message(
        status=planning_result.status or STATUS_CLARIFICATION_REQUIRED,
        reason_code=planning_result.reason_code,
        lines=lines,
    )


def _executed_message(
    planning_result: dialogue.BiblioDialoguePlanningResult,
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
) -> BiblioConsultationMessage:
    lines = [
        "Navigation documentaire bornee executee.",
        f"Statut boucle: {loop_result.status}",
        f"Raison boucle: {loop_result.reason_code}",
    ]
    for result in tool_results:
        if result is None:
            continue
        lines.extend(_tool_lines(result))
    return _message(
        status=_runtime_status(loop_result.status),
        reason_code=planning_result.reason_code if loop_result.status == librarian_planner.STATUS_TOOL_EXECUTED else loop_result.reason_code,
        lines=lines,
        doc_id_shorts=librarian_runtime_projection.tool_results_doc_id_shorts(tool_results),
        item_count=len(tool_results),
    )


def _message(
    *,
    status: str,
    reason_code: str,
    lines: Sequence[str],
    doc_id_shorts: Sequence[str] = (),
    item_count: int | None = None,
) -> BiblioConsultationMessage:
    content = _bounded_content(
        [
            CONSULTATION_HEADER,
            "Contrat d'interpretation:",
            "- Cette consultation provient de la bibliotheque persistante, a la demande.",
            "- Elle reste bornee et GET-only.",
            "- Elle peut montrer une page ou un contexte, pas un export complet.",
            f"Statut: {status}",
            f"Raison: {reason_code}",
            *[_neutralize(str(line or "")) for line in lines if str(line or "").strip()],
            CONSULTATION_FOOTER,
        ]
    )
    return BiblioConsultationMessage(
        message={"role": "system", "content": content},
        status=status,
        reason_code=reason_code,
        item_count=item_count or len([line for line in lines if str(line or "").strip()]),
        chars=len(content),
        doc_id_shorts=tuple(doc_id_shorts),
    )


def _tool_lines(result: librarian_tools.BiblioLibrarianToolResult) -> list[str]:
    lines = [
        "",
        f"Outil: {result.tool_name}",
        f"Endpoint: {result.endpoint_kind}",
        f"Statut outil: {result.status}",
    ]
    if result.document_summary:
        doc = _text(result.document_summary.get("doc_id_short") or result.document_summary.get("document_id")) or "unknown"
        title = _text(result.document_summary.get("title"))
        line = f"Document: catalogue_doc={doc}"
        if title:
            line = f"{line}; titre={_neutralize(title)}"
        lines.append(line)
    if result.positions:
        position = result.positions[0]
        parts = []
        if position.get("page_no") is not None:
            parts.append(f"page={position['page_no']}")
        if position.get("para_no") is not None:
            parts.append(f"paragraphe={position['para_no']}")
        if position.get("paragraph_id") is not None:
            parts.append(f"paragraph_id={position['paragraph_id']}")
        if parts:
            lines.append("Position: " + "; ".join(parts))
    if result.chapter_hint:
        chapter_no = _int(result.chapter_hint.get("chapter_no"))
        chapter_title = _text(result.chapter_hint.get("title"))
        if chapter_no is not None or chapter_title:
            label = "Repere TOC:"
            if chapter_no is not None and chapter_title:
                lines.append(f"{label} chapitre {chapter_no} - {_neutralize(chapter_title)}")
            elif chapter_no is not None:
                lines.append(f"{label} chapitre {chapter_no}")
            else:
                lines.append(f"{label} {_neutralize(chapter_title)}")
        next_chapter_no = _int(result.chapter_hint.get("next_chapter_no"))
        next_chapter_title = _text(result.chapter_hint.get("next_chapter_title"))
        if next_chapter_no is not None or next_chapter_title:
            if next_chapter_no is not None and next_chapter_title:
                lines.append(f"Chapitre suivant: {next_chapter_no} - {_neutralize(next_chapter_title)}")
            elif next_chapter_no is not None:
                lines.append(f"Chapitre suivant: {next_chapter_no}")
            else:
                lines.append(f"Chapitre suivant: {_neutralize(next_chapter_title)}")
    if result.page_text:
        lines.append("Page consultee:")
        lines.append(_neutralize(_clip(result.page_text, DEFAULT_PAGE_SNIPPET_MAX_CHARS)))
    if result.context_text:
        lines.append("Contexte consulte autour du passage:")
        lines.append(_neutralize(_clip(result.context_text, DEFAULT_CONTEXT_SNIPPET_MAX_CHARS)))
    return lines


def _bounded_content(lines: Sequence[str]) -> str:
    content = "\n".join(lines)
    if len(content) <= DEFAULT_MAX_CONTEXT_CHARS:
        return content
    suffix = "\n[contenu borne: suite masquee]\n" + CONSULTATION_FOOTER
    return content[: max(0, DEFAULT_MAX_CONTEXT_CHARS - len(suffix))].rstrip() + suffix


def _clip(value: str, max_chars: int) -> str:
    if len(value) <= max_chars:
        return value
    return value[:max_chars].rstrip() + " [...]"


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""


def _int(value: Any) -> int | None:
    if type(value) is int:
        return value
    return None


def _neutralize(value: str) -> str:
    return (
        value.replace(CONSULTATION_HEADER, "[CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace(CONSULTATION_FOOTER, "[/CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
        .replace("[/PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
    )
