"""Content-free conversation state for native Biblio.

The state is attached to conversation messages through ``meta``.  It stores
technical anchors only: document ids, short ids, positions, hashes, counts and
reason codes.  It never stores passages, Catalogue payloads, raw prompts or
raw user queries.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


META_KEY = "biblio_state"
SCHEMA_VERSION = "biblio_conversation_state_v1"
PERSISTENCE_MODE = "conversation_message_meta"

_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-.:/")
_HEX_CHARS = set("0123456789abcdef")


@dataclass(frozen=True)
class BiblioConversationState:
    schema_version: str = SCHEMA_VERSION
    conversation_id: str = ""
    current_document: dict[str, Any] = field(default_factory=dict)
    current_work: dict[str, Any] = field(default_factory=dict)
    page_no: int | None = None
    para_no: int | None = None
    paragraph_id: int | None = None
    last_passage_hash: str = ""
    last_result: dict[str, Any] = field(default_factory=dict)
    last_candidates: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    last_ambiguity: dict[str, Any] = field(default_factory=dict)
    last_intent: str = ""
    updated_at: str = ""
    source_event: str = ""

    @classmethod
    def empty(cls, *, conversation_id: str = "") -> "BiblioConversationState":
        return cls(conversation_id=_safe_text(conversation_id, max_chars=160))

    @classmethod
    def from_mapping(cls, value: Any, *, conversation_id: str = "") -> "BiblioConversationState":
        data = _mapping(value)
        if data.get("schema_version") != SCHEMA_VERSION:
            return cls.empty(conversation_id=conversation_id)
        state_conversation_id = _safe_text(data.get("conversation_id"), max_chars=160)
        return cls(
            conversation_id=state_conversation_id or _safe_text(conversation_id, max_chars=160),
            current_document=_anchor_mapping(data.get("current_document")),
            current_work=_work_mapping(data.get("current_work")),
            page_no=_optional_int(data.get("page_no")),
            para_no=_optional_int(data.get("para_no")),
            paragraph_id=_optional_int(data.get("paragraph_id")),
            last_passage_hash=_strict_hash_12(data.get("last_passage_hash")),
            last_result=_anchor_mapping(data.get("last_result")),
            last_candidates=tuple(_anchor_mapping(item) for item in _sequence(data.get("last_candidates")))[:8],
            last_ambiguity=_ambiguity_mapping(data.get("last_ambiguity")),
            last_intent=_safe_token(data.get("last_intent")),
            updated_at=_safe_text(data.get("updated_at"), max_chars=40),
            source_event=_safe_token(data.get("source_event")),
        )

    @property
    def present(self) -> bool:
        return bool(
            self.current_document
            or self.current_work
            or self.last_result
            or self.last_candidates
            or self.last_ambiguity
            or self.last_intent
        )

    @property
    def has_last_anchor(self) -> bool:
        return _anchor_has_position(self.last_result) or bool(self.last_passage_hash)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "conversation_id": self.conversation_id,
            "current_document": dict(self.current_document),
            "current_work": dict(self.current_work),
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "last_passage_hash": self.last_passage_hash,
            "last_result": dict(self.last_result),
            "last_candidates": [dict(item) for item in self.last_candidates],
            "last_ambiguity": dict(self.last_ambiguity),
            "last_intent": self.last_intent,
            "updated_at": self.updated_at,
            "source_event": self.source_event,
        }

    def to_observability(self) -> dict[str, Any]:
        interval_hint = _mapping(self.last_result.get("interval_hint"))
        return {
            "schema_version": SCHEMA_VERSION,
            "persistence_mode": PERSISTENCE_MODE,
            "present": self.present,
            "conversation_id_present": bool(self.conversation_id),
            "current_document_present": bool(self.current_document),
            "current_document_doc_id_short": _safe_doc_id(self.current_document.get("doc_id_short")),
            "current_document_id_present": bool(self.current_document.get("document_id")),
            "current_work_present": bool(self.current_work),
            "page_no": self.page_no,
            "para_no": self.para_no,
            "paragraph_id": self.paragraph_id,
            "last_passage_hash": self.last_passage_hash,
            "last_result_present": bool(self.last_result),
            "last_result_status": _safe_token(self.last_result.get("status")),
            "last_result_reason_code": _safe_token(self.last_result.get("reason_code")),
            "last_result_interval_kind": _safe_token(interval_hint.get("kind")),
            "last_result_interval_mode": _safe_token(interval_hint.get("mode")),
            "last_result_interval_state": _safe_token(interval_hint.get("state")),
            "last_result_interval_end_page_no": _optional_int(interval_hint.get("end_page_no")),
            "last_result_interval_end_para_no": _optional_int(interval_hint.get("end_para_no")),
            "last_result_interval_requested_end_page_no": _optional_int(interval_hint.get("requested_end_page_no")),
            "last_result_interval_section_id_present": bool(interval_hint.get("section_id")),
            "last_result_interval_section_no": _optional_int(interval_hint.get("section_no")),
            "last_result_interval_chapter_no": _optional_int(interval_hint.get("chapter_no")),
            "last_result_interval_section_kind": _safe_token(interval_hint.get("section_kind")),
            "last_result_interval_section_level": _optional_int(interval_hint.get("section_level")),
            "last_result_interval_parent_section_id_present": bool(interval_hint.get("parent_section_id")),
            "last_result_interval_next_page_no": _optional_int(interval_hint.get("next_page_no")),
            "last_result_interval_next_para_no": _optional_int(interval_hint.get("next_para_no")),
            "last_candidate_count": len(self.last_candidates),
            "last_ambiguity_present": bool(self.last_ambiguity),
            "last_ambiguity_candidate_count": _optional_int(self.last_ambiguity.get("candidate_count")) or 0,
            "last_intent": self.last_intent,
            "updated_at_present": bool(self.updated_at),
        }


@dataclass(frozen=True)
class BiblioStateTransition:
    before_present: bool
    after_present: bool
    changed: bool
    reason_code: str
    source_event: str
    persistence_mode: str = PERSISTENCE_MODE
    attached_to_message_meta: bool = True
    persistence_status: str = "pending_normal_conversation_save"
    persistence_guarantee: str = "after_normal_conversation_save"

    def to_observability(self) -> dict[str, Any]:
        return {
            "before_present": self.before_present,
            "after_present": self.after_present,
            "changed": self.changed,
            "reason_code": self.reason_code,
            "source_event": self.source_event,
            "persistence_mode": self.persistence_mode,
            "attached_to_message_meta": self.attached_to_message_meta,
            "persistence_status": self.persistence_status,
            "persistence_guarantee": self.persistence_guarantee,
        }


def read_state_from_conversation(conversation: Mapping[str, Any]) -> BiblioConversationState:
    conversation_id = _safe_text(conversation.get("id"), max_chars=160)
    top_level_state = _mapping(conversation.get(META_KEY))
    if top_level_state:
        return BiblioConversationState.from_mapping(top_level_state, conversation_id=conversation_id)
    for message in reversed(_sequence(conversation.get("messages"))):
        meta = _mapping(_mapping(message).get("meta"))
        raw_state = meta.get(META_KEY)
        if raw_state:
            state = BiblioConversationState.from_mapping(raw_state, conversation_id=conversation_id)
            if state.present:
                return state
    return BiblioConversationState.empty(conversation_id=conversation_id)


def attach_state_to_latest_user_message(
    conversation: dict[str, Any],
    state: BiblioConversationState | None,
) -> bool:
    if state is None or not state.present:
        return False
    messages = conversation.get("messages")
    if not isinstance(messages, list):
        return False
    for message in reversed(messages):
        if not isinstance(message, dict) or str(message.get("role") or "") != "user":
            continue
        meta = message.get("meta")
        if not isinstance(meta, dict):
            meta = {}
        meta[META_KEY] = state.to_dict()
        message["meta"] = meta
        return True
    return False


def clear_state(*, conversation_id: str = "") -> BiblioConversationState:
    return BiblioConversationState.empty(conversation_id=conversation_id)


def update_state_from_runtime(
    previous: BiblioConversationState,
    *,
    query_plan: Any = None,
    library_result: Any = None,
    chat_result: Any = None,
    conversation_id: str = "",
    now_iso: str = "",
    source_event: str = "biblio_chat_turn",
    reason_code: str = "biblio_state_updated",
) -> tuple[BiblioConversationState, BiblioStateTransition]:
    before = previous if isinstance(previous, BiblioConversationState) else BiblioConversationState.empty()
    current_document = dict(before.current_document)
    current_work = dict(before.current_work)
    page_no = before.page_no
    para_no = before.para_no
    paragraph_id = before.paragraph_id
    last_passage_hash = before.last_passage_hash
    last_result = dict(before.last_result)
    last_candidates = list(before.last_candidates)
    last_ambiguity = dict(before.last_ambiguity)
    last_intent = _safe_token(getattr(query_plan, "intent", None)) or before.last_intent

    runtime_result = library_result or chat_result
    work_signal = _work_signal_from_plan(query_plan) or _work_signal_from_runtime(runtime_result)
    if work_signal:
        current_work = work_signal

    anchor = _anchor_from_runtime_result(runtime_result)
    if anchor:
        last_result = anchor
        current_document = _document_from_anchor(anchor) or current_document
        page_no = _optional_int(anchor.get("page_no")) or page_no
        para_no = _optional_int(anchor.get("para_no")) or para_no
        paragraph_id = _optional_int(anchor.get("paragraph_id")) or paragraph_id
        last_passage_hash = _strict_hash_12(anchor.get("passage_hash")) or last_passage_hash

    candidates = _candidate_anchors_from_runtime(runtime_result)
    if candidates:
        last_candidates = list(candidates)

    ambiguity = _ambiguity_from_runtime(runtime_result, candidates)
    if ambiguity:
        last_ambiguity = ambiguity
    elif anchor and _safe_token(anchor.get("status")) not in {"ambiguous"}:
        last_ambiguity = {}

    after = BiblioConversationState(
        conversation_id=_safe_text(conversation_id, max_chars=160) or before.conversation_id,
        current_document=current_document,
        current_work=current_work,
        page_no=page_no,
        para_no=para_no,
        paragraph_id=paragraph_id,
        last_passage_hash=last_passage_hash,
        last_result=last_result,
        last_candidates=tuple(last_candidates[:8]),
        last_ambiguity=last_ambiguity,
        last_intent=last_intent,
        updated_at=_safe_text(now_iso, max_chars=40) or before.updated_at,
        source_event=_safe_token(source_event),
    )
    transition = BiblioStateTransition(
        before_present=before.present,
        after_present=after.present,
        changed=before.to_dict() != after.to_dict(),
        reason_code=_safe_token(reason_code) or "biblio_state_updated",
        source_event=_safe_token(source_event),
    )
    return after, transition


def _anchor_from_runtime_result(value: Any) -> dict[str, Any]:
    direct_anchor = _anchor_mapping(getattr(value, "state_anchor", None))
    if direct_anchor:
        return direct_anchor
    for candidate in (
        getattr(value, "passage_result", None),
        getattr(value, "context_result", None),
    ):
        anchor = _anchor_from_passage_like(candidate)
        if anchor:
            return anchor
    passage_results = getattr(value, "passage_results", None)
    for item in _sequence(passage_results):
        anchor = _anchor_from_passage_like(item)
        if anchor:
            return anchor
    consultation = getattr(value, "consultation_message", None)
    document_ids = tuple(_safe_doc_id(item) for item in _sequence(getattr(value, "document_ids", ())) if item)
    doc_ids = tuple(_safe_doc_id(item) for item in _sequence(getattr(consultation, "doc_id_shorts", ())) if item)
    status = _safe_token(getattr(value, "status", ""))
    if (document_ids or doc_ids) and status in {"opened", "resolved", "toc_listed", "toc_summary"}:
        return {
            "status": status,
            "reason_code": _safe_token(getattr(value, "reason_code", "")),
            "document_id": document_ids[0] if document_ids else "",
            "doc_id_short": doc_ids[0] if doc_ids else (document_ids[0][:8] if document_ids else ""),
        }
    return {}


def _anchor_from_passage_like(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    observed = _mapping(getattr(value, "to_observability", lambda: {})())
    passage_hash = _strict_hash_12(observed.get("passage_hash")) or _strict_hash_12(getattr(value, "passage_hash", ""))
    raw_passage = getattr(value, "passage", "")
    if not passage_hash and raw_passage:
        passage_hash = _sha256_12(raw_passage)
    resolution = getattr(value, "resolution", None)
    document = getattr(resolution, "document", None)
    locator = getattr(resolution, "locator", None)
    doc_id = _safe_doc_id(getattr(document, "document_id", ""))
    if not doc_id:
        doc_id = _safe_doc_id(getattr(locator, "document_id", ""))
    anchor = {
        "status": _safe_token(getattr(value, "status", None) or observed.get("status")),
        "reason_code": _safe_token(getattr(value, "reason_code", None) or observed.get("reason_code")),
        "document_id": doc_id,
        "doc_id_short": _safe_doc_id(
            getattr(value, "doc_id_short", None)
            or observed.get("doc_id_short")
            or getattr(document, "doc_id_short", "")
            or getattr(locator, "doc_id_short", "")
        ),
        "page_no": _optional_int(getattr(value, "page_no", None) or observed.get("page_no") or getattr(locator, "page_no", None)),
        "para_no": _optional_int(getattr(value, "para_no", None) or observed.get("para_no") or getattr(locator, "para_no", None)),
        "paragraph_id": _optional_int(
            getattr(value, "paragraph_id", None) or observed.get("paragraph_id") or getattr(locator, "paragraph_id", None)
        ),
        "passage_hash": passage_hash,
        "passage_chars": _optional_int(getattr(value, "passage_chars", None) or observed.get("passage_chars")),
        "excerpt_start": _optional_int(getattr(value, "excerpt_start", None) or observed.get("excerpt_start")),
        "excerpt_end": _optional_int(getattr(value, "excerpt_end", None) or observed.get("excerpt_end")),
        "text_length": _optional_int(getattr(value, "text_length", None) or observed.get("text_length")),
        "interval_hint": _interval_hint_mapping(
            getattr(getattr(value, "interval_hint", None), "to_observability", lambda: getattr(value, "interval_hint", None))()
            if getattr(value, "interval_hint", None) is not None
            else observed.get("interval_hint")
        ),
    }
    return _anchor_mapping(anchor)


def _candidate_anchors_from_runtime(value: Any) -> tuple[dict[str, Any], ...]:
    anchors: list[dict[str, Any]] = []
    context_result = getattr(value, "context_result", None) or (
        value if value is not None and value.__class__.__name__ == "BiblioPassageContextSearchResult" else None
    )
    if context_result is not None:
        candidate_result = getattr(context_result, "candidate_result", None)
        for candidate in _sequence(getattr(candidate_result, "candidates", ())):
            anchors.append(
                _anchor_mapping(
                    {
                        "status": _safe_token(getattr(candidate_result, "status", "")),
                        "reason_code": _safe_token(getattr(candidate_result, "reason_code", "")),
                        "document_id": _safe_doc_id(getattr(candidate, "document_id", "")),
                        "doc_id_short": _safe_doc_id(getattr(candidate, "doc_id_short", "")),
                        "page_no": _optional_int(getattr(candidate, "page_no", None)),
                        "para_no": _optional_int(getattr(candidate, "para_no", None)),
                        "paragraph_id": _optional_int(getattr(candidate, "paragraph_id", None)),
                    }
                )
            )
        for passage in _sequence(getattr(context_result, "passage_results", ())):
            anchors.append(_anchor_from_passage_like(passage))
        for decision in _sequence(getattr(context_result, "decisions", ())):
            anchors.append(
                _anchor_mapping(
                    {
                        "status": _safe_token(getattr(decision, "status", "")),
                        "reason_code": _safe_token(getattr(decision, "reason_code", "")),
                        "doc_id_short": _safe_doc_id(getattr(decision, "doc_id_short", "")),
                        "page_no": _optional_int(getattr(decision, "page_no", None)),
                        "para_no": _optional_int(getattr(decision, "para_no", None)),
                        "paragraph_id": _optional_int(getattr(decision, "paragraph_id", None)),
                        "passage_hash": _strict_hash_12(getattr(decision, "context_hash", "")),
                    }
                )
            )
    else:
        passage = getattr(value, "passage_result", None)
        if passage is not None:
            anchors.append(_anchor_from_passage_like(passage))
        consultation = getattr(value, "consultation_message", None)
        status = _safe_token(getattr(value, "status", ""))
        reason = _safe_token(getattr(value, "reason_code", ""))
        for document_id in _sequence(getattr(value, "document_ids", ())):
            anchors.append(
                _anchor_mapping(
                    {
                        "status": status,
                        "reason_code": reason,
                        "document_id": _safe_doc_id(document_id),
                        "doc_id_short": _safe_doc_id(document_id)[:8],
                    }
                )
            )
        for doc_id_short in _sequence(getattr(consultation, "doc_id_shorts", ())):
            anchors.append(
                _anchor_mapping(
                    {
                        "status": status,
                        "reason_code": reason,
                        "doc_id_short": _safe_doc_id(doc_id_short),
                    }
                )
            )

    out: list[dict[str, Any]] = []
    seen: set[tuple[Any, ...]] = set()
    for anchor in anchors:
        clean = _anchor_mapping(anchor)
        if not clean:
            continue
        key = (
            clean.get("document_id") or clean.get("doc_id_short"),
            clean.get("page_no"),
            clean.get("para_no"),
            clean.get("paragraph_id"),
            clean.get("passage_hash"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(clean)
    return tuple(out[:8])


def _ambiguity_from_runtime(value: Any, candidates: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    status = _safe_token(getattr(value, "status", ""))
    reason_code = _safe_token(getattr(value, "reason_code", ""))
    context_result = getattr(value, "context_result", None) or (
        value if value is not None and value.__class__.__name__ == "BiblioPassageContextSearchResult" else None
    )
    if context_result is not None:
        status = _safe_token(getattr(context_result, "status", "")) or status
        reason_code = _safe_token(getattr(context_result, "reason_code", "")) or reason_code
        observed = _mapping(getattr(context_result, "to_observability", lambda: {})())
        if status == "ambiguous" or bool(observed.get("ambiguous")):
            return {
                "status": status or "ambiguous",
                "reason_code": reason_code,
                "candidate_count": _optional_int(observed.get("candidate_count")) or len(candidates),
                "selected_count": _optional_int(observed.get("selected_count")) or 0,
                "doc_id_shorts": [
                    _safe_doc_id(item.get("doc_id_short"))
                    for item in candidates[:8]
                    if _safe_doc_id(item.get("doc_id_short"))
                ],
            }
    if status == "ambiguous":
        return {
            "status": status,
            "reason_code": reason_code,
            "candidate_count": len(candidates),
            "selected_count": 0,
            "doc_id_shorts": [
                _safe_doc_id(item.get("doc_id_short")) for item in candidates[:8] if _safe_doc_id(item.get("doc_id_short"))
            ],
        }
    return {}


def _document_from_anchor(anchor: Mapping[str, Any]) -> dict[str, Any]:
    doc_id = _safe_doc_id(anchor.get("document_id"))
    doc_id_short = _safe_doc_id(anchor.get("doc_id_short"))
    if not (doc_id or doc_id_short):
        return {}
    return {
        "document_id": doc_id,
        "doc_id_short": doc_id_short or doc_id[:8],
        "source": "biblio_runtime_anchor",
    }


def _work_signal_from_plan(plan: Any) -> dict[str, Any]:
    if plan is None:
        return {}
    text = ""
    for attr in ("work_title", "document_title", "catalogue_query", "author"):
        value = str(getattr(plan, attr, "") or "").strip()
        if value:
            text = value
            break
    if not text:
        return {}
    return {
        "present": True,
        "label_sha256_12": _sha256_12(text),
        "label_chars": len(text),
        "source": "query_plan",
    }


def _work_signal_from_runtime(value: Any) -> dict[str, Any]:
    answer = getattr(value, "answer_object", None)
    if answer is None:
        return {}
    if _safe_token(getattr(answer, "work_state", "")) != "ready":
        return {}
    work_id = _safe_token(getattr(answer, "work_id", ""))
    if not work_id:
        return {}
    return {
        "present": True,
        "label_sha256_12": _sha256_12(work_id),
        "label_chars": len(work_id),
        "source": "answer_object",
    }


def _anchor_mapping(value: Any) -> dict[str, Any]:
    item = _mapping(value)
    if not item:
        return {}
    out = {
        "status": _safe_token(item.get("status")),
        "reason_code": _safe_token(item.get("reason_code")),
        "document_id": _safe_doc_id(item.get("document_id")),
        "doc_id_short": _safe_doc_id(item.get("doc_id_short")),
        "page_no": _optional_int(item.get("page_no")),
        "para_no": _optional_int(item.get("para_no")),
        "paragraph_id": _optional_int(item.get("paragraph_id")),
        "passage_hash": _strict_hash_12(item.get("passage_hash")),
        "passage_chars": _optional_int(item.get("passage_chars")),
        "excerpt_start": _optional_int(item.get("excerpt_start")),
        "excerpt_end": _optional_int(item.get("excerpt_end")),
        "text_length": _optional_int(item.get("text_length")),
        "interval_hint": _interval_hint_mapping(item.get("interval_hint")),
    }
    return {key: value for key, value in out.items() if value not in ("", None)}


def _interval_hint_mapping(value: Any) -> dict[str, Any]:
    item = _mapping(value)
    if not item:
        return {}
    out = {
        "kind": _safe_token(item.get("kind")),
        "mode": _safe_token(item.get("mode")),
        "state": _safe_token(item.get("state")),
        "start_page_no": _optional_int(item.get("start_page_no")),
        "start_para_no": _optional_int(item.get("start_para_no")),
        "start_paragraph_id": _optional_int(item.get("start_paragraph_id")),
        "end_page_no": _optional_int(item.get("end_page_no")),
        "end_para_no": _optional_int(item.get("end_para_no")),
        "end_paragraph_id": _optional_int(item.get("end_paragraph_id")),
        "requested_end_page_no": _optional_int(item.get("requested_end_page_no")),
        "requested_end_para_no": _optional_int(item.get("requested_end_para_no")),
        "requested_end_paragraph_id": _optional_int(item.get("requested_end_paragraph_id")),
        "section_id": _safe_doc_id(item.get("section_id")),
        "section_no": _optional_int(item.get("section_no")),
        "chapter_no": _optional_int(item.get("chapter_no")),
        "section_kind": _safe_token(item.get("section_kind")),
        "section_level": _optional_int(item.get("section_level")),
        "parent_section_id": _safe_doc_id(item.get("parent_section_id")),
        "next_page_no": _optional_int(item.get("next_page_no")),
        "next_para_no": _optional_int(item.get("next_para_no")),
        "next_paragraph_id": _optional_int(item.get("next_paragraph_id")),
        "page_span": _optional_int(item.get("page_span")),
        "paragraph_span": _optional_int(item.get("paragraph_span")),
    }
    return {key: value for key, value in out.items() if value not in ("", None)}


def _work_mapping(value: Any) -> dict[str, Any]:
    item = _mapping(value)
    if not item:
        return {}
    label_hash = _strict_hash_12(item.get("label_sha256_12"))
    chars = _optional_int(item.get("label_chars"))
    if not (label_hash or chars):
        return {}
    return {
        "present": True,
        "label_sha256_12": label_hash,
        "label_chars": chars or 0,
        "source": _safe_token(item.get("source")),
    }


def _ambiguity_mapping(value: Any) -> dict[str, Any]:
    item = _mapping(value)
    if not item:
        return {}
    out = {
        "status": _safe_token(item.get("status")),
        "reason_code": _safe_token(item.get("reason_code")),
        "candidate_count": _optional_int(item.get("candidate_count")) or 0,
        "selected_count": _optional_int(item.get("selected_count")) or 0,
        "doc_id_shorts": [
            _safe_doc_id(raw)
            for raw in _sequence(item.get("doc_id_shorts"))
            if _safe_doc_id(raw)
        ][:8],
    }
    return {key: value for key, value in out.items() if value not in ("", None, [])}


def _anchor_has_position(anchor: Mapping[str, Any]) -> bool:
    return bool(
        anchor
        and (
            _safe_doc_id(anchor.get("document_id"))
            or _safe_doc_id(anchor.get("doc_id_short"))
        )
        and (
            _optional_int(anchor.get("page_no")) is not None
            or _optional_int(anchor.get("para_no")) is not None
            or _optional_int(anchor.get("paragraph_id")) is not None
        )
    )


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return value
    return ()


def _optional_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _safe_text(value: Any, *, max_chars: int) -> str:
    return str(value or "").strip()[:max_chars]


def _safe_token(value: Any, *, max_chars: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if any(char not in _TOKEN_CHARS for char in text):
        return f"sha256:{_sha256_12(text)}"
    return text[:max_chars]


def _safe_doc_id(value: Any) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    lowered = text.lower()
    if all(char in _TOKEN_CHARS for char in lowered):
        return text[:160]
    return f"sha256:{_sha256_12(text)}"


def _strict_hash_12(value: Any) -> str:
    text = str(value or "").strip().lower()
    if len(text) == 12 and all(char in _HEX_CHARS for char in text):
        return text
    return ""


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
