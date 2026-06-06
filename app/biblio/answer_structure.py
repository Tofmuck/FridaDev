"""Document structure / TOC projection for Biblio answer objects.

The structure renderer reports TOC, chapter and section structure already
returned by GET-only tools. It does not interpret the user's wording, choose an
ambiguous document, or turn structural rows into primary-text extraction.
"""

from __future__ import annotations

import hashlib
from typing import Any, Iterable, Mapping, Sequence

from . import librarian_product_methods as product_methods
from . import librarian_tools
from .catalogue_client import short_doc_id


ANSWER_STATUS_READY = "ready"
ANSWER_STATUS_AMBIGUOUS = "ambiguous"
ANSWER_STATUS_NOT_FOUND = "not_found"
ANSWER_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
ANSWER_STATUS_ERROR = "error"

STRUCTURE_STATUS_RESOLVED = "resolved"
STRUCTURE_STATUS_AMBIGUOUS = "ambiguous"
STRUCTURE_STATUS_NOT_FOUND = "not_found"
STRUCTURE_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
STRUCTURE_STATUS_ERROR = "error"

_STRUCTURAL_CLARIFICATION_REASONS = frozenset(
    {
        librarian_tools.REASON_SECTION_ALIAS_MISSING,
        librarian_tools.REASON_INTERNAL_WORK_UNRESOLVED,
        librarian_tools.REASON_SECTION_BOUNDS_UNAVAILABLE,
    }
)

_ROLE_SIGNAL_TO_CONTENT_ROLE = {
    "commentary": "commentary",
    "introduction": "introduction",
    "notice": "notice",
}


def build_document_structure(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    base_status: str,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    if product_methods.canonical_family_for_method(product_method) != product_methods.CANONICAL_FAMILY_DOCUMENT_STRUCTURE:
        return {}
    chapters = _dedupe_chapters(_chapter for result in results for _chapter in _chapters_from_result(result))
    sections = _dedupe_sections(_section for result in results for _section in _sections_from_result(result))
    document_candidates = _dedupe_candidates(
        _candidate for result in results for _candidate in _document_candidates_from_result(result)
    )
    interval = _last_interval(results)
    anchors = _last_anchors(results)
    status = _structure_status(
        results,
        chapters=chapters,
        sections=sections,
        document_candidates=document_candidates,
        base_status=base_status,
        reason_codes=reason_codes,
    )
    document_id = _unique_document_id(results, document_candidates, sections)
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_DOCUMENT_STRUCTURE,
            "status": status,
            "document_id": document_id,
            "doc_id_short": short_doc_id(document_id),
            "chapter_count": len(chapters),
            "section_count": len(sections),
            "candidate_count": len(document_candidates),
            "chapters": chapters[:100],
            "sections": sections[:50],
            "document_candidates": document_candidates[:20],
            "interval": interval,
            "anchor_count": len(anchors),
            "reason_codes": list(_unique(reason_codes)),
            "limits": list(_structure_limits(sections)),
            "truncated": len(chapters) > 100 or len(sections) > 50 or len(document_candidates) > 20,
        }
    )


def override_answer_status(payload: Mapping[str, Any], *, base_status: str) -> str:
    if not payload:
        return base_status
    status = _text(payload.get("status"))
    if status == STRUCTURE_STATUS_RESOLVED:
        return ANSWER_STATUS_READY
    if status == STRUCTURE_STATUS_AMBIGUOUS:
        return ANSWER_STATUS_AMBIGUOUS
    if status == STRUCTURE_STATUS_NOT_FOUND:
        return ANSWER_STATUS_NOT_FOUND
    if status == STRUCTURE_STATUS_NEEDS_CLARIFICATION:
        return ANSWER_STATUS_NEEDS_CLARIFICATION
    if status == STRUCTURE_STATUS_ERROR:
        return ANSWER_STATUS_ERROR
    return base_status


def render_lines(payload: Mapping[str, Any]) -> list[str]:
    if not payload:
        return []
    status = _text(payload.get("status")) or "unknown"
    lines = ["Structure du document:"]
    if status == STRUCTURE_STATUS_AMBIGUOUS:
        lines.append("Plusieurs documents ou sections restent possibles; precise lequel viser.")
    elif status == STRUCTURE_STATUS_NOT_FOUND:
        lines.append("Aucune structure documentaire exploitable n'a ete trouvee.")
    elif status == STRUCTURE_STATUS_NEEDS_CLARIFICATION:
        lines.append("La structure disponible ne suffit pas encore a fermer la demande.")

    chapters = _sequence(payload.get("chapters"))
    if chapters:
        lines.append("Table des matieres:")
        for chapter in chapters[:40]:
            if isinstance(chapter, Mapping):
                lines.append("  " + _chapter_line(chapter))
        if len(chapters) > 40:
            lines.append(f"  ... {len(chapters) - 40} entrees supplementaires masquees par borne")

    sections = _sequence(payload.get("sections"))
    if sections:
        lines.append("Sections reperees:")
        for section in sections[:20]:
            if isinstance(section, Mapping):
                lines.append("  " + _section_line(section))
        if len(sections) > 20:
            lines.append(f"  ... {len(sections) - 20} sections supplementaires masquees par borne")

    candidates = _sequence(payload.get("document_candidates"))
    if candidates and not chapters and not sections:
        lines.append("Candidats documentaires:")
        for candidate in candidates[:10]:
            if isinstance(candidate, Mapping):
                lines.append("  " + _candidate_line(candidate))

    interval = payload.get("interval")
    if isinstance(interval, Mapping) and interval:
        visible_interval = _interval_line(interval)
        if visible_interval:
            lines.append(visible_interval)
    limits = _sequence(payload.get("limits"))
    if limits:
        visible_limits = [_visible_limit(item) for item in limits if _visible_limit(item)]
        if visible_limits:
            lines.append("Limite: " + ", ".join(visible_limits))
    if bool(payload.get("truncated")):
        lines.append("Resultat borne: elements structurels supplementaires masques.")
    return lines


def to_observability(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    chapters = _sequence(payload.get("chapters"))
    sections = _sequence(payload.get("sections"))
    candidates = _sequence(payload.get("document_candidates"))
    return _clean(
        {
            "family": _text(payload.get("family")),
            "status": _text(payload.get("status")),
            "doc_id_short": _text(payload.get("doc_id_short")) or short_doc_id(_text(payload.get("document_id"))),
            "chapter_count": _int(payload.get("chapter_count")),
            "section_count": _int(payload.get("section_count")),
            "candidate_count": _int(payload.get("candidate_count")),
            "chapter_title_hashes": [_hash(_text(item.get("title"))) for item in chapters if isinstance(item, Mapping) and _text(item.get("title"))],
            "section_title_hashes": [_hash(_text(item.get("title"))) for item in sections if isinstance(item, Mapping) and _text(item.get("title"))],
            "candidate_title_hashes": [_hash(_text(item.get("title"))) for item in candidates if isinstance(item, Mapping) and _text(item.get("title"))],
            "section_content_role_counts": _counts(_text(item.get("content_role")) for item in sections if isinstance(item, Mapping)),
            "boundary_state_counts": _counts(_text(item.get("boundary_state")) for item in sections if isinstance(item, Mapping)),
            "candidate_doc_id_shorts": list(
                _unique(
                    _text(item.get("doc_id_short")) or short_doc_id(_text(item.get("document_id")))
                    for item in candidates
                    if isinstance(item, Mapping)
                )
            ),
            "interval_state": _text(_mapping(payload.get("interval")).get("state")),
            "interval_type": _text(_mapping(payload.get("interval")).get("type")),
            "anchor_count": _int(payload.get("anchor_count")),
            "reason_codes": list(_unique(payload.get("reason_codes") or ())),
            "limits": list(_unique(payload.get("limits") or ())),
            "truncated": bool(payload.get("truncated")),
        }
    )


def _structure_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    chapters: Sequence[Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]],
    document_candidates: Sequence[Mapping[str, Any]],
    base_status: str,
    reason_codes: Sequence[str],
) -> str:
    if any(result.status in {librarian_tools.STATUS_ERROR, librarian_tools.STATUS_INCOHERENT_CATALOGUE} for result in results):
        return STRUCTURE_STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return STRUCTURE_STATUS_AMBIGUOUS
    if len(document_candidates) > 1 and not chapters and not sections:
        return STRUCTURE_STATUS_AMBIGUOUS
    if chapters or sections:
        return STRUCTURE_STATUS_RESOLVED
    if any(reason in _STRUCTURAL_CLARIFICATION_REASONS for reason in reason_codes):
        return STRUCTURE_STATUS_NEEDS_CLARIFICATION
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return STRUCTURE_STATUS_NOT_FOUND
    if base_status == ANSWER_STATUS_ERROR:
        return STRUCTURE_STATUS_ERROR
    return STRUCTURE_STATUS_NOT_FOUND


def _chapters_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    chapters = []
    for chapter in result.chapters:
        if isinstance(chapter, Mapping):
            chapters.append(
                _clean(
                    {
                        "chapter_no": _int(chapter.get("chapter_no")),
                        "title": _text(chapter.get("title")),
                        "page_start": _int(chapter.get("page_start")),
                        "page_end": _int(chapter.get("page_end")),
                        "paragraph_start": _int(chapter.get("paragraph_start")),
                        "paragraph_end": _int(chapter.get("paragraph_end")),
                    }
                )
            )
    return tuple(chapters)


def _sections_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    sections = []
    for item in result.items:
        if not isinstance(item, Mapping):
            continue
        role_signal = _chapter_role_signal(item)
        if _text(item.get("candidate_type")) != "section" and not _text(item.get("section_id")) and not role_signal:
            continue
        sections.append(
            _clean(
                {
                    "document_id": _text(item.get("document_id")),
                    "doc_id_short": _text(item.get("doc_id_short")) or short_doc_id(_text(item.get("document_id"))),
                    "section_id": _text(item.get("section_id")),
                    "chapter_no": _int(item.get("chapter_no")),
                    "title": _text(item.get("title")),
                    "content_role": _text(item.get("content_role")) or _ROLE_SIGNAL_TO_CONTENT_ROLE.get(role_signal, ""),
                    "content_role_state": _text(item.get("content_role_state")) or ("derived" if role_signal else ""),
                    "content_role_confidence": _text(item.get("document_role_signal_strength")),
                    "content_role_source": _text(item.get("document_role_signal_source")),
                    "boundary_state": _text(item.get("boundary_state")),
                    "unit_start": _int(item.get("unit_start")),
                    "unit_end": _int(item.get("unit_end")),
                    "page_start": _int(item.get("page_start")),
                    "page_end": _int(item.get("page_end")),
                    "source": _text(item.get("source")),
                    "limits": tuple(_text(value) for value in _sequence(item.get("limits")) if _text(value)),
                }
            )
        )
    return tuple(sections)


def _document_candidates_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    values = []
    for item in result.items:
        if not isinstance(item, Mapping):
            continue
        if _text(item.get("candidate_type")) == "section" or _text(item.get("section_id")):
            continue
        candidate = _document_candidate(item)
        if candidate:
            values.append(candidate)
    if result.document_summary:
        candidate = _document_candidate(result.document_summary)
        if candidate:
            values.append(candidate)
    return tuple(values)


def _document_candidate(raw: Mapping[str, Any]) -> dict[str, Any]:
    doc_id = _text(raw.get("document_id"))
    doc_id_short = _text(raw.get("doc_id_short")) or short_doc_id(doc_id)
    if not (doc_id or doc_id_short):
        return {}
    return _clean(
        {
            "document_id": doc_id,
            "doc_id_short": doc_id_short,
            "candidate_type": _text(raw.get("candidate_type")) or "document",
            "title": _text(raw.get("title")),
            "authors": _text(raw.get("authors")),
            "metadata_status": _text(raw.get("metadata_status")),
        }
    )


def _last_interval(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> dict[str, Any]:
    for result in reversed(results):
        if result.interval:
            return dict(result.interval)
    return {}


def _last_anchors(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> tuple[dict[str, Any], ...]:
    for result in reversed(results):
        if result.anchors:
            return tuple(dict(anchor) for anchor in result.anchors)
    return ()


def _unique_document_id(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    candidates: Sequence[Mapping[str, Any]],
    sections: Sequence[Mapping[str, Any]],
) -> str:
    ids: list[str] = []
    for result in results:
        value = _text(getattr(result, "document_id", ""))
        if value and value not in ids:
            ids.append(value)
    for source in (*candidates, *sections):
        value = _text(source.get("document_id"))
        if value and value not in ids:
            ids.append(value)
    return ids[0] if len(ids) == 1 else ""


def _dedupe_chapters(chapters: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[int, str]] = set()
    for chapter in chapters:
        key = (_int(chapter.get("chapter_no")), _text(chapter.get("title")))
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(chapter))
    return tuple(out)


def _dedupe_sections(sections: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    seen: set[tuple[str, int, str]] = set()
    for section in sections:
        key = (
            _text(section.get("section_id")),
            _int(section.get("chapter_no")),
            _text(section.get("document_id")),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(dict(section))
    return tuple(out)


def _dedupe_candidates(candidates: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = _text(candidate.get("document_id")) or _text(candidate.get("doc_id_short"))
        if key in seen:
            continue
        if key:
            seen.add(key)
        out.append(dict(candidate))
    return tuple(out)


def _chapter_line(chapter: Mapping[str, Any]) -> str:
    parts = []
    number = _int(chapter.get("chapter_no"))
    label = "Chapitre" if number else "Entree"
    if number:
        label = f"Chapitre {number}"
    title = _text(chapter.get("title"))
    if title:
        label = f"{label}: {_neutralize(title)}"
    page_start = _int(chapter.get("page_start"))
    page_end = _int(chapter.get("page_end"))
    if page_start and page_end:
        parts.append(f"pages {page_start}-{page_end}" if page_start != page_end else f"page {page_start}")
    elif page_start:
        parts.append(f"commence page {page_start}")
    return label + (f" ({'; '.join(parts)})" if parts else "")


def _section_line(section: Mapping[str, Any]) -> str:
    label = _section_label(section)
    title = _text(section.get("title"))
    if title:
        label = f"{label}: {_neutralize(title)}"
    start = _int(section.get("unit_start") or section.get("page_start"))
    end = _int(section.get("unit_end") or section.get("page_end"))
    details = []
    if start and end:
        details.append(f"pages {start}-{end}" if start != end else f"page {start}")
    elif start:
        details.append(f"commence page {start}")
    boundary = _boundary_note(section.get("boundary_state"))
    if boundary:
        details.append(boundary)
    role = _role_note(section)
    if role:
        details.append(role)
    return label + (f" ({'; '.join(details)})" if details else "")


def _candidate_line(candidate: Mapping[str, Any]) -> str:
    title = _text(candidate.get("title"))
    parts = [_neutralize(title) if title else "Document du catalogue"]
    authors = _text(candidate.get("authors"))
    if authors:
        parts.append(f"auteur: {_neutralize(authors)}")
    return "; ".join(parts)


def _section_label(section: Mapping[str, Any]) -> str:
    kind = _text(section.get("section_kind"))
    level = _int(section.get("level"))
    if kind == "chapter" and level <= 1:
        number = _int(section.get("chapter_no"))
        return f"Chapitre {number}" if number else "Chapitre"
    if kind == "subsection" or level > 2:
        return "Sous-section"
    if kind == "section" or level == 2:
        return "Section interne"
    return "Section"


def _boundary_note(value: Any) -> str:
    state = _text(value)
    if state == "derived":
        return "fin derivee"
    if state == "known":
        return "borne connue"
    if state == "ambiguous":
        return "borne ambigue"
    return ""


def _role_note(section: Mapping[str, Any]) -> str:
    role = _text(section.get("content_role"))
    state = _text(section.get("content_role_state"))
    if role == "introduction":
        label = "role: introduction"
    elif role == "commentary":
        label = "role: commentaire"
    elif role == "notice":
        label = "role: notice"
    elif role == "preface":
        label = "role: preface"
    elif role == "note":
        label = "role: notes"
    elif role == "apparatus":
        label = "role: appareil critique"
    elif role == "primary_text":
        label = "role: texte principal"
    else:
        return ""
    if state == "derived":
        return f"{label}, derive"
    if state == "ambiguous":
        return f"{label}, ambigu"
    return label


def _interval_line(interval: Mapping[str, Any]) -> str:
    state = _text(interval.get("state"))
    if state == "derived":
        return "Bornes documentaires derivees."
    if state == "known":
        return "Bornes documentaires connues."
    if state == "ambiguous":
        return "Bornes documentaires ambigues."
    return ""


def _visible_limit(value: Any) -> str:
    text = _text(value)
    if text == "section_end_unknown":
        return "fin de section inconnue"
    if text == "chapter_level_not_internal_section":
        return "niveau chapitre, pas section interne distincte"
    return ""


def _structure_limits(sections: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    values: list[str] = []
    for section in sections:
        for item in _sequence(section.get("limits")):
            value = _text(item)
            if value and value not in values:
                values.append(value)
    return tuple(values)


def _chapter_role_signal(item: Mapping[str, Any]) -> str:
    signal = _text(item.get("document_role_signal"))
    return signal if signal in _ROLE_SIGNAL_TO_CONTENT_ROLE else ""


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


def _counts(values: Iterable[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return counts


def _unique(values: Iterable[Any]) -> tuple[str, ...]:
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


def _neutralize(value: str) -> str:
    return (
        value.replace("[RESULTAT BIBLIO STRUCTURE]", "[RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace("[/RESULTAT BIBLIO STRUCTURE]", "[/RESULTAT BIBLIO STRUCTURE neutralise]")
        .replace("[CONSULTATION DE BIBLIOTHEQUE]", "[CONSULTATION DE BIBLIOTHEQUE neutralise]")
        .replace("[/CONSULTATION DE BIBLIOTHEQUE]", "[/CONSULTATION DE BIBLIOTHEQUE neutralise]")
    )


def _clean(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in ("", None, [], {}, ())}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0
