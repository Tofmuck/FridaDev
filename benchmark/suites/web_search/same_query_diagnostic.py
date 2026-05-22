from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import time
from typing import Any
from urllib.parse import urlparse

import requests

from benchmark.core.campaign import sha256_text, utc_timestamp, write_json
from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.web_search import adapter
from benchmark.suites.web_search import campaign as web_campaign


DEFAULT_OUTPUT_DIR = Path("/tmp/fridadev-web-search-same-query-diagnostic")
DEFAULT_SEARXNG_URL = "http://127.0.0.1:8092"

DIAGNOSTIC_CASES: list[dict[str, Any]] = [
    {
        "id": "recent_ai_policy_news",
        "title": "Actualite recente IA",
        "query": "régulation intelligence artificielle Europe 2026 sources changements récents",
        "expected_domains": ["ec.europa.eu", "artificialintelligenceact.eu", "europarl.europa.eu", "consilium.europa.eu"],
        "noise_domains": ["outlook.com", "zhihu.com", "forum.cgsecurity.org"],
    },
    {
        "id": "official_openrouter_server_tools",
        "title": "Documentation technique OpenRouter",
        "query": "OpenRouter web_search documentation coût paramètres prix",
        "expected_domains": ["openrouter.ai"],
        "noise_domains": ["datacamp.com", "linkedin.com", "justgeek.fr"],
    },
    {
        "id": "conceptual_philosophy_search",
        "title": "Derrida trace sources",
        "query": "trace Derrida sources primaires encyclopédiques commentaires académiques",
        "expected_domains": ["plato.stanford.edu", "jstor.org", "wikipedia.org", "openedition.org", "cairn.info"],
        "noise_domains": ["trace-colmar.fr", "larousse.fr", "cnrtl.fr", "geoportail.gouv.fr", "reddit.com", "medium.com"],
    },
    {
        "id": "french_admin_service_public",
        "title": "Renouvellement CNI",
        "query": "renouveler carte nationale identité française procédure officielle service public ANTS",
        "expected_domains": ["service-public.fr", "service-public.gouv.fr", "ants.gouv.fr", "passeport.ants.gouv.fr"],
        "noise_domains": ["leconjugueur.lefigaro.fr", "conjugaison.bescherelle.com", "larousse.fr", "nouvelobs.com"],
    },
]


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the same-query web search diagnostic.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--searxng-url", default=os.environ.get("SEARXNG_URL") or DEFAULT_SEARXNG_URL)
    parser.add_argument("--model", default=adapter.DEFAULT_MODEL)
    parser.add_argument("--max-results", type=int, default=adapter.DEFAULT_MAX_RESULTS)
    parser.add_argument("--max-total-results", type=int, default=adapter.DEFAULT_MAX_TOTAL_RESULTS)
    parser.add_argument("--search-context-size", default=adapter.DEFAULT_SEARCH_CONTEXT_SIZE)
    parser.add_argument("--timeout-s", type=int, default=90)
    parser.add_argument("--base-url", default=None)
    args = parser.parse_args()

    output_dir = Path(args.output_dir).resolve()
    client = OpenRouterClient.from_env(
        base_url=args.base_url,
        title="FridaDev/Benchmark/WebSearchSameQuery",
    )
    run_same_query_diagnostic(
        output_dir=output_dir,
        client=client,
        searxng_url=str(args.searxng_url),
        model=str(args.model),
        max_results=int(args.max_results),
        max_total_results=int(args.max_total_results),
        search_context_size=str(args.search_context_size),
        timeout_s=int(args.timeout_s),
    )
    print(f"wrote {output_dir / 'same-query-diagnostic.json'}")
    print(f"wrote {output_dir / 'searxng.md'}")
    print(f"wrote {output_dir / 'openrouter-exa.md'}")
    print(f"wrote {output_dir / 'openrouter-parallel.md'}")
    print(f"wrote {output_dir / 'comparison.md'}")
    return 0


def run_same_query_diagnostic(
    *,
    output_dir: Path,
    client: OpenRouterClient,
    searxng_url: str,
    model: str,
    max_results: int = adapter.DEFAULT_MAX_RESULTS,
    max_total_results: int = adapter.DEFAULT_MAX_TOTAL_RESULTS,
    search_context_size: str = adapter.DEFAULT_SEARCH_CONTEXT_SIZE,
    timeout_s: int = 90,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    for case in DIAGNOSTIC_CASES:
        case_result = {
            "case": _public_case(case),
            "arms": [
                _run_searxng_case(
                    case,
                    searxng_url=searxng_url,
                    max_results=max_results,
                    timeout_s=min(timeout_s, 15),
                ),
                _run_openrouter_case(
                    case,
                    client=client,
                    model=model,
                    engine="exa",
                    max_results=max_results,
                    max_total_results=max_total_results,
                    search_context_size=search_context_size,
                    timeout_s=timeout_s,
                ),
                _run_openrouter_case(
                    case,
                    client=client,
                    model=model,
                    engine="parallel",
                    max_results=max_results,
                    max_total_results=max_total_results,
                    search_context_size=search_context_size,
                    timeout_s=timeout_s,
                ),
            ],
        }
        results.append(case_result)

    diagnostic = {
        "created_at_utc": utc_timestamp(),
        "suite": "web_search_same_query_diagnostic",
        "query_parity": {
            "searxng": "strict_q_parameter",
            "openrouter": "prompt_locked_but_tool_query_not_exposed_by_api",
        },
        "secrets_written": False,
        "production_runtime_changed": False,
        "cases": results,
    }
    write_json(output_dir / "same-query-diagnostic.json", diagnostic)
    (output_dir / "searxng.md").write_text(_render_arm_report(diagnostic, arm="searxng"), encoding="utf-8")
    (output_dir / "openrouter-exa.md").write_text(_render_arm_report(diagnostic, arm="openrouter_exa"), encoding="utf-8")
    (output_dir / "openrouter-parallel.md").write_text(
        _render_arm_report(diagnostic, arm="openrouter_parallel"),
        encoding="utf-8",
    )
    (output_dir / "comparison.md").write_text(_render_comparison(diagnostic), encoding="utf-8")
    return diagnostic


def build_same_query_openrouter_payload(
    *,
    case: dict[str, Any],
    model: str,
    engine: str,
    max_results: int = adapter.DEFAULT_MAX_RESULTS,
    max_total_results: int = adapter.DEFAULT_MAX_TOTAL_RESULTS,
    search_context_size: str = adapter.DEFAULT_SEARCH_CONTEXT_SIZE,
) -> dict[str, Any]:
    query = str(case.get("query") or "")
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a web search diagnostic runner. Search the web using the exact query string "
                    "provided by the user. Do not rewrite, translate, broaden, narrow, or add domains. "
                    "Return the top useful URLs with titles and very short relevance notes. "
                    "If the tool does not expose the exact query it used, say that limitation."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Search the web using exactly this query string, without rewriting it:\n"
                    f"{query}\n\n"
                    "Return top 5 URLs, domains, titles, and a short note for official/source quality."
                ),
            },
        ],
        "tools": [
            {
                "type": adapter.OPENROUTER_SEARCH_TOOL_TYPE,
                "parameters": {
                    "engine": engine,
                    "max_results": int(max_results),
                    "max_total_results": int(max_total_results),
                    "search_context_size": str(search_context_size),
                },
            }
        ],
        "temperature": 0,
        "top_p": 1.0,
        "max_tokens": 700,
        "metadata": {
            "frida_benchmark_suite": "web_search_same_query_diagnostic",
            "frida_benchmark_case_id": str(case.get("id") or ""),
            "frida_benchmark_engine": engine,
            "frida_same_query_sha256": sha256_text(query),
        },
    }


def _run_searxng_case(
    case: dict[str, Any],
    *,
    searxng_url: str,
    max_results: int,
    timeout_s: int,
) -> dict[str, Any]:
    query = str(case.get("query") or "")
    start = time.perf_counter()
    try:
        response = requests.get(
            f"{searxng_url.rstrip('/')}/search",
            params={"q": query, "format": "json", "language": "fr-FR", "safesearch": "0"},
            timeout=timeout_s,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json() if response.content else {}
        sources = [_searxng_source(item, case=case) for item in (data.get("results") or [])[:max_results]]
        return _with_arm_quality(
            {
                "arm": "searxng",
                "engine": "searxng",
                "ok": response.status_code < 400,
                "status": str(response.status_code),
                "elapsed_ms": round(elapsed_ms, 3),
                "error": None if response.status_code < 400 else response.text[:300],
                "cost_estimate_usd": None,
                "query_exactness": "strict_q_parameter",
                "sources": sources,
                "answer_preview": "",
            },
            case=case,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return _with_arm_quality(
            {
                "arm": "searxng",
                "engine": "searxng",
                "ok": False,
                "status": "error",
                "elapsed_ms": round(elapsed_ms, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                "cost_estimate_usd": None,
                "query_exactness": "strict_q_parameter",
                "sources": [],
                "answer_preview": "",
            },
            case=case,
        )


def _run_openrouter_case(
    case: dict[str, Any],
    *,
    client: OpenRouterClient,
    model: str,
    engine: str,
    max_results: int,
    max_total_results: int,
    search_context_size: str,
    timeout_s: int,
) -> dict[str, Any]:
    payload = build_same_query_openrouter_payload(
        case=case,
        model=model,
        engine=engine,
        max_results=max_results,
        max_total_results=max_total_results,
        search_context_size=search_context_size,
    )
    start = time.perf_counter()
    try:
        response = requests.post(
            f"{client.config.base_url}/chat/completions",
            json=payload,
            headers=client._headers(caller=f"benchmark_web_search_same_query_{engine}"),  # noqa: SLF001
            timeout=timeout_s,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000
        data = response.json() if response.content else {}
        usage = dict(data.get("usage") or {}) if isinstance(data, dict) else {}
        sources = [
            _classified_source(source, case=case)
            for source in web_campaign._openrouter_sources(data)[:max_results]
        ]
        cost, cost_source = web_campaign._estimate_openrouter_web_cost(
            client,
            model=model,
            engine=engine,
            usage=usage,
        )
        error = None if response.status_code < 400 else web_campaign._compact_error(data) or response.text[:300]
        return _with_arm_quality(
            {
                "arm": f"openrouter_{engine}",
                "engine": engine,
                "model": model,
                "ok": response.status_code < 400,
                "status": str(response.status_code),
                "elapsed_ms": round(elapsed_ms, 3),
                "error": error,
                "cost_estimate_usd": cost,
                "cost_estimate_source": cost_source,
                "query_exactness": "prompt_locked_tool_query_not_exposed",
                "usage": usage,
                "sources": sources,
                "answer_preview": web_campaign._bounded_preview(
                    web_campaign._extract_text(data),
                    max_chars=web_campaign.ANSWER_PREVIEW_CHARS,
                ),
            },
            case=case,
        )
    except Exception as exc:
        elapsed_ms = (time.perf_counter() - start) * 1000
        return _with_arm_quality(
            {
                "arm": f"openrouter_{engine}",
                "engine": engine,
                "model": model,
                "ok": False,
                "status": "error",
                "elapsed_ms": round(elapsed_ms, 3),
                "error": f"{type(exc).__name__}: {str(exc)[:300]}",
                "cost_estimate_usd": None,
                "cost_estimate_source": "exception",
                "query_exactness": "prompt_locked_tool_query_not_exposed",
                "usage": {},
                "sources": [],
                "answer_preview": "",
            },
            case=case,
        )


def _searxng_source(item: dict[str, Any], *, case: dict[str, Any]) -> dict[str, Any]:
    url = str(item.get("url") or "")
    return _classified_source(
        {
            "title": str(item.get("title") or ""),
            "url": url,
            "domain": _domain(url),
            "content_preview": web_campaign._bounded_preview(
                item.get("content") or "",
                max_chars=web_campaign.SNIPPET_MAX_CHARS,
            ),
            "source_kind": "searxng_result",
        },
        case=case,
    )


def _classified_source(source: dict[str, Any], *, case: dict[str, Any]) -> dict[str, Any]:
    copied = dict(source)
    domain = str(copied.get("domain") or _domain(str(copied.get("url") or "")) or "")
    copied["domain"] = domain
    copied["quality_hint"] = _quality_hint(domain, copied, case=case)
    return copied


def _with_arm_quality(result: dict[str, Any], *, case: dict[str, Any]) -> dict[str, Any]:
    sources = list(result.get("sources") or [])
    result["expected_domain_hits"] = _expected_domain_hits(sources, case=case)
    result["noise_domain_hits"] = _noise_domain_hits(sources, case=case)
    result["official_like_count"] = sum(1 for source in sources if source.get("quality_hint") in {"expected_official", "official_like"})
    return result


def _quality_hint(domain: str, source: dict[str, Any], *, case: dict[str, Any]) -> str:
    domain = domain.lower()
    url = str(source.get("url") or "").lower()
    expected = [str(item).lower() for item in case.get("expected_domains") or []]
    noise = [str(item).lower() for item in case.get("noise_domains") or []]
    if any(_domain_matches(domain, expected_domain) for expected_domain in expected):
        return "expected_official"
    if any(_domain_matches(domain, noise_domain) for noise_domain in noise):
        return "known_noise"
    if (
        domain.endswith(".gouv.fr")
        or domain.endswith(".gov")
        or "europa.eu" in domain
        or domain in {"openrouter.ai", "docs.openrouter.ai", "react.dev", "learn.microsoft.com"}
        or "/docs" in url
        or "/documentation" in url
        or "/reference" in url
        or "/api/" in url
    ):
        return "official_like"
    if any(marker in domain for marker in ("conjug", "larousse", "wiktionary", "reddit", "medium")):
        return "likely_noise"
    return "secondary_or_unknown"


def _expected_domain_hits(sources: list[dict[str, Any]], *, case: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    expected = [str(item).lower() for item in case.get("expected_domains") or []]
    for source in sources:
        domain = str(source.get("domain") or "").lower()
        for expected_domain in expected:
            if _domain_matches(domain, expected_domain) and expected_domain not in hits:
                hits.append(expected_domain)
    return hits


def _noise_domain_hits(sources: list[dict[str, Any]], *, case: dict[str, Any]) -> list[str]:
    hits: list[str] = []
    noise = [str(item).lower() for item in case.get("noise_domains") or []]
    for source in sources:
        domain = str(source.get("domain") or "").lower()
        for noise_domain in noise:
            if _domain_matches(domain, noise_domain) and noise_domain not in hits:
                hits.append(noise_domain)
    return hits


def _domain_matches(domain: str, expected_domain: str) -> bool:
    domain = domain.lower().lstrip(".")
    expected_domain = expected_domain.lower().lstrip(".")
    return domain == expected_domain or domain.endswith("." + expected_domain)


def _public_case(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(case.get("id") or ""),
        "title": str(case.get("title") or ""),
        "query": str(case.get("query") or ""),
        "query_sha256_12": sha256_text(str(case.get("query") or ""))[:12],
        "expected_domains": list(case.get("expected_domains") or []),
        "noise_domains": list(case.get("noise_domains") or []),
    }


def _render_arm_report(diagnostic: dict[str, Any], *, arm: str) -> str:
    lines = [
        f"# Same-query diagnostic - {arm.replace('_', '-')}",
        "",
        f"- Created UTC: `{diagnostic.get('created_at_utc')}`",
        "- Runtime FridaDev modified: `False`",
        f"- Query parity: `{(diagnostic.get('query_parity') or {}).get('openrouter' if arm.startswith('openrouter') else 'searxng')}`",
        "",
    ]
    for case_result in diagnostic.get("cases") or []:
        case = case_result.get("case") or {}
        result = _find_arm(case_result, arm)
        lines.extend(
            [
                f"## {case.get('id')} - {case.get('title')}",
                "",
                f"- Exact query: `{case.get('query')}`",
            ]
        )
        if not result:
            lines.extend(["- Status: `not_run`", ""])
            continue
        lines.extend(_result_block(result))
    return "\n".join(lines)


def _render_comparison(diagnostic: dict[str, Any]) -> str:
    lines = [
        "# Same-query diagnostic - comparison",
        "",
        f"- Created UTC: `{diagnostic.get('created_at_utc')}`",
        "- Scope: benchmark-only, no `/api/chat` or runtime FridaDev change.",
        "- SearXNG query parity: strict `q` parameter.",
        "- OpenRouter query parity: prompt-locked only; the API does not expose the exact search query sent to Exa/Parallel.",
        "",
        "## Matrix",
        "",
        "| Case | SearXNG | Exa | Parallel | Diagnostic hint |",
        "| --- | --- | --- | --- | --- |",
    ]
    for case_result in diagnostic.get("cases") or []:
        case = case_result.get("case") or {}
        searxng = _find_arm(case_result, "searxng") or {}
        exa = _find_arm(case_result, "openrouter_exa") or {}
        parallel = _find_arm(case_result, "openrouter_parallel") or {}
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{case.get('id')}`",
                    _score_cell(searxng),
                    _score_cell(exa),
                    _score_cell(parallel),
                    _diagnostic_hint(searxng, exa, parallel),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Interpretation rules",
            "",
            "- If SearXNG does as well as Exa/Parallel with the exact query, the problem is more likely FridaDev reformulation, specialized query planning, profiled SearXNG parameters, or rerank/crawl selection.",
            "- If SearXNG misses expected domains while Exa finds them, the problem is more likely SearXNG index/ranking for that query.",
            "- If all arms miss, the fixed query itself is probably weak or the target information is hard to retrieve.",
            "- Because OpenRouter does not expose the exact delegated search query, this diagnostic cannot prove strict parity for Exa/Parallel.",
            "",
            "## Per-case details",
            "",
        ]
    )
    for case_result in diagnostic.get("cases") or []:
        case = case_result.get("case") or {}
        lines.extend(
            [
                f"### {case.get('id')}",
                "",
                f"- Exact query: `{case.get('query')}`",
            ]
        )
        for result in case_result.get("arms") or []:
            lines.append(
                f"- `{result.get('arm')}`: expected_hits=`{','.join(result.get('expected_domain_hits') or []) or 'none'}`, "
                f"noise_hits=`{','.join(result.get('noise_domain_hits') or []) or 'none'}`, "
                f"latency=`{float(result.get('elapsed_ms') or 0.0):.0f} ms`, "
                f"cost=`{_format_cost(result.get('cost_estimate_usd'))}`"
            )
        lines.append("")
    return "\n".join(lines)


def _result_block(result: dict[str, Any]) -> list[str]:
    lines = [
        f"- Engine: `{result.get('engine')}`",
        f"- Status: `{result.get('status')}` (`{'ok' if result.get('ok') else 'error'}`)",
        f"- Query exactness: `{result.get('query_exactness')}`",
        f"- Latency: `{float(result.get('elapsed_ms') or 0.0):.0f} ms`",
        f"- Cost estimate: `{_format_cost(result.get('cost_estimate_usd'))}`",
        f"- Expected domain hits: `{','.join(result.get('expected_domain_hits') or []) or 'none'}`",
        f"- Noise domain hits: `{','.join(result.get('noise_domain_hits') or []) or 'none'}`",
        "- Top sources:",
    ]
    if result.get("error"):
        lines.append(f"  - error: `{web_campaign._markdown_inline(str(result.get('error') or ''))}`")
    for source in (result.get("sources") or [])[:5]:
        title = web_campaign._markdown_inline(str(source.get("title") or "source"))
        url = str(source.get("url") or "")
        domain = str(source.get("domain") or _domain(url) or "domain_unknown")
        preview = web_campaign._markdown_inline(str(source.get("content_preview") or ""))
        quality = str(source.get("quality_hint") or "unknown")
        parts = [f"`{domain}`", url, f"quality={quality}"]
        if preview:
            parts.append(f"excerpt: {preview}")
        lines.append(f"  - {title}: " + " ; ".join(parts))
    if result.get("answer_preview"):
        lines.extend(["- Answer preview:", "", f"> {web_campaign._markdown_quote(str(result.get('answer_preview') or ''))}", ""])
    lines.append("")
    return lines


def _score_cell(result: dict[str, Any]) -> str:
    expected = len(result.get("expected_domain_hits") or [])
    noise = len(result.get("noise_domain_hits") or [])
    status = "ok" if result.get("ok") else "error"
    domains = [str(source.get("domain") or "") for source in (result.get("sources") or [])[:3] if source.get("domain")]
    return web_campaign._markdown_cell(
        f"{status}; expected={expected}; noise={noise}; top={','.join(domains) or 'none'}"
    )


def _diagnostic_hint(searxng: dict[str, Any], exa: dict[str, Any], parallel: dict[str, Any]) -> str:
    s_hits = len(searxng.get("expected_domain_hits") or [])
    e_hits = len(exa.get("expected_domain_hits") or [])
    p_hits = len(parallel.get("expected_domain_hits") or [])
    s_noise = len(searxng.get("noise_domain_hits") or [])
    if s_hits >= max(e_hits, p_hits) and s_hits > 0:
        return "SearXNG can find target with same query; suspect FridaDev query/profile path before index."
    if s_hits == 0 and max(e_hits, p_hits) > 0:
        return "OpenRouter finds expected domains where SearXNG does not; suspect SearXNG index/ranking."
    if s_hits == 0 and e_hits == 0 and p_hits == 0:
        return "All arms miss expected domains; suspect query weakness or hard target."
    if s_noise > 0 and max(e_hits, p_hits) > s_hits:
        return "SearXNG shows known noise while OpenRouter improves; suspect SearXNG ranking."
    return "Mixed signal; inspect source list."


def _format_cost(value: Any) -> str:
    if isinstance(value, (int, float)):
        return f"${float(value):.6f}"
    return "n/a"


def _find_arm(case_result: dict[str, Any], arm: str) -> dict[str, Any] | None:
    for result in case_result.get("arms") or []:
        if result.get("arm") == arm:
            return result
    return None


def _domain(url: str) -> str:
    return urlparse(str(url or "")).netloc.strip().lower()


if __name__ == "__main__":
    raise SystemExit(main())
