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

from . import answer_extraction
from . import answer_resolution
from . import answer_surface
from . import answer_search
from . import answer_structure
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

FINAL_RESPONSE_SOURCE = "biblio_rendered_answer"
REASON_FINAL_RESPONSE_AUTHORIZED = "biblio_final_response_authorized"
REASON_FINAL_RESPONSE_MISSING_ANSWER = "biblio_final_response_answer_missing"
REASON_FINAL_RESPONSE_MISSING_RENDERED = "biblio_final_response_rendered_missing"
REASON_FINAL_RESPONSE_EMPTY_CONTENT = "biblio_final_response_empty_content"
REASON_FINAL_RESPONSE_INVALID_STATUS = "biblio_final_response_invalid_status"
REASON_FINAL_RESPONSE_STATUS_MISMATCH = "biblio_final_response_status_mismatch"
REASON_FINAL_RESPONSE_RENDER_MODE_MISMATCH = "biblio_final_response_render_mode_mismatch"
REASON_FINAL_RESPONSE_EXACT_CONTRACT_FAILED = "biblio_final_response_exact_contract_failed"
REASON_FINAL_RESPONSE_ANCHOR_MISSING = "biblio_final_response_anchor_missing"
REASON_FINAL_RESPONSE_BLOCKED_CONTRACT_FAILED = "biblio_final_response_blocked_contract_failed"
REASON_SURFACE_INTRO_EMPTY = "biblio_surface_intro_empty"
REASON_SURFACE_OUTRO_EMPTY = "biblio_surface_outro_empty"
REASON_SURFACE_INTRO_INVALID_TYPE = "biblio_surface_intro_invalid_type"
REASON_SURFACE_OUTRO_INVALID_TYPE = "biblio_surface_outro_invalid_type"
REASON_SURFACE_INTRO_TOO_LONG = "biblio_surface_intro_too_long"
REASON_SURFACE_OUTRO_TOO_LONG = "biblio_surface_outro_too_long"

ANSWER_HEADER = "[RESULTAT BIBLIO STRUCTURE]"
ANSWER_FOOTER = "[/RESULTAT BIBLIO STRUCTURE]"

DEFAULT_MAX_RENDERED_EXACT_CHARS = 8_000
DEFAULT_MAX_SURFACE_ENVELOPE_CHARS = 600

_KNOWN_STATUSES = frozenset(
    {
        STATUS_READY,
        STATUS_AMBIGUOUS,
        STATUS_NOT_FOUND,
        STATUS_NEEDS_CLARIFICATION,
        STATUS_ERROR,
    }
)

_STRUCTURAL_CLARIFICATION_REASONS = frozenset(
    {
        librarian_tools.REASON_SECTION_ALIAS_MISSING,
        librarian_tools.REASON_INTERNAL_WORK_UNRESOLVED,
        librarian_tools.REASON_WORK_ALIAS_MISSING,
        librarian_tools.REASON_PRIMARY_TEXT_ROLE_UNKNOWN,
        librarian_tools.REASON_SECTION_BOUNDS_UNAVAILABLE,
    }
)

_RENDER_LOW_PRIORITY_REASONS = frozenset(
    {
        librarian_tools.REASON_OK,
        librarian_planner.REASON_TOOL_EXECUTED,
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
    inventory_metadata: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    document_resolution: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    document_structure: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    scoped_search: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    extraction: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    truth_level: str = ""
    source_tool_names: tuple[str, ...] = field(default_factory=tuple)
    render_mode: str = RENDER_STRUCTURED_STATUS
    exact_text: str = field(default="", repr=False, compare=False)
    surface_intro: str = field(default="", repr=False, compare=False)
    surface_outro: str = field(default="", repr=False, compare=False)
    surface_empty_reason_codes: tuple[str, ...] = field(default_factory=tuple)

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
                "inventory_metadata": _inventory_observability(self.inventory_metadata),
                "document_resolution": answer_resolution.to_observability(self.document_resolution),
                "document_structure": answer_structure.to_observability(self.document_structure),
                "scoped_search": answer_search.to_observability(self.scoped_search),
                "extraction": answer_extraction.to_observability(self.extraction),
                "truth_level": self.truth_level,
                "source_tool_names": list(self.source_tool_names),
                "render_mode": self.render_mode,
                "exact_text_present": bool(self.exact_text),
                "exact_text_chars": self.exact_text_chars,
                "exact_text_hash": self.exact_text_hash,
                "surface_envelope": _surface_observability(
                    self.surface_intro,
                    self.surface_outro,
                    self.surface_empty_reason_codes,
                ),
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
    surface_intro_present: bool = False
    surface_intro_chars: int = 0
    surface_intro_hash: str = ""
    surface_outro_present: bool = False
    surface_outro_chars: int = 0
    surface_outro_hash: str = ""
    surface_empty_reason_codes: tuple[str, ...] = ()

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
                "surface_intro_present": self.surface_intro_present,
                "surface_intro_chars": self.surface_intro_chars,
                "surface_intro_hash": self.surface_intro_hash,
                "surface_outro_present": self.surface_outro_present,
                "surface_outro_chars": self.surface_outro_chars,
                "surface_outro_hash": self.surface_outro_hash,
                "surface_empty_reason_codes": list(self.surface_empty_reason_codes),
            }
        )


@dataclass(frozen=True, repr=False)
class BiblioFinalResponseLock:
    ok: bool
    reason_code: str
    content: str = field(default="", repr=False, compare=False)
    source: str = FINAL_RESPONSE_SOURCE
    status: str = ""
    render_mode: str = ""
    exact_text_rendered: bool = False
    exact_text_chars: int = 0
    exact_text_hash: str = ""
    surface_intro_present: bool = False
    surface_intro_chars: int = 0
    surface_intro_hash: str = ""
    surface_outro_present: bool = False
    surface_outro_chars: int = 0
    surface_outro_hash: str = ""
    surface_empty_reason_codes: tuple[str, ...] = ()

    def to_message_meta(self) -> dict[str, Any]:
        return _clean(
            {
                "source": self.source,
                "reason_code": self.reason_code,
                "biblio_answer_status": self.status,
                "biblio_render_mode": self.render_mode,
                "biblio_exact_text_rendered": self.exact_text_rendered,
                "biblio_exact_text_chars": self.exact_text_chars,
                "biblio_exact_text_hash": self.exact_text_hash,
                "biblio_surface_intro_present": self.surface_intro_present,
                "biblio_surface_intro_chars": self.surface_intro_chars,
                "biblio_surface_intro_hash": self.surface_intro_hash,
                "biblio_surface_outro_present": self.surface_outro_present,
                "biblio_surface_outro_chars": self.surface_outro_chars,
                "biblio_surface_outro_hash": self.surface_outro_hash,
                "biblio_surface_empty_reason_codes": list(self.surface_empty_reason_codes),
            }
        )

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "status": "authorized" if self.ok else "blocked",
                "reason_code": self.reason_code,
                "source": self.source,
                "answer_status": self.status,
                "render_mode": self.render_mode,
                "content_present": bool(self.content),
                "content_chars": len(self.content),
                "content_sha256_12": _hash(self.content),
                "exact_text_rendered": self.exact_text_rendered,
                "exact_text_chars": self.exact_text_chars,
                "exact_text_hash": self.exact_text_hash,
                "surface_intro_present": self.surface_intro_present,
                "surface_intro_chars": self.surface_intro_chars,
                "surface_intro_hash": self.surface_intro_hash,
                "surface_outro_present": self.surface_outro_present,
                "surface_outro_chars": self.surface_outro_chars,
                "surface_outro_hash": self.surface_outro_hash,
                "surface_empty_reason_codes": list(self.surface_empty_reason_codes),
                "semantic_judgment": False,
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
    surface_intro: Any = "",
    surface_outro: Any = "",
) -> BiblioAnswerObject:
    results = tuple(result for result in tool_results if result is not None)
    reason_codes = _unique([loop_reason_code, *(result.reason_code for result in results)])
    source_tool_names = _unique(result.tool_name for result in results)
    base_status = _answer_status(results, loop_status=loop_status, reason_codes=reason_codes)
    document_resolution = answer_resolution.build_document_resolution(
        results,
        product_method=product_method,
        base_status=base_status,
        reason_codes=reason_codes,
    )
    status = answer_resolution.override_answer_status(document_resolution, base_status=base_status)
    document_structure = answer_structure.build_document_structure(
        results,
        product_method=product_method,
        base_status=status,
        reason_codes=reason_codes,
    )
    status = answer_structure.override_answer_status(document_structure, base_status=status)
    scoped_search = answer_search.build_scoped_search(
        results,
        product_method=product_method,
        base_status=status,
        reason_codes=reason_codes,
    )
    status = answer_search.override_answer_status(scoped_search, base_status=status)
    extraction = answer_extraction.build_extraction(
        results,
        product_method=product_method,
        base_status=status,
        reason_codes=reason_codes,
    )
    status = answer_extraction.override_answer_status(extraction, base_status=status)
    exact_text = _exact_text_for_method(results, product_method=product_method, extraction=extraction, status=status)
    selected = _selected_candidate(results, status=status)
    document_id = _document_id(results, selected)
    interval = _interval(results)
    anchors = _anchors(results, interval, extraction=extraction)
    render_mode = _render_mode(status, exact_text)
    inventory_metadata = _inventory_metadata(results, product_method)
    surface_intro_text, surface_outro_text, surface_empty_reasons = _surface_envelope(
        surface_intro,
        surface_outro,
    )

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
        inventory_metadata=inventory_metadata,
        document_resolution=document_resolution,
        document_structure=document_structure,
        scoped_search=scoped_search,
        extraction=extraction,
        truth_level=_text(truth_level) or _default_truth(product_method),
        source_tool_names=source_tool_names,
        render_mode=render_mode,
        exact_text=exact_text,
        surface_intro=surface_intro_text,
        surface_outro=surface_outro_text,
        surface_empty_reason_codes=surface_empty_reasons,
    )


def build_final_response_lock(
    answer: BiblioAnswerObject | None,
    rendered: BiblioRenderedAnswer | None,
) -> BiblioFinalResponseLock:
    if answer is None:
        return BiblioFinalResponseLock(
            ok=False,
            reason_code=REASON_FINAL_RESPONSE_MISSING_ANSWER,
        )
    if rendered is None:
        return BiblioFinalResponseLock(
            ok=False,
            reason_code=REASON_FINAL_RESPONSE_MISSING_RENDERED,
            status=answer.status,
            render_mode=answer.render_mode,
        )
    reason_code = _final_response_contract_reason(answer, rendered)
    ok = reason_code == REASON_FINAL_RESPONSE_AUTHORIZED
    return BiblioFinalResponseLock(
        ok=ok,
        reason_code=reason_code,
        content=rendered.content if ok else "",
        status=answer.status,
        render_mode=rendered.render_mode,
        exact_text_rendered=rendered.exact_text_rendered,
        exact_text_chars=rendered.exact_text_chars,
        exact_text_hash=rendered.exact_text_hash,
        surface_intro_present=rendered.surface_intro_present,
        surface_intro_chars=rendered.surface_intro_chars,
        surface_intro_hash=rendered.surface_intro_hash,
        surface_outro_present=rendered.surface_outro_present,
        surface_outro_chars=rendered.surface_outro_chars,
        surface_outro_hash=rendered.surface_outro_hash,
        surface_empty_reason_codes=rendered.surface_empty_reason_codes,
    )


def render_biblio_answer_object(
    answer: BiblioAnswerObject,
    *,
    max_exact_chars: int = DEFAULT_MAX_RENDERED_EXACT_CHARS,
) -> BiblioRenderedAnswer:
    max_exact_chars = _bounded_int(max_exact_chars, minimum=0, maximum=DEFAULT_MAX_RENDERED_EXACT_CHARS)
    reason_code = _render_reason_code(answer)
    exact_text = answer.exact_text if answer.status == STATUS_READY else ""
    exact_rendered = False
    if answer.render_mode == RENDER_EXACT_EXCERPT and exact_text and len(exact_text) <= max_exact_chars:
        lines = answer_surface.exact_excerpt_lines(answer, exact_text)
        exact_rendered = True
    else:
        lines = _structured_answer_lines(answer)
        if answer.status == STATUS_READY and not lines:
            lines.append("Resultat documentaire pret, sans extrait exact a afficher ici.")
        elif answer.status != STATUS_READY and not lines:
            lines.append(_blocked_exact_line(answer.status))
    content = "\n".join(_surface_wrapped_lines(answer, lines))
    return BiblioRenderedAnswer(
        status=answer.status,
        reason_code=reason_code,
        render_mode=answer.render_mode,
        content=content,
        exact_text_rendered=exact_rendered,
        exact_text_chars=len(exact_text) if exact_rendered else 0,
        exact_text_hash=_hash(exact_text) if exact_rendered else "",
        surface_intro_present=bool(answer.surface_intro),
        surface_intro_chars=len(answer.surface_intro),
        surface_intro_hash=_hash(answer.surface_intro),
        surface_outro_present=bool(answer.surface_outro),
        surface_outro_chars=len(answer.surface_outro),
        surface_outro_hash=_hash(answer.surface_outro),
        surface_empty_reason_codes=answer.surface_empty_reason_codes,
    )


def _surface_envelope(surface_intro: Any, surface_outro: Any) -> tuple[str, str, tuple[str, ...]]:
    intro, intro_reason = _surface_text(
        surface_intro,
        empty_reason=REASON_SURFACE_INTRO_EMPTY,
        invalid_type_reason=REASON_SURFACE_INTRO_INVALID_TYPE,
        too_long_reason=REASON_SURFACE_INTRO_TOO_LONG,
    )
    outro, outro_reason = _surface_text(
        surface_outro,
        empty_reason=REASON_SURFACE_OUTRO_EMPTY,
        invalid_type_reason=REASON_SURFACE_OUTRO_INVALID_TYPE,
        too_long_reason=REASON_SURFACE_OUTRO_TOO_LONG,
    )
    return intro, outro, _unique([intro_reason, outro_reason])


def _surface_text(
    value: Any,
    *,
    empty_reason: str,
    invalid_type_reason: str,
    too_long_reason: str,
) -> tuple[str, str]:
    if not isinstance(value, str):
        return "", invalid_type_reason
    text = value.strip()
    if not text:
        return "", empty_reason
    if len(text) > DEFAULT_MAX_SURFACE_ENVELOPE_CHARS:
        return "", too_long_reason
    return text, ""


def _surface_wrapped_lines(answer: BiblioAnswerObject, base_lines: Sequence[str]) -> list[str]:
    lines: list[str] = []
    if answer.surface_intro:
        lines.extend(answer.surface_intro.splitlines())
        if base_lines:
            lines.append("")
    lines.extend(base_lines)
    if answer.surface_outro:
        if lines:
            lines.append("")
        lines.extend(answer.surface_outro.splitlines())
    return lines


def _surface_observability(
    surface_intro: str,
    surface_outro: str,
    empty_reason_codes: Sequence[str],
) -> dict[str, Any]:
    return _clean(
        {
            "intro_present": bool(surface_intro),
            "intro_chars": len(surface_intro),
            "intro_hash": _hash(surface_intro),
            "outro_present": bool(surface_outro),
            "outro_chars": len(surface_outro),
            "outro_hash": _hash(surface_outro),
            "empty_reason_codes": list(empty_reason_codes),
        }
    )


def _structured_answer_lines(answer: BiblioAnswerObject) -> list[str]:
    lines: list[str] = []
    if answer.inventory_metadata:
        lines.extend(_inventory_lines(answer.inventory_metadata))
    if answer.document_resolution:
        lines.extend(answer_resolution.render_lines(answer.document_resolution))
    if answer.document_structure:
        lines.extend(answer_structure.render_lines(answer.document_structure))
    if answer.scoped_search:
        lines.extend(answer_search.render_lines(answer.scoped_search))
    if answer.extraction:
        lines.extend(answer_extraction.render_lines(answer.extraction))
    if (
        answer.product_method == product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE
        and answer.status == STATUS_READY
        and not answer.exact_text
    ):
        lines.append(
            "Plage canonique non rendue: l'intervalle complet debut/fin n'a pas ete extrait mecaniquement."
        )
    if answer.interval and not answer.document_structure:
        interval = _visible_interval_line(answer.interval)
        if interval:
            lines.append(interval)
    if not lines:
        status_line = _visible_status_line(answer.status)
        if status_line:
            lines.append(status_line)
    return lines


def _visible_interval_line(interval: Mapping[str, Any]) -> str:
    state = _text(interval.get("state"))
    if state == "derived":
        return "Bornes documentaires derivees."
    if state == "known":
        return "Bornes documentaires connues."
    if state == "ambiguous":
        return "Bornes documentaires ambigues."
    return ""


def _visible_status_line(status: str) -> str:
    if status == STATUS_AMBIGUOUS:
        return "Plusieurs possibilites restent ouvertes; il faut clarifier avant de rendre un extrait exact."
    if status == STATUS_NOT_FOUND:
        return "Aucun resultat exploitable n'a ete trouve dans le scope demande."
    if status == STATUS_NEEDS_CLARIFICATION:
        return "Je ne peux pas rendre un extrait exact sans precision ou ancre supplementaire."
    if status == STATUS_ERROR:
        return "La lecture Biblio n'a pas pu aboutir."
    return ""


def _blocked_exact_line(status: str) -> str:
    status_line = _visible_status_line(status)
    if status_line:
        return status_line
    return "Extraction exacte non rendue: structure ou ancre insuffisante."


def _render_reason_code(answer: BiblioAnswerObject) -> str:
    family_reason_codes = _unique(
        [
            *_payload_reason_codes(answer.document_resolution),
            *_payload_reason_codes(answer.document_structure),
            *_payload_reason_codes(answer.scoped_search),
            *_payload_reason_codes(answer.extraction),
        ]
    )
    for reason in family_reason_codes:
        if reason not in _RENDER_LOW_PRIORITY_REASONS:
            return reason
    for reason in answer.reason_codes:
        if reason not in _RENDER_LOW_PRIORITY_REASONS:
            return reason
    if answer.reason_codes:
        return answer.reason_codes[0]
    return family_reason_codes[0] if family_reason_codes else ""


def _payload_reason_codes(payload: Mapping[str, Any]) -> tuple[str, ...]:
    raw = payload.get("reason_codes") if payload else ()
    if not isinstance(raw, Sequence) or isinstance(raw, (str, bytes, bytearray)):
        return ()
    return _unique(raw)


def _final_response_contract_reason(
    answer: BiblioAnswerObject,
    rendered: BiblioRenderedAnswer,
) -> str:
    if not rendered.content:
        return REASON_FINAL_RESPONSE_EMPTY_CONTENT
    if answer.status not in _KNOWN_STATUSES:
        return REASON_FINAL_RESPONSE_INVALID_STATUS
    if rendered.status != answer.status:
        return REASON_FINAL_RESPONSE_STATUS_MISMATCH
    if rendered.render_mode != answer.render_mode:
        return REASON_FINAL_RESPONSE_RENDER_MODE_MISMATCH
    if rendered.exact_text_rendered:
        if (
            answer.status != STATUS_READY
            or answer.render_mode != RENDER_EXACT_EXCERPT
            or not answer.exact_text
            or rendered.exact_text_hash != answer.exact_text_hash
            or rendered.exact_text_chars != answer.exact_text_chars
        ):
            return REASON_FINAL_RESPONSE_EXACT_CONTRACT_FAILED
        if not answer.anchors:
            return REASON_FINAL_RESPONSE_ANCHOR_MISSING
        if not _exact_rendered_anchor_coverage_ok(answer):
            return REASON_FINAL_RESPONSE_ANCHOR_MISSING
    elif answer.status != STATUS_READY and rendered.render_mode != RENDER_BLOCKED_EXACT:
        return REASON_FINAL_RESPONSE_BLOCKED_CONTRACT_FAILED
    return REASON_FINAL_RESPONSE_AUTHORIZED


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
    *,
    extraction: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], ...]:
    extraction_anchors = _extraction_block_anchors(extraction or {})
    if extraction:
        return extraction_anchors
    for result in reversed(results):
        if result.anchors:
            return tuple(dict(anchor) for anchor in result.anchors)
    for result in reversed(results):
        if result.positions:
            anchors: list[dict[str, Any]] = []
            for position in result.positions:
                anchor = dict(position)
                document_id = _text(getattr(result, "document_id", ""))
                if document_id:
                    anchor.setdefault("document_id", document_id)
                anchors.append(anchor)
            return tuple(anchors)
    anchors = []
    for key in ("start", "end"):
        anchor = interval.get(key)
        if isinstance(anchor, Mapping) and anchor:
            anchors.append(dict(anchor))
    return tuple(anchors)


def _extraction_block_anchors(extraction: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    if _text(extraction.get("status")) != "resolved":
        return ()
    anchors: list[dict[str, Any]] = []
    blocks = extraction.get("blocks")
    if not isinstance(blocks, Sequence) or isinstance(blocks, (str, bytes, bytearray)):
        return ()
    for block in blocks:
        if not isinstance(block, Mapping):
            continue
        document_id = _text(block.get("document_id"))
        for key in ("anchor", "anchor_end"):
            raw_anchor = block.get(key)
            if not isinstance(raw_anchor, Mapping):
                continue
            anchor = dict(raw_anchor)
            if document_id:
                anchor.setdefault("document_id", document_id)
            if (
                _text(anchor.get("document_id"))
                and (_int(anchor.get("page_no")) or _int(anchor.get("paragraph_id")))
                and anchor not in anchors
            ):
                anchors.append(anchor)
    return tuple(anchors)


def _exact_rendered_anchor_coverage_ok(answer: BiblioAnswerObject) -> bool:
    extraction = answer.extraction
    if not extraction or _text(extraction.get("status")) != "resolved":
        return True
    required = _extraction_block_anchors(extraction)
    if not required:
        return False
    available = {_anchor_key(anchor) for anchor in answer.anchors}
    return all(_anchor_key(anchor) in available for anchor in required)


def _anchor_key(anchor: Mapping[str, Any]) -> tuple[str, int, int]:
    return (
        _text(anchor.get("document_id")),
        _int(anchor.get("page_no")),
        _int(anchor.get("paragraph_id")),
    )


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


def _inventory_metadata(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    product_method: str,
) -> dict[str, Any]:
    if product_methods.canonical_family_for_method(product_method) != product_methods.CANONICAL_FAMILY_INVENTORY_METADATA:
        return {}
    documents: list[dict[str, Any]] = []
    total_count = 0
    truncated = False
    metadata_statuses: list[str] = []
    for result in results:
        observed = result.to_observability()
        total_count = max(total_count, _int(observed.get("total_count")))
        truncated = truncated or bool(observed.get("truncated"))
        for item in result.items:
            document = _inventory_document(item)
            if document:
                documents.append(document)
        if result.document_summary:
            document = _inventory_document(result.document_summary)
            if document:
                documents.append(document)
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for document in documents:
        key = _text(document.get("document_id")) or _text(document.get("doc_id_short"))
        if key and key in seen:
            continue
        if key:
            seen.add(key)
        status = _text(document.get("metadata_status"))
        if status and status not in metadata_statuses:
            metadata_statuses.append(status)
        deduped.append(document)
    if not deduped and not total_count:
        return {}
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_INVENTORY_METADATA,
            "documents": deduped,
            "document_count": len(deduped),
            "total_count": total_count,
            "truncated": truncated,
            "metadata_statuses": metadata_statuses,
        }
    )


def _inventory_document(raw: Mapping[str, Any]) -> dict[str, Any]:
    doc_id = _text(raw.get("document_id"))
    doc_id_short = _text(raw.get("doc_id_short")) or short_doc_id(doc_id)
    if not doc_id and not doc_id_short:
        return {}
    return _clean(
        {
            "document_id": doc_id,
            "doc_id_short": doc_id_short,
            "title": _text(raw.get("title")),
            "authors": _text(raw.get("authors")),
            "language": _text(raw.get("language")),
            "page_count": _int(raw.get("page_count")),
            "metadata_status": _text(raw.get("metadata_status")),
        }
    )


def _inventory_lines(payload: Mapping[str, Any]) -> list[str]:
    lines = ["Bibliotheque:"]
    total_count = _int(payload.get("total_count"))
    document_count = _int(payload.get("document_count"))
    if total_count:
        lines.append(f"- {total_count} ouvrages repertories.")
    if document_count:
        lines.append(f"- {document_count} ouvrages affiches dans cette reponse.")
    if bool(payload.get("truncated")):
        lines.append("- Liste bornee: certains ouvrages ne sont pas affiches ici.")
    raw_documents = payload.get("documents")
    documents = raw_documents if isinstance(raw_documents, Sequence) and not isinstance(raw_documents, (str, bytes, bytearray)) else ()
    for index, raw_document in enumerate(documents[:20], 1):
        if not isinstance(raw_document, Mapping):
            continue
        parts = [f"{index}. "]
        title = _text(raw_document.get("title"))
        authors = _text(raw_document.get("authors"))
        language = _text(raw_document.get("language"))
        page_count = _int(raw_document.get("page_count"))
        metadata_status = _text(raw_document.get("metadata_status"))
        if title:
            parts[0] += _neutralize(title)
        else:
            parts[0] += "Ouvrage du catalogue"
        if authors:
            parts.append(f"auteur: {_neutralize(authors)}")
        if language:
            parts.append(f"langue: {_neutralize(language)}")
        if page_count:
            parts.append(f"{page_count} pages")
        if metadata_status:
            visible_status = _visible_metadata_status(metadata_status)
            if visible_status:
                parts.append(visible_status)
        lines.append("; ".join(parts))
    if len(documents) > 20:
        lines.append(f"... {len(documents) - 20} documents supplementaires masques par borne.")
    return lines


def _visible_metadata_status(value: str) -> str:
    text = _text(value)
    if text in {"validated", "known", "complete"}:
        return "metadonnees connues"
    if text in {"unknown", "missing"}:
        return "metadonnees incompletes"
    if text:
        return "metadonnees disponibles"
    return ""


def _inventory_observability(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    raw_documents = payload.get("documents")
    documents = raw_documents if isinstance(raw_documents, Sequence) and not isinstance(raw_documents, (str, bytes, bytearray)) else ()
    language_values = [
        _text(document.get("language"))
        for document in documents
        if isinstance(document, Mapping) and _text(document.get("language"))
    ]
    page_count_known = sum(
        1
        for document in documents
        if isinstance(document, Mapping) and _int(document.get("page_count")) > 0
    )
    return _clean(
        {
            "family": _text(payload.get("family")),
            "document_count": _int(payload.get("document_count")),
            "total_count": _int(payload.get("total_count")),
            "truncated": bool(payload.get("truncated")),
            "language_known_count": len(language_values),
            "language_hashes": [_hash(value) for value in language_values],
            "page_count_known_count": page_count_known,
            "metadata_statuses": list(payload.get("metadata_statuses") or ()),
        }
    )


def _exact_text_for_method(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    extraction: Mapping[str, Any],
    status: str,
) -> str:
    if status != STATUS_READY or not _method_allows_exact_text(product_method):
        return ""
    if product_method == product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE and not extraction:
        return ""
    if extraction:
        return answer_extraction.mechanical_exact_text(results, extraction)
    return _mechanical_exact_text(results)


def _mechanical_exact_text(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> str:
    for result in reversed(results):
        if not _mechanical_result_has_anchor(result):
            continue
        if result.context_text and result.tool_name == librarian_tools.TOOL_PASSAGE_CONTEXT:
            return result.context_text
        if result.page_text and result.tool_name == librarian_tools.TOOL_PAGE_READ:
            return result.page_text
    return ""


def _mechanical_result_has_anchor(result: librarian_tools.BiblioLibrarianToolResult) -> bool:
    document_id = _text(getattr(result, "document_id", ""))
    if not document_id:
        return False
    for position in result.positions:
        if not isinstance(position, Mapping):
            continue
        if _int(position.get("paragraph_id")) or _int(position.get("page_no")):
            return True
    return False


def _method_allows_exact_text(product_method: str) -> bool:
    method = _text(product_method)
    if method == product_methods.PRODUCT_METHOD_SCOPED_SEARCH:
        return False
    family = product_methods.canonical_family_for_method(method)
    if not family:
        return True
    return family in {
        product_methods.CANONICAL_FAMILY_SCOPED_SEARCH,
        product_methods.CANONICAL_FAMILY_EXTRACTION,
        product_methods.CANONICAL_FAMILY_READER_NAVIGATION,
        product_methods.CANONICAL_FAMILY_PROVENANCE,
        product_methods.CANONICAL_FAMILY_ANCHORING_STATE,
    }


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


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


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
