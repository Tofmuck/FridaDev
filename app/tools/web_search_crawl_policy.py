from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tools import web_search_profile


CRAWL4AI_FILTER_FIT = 'fit'
CRAWL4AI_FILTER_RAW = 'raw'
CRAWL4AI_FILTER_BM25 = 'bm25'

CACHE_FRESH_WRITE = '0'
CACHE_ENABLED = '1'

BM25_MIN_MARKDOWN_CHARS = 120

BM25_SEARCH_PROFILES = {
    web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
    web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
    web_search_profile.PROFILE_ACADEMIQUE,
}

PROFILE_MAX_CHARS = {
    web_search_profile.PROFILE_ACTUALITE: 4500,
    web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE: 7000,
    web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS: 6500,
    web_search_profile.PROFILE_ACADEMIQUE: 8000,
    web_search_profile.PROFILE_GENERAL: 5000,
    web_search_profile.PROFILE_EXPLICIT_URL: 5000,
}


@dataclass(frozen=True)
class Crawl4AIExtractionPolicy:
    kind: str
    reason_code: str
    primary_filter: str = CRAWL4AI_FILTER_FIT
    fallback_filter: str = ''
    query: str = ''
    cache_mode: str = CACHE_FRESH_WRITE
    max_chars: int = 0

    def query_hash_fields(self, sha256_12: str, query_chars: int) -> dict[str, Any]:
        return {
            'crawl_query_sha256_12': str(sha256_12 or ''),
            'crawl_query_chars': int(query_chars or 0),
        }


def effective_max_chars(search_profile: str, runtime_max_chars: int | None) -> int:
    try:
        base = int(runtime_max_chars or 0)
    except (TypeError, ValueError):
        base = 0
    if base <= 0:
        return base
    cap = PROFILE_MAX_CHARS.get(str(search_profile or ''), PROFILE_MAX_CHARS[web_search_profile.PROFILE_GENERAL])
    return min(base, int(cap))


def build_search_result_policy(
    search_profile: str,
    *,
    primary_query: str,
    runtime_max_chars: int | None,
) -> Crawl4AIExtractionPolicy:
    profile = str(search_profile or web_search_profile.PROFILE_GENERAL)
    query = str(primary_query or '').strip()
    max_chars = effective_max_chars(profile, runtime_max_chars)
    if profile in BM25_SEARCH_PROFILES and query:
        return Crawl4AIExtractionPolicy(
            kind='profile_query_aware_bm25_with_fit_fallback',
            reason_code='profile_query_aware_long_page_candidate',
            primary_filter=CRAWL4AI_FILTER_BM25,
            fallback_filter=CRAWL4AI_FILTER_FIT,
            query=query,
            cache_mode=CACHE_ENABLED,
            max_chars=max_chars,
        )
    if profile == web_search_profile.PROFILE_ACTUALITE:
        return Crawl4AIExtractionPolicy(
            kind='profile_fit_fresh',
            reason_code='actualite_fresh_fit_default',
            primary_filter=CRAWL4AI_FILTER_FIT,
            cache_mode=CACHE_FRESH_WRITE,
            max_chars=max_chars,
        )
    if profile == web_search_profile.PROFILE_EXPLICIT_URL:
        return Crawl4AIExtractionPolicy(
            kind='explicit_url_fallback_search_fit',
            reason_code='explicit_url_fallback_search_no_raw',
            primary_filter=CRAWL4AI_FILTER_FIT,
            cache_mode=CACHE_FRESH_WRITE,
            max_chars=max_chars,
        )
    return Crawl4AIExtractionPolicy(
        kind='historical_fit',
        reason_code='general_fit_default',
        primary_filter=CRAWL4AI_FILTER_FIT,
        cache_mode=CACHE_FRESH_WRITE,
        max_chars=max_chars,
    )


def should_fallback_from_primary(
    policy: Crawl4AIExtractionPolicy,
    crawl_result: dict[str, Any],
) -> tuple[bool, str]:
    if policy.primary_filter != CRAWL4AI_FILTER_BM25 or not policy.fallback_filter:
        return False, ''
    status = str(crawl_result.get('status') or '')
    markdown = str(crawl_result.get('markdown') or '').strip()
    if status != 'success':
        return True, 'bm25_not_success_fit_fallback'
    if len(markdown) < BM25_MIN_MARKDOWN_CHARS:
        return True, 'bm25_poor_fit_fallback'
    return False, ''


def is_historical_fit(policy: Crawl4AIExtractionPolicy) -> bool:
    return (
        policy.primary_filter == CRAWL4AI_FILTER_FIT
        and not policy.fallback_filter
        and not policy.query
        and policy.cache_mode == CACHE_FRESH_WRITE
    )
