"""Separate frozen v2.4 evidence from deliberately refused runner reuse."""

from __future__ import annotations

import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_execution_v2 as execution_v2
from benchmark.suites.stimmung import final_wording_finalization_v2 as finalization_v2
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol_v2
from benchmark.suites.stimmung import final_wording_rating_v2 as rating_v2


REPO_ROOT = Path(__file__).resolve().parents[4]
V24_FREEZE_COMMIT = "7fcf26d8d3991b6d64f586b89025b9404316e30e"
V24_MANIFEST_PATH = (
    REPO_ROOT
    / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_4.json"
)
V24_MANIFEST_SHA256 = "736cb6d83ab8c0626de8f7cc4cf3ba4a9c7ab494d69353a2d0383f361ca25f91"
V24_RESULT_PATH = (
    REPO_ROOT
    / "benchmark/results/stimmung/2026-09-01-lot4c4-final-wording-v2-4-gpt-5-1.json"
)
V24_RESULT_SHA256 = "7bcfd7f15b7941a3b1257594c3c0f694148a3aa4e1a3c4daba6cf1e182cdd2be"


class _UnreachableClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completion(self, payload: dict[str, object], **_: object) -> dict[str, object]:
        self.calls.append(payload)
        raise AssertionError("historical runner reached the provider boundary")


def _rating_material(
    schedule: list[dict[str, object]],
    protocol: dict[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    executions = [
        (
            plan,
            {
                "status": "valid",
                "raw_text": f"SYNTHETIC_OUTPUT_{plan['sequence']}",
            },
        )
        for plan in schedule
    ]
    return execution_v2._build_rating_material(
        corpus=protocol_v2.load_corpus(REPO_ROOT),
        protocol_sha=protocol_v2.protocol_sha256(protocol),
        evidence_source="synthetic_test",
        executions=executions,
    )


class Lot4C4ProtocolV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = protocol_v2.load_corpus(REPO_ROOT)
        cls.protocol, cls.schedule = finalization_v2.load_historical_protocol(
            REPO_ROOT,
            freeze_commit=V24_FREEZE_COMMIT,
        )
        raw = V24_MANIFEST_PATH.read_bytes()
        cls.manifest = json.loads(raw.decode("utf-8"))
        if hashlib.sha256(raw).hexdigest() != V24_MANIFEST_SHA256:
            raise AssertionError("v2.4 historical manifest changed")

    def test_corpus_v2_is_answerable_from_explicit_provider_visible_matter(self) -> None:
        summary = protocol_v2.validate_corpus(self.corpus)

        self.assertEqual(summary["case_count"], 14)
        self.assertEqual(summary["provider_case_count"], 12)
        self.assertEqual(summary["causal_transition_case_count"], 6)
        self.assertEqual(summary["absolute_countercase_count"], 6)
        self.assertEqual(summary["provider_visible_fact_count"], 17)

        for case in self.corpus["cases"]:
            if not case["provider_eligible"]:
                continue
            for fact in case["epistemic_matter"]["factual_basis"]:
                visible_at = fact["visible_at"]
                content = (
                    case["dialogue"]["user"]
                    if visible_at["source"] == "user"
                    else case["dialogue"]["history"][visible_at["index"]]["content"]
                )
                self.assertIn(fact["literal"], content)

        hidden = copy.deepcopy(self.corpus)
        hidden["cases"][0]["epistemic_matter"]["factual_basis"][0]["literal"] = (
            "fait absent du dialogue"
        )
        with self.assertRaisesRegex(ValueError, "required_fact_not_provider_visible"):
            protocol_v2.validate_corpus(hidden)

    def test_historical_schedule_has_exactly_24_bounded_candidate_calls(self) -> None:
        summary = protocol_v2.validate_schedule(self.corpus, self.schedule)
        self.assertEqual(summary["causal_call_count"], 24)
        self.assertEqual(summary["causal_comparison_count"], 12)
        self.assertEqual(summary["absolute_call_count"], 0)
        self.assertEqual(summary["unauthorized_difference_count"], 0)
        self.assertEqual(summary["identical_causal_pair_count"], 0)
        self.assertEqual(summary["raw_stimmung_occurrence_count"], 0)
        self.assertEqual(
            protocol_v2._sha256_text(
                json.dumps(
                    protocol_v2._schedule_fingerprint(self.schedule),
                    ensure_ascii=False,
                    sort_keys=True,
                    separators=(",", ":"),
                )
            ),
            self.manifest["schedule"]["sha256"],
        )

    def test_protocol_archive_is_valid_but_not_comparable_to_current_sources(self) -> None:
        self.assertEqual(
            self.protocol["protocol_version"],
            "lot4c4_final_wording_bounded_candidate_v2_4",
        )
        self.assertEqual(self.protocol["model"], "openai/gpt-5.1")
        self.assertEqual(self.protocol["expected_call_count"], 24)
        self.assertEqual(self.protocol["absolute_call_cap"], 24)
        self.assertLessEqual(
            self.protocol["budget_with_safety_margin_usd"],
            self.protocol["absolute_cost_cap_usd"],
        )
        self.assertEqual(
            self.protocol["input_fingerprints"],
            self.manifest["frozen_inputs"],
        )
        with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
            protocol_v2.validate_protocol(self.protocol, REPO_ROOT)

    def test_v1_and_v2_lineage_remain_byte_frozen_and_superseded(self) -> None:
        v1_path = (
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v1.json"
        )
        v1_raw = v1_path.read_bytes()
        self.assertEqual(
            hashlib.sha256(v1_raw).hexdigest(),
            "207b44a407b0b468540921e22ffa7a0a49f192770dc07ae31c18e7f57219e996",
        )
        v1 = json.loads(v1_raw.decode("utf-8"))
        self.assertEqual(v1["protocol_version"], "lot4c4_final_wording_provider_campaign_v1")
        self.assertEqual(v1["schedule"]["call_count"], 48)
        self.assertEqual(
            self.protocol["supersedes_protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_3",
        )
        self.assertFalse(self.manifest["supersedes"]["campaign_reusable"])
        self.assertEqual(
            self.manifest["frozen_inputs"]["superseded_freeze_v2_1_sha256"],
            "a3afa9e8537311a107694dfc1e780741cb37676a3afbd789e3917d3e48cbab10",
        )


class Lot4C4WorkflowV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol, cls.schedule = finalization_v2.load_historical_protocol(
            REPO_ROOT,
            freeze_commit=V24_FREEZE_COMMIT,
        )

    def test_cli_refuses_historical_dry_run_and_execution_before_credentials_or_output(self) -> None:
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            output = io.StringIO()
            with mock.patch.object(
                execution_v2.OpenRouterClient,
                "from_env",
                side_effect=AssertionError("credentials must stay unreachable"),
            ), redirect_stdout(output):
                with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                    execution_v2.main(
                        [
                            "--repo-root", str(REPO_ROOT),
                            "--freeze-commit", V24_FREEZE_COMMIT,
                            "--dry-run",
                        ]
                    )
                with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                    execution_v2.main(
                        [
                            "--repo-root", str(REPO_ROOT),
                            "--freeze-commit", V24_FREEZE_COMMIT,
                            "--execute-live",
                            "--output-dir", str(private),
                            "--review-export-dir", str(review),
                        ]
                    )
            self.assertEqual(output.getvalue(), "")
            self.assertFalse(private.exists())
            self.assertFalse(review.exists())

    def test_direct_runner_refuses_drift_before_client_progress_or_files(self) -> None:
        client = _UnreachableClient()
        progress: list[tuple[object, ...]] = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.protocol,
                    client=client,
                    output_dir=private,
                    review_export_dir=review,
                    execution_authorized=True,
                    evidence_source="synthetic_test",
                    progress=lambda *args: progress.append(args),
                    capability_progress=lambda *args: progress.append(args),
                )
            self.assertEqual(client.calls, [])
            self.assertEqual(progress, [])
            self.assertFalse(private.exists())
            self.assertFalse(review.exists())

    def test_blind_packet_mapping_and_ledger_builders_keep_separation(self) -> None:
        packet, mapping = _rating_material(self.schedule, self.protocol)
        packet_text = json.dumps(packet, sort_keys=True)
        mapping_text = json.dumps(mapping, sort_keys=True)
        self.assertEqual(len(packet["items"]), 12)
        self.assertNotIn('"variant"', packet_text)
        self.assertNotIn('"sequence"', packet_text)
        self.assertIn('"variant"', mapping_text)
        self.assertIn('"sequence"', mapping_text)
        self.assertEqual(len(rating_v2.validate_mapping(mapping, packet)), 12)

    def test_incomplete_provider_shape_remains_non_semantic(self) -> None:
        outcome = execution_v2._classify_provider_result(
            {
                "ok": False,
                "status_code": None,
                "error": "synthetic timeout",
                "raw_text": None,
                "finish_reason": None,
                "native_finish_reason": None,
                "usage": {},
                "cost_estimate_usd": None,
                "model": "",
                "provider": "",
            }
        )
        self.assertEqual(outcome["status"], "timeout")
        self.assertEqual(outcome["observed_model"], "unknown")
        self.assertEqual(outcome["observed_provider"], "unknown")
        self.assertIsNone(outcome["raw_text"])

    def test_retained_v24_result_is_exact_content_free_historical_evidence(self) -> None:
        raw = V24_RESULT_PATH.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), V24_RESULT_SHA256)
        artifact = json.loads(raw.decode("utf-8"))
        self.assertTrue(rating_v2.validate_durable_artifact(artifact))
        self.assertEqual(artifact["protocol_sha256"], protocol_v2.protocol_sha256(self.protocol))
        self.assertEqual(artifact["decision"], "fail")
        self.assertTrue(artifact["provider_results_observed"])
        self.assertEqual(artifact["route_counts"]["models"], {"openai/gpt-5.1": 24})
        self.assertFalse(any(artifact["content_policy"].values()))

    def test_partial_ratings_and_synthetic_scores_cannot_claim_a_provider_verdict(self) -> None:
        packet, mapping = _rating_material(self.schedule, self.protocol)
        ratings = {
            "schema_version": rating_v2.RATINGS_SCHEMA_VERSION,
            "packet_sha256": packet["packet_sha256"],
            "rating_source": "synthetic_test",
            "rater_id": "offline_workflow_test",
            "ratings_created_outside_runner": True,
            "ratings": [],
        }
        with self.assertRaisesRegex(ValueError, "ratings_incomplete"):
            rating_v2.validate_ratings(
                ratings,
                packet=packet,
                evidence_source="synthetic_test",
            )

        ratings["ratings"] = [
            {
                "blind_id": item["blind_id"],
                "delicacy_effect": "equivalent",
                "formulation_fit": "equivalent",
                "psychologization": "none",
                "certainty_change": "none",
                "truth_or_evidence_change": "none",
                "masked_target": "none",
            }
            for item in packet["items"]
        ]
        ratings_by_id = rating_v2.validate_ratings(
            ratings,
            packet=packet,
            evidence_source="synthetic_test",
        )
        metrics = rating_v2._score_validated_ratings(
            ratings_by_id,
            rating_v2.validate_mapping(mapping, packet),
        )
        self.assertEqual(
            rating_v2._decision(
                evidence_source="synthetic_test",
                ledger={"outputs_complete": True},
                metrics=metrics,
            ),
            ("provider_campaign_required", ["synthetic_workflow_only"], False),
        )

    def test_scorer_still_counts_each_dimension_once_without_rebuilding_campaign(self) -> None:
        packet, mapping = _rating_material(self.schedule, self.protocol)
        mapping_by_id = rating_v2.validate_mapping(mapping, packet)
        ratings: dict[str, dict[str, object]] = {}
        for item in packet["items"]:
            ratings[item["blind_id"]] = {
                "blind_id": item["blind_id"],
                "delicacy_effect": "equivalent",
                "formulation_fit": "equivalent",
                "psychologization": "none",
                "certainty_change": "none",
                "truth_or_evidence_change": "none",
                "masked_target": "none",
            }
        for blind_id, item in mapping_by_id.items():
            candidate_slot = next(
                slot
                for slot, detail in item["slots"].items()
                if detail["variant"] == "bounded_candidate"
            )
            preferred = "better_a" if candidate_slot == "A" else "better_b"
            ratings[blind_id]["delicacy_effect"] = preferred
            ratings[blind_id]["formulation_fit"] = preferred
        metrics = rating_v2._score_validated_ratings(ratings, mapping_by_id)
        self.assertEqual(metrics["transition_delicacy_improvement_rate"], 1.0)
        self.assertEqual(metrics["transition_formulation_improvement_rate"], 1.0)
        self.assertEqual(metrics["critical_failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
