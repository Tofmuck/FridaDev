from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from agenda import agent_contract as contract
from agenda import product_methods
from agenda.observability import sha256_12


_SURFACE_TEXT_MAX_CHARS = 600
_INTENT_MAX_CHARS = 400
_ROOT_KEYS = {
    'schema_version',
    'product_method',
    'intent',
    'calendar_scope',
    'time_scope',
    'tool_calls',
    'mutation',
    'answer_mode',
    'risk_flags',
    'fallback_reason',
    'surface_intro',
    'surface_outro',
}
_CALENDAR_SCOPE_KEYS = {'calendar_ids', 'family_calendar', 'ambiguity'}
_TIME_SCOPE_KEYS = {'kind', 'start', 'end', 'timezone', 'ambiguity'}
_MUTATION_KEYS = {'requested', 'kind', 'confirmation_required', 'confirmation_level', 'pending_action_id'}
_CALL_KEYS = {'tool_name', 'method', 'params', 'call_id'}
_SAFE_CODE_CHARS = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-/')
_MUTATION_KINDS = {'none', 'create', 'update', 'delete'}
_CONFIRMATION_LEVELS = {'none', 'simple', 'reinforced'}
_ANSWER_MODES = {
    'agenda_summary',
    'agenda_details',
    'clarify',
    'proposal',
    'mutation_pending_confirmation',
    'mutation_refused',
    'fallback',
}
_FORBIDDEN_MARKERS = (
    'BEGIN:VCALENDAR',
    'BEGIN:VEVENT',
    'END:VEVENT',
    'UID:',
    'ETag:',
    'SUMMARY:',
    'LOCATION:',
    'DESCRIPTION:',
    'ATTENDEE:',
    'ORGANIZER:',
    'RECURRENCE-ID:',
    'RRULE:',
    'RDATE:',
    'EXDATE:',
    'DTSTART:',
    'DTEND:',
    'DTSTAMP:',
    'CREATED:',
    'LAST-MODIFIED:',
    'SEQUENCE:',
    'STATUS:',
    'TRANSP:',
    'CATEGORIES:',
    'CLASS:',
    'PRIORITY:',
    'Authorization',
    'Cookie:',
    'app-password',
    'app_password',
    'value_encrypted',
    'caldav_path',
    'caldav_url',
)
_FORBIDDEN_PARAM_KEYS = {
    'uid',
    'etag',
    'url',
    'href',
    'caldav_path',
    'caldav_url',
    'authorization',
    'cookie',
    'token',
    'app_password',
    'app-password',
    'ics',
    'raw_ics',
}
_TOOL_PARAM_CONTRACTS = {
    product_methods.TOOL_CALENDAR_LIST: {
        'allowed': set(),
        'required': set(),
        'int_bounds': {},
    },
    product_methods.TOOL_EVENT_QUERY_RANGE: {
        'allowed': {'calendar_id', 'start', 'end', 'timezone', 'max_days'},
        'required': {'start', 'end'},
        'int_bounds': {'max_days': (1, 31)},
    },
    product_methods.TOOL_EVENT_GET: {
        'allowed': {'event_id'},
        'required': {'event_id'},
        'int_bounds': {},
    },
    product_methods.TOOL_EVENT_SEARCH: {
        'allowed': {'query', 'calendar_id', 'limit'},
        'required': {'query'},
        'int_bounds': {'limit': (1, 50)},
    },
}


def parse_and_validate_agent_json(
    text: str,
    *,
    settings: contract.AgendaAgentSettings | None = None,
    finish_reason: str = '',
) -> contract.AgendaAgentValidation:
    raw = str(text or '')
    json_hash = sha256_12(raw)
    if str(finish_reason or '').strip().lower() == 'length':
        return _rejected(contract.REASON_JSON_TRUNCATED, raw, json_hash=json_hash, finish_reason=finish_reason)
    if not raw.strip():
        return _rejected(contract.REASON_JSON_ABSENT, raw, json_hash=json_hash, finish_reason=finish_reason)
    if not raw.lstrip().startswith('{'):
        return _rejected(contract.REASON_JSON_FREE_TEXT, raw, json_hash=json_hash, finish_reason=finish_reason)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _rejected(contract.REASON_JSON_INVALID, raw, json_hash=json_hash, finish_reason=finish_reason)
    validation = validate_agent_payload(payload, settings=settings)
    return contract.AgendaAgentValidation(
        status=validation.status,
        reason_code=validation.reason_code,
        plan=validation.plan,
        surface_intro=validation.surface_intro,
        surface_outro=validation.surface_outro,
        tool_names=validation.tool_names,
        json_chars=len(raw),
        json_hash=json_hash,
        finish_reason=finish_reason,
    )


def validate_agent_payload(
    payload: Mapping[str, Any],
    *,
    settings: contract.AgendaAgentSettings | None = None,
) -> contract.AgendaAgentValidation:
    settings = settings or contract.AgendaAgentSettings()
    if not isinstance(payload, Mapping) or set(payload.keys()) != _ROOT_KEYS:
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    if payload.get('schema_version') != contract.SCHEMA_VERSION:
        return _rejected(contract.REASON_SCHEMA_VERSION, '')
    product_method = _safe_code(payload.get('product_method'))
    method = product_methods.get_method(product_method)
    if method is None:
        return _rejected(contract.REASON_PRODUCT_METHOD_UNKNOWN, '')
    if not _valid_surface(payload.get('surface_intro')) or not _valid_surface(payload.get('surface_outro')):
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    if not _valid_text(payload.get('intent'), max_chars=_INTENT_MAX_CHARS):
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    calendar_scope = payload.get('calendar_scope')
    time_scope = payload.get('time_scope')
    mutation = payload.get('mutation')
    if not _valid_calendar_scope(calendar_scope) or not _valid_time_scope(time_scope):
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    if not isinstance(mutation, Mapping) or set(mutation.keys()) != _MUTATION_KEYS:
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    risk_flags = _risk_flags(payload.get('risk_flags'))
    if risk_flags is None:
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    answer_mode = _safe_code(payload.get('answer_mode'))
    if answer_mode not in _ANSWER_MODES:
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    fallback_reason = _safe_code(payload.get('fallback_reason'), allow_empty=True)
    if fallback_reason is None:
        return _rejected(contract.REASON_SCHEMA_INVALID, '')
    mutation_reason = _validate_mutation(method, mutation, calendar_scope, risk_flags)
    if mutation_reason:
        return _rejected(mutation_reason, '')
    tool_calls = _validate_tool_calls(payload.get('tool_calls'), product_method, settings)
    if isinstance(tool_calls, str):
        return _rejected(tool_calls, '')
    surface_intro = str(payload.get('surface_intro') or '')
    surface_outro = str(payload.get('surface_outro') or '')
    plan = contract.AgendaAgentPlan(
        product_method=product_method,
        intent=str(payload.get('intent') or ''),
        calendar_scope=dict(calendar_scope),
        time_scope=dict(time_scope),
        tool_calls=tuple(tool_calls),
        mutation=dict(mutation),
        answer_mode=answer_mode,
        risk_flags=tuple(risk_flags),
        fallback_reason=fallback_reason,
        surface_intro=surface_intro,
        surface_outro=surface_outro,
    )
    return contract.AgendaAgentValidation(
        status=contract.STATUS_VALIDATED,
        reason_code=contract.REASON_VALIDATED,
        plan=plan,
        surface_intro=surface_intro,
        surface_outro=surface_outro,
        tool_names=tuple(call.tool_name for call in tool_calls),
    )


def _rejected(
    reason_code: str,
    raw: str,
    *,
    json_hash: str = '',
    finish_reason: str = '',
) -> contract.AgendaAgentValidation:
    return contract.AgendaAgentValidation(
        status=contract.STATUS_REJECTED,
        reason_code=reason_code,
        json_chars=len(raw),
        json_hash=json_hash,
        finish_reason=finish_reason,
    )


def _safe_code(value: Any, *, allow_empty: bool = False, max_chars: int = 120) -> str | None:
    text = str(value or '').strip()
    if not text:
        return '' if allow_empty else None
    if len(text) > max_chars or any(char not in _SAFE_CODE_CHARS for char in text):
        return None
    return text


def _valid_surface(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > _SURFACE_TEXT_MAX_CHARS:
        return False
    return not _contains_forbidden_marker(value)


def _valid_text(value: Any, *, max_chars: int) -> bool:
    if not isinstance(value, str) or len(value) > max_chars:
        return False
    return not _contains_forbidden_marker(value)


def _contains_forbidden_marker(value: Any) -> bool:
    text = str(value or '')
    lower = text.lower()
    return any(marker.lower() in lower for marker in _FORBIDDEN_MARKERS)


def _valid_calendar_scope(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value.keys()) != _CALENDAR_SCOPE_KEYS:
        return False
    calendar_ids = value.get('calendar_ids')
    if not isinstance(calendar_ids, Sequence) or isinstance(calendar_ids, (str, bytes)):
        return False
    if len(calendar_ids) > 20 or any(_safe_code(item, max_chars=80) is None for item in calendar_ids):
        return False
    return (
        isinstance(value.get('family_calendar'), bool)
        and _safe_code(value.get('ambiguity'), allow_empty=True, max_chars=80) is not None
    )


def _valid_time_scope(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value.keys()) != _TIME_SCOPE_KEYS:
        return False
    for field_name in ('kind', 'timezone', 'ambiguity'):
        if _safe_code(value.get(field_name), allow_empty=True, max_chars=80) is None:
            return False
    for field_name in ('start', 'end'):
        raw = value.get(field_name)
        if not isinstance(raw, str) or len(raw) > 64 or _contains_forbidden_marker(raw):
            return False
        if raw and not _valid_iso(raw):
            return False
    return True


def _valid_iso(value: str) -> bool:
    try:
        datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return False
    return True


def _risk_flags(value: Any) -> tuple[str, ...] | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)) or len(value) > 12:
        return None
    flags: list[str] = []
    for item in value:
        flag = _safe_code(item, max_chars=80)
        if flag is None:
            return None
        flags.append(flag)
    return tuple(flags)


def _validate_mutation(
    method: product_methods.AgendaProductMethod,
    mutation: Mapping[str, Any],
    calendar_scope: Mapping[str, Any],
    risk_flags: tuple[str, ...],
) -> str:
    requested = mutation.get('requested')
    confirmation_required = mutation.get('confirmation_required')
    if not isinstance(requested, bool) or not isinstance(confirmation_required, bool):
        return contract.REASON_SCHEMA_INVALID
    kind = _safe_code(mutation.get('kind'))
    level = _safe_code(mutation.get('confirmation_level'))
    pending_action_id = _safe_code(mutation.get('pending_action_id'), allow_empty=True, max_chars=120)
    if kind not in _MUTATION_KINDS or level not in _CONFIRMATION_LEVELS or pending_action_id is None:
        return contract.REASON_SCHEMA_INVALID
    if method.family in {product_methods.FAMILY_READ, product_methods.FAMILY_CLARIFY, product_methods.FAMILY_CONTEXT}:
        if kind != 'none' or requested or confirmation_required or level != 'none' or pending_action_id:
            return contract.REASON_MUTATION_METHOD_MISMATCH
    if method.family == product_methods.FAMILY_PROPOSE:
        if requested:
            return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
        if kind not in {method.mutation_kind, 'none'}:
            return contract.REASON_MUTATION_METHOD_MISMATCH
        if kind == 'none' and (confirmation_required or level != 'none' or pending_action_id):
            return contract.REASON_MUTATION_METHOD_MISMATCH
    if kind == 'delete' and (not confirmation_required or level != 'reinforced'):
        return contract.REASON_DELETION_REQUIRES_REINFORCED_CONFIRMATION
    if requested and (not confirmation_required or level == 'none'):
        return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
    if requested and method.name not in product_methods.CONFIRMED_MUTATION_METHODS:
        return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
    if method.name in product_methods.CONFIRMED_MUTATION_METHODS:
        if not requested or method.mutation_kind != kind:
            return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
        if not pending_action_id:
            return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
    if method.mutation_kind != 'none' and kind not in {method.mutation_kind, 'none'}:
        return contract.REASON_SCHEMA_INVALID
    if bool(calendar_scope.get('family_calendar')) and kind != 'none':
        if 'family_calendar' not in risk_flags or not confirmation_required:
            return contract.REASON_MUTATION_REQUIRES_CONFIRMATION
    return ''

def _validate_tool_calls(
    value: Any,
    product_method: str,
    settings: contract.AgendaAgentSettings,
) -> tuple[contract.AgendaToolCall, ...] | str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return contract.REASON_SCHEMA_INVALID
    if len(value) > int(settings.max_tool_calls or 0):
        return contract.REASON_TOOL_NOT_EXECUTABLE
    allowed_for_method = product_methods.allowed_tools_for_method(product_method)
    calls: list[contract.AgendaToolCall] = []
    for raw_call in value:
        if not isinstance(raw_call, Mapping) or set(raw_call.keys()) != _CALL_KEYS:
            return contract.REASON_SCHEMA_INVALID
        tool_name = _safe_code(raw_call.get('tool_name'))
        if tool_name not in product_methods.READ_ONLY_TOOLS:
            return contract.REASON_TOOL_UNKNOWN
        if tool_name not in allowed_for_method:
            return contract.REASON_TOOL_FORBIDDEN
        method = _safe_code(raw_call.get('method'))
        if method != 'GET':
            return contract.REASON_METHOD_FORBIDDEN
        call_id = _safe_code(raw_call.get('call_id'), allow_empty=True, max_chars=120)
        if call_id is None:
            return contract.REASON_SCHEMA_INVALID
        param_error = _validate_tool_params(tool_name, raw_call.get('params'))
        if param_error:
            return param_error
        calls.append(
            contract.AgendaToolCall(
                tool_name=tool_name,
                method=method,
                params=dict(raw_call.get('params') or {}),
                call_id=call_id,
            )
        )
    return tuple(calls)


def _validate_tool_params(tool_name: str, value: Any) -> str:
    if not isinstance(value, Mapping):
        return contract.REASON_SCHEMA_INVALID
    tool_contract = _TOOL_PARAM_CONTRACTS[tool_name]
    keys = set(str(key) for key in value.keys())
    if keys & _FORBIDDEN_PARAM_KEYS or not keys.issubset(tool_contract['allowed']):
        return contract.REASON_TOOL_NOT_EXECUTABLE
    if not set(tool_contract['required']).issubset(keys):
        return contract.REASON_TOOL_NOT_EXECUTABLE
    for key, item in value.items():
        key_text = str(key)
        if key_text in tool_contract['int_bounds']:
            if not isinstance(item, int):
                return contract.REASON_TOOL_NOT_EXECUTABLE
            lower, upper = tool_contract['int_bounds'][key_text]
            if item < lower or item > upper:
                return contract.REASON_TOOL_NOT_EXECUTABLE
            continue
        if not _validate_tool_param_value(key_text, item):
            return contract.REASON_TOOL_NOT_EXECUTABLE
    return ''


def _validate_tool_param_value(key: str, value: Any) -> bool:
    if key in {'calendar_id', 'event_id'}:
        return _valid_local_identifier(value)
    if key in {'start', 'end'}:
        return isinstance(value, str) and len(value) <= 64 and not _dangerous_param_text(value) and _valid_iso(value)
    if key == 'timezone':
        return _valid_timezone(value)
    if key == 'query':
        return _valid_query(value)
    return isinstance(value, str) and len(value) <= 240 and not _dangerous_param_text(value)


def _valid_local_identifier(value: Any) -> bool:
    text = str(value or '').strip()
    if not text or len(text) > 80:
        return False
    if _dangerous_param_text(text):
        return False
    lowered = text.lower()
    if lowered.startswith(('uid:', 'uid=', 'etag:', 'etag=')):
        return False
    local_id_chars = set('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_:-')
    return all(char in local_id_chars for char in text)


def _valid_timezone(value: Any) -> bool:
    text = str(value or '').strip()
    if not text or len(text) > 80 or _dangerous_param_text(text):
        return False
    return _safe_code(text, max_chars=80) is not None


def _valid_query(value: Any) -> bool:
    text = str(value or '').strip()
    if not text or len(text) > 160:
        return False
    if any(char in text for char in '\r\n\t'):
        return False
    return not _dangerous_param_text(text)


def _dangerous_param_text(value: Any) -> bool:
    text = str(value or '').strip()
    lower = text.lower()
    if _contains_forbidden_marker(text):
        return True
    if '://' in lower or lower.startswith(('http:', 'https:', 'webcal:', 'caldav:')):
        return True
    if lower.startswith('/remote.php/') or '/remote.php/dav' in lower or '/calendars/' in lower:
        return True
    if '@' in text:
        return True
    if lower.startswith(('uid:', 'uid=', 'etag:', 'etag=')):
        return True
    if '"' in text or lower.startswith('w/'):
        return True
    secret_markers = ('authorization', 'bearer ', 'cookie', 'token', 'app-password', 'app_password')
    return any(marker in lower for marker in secret_markers)
