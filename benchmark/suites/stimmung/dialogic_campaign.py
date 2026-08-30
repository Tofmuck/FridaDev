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
from benchmark.suites.validation_agent import lot4c1_policy_comparison as validation_model_policy
from core import token_utils
from core.hermeneutic_node.inputs import recent_context_input, recent_window_input
from core.hermeneutic_node.inputs.stimmung_input import build_stimmung_input
from core.stimmung_agent import (
    ALLOWED_TONES as RUNTIME_ALLOWED_TONES,
    SCHEMA_VERSION as RUNTIME_SIGNAL_SCHEMA_VERSION,
    _ALLOWED_SIGNAL_KEYS as RUNTIME_SIGNAL_KEYS,
    _build_fail_open_signal,
    _build_messages,
    _safe_json_loads,
    _validate_affective_turn_signal,
)


PROTOCOL_VERSION = "lot4s1_stimmung_provider_campaign_v1"
ARTIFACT_VERSION = "lot4s1_stimmung_provider_results_v1"
STRENGTHENING_PROTOCOL_VERSION = "lot4c2_stimmung_semantic_strengthening_v1"
STRENGTHENING_ARTIFACT_VERSION = "lot4c2_stimmung_semantic_strengthening_results_v1"
MODEL_COMPARISON_PROTOCOL_VERSION = "lot4c2_stimmung_gemini_3_7_medium_comparison_v1"
MODEL_COMPARISON_ARTIFACT_VERSION = "lot4c2_stimmung_gemini_3_7_medium_results_v1"
TOKEN_CAP_RERUN_PROTOCOL_VERSION = "lot4c2_stimmung_gemini_3_7_medium_token_cap_rerun_v2"
TOKEN_CAP_RERUN_ARTIFACT_VERSION = "lot4c2_stimmung_gemini_3_7_medium_token_cap_results_v2"
SONNET_CANDIDATE_PROTOCOL_VERSION = "lot4c2_stimmung_sonnet_5_medium_candidate_v1"
SONNET_CANDIDATE_ARTIFACT_VERSION = "lot4c2_stimmung_sonnet_5_medium_results_v1"
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
MODEL_COMPARISON_MODEL = "google/gemini-3.7-flash"
MODEL_COMPARISON_CONFIGURATION_ID = "gemini_3_7_flash_medium"
MODEL_COMPARISON_MAX_TOKENS = 400
MODEL_COMPARISON_TIMEOUT_S = 10
MODEL_COMPARISON_EXPECTED_CALLS = EXPECTED_TURNS * REPETITIONS
MODEL_COMPARISON_ABSOLUTE_CALL_CAP = MODEL_COMPARISON_EXPECTED_CALLS
MODEL_COMPARISON_COST_CAP_USD = 0.30
MODEL_COMPARISON_COST_MARGIN = 1.10
MODEL_COMPARISON_PRICING_OBSERVED_AT = "2026-08-30T14:52:34Z"
MODEL_COMPARISON_PRICING_USD_PER_TOKEN = {
    "prompt": 0.00000075,
    "completion": 0.00000375,
}
MODEL_COMPARISON_FREEZE_COMMIT = "1e9bb9f99c8a5bd73af855e3dc6dbedf211aa5b7"
MODEL_COMPARISON_FREEZE_HARNESS_SHA256 = "fb65297448608e3ba17abbfe69820878f1c1b87b3a93c2d4b03af9b4f76ad837"
MODEL_COMPARISON_ARTIFACT = "2026-08-30-lot4c2-stimmung-gemini-3-7-medium.jsonl"
MODEL_COMPARISON_ARTIFACT_SHA256 = "5adb54eec321f671fb05e2b350d35120a7ce84a52e7b936c4e54829002bce8f3"
TOKEN_CAP_RERUN_MAX_TOKENS = 800
TOKEN_CAP_RERUN_COST_CAP_USD = 0.50
TOKEN_CAP_RERUN_PRICING_OBSERVED_AT = "2026-08-30T15:48:43Z"
TOKEN_CAP_RERUN_FREEZE_COMMIT = "08da24a706d9701d46f0c9e8b63b303a114eeb1a"
TOKEN_CAP_RERUN_FREEZE_HARNESS_SHA256 = "8bda75955557edb2acc2b730f795679ae32c67c1fbc51c18a240421941fc92af"
TOKEN_CAP_RERUN_ALLOWED_POLICY_DIFFERENCES = ("max_tokens",)
TOKEN_CAP_RERUN_FINISH_REASONS = {
    "stop",
    "length",
    "content_filter",
    "tool_calls",
    "error",
    "unknown",
}
MODEL_COMPARISON_ALLOWED_POLICY_DIFFERENCES = (
    "max_tokens",
    "model",
    "provider.require_parameters",
    "reasoning",
    "temperature",
    "top_p",
)
SONNET_CANDIDATE_MODEL = "anthropic/claude-sonnet-5"
SONNET_CANDIDATE_CANONICAL_SLUG = "anthropic/claude-sonnet-5-20260630"
SONNET_CANDIDATE_PROVIDER = "Anthropic"
SONNET_CANDIDATE_REASONING_EFFORT = "medium"
SONNET_CANDIDATE_MAX_TOKENS = 16_000
SONNET_CANDIDATE_TIMEOUT_S = 30
SONNET_RESPONSE_RESERVE_TOKENS = 1_024
SONNET_CANDIDATE_EXPECTED_CALLS = EXPECTED_TURNS * REPETITIONS
SONNET_CANDIDATE_ABSOLUTE_CALL_CAP = SONNET_CANDIDATE_EXPECTED_CALLS
SONNET_CANDIDATE_COST_CAP_USD = 25.0
SONNET_CANDIDATE_COST_MARGIN = 1.10
SONNET_CANDIDATE_TOKENIZER_MARGIN = 1.30
SONNET_CANDIDATE_REALISTIC_COMPLETION_TOKENS = 4_096
SONNET_CANDIDATE_PRICING_OBSERVED_AT = "2026-08-30T16:43:40Z"
SONNET_CANDIDATE_FREEZE_COMMIT = "306d08773beeb80eeb888f784a4dfe5ae2442fcc"
SONNET_CANDIDATE_FREEZE_HARNESS_SHA256 = (
    "c29ceee5306249ae9f7fe83eb405b1893d6b673e14975cbe58212d34eff99fdc"
)
SONNET_CANDIDATE_PRICING_USD_PER_TOKEN = {
    "prompt": 0.000002,
    "completion": 0.00001,
}
SONNET_ALLOWED_POLICY_DIFFERENCES = (
    "max_tokens",
    "model",
    "provider.order",
    "provider.require_parameters",
    "reasoning",
    "response_format",
    "temperature",
    "top_p",
)
SONNET_FINISH_REASONS = TOKEN_CAP_RERUN_FINISH_REASONS

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
    "generation_incomplete",
}
_PROVIDERS = {"google", "openai", "anthropic", "unknown"}
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
_MODEL_COMPARISON_DECISIONS = {
    "eligible_primary",
    "not_eligible",
    "inconclusive",
}
_MODEL_COMPARISON_FINAL_REASON_CODES = {
    "all_thresholds_met_no_regression",
    "semantic_threshold_missed",
    "dialogue_results_incomplete",
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
_MODEL_COMPARISON_CALL_KEYS = _CALL_KEYS | {
    "requested_reasoning_effort",
    "reasoning_excluded",
    "reasoning_tokens",
    "transport",
    "batch",
    "provider_fallbacks",
    "require_parameters",
    "max_tokens",
    "timeout_s",
    "sampling_parameters_present",
    "observed_service_tier",
}
_TOKEN_CAP_RERUN_CALL_KEYS = _MODEL_COMPARISON_CALL_KEYS | {
    "finish_reason",
    "native_finish_reason",
}
_MODEL_COMPARISON_FINAL_KEYS = _FINAL_KEYS | {
    "historical_artifact_sha256",
    "historical_primary_pass_count",
    "candidate_pass_count",
    "semantic_regression_count",
    "reproducible_semantic_failure_count",
    "runtime_cutover_authorized",
    "fallback_evaluated",
}
_SONNET_CALL_KEYS = _TOKEN_CAP_RERUN_CALL_KEYS | {
    "requested_provider",
    "response_format_strict",
    "response_schema_sha256",
    "structured_output_required",
    "tools_present",
}
_SONNET_SOURCE_SUMMARY_KEYS = _SOURCE_SUMMARY_KEYS | {
    "reasoning_tokens",
    "cost_per_call_usd",
    "finish_reason_counts",
    "native_finish_reason_counts",
    "metric_stats",
}
_SONNET_FINAL_KEYS = _MODEL_COMPARISON_FINAL_KEYS | {
    "valid_call_count",
    "finish_stop_count",
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_stimmung_response_format() -> dict[str, Any]:
    tones = list(RUNTIME_ALLOWED_TONES)
    return {
        "type": "json_schema",
        "json_schema": {
            "name": "affective_turn_signal_v1",
            "strict": True,
            "schema": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "schema_version",
                    "present",
                    "tones",
                    "dominant_tone",
                    "confidence",
                ],
                "properties": {
                    "schema_version": {
                        "type": "string",
                        "enum": [RUNTIME_SIGNAL_SCHEMA_VERSION],
                    },
                    "present": {"type": "boolean"},
                    "tones": {
                        "type": "array",
                        "minItems": 0,
                        "maxItems": len(tones),
                        "items": {
                            "type": "object",
                            "additionalProperties": False,
                            "required": ["tone", "strength"],
                            "properties": {
                                "tone": {"type": "string", "enum": tones},
                                "strength": {
                                    "type": "integer",
                                    "minimum": 1,
                                    "maximum": 10,
                                },
                            },
                        },
                    },
                    "dominant_tone": {
                        "anyOf": [
                            {"type": "string", "enum": tones},
                            {"type": "null"},
                        ]
                    },
                    "confidence": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                    },
                },
            },
        },
    }


def derive_stimmung_structural_maximum() -> dict[str, int]:
    if set(RUNTIME_SIGNAL_KEYS) != {
        "schema_version",
        "present",
        "tones",
        "dominant_tone",
        "confidence",
    }:
        raise ValueError("stimmung_runtime_signal_contract_changed")
    longest_tone = max(RUNTIME_ALLOWED_TONES, key=lambda value: (len(value), value))
    maximum_witness = _validate_affective_turn_signal(
        {
            "schema_version": RUNTIME_SIGNAL_SCHEMA_VERSION,
            "present": True,
            "tones": [
                {"tone": tone, "strength": 10}
                for tone in RUNTIME_ALLOWED_TONES
            ],
            "dominant_tone": longest_tone,
            "confidence": 1.0,
        }
    )
    return {
        "tone_count": len(RUNTIME_ALLOWED_TONES),
        "compact_chars": len(
            json.dumps(
                maximum_witness,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        ),
        "spaced_chars": len(json.dumps(maximum_witness, ensure_ascii=False)),
        "indent2_chars": len(
            json.dumps(maximum_witness, ensure_ascii=False, indent=2)
        ),
        "response_reserve_tokens": SONNET_RESPONSE_RESERVE_TOKENS,
        "reasoning_headroom_tokens": (
            SONNET_CANDIDATE_MAX_TOKENS - SONNET_RESPONSE_RESERVE_TOKENS
        ),
    }


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


def _model_comparison_configuration() -> Mapping[str, Any]:
    configuration = validation_model_policy.MODEL_COMPARISON_CONFIGURATIONS.get(
        MODEL_COMPARISON_CONFIGURATION_ID
    )
    if not isinstance(configuration, Mapping):
        raise ValueError("model_comparison_configuration_missing")
    if (
        configuration.get("model") != MODEL_COMPARISON_MODEL
        or configuration.get("reasoning_effort") != "medium"
        or "medium" not in tuple(configuration.get("supported_efforts") or ())
    ):
        raise ValueError("model_comparison_configuration_changed")
    return configuration


def _historical_primary_control(repo_root: Path) -> dict[str, Any]:
    records = load_historical_provider_artifact(repo_root)
    calls = [
        item
        for item in records
        if item.get("record_type") == "call" and item.get("source") == "primary"
    ]
    scores = [
        item
        for item in records
        if item.get("record_type") == "dialogue_score"
        and item.get("source") == "primary"
    ]
    if len(calls) != MODEL_COMPARISON_EXPECTED_CALLS or len(scores) != 32:
        raise ValueError("historical_primary_control_incomplete")
    return {
        "artifact_sha256": _sha256_file(_historical_artifact_path(repo_root)),
        "calls_sha256": _sha256_text(_compact_json(calls)),
        "call_count": len(calls),
        "dialogue_score_count": len(scores),
        "pass_count": sum(item.get("classification") == "pass" for item in scores),
        "fail_count": sum(item.get("classification") == "fail" for item in scores),
        "inconclusive_count": sum(
            item.get("classification") == "inconclusive" for item in scores
        ),
        "model": PRIMARY_MODEL,
        "prompt_sha256": calls[0]["prompt_sha256"],
        "corpus_sha256": calls[0]["corpus_sha256"],
    }


def build_model_comparison_protocol(
    repo_root: Path,
    *,
    freeze_commit: str,
) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(str(freeze_commit)) is None:
        raise ValueError("invalid_freeze_commit")
    configuration = _model_comparison_configuration()
    corpus, _ = _load_inputs(repo_root)
    base = _base_requests(repo_root)
    if (
        len(corpus["dialogues"]),
        len(base),
        sum(1 for item in base if item["evaluated"]),
    ) != (EXPECTED_DIALOGUES, EXPECTED_TURNS, EXPECTED_EVALUATED_STEPS):
        raise ValueError("frozen_corpus_dimensions_changed")
    if MODEL_COMPARISON_EXPECTED_CALLS != MODEL_COMPARISON_ABSOLUTE_CALL_CAP:
        raise ValueError("model_comparison_call_cap_mismatch")

    prompt_token_estimates = [
        token_utils.estimate_tokens(item["messages"], MODEL_COMPARISON_MODEL)
        for item in base
    ]
    estimated_cost = MODEL_COMPARISON_COST_MARGIN * (
        REPETITIONS
        * sum(prompt_token_estimates)
        * MODEL_COMPARISON_PRICING_USD_PER_TOKEN["prompt"]
        + MODEL_COMPARISON_EXPECTED_CALLS
        * MODEL_COMPARISON_MAX_TOKENS
        * MODEL_COMPARISON_PRICING_USD_PER_TOKEN["completion"]
    )
    estimated_cost = round(estimated_cost, 8)
    if estimated_cost > MODEL_COMPARISON_COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")

    historical_control = _historical_primary_control(repo_root)
    runtime_prompt_sha256 = _sha256_file(_prompt_path(repo_root))
    if historical_control["prompt_sha256"] != runtime_prompt_sha256:
        raise ValueError("historical_prompt_not_comparable")
    corpus_sha256 = _sha256_file(_corpus_path(repo_root))
    if historical_control["corpus_sha256"] != corpus_sha256:
        raise ValueError("historical_corpus_not_comparable")

    parameters = {
        "model": MODEL_COMPARISON_MODEL,
        "reasoning": {"effort": "medium", "exclude": True},
        "max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "provider": {"allow_fallbacks": False, "require_parameters": True},
        "transport": "standard",
        "repetitions": REPETITIONS,
        "order": ["candidate_primary:1", "candidate_primary:2"],
    }
    return {
        "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
        "artifact_version": MODEL_COMPARISON_ARTIFACT_VERSION,
        "campaign_kind": "stimmung_primary_model_comparison_v1",
        "freeze_commit": freeze_commit,
        "corpus_id": corpus["corpus_id"],
        "corpus_schema_version": corpus["schema_version"],
        "corpus_sha256": corpus_sha256,
        "prompt_sha256": runtime_prompt_sha256,
        "excluded_strengthening_candidate_sha256": _sha256_file(
            _strengthening_candidate_path(repo_root)
        ),
        "scorer_sha256": _sha256_file(
            repo_root / "benchmark/suites/stimmung/dialogic_semantics.py"
        ),
        "normalizer_sha256": _sha256_file(repo_root / "app/core/stimmung_agent.py"),
        "aggregator_sha256": _sha256_file(
            repo_root / "app/core/hermeneutic_node/inputs/stimmung_input.py"
        ),
        "message_builder_sha256": _sha256_file(repo_root / "app/core/stimmung_agent.py"),
        "harness_sha256": (
            MODEL_COMPARISON_FREEZE_HARNESS_SHA256
            if freeze_commit == MODEL_COMPARISON_FREEZE_COMMIT
            else _sha256_file(_harness_path(repo_root))
        ),
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
        "model": MODEL_COMPARISON_MODEL,
        "canonical_slug": configuration["canonical_slug"],
        "allowed_providers": list(configuration["allowed_providers"]),
        "reasoning": {"effort": "medium", "exclude": True},
        "max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "provider_policy": {"allow_fallbacks": False, "require_parameters": True},
        "transport": "standard",
        "policy_difference_allowlist": list(
            MODEL_COMPARISON_ALLOWED_POLICY_DIFFERENCES
        ),
        "repetitions": REPETITIONS,
        "dialogue_count": EXPECTED_DIALOGUES,
        "turn_count": EXPECTED_TURNS,
        "evaluated_step_count": EXPECTED_EVALUATED_STEPS,
        "expected_call_count": MODEL_COMPARISON_EXPECTED_CALLS,
        "absolute_call_cap": MODEL_COMPARISON_ABSOLUTE_CALL_CAP,
        "cost_cap_usd": MODEL_COMPARISON_COST_CAP_USD,
        "estimated_max_cost_usd": estimated_cost,
        "prompt_token_estimate_sum": REPETITIONS * sum(prompt_token_estimates),
        "maximum_estimated_prompt_tokens": max(prompt_token_estimates),
        "pricing_observed_at": MODEL_COMPARISON_PRICING_OBSERVED_AT,
        "pricing_usd_per_token": dict(MODEL_COMPARISON_PRICING_USD_PER_TOKEN),
        "historical_control": historical_control,
        "decision_rules": {
            "all_dialogues_all_repetitions_pass": "eligible_primary",
            "semantic_threshold_missed": "not_eligible",
            "incomplete_invalid_or_route_unknown": "inconclusive",
            "runtime_cutover_authorized": False,
        },
    }


def validate_model_comparison_protocol(
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if protocol.get("protocol_version") != MODEL_COMPARISON_PROTOCOL_VERSION:
        raise ValueError("model_comparison_protocol_version_invalid")
    expected = build_model_comparison_protocol(
        repo_root,
        freeze_commit=str(protocol.get("freeze_commit") or ""),
    )
    if dict(protocol) != expected:
        raise ValueError("model_comparison_protocol_freeze_mismatch")
    return {
        "dialogue_count": expected["dialogue_count"],
        "turn_count": expected["turn_count"],
        "evaluated_step_count": expected["evaluated_step_count"],
        "expected_call_count": expected["expected_call_count"],
        "estimated_max_cost_usd": expected["estimated_max_cost_usd"],
    }


def _model_comparison_artifact_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/results/stimmung" / MODEL_COMPARISON_ARTIFACT


def _baseline_saturation(repo_root: Path) -> dict[str, Any]:
    artifact_path = _model_comparison_artifact_path(repo_root)
    if _sha256_file(artifact_path) != MODEL_COMPARISON_ARTIFACT_SHA256:
        raise ValueError("token_cap_baseline_artifact_changed")
    calls = [
        item
        for item in load_jsonl(artifact_path)
        if item.get("record_type") == "call"
    ]
    invalid = [item for item in calls if item.get("status") == "json_error"]
    invalid_reasoning = [int(item["reasoning_tokens"]) for item in invalid]
    valid_reasoning = [
        int(item["reasoning_tokens"])
        for item in calls
        if item.get("status") == "ok"
    ]
    if (
        len(calls) != MODEL_COMPARISON_EXPECTED_CALLS
        or len(invalid) != 24
        or not invalid_reasoning
        or not valid_reasoning
    ):
        raise ValueError("token_cap_baseline_saturation_changed")
    return {
        "artifact_sha256": MODEL_COMPARISON_ARTIFACT_SHA256,
        "call_count": len(calls),
        "valid_call_count": sum(item.get("status") == "ok" for item in calls),
        "invalid_json_count": len(invalid),
        "invalid_completion_tokens": sorted(
            {int(item["completion_tokens"]) for item in invalid}
        ),
        "invalid_reasoning_tokens_min": min(invalid_reasoning),
        "invalid_reasoning_tokens_median": statistics.median(invalid_reasoning),
        "invalid_reasoning_tokens_max": max(invalid_reasoning),
        "valid_reasoning_tokens_median": statistics.median(valid_reasoning),
        "timeout_count": sum(item.get("status") == "timeout" for item in calls),
        "transport_error_count": sum(
            item.get("status") == "transport_error" for item in calls
        ),
        "finish_reason_observed": any("finish_reason" in item for item in calls),
        "native_finish_reason_observed": any(
            "native_finish_reason" in item for item in calls
        ),
    }


def build_token_cap_rerun_protocol(
    repo_root: Path,
    *,
    freeze_commit: str,
) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(str(freeze_commit)) is None:
        raise ValueError("invalid_freeze_commit")
    control = build_model_comparison_protocol(
        repo_root,
        freeze_commit=MODEL_COMPARISON_FREEZE_COMMIT,
    )
    prompt_token_estimate_sum = int(control["prompt_token_estimate_sum"])
    estimated_cost = round(
        prompt_token_estimate_sum
        * MODEL_COMPARISON_PRICING_USD_PER_TOKEN["prompt"]
        + MODEL_COMPARISON_EXPECTED_CALLS
        * TOKEN_CAP_RERUN_MAX_TOKENS
        * MODEL_COMPARISON_PRICING_USD_PER_TOKEN["completion"],
        8,
    )
    if estimated_cost > TOKEN_CAP_RERUN_COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")
    parameters = {
        "model": MODEL_COMPARISON_MODEL,
        "reasoning": {"effort": "medium", "exclude": True},
        "max_tokens": TOKEN_CAP_RERUN_MAX_TOKENS,
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "provider": {"allow_fallbacks": False, "require_parameters": True},
        "transport": "standard",
        "repetitions": REPETITIONS,
        "order": ["candidate_primary:1", "candidate_primary:2"],
    }
    return {
        **{
            key: value
            for key, value in control.items()
            if key
            not in {
                "protocol_version",
                "artifact_version",
                "campaign_kind",
                "freeze_commit",
                "harness_sha256",
                "parameters_sha256",
                "max_tokens",
                "policy_difference_allowlist",
                "cost_cap_usd",
                "estimated_max_cost_usd",
                "pricing_observed_at",
            }
        },
        "protocol_version": TOKEN_CAP_RERUN_PROTOCOL_VERSION,
        "artifact_version": TOKEN_CAP_RERUN_ARTIFACT_VERSION,
        "campaign_kind": "stimmung_primary_token_cap_rerun_v2",
        "freeze_commit": freeze_commit,
        "harness_sha256": (
            TOKEN_CAP_RERUN_FREEZE_HARNESS_SHA256
            if freeze_commit == TOKEN_CAP_RERUN_FREEZE_COMMIT
            else _sha256_file(_harness_path(repo_root))
        ),
        "parameters_sha256": _sha256_text(_compact_json(parameters)),
        "max_tokens": TOKEN_CAP_RERUN_MAX_TOKENS,
        "baseline_max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "policy_difference_allowlist": list(
            TOKEN_CAP_RERUN_ALLOWED_POLICY_DIFFERENCES
        ),
        "finish_reason_allowlist": sorted(TOKEN_CAP_RERUN_FINISH_REASONS),
        "baseline_saturation": _baseline_saturation(repo_root),
        "cost_cap_usd": TOKEN_CAP_RERUN_COST_CAP_USD,
        "estimated_max_cost_usd": estimated_cost,
        "pricing_observed_at": TOKEN_CAP_RERUN_PRICING_OBSERVED_AT,
    }


def validate_token_cap_rerun_protocol(
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if protocol.get("protocol_version") != TOKEN_CAP_RERUN_PROTOCOL_VERSION:
        raise ValueError("token_cap_rerun_protocol_version_invalid")
    expected = build_token_cap_rerun_protocol(
        repo_root,
        freeze_commit=str(protocol.get("freeze_commit") or ""),
    )
    if dict(protocol) != expected:
        raise ValueError("token_cap_rerun_protocol_freeze_mismatch")
    return {
        "dialogue_count": expected["dialogue_count"],
        "turn_count": expected["turn_count"],
        "evaluated_step_count": expected["evaluated_step_count"],
        "expected_call_count": expected["expected_call_count"],
        "estimated_max_cost_usd": expected["estimated_max_cost_usd"],
    }


def build_sonnet_candidate_protocol(
    repo_root: Path,
    *,
    freeze_commit: str,
) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(str(freeze_commit)) is None:
        raise ValueError("invalid_freeze_commit")
    corpus, _ = _load_inputs(repo_root)
    base = _base_requests(repo_root)
    if (
        len(corpus["dialogues"]),
        len(base),
        sum(1 for item in base if item["evaluated"]),
    ) != (EXPECTED_DIALOGUES, EXPECTED_TURNS, EXPECTED_EVALUATED_STEPS):
        raise ValueError("frozen_corpus_dimensions_changed")
    if SONNET_CANDIDATE_EXPECTED_CALLS != SONNET_CANDIDATE_ABSOLUTE_CALL_CAP:
        raise ValueError("sonnet_candidate_call_cap_mismatch")

    maximum = derive_stimmung_structural_maximum()
    if maximum["indent2_chars"] >= SONNET_RESPONSE_RESERVE_TOKENS:
        raise ValueError("sonnet_response_reserve_insufficient")
    prompt_token_estimates = [
        token_utils.estimate_tokens(item["messages"], SONNET_CANDIDATE_MODEL)
        for item in base
    ]
    prompt_token_estimate_sum = REPETITIONS * sum(prompt_token_estimates)
    conservative_prompt_tokens = math.ceil(
        prompt_token_estimate_sum * SONNET_CANDIDATE_TOKENIZER_MARGIN
    )
    theoretical_cost = round(
        conservative_prompt_tokens
        * SONNET_CANDIDATE_PRICING_USD_PER_TOKEN["prompt"]
        + SONNET_CANDIDATE_EXPECTED_CALLS
        * SONNET_CANDIDATE_MAX_TOKENS
        * SONNET_CANDIDATE_PRICING_USD_PER_TOKEN["completion"],
        8,
    )
    estimated_max_cost = round(
        theoretical_cost * SONNET_CANDIDATE_COST_MARGIN,
        8,
    )
    realistic_cost = round(
        conservative_prompt_tokens
        * SONNET_CANDIDATE_PRICING_USD_PER_TOKEN["prompt"]
        + SONNET_CANDIDATE_EXPECTED_CALLS
        * SONNET_CANDIDATE_REALISTIC_COMPLETION_TOKENS
        * SONNET_CANDIDATE_PRICING_USD_PER_TOKEN["completion"],
        8,
    )
    if estimated_max_cost > SONNET_CANDIDATE_COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")

    response_format = build_stimmung_response_format()
    parameters = {
        "model": SONNET_CANDIDATE_MODEL,
        "reasoning": {
            "effort": SONNET_CANDIDATE_REASONING_EFFORT,
            "exclude": True,
        },
        "max_tokens": SONNET_CANDIDATE_MAX_TOKENS,
        "timeout_s": SONNET_CANDIDATE_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "response_format": response_format,
        "provider": {
            "order": ["Anthropic"],
            "allow_fallbacks": False,
            "require_parameters": True,
        },
        "transport": "standard",
        "repetitions": REPETITIONS,
        "order": ["candidate_primary:1", "candidate_primary:2"],
    }
    historical_control = _historical_primary_control(repo_root)
    runtime_prompt_sha256 = _sha256_file(_prompt_path(repo_root))
    corpus_sha256 = _sha256_file(_corpus_path(repo_root))
    if historical_control["prompt_sha256"] != runtime_prompt_sha256:
        raise ValueError("historical_prompt_not_comparable")
    if historical_control["corpus_sha256"] != corpus_sha256:
        raise ValueError("historical_corpus_not_comparable")
    return {
        "protocol_version": SONNET_CANDIDATE_PROTOCOL_VERSION,
        "artifact_version": SONNET_CANDIDATE_ARTIFACT_VERSION,
        "campaign_kind": "stimmung_sonnet_5_medium_candidate_v1",
        "freeze_commit": freeze_commit,
        "corpus_id": corpus["corpus_id"],
        "corpus_schema_version": corpus["schema_version"],
        "corpus_sha256": corpus_sha256,
        "prompt_sha256": runtime_prompt_sha256,
        "scorer_sha256": _sha256_file(
            repo_root / "benchmark/suites/stimmung/dialogic_semantics.py"
        ),
        "normalizer_sha256": _sha256_file(repo_root / "app/core/stimmung_agent.py"),
        "aggregator_sha256": _sha256_file(
            repo_root / "app/core/hermeneutic_node/inputs/stimmung_input.py"
        ),
        "message_builder_sha256": _sha256_file(
            repo_root / "app/core/stimmung_agent.py"
        ),
        "harness_sha256": (
            SONNET_CANDIDATE_FREEZE_HARNESS_SHA256
            if freeze_commit == SONNET_CANDIDATE_FREEZE_COMMIT
            else _sha256_file(_harness_path(repo_root))
        ),
        "parameters_sha256": _sha256_text(_compact_json(parameters)),
        "response_schema_sha256": _sha256_text(_compact_json(response_format)),
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
        "model": SONNET_CANDIDATE_MODEL,
        "canonical_slug": SONNET_CANDIDATE_CANONICAL_SLUG,
        "allowed_providers": [SONNET_CANDIDATE_PROVIDER],
        "reasoning": {
            "effort": SONNET_CANDIDATE_REASONING_EFFORT,
            "exclude": True,
        },
        "max_tokens": SONNET_CANDIDATE_MAX_TOKENS,
        "response_reserve_tokens": SONNET_RESPONSE_RESERVE_TOKENS,
        "reasoning_headroom_tokens": maximum["reasoning_headroom_tokens"],
        "structural_maximum": maximum,
        "timeout_s": SONNET_CANDIDATE_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "response_format": response_format,
        "provider_policy": {
            "order": ["Anthropic"],
            "allow_fallbacks": False,
            "require_parameters": True,
        },
        "transport": "standard",
        "policy_difference_allowlist": list(SONNET_ALLOWED_POLICY_DIFFERENCES),
        "repetitions": REPETITIONS,
        "dialogue_count": EXPECTED_DIALOGUES,
        "turn_count": EXPECTED_TURNS,
        "evaluated_step_count": EXPECTED_EVALUATED_STEPS,
        "expected_call_count": SONNET_CANDIDATE_EXPECTED_CALLS,
        "absolute_call_cap": SONNET_CANDIDATE_ABSOLUTE_CALL_CAP,
        "cost_cap_usd": SONNET_CANDIDATE_COST_CAP_USD,
        "theoretical_max_cost_usd": theoretical_cost,
        "estimated_max_cost_usd": estimated_max_cost,
        "realistic_estimated_cost_usd": realistic_cost,
        "realistic_completion_tokens_per_call": (
            SONNET_CANDIDATE_REALISTIC_COMPLETION_TOKENS
        ),
        "prompt_token_estimate_sum": prompt_token_estimate_sum,
        "conservative_prompt_token_estimate_sum": conservative_prompt_tokens,
        "maximum_estimated_prompt_tokens": max(prompt_token_estimates),
        "pricing_observed_at": SONNET_CANDIDATE_PRICING_OBSERVED_AT,
        "pricing_usd_per_token": dict(
            SONNET_CANDIDATE_PRICING_USD_PER_TOKEN
        ),
        "model_metadata": {
            "context_length": 1_000_000,
            "max_completion_tokens": 128_000,
            "structured_outputs": True,
            "reasoning_efforts": ["low", "medium", "high", "xhigh", "max"],
            "adaptive_thinking": True,
            "standard_route": True,
            "batch": False,
        },
        "historical_control": historical_control,
        "decision_rules": {
            "all_calls_stop_and_all_scores_pass": "eligible_primary",
            "complete_semantic_threshold_missed": "not_eligible",
            "incomplete_invalid_or_route_unknown": "inconclusive",
            "conditional_runtime_cutover": True,
        },
    }


def validate_sonnet_candidate_protocol(
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    if protocol.get("protocol_version") != SONNET_CANDIDATE_PROTOCOL_VERSION:
        raise ValueError("sonnet_candidate_protocol_version_invalid")
    expected = build_sonnet_candidate_protocol(
        repo_root,
        freeze_commit=str(protocol.get("freeze_commit") or ""),
    )
    if dict(protocol) != expected:
        raise ValueError("sonnet_candidate_protocol_freeze_mismatch")
    return {
        "dialogue_count": expected["dialogue_count"],
        "turn_count": expected["turn_count"],
        "evaluated_step_count": expected["evaluated_step_count"],
        "expected_call_count": expected["expected_call_count"],
        "estimated_max_cost_usd": expected["estimated_max_cost_usd"],
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


def validate_model_comparison_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {"model", "messages", "max_tokens", "reasoning", "provider"}
    normalized = dict(payload)
    if set(normalized) != expected_keys:
        raise ValueError("model_comparison_payload_fields_invalid")
    if normalized.get("model") != MODEL_COMPARISON_MODEL or ":" in str(
        normalized.get("model")
    ).removeprefix("google"):
        raise ValueError("model_comparison_payload_model_invalid")
    messages = normalized.get("messages")
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or any(
            not isinstance(message, Mapping)
            or set(message) != {"role", "content"}
            or message.get("role") not in {"system", "user"}
            or not isinstance(message.get("content"), str)
            or not message["content"]
            for message in messages
        )
    ):
        raise ValueError("model_comparison_payload_messages_invalid")
    if normalized.get("max_tokens") != MODEL_COMPARISON_MAX_TOKENS:
        raise ValueError("model_comparison_payload_max_tokens_invalid")
    if normalized.get("reasoning") != {"effort": "medium", "exclude": True}:
        raise ValueError("model_comparison_payload_reasoning_invalid")
    if normalized.get("provider") != {
        "allow_fallbacks": False,
        "require_parameters": True,
    }:
        raise ValueError("model_comparison_payload_provider_invalid")
    return normalized


def _difference_paths(left: Any, right: Any, *, prefix: str = "") -> set[str]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        differences: set[str] = set()
        for key in sorted(set(left) | set(right)):
            child = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                differences.add(child)
            else:
                differences.update(_difference_paths(left[key], right[key], prefix=child))
        return differences
    return set() if left == right else {prefix}


def validate_model_policy_difference(
    historical_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
) -> list[str]:
    validate_model_comparison_payload(candidate_payload)
    differences = _difference_paths(historical_payload, candidate_payload)
    if differences != set(MODEL_COMPARISON_ALLOWED_POLICY_DIFFERENCES):
        raise ValueError("model_comparison_policy_difference_invalid")
    return sorted(differences)


def _build_model_comparison_payload(messages: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    payload = validation_model_policy.build_model_comparison_payload(
        messages,
        MODEL_COMPARISON_CONFIGURATION_ID,
    )
    payload["max_tokens"] = MODEL_COMPARISON_MAX_TOKENS
    return validate_model_comparison_payload(payload)


def build_model_comparison_request_schedule(
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validate_model_comparison_protocol(protocol, repo_root)
    base = _base_requests(repo_root)
    historical_protocol = build_protocol(
        repo_root,
        freeze_commit=PHASE_A_FREEZE_COMMIT,
    )
    historical_primary = [
        item
        for item in build_request_schedule(repo_root, historical_protocol)
        if item["source"] == "primary"
    ]
    schedule: list[dict[str, Any]] = []
    sequence = 0
    for repetition in range(1, REPETITIONS + 1):
        for item in base:
            sequence += 1
            payload = _build_model_comparison_payload(item["messages"])
            control = historical_primary[sequence - 1]
            validate_model_policy_difference(control["payload"], payload)
            schedule.append(
                {
                    **item,
                    "sequence": sequence,
                    "source": "primary",
                    "repetition": repetition,
                    "payload": payload,
                }
            )
    if len(schedule) != MODEL_COMPARISON_EXPECTED_CALLS:
        raise ValueError("model_comparison_call_schedule_mismatch")
    return schedule


def validate_token_cap_rerun_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    if normalized.get("max_tokens") != TOKEN_CAP_RERUN_MAX_TOKENS:
        raise ValueError("token_cap_rerun_payload_max_tokens_invalid")
    control = {**normalized, "max_tokens": MODEL_COMPARISON_MAX_TOKENS}
    validate_model_comparison_payload(control)
    return normalized


def validate_token_cap_rerun_policy_difference(
    control_payload: Mapping[str, Any],
    rerun_payload: Mapping[str, Any],
) -> list[str]:
    try:
        validate_model_comparison_payload(control_payload)
        validate_token_cap_rerun_payload(rerun_payload)
    except ValueError as exc:
        raise ValueError("token_cap_rerun_policy_difference_invalid") from exc
    differences = _difference_paths(control_payload, rerun_payload)
    if differences != set(TOKEN_CAP_RERUN_ALLOWED_POLICY_DIFFERENCES):
        raise ValueError("token_cap_rerun_policy_difference_invalid")
    return sorted(differences)


def build_token_cap_rerun_request_schedule(
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validate_token_cap_rerun_protocol(protocol, repo_root)
    control_protocol = build_model_comparison_protocol(
        repo_root,
        freeze_commit=MODEL_COMPARISON_FREEZE_COMMIT,
    )
    control_schedule = build_model_comparison_request_schedule(
        repo_root,
        control_protocol,
    )
    schedule: list[dict[str, Any]] = []
    for item in control_schedule:
        payload = {**item["payload"], "max_tokens": TOKEN_CAP_RERUN_MAX_TOKENS}
        validate_token_cap_rerun_policy_difference(item["payload"], payload)
        schedule.append({**item, "payload": payload})
    if (
        len(schedule) != MODEL_COMPARISON_EXPECTED_CALLS
        or {item["source"] for item in schedule} != {"primary"}
        or any(item["payload"]["model"] != MODEL_COMPARISON_MODEL for item in schedule)
    ):
        raise ValueError("token_cap_rerun_call_schedule_invalid")
    return schedule


def validate_sonnet_candidate_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    expected_keys = {
        "model",
        "messages",
        "max_tokens",
        "reasoning",
        "provider",
        "response_format",
    }
    normalized = dict(payload)
    if set(normalized) != expected_keys:
        raise ValueError("sonnet_candidate_payload_fields_invalid")
    if normalized.get("model") != SONNET_CANDIDATE_MODEL or ":" in str(
        normalized.get("model")
    ).removeprefix("anthropic"):
        raise ValueError("sonnet_candidate_payload_model_invalid")
    messages = normalized.get("messages")
    if (
        not isinstance(messages, list)
        or len(messages) != 2
        or any(
            not isinstance(message, Mapping)
            or set(message) != {"role", "content"}
            or message.get("role") not in {"system", "user"}
            or not isinstance(message.get("content"), str)
            or not message["content"]
            for message in messages
        )
    ):
        raise ValueError("sonnet_candidate_payload_messages_invalid")
    if normalized.get("max_tokens") != SONNET_CANDIDATE_MAX_TOKENS:
        raise ValueError("sonnet_candidate_payload_max_tokens_invalid")
    if normalized.get("reasoning") != {
        "effort": SONNET_CANDIDATE_REASONING_EFFORT,
        "exclude": True,
    }:
        raise ValueError("sonnet_candidate_payload_reasoning_invalid")
    if normalized.get("provider") != {
        "order": ["Anthropic"],
        "allow_fallbacks": False,
        "require_parameters": True,
    }:
        raise ValueError("sonnet_candidate_payload_provider_invalid")
    if normalized.get("response_format") != build_stimmung_response_format():
        raise ValueError("sonnet_candidate_payload_schema_invalid")
    return normalized


def validate_sonnet_model_policy_difference(
    historical_payload: Mapping[str, Any],
    candidate_payload: Mapping[str, Any],
) -> list[str]:
    validate_sonnet_candidate_payload(candidate_payload)
    differences = _difference_paths(historical_payload, candidate_payload)
    if differences != set(SONNET_ALLOWED_POLICY_DIFFERENCES):
        raise ValueError("sonnet_candidate_policy_difference_invalid")
    return sorted(differences)


def _build_sonnet_candidate_payload(
    messages: Sequence[Mapping[str, str]],
) -> dict[str, Any]:
    return validate_sonnet_candidate_payload(
        {
            "model": SONNET_CANDIDATE_MODEL,
            "messages": [dict(item) for item in messages],
            "max_tokens": SONNET_CANDIDATE_MAX_TOKENS,
            "reasoning": {
                "effort": SONNET_CANDIDATE_REASONING_EFFORT,
                "exclude": True,
            },
            "provider": {
                "order": ["Anthropic"],
                "allow_fallbacks": False,
                "require_parameters": True,
            },
            "response_format": build_stimmung_response_format(),
        }
    )


def build_sonnet_candidate_request_schedule(
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validate_sonnet_candidate_protocol(protocol, repo_root)
    base = _base_requests(repo_root)
    historical_protocol = build_protocol(
        repo_root,
        freeze_commit=PHASE_A_FREEZE_COMMIT,
    )
    historical_primary = [
        item
        for item in build_request_schedule(repo_root, historical_protocol)
        if item["source"] == "primary"
    ]
    schedule: list[dict[str, Any]] = []
    sequence = 0
    for repetition in range(1, REPETITIONS + 1):
        for item in base:
            sequence += 1
            payload = _build_sonnet_candidate_payload(item["messages"])
            control = historical_primary[sequence - 1]
            validate_sonnet_model_policy_difference(control["payload"], payload)
            schedule.append(
                {
                    **item,
                    "sequence": sequence,
                    "source": "primary",
                    "repetition": repetition,
                    "payload": payload,
                }
            )
    if (
        len(schedule) != SONNET_CANDIDATE_EXPECTED_CALLS
        or {item["source"] for item in schedule} != {"primary"}
        or any(
            item["payload"]["model"] != SONNET_CANDIDATE_MODEL
            or item["payload"]["provider"].get("allow_fallbacks") is not False
            for item in schedule
        )
    ):
        raise ValueError("sonnet_candidate_call_schedule_invalid")
    return schedule


def _provider_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    if "google" in text:
        return "google"
    if "openai" in text:
        return "openai"
    if "anthropic" in text:
        return "anthropic"
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


def _classify_response(
    response: Mapping[str, Any],
    requested_model: str,
    *,
    allowed_observed_models: set[str] | None = None,
    allowed_observed_providers: set[str] | None = None,
) -> dict[str, Any]:
    latency = _float_metric(response.get("elapsed_ms"))
    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    observed_model_raw = str(response.get("model") or "").strip()
    allowed_models = allowed_observed_models or {requested_model}
    observed_model = observed_model_raw if observed_model_raw in allowed_models else "unknown"
    expected_providers = allowed_observed_providers or {
        "google" if requested_model.startswith("google/") else "openai"
    }
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
    if observed_model == "unknown" or observed_provider not in expected_providers:
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


def _reasoning_tokens_or_none(response: Mapping[str, Any]) -> int | None:
    usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping) and "reasoning_tokens" in details:
        value = details.get("reasoning_tokens")
    else:
        value = usage.get("reasoning_tokens")
    return _int_metric(value)


def _closed_finish_reason(value: Any) -> str:
    normalized = str(value or "").strip().lower()
    aliases = {
        "stop": "stop",
        "end_turn": "stop",
        "length": "length",
        "max_tokens": "length",
        "max_tokens_reached": "length",
        "content_filter": "content_filter",
        "safety": "content_filter",
        "tool_calls": "tool_calls",
        "tool_call": "tool_calls",
        "error": "error",
    }
    return aliases.get(normalized, "unknown")


def _model_comparison_call_record(
    *,
    plan: Mapping[str, Any],
    response: Mapping[str, Any],
    outcome: Mapping[str, Any],
    aggregate: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    service_tier = str(response.get("service_tier") or "").strip().lower()
    record = {
        "artifact_version": protocol["artifact_version"],
        "protocol_version": protocol["protocol_version"],
        "record_type": "call",
        "sequence": plan["sequence"],
        "dialogue_id": plan["dialogue_id"],
        "turn_id": plan["turn_id"],
        "evaluated": plan["evaluated"],
        "source": "primary",
        "repetition": plan["repetition"],
        "requested_model": MODEL_COMPARISON_MODEL,
        "requested_reasoning_effort": "medium",
        "reasoning_excluded": True,
        "reasoning_tokens": _reasoning_tokens_or_none(response),
        "transport": "standard",
        "batch": False,
        "provider_fallbacks": False,
        "require_parameters": True,
        "max_tokens": protocol["max_tokens"],
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "sampling_parameters_present": any(
            key in plan["payload"] for key in ("temperature", "top_p")
        ),
        "observed_model": outcome["observed_model"],
        "observed_provider": outcome["observed_provider"],
        "observed_service_tier": service_tier,
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
    if protocol["protocol_version"] == TOKEN_CAP_RERUN_PROTOCOL_VERSION:
        record["finish_reason"] = _closed_finish_reason(
            response.get("finish_reason")
        )
        record["native_finish_reason"] = _closed_finish_reason(
            response.get("native_finish_reason")
        )
    return record


def _model_comparison_decision(
    calls: Sequence[Mapping[str, Any]],
    scores: Sequence[Mapping[str, Any]],
    *,
    historical_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected_groups = {
        repetition: {
            str(item.get("dialogue_id") or "")
            for item in scores
            if item.get("repetition") == repetition
        }
        for repetition in (1, 2)
    }
    historical_primary_scores = [
        item
        for item in historical_records
        if item.get("record_type") == "dialogue_score"
        and item.get("source") == "primary"
    ]
    historical_passes = {
        (int(item["repetition"]), str(item["dialogue_id"]))
        for item in historical_primary_scores
        if item.get("classification") == "pass"
    }
    semantic_regressions = sum(
        (int(item.get("repetition") or 0), str(item.get("dialogue_id") or ""))
        in historical_passes
        for item in scores
        if item.get("classification") == "fail"
    )
    failed_by_dialogue: dict[str, set[int]] = {}
    for item in scores:
        if item.get("classification") == "fail":
            failed_by_dialogue.setdefault(str(item["dialogue_id"]), set()).add(
                int(item["repetition"])
            )
    reproducible_failures = sum(
        repetitions == {1, 2} for repetitions in failed_by_dialogue.values()
    )
    complete_shape = (
        len(calls) == MODEL_COMPARISON_EXPECTED_CALLS
        and len(scores) == 32
        and all(len(ids) == EXPECTED_DIALOGUES for ids in expected_groups.values())
    )
    metrics_complete = complete_shape and all(
        item.get("status") == "ok"
        and item.get("latency_ms") is not None
        and item.get("prompt_tokens") is not None
        and item.get("completion_tokens") is not None
        and item.get("reasoning_tokens") is not None
        and item.get("total_tokens") is not None
        and item.get("cost_usd") is not None
        and item.get("observed_model")
        in {MODEL_COMPARISON_MODEL, _model_comparison_configuration()["canonical_slug"]}
        and item.get("observed_provider") == "google"
        and item.get("observed_service_tier") in {"", "default", "standard"}
        for item in calls
    )
    if not complete_shape:
        decision, reason = "inconclusive", "dialogue_results_incomplete"
    elif not metrics_complete or any(
        item.get("classification") == "inconclusive" for item in scores
    ):
        decision, reason = "inconclusive", "provider_results_or_metrics_incomplete"
    elif any(item.get("classification") == "fail" for item in scores):
        decision, reason = "not_eligible", "semantic_threshold_missed"
    else:
        decision, reason = "eligible_primary", "all_thresholds_met_no_regression"
    return {
        "decision": decision,
        "reason_codes": [reason],
        "next_micro_lot": None,
        "historical_primary_pass_count": sum(
            item.get("classification") == "pass" for item in historical_primary_scores
        ),
        "candidate_pass_count": sum(
            item.get("classification") == "pass" for item in scores
        ),
        "semantic_regression_count": semantic_regressions,
        "reproducible_semantic_failure_count": reproducible_failures,
        "runtime_cutover_authorized": False,
        "fallback_evaluated": False,
    }


def _model_comparison_summary_records(
    calls: Sequence[Mapping[str, Any]],
    dialogue_scores: Sequence[Mapping[str, Any]],
    corpus: Mapping[str, Any],
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = list(dialogue_scores)
    repetition_decisions: list[str] = []
    for repetition in (1, 2):
        selected = [
            item for item in dialogue_scores if item["repetition"] == repetition
        ]
        summary = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=corpus,
            dialogue_scores=selected,
            provider_results_observed=True,
        )
        repetition_decisions.append(summary["decision"])
        results.append(
            {
                "artifact_version": protocol["artifact_version"],
                "protocol_version": protocol["protocol_version"],
                "record_type": "repetition_summary",
                "source": "primary",
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
    latencies = [float(item["latency_ms"]) for item in calls if item["latency_ms"] is not None]
    results.append(
        {
            "artifact_version": protocol["artifact_version"],
            "protocol_version": protocol["protocol_version"],
            "record_type": "source_summary",
            "source": "primary",
            "repetition_decisions": repetition_decisions,
            "call_count": len(calls),
            "ok_count": sum(item["status"] == "ok" for item in calls),
            "semantic_failure_count": sum(
                item["classification"] == "fail" for item in dialogue_scores
            ),
            "inconclusive_dialogue_count": sum(
                item["classification"] == "inconclusive" for item in dialogue_scores
            ),
            "latency_median_ms": round(statistics.median(latencies), 3) if latencies else None,
            "latency_p95_ms": _percentile(latencies, 0.95),
            "prompt_tokens": _sum_metric(calls, "prompt_tokens"),
            "completion_tokens": _sum_metric(calls, "completion_tokens"),
            "total_tokens": _sum_metric(calls, "total_tokens"),
            "cost_usd": _sum_cost(calls),
        }
    )
    decision = _model_comparison_decision(
        calls,
        dialogue_scores,
        historical_records=load_historical_provider_artifact(repo_root),
    )
    results.append(
        {
            "artifact_version": protocol["artifact_version"],
            "protocol_version": protocol["protocol_version"],
            "record_type": "final_summary",
            **decision,
            "call_count": len(calls),
            "dialogue_score_count": len(dialogue_scores),
            "cost_usd": _sum_cost(calls),
            "calls_sha256": _sha256_text(_compact_json(list(calls))),
            "historical_artifact_sha256": protocol["historical_control"][
                "artifact_sha256"
            ],
        }
    )
    return results


def run_model_comparison_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    token_cap_rerun = (
        protocol.get("protocol_version") == TOKEN_CAP_RERUN_PROTOCOL_VERSION
    )
    schedule = (
        build_token_cap_rerun_request_schedule(repo_root, protocol)
        if token_cap_rerun
        else build_model_comparison_request_schedule(repo_root, protocol)
    )
    corpus, _ = _load_inputs(repo_root)
    cases = {item["id"]: item for item in corpus["dialogues"]}
    records: list[dict[str, Any]] = []
    dialogue_scores: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    group: tuple[int, str] | None = None

    def finish_dialogue() -> None:
        if group is None:
            return
        repetition, dialogue_id = group
        score = dialogic_semantics.score_dialogue(cases[dialogue_id], observations)
        dialogue_scores.append(
            _dialogue_score_record(
                score,
                source="primary",
                repetition=repetition,
                protocol=protocol,
            )
        )

    allowed_models = {
        MODEL_COMPARISON_MODEL,
        str(protocol["canonical_slug"]),
    }
    allowed_providers = {
        _provider_name(item) for item in protocol["allowed_providers"]
    }
    for plan in schedule:
        next_group = (int(plan["repetition"]), str(plan["dialogue_id"]))
        if group != next_group:
            finish_dialogue()
            group = next_group
            history = []
            observations = []
        turn = cases[plan["dialogue_id"]]["turns"][plan["turn_id"] - 1]
        user_message = {
            "role": "user",
            "content": turn["user"],
            "timestamp": None,
            "meta": {},
        }
        history.append(user_message)
        response = client.chat_completion(
            dict(plan["payload"]),
            caller="stimmung_agent",
            timeout_s=MODEL_COMPARISON_TIMEOUT_S,
        )
        outcome = _classify_response(
            response,
            MODEL_COMPARISON_MODEL,
            allowed_observed_models=allowed_models,
            allowed_observed_providers=allowed_providers,
        )
        service_tier = str(response.get("service_tier") or "").strip().lower()
        if outcome["status"] == "ok" and service_tier not in {"", "default", "standard"}:
            outcome = {
                **outcome,
                "status": "transport_error",
                "reason_code": "route_mismatch",
                "signal": None,
            }
        attached_signal = (
            outcome["signal"] if outcome["status"] == "ok" else _build_fail_open_signal()
        )
        user_message["meta"]["affective_turn_signal"] = attached_signal
        aggregate = build_stimmung_input(messages=history)
        record = _model_comparison_call_record(
            plan=plan,
            response=response,
            outcome=outcome,
            aggregate=aggregate,
            protocol=protocol,
        )
        (
            validate_token_cap_rerun_record(record)
            if token_cap_rerun
            else validate_model_comparison_record(record)
        )
        records.append(record)
        if plan["evaluated"]:
            observations.append(
                {
                    "turn_id": plan["turn_id"],
                    "execution_status": outcome["status"],
                    "source": "primary",
                    "signal": outcome["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append(
            {"role": "assistant", "content": turn["assistant"], "timestamp": None}
        )
        observed_cost = _sum_cost(records)
        if observed_cost is not None and observed_cost > float(protocol["cost_cap_usd"]):
            raise ValueError("provider_cost_cap_exceeded")
        if callable(progress):
            progress(int(plan["sequence"]), MODEL_COMPARISON_EXPECTED_CALLS, dict(record))
    finish_dialogue()
    records.extend(
        _model_comparison_summary_records(
            records,
            dialogue_scores,
            corpus,
            repo_root=repo_root,
            protocol=protocol,
        )
    )
    return records


def run_token_cap_rerun_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    validate_token_cap_rerun_protocol(protocol, repo_root)
    return run_model_comparison_campaign(
        repo_root=repo_root,
        protocol=protocol,
        client=client,
        progress=progress,
    )


def _sonnet_candidate_call_record(
    *,
    plan: Mapping[str, Any],
    response: Mapping[str, Any],
    outcome: Mapping[str, Any],
    aggregate: Mapping[str, Any],
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    service_tier = str(response.get("service_tier") or "").strip().lower()
    return {
        "artifact_version": protocol["artifact_version"],
        "protocol_version": protocol["protocol_version"],
        "record_type": "call",
        "sequence": plan["sequence"],
        "dialogue_id": plan["dialogue_id"],
        "turn_id": plan["turn_id"],
        "evaluated": plan["evaluated"],
        "source": "primary",
        "repetition": plan["repetition"],
        "requested_model": SONNET_CANDIDATE_MODEL,
        "requested_provider": "anthropic",
        "requested_reasoning_effort": SONNET_CANDIDATE_REASONING_EFFORT,
        "reasoning_excluded": True,
        "reasoning_tokens": _reasoning_tokens_or_none(response),
        "transport": "standard",
        "batch": False,
        "provider_fallbacks": False,
        "require_parameters": True,
        "max_tokens": SONNET_CANDIDATE_MAX_TOKENS,
        "timeout_s": SONNET_CANDIDATE_TIMEOUT_S,
        "sampling_parameters_present": any(
            key in plan["payload"] for key in ("temperature", "top_p", "top_k")
        ),
        "response_format_strict": True,
        "response_schema_sha256": protocol["response_schema_sha256"],
        "structured_output_required": True,
        "tools_present": any(
            key in plan["payload"] for key in ("tools", "tool_choice")
        ),
        "finish_reason": _closed_finish_reason(response.get("finish_reason")),
        "native_finish_reason": _closed_finish_reason(
            response.get("native_finish_reason")
        ),
        "observed_model": outcome["observed_model"],
        "observed_provider": outcome["observed_provider"],
        "observed_service_tier": service_tier,
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


def decide_sonnet_candidate(
    calls: Sequence[Mapping[str, Any]],
    scores: Sequence[Mapping[str, Any]],
    *,
    historical_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    grouped_ids = {
        repetition: [
            str(item.get("dialogue_id") or "")
            for item in scores
            if item.get("repetition") == repetition
        ]
        for repetition in (1, 2)
    }
    historical_primary_scores = [
        item
        for item in historical_records
        if item.get("record_type") == "dialogue_score"
        and item.get("source") == "primary"
    ]
    historical_passes = {
        (int(item["repetition"]), str(item["dialogue_id"]))
        for item in historical_primary_scores
        if item.get("classification") == "pass"
    }
    semantic_regressions = sum(
        (int(item.get("repetition") or 0), str(item.get("dialogue_id") or ""))
        in historical_passes
        for item in scores
        if item.get("classification") == "fail"
    )
    failed_by_dialogue: dict[str, set[int]] = {}
    for item in scores:
        if item.get("classification") == "fail":
            failed_by_dialogue.setdefault(str(item["dialogue_id"]), set()).add(
                int(item["repetition"])
            )
    reproducible_failures = sum(
        repetitions == {1, 2} for repetitions in failed_by_dialogue.values()
    )
    complete_shape = (
        len(calls) == SONNET_CANDIDATE_EXPECTED_CALLS
        and len(scores) == 32
        and all(
            len(ids) == EXPECTED_DIALOGUES
            and len(set(ids)) == EXPECTED_DIALOGUES
            for ids in grouped_ids.values()
        )
    )
    technical_complete = complete_shape and all(
        item.get("status") == "ok"
        and item.get("finish_reason") == "stop"
        and item.get("native_finish_reason") in {"stop", "unknown"}
        and item.get("latency_ms") is not None
        and item.get("prompt_tokens") is not None
        and item.get("completion_tokens") is not None
        and item.get("reasoning_tokens") is not None
        and item.get("total_tokens") is not None
        and item.get("cost_usd") is not None
        and item.get("observed_model")
        in {SONNET_CANDIDATE_MODEL, SONNET_CANDIDATE_CANONICAL_SLUG}
        and item.get("observed_provider") == "anthropic"
        and item.get("observed_service_tier") in {"", "default", "standard"}
        for item in calls
    )
    if not complete_shape:
        decision, reason = "inconclusive", "dialogue_results_incomplete"
    elif not technical_complete or any(
        item.get("classification") == "inconclusive" for item in scores
    ):
        decision, reason = "inconclusive", "provider_results_or_metrics_incomplete"
    elif any(item.get("classification") == "fail" for item in scores):
        decision, reason = "not_eligible", "semantic_threshold_missed"
    else:
        decision, reason = "eligible_primary", "all_thresholds_met_no_regression"
    return {
        "decision": decision,
        "reason_codes": [reason],
        "next_micro_lot": None,
        "historical_primary_pass_count": sum(
            item.get("classification") == "pass"
            for item in historical_primary_scores
        ),
        "candidate_pass_count": sum(
            item.get("classification") == "pass" for item in scores
        ),
        "semantic_regression_count": semantic_regressions,
        "reproducible_semantic_failure_count": reproducible_failures,
        "runtime_cutover_authorized": decision == "eligible_primary",
        "fallback_evaluated": False,
        "valid_call_count": sum(item.get("status") == "ok" for item in calls),
        "finish_stop_count": sum(
            item.get("finish_reason") == "stop" for item in calls
        ),
    }


def _metric_distribution(
    records: Sequence[Mapping[str, Any]],
    key: str,
) -> dict[str, float | int | None]:
    values = [item.get(key) for item in records]
    if not values or any(value is None for value in values):
        return {"min": None, "median": None, "p95": None, "max": None}
    numeric = [float(value) for value in values]
    def normalized(value: float) -> float | int:
        return int(value) if float(value).is_integer() else round(float(value), 3)

    return {
        "min": normalized(min(numeric)),
        "median": normalized(statistics.median(numeric)),
        "p95": normalized(float(_percentile(numeric, 0.95))),
        "max": normalized(max(numeric)),
    }


def _closed_reason_counts(
    records: Sequence[Mapping[str, Any]],
    key: str,
) -> dict[str, int]:
    return {
        reason: sum(item.get(key) == reason for item in records)
        for reason in sorted(SONNET_FINISH_REASONS)
    }


def _sonnet_candidate_summary_records(
    calls: Sequence[Mapping[str, Any]],
    dialogue_scores: Sequence[Mapping[str, Any]],
    corpus: Mapping[str, Any],
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = list(dialogue_scores)
    repetition_decisions: list[str] = []
    for repetition in (1, 2):
        selected = [
            item for item in dialogue_scores if item["repetition"] == repetition
        ]
        summary = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=corpus,
            dialogue_scores=selected,
            provider_results_observed=True,
        )
        repetition_decisions.append(summary["decision"])
        results.append(
            {
                "artifact_version": protocol["artifact_version"],
                "protocol_version": protocol["protocol_version"],
                "record_type": "repetition_summary",
                "source": "primary",
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
    latencies = [
        float(item["latency_ms"])
        for item in calls
        if item["latency_ms"] is not None
    ]
    total_cost = _sum_cost(calls)
    results.append(
        {
            "artifact_version": protocol["artifact_version"],
            "protocol_version": protocol["protocol_version"],
            "record_type": "source_summary",
            "source": "primary",
            "repetition_decisions": repetition_decisions,
            "call_count": len(calls),
            "ok_count": sum(item["status"] == "ok" for item in calls),
            "semantic_failure_count": sum(
                item["classification"] == "fail" for item in dialogue_scores
            ),
            "inconclusive_dialogue_count": sum(
                item["classification"] == "inconclusive"
                for item in dialogue_scores
            ),
            "latency_median_ms": (
                round(statistics.median(latencies), 3) if latencies else None
            ),
            "latency_p95_ms": _percentile(latencies, 0.95),
            "prompt_tokens": _sum_metric(calls, "prompt_tokens"),
            "completion_tokens": _sum_metric(calls, "completion_tokens"),
            "reasoning_tokens": _sum_metric(calls, "reasoning_tokens"),
            "total_tokens": _sum_metric(calls, "total_tokens"),
            "cost_usd": total_cost,
            "cost_per_call_usd": (
                round(float(total_cost) / len(calls), 8)
                if total_cost is not None and calls
                else None
            ),
            "finish_reason_counts": _closed_reason_counts(
                calls, "finish_reason"
            ),
            "native_finish_reason_counts": _closed_reason_counts(
                calls, "native_finish_reason"
            ),
            "metric_stats": {
                key: _metric_distribution(calls, key)
                for key in (
                    "latency_ms",
                    "prompt_tokens",
                    "completion_tokens",
                    "reasoning_tokens",
                    "total_tokens",
                )
            },
        }
    )
    decision = decide_sonnet_candidate(
        calls,
        dialogue_scores,
        historical_records=load_historical_provider_artifact(repo_root),
    )
    results.append(
        {
            "artifact_version": protocol["artifact_version"],
            "protocol_version": protocol["protocol_version"],
            "record_type": "final_summary",
            **decision,
            "call_count": len(calls),
            "dialogue_score_count": len(dialogue_scores),
            "cost_usd": total_cost,
            "calls_sha256": _sha256_text(_compact_json(list(calls))),
            "historical_artifact_sha256": protocol["historical_control"][
                "artifact_sha256"
            ],
        }
    )
    return results


def run_sonnet_candidate_campaign(
    *,
    repo_root: Path,
    protocol: Mapping[str, Any],
    client: Any,
    progress: Any | None = None,
) -> list[dict[str, Any]]:
    schedule = build_sonnet_candidate_request_schedule(repo_root, protocol)
    corpus, _ = _load_inputs(repo_root)
    cases = {item["id"]: item for item in corpus["dialogues"]}
    records: list[dict[str, Any]] = []
    dialogue_scores: list[dict[str, Any]] = []
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    group: tuple[int, str] | None = None

    def finish_dialogue() -> None:
        if group is None:
            return
        repetition, dialogue_id = group
        score = dialogic_semantics.score_dialogue(
            cases[dialogue_id], observations
        )
        dialogue_scores.append(
            _dialogue_score_record(
                score,
                source="primary",
                repetition=repetition,
                protocol=protocol,
            )
        )

    for plan in schedule:
        next_group = (int(plan["repetition"]), str(plan["dialogue_id"]))
        if group != next_group:
            finish_dialogue()
            group = next_group
            history = []
            observations = []
        turn = cases[plan["dialogue_id"]]["turns"][plan["turn_id"] - 1]
        user_message = {
            "role": "user",
            "content": turn["user"],
            "timestamp": None,
            "meta": {},
        }
        history.append(user_message)
        response = client.chat_completion(
            dict(plan["payload"]),
            caller="stimmung_agent",
            timeout_s=SONNET_CANDIDATE_TIMEOUT_S,
        )
        outcome = _classify_response(
            response,
            SONNET_CANDIDATE_MODEL,
            allowed_observed_models={
                SONNET_CANDIDATE_MODEL,
                SONNET_CANDIDATE_CANONICAL_SLUG,
            },
            allowed_observed_providers={"anthropic"},
        )
        finish_reason = _closed_finish_reason(response.get("finish_reason"))
        native_finish_reason = _closed_finish_reason(
            response.get("native_finish_reason")
        )
        service_tier = str(response.get("service_tier") or "").strip().lower()
        if outcome["status"] == "ok" and (
            finish_reason != "stop"
            or native_finish_reason not in {"stop", "unknown"}
        ):
            outcome = {
                **outcome,
                "status": "transport_error",
                "reason_code": "generation_incomplete",
                "signal": None,
            }
        if outcome["status"] == "ok" and service_tier not in {
            "",
            "default",
            "standard",
        }:
            outcome = {
                **outcome,
                "status": "transport_error",
                "reason_code": "route_mismatch",
                "signal": None,
            }
        attached_signal = (
            outcome["signal"]
            if outcome["status"] == "ok"
            else _build_fail_open_signal()
        )
        user_message["meta"]["affective_turn_signal"] = attached_signal
        aggregate = build_stimmung_input(messages=history)
        record = _sonnet_candidate_call_record(
            plan=plan,
            response=response,
            outcome=outcome,
            aggregate=aggregate,
            protocol=protocol,
        )
        validate_sonnet_candidate_record(record)
        records.append(record)
        if plan["evaluated"]:
            observations.append(
                {
                    "turn_id": plan["turn_id"],
                    "execution_status": outcome["status"],
                    "source": "primary",
                    "signal": outcome["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append(
            {
                "role": "assistant",
                "content": turn["assistant"],
                "timestamp": None,
            }
        )
        observed_cost = _sum_cost(records)
        if observed_cost is not None and observed_cost > float(
            protocol["cost_cap_usd"]
        ):
            raise ValueError("provider_cost_cap_exceeded")
        if callable(progress):
            progress(
                int(plan["sequence"]),
                SONNET_CANDIDATE_EXPECTED_CALLS,
                dict(record),
            )
    finish_dialogue()
    records.extend(
        _sonnet_candidate_summary_records(
            records,
            dialogue_scores,
            corpus,
            repo_root=repo_root,
            protocol=protocol,
        )
    )
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


def validate_model_comparison_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("record_not_object")
    record_type = record.get("record_type")
    keys = {
        "call": _MODEL_COMPARISON_CALL_KEYS,
        "dialogue_score": _DIALOGUE_SCORE_KEYS,
        "repetition_summary": _REPETITION_SUMMARY_KEYS,
        "source_summary": _SOURCE_SUMMARY_KEYS,
        "final_summary": _MODEL_COMPARISON_FINAL_KEYS,
    }.get(record_type)
    if keys is None or set(record) != keys:
        raise ValueError("model_comparison_record_schema_invalid")
    if (
        record.get("artifact_version"),
        record.get("protocol_version"),
    ) != (
        MODEL_COMPARISON_ARTIFACT_VERSION,
        MODEL_COMPARISON_PROTOCOL_VERSION,
    ):
        raise ValueError("model_comparison_record_version_invalid")

    if record_type == "call":
        if (
            record.get("source") != "primary"
            or record.get("requested_model") != MODEL_COMPARISON_MODEL
            or record.get("requested_reasoning_effort") != "medium"
            or record.get("reasoning_excluded") is not True
            or record.get("transport") != "standard"
            or record.get("batch") is not False
            or record.get("provider_fallbacks") is not False
            or record.get("require_parameters") is not True
            or record.get("max_tokens") != MODEL_COMPARISON_MAX_TOKENS
            or record.get("timeout_s") != MODEL_COMPARISON_TIMEOUT_S
            or record.get("sampling_parameters_present") is not False
        ):
            raise ValueError("model_comparison_call_policy_invalid")
        if (
            record.get("status") not in _CALL_STATUSES
            or record.get("reason_code") not in _CALL_REASONS
            or record.get("observed_provider") not in _PROVIDERS
            or record.get("observed_service_tier")
            not in {"", "default", "standard"}
        ):
            raise ValueError("model_comparison_call_status_invalid")
        allowed_models = {
            MODEL_COMPARISON_MODEL,
            str(_model_comparison_configuration()["canonical_slug"]),
            "unknown",
        }
        if record.get("observed_model") not in allowed_models:
            raise ValueError("model_comparison_observed_model_invalid")
        if (
            not isinstance(record.get("sequence"), int)
            or not 1 <= record["sequence"] <= MODEL_COMPARISON_EXPECTED_CALLS
            or record.get("repetition") not in {1, 2}
            or not isinstance(record.get("turn_id"), int)
            or not 1 <= record["turn_id"] <= 6
            or not isinstance(record.get("evaluated"), bool)
        ):
            raise ValueError("model_comparison_call_identity_invalid")
        if (
            not isinstance(record.get("dialogue_id"), str)
            or not 1 <= len(record["dialogue_id"]) <= 64
        ):
            raise ValueError("model_comparison_dialogue_id_invalid")
        if (
            not isinstance(record.get("latency_ms"), (int, float))
            or isinstance(record.get("latency_ms"), bool)
            or not math.isfinite(float(record["latency_ms"]))
            or float(record["latency_ms"]) < 0
        ):
            raise ValueError("model_comparison_latency_invalid")
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            value = record.get(key)
            if value is not None and _int_metric(value) != value:
                raise ValueError("model_comparison_token_metric_invalid")
        cost = record.get("cost_usd")
        if cost is not None and _float_metric(cost) != cost:
            raise ValueError("model_comparison_cost_metric_invalid")
        _validate_signal(record.get("signal"))
        _validate_aggregate(record.get("aggregate"))
        if record["status"] == "ok":
            if (
                record.get("json_valid") is not True
                or record.get("schema_valid") is not True
                or record.get("signal") is None
                or record.get("fail_open") is not False
                or record.get("observed_model") == "unknown"
                or record.get("observed_provider") != "google"
            ):
                raise ValueError("model_comparison_false_semantic_success")
        elif record.get("signal") is not None or record.get("fail_open") is not True:
            raise ValueError("model_comparison_failed_call_signal_present")
        for key in (
            "messages_sha256",
            "corpus_sha256",
            "prompt_sha256",
            "harness_sha256",
            "parameters_sha256",
        ):
            _validate_sha(record.get(key))
        if _COMMIT_RE.fullmatch(str(record.get("freeze_commit") or "")) is None:
            raise ValueError("model_comparison_freeze_commit_invalid")
    elif record_type == "dialogue_score":
        if (
            record.get("source") != "primary"
            or record.get("repetition") not in {1, 2}
            or record.get("classification") not in {"pass", "fail", "inconclusive"}
            or record.get("error_class") not in {"none", "semantic", "schema", "execution"}
            or not isinstance(record.get("families"), list)
            or not set(record["families"]).issubset(dialogic_semantics.REQUIRED_FAMILIES)
            or not isinstance(record.get("evaluated_turns"), int)
            or not 1 <= record["evaluated_turns"] <= 6
        ):
            raise ValueError("model_comparison_dialogue_score_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _DIALOGUE_REASON_CODES for code in record["reason_codes"]
        ):
            raise ValueError("model_comparison_dialogue_reason_invalid")
    elif record_type == "repetition_summary":
        rates = record.get("family_pass_rates")
        if (
            record.get("source") != "primary"
            or record.get("repetition") not in {1, 2}
            or record.get("decision") not in {"pass", "fail", "inconclusive"}
            or record.get("dialogue_count") != EXPECTED_DIALOGUES
            or record.get("provider_results_observed") is not True
            or not isinstance(rates, Mapping)
            or set(rates) != set(dialogic_semantics.MEASURED_FAMILIES)
            or any(
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= float(value) <= 1
                for value in rates.values()
            )
            or not isinstance(record.get("semantic_failures"), int)
            or not 0 <= record["semantic_failures"] <= EXPECTED_DIALOGUES
            or not isinstance(record.get("inconclusive_results"), int)
            or not 0 <= record["inconclusive_results"] <= EXPECTED_DIALOGUES
        ):
            raise ValueError("model_comparison_repetition_summary_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _REPETITION_REASON_CODES for code in record["reason_codes"]
        ):
            raise ValueError("model_comparison_repetition_reason_invalid")
    elif record_type == "source_summary":
        if (
            record.get("source") != "primary"
            or record.get("call_count") != MODEL_COMPARISON_EXPECTED_CALLS
            or not isinstance(record.get("repetition_decisions"), list)
            or len(record["repetition_decisions"]) != REPETITIONS
            or any(
                value not in {"pass", "fail", "inconclusive"}
                for value in record["repetition_decisions"]
            )
            or not isinstance(record.get("ok_count"), int)
            or not 0 <= record["ok_count"] <= MODEL_COMPARISON_EXPECTED_CALLS
            or not isinstance(record.get("semantic_failure_count"), int)
            or not 0 <= record["semantic_failure_count"] <= 32
            or not isinstance(record.get("inconclusive_dialogue_count"), int)
            or not 0 <= record["inconclusive_dialogue_count"] <= 32
        ):
            raise ValueError("model_comparison_source_summary_invalid")
        for key in ("latency_median_ms", "latency_p95_ms", "cost_usd"):
            value = record.get(key)
            if value is not None and _float_metric(value) != value:
                raise ValueError("model_comparison_source_metric_invalid")
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            value = record.get(key)
            if value is not None and _int_metric(value) != value:
                raise ValueError("model_comparison_source_metric_invalid")
    else:
        if (
            record.get("decision") not in _MODEL_COMPARISON_DECISIONS
            or record.get("next_micro_lot") is not None
            or record.get("call_count") != MODEL_COMPARISON_EXPECTED_CALLS
            or record.get("dialogue_score_count") != 32
            or record.get("historical_primary_pass_count") not in range(33)
            or record.get("candidate_pass_count") not in range(33)
            or record.get("semantic_regression_count") not in range(33)
            or record.get("reproducible_semantic_failure_count") not in range(17)
            or record.get("runtime_cutover_authorized") is not False
            or record.get("fallback_evaluated") is not False
        ):
            raise ValueError("model_comparison_final_summary_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _MODEL_COMPARISON_FINAL_REASON_CODES
            for code in record["reason_codes"]
        ):
            raise ValueError("model_comparison_final_reason_invalid")
        cost = record.get("cost_usd")
        if cost is not None and _float_metric(cost) != cost:
            raise ValueError("model_comparison_final_cost_invalid")
        _validate_sha(record.get("calls_sha256"))
        _validate_sha(record.get("historical_artifact_sha256"))
        if record["decision"] == "eligible_primary" and (
            record["candidate_pass_count"] != 32
            or record["semantic_regression_count"] != 0
            or record["cost_usd"] is None
        ):
            raise ValueError("model_comparison_false_eligibility")
    return dict(record)


def validate_token_cap_rerun_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("record_not_object")
    record_type = record.get("record_type")
    expected_keys = {
        "call": _TOKEN_CAP_RERUN_CALL_KEYS,
        "dialogue_score": _DIALOGUE_SCORE_KEYS,
        "repetition_summary": _REPETITION_SUMMARY_KEYS,
        "source_summary": _SOURCE_SUMMARY_KEYS,
        "final_summary": _MODEL_COMPARISON_FINAL_KEYS,
    }.get(record_type)
    if expected_keys is None or set(record) != expected_keys:
        raise ValueError("token_cap_rerun_record_schema_invalid")
    if (
        record.get("artifact_version"),
        record.get("protocol_version"),
    ) != (TOKEN_CAP_RERUN_ARTIFACT_VERSION, TOKEN_CAP_RERUN_PROTOCOL_VERSION):
        raise ValueError("token_cap_rerun_record_version_invalid")
    translated = dict(record)
    translated["artifact_version"] = MODEL_COMPARISON_ARTIFACT_VERSION
    translated["protocol_version"] = MODEL_COMPARISON_PROTOCOL_VERSION
    if record_type == "call":
        if (
            record.get("max_tokens") != TOKEN_CAP_RERUN_MAX_TOKENS
            or record.get("finish_reason") not in TOKEN_CAP_RERUN_FINISH_REASONS
            or record.get("native_finish_reason")
            not in TOKEN_CAP_RERUN_FINISH_REASONS
        ):
            raise ValueError("token_cap_rerun_call_policy_invalid")
        translated["max_tokens"] = MODEL_COMPARISON_MAX_TOKENS
        translated.pop("finish_reason")
        translated.pop("native_finish_reason")
    validate_model_comparison_record(translated)
    return dict(record)


def _validate_metric_stats(value: Any) -> None:
    expected_metrics = {
        "latency_ms",
        "prompt_tokens",
        "completion_tokens",
        "reasoning_tokens",
        "total_tokens",
    }
    if not isinstance(value, Mapping) or set(value) != expected_metrics:
        raise ValueError("sonnet_candidate_metric_stats_invalid")
    for stats in value.values():
        if not isinstance(stats, Mapping) or set(stats) != {
            "min",
            "median",
            "p95",
            "max",
        }:
            raise ValueError("sonnet_candidate_metric_stats_invalid")
        values = [stats[key] for key in ("min", "median", "p95", "max")]
        if any(item is None for item in values):
            if not all(item is None for item in values):
                raise ValueError("sonnet_candidate_metric_stats_invalid")
            continue
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            or float(item) < 0
            for item in values
        ):
            raise ValueError("sonnet_candidate_metric_stats_invalid")
        if not float(values[0]) <= float(values[1]) <= float(values[2]) <= float(
            values[3]
        ):
            raise ValueError("sonnet_candidate_metric_stats_invalid")


def validate_sonnet_candidate_record(record: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(record, Mapping):
        raise ValueError("record_not_object")
    record_type = record.get("record_type")
    expected_keys = {
        "call": _SONNET_CALL_KEYS,
        "dialogue_score": _DIALOGUE_SCORE_KEYS,
        "repetition_summary": _REPETITION_SUMMARY_KEYS,
        "source_summary": _SONNET_SOURCE_SUMMARY_KEYS,
        "final_summary": _SONNET_FINAL_KEYS,
    }.get(record_type)
    if expected_keys is None or set(record) != expected_keys:
        raise ValueError("sonnet_candidate_record_schema_invalid")
    if (
        record.get("artifact_version"),
        record.get("protocol_version"),
    ) != (SONNET_CANDIDATE_ARTIFACT_VERSION, SONNET_CANDIDATE_PROTOCOL_VERSION):
        raise ValueError("sonnet_candidate_record_version_invalid")

    if record_type == "call":
        if (
            record.get("source") != "primary"
            or record.get("requested_model") != SONNET_CANDIDATE_MODEL
            or record.get("requested_provider") != "anthropic"
            or record.get("requested_reasoning_effort")
            != SONNET_CANDIDATE_REASONING_EFFORT
            or record.get("reasoning_excluded") is not True
            or record.get("transport") != "standard"
            or record.get("batch") is not False
            or record.get("provider_fallbacks") is not False
            or record.get("require_parameters") is not True
            or record.get("max_tokens") != SONNET_CANDIDATE_MAX_TOKENS
            or record.get("timeout_s") != SONNET_CANDIDATE_TIMEOUT_S
            or record.get("sampling_parameters_present") is not False
            or record.get("response_format_strict") is not True
            or record.get("structured_output_required") is not True
            or record.get("tools_present") is not False
        ):
            raise ValueError("sonnet_candidate_call_policy_invalid")
        if (
            record.get("status") not in _CALL_STATUSES
            or record.get("reason_code") not in _CALL_REASONS
            or record.get("observed_provider") not in _PROVIDERS
            or record.get("observed_service_tier")
            not in {"", "default", "standard"}
            or record.get("finish_reason") not in SONNET_FINISH_REASONS
            or record.get("native_finish_reason") not in SONNET_FINISH_REASONS
        ):
            raise ValueError("sonnet_candidate_call_status_invalid")
        if record.get("observed_model") not in {
            SONNET_CANDIDATE_MODEL,
            SONNET_CANDIDATE_CANONICAL_SLUG,
            "unknown",
        }:
            raise ValueError("sonnet_candidate_observed_model_invalid")
        if (
            not isinstance(record.get("sequence"), int)
            or not 1 <= record["sequence"] <= SONNET_CANDIDATE_EXPECTED_CALLS
            or record.get("repetition") not in {1, 2}
            or not isinstance(record.get("turn_id"), int)
            or not 1 <= record["turn_id"] <= 6
            or not isinstance(record.get("evaluated"), bool)
            or not isinstance(record.get("dialogue_id"), str)
            or not 1 <= len(record["dialogue_id"]) <= 64
        ):
            raise ValueError("sonnet_candidate_call_identity_invalid")
        if (
            not isinstance(record.get("latency_ms"), (int, float))
            or isinstance(record.get("latency_ms"), bool)
            or not math.isfinite(float(record["latency_ms"]))
            or float(record["latency_ms"]) < 0
        ):
            raise ValueError("sonnet_candidate_latency_invalid")
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            value = record.get(key)
            if value is not None and _int_metric(value) != value:
                raise ValueError("sonnet_candidate_token_metric_invalid")
        cost = record.get("cost_usd")
        if cost is not None and _float_metric(cost) != cost:
            raise ValueError("sonnet_candidate_cost_metric_invalid")
        _validate_signal(record.get("signal"))
        _validate_aggregate(record.get("aggregate"))
        if record["status"] == "ok":
            if (
                record.get("finish_reason") != "stop"
                or record.get("native_finish_reason") not in {"stop", "unknown"}
                or record.get("json_valid") is not True
                or record.get("schema_valid") is not True
                or record.get("signal") is None
                or record.get("fail_open") is not False
                or record.get("observed_model") == "unknown"
                or record.get("observed_provider") != "anthropic"
            ):
                raise ValueError("sonnet_candidate_false_semantic_success")
        elif record.get("signal") is not None or record.get("fail_open") is not True:
            raise ValueError("sonnet_candidate_failed_call_signal_present")
        for key in (
            "messages_sha256",
            "corpus_sha256",
            "prompt_sha256",
            "harness_sha256",
            "parameters_sha256",
            "response_schema_sha256",
        ):
            _validate_sha(record.get(key))
        if _COMMIT_RE.fullmatch(str(record.get("freeze_commit") or "")) is None:
            raise ValueError("sonnet_candidate_freeze_commit_invalid")
    elif record_type in {"dialogue_score", "repetition_summary"}:
        translated = dict(record)
        translated["artifact_version"] = MODEL_COMPARISON_ARTIFACT_VERSION
        translated["protocol_version"] = MODEL_COMPARISON_PROTOCOL_VERSION
        validate_model_comparison_record(translated)
    elif record_type == "source_summary":
        if (
            record.get("source") != "primary"
            or record.get("call_count") != SONNET_CANDIDATE_EXPECTED_CALLS
            or not isinstance(record.get("repetition_decisions"), list)
            or len(record["repetition_decisions"]) != REPETITIONS
            or any(
                value not in {"pass", "fail", "inconclusive"}
                for value in record["repetition_decisions"]
            )
            or not isinstance(record.get("ok_count"), int)
            or not 0 <= record["ok_count"] <= SONNET_CANDIDATE_EXPECTED_CALLS
            or not isinstance(record.get("semantic_failure_count"), int)
            or not 0 <= record["semantic_failure_count"] <= 32
            or not isinstance(record.get("inconclusive_dialogue_count"), int)
            or not 0 <= record["inconclusive_dialogue_count"] <= 32
        ):
            raise ValueError("sonnet_candidate_source_summary_invalid")
        for key in (
            "latency_median_ms",
            "latency_p95_ms",
            "cost_usd",
            "cost_per_call_usd",
        ):
            value = record.get(key)
            if value is not None and _float_metric(value) != value:
                raise ValueError("sonnet_candidate_source_metric_invalid")
        for key in (
            "prompt_tokens",
            "completion_tokens",
            "reasoning_tokens",
            "total_tokens",
        ):
            value = record.get(key)
            if value is not None and _int_metric(value) != value:
                raise ValueError("sonnet_candidate_source_metric_invalid")
        for key in ("finish_reason_counts", "native_finish_reason_counts"):
            counts = record.get(key)
            if (
                not isinstance(counts, Mapping)
                or set(counts) != SONNET_FINISH_REASONS
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, int)
                    or value < 0
                    for value in counts.values()
                )
                or sum(counts.values()) != SONNET_CANDIDATE_EXPECTED_CALLS
            ):
                raise ValueError("sonnet_candidate_finish_counts_invalid")
        _validate_metric_stats(record.get("metric_stats"))
    else:
        if (
            record.get("decision") not in _MODEL_COMPARISON_DECISIONS
            or record.get("next_micro_lot") is not None
            or record.get("call_count") != SONNET_CANDIDATE_EXPECTED_CALLS
            or record.get("dialogue_score_count") != 32
            or record.get("historical_primary_pass_count") not in range(33)
            or record.get("candidate_pass_count") not in range(33)
            or record.get("semantic_regression_count") not in range(33)
            or record.get("reproducible_semantic_failure_count") not in range(17)
            or not isinstance(record.get("runtime_cutover_authorized"), bool)
            or record.get("fallback_evaluated") is not False
            or record.get("valid_call_count") not in range(139)
            or record.get("finish_stop_count") not in range(139)
        ):
            raise ValueError("sonnet_candidate_final_summary_invalid")
        if not isinstance(record.get("reason_codes"), list) or any(
            code not in _MODEL_COMPARISON_FINAL_REASON_CODES
            for code in record["reason_codes"]
        ):
            raise ValueError("sonnet_candidate_final_reason_invalid")
        cost = record.get("cost_usd")
        if cost is not None and _float_metric(cost) != cost:
            raise ValueError("sonnet_candidate_final_cost_invalid")
        _validate_sha(record.get("calls_sha256"))
        _validate_sha(record.get("historical_artifact_sha256"))
        if record["decision"] == "eligible_primary":
            if (
                record["candidate_pass_count"] != 32
                or record["semantic_regression_count"] != 0
                or record["valid_call_count"] != SONNET_CANDIDATE_EXPECTED_CALLS
                or record["finish_stop_count"] != SONNET_CANDIDATE_EXPECTED_CALLS
                or record["runtime_cutover_authorized"] is not True
                or record["cost_usd"] is None
            ):
                raise ValueError("sonnet_candidate_false_eligibility")
        elif record["runtime_cutover_authorized"] is not False:
            raise ValueError("sonnet_candidate_false_cutover_authority")
    return dict(record)


def validate_model_comparison_artifact(
    records: Sequence[Mapping[str, Any]],
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    token_cap_rerun = (
        protocol.get("protocol_version") == TOKEN_CAP_RERUN_PROTOCOL_VERSION
    )
    (
        validate_token_cap_rerun_protocol(protocol, repo_root)
        if token_cap_rerun
        else validate_model_comparison_protocol(protocol, repo_root)
    )
    for record in records:
        (
            validate_token_cap_rerun_record(record)
            if token_cap_rerun
            else validate_model_comparison_record(record)
        )
    calls = [dict(item) for item in records if item.get("record_type") == "call"]
    if (
        len(calls) != MODEL_COMPARISON_EXPECTED_CALLS
        or [item["sequence"] for item in calls]
        != list(range(1, MODEL_COMPARISON_EXPECTED_CALLS + 1))
        or list(records[:MODEL_COMPARISON_EXPECTED_CALLS]) != calls
    ):
        raise ValueError("model_comparison_call_order_invalid")
    schedule = (
        build_token_cap_rerun_request_schedule(repo_root, protocol)
        if token_cap_rerun
        else build_model_comparison_request_schedule(repo_root, protocol)
    )
    corpus, _ = _load_inputs(repo_root)
    cases = {item["id"]: item for item in corpus["dialogues"]}
    histories: dict[tuple[int, str], list[dict[str, Any]]] = {}
    observations: dict[tuple[int, str], list[dict[str, Any]]] = {}
    frozen_call_fields = {
        "corpus_sha256": protocol["corpus_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "harness_sha256": protocol["harness_sha256"],
        "parameters_sha256": protocol["parameters_sha256"],
        "freeze_commit": protocol["freeze_commit"],
    }
    for call, plan in zip(calls, schedule):
        if any(
            call[key] != plan[key]
            for key in (
                "sequence",
                "source",
                "repetition",
                "dialogue_id",
                "turn_id",
                "evaluated",
                "messages_sha256",
            )
        ):
            raise ValueError("model_comparison_call_order_invalid")
        if any(call.get(key) != value for key, value in frozen_call_fields.items()):
            raise ValueError("model_comparison_call_protocol_fingerprint_mismatch")
        group = (int(call["repetition"]), str(call["dialogue_id"]))
        history = histories.setdefault(group, [])
        turn = cases[call["dialogue_id"]]["turns"][call["turn_id"] - 1]
        signal = (
            call["signal"] if call["status"] == "ok" else _build_fail_open_signal()
        )
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
            raise ValueError("model_comparison_aggregate_reconstruction_mismatch")
        if call["evaluated"]:
            observations.setdefault(group, []).append(
                {
                    "turn_id": call["turn_id"],
                    "execution_status": call["status"],
                    "source": "primary",
                    "signal": call["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append(
            {
                "role": "assistant",
                "content": turn["assistant"],
                "timestamp": None,
            }
        )
    scores: list[dict[str, Any]] = []
    for repetition in (1, 2):
        for case in corpus["dialogues"]:
            group = (repetition, case["id"])
            score = dialogic_semantics.score_dialogue(
                case,
                observations.get(group, []),
            )
            scores.append(
                _dialogue_score_record(
                    score,
                    source="primary",
                    repetition=repetition,
                    protocol=protocol,
                )
            )
    expected_tail = _model_comparison_summary_records(
        calls,
        scores,
        corpus,
        repo_root=repo_root,
        protocol=protocol,
    )
    if list(records[MODEL_COMPARISON_EXPECTED_CALLS:]) != expected_tail:
        raise ValueError("model_comparison_artifact_summary_reconstruction_mismatch")
    final = expected_tail[-1]
    return {
        "call_count": len(calls),
        "dialogue_score_count": len(scores),
        "final_decision": final["decision"],
        "cost_usd": final["cost_usd"],
    }


def validate_token_cap_rerun_artifact(
    records: Sequence[Mapping[str, Any]],
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    validate_token_cap_rerun_protocol(protocol, repo_root)
    return validate_model_comparison_artifact(records, repo_root, protocol)


def validate_sonnet_candidate_artifact(
    records: Sequence[Mapping[str, Any]],
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> dict[str, Any]:
    validate_sonnet_candidate_protocol(protocol, repo_root)
    for record in records:
        validate_sonnet_candidate_record(record)
    calls = [dict(item) for item in records if item.get("record_type") == "call"]
    if (
        len(calls) != SONNET_CANDIDATE_EXPECTED_CALLS
        or [item["sequence"] for item in calls]
        != list(range(1, SONNET_CANDIDATE_EXPECTED_CALLS + 1))
        or list(records[:SONNET_CANDIDATE_EXPECTED_CALLS]) != calls
    ):
        raise ValueError("sonnet_candidate_call_order_invalid")
    schedule = build_sonnet_candidate_request_schedule(repo_root, protocol)
    corpus, _ = _load_inputs(repo_root)
    cases = {item["id"]: item for item in corpus["dialogues"]}
    histories: dict[tuple[int, str], list[dict[str, Any]]] = {}
    observations: dict[tuple[int, str], list[dict[str, Any]]] = {}
    frozen_call_fields = {
        "corpus_sha256": protocol["corpus_sha256"],
        "prompt_sha256": protocol["prompt_sha256"],
        "harness_sha256": protocol["harness_sha256"],
        "parameters_sha256": protocol["parameters_sha256"],
        "response_schema_sha256": protocol["response_schema_sha256"],
        "freeze_commit": protocol["freeze_commit"],
    }
    for call, plan in zip(calls, schedule):
        if any(
            call[key] != plan[key]
            for key in (
                "sequence",
                "source",
                "repetition",
                "dialogue_id",
                "turn_id",
                "evaluated",
                "messages_sha256",
            )
        ):
            raise ValueError("sonnet_candidate_call_order_invalid")
        if any(call.get(key) != value for key, value in frozen_call_fields.items()):
            raise ValueError("sonnet_candidate_call_protocol_fingerprint_mismatch")
        group = (int(call["repetition"]), str(call["dialogue_id"]))
        history = histories.setdefault(group, [])
        turn = cases[call["dialogue_id"]]["turns"][call["turn_id"] - 1]
        signal = (
            call["signal"]
            if call["status"] == "ok"
            else _build_fail_open_signal()
        )
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
            raise ValueError("sonnet_candidate_aggregate_reconstruction_mismatch")
        if call["evaluated"]:
            observations.setdefault(group, []).append(
                {
                    "turn_id": call["turn_id"],
                    "execution_status": call["status"],
                    "source": "primary",
                    "signal": call["signal"],
                    "aggregate": aggregate,
                }
            )
        history.append(
            {
                "role": "assistant",
                "content": turn["assistant"],
                "timestamp": None,
            }
        )
    scores: list[dict[str, Any]] = []
    for repetition in (1, 2):
        for case in corpus["dialogues"]:
            group = (repetition, case["id"])
            score = dialogic_semantics.score_dialogue(
                case,
                observations.get(group, []),
            )
            scores.append(
                _dialogue_score_record(
                    score,
                    source="primary",
                    repetition=repetition,
                    protocol=protocol,
                )
            )
    expected_tail = _sonnet_candidate_summary_records(
        calls,
        scores,
        corpus,
        repo_root=repo_root,
        protocol=protocol,
    )
    if list(records[SONNET_CANDIDATE_EXPECTED_CALLS:]) != expected_tail:
        raise ValueError("sonnet_candidate_artifact_summary_reconstruction_mismatch")
    final = expected_tail[-1]
    return {
        "call_count": len(calls),
        "dialogue_score_count": len(scores),
        "final_decision": final["decision"],
        "cost_usd": final["cost_usd"],
    }


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
    parser.add_argument("--model-comparison", action="store_true")
    parser.add_argument("--token-cap-rerun", action="store_true")
    parser.add_argument("--sonnet-candidate", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    selected_modes = sum(
        bool(value)
        for value in (
            args.strengthening,
            args.model_comparison,
            args.token_cap_rerun,
            args.sonnet_candidate,
        )
    )
    if selected_modes > 1:
        raise SystemExit("campaign modes are mutually exclusive")
    if args.sonnet_candidate:
        protocol = build_sonnet_candidate_protocol(
            args.repo_root,
            freeze_commit=args.freeze_commit,
        )
        summary = validate_sonnet_candidate_protocol(protocol, args.repo_root)
    elif args.token_cap_rerun:
        protocol = build_token_cap_rerun_protocol(
            args.repo_root,
            freeze_commit=args.freeze_commit,
        )
        summary = validate_token_cap_rerun_protocol(protocol, args.repo_root)
    elif args.model_comparison:
        protocol = build_model_comparison_protocol(
            args.repo_root,
            freeze_commit=args.freeze_commit,
        )
        summary = validate_model_comparison_protocol(protocol, args.repo_root)
    elif args.strengthening:
        protocol = build_strengthening_protocol(
            args.repo_root,
            freeze_commit=args.freeze_commit,
        )
        summary = validate_protocol(protocol, args.repo_root)
    else:
        protocol = build_protocol(args.repo_root, freeze_commit=args.freeze_commit)
        summary = validate_protocol(protocol, args.repo_root)
    if args.dry_run:
        print(_compact_json({"status": "ready", **summary, "protocol_sha256": _sha256_text(_compact_json(protocol))}))
        return 0
    if args.output is None:
        raise SystemExit("--output is required for a live campaign")
    client = OpenRouterClient.from_env(
        title=(
            "FridaDev/Lot4C2-Stimmung-Sonnet-Candidate"
            if args.sonnet_candidate
            else (
                "FridaDev/Lot4C2-Stimmung-Gemini-Comparison"
                if args.model_comparison or args.token_cap_rerun
                else "FridaDev/Lot4S1"
            )
        )
    )

    def progress(current: int, total: int, _record: Mapping[str, Any]) -> None:
        if current == 1 or current % 20 == 0 or current == total:
            print(_compact_json({"status": "running", "completed": current, "total": total}), flush=True)

    if args.sonnet_candidate:
        records = run_sonnet_candidate_campaign(
            repo_root=args.repo_root,
            protocol=protocol,
            client=client,
            progress=progress,
        )
        validate_sonnet_candidate_artifact(
            records,
            args.repo_root,
            protocol,
        )
    elif args.model_comparison or args.token_cap_rerun:
        records = (
            run_token_cap_rerun_campaign(
                repo_root=args.repo_root,
                protocol=protocol,
                client=client,
                progress=progress,
            )
            if args.token_cap_rerun
            else run_model_comparison_campaign(
                repo_root=args.repo_root,
                protocol=protocol,
                client=client,
                progress=progress,
            )
        )
        (
            validate_token_cap_rerun_artifact(records, args.repo_root, protocol)
            if args.token_cap_rerun
            else validate_model_comparison_artifact(
                records,
                args.repo_root,
                protocol,
            )
        )
    else:
        records = run_campaign(
            repo_root=args.repo_root,
            protocol=protocol,
            client=client,
            progress=progress,
        )
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
