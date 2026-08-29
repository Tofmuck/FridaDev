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

from benchmark.suites.validation_agent import lot4c1_comparison as comparison
from core.hermeneutic_node.inputs import stimmung_input
from core.hermeneutic_node.validation import validation_canonical_family_projection
from core.hermeneutic_node.validation import validation_contract


class Lot4C1ValidationComparisonTests(unittest.TestCase):
    def test_v2_maxima_are_derived_from_authoritative_limits_and_leave_strict_margin(self) -> None:
        maxima = comparison.measured_v2_maxima()

        self.assertEqual(maxima["accepted_contract_chars"], 3741)
        self.assertEqual(maxima["runtime_emittable_chars"], 3546)
        self.assertEqual(maxima["budget_chars"], 3840)
        self.assertEqual(maxima["accepted_margin_chars"], 99)
        self.assertEqual(maxima["runtime_emittable_margin_chars"], 294)
        self.assertLess(maxima["accepted_contract_chars"], maxima["budget_chars"])

        accepted = comparison._maximal_v2_projection(runtime_emittable=False)
        tones = [item["tone"] for item in accepted["families"]["stimmung_input"]["active_tones"]]
        self.assertEqual(
            tones,
            sorted(
                stimmung_input.ALLOWED_TONES,
                key=lambda item: (-len(item), item),
            )[: stimmung_input.ACTIVE_TONES_LIMIT],
        )
        self.assertEqual(
            accepted["families"]["web_input"]["activation_mode"],
            max(
                validation_canonical_family_projection._WEB_ACTIVATION_MODES,
                key=lambda item: (len(item), item),
            ),
        )

    def test_protocol_freezes_corpus_models_calls_cost_and_decision_before_live_results(self) -> None:
        corpus = comparison.load_corpus()
        protocol = comparison.protocol_document(corpus, phase1_commit="phase1-synthetic")

        self.assertEqual(len(corpus["cases"]), 10)
        self.assertEqual(protocol["planned_provider_calls"], 80)
        self.assertLessEqual(protocol["planned_provider_calls"], 96)
        self.assertEqual(protocol["max_estimated_cost_usd"], 0.10)
        self.assertEqual(
            protocol["models"],
            [
                {"source": "primary", "model": "google/gemini-3.1-flash-lite"},
                {"source": "fallback", "model": "openai/gpt-5.4-nano"},
            ],
        )
        self.assertFalse(protocol["decision_rule"]["thresholds_mutable_after_provider_results"])
        tags = {tag for case in corpus["cases"] for tag in case["tags"]}
        self.assertTrue(
            {
                "interrogation",
                "explicit_request",
                "presence_opportunity",
                "presence_countercase",
                "actionable_ambiguity",
                "epistemic_uncertainty",
                "temporal_qualification",
                "stable_stimmung",
                "stimmung_transition",
                "web_active",
                "memory_summary_identity",
                "optional_absent",
            }.issubset(tags)
        )

    def test_each_case_uses_real_builders_and_current_validation_message_constructor(self) -> None:
        corpus = comparison.load_corpus()
        for case in corpus["cases"]:
            with self.subTest(case=case["id"]):
                built = comparison.build_current_messages(case, "synthetic-system-prompt")
                material = comparison._canonical_material_from_user_message(
                    built["messages"][1]["content"]
                )
                projection = json.loads(material)
                self.assertEqual(
                    projection["projection_version"],
                    validation_contract.CANONICAL_PROJECTION_VERSION,
                )
                self.assertLessEqual(len(material), validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS)
                expected_guard = str((case.get("expected") or {}).get("required_hard_guard") or "")
                if expected_guard:
                    self.assertIn(expected_guard, built["hard_guard"]["applied_hard_guards"])

    def test_message_pair_changes_only_exact_canonical_inputs_block(self) -> None:
        case = comparison.load_corpus()["cases"][7]
        built = comparison.build_current_messages(case, "synthetic-system-prompt")
        v2_messages = built["messages"]
        v2_material = comparison._canonical_material_from_user_message(v2_messages[1]["content"])
        synthetic_v1_material = json.dumps(
            {
                "projection_version": "validation_canonical_inputs_v1",
                "stimmung_delivery": {"status": "full", "reason_code": "included"},
                "families": {"stimmung_input": built["canonical_inputs"]["stimmung_input"]},
                "omitted_families": ["user_turn_input"],
            },
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        v1_messages = comparison.messages_with_canonical_material(
            v2_messages,
            expected_current_material=v2_material,
            replacement_material=synthetic_v1_material,
        )

        fingerprints = comparison.pair_fingerprints({"v1": v1_messages, "v2": v2_messages})
        self.assertNotEqual(
            fingerprints["v1_canonical_sha256"],
            fingerprints["v2_canonical_sha256"],
        )
        self.assertEqual(v1_messages[0], v2_messages[0])
        self.assertNotEqual(v1_messages[1], v2_messages[1])

    def test_shared_scorer_rejects_false_presence_hard_guard_and_v2_regression(self) -> None:
        corpus = comparison.load_corpus()
        request_case = corpus["cases"][1]
        request_built = comparison.build_current_messages(request_case, "system")
        false_presence = comparison.score_parsed_output(
            request_case,
            json.dumps(
                {
                    "schema_version": "v1",
                    "final_judgment_posture": "answer",
                    "final_output_regime": "presence",
                    "arbiter_reason": "synthetic",
                }
            ),
            hard_guard_payload=request_built["hard_guard"],
        )
        self.assertFalse(false_presence["pass"])
        self.assertIn("false_presence", false_presence["semantic_codes"])

        guarded_case = corpus["cases"][5]
        guarded_built = comparison.build_current_messages(guarded_case, "system")
        forbidden_answer = comparison.score_parsed_output(
            guarded_case,
            json.dumps(
                {
                    "schema_version": "v1",
                    "final_judgment_posture": "answer",
                    "final_output_regime": "simple",
                    "arbiter_reason": "synthetic",
                }
            ),
            hard_guard_payload=guarded_built["hard_guard"],
        )
        self.assertFalse(forbidden_answer["pass"])
        self.assertEqual(forbidden_answer["status"], "ok")
        self.assertIn("hard_guard_violation", forbidden_answer["semantic_codes"])

        v1_pass = {"status": "ok", "pass": True, "semantic_codes": [], "final_judgment_posture": "answer", "final_output_regime": "simple"}
        v2_fail = {"status": "ok", "pass": False, "semantic_codes": ["false_presence"], "final_judgment_posture": "answer", "final_output_regime": "presence"}
        pair = comparison.compare_pair(
            case=request_case,
            source="primary",
            v1_score=v1_pass,
            v2_score=v2_fail,
        )
        self.assertEqual(pair["classification"], "fail")
        self.assertIn("v2_regression", pair["divergence_codes"])

    def test_campaign_decision_is_fail_pass_or_inconclusive_without_moving_thresholds(self) -> None:
        records = []
        for case in comparison.load_corpus()["cases"]:
            for source in ("primary", "fallback"):
                records.append(
                    {
                        "record_type": "pair_comparison",
                        "case_id": case["id"],
                        "source": source,
                        "status": "pass",
                    }
                )
        self.assertEqual(comparison.campaign_decision(records)["decision"], "pass")
        records[0]["status"] = "fail"
        self.assertEqual(comparison.campaign_decision(records)["decision"], "fail")
        records[0]["status"] = "provider_invalid_pair"
        self.assertEqual(comparison.campaign_decision(records)["decision"], "inconclusive")

    def test_artifact_contract_rejects_raw_provider_or_dialogue_content(self) -> None:
        record = {key: None for key in comparison.ARTIFACT_RECORD_KEYS}
        record.update(
            {
                "record_type": "provider_call",
                "system_sha256": "a" * 64,
                "noncanonical_user_sha256": "b" * 64,
                "canonical_sha256": "c" * 64,
            }
        )
        self.assertEqual(
            comparison.validate_content_free_record(record)["record_type"],
            "provider_call",
        )
        raw_mutant = dict(record, raw_text="synthetic-provider-output")
        with self.assertRaisesRegex(ValueError, "artifact_fields"):
            comparison.validate_content_free_record(raw_mutant)
        dialogue_mutant = dict(record, dialogue="synthetic-dialogue")
        with self.assertRaisesRegex(ValueError, "artifact_fields"):
            comparison.validate_content_free_record(dialogue_mutant)


if __name__ == "__main__":
    unittest.main()
