from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import statistics
from pathlib import Path
from typing import Any, Mapping, Sequence

from benchmark.core.openrouter import OpenRouterClient
from benchmark.suites.stimmung import dialogic_semantics
from core import token_utils
from core.hermeneutic_node.inputs import recent_context_input, recent_window_input
from core.hermeneutic_node.inputs.stimmung_input import build_stimmung_input
from core.stimmung_agent import (
    _build_fail_open_signal,
    _build_messages,
    _safe_json_loads,
    _validate_affective_turn_signal,
)


PROTOCOL_VERSION = "lot4s1_stimmung_provider_campaign_v1"
ARTIFACT_VERSION = "lot4s1_stimmung_provider_results_v1"
STRENGTHENING_PROTOCOL_VERSION = "lot4c2_stimmung_semantic_strengthening_v1"
STRENGTHENING_ARTIFACT_VERSION = "lot4c2_stimmung_semantic_strengthening_results_v1"
PRIMARY_MODEL = "google/gemini-3.1-flash-lite"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
MODELS = {"primary": PRIMARY_MODEL, "fallback": FALLBACK_MODEL}
GENERATION_PARAMS = {"temperature": 0.1, "top_p": 1.0, "max_tokens": 220}
TIMEOUT_S = 10
REPETITIONS = 2
EXPECTED_DIALOGUES = 16
EXPECTED_TURNS = 69
EXPECTED_EVALUATED_STEPS = 32
EXPECTED_CALLS = 276
ABSOLUTE_CALL_CAP = 276
COST_CAP_USD = 0.30
PRICING_OBSERVED_AT = "2026-08-30T14:11:55Z"
PRICING_USD_PER_TOKEN = {
    PRIMARY_MODEL: {"prompt": 0.00000025, "completion": 0.0000015},
    FALLBACK_MODEL: {"prompt": 0.0000002, "completion": 0.00000125},
}
PHASE_A_FREEZE_COMMIT = "c02e1dd7ad53c6eb33296c563304c5e4d7be3f7e"
PHASE_A_HARNESS_SHA256 = "2458512091d7d51c9414bd6256bc969f6d42f19a6545468a5a1a45a3ea46566e"
STRENGTHENING_CANDIDATE_FIXTURE = "stimmung_semantic_strengthening_candidate_v1.txt"
STRENGTHENING_FREEZE_MANIFEST = "stimmung_semantic_strengthening_freeze_v1.json"
HISTORICAL_ARTIFACT = "2026-08-30-lot4s1-stimmung-primary-fallback.jsonl"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_SOURCES = ("primary", "fallback")
_CALL_STATUSES = {"ok", "transport_error", "timeout", "refusal", "json_error", "schema_error"}
_CALL_REASONS = {
    "ok",
    "transport_error",
    "timeout",
    "refusal",
    "invalid_json",
    "validation_error",
    "route_mismatch",
}
_PROVIDERS = {"google", "openai", "unknown"}
_EXPECTED_PROVIDER = {"primary": "google", "fallback": "openai"}
_DECISIONS = {"keep_current", "strengthen", "inconclusive"}
_DIALOGUE_REASON_CODES = {
    "aggregate_decay_mismatch",
    "aggregate_dominant_outside_allowed",
    "aggregate_overcoded",
    "aggregate_presence_mismatch",
    "aggregate_schema_invalid",
    "aggregate_turn_count_mismatch",
    "caller_result_unavailable",
    "dominant_tone_outside_allowed",
    "execution_status_invalid",
    "fail_open_not_semantic_success",
    "irony_literalized",
    "mixed_sources",
    "observation_order_invalid",
    "observation_schema_invalid",
    "quoted_affect_internalized",
    "reported_affect_internalized",
    "signal_false_negative",
    "signal_false_positive",
    "signal_overcoded",
    "signal_schema_invalid",
    "signal_tone_forbidden",
    "source_invalid",
    "strength_outside_allowed",
    "trajectory_shift_mismatch",
    "trajectory_stability_mismatch",
}
_REPETITION_REASON_CODES = {
    "all_thresholds_met",
    "caller_semantic_failure",
    "dialogue_result_inconclusive",
    "dialogue_set_incomplete",
    "family_threshold_missed",
    "provider_results_not_observed",
    "source_mismatch",
}
_HISTORICAL_FINAL_REASON_CODES = _DIALOGUE_REASON_CODES | {
    "all_thresholds_met",
    "dialogue_results_incomplete",
    "provider_or_schema_inconclusive",
    "provider_results_or_metrics_incomplete",
    "semantic_failure_not_reproducible",
}
_STRENGTHENING_FINAL_REASON_CODES = {
    "all_thresholds_met_no_regression",
    "candidate_semantic_failure",
    "dialogue_results_incomplete",
    "provider_or_schema_inconclusive",
    "provider_results_or_metrics_incomplete",
}
_CALL_KEYS = {
    "artifact_version",
    "protocol_version",
    "record_type",
    "sequence",
    "dialogue_id",
    "turn_id",
    "evaluated",
    "source",
    "repetition",
    "requested_model",
    "observed_model",
    "observed_provider",
    "status",
    "reason_code",
    "json_valid",
    "schema_valid",
    "fail_open",
    "signal",
    "aggregate",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost_usd",
    "messages_sha256",
    "corpus_sha256",
    "prompt_sha256",
    "harness_sha256",
    "parameters_sha256",
    "freeze_commit",
}
_DIALOGUE_SCORE_KEYS = {
    "artifact_version",
    "protocol_version",
    "record_type",
    "dialogue_id",
    "families",
    "source",
    "repetition",
    "classification",
    "error_class",
    "reason_codes",
    "evaluated_turns",
}
_REPETITION_SUMMARY_KEYS = {
    "artifact_version",
    "protocol_version",
    "record_type",
    "source",
    "repetition",
    "decision",
    "reason_codes",
    "dialogue_count",
    "family_pass_rates",
    "semantic_failures",
    "inconclusive_results",
    "provider_results_observed",
}
_SOURCE_SUMMARY_KEYS = {
    "artifact_version",
    "protocol_version",
    "record_type",
    "source",
    "repetition_decisions",
    "call_count",
    "ok_count",
    "semantic_failure_count",
    "inconclusive_dialogue_count",
    "latency_median_ms",
    "latency_p95_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost_usd",
}
_FINAL_KEYS = {
    "artifact_version",
    "protocol_version",
    "record_type",
    "decision",
    "reason_codes",
    "next_micro_lot",
    "call_count",
    "dialogue_score_count",
    "cost_usd",
    "calls_sha256",
}
_STRENGTHENING_FINAL_KEYS = _FINAL_KEYS | {
    "baseline_artifact_sha256",
    "semantic_regression_count",
    "semantic_regression_count_complete",
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _corpus_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_dialogic_semantic_v2.json"


def _prompt_path(repo_root: Path) -> Path:
    return repo_root / "app/prompts/stimmung_agent.txt"


def _strengthening_candidate_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "benchmark/suites/stimmung/fixtures"
        / STRENGTHENING_CANDIDATE_FIXTURE
    )


def _strengthening_manifest_path(repo_root: Path) -> Path:
    return (
        repo_root
        / "benchmark/suites/stimmung/fixtures"
        / STRENGTHENING_FREEZE_MANIFEST
    )


def _historical_artifact_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/results/stimmung" / HISTORICAL_ARTIFACT


def _harness_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/dialogic_campaign.py"


def load_strengthening_candidate(repo_root: Path) -> str:
    candidate = _strengthening_candidate_path(repo_root).read_text(encoding="utf-8").strip()
    if not candidate or len(candidate) > 3200:
        raise ValueError("strengthening_candidate_invalid")
    return candidate


def _load_inputs(
    repo_root: Path,
    *,
    prompt_path: Path | None = None,
) -> tuple[dict[str, Any], str]:
    corpus = dialogic_semantics.load_corpus(repo_root)
    dialogic_semantics.validate_corpus(corpus)
    prompt = (prompt_path or _prompt_path(repo_root)).read_text(encoding="utf-8").strip()
    if not prompt:
        raise ValueError("stimmung_prompt_missing")
    return corpus, prompt


def _base_requests(
    repo_root: Path,
    *,
    prompt_path: Path | None = None,
) -> list[dict[str, Any]]:
    corpus, prompt = _load_inputs(repo_root, prompt_path=prompt_path)
    requests: list[dict[str, Any]] = []
    for dialogue in corpus["dialogues"]:
        history: list[dict[str, Any]] = []
        for turn in dialogue["turns"]:
            user = {"role": "user", "content": turn["user"], "timestamp": None}
            history.append(user)
            context = recent_context_input.build_recent_context_input(messages=history)
            window = recent_window_input.build_recent_window_input(
                recent_context_input_payload=context,
            )
            messages = _build_messages(
                system_prompt=prompt,
                user_msg=turn["user"],
                recent_window_input_payload=window,
            )
            requests.append(
                {
                    "dialogue_id": dialogue["id"],
                    "turn_id": int(turn["turn_id"]),
                    "evaluated": "expectation" in turn,
                    "messages": messages,
                    "messages_sha256": _sha256_text(_compact_json(messages)),
                    "window_turn_count": int(window["turn_count"]),
                }
            )
            history.append({"role": "assistant", "content": turn["assistant"], "timestamp": None})
    return requests


def build_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(str(freeze_commit)) is None:
        raise ValueError("invalid_freeze_commit")
    corpus, _ = _load_inputs(repo_root)
    base = _base_requests(repo_root)
    dialogue_count = len(corpus["dialogues"])
    turn_count = len(base)
    evaluated_count = sum(1 for item in base if item["evaluated"])
    if (dialogue_count, turn_count, evaluated_count) != (
        EXPECTED_DIALOGUES,
        EXPECTED_TURNS,
        EXPECTED_EVALUATED_STEPS,
    ):
        raise ValueError("frozen_corpus_dimensions_changed")

    maximum_prompt_tokens = max(
        token_utils.estimate_tokens(item["messages"], PRIMARY_MODEL) for item in base
    )
    conservative_cost = 0.0
    for source in _SOURCES:
        prices = PRICING_USD_PER_TOKEN[MODELS[source]]
        conservative_cost += REPETITIONS * EXPECTED_TURNS * (
            maximum_prompt_tokens * prices["prompt"]
            + GENERATION_PARAMS["max_tokens"] * prices["completion"]
        )
    conservative_cost = round(conservative_cost * 1.25, 8)
    if conservative_cost > COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")

    parameters = {
        "models": MODELS,
        "generation_params": GENERATION_PARAMS,
        "timeout_s": TIMEOUT_S,
        "provider": {"allow_fallbacks": False},
        "repetitions": REPETITIONS,
        "order": ["primary:1", "primary:2", "fallback:1", "fallback:2"],
    }
    harness_sha256 = (
        PHASE_A_HARNESS_SHA256
        if freeze_commit == PHASE_A_FREEZE_COMMIT
        else _sha256_file(_harness_path(repo_root))
    )
    return {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "campaign_kind": "historical_4s1",
        "freeze_commit": freeze_commit,
        "corpus_id": corpus["corpus_id"],
        "corpus_schema_version": corpus["schema_version"],
        "corpus_sha256": _sha256_file(_corpus_path(repo_root)),
        "prompt_sha256": _sha256_file(_prompt_path(repo_root)),
        "harness_sha256": harness_sha256,
        "parameters_sha256": _sha256_text(_compact_json(parameters)),
        "schedule_sha256": _sha256_text(
            _compact_json(
                [
                    {
                        key: item[key]
                        for key in (
                            "dialogue_id",
                            "turn_id",
                            "evaluated",
                            "messages_sha256",
                            "window_turn_count",
                        )
                    }
                    for item in base
                ]
            )
        ),
        "models": dict(MODELS),
        "generation_params": dict(GENERATION_PARAMS),
        "timeout_s": TIMEOUT_S,
        "provider_policy": {"allow_fallbacks": False},
        "repetitions": REPETITIONS,
        "dialogue_count": dialogue_count,
        "turn_count": turn_count,
        "evaluated_step_count": evaluated_count,
        "expected_call_count": EXPECTED_CALLS,
        "absolute_call_cap": ABSOLUTE_CALL_CAP,
        "cost_cap_usd": COST_CAP_USD,
        "estimated_max_cost_usd": conservative_cost,
        "maximum_estimated_prompt_tokens": maximum_prompt_tokens,
        "pricing_observed_at": PRICING_OBSERVED_AT,
        "pricing_usd_per_token": PRICING_USD_PER_TOKEN,
        "decision_rules": {
            "all_sources_all_repetitions_pass": "keep_current",
            "same_case_source_failure_both_repetitions": "strengthen",
            "incomplete_or_unstable_or_invalid": "inconclusive",
        },
    }


def _load_strengthening_manifest(repo_root: Path) -> dict[str, Any]:
    data = json.loads(_strengthening_manifest_path(repo_root).read_text(encoding="utf-8"))
    required = {
        "schema_version",
        "candidate_prompt_sha256",
        "runtime_prompt_baseline_sha256",
        "corpus_sha256",
        "scorer_sha256",
        "normalizer_sha256",
        "aggregator_sha256",
        "campaign_harness_sha256",
        "baseline_artifact_sha256",
    }
    if not isinstance(data, dict) or set(data) != required:
        raise ValueError("strengthening_manifest_invalid")
    if data.get("schema_version") != "lot4c2_stimmung_strengthening_freeze_v1":
        raise ValueError("strengthening_manifest_invalid")
    for key in required - {"schema_version"}:
        _validate_sha(data.get(key))
    # The harness hash is a freeze-time provenance field. Requiring it to match
    # the evolving reader would make an already-persisted artifact unreadable
    # as soon as its validation contract is corrected.
    expected_files = {
        "candidate_prompt_sha256": _strengthening_candidate_path(repo_root),
        "runtime_prompt_baseline_sha256": _prompt_path(repo_root),
        "corpus_sha256": _corpus_path(repo_root),
        "scorer_sha256": repo_root / "benchmark/suites/stimmung/dialogic_semantics.py",
        "normalizer_sha256": repo_root / "app/core/stimmung_agent.py",
        "aggregator_sha256": repo_root / "app/core/hermeneutic_node/inputs/stimmung_input.py",
        "baseline_artifact_sha256": _historical_artifact_path(repo_root),
    }
    if any(data[key] != _sha256_file(path) for key, path in expected_files.items()):
        raise ValueError("strengthening_manifest_fingerprint_mismatch")
    if data["candidate_prompt_sha256"] == data["runtime_prompt_baseline_sha256"]:
        raise ValueError("strengthening_candidate_not_distinct")
    return data


def build_strengthening_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(str(freeze_commit)) is None:
        raise ValueError("invalid_freeze_commit")
    manifest = _load_strengthening_manifest(repo_root)
    candidate_path = _strengthening_candidate_path(repo_root)
    corpus, _ = _load_inputs(repo_root, prompt_path=candidate_path)
    base = _base_requests(repo_root, prompt_path=candidate_path)
    dialogue_count = len(corpus["dialogues"])
    turn_count = len(base)
    evaluated_count = sum(1 for item in base if item["evaluated"])
    if (dialogue_count, turn_count, evaluated_count) != (
        EXPECTED_DIALOGUES,
        EXPECTED_TURNS,
        EXPECTED_EVALUATED_STEPS,
    ):
        raise ValueError("frozen_corpus_dimensions_changed")

    maximum_prompt_tokens = max(
        token_utils.estimate_tokens(item["messages"], PRIMARY_MODEL) for item in base
    )
    conservative_cost = 0.0
    for source in _SOURCES:
        prices = PRICING_USD_PER_TOKEN[MODELS[source]]
        conservative_cost += REPETITIONS * EXPECTED_TURNS * (
            maximum_prompt_tokens * prices["prompt"]
            + GENERATION_PARAMS["max_tokens"] * prices["completion"]
        )
    conservative_cost = round(conservative_cost * 1.25, 8)
    if conservative_cost > COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")

    parameters = {
        "models": MODELS,
        "generation_params": GENERATION_PARAMS,
        "timeout_s": TIMEOUT_S,
        "provider": {"allow_fallbacks": False},
        "repetitions": REPETITIONS,
        "order": ["primary:1", "primary:2", "fallback:1", "fallback:2"],
    }
    return {
        "protocol_version": STRENGTHENING_PROTOCOL_VERSION,
        "artifact_version": STRENGTHENING_ARTIFACT_VERSION,
        "campaign_kind": "semantic_strengthening_candidate_v1",
        "freeze_commit": freeze_commit,
        "corpus_id": corpus["corpus_id"],
        "corpus_schema_version": corpus["schema_version"],
        "corpus_sha256": manifest["corpus_sha256"],
        "prompt_sha256": manifest["candidate_prompt_sha256"],
        "candidate_prompt_sha256": manifest["candidate_prompt_sha256"],
        "runtime_prompt_baseline_sha256": manifest["runtime_prompt_baseline_sha256"],
        "scorer_sha256": manifest["scorer_sha256"],
        "normalizer_sha256": manifest["normalizer_sha256"],
        "aggregator_sha256": manifest["aggregator_sha256"],
        "harness_sha256": manifest["campaign_harness_sha256"],
        "baseline_artifact_sha256": manifest["baseline_artifact_sha256"],
        "parameters_sha256": _sha256_text(_compact_json(parameters)),
        "schedule_sha256": _sha256_text(
            _compact_json(
                [
                    {
                        key: item[key]
                        for key in (
                            "dialogue_id",
                            "turn_id",
                            "evaluated",
                            "messages_sha256",
                            "window_turn_count",
                        )
                    }
                    for item in base
                ]
            )
        ),
        "models": dict(MODELS),
        "generation_params": dict(GENERATION_PARAMS),
        "timeout_s": TIMEOUT_S,
        "provider_policy": {"allow_fallbacks": False},
        "repetitions": REPETITIONS,
        "dialogue_count": dialogue_count,
        "turn_count": turn_count,
        "evaluated_step_count": evaluated_count,
        "expected_call_count": EXPECTED_CALLS,
        "absolute_call_cap": ABSOLUTE_CALL_CAP,
        "cost_cap_usd": COST_CAP_USD,
        "estimated_max_cost_usd": conservative_cost,
        "maximum_estimated_prompt_tokens": maximum_prompt_tokens,
        "pricing_observed_at": PRICING_OBSERVED_AT,
        "pricing_usd_per_token": PRICING_USD_PER_TOKEN,
        "decision_rules": {
            "all_sources_all_repetitions_pass": "pass",
            "any_semantic_failure": "fail",
            "incomplete_or_invalid": "inconclusive",
        },
    }


def validate_protocol(protocol: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    if protocol.get("protocol_version") == STRENGTHENING_PROTOCOL_VERSION:
        expected = build_strengthening_protocol(
            repo_root,
            freeze_commit=str(protocol.get("freeze_commit") or ""),
        )
    else:
        expected = build_protocol(repo_root, freeze_commit=str(protocol.get("freeze_commit") or ""))
    if dict(protocol) != expected:
        raise ValueError("protocol_freeze_mismatch")
    if expected["expected_call_count"] != expected["absolute_call_cap"]:
        raise ValueError("call_cap_mismatch")
    return {
        "dialogue_count": expected["dialogue_count"],
        "turn_count": expected["turn_count"],
        "evaluated_step_count": expected["evaluated_step_count"],
        "expected_call_count": expected["expected_call_count"],
        "estimated_max_cost_usd": expected["estimated_max_cost_usd"],
    }


def validate_strengthening_protocol(
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if protocol.get("protocol_version") != STRENGTHENING_PROTOCOL_VERSION:
        raise ValueError("strengthening_protocol_version_invalid")
    return validate_protocol(protocol, repo_root)


def build_request_schedule(repo_root: Path, protocol: Mapping[str, Any]) -> list[dict[str, Any]]:
    validate_protocol(protocol, repo_root)
    candidate = protocol.get("protocol_version") == STRENGTHENING_PROTOCOL_VERSION
    base = _base_requests(
        repo_root,
        prompt_path=_strengthening_candidate_path(repo_root) if candidate else None,
    )
    schedule: list[dict[str, Any]] = []
    sequence = 0
    for source in _SOURCES:
        for repetition in range(1, REPETITIONS + 1):
            for item in base:
                sequence += 1
                payload = {
                    "model": MODELS[source],
                    "messages": item["messages"],
                    **GENERATION_PARAMS,
                    "provider": {"allow_fallbacks": False},
                }
                schedule.append(
                    {
                        **item,
                        "sequence": sequence,
                        "source": source,
                        "repetition": repetition,
                        "payload": payload,
                    }
                )
    if len(schedule) != EXPECTED_CALLS:
        raise ValueError("call_schedule_mismatch")
    return schedule


def _provider_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "google" in text:
        return "google"
    if "openai" in text:
        return "openai"
    return "unknown"


def _int_metric(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    try:
        result = int(value)
    except (TypeError, ValueError):
        return None
    return result if 0 <= result <= 10_000_000 else None


def _float_metric(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return round(result, 8) if math.isfinite(result) and result >= 0 else None


def _classify_response(response: Mapping[str, Any], requested_model: str) -> dict[str, Any]:
    latency = _float_metric(response.get("elapsed_ms"))
    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    observed_model_raw = str(response.get("model") or "").strip()
    observed_model = observed_model_raw if observed_model_raw == requested_model else "unknown"
    expected_provider = "google" if requested_model.startswith("google/") else "openai"
    observed_provider = _provider_name(response.get("provider"))
    base = {
        "latency_ms": latency,
        "prompt_tokens": _int_metric(usage.get("prompt_tokens")),
        "completion_tokens": _int_metric(usage.get("completion_tokens")),
        "total_tokens": _int_metric(usage.get("total_tokens")),
        "cost_usd": _float_metric(response.get("cost_estimate_usd")),
        "observed_model": observed_model,
        "observed_provider": observed_provider,
        "signal": None,
        "json_valid": False,
        "schema_valid": False,
    }
    if not response.get("ok"):
        error_kind = str(response.get("error") or "").lower()
        timed_out = "timeout" in error_kind
        return {
            **base,
            "status": "timeout" if timed_out else "transport_error",
            "reason_code": "timeout" if timed_out else "transport_error",
        }
    raw_text = response.get("raw_text")
    if not str(raw_text or "").strip():
        return {**base, "status": "refusal", "reason_code": "refusal"}
    try:
        parsed = _safe_json_loads(raw_text)
    except Exception:
        return {**base, "status": "json_error", "reason_code": "invalid_json"}
    base["json_valid"] = True
    try:
        signal = _validate_affective_turn_signal(parsed)
    except Exception:
        return {**base, "status": "schema_error", "reason_code": "validation_error"}
    base["schema_valid"] = True
    if observed_model != requested_model or observed_provider != expected_provider:
        return {**base, "status": "transport_error", "reason_code": "route_mismatch"}
    return {**base, "status": "ok", "reason_code": "ok", "signal": signal}


def _call_record(
    *,
    plan: Mapping[str, Any],
    outcome: Mapping[str, Any],
    aggregate: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "artifact_version": protocol.get("artifact_version", ARTIFACT_VERSION),
        "protocol_version": protocol["protocol_version"],
        "record_type": "call",
        "sequence": plan["sequence"],
        "dialogue_id": plan["dialogue_id"],
        "turn_id": plan["turn_id"],
        "evaluated": plan["evaluated"],
        "source": plan["source"],
        "repetition": plan["repetition"],
        "requested_model": MODELS[plan["source"]],
        "observed_model": outcome["observed_model"],
        "observed_provider": outcome["observed_provider"],
        "status": outcome["status"],
        "reason_code": outcome["reason_code"],
        "json_valid": outcome["json_valid"],
        "schema_valid": outcome["schema_valid"],
        "fail_open": outcome["status"] != "ok",
        "signal": outcome["signal"],
        "aggregate": dict(aggregate),
        "latency_ms": outcome["latency_ms"],
        "prompt_tokens": outcome["prompt_tokens"],
        "completion_tokens": outcome["completion_tokens"],
        "total_tokens": outcome["total_tokens"],
        "cost_usd": outcome["cost_usd"],
        "messages_sha256": plan["messages_sha256"],
        "corpus_sha256": protocol["corpus_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "harness_sha256": protocol["harness_sha256"],
        "parameters_sha256": protocol["parameters_sha256"],
        "freeze_commit": protocol["freeze_commit"],
    }


def run_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    schedule = build_request_schedule(repo_root, protocol)
    candidate = protocol.get("protocol_version") == STRENGTHENING_PROTOCOL_VERSION
    corpus, _ = _load_inputs(
        repo_root,
        prompt_path=_strengthening_candidate_path(repo_root) if candidate else None,
    )
    cases = {item["id"]: item for item in corpus["dialogues"]}
    records: list[dict[str, Any]] = []
    dialogue_scores: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    group: tuple[str, int, str] | None = None

    def finish_dialogue() -> None:
        if group is None:
            return
        source, repetition, dialogue_id = group
        score = dialogic_semantics.score_dialogue(cases[dialogue_id], observations)
        dialogue_scores.append(
            _dialogue_score_record(
                score,
                source=source,
                repetition=repetition,
                protocol=protocol,
            )
        )

    for plan in schedule:
        next_group = (plan["source"], plan["repetition"], plan["dialogue_id"])
        if group != next_group:
            finish_dialogue()
            group = next_group
            history = []
            observations = []
        turn = cases[plan["dialogue_id"]]["turns"][plan["turn_id"] - 1]
        user_message = {"role": "user", "content": turn["user"], "timestamp": None, "meta": {}}
        history.append(user_message)
        response = client.chat_completion(
            dict(plan["payload"]),
            caller="stimmung_agent",
            timeout_s=TIMEOUT_S,
        )
        outcome = _classify_response(response, MODELS[plan["source"]])
        attached_signal = outcome["signal"] if outcome["status"] == "ok" else _build_fail_open_signal()
        user_message["meta"]["affective_turn_signal"] = attached_signal
        aggregate = build_stimmung_input(messages=history)
        record = _call_record(plan=plan, outcome=outcome, aggregate=aggregate, protocol=protocol)
        validate_content_free_record(record)
        records.append(record)
        if plan["evaluated"]:
            observations.append(
                {
                    "turn_id": plan["turn_id"],
                    "execution_status": outcome["status"],
                    "source": plan["source"],
                    "signal": outcome["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append({"role": "assistant", "content": turn["assistant"], "timestamp": None})
        if callable(progress):
            progress(int(plan["sequence"]), EXPECTED_CALLS, dict(record))
    finish_dialogue()
    records.extend(_summary_records(records, dialogue_scores, corpus, protocol=protocol))
    return records


def _dialogue_score_record(
    score: Mapping[str, Any],
    *,
    source: str,
    repetition: int,
    protocol: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_version": (protocol or {}).get("artifact_version", ARTIFACT_VERSION),
        "protocol_version": (protocol or {}).get("protocol_version", PROTOCOL_VERSION),
        "record_type": "dialogue_score",
        "dialogue_id": score["dialogue_id"],
        "families": list(score["families"]),
        "source": source,
        "repetition": repetition,
        "classification": score["classification"],
        "error_class": score["error_class"],
        "reason_codes": list(score["reason_codes"]),
        "evaluated_turns": int(score["evaluated_turns"]),
    }


def decide_from_dialogue_scores(scores: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    grouped_ids = {
        (source, repetition): [
            str(item.get("dialogue_id") or "")
            for item in scores
            if item.get("source") == source and item.get("repetition") == repetition
        ]
        for source in _SOURCES
        for repetition in (1, 2)
    }
    if (
        len(scores) != 64
        or any(len(ids) != EXPECTED_DIALOGUES or len(set(ids)) != EXPECTED_DIALOGUES for ids in grouped_ids.values())
        or any(item.get("classification") not in {"pass", "fail", "inconclusive"} for item in scores)
    ):
        return {"decision": "inconclusive", "reason_codes": ["dialogue_results_incomplete"], "next_micro_lot": None}
    if any(item.get("classification") == "inconclusive" for item in scores):
        return {"decision": "inconclusive", "reason_codes": ["provider_or_schema_inconclusive"], "next_micro_lot": None}
    failures = [item for item in scores if item.get("classification") == "fail"]
    if not failures:
        return {"decision": "keep_current", "reason_codes": ["all_thresholds_met"], "next_micro_lot": None}
    by_case: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for item in failures:
        by_case.setdefault((str(item["source"]), str(item["dialogue_id"])), []).append(item)
    reproducible = []
    for key, items in by_case.items():
        repetitions = {int(item["repetition"]) for item in items}
        shared = set(items[0].get("reason_codes") or [])
        for item in items[1:]:
            shared &= set(item.get("reason_codes") or [])
        if repetitions == {1, 2} and shared:
            reproducible.append((key, sorted(shared)))
    if reproducible:
        codes = sorted({code for _, shared in reproducible for code in shared})
        return {"decision": "strengthen", "reason_codes": codes, "next_micro_lot": "4C.2"}
    return {"decision": "inconclusive", "reason_codes": ["semantic_failure_not_reproducible"], "next_micro_lot": None}


def load_historical_provider_artifact(repo_root: Path) -> list[dict[str, Any]]:
    records = load_jsonl(_historical_artifact_path(repo_root))
    protocol = build_protocol(repo_root, freeze_commit=PHASE_A_FREEZE_COMMIT)
    validate_artifact(records, repo_root, protocol)
    return records


def _historical_pass_keys(records: Sequence[Mapping[str, Any]]) -> set[tuple[str, int, str]]:
    return {
        (str(item["source"]), int(item["repetition"]), str(item["dialogue_id"]))
        for item in records
        if item.get("record_type") == "dialogue_score" and item.get("classification") == "pass"
    }


def decide_strengthening_from_dialogue_scores(
    scores: Sequence[Mapping[str, Any]],
    *,
    historical_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    historical_passes = _historical_pass_keys(historical_records)
    semantic_regression_count = sum(
        (
            str(item.get("source") or ""),
            int(item.get("repetition") or 0),
            str(item.get("dialogue_id") or ""),
        )
        in historical_passes
        for item in scores
        if item.get("classification") == "fail"
    )
    grouped_ids = {
        (source, repetition): [
            str(item.get("dialogue_id") or "")
            for item in scores
            if item.get("source") == source and item.get("repetition") == repetition
        ]
        for source in _SOURCES
        for repetition in (1, 2)
    }
    if (
        len(scores) != 64
        or any(
            len(ids) != EXPECTED_DIALOGUES or len(set(ids)) != EXPECTED_DIALOGUES
            for ids in grouped_ids.values()
        )
        or any(
            item.get("classification") not in {"pass", "fail", "inconclusive"}
            for item in scores
        )
    ):
        return {
            "decision": "inconclusive",
            "reason_codes": ["dialogue_results_incomplete"],
            "next_micro_lot": None,
            "semantic_regression_count": semantic_regression_count,
            "semantic_regression_count_complete": False,
        }
    if any(item.get("classification") == "inconclusive" for item in scores):
        return {
            "decision": "inconclusive",
            "reason_codes": ["provider_or_schema_inconclusive"],
            "next_micro_lot": None,
            "semantic_regression_count": semantic_regression_count,
            "semantic_regression_count_complete": False,
        }
    failed = [item for item in scores if item.get("classification") == "fail"]
    if failed:
        return {
            "decision": "fail",
            "reason_codes": ["candidate_semantic_failure"],
            "next_micro_lot": None,
            "semantic_regression_count": semantic_regression_count,
            "semantic_regression_count_complete": True,
        }
    return {
        "decision": "pass",
        "reason_codes": ["all_thresholds_met_no_regression"],
        "next_micro_lot": None,
        "semantic_regression_count": 0,
        "semantic_regression_count_complete": True,
    }


def _summary_records(
    calls: Sequence[Mapping[str, Any]],
    dialogue_scores: Sequence[Mapping[str, Any]],
    corpus: Mapping[str, Any],
    *,
    protocol: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    protocol_data = protocol or {
        "artifact_version": ARTIFACT_VERSION,
        "protocol_version": PROTOCOL_VERSION,
    }
    artifact_version = str(protocol_data.get("artifact_version", ARTIFACT_VERSION))
    protocol_version = str(protocol_data["protocol_version"])
    strengthening = protocol_version == STRENGTHENING_PROTOCOL_VERSION
    results: list[dict[str, Any]] = list(dialogue_scores)
    repetition_decisions: dict[str, list[str]] = {source: [] for source in _SOURCES}
    for source in _SOURCES:
        for repetition in (1, 2):
            selected = [
                item for item in dialogue_scores
                if item["source"] == source and item["repetition"] == repetition
            ]
            summary = dialogic_semantics.summarize_configuration(
                source=source,
                corpus=corpus,
                dialogue_scores=selected,
                provider_results_observed=True,
            )
            repetition_decisions[source].append(summary["decision"])
            results.append(
                {
                    "artifact_version": artifact_version,
                    "protocol_version": protocol_version,
                    "record_type": "repetition_summary",
                    "source": source,
                    "repetition": repetition,
                    "decision": summary["decision"],
                    "reason_codes": summary["reason_codes"],
                    "dialogue_count": summary["dialogue_count"],
                    "family_pass_rates": summary["family_pass_rates"],
                    "semantic_failures": summary["semantic_failures"],
                    "inconclusive_results": summary["inconclusive_results"],
                    "provider_results_observed": True,
                }
            )
    for source in _SOURCES:
        selected_calls = [item for item in calls if item["source"] == source]
        selected_scores = [item for item in dialogue_scores if item["source"] == source]
        latencies = [float(item["latency_ms"]) for item in selected_calls if item["latency_ms"] is not None]
        results.append(
            {
                "artifact_version": artifact_version,
                "protocol_version": protocol_version,
                "record_type": "source_summary",
                "source": source,
                "repetition_decisions": repetition_decisions[source],
                "call_count": len(selected_calls),
                "ok_count": sum(item["status"] == "ok" for item in selected_calls),
                "semantic_failure_count": sum(item["classification"] == "fail" for item in selected_scores),
                "inconclusive_dialogue_count": sum(
                    item["classification"] == "inconclusive" for item in selected_scores
                ),
                "latency_median_ms": round(statistics.median(latencies), 3) if latencies else None,
                "latency_p95_ms": _percentile(latencies, 0.95),
                "prompt_tokens": _sum_metric(selected_calls, "prompt_tokens"),
                "completion_tokens": _sum_metric(selected_calls, "completion_tokens"),
                "total_tokens": _sum_metric(selected_calls, "total_tokens"),
                "cost_usd": _sum_cost(selected_calls),
            }
        )
    decision = (
        decide_strengthening_from_dialogue_scores(
            dialogue_scores,
            historical_records=load_historical_provider_artifact(Path(__file__).resolve().parents[3]),
        )
        if strengthening
        else decide_from_dialogue_scores(dialogue_scores)
    )
    metrics_complete = all(
        item["status"] == "ok"
        and item["latency_ms"] is not None
        and item["prompt_tokens"] is not None
        and item["completion_tokens"] is not None
        and item["total_tokens"] is not None
        and item["cost_usd"] is not None
        for item in calls
    )
    if not metrics_complete:
        semantic_evidence = (
            {
                "semantic_regression_count": decision["semantic_regression_count"],
                "semantic_regression_count_complete": decision[
                    "semantic_regression_count_complete"
                ],
            }
            if strengthening
            else {}
        )
        decision = {
            "decision": "inconclusive",
            "reason_codes": ["provider_results_or_metrics_incomplete"],
            "next_micro_lot": None,
            **semantic_evidence,
        }
    final = {
        "artifact_version": artifact_version,
        "protocol_version": protocol_version,
        "record_type": "final_summary",
        **decision,
        "call_count": len(calls),
        "dialogue_score_count": len(dialogue_scores),
        "cost_usd": _sum_cost(calls),
        "calls_sha256": _sha256_text(_compact_json(list(calls))),
    }
    if strengthening:
        final["baseline_artifact_sha256"] = protocol_data["baseline_artifact_sha256"]
    results.append(final)
    return results


def _sum_metric(records: Sequence[Mapping[str, Any]], key: str) -> int | None:
    values = [item.get(key) for item in records]
    return sum(int(value) for value in values) if values and all(value is not None for value in values) else None


def _sum_cost(records: Sequence[Mapping[str, Any]]) -> float | None:
    values = [item.get("cost_usd") for item in records]
    return round(sum(float(value) for value in values), 8) if values and all(value is not None for value in values) else None


def _percentile(values: Sequence[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, math.ceil(quantile * len(ordered)) - 1))
    return round(float(ordered[index]), 3)


def _validate_sha(value: Any) -> None:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("invalid_sha256")


def _validate_signal(value: Any) -> None:
    if value is None:
        return
    if not isinstance(value, Mapping):
        raise ValueError("invalid_signal")
    _validate_affective_turn_signal(value)


def _validate_aggregate(value: Any) -> None:
    if not isinstance(value, Mapping) or set(value) != {
        "schema_version", "present", "dominant_tone", "active_tones", "stability", "shift_state", "turns_considered"
    }:
        raise ValueError("invalid_aggregate")
    if value.get("schema_version") != "v1" or not isinstance(value.get("present"), bool):
        raise ValueError("invalid_aggregate")
    if not isinstance(value.get("active_tones"), list) or not 0 <= int(value.get("turns_considered", -1)) <= 4:
        raise ValueError("invalid_aggregate")
    if value["present"]:
        if value.get("dominant_tone") not in dialogic_semantics.ALLOWED_TONES:
            raise ValueError("invalid_aggregate")
        if value.get("stability") not in {"emerging", "stable", "volatile"}:
            raise ValueError("invalid_aggregate")
        if value.get("shift_state") not in {"steady", "candidate_shift", "shifted"}:
            raise ValueError("invalid_aggregate")
    else:
        if value.get("dominant_tone") is not None or value.get("active_tones") != []:
            raise ValueError("invalid_aggregate")


def validate_content_free_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("record_not_object")
    record_type = record.get("record_type")
    strengthening = record.get("protocol_version") == STRENGTHENING_PROTOCOL_VERSION
    keys = {
        "call": _CALL_KEYS,
        "dialogue_score": _DIALOGUE_SCORE_KEYS,
        "repetition_summary": _REPETITION_SUMMARY_KEYS,
        "source_summary": _SOURCE_SUMMARY_KEYS,
        "final_summary": _STRENGTHENING_FINAL_KEYS if strengthening else _FINAL_KEYS,
    }.get(record_type)
    if keys is None or set(record) != keys:
        raise ValueError("record_schema_invalid")
    valid_version_pair = (
        (ARTIFACT_VERSION, PROTOCOL_VERSION),
        (STRENGTHENING_ARTIFACT_VERSION, STRENGTHENING_PROTOCOL_VERSION),
    )
    if (record.get("artifact_version"), record.get("protocol_version")) not in valid_version_pair:
        raise ValueError("record_version_invalid")
    if record_type == "call":
        if record.get("status") not in _CALL_STATUSES or record.get("reason_code") not in _CALL_REASONS:
            raise ValueError("call_status_invalid")
        if record.get("source") not in _SOURCES or record.get("requested_model") != MODELS[record["source"]]:
            raise ValueError("call_source_invalid")
        if record.get("observed_model") not in {record["requested_model"], "unknown"}:
            raise ValueError("observed_model_invalid")
        if record.get("observed_provider") not in _PROVIDERS:
            raise ValueError("observed_provider_invalid")
        if not isinstance(record.get("latency_ms"), (int, float)) or not math.isfinite(float(record["latency_ms"])):
            raise ValueError("latency_missing")
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            if record.get(key) is not None and _int_metric(record.get(key)) != record.get(key):
                raise ValueError("token_metric_invalid")
        if record.get("cost_usd") is not None and _float_metric(record.get("cost_usd")) != record.get("cost_usd"):
            raise ValueError("cost_metric_invalid")
        _validate_signal(record.get("signal"))
        _validate_aggregate(record.get("aggregate"))
        if record["status"] == "ok":
            if not record.get("json_valid") or not record.get("schema_valid") or record.get("signal") is None or record.get("fail_open"):
                raise ValueError("false_semantic_success")
            if (
                record.get("observed_model") != record["requested_model"]
                or record.get("observed_provider") != _EXPECTED_PROVIDER[record["source"]]
            ):
                raise ValueError("observed_route_mismatch")
        elif record.get("signal") is not None or not record.get("fail_open"):
            raise ValueError("failed_call_signal_present")
        for key in ("messages_sha256", "corpus_sha256", "prompt_sha256", "harness_sha256", "parameters_sha256"):
            _validate_sha(record.get(key))
        if _COMMIT_RE.fullmatch(str(record.get("freeze_commit") or "")) is None:
            raise ValueError("freeze_commit_invalid")
    elif record_type == "dialogue_score":
        if record.get("source") not in _SOURCES or record.get("classification") not in {"pass", "fail", "inconclusive"}:
            raise ValueError("dialogue_score_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _DIALOGUE_REASON_CODES for code in record["reason_codes"]
        ):
            raise ValueError("dialogue_reason_invalid")
    elif record_type == "repetition_summary":
        if record.get("source") not in _SOURCES or record.get("decision") not in {"pass", "fail", "inconclusive"}:
            raise ValueError("repetition_summary_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _REPETITION_REASON_CODES for code in record["reason_codes"]
        ):
            raise ValueError("repetition_reason_invalid")
    elif record_type == "source_summary":
        if record.get("source") not in _SOURCES or record.get("call_count") != 138:
            raise ValueError("source_summary_invalid")
    else:
        allowed_decisions = {"pass", "fail", "inconclusive"} if strengthening else _DECISIONS
        if record.get("decision") not in allowed_decisions:
            raise ValueError("final_decision_invalid")
        allowed_reasons = (
            _STRENGTHENING_FINAL_REASON_CODES
            if strengthening
            else _HISTORICAL_FINAL_REASON_CODES
        )
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in allowed_reasons for code in record["reason_codes"]
        ):
            raise ValueError("final_reason_invalid")
        if strengthening and record.get("next_micro_lot") is not None:
            raise ValueError("strengthening_next_micro_lot_invalid")
        _validate_sha(record.get("calls_sha256"))
        if strengthening:
            _validate_sha(record.get("baseline_artifact_sha256"))
            if not isinstance(record.get("semantic_regression_count"), int) or not 0 <= record["semantic_regression_count"] <= 64:
                raise ValueError("semantic_regression_count_invalid")
            if not isinstance(record.get("semantic_regression_count_complete"), bool):
                raise ValueError("semantic_regression_count_completeness_invalid")
    return dict(record)


def validate_artifact(
    records: Sequence[Mapping[str, Any]],
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    validate_protocol(protocol, repo_root)
    for record in records:
        validate_content_free_record(record)
    calls = [dict(item) for item in records if item.get("record_type") == "call"]
    if len(calls) != EXPECTED_CALLS or [item["sequence"] for item in calls] != list(range(1, EXPECTED_CALLS + 1)):
        raise ValueError("call_order_invalid")
    if list(records[:EXPECTED_CALLS]) != calls:
        raise ValueError("call_order_invalid")
    schedule = build_request_schedule(repo_root, protocol)
    candidate = protocol.get("protocol_version") == STRENGTHENING_PROTOCOL_VERSION
    corpus, _ = _load_inputs(
        repo_root,
        prompt_path=_strengthening_candidate_path(repo_root) if candidate else None,
    )
    histories: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    observations: dict[tuple[str, int, str], list[dict[str, Any]]] = {}
    cases = {item["id"]: item for item in corpus["dialogues"]}
    frozen_call_fields = {
        "corpus_sha256": protocol["corpus_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "harness_sha256": protocol["harness_sha256"],
        "parameters_sha256": protocol["parameters_sha256"],
        "freeze_commit": protocol["freeze_commit"],
    }
    for call, plan in zip(calls, schedule):
        if any(call[key] != plan[key] for key in ("sequence", "source", "repetition", "dialogue_id", "turn_id", "evaluated", "messages_sha256")):
            raise ValueError("call_order_invalid")
        if any(call.get(key) != value for key, value in frozen_call_fields.items()):
            raise ValueError("call_protocol_fingerprint_mismatch")
        group = (call["source"], call["repetition"], call["dialogue_id"])
        history = histories.setdefault(group, [])
        turn = cases[call["dialogue_id"]]["turns"][call["turn_id"] - 1]
        signal = call["signal"] if call["status"] == "ok" else _build_fail_open_signal()
        history.append(
            {
                "role": "user",
                "content": turn["user"],
                "timestamp": None,
                "meta": {"affective_turn_signal": signal},
            }
        )
        aggregate = build_stimmung_input(messages=history)
        if aggregate != call["aggregate"]:
            raise ValueError("aggregate_reconstruction_mismatch")
        if call["evaluated"]:
            observations.setdefault(group, []).append(
                {
                    "turn_id": call["turn_id"],
                    "execution_status": call["status"],
                    "source": call["source"],
                    "signal": call["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append({"role": "assistant", "content": turn["assistant"], "timestamp": None})
    scores = []
    for source in _SOURCES:
        for repetition in (1, 2):
            for case in corpus["dialogues"]:
                group = (source, repetition, case["id"])
                score = dialogic_semantics.score_dialogue(case, observations.get(group, []))
                scores.append(
                    _dialogue_score_record(
                        score,
                        source=source,
                        repetition=repetition,
                        protocol=protocol,
                    )
                )
    expected_tail = _summary_records(calls, scores, corpus, protocol=protocol)
    if list(records[EXPECTED_CALLS:]) != expected_tail:
        raise ValueError("artifact_summary_reconstruction_mismatch")
    final = expected_tail[-1]
    return {
        "call_count": len(calls),
        "dialogue_score_count": len(scores),
        "final_decision": final["decision"],
        "cost_usd": final["cost_usd"],
    }


def encode_jsonl(records: Sequence[Mapping[str, Any]]) -> str:
    return "".join(f"{_compact_json(record)}\n" for record in records)


def parse_jsonl(text: str) -> list[dict[str, Any]]:
    records = [json.loads(line) for line in text.splitlines() if line.strip()]
    if not all(isinstance(item, dict) for item in records):
        raise ValueError("artifact_line_not_object")
    return records


def write_jsonl(path: Path, records: Sequence[Mapping[str, Any]]) -> None:
    path.write_text(encode_jsonl(records), encoding="utf-8")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return parse_jsonl(path.read_text(encoding="utf-8"))


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lot 4S.1 bounded Stimmung provider campaign")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--strengthening", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    protocol = (
        build_strengthening_protocol(args.repo_root, freeze_commit=args.freeze_commit)
        if args.strengthening
        else build_protocol(args.repo_root, freeze_commit=args.freeze_commit)
    )
    summary = validate_protocol(protocol, args.repo_root)
    if args.dry_run:
        print(_compact_json({"status": "ready", **summary, "protocol_sha256": _sha256_text(_compact_json(protocol))}))
        return 0
    if args.output is None:
        raise SystemExit("--output is required for a live campaign")
    client = OpenRouterClient.from_env(title="FridaDev/Lot4S1")

    def progress(current: int, total: int, _record: Mapping[str, Any]) -> None:
        if current == 1 or current % 20 == 0 or current == total:
            print(_compact_json({"status": "running", "completed": current, "total": total}), flush=True)

    records = run_campaign(repo_root=args.repo_root, protocol=protocol, client=client, progress=progress)
    validate_artifact(records, args.repo_root, protocol)
    write_jsonl(args.output, records)
    final = records[-1]
    print(
        _compact_json(
            {
                "status": "complete",
                "calls": final["call_count"],
                "decision": final["decision"],
                "cost_usd": final["cost_usd"],
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
