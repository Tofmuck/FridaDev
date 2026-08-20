from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from admin import admin_identity_judge_activity_projection, admin_identity_read_model_service
from memory import memory_identity_periodic_agent, mutable_identity_judge_v2
from tests.support import lot0_identity_goldens, lot1_identity_liveness_goldens


def _failure(reason_code: str, **observability: Any) -> dict[str, Any]:
    return {
        "status": "skipped",
        "reason_code": reason_code,
        "contract": None,
        "observability": {
            "status": "skipped",
            "reason_code": reason_code,
            **observability,
        },
    }


def _different_add_contract() -> dict[str, Any]:
    contract = lot0_identity_goldens.add_contract()
    contract["verdicts"][1]["proposition"] = (
        "Tof maintient une seconde limite synthetique explicite stable."
    )
    return contract


def _count_marker(state: dict[str, Any], marker: str) -> int:
    return repr(state.get("buffer_pairs") or []).count(marker)


class _CommittedThenIncoherentStore(lot0_identity_goldens.RealStagingIdentityStore):
    def __init__(self) -> None:
        super().__init__()
        self.nonempty_audit_count = 0
        self.return_incoherent_once = True

    def apply_mutable_identity_subject_updates(
        self,
        updates: list[dict[str, Any]],
        **kwargs: Any,
    ) -> Any:
        result = super().apply_mutable_identity_subject_updates(updates, **kwargs)
        if updates:
            self.nonempty_audit_count += 1
        if self.return_incoherent_once:
            self.return_incoherent_once = False
            return None
        return result


class _FinalizeFailsOnceStore(lot0_identity_goldens.RealStagingIdentityStore):
    def __init__(self) -> None:
        super().__init__()
        self.clear_calls = 0

    def clear_identity_staging_buffer(self, conversation_id: str, **kwargs: Any) -> Any:
        self.clear_calls += 1
        if self.clear_calls == 1:
            return None
        return super().clear_identity_staging_buffer(conversation_id, **kwargs)


class IdentityLivenessLot1Tests(unittest.TestCase):
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

    def _stage_four(self, conversation_id: str, store: Any, arbiter: Any) -> None:
        for index in range(1, 5):
            summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                conversation_id,
                lot0_identity_goldens.synthetic_pair(index),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
            self.assertEqual(summary["status"], "buffering")

    def test_timeout_then_success_retries_same_window_and_stages_current_pair_once(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        fingerprints: list[str] = []
        responses = [
            _failure("judge_timeout"),
            lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.no_change_contract()),
        ]

        def run_judge(payload: dict[str, Any]) -> dict[str, Any]:
            fingerprints.append(lot0_identity_goldens.window_fingerprint({"buffer_pairs": payload["window_pairs"]}))
            return copy.deepcopy(responses.pop(0))

        arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
        self._stage_four("lot1-timeout-success", store, arbiter)
        first = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-timeout-success",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        second = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-timeout-success",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-timeout-success")
        actual = {
            "first_action": first["recovery_action"],
            "second_action": second["recovery_action"],
            "attempts": [first["attempt_current"], second["attempt_current"]],
            "attempt_limit": second["attempt_limit"],
            "same_window_fingerprint": len(set(fingerprints)) == 1,
            "next_window_progress": second["next_window_progress"],
            "next_pairs_count": state["buffer_pairs_count"],
            "current_pair_occurrences": _count_marker(state, "LOT0_USER_06"),
        }
        lot1_identity_liveness_goldens.assert_retry_then_progress(actual)
        for key, value in (
            ("first_action", "terminal_consume_without_write"),
            ("attempts", [1, 1]),
            ("attempt_limit", 3),
            ("same_window_fingerprint", False),
            ("next_pairs_count", 0),
            ("current_pair_occurrences", 2),
        ):
            mutated = dict(actual)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot1_identity_liveness_goldens.assert_retry_then_progress(mutated)

    def test_repeated_timeout_is_bounded_then_next_five_turn_window_progresses(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        judged_windows: list[list[dict[str, Any]]] = []
        responses = [
            _failure("judge_timeout"),
            _failure("judge_timeout"),
            lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.no_change_contract()),
        ]

        def run_judge(payload: dict[str, Any]) -> dict[str, Any]:
            judged_windows.append(copy.deepcopy(payload["window_pairs"]))
            return copy.deepcopy(responses.pop(0))

        arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
        self._stage_four("lot1-timeout-terminal", store, arbiter)
        memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-timeout-terminal",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        terminal = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-timeout-terminal",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-timeout-terminal")
        actual = {
            "failure_class": terminal["failure_class"],
            "action": terminal["recovery_action"],
            "processing_state": terminal["processing_state"],
            "attempt": terminal["attempt_current"],
            "attempt_limit": terminal["attempt_limit"],
            "buffer_cleared": terminal["buffer_cleared"],
            "writes_applied": terminal["writes_applied"],
            "next_window_progress": terminal["next_window_progress"],
            "next_pairs_count": state["buffer_pairs_count"],
            "current_pair_occurrences": _count_marker(state, "LOT0_USER_06"),
        }
        lot1_identity_liveness_goldens.assert_terminal_progression(actual)
        for index in range(7, 11):
            memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot1-timeout-terminal",
                lot0_identity_goldens.synthetic_pair(index),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
        self.assertEqual(len(judged_windows), 3)
        self.assertEqual(
            [pair["user"]["content"].split("_")[2] for pair in judged_windows[2]],
            ["06", "07", "08", "09", "10"],
        )
        self.assertEqual(store.get_identity_staging_state("lot1-timeout-terminal")["buffer_pairs_count"], 0)

    def test_http_transport_classification_separates_recoverable_and_nonrecoverable_statuses(self) -> None:
        actual: dict[int, str] = {}
        for http_status in (401, 422, 429, 503):
            with self.subTest(http_status=http_status):
                conversation_id = f"lot1-http-{http_status}"
                store = lot0_identity_goldens.RealStagingIdentityStore()
                arbiter = SimpleNamespace(
                    run_mutable_identity_judge=lambda _payload, status=http_status: _failure(
                        "judge_transport_error",
                        http_status=status,
                    )
                )
                self._stage_four(conversation_id, store, arbiter)
                summary = memory_identity_periodic_agent.stage_identity_turn_pair(
                    conversation_id,
                    lot0_identity_goldens.synthetic_pair(5),
                    arbiter_module=arbiter,
                    memory_store_module=store,
                )
                actual[http_status] = summary["failure_class"]
                self.assertEqual(summary["recovery_action"], "retry_preserve")
                self.assertEqual(summary["attempt_current"], 1)
        lot1_identity_liveness_goldens.assert_http_failure_classes(actual)
        mutated = dict(actual)
        mutated[401] = "transient"
        with self.assertRaises(AssertionError):
            lot1_identity_liveness_goldens.assert_http_failure_classes(mutated)

    def test_deterministic_input_is_consumed_without_provider_or_canonical_write(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        provider_calls = 0
        original_prompt = mutable_identity_judge_v2.load_prompt_v2
        original_settings = mutable_identity_judge_v2.judge_common.runtime_model_settings
        original_post = mutable_identity_judge_v2.requests.post
        mutable_identity_judge_v2.load_prompt_v2 = lambda _path: "LOT1_SYNTHETIC_JUDGE_PROMPT"
        mutable_identity_judge_v2.judge_common.runtime_model_settings = lambda: {
            "model": "synthetic/judge",
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 32,
            "timeout_s": 1,
        }

        def forbidden_post(*_args: Any, **_kwargs: Any) -> Any:
            nonlocal provider_calls
            provider_calls += 1
            raise AssertionError("irreducible local input must not reach provider")

        mutable_identity_judge_v2.requests.post = forbidden_post
        arbiter = SimpleNamespace(run_mutable_identity_judge=mutable_identity_judge_v2.run_mutable_identity_judge_v2)
        try:
            for index in range(1, 5):
                memory_identity_periodic_agent.stage_identity_turn_pair(
                    "lot1-window-too-large",
                    lot0_identity_goldens.synthetic_pair(index, chars_per_message=5000),
                    arbiter_module=arbiter,
                    memory_store_module=store,
                )
            terminal = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot1-window-too-large",
                lot0_identity_goldens.synthetic_pair(5, chars_per_message=5000),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
        finally:
            mutable_identity_judge_v2.load_prompt_v2 = original_prompt
            mutable_identity_judge_v2.judge_common.runtime_model_settings = original_settings
            mutable_identity_judge_v2.requests.post = original_post
        state = store.get_identity_staging_state("lot1-window-too-large")
        self.assertEqual(terminal["failure_class"], "deterministic_input")
        self.assertEqual(terminal["recovery_action"], "terminal_consume_without_write")
        self.assertEqual(terminal["processing_state"], "judge_not_called")
        self.assertEqual(terminal["attempt_current"], 1)
        self.assertTrue(terminal["buffer_cleared"])
        self.assertEqual(state["buffer_pairs_count"], 0)
        self.assertEqual(provider_calls, 0)
        self.assertEqual(store.canonical_update_batches, [])

    def test_repeated_schema_and_business_contract_failures_are_bounded_without_false_no_change(self) -> None:
        for reason_code in (
            "schema_invalid",
            "invalid_verdict",
            "non_ontological_proposition",
        ):
            with self.subTest(reason_code=reason_code):
                conversation_id = f"lot1-{reason_code}"
                store = lot0_identity_goldens.RealStagingIdentityStore()
                arbiter = SimpleNamespace(
                    run_mutable_identity_judge=lambda _payload, reason=reason_code: _failure(reason)
                )
                self._stage_four(conversation_id, store, arbiter)
                first = memory_identity_periodic_agent.stage_identity_turn_pair(
                    conversation_id,
                    lot0_identity_goldens.synthetic_pair(5),
                    arbiter_module=arbiter,
                    memory_store_module=store,
                )
                second = memory_identity_periodic_agent.stage_identity_turn_pair(
                    conversation_id,
                    lot0_identity_goldens.synthetic_pair(6),
                    arbiter_module=arbiter,
                    memory_store_module=store,
                )
                self.assertEqual(first["failure_class"], "deterministic_contract")
                self.assertEqual(first["recovery_action"], "retry_preserve")
                self.assertEqual(second["recovery_action"], "terminal_consume_without_write")
                self.assertEqual(second["reason_code"], reason_code)
                self.assertNotIn(second["last_agent_status"], {"completed_no_change", "applied"})
                self.assertFalse(second["writes_applied"])
                self.assertEqual(
                    store.get_identity_staging_state(conversation_id)["buffer_pairs_count"],
                    1,
                )

    def test_apply_failure_retries_then_applies_once_and_stages_current_pair(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        store.fail_canonical_updates = True
        judge_calls = 0

        def run_judge(_payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal judge_calls
            judge_calls += 1
            return lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract())

        arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
        self._stage_four("lot1-apply-retry", store, arbiter)
        first = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-apply-retry",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        store.fail_canonical_updates = False
        second = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-apply-retry",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-apply-retry")
        self.assertEqual(first["failure_class"], "write_recovery")
        self.assertEqual(first["recovery_action"], "apply_recovery")
        self.assertEqual(second["recovery_action"], "completed")
        self.assertEqual(judge_calls, 2)
        self.assertEqual(len(store.mutable), 1)
        self.assertEqual(len(store.canonical_successful_update_batches), 1)
        self.assertEqual(state["buffer_pairs_count"], 1)
        self.assertEqual(_count_marker(state, "LOT0_USER_06"), 1)

    def test_committed_but_incoherent_apply_is_verified_without_duplicate_write_or_audit(self) -> None:
        store = _CommittedThenIncoherentStore()
        arbiter = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: lot0_identity_goldens.ok_judge_result(
                lot0_identity_goldens.add_contract()
            )
        )
        self._stage_four("lot1-apply-incoherent", store, arbiter)
        first = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-apply-incoherent",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        second = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-apply-incoherent",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        self.assertEqual(first["recovery_action"], "apply_recovery")
        self.assertEqual(second["recovery_action"], "completed")
        self.assertEqual(second["reason_code"], "write_recovery_completed")
        state = store.get_identity_staging_state("lot1-apply-incoherent")
        actual = {
            "canonical_successful_batches": len(store.canonical_successful_update_batches),
            "nonempty_audits": store.nonempty_audit_count,
            "canonical_items": len(store.mutable),
            "current_pair_occurrences": _count_marker(state, "LOT0_USER_06"),
        }
        lot1_identity_liveness_goldens.assert_idempotent_write_recovery(actual)
        for key, value in (
            ("canonical_successful_batches", 2),
            ("nonempty_audits", 2),
            ("canonical_items", 2),
            ("current_pair_occurrences", 0),
        ):
            mutated = dict(actual)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot1_identity_liveness_goldens.assert_idempotent_write_recovery(mutated)

    def test_ambiguous_commit_fence_blocks_identical_different_and_no_change_rejudgment(self) -> None:
        cases = (
            ("identical", lot0_identity_goldens.add_contract()),
            ("different", _different_add_contract()),
            ("no_change", lot0_identity_goldens.no_change_contract()),
        )
        for label, retry_contract in cases:
            with self.subTest(retry_verdict=label):
                store = _CommittedThenIncoherentStore()
                judge_calls = 0
                responses = [
                    lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract()),
                    lot0_identity_goldens.ok_judge_result(retry_contract),
                ]
                events: list[dict[str, Any]] = []
                original_emit = memory_identity_periodic_agent.chat_turn_logger.emit

                def run_judge(_payload: dict[str, Any]) -> dict[str, Any]:
                    nonlocal judge_calls
                    judge_calls += 1
                    return copy.deepcopy(responses.pop(0))

                memory_identity_periodic_agent.chat_turn_logger.emit = (
                    lambda stage, **kwargs: events.append(
                        {"stage": stage, **copy.deepcopy(kwargs)}
                    )
                    or True
                )
                arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
                try:
                    self._stage_four(f"lot1-ambiguous-{label}", store, arbiter)
                    first = memory_identity_periodic_agent.stage_identity_turn_pair(
                        f"lot1-ambiguous-{label}",
                        lot0_identity_goldens.synthetic_pair(5),
                        arbiter_module=arbiter,
                        memory_store_module=store,
                    )
                    second = memory_identity_periodic_agent.stage_identity_turn_pair(
                        f"lot1-ambiguous-{label}",
                        lot0_identity_goldens.synthetic_pair(6),
                        arbiter_module=arbiter,
                        memory_store_module=store,
                    )
                finally:
                    memory_identity_periodic_agent.chat_turn_logger.emit = original_emit

                self.assertEqual(first["recovery_action"], "apply_recovery")
                projected = admin_identity_judge_activity_projection.latest_agent_activity(
                    {
                        "stage": "mutable_identity_judge",
                        "status": events[-1]["status"],
                        "payload": copy.deepcopy(events[-1]["payload"]),
                    }
                )
                state = store.get_identity_staging_state(f"lot1-ambiguous-{label}")
                actual = {
                    "judge_calls": judge_calls,
                    "canonical_successful_batches": len(
                        store.canonical_successful_update_batches
                    ),
                    "nonempty_audits": store.nonempty_audit_count,
                    "reason_code": second.get("reason_code"),
                    "action": second.get("recovery_action"),
                    "judge_status": second.get("judge_status"),
                    "apply_status": second.get("apply_status"),
                    "writes_previously_applied": second.get(
                        "writes_previously_applied"
                    ),
                    "projected_writes_previously_applied": projected.get(
                        "writes_previously_applied"
                    ),
                    "next_pairs_count": state["buffer_pairs_count"],
                    "current_pair_occurrences": _count_marker(state, "LOT0_USER_06"),
                }
                lot1_identity_liveness_goldens.assert_ambiguous_commit_recovery(actual)
                for field in (
                    "writes_previously_applied",
                    "projected_writes_previously_applied",
                ):
                    for mutation in (False, None):
                        mutated = dict(actual)
                        if mutation is None:
                            mutated.pop(field)
                        else:
                            mutated[field] = mutation
                        with self.assertRaises(AssertionError):
                            lot1_identity_liveness_goldens.assert_ambiguous_commit_recovery(mutated)

    def test_complete_window_after_crash_before_judge_starts_at_attempt_one(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        for index in range(1, 6):
            store.append_identity_staging_pair(
                "lot1-crash-before-judge",
                lot0_identity_goldens.synthetic_pair(index),
                target_pairs=memory_identity_periodic_agent.BUFFER_TARGET_PAIRS,
            )
        pre_crash = store.get_identity_staging_state("lot1-crash-before-judge")
        judge_calls = 0

        def run_judge(_payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal judge_calls
            judge_calls += 1
            return lot0_identity_goldens.ok_judge_result(
                lot0_identity_goldens.no_change_contract()
            )

        summary = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-crash-before-judge",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=SimpleNamespace(run_mutable_identity_judge=run_judge),
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-crash-before-judge")
        actual = {
            "pre_crash_status": pre_crash["last_agent_status"],
            "pre_crash_attempt_recorded": bool(pre_crash["last_agent_run_ts"]),
            "attempt_current": summary["attempt_current"],
            "judge_calls": judge_calls,
            "action": summary["recovery_action"],
            "next_pairs_count": state["buffer_pairs_count"],
            "current_pair_occurrences": _count_marker(state, "LOT0_USER_06"),
        }
        lot1_identity_liveness_goldens.assert_crash_before_judge_attempt(actual)
        mutated = dict(actual, attempt_current=2)
        with self.assertRaises(AssertionError):
            lot1_identity_liveness_goldens.assert_crash_before_judge_attempt(mutated)

    def test_runtime_safety_violation_retries_before_terminal_consumption(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        arbiter = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: self.fail(
                "judge must not be called when the local runtime input cannot load"
            )
        )
        self._stage_four("lot1-runtime-safety", store, arbiter)
        runtime = memory_identity_periodic_agent.mutable_identity_runtime
        original_load = runtime.identity.load_llm_identity
        runtime.identity.load_llm_identity = lambda: (_ for _ in ()).throw(
            OSError("synthetic load failure")
        )
        try:
            first = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot1-runtime-safety",
                lot0_identity_goldens.synthetic_pair(5),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
            second = memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot1-runtime-safety",
                lot0_identity_goldens.synthetic_pair(6),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
        finally:
            runtime.identity.load_llm_identity = original_load
        state = store.get_identity_staging_state("lot1-runtime-safety")
        actual = {
            "reason_code": first.get("reason_code"),
            "failure_class": first.get("failure_class"),
            "first_action": first.get("recovery_action"),
            "first_attempt": first.get("attempt_current"),
            "first_buffer_cleared": first.get("buffer_cleared"),
            "second_action": second.get("recovery_action"),
            "second_attempt": second.get("attempt_current"),
            "next_pairs_count": state["buffer_pairs_count"],
        }
        lot1_identity_liveness_goldens.assert_runtime_safety_retry(actual)

    def test_unverified_write_recovery_is_terminal_without_false_success(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        store.fail_canonical_updates = True
        responses = [
            lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract()),
            lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.no_change_contract()),
        ]
        arbiter = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: copy.deepcopy(responses.pop(0))
        )
        self._stage_four("lot1-write-unverified", store, arbiter)
        first = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-write-unverified",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        store.fail_canonical_updates = False
        second = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-write-unverified",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-write-unverified")
        self.assertEqual(first["recovery_action"], "apply_recovery")
        actual = {
            "reason_code": second["reason_code"],
            "action": second["recovery_action"],
            "processing_state": second["processing_state"],
            "writes_applied": second["writes_applied"],
            "canonical_items": len(store.mutable),
            "next_pairs_count": state["buffer_pairs_count"],
        }
        lot1_identity_liveness_goldens.assert_unverified_write_recovery_terminal(actual)
        for key, value in (
            ("reason_code", "completed_no_change"),
            ("action", "completed"),
            ("writes_applied", True),
            ("canonical_items", 1),
        ):
            mutated = dict(actual)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot1_identity_liveness_goldens.assert_unverified_write_recovery_terminal(mutated)

    def test_successful_write_then_finalize_failure_recovers_without_rejudging_or_reapplying(self) -> None:
        store = _FinalizeFailsOnceStore()
        judge_calls = 0

        def run_judge(_payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal judge_calls
            judge_calls += 1
            return lot0_identity_goldens.ok_judge_result(lot0_identity_goldens.add_contract())

        arbiter = SimpleNamespace(run_mutable_identity_judge=run_judge)
        self._stage_four("lot1-finalize-recovery", store, arbiter)
        first = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-finalize-recovery",
            lot0_identity_goldens.synthetic_pair(5),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        second = memory_identity_periodic_agent.stage_identity_turn_pair(
            "lot1-finalize-recovery",
            lot0_identity_goldens.synthetic_pair(6),
            arbiter_module=arbiter,
            memory_store_module=store,
        )
        state = store.get_identity_staging_state("lot1-finalize-recovery")
        self.assertEqual(first["failure_class"], "write_recovery")
        self.assertEqual(first["recovery_action"], "apply_recovery")
        self.assertEqual(first["reason_code"], "staging_finalize_failed")
        self.assertEqual(second["recovery_action"], "completed")
        self.assertEqual(second["reason_code"], "staging_finalize_recovered")
        self.assertEqual(judge_calls, 1)
        self.assertEqual(len(store.canonical_successful_update_batches), 1)
        self.assertEqual(state["buffer_pairs_count"], 1)
        self.assertEqual(_count_marker(state, "LOT0_USER_06"), 1)

    def test_event_and_read_model_keep_failure_policy_fields_content_free(self) -> None:
        store = lot0_identity_goldens.RealStagingIdentityStore()
        events: list[dict[str, Any]] = []
        original_emit = memory_identity_periodic_agent.chat_turn_logger.emit
        memory_identity_periodic_agent.chat_turn_logger.emit = (
            lambda stage, **kwargs: events.append({"stage": stage, **copy.deepcopy(kwargs)}) or True
        )
        arbiter = SimpleNamespace(
            run_mutable_identity_judge=lambda _payload: lot0_identity_goldens.ok_judge_result(
                lot0_identity_goldens.add_contract()
            )
        )
        store.fail_canonical_updates = True
        try:
            self._stage_four("lot1-observability", store, arbiter)
            memory_identity_periodic_agent.stage_identity_turn_pair(
                "lot1-observability",
                lot0_identity_goldens.synthetic_pair(5),
                arbiter_module=arbiter,
                memory_store_module=store,
            )
        finally:
            memory_identity_periodic_agent.chat_turn_logger.emit = original_emit
        payload = events[-1]["payload"]
        projected = admin_identity_read_model_service.build_identity_staging_block(
            memory_store_module=SimpleNamespace(
                get_latest_identity_staging_state=lambda: store.get_identity_staging_state(
                    "lot1-observability"
                )
            ),
            log_store_module=SimpleNamespace(
                read_chat_log_events=lambda **_kwargs: {
                    "items": [
                        {
                            "stage": "mutable_identity_judge",
                            "status": events[-1]["status"],
                            "payload": copy.deepcopy(payload),
                        }
                    ]
                }
            ),
        )["latest_agent_activity"]
        actual = {
            "failure_class": projected["failure_class"],
            "recovery_action": projected["recovery_action"],
            "processing_state": projected["processing_state"],
            "attempt_current": projected["attempt_current"],
            "attempt_limit": projected["attempt_limit"],
            "window_fingerprint_present": len(projected["window_fingerprint"]) == 12,
            "next_window_progress": projected["next_window_progress"],
        }
        lot1_identity_liveness_goldens.assert_observability_contract(actual)
        self.assertTrue(
            {"content", "prompt", "messages", "proposition", "buffer_pairs"}.isdisjoint(payload)
        )
        for key in ("failure_class", "recovery_action", "window_fingerprint"):
            mutated = dict(actual)
            mutated[key] = ""
            with self.assertRaises(AssertionError):
                lot1_identity_liveness_goldens.assert_observability_contract(mutated)

    def test_guard_increase_is_bounded_and_keeps_irreducible_limit(self) -> None:
        self.assertEqual(mutable_identity_judge_v2.JUDGE_WINDOW_MAX_CHARS, 40_000)
        self.assertEqual(mutable_identity_judge_v2.JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT, 16_000)
        self.assertLess(mutable_identity_judge_v2.JUDGE_ESTIMATED_PROMPT_TOKEN_LIMIT, 400_000 // 10)

    def test_window_above_old_guard_reaches_only_fake_provider_under_new_guard(self) -> None:
        pairs = []
        for index in range(1, 6):
            pair = lot0_identity_goldens.synthetic_pair(index, chars_per_message=3600)
            pairs.append({"user": pair[0], "assistant": pair[1]})
        judge_input = mutable_identity_judge_v2.build_judge_input(
            window_pairs=pairs,
            identities={
                "llm": {"static": "Synthetic Frida identity.", "mutable_current": ""},
                "user": {"static": "Synthetic user identity.", "mutable_current": ""},
            },
            mutable_budget={"target_chars": 3000, "max_chars": 3300},
        )
        provider_calls = 0
        original_prompt = mutable_identity_judge_v2.load_prompt_v2
        original_settings = mutable_identity_judge_v2.judge_common.runtime_model_settings
        original_post = mutable_identity_judge_v2.requests.post
        original_url = mutable_identity_judge_v2.llm_client.or_chat_completions_url
        original_headers = mutable_identity_judge_v2.llm_client.or_headers_custom
        original_log_provider = mutable_identity_judge_v2.llm_client.log_provider_metadata

        class FakeResponse:
            def raise_for_status(self) -> None:
                return None

            def json(self) -> dict[str, Any]:
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    lot0_identity_goldens.no_change_contract(),
                                    ensure_ascii=False,
                                )
                            }
                        }
                    ]
                }

        def fake_post(*_args: Any, **_kwargs: Any) -> FakeResponse:
            nonlocal provider_calls
            provider_calls += 1
            return FakeResponse()

        mutable_identity_judge_v2.load_prompt_v2 = lambda _path: "LOT1_SYNTHETIC_JUDGE_PROMPT"
        mutable_identity_judge_v2.judge_common.runtime_model_settings = lambda: {
            "model": "synthetic/judge",
            "temperature": 0.0,
            "top_p": 1.0,
            "max_tokens": 32,
            "timeout_s": 1,
        }
        mutable_identity_judge_v2.requests.post = fake_post
        mutable_identity_judge_v2.llm_client.or_chat_completions_url = lambda: "https://synthetic.invalid"
        mutable_identity_judge_v2.llm_client.or_headers_custom = lambda **_kwargs: {}
        mutable_identity_judge_v2.llm_client.log_provider_metadata = lambda *_args, **_kwargs: None
        try:
            result = mutable_identity_judge_v2.run_mutable_identity_judge_v2(judge_input)
        finally:
            mutable_identity_judge_v2.load_prompt_v2 = original_prompt
            mutable_identity_judge_v2.judge_common.runtime_model_settings = original_settings
            mutable_identity_judge_v2.requests.post = original_post
            mutable_identity_judge_v2.llm_client.or_chat_completions_url = original_url
            mutable_identity_judge_v2.llm_client.or_headers_custom = original_headers
            mutable_identity_judge_v2.llm_client.log_provider_metadata = original_log_provider

        window_chars = sum(
            len(message["content"])
            for pair in pairs
            for message in (pair["user"], pair["assistant"])
        )
        actual = {
            "status": result["status"],
            "window_above_old_limit": window_chars > 32_000,
            "window_within_new_limit": window_chars <= 40_000,
            "provider_calls": provider_calls,
        }
        lot1_identity_liveness_goldens.assert_expanded_guard_acceptance(actual)
        for key, value in (
            ("status", "skipped"),
            ("window_above_old_limit", False),
            ("provider_calls", 0),
        ):
            mutated = dict(actual)
            mutated[key] = value
            with self.assertRaises(AssertionError):
                lot1_identity_liveness_goldens.assert_expanded_guard_acceptance(mutated)

    def test_projection_preserves_wait_retry_terminal_write_recovery_and_completed_states(self) -> None:
        waiting = admin_identity_judge_activity_projection.empty_latest_agent_activity()
        self.assertIsNone(waiting["recovery_action"])
        self.assertIsNone(waiting["processing_state"])
        cases = (
            ("retry_preserve", "transient", "judge_failed", "blocked_retry_pending"),
            (
                "terminal_consume_without_write",
                "deterministic_contract",
                "judge_failed",
                "current_pair_staged",
            ),
            ("apply_recovery", "write_recovery", "write_failed", "blocked_write_recovery"),
            ("completed", "", "completed", "ready_for_next_window"),
        )
        for action, failure_class, processing_state, progress in cases:
            with self.subTest(action=action):
                activity = admin_identity_judge_activity_projection.latest_agent_activity(
                    {
                        "stage": "mutable_identity_judge",
                        "status": "ok" if action == "completed" else "skipped",
                        "payload": {
                            "reason_code": "synthetic_reason",
                            "recovery_action": action,
                            "failure_class": failure_class,
                            "processing_state": processing_state,
                            "attempt_current": 1,
                            "attempt_limit": 2,
                            "window_fingerprint": "0123456789ab",
                            "next_window_progress": progress,
                            "writes_previously_applied": action == "completed",
                        },
                    }
                )
                self.assertEqual(activity["recovery_action"], action)
                self.assertEqual(activity["failure_class"], failure_class or None)
                self.assertEqual(activity["processing_state"], processing_state)
                self.assertEqual(activity["next_window_progress"], progress)
                self.assertEqual(activity["attempt_current"], 1)
                self.assertEqual(activity["attempt_limit"], 2)
                self.assertEqual(activity["writes_previously_applied"], action == "completed")


if __name__ == "__main__":
    unittest.main()
