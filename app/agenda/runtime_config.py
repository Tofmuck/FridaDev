from __future__ import annotations

from collections.abc import Mapping
from typing import Any


AGENDA_AGENT_SECTION = 'agenda_agent'
AGENDA_AGENT_MODES = ('off', 'active')
AGENDA_AGENT_DEFAULT_MODE = 'off'
CALDAV_ACCOUNT_V1 = 'tof'
CALDAV_APP_PASSWORD_FIELD = 'caldav_app_password'
RUNTIME_READ_MODEL_SCHEMA = 'frida_agenda_runtime_settings_v1'


def normalize_agent_mode(value: Any) -> str:
    mode = str(value or '').strip().lower()
    return mode or AGENDA_AGENT_DEFAULT_MODE


def agent_mode_is_valid(value: Any) -> bool:
    return normalize_agent_mode(value) in AGENDA_AGENT_MODES


def redacted_secret_state(
    payload: Mapping[str, Any],
    *,
    secret_sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    secret_payload = payload.get(CALDAV_APP_PASSWORD_FIELD) or {}
    if not isinstance(secret_payload, Mapping):
        secret_payload = {}
    source = str((secret_sources or {}).get(CALDAV_APP_PASSWORD_FIELD) or '').strip() or 'missing'
    configured = bool(secret_payload.get('is_set'))
    return {
        'field': CALDAV_APP_PASSWORD_FIELD,
        'configured': configured,
        'source_configured': source != 'missing',
        'source': source,
        'redacted': True,
    }


def build_admin_read_model(
    payload: Mapping[str, Any],
    *,
    source: str,
    source_reason: str,
    secret_sources: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    mode_payload = payload.get('mode') or {}
    account_payload = payload.get('caldav_account') or {}
    mode = normalize_agent_mode(mode_payload.get('value') if isinstance(mode_payload, Mapping) else None)
    account = str(account_payload.get('value') if isinstance(account_payload, Mapping) else '').strip()
    if not account:
        account = CALDAV_ACCOUNT_V1
    return {
        'schema_version': RUNTIME_READ_MODEL_SCHEMA,
        'section': AGENDA_AGENT_SECTION,
        'mode': mode,
        'mode_allowed': mode in AGENDA_AGENT_MODES,
        'caldav_identity': {
            'account': account,
            'account_kind': 'human_nextcloud_user',
            'service_account': False,
        },
        'caldav_secret': redacted_secret_state(payload, secret_sources=secret_sources),
        'caldav_access': False,
        'nextcloud_access': False,
        'content_free': True,
        'source': str(source or ''),
        'source_reason': str(source_reason or ''),
    }
