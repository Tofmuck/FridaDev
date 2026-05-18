#!/usr/bin/env python3
import logging
import re
import inspect
import hashlib
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import requests

import config
from admin import runtime_settings
from core import prompt_loader
from core.hermeneutic_node.inputs import time_input
from core.web_read_state import (
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
    READ_STATE_PAGE_PARTIALLY_READ,
    READ_STATE_PAGE_READ,
)
from observability import chat_turn_logger
from tools import web_reformulation_settings

logger = logging.getLogger("frida.web_search")
_EXPLICIT_URL_RE = re.compile(r'https?://[^\s<>"\']+')
_URL_TRAILING_PUNCTUATION = '.,;:!?)]}\'"'
CRAWL4AI_FILTER_FIT = 'fit'
CRAWL4AI_FILTER_RAW = 'raw'


def _sha256_12(value: Any) -> str:
    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _safe_len(value: Any) -> int:
    return len(str(value or ''))


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
        'crawl4ai_explicit_url_max_chars': _safe_runtime_services_value('crawl4ai_explicit_url_max_chars'),
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def _web_temporal_label(*, now_iso: str | None = None) -> str:
    source_now = str(now_iso or '').strip() or _now_iso()
    return (
        time_input.local_date_label_fr(
            source_now,
            timezone_name=str(config.FRIDA_TIMEZONE),
            include_timezone=True,
        )
        or source_now
    )


def _source_domain(url: str) -> str | None:
    host = urlparse(str(url or '')).netloc.strip().lower()
    return host or None


def _normalized_source_url(url: str) -> str:
    text = str(url or '').strip()
    if not text:
        return ''
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return text.rstrip('/')
    path = parsed.path or ''
    if path != '/':
        path = path.rstrip('/')
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        fragment='',
    )
    return normalized.geturl()


def _urls_match(left: str, right: str) -> bool:
    normalized_left = _normalized_source_url(left)
    normalized_right = _normalized_source_url(right)
    return bool(normalized_left and normalized_right and normalized_left == normalized_right)


def _extract_explicit_url(user_msg: str) -> str | None:
    text = str(user_msg or '')
    if not text:
        return None

    for match in _EXPLICIT_URL_RE.finditer(text):
        candidate = match.group(0).rstrip(_URL_TRAILING_PUNCTUATION)
        parsed = urlparse(candidate)
        if parsed.scheme in {'http', 'https'} and parsed.netloc:
            return candidate
    return None


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


def _explicit_url_max_chars(runtime: dict[str, int | None]) -> int:
    explicit_budget = int(runtime.get('crawl4ai_explicit_url_max_chars') or 0)
    if explicit_budget > 0:
        return explicit_budget
    return int(runtime.get('crawl4ai_max_chars') or 0)


def _build_crawl4ai_md_payload(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = '0',
) -> dict[str, str]:
    payload = {
        'url': str(url or ''),
        'f': str(filter_type or CRAWL4AI_FILTER_FIT),
        'c': str(cache_mode or '0'),
    }
    if query:
        payload['q'] = str(query)
    return payload


def _crawl_markdown_with_status(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
) -> dict[str, Any]:
    """Récupère le markdown via /md avec le contrat OpenAPI Crawl4AI."""
    try:
        crawl4ai_url = str(_runtime_services_value('crawl4ai_url')).rstrip('/')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_runtime_crawl4ai_token()}",
        }
        payload = _build_crawl4ai_md_payload(
            url,
            filter_type=filter_type,
            query=query,
            cache_mode='0',
        )
        resp = requests.post(
            f"{crawl4ai_url}/md",
            json=payload,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()
        data = resp.json()
        actual_filter = str(data.get('filter') or filter_type or CRAWL4AI_FILTER_FIT)
        if not data.get("success"):
            return {
                'status': 'error',
                'markdown': '',
                'error_class': 'crawl_unsuccessful',
                'filter': actual_filter,
            }
        markdown = (data.get("markdown") or "").strip()
        if not markdown:
            return {
                'status': 'empty',
                'markdown': '',
                'error_class': None,
                'filter': actual_filter,
            }
        return {
            'status': 'success',
            'markdown': markdown,
            'error_class': None,
            'filter': actual_filter,
        }
    except Exception as e:
        logger.warning("crawl_error url=%s filter=%s err=%s", url, filter_type, e)
        return {
            'status': 'error',
            'markdown': '',
            'error_class': e.__class__.__name__,
            'filter': str(filter_type or CRAWL4AI_FILTER_FIT),
        }


def _crawl_explicit_url_primary_with_status(url: str) -> dict[str, Any]:
    """Lecture primaire d'une URL explicite: fit d'abord, raw seulement si fit est vide."""
    fit_result = _crawl_markdown_with_status(url, filter_type=CRAWL4AI_FILTER_FIT)
    fit_result['raw_fallback_used'] = False
    if str(fit_result.get('status') or '') != 'empty':
        return fit_result

    raw_result = _crawl_markdown_with_status(url, filter_type=CRAWL4AI_FILTER_RAW)
    raw_result['raw_fallback_used'] = True
    return raw_result


def _build_source_payload(
    rank: int,
    result: dict[str, str],
    *,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    source_origin: str = 'search_result',
    is_primary_source: bool = False,
) -> dict[str, Any]:
    title = str(result.get('title') or '')
    url = str(result.get('url') or '')
    search_snippet = str(result.get('content') or '')
    used_in_prompt = False
    used_content_kind = 'none'
    content_used = ''
    truncated = False
    crawl_status = 'not_attempted'

    if rank <= crawl4ai_top_n:
        crawl_result = (
            dict(preloaded_crawl_results[url])
            if preloaded_crawl_results and url in preloaded_crawl_results
            else crawl_with_status(url)
        )
        crawled_markdown = str(crawl_result.get('markdown') or '')
        crawl_status = str(crawl_result.get('status') or 'error')
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
        'source_origin': str(source_origin or 'search_result'),
        'is_primary_source': bool(is_primary_source),
        'crawl_status': crawl_status,
    }


def _source_content_chars(source: dict[str, Any]) -> int:
    return len(str(source.get('content_used') or ''))


def _build_source_material_summary(sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for source in sources or []:
        try:
            rank = int(source.get('rank') or 0)
        except (TypeError, ValueError):
            rank = 0
        summary.append(
            {
                'rank': rank,
                'url': str(source.get('url') or ''),
                'source_origin': str(source.get('source_origin') or 'search_result'),
                'is_primary_source': bool(source.get('is_primary_source', False)),
                'used_in_prompt': bool(source.get('used_in_prompt', False)),
                'used_content_kind': str(source.get('used_content_kind') or 'none'),
                'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                'content_chars': _source_content_chars(source),
                'truncated': bool(source.get('truncated', False)),
            }
        )
    return summary


def _derive_used_content_kinds(source_material_summary: list[dict[str, Any]] | None) -> list[str]:
    kinds: list[str] = []
    for source in source_material_summary or []:
        if not bool(source.get('used_in_prompt', False)):
            continue
        kind = str(source.get('used_content_kind') or 'none')
        if kind == 'none' or kind in kinds:
            continue
        kinds.append(kind)
    return kinds


def _derive_injected_chars(source_material_summary: list[dict[str, Any]] | None) -> int:
    total = 0
    for source in source_material_summary or []:
        if not bool(source.get('used_in_prompt', False)):
            continue
        try:
            total += int(source.get('content_chars') or 0)
        except (TypeError, ValueError):
            continue
    return total


def _augment_payload_observability(payload: dict[str, Any]) -> dict[str, Any]:
    source_material_summary = _build_source_material_summary(list(payload.get('sources') or []))
    payload['source_material_summary'] = source_material_summary
    payload['used_content_kinds'] = _derive_used_content_kinds(source_material_summary)
    payload['injected_chars'] = _derive_injected_chars(source_material_summary)
    payload['context_chars'] = len(str(payload.get('context_block') or ''))
    return payload


def _build_context_material(
    query: str,
    results: list[dict[str, str]],
    *,
    now_iso: str | None = None,
) -> dict[str, Any]:
    return _build_search_context_material(query, results, now_iso=now_iso)


def _build_explicit_url_fallback_source(
    explicit_url: str,
    *,
    matching_result: dict[str, str] | None,
    primary_read_status: str,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    base_result = dict(matching_result or {})
    base_result['title'] = str(base_result.get('title') or 'URL explicite utilisateur')
    base_result['url'] = str(explicit_url or '')
    source = _build_source_payload(
        1,
        base_result,
        crawl4ai_top_n=crawl4ai_top_n,
        crawl4ai_max_chars=crawl4ai_max_chars,
        preloaded_crawl_results=preloaded_crawl_results,
        source_origin='explicit_url',
        is_primary_source=True,
    )
    source['title'] = str(base_result.get('title') or 'URL explicite utilisateur')
    source['url'] = str(explicit_url or '')
    source['source_domain'] = _source_domain(explicit_url)
    source['source_origin'] = 'explicit_url'
    source['is_primary_source'] = True
    source['crawl_status'] = str(primary_read_status or source.get('crawl_status') or 'not_attempted')
    return source


def _build_explicit_url_context_material(
    url: str,
    crawled_markdown: str,
    *,
    now_iso: str | None = None,
) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    crawl4ai_max_chars = _explicit_url_max_chars(runtime)
    today = _web_temporal_label(now_iso=now_iso)
    content_used, truncated = _truncate_crawl_markdown(crawled_markdown, crawl4ai_max_chars)
    source = {
        'rank': 1,
        'title': 'URL explicite utilisateur',
        'url': str(url or ''),
        'source_domain': _source_domain(url),
        'search_snippet': '',
        'used_in_prompt': True,
        'used_content_kind': 'crawl_markdown',
        'content_used': content_used,
        'truncated': truncated,
        'source_origin': 'explicit_url',
        'is_primary_source': True,
        'crawl_status': 'success',
    }
    lines = [
        f"[RECHERCHE WEB — {today}]",
        f"URL explicite fournie par l'utilisateur : {url}",
        "Lecture directe prioritaire reussie sur cette URL.",
        "",
        f"--- Source {source['rank']} : {source['title']}",
        f"URL : {source['url']}",
    ]
    if source['content_used']:
        lines.append(source['content_used'])
    lines.extend(('', '[FIN DES RÉSULTATS WEB]'))
    return {
        'runtime': runtime,
        'results_count': 1,
        'sources': [source],
        'context_block': "\n".join(lines),
    }


def _derive_read_state(
    *,
    explicit_url: str | None,
    primary_read_status: str,
    sources: list[dict[str, Any]],
) -> str | None:
    if not explicit_url:
        return None

    normalized_primary_status = str(primary_read_status or 'not_attempted')
    primary_source = next((source for source in sources if bool(source.get('is_primary_source'))), None)
    if normalized_primary_status == 'success':
        if primary_source and bool(primary_source.get('truncated')):
            return READ_STATE_PAGE_PARTIALLY_READ
        return READ_STATE_PAGE_READ

    if any(
        bool(source.get('used_in_prompt'))
        and str(source.get('used_content_kind') or 'none') == 'search_snippet'
        for source in sources
    ):
        return READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK

    if normalized_primary_status == 'empty':
        return READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY

    return READ_STATE_PAGE_NOT_READ_ERROR


def _build_search_context_material(
    query: str,
    results: list[dict[str, str]],
    *,
    explicit_url: str | None = None,
    primary_read_status: str = 'not_attempted',
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    crawl4ai_top_n = int(runtime.get('crawl4ai_top_n') or 0)
    crawl4ai_max_chars = int(runtime.get('crawl4ai_max_chars') or 0)
    today = _web_temporal_label(now_iso=now_iso)
    primary_source: dict[str, Any] | None = None
    fallback_results = list(results or [])

    if explicit_url:
        matching_result: dict[str, str] | None = None
        deduped_results: list[dict[str, str]] = []
        for result in fallback_results:
            result_url = str(result.get('url') or '')
            if matching_result is None and _urls_match(result_url, explicit_url):
                matching_result = result
                continue
            deduped_results.append(result)
        primary_source = _build_explicit_url_fallback_source(
            explicit_url,
            matching_result=matching_result,
            primary_read_status=primary_read_status,
            crawl4ai_top_n=crawl4ai_top_n,
            crawl4ai_max_chars=crawl4ai_max_chars,
            preloaded_crawl_results=preloaded_crawl_results,
        )
        fallback_results = deduped_results

    primary_source_has_content = bool(
        primary_source
        and str(primary_source.get('used_content_kind') or 'none') != 'none'
    )

    if not fallback_results and not primary_source:
        return {
            'runtime': runtime,
            'results_count': 0,
            'sources': [],
            'context_block': '',
        }

    if explicit_url and not fallback_results and primary_source and not primary_source_has_content:
        return {
            'runtime': runtime,
            'results_count': 0,
            'sources': [primary_source],
            'context_block': '',
        }

    search_sources = [
        _build_source_payload(
            index,
            result,
            crawl4ai_top_n=crawl4ai_top_n,
            crawl4ai_max_chars=crawl4ai_max_chars,
            preloaded_crawl_results=preloaded_crawl_results,
        )
        for index, result in enumerate(fallback_results, 2 if primary_source else 1)
    ]
    sources = [primary_source] if primary_source else []
    sources.extend(search_sources)
    lines = [f"[RECHERCHE WEB — {today}]"]
    if explicit_url:
        lines.extend(
            [
                f"URL explicite fournie par l'utilisateur : {explicit_url}",
                f"Lecture directe tentee d'abord : {primary_read_status}.",
                f"Recherche de fallback pour : « {query} ».",
                "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"J'ai effectué une recherche pour : « {query} ».",
                "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
                "",
            ]
        )
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


def _call_reformulate(
    user_msg: str,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> str:
    reformulate_func = reformulate
    try:
        signature = inspect.signature(reformulate_func)
    except (TypeError, ValueError):
        signature = None

    if signature is not None:
        params = signature.parameters
        supports_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in params.values()
        )
        kwargs: dict[str, Any] = {}
        if supports_kwargs or 'requests_module' in params:
            kwargs['requests_module'] = requests_module
        if supports_kwargs or 'llm_module' in params:
            kwargs['llm_module'] = llm_module
        if supports_kwargs or 'now_iso' in params:
            kwargs['now_iso'] = now_iso
        if kwargs:
            return reformulate_func(user_msg, **kwargs)
    return reformulate_func(user_msg)


def _emit_web_reformulation_prompt_prepared(
    *,
    model: str,
    system_prompt: str,
    user_msg: str,
    max_tokens: int,
    temperature: float,
    timeout_s: int,
    llm_module: Any,
) -> None:
    resolve_title = getattr(llm_module, 'resolve_provider_title', None)
    provider_title = ''
    if callable(resolve_title):
        provider_title = str(resolve_title('web_reformulation') or '')
    payload = {
        'schema_version': 'v1',
        'payload_kind': 'secondary_web_reformulation_provider',
        'provider_caller': 'web_reformulation',
        'provider_title': provider_title,
        'secondary_provider_payload': True,
        'main_llm_payload': False,
        'system_prompt_present': bool(system_prompt),
        'current_user_present': bool(user_msg),
        'messages_count': 2,
        'message_role_counts': {
            'system': 1,
            'user': 1,
        },
        'system_prompt_chars': _safe_len(system_prompt),
        'current_user_chars': _safe_len(user_msg),
        'input_chars_total': _safe_len(system_prompt) + _safe_len(user_msg),
        'system_prompt_sha256_12': _sha256_12(system_prompt),
        'current_user_sha256_12': _sha256_12(user_msg),
        'sampling': {
            'temperature': float(temperature),
            'max_tokens': int(max_tokens),
            'timeout_s': int(timeout_s),
        },
        'reason_code': '',
    }
    chat_turn_logger.emit(
        'web_reformulation_prompt_prepared',
        status='ok',
        model=str(model or '') or None,
        prompt_kind='chat_web_reformulation',
        payload=payload,
    )


def reformulate(
    user_msg: str,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> str:
    """Reformule le message utilisateur en requête de recherche web concise."""
    try:
        if llm_module is None:
            from core import llm_client as llm_module

        today = _web_temporal_label(now_iso=now_iso)
        system_prompt = prompt_loader.get_web_reformulation_prompt().format(today=today)
        reformulation_settings = web_reformulation_settings.get_runtime_settings()
        model = reformulation_settings.model
        max_tokens = reformulation_settings.max_tokens
        temperature = reformulation_settings.temperature
        timeout_s = reformulation_settings.timeout_s
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": user_msg},
            ],
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        _emit_web_reformulation_prompt_prepared(
            model=model,
            system_prompt=system_prompt,
            user_msg=user_msg,
            max_tokens=max_tokens,
            temperature=temperature,
            timeout_s=timeout_s,
            llm_module=llm_module,
        )
        r = requests_module.post(
            llm_module.or_chat_completions_url(),
            json=payload,
            headers=llm_module.or_headers(caller='web_reformulation'),
            timeout=timeout_s,
        )
        r.raise_for_status()
        response_payload = llm_module.read_openrouter_response_payload(r)
        query = llm_module.extract_openrouter_text(response_payload).strip().strip('"').strip("'")
        logger.info(
            "reformulate original_chars=%s original_sha256_12=%s query_chars=%s query_sha256_12=%s",
            _safe_len(user_msg),
            _sha256_12(user_msg),
            _safe_len(query),
            _sha256_12(query),
        )
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
        logger.warning(
            "search_error query_chars=%s query_sha256_12=%s error_class=%s reason_code=searxng_request_failed",
            _safe_len(query),
            _sha256_12(query),
            type(e).__name__,
        )
        return []


def crawl_with_status(url: str) -> dict[str, Any]:
    """Récupère le contenu markdown d'une URL via Crawl4AI avec statut explicite."""
    return _crawl_markdown_with_status(url, filter_type=CRAWL4AI_FILTER_FIT)


def crawl(url: str) -> str:
    """Récupère le contenu markdown d'une URL via Crawl4AI."""
    return str(crawl_with_status(url).get('markdown') or '')


def _format_context(
    query: str,
    results: list[dict[str, str]],
    *,
    now_iso: str | None = None,
) -> str:
    """Formate les résultats SearXNG + contenu crawlé pour le LLM."""
    if not results:
        return (
            f"[RECHERCHE WEB — aucun résultat pour : « {query} »]\n"
            "Je n'ai rien trouvé pour cette recherche.\n"
        )
    return str(_build_context_material(query, results, now_iso=now_iso)['context_block'])


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
    truncated: bool | None = None,
    message_short: str | None = None,
    prompt_kind: str = 'chat_web_reformulation',
    explicit_url_detected: bool = False,
    explicit_url: str | None = None,
    read_state: str | None = None,
    primary_source_kind: str = 'search',
    primary_read_attempted: bool = False,
    primary_read_status: str | None = None,
    primary_read_filter: str | None = None,
    primary_read_raw_fallback_used: bool = False,
    fallback_used: bool = False,
    collection_path: str = 'search_only',
    used_content_kinds: list[str] | None = None,
    injected_chars: int | None = None,
    context_chars: int | None = None,
    source_material_summary: list[dict[str, Any]] | None = None,
) -> None:
    query_text = str(query_preview or '')
    if truncated is None:
        truncated = any(bool(source.get('truncated')) for source in (sources or []))
        if not truncated and context_block:
            truncated = '[...contenu tronqué]' in str(context_block)
    if source_material_summary is None:
        source_material_summary = _build_source_material_summary(list(sources or []))
    if used_content_kinds is None:
        used_content_kinds = _derive_used_content_kinds(source_material_summary)
    if injected_chars is None:
        injected_chars = _derive_injected_chars(source_material_summary)
    if context_chars is None:
        context_chars = len(str(context_block or ''))
    payload = {
        'enabled': bool(enabled),
        'query_preview': '',
        'query_present': bool(query_text.strip()),
        'query_chars': len(query_text),
        'query_sha256_12': _sha256_12(query_text),
        'results_count': int(results_count),
        'context_injected': bool(context_block),
        'truncated': bool(truncated),
        'explicit_url_detected': bool(explicit_url_detected),
        'explicit_url': str(explicit_url or ''),
        'read_state': read_state,
        'primary_source_kind': str(primary_source_kind or 'search'),
        'primary_read_attempted': bool(primary_read_attempted),
        'primary_read_status': str(primary_read_status or ''),
        'primary_read_filter': str(primary_read_filter or ''),
        'primary_read_raw_fallback_used': bool(primary_read_raw_fallback_used),
        'fallback_used': bool(fallback_used),
        'collection_path': str(collection_path or 'search_only'),
        'used_content_kinds': list(used_content_kinds or []),
        'injected_chars': int(injected_chars or 0),
        'context_chars': int(context_chars or 0),
        'source_material_summary': list(source_material_summary or []),
    }
    if error_class:
        payload['error_class'] = error_class
    chat_turn_logger.emit(
        'web_search',
        status=status,
        reason_code=reason_code,
        prompt_kind=prompt_kind,
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
            message_short=str(message_short or query_preview),
        )


def _build_payload_from_collection(
    *,
    user_msg: str,
    explicit_url: str | None,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if explicit_url:
        primary_crawl = _crawl_explicit_url_primary_with_status(explicit_url)
        primary_read_status = str(primary_crawl.get('status') or 'error')
        primary_read_filter = str(primary_crawl.get('filter') or CRAWL4AI_FILTER_FIT)
        primary_read_raw_fallback_used = bool(primary_crawl.get('raw_fallback_used', False))
        if primary_read_status == 'success':
            material = _build_explicit_url_context_material(
                explicit_url,
                str(primary_crawl.get('markdown') or ''),
                now_iso=now_iso,
            )
            read_state = _derive_read_state(
                explicit_url=explicit_url,
                primary_read_status=primary_read_status,
                sources=list(material['sources']),
            )
            return {
                'enabled': True,
                'status': 'ok',
                'reason_code': None,
                'original_user_message': str(user_msg or ''),
                'query': '',
                'results_count': int(material['results_count']),
                'runtime': dict(material['runtime']),
                'sources': list(material['sources']),
                'context_block': str(material['context_block'] or ''),
                'prompt_kind': 'chat_web_explicit_url',
                'explicit_url_detected': True,
                'explicit_url': str(explicit_url),
                'read_state': read_state,
                'primary_source_kind': 'explicit_url',
                'primary_read_attempted': True,
                'primary_read_status': primary_read_status,
                'primary_read_filter': primary_read_filter,
                'primary_read_raw_fallback_used': primary_read_raw_fallback_used,
                'fallback_used': False,
                'collection_path': 'explicit_url_direct',
            }

        query = _call_reformulate(
            user_msg,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso,
        )
        results = search(query)
        material = _build_search_context_material(
            query,
            results,
            explicit_url=explicit_url,
            primary_read_status=primary_read_status,
            preloaded_crawl_results={explicit_url: primary_crawl},
            now_iso=now_iso,
        )
        has_results = int(material['results_count']) > 0
        read_state = _derive_read_state(
            explicit_url=explicit_url,
            primary_read_status=primary_read_status,
            sources=list(material['sources']),
        )
        return {
            'enabled': True,
            'status': 'ok' if has_results else 'skipped',
            'reason_code': None if has_results else 'no_data',
            'original_user_message': str(user_msg or ''),
            'query': str(query),
            'results_count': int(material['results_count']),
            'runtime': dict(material['runtime']),
            'sources': list(material['sources']),
            'context_block': str(material['context_block'] or ''),
            'prompt_kind': 'chat_web_explicit_url_fallback',
            'explicit_url_detected': True,
            'explicit_url': str(explicit_url),
            'read_state': read_state,
            'primary_source_kind': 'explicit_url',
            'primary_read_attempted': True,
            'primary_read_status': primary_read_status,
            'primary_read_filter': primary_read_filter,
            'primary_read_raw_fallback_used': primary_read_raw_fallback_used,
            'fallback_used': True,
            'collection_path': 'explicit_url_fallback_search',
        }

    query = _call_reformulate(
        user_msg,
        requests_module=requests_module,
        llm_module=llm_module,
        now_iso=now_iso,
    )
    results = search(query)
    material = _build_search_context_material(query, results, now_iso=now_iso)
    has_results = int(material['results_count']) > 0
    return {
        'enabled': True,
        'status': 'ok' if has_results else 'skipped',
        'reason_code': None if has_results else 'no_data',
        'original_user_message': str(user_msg or ''),
        'query': str(query),
        'results_count': int(material['results_count']),
        'runtime': dict(material['runtime']),
        'sources': list(material['sources']),
        'context_block': str(material['context_block'] or ''),
        'prompt_kind': 'chat_web_reformulation',
        'explicit_url_detected': False,
        'explicit_url': '',
        'read_state': None,
        'primary_source_kind': 'search',
        'primary_read_attempted': False,
        'primary_read_status': 'not_attempted',
        'primary_read_filter': None,
        'primary_read_raw_fallback_used': False,
        'fallback_used': False,
        'collection_path': 'search_only',
    }


def build_context_payload(
    user_msg: str,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    explicit_url = _extract_explicit_url(user_msg)
    try:
        payload = _augment_payload_observability(_build_payload_from_collection(
            user_msg=user_msg,
            explicit_url=explicit_url,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso,
        ))
        _emit_web_search_runtime_event(
            enabled=True,
            status=payload['status'],
            reason_code=payload['reason_code'],
            query_preview=str(payload['query'] or payload['explicit_url'] or user_msg or ''),
            results_count=payload['results_count'],
            context_block=payload['context_block'],
            sources=payload['sources'],
            prompt_kind=str(payload['prompt_kind']),
            explicit_url_detected=bool(payload['explicit_url_detected']),
            explicit_url=str(payload['explicit_url'] or ''),
            read_state=payload.get('read_state'),
            primary_source_kind=str(payload['primary_source_kind']),
            primary_read_attempted=bool(payload['primary_read_attempted']),
            primary_read_status=str(payload['primary_read_status'] or ''),
            primary_read_filter=str(payload.get('primary_read_filter') or ''),
            primary_read_raw_fallback_used=bool(payload.get('primary_read_raw_fallback_used', False)),
            fallback_used=bool(payload['fallback_used']),
            collection_path=str(payload['collection_path']),
            used_content_kinds=list(payload.get('used_content_kinds') or []),
            injected_chars=int(payload.get('injected_chars') or 0),
            context_chars=int(payload.get('context_chars') or 0),
            source_material_summary=list(payload.get('source_material_summary') or []),
        )
        return payload
    except Exception as exc:
        error_payload = _augment_payload_observability({
            'enabled': True,
            'status': 'error',
            'reason_code': 'upstream_error',
            'original_user_message': str(user_msg or ''),
            'query': str(user_msg or ''),
            'results_count': 0,
            'runtime': _runtime_collection_settings(),
            'sources': [],
            'context_block': '',
            'prompt_kind': 'chat_web_explicit_url_fallback' if explicit_url else 'chat_web_reformulation',
            'explicit_url_detected': bool(explicit_url),
            'explicit_url': str(explicit_url or ''),
            'read_state': READ_STATE_PAGE_NOT_READ_ERROR if explicit_url else None,
            'primary_source_kind': 'explicit_url' if explicit_url else 'search',
            'primary_read_attempted': bool(explicit_url),
            'primary_read_status': 'error' if explicit_url else 'not_attempted',
            'primary_read_filter': CRAWL4AI_FILTER_FIT if explicit_url else None,
            'primary_read_raw_fallback_used': False,
            'fallback_used': bool(explicit_url),
            'collection_path': 'explicit_url_fallback_search' if explicit_url else 'search_only',
        })
        _emit_web_search_runtime_event(
            enabled=True,
            status='error',
            reason_code='upstream_error',
            query_preview=str(error_payload['query'] or error_payload['explicit_url'] or user_msg or ''),
            results_count=0,
            context_block='',
            sources=[],
            error_class=exc.__class__.__name__,
            message_short=str(exc),
            prompt_kind=str(error_payload['prompt_kind']),
            explicit_url_detected=bool(error_payload['explicit_url_detected']),
            explicit_url=str(error_payload['explicit_url'] or ''),
            read_state=error_payload.get('read_state'),
            primary_source_kind=str(error_payload['primary_source_kind']),
            primary_read_attempted=bool(error_payload['primary_read_attempted']),
            primary_read_status=str(error_payload['primary_read_status'] or ''),
            primary_read_filter=str(error_payload.get('primary_read_filter') or ''),
            primary_read_raw_fallback_used=bool(error_payload.get('primary_read_raw_fallback_used', False)),
            fallback_used=bool(error_payload['fallback_used']),
            collection_path=str(error_payload['collection_path']),
            used_content_kinds=list(error_payload.get('used_content_kinds') or []),
            injected_chars=int(error_payload.get('injected_chars') or 0),
            context_chars=int(error_payload.get('context_chars') or 0),
            source_material_summary=list(error_payload.get('source_material_summary') or []),
        )
        return error_payload


def build_context(
    user_msg: str,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> tuple[str, str, int]:
    """
    Pipeline complet : reformulation → SearXNG/Crawl4AI.
    Retourne (contexte, query_reformulee, nb_resultats_web).
    """
    explicit_url = _extract_explicit_url(user_msg)
    if explicit_url:
        payload = build_context_payload(
            user_msg,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso,
        )
        query = str(payload.get('query') or payload.get('explicit_url') or user_msg or '')
        return str(payload.get('context_block') or ''), query, int(payload.get('results_count') or 0)
    try:
        query = _call_reformulate(
            user_msg,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso,
        )
        results = search(query)
        ctx_parts = []
        if results:
            if now_iso:
                ctx_parts.append(_format_context(query, results, now_iso=now_iso))
            else:
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
            truncated='[...contenu tronqué]' in ctx,
            prompt_kind='chat_web_reformulation',
            explicit_url_detected=False,
            explicit_url='',
            read_state=None,
            primary_source_kind='search',
            primary_read_attempted=False,
            primary_read_status='not_attempted',
            fallback_used=False,
            collection_path='search_only',
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
            message_short=str(exc),
            prompt_kind='chat_web_reformulation',
            explicit_url_detected=False,
            explicit_url='',
            read_state=None,
            primary_source_kind='search',
            primary_read_attempted=False,
            primary_read_status='not_attempted',
            fallback_used=False,
            collection_path='search_only',
        )
        return '', str(user_msg or ''), 0
