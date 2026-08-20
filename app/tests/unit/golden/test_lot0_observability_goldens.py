from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_read_model_service
from observability import hermeneutic_node_logger, turn_pipeline_read_model


def assert_liveness_read_model(payload):
    expected = {
        "status": "buffering",
        "reason_code": "below_threshold",
        "pairs_count": 1,
        "target_pairs": 5,
        "frozen": False,
        "failure_class": "deterministic_input",
        "recovery_action": "terminal_consume_without_write",
        "processing_state": "judge_not_called",
        "attempt_current": 1,
        "attempt_limit": 2,
        "window_fingerprint": "0123456789ab",
        "next_window_progress": "current_pair_staged",
        "window_chars": 50000,
        "payload_chars": 54000,
        "estimated_prompt_tokens": 13500,
    }
    if payload != expected:
        raise AssertionError("Lot 1 Identity liveness read-model critical state changed")


class Lot0ObservabilityGoldensTests(unittest.TestCase):
    def test_terminal_identity_event_projects_authoritative_policy_and_next_window_progress(self) -> None:
        staging_state = {
            "conversation_id": "lot0-observability",
            "buffer_pairs_count": 1,
            "buffer_target_pairs": 5,
            "buffer_frozen": False,
            "auto_canonization_suspended": False,
            "last_agent_status": "buffering",
            "last_agent_reason": None,
            "last_agent_run_ts": "2026-08-20T00:00:02Z",
            "updated_ts": "2026-08-20T00:00:03Z",
        }
        event = {
            "conversation_id": "lot0-observability",
            "turn_id": "lot0-turn",
            "ts": "2026-08-20T00:00:03Z",
            "stage": "mutable_identity_judge",
            "status": "skipped",
            "payload": {
                "reason_code": "window_too_large",
                "runtime_pipeline": "mutable_identity_judge_v2_add_only",
                "buffer_pairs_count": 5,
                "buffer_target_pairs": 5,
                "buffer_frozen": True,
                "buffer_cleared": True,
                "writes_applied": False,
                "failure_class": "deterministic_input",
                "recovery_action": "terminal_consume_without_write",
                "processing_state": "judge_not_called",
                "attempt_current": 1,
                "attempt_limit": 2,
                "window_fingerprint": "0123456789ab",
                "next_window_progress": "current_pair_staged",
                "next_buffer_pairs_count": 1,
                "judge_status": "skipped",
                "judge_reason_code": "window_too_large",
                "window_chars": 50000,
                "payload_chars": 54000,
                "estimated_prompt_tokens": 13500,
                "max_window_chars": 40000,
                "max_estimated_prompt_tokens": 16000,
            },
        }
        block = admin_identity_read_model_service.build_identity_staging_block(
            memory_store_module=SimpleNamespace(get_latest_identity_staging_state=lambda: staging_state),
            log_store_module=SimpleNamespace(
                read_chat_log_events=lambda **_kwargs: {"items": [copy.deepcopy(event)]}
            ),
        )
        compact = {
            "status": block["current_buffer"]["status"],
            "reason_code": block["current_buffer"]["reason_code"],
            "pairs_count": block["current_buffer"]["pairs_count"],
            "target_pairs": block["current_buffer"]["target_pairs"],
            "frozen": block["current_buffer"]["frozen"],
            "failure_class": block["latest_agent_activity"]["failure_class"],
            "recovery_action": block["latest_agent_activity"]["recovery_action"],
            "processing_state": block["latest_agent_activity"]["processing_state"],
            "attempt_current": block["latest_agent_activity"]["attempt_current"],
            "attempt_limit": block["latest_agent_activity"]["attempt_limit"],
            "window_fingerprint": block["latest_agent_activity"]["window_fingerprint"],
            "next_window_progress": block["latest_agent_activity"]["next_window_progress"],
            "window_chars": block["latest_agent_activity"]["window_chars"],
            "payload_chars": block["latest_agent_activity"]["payload_chars"],
            "estimated_prompt_tokens": block["latest_agent_activity"]["estimated_prompt_tokens"],
        }
        assert_liveness_read_model(compact)
        self.assertNotIn("buffer_pairs", block)
        self.assertNotIn("buffer_pairs_json", block)
        self.assertFalse(block["actively_injected"])

        for key, value in (
            ("status", "ok"),
            ("reason_code", "window_too_large"),
            ("frozen", True),
            ("pairs_count", 5),
            ("recovery_action", "retry_preserve"),
        ):
            mutated = dict(compact)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                assert_liveness_read_model(mutated)

    def test_secondary_sources_final_verdict_and_fail_open_are_in_events_but_partly_lost_in_cockpit(self) -> None:
        stimmung_prompt = hermeneutic_node_logger.build_stimmung_prompt_prepared_payload(
            decision_source="primary",
            messages=[{"role": "system", "content": "synthetic"}, {"role": "user", "content": "synthetic"}],
            recent_window_input_payload={"turns": []},
            temperature=0.1,
            top_p=1.0,
            max_tokens=32,
            timeout_s=10,
            context_window_turns=3,
        )
        validated_result = SimpleNamespace(
            status="ok",
            model="synthetic/validation-fallback",
            decision_source="fallback",
            reason_code="primary_invalid_json",
            validated_output={
                "validation_decision": "challenge",
                "final_judgment_posture": "answer",
                "final_output_regime": "presence",
                "arbiter_followed_upstream": False,
                "advisory_recommendations_followed": [],
                "advisory_recommendations_overridden": ["upstream_output_regime_proposed"],
                "applied_hard_guards": [],
                "arbiter_reason": "synthetic",
                "pipeline_directives_final": [],
            },
        )
        validation_payload = hermeneutic_node_logger.build_validation_agent_payload(
            validation_dialogue_context={"messages": [], "truncated": False},
            primary_payload={"primary_verdict": {"audit": {"fail_open": False}}},
            validated_result=validated_result,
        )
        primary_fail_open = hermeneutic_node_logger.build_primary_node_payload(
            primary_payload={
                "primary_verdict": {
                    "audit": {
                        "fail_open": True,
                        "fallback_used": True,
                        "fallback_source": "deterministic_primary",
                        "reason_code": "synthetic_primary_error",
                        "error_class": "SyntheticError",
                    }
                }
            }
        )
        events = [
            {
                "conversation_id": "lot0-observability",
                "turn_id": "lot0-turn",
                "ts": "2026-08-20T00:00:01Z",
                "stage": "stimmung_prompt_prepared",
                "status": "ok",
                "model": "synthetic/stimmung-primary",
                "payload": stimmung_prompt,
            },
            {
                "conversation_id": "lot0-observability",
                "turn_id": "lot0-turn",
                "ts": "2026-08-20T00:00:02Z",
                "stage": "stimmung_agent",
                "status": "ok",
                "model": "synthetic/stimmung-fallback",
                "payload": {"decision_source": "fallback", "reason_code": "primary_invalid_json"},
            },
            {
                "conversation_id": "lot0-observability",
                "turn_id": "lot0-turn",
                "ts": "2026-08-20T00:00:03Z",
                "stage": "primary_node",
                "status": "error",
                "payload": primary_fail_open,
            },
            {
                "conversation_id": "lot0-observability",
                "turn_id": "lot0-turn",
                "ts": "2026-08-20T00:00:04Z",
                "stage": "validation_prompt_prepared",
                "status": "ok",
                "model": "synthetic/validation-primary",
                "payload": {
                    "provider_caller": "validation_agent",
                    "attempt_decision_source": "primary",
                },
            },
            {
                "conversation_id": "lot0-observability",
                "turn_id": "lot0-turn",
                "ts": "2026-08-20T00:00:05Z",
                "stage": "validation_agent",
                "status": "ok",
                "model": "synthetic/validation-fallback",
                "payload": validation_payload,
            },
        ]
        cockpit = turn_pipeline_read_model.build_turn_pipeline_item(events)

        self.assertEqual(stimmung_prompt["attempt_decision_source"], "primary")
        self.assertEqual(events[1]["payload"]["decision_source"], "fallback")
        self.assertEqual(validation_payload["decision_source"], "fallback")
        self.assertEqual(validation_payload["final_judgment_posture"], "answer")
        self.assertEqual(validation_payload["final_output_regime"], "presence")
        self.assertTrue(primary_fail_open["fail_open"])
        self.assertEqual(cockpit["stage_counts"]["stimmung_prompt_prepared"], 1)
        self.assertEqual(cockpit["stage_counts"]["stimmung_agent"], 1)
        self.assertEqual(cockpit["stage_counts"]["validation_prompt_prepared"], 1)
        self.assertEqual(cockpit["stage_counts"]["validation_agent"], 1)
        self.assertTrue(cockpit["hermeneutic"]["node_state"]["fail_open"])
        self.assertGreaterEqual(cockpit["errors"]["fallback_count"], 1)
        self.assertTrue(cockpit["providers"]["secondary"]["stimmung"]["prepared_present"])
        self.assertTrue(cockpit["providers"]["secondary"]["validation"]["result_present"])
        self.assertNotIn("decision_source", cockpit["providers"]["secondary"]["stimmung"])
        self.assertNotIn("final_output_regime", cockpit["providers"]["secondary"]["validation"])


if __name__ == "__main__":
    unittest.main()
