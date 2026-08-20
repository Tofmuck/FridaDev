from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_agent_lane_orchestration
from core.hermeneutic_node.validation import validation_contract


COUNTERCASES_PATH = APP_DIR / "tests" / "support" / "lot0_presence_countercases.json"


def assert_countercase_matrix(cases):
    expected = {
        "QUESTION": ("question", False, "clarify", "simple"),
        "REQUEST": ("request", False, "answer", "simple"),
        "DISTRESS": ("distress", False, "answer", "simple"),
        "RISK": ("risk", False, "suspend", "simple"),
        "HARD_GUARD": ("hard_guard", False, "suspend", "simple"),
        "MATERIAL_AMBIGUITY": ("material_instruction_ambiguous", False, "clarify", "simple"),
    }
    actual = {
        str(case.get("id") or ""): (
            str(case.get("input_kind") or ""),
            case.get("presence_allowed"),
            str(case.get("expected_posture") or ""),
            str(case.get("expected_regime") or ""),
        )
        for case in cases
    }
    if actual != expected:
        raise AssertionError("Lot 0 Presence countercase matrix changed")


def assert_fail_open_cannot_select_presence(summary):
    expected = {
        "decision_source": "fail_open",
        "status": "error",
        "final_output_regime": "",
        "presence_override": False,
    }
    if summary != expected:
        raise AssertionError("Lot 0 fail-open produced or authorized Presence")


class Lot0PresenceCountercaseTests(unittest.TestCase):
    def test_content_free_countercase_matrix_forbids_presence_and_rejects_mutations(self) -> None:
        payload = json.loads(COUNTERCASES_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema_version"], "lot0_presence_countercases_v1")
        assert_countercase_matrix(payload["cases"])

        for index in range(len(payload["cases"])):
            mutated = copy.deepcopy(payload["cases"])
            mutated[index]["presence_allowed"] = True
            mutated[index]["expected_regime"] = "presence"
            with self.subTest(case_id=mutated[index]["id"]):
                with self.assertRaises(AssertionError):
                    assert_countercase_matrix(mutated)

    def test_real_fail_open_contract_cannot_reach_presence_override_and_mutation_is_rejected(self) -> None:
        result = validation_contract.build_fail_open_result(
            primary_verdict={},
            reason_code="synthetic_double_failure",
            model="synthetic/validation-fallback",
            applied_hard_guards=[],
            hard_guard_effect=None,
        )
        override = chat_agent_lane_orchestration._hermeneutic_presence_assistant_response_override(result)
        summary = {
            "decision_source": result.decision_source,
            "status": result.status,
            "final_output_regime": str(result.validated_output.get("final_output_regime") or ""),
            "presence_override": override is not None,
        }
        assert_fail_open_cannot_select_presence(summary)

        for mutation in (
            {"status": "ok", "final_output_regime": "presence"},
            {"presence_override": True},
        ):
            mutated = {**summary, **mutation}
            with self.assertRaises(AssertionError):
                assert_fail_open_cannot_select_presence(mutated)


if __name__ == "__main__":
    unittest.main()
