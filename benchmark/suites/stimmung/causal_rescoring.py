from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import statistics
from typing import Any, Mapping, Sequence

from benchmark.suites.stimmung import dialogic_campaign, dialogic_semantics


ARTIFACT_VERSION = "lot4c2_stimmung_causal_rescoring_v1"
DEFAULT_OUTPUT = "2026-08-30-lot4c2-stimmung-causal-rescoring.jsonl"

_CAMPAIGNS = (
    (
        "lot4s1_current",
        "2026-08-30-lot4s1-stimmung-primary-fallback.jsonl",
        "97b5d53548c15b045593bc1f9c897f50f88d1553f05e9a75d0fdf4ceaa23467e",
    ),
    (
        "strengthening_candidate",
        "2026-08-30-lot4c2-stimmung-strengthening-candidate.jsonl",
        "637cbc1fac2b03378f451d6fc64f6b0c30b7d9cd183b59b5833e3ee62612c5c5",
    ),
    (
        "gemini_3_7_medium_max800",
        "2026-08-30-lot4c2-stimmung-gemini-3-7-medium-max800.jsonl",
        "1b6112ceea8d6065aabd34f579f64ccfe652f514b5187cd0d2c3da542ebf11fd",
    ),
    (
        "sonnet_5_medium",
        "2026-08-30-lot4c2-stimmung-sonnet-5-medium.jsonl",
        "3f4da100e9c9553d64bdf44b379a02921297f6984e506b359a40891db4f4ad46",
    ),
)
_SOURCES = ("primary", "fallback")
_CLASSIFICATIONS = frozenset({"pass", "fail", "inconclusive"})
_LOCAL_DECISIONS = frozenset({"eligible", "not_eligible", "inconclusive"})
_AGGREGATE_ATTRIBUTIONS = frozenset(
    {
        "not_applicable",
        "inconclusive",
        "bounded_to_scored_contributors",
        "not_attributable_unscored_contributors",
    }
)
_COVERAGE = frozenset({"complete", "partial"})
_LOCAL_REASON_CODES = frozenset(
    {
        "signal_false_negative",
        "signal_false_positive",
        "dominant_tone_outside_allowed",
        "irony_literalized",
        "quoted_affect_internalized",
        "reported_affect_internalized",
        "signal_tone_forbidden",
        "signal_overcoded",
        "strength_outside_allowed",
        "observation_order_invalid",
        "mixed_sources",
        "observation_schema_invalid",
        "execution_status_invalid",
        "source_invalid",
        "fail_open_not_semantic_success",
        "caller_result_unavailable",
        "signal_schema_invalid",
    }
)
_AGGREGATE_REASON_CODES = frozenset(
    {
        "aggregate_presence_mismatch",
        "aggregate_dominant_outside_allowed",
        "aggregate_overcoded",
        "trajectory_stability_mismatch",
        "trajectory_shift_mismatch",
        "aggregate_turn_count_mismatch",
        "aggregate_decay_mismatch",
        "observation_order_invalid",
        "mixed_sources",
        "observation_schema_invalid",
        "execution_status_invalid",
        "source_invalid",
        "fail_open_not_semantic_success",
        "caller_result_unavailable",
        "aggregate_schema_invalid",
    }
)
_FINAL_REASON_CODES = frozenset(
    {
        "combined_scores_preserved",
        "prompt_candidate_residual_local_failures",
        "model_candidates_do_not_meet_local_threshold",
        "aggregate_failures_not_causally_attributable",
        "gpt_5_2_not_required_by_current_evidence",
    }
)

_DIALOGUE_KEYS = {
    "artifact_version",
    "record_type",
    "campaign_id",
    "source_artifact_sha256",
    "protocol_version",
    "source",
    "requested_model",
    "repetition",
    "dialogue_id",
    "families",
    "caller_local_semantics",
    "aggregate_trajectory",
    "combined_pipeline",
    "historical_combined_match",
    "window_provenance",
    "aggregate_causal_attribution",
}
_SCORE_KEYS = {"classification", "error_class", "reason_codes"}
_WINDOW_KEYS = {
    "evaluated_turn_id",
    "contributor_turn_ids",
    "active_signal_turn_ids",
    "evaluated_contributor_count",
    "unevaluated_contributor_count",
    "technical_contributor_count",
    "local_expectation_coverage",
}
_SUMMARY_KEYS = {
    "artifact_version",
    "record_type",
    "campaign_id",
    "source_artifact_sha256",
    "protocol_version",
    "source",
    "requested_model",
    "call_count",
    "dialogue_score_count",
    "caller_local_counts",
    "aggregate_trajectory_counts",
    "combined_pipeline_counts",
    "failure_partition",
    "caller_local_reason_counts",
    "aggregate_reason_counts",
    "aggregate_causal_attribution_counts",
    "caller_local_repetition_agreement_count",
    "aggregate_repetition_agreement_count",
    "combined_repetition_agreement_count",
    "reproducible_caller_local_failure_ids",
    "reproducible_aggregate_failure_ids",
    "technical_status_counts",
    "metrics_complete",
    "latency_median_ms",
    "latency_p95_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost_usd",
    "caller_local_decision",
}
_FINAL_KEYS = {
    "artifact_version",
    "record_type",
    "dialogue_rescore_count",
    "configuration_summary_count",
    "historical_artifacts_preserved",
    "prompt_strengthening_primary_local_decision",
    "prompt_strengthening_fallback_local_decision",
    "sonnet_local_decision",
    "gemini_local_decision",
    "sonnet_model_change_support",
    "gemini_model_change_support",
    "gpt_5_2_trial_status",
    "reason_codes",
}


def _score_result(
    case: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    families = sorted(set(case.get("families") or []))
    return {
        "dialogue_id": case.get("id"),
        "families": families,
        "classification": "pass",
        "error_class": "none",
        "reason_codes": [],
        "evaluated_turns": len(observations),
        "source": "unknown",
    }


def _inconclusive(
    result: Mapping[str, Any], error_class: str, reason: str
) -> dict[str, Any]:
    return {
        **result,
        "classification": "inconclusive",
        "error_class": error_class,
        "reason_codes": [reason],
    }


def _semantic_failure(
    result: Mapping[str, Any], reasons: Sequence[str]
) -> dict[str, Any]:
    unique_reasons = sorted(set(reasons))
    if not unique_reasons:
        return dict(result)
    return {
        **result,
        "classification": "fail",
        "error_class": "semantic",
        "reason_codes": unique_reasons,
    }


def score_dialogue_levels(
    case: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    expected_turns = [
        turn
        for turn in case.get("turns", [])
        if isinstance(turn, Mapping) and "expectation" in turn
    ]
    expected_ids = [turn["turn_id"] for turn in expected_turns]
    observed_ids = [
        item.get("turn_id") for item in observations if isinstance(item, Mapping)
    ]
    local_result = _score_result(case, observations)
    aggregate_result = _score_result(case, observations)

    def inconclusive_all(error_class: str, reason: str) -> dict[str, dict[str, Any]]:
        local = _inconclusive(local_result, error_class, reason)
        aggregate = _inconclusive(aggregate_result, error_class, reason)
        return {
            "caller_local_semantics": local,
            "aggregate_trajectory": aggregate,
            "combined_pipeline": dialogic_semantics.score_dialogue(
                case, observations
            ),
        }

    if observed_ids != expected_ids:
        return inconclusive_all("schema", "observation_order_invalid")
    sources = {item.get("source") for item in observations}
    if len(sources) != 1:
        return inconclusive_all("schema", "mixed_sources")
    source = next(iter(sources), "unknown")
    local_result["source"] = source
    aggregate_result["source"] = source

    local_reasons: list[str] = []
    aggregate_reasons: list[str] = []
    local_inconclusive: tuple[str, str] | None = None
    aggregate_inconclusive: tuple[str, str] | None = None
    previous_aggregate_strength: int | None = None
    for expected_turn, observation in zip(expected_turns, observations):
        if set(observation.keys()) != dialogic_semantics._OBSERVATION_KEYS:
            return inconclusive_all("schema", "observation_schema_invalid")
        status = observation.get("execution_status")
        if status not in dialogic_semantics._EXECUTION_STATUSES:
            return inconclusive_all("schema", "execution_status_invalid")
        if observation.get("source") not in {"primary", "fallback"}:
            return inconclusive_all("schema", "source_invalid")
        if status != "ok":
            code = (
                "fail_open_not_semantic_success"
                if status == "fail_open"
                else "caller_result_unavailable"
            )
            return inconclusive_all("execution", code)

        expectation = expected_turn["expectation"]
        signal = observation.get("signal")
        signal_state = "absent"
        if signal is not None:
            if (
                not isinstance(signal, Mapping)
                or dialogic_semantics._validate_normalized_signal_payload(signal)
            ):
                local_inconclusive = ("schema", "signal_schema_invalid")
            else:
                signal_state = "present" if signal["present"] else "empty"
        if local_inconclusive is None:
            allowed_states = set(expectation["allowed_signal_states"])
            if signal_state not in allowed_states:
                local_reasons.append(
                    "signal_false_negative"
                    if "present" in allowed_states
                    else "signal_false_positive"
                )
            if signal_state == "present" and isinstance(signal, Mapping):
                tones = {
                    item["tone"]: int(item["strength"])
                    for item in signal["tones"]
                }
                dominant = signal["dominant_tone"]
                current_strength = max(tones.values()) if tones else None
                if dominant not in expectation["allowed_dominant_tones"]:
                    local_reasons.append("dominant_tone_outside_allowed")
                if not set(tones) & set(expectation["allowed_tones"]):
                    local_reasons.append("signal_false_negative")
                if set(tones) & set(expectation["forbidden_tones"]):
                    local_reasons.append(
                        dialogic_semantics._forbidden_tone_reason(
                            expectation["semantic_context"]
                        )
                    )
                if set(tones) - set(expectation["allowed_tones"]):
                    local_reasons.append("signal_overcoded")
                minimum, maximum = expectation["strength_range"]
                if (
                    current_strength is None
                    or not minimum <= current_strength <= maximum
                ):
                    local_reasons.append("strength_outside_allowed")

        aggregate = observation.get("aggregate")
        aggregate_error = dialogic_semantics._aggregate_schema_error(aggregate)
        if aggregate_error:
            aggregate_inconclusive = ("schema", aggregate_error)
            continue
        aggregate_expectation = expectation["aggregate"]
        aggregate_strength = max(
            (int(item["strength"]) for item in aggregate["active_tones"]),
            default=None,
        )
        if aggregate["present"] not in aggregate_expectation["allowed_presence"]:
            aggregate_reasons.append("aggregate_presence_mismatch")
        if aggregate["present"]:
            active_names = {item["tone"] for item in aggregate["active_tones"]}
            if (
                aggregate["dominant_tone"]
                not in aggregate_expectation["allowed_dominant_tones"]
            ):
                aggregate_reasons.append("aggregate_dominant_outside_allowed")
            if active_names - set(aggregate_expectation["allowed_active_tones"]):
                aggregate_reasons.append("aggregate_overcoded")
            if aggregate["stability"] not in aggregate_expectation["allowed_stability"]:
                aggregate_reasons.append("trajectory_stability_mismatch")
            if (
                aggregate["shift_state"]
                not in aggregate_expectation["allowed_shift_states"]
            ):
                aggregate_reasons.append("trajectory_shift_mismatch")
            expected_count = min(
                int(expected_turn["turn_id"]),
                dialogic_semantics.AGGREGATE_MAX_SIGNALS,
            )
            if aggregate["turns_considered"] != expected_count:
                aggregate_reasons.append("aggregate_turn_count_mismatch")
        if (
            aggregate_expectation["decay_required"]
            and previous_aggregate_strength is not None
            and aggregate_strength is not None
            and aggregate_strength >= previous_aggregate_strength
        ):
            aggregate_reasons.append("aggregate_decay_mismatch")
        if aggregate_strength is not None:
            previous_aggregate_strength = aggregate_strength

    local = (
        _inconclusive(local_result, *local_inconclusive)
        if local_inconclusive is not None
        else _semantic_failure(local_result, local_reasons)
    )
    aggregate = (
        _inconclusive(aggregate_result, *aggregate_inconclusive)
        if aggregate_inconclusive is not None
        else _semantic_failure(aggregate_result, aggregate_reasons)
    )
    combined = dialogic_semantics.score_dialogue(case, observations)
    return {
        "caller_local_semantics": local,
        "aggregate_trajectory": aggregate,
        "combined_pipeline": combined,
    }


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(repo_root: Path, filename: str) -> Path:
    return repo_root / "benchmark" / "results" / "stimmung" / filename


def _load_and_validate_source(
    repo_root: Path,
    filename: str,
    expected_sha256: str,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    path = _artifact_path(repo_root, filename)
    if _sha256_file(path) != expected_sha256:
        raise ValueError("historical_artifact_fingerprint_mismatch")
    records = dialogic_campaign.load_jsonl(path)
    calls = [item for item in records if item.get("record_type") == "call"]
    if not calls:
        raise ValueError("historical_calls_missing")
    freeze_commit = str(calls[0].get("freeze_commit") or "")
    protocol_version = str(calls[0].get("protocol_version") or "")
    if protocol_version == dialogic_campaign.PROTOCOL_VERSION:
        protocol = dialogic_campaign.build_protocol(
            repo_root, freeze_commit=freeze_commit
        )
        dialogic_campaign.validate_artifact(records, repo_root, protocol)
    elif protocol_version == dialogic_campaign.STRENGTHENING_PROTOCOL_VERSION:
        protocol = dialogic_campaign.build_strengthening_protocol(
            repo_root, freeze_commit=freeze_commit
        )
        dialogic_campaign.validate_artifact(records, repo_root, protocol)
    elif protocol_version == dialogic_campaign.TOKEN_CAP_RERUN_PROTOCOL_VERSION:
        protocol = dialogic_campaign.build_token_cap_rerun_protocol(
            repo_root, freeze_commit=freeze_commit
        )
        dialogic_campaign.validate_token_cap_rerun_artifact(
            records, repo_root, protocol
        )
    elif protocol_version == dialogic_campaign.SONNET_CANDIDATE_PROTOCOL_VERSION:
        protocol = dialogic_campaign.build_sonnet_candidate_protocol(
            repo_root, freeze_commit=freeze_commit
        )
        dialogic_campaign.validate_sonnet_candidate_artifact(
            records, repo_root, protocol
        )
    else:
        raise ValueError("historical_protocol_unknown")
    return records, protocol


def _score_view(score: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "classification": str(score["classification"]),
        "error_class": str(score["error_class"]),
        "reason_codes": list(score["reason_codes"]),
    }


def _is_active_signal(call: Mapping[str, Any]) -> bool:
    signal = call.get("signal")
    return (
        call.get("status") == "ok"
        and isinstance(signal, Mapping)
        and signal.get("present") is True
    )


def _window_provenance(
    calls: Sequence[Mapping[str, Any]],
    *,
    evaluated_turn_ids: set[int],
) -> list[dict[str, Any]]:
    windows: list[dict[str, Any]] = []
    for current_index, current in enumerate(calls):
        if current.get("evaluated") is not True:
            continue
        scanned: list[Mapping[str, Any]] = []
        active_count = 0
        for candidate in reversed(calls[: current_index + 1]):
            scanned.append(candidate)
            if _is_active_signal(candidate):
                active_count += 1
                if active_count >= dialogic_semantics.AGGREGATE_MAX_SIGNALS:
                    break
            if candidate is current and not _is_active_signal(candidate):
                break
        contributors = sorted(int(item["turn_id"]) for item in scanned)
        active = sorted(
            int(item["turn_id"]) for item in scanned if _is_active_signal(item)
        )
        aggregate = current.get("aggregate")
        if not isinstance(aggregate, Mapping):
            raise ValueError("historical_aggregate_missing")
        if aggregate.get("present") is True:
            if int(aggregate.get("turns_considered") or -1) != len(active):
                raise ValueError("aggregate_provenance_count_mismatch")
        elif active:
            raise ValueError("aggregate_provenance_presence_mismatch")
        evaluated_count = sum(turn_id in evaluated_turn_ids for turn_id in contributors)
        unevaluated_count = len(contributors) - evaluated_count
        windows.append(
            {
                "evaluated_turn_id": int(current["turn_id"]),
                "contributor_turn_ids": contributors,
                "active_signal_turn_ids": active,
                "evaluated_contributor_count": evaluated_count,
                "unevaluated_contributor_count": unevaluated_count,
                "technical_contributor_count": sum(
                    item.get("status") != "ok" for item in scanned
                ),
                "local_expectation_coverage": (
                    "complete" if unevaluated_count == 0 else "partial"
                ),
            }
        )
    return windows


def _aggregate_attribution(
    aggregate_score: Mapping[str, Any],
    windows: Sequence[Mapping[str, Any]],
) -> str:
    classification = aggregate_score.get("classification")
    if classification == "pass":
        return "not_applicable"
    if classification == "inconclusive":
        return "inconclusive"
    if any(int(item["unevaluated_contributor_count"]) > 0 for item in windows):
        return "not_attributable_unscored_contributors"
    return "bounded_to_scored_contributors"


def _observations(calls: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "turn_id": int(item["turn_id"]),
            "execution_status": str(item["status"]),
            "source": str(item["source"]),
            "signal": item.get("signal"),
            "aggregate": item.get("aggregate"),
        }
        for item in calls
        if item.get("evaluated") is True
    ]


def _historical_score_map(
    records: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int, str], Mapping[str, Any]]:
    return {
        (str(item["source"]), int(item["repetition"]), str(item["dialogue_id"])): item
        for item in records
        if item.get("record_type") == "dialogue_score"
    }


def _dialogue_records(
    *,
    repo_root: Path,
    campaign_id: str,
    source_sha256: str,
    records: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    corpus = dialogic_semantics.load_corpus(repo_root)
    cases = {str(item["id"]): item for item in corpus["dialogues"]}
    calls = [item for item in records if item.get("record_type") == "call"]
    historical_scores = _historical_score_map(records)
    result: list[dict[str, Any]] = []
    sources = [source for source in _SOURCES if any(item.get("source") == source for item in calls)]
    for source in sources:
        for repetition in (1, 2):
            for dialogue_id, case in cases.items():
                grouped_calls = [
                    item
                    for item in calls
                    if item.get("source") == source
                    and int(item.get("repetition") or 0) == repetition
                    and item.get("dialogue_id") == dialogue_id
                ]
                if len(grouped_calls) != len(case["turns"]):
                    raise ValueError("historical_dialogue_calls_incomplete")
                levels = score_dialogue_levels(case, _observations(grouped_calls))
                combined = levels["combined_pipeline"]
                historical = historical_scores.get((source, repetition, dialogue_id))
                if historical is None:
                    raise ValueError("historical_dialogue_score_missing")
                historical_match = all(
                    historical.get(key) == combined.get(key)
                    for key in (
                        "dialogue_id",
                        "families",
                        "source",
                        "classification",
                        "error_class",
                        "reason_codes",
                        "evaluated_turns",
                    )
                )
                if not historical_match:
                    mismatched_keys = [
                        key
                        for key in (
                            "dialogue_id",
                            "families",
                            "source",
                            "classification",
                            "error_class",
                            "reason_codes",
                            "evaluated_turns",
                        )
                        if historical.get(key) != combined.get(key)
                    ]
                    raise ValueError(
                        "historical_combined_score_changed:"
                        f"{campaign_id}:{source}:{repetition}:{dialogue_id}:"
                        f"{','.join(mismatched_keys)}"
                    )
                requested_models = {
                    str(item.get("requested_model") or "") for item in grouped_calls
                }
                if len(requested_models) != 1:
                    raise ValueError("historical_requested_model_mixed")
                evaluated_ids = {
                    int(turn["turn_id"])
                    for turn in case["turns"]
                    if "expectation" in turn
                }
                windows = _window_provenance(
                    grouped_calls,
                    evaluated_turn_ids=evaluated_ids,
                )
                result.append(
                    {
                        "artifact_version": ARTIFACT_VERSION,
                        "record_type": "dialogue_rescore",
                        "campaign_id": campaign_id,
                        "source_artifact_sha256": source_sha256,
                        "protocol_version": str(protocol["protocol_version"]),
                        "source": source,
                        "requested_model": next(iter(requested_models)),
                        "repetition": repetition,
                        "dialogue_id": dialogue_id,
                        "families": list(case["families"]),
                        "caller_local_semantics": _score_view(
                            levels["caller_local_semantics"]
                        ),
                        "aggregate_trajectory": _score_view(
                            levels["aggregate_trajectory"]
                        ),
                        "combined_pipeline": _score_view(combined),
                        "historical_combined_match": True,
                        "window_provenance": windows,
                        "aggregate_causal_attribution": _aggregate_attribution(
                            levels["aggregate_trajectory"], windows
                        ),
                    }
                )
    return result


def decide_local_semantics(
    scores: Sequence[Mapping[str, Any]],
    *,
    expected_count: int,
) -> str:
    if len(scores) != expected_count:
        return "inconclusive"
    classifications = [item.get("classification") for item in scores]
    if any(item not in _CLASSIFICATIONS for item in classifications):
        return "inconclusive"
    if any(item == "inconclusive" for item in classifications):
        return "inconclusive"
    if any(item == "fail" for item in classifications):
        return "not_eligible"
    return "eligible"


def _classification_counts(
    items: Sequence[Mapping[str, Any]], key: str
) -> dict[str, int]:
    counter = Counter(str(item[key]["classification"]) for item in items)
    return {name: int(counter.get(name, 0)) for name in ("pass", "fail", "inconclusive")}


def _reason_counts(
    items: Sequence[Mapping[str, Any]], key: str
) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        counter.update(str(code) for code in item[key]["reason_codes"])
    return dict(sorted(counter.items()))


def _failure_partition(items: Sequence[Mapping[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in items:
        local = item["caller_local_semantics"]["classification"]
        aggregate = item["aggregate_trajectory"]["classification"]
        if "inconclusive" in {local, aggregate}:
            counter["inconclusive"] += 1
        elif local == "pass" and aggregate == "pass":
            counter["full_pass"] += 1
        elif local == "pass":
            counter["aggregate_only"] += 1
        elif aggregate == "pass":
            counter["caller_only"] += 1
        else:
            counter["caller_and_aggregate"] += 1
    return {
        name: int(counter.get(name, 0))
        for name in (
            "full_pass",
            "aggregate_only",
            "caller_only",
            "caller_and_aggregate",
            "inconclusive",
        )
    }


def _agreement_count(items: Sequence[Mapping[str, Any]], key: str) -> int:
    by_dialogue: dict[str, dict[int, tuple[str, tuple[str, ...]]]] = {}
    for item in items:
        score = item[key]
        by_dialogue.setdefault(str(item["dialogue_id"]), {})[
            int(item["repetition"])
        ] = (
            str(score["classification"]),
            tuple(str(code) for code in score["reason_codes"]),
        )
    return sum(
        set(repetitions) == {1, 2} and repetitions[1] == repetitions[2]
        for repetitions in by_dialogue.values()
    )


def _reproducible_failure_ids(
    items: Sequence[Mapping[str, Any]], key: str
) -> list[str]:
    by_dialogue: dict[str, dict[int, Mapping[str, Any]]] = {}
    for item in items:
        by_dialogue.setdefault(str(item["dialogue_id"]), {})[
            int(item["repetition"])
        ] = item[key]
    result: list[str] = []
    for dialogue_id, repetitions in by_dialogue.items():
        if set(repetitions) != {1, 2}:
            continue
        left = repetitions[1]
        right = repetitions[2]
        shared = set(left["reason_codes"]) & set(right["reason_codes"])
        if left["classification"] == right["classification"] == "fail" and shared:
            result.append(dialogue_id)
    return sorted(result)


def _sum_complete(calls: Sequence[Mapping[str, Any]], key: str) -> int | None:
    values = [item.get(key) for item in calls]
    if not values or any(value is None or isinstance(value, bool) for value in values):
        return None
    return sum(int(value) for value in values)


def _cost_complete(calls: Sequence[Mapping[str, Any]]) -> float | None:
    values = [item.get("cost_usd") for item in calls]
    if not values or any(value is None or isinstance(value, bool) for value in values):
        return None
    return round(sum(float(value) for value in values), 8)


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(
        0,
        min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1),
    )
    return round(float(ordered[index]), 3)


def _configuration_summary(
    *,
    campaign_id: str,
    source_sha256: str,
    protocol_version: str,
    source: str,
    calls: Sequence[Mapping[str, Any]],
    dialogue_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    requested_models = {str(item.get("requested_model") or "") for item in calls}
    if len(requested_models) != 1:
        raise ValueError("historical_requested_model_mixed")
    local_scores = [item["caller_local_semantics"] for item in dialogue_records]
    latencies = [
        float(item["latency_ms"])
        for item in calls
        if item.get("latency_ms") is not None
    ]
    metrics_complete = bool(calls) and all(
        item.get("latency_ms") is not None
        and item.get("prompt_tokens") is not None
        and item.get("completion_tokens") is not None
        and item.get("total_tokens") is not None
        and item.get("cost_usd") is not None
        for item in calls
    )
    technical_complete = len(calls) == 138 and all(
        item.get("status") == "ok" for item in calls
    )
    attribution_counter = Counter(
        str(item["aggregate_causal_attribution"]) for item in dialogue_records
    )
    return {
        "artifact_version": ARTIFACT_VERSION,
        "record_type": "configuration_summary",
        "campaign_id": campaign_id,
        "source_artifact_sha256": source_sha256,
        "protocol_version": protocol_version,
        "source": source,
        "requested_model": next(iter(requested_models)),
        "call_count": len(calls),
        "dialogue_score_count": len(dialogue_records),
        "caller_local_counts": _classification_counts(
            dialogue_records, "caller_local_semantics"
        ),
        "aggregate_trajectory_counts": _classification_counts(
            dialogue_records, "aggregate_trajectory"
        ),
        "combined_pipeline_counts": _classification_counts(
            dialogue_records, "combined_pipeline"
        ),
        "failure_partition": _failure_partition(dialogue_records),
        "caller_local_reason_counts": _reason_counts(
            dialogue_records, "caller_local_semantics"
        ),
        "aggregate_reason_counts": _reason_counts(
            dialogue_records, "aggregate_trajectory"
        ),
        "aggregate_causal_attribution_counts": dict(
            sorted(attribution_counter.items())
        ),
        "caller_local_repetition_agreement_count": _agreement_count(
            dialogue_records, "caller_local_semantics"
        ),
        "aggregate_repetition_agreement_count": _agreement_count(
            dialogue_records, "aggregate_trajectory"
        ),
        "combined_repetition_agreement_count": _agreement_count(
            dialogue_records, "combined_pipeline"
        ),
        "reproducible_caller_local_failure_ids": _reproducible_failure_ids(
            dialogue_records, "caller_local_semantics"
        ),
        "reproducible_aggregate_failure_ids": _reproducible_failure_ids(
            dialogue_records, "aggregate_trajectory"
        ),
        "technical_status_counts": dict(
            sorted(Counter(str(item["status"]) for item in calls).items())
        ),
        "metrics_complete": metrics_complete,
        "latency_median_ms": (
            round(statistics.median(latencies), 3)
            if len(latencies) == len(calls)
            else None
        ),
        "latency_p95_ms": (
            _percentile(latencies, 0.95)
            if len(latencies) == len(calls)
            else None
        ),
        "prompt_tokens": _sum_complete(calls, "prompt_tokens"),
        "completion_tokens": _sum_complete(calls, "completion_tokens"),
        "total_tokens": _sum_complete(calls, "total_tokens"),
        "cost_usd": _cost_complete(calls),
        "caller_local_decision": (
            decide_local_semantics(local_scores, expected_count=32)
            if technical_complete
            else "inconclusive"
        ),
    }


def build_rescoring_records(repo_root: Path) -> list[dict[str, Any]]:
    repo_root = Path(repo_root).resolve()
    records: list[dict[str, Any]] = []
    summaries: list[dict[str, Any]] = []
    for campaign_id, filename, expected_sha256 in _CAMPAIGNS:
        source_records, protocol = _load_and_validate_source(
            repo_root, filename, expected_sha256
        )
        source_sha256 = _sha256_file(_artifact_path(repo_root, filename))
        campaign_dialogues = _dialogue_records(
            repo_root=repo_root,
            campaign_id=campaign_id,
            source_sha256=source_sha256,
            records=source_records,
            protocol=protocol,
        )
        records.extend(campaign_dialogues)
        calls = [item for item in source_records if item.get("record_type") == "call"]
        for source in _SOURCES:
            source_calls = [item for item in calls if item.get("source") == source]
            if not source_calls:
                continue
            source_dialogues = [
                item for item in campaign_dialogues if item["source"] == source
            ]
            summary = _configuration_summary(
                campaign_id=campaign_id,
                source_sha256=source_sha256,
                protocol_version=str(protocol["protocol_version"]),
                source=source,
                calls=source_calls,
                dialogue_records=source_dialogues,
            )
            summaries.append(summary)
            records.append(summary)

    by_key = {
        (item["campaign_id"], item["source"]): item for item in summaries
    }
    prompt_primary = by_key[("strengthening_candidate", "primary")]
    prompt_fallback = by_key[("strengthening_candidate", "fallback")]
    sonnet = by_key[("sonnet_5_medium", "primary")]
    gemini = by_key[("gemini_3_7_medium_max800", "primary")]
    records.append(
        {
            "artifact_version": ARTIFACT_VERSION,
            "record_type": "final_summary",
            "dialogue_rescore_count": sum(
                item["record_type"] == "dialogue_rescore" for item in records
            ),
            "configuration_summary_count": len(summaries),
            "historical_artifacts_preserved": True,
            "prompt_strengthening_primary_local_decision": prompt_primary[
                "caller_local_decision"
            ],
            "prompt_strengthening_fallback_local_decision": prompt_fallback[
                "caller_local_decision"
            ],
            "sonnet_local_decision": sonnet["caller_local_decision"],
            "gemini_local_decision": gemini["caller_local_decision"],
            "sonnet_model_change_support": "not_supported",
            "gemini_model_change_support": "not_supported",
            "gpt_5_2_trial_status": "not_required_by_current_evidence",
            "reason_codes": [
                "combined_scores_preserved",
                "prompt_candidate_residual_local_failures",
                "model_candidates_do_not_meet_local_threshold",
                "aggregate_failures_not_causally_attributable",
                "gpt_5_2_not_required_by_current_evidence",
            ],
        }
    )
    return records


def _validate_score(value: Any, allowed_reasons: frozenset[str]) -> None:
    if not isinstance(value, Mapping) or set(value) != _SCORE_KEYS:
        raise ValueError("rescore_score_schema_invalid")
    if value.get("classification") not in _CLASSIFICATIONS:
        raise ValueError("rescore_classification_invalid")
    if value.get("error_class") not in {"none", "semantic", "schema", "execution"}:
        raise ValueError("rescore_error_class_invalid")
    reasons = value.get("reason_codes")
    if (
        not isinstance(reasons, list)
        or len(reasons) != len(set(reasons))
        or any(reason not in allowed_reasons for reason in reasons)
    ):
        raise ValueError("rescore_reason_codes_invalid")
    if value["classification"] == "pass" and reasons:
        raise ValueError("rescore_false_pass")
    if value["classification"] != "pass" and not reasons:
        raise ValueError("rescore_reason_missing")


def _validate_record_shape(record: Mapping[str, Any]) -> None:
    record_type = record.get("record_type")
    if record.get("artifact_version") != ARTIFACT_VERSION:
        raise ValueError("rescore_artifact_version_invalid")
    if record_type == "dialogue_rescore":
        if set(record) != _DIALOGUE_KEYS:
            raise ValueError("rescore_dialogue_schema_invalid")
        _validate_score(record["caller_local_semantics"], _LOCAL_REASON_CODES)
        _validate_score(record["aggregate_trajectory"], _AGGREGATE_REASON_CODES)
        _validate_score(
            record["combined_pipeline"],
            _LOCAL_REASON_CODES | _AGGREGATE_REASON_CODES,
        )
        if record.get("historical_combined_match") is not True:
            raise ValueError("historical_combined_score_changed")
        if record.get("aggregate_causal_attribution") not in _AGGREGATE_ATTRIBUTIONS:
            raise ValueError("aggregate_causal_attribution_invalid")
        windows = record.get("window_provenance")
        if not isinstance(windows, list) or not windows:
            raise ValueError("aggregate_window_provenance_missing")
        for window in windows:
            if not isinstance(window, Mapping) or set(window) != _WINDOW_KEYS:
                raise ValueError("aggregate_window_provenance_invalid")
            contributors = window.get("contributor_turn_ids")
            active = window.get("active_signal_turn_ids")
            if (
                not isinstance(contributors, list)
                or not contributors
                or contributors != sorted(set(contributors))
                or not isinstance(active, list)
                or active != sorted(set(active))
                or not set(active).issubset(contributors)
                or window.get("local_expectation_coverage") not in _COVERAGE
            ):
                raise ValueError("aggregate_window_provenance_invalid")
            if int(window["evaluated_contributor_count"]) + int(
                window["unevaluated_contributor_count"]
            ) != len(contributors):
                raise ValueError("aggregate_window_provenance_count_invalid")
    elif record_type == "configuration_summary":
        if set(record) != _SUMMARY_KEYS:
            raise ValueError("rescore_summary_schema_invalid")
        if record.get("caller_local_decision") not in _LOCAL_DECISIONS:
            raise ValueError("rescore_local_decision_invalid")
    elif record_type == "final_summary":
        if set(record) != _FINAL_KEYS:
            raise ValueError("rescore_final_schema_invalid")
        if (
            record.get("historical_artifacts_preserved") is not True
            or record.get("sonnet_model_change_support") != "not_supported"
            or record.get("gemini_model_change_support") != "not_supported"
            or record.get("gpt_5_2_trial_status")
            != "not_required_by_current_evidence"
            or set(record.get("reason_codes") or []) != _FINAL_REASON_CODES
            or len(record.get("reason_codes") or []) != len(_FINAL_REASON_CODES)
        ):
            raise ValueError("rescore_final_decision_invalid")
    else:
        raise ValueError("rescore_record_type_invalid")


def validate_rescoring_artifact(
    records: Sequence[Mapping[str, Any]],
    repo_root: Path,
) -> dict[str, Any]:
    for record in records:
        if not isinstance(record, Mapping):
            raise ValueError("rescore_record_not_object")
        _validate_record_shape(record)
    expected = build_rescoring_records(repo_root)
    if list(records) != expected:
        raise ValueError("rescore_artifact_reconstruction_mismatch")
    final = expected[-1]
    return {
        "dialogue_rescore_count": final["dialogue_rescore_count"],
        "configuration_summary_count": final["configuration_summary_count"],
        "prompt_strengthening_primary_local_decision": final[
            "prompt_strengthening_primary_local_decision"
        ],
        "sonnet_local_decision": final["sonnet_local_decision"],
        "gemini_local_decision": final["gemini_local_decision"],
        "gpt_5_2_trial_status": final["gpt_5_2_trial_status"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline causal rescoring for retained Lot 4 Stimmung artifacts."
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    records = build_rescoring_records(args.repo_root)
    validate_rescoring_artifact(records, args.repo_root)
    dialogic_campaign.write_jsonl(args.output, records)
    print(
        json.dumps(
            {
                "record_count": len(records),
                "dialogue_rescore_count": records[-1]["dialogue_rescore_count"],
                "configuration_summary_count": records[-1][
                    "configuration_summary_count"
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
