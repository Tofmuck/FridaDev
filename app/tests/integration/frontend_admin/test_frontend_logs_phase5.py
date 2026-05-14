from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path
from typing import Any


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conv_store
from memory import memory_store


class FrontendLogsPhase5Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        original_init_db = memory_store.init_db
        original_init_catalog_db = conv_store.init_catalog_db
        original_init_messages_db = conv_store.init_messages_db
        sys.modules.pop("server", None)
        memory_store.init_db = lambda: None
        conv_store.init_catalog_db = lambda: None
        conv_store.init_messages_db = lambda: None
        try:
            cls.server = importlib.import_module("server")
        finally:
            memory_store.init_db = original_init_db
            conv_store.init_catalog_db = original_init_catalog_db
            conv_store.init_messages_db = original_init_messages_db

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self._original_admin_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False

    def tearDown(self) -> None:
        self.server.config.FRIDA_ADMIN_LAN_ONLY = self._original_admin_lan_only

    def test_index_exposes_log_entry_next_to_admin(self) -> None:
        html = (APP_DIR / "web" / "index.html").read_text(encoding="utf-8")

        self.assertIn('id="btnLogs"', html)
        self.assertIn('href="/log"', html)
        self.assertIn('id="btnSettings"', html)
        self.assertIn('href="/admin"', html)
        self.assertNotIn('href="log.html"', html)

    def test_log_page_reuses_admin_css_and_dedicated_log_js(self) -> None:
        source = (APP_DIR / "web" / "log.html").read_text(encoding="utf-8")

        self.assertIn('class="admin-page"', source)
        self.assertIn('href="admin.css"', source)
        self.assertIn('href="/admin"', source)
        self.assertIn('href="/hermeneutic-admin"', source)
        self.assertNotIn('href="/hermeneutic-admin" target="_blank"', source)
        self.assertIn('script src="admin_api.js"', source)
        self.assertIn('script src="log/log.js"', source)
        self.assertIn('id="logFiltersForm"', source)
        self.assertIn('<select id="logConversationId"', source)
        self.assertIn('<select id="logTurnId"', source)
        self.assertIn('<select id="logStage"', source)
        self.assertIn('<option value="turn_start">turn_start</option>', source)
        self.assertIn('<option value="memory_chain_snapshot">memory_chain_snapshot</option>', source)
        self.assertIn('<option value="stimmung_agent">stimmung_agent</option>', source)
        self.assertIn('<option value="hermeneutic_node_insertion">hermeneutic_node_insertion</option>', source)
        self.assertIn('<option value="primary_node">primary_node</option>', source)
        self.assertIn('<option value="validation_agent">validation_agent</option>', source)
        self.assertIn('<option value="turn_end">turn_end</option>', source)
        self.assertIn('id="deleteConversationLogs"', source)
        self.assertIn('id="deleteTurnLogs"', source)
        self.assertIn('id="exportConversationLogs"', source)
        self.assertIn('id="exportTurnLogs"', source)
        self.assertIn('id="logCockpitCards"', source)
        self.assertIn('id="logTurns"', source)
        self.assertIn('id="logTurnCountChip"', source)
        self.assertIn('id="logGroups"', source)
        self.assertNotIn('placeholder="conv-..."', source)
        self.assertNotIn('placeholder="turn-..."', source)
        self.assertNotIn("all_logs", source)
        self.assertNotIn("delete all logs", source.lower())

    def test_log_js_uses_admin_logs_chat_read_delete_and_export_routes(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")
        admin_source = (APP_DIR / "web" / "admin.js").read_text(encoding="utf-8")

        self.assertIn("/api/admin/logs/chat", source)
        self.assertIn("/api/admin/logs/chat/metadata", source)
        self.assertIn("/api/admin/logs/chat/metrics", source)
        self.assertIn("/api/admin/logs/chat/turns", source)
        self.assertIn("/api/admin/logs/chat/export.md", source)
        self.assertIn('method: "DELETE"', source)
        self.assertIn('deleteLogs("conversation")', source)
        self.assertIn('deleteLogs("turn")', source)
        self.assertIn('exportLogsMarkdown("conversation")', source)
        self.assertIn('exportLogsMarkdown("turn")', source)
        self.assertIn("elements.conversationId.addEventListener(\"change\"", source)
        self.assertIn("renderTurnOptions", source)
        self.assertIn("renderCockpit", source)
        self.assertIn("renderTurnRows", source)
        self.assertIn("loadCockpitMetrics", source)
        self.assertIn("loadTurnPipeline", source)
        self.assertIn("METRICS_EVENT_LIMIT", source)
        self.assertIn("METRIC_VISUAL_SOURCES", source)
        self.assertIn("sanitizeMetricLabel", source)
        self.assertIn("elements.turnId.disabled = true", source)
        self.assertIn("query.set(\"conversation_id\", conversationId)", source)
        self.assertIn("query.set(\"turn_id\", turnId)", source)
        self.assertNotIn("renseigner conversation_id", source)
        self.assertNotIn("all_logs", source)
        self.assertNotIn("/api/admin/logs/chat", admin_source)

    def test_frontend_flow_contract_selection_then_scoped_deletes(self) -> None:
        observed: dict[str, list[Any]] = {
            "metadata_calls": [],
            "read_calls": [],
            "metrics_calls": [],
            "turns_calls": [],
            "delete_calls": [],
            "export_calls": [],
        }
        original_read_metadata = self.server.log_store.read_chat_log_metadata
        original_read_events = self.server.log_store.read_chat_log_events
        original_read_metrics = self.server.log_store.read_full_turn_metrics_snapshot
        original_read_turns = self.server.log_store.read_chat_turn_pipeline
        original_delete = self.server.log_store.delete_chat_log_events
        original_export = self.server.log_markdown_export.export_chat_logs_markdown

        def fake_read_chat_log_metadata(*, conversation_id=None, **_kwargs: Any) -> dict[str, Any]:
            normalized = str(conversation_id or "").strip() or None
            observed["metadata_calls"].append(normalized)
            if normalized == "conv-1":
                return {
                    "selected_conversation_id": "conv-1",
                    "conversations": [
                        {"conversation_id": "conv-1", "last_ts": "2026-03-27T12:01:00+00:00", "events_count": 2},
                        {"conversation_id": "conv-2", "last_ts": "2026-03-27T12:00:00+00:00", "events_count": 1},
                    ],
                    "turns": [
                        {"turn_id": "turn-1", "last_ts": "2026-03-27T12:01:00+00:00", "events_count": 1},
                        {"turn_id": "turn-2", "last_ts": "2026-03-27T12:00:00+00:00", "events_count": 1},
                    ],
                }
            return {
                "selected_conversation_id": None,
                "conversations": [
                    {"conversation_id": "conv-1", "last_ts": "2026-03-27T12:01:00+00:00", "events_count": 2},
                    {"conversation_id": "conv-2", "last_ts": "2026-03-27T12:00:00+00:00", "events_count": 1},
                ],
                "turns": [],
            }

        def fake_read_chat_log_events(**kwargs: Any) -> dict[str, Any]:
            observed["read_calls"].append(
                {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                }
            )
            return {
                "items": [],
                "count": 0,
                "total": 0,
                "limit": int(kwargs.get("limit") or 100),
                "offset": int(kwargs.get("offset") or 0),
                "next_offset": None,
                "filters": {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                    "stage": kwargs.get("stage"),
                    "status": kwargs.get("status"),
                    "ts_from": kwargs.get("ts_from"),
                    "ts_to": kwargs.get("ts_to"),
                },
            }

        def fake_read_full_turn_metrics_snapshot(**kwargs: Any) -> dict[str, Any]:
            observed["metrics_calls"].append(
                {
                    "event_limit": kwargs.get("event_limit"),
                    "ts_from": kwargs.get("ts_from"),
                    "ts_to": kwargs.get("ts_to"),
                }
            )
            return {
                "kind": "full_turn_metrics_snapshot",
                "events_count": 8,
                "turns_observed_count": 2,
                "checklist": {
                    "classification_counts": {
                        "complete": 1,
                        "degraded": 1,
                        "partial": 0,
                        "legacy_incomplete": 0,
                    }
                },
                "llm_call_provider_metrics": {
                    "main_llm_call_count": 2,
                    "secondary_llm_call_count": 1,
                    "unknown_llm_call_count": 0,
                },
                "fallback_fail_open": {"total_count": 0},
                "rag_funnel": {
                    "retrieved_candidates_total": 3,
                    "basketed_candidates_total": 2,
                    "kept_candidates_total": 1,
                    "injected_candidates_total": 1,
                    "prompt_fallback_turns": 0,
                },
                "web": {
                    "requested_turns": 1,
                    "successful_count": 1,
                    "injected_turns": 1,
                    "skipped_count": 0,
                    "error_count": 0,
                },
                "errors_by_stage": {},
                "skipped_by_stage": {},
                "source": {"events_total": 8, "events_read": 8, "events_truncated": False},
                "redaction": {"raw_event_payloads_included": False},
            }

        def fake_read_chat_turn_pipeline(**kwargs: Any) -> dict[str, Any]:
            observed["turns_calls"].append(
                {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                    "limit": kwargs.get("limit"),
                    "offset": kwargs.get("offset"),
                }
            )
            return {
                "kind": "chat_turn_pipeline_read_model",
                "items": [
                    {
                        "conversation_id": "conv-1",
                        "turn_id": "turn-2",
                        "latest_ts": "2026-03-27T12:02:00+00:00",
                        "classification": "degraded",
                        "score": 86,
                        "persistence": {
                            "status": "saved",
                            "assistant_final_saved": True,
                            "assistant_interrupted": False,
                        },
                        "providers": {
                            "main": {"status": "ok", "response_chars": 12},
                            "secondary": {
                                "stimmung": {"status": "ok"},
                                "validation": {"status": "ok"},
                                "web_reformulation": {"status": "not_applicable"},
                            },
                        },
                        "rag": {"retrieved": 3, "basket": 2, "kept": 1, "injected": 1},
                        "identity": {"status": "present", "chars": 24},
                        "hermeneutic": {
                            "status": "present",
                            "node_state": {"read_valid": True, "write_succeeded": True},
                        },
                        "web": {"status": "ok", "requested": True},
                        "errors": {"error_count": 0, "fallback_count": 0},
                        "flags": {"events_truncated": False, "raw_event_payloads_included": False},
                    }
                ],
                "count": 1,
                "total": 1,
                "limit": int(kwargs.get("limit") or 50),
                "offset": int(kwargs.get("offset") or 0),
                "next_offset": None,
                "filters": {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                },
                "source": {"source_kind": "chat_log_events", "turns_truncated": False},
                "redaction": {"raw_event_payloads_included": False},
            }

        def fake_delete_chat_log_events(**kwargs: Any) -> dict[str, Any]:
            observed["delete_calls"].append(
                {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                }
            )
            conversation_id = str(kwargs.get("conversation_id") or "").strip() or None
            turn_id = str(kwargs.get("turn_id") or "").strip() or None
            if not conversation_id:
                raise ValueError("all_logs deletion is not supported in MVP")
            return {
                "scope": "turn_logs" if turn_id else "conversation_logs",
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "deleted_count": 1,
            }

        def fake_export_chat_logs_markdown(**kwargs: Any) -> dict[str, Any]:
            observed["export_calls"].append(
                {
                    "conversation_id": kwargs.get("conversation_id"),
                    "turn_id": kwargs.get("turn_id"),
                }
            )
            conversation_id = str(kwargs.get("conversation_id") or "").strip()
            turn_id = str(kwargs.get("turn_id") or "").strip() or None
            scope = "turn" if turn_id else "conversation"
            return {
                "scope": scope,
                "conversation_id": conversation_id,
                "turn_id": turn_id,
                "events_count": 1,
                "markdown": "# Frida Chat Logs Export\n",
            }

        self.server.log_store.read_chat_log_metadata = fake_read_chat_log_metadata
        self.server.log_store.read_chat_log_events = fake_read_chat_log_events
        self.server.log_store.read_full_turn_metrics_snapshot = fake_read_full_turn_metrics_snapshot
        self.server.log_store.read_chat_turn_pipeline = fake_read_chat_turn_pipeline
        self.server.log_store.delete_chat_log_events = fake_delete_chat_log_events
        self.server.log_markdown_export.export_chat_logs_markdown = fake_export_chat_logs_markdown
        try:
            page = self.client.get("/log")
            self.assertEqual(page.status_code, 200)
            page_html = page.get_data(as_text=True)
            page.close()
            self.assertIn('id="logConversationId"', page_html)
            self.assertIn('id="logTurnId"', page_html)

            metadata_root = self.client.get("/api/admin/logs/chat/metadata")
            self.assertEqual(metadata_root.status_code, 200)
            root_payload = metadata_root.get_json()
            self.assertTrue(root_payload["ok"])
            self.assertEqual(len(root_payload["conversations"]), 2)
            self.assertEqual(root_payload["turns"], [])

            metadata_conv = self.client.get("/api/admin/logs/chat/metadata?conversation_id=conv-1")
            self.assertEqual(metadata_conv.status_code, 200)
            conv_payload = metadata_conv.get_json()
            self.assertTrue(conv_payload["ok"])
            self.assertEqual(conv_payload["selected_conversation_id"], "conv-1")
            self.assertEqual([item["turn_id"] for item in conv_payload["turns"]], ["turn-1", "turn-2"])

            scoped_read = self.client.get("/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-2")
            self.assertEqual(scoped_read.status_code, 200)
            self.assertTrue(scoped_read.get_json()["ok"])

            metrics_read = self.client.get("/api/admin/logs/chat/metrics?event_limit=2000")
            self.assertEqual(metrics_read.status_code, 200)
            self.assertTrue(metrics_read.get_json()["ok"])

            turns_read = self.client.get("/api/admin/logs/chat/turns?conversation_id=conv-1&turn_id=turn-2")
            self.assertEqual(turns_read.status_code, 200)
            turns_payload = turns_read.get_json()
            self.assertTrue(turns_payload["ok"])
            self.assertEqual(turns_payload["items"][0]["classification"], "degraded")

            delete_conversation = self.client.delete("/api/admin/logs/chat?conversation_id=conv-1")
            self.assertEqual(delete_conversation.status_code, 200)
            self.assertEqual(delete_conversation.get_json()["scope"], "conversation_logs")

            delete_turn = self.client.delete("/api/admin/logs/chat?conversation_id=conv-1&turn_id=turn-2")
            self.assertEqual(delete_turn.status_code, 200)
            self.assertEqual(delete_turn.get_json()["scope"], "turn_logs")

            export_conversation = self.client.get(
                "/api/admin/logs/chat/export.md?conversation_id=conv-1",
            )
            self.assertEqual(export_conversation.status_code, 200)
            self.assertIn("text/markdown", export_conversation.content_type)

            export_turn = self.client.get(
                "/api/admin/logs/chat/export.md?conversation_id=conv-1&turn_id=turn-2",
            )
            self.assertEqual(export_turn.status_code, 200)
            self.assertIn("text/markdown", export_turn.content_type)
        finally:
            self.server.log_store.read_chat_log_metadata = original_read_metadata
            self.server.log_store.read_chat_log_events = original_read_events
            self.server.log_store.read_full_turn_metrics_snapshot = original_read_metrics
            self.server.log_store.read_chat_turn_pipeline = original_read_turns
            self.server.log_store.delete_chat_log_events = original_delete
            self.server.log_markdown_export.export_chat_logs_markdown = original_export

        self.assertEqual(observed["metadata_calls"], [None, "conv-1"])
        self.assertEqual(
            observed["read_calls"],
            [{"conversation_id": "conv-1", "turn_id": "turn-2"}],
        )
        self.assertEqual(observed["metrics_calls"], [{"event_limit": 2000, "ts_from": None, "ts_to": None}])
        self.assertEqual(
            observed["turns_calls"],
            [{"conversation_id": "conv-1", "turn_id": "turn-2", "limit": 50, "offset": 0}],
        )
        self.assertEqual(
            observed["delete_calls"],
            [
                {"conversation_id": "conv-1", "turn_id": None},
                {"conversation_id": "conv-1", "turn_id": "turn-2"},
            ],
        )
        self.assertEqual(
            observed["export_calls"],
            [
                {"conversation_id": "conv-1", "turn_id": None},
                {"conversation_id": "conv-1", "turn_id": "turn-2"},
            ],
        )

    def test_log_js_sorts_events_inside_turn_in_chronological_order(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")

        self.assertIn("const compareEventsChronoAsc", source)
        self.assertIn("Date.parse(toText(left?.ts))", source)
        self.assertIn("Date.parse(toText(right?.ts))", source)
        self.assertIn("group.events.sort(compareEventsChronoAsc)", source)

    def test_log_js_formats_memory_prompt_injection_compactly_without_raw_content(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")

        self.assertIn("const formatMemoryPromptInjection", source)
        self.assertIn('key === "memory_prompt_injection"', source)
        self.assertIn("injection_class", source)
        self.assertIn("trace_memory_injected_count", source)
        self.assertIn("summary_context_injected_count", source)
        self.assertIn("memory_traces_injected_count", source)
        self.assertIn("memory_context_summary_count", source)
        self.assertIn("context_hints_injected_count", source)
        self.assertNotIn("memory_trace_content", source)
        self.assertNotIn("context_hint_content", source)

    def test_log_js_renders_cockpit_and_turn_table_without_parsing_raw_payloads(self) -> None:
        source = (APP_DIR / "web" / "log" / "log.js").read_text(encoding="utf-8")

        self.assertIn("LOG_METRICS_ENDPOINT", source)
        self.assertIn("LOG_TURNS_ENDPOINT", source)
        self.assertIn("const BLOCKED_PAYLOAD_KEYS", source)
        self.assertIn('"prompt"', source)
        self.assertIn('"messages"', source)
        self.assertIn('"content"', source)
        self.assertIn('"query"', source)
        self.assertIn('"context_block"', source)
        self.assertIn("classification_counts", source)
        self.assertIn("main_llm_call_count", source)
        self.assertIn("secondary_llm_call_count", source)
        self.assertIn("rag_funnel", source)
        self.assertIn("createMiniBars", source)
        self.assertIn("objectMetricRows", source)
        self.assertIn("checklist.classification_counts", source)
        self.assertIn("llm_call_provider_metrics", source)
        self.assertIn("errors_by_stage/skipped_by_stage/fallback_fail_open.by_stage", source)
        self.assertIn("BLOCKED_METRIC_LABELS", source)
        self.assertIn("log-turn-table", source)
        self.assertNotIn("JSON.stringify(event.payload", source)

    def test_server_exposes_log_static_route(self) -> None:
        source = (APP_DIR / "server.py").read_text(encoding="utf-8")

        self.assertIn('@app.get("/log")', source)
        self.assertIn('return send_from_directory(app.static_folder, "log.html")', source)


if __name__ == "__main__":
    unittest.main()
