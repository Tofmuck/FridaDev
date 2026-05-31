"""Navigation classification for Biblio dialogue planning."""

from __future__ import annotations

import re
from typing import Any

from .conversation_state import BiblioConversationState
from . import librarian_dialogue_references as references


NAVIGATION_AROUND_PASSAGE = "around_passage"
NAVIGATION_NEARBY_PASSAGE = "nearby_passage"
NAVIGATION_PAGE_PREVIOUS = "page_previous"
NAVIGATION_PAGE_NEXT = "page_next"
NAVIGATION_UP = "up"
NAVIGATION_DOWN = "down"
NAVIGATION_CONTINUE = "continue"
NAVIGATION_GENERIC = "generic"


def classify_navigation(folded: str) -> str:
    if re.search(r"\b(continue|continuer|la suite|suite|poursuis)\b", folded):
        return NAVIGATION_CONTINUE
    if re.search(r"\b(autour|alentour)\b.*\b(passage|extrait)\b", folded):
        return NAVIGATION_AROUND_PASSAGE
    if re.search(r"\b(passage|extrait)\b.*\b(autour|alentour)\b", folded):
        return NAVIGATION_AROUND_PASSAGE
    if re.search(r"\b(autre\s+)?(passage|extrait)\b.*\b(proche|voisin|voisine)\b", folded):
        return NAVIGATION_NEARBY_PASSAGE
    if re.search(r"\b(page|passage|extrait)\s+(precedente|precedent|avant)\b", folded):
        return NAVIGATION_PAGE_PREVIOUS
    if re.search(r"\b(avant)\s+(le|la|l'|ce|cet|cette|celui|celle)?\s*(page|passage|extrait)\b", folded):
        return NAVIGATION_PAGE_PREVIOUS
    if re.search(r"\b(page|passage|extrait)\s+(suivante|suivant|apres)\b", folded):
        return NAVIGATION_PAGE_NEXT
    if re.search(r"\b(apres)\s+(le|la|l'|ce|cet|cette|celui|celle)?\s*(page|passage|extrait)\b", folded):
        return NAVIGATION_PAGE_NEXT
    if re.search(r"\b(plus haut|remonte|monte)\b", folded):
        return NAVIGATION_UP
    if re.search(r"\b(plus bas|descends|avance|recule)\b", folded):
        return NAVIGATION_DOWN
    return NAVIGATION_GENERIC


def can_plan_context_navigation(kind: str) -> bool:
    return kind == NAVIGATION_AROUND_PASSAGE


def tool_required_for_navigation(kind: str) -> str:
    clean = re.sub(r"[^a-z0-9_]+", "_", str(kind or NAVIGATION_GENERIC).lower()).strip("_")
    return f"navigation_{clean or NAVIGATION_GENERIC}"


def context_params_for_navigation(kind: str, state: BiblioConversationState) -> dict[str, Any]:
    if not can_plan_context_navigation(kind):
        return {}
    params = references.last_result_context_params(state)
    if params:
        params["window_chars"] = 1_400
    return params
