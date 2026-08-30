from __future__ import annotations

import copy
import hashlib
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

from benchmark.suites.stimmung import dialogic_semantics
from benchmark.suites.stimmung import causal_rescoring


SONNET_ARTIFACT = (
    REPO_ROOT
    / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-sonnet-5-medium.jsonl"
)
DERIVED_ARTIFACT = (
    REPO_ROOT
    / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-causal-rescoring.jsonl"
)
DERIVED_ARTIFACT_SHA256 = "4cadffa37afb9802345ec16aaf3095468e37a8c17969374a1935ebac790e4ea0"


def _load_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _case(dialogue_id: str) -> dict:
    corpus = dialogic_semantics.load_corpus(REPO_ROOT)
    return next(item for item in corpus["dialogues"] if item["id"] == dialogue_id)


def _observations(
    records: list[dict],
    *,
    dialogue_id: str,
    repetition: int,
) -> list[dict]:
    return [
        {
            "turn_id": item["turn_id"],
            "execution_status": item["status"],
            "source": item["source"],
            "signal": copy.deepcopy(item["signal"]),
            "aggregate": copy.deepcopy(item["aggregate"]),
        }
        for item in records
        if item.get("record_type") == "call"
        and item.get("dialogue_id") == dialogue_id
        and item.get("repetition") == repetition
        and item.get("evaluated") is True
    ]


class Lot4C2StimmungCausalRescoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.sonnet_records = _load_records(SONNET_ARTIFACT)
        cls.rescoring_records = causal_rescoring.build_rescoring_records(REPO_ROOT)

    def test_aggregate_only_failure_does_not_fail_caller_local(self) -> None:
        case = _case("L4S0-ST-001")
        levels = causal_rescoring.score_dialogue_levels(
            case,
            _observations(
                self.sonnet_records,
                dialogue_id=case["id"],
                repetition=1,
            ),
        )

        self.assertEqual(levels["caller_local_semantics"]["classification"], "pass")
        self.assertEqual(levels["aggregate_trajectory"]["classification"], "fail")
        self.assertEqual(levels["combined_pipeline"]["classification"], "fail")
        self.assertEqual(
            levels["aggregate_trajectory"]["reason_codes"],
            ["trajectory_stability_mismatch"],
        )

    def test_bad_local_signal_fails_even_when_aggregate_is_conforming(self) -> None:
        case = _case("L4S0-ST-006")
        observations = _observations(
            self.sonnet_records,
            dialogue_id=case["id"],
            repetition=1,
        )
        levels = causal_rescoring.score_dialogue_levels(case, observations)

        self.assertEqual(levels["caller_local_semantics"]["classification"], "fail")
        self.assertEqual(levels["aggregate_trajectory"]["classification"], "pass")
        self.assertEqual(levels["combined_pipeline"]["classification"], "fail")
        self.assertEqual(
            levels["caller_local_semantics"]["reason_codes"],
            ["signal_overcoded"],
        )

    def test_corrupt_aggregate_is_inconclusive_only_for_aggregate_and_combined(self) -> None:
        case = _case("L4S0-ST-001")
        observations = _observations(
            self.sonnet_records,
            dialogue_id=case["id"],
            repetition=1,
        )
        observations[0]["aggregate"] = None

        levels = causal_rescoring.score_dialogue_levels(case, observations)

        self.assertEqual(levels["caller_local_semantics"]["classification"], "pass")
        self.assertEqual(levels["aggregate_trajectory"]["classification"], "inconclusive")
        self.assertEqual(levels["combined_pipeline"]["classification"], "inconclusive")
        self.assertEqual(
            levels["aggregate_trajectory"]["reason_codes"],
            ["aggregate_schema_invalid"],
        )

    def test_offline_rescoring_preserves_historical_combined_and_splits_failures(self) -> None:
        records = self.rescoring_records
        validation = causal_rescoring.validate_rescoring_artifact(records, REPO_ROOT)

        self.assertEqual(validation["dialogue_rescore_count"], 192)
        self.assertEqual(validation["configuration_summary_count"], 6)
        sonnet = next(
            item
            for item in records
            if item.get("record_type") == "configuration_summary"
            and item.get("campaign_id") == "sonnet_5_medium"
        )
        self.assertEqual(
            sonnet["failure_partition"],
            {
                "full_pass": 6,
                "aggregate_only": 16,
                "caller_only": 3,
                "caller_and_aggregate": 7,
                "inconclusive": 0,
            },
        )
        self.assertEqual(sonnet["caller_local_counts"], {"pass": 22, "fail": 10, "inconclusive": 0})
        self.assertEqual(sonnet["combined_pipeline_counts"], {"pass": 6, "fail": 26, "inconclusive": 0})
        gemini = next(
            item
            for item in records
            if item.get("record_type") == "configuration_summary"
            and item.get("campaign_id") == "gemini_3_7_medium_max800"
        )
        self.assertEqual(gemini["caller_local_counts"], {"pass": 15, "fail": 17, "inconclusive": 0})
        self.assertEqual(gemini["technical_status_counts"], {"ok": 137, "json_error": 1})
        self.assertEqual(gemini["caller_local_decision"], "inconclusive")

    def test_prompt_candidate_local_result_is_not_hidden_by_aggregate_failures(self) -> None:
        records = self.rescoring_records
        candidate_primary = next(
            item
            for item in records
            if item.get("record_type") == "configuration_summary"
            and item.get("campaign_id") == "strengthening_candidate"
            and item.get("source") == "primary"
        )

        self.assertEqual(candidate_primary["caller_local_counts"], {"pass": 28, "fail": 4, "inconclusive": 0})
        self.assertEqual(candidate_primary["combined_pipeline_counts"], {"pass": 10, "fail": 22, "inconclusive": 0})
        self.assertEqual(candidate_primary["caller_local_decision"], "not_eligible")
        self.assertEqual(
            candidate_primary["caller_local_reason_counts"],
            {"signal_overcoded": 2, "strength_outside_allowed": 2},
        )

    def test_unscored_contributors_prevent_false_aggregate_attribution(self) -> None:
        records = self.rescoring_records
        aggregate_failure = next(
            item
            for item in records
            if item.get("record_type") == "dialogue_rescore"
            and item["aggregate_trajectory"]["classification"] == "fail"
            and any(
                window["unevaluated_contributor_count"] > 0
                for window in item["window_provenance"]
            )
        )

        self.assertEqual(
            aggregate_failure["aggregate_causal_attribution"],
            "not_attributable_unscored_contributors",
        )
        for window in aggregate_failure["window_provenance"]:
            self.assertEqual(
                window["evaluated_contributor_count"]
                + window["unevaluated_contributor_count"],
                len(window["contributor_turn_ids"]),
            )

    def test_derived_artifact_rejects_raw_fields_false_eligibility_and_false_attribution(self) -> None:
        records = self.rescoring_records

        raw = copy.deepcopy(records)
        raw[0]["provider_output"] = "synthetic free text"
        with self.assertRaises(ValueError):
            causal_rescoring.validate_rescoring_artifact(raw, REPO_ROOT)

        false_eligibility = copy.deepcopy(records)
        summary = next(
            item
            for item in false_eligibility
            if item.get("record_type") == "configuration_summary"
            and item.get("campaign_id") == "sonnet_5_medium"
        )
        summary["caller_local_decision"] = "eligible"
        with self.assertRaises(ValueError):
            causal_rescoring.validate_rescoring_artifact(false_eligibility, REPO_ROOT)

        false_attribution = copy.deepcopy(records)
        rescore = next(
            item
            for item in false_attribution
            if item.get("record_type") == "dialogue_rescore"
            and item.get("aggregate_causal_attribution")
            == "not_attributable_unscored_contributors"
        )
        rescore["aggregate_causal_attribution"] = "bounded_to_scored_contributors"
        with self.assertRaises(ValueError):
            causal_rescoring.validate_rescoring_artifact(false_attribution, REPO_ROOT)

    def test_incomplete_local_result_cannot_be_declared_eligible(self) -> None:
        self.assertEqual(
            causal_rescoring.decide_local_semantics(
                [{"classification": "pass"}] * 31
                + [{"classification": "inconclusive"}],
                expected_count=32,
            ),
            "inconclusive",
        )
        self.assertEqual(
            causal_rescoring.decide_local_semantics(
                [{"classification": "pass"}] * 31,
                expected_count=32,
            ),
            "inconclusive",
        )

    def test_retained_rescoring_artifact_is_content_free_and_reconstructible(self) -> None:
        self.assertEqual(
            hashlib.sha256(DERIVED_ARTIFACT.read_bytes()).hexdigest(),
            DERIVED_ARTIFACT_SHA256,
        )
        records = _load_records(DERIVED_ARTIFACT)
        validation = causal_rescoring.validate_rescoring_artifact(
            records, REPO_ROOT
        )

        self.assertEqual(validation["dialogue_rescore_count"], 192)
        self.assertEqual(validation["configuration_summary_count"], 6)
        self.assertEqual(
            validation["gpt_5_2_trial_status"],
            "not_required_by_current_evidence",
        )


if __name__ == "__main__":
    unittest.main()
