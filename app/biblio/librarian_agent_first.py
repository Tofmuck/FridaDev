"""Minimal agent-first execution bridge for Biblio.

This module intentionally supports only a single validated `catalog_search`
tool call.  It is a narrow bridge for work-lookup turns where the deterministic
planner did not consult Catalogue, not a general agent loop activation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping

from . import librarian_planner
from . import librarian_tools
from .library_runtime import BiblioConsultationMessage, CONSULTATION_FOOTER, CONSULTATION_HEADER


STATUS_AGENT_FIRST_EXECUTED = "agent_first_executed"
REASON_AGENT_FIRST_CATALOG_SEARCH_EXECUTED = "biblio_agent_first_catalog_search_executed"
REASON_AGENT_FIRST_NOT_ELIGIBLE = "biblio_agent_first_not_eligible"
EXECUTION_SCOPE_CATALOG_SEARCH_ONLY = "catalog_search_only"


@dataclass(frozen=True, repr=False)
class BiblioAgentFirstExecutionResult:
    status: str
    reason_code: str
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None = field(default=None, repr=False, compare=False)
    consultation_message: BiblioConsultationMessage | None = field(default=None, repr=False, compare=False)

    def client_observability(self) -> list[dict[str, Any]]:
        if self.loop_result is None:
            return []
        items: list[dict[str, Any]] = []
        for step in self.loop_result.steps:
            if step.tool_result is not None:
                items.append(dict(step.tool_result.to_observability()))
        return items


def run_agent_first_catalog_search(
    *,
    comparison: Any,
    client: Any,
) -> BiblioAgentFirstExecutionResult | None:
    plan = _candidate_plan(comparison)
    if plan is None or not _is_single_catalog_search_plan(plan):
        return None

    registry = librarian_tools.build_librarian_tool_registry(client)
    loop_result = librarian_planner.BiblioLibrarianPlanner(registry).run(
        librarian_planner.BiblioLibrarianLoopRequest(
            plan=plan,
            options=librarian_planner.BiblioLibrarianLoopOptions(
                max_steps=1,
                max_tool_calls=1,
                max_total_duration_ms=5_000,
                max_clarifications=0,
                max_context_chars=0,
            ),
        )
    )
    if loop_result.status != librarian_planner.STATUS_TOOL_EXECUTED:
        return BiblioAgentFirstExecutionResult(
            status=loop_result.status,
            reason_code=loop_result.reason_code,
            loop_result=loop_result,
        )

    consultation = _consultation_message(loop_result)
    return BiblioAgentFirstExecutionResult(
        status=STATUS_AGENT_FIRST_EXECUTED,
        reason_code=REASON_AGENT_FIRST_CATALOG_SEARCH_EXECUTED,
        loop_result=loop_result,
        consultation_message=consultation,
    )


def _candidate_plan(comparison: Any) -> librarian_planner.BiblioLibrarianPlan | None:
    agent_result = getattr(comparison, "agent_result", None)
    plan = getattr(agent_result, "candidate_plan", None)
    if isinstance(plan, librarian_planner.BiblioLibrarianPlan):
        return plan
    return None


def _is_single_catalog_search_plan(plan: librarian_planner.BiblioLibrarianPlan) -> bool:
    if len(plan.tool_calls) != 1:
        return False
    call = plan.tool_calls[0]
    return (
        call.tool_name == librarian_tools.TOOL_CATALOG_SEARCH
        and str(call.method or "").strip().upper() == "GET"
        and isinstance(call.params, Mapping)
    )


def _consultation_message(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> BiblioConsultationMessage:
    observed = loop_result.to_observability()
    first_step = observed.get("steps", [{}])[0] if observed.get("steps") else {}
    doc_ids = tuple(str(item or "") for item in observed.get("doc_id_shorts", []) if str(item or ""))
    displayed_count = _int(first_step.get("displayed_count"))
    total_count = _int(first_step.get("total_count")) or None
    truncated = bool(first_step.get("truncated"))
    lines = [
        CONSULTATION_HEADER,
        "Contrat d'interpretation:",
        "- Cette consultation provient de la bibliotheque persistante, a la demande.",
        "- Elle a ete declenchee par un plan agent valide, sous garde deterministe.",
        "- Elle est bornee a un seul outil GET catalog_search.",
        "- Ne confonds pas cette consultation avec les documents actifs, la memoire, le web, l'identite ou le resume.",
        f"Statut: {STATUS_AGENT_FIRST_EXECUTED}",
        f"Raison: {REASON_AGENT_FIRST_CATALOG_SEARCH_EXECUTED}",
        "Recherche Catalogue executee.",
        f"Outil: {librarian_tools.TOOL_CATALOG_SEARCH}",
        f"Resultats affiches: {displayed_count}",
        f"Total observe: {total_count or 0}",
        CONSULTATION_FOOTER,
    ]
    content = "\n".join(lines)
    return BiblioConsultationMessage(
        message={"role": "system", "content": content},
        status=STATUS_AGENT_FIRST_EXECUTED,
        reason_code=REASON_AGENT_FIRST_CATALOG_SEARCH_EXECUTED,
        item_count=displayed_count,
        chars=len(content),
        doc_id_shorts=doc_ids,
        total_count=total_count,
        displayed_count=displayed_count,
        truncated=truncated,
    )


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0
