"""Reusable query normalization for the native Biblio librarian.

The normalizer keeps raw text internal and exposes only compact hashes for
observability.  It does not call Catalogue and does not decide whether a query
is bibliographic; it only prepares safer textual variants for deterministic
planning and GET-only lookup paths.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from typing import Any, Iterable


_LIGATURE_TRANSLATION = str.maketrans(
    {
        "œ": "oe",
        "Œ": "Oe",
        "æ": "ae",
        "Æ": "Ae",
    }
)
_APOSTROPHES_RE = re.compile(r"[’`´ʻʼʹ]")
_WHITESPACE_RE = re.compile(r"\s+")
_TOKEN_RE = re.compile(r"[^\W_]+(?:[-'][^\W_]+)?", re.UNICODE)

_SURFACE_WORDS = {
    "bibliotheque",
    "biblio",
    "catalogue",
    "document",
    "documents",
    "livre",
    "livres",
    "ouvrage",
    "ouvrages",
}
_FUNCTION_WORDS = {
    "a",
    "au",
    "aux",
    "chez",
    "dans",
    "de",
    "des",
    "du",
    "d",
    "l",
    "la",
    "le",
    "les",
    "un",
    "une",
}

_WORK_ALIAS_GROUPS = (
    ("Théétète", "Theetete", "Theaitetos", "Theaetetus"),
)
_TERM_ALIAS_GROUPS = (
    ("maïeutique", "maieutique"),
    ("sage-femme", "sage femme"),
)


@dataclass(frozen=True)
class BiblioQueryNormalization:
    original: str
    normalized: str
    folded: str
    variants: tuple[str, ...]

    def to_observability(self) -> dict[str, Any]:
        return {
            "original": compact_text_signal(self.original),
            "normalized": compact_text_signal(self.normalized),
            "folded": compact_text_signal(self.folded),
            "variant_count": len(self.variants),
            "variant_hashes": [_sha256_12(variant) for variant in self.variants],
        }


def normalize_biblio_query(value: str) -> BiblioQueryNormalization:
    original = str(value or "")
    normalized = normalize_text(original)
    return BiblioQueryNormalization(
        original=original,
        normalized=normalized,
        folded=fold_text(normalized),
        variants=query_variants(normalized),
    )


def normalize_text(value: str) -> str:
    text = str(value or "").translate(_LIGATURE_TRANSLATION)
    text = _APOSTROPHES_RE.sub("'", text)
    text = text.replace("“", '"').replace("”", '"')
    return _WHITESPACE_RE.sub(" ", text).strip()


def fold_text(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", normalize_text(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return ascii_text.lower()


def alias_key(value: str) -> str:
    folded = fold_text(value)
    folded = folded.replace("'", " ")
    folded = folded.replace("-", " ")
    folded = re.sub(r"[^a-z0-9]+", " ", folded)
    return _WHITESPACE_RE.sub(" ", folded).strip()


_WORK_ALIASES = {
    alias_key(alias): tuple(group)
    for group in _WORK_ALIAS_GROUPS
    for alias in group
}
_TERM_ALIASES = {
    alias_key(alias): tuple(group)
    for group in _TERM_ALIAS_GROUPS
    for alias in group
}


def canonical_work_title(value: str) -> str:
    text = normalize_text(value)
    aliases = _WORK_ALIASES.get(alias_key(text))
    return aliases[0] if aliases else text


def is_known_work_alias(value: str) -> bool:
    return alias_key(value) in _WORK_ALIASES


def query_variants(*values: str, max_variants: int = 12) -> tuple[str, ...]:
    variants: list[str] = []
    for raw in values:
        text = normalize_text(raw)
        if not text:
            continue
        _append_unique(variants, text)
        _append_unique(variants, canonical_work_title(text))
        for alias in _direct_aliases(text):
            _append_unique(variants, alias)
        for variant in _phrase_alias_variants(text):
            _append_unique(variants, variant)
        for alias in _contained_alias_terms(text):
            _append_unique(variants, alias)
        folded = fold_text(text)
        if folded and folded != text.lower():
            _append_unique(variants, folded)
        spaced = text.replace("-", " ")
        hyphenated = _hyphenate_known_terms(text)
        _append_unique(variants, spaced)
        _append_unique(variants, hyphenated)
    return tuple(variant for variant in variants if variant)[:max_variants]


def compact_text_signal(value: Any) -> dict[str, Any]:
    text = str(value or "").strip()
    if not text:
        return {"present": False, "length": 0, "hash": ""}
    return {"present": True, "length": len(text), "hash": _sha256_12(text)}


def variants_observability(values: Iterable[str]) -> dict[str, Any]:
    variants = tuple(str(value or "").strip() for value in values if str(value or "").strip())
    return {
        "count": len(variants),
        "hashes": [_sha256_12(value) for value in variants],
    }


def is_surface_only(value: str) -> bool:
    words = {alias_key(part) for part in re.findall(r"\w+", str(value or ""))}
    return bool(words) and all(word in _SURFACE_WORDS or word in _FUNCTION_WORDS for word in words)


def is_usable_title(value: str) -> bool:
    text = normalize_text(value)
    if len(text) < 2:
        return False
    folded = alias_key(text)
    if folded in _SURFACE_WORDS or folded in _FUNCTION_WORDS:
        return False
    if re.fullmatch(r"(?:mon|ma|mes|ton|ta|tes|son|sa|ses|ce|cet|cette)?\s*(?:livre|ouvrage|document)s?", folded):
        return False
    if folded in {"adobe", "photoshop", "illustrator", "web"}:
        return False
    return True


def _direct_aliases(value: str) -> tuple[str, ...]:
    key = alias_key(value)
    return (*_WORK_ALIASES.get(key, ()), *_TERM_ALIASES.get(key, ()))


def _phrase_alias_variants(value: str) -> tuple[str, ...]:
    variants: list[str] = []
    for alias_map in (_WORK_ALIASES, _TERM_ALIASES):
        for key, aliases in alias_map.items():
            if not _contains_alias_key(value, key):
                continue
            for alias in aliases:
                replaced = _replace_alias_phrase(value, key, alias)
                _append_unique(variants, replaced)
    return tuple(variants)


def _contained_alias_terms(value: str) -> tuple[str, ...]:
    terms: list[str] = []
    for alias_map in (_WORK_ALIASES, _TERM_ALIASES):
        for key, aliases in alias_map.items():
            if _contains_alias_key(value, key):
                for alias in aliases:
                    _append_unique(terms, alias)
    return tuple(terms)


def _contains_alias_key(value: str, key: str) -> bool:
    haystack = f" {alias_key(value)} "
    return f" {key} " in haystack


def _replace_alias_phrase(value: str, key: str, replacement: str) -> str:
    words = key.split()
    if not words:
        return value
    text = normalize_text(value)
    tokens = list(_TOKEN_RE.finditer(text))
    for index in range(0, len(tokens)):
        for end_index in range(index + 1, len(tokens) + 1):
            phrase = " ".join(token.group(0) for token in tokens[index:end_index])
            if alias_key(phrase) != key:
                continue
            start = tokens[index].start()
            end = tokens[end_index - 1].end()
            return f"{text[:start]}{replacement}{text[end:]}"
    return value


def _hyphenate_known_terms(value: str) -> str:
    key = alias_key(value)
    if key == "sage femme":
        return "sage-femme"
    return value


def _append_unique(values: list[str], value: str) -> None:
    text = normalize_text(value)
    if text and text not in values:
        values.append(text)


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
