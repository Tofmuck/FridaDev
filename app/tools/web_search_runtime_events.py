#!/usr/bin/env python3
from __future__ import annotations

import hashlib
from typing import Any

from observability import chat_turn_logger
from tools import (
    web_search_confidence,
    web_search_context,
    web_search_evidence,
    web_search_profile_policy,
)


def _sha256_12(value: Any) -> str:
    text = str(value or "")
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


def _source_content_chars(source: dict[str, Any]) -> int:
    return len(str(source.get("content_used") or ""))


def build_source_material_summary(
    sources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for source in sources or []:
        try:
            rank = int(source.get("rank") or 0)
        except (TypeError, ValueError):
            rank = 0
        summary.append(
            {
                "rank": rank,
                "url": str(source.get("url") or ""),
                "source_origin": str(
                    source.get("source_origin") or "search_result"
                ),
                "is_primary_source": bool(
                    source.get("is_primary_source", False)
                ),
                "used_in_prompt": bool(source.get("used_in_prompt", False)),
                "used_content_kind": str(
                    source.get("used_content_kind") or "none"
                ),
                "crawl_status": str(
                    source.get("crawl_status") or "not_attempted"
                ),
                "content_chars": _source_content_chars(source),
                "truncated": bool(source.get("truncated", False)),
            }
        )
    return summary


def build_crawl4ai_extraction_summary(
    sources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for source in sources or []:
        try:
            rank = int(source.get("rank") or 0)
        except (TypeError, ValueError):
            rank = 0
        summary.append(
            {
                "rank": rank,
                "url": str(source.get("url") or ""),
                "source_origin": str(
                    source.get("source_origin") or "search_result"
                ),
                "is_primary_source": bool(
                    source.get("is_primary_source", False)
                ),
                "crawl_status": str(
                    source.get("crawl_status") or "not_attempted"
                ),
                "crawl_filter": str(source.get("crawl_filter") or ""),
                "crawl_filter_requested": str(
                    source.get("crawl_filter_requested") or ""
                ),
                "crawl_policy_kind": str(
                    source.get("crawl_policy_kind") or ""
                ),
                "crawl_policy_reason": str(
                    source.get("crawl_policy_reason") or ""
                ),
                "crawl_cache_mode": str(
                    source.get("crawl_cache_mode") or ""
                ),
                "crawl_query_sha256_12": str(
                    source.get("crawl_query_sha256_12") or ""
                ),
                "crawl_query_chars": int(
                    source.get("crawl_query_chars") or 0
                ),
                "crawl_fallback_used": bool(
                    source.get("crawl_fallback_used", False)
                ),
                "crawl_fallback_reason": str(
                    source.get("crawl_fallback_reason") or ""
                ),
                "crawl_primary_status": str(
                    source.get("crawl_primary_status") or ""
                ),
                "crawl_fallback_status": str(
                    source.get("crawl_fallback_status") or ""
                ),
                "crawl_markdown_chars": int(
                    source.get("crawl_markdown_chars") or 0
                ),
                "crawl_max_chars": int(source.get("crawl_max_chars") or 0),
                "used_content_kind": str(
                    source.get("used_content_kind") or "none"
                ),
                "content_chars": _source_content_chars(source),
                "truncated": bool(source.get("truncated", False)),
            }
        )
    return summary


def build_web_pdf_read_summary(
    sources: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for source in sources or []:
        if not bool(source.get("web_pdf_read_attempted", False)):
            continue
        try:
            rank = int(source.get("rank") or 0)
        except (TypeError, ValueError):
            rank = 0
        source_url = str(source.get("url") or "")
        summary.append(
            {
                "rank": rank,
                "url_sha256_12": _sha256_12(source_url),
                "source_domain": web_search_context.source_domain(source_url)
                or "",
                "source_origin": str(
                    source.get("source_origin") or "search_result"
                ),
                "is_primary_source": bool(
                    source.get("is_primary_source", False)
                ),
                "web_pdf_read_status": str(
                    source.get("web_pdf_read_status") or ""
                ),
                "web_pdf_read_reason_code": str(
                    source.get("web_pdf_read_reason_code") or ""
                ),
                "web_pdf_read_pages": int(
                    source.get("web_pdf_read_pages") or 0
                ),
                "web_pdf_read_bytes": int(
                    source.get("web_pdf_read_bytes") or 0
                ),
                "web_pdf_read_chars": int(
                    source.get("web_pdf_read_chars") or 0
                ),
                "web_pdf_read_elapsed_ms": int(
                    source.get("web_pdf_read_elapsed_ms") or 0
                ),
                "web_pdf_read_truncated": bool(
                    source.get("web_pdf_read_truncated", False)
                ),
                "used_in_prompt": bool(source.get("used_in_prompt", False)),
                "used_content_kind": str(
                    source.get("used_content_kind") or "none"
                ),
            }
        )
    return summary


def _redact_observability_url(item: dict[str, Any]) -> dict[str, Any]:
    result = dict(item)
    source_url = str(result.pop("url", "") or "")
    result["source_domain"] = str(
        result.get("source_domain")
        or web_search_context.source_domain(source_url)
        or ""
    )
    result["url_present"] = bool(source_url)
    result["url_chars"] = len(source_url)
    result["url_included"] = False
    return result


def event_source_material_summary(
    summary: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    return [_redact_observability_url(dict(item)) for item in summary or []]


def event_crawl4ai_extraction_summary(
    summary: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    for item in summary or []:
        event_item = _redact_observability_url(dict(item))
        crawl_query_hash_present = bool(
            str(event_item.pop("crawl_query_sha256_12", "") or "").strip()
        )
        event_item["crawl_query_hash_present"] = crawl_query_hash_present
        event_item["crawl_query_hash_included"] = False
        redacted.append(event_item)
    return redacted


def event_web_pdf_read_summary(
    summary: list[dict[str, Any]] | None,
) -> list[dict[str, Any]]:
    redacted: list[dict[str, Any]] = []
    for item in summary or []:
        event_item = dict(item)
        url_fingerprint_present = bool(
            str(event_item.pop("url_sha256_12", "") or "").strip()
        )
        event_item["url_fingerprint_present"] = url_fingerprint_present
        event_item["url_fingerprint_included"] = False
        redacted.append(event_item)
    return redacted


def count_web_pdf_statuses(
    web_pdf_summary: list[dict[str, Any]] | None,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in web_pdf_summary or []:
        status = str(item.get("web_pdf_read_status") or "").strip()
        if status:
            counts[status] = counts.get(status, 0) + 1
    return dict(sorted(counts.items()))


def web_pdf_reason_codes(
    web_pdf_summary: list[dict[str, Any]] | None,
) -> list[str]:
    codes: list[str] = []
    for item in web_pdf_summary or []:
        code = str(item.get("web_pdf_read_reason_code") or "").strip()
        if code and code not in codes:
            codes.append(code)
    return codes


def derive_used_content_kinds(
    source_material_summary: list[dict[str, Any]] | None,
) -> list[str]:
    kinds: list[str] = []
    for source in source_material_summary or []:
        if not bool(source.get("used_in_prompt", False)):
            continue
        kind = str(source.get("used_content_kind") or "none")
        if kind != "none" and kind not in kinds:
            kinds.append(kind)
    return kinds


def derive_injected_chars(
    source_material_summary: list[dict[str, Any]] | None,
) -> int:
    total = 0
    for source in source_material_summary or []:
        if not bool(source.get("used_in_prompt", False)):
            continue
        try:
            total += int(source.get("content_chars") or 0)
        except (TypeError, ValueError):
            continue
    return total


def count_crawl4ai_extraction_field(
    crawl4ai_extraction_summary: list[dict[str, Any]] | None,
    field: str,
) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get(field) or "").strip()
        if value:
            counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _derive_crawl4ai_policy_kinds(
    crawl4ai_extraction_summary: list[dict[str, Any]] | None,
) -> list[str]:
    kinds: list[str] = []
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get("crawl_policy_kind") or "").strip()
        if value and value not in kinds:
            kinds.append(value)
    return kinds


def crawl4ai_query_hashes(
    crawl4ai_extraction_summary: list[dict[str, Any]] | None,
) -> list[str]:
    hashes: list[str] = []
    for item in crawl4ai_extraction_summary or []:
        value = str(item.get("crawl_query_sha256_12") or "").strip()
        if value and value not in hashes:
            hashes.append(value)
    return hashes


def augment_payload_observability(payload: dict[str, Any]) -> dict[str, Any]:
    sources = list(payload.get("sources") or [])
    source_material_summary = build_source_material_summary(sources)
    crawl4ai_extraction_summary = build_crawl4ai_extraction_summary(sources)
    web_pdf_read_summary = build_web_pdf_read_summary(sources)
    payload["source_material_summary"] = source_material_summary
    payload["crawl4ai_extraction_summary"] = crawl4ai_extraction_summary
    payload["web_pdf_read_summary"] = web_pdf_read_summary
    payload["web_pdf_read_attempted_count"] = len(web_pdf_read_summary)
    payload["web_pdf_read_status_counts"] = count_web_pdf_statuses(
        web_pdf_read_summary
    )
    payload["web_pdf_read_reason_codes"] = web_pdf_reason_codes(
        web_pdf_read_summary
    )
    payload["crawl4ai_policy_kinds"] = _derive_crawl4ai_policy_kinds(
        crawl4ai_extraction_summary
    )
    payload["crawl4ai_filter_counts"] = count_crawl4ai_extraction_field(
        crawl4ai_extraction_summary,
        "crawl_filter",
    )
    payload["crawl4ai_cache_modes"] = count_crawl4ai_extraction_field(
        crawl4ai_extraction_summary,
        "crawl_cache_mode",
    )
    payload["crawl4ai_fallback_used_count"] = sum(
        1
        for item in crawl4ai_extraction_summary
        if bool(item.get("crawl_fallback_used", False))
    )
    payload["crawl4ai_query_sha256_12"] = crawl4ai_query_hashes(
        crawl4ai_extraction_summary
    )
    payload["used_content_kinds"] = derive_used_content_kinds(
        source_material_summary
    )
    payload["injected_chars"] = derive_injected_chars(source_material_summary)
    payload["context_chars"] = len(str(payload.get("context_block") or ""))
    return web_search_context.augment_payload_evidence(payload)


def web_confidence_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "web_confidence_policy_kind": str(
            payload.get("web_confidence_policy_kind") or ""
        ),
        "web_confidence_level": str(
            payload.get("web_confidence_level") or "unknown"
        ),
        "web_confidence_score": float(payload.get("web_confidence_score") or 0.0),
        "web_confidence_reason_codes": list(
            payload.get("web_confidence_reason_codes") or []
        ),
        "web_confidence_inputs_summary": dict(
            payload.get("web_confidence_inputs_summary") or {}
        ),
        "openrouter_fallback_state": str(
            payload.get("openrouter_fallback_state") or "future_only"
        ),
        "openrouter_fallback_used": bool(
            payload.get("openrouter_fallback_used", False)
        ),
        "openrouter_fallback_reason_codes": list(
            payload.get("openrouter_fallback_reason_codes") or []
        ),
    }


def web_evidence_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "web_evidence_policy_kind": str(
            payload.get("web_evidence_policy_kind") or ""
        ),
        "web_evidence_status": str(
            payload.get("web_evidence_status") or "not_applicable"
        ),
        "web_evidence_reason_codes": list(
            payload.get("web_evidence_reason_codes") or []
        ),
        "web_evidence_guidance_codes": list(
            payload.get("web_evidence_guidance_codes") or []
        ),
        "web_evidence_inputs_summary": dict(
            payload.get("web_evidence_inputs_summary") or {}
        ),
        "web_evidence_can_answer": bool(
            payload.get("web_evidence_can_answer", False)
        ),
        "web_evidence_requires_caveat": bool(
            payload.get("web_evidence_requires_caveat", False)
        ),
        "web_evidence_can_suggest_reformulation": bool(
            payload.get("web_evidence_can_suggest_reformulation", False)
        ),
        "web_evidence_url_request_policy": str(
            payload.get("web_evidence_url_request_policy") or ""
        ),
        "web_evidence_external_fallback_used": bool(
            payload.get("web_evidence_external_fallback_used", False)
        ),
    }


def profile_policy_event_fields(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "profile_policy_kind": str(payload.get("profile_policy_kind") or "none"),
        "profile_policy_mode": str(payload.get("profile_policy_mode") or "none"),
        "profile_expected_domains": list(payload.get("profile_expected_domains") or []),
        "profile_secondary_domains": list(payload.get("profile_secondary_domains") or []),
        "profile_downrank_domains": list(payload.get("profile_downrank_domains") or []),
        "profile_situated_secondary_domains": list(
            payload.get("profile_situated_secondary_domains") or []
        ),
        "profile_policy_reason_codes": list(
            payload.get("profile_policy_reason_codes") or []
        ),
        "profile_crawl_top_n_budget": int(payload.get("profile_crawl_top_n_budget") or 0),
        "profile_crawl_max_chars_budget": int(payload.get("profile_crawl_max_chars_budget") or 0),
        "profile_manual_latency_target_s": int(
            payload.get("profile_manual_latency_target_s") or 0
        ),
        "profile_source_evidence_policy_kind": str(
            payload.get("profile_source_evidence_policy_kind")
            or web_search_profile_policy.SOURCE_EVIDENCE_POLICY_KIND
        ),
        "profile_expected_source_present": bool(
            payload.get("profile_expected_source_present", False)
        ),
        "profile_expected_material_used": bool(
            payload.get("profile_expected_material_used", False)
        ),
        "profile_secondary_source_present": bool(
            payload.get("profile_secondary_source_present", False)
        ),
        "profile_secondary_material_used": bool(
            payload.get("profile_secondary_material_used", False)
        ),
        "profile_situated_source_present": bool(
            payload.get("profile_situated_source_present", False)
        ),
        "profile_situated_material_used": bool(
            payload.get("profile_situated_material_used", False)
        ),
        "profile_downrank_source_present": bool(
            payload.get("profile_downrank_source_present", False)
        ),
        "profile_downrank_material_used": bool(
            payload.get("profile_downrank_material_used", False)
        ),
        "profile_insufficient_evidence": bool(
            payload.get("profile_insufficient_evidence", False)
        ),
        "profile_insufficient_evidence_reason_codes": list(
            payload.get("profile_insufficient_evidence_reason_codes") or []
        ),
        "profile_source_domain_counts": dict(
            payload.get("profile_source_domain_counts") or {}
        ),
    }


def emit_web_search_runtime_event(
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
    prompt_kind: str = "chat_web_reformulation",
    explicit_url_detected: bool = False,
    explicit_url: str | None = None,
    read_state: str | None = None,
    primary_source_kind: str = "search",
    primary_read_attempted: bool = False,
    primary_read_status: str | None = None,
    primary_read_filter: str | None = None,
    primary_read_raw_fallback_used: bool = False,
    fallback_used: bool = False,
    collection_path: str = "search_only",
    search_profile: str | None = None,
    query_plan_kind: str = "none",
    query_count: int = 0,
    primary_query_sha256_12: str | None = None,
    secondary_query_count: int = 0,
    secondary_query_sha256_12: list[str] | None = None,
    raw_result_count: int = 0,
    deduped_result_count: int = 0,
    source_first_policy_kind: str = "none",
    source_first_active: bool = False,
    source_first_authority: str = "",
    source_first_product: str = "",
    source_first_probable_domains: list[str] | None = None,
    source_first_reason_codes: list[str] | None = None,
    profile_policy_fields: dict[str, Any] | None = None,
    searxng_profile_params_kind: str = "none",
    searxng_profile_params_policy: str = "none",
    searxng_categories: list[str] | None = None,
    searxng_engines: list[str] | None = None,
    searxng_time_range: str = "",
    searxng_language: str = "",
    searxng_safesearch: str = "",
    searxng_params_reason_codes: list[str] | None = None,
    searxng_hard_parameters: list[str] | None = None,
    searxng_soft_signal_policy: str = "",
    web_discovery_provider: str = "",
    web_discovery_provider_requested: str = "",
    web_discovery_provider_effective: str = "",
    web_discovery_external_used: bool = False,
    web_discovery_external_provider: str = "",
    web_discovery_external_error_kind: str = "",
    web_discovery_reason_codes: list[str] | None = None,
    rerank_applied: bool = False,
    rerank_policy: str = "none",
    rerank_input_count: int = 0,
    rerank_output_count: int = 0,
    rerank_profile: str = "",
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
    web_pdf_read_summary: list[dict[str, Any]] | None = None,
    web_pdf_read_attempted_count: int | None = None,
    web_pdf_read_status_counts: dict[str, int] | None = None,
    web_pdf_read_reason_codes: list[str] | None = None,
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
    web_evidence_policy_kind: str | None = None,
    web_evidence_status: str | None = None,
    web_evidence_reason_codes: list[str] | None = None,
    web_evidence_guidance_codes: list[str] | None = None,
    web_evidence_inputs_summary: dict[str, Any] | None = None,
    web_evidence_can_answer: bool | None = None,
    web_evidence_requires_caveat: bool | None = None,
    web_evidence_can_suggest_reformulation: bool | None = None,
    web_evidence_url_request_policy: str | None = None,
    web_evidence_external_fallback_used: bool = False,
) -> None:
    query_text = str(query_preview or "")
    if truncated is None:
        truncated = any(bool(source.get("truncated")) for source in (sources or []))
        if not truncated and context_block:
            truncated = "[...contenu tronqué]" in str(context_block)
    if source_material_summary is None:
        source_material_summary = build_source_material_summary(list(sources or []))
    if crawl4ai_extraction_summary is None:
        crawl4ai_extraction_summary = build_crawl4ai_extraction_summary(list(sources or []))
    if web_pdf_read_summary is None:
        web_pdf_read_summary = build_web_pdf_read_summary(list(sources or []))
    if web_pdf_read_attempted_count is None:
        web_pdf_read_attempted_count = len(web_pdf_read_summary)
    if web_pdf_read_status_counts is None:
        web_pdf_read_status_counts = count_web_pdf_statuses(web_pdf_read_summary)
    if web_pdf_read_reason_codes is None:
        web_pdf_read_reason_codes = web_pdf_reason_codes(web_pdf_read_summary)
    if crawl4ai_policy_kinds is None:
        crawl4ai_policy_kinds = _derive_crawl4ai_policy_kinds(crawl4ai_extraction_summary)
    if crawl4ai_filter_counts is None:
        crawl4ai_filter_counts = count_crawl4ai_extraction_field(
            crawl4ai_extraction_summary,
            "crawl_filter",
        )
    if crawl4ai_cache_modes is None:
        crawl4ai_cache_modes = count_crawl4ai_extraction_field(
            crawl4ai_extraction_summary,
            "crawl_cache_mode",
        )
    if crawl4ai_fallback_used_count is None:
        crawl4ai_fallback_used_count = sum(
            1
            for item in crawl4ai_extraction_summary
            if bool(item.get("crawl_fallback_used", False))
        )
    if crawl4ai_query_sha256_12 is None:
        crawl4ai_query_sha256_12 = crawl4ai_query_hashes(
            crawl4ai_extraction_summary
        )
    if used_content_kinds is None:
        used_content_kinds = derive_used_content_kinds(source_material_summary)
    if injected_chars is None:
        injected_chars = derive_injected_chars(source_material_summary)
    if context_chars is None:
        context_chars = len(str(context_block or ""))
    redacted_source_summary = event_source_material_summary(source_material_summary)
    redacted_crawl_summary = event_crawl4ai_extraction_summary(
        crawl4ai_extraction_summary
    )
    redacted_pdf_summary = event_web_pdf_read_summary(web_pdf_read_summary)
    payload = {
        "enabled": bool(enabled),
        "status": str(status or ""),
        "reason_code": str(reason_code or ""),
        "query_preview": "",
        "query_present": bool(query_text.strip()),
        "query_chars": len(query_text),
        "query_hash_included": False,
        "results_count": int(results_count),
        "context_injected": bool(context_block),
        "truncated": bool(truncated),
        "explicit_url_detected": bool(explicit_url_detected),
        "explicit_url_chars": len(str(explicit_url or "")),
        "explicit_url_included": False,
        "read_state": str(read_state or ""),
        "primary_source_kind": str(primary_source_kind or "search"),
        "primary_read_attempted": bool(primary_read_attempted),
        "primary_read_status": str(primary_read_status or ""),
        "primary_read_filter": str(primary_read_filter or ""),
        "primary_read_raw_fallback_used": bool(primary_read_raw_fallback_used),
        "fallback_used": bool(fallback_used),
        "collection_path": str(collection_path or "search_only"),
        "search_profile": str(search_profile or ""),
        "query_plan_kind": str(query_plan_kind or "none"),
        "query_count": int(query_count or 0),
        "primary_query_hash_included": False,
        "secondary_query_count": int(secondary_query_count or 0),
        "secondary_query_hash_count": len(list(secondary_query_sha256_12 or [])),
        "secondary_query_hashes_included": False,
        "raw_result_count": int(raw_result_count or 0),
        "deduped_result_count": int(deduped_result_count or 0),
        "source_first_policy_kind": str(source_first_policy_kind or "none"),
        "source_first_active": bool(source_first_active),
        "source_first_authority": str(source_first_authority or ""),
        "source_first_product": str(source_first_product or ""),
        "source_first_probable_domains": list(source_first_probable_domains or []),
        "source_first_reason_codes": list(source_first_reason_codes or []),
        **profile_policy_event_fields(profile_policy_fields or {}),
        "searxng_profile_params_kind": str(searxng_profile_params_kind or "none"),
        "searxng_profile_params_policy": str(searxng_profile_params_policy or "none"),
        "searxng_categories": list(searxng_categories or []),
        "searxng_engines": list(searxng_engines or []),
        "searxng_time_range": str(searxng_time_range or ""),
        "searxng_language": str(searxng_language or ""),
        "searxng_safesearch": str(searxng_safesearch or ""),
        "searxng_params_reason_codes": list(searxng_params_reason_codes or []),
        "searxng_hard_parameters": list(searxng_hard_parameters or []),
        "searxng_soft_signal_policy": str(searxng_soft_signal_policy or ""),
        "web_discovery_provider": str(web_discovery_provider or ""),
        "web_discovery_provider_requested": str(web_discovery_provider_requested or ""),
        "web_discovery_provider_effective": str(web_discovery_provider_effective or ""),
        "web_discovery_external_used": bool(web_discovery_external_used),
        "web_discovery_external_provider": str(web_discovery_external_provider or ""),
        "web_discovery_external_error_kind": str(web_discovery_external_error_kind or ""),
        "web_discovery_reason_codes": list(web_discovery_reason_codes or []),
        "rerank_applied": bool(rerank_applied),
        "rerank_policy": str(rerank_policy or "none"),
        "rerank_input_count": int(rerank_input_count or 0),
        "rerank_output_count": int(rerank_output_count or 0),
        "rerank_profile": str(rerank_profile or ""),
        "rerank_top_domains_before": list(rerank_top_domains_before or []),
        "rerank_top_domains_after": list(rerank_top_domains_after or []),
        "rerank_reason_counts": dict(rerank_reason_counts or {}),
        "rerank_promoted_count": int(rerank_promoted_count or 0),
        "rerank_downranked_count": int(rerank_downranked_count or 0),
        "used_content_kinds": list(used_content_kinds or []),
        "injected_chars": int(injected_chars or 0),
        "context_chars": int(context_chars or 0),
        "source_material_summary": redacted_source_summary,
        "crawl4ai_extraction_summary": redacted_crawl_summary,
        "web_pdf_read_summary": redacted_pdf_summary,
        "web_pdf_read_attempted_count": int(web_pdf_read_attempted_count or 0),
        "web_pdf_read_status_counts": dict(web_pdf_read_status_counts or {}),
        "web_pdf_read_reason_codes": list(web_pdf_read_reason_codes or []),
        "crawl4ai_policy_kinds": list(crawl4ai_policy_kinds or []),
        "crawl4ai_filter_counts": dict(crawl4ai_filter_counts or {}),
        "crawl4ai_cache_modes": dict(crawl4ai_cache_modes or {}),
        "crawl4ai_fallback_used_count": int(crawl4ai_fallback_used_count or 0),
        "crawl4ai_query_hash_count": len(list(crawl4ai_query_sha256_12 or [])),
        "crawl4ai_query_hashes_included": False,
    }
    if web_confidence_policy_kind is None:
        payload.update(web_search_confidence.evaluate_web_confidence(payload))
    else:
        payload.update(
            {
                "web_confidence_policy_kind": str(web_confidence_policy_kind or ""),
                "web_confidence_level": str(web_confidence_level or "unknown"),
                "web_confidence_score": float(web_confidence_score or 0.0),
                "web_confidence_reason_codes": list(web_confidence_reason_codes or []),
                "web_confidence_inputs_summary": dict(web_confidence_inputs_summary or {}),
                "openrouter_fallback_state": str(openrouter_fallback_state or "future_only"),
                "openrouter_fallback_used": bool(openrouter_fallback_used),
                "openrouter_fallback_reason_codes": list(openrouter_fallback_reason_codes or []),
            }
        )
    if web_evidence_policy_kind is None:
        payload.update(web_search_evidence.evaluate_web_evidence(payload))
    else:
        payload.update(
            {
                "web_evidence_policy_kind": str(web_evidence_policy_kind or ""),
                "web_evidence_status": str(web_evidence_status or "not_applicable"),
                "web_evidence_reason_codes": list(web_evidence_reason_codes or []),
                "web_evidence_guidance_codes": list(web_evidence_guidance_codes or []),
                "web_evidence_inputs_summary": dict(web_evidence_inputs_summary or {}),
                "web_evidence_can_answer": bool(web_evidence_can_answer),
                "web_evidence_requires_caveat": bool(web_evidence_requires_caveat),
                "web_evidence_can_suggest_reformulation": bool(
                    web_evidence_can_suggest_reformulation
                ),
                "web_evidence_url_request_policy": str(
                    web_evidence_url_request_policy or ""
                ),
                "web_evidence_external_fallback_used": bool(
                    web_evidence_external_fallback_used
                ),
            }
        )
    if reason_code:
        payload["reason_code"] = str(reason_code)
    if error_class:
        payload["error_class"] = error_class
    chat_turn_logger.emit(
        "web_search",
        status=status,
        reason_code=reason_code,
        prompt_kind=prompt_kind,
        payload=payload,
    )
    if status == "skipped" and reason_code:
        chat_turn_logger.emit_branch_skipped(
            reason_code=reason_code,
            reason_short="web_search_no_results",
        )
    if status == "error" and error_class:
        chat_turn_logger.emit_error(
            error_code=reason_code or "upstream_error",
            error_class=error_class,
            message_short=str(message_short or reason_code or "web_search_error"),
        )
