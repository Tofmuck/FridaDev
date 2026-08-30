from __future__ import annotations

import copy
import json
import statistics
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
        self.assertEqual(
            self.protocol["prompt_sha256"],
            dialogic_campaign.RUNTIME_PROMPT_BASELINE_SHA256,
        )
        self.assertNotEqual(
            self.protocol["prompt_sha256"],
            dialogic_campaign._sha256_file(
                REPO_ROOT / "app/prompts/stimmung_agent.txt"
            ),
        )
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

    def test_historical_control_stays_frozen_after_runtime_prompt_cutover(self) -> None:
        self.assertEqual(
            dialogic_campaign._sha256_file(dialogic_campaign._historical_artifact_path(REPO_ROOT)),
            "97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e",
        )
        self.assertEqual(
            dialogic_campaign._sha256_file(REPO_ROOT / "app/prompts/stimmung_agent.txt"),
            "567f0615f14fe9f13a50e6e57ef46dc6fdba2cd6e6156407d6e2f489c2076a7f",
        )
        self.assertNotEqual(
            dialogic_campaign._sha256_file(REPO_ROOT / "app/prompts/stimmung_agent.txt"),
            dialogic_campaign.RUNTIME_PROMPT_BASELINE_SHA256,
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


class Lot4C2StimmungGeminiTokenCapRerunTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = dialogic_campaign.build_token_cap_rerun_protocol(
            REPO_ROOT,
            freeze_commit="3" * 40,
        )
        cls.schedule = dialogic_campaign.build_token_cap_rerun_request_schedule(
            REPO_ROOT,
            cls.protocol,
        )
        cls.control_protocol = dialogic_campaign.build_model_comparison_protocol(
            REPO_ROOT,
            freeze_commit="1e9bb9f99c8a5bd73af855e3dc6dbedf211aa5b7",
        )
        cls.control_schedule = dialogic_campaign.build_model_comparison_request_schedule(
            REPO_ROOT,
            cls.control_protocol,
        )
        witness_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json"
        )
        witness = json.loads(witness_path.read_text(encoding="utf-8"))
        cls.witness_by_dialogue = {
            item["dialogue_id"]: item["signals"] for item in witness["dialogues"]
        }

    def test_400_artifact_proves_saturation_signature_without_finish_reason(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-gemini-3-7-medium.jsonl"
        )
        calls = [
            item
            for item in dialogic_campaign.load_jsonl(artifact_path)
            if item["record_type"] == "call"
        ]
        invalid = [item for item in calls if item["status"] == "json_error"]
        valid = [item for item in calls if item["status"] == "ok"]

        self.assertEqual(len(calls), 138)
        self.assertEqual(len(invalid), 24)
        self.assertEqual({item["completion_tokens"] for item in invalid}, {396})
        self.assertEqual(
            (
                min(item["reasoning_tokens"] for item in invalid),
                statistics.median(item["reasoning_tokens"] for item in invalid),
                max(item["reasoning_tokens"] for item in invalid),
            ),
            (326, 380.5, 384),
        )
        self.assertEqual(
            statistics.median(item["reasoning_tokens"] for item in valid),
            171.0,
        )
        self.assertFalse(any(item["status"] in {"timeout", "transport_error"} for item in calls))
        self.assertFalse(any("finish_reason" in item for item in calls))
        self.assertFalse(any("native_finish_reason" in item for item in calls))

    def test_protocol_and_schedule_change_only_max_tokens_from_400_to_800(self) -> None:
        summary = dialogic_campaign.validate_token_cap_rerun_protocol(
            self.protocol,
            REPO_ROOT,
        )

        self.assertEqual(summary["expected_call_count"], 138)
        self.assertEqual(self.protocol["max_tokens"], 800)
        self.assertEqual(self.protocol["baseline_max_tokens"], 400)
        self.assertEqual(self.protocol["cost_cap_usd"], 0.50)
        self.assertEqual(self.protocol["estimated_max_cost_usd"], 0.473388)
        self.assertEqual(self.protocol["baseline_saturation"]["invalid_json_count"], 24)
        self.assertEqual(
            self.protocol["baseline_saturation"]["invalid_completion_tokens"],
            [396],
        )
        self.assertEqual(self.protocol["baseline_saturation"]["timeout_count"], 0)
        self.assertEqual(len(self.schedule), 138)
        self.assertEqual(len(self.control_schedule), 138)
        for control, rerun in zip(self.control_schedule, self.schedule):
            self.assertEqual(
                {key: control[key] for key in ("sequence", "dialogue_id", "turn_id", "evaluated", "repetition")},
                {key: rerun[key] for key in ("sequence", "dialogue_id", "turn_id", "evaluated", "repetition")},
            )
            self.assertEqual(
                dialogic_campaign.validate_token_cap_rerun_policy_difference(
                    control["payload"], rerun["payload"]
                ),
                ["max_tokens"],
            )
            self.assertEqual(rerun["payload"]["max_tokens"], 800)
            self.assertEqual(rerun["payload"]["model"], "google/gemini-3.7-flash")
            self.assertEqual(rerun["payload"]["reasoning"], {"effort": "medium", "exclude": True})
            self.assertEqual(
                rerun["payload"]["provider"],
                {"allow_fallbacks": False, "require_parameters": True},
            )

        forbidden_difference = copy.deepcopy(self.schedule[0]["payload"])
        forbidden_difference["reasoning"]["effort"] = "high"
        with self.assertRaisesRegex(ValueError, "token_cap_rerun_policy_difference_invalid"):
            dialogic_campaign.validate_token_cap_rerun_policy_difference(
                self.control_schedule[0]["payload"], forbidden_difference
            )

    def test_fake_rerun_records_closed_finish_reasons_and_rejects_mutations(self) -> None:
        client = _GeminiWitnessClient(self.witness_by_dialogue, self.schedule)
        records = dialogic_campaign.run_token_cap_rerun_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        validation = dialogic_campaign.validate_token_cap_rerun_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )
        calls = [item for item in records if item["record_type"] == "call"]

        self.assertEqual(len(client.calls), 138)
        self.assertEqual(validation["call_count"], 138)
        self.assertEqual(validation["dialogue_score_count"], 32)
        self.assertEqual(validation["final_decision"], "eligible_primary")
        self.assertEqual({item["finish_reason"] for item in calls}, {"stop"})
        self.assertEqual({item["native_finish_reason"] for item in calls}, {"stop"})
        self.assertTrue(all(item["max_tokens"] == 800 for item in calls))
        self.assertTrue(all(item["provider_fallbacks"] is False for item in calls))

        mutations = {
            "free_finish_reason": (0, "finish_reason", "synthetic free text"),
            "wrong_native_finish_reason": (0, "native_finish_reason", "MAX_TOKENS_WITH_DETAIL"),
            "wrong_cap": (0, "max_tokens", 400),
        }
        for name, (index, key, value) in mutations.items():
            with self.subTest(name=name):
                mutant = copy.deepcopy(records)
                mutant[index][key] = value
                with self.assertRaises(ValueError):
                    dialogic_campaign.validate_token_cap_rerun_artifact(
                        mutant,
                        REPO_ROOT,
                        self.protocol,
                    )

        with self.assertRaises(ValueError):
            dialogic_campaign.validate_token_cap_rerun_artifact(
                records[1:],
                REPO_ROOT,
                self.protocol,
            )

    def test_retained_800_artifact_is_content_free_and_reconstructible(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-gemini-3-7-medium-max800.jsonl"
        )
        protocol = dialogic_campaign.build_token_cap_rerun_protocol(
            REPO_ROOT,
            freeze_commit="08da24a706d9701d46f0c9e8b63b303a114eeb1a",
        )
        records = dialogic_campaign.load_jsonl(artifact_path)
        validation = dialogic_campaign.validate_token_cap_rerun_artifact(
            records,
            REPO_ROOT,
            protocol,
        )
        calls = [item for item in records if item["record_type"] == "call"]

        self.assertEqual(
            dialogic_campaign._sha256_file(artifact_path),
            "1b6112ceea8d6065aabd34f579f64ccfe652f514b5187cd0d2c3da542ebf11fd",
        )
        self.assertEqual(validation["call_count"], 138)
        self.assertEqual(validation["dialogue_score_count"], 32)
        self.assertEqual(validation["final_decision"], "inconclusive")
        self.assertEqual(sum(item["status"] == "ok" for item in calls), 137)
        self.assertEqual(sum(item["status"] == "json_error" for item in calls), 1)
        self.assertEqual(
            {
                (item["finish_reason"], item["native_finish_reason"])
                for item in calls
                if item["status"] == "json_error"
            },
            {("length", "length")},
        )
        self.assertTrue(all(item["max_tokens"] == 800 for item in calls))
        self.assertTrue(all(item["provider_fallbacks"] is False for item in calls))


if __name__ == "__main__":
    unittest.main()
