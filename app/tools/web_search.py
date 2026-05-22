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
from tools import (
    web_reformulation_settings,
    web_search_confidence,
    web_search_profile,
    web_search_query_plan,
    web_search_source_first,
    web_search_crawl_policy,
    web_search_rerank,
    web_search_searxng_params,
)

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
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
) -> dict[str, Any]:
    """Récupère le markdown via /md avec le contrat OpenAPI Crawl4AI."""
    normalized_query = str(query or '').strip()
    normalized_filter = str(filter_type or CRAWL4AI_FILTER_FIT)
    normalized_cache_mode = str(cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE)
    try:
        crawl4ai_url = str(_runtime_services_value('crawl4ai_url')).rstrip('/')
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_runtime_crawl4ai_token()}",
        }
        payload = _build_crawl4ai_md_payload(
            url,
            filter_type=normalized_filter,
            query=normalized_query or None,
            cache_mode=normalized_cache_mode,
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
                'cache_mode': normalized_cache_mode,
                'query_sha256_12': _sha256_12(normalized_query),
                'query_chars': _safe_len(normalized_query),
            }
        markdown = (data.get("markdown") or "").strip()
        if not markdown:
            return {
                'status': 'empty',
                'markdown': '',
                'error_class': None,
                'filter': actual_filter,
                'cache_mode': normalized_cache_mode,
                'query_sha256_12': _sha256_12(normalized_query),
                'query_chars': _safe_len(normalized_query),
            }
        return {
            'status': 'success',
            'markdown': markdown,
            'error_class': None,
            'filter': actual_filter,
            'cache_mode': normalized_cache_mode,
            'query_sha256_12': _sha256_12(normalized_query),
            'query_chars': _safe_len(normalized_query),
        }
    except Exception as e:
        logger.warning("crawl_error url=%s filter=%s err=%s", url, normalized_filter, e)
        return {
            'status': 'error',
            'markdown': '',
            'error_class': e.__class__.__name__,
            'filter': normalized_filter,
            'cache_mode': normalized_cache_mode,
            'query_sha256_12': _sha256_12(normalized_query),
            'query_chars': _safe_len(normalized_query),
        }


def _call_crawl_markdown_with_status(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
) -> dict[str, Any]:
    crawl_func = _crawl_markdown_with_status
    try:
        signature = inspect.signature(crawl_func)
        params = signature.parameters
        supports_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in params.values()
        )
        kwargs: dict[str, Any] = {'filter_type': filter_type}
        if supports_kwargs or 'query' in params:
            kwargs['query'] = query
        if supports_kwargs or 'cache_mode' in params:
            kwargs['cache_mode'] = cache_mode
        result = crawl_func(url, **kwargs)
    except (TypeError, ValueError):
        result = crawl_func(url, filter_type=filter_type, query=query)
    normalized = dict(result or {})
    normalized.setdefault('filter', str(filter_type or CRAWL4AI_FILTER_FIT))
    normalized.setdefault('cache_mode', str(cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE))
    normalized.setdefault('query_sha256_12', _sha256_12(query))
    normalized.setdefault('query_chars', _safe_len(query))
    return normalized


def _crawl_explicit_url_primary_with_status(url: str) -> dict[str, Any]:
    """Lecture primaire d'une URL explicite: fit d'abord, raw seulement si fit est vide."""
    fit_result = _call_crawl_markdown_with_status(url, filter_type=CRAWL4AI_FILTER_FIT)
    fit_result['raw_fallback_used'] = False
    fit_result['crawl_policy_kind'] = 'explicit_url_direct_fit_then_raw'
    fit_result['crawl_policy_reason'] = 'explicit_url_fit_primary'
    fit_result['crawl_filter_requested'] = CRAWL4AI_FILTER_FIT
    fit_result['crawl_primary_filter'] = CRAWL4AI_FILTER_FIT
    fit_result['crawl_fallback_filter'] = CRAWL4AI_FILTER_RAW
    fit_result['crawl_fallback_used'] = False
    fit_result['crawl_fallback_reason'] = ''
    fit_result['crawl_primary_status'] = str(fit_result.get('status') or '')
    fit_result['crawl_fallback_status'] = ''
    if str(fit_result.get('status') or '') != 'empty':
        return fit_result

    raw_result = _call_crawl_markdown_with_status(url, filter_type=CRAWL4AI_FILTER_RAW)
    raw_result['raw_fallback_used'] = True
    raw_result['crawl_policy_kind'] = 'explicit_url_direct_fit_then_raw'
    raw_result['crawl_policy_reason'] = 'explicit_url_raw_only_after_empty_fit'
    raw_result['crawl_filter_requested'] = CRAWL4AI_FILTER_RAW
    raw_result['crawl_primary_filter'] = CRAWL4AI_FILTER_FIT
    raw_result['crawl_fallback_filter'] = CRAWL4AI_FILTER_RAW
    raw_result['crawl_fallback_used'] = True
    raw_result['crawl_fallback_reason'] = 'fit_empty_raw_fallback'
    raw_result['crawl_primary_status'] = str(fit_result.get('status') or '')
    raw_result['crawl_fallback_status'] = str(raw_result.get('status') or '')
    return raw_result


def _annotate_crawl_result(
    crawl_result: dict[str, Any],
    *,
    policy: web_search_crawl_policy.Crawl4AIExtractionPolicy,
    requested_filter: str,
    used_filter: str | None = None,
    fallback_used: bool = False,
    fallback_reason: str = '',
    primary_status: str = '',
    fallback_status: str = '',
) -> dict[str, Any]:
    result = dict(crawl_result or {})
    query = str(policy.query or '')
    result['crawl_policy_kind'] = str(policy.kind or '')
    result['crawl_policy_reason'] = str(policy.reason_code or '')
    result['crawl_filter_requested'] = str(requested_filter or policy.primary_filter or CRAWL4AI_FILTER_FIT)
    result['crawl_primary_filter'] = str(policy.primary_filter or CRAWL4AI_FILTER_FIT)
    result['crawl_fallback_filter'] = str(policy.fallback_filter or '')
    result['crawl_filter_used'] = str(used_filter or result.get('filter') or requested_filter or CRAWL4AI_FILTER_FIT)
    result['crawl_cache_mode'] = str(policy.cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE)
    result['crawl_query_sha256_12'] = _sha256_12(query)
    result['crawl_query_chars'] = _safe_len(query)
    result['crawl_fallback_used'] = bool(fallback_used)
    result['crawl_fallback_reason'] = str(fallback_reason or '')
    result['crawl_primary_status'] = str(primary_status or result.get('status') or '')
    result['crawl_fallback_status'] = str(fallback_status or '')
    result['crawl_markdown_chars'] = len(str(result.get('markdown') or ''))
    result['crawl_max_chars'] = int(policy.max_chars or 0)
    return result


def _crawl_search_result_with_policy(
    url: str,
    policy: web_search_crawl_policy.Crawl4AIExtractionPolicy,
) -> dict[str, Any]:
    primary = _call_crawl_markdown_with_status(
        url,
        filter_type=policy.primary_filter,
        query=policy.query or None,
        cache_mode=policy.cache_mode,
    )
    should_fallback, fallback_reason = web_search_crawl_policy.should_fallback_from_primary(policy, primary)
    primary_status = str(primary.get('status') or '')
    if not should_fallback:
        return _annotate_crawl_result(
            primary,
            policy=policy,
            requested_filter=policy.primary_filter,
            used_filter=str(primary.get('filter') or policy.primary_filter),
            primary_status=primary_status,
        )

    fallback = _call_crawl_markdown_with_status(
        url,
        filter_type=policy.fallback_filter,
        query=None,
        cache_mode=policy.cache_mode,
    )
    fallback_status = str(fallback.get('status') or '')
    fallback_markdown = str(fallback.get('markdown') or '')
    selected = fallback if fallback_markdown else primary
    selected_filter = str(selected.get('filter') or policy.fallback_filter or policy.primary_filter)
    selected_is_fallback = selected is fallback
    return _annotate_crawl_result(
        selected,
        policy=policy,
        requested_filter=policy.primary_filter,
        used_filter=selected_filter,
        fallback_used=selected_is_fallback,
        fallback_reason=fallback_reason,
        primary_status=primary_status,
        fallback_status=fallback_status,
    )


def _build_source_payload(
    rank: int,
    result: dict[str, Any],
    *,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    source_origin: str = 'search_result',
    is_primary_source: bool = False,
    search_profile: str = web_search_profile.PROFILE_GENERAL,
    primary_query: str = '',
    enable_profiled_crawl4ai_policy: bool = True,
) -> dict[str, Any]:
    title = str(result.get('title') or '')
    url = str(result.get('url') or '')
    search_snippet = str(result.get('content') or '')
    query_source_kind = str(result.get('query_source_kind') or result.get('_query_source_kind') or 'primary')
    try:
        query_source_index = int(result.get('query_source_index') or result.get('_query_source_index') or 0)
    except (TypeError, ValueError):
        query_source_index = 0
    query_source_sha256_12 = str(
        result.get('query_source_sha256_12')
        or result.get('_query_source_sha256_12')
        or ''
    )
    used_in_prompt = False
    used_content_kind = 'none'
    content_used = ''
    truncated = False
    crawl_status = 'not_attempted'
    crawl_result: dict[str, Any] = {}

    if rank <= crawl4ai_top_n:
        if preloaded_crawl_results and url in preloaded_crawl_results:
            crawl_result = dict(preloaded_crawl_results[url])
        else:
            if enable_profiled_crawl4ai_policy:
                policy = web_search_crawl_policy.build_search_result_policy(
                    search_profile,
                    primary_query=primary_query,
                    runtime_max_chars=crawl4ai_max_chars,
                )
            else:
                policy = web_search_crawl_policy.Crawl4AIExtractionPolicy(
                    kind='historical_fit',
                    reason_code='profiled_crawl4ai_policy_disabled',
                    primary_filter=CRAWL4AI_FILTER_FIT,
                    cache_mode=web_search_crawl_policy.CACHE_FRESH_WRITE,
                    max_chars=int(crawl4ai_max_chars or 0),
                )
            if web_search_crawl_policy.is_historical_fit(policy):
                crawl_result = _annotate_crawl_result(
                    crawl_with_status(url),
                    policy=policy,
                    requested_filter=policy.primary_filter,
                    used_filter=policy.primary_filter,
                    primary_status='',
                )
            else:
                crawl_result = _crawl_search_result_with_policy(url, policy)
        crawled_markdown = str(crawl_result.get('markdown') or '')
        crawl_status = str(crawl_result.get('status') or 'error')
        if crawled_markdown:
            max_chars_for_source = int(crawl_result.get('crawl_max_chars') or crawl4ai_max_chars)
            content_used, truncated = _truncate_crawl_markdown(crawled_markdown, max_chars_for_source)
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
        'crawl_filter': str(crawl_result.get('crawl_filter_used') or crawl_result.get('filter') or ''),
        'crawl_filter_requested': str(crawl_result.get('crawl_filter_requested') or ''),
        'crawl_policy_kind': str(crawl_result.get('crawl_policy_kind') or ''),
        'crawl_policy_reason': str(crawl_result.get('crawl_policy_reason') or ''),
        'crawl_cache_mode': str(
            crawl_result.get('crawl_cache_mode')
            or crawl_result.get('cache_mode')
            or ''
        ),
        'crawl_query_sha256_12': str(
            crawl_result.get('crawl_query_sha256_12')
            or crawl_result.get('query_sha256_12')
            or ''
        ),
        'crawl_query_chars': int(crawl_result.get('crawl_query_chars') or crawl_result.get('query_chars') or 0),
        'crawl_fallback_used': bool(crawl_result.get('crawl_fallback_used', False)),
        'crawl_fallback_reason': str(crawl_result.get('crawl_fallback_reason') or ''),
        'crawl_primary_status': str(crawl_result.get('crawl_primary_status') or crawl_status or ''),
        'crawl_fallback_status': str(crawl_result.get('crawl_fallback_status') or ''),
        'crawl_markdown_chars': int(crawl_result.get('crawl_markdown_chars') or len(str(crawl_result.get('markdown') or ''))),
        'crawl_max_chars': int(crawl_result.get('crawl_max_chars') or crawl4ai_max_chars or 0),
        'query_source_kind': query_source_kind,
        'query_source_index': query_source_index,
        'query_source_sha256_12': query_source_sha256_12,
        'raw_rank': result.get('raw_rank'),
        'reranked_rank': result.get('reranked_rank'),
        'rerank_score': result.get('rerank_score'),
        'rerank_bucket': str(result.get('rerank_bucket') or ''),
        'rerank_reason_codes': list(result.get('rerank_reason_codes') or []),
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


def _build_crawl4ai_extraction_summary(sources: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
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
                'crawl_status': str(source.get('crawl_status') or 'not_attempted'),
                'crawl_filter': str(source.get('crawl_filter') or ''),
                'crawl_filter_requested': str(source.get('crawl_filter_requested') or ''),
                'crawl_policy_kind': str(source.get('crawl_policy_kind') or ''),
                'crawl_policy_reason': str(source.get('crawl_policy_reason') or ''),
                'crawl_cache_mode': str(source.get('crawl_cache_mode') or ''),
                'crawl_query_sha256_12': str(source.get('crawl_query_sha256_12') or ''),
                'crawl_query_chars': int(source.get('crawl_query_chars') or 0),
                'crawl_fallback_used': bool(source.get('crawl_fallback_used', False)),
                'crawl_fallback_reason': str(source.get('crawl_fallback_reason') or ''),
                'crawl_primary_status': str(source.get('crawl_primary_status') or ''),
                'crawl_fallback_status': str(source.get('crawl_fallback_status') or ''),
                'crawl_markdown_chars': int(source.get('crawl_markdown_chars') or 0),
                'crawl_max_chars': int(source.get('crawl_max_chars') or 0),
                'used_content_kind': str(source.get('used_content_kind') or 'none'),
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


def _count_crawl4ai_extraction_field(
    crawl4ai_extraction_summary: list[dict[str, Any]] | None,
    field: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get(field) or '').strip()
        if not value:
            continue
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _crawl4ai_policy_kinds(crawl4ai_extraction_summary: list[dict[str, Any]] | None) -> list[str]:
    kinds: list[str] = []
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get('crawl_policy_kind') or '').strip()
        if value and value not in kinds:
            kinds.append(value)
    return kinds


def _crawl4ai_query_hashes(crawl4ai_extraction_summary: list[dict[str, Any]] | None) -> list[str]:
    hashes: list[str] = []
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get('crawl_query_sha256_12') or '').strip()
        if value and value not in hashes:
            hashes.append(value)
    return hashes


def _augment_payload_observability(payload: dict[str, Any]) -> dict[str, Any]:
    source_material_summary = _build_source_material_summary(list(payload.get('sources') or []))
    crawl4ai_extraction_summary = _build_crawl4ai_extraction_summary(list(payload.get('sources') or []))
    payload['source_material_summary'] = source_material_summary
    payload['crawl4ai_extraction_summary'] = crawl4ai_extraction_summary
    payload['crawl4ai_policy_kinds'] = _crawl4ai_policy_kinds(crawl4ai_extraction_summary)
    payload['crawl4ai_filter_counts'] = _count_crawl4ai_extraction_field(crawl4ai_extraction_summary, 'crawl_filter')
    payload['crawl4ai_cache_modes'] = _count_crawl4ai_extraction_field(crawl4ai_extraction_summary, 'crawl_cache_mode')
    payload['crawl4ai_fallback_used_count'] = sum(
        1
        for item in crawl4ai_extraction_summary
        if bool(item.get('crawl_fallback_used', False))
    )
    payload['crawl4ai_query_sha256_12'] = _crawl4ai_query_hashes(crawl4ai_extraction_summary)
    payload['used_content_kinds'] = _derive_used_content_kinds(source_material_summary)
    payload['injected_chars'] = _derive_injected_chars(source_material_summary)
    payload['context_chars'] = len(str(payload.get('context_block') or ''))
    payload.update(web_search_confidence.evaluate_web_confidence(payload))
    return payload


def _web_confidence_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        'web_confidence_policy_kind': str(payload.get('web_confidence_policy_kind') or ''),
        'web_confidence_level': str(payload.get('web_confidence_level') or 'unknown'),
        'web_confidence_score': float(payload.get('web_confidence_score') or 0.0),
        'web_confidence_reason_codes': list(payload.get('web_confidence_reason_codes') or []),
        'web_confidence_inputs_summary': dict(payload.get('web_confidence_inputs_summary') or {}),
        'openrouter_fallback_state': str(payload.get('openrouter_fallback_state') or 'future_only'),
        'openrouter_fallback_used': bool(payload.get('openrouter_fallback_used', False)),
        'openrouter_fallback_reason_codes': list(payload.get('openrouter_fallback_reason_codes') or []),
    }


def _empty_query_plan(kind: str) -> dict[str, Any]:
    return {
        'query_plan_kind': str(kind or 'none'),
        'queries': [],
        'query_count': 0,
        'primary_query_sha256_12': '',
        'secondary_query_count': 0,
        'secondary_query_sha256_12': [],
        'raw_result_count': 0,
        'deduped_result_count': 0,
        **web_search_source_first.empty_observability_fields(),
        **web_search_searxng_params.empty_observability_fields(kind='none'),
        **web_search_rerank.empty_observability_fields(applied=False),
    }


def _build_query_plan(
    *,
    user_msg: str,
    primary_query: str,
    search_profile: str,
    enable_specialized_queries: bool,
    enable_profiled_searxng_params: bool,
) -> dict[str, Any]:
    primary = str(primary_query or '').strip()
    source_first_plan = web_search_source_first.build_source_first_plan(
        user_msg,
        primary,
        search_profile,
    )
    secondary_queries = (
        web_search_query_plan.build_specialized_queries(
            user_msg,
            primary,
            search_profile,
            source_first_plan=source_first_plan,
        )
        if enable_specialized_queries
        else []
    )
    searxng_profile_params = web_search_searxng_params.build_profile_params(
        search_profile,
        enabled=enable_profiled_searxng_params,
    )
    queries: list[dict[str, Any]] = []
    if primary:
        queries.append(
            {
                'query': primary,
                'query_source_kind': 'primary',
                'query_source_index': 0,
                'query_source_sha256_12': _sha256_12(primary),
            }
        )
    for offset, query in enumerate(secondary_queries, 1):
        queries.append(
            {
                'query': query,
                'query_source_kind': 'secondary',
                'query_source_index': offset,
                'query_source_sha256_12': _sha256_12(query),
            }
        )
    query_count = len(queries)
    secondary_hashes = [_sha256_12(query) for query in secondary_queries]
    return {
        'query_plan_kind': 'profiled_bounded' if secondary_queries else 'single_query',
        'queries': queries,
        'query_count': query_count,
        'primary_query_sha256_12': _sha256_12(primary),
        'secondary_query_count': len(secondary_queries),
        'secondary_query_sha256_12': secondary_hashes,
        'raw_result_count': 0,
        'deduped_result_count': 0,
        'source_first': source_first_plan.as_dict(),
        **source_first_plan.as_observability_fields(),
        'searxng_request_params': searxng_profile_params.as_request_params(),
        **searxng_profile_params.as_observability_fields(),
    }


def _query_plan_observability_fields(query_plan: dict[str, Any] | None) -> dict[str, Any]:
    plan = dict(query_plan or {})
    return {
        'query_plan_kind': str(plan.get('query_plan_kind') or 'none'),
        'query_count': int(plan.get('query_count') or 0),
        'primary_query_sha256_12': str(plan.get('primary_query_sha256_12') or ''),
        'secondary_query_count': int(plan.get('secondary_query_count') or 0),
        'secondary_query_sha256_12': list(plan.get('secondary_query_sha256_12') or []),
        'raw_result_count': int(plan.get('raw_result_count') or 0),
        'deduped_result_count': int(plan.get('deduped_result_count') or 0),
        'source_first_policy_kind': str(plan.get('source_first_policy_kind') or 'none'),
        'source_first_active': bool(plan.get('source_first_active', False)),
        'source_first_authority': str(plan.get('source_first_authority') or ''),
        'source_first_product': str(plan.get('source_first_product') or ''),
        'source_first_probable_domains': list(plan.get('source_first_probable_domains') or []),
        'source_first_reason_codes': list(plan.get('source_first_reason_codes') or []),
        'searxng_profile_params_kind': str(plan.get('searxng_profile_params_kind') or 'none'),
        'searxng_profile_params_policy': str(plan.get('searxng_profile_params_policy') or 'none'),
        'searxng_categories': list(plan.get('searxng_categories') or []),
        'searxng_engines': list(plan.get('searxng_engines') or []),
        'searxng_time_range': str(plan.get('searxng_time_range') or ''),
        'searxng_language': str(plan.get('searxng_language') or ''),
        'searxng_safesearch': str(plan.get('searxng_safesearch') or ''),
        'searxng_params_reason_codes': list(plan.get('searxng_params_reason_codes') or []),
        'searxng_hard_parameters': list(plan.get('searxng_hard_parameters') or []),
        'searxng_soft_signal_policy': str(plan.get('searxng_soft_signal_policy') or ''),
        'rerank_applied': bool(plan.get('rerank_applied', False)),
        'rerank_policy': str(plan.get('rerank_policy') or 'none'),
        'rerank_input_count': int(plan.get('rerank_input_count') or 0),
        'rerank_output_count': int(plan.get('rerank_output_count') or 0),
        'rerank_profile': str(plan.get('rerank_profile') or ''),
        'rerank_top_domains_before': list(plan.get('rerank_top_domains_before') or []),
        'rerank_top_domains_after': list(plan.get('rerank_top_domains_after') or []),
        'rerank_reason_counts': dict(plan.get('rerank_reason_counts') or {}),
        'rerank_promoted_count': int(plan.get('rerank_promoted_count') or 0),
        'rerank_downranked_count': int(plan.get('rerank_downranked_count') or 0),
    }


def _with_query_source(result: dict[str, Any], query_entry: dict[str, Any]) -> dict[str, Any]:
    enriched = dict(result or {})
    enriched['query_source_kind'] = str(query_entry.get('query_source_kind') or 'primary')
    enriched['query_source_index'] = int(query_entry.get('query_source_index') or 0)
    enriched['query_source_sha256_12'] = str(query_entry.get('query_source_sha256_12') or '')
    return enriched


def _interleave_and_dedupe_query_results(
    query_result_groups: list[tuple[dict[str, Any], list[dict[str, str]]]],
    *,
    max_results: int,
) -> tuple[list[dict[str, Any]], int]:
    raw_result_count = sum(len(results) for _, results in query_result_groups)
    max_group_length = max((len(results) for _, results in query_result_groups), default=0)
    seen_urls: set[str] = set()
    merged: list[dict[str, Any]] = []
    for result_index in range(max_group_length):
        for query_entry, results in query_result_groups:
            if result_index >= len(results):
                continue
            result = results[result_index]
            normalized_url = _normalized_source_url(str(result.get('url') or ''))
            if normalized_url and normalized_url in seen_urls:
                continue
            if normalized_url:
                seen_urls.add(normalized_url)
            merged.append(_with_query_source(dict(result), query_entry))
            if max_results > 0 and len(merged) >= max_results:
                return merged, raw_result_count
    return merged, raw_result_count


def _call_search_with_profile_params(
    query: str,
    searxng_params: dict[str, str] | None,
) -> list[dict[str, str]]:
    try:
        signature = inspect.signature(search)
        accepts_profile_params = (
            'searxng_params' in signature.parameters
            or any(
                parameter.kind == inspect.Parameter.VAR_KEYWORD
                for parameter in signature.parameters.values()
            )
        )
    except (TypeError, ValueError):
        accepts_profile_params = False
    if accepts_profile_params:
        return search(query, searxng_params=searxng_params)
    return search(query)


def _run_search_query_plan(
    query_plan: dict[str, Any],
    *,
    user_msg: str,
    primary_query: str,
    search_profile: str,
    enable_reranking: bool,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queries = list(query_plan.get('queries') or [])
    if not queries:
        plan = dict(query_plan)
        plan['raw_result_count'] = 0
        plan['deduped_result_count'] = 0
        plan.update(web_search_rerank.empty_observability_fields(applied=False))
        return [], plan

    max_results = int(_safe_runtime_services_value('searxng_results') or 0)
    searxng_params = dict(query_plan.get('searxng_request_params') or {})
    query_result_groups: list[tuple[dict[str, Any], list[dict[str, str]]]] = []
    for query_entry in queries:
        query = str(query_entry.get('query') or '')
        query_result_groups.append((query_entry, _call_search_with_profile_params(query, searxng_params)))

    merged_results, raw_result_count = _interleave_and_dedupe_query_results(
        query_result_groups,
        max_results=max_results,
    )
    plan = dict(query_plan)
    plan['raw_result_count'] = raw_result_count
    plan['deduped_result_count'] = len(merged_results)
    reranked_results, rerank_observability = web_search_rerank.rerank_results(
        merged_results,
        user_msg=user_msg,
        primary_query=primary_query,
        search_profile=search_profile,
        max_results=max_results,
        enabled=enable_reranking,
        source_first_plan=query_plan.get('source_first'),
    )
    plan.update(rerank_observability)
    return reranked_results, plan


def _build_context_material(
    query: str,
    results: list[dict[str, Any]],
    *,
    now_iso: str | None = None,
    search_profile: str = web_search_profile.PROFILE_GENERAL,
) -> dict[str, Any]:
    return _build_search_context_material(query, results, now_iso=now_iso, search_profile=search_profile)


def _build_explicit_url_fallback_source(
    explicit_url: str,
    *,
    matching_result: dict[str, Any] | None,
    primary_read_status: str,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    search_profile: str = web_search_profile.PROFILE_EXPLICIT_URL,
    primary_query: str = '',
    enable_profiled_crawl4ai_policy: bool = True,
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
        search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
        primary_query='',
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
    crawl_result: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    crawl4ai_max_chars = _explicit_url_max_chars(runtime)
    today = _web_temporal_label(now_iso=now_iso)
    content_used, truncated = _truncate_crawl_markdown(crawled_markdown, crawl4ai_max_chars)
    crawl_payload = dict(crawl_result or {})
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
        'crawl_filter': str(crawl_payload.get('crawl_filter_used') or crawl_payload.get('filter') or CRAWL4AI_FILTER_FIT),
        'crawl_filter_requested': str(crawl_payload.get('crawl_filter_requested') or crawl_payload.get('filter') or CRAWL4AI_FILTER_FIT),
        'crawl_policy_kind': str(crawl_payload.get('crawl_policy_kind') or 'explicit_url_direct_fit_then_raw'),
        'crawl_policy_reason': str(crawl_payload.get('crawl_policy_reason') or 'explicit_url_direct_success'),
        'crawl_cache_mode': str(
            crawl_payload.get('crawl_cache_mode')
            or crawl_payload.get('cache_mode')
            or web_search_crawl_policy.CACHE_FRESH_WRITE
        ),
        'crawl_query_sha256_12': str(crawl_payload.get('crawl_query_sha256_12') or crawl_payload.get('query_sha256_12') or ''),
        'crawl_query_chars': int(crawl_payload.get('crawl_query_chars') or crawl_payload.get('query_chars') or 0),
        'crawl_fallback_used': bool(crawl_payload.get('crawl_fallback_used', False)),
        'crawl_fallback_reason': str(crawl_payload.get('crawl_fallback_reason') or ''),
        'crawl_primary_status': str(crawl_payload.get('crawl_primary_status') or 'success'),
        'crawl_fallback_status': str(crawl_payload.get('crawl_fallback_status') or ''),
        'crawl_markdown_chars': len(str(crawled_markdown or '')),
        'crawl_max_chars': crawl4ai_max_chars,
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
    results: list[dict[str, Any]],
    *,
    explicit_url: str | None = None,
    primary_read_status: str = 'not_attempted',
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    now_iso: str | None = None,
    search_profile: str = web_search_profile.PROFILE_GENERAL,
    enable_profiled_crawl4ai_policy: bool = True,
) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    crawl4ai_top_n = int(runtime.get('crawl4ai_top_n') or 0)
    crawl4ai_max_chars = int(runtime.get('crawl4ai_max_chars') or 0)
    today = _web_temporal_label(now_iso=now_iso)
    primary_source: dict[str, Any] | None = None
    fallback_results = list(results or [])

    if explicit_url:
        matching_result: dict[str, Any] | None = None
        deduped_results: list[dict[str, Any]] = []
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
            search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
            primary_query=query,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
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
            search_profile=search_profile,
            primary_query=query,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
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
        with_attribution = getattr(llm_module, 'with_provider_attribution', None)
        if callable(with_attribution):
            payload = with_attribution(payload, caller='web_reformulation')
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


def search(
    query: str,
    max_results: int | None = None,
    *,
    searxng_params: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Interroge SearXNG et retourne les résultats."""
    if max_results is None:
        max_results = int(_runtime_services_value('searxng_results'))
    try:
        params = {"q": query, "format": "json", "language": "fr-FR", "safesearch": "0"}
        params.update({key: value for key, value in dict(searxng_params or {}).items() if value})
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
    search_profile: str | None = None,
    query_plan_kind: str = 'none',
    query_count: int = 0,
    primary_query_sha256_12: str | None = None,
    secondary_query_count: int = 0,
    secondary_query_sha256_12: list[str] | None = None,
    raw_result_count: int = 0,
    deduped_result_count: int = 0,
    source_first_policy_kind: str = 'none',
    source_first_active: bool = False,
    source_first_authority: str = '',
    source_first_product: str = '',
    source_first_probable_domains: list[str] | None = None,
    source_first_reason_codes: list[str] | None = None,
    searxng_profile_params_kind: str = 'none',
    searxng_profile_params_policy: str = 'none',
    searxng_categories: list[str] | None = None,
    searxng_engines: list[str] | None = None,
    searxng_time_range: str = '',
    searxng_language: str = '',
    searxng_safesearch: str = '',
    searxng_params_reason_codes: list[str] | None = None,
    searxng_hard_parameters: list[str] | None = None,
    searxng_soft_signal_policy: str = '',
    rerank_applied: bool = False,
    rerank_policy: str = 'none',
    rerank_input_count: int = 0,
    rerank_output_count: int = 0,
    rerank_profile: str = '',
    rerank_top_domains_before: list[str] | None = None,
    rerank_top_domains_after: list[str] | None = None,
    rerank_reason_counts: dict[str, int] | None = None,
    rerank_promoted_count: int = 0,
    rerank_downranked_count: int = 0,
    used_content_kinds: list[str] | None = None,
    injected_chars: int | None = None,
    context_chars: int | None = None,
    source_material_summary: list[dict[str, Any]] | None = None,
    crawl4ai_extraction_summary: list[dict[str, Any]] | None = None,
    crawl4ai_policy_kinds: list[str] | None = None,
    crawl4ai_filter_counts: dict[str, int] | None = None,
    crawl4ai_cache_modes: dict[str, int] | None = None,
    crawl4ai_fallback_used_count: int | None = None,
    crawl4ai_query_sha256_12: list[str] | None = None,
    web_confidence_policy_kind: str | None = None,
    web_confidence_level: str | None = None,
    web_confidence_score: float | None = None,
    web_confidence_reason_codes: list[str] | None = None,
    web_confidence_inputs_summary: dict[str, Any] | None = None,
    openrouter_fallback_state: str | None = None,
    openrouter_fallback_used: bool = False,
    openrouter_fallback_reason_codes: list[str] | None = None,
) -> None:
    query_text = str(query_preview or '')
    if truncated is None:
        truncated = any(bool(source.get('truncated')) for source in (sources or []))
        if not truncated and context_block:
            truncated = '[...contenu tronqué]' in str(context_block)
    if source_material_summary is None:
        source_material_summary = _build_source_material_summary(list(sources or []))
    if crawl4ai_extraction_summary is None:
        crawl4ai_extraction_summary = _build_crawl4ai_extraction_summary(list(sources or []))
    if crawl4ai_policy_kinds is None:
        crawl4ai_policy_kinds = _crawl4ai_policy_kinds(crawl4ai_extraction_summary)
    if crawl4ai_filter_counts is None:
        crawl4ai_filter_counts = _count_crawl4ai_extraction_field(crawl4ai_extraction_summary, 'crawl_filter')
    if crawl4ai_cache_modes is None:
        crawl4ai_cache_modes = _count_crawl4ai_extraction_field(crawl4ai_extraction_summary, 'crawl_cache_mode')
    if crawl4ai_fallback_used_count is None:
        crawl4ai_fallback_used_count = sum(
            1
            for item in crawl4ai_extraction_summary
            if bool(item.get('crawl_fallback_used', False))
        )
    if crawl4ai_query_sha256_12 is None:
        crawl4ai_query_sha256_12 = _crawl4ai_query_hashes(crawl4ai_extraction_summary)
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
        'search_profile': str(search_profile or ''),
        'query_plan_kind': str(query_plan_kind or 'none'),
        'query_count': int(query_count or 0),
        'primary_query_sha256_12': str(primary_query_sha256_12 or ''),
        'secondary_query_count': int(secondary_query_count or 0),
        'secondary_query_sha256_12': list(secondary_query_sha256_12 or []),
        'raw_result_count': int(raw_result_count or 0),
        'deduped_result_count': int(deduped_result_count or 0),
        'source_first_policy_kind': str(source_first_policy_kind or 'none'),
        'source_first_active': bool(source_first_active),
        'source_first_authority': str(source_first_authority or ''),
        'source_first_product': str(source_first_product or ''),
        'source_first_probable_domains': list(source_first_probable_domains or []),
        'source_first_reason_codes': list(source_first_reason_codes or []),
        'searxng_profile_params_kind': str(searxng_profile_params_kind or 'none'),
        'searxng_profile_params_policy': str(searxng_profile_params_policy or 'none'),
        'searxng_categories': list(searxng_categories or []),
        'searxng_engines': list(searxng_engines or []),
        'searxng_time_range': str(searxng_time_range or ''),
        'searxng_language': str(searxng_language or ''),
        'searxng_safesearch': str(searxng_safesearch or ''),
        'searxng_params_reason_codes': list(searxng_params_reason_codes or []),
        'searxng_hard_parameters': list(searxng_hard_parameters or []),
        'searxng_soft_signal_policy': str(searxng_soft_signal_policy or ''),
        'rerank_applied': bool(rerank_applied),
        'rerank_policy': str(rerank_policy or 'none'),
        'rerank_input_count': int(rerank_input_count or 0),
        'rerank_output_count': int(rerank_output_count or 0),
        'rerank_profile': str(rerank_profile or ''),
        'rerank_top_domains_before': list(rerank_top_domains_before or []),
        'rerank_top_domains_after': list(rerank_top_domains_after or []),
        'rerank_reason_counts': dict(rerank_reason_counts or {}),
        'rerank_promoted_count': int(rerank_promoted_count or 0),
        'rerank_downranked_count': int(rerank_downranked_count or 0),
        'used_content_kinds': list(used_content_kinds or []),
        'injected_chars': int(injected_chars or 0),
        'context_chars': int(context_chars or 0),
        'source_material_summary': list(source_material_summary or []),
        'crawl4ai_extraction_summary': list(crawl4ai_extraction_summary or []),
        'crawl4ai_policy_kinds': list(crawl4ai_policy_kinds or []),
        'crawl4ai_filter_counts': dict(crawl4ai_filter_counts or {}),
        'crawl4ai_cache_modes': dict(crawl4ai_cache_modes or {}),
        'crawl4ai_fallback_used_count': int(crawl4ai_fallback_used_count or 0),
        'crawl4ai_query_sha256_12': list(crawl4ai_query_sha256_12 or []),
    }
    if web_confidence_policy_kind is None:
        payload.update(web_search_confidence.evaluate_web_confidence(payload))
    else:
        payload.update(
            {
                'web_confidence_policy_kind': str(web_confidence_policy_kind or ''),
                'web_confidence_level': str(web_confidence_level or 'unknown'),
                'web_confidence_score': float(web_confidence_score or 0.0),
                'web_confidence_reason_codes': list(web_confidence_reason_codes or []),
                'web_confidence_inputs_summary': dict(web_confidence_inputs_summary or {}),
                'openrouter_fallback_state': str(openrouter_fallback_state or 'future_only'),
                'openrouter_fallback_used': bool(openrouter_fallback_used),
                'openrouter_fallback_reason_codes': list(openrouter_fallback_reason_codes or []),
            }
        )
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
    search_profile: str,
    enable_specialized_queries: bool = True,
    enable_profiled_searxng_params: bool = True,
    enable_reranking: bool = True,
    enable_profiled_crawl4ai_policy: bool = True,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if explicit_url:
        direct_query_plan = _empty_query_plan('explicit_url_direct')
        primary_crawl = _crawl_explicit_url_primary_with_status(explicit_url)
        primary_read_status = str(primary_crawl.get('status') or 'error')
        primary_read_filter = str(primary_crawl.get('filter') or CRAWL4AI_FILTER_FIT)
        primary_read_raw_fallback_used = bool(primary_crawl.get('raw_fallback_used', False))
        if primary_read_status == 'success':
            material = _build_explicit_url_context_material(
                explicit_url,
                str(primary_crawl.get('markdown') or ''),
                crawl_result=primary_crawl,
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
                'search_profile': str(search_profile or ''),
                **_query_plan_observability_fields(direct_query_plan),
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
        query_plan = _build_query_plan(
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_specialized_queries=enable_specialized_queries,
            enable_profiled_searxng_params=enable_profiled_searxng_params,
        )
        results, query_plan = _run_search_query_plan(
            query_plan,
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_reranking=enable_reranking,
        )
        material = _build_search_context_material(
            query,
            results,
            explicit_url=explicit_url,
            primary_read_status=primary_read_status,
            preloaded_crawl_results={explicit_url: primary_crawl},
            now_iso=now_iso,
            search_profile=search_profile,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
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
            'search_profile': str(search_profile or ''),
            **_query_plan_observability_fields(query_plan),
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
    query_plan = _build_query_plan(
        user_msg=user_msg,
        primary_query=query,
        search_profile=search_profile,
        enable_specialized_queries=enable_specialized_queries,
        enable_profiled_searxng_params=enable_profiled_searxng_params,
    )
    results, query_plan = _run_search_query_plan(
        query_plan,
        user_msg=user_msg,
        primary_query=query,
        search_profile=search_profile,
        enable_reranking=enable_reranking,
    )
    material = _build_search_context_material(
        query,
        results,
        now_iso=now_iso,
        search_profile=search_profile,
        enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
    )
    has_results = int(material['results_count']) > 0
    return {
        'enabled': True,
        'status': 'ok' if has_results else 'skipped',
        'reason_code': None if has_results else 'no_data',
        'original_user_message': str(user_msg or ''),
        'search_profile': str(search_profile or ''),
        **_query_plan_observability_fields(query_plan),
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
    enable_specialized_queries: bool = True,
    enable_profiled_searxng_params: bool = True,
    enable_reranking: bool = True,
    enable_profiled_crawl4ai_policy: bool = True,
) -> dict[str, Any]:
    explicit_url = _extract_explicit_url(user_msg)
    search_profile = web_search_profile.classify_search_profile(
        user_msg,
        explicit_url=explicit_url,
    )
    try:
        payload = _augment_payload_observability(_build_payload_from_collection(
            user_msg=user_msg,
            explicit_url=explicit_url,
            search_profile=search_profile,
            enable_specialized_queries=enable_specialized_queries,
            enable_profiled_searxng_params=enable_profiled_searxng_params,
            enable_reranking=enable_reranking,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
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
            search_profile=str(payload.get('search_profile') or search_profile),
            query_plan_kind=str(payload.get('query_plan_kind') or 'none'),
            query_count=int(payload.get('query_count') or 0),
            primary_query_sha256_12=str(payload.get('primary_query_sha256_12') or ''),
            secondary_query_count=int(payload.get('secondary_query_count') or 0),
            secondary_query_sha256_12=list(payload.get('secondary_query_sha256_12') or []),
            raw_result_count=int(payload.get('raw_result_count') or 0),
            deduped_result_count=int(payload.get('deduped_result_count') or 0),
            source_first_policy_kind=str(payload.get('source_first_policy_kind') or 'none'),
            source_first_active=bool(payload.get('source_first_active', False)),
            source_first_authority=str(payload.get('source_first_authority') or ''),
            source_first_product=str(payload.get('source_first_product') or ''),
            source_first_probable_domains=list(payload.get('source_first_probable_domains') or []),
            source_first_reason_codes=list(payload.get('source_first_reason_codes') or []),
            searxng_profile_params_kind=str(payload.get('searxng_profile_params_kind') or 'none'),
            searxng_profile_params_policy=str(payload.get('searxng_profile_params_policy') or 'none'),
            searxng_categories=list(payload.get('searxng_categories') or []),
            searxng_engines=list(payload.get('searxng_engines') or []),
            searxng_time_range=str(payload.get('searxng_time_range') or ''),
            searxng_language=str(payload.get('searxng_language') or ''),
            searxng_safesearch=str(payload.get('searxng_safesearch') or ''),
            searxng_params_reason_codes=list(payload.get('searxng_params_reason_codes') or []),
            searxng_hard_parameters=list(payload.get('searxng_hard_parameters') or []),
            searxng_soft_signal_policy=str(payload.get('searxng_soft_signal_policy') or ''),
            rerank_applied=bool(payload.get('rerank_applied', False)),
            rerank_policy=str(payload.get('rerank_policy') or 'none'),
            rerank_input_count=int(payload.get('rerank_input_count') or 0),
            rerank_output_count=int(payload.get('rerank_output_count') or 0),
            rerank_profile=str(payload.get('rerank_profile') or ''),
            rerank_top_domains_before=list(payload.get('rerank_top_domains_before') or []),
            rerank_top_domains_after=list(payload.get('rerank_top_domains_after') or []),
            rerank_reason_counts=dict(payload.get('rerank_reason_counts') or {}),
            rerank_promoted_count=int(payload.get('rerank_promoted_count') or 0),
            rerank_downranked_count=int(payload.get('rerank_downranked_count') or 0),
            used_content_kinds=list(payload.get('used_content_kinds') or []),
            injected_chars=int(payload.get('injected_chars') or 0),
            context_chars=int(payload.get('context_chars') or 0),
            source_material_summary=list(payload.get('source_material_summary') or []),
            crawl4ai_extraction_summary=list(payload.get('crawl4ai_extraction_summary') or []),
            crawl4ai_policy_kinds=list(payload.get('crawl4ai_policy_kinds') or []),
            crawl4ai_filter_counts=dict(payload.get('crawl4ai_filter_counts') or {}),
            crawl4ai_cache_modes=dict(payload.get('crawl4ai_cache_modes') or {}),
            crawl4ai_fallback_used_count=int(payload.get('crawl4ai_fallback_used_count') or 0),
            crawl4ai_query_sha256_12=list(payload.get('crawl4ai_query_sha256_12') or []),
            **_web_confidence_event_fields(payload),
        )
        return payload
    except Exception as exc:
        error_payload = _augment_payload_observability({
            'enabled': True,
            'status': 'error',
            'reason_code': 'upstream_error',
            'original_user_message': str(user_msg or ''),
            'search_profile': str(search_profile or ''),
            **_query_plan_observability_fields(_empty_query_plan('error')),
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
            search_profile=str(error_payload.get('search_profile') or search_profile),
            query_plan_kind=str(error_payload.get('query_plan_kind') or 'error'),
            query_count=int(error_payload.get('query_count') or 0),
            primary_query_sha256_12=str(error_payload.get('primary_query_sha256_12') or ''),
            secondary_query_count=int(error_payload.get('secondary_query_count') or 0),
            secondary_query_sha256_12=list(error_payload.get('secondary_query_sha256_12') or []),
            raw_result_count=int(error_payload.get('raw_result_count') or 0),
            deduped_result_count=int(error_payload.get('deduped_result_count') or 0),
            source_first_policy_kind=str(error_payload.get('source_first_policy_kind') or 'none'),
            source_first_active=bool(error_payload.get('source_first_active', False)),
            source_first_authority=str(error_payload.get('source_first_authority') or ''),
            source_first_product=str(error_payload.get('source_first_product') or ''),
            source_first_probable_domains=list(error_payload.get('source_first_probable_domains') or []),
            source_first_reason_codes=list(error_payload.get('source_first_reason_codes') or []),
            searxng_profile_params_kind=str(error_payload.get('searxng_profile_params_kind') or 'none'),
            searxng_profile_params_policy=str(error_payload.get('searxng_profile_params_policy') or 'none'),
            searxng_categories=list(error_payload.get('searxng_categories') or []),
            searxng_engines=list(error_payload.get('searxng_engines') or []),
            searxng_time_range=str(error_payload.get('searxng_time_range') or ''),
            searxng_language=str(error_payload.get('searxng_language') or ''),
            searxng_safesearch=str(error_payload.get('searxng_safesearch') or ''),
            searxng_params_reason_codes=list(error_payload.get('searxng_params_reason_codes') or []),
            searxng_hard_parameters=list(error_payload.get('searxng_hard_parameters') or []),
            searxng_soft_signal_policy=str(error_payload.get('searxng_soft_signal_policy') or ''),
            rerank_applied=bool(error_payload.get('rerank_applied', False)),
            rerank_policy=str(error_payload.get('rerank_policy') or 'none'),
            rerank_input_count=int(error_payload.get('rerank_input_count') or 0),
            rerank_output_count=int(error_payload.get('rerank_output_count') or 0),
            rerank_profile=str(error_payload.get('rerank_profile') or ''),
            rerank_top_domains_before=list(error_payload.get('rerank_top_domains_before') or []),
            rerank_top_domains_after=list(error_payload.get('rerank_top_domains_after') or []),
            rerank_reason_counts=dict(error_payload.get('rerank_reason_counts') or {}),
            rerank_promoted_count=int(error_payload.get('rerank_promoted_count') or 0),
            rerank_downranked_count=int(error_payload.get('rerank_downranked_count') or 0),
            used_content_kinds=list(error_payload.get('used_content_kinds') or []),
            injected_chars=int(error_payload.get('injected_chars') or 0),
            context_chars=int(error_payload.get('context_chars') or 0),
            source_material_summary=list(error_payload.get('source_material_summary') or []),
            crawl4ai_extraction_summary=list(error_payload.get('crawl4ai_extraction_summary') or []),
            crawl4ai_policy_kinds=list(error_payload.get('crawl4ai_policy_kinds') or []),
            crawl4ai_filter_counts=dict(error_payload.get('crawl4ai_filter_counts') or {}),
            crawl4ai_cache_modes=dict(error_payload.get('crawl4ai_cache_modes') or {}),
            crawl4ai_fallback_used_count=int(error_payload.get('crawl4ai_fallback_used_count') or 0),
            crawl4ai_query_sha256_12=list(error_payload.get('crawl4ai_query_sha256_12') or []),
            **_web_confidence_event_fields(error_payload),
        )
        return error_payload


def build_context(
    user_msg: str,
    *,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
    enable_specialized_queries: bool = True,
    enable_profiled_searxng_params: bool = True,
    enable_reranking: bool = True,
    enable_profiled_crawl4ai_policy: bool = True,
) -> tuple[str, str, int]:
    """
    Pipeline complet : reformulation → SearXNG/Crawl4AI.
    Retourne (contexte, query_reformulee, nb_resultats_web).
    """
    explicit_url = _extract_explicit_url(user_msg)
    search_profile = web_search_profile.classify_search_profile(
        user_msg,
        explicit_url=explicit_url,
    )
    if explicit_url:
        payload = build_context_payload(
            user_msg,
            requests_module=requests_module,
            llm_module=llm_module,
            now_iso=now_iso,
            enable_specialized_queries=enable_specialized_queries,
            enable_profiled_searxng_params=enable_profiled_searxng_params,
            enable_reranking=enable_reranking,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
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
        query_plan = _build_query_plan(
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_specialized_queries=enable_specialized_queries,
            enable_profiled_searxng_params=enable_profiled_searxng_params,
        )
        results, query_plan = _run_search_query_plan(
            query_plan,
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_reranking=enable_reranking,
        )
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
            search_profile=search_profile,
            **_query_plan_observability_fields(query_plan),
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
            search_profile=search_profile,
            **_query_plan_observability_fields(_empty_query_plan('error')),
        )
        return '', str(user_msg or ''), 0
