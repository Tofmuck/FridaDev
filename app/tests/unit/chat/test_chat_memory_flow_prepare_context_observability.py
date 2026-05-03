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


class ChatMemoryFlowPrepareContextObservabilityTests(unittest.TestCase):
    def test_prepare_memory_context_logs_context_hints_when_present(self) -> None:
        events = []
        context_hints = [{"identity_id": "id-1"}, {"identity_id": "id-2"}]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="off",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-hints",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: [],
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: context_hints,
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: ([], []),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        _mode, memory_traces, returned_hints = chat_memory_flow.prepare_memory_context(
            conversation=conversation,
            user_msg="bonjour",
            config_module=config_module,
            memory_store_module=memory_store_module,
            arbiter_module=arbiter_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(memory_traces, [])
        self.assertEqual(returned_hints, context_hints)
        self.assertEqual(_event_payloads(events, "context_hints_selected")[0]["count"], 2)

    def test_prepare_memory_context_emits_arbiter_skipped_when_no_raw_traces(self) -> None:
        events = []
        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        state_events: list[tuple[str, dict[str, object]]] = []

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-empty",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: [],
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("arbiter should not run with empty traces")
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        original_set_state = chat_memory_flow.chat_turn_logger.set_state
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        chat_memory_flow.chat_turn_logger.set_state = (
            lambda key, value: state_events.append((key, dict(value))) or None
        )
        try:
            prepared = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg="bonjour",
                config_module=config_module,
                memory_store_module=memory_store_module,
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
            )
            _mode, memory_traces, context_hints = prepared
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch
            chat_memory_flow.chat_turn_logger.set_state = original_set_state

        self.assertEqual(memory_traces, [])
        self.assertEqual(context_hints, [])
        self.assertEqual(prepared.memory_retrieved["status"], "ok")
        self.assertEqual(prepared.memory_retrieved["reason_code"], "no_data")
        self.assertEqual(prepared.memory_arbitration["reason_code"], "no_data")
        self.assertEqual(
            state_events,
            [
                (
                    "memory_retrieval",
                    {
                        "status": "ok",
                        "reason_code": "no_data",
                        "error_code": None,
                        "error_class": None,
                        "top_k_requested": None,
                        "top_k_returned": 0,
                    },
                )
            ],
        )
        self.assertTrue(chat_events)
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, "arbiter")
        self.assertEqual(kwargs["status"], "skipped")
        self.assertEqual(kwargs["reason_code"], "no_data")
        self.assertEqual(kwargs["payload"]["raw_candidates"], 0)
        self.assertEqual(kwargs["payload"]["kept_candidates"], 0)
        self.assertEqual(kwargs["payload"]["mode"], "shadow")
        self.assertEqual(branch_events, [("no_data", "arbiter_no_traces")])

    def test_prepare_memory_context_propagates_retrieve_error_without_calling_arbiter(self) -> None:
        events = []
        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        state_events: list[tuple[str, dict[str, object]]] = []

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="shadow",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-retrieve-error",
            "messages": [{"role": "user", "content": "hello"}],
        }
        retrieval_result = SimpleNamespace(
            traces=[],
            status="error",
            ok=False,
            reason_code="retrieve_error",
            error_code="upstream_error",
            error_class="RuntimeError",
            top_k_requested=5,
        )
        memory_store_module = SimpleNamespace(
            _runtime_embedding_value=lambda field: 5 if field == "top_k" else None,
            retrieve_for_arbiter_with_status=lambda _msg: retrieval_result,
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("arbiter should not run when retrieval failed")
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        original_set_state = chat_memory_flow.chat_turn_logger.set_state
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        chat_memory_flow.chat_turn_logger.set_state = (
            lambda key, value: state_events.append((key, dict(value))) or None
        )
        try:
            prepared = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg="bonjour",
                config_module=config_module,
                memory_store_module=memory_store_module,
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
            )
            _mode, memory_traces, context_hints = prepared
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch
            chat_memory_flow.chat_turn_logger.set_state = original_set_state

        self.assertEqual(memory_traces, [])
        self.assertEqual(context_hints, [])
        self.assertEqual(prepared.memory_retrieved["status"], "error")
        self.assertEqual(prepared.memory_retrieved["reason_code"], "retrieve_error")
        self.assertEqual(prepared.memory_retrieved["error_code"], "upstream_error")
        self.assertEqual(prepared.memory_retrieved["error_class"], "RuntimeError")
        self.assertEqual(prepared.memory_arbitration["status"], "skipped")
        self.assertEqual(prepared.memory_arbitration["reason_code"], "retrieve_error")
        self.assertEqual(
            state_events,
            [
                (
                    "memory_retrieval",
                    {
                        "status": "error",
                        "reason_code": "retrieve_error",
                        "error_code": "upstream_error",
                        "error_class": "RuntimeError",
                        "top_k_requested": 5,
                        "top_k_returned": 0,
                    },
                )
            ],
        )
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, "arbiter")
        self.assertEqual(kwargs["status"], "skipped")
        self.assertEqual(kwargs["reason_code"], "retrieve_error")
        self.assertEqual(kwargs["payload"]["retrieval_status"], "error")
        self.assertEqual(kwargs["payload"]["retrieval_error_code"], "upstream_error")
        self.assertEqual(kwargs["payload"]["retrieval_error_class"], "RuntimeError")
        self.assertEqual(branch_events, [("retrieve_error", "memory_retrieve_failed")])

    def test_prepare_memory_context_emits_arbiter_skipped_when_mode_off_with_raw_traces(self) -> None:
        events = []
        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        raw_traces = [
            _trace(
                "r1",
                conversation_id="conv-off-a",
                role="user",
                content="Je suis Christophe Muck",
                timestamp="2026-04-10T09:00:00Z",
                score=0.91,
            ),
            _trace(
                "r2",
                conversation_id="conv-off-b",
                role="assistant",
                content="Nous travaillons sur FridaDev",
                timestamp="2026-04-10T09:01:00Z",
                score=0.74,
            ),
        ]

        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="off",
            CONTEXT_HINTS_MAX_ITEMS=2,
            CONTEXT_HINTS_MAX_AGE_DAYS=7,
            CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        )
        conversation = {
            "id": "conv-memory-off-skip",
            "messages": [{"role": "user", "content": "hello"}],
        }
        memory_store_module = SimpleNamespace(
            retrieve=lambda _msg: raw_traces,
            enrich_traces_with_summaries=lambda traces: traces,
            get_recent_context_hints=lambda **_kwargs: [],
        )
        arbiter_module = SimpleNamespace(
            filter_traces_with_diagnostics=lambda *_args, **_kwargs: (_ for _ in ()).throw(
                AssertionError("arbiter should not run in off mode")
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        try:
            _mode, memory_traces, context_hints = chat_memory_flow.prepare_memory_context(
                conversation=conversation,
                user_msg="bonjour",
                config_module=config_module,
                memory_store_module=memory_store_module,
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch

        self.assertEqual([trace["trace_id"] for trace in memory_traces], ["r1", "r2"])
        self.assertTrue(all(trace["candidate_id"].startswith("cand-") for trace in memory_traces))
        self.assertEqual(context_hints, [])
        self.assertTrue(chat_events)
        stage, kwargs = chat_events[0]
        self.assertEqual(stage, "arbiter")
        self.assertEqual(kwargs["status"], "skipped")
        self.assertEqual(kwargs["reason_code"], "mode_off")
        self.assertEqual(kwargs["payload"]["raw_candidates"], 2)
        self.assertEqual(kwargs["payload"]["basket_candidates"], 2)
        self.assertEqual(kwargs["payload"]["kept_candidates"], 2)
        self.assertEqual(kwargs["payload"]["mode"], "off")
        self.assertEqual(branch_events, [("mode_off", "arbiter_disabled_for_mode")])


if __name__ == "__main__":
    unittest.main()
