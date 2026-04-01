from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping

import requests

import config
from core import llm_client
from core import prompt_loader


SCHEMA_VERSION = 'v1'
PRIMARY_MODEL = 'openai/gpt-5.4-mini'
FALLBACK_MODEL = 'openai/gpt-5.4-nano'
PROMPT_PATH = 'prompts/stimmung_agent.txt'
REQUEST_TIMEOUT_S = 10

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


def _build_messages(*, system_prompt: str, user_msg: str) -> list[dict[str, str]]:
    return [
        {'role': 'system', 'content': str(system_prompt or '')},
        {'role': 'user', 'content': f'Tour utilisateur courant :\n{str(user_msg or "").strip()}'},
    ]


def _extract_response_text(response: Any) -> str:
    try:
        return llm_client._sanitize_encoding(response.json()['choices'][0]['message']['content']).strip()
    except (KeyError, IndexError, TypeError, AttributeError) as exc:
        raise _SignalJsonError('invalid_json') from exc


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
    model: str,
    requests_module: Any,
) -> dict[str, Any]:
    response = requests_module.post(
        f'{config.OR_BASE}/chat/completions',
        json={
            'model': model,
            'messages': _build_messages(system_prompt=system_prompt, user_msg=user_msg),
            'temperature': 0.1,
            'top_p': 1.0,
            'max_tokens': 220,
        },
        headers=llm_client.or_headers(caller='stimmung_agent'),
        timeout=REQUEST_TIMEOUT_S,
    )
    response.raise_for_status()
    return _validate_affective_turn_signal(_safe_json_loads(_extract_response_text(response)))


def build_affective_turn_signal(
    *,
    user_msg: str,
    recent_window_input_payload: Mapping[str, Any] | None = None,
    requests_module: Any = requests,
) -> StimmungAgentResult:
    del recent_window_input_payload

    system_prompt = _load_system_prompt()
    if not system_prompt:
        return _build_fail_open_result(reason_code='prompt_missing', model=PRIMARY_MODEL)

    last_reason_code = 'upstream_error'
    for model, decision_source in (
        (PRIMARY_MODEL, 'primary'),
        (FALLBACK_MODEL, 'fallback'),
    ):
        try:
            signal = _call_model(
                system_prompt=system_prompt,
                user_msg=user_msg,
                model=model,
                requests_module=requests_module,
            )
            return StimmungAgentResult(
                signal=signal,
                status='ok',
                model=model,
                decision_source=decision_source,
                reason_code=None,
            )
        except _SignalJsonError as exc:
            last_reason_code = str(exc) or 'invalid_json'
        except _SignalValidationError as exc:
            last_reason_code = str(exc) or 'validation_error'
        except Exception as exc:
            last_reason_code = _request_reason_code(exc, requests_module)

    return _build_fail_open_result(reason_code=last_reason_code, model=FALLBACK_MODEL)
