#!/usr/bin/env python3
from typing import Any, Mapping

import config
from admin import runtime_settings

INTERNAL_PROVIDER_CALLER_HEADER = 'X-Frida-Caller'
_KNOWN_PROVIDER_CALLERS = (
    'llm',
    'web_reformulation',
    'arbiter',
    'identity_extractor',
    'resumer',
    'stimmung_agent',
    'validation_agent',
)
_PROVIDER_TITLE_FIELD_MAP = {
    'llm': 'title_llm',
    'web_reformulation': '',
    'arbiter': 'title_arbiter',
    'identity_extractor': 'title_identity_extractor',
    'resumer': 'title_resumer',
    'stimmung_agent': 'title_stimmung_agent',
    'validation_agent': 'title_validation_agent',
}
_PROVIDER_DEFAULT_TITLE_MAP = {
    'llm': config.OR_TITLE_LLM,
    'web_reformulation': config.OR_TITLE_WEB_REFORMULATION,
    'arbiter': config.OR_TITLE_ARBITER,
    'identity_extractor': config.OR_TITLE_IDENTITY_EXTRACTOR,
    'resumer': config.OR_TITLE_RESUMER,
    'stimmung_agent': config.OR_TITLE_STIMMUNG_AGENT,
    'validation_agent': config.OR_TITLE_VALIDATION_AGENT,
}
_PROVIDER_REFERER_FIELD_MAP = {
    'llm': 'referer_llm',
    'web_reformulation': '',
    'arbiter': 'referer_arbiter',
    'identity_extractor': 'referer_identity_extractor',
    'resumer': 'referer_resumer',
    'stimmung_agent': 'referer_stimmung_agent',
    'validation_agent': 'referer_validation_agent',
}
_PROVIDER_DEFAULT_REFERER_MAP = {
    'llm': config.OR_REFERER_LLM,
    'web_reformulation': config.OR_REFERER_WEB_REFORMULATION,
    'arbiter': config.OR_REFERER_ARBITER,
    'identity_extractor': config.OR_REFERER_IDENTITY_EXTRACTOR,
    'resumer': config.OR_REFERER_RESUMER,
    'stimmung_agent': config.OR_REFERER_STIMMUNG_AGENT,
    'validation_agent': config.OR_REFERER_VALIDATION_AGENT,
}


def _sanitize_encoding(text: str) -> str:
    """Corrige les chaînes doublement encodées type 'Ã§' si nécessaire."""
    if not isinstance(text, str):
        return text
    try:
        repaired = text.encode("latin-1").decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return text
    if repaired == text or "\ufffd" in repaired:
        return text
    return repaired


def _runtime_main_api_key() -> str:
    secret = runtime_settings.get_runtime_secret_value('main_model', 'api_key')
    return str(secret.value)


def _runtime_main_view():
    return runtime_settings.get_main_model_settings()


def _runtime_main_base_url() -> str:
    view = _runtime_main_view()
    payload = view.payload.get('base_url') or {}
    return str(payload.get('value') or config.OR_BASE).rstrip('/')


def _runtime_main_title(caller: str) -> str:
    caller_key = normalize_provider_caller(caller)
    view = _runtime_main_view()
    field_name = _PROVIDER_TITLE_FIELD_MAP.get(caller_key, 'title_llm')
    payload = view.payload.get(field_name) or {}
    title = str(payload.get('value') or '').strip()
    return title or _PROVIDER_DEFAULT_TITLE_MAP.get(caller_key, config.OR_TITLE_LLM)


def _runtime_main_referer(caller: str) -> str:
    caller_key = normalize_provider_caller(caller)
    view = _runtime_main_view()
    field_name = _PROVIDER_REFERER_FIELD_MAP.get(caller_key, 'referer_llm')
    component_payload = view.payload.get(field_name) if field_name else None
    component_referer = str((component_payload or {}).get('value') or '').strip()
    if component_referer:
        return component_referer

    default_component_referer = str(
        _PROVIDER_DEFAULT_REFERER_MAP.get(caller_key, config.OR_REFERER_LLM) or ''
    ).strip()
    if not field_name:
        return default_component_referer or str(config.OR_REFERER or '').strip()

    legacy_payload = view.payload.get('referer') or {}
    legacy_referer = str(legacy_payload.get('value') or '').strip()
    if legacy_referer:
        return legacy_referer

    return default_component_referer or str(config.OR_REFERER or '').strip()


def resolve_provider_title(caller: str = "llm") -> str:
    return _runtime_main_title(caller)


def resolve_provider_referer(caller: str = "llm") -> str:
    return _runtime_main_referer(caller)


def normalize_provider_caller(caller: Any) -> str:
    caller_key = str(caller or 'llm').strip().lower()
    if caller_key in _KNOWN_PROVIDER_CALLERS:
        return caller_key
    return 'llm'


def resolve_provider_caller_from_headers(headers: Mapping[str, Any] | None) -> str:
    header_map = _mapping(headers)
    internal_caller = str(header_map.get(INTERNAL_PROVIDER_CALLER_HEADER) or '').strip()
    if internal_caller:
        return normalize_provider_caller(internal_caller)

    provider_title = str(
        header_map.get('X-OpenRouter-Title') or header_map.get('X-Title') or ''
    ).strip()
    if provider_title:
        provider_title_key = provider_title.casefold()
        for caller in _KNOWN_PROVIDER_CALLERS:
            if resolve_provider_title(caller).casefold() == provider_title_key:
                return caller
    return 'llm'


def strip_internal_provider_headers(headers: Mapping[str, Any] | None) -> dict[str, Any]:
    sanitized_headers = dict(_mapping(headers))
    sanitized_headers.pop(INTERNAL_PROVIDER_CALLER_HEADER, None)
    return sanitized_headers


def or_headers(caller: str = "llm") -> dict:
    """Construit les headers HTTP pour OpenRouter, selon le composant appelant."""
    caller_key = normalize_provider_caller(caller)
    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_runtime_main_api_key()}",
        INTERNAL_PROVIDER_CALLER_HEADER: caller_key,
    }
    referer = resolve_provider_referer(caller_key)
    if referer:
        h["HTTP-Referer"] = referer
    title = _runtime_main_title(caller_key)
    if title:
        h["X-OpenRouter-Title"] = title
        h["X-Title"] = title
    return h


def or_chat_completions_url() -> str:
    return f"{_runtime_main_base_url()}/chat/completions"


def _mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return value
    return {}


def _int_or_none(value: Any) -> int | None:
    if isinstance(value, bool) or value is None:
        return None
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def read_openrouter_response_payload(response: Any) -> dict[str, Any]:
    payload = response.json()
    if not isinstance(payload, Mapping):
        raise TypeError('provider response payload must be a mapping')
    return dict(payload)


def extract_openrouter_text(payload: Any) -> str:
    data = _mapping(payload)
    return _sanitize_encoding(data['choices'][0]['message']['content']).strip()


def extract_openrouter_provider_metadata(
    payload: Any,
    *,
    requested_model: str | None = None,
) -> dict[str, Any]:
    data = _mapping(payload)
    metadata: dict[str, Any] = {}

    model_fallback = str(requested_model or '').strip()
    if model_fallback:
        metadata['provider_model'] = model_fallback

    generation_id = str(data.get('id') or '').strip()
    if generation_id:
        metadata['provider_generation_id'] = generation_id

    provider_model = str(data.get('model') or '').strip()
    if provider_model:
        metadata['provider_model'] = provider_model

    usage = _mapping(data.get('usage'))
    token_fields = (
        ('prompt_tokens', 'provider_prompt_tokens'),
        ('completion_tokens', 'provider_completion_tokens'),
        ('total_tokens', 'provider_total_tokens'),
    )
    for source_key, target_key in token_fields:
        parsed = _int_or_none(usage.get(source_key))
        if parsed is not None:
            metadata[target_key] = parsed

    return metadata


def build_provider_observability_fields(
    *,
    caller: str,
    provider_metadata: Any,
) -> dict[str, Any]:
    caller_value = str(caller or 'llm').strip() or 'llm'
    fields = {'provider_caller': caller_value}
    title = resolve_provider_title(caller_value)
    if title:
        fields['provider_title'] = title
    fields.update(dict(_mapping(provider_metadata)))
    return fields


def _caller_from_provider_event_name(event_name: str) -> str:
    event_key = str(event_name or '').strip().lower()
    return {
        'llm_provider_response': 'llm',
        'arbiter_provider_response': 'arbiter',
        'identity_extractor_provider_response': 'identity_extractor',
        'summarizer_provider_response': 'resumer',
        'stimmung_agent_provider_response': 'stimmung_agent',
        'validation_agent_provider_response': 'validation_agent',
    }.get(event_key, 'llm')


def merge_openrouter_provider_metadata(
    current: Any,
    payload: Any,
    *,
    requested_model: str | None = None,
) -> dict[str, Any]:
    merged = dict(_mapping(current))
    merged.update(extract_openrouter_provider_metadata(payload, requested_model=requested_model))
    return merged


def log_provider_metadata(logger: Any, event_name: str, provider_metadata: Any) -> None:
    metadata = dict(_mapping(provider_metadata))
    log_info = getattr(logger, 'info', None)
    if not metadata or not callable(log_info):
        return
    provider_caller = str(metadata.get('provider_caller') or '').strip()
    if not provider_caller:
        provider_caller = _caller_from_provider_event_name(event_name)
        metadata['provider_caller'] = provider_caller
    provider_title = str(metadata.get('provider_title') or '').strip()
    if not provider_title:
        provider_title = resolve_provider_title(provider_caller)
        if provider_title:
            metadata['provider_title'] = provider_title
    log_info(
        '%s provider_caller=%s provider_title=%s provider_generation_id=%s provider_model=%s provider_prompt_tokens=%s provider_completion_tokens=%s provider_total_tokens=%s',
        str(event_name or 'provider_response'),
        provider_caller,
        provider_title,
        str(metadata.get('provider_generation_id') or ''),
        str(metadata.get('provider_model') or ''),
        metadata.get('provider_prompt_tokens'),
        metadata.get('provider_completion_tokens'),
        metadata.get('provider_total_tokens'),
    )


def _runtime_main_model_name() -> str:
    view = runtime_settings.get_main_model_settings()
    return str(view.payload['model']['value'])


def build_payload(messages: list, temperature: float, top_p: float,
                  max_tokens: int, stream: bool = False) -> dict:
    """Construit le payload pour l'API OpenRouter."""
    payload = {
        "model": _runtime_main_model_name(),
        "messages": messages,
        "temperature": temperature,
        "top_p": top_p,
        "max_tokens": max_tokens,
        "stop": ["<|endoftext|>", "<|return|>", "<|call|>"],
    }
    if stream:
        payload["stream"] = True
        payload["stream_options"] = {"include_usage": True}
    return payload
