from __future__ import annotations

from typing import Any, Mapping


def assert_retry_then_progress(actual: Mapping[str, Any]) -> None:
    expected = {
        "first_action": "retry_preserve",
        "second_action": "completed",
        "attempts": [1, 2],
        "attempt_limit": 2,
        "same_window_fingerprint": True,
        "next_window_progress": "current_pair_staged",
        "next_pairs_count": 1,
        "current_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 retry/progression golden changed")


def assert_terminal_progression(actual: Mapping[str, Any]) -> None:
    expected = {
        "failure_class": "transient",
        "action": "terminal_consume_without_write",
        "processing_state": "judge_failed",
        "attempt": 2,
        "attempt_limit": 2,
        "buffer_cleared": True,
        "writes_applied": False,
        "next_window_progress": "current_pair_staged",
        "next_pairs_count": 1,
        "current_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 terminal Identity progression golden changed")


def assert_observability_contract(actual: Mapping[str, Any]) -> None:
    required = {
        "failure_class": "write_recovery",
        "recovery_action": "apply_recovery",
        "processing_state": "write_failed",
        "attempt_current": 1,
        "attempt_limit": 2,
        "window_fingerprint_present": True,
        "next_window_progress": "blocked_write_recovery",
    }
    if dict(actual) != required:
        raise AssertionError("Lot 1 Identity observability golden changed")


def assert_idempotent_write_recovery(actual: Mapping[str, Any]) -> None:
    expected = {
        "canonical_successful_batches": 1,
        "nonempty_audits": 1,
        "canonical_items": 1,
        "current_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 Identity write recovery idempotence changed")


def assert_expanded_guard_acceptance(actual: Mapping[str, Any]) -> None:
    expected = {
        "status": "ok",
        "window_above_old_limit": True,
        "window_within_new_limit": True,
        "provider_calls": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 Identity expanded size guard acceptance changed")


def assert_unverified_write_recovery_terminal(actual: Mapping[str, Any]) -> None:
    expected = {
        "reason_code": "write_recovery_unverified",
        "action": "terminal_consume_without_write",
        "processing_state": "write_failed",
        "writes_applied": False,
        "canonical_items": 0,
        "next_pairs_count": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 unverified Identity write recovery changed")


def assert_http_failure_classes(actual: Mapping[int, str]) -> None:
    expected = {
        401: "deterministic_contract",
        422: "deterministic_contract",
        429: "transient",
        503: "transient",
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 Identity HTTP failure classification changed")


def assert_ambiguous_commit_recovery(actual: Mapping[str, Any]) -> None:
    expected = {
        "judge_calls": 1,
        "canonical_successful_batches": 1,
        "nonempty_audits": 1,
        "reason_code": "write_recovery_completed",
        "action": "completed",
        "judge_status": "not_called",
        "apply_status": "not_called",
        "writes_previously_applied": True,
        "projected_writes_previously_applied": True,
        "next_pairs_count": 1,
        "current_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 ambiguous canonical commit recovery changed")


def assert_crash_before_judge_attempt(actual: Mapping[str, Any]) -> None:
    expected = {
        "pre_crash_status": "buffering",
        "pre_crash_attempt_recorded": False,
        "attempt_current": 1,
        "judge_calls": 1,
        "action": "completed",
        "next_pairs_count": 1,
        "current_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 crash-before-judge attempt accounting changed")


def assert_runtime_safety_retry(actual: Mapping[str, Any]) -> None:
    expected = {
        "reason_code": "runtime_safety_violation",
        "failure_class": "transient",
        "first_action": "retry_preserve",
        "first_attempt": 1,
        "first_buffer_cleared": False,
        "second_action": "terminal_consume_without_write",
        "second_attempt": 2,
        "next_pairs_count": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 runtime safety failure retry policy changed")


def assert_concurrent_window_exclusion(actual: Mapping[str, Any]) -> None:
    expected = {
        "judge_calls": 1,
        "canonical_batches": 1,
        "audit_count": 1,
        "sixth_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 concurrent window exclusion changed")


def assert_compare_and_set_finalization(actual: Mapping[str, Any]) -> None:
    expected = {
        "wrong_status_rejected": True,
        "wrong_owner_rejected": True,
        "late_window_rejected": True,
        "next_pairs_count": 2,
        "sixth_pair_occurrences": 1,
        "seventh_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 staging finalization CAS changed")


def assert_running_crash_recovery(actual: Mapping[str, Any]) -> None:
    expected = {
        "judge_calls": 2,
        "attempt_current": 2,
        "action": "completed",
        "buffer_cleared": True,
        "sixth_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 running-before-judge crash recovery changed")


def assert_terminal_discard_recovery(actual: Mapping[str, Any]) -> None:
    expected = {
        "judge_calls": 2,
        "judge_status": "not_called",
        "apply_status": "not_called",
        "action": "terminal_consume_without_write",
        "seventh_pair_occurrences": 1,
    }
    if dict(actual) != expected:
        raise AssertionError("Lot 1 terminal discard finalization recovery changed")
