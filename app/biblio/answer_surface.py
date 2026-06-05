"""User-visible Biblio answer surface helpers.

This module only formats already-authorized Biblio data for the assistant
message. It does not choose documents, sections, anchors, or relevance.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from .catalogue_client import short_doc_id


_ANSWER_HEADER = "[RESULTAT BIBLIO STRUCTURE]"
_ANSWER_FOOTER = "[/RESULTAT BIBLIO STRUCTURE]"


def exact_excerpt_lines(answer: Any, exact_text: str) -> list[str]:
    lines: list[str] = []
    source = _source_line(answer)
    if source:
        lines.append(source)
    limits = _limit_lines(answer)
    if limits:
        lines.extend(limits)
    if lines:
        lines.append("")
    lines.append(_neutralize(exact_text))
    return lines


def _source_line(answer: Any) -> str:
    parts: list[str] = []
    doc = _doc_id(answer)
    if doc:
        parts.append(f"catalogue_doc={doc}")
    page = _page_label(answer)
    if page:
        parts.append(page)
    anchor = _anchor_label(answer)
    if anchor:
        parts.append(anchor)
    section = _section_label(answer)
    if section:
        parts.append(section)
    elif doc:
        parts.append("section/chapitre non renseigne")
    return "Source: " + ", ".join(parts) + "." if parts else ""


def _doc_id(answer: Any) -> str:
    extraction = _mapping(getattr(answer, "extraction", {}))
    if extraction:
        doc = _text(extraction.get("doc_id_short")) or short_doc_id(_text(extraction.get("document_id")))
        if doc:
            return doc
    document_id = _text(getattr(answer, "document_id", ""))
    if document_id:
        return short_doc_id(document_id)
    for anchor in _sequence(getattr(answer, "anchors", ())):
        if not isinstance(anchor, Mapping):
            continue
        doc = _text(anchor.get("doc_id_short")) or short_doc_id(_text(anchor.get("document_id")))
        if doc:
            return doc
    return ""


def _page_label(answer: Any) -> str:
    extraction = _mapping(getattr(answer, "extraction", {}))
    if extraction:
        page_start = _int(extraction.get("page_start"))
        page_end = _int(extraction.get("page_end"))
        if page_start and page_end:
            if page_start == page_end:
                return f"page {page_start}"
            return f"pages {page_start}-{page_end}"
    page_values = [
        _int(anchor.get("page_no"))
        for anchor in _sequence(getattr(answer, "anchors", ()))
        if isinstance(anchor, Mapping) and _int(anchor.get("page_no"))
    ]
    page_values = sorted(set(page_values))
    if len(page_values) == 1:
        return f"page {page_values[0]}"
    if len(page_values) > 1:
        return f"pages {page_values[0]}-{page_values[-1]}"
    return ""


def _anchor_label(answer: Any) -> str:
    for anchor in _sequence(getattr(answer, "anchors", ())):
        if not isinstance(anchor, Mapping):
            continue
        paragraph_id = _int(anchor.get("paragraph_id"))
        if paragraph_id:
            return f"paragraph_id={paragraph_id}"
        para_no = _int(anchor.get("para_no"))
        if para_no:
            return f"para {para_no}"
    return ""


def _section_label(answer: Any) -> str:
    section_id = _text(getattr(answer, "section_id", ""))
    if section_id:
        return f"section={_neutralize(section_id)}"
    return ""


def _limit_lines(answer: Any) -> list[str]:
    limits = [_visible_limit(limit) for limit in _sequence(getattr(answer, "limits", ())) if _text(limit)]
    extraction = _mapping(getattr(answer, "extraction", {}))
    if not limits:
        limits = [_visible_limit(limit) for limit in _sequence(extraction.get("limits")) if _text(limit)]
    if not limits:
        return []
    return ["Limite: " + ", ".join(limits)]


def _visible_limit(value: Any) -> str:
    text = _text(value)
    if text == "canonical_range_segment_partial":
        return "plage canonique rendue par segment; la plage complete n'est pas entierement affichee"
    if text == "canonical_range_continuation_anchor_present":
        return "suite disponible depuis l'ancre de continuation"
    if text == "canonical_range_continuation_anchor_missing":
        return "suite non garantie: ancre de continuation absente"
    return _neutralize(text)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""


def _neutralize(value: str) -> str:
    return (
        value.replace(_ANSWER_HEADER, "[RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace(_ANSWER_FOOTER, "[/RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace("[CONSULTATION DE BIBLIOTHEQUE]", "[CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[/CONSULTATION DE BIBLIOTHEQUE]", "[/CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
        .replace("[/PASSAGES DE BIBLIOTHEQUE CONSULTES]", "[/PASSAGES DE BIBLIOTHEQUE CONSULTES neutralise]")
    )
