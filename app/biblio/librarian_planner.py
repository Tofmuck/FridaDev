"""Bounded planning loop above the Biblio librarian tool registry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import librarian_tools as tools
from .librarian_planner_budget import bounded_context_params as _bounded_context_params
from .librarian_planner_budget import plan_requests_clarification as _plan_requests_clarification
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import collect_doc_id_shorts as _collect_doc_id_shorts
from .librarian_planner_observability import collect_positions as _collect_positions
from .librarian_planner_observability import field_values as _field_values
from .librarian_planner_observability import int_value as _int
from .librarian_planner_observability import safe_observation as _safe_observation
from .librarian_planner_observability import safe_token as _safe_token
from .librarian_planner_observability import safe_tool_name as _safe_tool_name
from .librarian_planner_observability import unique as _unique


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
        carried_document_id = ""
        carried_position: dict[str, Any] = {}
        terminal_status = ""
        terminal_reason = ""
        if _plan_requests_clarification(
            loop_request.plan.intent,
            loop_request.plan.answer_mode,
            needs_status=STATUS_NEEDS_CLARIFICATION,
        ):
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
            bounded_params, budget = _bounded_context_params(
                call.tool_name,
                call.params,
                context_chars=context_chars,
                max_context_chars=loop_request.options.max_context_chars,
            )
            if budget:
                steps = _with_budget_step_if_room(steps, call, loop_request.options, budget)
                terminal_status = STATUS_BUDGET_EXHAUSTED
                terminal_reason = REASON_BUDGET_EXHAUSTED
                break
            if bounded_params is not None:
                call = BiblioLibrarianToolCall(
                    tool_name=call.tool_name,
                    params=bounded_params,
                    call_id=call.call_id,
                    method=call.method,
                )
            call = _with_carried_anchor(
                call,
                document_id=carried_document_id,
                position=carried_position,
            )
            step = self.run_tool_call(len(steps), call)
            steps.append(step)
            if step.tool_result is not None:
                tool_calls += 1
                carried_document_id = _carried_document_id(step.tool_result) or carried_document_id
                carried_position = _carried_position(step.tool_result) or carried_position
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

    def run_tool_call(self, index: int, call: BiblioLibrarianToolCall) -> BiblioLibrarianStep:
        """Run one bounded GET-only tool call for loop continuations."""
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


def _with_carried_anchor(
    call: BiblioLibrarianToolCall,
    *,
    document_id: str,
    position: Mapping[str, Any],
) -> BiblioLibrarianToolCall:
    params = dict(call.params)
    changed = False
    if call.tool_name in {
        tools.TOOL_DOCUMENT_TOC,
        tools.TOOL_LOCATE,
        tools.TOOL_PASSAGE_CONTEXT,
    } and document_id and not (params.get("document_id") or params.get("doc_id")):
        params["document_id"] = document_id
        changed = True
    if call.tool_name == tools.TOOL_PASSAGE_CONTEXT and position:
        for key in ("paragraph_id", "page_no", "para_no"):
            if key not in params and position.get(key) is not None:
                params[key] = position[key]
                changed = True
    if not changed:
        return call
    return BiblioLibrarianToolCall(
        tool_name=call.tool_name,
        params=params,
        call_id=call.call_id,
        method=call.method,
    )


def _carried_document_id(result: tools.BiblioLibrarianToolResult) -> str:
    direct = str(getattr(result, "document_id", "") or "").strip()
    if direct:
        return direct
    ids: list[str] = []
    sources: tuple[Any, ...] = tuple(result.items)
    if result.document_summary:
        sources = sources + (result.document_summary,)
    for item in sources:
        if isinstance(item, Mapping):
            doc_id = str(item.get("document_id") or "").strip()
            if doc_id and doc_id not in ids:
                ids.append(doc_id)
    return ids[0] if len(ids) == 1 else ""


def _carried_position(result: tools.BiblioLibrarianToolResult) -> dict[str, Any]:
    if len(result.positions) != 1:
        if len(result.items) != 1:
            return {}
        position = result.items[0]
    else:
        position = result.positions[0]
    if not isinstance(position, Mapping):
        return {}
    return {
        key: position.get(key)
        for key in ("paragraph_id", "page_no", "para_no")
        if position.get(key) is not None
    }


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


def _duration_ms(started: float, monotonic: Any) -> int:
    return int(max((monotonic() - started) * 1000, 0))
