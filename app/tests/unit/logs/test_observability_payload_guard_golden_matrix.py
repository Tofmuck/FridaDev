from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from observability import observability_payload_guard
from tests.support.observability_guard_golden_matrix import ACCEPTED_STAGE_CASES


EXPECTED_STAGE_NAMES = (
    "chat_response",
    "stream",
    "arbiter",
    "memory",
    "identity",
    "web",
    "agenda",
    "biblio",
    "stimmung",
    "manifest",
)


class ObservabilityPayloadGuardGoldenMatrixTests(unittest.TestCase):
    def test_accepted_matrix_covers_each_contractual_stage_once(self) -> None:
        observed = tuple(case["name"] for case in ACCEPTED_STAGE_CASES)

        self.assertEqual(observed, EXPECTED_STAGE_NAMES)
        self.assertEqual(len(observed), len(set(observed)))

    def test_each_contractual_stage_payload_is_accepted_unchanged(self) -> None:
        for case in ACCEPTED_STAGE_CASES:
            with self.subTest(stage=case["stage"], name=case["name"]):
                payload = copy.deepcopy(case["payload"])

                decision = observability_payload_guard.guard_payload(payload)

                self.assertTrue(decision.accepted, decision.payload)
                self.assertEqual(decision.payload, payload)

    def test_each_contractual_stage_rejects_added_uncontracted_text(self) -> None:
        sentinel = "LOT9D0_UNCONTRACTED_TEXT_SENTINEL"
        for case in ACCEPTED_STAGE_CASES:
            with self.subTest(stage=case["stage"], name=case["name"]):
                mutant = copy.deepcopy(case["payload"])
                mutant["private_sentence"] = sentinel

                decision = observability_payload_guard.guard_payload(mutant)
                encoded = json.dumps(decision.payload, sort_keys=True)

                self.assertFalse(decision.accepted)
                self.assertNotIn(sentinel, encoded)
                self.assertTrue(decision.payload["rejected_payload"])
                self.assertFalse(decision.payload["raw_content_included"])


if __name__ == "__main__":
    unittest.main()
