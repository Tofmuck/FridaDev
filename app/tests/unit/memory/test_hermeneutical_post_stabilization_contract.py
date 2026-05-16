from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    container_app = Path("/app")
    if (container_app / "web").exists() and (container_app / "server.py").exists():
        return container_app
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_stage_latency_summary
from core import chat_memory_flow
from core import conversations_prompt_window
from identity import mutable_identity_validation
from memory import arbiter
from memory import hermeneutics_policy
from memory import memory_identity_dynamics
from observability import prompt_injection_summary


L2_CORPUS_PATH = APP_DIR / "tests" / "support" / "hermeneutical_post_stabilization_l2_corpus.json"


def _load_l2_corpus() -> dict[str, Any]:
    return json.loads(L2_CORPUS_PATH.read_text(encoding="utf-8"))


def _hps_config(mode: str = "enforced_all") -> SimpleNamespace:
    return SimpleNamespace(
        HERMENEUTIC_MODE=mode,
        CONTEXT_HINTS_MAX_ITEMS=2,
        CONTEXT_HINTS_MAX_AGE_DAYS=7,
        CONTEXT_HINTS_MIN_CONFIDENCE=0.6,
        MEMORY_TOP_K=3,
    )


class _HpsIdentityStore:
    def __init__(self) -> None:
        self.mutable: dict[str, dict[str, Any]] = {}
        self.staging: dict[str, dict[str, Any]] = {}
        self.persisted_legacy: list[tuple[str, list[dict[str, Any]]]] = []
        self.upsert_calls: list[tuple[str, str, str, str]] = []
        self.clear_calls: list[str] = []

    def get_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        item = self.mutable.get(subject)
        return copy.deepcopy(item) if item is not None else None

    def upsert_mutable_identity(
        self,
        subject: str,
        content: str,
        source_trace_id: str | None = None,
        *,
        updated_by: str = "system",
        update_reason: str = "",
    ) -> dict[str, Any]:
        payload = {
            "subject": subject,
            "content": content,
            "source_trace_id": source_trace_id,
            "updated_by": updated_by,
            "update_reason": update_reason,
        }
        self.mutable[subject] = payload
        self.upsert_calls.append((subject, content, updated_by, update_reason))
        return copy.deepcopy(payload)

    def clear_mutable_identity(self, subject: str) -> dict[str, Any] | None:
        self.clear_calls.append(subject)
        return copy.deepcopy(self.mutable.pop(subject, None))

    def persist_identity_entries(self, conversation_id: str, entries: list[dict[str, Any]]) -> None:
        self.persisted_legacy.append((conversation_id, copy.deepcopy(list(entries))))

    def preview_identity_entries(self, entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return copy.deepcopy(list(entries))

    def record_identity_evidence(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def get_identity_staging_state(self, conversation_id: str) -> dict[str, Any] | None:
        state = self.staging.get(conversation_id)
        return copy.deepcopy(state) if state is not None else None

    def append_identity_staging_pair(
        self,
        conversation_id: str,
        pair: list[dict[str, Any]],
        *,
        target_pairs: int = 15,
    ) -> dict[str, Any] | None:
        state = copy.deepcopy(
            self.staging.get(
                conversation_id,
                {
                    "conversation_id": conversation_id,
                    "buffer_pairs": [],
                    "buffer_pairs_count": 0,
                    "buffer_target_pairs": int(target_pairs),
                    "auto_canonization_suspended": False,
                    "last_agent_status": "buffering",
                    "last_agent_reason": None,
                    "last_agent_run_ts": None,
                },
            )
        )
        current_pairs = list(state["buffer_pairs"])
        if len(current_pairs) < int(target_pairs):
            current_pairs.append(copy.deepcopy({"user": pair[0], "assistant": pair[1]}))
        state["buffer_pairs"] = current_pairs[: int(target_pairs)]
        state["buffer_pairs_count"] = len(state["buffer_pairs"])
        state["buffer_target_pairs"] = int(target_pairs)
        state["buffer_frozen"] = state["buffer_pairs_count"] >= int(target_pairs)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def mark_identity_staging_status(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = "",
        touch_run_ts: bool = False,
        auto_canonization_suspended: bool | None = None,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state["last_agent_status"] = status
        state["last_agent_reason"] = reason or None
        if touch_run_ts:
            state["last_agent_run_ts"] = "2026-05-04T00:00:00Z"
        if auto_canonization_suspended is not None:
            state["auto_canonization_suspended"] = bool(auto_canonization_suspended)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)

    def clear_identity_staging_buffer(
        self,
        conversation_id: str,
        *,
        status: str,
        reason: str = "",
        auto_canonization_suspended: bool = False,
    ) -> dict[str, Any] | None:
        state = self.get_identity_staging_state(conversation_id)
        if state is None:
            return None
        state["buffer_pairs"] = []
        state["buffer_pairs_count"] = 0
        state["last_agent_status"] = status
        state["last_agent_reason"] = reason or None
        state["last_agent_run_ts"] = "2026-05-04T00:00:00Z"
        state["auto_canonization_suspended"] = bool(auto_canonization_suspended)
        self.staging[conversation_id] = copy.deepcopy(state)
        return copy.deepcopy(state)


class HermeneuticalPostStabilizationContractTests(unittest.TestCase):
    def _build_prompt_with_memory(self, memory_traces: list[dict[str, object]]) -> list[dict[str, str]]:
        logger = SimpleNamespace(info=lambda *_args, **_kwargs: None, warning=lambda *_args, **_kwargs: None)
        return conversations_prompt_window.build_prompt_messages(
            {
                "id": "conv-post-stabilization",
                "messages": [
                    {"role": "system", "content": "SYSTEM"},
                    {
                        "role": "user",
                        "content": "Tu te souviens du cadrage ?",
                        "timestamp": "2026-05-04T08:00:00Z",
                    },
                ],
            },
            "runtime/model",
            now="2026-05-04T09:00:00Z",
            memory_traces=memory_traces,
            context_hints=None,
            ensure_system_message_func=lambda messages: messages[0],
            get_active_summary_func=lambda _conversation_id: None,
            summary_cutoff_iso_func=lambda _summary: None,
            message_is_after_summary_func=lambda _message, _cutoff: True,
            make_summary_message_func=conversations_prompt_window.make_summary_message,
            make_context_hints_message_func=lambda *_args, **_kwargs: None,
            make_memory_context_message_func=conversations_prompt_window.make_memory_context_message,
            make_memory_message_func=lambda traces, ts_now: conversations_prompt_window.make_memory_message(
                traces,
                ts_now,
                delta_t_label_func=lambda _ts_msg, _ts_now: "il y a 1 h",
            ),
            count_tokens_func=lambda _messages, _model: 1,
            max_tokens=1000,
            now_iso_func=lambda: "2026-05-04T09:00:00Z",
            logger=logger,
            admin_log_event_func=lambda *_args, **_kwargs: None,
            silence_label_func=lambda _before, _after: "",
            delta_t_label_func=lambda _ts_msg, _ts_now: "il y a 1 h",
        )

    def test_parent_summary_is_the_only_source_of_contexte_du_souvenir_block(self) -> None:
        parent_summary = {
            "id": "summary-cadrage",
            "conversation_id": "conv-source",
            "start_ts": "2026-05-01T08:00:00Z",
            "end_ts": "2026-05-02T18:00:00Z",
            "content": "Le cadrage memoire a ete stabilise autour des preuves automatisables.",
        }
        memory_traces = [
            {
                "candidate_id": "cand-1",
                "role": "user",
                "content": "On veut des preuves automatisables.",
                "timestamp": "2026-05-02T10:00:00Z",
                "parent_summary": parent_summary,
            },
            {
                "candidate_id": "cand-2",
                "role": "assistant",
                "content": "Je reformule le cadrage sans attente passive.",
                "timestamp": "2026-05-02T11:00:00Z",
                "parent_summary": dict(parent_summary),
            },
        ]

        prompt_messages = self._build_prompt_with_memory(memory_traces)
        rendered = "\n\n".join(message["content"] for message in prompt_messages)

        self.assertIn("[Contexte du souvenir", rendered)
        self.assertEqual(rendered.count("[Contexte du souvenir"), 1)
        self.assertIn("Le cadrage memoire a ete stabilise autour des preuves automatisables.", rendered)
        self.assertIn("[Mémoire — souvenirs pertinents]", rendered)
        self.assertIn("On veut des preuves automatisables.", rendered)

        prompt_without_parent_summary = self._build_prompt_with_memory(
            [{**trace, "parent_summary": None} for trace in memory_traces]
        )
        rendered_without_parent = "\n\n".join(message["content"] for message in prompt_without_parent_summary)
        self.assertNotIn("[Contexte du souvenir", rendered_without_parent)
        self.assertIn("[Mémoire — souvenirs pertinents]", rendered_without_parent)

    def test_identity_preview_rejects_irony_and_role_play_even_with_durable_high_confidence(self) -> None:
        base_entry = {
            "subject": "user",
            "content": "Je suis evidemment le roi de la planete dans ce jeu.",
            "confidence": 0.99,
            "stability": "durable",
            "recurrence": "habitual",
            "scope": "user",
            "evidence_kind": "explicit",
        }

        preview = memory_identity_dynamics.preview_identity_entries(
            [
                {**base_entry, "utterance_mode": "irony"},
                {**base_entry, "content": "Imagine que je suis un capitaine fictif.", "utterance_mode": "role_play"},
            ],
            policy_module=hermeneutics_policy,
            config_module=SimpleNamespace(
                IDENTITY_MIN_CONFIDENCE=0.72,
                IDENTITY_DEFER_MIN_CONFIDENCE=0.58,
            ),
            trace_float_fn=lambda value: float(value or 0.0),
        )

        self.assertEqual([entry["status"] for entry in preview], ["rejected", "rejected"])
        self.assertIn("policy:utterance_mode=irony", preview[0]["reason"])
        self.assertIn("policy:utterance_mode=role_play", preview[1]["reason"])

    def test_l2_fixture_blocks_circumstantial_noise_from_mutable_canon(self) -> None:
        corpus = _load_l2_corpus()

        for case in corpus["mutable_identity_cases"]:
            with self.subTest(case=case["id"]):
                result = mutable_identity_validation.validate_mutable_identity_content(case["content"])

                self.assertEqual(result.ok, case["expected_ok"])
                self.assertEqual(result.reason_code, case["expected_reason"])

    def test_l2_active_identity_staging_does_not_canonize_role_play_or_irony_window(self) -> None:
        corpus = _load_l2_corpus()
        role_play_window = corpus["role_play_window"]
        proposition = role_play_window["proposition"]
        store = _HpsIdentityStore()
        events: list[tuple[str, dict[str, Any]]] = []
        observed_payloads: list[dict[str, Any]] = []

        def fake_run_identity_periodic_agent(payload: dict[str, Any]) -> dict[str, Any]:
            observed_payloads.append(copy.deepcopy(payload))
            return {
                "llm": {
                    "operations": [
                        {"kind": "no_change", "proposition": "", "reason": "stable canon"},
                    ]
                },
                "user": {
                    "operations": [
                        {"kind": "add", "proposition": proposition, "reason": "role-play should not canonize"},
                    ]
                },
                "meta": {
                    "execution_status": "complete",
                    "buffer_pairs_count": 15,
                    "window_complete": True,
                },
            }

        original_load_llm = chat_memory_flow.memory_identity_periodic_agent.identity.load_llm_identity
        original_load_user = chat_memory_flow.memory_identity_periodic_agent.identity.load_user_identity
        original_read_static_snapshot = (
            chat_memory_flow.memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot
        )
        original_write_static_content = (
            chat_memory_flow.memory_identity_periodic_agent.static_identity_content.write_static_identity_content
        )
        chat_memory_flow.memory_identity_periodic_agent.identity.load_llm_identity = lambda: "Frida garde une tenue sobre."
        chat_memory_flow.memory_identity_periodic_agent.identity.load_user_identity = (
            lambda: "Tof garde une orientation stable."
        )
        chat_memory_flow.memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot = (
            lambda subject: SimpleNamespace(
                content="Frida garde une tenue sobre." if subject == "llm" else "Tof garde une orientation stable.",
                raw_content="Frida garde une tenue sobre." if subject == "llm" else "Tof garde une orientation stable.",
                resolved_path=None,
            )
        )
        chat_memory_flow.memory_identity_periodic_agent.static_identity_content.write_static_identity_content = (
            lambda *_args, **_kwargs: None
        )

        try:
            for index, pair in enumerate(role_play_window["pairs"], start=1):
                utterance_mode = str(pair["utterance_mode"])
                arbiter_module = SimpleNamespace(
                    extract_identities=lambda _turns, mode=utterance_mode: [
                        {
                            "subject": "user",
                            "content": proposition,
                            "confidence": 0.99,
                            "stability": "durable",
                            "utterance_mode": mode,
                            "recurrence": "habitual",
                            "scope": "user",
                            "evidence_kind": "explicit",
                        }
                    ],
                    run_identity_periodic_agent=fake_run_identity_periodic_agent,
                )
                chat_memory_flow.record_identity_entries_for_mode(
                    "conv-hps-l2-role-play",
                    [
                        {"role": "user", "content": pair["user"]},
                        {"role": "assistant", "content": pair["assistant"]},
                    ],
                    mode="enforced_all",
                    arbiter_module=arbiter_module,
                    memory_store_module=store,
                    admin_logs_module=SimpleNamespace(
                        log_event=lambda event, **kwargs: events.append((event, dict(kwargs)))
                    ),
                )
                if index < 15:
                    self.assertEqual(store.get_identity_staging_state("conv-hps-l2-role-play")["buffer_pairs_count"], index)
        finally:
            chat_memory_flow.memory_identity_periodic_agent.identity.load_llm_identity = original_load_llm
            chat_memory_flow.memory_identity_periodic_agent.identity.load_user_identity = original_load_user
            chat_memory_flow.memory_identity_periodic_agent.static_identity_content.read_static_identity_snapshot = (
                original_read_static_snapshot
            )
            chat_memory_flow.memory_identity_periodic_agent.static_identity_content.write_static_identity_content = (
                original_write_static_content
            )

        self.assertEqual(len(observed_payloads), 1)
        self.assertTrue(all(pair["user"]["content"] == "" for pair in observed_payloads[0]["buffer_pairs"]))
        stage_event = [payload for event, payload in events if event == "identity_periodic_agent_apply"][-1]
        mode_event = [payload for event, payload in events if event == "identity_mode_apply"][-1]
        self.assertEqual(stage_event["status"], "ok")
        self.assertEqual(stage_event["reason_code"], "completed_no_change")
        self.assertFalse(stage_event["writes_applied"])
        self.assertTrue(stage_event["buffer_cleared"])
        self.assertEqual(store.upsert_calls, [])
        self.assertEqual(store.mutable, {})
        self.assertFalse(mode_event["canonical_write_applied"])
        self.assertEqual(mode_event["staging_reason_code"], "completed_no_change")

    def test_l2_memory_corpus_links_retrieval_basket_arbitration_and_prompt_injection(self) -> None:
        corpus = _load_l2_corpus()
        useful = corpus["memory_useful_case"]

        def prepare_with_result(result: Any, *, filter_fn: Any):
            events: list[tuple[str, dict[str, Any]]] = []
            store = SimpleNamespace(
                _runtime_embedding_value=lambda field: 3 if field == "top_k" else None,
                retrieve_for_arbiter_with_status=lambda _query: result,
                enrich_traces_with_summaries=lambda traces: [
                    {
                        **dict(trace),
                        "parent_summary": useful["parent_summary"] if trace.get("summary_id") == "sum-hps" else None,
                    }
                    for trace in traces
                ],
                record_arbiter_decisions=lambda *_args, **_kwargs: None,
                get_recent_context_hints=lambda **_kwargs: [],
            )
            prepared = chat_memory_flow.prepare_memory_context(
                conversation={
                    "id": "conv-hps-l2-memory",
                    "messages": [{"role": "user", "content": "question"}],
                },
                user_msg=useful["query"],
                config_module=_hps_config("enforced_all"),
                memory_store_module=store,
                arbiter_module=SimpleNamespace(filter_traces_with_diagnostics=filter_fn),
                admin_logs_module=SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, dict(kwargs)))),
            )
            return prepared, events

        no_data, _events = prepare_with_result(
            SimpleNamespace(
                traces=[],
                status="ok",
                ok=True,
                reason_code="no_data",
                error_code=None,
                error_class=None,
                top_k_requested=3,
            ),
            filter_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("arbiter must not run")),
        )
        self.assertEqual(no_data.memory_retrieved["status"], "ok")
        self.assertEqual(no_data.memory_retrieved["reason_code"], "no_data")
        self.assertEqual(no_data.memory_arbitration["reason_code"], "no_data")

        retrieve_error, _events = prepare_with_result(
            SimpleNamespace(
                traces=[],
                status="error",
                ok=False,
                reason_code="retrieve_error",
                error_code="upstream_error",
                error_class="RuntimeError",
                top_k_requested=3,
            ),
            filter_fn=lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("arbiter must not run")),
        )
        self.assertEqual(retrieve_error.memory_retrieved["status"], "error")
        self.assertEqual(retrieve_error.memory_retrieved["reason_code"], "retrieve_error")
        self.assertEqual(retrieve_error.memory_arbitration["reason_code"], "retrieve_error")

        def keep_first(traces: list[dict[str, Any]], _recent_turns: list[dict[str, Any]]):
            return [traces[0]], [
                {
                    "candidate_id": traces[0]["candidate_id"],
                    "keep": True,
                    "semantic_relevance": 0.93,
                    "contextual_gain": 0.91,
                    "redundant_with_recent": False,
                    "reason": "hps_fixture_useful",
                    "decision_source": "fixture",
                    "model": "tests",
                }
            ]

        useful_prepared, _events = prepare_with_result(
            SimpleNamespace(
                traces=[dict(useful["trace"])],
                status="ok",
                ok=True,
                reason_code=None,
                error_code=None,
                error_class=None,
                top_k_requested=3,
            ),
            filter_fn=keep_first,
        )
        self.assertEqual(useful_prepared.memory_retrieved["retrieved_count"], 1)
        self.assertEqual(useful_prepared.memory_arbitration["status"], "available")
        self.assertEqual(useful_prepared.memory_arbitration["kept_count"], 1)
        self.assertEqual(
            useful_prepared.memory_arbitration["injected_candidate_ids"],
            [useful_prepared.memory_traces[0]["candidate_id"]],
        )
        prompt_messages = self._build_prompt_with_memory(useful_prepared.memory_traces)
        injection = prompt_injection_summary.build_memory_prompt_injection_summary(
            prompt_messages,
            memory_traces=useful_prepared.memory_traces,
            context_hints=[],
        )
        self.assertTrue(injection["injected"])
        self.assertEqual(injection["memory_traces_injected_count"], 1)
        self.assertEqual(injection["memory_context_summary_count"], 1)
        self.assertEqual(injection["injected_candidate_ids"], useful_prepared.memory_arbitration["injected_candidate_ids"])

    def test_l2_cost_latency_probe_names_available_counters_and_missing_global_cost(self) -> None:
        events = [
            {
                "event": "context_build",
                "payload": {
                    "estimated_context_tokens": 400,
                    "prompt_soft_token_limit": 8000,
                    "prompt_soft_limit_exceeded": False,
                    "dialogue_messages_truncated": False,
                },
            },
            {
                "event": "prompt_prepared",
                "payload": {"estimated_prompt_tokens": 420, "memory_items_used": 1},
            },
            {"event": "llm_call", "duration_ms": 1200, "payload": {"response_chars": 180}},
            {"event": "turn_end", "duration_ms": 1500, "payload": {"final_status": "ok"}},
            {"event": "stage_latency", "stage": "retrieve", "duration_ms": 12},
            {"event": "stage_latency", "stage": "arbiter", "duration_ms": 24},
            {"event": "stage_latency", "stage": "identity_extractor", "duration_ms": 8},
            {"event": "stage_latency", "stage": "identity_periodic_agent", "duration_ms": 6},
            {"event": "stage_latency", "stage": "hermeneutic_node_insertion", "duration_ms": 7},
        ]

        available_token_counters = {
            "context_build.estimated_context_tokens": events[0]["payload"]["estimated_context_tokens"],
            "prompt_prepared.estimated_prompt_tokens": events[1]["payload"]["estimated_prompt_tokens"],
            "prompt_prepared.memory_items_used": events[1]["payload"]["memory_items_used"],
        }
        available_duration_counters = {
            "llm_call.duration_ms": events[2]["duration_ms"],
            "turn_end.duration_ms": events[3]["duration_ms"],
        }
        latency_summary = admin_stage_latency_summary.compute_stage_latencies(events)

        self.assertEqual(set(available_token_counters), {
            "context_build.estimated_context_tokens",
            "prompt_prepared.estimated_prompt_tokens",
            "prompt_prepared.memory_items_used",
        })
        self.assertEqual(set(available_duration_counters), {"llm_call.duration_ms", "turn_end.duration_ms"})
        self.assertEqual(set(latency_summary), {"retrieve", "arbiter", "identity_extractor"})
        self.assertNotIn("identity_periodic_agent", latency_summary)
        self.assertNotIn("hermeneutic_node_insertion", latency_summary)

    def test_l2_arbiter_parse_failure_never_reinjects_the_full_basket(self) -> None:
        original_get_model = arbiter._runtime_arbiter_model_name
        original_load_prompt = arbiter._load_prompt
        original_post = arbiter.requests.post
        original_headers = arbiter.llm_client.or_headers
        original_metrics = dict(arbiter._METRICS)

        def boom(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("invalid arbiter json")

        arbiter._runtime_arbiter_model_name = lambda: "tests/arbiter"
        arbiter._load_prompt = lambda _path, _label: "prompt"
        arbiter.requests.post = boom
        arbiter.llm_client.or_headers = lambda caller="arbiter": {"Authorization": f"caller={caller}"}
        try:
            kept, decisions = arbiter.filter_traces_with_diagnostics(
                [
                    {
                        "candidate_id": "cand-best",
                        "role": "user",
                        "content": "memoire utile",
                        "timestamp": "2026-05-04T08:00:00Z",
                        "score": 0.99,
                        "semantic_score": 0.99,
                    },
                    {
                        "candidate_id": "cand-other",
                        "role": "assistant",
                        "content": "memoire secondaire",
                        "timestamp": "2026-05-04T08:01:00Z",
                        "score": 0.88,
                        "semantic_score": 0.88,
                    },
                ],
                [{"role": "user", "content": "question"}],
            )
            low_kept, low_decisions = arbiter.filter_traces_with_diagnostics(
                [
                    {
                        "candidate_id": "cand-low-a",
                        "role": "user",
                        "content": "bruit",
                        "timestamp": "2026-05-04T08:02:00Z",
                        "score": 0.0,
                        "semantic_score": 0.0,
                    },
                    {
                        "candidate_id": "cand-low-b",
                        "role": "assistant",
                        "content": "autre bruit",
                        "timestamp": "2026-05-04T08:03:00Z",
                        "score": 0.0,
                        "semantic_score": 0.0,
                    },
                ],
                [{"role": "user", "content": "question"}],
            )
        finally:
            arbiter._runtime_arbiter_model_name = original_get_model
            arbiter._load_prompt = original_load_prompt
            arbiter.requests.post = original_post
            arbiter.llm_client.or_headers = original_headers
            arbiter._METRICS.clear()
            arbiter._METRICS.update(original_metrics)

        self.assertEqual([trace["candidate_id"] for trace in kept], ["cand-best"])
        self.assertEqual(sum(1 for decision in decisions if decision["keep"]), 1)
        self.assertTrue(all(decision["decision_source"] == "fallback" for decision in decisions))
        self.assertTrue(all("fallback:parse_or_runtime_error" in decision["reason"] for decision in decisions))
        self.assertEqual(low_kept, [])
        self.assertFalse(any(decision["keep"] for decision in low_decisions))

    def test_stage_latency_probe_scope_is_explicit_and_ignores_untracked_stages(self) -> None:
        summary = admin_stage_latency_summary.compute_stage_latencies(
            [
                {"event": "stage_latency", "stage": "retrieve", "duration_ms": 10},
                {"event": "stage_latency", "stage": "retrieve", "duration_ms": 30},
                {"event": "stage_latency", "stage": "arbiter", "duration_ms": 50},
                {"event": "stage_latency", "stage": "identity_extractor", "duration_ms": 70},
                {"event": "stage_latency", "stage": "prompt_prepared", "duration_ms": 5},
                {"event": "stage_latency", "stage": "hermeneutic_node_insertion", "duration_ms": 6},
                {"event": "other_event", "stage": "retrieve", "duration_ms": 999},
                {"event": "stage_latency", "stage": "retrieve", "duration_ms": -1},
            ]
        )

        self.assertEqual(set(summary.keys()), {"retrieve", "arbiter", "identity_extractor"})
        self.assertEqual(summary["retrieve"], {"count": 2, "p50_ms": 20.0, "p95_ms": 29.0})
        self.assertEqual(summary["arbiter"], {"count": 1, "p50_ms": 50.0, "p95_ms": 50.0})
        self.assertEqual(summary["identity_extractor"], {"count": 1, "p50_ms": 70.0, "p95_ms": 70.0})


if __name__ == "__main__":
    unittest.main()
