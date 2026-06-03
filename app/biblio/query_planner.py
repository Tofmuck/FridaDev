"""Structured query planning for the native Biblio librarian lane.

The planner is deliberately deterministic.  It turns a user message into a
small internal plan, while observability only exposes lengths and hashes of
raw textual signals.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace
from typing import Any

from .query_normalizer import (
    canonical_work_title,
    compact_text_signal,
    fold_text,
    is_known_work_alias,
    is_surface_only,
    is_usable_title,
    normalize_biblio_query,
    normalize_text,
    query_variants,
    variants_observability,
)


INTENT_NONE = "none"
INTENT_LIST_CATALOG = "list_catalog"
INTENT_OPEN_DOCUMENT = "open_document"
INTENT_SHOW_TABLE_OF_CONTENTS = "show_table_of_contents"
INTENT_SEARCH_CATALOG = "search_catalog"
INTENT_RESOLVE_WORK = "resolve_work"
INTENT_EXTRACT_PASSAGE = "extract_passage"
INTENT_EXTRACT_RANGE = "extract_range"
INTENT_CLARIFY_AMBIGUOUS = "clarify_ambiguous"

REASON_NO_SIGNAL = "biblio_no_bibliographic_signal"
REASON_LIST_CATALOG = "biblio_list_catalog_requested"
REASON_OPEN_DOCUMENT = "biblio_open_document_requested"
REASON_TABLE_OF_CONTENTS = "biblio_table_of_contents_requested"
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
    r"\b(?:cherche|chercher|recherche|trouve|trouver|consulte|sortir|sors|voir)\b(?:\s+dans\s+(?:la\s+)?(?:bibliotheque|bibliothèque|biblio|catalogue))?\s+([^,.;?!\n]{2,120})",
    re.IGNORECASE,
)
_THEMATIC_WORK_RE = re.compile(
    r"\b(?:cherche|chercher|recherche|trouve|trouver|consulte|sortir|sors|voir|donne)\b"
    r"(?:\s+\w+){0,3}?\s+dans\s+"
    r"(?:le\s+|la\s+|l['’]\s*|l\s+)?"
    r"([^,.;?!\n]{2,100}?)\s+"
    r"(?:le\s+|un\s+|du\s+)?(?:passage|extrait|endroit|moment)\s+"
    r"(?:ou|où|dans lequel|qui)\s+([^.;?!\n]{2,160})",
    re.IGNORECASE,
)
_INVERTED_THEMATIC_WORK_RE = re.compile(
    r"\b(?:cherche|chercher|recherche|trouve|trouver|consulte|sortir|sors|voir|donne)\b"
    r"(?:\s+\w+){0,4}?\s+"
    r"(?:passage|extrait|endroit|moment)\s+"
    r"(?:sur|a\s+propos\s+de|à\s+propos\s+de|concernant|au\s+sujet\s+de)\s+"
    r"([^,.;?!\n]{2,120}?)\s+dans\s+"
    r"(?:le\s+|la\s+|l['’]\s*|l\s+)?"
    r"([^,.;?!\n]{2,100})",
    re.IGNORECASE,
)

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
    theme_query: str = ""
    author: str = ""
    locator: str = ""
    locator_end: str = ""
    locator_kind: str = "stephanus"
    limit: int = 5
    catalogue_query_variants: tuple[str, ...] = field(default_factory=tuple)
    document_title_variants: tuple[str, ...] = field(default_factory=tuple)
    work_title_variants: tuple[str, ...] = field(default_factory=tuple)
    theme_query_variants: tuple[str, ...] = field(default_factory=tuple)

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
            "theme_query": _compact_text_signal(self.theme_query),
            "author": _compact_text_signal(self.author),
            "locator": _compact_text_signal(self.locator),
            "locator_end": _compact_text_signal(self.locator_end),
            "locator_kind": self.locator_kind if self.locator_kind in {"stephanus"} else "custom",
            "limit": self.limit,
            "catalogue_query_variants": variants_observability(self.catalogue_query_variants),
            "document_title_variants": variants_observability(self.document_title_variants),
            "work_title_variants": variants_observability(self.work_title_variants),
            "theme_query_variants": variants_observability(self.theme_query_variants),
        }


def plan_biblio_query(user_msg: str) -> BiblioQueryPlan:
    text = str(user_msg or "").strip()
    if not text:
        return _none(REASON_NO_SIGNAL)
    normalized = normalize_biblio_query(text)
    text = normalized.normalized
    folded = normalized.folded
    if "document actif" in folded or "documents actifs" in folded:
        return _none(REASON_NO_SIGNAL)
    if _adobe_topic_without_biblio_signal(folded):
        return _none(REASON_ADOBE_TOPIC_IGNORED)

    document_id = _extract_document_id(text)
    locator, locator_end = _extract_locator_pair(folded)
    author = _extract_author(text)
    thematic_work, theme_query = _extract_thematic_work_and_query(text)
    work_title, document_title = _extract_work_and_document_titles(
        text,
        folded,
        locator=locator,
        locator_end=locator_end,
    )
    work_title = canonical_work_title(thematic_work or work_title)

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
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_EXTRACT_RANGE if locator_end else INTENT_EXTRACT_PASSAGE,
            reason_code=REASON_RANGE_REQUESTED if locator_end else REASON_PASSAGE_REQUESTED,
            query_kind=INTENT_EXTRACT_RANGE if locator_end else INTENT_EXTRACT_PASSAGE,
            document_id=document_id,
            document_title=document_title,
            work_title=work_title,
            theme_query=theme_query,
            author=author,
            catalogue_query=_first_non_empty(document_title, author, work_title),
            locator=locator,
            locator_end=locator_end,
        ))

    toc_work_title, toc_document_title = _extract_table_of_contents_titles(text, folded)
    if toc_work_title or toc_document_title or _is_table_of_contents_request(folded):
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_SHOW_TABLE_OF_CONTENTS,
            reason_code=REASON_TABLE_OF_CONTENTS,
            query_kind=INTENT_SHOW_TABLE_OF_CONTENTS,
            document_title=toc_document_title,
            work_title=toc_work_title,
            catalogue_query=_first_non_empty(toc_document_title, toc_work_title),
            limit=8,
        ))

    open_target = _extract_open_document_target(text, folded)
    if open_target:
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_OPEN_DOCUMENT,
            reason_code=REASON_OPEN_DOCUMENT,
            query_kind=INTENT_OPEN_DOCUMENT,
            document_title=open_target,
            catalogue_query=open_target,
            limit=8,
        ))

    if _is_catalogue_list_request(folded):
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_LIST_CATALOG,
            reason_code=REASON_LIST_CATALOG,
            query_kind=INTENT_LIST_CATALOG,
            limit=100,
        ))

    search_query = theme_query or _extract_search_query(text, folded)
    if search_query:
        search_work = work_title or (canonical_work_title(search_query) if is_known_work_alias(search_query) else "")
        search_theme = theme_query or ("" if search_work else search_query)
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_SEARCH_CATALOG,
            reason_code=REASON_SEARCH_CATALOG,
            query_kind=INTENT_SEARCH_CATALOG,
            catalogue_query=search_query,
            work_title=search_work,
            theme_query=search_theme,
            limit=8,
        ))

    if _is_generic_catalogue_consultation(folded):
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_LIST_CATALOG,
            reason_code=REASON_LIST_CATALOG,
            query_kind=INTENT_LIST_CATALOG,
            limit=100,
        ))

    bare_work, bare_document = _extract_bare_work_and_document_titles(text)
    if bare_work or bare_document:
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_RESOLVE_WORK,
            reason_code=REASON_WORK_REQUESTED,
            query_kind=INTENT_RESOLVE_WORK,
            document_title=bare_document,
            work_title=canonical_work_title(bare_work),
            catalogue_query=_first_non_empty(bare_document, bare_work),
            limit=8,
        ))

    if work_title or document_title or author or document_id:
        return _with_variants(BiblioQueryPlan(
            should_consult=True,
            intent=INTENT_RESOLVE_WORK,
            reason_code=REASON_WORK_REQUESTED,
            query_kind=INTENT_RESOLVE_WORK,
            document_id=document_id,
            document_title=document_title,
            work_title=work_title,
            theme_query=theme_query,
            author=author,
            catalogue_query=_first_non_empty(document_title, author, work_title),
            limit=8,
        ))

    return _none(REASON_NO_SIGNAL)


def _none(reason_code: str) -> BiblioQueryPlan:
    return BiblioQueryPlan(
        should_consult=False,
        intent=INTENT_NONE,
        reason_code=reason_code,
        query_kind="no_signal",
    )


def _with_variants(plan: BiblioQueryPlan) -> BiblioQueryPlan:
    return replace(
        plan,
        catalogue_query_variants=query_variants(plan.catalogue_query, plan.theme_query, plan.work_title),
        document_title_variants=query_variants(plan.document_title),
        work_title_variants=query_variants(plan.work_title),
        theme_query_variants=query_variants(plan.theme_query),
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


def _extract_thematic_work_and_query(text: str) -> tuple[str, str]:
    match = _THEMATIC_WORK_RE.search(text)
    if match:
        work = _clean_title(match.group(1), locator="")
        theme = _clean_theme_query(match.group(2))
        if _usable_title(work) and _usable_title(theme):
            return canonical_work_title(work), theme

    match = _INVERTED_THEMATIC_WORK_RE.search(text)
    if not match:
        return "", ""
    theme = _clean_theme_query(match.group(1))
    work = _clean_title(match.group(2), locator="")
    if not _usable_title(work) or not _usable_title(theme):
        return "", ""
    return canonical_work_title(work), theme


def _extract_work_and_document_titles(
    text: str,
    folded: str,
    *,
    locator: str,
    locator_end: str = "",
) -> tuple[str, str]:
    explicit_title = _extract_explicit_title(text, locator=locator)
    if explicit_title:
        return "", explicit_title

    passage_title = _extract_passage_title(text, locator=locator)
    if passage_title:
        work, document = _split_work_of_corpus(passage_title)
        return work or passage_title, document

    if locator:
        after = _title_after_locator(text, locator_end or locator)
        if after:
            work, document = _split_work_of_corpus(after)
            if work and document:
                return work, document
            if document:
                return "", document
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
        if query and not _is_surface_only(query) and is_known_work_alias(query):
            return canonical_work_title(query), ""

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


def _extract_table_of_contents_titles(text: str, folded: str) -> tuple[str, str]:
    if not _is_table_of_contents_request(folded):
        return "", ""
    candidate = ""
    match = re.search(
        r"\b(?:table\s+des\s+matieres|table\s+des\s+matières|sommaire|chapitres?|oeuvres\s+internes|œuvres\s+internes)\b"
        r".{0,100}?\b(?:de|du|des|d['’])\s+([^,.;?!\n]{2,120})",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        candidate = _clean_catalogue_target(match.group(1))
    if not _usable_title(candidate):
        candidate = _extract_catalogue_named_target(text)
    if not _usable_title(candidate):
        return "", ""
    work, document = _split_work_of_corpus_for_table_of_contents(candidate)
    if work and document:
        return canonical_work_title(work), document
    return "", candidate


def _extract_open_document_target(text: str, folded: str) -> str:
    if not re.search(r"\b(?:ouvre|ouvrir|consulte|regarde)\b", folded):
        return ""
    if not _has_biblio_catalogue_cue(folded) and not re.search(r"\b(?:document|ouvrage|livre|volume)\b", folded):
        return ""
    match = re.search(
        r"\b(?:ouvre|ouvrir|consulte|regarde)\b(?:\s+le|\s+la|\s+l['’]?|\s+un|\s+une|\s+document|\s+ouvrage|\s+livre|\s+volume)*\s+([^,.;?!\n]{2,120})",
        text,
        flags=re.IGNORECASE,
    )
    if not match:
        return ""
    candidate = _clean_catalogue_target(match.group(1))
    return candidate if _usable_title(candidate) and not _is_surface_only(candidate) else ""


def _extract_catalogue_named_target(text: str) -> str:
    patterns = (
        r"\b(?:editions?|éditions?|oeuvres|œuvres|ouvrages|volumes?)\s+(?:completes|complètes)\s+de\s+([^,.;?!\n]{2,120})",
        r"\b(?:de|du|des|d['’])\s+([^,.;?!\n]{2,120})\s+(?:dans\s+la\s+)?(?:bibliotheque|bibliothèque|biblio|catalogue)",
    )
    for pattern in patterns:
        match = re.search(pattern, text, flags=re.IGNORECASE)
        if not match:
            continue
        candidate = _clean_catalogue_target(match.group(1))
        if _usable_title(candidate):
            return candidate
    return ""


def _extract_bare_work_and_document_titles(text: str) -> tuple[str, str]:
    candidate = normalize_text(text)
    candidate = re.sub(r"^(?:bon\s*,\s*|vas-y\s*,\s*)+", "", candidate, flags=re.IGNORECASE)
    candidate = re.sub(
        r"^(?:trouve|trouver|cherche|chercher|retrouve|retrouver|ouvre|ouvrir|consulte|regarde|montre)"
        r"(?:[-\s]+moi|[-\s]+nous|[-\s]+le|[-\s]+la|[-\s]+l['’]?|[-\s]+un|[-\s]+une|\s+me)?\s+",
        "",
        candidate,
        count=1,
        flags=re.IGNORECASE,
    )
    candidate = _clean_title(candidate, locator="")
    if not candidate:
        return "", ""
    work, document = _split_work_of_corpus(candidate)
    if work and not is_known_work_alias(work) and canonical_work_title(work) == work:
        return "", ""
    if work and document:
        return work, document
    return "", ""


def _clean_theme_query(value: str) -> str:
    text = normalize_text(value)
    text = re.sub(
        r"\s+(?:dans\s+|du\s+|de\s+)?(?:le\s+|la\s+)?(?:catalogue|bibliotheque|bibliothèque|biblio)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:ou|où|que|qui|dont)\s+", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(
        r"^(?:sur|a\s+propos\s+de|à\s+propos\s+de|concernant|au\s+sujet\s+de)\s+",
        "",
        text,
        count=1,
        flags=re.IGNORECASE,
    )
    text = re.sub(r"^(?:le|la|les|l['’]?|un|une)\s+", "", text, count=1, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" ,;:-?.!")
    return text[:160]


def _clean_catalogue_target(value: str) -> str:
    text = _clean_title(value, locator="")
    text = re.sub(
        r"\b(?:que\s+tu\s+as|que\s+vous\s+avez|disponibles?|dans\s+la\s+bibliotheque|dans\s+le\s+catalogue)\b.*$",
        "",
        text,
        flags=re.IGNORECASE,
    )
    text = re.sub(
        r"\b(?:editions?|éditions?|oeuvres|œuvres|ouvrages|volumes?)\s+(?:completes|complètes)\s+de\s+",
        "",
        text,
        flags=re.IGNORECASE,
    )
    return re.sub(r"\s+", " ", text).strip(" ,;:-?.!")[:120]


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


def _split_work_of_corpus_for_table_of_contents(value: str) -> tuple[str, str]:
    candidate = str(value or "").strip()
    match = re.match(
        r"^\s*(.+?)\s+(?:de|du|des|d['’])\s+([^,.;?!\n]{1,80})\s*$",
        candidate,
        flags=re.IGNORECASE,
    )
    if not match:
        return "", ""
    work = _clean_title(match.group(1), locator="")
    document = _clean_title(match.group(2), locator="")
    if not _usable_title(work) or not _usable_title(document):
        return "", ""
    return work, document


def _clean_title(value: str, *, locator: str) -> str:
    text = normalize_text(value).strip(" \t\r\n'\"")
    text = _RANGE_RE.sub(" ", text)
    text = _LOCATOR_RE.sub(" ", text)
    if locator:
        text = re.sub(re.escape(locator), " ", text, flags=re.IGNORECASE)
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
    return is_usable_title(candidate)


def _is_surface_only(value: str) -> bool:
    return is_surface_only(value)


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
    if re.search(r"\b(?:quels?|quoi|que)\b.*\b(?:ouvrages?|livres?|documents?|bibliotheque|biblio|catalogue)\b", folded):
        return True
    if re.search(r"\bcombien\b.*\b(?:ouvrages?|livres?|documents?)\b", folded):
        return True
    if re.search(r"\b(?:liste|lister|inventaire)\b.*\b(?:bibliotheque|biblio|catalogue)\b", folded):
        return True
    if re.search(r"\bc(?:'| )?est\s+tout\b.*\b(?:tu\s+as|vous\s+avez|ouvrages?|livres?|documents?|bibliotheque|biblio|catalogue)\b", folded):
        return True
    if re.fullmatch(r"\s*c(?:'| )?est\s+tout\s*\??\s*", folded):
        return True
    return False


def _is_table_of_contents_request(folded: str) -> bool:
    return bool(
        re.search(
            r"\b(?:table\s+des\s+matieres|sommaire|chapitres?|oeuvres\s+internes|contenu\s+du\s+volume)\b",
            folded,
        )
    )


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
    return compact_text_signal(value)


def _fold(value: str) -> str:
    return fold_text(value)
