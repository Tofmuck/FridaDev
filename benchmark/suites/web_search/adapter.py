from __future__ import annotations

import json
from pathlib import Path
from typing import Any


FIXTURE_PATH = Path("benchmark/suites/web_search/fixtures/cases.json")
LOCAL_BAD_ORDER_FIXTURE_PATH = Path("benchmark/suites/web_search/fixtures/local_bad_orders.json")
DEFAULT_ARMS = ["local", "local_profiled", "openrouter_exa", "openrouter_parallel"]
OPENROUTER_SEARCH_TOOL_TYPE = "openrouter:web_search"
DEFAULT_SEARCH_CONTEXT_SIZE = "low"
DEFAULT_MAX_RESULTS = 5
DEFAULT_MAX_TOTAL_RESULTS = 5
DEFAULT_MODEL = "openai/gpt-5.1"


def fixture_path(repo_root: Path) -> Path:
    return repo_root / FIXTURE_PATH


def local_bad_order_fixture_path(repo_root: Path) -> Path:
    return repo_root / LOCAL_BAD_ORDER_FIXTURE_PATH


def load_cases(repo_root: Path) -> list[dict[str, Any]]:
    raw = json.loads(fixture_path(repo_root).read_text(encoding="utf-8"))
    cases = [dict(item) for item in raw if isinstance(item, dict)]
    _validate_cases(cases)
    return cases


def load_local_bad_order_fixtures(repo_root: Path) -> list[dict[str, Any]]:
    raw = json.loads(local_bad_order_fixture_path(repo_root).read_text(encoding="utf-8"))
    fixtures = [dict(item) for item in raw if isinstance(item, dict)]
    case_ids = {case["id"] for case in load_cases(repo_root)}
    _validate_local_bad_order_fixtures(fixtures, known_case_ids=case_ids)
    return fixtures


def normalize_arms(values: list[str] | None) -> list[str]:
    raw = values or list(DEFAULT_ARMS)
    seen: set[str] = set()
    arms: list[str] = []
    allowed = {"local", "local_profiled", "openrouter_exa", "openrouter_parallel", "openrouter_native"}
    for value in raw:
        arm = str(value or "").strip()
        if not arm:
            continue
        if arm not in allowed:
            raise ValueError(f"unsupported_web_search_arm:{arm}")
        if arm in seen:
            continue
        seen.add(arm)
        arms.append(arm)
    if not arms:
        raise ValueError("at_least_one_web_search_arm_required")
    return arms


def openrouter_engine_for_arm(arm: str) -> str:
    mapping = {
        "openrouter_exa": "exa",
        "openrouter_parallel": "parallel",
        "openrouter_native": "native",
    }
    return mapping[arm]


def build_openrouter_payload(
    *,
    case: dict[str, Any],
    model: str,
    engine: str,
    max_results: int = DEFAULT_MAX_RESULTS,
    max_total_results: int = DEFAULT_MAX_TOTAL_RESULTS,
    search_context_size: str = DEFAULT_SEARCH_CONTEXT_SIZE,
) -> dict[str, Any]:
    parameters: dict[str, Any] = {
        "engine": engine,
        "max_results": int(max_results),
        "max_total_results": int(max_total_results),
        "search_context_size": str(search_context_size),
    }
    domains = [str(item).strip() for item in case.get("must_include_domains") or [] if str(item).strip()]
    if domains and str(case.get("category") or "") in {"tech_doc_officielle", "url_explicite"}:
        parameters["allowed_domains"] = domains
    return {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "Tu es un banc de comparaison web FridaDev. "
                    "Utilise l'outil web_search si une information externe est nécessaire. "
                    "Réponds en français, cite les URLs utiles, distingue source officielle, source secondaire et incertitude. "
                    "Ne prétends pas avoir lu une page entière si l'outil ne fournit que des extraits."
                ),
            },
            {"role": "user", "content": str(case.get("user_query") or "")},
        ],
        "tools": [{"type": OPENROUTER_SEARCH_TOOL_TYPE, "parameters": parameters}],
        "temperature": 0,
        "top_p": 1.0,
        "max_tokens": 900,
        "metadata": {
            "frida_benchmark_suite": "web_search",
            "frida_benchmark_case_id": str(case.get("id") or ""),
            "frida_benchmark_arm": f"openrouter_{engine}",
        },
        "trace": {
            "trace_name": "FridaDev Benchmark",
            "generation_name": f"FridaDev / Benchmark / Web Search / {engine}",
        },
    }


def dry_run_source(case: dict[str, Any], *, arm: str) -> dict[str, Any]:
    domain = next((str(item).strip() for item in case.get("must_include_domains") or [] if str(item).strip()), "example.invalid")
    return {
        "title": f"Dry-run source for {case.get('id')}",
        "url": f"https://{domain}/fridadev-benchmark-dry-run/{arm}",
        "domain": domain,
        "content_preview": "Source synthétique de dry-run, sans contenu externe réel.",
        "source_kind": "dry_run_fixture",
    }


def _validate_cases(cases: list[dict[str, Any]]) -> None:
    ids: set[str] = set()
    for case in cases:
        case_id = str(case.get("id") or "").strip()
        if not case_id:
            raise ValueError("web_search_case_missing_id")
        if case_id in ids:
            raise ValueError(f"web_search_case_duplicate_id:{case_id}")
        ids.add(case_id)
        for key in ("title", "user_query", "category", "expected_source_kinds"):
            if not case.get(key):
                raise ValueError(f"web_search_case_missing_{key}:{case_id}")
        if not isinstance(case.get("expected_source_kinds"), list):
            raise ValueError(f"web_search_case_invalid_expected_source_kinds:{case_id}")


def _validate_local_bad_order_fixtures(
    fixtures: list[dict[str, Any]],
    *,
    known_case_ids: set[str],
) -> None:
    if not fixtures:
        raise ValueError("web_search_local_bad_order_fixtures_empty")
    seen: set[str] = set()
    for fixture in fixtures:
        case_id = str(fixture.get("case_id") or "").strip()
        if not case_id:
            raise ValueError("web_search_local_bad_order_fixture_missing_case_id")
        if case_id in seen:
            raise ValueError(f"web_search_local_bad_order_fixture_duplicate:{case_id}")
        if case_id not in known_case_ids:
            raise ValueError(f"web_search_local_bad_order_fixture_unknown_case:{case_id}")
        seen.add(case_id)
        if not str(fixture.get("target_profile") or "").strip():
            raise ValueError(f"web_search_local_bad_order_fixture_missing_profile:{case_id}")
        if not isinstance(fixture.get("results"), list) or not fixture.get("results"):
            raise ValueError(f"web_search_local_bad_order_fixture_missing_results:{case_id}")
        for result in fixture.get("results") or []:
            if not isinstance(result, dict):
                raise ValueError(f"web_search_local_bad_order_fixture_invalid_result:{case_id}")
            for key in ("rank", "title", "url", "domain", "problem"):
                if result.get(key) in (None, ""):
                    raise ValueError(f"web_search_local_bad_order_fixture_missing_{key}:{case_id}")
