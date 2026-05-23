from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
import time
from typing import Any
from urllib.parse import urlparse

import requests

from benchmark.core.campaign import CampaignConfig, sha256_file, sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.web_search import adapter


SNIPPET_MAX_CHARS = 280
ANSWER_PREVIEW_CHARS = 700
WEB_SEARCH_TOOL_COST_USD = 0.005


def run_web_search_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    arms: list[str] | None = None,
    max_results: int = adapter.DEFAULT_MAX_RESULTS,
    max_total_results: int = adapter.DEFAULT_MAX_TOTAL_RESULTS,
    search_context_size: str = adapter.DEFAULT_SEARCH_CONTEXT_SIZE,
) -> dict[str, Any]:
    campaign = build_web_search_campaign(
        config=config,
        client=client,
        arms=arms,
        max_results=max_results,
        max_total_results=max_total_results,
        search_context_size=search_context_size,
    )
    output_dir = config.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"{config.campaign_id}.json"
    jsonl_path = output_dir / f"{config.campaign_id}.jsonl"
    markdown_path = output_dir / f"{config.campaign_id}.md"
    system_markdown_paths = _write_system_markdown_reports(output_dir, campaign)
    write_json(json_path, campaign)
    jsonl_path.write_text(_render_jsonl(campaign), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(campaign), encoding="utf-8")
    return {
        "json_path": str(json_path),
        "jsonl_path": str(jsonl_path),
        "markdown_path": str(markdown_path),
        "system_markdown_paths": {key: str(value) for key, value in system_markdown_paths.items()},
    }


def build_web_search_campaign(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    arms: list[str] | None = None,
    max_results: int = adapter.DEFAULT_MAX_RESULTS,
    max_total_results: int = adapter.DEFAULT_MAX_TOTAL_RESULTS,
    search_context_size: str = adapter.DEFAULT_SEARCH_CONTEXT_SIZE,
) -> dict[str, Any]:
    normalized_arms = adapter.normalize_arms(arms)
    cases = adapter.load_cases(config.repo_root)
    case_results: list[dict[str, Any]] = []
    for case in cases:
        arm_results: list[dict[str, Any]] = []
        for arm in normalized_arms:
            if arm == "local":
                arm_results.append(_run_local_arm(config=config, case=case))
                continue
            if arm == "local_profiled":
                arm_results.append(_run_local_profiled_arm(config=config, case=case))
                continue
            for model in config.models:
                engine = adapter.openrouter_engine_for_arm(arm)
                arm_results.append(
                    _run_openrouter_search_arm(
                        config=config,
                        client=client,
                        case=case,
                        arm=arm,
                        model=model,
                        engine=engine,
                        max_results=max_results,
                        max_total_results=max_total_results,
                        search_context_size=search_context_size,
                    )
                )
        case_results.append(
            {
                "case": _public_case(case),
                "arms": arm_results,
            }
        )
    return {
        "campaign_id": config.campaign_id,
        "created_at_utc": utc_timestamp(),
        "suite": "web_search",
        "dry_run": config.dry_run,
        "models": config.models,
        "arms": normalized_arms,
        "case_count": len(cases),
        "fixture_path": str(adapter.fixture_path(config.repo_root).relative_to(config.repo_root)),
        "fixture_sha256": sha256_file(adapter.fixture_path(config.repo_root)),
        "openrouter_parameters": {
            "tool_type": adapter.OPENROUTER_SEARCH_TOOL_TYPE,
            "max_results": int(max_results),
            "max_total_results": int(max_total_results),
            "search_context_size": str(search_context_size),
            "deprecated_paths_forbidden": ["plugins:[{id:web}]", ":online"],
        },
        "local_pipeline": {
            "mode": "local keeps the single-query historical SearXNG baseline; local_profiled uses bounded queries, governed SearXNG engine baskets, soft reranking, profiled Crawl4AI extraction and confidence observability",
            "runtime_changed": True,
            "chat_pipeline_changed": False,
            "local_profiled_stub": "false_after_lot7_confidence_observability",
        },
        "evaluation_grid": _evaluation_grid(),
        "secrets_written": False,
        "production_runtime_changed": False,
        "human_decision_required": True,
        "results": case_results,
    }


def _run_local_arm(
    *,
    config: CampaignConfig,
    case: dict[str, Any],
    arm: str = "local",
    mode: str = "local_searxng_crawl4ai",
    engine: str = "searxng_crawl4ai",
    enable_specialized_queries: bool = False,
    enable_profiled_searxng_params: bool = False,
    enable_reranking: bool = False,
    enable_profiled_crawl4ai_policy: bool = False,
) -> dict[str, Any]:
    if config.dry_run:
        source = adapter.dry_run_source(case, arm=arm)
        return {
            "arm": arm,
            "mode": mode,
            "model": None,
            "engine": engine,
            "ok": True,
            "status": "dry_run",
            "elapsed_ms": 0.0,
            "error": None,
            "cost_estimate_usd": None,
            "cost_estimate_source": "dry_run",
            "usage": {},
            "local": {
                "read_state": "dry_run",
                "collection_path": "dry_run",
                "used_content_kinds": ["dry_run_fixture"],
                "injected_chars": 0,
                "context_chars": 0,
                "results_count": 1,
                "query_plan_kind": "dry_run",
                "query_count": 0,
                "secondary_query_count": 0,
                "deduped_result_count": 1,
                "searxng_profile_params_kind": "dry_run",
                "searxng_profile_params_policy": "dry_run",
                "searxng_categories": [],
                "searxng_engines": [],
                "searxng_time_range": "",
                "searxng_language": "",
                "searxng_safesearch": "",
                "rerank_applied": False,
                "rerank_policy": "dry_run",
                "rerank_input_count": 0,
                "rerank_output_count": 0,
                "rerank_profile": "",
                "rerank_top_domains_before": [],
                "rerank_top_domains_after": [],
                "rerank_reason_counts": {},
                "rerank_promoted_count": 0,
                "rerank_downranked_count": 0,
                "crawl4ai_policy_kinds": [],
                "crawl4ai_filter_counts": {},
                "crawl4ai_cache_modes": {},
                "crawl4ai_fallback_used_count": 0,
                "crawl4ai_query_sha256_12": [],
                "web_confidence_policy_kind": "dry_run",
                "web_confidence_level": "unknown",
                "web_confidence_score": 0.0,
                "web_confidence_reason_codes": [],
                "web_confidence_inputs_summary": {},
                "openrouter_fallback_state": "not_applicable",
                "openrouter_fallback_used": False,
                "openrouter_fallback_reason_codes": [],
                "web_discovery_provider": "local",
                "web_discovery_provider_requested": "local",
                "web_discovery_provider_effective": "local",
                "web_discovery_external_used": False,
                "web_discovery_external_provider": "",
                "web_discovery_external_error_kind": "",
                "web_discovery_reason_codes": ["dry_run"],
            },
            "sources": [source],
            "answer_preview": "Dry-run local: aucun appel SearXNG, Crawl4AI ou OpenRouter.",
            "raw_text_sha256": "",
            "raw_text_chars": 0,
            "request_signature": _local_request_signature(case, arm=arm),
        }

    app_dir = config.repo_root / "app"
    if str(app_dir) not in sys.path:
        sys.path.insert(0, str(app_dir))
    start = time.perf_counter()
    try:
        from tools import web_search

        payload = web_search.build_context_payload(
            str(case.get("user_query") or ""),
            enable_specialized_queries=enable_specialized_queries,
            enable_profiled_searxng_params=enable_profiled_searxng_params,
            enable_reranking=enable_reranking,
            enable_profiled_crawl4ai_policy=enable_profiled_crawl4ai_policy,
            discovery_provider="local" if arm == "local" else None,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        sources = [_local_source(source) for source in payload.get("sources") or []]
        return {
            "arm": arm,
            "mode": mode,
            "model": None,
            "engine": engine,
            "ok": str(payload.get("status") or "") == "ok",
            "status": str(payload.get("status") or ""),
            "elapsed_ms": round(elapsed_ms, 3),
            "error": payload.get("reason_code"),
            "cost_estimate_usd": None,
            "cost_estimate_source": "local_pipeline_unpriced",
            "usage": {},
            "local": {
                "read_state": payload.get("read_state"),
                "collection_path": payload.get("collection_path"),
                "search_profile": payload.get("search_profile"),
                "query_plan_kind": payload.get("query_plan_kind"),
                "query_count": int(payload.get("query_count") or 0),
                "secondary_query_count": int(payload.get("secondary_query_count") or 0),
                "deduped_result_count": int(payload.get("deduped_result_count") or 0),
                "searxng_profile_params_kind": payload.get("searxng_profile_params_kind"),
                "searxng_profile_params_policy": payload.get("searxng_profile_params_policy"),
                "searxng_categories": list(payload.get("searxng_categories") or []),
                "searxng_engines": list(payload.get("searxng_engines") or []),
                "searxng_time_range": payload.get("searxng_time_range"),
                "searxng_language": payload.get("searxng_language"),
                "searxng_safesearch": payload.get("searxng_safesearch"),
                "rerank_applied": bool(payload.get("rerank_applied", False)),
                "rerank_policy": payload.get("rerank_policy"),
                "rerank_input_count": int(payload.get("rerank_input_count") or 0),
                "rerank_output_count": int(payload.get("rerank_output_count") or 0),
                "rerank_profile": payload.get("rerank_profile"),
                "rerank_top_domains_before": list(payload.get("rerank_top_domains_before") or []),
                "rerank_top_domains_after": list(payload.get("rerank_top_domains_after") or []),
                "rerank_reason_counts": dict(payload.get("rerank_reason_counts") or {}),
                "rerank_promoted_count": int(payload.get("rerank_promoted_count") or 0),
                "rerank_downranked_count": int(payload.get("rerank_downranked_count") or 0),
                "crawl4ai_policy_kinds": list(payload.get("crawl4ai_policy_kinds") or []),
                "crawl4ai_filter_counts": dict(payload.get("crawl4ai_filter_counts") or {}),
                "crawl4ai_cache_modes": dict(payload.get("crawl4ai_cache_modes") or {}),
                "crawl4ai_fallback_used_count": int(payload.get("crawl4ai_fallback_used_count") or 0),
                "crawl4ai_query_sha256_12": list(payload.get("crawl4ai_query_sha256_12") or []),
                "used_content_kinds": list(payload.get("used_content_kinds") or []),
                "injected_chars": int(payload.get("injected_chars") or 0),
                "context_chars": int(payload.get("context_chars") or 0),
                "results_count": int(payload.get("results_count") or 0),
                "primary_read_status": payload.get("primary_read_status"),
                "fallback_used": bool(payload.get("fallback_used", False)),
                "web_confidence_policy_kind": payload.get("web_confidence_policy_kind"),
                "web_confidence_level": payload.get("web_confidence_level"),
                "web_confidence_score": payload.get("web_confidence_score"),
                "web_confidence_reason_codes": list(payload.get("web_confidence_reason_codes") or []),
                "web_confidence_inputs_summary": dict(payload.get("web_confidence_inputs_summary") or {}),
                "openrouter_fallback_state": payload.get("openrouter_fallback_state"),
                "openrouter_fallback_used": bool(payload.get("openrouter_fallback_used", False)),
                "openrouter_fallback_reason_codes": list(payload.get("openrouter_fallback_reason_codes") or []),
                "web_discovery_provider": payload.get("web_discovery_provider"),
                "web_discovery_provider_requested": payload.get("web_discovery_provider_requested"),
                "web_discovery_provider_effective": payload.get("web_discovery_provider_effective"),
                "web_discovery_external_used": bool(payload.get("web_discovery_external_used", False)),
                "web_discovery_external_provider": payload.get("web_discovery_external_provider"),
                "web_discovery_external_error_kind": payload.get("web_discovery_external_error_kind"),
                "web_discovery_reason_codes": list(payload.get("web_discovery_reason_codes") or []),
            },
            "sources": sources,
            "answer_preview": _bounded_preview(payload.get("context_block"), max_chars=ANSWER_PREVIEW_CHARS),
            "raw_text_sha256": _sha256_text(str(payload.get("context_block") or "")),
            "raw_text_chars": len(str(payload.get("context_block") or "")),
            "request_signature": _local_request_signature(case, arm=arm),
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "arm": arm,
            "mode": mode,
            "model": None,
            "engine": engine,
            "ok": False,
            "status": "error",
            "elapsed_ms": round(elapsed_ms, 3),
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "cost_estimate_usd": None,
            "cost_estimate_source": "local_pipeline_error",
            "usage": {},
            "local": {},
            "sources": [],
            "answer_preview": "",
            "raw_text_sha256": "",
            "raw_text_chars": 0,
            "request_signature": _local_request_signature(case, arm=arm),
        }


def _run_local_profiled_arm(*, config: CampaignConfig, case: dict[str, Any]) -> dict[str, Any]:
    result = _run_local_arm(
        config=config,
        case=case,
        arm="local_profiled",
        mode="local_profiled_specialized_queries_governed_searxng_baskets_rerank_crawl4ai_policy_confidence_observability",
        engine="searxng_crawl4ai_profiled_queries_governed_baskets_rerank_crawl_policy_confidence",
        enable_specialized_queries=True,
        enable_profiled_searxng_params=True,
        enable_reranking=True,
        enable_profiled_crawl4ai_policy=True,
    )
    local = dict(result.get("local") or {})
    runtime_profile = str(local.get("search_profile") or "").strip()
    local.update(
        {
            "search_profile": runtime_profile or "stub_not_implemented",
            "local_profiled_stub": False,
        }
    )
    result["local"] = local
    result["profiled_stub"] = {
        "status": "confidence_observability_lot7",
        "runtime_changed": True,
        "fixture_path": str(adapter.local_bad_order_fixture_path(config.repo_root).relative_to(config.repo_root)),
    }
    if config.dry_run:
        result["answer_preview"] = "Dry-run local_profiled: Lot 7 shape only, no SearXNG, Crawl4AI or OpenRouter call."
    return result


def _run_openrouter_search_arm(
    *,
    config: CampaignConfig,
    client: OpenRouterClient | None,
    case: dict[str, Any],
    arm: str,
    model: str,
    engine: str,
    max_results: int,
    max_total_results: int,
    search_context_size: str,
) -> dict[str, Any]:
    payload = adapter.build_openrouter_payload(
        case=case,
        model=model,
        engine=engine,
        max_results=max_results,
        max_total_results=max_total_results,
        search_context_size=search_context_size,
    )
    request_signature = {
        "messages_sha256": sha256_text(json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)),
        "tools_sha256": sha256_text(json.dumps(payload["tools"], ensure_ascii=False, sort_keys=True)),
        "generation_params": {
            "temperature": payload.get("temperature"),
            "top_p": payload.get("top_p"),
            "max_tokens": payload.get("max_tokens"),
        },
    }
    if config.dry_run:
        source = adapter.dry_run_source(case, arm=arm)
        return {
            "arm": arm,
            "mode": "openrouter_server_tool",
            "model": model,
            "engine": engine,
            "ok": True,
            "status": "dry_run",
            "elapsed_ms": 0.0,
            "error": None,
            "cost_estimate_usd": None,
            "cost_estimate_source": "dry_run",
            "usage": {"server_tool_use": {"web_search_requests": 1}, "input_tokens": 0, "output_tokens": 0},
            "openrouter": {
                "web_search_requests": 1,
                "finish_reason": "dry_run",
                "native_finish_reason": "dry_run",
            },
            "sources": [source],
            "answer_preview": f"Dry-run {engine}: aucun appel OpenRouter.",
            "raw_text_sha256": "",
            "raw_text_chars": 0,
            "request_signature": request_signature,
        }
    if client is None:
        raise RuntimeError("client is required outside dry-run mode")
    return _call_openrouter(client, payload=payload, arm=arm, model=model, engine=engine, timeout_s=config.timeout_s, request_signature=request_signature)


def _call_openrouter(
    client: OpenRouterClient,
    *,
    payload: dict[str, Any],
    arm: str,
    model: str,
    engine: str,
    timeout_s: int,
    request_signature: dict[str, Any],
) -> dict[str, Any]:
    start = time.perf_counter()
    try:
        response = requests.post(
            f"{client.config.base_url}/chat/completions",
            json=payload,
            headers=client._headers(caller=f"benchmark_web_search_{engine}"),  # noqa: SLF001 - benchmark helper uses shared client auth.
            timeout=timeout_s,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json() if response.content else {}
        usage = dict(data.get("usage") or {}) if isinstance(data, dict) else {}
        text = _extract_text(data)
        sources = _openrouter_sources(data)
        cost, cost_source = _estimate_openrouter_web_cost(client, model=model, engine=engine, usage=usage)
        error = None
        ok = response.status_code < 400
        if not ok:
            error = _compact_error(data) or response.text[:500]
        return {
            "arm": arm,
            "mode": "openrouter_server_tool",
            "model": model,
            "engine": engine,
            "ok": ok,
            "status": str(response.status_code),
            "elapsed_ms": round(elapsed_ms, 3),
            "error": error,
            "cost_estimate_usd": cost,
            "cost_estimate_source": cost_source,
            "usage": usage,
            "openrouter": {
                "web_search_requests": _web_search_requests(usage),
                "finish_reason": _finish_reason(data),
                "native_finish_reason": _native_finish_reason(data),
            },
            "sources": sources,
            "answer_preview": _bounded_preview(text, max_chars=ANSWER_PREVIEW_CHARS),
            "raw_text_sha256": _sha256_text(text),
            "raw_text_chars": len(text),
            "request_signature": request_signature,
        }
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return {
            "arm": arm,
            "mode": "openrouter_server_tool",
            "model": model,
            "engine": engine,
            "ok": False,
            "status": "error",
            "elapsed_ms": round(elapsed_ms, 3),
            "error": f"{type(exc).__name__}: {str(exc)[:300]}",
            "cost_estimate_usd": None,
            "cost_estimate_source": "exception",
            "usage": {},
            "openrouter": {"web_search_requests": None},
            "sources": [],
            "answer_preview": "",
            "raw_text_sha256": "",
            "raw_text_chars": 0,
            "request_signature": request_signature,
        }


def render_markdown_report(campaign: dict[str, Any]) -> str:
    params = campaign.get("openrouter_parameters") or {}
    lines = [
        f"# Benchmark recherche web - {campaign['campaign_id']}",
        "",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- Fixtures: `{campaign['fixture_path']}` (`{campaign['fixture_sha256'][:12]}`)",
        f"- Arms: `{', '.join(campaign.get('arms') or [])}`",
        f"- OpenRouter tool: `{params.get('tool_type')}`",
        f"- OpenRouter params: `max_results={params.get('max_results')}`, `max_total_results={params.get('max_total_results')}`, `search_context_size={params.get('search_context_size')}`",
        "- Production runtime changed: `False`",
        "- Decision automatique: `False`",
        "",
        "## Ce que ce benchmark mesure",
        "",
        "- Pipeline local FridaDev: SearXNG, Crawl4AI et reformulation web existante quand nécessaire.",
        "- OpenRouter `openrouter:web_search` avec moteurs Exa et Parallel, bornés en résultats et contexte.",
        "- Latence, coût estimé, sources, domaines, signaux de vérité de lecture et intégrabilité FridaDev.",
        "",
        "## Ce qu'il ne décide pas",
        "",
        "- Il ne remplace pas le pipeline web de production.",
        "- Il ne choisit pas automatiquement Exa, Parallel ou un hybride.",
        "- Il ne prouve pas la qualité conversationnelle finale de Frida.",
        "",
        "## Grille d'évaluation humaine",
        "",
        "| Critère | Lecture humaine attendue |",
        "| --- | --- |",
    ]
    for item in campaign.get("evaluation_grid") or []:
        lines.append(f"| {item['criterion']} | {item['question']} |")
    lines.extend(
        [
            "",
            "## Synthèse par cas",
            "",
        ]
    )
    for case_result in campaign.get("results") or []:
        case = case_result.get("case") or {}
        lines.extend(
            [
                f"### {case.get('id')} - {case.get('title')}",
                "",
                f"- Catégorie: `{case.get('category')}`",
                f"- Requête: {case.get('user_query')}",
                f"- Domaines attendus possibles: `{', '.join(case.get('must_include_domains') or []) or 'n/a'}`",
                "",
                "| Bras | OK | Latence | Coût est. | Requêtes web | Tokens | Sources | Signaux locaux | Aperçu borné |",
                "| --- | --- | ---: | ---: | ---: | --- | --- | --- | --- |",
            ]
        )
        for result in case_result.get("arms") or []:
            lines.append(
                "| "
                + " | ".join(
                    [
                        f"`{_arm_label(result)}`",
                        "oui" if result.get("ok") else "non",
                        f"{float(result.get('elapsed_ms') or 0.0):.0f} ms",
                        _format_cost(result.get("cost_estimate_usd")),
                        _web_search_requests_text(result.get("usage") or {}),
                        _token_summary(result.get("usage") or {}),
                        _source_domains_summary(result.get("sources") or []),
                        _local_signal_summary(result),
                        _markdown_cell(str(result.get("answer_preview") or "")),
                    ]
                )
                + " |"
            )
        lines.append("")
    lines.extend(
        [
            "## Options de décision futures",
            "",
            "- Garder le local seul si les sources et la vérité de lecture sont suffisantes.",
            "- Utiliser OpenRouter Exa en fallback borné si les extraits sont meilleurs sur les requêtes larges.",
            "- Utiliser OpenRouter Parallel en fallback borné si la fraîcheur ou la qualité de synthèse compense le coût.",
            "- Construire un hybride local + OpenRouter, avec garde de coût et observabilité claire.",
            "- Ne rien changer si le benchmark ne montre pas d'amélioration nette.",
            "",
        ]
    )
    return "\n".join(lines)


def render_system_markdown_report(campaign: dict[str, Any], *, arm: str) -> str:
    params = campaign.get("openrouter_parameters") or {}
    lines = [
        f"# Benchmark recherche web - {arm.replace('_', '-')}",
        "",
        f"- Campaign: `{campaign['campaign_id']}`",
        f"- Created UTC: `{campaign['created_at_utc']}`",
        f"- Dry run: `{campaign['dry_run']}`",
        f"- OpenRouter tool: `{params.get('tool_type')}`",
        f"- OpenRouter params: `max_results={params.get('max_results')}`, `max_total_results={params.get('max_total_results')}`, `search_context_size={params.get('search_context_size')}`",
        "- Runtime FridaDev modifié: `False`",
        "",
        "Ce fichier isole un seul système pour comparer les bras côte à côte.",
        "",
    ]
    for case_result in campaign.get("results") or []:
        case = case_result.get("case") or {}
        matching = [result for result in case_result.get("arms") or [] if result.get("arm") == arm]
        lines.extend(
            [
                f"## {case.get('id')} - {case.get('title')}",
                "",
                f"- Catégorie: `{case.get('category')}`",
                f"- Question utilisateur: {case.get('user_query')}",
            ]
        )
        if not matching:
            lines.extend(["- Statut: `not_run`", ""])
            continue
        for result in matching:
            lines.extend(_result_markdown_block(result))
        lines.append("")
    return "\n".join(lines)


def _render_jsonl(campaign: dict[str, Any]) -> str:
    lines: list[str] = []
    for case_result in campaign.get("results") or []:
        case = case_result.get("case") or {}
        for result in case_result.get("arms") or []:
            lines.append(json.dumps({"case_id": case.get("id"), "result": result}, ensure_ascii=False, sort_keys=True))
    return "\n".join(lines) + ("\n" if lines else "")


def _write_system_markdown_reports(output_dir: Path, campaign: dict[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for arm in campaign.get("arms") or []:
        file_name = f"{str(arm).replace('_', '-')}.md"
        path = output_dir / file_name
        path.write_text(render_system_markdown_report(campaign, arm=str(arm)), encoding="utf-8")
        paths[str(arm)] = path
    return paths


def _result_markdown_block(result: dict[str, Any]) -> list[str]:
    usage = result.get("usage") or {}
    lines = [
        f"- Système: `{_arm_label(result)}`",
        f"- Statut: `{result.get('status')}` (`{'ok' if result.get('ok') else 'error'}`)",
        f"- Latence: `{float(result.get('elapsed_ms') or 0.0):.0f} ms`",
        f"- Coût estimé: `{_format_cost(result.get('cost_estimate_usd'))}` ({result.get('cost_estimate_source') or 'n/a'})",
        f"- Tokens input/output/total: `{_token_summary(usage)}`",
        f"- Requêtes web OpenRouter: `{_web_search_requests_text(usage)}`",
    ]
    if result.get("error"):
        lines.append(f"- Erreur: `{_markdown_inline(str(result.get('error') or ''))}`")
    local = result.get("local") or {}
    if local:
        lines.extend(
            [
                "- Signaux locaux:",
                f"  - `read_state`: `{local.get('read_state')}`",
                f"  - `collection_path`: `{local.get('collection_path')}`",
                f"  - `used_content_kinds`: `{', '.join(local.get('used_content_kinds') or []) or 'none'}`",
                f"  - `injected_chars`: `{local.get('injected_chars')}`",
                f"  - `context_chars`: `{local.get('context_chars')}`",
            ]
        )
        if "search_profile" in local:
            lines.append(f"  - `search_profile`: `{local.get('search_profile')}`")
        if "query_plan_kind" in local:
            lines.append(f"  - `query_plan_kind`: `{local.get('query_plan_kind')}`")
            lines.append(f"  - `query_count`: `{local.get('query_count')}`")
            lines.append(f"  - `secondary_query_count`: `{local.get('secondary_query_count')}`")
            lines.append(f"  - `deduped_result_count`: `{local.get('deduped_result_count')}`")
        if "searxng_profile_params_kind" in local:
            lines.append(f"  - `searxng_profile_params_kind`: `{local.get('searxng_profile_params_kind')}`")
            lines.append(f"  - `searxng_profile_params_policy`: `{local.get('searxng_profile_params_policy')}`")
            lines.append(f"  - `searxng_categories`: `{','.join(local.get('searxng_categories') or [])}`")
            lines.append(f"  - `searxng_engines`: `{','.join(local.get('searxng_engines') or [])}`")
            lines.append(f"  - `searxng_time_range`: `{local.get('searxng_time_range') or ''}`")
            lines.append(f"  - `searxng_language`: `{local.get('searxng_language') or ''}`")
            lines.append(f"  - `searxng_safesearch`: `{local.get('searxng_safesearch') or ''}`")
        if "rerank_applied" in local:
            lines.append(f"  - `rerank_applied`: `{bool(local.get('rerank_applied', False))}`")
            lines.append(f"  - `rerank_policy`: `{local.get('rerank_policy') or ''}`")
            lines.append(f"  - `rerank_input_count`: `{local.get('rerank_input_count')}`")
            lines.append(f"  - `rerank_output_count`: `{local.get('rerank_output_count')}`")
            lines.append(f"  - `rerank_top_domains_before`: `{','.join(local.get('rerank_top_domains_before') or [])}`")
            lines.append(f"  - `rerank_top_domains_after`: `{','.join(local.get('rerank_top_domains_after') or [])}`")
            lines.append(
                f"  - `rerank_reason_counts`: `{json.dumps(local.get('rerank_reason_counts') or {}, ensure_ascii=False, sort_keys=True)}`"
            )
        if "crawl4ai_policy_kinds" in local:
            lines.append(f"  - `crawl4ai_policy_kinds`: `{','.join(local.get('crawl4ai_policy_kinds') or [])}`")
            lines.append(
                f"  - `crawl4ai_filter_counts`: `{json.dumps(local.get('crawl4ai_filter_counts') or {}, ensure_ascii=False, sort_keys=True)}`"
            )
            lines.append(
                f"  - `crawl4ai_cache_modes`: `{json.dumps(local.get('crawl4ai_cache_modes') or {}, ensure_ascii=False, sort_keys=True)}`"
            )
            lines.append(f"  - `crawl4ai_fallback_used_count`: `{local.get('crawl4ai_fallback_used_count')}`")
        if "web_confidence_level" in local:
            lines.append(f"  - `web_confidence_policy_kind`: `{local.get('web_confidence_policy_kind') or ''}`")
            lines.append(f"  - `web_confidence_level`: `{local.get('web_confidence_level') or ''}`")
            lines.append(f"  - `web_confidence_score`: `{local.get('web_confidence_score')}`")
            lines.append(
                f"  - `web_confidence_reason_codes`: `{','.join(local.get('web_confidence_reason_codes') or [])}`"
            )
            lines.append(f"  - `openrouter_fallback_state`: `{local.get('openrouter_fallback_state') or ''}`")
            lines.append(f"  - `openrouter_fallback_used`: `{bool(local.get('openrouter_fallback_used', False))}`")
            lines.append(
                f"  - `openrouter_fallback_reason_codes`: `{','.join(local.get('openrouter_fallback_reason_codes') or [])}`"
            )
        if bool(local.get("local_profiled_stub", False)):
            lines.append("  - `local_profiled_stub`: `True`")
    lines.extend(
        [
            "- Sources / URLs:",
            *_sources_markdown_lines(result.get("sources") or []),
            "- Extrait borné:",
            "",
            f"> {_markdown_quote(str(result.get('answer_preview') or 'n/a'))}",
            "",
        ]
    )
    return lines


def _sources_markdown_lines(sources: list[dict[str, Any]]) -> list[str]:
    if not sources:
        return ["  - n/a"]
    lines: list[str] = []
    for source in sources[:8]:
        url = str(source.get("url") or "")
        domain = str(source.get("domain") or _domain(url) or "")
        title = _markdown_inline(str(source.get("title") or "source"))
        preview = _markdown_inline(str(source.get("content_preview") or ""))
        bits = [f"`{domain or 'domain_unknown'}`"]
        if url:
            bits.append(url)
        if source.get("rerank_bucket"):
            bits.append(f"rerank={source.get('rerank_bucket')}")
        if source.get("rerank_reason_codes"):
            bits.append(f"reasons={','.join(source.get('rerank_reason_codes') or [])}")
        if source.get("crawl_policy_kind"):
            bits.append(f"crawl={source.get('crawl_filter') or 'n/a'}")
            bits.append(f"crawl_policy={source.get('crawl_policy_kind')}")
            if source.get("crawl_fallback_used"):
                bits.append(f"crawl_fallback={source.get('crawl_fallback_reason') or 'true'}")
        if preview:
            bits.append(f"extrait: {preview}")
        lines.append(f"  - {title}: " + " ; ".join(bits))
    if len(sources) > 8:
        lines.append(f"  - ... {len(sources) - 8} source(s) supplémentaire(s) bornées dans le JSON")
    return lines


def _public_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(case.get("id") or ""),
        "title": str(case.get("title") or ""),
        "category": str(case.get("category") or ""),
        "user_query": str(case.get("user_query") or ""),
        "expected_source_kinds": list(case.get("expected_source_kinds") or []),
        "must_include_domains": list(case.get("must_include_domains") or []),
        "notes": str(case.get("notes") or ""),
    }


def _evaluation_grid() -> list[dict[str, str]]:
    return [
        {"criterion": "Pertinence des sources", "question": "Les sources répondent-elles vraiment à la question ?"},
        {"criterion": "Fraîcheur", "question": "Les informations récentes sont-elles datées et actuelles ?"},
        {"criterion": "Autorité", "question": "Les sources officielles ou primaires sont-elles favorisées quand nécessaire ?"},
        {"criterion": "Qualité des extraits", "question": "Les extraits suffisent-ils à soutenir la réponse sans surlecture ?"},
        {"criterion": "URL explicite", "question": "Le bras sait-il lire ou reconnaître la source cible plutôt qu'une recherche générique ?"},
        {"criterion": "Coût", "question": "Le gain qualitatif justifie-t-il les requêtes serveur et tokens ajoutés ?"},
        {"criterion": "Latence", "question": "Le délai reste-t-il acceptable pour un chat FridaDev ?"},
        {"criterion": "Intégrabilité", "question": "Le résultat expose-t-il assez de signaux pour read_state, logs et non-contamination ?"},
    ]


def _local_source(source: dict[str, Any]) -> dict[str, Any]:
    content = str(source.get("content_used") or "")
    url = str(source.get("url") or "")
    return {
        "title": str(source.get("title") or ""),
        "url": url,
        "domain": str(source.get("source_domain") or _domain(url) or ""),
        "source_origin": str(source.get("source_origin") or ""),
        "used_content_kind": str(source.get("used_content_kind") or ""),
        "crawl_status": str(source.get("crawl_status") or ""),
        "crawl_filter": str(source.get("crawl_filter") or ""),
        "crawl_filter_requested": str(source.get("crawl_filter_requested") or ""),
        "crawl_policy_kind": str(source.get("crawl_policy_kind") or ""),
        "crawl_policy_reason": str(source.get("crawl_policy_reason") or ""),
        "crawl_cache_mode": str(source.get("crawl_cache_mode") or ""),
        "crawl_query_sha256_12": str(source.get("crawl_query_sha256_12") or ""),
        "crawl_query_chars": int(source.get("crawl_query_chars") or 0),
        "crawl_fallback_used": bool(source.get("crawl_fallback_used", False)),
        "crawl_fallback_reason": str(source.get("crawl_fallback_reason") or ""),
        "crawl_primary_status": str(source.get("crawl_primary_status") or ""),
        "crawl_fallback_status": str(source.get("crawl_fallback_status") or ""),
        "crawl_markdown_chars": int(source.get("crawl_markdown_chars") or 0),
        "crawl_max_chars": int(source.get("crawl_max_chars") or 0),
        "content_chars": len(content),
        "content_sha256_12": _sha256_text(content)[:12] if content else "",
        "content_preview": _bounded_preview(content, max_chars=SNIPPET_MAX_CHARS),
        "truncated": bool(source.get("truncated", False)),
        "raw_rank": source.get("raw_rank"),
        "reranked_rank": source.get("reranked_rank"),
        "rerank_score": source.get("rerank_score"),
        "rerank_bucket": str(source.get("rerank_bucket") or ""),
        "rerank_reason_codes": list(source.get("rerank_reason_codes") or []),
    }


def _openrouter_sources(data: dict[str, Any]) -> list[dict[str, Any]]:
    message = _message(data)
    sources: list[dict[str, Any]] = []
    for annotation in message.get("annotations") or []:
        if not isinstance(annotation, dict):
            continue
        citation = annotation.get("url_citation") or annotation.get("citation") or {}
        if not isinstance(citation, dict):
            continue
        url = str(citation.get("url") or citation.get("source_url") or "")
        content = str(citation.get("content") or citation.get("text") or "")
        sources.append(
            {
                "title": str(citation.get("title") or ""),
                "url": url,
                "domain": _domain(url) or "",
                "content_chars": len(content),
                "content_sha256_12": _sha256_text(content)[:12] if content else "",
                "content_preview": _bounded_preview(content, max_chars=SNIPPET_MAX_CHARS),
                "source_kind": "url_citation",
            }
        )
    if sources:
        return _dedupe_sources(sources)

    text = _extract_text(data)
    for url in _extract_urls(text):
        sources.append(
            {
                "title": "",
                "url": url,
                "domain": _domain(url) or "",
                "content_chars": 0,
                "content_sha256_12": "",
                "content_preview": "",
                "source_kind": "answer_url",
            }
        )
    return _dedupe_sources(sources)


def _estimate_openrouter_web_cost(
    client: OpenRouterClient,
    *,
    model: str,
    engine: str,
    usage: dict[str, Any],
) -> tuple[float | None, str]:
    direct = usage.get("cost")
    if isinstance(direct, (int, float)):
        return round(float(direct), 8), "provider_usage_cost"
    pricing = client.pricing_by_model.get(model) or {}
    prompt_price = pricing.get("prompt")
    completion_price = pricing.get("completion")
    input_tokens = _int_or_zero(usage.get("prompt_tokens", usage.get("input_tokens")))
    output_tokens = _int_or_zero(usage.get("completion_tokens", usage.get("output_tokens")))
    model_cost = None
    if prompt_price is not None and completion_price is not None:
        model_cost = (input_tokens * prompt_price) + (output_tokens * completion_price)
    web_requests = _web_search_requests(usage) or 0
    tool_cost = web_requests * WEB_SEARCH_TOOL_COST_USD if engine in {"exa", "parallel"} else 0.0
    if model_cost is None and web_requests <= 0:
        return None, "unavailable"
    total = (model_cost or 0.0) + tool_cost
    return round(total, 8), "openrouter_model_pricing_plus_server_tool_estimate"


def _local_request_signature(case: dict[str, Any], *, arm: str = "local") -> dict[str, Any]:
    return {
        "arm": str(arm or "local"),
        "user_query_sha256": _sha256_text(str(case.get("user_query") or "")),
    }


def _message(data: dict[str, Any]) -> dict[str, Any]:
    try:
        message = data["choices"][0]["message"]
    except Exception:
        return {}
    return message if isinstance(message, dict) else {}


def _extract_text(data: dict[str, Any]) -> str:
    content = _message(data).get("content")
    if isinstance(content, list):
        parts = [str(part.get("text") or "") for part in content if isinstance(part, dict)]
        return "\n".join(part for part in parts if part).strip()
    return str(content or "").strip()


def _finish_reason(data: dict[str, Any]) -> str | None:
    try:
        value = data["choices"][0].get("finish_reason")
    except Exception:
        return None
    return str(value) if value is not None else None


def _native_finish_reason(data: dict[str, Any]) -> str | None:
    try:
        value = data["choices"][0].get("native_finish_reason")
    except Exception:
        return None
    return str(value) if value is not None else None


def _compact_error(data: Any) -> str:
    if isinstance(data, dict):
        error = data.get("error")
        if isinstance(error, dict):
            return str(error.get("message") or error.get("code") or "")[:500]
        if isinstance(error, str):
            return error[:500]
    return ""


def _web_search_requests(usage: dict[str, Any]) -> int | None:
    server_tool_use = usage.get("server_tool_use")
    if isinstance(server_tool_use, dict):
        return _int_or_zero(server_tool_use.get("web_search_requests"))
    return None


def _web_search_requests_text(usage: dict[str, Any]) -> str:
    value = _web_search_requests(usage)
    return str(value) if value is not None else "n/a"


def _token_summary(usage: dict[str, Any]) -> str:
    input_tokens = _int_or_zero(usage.get("prompt_tokens", usage.get("input_tokens")))
    output_tokens = _int_or_zero(usage.get("completion_tokens", usage.get("output_tokens")))
    total_tokens = _int_or_zero(usage.get("total_tokens"))
    if input_tokens <= 0 and output_tokens <= 0 and total_tokens <= 0:
        return "n/a"
    total = total_tokens or (input_tokens + output_tokens)
    return f"{input_tokens}/{output_tokens}/{total}"


def _dedupe_sources(sources: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for source in sources:
        url = str(source.get("url") or "")
        if not url or url in seen:
            continue
        seen.add(url)
        deduped.append(source)
    return deduped


def _extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s)<>\"]+", str(text or ""))


def _domain(url: str) -> str | None:
    host = urlparse(str(url or "")).netloc.strip().lower()
    return host or None


def _bounded_preview(value: Any, *, max_chars: int) -> str:
    text = _redact_artifact_text(" ".join(str(value or "").split()))
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _redact_artifact_text(value: str) -> str:
    text = str(value or "")
    replacements = {
        "OPENROUTER_API_KEY": "OPENROUTER_KEY_REDACTED",
        "Authorization": "Auth header",
        "Bearer": "Token scheme",
        "sk-or-": "openrouter-key-prefix-redacted-",
        "api_key": "api-key",
        "data:image": "data-image",
        "data:application/pdf": "data-application-pdf",
        ";base64,": ";base64-redacted,",
    }
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)
    return text


def _sha256_text(value: str) -> str:
    if not value:
        return ""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"


def _source_domains_summary(sources: list[dict[str, Any]]) -> str:
    domains = [str(source.get("domain") or "") for source in sources if str(source.get("domain") or "")]
    if not domains:
        return "n/a"
    return _markdown_cell(", ".join(domains[:5]))


def _local_signal_summary(result: dict[str, Any]) -> str:
    local = result.get("local") or {}
    if not local:
        return "n/a"
    bits = [
        f"read_state={local.get('read_state')}",
        f"path={local.get('collection_path')}",
        f"kinds={','.join(local.get('used_content_kinds') or []) or 'none'}",
        f"chars={local.get('injected_chars')}",
    ]
    if local.get("search_profile"):
        bits.append(f"profile={local.get('search_profile')}")
    if local.get("query_plan_kind"):
        bits.append(f"plan={local.get('query_plan_kind')}")
    if local.get("secondary_query_count") is not None:
        bits.append(f"secondary={local.get('secondary_query_count')}")
    if local.get("searxng_profile_params_kind"):
        bits.append(f"searxng={local.get('searxng_profile_params_kind')}")
    if local.get("web_discovery_provider_effective"):
        discovery = str(local.get("web_discovery_provider_effective") or "")
        if local.get("web_discovery_external_used"):
            discovery += ":external"
        if local.get("web_discovery_external_error_kind"):
            discovery += f":{local.get('web_discovery_external_error_kind')}"
        bits.append(f"discovery={discovery}")
    if "rerank_applied" in local:
        bits.append(f"rerank={bool(local.get('rerank_applied', False))}")
        if local.get("rerank_policy"):
            bits.append(f"rerank_policy={local.get('rerank_policy')}")
    if local.get("crawl4ai_policy_kinds"):
        bits.append(f"crawl4ai={','.join(local.get('crawl4ai_policy_kinds') or [])}")
    if local.get("crawl4ai_fallback_used_count"):
        bits.append(f"crawl4ai_fallbacks={local.get('crawl4ai_fallback_used_count')}")
    if local.get("web_confidence_level"):
        bits.append(f"confidence={local.get('web_confidence_level')}:{local.get('web_confidence_score')}")
    if local.get("openrouter_fallback_state"):
        bits.append(f"openrouter_fallback={local.get('openrouter_fallback_state')}")
    if local.get("local_profiled_stub"):
        bits.append("stub=true")
    return _markdown_cell("; ".join(bits))


def _arm_label(result: dict[str, Any]) -> str:
    model = result.get("model")
    suffix = f"/{model}" if model else ""
    return f"{result.get('arm')}{suffix}"


def _markdown_cell(value: str) -> str:
    text = str(value or "").replace("|", "\\|").replace("\n", " ")
    return text if len(text) <= 180 else text[:179].rstrip() + "…"


def _markdown_inline(value: str) -> str:
    return str(value or "").replace("`", "'").replace("\n", " ")


def _markdown_quote(value: str) -> str:
    text = str(value or "").replace("\n", " ")
    return text.replace(">", "\\>")


def _int_or_zero(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
