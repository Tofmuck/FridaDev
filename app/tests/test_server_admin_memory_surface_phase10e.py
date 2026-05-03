from __future__ import annotations

import importlib
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_memory_history_dashboard, admin_memory_service
from core import conv_store
from memory import memory_store


class ServerAdminMemorySurfacePhase10eTests(unittest.TestCase):
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
        self._original_admin_token = self.server.config.FRIDA_ADMIN_TOKEN
        self._original_admin_lan_only = self.server.config.FRIDA_ADMIN_LAN_ONLY
        self._original_admin_allowed_cidrs = self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS
        self.server.config.FRIDA_ADMIN_TOKEN = ""
        self.server.config.FRIDA_ADMIN_LAN_ONLY = False
        self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS = ""

    def tearDown(self) -> None:
        self.server.config.FRIDA_ADMIN_TOKEN = self._original_admin_token
        self.server.config.FRIDA_ADMIN_LAN_ONLY = self._original_admin_lan_only
        self.server.config.FRIDA_ADMIN_ALLOWED_CIDRS = self._original_admin_allowed_cidrs

    def test_memory_admin_route_serves_dedicated_static_page(self) -> None:
        response = self.client.get("/memory-admin")
        try:
            self.assertEqual(response.status_code, 200)
            html = response.get_data(as_text=True)
            self.assertIn("Memory Admin", html)
            self.assertIn('href="admin.css"', html)
            self.assertIn('script src="memory_admin/api.js"', html)
            self.assertIn('script src="memory_admin/render_overview.js"', html)
            self.assertIn('script src="memory_admin/render_turns.js"', html)
            self.assertIn('script src="memory_admin/main.js"', html)
        finally:
            response.close()

    def test_memory_dashboard_route_wires_dedicated_service(self) -> None:
        observed = {"called": False}
        original_dashboard_response = self.server.admin_memory_service.dashboard_response

        def fake_dashboard_response(*_args, **_kwargs):
            observed["called"] = True
            return (
                {
                    "ok": True,
                    "surface": {"name": "Memory Admin"},
                    "overview": {"mode": "enforced_all"},
                },
                200,
            )

        self.server.admin_memory_service.dashboard_response = fake_dashboard_response
        try:
            response = self.client.get("/api/admin/memory/dashboard")
        finally:
            self.server.admin_memory_service.dashboard_response = original_dashboard_response

        self.assertEqual(response.status_code, 200)
        self.assertTrue(observed["called"])
        self.assertEqual(response.get_json()["surface"]["name"], "Memory Admin")

    def test_read_recent_turns_keeps_stages_promised_by_memory_admin(self) -> None:
        rows = [
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 9, 0, tzinfo=timezone.utc),
                'branch_skipped',
                'skipped',
                {'reason_code': 'no_data', 'reason_short': 'no_optional_branch'},
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 59, tzinfo=timezone.utc),
                'prompt_prepared',
                'ok',
                {'memory_prompt_injection': {'memory_traces_injected_count': 2}},
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 58, tzinfo=timezone.utc),
                'hermeneutic_node_insertion',
                'ok',
                {'inputs': {'memory_retrieved': {'retrieved_count': 4}, 'memory_arbitration': {'kept_count': 2}}},
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 57, tzinfo=timezone.utc),
                'arbiter',
                'ok',
                {'kept_candidates': 2, 'decision_source': 'llm'},
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 56, tzinfo=timezone.utc),
                'summaries',
                'ok',
                {
                    'active_summary_present': True,
                    'summary_count_used': 1,
                    'summary_usage': 'prompt_injection',
                    'in_prompt': True,
                    'summary_generation_observed': True,
                },
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 55, tzinfo=timezone.utc),
                'memory_retrieve',
                'ok',
                {'top_k_returned': 4, 'dense_candidates_count': 6},
            ),
            (
                'conv-memory',
                'turn-memory',
                datetime(2026, 4, 12, 8, 54, tzinfo=timezone.utc),
                'embedding',
                'ok',
                {'source_kind': 'query', 'provider': 'embed.example', 'dimensions': 384},
            ),
        ]

        class FakeCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, _query, _params):
                return None

            def fetchall(self):
                return list(rows)

        class FakeConn:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self):
                return FakeCursor()

        payload = admin_memory_service._read_recent_turns(
            conn_factory=lambda: FakeConn(),
            turn_limit=4,
        )

        self.assertEqual(payload["source_kind"], "historical_logs")
        self.assertEqual(len(payload["items"]), 1)
        stages = payload["items"][0]["stages"]
        self.assertEqual(
            set(stages.keys()),
            {
                'embedding',
                'memory_retrieve',
                'summaries',
                'arbiter',
                'hermeneutic_node_insertion',
                'prompt_prepared',
                'branch_skipped',
            },
        )
        self.assertEqual(stages['embedding']['payload']['source_kind'], 'query')
        self.assertEqual(stages['summaries']['payload']['summary_count_used'], 1)
        self.assertTrue(stages['summaries']['payload']['in_prompt'])
        self.assertTrue(stages['summaries']['payload']['summary_generation_observed'])
        self.assertEqual(stages['branch_skipped']['payload']['reason_code'], 'no_data')

    def test_stage_latencies_use_shared_summary_helper(self) -> None:
        admin_logs_module = SimpleNamespace(read_logs=lambda limit=5000: [{'event': 'stage_latency'}])
        expected = {'retrieve': {'count': 1, 'p50_ms': 12.0, 'p95_ms': 12.0}}

        with mock.patch.object(
            admin_memory_history_dashboard.admin_stage_latency_summary,
            'compute_stage_latencies',
            return_value=expected,
        ) as compute_stage_latencies:
            payload = admin_memory_service._stage_latencies(admin_logs_module)

        self.assertEqual(payload, expected)
        compute_stage_latencies.assert_called_once_with([{'event': 'stage_latency'}])

    def test_dashboard_response_builds_dedicated_memory_contract(self) -> None:
        runtime_settings_module = SimpleNamespace(
            get_embedding_settings=lambda: SimpleNamespace(
                payload={
                    "model": {"value": "embed/test"},
                    "endpoint": {"value": "https://embed.example/v1"},
                    "dimensions": {"value": 384},
                    "top_k": {"value": 5},
                    "token": {"is_set": True},
                }
            ),
            get_arbiter_model_settings=lambda: SimpleNamespace(
                payload={
                    "model": {"value": "arbiter/test"},
                    "timeout_s": {"value": 18},
                }
            ),
        )
        config_module = SimpleNamespace(
            HERMENEUTIC_MODE="enforced_all",
            ARBITER_MIN_SEMANTIC_RELEVANCE=0.62,
            ARBITER_MIN_CONTEXTUAL_GAIN=0.55,
            ARBITER_MAX_KEPT_TRACES=3,
        )
        admin_logs_module = SimpleNamespace(
            summarize_hermeneutic_mode_observation=lambda _mode: {
                "current_mode_observed": True,
                "observed_since": "2026-04-12T08:00:00Z",
            },
            read_logs=lambda limit=5000: [],
        )
        arbiter_module = SimpleNamespace(
            get_runtime_metrics=lambda: {"arbiter_call_count": 12, "arbiter_fallback_count": 1}
        )

        with mock.patch.object(
            admin_memory_service,
            "_conn_factory",
            return_value=lambda: None,
        ), mock.patch.object(
            admin_memory_service,
            "_read_durable_state",
            return_value={
                "source_kind": "durable_persistence",
                "traces": {"total": 12},
                "summaries": {"total": 0},
                "arbiter_decisions": {"total": 8, "kept_count": 2, "rejected_count": 6},
            },
        ), mock.patch.object(
            admin_memory_service,
            "_read_retrieval_summary",
            return_value={
                "config_source_kind": "calculated_aggregate",
                "activity_source_kind": "historical_logs",
                "recent_activity": {"turns_observed": 4},
            },
        ), mock.patch.object(
            admin_memory_service,
            "_read_embeddings_summary",
            return_value={
                "settings_source_kind": "calculated_aggregate",
                "activity_source_kind": "historical_logs",
                "recent_activity": {"total_events": 9},
            },
        ), mock.patch.object(
            admin_memory_service,
            "_read_pre_arbiter_summary",
            return_value={
                "contract_source_kind": "calculated_aggregate",
                "recent_activity_source_kind": "historical_logs",
                "contract": {"basket_limit": 8},
                "recent_activity": {"avg_basket_candidates": 6.0},
            },
        ), mock.patch.object(
            admin_memory_service,
            "_read_injection_summary",
            return_value={
                "source_kind": "historical_logs",
                "recent_activity": {"injected_turns": 3},
            },
        ), mock.patch.object(
            admin_memory_service,
            "_read_recent_turns",
            return_value={"source_kind": "historical_logs", "items": []},
        ), mock.patch.object(
            admin_memory_service,
            "_read_arbiter_persisted_preview",
            return_value={"source_kind": "durable_persistence", "count": 1, "items": []},
        ), mock.patch.object(
            admin_memory_service,
            "_stage_latencies",
            return_value={"retrieve": {"p50_ms": 12.0}},
        ):
            payload, status = admin_memory_service.dashboard_response(
                {},
                memory_store_module=SimpleNamespace(),
                arbiter_module=arbiter_module,
                admin_logs_module=admin_logs_module,
                runtime_settings_module=runtime_settings_module,
                config_module=config_module,
                log_store_module=SimpleNamespace(),
            )

        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["surface"]["name"], "Memory Admin")
        self.assertEqual(payload["surface"]["route"], "/memory-admin")
        self.assertEqual(payload["retrieval"]["config"]["top_k"], 5)
        self.assertEqual(payload["embeddings"]["settings"]["endpoint_host"], "embed.example")
        self.assertEqual(payload["arbiter"]["settings"]["reranker_status"], "no_go_for_now")
        self.assertEqual(payload["durable_state"]["source_kind"], "durable_persistence")
        self.assertEqual(payload["recent_turns"]["source_kind"], "historical_logs")
        self.assertTrue(payload["scope"]["dedicated_surface"])
        self.assertEqual(payload["read_errors"], [])


if __name__ == "__main__":
    unittest.main()
