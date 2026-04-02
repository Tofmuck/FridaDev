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

from core.hermeneutic_node.doctrine import epistemic_regime


def _user_turn(
    *,
    provenances: list[str] | None = None,
    proof_types: list[str] | None = None,
    temporal_scope: str = "atemporale",
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "geste_dialogique_dominant": "interrogation",
        "regime_probatoire": {
            "principe": "maximal_possible",
            "types_de_preuve_attendus": list(proof_types or []),
            "provenances": list(provenances or []),
            "regime_de_vigilance": "standard",
            "composition_probatoire": "isolee",
        },
        "qualification_temporelle": {
            "portee_temporelle": temporal_scope,
            "ancrage_temporel": "non_ancre",
        },
    }


def _signals(
    *,
    ambiguity: bool = False,
    underdetermination: bool = False,
    families: list[str] | None = None,
) -> dict[str, object]:
    return {
        "present": True,
        "ambiguity_present": ambiguity,
        "underdetermination_present": underdetermination,
        "active_signal_families": list(families or []),
        "active_signal_families_count": len(list(families or [])),
    }


def _stimmung(
    *,
    present: bool = False,
    dominant_tone: str | None = None,
    stability: str = "",
    shift_state: str = "",
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "present": present,
        "dominant_tone": dominant_tone,
        "active_tones": [] if not present else [{"tone": dominant_tone, "strength": 5}],
        "stability": stability,
        "shift_state": shift_state,
        "turns_considered": 0 if not present else 3,
    }


def _web_source(
    *,
    used_in_prompt: bool = False,
    used_content_kind: str = "none",
    content_used: str = "",
) -> dict[str, object]:
    return {
        "rank": 1,
        "title": "Source",
        "url": "https://example.test/source",
        "source_domain": "example.test",
        "search_snippet": "",
        "used_in_prompt": used_in_prompt,
        "used_content_kind": used_content_kind,
        "content_used": content_used,
        "truncated": False,
    }


def _web(
    *,
    status: str = "skipped",
    results_count: int = 0,
    reason_code: str | None = None,
    sources: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "enabled": True,
        "status": status,
        "reason_code": reason_code,
        "original_user_message": "",
        "query": None,
        "results_count": results_count,
        "runtime": {},
        "sources": list(sources or []),
        "context_block": "",
    }


def _summary(*, available: bool) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "status": "available" if available else "missing",
        "summary": {"id": "sum-1"} if available else None,
    }


def _recent_window(*, turn_count: int) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "max_recent_turns": 5,
        "turn_count": turn_count,
        "has_in_progress_turn": False,
        "turns": [],
    }


def _memory_retrieved(*, retrieved_count: int) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "retrieval_query": "",
        "top_k_requested": None,
        "retrieved_count": retrieved_count,
        "traces": [],
    }


def _memory_arbitration(
    *,
    status: str = "ok",
    reason_code: str | None = None,
    kept_count: int = 0,
    rejected_count: int = 0,
    decisions: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    decision_list = list(decisions or [])
    return {
        "schema_version": "v1",
        "status": status,
        "reason_code": reason_code,
        "raw_candidates_count": kept_count + rejected_count,
        "decisions_count": len(decision_list),
        "kept_count": kept_count,
        "rejected_count": rejected_count,
        "decisions": decision_list,
    }


class EpistemicRegimeTests(unittest.TestCase):
    def test_build_epistemic_regime_returns_certain_on_strong_convergence(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            memory_retrieved=_memory_retrieved(retrieved_count=2),
            memory_arbitration=_memory_arbitration(kept_count=1),
            summary_input=_summary(available=True),
            recent_window_input=_recent_window(turn_count=2),
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "certain",
                "proof_regime": "suffisant_en_l_etat",
                "uncertainty_posture": "discrete",
            },
        )

    def test_build_epistemic_regime_returns_probable_for_dominant_but_prudent_reading(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            summary_input=_summary(available=False),
            recent_window_input=_recent_window(turn_count=1),
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            user_turn_signals=_signals(underdetermination=True, families=["critere"]),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "probable",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "prudente",
            },
        )

    def test_build_epistemic_regime_returns_incertain_for_poor_but_non_blocked_reading(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(underdetermination=True, families=["critere"]),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "incertain",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "explicite",
            },
        )

    def test_build_epistemic_regime_returns_a_verifier_when_identifiable_verification_is_missing(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            user_turn_input=_user_turn(provenances=["web"], proof_types=["scientifique"], temporal_scope="actuelle"),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(status="skipped", results_count=0, reason_code="no_data"),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "a_verifier",
                "proof_regime": "verification_externe_requise",
                "uncertainty_posture": "explicite",
            },
        )

    def test_build_epistemic_regime_returns_suspendu_when_no_responsible_reading_can_be_held(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            user_turn_signals=_signals(
                ambiguity=True,
                underdetermination=True,
                families=["referent", "critere"],
            ),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "suspendu",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "bloquante",
            },
        )

    def test_build_epistemic_regime_does_not_count_fully_rejected_memory_as_support(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            memory_retrieved=_memory_retrieved(retrieved_count=2),
            memory_arbitration=_memory_arbitration(
                kept_count=0,
                rejected_count=2,
            ),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "incertain",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "prudente",
            },
        )

    def test_build_epistemic_regime_keeps_scientifique_in_a_verifier_on_generic_web_hit(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            user_turn_input=_user_turn(provenances=["web"], proof_types=["scientifique"], temporal_scope="actuelle"),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "a_verifier",
                "proof_regime": "verification_externe_requise",
                "uncertainty_posture": "explicite",
            },
        )

    def test_build_epistemic_regime_does_not_invent_contradiction_from_synthetic_reason_codes(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            memory_retrieved=_memory_retrieved(retrieved_count=2),
            memory_arbitration=_memory_arbitration(
                kept_count=1,
                rejected_count=1,
                reason_code="source_conflict",
                decisions=[
                    {"keep": True, "reason": "source_conflict"},
                    {"keep": False, "reason": "conflict marker"},
                ],
            ),
            recent_window_input=_recent_window(turn_count=1),
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "probable",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "discrete",
            },
        )

    def test_build_epistemic_regime_does_not_invent_contradiction_from_simple_memory_plurality(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            memory_retrieved=_memory_retrieved(retrieved_count=2),
            memory_arbitration=_memory_arbitration(
                kept_count=1,
                rejected_count=1,
                decisions=[
                    {"keep": True, "reason": "useful reminder"},
                    {"keep": False, "reason": "redundant with recent"},
                ],
            ),
            recent_window_input=_recent_window(turn_count=1),
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(payload["epistemic_regime"], "probable")
        self.assertNotEqual(payload["epistemic_regime"], "contradictoire")

    def test_build_epistemic_regime_keeps_spec_compatible_triples(self) -> None:
        cases = (
            epistemic_regime.build_epistemic_regime(
                memory_retrieved=_memory_retrieved(retrieved_count=2),
                memory_arbitration=_memory_arbitration(kept_count=1),
                summary_input=_summary(available=True),
                recent_window_input=_recent_window(turn_count=2),
                user_turn_input=_user_turn(provenances=["dialogue_trace"]),
                user_turn_signals=_signals(),
                stimmung_input=_stimmung(),
                web_input=_web(),
            ),
            epistemic_regime.build_epistemic_regime(
                user_turn_input=_user_turn(provenances=["web"], proof_types=["scientifique"]),
                user_turn_signals=_signals(),
                stimmung_input=_stimmung(),
                web_input=_web(status="error", results_count=0, reason_code="upstream_error"),
            ),
            epistemic_regime.build_epistemic_regime(
                recent_window_input=_recent_window(turn_count=1),
                user_turn_input=_user_turn(provenances=["dialogue_trace"]),
                user_turn_signals=_signals(),
                stimmung_input=_stimmung(),
                web_input=_web(),
            ),
            epistemic_regime.build_epistemic_regime(
                user_turn_input=_user_turn(provenances=["dialogue_trace"]),
                user_turn_signals=_signals(
                    ambiguity=True,
                    underdetermination=True,
                    families=["referent", "critere"],
                ),
                stimmung_input=_stimmung(),
                web_input=_web(),
            ),
        )

        for payload in cases:
            self.assertIn(payload["epistemic_regime"], epistemic_regime.EPISTEMIC_REGIMES)
            self.assertIn(payload["proof_regime"], epistemic_regime.PROOF_REGIMES)
            self.assertIn(payload["uncertainty_posture"], epistemic_regime.UNCERTAINTY_POSTURES)

            if payload["epistemic_regime"] == "certain":
                self.assertEqual(payload["proof_regime"], "suffisant_en_l_etat")
                self.assertEqual(payload["uncertainty_posture"], "discrete")
            if payload["epistemic_regime"] == "contradictoire":
                self.assertEqual(payload["proof_regime"], "arbitrage_requis")
                self.assertEqual(payload["uncertainty_posture"], "bloquante")
            if payload["epistemic_regime"] == "a_verifier":
                self.assertEqual(payload["proof_regime"], "verification_externe_requise")
                self.assertIn(payload["uncertainty_posture"], {"explicite", "bloquante"})
            if payload["epistemic_regime"] == "suspendu":
                self.assertNotEqual(payload["proof_regime"], "suffisant_en_l_etat")

    def test_build_epistemic_regime_does_not_promote_certainty_from_stimmung_alone(self) -> None:
        payload = epistemic_regime.build_epistemic_regime(
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(
                present=True,
                dominant_tone="apaisement",
                stability="stable",
                shift_state="steady",
            ),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "epistemic_regime": "incertain",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "prudente",
            },
        )


if __name__ == "__main__":
    unittest.main()
