from __future__ import annotations

import json
from typing import Any


def score_response(case: dict[str, Any], raw_text: str | None, provider_error: str | None) -> dict[str, Any]:
    candidate_ids = [str(candidate["candidate_id"]) for candidate in case.get("candidates", [])]
    expected_keep = set(str(value) for value in case.get("expected_keep_ids", []))
    if provider_error:
        return _empty_score(candidate_ids, expected_keep, provider_error=provider_error)
    if raw_text is None:
        return _empty_score(candidate_ids, expected_keep, provider_error="dry_run")

    try:
        data = _load_json_object(raw_text)
    except Exception as exc:
        return _empty_score(candidate_ids, expected_keep, json_valid=False, schema_valid=False, provider_error=f"json_error:{exc}")

    raw_decisions = data.get("decisions")
    if not isinstance(raw_decisions, list):
        return _empty_score(candidate_ids, expected_keep, json_valid=True, schema_valid=False, provider_error="schema_error:missing_decisions")

    parsed: dict[str, bool] = {}
    schema_valid = True
    for item in raw_decisions:
        if not isinstance(item, dict):
            schema_valid = False
            continue
        candidate_id = str(item.get("candidate_id") or "").strip()
        keep = item.get("keep")
        if candidate_id not in candidate_ids or not isinstance(keep, bool):
            schema_valid = False
            continue
        if not _score_in_range(item.get("semantic_relevance")) or not _score_in_range(item.get("contextual_gain")):
            schema_valid = False
            continue
        redundant = item.get("redundant_with_recent", False)
        if not isinstance(redundant, bool):
            schema_valid = False
            continue
        parsed[candidate_id] = keep

    predicted_keep = {candidate_id for candidate_id, keep in parsed.items() if keep}
    false_positives = sorted(predicted_keep - expected_keep)
    false_negatives = sorted(expected_keep - predicted_keep)
    true_positives = sorted(predicted_keep & expected_keep)
    true_negatives = sorted((set(candidate_ids) - expected_keep) - predicted_keep)
    total = len(candidate_ids)
    accuracy = ((len(true_positives) + len(true_negatives)) / total) if total else 0.0
    weighted_penalty = (2 * len(false_positives)) + len(false_negatives)
    max_weighted_penalty = (2 * (total - len(expected_keep))) + len(expected_keep)
    weighted_score = (
        max(0.0, 100.0 * (1.0 - (weighted_penalty / max_weighted_penalty)))
        if max_weighted_penalty
        else 100.0
    )
    score = accuracy * 100.0
    if not schema_valid:
        weighted_penalty = max_weighted_penalty
        weighted_score = 0.0
        score = 0.0
    return {
        "json_valid": True,
        "schema_valid": schema_valid,
        "candidate_count": total,
        "expected_keep_count": len(expected_keep),
        "predicted_keep_ids": sorted(predicted_keep),
        "true_positives": true_positives,
        "true_negatives": true_negatives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "accuracy": accuracy,
        "weighted_penalty": weighted_penalty,
        "max_weighted_penalty": max_weighted_penalty,
        "weighted_score": weighted_score,
        "score": score,
        "error": None if schema_valid else "schema_error",
    }


def summarize_model(model: str, calls: list[dict[str, Any]]) -> dict[str, Any]:
    count = max(len(calls), 1)
    json_valid = sum(1 for call in calls if call["score"].get("json_valid"))
    schema_valid = sum(1 for call in calls if call["score"].get("schema_valid"))
    provider_errors = sum(1 for call in calls if not call["provider"].get("ok"))
    false_positives = sum(len(call["score"].get("false_positives") or []) for call in calls)
    false_negatives = sum(len(call["score"].get("false_negatives") or []) for call in calls)
    candidate_count = sum(int(call["score"].get("candidate_count") or 0) for call in calls)
    weighted_penalty = sum(int(call["score"].get("weighted_penalty") or 0) for call in calls)
    max_weighted_penalty = sum(int(call["score"].get("max_weighted_penalty") or 0) for call in calls)
    hard_calls = [
        call
        for call in calls
        if call.get("case_difficulty") == "hard" or "hard" in set(call.get("case_tags") or [])
    ]
    hard_weighted_penalty = sum(int(call["score"].get("weighted_penalty") or 0) for call in hard_calls)
    hard_max_weighted_penalty = sum(int(call["score"].get("max_weighted_penalty") or 0) for call in hard_calls)
    correct = sum(
        len(call["score"].get("true_positives") or []) + len(call["score"].get("true_negatives") or [])
        for call in calls
    )
    score = (correct / candidate_count * 100.0) if candidate_count else 0.0
    weighted_score = (
        max(0.0, 100.0 * (1.0 - (weighted_penalty / max_weighted_penalty)))
        if max_weighted_penalty
        else 0.0
    )
    hard_weighted_score = (
        max(0.0, 100.0 * (1.0 - (hard_weighted_penalty / hard_max_weighted_penalty)))
        if hard_max_weighted_penalty
        else weighted_score
    )
    avg_latency = sum(float(call["provider"].get("elapsed_ms") or 0.0) for call in calls) / count
    costs = [call["provider"].get("cost_estimate_usd") for call in calls]
    numeric_costs = [float(cost) for cost in costs if isinstance(cost, (int, float))]
    total_cost = round(sum(numeric_costs), 8) if numeric_costs else None

    json_rate = json_valid / count
    schema_rate = schema_valid / count
    provider_error_rate = provider_errors / count
    verdict = _verdict(weighted_score, schema_rate, provider_error_rate, false_positives, false_negatives)
    notes = _notes(false_positives, false_negatives, provider_errors, schema_rate)
    return {
        "model": model,
        "score": round(score, 3),
        "weighted_score": round(weighted_score, 3),
        "hard_weighted_score": round(hard_weighted_score, 3),
        "weighted_penalty": weighted_penalty,
        "max_weighted_penalty": max_weighted_penalty,
        "json_valid_rate": json_rate,
        "schema_valid_rate": schema_rate,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
        "provider_error_rate": provider_error_rate,
        "avg_latency_ms": round(avg_latency, 3),
        "cost_estimate_usd": total_cost,
        "verdict": verdict,
        "notes": notes,
    }


def rank_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        summaries,
        key=lambda item: (
            -float(item.get("weighted_score") or 0.0),
            int(item.get("false_positives") or 0),
            int(item.get("false_negatives") or 0),
            float(item.get("avg_latency_ms") or 999999.0),
            float(item.get("cost_estimate_usd") if item.get("cost_estimate_usd") is not None else 999999.0),
        ),
    )


def value_rank_summaries(summaries: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        summaries,
        key=lambda item: (
            -float(item.get("weighted_score") or 0.0),
            float(item.get("cost_estimate_usd") if item.get("cost_estimate_usd") is not None else 999999.0),
            float(item.get("avg_latency_ms") or 999999.0),
            int(item.get("false_positives") or 0),
            int(item.get("false_negatives") or 0),
        ),
    )


def campaign_verdict(results: list[dict[str, Any]]) -> dict[str, str]:
    summaries = [result.get("summary") or {} for result in results]
    keepers = [summary for summary in summaries if summary.get("verdict") == "garder"]
    if not keepers:
        testers = [summary for summary in summaries if summary.get("verdict") == "tester plus"]
        if testers:
            return {
                "verdict": "tester plus",
                "summary": "No model is ready to replace the arbiter on this diagnostic set, but at least one deserves another campaign.",
                "next_step": "Broaden arbiter fixtures before any runtime decoupling decision.",
            }
        return {
            "verdict": "exclure",
            "summary": "No candidate met the minimum JSON/schema and keep/drop expectations for the arbiter task.",
            "next_step": "Keep the current production model untouched and improve the suite or candidate list.",
        }

    fastest = min(keepers, key=lambda item: float(item.get("avg_latency_ms") or 0.0))
    cheapest_candidates = [item for item in keepers if isinstance(item.get("cost_estimate_usd"), (int, float))]
    cheapest = min(cheapest_candidates, key=lambda item: float(item["cost_estimate_usd"])) if cheapest_candidates else None
    summary = (
        f"{len(keepers)} model(s) are viable on the diagnostic arbiter fixtures; "
        f"fastest kept model: {fastest.get('model')}."
    )
    if cheapest:
        summary += f" Cheapest estimated kept model: {cheapest.get('model')}."
    return {
        "verdict": "garder",
        "summary": summary,
        "next_step": "Keep production unchanged until the bounded arbiter decoupling lot chooses the caller-local slot.",
    }


def _load_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines:
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end >= start:
        text = text[start : end + 1]
    data = json.loads(text)
    if not isinstance(data, dict):
        raise ValueError("JSON root must be an object")
    return data


def _score_in_range(value: Any) -> bool:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return False
    return 0.0 <= score <= 1.0


def _empty_score(
    candidate_ids: list[str],
    expected_keep: set[str],
    *,
    json_valid: bool = False,
    schema_valid: bool = False,
    provider_error: str | None,
) -> dict[str, Any]:
    return {
        "json_valid": json_valid,
        "schema_valid": schema_valid,
        "candidate_count": len(candidate_ids),
        "expected_keep_count": len(expected_keep),
        "predicted_keep_ids": [],
        "true_positives": [],
        "true_negatives": sorted(set(candidate_ids) - expected_keep),
        "false_positives": [],
        "false_negatives": sorted(expected_keep),
        "accuracy": 0.0,
        "max_weighted_penalty": (2 * (len(candidate_ids) - len(expected_keep))) + len(expected_keep),
        "weighted_penalty": (2 * (len(candidate_ids) - len(expected_keep))) + len(expected_keep),
        "weighted_score": 0.0,
        "score": 0.0,
        "error": provider_error,
    }


def _verdict(score: float, schema_rate: float, provider_error_rate: float, false_positives: int, false_negatives: int) -> str:
    if provider_error_rate >= 0.5 or schema_rate < 0.75:
        return "exclure"
    if schema_rate == 1.0 and score >= 90.0 and false_positives <= 1 and false_negatives <= 1:
        return "garder"
    if score >= 75.0 and provider_error_rate <= 0.25:
        return "tester plus"
    return "exclure"


def _notes(false_positives: int, false_negatives: int, provider_errors: int, schema_rate: float) -> str:
    parts: list[str] = []
    if provider_errors:
        parts.append(f"{provider_errors} provider error(s)")
    if schema_rate < 1.0:
        parts.append("schema issues")
    if false_positives:
        parts.append(f"{false_positives} FP")
    if false_negatives:
        parts.append(f"{false_negatives} FN")
    return ", ".join(parts) if parts else "ok on diagnostic fixtures"
