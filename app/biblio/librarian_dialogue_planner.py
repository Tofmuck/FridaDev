"""Dialogue-level planning for the future Biblio librarian agent.

This module prepares implicit conversation requests for the bounded librarian
loop.  It does not call Catalogue, does not call a model and is not wired into
the product runtime.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from .conversation_state import BiblioConversationState
from .librarian_planner import BiblioLibrarianPlan, BiblioLibrarianToolCall
from . import librarian_tools as tools
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_token as _safe_token
from .query_normalizer import compact_text_signal, fold_text, normalize_text, query_variants


SCHEMA_VERSION = "biblio_librarian_dialogue_plan_v1"

STATUS_PLANNED = "planned"
STATUS_NEEDS_CLARIFICATION = "needs_clarification"
STATUS_UNSUPPORTED_MISSING_TOOL = "unsupported_missing_tool"
STATUS_FALLBACK_DETERMINISTIC = "fallback_deterministic"

INTENT_LIST_CATALOG = "list_catalog"
INTENT_SEARCH_PASSAGE = "search_passage"
INTENT_SEARCH_CURRENT_DOCUMENT = "search_current_document"
INTENT_SHOW_TABLE_OF_CONTENTS = "show_table_of_contents"
INTENT_COMPARE_PASSAGES = "compare_passages"
INTENT_NAVIGATE = "navigate"
INTENT_FALLBACK = "fallback"

REASON_CATALOG_LIST = "biblio_dialogue_catalog_list"
REASON_THEME_SEARCH = "biblio_dialogue_theme_search"
REASON_CURRENT_DOCUMENT_SEARCH = "biblio_dialogue_current_document_search"
REASON_CURRENT_DOCUMENT_MISSING = "biblio_dialogue_current_document_missing"
REASON_TABLE_OF_CONTENTS = "biblio_dialogue_table_of_contents"
REASON_NAVIGATION_TOOL_MISSING = "biblio_dialogue_navigation_tool_missing"
REASON_CANDIDATES_MISSING = "biblio_dialogue_candidates_missing"
REASON_CANDIDATES_INCOMPLETE = "biblio_dialogue_candidates_incomplete"
REASON_COMPARE_CANDIDATES = "biblio_dialogue_compare_candidates"
REASON_FALLBACK = "biblio_dialogue_fallback_deterministic"

_CURRENT_DOCUMENT_RE = re.compile(r"\b(ce|cet|cette|celui|celle|meme|même)\b")
_RECENT_DIALOGUE_MAX = 6


@dataclass(frozen=True)
class BiblioDialogueIntent:
    intent: str
    query_kind: str = ""
    state_required: bool = False
    tool_required: str = ""

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "intent": _safe_token(self.intent),
                "query_kind": _safe_token(self.query_kind),
                "state_required": self.state_required,
                "tool_required": _safe_token(self.tool_required),
            }
        )


@dataclass(frozen=True)
class BiblioDialoguePlanningRequest:
    user_message: str = field(default="", repr=False, compare=False)
    state: BiblioConversationState | Mapping[str, Any] | None = field(default=None, repr=False, compare=False)
    recent_dialogue: tuple[Mapping[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)

    @property
    def conversation_state(self) -> BiblioConversationState:
        if isinstance(self.state, BiblioConversationState):
            return self.state
        if isinstance(self.state, Mapping):
            return BiblioConversationState.from_mapping(self.state)
        return BiblioConversationState.empty()

    def to_observability(self) -> dict[str, Any]:
        state = self.conversation_state
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "user_message": compact_text_signal(self.user_message),
                "recent_dialogue_count": min(len(self.recent_dialogue), _RECENT_DIALOGUE_MAX),
                "state_present": state.present,
                "current_document_present": bool(state.current_document),
                "candidate_count": len(state.last_candidates),
            }
        )


@dataclass(frozen=True)
class BiblioDialoguePlanningResult:
    status: str
    reason_code: str
    intent: BiblioDialogueIntent
    plan: BiblioLibrarianPlan = field(default_factory=BiblioLibrarianPlan)
    state_present: bool = False
    current_document_used: bool = False
    candidate_count: int = 0
    tool_required: str = ""
    user_message_signal: dict[str, Any] = field(default_factory=dict)
    query_variant_count: int = 0
    query_variant_hashes: tuple[str, ...] = field(default_factory=tuple)

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "status": _safe_token(self.status),
                "reason_code": _safe_token(self.reason_code),
                "intent": self.intent.to_observability(),
                "plan": self.plan.to_observability(),
                "state_present": self.state_present,
                "current_document_used": self.current_document_used,
                "candidate_count": self.candidate_count,
                "tool_required": _safe_token(self.tool_required),
                "user_message": dict(self.user_message_signal),
                "query_variant_count": self.query_variant_count,
                "query_variant_hashes": list(self.query_variant_hashes),
            }
        )


class BiblioDialoguePlanner:
    def plan(
        self,
        request: BiblioDialoguePlanningRequest | None = None,
        *,
        user_message: str = "",
        state: BiblioConversationState | Mapping[str, Any] | None = None,
        recent_dialogue: Sequence[Mapping[str, Any]] = (),
    ) -> BiblioDialoguePlanningResult:
        planning_request = request or BiblioDialoguePlanningRequest(
            user_message=user_message,
            state=state,
            recent_dialogue=tuple(recent_dialogue)[:_RECENT_DIALOGUE_MAX],
        )
        message = normalize_text(planning_request.user_message)
        folded = fold_text(message)
        conversation_state = planning_request.conversation_state
        variants = query_variants(message)

        if _asks_table_of_contents(folded):
            return _toc_result(message, conversation_state, variants)
        if _asks_navigation(folded):
            return _navigation_result(message, conversation_state, variants)
        if _asks_compare(folded):
            return _compare_result(message, conversation_state, variants)
        if _asks_catalogue_list(folded):
            return _planned_result(
                message,
                variants,
                status=STATUS_PLANNED,
                reason_code=REASON_CATALOG_LIST,
                intent=BiblioDialogueIntent(INTENT_LIST_CATALOG, query_kind="list_catalog"),
                plan=BiblioLibrarianPlan(
                    intent=INTENT_LIST_CATALOG,
                    answer_mode="tool",
                    tool_calls=(
                        BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_LIST,
                            params={"limit": 100, "offset": 0},
                            method="GET",
                        ),
                    ),
                ),
                state=conversation_state,
            )
        if _mentions_current_document(folded):
            return _current_document_search_result(message, conversation_state, variants)
        if _asks_thematic_search(folded):
            return _theme_search_result(message, conversation_state, variants)

        return _planned_result(
            message,
            variants,
            status=STATUS_FALLBACK_DETERMINISTIC,
            reason_code=REASON_FALLBACK,
            intent=BiblioDialogueIntent(INTENT_FALLBACK),
            plan=BiblioLibrarianPlan(fallback_reason=REASON_FALLBACK),
            state=conversation_state,
        )


def plan_biblio_dialogue(
    user_message: str,
    *,
    state: BiblioConversationState | Mapping[str, Any] | None = None,
    recent_dialogue: Sequence[Mapping[str, Any]] = (),
) -> BiblioDialoguePlanningResult:
    return BiblioDialoguePlanner().plan(user_message=user_message, state=state, recent_dialogue=recent_dialogue)


def _toc_result(
    message: str,
    state: BiblioConversationState,
    variants: Sequence[str],
) -> BiblioDialoguePlanningResult:
    doc_id = _current_document_id(state)
    if not doc_id:
        return _clarification_result(
            message,
            variants,
            reason_code=REASON_CURRENT_DOCUMENT_MISSING,
            intent=BiblioDialogueIntent(
                INTENT_SHOW_TABLE_OF_CONTENTS,
                query_kind="show_table_of_contents",
                state_required=True,
            ),
            state=state,
        )
    return _planned_result(
        message,
        variants,
        status=STATUS_PLANNED,
        reason_code=REASON_TABLE_OF_CONTENTS,
        intent=BiblioDialogueIntent(
            INTENT_SHOW_TABLE_OF_CONTENTS,
            query_kind="show_table_of_contents",
            state_required=True,
        ),
        plan=BiblioLibrarianPlan(
            intent=INTENT_SHOW_TABLE_OF_CONTENTS,
            answer_mode="tool",
            tool_calls=(
                BiblioLibrarianToolCall(
                    tool_name=tools.TOOL_DOCUMENT_TOC,
                    params={"document_id": doc_id, "limit": 500, "offset": 0},
                    method="GET",
                ),
            ),
        ),
        state=state,
        current_document_used=True,
    )


def _navigation_result(
    message: str,
    state: BiblioConversationState,
    variants: Sequence[str],
) -> BiblioDialoguePlanningResult:
    reason = REASON_NAVIGATION_TOOL_MISSING if state.present else REASON_CURRENT_DOCUMENT_MISSING
    return _planned_result(
        message,
        variants,
        status=STATUS_UNSUPPORTED_MISSING_TOOL if state.present else STATUS_NEEDS_CLARIFICATION,
        reason_code=reason,
        intent=BiblioDialogueIntent(INTENT_NAVIGATE, state_required=True, tool_required="navigation"),
        plan=BiblioLibrarianPlan(intent="clarify", answer_mode="clarify", fallback_reason=reason),
        state=state,
        tool_required="navigation",
    )


def _compare_result(
    message: str,
    state: BiblioConversationState,
    variants: Sequence[str],
) -> BiblioDialoguePlanningResult:
    usable = tuple(candidate for candidate in state.last_candidates if _candidate_has_context_position(candidate))[:2]
    if len(usable) < 2:
        reason = REASON_CANDIDATES_MISSING if len(state.last_candidates) < 2 else REASON_CANDIDATES_INCOMPLETE
        return _clarification_result(
            message,
            variants,
            reason_code=reason,
            intent=BiblioDialogueIntent(INTENT_COMPARE_PASSAGES, query_kind="compare_passages", state_required=True),
            state=state,
        )
    calls = tuple(_context_call_from_candidate(candidate) for candidate in usable)
    return _planned_result(
        message,
        variants,
        status=STATUS_PLANNED,
        reason_code=REASON_COMPARE_CANDIDATES,
        intent=BiblioDialogueIntent(INTENT_COMPARE_PASSAGES, query_kind="compare_passages", state_required=True),
        plan=BiblioLibrarianPlan(intent=INTENT_COMPARE_PASSAGES, answer_mode="tool", tool_calls=calls),
        state=state,
        candidate_count=len(state.last_candidates),
    )


def _current_document_search_result(
    message: str,
    state: BiblioConversationState,
    variants: Sequence[str],
) -> BiblioDialoguePlanningResult:
    doc_id = _current_document_id(state)
    if not doc_id:
        return _clarification_result(
            message,
            variants,
            reason_code=REASON_CURRENT_DOCUMENT_MISSING,
            intent=BiblioDialogueIntent(INTENT_SEARCH_CURRENT_DOCUMENT, query_kind="search_catalog", state_required=True),
            state=state,
        )
    return _planned_result(
        message,
        variants,
        status=STATUS_PLANNED,
        reason_code=REASON_CURRENT_DOCUMENT_SEARCH,
        intent=BiblioDialogueIntent(INTENT_SEARCH_CURRENT_DOCUMENT, query_kind="search_catalog", state_required=True),
        plan=BiblioLibrarianPlan(
            intent=INTENT_SEARCH_CURRENT_DOCUMENT,
            answer_mode="tool",
            tool_calls=(
                BiblioLibrarianToolCall(
                    tool_name=tools.TOOL_DOCUMENT_OPEN_SUMMARY,
                    params={"document_id": doc_id},
                    method="GET",
                ),
                BiblioLibrarianToolCall(
                    tool_name=tools.TOOL_CATALOG_SEARCH,
                    params={"query": _search_query(message), "limit": 20},
                    method="GET",
                ),
            ),
        ),
        state=state,
        current_document_used=True,
    )


def _theme_search_result(
    message: str,
    state: BiblioConversationState,
    variants: Sequence[str],
) -> BiblioDialoguePlanningResult:
    return _planned_result(
        message,
        variants,
        status=STATUS_PLANNED,
        reason_code=REASON_THEME_SEARCH,
        intent=BiblioDialogueIntent(INTENT_SEARCH_PASSAGE, query_kind="search_catalog"),
        plan=BiblioLibrarianPlan(
            intent=INTENT_SEARCH_PASSAGE,
            answer_mode="tool",
            tool_calls=(
                BiblioLibrarianToolCall(
                    tool_name=tools.TOOL_CATALOG_SEARCH,
                    params={"query": _search_query(message), "limit": 20},
                    method="GET",
                ),
            ),
        ),
        state=state,
    )


def _planned_result(
    message: str,
    variants: Sequence[str],
    *,
    status: str,
    reason_code: str,
    intent: BiblioDialogueIntent,
    plan: BiblioLibrarianPlan,
    state: BiblioConversationState,
    current_document_used: bool = False,
    candidate_count: int | None = None,
    tool_required: str = "",
) -> BiblioDialoguePlanningResult:
    return BiblioDialoguePlanningResult(
        status=status,
        reason_code=reason_code,
        intent=intent,
        plan=plan,
        state_present=state.present,
        current_document_used=current_document_used,
        candidate_count=len(state.last_candidates) if candidate_count is None else candidate_count,
        tool_required=tool_required,
        user_message_signal=compact_text_signal(message),
        query_variant_count=len(variants),
        query_variant_hashes=tuple(_sha256_12(variant) for variant in variants[:8]),
    )


def _clarification_result(
    message: str,
    variants: Sequence[str],
    *,
    reason_code: str,
    intent: BiblioDialogueIntent,
    state: BiblioConversationState,
) -> BiblioDialoguePlanningResult:
    return _planned_result(
        message,
        variants,
        status=STATUS_NEEDS_CLARIFICATION,
        reason_code=reason_code,
        intent=intent,
        plan=BiblioLibrarianPlan(intent="clarify", answer_mode="clarify", fallback_reason=reason_code),
        state=state,
    )


def _asks_catalogue_list(folded: str) -> bool:
    if re.search(r"\b(liste|lister|affiche|montre|voir|vois)\b", folded) and re.search(
        r"\b(catalogue|bibliotheque|biblio|ouvrages|livres|documents)\b",
        folded,
    ):
        return True
    return bool(re.search(r"\b(quels|combien)\b.*\b(ouvrages|livres|documents)\b", folded))


def _asks_table_of_contents(folded: str) -> bool:
    return bool("table des matieres" in folded or "sommaire" in folded)


def _asks_navigation(folded: str) -> bool:
    if re.search(r"\b(page|passage|extrait)\s+(suivante|suivant|precedente|precedent)\b", folded):
        return True
    return bool(re.search(r"\b(continue|continuer|la suite|suite|poursuis|apres|avant)\b", folded))


def _asks_compare(folded: str) -> bool:
    return bool(re.search(r"\b(compare|comparer|difference|differences)\b", folded))


def _mentions_current_document(folded: str) -> bool:
    return bool(_CURRENT_DOCUMENT_RE.search(folded) and re.search(r"\b(livre|ouvrage|document|volume)\b", folded))


def _asks_thematic_search(folded: str) -> bool:
    if re.search(r"\b(cherche|chercher|trouve|trouver|retrouve|sort|sortir)\b", folded):
        return True
    return bool(re.search(r"\b(moment|passage|extrait)\b.*\b(parle|question|theme|sujet|sur)\b", folded))


def _current_document_id(state: BiblioConversationState) -> str:
    return str(state.current_document.get("document_id") or "").strip()


def _search_query(message: str) -> str:
    variants = query_variants(message, max_variants=2)
    return variants[0] if variants else normalize_text(message)


def _candidate_has_context_position(candidate: Mapping[str, Any]) -> bool:
    if not str(candidate.get("document_id") or "").strip():
        return False
    if candidate.get("paragraph_id") is not None:
        return True
    return candidate.get("page_no") is not None and candidate.get("para_no") is not None


def _context_call_from_candidate(candidate: Mapping[str, Any]) -> BiblioLibrarianToolCall:
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


def _sha256_12(value: Any) -> str:
    return hashlib.sha256(str(value or "").encode("utf-8")).hexdigest()[:12]
