#!/usr/bin/env python3
from __future__ import annotations

from typing import Any, Callable
from urllib.parse import urlparse

from core.web_read_state import (
    READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY,
    READ_STATE_PAGE_NOT_READ_ERROR,
    READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK,
    READ_STATE_PAGE_PARTIALLY_READ,
    READ_STATE_PAGE_READ,
)
from tools import (
    web_search_confidence,
    web_search_crawl_policy,
    web_search_evidence,
    web_search_profile,
    web_search_profile_policy,
    web_search_readers,
)


CRAWL4AI_FILTER_FIT = web_search_readers.CRAWL4AI_FILTER_FIT
WEB_PDF_CONTENT_KIND = "web_pdf_text"
WEB_SEARCH_SOURCE_ATTRIBUTION_LINE = (
    "Sources trouvées par Frida via la recherche web, non fournies par l'utilisateur."
)
WEB_SEARCH_FALLBACK_SOURCE_ATTRIBUTION_LINE = (
    "Sources de fallback trouvées par Frida via la recherche web, non fournies par l'utilisateur."
)


def source_domain(url: str) -> str | None:
    host = urlparse(str(url or "")).netloc.strip().lower()
    return host or None


def normalized_source_url(url: str) -> str:
    text = str(url or "").strip()
    if not text:
        return ""
    parsed = urlparse(text)
    if not parsed.scheme or not parsed.netloc:
        return text.rstrip("/")
    path = parsed.path or ""
    if path != "/":
        path = path.rstrip("/")
    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        path=path,
        fragment="",
    )
    return normalized.geturl()


def urls_match(left: str, right: str) -> bool:
    normalized_left = normalized_source_url(left)
    normalized_right = normalized_source_url(right)
    return bool(
        normalized_left
        and normalized_right
        and normalized_left == normalized_right
    )


def truncate_search_snippet(
    content: str,
    max_chars: int = 400,
) -> tuple[str, bool]:
    snippet = str(content or "")
    if len(snippet) <= max_chars:
        return snippet, False
    return snippet[:max_chars], True


def truncate_crawl_markdown(content: str, max_chars: int) -> tuple[str, bool]:
    markdown = str(content or "")
    if len(markdown) <= max_chars:
        return markdown, False
    return markdown[:max_chars] + "\n[...contenu tronqué]", True


def explicit_url_max_chars(runtime: dict[str, int | None]) -> int:
    explicit_budget = int(runtime.get("crawl4ai_explicit_url_max_chars") or 0)
    if explicit_budget > 0:
        return explicit_budget
    return int(runtime.get("crawl4ai_max_chars") or 0)


def web_pdf_source_fields(crawl_result: dict[str, Any]) -> dict[str, Any]:
    return {
        "web_pdf_read_attempted": bool(
            crawl_result.get("web_pdf_read_attempted", False)
        ),
        "web_pdf_read_detected": bool(
            crawl_result.get("web_pdf_read_detected", False)
        ),
        "web_pdf_read_status": str(crawl_result.get("web_pdf_read_status") or ""),
        "web_pdf_read_reason_code": str(
            crawl_result.get("web_pdf_read_reason_code") or ""
        ),
        "web_pdf_read_pages": int(crawl_result.get("web_pdf_read_pages") or 0),
        "web_pdf_read_bytes": int(crawl_result.get("web_pdf_read_bytes") or 0),
        "web_pdf_read_chars": int(crawl_result.get("web_pdf_read_chars") or 0),
        "web_pdf_read_elapsed_ms": int(
            crawl_result.get("web_pdf_read_elapsed_ms") or 0
        ),
        "web_pdf_read_truncated": bool(
            crawl_result.get("web_pdf_read_truncated", False)
        ),
        "web_pdf_read_error_class": str(
            crawl_result.get("web_pdf_read_error_class") or ""
        ),
    }


def build_explicit_url_context_material(
    url: str,
    crawled_markdown: str,
    *,
    crawl_result: dict[str, Any] | None = None,
    runtime: dict[str, int | None],
    today: str,
) -> dict[str, Any]:
    crawl4ai_max_chars = explicit_url_max_chars(runtime)
    content_used, truncated = truncate_crawl_markdown(
        crawled_markdown,
        crawl4ai_max_chars,
    )
    crawl_payload = dict(crawl_result or {})
    is_pdf_read = bool(crawl_payload.get("web_pdf_read_attempted", False))
    source = {
        "rank": 1,
        "title": "URL explicite utilisateur",
        "url": str(url or ""),
        "source_domain": source_domain(url),
        "search_snippet": "",
        "used_in_prompt": True,
        "used_content_kind": (
            WEB_PDF_CONTENT_KIND if is_pdf_read else "crawl_markdown"
        ),
        "content_used": content_used,
        "truncated": truncated,
        "source_origin": "explicit_url",
        "is_primary_source": True,
        "crawl_status": "success",
        "crawl_filter": str(
            crawl_payload.get("crawl_filter_used")
            or crawl_payload.get("filter")
            or CRAWL4AI_FILTER_FIT
        ),
        "crawl_filter_requested": str(
            crawl_payload.get("crawl_filter_requested")
            or crawl_payload.get("filter")
            or CRAWL4AI_FILTER_FIT
        ),
        "crawl_policy_kind": str(
            crawl_payload.get("crawl_policy_kind")
            or "explicit_url_direct_fit_then_raw"
        ),
        "crawl_policy_reason": str(
            crawl_payload.get("crawl_policy_reason")
            or "explicit_url_direct_success"
        ),
        "crawl_cache_mode": str(
            crawl_payload.get("crawl_cache_mode")
            or crawl_payload.get("cache_mode")
            or web_search_crawl_policy.CACHE_FRESH_WRITE
        ),
        "crawl_query_sha256_12": str(
            crawl_payload.get("crawl_query_sha256_12")
            or crawl_payload.get("query_sha256_12")
            or ""
        ),
        "crawl_query_chars": int(
            crawl_payload.get("crawl_query_chars")
            or crawl_payload.get("query_chars")
            or 0
        ),
        "crawl_fallback_used": bool(
            crawl_payload.get("crawl_fallback_used", False)
        ),
        "crawl_fallback_reason": str(
            crawl_payload.get("crawl_fallback_reason") or ""
        ),
        "crawl_primary_status": str(
            crawl_payload.get("crawl_primary_status") or "success"
        ),
        "crawl_fallback_status": str(
            crawl_payload.get("crawl_fallback_status") or ""
        ),
        "crawl_markdown_chars": len(str(crawled_markdown or "")),
        "crawl_max_chars": crawl4ai_max_chars,
        **web_pdf_source_fields(crawl_payload),
    }
    read_success_line = (
        "Lecture directe PDF prioritaire reussie sur cette URL."
        if is_pdf_read
        else "Lecture directe prioritaire reussie sur cette URL."
    )
    lines = [
        f"[RECHERCHE WEB — {today}]",
        f"URL explicite fournie par l'utilisateur : {url}",
        read_success_line,
        "",
        f"--- Source {source['rank']} : {source['title']}",
        f"URL : {source['url']}",
    ]
    if source["content_used"]:
        lines.append(str(source["content_used"]))
    lines.extend(("", "[FIN DES RÉSULTATS WEB]"))
    return {
        "runtime": dict(runtime),
        "results_count": 1,
        "sources": [source],
        "context_block": "\n".join(lines),
    }


def derive_read_state(
    *,
    explicit_url: str | None,
    primary_read_status: str,
    sources: list[dict[str, Any]],
) -> str | None:
    if not explicit_url:
        return None

    normalized_primary_status = str(primary_read_status or "not_attempted")
    primary_source = next(
        (source for source in sources if bool(source.get("is_primary_source"))),
        None,
    )
    if normalized_primary_status == "success":
        if primary_source and bool(primary_source.get("truncated")):
            return READ_STATE_PAGE_PARTIALLY_READ
        return READ_STATE_PAGE_READ

    if any(
        bool(source.get("used_in_prompt"))
        and str(source.get("used_content_kind") or "none") == "search_snippet"
        for source in sources
    ):
        return READ_STATE_PAGE_NOT_READ_SNIPPET_FALLBACK

    if normalized_primary_status == "empty":
        return READ_STATE_PAGE_NOT_READ_CRAWL_EMPTY

    return READ_STATE_PAGE_NOT_READ_ERROR


def _build_explicit_url_fallback_source(
    explicit_url: str,
    *,
    matching_result: dict[str, Any] | None,
    primary_read_status: str,
    crawl4ai_top_n: int,
    crawl4ai_max_chars: int,
    preloaded_crawl_results: dict[str, dict[str, Any]] | None,
    build_source_payload: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    base_result = dict(matching_result or {})
    base_result["title"] = str(
        base_result.get("title") or "URL explicite utilisateur"
    )
    base_result["url"] = str(explicit_url or "")
    source = build_source_payload(
        1,
        base_result,
        crawl4ai_top_n=crawl4ai_top_n,
        crawl4ai_max_chars=crawl4ai_max_chars,
        preloaded_crawl_results=preloaded_crawl_results,
        source_origin="explicit_url",
        is_primary_source=True,
        search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
        primary_query="",
    )
    source["title"] = str(
        base_result.get("title") or "URL explicite utilisateur"
    )
    source["url"] = str(explicit_url or "")
    source["source_domain"] = source_domain(explicit_url)
    source["source_origin"] = "explicit_url"
    source["is_primary_source"] = True
    source["crawl_status"] = str(
        primary_read_status or source.get("crawl_status") or "not_attempted"
    )
    return source


def build_search_context_material(
    query: str,
    results: list[dict[str, Any]],
    *,
    runtime: dict[str, int | None],
    today: str,
    build_source_payload: Callable[..., dict[str, Any]],
    explicit_url: str | None = None,
    primary_read_status: str = "not_attempted",
    preloaded_crawl_results: dict[str, dict[str, Any]] | None = None,
    search_profile: str = web_search_profile.PROFILE_GENERAL,
    enable_profiled_crawl4ai_policy: bool = True,
) -> dict[str, Any]:
    crawl4ai_top_n = web_search_profile_policy.effective_crawl_top_n(
        search_profile,
        int(runtime.get("crawl4ai_top_n") or 0),
    )
    crawl4ai_max_chars = web_search_profile_policy.effective_crawl_max_chars(
        search_profile,
        int(runtime.get("crawl4ai_max_chars") or 0),
    )
    effective_runtime = dict(runtime)
    effective_runtime["crawl4ai_effective_top_n"] = crawl4ai_top_n
    effective_runtime["crawl4ai_effective_max_chars"] = crawl4ai_max_chars
    primary_source: dict[str, Any] | None = None
    fallback_results = list(results or [])

    if explicit_url:
        matching_result: dict[str, Any] | None = None
        deduped_results: list[dict[str, Any]] = []
        for result in fallback_results:
            result_url = str(result.get("url") or "")
            if matching_result is None and urls_match(result_url, explicit_url):
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
            build_source_payload=build_source_payload,
        )
        fallback_results = deduped_results

    primary_source_has_content = bool(
        primary_source
        and str(primary_source.get("used_content_kind") or "none") != "none"
    )

    if not fallback_results and not primary_source:
        return {
            "runtime": effective_runtime,
            "results_count": 0,
            "sources": [],
            "context_block": "",
        }

    if (
        explicit_url
        and not fallback_results
        and primary_source
        and not primary_source_has_content
    ):
        return {
            "runtime": effective_runtime,
            "results_count": 0,
            "sources": [primary_source],
            "context_block": "",
        }

    search_sources = [
        build_source_payload(
            index,
            result,
            crawl4ai_top_n=crawl4ai_top_n,
            crawl4ai_max_chars=crawl4ai_max_chars,
            preloaded_crawl_results=preloaded_crawl_results,
            search_profile=search_profile,
            primary_query=query,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
        )
        for index, result in enumerate(
            fallback_results,
            2 if primary_source else 1,
        )
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
                WEB_SEARCH_FALLBACK_SOURCE_ATTRIBUTION_LINE,
                "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
                "",
            ]
        )
    else:
        lines.extend(
            [
                f"J'ai effectué une recherche pour : « {query} ».",
                WEB_SEARCH_SOURCE_ATTRIBUTION_LINE,
                "Voici ce que j'ai trouvé — je l'utilise pour répondre.",
                "",
            ]
        )
    for source in sources:
        lines.append(f"--- Source {source['rank']} : {source['title']}")
        lines.append(f"URL : {source['url']}")
        if source["content_used"]:
            lines.append(str(source["content_used"]))
        lines.append("")
    lines.append("[FIN DES RÉSULTATS WEB]")
    return {
        "runtime": effective_runtime,
        "results_count": len(sources),
        "sources": sources,
        "context_block": "\n".join(lines),
    }


def web_search_payload_status(
    *,
    has_results: bool,
    query_plan: dict[str, Any] | None,
    local_error_reason_code: str,
    discovery_error_reason_code: str,
) -> tuple[str, str | None, str]:
    if has_results:
        return "ok", None, ""
    plan = dict(query_plan or {})
    if int(plan.get("local_search_error_count") or 0) > 0:
        return (
            "error",
            local_error_reason_code,
            str(plan.get("local_search_error_class") or ""),
        )
    reason_codes = {
        str(value or "")
        for value in plan.get("web_discovery_reason_codes") or []
    }
    if (
        bool(str(plan.get("web_discovery_external_error_kind") or ""))
        and "openrouter_exa_discovery_failed" in reason_codes
    ):
        return "error", discovery_error_reason_code, "WebDiscoveryUpstreamError"
    return "skipped", "no_data", ""


def augment_payload_evidence(payload: dict[str, Any]) -> dict[str, Any]:
    payload.update(
        web_search_profile_policy.evaluate_profile_evidence(
            str(
                payload.get("search_profile")
                or web_search_profile.PROFILE_GENERAL
            ),
            sources=list(payload.get("sources") or []),
            policy_fields=payload,
        )
    )
    payload.update(web_search_confidence.evaluate_web_confidence(payload))
    payload.update(web_search_evidence.evaluate_web_evidence(payload))
    return payload
