from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.run_benchmark import DEFAULT_STIMMUNG_MODELS
from benchmark.suites.stimmung import adapter as stimmung_adapter
from benchmark.suites.stimmung import campaign as stimmung_campaign
from benchmark.suites.stimmung import scorer as stimmung_scorer


class StimmungBenchmarkSuiteTests(unittest.TestCase):
    def test_default_stimmung_models_match_primary_campaign(self) -> None:
        self.assertEqual(
            DEFAULT_STIMMUNG_MODELS,
            [
                "openai/gpt-5.4-mini",
                "anthropic/claude-haiku-4.5",
                "google/gemini-3.1-flash-lite",
                "mistralai/mistral-small-2603",
            ],
        )

    def test_stimmung_fixtures_cover_required_case_families(self) -> None:
        cases = stimmung_adapter.load_cases(REPO_ROOT)
        self.assertEqual(len(cases), 24)
        tags = {tag for case in cases for tag in case.get("tags", [])}
        required = {
            "neutral_probe",
            "curiosite",
            "confusion",
            "frustration",
            "colere",
            "anxiete",
            "decouragement",
            "enthousiasme",
            "apaisement",
            "ironie",
            "agacement_joueur",
            "role_play",
            "temporal",
            "recent_context_trap",
            "oral_dicte",
            "french",
        }
        self.assertTrue(required.issubset(tags), sorted(required - tags))
        for case in cases:
            self.assertTrue(case.get("current_user_message"))
            self.assertTrue(case.get("design_note"))
            self.assertTrue((case.get("expected_acceptables") or {}).get("dominant_tones"))

    def test_stimmung_final_fixtures_are_repo_sourced_and_short(self) -> None:
        cases = stimmung_adapter.load_cases(REPO_ROOT, fixture_set="final")
        self.assertEqual(len(cases), 10)
        self.assertTrue(all(case["provenance"] == "existing_test_case" for case in cases))
        self.assertTrue(all(case["source_reference"].startswith("app/tests/") for case in cases))
        self.assertTrue(all("repo_test_fixture" in case.get("tags", []) for case in cases))

    def test_stimmung_payload_uses_production_prompt_shape_and_fixed_params(self) -> None:
        cases = stimmung_adapter.load_cases(REPO_ROOT)
        prompt = stimmung_adapter.prompt_path(REPO_ROOT).read_text(encoding="utf-8").strip()
        payload_a = stimmung_adapter.build_payload(cases[0], "openai/gpt-5.4-mini", prompt)
        payload_b = stimmung_adapter.build_payload(cases[0], "mistralai/mistral-small-2603", prompt)

        self.assertEqual(payload_a["temperature"], 0.1)
        self.assertEqual(payload_a["top_p"], 1.0)
        self.assertEqual(payload_a["max_tokens"], 220)
        self.assertEqual(payload_a["messages"], payload_b["messages"])
        self.assertEqual(payload_a["messages"][0]["content"], prompt)
        self.assertIn("Tour utilisateur courant", payload_a["messages"][1]["content"])
        self.assertEqual(payload_a["model"], "openai/gpt-5.4-mini")
        self.assertEqual(payload_b["model"], "mistralai/mistral-small-2603")

    def test_stimmung_scorer_validates_schema_and_expected_tone(self) -> None:
        case = {
            "expected_acceptables": {
                "dominant_tones": ["frustration"],
                "tones": ["frustration"],
                "avoid_tones": ["enthousiasme"],
                "min_strength": 4,
            },
            "tags": ["marked_affect"],
        }
        raw = json.dumps(
            {
                "schema_version": "v1",
                "present": True,
                "tones": [{"tone": "frustration", "strength": 5}],
                "dominant_tone": "frustration",
                "confidence": 0.8,
            },
            ensure_ascii=False,
        )
        result = stimmung_scorer.score_response(case, raw, None)
        self.assertTrue(result["json_valid"])
        self.assertTrue(result["schema_valid"])
        self.assertTrue(result["hard_pass"])

    def test_stimmung_scorer_rejects_schema_drift(self) -> None:
        result = stimmung_scorer.score_response(
            {"expected_acceptables": {"dominant_tones": ["neutralite"]}},
            (
                '{"schema_version": "v1", "present": true, '
                '"tones": [{"tone": "joie", "strength": 5}], '
                '"dominant_tone": "joie", "confidence": 0.8}'
            ),
            None,
        )
        self.assertTrue(result["json_valid"])
        self.assertFalse(result["schema_valid"])
        self.assertIn("tone_0:invalid_tone", result["schema_errors"])

    def test_stimmung_campaign_dry_run_writes_artifacts(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            config = stimmung_campaign.CampaignConfig(
                campaign_id="stimmung-dry",
                suite="stimmung",
                repo_root=REPO_ROOT,
                output_dir=tmp_path / "results",
                models=["openai/gpt-5.4-mini"],
                dry_run=True,
                timeout_s=1,
            )

            result = stimmung_campaign.run_stimmung_primary_campaign(config=config, client=None)

            json_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")
            self.assertFalse(json_payload["production_runtime_changed"])
            self.assertFalse(json_payload["fallback_benchmarked"])
            self.assertTrue(json_payload["human_decision_required"])
            self.assertEqual(json_payload["case_count"], 24)
            provider = json_payload["results"][0]["calls"][0]["provider"]
            self.assertNotIn("raw_text", provider)
            self.assertFalse(provider["raw_text_retained"])
            self.assertTrue(provider["raw_text_sha256"])
            self.assertIn("Lecture hermeneutique par modele", markdown)


if __name__ == "__main__":
    unittest.main()
