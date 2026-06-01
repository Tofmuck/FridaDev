"""Comparative runtime wiring for the Biblio librarian agent.

Lot 8 keeps the deterministic Biblio path as the product controller.  This
module only builds a bounded agent request, runs the agent when its mode allows
it, and exposes a content-free comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from . import librarian_agent
from . import librarian_agent_contract as contract
from .librarian_planner_observability import clean as _clean
from .librarian_planner_observability import safe_observation as _safe_observation
from .librarian_planner_observability import safe_token as _safe_token


STATUS_SKIPPED = "skipped"
STATUS_EVALUATED = "evaluated"
STATUS_FALLBACK_DETERMINISTIC = "fallback_deterministic"

REASON_BIBLIO_DISABLED = "biblio_librarian_agent_biblio_disabled"
REASON_MODE_OFF = librarian_agent.REASON_MODE_OFF
REASON_EVALUATED = "biblio_librarian_agent_compared"


@dataclass(frozen=True)
class BiblioLibrarianAgentComparison:
    status: str
    reason_code: str
    settings: contract.BiblioLibrarianAgentSettings = field(default_factory=contract.BiblioLibrarianAgentSettings)
    request_observation: dict[str, Any] = field(default_factory=dict)
    deterministic_observation: dict[str, Any] = field(default_factory=dict)
    agent_result: librarian_agent.BiblioLibrarianAgentResult | None = field(default=None, repr=False, compare=False)
    tool_loop_result: Any = field(default=None, repr=False, compare=False)
    execution_scope: str = ""
    used_for_response_override: bool = False
    product_response_changed_override: bool = False

    @property
    def model_called(self) -> bool:
        return bool(self.agent_result and self.agent_result.model_called)

    @property
    def candidate_plan_present(self) -> bool:
        return bool(self.agent_result and self.agent_result.candidate_plan is not None)

    def to_observability(self) -> dict[str, Any]:
        agent_observation = self.agent_result.to_observability() if self.agent_result else {}
        loop_observation = self.tool_loop_result.to_observability() if self.tool_loop_result else {}
        tool_call_count = _int_value(loop_observation.get("tool_call_count"))
        used_for_response = bool(agent_observation.get("used_for_response") or self.used_for_response_override)
        product_response_changed = bool(self.product_response_changed_override)
        tool_execution_status = "not_executed"
        if loop_observation:
            tool_execution_status = "executed" if tool_call_count > 0 else _safe_token(loop_observation.get("status"))
        return _clean(
            {
                "present": True,
                "comparison_kind": "deterministic_comparison",
                "status": _safe_token(self.status),
                "reason_code": _safe_token(self.reason_code),
                "mode": contract.normalize_mode(self.settings.mode),
                "model_called": self.model_called,
                "candidate_plan_present": self.candidate_plan_present,
                "used_for_response": used_for_response,
                "deterministic_controller": not used_for_response,
                "product_response_changed": product_response_changed,
                "fallback_deterministic": True,
                "tool_execution_status": tool_execution_status,
                "tool_call_event_count": tool_call_count,
                "selection_event_count": 0,
                "state_update_event_count": 0,
                "final_event_count": 0,
                "agent_loop_executed": bool(loop_observation),
                "execution_scope": _safe_token(self.execution_scope),
                "request_observation": self.request_observation,
                "deterministic": self.deterministic_observation,
                "agent": agent_observation,
                "tool_loop": loop_observation,
            }
        )


def run_biblio_librarian_agent_comparison(
    *,
    biblio_enabled: bool,
    user_msg: str,
    recent_dialogue: Sequence[Mapping[str, Any]] = (),
    biblio_state: Any = None,
    deterministic_plan: Any = None,
    deterministic_status: str = "",
    deterministic_reason_code: str = "",
    deterministic_query_kind: str = "",
    config_module: Any = None,
    agent_factory: Any = librarian_agent.BiblioLibrarianAgent,
) -> BiblioLibrarianAgentComparison:
    settings = _resolve_settings(config_module)
    deterministic_observation = _deterministic_observation(
        plan=deterministic_plan,
        status=deterministic_status,
        reason_code=deterministic_reason_code,
        query_kind=deterministic_query_kind,
    )
    if not biblio_enabled:
        return BiblioLibrarianAgentComparison(
            status=STATUS_SKIPPED,
            reason_code=REASON_BIBLIO_DISABLED,
            settings=settings,
            deterministic_observation=deterministic_observation,
        )
    if contract.normalize_mode(settings.mode) == contract.MODE_OFF:
        return BiblioLibrarianAgentComparison(
            status=STATUS_SKIPPED,
            reason_code=REASON_MODE_OFF,
            settings=settings,
            deterministic_observation=deterministic_observation,
        )

    request = contract.BiblioLibrarianAgentRequest(
        user_message=user_msg,
        recent_dialogue=tuple(recent_dialogue),
        biblio_state=biblio_state,
        deterministic_plan=deterministic_observation,
        settings=settings,
    )
    agent_result = agent_factory().run(request)
    status = STATUS_EVALUATED
    if agent_result.status == librarian_agent.STATUS_FALLBACK_DETERMINISTIC:
        status = STATUS_FALLBACK_DETERMINISTIC
    return BiblioLibrarianAgentComparison(
        status=status,
        reason_code=REASON_EVALUATED if status == STATUS_EVALUATED else agent_result.reason_code,
        settings=settings,
        request_observation=request.to_observability(),
        deterministic_observation=deterministic_observation,
        agent_result=agent_result,
    )


def _resolve_settings(config_module: Any = None) -> contract.BiblioLibrarianAgentSettings:
    if config_module is None:
        return contract.BiblioLibrarianAgentSettings.from_runtime_settings()
    if bool(getattr(config_module, "_runtime_settings_mode_override", False)):
        return contract.BiblioLibrarianAgentSettings.from_runtime_settings(
            mode_override=getattr(config_module, "BIBLIO_LIBRARIAN_AGENT_MODE", None)
        )
    return contract.BiblioLibrarianAgentSettings.from_config(config_module)


def _int_value(value: Any) -> int:
    if type(value) is int:
        return value
    if isinstance(value, str) and value.isdecimal():
        return int(value)
    return 0


def _deterministic_observation(
    *,
    plan: Any,
    status: str,
    reason_code: str,
    query_kind: str,
) -> dict[str, Any]:
    plan_observation: dict[str, Any] = {}
    to_observability = getattr(plan, "to_observability", None)
    if callable(to_observability):
        try:
            raw_plan = to_observability()
            if isinstance(raw_plan, Mapping):
                plan_observation = _safe_observation(raw_plan)
        except Exception:
            plan_observation = {
                "status": "error",
                "reason_code": "biblio_librarian_agent_deterministic_projection_error",
            }
    elif isinstance(plan, Mapping):
        plan_observation = _safe_observation(plan)
    return _clean(
        {
            "status": _safe_token(status),
            "reason_code": _safe_token(reason_code),
            "query_kind": _safe_token(query_kind),
            "plan": plan_observation,
        }
    )
