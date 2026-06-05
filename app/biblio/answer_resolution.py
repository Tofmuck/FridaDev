"""Document resolution projection for Biblio answer objects.

This module is intentionally narrow: it projects already executed GET-only
tool results into a renderable document/work resolution status. It does not
choose between ambiguous candidates and does not parse user wording.
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

RESOLUTION_STATUS_RESOLVED = "resolved"
RESOLUTION_STATUS_AMBIGUOUS = "ambiguous"
RESOLUTION_STATUS_NOT_FOUND = "not_found"
RESOLUTION_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
RESOLUTION_STATUS_ERROR = "error"

_UNCONFIRMED_INTERNAL_WORK_LIMIT = "section_candidate_not_confirmed_internal_work"


def build_document_resolution(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    base_status: str,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    if product_methods.canonical_family_for_method(product_method) != product_methods.CANONICAL_FAMILY_DOCUMENT_RESOLUTION:
        return {}
    candidates = _dedupe_candidates(_candidate for result in results for _candidate in _result_candidates(result))
    status = _resolution_status(results, candidates, base_status=base_status)
    selected = candidates[0] if status == RESOLUTION_STATUS_RESOLVED and len(candidates) == 1 else {}
    if selected and _has_unconfirmed_internal_work_limit(selected):
        status = RESOLUTION_STATUS_NEEDS_CLARIFICATION
        selected = {}
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_DOCUMENT_RESOLUTION,
            "status": status,
            "candidate_count": len(candidates),
            "selected": selected,
            "candidates": candidates[:20],
            "truncated": len(candidates) > 20,
            "reason_codes": list(_unique(reason_codes)),
            "limits": list(_resolution_limits(candidates)),
        }
    )


def override_answer_status(payload: Mapping[str, Any], *, base_status: str) -> str:
    if not payload:
        return base_status
    status = _text(payload.get("status"))
    if status == RESOLUTION_STATUS_RESOLVED:
        return ANSWER_STATUS_READY
    if status == RESOLUTION_STATUS_AMBIGUOUS:
        return ANSWER_STATUS_AMBIGUOUS
    if status == RESOLUTION_STATUS_NOT_FOUND:
        return ANSWER_STATUS_NOT_FOUND
    if status == RESOLUTION_STATUS_NEEDS_CLARIFICATION:
        return ANSWER_STATUS_NEEDS_CLARIFICATION
    if status == RESOLUTION_STATUS_ERROR:
        return ANSWER_STATUS_ERROR
    return base_status


def render_lines(payload: Mapping[str, Any]) -> list[str]:
    if not payload:
        return []
    status = _text(payload.get("status")) or "unknown"
    lines: list[str]
    candidate_count = _int(payload.get("candidate_count"))
    selected = payload.get("selected")
    if isinstance(selected, Mapping) and selected:
        lines = ["Ouvrage trouve:"]
        lines.append("  " + _candidate_line(selected))
    elif status == RESOLUTION_STATUS_AMBIGUOUS:
        lines = ["Plusieurs ouvrages peuvent correspondre. Peux-tu preciser ?"]
        if candidate_count:
            lines.append(f"{candidate_count} possibilites sont disponibles.")
    elif status == RESOLUTION_STATUS_NOT_FOUND:
        lines = ["Aucun ouvrage correspondant n'a ete trouve."]
    elif status == RESOLUTION_STATUS_NEEDS_CLARIFICATION:
        lines = ["Il faut une precision supplementaire pour identifier l'ouvrage ou la section."]
    else:
        lines = ["Resolution documentaire en cours."]
    raw_candidates = payload.get("candidates")
    candidates = raw_candidates if isinstance(raw_candidates, Sequence) and not isinstance(raw_candidates, (str, bytes, bytearray)) else ()
    if candidates and not selected:
        lines.append("Candidats possibles:")
        for item in candidates[:10]:
            if isinstance(item, Mapping):
                lines.append("  " + _candidate_line(item))
    if bool(payload.get("truncated")):
        lines.append("D'autres candidats existent mais ne sont pas affiches ici.")
    limits = payload.get("limits")
    if isinstance(limits, Sequence) and not isinstance(limits, (str, bytes, bytearray)) and limits:
        visible_limits = [_visible_limit(item) for item in limits if _visible_limit(item)]
        if visible_limits:
            lines.append("Limite: " + ", ".join(visible_limits))
    return lines


def to_observability(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    candidates = _sequence(payload.get("candidates"))
    selected = payload.get("selected")
    selected_doc_id = _text(selected.get("document_id")) if isinstance(selected, Mapping) else ""
    return _clean(
        {
            "family": _text(payload.get("family")),
            "status": _text(payload.get("status")),
            "candidate_count": _int(payload.get("candidate_count")),
            "candidate_doc_id_shorts": list(
                _unique(_text(item.get("doc_id_short")) or short_doc_id(_text(item.get("document_id"))) for item in candidates)
            ),
            "candidate_type_counts": _counts(_text(item.get("candidate_type")) for item in candidates),
            "work_kind_counts": _counts(_text(item.get("work_kind")) for item in candidates),
            "selected_doc_id_short": short_doc_id(selected_doc_id),
            "selected_present": bool(selected_doc_id),
            "title_hashes": [_hash(_text(item.get("title"))) for item in candidates if _text(item.get("title"))],
            "author_hashes": [_hash(_text(item.get("authors"))) for item in candidates if _text(item.get("authors"))],
            "metadata_statuses": list(_unique(_text(item.get("metadata_status")) for item in candidates)),
            "reason_codes": list(_unique(payload.get("reason_codes") or ())),
            "limits": list(_unique(payload.get("limits") or ())),
            "truncated": bool(payload.get("truncated")),
        }
    )


def _resolution_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    candidates: Sequence[Mapping[str, Any]],
    *,
    base_status: str,
) -> str:
    if any(result.status in {librarian_tools.STATUS_ERROR, librarian_tools.STATUS_INCOHERENT_CATALOGUE} for result in results):
        return RESOLUTION_STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return RESOLUTION_STATUS_AMBIGUOUS
    if len(candidates) > 1:
        return RESOLUTION_STATUS_AMBIGUOUS
    if len(candidates) == 1:
        return RESOLUTION_STATUS_RESOLVED
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return RESOLUTION_STATUS_NOT_FOUND
    if base_status == ANSWER_STATUS_ERROR:
        return RESOLUTION_STATUS_ERROR
    return RESOLUTION_STATUS_NOT_FOUND


def _result_candidates(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    values: list[dict[str, Any]] = []
    for item in result.items:
        if isinstance(item, Mapping):
            candidate = _candidate_from_mapping(item)
            if candidate:
                values.append(candidate)
    if result.document_summary:
        candidate = _candidate_from_mapping(result.document_summary)
        if candidate:
            values.append(candidate)
    return tuple(values)


def _candidate_from_mapping(raw: Mapping[str, Any]) -> dict[str, Any]:
    doc_id = _text(raw.get("document_id"))
    doc_id_short = _text(raw.get("doc_id_short")) or short_doc_id(doc_id)
    work_id = _text(raw.get("work_id"))
    section_id = _text(raw.get("section_id"))
    if not (doc_id or doc_id_short or work_id or section_id):
        return {}
    return _clean(
        {
            "candidate_type": _text(raw.get("candidate_type")) or ("work" if work_id else "document"),
            "work_kind": _text(raw.get("work_kind")),
            "document_id": doc_id,
            "doc_id_short": doc_id_short,
            "work_id": work_id,
            "section_id": section_id,
            "title": _text(raw.get("title")),
            "authors": _text(raw.get("authors")),
            "metadata_status": _text(raw.get("metadata_status")),
            "content_role": _text(raw.get("content_role")),
            "content_role_state": _text(raw.get("content_role_state")),
            "limits": tuple(_text(item) for item in _sequence(raw.get("limits")) if _text(item)),
        }
    )


def _dedupe_candidates(candidates: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for candidate in candidates:
        key = (
            _text(candidate.get("document_id")) or _text(candidate.get("doc_id_short")),
            _text(candidate.get("work_id")),
            _text(candidate.get("section_id")),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(candidate))
    return tuple(deduped)


def _candidate_line(candidate: Mapping[str, Any]) -> str:
    title = _text(candidate.get("title"))
    parts = [_neutralize(title) if title else "Ouvrage du catalogue"]
    authors = _text(candidate.get("authors"))
    if authors:
        parts.append(f"auteur: {_neutralize(authors)}")
    metadata_status = _visible_metadata_status(candidate.get("metadata_status"))
    if metadata_status:
        parts.append(metadata_status)
    if _text(candidate.get("section_id")):
        parts.append("section ou oeuvre interne a confirmer")
    return "; ".join(parts)


def _visible_metadata_status(value: Any) -> str:
    text = _text(value)
    if text in {"validated", "known", "complete"}:
        return "metadonnees connues"
    if text in {"unknown", "missing"}:
        return "metadonnees incompletes"
    if text:
        return "metadonnees disponibles"
    return ""


def _resolution_limits(candidates: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    values: list[str] = []
    for candidate in candidates:
        for item in _sequence(candidate.get("limits")):
            value = _text(item)
            if value and value not in values:
                values.append(value)
    return tuple(values)


def _visible_limit(value: Any) -> str:
    text = _text(value)
    if text == _UNCONFIRMED_INTERNAL_WORK_LIMIT:
        return "la section doit etre confirmee avant d'etre traitee comme oeuvre interne"
    return ""


def _has_unconfirmed_internal_work_limit(candidate: Mapping[str, Any]) -> bool:
    return _UNCONFIRMED_INTERNAL_WORK_LIMIT in set(_text(item) for item in _sequence(candidate.get("limits")))


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
