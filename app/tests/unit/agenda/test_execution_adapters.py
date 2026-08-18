from __future__ import annotations

import unittest

from agenda import agent_contract, execution_adapters, pending_store, product_methods
from tests.support.agenda_runtime_golden import (
    FakeAgendaReadClient,
    assert_content_free,
    propose_create_payload,
    read_today_payload,
)


ACTIVE_SETTINGS = agent_contract.AgendaAgentSettings(
    mode=agent_contract.MODE_ACTIVE,
    caldav_secret_configured=True,
)


class AgendaExecutionAdaptersTests(unittest.TestCase):
    def test_read_adapter_preserves_execution_and_final_lock(self) -> None:
        plan = _validated_plan(read_today_payload())
        read_client = FakeAgendaReadClient()

        outcome = execution_adapters.execute_read_plan(
            plan,
            settings=ACTIVE_SETTINGS,
            injected_read_client=read_client,
            now_iso="2026-06-08T00:00:00Z",
        )

        self.assertEqual(read_client.calls, ["list_calendars", "query_calendar_events"])
        self.assertEqual(outcome.read_execution_result.status, "ok")
        self.assertEqual(outcome.read_execution_result.reason_code, "agenda_readonly_executed")
        self.assertIsNone(outcome.proposal_execution_result)
        self.assertIsNotNone(outcome.final_response_lock)
        self.assertTrue(outcome.final_response_lock.ok)
        assert_content_free(outcome.read_execution_result.observation)
        assert_content_free(outcome.final_response_lock.to_message_meta())

    def test_proposal_adapter_updates_pending_state_without_event_read(self) -> None:
        plan = _validated_plan(propose_create_payload())
        read_client = FakeAgendaReadClient()
        initial_state = pending_store.AgendaPendingState.empty(conversation_id="synthetic-conversation")

        outcome = execution_adapters.execute_proposal_plan(
            plan,
            settings=ACTIVE_SETTINGS,
            pending_state=initial_state,
            now_iso="2026-06-08T00:00:00Z",
            injected_read_client=read_client,
            pending_id_factory=lambda: "agenda-pending-adapter-create",
        )

        self.assertEqual(read_client.calls, [])
        self.assertIsNone(outcome.read_execution_result)
        self.assertEqual(outcome.proposal_execution_result.status, "ok")
        self.assertEqual(outcome.proposal_execution_result.reason_code, "agenda_pending_action_created")
        self.assertEqual(len(outcome.pending_state.actions), 1)
        self.assertEqual(outcome.pending_state.actions[0].pending_action_id, "agenda-pending-adapter-create")
        self.assertEqual(outcome.pending_state.actions[0].status, "pending")
        self.assertIsNotNone(outcome.final_response_lock)
        self.assertTrue(outcome.final_response_lock.ok)
        assert_content_free(outcome.proposal_execution_result.observation)
        assert_content_free(outcome.final_response_lock.to_message_meta())

    def test_context_adapter_returns_capabilities_without_read_execution(self) -> None:
        plan = _validated_plan(_capabilities_payload())

        outcome = execution_adapters.execute_context_plan(plan)

        self.assertIsNone(outcome.read_execution_result)
        self.assertIsNone(outcome.proposal_execution_result)
        self.assertIsNotNone(outcome.final_response_lock)
        self.assertTrue(outcome.final_response_lock.ok)
        self.assertEqual(
            outcome.final_response_lock.reason_code,
            "agenda_capabilities_final_response",
        )
        assert_content_free(outcome.final_response_lock.to_message_meta())


def _validated_plan(payload):
    validation = agent_contract.validate_agent_payload(payload, settings=ACTIVE_SETTINGS)
    if validation.status != agent_contract.STATUS_VALIDATED or validation.plan is None:
        raise AssertionError(f"invalid synthetic Agenda plan: {validation.reason_code}")
    return validation.plan


def _capabilities_payload():
    payload = read_today_payload()
    payload.update(
        {
            "product_method": product_methods.METHOD_DESCRIBE_AGENDA_CAPABILITIES,
            "time_scope": {
                "kind": "none",
                "start": "",
                "end": "",
                "timezone": "UTC",
                "ambiguity": "none",
            },
            "tool_calls": [],
            "answer_mode": "agenda_summary",
        }
    )
    return payload


if __name__ == "__main__":
    unittest.main()
