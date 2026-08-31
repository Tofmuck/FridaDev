from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

import config
from core import chat_prompt_context
from core import continuity_capsule
from core import prompt_loader
from core import token_utils


CORPUS_SCHEMA_VERSION = "stimmung_final_wording_corpus_v1"
THRESHOLD_SCHEMA_VERSION = "stimmung_final_wording_thresholds_v1"
PROTOCOL_VERSION = "lot4c4_final_wording_provider_campaign_v1"
ARTIFACT_VERSION = "lot4c4_final_wording_provider_results_v1"
DEFAULT_FIXTURE = "stimmung_final_wording_corpus_v1.json"
DEFAULT_FREEZE_MANIFEST = "stimmung_final_wording_freeze_v1.json"

ACTIVE_MAIN_MODEL = "openai/gpt-5.1"
ACTIVE_TEMPERATURE = 0.7
ACTIVE_TOP_P = 1.0
ACTIVE_MAX_TOKENS = 8192
ACTIVE_REASONING = {"effort": "high", "exclude": True}
ACTIVE_TIMEOUT_S = 900
REPETITIONS = 2
REPETITION_RATIONALE = (
    "minimum_repeat_to_expose_single_decode_variance_within_48_call_cap"
)
EXPECTED_CASES = 14
EXPECTED_PROVIDER_CASES = 12
EXPECTED_PAIRS = EXPECTED_PROVIDER_CASES * REPETITIONS
EXPECTED_CALLS = EXPECTED_PAIRS * 2
ABSOLUTE_CALL_CAP = EXPECTED_CALLS
ABSOLUTE_COST_CAP_USD = 5.0
PRICING_OBSERVED_AT = "2026-08-31"
PRICING_SOURCE = "https://openrouter.ai/openai/gpt-5.1"
PRICING_USD_PER_TOKEN = {"prompt": 0.00000125, "completion": 0.00001}
COST_MARGIN = 1.10
FIXED_NOW_ISO = "2026-08-31T12:00:00Z"
BASELINE_HEAD = "d208d3e300bacfcb836d71e5adb8001384b32776"

REQUIRED_FAMILIES = (
    "delicacy_expected",
    "counter_no_extra_caution",
    "irony",
    "quoted_affect",
    "reported_affect",
    "question",
    "request",
    "risk",
    "material_action",
    "counter_presence",
    "presence_eligible",
    "hard_guard",
    "certainty_unchanged",
    "evidence_unchanged",
    "stable_noop",
    "fail_open_unknown",
)
FINAL_TEXT_PROPERTIES = (
    "justified_delicacy_effect",
    "formulation_fit",
    "no_psychologization",
    "no_certainty_change",
    "no_truth_or_evidence_change",
    "unmasked_question_request_risk_or_action",
    "no_delicacy_overapplication",
)
OTHER_STAGE_PROPERTIES = (
    "presence_decision",
    "main_model_call_authorization",
)
CONTRACT_ONLY_PROPERTIES = (
    "identical_dialogic_and_epistemic_matter",
    "hard_guards_unchanged",
    "raw_stimmung_absent",
    "single_terminal_continuity_capsule",
    "main_payload_manifest_coherent",
    "assistant_persistence_and_provenance",
    "json_stream_equivalence",
)
ENUNCIATION_STATES = (
    "not_applicable",
    "stable_noop",
    "transition_delicate",
    "fail_open_unknown",
)
REQUIRED_MUTATIONS = frozenset(
    {
        "directive_removed",
        "directive_duplicated",
        "raw_stimmung_injected",
        "epistemic_change_attributed_to_stimmung",
        "final_lock_bypassed",
        "continuity_capsule_removed",
        "continuity_capsule_moved",
        "continuity_capsule_duplicated",
        "manifest_incoherent",
        "fake_semantic_result_fabricated",
    }
)

_TOP_KEYS = {
    "schema_version",
    "corpus_id",
    "language",
    "pairing_contract",
    "measurement_taxonomy",
    "thresholds",
    "cases",
    "mutation_matrix",
}
_CASE_KEYS = {
    "id",
    "version",
    "families",
    "enunciation_state",
    "provider_eligible",
    "dialogue",
    "epistemic_matter",
    "expectations",
}
_DIALOGUE_KEYS = {"history", "user"}
_EPISTEMIC_KEYS = {
    "epistemic_regime",
    "proof_regime",
    "uncertainty_posture",
    "factual_basis",
}
_EXPECTATION_KEYS = {"final_text", "other_stage", "contract_only"}
_FINAL_TEXT_EXPECTATION_KEYS = {
    "delicacy_effect",
    "formulation_fit",
    "psychologization",
    "certainty_change",
    "truth_or_evidence_change",
    "masked_targets",
    "overapplication",
}
_OTHER_STAGE_EXPECTATION_KEYS = {"presence_relation", "main_model_call"}
_CONTRACT_EXPECTATION_KEYS = {
    "identical_matter",
    "hard_guards_unchanged",
    "raw_stimmung_absent",
}
_OBSERVATION_KEYS = {
    "case_id",
    "repetition",
    "source_kind",
    "call_attempts_complete",
    "responses_complete",
    "control_response_sha256",
    "treatment_response_sha256",
    "delicacy_effect",
    "formulation_fit",
    "psychologization",
    "certainty_change",
    "truth_or_evidence_change",
    "masked_targets",
    "presence_regression",
    "overapplication",
}
_RAW_STIMMUNG_MARKERS = (
    "stimmung_input",
    "active_tones",
    "dominant_tone",
    "turns_considered",
    "shift_state",
)
_ENUNCIATION_PREFIXES = (
    "Effet d'enonciation:",
    "Consigne d'enonciation:",
)
_CAPSULE_HEADER = "[CONTINUITY CAPSULE]"
_HEX = frozenset("0123456789abcdef")


class _EmptyIdentity:
    @staticmethod
    def build_identity_block() -> tuple[str, list[str]]:
        return "", []


def _compact_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_sha256(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 64 and all(char in _HEX for char in text)


def _is_commit(value: Any) -> bool:
    text = str(value or "")
    return len(text) == 40 and all(char in _HEX for char in text)


def _exact_keys(value: Any, expected: set[str], reason: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(reason)
    return value


def _bounded_text(value: Any, *, minimum: int = 1, maximum: int = 1200) -> str:
    text = str(value or "").strip()
    if not minimum <= len(text) <= maximum:
        raise ValueError("bounded_text_invalid")
    return text


def _fixture_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures" / DEFAULT_FIXTURE


def _harness_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/final_wording_diagnostic.py"


def _freeze_manifest_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures" / DEFAULT_FREEZE_MANIFEST


def load_corpus(repo_root: Path) -> dict[str, Any]:
    payload = json.loads(_fixture_path(repo_root).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("corpus_root_not_object")
    validate_corpus(payload)
    return payload


def validate_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(corpus, _TOP_KEYS, "corpus_fields_invalid")
    if corpus.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("corpus_schema_invalid")
    if corpus.get("corpus_id") != "lot4c4-final-wording-fr-v1":
        raise ValueError("corpus_id_invalid")
    if corpus.get("language") != "fr":
        raise ValueError("corpus_language_invalid")
    if corpus.get("pairing_contract") != {
        "control": "same_matter_without_applicable_dialogic_effect",
        "treatment": "same_matter_with_current_derived_enunciation_directive",
        "only_allowed_difference": "bounded_enunciation_directive",
        "exact_output_expected": False,
    }:
        raise ValueError("pairing_contract_invalid")

    taxonomy = _exact_keys(
        corpus.get("measurement_taxonomy"),
        {"final_text", "other_stage", "contract_only"},
        "measurement_taxonomy_invalid",
    )
    expected_taxonomy = {
        "final_text": list(FINAL_TEXT_PROPERTIES),
        "other_stage": list(OTHER_STAGE_PROPERTIES),
        "contract_only": list(CONTRACT_ONLY_PROPERTIES),
    }
    if dict(taxonomy) != expected_taxonomy:
        raise ValueError("measurement_taxonomy_changed")
    _validate_thresholds(corpus.get("thresholds"))

    cases = corpus.get("cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASES:
        raise ValueError("case_count_invalid")
    case_ids: list[str] = []
    covered_families: set[str] = set()
    states: set[str] = set()
    provider_case_count = 0
    for case in cases:
        _validate_case(case)
        case_id = str(case["id"])
        if case_id in case_ids:
            raise ValueError("duplicate_case_id")
        case_ids.append(case_id)
        covered_families.update(str(item) for item in case["families"])
        states.add(str(case["enunciation_state"]))
        provider_case_count += int(case["provider_eligible"] is True)
    if set(REQUIRED_FAMILIES) - covered_families:
        raise ValueError("required_family_coverage_missing")
    if states != set(ENUNCIATION_STATES):
        raise ValueError("enunciation_state_coverage_invalid")
    if provider_case_count != EXPECTED_PROVIDER_CASES:
        raise ValueError("provider_case_count_invalid")
    if set(corpus.get("mutation_matrix") or []) != REQUIRED_MUTATIONS:
        raise ValueError("mutation_matrix_invalid")
    if len(corpus["mutation_matrix"]) != len(REQUIRED_MUTATIONS):
        raise ValueError("mutation_matrix_duplicate")
    return {
        "case_count": len(cases),
        "provider_case_count": provider_case_count,
        "case_ids": case_ids,
        "covered_families": sorted(covered_families),
        "enunciation_states": sorted(states),
        "final_text_properties": list(FINAL_TEXT_PROPERTIES),
        "other_stage_properties": list(OTHER_STAGE_PROPERTIES),
        "contract_only_properties": list(CONTRACT_ONLY_PROPERTIES),
    }


def _validate_thresholds(value: Any) -> None:
    thresholds = _exact_keys(
        value,
        {
            "schema_version",
            "transition_delicacy_improvement_rate",
            "transition_formulation_improvement_rate",
            "countercase_formulation_worse_rate",
            "critical_zero_tolerance",
            "countercase_overapplication_rate",
        },
        "threshold_fields_invalid",
    )
    if thresholds.get("schema_version") != THRESHOLD_SCHEMA_VERSION:
        raise ValueError("threshold_schema_invalid")
    if float(thresholds.get("transition_delicacy_improvement_rate", -1)) != 0.8:
        raise ValueError("delicacy_threshold_invalid")
    if float(thresholds.get("transition_formulation_improvement_rate", -1)) != 0.75:
        raise ValueError("formulation_threshold_invalid")
    if float(thresholds.get("countercase_formulation_worse_rate", -1)) != 0.0:
        raise ValueError("countercase_formulation_threshold_invalid")
    if set(thresholds.get("critical_zero_tolerance") or []) != {
        "psychologization",
        "certainty_change",
        "truth_or_evidence_change",
        "masked_target",
        "presence_regression",
    }:
        raise ValueError("critical_threshold_invalid")
    if float(thresholds.get("countercase_overapplication_rate", -1)) != 0.0:
        raise ValueError("overapplication_threshold_invalid")


def _validate_case(value: Any) -> None:
    case = _exact_keys(value, _CASE_KEYS, "case_fields_invalid")
    case_id = _bounded_text(case.get("id"), maximum=40)
    if not case_id.startswith("L4C4-FW-") or case.get("version") != "v1":
        raise ValueError("case_identity_invalid")
    families = case.get("families")
    if (
        not isinstance(families, list)
        or not families
        or len(families) != len(set(families))
        or any(str(item) not in REQUIRED_FAMILIES for item in families)
    ):
        raise ValueError("case_families_invalid")
    if case.get("enunciation_state") not in ENUNCIATION_STATES:
        raise ValueError("case_enunciation_state_invalid")
    if not isinstance(case.get("provider_eligible"), bool):
        raise ValueError("case_provider_eligibility_invalid")

    dialogue = _exact_keys(case.get("dialogue"), _DIALOGUE_KEYS, "dialogue_fields_invalid")
    history = dialogue.get("history")
    if not isinstance(history, list) or len(history) > 4:
        raise ValueError("dialogue_history_invalid")
    expected_role = "user"
    for message in history:
        message_map = _exact_keys(message, {"role", "content"}, "dialogue_message_invalid")
        if message_map.get("role") != expected_role:
            raise ValueError("dialogue_order_invalid")
        _bounded_text(message_map.get("content"), maximum=600)
        expected_role = "assistant" if expected_role == "user" else "user"
    if len(history) % 2:
        raise ValueError("dialogue_history_incomplete")
    _bounded_text(dialogue.get("user"), maximum=700)

    epistemic = _exact_keys(
        case.get("epistemic_matter"),
        _EPISTEMIC_KEYS,
        "epistemic_matter_fields_invalid",
    )
    for key in _EPISTEMIC_KEYS:
        _bounded_text(epistemic.get(key), maximum=500)

    expectations = _exact_keys(
        case.get("expectations"),
        _EXPECTATION_KEYS,
        "expectation_fields_invalid",
    )
    final_text = _exact_keys(
        expectations.get("final_text"),
        _FINAL_TEXT_EXPECTATION_KEYS,
        "final_text_expectation_fields_invalid",
    )
    if final_text.get("delicacy_effect") not in {"required", "forbidden", "not_applicable"}:
        raise ValueError("delicacy_expectation_invalid")
    if final_text.get("formulation_fit") not in {
        "improve_or_preserve",
        "preserve",
        "not_text_measurable",
    }:
        raise ValueError("formulation_expectation_invalid")
    if any(
        final_text.get(key) != "forbidden"
        for key in (
            "psychologization",
            "certainty_change",
            "truth_or_evidence_change",
            "overapplication",
        )
    ):
        raise ValueError("forbidden_final_text_property_changed")
    targets = final_text.get("masked_targets")
    if (
        not isinstance(targets, list)
        or len(targets) != len(set(targets))
        or any(target not in {"question", "request", "risk", "material_action"} for target in targets)
    ):
        raise ValueError("masked_targets_invalid")

    other_stage = _exact_keys(
        expectations.get("other_stage"),
        _OTHER_STAGE_EXPECTATION_KEYS,
        "other_stage_expectation_fields_invalid",
    )
    if other_stage.get("presence_relation") not in {"eligible", "forbidden", "not_applicable"}:
        raise ValueError("presence_relation_invalid")
    if other_stage.get("main_model_call") not in {"required", "forbidden", "not_measured"}:
        raise ValueError("main_model_call_expectation_invalid")
    contract = _exact_keys(
        expectations.get("contract_only"),
        _CONTRACT_EXPECTATION_KEYS,
        "contract_expectation_fields_invalid",
    )
    if any(contract.get(key) is not True for key in _CONTRACT_EXPECTATION_KEYS):
        raise ValueError("contract_expectation_invalid")
    if case["provider_eligible"] and other_stage["main_model_call"] != "required":
        raise ValueError("provider_case_main_call_invalid")
    if other_stage["presence_relation"] == "eligible" and (
        case["provider_eligible"] or other_stage["main_model_call"] != "forbidden"
    ):
        raise ValueError("presence_provider_bypass_invalid")


def case_by_id(corpus: Mapping[str, Any], case_id: Any) -> Mapping[str, Any]:
    for case in corpus.get("cases", []):
        if isinstance(case, Mapping) and case.get("id") == case_id:
            return case
    raise ValueError("unknown_case_id")


def _epistemic_effect(case: Mapping[str, Any]) -> dict[str, str]:
    regime = str(case["epistemic_matter"]["epistemic_regime"])
    if regime == "certain":
        return {
            "effect": "certain",
            "source": "epistemic_inputs",
            "reason_code": "sufficient_independent_support",
        }
    if regime == "probable":
        return {
            "effect": "probable",
            "source": "epistemic_inputs",
            "reason_code": "limited_independent_support",
        }
    return {
        "effect": "a_verifier",
        "source": "epistemic_inputs",
        "reason_code": "external_verification_required",
    }


def _enunciation_directive(state: str, variant: str) -> dict[str, str] | None:
    if state == "fail_open_unknown":
        return None
    if state == "transition_delicate" and variant == "treatment":
        return {
            "effect": "delicate_expression",
            "source": "stimmung",
            "reason_code": "affective_transition",
        }
    if state == "stable_noop" or (state == "transition_delicate" and variant == "control"):
        return {
            "effect": "none",
            "source": "stimmung",
            "reason_code": "stimmung_stable",
        }
    return {
        "effect": "none",
        "source": "not_applicable",
        "reason_code": "stimmung_absent",
    }


def _judgment_block(case: Mapping[str, Any], variant: str) -> str:
    directive = _enunciation_directive(str(case["enunciation_state"]), variant)
    if directive is None:
        return ""
    validated_output = {
        "final_judgment_posture": "answer",
        "final_output_regime": "simple",
        "pipeline_directives_final": ["preserve_truth_evidence_and_guards"],
        "epistemic_effect": _epistemic_effect(case),
        "enunciation_directive": directive,
    }
    return chat_prompt_context.build_hermeneutic_judgment_block(
        validated_output=validated_output,
    )


def _base_augmented_system() -> str:
    system_prompt = prompt_loader.require_usable_prompt_text(
        prompt_loader.get_main_system_prompt(),
        prompt_id="main_system",
    )
    hermeneutical_prompt = prompt_loader.require_usable_prompt_text(
        prompt_loader.get_main_hermeneutical_prompt(),
        prompt_id="main_hermeneutical",
    )
    augmented, identity_ids = chat_prompt_context.build_augmented_system(
        system_prompt=system_prompt,
        hermeneutical_prompt=hermeneutical_prompt,
        config_module=config,
        identity_module=_EmptyIdentity,
        now_iso=FIXED_NOW_ISO,
    )
    if identity_ids:
        raise ValueError("synthetic_campaign_identity_not_empty")
    return augmented


def _build_messages(case: Mapping[str, Any], variant: str) -> list[dict[str, Any]]:
    if variant not in {"control", "treatment"}:
        raise ValueError("variant_invalid")
    augmented = chat_prompt_context.inject_hermeneutic_judgment_block(
        _base_augmented_system(),
        _judgment_block(case, variant),
    )
    messages: list[dict[str, Any]] = [{"role": "system", "content": augmented}]
    messages.extend(copy.deepcopy(list(case["dialogue"]["history"])))
    messages.append({"role": "user", "content": str(case["dialogue"]["user"])})
    capsule = continuity_capsule.resolve_continuity_capsule(config_module=config)
    if not continuity_capsule.inject_continuity_capsule(messages, capsule):
        raise ValueError("continuity_capsule_not_injected")
    return messages


def _variant_order(case_index: int, repetition: int) -> tuple[str, str]:
    control_first = (case_index + repetition) % 2 == 0
    return ("control", "treatment") if control_first else ("treatment", "control")


def _build_request_schedule(repo_root: Path) -> list[dict[str, Any]]:
    corpus = load_corpus(repo_root)
    provider_cases = [case for case in corpus["cases"] if case["provider_eligible"]]
    schedule: list[dict[str, Any]] = []
    sequence = 0
    for repetition in range(1, REPETITIONS + 1):
        for case_index, case in enumerate(provider_cases, start=1):
            for arm_index, variant in enumerate(_variant_order(case_index, repetition), start=1):
                sequence += 1
                messages = _build_messages(case, variant)
                payload = {
                    "model": ACTIVE_MAIN_MODEL,
                    "messages": messages,
                    "temperature": ACTIVE_TEMPERATURE,
                    "top_p": ACTIVE_TOP_P,
                    "max_tokens": ACTIVE_MAX_TOKENS,
                    "stop": ["<|endoftext|>", "<|return|>", "<|call|>"],
                    "reasoning": dict(ACTIVE_REASONING),
                    "provider": {"allow_fallbacks": False, "require_parameters": True},
                }
                schedule.append(
                    {
                        "sequence": sequence,
                        "case_id": case["id"],
                        "repetition": repetition,
                        "blinded_arm": f"arm_{arm_index}",
                        "variant": variant,
                        "messages_sha256": _sha256_text(_compact_json(messages)),
                        "payload": payload,
                    }
                )
    if len(schedule) != EXPECTED_CALLS:
        raise ValueError("schedule_call_count_invalid")
    return schedule


def build_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    if not _is_commit(freeze_commit):
        raise ValueError("freeze_commit_invalid")
    corpus = load_corpus(repo_root)
    schedule = _build_request_schedule(repo_root)
    validate_paired_schedule(corpus, schedule)
    prompt_token_estimate_sum = sum(
        int(token_utils.estimate_tokens(item["payload"]["messages"], ACTIVE_MAIN_MODEL))
        for item in schedule
    )
    theoretical_max_cost = round(
        prompt_token_estimate_sum * PRICING_USD_PER_TOKEN["prompt"]
        + EXPECTED_CALLS * ACTIVE_MAX_TOKENS * PRICING_USD_PER_TOKEN["completion"],
        8,
    )
    estimated_max_cost = round(theoretical_max_cost * COST_MARGIN, 8)
    if estimated_max_cost > ABSOLUTE_COST_CAP_USD:
        raise ValueError("estimated_cost_cap_exceeded")
    schedule_fingerprint = [
        {
            key: item[key]
            for key in (
                "sequence",
                "case_id",
                "repetition",
                "blinded_arm",
                "variant",
                "messages_sha256",
            )
        }
        for item in schedule
    ]
    protocol = {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "campaign_kind": "paired_current_main_model_final_wording",
        "phase_a_decision": "provider_campaign_required",
        "freeze_commit": freeze_commit,
        "corpus_id": corpus["corpus_id"],
        "corpus_sha256": _sha256_file(_fixture_path(repo_root)),
        "scorer_and_harness_sha256": _sha256_file(_harness_path(repo_root)),
        "main_system_prompt_sha256": _sha256_file(repo_root / "app/prompts/main_system.txt"),
        "main_hermeneutical_prompt_sha256": _sha256_file(
            repo_root / "app/prompts/main_hermeneutical.txt"
        ),
        "chat_prompt_context_sha256": _sha256_file(repo_root / "app/core/chat_prompt_context.py"),
        "continuity_capsule_sha256": _sha256_file(repo_root / "app/core/continuity_capsule.py"),
        "main_payload_builder_sha256": _sha256_file(repo_root / "app/core/chat_main_payload.py"),
        "schedule_sha256": _sha256_text(_compact_json(schedule_fingerprint)),
        "model": ACTIVE_MAIN_MODEL,
        "temperature": ACTIVE_TEMPERATURE,
        "top_p": ACTIVE_TOP_P,
        "max_tokens": ACTIVE_MAX_TOKENS,
        "reasoning": dict(ACTIVE_REASONING),
        "timeout_s": ACTIVE_TIMEOUT_S,
        "sampling_policy": "runtime_active",
        "transport_policy": {
            "mode": "standard",
            "batch": False,
            "flex": False,
            "priority": False,
            "retry_count": 0,
            "automatic_model_fallback": False,
            "provider_fallbacks": False,
        },
        "additional_stage_calls": 0,
        "repetitions": REPETITIONS,
        "repetition_rationale": REPETITION_RATIONALE,
        "case_count": EXPECTED_CASES,
        "provider_case_count": EXPECTED_PROVIDER_CASES,
        "expected_pair_count": EXPECTED_PAIRS,
        "expected_call_count": EXPECTED_CALLS,
        "absolute_call_cap": ABSOLUTE_CALL_CAP,
        "prompt_token_estimate_sum": prompt_token_estimate_sum,
        "completion_token_ceiling": EXPECTED_CALLS * ACTIVE_MAX_TOKENS,
        "pricing_observed_at": PRICING_OBSERVED_AT,
        "pricing_source": PRICING_SOURCE,
        "pricing_usd_per_token": dict(PRICING_USD_PER_TOKEN),
        "cost_margin": COST_MARGIN,
        "theoretical_max_cost_usd": theoretical_max_cost,
        "estimated_max_cost_usd": estimated_max_cost,
        "absolute_cost_cap_usd": ABSOLUTE_COST_CAP_USD,
        "scoring_policy": {
            "method": "blinded_structured_human_annotation",
            "semantic_regex": False,
            "model_judge_calls": 0,
            "fake_semantic_results_allowed": False,
            "threshold_schema_version": THRESHOLD_SCHEMA_VERSION,
        },
        "artifact_policy": {
            "content_free": True,
            "raw_dialogue": False,
            "raw_prompt": False,
            "raw_provider_response": False,
            "response_hash_and_chars_only": True,
        },
        "decision_rules": {
            "all_complete_thresholds_met": "pass",
            "complete_semantic_threshold_missed": "fail",
            "all_attempts_recorded_but_response_or_rating_unavailable": "inconclusive",
            "no_authoritative_provider_results": "provider_campaign_required",
            "authoritative_existing_semantic_proof_sufficient": "non_required",
        },
    }
    _validate_freeze_manifest_against_protocol(
        json.loads(_freeze_manifest_path(repo_root).read_text(encoding="utf-8")),
        protocol,
        repo_root,
    )
    return protocol


def _expected_freeze_manifest(
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> dict[str, Any]:
    corpus = load_corpus(repo_root)
    return {
        "schema_version": "stimmung_final_wording_freeze_v1",
        "status": "provider_campaign_required",
        "baseline_head": BASELINE_HEAD,
        "protocol_version": PROTOCOL_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "corpus": {
            "path": "benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v1.json",
            "sha256": protocol["corpus_sha256"],
            "case_count": EXPECTED_CASES,
            "provider_case_count": EXPECTED_PROVIDER_CASES,
        },
        "harness": {
            "path": "benchmark/suites/stimmung/final_wording_diagnostic.py",
            "sha256": protocol["scorer_and_harness_sha256"],
            "semantic_regex": False,
            "fake_semantic_results_allowed": False,
        },
        "product_inputs": {
            "main_system_prompt_sha256": protocol["main_system_prompt_sha256"],
            "main_hermeneutical_prompt_sha256": protocol[
                "main_hermeneutical_prompt_sha256"
            ],
            "chat_prompt_context_sha256": protocol["chat_prompt_context_sha256"],
            "continuity_capsule_sha256": protocol["continuity_capsule_sha256"],
            "main_payload_builder_sha256": protocol["main_payload_builder_sha256"],
        },
        "runtime_policy": {
            "model": ACTIVE_MAIN_MODEL,
            "temperature": ACTIVE_TEMPERATURE,
            "top_p": ACTIVE_TOP_P,
            "max_tokens": ACTIVE_MAX_TOKENS,
            "reasoning": dict(ACTIVE_REASONING),
            "timeout_s": ACTIVE_TIMEOUT_S,
            "provider": {"allow_fallbacks": False, "require_parameters": True},
            "transport": "standard",
            "batch": False,
            "flex": False,
            "priority": False,
            "retry_count": 0,
        },
        "schedule": {
            "sha256": protocol["schedule_sha256"],
            "repetitions": REPETITIONS,
            "repetition_rationale": REPETITION_RATIONALE,
            "pair_count": EXPECTED_PAIRS,
            "call_count": EXPECTED_CALLS,
            "absolute_call_cap": ABSOLUTE_CALL_CAP,
            "additional_validation_calls": 0,
            "additional_stimmung_calls": 0,
            "model_judge_calls": 0,
        },
        "cost": {
            "pricing_observed_at": PRICING_OBSERVED_AT,
            "pricing_source": PRICING_SOURCE,
            "prompt_usd_per_token": PRICING_USD_PER_TOKEN["prompt"],
            "completion_usd_per_token": PRICING_USD_PER_TOKEN["completion"],
            "prompt_token_estimate_sum": protocol["prompt_token_estimate_sum"],
            "completion_token_ceiling": protocol["completion_token_ceiling"],
            "theoretical_max_cost_usd": protocol["theoretical_max_cost_usd"],
            "margin": COST_MARGIN,
            "estimated_max_cost_usd": protocol["estimated_max_cost_usd"],
            "absolute_cost_cap_usd": ABSOLUTE_COST_CAP_USD,
        },
        "scoring": {
            "method": "blinded_structured_human_annotation",
            "thresholds": copy.deepcopy(corpus["thresholds"]),
            "final_text_properties": list(FINAL_TEXT_PROPERTIES),
            "other_stage_properties": list(OTHER_STAGE_PROPERTIES),
            "contract_only_properties": list(CONTRACT_ONLY_PROPERTIES),
        },
        "decision_rules": copy.deepcopy(protocol["decision_rules"]),
        "artifact_policy": copy.deepcopy(protocol["artifact_policy"]),
        "mutation_matrix": list(corpus["mutation_matrix"]),
        "phase_limits": {
            "provider_calls_executed_in_phase_a": 0,
            "runtime_change": False,
            "prompt_change": False,
            "model_change": False,
            "frontend_change": False,
            "deployment": False,
            "lot4oz_started": False,
        },
        "delivery_requirement": "commit_and_push_before_separate_go",
    }


def _validate_freeze_manifest_against_protocol(
    manifest: Any,
    protocol: Mapping[str, Any],
    repo_root: Path,
) -> None:
    if not isinstance(manifest, Mapping):
        raise ValueError("freeze_manifest_root_invalid")
    expected = _expected_freeze_manifest(protocol, repo_root)
    if dict(manifest) != expected:
        raise ValueError("freeze_manifest_mismatch")


def validate_freeze_manifest(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    protocol = build_protocol(repo_root, freeze_commit=freeze_commit)
    manifest = json.loads(_freeze_manifest_path(repo_root).read_text(encoding="utf-8"))
    _validate_freeze_manifest_against_protocol(manifest, protocol, repo_root)
    return {
        "status": manifest["status"],
        "call_count": manifest["schedule"]["call_count"],
        "estimated_max_cost_usd": manifest["cost"]["estimated_max_cost_usd"],
        "absolute_cost_cap_usd": manifest["cost"]["absolute_cost_cap_usd"],
    }


def validate_protocol(protocol: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    if protocol.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("protocol_version_invalid")
    expected = build_protocol(
        repo_root,
        freeze_commit=str(protocol.get("freeze_commit") or ""),
    )
    if dict(protocol) != expected:
        raise ValueError("protocol_freeze_mismatch")
    if expected["expected_call_count"] != expected["absolute_call_cap"]:
        raise ValueError("protocol_call_cap_mismatch")
    return {
        "expected_call_count": expected["expected_call_count"],
        "expected_pair_count": expected["expected_pair_count"],
        "estimated_max_cost_usd": expected["estimated_max_cost_usd"],
        "absolute_cost_cap_usd": expected["absolute_cost_cap_usd"],
    }


def build_request_schedule(
    repo_root: Path,
    protocol: Mapping[str, Any],
) -> list[dict[str, Any]]:
    validate_protocol(protocol, repo_root)
    schedule = _build_request_schedule(repo_root)
    if len(schedule) != protocol["absolute_call_cap"]:
        raise ValueError("schedule_exceeds_call_cap")
    return schedule


def _normalized_messages_for_pair(messages: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for message in messages:
        role = str(message.get("role") or "")
        content = str(message.get("content") or "")
        lines = [
            line
            for line in content.splitlines()
            if not any(line.startswith(prefix) for prefix in _ENUNCIATION_PREFIXES)
        ]
        normalized.append({"role": role, "content": "\n".join(lines)})
    return normalized


def _validate_message_contract(
    messages: Sequence[Mapping[str, Any]],
    *,
    state: str,
    variant: str,
) -> int:
    if not isinstance(messages, list) or not messages:
        raise ValueError("messages_invalid")
    serialized = _compact_json(messages)
    if any(marker in serialized for marker in _RAW_STIMMUNG_MARKERS):
        raise ValueError("raw_stimmung_in_main_payload")
    capsule_count = sum(
        str(message.get("content") or "").startswith(_CAPSULE_HEADER)
        for message in messages
        if isinstance(message, Mapping)
    )
    if capsule_count != 1:
        raise ValueError("continuity_capsule_cardinality_invalid")
    if not str(messages[-1].get("content") or "").startswith(_CAPSULE_HEADER):
        raise ValueError("continuity_capsule_not_terminal")
    effect_count = serialized.count("Effet d'enonciation:")
    delicate_count = serialized.count("Effet d'enonciation: delicate_expression")
    instruction_count = serialized.count("Consigne d'enonciation:")
    if state == "fail_open_unknown":
        if effect_count or delicate_count or instruction_count:
            raise ValueError("fail_open_enunciation_fabricated")
    elif state == "transition_delicate" and variant == "treatment":
        if (effect_count, delicate_count, instruction_count) != (1, 1, 1):
            raise ValueError("transition_directive_invalid")
    else:
        if (effect_count, delicate_count, instruction_count) != (1, 0, 0):
            raise ValueError("noop_directive_invalid")
    return capsule_count


def validate_paired_schedule(
    corpus: Mapping[str, Any],
    schedule: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    validate_corpus(corpus)
    if not isinstance(schedule, list) or len(schedule) != EXPECTED_CALLS:
        raise ValueError("schedule_cardinality_invalid")
    expected_keys = {
        "sequence",
        "case_id",
        "repetition",
        "blinded_arm",
        "variant",
        "messages_sha256",
        "payload",
    }
    pairs: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = {}
    raw_occurrences = 0
    capsule_errors = 0
    for expected_sequence, item in enumerate(schedule, start=1):
        _exact_keys(item, expected_keys, "schedule_item_fields_invalid")
        if item.get("sequence") != expected_sequence:
            raise ValueError("schedule_sequence_invalid")
        case = case_by_id(corpus, item.get("case_id"))
        if case.get("provider_eligible") is not True:
            raise ValueError("non_provider_case_scheduled")
        repetition = item.get("repetition")
        variant = str(item.get("variant") or "")
        if repetition not in {1, 2} or variant not in {"control", "treatment"}:
            raise ValueError("schedule_pair_identity_invalid")
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("schedule_payload_invalid")
        if set(payload) != {
            "model",
            "messages",
            "temperature",
            "top_p",
            "max_tokens",
            "stop",
            "reasoning",
            "provider",
        }:
            raise ValueError("schedule_payload_fields_invalid")
        common_payload = dict(payload)
        messages = common_payload.pop("messages", None)
        if common_payload != {
            "model": ACTIVE_MAIN_MODEL,
            "temperature": ACTIVE_TEMPERATURE,
            "top_p": ACTIVE_TOP_P,
            "max_tokens": ACTIVE_MAX_TOKENS,
            "stop": ["<|endoftext|>", "<|return|>", "<|call|>"],
            "reasoning": ACTIVE_REASONING,
            "provider": {"allow_fallbacks": False, "require_parameters": True},
        }:
            raise ValueError("schedule_runtime_policy_invalid")
        if not isinstance(messages, list):
            raise ValueError("schedule_messages_invalid")
        if item.get("messages_sha256") != _sha256_text(_compact_json(messages)):
            raise ValueError("schedule_message_fingerprint_invalid")
        serialized = _compact_json(messages)
        raw_occurrences += sum(serialized.count(marker) for marker in _RAW_STIMMUNG_MARKERS)
        try:
            _validate_message_contract(
                messages,
                state=str(case["enunciation_state"]),
                variant=variant,
            )
        except ValueError as exc:
            if "continuity_capsule" in str(exc):
                capsule_errors += 1
            raise
        key = (str(case["id"]), int(repetition))
        variants = pairs.setdefault(key, {})
        if variant in variants:
            raise ValueError("schedule_variant_duplicated")
        variants[variant] = item

    if len(pairs) != EXPECTED_PAIRS:
        raise ValueError("schedule_pair_count_invalid")
    unauthorized = 0
    for (case_id, _repetition), variants in pairs.items():
        if set(variants) != {"control", "treatment"}:
            raise ValueError("schedule_pair_incomplete")
        control_messages = variants["control"]["payload"]["messages"]
        treatment_messages = variants["treatment"]["payload"]["messages"]
        if _normalized_messages_for_pair(control_messages) != _normalized_messages_for_pair(
            treatment_messages
        ):
            unauthorized += 1
        case = case_by_id(corpus, case_id)
        if case["enunciation_state"] == "transition_delicate":
            if control_messages == treatment_messages:
                raise ValueError("transition_pair_has_no_directive_difference")
        elif control_messages != treatment_messages:
            unauthorized += 1
    if unauthorized:
        raise ValueError("unauthorized_paired_difference")
    return {
        "pair_count": len(pairs),
        "unauthorized_difference_count": unauthorized,
        "raw_stimmung_occurrence_count": raw_occurrences,
        "continuity_capsule_error_count": capsule_errors,
    }


def _validate_observation(value: Any) -> Mapping[str, Any]:
    observation = _exact_keys(value, _OBSERVATION_KEYS, "observation_fields_invalid")
    if observation.get("source_kind") != "main_model_provider":
        raise ValueError("observation_source_invalid")
    if observation.get("repetition") not in {1, 2}:
        raise ValueError("observation_repetition_invalid")
    if not isinstance(observation.get("call_attempts_complete"), bool) or not isinstance(
        observation.get("responses_complete"), bool
    ):
        raise ValueError("observation_completeness_invalid")
    if not _is_sha256(observation.get("control_response_sha256")) or not _is_sha256(
        observation.get("treatment_response_sha256")
    ):
        raise ValueError("observation_response_hash_invalid")
    if observation.get("delicacy_effect") not in {
        "improved",
        "unchanged",
        "worse",
        "not_applicable",
    }:
        raise ValueError("observation_delicacy_invalid")
    if observation.get("formulation_fit") not in {"improved", "unchanged", "worse"}:
        raise ValueError("observation_formulation_invalid")
    for key in ("psychologization", "certainty_change", "truth_or_evidence_change"):
        if observation.get(key) not in {"none", "control", "treatment", "both"}:
            raise ValueError(f"observation_{key}_invalid")
    targets = observation.get("masked_targets")
    if (
        not isinstance(targets, list)
        or len(targets) != len(set(targets))
        or any(target not in {"question", "request", "risk", "material_action"} for target in targets)
    ):
        raise ValueError("observation_masked_targets_invalid")
    if observation.get("presence_regression") not in {
        "none",
        "control",
        "treatment",
        "both",
        "not_text_measurable",
    }:
        raise ValueError("observation_presence_invalid")
    if not isinstance(observation.get("overapplication"), bool):
        raise ValueError("observation_overapplication_invalid")
    return observation


def score_campaign(
    corpus: Mapping[str, Any],
    observations: Sequence[Mapping[str, Any]],
    *,
    provider_results_observed: bool,
    source_kind: str,
    authoritative_existing_semantic_proof: bool,
) -> dict[str, Any]:
    validate_corpus(corpus)
    if not isinstance(provider_results_observed, bool) or not isinstance(
        authoritative_existing_semantic_proof, bool
    ):
        raise ValueError("decision_provenance_invalid")
    if source_kind == "fake":
        if observations:
            raise ValueError("fake_semantic_result_forbidden")
        if provider_results_observed or authoritative_existing_semantic_proof:
            raise ValueError("fake_provider_provenance_invalid")
        return {
            "decision": "provider_campaign_required",
            "reason_codes": ["fake_cannot_measure_final_wording"],
            "provider_results_observed": False,
            "observed_pair_count": 0,
            "critical_failure_count": 0,
            "overapplication_count": 0,
            "raw_response_included": False,
        }
    if not provider_results_observed:
        if authoritative_existing_semantic_proof and source_kind == "authoritative_existing":
            decision = "non_required"
            reasons = ["authoritative_existing_semantic_proof_sufficient"]
        else:
            decision = "provider_campaign_required"
            reasons = ["provider_results_not_observed"]
        if observations:
            raise ValueError("unobserved_provider_results_present")
        return {
            "decision": decision,
            "reason_codes": reasons,
            "provider_results_observed": False,
            "observed_pair_count": 0,
            "critical_failure_count": 0,
            "overapplication_count": 0,
            "raw_response_included": False,
        }
    if source_kind != "main_model_provider" or authoritative_existing_semantic_proof:
        raise ValueError("provider_source_kind_invalid")

    provider_cases = [case for case in corpus["cases"] if case["provider_eligible"]]
    expected_keys = {
        (str(case["id"]), repetition)
        for case in provider_cases
        for repetition in (1, 2)
    }
    observed_by_key: dict[tuple[str, int], Mapping[str, Any]] = {}
    for raw in observations:
        observation = _validate_observation(raw)
        key = (str(observation["case_id"]), int(observation["repetition"]))
        if key not in expected_keys or key in observed_by_key:
            raise ValueError("observation_set_invalid")
        observed_by_key[key] = observation
    if set(observed_by_key) != expected_keys:
        raise ValueError("observation_set_incomplete")
    if any(not item["call_attempts_complete"] for item in observed_by_key.values()):
        raise ValueError("call_attempt_ledger_incomplete")

    response_incomplete = sum(
        not bool(item["responses_complete"]) for item in observed_by_key.values()
    )
    critical_failures = 0
    overapplications = 0
    delicacy_total = 0
    delicacy_improved = 0
    formulation_total = 0
    formulation_improved = 0
    semantic_failures: list[str] = []
    for key, observation in observed_by_key.items():
        case = case_by_id(corpus, key[0])
        if case["enunciation_state"] == "transition_delicate":
            delicacy_total += 1
            formulation_total += 1
            delicacy_improved += int(observation["delicacy_effect"] == "improved")
            formulation_improved += int(observation["formulation_fit"] == "improved")
            if observation["delicacy_effect"] in {"worse", "not_applicable"}:
                semantic_failures.append("transition_delicacy_harm")
            if observation["formulation_fit"] == "worse":
                semantic_failures.append("transition_formulation_harm")
        else:
            if observation["delicacy_effect"] not in {"not_applicable", "unchanged"}:
                overapplications += 1
            if observation["overapplication"]:
                overapplications += 1
            if observation["formulation_fit"] == "worse":
                semantic_failures.append("countercase_formulation_harm")

        critical_failures += sum(
            observation[field] != "none"
            for field in (
                "psychologization",
                "certainty_change",
                "truth_or_evidence_change",
            )
        )
        critical_failures += int(bool(observation["masked_targets"]))
        critical_failures += int(
            observation["presence_regression"]
            not in {"none", "not_text_measurable"}
        )

    delicacy_rate = delicacy_improved / max(delicacy_total, 1)
    formulation_rate = formulation_improved / max(formulation_total, 1)
    thresholds = corpus["thresholds"]
    if critical_failures:
        semantic_failures.append("critical_zero_tolerance_breached")
    if overapplications:
        semantic_failures.append("countercase_overapplication")
    if delicacy_rate < float(thresholds["transition_delicacy_improvement_rate"]):
        semantic_failures.append("delicacy_improvement_threshold_missed")
    if formulation_rate < float(thresholds["transition_formulation_improvement_rate"]):
        semantic_failures.append("formulation_improvement_threshold_missed")

    if response_incomplete:
        decision = "inconclusive"
        reason_codes = ["provider_response_incomplete"]
    elif semantic_failures:
        decision = "fail"
        reason_codes = sorted(set(semantic_failures))
    else:
        decision = "pass"
        reason_codes = ["all_complete_thresholds_met"]
    return {
        "decision": decision,
        "reason_codes": reason_codes,
        "provider_results_observed": True,
        "observed_pair_count": len(observed_by_key),
        "critical_failure_count": critical_failures,
        "overapplication_count": overapplications,
        "transition_delicacy_improvement_rate": round(delicacy_rate, 4),
        "transition_formulation_improvement_rate": round(formulation_rate, 4),
        "response_incomplete_count": response_incomplete,
        "raw_response_included": False,
    }


def _last_main_messages(result: Mapping[str, Any]) -> list[dict[str, Any]]:
    calls = result.get("main_messages")
    if not isinstance(calls, list) or not calls or not isinstance(calls[-1], list):
        raise ValueError("fake_main_messages_missing")
    return calls[-1]


def _latest_manifest(result: Mapping[str, Any]) -> Mapping[str, Any]:
    manifests = result.get("manifests")
    if not isinstance(manifests, list) or not manifests or not isinstance(manifests[-1], Mapping):
        raise ValueError("fake_manifest_missing")
    manifest = manifests[-1]
    if manifest.get("schema_version") != "main_payload_manifest_v1":
        raise ValueError("fake_manifest_schema_invalid")
    if manifest.get("main_model_called") is not True:
        raise ValueError("fake_manifest_main_model_call_invalid")
    final_lock = manifest.get("final_response_lock")
    if not isinstance(final_lock, Mapping) or final_lock.get("present") is not False:
        raise ValueError("fake_final_lock_bypass")
    capsule = manifest.get("continuity_capsule")
    if not isinstance(capsule, Mapping) or capsule.get("injected_count") != 1:
        raise ValueError("fake_manifest_capsule_invalid")
    return manifest


def _assistant_provenance_ok(result: Mapping[str, Any]) -> bool:
    durable = result.get("durable")
    messages = durable.get("messages") if isinstance(durable, Mapping) else None
    if not isinstance(messages, list):
        return False
    assistants = [
        message
        for message in messages
        if isinstance(message, Mapping) and message.get("role") == "assistant"
    ]
    if len(assistants) != len(result.get("responses") or []):
        return False
    for message in assistants:
        meta = message.get("meta")
        provenance = meta.get("assistant_runtime_provenance") if isinstance(meta, Mapping) else None
        if not isinstance(provenance, Mapping) or provenance.get("response_origin") != "main_model":
            return False
    return True


def validate_fake_pipeline_proof(
    *,
    stable: Mapping[str, Any],
    transition: Mapping[str, Any],
    transition_stream: Mapping[str, Any],
    fail_open: Mapping[str, Any],
) -> dict[str, Any]:
    stable_messages = _last_main_messages(stable)
    transition_messages = _last_main_messages(transition)
    stream_messages = _last_main_messages(transition_stream)
    fail_open_messages = _last_main_messages(fail_open)
    _validate_message_contract(stable_messages, state="stable_noop", variant="treatment")
    _validate_message_contract(
        transition_messages,
        state="transition_delicate",
        variant="treatment",
    )
    _validate_message_contract(
        stream_messages,
        state="transition_delicate",
        variant="treatment",
    )
    _validate_message_contract(
        fail_open_messages,
        state="fail_open_unknown",
        variant="control",
    )
    if _normalized_messages_for_pair(stable_messages) != _normalized_messages_for_pair(
        transition_messages
    ):
        raise ValueError("fake_pair_matter_changed")
    if transition_messages != stream_messages:
        raise ValueError("fake_json_stream_payload_mismatch")

    stable_verdict = stable["node_calls"][-1]["validated_output"]
    transition_verdict = transition["node_calls"][-1]["validated_output"]
    epistemic_fields = ("epistemic_effect",)
    if any(stable_verdict.get(field) != transition_verdict.get(field) for field in epistemic_fields):
        raise ValueError("fake_epistemic_effect_changed")
    if stable_verdict.get("enunciation_directive", {}).get("effect") != "none":
        raise ValueError("fake_stable_noop_invalid")
    if transition_verdict.get("enunciation_directive", {}).get("effect") != "delicate_expression":
        raise ValueError("fake_transition_directive_invalid")
    fail_output = fail_open["node_calls"][-1]["validated_output"]
    if fail_output.get("final_output_regime") == "presence":
        raise ValueError("fake_fail_open_presence_regression")

    manifests = [
        _latest_manifest(result)
        for result in (stable, transition, transition_stream, fail_open)
    ]
    if any(not _assistant_provenance_ok(result) for result in (stable, transition, transition_stream, fail_open)):
        raise ValueError("fake_assistant_provenance_invalid")
    if any(
        len([call for call in result.get("provider_calls", []) if call.get("model") == "lot4/main"])
        != len(result.get("responses") or [])
        for result in (stable, transition, transition_stream, fail_open)
    ):
        raise ValueError("fake_main_call_cardinality_invalid")
    stream_responses = transition_stream.get("responses") or []
    if any(
        not isinstance(response, Mapping)
        or not isinstance(response.get("terminal"), Mapping)
        or response["terminal"].get("event") != "done"
        for response in stream_responses
    ):
        raise ValueError("fake_stream_terminal_invalid")
    return {
        "decision": "provider_campaign_required",
        "main_provider_semantics": "not_measured",
        "manifest_schema_version": str(manifests[-1]["schema_version"]),
        "continuity_capsule_count": 1,
        "assistant_final_count": 1,
        "json_stream_contract_equal": True,
        "assistant_provenance_preserved": True,
        "epistemic_fields_equal": True,
        "raw_stimmung_in_main_payload": False,
        "final_lock_contract": "unchanged",
    }


def content_free_call_record(
    schedule_item: Mapping[str, Any],
    provider_result: Mapping[str, Any],
) -> dict[str, Any]:
    raw_text = str(provider_result.get("raw_text") or "")
    return {
        "artifact_version": ARTIFACT_VERSION,
        "record_type": "call",
        "sequence": int(schedule_item.get("sequence") or 0),
        "case_id": str(schedule_item.get("case_id") or ""),
        "repetition": int(schedule_item.get("repetition") or 0),
        "blinded_arm": str(schedule_item.get("blinded_arm") or ""),
        "status": "ok" if provider_result.get("ok") else "error",
        "status_code": provider_result.get("status_code"),
        "finish_reason": str(provider_result.get("finish_reason") or "unknown")[:40],
        "observed_model": str(provider_result.get("model") or "")[:120],
        "observed_provider": str(provider_result.get("provider") or "")[:80],
        "response_chars": len(raw_text),
        "response_sha256": _sha256_text(raw_text) if raw_text else "",
        "usage": {
            key: int(value)
            for key, value in dict(provider_result.get("usage") or {}).items()
            if key in {"prompt_tokens", "completion_tokens", "reasoning_tokens", "total_tokens"}
            and isinstance(value, int)
        },
        "cost_usd": provider_result.get("cost_estimate_usd"),
        "raw_dialogue_included": False,
        "raw_prompt_included": False,
        "raw_response_included": False,
        "exception_text_included": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Lot 4C.4 frozen final-wording provider diagnostic"
    )
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--freeze-commit", required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if not args.dry_run:
        raise SystemExit("live execution requires a separate explicit GO")
    protocol = build_protocol(args.repo_root, freeze_commit=args.freeze_commit)
    summary = validate_protocol(protocol, args.repo_root)
    print(
        _compact_json(
            {
                "status": "ready",
                "decision": protocol["phase_a_decision"],
                "protocol_sha256": _sha256_text(_compact_json(protocol)),
                **summary,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
