from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.core import openrouter
from benchmark.suites.validation_agent import lot4c1_policy_comparison as policy


class _SyntheticResponse:
    status_code = 200
    content = b"synthetic"

    @staticmethod
    def json() -> dict:
        return {
            "id": "generation-synthetic-001",
            "model": "google/gemini-3.7-flash",
            "provider": "Google AI Studio",
            "service_tier": "default",
            "choices": [
                {
                    "message": {
                        "content": "{}",
                        "reasoning": "SYNTHETIC_REASONING_MUST_NOT_ESCAPE",
                    },
                    "finish_reason": "stop",
                    "native_finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "total_tokens": 30,
                "completion_tokens_details": {"reasoning_tokens": 8},
            },
        }


class Lot4C1ValidationModelComparisonTests(unittest.TestCase):
    @staticmethod
    def _synthetic_comparable_witness() -> dict[str, object]:
        return {
            "status": "comparable",
            "model": "google/gemini-3.1-flash-lite",
            "provider_calls": 22,
            "semantic_passes": 20,
        }

    def test_protocol_freezes_four_standard_configurations_calls_and_cost(self) -> None:
        corpus = policy.load_policy_corpus()
        with patch.object(
            policy,
            "historical_primary_witness",
            return_value=self._synthetic_comparable_witness(),
        ):
            protocol = policy.model_comparison_protocol_document(
                corpus,
                freeze_commit="f" * 40,
            )

        self.assertEqual(protocol["planned_provider_calls"], 88)
        self.assertLessEqual(protocol["planned_provider_calls"], 96)
        self.assertEqual(protocol["max_tokens"], 500)
        self.assertEqual(protocol["timeout_s"], 15)
        self.assertEqual(protocol["max_estimated_cost_usd"], 0.28)
        self.assertEqual(protocol["repetitions"], 2)
        self.assertEqual(
            [(item["model"], item["reasoning_effort"]) for item in protocol["configurations"]],
            [
                ("google/gemini-3.7-flash", "medium"),
                ("google/gemini-3.7-flash", "high"),
                ("openai/gpt-5.6-luna-pro", "medium"),
                ("openai/gpt-5.6-luna-pro", "high"),
            ],
        )
        self.assertTrue(all(item["transport"] == "standard" for item in protocol["configurations"]))
        self.assertTrue(all(not item["batch"] for item in protocol["configurations"]))
        self.assertEqual(protocol["historical_control"]["semantic_passes"], 20)
        self.assertEqual(protocol["historical_control"]["provider_calls"], 22)
        self.assertTrue(protocol["decision_rule"]["no_automatic_runtime_cutover"])
        self.assertFalse(protocol["decision_rule"]["thresholds_mutable_after_results"])

        with patch.object(policy, "MODEL_COMPARISON_PLANNED_CALLS", 97):
            with self.assertRaisesRegex(ValueError, "provider_call_cap_exceeded"):
                policy.model_comparison_protocol_document(
                    corpus,
                    freeze_commit="f" * 40,
                )

    def test_supported_effort_and_historical_fingerprints_are_not_assumed(self) -> None:
        original = policy.MODEL_COMPARISON_CONFIGURATIONS["gemini_3_7_flash_high"]
        unsupported = dict(original, supported_efforts=("medium", "low"))
        with patch.dict(
            policy.MODEL_COMPARISON_CONFIGURATIONS,
            {"gemini_3_7_flash_high": unsupported},
        ):
            with self.assertRaisesRegex(ValueError, "unsupported_model_comparison_effort"):
                policy.build_model_comparison_payload(
                    [
                        {"role": "system", "content": "synthetic-system"},
                        {"role": "user", "content": "synthetic-user"},
                    ],
                    "gemini_3_7_flash_high",
                )

        with patch.object(policy, "HISTORICAL_SCORER_SOURCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(ValueError, "historical_primary_witness_not_comparable"):
                policy.historical_primary_witness()

    def test_payloads_use_model_specific_reasoning_without_sampling_or_tiers(self) -> None:
        messages = [
            {"role": "system", "content": "synthetic-system"},
            {"role": "user", "content": "synthetic-user"},
        ]
        payloads = {
            config_id: policy.build_model_comparison_payload(messages, config_id)
            for config_id in policy.MODEL_COMPARISON_CONFIGURATION_IDS
        }

        for config_id, payload in payloads.items():
            with self.subTest(configuration=config_id):
                self.assertEqual(payload["messages"], messages)
                self.assertEqual(payload["max_tokens"], 500)
                self.assertEqual(
                    payload["reasoning"],
                    {
                        "effort": policy.MODEL_COMPARISON_CONFIGURATIONS[config_id][
                            "reasoning_effort"
                        ],
                        "exclude": True,
                    },
                )
                self.assertEqual(
                    payload["provider"],
                    {"allow_fallbacks": False, "require_parameters": True},
                )
                for forbidden in (
                    "temperature",
                    "top_p",
                    "response_format",
                    "service_tier",
                    "models",
                ):
                    self.assertNotIn(forbidden, payload)
                self.assertNotIn(":batch", payload["model"])
                policy.validate_model_comparison_payload(payload, config_id)

        mutant = copy.deepcopy(payloads["gemini_3_7_flash_medium"])
        mutant["temperature"] = 0.0
        with self.assertRaisesRegex(ValueError, "invalid_model_comparison_payload"):
            policy.validate_model_comparison_payload(mutant, "gemini_3_7_flash_medium")
        mutant = copy.deepcopy(payloads["luna_pro_high"])
        mutant["model"] += ":batch"
        with self.assertRaisesRegex(ValueError, "invalid_model_comparison_payload"):
            policy.validate_model_comparison_payload(mutant, "luna_pro_high")
        mutant = copy.deepcopy(payloads["luna_pro_high"])
        mutant["service_tier"] = "priority"
        with self.assertRaisesRegex(ValueError, "invalid_model_comparison_payload"):
            policy.validate_model_comparison_payload(mutant, "luna_pro_high")

    def test_order_is_alternated_and_only_configuration_fields_change(self) -> None:
        orders = [
            policy.model_comparison_configuration_order(case_index, repetition)
            for case_index in range(11)
            for repetition in (1, 2)
        ]
        self.assertTrue(all(set(order) == set(policy.MODEL_COMPARISON_CONFIGURATION_IDS) for order in orders))
        self.assertGreater(len({tuple(order) for order in orders}), 1)

        case = policy.load_policy_corpus()["cases"][0]
        prompt = (REPO_ROOT / "app/prompts/validation_agent.txt").read_text(
            encoding="utf-8"
        ).strip()
        messages = policy.build_policy_message_pair(case, prompt)["current"]
        payloads = [
            policy.build_model_comparison_payload(messages, config_id)
            for config_id in policy.MODEL_COMPARISON_CONFIGURATION_IDS
        ]
        self.assertEqual(len({policy.model_comparison_messages_sha256(item) for item in payloads}), 1)
        normalized = []
        for payload in payloads:
            item = copy.deepcopy(payload)
            item["model"] = "<MODEL>"
            item["reasoning"]["effort"] = "<EFFORT>"
            normalized.append(item)
        self.assertEqual(len({json.dumps(item, sort_keys=True) for item in normalized}), 1)

    def test_historical_primary_witness_rejects_changed_runtime_contract(self) -> None:
        with self.assertRaisesRegex(ValueError, "historical_primary_witness_not_comparable"):
            policy.historical_primary_witness()

    def test_model_artifact_guard_rejects_routing_metrics_and_raw_mutations(self) -> None:
        record = policy.synthetic_valid_model_comparison_call_record()
        self.assertEqual(
            policy.validate_model_comparison_record(record)["record_type"],
            "provider_call",
        )
        mutations = (
            {"reasoning_text": "SYNTHETIC RAW REASONING"},
            {"observed_model": "other/model"},
            {"observed_provider": "synthetic provider narrative"},
            {"requested_reasoning_effort": "low"},
            {"batch": True},
            {"observed_service_tier": "flex"},
            {"cost_usd": None},
            {"reasoning_tokens": None},
        )
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                with self.assertRaises(ValueError):
                    policy.validate_model_comparison_record(
                        dict(record, **mutation)
                    )

    def test_configuration_eligibility_rejects_missing_or_semantically_false_calls(self) -> None:
        records = policy.synthetic_passing_model_comparison_records(
            "gemini_3_7_flash_medium"
        )
        summary = policy.summarize_model_comparison_configuration(
            records,
            "gemini_3_7_flash_medium",
        )
        self.assertEqual(summary["status"], "eligible")
        self.assertEqual(summary["semantic_passes"], 22)

        missing = policy.summarize_model_comparison_configuration(
            records[:-1],
            "gemini_3_7_flash_medium",
        )
        self.assertEqual(missing["status"], "inconclusive")

        critical = copy.deepcopy(records)
        target = next(item for item in critical if item["case_id"] == "L4C1-VAL-005")
        target.update(
            final_judgment_posture="answer",
            final_output_regime="simple",
            scorer_pass=False,
            reason_code="pair_not_allowed",
            semantic_codes=["pair_not_allowed"],
        )
        rejected = policy.summarize_model_comparison_configuration(
            critical,
            "gemini_3_7_flash_medium",
        )
        self.assertEqual(rejected["status"], "non_eligible")
        self.assertIn("critical_case_005_failed", rejected["reason_codes"])

        missed_presence = copy.deepcopy(records)
        target = next(
            item for item in missed_presence if item["case_id"] == "L4C1-VAL-003"
        )
        target.update(
            final_output_regime="simple",
            scorer_pass=False,
            reason_code="missed_presence",
            semantic_codes=["missed_presence"],
        )
        rejected_presence = policy.summarize_model_comparison_configuration(
            missed_presence,
            "gemini_3_7_flash_medium",
        )
        self.assertEqual(rejected_presence["status"], "non_eligible")
        self.assertIn("presence_case_003_failed", rejected_presence["reason_codes"])

        invalid = copy.deepcopy(records)
        target = invalid[0]
        target.update(
            status="invalid_json",
            reason_code="invalid_json",
            final_judgment_posture=None,
            final_output_regime=None,
            scorer_pass=False,
            semantic_codes=[],
        )
        inconclusive = policy.summarize_model_comparison_configuration(
            invalid,
            "gemini_3_7_flash_medium",
        )
        self.assertEqual(inconclusive["status"], "inconclusive")
        self.assertEqual(inconclusive["reason_codes"], ["provider_result_invalid"])

    def test_recommendation_never_converts_evaluation_into_runtime_cutover(self) -> None:
        summaries = [
            policy.summarize_model_comparison_configuration(
                policy.synthetic_passing_model_comparison_records(config_id),
                config_id,
            )
            for config_id in policy.MODEL_COMPARISON_CONFIGURATION_IDS
        ]
        decision = policy.model_comparison_recommendation(summaries)

        self.assertIn(
            decision["recommendation"],
            {
                "human_tradeoff_required",
                *(f"recommend_{config_id}" for config_id in policy.MODEL_COMPARISON_CONFIGURATION_IDS),
            },
        )
        self.assertFalse(decision["runtime_cutover_authorized"])

        one_short = copy.deepcopy(summaries)
        one_short[0]["semantic_passes"] = 21
        one_short[0]["status"] = "non_eligible"
        self.assertNotIn(
            one_short[0]["configuration_id"],
            policy.model_comparison_recommendation(one_short)["eligible_configurations"],
        )

        independent = copy.deepcopy(one_short)
        independent[0] = policy.summarize_model_comparison_configuration(
            policy.synthetic_passing_model_comparison_records(
                "gemini_3_7_flash_medium"
            ),
            "gemini_3_7_flash_medium",
        )
        independent[1]["status"] = "inconclusive"
        independent[1]["reason_codes"] = ["provider_result_invalid"]
        for index in (2, 3):
            independent[index]["status"] = "non_eligible"
            independent[index]["reason_codes"] = ["semantic_failure"]
        independent_decision = policy.model_comparison_recommendation(independent)
        self.assertEqual(
            independent_decision["recommendation"],
            "recommend_gemini_3_7_flash_medium",
        )
        self.assertEqual(
            independent_decision["eligible_configurations"],
            ["gemini_3_7_flash_medium"],
        )
        self.assertFalse(independent_decision["runtime_cutover_authorized"])

    def test_openrouter_client_reports_service_tier_without_reasoning_text(self) -> None:
        client = openrouter.OpenRouterClient(
            openrouter.OpenRouterConfig(
                base_url="https://synthetic.invalid/api/v1",
                api_key="synthetic-key",
            )
        )
        with patch.object(openrouter.requests, "post", return_value=_SyntheticResponse()):
            observed = client.chat_completion(
                {"model": "google/gemini-3.7-flash", "messages": []},
                caller="validation_agent",
                timeout_s=15,
            )

        self.assertEqual(observed["service_tier"], "default")
        self.assertNotIn("reasoning", observed)
        self.assertNotIn("reasoning_details", observed)
        self.assertNotIn("SYNTHETIC_REASONING_MUST_NOT_ESCAPE", json.dumps(observed))

    def test_live_orchestrator_makes_exactly_88_calls_and_writes_93_records(self) -> None:
        class SyntheticClient:
            def __init__(self) -> None:
                self.calls: list[dict] = []

            def chat_completion(self, payload: dict, *, caller: str, timeout_s: int) -> dict:
                self.calls.append(copy.deepcopy(payload))
                return {
                    "ok": True,
                    "status_code": 200,
                    "elapsed_ms": 10.0,
                    "error": None,
                    "raw_text": json.dumps(
                        {
                            "schema_version": "v1",
                            "final_judgment_posture": "answer",
                            "final_output_regime": "simple",
                            "arbiter_reason": "synthetic",
                        }
                    ),
                    "finish_reason": "stop",
                    "native_finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 100,
                        "completion_tokens": 20,
                        "total_tokens": 120,
                        "completion_tokens_details": {"reasoning_tokens": 10},
                    },
                    "cost_estimate_usd": 0.0001,
                    "cost_estimate_source": "openrouter_models_pricing",
                    "generation_id": "synthetic",
                    "model": payload["model"],
                    "provider": (
                        "Google AI Studio"
                        if payload["model"].startswith("google/")
                        else "OpenAI"
                    ),
                    "service_tier": "default",
                }

        client = SyntheticClient()
        with TemporaryDirectory() as tmp:
            output = Path(tmp) / "model-comparison.jsonl"
            with patch.object(
                policy,
                "historical_primary_witness",
                return_value=self._synthetic_comparable_witness(),
            ):
                result = policy.run_model_comparison_campaign(
                    output_path=output,
                    freeze_commit="f" * 40,
                    client=client,
                )
            records = [
                json.loads(line)
                for line in output.read_text(encoding="utf-8").splitlines()
            ]

        self.assertEqual(len(client.calls), 88)
        self.assertEqual(len(records), 93)
        self.assertEqual(sum(item["record_type"] == "provider_call" for item in records), 88)
        self.assertEqual(sum(item["record_type"] == "configuration_summary" for item in records), 4)
        self.assertEqual(sum(item["record_type"] == "campaign_summary" for item in records), 1)
        self.assertTrue(all(policy.validate_model_comparison_record(item) for item in records))
        self.assertFalse(result["decision"]["runtime_cutover_authorized"])
        serialized = json.dumps(records)
        self.assertNotIn("synthetic-system", serialized)
        self.assertNotIn("synthetic-user", serialized)
        self.assertNotIn("arbiter_reason", serialized)

    def test_reclassification_separates_invalid_json_without_new_provider_output(self) -> None:
        records = [
            record
            for config_id in policy.MODEL_COMPARISON_CONFIGURATION_IDS
            for record in policy.synthetic_passing_model_comparison_records(config_id)
        ]
        target = records[0]
        target.update(
            status="invalid_json",
            reason_code="missed_presence",
            final_judgment_posture=None,
            final_output_regime=None,
            scorer_pass=False,
            semantic_codes=["missed_presence"],
        )

        with patch.object(
            policy,
            "historical_primary_witness",
            return_value=self._synthetic_comparable_witness(),
        ):
            rebuilt = policy.reclassify_model_comparison_records(
                records,
                freeze_commit="f" * 40,
            )

        self.assertEqual(len(rebuilt), 93)
        normalized = next(
            record
            for record in rebuilt
            if record["record_type"] == "provider_call"
            and record["sequence_index"] == target["sequence_index"]
            and record["configuration_id"] == target["configuration_id"]
        )
        self.assertEqual(normalized["reason_code"], "invalid_json")
        self.assertEqual(normalized["semantic_codes"], [])
        summary = next(
            record
            for record in rebuilt
            if record["record_type"] == "configuration_summary"
            and record["configuration_id"] == target["configuration_id"]
        )
        self.assertEqual(summary["status"], "inconclusive")
        self.assertEqual(summary["reason_codes"], ["provider_result_invalid"])

    def test_durable_model_comparison_artifact_recommends_the_unique_eligible_candidate(self) -> None:
        path = (
            REPO_ROOT
            / "benchmark/results/validation_agent/2026-08-29-lot4c1-validation-primary-models.jsonl"
        )
        records = [
            json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]

        self.assertEqual(
            hashlib.sha256(path.read_bytes()).hexdigest(),
            "b0f6f05d00b12bc0ae72404f493d72df72a5c600dc724381d7563c0759c136b1",
        )
        self.assertEqual(len(records), 93)
        self.assertTrue(all(policy.validate_model_comparison_record(record) for record in records))
        calls = [record for record in records if record["record_type"] == "provider_call"]
        self.assertEqual(len(calls), 88)
        self.assertEqual(sum(record["status"] == "invalid_json" for record in calls), 11)
        self.assertTrue(
            all(
                record["reason_code"] == "invalid_json"
                and record["semantic_codes"] == []
                for record in calls
                if record["status"] == "invalid_json"
            )
        )
        summary = records[-1]
        self.assertEqual(
            summary["recommendation"],
            "recommend_gemini_3_7_flash_medium",
        )
        self.assertEqual(summary["eligible_configurations"], ["gemini_3_7_flash_medium"])
        self.assertEqual(summary["provider_calls"], 88)
        self.assertEqual(summary["valid_calls"], 77)
        self.assertEqual(summary["cost_usd"], 0.21959182)
        self.assertFalse(summary["runtime_cutover_authorized"])


if __name__ == "__main__":
    unittest.main()
