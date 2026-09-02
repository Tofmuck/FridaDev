from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.suites.stimmung import dialogic_campaign
from app.tests.unit.golden.test_lot4s1_stimmung_provider_campaign import _WitnessClient


class Lot4C2StimmungSemanticStrengtheningTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.protocol = dialogic_campaign.build_strengthening_protocol(
            REPO_ROOT,
            freeze_commit="1" * 40,
        )
        historical_protocol = dialogic_campaign.build_protocol(
            REPO_ROOT,
            freeze_commit=dialogic_campaign.PHASE_A_FREEZE_COMMIT,
        )
        cls.historical_schedule = dialogic_campaign.build_request_schedule(
            REPO_ROOT,
            historical_protocol,
        )
        cls.candidate_schedule = dialogic_campaign.build_request_schedule(
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

    def test_protocol_freezes_candidate_and_all_non_prompt_inputs(self) -> None:
        summary = dialogic_campaign.validate_strengthening_protocol(
            self.protocol,
            REPO_ROOT,
        )

        self.assertEqual(summary["dialogue_count"], 16)
        self.assertEqual(summary["turn_count"], 69)
        self.assertEqual(summary["evaluated_step_count"], 32)
        self.assertEqual(summary["expected_call_count"], 276)
        self.assertLessEqual(summary["estimated_max_cost_usd"], 0.30)
        self.assertEqual(self.protocol["absolute_call_cap"], 276)
        self.assertEqual(
            self.protocol["models"],
            {
                "primary": "google/gemini-3.1-flash-lite",
                "fallback": "openai/gpt-5.4-nano",
            },
        )
        self.assertEqual(
            self.protocol["generation_params"],
            {"temperature": 0.1, "top_p": 1.0, "max_tokens": 220},
        )
        self.assertEqual(self.protocol["timeout_s"], 10)
        self.assertNotEqual(
            self.protocol["candidate_prompt_sha256"],
            self.protocol["runtime_prompt_baseline_sha256"],
        )

        threshold_mutant = copy.deepcopy(self.protocol)
        threshold_mutant["corpus_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "protocol_freeze_mismatch"):
            dialogic_campaign.validate_strengthening_protocol(
                threshold_mutant,
                REPO_ROOT,
            )

    def test_frozen_normalizer_provenance_survives_runtime_drift_and_rejects_mutation(self) -> None:
        self.assertEqual(
            self.protocol["normalizer_sha256"],
            dialogic_campaign.STRENGTHENING_FROZEN_NORMALIZER_SHA256,
        )
        self.assertNotEqual(
            dialogic_campaign._sha256_file(REPO_ROOT / "app/core/stimmung_agent.py"),
            self.protocol["normalizer_sha256"],
        )

        source = dialogic_campaign._strengthening_manifest_path(REPO_ROOT)
        manifest = json.loads(source.read_text(encoding="utf-8"))
        manifest["normalizer_sha256"] = "f" * 64
        with TemporaryDirectory() as tmp:
            mutant = Path(tmp) / source.name
            mutant.write_text(json.dumps(manifest), encoding="utf-8")
            with patch.object(
                dialogic_campaign,
                "_strengthening_manifest_path",
                return_value=mutant,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "strengthening_manifest_integrity_mismatch",
                ):
                    dialogic_campaign.build_strengthening_protocol(
                        REPO_ROOT,
                        freeze_commit="f" * 40,
                    )

    def test_candidate_changes_only_the_system_prompt_seen_by_the_provider(self) -> None:
        self.assertEqual(len(self.historical_schedule), 276)
        self.assertEqual(len(self.candidate_schedule), 276)
        for historical, candidate in zip(
            self.historical_schedule,
            self.candidate_schedule,
        ):
            self.assertEqual(
                {
                    key: historical[key]
                    for key in ("dialogue_id", "turn_id", "evaluated", "source", "repetition")
                },
                {
                    key: candidate[key]
                    for key in ("dialogue_id", "turn_id", "evaluated", "source", "repetition")
                },
            )
            historical_payload = copy.deepcopy(historical["payload"])
            candidate_payload = copy.deepcopy(candidate["payload"])
            historical_system = historical_payload["messages"][0].pop("content")
            candidate_system = candidate_payload["messages"][0].pop("content")
            self.assertNotEqual(historical_system, candidate_system)
            self.assertEqual(historical_payload, candidate_payload)

    def test_candidate_is_bounded_and_not_a_corpus_catalogue(self) -> None:
        candidate = dialogic_campaign.load_strengthening_candidate(REPO_ROOT)
        corpus, _ = dialogic_campaign._load_inputs(REPO_ROOT)

        self.assertLessEqual(len(candidate), 3200)
        self.assertNotIn("L4S0-ST-", candidate)
        for dialogue in corpus["dialogues"]:
            for turn in dialogue["turns"]:
                self.assertNotIn(turn["user"], candidate)
                self.assertNotIn(turn["assistant"], candidate)

    def test_fake_run_reuses_normalizer_real_aggregator_and_strict_decision(self) -> None:
        client = _WitnessClient(self.witness_by_dialogue, self.candidate_schedule)
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        validation = dialogic_campaign.validate_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )

        self.assertEqual(len(client.calls), 276)
        self.assertEqual(validation["call_count"], 276)
        self.assertEqual(validation["dialogue_score_count"], 64)
        self.assertEqual(validation["final_decision"], "pass")
        self.assertEqual(records[-1]["baseline_artifact_sha256"], self.protocol["baseline_artifact_sha256"])
        self.assertEqual(records[-1]["semantic_regression_count"], 0)
        self.assertTrue(records[-1]["semantic_regression_count_complete"])

    def test_candidate_decision_rejects_one_failure_or_incomplete_result(self) -> None:
        client = _WitnessClient(self.witness_by_dialogue, self.candidate_schedule)
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        scores = [record for record in records if record["record_type"] == "dialogue_score"]

        historical_records = dialogic_campaign.load_historical_provider_artifact(REPO_ROOT)
        historical_pass = next(
            item
            for item in historical_records
            if item.get("record_type") == "dialogue_score"
            and item.get("classification") == "pass"
        )
        failed = copy.deepcopy(scores)
        target = next(
            item
            for item in failed
            if item["source"] == historical_pass["source"]
            and item["repetition"] == historical_pass["repetition"]
            and item["dialogue_id"] == historical_pass["dialogue_id"]
        )
        target["classification"] = "fail"
        target["error_class"] = "semantic"
        target["reason_codes"] = ["signal_overcoded"]
        decision = dialogic_campaign.decide_strengthening_from_dialogue_scores(
            failed,
            historical_records=historical_records,
        )
        self.assertEqual(decision["decision"], "fail")
        self.assertEqual(decision["semantic_regression_count"], 1)
        self.assertTrue(decision["semantic_regression_count_complete"])

        incomplete = dialogic_campaign.decide_strengthening_from_dialogue_scores(
            scores[:-1],
            historical_records=historical_records,
        )
        self.assertEqual(incomplete["decision"], "inconclusive")
        self.assertFalse(incomplete["semantic_regression_count_complete"])

    def test_historical_artifact_stays_authoritative_and_unchanged(self) -> None:
        historical_records = dialogic_campaign.load_historical_provider_artifact(REPO_ROOT)
        historical_protocol = dialogic_campaign.build_protocol(
            REPO_ROOT,
            freeze_commit=dialogic_campaign.PHASE_A_FREEZE_COMMIT,
        )
        validation = dialogic_campaign.validate_artifact(
            historical_records,
            REPO_ROOT,
            historical_protocol,
        )

        self.assertEqual(validation["final_decision"], "strengthen")
        self.assertEqual(
            dialogic_campaign._sha256_file(dialogic_campaign._historical_artifact_path(REPO_ROOT)),
            self.protocol["baseline_artifact_sha256"],
        )

    def test_candidate_artifact_rejects_raw_content_and_fingerprint_drift(self) -> None:
        records = dialogic_campaign.run_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=_WitnessClient(self.witness_by_dialogue, self.candidate_schedule),
        )

        raw_mutant = copy.deepcopy(records)
        raw_mutant[0]["provider_output"] = "synthetic free text"
        with self.assertRaises(ValueError):
            dialogic_campaign.validate_content_free_record(raw_mutant[0])

        fingerprint_mutant = copy.deepcopy(records)
        fingerprint_mutant[0]["prompt_sha256"] = "f" * 64
        with self.assertRaisesRegex(ValueError, "call_protocol_fingerprint_mismatch"):
            dialogic_campaign.validate_artifact(
                fingerprint_mutant,
                REPO_ROOT,
                self.protocol,
            )

        free_reason_mutant = copy.deepcopy(records[-1])
        free_reason_mutant["reason_codes"] = ["synthetic conversational sentence"]
        with self.assertRaisesRegex(ValueError, "final_reason_invalid"):
            dialogic_campaign.validate_content_free_record(free_reason_mutant)

    def test_provider_artifact_is_content_free_and_reconstructible(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "benchmark/results/stimmung"
            / "2026-08-30-lot4c2-stimmung-strengthening-candidate.jsonl"
        )
        records = dialogic_campaign.load_jsonl(artifact_path)
        artifact_protocol = dialogic_campaign.build_strengthening_protocol(
            REPO_ROOT,
            freeze_commit="d69dc8b21e3df9bf4989a407e257c70a8305255d",
        )
        validation = dialogic_campaign.validate_artifact(
            records,
            REPO_ROOT,
            artifact_protocol,
        )

        self.assertEqual(validation["call_count"], 276)
        self.assertEqual(validation["dialogue_score_count"], 64)
        self.assertEqual(validation["final_decision"], "inconclusive")
        self.assertEqual(
            records[-1]["reason_codes"],
            ["provider_results_or_metrics_incomplete"],
        )
        self.assertEqual(
            sum(
                record.get("status") == "schema_error"
                for record in records
                if record.get("record_type") == "call"
            ),
            1,
        )
        self.assertEqual(records[-1]["semantic_regression_count"], 1)
        self.assertFalse(records[-1]["semantic_regression_count_complete"])

        false_zero = copy.deepcopy(records)
        false_zero[-1]["semantic_regression_count"] = 0
        with self.assertRaisesRegex(
            ValueError,
            "artifact_summary_reconstruction_mismatch",
        ):
            dialogic_campaign.validate_artifact(
                false_zero,
                REPO_ROOT,
                artifact_protocol,
            )
        self.assertEqual(
            dialogic_campaign._sha256_file(artifact_path),
            "637cbc1fac2b03378f451d6fc64f6b0c30b7d9cd183b59b5833e3ee62612c5c5",
        )


if __name__ == "__main__":
    unittest.main()
