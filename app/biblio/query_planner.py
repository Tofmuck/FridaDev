"""Structured query planning for the native Biblio librarian lane.

The planner is deliberately deterministic.  It turns a user message into a
small internal plan, while observability only exposes lengths and hashes of
raw textual signals.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any


INTENT_NONE = "none"
INTENT_LIST_CATALOG = "list_catalog"
INTENT_SEARCH_CATALOG = "search_catalog"
INTENT_RESOLVE_WORK = "resolve_work"
INTENT_EXTRACT_PASSAGE = "extract_passage"
INTENT_EXTRACT_RANGE = "extract_range"
INTENT_CLARIFY_AMBIGUOUS = "clarify_ambiguous"

REASON_NO_SIGNAL = "biblio_no_bibliographic_signal"
REASON_LIST_CATALOG = "biblio_list_catalog_requested"
REASON_SEARCH_CATALOG = "biblio_search_catalog_requested"
REASON_WORK_REQUESTED = "biblio_work_requested"
REASON_PASSAGE_REQUESTED = "biblio_passage_requested"
REASON_RANGE_REQUESTED = "biblio_range_requested"
REASON_CLARIFY_DOCUMENT_REQUIRED = "biblio_clarify_document_required"
REASON_ADOBE_TOPIC_IGNORED = "biblio_adobe_topic_ignored"

_LOCATOR_RE = re.compile(r"\b([1-9][0-9]{1,3}[a-e])\b", re.IGNORECASE)
_RANGE_RE = re.compile(
    r"\b([1-9][0-9]{1,3}[a-e])\s*(?:->|-->|-|a|à)\s*([1-9][0-9]{1,3}[a-e])\b",
    re.IGNORECASE,
)
_DOC_ID_RE = re.compile(
    r"\b(?:catalogue_doc|document_id|doc_id)\s*[:=]\s*([A-Za-z0-9][A-Za-z0-9_.:-]{2,127})",
    re.IGNORECASE,
)
_AUTHOR_RE = re.compile(r"\bauteur\s*[:=]\s*([^,.;?!\n]{2,80})", re.IGNORECASE)
_QUOTED_RE = re.compile(r"[\"'“”]([^\"'“”\n]{2,120})[\"'“”]")
_TITLE_FIELD_RE = re.compile(
    r"\b(?:titre|ouvrage|document)\s*[:=]\s*([^,.;?!\n]{2,120})",
    re.IGNORECASE,
)
_PASSAGE_WORK_RE = re.compile(
    r"\b(?:extrait|passage|stephanus)\b(?:\s+\w+){0,4}?\s+"
    r"(?:du|de la|de l['’]?|de l\s+|d['’])\s+([^,.;?!\n]{2,120})",
    re.IGNORECASE,
)
_WORK_OF_CORPUS_RE = re.compile(
    r"^\s*(.+?)\s+(?:de|du|des|d['’])\s+([A-ZÀ-ÖØ-Þ][^,.;?!\n]{1,80})\s*$"
)
_IN_CORPUS_RE = re.compile(
    r"\b(?:dans|chez)\s+(?:les\s+)?(?:oeuvres|œuvres|ouvrages|textes|corpus)?"
    r"(?:\s+completes|\s+complètes)?(?:\s+de)?\s+([^,.;?!\n]{2,80})",
    re.IGNORECASE,
)
_SEARCH_AFTER_RE = re.compile(
    r"\b(?:cherche|recherche|trouve|consulte|sortir|sors|voir)\b(?:\s+dans\s+(?:la\s+)?(?:bibliotheque|bibliothèque|biblio|catalogue))?\s+([^,.;?!\n]{2,120})",
    re.IGNORECASE,
)

_SURFACE_WORDS = {
    "bibliotheque",
    "biblio",
    "catalogue",
    "livre",
    "livres",
    "ouvrage",
    "ouvrages",
    "document",
    "documents",
}
_FUNCTION_WORDS = {
    "a",
    "au",
    "aux",
    "dans",
    "de",
    "des",
    "du",
    "l",
    "la",
    "le",
    "les",
    "un",
    "une",
}


@dataclass(frozen=True)
class BiblioQueryPlan:
    should_consult: bool
    intent: str
    reason_code: str
    query_kind: str
    document_id: str = ""
    catalogue_query: str = ""
    document_title: str = ""
    work_title: str = ""
    author: str = ""
    locator: str = ""
    locator_end: str = ""
    locator_kind: str = "stephanus"
    limit: int = 5

    def to_observability(self) -> dict[str, Any]:
        return {
            "intent": self.intent,
            "reason_code": self.reason_code,
            "query_kind": self.query_kind,
            "should_consult": self.should_consult,
            "has_document_id": bool(self.document_id),
            "catalogue_query": _compact_text_signal(self.catalogue_query),
            "document_title": _compact_text_signal(self.document_title),
            "work_title": _compact_text_signal(self.work_title),
            "author": _compact_text_signal(self.author),
            "locator": _compact_text_signal(self.locator),
            "locator_end": _compact_text_signal(self.locator_end),
            "locator_kind": self.locator_kind if self.locator_kind in {"stephanus"} else "custom",
            "limit": self.limit,
        }


def plan_biblio_query(user_msg: str) -> BiblioQueryPlan:
    text = str(user_msg or "").strip()
    if not text:
        return _none(REASON_NO_SIGNAL)
    folded = _fold(text)
    if "document actif" in folded or "documents actifs" in folded:
        return _none(REASON_NO_SIGNAL)
    if _adobe_topic_without_biblio_signal(folded):
        return _none(REASON_ADOBE_TOPIC_IGNORED)

    document_id = _extract_document_id(text)
    locator, locator_end = _extract_locator_pair(folded)
    author = _extract_author(text)
    work_title, document_title = _extract_work_and_document_titles(text, folded, locator=locator)

    if locator and not (document_id or work_title or document_title or author):
        return BiblioQueryPlan(
            should_consult=False,
            intent=INTENT_CLARIFY_AMBIGUOUS,
            reason_code=REASON_CLARIFY_DOCUMENT_REQUIRED,
            query_kind=INTENT_CLARIFY_AMBIGUOUS,
            locator=locator,
            locator_end=locator_end,
        )

    if locator and (document_id or work_title or document_title or author):
        return BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_EXTRACT_RANGE if locator_end else INTENT_EXTRACT_PASSAGE,
            reason_code=REASON_RANGE_REQUESTED if locator_end else REASON_PASSAGE_REQUESTED,
            query_kind=INTENT_EXTRACT_RANGE if locator_end else INTENT_EXTRACT_PASSAGE,
            document_id=document_id,
            document_title=document_title,
            work_title=work_title,
            author=author,
            catalogue_query=_first_non_empty(document_title, author, work_title),
            locator=locator,
            locator_end=locator_end,
        )

    if _is_catalogue_list_request(folded):
        return BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_LIST_CATALOG,
            reason_code=REASON_LIST_CATALOG,
            query_kind=INTENT_LIST_CATALOG,
            limit=5,
        )

    search_query = _extract_search_query(text, folded)
    if search_query:
        return BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_SEARCH_CATALOG,
            reason_code=REASON_SEARCH_CATALOG,
            query_kind=INTENT_SEARCH_CATALOG,
            catalogue_query=search_query,
            work_title=search_query,
            limit=8,
        )

    if _is_generic_catalogue_consultation(folded):
        return BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_LIST_CATALOG,
            reason_code=REASON_LIST_CATALOG,
            query_kind=INTENT_LIST_CATALOG,
            limit=5,
        )

    if work_title or document_title or author or document_id:
        return BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_RESOLVE_WORK,
            reason_code=REASON_WORK_REQUESTED,
            query_kind=INTENT_RESOLVE_WORK,
            document_id=document_id,
            document_title=document_title,
            work_title=work_title,
            author=author,
            catalogue_query=_first_non_empty(document_title, author, work_title),
            limit=8,
        )

    return _none(REASON_NO_SIGNAL)


def _none(reason_code: str) -> BiblioQueryPlan:
    return BiblioQueryPlan(
        should_consult=False,
        intent=INTENT_NONE,
        reason_code=reason_code,
        query_kind="no_signal",
    )


def _extract_document_id(text: str) -> str:
    match = _DOC_ID_RE.search(text)
    return match.group(1).strip() if match else ""


def _extract_locator_pair(folded_text: str) -> tuple[str, str]:
    range_match = _RANGE_RE.search(folded_text)
    if range_match:
        return range_match.group(1).lower(), range_match.group(2).lower()
    locator_match = _LOCATOR_RE.search(folded_text)
    if locator_match:
        return locator_match.group(1).lower(), ""
    return "", ""


def _extract_author(text: str) -> str:
    match = _AUTHOR_RE.search(text)
    if not match:
        return ""
    return _clean_title(match.group(1), locator="") if _usable_title(match.group(1)) else ""


def _extract_work_and_document_titles(text: str, folded: str, *, locator: str) -> tuple[str, str]:
    explicit_title = _extract_explicit_title(text, locator=locator)
    if explicit_title:
        return "", explicit_title

    passage_title = _extract_passage_title(text, locator=locator)
    if passage_title:
        work, document = _split_work_of_corpus(passage_title)
        return work or passage_title, document

    if locator:
        after = _title_after_locator(text, locator)
        if after:
            return "", after

        before = _title_before_locator(text, locator)
        if before:
            work, document = _split_work_of_corpus(before)
            if work or document:
                return work, document
            return "", before

    document = _extract_in_corpus_title(text, locator=locator)
    if document and not _is_surface_only(document):
        return "", document

    if _has_biblio_catalogue_cue(folded):
        query = _extract_search_query(text, folded)
        if query and not _is_surface_only(query):
            return query, ""

    return "", ""


def _extract_explicit_title(text: str, *, locator: str) -> str:
    for regex in (_TITLE_FIELD_RE, _QUOTED_RE):
        match = regex.search(text)
        if not match:
            continue
        candidate = _clean_title(match.group(1), locator=locator)
        if _usable_title(candidate):
            return candidate
    return ""


def _extract_passage_title(text: str, *, locator: str) -> str:
    match = _PASSAGE_WORK_RE.search(text)
    if not match:
        return ""
    candidate = _clean_title(match.group(1), locator=locator)
    return candidate if _usable_title(candidate) else ""


def _title_before_locator(text: str, locator: str) -> str:
    index = _fold(text).find(str(locator or "").lower())
    if index <= 0:
        return ""
    prefix = text[:index]
    prefix = re.sub(
        r"\b(?:on\s+va\s+dire|passage|extrait|stephanus|cherche|recherche|consulte|trouve|sortir|sors|voir|donne|balances?|ici|moi|me|tu|peux|peux-tu)\b",
        " ",
        prefix,
        flags=re.IGNORECASE,
    )
    candidate = _clean_title(prefix, locator=locator)
    return candidate if _usable_title(candidate) else ""


def _title_after_locator(text: str, locator: str) -> str:
    match = re.search(
        rf"\b{re.escape(locator)}\b\s+(?:de\s+la|de\s+l['’]?|d['’]|du|des|de|chez|dans)\s+([^,.;?!\n]{{2,120}})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    candidate = _clean_title(match.group(1), locator=locator)
    return candidate if _usable_title(candidate) else ""


def _extract_in_corpus_title(text: str, *, locator: str) -> str:
    candidates: list[str] = []
    for match in _IN_CORPUS_RE.finditer(text):
        candidates.append(match.group(1))
    for raw in candidates:
        candidate = _clean_title(raw, locator=locator)
        if _usable_title(candidate):
            return candidate
    return ""


def _extract_search_query(text: str, folded: str) -> str:
    if _is_catalogue_list_request(folded):
        return ""
    for match in _SEARCH_AFTER_RE.finditer(text):
        candidate = _clean_title(match.group(1), locator="")
        if _usable_title(candidate) and not _is_surface_only(candidate) and not _is_vague_book_query(candidate, folded):
            return candidate
    if _has_biblio_catalogue_cue(folded):
        candidate = re.sub(
            r"\b(?:dans|la|le|les|un|une|bibliotheque|bibliothèque|biblio|catalogue|cherche|recherche|trouve|consulte|voir)\b",
            " ",
            text,
            flags=re.IGNORECASE,
        )
        candidate = _clean_title(candidate, locator="")
        if _usable_title(candidate) and not _is_surface_only(candidate) and not _is_vague_book_query(candidate, folded):
            return candidate
    return ""


def _split_work_of_corpus(value: str) -> tuple[str, str]:
    candidate = str(value or "").strip()
    match = _WORK_OF_CORPUS_RE.match(candidate)
    if not match:
        return candidate if _usable_title(candidate) else "", ""
    work = _clean_title(match.group(1), locator="")
    document = _clean_title(match.group(2), locator="")
    return (
        work if _usable_title(work) else "",
        document if _usable_title(document) else "",
    )


def _clean_title(value: str, *, locator: str) -> str:
    text = str(value or "").strip(" \t\r\n'\"“”")
    if locator:
        text = re.sub(re.escape(locator), " ", text, flags=re.IGNORECASE)
    text = _RANGE_RE.sub(" ", text)
    text = _LOCATOR_RE.sub(" ", text)
    text = re.sub(
        r"\s+(?:dans\s+|du\s+|de\s+)?(?:le\s+|la\s+)?(?:catalogue|bibliotheque|bibliothèque|biblio)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^l(?:['’]\s*|\s+)", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(
        r"^(?:de la|de l['’]?|d['’]|du|des|le|la|les|un|une)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:passage|extrait|stephanus|page|paragraphe|dans|chez|catalogue|bibliotheque|bibliothèque|biblio)\b",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"\s*(?:->|-->)\s*", " ", text)
    text = re.sub(r"\s+", " ", text).strip(" ,;:-?.!")
    return text[:120]


def _usable_title(candidate: str) -> bool:
    text = str(candidate or "").strip()
    if len(text) < 2:
        return False
    folded = _fold(text)
    if folded in _SURFACE_WORDS or folded in _FUNCTION_WORDS:
        return False
    if re.fullmatch(r"(?:mon|ma|mes|ton|ta|tes|son|sa|ses|ce|cet|cette)?\s*(?:livre|ouvrage|document)s?", folded):
        return False
    if folded in {"adobe", "photoshop", "illustrator", "web"}:
        return False
    return True


def _is_surface_only(value: str) -> bool:
    words = {_fold(part) for part in re.findall(r"\w+", str(value or ""))}
    return bool(words) and all(word in _SURFACE_WORDS or word in _FUNCTION_WORDS for word in words)


def _is_vague_book_query(value: str, folded_message: str) -> bool:
    folded_value = _fold(value)
    has_surface_word = any(word in folded_value.split() for word in ("livre", "livres", "ouvrage", "ouvrages"))
    if not has_surface_word:
        return False
    return not _has_biblio_catalogue_cue(folded_message)


def _is_catalogue_list_request(folded: str) -> bool:
    if re.search(r"\b(?:premiers?|liste|lister|voir)\b.*\b(?:ouvrages?|livres?|documents?|catalogue)\b", folded):
        return True
    if re.search(r"\b(?:ouvrages?|livres?|documents?)\b.*\b(?:premiers?|liste|lister)\b", folded):
        return True
    return False


def _is_generic_catalogue_consultation(folded: str) -> bool:
    return bool(
        re.search(r"\b(?:cherche|recherche|consulte|voir|regarde)\b.*\b(?:bibliotheque|biblio|catalogue)\b", folded)
    )


def _has_biblio_catalogue_cue(folded: str) -> bool:
    return any(cue in folded for cue in ("bibliotheque", "biblio", "catalogue"))


def _adobe_topic_without_biblio_signal(folded: str) -> bool:
    if not any(term in folded for term in ("adobe", "photoshop", "illustrator")):
        return False
    return not _has_biblio_catalogue_cue(folded)


def _first_non_empty(*values: str) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def _compact_text_signal(value: str) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"present": False, "length": 0, "hash": ""}
    return {
        "present": True,
        "length": len(text),
        "hash": hashlib.sha256(text.encode("utf-8")).hexdigest()[:12],
    }


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()
