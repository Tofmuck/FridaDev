"""Structural navigation decisions for Biblio product methods."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


REASON_NEXT_CHAPTER_ANCHOR_MISSING = "biblio_next_chapter_anchor_missing"
REASON_NEXT_CHAPTER_UNRESOLVED = "biblio_next_chapter_unresolved"


@dataclass(frozen=True)
class NextChapterTarget:
    document_id: str = ""
    section_params: dict[str, Any] = field(default_factory=dict)
    reason_code: str = ""


def resolve_next_chapter_target(
    conversation_state: Any,
    *,
    catalogue_client: Any,
) -> NextChapterTarget:
    """Resolve the next structural sibling without executing librarian tools."""
    document_id, interval = _state_section_scope(conversation_state)
    if not document_id or not interval:
        return NextChapterTarget(reason_code=REASON_NEXT_CHAPTER_ANCHOR_MISSING)
    params = _next_structural_sibling_params(
        catalogue_client,
        document_id=document_id,
        interval=interval,
    )
    if not params:
        return NextChapterTarget(
            document_id=document_id,
            reason_code=REASON_NEXT_CHAPTER_UNRESOLVED,
        )
    return NextChapterTarget(document_id=document_id, section_params=params)


def _state_section_scope(conversation_state: Any) -> tuple[str, Mapping[str, Any]]:
    last_result = getattr(conversation_state, "last_result", None)
    if not isinstance(last_result, Mapping):
        last_result = {}
    current_document = getattr(conversation_state, "current_document", None)
    if not isinstance(current_document, Mapping):
        current_document = {}
    document_id = _text(last_result.get("document_id")) or _text(current_document.get("document_id"))
    interval = last_result.get("interval_hint")
    if not isinstance(interval, Mapping):
        return document_id, {}
    if _text(interval.get("kind")) != "section":
        return document_id, {}
    if not (
        _text(interval.get("section_id"))
        or _positive_int(interval.get("section_no"))
        or _positive_int(interval.get("chapter_no"))
    ):
        return document_id, {}
    return document_id, interval


def _next_structural_sibling_params(
    catalogue_client: Any,
    *,
    document_id: str,
    interval: Mapping[str, Any],
) -> dict[str, Any]:
    rows = _structure_rows(catalogue_client, document_id=document_id)
    if not rows:
        return {}
    current_index = _current_section_index(rows, interval=interval)
    if current_index < 0:
        return {}
    current_row = rows[current_index]
    current_level = _positive_int(current_row.get("level")) or _positive_int(interval.get("section_level")) or 1
    current_parent = _text(current_row.get("parent_section_id")) or _text(interval.get("parent_section_id"))
    for row in rows[current_index + 1 :]:
        level = _positive_int(row.get("level")) or 1
        parent = _text(row.get("parent_section_id"))
        if level != current_level or parent != current_parent:
            continue
        section_id = _text(row.get("section_id"))
        if section_id:
            return {"section_id": section_id}
        section_no = _positive_int(row.get("section_no") or row.get("chapter_no"))
        if section_no:
            return {"chapter_no": section_no}
    return {}


def _structure_rows(catalogue_client: Any, *, document_id: str) -> tuple[Mapping[str, Any], ...]:
    sections_fn = getattr(catalogue_client, "sections", None)
    if callable(sections_fn):
        try:
            response = sections_fn(document_id, limit=500, offset=0)
        except Exception:
            response = None
        rows = _payload_rows(getattr(response, "payload", {}), "sections") if response is not None else ()
        if rows:
            return rows
    chapters_fn = getattr(catalogue_client, "chapters", None)
    if callable(chapters_fn):
        try:
            response = chapters_fn(document_id, limit=500, offset=0)
        except Exception:
            response = None
        rows = _payload_rows(getattr(response, "payload", {}), "chapters") if response is not None else ()
        if rows:
            return rows
    return ()


def _payload_rows(payload: Any, key: str) -> tuple[Mapping[str, Any], ...]:
    if not isinstance(payload, Mapping):
        return ()
    rows = payload.get(key)
    if not isinstance(rows, Sequence) or isinstance(rows, (str, bytes, bytearray)):
        return ()
    return tuple(row for row in rows if isinstance(row, Mapping))


def _current_section_index(rows: Sequence[Mapping[str, Any]], *, interval: Mapping[str, Any]) -> int:
    section_id = _text(interval.get("section_id"))
    section_no = _positive_int(interval.get("section_no")) or _positive_int(interval.get("chapter_no"))
    for index, row in enumerate(rows):
        if section_id and _text(row.get("section_id")) == section_id:
            return index
        row_no = _positive_int(row.get("section_no")) or _positive_int(row.get("chapter_no"))
        if section_no and row_no == section_no:
            return index
    return -1


def _positive_int(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 0
    return parsed if parsed > 0 else 0


def _text(value: Any) -> str:
    return str(value or "").strip()
