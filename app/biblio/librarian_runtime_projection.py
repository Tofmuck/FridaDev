"""Shared runtime projection helpers for Biblio execution surfaces.

This module owns the content-free projections that execution runtimes reuse:

- loop tool-result collection;
- client-observability projections;
- endpoint-observation projections;
- state-anchor derivation from executed tool results.
"""

from __future__ import annotations

import hashlib
from typing import Any, Sequence

from . import librarian_planner
from . import librarian_tools
from .catalogue_client import CatalogueEndpointObservation, short_doc_id


def loop_tool_results(
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None,
) -> tuple[librarian_tools.BiblioLibrarianToolResult, ...]:
    if loop_result is None:
        return ()
    return tuple(step.tool_result for step in loop_result.steps if step.tool_result is not None)


def loop_client_observability(
    loop_result: librarian_planner.BiblioLibrarianLoopResult | None,
) -> list[dict[str, Any]]:
    return [dict(result.to_observability()) for result in loop_tool_results(loop_result)]


def endpoint_client_observability(
    endpoint_observations: Sequence[CatalogueEndpointObservation],
) -> list[dict[str, Any]]:
    return [dict(observation.to_observability()) for observation in endpoint_observations]


def tool_result_endpoint_observations(
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
) -> tuple[CatalogueEndpointObservation, ...]:
    observations: list[CatalogueEndpointObservation] = []
    for result in tool_results:
        if result is None:
            continue
        observed = result.to_observability()
        observations.append(
            CatalogueEndpointObservation(
                endpoint_kind=result.endpoint_kind,
                status_code=_int(observed.get("status_code")),
                duration_ms=_int(observed.get("duration_ms")) or 0,
                result_count=_int(observed.get("result_count")),
                doc_id_short=_text(observed.get("doc_id_short")),
                content_chars=_int(observed.get("content_chars")) or 0,
                reason_code=result.reason_code,
            )
        )
    return tuple(observations)


def tool_results_document_ids(
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
) -> tuple[str, ...]:
    ids: list[str] = []
    for result in tool_results:
        if result is None:
            continue
        doc_id = _text(getattr(result, "document_id", ""))
        if not doc_id and result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
        if doc_id and doc_id not in ids:
            ids.append(doc_id)
    return tuple(ids)


def tool_results_doc_id_shorts(
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
) -> tuple[str, ...]:
    shorts: list[str] = []
    for doc_id in tool_results_document_ids(tool_results):
        short = short_doc_id(doc_id)
        if short and short not in shorts:
            shorts.append(short)
    return tuple(shorts)


def state_anchor_from_tool_results(
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
    *,
    status: str,
    reason_code: str | None = None,
    answer: Any = None,
) -> dict[str, Any]:
    answer_interval = _interval_hint_from_answer(answer)
    section_interval_doc_id, section_interval = _section_interval_hint_from_tool_results(tool_results)
    for result in reversed(tool_results):
        if result is None:
            continue
        doc_id = _text(getattr(result, "document_id", ""))
        if not doc_id and result.document_summary:
            doc_id = _text(result.document_summary.get("document_id"))
        if not doc_id:
            continue
        position = result.positions[0] if result.positions else {}
        observed = result.to_observability()
        anchor = {
            "status": status,
            "reason_code": reason_code or result.reason_code,
            "document_id": doc_id,
            "doc_id_short": _text(observed.get("doc_id_short")) or short_doc_id(doc_id),
            "page_no": _int(position.get("page_no")),
            "para_no": _int(position.get("para_no")),
            "paragraph_id": _int(position.get("paragraph_id")),
        }
        if answer_interval:
            anchor["interval_hint"] = answer_interval
        elif result.interval:
            anchor["interval_hint"] = _interval_hint_from_section_result(result) or dict(result.interval)
        elif section_interval and (not section_interval_doc_id or section_interval_doc_id == doc_id):
            anchor["interval_hint"] = section_interval
        if result.context_text:
            anchor["passage_hash"] = hashlib.sha256(result.context_text.encode("utf-8")).hexdigest()[:12]
            anchor["passage_chars"] = len(result.context_text)
        return {key: value for key, value in anchor.items() if value not in ("", None)}
    return {}


def _interval_hint_from_answer(answer: Any) -> dict[str, Any]:
    extraction = getattr(answer, "extraction", None)
    if not isinstance(extraction, dict) or not extraction:
        return {}
    content_kind = _text(extraction.get("content_kind"))
    if content_kind not in {"section_complete", "section_segment", "canonical_range", "canonical_range_segment"}:
        return {}
    next_anchor = extraction.get("next_anchor")
    if not isinstance(next_anchor, dict):
        next_anchor = {}
    kind = "section" if content_kind in {"section_complete", "section_segment"} else "range"
    return {
        key: value
        for key, value in {
            "kind": kind,
            "mode": content_kind,
            "state": _text(extraction.get("range_state")) or ("segment" if content_kind.endswith("_segment") else "complete"),
            "start_page_no": _int(extraction.get("page_start")),
            "end_page_no": _int(extraction.get("page_end")),
            "requested_end_page_no": _int(extraction.get("requested_page_end")),
            "section_id": _text(extraction.get("section_id")),
            "section_no": _int(extraction.get("section_no")),
            "chapter_no": _int(extraction.get("chapter_no")),
            "section_kind": _text(extraction.get("section_kind")),
            "section_level": _int(extraction.get("section_level")),
            "parent_section_id": _text(extraction.get("parent_section_id")),
            "next_page_no": _int(next_anchor.get("page_no")),
            "next_para_no": _int(next_anchor.get("para_no")),
            "next_paragraph_id": _int(next_anchor.get("paragraph_id")),
            "incomplete_page_no": _first_int(extraction.get("incomplete_pages")),
            "page_span": _int(extraction.get("page_count")),
        }.items()
        if value not in ("", None)
    }


def _interval_hint_from_section_result(result: Any) -> dict[str, Any]:
    if getattr(result, "tool_name", "") != librarian_tools.TOOL_SECTION_BOUNDS:
        return {}
    interval = getattr(result, "interval", None)
    if not isinstance(interval, dict) or not interval:
        return {}
    item = result.items[0] if getattr(result, "items", None) else {}
    if not isinstance(item, dict):
        item = {}
    start = interval.get("start") if isinstance(interval.get("start"), dict) else {}
    end = interval.get("end") if isinstance(interval.get("end"), dict) else {}
    return {
        key: value
        for key, value in {
            "kind": "section",
            "mode": "section_bounds",
            "state": _text(interval.get("state") or interval.get("boundary_state")),
            "start_page_no": _int(start.get("page_no") or start.get("unit_no")),
            "end_page_no": _int(end.get("page_no") or end.get("unit_no")),
            "section_id": _text(item.get("section_id")),
            "section_no": _int(item.get("section_no")),
            "chapter_no": _int(item.get("chapter_no")),
            "section_kind": _text(item.get("section_kind")),
            "section_level": _int(item.get("level")),
            "parent_section_id": _text(item.get("parent_section_id")),
        }.items()
        if value not in ("", None)
    }


def _section_interval_hint_from_tool_results(
    tool_results: Sequence[librarian_tools.BiblioLibrarianToolResult | None],
) -> tuple[str, dict[str, Any]]:
    for result in reversed(tool_results):
        if result is None or getattr(result, "tool_name", "") != librarian_tools.TOOL_SECTION_BOUNDS:
            continue
        interval = _interval_hint_from_section_result(result)
        if interval:
            return _text(getattr(result, "document_id", "")), interval
    return "", {}


def _text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if type(value) in {int, float}:
        return str(value)
    return ""


def _int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _first_int(value: Any) -> int | None:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            parsed = _int(item)
            if parsed is not None:
                return parsed
    return None
