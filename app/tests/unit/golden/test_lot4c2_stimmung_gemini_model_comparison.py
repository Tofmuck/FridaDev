from __future__ import annotations

import copy
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

from benchmark.suites.stimmung import dialogic_campaign


class _GeminiWitnessClient:
    def __init__(self, witness_by_dialogue: dict[str, list[dict]], schedule: list[dict]) -> None:
        self.witness_by_dialogue = witness_by_dialogue
        self.schedule = schedule
        self.calls: list[dict] = []

    def chat_completion(self, payload: dict, *, caller: str, timeout_s: int) -> dict:
        plan = self.schedule[len(self.calls)]
        self.calls.append(
            {
                "payload": copy.deepcopy(payload),
                "caller": caller,
                "timeout_s": timeout_s,
            }
        )
        signal = self.witness_by_dialogue[plan["dialogue_id"]][plan["turn_id"] - 1]
        return {
            "ok": True,
            "status_code": 200,
            "elapsed_ms": 125.0,
            "error": None,
            "raw_text": json.dumps(signal, ensure_ascii=False),
            "finish_reason": "stop",
            "native_finish_reason": "STOP",
            "usage": {
                "prompt_tokens": 640,
                "completion_tokens": 80,
                "total_tokens": 720,
                "completion_tokens_details": {"reasoning_tokens": 40},
            },
            "cost_estimate_usd": 0.0005,
            "cost_estimate_source": "provider_usage_cost",
            "generation_id": "not-retained",
            "model": "google/gemini-3.7-flash",
            "provider": "Google AI Studio",
            "service_tier": "default",
        }


class Lot4C2StimmungGeminiModelComparisonTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = dialogic_campaign.build_model_comparison_protocol(
            REPO_ROOT,
            freeze_commit="2" * 40,
        )
        cls.schedule = dialogic_campaign.build_model_comparison_request_schedule(
            REPO_ROOT,
            cls.protocol,
        )
        witness_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json"
        )
        witness = json.loads(witness_path.read_text(encoding="utf-8"))
        cls.witness_by_dialogue = {
            item["dialogue_id"]: item["signals"] for item in witness["dialogues"]
        }

    def test_protocol_freezes_native_policy_runtime_prompt_and_138_call_cap(self) -> None:
        summary = dialogic_campaign.validate_model_comparison_protocol(
            self.protocol,
            REPO_ROOT,
        )

        self.assertEqual(summary["expected_call_count"], 138)
        self.assertEqual(self.protocol["absolute_call_cap"], 138)
        self.assertEqual(self.protocol["model"], "google/gemini-3.7-flash")
        self.assertEqual(self.protocol["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(self.protocol["max_tokens"], 400)
        self.assertEqual(self.protocol["timeout_s"], 10)
        self.assertLessEqual(self.protocol["estimated_max_cost_usd"], 0.30)
        self.assertEqual(self.protocol["prompt_sha256"], dialogic_campaign._sha256_file(
            REPO_ROOT / "app/prompts/stimmung_agent.txt"
        ))
        self.assertNotEqual(
            self.protocol["prompt_sha256"],
            self.protocol["excluded_strengthening_candidate_sha256"],
        )
        self.assertEqual(self.protocol["historical_control"]["call_count"], 138)
        self.assertEqual(self.protocol["historical_control"]["model"], "google/gemini-3.1-flash-lite")

    def test_schedule_changes_only_the_frozen_model_policy_allowlist(self) -> None:
        historical_protocol = dialogic_campaign.build_protocol(
            REPO_ROOT,
            freeze_commit=dialogic_campaign.PHASE_A_FREEZE_COMMIT,
        )
        historical = [
            item
            for item in dialogic_campaign.build_request_schedule(REPO_ROOT, historical_protocol)
            if item["source"] == "primary"
        ]

        self.assertEqual(len(historical), 138)
        self.assertEqual(len(self.schedule), 138)
        for control, candidate in zip(historical, self.schedule):
            self.assertEqual(
                {key: control[key] for key in ("dialogue_id", "turn_id", "evaluated", "repetition")},
                {key: candidate[key] for key in ("dialogue_id", "turn_id", "evaluated", "repetition")},
            )
            self.assertEqual(control["payload"]["messages"], candidate["payload"]["messages"])
            self.assertEqual(
                dialogic_campaign.validate_model_policy_difference(
                    control["payload"],
                    candidate["payload"],
                ),
                list(dialogic_campaign.MODEL_COMPARISON_ALLOWED_POLICY_DIFFERENCES),
            )
            dialogic_campaign.validate_model_comparison_payload(candidate["payload"])

        sampling_mutant = copy.deepcopy(self.schedule[0]["payload"])
        sampling_mutant["temperature"] = 0.1
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_payload(sampling_mutant)

        effort_mutant = copy.deepcopy(self.schedule[0]["payload"])
        effort_mutant["reasoning"]["effort"] = "high"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_payload(effort_mutant)

        route_mutant = copy.deepcopy(self.schedule[0]["payload"])
        route_mutant["model"] += ":batch"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_payload(route_mutant)

        extra_mutant = copy.deepcopy(self.schedule[0]["payload"])
        extra_mutant["response_format"] = {"type": "json_object"}
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_payload(extra_mutant)

    def test_fake_run_traverses_normalizer_aggregator_scorer_and_strict_decision(self) -> None:
        client = _GeminiWitnessClient(self.witness_by_dialogue, self.schedule)
        records = dialogic_campaign.run_model_comparison_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        validation = dialogic_campaign.validate_model_comparison_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )

        self.assertEqual(len(client.calls), 138)
        self.assertEqual(validation["call_count"], 138)
        self.assertEqual(validation["dialogue_score_count"], 32)
        self.assertEqual(validation["final_decision"], "eligible_primary")
        self.assertTrue(all(call["caller"] == "stimmung_agent" for call in client.calls))
        self.assertTrue(all(call["timeout_s"] == 10 for call in client.calls))
        self.assertTrue(all("temperature" not in call["payload"] for call in client.calls))
        self.assertTrue(all("top_p" not in call["payload"] for call in client.calls))

    def test_artifact_rejects_missing_call_false_eligibility_route_and_raw_content(self) -> None:
        records = dialogic_campaign.run_model_comparison_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_GeminiWitnessClient(self.witness_by_dialogue, self.schedule),
        )

        raw_mutant = copy.deepcopy(records[0])
        raw_mutant["reasoning_text"] = "synthetic raw reasoning"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_record(raw_mutant)

        route_mutant = copy.deepcopy(records)
        route_mutant[0]["observed_provider"] = "unknown"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_artifact(
                route_mutant,
                REPO_ROOT,
                self.protocol,
            )

        missing_mutant = copy.deepcopy(records[1:])
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_artifact(
                missing_mutant,
                REPO_ROOT,
                self.protocol,
            )

        false_eligible = copy.deepcopy(records)
        score = next(item for item in false_eligible if item["record_type"] == "dialogue_score")
        score["classification"] = "fail"
        score["error_class"] = "semantic"
        score["reason_codes"] = ["signal_overcoded"]
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_model_comparison_artifact(
                false_eligible,
                REPO_ROOT,
                self.protocol,
            )

    def test_historical_control_and_runtime_sources_remain_unchanged(self) -> None:
        self.assertEqual(
            dialogic_campaign._sha256_file(dialogic_campaign._historical_artifact_path(REPO_ROOT)),
            "97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e",
        )
        self.assertEqual(
            dialogic_campaign._sha256_file(REPO_ROOT / "app/prompts/stimmung_agent.txt"),
            "6374bf40468ec2c8879eaaba8c81472d117bb241f7490d033d78be14bf837663",
        )
        self.assertEqual(
            dialogic_campaign._sha256_file(REPO_ROOT / "app/core/stimmung_agent.py"),
            "314bbd75f20ff02baa1acd38e5d7d5384abd779eb2c1435bb740dc33bfc7771a",
        )

    def test_retained_candidate_artifact_is_content_free_and_reconstructible(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-gemini-3-7-medium.jsonl"
        )
        protocol = dialogic_campaign.build_model_comparison_protocol(
            REPO_ROOT,
            freeze_commit="1e9bb9f99c8a5bd73af855e3dc6dbedf211aa5b7",
        )
        records = dialogic_campaign.load_jsonl(artifact_path)
        validation = dialogic_campaign.validate_model_comparison_artifact(
            records,
            REPO_ROOT,
            protocol,
        )
        calls = [item for item in records if item["record_type"] == "call"]

        self.assertEqual(
            dialogic_campaign._sha256_file(artifact_path),
            "5adb54eec321f671fb05e2b350d35120a7ce84a52e7b936c4e54829002bce8f3",
        )
        self.assertEqual(validation["call_count"], 138)
        self.assertEqual(validation["dialogue_score_count"], 32)
        self.assertEqual(validation["final_decision"], "inconclusive")
        self.assertEqual(sum(item["status"] == "ok" for item in calls), 114)
        self.assertEqual(sum(item["status"] == "json_error" for item in calls), 24)
        self.assertTrue(
            all(
                item["requested_model"] == "google/gemini-3.7-flash"
                for item in calls
            )
        )
        self.assertTrue(all(item["observed_provider"] == "google" for item in calls))
        self.assertTrue(all(item["provider_fallbacks"] is False for item in calls))


if __name__ == "__main__":
    unittest.main()
