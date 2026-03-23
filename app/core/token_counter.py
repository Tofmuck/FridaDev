"""Token counters (heuristic only)."""

from __future__ import annotations

import math
import re
from typing import Iterable, List

_BASE_CHARS_PER_TOKEN_EN = 4.0
_BASE_CHARS_PER_TOKEN_FR = 3.3
_BASE_CHARS_PER_TOKEN_CJK = 1.9
_PER_MESSAGE_OVERHEAD = 4
_SAFETY_MARGIN = 1.10
_HARD_MIN = 1
_URL_SURCHARGE = 12
_EMOJI_SURCHARGE = 2
_CODE_BLOCK_SURCHARGE = 8
_BULLET_SURCHARGE = 1
_MAX_BULLETS = 50
_MAX_CODE_BLOCKS = 50

_URL_RE = re.compile(r"https?://\S+", re.IGNORECASE)
_CODE_RE = re.compile(r"```[\s\S]*?```", re.MULTILINE)
_BULLET_RE = re.compile(r"^\s*([-*•+]|\d+\.)", re.MULTILINE)
_WHITESPACE_COLLAPSE_RE = re.compile(r"[ \t]{2,}")

def count(text: str) -> int:
    cleaned = _normalize(text)
    if not cleaned:
        return 0
    latin_chars, cjk_chars, emoji_count = _count_characters(cleaned)
    latin_factor = _chars_per_token_latin_factor(cleaned)
    latin_tokens = math.ceil(latin_chars / latin_factor)
    cjk_tokens = math.ceil(cjk_chars / _BASE_CHARS_PER_TOKEN_CJK)
    tokens = latin_tokens + cjk_tokens
    tokens += _count_urls(cleaned) * _URL_SURCHARGE
    tokens += emoji_count * _EMOJI_SURCHARGE
    tokens += min(_count_code_blocks(cleaned), _MAX_CODE_BLOCKS) * _CODE_BLOCK_SURCHARGE
    tokens += min(_count_bullets(cleaned), _MAX_BULLETS) * _BULLET_SURCHARGE
    tokens = int(math.ceil(tokens * _SAFETY_MARGIN))
    return max(_HARD_MIN, tokens)


def count_messages(contents: Iterable[str]) -> int:
    total = 0
    for content in contents:
        total += _PER_MESSAGE_OVERHEAD
        total += count(content)
    total += 2
    return max(_HARD_MIN, total)


def _normalize(text: str) -> str:
    unified = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = unified.split("\n")
    cleaned_lines = []
    for line in lines:
        leading = len(line) - len(li := line.lstrip('\t '))
        preserved_leading = line[:leading]
        collapsed = _WHITESPACE_COLLAPSE_RE.sub(" ", li)
        cleaned_lines.append(preserved_leading + collapsed)
    return "\n".join(cleaned_lines).strip()


def _chars_per_token_latin_factor(text: str) -> float:
    lower = text.lower()
    french_markers = sum(lower.count(marker) for marker in ("é", "à", "ç", "ou", "toi", "vous"))
    if french_markers >= 3:
        return _BASE_CHARS_PER_TOKEN_FR
    return _BASE_CHARS_PER_TOKEN_EN


def _count_characters(text: str) -> tuple[int, int, int]:
    latin = 0
    cjk = 0
    emoji = 0
    for ch in text:
        if _is_emoji(ch):
            emoji += 1
            continue
        if _is_cjk(ch):
            cjk += 1
        elif not ch.isspace():
            latin += 1
    return latin, cjk, emoji


def _is_cjk(ch: str) -> bool:
    code = ord(ch)
    ranges = (
        (0x3040, 0x30FF),
        (0x3400, 0x4DBF),
        (0x4E00, 0x9FFF),
        (0xF900, 0xFAFF),
        (0x2E80, 0x2EFF),
        (0x2F00, 0x2FDF),
        (0x2FF0, 0x2FFF),
        (0x3000, 0x303F),
        (0x31C0, 0x31EF),
        (0x2F800, 0x2FA1F),
        (0x1100, 0x11FF),
        (0x3130, 0x318F),
        (0xA960, 0xA97F),
        (0xAC00, 0xD7AF),
        (0xD7B0, 0xD7FF),
        (0x20000, 0x2A6DF),
        (0x2A700, 0x2B73F),
        (0x2B740, 0x2B81F),
        (0x2B820, 0x2CEAF),
        (0x2CEB0, 0x2EBEF),
        (0x30000, 0x3134F),
    )
    return any(start <= code <= end for start, end in ranges)


def _is_emoji(ch: str) -> bool:
    return any(ord(ch) in range_ for range_ in (
        range(0x1F600, 0x1F64F),
        range(0x1F300, 0x1F5FF),
        range(0x1F680, 0x1F6FF),
        range(0x1F700, 0x1F77F),
        range(0x2600, 0x26FF),
        range(0x2700, 0x27BF),
    ))


def _count_urls(text: str) -> int:
    return len(_URL_RE.findall(text))


def _count_code_blocks(text: str) -> int:
    return len(_CODE_RE.findall(text))


def _count_bullets(text: str) -> int:
    matches = _BULLET_RE.findall(text)
    count = 0
    for bullet in matches:
        count += 1
        if count >= _MAX_BULLETS:
            break
    return count
