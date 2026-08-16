#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import requests

from tools import web_search_discovery


WEB_SEARCH_UPSTREAM_ERROR_REASON = 'web_search_upstream_error'
SEARXNG_REQUEST_FAILED_REASON = 'searxng_request_failed'
SEARXNG_TIMEOUT_S = 10


@dataclass(frozen=True)
class DiscoveryClientResult:
    response: web_search_discovery.DiscoveryResponse
    error_class: str = ''


def search_local_with_status(
    query: str,
    *,
    searxng_url: str,
    max_results: int,
    searxng_params: Mapping[str, str] | None = None,
    timeout_s: int = SEARXNG_TIMEOUT_S,
    requests_module: Any = requests,
) -> dict[str, Any]:
    """Call SearXNG and normalize transport success or failure."""
    try:
        params = {'q': query, 'format': 'json', 'language': 'fr-FR', 'safesearch': '0'}
        params.update({key: value for key, value in dict(searxng_params or {}).items() if value})
        response = requests_module.get(
            f"{str(searxng_url or '').rstrip('/')}/search",
            params=params,
            timeout=timeout_s,
        )
        response.raise_for_status()
        results = response.json().get('results', [])[:max_results]
        return {
            'status': 'ok',
            'reason_code': None,
            'error_class': '',
            'results': [
                {
                    'title': result.get('title', ''),
                    'url': result.get('url', ''),
                    'content': result.get('content', ''),
                }
                for result in results
            ],
        }
    except Exception as exc:
        return {
            'status': 'error',
            'reason_code': WEB_SEARCH_UPSTREAM_ERROR_REASON,
            'error_class': type(exc).__name__,
            'results': [],
        }


def discover_with_status(
    query: str,
    *,
    search_profile: str,
    searxng_params: dict[str, str] | None,
    max_results: int,
    requested_provider: str | None,
    local_search_response: Callable[[str, dict[str, str] | None], dict[str, Any]],
    requests_module: Any = requests,
    llm_module: Any | None = None,
) -> DiscoveryClientResult:
    """Select the configured discovery client without exposing it to the context builder."""
    effective_provider = web_search_discovery.effective_provider(
        requested_provider=requested_provider,
        search_profile=search_profile,
    )
    if effective_provider != web_search_discovery.PROVIDER_LOCAL:
        return DiscoveryClientResult(
            response=web_search_discovery.discover_urls(
                query,
                search_profile=search_profile,
                searxng_params=searxng_params,
                max_results=max_results,
                requested_provider=requested_provider,
                requests_module=requests_module,
                llm_module=llm_module,
            )
        )

    search_response = local_search_response(query, searxng_params)
    status = str(search_response.get('status') or 'ok')
    reason_codes = ['local_searxng_discovery_used']
    error_class = ''
    if status == 'error':
        reason_codes.extend([SEARXNG_REQUEST_FAILED_REASON, WEB_SEARCH_UPSTREAM_ERROR_REASON])
        error_class = str(search_response.get('error_class') or '')
    result_limit = max_results if max_results > 0 else 5
    results = [
        _normalize_local_result(item)
        for item in list(search_response.get('results') or [])[:result_limit]
    ]
    return DiscoveryClientResult(
        response=web_search_discovery.DiscoveryResponse(
            results=results,
            observability=web_search_discovery.empty_observability_fields(
                requested_provider=requested_provider,
                effective_provider_value=web_search_discovery.PROVIDER_LOCAL,
                reason_codes=reason_codes,
            ),
        ),
        error_class=error_class,
    )


def _normalize_local_result(result: Mapping[str, Any]) -> dict[str, str]:
    url = str(result.get('url') or '').strip()
    return {
        'title': str(result.get('title') or '').strip(),
        'url': url,
        'content': str(result.get('content') or '').strip(),
        'discovery_source_kind': 'searxng_result',
        'discovery_domain': str(urlparse(url).netloc or '').lower(),
    }
