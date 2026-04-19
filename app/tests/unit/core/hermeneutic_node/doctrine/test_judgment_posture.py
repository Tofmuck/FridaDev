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

from core.hermeneutic_node.doctrine import judgment_posture


def _signals(
    *,
    present: bool = True,
    ambiguity: bool = False,
    underdetermination: bool = False,
    families: list[str] | None = None,
) -> dict[str, object]:
    family_list = list(families or [])
    return {
        "present": present,
        "ambiguity_present": ambiguity,
        "underdetermination_present": underdetermination,
        "active_signal_families": family_list,
        "active_signal_families_count": len(family_list),
    }


class JudgmentPostureTests(unittest.TestCase):
    def test_build_judgment_posture_rejects_missing_user_turn_signals(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_signals"):
            judgment_posture.build_judgment_posture(
                user_turn_signals=None,
                epistemic_regime="probable",
                proof_regime="source_explicite_requise",
                uncertainty_posture="prudente",
            )

    def test_build_judgment_posture_rejects_non_produced_user_turn_signals(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_signals"):
            judgment_posture.build_judgment_posture(
                user_turn_signals=_signals(present=False),
                epistemic_regime="probable",
                proof_regime="source_explicite_requise",
                uncertainty_posture="prudente",
            )

    def test_build_judgment_posture_returns_answer_for_certain_without_cadrage_block(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(),
            epistemic_regime="certain",
            proof_regime="suffisant_en_l_etat",
            uncertainty_posture="discrete",
        )

        self.assertEqual(payload, {"judgment_posture": "answer"})

    def test_build_judgment_posture_returns_answer_for_probable_without_cadrage_block(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(),
            epistemic_regime="probable",
            proof_regime="source_explicite_requise",
            uncertainty_posture="prudente",
        )

        self.assertEqual(payload, {"judgment_posture": "answer"})

    def test_build_judgment_posture_returns_clarify_for_certain_with_referent_signal(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(ambiguity=True, families=["referent"]),
            epistemic_regime="certain",
            proof_regime="suffisant_en_l_etat",
            uncertainty_posture="discrete",
        )

        self.assertEqual(payload, {"judgment_posture": "clarify"})

    def test_build_judgment_posture_returns_clarify_for_probable_with_critere_signal(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(underdetermination=True, families=["critere"]),
            epistemic_regime="probable",
            proof_regime="source_explicite_requise",
            uncertainty_posture="prudente",
        )

        self.assertEqual(payload, {"judgment_posture": "clarify"})

    def test_build_judgment_posture_keeps_a_verifier_in_clarify_when_cadrage_signal_exists(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(ambiguity=True, families=["referent"]),
            epistemic_regime="a_verifier",
            proof_regime="verification_externe_requise",
            uncertainty_posture="explicite",
        )

        self.assertEqual(payload, {"judgment_posture": "clarify"})

    def test_build_judgment_posture_returns_suspend_for_contradictoire(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(),
            epistemic_regime="contradictoire",
            proof_regime="arbitrage_requis",
            uncertainty_posture="bloquante",
        )

        self.assertEqual(payload, {"judgment_posture": "suspend"})

    def test_build_judgment_posture_returns_suspend_for_suspendu(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(underdetermination=True, families=["portee"]),
            epistemic_regime="suspendu",
            proof_regime="source_explicite_requise",
            uncertainty_posture="bloquante",
        )

        self.assertEqual(payload, {"judgment_posture": "suspend"})

    def test_build_judgment_posture_does_not_suspend_when_verification_externe_is_required_by_itself(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(ambiguity=True, families=["referent"]),
            epistemic_regime="probable",
            proof_regime="verification_externe_requise",
            uncertainty_posture="explicite",
        )

        self.assertEqual(payload, {"judgment_posture": "clarify"})

    def test_build_judgment_posture_returns_suspend_when_uncertainty_is_bloquante(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(ambiguity=True, families=["referent"]),
            epistemic_regime="probable",
            proof_regime="source_explicite_requise",
            uncertainty_posture="bloquante",
        )

        self.assertEqual(payload, {"judgment_posture": "suspend"})

    def test_build_judgment_posture_returns_clarify_for_incertain_with_cadrage_signals(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(ambiguity=True, underdetermination=True, families=["visee", "critere"]),
            epistemic_regime="incertain",
            proof_regime="source_explicite_requise",
            uncertainty_posture="explicite",
        )

        self.assertEqual(payload, {"judgment_posture": "clarify"})
        self.assertNotEqual(payload["judgment_posture"], "suspend")

    def test_build_judgment_posture_returns_answer_for_incertain_without_cadrage_signals(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(),
            epistemic_regime="incertain",
            proof_regime="source_explicite_requise",
            uncertainty_posture="explicite",
        )

        self.assertEqual(payload, {"judgment_posture": "answer"})

    def test_build_judgment_posture_ignores_non_canonical_signal_family_count_alone(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(families=["tonalite"]),
            epistemic_regime="probable",
            proof_regime="source_explicite_requise",
            uncertainty_posture="prudente",
        )

        self.assertEqual(payload, {"judgment_posture": "answer"})

    def test_build_judgment_posture_does_not_turn_explicite_uncertainty_into_suspend_by_itself(self) -> None:
        payload = judgment_posture.build_judgment_posture(
            user_turn_signals=_signals(),
            epistemic_regime="probable",
            proof_regime="source_explicite_requise",
            uncertainty_posture="explicite",
        )

        self.assertEqual(payload, {"judgment_posture": "answer"})


if __name__ == "__main__":
    unittest.main()
