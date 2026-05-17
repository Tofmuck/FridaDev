from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import config
from admin import runtime_settings


@dataclass(frozen=True)
class WebReformulationRuntimeSettings:
    model: str
    temperature: float
    max_tokens: int
    timeout_s: int


def _payload_value(view: Any, field: str, default: Any) -> Any:
    payload = getattr(view, 'payload', {}) or {}
    field_payload = payload.get(field) or {}
    if 'value' in field_payload:
        return field_payload['value']
    return default


def get_runtime_settings(
    *,
    runtime_settings_module: Any = runtime_settings,
) -> WebReformulationRuntimeSettings:
    view = runtime_settings_module.get_web_reformulation_model_settings()
    return WebReformulationRuntimeSettings(
        model=str(_payload_value(view, 'model', config.WEB_REFORMULATION_MODEL) or config.WEB_REFORMULATION_MODEL),
        temperature=float(_payload_value(view, 'temperature', config.WEB_REFORMULATION_TEMPERATURE)),
        max_tokens=int(_payload_value(view, 'max_tokens', config.WEB_REFORMULATION_MAX_TOKENS)),
        timeout_s=int(_payload_value(view, 'timeout_s', config.WEB_REFORMULATION_TIMEOUT_S)),
    )
