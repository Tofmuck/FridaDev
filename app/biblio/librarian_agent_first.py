"""Agent-first execution bridge for Biblio.

The librarian agent is allowed to control Biblio requests only inside the hard
walls already enforced by the validated plan, the tool registry and the bounded
planner loop.  Product data is projected into the prompt lane; observability is
kept content-free through the existing ``to_observability()`` projections.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

from . import librarian_method_runtime
from . import librarian_planner
from . import librarian_runtime_projection
from . import librarian_tools
from .library_runtime import BiblioConsultationMessage, CONSULTATION_FOOTER, CONSULTATION_HEADER
from .librarian_agent_contract import MODE_ACTIVE, normalize_mode


STATUS_AGENT_FIRST_EXECUTED = "agent_first_executed"
STATUS_AGENT_FIRST_NEEDS_CLARIFICATION = "agent_first_needs_clarification"
REASON_AGENT_FIRST_EXECUTED = "biblio_agent_first_plan_executed"
REASON_AGENT_FIRST_NEEDS_CLARIFICATION = "biblio_agent_first_needs_clarification"
REASON_AGENT_FIRST_NOT_ELIGIBLE = "biblio_agent_first_not_eligible"
EXECUTION_SCOPE_AGENT_FIRST = "agent_first"

DEFAULT_MAX_STEPS = 5
DEFAULT_MAX_TOOL_CALLS = 5
DEFAULT_MAX_TOTAL_DURATION_MS = 8_000
DEFAULT_MAX_CONTEXT_CHARS = 6_000
DEFAULT_LANE_MAX_CHARS = 14_000
DEFAULT_MAX_ITEMS_PER_TOOL = 100
DEFAULT_SNIPPET_MAX_CHARS = 900


@dataclass(frozen=True, repr=False)
class BiblioAgentFirstExecutionResult:
    status: str
    reason_code: str
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None = field(default=None, repr=False, compare=False)
    consultation_message: BiblioConsultationMessage | None = field(default=None, repr=False, compare=False)
    state_anchor: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    executed: bool = False

    def client_observability(self) -> list[dict[str, Any]]:
        return librarian_runtime_projection.loop_client_observability(self.loop_result)


def run_agent_first_plan(
    *,
    comparison: Any,
    client: Any,
    deterministic_plan: Any = None,
) -> BiblioAgentFirstExecutionResult | None:
    plan = _candidate_plan(comparison)
    if plan is None or not _is_active_comparison(comparison):
        return None

    registry = librarian_tools.build_librarian_tool_registry(client)
    loop_result = librarian_planner.BiblioLibrarianPlanner(registry).run(
        librarian_planner.BiblioLibrarianLoopRequest(
            plan=plan,
            options=librarian_planner.BiblioLibrarianLoopOptions(
                max_steps=_positive_int(getattr(getattr(comparison, "settings", None), "max_tool_calls", 0))
                or DEFAULT_MAX_STEPS,
                max_tool_calls=_positive_int(getattr(getattr(comparison, "settings", None), "max_tool_calls", 0))
                or DEFAULT_MAX_TOOL_CALLS,
                max_total_duration_ms=DEFAULT_MAX_TOTAL_DURATION_MS,
                max_clarifications=1,
                max_context_chars=DEFAULT_MAX_CONTEXT_CHARS,
            ),
        )
    )
    loop_result = librarian_method_runtime.complete_product_method_loop(
        loop_result,
        plan=plan,
        registry=registry,
        deterministic_plan=deterministic_plan,
    )
    if loop_result.status == librarian_planner.STATUS_NEEDS_CLARIFICATION:
        consultation = _consultation_message(
            loop_result,
            status=STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
            reason_code=REASON_AGENT_FIRST_NEEDS_CLARIFICATION,
        )
        return BiblioAgentFirstExecutionResult(
            status=STATUS_AGENT_FIRST_NEEDS_CLARIFICATION,
            reason_code=REASON_AGENT_FIRST_NEEDS_CLARIFICATION,
            loop_result=loop_result,
            consultation_message=consultation,
            executed=False,
        )
    if loop_result.status != librarian_planner.STATUS_TOOL_EXECUTED:
        return BiblioAgentFirstExecutionResult(
            status=loop_result.status,
            reason_code=loop_result.reason_code,
            loop_result=loop_result,
            executed=False,
        )

    tool_results = librarian_runtime_projection.loop_tool_results(loop_result)
    consultation = _consultation_message(
        loop_result,
        status=STATUS_AGENT_FIRST_EXECUTED,
        reason_code=REASON_AGENT_FIRST_EXECUTED,
    )
    return BiblioAgentFirstExecutionResult(
        status=STATUS_AGENT_FIRST_EXECUTED,
        reason_code=REASON_AGENT_FIRST_EXECUTED,
        loop_result=loop_result,
        consultation_message=consultation,
        state_anchor=librarian_runtime_projection.state_anchor_from_tool_results(
            tool_results,
            status=STATUS_AGENT_FIRST_EXECUTED,
            reason_code=REASON_AGENT_FIRST_EXECUTED,
        ),
        executed=True,
    )


def _candidate_plan(comparison: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    agent_result = getattr(comparison, "agent_result", None)
    plan = getattr(agent_result, "candidate_plan", None)
    if isinstance(plan, librarian_planner.BiblioLibrarianPlan):
        return plan
    return None


def _is_active_comparison(comparison: Any) -> bool:
    settings = getattr(comparison, "settings", None)
    if normalize_mode(getattr(settings, "mode", "")) != MODE_ACTIVE:
        return False
    agent_result = getattr(comparison, "agent_result", None)
    return bool(agent_result and getattr(agent_result, "candidate_plan", None) is not None)


def _consultation_message(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    status: str,
    reason_code: str,
) -> BiblioConsultationMessage:
    observed = loop_result.to_observability()
    tool_results = librarian_runtime_projection.loop_tool_results(loop_result)
    doc_ids = librarian_runtime_projection.tool_results_doc_id_shorts(tool_results)
    displayed_count = sum(_displayed_count(result) for result in tool_results)
    total_count = _first_total_count(tool_results)
    truncated = any(bool(result.to_observability().get("truncated")) for result in tool_results)
    passage_count, hashes = _passage_summary(tool_results)
    body = [
        CONSULTATION_HEADER,
        "Contrat d'interpretation:",
        "- Cette consultation provient de la bibliotheque persistante, a la demande.",
        "- Elle a ete declenchee par un plan bibliothecaire valide, sous garde deterministe.",
        "- Les outils Catalogue appeles sont GET-only et bornes.",
        "- Ne confonds pas cette consultation avec les documents actifs, la memoire, le web, l'identite ou le resume.",
        f"Statut: {status}",
        f"Raison: {reason_code}",
        f"Outils executes: {loop_result.tool_call_count}",
        f"Resultats affiches: {displayed_count}",
        f"Total observe: {total_count or 0}",
    ]
    body.extend(_tool_result_lines(tool_results))
    if not tool_results and loop_result.status == librarian_planner.STATUS_NEEDS_CLARIFICATION:
        body.append("Clarification bibliothecaire requise avant consultation.")
    content = _bounded_content([CONSULTATION_HEADER, *body[1:], CONSULTATION_FOOTER])
    return BiblioConsultationMessage(
        message={"role": "system", "content": content},
        status=status,
        reason_code=reason_code,
        item_count=displayed_count,
        chars=len(content),
        doc_id_shorts=tuple(doc_ids),
        total_count=total_count,
        displayed_count=displayed_count,
        truncated=truncated,
        passage_count=passage_count,
        hashes=hashes,
    )


def _tool_result_lines(tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> list[str]:
    lines: list[str] = []
    for index, result in enumerate(tool_results, 1):
        lines.append("")
        lines.append(f"Outil {index}: {result.tool_name}")
        lines.append(f"Endpoint: {result.endpoint_kind}")
        lines.append(f"Statut outil: {result.status}")
        if result.items:
            lines.extend(_item_lines(result.tool_name, result.items))
        if result.document_summary:
            lines.extend(_document_summary_lines(result.document_summary))
        if result.chapters:
            lines.extend(_chapter_lines(result.chapters))
        if result.positions:
            lines.extend(_position_lines(result.positions))
        if result.page_text:
            lines.extend(_page_lines(result.page_text))
        if result.context_text:
            lines.extend(_passage_lines(result.context_text))
    return lines


def _item_lines(tool_name: str, items: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["Resultats:"]
    for index, item in enumerate(items[:DEFAULT_MAX_ITEMS_PER_TOOL], 1):
        doc = _text(item.get("doc_id_short") or item.get("document_id")) or "unknown"
        title = _text(item.get("title"))
        authors = _text(item.get("authors"))
        page = _text(item.get("page_no"))
        para = _text(item.get("para_no"))
        paragraph_id = _text(item.get("paragraph_id"))
        rank = _text(item.get("rank") or item.get("score"))
        parts = [f"{index}. catalogue_doc={doc}"]
        if title:
            parts.append(f"titre={_neutralize(title)}")
        if authors:
            parts.append(f"auteur={_neutralize(authors)}")
        if page:
            parts.append(f"page={page}")
        if para:
            parts.append(f"paragraphe={para}")
        if paragraph_id:
            parts.append(f"paragraph_id={paragraph_id}")
        if rank:
            parts.append(f"score={rank}")
        lines.append("; ".join(parts))
        snippet = _text(item.get("snippet"))
        if snippet and tool_name == librarian_tools.TOOL_CATALOG_SEARCH:
            lines.append(f"   extrait: {_neutralize(_clip(snippet, DEFAULT_SNIPPET_MAX_CHARS))}")
    if len(items) > DEFAULT_MAX_ITEMS_PER_TOOL:
        lines.append(f"... {len(items) - DEFAULT_MAX_ITEMS_PER_TOOL} resultats supplementaires masques par borne.")
    return lines


def _document_summary_lines(summary: Mapping[str, Any]) -> list[str]:
    doc = _text(summary.get("doc_id_short") or summary.get("document_id")) or "unknown"
    lines = [f"Document: catalogue_doc={doc}"]
    title = _text(summary.get("title"))
    authors = _text(summary.get("authors"))
    status = _text(summary.get("metadata_status"))
    if title:
        lines.append(f"Titre: {_neutralize(title)}")
    if authors:
        lines.append(f"Auteur: {_neutralize(authors)}")
    if status:
        lines.append(f"Metadata: {_neutralize(status)}")
    return lines


def _chapter_lines(chapters: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["Table des matieres:"]
    for index, chapter in enumerate(chapters[:DEFAULT_MAX_ITEMS_PER_TOOL], 1):
        number = _text(chapter.get("chapter_no")) or str(index)
        title = _text(chapter.get("title")) or "sans titre"
        page_start = _text(chapter.get("page_start"))
        detail = f"{index}. chapitre={number}; titre={_neutralize(title)}"
        if page_start:
            detail = f"{detail}; page_start={page_start}"
        lines.append(detail)
    if len(chapters) > DEFAULT_MAX_ITEMS_PER_TOOL:
        lines.append(f"... {len(chapters) - DEFAULT_MAX_ITEMS_PER_TOOL} chapitres supplementaires masques par borne.")
    return lines


def _position_lines(positions: Sequence[Mapping[str, Any]]) -> list[str]:
    lines = ["Positions:"]
    for index, position in enumerate(positions[:DEFAULT_MAX_ITEMS_PER_TOOL], 1):
        parts = [f"{index}."]
        for key in ("page_no", "para_no", "paragraph_id", "char_offset", "window_chars", "rank", "score"):
            value = _text(position.get(key))
            if value:
                parts.append(f"{key}={value}")
        lines.append(" ".join(parts))
    return lines


def _passage_lines(text: str) -> list[str]:
    clipped = _neutralize(_clip(text, DEFAULT_SNIPPET_MAX_CHARS * 3))
    return ["Passage consulte:", clipped]


def _page_lines(text: str) -> list[str]:
    clipped = _neutralize(_clip(text, DEFAULT_SNIPPET_MAX_CHARS * 3))
    return ["Page consultee:", clipped]


def _displayed_count(result: librarian_tools.BiblioLibrarianToolResult) -> int:
    observed = result.to_observability()
    return _int(observed.get("displayed_count")) or len(result.items or result.chapters or result.positions)


def _first_total_count(tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> int | None:
    for result in tool_results:
        total = _int(result.to_observability().get("total_count"))
        if total:
            return total
    return None


def _passage_summary(tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> tuple[int, tuple[str, ...]]:
    hashes: list[str] = []
    count = 0
    for result in tool_results:
        if not result.context_text:
            continue
        count += 1
        hashes.append(hashlib.sha256(result.context_text.encode("utf-8")).hexdigest()[:12])
    return count, tuple(hashes)


def _bounded_content(lines: Sequence[str]) -> str:
    content = "\n".join(lines)
    if len(content) <= DEFAULT_LANE_MAX_CHARS:
        return content
    suffix = "\n[contenu borne: suite masquee]\n" + CONSULTATION_FOOTER
    return content[: max(0, DEFAULT_LANE_MAX_CHARS - len(suffix))].rstrip() + suffix


def _neutralize(value: str) -> str:
    return (
        value.replace(CONSULTATION_HEADER, "[CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace(CONSULTATION_FOOTER, "[/CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
        .replace("[/PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
    )


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


def _positive_int(value: Any) -> int:
    if type(value) is int and value > 0:
        return value
    return 0


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0
