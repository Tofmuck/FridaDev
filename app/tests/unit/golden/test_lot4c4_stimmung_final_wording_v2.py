from __future__ import annotations

import copy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_diagnostic
from benchmark.suites.stimmung import final_wording_execution_v2
from benchmark.suites.stimmung import final_wording_protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2


REPO_ROOT = Path(__file__).resolve().parents[4]


class _SyntheticClient:
    def __init__(
        self,
        *,
        missing_sequence: int | None = None,
        cost_usd: float = 0.000225,
    ) -> None:
        self.calls: list[dict[str, object]] = []
        self.missing_sequence = missing_sequence
        self.cost_usd = cost_usd

    def chat_completion(
        self,
        payload: dict[str, object],
        *,
        caller: str,
        timeout_s: int,
    ) -> dict[str, object]:
        sequence = len(self.calls) + 1
        self.calls.append(
            {"payload": copy.deepcopy(payload), "caller": caller, "timeout_s": timeout_s}
        )
        if sequence == self.missing_sequence:
            return {
                "ok": False,
                "status_code": None,
                "elapsed_ms": 2.0,
                "error": "synthetic timeout",
                "raw_text": None,
                "finish_reason": None,
                "native_finish_reason": None,
                "usage": {},
                "cost_estimate_usd": None,
                "model": "",
                "provider": "",
            }
        return {
            "ok": True,
            "status_code": 200,
            "elapsed_ms": 1.0,
            "error": None,
            "raw_text": f"SYNTHETIC_TEST_RESPONSE_{sequence}",
            "finish_reason": "stop",
            "native_finish_reason": "stop",
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 10,
                "total_tokens": 110,
            },
            "cost_estimate_usd": self.cost_usd,
            "model": "openai/gpt-5.1",
            "provider": "OpenAI",
        }


def _synthetic_ratings(packet: dict[str, object]) -> dict[str, object]:
    ratings: list[dict[str, object]] = []
    for item in packet["items"]:
        if item["comparison_kind"] == "causal_transition":
            rating = {
                "blind_id": item["blind_id"],
                "delicacy_effect": "better_a",
                "formulation_fit": "better_a",
                "psychologization": "none",
                "certainty_change": "none",
                "truth_or_evidence_change": "none",
                "masked_target": "none",
            }
        else:
            rating = {
                "blind_id": item["blind_id"],
                "formulation_fit": "adequate",
                "artificial_caution": "absent",
                "psychologization": "absent",
                "certainty_change": "absent",
                "truth_or_evidence_change": "absent",
                "masked_target": "absent",
            }
        ratings.append(rating)
    return {
        "schema_version": final_wording_rating_v2.RATINGS_SCHEMA_VERSION,
        "packet_sha256": packet["packet_sha256"],
        "rating_source": "synthetic_test",
        "rater_id": "offline_workflow_test",
        "ratings_created_outside_runner": True,
        "ratings": ratings,
    }


class Lot4C4ProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = final_wording_protocol_v2.load_corpus(REPO_ROOT)
        cls.protocol = final_wording_protocol_v2.build_protocol(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )
        cls.schedule = final_wording_protocol_v2.build_request_schedule(
            REPO_ROOT,
            cls.protocol,
        )

    def test_corpus_v2_is_answerable_from_explicit_provider_visible_matter(self) -> None:
        summary = final_wording_protocol_v2.validate_corpus(self.corpus)

        self.assertEqual(summary["case_count"], 14)
        self.assertEqual(summary["provider_case_count"], 12)
        self.assertEqual(summary["causal_transition_case_count"], 6)
        self.assertEqual(summary["absolute_countercase_count"], 6)
        self.assertEqual(summary["provider_visible_fact_count"], 17)

        for case in self.corpus["cases"]:
            if not case["provider_eligible"]:
                continue
            for fact in case["epistemic_matter"]["factual_basis"]:
                source = fact["visible_at"]["source"]
                if source == "user":
                    content = case["dialogue"]["user"]
                else:
                    content = case["dialogue"]["history"][fact["visible_at"]["index"]][
                        "content"
                    ]
                self.assertIn(fact["literal"], content)

        hidden = copy.deepcopy(self.corpus)
        hidden["cases"][0]["epistemic_matter"]["factual_basis"][0]["literal"] = (
            "fait absent du dialogue"
        )
        with self.assertRaisesRegex(ValueError, "required_fact_not_provider_visible"):
            final_wording_protocol_v2.validate_corpus(hidden)

        missing_list = copy.deepcopy(self.corpus)
        recap = next(case for case in missing_list["cases"] if case["id"] == "L4C4-FW2-004")
        recap["dialogue"]["history"][0]["content"] = "Voici les points."
        with self.assertRaisesRegex(ValueError, "required_fact_not_provider_visible"):
            final_wording_protocol_v2.validate_corpus(missing_list)

    def test_schedule_has_24_causal_calls_and_12_single_arm_countercase_calls(self) -> None:
        summary = final_wording_protocol_v2.validate_schedule(self.corpus, self.schedule)

        self.assertEqual(len(self.schedule), 36)
        self.assertEqual(summary["causal_call_count"], 24)
        self.assertEqual(summary["absolute_call_count"], 12)
        self.assertEqual(summary["causal_comparison_count"], 12)
        self.assertEqual(summary["absolute_observation_count"], 12)
        self.assertEqual(summary["unauthorized_difference_count"], 0)
        self.assertEqual(summary["identical_causal_pair_count"], 0)
        self.assertEqual(summary["raw_stimmung_occurrence_count"], 0)

        countercase_items = [
            item for item in self.schedule if item["comparison_kind"] == "absolute_countercase"
        ]
        self.assertEqual({item["variant"] for item in countercase_items}, {"runtime_active"})
        self.assertEqual(
            len({(item["case_id"], item["repetition"]) for item in countercase_items}),
            12,
        )

        doubled = copy.deepcopy(self.schedule)
        countercase = next(
            item for item in doubled if item["comparison_kind"] == "absolute_countercase"
        )
        doubled.append({**copy.deepcopy(countercase), "sequence": 37})
        with self.assertRaisesRegex(ValueError, "schedule_cardinality_invalid"):
            final_wording_protocol_v2.validate_schedule(self.corpus, doubled)

    def test_protocol_v2_has_honest_cost_names_and_detects_every_frozen_mutation(self) -> None:
        summary = final_wording_protocol_v2.validate_protocol(self.protocol, REPO_ROOT)

        self.assertEqual(
            self.protocol["protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_2",
        )
        self.assertEqual(summary["expected_call_count"], 36)
        self.assertEqual(self.protocol["absolute_call_cap"], 36)
        self.assertEqual(self.protocol["model"], "openai/gpt-5.1")
        self.assertNotIn("temperature", self.protocol)
        self.assertNotIn("top_p", self.protocol)
        self.assertEqual(self.protocol["max_tokens"], 8192)
        self.assertEqual(self.protocol["reasoning"], {"effort": "high", "exclude": True})
        self.assertEqual(self.protocol["timeout_s"], 900)
        self.assertNotIn("theoretical_max_cost_usd", self.protocol)
        self.assertNotIn("estimated_max_cost_usd", self.protocol)
        self.assertGreater(self.protocol["calculated_completion_ceiling_cost_usd"], 0)
        self.assertLessEqual(
            self.protocol["budget_with_safety_margin_usd"],
            self.protocol["absolute_cost_cap_usd"],
        )
        self.assertEqual(
            self.protocol["transport_policy"],
            {
                "mode": "standard",
                "batch": False,
                "flex": False,
                "priority": False,
                "retry_count": 0,
                "automatic_model_fallback": False,
                "provider_fallbacks": False,
                "require_parameters": True,
                "model_endpoint_preflight": True,
                "canary_sequence": 1,
            },
        )

        for path, value in (
            (("expected_call_count",), 48),
            (("absolute_call_cap",), 48),
            (("model",), "openai/gpt-5.2"),
            (("temperature",), 0.7),
            (("transport_policy", "retry_count"), 1),
            (("transport_policy", "provider_fallbacks"), True),
        ):
            mutated = copy.deepcopy(self.protocol)
            target = mutated
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    final_wording_protocol_v2.validate_protocol(mutated, REPO_ROOT)

    def test_v1_remains_byte_frozen_and_is_explicitly_superseded(self) -> None:
        v1 = final_wording_diagnostic.build_protocol(REPO_ROOT, freeze_commit="f" * 40)
        self.assertEqual(v1["protocol_version"], "lot4c4_final_wording_provider_campaign_v1")
        self.assertEqual(v1["expected_call_count"], 48)
        self.assertEqual(
            self.protocol["supersedes_protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_1",
        )
        self.assertEqual(self.protocol["historical_v1_protocol_version"], v1["protocol_version"])
        self.assertEqual(self.protocol["v2_provider_calls_observed"], 0)
        self.assertEqual(self.protocol["v1_provider_calls_observed"], 0)
        historical_v2 = json.loads(
            (
                REPO_ROOT
                / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            historical_v2["status"],
            "phase_a_v2_frozen_separate_provider_go_required",
        )
        final_wording_diagnostic.validate_freeze_manifest(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )


class Lot4C4WorkflowV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = final_wording_protocol_v2.build_protocol(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )

    def test_cli_is_offline_without_complete_explicit_live_authorization(self) -> None:
        with mock.patch.object(
            final_wording_execution_v2.OpenRouterClient,
            "from_env",
            side_effect=AssertionError("network client must stay unreachable"),
        ):
            with self.assertRaises(SystemExit):
                final_wording_execution_v2.main(
                    ["--repo-root", str(REPO_ROOT), "--freeze-commit", "f" * 40]
                )
            with self.assertRaises(SystemExit):
                final_wording_execution_v2.main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--freeze-commit",
                        "f" * 40,
                        "--execute-live",
                    ]
                )
            with self.assertRaises(SystemExit):
                final_wording_execution_v2.main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--freeze-commit",
                        "f" * 40,
                        "--dry-run",
                        "--resume",
                    ]
                )
            self.assertEqual(
                final_wording_execution_v2.main(
                    [
                        "--repo-root",
                        str(REPO_ROOT),
                        "--freeze-commit",
                        "f" * 40,
                        "--dry-run",
                    ]
                ),
                0,
            )

    def test_synthetic_runner_builds_private_blind_packet_mapping_and_content_free_ledger(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            review_dir = Path(parent) / "review"
            client = _SyntheticClient()
            result = final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=client,
                output_dir=output_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )

            self.assertEqual(result["status"], "human_rating_required")
            self.assertEqual(result["attempted_call_count"], 36)
            self.assertEqual(len(client.calls), 36)
            for name in ("blind_mapping.json", "call_ledger.json", "private_outputs.json"):
                path = output_dir / name
                self.assertTrue(path.is_file())
                self.assertEqual(path.stat().st_mode & 0o777, 0o600)

            packet_text = (review_dir / "rating_packet.json").read_text(encoding="utf-8")
            mapping_text = (output_dir / "blind_mapping.json").read_text(encoding="utf-8")
            ledger_text = (output_dir / "call_ledger.json").read_text(encoding="utf-8")
            packet = json.loads(packet_text)
            self.assertEqual(len(packet["items"]), 24)
            self.assertNotIn('"variant"', packet_text)
            self.assertNotIn('"control"', packet_text)
            self.assertNotIn('"treatment"', packet_text)
            self.assertIn('"variant"', mapping_text)
            self.assertNotIn("SYNTHETIC_TEST_RESPONSE", ledger_text)
            self.assertNotIn('"raw_text"', ledger_text)

    def test_incomplete_provider_shape_is_not_a_semantic_result(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            review_dir = Path(parent) / "review"
            result = final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=_SyntheticClient(missing_sequence=3),
                output_dir=output_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            ledger = json.loads((output_dir / "call_ledger.json").read_text(encoding="utf-8"))

            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(ledger["status_counts"]["timeout"], 1)
            self.assertFalse(ledger["outputs_complete"])
            self.assertNotIn("decision", ledger)
            self.assertFalse(review_dir.exists())

    def test_runner_rejects_fake_provider_provenance_raw_repo_path_and_cost_overrun(self) -> None:
        client = _SyntheticClient()
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            with self.assertRaisesRegex(ValueError, "explicit_execution_authorization_required"):
                final_wording_execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.protocol,
                    client=client,
                    output_dir=output_dir,
                    review_export_dir=Path(parent) / "review",
                    execution_authorized=False,
                    evidence_source="synthetic_test",
                )
            self.assertEqual(client.calls, [])
            with self.assertRaisesRegex(
                ValueError, "provider_provenance_requires_openrouter_client"
            ):
                final_wording_execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.protocol,
                    client=client,
                    output_dir=output_dir,
                    review_export_dir=Path(parent) / "review",
                    execution_authorized=True,
                    evidence_source="main_model_provider",
                )
            self.assertEqual(client.calls, [])

        with self.assertRaisesRegex(ValueError, "raw_packet_inside_repo_forbidden"):
            final_wording_execution_v2._validate_output_dir(
                REPO_ROOT,
                REPO_ROOT / "benchmark/results/forbidden-raw-campaign",
            )

        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            expensive = _SyntheticClient(cost_usd=1.0)
            output_dir = Path(parent) / "campaign"
            result = final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=expensive,
                output_dir=output_dir,
                review_export_dir=Path(parent) / "review",
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            self.assertEqual(result["status"], "campaign_incomplete")
            self.assertEqual(result["reason_code"], "cost_cap_would_be_exceeded")
            self.assertEqual(len(expensive.calls), 4)
            self.assertTrue((output_dir / "call_ledger.json").is_file())

    def test_synthetic_ratings_validate_workflow_but_cannot_yield_provider_verdict(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            review_dir = Path(parent) / "review"
            durable_path = Path(parent) / "durable.json"
            final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=_SyntheticClient(),
                output_dir=output_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            packet_path = review_dir / "rating_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            ratings = _synthetic_ratings(packet)
            ratings_path = review_dir / "ratings.json"
            ratings_path.write_text(json.dumps(ratings), encoding="utf-8")
            os.chmod(ratings_path, 0o600)

            artifact = final_wording_rating_v2.finalize_campaign(
                campaign_dir=output_dir,
                rating_packet_path=packet_path,
                ratings_path=ratings_path,
                durable_output=durable_path,
            )

            self.assertEqual(artifact["decision"], "provider_campaign_required")
            self.assertEqual(artifact["reason_codes"], ["synthetic_workflow_only"])
            self.assertFalse(artifact["provider_results_observed"])
            self.assertTrue(durable_path.is_file())
            durable_text = durable_path.read_text(encoding="utf-8")
            self.assertNotIn("SYNTHETIC_TEST_RESPONSE", durable_text)
            self.assertNotIn('"outputs"', durable_text)
            self.assertNotIn('"raw_text"', durable_text)
            self.assertEqual(
                artifact["content_policy"],
                {
                    "raw_dialogue_included": False,
                    "raw_prompt_included": False,
                    "raw_provider_output_included": False,
                    "reasoning_text_included": False,
                    "exception_text_included": False,
                },
            )
            self.assertFalse(packet_path.exists())
            self.assertFalse((output_dir / "blind_mapping.json").exists())
            self.assertFalse(ratings_path.exists())
            self.assertTrue(final_wording_rating_v2.validate_durable_artifact(artifact))
            leaked_reason = copy.deepcopy(artifact)
            leaked_reason["reason_codes"] = ["raw exception text"]
            with self.assertRaisesRegex(ValueError, "durable_reason_codes_invalid"):
                final_wording_rating_v2.validate_durable_artifact(leaked_reason)
            fake_provider_result = copy.deepcopy(artifact)
            fake_provider_result["provider_results_observed"] = True
            with self.assertRaisesRegex(ValueError, "synthetic_provider_verdict_forbidden"):
                final_wording_rating_v2.validate_durable_artifact(fake_provider_result)

    def test_partial_or_self_declared_ratings_do_not_unblind_or_delete_material(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            review_dir = Path(parent) / "review"
            final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=_SyntheticClient(),
                output_dir=output_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            packet_path = review_dir / "rating_packet.json"
            packet = json.loads(packet_path.read_text(encoding="utf-8"))
            ratings = _synthetic_ratings(packet)
            ratings["ratings"].pop()
            ratings_path = review_dir / "ratings.json"
            ratings_path.write_text(json.dumps(ratings), encoding="utf-8")
            os.chmod(ratings_path, 0o600)
            mapping_path = output_dir / "blind_mapping.json"
            original_mapping = mapping_path.read_text(encoding="utf-8")
            mapping_path.write_text('{"must_not_be_read_before_ratings_validation":true}')
            os.chmod(mapping_path, 0o600)

            with self.assertRaisesRegex(ValueError, "ratings_incomplete"):
                final_wording_rating_v2.finalize_campaign(
                    campaign_dir=output_dir,
                    rating_packet_path=packet_path,
                    ratings_path=ratings_path,
                    durable_output=Path(parent) / "durable.json",
                )
            self.assertTrue(packet_path.exists())
            self.assertTrue((output_dir / "blind_mapping.json").exists())

            mapping_path.write_text(original_mapping, encoding="utf-8")
            os.chmod(mapping_path, 0o600)
            ratings = _synthetic_ratings(packet)
            ratings["rating_source"] = "provider"
            ratings_path.write_text(json.dumps(ratings), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "rating_source_invalid"):
                final_wording_rating_v2.finalize_campaign(
                    campaign_dir=output_dir,
                    rating_packet_path=packet_path,
                    ratings_path=ratings_path,
                    durable_output=Path(parent) / "durable.json",
                )

            delegated = _synthetic_ratings(packet)
            delegated["rating_source"] = "delegated_human_review"
            delegated["rater_id"] = "agent_judge"
            with self.assertRaisesRegex(ValueError, "rating_source_invalid"):
                final_wording_rating_v2.validate_ratings(
                    delegated,
                    packet=packet,
                    evidence_source="main_model_provider",
                )
            delegated["rating_source"] = "codex_assisted_review_for_tof"
            delegated["rater_id"] = "codex_for_tof"
            self.assertEqual(
                len(
                    final_wording_rating_v2.validate_ratings(
                        delegated,
                        packet=packet,
                        evidence_source="main_model_provider",
                    )
                ),
                24,
            )

    def test_scorer_counts_each_dimension_once_without_making_a_synthetic_verdict(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as parent:
            output_dir = Path(parent) / "campaign"
            review_dir = Path(parent) / "review"
            final_wording_execution_v2.run_campaign(
                repo_root=REPO_ROOT,
                protocol=self.protocol,
                client=_SyntheticClient(),
                output_dir=output_dir,
                review_export_dir=review_dir,
                execution_authorized=True,
                evidence_source="synthetic_test",
            )
            packet = json.loads((review_dir / "rating_packet.json").read_text(encoding="utf-8"))
            mapping = json.loads((output_dir / "blind_mapping.json").read_text(encoding="utf-8"))
            mapping_by_id = final_wording_rating_v2.validate_mapping(mapping, packet)
            ratings = _synthetic_ratings(packet)
            by_id = {item["blind_id"]: item for item in ratings["ratings"]}
            for blind_id, item in mapping_by_id.items():
                if item["comparison_kind"] != "causal_transition":
                    continue
                treatment_slot = next(
                    slot
                    for slot, detail in item["slots"].items()
                    if detail["variant"] == "treatment"
                )
                preferred = "better_a" if treatment_slot == "A" else "better_b"
                by_id[blind_id]["delicacy_effect"] = preferred
                by_id[blind_id]["formulation_fit"] = preferred
            metrics = final_wording_rating_v2._score_validated_ratings(by_id, mapping_by_id)
            self.assertEqual(metrics["transition_delicacy_improvement_rate"], 1.0)
            self.assertEqual(metrics["transition_formulation_improvement_rate"], 1.0)
            self.assertEqual(metrics["countercase_formulation_adequacy_rate"], 1.0)
            self.assertEqual(metrics["critical_failure_count"], 0)

            transition_id = next(
                blind_id
                for blind_id, item in mapping_by_id.items()
                if item["comparison_kind"] == "causal_transition"
            )
            by_id[transition_id]["psychologization"] = "both"
            mutated = final_wording_rating_v2._score_validated_ratings(by_id, mapping_by_id)
            self.assertEqual(mutated["critical_failure_count"], 1)
            decision = final_wording_rating_v2._decision(
                evidence_source="synthetic_test",
                ledger={"outputs_complete": True},
                metrics=mutated,
            )
            self.assertEqual(
                decision,
                ("provider_campaign_required", ["synthetic_workflow_only"], False),
            )


if __name__ == "__main__":
    unittest.main()
