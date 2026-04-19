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

from core.hermeneutic_node.doctrine import source_conflicts


def _source_priority(
    ranks: list[list[str]] | None = None,
) -> dict[str, object]:
    return {
        "source_priority": ranks
        or [
            ["tour_utilisateur"],
            ["temps"],
            ["memoire", "contexte_recent", "identity"],
            ["resume"],
            ["web"],
            ["stimmung"],
        ]
    }


def _user_turn(
    *,
    gesture: str = "interrogation",
    provenances: list[str] | None = None,
    proof_types: list[str] | None = None,
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
            "composition_probatoire": "isolee",
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


def _identity(*, static: bool = False, mutable: bool = False) -> dict[str, object]:
    static_block = {"content": "known", "source": "repo"} if static else {"content": "", "source": None}
    mutable_block = {
        "content": "identity mutable",
        "source_trace_id": "11111111-1111-1111-1111-111111111111",
        "updated_by": "identity_periodic_agent",
        "update_reason": "periodic_agent",
        "updated_ts": "2026-04-01T10:00:00Z",
    } if mutable else {
        "content": "",
        "source_trace_id": None,
        "updated_by": None,
        "update_reason": None,
        "updated_ts": None,
    }
    return {
        "schema_version": "v2",
        "frida": {"static": static_block, "mutable": dict(mutable_block)},
        "user": {"static": static_block, "mutable": dict(mutable_block)},
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


class SourceConflictsTests(unittest.TestCase):
    def test_build_source_conflicts_requires_valid_source_priority(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_source_priority"):
            source_conflicts.build_source_conflicts(
                source_priority={"source_priority": [["tour_utilisateur"], ["temps"]]},
                user_turn_input=_user_turn(),
                user_turn_signals=_signals(),
            )

    def test_build_source_conflicts_requires_valid_user_turn_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_input"):
            source_conflicts.build_source_conflicts(
                source_priority=_source_priority(),
                user_turn_input=None,
                user_turn_signals=_signals(),
            )

    def test_build_source_conflicts_requires_produced_user_turn_signals(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_signals"):
            source_conflicts.build_source_conflicts(
                source_priority=_source_priority(),
                user_turn_input=_user_turn(),
                user_turn_signals=_signals(present=False),
            )

    def test_build_source_conflicts_returns_empty_by_default(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_does_not_treat_same_rank_alone_as_conflict(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            recent_context_input=_recent_context(message_count=2),
            identity_input=_identity(static=True),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_does_not_treat_simple_simultaneous_availability_as_conflict(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            recent_context_input=_recent_context(message_count=1),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_does_not_treat_web_request_alone_as_conflict(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(
                [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["web"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["stimmung"],
                ]
            ),
            user_turn_input=_user_turn(provenances=["web"], proof_types=["scientifique"]),
            user_turn_signals=_signals(),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_detects_residual_source_anchor_conflict(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(
                [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "web"],
                    ["contexte_recent", "identity"],
                    ["resume"],
                    ["stimmung"],
                ]
            ),
            user_turn_input=_user_turn(provenances=["dialogue_trace", "web"]),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(
            payload,
            {
                "source_conflicts": [
                    {
                        "conflict_type": "conflit_d_ancrage_de_source",
                        "sources": ["memoire", "web"],
                        "issue": "review_required",
                    }
                ]
            },
        )

    def test_build_source_conflicts_does_not_emit_anchor_conflict_from_mutable_only_identity(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(gesture="adresse_relationnelle"),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            identity_input=_identity(static=False, mutable=True),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_keeps_static_identity_as_anchor_conflict_candidate(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(gesture="adresse_relationnelle"),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            identity_input=_identity(static=True),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
        )

        self.assertEqual(
            payload,
            {
                "source_conflicts": [
                    {
                        "conflict_type": "conflit_d_ancrage_de_source",
                        "sources": ["memoire", "identity"],
                        "issue": "review_required",
                    }
                ]
            },
        )

    def test_build_source_conflicts_does_not_emit_anchor_conflict_when_one_source_is_missing(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(
                [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "web"],
                    ["contexte_recent", "identity"],
                    ["resume"],
                    ["stimmung"],
                ]
            ),
            user_turn_input=_user_turn(provenances=["dialogue_trace", "web"]),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            web_input=_web(status="skipped", results_count=0),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_does_not_invent_continuite_conflict_from_coherence_signal(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(),
            user_turn_input=_user_turn(),
            user_turn_signals=_signals(ambiguity=True, families=["coherence"]),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            recent_context_input=_recent_context(message_count=1),
            summary_input=_summary(available=True),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_does_not_invent_factuel_conflict_from_counts_or_ranks(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(
                [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "web"],
                    ["contexte_recent", "identity"],
                    ["resume"],
                    ["stimmung"],
                ]
            ),
            user_turn_input=_user_turn(provenances=["dialogue_trace", "web"]),
            user_turn_signals=_signals(ambiguity=True, families=["coherence"]),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(payload, {"source_conflicts": []})

    def test_build_source_conflicts_emits_only_review_required_issue(self) -> None:
        payload = source_conflicts.build_source_conflicts(
            source_priority=_source_priority(
                [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "web"],
                    ["contexte_recent", "identity"],
                    ["resume"],
                    ["stimmung"],
                ]
            ),
            user_turn_input=_user_turn(provenances=["dialogue_trace", "web"]),
            user_turn_signals=_signals(
                underdetermination=True,
                families=["ancrage_de_source"],
            ),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            memory_arbitration=_memory_arbitration(kept_count=1),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual([conflict["issue"] for conflict in payload["source_conflicts"]], ["review_required"])


if __name__ == "__main__":
    unittest.main()
