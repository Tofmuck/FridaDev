from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.suites.validation_agent import lot4c1_policy_comparison as policy
from benchmark.suites.validation_agent import lot4c1_comparison as projection


class Lot4C1ValidationPolicyComparisonTests(unittest.TestCase):
    def test_protocol_freezes_single_candidate_models_calls_cost_and_decision(self) -> None:
        corpus = policy.load_policy_corpus()
        protocol = policy.protocol_document(corpus, freeze_commit="f" * 40)

        self.assertEqual(len(corpus["cases"]), 11)
        self.assertEqual(protocol["planned_provider_calls"], 88)
        self.assertLessEqual(protocol["planned_provider_calls"], 96)
        self.assertEqual(protocol["max_estimated_cost_usd"], 0.10)
        self.assertEqual(protocol["repetitions"], 2)
        self.assertEqual(protocol["policy_order"], "alternating_by_repetition")
        self.assertEqual(
            protocol["models"],
            [
                {"source": "primary", "model": "google/gemini-3.1-flash-lite"},
                {"source": "fallback", "model": "openai/gpt-5.4-nano"},
            ],
        )
        self.assertEqual(
            protocol["generation"],
            {
                "temperature": 0.0,
                "top_p": 1.0,
                "max_tokens": 140,
                "timeout_s": 15,
                "reasoning_effort": None,
            },
        )
        self.assertFalse(protocol["decision_rule"]["thresholds_mutable_after_results"])
        self.assertEqual(
            protocol["candidate_policy_sha256"],
            policy.CANDIDATE_POLICY_SHA256,
        )

    def test_frozen_policy_pairs_changed_only_the_policy_fragment_at_freeze(self) -> None:
        archive = policy.historical_primary_archive()

        self.assertEqual(archive["policy_pair_count"], 44)
        self.assertTrue(archive["all_policy_pair_fingerprints_match"])

    def test_shared_scorer_rejects_critical_answer_and_nonmaterial_clarify(self) -> None:
        cases = {case["id"]: case for case in policy.load_policy_corpus()["cases"]}
        critical = cases["L4C1-VAL-005"]
        countercase = cases["L4C1-VAL-011"]

        critical_answer = policy.score_structured_pair(
            critical,
            posture="answer",
            regime="simple",
        )
        countercase_clarify = policy.score_structured_pair(
            countercase,
            posture="clarify",
            regime="meta",
        )
        countercase_answer = policy.score_structured_pair(
            countercase,
            posture="answer",
            regime="simple",
        )
        self.assertFalse(critical_answer["pass"])
        self.assertFalse(countercase_clarify["pass"])
        self.assertTrue(countercase_answer["pass"])
        user_turn_signals = projection.build_case_inputs(countercase)[
            "user_turn_signals"
        ]
        self.assertEqual(
            projection._primary_verdict(
                countercase,
                user_turn_signals=user_turn_signals,
            )["upstream_advisory"][
                "recommended_judgment_posture"
            ],
            "clarify",
        )

    def test_decision_fails_on_one_critical_or_regression_and_keeps_fallback_gap_visible(self) -> None:
        passing = policy.synthetic_passing_pair_records()
        self.assertEqual(policy.campaign_decision(passing)["decision"], "pass")

        regression = [dict(record) for record in passing]
        regression[0]["status"] = "candidate_semantic_regression"
        self.assertEqual(
            policy.campaign_decision(regression),
            {"decision": "fail", "reason_code": "candidate_semantic_regression"},
        )
        critical = [dict(record) for record in passing]
        target = next(
            record
            for record in critical
            if record["case_id"] == "L4C1-VAL-005" and record["source"] == "primary"
        )
        target["status"] = "shared_critical_invariant_failure"
        self.assertEqual(
            policy.campaign_decision(critical),
            {"decision": "fail", "reason_code": "shared_critical_invariant_failure"},
        )
        gap = [dict(record) for record in passing]
        gap_target = next(
            record
            for record in gap
            if record["case_id"] == "L4C1-VAL-003" and record["source"] == "fallback"
        )
        gap_target["status"] = "accepted_preexisting_fallback_gap"
        self.assertEqual(policy.campaign_decision(gap)["decision"], "pass")

    def test_policy_artifact_rejects_content_in_allowed_fields_and_false_version(self) -> None:
        record = policy.synthetic_valid_provider_record()
        self.assertEqual(
            policy.validate_content_free_record(record)["record_type"],
            "provider_call",
        )
        for field, value in (
            ("reason_code", "synthetic conversation-like sentence"),
            ("observed_provider", "synthetic provider narrative"),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ValueError):
                    policy.validate_content_free_record(dict(record, **{field: value}))
        with self.assertRaises(ValueError):
            policy.validate_content_free_record(
                dict(record, policy="candidate", policy_version=policy.CURRENT_POLICY_VERSION)
            )

    def test_durable_campaign_artifact_is_content_free_and_records_the_frozen_failure(self) -> None:
        artifact_path = (
            REPO_ROOT
            / "benchmark/results/validation_agent/2026-08-29-lot4c1-validation-policy-current-candidate.jsonl"
        )
        records = [
            json.loads(line)
            for line in artifact_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        self.assertEqual(len(records), 133)
        self.assertTrue(all(policy.validate_content_free_record(record) for record in records))
        summary = next(record for record in records if record["record_type"] == "campaign_summary")
        self.assertEqual(summary["status"], "fail")
        self.assertEqual(summary["reason_code"], "shared_critical_invariant_failure")
        critical_pairs = [
            record
            for record in records
            if record["record_type"] == "pair_comparison"
            and record["case_id"] == "L4C1-VAL-005"
            and record["source"] == "primary"
        ]
        self.assertEqual(len(critical_pairs), 2)
        self.assertTrue(
            all(
                record["status"] == "shared_critical_invariant_failure"
                for record in critical_pairs
            )
        )


if __name__ == "__main__":
    unittest.main()
