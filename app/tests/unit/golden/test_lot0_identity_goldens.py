from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from memory import memory_identity_periodic_agent, mutable_identity_judge_v2
from tests.support import lot0_identity_goldens, server_chat_pipeline
from tests.support.server_test_bootstrap import load_server_module_for_tests


def _contains_forbidden_content_key(value: Any) -> bool:
    forbidden = {"buffer_pairs", "buffer_pairs_json", "content", "messages", "prompt", "proposition"}
    if isinstance(value, Mapping):
        return any(str(key) in forbidden or _contains_forbidden_content_key(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_forbidden_content_key(item) for item in value)
    return False


class Lot0IdentityGoldensTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        runtime = memory_identity_periodic_agent.mutable_identity_runtime
        self._original_llm_identity = runtime.identity.load_llm_identity
        self._original_user_identity = runtime.identity.load_user_identity
        runtime.identity.load_llm_identity = lambda: "Synthetic Frida identity."
        runtime.identity.load_user_identity = lambda: "Synthetic user identity."

    def tearDown(self) -> None:
        runtime = memory_identity_periodic_agent.mutable_identity_runtime
        runtime.identity.load_llm_identity = self._original_llm_identity
        runtime.identity.load_user_identity = self._original_user_identity

    def _run_threshold_case(
        self,
        behavior,
        *,
        fail_canonical_updates: bool = False,
    ) -> tuple[lot0_identity_goldens.RealStagingIdentityStore, dict[str, Any], list[dict[str, Any]], int]:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        store.fail_canonical_updates = fail_canonical_updates
        judge_calls = 0

        def run_judge(payload):
            nonlocal judge_calls
            judge_calls += 1
            return behavior(payload)

        arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
        for index in range(1, 5):
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot0-error-matrix",
                lot0_identity_goldens.synthetic_pair(index),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
            self.assertEqual(summary["status"], "buffering")
            self.assertEqual(judge_calls, 0)

        events: list[dict[str, Any]] = []
        original_emit = memory_identity_periodic_agent.chat_turn_logger.emit
        memory_identity_periodic_agent.chat_turn_logger.emit = (
            lambda stage, **kwargs: events.append({"stage": stage, **copy.deepcopy(kwargs)}) or True
        )
        try:
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot0-error-matrix",
                lot0_identity_goldens.synthetic_pair(5),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
        finally:
            memory_identity_periodic_agent.chat_turn_logger.emit = original_emit
        return store, summary, events, judge_calls

    def test_irreducible_window_is_terminal_and_sixth_turn_starts_next_window(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        events: list[dict[str, Any]] = []
        provider_calls = 0
        original_prompt = mutable_identity_judge_v2.load_prompt_v2
        original_settings = mutable_identity_judge_v2.judge_common.runtime_model_settings
        original_post = mutable_identity_judge_v2.requests.post
        original_emit = memory_identity_periodic_agent.chat_turn_logger.emit
        mutable_identity_judge_v2.load_prompt_v2 = lambda _path: "LOT0_SYNTHETIC_JUDGE_PROMPT"
        mutable_identity_judge_v2.judge_common.runtime_model_settings = lambda: {
            "model": "synthetic/judge",
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 32,
            "timeout_s": 1,
        }

        def forbidden_post(*_args, **_kwargs):
            nonlocal provider_calls
            provider_calls += 1
            raise AssertionError("window_too_large must stop before provider transport")

        mutable_identity_judge_v2.requests.post = forbidden_post
        memory_identity_periodic_agent.chat_turn_logger.emit = (
            lambda stage, **kwargs: events.append({"stage": stage, **copy.deepcopy(kwargs)}) or True
        )
        arbiter = SimpleNamespace(run_mutable_identity_judge=mutable_identity_judge_v2.run_mutable_identity_judge_v2)
        try:
            for index in range(1, 5):
                buffering = memory_identity_periodic_agent.stage_identity_turn_pair(
                    "lot0-frozen-window",
                    lot0_identity_goldens.synthetic_pair(index, chars_per_message=5000),
                    arbiter_module=arbiter,
                    memory_store_module=store,
                )
                self.assertEqual(buffering["status"], "buffering")
            terminal = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot0-frozen-window",
                lot0_identity_goldens.synthetic_pair(5, chars_per_message=5000),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
            state_after_terminal = store.get_identity_staging_state("lot0-frozen-window")
            sixth = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot0-frozen-window",
                lot0_identity_goldens.synthetic_pair(6, chars_per_message=5000),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
            state_after_sixth = store.get_identity_staging_state("lot0-frozen-window")
        finally:
            mutable_identity_judge_v2.load_prompt_v2 = original_prompt
            mutable_identity_judge_v2.judge_common.runtime_model_settings = original_settings
            mutable_identity_judge_v2.requests.post = original_post
            memory_identity_periodic_agent.chat_turn_logger.emit = original_emit

        serialized_window = repr(state_after_sixth["buffer_pairs"])
        golden = {
            "processed_pairs_count": terminal["buffer_pairs_count"],
            "target_pairs": terminal["buffer_target_pairs"],
            "reason_code": terminal["reason_code"],
            "failure_class": terminal["failure_class"],
            "action": terminal["recovery_action"],
            "attempt": terminal["attempt_current"],
            "terminal_buffer_cleared": terminal["buffer_cleared"],
            "pairs_after_terminal": state_after_terminal["buffer_pairs_count"],
            "pairs_after_sixth": state_after_sixth["buffer_pairs_count"],
            "sixth_staged_once": serialized_window.count("LOT0_USER_06") == 1,
            "sixth_window_frozen": state_after_sixth["buffer_frozen"],
            "canonical_update_count": sum(len(batch) for batch in store.canonical_update_batches),
        }
        lot0_identity_goldens.assert_frozen_window_regression_golden(golden)
        self.assertEqual(provider_calls, 0)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["stage"], "mutable_identity_judge")
        self.assertEqual(events[0]["reason_code"], "window_too_large")
        self.assertTrue(not _contains_forbidden_content_key(events[0]))
        self.assertEqual(sixth["status"], "buffering")
        self.assertEqual(store.mutable, {})

        for key, value in (
            ("pairs_after_terminal", 5),
            ("pairs_after_sixth", 5),
            ("sixth_staged_once", False),
            ("action", "retry_preserve"),
            ("canonical_update_count", 1),
        ):
            mutated = copy.deepcopy(golden)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot0_identity_goldens.assert_frozen_window_regression_golden(mutated)

    def test_identity_error_matrix_preserves_or_consumes_window_and_canon_exactly(self) -> None:
        def raising(exc):
            def behavior(_payload):
                raise exc

            return behavior

        def rejected_contract(contract):
            validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(contract)
            self.assertIsNone(validated)
            self.assertTrue(reason)
            return {
                "status": "skipped",
                "reason_code": reason,
                "observability": {"status": "skipped", "reason_code": reason},
            }

        invalid_business_contract = lot0_identity_goldens.add_contract()
        invalid_business_contract["verdicts"][1]["proposition"] = "Synthetic non ontological proposition."

        for valid_contract in (
            lot0_identity_goldens.no_change_contract(),
            lot0_identity_goldens.add_contract(),
        ):
            validated, reason = mutable_identity_judge_v2.validate_mutable_judge_contract_v2(valid_contract)
            self.assertIsNotNone(validated)
            self.assertEqual(reason, "")

        cases = (
            ("timeout", raising(TimeoutError("synthetic timeout")), False, "judge_transport_error", "retry_pending", False, 5, 0),
            ("transport", raising(ConnectionError("synthetic transport")), False, "judge_transport_error", "retry_pending", False, 5, 0),
            (
                "schema_invalid",
                lambda _payload: rejected_contract({}),
                False,
                "schema_invalid",
                "retry_pending",
                False,
                5,
                0,
            ),
            (
                "business_verdict_invalid",
                lambda _payload: rejected_contract(invalid_business_contract),
                False,
                "non_ontological_proposition",
                "retry_pending",
                False,
                5,
                0,
            ),
            (
                "window_too_large",
                lambda _payload: {
                    "status": "skipped",
                    "reason_code": "window_too_large",
                    "observability": {
                        "reason_code": "window_too_large",
                        "window_chars": 33000,
                        "payload_chars": 34000,
                        "estimated_prompt_tokens": 12100,
                    },
                },
                False,
                "window_too_large",
                "terminal_discarded",
                True,
                0,
                0,
            ),
            (
                "apply_failure",
                lambda _payload: lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract()),
                True,
                "canonical_write_failed",
                "write_recovery_pending",
                False,
                5,
                0,
            ),
            (
                "no_change",
                lambda _payload: lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.no_change_contract()),
                False,
                "completed_no_change",
                "completed_no_change",
                True,
                0,
                0,
            ),
            (
                "add",
                lambda _payload: lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract()),
                False,
                "applied",
                "applied",
                True,
                0,
                1,
            ),
        )
        observed_by_name = {}
        for name, behavior, fail_updates, reason, last_status, consumed, remaining, writes in cases:
            with self.subTest(name=name):
                store, summary, events, judge_calls = self._run_threshold_case(
                    behavior,
                    fail_canonical_updates=fail_updates,
                )
                state = store.get_identity_staging_state("lot0-error-matrix")
                actual = {
                    "status": summary["status"],
                    "reason_code": summary["reason_code"],
                    "last_agent_status": summary["last_agent_status"],
                    "window_consumed": summary["buffer_cleared"],
                    "remaining_pairs": state["buffer_pairs_count"],
                    "judge_calls": judge_calls,
                    "canonical_writes": len(store.mutable),
                    "event_stage": events[0]["stage"],
                    "event_reason_code": events[0]["reason_code"],
                    "event_content_free": not _contains_forbidden_content_key(events[0]),
                }
                expected = {
                    "status": "ok" if name in {"no_change", "add"} else "skipped",
                    "reason_code": reason,
                    "last_agent_status": last_status,
                    "window_consumed": consumed,
                    "remaining_pairs": remaining,
                    "judge_calls": 1,
                    "canonical_writes": writes,
                    "event_stage": "mutable_identity_judge",
                    "event_reason_code": reason,
                    "event_content_free": True,
                }
                lot0_identity_goldens.assert_error_case(actual, expected)
                observed_by_name[name] = actual

        for case_name, mutation in (
            ("timeout", {"window_consumed": True, "remaining_pairs": 0}),
            ("window_too_large", {"reason_code": "completed_no_change", "last_agent_status": "completed_no_change"}),
            ("apply_failure", {"canonical_writes": 1}),
        ):
            mutated = {**observed_by_name[case_name], **mutation}
            expected = observed_by_name[case_name]
            with self.assertRaises(AssertionError):
                lot0_identity_goldens.assert_error_case(mutated, expected)

    def test_five_saved_assistant_turns_call_legacy_extractor_five_times_and_judge_once(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        extractor_calls = 0
        judge_calls = 0
        judge_extract_counts: list[int] = []

        def extract_identities(_turn_pair):
            nonlocal extractor_calls
            extractor_calls += 1
            return []

        def run_judge(_payload):
            nonlocal judge_calls
            judge_calls += 1
            judge_extract_counts.append(extractor_calls)
            return lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.no_change_contract())

        replacements = {
            (self.server.arbiter, "extract_identities"): extract_identities,
            (self.server.arbiter, "run_mutable_identity_judge"): run_judge,
            (self.server.memory_store, "persist_identity_entries"): store.persist_identity_entries,
            (self.server.memory_store, "append_identity_staging_pair"): store.append_identity_staging_pair,
            (self.server.memory_store, "get_identity_staging_state"): store.get_identity_staging_state,
            (self.server.memory_store, "mark_identity_staging_status"): store.mark_identity_staging_status,
            (self.server.memory_store, "clear_identity_staging_buffer"): store.clear_identity_staging_buffer,
            (self.server.memory_store, "get_mutable_identity"): store.get_mutable_identity,
            (
                self.server.memory_store,
                "apply_mutable_identity_subject_updates",
            ): store.apply_mutable_identity_subject_updates,
        }
        originals = [(obj, name, getattr(obj, name)) for obj, name in replacements]
        for (obj, name), replacement in replacements.items():
            setattr(obj, name, replacement)
        try:
            result = server_chat_pipeline.exercise_chat_orchestration_golden(
                self.server,
                enabled_lanes=(),
                turn_count=5,
                preserve_identity_effects=True,
                hermeneutic_mode="enforced_identities",
            )
        finally:
            for obj, name, value in reversed(originals):
                setattr(obj, name, value)

        final_messages = result["conversation"]["messages"]
        actual = {
            "turns": len(result["responses"]),
            "assistant_saves": len(result["observed"]["save_calls"]),
            "final_user_messages": sum(message.get("role") == "user" for message in final_messages),
            "final_assistant_messages": sum(message.get("role") == "assistant" for message in final_messages),
            "extractor_calls": extractor_calls,
            "judge_calls": judge_calls,
            "judge_extract_counts": judge_extract_counts,
            "legacy_persist_calls": len(store.legacy_persist_calls),
            "canonical_update_count": sum(len(batch) for batch in store.canonical_update_batches),
        }
        lot0_identity_goldens.assert_identity_cardinality(actual)
        self.assertTrue(all(response.status_code == 200 for response in result["responses"]))
        for key, value in (
            ("extractor_calls", 4),
            ("judge_calls", 2),
            ("judge_extract_counts", [4]),
        ):
            mutated = dict(actual)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot0_identity_goldens.assert_identity_cardinality(mutated)


if __name__ == "__main__":
    unittest.main()
