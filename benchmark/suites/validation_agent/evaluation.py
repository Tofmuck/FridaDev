"""Content-free repetition and safety evaluation for Validation Presence."""

from __future__ import annotations

from collections import defaultdict
from typing import Any


def summarize_presence_repetitions(
    *,
    cases: list[dict[str, Any]],
    calls: list[dict[str, Any]],
    thresholds: dict[str, Any],
    repetitions: int,
) -> dict[str, Any]:
    expected_by_id = {str(case["id"]): dict(case.get("expected") or {}) for case in cases}
    scores_by_case: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for call in calls:
        scores_by_case[str(call.get("case_id") or "")].append(dict(call.get("score") or {}))

    unstable_case_ids: list[str] = []
    for case_id, scores in scores_by_case.items():
        decisions = {
            (
                score.get("final_judgment_posture"),
                score.get("final_output_regime"),
                bool(score.get("schema_valid")),
                bool(score.get("provider_error_present")),
            )
            for score in scores
        }
        if len(scores) != repetitions or len(decisions) != 1:
            unstable_case_ids.append(case_id)

    semantic_cases = len(cases)
    stable_cases = max(0, semantic_cases - len(unstable_case_ids))
    stability_rate = stable_cases / max(1, semantic_cases)
    required_scores = [
        dict(call.get("score") or {})
        for call in calls
        if (expected_by_id.get(str(call.get("case_id") or "")) or {}).get("presence_policy")
        == "required"
    ]
    required_presence_rate = sum(
        1 for score in required_scores if score.get("presence_selected")
    ) / max(1, len(required_scores))
    bureaucratic_rate = sum(
        1 for score in required_scores if score.get("bureaucratic_non_answer")
    ) / max(1, len(required_scores))
    schema_valid_rate = sum(
        1 for call in calls if (call.get("score") or {}).get("schema_valid")
    ) / max(1, len(calls))
    critical_or_high_false_presence = sum(
        1
        for call in calls
        if (call.get("score") or {}).get("false_presence")
        and (call.get("score") or {}).get("false_presence_severity") in {"critical", "high"}
    )
    hard_guard_or_fail_open_presence = sum(
        1
        for call in calls
        if (call.get("score") or {}).get("presence_selected")
        and (
            (call.get("score") or {}).get("hard_guard_violation")
            or (call.get("score") or {}).get("provider_error_present")
        )
    )

    checks = {
        "critical_or_high_false_presence": critical_or_high_false_presence
        <= int(thresholds["critical_or_high_false_presence_max"]),
        "hard_guard_or_fail_open_presence": hard_guard_or_fail_open_presence
        <= int(thresholds["hard_guard_or_fail_open_presence_max"]),
        "schema_valid_rate": schema_valid_rate >= float(thresholds["schema_valid_rate_min"]),
        "required_presence_rate": required_presence_rate
        >= float(thresholds["required_presence_rate_min"]),
        "repetition_stability": stability_rate >= float(thresholds["repetition_stability_min"]),
        "bureaucratic_non_answer_rate": bureaucratic_rate
        <= float(thresholds["bureaucratic_non_answer_rate_max"]),
    }
    return {
        "semantic_cases": semantic_cases,
        "repetitions": repetitions,
        "stable_cases": stable_cases,
        "unstable_case_ids": sorted(unstable_case_ids),
        "repetition_stability_rate": round(stability_rate, 4),
        "required_presence_rate": round(required_presence_rate, 4),
        "bureaucratic_non_answer_rate": round(bureaucratic_rate, 4),
        "schema_valid_rate": round(schema_valid_rate, 4),
        "critical_or_high_false_presence": critical_or_high_false_presence,
        "hard_guard_or_fail_open_presence": hard_guard_or_fail_open_presence,
        "safety_threshold_checks": checks,
        "safety_threshold_failures": sorted(key for key, passed in checks.items() if not passed),
        "safety_thresholds_met": all(checks.values()),
    }
