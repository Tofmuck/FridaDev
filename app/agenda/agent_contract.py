from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from agenda import product_methods, runtime_config
from agenda.observability import sha256_12


SCHEMA_VERSION = 'frida_agenda_agent_v1'

MODE_OFF = runtime_config.AGENDA_AGENT_DEFAULT_MODE
MODE_ACTIVE = 'active'
ALLOWED_MODES = {MODE_OFF, MODE_ACTIVE}

STATUS_VALIDATED = 'validated'
STATUS_REJECTED = 'rejected'

REASON_VALIDATED = 'agenda_agent_json_validated'
REASON_JSON_ABSENT = 'agenda_agent_json_absent'
REASON_JSON_INVALID = 'agenda_agent_json_invalid'
REASON_JSON_FREE_TEXT = 'agenda_agent_free_text'
REASON_JSON_TRUNCATED = 'agenda_agent_json_truncated'
REASON_SCHEMA_VERSION = 'agenda_agent_schema_version_invalid'
REASON_SCHEMA_INVALID = 'agenda_agent_schema_invalid'
REASON_PRODUCT_METHOD_UNKNOWN = 'agenda_agent_product_method_unknown'
REASON_TOOL_UNKNOWN = 'agenda_agent_unknown_tool'
REASON_TOOL_FORBIDDEN = 'agenda_agent_forbidden_tool'
REASON_METHOD_FORBIDDEN = 'agenda_agent_forbidden_method'
REASON_TOOL_NOT_EXECUTABLE = 'agenda_agent_tool_not_executable'
REASON_MUTATION_REQUIRES_CONFIRMATION = 'agenda_agent_mutation_requires_confirmation'
REASON_MUTATION_METHOD_MISMATCH = 'agenda_agent_mutation_method_mismatch'
REASON_DELETION_REQUIRES_REINFORCED_CONFIRMATION = 'agenda_agent_deletion_requires_reinforced_confirmation'
REASON_TIME_WINDOW_MISMATCH = 'agenda_agent_time_window_mismatch'
REASON_DRAFT_INVALID = 'agenda_agent_draft_invalid'

_RECENT_DIALOGUE_MAX_TURNS = 8


@dataclass(frozen=True)
class AgendaAgentSettings:
    mode: str = MODE_OFF
    caldav_account: str = runtime_config.CALDAV_ACCOUNT_V1
    caldav_secret_configured: bool = False
    max_tool_calls: int = 4
    max_model_calls: int = 1
    max_recent_turns: int = _RECENT_DIALOGUE_MAX_TURNS
    source: str = ''
    source_reason: str = ''

    @classmethod
    def from_runtime_settings(
        cls,
        *,
        runtime_settings_module: Any = None,
        fetcher: Any = None,
    ) -> 'AgendaAgentSettings':
        if runtime_settings_module is None:
            return cls(source='local_default', source_reason='runtime_settings_unavailable')
        getter = getattr(runtime_settings_module, 'get_agenda_agent_settings', None)
        if not callable(getter):
            return cls(source='local_default', source_reason='runtime_settings_getter_missing')
        try:
            view = getter(fetcher=fetcher) if fetcher is not None else getter()
        except Exception:
            return cls(source='local_default', source_reason='runtime_settings_error')
        payload = getattr(view, 'payload', {}) or {}
        if not isinstance(payload, Mapping):
            payload = {}
        mode = _field_value(payload, 'mode') or MODE_OFF
        account = _field_value(payload, 'caldav_account') or runtime_config.CALDAV_ACCOUNT_V1
        secret_payload = payload.get(runtime_config.CALDAV_APP_PASSWORD_FIELD) or {}
        secret_configured = bool(secret_payload.get('is_set')) if isinstance(secret_payload, Mapping) else False
        return cls(
            mode=str(mode or MODE_OFF).strip().lower() or MODE_OFF,
            caldav_account=str(account or runtime_config.CALDAV_ACCOUNT_V1).strip() or runtime_config.CALDAV_ACCOUNT_V1,
            caldav_secret_configured=secret_configured,
            source=str(getattr(view, 'source', '') or ''),
            source_reason=str(getattr(view, 'source_reason', '') or ''),
        )

    def normalized_mode(self) -> str:
        return str(self.mode or MODE_OFF).strip().lower() or MODE_OFF


@dataclass(frozen=True)
class AgendaAgentRequest:
    user_message: str
    recent_dialogue: tuple[dict[str, Any], ...] = ()
    now_iso: str = ''
    timezone: str = 'UTC'
    canonical_time_windows: Mapping[str, Any] | None = None
    available_calendars: tuple[dict[str, Any], ...] = ()
    agenda_state: Mapping[str, Any] | None = None
    settings: AgendaAgentSettings = field(default_factory=AgendaAgentSettings)

    def bounded_recent_dialogue(self) -> tuple[dict[str, Any], ...]:
        turns = tuple(turn for turn in self.recent_dialogue if isinstance(turn, Mapping))
        return turns[-int(self.settings.max_recent_turns or _RECENT_DIALOGUE_MAX_TURNS):]

    def to_observability(self) -> dict[str, Any]:
        recent = self.bounded_recent_dialogue()
        return {
            'schema_version': SCHEMA_VERSION,
            'user_message_hash': sha256_12(self.user_message),
            'user_message_chars': len(str(self.user_message or '')),
            'recent_turn_count': len(recent),
            'recent_turn_hashes': [sha256_12(turn.get('content')) for turn in recent],
            'now_iso_present': bool(self.now_iso),
            'timezone': str(self.timezone or ''),
            'canonical_time_window_keys': sorted((self.canonical_time_windows or {}).keys()),
            'canonical_time_windows_present': bool(self.canonical_time_windows),
            'available_calendar_count': len(self.available_calendars),
            'agenda_state_present': bool(self.agenda_state),
            'content_free': True,
        }


@dataclass(frozen=True)
class AgendaToolCall:
    tool_name: str
    method: str
    params: Mapping[str, Any]
    call_id: str = ''


@dataclass(frozen=True)
class AgendaAgentPlan:
    product_method: str
    intent: str
    calendar_scope: Mapping[str, Any]
    time_scope: Mapping[str, Any]
    tool_calls: tuple[AgendaToolCall, ...]
    draft: Mapping[str, Any]
    mutation: Mapping[str, Any]
    answer_mode: str
    risk_flags: tuple[str, ...]
    fallback_reason: str
    surface_intro: str
    surface_outro: str

    def to_observability(self) -> dict[str, Any]:
        calendar_ids = tuple(self.calendar_scope.get('calendar_ids') or ())
        method = product_methods.get_method(self.product_method)
        return {
            'product_method': self.product_method,
            'method_family': method.family if method is not None else '',
            'intent_hash': sha256_12(self.intent),
            'intent_chars': len(str(self.intent or '')),
            'calendar_count': len(calendar_ids),
            'calendar_id_hashes': [sha256_12(calendar_id) for calendar_id in calendar_ids],
            'family_calendar': bool(self.calendar_scope.get('family_calendar')),
            'calendar_ambiguity': str(self.calendar_scope.get('ambiguity') or ''),
            'time_kind': str(self.time_scope.get('kind') or ''),
            'window_start': str(self.time_scope.get('start') or ''),
            'window_end': str(self.time_scope.get('end') or ''),
            'timezone': str(self.time_scope.get('timezone') or ''),
            'time_ambiguity': str(self.time_scope.get('ambiguity') or ''),
            'tool_count': len(self.tool_calls),
            'tool_names': [call.tool_name for call in self.tool_calls],
            'draft_present': bool(self.draft),
            'draft_field_names': sorted(str(key) for key, value in self.draft.items() if value not in ('', None, False)),
            'draft_title_hash': sha256_12(self.draft.get('title')),
            'draft_title_chars': len(str(self.draft.get('title') or '')),
            'draft_description_present': bool(self.draft.get('description')),
            'mutation_requested': bool(self.mutation.get('requested')),
            'mutation_kind': str(self.mutation.get('kind') or ''),
            'confirmation_required': bool(self.mutation.get('confirmation_required')),
            'confirmation_level': str(self.mutation.get('confirmation_level') or ''),
            'pending_action_present': bool(self.mutation.get('pending_action_id')),
            'pending_action_hash': sha256_12(self.mutation.get('pending_action_id')),
            'answer_mode': self.answer_mode,
            'risk_flags': list(self.risk_flags),
            'fallback_reason': self.fallback_reason,
            'surface_intro_present': bool(self.surface_intro),
            'surface_intro_chars': len(self.surface_intro),
            'surface_intro_hash': sha256_12(self.surface_intro),
            'surface_outro_present': bool(self.surface_outro),
            'surface_outro_chars': len(self.surface_outro),
            'surface_outro_hash': sha256_12(self.surface_outro),
            'content_free': True,
        }


@dataclass(frozen=True)
class AgendaAgentValidation:
    status: str
    reason_code: str
    plan: AgendaAgentPlan | None = None
    surface_intro: str = ''
    surface_outro: str = ''
    tool_names: tuple[str, ...] = ()
    json_chars: int = 0
    json_hash: str = ''
    finish_reason: str = ''

    def to_observability(self) -> dict[str, Any]:
        return {
            'schema_version': SCHEMA_VERSION,
            'status': self.status,
            'reason_code': self.reason_code,
            'validated': self.status == STATUS_VALIDATED,
            'tool_names': list(self.tool_names),
            'json_chars': self.json_chars,
            'json_hash': self.json_hash,
            'finish_reason': str(self.finish_reason or ''),
            'surface_intro_present': bool(self.surface_intro),
            'surface_intro_chars': len(self.surface_intro),
            'surface_intro_hash': sha256_12(self.surface_intro),
            'surface_outro_present': bool(self.surface_outro),
            'surface_outro_chars': len(self.surface_outro),
            'surface_outro_hash': sha256_12(self.surface_outro),
            'plan': self.plan.to_observability() if self.plan is not None else {},
            'content_free': True,
        }


def parse_and_validate_agent_json(
    text: str,
    *,
    settings: AgendaAgentSettings | None = None,
    canonical_time_windows: Mapping[str, Any] | None = None,
    finish_reason: str = '',
) -> AgendaAgentValidation:
    from agenda import agent_validation

    return agent_validation.parse_and_validate_agent_json(
        text,
        settings=settings,
        canonical_time_windows=canonical_time_windows,
        finish_reason=finish_reason,
    )


def validate_agent_payload(
    payload: Mapping[str, Any],
    *,
    settings: AgendaAgentSettings | None = None,
    canonical_time_windows: Mapping[str, Any] | None = None,
) -> AgendaAgentValidation:
    from agenda import agent_validation

    return agent_validation.validate_agent_payload(
        payload,
        settings=settings,
        canonical_time_windows=canonical_time_windows,
    )


def _field_value(payload: Mapping[str, Any], field: str) -> Any:
    field_payload = payload.get(field) or {}
    if not isinstance(field_payload, Mapping):
        return None
    return field_payload.get('value')
