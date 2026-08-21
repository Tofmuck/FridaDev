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
from benchmark.run_benchmark import DEFAULT_VALIDATION_AGENT_MODELS
from benchmark.suites.validation_agent import adapter as validation_adapter
from benchmark.suites.validation_agent import campaign as validation_campaign
from benchmark.suites.validation_agent import scorer as validation_scorer


class ValidationAgentBenchmarkSuiteTests(unittest.TestCase):
    def test_default_validation_agent_models_match_primary_campaign(self) -> None:
        self.assertEqual(
            DEFAULT_VALIDATION_AGENT_MODELS,
            [
                "openai/gpt-5.4-mini",
                "google/gemini-3.1-flash-lite",
                "mistralai/mistral-small-2603",
                "anthropic/claude-haiku-4.5",
            ],
        )

    def test_validation_agent_fixtures_cover_required_case_families(self) -> None:
        cases = validation_adapter.load_fixtures(REPO_ROOT / validation_adapter.FIXTURE_PATH)
        self.assertEqual(len(cases), 13)
        tags = {tag for case in cases for tag in case.get("tags", [])}
        required = {
            "answer_simple",
            "clarify",
            "suspend_simple",
            "hard_guard",
            "source_conflict",
            "time",
            "affective_tension",
            "primary_too_prudent",
        }
        self.assertTrue(required.issubset(tags), sorted(required - tags))
        self.assertGreaterEqual(sum(1 for case in cases if case["origin"] == "existing_test_case"), 10)
        for case in cases:
            self.assertTrue(case.get("design_note"))
            self.assertTrue(case.get("source_reference"))
            expected = case.get("expected") or {}
            self.assertIn(expected.get("final_judgment_posture"), validation_adapter.ALLOWED_POSTURES)
            self.assertIn(expected.get("final_output_regime"), validation_adapter.ALLOWED_OUTPUT_REGIMES)

    def test_validation_agent_payload_uses_production_prompt_shape_and_fixed_params(self) -> None:
        cases = validation_adapter.load_fixtures(REPO_ROOT / validation_adapter.FIXTURE_PATH)
        prompt = (REPO_ROOT / validation_adapter.PROMPT_PATH).read_text(encoding="utf-8").strip()
        payload_a = validation_adapter.build_payload(cases[0], "openai/gpt-5.4-mini", prompt)
        payload_b = validation_adapter.build_payload(cases[0], "mistralai/mistral-small-2603", prompt)

        self.assertEqual(payload_a["temperature"], 0.0)
        self.assertEqual(payload_a["top_p"], 1.0)
        self.assertEqual(payload_a["max_tokens"], 140)
        self.assertEqual(payload_a["messages"], payload_b["messages"])
        self.assertEqual(payload_a["messages"][0]["content"], prompt)
        self.assertIn("validation_dialogue_context", payload_a["messages"][1]["content"])
        self.assertIn("primary_verdict", payload_a["messages"][1]["content"])
        self.assertIn("canonical_inputs", payload_a["messages"][1]["content"])
        self.assertEqual(payload_a["model"], "openai/gpt-5.4-mini")
        self.assertEqual(payload_b["model"], "mistralai/mistral-small-2603")

    def test_validation_agent_payload_can_raise_output_budget_for_comparison(self) -> None:
        cases = validation_adapter.load_fixtures(REPO_ROOT / validation_adapter.FIXTURE_PATH)
        prompt = (REPO_ROOT / validation_adapter.PROMPT_PATH).read_text(encoding="utf-8").strip()
        payload = validation_adapter.build_payload(
            cases[0],
            "openai/gpt-5.4-mini",
            prompt,
            generation_settings=validation_adapter.generation_params(max_tokens=140),
        )

        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["top_p"], 1.0)
        self.assertEqual(payload["max_tokens"], 140)

    def test_validation_agent_scorer_flags_hard_guard_answer_violation(self) -> None:
        cases = validation_adapter.load_fixtures(REPO_ROOT / validation_adapter.FIXTURE_PATH)
        case = next(item for item in cases if item["id"] == "repo_explicit_url_not_read_blocks_answer")
        raw = json.dumps(
            {
                "schema_version": "v1",
                "final_judgment_posture": "answer",
                "final_output_regime": "simple",
                "arbiter_reason": "La page semble suffisante.",
            },
            ensure_ascii=False,
        )
        result = validation_scorer.score_output(case, raw)
        self.assertTrue(result["json_valid"])
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["hard_guard_violation"])
        self.assertTrue(result["unsafe_answer"])
        self.assertFalse(result["pass"])

    def test_validation_agent_campaign_dry_run_writes_compact_artifacts(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = CampaignConfig(
                campaign_id="validation-agent-dry",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=tmp_path / "results",
                models=["openai/gpt-5.4-mini"],
                dry_run=True,
                timeout_s=1,
            )

            result = validation_campaign.run_validation_agent_campaign(config=config, client=None)

            json_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
            self.assertFalse(json_payload["production_runtime_changed"])
            self.assertFalse(json_payload["fallback_benchmarked"])
            self.assertTrue(json_payload["human_decision_required"])
            self.assertEqual(json_payload["case_count"], 13)
            provider = json_payload["results"][0]["calls"][0]["provider"]
            self.assertNotIn("raw_text", provider)
            self.assertFalse(provider["raw_text_retained"])
            self.assertTrue(provider["raw_text_sha256"])
            self.assertIn("Lecture hermeneutique par modele", markdown)
            self.assertNotIn("| ECHEC |", markdown)


if __name__ == "__main__":
    unittest.main()
