"""Content-free state-reference helpers for Biblio dialogue planning."""

from __future__ import annotations

from typing import Any, Mapping

from .conversation_state import BiblioConversationState
from .librarian_planner import BiblioLibrarianToolCall
from . import librarian_tools as tools


def current_document_id(state: BiblioConversationState) -> str:
    return str(state.current_document.get("document_id") or "").strip()


def anchored_document_id(state: BiblioConversationState) -> str:
    doc_id = current_document_id(state)
    if doc_id:
        return doc_id
    return str(state.last_result.get("document_id") or "").strip()


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


def last_result_interval_end_context_params(
    state: BiblioConversationState,
    *,
    window_chars: int = 700,
) -> dict[str, Any]:
    last = state.last_result
    doc_id = str(last.get("document_id") or "").strip() or current_document_id(state)
    if not doc_id:
        return {}
    interval_hint = last.get("interval_hint")
    if not isinstance(interval_hint, Mapping) or str(interval_hint.get("kind") or "").strip() != "range":
        return {}
    params: dict[str, Any] = {"document_id": doc_id, "window_chars": window_chars}
    if str(interval_hint.get("state") or "").strip() == "segment":
        if interval_hint.get("next_paragraph_id") is not None:
            params["paragraph_id"] = interval_hint.get("next_paragraph_id")
            return params
        next_page_no = interval_hint.get("next_page_no")
        next_para_no = interval_hint.get("next_para_no")
        if next_page_no is not None and next_para_no is not None:
            params["page_no"] = next_page_no
            params["para_no"] = next_para_no
            return params
    if interval_hint.get("end_paragraph_id") is not None:
        params["paragraph_id"] = interval_hint.get("end_paragraph_id")
        return params
    end_page_no = interval_hint.get("end_page_no")
    end_para_no = interval_hint.get("end_para_no")
    if end_page_no is None or end_para_no is None:
        return {}
    params["page_no"] = end_page_no
    params["para_no"] = end_para_no
    return params


def previous_segment_context_params(
    state: BiblioConversationState,
    *,
    window_chars: int = 700,
) -> dict[str, Any]:
    last = state.last_result
    doc_id = str(last.get("document_id") or "").strip() or current_document_id(state)
    if not doc_id:
        return {}
    page_no = last.get("page_no") if last.get("page_no") is not None else state.page_no
    para_no = last.get("para_no") if last.get("para_no") is not None else state.para_no
    if page_no is None or para_no is None or para_no <= 1:
        return {}
    return {
        "document_id": doc_id,
        "page_no": page_no,
        "para_no": para_no - 1,
        "window_chars": window_chars,
    }


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
