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

from core.hermeneutic_node.doctrine import source_priority


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
    enabled: bool = True,
    status: str = "skipped",
    results_count: int = 0,
    sources: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "enabled": enabled,
        "status": status,
        "reason_code": None,
        "original_user_message": "",
        "query": None,
        "results_count": results_count,
        "runtime": {},
        "sources": list(sources or []),
        "context_block": "",
    }


def _flatten(priority_payload: dict[str, list[list[str]]]) -> list[str]:
    return [family for rank in priority_payload["source_priority"] for family in rank]


class SourcePriorityTests(unittest.TestCase):
    def test_build_source_priority_requires_user_turn_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_user_turn_input"):
            source_priority.build_source_priority(
                user_turn_input=None,
                time_input=_time(),
            )

    def test_build_source_priority_requires_time_input(self) -> None:
        with self.assertRaisesRegex(ValueError, "invalid_time_input"):
            source_priority.build_source_priority(
                user_turn_input=_user_turn(),
                time_input=None,
            )

    def test_build_source_priority_returns_default_order(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(),
            time_input=_time(),
        )

        self.assertEqual(
            payload,
            {
                "source_priority": [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["web"],
                    ["stimmung"],
                ]
            },
        )

    def test_build_source_priority_does_not_promote_web_on_simple_availability(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(),
            time_input=_time(),
            web_input=_web(status="ok", results_count=3),
        )

        self.assertEqual(payload["source_priority"][4], ["web"])
        self.assertEqual(payload["source_priority"][2], ["memoire", "contexte_recent", "identity"])

    def test_build_source_priority_promotes_web_for_explicit_web_provenance(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(provenances=["web"]),
            time_input=_time(),
        )

        self.assertEqual(
            payload["source_priority"],
            [
                ["tour_utilisateur"],
                ["temps"],
                ["web"],
                ["memoire", "contexte_recent", "identity"],
                ["resume"],
                ["stimmung"],
            ],
        )

    def test_build_source_priority_promotes_web_for_scientific_need(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(proof_types=["scientifique"]),
            time_input=_time(),
        )

        self.assertEqual(payload["source_priority"][2], ["web"])

    def test_build_source_priority_promotes_web_for_current_fact_request(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(proof_types=["factuelle"], temporal_scope="actuelle"),
            time_input=_time(),
        )

        self.assertEqual(payload["source_priority"][2], ["web"])

    def test_build_source_priority_promotes_memoire_for_dialogue_trace(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(provenances=["dialogue_trace"]),
            time_input=_time(),
            memory_retrieved=_memory_retrieved(retrieved_count=2),
        )

        self.assertEqual(payload["source_priority"][2], ["memoire"])
        self.assertEqual(payload["source_priority"][3], ["contexte_recent", "identity"])

    def test_build_source_priority_promotes_resume_only_as_bounded_fallback(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(provenances=["dialogue_resume"], temporal_anchor="dialogue_resume"),
            time_input=_time(),
            summary_input=_summary(available=True),
            memory_retrieved=_memory_retrieved(retrieved_count=0),
            recent_context_input=_recent_context(message_count=0),
        )

        self.assertEqual(payload["source_priority"][2], ["memoire", "contexte_recent", "identity", "resume"])
        self.assertEqual(payload["source_priority"][3], ["web"])

    def test_build_source_priority_promotes_recent_context_for_local_regulation(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(gesture="regulation"),
            time_input=_time(),
            recent_context_input=_recent_context(message_count=2),
        )

        self.assertEqual(payload["source_priority"][2], ["contexte_recent"])
        self.assertEqual(payload["source_priority"][3], ["memoire", "identity"])

    def test_build_source_priority_promotes_identity_once_with_static_priority(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(gesture="adresse_relationnelle"),
            time_input=_time(),
            identity_input=_identity(static=True, dynamic_count=2),
        )

        self.assertEqual(payload["source_priority"][2], ["identity"])
        self.assertEqual(_flatten(payload).count("identity"), 1)

    def test_build_source_priority_does_not_promote_identity_from_sourced_but_empty_static_block(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(gesture="adresse_relationnelle"),
            time_input=_time(),
            identity_input={
                "schema_version": "v1",
                "frida": {"static": {"content": "", "source": "repo"}, "dynamic": []},
                "user": {"static": {"content": "", "source": None}, "dynamic": []},
            },
        )

        self.assertEqual(
            payload,
            {
                "source_priority": [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["web"],
                    ["stimmung"],
                ]
            },
        )

    def test_build_source_priority_does_not_promote_identity_from_dynamic_only(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(gesture="adresse_relationnelle"),
            time_input=_time(),
            identity_input=_identity(static=False, dynamic_count=2),
        )

        self.assertEqual(
            payload,
            {
                "source_priority": [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["web"],
                    ["stimmung"],
                ]
            },
        )

    def test_build_source_priority_does_not_promote_web_from_downstream_usage_markers(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(),
            time_input=_time(),
            web_input=_web(
                status="ok",
                results_count=3,
                sources=[_web_source(used_in_prompt=True, used_content_kind="quote", content_used="used")],
            ),
        )

        self.assertEqual(
            payload,
            {
                "source_priority": [
                    ["tour_utilisateur"],
                    ["temps"],
                    ["memoire", "contexte_recent", "identity"],
                    ["resume"],
                    ["web"],
                    ["stimmung"],
                ]
            },
        )

    def test_build_source_priority_keeps_stimmung_last_even_with_other_promotions(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(provenances=["web", "dialogue_trace"], proof_types=["scientifique"]),
            time_input=_time(),
            memory_retrieved=_memory_retrieved(retrieved_count=2),
            web_input=_web(
                status="ok",
                results_count=2,
                sources=[_web_source(used_in_prompt=True, used_content_kind="quote", content_used="used")],
            ),
        )

        self.assertEqual(payload["source_priority"][-1], ["stimmung"])
        flattened = _flatten(payload)
        self.assertLess(flattened.index("temps"), flattened.index("stimmung"))
        self.assertLess(flattened.index("memoire"), flattened.index("stimmung"))
        self.assertLess(flattened.index("web"), flattened.index("stimmung"))

    def test_build_source_priority_output_invariants_hold(self) -> None:
        payload = source_priority.build_source_priority(
            user_turn_input=_user_turn(
                gesture="regulation",
                provenances=["web", "dialogue_trace"],
                proof_types=["factuelle"],
                temporal_scope="prospective",
            ),
            time_input=_time(),
            memory_retrieved=_memory_retrieved(retrieved_count=1),
            recent_context_input=_recent_context(message_count=1),
            identity_input=_identity(static=True, dynamic_count=1),
            summary_input=_summary(available=True),
            web_input=_web(status="ok", results_count=4),
        )

        flattened = _flatten(payload)
        self.assertCountEqual(flattened, list(source_priority.SOURCE_FAMILIES))
        self.assertEqual(len(flattened), len(set(flattened)))


if __name__ == "__main__":
    unittest.main()
