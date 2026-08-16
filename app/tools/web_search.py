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
    READ_STATE_PAGE_NOT_READ_ERROR,
)
from observability import chat_turn_logger
from tools import (
    web_reformulation_settings,
    web_search_profile,
    web_search_query_plan,
    web_search_source_first,
    web_search_crawl_policy,
    web_search_profile_policy,
    web_search_rerank,
    web_search_searxng_params,
    web_search_clients,
    web_search_context,
    web_search_discovery,
    web_search_readers,
    web_search_runtime_events,
    web_pdf_reader,
    web_public_url_policy,
)

logger = logging.getLogger("frida.web_search")
_EXPLICIT_URL_RE = re.compile(r'https?://[^\s<>"\']+')
WEB_SEARCH_UPSTREAM_ERROR_REASON = web_search_clients.WEB_SEARCH_UPSTREAM_ERROR_REASON
WEB_DISCOVERY_UPSTREAM_ERROR_REASON = 'web_discovery_upstream_error'
SEARXNG_REQUEST_FAILED_REASON = web_search_clients.SEARXNG_REQUEST_FAILED_REASON
_URL_TRAILING_PUNCTUATION = '.,;:!?)]}\'"'
CRAWL4AI_FILTER_FIT = web_search_readers.CRAWL4AI_FILTER_FIT
CRAWL4AI_FILTER_RAW = web_search_readers.CRAWL4AI_FILTER_RAW
WEB_PDF_CONTENT_KIND = web_search_context.WEB_PDF_CONTENT_KIND
WEB_SEARCH_SOURCE_ATTRIBUTION_LINE = web_search_context.WEB_SEARCH_SOURCE_ATTRIBUTION_LINE
WEB_SEARCH_FALLBACK_SOURCE_ATTRIBUTION_LINE = (
    web_search_context.WEB_SEARCH_FALLBACK_SOURCE_ATTRIBUTION_LINE
)


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
    return web_search_context.source_domain(url)


def _normalized_source_url(url: str) -> str:
    return web_search_context.normalized_source_url(url)


def _urls_match(left: str, right: str) -> bool:
    return web_search_context.urls_match(left, right)


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
    return web_search_context.truncate_search_snippet(content, max_chars)


def _truncate_crawl_markdown(content: str, max_chars: int) -> tuple[str, bool]:
    return web_search_context.truncate_crawl_markdown(content, max_chars)


def _explicit_url_max_chars(runtime: dict[str, int | None]) -> int:
    return web_search_context.explicit_url_max_chars(runtime)


def _build_crawl4ai_md_payload(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = '0',
) -> dict[str, str]:
    return web_search_readers.build_crawl4ai_md_payload(
        url,
        filter_type=filter_type,
        query=query,
        cache_mode=cache_mode,
    )


def _crawl_markdown_with_status(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
) -> dict[str, Any]:
    return web_search_readers.crawl_markdown_with_status(
        url,
        filter_type=filter_type,
        query=query,
        cache_mode=cache_mode,
        runtime_service_value=_runtime_services_value,
        runtime_token=_runtime_crawl4ai_token,
        requests_module=requests,
        payload_builder=_build_crawl4ai_md_payload,
        blocked_url_reason=web_public_url_policy.blocked_url_reason,
    )


def _call_crawl_markdown_with_status(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
) -> dict[str, Any]:
    return web_search_readers.call_crawl_markdown_with_status(
        url,
        crawl_func=_crawl_markdown_with_status,
        filter_type=filter_type,
        query=query,
        cache_mode=cache_mode,
    )


def _crawl_explicit_url_primary_with_status(url: str) -> dict[str, Any]:
    return web_search_readers.read_explicit_url_with_status(
        url,
        crawl_func=_crawl_markdown_with_status,
    )


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
    return web_search_readers.annotate_crawl_result(
        crawl_result,
        policy=policy,
        requested_filter=requested_filter,
        used_filter=used_filter,
        fallback_used=fallback_used,
        fallback_reason=fallback_reason,
        primary_status=primary_status,
        fallback_status=fallback_status,
    )


def _crawl_search_result_with_policy(
    url: str,
    policy: web_search_crawl_policy.Crawl4AIExtractionPolicy,
) -> dict[str, Any]:
    return web_search_readers.read_search_result_with_policy(
        url,
        policy,
        crawl_func=_crawl_markdown_with_status,
    )


def _read_web_pdf_as_crawl_result(
    url: str,
    *,
    max_chars: int,
    probe_content_type: bool,
) -> dict[str, Any] | None:
    return web_search_readers.read_pdf_as_crawl_result(
        url,
        max_chars=max_chars,
        probe_content_type=probe_content_type,
        pdf_reader_module=web_pdf_reader,
    )


def _web_pdf_source_fields(crawl_result: dict[str, Any]) -> dict[str, Any]:
    return web_search_context.web_pdf_source_fields(crawl_result)


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
        elif web_pdf_reader.is_pdf_url_candidate(url):
            crawl_result = _read_web_pdf_as_crawl_result(
                url,
                max_chars=crawl4ai_max_chars,
                probe_content_type=False,
            ) or {}
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
            if bool(crawl_result.get('web_pdf_read_attempted', False)):
                used_content_kind = WEB_PDF_CONTENT_KIND
            else:
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
        **_web_pdf_source_fields(crawl_result),
        'query_source_kind': query_source_kind,
        'query_source_index': query_source_index,
        'query_source_sha256_12': query_source_sha256_12,
        'raw_rank': result.get('raw_rank'),
        'reranked_rank': result.get('reranked_rank'),
        'rerank_score': result.get('rerank_score'),
        'rerank_bucket': str(result.get('rerank_bucket') or ''),
        'rerank_reason_codes': list(result.get('rerank_reason_codes') or []),
    }


def _augment_payload_observability(payload: dict[str, Any]) -> dict[str, Any]:
    return web_search_runtime_events.augment_payload_observability(payload)


def _web_confidence_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return web_search_runtime_events.web_confidence_event_fields(payload)


def _web_evidence_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return web_search_runtime_events.web_evidence_event_fields(payload)


def _profile_policy_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return web_search_runtime_events.profile_policy_event_fields(payload)


def _empty_query_plan(
    kind: str,
    *,
    search_profile: str = '',
    discovery_provider: str | None = None,
) -> dict[str, Any]:
    profile_policy = web_search_profile_policy.build_profile_policy(
        search_profile,
    ) if search_profile else None
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
        **(
            profile_policy.as_observability_fields()
            if profile_policy is not None
            else web_search_profile_policy.empty_observability_fields()
        ),
        **web_search_searxng_params.empty_observability_fields(kind='none'),
        **web_search_discovery.plan_observability_fields(
            search_profile=search_profile,
            requested_provider=discovery_provider,
        ),
        **web_search_rerank.empty_observability_fields(applied=False),
    }


def _build_query_plan(
    *,
    user_msg: str,
    primary_query: str,
    search_profile: str,
    enable_specialized_queries: bool,
    enable_profiled_searxng_params: bool,
    discovery_provider: str | None,
) -> dict[str, Any]:
    primary = str(primary_query or '').strip()
    source_first_plan = web_search_source_first.build_source_first_plan(
        user_msg,
        primary,
        search_profile,
    )
    profile_policy = web_search_profile_policy.build_profile_policy(
        search_profile,
        source_first_plan=source_first_plan,
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
        'profile_policy': profile_policy.as_dict(),
        **profile_policy.as_observability_fields(),
        'searxng_request_params': searxng_profile_params.as_request_params(),
        **searxng_profile_params.as_observability_fields(),
        **web_search_discovery.plan_observability_fields(
            search_profile=search_profile,
            requested_provider=discovery_provider,
        ),
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
        'profile_policy_kind': str(plan.get('profile_policy_kind') or 'none'),
        'profile_policy_mode': str(plan.get('profile_policy_mode') or 'none'),
        'profile_expected_domains': list(plan.get('profile_expected_domains') or []),
        'profile_secondary_domains': list(plan.get('profile_secondary_domains') or []),
        'profile_downrank_domains': list(plan.get('profile_downrank_domains') or []),
        'profile_situated_secondary_domains': list(plan.get('profile_situated_secondary_domains') or []),
        'profile_policy_reason_codes': list(plan.get('profile_policy_reason_codes') or []),
        'profile_crawl_top_n_budget': int(plan.get('profile_crawl_top_n_budget') or 0),
        'profile_crawl_max_chars_budget': int(plan.get('profile_crawl_max_chars_budget') or 0),
        'profile_manual_latency_target_s': int(plan.get('profile_manual_latency_target_s') or 0),
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
        'web_discovery_provider': str(plan.get('web_discovery_provider') or ''),
        'web_discovery_provider_requested': str(plan.get('web_discovery_provider_requested') or ''),
        'web_discovery_provider_effective': str(plan.get('web_discovery_provider_effective') or ''),
        'web_discovery_external_used': bool(plan.get('web_discovery_external_used', False)),
        'web_discovery_external_provider': str(plan.get('web_discovery_external_provider') or ''),
        'web_discovery_external_error_kind': str(plan.get('web_discovery_external_error_kind') or ''),
        'web_discovery_reason_codes': list(plan.get('web_discovery_reason_codes') or []),
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


def _query_plan_event_kwargs(query_plan: dict[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any]]:
    fields = _query_plan_observability_fields(query_plan)
    event_kwargs = {
        key: value
        for key, value in fields.items()
        if not key.startswith('profile_')
    }
    return event_kwargs, fields


def _web_search_payload_status(
    *,
    has_results: bool,
    query_plan: dict[str, Any] | None,
) -> tuple[str, str | None, str]:
    return web_search_context.web_search_payload_status(
        has_results=has_results,
        query_plan=query_plan,
        local_error_reason_code=WEB_SEARCH_UPSTREAM_ERROR_REASON,
        discovery_error_reason_code=WEB_DISCOVERY_UPSTREAM_ERROR_REASON,
    )


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


def _call_discovery_with_profile_params(
    query: str,
    *,
    search_profile: str,
    searxng_params: dict[str, str] | None,
    max_results: int,
    discovery_provider: str | None,
    requests_module: Any = requests,
    llm_module: Any | None = None,
) -> web_search_clients.DiscoveryClientResult:
    return web_search_clients.discover_with_status(
        query,
        search_profile=search_profile,
        searxng_params=searxng_params,
        max_results=max_results,
        requested_provider=discovery_provider,
        local_search_response=_call_search_response_with_profile_params,
        requests_module=requests_module,
        llm_module=llm_module,
    )


def _run_search_query_plan(
    query_plan: dict[str, Any],
    *,
    user_msg: str,
    primary_query: str,
    search_profile: str,
    enable_reranking: bool,
    discovery_provider: str | None,
    requests_module: Any = requests,
    llm_module: Any | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queries = list(query_plan.get('queries') or [])
    if not queries:
        plan = dict(query_plan)
        plan['raw_result_count'] = 0
        plan['deduped_result_count'] = 0
        plan.update(
            web_search_discovery.plan_observability_fields(
                search_profile=search_profile,
                requested_provider=discovery_provider,
            )
        )
        plan.update(web_search_rerank.empty_observability_fields(applied=False))
        return [], plan

    max_results = int(_safe_runtime_services_value('searxng_results') or 0)
    searxng_params = dict(query_plan.get('searxng_request_params') or {})
    query_result_groups: list[tuple[dict[str, Any], list[dict[str, str]]]] = []
    discovery_observability: list[dict[str, Any]] = []
    local_search_error_classes: list[str] = []
    for query_entry in queries:
        query = str(query_entry.get('query') or '')
        discovery_result = _call_discovery_with_profile_params(
            query,
            search_profile=search_profile,
            searxng_params=searxng_params,
            max_results=max_results,
            discovery_provider=discovery_provider,
            requests_module=requests_module,
            llm_module=llm_module,
        )
        discovery_response = discovery_result.response
        if discovery_result.error_class:
            local_search_error_classes.append(discovery_result.error_class)
        discovery_observability.append(discovery_response.observability)
        query_result_groups.append((query_entry, discovery_response.results))

    merged_results, raw_result_count = _interleave_and_dedupe_query_results(
        query_result_groups,
        max_results=max_results,
    )
    plan = dict(query_plan)
    plan['raw_result_count'] = raw_result_count
    plan['deduped_result_count'] = len(merged_results)
    plan['local_search_error_count'] = len(local_search_error_classes)
    plan['local_search_error_class'] = local_search_error_classes[0] if local_search_error_classes else ''
    plan.update(web_search_discovery.merge_observability_fields(discovery_observability))
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


def _build_explicit_url_context_material(
    url: str,
    crawled_markdown: str,
    *,
    crawl_result: dict[str, Any] | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    runtime = _runtime_collection_settings()
    today = _web_temporal_label(now_iso=now_iso)
    return web_search_context.build_explicit_url_context_material(
        url,
        crawled_markdown,
        crawl_result=crawl_result,
        runtime=runtime,
        today=today,
    )


def _derive_read_state(
    *,
    explicit_url: str | None,
    primary_read_status: str,
    sources: list[dict[str, Any]],
) -> str | None:
    return web_search_context.derive_read_state(
        explicit_url=explicit_url,
        primary_read_status=primary_read_status,
        sources=sources,
    )


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
    today = _web_temporal_label(now_iso=now_iso)
    return web_search_context.build_search_context_material(
        query,
        results,
        explicit_url=explicit_url,
        primary_read_status=primary_read_status,
        preloaded_crawl_results=preloaded_crawl_results,
        runtime=runtime,
        today=today,
        search_profile=search_profile,
        enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
        build_source_payload=_build_source_payload,
    )


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
        'provider_title_present': bool(provider_title),
        'provider_title_chars': _safe_len(provider_title),
        'provider_title_included': False,
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
        'system_prompt_hash_included': False,
        'current_user_hash_included': False,
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
        prompt_template = prompt_loader.require_usable_prompt_text(
            prompt_loader.get_web_reformulation_prompt(),
            prompt_id='web_reformulation',
        )
    except prompt_loader.RequiredPromptUnavailable as exc:
        logger.warning(
            "reformulate_skipped reason=prompt_missing prompt_id=%s",
            exc.prompt_id,
        )
        return user_msg

    try:
        if llm_module is None:
            from core import llm_client as llm_module

        today = _web_temporal_label(now_iso=now_iso)
        system_prompt = prompt_template.format(today=today)
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
        logger.warning(
            "reformulate_error reason=web_reformulation_exception err_class=%s",
            e.__class__.__name__,
        )
        return user_msg


def search(
    query: str,
    max_results: int | None = None,
    *,
    searxng_params: dict[str, str] | None = None,
) -> list[dict[str, str]]:
    """Interroge SearXNG et retourne les résultats."""
    return list(search_with_status(query, max_results=max_results, searxng_params=searxng_params).get('results') or [])


def search_with_status(
    query: str,
    max_results: int | None = None,
    *,
    searxng_params: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Interroge SearXNG avec un statut explicite content-free."""
    if max_results is None:
        max_results = int(_runtime_services_value('searxng_results'))
    response = web_search_clients.search_local_with_status(
        query,
        searxng_url=str(_runtime_services_value('searxng_url')),
        max_results=max_results,
        searxng_params=searxng_params,
        timeout_s=web_search_clients.SEARXNG_TIMEOUT_S,
        requests_module=requests,
    )
    if response.get('status') == 'error':
        logger.warning(
            "search_error query_chars=%s query_sha256_12=%s error_class=%s reason_code=searxng_request_failed",
            _safe_len(query),
            _sha256_12(query),
            response.get('error_class') or '',
        )
    return response


_DEFAULT_SEARCH_FUNCTION = search


def _call_search_response_with_profile_params(
    query: str,
    searxng_params: dict[str, str] | None,
) -> dict[str, Any]:
    if search is _DEFAULT_SEARCH_FUNCTION:
        return search_with_status(query, searxng_params=searxng_params)
    return {
        'status': 'ok',
        'reason_code': None,
        'error_class': '',
        'results': _call_search_with_profile_params(query, searxng_params),
    }


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


def _emit_web_search_runtime_event(**kwargs: Any) -> None:
    web_search_runtime_events.emit_web_search_runtime_event(**kwargs)


def _build_payload_from_collection(
    *,
    user_msg: str,
    explicit_url: str | None,
    search_profile: str,
    enable_specialized_queries: bool = True,
    enable_profiled_searxng_params: bool = True,
    enable_reranking: bool = True,
    enable_profiled_crawl4ai_policy: bool = True,
    discovery_provider: str | None = None,
    requests_module: Any = requests,
    llm_module: Any | None = None,
    now_iso: str | None = None,
) -> dict[str, Any]:
    if explicit_url:
        direct_query_plan = _empty_query_plan(
            'explicit_url_direct',
            search_profile=search_profile,
            discovery_provider=discovery_provider,
        )
        primary_crawl = None
        if web_pdf_reader.is_pdf_url_candidate(explicit_url):
            primary_crawl = _read_web_pdf_as_crawl_result(
                explicit_url,
                max_chars=_explicit_url_max_chars(_runtime_collection_settings()),
                probe_content_type=True,
            )
        if primary_crawl is None:
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
            discovery_provider=discovery_provider,
        )
        results, query_plan = _run_search_query_plan(
            query_plan,
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_reranking=enable_reranking,
            discovery_provider=discovery_provider,
            requests_module=requests_module,
            llm_module=llm_module,
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
        payload_status, payload_reason_code, payload_error_class = _web_search_payload_status(
            has_results=has_results,
            query_plan=query_plan,
        )
        read_state = _derive_read_state(
            explicit_url=explicit_url,
            primary_read_status=primary_read_status,
            sources=list(material['sources']),
        )
        return {
            'enabled': True,
            'status': payload_status,
            'reason_code': payload_reason_code,
            'error_class': payload_error_class,
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
        discovery_provider=discovery_provider,
    )
    results, query_plan = _run_search_query_plan(
        query_plan,
        user_msg=user_msg,
        primary_query=query,
        search_profile=search_profile,
        enable_reranking=enable_reranking,
        discovery_provider=discovery_provider,
        requests_module=requests_module,
        llm_module=llm_module,
    )
    material = _build_search_context_material(
        query,
        results,
        now_iso=now_iso,
        search_profile=search_profile,
        enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
    )
    has_results = int(material['results_count']) > 0
    payload_status, payload_reason_code, payload_error_class = _web_search_payload_status(
        has_results=has_results,
        query_plan=query_plan,
    )
    return {
        'enabled': True,
        'status': payload_status,
        'reason_code': payload_reason_code,
        'error_class': payload_error_class,
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
    discovery_provider: str | None = None,
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
            discovery_provider=discovery_provider,
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
            error_class=str(payload.get('error_class') or '') or None,
            message_short=(
                str(payload.get('reason_code') or '')
                if str(payload.get('status') or '') == 'error'
                else None
            ),
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
            profile_policy_fields=_profile_policy_event_fields(payload),
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
            web_discovery_provider=str(payload.get('web_discovery_provider') or ''),
            web_discovery_provider_requested=str(payload.get('web_discovery_provider_requested') or ''),
            web_discovery_provider_effective=str(payload.get('web_discovery_provider_effective') or ''),
            web_discovery_external_used=bool(payload.get('web_discovery_external_used', False)),
            web_discovery_external_provider=str(payload.get('web_discovery_external_provider') or ''),
            web_discovery_external_error_kind=str(payload.get('web_discovery_external_error_kind') or ''),
            web_discovery_reason_codes=list(payload.get('web_discovery_reason_codes') or []),
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
            web_pdf_read_summary=list(payload.get('web_pdf_read_summary') or []),
            web_pdf_read_attempted_count=int(payload.get('web_pdf_read_attempted_count') or 0),
            web_pdf_read_status_counts=dict(payload.get('web_pdf_read_status_counts') or {}),
            web_pdf_read_reason_codes=list(payload.get('web_pdf_read_reason_codes') or []),
            crawl4ai_policy_kinds=list(payload.get('crawl4ai_policy_kinds') or []),
            crawl4ai_filter_counts=dict(payload.get('crawl4ai_filter_counts') or {}),
            crawl4ai_cache_modes=dict(payload.get('crawl4ai_cache_modes') or {}),
            crawl4ai_fallback_used_count=int(payload.get('crawl4ai_fallback_used_count') or 0),
            crawl4ai_query_sha256_12=list(payload.get('crawl4ai_query_sha256_12') or []),
            **_web_confidence_event_fields(payload),
            **_web_evidence_event_fields(payload),
        )
        return payload
    except Exception as exc:
        error_payload = _augment_payload_observability({
            'enabled': True,
            'status': 'error',
            'reason_code': 'upstream_error',
            'original_user_message': str(user_msg or ''),
            'search_profile': str(search_profile or ''),
            **_query_plan_observability_fields(
                _empty_query_plan(
                    'error',
                    search_profile=search_profile,
                    discovery_provider=discovery_provider,
                )
            ),
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
            message_short=str(error_payload.get('reason_code') or 'upstream_error'),
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
            profile_policy_fields=_profile_policy_event_fields(error_payload),
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
            web_discovery_provider=str(error_payload.get('web_discovery_provider') or ''),
            web_discovery_provider_requested=str(error_payload.get('web_discovery_provider_requested') or ''),
            web_discovery_provider_effective=str(error_payload.get('web_discovery_provider_effective') or ''),
            web_discovery_external_used=bool(error_payload.get('web_discovery_external_used', False)),
            web_discovery_external_provider=str(error_payload.get('web_discovery_external_provider') or ''),
            web_discovery_external_error_kind=str(error_payload.get('web_discovery_external_error_kind') or ''),
            web_discovery_reason_codes=list(error_payload.get('web_discovery_reason_codes') or []),
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
            web_pdf_read_summary=list(error_payload.get('web_pdf_read_summary') or []),
            web_pdf_read_attempted_count=int(error_payload.get('web_pdf_read_attempted_count') or 0),
            web_pdf_read_status_counts=dict(error_payload.get('web_pdf_read_status_counts') or {}),
            web_pdf_read_reason_codes=list(error_payload.get('web_pdf_read_reason_codes') or []),
            crawl4ai_policy_kinds=list(error_payload.get('crawl4ai_policy_kinds') or []),
            crawl4ai_filter_counts=dict(error_payload.get('crawl4ai_filter_counts') or {}),
            crawl4ai_cache_modes=dict(error_payload.get('crawl4ai_cache_modes') or {}),
            crawl4ai_fallback_used_count=int(error_payload.get('crawl4ai_fallback_used_count') or 0),
            crawl4ai_query_sha256_12=list(error_payload.get('crawl4ai_query_sha256_12') or []),
            **_web_confidence_event_fields(error_payload),
            **_web_evidence_event_fields(error_payload),
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
    discovery_provider: str | None = None,
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
            discovery_provider=discovery_provider,
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
            discovery_provider=discovery_provider,
        )
        results, query_plan = _run_search_query_plan(
            query_plan,
            user_msg=user_msg,
            primary_query=query,
            search_profile=search_profile,
            enable_reranking=enable_reranking,
            discovery_provider=discovery_provider,
            requests_module=requests_module,
            llm_module=llm_module,
        )
        ctx_parts = []
        if results:
            if now_iso:
                ctx_parts.append(_format_context(query, results, now_iso=now_iso))
            else:
                ctx_parts.append(_format_context(query, results))
        ctx = "\n\n".join(ctx_parts)
        has_results = len(results) > 0
        payload_status, payload_reason_code, payload_error_class = _web_search_payload_status(
            has_results=has_results,
            query_plan=query_plan,
        )
        query_plan_event_kwargs, query_plan_fields = _query_plan_event_kwargs(query_plan)
        _emit_web_search_runtime_event(
            enabled=True,
            status=payload_status,
            reason_code=payload_reason_code,
            query_preview=str(query),
            results_count=len(results),
            context_block=ctx,
            sources=[],
            error_class=payload_error_class or None,
            message_short=payload_reason_code if payload_status == 'error' else None,
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
            profile_policy_fields=query_plan_fields,
            **query_plan_event_kwargs,
        )
        return ctx, query, len(results)
    except Exception as exc:
        query_plan_event_kwargs, query_plan_fields = _query_plan_event_kwargs(
            _empty_query_plan(
                'error',
                search_profile=search_profile,
                discovery_provider=discovery_provider,
            )
        )
        _emit_web_search_runtime_event(
            enabled=True,
            status='error',
            reason_code='upstream_error',
            query_preview=str(user_msg or ''),
            results_count=0,
            context_block='',
            sources=[],
            error_class=exc.__class__.__name__,
            message_short='upstream_error',
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
            profile_policy_fields=query_plan_fields,
            **query_plan_event_kwargs,
        )
        return '', str(user_msg or ''), 0
