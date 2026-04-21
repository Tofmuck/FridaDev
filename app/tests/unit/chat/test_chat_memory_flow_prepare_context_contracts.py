from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import chat_memory_flow


def _event_payloads(events, name: str):
    return [payload for event, payload in events if event == name]


def _trace(
    trace_id: str,
    *,
    conversation_id: str,
    role: str,
    content: str,
    timestamp: str,
    score: float = 0.8,
    summary_id: str | None = None,
    retrieval_score: float | None = None,
    semantic_score: float | None = None,
    source_kind: str | None = None,
    source_lane: str | None = None,
    start_ts: str | None = None,
    end_ts: str | None = None,
):
    payload = {
        "trace_id": trace_id,
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        "timestamp": timestamp,
        "summary_id": summary_id,
        "score": score,
    }
    if retrieval_score is not None:
        payload["retrieval_score"] = retrieval_score
    if semantic_score is not None:
        payload["semantic_score"] = semantic_score
    if source_kind is not None:
        payload["source_kind"] = source_kind
    if source_lane is not None:
        payload["source_lane"] = source_lane
    if start_ts is not None:
        payload["start_ts"] = start_ts
    if end_ts is not None:
        payload["end_ts"] = end_ts
    return payload


class ChatMemoryFlowPrepareContextContractsTests(unittest.TestCase):
    def test_prepare_memory_context_mode_off_keeps_raw_traces_without_arbiter(self) -> None:
        events = []
        observed = {"record_calls": 0, "enrich_called_with": None}
        raw_traces = [
            _trace(
                "r1",
                conversation_id="conv-source-a",
                role="user",
                content="Je suis Christophe Muck",
                timestamp="2026-04-10T09:00:00Z",
                score=0.91,
            )
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="off",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-off",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: observed.update({"record_calls": observed["record_calls"] + 1}),
            enrich_traces_with_summaries=lambda traces: observed.update({"enrich_called_with": list(traces)})
            or [{**trace, "enriched": True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("arbiter should not run in off mode")
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )
        mode, memory_traces, context_hints = prepared

        self.assertEqual(mode, "off")
        self.assertEqual(len(memory_traces), 1)
        self.assertEqual(memory_traces[0]["trace_id"], "r1")
        self.assertTrue(memory_traces[0]["enriched"])
        self.assertTrue(memory_traces[0]["candidate_id"].startswith("cand-"))
        self.assertEqual(context_hints, [])
        self.assertEqual(observed["record_calls"], 0)
        self.assertEqual(observed["enrich_called_with"], raw_traces)
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["source"], "pre_arbiter_basket_mode_off")
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["selected"], 1)
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["filtered"], 0)
        self.assertEqual(_event_payloads(events, "memory_arbitrated"), [])
        self.assertEqual(prepared.memory_arbitration["status"], "skipped")
        self.assertEqual(prepared.memory_arbitration["reason_code"], "mode_off")
        self.assertEqual(prepared.memory_arbitration["raw_candidates_count"], 1)
        self.assertEqual(prepared.memory_arbitration["basket_candidates_count"], 1)
        self.assertEqual(
            prepared.memory_arbitration["injected_candidate_ids"],
            [memory_traces[0]["candidate_id"]],
        )
        self.assertEqual(prepared.memory_arbitration["decisions"], [])

    def test_prepare_memory_context_exposes_canonical_memory_retrieved_without_arbiter_fields(self) -> None:
        events = []
        raw_traces = [
            {
                "conversation_id": "conv-source-a",
                "role": "user",
                "content": "Je cours le matin",
                "timestamp": "2026-03-01T08:00:00Z",
                "summary_id": "sum-1",
                "score": 0.91,
            },
            {
                "conversation_id": "conv-source-b",
                "role": "assistant",
                "content": "Tu avais parle de natation",
                "timestamp": "2026-03-02T09:15:00Z",
                "summary_id": None,
                "score": 0.73,
            },
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-canonical",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            _runtime_embedding_value=lambda field: 9 if field == "top_k" else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [
                {
                    **trace,
                    "parent_summary": (
                        {
                            "id": "sum-1",
                            "conversation_id": "conv-source-a",
                            "start_ts": "2026-03-01T07:00:00Z",
                            "end_ts": "2026-03-01T08:30:00Z",
                            "content": "Routine sportive du matin",
                        }
                        if trace.get("summary_id") == "sum-1"
                        else None
                    ),
                }
                for trace in traces
            ],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda _traces, _recent_turns: (
                [raw_traces[0]],
                [{"candidate_id": "0", "keep": True, "reason": "best_match"}],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )
        mode, memory_traces, context_hints = prepared

        self.assertEqual(mode, "shadow")
        self.assertEqual(len(memory_traces), 2)
        self.assertEqual(context_hints, [])

        memory_retrieved = prepared.memory_retrieved
        self.assertEqual(memory_retrieved["schema_version"], "v1")
        self.assertEqual(memory_retrieved["retrieval_query"], "bonjour")
        self.assertEqual(memory_retrieved["top_k_requested"], 9)
        self.assertEqual(memory_retrieved["retrieved_count"], 2)
        self.assertEqual(len(memory_retrieved["traces"]), 2)

        candidate_ids = [trace["candidate_id"] for trace in memory_retrieved["traces"]]
        self.assertEqual(len(candidate_ids), len(set(candidate_ids)))

        first_trace = memory_retrieved["traces"][0]
        second_trace = memory_retrieved["traces"][1]
        self.assertEqual(first_trace["conversation_id"], "conv-source-a")
        self.assertEqual(first_trace["role"], "user")
        self.assertEqual(first_trace["content"], "Je cours le matin")
        self.assertEqual(first_trace["timestamp_iso"], "2026-03-01T08:00:00Z")
        self.assertEqual(first_trace["retrieval_score"], 0.91)
        self.assertEqual(first_trace["summary_id"], "sum-1")
        self.assertEqual(first_trace["parent_summary"]["id"], "sum-1")
        self.assertEqual(first_trace["parent_summary"]["content"], "Routine sportive du matin")
        self.assertNotIn("keep", first_trace)
        self.assertNotIn("reason", first_trace)

        self.assertEqual(second_trace["conversation_id"], "conv-source-b")
        self.assertIsNone(second_trace["parent_summary"])
        self.assertNotIn("semantic_relevance", second_trace)
        self.assertNotIn("decision_source", second_trace)

    def test_prepare_memory_context_prefers_retrieve_for_arbiter_and_keeps_memory_retrieved_public(self) -> None:
        observed = {"arbiter_traces": None}
        internal_traces = [
            {
                "conversation_id": "conv-source-a",
                "role": "user",
                "content": "codex-8192-live-1775296899",
                "timestamp": "2026-04-10T08:00:00Z",
                "summary_id": "sum-1",
                "score": 0.98,
                "retrieval_score": 0.98,
                "semantic_score": 0.0,
            }
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-internal-retrieval",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: (_ for _ in ()).throw(
                AssertionError("public retrieve should not be used when retrieve_for_arbiter exists")
            ),
            retrieve_for_arbiter=lambda _msg: list(internal_traces),
            _runtime_embedding_value=lambda field: 5 if field == "top_k" else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: list(traces),
            get_recent_context_hints=lambda **_kwargs: [],
        )

        def fake_filter(traces, _recent_turns):
            observed["arbiter_traces"] = list(traces)
            return [], [
                {
                    "candidate_id": traces[0]["candidate_id"],
                    "keep": False,
                    "semantic_relevance": 0.0,
                    "contextual_gain": 0.0,
                    "redundant_with_recent": False,
                    "reason": "no_semantic_signal",
                    "decision_source": "fallback",
                    "model": "openai/gpt-5.4-mini",
                }
            ]

        arbiter_module = SimpleNamespace(filter_traces_with_diagnostics=fake_filter)
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertIsNotNone(observed["arbiter_traces"])
        self.assertEqual(observed["arbiter_traces"][0]["retrieval_score"], 0.98)
        self.assertEqual(observed["arbiter_traces"][0]["semantic_score"], 0.0)
        self.assertEqual(observed["arbiter_traces"][0]["source_lane"], "global")
        self.assertTrue(observed["arbiter_traces"][0]["candidate_id"].startswith("cand-"))
        self.assertEqual(prepared.memory_retrieved["traces"][0]["retrieval_score"], 0.98)
        self.assertNotIn("semantic_score", prepared.memory_retrieved["traces"][0])

    def test_prepare_memory_context_exposes_canonical_memory_arbitration_with_stable_and_legacy_links(self) -> None:
        raw_traces = [
            {
                "conversation_id": "conv-source-a",
                "role": "user",
                "content": "Je cours le matin",
                "timestamp": "2026-03-01T08:00:00Z",
                "summary_id": "sum-1",
                "score": 0.91,
            },
            {
                "conversation_id": "conv-source-b",
                "role": "assistant",
                "content": "Tu avais parle de natation",
                "timestamp": "2026-03-02T09:15:00Z",
                "summary_id": None,
                "score": 0.73,
            },
        ]
        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-arbitration",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: list(traces),
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[0]],
                [
                    {
                        "candidate_id": traces[0]["candidate_id"],
                        "keep": True,
                        "semantic_relevance": 0.94,
                        "contextual_gain": 0.81,
                        "redundant_with_recent": False,
                        "reason": "best_match",
                        "decision_source": "llm",
                        "model": "openrouter/arbiter-test",
                    },
                    {
                        "candidate_id": traces[1]["candidate_id"],
                        "keep": False,
                        "semantic_relevance": 0.33,
                        "contextual_gain": 0.11,
                        "redundant_with_recent": True,
                        "reason": "redundant",
                        "decision_source": "llm",
                        "model": "openrouter/arbiter-test",
                    },
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        memory_retrieved = prepared.memory_retrieved
        memory_arbitration = prepared.memory_arbitration
        candidate_ids = [trace["candidate_id"] for trace in memory_retrieved["traces"]]

        self.assertEqual(memory_arbitration["schema_version"], "v1")
        self.assertEqual(memory_arbitration["status"], "available")
        self.assertIsNone(memory_arbitration["reason_code"])
        self.assertEqual(memory_arbitration["raw_candidates_count"], 2)
        self.assertEqual(memory_arbitration["basket_candidates_count"], 2)
        self.assertEqual(memory_arbitration["decisions_count"], 2)
        self.assertEqual(memory_arbitration["kept_count"], 1)
        self.assertEqual(memory_arbitration["rejected_count"], 1)
        self.assertEqual(memory_arbitration["injected_candidate_ids"], candidate_ids[:2])

        first_decision = memory_arbitration["decisions"][0]
        second_decision = memory_arbitration["decisions"][1]
        self.assertEqual(first_decision["candidate_id"], memory_retrieved["traces"][0]["candidate_id"])
        self.assertEqual(first_decision["retrieved_candidate_id"], memory_retrieved["traces"][0]["candidate_id"])
        self.assertIsNone(first_decision["legacy_candidate_id"])
        self.assertIsNone(first_decision["legacy_candidate_index"])
        self.assertTrue(first_decision["keep"])
        self.assertEqual(first_decision["semantic_relevance"], 0.94)
        self.assertEqual(first_decision["contextual_gain"], 0.81)
        self.assertFalse(first_decision["redundant_with_recent"])
        self.assertEqual(first_decision["reason"], "best_match")
        self.assertEqual(first_decision["decision_source"], "llm")
        self.assertEqual(first_decision["model"], "openrouter/arbiter-test")
        self.assertEqual(first_decision["source_candidate_ids"], [memory_retrieved["traces"][0]["candidate_id"]])
        self.assertNotIn("content", first_decision)

        self.assertEqual(second_decision["candidate_id"], memory_retrieved["traces"][1]["candidate_id"])
        self.assertEqual(second_decision["retrieved_candidate_id"], memory_retrieved["traces"][1]["candidate_id"])
        self.assertIsNone(second_decision["legacy_candidate_id"])
        self.assertIsNone(second_decision["legacy_candidate_index"])
        self.assertFalse(second_decision["keep"])
        self.assertTrue(second_decision["redundant_with_recent"])

    def test_prepare_memory_context_keeps_summary_candidate_ids_stable_through_basket_and_injection(self) -> None:
        raw_traces = [
            _trace(
                "summary-1",
                conversation_id="conv-prefs",
                role="summary",
                content="Preferences durables: reponses courtes et ton direct.",
                timestamp="2026-04-10T09:10:00Z",
                score=0.92,
                summary_id="sum-prefs",
                retrieval_score=0.92,
                semantic_score=0.92,
                source_kind="summary",
                source_lane="summaries",
                start_ts="2026-04-10T09:00:00Z",
                end_ts="2026-04-10T09:10:00Z",
            ),
            _trace(
                "trace-1",
                conversation_id="conv-prefs",
                role="user",
                content="Tu preferes les reponses courtes.",
                timestamp="2026-04-10T09:02:00Z",
                score=0.82,
                summary_id="sum-prefs",
                retrieval_score=0.82,
                semantic_score=0.82,
            ),
            _trace(
                "trace-2",
                conversation_id="conv-prefs",
                role="user",
                content="Tu veux un ton direct.",
                timestamp="2026-04-10T09:05:00Z",
                score=0.81,
                summary_id="sum-prefs",
                retrieval_score=0.81,
                semantic_score=0.81,
            ),
        ]
        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="enforced_all",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-summary-lane",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve_for_arbiter=lambda _msg: list(raw_traces),
            _runtime_embedding_value=lambda field: 5 if field == "top_k" else None,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [
                {
                    **trace,
                    "parent_summary": None if trace.get("role") == "summary" else {
                        "id": "sum-prefs",
                        "conversation_id": "conv-prefs",
                        "start_ts": "2026-04-10T09:00:00Z",
                        "end_ts": "2026-04-10T09:10:00Z",
                        "content": "Preferences utilisateur durables",
                    },
                }
                for trace in traces
            ],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[0]],
                [
                    {
                        "candidate_id": traces[0]["candidate_id"],
                        "keep": True,
                        "semantic_relevance": 0.92,
                        "contextual_gain": 0.9,
                        "redundant_with_recent": False,
                        "reason": "summary_wins",
                        "decision_source": "fallback",
                        "model": "tests",
                    }
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda *_args, **_kwargs: None)

        prepared = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="preferences durables",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(len(prepared.memory_traces), 1)
        self.assertEqual(prepared.memory_traces[0]["candidate_id"], "summary:sum-prefs")
        self.assertEqual(prepared.memory_traces[0]["role"], "summary")
        self.assertIsNone(prepared.memory_traces[0]["parent_summary"])
        self.assertEqual(prepared.memory_arbitration["injected_candidate_ids"], ["summary:sum-prefs"])
        self.assertEqual(prepared.memory_arbitration["basket_candidates"][0]["candidate_id"], "summary:sum-prefs")
        self.assertEqual(prepared.memory_arbitration["basket_candidates"][0]["source_kind"], "summary")
        self.assertEqual(
            set(prepared.memory_arbitration["basket_candidates"][0]["source_candidate_ids"]),
            {
                "summary:sum-prefs",
                prepared.memory_retrieved["traces"][1]["candidate_id"],
                prepared.memory_retrieved["traces"][2]["candidate_id"],
            },
        )

    def test_prepare_memory_context_mode_shadow_uses_pre_arbiter_basket_for_prompt_side(self) -> None:
        events = []
        observed = {
            "arbiter_recent_turns": None,
            "record_args": None,
            "enrich_called_with": None,
        }
        raw_traces = [
            _trace(
                "r1",
                conversation_id="conv-shadow-a",
                role="user",
                content="Je suis Christophe Muck",
                timestamp="2026-04-10T09:00:00Z",
                score=0.91,
            ),
            _trace(
                "r2",
                conversation_id="conv-shadow-b",
                role="assistant",
                content="Nous travaillons sur FridaDev",
                timestamp="2026-04-10T09:01:00Z",
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-shadow",
            "messages": [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "hello"},
                {"role": "assistant", "content": "world"},
            ],
        }

        def fake_filter(traces, recent_turns):
            observed["arbiter_recent_turns"] = list(recent_turns)
            decisions = [
                {
                    "candidate_id": traces[0]["candidate_id"],
                    "keep": False,
                    "semantic_relevance": 0.1,
                    "contextual_gain": 0.1,
                    "redundant_with_recent": False,
                    "reason": "shadow",
                    "decision_source": "llm",
                    "model": "openrouter/arbiter-test",
                },
                {
                    "candidate_id": traces[1]["candidate_id"],
                    "keep": True,
                    "semantic_relevance": 0.9,
                    "contextual_gain": 0.8,
                    "redundant_with_recent": False,
                    "reason": "keep",
                    "decision_source": "llm",
                    "model": "openrouter/arbiter-test",
                },
            ]
            return [traces[1]], decisions

        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda conversation_id, traces, decisions: observed.update(
                {"record_args": (conversation_id, list(traces), list(decisions))}
            ),
            enrich_traces_with_summaries=lambda traces: observed.update({"enrich_called_with": list(traces)})
            or [{**trace, "enriched": True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(filter_traces_with_diagnostics=fake_filter)
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        mode, memory_traces, _context_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(mode, "shadow")
        self.assertEqual([trace["trace_id"] for trace in memory_traces], ["r1", "r2"])
        self.assertTrue(all(trace["candidate_id"].startswith("cand-") for trace in memory_traces))
        self.assertEqual(observed["record_args"][0], "conv-memory-shadow")
        self.assertEqual(
            [trace["trace_id"] for trace in observed["record_args"][1]],
            ["r1", "r2"],
        )
        self.assertEqual(
            [decision["candidate_id"] for decision in observed["record_args"][2]],
            [trace["candidate_id"] for trace in observed["record_args"][1]],
        )
        self.assertEqual(observed["enrich_called_with"], raw_traces)
        self.assertEqual(
            [entry["role"] for entry in observed["arbiter_recent_turns"]],
            ["user", "assistant"],
        )
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["source"], "pre_arbiter_basket_shadow")
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["selected"], 2)
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["filtered"], 1)
        self.assertEqual(_event_payloads(events, "memory_arbitrated")[0]["decisions"], 2)

    def test_prepare_memory_context_mode_enforced_all_uses_filtered_traces(self) -> None:
        events = []
        raw_traces = [
            _trace(
                "r1",
                conversation_id="conv-enforced-a",
                role="user",
                content="Je suis Christophe Muck",
                timestamp="2026-04-10T09:00:00Z",
                score=0.91,
            ),
            _trace(
                "r2",
                conversation_id="conv-enforced-b",
                role="assistant",
                content="Nous travaillons sur FridaDev",
                timestamp="2026-04-10T09:01:00Z",
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="enforced_all",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-enforced-all",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            record_arbiter_decisions=lambda *_args, **_kwargs: None,
            enrich_traces_with_summaries=lambda traces: [{**trace, "enriched": True} for trace in traces],
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda traces, _recent_turns: (
                [traces[1]],
                [
                    {
                        "candidate_id": traces[0]["candidate_id"],
                        "keep": False,
                        "semantic_relevance": 0.2,
                        "contextual_gain": 0.1,
                        "redundant_with_recent": False,
                        "reason": "reject",
                        "decision_source": "llm",
                        "model": "openrouter/arbiter-test",
                    },
                    {
                        "candidate_id": traces[1]["candidate_id"],
                        "keep": True,
                        "semantic_relevance": 0.9,
                        "contextual_gain": 0.8,
                        "redundant_with_recent": False,
                        "reason": "keep",
                        "decision_source": "llm",
                        "model": "openrouter/arbiter-test",
                    },
                ],
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        mode, memory_traces, _context_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(mode, "enforced_all")
        self.assertEqual([trace["trace_id"] for trace in memory_traces], ["r2"])
        self.assertTrue(memory_traces[0]["candidate_id"].startswith("cand-"))
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["source"], "arbiter_enforced")
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["selected"], 1)
        self.assertEqual(_event_payloads(events, "memory_mode_apply")[0]["filtered"], 1)


if __name__ == "__main__":
    unittest.main()
