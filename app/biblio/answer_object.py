"""Structured Biblio answer object and minimal renderer.

Lot 3 deliberately stays downstream of the librarian and the GET-only tools.
It does not choose a document, section, or anchor. It only projects already
executed tool results into a content-free truth object, then renders the
minimal product status or a mechanically available exact text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
from typing import Any, Mapping, Sequence

from . import librarian_planner
from . import librarian_product_methods as product_methods
from . import librarian_tools
from .catalogue_client import short_doc_id


SCHEMA_VERSION = "frida_biblio_answer_object.v1"

STATUS_READY = "ready"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_NOT_FOUND = "not_found"
STATUS_NEEDS_CLARIFICATION = "needs_clarification"
STATUS_ERROR = "error"

RENDER_STRUCTURED_STATUS = "structured_status"
RENDER_EXACT_EXCERPT = "exact_excerpt"
RENDER_BLOCKED_EXACT = "blocked_exact"

ANSWER_HEADER = "[RESULTAT BIBLIO STRUCTURE]"
ANSWER_FOOTER = "[/RESULTAT BIBLIO STRUCTURE]"

DEFAULT_MAX_RENDERED_EXACT_CHARS = 8_000

_STRUCTURAL_CLARIFICATION_REASONS = frozenset(
    {
        librarian_tools.REASON_SECTION_ALIAS_MISSING,
        librarian_tools.REASON_INTERNAL_WORK_UNRESOLVED,
        librarian_tools.REASON_WORK_ALIAS_MISSING,
        librarian_tools.REASON_PRIMARY_TEXT_ROLE_UNKNOWN,
        librarian_tools.REASON_SECTION_BOUNDS_UNAVAILABLE,
    }
)


@dataclass(frozen=True, repr=False)
class BiblioAnswerObject:
    status: str
    reason_codes: tuple[str, ...] = field(default_factory=tuple)
    product_method: str = ""
    case_id: str = ""
    document_id: str = field(default="", repr=False, compare=False)
    work_id: str = ""
    work_state: str = ""
    section_id: str = ""
    section_state: str = ""
    anchors: tuple[dict[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    interval: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    content_role: str = ""
    provenance: dict[str, Any] = field(default_factory=dict)
    limits: tuple[str, ...] = field(default_factory=tuple)
    truth_level: str = ""
    source_tool_names: tuple[str, ...] = field(default_factory=tuple)
    render_mode: str = RENDER_STRUCTURED_STATUS
    exact_text: str = field(default="", repr=False, compare=False)

    @property
    def exact_text_hash(self) -> str:
        return _hash(self.exact_text)

    @property
    def exact_text_chars(self) -> int:
        return len(self.exact_text)

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "status": self.status,
                "reason_codes": list(self.reason_codes),
                "product_method": self.product_method,
                "case_id": self.case_id,
                "doc_id_short": short_doc_id(self.document_id),
                "work_id": self.work_id,
                "work_state": self.work_state,
                "section_id": self.section_id,
                "section_state": self.section_state,
                "anchor_count": len(self.anchors),
                "interval_state": _text(self.interval.get("state")),
                "interval_type": _text(self.interval.get("type")),
                "content_role": self.content_role,
                "provenance": dict(self.provenance),
                "limits": list(self.limits),
                "truth_level": self.truth_level,
                "source_tool_names": list(self.source_tool_names),
                "render_mode": self.render_mode,
                "exact_text_present": bool(self.exact_text),
                "exact_text_chars": self.exact_text_chars,
                "exact_text_hash": self.exact_text_hash,
            }
        )


@dataclass(frozen=True, repr=False)
class BiblioRenderedAnswer:
    status: str
    reason_code: str
    render_mode: str
    content: str = field(default="", repr=False, compare=False)
    exact_text_rendered: bool = False
    exact_text_chars: int = 0
    exact_text_hash: str = ""

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "status": self.status,
                "reason_code": self.reason_code,
                "render_mode": self.render_mode,
                "present": bool(self.content),
                "chars": len(self.content),
                "exact_text_rendered": self.exact_text_rendered,
                "exact_text_chars": self.exact_text_chars,
                "exact_text_hash": self.exact_text_hash,
            }
        )


def build_biblio_answer_object(
    *,
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
    loop_status: str = "",
    loop_reason_code: str = "",
    product_method: str = "",
    case_id: str = "",
    truth_level: str = "",
) -> BiblioAnswerObject:
    results = tuple(result for result in tool_results if result is not None)
    reason_codes = _unique([loop_reason_code, *(result.reason_code for result in results)])
    source_tool_names = _unique(result.tool_name for result in results)
    status = _answer_status(results, loop_status=loop_status, reason_codes=reason_codes)
    exact_text = _mechanical_exact_text(results) if status == STATUS_READY else ""
    selected = _selected_candidate(results, status=status)
    document_id = _document_id(results, selected)
    interval = _interval(results)
    anchors = _anchors(results, interval)
    render_mode = _render_mode(status, exact_text)

    return BiblioAnswerObject(
        status=status,
        reason_codes=reason_codes,
        product_method=_text(product_method),
        case_id=_text(case_id),
        document_id=document_id,
        work_id=_text(selected.get("work_id")),
        work_state=_state_from_candidate(selected, "work"),
        section_id=_text(selected.get("section_id")),
        section_state=_state_from_candidate(selected, "section"),
        anchors=anchors,
        interval=interval,
        content_role=_text(selected.get("content_role")),
        provenance=_provenance(results),
        limits=_limits(results, selected),
        truth_level=_text(truth_level) or _default_truth(product_method),
        source_tool_names=source_tool_names,
        render_mode=render_mode,
        exact_text=exact_text,
    )


def render_biblio_answer_object(
    answer: BiblioAnswerObject,
    *,
    max_exact_chars: int = DEFAULT_MAX_RENDERED_EXACT_CHARS,
) -> BiblioRenderedAnswer:
    max_exact_chars = _bounded_int(max_exact_chars, minimum=0, maximum=DEFAULT_MAX_RENDERED_EXACT_CHARS)
    reason_code = answer.reason_codes[0] if answer.reason_codes else ""
    lines = [
        ANSWER_HEADER,
        "Contrat de restitution:",
        "- Ceci est le resultat structure Biblio, pas une generation libre.",
        "- Le renderer ne choisit pas une oeuvre, une section ou une ancre ambigue.",
        f"Status: {answer.status}",
        f"Render mode: {answer.render_mode}",
    ]
    if reason_code:
        lines.append(f"Reason: {reason_code}")
    if answer.product_method:
        lines.append(f"Product method: {answer.product_method}")
    if answer.document_id:
        lines.append(f"Document: catalogue_doc={short_doc_id(answer.document_id)}")
    if answer.section_id:
        lines.append(f"Section: {answer.section_id}")
    if answer.interval:
        lines.append(
            "Intervalle: "
            + ", ".join(
                part
                for part in (
                    f"type={_text(answer.interval.get('type'))}" if _text(answer.interval.get("type")) else "",
                    f"state={_text(answer.interval.get('state'))}" if _text(answer.interval.get("state")) else "",
                )
                if part
            )
        )

    exact_text = answer.exact_text if answer.status == STATUS_READY else ""
    exact_rendered = False
    if answer.render_mode == RENDER_EXACT_EXCERPT and exact_text and len(exact_text) <= max_exact_chars:
        lines.extend(["Texte exact rendu mecaniquement:", _neutralize(exact_text)])
        exact_rendered = True
    elif answer.status == STATUS_READY:
        lines.append("Resultat structure pret; aucun texte exact n'est rendu par ce cran.")
    else:
        lines.append("Extraction exacte non rendue: statut ou structure insuffisante.")
    lines.append(ANSWER_FOOTER)
    content = "\n".join(lines)
    return BiblioRenderedAnswer(
        status=answer.status,
        reason_code=reason_code,
        render_mode=answer.render_mode,
        content=content,
        exact_text_rendered=exact_rendered,
        exact_text_chars=len(exact_text) if exact_rendered else 0,
        exact_text_hash=_hash(exact_text) if exact_rendered else "",
    )


def _answer_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    loop_status: str,
    reason_codes: Sequence[str],
) -> str:
    if loop_status == librarian_planner.STATUS_NEEDS_CLARIFICATION:
        return STATUS_NEEDS_CLARIFICATION
    if any(result.status == librarian_tools.STATUS_ERROR for result in results):
        return STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return STATUS_AMBIGUOUS
    if any(reason in _STRUCTURAL_CLARIFICATION_REASONS for reason in reason_codes):
        return STATUS_NEEDS_CLARIFICATION
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return STATUS_NOT_FOUND
    if results and all(result.status in {librarian_tools.STATUS_OK, librarian_tools.STATUS_RESOLVED} for result in results):
        return STATUS_READY
    if not results:
        return STATUS_NEEDS_CLARIFICATION
    return STATUS_ERROR


def _render_mode(status: str, exact_text: str) -> str:
    if status != STATUS_READY:
        return RENDER_BLOCKED_EXACT
    if exact_text:
        return RENDER_EXACT_EXCERPT
    return RENDER_STRUCTURED_STATUS


def _selected_candidate(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    status: str,
) -> Mapping[str, Any]:
    if status != STATUS_READY:
        return {}
    for result in reversed(results):
        if len(result.items) == 1:
            item = result.items[0]
            if isinstance(item, Mapping):
                return item
    return {}


def _document_id(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    selected: Mapping[str, Any],
) -> str:
    direct = _text(selected.get("document_id"))
    if direct:
        return direct
    ids: list[str] = []
    for result in results:
        value = _text(getattr(result, "document_id", ""))
        if value and value not in ids:
            ids.append(value)
        for item in result.items:
            if isinstance(item, Mapping):
                value = _text(item.get("document_id"))
                if value and value not in ids:
                    ids.append(value)
    return ids[0] if len(ids) == 1 else ""


def _interval(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> dict[str, Any]:
    for result in reversed(results):
        if result.interval:
            return dict(result.interval)
    return {}


def _anchors(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    interval: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    for result in reversed(results):
        if result.anchors:
            return tuple(dict(anchor) for anchor in result.anchors)
    anchors = []
    for key in ("start", "end"):
        anchor = interval.get(key)
        if isinstance(anchor, Mapping) and anchor:
            anchors.append(dict(anchor))
    return tuple(anchors)


def _provenance(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> dict[str, Any]:
    endpoint_kinds = _unique(result.endpoint_kind for result in results)
    doc_id_shorts = _unique(
        _text(result.to_observability().get("doc_id_short"))
        for result in results
        if _text(result.to_observability().get("doc_id_short"))
    )
    return _clean(
        {
            "endpoint_kinds": list(endpoint_kinds),
            "doc_id_shorts": list(doc_id_shorts),
            "tool_count": len(results),
        }
    )


def _limits(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    selected: Mapping[str, Any],
) -> tuple[str, ...]:
    values: list[str] = []
    for item in (*[selected], *(candidate for result in results for candidate in result.items)):
        if not isinstance(item, Mapping):
            continue
        raw = item.get("limits")
        if isinstance(raw, (list, tuple)):
            values.extend(_text(value) for value in raw if _text(value))
    return _unique(values)


def _mechanical_exact_text(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> str:
    for result in reversed(results):
        if result.context_text:
            return result.context_text
        if result.page_text:
            return result.page_text
    return ""


def _state_from_candidate(candidate: Mapping[str, Any], kind: str) -> str:
    if not candidate:
        return ""
    if kind == "work" and _text(candidate.get("work_id")):
        return STATUS_READY
    if kind == "section" and _text(candidate.get("section_id")):
        return STATUS_READY
    return ""


def _default_truth(product_method: str) -> str:
    spec = product_methods.get_product_method_spec(_text(product_method))
    if not spec or not spec.truth_levels:
        return ""
    return _text(spec.truth_levels[0])


def _unique(values: Sequence[Any]) -> tuple[str, ...]:
    items: list[str] = []
    for value in values:
        text = _text(value)
        if text and text not in items:
            items.append(text)
    return tuple(items)


def _hash(value: str) -> str:
    text = _text(value)
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _bounded_int(value: Any, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return maximum
    return min(max(parsed, minimum), maximum)


def _neutralize(value: str) -> str:
    return (
        value.replace(ANSWER_HEADER, "[RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace(ANSWER_FOOTER, "[/RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace("[CONSULTATION DE BIBLIOTHEQUE]", "[CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[/CONSULTATION DE BIBLIOTHEQUE]", "[/CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
        .replace("[/PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
    )


def _clean(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in ("", None, [], {}, ())}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""
