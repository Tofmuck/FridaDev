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


def or_headers(caller: str = "llm") -> dict:
    """Construit les headers HTTP pour OpenRouter, selon le composant appelant."""
    caller_key = str(caller or "llm").strip().lower()
    title_map = {
        "llm": config.OR_TITLE_LLM,
        "arbiter": config.OR_TITLE_ARBITER,
        "resumer": config.OR_TITLE_RESUMER,
    }
    title = title_map.get(caller_key, config.OR_TITLE_LLM)

    h = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_runtime_main_api_key()}",
    }
    if config.OR_REFERER:
        h["HTTP-Referer"] = config.OR_REFERER
    if title:
        h["X-Title"] = title
    return h


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
