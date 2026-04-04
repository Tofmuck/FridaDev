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
