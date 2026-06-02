"""Navigation classification for Biblio dialogue planning."""

from __future__ import annotations

import re
from typing import Any

from .conversation_state import BiblioConversationState
from . import librarian_dialogue_references as references


NAVIGATION_AROUND_PASSAGE = "around_passage"
NAVIGATION_NEARBY_PASSAGE = "nearby_passage"
NAVIGATION_PAGE_EXPLICIT = "page_explicit"
NAVIGATION_PAGE_PREVIOUS = "page_previous"
NAVIGATION_PAGE_NEXT = "page_next"
NAVIGATION_UP = "up"
NAVIGATION_DOWN = "down"
NAVIGATION_CONTINUE = "continue"
NAVIGATION_GENERIC = "generic"
PAGE_RANGE_MAX_PAGES = 5

_SEARCH_VERB_RE = re.compile(r"\b(cherche|chercher|trouve|trouver|retrouve|retrouver|sort|sortir)\b")
_NEARBY_TOPIC_RE = re.compile(
    r"\b(?:dans|chez|sur|de|du|des)\s+(?:(?:le|la|l['’]?|les|un|une)\s*)?([a-z0-9]{3,})\b"
    r"|\bd['’]\s*([a-z0-9]{3,})\b"
)
_NEARBY_ANAPHORIC_RE = re.compile(r"\bautre\s+(passage|extrait)\b.*\b(proche|voisin|voisine)\b")
_PAGE_REQUEST_RE = re.compile(
    r"\bpages?\s+(\d{1,5})(?:\s*(?:a|à|-|au)\s*(?:pages?\s+)?(\d{1,5}))?\b"
)
_REFERENCE_RE = re.compile(
    r"\b(?:dans|chez|de|du|des)\s+(?:(?:le|la|l['’]?|les|un|une)\s*)?([a-z0-9]{3,})\b"
    r"|\bd['’]\s*([a-z0-9]{3,})\b"
)
_REFERENCE_STOPWORDS = frozenset(
    {
        "autour",
        "celle",
        "celui",
        "ceci",
        "cela",
        "ces",
        "cet",
        "cette",
        "document",
        "extrait",
        "livre",
        "meme",
        "même",
        "ouvrage",
        "page",
        "passage",
        "volume",
    }
)


def is_navigation_request(folded: str) -> bool:
    return classify_navigation(folded) != NAVIGATION_GENERIC


def classify_navigation(folded: str) -> str:
    if page_request(folded) is not None:
        return NAVIGATION_PAGE_EXPLICIT
    if re.search(r"\b(continue|continuer|la suite|suite|poursuis)\b", folded):
        return NAVIGATION_CONTINUE
    if re.search(r"\b(autour|alentour)\b.*\b(passage|extrait)\b", folded):
        return NAVIGATION_AROUND_PASSAGE
    if re.search(r"\b(passage|extrait)\b.*\b(autour|alentour)\b", folded):
        return NAVIGATION_AROUND_PASSAGE
    if _is_nearby_navigation(folded):
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


def has_unresolved_explicit_reference(folded: str) -> bool:
    for match in _REFERENCE_RE.finditer(folded):
        token = _first_match_group(match)
        if token and token not in _REFERENCE_STOPWORDS:
            return True
    return False


def can_plan_context_navigation(kind: str) -> bool:
    return kind == NAVIGATION_AROUND_PASSAGE


def can_plan_page_navigation(kind: str) -> bool:
    return kind in {
        NAVIGATION_PAGE_EXPLICIT,
        NAVIGATION_PAGE_PREVIOUS,
        NAVIGATION_PAGE_NEXT,
        NAVIGATION_CONTINUE,
    }


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


def page_request(folded: str) -> tuple[int, int] | None:
    match = _PAGE_REQUEST_RE.search(folded)
    if match is None:
        return None
    start = int(match.group(1))
    end = int(match.group(2) or match.group(1))
    if start <= 0 or end <= 0:
        return None
    if end < start:
        start, end = end, start
    return start, end


def page_numbers_for_navigation(kind: str, state: BiblioConversationState, folded: str) -> tuple[int, ...]:
    if kind == NAVIGATION_PAGE_EXPLICIT:
        request = page_request(folded)
        if request is None:
            return ()
        start, end = request
        if (end - start) + 1 > PAGE_RANGE_MAX_PAGES:
            return ()
        return tuple(range(start, end + 1))
    last = getattr(state, "last_result", {}) or {}
    anchor_page = last.get("page_no") if isinstance(last, dict) else None
    if anchor_page is None:
        anchor_page = state.page_no
    if type(anchor_page) is not int or anchor_page < 1:
        return ()
    if kind == NAVIGATION_PAGE_PREVIOUS:
        return (anchor_page - 1,) if anchor_page > 1 else ()
    if kind in {NAVIGATION_PAGE_NEXT, NAVIGATION_CONTINUE}:
        return (anchor_page + 1,)
    return ()


def _is_nearby_navigation(folded: str) -> bool:
    if not re.search(r"\b(autre\s+)?(passage|extrait)\b.*\b(proche|voisin|voisine)\b", folded):
        return False
    if not _SEARCH_VERB_RE.search(folded):
        return True
    if _nearby_request_has_explicit_topic(folded):
        return False
    return bool(_NEARBY_ANAPHORIC_RE.search(folded))


def _nearby_request_has_explicit_topic(folded: str) -> bool:
    for match in _NEARBY_TOPIC_RE.finditer(folded):
        token = _first_match_group(match)
        if token and token not in _REFERENCE_STOPWORDS:
            return True
    return False


def _first_match_group(match: re.Match[str]) -> str:
    for value in match.groups():
        if value:
            return str(value).strip()
    return ""
