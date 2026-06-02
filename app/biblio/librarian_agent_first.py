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

from . import librarian_planner
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
_THEME_QUERY_STOPWORDS = frozenset(
    {
        "a",
        "au",
        "aux",
        "ce",
        "ces",
        "cet",
        "cette",
        "dans",
        "de",
        "des",
        "du",
        "en",
        "et",
        "la",
        "le",
        "les",
        "l",
        "ou",
        "où",
        "par",
        "pour",
        "sa",
        "se",
        "ses",
        "son",
        "sur",
        "un",
        "une",
    }
)


@dataclass(frozen=True, repr=False)
class BiblioAgentFirstExecutionResult:
    status: str
    reason_code: str
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None = field(default=None, repr=False, compare=False)
    consultation_message: BiblioConsultationMessage | None = field(default=None, repr=False, compare=False)
    state_anchor: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    executed: bool = False

    def client_observability(self) -> list[dict[str, Any]]:
        if self.loop_result is None:
            return []
        items: list[dict[str, Any]] = []
        for step in self.loop_result.steps:
            if step.tool_result is not None:
                items.append(dict(step.tool_result.to_observability()))
        return items


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
    loop_result = _complete_agent_loop_if_needed(
        loop_result,
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
        state_anchor=_state_anchor([step.tool_result for step in loop_result.steps if step.tool_result is not None]),
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


def _complete_agent_loop_if_needed(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    deterministic_plan: Any,
) -> librarian_planner.BiblioLibrarianLoopResult:
    if loop_result.status not in {
        librarian_planner.STATUS_TOOL_EXECUTED,
        librarian_planner.STATUS_TOOL_FAILED,
        librarian_planner.STATUS_TOOL_REJECTED,
    }:
        return loop_result
    intent = str(getattr(deterministic_plan, "intent", "") or "")
    if intent == "show_table_of_contents" and not _has_endpoint(loop_result, "chapters"):
        doc_id = _first_document_id(loop_result)
        if doc_id:
            return _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_DOCUMENT_TOC,
                params={"document_id": doc_id, "limit": 500},
            )
    if intent in {"search_catalog", "extract_passage", "extract_range", "document_locator"} and not _has_endpoint(
        loop_result,
        "context",
    ):
        for _ in range(3):
            if _first_context_params(loop_result):
                break
            fallback_query = _fallback_search_query(deterministic_plan, loop_result)
            if not fallback_query:
                break
            loop_result = _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_CATALOG_SEARCH,
                params={
                    "query": fallback_query,
                    "limit": _positive_int(getattr(deterministic_plan, "limit", 0)) or 8,
                },
            )
        context_params = _first_context_params(loop_result)
        if context_params:
            return _append_tool_call(
                loop_result,
                registry=registry,
                tool_name=librarian_tools.TOOL_PASSAGE_CONTEXT,
                params=context_params,
            )
    return loop_result


def _append_tool_call(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    tool_name: str,
    params: Mapping[str, Any],
) -> librarian_planner.BiblioLibrarianLoopResult:
    if loop_result.tool_call_count >= loop_result.options.max_tool_calls:
        return loop_result
    call = librarian_planner.BiblioLibrarianToolCall(tool_name=tool_name, method="GET", params=dict(params))
    planner = librarian_planner.BiblioLibrarianPlanner(registry)
    step = planner.run_tool_call(len(loop_result.steps), call)  # Bounded single GET continuation.
    steps = (*loop_result.steps, step)
    status = librarian_planner.STATUS_TOOL_EXECUTED
    reason = librarian_planner.REASON_TOOL_EXECUTED
    if step.status != librarian_planner.STATUS_TOOL_EXECUTED:
        status = step.status
        reason = step.reason_code
    return librarian_planner.BiblioLibrarianLoopResult(
        status=status,
        reason_code=reason,
        steps=steps,
        options=loop_result.options,
        duration_ms=loop_result.duration_ms,
        fallback_deterministic=loop_result.fallback_deterministic,
    )


def _has_endpoint(loop_result: librarian_planner.BiblioLibrarianLoopResult, endpoint_kind: str) -> bool:
    return any(
        step.endpoint_kind == endpoint_kind and step.status == librarian_planner.STATUS_TOOL_EXECUTED
        for step in loop_result.steps
    )


def _first_document_id(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> str:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None:
            continue
        direct = _text(getattr(result, "document_id", ""))
        if direct:
            return direct
        for item in result.items:
            doc_id = _text(item.get("document_id"))
            if doc_id:
                return doc_id
        if result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
            if doc_id:
                return doc_id
    return ""


def _first_context_params(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> dict[str, Any]:
    for step in loop_result.steps:
        result = step.tool_result
        if result is None:
            continue
        for item in result.items:
            if not isinstance(item, Mapping):
                continue
            doc_id = _text(item.get("document_id"))
            paragraph_id = _int(item.get("paragraph_id"))
            page_no = _int(item.get("page_no"))
            para_no = _int(item.get("para_no"))
            if doc_id and (paragraph_id or (page_no and para_no)):
                params: dict[str, Any] = {"document_id": doc_id, "window_chars": 700}
                if paragraph_id:
                    params["paragraph_id"] = paragraph_id
                else:
                    params["page_no"] = page_no
                    params["para_no"] = para_no
                return params
    return {}


def _fallback_search_query(deterministic_plan: Any, loop_result: librarian_planner.BiblioLibrarianLoopResult) -> str:
    if _first_context_params(loop_result):
        return ""
    used = _used_search_queries(loop_result)
    for raw_query in _deterministic_queries(deterministic_plan):
        for candidate in _fallback_query_candidates(raw_query):
            if candidate and candidate not in used:
                return candidate
    return ""


def _used_search_queries(loop_result: librarian_planner.BiblioLibrarianLoopResult) -> set[str]:
    queries: set[str] = set()
    for step in loop_result.steps:
        call = step.tool_call
        if call is None or call.tool_name != librarian_tools.TOOL_CATALOG_SEARCH:
            continue
        for key in ("query", "q"):
            value = _text(call.params.get(key))
            if value:
                queries.add(value)
    return queries


def _deterministic_queries(deterministic_plan: Any) -> tuple[str, ...]:
    values: list[str] = []
    for attr in (
        "theme_query_variants",
        "catalogue_query_variants",
        "work_title_variants",
        "document_title_variants",
    ):
        raw = getattr(deterministic_plan, attr, ())
        if isinstance(raw, Sequence) and not isinstance(raw, (str, bytes, bytearray)):
            for item in raw:
                value = _text(item)
                if value and value not in values:
                    values.append(value)
    for attr in ("theme_query", "catalogue_query", "work_title", "document_title", "author"):
        value = _text(getattr(deterministic_plan, attr, ""))
        if value and value not in values:
            values.append(value)
    values.sort(key=_query_priority)
    return tuple(values)


def _query_priority(value: str) -> tuple[int, int]:
    return (0 if _has_non_ascii(value) else 1, len(value))


def _has_non_ascii(value: str) -> bool:
    return any(ord(char) > 127 for char in value)


def _fallback_query_candidates(raw_query: str) -> tuple[str, ...]:
    query = _text(raw_query)
    if not query:
        return ()
    tokens = [
        token
        for token in _query_tokens(query)
        if len(token) > 2 and token.casefold() not in _THEME_QUERY_STOPWORDS
    ]
    candidates: list[str] = []
    if len(tokens) >= 3:
        candidates.append(" ".join(tokens[-3:]))
    if len(tokens) >= 2:
        candidates.append(" ".join(tokens[-2:]))
    if tokens:
        candidates.append(tokens[-1])
    cleaned = " ".join(tokens)
    if cleaned:
        candidates.append(cleaned)
    if not candidates and query:
        candidates.append(query)
    allow_original = len(tokens) == 1
    out: list[str] = []
    for candidate in candidates:
        if not candidate or (not allow_original and candidate == query) or candidate in out:
            continue
        out.append(candidate)
    return tuple(out)


def _query_tokens(query: str) -> tuple[str, ...]:
    tokens: list[str] = []
    current: list[str] = []
    for char in query:
        if char.isalnum() or char in {"'", "’", "-"}:
            current.append(char)
            continue
        if current:
            tokens.append("".join(current).strip("'’-."))
            current = []
    if current:
        tokens.append("".join(current).strip("'’-."))
    return tuple(token for token in tokens if token)


def _consultation_message(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    status: str,
    reason_code: str,
) -> BiblioConsultationMessage:
    observed = loop_result.to_observability()
    doc_ids = tuple(str(item or "") for item in observed.get("doc_id_shorts", []) if str(item or ""))
    tool_results = [step.tool_result for step in loop_result.steps if step.tool_result is not None]
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
        doc_id_shorts=doc_ids,
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


def _state_anchor(tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> dict[str, Any]:
    for result in reversed(tool_results):
        doc_id = _text(getattr(result, "document_id", ""))
        if not doc_id and result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
        if not doc_id:
            continue
        position = result.positions[0] if result.positions else {}
        anchor = {
            "status": STATUS_AGENT_FIRST_EXECUTED,
            "reason_code": REASON_AGENT_FIRST_EXECUTED,
            "document_id": doc_id,
            "doc_id_short": _text(result.to_observability().get("doc_id_short")) or doc_id[:8],
            "page_no": _int(position.get("page_no")),
            "para_no": _int(position.get("para_no")),
            "paragraph_id": _int(position.get("paragraph_id")),
        }
        if result.context_text:
            anchor["passage_hash"] = hashlib.sha256(result.context_text.encode("utf-8")).hexdigest()[:12]
            anchor["passage_chars"] = len(result.context_text)
        return {key: value for key, value in anchor.items() if value}
    return {}


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
