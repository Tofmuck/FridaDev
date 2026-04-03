from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

import requests

import config
from admin import runtime_settings
from core import llm_client, prompt_loader
from core.token_utils import count_tokens

logger = logging.getLogger("frida.summarizer")


def _runtime_summary_model_name() -> str:
    view = runtime_settings.get_summary_model_settings()
    return str(view.payload['model']['value'])


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _raw_dialogue(conversation: dict[str, Any]) -> list[dict[str, Any]]:
    """Retourne uniquement les messages bruts non encore résumés (jamais un résumé)."""
    return [
        m for m in conversation.get("messages", [])
        if m.get("role") in {"user", "assistant"} and not m.get("summarized_by")
    ]


def summarize_conversation(turns: list[dict[str, Any]], model: str) -> str:
    """Appelle un LLM cheap via OpenRouter pour résumer une liste de tours de dialogue."""
    parts = []
    for turn in turns:
        role = "Utilisateur" if turn.get("role") == "user" else "Assistant"
        ts = (turn.get("timestamp") or "")[:10]
        prefix = f"[{ts}] " if ts else ""
        parts.append(f"{prefix}{role} : {turn.get('content', '')}")
    dialogue_text = "\n\n".join(parts)

    system = prompt_loader.get_summary_system_prompt()
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"Voici le dialogue à résumer :\n\n{dialogue_text}"},
    ]
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.3,
        "top_p": 1.0,
        "max_tokens": config.SUMMARY_TARGET_TOKENS,
    }
    r = requests.post(
        f"{config.OR_BASE}/chat/completions",
        json=payload,
        headers=llm_client.or_headers(caller='resumer'),
        timeout=90,
    )
    r.raise_for_status()
    response_payload = llm_client.read_openrouter_response_payload(r)
    llm_client.log_provider_metadata(
        logger,
        'summarizer_provider_response',
        llm_client.extract_openrouter_provider_metadata(response_payload, requested_model=model),
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

    total = count_tokens(
        [{"role": m["role"], "content": m["content"]} for m in unsummarized],
        model,
    )
    if total <= config.SUMMARY_THRESHOLD_TOKENS:
        return False

    keep_n = config.SUMMARY_KEEP_TURNS * 2  # user + assistant = 2 messages par tour
    to_summarize = unsummarized[:-keep_n] if len(unsummarized) > keep_n else []
    if not to_summarize:
        return False

    logger.info(
        "summarize_trigger conv_id=%s tokens=%s to_summarize=%s",
        conversation.get("id"), total, len(to_summarize),
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

    logger.info(
        "summarize_done conv_id=%s summary_id=%s start=%s end=%s covered=%s",
        conversation.get("id"), summary_id, start_ts[:10], end_ts[:10], len(to_summarize),
    )
    return True
