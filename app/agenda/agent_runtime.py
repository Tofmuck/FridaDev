from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agenda import agent_contract as contract


STATUS_SKIPPED = 'skipped'
STATUS_ACTIVE_READY = 'active_ready'
STATUS_FALLBACK = 'fallback'

REASON_MODE_OFF = 'agenda_agent_mode_off'
REASON_MODE_UNSUPPORTED = 'agenda_agent_mode_unsupported'
REASON_SECRET_NOT_CONFIGURED = 'agenda_agent_secret_not_configured'
REASON_MODEL_NOT_CONFIGURED = 'agenda_agent_model_not_configured'
REASON_ACTIVE_VALIDATED = 'agenda_agent_active_validated'


@dataclass(frozen=True)
class AgendaAgentModelResponse:
    status: str
    reason_code: str
    content: str = ''
    finish_reason: str = ''
    attempt_count: int = 0

    def to_observability(self) -> dict[str, Any]:
        return {
            'status': self.status,
            'reason_code': self.reason_code,
            'content_present': bool(self.content),
            'content_chars': len(self.content),
            'content_hash': contract.sha256_12(self.content),
            'finish_reason': str(self.finish_reason or ''),
            'attempt_count': int(self.attempt_count or 0),
            'content_free': True,
        }


@dataclass(frozen=True)
class AgendaJsonAgentResult:
    status: str
    reason_code: str
    mode: str
    model_called: bool = False
    used_for_response: bool = False
    fallback_deterministic: bool = True
    validated_plan: Any = field(default=None, repr=False, compare=False)
    surface_intro: str = field(default='', repr=False, compare=False)
    surface_outro: str = field(default='', repr=False, compare=False)
    request_observation: dict[str, Any] = field(default_factory=dict)
    validation_observation: dict[str, Any] = field(default_factory=dict)
    model_observation: dict[str, Any] = field(default_factory=dict)

    def to_observability(self) -> dict[str, Any]:
        return {
            'schema_version': contract.SCHEMA_VERSION,
            'status': self.status,
            'reason_code': self.reason_code,
            'mode': self.mode,
            'model_called': self.model_called,
            'used_for_response': self.used_for_response,
            'fallback_deterministic': self.fallback_deterministic,
            'validated_plan_present': self.validated_plan is not None,
            'surface_intro_present': bool(self.surface_intro),
            'surface_intro_chars': len(self.surface_intro),
            'surface_intro_hash': contract.sha256_12(self.surface_intro),
            'surface_outro_present': bool(self.surface_outro),
            'surface_outro_chars': len(self.surface_outro),
            'surface_outro_hash': contract.sha256_12(self.surface_outro),
            'request': dict(self.request_observation),
            'validation': dict(self.validation_observation),
            'model': dict(self.model_observation),
            'caldav_access': False,
            'nextcloud_access': False,
            'secret_access': False,
            'mutation_attempted': False,
            'content_free': True,
        }


class NoopAgendaAgentModelClient:
    def complete(
        self,
        request: contract.AgendaAgentRequest,
        *,
        settings: contract.AgendaAgentSettings,
    ) -> AgendaAgentModelResponse:
        del request, settings
        return AgendaAgentModelResponse(
            status='error',
            reason_code=REASON_MODEL_NOT_CONFIGURED,
            content='',
            attempt_count=0,
        )


class AgendaJsonAgent:
    def __init__(self, model_client: Any | None = None) -> None:
        self._model_client = model_client or NoopAgendaAgentModelClient()

    def run(self, request: contract.AgendaAgentRequest) -> AgendaJsonAgentResult:
        settings = request.settings
        mode = settings.normalized_mode()
        request_observation = request.to_observability()
        if mode == contract.MODE_OFF:
            return AgendaJsonAgentResult(
                status=STATUS_SKIPPED,
                reason_code=REASON_MODE_OFF,
                mode=mode,
                request_observation=request_observation,
            )
        if mode != contract.MODE_ACTIVE:
            return AgendaJsonAgentResult(
                status=STATUS_FALLBACK,
                reason_code=REASON_MODE_UNSUPPORTED,
                mode=mode,
                request_observation=request_observation,
            )
        if not settings.caldav_secret_configured:
            return AgendaJsonAgentResult(
                status=STATUS_FALLBACK,
                reason_code=REASON_SECRET_NOT_CONFIGURED,
                mode=mode,
                request_observation=request_observation,
            )
        model_response = self._model_client.complete(request, settings=settings)
        model_observation = model_response.to_observability()
        model_called = int(model_observation.get('attempt_count') or 0) > 0
        if model_response.status != 'ok':
            return AgendaJsonAgentResult(
                status=STATUS_FALLBACK,
                reason_code=model_response.reason_code,
                mode=mode,
                model_called=model_called,
                request_observation=request_observation,
                model_observation=model_observation,
            )
        validation = contract.parse_and_validate_agent_json(
            model_response.content,
            settings=settings,
            canonical_time_windows=request.canonical_time_windows,
            finish_reason=model_response.finish_reason,
        )
        validation_observation = validation.to_observability()
        if validation.status != contract.STATUS_VALIDATED:
            return AgendaJsonAgentResult(
                status=STATUS_FALLBACK,
                reason_code=validation.reason_code,
                mode=mode,
                model_called=model_called,
                surface_intro=validation.surface_intro,
                surface_outro=validation.surface_outro,
                request_observation=request_observation,
                validation_observation=validation_observation,
                model_observation=model_observation,
            )
        return AgendaJsonAgentResult(
            status=STATUS_ACTIVE_READY,
            reason_code=REASON_ACTIVE_VALIDATED,
            mode=mode,
            model_called=model_called,
            used_for_response=False,
            fallback_deterministic=True,
            validated_plan=validation.plan,
            surface_intro=validation.surface_intro,
            surface_outro=validation.surface_outro,
            request_observation=request_observation,
            validation_observation=validation_observation,
            model_observation=model_observation,
        )
