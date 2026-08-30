from __future__ import annotations

import copy
import difflib
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

from benchmark.suites.stimmung import causal_rescoring, dialogic_campaign, dialogic_semantics
from app.tests.unit.golden.test_lot4s1_stimmung_provider_campaign import _WitnessClient


CORPUS_V2 = REPO_ROOT / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v2.json"
CORPUS_V3 = REPO_ROOT / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v3.json"
CANDIDATE_V1 = REPO_ROOT / "benchmark/suites/stimmung/fixtures/stimmung_semantic_strengthening_candidate_v1.txt"
CANDIDATE_V2 = REPO_ROOT / "benchmark/suites/stimmung/fixtures/stimmung_semantic_strengthening_candidate_v2.txt"
HISTORICAL_CANDIDATE = REPO_ROOT / "benchmark/results/stimmung/2026-08-30-lot4c2-stimmung-strengthening-candidate.jsonl"
HISTORICAL_SHA256 = {
    CORPUS_V2: "5059d5ea4b57409bc08ee95dae39f74b2411268dcf5fe6aee516dd9ffb310ee5",
    CANDIDATE_V1: "e1ce1bd0490a3f6ef0757a63768d0c32a1c277db4636c2b33ba0cafd793ed0c7",
    HISTORICAL_CANDIDATE: "637cbc1fac2b03378f451d6fc64f6b0c30b7d9cd183b59b5833e3ee62612c5c5",
}
NEW_RULE = (
    "- La simple volonte de poursuivre, continuer, comprendre, examiner ou agir "
    "ne constitue pas en elle-meme un enthousiasme. Ne retiens l'enthousiasme "
    "que lorsqu'un affect positif suffisamment explicite le justifie independamment."
)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _diff_paths(left: object, right: object, prefix: str = "") -> set[str]:
    if isinstance(left, dict) and isinstance(right, dict):
        result: set[str] = set()
        for key in set(left) | set(right):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                result.add(child)
            else:
                result.update(_diff_paths(left[key], right[key], child))
        return result
    if isinstance(left, list) and isinstance(right, list):
        if len(left) != len(right):
            return {f"{prefix}.length"}
        result: set[str] = set()
        for index, (left_item, right_item) in enumerate(zip(left, right)):
            result.update(_diff_paths(left_item, right_item, f"{prefix}[{index}]"))
        return result
    return set() if left == right else {prefix}


def _case(corpus: dict, dialogue_id: str) -> dict:
    return next(item for item in corpus["dialogues"] if item["id"] == dialogue_id)


def _historical_observations(dialogue_id: str, repetition: int) -> list[dict]:
    records = dialogic_campaign.load_jsonl(HISTORICAL_CANDIDATE)
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
        and item.get("source") == "primary"
        and item.get("repetition") == repetition
        and item.get("dialogue_id") == dialogue_id
        and item.get("evaluated") is True
    ]


class Lot4C2StimmungFinalPromptCandidateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        witness = _load(
            REPO_ROOT
            / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_reachability_witness_v1.json"
        )
        cls.witness_by_dialogue = {
            item["dialogue_id"]: item["signals"] for item in witness["dialogues"]
        }
        cls.protocol = dialogic_campaign.build_final_strengthening_protocol(
            REPO_ROOT,
            freeze_commit="f" * 40,
        )
        cls.schedule = dialogic_campaign.build_final_strengthening_request_schedule(
            REPO_ROOT,
            cls.protocol,
        )

    def test_v3_is_an_exact_versioned_derivation_with_one_semantic_change(self) -> None:
        v2 = _load(CORPUS_V2)
        v3 = _load(CORPUS_V3)
        summary = dialogic_campaign.validate_final_strengthening_corpus(v3)
        changed = _diff_paths(v2, v3)
        metadata_changes = {
            "schema_version",
            "corpus_id",
            *{f"dialogues[{index}].version" for index in range(16)},
        }
        target_index = next(
            index for index, item in enumerate(v3["dialogues"])
            if item["id"] == "L4S0-ST-003"
        )
        self.assertEqual(
            changed,
            metadata_changes
            | {f"dialogues[{target_index}].turns[5].expectation.strength_range[1]"},
        )
        self.assertEqual(summary["dialogue_count"], 16)
        self.assertEqual(
            _case(v3, "L4S0-ST-003")["turns"][5]["expectation"]["strength_range"],
            [2, 7],
        )

    def test_v3_accepts_strength_seven_and_still_rejects_eight_locally(self) -> None:
        case = _case(_load(CORPUS_V3), "L4S0-ST-003")
        observations = _historical_observations(case["id"], repetition=1)
        seven = causal_rescoring.score_dialogue_levels(case, observations)
        self.assertEqual(seven["caller_local_semantics"]["classification"], "pass")

        eight_observations = copy.deepcopy(observations)
        eight_observations[-1]["signal"]["tones"][0]["strength"] = 8
        eight = causal_rescoring.score_dialogue_levels(case, eight_observations)
        self.assertEqual(eight["caller_local_semantics"]["classification"], "fail")
        self.assertEqual(
            eight["caller_local_semantics"]["reason_codes"],
            ["strength_outside_allowed"],
        )

    def test_candidate_v2_is_candidate_v1_plus_exactly_one_general_rule(self) -> None:
        v1_lines = CANDIDATE_V1.read_text(encoding="utf-8").splitlines()
        v2_lines = CANDIDATE_V2.read_text(encoding="utf-8").splitlines()
        diff = list(difflib.ndiff(v1_lines, v2_lines))
        additions = [line[2:] for line in diff if line.startswith("+ ")]
        removals = [line[2:] for line in diff if line.startswith("- ")]
        self.assertEqual(additions, [NEW_RULE])
        self.assertEqual(removals, [])
        self.assertNotIn("L4S0-ST-", CANDIDATE_V2.read_text(encoding="utf-8"))

    def test_protocol_and_schedule_are_primary_only_bounded_and_frozen(self) -> None:
        summary = dialogic_campaign.validate_final_strengthening_protocol(
            self.protocol,
            REPO_ROOT,
        )
        self.assertEqual(summary["expected_call_count"], 138)
        self.assertEqual(self.protocol["absolute_call_cap"], 138)
        self.assertEqual(self.protocol["model"], "google/gemini-3.1-flash-lite")
        self.assertEqual(self.protocol["generation_params"], {"temperature": 0.1, "top_p": 1.0, "max_tokens": 220})
        self.assertEqual(self.protocol["timeout_s"], 10)
        self.assertLessEqual(self.protocol["estimated_max_cost_usd"], 0.30)
        self.assertEqual(len(self.schedule), 138)
        self.assertEqual({item["source"] for item in self.schedule}, {"primary"})
        self.assertEqual([item["repetition"] for item in self.schedule[:69]], [1] * 69)
        self.assertEqual([item["repetition"] for item in self.schedule[69:]], [2] * 69)
        self.assertTrue(all(item["payload"]["provider"] == {"allow_fallbacks": False} for item in self.schedule))
        model_mutant = copy.deepcopy(self.protocol)
        model_mutant["model"] = "openai/gpt-5.4-nano"
        with self.assertRaisesRegex(
            ValueError,
            "final_strengthening_protocol_freeze_mismatch",
        ):
            dialogic_campaign.validate_final_strengthening_protocol(
                model_mutant,
                REPO_ROOT,
            )

    def test_provider_visible_difference_is_only_the_single_prompt_rule(self) -> None:
        historical = dialogic_campaign.build_request_schedule(
            REPO_ROOT,
            dialogic_campaign.build_strengthening_protocol(
                REPO_ROOT,
                freeze_commit="e" * 40,
            ),
        )[:138]
        self.assertEqual(len(historical), len(self.schedule))
        for old, new in zip(historical, self.schedule):
            self.assertEqual(
                {key: old[key] for key in ("dialogue_id", "turn_id", "evaluated", "source", "repetition")},
                {key: new[key] for key in ("dialogue_id", "turn_id", "evaluated", "source", "repetition")},
            )
            old_payload = copy.deepcopy(old["payload"])
            new_payload = copy.deepcopy(new["payload"])
            old_system = old_payload["messages"][0].pop("content")
            new_system = new_payload["messages"][0].pop("content")
            self.assertNotEqual(old_system, new_system)
            self.assertEqual(old_payload, new_payload)

    def test_witness_run_uses_local_gate_and_reaches_eligible_primary(self) -> None:
        client = _WitnessClient(self.witness_by_dialogue, self.schedule)
        records = dialogic_campaign.run_final_strengthening_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        result = dialogic_campaign.validate_final_strengthening_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )
        self.assertEqual(len(client.calls), 138)
        self.assertEqual(result["call_count"], 138)
        self.assertEqual(result["local_score_count"], 32)
        self.assertEqual(result["final_decision"], "eligible_primary")
        raw_mutant = copy.deepcopy(records[0])
        raw_mutant["provider_output"] = "synthetic free text"
        with self.assertRaisesRegex(
            ValueError,
            "final_strengthening_record_schema_invalid",
        ):
            dialogic_campaign.validate_final_strengthening_record(raw_mutant)

    def test_first_repetition_semantic_failure_stops_before_call_seventy(self) -> None:
        witness = copy.deepcopy(self.witness_by_dialogue)
        witness["L4S0-ST-001"][1]["tones"].append(
            {"tone": "enthousiasme", "strength": 4}
        )
        client = _WitnessClient(witness, self.schedule)
        records = dialogic_campaign.run_final_strengthening_campaign(
            repo_root=REPO_ROOT,
            protocol=self.protocol,
            client=client,
        )
        result = dialogic_campaign.validate_final_strengthening_artifact(
            records,
            REPO_ROOT,
            self.protocol,
        )
        self.assertEqual(len(client.calls), 69)
        self.assertEqual(result["call_count"], 69)
        self.assertEqual(result["local_score_count"], 16)
        self.assertEqual(result["final_decision"], "not_eligible")
        false_eligible = copy.deepcopy(records[-1])
        false_eligible["decision"] = "eligible_primary"
        with self.assertRaisesRegex(
            ValueError,
            "final_strengthening_false_eligibility",
        ):
            dialogic_campaign.validate_final_strengthening_record(false_eligible)

    def test_historical_inputs_remain_byte_for_byte_unchanged(self) -> None:
        for path, expected in HISTORICAL_SHA256.items():
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
