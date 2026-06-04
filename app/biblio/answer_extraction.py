"""Mechanical extraction projection for Biblio answer objects.

The extraction family reports text that already came from bounded GET-only
reading tools. It does not pick a passage, interpret relevance, or turn search
snippets into exact excerpts.
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping, Sequence

from . import librarian_product_methods as product_methods
from . import librarian_tools
from .catalogue_client import short_doc_id


ANSWER_STATUS_READY = "ready"
ANSWER_STATUS_AMBIGUOUS = "ambiguous"
ANSWER_STATUS_NOT_FOUND = "not_found"
ANSWER_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
ANSWER_STATUS_ERROR = "error"

EXTRACTION_STATUS_RESOLVED = "resolved"
EXTRACTION_STATUS_AMBIGUOUS = "ambiguous"
EXTRACTION_STATUS_NOT_FOUND = "not_found"
EXTRACTION_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
EXTRACTION_STATUS_ERROR = "error"

_MECHANICAL_TEXT_TOOLS = frozenset(
    {
        librarian_tools.TOOL_PAGE_READ,
        librarian_tools.TOOL_PASSAGE_CONTEXT,
    }
)


def build_extraction(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    base_status: str,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    if product_method != product_methods.PRODUCT_METHOD_EXTRACTION:
        return {}
    candidates = _candidates_from_results(results)
    extraction_attempted = any(result.tool_name in _MECHANICAL_TEXT_TOOLS for result in results)
    selected = candidates[0] if candidates else {}
    status = _extraction_status(
        results,
        selected=selected,
        extraction_attempted=extraction_attempted,
        base_status=base_status,
    )
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_EXTRACTION,
            "status": status,
            "source_tool_name": _text(selected.get("source_tool_name")),
            "document_id": _text(selected.get("document_id")),
            "doc_id_short": _text(selected.get("doc_id_short")),
            "content_kind": _text(selected.get("content_kind")),
            "exact_text_present": bool(selected.get("exact_text_present")) and _has_minimum_anchor(selected),
            "exact_text_chars": _int(selected.get("exact_text_chars")),
            "exact_text_hash": _text(selected.get("exact_text_hash")),
            "anchor": _mapping(selected.get("anchor")),
            "candidate_count": len(candidates),
            "extraction_attempted": extraction_attempted,
            "reason_codes": list(_reason_codes(reason_codes, status=status, selected=selected, extraction_attempted=extraction_attempted)),
            "limits": list(_limits(selected, extraction_attempted=extraction_attempted)),
        }
    )


def override_answer_status(payload: Mapping[str, Any], *, base_status: str) -> str:
    if not payload:
        return base_status
    status = _text(payload.get("status"))
    if status == EXTRACTION_STATUS_RESOLVED:
        return ANSWER_STATUS_READY
    if status == EXTRACTION_STATUS_AMBIGUOUS:
        return ANSWER_STATUS_AMBIGUOUS
    if status == EXTRACTION_STATUS_NOT_FOUND:
        return ANSWER_STATUS_NOT_FOUND
    if status == EXTRACTION_STATUS_NEEDS_CLARIFICATION:
        return ANSWER_STATUS_NEEDS_CLARIFICATION
    if status == EXTRACTION_STATUS_ERROR:
        return ANSWER_STATUS_ERROR
    return base_status


def mechanical_exact_text(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    payload: Mapping[str, Any],
) -> str:
    if _text(payload.get("status")) != EXTRACTION_STATUS_RESOLVED:
        return ""
    source_tool_name = _text(payload.get("source_tool_name"))
    document_id = _text(payload.get("document_id"))
    content_kind = _text(payload.get("content_kind"))
    for result in results:
        if result.tool_name != source_tool_name:
            continue
        if _text(getattr(result, "document_id", "")) != document_id:
            continue
        if not _has_result_anchor(result):
            continue
        text = _result_text(result, content_kind=content_kind)
        if text:
            return text
    return ""


def render_lines(payload: Mapping[str, Any]) -> list[str]:
    if not payload:
        return []
    lines = ["Extraction mecanique:"]
    status = _text(payload.get("status")) or "unknown"
    lines.append(f"- statut: {status}")
    source_tool = _text(payload.get("source_tool_name"))
    if source_tool:
        lines.append(f"- outil source: {source_tool}")
    doc = _text(payload.get("doc_id_short")) or short_doc_id(_text(payload.get("document_id")))
    if doc:
        lines.append(f"- document: catalogue_doc={doc}")
    content_kind = _text(payload.get("content_kind"))
    if content_kind:
        lines.append(f"- type de texte: {content_kind}")
    anchor = _mapping(payload.get("anchor"))
    if anchor:
        parts = []
        for label, key in (("page", "page_no"), ("para", "para_no"), ("paragraph_id", "paragraph_id")):
            value = _int(anchor.get(key))
            if value:
                parts.append(f"{label}={value}")
        if parts:
            lines.append("- ancre technique: " + ", ".join(parts))
    if bool(payload.get("exact_text_present")):
        lines.append(f"- texte mecanique disponible: {_int(payload.get('exact_text_chars'))} caracteres")
    elif status == EXTRACTION_STATUS_NEEDS_CLARIFICATION:
        lines.append("- extraction bloquee: ancre ou texte mecanique insuffisant")
    elif status == EXTRACTION_STATUS_NOT_FOUND:
        lines.append("- aucun texte mecanique n'a ete extrait par les outils autorises")
    limits = _sequence(payload.get("limits"))
    if limits:
        lines.append("- limites: " + ", ".join(_text(item) for item in limits if _text(item)))
    return lines


def to_observability(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    anchor = _mapping(payload.get("anchor"))
    return _clean(
        {
            "family": _text(payload.get("family")),
            "status": _text(payload.get("status")),
            "source_tool_name": _text(payload.get("source_tool_name")),
            "doc_id_short": _text(payload.get("doc_id_short")) or short_doc_id(_text(payload.get("document_id"))),
            "content_kind": _text(payload.get("content_kind")),
            "exact_text_present": bool(payload.get("exact_text_present")),
            "exact_text_chars": _int(payload.get("exact_text_chars")),
            "exact_text_hash": _text(payload.get("exact_text_hash")),
            "anchor_present": bool(anchor),
            "anchor_page_no": _int(anchor.get("page_no")),
            "anchor_para_no": _int(anchor.get("para_no")),
            "anchor_paragraph_id": _int(anchor.get("paragraph_id")),
            "candidate_count": _int(payload.get("candidate_count")),
            "extraction_attempted": bool(payload.get("extraction_attempted")),
            "reason_codes": list(_unique(payload.get("reason_codes") or ())),
            "limits": list(_unique(payload.get("limits") or ())),
        }
    )


def _extraction_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    selected: Mapping[str, Any],
    extraction_attempted: bool,
    base_status: str,
) -> str:
    if any(result.status in {librarian_tools.STATUS_ERROR, librarian_tools.STATUS_INCOHERENT_CATALOGUE} for result in results):
        return EXTRACTION_STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return EXTRACTION_STATUS_AMBIGUOUS
    if selected:
        if _has_minimum_anchor(selected):
            return EXTRACTION_STATUS_RESOLVED
        return EXTRACTION_STATUS_NEEDS_CLARIFICATION
    if extraction_attempted:
        return EXTRACTION_STATUS_NOT_FOUND
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return EXTRACTION_STATUS_NOT_FOUND
    if base_status == ANSWER_STATUS_ERROR:
        return EXTRACTION_STATUS_ERROR
    return EXTRACTION_STATUS_NEEDS_CLARIFICATION


def _candidate_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> dict[str, Any]:
    if result.tool_name not in _MECHANICAL_TEXT_TOOLS:
        return {}
    text = _result_text(result)
    if not text:
        return {}
    document_id = _text(getattr(result, "document_id", ""))
    anchor = _result_anchor(result)
    content_kind = "page" if result.tool_name == librarian_tools.TOOL_PAGE_READ else "context"
    return _clean(
        {
            "source_tool_name": result.tool_name,
            "document_id": document_id,
            "doc_id_short": short_doc_id(document_id),
            "content_kind": content_kind,
            "exact_text_present": True,
            "exact_text_chars": len(text),
            "exact_text_hash": _hash(text),
            "anchor": anchor,
        }
    )


def _candidates_from_results(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
) -> tuple[dict[str, Any], ...]:
    candidates: list[dict[str, Any]] = []
    for result in results:
        candidate = _candidate_from_result(result)
        if candidate:
            candidates.append(candidate)
    return tuple(candidates)


def _result_text(result: librarian_tools.BiblioLibrarianToolResult, *, content_kind: str = "") -> str:
    kind = _text(content_kind)
    if kind == "page":
        return _text(result.page_text)
    if kind == "context":
        return _text(result.context_text)
    if result.tool_name == librarian_tools.TOOL_PAGE_READ:
        return _text(result.page_text)
    if result.tool_name == librarian_tools.TOOL_PASSAGE_CONTEXT:
        return _text(result.context_text)
    return ""


def _result_anchor(result: librarian_tools.BiblioLibrarianToolResult) -> dict[str, Any]:
    for position in result.positions:
        if isinstance(position, Mapping):
            anchor = {
                key: _int(position.get(key))
                for key in ("page_no", "para_no", "paragraph_id", "char_offset", "window_chars")
                if _int(position.get(key))
            }
            if anchor:
                return anchor
    return {}


def _has_result_anchor(result: librarian_tools.BiblioLibrarianToolResult) -> bool:
    return _has_minimum_anchor({"document_id": _text(getattr(result, "document_id", "")), "anchor": _result_anchor(result)})


def _has_minimum_anchor(candidate: Mapping[str, Any]) -> bool:
    if not _text(candidate.get("document_id")):
        return False
    anchor = _mapping(candidate.get("anchor"))
    return bool(_int(anchor.get("paragraph_id")) or _int(anchor.get("page_no")))


def _reason_codes(
    reason_codes: Sequence[str],
    *,
    status: str,
    selected: Mapping[str, Any],
    extraction_attempted: bool,
) -> tuple[str, ...]:
    values = list(_unique(reason_codes))
    if status == EXTRACTION_STATUS_NEEDS_CLARIFICATION:
        reason = (
            librarian_tools.REASON_EXTRACTION_ANCHOR_MISSING
            if selected
            else librarian_tools.REASON_EXTRACTION_SOURCE_TOOL_UNSUPPORTED
        )
        values.append(reason)
    elif status == EXTRACTION_STATUS_NOT_FOUND and extraction_attempted:
        values.append(librarian_tools.REASON_EXTRACTION_MECHANICAL_TEXT_MISSING)
    return _unique(values)


def _limits(selected: Mapping[str, Any], *, extraction_attempted: bool) -> tuple[str, ...]:
    values: list[str] = []
    if selected and not _has_minimum_anchor(selected):
        values.append("exact_text_blocked_without_technical_anchor")
    if not selected and not extraction_attempted:
        values.append("no_mechanical_extraction_tool_result")
    return tuple(values)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


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


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _clean(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in ("", None, [], {}, ())}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""
