#!/usr/bin/env python3
from typing import Any, Mapping

import config
from admin import runtime_settings


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


def _runtime_main_referer() -> str:
    view = _runtime_main_view()
    payload = view.payload.get('referer') or {}
    return str(payload.get('value') or config.OR_REFERER).strip()


def _runtime_main_title(caller: str) -> str:
    caller_key = str(caller or "llm").strip().lower()
    title_field_map = {
        "llm": "title_llm",
        "arbiter": "title_arbiter",
        "identity_extractor": "title_identity_extractor",
        "resumer": "title_resumer",
        "stimmung_agent": "title_stimmung_agent",
        "validation_agent": "title_validation_agent",
    }
    title_default_map = {
        "llm": config.OR_TITLE_LLM,
        "arbiter": config.OR_TITLE_ARBITER,
        "identity_extractor": config.OR_TITLE_IDENTITY_EXTRACTOR,
        "resumer": config.OR_TITLE_RESUMER,
        "stimmung_agent": config.OR_TITLE_STIMMUNG_AGENT,
        "validation_agent": config.OR_TITLE_VALIDATION_AGENT,
    }
    view = _runtime_main_view()
    field_name = title_field_map.get(caller_key, "title_llm")
    payload = view.payload.get(field_name) or {}
    title = str(payload.get('value') or '').strip()
    return title or title_default_map.get(caller_key, config.OR_TITLE_LLM)


def or_headers(caller: str = "llm") -> dict:
    """Construit les headers HTTP pour OpenRouter, selon le composant appelant."""
    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_runtime_main_api_key()}",
    }
    referer = _runtime_main_referer()
    if referer:
        h["HTTP-Referer"] = referer
    title = _runtime_main_title(caller)
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
    metadata = _mapping(provider_metadata)
    log_info = getattr(logger, 'info', None)
    if not metadata or not callable(log_info):
        return
    log_info(
        '%s provider_generation_id=%s provider_model=%s provider_prompt_tokens=%s provider_completion_tokens=%s provider_total_tokens=%s',
        str(event_name or 'provider_response'),
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
