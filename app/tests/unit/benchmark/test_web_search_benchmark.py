from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import ModuleType


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.core.campaign import CampaignConfig
from benchmark.run_benchmark import DEFAULT_WEB_SEARCH_MODELS
from benchmark.suites.web_search import adapter as web_adapter
from benchmark.suites.web_search import campaign as web_campaign
from benchmark.suites.web_search import same_query_diagnostic


class WebSearchBenchmarkSuiteTests(unittest.TestCase):
    def test_default_web_search_models_and_arms_are_bounded(self) -> None:
        self.assertEqual(DEFAULT_WEB_SEARCH_MODELS, ["openai/gpt-5.1"])
        self.assertEqual(web_adapter.DEFAULT_ARMS, ["local", "local_profiled", "openrouter_exa", "openrouter_parallel"])
        self.assertEqual(web_adapter.DEFAULT_MAX_RESULTS, 5)
        self.assertEqual(web_adapter.DEFAULT_MAX_TOTAL_RESULTS, 5)
        self.assertEqual(web_adapter.DEFAULT_SEARCH_CONTEXT_SIZE, "low")

    def test_web_search_fixtures_cover_product_matrix(self) -> None:
        cases = web_adapter.load_cases(REPO_ROOT)
        self.assertEqual(len(cases), 5)
        categories = {case["category"] for case in cases}
        self.assertEqual(
            categories,
            {
                "actualite_recente",
                "tech_doc_officielle",
                "url_explicite",
                "philosophie_academique",
                "institutionnel_francais",
            },
        )
        for case in cases:
            self.assertTrue(case["id"])
            self.assertTrue(case["title"])
            self.assertTrue(case["user_query"])
            self.assertTrue(case["expected_source_kinds"])
            self.assertIsInstance(case.get("must_include_domains"), list)

    def test_openrouter_payload_uses_server_tool_not_deprecated_web_paths(self) -> None:
        case = next(case for case in web_adapter.load_cases(REPO_ROOT) if case["id"] == "official_openrouter_server_tools")
        payload = web_adapter.build_openrouter_payload(case=case, model="openai/gpt-5.1", engine="exa")
        dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertEqual(payload["model"], "openai/gpt-5.1")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["top_p"], 1.0)
        self.assertEqual(payload["tools"][0]["type"], "openrouter:web_search")
        self.assertEqual(payload["tools"][0]["parameters"]["engine"], "exa")
        self.assertEqual(payload["tools"][0]["parameters"]["max_results"], 5)
        self.assertEqual(payload["tools"][0]["parameters"]["max_total_results"], 5)
        self.assertEqual(payload["tools"][0]["parameters"]["search_context_size"], "low")
        self.assertEqual(payload["tools"][0]["parameters"]["allowed_domains"], ["openrouter.ai"])
        self.assertNotIn('"plugins"', dumped)
        self.assertNotIn(":online", dumped)

    def test_openrouter_parallel_payload_can_be_raised_to_medium_later(self) -> None:
        case = web_adapter.load_cases(REPO_ROOT)[0]
        payload = web_adapter.build_openrouter_payload(
            case=case,
            model="openai/gpt-5.1",
            engine="parallel",
            max_results=5,
            max_total_results=5,
            search_context_size="medium",
        )

        parameters = payload["tools"][0]["parameters"]
        self.assertEqual(parameters["engine"], "parallel")
        self.assertEqual(parameters["search_context_size"], "medium")
        self.assertNotIn("allowed_domains", parameters)

    def test_dry_run_campaign_writes_redacted_artifacts_without_provider_calls(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = CampaignConfig(
                campaign_id="web-search-dry",
                suite="web_search",
                repo_root=REPO_ROOT,
                output_dir=tmp_path / "results",
                models=["openai/gpt-5.1"],
                dry_run=True,
                timeout_s=1,
            )

            result = web_campaign.run_web_search_campaign(
                config=config,
                client=None,
                arms=web_adapter.DEFAULT_ARMS,
            )

            json_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
            jsonl = Path(result["jsonl_path"]).read_text(encoding="utf-8")
            system_paths = {key: Path(value) for key, value in result["system_markdown_paths"].items()}
            system_markdowns = {key: path.read_text(encoding="utf-8") for key, path in system_paths.items()}
            combined = "\n".join(
                [
                    json.dumps(json_payload, ensure_ascii=False),
                    markdown,
                    jsonl,
                    *system_markdowns.values(),
                ]
            )

            self.assertFalse(json_payload["production_runtime_changed"])
            self.assertFalse(json_payload["secrets_written"])
            self.assertTrue(json_payload["human_decision_required"])
            self.assertEqual(json_payload["case_count"], 5)
            self.assertEqual(json_payload["arms"], web_adapter.DEFAULT_ARMS)
            self.assertIn("Grille d'évaluation humaine", markdown)
            self.assertIn("openrouter:web_search", markdown)
            self.assertIn("local_profiled", markdown)
            self.assertIn("web_search_requests", json.dumps(json_payload, ensure_ascii=False))
            self.assertEqual(set(system_paths), {"local", "local_profiled", "openrouter_exa", "openrouter_parallel"})
            self.assertEqual(system_paths["local"].name, "local.md")
            self.assertEqual(system_paths["local_profiled"].name, "local-profiled.md")
            self.assertEqual(system_paths["openrouter_exa"].name, "openrouter-exa.md")
            self.assertEqual(system_paths["openrouter_parallel"].name, "openrouter-parallel.md")
            case_ids = [case["id"] for case in web_adapter.load_cases(REPO_ROOT)]
            for text in system_markdowns.values():
                positions = [text.find(f"## {case_id} -") for case_id in case_ids]
                self.assertTrue(all(position >= 0 for position in positions), positions)
                self.assertEqual(positions, sorted(positions))
            self.assertIn("read_state", system_markdowns["local"])
            self.assertIn("search_profile", system_markdowns["local_profiled"])
            self.assertIn("query_plan_kind", system_markdowns["local_profiled"])
            self.assertIn("searxng_profile_params_kind", system_markdowns["local_profiled"])
            self.assertIn("web_confidence_level", system_markdowns["local_profiled"])
            self.assertIn("openrouter_fallback_used", system_markdowns["local_profiled"])
            self.assertIn("Requêtes web OpenRouter", system_markdowns["openrouter_exa"])
            self.assertIn("Requêtes web OpenRouter", system_markdowns["openrouter_parallel"])
            for forbidden in (
                "OPENROUTER_API_KEY",
                "Authorization",
                "Bearer ",
                "sk-or-",
                "data:image",
                "data:application/pdf",
                ";base64,",
            ):
                self.assertNotIn(forbidden, combined)

    def test_benchmark_previews_redact_secret_placeholders_from_sources(self) -> None:
        preview = web_campaign._bounded_preview(
            "headers: Authorization: Bearer <OPENROUTER_API_KEY> sk-or-demo api_key data:image/png;base64,",
            max_chars=240,
        )

        for forbidden in (
            "OPENROUTER_API_KEY",
            "Authorization",
            "Bearer ",
            "sk-or-",
            "api_key",
            "data:image",
            ";base64,",
        ):
            self.assertNotIn(forbidden, preview)
        self.assertIn("OPENROUTER_KEY_REDACTED", preview)

    def test_same_query_diagnostic_cases_are_search_only_and_fixed(self) -> None:
        case_ids = {case["id"] for case in same_query_diagnostic.DIAGNOSTIC_CASES}

        self.assertEqual(
            case_ids,
            {
                "recent_ai_policy_news",
                "official_openrouter_server_tools",
                "conceptual_philosophy_search",
                "french_admin_service_public",
            },
        )
        self.assertNotIn("explicit_url_reading_contract", case_ids)
        for case in same_query_diagnostic.DIAGNOSTIC_CASES:
            self.assertTrue(case["query"])
            self.assertTrue(case["expected_domains"])

    def test_same_query_openrouter_payload_locks_query_without_domain_allowlist(self) -> None:
        case = next(
            case
            for case in same_query_diagnostic.DIAGNOSTIC_CASES
            if case["id"] == "french_admin_service_public"
        )

        payload = same_query_diagnostic.build_same_query_openrouter_payload(
            case=case,
            model="openai/gpt-5.1",
            engine="exa",
        )
        dumped = json.dumps(payload, ensure_ascii=False, sort_keys=True)

        self.assertIn(case["query"], dumped)
        self.assertIn("without rewriting", dumped)
        self.assertEqual(payload["tools"][0]["type"], "openrouter:web_search")
        self.assertEqual(payload["tools"][0]["parameters"]["engine"], "exa")
        self.assertNotIn("allowed_domains", payload["tools"][0]["parameters"])

    def test_unknown_arm_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            web_adapter.normalize_arms(["local", "plugins_web"])

    def test_local_profiled_arm_exposes_lot7_query_searxng_rerank_crawl_and_confidence_shape(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = CampaignConfig(
                campaign_id="web-search-local-profiled-dry",
                suite="web_search",
                repo_root=REPO_ROOT,
                output_dir=tmp_path / "results",
                models=["openai/gpt-5.1"],
                dry_run=True,
                timeout_s=1,
            )

            campaign = web_campaign.build_web_search_campaign(
                config=config,
                client=None,
                arms=["local", "local_profiled"],
            )

        self.assertEqual(campaign["arms"], ["local", "local_profiled"])
        first_case_arms = campaign["results"][0]["arms"]
        self.assertEqual([result["arm"] for result in first_case_arms], ["local", "local_profiled"])
        profiled = first_case_arms[1]
        self.assertEqual(
            profiled["mode"],
            "local_profiled_specialized_queries_searxng_params_rerank_crawl4ai_policy_confidence_observability",
        )
        self.assertEqual(
            profiled["engine"],
            "searxng_crawl4ai_profiled_queries_params_rerank_crawl_policy_confidence",
        )
        self.assertFalse(profiled["local"]["local_profiled_stub"])
        self.assertEqual(profiled["local"]["search_profile"], "stub_not_implemented")
        self.assertEqual(profiled["local"]["query_plan_kind"], "dry_run")
        self.assertEqual(profiled["local"]["secondary_query_count"], 0)
        self.assertEqual(profiled["local"]["searxng_profile_params_kind"], "dry_run")
        self.assertEqual(profiled["local"]["searxng_profile_params_policy"], "dry_run")
        self.assertEqual(profiled["local"]["searxng_categories"], [])
        self.assertEqual(profiled["local"]["searxng_engines"], [])
        self.assertFalse(profiled["local"]["rerank_applied"])
        self.assertEqual(profiled["local"]["rerank_policy"], "dry_run")
        self.assertEqual(profiled["local"]["rerank_reason_counts"], {})
        self.assertEqual(profiled["local"]["crawl4ai_policy_kinds"], [])
        self.assertEqual(profiled["local"]["crawl4ai_filter_counts"], {})
        self.assertEqual(profiled["local"]["crawl4ai_cache_modes"], {})
        self.assertEqual(profiled["local"]["crawl4ai_fallback_used_count"], 0)
        self.assertEqual(profiled["local"]["web_confidence_policy_kind"], "dry_run")
        self.assertEqual(profiled["local"]["web_confidence_level"], "unknown")
        self.assertEqual(profiled["local"]["web_confidence_score"], 0.0)
        self.assertEqual(profiled["local"]["web_confidence_reason_codes"], [])
        self.assertEqual(profiled["local"]["web_confidence_inputs_summary"], {})
        self.assertEqual(profiled["local"]["openrouter_fallback_state"], "not_applicable")
        self.assertFalse(profiled["local"]["openrouter_fallback_used"])
        self.assertEqual(profiled["local"]["openrouter_fallback_reason_codes"], [])
        self.assertTrue(profiled["profiled_stub"]["runtime_changed"])
        self.assertEqual(
            profiled["profiled_stub"]["fixture_path"],
            "benchmark/suites/web_search/fixtures/local_bad_orders.json",
        )

    def test_live_local_and_local_profiled_toggle_profiled_runtime_flags(self) -> None:
        observed_kwargs: list[dict[str, object]] = []

        def fake_build_context_payload(_user_query: str, **kwargs: object) -> dict[str, object]:
            observed_kwargs.append(dict(kwargs))
            enabled_params = bool(kwargs.get("enable_profiled_searxng_params"))
            enabled_rerank = bool(kwargs.get("enable_reranking"))
            return {
                "status": "ok",
                "reason_code": None,
                "sources": [],
                "context_block": "",
                "read_state": None,
                "collection_path": "search_only",
                "search_profile": "actualite",
                "query_plan_kind": "profiled_bounded" if bool(kwargs.get("enable_specialized_queries")) else "single_query",
                "query_count": 3 if bool(kwargs.get("enable_specialized_queries")) else 1,
                "secondary_query_count": 2 if bool(kwargs.get("enable_specialized_queries")) else 0,
                "deduped_result_count": 0,
                "searxng_profile_params_kind": "profiled_actualite_year_general" if enabled_params else "historical",
                "searxng_profile_params_policy": "soft_broad_hints" if enabled_params else "historical_baseline",
                "searxng_categories": ["general"] if enabled_params else [],
                "searxng_engines": [],
                "searxng_time_range": "year" if enabled_params else "",
                "searxng_language": "fr-FR",
                "searxng_safesearch": "0",
                "rerank_applied": enabled_rerank,
                "rerank_policy": "soft_reorder_no_drop_v0" if enabled_rerank else "none",
                "rerank_input_count": 4 if enabled_rerank else 0,
                "rerank_output_count": 4 if enabled_rerank else 0,
                "rerank_profile": "actualite" if enabled_rerank else "",
                "rerank_top_domains_before": ["fr.wikipedia.org", "digital-strategy.ec.europa.eu"] if enabled_rerank else [],
                "rerank_top_domains_after": ["digital-strategy.ec.europa.eu", "fr.wikipedia.org"] if enabled_rerank else [],
                "rerank_reason_counts": {"profile_official_domain_soft_bonus": 1} if enabled_rerank else {},
                "rerank_promoted_count": 1 if enabled_rerank else 0,
                "rerank_downranked_count": 1 if enabled_rerank else 0,
                "crawl4ai_policy_kinds": ["profile_query_aware_bm25_with_fit_fallback"] if enabled_rerank else ["historical_fit"],
                "crawl4ai_filter_counts": {"bm25": 1} if enabled_rerank else {"fit": 1},
                "crawl4ai_cache_modes": {"1": 1} if enabled_rerank else {"0": 1},
                "crawl4ai_fallback_used_count": 0,
                "crawl4ai_query_sha256_12": ["abc123def456"] if enabled_rerank else [],
                "web_confidence_policy_kind": "local_web_confidence_observable_v0",
                "web_confidence_level": "high" if enabled_rerank else "medium",
                "web_confidence_score": 0.89 if enabled_rerank else 0.61,
                "web_confidence_reason_codes": ["confidence_signal_only", "crawl_markdown_used"],
                "web_confidence_inputs_summary": {"source_count": 2, "domain_count": 2},
                "openrouter_fallback_state": "future_only",
                "openrouter_fallback_used": False,
                "openrouter_fallback_reason_codes": ["external_fallback_disabled_lot7"],
                "used_content_kinds": [],
                "injected_chars": 0,
                "context_chars": 0,
                "results_count": 0,
                "primary_read_status": "not_attempted",
                "fallback_used": False,
            }

        fake_web_search = ModuleType("tools.web_search")
        fake_web_search.build_context_payload = fake_build_context_payload  # type: ignore[attr-defined]
        original_web_search_module = sys.modules.get("tools.web_search")
        sys.modules["tools.web_search"] = fake_web_search
        config = CampaignConfig(
            campaign_id="web-search-live-toggle",
            suite="web_search",
            repo_root=REPO_ROOT,
            output_dir=REPO_ROOT / "tmp-test-output-unused",
            models=["openai/gpt-5.1"],
            dry_run=False,
            timeout_s=1,
        )
        case = {"user_query": "Actualité IA Europe"}
        try:
            local = web_campaign._run_local_arm(config=config, case=case)
            profiled = web_campaign._run_local_profiled_arm(config=config, case=case)
        finally:
            if original_web_search_module is None:
                sys.modules.pop("tools.web_search", None)
            else:
                sys.modules["tools.web_search"] = original_web_search_module

        self.assertFalse(observed_kwargs[0]["enable_specialized_queries"])
        self.assertFalse(observed_kwargs[0]["enable_profiled_searxng_params"])
        self.assertFalse(observed_kwargs[0]["enable_reranking"])
        self.assertFalse(observed_kwargs[0]["enable_profiled_crawl4ai_policy"])
        self.assertTrue(observed_kwargs[1]["enable_specialized_queries"])
        self.assertTrue(observed_kwargs[1]["enable_profiled_searxng_params"])
        self.assertTrue(observed_kwargs[1]["enable_reranking"])
        self.assertTrue(observed_kwargs[1]["enable_profiled_crawl4ai_policy"])
        self.assertEqual(local["local"]["searxng_profile_params_kind"], "historical")
        self.assertEqual(profiled["local"]["searxng_profile_params_kind"], "profiled_actualite_year_general")
        self.assertEqual(profiled["local"]["searxng_profile_params_policy"], "soft_broad_hints")
        self.assertEqual(profiled["local"]["searxng_time_range"], "year")
        self.assertFalse(local["local"]["rerank_applied"])
        self.assertTrue(profiled["local"]["rerank_applied"])
        self.assertEqual(profiled["local"]["rerank_policy"], "soft_reorder_no_drop_v0")
        self.assertEqual(
            profiled["local"]["rerank_reason_counts"],
            {"profile_official_domain_soft_bonus": 1},
        )
        self.assertEqual(
            profiled["local"]["crawl4ai_policy_kinds"],
            ["profile_query_aware_bm25_with_fit_fallback"],
        )
        self.assertEqual(profiled["local"]["crawl4ai_filter_counts"], {"bm25": 1})
        self.assertEqual(profiled["local"]["crawl4ai_cache_modes"], {"1": 1})
        self.assertEqual(profiled["local"]["web_confidence_level"], "high")
        self.assertEqual(profiled["local"]["openrouter_fallback_state"], "future_only")
        self.assertFalse(profiled["local"]["openrouter_fallback_used"])

    def test_local_bad_order_fixtures_capture_live_local_failures(self) -> None:
        fixtures = web_adapter.load_local_bad_order_fixtures(REPO_ROOT)
        self.assertEqual(
            {fixture["case_id"] for fixture in fixtures},
            {
                "recent_ai_policy_news",
                "official_openrouter_server_tools",
                "conceptual_philosophy_search",
                "french_admin_service_public",
            },
        )
        self.assertEqual(
            {fixture["target_profile"] for fixture in fixtures},
            {
                "actualite",
                "technique_officielle",
                "academique_philosophique",
                "institutionnel_francais",
            },
        )
        problem_labels = {
            str(result["problem"])
            for fixture in fixtures
            for result in fixture["results"]
        }
        self.assertIn("dictionnaire", problem_labels)
        self.assertIn("conjugueur", problem_labels)
        self.assertIn("homonyme_hors_sujet", problem_labels)
        self.assertIn("source_officielle_trop_basse", problem_labels)


if __name__ == "__main__":
    unittest.main()
