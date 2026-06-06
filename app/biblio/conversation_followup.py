"""Clarification policy for Biblio conversation-state follow-ups."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any

from .conversation_state import BiblioConversationState, BiblioStateTransition
from .query_normalizer import fold_text


STATUS_CLARIFICATION_REQUIRED = "clarification_required"

FOLLOWUP_CONTINUE = "continue_after"
FOLLOWUP_PREVIOUS_PAGE = "previous_page"
FOLLOWUP_NEXT_PAGE = "next_page"
FOLLOWUP_VERIFY_ORIGIN = "verify_origin"
FOLLOWUP_SELECT_CANDIDATE = "select_candidate"

REASON_STATE_NOT_REQUESTED = "biblio_state_not_requested"
REASON_STATE_MISSING = "biblio_state_missing_for_followup"
REASON_STATE_ANCHOR_MISSING = "biblio_state_anchor_missing"
REASON_NAVIGATION_NOT_IN_LOT = "biblio_state_navigation_not_in_lot"
REASON_PAGE_TOOL_UNAVAILABLE = "biblio_page_tool_unavailable"
REASON_VERIFICATION_DEFERRED = "biblio_state_verification_deferred"
REASON_AMBIGUITY_SELECTION_DEFERRED = "biblio_state_ambiguity_selection_deferred"

_TOKEN_CHARS = set("abcdefghijklmnopqrstuvwxyz0123456789_-.:/")


@dataclass(frozen=True)
class BiblioFollowupRequest:
    kind: str = ""
    reason_code: str = REASON_STATE_NOT_REQUESTED

    @property
    def present(self) -> bool:
        return bool(self.kind)

    def to_observability(self) -> dict[str, Any]:
        return {
            "present": self.present,
            "kind": _safe_token(self.kind),
            "reason_code": _safe_token(self.reason_code),
        }


@dataclass(frozen=True)
class BiblioStateClarification:
    followup_kind: str
    reason_code: str
    state_present: bool
    anchor_present: bool
    tool_required: str = ""

    @property
    def message(self) -> dict[str, Any]:
        lines = [
            "[ETAT BIBLIO]",
            "Reprise bibliotheque demandee.",
            f"Statut: {STATUS_CLARIFICATION_REQUIRED}",
            f"Raison: {self.reason_code}",
            f"Type de reprise: {self.followup_kind}",
            f"Etat disponible: {_bool_word(self.state_present)}",
            f"Ancre technique disponible: {_bool_word(self.anchor_present)}",
        ]
        if self.tool_required:
            lines.append(f"Outil requis indisponible dans ce lot: {self.tool_required}")
        lines.extend(
            [
                "Consigne: clarifier brievement au lieu d'inventer une reprise documentaire.",
                "Ne pas utiliser latest/page, latest/context, ni supposer une page ou un passage absent de l'etat.",
                "[/ETAT BIBLIO]",
            ]
        )
        return {"role": "system", "content": "\n".join(lines)}

    def to_observability(self) -> dict[str, Any]:
        content = str(self.message.get("content") or "")
        return {
            "present": True,
            "status": STATUS_CLARIFICATION_REQUIRED,
            "reason_code": self.reason_code,
            "followup_kind": self.followup_kind,
            "state_present": self.state_present,
            "anchor_present": self.anchor_present,
            "tool_required": _safe_token(self.tool_required),
            "chars": len(content),
        }


def detect_followup_request(user_msg: str) -> BiblioFollowupRequest:
    folded = fold_text(str(user_msg or ""))
    if not folded:
        return BiblioFollowupRequest()
    if re.search(r"\bpage\s+(precedente|d'avant|avant)\b", folded):
        return BiblioFollowupRequest(FOLLOWUP_PREVIOUS_PAGE, REASON_PAGE_TOOL_UNAVAILABLE)
    if re.search(r"\bpage\s+(suivante|d'apres|apres)\b", folded):
        return BiblioFollowupRequest(FOLLOWUP_NEXT_PAGE, REASON_PAGE_TOOL_UNAVAILABLE)
    if re.fullmatch(r"(continue|continuer|suite|la suite|poursuis|poursuivre)", folded):
        return BiblioFollowupRequest(FOLLOWUP_CONTINUE, REASON_NAVIGATION_NOT_IN_LOT)
    if re.search(r"\b(continue|continuer|suite|poursuis|poursuivre)\b", folded) and re.search(
        r"\b(passage|extrait|page|paragraphe)\b",
        folded,
    ):
        return BiblioFollowupRequest(FOLLOWUP_CONTINUE, REASON_NAVIGATION_NOT_IN_LOT)
    if ("ce passage" in folded or "cet extrait" in folded) and re.search(
        r"\b(vient|provient|origine|source|bien)\b",
        folded,
    ):
        return BiblioFollowupRequest(FOLLOWUP_VERIFY_ORIGIN, REASON_VERIFICATION_DEFERRED)
    if re.search(r"\b(le|la|les)?\s*(deuxieme|second|premier|troisieme)\b", folded):
        return BiblioFollowupRequest(FOLLOWUP_SELECT_CANDIDATE, REASON_AMBIGUITY_SELECTION_DEFERRED)
    return BiblioFollowupRequest()


def clarification_for_followup(
    state: BiblioConversationState,
    request: BiblioFollowupRequest,
) -> BiblioStateClarification | None:
    if not request.present:
        return None
    if not state.present:
        return BiblioStateClarification(
            followup_kind=request.kind,
            reason_code=REASON_STATE_MISSING,
            state_present=False,
            anchor_present=False,
            tool_required=_tool_for_followup(request.kind),
        )
    anchor_present = state.has_last_anchor
    reason_code = request.reason_code
    if request.kind in {FOLLOWUP_CONTINUE, FOLLOWUP_VERIFY_ORIGIN} and not anchor_present:
        reason_code = REASON_STATE_ANCHOR_MISSING
    if request.kind == FOLLOWUP_SELECT_CANDIDATE and not state.last_ambiguity:
        reason_code = REASON_STATE_ANCHOR_MISSING
    return BiblioStateClarification(
        followup_kind=request.kind,
        reason_code=reason_code,
        state_present=True,
        anchor_present=anchor_present,
        tool_required=_tool_for_followup(request.kind),
    )


def update_state_for_clarification(
    previous: BiblioConversationState,
    *,
    followup: BiblioFollowupRequest,
    clarification: BiblioStateClarification,
    conversation_id: str = "",
    now_iso: str = "",
) -> tuple[BiblioConversationState, BiblioStateTransition]:
    before = previous if isinstance(previous, BiblioConversationState) else BiblioConversationState.empty()
    after = BiblioConversationState(
        conversation_id=_safe_text(conversation_id, max_chars=160) or before.conversation_id,
        current_document=dict(before.current_document),
        current_work=dict(before.current_work),
        page_no=before.page_no,
        para_no=before.para_no,
        paragraph_id=before.paragraph_id,
        last_passage_hash=before.last_passage_hash,
        last_result=dict(before.last_result),
        last_candidates=tuple(before.last_candidates),
        last_ambiguity=dict(before.last_ambiguity),
        last_intent=_safe_token(followup.kind) or before.last_intent,
        updated_at=_safe_text(now_iso, max_chars=40) or before.updated_at,
        source_event="biblio_state_clarification",
    )
    transition = BiblioStateTransition(
        before_present=before.present,
        after_present=after.present,
        changed=before.to_dict() != after.to_dict(),
        reason_code=clarification.reason_code,
        source_event="biblio_state_clarification",
    )
    return after, transition


def _tool_for_followup(kind: str) -> str:
    if kind in {FOLLOWUP_PREVIOUS_PAGE, FOLLOWUP_NEXT_PAGE}:
        return "page"
    if kind == FOLLOWUP_CONTINUE:
        return "navigation"
    if kind == FOLLOWUP_VERIFY_ORIGIN:
        return "verification"
    if kind == FOLLOWUP_SELECT_CANDIDATE:
        return "agent_selection"
    return ""


def _safe_text(value: Any, *, max_chars: int) -> str:
    return str(value or "").strip()[:max_chars]


def _safe_token(value: Any, *, max_chars: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if any(char not in _TOKEN_CHARS for char in text):
        return f"sha256:{_sha256_12(text)}"
    return text[:max_chars]


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _bool_word(value: bool) -> str:
    return "oui" if value else "non"
