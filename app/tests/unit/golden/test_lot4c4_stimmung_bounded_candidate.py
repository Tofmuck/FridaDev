from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import unittest
from unittest import mock

from benchmark.suites.stimmung import final_wording_diagnostic as v1
from benchmark.suites.stimmung import final_wording_protocol_v2 as protocol
from benchmark.suites.stimmung import final_wording_rating_v2 as rating


REPO_ROOT = Path(__file__).resolve().parents[4]
FREEZE_COMMIT = "7fcf26d8d3991b6d64f586b89025b9404316e30e"


class Lot4C4BoundedCandidateTests(unittest.TestCase):
    def test_candidate_policy_is_closed_compact_and_surface_only(self) -> None:
        policy = protocol.BOUNDED_ENUNCIATION_POLICY
        self.assertEqual(policy["version"], "surface_only_v1")
        self.assertEqual(
            set(policy),
            {"version", "priority", "allowed_operations", "preserved", "forbidden", "fallback"},
        )
        self.assertEqual(policy["allowed_operations"], ("lexical_choice", "connectors", "rhythm"))
        self.assertEqual(policy["priority"], "direct_answer_and_substance_first")
        self.assertEqual(
            set(policy["preserved"]),
            {
                "requested_answer",
                "facts",
                "sources",
                "hypotheses",
                "inferences",
                "conclusions",
                "actions",
                "certainty_degrees",
                "proof_regimes",
                "hard_guards",
            },
        )
        self.assertIn("add_or_remove_conclusion", policy["forbidden"])
        self.assertEqual(policy["fallback"], "no_op_if_substance_risk")
        rendered = protocol.bounded_candidate_instruction()
        self.assertLessEqual(len(rendered), 900)
        self.assertNotIn("prudence", rendered.casefold())
        self.assertEqual(
            hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            protocol.BOUNDED_ENUNCIATION_POLICY_SHA256,
        )

    def test_schedule_contains_only_six_transition_pairs_and_candidate_is_the_only_difference(self) -> None:
        campaign = protocol.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        schedule = protocol.build_request_schedule(REPO_ROOT, campaign)
        self.assertEqual(len(schedule), 24)
        self.assertEqual({item["comparison_kind"] for item in schedule}, {"causal_transition"})
        self.assertEqual({item["variant"] for item in schedule}, {"runtime_current", "bounded_candidate"})
        by_pair: dict[tuple[str, int], dict[str, dict]] = {}
        for item in schedule:
            by_pair.setdefault((item["case_id"], item["repetition"]), {})[item["variant"]] = item
        self.assertEqual(len(by_pair), 12)
        for arms in by_pair.values():
            current = arms["runtime_current"]["payload"]["messages"]
            candidate = arms["bounded_candidate"]["payload"]["messages"]
            self.assertEqual(v1._normalized_messages_for_pair(current), v1._normalized_messages_for_pair(candidate))
            self.assertNotEqual(current, candidate)

    def test_countercase_none_path_remains_byte_identical_and_is_not_scheduled(self) -> None:
        corpus = protocol.load_corpus(REPO_ROOT)
        manifest = json.loads(
            (
                REPO_ROOT
                / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_4.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            protocol._sha256_file(
                REPO_ROOT
                / "benchmark/suites/stimmung/final_wording_diagnostic.py"
            ),
            manifest["frozen_inputs"]["v1_message_builder_sha256"],
        )
        countercases = [
            case
            for case in corpus["cases"]
            if case["provider_eligible"] and case["enunciation_state"] != "transition_delicate"
        ]
        self.assertEqual(len(countercases), 6)
        for case in countercases:
            self.assertEqual(
                protocol.countercase_runtime_messages(case),
                v1._build_messages(case, "treatment"),
            )
        schedule_ids = {
            item["case_id"]
            for item in protocol.build_request_schedule(
                REPO_ROOT,
                protocol.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT),
            )
        }
        self.assertTrue(schedule_ids.isdisjoint({case["id"] for case in countercases}))

    def test_protocol_freezes_candidate_observability_cost_and_v23_history(self) -> None:
        campaign = protocol.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        self.assertEqual(campaign["expected_call_count"], 24)
        self.assertEqual(campaign["absolute_call_cap"], 24)
        self.assertEqual(campaign["absolute_cost_cap_usd"], 3.0)
        self.assertLessEqual(campaign["budget_with_safety_margin_usd"], 3.0)
        self.assertEqual(campaign["candidate_policy"]["version"], "surface_only_v1")
        self.assertEqual(
            campaign["candidate_policy"]["sha256"],
            protocol.BOUNDED_ENUNCIATION_POLICY_SHA256,
        )
        self.assertEqual(campaign["observability_policy"]["candidate_version"], "surface_only_v1")
        self.assertFalse(campaign["observability_policy"]["active_in_runtime"])
        self.assertEqual(
            protocol._sha256_file(protocol._v23_freeze_path(REPO_ROOT)),
            protocol.V23_FREEZE_SHA256,
        )

    def test_raw_stimmung_and_runtime_policy_mutations_are_rejected(self) -> None:
        campaign = protocol.build_protocol(REPO_ROOT, freeze_commit=FREEZE_COMMIT)
        schedule = protocol.build_request_schedule(REPO_ROOT, campaign)
        raw = copy.deepcopy(schedule)
        raw[0]["payload"]["messages"][0]["content"] += "\nstimmung_input=forbidden"
        raw[0]["messages_sha256"] = protocol._sha256_text(
            protocol._compact_json(raw[0]["payload"]["messages"])
        )
        raw[0]["prompt_token_estimate"] = int(
            protocol.token_utils.estimate_tokens(
                raw[0]["payload"]["messages"], protocol.ACTIVE_MAIN_MODEL
            )
        )
        raw[0]["calculated_ceiling_cost_usd"] = round(
            raw[0]["prompt_token_estimate"] * protocol.PRICING_USD_PER_TOKEN["prompt"]
            + protocol.ACTIVE_MAX_TOKENS * protocol.PRICING_USD_PER_TOKEN["completion"],
            8,
        )
        with self.assertRaisesRegex(ValueError, "raw_stimmung"):
            protocol.validate_schedule(protocol.load_corpus(REPO_ROOT), raw)
        changed = copy.deepcopy(schedule)
        changed[0]["payload"]["provider"]["allow_fallbacks"] = True
        with self.assertRaisesRegex(ValueError, "schedule_runtime_policy_invalid"):
            protocol.validate_schedule(protocol.load_corpus(REPO_ROOT), changed)

    def test_candidate_contract_and_fingerprint_mutations_are_rejected(self) -> None:
        for field, value in (
            ("priority", "dialogic_effect_first"),
            ("fallback", "always_adjust"),
            ("forbidden", tuple()),
        ):
            mutated = copy.deepcopy(protocol.BOUNDED_ENUNCIATION_POLICY)
            mutated[field] = value
            with self.subTest(field=field), mock.patch.object(
                protocol, "BOUNDED_ENUNCIATION_POLICY", mutated
            ):
                with self.assertRaisesRegex(ValueError, "bounded_enunciation_policy_invalid"):
                    protocol.bounded_candidate_instruction()
        with mock.patch.object(
            protocol,
            "BOUNDED_ENUNCIATION_POLICY_SHA256",
            "0" * 64,
        ):
            with self.assertRaisesRegex(
                ValueError, "bounded_enunciation_policy_fingerprint_invalid"
            ):
                protocol.bounded_candidate_instruction()

    def test_one_candidate_critical_failure_forces_fail(self) -> None:
        ratings_by_id = {}
        mapping_by_id = {}
        for index in range(12):
            blind_id = f"FW24-{index:02d}"
            ratings_by_id[blind_id] = {
                "blind_id": blind_id,
                "delicacy_effect": "better_b",
                "formulation_fit": "better_b",
                "psychologization": "b" if index == 0 else "none",
                "certainty_change": "none",
                "truth_or_evidence_change": "none",
                "masked_target": "none",
            }
            mapping_by_id[blind_id] = {
                "comparison_kind": "causal_transition",
                "slots": {
                    "A": {"variant": "runtime_current"},
                    "B": {"variant": "bounded_candidate"},
                },
            }
        metrics = rating._score_validated_ratings(ratings_by_id, mapping_by_id)
        decision, reasons, observed = rating._decision(
            evidence_source="main_model_provider",
            ledger={"outputs_complete": True},
            metrics=metrics,
        )
        self.assertEqual(decision, "fail")
        self.assertIn("critical_zero_tolerance_breached", reasons)
        self.assertTrue(observed)


if __name__ == "__main__":
    unittest.main()
