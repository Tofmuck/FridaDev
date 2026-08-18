from __future__ import annotations

import unittest
from types import SimpleNamespace

from agenda import agent_contract, agent_openrouter, chat_runtime, observability_read_model
from tests.support.agenda_runtime_golden import (
    ErrorAgendaModelClient,
    ExplodingAgendaModelClient,
    FakeAgendaModelClient,
    FakeAgendaReadClient,
    SecretCountingRuntimeSettings,
    assert_content_free,
    propose_create_payload,
    read_today_payload,
)


ACTIVE_SETTINGS = agent_contract.AgendaAgentSettings(
    mode="active",
    caldav_secret_configured=True,
)


class Lot9AgendaGoldenMatrixTests(unittest.TestCase):
    def test_toggle_and_resolution_matrix_preserves_status_without_side_effects(self) -> None:
        cases = (
            {
                "name": "toggle_off",
                "data": {"agenda_enabled": False},
                "settings": ACTIVE_SETTINGS,
                "model": ExplodingAgendaModelClient(),
                "expected": ("disabled", "agenda_toggle_off", "disabled", 0),
            },
            {
                "name": "runtime_off",
                "data": {"agenda_enabled": True},
                "settings": agent_contract.AgendaAgentSettings(
                    mode="off",
                    caldav_secret_configured=True,
                ),
                "model": ExplodingAgendaModelClient(),
                "expected": ("skipped", "agenda_agent_mode_off", "skipped", 0),
            },
            {
                "name": "secret_not_configured",
                "data": {"agenda_enabled": True},
                "settings": agent_contract.AgendaAgentSettings(
                    mode="active",
                    caldav_secret_configured=False,
                ),
                "model": ExplodingAgendaModelClient(),
                "expected": (
                    "fallback",
                    "agenda_agent_secret_not_configured",
                    "not_configured",
                    0,
                ),
            },
            {
                "name": "provider_error",
                "data": {"agenda_enabled": True},
                "settings": ACTIVE_SETTINGS,
                "model": ErrorAgendaModelClient(agent_openrouter.REASON_PROVIDER_ERROR),
                "expected": ("fallback", "agenda_agent_provider_error", "error", 1),
            },
        )

        for case in cases:
            with self.subTest(case=case["name"]):
                result = chat_runtime.run_agenda_chat_turn(
                    case["data"],
                    user_msg="SYNTHETIC-USER-CONTENT",
                    now_iso="2026-06-08T00:00:00Z",
                    config_module=SimpleNamespace(FRIDA_TIMEZONE="UTC"),
                    settings_override=case["settings"],
                    agent_model_client=case["model"],
                )

                expected_status, expected_reason, expected_projection, expected_calls = case["expected"]
                self.assertEqual(result.status, expected_status)
                self.assertEqual(result.reason_code, expected_reason)
                self.assertEqual(
                    chat_runtime.observability_status_for_payload(result.observability_payload),
                    expected_projection,
                )
                self.assertEqual(case["model"].calls, expected_calls)
                self.assertFalse(result.used)
                self.assertFalse(result.observability_payload["caldav_access"])
                self.assertFalse(result.observability_payload["secret_access"])
                self.assertFalse(result.observability_payload["mutation_attempted"])
                assert_content_free(result.observability_payload)

    def test_read_and_proposal_matrix_preserves_execution_and_confirmation_boundaries(self) -> None:
        read_client = FakeAgendaReadClient()
        read_result = chat_runtime.run_agenda_chat_turn(
            {"agenda_enabled": True},
            user_msg="SYNTHETIC-USER-CONTENT",
            now_iso="2026-06-08T00:00:00Z",
            config_module=SimpleNamespace(FRIDA_TIMEZONE="UTC"),
            settings_override=ACTIVE_SETTINGS,
            agent_model_client=FakeAgendaModelClient(read_today_payload()),
            read_client=read_client,
        )

        self.assertTrue(read_result.used)
        self.assertEqual(read_client.calls, ["list_calendars", "query_calendar_events"])
        self.assertEqual(read_result.observability_payload["read_execution_status"], "ok")
        self.assertEqual(read_result.observability_payload["read_tool_names"], ["event_query_range"])
        self.assertEqual(read_result.observability_payload["read_event_count"], 1)
        self.assertFalse(read_result.observability_payload["mutation_attempted"])
        self.assertIsNone(read_result.proposal_execution_result)
        assert_content_free(read_result.observability_payload)
        assert_content_free(read_result.final_response_lock.to_message_meta())

        proposal_client = FakeAgendaReadClient()
        runtime_settings = SecretCountingRuntimeSettings()
        proposal_result = chat_runtime.run_agenda_chat_turn(
            {"agenda_enabled": True},
            user_msg="SYNTHETIC-USER-CONTENT",
            now_iso="2026-06-08T00:00:00Z",
            config_module=SimpleNamespace(FRIDA_TIMEZONE="UTC"),
            settings_override=ACTIVE_SETTINGS,
            runtime_settings_module=runtime_settings,
            agent_model_client=FakeAgendaModelClient(propose_create_payload()),
            read_client=proposal_client,
            pending_id_factory=lambda: "agenda-pending-golden-create",
        )

        self.assertTrue(proposal_result.used)
        self.assertEqual(proposal_client.calls, [])
        self.assertEqual(runtime_settings.secret_reads, 0)
        self.assertIsNone(proposal_result.read_execution_result)
        self.assertEqual(len(proposal_result.pending_state.actions), 1)
        action = proposal_result.pending_state.actions[0]
        self.assertEqual(action.pending_action_id, "agenda-pending-golden-create")
        self.assertEqual(action.status, "pending")
        self.assertEqual(action.confirmation_level, "simple")
        self.assertEqual(proposal_result.observability_payload["pending_execution_status"], "ok")
        self.assertEqual(proposal_result.observability_payload["pending_status"], "pending")
        self.assertFalse(proposal_result.observability_payload["caldav_access"])
        self.assertFalse(proposal_result.observability_payload["secret_access"])
        self.assertFalse(proposal_result.observability_payload["mutation_attempted"])
        assert_content_free(proposal_result.observability_payload)
        assert_content_free(proposal_result.final_response_lock.to_message_meta())

    def test_observability_projection_prefers_each_child_error_and_rejects_raw_content(self) -> None:
        cases = (
            ("read", "read_execution", "agenda_readonly_client_resolution_error"),
            ("pending", "pending_execution", "agenda_pending_read_client_resolution_error"),
            ("write", "write_execution", "agenda_write_conflict"),
        )

        for child_name, child_key, reason_code in cases:
            with self.subTest(child=child_name):
                payload = {
                    "schema_version": "frida_agenda_golden_v1",
                    "status": "active_ready",
                    "reason_code": "agenda_agent_active_validated",
                    f"{child_name}_execution_status": "error",
                    f"{child_name}_execution_reason_code": reason_code,
                    child_key: {
                        "status": "error",
                        "reason_code": reason_code,
                        "raw_ics": "BEGIN:VCALENDAR\nBEGIN:VEVENT",
                        "caldav_path": "/remote.php/dav/calendars/fixture-user/private.ics",
                        "content_free": True,
                    },
                    "content_free": True,
                }

                projected = observability_read_model.project_observability_payload(payload)

                self.assertEqual(projected["status"], "error")
                self.assertEqual(projected["reason_code"], reason_code)
                self.assertTrue(projected["content_free"])
                assert_content_free(projected)


if __name__ == "__main__":
    unittest.main()
