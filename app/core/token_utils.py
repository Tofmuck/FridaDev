from __future__ import annotations

from typing import Iterable, Mapping

from .token_counter import count_messages


def count_tokens(messages: Iterable[Mapping[str, str]], model: str) -> int:
    contents = []
    for msg in messages:
        content = msg.get("content", "")
        if not isinstance(content, str):
            content = str(content)
        contents.append(content)
    return count_messages(contents)
