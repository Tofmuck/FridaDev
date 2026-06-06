"""Biblio librarian agent orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from . import librarian_agent_contract as contract
from . import librarian_agent_openrouter as openrouter
from .librarian_planner_observability import clean as _clean


STATUS_SKIPPED = "skipped"
STATUS_SHADOW_READY = "shadow_ready"
STATUS_CANDIDATE_READY = "candidate_ready"
STATUS_ACTIVE_READY = "active_ready"
STATUS_FALLBACK_DETERMINISTIC = "fallback_deterministic"

REASON_MODE_OFF = "biblio_librarian_agent_mode_off"
REASON_MODE_UNSUPPORTED = "biblio_librarian_agent_mode_unsupported"
REASON_MODEL_CALL_BUDGET_EXHAUSTED = "biblio_librarian_agent_model_call_budget_exhausted"
REASON_SHADOW_VALIDATED = "biblio_librarian_agent_shadow_validated"
REASON_CANDIDATE_VALIDATED = "biblio_librarian_agent_candidate_validated"
REASON_ACTIVE_VALIDATED = "biblio_librarian_agent_active_validated"


@dataclass(frozen=True)
class BiblioLibrarianAgentResult:
    status: str
    reason_code: str
    mode: str
    model_called: bool = False
    used_for_response: bool = False
    fallback_deterministic: bool = True
    candidate_plan: Any = field(default=None, repr=False, compare=False)
    validation_observation: dict[str, Any] = field(default_factory=dict)
    model_observation: dict[str, Any] = field(default_factory=dict)

    def to_observability(self) -> dict[str, Any]:
        return _clean(
            {
                "schema_version": contract.SCHEMA_VERSION,
                "status": self.status,
                "reason_code": self.reason_code,
                "mode": self.mode,
                "model_called": self.model_called,
                "used_for_response": self.used_for_response,
                "fallback_deterministic": self.fallback_deterministic,
                "candidate_plan_present": self.candidate_plan is not None,
                "validation": self.validation_observation,
                "model": self.model_observation,
            }
        )


class BiblioLibrarianAgent:
    def __init__(
        self,
        model_client: Any | None = None,
    ) -> None:
        self._model_client = model_client or openrouter.OpenRouterBiblioLibrarianAgentClient()

    def run(self, request: contract.BiblioLibrarianAgentRequest) -> BiblioLibrarianAgentResult:
        mode = contract.normalize_mode(request.settings.mode)
        if mode == contract.MODE_OFF:
            return BiblioLibrarianAgentResult(
                status=STATUS_SKIPPED,
                reason_code=REASON_MODE_OFF,
                mode=mode,
                model_called=False,
                fallback_deterministic=True,
            )
        if request.settings.max_model_calls < 1:
            return BiblioLibrarianAgentResult(
                status=STATUS_FALLBACK_DETERMINISTIC,
                reason_code=REASON_MODEL_CALL_BUDGET_EXHAUSTED,
                mode=mode,
                model_called=False,
                fallback_deterministic=True,
            )

        model_response = self._model_client.complete(request, settings=request.settings)
        model_observation = model_response.to_observability()
        provider_called = _provider_called(model_observation)
        if model_response.status != openrouter.STATUS_OK:
            return BiblioLibrarianAgentResult(
                status=STATUS_FALLBACK_DETERMINISTIC,
                reason_code=model_response.reason_code,
                mode=mode,
                model_called=provider_called,
                fallback_deterministic=True,
                model_observation=model_observation,
            )

        validation = contract.parse_and_validate_agent_json(
            model_response.content,
            settings=request.settings,
            finish_reason=model_response.finish_reason,
        )
        validation_observation = validation.to_observability()
        if validation.status != contract.STATUS_VALIDATED:
            return BiblioLibrarianAgentResult(
                status=STATUS_FALLBACK_DETERMINISTIC,
                reason_code=validation.reason_code,
                mode=mode,
                model_called=provider_called,
                fallback_deterministic=True,
                validation_observation=validation_observation,
                model_observation=model_observation,
            )

        if mode == contract.MODE_SHADOW:
            return BiblioLibrarianAgentResult(
                status=STATUS_SHADOW_READY,
                reason_code=REASON_SHADOW_VALIDATED,
                mode=mode,
                model_called=provider_called,
                fallback_deterministic=True,
                candidate_plan=validation.plan,
                validation_observation=validation_observation,
                model_observation=model_observation,
            )
        if mode == contract.MODE_CANDIDATE:
            return BiblioLibrarianAgentResult(
                status=STATUS_CANDIDATE_READY,
                reason_code=REASON_CANDIDATE_VALIDATED,
                mode=mode,
                model_called=provider_called,
                fallback_deterministic=True,
                candidate_plan=validation.plan,
                validation_observation=validation_observation,
                model_observation=model_observation,
            )
        if mode == contract.MODE_ACTIVE:
            return BiblioLibrarianAgentResult(
                status=STATUS_ACTIVE_READY,
                reason_code=REASON_ACTIVE_VALIDATED,
                mode=mode,
                model_called=provider_called,
                fallback_deterministic=True,
                candidate_plan=validation.plan,
                validation_observation=validation_observation,
                model_observation=model_observation,
            )
        return BiblioLibrarianAgentResult(
            status=STATUS_FALLBACK_DETERMINISTIC,
            reason_code=REASON_MODE_UNSUPPORTED,
            mode=mode,
            model_called=False,
            fallback_deterministic=True,
        )


def _provider_called(model_observation: dict[str, Any]) -> bool:
    try:
        return int(model_observation.get("attempt_count") or 0) > 0
    except (TypeError, ValueError):
        return False
