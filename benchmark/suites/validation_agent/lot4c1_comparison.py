"""Frozen Validation v1/v2 comparison for Lot 4C.1.

The live campaign changes exactly one provider-visible block: the bounded
``canonical_inputs`` projection.  Raw provider output exists only in memory
until it has been parsed and reduced to the content-free JSONL contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) not in sys.path:
    sys.path.insert(0, str(APP_ROOT))

from benchmark.core.openrouter import OpenRouterClient, OpenRouterConfig
from core.hermeneutic_node.inputs import identity_input
from core.hermeneutic_node.inputs import memory_arbitration_input
from core.hermeneutic_node.inputs import memory_retrieved_input
from core.hermeneutic_node.inputs import recent_context_input
from core.hermeneutic_node.inputs import recent_window_input
from core.hermeneutic_node.inputs import stimmung_input
from core.hermeneutic_node.inputs import summary_input
from core.hermeneutic_node.inputs import time_input
from core.hermeneutic_node.inputs import user_turn_input
from core.hermeneutic_node.inputs import web_input
from core.hermeneutic_node.validation import hard_guards
from core.hermeneutic_node.validation import validation_canonical_family_projection as family_projection
from core.hermeneutic_node.validation import validation_canonical_projection
from core.hermeneutic_node.validation import validation_contract
from core.hermeneutic_node.validation import validation_messages


CORPUS_PATH = Path(
    "benchmark/suites/validation_agent/fixtures/lot4c1_validation_projection_cases.json"
)
CORPUS_SCHEMA_VERSION = "lot4c1_validation_projection_corpus_v1"
PROTOCOL_VERSION = "lot4c1_validation_projection_comparison_v1"
HISTORICAL_COMMIT = "ba246653fc4a68dfac340a34921cc48bee820bc8"
HISTORICAL_PROJECTION_VERSION = "validation_canonical_inputs_v1"
HISTORICAL_PROJECTOR_SHA256 = (
    "91b1f911c7a14dd18f461287884c89a3d845dc15d1a478e89b48df85fe7b3729"
)
CURRENT_PROJECTION_VERSION = "validation_canonical_inputs_v2"
PRIMARY_MODEL = "google/gemini-3.1-flash-lite"
FALLBACK_MODEL = "openai/gpt-5.4-nano"
MODEL_ROLES = {PRIMARY_MODEL: "primary", FALLBACK_MODEL: "fallback"}
TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 140
TIMEOUT_S = 15
REASONING_EFFORT = None
REPETITIONS = 2
CASE_COUNT = 10
PROJECTION_COUNT = 2
PLANNED_PROVIDER_CALLS = CASE_COUNT * PROJECTION_COUNT * len(MODEL_ROLES) * REPETITIONS
ABSOLUTE_PROVIDER_CALL_CAP = 96
MAX_ESTIMATED_COST_USD = 0.10
EXPECTED_ACCEPTED_V2_MAX_CHARS = 3741
EXPECTED_RUNTIME_EMITTABLE_V2_MAX_CHARS = 3546
CANONICAL_MARKER = "canonical_inputs (supports secondaires de relecture contextuelle):\n"
ARTIFACT_RECORD_KEYS = {
    "record_type",
    "protocol_version",
    "corpus_id",
    "corpus_sha256",
    "case_id",
    "projection",
    "source_commit",
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
    "noncanonical_user_sha256",
    "canonical_sha256",
}


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def validate_content_free_record(record: Mapping[str, Any]) -> dict[str, Any]:
    payload = dict(record)
    if set(payload) != ARTIFACT_RECORD_KEYS:
        raise ValueError("invalid_lot4c1_artifact_fields")
    forbidden_fragments = {
        "dialogue",
        "raw_text",
        "prompt_complete",
        "canonical_inputs",
        "provider_payload",
        "exception",
        "url",
        "secret",
        "memory_content",
        "identity_content",
    }
    serialized_keys = " ".join(payload).lower()
    if any(fragment in serialized_keys for fragment in forbidden_fragments):
        raise ValueError("lot4c1_artifact_raw_content_forbidden")
    for key in ("system_sha256", "noncanonical_user_sha256", "canonical_sha256"):
        value = str(payload.get(key) or "")
        if value and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
            raise ValueError("invalid_lot4c1_artifact_fingerprint")
    return payload


def _longest(values: Sequence[str] | set[str]) -> str:
    return max(values, key=lambda item: (len(item), item))


def _longest_ordered(values: Sequence[str] | set[str], count: int) -> list[str]:
    return sorted(values, key=lambda item: (-len(item), item))[:count]


def _maximal_v2_projection(*, runtime_emittable: bool) -> dict[str, Any]:
    """Return a maximum derived from current validator limits and vocabularies.

    The accepted contract permits any bounded disposition on an absent family.
    The runtime projector emits ``redundant_elsewhere`` for its three duplicate
    families and the Summary builder cannot emit the validator's larger generic
    status/reason combination.  Those are the only intentional differences.
    """

    code = "x" * int(family_projection._CODE_RE.pattern.rsplit("{1,", 1)[1].split("}", 1)[0])
    tones = _longest_ordered(stimmung_input.ALLOWED_TONES, stimmung_input.ACTIVE_TONES_LIMIT)
    summary_family: dict[str, Any]
    if runtime_emittable:
        summary_family = {
            "schema_version": "v1",
            "status": "available",
            "reason_code": None,
            "error_code": None,
            "summary_present": True,
            "start_ts": code,
            "end_ts": code,
        }
    else:
        summary_family = {
            "schema_version": "v1",
            "status": code,
            "reason_code": code,
            "error_code": code,
            "summary_present": False,
            "start_ts": code,
            "end_ts": code,
        }
    families = {
        "memory_retrieved": {
            "schema_version": "v1",
            "status": code,
            "reason_code": code,
            "error_code": code,
            "retrieved_count": 999999,
            "parent_summary_count": 999999,
        },
        "memory_arbitration": {
            "schema_version": "v1",
            "status": code,
            "reason_code": code,
            "raw_candidates_count": 999999,
            "kept_count": 999999,
            "rejected_count": 999999,
            "injected_count": 999999,
        },
        "summary_input": summary_family,
        "identity_input": {
            "schema_version": "v2",
            "status": code,
            "reason_code": code,
            "error_code": code,
            "frida": {"static_present": False, "mutable_present": False},
            "user": {"static_present": False, "mutable_present": False},
        },
        "user_turn_input": {
            "schema_version": "v1",
            "geste_dialogique_dominant": _longest(family_projection._USER_GESTURES),
            "regime_probatoire": {
                "principe": "maximal_possible",
                "types_de_preuve_attendus": list(
                    item
                    for item in ("factuelle", "scientifique", "argumentative", "hermeneutique", "dialogique")
                    if item in family_projection._PROOF_TYPES
                ),
                "provenances": list(
                    item
                    for item in ("dialogue_trace", "dialogue_resume", "web")
                    if item in family_projection._PROVENANCES
                ),
                "regime_de_vigilance": _longest({"standard", "renforce"}),
                "composition_probatoire": _longest({"isolee", "appuyee"}),
            },
            "qualification_temporelle": {
                "portee_temporelle": _longest(family_projection._TEMPORAL_SCOPES),
                "ancrage_temporel": _longest(family_projection._TEMPORAL_ANCHORS),
            },
        },
        "user_turn_signals": {
            "present": False,
            "ambiguity_present": False,
            "underdetermination_present": False,
            "active_signal_families": list(family_projection._SIGNAL_FAMILIES),
            "active_signal_families_count": len(family_projection._SIGNAL_FAMILIES),
        },
        "stimmung_input": {
            "schema_version": stimmung_input.SCHEMA_VERSION,
            "present": True,
            "dominant_tone": tones[0],
            "active_tones": [{"tone": tone, "strength": 10} for tone in tones],
            "stability": _longest(validation_canonical_projection._STIMMUNG_STABILITIES),
            "shift_state": _longest(validation_canonical_projection._STIMMUNG_SHIFT_STATES),
            "turns_considered": stimmung_input.MAX_SIGNAL_TURNS,
        },
        "web_input": {
            "schema_version": "v1",
            "enabled": True,
            "status": code,
            "activation_mode": _longest(family_projection._WEB_ACTIVATION_MODES),
            "reason_code": code,
            "results_count": 999999,
            "read_state": code,
            "fallback_used": False,
            "web_confidence_level": code,
            "web_evidence_status": code,
            "web_evidence_can_answer": False,
            "web_evidence_requires_caveat": False,
            "web_evidence_can_suggest_reformulation": False,
            "web_evidence_external_fallback_used": False,
            "openrouter_fallback_used": False,
        },
    }
    dispositions = {}
    for family in validation_contract.CANONICAL_FAMILY_ORDER:
        if family in families:
            dispositions[family] = "included"
        elif runtime_emittable:
            dispositions[family] = "redundant_elsewhere"
        else:
            dispositions[family] = _longest(validation_contract.CANONICAL_FAMILY_DISPOSITIONS)
    return validation_messages.validate_validation_canonical_projection(
        {
            "projection_version": CURRENT_PROJECTION_VERSION,
            "stimmung_delivery": {"status": "full", "reason_code": "included"},
            "family_dispositions": dispositions,
            "families": families,
        }
    )


def measured_v2_maxima() -> dict[str, int]:
    accepted = len(_compact_json(_maximal_v2_projection(runtime_emittable=False)))
    runtime_emittable = len(_compact_json(_maximal_v2_projection(runtime_emittable=True)))
    return {
        "accepted_contract_chars": accepted,
        "runtime_emittable_chars": runtime_emittable,
        "budget_chars": validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS,
        "accepted_margin_chars": validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS - accepted,
        "runtime_emittable_margin_chars": (
            validation_contract.MAX_CANONICAL_INPUTS_JSON_CHARS - runtime_emittable
        ),
    }


def load_corpus(path: Path | None = None) -> dict[str, Any]:
    resolved = path or (REPO_ROOT / CORPUS_PATH)
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if payload.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("invalid_lot4c1_corpus_version")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != CASE_COUNT:
        raise ValueError("invalid_lot4c1_case_count")
    seen: set[str] = set()
    for case in cases:
        case_id = str(case.get("id") or "")
        if not case_id or case_id in seen:
            raise ValueError("invalid_lot4c1_case_id")
        seen.add(case_id)
        expected = case.get("expected") or {}
        pairs = expected.get("allowed_pairs")
        if not isinstance(pairs, list) or not pairs:
            raise ValueError("invalid_lot4c1_allowed_pairs")
        for pair in pairs:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or pair[0] not in validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES
                or pair[1] not in validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES
            ):
                raise ValueError("invalid_lot4c1_allowed_pair")
        if expected.get("presence_policy") not in {"required", "forbidden", "allowed"}:
            raise ValueError("invalid_lot4c1_presence_policy")
    return payload


def corpus_sha256(payload: Mapping[str, Any]) -> str:
    return _sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def _primary_verdict(case: Mapping[str, Any]) -> dict[str, Any]:
    source = dict(case.get("primary") or {})
    posture = str(source.get("judgment_posture") or "answer")
    regime = str(source.get("discursive_regime") or "simple")
    active = [str(item) for item in case.get("tags") or []]
    payload = {
        "schema_version": "v1",
        "epistemic_regime": str(source.get("epistemic_regime") or "certain"),
        "proof_regime": str(source.get("proof_regime") or "source_explicite_requise"),
        "uncertainty_posture": str(source.get("uncertainty_posture") or "discrete"),
        "judgment_posture": posture,
        "discursive_regime": regime,
        "resituation_level": "none",
        "time_reference_mode": str(source.get("time_reference_mode") or "atemporal"),
        "source_priority": [["tour_utilisateur"], ["temps"], ["memoire", "contexte_recent", "identity"]],
        "source_conflicts": [],
        "upstream_advisory": {
            "schema_version": "v1",
            "recommended_judgment_posture": posture,
            "proposed_output_regime": regime,
            "active_signal_families": active,
            "active_signal_families_count": len(active),
            "constraint_present": False,
        },
        "pipeline_directives_provisional": [f"posture_{posture}"],
        "audit": {"fail_open": False, "state_used": False, "degraded_fields": []},
    }
    return validation_contract.validate_primary_verdict(payload)


def _stimmung(profile: str) -> dict[str, Any]:
    if profile == "absent":
        return {
            "schema_version": "v1",
            "present": False,
            "dominant_tone": None,
            "active_tones": [],
            "stability": "",
            "shift_state": "",
            "turns_considered": 0,
        }
    if profile == "stable":
        return {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "apaisement",
            "active_tones": [{"tone": "apaisement", "strength": 6}],
            "stability": "stable",
            "shift_state": "steady",
            "turns_considered": 4,
        }
    if profile == "transition":
        return {
            "schema_version": "v1",
            "present": True,
            "dominant_tone": "frustration",
            "active_tones": [
                {"tone": "frustration", "strength": 6},
                {"tone": "apaisement", "strength": 4},
            ],
            "stability": "volatile",
            "shift_state": "candidate_shift",
            "turns_considered": 4,
        }
    raise ValueError("invalid_lot4c1_stimmung_profile")


def _web(profile: str) -> dict[str, Any]:
    if profile == "absent":
        return web_input.build_web_input(enabled=False, status="skipped", activation_mode="not_requested")
    if profile == "missing_external":
        return web_input.build_web_input(
            enabled=True,
            status="skipped",
            activation_mode="manual",
            reason_code="no_evidence",
            results_count=0,
            read_state="page_not_read_error",
        )
    if profile == "active_caveat":
        return web_input.build_web_input(
            enabled=True,
            status="ok",
            activation_mode="manual",
            reason_code="caveat",
            results_count=1,
            explicit_url_detected=True,
            read_state="page_not_read_snippet_fallback",
            sources=[
                {
                    "title": "synthetic-source",
                    "url": "https://synthetic.invalid/source",
                    "content": "synthetic-evidence",
                    "used_in_prompt": True,
                    "used_content_kind": "snippet",
                    "content_used": "synthetic-evidence",
                }
            ],
            web_confidence={"web_confidence_level": "bounded"},
            web_evidence={
                "web_evidence_status": "bounded",
                "web_evidence_can_answer": True,
                "web_evidence_requires_caveat": True,
                "web_evidence_can_suggest_reformulation": False,
                "web_evidence_external_fallback_used": False,
            },
        )
    raise ValueError("invalid_lot4c1_web_profile")


def build_case_inputs(case: Mapping[str, Any]) -> dict[str, Any]:
    dialogue = [dict(item) for item in case.get("dialogue") or []]
    current_message = str(dialogue[-1]["content"])
    time_payload = time_input.build_time_input(
        now_utc_iso="2026-08-29T10:00:00Z",
        timezone_name="UTC",
    )
    recent_payload = recent_context_input.build_recent_context_input(messages=dialogue)
    window_payload = recent_window_input.build_recent_window_input(
        recent_context_input_payload=recent_payload,
    )
    turn_bundle = user_turn_input.build_user_turn_bundle(
        user_message=current_message,
        recent_window_input_payload=window_payload,
        time_input_payload=time_payload,
    )
    matter = dict(case.get("matter") or {})
    memory_payload = memory_retrieved_input.build_memory_retrieved_input(
        retrieval_query="synthetic-query",
        top_k_requested=1,
        traces=([{"role": "assistant", "content": "synthetic-memory"}] if matter.get("memory") else []),
        status="ok",
        reason_code=None,
    )
    arbitration_payload = memory_arbitration_input.build_memory_arbitration_input(
        memory_retrieved=memory_payload,
        raw_candidates_count=int(bool(matter.get("memory"))),
        decisions=[],
        status="available" if matter.get("memory") else "skipped",
        reason_code=None if matter.get("memory") else "no_data",
    )
    summary_payload = summary_input.build_summary_input(
        active_summary=(
            {
                "id": "synthetic-summary",
                "conversation_id": "synthetic-conversation",
                "start_ts": "2026-08-29T08:00:00Z",
                "end_ts": "2026-08-29T09:00:00Z",
                "content": "synthetic-summary-content",
            }
            if matter.get("summary")
            else None
        ),
        conversation_id="synthetic-conversation",
    )
    identity_payload = identity_input.build_identity_input(
        frida_static_content="synthetic-frida" if matter.get("identity") else "",
        user_static_content="synthetic-user" if matter.get("identity") else "",
    )
    return {
        "time_input": time_payload,
        "memory_retrieved": memory_payload,
        "memory_arbitration": arbitration_payload,
        "summary_input": summary_payload,
        "identity_input": identity_payload,
        "recent_context_input": recent_payload,
        "recent_window_input": window_payload,
        "user_turn_input": turn_bundle["user_turn"],
        "user_turn_signals": turn_bundle["user_turn_signals"],
        "stimmung_input": _stimmung(str(case.get("stimmung") or "absent")),
        "web_input": _web(str(matter.get("web") or "absent")),
    }


def _dialogue_context(case: Mapping[str, Any]) -> dict[str, Any]:
    return recent_context_input.build_validation_dialogue_context(
        messages=[dict(item) for item in case.get("dialogue") or []],
        summary_input_payload=None,
    )


def build_current_messages(case: Mapping[str, Any], system_prompt: str) -> dict[str, Any]:
    canonical_inputs = build_case_inputs(case)
    primary = _primary_verdict(case)
    guard = hard_guards.evaluate_hard_guards(
        primary_verdict=primary,
        canonical_inputs=canonical_inputs,
    )
    messages, metadata = validation_messages.build_messages_with_projection(
        system_prompt=system_prompt,
        primary_verdict=primary,
        justifications={"basis": "synthetic"},
        validation_dialogue_context=_dialogue_context(case),
        canonical_inputs=canonical_inputs,
        hard_guard_payload=guard.prompt_payload(),
    )
    return {
        "canonical_inputs": canonical_inputs,
        "primary_verdict": primary,
        "hard_guard": guard.prompt_payload(),
        "messages": messages,
        "projection_metadata": metadata,
    }


def _canonical_material_from_user_message(user_content: str) -> str:
    if user_content.count(CANONICAL_MARKER) != 1:
        raise ValueError("invalid_canonical_message_marker")
    suffix = user_content.split(CANONICAL_MARKER, 1)[1]
    return suffix.split("\n\n", 1)[0]


def messages_with_canonical_material(
    messages: Sequence[Mapping[str, str]],
    *,
    expected_current_material: str,
    replacement_material: str,
) -> list[dict[str, str]]:
    copied = [dict(message) for message in messages]
    if len(copied) != 2:
        raise ValueError("invalid_validation_message_count")
    current = _canonical_material_from_user_message(copied[1]["content"])
    if current != expected_current_material:
        raise ValueError("canonical_material_mismatch")
    copied[1]["content"] = copied[1]["content"].replace(
        f"{CANONICAL_MARKER}{current}\n\n",
        f"{CANONICAL_MARKER}{replacement_material}\n\n",
        1,
    )
    return copied


def pair_fingerprints(messages_by_projection: Mapping[str, Sequence[Mapping[str, str]]]) -> dict[str, str]:
    normalized: dict[str, str] = {}
    canonical: dict[str, str] = {}
    system: dict[str, str] = {}
    for version, messages in messages_by_projection.items():
        system[version] = _sha256_text(str(messages[0]["content"]))
        user = str(messages[1]["content"])
        material = _canonical_material_from_user_message(user)
        canonical[version] = _sha256_text(material)
        normalized[version] = _sha256_text(user.replace(material, "<CANONICAL_INPUTS>", 1))
    if len(set(system.values())) != 1 or len(set(normalized.values())) != 1:
        raise ValueError("comparison_changes_noncanonical_material")
    if len(set(canonical.values())) != len(canonical):
        raise ValueError("comparison_does_not_change_canonical_material")
    return {
        "system_sha256": next(iter(system.values())),
        "noncanonical_user_sha256": next(iter(normalized.values())),
        "v1_canonical_sha256": canonical["v1"],
        "v2_canonical_sha256": canonical["v2"],
    }


def historical_projection(
    canonical_inputs: Mapping[str, Any],
    *,
    historical_app_root: Path,
) -> tuple[str, dict[str, Any]]:
    projector_path = historical_app_root / "core/hermeneutic_node/validation/validation_canonical_projection.py"
    if hashlib.sha256(projector_path.read_bytes()).hexdigest() != HISTORICAL_PROJECTOR_SHA256:
        raise ValueError("historical_projector_hash_mismatch")
    driver = (
        "import json,sys;"
        "from core.hermeneutic_node.validation.validation_canonical_projection "
        "import project_validation_canonical_inputs as p;"
        "m,d=p(json.load(sys.stdin));"
        "json.dump({'material':m,'metadata':d},sys.stdout,ensure_ascii=False,separators=(',',':'))"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = str(historical_app_root)
    completed = subprocess.run(
        [sys.executable, "-c", driver],
        input=json.dumps(canonical_inputs, ensure_ascii=False),
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    payload = json.loads(completed.stdout)
    metadata = dict(payload["metadata"])
    if metadata.get("canonical_projection_version") != HISTORICAL_PROJECTION_VERSION:
        raise ValueError("historical_projection_version_mismatch")
    return str(payload["material"]), metadata


def protocol_document(corpus: Mapping[str, Any], *, phase1_commit: str) -> dict[str, Any]:
    maxima = measured_v2_maxima()
    if maxima["accepted_contract_chars"] != EXPECTED_ACCEPTED_V2_MAX_CHARS:
        raise ValueError("accepted_v2_maximum_changed")
    if maxima["runtime_emittable_chars"] != EXPECTED_RUNTIME_EMITTABLE_V2_MAX_CHARS:
        raise ValueError("runtime_emittable_v2_maximum_changed")
    if PLANNED_PROVIDER_CALLS > ABSOLUTE_PROVIDER_CALL_CAP:
        raise ValueError("provider_call_cap_exceeded")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "corpus_id": corpus["corpus_id"],
        "corpus_sha256": corpus_sha256(corpus),
        "historical_commit": HISTORICAL_COMMIT,
        "historical_projection_version": HISTORICAL_PROJECTION_VERSION,
        "current_phase1_commit": phase1_commit,
        "current_projection_version": CURRENT_PROJECTION_VERSION,
        "models": [
            {"source": source, "model": model}
            for model, source in MODEL_ROLES.items()
        ],
        "generation": {
            "temperature": TEMPERATURE,
            "top_p": TOP_P,
            "max_tokens": MAX_TOKENS,
            "timeout_s": TIMEOUT_S,
            "reasoning_effort": REASONING_EFFORT,
        },
        "case_count": CASE_COUNT,
        "repetitions": REPETITIONS,
        "projection_count": PROJECTION_COUNT,
        "planned_provider_calls": PLANNED_PROVIDER_CALLS,
        "absolute_provider_call_cap": ABSOLUTE_PROVIDER_CALL_CAP,
        "max_estimated_cost_usd": MAX_ESTIMATED_COST_USD,
        "decision_rule": {
            "minimum_valid_paired_repetitions_per_case_model": 1,
            "fail_on_new_v2_regression": True,
            "fail_on_v2_critical_invariant": True,
            "fallback_preexisting_presence_gap_requires_v1_v2_equivalence": True,
            "inconclusive_on_missing_valid_pair": True,
            "thresholds_mutable_after_provider_results": False,
        },
        "v2_maxima": maxima,
    }


def score_parsed_output(
    case: Mapping[str, Any],
    raw_text: str,
    *,
    hard_guard_payload: Mapping[str, Any],
) -> dict[str, Any]:
    status = "ok"
    try:
        parsed = validation_contract.safe_json_loads(raw_text)
    except Exception:
        parsed = None
        status = "invalid_json"
    verdict: dict[str, str] | None = None
    if parsed is not None:
        try:
            verdict = validation_contract.validate_model_verdict(
                parsed,
                allowed_postures=validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES,
            )
        except Exception:
            status = "invalid_schema"
    expected = dict(case.get("expected") or {})
    posture = verdict.get("final_judgment_posture") if verdict else None
    regime = verdict.get("final_output_regime") if verdict else None
    allowed_pairs = {tuple(pair) for pair in expected.get("allowed_pairs") or []}
    hard_guard_violation = (
        hard_guard_payload.get("hard_guard_effect") == "answer_forbidden" and posture == "answer"
    )
    presence_policy = str(expected.get("presence_policy") or "allowed")
    false_presence = regime == "presence" and presence_policy == "forbidden"
    missed_presence = presence_policy == "required" and regime != "presence"
    semantic_codes = []
    if verdict and (posture, regime) not in allowed_pairs:
        semantic_codes.append("pair_not_allowed")
    if hard_guard_violation:
        semantic_codes.append("hard_guard_violation")
    if false_presence:
        semantic_codes.append("false_presence")
    if missed_presence:
        semantic_codes.append("missed_presence")
    passed = status == "ok" and not semantic_codes
    return {
        "status": status,
        "reason_code": "accepted" if passed else (semantic_codes[0] if semantic_codes else status),
        "final_judgment_posture": posture,
        "final_output_regime": regime,
        "pass": passed,
        "semantic_codes": semantic_codes,
        "hard_guard_violation": hard_guard_violation,
        "false_presence": false_presence,
        "missed_presence": missed_presence,
    }


def compare_pair(
    *,
    case: Mapping[str, Any],
    source: str,
    v1_score: Mapping[str, Any],
    v2_score: Mapping[str, Any],
) -> dict[str, Any]:
    if v1_score.get("status") != "ok" or v2_score.get("status") != "ok":
        return {"classification": "provider_invalid_pair", "divergence_codes": []}
    v1_pair = (v1_score.get("final_judgment_posture"), v1_score.get("final_output_regime"))
    v2_pair = (v2_score.get("final_judgment_posture"), v2_score.get("final_output_regime"))
    codes: list[str] = []
    if v1_pair != v2_pair:
        codes.append("allowed_semantic_pair_divergence")
    if v1_score.get("pass") and not v2_score.get("pass"):
        codes.append("v2_regression")
        return {"classification": "fail", "divergence_codes": codes}
    if not v1_score.get("pass") and v2_score.get("pass"):
        codes.append("v2_corrects_v1_blindness")
        return {"classification": "pass", "divergence_codes": codes}
    if v2_score.get("pass"):
        return {"classification": "pass", "divergence_codes": codes}
    accepted_gap = str((case.get("expected") or {}).get("fallback_preexisting_gap") or "")
    same_codes = list(v1_score.get("semantic_codes") or []) == list(v2_score.get("semantic_codes") or [])
    if source == "fallback" and accepted_gap and same_codes and accepted_gap in v2_score.get("semantic_codes", []):
        return {
            "classification": "accepted_preexisting_fallback_gap",
            "divergence_codes": ["preexisting_fallback_presence_gap"],
        }
    return {"classification": "fail", "divergence_codes": ["v2_critical_invariant_failed"]}


def campaign_decision(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    comparisons = [record for record in records if record.get("record_type") == "pair_comparison"]
    groups: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in comparisons:
        groups.setdefault((str(record["case_id"]), str(record["source"])), []).append(record)
    expected_groups = CASE_COUNT * len(MODEL_ROLES)
    if len(groups) != expected_groups:
        return {"decision": "inconclusive", "reason_code": "missing_case_model_group"}
    def classification(record: Mapping[str, Any]) -> str:
        return str(record.get("classification") or record.get("status") or "")

    if any(classification(record) == "fail" for record in comparisons):
        return {"decision": "fail", "reason_code": "semantic_regression_or_critical_failure"}
    if any(
        not any(classification(record) != "provider_invalid_pair" for record in group)
        for group in groups.values()
    ):
        return {"decision": "inconclusive", "reason_code": "insufficient_valid_paired_results"}
    return {"decision": "pass", "reason_code": "no_v2_semantic_regression"}


def _provider_status(provider: Mapping[str, Any]) -> tuple[str, str]:
    if provider.get("ok"):
        if not str(provider.get("raw_text") or "").strip():
            return "empty_output", "empty_output"
        return "ok", "provider_ok"
    text = str(provider.get("error") or "").lower()
    if "timeout" in text:
        return "timeout", "timeout"
    if provider.get("status_code") in {401, 403}:
        return "refusal", "provider_refusal"
    return "transport_error", "transport_error"


def run_live_campaign(
    *,
    historical_app_root: Path,
    output_path: Path,
    phase1_commit: str,
    client: OpenRouterClient,
) -> dict[str, Any]:
    corpus = load_corpus()
    protocol = protocol_document(corpus, phase1_commit=phase1_commit)
    system_prompt = (REPO_ROOT / "app/prompts/validation_agent.txt").read_text(encoding="utf-8").strip()
    records: list[dict[str, Any]] = []
    call_count = 0
    for case in corpus["cases"]:
        built = build_current_messages(case, system_prompt)
        v2_messages = [dict(item) for item in built["messages"]]
        v2_material = _canonical_material_from_user_message(v2_messages[1]["content"])
        v1_material, _v1_metadata = historical_projection(
            built["canonical_inputs"],
            historical_app_root=historical_app_root,
        )
        v1_messages = messages_with_canonical_material(
            v2_messages,
            expected_current_material=v2_material,
            replacement_material=v1_material,
        )
        fingerprints = pair_fingerprints({"v1": v1_messages, "v2": v2_messages})
        for model, source in MODEL_ROLES.items():
            for repetition in range(1, REPETITIONS + 1):
                scored: dict[str, dict[str, Any]] = {}
                message_pairs = {"v1": v1_messages, "v2": v2_messages}
                projection_order = ("v1", "v2") if repetition % 2 else ("v2", "v1")
                for projection in projection_order:
                    messages = message_pairs[projection]
                    call_count += 1
                    if call_count > ABSOLUTE_PROVIDER_CALL_CAP:
                        raise ValueError("provider_call_cap_exceeded")
                    provider = client.chat_completion(
                        {
                            "model": model,
                            "messages": messages,
                            "temperature": TEMPERATURE,
                            "top_p": TOP_P,
                            "max_tokens": MAX_TOKENS,
                        },
                        caller="validation_agent",
                        timeout_s=TIMEOUT_S,
                    )
                    provider_status, provider_reason = _provider_status(provider)
                    if provider_status == "ok":
                        score = score_parsed_output(
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
                    scored[projection] = score
                    usage = dict(provider.get("usage") or {})
                    records.append(
                        {
                            "record_type": "provider_call",
                            "protocol_version": PROTOCOL_VERSION,
                            "corpus_id": corpus["corpus_id"],
                            "corpus_sha256": protocol["corpus_sha256"],
                            "case_id": case["id"],
                            "projection": projection,
                            "source_commit": HISTORICAL_COMMIT if projection == "v1" else phase1_commit,
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
                            "system_sha256": fingerprints["system_sha256"],
                            "noncanonical_user_sha256": fingerprints["noncanonical_user_sha256"],
                            "canonical_sha256": fingerprints[f"{projection}_canonical_sha256"],
                        }
                    )
                comparison = compare_pair(
                    case=case,
                    source=source,
                    v1_score=scored["v1"],
                    v2_score=scored["v2"],
                )
                records.append(
                    {
                        "record_type": "pair_comparison",
                        "protocol_version": PROTOCOL_VERSION,
                        "corpus_id": corpus["corpus_id"],
                        "corpus_sha256": protocol["corpus_sha256"],
                        "case_id": case["id"],
                        "projection": "v1_vs_v2",
                        "source_commit": phase1_commit,
                        "source": source,
                        "model": model,
                        "observed_model": "",
                        "observed_provider": "",
                        "generation": protocol["generation"],
                        "repetition": repetition,
                        "status": comparison["classification"],
                        "reason_code": comparison["classification"],
                        "final_judgment_posture": None,
                        "final_output_regime": None,
                        "scorer_pass": comparison["classification"] in {"pass", "accepted_preexisting_fallback_gap"},
                        "divergence_codes": comparison["divergence_codes"],
                        "latency_ms": None,
                        "prompt_tokens": None,
                        "completion_tokens": None,
                        "total_tokens": None,
                        "cost_usd": None,
                        "system_sha256": fingerprints["system_sha256"],
                        "noncanonical_user_sha256": fingerprints["noncanonical_user_sha256"],
                        "canonical_sha256": "",
                    }
                )
    if call_count != PLANNED_PROVIDER_CALLS:
        raise ValueError("unexpected_provider_call_count")
    decision = campaign_decision(records)
    records.append(
        {
            "record_type": "campaign_summary",
            "protocol_version": PROTOCOL_VERSION,
            "corpus_id": corpus["corpus_id"],
            "corpus_sha256": protocol["corpus_sha256"],
            "case_id": "campaign",
            "projection": "v1_vs_v2",
            "source_commit": phase1_commit,
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
            "completion_tokens": sum(int(record.get("completion_tokens") or 0) for record in records),
            "total_tokens": sum(int(record.get("total_tokens") or 0) for record in records),
            "cost_usd": round(sum(float(record.get("cost_usd") or 0) for record in records), 8),
            "system_sha256": "",
            "noncanonical_user_sha256": "",
            "canonical_sha256": "",
        }
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validated_records = [validate_content_free_record(record) for record in records]
    output_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
            for record in validated_records
        ),
        encoding="utf-8",
    )
    return {"decision": decision, "records": validated_records, "protocol": protocol}


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--historical-app-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--phase1-commit", required=True)
    args = parser.parse_args()
    api_key = os.environ.get("OPENROUTER_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is required for the live comparison")
    base_url = (os.environ.get("OPENROUTER_BASE") or "https://openrouter.ai/api/v1").rstrip("/")
    client = OpenRouterClient(
        OpenRouterConfig(
            base_url=base_url,
            api_key=api_key,
            referer=os.environ.get("OPENROUTER_REFERER", "").strip(),
            title="FridaDev/ValidationAgent",
        )
    )
    result = run_live_campaign(
        historical_app_root=args.historical_app_root,
        output_path=args.output,
        phase1_commit=args.phase1_commit,
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
