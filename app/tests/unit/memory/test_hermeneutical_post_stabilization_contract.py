from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


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
from core import conversations_prompt_window
from memory import hermeneutics_policy
from memory import memory_identity_dynamics


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
