"""Authenticate v2.1 evidence without treating its superseded runner as current."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_execution_v2 as execution_v2
from benchmark.suites.stimmung import final_wording_finalization_v2 as finalization_v2


REPO_ROOT = Path(__file__).resolve().parents[4]
V21_MANIFEST_PATH = (
    REPO_ROOT
    / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_1.json"
)
V21_MANIFEST_SHA256 = "a3afa9e8537311a107694dfc1e780741cb37676a3afbd789e3917d3e48cbab10"
V24_FREEZE_COMMIT = "7fcf26d8d3991b6d64f586b89025b9404316e30e"


class _UnreachableClient:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def chat_completion(self, payload: dict[str, object], **_: object) -> dict[str, object]:
        self.calls.append(payload)
        raise AssertionError("historical runner reached the provider boundary")


class Lot4C4WorkflowV21Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = V21_MANIFEST_PATH.read_bytes()
        cls.manifest = json.loads(raw.decode("utf-8"))
        if hashlib.sha256(raw).hexdigest() != V21_MANIFEST_SHA256:
            raise AssertionError("v2.1 historical manifest changed")
        cls.v24_protocol, _ = finalization_v2.load_historical_protocol(
            REPO_ROOT,
            freeze_commit=V24_FREEZE_COMMIT,
        )

    def test_v21_archive_is_byte_authenticated_with_exact_provenance(self) -> None:
        self.assertEqual(
            self.manifest["schema_version"],
            "stimmung_final_wording_freeze_v2_1",
        )
        self.assertEqual(
            self.manifest["baseline_head"],
            "9d6b66be05fb89561961deaa4d64f6acbbb42e48",
        )
        self.assertEqual(
            self.manifest["protocol_version"],
            "lot4c4_final_wording_provider_campaign_v2_1",
        )
        self.assertEqual(self.manifest["schedule"]["call_count"], 36)
        self.assertFalse(self.manifest["phase_limits"]["runtime_change"])

    def test_completed_attempt_resume_contract_remains_in_the_archive(self) -> None:
        self.assertTrue(
            self.manifest["artifact_policy"]["resume_completed_attempts_without_recall"]
        )
        self.assertIn(
            "completed_sequence_recalled_on_resume",
            self.manifest["v2_1_mutation_matrix"],
        )

    def test_ambiguous_attempt_contract_is_costed_and_terminal(self) -> None:
        self.assertTrue(
            self.manifest["artifact_policy"]["ambiguous_attempt_costed_at_call_ceiling"]
        )
        self.assertEqual(
            self.manifest["decision_rules"]["ambiguous_started_attempt"],
            "campaign_incomplete",
        )
        self.assertIn(
            "attempt_started_sequence_recalled_on_resume",
            self.manifest["v2_1_mutation_matrix"],
        )

    def test_pre_provider_checkpoint_contract_remains_frozen(self) -> None:
        self.assertTrue(
            self.manifest["artifact_policy"]["atomic_checkpoint_before_each_call"]
        )
        self.assertIn(
            "ledger_not_fsynced_before_provider_boundary",
            self.manifest["v2_1_mutation_matrix"],
        )

    def test_unknown_outcome_cannot_be_counted_as_free_or_successful(self) -> None:
        self.assertIn(
            "unknown_outcome_counted_as_free_or_successful",
            self.manifest["v2_1_mutation_matrix"],
        )
        self.assertIn(
            "rating_packet_created_from_incomplete_campaign",
            self.manifest["v2_1_mutation_matrix"],
        )

    def test_interruption_and_atomic_write_contracts_remain_effective_helpers(self) -> None:
        self.assertIn(
            "partial_evidence_deleted_after_interruption",
            self.manifest["v2_1_mutation_matrix"],
        )
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            target = Path(raw) / "checkpoint.json"
            execution_v2._atomic_write_private_json(target, {"state": "old"})
            self.assertEqual(target.stat().st_mode & 0o777, 0o600)
            with mock.patch.object(
                execution_v2.os,
                "replace",
                side_effect=OSError("controlled replace interruption"),
            ), self.assertRaisesRegex(OSError, "controlled replace interruption"):
                execution_v2._atomic_write_private_json(target, {"state": "new"})
            self.assertEqual(json.loads(target.read_text(encoding="utf-8")), {"state": "old"})
            self.assertEqual(list(target.parent.glob(".checkpoint.json.*.tmp")), [])

    def test_resume_freeze_attempt_and_cost_guards_remain_declared(self) -> None:
        expected = {
            "freeze_changed_during_resume",
            "attempt_counter_reset_between_invocations",
            "prior_cost_forgotten_on_resume",
            "attempt_37_allowed",
            "cumulative_cost_cap_exceeded_after_resume",
        }
        self.assertTrue(expected.issubset(set(self.manifest["v2_1_mutation_matrix"])))
        self.assertEqual(self.manifest["schedule"]["absolute_call_cap"], 36)

    def test_ratification_and_preblind_contracts_remain_frozen(self) -> None:
        self.assertEqual(
            self.manifest["rating_policy"]["codex_assisted_review_for_tof"],
            "human_ratification_required",
        )
        expected = {
            "codex_assistance_claimed_as_human_review",
            "codex_assisted_rating_finalized_without_tof_ratification",
            "ratification_fingerprint_mismatch",
            "unblinding_before_complete_validation",
        }
        self.assertTrue(expected.issubset(set(self.manifest["v2_1_mutation_matrix"])))

    def test_review_export_and_durable_content_contracts_remain_frozen(self) -> None:
        policy = self.manifest["artifact_policy"]
        self.assertTrue(policy["review_export_contains_blind_packet_only"])
        self.assertTrue(policy["durable_content_free"])
        self.assertFalse(policy["raw_dialogue_in_durable_artifact"])
        self.assertFalse(policy["raw_prompt_in_durable_artifact"])
        self.assertFalse(policy["raw_provider_response_in_durable_artifact"])
        self.assertIn(
            "private_mapping_exposed_in_review_export",
            self.manifest["v2_1_mutation_matrix"],
        )

    def test_v21_history_is_non_reusable_in_the_authenticated_v24_lineage(self) -> None:
        history = self.v24_protocol["v2_1_campaign_history"]
        self.assertEqual(history["attempted_call_count"], 36)
        self.assertEqual(history["http_404_count"], 36)
        self.assertEqual(history["provider_inference_count"], 0)
        self.assertFalse(history["reusable"])

    def test_surviving_public_runner_refuses_drift_before_any_effect(self) -> None:
        client = _UnreachableClient()
        progress: list[tuple[object, ...]] = []
        with tempfile.TemporaryDirectory(dir="/tmp") as raw:
            root = Path(raw)
            private = root / "private"
            review = root / "review"
            with self.assertRaisesRegex(ValueError, "freeze_manifest_mismatch"):
                execution_v2.run_campaign(
                    repo_root=REPO_ROOT,
                    protocol=self.v24_protocol,
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


if __name__ == "__main__":
    unittest.main()
