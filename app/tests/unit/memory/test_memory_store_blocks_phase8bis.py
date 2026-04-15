from __future__ import annotations

import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_arbiter_audit
from memory import memory_context_read
from memory import hermeneutics_policy
from memory import memory_identity_dynamics
from memory import memory_identity_write
from memory import memory_store_infra
from memory import memory_traces_summaries


class _NoopLogger:
    def debug(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def warning(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


class MemoryStoreInfraBlockTests(unittest.TestCase):
    def test_runtime_embedding_value_falls_back_to_env_seed_when_runtime_value_missing(self) -> None:
        runtime_settings_module = SimpleNamespace(
            get_embedding_settings=lambda: SimpleNamespace(payload={"top_k": {}}),
            build_env_seed_bundle=lambda section: SimpleNamespace(
                payload={"top_k": {"value": 17}, "section": section}
            ),
        )

        top_k = memory_store_infra.runtime_embedding_value(
            "top_k",
            runtime_settings_module=runtime_settings_module,
        )

        self.assertEqual(top_k, 17)


class MemoryTracesSummariesBlockTests(unittest.TestCase):
    def test_enrich_traces_with_summaries_caches_lookups_for_duplicate_summary_id(self) -> None:
        calls = {"count": 0}

        def fake_get_summary_for_trace(_trace: dict[str, Any]) -> dict[str, Any]:
            calls["count"] += 1
            return {"id": "sum-1", "content": "summary"}

        traces = [
            {"conversation_id": "conv-a", "timestamp": "2026-03-26T10:00:00Z", "summary_id": "sum-1"},
            {"conversation_id": "conv-a", "timestamp": "2026-03-26T10:01:00Z", "summary_id": "sum-1"},
        ]

        enriched = memory_traces_summaries.enrich_traces_with_summaries(
            traces,
            get_summary_for_trace_fn=fake_get_summary_for_trace,
        )

        self.assertEqual(calls["count"], 1)
        self.assertEqual(enriched[0]["parent_summary"]["id"], "sum-1")
        self.assertEqual(enriched[1]["parent_summary"]["id"], "sum-1")

    def test_save_new_traces_skips_interrupted_assistant_markers_even_on_later_passes(self) -> None:
        observed_inserts: list[tuple[Any, ...]] = []
        original_trace_exists = memory_traces_summaries._trace_exists_for_message

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, query: str, params: tuple[Any, ...]) -> None:
                if "INSERT INTO traces" in query:
                    observed_inserts.append(params)

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        conversation = {
            "id": "conv-interrupted-traces",
            "messages": [
                {"role": "user", "content": "Salut", "timestamp": "2026-03-28T11:59:30Z"},
                {
                    "role": "assistant",
                    "content": "",
                    "timestamp": "2026-03-28T11:59:40Z",
                    "meta": {
                        "assistant_turn": {
                            "status": "interrupted",
                            "error_code": "upstream_error",
                        }
                    },
                },
                {"role": "assistant", "content": "Réponse complète", "timestamp": "2026-03-28T12:00:00Z"},
            ],
        }

        memory_traces_summaries._trace_exists_for_message = lambda *_args, **_kwargs: False
        try:
            memory_traces_summaries.save_new_traces(
                conversation,
                conn_factory=lambda: FakeConn(),
                embed_fn=lambda *_args, **_kwargs: [0.1, 0.2, 0.3],
                logger=_NoopLogger(),
            )
            memory_traces_summaries.save_new_traces(
                conversation,
                conn_factory=lambda: FakeConn(),
                embed_fn=lambda *_args, **_kwargs: [0.1, 0.2, 0.3],
                logger=_NoopLogger(),
            )
        finally:
            memory_traces_summaries._trace_exists_for_message = original_trace_exists

        self.assertEqual(
            [(params[1], params[2]) for params in observed_inserts],
            [
                ("user", "Salut"),
                ("assistant", "Réponse complète"),
            ],
        )


class MemoryContextReadBlockTests(unittest.TestCase):
    def test_get_recent_context_hints_deduplicates_content_norm_and_respects_max_items(self) -> None:
        observed = {"params": None}

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, params: tuple[Any, ...]) -> None:
                observed["params"] = params

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        "conv-1",
                        "Indice A",
                        "indice-a",
                        datetime(2026, 3, 26, 10, 0, tzinfo=timezone.utc),
                        0.9,
                        "situation",
                        "episodic",
                        "self_description",
                        0.8,
                    ),
                    (
                        "conv-2",
                        "Indice A bis",
                        "indice-a",
                        datetime(2026, 3, 26, 9, 0, tzinfo=timezone.utc),
                        0.8,
                        "situation",
                        "episodic",
                        "self_description",
                        0.7,
                    ),
                    (
                        "conv-3",
                        "Indice B",
                        "indice-b",
                        datetime(2026, 3, 26, 8, 0, tzinfo=timezone.utc),
                        0.7,
                        "situation",
                        "episodic",
                        "self_description",
                        0.6,
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

        hints = memory_context_read.get_recent_context_hints(
            max_items=2,
            max_age_days=7,
            min_confidence=0.3,
            conn_factory=lambda: FakeConn(),
            default_max_items=5,
            default_max_age_days=30,
            default_min_confidence=0.2,
            logger=_NoopLogger(),
        )

        self.assertEqual(len(hints), 2)
        self.assertEqual([hint["content"] for hint in hints], ["Indice A", "Indice B"])
        self.assertEqual(observed["params"][-1], 16)  # fetch_limit = max(5, max_items * 8)


class MemoryArbiterAuditBlockTests(unittest.TestCase):
    def test_record_arbiter_decisions_uses_effective_model_fallback(self) -> None:
        observed = {"models": [], "committed": False}

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, params: tuple[Any, ...]) -> None:
                observed["models"].append(params[11])

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed["committed"] = True

        memory_arbiter_audit.record_arbiter_decisions(
            "conv-audit",
            traces=[{"role": "assistant", "content": "candidate", "timestamp": "2026-03-26T00:00:00Z", "score": 0.4}],
            decisions=[{"candidate_id": "0", "keep": True, "semantic_relevance": 0.4, "contextual_gain": 0.3}],
            effective_model="openrouter/arbiter-runtime-model",
            conn_factory=lambda: FakeConn(),
            trace_float_fn=lambda value: float(value or 0.0),
            logger=_NoopLogger(),
        )

        self.assertEqual(observed["models"], ["openrouter/arbiter-runtime-model"])
        self.assertTrue(observed["committed"])


class MemoryIdentityWriteBlockTests(unittest.TestCase):
    def test_record_identity_evidence_persists_only_valid_entries(self) -> None:
        observed = {"inserts": 0, "params": [], "committed": False}

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, params: tuple[Any, ...]) -> None:
                observed["inserts"] += 1
                observed["params"].append(params)

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                observed["committed"] = True

        memory_identity_write.record_identity_evidence(
            "conv-write",
            entries=[
                {"subject": "system", "content": "skip"},
                {"subject": "user", "content": ""},
                {"subject": "user", "content": "Alpha", "confidence": 0.8, "status": "accepted"},
            ],
            source_trace_id="trace-1",
            conn_factory=lambda: FakeConn(),
            normalize_identity_content_fn=lambda text: text.strip().lower(),
            trace_float_fn=lambda value: float(value or 0.0),
            logger=_NoopLogger(),
        )

        self.assertEqual(observed["inserts"], 1)
        self.assertEqual(observed["params"][0][3], "alpha")
        self.assertTrue(observed["committed"])


class MemoryIdentityDynamicsBlockTests(unittest.TestCase):
    def test_preview_identity_entries_merges_llm_and_policy_reasons(self) -> None:
        policy_module = SimpleNamespace(
            should_accept_identity=lambda _entry, **_kwargs: {
                "status": "accepted",
                "reason": "policy-accepted",
            }
        )
        config_module = SimpleNamespace(
            IDENTITY_MIN_CONFIDENCE=0.6,
            IDENTITY_DEFER_MIN_CONFIDENCE=0.3,
        )

        processed = memory_identity_dynamics.preview_identity_entries(
            entries=[
                {"subject": "user", "content": "I am a researcher", "confidence": 0.9, "reason": "llm-signal"},
                {"subject": "assistant", "content": "skip-me"},
            ],
            policy_module=policy_module,
            config_module=config_module,
            trace_float_fn=lambda value: float(value or 0.0),
        )

        self.assertEqual(len(processed), 1)
        self.assertEqual(processed[0]["status"], "accepted")
        self.assertEqual(processed[0]["confidence"], 0.9)
        self.assertIn("llm:llm-signal", processed[0]["reason"])
        self.assertIn("policy:policy-accepted", processed[0]["reason"])

    def test_detect_and_record_conflicts_reuses_current_embedding_once_for_multiple_candidates(self) -> None:
        embed_calls: list[tuple[str, str]] = []
        similarity_pairs: list[tuple[tuple[float, ...], tuple[float, ...]]] = []

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchone(self) -> tuple[Any, ...]:
                return (
                    "11111111-1111-1111-1111-111111111111",
                    "llm",
                    "Current identity",
                    "current identity",
                    "accepted",
                    datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc),
                    "none",
                )

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        "22222222-2222-2222-2222-222222222222",
                        "Candidate one",
                        "candidate one",
                        "accepted",
                        datetime(2026, 4, 8, 9, 59, tzinfo=timezone.utc),
                        "none",
                    ),
                    (
                        "33333333-3333-3333-3333-333333333333",
                        "Candidate two",
                        "candidate two",
                        "accepted",
                        datetime(2026, 4, 8, 9, 58, tzinfo=timezone.utc),
                        "none",
                    ),
                    (
                        "44444444-4444-4444-4444-444444444444",
                        "Candidate three",
                        "candidate three",
                        "accepted",
                        datetime(2026, 4, 8, 9, 57, tzinfo=timezone.utc),
                        "none",
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_embed_identity_conflict_vector(text: str, *, purpose: str) -> list[float]:
            embed_calls.append((purpose, text))
            if purpose == "identity_conflict_current":
                return [1.0, 0.0]
            return [0.0, 1.0]

        def fake_embedding_similarity_safe(
            vec_a: list[float] | None,
            vec_b: list[float] | None,
        ) -> float | None:
            if vec_a is None or vec_b is None:
                return None
            similarity_pairs.append((tuple(vec_a), tuple(vec_b)))
            return 0.42

        policy_module = SimpleNamespace(
            is_contradictory=lambda *_args, **_kwargs: (False, 0.0, "no_conflict"),
            conflict_resolution_action=lambda _confidence: "no_op",
        )

        memory_identity_dynamics.detect_and_record_conflicts(
            "11111111-1111-1111-1111-111111111111",
            conn_factory=lambda: FakeConn(),
            policy_module=policy_module,
            logger=_NoopLogger(),
            conflict_already_open_fn=lambda *_args, **_kwargs: False,
            embed_identity_conflict_vector_fn=fake_embed_identity_conflict_vector,
            embedding_similarity_safe_fn=fake_embedding_similarity_safe,
            insert_conflict_fn=lambda *_args, **_kwargs: None,
        )

        purposes = [purpose for purpose, _text in embed_calls]
        self.assertEqual(purposes.count("identity_conflict_current"), 1)
        self.assertEqual(purposes.count("identity_conflict_candidate"), 3)
        self.assertEqual(
            purposes,
            [
                "identity_conflict_current",
                "identity_conflict_candidate",
                "identity_conflict_candidate",
                "identity_conflict_candidate",
            ],
        )
        self.assertEqual(len(similarity_pairs), 3)

    def test_detect_and_record_conflicts_still_records_conflict_with_reused_embeddings(self) -> None:
        inserted_conflicts: list[tuple[str, str, float, str]] = []
        embed_calls: list[str] = []

        class FakeCursor:
            def __enter__(self) -> "FakeCursor":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def execute(self, _query: str, _params: tuple[Any, ...]) -> None:
                return None

            def fetchone(self) -> tuple[Any, ...]:
                return (
                    "11111111-1111-1111-1111-111111111111",
                    "llm",
                    "Current identity",
                    "current identity",
                    "accepted",
                    datetime(2026, 4, 8, 10, 0, tzinfo=timezone.utc),
                    "none",
                )

            def fetchall(self) -> list[tuple[Any, ...]]:
                return [
                    (
                        "22222222-2222-2222-2222-222222222222",
                        "Conflicting candidate",
                        "conflicting candidate",
                        "accepted",
                        datetime(2026, 4, 8, 9, 59, tzinfo=timezone.utc),
                        "none",
                    ),
                    (
                        "33333333-3333-3333-3333-333333333333",
                        "Compatible candidate",
                        "compatible candidate",
                        "accepted",
                        datetime(2026, 4, 8, 9, 58, tzinfo=timezone.utc),
                        "none",
                    ),
                ]

        class FakeConn:
            def __enter__(self) -> "FakeConn":
                return self

            def __exit__(self, exc_type, exc, tb) -> bool:
                return False

            def cursor(self) -> FakeCursor:
                return FakeCursor()

            def commit(self) -> None:
                return None

        def fake_embed_identity_conflict_vector(text: str, *, purpose: str) -> list[float]:
            embed_calls.append(purpose)
            vectors = {
                "Current identity": [1.0, 0.0],
                "Conflicting candidate": [1.0, 0.0],
                "Compatible candidate": [0.0, 1.0],
            }
            return vectors[text]

        def fake_insert_conflict(
            _cur: Any,
            id_a: str,
            id_b: str,
            confidence_conflict: float,
            reason: str,
        ) -> None:
            inserted_conflicts.append((id_a, id_b, confidence_conflict, reason))

        policy_module = SimpleNamespace(
            is_contradictory=lambda _me, _other, *, semantic_similarity: (
                semantic_similarity >= 0.8,
                semantic_similarity,
                "semantic_conflict",
            ),
            conflict_resolution_action=lambda _confidence: "no_op",
        )

        memory_identity_dynamics.detect_and_record_conflicts(
            "11111111-1111-1111-1111-111111111111",
            conn_factory=lambda: FakeConn(),
            policy_module=policy_module,
            logger=_NoopLogger(),
            conflict_already_open_fn=lambda *_args, **_kwargs: False,
            embed_identity_conflict_vector_fn=fake_embed_identity_conflict_vector,
            embedding_similarity_safe_fn=lambda vec_a, vec_b: memory_identity_dynamics._embedding_similarity_safe(
                vec_a,
                vec_b,
                cosine_similarity_fn=memory_identity_dynamics._cosine_similarity,
                logger=_NoopLogger(),
            ),
            insert_conflict_fn=fake_insert_conflict,
        )

        self.assertEqual(embed_calls.count("identity_conflict_current"), 1)
        self.assertEqual(embed_calls.count("identity_conflict_candidate"), 2)
        self.assertEqual(len(inserted_conflicts), 1)
        self.assertEqual(
            inserted_conflicts[0],
            (
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-2222-2222-222222222222",
                1.0,
                "semantic_conflict",
            ),
        )


class HermeneuticsPolicyWebReadingGuardTests(unittest.TestCase):
    def test_filter_unsupported_web_reading_identities_rejects_direct_claim_for_snippet_fallback(self) -> None:
        kept, filtered = hermeneutics_policy.filter_unsupported_web_reading_identities(
            [
                {
                    'subject': 'llm',
                    'content': 'Claims to have the linked article open and read it',
                }
            ],
            web_input={'read_state': 'page_not_read_snippet_fallback'},
        )

        self.assertEqual(kept, [])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['subject'], 'llm')
        self.assertEqual(
            filtered[0]['reason'],
            'web_reading_claim_unsupported_for_page_not_read_snippet_fallback',
        )

    def test_filter_unsupported_web_reading_identities_keeps_prudent_limitation_statement(self) -> None:
        prudent_entry = {
            'subject': 'llm',
            'content': "Frida n'a pas accès au contenu complet d'un article via un lien direct dans ce contexte",
        }

        kept, filtered = hermeneutics_policy.filter_unsupported_web_reading_identities(
            [prudent_entry],
            web_input={'read_state': 'page_not_read_crawl_empty'},
        )

        self.assertEqual(kept, [prudent_entry])
        self.assertEqual(filtered, [])

    def test_filter_unsupported_web_reading_identities_blocks_full_read_claim_when_page_partially_read(self) -> None:
        kept, filtered = hermeneutics_policy.filter_unsupported_web_reading_identities(
            [
                {
                    'subject': 'llm',
                    'content': 'Claims to have read the full article in detail',
                }
            ],
            web_input={'read_state': 'page_partially_read'},
        )

        self.assertEqual(kept, [])
        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0]['reason'], 'web_reading_claim_requires_partial_nuance')


if __name__ == "__main__":
    unittest.main()
