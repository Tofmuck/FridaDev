"""Scoped search projection for Biblio answer objects.

This module projects already executed GET-only results into a bounded search
surface. It filters technically by an explicit or carried document scope. It
does not decide which hit is intellectually the right passage, and it does not
turn search hits into exact extraction.
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

SEARCH_STATUS_RESOLVED = "resolved"
SEARCH_STATUS_AMBIGUOUS = "ambiguous"
SEARCH_STATUS_NOT_FOUND = "not_found"
SEARCH_STATUS_NEEDS_CLARIFICATION = "needs_clarification"
SEARCH_STATUS_ERROR = "error"
REASON_SCOPED_SEARCH_SECTION_BOUNDS_MISSING = "scoped_search_section_bounds_missing"


def build_scoped_search(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    base_status: str,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    if product_methods.canonical_family_for_method(product_method) != product_methods.CANONICAL_FAMILY_SCOPED_SEARCH:
        return {}
    scope_candidates = _dedupe_scopes(_scope for result in results for _scope in _scope_candidates_from_result(result))
    scope_doc_id = _unique_scope_document_id(scope_candidates)
    section_scope = _unique_section_scope(scope_candidates)
    raw_hits = _dedupe_hits(_hit for result in results for _hit in _search_hits_from_result(result))
    scoped_hits = tuple(
        hit
        for hit in raw_hits
        if scope_doc_id
        and _text(hit.get("document_id")) == scope_doc_id
        and _hit_in_section_scope(hit, section_scope)
    )
    search_attempted = _catalog_search_attempted(results)
    status = _search_status(
        results,
        scope_candidates=scope_candidates,
        scope_doc_id=scope_doc_id,
        section_scope=section_scope,
        raw_hits=raw_hits,
        scoped_hits=scoped_hits,
        search_attempted=search_attempted,
        base_status=base_status,
        reason_codes=reason_codes,
    )
    effective_reason_codes = list(_unique(reason_codes))
    if status == SEARCH_STATUS_NEEDS_CLARIFICATION and not scope_doc_id:
        effective_reason_codes = list(_unique((*effective_reason_codes, librarian_tools.REASON_SCOPED_SEARCH_SCOPE_MISSING)))
    if status == SEARCH_STATUS_NOT_FOUND and (raw_hits or search_attempted):
        effective_reason_codes = list(_unique((*effective_reason_codes, librarian_tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE)))
    if section_scope and not _section_scope_has_bounds(section_scope):
        effective_reason_codes = list(_unique((*effective_reason_codes, REASON_SCOPED_SEARCH_SECTION_BOUNDS_MISSING)))
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_SCOPED_SEARCH,
            "status": status,
            "scope_document_id": scope_doc_id,
            "scope_doc_id_short": short_doc_id(scope_doc_id),
            "section_scope_id": _text(section_scope.get("section_id")) if section_scope else "",
            "section_scope_kind": _text(section_scope.get("section_kind")) if section_scope else "",
            "section_scope_level": _int(section_scope.get("level")) if section_scope else 0,
            "section_scope_unit_start": _int(section_scope.get("unit_start")) if section_scope else 0,
            "section_scope_unit_end": _int(section_scope.get("unit_end")) if section_scope else 0,
            "scope_count": len(scope_candidates),
            "candidate_count": len(scoped_hits),
            "raw_candidate_count": len(raw_hits),
            "filtered_out_count": max(len(raw_hits) - len(scoped_hits), 0),
            "search_attempted": search_attempted,
            "scope_candidates": scope_candidates[:20],
            "candidates": scoped_hits[:20],
            "truncated": len(scope_candidates) > 20 or len(scoped_hits) > 20,
            "reason_codes": effective_reason_codes,
            "limits": list(
                _search_limits(
                    scope_candidates,
                    raw_hits,
                    scoped_hits,
                    search_attempted=search_attempted,
                    scope_doc_id=scope_doc_id,
                )
            ),
        }
    )


def override_answer_status(payload: Mapping[str, Any], *, base_status: str) -> str:
    if not payload:
        return base_status
    status = _text(payload.get("status"))
    if status == SEARCH_STATUS_RESOLVED:
        return ANSWER_STATUS_READY
    if status == SEARCH_STATUS_AMBIGUOUS:
        return ANSWER_STATUS_AMBIGUOUS
    if status == SEARCH_STATUS_NOT_FOUND:
        return ANSWER_STATUS_NOT_FOUND
    if status == SEARCH_STATUS_NEEDS_CLARIFICATION:
        return ANSWER_STATUS_NEEDS_CLARIFICATION
    if status == SEARCH_STATUS_ERROR:
        return ANSWER_STATUS_ERROR
    return base_status


def render_lines(payload: Mapping[str, Any]) -> list[str]:
    if not payload:
        return []
    lines = ["Recherche scoped:"]
    status = _text(payload.get("status")) or "unknown"
    lines.append(f"- statut: {status}")
    scope = _text(payload.get("scope_doc_id_short")) or short_doc_id(_text(payload.get("scope_document_id")))
    if scope:
        lines.append(f"- scope: catalogue_doc={scope}")
    lines.append(f"- candidats dans scope: {_int(payload.get('candidate_count'))}")
    raw_count = _int(payload.get("raw_candidate_count"))
    filtered = _int(payload.get("filtered_out_count"))
    if raw_count:
        lines.append(f"- candidats bruts controles: {raw_count}")
    if filtered:
        lines.append(f"- candidats hors scope filtres: {filtered}")
    if status == SEARCH_STATUS_AMBIGUOUS:
        lines.append("- ambiguite conservee: aucun scope documentaire n'est choisi par le renderer")
    elif status == SEARCH_STATUS_NEEDS_CLARIFICATION:
        reason_codes = set(_text(item) for item in _sequence(payload.get("reason_codes")))
        if REASON_SCOPED_SEARCH_SECTION_BOUNDS_MISSING in reason_codes:
            lines.append("- clarification requise: la section precise n'a pas de bornes techniques exploitables")
        else:
            lines.append("- clarification requise: la recherche scoped n'a pas de scope documentaire unique")
    elif status == SEARCH_STATUS_NOT_FOUND:
        lines.append("- aucun candidat de recherche ne reste dans le scope")

    candidates = _sequence(payload.get("candidates"))
    if candidates:
        lines.append("- candidats de recherche bornes:")
        for index, candidate in enumerate(candidates[:10], 1):
            if isinstance(candidate, Mapping):
                lines.append(f"  {index}. " + _candidate_line(candidate))
        if len(candidates) > 10:
            lines.append(f"  ... {len(candidates) - 10} candidats supplementaires masques par borne")
    elif status == SEARCH_STATUS_AMBIGUOUS:
        scopes = _sequence(payload.get("scope_candidates"))
        if scopes:
            lines.append("- scopes possibles:")
            for scope_candidate in scopes[:10]:
                if isinstance(scope_candidate, Mapping):
                    lines.append("  " + _scope_line(scope_candidate))

    limits = _sequence(payload.get("limits"))
    if limits:
        lines.append("- limites: " + ", ".join(_neutralize(_text(item)) for item in limits if _text(item)))
    if bool(payload.get("truncated")):
        lines.append("- resultat borne: candidats supplementaires masques")
    return lines


def to_observability(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not payload:
        return {}
    candidates = _sequence(payload.get("candidates"))
    scopes = _sequence(payload.get("scope_candidates"))
    return _clean(
        {
            "family": _text(payload.get("family")),
            "status": _text(payload.get("status")),
            "scope_doc_id_short": _text(payload.get("scope_doc_id_short"))
            or short_doc_id(_text(payload.get("scope_document_id"))),
            "section_scope_present": bool(_text(payload.get("section_scope_id"))),
            "section_scope_kind": _text(payload.get("section_scope_kind")),
            "section_scope_level": _int(payload.get("section_scope_level")),
            "section_scope_bounds_present": bool(
                _int(payload.get("section_scope_unit_start")) and _int(payload.get("section_scope_unit_end"))
            ),
            "scope_count": _int(payload.get("scope_count")),
            "candidate_count": _int(payload.get("candidate_count")),
            "raw_candidate_count": _int(payload.get("raw_candidate_count")),
            "filtered_out_count": _int(payload.get("filtered_out_count")),
            "search_attempted": bool(payload.get("search_attempted")),
            "candidate_doc_id_shorts": list(
                _unique(
                    _text(item.get("doc_id_short")) or short_doc_id(_text(item.get("document_id")))
                    for item in candidates
                    if isinstance(item, Mapping)
                )
            ),
            "scope_doc_id_shorts": list(
                _unique(
                    _text(item.get("doc_id_short")) or short_doc_id(_text(item.get("document_id")))
                    for item in scopes
                    if isinstance(item, Mapping)
                )
            ),
            "snippet_hashes": [_hash(_text(item.get("snippet"))) for item in candidates if isinstance(item, Mapping) and _text(item.get("snippet"))],
            "snippet_char_counts": [_text_len(item.get("snippet")) for item in candidates if isinstance(item, Mapping) and _text(item.get("snippet"))],
            "title_hashes": [_hash(_text(item.get("title"))) for item in candidates if isinstance(item, Mapping) and _text(item.get("title"))],
            "position_count": sum(1 for item in candidates if isinstance(item, Mapping) and _has_position(item)),
            "reason_codes": list(_unique(payload.get("reason_codes") or ())),
            "limits": list(_unique(payload.get("limits") or ())),
            "truncated": bool(payload.get("truncated")),
        }
    )


def _search_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    scope_candidates: Sequence[Mapping[str, Any]],
    scope_doc_id: str,
    section_scope: Mapping[str, Any],
    raw_hits: Sequence[Mapping[str, Any]],
    scoped_hits: Sequence[Mapping[str, Any]],
    search_attempted: bool,
    base_status: str,
    reason_codes: Sequence[str],
) -> str:
    if any(result.status in {librarian_tools.STATUS_ERROR, librarian_tools.STATUS_INCOHERENT_CATALOGUE} for result in results):
        return SEARCH_STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return SEARCH_STATUS_AMBIGUOUS
    if len(_unique(_text(scope.get("document_id")) for scope in scope_candidates)) > 1:
        return SEARCH_STATUS_AMBIGUOUS
    if len(_unique(_text(scope.get("section_id")) for scope in scope_candidates if _text(scope.get("section_id")))) > 1:
        return SEARCH_STATUS_AMBIGUOUS
    if librarian_tools.REASON_SCOPED_SEARCH_SCOPE_MISSING in set(_text(reason) for reason in reason_codes):
        return SEARCH_STATUS_NEEDS_CLARIFICATION
    if section_scope and not _section_scope_has_bounds(section_scope):
        return SEARCH_STATUS_NEEDS_CLARIFICATION
    if raw_hits and not scope_doc_id:
        return SEARCH_STATUS_NEEDS_CLARIFICATION
    if scoped_hits:
        return SEARCH_STATUS_RESOLVED
    if search_attempted and scope_doc_id:
        return SEARCH_STATUS_NOT_FOUND
    if raw_hits:
        return SEARCH_STATUS_NOT_FOUND
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return SEARCH_STATUS_NOT_FOUND
    if base_status == ANSWER_STATUS_ERROR:
        return SEARCH_STATUS_ERROR
    return SEARCH_STATUS_NEEDS_CLARIFICATION


def _scope_candidates_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    if result.tool_name == librarian_tools.TOOL_CATALOG_SEARCH:
        if result.document_id:
            return (
                _clean(
                    {
                        "document_id": _text(result.document_id),
                        "doc_id_short": short_doc_id(_text(result.document_id)),
                        "scope_source": "catalog_search_document_id",
                    }
                ),
            )
        return ()
    values: list[dict[str, Any]] = []
    direct = _text(result.document_id)
    if direct:
        values.append({"document_id": direct, "doc_id_short": short_doc_id(direct), "scope_source": result.tool_name})
    if result.document_summary:
        candidate = _scope_from_mapping(result.document_summary, source=f"{result.tool_name}_summary")
        if candidate:
            values.append(candidate)
    for item in result.items:
        if isinstance(item, Mapping):
            candidate = _scope_from_mapping(item, source=result.tool_name)
            if candidate:
                values.append(candidate)
    return tuple(_clean(value) for value in values if value)


def _scope_from_mapping(raw: Mapping[str, Any], *, source: str) -> dict[str, Any]:
    doc_id = _text(raw.get("document_id"))
    if not doc_id:
        return {}
    return _clean(
        {
            "document_id": doc_id,
            "doc_id_short": _text(raw.get("doc_id_short")) or short_doc_id(doc_id),
            "candidate_type": _text(raw.get("candidate_type")),
            "work_id": _text(raw.get("work_id")),
            "section_id": _text(raw.get("section_id")),
            "title": _text(raw.get("title")),
            "section_kind": _text(raw.get("section_kind")),
            "level": _int(raw.get("level")),
            "unit_start": _int(raw.get("unit_start") or raw.get("page_start")),
            "unit_end": _int(raw.get("unit_end") or raw.get("page_end")),
            "scope_source": source,
            "limits": tuple(_text(item) for item in _sequence(raw.get("limits")) if _text(item)),
        }
    )


def _search_hits_from_result(result: librarian_tools.BiblioLibrarianToolResult) -> tuple[dict[str, Any], ...]:
    if result.tool_name != librarian_tools.TOOL_CATALOG_SEARCH:
        return ()
    hits = []
    for item in result.items:
        if not isinstance(item, Mapping):
            continue
        doc_id = _text(item.get("document_id"))
        if not doc_id:
            continue
        hits.append(
            _clean(
                {
                    "document_id": doc_id,
                    "doc_id_short": _text(item.get("doc_id_short")) or short_doc_id(doc_id),
                    "title": _text(item.get("title")),
                    "snippet": _bounded_text(item.get("snippet"), maximum=500),
                    "page_no": _int(item.get("page_no")),
                    "para_no": _int(item.get("para_no")),
                    "paragraph_id": _int(item.get("paragraph_id")),
                    "rank": _number(item.get("rank")),
                    "score": _number(item.get("score")),
                    "document_role_signal": _text(item.get("document_role_signal")),
                    "document_role_signal_source": _text(item.get("document_role_signal_source")),
                    "document_role_signal_strength": _text(item.get("document_role_signal_strength")),
                }
            )
        )
    return tuple(hits)


def _catalog_search_attempted(results: Sequence[librarian_tools.BiblioLibrarianToolResult]) -> bool:
    return any(result.tool_name == librarian_tools.TOOL_CATALOG_SEARCH for result in results)


def _unique_scope_document_id(scope_candidates: Sequence[Mapping[str, Any]]) -> str:
    ids = _unique(_text(scope.get("document_id")) for scope in scope_candidates)
    return ids[0] if len(ids) == 1 else ""


def _unique_section_scope(scope_candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    section_scopes = [scope for scope in scope_candidates if _text(scope.get("section_id"))]
    section_ids = _unique(_text(scope.get("section_id")) for scope in section_scopes)
    if len(section_ids) != 1:
        return {}
    for scope in section_scopes:
        if _text(scope.get("section_id")) == section_ids[0]:
            return dict(scope)
    return {}


def _section_scope_has_bounds(section_scope: Mapping[str, Any]) -> bool:
    if not section_scope:
        return False
    return bool(_int(section_scope.get("unit_start")) and _int(section_scope.get("unit_end")))


def _hit_in_section_scope(hit: Mapping[str, Any], section_scope: Mapping[str, Any]) -> bool:
    if not section_scope:
        return True
    start = _int(section_scope.get("unit_start"))
    end = _int(section_scope.get("unit_end"))
    if not start or not end:
        return False
    page_no = _int(hit.get("page_no"))
    if not page_no:
        return False
    return start <= page_no <= end


def _dedupe_scopes(scopes: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str]] = set()
    for scope in scopes:
        key = (_text(scope.get("document_id")), _text(scope.get("work_id")), _text(scope.get("section_id")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(scope))
    return tuple(deduped)


def _dedupe_hits(hits: Iterable[Mapping[str, Any]]) -> tuple[dict[str, Any], ...]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, int, int, int, str]] = set()
    for hit in hits:
        key = (
            _text(hit.get("document_id")),
            _int(hit.get("paragraph_id")),
            _int(hit.get("page_no")),
            _int(hit.get("para_no")),
            _hash(_text(hit.get("snippet"))),
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(dict(hit))
    return tuple(deduped)


def _candidate_line(candidate: Mapping[str, Any]) -> str:
    doc = _text(candidate.get("doc_id_short")) or short_doc_id(_text(candidate.get("document_id"))) or "unknown"
    parts = [f"catalogue_doc={doc}"]
    for label, key in (
        ("page", "page_no"),
        ("para", "para_no"),
        ("paragraph_id", "paragraph_id"),
        ("rank", "rank"),
        ("score", "score"),
        ("titre", "title"),
        ("snippet", "snippet"),
    ):
        value = _number(candidate.get(key)) if key in {"rank", "score"} else _text(candidate.get(key))
        if key in {"page_no", "para_no", "paragraph_id"}:
            value = str(_int(candidate.get(key)) or "")
        if value:
            parts.append(f"{label}={_neutralize(str(value))}")
    return "; ".join(parts)


def _scope_line(candidate: Mapping[str, Any]) -> str:
    doc = _text(candidate.get("doc_id_short")) or short_doc_id(_text(candidate.get("document_id"))) or "unknown"
    parts = [f"catalogue_doc={doc}"]
    for label, key in (("type", "candidate_type"), ("work", "work_id"), ("section", "section_id"), ("titre", "title")):
        value = _text(candidate.get(key))
        if value:
            parts.append(f"{label}={_neutralize(value)}")
    return "; ".join(parts)


def _search_limits(
    scope_candidates: Sequence[Mapping[str, Any]],
    raw_hits: Sequence[Mapping[str, Any]],
    scoped_hits: Sequence[Mapping[str, Any]],
    *,
    search_attempted: bool,
    scope_doc_id: str,
) -> tuple[str, ...]:
    values: list[str] = []
    if raw_hits and len(scoped_hits) < len(raw_hits):
        values.append("global_hits_filtered_by_document_scope")
    if search_attempted and scope_doc_id and not scoped_hits:
        values.append("zero_hits_in_document_scope")
    if len(scope_candidates) > 1:
        values.append("scope_ambiguous")
    for scope in scope_candidates:
        for item in _sequence(scope.get("limits")):
            value = _text(item)
            if value and value not in values:
                values.append(value)
    return tuple(values)


def _has_position(candidate: Mapping[str, Any]) -> bool:
    return bool(_int(candidate.get("paragraph_id")) or (_int(candidate.get("page_no")) and _int(candidate.get("para_no"))))


def _bounded_text(value: Any, *, maximum: int) -> str:
    text = _text(value)
    if len(text) <= maximum:
        return text
    return text[:maximum].rstrip() + " [snippet borne]"


def _sequence(value: Any) -> tuple[Any, ...]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(value)
    return ()


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


def _text_len(value: Any) -> int:
    return len(_text(value))


def _int(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _number(value: Any) -> str:
    if type(value) in {int, float}:
        return str(value)
    return ""
