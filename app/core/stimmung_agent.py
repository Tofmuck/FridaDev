from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
from typing import Any, Mapping

import requests

from admin import runtime_settings
from core.hermeneutic_node.inputs import recent_window_input as canonical_recent_window_input
from core import llm_client
from core import prompt_loader

logger = logging.getLogger('frida.stimmung_agent')

SCHEMA_VERSION = 'v1'
PRIMARY_MODEL = 'openai/gpt-5.4-mini'
FALLBACK_MODEL = 'openai/gpt-5.4-nano'
PROMPT_PATH = 'prompts/stimmung_agent.txt'
REQUEST_TIMEOUT_S = 10
CONTEXT_WINDOW_TURNS = canonical_recent_window_input.MAX_RECENT_TURNS
MAX_CONTEXT_MESSAGE_CHARS = 220
MAX_CURRENT_TURN_CHARS = 600
RUNTIME_SETTINGS_SECTION = 'stimmung_agent_model'

ALLOWED_TONES = (
    'apaisement',
    'enthousiasme',
    'curiosite',
    'confusion',
    'frustration',
    'colere',
    'anxiete',
    'decouragement',
    'neutralite',
)

_ALLOWED_TONE_SET = set(ALLOWED_TONES)
_ALLOWED_SIGNAL_KEYS = {
    'schema_version',
    'present',
    'tones',
    'dominant_tone',
    'confidence',
}
_ALLOWED_TONE_KEYS = {'tone', 'strength'}


@dataclass(frozen=True)
class StimmungAgentResult:
    signal: dict[str, Any]
    status: str
    model: str
    decision_source: str
    reason_code: str | None = None
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class _SignalJsonError(ValueError):
    pass


class _SignalValidationError(ValueError):
    pass


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _extract_json_blob(raw: Any) -> str:
    text = str(raw or '').strip()
    if text.startswith('```'):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        text = '\n'.join(lines).strip()

    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end >= start:
        return text[start : end + 1]
    return text


def _safe_json_loads(raw: Any) -> dict[str, Any]:
    try:
        payload = json.loads(_extract_json_blob(raw))
    except json.JSONDecodeError as exc:
        raise _SignalJsonError('invalid_json') from exc
    if not isinstance(payload, dict):
        raise _SignalJsonError('invalid_json')
    return payload


def _as_strength(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise _SignalValidationError('validation_error')
    if value < 1 or value > 10:
        raise _SignalValidationError('validation_error')
    return int(value)


def _as_confidence(value: Any) -> float:
    if isinstance(value, bool):
        raise _SignalValidationError('validation_error')
    try:
        confidence = float(value)
    except (TypeError, ValueError) as exc:
        raise _SignalValidationError('validation_error') from exc
    if confidence < 0.0 or confidence > 1.0:
        raise _SignalValidationError('validation_error')
    return confidence


def _build_fail_open_signal() -> dict[str, Any]:
    return {
        'schema_version': SCHEMA_VERSION,
        'present': False,
        'tones': [],
        'dominant_tone': None,
        'confidence': 0.0,
    }


def _build_fail_open_result(*, reason_code: str, model: str) -> StimmungAgentResult:
    return StimmungAgentResult(
        signal=_build_fail_open_signal(),
        status='error',
        model=str(model or FALLBACK_MODEL),
        decision_source='fail_open',
        reason_code=str(reason_code or 'upstream_error'),
    )


def _load_system_prompt() -> str:
    return prompt_loader.read_prompt_text(PROMPT_PATH)


def _runtime_model_settings() -> dict[str, Any]:
    view = runtime_settings.get_stimmung_agent_model_settings()
    return {
        'primary_model': str(view.payload['primary_model']['value']),
        'fallback_model': str(view.payload['fallback_model']['value']),
        'timeout_s': int(view.payload['timeout_s']['value']),
        'temperature': float(view.payload['temperature']['value']),
        'top_p': float(view.payload['top_p']['value']),
        'max_tokens': int(view.payload['max_tokens']['value']),
    }


def _compact_text(value: Any, *, max_chars: int) -> str:
    text = ' '.join(str(value or '').split())
    if len(text) <= max_chars:
        return text
    return f"{text[: max(0, max_chars - 3)].rstrip()}..."


def _is_duplicate_current_turn(turn_payload: Mapping[str, Any], user_msg: str) -> bool:
    raw_messages = turn_payload.get('messages')
    if not isinstance(raw_messages, list) or len(raw_messages) != 1:
        return False

    message_payload = _mapping(raw_messages[0])
    if str(message_payload.get('role') or '') != 'user':
        return False

    return _compact_text(message_payload.get('content'), max_chars=MAX_CURRENT_TURN_CHARS) == _compact_text(
        user_msg,
        max_chars=MAX_CURRENT_TURN_CHARS,
    )


def _serialize_recent_window(*, recent_window_input_payload: Mapping[str, Any] | None, user_msg: str) -> str:
    payload = _mapping(recent_window_input_payload)
    raw_turns = payload.get('turns')
    if not isinstance(raw_turns, list):
        return f"Aucun contexte recent exploitable ({CONTEXT_WINDOW_TURNS} tours max)."

    turns = [_mapping(item) for item in raw_turns if isinstance(item, Mapping)]
    if turns and _is_duplicate_current_turn(turns[-1], user_msg):
        turns = turns[:-1]
    turns = turns[-CONTEXT_WINDOW_TURNS:]

    if not turns:
        return f"Aucun contexte recent exploitable ({CONTEXT_WINDOW_TURNS} tours max)."

    lines = [f"Fenetre conversationnelle locale ({CONTEXT_WINDOW_TURNS} tours max) :"]
    for index, turn_payload in enumerate(turns, start=1):
        turn_status = str(turn_payload.get('turn_status') or 'unknown')
        lines.append(f"- Tour {index} [{turn_status}]")
        raw_messages = turn_payload.get('messages')
        if not isinstance(raw_messages, list):
            continue
        for message in raw_messages:
            message_payload = _mapping(message)
            role = str(message_payload.get('role') or '').strip()
            content = _compact_text(message_payload.get('content'), max_chars=MAX_CONTEXT_MESSAGE_CHARS)
            if role in {'user', 'assistant'} and content:
                lines.append(f"  - {role}: {content}")

    return '\n'.join(lines)


def _build_messages(
    *,
    system_prompt: str,
    user_msg: str,
    recent_window_input_payload: Mapping[str, Any] | None,
) -> list[dict[str, str]]:
    contextual_window = _serialize_recent_window(
        recent_window_input_payload=recent_window_input_payload,
        user_msg=user_msg,
    )
    return [
        {'role': 'system', 'content': str(system_prompt or '')},
        {
            'role': 'user',
            'content': (
                f"{contextual_window}\n\n"
                "Tour utilisateur courant (centre de l'analyse, signal a produire pour ce tour) :\n"
                f"{_compact_text(user_msg, max_chars=MAX_CURRENT_TURN_CHARS)}"
            ),
        },
    ]


def _validate_affective_turn_signal(data: Mapping[str, Any]) -> dict[str, Any]:
    payload = _mapping(data)
    if set(payload.keys()) != _ALLOWED_SIGNAL_KEYS:
        raise _SignalValidationError('validation_error')

    schema_version = str(payload.get('schema_version') or '')
    if schema_version != SCHEMA_VERSION:
        raise _SignalValidationError('validation_error')

    present = payload.get('present')
    if not isinstance(present, bool):
        raise _SignalValidationError('validation_error')

    raw_tones = payload.get('tones')
    if not isinstance(raw_tones, list):
        raise _SignalValidationError('validation_error')

    tones: list[dict[str, Any]] = []
    tone_names: list[str] = []
    seen_tones: set[str] = set()
    for item in raw_tones:
        tone_payload = _mapping(item)
        if set(tone_payload.keys()) != _ALLOWED_TONE_KEYS:
            raise _SignalValidationError('validation_error')

        tone = str(tone_payload.get('tone') or '').strip()
        if tone not in _ALLOWED_TONE_SET:
            raise _SignalValidationError('validation_error')

        strength = _as_strength(tone_payload.get('strength'))
        if tone in seen_tones:
            continue
        seen_tones.add(tone)
        tone_names.append(tone)
        tones.append({'tone': tone, 'strength': strength})

    confidence = _as_confidence(payload.get('confidence'))
    dominant_tone = payload.get('dominant_tone')

    if present:
        if not tones:
            raise _SignalValidationError('validation_error')
        if not isinstance(dominant_tone, str) or dominant_tone not in tone_names:
            raise _SignalValidationError('validation_error')
    else:
        if tones:
            raise _SignalValidationError('validation_error')
        if dominant_tone is not None:
            raise _SignalValidationError('validation_error')

    return {
        'schema_version': SCHEMA_VERSION,
        'present': present,
        'tones': tones,
        'dominant_tone': dominant_tone,
        'confidence': confidence,
    }


def _request_reason_code(exc: Exception, requests_module: Any) -> str:
    exceptions = getattr(requests_module, 'exceptions', None)
    timeout_cls = getattr(exceptions, 'Timeout', None)
    request_cls = getattr(exceptions, 'RequestException', None)
    if timeout_cls is not None and isinstance(exc, timeout_cls):
        return 'timeout'
    if request_cls is not None and isinstance(exc, request_cls):
        return 'http_error'
    return 'upstream_error'


def _call_model(
    *,
    system_prompt: str,
    user_msg: str,
    recent_window_input_payload: Mapping[str, Any] | None,
    model: str,
    timeout_s: int,
    temperature: float,
    top_p: float,
    max_tokens: int,
    requests_module: Any,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = requests_module.post(
        llm_client.or_chat_completions_url(),
        json={
            'model': model,
            'messages': _build_messages(
                system_prompt=system_prompt,
                user_msg=user_msg,
                recent_window_input_payload=recent_window_input_payload,
            ),
            'temperature': temperature,
            'top_p': top_p,
            'max_tokens': max_tokens,
        },
        headers=llm_client.or_headers(caller='stimmung_agent'),
        timeout=timeout_s,
    )
    response.raise_for_status()
    response_payload = llm_client.read_openrouter_response_payload(response)
    provider_metadata = llm_client.extract_openrouter_provider_metadata(
        response_payload,
        requested_model=model,
    )
    llm_client.log_provider_metadata(logger, 'stimmung_agent_provider_response', provider_metadata)
    return (
        _validate_affective_turn_signal(_safe_json_loads(llm_client.extract_openrouter_text(response_payload))),
        provider_metadata,
    )


def build_affective_turn_signal(
    *,
    user_msg: str,
    recent_window_input_payload: Mapping[str, Any] | None = None,
    requests_module: Any = requests,
) -> StimmungAgentResult:
    runtime_model_settings = _runtime_model_settings()
    system_prompt = _load_system_prompt()
    if not system_prompt:
        return _build_fail_open_result(
            reason_code='prompt_missing',
            model=runtime_model_settings['primary_model'],
        )

    last_reason_code = 'upstream_error'
    for model, decision_source in (
        (runtime_model_settings['primary_model'], 'primary'),
        (runtime_model_settings['fallback_model'], 'fallback'),
    ):
        try:
            signal, provider_metadata = _call_model(
                system_prompt=system_prompt,
                user_msg=user_msg,
                recent_window_input_payload=recent_window_input_payload,
                model=model,
                timeout_s=runtime_model_settings['timeout_s'],
                temperature=runtime_model_settings['temperature'],
                top_p=runtime_model_settings['top_p'],
                max_tokens=runtime_model_settings['max_tokens'],
                requests_module=requests_module,
            )
            return StimmungAgentResult(
                signal=signal,
                status='ok',
                model=model,
                decision_source=decision_source,
                reason_code=None,
                provider_metadata=provider_metadata,
            )
        except _SignalJsonError as exc:
            last_reason_code = str(exc) or 'invalid_json'
        except _SignalValidationError as exc:
            last_reason_code = str(exc) or 'validation_error'
        except Exception as exc:
            last_reason_code = _request_reason_code(exc, requests_module)

    return _build_fail_open_result(
        reason_code=last_reason_code,
        model=runtime_model_settings['fallback_model'],
    )
