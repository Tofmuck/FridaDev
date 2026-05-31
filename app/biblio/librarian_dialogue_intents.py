"""Deterministic intent classifiers for Biblio librarian dialogue planning."""

from __future__ import annotations

import re

from . import librarian_dialogue_navigation as navigation
from .query_normalizer import fold_text, normalize_text, query_variants


RECENT_DIALOGUE_MAX = 6

_CURRENT_DOCUMENT_RE = re.compile(r"\b(ce|cet|cette|celui|celle|meme|même)\b")
_DEICTIC_TOC_RE = re.compile(
    r"\b(de|du|des|d')\s+(celui|celle|cela|ca|ça|ceci|ce|cet|cette|livre|ouvrage|document|volume)\b"
)
_TOC_PREFIX_STOPWORDS = frozenset(
    {
        "affiche",
        "donne",
        "liste",
        "montre",
        "ouvre",
        "peux",
        "table",
        "vois",
        "voir",
    }
)
_TOC_TERM_RE = re.compile(r"\b(table des matieres|sommaire)\b")
_TOC_SUFFIX_QUALIFIERS = frozenset(
    {
        "complet",
        "complete",
        "complets",
        "completes",
        "detaille",
        "detaillee",
        "detailles",
        "detaillees",
        "general",
        "generale",
        "generales",
        "generaux",
    }
)
_TOC_SUFFIX_POLITENESS = frozenset(
    {
        "maintenant",
        "merci",
        "plait",
        "please",
        "svp",
        "stp",
    }
)
_TOC_SUFFIX_IGNORED_TOKENS = _TOC_SUFFIX_QUALIFIERS | _TOC_SUFFIX_POLITENESS


def normalize_message(value: str) -> str:
    return normalize_text(value)


def fold_message(value: str) -> str:
    return fold_text(value)


def variants_for_message(value: str) -> tuple[str, ...]:
    return query_variants(value)


def search_query(value: str) -> str:
    variants = query_variants(value, max_variants=2)
    return variants[0] if variants else normalize_text(value)


def asks_catalogue_list(folded: str) -> bool:
    if re.search(r"\b(liste|lister|affiche|montre|voir|vois)\b", folded) and re.search(
        r"\b(catalogue|bibliotheque|biblio|ouvrages|livres|documents)\b",
        folded,
    ):
        return True
    return bool(re.search(r"\b(quels|combien)\b.*\b(ouvrages|livres|documents)\b", folded))


def asks_table_of_contents(folded: str) -> bool:
    return bool("table des matieres" in folded or "sommaire" in folded)


def toc_has_unresolved_explicit_reference(folded: str) -> bool:
    if not asks_table_of_contents(folded):
        return False
    if _DEICTIC_TOC_RE.search(folded):
        return False
    if re.search(r"\b(table des matieres|sommaire)\b.*\b(de|du|des|d')\s+[a-z0-9]{3,}", folded):
        return True
    if _toc_suffix_has_explicit_reference(folded):
        return True
    if re.search(r"^\s*(de|du|des|d')\s+[a-z0-9]{3,}.*\b(table des matieres|sommaire)\b", folded):
        return True
    prefix = re.search(r"\b([a-z0-9]{3,})\b\s+(table des matieres|sommaire)\b", folded)
    return bool(prefix and prefix.group(1) not in _TOC_PREFIX_STOPWORDS)


def _toc_suffix_has_explicit_reference(folded: str) -> bool:
    match = _TOC_TERM_RE.search(folded)
    if not match:
        return False
    suffix = folded[match.end() :]
    tokens = re.findall(r"\b[a-z0-9]{3,}\b", suffix)
    return any(token not in _TOC_SUFFIX_IGNORED_TOKENS for token in tokens)


def asks_navigation(folded: str) -> bool:
    return navigation.is_navigation_request(folded)


def asks_passage_reference(folded: str) -> bool:
    if not re.search(
        r"\b(le|l'|ce|cet|cette|dernier|derniere|meme|même)\s+(passage|extrait|paragraphe)\b",
        folded,
    ):
        return False
    return bool(re.search(r"\b(explique|expliquer|reprends|reprendre|resume|resumer|relis|relire|commente)\b", folded))


def asks_compare(folded: str) -> bool:
    return bool(re.search(r"\b(compare|comparer|difference|differences)\b", folded))


def mentions_current_document(folded: str) -> bool:
    return bool(_CURRENT_DOCUMENT_RE.search(folded) and re.search(r"\b(livre|ouvrage|document|volume)\b", folded))


def asks_thematic_search(folded: str) -> bool:
    if re.search(r"\b(cherche|chercher|trouve|trouver|retrouve|sort|sortir)\b", folded):
        return True
    return bool(re.search(r"\b(moment|passage|extrait)\b.*\b(parle|question|theme|sujet|sur)\b", folded))
