"""Runtime handoff for dialogue-level Biblio requests.

This module keeps residual dialogue recognition and execution out of the
top-level chat runtime:

- navigation dialogue planning and named-document page recovery;
- state-followup clarification detection for cases still outside the bounded
  dialogue planner.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping, Sequence

from . import document_resolver
from .conversation_followup import (
    BiblioFollowupRequest,
    BiblioStateClarification,
    clarification_for_followup,
    detect_followup_request,
)
from .conversation_state import BiblioConversationState
from . import librarian_dialogue_intents
from . import librarian_dialogue_navigation
from . import librarian_dialogue_planner
from . import librarian_planner
from . import librarian_tools
from .librarian_navigation_runtime import run_biblio_navigation_plan


@dataclass(frozen=True)
class BiblioDialogueFollowupClarification:
    followup: BiblioFollowupRequest
    clarification: BiblioStateClarification


def detect_biblio_followup_clarification(
    *,
    enabled: bool,
    user_msg: str,
    state: BiblioConversationState,
) -> BiblioDialogueFollowupClarification | None:
    if not enabled:
        return None
    followup = detect_followup_request(user_msg)
    if not followup.present:
        return None
    clarification = clarification_for_followup(state, followup)
    if clarification is None:
        return None
    return BiblioDialogueFollowupClarification(
        followup=followup,
        clarification=clarification,
    )


def run_navigation_dialogue_plan(
    *,
    enabled: bool,
    user_msg: str,
    state: BiblioConversationState,
    recent_dialogue: Sequence[Mapping[str, Any]],
    client_factory: Any,
    config_module: Any,
) -> Any:
    if not enabled:
        return None
    dialogue = librarian_dialogue_planner.plan_biblio_dialogue(
        user_msg,
        state=state,
        recent_dialogue=recent_dialogue,
    )
    if dialogue.intent.intent != librarian_dialogue_planner.INTENT_NAVIGATE:
        return None
    if dialogue.status not in {
        librarian_dialogue_planner.STATUS_PLANNED,
        librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
        librarian_dialogue_planner.STATUS_UNSUPPORTED_MISSING_TOOL,
    }:
        return None
    if (
        dialogue.status == librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION
        and dialogue.reason_code == librarian_dialogue_planner.REASON_NAVIGATION_EXPLICIT_REFERENCE_UNRESOLVED
    ):
        resolved = _resolve_named_document_page_navigation(
            dialogue=dialogue,
            user_msg=user_msg,
            state=state,
            client_factory=client_factory,
            config_module=config_module,
        )
        if resolved is not None:
            resolved_dialogue, client = resolved
            if resolved_dialogue.status == librarian_dialogue_planner.STATUS_PLANNED and client is not None:
                return run_biblio_navigation_plan(client, resolved_dialogue)
            return run_biblio_navigation_plan(None, resolved_dialogue)
    if dialogue.status == librarian_dialogue_planner.STATUS_PLANNED:
        client = client_factory(config_module=config_module)
        return run_biblio_navigation_plan(client, dialogue)
    return run_biblio_navigation_plan(None, dialogue)


def _resolve_named_document_page_navigation(
    *,
    dialogue: librarian_dialogue_planner.BiblioDialoguePlanningResult,
    user_msg: str,
    state: BiblioConversationState,
    client_factory: Any,
    config_module: Any,
) -> tuple[librarian_dialogue_planner.BiblioDialoguePlanningResult, Any | None] | None:
    kind = str(dialogue.intent.scope_mode or "")
    if not librarian_dialogue_navigation.can_plan_page_navigation(kind):
        return None
    target = librarian_dialogue_navigation.explicit_reference_target(user_msg)
    if not target:
        return None
    client = client_factory(config_module=config_module)
    resolution = document_resolver.BiblioDocumentResolver(client).resolve(
        document_resolver.BiblioResolveRequest(title=target)
    )
    if resolution.status != document_resolver.STATUS_RESOLVED or resolution.document is None:
        return None
    resolved_dialogue = _named_document_page_dialogue(
        dialogue=dialogue,
        user_msg=user_msg,
        state=state,
        document_id=resolution.document.document_id,
        doc_id_short=resolution.document.doc_id_short,
    )
    return resolved_dialogue, client


def _named_document_page_dialogue(
    *,
    dialogue: librarian_dialogue_planner.BiblioDialoguePlanningResult,
    user_msg: str,
    state: BiblioConversationState,
    document_id: str,
    doc_id_short: str,
) -> librarian_dialogue_planner.BiblioDialoguePlanningResult:
    kind = str(dialogue.intent.scope_mode or "")
    tool_required = librarian_dialogue_navigation.tool_required_for_navigation(kind)
    intent = librarian_dialogue_planner.BiblioDialogueIntent(
        librarian_dialogue_planner.INTENT_NAVIGATE,
        query_kind="page_read",
        state_required=True,
        tool_required=tool_required,
        scope_mode=kind,
    )
    resolved_state = _state_for_navigation_document(
        state,
        document_id=document_id,
        doc_id_short=doc_id_short,
    )
    folded = librarian_dialogue_intents.fold_message(
        librarian_dialogue_intents.normalize_message(user_msg)
    )
    page_numbers = librarian_dialogue_navigation.page_numbers_for_navigation(
        kind,
        resolved_state,
        folded,
    )
    if (
        kind == librarian_dialogue_navigation.NAVIGATION_PAGE_EXPLICIT
        and librarian_dialogue_navigation.page_request(folded) is not None
        and not page_numbers
    ):
        return replace(
            dialogue,
            status=librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
            reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_RANGE_TOO_WIDE,
            intent=intent,
            plan=librarian_planner.BiblioLibrarianPlan(
                intent="clarify",
                answer_mode="clarify",
                fallback_reason=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_RANGE_TOO_WIDE,
            ),
            state_present=resolved_state.present,
            current_document_used=False,
            tool_required=tool_required,
        )
    if not page_numbers:
        return replace(
            dialogue,
            status=librarian_dialogue_planner.STATUS_NEEDS_CLARIFICATION,
            reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_ANCHOR_MISSING,
            intent=intent,
            plan=librarian_planner.BiblioLibrarianPlan(
                intent="clarify",
                answer_mode="clarify",
                fallback_reason=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_ANCHOR_MISSING,
            ),
            state_present=resolved_state.present,
            current_document_used=False,
            tool_required=tool_required,
        )
    tool_calls = tuple(
        librarian_planner.BiblioLibrarianToolCall(
            tool_name=librarian_tools.TOOL_PAGE_READ,
            params={"document_id": document_id, "page_no": page_no},
            method="GET",
        )
        for page_no in page_numbers
    )
    return replace(
        dialogue,
        status=librarian_dialogue_planner.STATUS_PLANNED,
        reason_code=librarian_dialogue_planner.REASON_NAVIGATION_PAGE_READ,
        intent=intent,
        plan=librarian_planner.BiblioLibrarianPlan(
            intent=librarian_dialogue_planner.INTENT_NAVIGATE,
            answer_mode="tool",
            tool_calls=tool_calls,
        ),
        state_present=resolved_state.present,
        current_document_used=_navigation_state_matches_document(state, document_id),
        tool_required=tool_required,
    )


def _state_for_navigation_document(
    state: BiblioConversationState,
    *,
    document_id: str,
    doc_id_short: str,
) -> BiblioConversationState:
    if _navigation_state_matches_document(state, document_id):
        return replace(
            state,
            current_document={"document_id": document_id, "doc_id_short": doc_id_short},
        )
    return replace(
        state,
        current_document={"document_id": document_id, "doc_id_short": doc_id_short},
        page_no=None,
        para_no=None,
        paragraph_id=None,
        last_result={},
        last_candidates=(),
        last_ambiguity={},
    )


def _navigation_state_matches_document(state: BiblioConversationState, document_id: str) -> bool:
    anchored = str(state.last_result.get("document_id") or state.current_document.get("document_id") or "").strip()
    return bool(anchored) and anchored == str(document_id or "").strip()
