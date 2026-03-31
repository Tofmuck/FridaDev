#!/usr/bin/env python3
import logging
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

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


def _safe_runtime_services_value(field: str) -> Any:
    try:
        return _runtime_services_value(field)
    except Exception:
        return None


def _runtime_collection_settings() -> dict[str, int | None]:
    return {
        'searxng_results': _safe_runtime_services_value('searxng_results'),
        'crawl4ai_top_n': _safe_runtime_services_value('crawl4ai_top_n'),
        'crawl4ai_max_chars': _safe_runtime_services_value('crawl4ai_max_chars'),
    }


def _source_domain(url: str) -> str | None:
    host = urlparse(str(url or '')).netloc.strip().lower()
    return host or None


def _truncate_search_snippet(content: str, max_chars: int = 400) -> tuple[str, bool]:
    snippet = str(content or '')
    if len(snippet) <= max_chars:
        return snippet, False
    return snippet[:max_chars], True


def _truncate_crawl_markdown(content: str, max_chars: int) -> tuple[str, bool]:
    markdown = str(content or '')
    if len(markdown) <= max_chars:
        return markdown, False
    return markdown[:max_chars] + "\n[...contenu tronqué]", True


def _build_source_payload(
    rank: int,
    result: dict[str, str],
    *,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
) -> dict[str, Any]:
    title = str(result.get('title') or '')
    url = str(result.get('url') or '')
    search_snippet = str(result.get('content') or '')
    used_in_prompt = False
    used_content_kind = 'none'
    content_used = ''
    truncated = False

    if rank <= crawl4ai_top_n:
        crawled_markdown = crawl(url)
        if crawled_markdown:
            content_used, truncated = _truncate_crawl_markdown(crawled_markdown, crawl4ai_max_chars)
            used_in_prompt = True
            used_content_kind = 'crawl_markdown'
        elif search_snippet:
            content_used, truncated = _truncate_search_snippet(search_snippet)
            used_in_prompt = True
            used_content_kind = 'search_snippet'
    elif search_snippet:
        content_used, truncated = _truncate_search_snippet(search_snippet)
        used_in_prompt = True
        used_content_kind = 'search_snippet'

    return {
        'rank': rank,
        'title': title,
        'url': url,
        'source_domain': _source_domain(url),
        'search_snippet': search_snippet,
        'used_in_prompt': used_in_prompt,
        'used_content_kind': used_content_kind,
        'content_used': content_used,
        'truncated': truncated,
    }


def _build_context_material(query: str, results: list[dict[str, str]]) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    if not results:
        return {
            'runtime': runtime,
            'results_count': 0,
            'sources': [],
            'context_block': '',
        }

    crawl4ai_top_n = int(runtime.get('crawl4ai_top_n') or 0)
    crawl4ai_max_chars = int(runtime.get('crawl4ai_max_chars') or 0)
    today = datetime.now(timezone.utc).strftime("%d %B %Y")
    sources = [
        _build_source_payload(
            index,
            result,
            crawl4ai_top_n=crawl4ai_top_n,
            crawl4ai_max_chars=crawl4ai_max_chars,
        )
        for index, result in enumerate(results, 1)
    ]
    lines = [
        f"[RECHERCHE WEB — {today}]",
        f"J'ai effectué une recherche pour : « {query} ».",
        "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
        "",
    ]
    for source in sources:
        lines.append(f"--- Source {source['rank']} : {source['title']}")
        lines.append(f"URL : {source['url']}")
        if source['content_used']:
            lines.append(source['content_used'])
        lines.append("")
    lines.append("[FIN DES RÉSULTATS WEB]")
    return {
        'runtime': runtime,
        'results_count': len(sources),
        'sources': sources,
        'context_block': "\n".join(lines),
    }


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
    return str(_build_context_material(query, results)['context_block'])


def _emit_web_search_runtime_event(
    *,
    enabled: bool,
    status: str,
    reason_code: str | None,
    query_preview: str,
    results_count: int,
    context_block: str,
    sources: list[dict[str, Any]] | None = None,
    error_class: str | None = None,
) -> None:
    payload = {
        'enabled': bool(enabled),
        'query_preview': str(query_preview)[:120],
        'results_count': int(results_count),
        'context_injected': bool(context_block),
        'truncated': any(bool(source.get('truncated')) for source in (sources or [])),
    }
    if error_class:
        payload['error_class'] = error_class
    chat_turn_logger.emit(
        'web_search',
        status=status,
        reason_code=reason_code,
        prompt_kind='chat_web_reformulation',
        payload=payload,
    )
    if status == 'skipped' and reason_code:
        chat_turn_logger.emit_branch_skipped(
            reason_code=reason_code,
            reason_short='web_search_no_results',
        )
    if status == 'error' and error_class:
        chat_turn_logger.emit_error(
            error_code=reason_code or 'upstream_error',
            error_class=error_class,
            message_short=query_preview,
        )


def build_context_payload(user_msg: str) -> dict[str, Any]:
    try:
        query = reformulate(user_msg)
        results = search(query)
        material = _build_context_material(query, results)
        has_results = int(material['results_count']) > 0
        payload = {
            'enabled': True,
            'status': 'ok' if has_results else 'skipped',
            'reason_code': None if has_results else 'no_data',
            'original_user_message': str(user_msg or ''),
            'query': str(query),
            'results_count': int(material['results_count']),
            'runtime': dict(material['runtime']),
            'sources': list(material['sources']),
            'context_block': str(material['context_block'] or ''),
        }
        _emit_web_search_runtime_event(
            enabled=True,
            status=payload['status'],
            reason_code=payload['reason_code'],
            query_preview=payload['query'],
            results_count=payload['results_count'],
            context_block=payload['context_block'],
            sources=payload['sources'],
        )
        return payload
    except Exception as exc:
        error_payload = {
            'enabled': True,
            'status': 'error',
            'reason_code': 'upstream_error',
            'original_user_message': str(user_msg or ''),
            'query': str(user_msg or ''),
            'results_count': 0,
            'runtime': _runtime_collection_settings(),
            'sources': [],
            'context_block': '',
        }
        _emit_web_search_runtime_event(
            enabled=True,
            status='error',
            reason_code='upstream_error',
            query_preview=error_payload['query'],
            results_count=0,
            context_block='',
            sources=[],
            error_class=exc.__class__.__name__,
        )
        return error_payload


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
        _emit_web_search_runtime_event(
            enabled=True,
            status='ok' if has_results else 'skipped',
            reason_code=None if has_results else 'no_data',
            query_preview=str(query),
            results_count=len(results),
            context_block=ctx,
            sources=[],
        )
        return ctx, query, len(results)
    except Exception as exc:
        _emit_web_search_runtime_event(
            enabled=True,
            status='error',
            reason_code='upstream_error',
            query_preview=str(user_msg or ''),
            results_count=0,
            context_block='',
            sources=[],
            error_class=exc.__class__.__name__,
        )
        return '', str(user_msg or ''), 0
