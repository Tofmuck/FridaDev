#!/usr/bin/env python3
import config


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
        "Authorization": f"Bearer {config.OR_KEY}",
    }
    if config.OR_REFERER:
        h["HTTP-Referer"] = config.OR_REFERER
    if title:
        h["X-Title"] = title
    return h


def build_payload(messages: list, temperature: float, top_p: float,
                  max_tokens: int, stream: bool = False) -> dict:
    """Construit le payload pour l'API OpenRouter."""
    payload = {
        "model": config.OR_MODEL,
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
