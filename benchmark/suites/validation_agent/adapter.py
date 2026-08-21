"""Payload adapter for the validation_agent benchmark suite."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[3]
APP_ROOT = REPO_ROOT / "app"
if str(APP_ROOT) in sys.path:
    sys.path.remove(str(APP_ROOT))
sys.path.insert(0, str(APP_ROOT))

from core.hermeneutic_node.validation import hard_guards as runtime_hard_guards
from core.hermeneutic_node.validation import validation_contract
from core.hermeneutic_node.validation import validation_messages
from core.hermeneutic_node.inputs import recent_context_input

PROMPT_PATH = Path("app/prompts/validation_agent.txt")
FIXTURE_PATH = Path("benchmark/suites/validation_agent/fixtures/validation_agent_primary_cases.json")
PRESENCE_FIXTURE_PATH = Path(
    "benchmark/suites/validation_agent/fixtures/validation_agent_presence_cases.json"
)
DIALOGIC_REGIME_CORPUS_PATH = Path("app/tests/support/dialogic_regime_corpus.json")

TEMPERATURE = 0.0
TOP_P = 1.0
MAX_TOKENS = 140
TIMEOUT_S = 15
REASONING_EFFORTS = frozenset({"none", "low", "medium", "high", "xhigh", "max"})

ALLOWED_POSTURES = set(validation_contract.ALLOWED_PRIMARY_JUDGMENT_POSTURES)
ALLOWED_OUTPUT_REGIMES = set(validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES)


def load_prompt(path: Path = PROMPT_PATH) -> str:
    return path.read_text(encoding="utf-8")


def load_fixtures(path: Path = FIXTURE_PATH) -> list[dict[str, Any]]:
    return load_fixture_document(path)["cases"]


def load_fixture_document(path: Path = FIXTURE_PATH) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("validation_agent fixture file must contain an object")
    cases = payload.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("validation_agent fixture file must contain a non-empty cases list")
    resolved_cases = _resolve_dialogue_references(cases, fixture_path=path)
    for case in resolved_cases:
        validate_fixture(case)
    result = dict(payload)
    result["cases"] = resolved_cases
    if payload.get("schema_version") == "validation_presence_corpus_v1":
        _validate_presence_document(result)
    return result


def _resolve_dialogue_references(
    cases: list[dict[str, Any]],
    *,
    fixture_path: Path,
) -> list[dict[str, Any]]:
    if not any(isinstance(case, dict) and case.get("dialogue_ref") for case in cases):
        return [dict(case) for case in cases]
    repo_root = _repo_root_for(fixture_path)
    shared_payload = json.loads((repo_root / DIALOGIC_REGIME_CORPUS_PATH).read_text(encoding="utf-8"))
    shared_cases = {
        str(case.get("id") or ""): list(case.get("messages") or [])
        for case in shared_payload.get("cases") or []
        if isinstance(case, dict)
    }
    resolved: list[dict[str, Any]] = []
    for raw_case in cases:
        case = dict(raw_case)
        reference = str(case.get("dialogue_ref") or "").strip()
        if reference:
            if reference not in shared_cases:
                raise ValueError(f"fixture {case.get('id', '<unknown>')} unknown dialogue_ref: {reference}")
            if case.get("dialogue"):
                raise ValueError(f"fixture {case.get('id', '<unknown>')} duplicates dialogue and dialogue_ref")
            case["dialogue"] = [dict(item) for item in shared_cases[reference]]
        resolved.append(case)
    return resolved


def _repo_root_for(path: Path) -> Path:
    for parent in path.resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise ValueError("unable to resolve repository root for validation_agent fixtures")


def _validate_presence_document(payload: dict[str, Any]) -> None:
    if payload.get("human_validation_status") not in {"pending", "validated", "rejected"}:
        raise ValueError("presence corpus must expose a bounded human_validation_status")
    if payload.get("human_validation_status") == "validated":
        if not str(payload.get("human_validation_date") or "").strip():
            raise ValueError("validated presence corpus must expose human_validation_date")
        if payload.get("human_validation_basis") != "operator_accepted_fixture_without_changes":
            raise ValueError("validated presence corpus must expose the bounded validation basis")
        observed_fingerprint = str(payload.get("validated_contract_sha256") or "").strip()
        expected_fingerprint = presence_contract_sha256(payload)
        if observed_fingerprint != expected_fingerprint:
            raise ValueError("validated presence corpus fingerprint mismatch")
    thresholds = payload.get("proposed_safety_thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError("presence corpus must expose proposed safety thresholds")
    boundary_cases = payload.get("runtime_boundary_cases")
    if not isinstance(boundary_cases, list) or not boundary_cases:
        raise ValueError("presence corpus must expose runtime boundary cases")
    seen_ids: set[str] = set()
    for item in [*(payload.get("cases") or []), *boundary_cases]:
        if not isinstance(item, dict):
            raise ValueError("presence corpus entries must be objects")
        case_id = str(item.get("id") or "").strip()
        if not case_id or case_id in seen_ids:
            raise ValueError("presence corpus IDs must be non-empty and unique")
        seen_ids.add(case_id)
        for key in (
            "semantic_family",
            "false_presence_severity",
            "human_justification",
            "synthetic_provenance_tags",
        ):
            if not item.get(key):
                raise ValueError(f"presence corpus {case_id} missing {key}")
        if item.get("false_presence_severity") not in {"low", "medium", "high", "critical"}:
            raise ValueError(f"presence corpus {case_id} invalid false_presence_severity")
        tags = item.get("synthetic_provenance_tags")
        if not isinstance(tags, list) or "synthetic" not in tags:
            raise ValueError(f"presence corpus {case_id} must be explicitly synthetic")
    for case in payload.get("cases") or []:
        policy = (case.get("expected") or {}).get("presence_policy")
        if policy not in {"required", "allowed", "forbidden"}:
            raise ValueError(f"presence corpus {case.get('id')} invalid presence_policy")


def validate_fixture(case: dict[str, Any]) -> None:
    required = {
        "id",
        "origin",
        "source_reference",
        "design_note",
        "dialogue",
        "primary",
        "canonical",
        "expected",
    }
    missing = sorted(required - set(case))
    if missing:
        raise ValueError(f"fixture {case.get('id', '<unknown>')} missing keys: {missing}")
    if not isinstance(case["dialogue"], list) or not case["dialogue"]:
        raise ValueError(f"fixture {case['id']} dialogue must be a non-empty list")

    expected = case["expected"]
    posture = expected.get("final_judgment_posture")
    regime = expected.get("final_output_regime")
    if posture not in ALLOWED_POSTURES:
        raise ValueError(f"fixture {case['id']} invalid expected posture: {posture}")
    if regime not in ALLOWED_OUTPUT_REGIMES:
        raise ValueError(f"fixture {case['id']} invalid expected output regime: {regime}")


def build_payload(
    case: dict[str, Any],
    model: str,
    prompt: str | None = None,
    *,
    generation_settings: dict[str, Any] | None = None,
    reasoning_effort: str | None = None,
) -> dict[str, Any]:
    prompt_text = prompt if prompt is not None else load_prompt()
    settings = generation_settings or generation_params()
    messages = build_messages(case, prompt_text)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": settings["temperature"],
        "top_p": settings["top_p"],
        "max_tokens": settings["max_tokens"],
    }
    if reasoning_effort is not None:
        normalized_effort = str(reasoning_effort).strip().lower()
        if normalized_effort not in REASONING_EFFORTS:
            raise ValueError(f"unsupported validation_agent reasoning effort: {reasoning_effort}")
        payload["reasoning"] = {"effort": normalized_effort, "exclude": True}
    return payload


def build_messages(case: dict[str, Any], prompt_text: str) -> list[dict[str, str]]:
    primary_verdict = build_primary_verdict(case)
    canonical_inputs = build_canonical_inputs(case)
    hard_guards = evaluate_hard_guards(primary_verdict, canonical_inputs)
    return validation_messages.build_messages(
        system_prompt=prompt_text,
        primary_verdict=primary_verdict,
        justifications=case.get("justifications") or {},
        validation_dialogue_context=build_validation_dialogue_context(case),
        canonical_inputs=canonical_inputs,
        hard_guard_payload=hard_guards,
    )


def build_user_content(case: dict[str, Any]) -> str:
    return build_messages(case, load_prompt())[1]["content"]


def build_validation_dialogue_context(case: dict[str, Any]) -> dict[str, Any]:
    messages = []
    for item in case["dialogue"]:
        messages.append(
            {
                "role": item["role"],
                "content": item["content"],
                **({"temporal_label": item["temporal_label"]} if item.get("temporal_label") else {}),
            }
        )
    return recent_context_input.build_validation_dialogue_context(
        messages=messages,
        summary_input_payload=None,
        max_messages=validation_contract.MAX_VALIDATION_CONTEXT_MESSAGES,
    )


def build_primary_verdict(case: dict[str, Any]) -> dict[str, Any]:
    primary = case["primary"]
    posture = primary["judgment_posture"]
    regime = primary["discursive_regime"]
    return {
        "schema_version": "v1",
        "system_state": primary.get("system_state", "ok"),
        "epistemic_regime": primary.get("epistemic_regime", "answerable"),
        "epistemic_regime_reason": primary.get("epistemic_regime_reason", "fixture"),
        "judgment_posture": posture,
        "judgment_posture_reason": primary.get("judgment_posture_reason", "fixture"),
        "discursive_regime": regime,
        "discursive_regime_reason": primary.get("discursive_regime_reason", "fixture"),
        "proof_regime": primary.get("proof_regime", "internal"),
        "proof_regime_reason": primary.get("proof_regime_reason", "fixture"),
        "uncertainty_posture": primary.get("uncertainty_posture", "normal"),
        "uncertainty_posture_reason": primary.get("uncertainty_posture_reason", "fixture"),
        "source_priority": primary.get(
            "source_priority",
            ["tour_utilisateur", "temps", "memoire/contexte_recent/identity", "resume", "web", "stimmung"],
        ),
        "source_conflicts": primary.get("source_conflicts", []),
        "active_signal_families": primary.get("active_signal_families", []),
        "dialogue_phase": primary.get("dialogue_phase", "continuation"),
    }


def build_canonical_inputs(case: dict[str, Any]) -> dict[str, Any]:
    canonical = case["canonical"]
    return {
        "time_input": canonical.get(
            "time_input",
            {
                "now_utc_iso": "2026-05-18T14:48:27Z",
                "timezone": "Europe/Paris",
                "now_local_iso": "2026-05-18T16:48:27+02:00",
                "local_date": "2026-05-18",
                "local_time": "16:48:27",
            },
        ),
        "user_turn_input": {
            "content": canonical.get("current_user_message", ""),
            "speaker": "user",
        },
        "user_turn_signals": canonical.get(
            "user_turn_signals",
            {
                "qualified_turn": canonical.get("qualified_turn", "question"),
                "ambiguity_present": canonical.get("ambiguity_present", False),
                "explicit_external_reference": canonical.get("explicit_external_reference", False),
                "temporal_signal": canonical.get("temporal_signal", "none"),
            },
        ),
        "recent_context_input": canonical.get("recent_context_input", {"available": True, "turns_count": 2}),
        "recent_window_input": canonical.get("recent_window_input", {"available": True}),
        "memory_retrieved": canonical.get("memory_retrieved", {"items_count": 0}),
        "memory_arbitration": canonical.get("memory_arbitration", {"kept_count": 0, "dropped_count": 0}),
        "summary_input": canonical.get("summary_input", {"available": False}),
        "identity_input": canonical.get("identity_input", {"available": False}),
        "stimmung_input": canonical.get("stimmung_input", {"available": True, "dominant_tone": "neutral"}),
        "web_input": canonical.get("web_input", {"mode": "none", "materially_used": False}),
    }


def evaluate_hard_guards(
    primary_verdict: dict[str, Any], canonical_inputs: dict[str, Any]
) -> dict[str, Any]:
    decision = runtime_hard_guards.evaluate_hard_guards(
        primary_verdict=primary_verdict,
        canonical_inputs=canonical_inputs,
    )
    return decision.prompt_payload()


def dry_run_response(case: dict[str, Any]) -> str:
    expected = case["expected"]
    payload = {
        "schema_version": "v1",
        "final_judgment_posture": expected["final_judgment_posture"],
        "final_output_regime": expected["final_output_regime"],
        "arbiter_reason": "dry-run expected fixture decision",
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def presence_contract_sha256(payload: dict[str, Any]) -> str:
    contract = {
        "cases": payload.get("cases") or [],
        "runtime_boundary_cases": payload.get("runtime_boundary_cases") or [],
        "proposed_safety_thresholds": payload.get("proposed_safety_thresholds") or {},
    }
    encoded = json.dumps(
        contract,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def generation_params(
    *,
    max_tokens: int | None = None,
    timeout_s: int | None = None,
) -> dict[str, Any]:
    resolved_max_tokens = MAX_TOKENS if max_tokens is None else int(max_tokens)
    resolved_timeout_s = TIMEOUT_S if timeout_s is None else int(timeout_s)
    if resolved_max_tokens <= 0:
        raise ValueError("validation_agent max_tokens must be positive")
    if resolved_timeout_s <= 0:
        raise ValueError("validation_agent timeout_s must be positive")
    return {
        "temperature": TEMPERATURE,
        "top_p": TOP_P,
        "max_tokens": resolved_max_tokens,
        "timeout_s": resolved_timeout_s,
    }
