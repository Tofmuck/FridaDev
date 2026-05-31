"""Content-free state-reference helpers for Biblio dialogue planning."""

from __future__ import annotations

from typing import Any, Mapping

from .conversation_state import BiblioConversationState
from .librarian_planner import BiblioLibrarianToolCall
from . import librarian_tools as tools


def current_document_id(state: BiblioConversationState) -> str:
    return str(state.current_document.get("document_id") or "").strip()


def last_result_context_params(state: BiblioConversationState) -> dict[str, Any]:
    last = state.last_result
    doc_id = str(last.get("document_id") or "").strip() or current_document_id(state)
    if not doc_id:
        return {}
    params: dict[str, Any] = {"document_id": doc_id, "window_chars": 700}
    if last.get("paragraph_id") is not None:
        params["paragraph_id"] = last.get("paragraph_id")
        return params
    page_no = last.get("page_no") if last.get("page_no") is not None else state.page_no
    para_no = last.get("para_no") if last.get("para_no") is not None else state.para_no
    if page_no is None or para_no is None:
        return {}
    params["page_no"] = page_no
    params["para_no"] = para_no
    return params


def candidate_has_context_position(candidate: Mapping[str, Any]) -> bool:
    if not str(candidate.get("document_id") or "").strip():
        return False
    if candidate.get("paragraph_id") is not None:
        return True
    return candidate.get("page_no") is not None and candidate.get("para_no") is not None


def context_call_from_candidate(candidate: Mapping[str, Any]) -> BiblioLibrarianToolCall:
    params: dict[str, Any] = {
        "document_id": str(candidate.get("document_id") or "").strip(),
        "window_chars": 700,
    }
    if candidate.get("paragraph_id") is not None:
        params["paragraph_id"] = candidate.get("paragraph_id")
    else:
        params["page_no"] = candidate.get("page_no")
        params["para_no"] = candidate.get("para_no")
    return BiblioLibrarianToolCall(tool_name=tools.TOOL_PASSAGE_CONTEXT, params=params, method="GET")
