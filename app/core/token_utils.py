from __future__ import annotations

from typing import Iterable, Mapping

from .token_counter import estimate_message_tokens


def estimate_tokens(messages: Iterable[Mapping[str, str]], model: str) -> int:
    contents = []
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        contents.append(content)
    return estimate_message_tokens(contents)


def count_tokens(messages: Iterable[Mapping[str, str]], model: str) -> int:
    """Legacy shim kept for older call sites."""
    return estimate_tokens(messages, model)
