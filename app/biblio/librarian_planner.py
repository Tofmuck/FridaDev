"""Bounded planning loop above the Biblio librarian tool registry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import catalogue_client as catalogue
from . import librarian_tools as tools


SCHEMA_VERSION = "biblio_librarian_loop_v1"

STATUS_PLANNED = "planned"
STATUS_TOOL_EXECUTED = "tool_executed"
STATUS_NEEDS_CLARIFICATION = "needs_clarification"
STATUS_NOT_FOUND = "not_found"
STATUS_AMBIGUOUS = "ambiguous"
STATUS_BUDGET_EXHAUSTED = "budget_exhausted"
STATUS_TOOL_REJECTED = "tool_rejected"
STATUS_TOOL_FAILED = "tool_failed"
STATUS_FALLBACK_DETERMINISTIC = "fallback_deterministic"

REASON_PLANNED = "biblio_librarian_plan_ready"
REASON_TOOL_EXECUTED = "biblio_librarian_tool_executed"
REASON_NEEDS_CLARIFICATION = "biblio_librarian_needs_clarification"
REASON_NOT_FOUND = "biblio_librarian_not_found"
REASON_AMBIGUOUS = "biblio_librarian_ambiguous"
REASON_BUDGET_EXHAUSTED = "biblio_librarian_budget_exhausted"
REASON_TOOL_REJECTED = "biblio_librarian_tool_rejected"
REASON_TOOL_FAILED = "biblio_librarian_tool_failed"
REASON_FALLBACK_DETERMINISTIC = "biblio_librarian_fallback_deterministic"
REASON_INVALID_PLAN = "biblio_librarian_invalid_plan"

_TERMINAL_STEP_STATUSES = {
    STATUS_TOOL_REJECTED,
    STATUS_TOOL_FAILED,
    STATUS_BUDGET_EXHAUSTED,
    STATUS_NEEDS_CLARIFICATION,
}


@dataclass(frozen=True)
class BiblioLibrarianLoopOptions:
    max_steps: int = 5
    max_tool_calls: int = 5
    max_total_duration_ms: int = 2_000
    max_clarifications: int = 1
    max_context_chars: int = 4_000

    def to_observability(self) -> dict[str, Any]:
        return {
            "max_steps": self.max_steps,
            "max_tool_calls": self.max_tool_calls,
            "max_total_duration_ms": self.max_total_duration_ms,
            "max_clarifications": self.max_clarifications,
            "max_context_chars": self.max_context_chars,
        }


@dataclass(frozen=True)
class BiblioLibrarianToolCall:
    tool_name: str
    params: dict[str, Any] = field(default_factory=dict, repr=False, compare=False)
    call_id: str = ""
    method: str = ""

    def to_observability(self) -> dict[str, Any]:
        return {
            "tool_name": _safe_tool_name(self.tool_name),
            "call_id_present": bool(self.call_id),
            "param_count": len(self.params),
            "method": _safe_token(self.method),
        }


@dataclass(frozen=True)
class BiblioLibrarianPlan:
    schema_version: str = SCHEMA_VERSION
    intent: str = ""
    tool_calls: tuple[BiblioLibrarianToolCall, ...] = field(
        default_factory=tuple,
        repr=False,
        compare=False,
    )
    answer_mode: str = ""
    fallback_reason: str = ""

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "schema_version": self.schema_version,
                "intent": _safe_token(self.intent),
                "answer_mode": _safe_token(self.answer_mode),
                "tool_call_count": len(self.tool_calls),
                "tool_names": [_safe_tool_name(call.tool_name) for call in self.tool_calls],
                "fallback_reason": _safe_token(self.fallback_reason),
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianLoopRequest:
    plan: BiblioLibrarianPlan = field(default_factory=BiblioLibrarianPlan, repr=False, compare=False)
    options: BiblioLibrarianLoopOptions = field(default_factory=BiblioLibrarianLoopOptions)
    user_message: str = field(default="", repr=False, compare=False)
    recent_dialogue: tuple[Mapping[str, Any], ...] = field(default_factory=tuple, repr=False, compare=False)
    biblio_state: Any = field(default=None, repr=False, compare=False)

    def to_observability(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "plan": self.plan.to_observability(),
            "options": self.options.to_observability(),
            "user_message_present": bool(self.user_message),
            "recent_dialogue_count": len(self.recent_dialogue),
            "biblio_state_present": self.biblio_state is not None,
        }


@dataclass(frozen=True)
class BiblioLibrarianStep:
    index: int
    status: str
    reason_code: str
    tool_name: str = ""
    endpoint_kind: str = ""
    observation: dict[str, Any] = field(default_factory=dict)
    tool_call: BiblioLibrarianToolCall | None = field(default=None, repr=False, compare=False)
    tool_result: tools.BiblioLibrarianToolResult | None = field(default=None, repr=False, compare=False)

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "index": self.index,
                "status": self.status,
                "reason_code": self.reason_code,
                "tool_name": _safe_tool_name(self.tool_name),
                "endpoint_kind": _safe_token(self.endpoint_kind),
                **_safe_observation(self.observation),
            }
        )


@dataclass(frozen=True)
class BiblioLibrarianLoopResult:
    status: str
    reason_code: str
    steps: tuple[BiblioLibrarianStep, ...] = field(default_factory=tuple)
    options: BiblioLibrarianLoopOptions = field(default_factory=BiblioLibrarianLoopOptions)
    duration_ms: int = 0
    fallback_deterministic: bool = False

    @property
    def tool_call_count(self) -> int:
        return sum(1 for step in self.steps if step.tool_result is not None)

    def to_observability(self) -> dict[str, Any]:
        step_observations = [step.to_observability() for step in self.steps]
        return _clean(
            {
                "schema_version": SCHEMA_VERSION,
                "status": self.status,
                "reason_code": self.reason_code,
                "step_count": len(self.steps),
                "tool_call_count": self.tool_call_count,
                "tool_names": _unique(_field_values(step_observations, "tool_name")),
                "endpoint_kinds": _unique(_field_values(step_observations, "endpoint_kind")),
                "doc_id_shorts": _unique(_collect_doc_id_shorts(step_observations)),
                "positions": _collect_positions(step_observations),
                "query_hashes": _unique(_field_values(step_observations, "query_hash")),
                "locator_hashes": _unique(_field_values(step_observations, "locator_hash")),
                "content_hashes": _unique(_field_values(step_observations, "content_hash")),
                "total_content_chars": sum(_int(item.get("content_chars")) or 0 for item in step_observations),
                "duration_ms": self.duration_ms,
                "fallback_deterministic": self.fallback_deterministic,
                "budget": self.options.to_observability(),
                "steps": step_observations,
            }
        )


class BiblioLibrarianPlanner:
    def __init__(
        self,
        registry: tools.BiblioLibrarianToolRegistry,
        *,
        monotonic: Any = time.monotonic,
    ) -> None:
        self._registry = registry
        self._monotonic = monotonic

    def run(
        self,
        request: BiblioLibrarianLoopRequest | None = None,
        *,
        proposed_tool_calls: Sequence[Mapping[str, Any] | BiblioLibrarianToolCall] | None = None,
        options: BiblioLibrarianLoopOptions | None = None,
    ) -> BiblioLibrarianLoopResult:
        loop_request = _coerce_request(request, proposed_tool_calls=proposed_tool_calls, options=options)
        started = self._monotonic()
        if loop_request.plan.schema_version != SCHEMA_VERSION:
            return _final_result(
                STATUS_TOOL_REJECTED,
                REASON_INVALID_PLAN,
                (),
                loop_request.options,
                started,
                self._monotonic,
            )
        steps: list[BiblioLibrarianStep] = []
        context_chars = 0
        tool_calls = 0
        terminal_status = ""
        terminal_reason = ""
        if _plan_requests_clarification(loop_request.plan):
            if loop_request.options.max_clarifications < 1:
                steps = _with_budget_step_if_room(
                    steps,
                    None,
                    loop_request.options,
                    "max_clarifications",
                )
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
            elif loop_request.options.max_steps < 1:
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
            else:
                steps.append(_clarification_step(0, loop_request.options))
                terminal_status = STATUS_NEEDS_CLARIFICATION
                terminal_reason = REASON_NEEDS_CLARIFICATION
            return _final_result(
                terminal_status,
                terminal_reason,
                tuple(steps),
                loop_request.options,
                started,
                self._monotonic,
            )
        if not loop_request.plan.tool_calls:
            return _final_result(
                STATUS_FALLBACK_DETERMINISTIC,
                REASON_FALLBACK_DETERMINISTIC,
                (),
                loop_request.options,
                started,
                self._monotonic,
                fallback=True,
            )

        for call in loop_request.plan.tool_calls:
            if _duration_ms(started, self._monotonic) > loop_request.options.max_total_duration_ms:
                steps = _with_budget_step_if_room(steps, call, loop_request.options, "max_total_duration_ms")
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
                break
            if len(steps) >= loop_request.options.max_steps or tool_calls >= loop_request.options.max_tool_calls:
                budget = "max_steps" if len(steps) >= loop_request.options.max_steps else "max_tool_calls"
                steps = _with_budget_step_if_room(steps, call, loop_request.options, budget)
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
                break
            call, budget = _bounded_context_call(call, context_chars, loop_request.options.max_context_chars)
            if budget:
                steps = _with_budget_step_if_room(steps, call, loop_request.options, budget)
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
                break
            step = self._run_tool_call(len(steps), call)
            steps.append(step)
            if step.tool_result is not None:
                tool_calls += 1
            context_chars += _int(step.observation.get("content_chars")) or 0
            if context_chars > loop_request.options.max_context_chars:
                steps = _with_budget_step_if_room(steps, call, loop_request.options, "max_context_chars")
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
                break
            if step.status in _TERMINAL_STEP_STATUSES:
                break

        status, reason = (
            (terminal_status, terminal_reason)
            if terminal_status
            else _result_status(tuple(steps))
        )
        return _final_result(
            status,
            reason,
            tuple(steps),
            loop_request.options,
            started,
            self._monotonic,
        )

    def _run_tool_call(self, index: int, call: BiblioLibrarianToolCall) -> BiblioLibrarianStep:
        tool_name = _safe_tool_name(call.tool_name)
        if not tool_name:
            return BiblioLibrarianStep(index, STATUS_TOOL_REJECTED, REASON_INVALID_PLAN)
        method = _safe_token(call.method).upper()
        if method and method != "GET":
            return BiblioLibrarianStep(
                index=index,
                status=STATUS_TOOL_REJECTED,
                reason_code=tools.REASON_FORBIDDEN_TOOL,
                tool_name=tool_name,
                tool_call=call,
            )
        if tool_name not in self._registry.tool_names:
            reason = tools.REASON_FORBIDDEN_TOOL if tool_name in tools.FORBIDDEN_TOOL_NAMES else tools.REASON_UNKNOWN_TOOL
            return BiblioLibrarianStep(
                index=index,
                status=STATUS_TOOL_REJECTED,
                reason_code=reason,
                tool_name=tool_name,
                tool_call=call,
            )
        try:
            result = self._registry.run(tool_name, call.params)
        except tools.BiblioLibrarianToolError as exc:
            return BiblioLibrarianStep(
                index=index,
                status=STATUS_TOOL_REJECTED,
                reason_code=exc.reason_code,
                tool_name=tool_name,
                endpoint_kind=exc.endpoint_kind,
                observation=exc.to_observability(),
                tool_call=call,
            )
        observation = result.to_observability()
        step_status = _step_status(result.status)
        step_reason = REASON_TOOL_EXECUTED if step_status == STATUS_TOOL_EXECUTED else result.reason_code
        return BiblioLibrarianStep(
            index=index,
            status=step_status,
            reason_code=step_reason,
            tool_name=tool_name,
            endpoint_kind=result.endpoint_kind,
            observation=observation,
            tool_call=call,
            tool_result=result,
        )


def _coerce_request(
    request: BiblioLibrarianLoopRequest | None,
    *,
    proposed_tool_calls: Sequence[Mapping[str, Any] | BiblioLibrarianToolCall] | None,
    options: BiblioLibrarianLoopOptions | None,
) -> BiblioLibrarianLoopRequest:
    if request is not None:
        return request
    calls = tuple(_coerce_call(item) for item in (proposed_tool_calls or ()))
    return BiblioLibrarianLoopRequest(
        plan=BiblioLibrarianPlan(tool_calls=calls),
        options=options or BiblioLibrarianLoopOptions(),
    )


def _coerce_call(value: Mapping[str, Any] | BiblioLibrarianToolCall) -> BiblioLibrarianToolCall:
    if isinstance(value, BiblioLibrarianToolCall):
        return value
    if not isinstance(value, Mapping):
        return BiblioLibrarianToolCall(tool_name="")
    params = value.get("params") if isinstance(value.get("params"), Mapping) else {}
    return BiblioLibrarianToolCall(
        tool_name=_safe_tool_name(value.get("tool_name") or value.get("name") or value.get("tool")),
        params=dict(params),
        call_id=_safe_token(value.get("call_id")),
        method=_safe_token(value.get("method")),
    )


def _step_status(tool_status: str) -> str:
    if tool_status == tools.STATUS_OK:
        return STATUS_TOOL_EXECUTED
    if tool_status == tools.STATUS_INCOHERENT_CATALOGUE:
        return STATUS_TOOL_FAILED
    if tool_status == tools.STATUS_ERROR:
        return STATUS_TOOL_FAILED
    if tool_status == STATUS_AMBIGUOUS:
        return STATUS_AMBIGUOUS
    if tool_status == STATUS_NOT_FOUND:
        return STATUS_NOT_FOUND
    return STATUS_TOOL_FAILED


def _result_status(steps: tuple[BiblioLibrarianStep, ...]) -> tuple[str, str]:
    if not steps:
        return STATUS_FALLBACK_DETERMINISTIC, REASON_FALLBACK_DETERMINISTIC
    last = steps[-1]
    if last.status == STATUS_BUDGET_EXHAUSTED:
        return STATUS_BUDGET_EXHAUSTED, REASON_BUDGET_EXHAUSTED
    for status, reason in (
        (STATUS_TOOL_REJECTED, REASON_TOOL_REJECTED),
        (STATUS_TOOL_FAILED, REASON_TOOL_FAILED),
        (STATUS_AMBIGUOUS, REASON_AMBIGUOUS),
        (STATUS_NOT_FOUND, REASON_NOT_FOUND),
    ):
        if any(step.status == status for step in steps):
            return status, reason
    if any(step.status == STATUS_TOOL_EXECUTED for step in steps):
        return STATUS_TOOL_EXECUTED, REASON_TOOL_EXECUTED
    return STATUS_NEEDS_CLARIFICATION, REASON_NEEDS_CLARIFICATION


def _plan_requests_clarification(plan: BiblioLibrarianPlan) -> bool:
    return _safe_token(plan.intent) in {"clarify", "clarification", STATUS_NEEDS_CLARIFICATION} or _safe_token(
        plan.answer_mode
    ) in {"clarify", "clarification", STATUS_NEEDS_CLARIFICATION}


def _clarification_step(index: int, options: BiblioLibrarianLoopOptions) -> BiblioLibrarianStep:
    return BiblioLibrarianStep(
        index=index,
        status=STATUS_NEEDS_CLARIFICATION,
        reason_code=REASON_NEEDS_CLARIFICATION,
        observation={
            "clarification_count": 1,
            "max_clarifications": options.max_clarifications,
        },
    )


def _with_budget_step_if_room(
    steps: Sequence[BiblioLibrarianStep],
    call: BiblioLibrarianToolCall | None,
    options: BiblioLibrarianLoopOptions,
    budget: str,
) -> list[BiblioLibrarianStep]:
    updated = list(steps)
    if len(updated) < max(options.max_steps, 0):
        updated.append(_budget_step(len(updated), call, budget))
    return updated


def _budget_step(index: int, call: BiblioLibrarianToolCall | None, budget: str) -> BiblioLibrarianStep:
    return BiblioLibrarianStep(
        index=index,
        status=STATUS_BUDGET_EXHAUSTED,
        reason_code=REASON_BUDGET_EXHAUSTED,
        tool_name=_safe_tool_name(call.tool_name) if call is not None else "",
        observation={"budget_exhausted": _safe_token(budget)},
        tool_call=call,
    )


def _bounded_context_call(
    call: BiblioLibrarianToolCall,
    context_chars: int,
    max_context_chars: int,
) -> tuple[BiblioLibrarianToolCall, str]:
    if _safe_tool_name(call.tool_name) != tools.TOOL_PASSAGE_CONTEXT:
        return call, ""
    remaining = max_context_chars - max(context_chars, 0)
    if remaining < catalogue.CONTEXT_WINDOW_CHARS_MIN:
        return call, "max_context_chars"
    requested = _strict_int(call.params.get("window_chars", 700))
    if requested is None:
        return call, ""
    if requested <= remaining:
        return call, ""
    params = dict(call.params)
    params["window_chars"] = remaining
    return (
        BiblioLibrarianToolCall(
            tool_name=call.tool_name,
            params=params,
            call_id=call.call_id,
            method=call.method,
        ),
        "",
    )


def _final_result(
    status: str,
    reason_code: str,
    steps: tuple[BiblioLibrarianStep, ...],
    options: BiblioLibrarianLoopOptions,
    started: float,
    monotonic: Any,
    *,
    fallback: bool = False,
) -> BiblioLibrarianLoopResult:
    return BiblioLibrarianLoopResult(
        status=status,
        reason_code=reason_code,
        steps=steps,
        options=options,
        duration_ms=_duration_ms(started, monotonic),
        fallback_deterministic=fallback or status == STATUS_FALLBACK_DETERMINISTIC,
    )


def _safe_observation(observation: Mapping[str, Any]) -> dict[str, Any]:
    allowed = {
        "endpoint_kind",
        "status_code",
        "duration_ms",
        "result_count",
        "total_count",
        "displayed_count",
        "truncated",
        "doc_id_short",
        "doc_id_shorts",
        "query_chars",
        "query_hash",
        "locator_chars",
        "locator_hash",
        "content_chars",
        "content_hash",
        "positions",
        "error_class",
        "budget_exhausted",
        "clarification_count",
        "max_clarifications",
    }
    return {key: value for key, value in observation.items() if key in allowed}


def _field_values(items: Sequence[Mapping[str, Any]], key: str) -> list[str]:
    return [str(item.get(key) or "") for item in items if str(item.get(key) or "")]


def _collect_doc_id_shorts(items: Sequence[Mapping[str, Any]]) -> list[str]:
    values: list[str] = []
    for item in items:
        if item.get("doc_id_short"):
            values.append(str(item["doc_id_short"]))
        value = item.get("doc_id_shorts")
        if isinstance(value, list):
            values.extend(str(part) for part in value if str(part or ""))
    return values


def _collect_positions(items: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    positions: list[dict[str, Any]] = []
    for item in items:
        value = item.get("positions")
        if isinstance(value, list):
            positions.extend(dict(position) for position in value if isinstance(position, Mapping))
    return positions[:12]


def _unique(values: Sequence[str]) -> list[str]:
    seen: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.append(value)
    return seen


def _duration_ms(started: float, monotonic: Any) -> int:
    return int(max((monotonic() - started) * 1000, 0))


def _safe_tool_name(value: Any) -> str:
    return str(value or "").strip()


def _safe_token(value: Any, *, max_chars: int = 120) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return ""
    if any(char not in "abcdefghijklmnopqrstuvwxyz0123456789_-.:/" for char in text):
        return "invalid_token"
    return text[:max_chars]


def _int(value: Any) -> int | None:
    return value if type(value) is int else None


def _strict_int(value: Any) -> int | None:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return None


def _clean(payload: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in payload.items()
        if value is not None and value != "" and value != [] and value != {}
    }
