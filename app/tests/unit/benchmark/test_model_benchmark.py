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

from benchmark.run_benchmark import DEFAULT_ARBITER_MODELS, DEFAULT_SUMMARY_MODELS
from benchmark.core import openrouter
from benchmark.suites.arbiter import adapter, scorer, tournament
from benchmark.suites.summary import adapter as summary_adapter
from benchmark.suites.summary import campaign as summary_campaign


class ArbiterBenchmarkSuiteTests(unittest.TestCase):
    def test_default_first_campaign_models_are_exact_and_exclude_nano(self) -> None:
        self.assertEqual(
            DEFAULT_ARBITER_MODELS,
            [
                "openai/gpt-5.4-mini",
                "google/gemini-3.1-flash-lite",
                "qwen/qwen3.6-flash",
                "mistralai/mistral-small-2603",
            ],
        )
        self.assertNotIn("openai/gpt-5.4-nano", DEFAULT_ARBITER_MODELS)

    def test_fixtures_cover_required_arbiter_case_families(self) -> None:
        cases = adapter.load_cases(REPO_ROOT)
        tags = {tag for case in cases for tag in case.get("tags", [])}
        required = {
            "clearly_useful",
            "clearly_useless",
            "ambiguous",
            "noise",
            "redundancy",
            "affective_near",
            "identity",
            "false_memory",
            "temporal",
            "today",
            "hier",
            "ce_soir",
            "depuis_hier",
            "french",
        }
        self.assertTrue(required.issubset(tags), sorted(required - tags))
        self.assertGreaterEqual(len(cases), 8)
        self.assertGreaterEqual(sum(len(case["candidates"]) for case in cases), 12)
        for case in cases:
            candidate_ids = {candidate["candidate_id"] for candidate in case["candidates"]}
            self.assertTrue(set(case.get("expected_keep_ids", [])).issubset(candidate_ids))
            self.assertTrue(case.get("why"))

    def test_tournament_fixtures_are_reserved_and_have_expected_composition(self) -> None:
        round1 = adapter.load_cases(REPO_ROOT, fixture_set="tournament_round1")
        final = adapter.load_cases(REPO_ROOT, fixture_set="tournament_final")
        self.assertEqual(len(round1), 40)
        self.assertEqual(len(final), 60)
        self.assertEqual(sum(1 for case in round1 if case["origin"] == "real_anonymized"), 24)
        self.assertEqual(sum(1 for case in round1 if case["origin"] == "artificial_hard"), 16)
        self.assertEqual(sum(1 for case in final if case["origin"] == "real_anonymized"), 40)
        self.assertEqual(sum(1 for case in final if case["origin"] == "artificial_hard"), 20)
        self.assertFalse({case["id"] for case in round1} & {case["id"] for case in final})

    def test_tournament_round1_models_are_exact(self) -> None:
        self.assertEqual(tournament.ROUND1_MODELS, DEFAULT_ARBITER_MODELS)
        self.assertNotIn("openai/gpt-5.4-nano", tournament.ROUND1_MODELS)

    def test_payload_uses_production_prompt_and_fixed_arbiter_params(self) -> None:
        cases = adapter.load_cases(REPO_ROOT)
        prompt = adapter.prompt_path(REPO_ROOT).read_text(encoding="utf-8").strip()
        payload_a = adapter.build_payload(cases[0], "openai/gpt-5.4-mini", prompt)
        payload_b = adapter.build_payload(cases[0], "qwen/qwen3.6-flash", prompt)

        self.assertEqual(payload_a["temperature"], 0)
        self.assertEqual(payload_a["top_p"], 1.0)
        self.assertEqual(payload_a["max_tokens"], 600)
        self.assertEqual(payload_a["messages"], payload_b["messages"])
        self.assertEqual(payload_a["messages"][0]["content"], prompt)
        self.assertIn("=== Recent context ===", payload_a["messages"][1]["content"])
        self.assertIn("=== Candidate memories ===", payload_a["messages"][1]["content"])
        self.assertEqual(payload_a["model"], "openai/gpt-5.4-mini")
        self.assertEqual(payload_b["model"], "qwen/qwen3.6-flash")

    def test_scorer_counts_false_positives_and_false_negatives(self) -> None:
        case = {
            "candidates": [
                {"candidate_id": "expected-keep"},
                {"candidate_id": "expected-drop"},
            ],
            "expected_keep_ids": ["expected-keep"],
        }
        raw = json.dumps(
            {
                "decisions": [
                    {
                        "candidate_id": "expected-keep",
                        "keep": False,
                        "semantic_relevance": 0.8,
                        "contextual_gain": 0.2,
                        "redundant_with_recent": False,
                        "reason": "missed useful memory",
                    },
                    {
                        "candidate_id": "expected-drop",
                        "keep": True,
                        "semantic_relevance": 0.9,
                        "contextual_gain": 0.8,
                        "redundant_with_recent": False,
                        "reason": "kept noise",
                    },
                ]
            }
        )
        result = scorer.score_response(case, raw, None)
        self.assertTrue(result["json_valid"])
        self.assertTrue(result["schema_valid"])
        self.assertEqual(result["false_positives"], ["expected-drop"])
        self.assertEqual(result["false_negatives"], ["expected-keep"])
        self.assertEqual(result["weighted_penalty"], 3)
        self.assertEqual(result["score"], 0.0)

    def test_scorer_rejects_non_schema_json(self) -> None:
        case = {"candidates": [{"candidate_id": "cand"}], "expected_keep_ids": []}
        result = scorer.score_response(case, '{"ids": ["cand"]}', None)
        self.assertTrue(result["json_valid"])
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["weighted_score"], 0.0)

    def test_provider_error_gets_no_keep_drop_credit(self) -> None:
        case = {"candidates": [{"candidate_id": "drop-me"}], "expected_keep_ids": []}
        result = scorer.score_response(case, None, "Provider returned error")
        self.assertFalse(result["json_valid"])
        self.assertFalse(result["schema_valid"])
        self.assertEqual(result["score"], 0.0)
        self.assertEqual(result["weighted_score"], 0.0)
        self.assertEqual(result["weighted_penalty"], result["max_weighted_penalty"])

    def test_campaign_verdict_keeps_runtime_unchanged_until_decoupling_lot(self) -> None:
        verdict = scorer.campaign_verdict(
            [
                {
                    "summary": {
                        "model": "openai/gpt-5.4-mini",
                        "verdict": "garder",
                        "avg_latency_ms": 1000,
                        "cost_estimate_usd": 0.002,
                    }
                },
                {
                    "summary": {
                        "model": "mistralai/mistral-small-2603",
                        "verdict": "garder",
                        "avg_latency_ms": 1500,
                        "cost_estimate_usd": 0.001,
                    }
                },
            ]
        )
        self.assertEqual(verdict["verdict"], "garder")
        self.assertIn("production unchanged", verdict["next_step"])
        self.assertIn("decoupling lot", verdict["next_step"])


class SummaryBenchmarkSuiteTests(unittest.TestCase):
    def test_default_summary_models_match_human_reading_campaign(self) -> None:
        self.assertEqual(
            DEFAULT_SUMMARY_MODELS,
            [
                "openai/gpt-5.4-mini",
                "anthropic/claude-sonnet-4.6",
                "mistralai/mistral-medium-3-5",
                "google/gemini-3.1-pro-preview",
                "qwen/qwen3.5-plus-20260420",
                "mistralai/mistral-small-2603",
            ],
        )

    def test_summary_payload_uses_production_prompt_shape_and_runtime_params(self) -> None:
        prompt = summary_adapter.prompt_path(REPO_ROOT).read_text(encoding="utf-8").strip()
        turns = [
            {"role": "user", "content": "Bonjour", "local_date": "2026-05-18"},
            {"role": "assistant", "content": "Bonjour Tof", "local_date": "2026-05-18"},
        ]
        user_content = summary_adapter.build_user_content(turns)

        payload_a = summary_adapter.build_payload(
            model="openai/gpt-5.4-mini",
            prompt_text=prompt,
            user_content=user_content,
        )
        payload_b = summary_adapter.build_payload(
            model="mistralai/mistral-small-2603",
            prompt_text=prompt,
            user_content=user_content,
            generation_params=summary_adapter.generation_params(max_tokens=4500),
        )

        self.assertEqual(payload_a["messages"], payload_b["messages"])
        self.assertEqual(payload_a["messages"][0]["content"], prompt)
        self.assertIn("Voici le dialogue à résumer", payload_a["messages"][1]["content"])
        self.assertEqual(payload_a["temperature"], 0.3)
        self.assertEqual(payload_a["top_p"], 1.0)
        self.assertEqual(payload_a["max_tokens"], 2000)
        self.assertEqual(payload_b["max_tokens"], 4500)
        self.assertEqual(payload_a["model"], "openai/gpt-5.4-mini")
        self.assertEqual(payload_b["model"], "mistralai/mistral-small-2603")

    def test_summary_campaign_reports_provider_finish_reason(self) -> None:
        provider = {
            "ok": True,
            "finish_reason": "length",
            "native_finish_reason": "max_tokens",
            "usage": {"completion_tokens": 4500},
        }
        self.assertEqual(
            summary_campaign._termination_assessment(provider, "Résumé coupé", True),
            "provider_declares_length_stop",
        )
        self.assertIn(
            "longueur",
            summary_campaign._result_notes(
                provider,
                "Résumé coupé",
                True,
                "provider_declares_length_stop",
            ),
        )

    def test_openrouter_extracts_finish_reason_metadata(self) -> None:
        data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "native_finish_reason": "end_turn",
                    "message": {"content": "ok"},
                }
            ]
        }
        self.assertEqual(openrouter._extract_text(data), "ok")
        self.assertEqual(openrouter._finish_reason(data), "stop")
        self.assertEqual(openrouter._native_finish_reason(data), "end_turn")

    def test_summary_campaign_writes_output_files_without_raw_material_in_json(self) -> None:
        from tempfile import TemporaryDirectory

        with TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            material_path = tmp_path / "material.json"
            material_path.write_text(
                json.dumps(
                    {
                        "source": {
                            "source_kind": "unit_test",
                            "conversation_id": "conv-test",
                            "approx_tokens": 42,
                        },
                        "turns": [
                            {"role": "user", "content": "Un fait important.", "local_date": "2026-05-18"},
                            {"role": "assistant", "content": "Je le garde en tête.", "local_date": "2026-05-18"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            config = summary_campaign.CampaignConfig(
                campaign_id="summary-dry",
                suite="summary",
                repo_root=REPO_ROOT,
                output_dir=tmp_path / "results",
                models=["openai/gpt-5.4-mini"],
                dry_run=True,
                timeout_s=1,
            )

            result = summary_campaign.run_summary_human_reading_campaign(
                config=config,
                input_path=material_path,
                client=None,
            )

            json_payload = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            self.assertFalse(json_payload["raw_material_written"])
            self.assertNotIn("Un fait important", json.dumps(json_payload, ensure_ascii=False))
            summary_file = Path(json_payload["results"][0]["summary_file"])
            if not summary_file.is_absolute():
                summary_file = REPO_ROOT / summary_file
            self.assertTrue(summary_file.exists())
            self.assertIn("dry-run summary", summary_file.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
