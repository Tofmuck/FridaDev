"""Visible rendering and final-lock validation for Biblio answers.

This boundary receives an already built ``BiblioAnswerObject``. It formats the
user-visible answer and validates only the technical final-response contract;
it never plans, chooses candidates, executes tools, or calls Catalogue.
"""

from __future__ import annotations

from typing import Any, Mapping, Sequence

from . import answer_extraction
from . import answer_resolution
from . import answer_search
from . import answer_structure
from . import answer_surface
from . import librarian_product_methods as product_methods
from .answer_object import (
    ANSWER_FOOTER,
    ANSWER_HEADER,
    DEFAULT_MAX_RENDERED_EXACT_CHARS,
    BiblioAnswerObject,
    BiblioFinalResponseLock,
    BiblioRenderedAnswer,
    REASON_FINAL_RESPONSE_ANCHOR_MISSING,
    REASON_FINAL_RESPONSE_AUTHORIZED,
    REASON_FINAL_RESPONSE_BLOCKED_CONTRACT_FAILED,
    REASON_FINAL_RESPONSE_EMPTY_CONTENT,
    REASON_FINAL_RESPONSE_EXACT_CONTRACT_FAILED,
    REASON_FINAL_RESPONSE_INVALID_STATUS,
    REASON_FINAL_RESPONSE_MISSING_ANSWER,
    REASON_FINAL_RESPONSE_MISSING_RENDERED,
    REASON_FINAL_RESPONSE_RENDER_MODE_MISMATCH,
    REASON_FINAL_RESPONSE_STATUS_MISMATCH,
    RENDER_BLOCKED_EXACT,
    RENDER_EXACT_EXCERPT,
    STATUS_AMBIGUOUS,
    STATUS_ERROR,
    STATUS_NEEDS_CLARIFICATION,
    STATUS_NOT_FOUND,
    STATUS_READY,
    _KNOWN_STATUSES,
    _RENDER_LOW_PRIORITY_REASONS,
    _extraction_block_anchors,
    _hash,
    _int,
    _text,
    _unique,
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
