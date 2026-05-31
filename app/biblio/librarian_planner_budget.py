"""Budget helpers for the Biblio librarian planner loop."""

from __future__ import annotations

from typing import Any, Mapping

from . import catalogue_client as catalogue
from . import librarian_tools as tools
from .librarian_planner_observability import safe_token, safe_tool_name, strict_int


def plan_requests_clarification(
    intent: Any,
    answer_mode: Any,
    *,
    needs_status: str,
) -> bool:
    clarification_tokens = {"clarify", "clarification", needs_status}
    return safe_token(intent) in clarification_tokens or safe_token(answer_mode) in clarification_tokens


def bounded_context_params(
    tool_name: Any,
    params: Mapping[str, Any],
    *,
    context_chars: int,
    max_context_chars: int,
) -> tuple[dict[str, Any] | None, str]:
    if safe_tool_name(tool_name) != tools.TOOL_PASSAGE_CONTEXT:
        return None, ""
    remaining = max_context_chars - max(context_chars, 0)
    if remaining < catalogue.CONTEXT_WINDOW_CHARS_MIN:
        return None, "max_context_chars"
    requested = strict_int(params.get("window_chars", 700))
    if requested is None or requested <= remaining:
        return None, ""
    bounded = dict(params)
    bounded["window_chars"] = remaining
    return bounded, ""
