from __future__ import annotations


MAX_STRONG_ETAG_LENGTH = 512


def validated_strong_etag(value: object) -> str:
    """Return one exact strong HTTP entity-tag, or an empty ownership proof."""
    if not isinstance(value, str):
        return ""
    if not 2 <= len(value) <= MAX_STRONG_ETAG_LENGTH:
        return ""
    if value[0] != '"' or value[-1] != '"':
        return ""
    for character in value[1:-1]:
        codepoint = ord(character)
        if codepoint == 0x21 or 0x23 <= codepoint <= 0x7E or 0x80 <= codepoint <= 0xFF:
            continue
        return ""
    return value
