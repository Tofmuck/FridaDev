#!/usr/bin/env python3
import logging
import requests
from datetime import datetime, timezone

import config

logger = logging.getLogger("kiki.web_search")


def reformulate(user_msg: str) -> str:
    """Reformule le message utilisateur en requête de recherche web concise."""
    try:
        today = datetime.now(timezone.utc).strftime("%d %B %Y")
        payload = {
            "model": config.OR_MODEL,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Nous sommes le {today}. "
                        "Tu es un assistant qui transforme un message en requête de recherche web courte et efficace. "
                        "Réponds UNIQUEMENT avec la requête de recherche, sans explication, sans guillemets, sans ponctuation finale. "
                        "La requête doit être en français sauf si le sujet est clairement anglophone. "
                        "Utilise l'année en cours si la recherche porte sur des événements récents ou à venir. "
                        "Maximum 8 mots."
                    ),
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


def search(query: str, max_results: int = None) -> list[dict]:
    """Interroge SearXNG et retourne les résultats."""
    if max_results is None:
        max_results = config.SEARXNG_RESULTS
    try:
        params = {"q": query, "format": "json", "language": "fr-FR", "safesearch": "0"}
        resp = requests.get(f"{config.SEARXNG_URL}/search", params=params, timeout=10)
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
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.CRAWL4AI_TOKEN}",
        }
        resp = requests.post(f"{config.CRAWL4AI_URL}/md",
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


def _format_context(query: str, results: list[dict]) -> str:
    """Formate les résultats SearXNG + contenu crawlé pour le LLM."""
    if not results:
        return (
            f"[RECHERCHE WEB — aucun résultat pour : « {query} »]\n"
            "Je n'ai rien trouvé pour cette recherche.\n"
        )
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
        if crawled < config.CRAWL4AI_TOP_N:
            content = crawl(r["url"])
            if content:
                truncated = content[:config.CRAWL4AI_MAX_CHARS]
                if len(content) > config.CRAWL4AI_MAX_CHARS:
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


def build_context(user_msg: str) -> tuple[str, str, int, bool]:
    """
    Pipeline complet : reformulation → SearXNG/Crawl4AI.
    Retourne (contexte, query_reformulee, nb_resultats_web, False).
    """
    query = reformulate(user_msg)
    results = search(query)
    ctx_parts = []
    if results:
        ctx_parts.append(_format_context(query, results))
    ctx = "\n\n".join(ctx_parts)
    return ctx, query, len(results), False
