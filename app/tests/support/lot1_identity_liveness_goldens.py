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
