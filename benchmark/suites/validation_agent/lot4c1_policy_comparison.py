"""Frozen current/candidate Validation policy comparison for Lot 4C.1.

Only the bounded decision-policy fragment differs between paired provider
calls. Raw provider output is parsed in memory and never enters the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
from pathlib import Path
import re
import statistics
import sys
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from benchmark.core.openrouter import OpenRouterClient, OpenRouterConfig
from benchmark.suites.validation_agent import lot4c1_comparison as projection
from core.hermeneutic_node.validation import validation_contract


CONTROL_PATH = Path(
    "benchmark/suites/validation_agent/fixtures/lot4c1_validation_policy_control.json"
)
CONTROL_SCHEMA_VERSION = "lot4c1_validation_policy_control_v1"
CORPUS_SCHEMA_VERSION = "lot4c1_validation_policy_corpus_v1"
CORPUS_ID = "lot4c1-validation-policy-v1"
PROTOCOL_VERSION = "lot4c1_validation_policy_comparison_v1"
CURRENT_POLICY_VERSION = "validation_decision_policy_v1"
CANDIDATE_POLICY_VERSION = "validation_decision_policy_v2"
CURRENT_POLICY_FRAGMENT = (
    "- privilegie la lecture la plus coherente du tour, la continuite dialogique locale et la reponse simple\n"
    "- ne choisis clarify qu'apres l'echec d'une interpretation coherente depuis le contexte, ou si des lectures incompatibles entraineraient des actions materiellement differentes\n"
    "- un signal lexical, une ponctuation ou une recommandation amont de clarification ne suffit jamais seul a choisir clarify\n"
)
CANDIDATE_POLICY_FRAGMENT = (
    "- examine d'abord si aucune interpretation coherente n'est possible depuis le contexte, ou si plusieurs lectures incompatibles encore coherentes entraineraient des actions materiellement differentes; dans ces seuls cas, choisis clarify\n"
    "- sinon, privilegie la lecture la plus coherente du tour, la continuite dialogique locale et la reponse simple\n"
    "- un signal lexical, une ponctuation ou une recommandation amont de clarification ne suffit jamais seul a choisir clarify\n"
)
CURRENT_POLICY_SHA256 = "c783ba346a7256699dae22a2b83133b72cfa5926fd630025dd9cb94892eafd2a"
CANDIDATE_POLICY_SHA256 = "68591a18cadf7ce61b7d39f87916c834cb068d26bbc82dbd88793aec9e9d62f9"
POLICY_VERSIONS = {
    "current": CURRENT_POLICY_VERSION,
    "candidate": CANDIDATE_POLICY_VERSION,
}
POLICY_HASHES = {
    "current": CURRENT_POLICY_SHA256,
    "candidate": CANDIDATE_POLICY_SHA256,
}
CASE_COUNT = 11
POLICY_COUNT = 2
REPETITIONS = 2
PLANNED_PROVIDER_CALLS = CASE_COUNT * POLICY_COUNT * len(projection.MODEL_ROLES) * REPETITIONS
ABSOLUTE_PROVIDER_CALL_CAP = 96
MAX_ESTIMATED_COST_USD = 0.10
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_OBSERVED_PROVIDERS = {"", "Google", "Google AI Studio", "OpenAI"}
_PROVIDER_STATUSES = {
    "ok",
    "empty_output",
    "timeout",
    "refusal",
    "transport_error",
    "invalid_json",
    "invalid_schema",
}
_PROVIDER_REASON_CODES = {
    "accepted",
    "pair_not_allowed",
    "hard_guard_violation",
    "false_presence",
    "missed_presence",
    "empty_output",
    "timeout",
    "provider_refusal",
    "transport_error",
    "invalid_json",
    "invalid_schema",
}
_PAIR_STATUSES = {
    "pass",
    "candidate_semantic_regression",
    "candidate_corrects_shared_failure",
    "shared_critical_invariant_failure",
    "accepted_preexisting_fallback_gap",
    "provider_invalid_pair",
}
_DIVERGENCE_CODES = {
    "allowed_semantic_pair_divergence",
    "candidate_semantic_regression",
    "candidate_corrects_shared_failure",
    "shared_critical_invariant_failure",
    "preexisting_fallback_presence_gap",
}
ARTIFACT_RECORD_KEYS = {
    "record_type",
    "protocol_version",
    "corpus_id",
    "corpus_sha256",
    "case_id",
    "policy",
    "policy_version",
    "policy_sha256",
    "freeze_commit",
    "source",
    "model",
    "observed_model",
    "observed_provider",
    "generation",
    "repetition",
    "status",
    "reason_code",
    "final_judgment_posture",
    "final_output_regime",
    "scorer_pass",
    "divergence_codes",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "total_tokens",
    "cost_usd",
    "system_sha256",
    "nonpolicy_user_sha256",
    "canonical_sha256",
}


MODEL_COMPARISON_PROTOCOL_VERSION = "lot4c1_validation_model_comparison_v1"
MODEL_COMPARISON_CORPUS_ID = CORPUS_ID
MODEL_COMPARISON_REPETITIONS = 2
MODEL_COMPARISON_MAX_TOKENS = 500
MODEL_COMPARISON_TIMEOUT_S = 15
MODEL_COMPARISON_ABSOLUTE_CALL_CAP = 96
MODEL_COMPARISON_MAX_ESTIMATED_COST_USD = 0.28
MODEL_METADATA_OBSERVED_AT_UTC = "2026-08-29T12:29:48Z"
HISTORICAL_CONTROL_PATH = Path(
    "benchmark/results/validation_agent/2026-08-29-lot4c1-validation-policy-current-candidate.jsonl"
)
HISTORICAL_CONTROL_ARTIFACT_SHA256 = (
    "97d9d208cb70882df32e714f708e0cde092450dc5156c35e9889ba2205fe10ab"
)
HISTORICAL_CONTROL_FREEZE_COMMIT = "daba97bbd9f6a3fda37a956d0b855bcd0647c415"
HISTORICAL_SCORER_SOURCE_SHA256 = (
    "4b71ed96943129ff54590bc46da3d7d5b94c86ec0f66f278a16cb4a969007b77"
)
HISTORICAL_MESSAGE_BUILDER_SOURCE_SHA256 = (
    "1d0717ab675802ebbd0c99ce780ec0b42a43ee07dd0f8f9b79acc858561dd957"
)
HISTORICAL_CORPUS_BUILDER_SOURCE_SHA256 = (
    "4957b3e952e123ba80846f8745fcd2afa56684dd0c0162389a2cc3df5b67760d"
)
HISTORICAL_POLICY_PAIR_BUILDER_SOURCE_SHA256 = (
    "d7d70764afbf8c60bf2e2c2bb930b0a72c1c51579a72e6e0667d44c4b1bd7871"
)
HISTORICAL_PROMPT_SHA256 = (
    "fd57ef111cb22d34cbacb72787efee7ff1f1040fbe294e9ef6daa144e60fd5e9"
)
HISTORICAL_CORPUS_SHA256 = (
    "bb0416662dd0cd9a42436c7f185c86e44ec877090326a6c0cf4ec4846c1184d4"
)
MODEL_COMPARISON_CONFIGURATIONS = {
    "gemini_3_7_flash_medium": {
        "model": "google/gemini-3.7-flash",
        "canonical_slug": "google/gemini-3.7-flash-20260813",
        "reasoning_effort": "medium",
        "allowed_providers": ("Google", "Google AI Studio"),
        "supported_efforts": ("high", "medium", "low"),
        "context_length": 1_048_576,
        "max_completion_tokens": 65_536,
        "structured_outputs": True,
        "prompt_price_per_token": 0.00000075,
        "completion_price_per_token": 0.00000375,
        "cache_read_price_per_token": 0.000000075,
    },
    "gemini_3_7_flash_high": {
        "model": "google/gemini-3.7-flash",
        "canonical_slug": "google/gemini-3.7-flash-20260813",
        "reasoning_effort": "high",
        "allowed_providers": ("Google", "Google AI Studio"),
        "supported_efforts": ("high", "medium", "low"),
        "context_length": 1_048_576,
        "max_completion_tokens": 65_536,
        "structured_outputs": True,
        "prompt_price_per_token": 0.00000075,
        "completion_price_per_token": 0.00000375,
        "cache_read_price_per_token": 0.000000075,
    },
    "luna_pro_medium": {
        "model": "openai/gpt-5.6-luna-pro",
        "canonical_slug": "openai/gpt-5.6-luna-pro-20260709",
        "reasoning_effort": "medium",
        "allowed_providers": ("Azure", "OpenAI"),
        "supported_efforts": ("max", "xhigh", "high", "medium", "low", "none"),
        "context_length": 1_050_000,
        "max_completion_tokens": 128_000,
        "structured_outputs": True,
        "prompt_price_per_token": 0.0000002,
        "completion_price_per_token": 0.0000012,
        "cache_read_price_per_token": 0.00000002,
    },
    "luna_pro_high": {
        "model": "openai/gpt-5.6-luna-pro",
        "canonical_slug": "openai/gpt-5.6-luna-pro-20260709",
        "reasoning_effort": "high",
        "allowed_providers": ("Azure", "OpenAI"),
        "supported_efforts": ("max", "xhigh", "high", "medium", "low", "none"),
        "context_length": 1_050_000,
        "max_completion_tokens": 128_000,
        "structured_outputs": True,
        "prompt_price_per_token": 0.0000002,
        "completion_price_per_token": 0.0000012,
        "cache_read_price_per_token": 0.00000002,
    },
}
MODEL_COMPARISON_CONFIGURATION_IDS = tuple(MODEL_COMPARISON_CONFIGURATIONS)
MODEL_COMPARISON_PLANNED_CALLS = (
    CASE_COUNT * MODEL_COMPARISON_REPETITIONS * len(MODEL_COMPARISON_CONFIGURATION_IDS)
)
_MODEL_COMPARISON_STATUSES = {
    "ok",
    "empty_output",
    "timeout",
    "refusal",
    "transport_error",
    "invalid_json",
    "invalid_schema",
    "routing_inconclusive",
    "metrics_inconclusive",
}
_MODEL_COMPARISON_REASON_CODES = _PROVIDER_REASON_CODES | {
    "observed_model_mismatch",
    "observed_provider_mismatch",
    "nonstandard_service_tier",
    "latency_budget_exceeded",
    "usage_missing",
    "reasoning_usage_missing",
    "cost_missing",
}
_MODEL_COMPARISON_SEMANTIC_CODES = {
    "pair_not_allowed",
    "hard_guard_violation",
    "false_presence",
    "missed_presence",
}
_MODEL_COMPARISON_SUMMARY_REASONS = {
    "eligible",
    "missing_calls",
    "non_comparable_transport",
    "metrics_missing",
    "provider_result_invalid",
    "semantic_invariant_failure",
    "critical_case_005_failed",
    "presence_case_003_failed",
    "countercase_011_failed",
}
_MODEL_COMPARISON_RECOMMENDATIONS = {
    "human_tradeoff_required",
    "no_eligible_candidate",
    "inconclusive",
    *(f"recommend_{config_id}" for config_id in MODEL_COMPARISON_CONFIGURATION_IDS),
}
_MODEL_CALL_KEYS = {
    "record_type",
    "protocol_version",
    "corpus_id",
    "corpus_sha256",
    "freeze_commit",
    "case_id",
    "configuration_id",
    "requested_model",
    "requested_reasoning_effort",
    "transport",
    "batch",
    "provider_fallbacks",
    "max_tokens",
    "timeout_s",
    "repetition",
    "sequence_index",
    "status",
    "reason_code",
    "observed_model",
    "observed_provider",
    "observed_service_tier",
    "final_judgment_posture",
    "final_output_regime",
    "scorer_pass",
    "semantic_codes",
    "latency_ms",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
    "cost_source",
    "system_sha256",
    "user_sha256",
    "canonical_sha256",
    "messages_sha256",
    "request_sha256",
    "raw_content_included",
}
_MODEL_CONFIGURATION_SUMMARY_KEYS = {
    "record_type",
    "protocol_version",
    "corpus_id",
    "corpus_sha256",
    "freeze_commit",
    "configuration_id",
    "requested_model",
    "requested_reasoning_effort",
    "status",
    "reason_codes",
    "provider_calls",
    "valid_calls",
    "semantic_passes",
    "case_005_passes",
    "case_003_passes",
    "case_011_passes",
    "observed_models",
    "observed_providers",
    "latency_median_ms",
    "latency_p95_ms",
    "latency_max_ms",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
    "transport",
    "batch",
    "raw_content_included",
}
_MODEL_CAMPAIGN_SUMMARY_KEYS = {
    "record_type",
    "protocol_version",
    "corpus_id",
    "corpus_sha256",
    "freeze_commit",
    "recommendation",
    "eligible_configurations",
    "configuration_statuses",
    "provider_calls",
    "valid_calls",
    "prompt_tokens",
    "completion_tokens",
    "reasoning_tokens",
    "total_tokens",
    "cost_usd",
    "historical_control_status",
    "historical_control_model",
    "historical_control_provider_calls",
    "historical_control_semantic_passes",
    "protocol_sha256",
    "records_sha256",
    "runtime_cutover_authorized",
    "raw_content_included",
}


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _validate_frozen_fragments() -> None:
    if _sha256_text(CURRENT_POLICY_FRAGMENT) != CURRENT_POLICY_SHA256:
        raise ValueError("current_policy_fragment_hash_mismatch")
    if _sha256_text(CANDIDATE_POLICY_FRAGMENT) != CANDIDATE_POLICY_SHA256:
        raise ValueError("candidate_policy_fragment_hash_mismatch")


def load_policy_corpus(control_path: Path | None = None) -> dict[str, Any]:
    base = projection.load_corpus()
    resolved = control_path or (REPO_ROOT / CONTROL_PATH)
    control = json.loads(resolved.read_text(encoding="utf-8"))
    if control.get("schema_version") != CONTROL_SCHEMA_VERSION:
        raise ValueError("invalid_lot4c1_policy_control_version")
    case = control.get("case")
    if not isinstance(case, Mapping) or case.get("id") != "L4C1-VAL-011":
        raise ValueError("invalid_lot4c1_policy_control_case")
    expected = case.get("expected") or {}
    if expected.get("allowed_pairs") != [["answer", "simple"]]:
        raise ValueError("invalid_lot4c1_policy_control_expectation")
    if str((case.get("primary") or {}).get("judgment_posture") or "") != "clarify":
        raise ValueError("invalid_lot4c1_policy_control_primary")
    cases = [dict(item) for item in base["cases"]] + [dict(case)]
    if len(cases) != CASE_COUNT or len({item["id"] for item in cases}) != CASE_COUNT:
        raise ValueError("invalid_lot4c1_policy_case_count")
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_id": CORPUS_ID,
        "cases": cases,
    }


def corpus_sha256(corpus: Mapping[str, Any]) -> str:
    return _sha256_text(_compact_json(corpus))


def build_policy_message_pair(
    case: Mapping[str, Any],
    system_prompt: str,
) -> dict[str, list[dict[str, str]]]:
    _validate_frozen_fragments()
    built = projection.build_current_messages(case, system_prompt)
    current = [dict(message) for message in built["messages"]]
    if len(current) != 2 or current[1]["content"].count(CURRENT_POLICY_FRAGMENT) != 1:
        raise ValueError("current_policy_fragment_not_unique")
    candidate = [dict(message) for message in current]
    candidate[1]["content"] = candidate[1]["content"].replace(
        CURRENT_POLICY_FRAGMENT,
        CANDIDATE_POLICY_FRAGMENT,
        1,
    )
    if candidate[1]["content"].count(CANDIDATE_POLICY_FRAGMENT) != 1:
        raise ValueError("candidate_policy_fragment_not_unique")
    return {"current": current, "candidate": candidate}


def policy_pair_fingerprints(
    messages_by_policy: Mapping[str, Sequence[Mapping[str, str]]],
) -> dict[str, str]:
    fingerprints: dict[str, str] = {}
    normalized: dict[str, str] = {}
    canonical: dict[str, str] = {}
    for policy, messages in messages_by_policy.items():
        fragment = CURRENT_POLICY_FRAGMENT if policy == "current" else CANDIDATE_POLICY_FRAGMENT
        system = str(messages[0]["content"])
        user = str(messages[1]["content"])
        if user.count(fragment) != 1:
            raise ValueError("policy_fragment_not_unique")
        material = projection._canonical_material_from_user_message(user)
        fingerprints[f"{policy}_system_sha256"] = _sha256_text(system)
        fingerprints[f"{policy}_policy_sha256"] = _sha256_text(fragment)
        fingerprints[f"{policy}_canonical_sha256"] = _sha256_text(material)
        normalized[policy] = _sha256_text(user.replace(fragment, "<POLICY>", 1))
        canonical[policy] = material
        fingerprints[f"{policy}_nonpolicy_user_sha256"] = normalized[policy]
    if len(set(normalized.values())) != 1 or len(set(canonical.values())) != 1:
        raise ValueError("policy_comparison_changes_nonpolicy_material")
    if (
        fingerprints["current_system_sha256"]
        != fingerprints["candidate_system_sha256"]
    ):
        raise ValueError("policy_comparison_changes_system_prompt")
    return fingerprints


def protocol_document(corpus: Mapping[str, Any], *, freeze_commit: str) -> dict[str, Any]:
    _validate_frozen_fragments()
    if _COMMIT_RE.fullmatch(freeze_commit) is None:
        raise ValueError("invalid_lot4c1_policy_freeze_commit")
    if PLANNED_PROVIDER_CALLS > ABSOLUTE_PROVIDER_CALL_CAP:
        raise ValueError("provider_call_cap_exceeded")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_sha256": corpus_sha256(corpus),
        "freeze_commit": freeze_commit,
        "current_policy_version": CURRENT_POLICY_VERSION,
        "current_policy_sha256": CURRENT_POLICY_SHA256,
        "candidate_policy_version": CANDIDATE_POLICY_VERSION,
        "candidate_policy_sha256": CANDIDATE_POLICY_SHA256,
        "models": [
            {"source": source, "model": model}
            for model, source in projection.MODEL_ROLES.items()
        ],
        "generation": {
            "temperature": projection.TEMPERATURE,
            "top_p": projection.TOP_P,
            "max_tokens": projection.MAX_TOKENS,
            "timeout_s": projection.TIMEOUT_S,
            "reasoning_effort": projection.REASONING_EFFORT,
        },
        "case_count": CASE_COUNT,
        "repetitions": REPETITIONS,
        "policy_count": POLICY_COUNT,
        "policy_order": "alternating_by_repetition",
        "planned_provider_calls": PLANNED_PROVIDER_CALLS,
        "absolute_provider_call_cap": ABSOLUTE_PROVIDER_CALL_CAP,
        "max_estimated_cost_usd": MAX_ESTIMATED_COST_USD,
        "decision_rule": {
            "critical_case_005_primary_all_valid_repetitions_must_pass": True,
            "nonmaterial_countercase_011_must_remain_answer": True,
            "fail_on_any_candidate_regression": True,
            "fail_on_false_or_missed_presence": True,
            "fail_on_hard_guard_violation": True,
            "fallback_preexisting_presence_gap_requires_equivalence": True,
            "all_paired_comparisons_required": True,
            "thresholds_mutable_after_results": False,
        },
    }


def score_structured_pair(
    case: Mapping[str, Any],
    *,
    posture: str,
    regime: str,
) -> dict[str, Any]:
    built = projection.build_current_messages(case, "synthetic-system")
    return projection.score_parsed_output(
        case,
        json.dumps(
            {
                "schema_version": "v1",
                "final_judgment_posture": posture,
                "final_output_regime": regime,
                "arbiter_reason": "synthetic",
            }
        ),
        hard_guard_payload=built["hard_guard"],
    )


def compare_pair(
    *,
    case: Mapping[str, Any],
    source: str,
    current_score: Mapping[str, Any],
    candidate_score: Mapping[str, Any],
) -> dict[str, Any]:
    if current_score.get("status") != "ok" or candidate_score.get("status") != "ok":
        return {"classification": "provider_invalid_pair", "divergence_codes": []}
    current_pair = (
        current_score.get("final_judgment_posture"),
        current_score.get("final_output_regime"),
    )
    candidate_pair = (
        candidate_score.get("final_judgment_posture"),
        candidate_score.get("final_output_regime"),
    )
    codes: list[str] = []
    if current_pair != candidate_pair:
        codes.append("allowed_semantic_pair_divergence")
    if current_score.get("pass") and not candidate_score.get("pass"):
        codes.append("candidate_semantic_regression")
        return {
            "classification": "candidate_semantic_regression",
            "divergence_codes": codes,
        }
    if not current_score.get("pass") and candidate_score.get("pass"):
        codes.append("candidate_corrects_shared_failure")
        return {
            "classification": "candidate_corrects_shared_failure",
            "divergence_codes": codes,
        }
    if candidate_score.get("pass"):
        return {"classification": "pass", "divergence_codes": codes}
    accepted_gap = str((case.get("expected") or {}).get("fallback_preexisting_gap") or "")
    same_codes = list(current_score.get("semantic_codes") or []) == list(
        candidate_score.get("semantic_codes") or []
    )
    if (
        source == "fallback"
        and accepted_gap
        and same_codes
        and accepted_gap in candidate_score.get("semantic_codes", [])
    ):
        return {
            "classification": "accepted_preexisting_fallback_gap",
            "divergence_codes": ["preexisting_fallback_presence_gap"],
        }
    return {
        "classification": "shared_critical_invariant_failure",
        "divergence_codes": ["shared_critical_invariant_failure"],
    }


def synthetic_passing_pair_records() -> list[dict[str, Any]]:
    return [
        {
            "record_type": "pair_comparison",
            "case_id": case["id"],
            "source": source,
            "repetition": repetition,
            "status": "pass",
        }
        for case in load_policy_corpus()["cases"]
        for source in ("primary", "fallback")
        for repetition in range(1, REPETITIONS + 1)
    ]


def campaign_decision(records: Sequence[Mapping[str, Any]]) -> dict[str, str]:
    pairs = [record for record in records if record.get("record_type") == "pair_comparison"]
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in pairs:
        groups.setdefault((str(record.get("case_id")), str(record.get("source"))), []).append(
            record
        )
    if len(groups) != CASE_COUNT * len(projection.MODEL_ROLES):
        return {"decision": "inconclusive", "reason_code": "missing_case_model_group"}
    if any(len(group) != REPETITIONS for group in groups.values()):
        return {"decision": "inconclusive", "reason_code": "missing_paired_repetition"}
    statuses = [str(record.get("status") or "") for record in pairs]
    if "candidate_semantic_regression" in statuses:
        return {"decision": "fail", "reason_code": "candidate_semantic_regression"}
    if "shared_critical_invariant_failure" in statuses:
        return {"decision": "fail", "reason_code": "shared_critical_invariant_failure"}
    if "provider_invalid_pair" in statuses:
        return {"decision": "inconclusive", "reason_code": "provider_invalid_pair"}
    allowed = {"pass", "candidate_corrects_shared_failure", "accepted_preexisting_fallback_gap"}
    if any(status not in allowed for status in statuses):
        return {"decision": "inconclusive", "reason_code": "unknown_pair_status"}
    return {"decision": "pass", "reason_code": "candidate_satisfies_frozen_invariants"}


def _is_finite_number(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _validate_hash(value: Any, *, allow_empty: bool = False) -> None:
    if allow_empty and value == "":
        return
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ValueError("invalid_lot4c1_policy_artifact_hash")


def _expected_generation() -> dict[str, Any]:
    return {
        "temperature": projection.TEMPERATURE,
        "top_p": projection.TOP_P,
        "max_tokens": projection.MAX_TOKENS,
        "timeout_s": projection.TIMEOUT_S,
        "reasoning_effort": projection.REASONING_EFFORT,
    }


def validate_content_free_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    if set(payload) != ARTIFACT_RECORD_KEYS:
        raise ValueError("invalid_lot4c1_policy_artifact_fields")
    record_type = payload.get("record_type")
    if record_type not in {"provider_call", "pair_comparison", "campaign_summary"}:
        raise ValueError("invalid_lot4c1_policy_artifact_record_type")
    if payload.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("invalid_lot4c1_policy_artifact_protocol")
    if payload.get("corpus_id") != CORPUS_ID:
        raise ValueError("invalid_lot4c1_policy_artifact_corpus")
    _validate_hash(payload.get("corpus_sha256"))
    if not isinstance(payload.get("freeze_commit"), str) or _COMMIT_RE.fullmatch(
        payload["freeze_commit"]
    ) is None:
        raise ValueError("invalid_lot4c1_policy_artifact_commit")
    if payload.get("generation") != _expected_generation():
        raise ValueError("invalid_lot4c1_policy_artifact_generation")
    if not isinstance(payload.get("scorer_pass"), bool):
        raise ValueError("invalid_lot4c1_policy_artifact_scorer")
    divergences = payload.get("divergence_codes")
    if (
        not isinstance(divergences, list)
        or len(divergences) != len(set(divergences))
        or any(code not in _DIVERGENCE_CODES for code in divergences)
    ):
        raise ValueError("invalid_lot4c1_policy_artifact_divergence")
    posture = payload.get("final_judgment_posture")
    regime = payload.get("final_output_regime")
    if posture is not None and posture not in validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES:
        raise ValueError("invalid_lot4c1_policy_artifact_posture")
    if regime is not None and regime not in validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES:
        raise ValueError("invalid_lot4c1_policy_artifact_regime")
    source = payload.get("source")
    model = payload.get("model")
    observed_model = payload.get("observed_model")
    observed_provider = payload.get("observed_provider")
    if observed_provider not in _OBSERVED_PROVIDERS:
        raise ValueError("invalid_lot4c1_policy_artifact_observed_provider")
    latency = payload.get("latency_ms")
    if latency is not None and (
        not _is_finite_number(latency)
        or not 0 <= float(latency) <= projection.TIMEOUT_S * 1000
    ):
        raise ValueError("invalid_lot4c1_policy_artifact_latency")
    for key, limit in (
        ("prompt_tokens", PLANNED_PROVIDER_CALLS * 10_000),
        ("completion_tokens", PLANNED_PROVIDER_CALLS * projection.MAX_TOKENS),
        ("total_tokens", PLANNED_PROVIDER_CALLS * (10_000 + projection.MAX_TOKENS)),
    ):
        value = payload.get(key)
        if value is not None and (
            isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= limit
        ):
            raise ValueError(f"invalid_lot4c1_policy_artifact_{key}")
    cost = payload.get("cost_usd")
    if cost is not None and (
        not _is_finite_number(cost) or not 0 <= float(cost) <= MAX_ESTIMATED_COST_USD
    ):
        raise ValueError("invalid_lot4c1_policy_artifact_cost")

    valid_case_ids = {f"L4C1-VAL-{index:03d}" for index in range(1, CASE_COUNT + 1)}
    if record_type in {"provider_call", "pair_comparison"}:
        if payload.get("case_id") not in valid_case_ids:
            raise ValueError("invalid_lot4c1_policy_artifact_case")
        if source not in {"primary", "fallback"} or projection.MODEL_ROLES.get(model) != source:
            raise ValueError("invalid_lot4c1_policy_artifact_model")
        repetition = payload.get("repetition")
        if (
            isinstance(repetition, bool)
            or not isinstance(repetition, int)
            or not 1 <= repetition <= REPETITIONS
        ):
            raise ValueError("invalid_lot4c1_policy_artifact_repetition")

    if record_type == "provider_call":
        policy = payload.get("policy")
        if policy not in POLICY_VERSIONS:
            raise ValueError("invalid_lot4c1_policy_artifact_policy")
        if payload.get("policy_version") != POLICY_VERSIONS[policy]:
            raise ValueError("invalid_lot4c1_policy_artifact_policy_version")
        if payload.get("policy_sha256") != POLICY_HASHES[policy]:
            raise ValueError("invalid_lot4c1_policy_artifact_policy_hash")
        if observed_model not in {"", model}:
            raise ValueError("invalid_lot4c1_policy_artifact_observed_model")
        if source == "primary" and observed_provider not in {"", "Google", "Google AI Studio"}:
            raise ValueError("invalid_lot4c1_policy_artifact_observed_provider")
        if source == "fallback" and observed_provider not in {"", "OpenAI"}:
            raise ValueError("invalid_lot4c1_policy_artifact_observed_provider")
        if payload.get("status") not in _PROVIDER_STATUSES:
            raise ValueError("invalid_lot4c1_policy_artifact_status")
        if payload.get("reason_code") not in _PROVIDER_REASON_CODES:
            raise ValueError("invalid_lot4c1_policy_artifact_reason_code")
        if payload.get("status") == "ok" and (posture is None or regime is None):
            raise ValueError("invalid_lot4c1_policy_artifact_verdict")
        for key in ("system_sha256", "nonpolicy_user_sha256", "canonical_sha256"):
            _validate_hash(payload.get(key))
    elif record_type == "pair_comparison":
        if (
            payload.get("policy") != "current_vs_candidate"
            or payload.get("policy_version") != ""
            or payload.get("policy_sha256") != ""
            or observed_model != ""
            or observed_provider != ""
        ):
            raise ValueError("invalid_lot4c1_policy_artifact_pair")
        status = payload.get("status")
        if status not in _PAIR_STATUSES or payload.get("reason_code") != status:
            raise ValueError("invalid_lot4c1_policy_artifact_reason_code")
        if payload.get("scorer_pass") is not (
            status in {"pass", "candidate_corrects_shared_failure"}
        ):
            raise ValueError("invalid_lot4c1_policy_artifact_scorer")
        if posture is not None or regime is not None:
            raise ValueError("invalid_lot4c1_policy_artifact_verdict")
        if any(
            payload.get(key) is not None
            for key in (
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "total_tokens",
                "cost_usd",
            )
        ):
            raise ValueError("invalid_lot4c1_policy_artifact_pair_metrics")
        _validate_hash(payload.get("system_sha256"))
        _validate_hash(payload.get("nonpolicy_user_sha256"))
        _validate_hash(payload.get("canonical_sha256"))
    else:
        if (
            payload.get("case_id") != "campaign"
            or payload.get("policy") != "current_vs_candidate"
            or payload.get("policy_version") != ""
            or payload.get("policy_sha256") != ""
            or source != "combined"
            or model != "primary_and_fallback"
            or observed_model != ""
            or observed_provider != ""
            or payload.get("repetition") != 0
            or posture is not None
            or regime is not None
            or latency is not None
        ):
            raise ValueError("invalid_lot4c1_policy_artifact_summary")
        summary_reasons = {
            "pass": {"candidate_satisfies_frozen_invariants"},
            "fail": {"candidate_semantic_regression", "shared_critical_invariant_failure"},
            "inconclusive": {
                "missing_case_model_group",
                "missing_paired_repetition",
                "provider_invalid_pair",
                "unknown_pair_status",
            },
        }
        status = payload.get("status")
        if status not in summary_reasons or payload.get("reason_code") not in summary_reasons[status]:
            raise ValueError("invalid_lot4c1_policy_artifact_reason_code")
        if payload.get("scorer_pass") is not (status == "pass"):
            raise ValueError("invalid_lot4c1_policy_artifact_scorer")
        for key in ("system_sha256", "nonpolicy_user_sha256", "canonical_sha256"):
            _validate_hash(payload.get(key), allow_empty=True)
    return payload


def synthetic_valid_provider_record() -> dict[str, Any]:
    return {
        "record_type": "provider_call",
        "protocol_version": PROTOCOL_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_sha256": "a" * 64,
        "case_id": "L4C1-VAL-001",
        "policy": "current",
        "policy_version": CURRENT_POLICY_VERSION,
        "policy_sha256": CURRENT_POLICY_SHA256,
        "freeze_commit": "f" * 40,
        "source": "primary",
        "model": projection.PRIMARY_MODEL,
        "observed_model": projection.PRIMARY_MODEL,
        "observed_provider": "Google",
        "generation": _expected_generation(),
        "repetition": 1,
        "status": "ok",
        "reason_code": "accepted",
        "final_judgment_posture": "answer",
        "final_output_regime": "simple",
        "scorer_pass": True,
        "divergence_codes": [],
        "latency_ms": 1.0,
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "total_tokens": 2,
        "cost_usd": 0.0,
        "system_sha256": "b" * 64,
        "nonpolicy_user_sha256": "c" * 64,
        "canonical_sha256": "d" * 64,
    }


def _source_sha256(callable_object: Any) -> str:
    return _sha256_text(inspect.getsource(callable_object))


def historical_primary_witness() -> dict[str, Any]:
    artifact_path = REPO_ROOT / HISTORICAL_CONTROL_PATH
    artifact_sha256 = hashlib.sha256(artifact_path.read_bytes()).hexdigest()
    if artifact_sha256 != HISTORICAL_CONTROL_ARTIFACT_SHA256:
        raise ValueError("historical_control_artifact_hash_mismatch")
    records = [
        validate_content_free_record(json.loads(line))
        for line in artifact_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    corpus = load_policy_corpus()
    prompt = (REPO_ROOT / "app/prompts/validation_agent.txt").read_text(
        encoding="utf-8"
    ).strip()
    scorer_source_matches = (
        _source_sha256(projection.score_parsed_output)
        == HISTORICAL_SCORER_SOURCE_SHA256
    )
    builder_sources_match = all(
        (
            _source_sha256(projection.build_current_messages)
            == HISTORICAL_MESSAGE_BUILDER_SOURCE_SHA256,
            _source_sha256(load_policy_corpus)
            == HISTORICAL_CORPUS_BUILDER_SOURCE_SHA256,
            _source_sha256(build_policy_message_pair)
            == HISTORICAL_POLICY_PAIR_BUILDER_SOURCE_SHA256,
        )
    )
    if corpus_sha256(corpus) != HISTORICAL_CORPUS_SHA256:
        raise ValueError("historical_control_corpus_hash_mismatch")
    if _sha256_text(prompt) != HISTORICAL_PROMPT_SHA256:
        raise ValueError("historical_control_prompt_hash_mismatch")
    calls = [
        record
        for record in records
        if record["record_type"] == "provider_call"
        and record["source"] == "primary"
        and record["policy"] == "current"
    ]
    by_case_repetition = {
        (record["case_id"], record["repetition"]): record for record in calls
    }
    message_matches: list[bool] = []
    for case in corpus["cases"]:
        pair = build_policy_message_pair(case, prompt)
        fingerprints = policy_pair_fingerprints(pair)
        for repetition in range(1, MODEL_COMPARISON_REPETITIONS + 1):
            record = by_case_repetition.get((case["id"], repetition))
            if record is None:
                message_matches.append(False)
                continue
            message_matches.append(
                all(
                    (
                        record["system_sha256"]
                        == fingerprints["current_system_sha256"],
                        record["nonpolicy_user_sha256"]
                        == fingerprints["current_nonpolicy_user_sha256"],
                        record["canonical_sha256"]
                        == fingerprints["current_canonical_sha256"],
                    )
                )
            )
    failed_case_ids = sorted(
        {
            str(record["case_id"])
            for record in calls
            if not bool(record["scorer_pass"])
        }
    )
    comparable = all(
        (
            len(calls) == 22,
            len(by_case_repetition) == 22,
            all(message_matches),
            scorer_source_matches,
            builder_sources_match,
            all(record["freeze_commit"] == HISTORICAL_CONTROL_FREEZE_COMMIT for record in calls),
            sum(bool(record["scorer_pass"]) for record in calls) == 20,
            failed_case_ids == ["L4C1-VAL-005"],
        )
    )
    if not comparable:
        raise ValueError("historical_primary_witness_not_comparable")
    return {
        "status": "comparable",
        "model": projection.PRIMARY_MODEL,
        "provider_calls": len(calls),
        "semantic_passes": sum(bool(record["scorer_pass"]) for record in calls),
        "failed_case_ids": failed_case_ids,
        "artifact_sha256": artifact_sha256,
        "freeze_commit": HISTORICAL_CONTROL_FREEZE_COMMIT,
        "corpus_sha256": HISTORICAL_CORPUS_SHA256,
        "prompt_sha256": HISTORICAL_PROMPT_SHA256,
        "scorer_sha256": HISTORICAL_SCORER_SOURCE_SHA256,
        "all_message_fingerprints_match": all(message_matches),
        "scorer_source_matches": scorer_source_matches,
        "builder_sources_match": builder_sources_match,
    }


def _model_metadata_document() -> dict[str, Any]:
    return {
        config_id: {
            key: list(value) if isinstance(value, tuple) else value
            for key, value in configuration.items()
        }
        for config_id, configuration in MODEL_COMPARISON_CONFIGURATIONS.items()
    }


def model_comparison_protocol_document(
    corpus: Mapping[str, Any],
    *,
    freeze_commit: str,
) -> dict[str, Any]:
    if _COMMIT_RE.fullmatch(freeze_commit) is None:
        raise ValueError("invalid_lot4c1_model_comparison_freeze_commit")
    if MODEL_COMPARISON_PLANNED_CALLS > MODEL_COMPARISON_ABSOLUTE_CALL_CAP:
        raise ValueError("provider_call_cap_exceeded")
    witness = historical_primary_witness()
    metadata = _model_metadata_document()
    configurations = [
        {
            "configuration_id": config_id,
            "model": configuration["model"],
            "reasoning_effort": configuration["reasoning_effort"],
            "transport": "standard",
            "batch": False,
            "sampling_parameters": "omitted",
            "reasoning_text_retained": False,
        }
        for config_id, configuration in MODEL_COMPARISON_CONFIGURATIONS.items()
    ]
    return {
        "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
        "corpus_id": MODEL_COMPARISON_CORPUS_ID,
        "corpus_sha256": corpus_sha256(corpus),
        "freeze_commit": freeze_commit,
        "metadata_observed_at_utc": MODEL_METADATA_OBSERVED_AT_UTC,
        "metadata_sha256": _sha256_text(_compact_json(metadata)),
        "model_metadata": metadata,
        "configurations": configurations,
        "configuration_order": "rotated_by_case_and_repetition",
        "case_count": CASE_COUNT,
        "repetitions": MODEL_COMPARISON_REPETITIONS,
        "planned_provider_calls": MODEL_COMPARISON_PLANNED_CALLS,
        "absolute_provider_call_cap": MODEL_COMPARISON_ABSOLUTE_CALL_CAP,
        "max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "sampling_parameters": "omitted",
        "response_format_added": False,
        "provider_fallbacks": False,
        "batch": False,
        "flex": False,
        "priority": False,
        "historical_control": witness,
        "projection_version": projection.CURRENT_PROJECTION_VERSION,
        "prompt_sha256": HISTORICAL_PROMPT_SHA256,
        "scorer_sha256": HISTORICAL_SCORER_SOURCE_SHA256,
        "cost_bound": {
            "historical_max_prompt_tokens": 2637,
            "tokenization_margin_percent": 10,
            "bounded_prompt_tokens_per_call": 2901,
            "bounded_completion_tokens_per_call": MODEL_COMPARISON_MAX_TOKENS,
            "price_basis": "openrouter_models_metadata_2026_08_29",
            "raw_estimate_usd": 0.2301618,
            "safety_margin_percent": 20,
        },
        "max_estimated_cost_usd": MODEL_COMPARISON_MAX_ESTIMATED_COST_USD,
        "decision_rule": {
            "semantic_results_required_per_configuration": 22,
            "case_005_both_repetitions_must_clarify": True,
            "case_003_both_repetitions_must_be_presence": True,
            "case_011_both_repetitions_must_answer_simple": True,
            "fail_on_any_semantic_invariant": True,
            "inconclusive_on_routing_or_metrics_gap": True,
            "prefer_lower_effort_at_equal_quality": True,
            "no_automatic_runtime_cutover": True,
            "thresholds_mutable_after_results": False,
        },
    }


def model_comparison_configuration_order(
    case_index: int,
    repetition: int,
) -> list[str]:
    if not 0 <= case_index < CASE_COUNT or not 1 <= repetition <= MODEL_COMPARISON_REPETITIONS:
        raise ValueError("invalid_model_comparison_order_coordinates")
    offset = (case_index + repetition - 1) % len(MODEL_COMPARISON_CONFIGURATION_IDS)
    ordered = list(MODEL_COMPARISON_CONFIGURATION_IDS)
    return ordered[offset:] + ordered[:offset]


def build_model_comparison_payload(
    messages: Sequence[Mapping[str, str]],
    configuration_id: str,
) -> dict[str, Any]:
    configuration = MODEL_COMPARISON_CONFIGURATIONS.get(configuration_id)
    if configuration is None:
        raise ValueError("unknown_model_comparison_configuration")
    if configuration["reasoning_effort"] not in configuration["supported_efforts"]:
        raise ValueError("unsupported_model_comparison_effort")
    payload = {
        "model": configuration["model"],
        "messages": [dict(message) for message in messages],
        "max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "reasoning": {
            "effort": configuration["reasoning_effort"],
            "exclude": True,
        },
        "provider": {
            "allow_fallbacks": False,
            "require_parameters": True,
        },
    }
    return validate_model_comparison_payload(payload, configuration_id)


def validate_model_comparison_payload(
    payload: Mapping[str, Any],
    configuration_id: str,
) -> dict[str, Any]:
    configuration = MODEL_COMPARISON_CONFIGURATIONS.get(configuration_id)
    if configuration is None:
        raise ValueError("invalid_model_comparison_payload_configuration")
    expected_keys = {"model", "messages", "max_tokens", "reasoning", "provider"}
    normalized = dict(payload)
    if set(normalized) != expected_keys:
        raise ValueError("invalid_model_comparison_payload_fields")
    if normalized.get("model") != configuration["model"] or ":batch" in str(
        normalized.get("model")
    ):
        raise ValueError("invalid_model_comparison_payload_model")
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
        raise ValueError("invalid_model_comparison_payload_messages")
    if normalized.get("max_tokens") != MODEL_COMPARISON_MAX_TOKENS:
        raise ValueError("invalid_model_comparison_payload_max_tokens")
    if normalized.get("reasoning") != {
        "effort": configuration["reasoning_effort"],
        "exclude": True,
    }:
        raise ValueError("invalid_model_comparison_payload_reasoning")
    if normalized.get("provider") != {
        "allow_fallbacks": False,
        "require_parameters": True,
    }:
        raise ValueError("invalid_model_comparison_payload_provider")
    return normalized


def model_comparison_messages_sha256(payload: Mapping[str, Any]) -> str:
    return _sha256_text(_compact_json(payload.get("messages")))


def _reasoning_tokens_or_none(usage: Mapping[str, Any]) -> int | None:
    details = usage.get("completion_tokens_details")
    if isinstance(details, Mapping) and "reasoning_tokens" in details:
        value = details.get("reasoning_tokens")
    elif "reasoning_tokens" in usage:
        value = usage.get("reasoning_tokens")
    else:
        return None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def _validate_exact_int(value: Any, *, minimum: int, maximum: int, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ValueError(code)
    return value


def _validate_optional_metric(value: Any, *, maximum: float, code: str) -> None:
    if value is not None and (
        not _is_finite_number(value) or not 0 <= float(value) <= maximum
    ):
        raise ValueError(code)


def validate_model_comparison_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    record_type = payload.get("record_type")
    expected_keys = {
        "provider_call": _MODEL_CALL_KEYS,
        "configuration_summary": _MODEL_CONFIGURATION_SUMMARY_KEYS,
        "campaign_summary": _MODEL_CAMPAIGN_SUMMARY_KEYS,
    }.get(str(record_type))
    if expected_keys is None or set(payload) != expected_keys:
        raise ValueError("invalid_model_comparison_artifact_fields")
    if payload.get("protocol_version") != MODEL_COMPARISON_PROTOCOL_VERSION:
        raise ValueError("invalid_model_comparison_artifact_protocol")
    if payload.get("corpus_id") != MODEL_COMPARISON_CORPUS_ID:
        raise ValueError("invalid_model_comparison_artifact_corpus")
    _validate_hash(payload.get("corpus_sha256"))
    if not isinstance(payload.get("freeze_commit"), str) or _COMMIT_RE.fullmatch(
        payload["freeze_commit"]
    ) is None:
        raise ValueError("invalid_model_comparison_artifact_commit")
    if payload.get("raw_content_included") is not False:
        raise ValueError("invalid_model_comparison_artifact_raw_content")

    if record_type == "provider_call":
        config_id = payload.get("configuration_id")
        configuration = MODEL_COMPARISON_CONFIGURATIONS.get(str(config_id))
        if configuration is None:
            raise ValueError("invalid_model_comparison_artifact_configuration")
        if (
            payload.get("requested_model") != configuration["model"]
            or payload.get("requested_reasoning_effort")
            != configuration["reasoning_effort"]
            or payload.get("transport") != "standard"
            or payload.get("batch") is not False
            or payload.get("provider_fallbacks") is not False
            or payload.get("max_tokens") != MODEL_COMPARISON_MAX_TOKENS
            or payload.get("timeout_s") != MODEL_COMPARISON_TIMEOUT_S
        ):
            raise ValueError("invalid_model_comparison_artifact_request")
        valid_case_ids = {f"L4C1-VAL-{index:03d}" for index in range(1, CASE_COUNT + 1)}
        if payload.get("case_id") not in valid_case_ids:
            raise ValueError("invalid_model_comparison_artifact_case")
        _validate_exact_int(
            payload.get("repetition"),
            minimum=1,
            maximum=MODEL_COMPARISON_REPETITIONS,
            code="invalid_model_comparison_artifact_repetition",
        )
        _validate_exact_int(
            payload.get("sequence_index"),
            minimum=1,
            maximum=MODEL_COMPARISON_PLANNED_CALLS,
            code="invalid_model_comparison_artifact_sequence",
        )
        if payload.get("status") not in _MODEL_COMPARISON_STATUSES:
            raise ValueError("invalid_model_comparison_artifact_status")
        if payload.get("reason_code") not in _MODEL_COMPARISON_REASON_CODES:
            raise ValueError("invalid_model_comparison_artifact_reason")
        fixed_failure_reasons = {
            "empty_output": "empty_output",
            "timeout": "timeout",
            "refusal": "provider_refusal",
            "transport_error": "transport_error",
            "invalid_json": "invalid_json",
            "invalid_schema": "invalid_schema",
        }
        if payload.get("status") in fixed_failure_reasons and (
            payload.get("reason_code") != fixed_failure_reasons[payload["status"]]
            or payload.get("semantic_codes") != []
            or payload.get("scorer_pass") is not False
        ):
            raise ValueError("invalid_model_comparison_artifact_failure_classification")
        if payload.get("observed_model") not in {
            "",
            configuration["model"],
            configuration["canonical_slug"],
        }:
            raise ValueError("invalid_model_comparison_artifact_observed_model")
        if payload.get("observed_provider") not in {
            "",
            *configuration["allowed_providers"],
        }:
            raise ValueError("invalid_model_comparison_artifact_observed_provider")
        if payload.get("observed_service_tier") not in {"", "default", "standard"}:
            raise ValueError("invalid_model_comparison_artifact_service_tier")
        posture = payload.get("final_judgment_posture")
        regime = payload.get("final_output_regime")
        if posture is not None and posture not in validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES:
            raise ValueError("invalid_model_comparison_artifact_posture")
        if regime is not None and regime not in validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES:
            raise ValueError("invalid_model_comparison_artifact_regime")
        if not isinstance(payload.get("scorer_pass"), bool):
            raise ValueError("invalid_model_comparison_artifact_scorer")
        semantic_codes = payload.get("semantic_codes")
        if (
            not isinstance(semantic_codes, list)
            or len(semantic_codes) != len(set(semantic_codes))
            or any(code not in _MODEL_COMPARISON_SEMANTIC_CODES for code in semantic_codes)
        ):
            raise ValueError("invalid_model_comparison_artifact_semantic_codes")
        for key in (
            "system_sha256",
            "user_sha256",
            "canonical_sha256",
            "messages_sha256",
            "request_sha256",
        ):
            _validate_hash(payload.get(key))
        for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
            value = payload.get(key)
            if value is not None:
                _validate_exact_int(
                    value,
                    minimum=0,
                    maximum=100_000,
                    code=f"invalid_model_comparison_artifact_{key}",
                )
        _validate_optional_metric(
            payload.get("latency_ms"),
            maximum=MODEL_COMPARISON_TIMEOUT_S * 1000,
            code="invalid_model_comparison_artifact_latency",
        )
        _validate_optional_metric(
            payload.get("cost_usd"),
            maximum=MODEL_COMPARISON_MAX_ESTIMATED_COST_USD,
            code="invalid_model_comparison_artifact_cost",
        )
        if payload.get("cost_source") not in {
            "provider_usage_cost",
            "openrouter_models_pricing",
            "",
        }:
            raise ValueError("invalid_model_comparison_artifact_cost_source")
        if payload.get("status") == "ok":
            if posture is None or regime is None:
                raise ValueError("invalid_model_comparison_artifact_verdict")
            for key in (
                "latency_ms",
                "prompt_tokens",
                "completion_tokens",
                "reasoning_tokens",
                "total_tokens",
                "cost_usd",
            ):
                if payload.get(key) is None:
                    raise ValueError(f"invalid_model_comparison_artifact_missing_{key}")
            if float(payload["cost_usd"]) <= 0:
                raise ValueError("invalid_model_comparison_artifact_zero_cost")
            if payload.get("observed_model") == "" or payload.get("observed_provider") == "":
                raise ValueError("invalid_model_comparison_artifact_missing_route")
            if bool(payload["scorer_pass"]) is not (not semantic_codes):
                raise ValueError("invalid_model_comparison_artifact_scorer")
    elif record_type == "configuration_summary":
        config_id = payload.get("configuration_id")
        configuration = MODEL_COMPARISON_CONFIGURATIONS.get(str(config_id))
        if configuration is None:
            raise ValueError("invalid_model_comparison_summary_configuration")
        if (
            payload.get("requested_model") != configuration["model"]
            or payload.get("requested_reasoning_effort") != configuration["reasoning_effort"]
            or payload.get("transport") != "standard"
            or payload.get("batch") is not False
        ):
            raise ValueError("invalid_model_comparison_summary_request")
        if payload.get("status") not in {"eligible", "non_eligible", "inconclusive"}:
            raise ValueError("invalid_model_comparison_summary_status")
        reasons = payload.get("reason_codes")
        if (
            not isinstance(reasons, list)
            or len(reasons) != len(set(reasons))
            or any(reason not in _MODEL_COMPARISON_SUMMARY_REASONS for reason in reasons)
        ):
            raise ValueError("invalid_model_comparison_summary_reasons")
        for key in (
            "provider_calls",
            "valid_calls",
            "semantic_passes",
            "case_005_passes",
            "case_003_passes",
            "case_011_passes",
        ):
            _validate_exact_int(
                payload.get(key),
                minimum=0,
                maximum=MODEL_COMPARISON_PLANNED_CALLS,
                code=f"invalid_model_comparison_summary_{key}",
            )
        if payload.get("status") == "eligible" and any(
            payload.get(key) != expected
            for key, expected in (
                ("provider_calls", 22),
                ("valid_calls", 22),
                ("semantic_passes", 22),
                ("case_005_passes", 2),
                ("case_003_passes", 2),
                ("case_011_passes", 2),
            )
        ):
            raise ValueError("invalid_model_comparison_summary_eligibility")
        models = payload.get("observed_models")
        if (
            not isinstance(models, list)
            or models != sorted(set(models))
            or any(
                model not in {configuration["model"], configuration["canonical_slug"]}
                for model in models
            )
            or (payload.get("status") == "eligible" and not models)
        ):
            raise ValueError("invalid_model_comparison_summary_models")
        providers = payload.get("observed_providers")
        if (
            not isinstance(providers, list)
            or providers != sorted(set(providers))
            or any(provider not in configuration["allowed_providers"] for provider in providers)
            or (payload.get("status") == "eligible" and not providers)
        ):
            raise ValueError("invalid_model_comparison_summary_providers")
        for key in ("latency_median_ms", "latency_p95_ms", "latency_max_ms"):
            _validate_optional_metric(
                payload.get(key),
                maximum=MODEL_COMPARISON_TIMEOUT_S * 1000,
                code=f"invalid_model_comparison_summary_{key}",
            )
        for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
            value = payload.get(key)
            if value is not None:
                _validate_exact_int(
                    value,
                    minimum=0,
                    maximum=10_000_000,
                    code=f"invalid_model_comparison_summary_{key}",
                )
        _validate_optional_metric(
            payload.get("cost_usd"),
            maximum=MODEL_COMPARISON_MAX_ESTIMATED_COST_USD,
            code="invalid_model_comparison_summary_cost",
        )
    else:
        recommendation = payload.get("recommendation")
        if recommendation not in _MODEL_COMPARISON_RECOMMENDATIONS:
            raise ValueError("invalid_model_comparison_campaign_recommendation")
        eligible = payload.get("eligible_configurations")
        if (
            not isinstance(eligible, list)
            or eligible != sorted(set(eligible))
            or any(config_id not in MODEL_COMPARISON_CONFIGURATIONS for config_id in eligible)
        ):
            raise ValueError("invalid_model_comparison_campaign_eligible")
        statuses = payload.get("configuration_statuses")
        if (
            not isinstance(statuses, Mapping)
            or set(statuses) != set(MODEL_COMPARISON_CONFIGURATION_IDS)
            or any(status not in {"eligible", "non_eligible", "inconclusive"} for status in statuses.values())
        ):
            raise ValueError("invalid_model_comparison_campaign_statuses")
        if payload.get("runtime_cutover_authorized") is not False:
            raise ValueError("invalid_model_comparison_campaign_cutover")
        for key in ("protocol_sha256", "records_sha256"):
            _validate_hash(payload.get(key))
        if (
            payload.get("historical_control_status") != "comparable"
            or payload.get("historical_control_model") != projection.PRIMARY_MODEL
            or payload.get("historical_control_provider_calls") != 22
            or payload.get("historical_control_semantic_passes") != 20
        ):
            raise ValueError("invalid_model_comparison_campaign_control")
        for key in ("provider_calls", "valid_calls"):
            _validate_exact_int(
                payload.get(key),
                minimum=0,
                maximum=10_000_000,
                code=f"invalid_model_comparison_campaign_{key}",
            )
        for key in ("prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"):
            value = payload.get(key)
            if value is not None:
                _validate_exact_int(
                    value,
                    minimum=0,
                    maximum=10_000_000,
                    code=f"invalid_model_comparison_campaign_{key}",
                )
        _validate_optional_metric(
            payload.get("cost_usd"),
            maximum=MODEL_COMPARISON_MAX_ESTIMATED_COST_USD,
            code="invalid_model_comparison_campaign_cost",
        )
    return payload


def _model_call_record(
    *,
    corpus_hash: str,
    freeze_commit: str,
    case: Mapping[str, Any],
    configuration_id: str,
    repetition: int,
    sequence_index: int,
    fingerprints: Mapping[str, str],
    payload: Mapping[str, Any],
    provider: Mapping[str, Any],
    score: Mapping[str, Any],
) -> dict[str, Any]:
    configuration = MODEL_COMPARISON_CONFIGURATIONS[configuration_id]
    status = str(score.get("status") or "transport_error")
    reason_code = str(score.get("reason_code") or "transport_error")
    observed_model = str(provider.get("model") or "")
    observed_provider = str(provider.get("provider") or "")
    observed_service_tier = str(provider.get("service_tier") or "")
    usage = dict(provider.get("usage") or {})
    reasoning_tokens = _reasoning_tokens_or_none(usage)
    latency = provider.get("elapsed_ms")
    cost = provider.get("cost_estimate_usd")
    if status == "ok" and observed_model not in {
        configuration["model"],
        configuration["canonical_slug"],
    }:
        status, reason_code = "routing_inconclusive", "observed_model_mismatch"
    elif status == "ok" and observed_provider not in configuration["allowed_providers"]:
        status, reason_code = "routing_inconclusive", "observed_provider_mismatch"
    elif status == "ok" and observed_service_tier not in {"", "default", "standard"}:
        status, reason_code = "routing_inconclusive", "nonstandard_service_tier"
    elif status == "ok" and (
        not _is_finite_number(latency)
        or not 0 <= float(latency) <= MODEL_COMPARISON_TIMEOUT_S * 1000
    ):
        status, reason_code = "metrics_inconclusive", "latency_budget_exceeded"
    elif status == "ok" and any(
        isinstance(usage.get(key), bool) or not isinstance(usage.get(key), int)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    ):
        status, reason_code = "metrics_inconclusive", "usage_missing"
    elif status == "ok" and reasoning_tokens is None:
        status, reason_code = "metrics_inconclusive", "reasoning_usage_missing"
    elif status == "ok" and (not _is_finite_number(cost) or float(cost) <= 0):
        status, reason_code = "metrics_inconclusive", "cost_missing"
    if status in {
        "empty_output",
        "timeout",
        "refusal",
        "transport_error",
        "invalid_json",
        "invalid_schema",
    }:
        reason_code = "provider_refusal" if status == "refusal" else status
        score = dict(score, semantic_codes=[])
    scorer_pass = status == "ok" and bool(score.get("pass"))
    return {
        "record_type": "provider_call",
        "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
        "corpus_id": MODEL_COMPARISON_CORPUS_ID,
        "corpus_sha256": corpus_hash,
        "freeze_commit": freeze_commit,
        "case_id": case["id"],
        "configuration_id": configuration_id,
        "requested_model": configuration["model"],
        "requested_reasoning_effort": configuration["reasoning_effort"],
        "transport": "standard",
        "batch": False,
        "provider_fallbacks": False,
        "max_tokens": MODEL_COMPARISON_MAX_TOKENS,
        "timeout_s": MODEL_COMPARISON_TIMEOUT_S,
        "repetition": repetition,
        "sequence_index": sequence_index,
        "status": status,
        "reason_code": reason_code,
        "observed_model": observed_model,
        "observed_provider": observed_provider,
        "observed_service_tier": observed_service_tier,
        "final_judgment_posture": score.get("final_judgment_posture"),
        "final_output_regime": score.get("final_output_regime"),
        "scorer_pass": scorer_pass,
        "semantic_codes": list(score.get("semantic_codes") or []),
        "latency_ms": latency,
        "prompt_tokens": usage.get("prompt_tokens"),
        "completion_tokens": usage.get("completion_tokens"),
        "reasoning_tokens": reasoning_tokens,
        "total_tokens": usage.get("total_tokens"),
        "cost_usd": cost,
        "cost_source": str(provider.get("cost_estimate_source") or ""),
        "system_sha256": fingerprints["current_system_sha256"],
        "user_sha256": _sha256_text(str(payload["messages"][1]["content"])),
        "canonical_sha256": fingerprints["current_canonical_sha256"],
        "messages_sha256": model_comparison_messages_sha256(payload),
        "request_sha256": _sha256_text(_compact_json(payload)),
        "raw_content_included": False,
    }


def synthetic_valid_model_comparison_call_record() -> dict[str, Any]:
    return {
        "record_type": "provider_call",
        "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
        "corpus_id": MODEL_COMPARISON_CORPUS_ID,
        "corpus_sha256": "a" * 64,
        "freeze_commit": "f" * 40,
        "case_id": "L4C1-VAL-001",
        "configuration_id": "gemini_3_7_flash_medium",
        "requested_model": "google/gemini-3.7-flash",
        "requested_reasoning_effort": "medium",
        "transport": "standard",
        "batch": False,
        "provider_fallbacks": False,
        "max_tokens": 500,
        "timeout_s": 15,
        "repetition": 1,
        "sequence_index": 1,
        "status": "ok",
        "reason_code": "accepted",
        "observed_model": "google/gemini-3.7-flash",
        "observed_provider": "Google AI Studio",
        "observed_service_tier": "default",
        "final_judgment_posture": "answer",
        "final_output_regime": "simple",
        "scorer_pass": True,
        "semantic_codes": [],
        "latency_ms": 1.0,
        "prompt_tokens": 1,
        "completion_tokens": 1,
        "reasoning_tokens": 0,
        "total_tokens": 2,
        "cost_usd": 0.000001,
        "cost_source": "openrouter_models_pricing",
        "system_sha256": "b" * 64,
        "user_sha256": "c" * 64,
        "canonical_sha256": "d" * 64,
        "messages_sha256": "e" * 64,
        "request_sha256": "f" * 64,
        "raw_content_included": False,
    }


def synthetic_passing_model_comparison_records(
    configuration_id: str,
) -> list[dict[str, Any]]:
    configuration = MODEL_COMPARISON_CONFIGURATIONS[configuration_id]
    records: list[dict[str, Any]] = []
    sequence = 0
    for case in load_policy_corpus()["cases"]:
        posture, regime = (case.get("expected") or {})["allowed_pairs"][0]
        for repetition in range(1, MODEL_COMPARISON_REPETITIONS + 1):
            sequence += 1
            record = synthetic_valid_model_comparison_call_record()
            record.update(
                case_id=case["id"],
                configuration_id=configuration_id,
                requested_model=configuration["model"],
                requested_reasoning_effort=configuration["reasoning_effort"],
                observed_model=configuration["model"],
                observed_provider=configuration["allowed_providers"][0],
                repetition=repetition,
                sequence_index=sequence,
                final_judgment_posture=posture,
                final_output_regime=regime,
                latency_ms=float(100 + sequence),
                prompt_tokens=100,
                completion_tokens=20,
                reasoning_tokens=10,
                total_tokens=120,
                cost_usd=0.0001,
            )
            records.append(validate_model_comparison_record(record))
    return records


def _complete_metric_sum(records: Sequence[Mapping[str, Any]], key: str) -> int | float | None:
    values = [record.get(key) for record in records]
    if not values or any(value is None for value in values):
        return None
    return sum(values)


def summarize_model_comparison_configuration(
    records: Sequence[Mapping[str, Any]],
    configuration_id: str,
) -> dict[str, Any]:
    configuration = MODEL_COMPARISON_CONFIGURATIONS[configuration_id]
    calls = [
        record
        for record in records
        if record.get("record_type") == "provider_call"
        and record.get("configuration_id") == configuration_id
    ]
    valid = [record for record in calls if record.get("status") == "ok"]
    reasons: list[str] = []
    if len(calls) != CASE_COUNT * MODEL_COMPARISON_REPETITIONS:
        reasons.append("missing_calls")
    expected_groups = {
        (f"L4C1-VAL-{index:03d}", repetition)
        for index in range(1, CASE_COUNT + 1)
        for repetition in range(1, MODEL_COMPARISON_REPETITIONS + 1)
    }
    observed_groups = {
        (str(record.get("case_id")), int(record.get("repetition") or 0))
        for record in calls
    }
    if observed_groups != expected_groups and "missing_calls" not in reasons:
        reasons.append("missing_calls")
    if any(record.get("status") in {"routing_inconclusive"} for record in calls):
        reasons.append("non_comparable_transport")
    if any(record.get("status") == "metrics_inconclusive" for record in calls):
        reasons.append("metrics_missing")
    if any(
        record.get("status")
        in {
            "empty_output",
            "timeout",
            "refusal",
            "transport_error",
            "invalid_json",
            "invalid_schema",
        }
        for record in calls
    ):
        reasons.append("provider_result_invalid")
    semantic_passes = sum(bool(record.get("scorer_pass")) for record in calls)
    all_calls_semantically_comparable = len(valid) == 22
    if all_calls_semantically_comparable and semantic_passes != 22:
        reasons.append("semantic_invariant_failure")
    case_passes = {
        case_id: sum(
            bool(record.get("scorer_pass"))
            for record in calls
            if record.get("case_id") == case_id
        )
        for case_id in ("L4C1-VAL-005", "L4C1-VAL-003", "L4C1-VAL-011")
    }
    for case_id, reason in (
        ("L4C1-VAL-005", "critical_case_005_failed"),
        ("L4C1-VAL-003", "presence_case_003_failed"),
        ("L4C1-VAL-011", "countercase_011_failed"),
    ):
        if all_calls_semantically_comparable and case_passes[case_id] != 2:
            reasons.append(reason)
    if reasons:
        status = (
            "inconclusive"
            if any(
                reason
                in {
                    "missing_calls",
                    "non_comparable_transport",
                    "metrics_missing",
                    "provider_result_invalid",
                }
                for reason in reasons
            )
            else "non_eligible"
        )
    else:
        status = "eligible"
        reasons = ["eligible"]
    latencies = [float(record["latency_ms"]) for record in calls if record.get("latency_ms") is not None]
    latencies.sort()
    p95 = latencies[max(0, math.ceil(len(latencies) * 0.95) - 1)] if latencies else None
    summary = {
        "record_type": "configuration_summary",
        "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
        "corpus_id": MODEL_COMPARISON_CORPUS_ID,
        "corpus_sha256": str(calls[0]["corpus_sha256"]) if calls else HISTORICAL_CORPUS_SHA256,
        "freeze_commit": str(calls[0]["freeze_commit"]) if calls else "f" * 40,
        "configuration_id": configuration_id,
        "requested_model": configuration["model"],
        "requested_reasoning_effort": configuration["reasoning_effort"],
        "status": status,
        "reason_codes": sorted(set(reasons)),
        "provider_calls": len(calls),
        "valid_calls": len(valid),
        "semantic_passes": semantic_passes,
        "case_005_passes": case_passes["L4C1-VAL-005"],
        "case_003_passes": case_passes["L4C1-VAL-003"],
        "case_011_passes": case_passes["L4C1-VAL-011"],
        "observed_models": sorted(
            {str(record["observed_model"]) for record in calls if record.get("observed_model")}
        ),
        "observed_providers": sorted(
            {str(record["observed_provider"]) for record in calls if record.get("observed_provider")}
        ),
        "latency_median_ms": round(statistics.median(latencies), 3) if latencies else None,
        "latency_p95_ms": round(p95, 3) if p95 is not None else None,
        "latency_max_ms": round(max(latencies), 3) if latencies else None,
        "prompt_tokens": _complete_metric_sum(calls, "prompt_tokens"),
        "completion_tokens": _complete_metric_sum(calls, "completion_tokens"),
        "reasoning_tokens": _complete_metric_sum(calls, "reasoning_tokens"),
        "total_tokens": _complete_metric_sum(calls, "total_tokens"),
        "cost_usd": (
            round(float(_complete_metric_sum(calls, "cost_usd")), 8)
            if _complete_metric_sum(calls, "cost_usd") is not None
            else None
        ),
        "transport": "standard",
        "batch": False,
        "raw_content_included": False,
    }
    if calls:
        return validate_model_comparison_record(summary)
    return summary


def _dominates(left: Mapping[str, Any], right: Mapping[str, Any]) -> bool:
    keys = (
        "cost_usd",
        "latency_median_ms",
        "latency_p95_ms",
        "reasoning_tokens",
        "total_tokens",
    )
    if any(left.get(key) is None or right.get(key) is None for key in keys):
        return False
    return all(float(left[key]) <= float(right[key]) for key in keys) and any(
        float(left[key]) < float(right[key]) for key in keys
    )


def model_comparison_recommendation(
    summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_id = {str(summary.get("configuration_id")): summary for summary in summaries}
    if set(by_id) != set(MODEL_COMPARISON_CONFIGURATION_IDS):
        recommendation = "inconclusive"
        eligible: list[str] = []
    elif any(summary.get("status") == "inconclusive" for summary in summaries):
        recommendation = "inconclusive"
        eligible = sorted(
            config_id for config_id, summary in by_id.items() if summary.get("status") == "eligible"
        )
    else:
        eligible = sorted(
            config_id for config_id, summary in by_id.items() if summary.get("status") == "eligible"
        )
        if not eligible:
            recommendation = "no_eligible_candidate"
        else:
            contenders = list(eligible)
            for medium, high in (
                ("gemini_3_7_flash_medium", "gemini_3_7_flash_high"),
                ("luna_pro_medium", "luna_pro_high"),
            ):
                if medium in contenders and high in contenders:
                    contenders.remove(high)
            if len(contenders) == 1:
                recommendation = f"recommend_{contenders[0]}"
            else:
                dominant = [
                    contender
                    for contender in contenders
                    if all(
                        contender == other or _dominates(by_id[contender], by_id[other])
                        for other in contenders
                    )
                ]
                recommendation = (
                    f"recommend_{dominant[0]}"
                    if len(dominant) == 1
                    else "human_tradeoff_required"
                )
    return {
        "recommendation": recommendation,
        "eligible_configurations": eligible,
        "runtime_cutover_authorized": False,
    }


def _model_campaign_summary_record(
    *,
    calls: Sequence[Mapping[str, Any]],
    summaries: Sequence[Mapping[str, Any]],
    protocol: Mapping[str, Any],
    records_sha256: str,
) -> dict[str, Any]:
    decision = model_comparison_recommendation(summaries)
    witness = protocol["historical_control"]
    return validate_model_comparison_record(
        {
            "record_type": "campaign_summary",
            "protocol_version": MODEL_COMPARISON_PROTOCOL_VERSION,
            "corpus_id": MODEL_COMPARISON_CORPUS_ID,
            "corpus_sha256": protocol["corpus_sha256"],
            "freeze_commit": protocol["freeze_commit"],
            "recommendation": decision["recommendation"],
            "eligible_configurations": decision["eligible_configurations"],
            "configuration_statuses": {
                summary["configuration_id"]: summary["status"] for summary in summaries
            },
            "provider_calls": len(calls),
            "valid_calls": sum(record["status"] == "ok" for record in calls),
            "prompt_tokens": _complete_metric_sum(calls, "prompt_tokens"),
            "completion_tokens": _complete_metric_sum(calls, "completion_tokens"),
            "reasoning_tokens": _complete_metric_sum(calls, "reasoning_tokens"),
            "total_tokens": _complete_metric_sum(calls, "total_tokens"),
            "cost_usd": (
                round(float(_complete_metric_sum(calls, "cost_usd")), 8)
                if _complete_metric_sum(calls, "cost_usd") is not None
                else None
            ),
            "historical_control_status": witness["status"],
            "historical_control_model": witness["model"],
            "historical_control_provider_calls": witness["provider_calls"],
            "historical_control_semantic_passes": witness["semantic_passes"],
            "protocol_sha256": _sha256_text(_compact_json(protocol)),
            "records_sha256": records_sha256,
            "runtime_cutover_authorized": False,
            "raw_content_included": False,
        }
    )


def reclassify_model_comparison_records(
    records: Sequence[Mapping[str, Any]],
    *,
    freeze_commit: str,
) -> list[dict[str, Any]]:
    corpus = load_policy_corpus()
    protocol = model_comparison_protocol_document(corpus, freeze_commit=freeze_commit)
    normalized_calls: list[dict[str, Any]] = []
    for source in records:
        if source.get("record_type") != "provider_call":
            continue
        record = dict(source)
        status = str(record.get("status") or "")
        if status in {
            "empty_output",
            "timeout",
            "refusal",
            "transport_error",
            "invalid_json",
            "invalid_schema",
        }:
            record["reason_code"] = "provider_refusal" if status == "refusal" else status
            record["semantic_codes"] = []
            record["scorer_pass"] = False
        normalized_calls.append(validate_model_comparison_record(record))
    if len(normalized_calls) != MODEL_COMPARISON_PLANNED_CALLS:
        raise ValueError("unexpected_provider_call_count")
    summaries = [
        summarize_model_comparison_configuration(normalized_calls, configuration_id)
        for configuration_id in MODEL_COMPARISON_CONFIGURATION_IDS
    ]
    rebuilt: list[dict[str, Any]] = [*normalized_calls, *summaries]
    records_hash = _sha256_text("".join(_compact_json(record) + "\n" for record in rebuilt))
    rebuilt.append(
        _model_campaign_summary_record(
            calls=normalized_calls,
            summaries=summaries,
            protocol=protocol,
            records_sha256=records_hash,
        )
    )
    return rebuilt


def run_model_comparison_campaign(
    *,
    output_path: Path,
    freeze_commit: str,
    client: OpenRouterClient,
) -> dict[str, Any]:
    corpus = load_policy_corpus()
    protocol = model_comparison_protocol_document(corpus, freeze_commit=freeze_commit)
    prompt = (REPO_ROOT / "app/prompts/validation_agent.txt").read_text(
        encoding="utf-8"
    ).strip()
    records: list[dict[str, Any]] = []
    sequence_index = 0
    for case_index, case in enumerate(corpus["cases"]):
        messages = build_policy_message_pair(case, prompt)["current"]
        fingerprints = policy_pair_fingerprints({"current": messages, "candidate": build_policy_message_pair(case, prompt)["candidate"]})
        built = projection.build_current_messages(case, prompt)
        for repetition in range(1, MODEL_COMPARISON_REPETITIONS + 1):
            for configuration_id in model_comparison_configuration_order(
                case_index,
                repetition,
            ):
                sequence_index += 1
                if sequence_index > MODEL_COMPARISON_ABSOLUTE_CALL_CAP:
                    raise ValueError("provider_call_cap_exceeded")
                payload = build_model_comparison_payload(messages, configuration_id)
                provider = client.chat_completion(
                    payload,
                    caller="validation_agent",
                    timeout_s=MODEL_COMPARISON_TIMEOUT_S,
                )
                provider_status, provider_reason = projection._provider_status(provider)
                if provider_status == "ok":
                    score = projection.score_parsed_output(
                        case,
                        str(provider.get("raw_text") or ""),
                        hard_guard_payload=built["hard_guard"],
                    )
                else:
                    score = {
                        "status": provider_status,
                        "reason_code": provider_reason,
                        "final_judgment_posture": None,
                        "final_output_regime": None,
                        "pass": False,
                        "semantic_codes": [],
                    }
                record = _model_call_record(
                    corpus_hash=protocol["corpus_sha256"],
                    freeze_commit=freeze_commit,
                    case=case,
                    configuration_id=configuration_id,
                    repetition=repetition,
                    sequence_index=sequence_index,
                    fingerprints=fingerprints,
                    payload=payload,
                    provider=provider,
                    score=score,
                )
                records.append(validate_model_comparison_record(record))
                cost_so_far = sum(float(item.get("cost_usd") or 0) for item in records)
                if cost_so_far > MODEL_COMPARISON_MAX_ESTIMATED_COST_USD:
                    raise ValueError("provider_cost_cap_exceeded")
    if sequence_index != MODEL_COMPARISON_PLANNED_CALLS:
        raise ValueError("unexpected_provider_call_count")
    summaries = [
        summarize_model_comparison_configuration(records, configuration_id)
        for configuration_id in MODEL_COMPARISON_CONFIGURATION_IDS
    ]
    records.extend(summaries)
    decision = model_comparison_recommendation(summaries)
    records_hash = _sha256_text(
        "".join(_compact_json(record) + "\n" for record in records)
    )
    calls = [record for record in records if record["record_type"] == "provider_call"]
    records.append(
        _model_campaign_summary_record(
            calls=calls,
            summaries=summaries,
            protocol=protocol,
            records_sha256=records_hash,
        )
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(_compact_json(record) + "\n" for record in records),
        encoding="utf-8",
    )
    return {
        "decision": decision,
        "protocol": protocol,
        "records": records,
        "artifact_sha256": hashlib.sha256(output_path.read_bytes()).hexdigest(),
    }


def run_live_campaign(
    *,
    output_path: Path,
    freeze_commit: str,
    client: OpenRouterClient,
) -> dict[str, Any]:
    corpus = load_policy_corpus()
    protocol = protocol_document(corpus, freeze_commit=freeze_commit)
    system_prompt = (REPO_ROOT / "app/prompts/validation_agent.txt").read_text(
        encoding="utf-8"
    ).strip()
    records: list[dict[str, Any]] = []
    call_count = 0
    for case in corpus["cases"]:
        pair = build_policy_message_pair(case, system_prompt)
        fingerprints = policy_pair_fingerprints(pair)
        built = projection.build_current_messages(case, system_prompt)
        for model, source in projection.MODEL_ROLES.items():
            for repetition in range(1, REPETITIONS + 1):
                scored: dict[str, dict[str, Any]] = {}
                order = ("current", "candidate") if repetition % 2 else ("candidate", "current")
                for policy in order:
                    call_count += 1
                    if call_count > ABSOLUTE_PROVIDER_CALL_CAP:
                        raise ValueError("provider_call_cap_exceeded")
                    provider = client.chat_completion(
                        {
                            "model": model,
                            "messages": pair[policy],
                            "temperature": projection.TEMPERATURE,
                            "top_p": projection.TOP_P,
                            "max_tokens": projection.MAX_TOKENS,
                        },
                        caller="validation_agent",
                        timeout_s=projection.TIMEOUT_S,
                    )
                    provider_status, provider_reason = projection._provider_status(provider)
                    if provider_status == "ok":
                        score = projection.score_parsed_output(
                            case,
                            str(provider.get("raw_text") or ""),
                            hard_guard_payload=built["hard_guard"],
                        )
                    else:
                        score = {
                            "status": provider_status,
                            "reason_code": provider_reason,
                            "final_judgment_posture": None,
                            "final_output_regime": None,
                            "pass": False,
                            "semantic_codes": [],
                        }
                    scored[policy] = score
                    usage = dict(provider.get("usage") or {})
                    record = {
                        "record_type": "provider_call",
                        "protocol_version": PROTOCOL_VERSION,
                        "corpus_id": CORPUS_ID,
                        "corpus_sha256": protocol["corpus_sha256"],
                        "case_id": case["id"],
                        "policy": policy,
                        "policy_version": POLICY_VERSIONS[policy],
                        "policy_sha256": POLICY_HASHES[policy],
                        "freeze_commit": freeze_commit,
                        "source": source,
                        "model": model,
                        "observed_model": str(provider.get("model") or ""),
                        "observed_provider": str(provider.get("provider") or ""),
                        "generation": protocol["generation"],
                        "repetition": repetition,
                        "status": score["status"],
                        "reason_code": score["reason_code"],
                        "final_judgment_posture": score.get("final_judgment_posture"),
                        "final_output_regime": score.get("final_output_regime"),
                        "scorer_pass": bool(score.get("pass")),
                        "divergence_codes": [],
                        "latency_ms": provider.get("elapsed_ms"),
                        "prompt_tokens": usage.get("prompt_tokens"),
                        "completion_tokens": usage.get("completion_tokens"),
                        "total_tokens": usage.get("total_tokens"),
                        "cost_usd": provider.get("cost_estimate_usd"),
                        "system_sha256": fingerprints[f"{policy}_system_sha256"],
                        "nonpolicy_user_sha256": fingerprints[
                            f"{policy}_nonpolicy_user_sha256"
                        ],
                        "canonical_sha256": fingerprints[f"{policy}_canonical_sha256"],
                    }
                    records.append(validate_content_free_record(record))
                comparison = compare_pair(
                    case=case,
                    source=source,
                    current_score=scored["current"],
                    candidate_score=scored["candidate"],
                )
                status = str(comparison["classification"])
                pair_record = {
                    "record_type": "pair_comparison",
                    "protocol_version": PROTOCOL_VERSION,
                    "corpus_id": CORPUS_ID,
                    "corpus_sha256": protocol["corpus_sha256"],
                    "case_id": case["id"],
                    "policy": "current_vs_candidate",
                    "policy_version": "",
                    "policy_sha256": "",
                    "freeze_commit": freeze_commit,
                    "source": source,
                    "model": model,
                    "observed_model": "",
                    "observed_provider": "",
                    "generation": protocol["generation"],
                    "repetition": repetition,
                    "status": status,
                    "reason_code": status,
                    "final_judgment_posture": None,
                    "final_output_regime": None,
                    "scorer_pass": status in {"pass", "candidate_corrects_shared_failure"},
                    "divergence_codes": comparison["divergence_codes"],
                    "latency_ms": None,
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "cost_usd": None,
                    "system_sha256": fingerprints["current_system_sha256"],
                    "nonpolicy_user_sha256": fingerprints[
                        "current_nonpolicy_user_sha256"
                    ],
                    "canonical_sha256": fingerprints["current_canonical_sha256"],
                }
                records.append(validate_content_free_record(pair_record))
    if call_count != PLANNED_PROVIDER_CALLS:
        raise ValueError("unexpected_provider_call_count")
    decision = campaign_decision(records)
    summary = {
        "record_type": "campaign_summary",
        "protocol_version": PROTOCOL_VERSION,
        "corpus_id": CORPUS_ID,
        "corpus_sha256": protocol["corpus_sha256"],
        "case_id": "campaign",
        "policy": "current_vs_candidate",
        "policy_version": "",
        "policy_sha256": "",
        "freeze_commit": freeze_commit,
        "source": "combined",
        "model": "primary_and_fallback",
        "observed_model": "",
        "observed_provider": "",
        "generation": protocol["generation"],
        "repetition": 0,
        "status": decision["decision"],
        "reason_code": decision["reason_code"],
        "final_judgment_posture": None,
        "final_output_regime": None,
        "scorer_pass": decision["decision"] == "pass",
        "divergence_codes": sorted(
            {
                code
                for record in records
                for code in record.get("divergence_codes") or []
            }
        ),
        "latency_ms": None,
        "prompt_tokens": sum(int(record.get("prompt_tokens") or 0) for record in records),
        "completion_tokens": sum(
            int(record.get("completion_tokens") or 0) for record in records
        ),
        "total_tokens": sum(int(record.get("total_tokens") or 0) for record in records),
        "cost_usd": round(sum(float(record.get("cost_usd") or 0) for record in records), 8),
        "system_sha256": "",
        "nonpolicy_user_sha256": "",
        "canonical_sha256": "",
    }
    records.append(validate_content_free_record(summary))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        "".join(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records),
        encoding="utf-8",
    )
    return {"decision": decision, "records": records, "protocol": protocol}


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--model-comparison", action="store_true")
    args = parser.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the live comparison")
    base_url = (os.environ.get("OPENROUTER_BASE") or "https://openrouter.ai/api/v1").rstrip(
        "/"
    )
    if args.model_comparison:
        client = OpenRouterClient.from_env(
            base_url=base_url,
            title="FridaDev/ValidationModelComparison",
        )
        result = run_model_comparison_campaign(
            output_path=args.output,
            freeze_commit=args.freeze_commit,
            client=client,
        )
        decision = result["decision"]["recommendation"]
        provider_calls = MODEL_COMPARISON_PLANNED_CALLS
        exit_code = 2 if decision == "inconclusive" else 0
    else:
        client = OpenRouterClient(
            OpenRouterConfig(
                base_url=base_url,
                api_key=api_key,
                referer=os.environ.get("OPENROUTER_REFERER", "").strip(),
                title="FridaDev/ValidationPolicy",
            )
        )
        result = run_live_campaign(
            output_path=args.output,
            freeze_commit=args.freeze_commit,
            client=client,
        )
        decision = result["decision"]
        provider_calls = PLANNED_PROVIDER_CALLS
        exit_code = 0 if result["decision"]["decision"] == "pass" else 2
    print(
        json.dumps(
            {
                "decision": decision,
                "provider_calls": provider_calls,
                "artifact": str(args.output),
            },
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(_main())
