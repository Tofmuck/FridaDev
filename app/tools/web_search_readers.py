#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import inspect
import logging
from typing import Any, Callable
from urllib.parse import urlparse

import requests

from tools import web_pdf_reader, web_public_url_policy, web_search_crawl_policy


logger = logging.getLogger("frida.web_search")

CRAWL4AI_FILTER_FIT = "fit"
CRAWL4AI_FILTER_RAW = "raw"
CRAWL4AI_TIMEOUT_S = 20


def build_crawl4ai_md_payload(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = "0",
) -> dict[str, str]:
    payload = {
        "url": str(url or ""),
        "f": str(filter_type or CRAWL4AI_FILTER_FIT),
        "c": str(cache_mode or "0"),
    }
    if query:
        payload["q"] = str(query)
    return payload


def crawl_markdown_with_status(
    url: str,
    *,
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
    runtime_service_value: Callable[[str], Any],
    runtime_token: Callable[[], str],
    requests_module: Any = requests,
    payload_builder: Callable[..., dict[str, str]] = build_crawl4ai_md_payload,
    blocked_url_reason: Callable[[str], str] = web_public_url_policy.blocked_url_reason,
) -> dict[str, Any]:
    """Read one public URL through Crawl4AI and normalize its status."""
    normalized_query = str(query or "").strip()
    normalized_filter = str(filter_type or CRAWL4AI_FILTER_FIT)
    normalized_cache_mode = str(cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE)
    blocked_reason = blocked_url_reason(url)
    if blocked_reason:
        return {
            "status": "error",
            "markdown": "",
            "error_class": "crawl_url_blocked",
            "reason_code": blocked_reason,
            "filter": normalized_filter,
            "cache_mode": normalized_cache_mode,
            "query_sha256_12": _sha256_12(normalized_query),
            "query_chars": _safe_len(normalized_query),
        }

    try:
        crawl4ai_url = str(runtime_service_value("crawl4ai_url")).rstrip("/")
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {runtime_token()}",
        }
        payload = payload_builder(
            url,
            filter_type=normalized_filter,
            query=normalized_query or None,
            cache_mode=normalized_cache_mode,
        )
        response = requests_module.post(
            f"{crawl4ai_url}/md",
            json=payload,
            headers=headers,
            timeout=CRAWL4AI_TIMEOUT_S,
        )
        response.raise_for_status()
        data = response.json()
        actual_filter = str(data.get("filter") or filter_type or CRAWL4AI_FILTER_FIT)
        if not data.get("success"):
            return {
                "status": "error",
                "markdown": "",
                "error_class": "crawl_unsuccessful",
                "filter": actual_filter,
                "cache_mode": normalized_cache_mode,
                "query_sha256_12": _sha256_12(normalized_query),
                "query_chars": _safe_len(normalized_query),
            }
        markdown = str(data.get("markdown") or "").strip()
        if not markdown:
            return {
                "status": "empty",
                "markdown": "",
                "error_class": None,
                "filter": actual_filter,
                "cache_mode": normalized_cache_mode,
                "query_sha256_12": _sha256_12(normalized_query),
                "query_chars": _safe_len(normalized_query),
            }
        return {
            "status": "success",
            "markdown": markdown,
            "error_class": None,
            "filter": actual_filter,
            "cache_mode": normalized_cache_mode,
            "query_sha256_12": _sha256_12(normalized_query),
            "query_chars": _safe_len(normalized_query),
        }
    except Exception as exc:
        url_fields = _url_log_fields(url)
        logger.warning(
            (
                "crawl_error reason=crawl_exception filter=%s url_scheme=%s "
                "url_host_sha256_12=%s url_chars=%s url_query_present=%s "
                "url_fragment_present=%s err_class=%s"
            ),
            normalized_filter,
            url_fields["url_scheme"],
            url_fields["url_host_sha256_12"],
            url_fields["url_chars"],
            url_fields["url_query_present"],
            url_fields["url_fragment_present"],
            exc.__class__.__name__,
        )
        return {
            "status": "error",
            "markdown": "",
            "error_class": exc.__class__.__name__,
            "filter": normalized_filter,
            "cache_mode": normalized_cache_mode,
            "query_sha256_12": _sha256_12(normalized_query),
            "query_chars": _safe_len(normalized_query),
        }


def call_crawl_markdown_with_status(
    url: str,
    *,
    crawl_func: Callable[..., dict[str, Any]],
    filter_type: str = CRAWL4AI_FILTER_FIT,
    query: str | None = None,
    cache_mode: str = web_search_crawl_policy.CACHE_FRESH_WRITE,
) -> dict[str, Any]:
    """Call the injectable Crawl4AI facade while preserving older test seams."""
    try:
        signature = inspect.signature(crawl_func)
        params = signature.parameters
        supports_kwargs = any(
            parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in params.values()
        )
        kwargs: dict[str, Any] = {"filter_type": filter_type}
        if supports_kwargs or "query" in params:
            kwargs["query"] = query
        if supports_kwargs or "cache_mode" in params:
            kwargs["cache_mode"] = cache_mode
        result = crawl_func(url, **kwargs)
    except (TypeError, ValueError):
        result = crawl_func(url, filter_type=filter_type, query=query)
    normalized = dict(result or {})
    normalized.setdefault("filter", str(filter_type or CRAWL4AI_FILTER_FIT))
    normalized.setdefault(
        "cache_mode",
        str(cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE),
    )
    normalized.setdefault("query_sha256_12", _sha256_12(query))
    normalized.setdefault("query_chars", _safe_len(query))
    return normalized


def read_explicit_url_with_status(
    url: str,
    *,
    crawl_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    """Read an explicit URL with fit first and raw only after an empty fit."""
    fit_result = call_crawl_markdown_with_status(
        url,
        crawl_func=crawl_func,
        filter_type=CRAWL4AI_FILTER_FIT,
    )
    fit_result["raw_fallback_used"] = False
    fit_result["crawl_policy_kind"] = "explicit_url_direct_fit_then_raw"
    fit_result["crawl_policy_reason"] = str(
        fit_result.get("reason_code") or "explicit_url_fit_primary"
    )
    fit_result["crawl_filter_requested"] = CRAWL4AI_FILTER_FIT
    fit_result["crawl_primary_filter"] = CRAWL4AI_FILTER_FIT
    fit_result["crawl_fallback_filter"] = CRAWL4AI_FILTER_RAW
    fit_result["crawl_fallback_used"] = False
    fit_result["crawl_fallback_reason"] = ""
    fit_result["crawl_primary_status"] = str(fit_result.get("status") or "")
    fit_result["crawl_fallback_status"] = ""
    if str(fit_result.get("status") or "") != "empty":
        return fit_result

    raw_result = call_crawl_markdown_with_status(
        url,
        crawl_func=crawl_func,
        filter_type=CRAWL4AI_FILTER_RAW,
    )
    raw_result["raw_fallback_used"] = True
    raw_result["crawl_policy_kind"] = "explicit_url_direct_fit_then_raw"
    raw_result["crawl_policy_reason"] = "explicit_url_raw_only_after_empty_fit"
    raw_result["crawl_filter_requested"] = CRAWL4AI_FILTER_RAW
    raw_result["crawl_primary_filter"] = CRAWL4AI_FILTER_FIT
    raw_result["crawl_fallback_filter"] = CRAWL4AI_FILTER_RAW
    raw_result["crawl_fallback_used"] = True
    raw_result["crawl_fallback_reason"] = "fit_empty_raw_fallback"
    raw_result["crawl_primary_status"] = str(fit_result.get("status") or "")
    raw_result["crawl_fallback_status"] = str(raw_result.get("status") or "")
    return raw_result


def annotate_crawl_result(
    crawl_result: dict[str, Any],
    *,
    policy: web_search_crawl_policy.Crawl4AIExtractionPolicy,
    requested_filter: str,
    used_filter: str | None = None,
    fallback_used: bool = False,
    fallback_reason: str = "",
    primary_status: str = "",
    fallback_status: str = "",
) -> dict[str, Any]:
    result = dict(crawl_result or {})
    query = str(policy.query or "")
    result["crawl_policy_kind"] = str(policy.kind or "")
    result["crawl_policy_reason"] = str(
        result.get("reason_code") or policy.reason_code or ""
    )
    result["crawl_filter_requested"] = str(
        requested_filter or policy.primary_filter or CRAWL4AI_FILTER_FIT
    )
    result["crawl_primary_filter"] = str(
        policy.primary_filter or CRAWL4AI_FILTER_FIT
    )
    result["crawl_fallback_filter"] = str(policy.fallback_filter or "")
    result["crawl_filter_used"] = str(
        used_filter
        or result.get("filter")
        or requested_filter
        or CRAWL4AI_FILTER_FIT
    )
    result["crawl_cache_mode"] = str(
        policy.cache_mode or web_search_crawl_policy.CACHE_FRESH_WRITE
    )
    result["crawl_query_sha256_12"] = _sha256_12(query)
    result["crawl_query_chars"] = _safe_len(query)
    result["crawl_fallback_used"] = bool(fallback_used)
    result["crawl_fallback_reason"] = str(fallback_reason or "")
    result["crawl_primary_status"] = str(
        primary_status or result.get("status") or ""
    )
    result["crawl_fallback_status"] = str(fallback_status or "")
    result["crawl_markdown_chars"] = len(str(result.get("markdown") or ""))
    result["crawl_max_chars"] = int(policy.max_chars or 0)
    return result


def read_search_result_with_policy(
    url: str,
    policy: web_search_crawl_policy.Crawl4AIExtractionPolicy,
    *,
    crawl_func: Callable[..., dict[str, Any]],
) -> dict[str, Any]:
    primary = call_crawl_markdown_with_status(
        url,
        crawl_func=crawl_func,
        filter_type=policy.primary_filter,
        query=policy.query or None,
        cache_mode=policy.cache_mode,
    )
    should_fallback, fallback_reason = web_search_crawl_policy.should_fallback_from_primary(
        policy,
        primary,
    )
    primary_status = str(primary.get("status") or "")
    if not should_fallback:
        return annotate_crawl_result(
            primary,
            policy=policy,
            requested_filter=policy.primary_filter,
            used_filter=str(primary.get("filter") or policy.primary_filter),
            primary_status=primary_status,
        )

    fallback = call_crawl_markdown_with_status(
        url,
        crawl_func=crawl_func,
        filter_type=policy.fallback_filter,
        query=None,
        cache_mode=policy.cache_mode,
    )
    fallback_status = str(fallback.get("status") or "")
    fallback_markdown = str(fallback.get("markdown") or "")
    selected = fallback if fallback_markdown else primary
    selected_filter = str(
        selected.get("filter")
        or policy.fallback_filter
        or policy.primary_filter
    )
    selected_is_fallback = selected is fallback
    return annotate_crawl_result(
        selected,
        policy=policy,
        requested_filter=policy.primary_filter,
        used_filter=selected_filter,
        fallback_used=selected_is_fallback,
        fallback_reason=fallback_reason,
        primary_status=primary_status,
        fallback_status=fallback_status,
    )


def read_pdf_as_crawl_result(
    url: str,
    *,
    max_chars: int,
    probe_content_type: bool,
    pdf_reader_module: Any = web_pdf_reader,
) -> dict[str, Any] | None:
    """Adapt the bounded PDF reader result to the existing crawl result shape."""
    effective_max_chars = int(
        max_chars or pdf_reader_module.DEFAULT_MAX_CHARS
    )
    result = pdf_reader_module.read_pdf_url(
        url,
        max_chars=effective_max_chars,
        probe_content_type=probe_content_type,
    )
    if not result.detected:
        return None
    crawl_result = result.to_crawl_like_result()
    crawl_result["crawl_max_chars"] = effective_max_chars
    return crawl_result


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _safe_len(value: Any) -> int:
    return len(str(value or ""))


def _url_log_fields(value: Any) -> dict[str, Any]:
    text = str(value or "")
    parsed = urlparse(text)
    host = str(parsed.netloc or "").strip().lower()
    return {
        "url_scheme": str(parsed.scheme or ""),
        "url_host_sha256_12": _sha256_12(host),
        "url_chars": len(text),
        "url_query_present": bool(parsed.query),
        "url_fragment_present": bool(parsed.fragment),
    }
