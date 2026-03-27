#!/usr/bin/env python3
import logging
from datetime import datetime, timezone
from typing import Any

import requests

import config
from admin import runtime_settings
from core import prompt_loader
from observability import chat_turn_logger

logger = logging.getLogger("frida.web_search")


def _runtime_main_model_name() -> str:
    view = runtime_settings.get_main_model_settings()
    return str(view.payload['model']['value'])


def _runtime_services_view() -> runtime_settings.RuntimeSectionView:
    return runtime_settings.get_services_settings()


def _runtime_services_value(field: str) -> Any:
    view = _runtime_services_view()
    payload = view.payload.get(field) or {}
    if 'value' in payload:
        return payload['value']

    env_bundle = runtime_settings.build_env_seed_bundle('services')
    fallback = env_bundle.payload.get(field) or {}
    if 'value' in fallback:
        return fallback['value']

    raise KeyError(f'missing services runtime value: {field}')


def _runtime_crawl4ai_token() -> str:
    secret = runtime_settings.get_runtime_secret_value('services', 'crawl4ai_token')
    return str(secret.value)


def reformulate(user_msg: str) -> str:
    """Reformule le message utilisateur en requête de recherche web concise."""
    try:
        today = datetime.now(timezone.utc).strftime("%d %B %Y")
        system_prompt = prompt_loader.get_web_reformulation_prompt().format(today=today)
        payload = {
            "model": _runtime_main_model_name(),
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": 40,
            "temperature": 0.2,
        }
        from core.llm_client import or_headers
        r = requests.post(f"{config.OR_BASE}/chat/completions", json=payload,
                          headers=or_headers(caller='llm'), timeout=10)
        r.raise_for_status()
        query = r.json()["choices"][0]["message"]["content"].strip().strip('"').strip("'")
        logger.info("reformulate original=%s query=%s", user_msg[:60], query)
        return query or user_msg
    except Exception as e:
        logger.warning("reformulate_error err=%s", e)
        return user_msg


def search(query: str, max_results: int | None = None) -> list[dict[str, str]]:
    """Interroge SearXNG et retourne les résultats."""
    if max_results is None:
        max_results = int(_runtime_services_value('searxng_results'))
    try:
        params = {"q": query, "format": "json", "language": "fr-FR", "safesearch": "0"}
        searxng_url = str(_runtime_services_value('searxng_url')).rstrip('/')
        resp = requests.get(f"{searxng_url}/search", params=params, timeout=10)
        resp.raise_for_status()
        results = resp.json().get("results", [])[:max_results]
        return [{"title": r.get("title", ""), "url": r.get("url", ""), "content": r.get("content", "")}
                for r in results]
    except Exception as e:
        logger.warning("search_error query=%s err=%s", query, e)
        return []


def crawl(url: str) -> str:
    """Récupère le contenu markdown d'une URL via Crawl4AI."""
    try:
        crawl4ai_url = str(_runtime_services_value('crawl4ai_url')).rstrip('/')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_runtime_crawl4ai_token()}",
        }
        resp = requests.post(f"{crawl4ai_url}/md",
                             json={"url": url, "only_text": True, "cache": "0"},
                             headers=headers, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        if not data.get("success"):
            return ""
        return (data.get("markdown") or "").strip()
    except Exception as e:
        logger.warning("crawl_error url=%s err=%s", url, e)
        return ""


def _format_context(query: str, results: list[dict[str, str]]) -> str:
    """Formate les résultats SearXNG + contenu crawlé pour le LLM."""
    if not results:
        return (
            f"[RECHERCHE WEB — aucun résultat pour : « {query} »]\n"
            "Je n'ai rien trouvé pour cette recherche.\n"
        )
    crawl4ai_top_n = int(_runtime_services_value('crawl4ai_top_n'))
    crawl4ai_max_chars = int(_runtime_services_value('crawl4ai_max_chars'))
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    lines = [
        f"[RECHERCHE WEB — {today}]",
        f"J'ai effectué une recherche pour : « {query} ».",
        "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
        "",
    ]
    crawled = 0
    for i, r in enumerate(results, 1):
        lines.append(f"--- Source {i} : {r['title']}")
        lines.append(f"URL : {r['url']}")
        if crawled < crawl4ai_top_n:
            content = crawl(r["url"])
            if content:
                truncated = content[:crawl4ai_max_chars]
                if len(content) > crawl4ai_max_chars:
                    truncated += "\n[...contenu tronqué]"
                lines.append(truncated)
                crawled += 1
            elif r["content"]:
                lines.append(r["content"][:400])
        elif r["content"]:
            lines.append(r["content"][:400])
        lines.append("")
    lines.append("[FIN DES RÉSULTATS WEB]")
    return "\n".join(lines)


def build_context(user_msg: str) -> tuple[str, str, int]:
    """
    Pipeline complet : reformulation → SearXNG/Crawl4AI.
    Retourne (contexte, query_reformulee, nb_resultats_web).
    """
    try:
        query = reformulate(user_msg)
        results = search(query)
        ctx_parts = []
        if results:
            ctx_parts.append(_format_context(query, results))
        ctx = "\n\n".join(ctx_parts)
        has_results = len(results) > 0
        chat_turn_logger.emit(
            'web_search',
            status='ok' if has_results else 'skipped',
            reason_code=None if has_results else 'no_data',
            prompt_kind='chat_web_reformulation',
            payload={
                'enabled': True,
                'query_preview': str(query)[:120],
                'results_count': len(results),
                'context_injected': bool(ctx),
                'truncated': '[...contenu tronqué]' in ctx,
            },
        )
        if not has_results:
            chat_turn_logger.emit_branch_skipped(
                reason_code='no_data',
                reason_short='web_search_no_results',
            )
        return ctx, query, len(results)
    except Exception as exc:
        chat_turn_logger.emit(
            'web_search',
            status='error',
            error_code='upstream_error',
            prompt_kind='chat_web_reformulation',
            payload={
                'enabled': True,
                'query_preview': str(user_msg)[:120],
                'results_count': 0,
                'context_injected': False,
                'truncated': False,
                'error_class': exc.__class__.__name__,
            },
        )
        chat_turn_logger.emit_error(
            error_code='upstream_error',
            error_class=exc.__class__.__name__,
            message_short=str(exc),
        )
        return '', str(user_msg or ''), 0
