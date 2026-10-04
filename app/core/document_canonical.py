"""Closed, shallow V1 canonical and Unicode volume checks, without rendering."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import unicodedata
from urllib.parse import urlsplit

from .document_workshop_contract import (
    DOCUMENT_PROFILE, MAX_CANONICAL_JSON_BYTES, MAX_DOCUMENT_CODEPOINTS,
    MAX_DOCUMENT_WORDS, DocumentWorkshopError,
)


def _invalid() -> None:
    raise DocumentWorkshopError("document_canonical_invalid")


def strict_json_loads(raw: str) -> object:
    def object_pairs(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                _invalid()
            result[key] = value
        return result

    def constant(_value):
        _invalid()

    try:
        return json.loads(raw, object_pairs_hook=object_pairs, parse_constant=constant)
    except (ValueError, TypeError, RecursionError):
        raise DocumentWorkshopError("document_canonical_invalid") from None


def _closed(value: object, keys: set[str]) -> dict:
    if type(value) is not dict or set(value) != keys:
        _invalid()
    return value


def _text(value: object) -> str:
    if type(value) is not str:
        _invalid()
    for char in value:
        category = unicodedata.category(char)
        if category == "Cs" or (category == "Cc" and char not in "\n\r\t"):
            _invalid()
    return value


def _link(value: object) -> str | None:
    if value is None:
        return None
    text = _text(value)
    if not text or any(c.isspace() or unicodedata.category(c).startswith("C") for c in text):
        _invalid()
    try:
        parts = urlsplit(text)
        if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
            _invalid()
        # Parsing the port detects malformed/ambiguous authorities without fetch.
        parts.port
    except ValueError:
        _invalid()
    return text


def _spans(value: object, texts: list[str], links: list[str], *, allow_empty=False) -> None:
    if type(value) is not list or (not value and not allow_empty):
        _invalid()
    joined = []
    for item in value:
        data = _closed(item, {"text", "bold", "italic", "link"})
        text = _text(data["text"])
        if not text or type(data["bold"]) is not bool or type(data["italic"]) is not bool:
            _invalid()
        joined.append(text)
        link = _link(data["link"])
        if link is not None:
            links.append(link)
    # Adjacent styled spans are one textual unit: splitting a word does not
    # multiply words, and no synthetic separator contributes to character count.
    texts.append("".join(joined))


def count_unicode_words(text: str) -> int:
    """L/N runs with attached M marks; internal apostrophe/hyphen joins a word.

    No normalization. French l'été/porte-monnaie are each one word; punctuation
    and whitespace delimit. Symbols/emoji do not count as words but do count as
    codepoints. A combining mark on its own is not a word.
    """
    count = 0
    inside = False
    for index, char in enumerate(text):
        category = unicodedata.category(char)[0]
        if category in {"L", "N"}:
            if not inside:
                count += 1
            inside = True
        elif category == "M" and inside:
            continue
        elif char in {"'", "’", "-"} and inside and index + 1 < len(text) and unicodedata.category(text[index + 1])[0] in {"L", "N"}:
            continue
        else:
            inside = False
    return count


@dataclass(frozen=True, repr=False)
class ValidatedCanonical:
    _json: str = field(repr=False)
    word_count: int
    codepoint_count: int

    def as_dict(self) -> dict:
        return json.loads(self._json)


def validate_canonical(value: object) -> ValidatedCanonical:
    root = _closed(value, {"schema_version", "profile", "blocks"})
    if type(root["schema_version"]) is not int or root["schema_version"] != 1 or root["profile"] != DOCUMENT_PROFILE:
        _invalid()
    blocks = root["blocks"]
    if type(blocks) is not list or not blocks:
        _invalid()
    texts: list[str] = []
    links: list[str] = []
    for block in blocks:
        if type(block) is not dict:
            _invalid()
        kind = block.get("type")
        if type(kind) is not str:
            _invalid()
        if kind in {"paragraph", "heading", "quote"}:
            _closed(block, {"type", "spans", "level"} if kind == "heading" else {"type", "spans"})
            if kind == "heading" and (type(block["level"]) is not int or not 1 <= block["level"] <= 6):
                _invalid()
            _spans(block["spans"], texts, links)
        elif kind == "list":
            _closed(block, {"type", "ordered", "items"})
            if type(block["ordered"]) is not bool or type(block["items"]) is not list or not block["items"]:
                _invalid()
            for item in block["items"]:
                _spans(item, texts, links)
        elif kind == "table":
            _closed(block, {"type", "rows"})
            rows = block["rows"]
            if type(rows) is not list or not rows or type(rows[0]) is not list or not rows[0]:
                _invalid()
            width = len(rows[0])
            for row in rows:
                if type(row) is not list or len(row) != width:
                    _invalid()
                for cell in row:
                    _spans(cell, texts, links, allow_empty=True)
        elif kind == "page_break":
            _closed(block, {"type"})
        else:
            _invalid()
    if not any(text.strip() for text in texts):
        _invalid()
    # Count every textual value, including passive URL targets, exactly once.
    units = texts + links
    codepoints = sum(len(text) for text in units)
    words = sum(count_unicode_words(text) for text in units)
    if codepoints > MAX_DOCUMENT_CODEPOINTS:
        raise DocumentWorkshopError("document_character_limit")
    if words > MAX_DOCUMENT_WORDS:
        raise DocumentWorkshopError("document_word_limit")
    try:
        snapshot = json.dumps(root, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
        byte_count = len(snapshot.encode("utf-8"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        _invalid()
    if byte_count > MAX_CANONICAL_JSON_BYTES:
        raise DocumentWorkshopError("document_json_envelope_limit")
    return ValidatedCanonical(snapshot, words, codepoints)


def read_canonical_json(raw: str) -> ValidatedCanonical:
    if type(raw) is not str:
        _invalid()
    try:
        size = len(raw.encode("utf-8"))
    except UnicodeError:
        _invalid()
    if size > MAX_CANONICAL_JSON_BYTES:
        raise DocumentWorkshopError("document_json_envelope_limit")
    return validate_canonical(strict_json_loads(raw))


# Instructions sent inside messages, before the *shared* input estimate. M0
# defines canonical only; prepared/clarify/refuse + action/pending belong to M4.
CANONICAL_INSTRUCTIONS = """Return one complete JSON object, no markdown fence or commentary:
{schema_version: 1, profile: "frida_document_v1", blocks: [...]}. All keys below
are required and no other keys are permitted. Block forms:
paragraph/quote: {type, spans}; heading: {type, level (integer 1..6), spans};
list: {type:"list", ordered (boolean), items (nonempty array of spans arrays)};
table: {type:"table", rows (nonempty rectangular array of cells/spans arrays)};
page_break: {type:"page_break"}. A span has exactly {text (nonempty string),
bold (boolean), italic (boolean), link (null or passive http/https URL)}.
No images, executable references, macros, commands or active HTML nodes.
Use the fixed A4, 12pt, 1.5 line spacing, 2.5cm margin profile. Include all text.
At most 10000 words and 75000 Unicode codepoints across all text and URL targets.
No truncation, summarizing or rewriting to evade limits. Binary pagination is
not established by this output; final Writer proof is required separately.
"""
