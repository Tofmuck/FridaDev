from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from typing import Any

from agenda import agent_contract as contract
from agenda import agent_runtime
from agenda import product_methods


STATUS_OK = 'ok'
STATUS_ERROR = 'error'

REASON_OK = 'agenda_agent_model_ok'
REASON_MODEL_NOT_CONFIGURED = 'agenda_agent_model_not_configured'
REASON_PROVIDER_NOT_CONFIGURED = 'agenda_agent_provider_not_configured'
REASON_PROVIDER_ERROR = 'agenda_agent_provider_error'
REASON_INVALID_RESPONSE = 'agenda_agent_provider_invalid_response'


class OpenRouterAgendaAgentClient:
    def __init__(
        self,
        *,
        llm_module: Any,
        runtime_settings_module: Any,
        requests_post: Callable[..., Any],
        config_module: Any = None,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        self._llm = llm_module
        self._runtime_settings = runtime_settings_module
        self._requests_post = requests_post
        self._config = config_module
        self._monotonic = monotonic

    def complete(
        self,
        request: contract.AgendaAgentRequest,
        *,
        settings: contract.AgendaAgentSettings,
    ) -> agent_runtime.AgendaAgentModelResponse:
        del settings
        try:
            model, max_tokens = _main_model_fields(self._runtime_settings)
        except Exception:
            return _model_error(REASON_MODEL_NOT_CONFIGURED)
        if not model:
            return _model_error(REASON_MODEL_NOT_CONFIGURED)
        try:
            headers = self._provider_headers()
            url = self._chat_completions_url()
        except Exception:
            return _model_error(REASON_PROVIDER_NOT_CONFIGURED)

        started = self._monotonic()
        try:
            response = self._requests_post(
                url,
                headers=headers,
                json=build_agenda_agent_payload(
                    request,
                    model=model,
                    max_tokens=max_tokens,
                ),
                timeout=_timeout_s(self._config),
            )
        except Exception:
            return _model_error(REASON_PROVIDER_ERROR, attempt_count=1)
        status_code = getattr(response, 'status_code', None)
        duration_ms = int((self._monotonic() - started) * 1000)
        if status_code is not None and int(status_code) >= 400:
            return _model_error(REASON_PROVIDER_ERROR, status_code=int(status_code), duration_ms=duration_ms, attempt_count=1)
        try:
            data = response.json()
        except (TypeError, ValueError):
            return _model_error(REASON_INVALID_RESPONSE, status_code=status_code, duration_ms=duration_ms, attempt_count=1)
        choice = _first_choice(data)
        message = choice.get('message') if isinstance(choice.get('message'), Mapping) else {}
        content = str(message.get('content') or '')
        finish_reason = str(choice.get('finish_reason') or '')
        if not content:
            return _model_error(REASON_INVALID_RESPONSE, status_code=status_code, duration_ms=duration_ms, attempt_count=1)
        return agent_runtime.AgendaAgentModelResponse(
            status=STATUS_OK,
            reason_code=REASON_OK,
            content=content,
            finish_reason=finish_reason,
            status_code=status_code,
            response_chars=len(content),
            duration_ms=duration_ms,
            attempt_count=1,
        )

    def _provider_headers(self) -> dict[str, Any]:
        custom = getattr(self._llm, 'or_headers_custom', None)
        if callable(custom):
            return custom(
                caller='agenda_agent',
                referer='https://fridadev.frida-system.fr/openrouter/agenda-agent',
                title='FridaDev / Agenda Agent',
            )
        headers = getattr(self._llm, 'or_headers', None)
        if callable(headers):
            return headers(caller='llm')
        raise RuntimeError('llm headers unavailable')

    def _chat_completions_url(self) -> str:
        url_builder = getattr(self._llm, 'or_chat_completions_url', None)
        if callable(url_builder):
            return str(url_builder())
        base = str(getattr(self._config, 'OR_BASE', '') or '').rstrip('/')
        if not base:
            raise RuntimeError('OpenRouter base URL unavailable')
        return f'{base}/chat/completions'


def build_agenda_agent_payload(
    request: contract.AgendaAgentRequest,
    *,
    model: str,
    max_tokens: int,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        'model': str(model or ''),
        'messages': build_agenda_agent_messages(request),
        'max_tokens': int(max_tokens or 700),
        'response_format': build_agenda_agent_response_format(
            max_tool_calls=int(request.settings.max_tool_calls or 4),
        ),
        'provider': {'require_parameters': True},
        'metadata': {
            'frida_caller': 'agenda_agent',
            'frida_contract': contract.SCHEMA_VERSION,
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': 'FridaDev / Agenda Agent',
        },
    }
    if _model_supports_sampling(str(model or '')):
        payload['temperature'] = 0.0
        payload['top_p'] = 1.0
    return payload


def build_agenda_agent_messages(request: contract.AgendaAgentRequest) -> list[dict[str, str]]:
    recent = [
        {
            'role': str(turn.get('role') or ''),
            'content': str(turn.get('content') or ''),
        }
        for turn in request.bounded_recent_dialogue()
    ]
    user_payload = {
        'user_message': request.user_message,
        'recent_dialogue': recent,
        'now_iso': request.now_iso,
        'timezone': request.timezone,
        'canonical_time_windows': dict(request.canonical_time_windows or {}),
        'available_calendars': list(request.available_calendars),
        'agenda_state': dict(request.agenda_state or {}),
    }
    system = (
        'Tu es le planificateur Agenda de FridaDev. '
        'Tu produis uniquement un JSON strict conforme a frida_agenda_agent_v1. '
        'Tu choisis une methode produit Agenda et seulement des outils GET '
        'read-only allowlistes. Tu ne demandes jamais de mutation executee. '
        'Pour preparer une creation, modification ou suppression future, utilise '
        'propose_create_event, propose_update_event ou propose_delete_event: '
        'cela cree une proposition en attente cote FridaDev, sans ecriture CalDAV. '
        'Pour propose_create_event, remplis draft avec title, start, end, timezone '
        'et calendar_id si connu. Pour propose_update_event ou propose_reschedule, '
        'fournis event_query_range ou event_search si necessaire puis event_get '
        'sur la cible locale, et remplis draft avec change_summary et les nouveaux '
        'champs proposes. Pour propose_delete_event, relis aussi la cible par '
        'event_query_range ou event_search puis event_get; la suppression ne sera pas executee. '
        'Pour une suppression, confirmation_level doit etre reinforced. '
        'Pour confirm_create_event, confirm_update_event et confirm_delete_event, '
        'fournis seulement un pending_action_id deja connu; le deterministe ne '
        'fera aucune ecriture avant le lot de confirmation. '
        'Pour cancel_pending_agenda_action, fournis pending_action_id avec '
        'mutation.kind=none et requested=false. '
        'Pour lire une fenetre, utilise event_query_range avec start et end ISO '
        'explicites. Si le calendrier cible est inconnu, omets calendar_id: '
        'le deterministe interrogera les calendriers accessibles. '
        'Pour read_today et read_tomorrow, utilise exactement les fenetres '
        'canonical_time_windows.today ou canonical_time_windows.tomorrow. '
        'Pour search_events, fournis deux tool_calls: d abord event_query_range '
        'avec start/end/timezone explicites pour constituer le pool borne, puis '
        'event_search avec query, limit et eventuellement calendar_id seulement; '
        'ne mets jamais start, end ou timezone dans les params event_search. '
        'surface_intro et surface_outro sont toujours des strings, eventuellement vides.'
    )
    return [
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': json.dumps(user_payload, ensure_ascii=False, sort_keys=True)},
    ]


def build_agenda_agent_response_format(*, max_tool_calls: int) -> dict[str, Any]:
    return {
        'type': 'json_schema',
        'json_schema': {
            'name': contract.SCHEMA_VERSION,
            'strict': True,
            'schema': _agenda_agent_json_schema(max_tool_calls=max_tool_calls),
        },
    }


def _agenda_agent_json_schema(*, max_tool_calls: int) -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': [
            'schema_version',
            'product_method',
            'intent',
            'calendar_scope',
            'time_scope',
            'tool_calls',
            'draft',
            'mutation',
            'answer_mode',
            'risk_flags',
            'fallback_reason',
            'surface_intro',
            'surface_outro',
        ],
        'properties': {
            'schema_version': {'type': 'string', 'enum': [contract.SCHEMA_VERSION]},
            'product_method': {'type': 'string', 'enum': sorted(product_methods.PRODUCT_METHODS)},
            'intent': {'type': 'string', 'maxLength': 400},
            'calendar_scope': _calendar_scope_schema(),
            'time_scope': _time_scope_schema(),
            'tool_calls': _tool_calls_schema(max_tool_calls=max_tool_calls),
            'draft': _draft_schema(),
            'mutation': _mutation_schema(),
            'answer_mode': {
                'type': 'string',
                'enum': [
                    'agenda_summary',
                    'agenda_details',
                    'clarify',
                    'proposal',
                    'mutation_pending_confirmation',
                    'mutation_refused',
                    'fallback',
                ],
            },
            'risk_flags': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 12},
            'fallback_reason': {'type': 'string', 'maxLength': 120},
            'surface_intro': {'type': 'string', 'maxLength': 600},
            'surface_outro': {'type': 'string', 'maxLength': 600},
        },
    }


def _calendar_scope_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['calendar_ids', 'family_calendar', 'ambiguity'],
        'properties': {
            'calendar_ids': {'type': 'array', 'items': {'type': 'string'}, 'maxItems': 20},
            'family_calendar': {'type': 'boolean'},
            'ambiguity': {'type': 'string', 'maxLength': 80},
        },
    }


def _time_scope_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['kind', 'start', 'end', 'timezone', 'ambiguity'],
        'properties': {
            'kind': {'type': 'string', 'maxLength': 80},
            'start': {'type': 'string', 'maxLength': 64},
            'end': {'type': 'string', 'maxLength': 64},
            'timezone': {'type': 'string', 'maxLength': 80},
            'ambiguity': {'type': 'string', 'maxLength': 80},
        },
    }


def _tool_calls_schema(*, max_tool_calls: int) -> dict[str, Any]:
    return {
        'type': 'array',
        'maxItems': int(max_tool_calls or 4),
        'items': {
            'type': 'object',
            'additionalProperties': False,
            'required': ['tool_name', 'method', 'params', 'call_id'],
            'properties': {
                'tool_name': {'type': 'string', 'enum': sorted(product_methods.READ_ONLY_TOOLS)},
                'method': {'type': 'string', 'enum': ['GET']},
                'params': _tool_params_schema(),
                'call_id': {'type': 'string', 'maxLength': 120},
            },
        },
    }


def _tool_params_schema() -> dict[str, Any]:
    properties = {
        'calendar_id': _nullable_text_schema(max_chars=80),
        'event_id': _nullable_text_schema(max_chars=80),
        'start': _nullable_text_schema(max_chars=64),
        'end': _nullable_text_schema(max_chars=64),
        'timezone': _nullable_text_schema(max_chars=80),
        'query': _nullable_text_schema(max_chars=160),
        'max_days': _nullable_integer_schema(minimum=1, maximum=31),
        'limit': _nullable_integer_schema(minimum=1, maximum=50),
    }
    return {
        'type': 'object',
        'additionalProperties': False,
        'description': 'Utilise null pour toute cle non employee; ne fournis une valeur que pour les params reels de l outil choisi.',
        'required': sorted(properties.keys()),
        'properties': properties,
    }


def _mutation_schema() -> dict[str, Any]:
    return {
        'type': 'object',
        'additionalProperties': False,
        'required': ['requested', 'kind', 'confirmation_required', 'confirmation_level', 'pending_action_id'],
        'properties': {
            'requested': {'type': 'boolean'},
            'kind': {'type': 'string', 'enum': ['none', 'create', 'update', 'delete']},
            'confirmation_required': {'type': 'boolean'},
            'confirmation_level': {'type': 'string', 'enum': ['none', 'simple', 'reinforced']},
            'pending_action_id': {'type': 'string', 'maxLength': 120},
        },
    }


def _draft_schema() -> dict[str, Any]:
    properties = {
        'title': _nullable_text_schema(max_chars=160),
        'location': _nullable_text_schema(max_chars=240),
        'description': _nullable_text_schema(max_chars=800),
        'calendar_id': _nullable_text_schema(max_chars=80),
        'start': _nullable_text_schema(max_chars=64),
        'end': _nullable_text_schema(max_chars=64),
        'timezone': _nullable_text_schema(max_chars=80),
        'all_day': {'type': ['boolean', 'null']},
        'target_event_id': _nullable_text_schema(max_chars=80),
        'change_summary': _nullable_text_schema(max_chars=400),
    }
    return {
        'type': 'object',
        'additionalProperties': False,
        'description': 'Brouillon structure pour les propositions futures; null pour les champs non employes.',
        'required': sorted(properties.keys()),
        'properties': properties,
    }


def _main_model_fields(runtime_settings_module: Any) -> tuple[str, int]:
    getter = getattr(runtime_settings_module, 'get_main_model_settings', None)
    if not callable(getter):
        return '', 700
    view = getter()
    payload = getattr(view, 'payload', {}) or {}
    model = str(((payload.get('model') or {}).get('value')) or '').strip()
    max_tokens = _int_value((payload.get('response_max_tokens') or {}).get('value'), default=700)
    return model, min(max_tokens, 900)


def _timeout_s(config_module: Any) -> int:
    return _int_value(getattr(config_module, 'TIMEOUT_S', 20), default=20)


def _int_value(value: Any, *, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _model_supports_sampling(model: str) -> bool:
    return not str(model or '').strip().lower().startswith('openai/gpt-5')


def _nullable_text_schema(*, max_chars: int) -> dict[str, Any]:
    return {
        'type': ['string', 'null'],
        'maxLength': int(max_chars),
    }


def _nullable_integer_schema(*, minimum: int, maximum: int) -> dict[str, Any]:
    return {
        'type': ['integer', 'null'],
        'minimum': int(minimum),
        'maximum': int(maximum),
    }


def _first_choice(data: Any) -> Mapping[str, Any]:
    if not isinstance(data, Mapping):
        return {}
    choices = data.get('choices')
    if not isinstance(choices, list) or not choices:
        return {}
    first = choices[0]
    return first if isinstance(first, Mapping) else {}


def _model_error(
    reason_code: str,
    *,
    status_code: Any = None,
    response_chars: int = 0,
    duration_ms: int = 0,
    attempt_count: int = 0,
) -> agent_runtime.AgendaAgentModelResponse:
    try:
        normalized_status_code = int(status_code) if status_code is not None else None
    except (TypeError, ValueError):
        normalized_status_code = None
    return agent_runtime.AgendaAgentModelResponse(
        status=STATUS_ERROR,
        reason_code=reason_code,
        content='',
        status_code=normalized_status_code,
        response_chars=int(response_chars or 0),
        duration_ms=int(duration_ms or 0),
        attempt_count=attempt_count,
    )
