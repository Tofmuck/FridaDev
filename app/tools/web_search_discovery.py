#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from typing import Any, Callable, Mapping
from urllib.parse import urlparse

import requests

import config
from tools import web_search_profile


PROVIDER_LOCAL = 'local'
PROVIDER_OPENROUTER_EXA = 'openrouter_exa'
SUPPORTED_PROVIDERS = frozenset({PROVIDER_LOCAL, PROVIDER_OPENROUTER_EXA})
OPENROUTER_SEARCH_TOOL_TYPE = 'openrouter:web_search'
OPENROUTER_ENGINE_EXA = 'exa'


@dataclass(frozen=True)
class DiscoveryResponse:
    results: list[dict[str, str]]
    observability: dict[str, Any]


def _sha256_12(value: str) -> str:
    text = str(value or '')
    if not text:
        return ''
    return hashlib.sha256(text.encode('utf-8')).hexdigest()[:12]


def _safe_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _normalized_provider(value: Any) -> str:
    provider = str(value or '').strip().lower()
    if provider in SUPPORTED_PROVIDERS:
        return provider
    return PROVIDER_LOCAL


def configured_provider() -> str:
    return _normalized_provider(
        os.environ.get(
            'WEB_SEARCH_DISCOVERY_PROVIDER',
            getattr(config, 'WEB_SEARCH_DISCOVERY_PROVIDER', PROVIDER_OPENROUTER_EXA),
        )
    )


def effective_provider(
    *,
    requested_provider: str | None = None,
    search_profile: str = '',
) -> str:
    requested = _normalized_provider(requested_provider or configured_provider())
    if str(search_profile or '') == web_search_profile.PROFILE_EXPLICIT_URL:
        return PROVIDER_LOCAL
    return requested


def empty_observability_fields(
    *,
    requested_provider: str | None = None,
    effective_provider_value: str | None = None,
    external_used: bool = False,
    reason_codes: list[str] | None = None,
    external_error_kind: str = '',
) -> dict[str, Any]:
    requested = _normalized_provider(requested_provider or configured_provider())
    effective = _normalized_provider(effective_provider_value or requested)
    return {
        'web_discovery_provider': effective,
        'web_discovery_provider_requested': requested,
        'web_discovery_provider_effective': effective,
        'web_discovery_external_used': bool(external_used),
        'web_discovery_external_provider': (
            'openrouter_exa'
            if effective == PROVIDER_OPENROUTER_EXA and (external_used or external_error_kind)
            else ''
        ),
        'web_discovery_external_error_kind': str(external_error_kind or ''),
        'web_discovery_reason_codes': list(reason_codes or []),
    }


def plan_observability_fields(
    *,
    search_profile: str,
    requested_provider: str | None = None,
) -> dict[str, Any]:
    requested = _normalized_provider(requested_provider or configured_provider())
    effective = effective_provider(requested_provider=requested, search_profile=search_profile)
    reason_codes = [f'discovery_provider_{effective}']
    if requested != effective:
        reason_codes.append('explicit_url_forces_local_discovery')
    return empty_observability_fields(
        requested_provider=requested,
        effective_provider_value=effective,
        reason_codes=reason_codes,
    )


def merge_observability_fields(items: list[Mapping[str, Any]]) -> dict[str, Any]:
    if not items:
        return empty_observability_fields()
    first = dict(items[0])
    reason_codes: list[str] = []
    external_used = False
    external_error_kind = ''
    for item in items:
        for reason in item.get('web_discovery_reason_codes') or []:
            text = str(reason or '')
            if text and text not in reason_codes:
                reason_codes.append(text)
        external_used = external_used or bool(item.get('web_discovery_external_used', False))
        if not external_error_kind and item.get('web_discovery_external_error_kind'):
            external_error_kind = str(item.get('web_discovery_external_error_kind') or '')
    provider_effective = str(first.get('web_discovery_provider_effective') or first.get('web_discovery_provider') or PROVIDER_LOCAL)
    return {
        'web_discovery_provider': provider_effective,
        'web_discovery_provider_requested': str(first.get('web_discovery_provider_requested') or PROVIDER_LOCAL),
        'web_discovery_provider_effective': provider_effective,
        'web_discovery_external_used': bool(external_used),
        'web_discovery_external_provider': 'openrouter_exa' if external_used else '',
        'web_discovery_external_error_kind': external_error_kind,
        'web_discovery_reason_codes': reason_codes,
    }


def discover_urls(
    query: str,
    *,
    search_profile: str,
    searxng_params: dict[str, str] | None = None,
    max_results: int = 5,
    requested_provider: str | None = None,
    local_search: Callable[..., list[dict[str, str]]] | None = None,
    requests_module: Any = requests,
    llm_module: Any | None = None,
) -> DiscoveryResponse:
    requested = _normalized_provider(requested_provider or configured_provider())
    effective = effective_provider(requested_provider=requested, search_profile=search_profile)
    if effective == PROVIDER_OPENROUTER_EXA:
        return _discover_openrouter_exa(
            query,
            max_results=max_results,
            requested_provider=requested,
            requests_module=requests_module,
            llm_module=llm_module,
        )
    return _discover_local(
        query,
        searxng_params=searxng_params,
        max_results=max_results,
        requested_provider=requested,
        local_search=local_search,
    )


def _discover_local(
    query: str,
    *,
    searxng_params: dict[str, str] | None,
    max_results: int,
    requested_provider: str,
    local_search: Callable[..., list[dict[str, str]]] | None,
) -> DiscoveryResponse:
    if local_search is None:
        raise RuntimeError('local_search_callable_required')
    try:
        results = local_search(query, searxng_params=searxng_params)
    except TypeError:
        results = local_search(query)
    bounded_results = [
        _normalize_result(item, source_kind='searxng_result')
        for item in list(results or [])[:_safe_int(max_results, 5)]
    ]
    return DiscoveryResponse(
        results=bounded_results,
        observability=empty_observability_fields(
            requested_provider=requested_provider,
            effective_provider_value=PROVIDER_LOCAL,
            reason_codes=['local_searxng_discovery_used'],
        ),
    )


def _discover_openrouter_exa(
    query: str,
    *,
    max_results: int,
    requested_provider: str,
    requests_module: Any,
    llm_module: Any | None,
) -> DiscoveryResponse:
    try:
        if llm_module is None:
            from core import llm_client as llm_module

        result_limit = _safe_int(max_results, getattr(config, 'WEB_SEARCH_DISCOVERY_MAX_RESULTS', 5))
        max_total_results = min(
            result_limit,
            _safe_int(getattr(config, 'WEB_SEARCH_DISCOVERY_MAX_TOTAL_RESULTS', result_limit), result_limit),
        )
        payload = _build_openrouter_exa_payload(
            query,
            max_results=result_limit,
            max_total_results=max_total_results,
        )
        headers = _openrouter_headers(llm_module)
        response = requests_module.post(
            llm_module.or_chat_completions_url(),
            json=payload,
            headers=headers,
            timeout=_safe_int(getattr(config, 'WEB_SEARCH_DISCOVERY_TIMEOUT_S', 20), 20),
        )
        response.raise_for_status()
        payload_data = llm_module.read_openrouter_response_payload(response)
        results = _openrouter_sources(payload_data)[:result_limit]
        reason_codes = ['openrouter_exa_discovery_used', 'openrouter_web_search_server_tool']
        if not results:
            reason_codes.append('openrouter_exa_no_url_citations')
        return DiscoveryResponse(
            results=results,
            observability=empty_observability_fields(
                requested_provider=requested_provider,
                effective_provider_value=PROVIDER_OPENROUTER_EXA,
                external_used=True,
                reason_codes=reason_codes,
            ),
        )
    except Exception as exc:
        error_kind = _external_error_kind(exc)
        return DiscoveryResponse(
            results=[],
            observability=empty_observability_fields(
                requested_provider=requested_provider,
                effective_provider_value=PROVIDER_OPENROUTER_EXA,
                reason_codes=['openrouter_exa_discovery_failed', error_kind],
                external_error_kind=error_kind,
            ),
        )


def _openrouter_headers(llm_module: Any) -> dict[str, Any]:
    custom_headers = getattr(llm_module, 'or_headers_custom', None)
    if callable(custom_headers):
        return custom_headers(
            caller='web_discovery',
            referer=getattr(config, 'OR_REFERER_WEB_DISCOVERY', ''),
            title=getattr(config, 'OR_TITLE_WEB_DISCOVERY', 'FridaDev / Web Discovery'),
        )
    return llm_module.or_headers(caller='web_discovery')


def _build_openrouter_exa_payload(
    query: str,
    *,
    max_results: int,
    max_total_results: int,
) -> dict[str, Any]:
    model = str(getattr(config, 'WEB_SEARCH_DISCOVERY_MODEL', '') or getattr(config, 'OR_MODEL', '')).strip()
    search_context_size = str(
        getattr(config, 'WEB_SEARCH_DISCOVERY_SEARCH_CONTEXT_SIZE', 'low') or 'low'
    ).strip().lower()
    return {
        'model': model,
        'messages': [
            {
                'role': 'system',
                'content': (
                    'Tu es la couche de decouverte URL de FridaDev. '
                    'Utilise le server tool web_search pour trouver les URLs les plus pertinentes. '
                    'Ne fais pas de synthese longue: les pages seront lues ensuite localement par Crawl4AI.'
                ),
            },
            {
                'role': 'user',
                'content': (
                    'Recherche le web pour cette requete exacte et retourne les meilleures URLs citees. '
                    f'Requete: {str(query or "")}'
                ),
            },
        ],
        'tools': [
            {
                'type': OPENROUTER_SEARCH_TOOL_TYPE,
                'parameters': {
                    'engine': OPENROUTER_ENGINE_EXA,
                    'max_results': _safe_int(max_results, 5),
                    'max_total_results': _safe_int(max_total_results, _safe_int(max_results, 5)),
                    'search_context_size': search_context_size if search_context_size in {'low', 'medium', 'high'} else 'low',
                },
            }
        ],
        'temperature': 0,
        'top_p': 1.0,
        'max_tokens': 900,
        'metadata': {
            'frida_caller': 'web_discovery',
            'frida_slot': 'web_search_discovery',
            'web_discovery_provider': PROVIDER_OPENROUTER_EXA,
            'query_sha256_12': _sha256_12(str(query or '')),
        },
        'trace': {
            'trace_name': 'FridaDev',
            'generation_name': getattr(config, 'OR_TITLE_WEB_DISCOVERY', 'FridaDev / Web Discovery'),
        },
    }


def _openrouter_sources(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    message = _message(payload)
    sources: list[dict[str, str]] = []
    for annotation in message.get('annotations') or []:
        if not isinstance(annotation, Mapping):
            continue
        citation = annotation.get('url_citation') or annotation.get('citation') or {}
        if not isinstance(citation, Mapping):
            continue
        normalized = _normalize_result(
            {
                'title': str(citation.get('title') or ''),
                'url': str(citation.get('url') or citation.get('source_url') or ''),
                'content': str(citation.get('content') or citation.get('text') or ''),
            },
            source_kind='openrouter_url_citation',
        )
        if normalized.get('url'):
            sources.append(normalized)
    return _dedupe_results(sources)


def _message(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    try:
        message = payload['choices'][0]['message']  # type: ignore[index]
    except Exception:
        return {}
    return message if isinstance(message, Mapping) else {}


def _normalize_result(result: Mapping[str, Any], *, source_kind: str) -> dict[str, str]:
    url = str(result.get('url') or '').strip()
    return {
        'title': str(result.get('title') or '').strip(),
        'url': url,
        'content': str(result.get('content') or '').strip(),
        'discovery_source_kind': str(source_kind or ''),
        'discovery_domain': _domain(url),
    }


def _dedupe_results(results: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    deduped: list[dict[str, str]] = []
    for result in results:
        normalized = _normalized_url(result.get('url') or '')
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        deduped.append(result)
    return deduped


def _normalized_url(url: str) -> str:
    parsed = urlparse(str(url or '').strip())
    if not parsed.scheme or not parsed.netloc:
        return ''
    path = parsed.path.rstrip('/') or '/'
    return f'{parsed.scheme.lower()}://{parsed.netloc.lower()}{path}'


def _domain(url: str) -> str:
    parsed = urlparse(str(url or '').strip())
    return str(parsed.netloc or '').lower()


def _external_error_kind(exc: Exception) -> str:
    name = exc.__class__.__name__
    lowered = str(name or '').lower()
    if 'timeout' in lowered:
        return 'openrouter_timeout'
    if name in {'RuntimeError', 'KeyError', 'ValueError'}:
        return 'openrouter_config_error'
    if hasattr(exc, 'response'):
        return 'openrouter_http_error'
    return 'openrouter_request_error'
