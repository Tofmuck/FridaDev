#!/usr/bin/env python3
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
        "resumer": "title_resumer",
        "stimmung_agent": "title_stimmung_agent",
        "validation_agent": "title_validation_agent",
    }
    title_default_map = {
        "llm": config.OR_TITLE_LLM,
        "arbiter": config.OR_TITLE_ARBITER,
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
        h["X-Title"] = title
    return h


def or_chat_completions_url() -> str:
    return f"{_runtime_main_base_url()}/chat/completions"


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
