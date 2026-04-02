from __future__ import annotations

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

from core.hermeneutic_node.doctrine import output_regime


def _user_turn(
    *,
    gesture: str = "interrogation",
    provenances: list[str] | None = None,
    proof_types: list[str] | None = None,
    composition: str = "isolee",
    temporal_scope: str = "atemporale",
    temporal_anchor: str = "non_ancre",
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "geste_dialogique_dominant": gesture,
        "regime_probatoire": {
            "principe": "maximal_possible",
            "types_de_preuve_attendus": list(proof_types or []),
            "provenances": list(provenances or []),
            "regime_de_vigilance": "renforce" if "web" in list(provenances or []) else "standard",
            "composition_probatoire": composition,
        },
        "qualification_temporelle": {
            "portee_temporelle": temporal_scope,
            "ancrage_temporel": temporal_anchor,
        },
    }


class OutputRegimeTests(unittest.TestCase):
    def test_build_output_regime_requires_valid_judgment_posture(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_judgment_posture"):
            output_regime.build_output_regime(
                judgment_posture="invalid",
                user_turn_input=_user_turn(),
            )

    def test_build_output_regime_requires_valid_user_turn_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_input"):
            output_regime.build_output_regime(
                judgment_posture="answer",
                user_turn_input=None,
            )

    def test_build_output_regime_returns_simple_none_atemporal_by_default(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(),
        )

        self.assertEqual(
            payload,
            {
                "discursive_regime": "simple",
                "resituation_level": "none",
                "time_reference_mode": "atemporal",
            },
        )
        self.assertEqual(set(payload), {"discursive_regime", "resituation_level", "time_reference_mode"})

    def test_build_output_regime_returns_meta_for_clarify(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="clarify",
            user_turn_input=_user_turn(),
        )

        self.assertEqual(payload["discursive_regime"], "meta")
        self.assertEqual(payload["resituation_level"], "none")
        self.assertEqual(payload["time_reference_mode"], "atemporal")

    def test_build_output_regime_returns_meta_for_suspend(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="suspend",
            user_turn_input=_user_turn(),
        )

        self.assertEqual(payload["discursive_regime"], "meta")
        self.assertEqual(payload["resituation_level"], "none")
        self.assertEqual(payload["time_reference_mode"], "atemporal")

    def test_build_output_regime_returns_cadre_for_regulation(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(gesture="regulation"),
        )

        self.assertEqual(
            payload,
            {
                "discursive_regime": "cadre",
                "resituation_level": "explicit",
                "time_reference_mode": "atemporal",
            },
        )

    def test_build_output_regime_returns_continuite_for_dialogue_trace_anchor(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(
                provenances=["dialogue_trace"],
                temporal_scope="passee",
                temporal_anchor="dialogue_trace",
            ),
        )

        self.assertEqual(payload["discursive_regime"], "continuite")
        self.assertEqual(payload["resituation_level"], "light")
        self.assertEqual(payload["time_reference_mode"], "dialogue_relative")

    def test_build_output_regime_returns_immediate_now_for_now_anchored_current_turn(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(
                temporal_scope="immediate",
                temporal_anchor="now",
            ),
        )

        self.assertEqual(payload["time_reference_mode"], "immediate_now")

    def test_build_output_regime_returns_anchored_past_for_historical_anchor(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(
                temporal_scope="passee",
                temporal_anchor="historique_externe",
            ),
        )

        self.assertEqual(payload["discursive_regime"], "simple")
        self.assertEqual(payload["time_reference_mode"], "anchored_past")

    def test_build_output_regime_returns_prospective_for_projection(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(
                temporal_scope="prospective",
                temporal_anchor="projection",
            ),
        )

        self.assertEqual(payload["time_reference_mode"], "prospective")

    def test_build_output_regime_does_not_invent_comparatif_from_multi_provenance_alone(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(
                provenances=["dialogue_trace", "web"],
                proof_types=["factuelle", "scientifique"],
                composition="convergente",
                temporal_scope="passee",
                temporal_anchor="dialogue_trace",
            ),
        )

        self.assertEqual(payload["discursive_regime"], "continuite")
        self.assertNotEqual(payload["discursive_regime"], "comparatif")

    def test_build_output_regime_returns_only_closed_taxonomies(self) -> None:
        payload = output_regime.build_output_regime(
            judgment_posture="answer",
            user_turn_input=_user_turn(gesture="regulation"),
        )

        self.assertIn(payload["discursive_regime"], output_regime.DISCURSIVE_REGIMES)
        self.assertIn(payload["resituation_level"], output_regime.RESITUATION_LEVELS)
        self.assertIn(payload["time_reference_mode"], output_regime.TIME_REFERENCE_MODES)
        self.assertNotEqual(payload["discursive_regime"], "meta")


if __name__ == "__main__":
    unittest.main()
