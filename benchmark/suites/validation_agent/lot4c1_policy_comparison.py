"""Frozen current/candidate Validation policy comparison for Lot 4C.1.

Only the bounded decision-policy fragment differs between paired provider
calls. Raw provider output is parsed in memory and never enters the artifact.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
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
    args = parser.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the live comparison")
    base_url = (os.environ.get("OPENROUTER_BASE") or "https://openrouter.ai/api/v1").rstrip(
        "/"
    )
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
    print(
        json.dumps(
            {
                "decision": result["decision"],
                "provider_calls": PLANNED_PROVIDER_CALLS,
                "artifact": str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0 if result["decision"]["decision"] == "pass" else 2


if __name__ == "__main__":
    raise SystemExit(_main())
