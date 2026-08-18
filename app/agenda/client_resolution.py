from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from agenda import (
    agent_contract,
    agent_openrouter,
    caldav_transport,
    proposal_execution,
    read_execution,
    runtime_config,
)


@dataclass(frozen=True)
class AgendaClientResolution:
    client: Any = field(default=None, repr=False, compare=False)
    live_caldav: bool = False
    status: str = 'unavailable'
    reason_code: str = ''
    error_class: str = ''

    @property
    def is_error(self) -> bool:
        return self.status == 'error'


def resolve_agent_model_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    injected_client: Any = None,
    runtime_settings_module: Any = None,
    llm_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> Any:
    if injected_client:
        return injected_client
    if settings.normalized_mode() != agent_contract.MODE_ACTIVE:
        return None
    if not settings.caldav_secret_configured:
        return None
    post = getattr(requests_module, 'post', None)
    if not callable(post) or llm_module is None or runtime_settings_module is None:
        return None
    return agent_openrouter.OpenRouterAgendaAgentClient(
        llm_module=llm_module,
        runtime_settings_module=runtime_settings_module,
        requests_post=post,
        config_module=config_module,
    )


def resolve_read_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    injected_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> AgendaClientResolution:
    if injected_client is not None:
        return AgendaClientResolution(client=injected_client, live_caldav=False, status='ok')
    if settings.normalized_mode() != agent_contract.MODE_ACTIVE:
        return AgendaClientResolution()
    if not settings.caldav_secret_configured:
        return AgendaClientResolution()
    if runtime_settings_module is None or requests_module is None:
        return AgendaClientResolution()
    secret_reader = getattr(runtime_settings_module, 'get_runtime_secret_value', None)
    if not callable(secret_reader):
        return AgendaClientResolution()
    try:
        secret = secret_reader(
            runtime_config.AGENDA_AGENT_SECTION,
            runtime_config.CALDAV_APP_PASSWORD_FIELD,
        )
        app_password = str(getattr(secret, 'value', '') or '')
        if not app_password:
            return AgendaClientResolution()
        return AgendaClientResolution(
            client=caldav_transport.build_live_caldav_read_client(
                account=settings.caldav_account,
                app_password=app_password,
                requests_module=requests_module,
                config_module=config_module,
            ),
            live_caldav=True,
            status='ok',
        )
    except Exception as exc:
        return AgendaClientResolution(
            status='error',
            reason_code=read_execution.REASON_CLIENT_RESOLUTION_ERROR,
            error_class=exc.__class__.__name__,
        )


def resolve_proposal_read_client(
    *,
    settings: agent_contract.AgendaAgentSettings,
    plan: agent_contract.AgendaAgentPlan,
    injected_client: Any = None,
    runtime_settings_module: Any = None,
    requests_module: Any = None,
    config_module: Any = None,
) -> AgendaClientResolution:
    if not proposal_execution.plan_can_attempt_target_verification(
        plan,
        injected_client=injected_client is not None,
    ) and not (
        injected_client is not None
        and proposal_execution.plan_can_attempt_calendar_classification(plan)
    ):
        return AgendaClientResolution()
    return resolve_read_client(
        settings=settings,
        injected_client=injected_client,
        runtime_settings_module=runtime_settings_module,
        requests_module=requests_module,
        config_module=config_module,
    )
