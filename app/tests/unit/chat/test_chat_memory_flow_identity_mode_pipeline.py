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


class ChatMemoryFlowIdentityModePipelineTests(unittest.TestCase):
    def test_record_identity_entries_for_mode_handles_off_and_enforced(self) -> None:
        events = []
        observed = {
            "extract_called": 0,
            "persisted": None,
            "preview_called": 0,
            "evidence_called": 0,
        }

        arbiter_module = SimpleNamespace(
            extract_identities=lambda turns: observed.update({"extract_called": observed["extract_called"] + 1})
            or [{"identity_id": "id-1"}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update({"persisted": (conversation_id, list(entries))}),
            preview_identity_entries=lambda entries: observed.update({"preview_called": observed["preview_called"] + 1}) or entries,
            record_identity_evidence=lambda *_args, **_kwargs: observed.update({"evidence_called": observed["evidence_called"] + 1}),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_memory_flow.record_identity_entries_for_mode(
            "conv-identity-off",
            [{"role": "user", "content": "x"}],
            mode="off",
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )
        chat_memory_flow.record_identity_entries_for_mode(
            "conv-identity-enforced",
            [{"role": "assistant", "content": "y"}],
            mode="enforced_all",
            arbiter_module=arbiter_module,
            memory_store_module=memory_store_module,
            admin_logs_module=admin_logs_module,
        )

        self.assertEqual(observed["extract_called"], 1)
        self.assertEqual(observed["persisted"], ("conv-identity-enforced", [{"identity_id": "id-1"}]))
        self.assertEqual(observed["preview_called"], 0)
        self.assertEqual(observed["evidence_called"], 0)
        self.assertEqual(_event_payloads(events, "identity_mode_apply")[0]["action"], "skip_mode_off")
        self.assertEqual(
            _event_payloads(events, "identity_mode_apply")[1]["action"],
            "record_legacy_identity_diagnostics_and_stage",
        )

    def test_record_identity_entries_for_mode_enforced_runs_periodic_identity_staging_after_legacy_persist(self) -> None:
        events = []
        order: list[str] = []
        observed = {"turn_pair": None}
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [{"identity_id": "id-1"}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: order.append(
                f"persist:{conversation_id}:{len(list(entries))}"
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def fake_stage(conversation_id, turn_pair, **_kwargs):
            order.append(f"stage:{conversation_id}")
            observed["turn_pair"] = list(turn_pair)
            return {
                "status": "buffering",
                "reason_code": "below_threshold",
                "buffer_pairs_count": 1,
                "buffer_target_pairs": 15,
                "buffer_cleared": False,
                "writes_applied": False,
                "last_agent_status": "buffering",
                "outcomes": [
                    {
                        "subject": "llm",
                        "action": "no_change",
                        "old_len": 0,
                        "new_len": 0,
                        "validation_ok": True,
                        "reason_code": "no_change",
                    }
                ],
            }

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = fake_stage
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                "conv-identity-enforced",
                [
                    {"role": "user", "content": "x"},
                    {"role": "assistant", "content": "y"},
                ],
                mode="enforced_all",
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(order, ["persist:conv-identity-enforced:1", "stage:conv-identity-enforced"])
        self.assertEqual(
            observed["turn_pair"],
            [
                {"role": "user", "content": "x"},
                {"role": "assistant", "content": "y"},
            ],
        )
        stage_event = _event_payloads(events, "identity_periodic_agent_apply")[0]
        self.assertEqual(stage_event["status"], "buffering")
        self.assertEqual(stage_event["reason_code"], "below_threshold")
        self.assertEqual(stage_event["buffer_pairs_count"], 1)
        self.assertEqual(
            _event_payloads(events, "identity_mode_apply")[0]["action"],
            "record_legacy_identity_diagnostics_and_stage",
        )

    def test_record_identity_entries_for_mode_enforced_keeps_fail_open_when_periodic_agent_raises(self) -> None:
        events = []
        observed = {"persisted": None}
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [{"identity_id": "id-1"}],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {"persisted": (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def boom(*_args, **_kwargs):
            raise RuntimeError("periodic staging exploded")

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = boom
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                "conv-identity-enforced",
                [
                    {"role": "user", "content": "x"},
                    {"role": "assistant", "content": "y"},
                ],
                mode="enforced_all",
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(observed["persisted"], ("conv-identity-enforced", [{"identity_id": "id-1"}]))
        stage_event = _event_payloads(events, "identity_periodic_agent_apply")[0]
        self.assertEqual(stage_event["status"], "skipped")
        self.assertEqual(stage_event["reason_code"], "periodic_agent_flow_error")
        self.assertEqual(
            _event_payloads(events, "identity_mode_apply")[0]["action"],
            "record_legacy_identity_diagnostics_and_stage",
        )

    def test_record_identity_entries_for_mode_does_not_pass_partial_read_overclaim_to_identity_buffer(self) -> None:
        events = []
        observed = {
            "persisted": None,
            "buffered_turn_pair": None,
        }
        original_stage = chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair

        arbiter_module = SimpleNamespace(
            extract_identities=lambda _turns: [
                {
                    "subject": "llm",
                    "content": "Claims to have read the full article in detail",
                    "confidence": 0.88,
                    "stability": "durable",
                    "utterance_mode": "self_description",
                    "recurrence": "repeated",
                    "scope": "llm",
                    "evidence_kind": "explicit",
                }
            ],
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda conversation_id, entries: observed.update(
                {"persisted": (conversation_id, list(entries))}
            ),
            preview_identity_entries=lambda entries: list(entries),
            record_identity_evidence=lambda *_args, **_kwargs: None,
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        def fake_stage(_conversation_id, turn_pair, **_kwargs):
            observed["buffered_turn_pair"] = list(turn_pair)
            return {
                "status": "buffering",
                "reason_code": "below_threshold",
                "buffer_pairs_count": 1,
                "buffer_target_pairs": 15,
                "buffer_cleared": False,
                "writes_applied": False,
                "last_agent_status": "buffering",
                "outcomes": [
                    {
                        "subject": "llm",
                        "action": "no_change",
                        "old_len": 0,
                        "new_len": 0,
                        "validation_ok": True,
                        "reason_code": "no_change",
                    }
                ],
            }

        chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = fake_stage
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                "conv-identity-partial-guard",
                [
                    {"role": "user", "content": "Peux-tu le lire ?"},
                    {"role": "assistant", "content": "Claims to have read the full article in detail"},
                ],
                mode="enforced_all",
                web_input={"read_state": "page_partially_read"},
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.memory_identity_periodic_agent.stage_identity_turn_pair = original_stage

        self.assertEqual(observed["persisted"], ("conv-identity-partial-guard", []))
        self.assertEqual(
            observed["buffered_turn_pair"],
            [
                {"role": "user", "content": "Peux-tu le lire ?"},
                {"role": "assistant", "content": ""},
            ],
        )
        stage_event = _event_payloads(events, "identity_periodic_agent_apply")[0]
        self.assertEqual(stage_event["status"], "buffering")
        self.assertEqual(stage_event["reason_code"], "below_threshold")
        self.assertEqual(_event_payloads(events, "identity_mode_apply")[0]["guard_filtered_count"], 1)

    def test_record_identity_entries_for_mode_shadow_emits_skipped_identity_write_per_side(self) -> None:
        events = []
        observed = {
            "extract_called": 0,
            "persist_called": 0,
            "preview_called": 0,
            "evidence_args": None,
        }
        preview_entries = [
            {"subject": "llm", "content": "Frida profile", "status": "accepted"},
            {"subject": "user", "content": "User preference one", "status": "deferred"},
            {"subject": "user", "content": "User preference two", "status": "accepted"},
        ]

        arbiter_module = SimpleNamespace(
            extract_identities=lambda turns: observed.update({"extract_called": observed["extract_called"] + 1}) or list(turns),
        )
        memory_store_module = SimpleNamespace(
            persist_identity_entries=lambda *_args, **_kwargs: observed.update({"persist_called": observed["persist_called"] + 1}),
            preview_identity_entries=lambda _entries: observed.update({"preview_called": observed["preview_called"] + 1}) or preview_entries,
            record_identity_evidence=lambda conversation_id, entries: observed.update(
                {"evidence_args": (conversation_id, list(entries))}
            ),
        )
        admin_logs_module = SimpleNamespace(log_event=lambda event, **kwargs: events.append((event, kwargs)))

        chat_events: list[tuple[str, dict[str, object]]] = []
        branch_events: list[tuple[str, str]] = []
        original_emit = chat_memory_flow.chat_turn_logger.emit
        original_branch = chat_memory_flow.chat_turn_logger.emit_branch_skipped
        chat_memory_flow.chat_turn_logger.emit = lambda stage, **kwargs: chat_events.append((stage, kwargs)) or True
        chat_memory_flow.chat_turn_logger.emit_branch_skipped = (
            lambda *, reason_code, reason_short: branch_events.append((reason_code, reason_short)) or True
        )
        try:
            chat_memory_flow.record_identity_entries_for_mode(
                "conv-identity-shadow",
                [{"subject": "user", "content": "hello"}],
                mode="shadow",
                arbiter_module=arbiter_module,
                memory_store_module=memory_store_module,
                admin_logs_module=admin_logs_module,
            )
        finally:
            chat_memory_flow.chat_turn_logger.emit = original_emit
            chat_memory_flow.chat_turn_logger.emit_branch_skipped = original_branch

        self.assertEqual(observed["extract_called"], 1)
        self.assertEqual(observed["persist_called"], 0)
        self.assertEqual(observed["preview_called"], 1)
        self.assertEqual(observed["evidence_args"], ("conv-identity-shadow", preview_entries))

        identity_events = [kwargs for stage, kwargs in chat_events if stage == "identity_write"]
        self.assertEqual(len(identity_events), 2)
        by_side = {event["payload"]["target_side"]: event for event in identity_events}
        self.assertSetEqual(set(by_side.keys()), {"frida", "user"})
        self.assertTrue(all(event["status"] == "skipped" for event in identity_events))
        self.assertTrue(all(event["reason_code"] == "not_applicable" for event in identity_events))
        self.assertEqual(by_side["frida"]["payload"]["write_mode"], "legacy_diagnostic_shadow")
        self.assertEqual(by_side["frida"]["payload"]["write_effect"], "evidence_only")
        self.assertEqual(by_side["frida"]["payload"]["evidence_count"], 1)
        self.assertEqual(by_side["frida"]["payload"]["observed_count"], 1)
        self.assertEqual(by_side["user"]["payload"]["evidence_count"], 2)
        self.assertEqual(by_side["user"]["payload"]["observed_count"], 2)
        self.assertTrue(all(event["payload"]["persisted_count"] == 0 for event in identity_events))
        self.assertTrue(all(event["payload"]["retained_count"] == 0 for event in identity_events))
        self.assertTrue(all(event["payload"]["content_present"] for event in identity_events))
        self.assertTrue(all("preview" not in event["payload"] for event in identity_events))
        self.assertTrue(all("entries" not in event["payload"] for event in identity_events))
        self.assertEqual(branch_events, [("not_applicable", "identity_write_shadow_mode")])
        self.assertEqual(
            _event_payloads(events, "identity_mode_apply")[0]["action"],
            "record_legacy_identity_evidence_shadow",
        )


if __name__ == "__main__":
    unittest.main()
