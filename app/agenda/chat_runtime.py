from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


AGENDA_PAYLOAD_KEY = 'agenda_enabled'
REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED = 'agenda_runtime_not_implemented'


def normalize_agenda_enabled(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    normalized = str(value or '').strip().lower()
    return normalized in {'1', 'true', 'yes', 'on', 'enabled', 'active'}


@dataclass(frozen=True)
class AgendaChatResult:
    enabled: bool
    used: bool
    status: str
    reason_code: str
    observability_payload: dict[str, Any]


def build_lot1_observability_payload(
    *,
    enabled: bool,
    status: str,
    reason_code: str,
) -> dict[str, Any]:
    return {
        'schema_version': 'frida_agenda_lot1_noop_v1',
        'enabled': bool(enabled),
        'used': False,
        'status': str(status or 'not_implemented'),
        'reason_code': str(reason_code or REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED),
        'runtime_available': False,
        'caldav_access': False,
        'nextcloud_access': False,
        'secret_access': False,
        'mutation_attempted': False,
        'content_free': True,
    }


def run_agenda_chat_turn(
    data: Mapping[str, Any],
    *,
    user_msg: str,
    conversation_id: Any = None,
    now_iso: str = '',
    config_module: Any = None,
) -> AgendaChatResult:
    del user_msg, conversation_id, now_iso, config_module
    enabled = normalize_agenda_enabled(data.get(AGENDA_PAYLOAD_KEY) if isinstance(data, Mapping) else None)
    if not enabled:
        payload = build_lot1_observability_payload(
            enabled=False,
            status='disabled',
            reason_code='agenda_toggle_off',
        )
        return AgendaChatResult(
            enabled=False,
            used=False,
            status='disabled',
            reason_code='agenda_toggle_off',
            observability_payload=payload,
        )
    payload = build_lot1_observability_payload(
        enabled=True,
        status='not_implemented',
        reason_code=REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED,
    )
    return AgendaChatResult(
        enabled=True,
        used=False,
        status='not_implemented',
        reason_code=REASON_TOGGLE_ON_RUNTIME_NOT_IMPLEMENTED,
        observability_payload=payload,
    )
