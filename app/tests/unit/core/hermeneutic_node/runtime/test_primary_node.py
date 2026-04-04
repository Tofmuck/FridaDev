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

from core.hermeneutic_node.runtime import primary_node
from core.hermeneutic_node.inputs import user_turn_input


def _time() -> dict[str, object]:
    return {
        "schema_version": "v1",
        "now_utc_iso": "2026-04-02T10:00:00Z",
        "timezone": "Europe/Paris",
        "now_local_iso": "2026-04-02T12:00:00+02:00",
        "local_date": "2026-04-02",
        "local_time": "12:00",
        "local_weekday": "thursday",
        "day_part_class": "afternoon",
        "day_part_human": "apres-midi",
    }


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


def _memory_retrieved(*, retrieved_count: int = 0) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "retrieval_query": "",
        "top_k_requested": None,
        "retrieved_count": retrieved_count,
        "traces": [],
    }


def _memory_arbitration(*, kept_count: int = 0, rejected_count: int = 0, status: str = "ok") -> dict[str, object]:
    return {
        "schema_version": "v1",
        "status": status,
        "reason_code": None,
        "raw_candidates_count": kept_count + rejected_count,
        "decisions_count": kept_count + rejected_count,
        "kept_count": kept_count,
        "rejected_count": rejected_count,
        "decisions": [],
    }


def _summary(*, available: bool = False) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "status": "available" if available else "missing",
        "summary": {"id": "sum-1"} if available else None,
    }


def _recent_context(*, message_count: int = 0) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "messages": [{"role": "user", "content": "", "timestamp": None} for _ in range(message_count)],
    }


def _recent_window(*, turn_count: int = 0) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "max_recent_turns": 5,
        "turn_count": turn_count,
        "has_in_progress_turn": False,
        "turns": [],
    }


def _identity(*, static: bool = False, dynamic_count: int = 0) -> dict[str, object]:
    static_block = {"content": "known", "source": "repo"} if static else {"content": "", "source": None}
    dynamic_entries = [
        {
            "id": f"dyn-{index}",
            "content": "episodic",
            "stability": "low",
            "recurrence": "low",
            "confidence": 0.6,
            "last_seen_ts": "2026-04-01T10:00:00Z",
            "scope": "conversation",
        }
        for index in range(dynamic_count)
    ]
    return {
        "schema_version": "v1",
        "frida": {"static": static_block, "dynamic": list(dynamic_entries)},
        "user": {"static": static_block, "dynamic": list(dynamic_entries)},
    }


def _web(*, status: str = "skipped", results_count: int = 0) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "enabled": True,
        "status": status,
        "reason_code": None,
        "original_user_message": "",
        "query": None,
        "results_count": results_count,
        "runtime": {},
        "sources": [],
        "context_block": "",
    }


def _existing_state(
    *,
    conversation_id: str = "conv-1",
    updated_at: str = "2026-04-01T12:00:00Z",
    judgment_posture: str = "answer",
    discursive_regime: str = "continuite",
    resituation_level: str = "light",
    time_reference_mode: str = "dialogue_relative",
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "conversation_id": conversation_id,
        "updated_at": updated_at,
        "last_judgment_posture": judgment_posture,
        "last_answer_output_regime": {
            "discursive_regime": discursive_regime,
            "resituation_level": resituation_level,
            "time_reference_mode": time_reference_mode,
        },
    }


class PrimaryNodeTests(unittest.TestCase):
    def test_build_primary_node_rejects_invalid_conversation_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_conversation_id"):
            primary_node.build_primary_node(
                conversation_id="",
                updated_at="2026-04-02T12:00:00Z",
                time_input=_time(),
                user_turn_input=_user_turn(),
                user_turn_signals=_signals(),
            )

    def test_build_primary_node_rejects_invalid_updated_at(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_updated_at"):
            primary_node.build_primary_node(
                conversation_id="conv-1",
                updated_at="bad-date",
                time_input=_time(),
                user_turn_input=_user_turn(),
                user_turn_signals=_signals(),
            )

    def test_build_primary_node_returns_nominal_primary_verdict_and_node_state(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload,
            {
                "primary_verdict": {
                    "schema_version": "v1",
                    "epistemic_regime": "incertain",
                    "proof_regime": "source_explicite_requise",
                    "uncertainty_posture": "prudente",
                    "judgment_posture": "answer",
                    "discursive_regime": "simple",
                    "resituation_level": "none",
                    "time_reference_mode": "atemporal",
                    "source_priority": [
                        ["tour_utilisateur"],
                        ["temps"],
                        ["memoire", "contexte_recent", "identity"],
                        ["resume"],
                        ["web"],
                        ["stimmung"],
                    ],
                    "source_conflicts": [],
                    "pipeline_directives_provisional": ["posture_answer"],
                    "audit": {
                        "fail_open": False,
                        "state_used": False,
                        "degraded_fields": [],
                    },
                },
                "node_state": {
                    "schema_version": "v1",
                    "conversation_id": "conv-1",
                    "updated_at": "2026-04-02T12:00:00Z",
                    "last_judgment_posture": "answer",
                    "last_answer_output_regime": {
                        "discursive_regime": "simple",
                        "resituation_level": "none",
                        "time_reference_mode": "atemporal",
                    },
                },
            },
        )
        self.assertNotIn("justifications", payload["primary_verdict"])

    def test_build_primary_node_propagates_source_conflicts_into_primary_verdict(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            identity_input=_identity(static=True),
            user_turn_input=_user_turn(
                gesture="adresse_relationnelle",
                provenances=["dialogue_trace"],
            ),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertEqual(
            payload["primary_verdict"]["source_conflicts"],
            [
                {
                    "conflict_type": "conflit_d_ancrage_de_source",
                    "sources": ["memoire", "identity"],
                    "issue": "clarify",
                }
            ],
        )
        self.assertEqual(
            payload["primary_verdict"]["pipeline_directives_provisional"],
            ["posture_clarify", "source_conflict_clarify"],
        )
        self.assertEqual(
            payload["primary_verdict"]["judgment_posture"],
            "clarify",
        )

    def test_build_primary_node_does_not_suspend_clear_imaginative_question_as_external_verification(self) -> None:
        bundle = user_turn_input.build_user_turn_bundle(
            user_message="Imagine que tu es une extraterrestre envoyee sur Terre pour sauver la biodiversite. C'est ton job ultime. Que fais-tu ?",
            recent_window_input_payload=None,
            time_input_payload={"now_utc_iso": "2026-04-02T10:00:00Z"},
        )

        payload = primary_node.build_primary_node(
            conversation_id="conv-fiction",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=bundle["user_turn"],
            user_turn_signals=bundle["user_turn_signals"],
            stimmung_input=_stimmung(),
            web_input=_web(),
        )

        self.assertNotEqual(payload["primary_verdict"]["epistemic_regime"], "a_verifier")
        self.assertNotEqual(payload["primary_verdict"]["proof_regime"], "verification_externe_requise")
        self.assertEqual(payload["primary_verdict"]["judgment_posture"], "answer")

    def test_build_primary_node_applies_inertia_before_verdict_and_state(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            existing_node_state=_existing_state(),
        )

        self.assertTrue(payload["primary_verdict"]["audit"]["state_used"])
        self.assertEqual(
            payload["primary_verdict"]["discursive_regime"],
            "continuite",
        )
        self.assertEqual(
            payload["node_state"]["last_answer_output_regime"],
            {
                "discursive_regime": "continuite",
                "resituation_level": "light",
                "time_reference_mode": "dialogue_relative",
            },
        )

    def test_build_primary_node_does_not_apply_inertia_on_marked_current_output_regime(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(gesture="regulation"),
            user_turn_signals=_signals(),
            existing_node_state=_existing_state(),
        )

        self.assertFalse(payload["primary_verdict"]["audit"]["state_used"])
        self.assertEqual(
            payload["primary_verdict"]["discursive_regime"],
            "cadre",
        )
        self.assertEqual(
            payload["node_state"]["last_answer_output_regime"],
            {
                "discursive_regime": "cadre",
                "resituation_level": "explicit",
                "time_reference_mode": "atemporal",
            },
        )

    def test_build_primary_node_ignores_invalid_existing_node_state_on_valid_turn(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(gesture="regulation"),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
            existing_node_state={},
        )

        self.assertFalse(payload["primary_verdict"]["audit"]["fail_open"])
        self.assertFalse(payload["primary_verdict"]["audit"]["state_used"])
        self.assertEqual(payload["primary_verdict"]["judgment_posture"], "answer")
        self.assertEqual(payload["primary_verdict"]["discursive_regime"], "cadre")
        self.assertEqual(payload["primary_verdict"]["resituation_level"], "explicit")
        self.assertEqual(
            payload["node_state"],
            {
                "schema_version": "v1",
                "conversation_id": "conv-1",
                "updated_at": "2026-04-02T12:00:00Z",
                "last_judgment_posture": "answer",
                "last_answer_output_regime": {
                    "discursive_regime": "cadre",
                    "resituation_level": "explicit",
                    "time_reference_mode": "atemporal",
                },
            },
        )

    def test_build_primary_node_ignores_cross_conversation_state_on_valid_turn(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(gesture="regulation"),
            user_turn_signals=_signals(),
            stimmung_input=_stimmung(),
            web_input=_web(),
            existing_node_state=_existing_state(conversation_id="conv-other"),
        )

        self.assertFalse(payload["primary_verdict"]["audit"]["fail_open"])
        self.assertFalse(payload["primary_verdict"]["audit"]["state_used"])
        self.assertEqual(payload["primary_verdict"]["judgment_posture"], "answer")
        self.assertEqual(payload["primary_verdict"]["discursive_regime"], "cadre")
        self.assertEqual(payload["primary_verdict"]["resituation_level"], "explicit")
        self.assertEqual(
            payload["node_state"],
            {
                "schema_version": "v1",
                "conversation_id": "conv-1",
                "updated_at": "2026-04-02T12:00:00Z",
                "last_judgment_posture": "answer",
                "last_answer_output_regime": {
                    "discursive_regime": "cadre",
                    "resituation_level": "explicit",
                    "time_reference_mode": "atemporal",
                },
            },
        )

    def test_build_primary_node_fail_opens_on_invalid_user_turn_signals(self) -> None:
        payload = primary_node.build_primary_node(
            conversation_id="conv-1",
            updated_at="2026-04-02T12:00:00Z",
            time_input=_time(),
            user_turn_input=_user_turn(),
            user_turn_signals=None,
            existing_node_state=_existing_state(),
        )

        self.assertEqual(
            payload["primary_verdict"],
            {
                "schema_version": "v1",
                "epistemic_regime": "suspendu",
                "proof_regime": "source_explicite_requise",
                "uncertainty_posture": "bloquante",
                "judgment_posture": "suspend",
                "discursive_regime": "meta",
                "resituation_level": "none",
                "time_reference_mode": "atemporal",
                "source_priority": [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["web"],
                    ["stimmung"],
                ],
                "source_conflicts": [],
                "pipeline_directives_provisional": [
                    "posture_suspend",
                    "fallback_primary_verdict",
                ],
                "audit": {
                    "fail_open": True,
                    "state_used": False,
                    "degraded_fields": [
                        "epistemic_regime",
                        "proof_regime",
                        "uncertainty_posture",
                        "judgment_posture",
                        "discursive_regime",
                        "resituation_level",
                        "time_reference_mode",
                        "source_priority",
                        "source_conflicts",
                        "pipeline_directives_provisional",
                    ],
                },
            },
        )
        self.assertEqual(
            payload["node_state"],
            {
                "schema_version": "v1",
                "conversation_id": "conv-1",
                "updated_at": "2026-04-02T12:00:00Z",
                "last_judgment_posture": "suspend",
                "last_answer_output_regime": {
                    "discursive_regime": "continuite",
                    "resituation_level": "light",
                    "time_reference_mode": "dialogue_relative",
                },
            },
        )
        self.assertEqual(set(payload["primary_verdict"]), {
            "schema_version",
            "epistemic_regime",
            "proof_regime",
            "uncertainty_posture",
            "judgment_posture",
            "discursive_regime",
            "resituation_level",
            "time_reference_mode",
            "source_priority",
            "source_conflicts",
            "pipeline_directives_provisional",
            "audit",
        })


if __name__ == "__main__":
    unittest.main()
