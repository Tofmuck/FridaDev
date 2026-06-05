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
        librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT,
    }
)
_MECHANICAL_TEXT_PROJECTION_METHODS = frozenset(
    {
        product_methods.PRODUCT_METHOD_EXTRACTION,
        product_methods.PRODUCT_METHOD_PASSAGE_ORIGIN_CHECK,
        product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
    }
)
_MAX_PAGE_BLOCKS = 3
_MAX_EXACT_TEXT_CHARS = 8_000


def build_extraction(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
    base_status: str,
    reason_codes: Sequence[str] = (),
) -> dict[str, Any]:
    if product_method not in _MECHANICAL_TEXT_PROJECTION_METHODS:
        return {}
    candidates = _candidates_from_results(results, product_method=product_method)
    extraction_attempted = any(_is_allowed_text_tool(result.tool_name, product_method) for result in results)
    projection = _project_blocks(candidates, extraction_attempted=extraction_attempted)
    status = _extraction_status(
        results,
        projection=projection,
        extraction_attempted=extraction_attempted,
        base_status=base_status,
    )
    return _clean(
        {
            "family": product_methods.CANONICAL_FAMILY_EXTRACTION,
            "status": status,
            "source_tool_name": _text(projection.get("source_tool_name")),
            "document_id": _text(projection.get("document_id")),
            "doc_id_short": _text(projection.get("doc_id_short")),
            "content_kind": _text(projection.get("content_kind")),
            "exact_text_present": (
                bool(projection.get("exact_text_present"))
                and _has_minimum_anchor(projection)
                and not _text(projection.get("blocking_reason"))
            ),
            "exact_text_chars": _int(projection.get("exact_text_chars")),
            "exact_text_hash": _text(projection.get("exact_text_hash")),
            "anchor": _mapping(projection.get("anchor")),
            "blocks": list(_sequence(projection.get("blocks"))),
            "block_count": _int(projection.get("block_count")),
            "page_start": _int(projection.get("page_start")),
            "page_end": _int(projection.get("page_end")),
            "page_count": _int(projection.get("page_count")),
            "missing_pages": list(_sequence(projection.get("missing_pages"))),
            "candidate_count": len(candidates),
            "extraction_attempted": extraction_attempted,
            "reason_codes": list(
                _reason_codes(
                    reason_codes,
                    status=status,
                    projection=projection,
                    extraction_attempted=extraction_attempted,
                )
            ),
            "limits": list(_limits(projection, extraction_attempted=extraction_attempted)),
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
    chunks: list[str] = []
    for block in _sequence(payload.get("blocks")):
        if not isinstance(block, Mapping):
            return ""
        text = _text_for_block(results, block)
        if not text:
            return ""
        chunks.append(text)
    return "\n\n".join(chunks)


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
    block_count = _int(payload.get("block_count"))
    if block_count:
        lines.append(f"- blocs mecaniques: {block_count}")
    page_start = _int(payload.get("page_start"))
    page_end = _int(payload.get("page_end"))
    if page_start and page_end:
        if page_start == page_end:
            lines.append(f"- page lue: {page_start}")
        else:
            lines.append(f"- intervalle pages lu: {page_start}-{page_end}")
    if status == EXTRACTION_STATUS_RESOLVED:
        chapter_no = _int(payload.get("chapter_no"))
        if chapter_no:
            lines.append(f"- section/chapitre: chapter_no={chapter_no}")
        else:
            lines.append("- section/chapitre: inconnu ou indisponible")
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
            "block_count": _int(payload.get("block_count")),
            "page_start": _int(payload.get("page_start")),
            "page_end": _int(payload.get("page_end")),
            "page_count": _int(payload.get("page_count")),
            "block_hashes": [
                _text(block.get("exact_text_hash"))
                for block in _sequence(payload.get("blocks"))
                if isinstance(block, Mapping) and _text(block.get("exact_text_hash"))
            ],
            "missing_pages": [
                _int(page)
                for page in _sequence(payload.get("missing_pages"))
                if _int(page)
            ],
            "candidate_count": _int(payload.get("candidate_count")),
            "extraction_attempted": bool(payload.get("extraction_attempted")),
            "reason_codes": list(_unique(payload.get("reason_codes") or ())),
            "limits": list(_unique(payload.get("limits") or ())),
        }
    )


def _extraction_status(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    projection: Mapping[str, Any],
    extraction_attempted: bool,
    base_status: str,
) -> str:
    if projection:
        if not _text(projection.get("blocking_reason")) and _has_minimum_anchor(projection):
            return EXTRACTION_STATUS_RESOLVED
        return EXTRACTION_STATUS_NEEDS_CLARIFICATION
    if any(result.status in {librarian_tools.STATUS_ERROR, librarian_tools.STATUS_INCOHERENT_CATALOGUE} for result in results):
        return EXTRACTION_STATUS_ERROR
    if any(result.status == librarian_tools.STATUS_AMBIGUOUS for result in results):
        return EXTRACTION_STATUS_AMBIGUOUS
    if extraction_attempted:
        return EXTRACTION_STATUS_NOT_FOUND
    if any(result.status == librarian_tools.STATUS_NOT_FOUND for result in results):
        return EXTRACTION_STATUS_NOT_FOUND
    if base_status == ANSWER_STATUS_ERROR:
        return EXTRACTION_STATUS_ERROR
    return EXTRACTION_STATUS_NEEDS_CLARIFICATION


def _candidate_from_result(
    result: librarian_tools.BiblioLibrarianToolResult,
    *,
    product_method: str,
) -> dict[str, Any]:
    if not _is_allowed_text_tool(result.tool_name, product_method):
        return {}
    text = _result_text(result)
    if not text:
        return {}
    document_id = _text(getattr(result, "document_id", ""))
    anchor = _result_anchor(result)
    if result.tool_name == librarian_tools.TOOL_PAGE_READ:
        content_kind = "page"
    elif result.tool_name == librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT:
        content_kind = "canonical_range"
    else:
        content_kind = "context"
    interval = _mapping(getattr(result, "interval", {}))
    return _clean_candidate(
        {
            "source_tool_name": result.tool_name,
            "document_id": document_id,
            "doc_id_short": short_doc_id(document_id),
            "content_kind": content_kind,
            "chapter_no": _int(result.chapter_hint.get("chapter_no")),
            "page_start": _int(interval.get("start_page_no")),
            "page_end": _int(interval.get("end_page_no")),
            "page_count": _int(interval.get("page_span")),
            "exact_text_present": True,
            "exact_text_chars": len(text),
            "exact_text_hash": _hash(text),
            "anchor": anchor,
            "anchor_end": _interval_anchor(interval, "end"),
            "_exact_text": text,
        }
    )


def _candidates_from_results(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    *,
    product_method: str,
) -> tuple[dict[str, Any], ...]:
    candidates: list[dict[str, Any]] = []
    for result in results:
        candidate = _candidate_from_result(result, product_method=product_method)
        if candidate:
            candidates.append(candidate)
    return tuple(candidates)


def _is_allowed_text_tool(tool_name: str, product_method: str) -> bool:
    if product_method == product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE:
        return tool_name == librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT
    return tool_name in _MECHANICAL_TEXT_TOOLS


def _project_blocks(candidates: Sequence[Mapping[str, Any]], *, extraction_attempted: bool) -> dict[str, Any]:
    valid_blocks = tuple(candidate for candidate in candidates if _has_minimum_anchor(candidate))
    if not valid_blocks:
        selected = candidates[0] if candidates else {}
        if selected:
            return {
                **dict(selected),
                "blocks": (_public_block(selected),),
                "block_count": 1,
                "blocking_reason": librarian_tools.REASON_EXTRACTION_ANCHOR_MISSING,
            }
        return {}
    documents = _unique(block.get("document_id") for block in valid_blocks)
    if len(documents) > 1:
        selected = dict(valid_blocks[0])
        return {
            **selected,
            "blocks": tuple(_public_block(block) for block in valid_blocks),
            "block_count": len(valid_blocks),
            "blocking_reason": librarian_tools.REASON_EXTRACTION_DOCUMENT_MISMATCH,
        }
    kinds = _unique(block.get("content_kind") for block in valid_blocks)
    if len(kinds) > 1:
        selected = dict(valid_blocks[0])
        return {
            **selected,
            "blocks": tuple(_public_block(block) for block in valid_blocks),
            "block_count": len(valid_blocks),
            "blocking_reason": librarian_tools.REASON_EXTRACTION_MIXED_BLOCK_TYPES,
        }
    kind = kinds[0] if kinds else ""
    if kind == "page":
        return _project_page_blocks(valid_blocks)
    if len(valid_blocks) > 1:
        selected = dict(valid_blocks[0])
        return {
            **selected,
            "blocks": tuple(_public_block(block) for block in valid_blocks),
            "block_count": len(valid_blocks),
            "blocking_reason": librarian_tools.REASON_EXTRACTION_MIXED_BLOCK_TYPES,
        }
    return _project_single_block(valid_blocks[0], extraction_attempted=extraction_attempted)


def _project_page_blocks(blocks: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    by_page: dict[int, Mapping[str, Any]] = {}
    for block in blocks:
        page_no = _int(_mapping(block.get("anchor")).get("page_no"))
        if not page_no:
            return {
                **dict(block),
                "blocks": tuple(_public_block(item) for item in blocks),
                "block_count": len(blocks),
                "blocking_reason": librarian_tools.REASON_EXTRACTION_ANCHOR_MISSING,
            }
        by_page.setdefault(page_no, block)
    ordered_pages = tuple(sorted(by_page))
    ordered_source_blocks = tuple(by_page[page] for page in ordered_pages)
    ordered_blocks = tuple(_public_block(block) for block in ordered_source_blocks)
    selected = dict(ordered_blocks[0]) if ordered_blocks else {}
    if len(ordered_pages) > _MAX_PAGE_BLOCKS:
        return {
            **selected,
            "content_kind": "page_range",
            "blocks": ordered_blocks,
            "block_count": len(ordered_blocks),
            "page_start": ordered_pages[0],
            "page_end": ordered_pages[-1],
            "page_count": len(ordered_pages),
            "blocking_reason": librarian_tools.REASON_EXTRACTION_PAGE_RANGE_TOO_LONG,
        }
    expected_pages = tuple(range(ordered_pages[0], ordered_pages[-1] + 1)) if ordered_pages else ()
    missing_pages = tuple(page for page in expected_pages if page not in by_page)
    if missing_pages:
        return {
            **selected,
            "content_kind": "page_range" if len(ordered_blocks) > 1 else "page",
            "blocks": ordered_blocks,
            "block_count": len(ordered_blocks),
            "page_start": ordered_pages[0],
            "page_end": ordered_pages[-1],
            "page_count": len(ordered_pages),
            "missing_pages": missing_pages,
            "blocking_reason": librarian_tools.REASON_EXTRACTION_PAGE_RANGE_INCOMPLETE,
        }
    combined_text = "\n\n".join(_text(block.get("_exact_text")) for block in ordered_source_blocks)
    content_kind = "page_range" if len(ordered_blocks) > 1 else "page"
    if len(combined_text) > _MAX_EXACT_TEXT_CHARS:
        return {
            **selected,
            "content_kind": content_kind,
            "blocks": ordered_blocks,
            "block_count": len(ordered_blocks),
            "page_start": ordered_pages[0],
            "page_end": ordered_pages[-1],
            "page_count": len(ordered_pages),
            "blocking_reason": librarian_tools.REASON_BUDGET_OR_LIMIT_EXCEEDED,
        }
    return _clean(
        {
            **selected,
            "content_kind": content_kind,
            "exact_text_chars": len(combined_text),
            "exact_text_hash": _hash(combined_text),
            "blocks": ordered_blocks,
            "block_count": len(ordered_blocks),
            "page_start": ordered_pages[0],
            "page_end": ordered_pages[-1],
            "page_count": len(ordered_pages),
            "anchor": _mapping(selected.get("anchor")),
        }
    )


def _project_single_block(block: Mapping[str, Any], *, extraction_attempted: bool) -> dict[str, Any]:
    text = _text(block.get("_exact_text"))
    if len(text) > _MAX_EXACT_TEXT_CHARS:
        return {
            **dict(block),
            "blocks": (_public_block(block),),
            "block_count": 1,
            "blocking_reason": librarian_tools.REASON_BUDGET_OR_LIMIT_EXCEEDED,
        }
    return _clean(
        {
            **dict(block),
            "blocks": (_public_block(block),),
            "block_count": 1,
            "extraction_attempted": extraction_attempted,
        }
    )


def _public_block(block: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in dict(block).items() if not str(key).startswith("_")}


def _result_text(result: librarian_tools.BiblioLibrarianToolResult, *, content_kind: str = "") -> str:
    kind = _text(content_kind)
    if kind == "page_range":
        kind = "page"
    if kind == "page":
        return _text(result.page_text)
    if kind == "context":
        return _text(result.context_text)
    if kind == "canonical_range":
        return _text(result.context_text)
    if result.tool_name == librarian_tools.TOOL_PAGE_READ:
        return _text(result.page_text)
    if result.tool_name == librarian_tools.TOOL_PASSAGE_CONTEXT:
        return _text(result.context_text)
    if result.tool_name == librarian_tools.TOOL_CANONICAL_RANGE_EXTRACT:
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


def _interval_anchor(interval: Mapping[str, Any], prefix: str) -> dict[str, Any]:
    anchor = {
        "page_no": _int(interval.get(f"{prefix}_page_no")),
        "para_no": _int(interval.get(f"{prefix}_para_no")),
        "paragraph_id": _int(interval.get(f"{prefix}_paragraph_id")),
    }
    return {key: value for key, value in anchor.items() if value}


def _has_result_anchor(result: librarian_tools.BiblioLibrarianToolResult) -> bool:
    return _has_minimum_anchor({"document_id": _text(getattr(result, "document_id", "")), "anchor": _result_anchor(result)})


def _has_minimum_anchor(candidate: Mapping[str, Any]) -> bool:
    if not _text(candidate.get("document_id")):
        return False
    anchor = _mapping(candidate.get("anchor"))
    return bool(_int(anchor.get("paragraph_id")) or _int(anchor.get("page_no")))


def _text_for_block(
    results: Sequence[librarian_tools.BiblioLibrarianToolResult],
    block: Mapping[str, Any],
) -> str:
    source_tool_name = _text(block.get("source_tool_name"))
    document_id = _text(block.get("document_id"))
    content_kind = _text(block.get("content_kind"))
    anchor = _mapping(block.get("anchor"))
    expected_hash = _text(block.get("exact_text_hash"))
    for result in results:
        if result.tool_name != source_tool_name:
            continue
        if _text(getattr(result, "document_id", "")) != document_id:
            continue
        if not _same_anchor(anchor, _result_anchor(result)):
            continue
        text = _result_text(result, content_kind=content_kind)
        if text and _hash(text) == expected_hash:
            return text
    return ""


def _same_anchor(expected: Mapping[str, Any], observed: Mapping[str, Any]) -> bool:
    if not expected or not observed:
        return False
    for key in ("page_no", "para_no", "paragraph_id"):
        value = _int(expected.get(key))
        if value and value != _int(observed.get(key)):
            return False
    return True


def _reason_codes(
    reason_codes: Sequence[str],
    *,
    status: str,
    projection: Mapping[str, Any],
    extraction_attempted: bool,
) -> tuple[str, ...]:
    values = list(_unique(reason_codes))
    blocking_reason = _text(projection.get("blocking_reason"))
    if blocking_reason:
        values.append(blocking_reason)
    if status == EXTRACTION_STATUS_NEEDS_CLARIFICATION:
        if not blocking_reason:
            reason = (
                librarian_tools.REASON_EXTRACTION_ANCHOR_MISSING
                if projection
                else librarian_tools.REASON_EXTRACTION_SOURCE_TOOL_UNSUPPORTED
            )
            values.append(reason)
    elif status == EXTRACTION_STATUS_NOT_FOUND and extraction_attempted:
        values.append(librarian_tools.REASON_EXTRACTION_MECHANICAL_TEXT_MISSING)
    return _unique(values)


def _limits(projection: Mapping[str, Any], *, extraction_attempted: bool) -> tuple[str, ...]:
    values: list[str] = []
    blocking_reason = _text(projection.get("blocking_reason"))
    if projection and not _has_minimum_anchor(projection):
        values.append("exact_text_blocked_without_technical_anchor")
    if blocking_reason == librarian_tools.REASON_EXTRACTION_PAGE_RANGE_TOO_LONG:
        values.append(f"max_page_blocks={_MAX_PAGE_BLOCKS}")
    if blocking_reason == librarian_tools.REASON_BUDGET_OR_LIMIT_EXCEEDED:
        values.append(f"max_exact_text_chars={_MAX_EXACT_TEXT_CHARS}")
    if not projection and not extraction_attempted:
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
    return {key: value for key, value in data.items() if not key.startswith("_") and value not in ("", None, [], {}, ())}


def _clean_candidate(data: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in data.items() if value not in ("", None, [], {}, ())}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""
