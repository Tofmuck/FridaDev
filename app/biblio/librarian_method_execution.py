"""Mechanical GET execution for Biblio product-method continuations."""

from __future__ import annotations

from typing import Any, Mapping

from . import librarian_planner
from . import librarian_tools


def append_get_tool_call(
    loop_result: librarian_planner.BiblioLibrarianLoopResult,
    *,
    registry: librarian_tools.BiblioLibrarianToolRegistry,
    tool_name: str,
    params: Mapping[str, Any],
) -> librarian_planner.BiblioLibrarianLoopResult:
    """Execute one bounded continuation call and append its canonical step."""
    if loop_result.tool_call_count >= loop_result.options.max_tool_calls:
        return loop_result
    call = librarian_planner.BiblioLibrarianToolCall(
        tool_name=tool_name,
        method="GET",
        params=dict(params),
    )
    planner = librarian_planner.BiblioLibrarianPlanner(registry)
    step = planner.run_tool_call(len(loop_result.steps), call)
    steps = (*loop_result.steps, step)
    status = librarian_planner.STATUS_TOOL_EXECUTED
    reason = librarian_planner.REASON_TOOL_EXECUTED
    if step.status != librarian_planner.STATUS_TOOL_EXECUTED:
        status = step.status
        reason = step.reason_code
    return librarian_planner.BiblioLibrarianLoopResult(
        status=status,
        reason_code=reason,
        steps=steps,
        options=loop_result.options,
        duration_ms=loop_result.duration_ms,
        fallback_deterministic=loop_result.fallback_deterministic,
    )
