from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Mapping

import requests

import config
from admin import runtime_settings
from core.hermeneutic_node.inputs import time_input
from core import llm_client, prompt_loader
from core.token_utils import estimate_tokens

logger = logging.getLogger("frida.summarizer")


def _runtime_summary_model_name() -> str:
    return str(_runtime_summary_settings()['model'])


def _runtime_summary_settings() -> dict[str, Any]:
    view = runtime_settings.get_summary_model_settings()
    payload = view.payload

    def value(field: str, default: Any) -> Any:
        field_payload = payload.get(field)
        if not isinstance(field_payload, Mapping):
            return default
        resolved = field_payload.get('value')
        if resolved in (None, ''):
            return default
        return resolved

    return {
        'model': str(value('model', config.SUMMARY_MODEL)).strip() or config.SUMMARY_MODEL,
        'temperature': float(value('temperature', config.SUMMARY_TEMPERATURE)),
        'top_p': float(value('top_p', config.SUMMARY_TOP_P)),
        'max_tokens': int(value('max_tokens', config.SUMMARY_TARGET_TOKENS)),
        'timeout_s': int(value('timeout_s', config.SUMMARY_TIMEOUT_S)),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _raw_dialogue(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Retourne uniquement les messages bruts non encore résumés (jamais un résumé)."""
    return [
        m for m in conversation.get("messages", [])
        if m.get("role") in {"user", "assistant"} and not m.get("summarized_by")
    ]


def summarize_conversation(turns: list[dict[str, Any]], model: str | None = None) -> str:
    """Appelle un LLM cheap via OpenRouter pour résumer une liste de tours de dialogue."""
    summary_settings = _runtime_summary_settings()
    summary_model = str(summary_settings['model'])
    parts = []
    for turn in turns:
        role = "Utilisateur" if turn.get("role") == "user" else "Assistant"
        ts = time_input.local_date_iso(
            str(turn.get("timestamp") or ""),
            timezone_name=config.FRIDA_TIMEZONE,
        )
        prefix = f"[{ts}] " if ts else ""
        parts.append(f"{prefix}{role} : {turn.get('content', '')}")
    dialogue_text = "\n\n".join(parts)

    system = prompt_loader.get_summary_system_prompt()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Voici le dialogue à résumer :\n\n{dialogue_text}"},
    ]
    payload = {
        "model": summary_model,
        "messages": messages,
        "temperature": float(summary_settings['temperature']),
        "top_p": float(summary_settings['top_p']),
        "max_tokens": int(summary_settings['max_tokens']),
    }
    r = requests.post(
        llm_client.or_chat_completions_url(),
        json=payload,
        headers=llm_client.or_headers(caller='resumer'),
        timeout=int(summary_settings['timeout_s']),
    )
    r.raise_for_status()
    response_payload = llm_client.read_openrouter_response_payload(r)
    llm_client.log_provider_metadata(
        logger,
        'summarizer_provider_response',
        llm_client.extract_openrouter_provider_metadata(response_payload, requested_model=summary_model),
    )
    return llm_client.extract_openrouter_text(response_payload)


def maybe_summarize(conversation: dict[str, Any], model: str) -> bool:
    """
    Si les messages bruts dépassent SUMMARY_THRESHOLD_TOKENS, résume les tours anciens,
    les marque avec summarized_by, et stocke le résumé en base.
    Retourne True si un résumé a été généré.
    """
    unsummarized = _raw_dialogue(conversation)
    if not unsummarized:
        return False

    estimated_total_tokens = estimate_tokens(
        [{"role": m["role"], "content": m["content"]} for m in unsummarized],
        model,
    )
    if estimated_total_tokens <= config.SUMMARY_THRESHOLD_TOKENS:
        return False

    keep_n = config.SUMMARY_KEEP_TURNS * 2  # user + assistant = 2 messages par tour
    to_summarize = unsummarized[:-keep_n] if len(unsummarized) > keep_n else []
    if not to_summarize:
        return False

    logger.info(
        "summarize_trigger conv_id=%s tokens=%s to_summarize=%s",
        conversation.get("id"), estimated_total_tokens, len(to_summarize),
    )

    try:
        summary_text = summarize_conversation(to_summarize, _runtime_summary_model_name())
    except Exception as exc:
        logger.error("summarize_failed conv_id=%s err=%s", conversation.get("id"), exc)
        return False

    start_ts = (to_summarize[0].get("timestamp") or "")
    end_ts   = (to_summarize[-1].get("timestamp") or "")
    summary_id = str(uuid.uuid4())

    summary_entry = {
        "id":         summary_id,
        "start_ts":   start_ts,
        "end_ts":     end_ts,
        "content":    summary_text,
        "turn_count": len(to_summarize),
    }

    # Persister le résumé en DB + rétro-renseigner summary_id sur les traces couvertes
    try:
        from memory import memory_store
        conv_id = conversation.get("id", "")
        memory_store.save_summary(conv_id, summary_entry)
        memory_store.update_traces_summary_id(conv_id, summary_id, start_ts, end_ts)
    except Exception as exc:
        logger.error("summary_db_save_failed conv_id=%s err=%s", conversation.get("id"), exc)

    # Marquer les messages couverts (par identité objet — même session, pas de GC)
    to_summarize_ids = {id(m) for m in to_summarize}
    for m in conversation.get("messages", []):
        if id(m) in to_summarize_ids:
            m["summarized_by"] = summary_id

    start_local_date = time_input.local_date_iso(start_ts, timezone_name=config.FRIDA_TIMEZONE)
    end_local_date = time_input.local_date_iso(end_ts, timezone_name=config.FRIDA_TIMEZONE)
    logger.info(
        "summarize_done conv_id=%s summary_id=%s start=%s end=%s covered=%s",
        conversation.get("id"), summary_id, start_local_date, end_local_date, len(to_summarize),
    )
    return True
