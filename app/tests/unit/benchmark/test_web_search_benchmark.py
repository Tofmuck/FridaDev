from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


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

    def test_unknown_arm_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            web_adapter.normalize_arms(["local", "plugins_web"])

    def test_local_profiled_arm_exposes_lot3_query_plan_shape(self) -> None:
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
        self.assertEqual(profiled["mode"], "local_profiled_specialized_queries")
        self.assertEqual(profiled["engine"], "searxng_crawl4ai_profiled_queries")
        self.assertFalse(profiled["local"]["local_profiled_stub"])
        self.assertEqual(profiled["local"]["search_profile"], "stub_not_implemented")
        self.assertEqual(profiled["local"]["query_plan_kind"], "dry_run")
        self.assertEqual(profiled["local"]["secondary_query_count"], 0)
        self.assertTrue(profiled["profiled_stub"]["runtime_changed"])
        self.assertEqual(
            profiled["profiled_stub"]["fixture_path"],
            "benchmark/suites/web_search/fixtures/local_bad_orders.json",
        )

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
