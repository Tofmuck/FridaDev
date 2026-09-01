from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from core import token_utils

from benchmark.suites.stimmung import final_wording_diagnostic as v1


CORPUS_SCHEMA_VERSION = "stimmung_final_wording_corpus_v2"
THRESHOLD_SCHEMA_VERSION = "stimmung_final_wording_thresholds_v2"
PROTOCOL_VERSION = "lot4c4_final_wording_bounded_candidate_v2_4"
ARTIFACT_VERSION = "lot4c4_final_wording_bounded_results_v2_4"
SUPERSEDED_V23_PROTOCOL_VERSION = "lot4c4_final_wording_provider_campaign_v2_3"
DEFAULT_FIXTURE = "stimmung_final_wording_corpus_v2.json"
DEFAULT_FREEZE_MANIFEST = "stimmung_final_wording_freeze_v2_4.json"

ACTIVE_MAIN_MODEL = "openai/gpt-5.1"
ACTIVE_MAX_TOKENS = 8192
ACTIVE_REASONING = {"effort": "high", "exclude": True}
ACTIVE_TIMEOUT_S = 900
REQUIRED_ENDPOINT_CAPABILITIES = {
    "reasoning": ("reasoning",),
    "output_token_limit": ("max_tokens",),
}
REPETITIONS = 2
REPETITION_RATIONALE = "minimum_repeat_to_expose_single_decode_variance"
EXPECTED_CASES = 14
EXPECTED_PROVIDER_CASES = 12
EXPECTED_TRANSITION_CASES = 6
EXPECTED_COUNTERCASES = 6
EXPECTED_CAUSAL_COMPARISONS = EXPECTED_TRANSITION_CASES * REPETITIONS
EXPECTED_ABSOLUTE_OBSERVATIONS = 0
EXPECTED_CALLS = EXPECTED_CAUSAL_COMPARISONS * 2
ABSOLUTE_CALL_CAP = EXPECTED_CALLS
ABSOLUTE_COST_CAP_USD = 3.0
PRICING_OBSERVED_AT = "2026-08-31"
PRICING_SOURCE = "https://openrouter.ai/api/v1/models"
PRICING_USD_PER_TOKEN = {"prompt": 0.00000125, "completion": 0.00001}
COST_SAFETY_MARGIN = 1.10
BASELINE_HEAD = "e51de209a487c80a7939a283d4e49ad866811cd6"
V1_CORPUS_SHA256 = "de8f63c6de4ec8d51a47db868e188b06a83d66ed8b07fb2278a5a47734f4f139"
V1_HARNESS_SHA256 = "2c34180f0d05d3ca2502f8ca71b23065749251945d5f8eb644ef44ba01288c7b"
V2_FREEZE_SHA256 = "4a682d89d5070bc7ff928aa36696220fcac662bc26ce7fbbba4066f07901e672"
V21_FREEZE_SHA256 = "a3afa9e8537311a107694dfc1e780741cb37676a3afbd789e3917d3e48cbab10"
V22_FREEZE_SHA256 = "428fd763c65f2692069b569ee740631642abd06214cd92e3f23bbd31915a99a2"
V23_FREEZE_SHA256 = "77bf7bf67c8bcb1b61ae18a8ec3f86a3f0cffa4b2eb1dc82334e2a4b0f7ccb70"

_BOUNDED_ALLOWED_OPERATIONS = ("lexical_choice", "connectors", "rhythm")
_BOUNDED_PRESERVED = (
    "requested_answer",
    "facts",
    "sources",
    "hypotheses",
    "inferences",
    "conclusions",
    "actions",
    "certainty_degrees",
    "proof_regimes",
    "hard_guards",
)
_BOUNDED_FORBIDDEN = (
    "add_or_remove_proposition",
    "add_or_remove_reservation",
    "add_or_remove_reason",
    "add_or_remove_conclusion",
    "add_diagnosis",
    "add_unsolicited_advice",
    "psychological_attribution",
    "mask_question_request_risk_or_action",
)
BOUNDED_ENUNCIATION_POLICY = {
    "version": "surface_only_v1",
    "priority": "direct_answer_and_substance_first",
    "allowed_operations": _BOUNDED_ALLOWED_OPERATIONS,
    "preserved": _BOUNDED_PRESERVED,
    "forbidden": _BOUNDED_FORBIDDEN,
    "fallback": "no_op_if_substance_risk",
}
BOUNDED_ENUNCIATION_POLICY_SHA256 = (
    "72d7b887b49f0e8d7d3e2ff0ba91a65e2772448f885f03455ffbd47f45b2d143"
)
OBSERVABILITY_POLICY_VERSION = "surface_only_v1"

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
V21_MUTATION_MATRIX = (
    "completed_sequence_recalled_on_resume",
    "attempt_started_sequence_recalled_on_resume",
    "attempt_counter_reset_between_invocations",
    "prior_cost_forgotten_on_resume",
    "attempt_37_allowed",
    "cumulative_cost_cap_exceeded_after_resume",
    "partial_evidence_deleted_after_interruption",
    "ledger_not_fsynced_before_provider_boundary",
    "freeze_changed_during_resume",
    "unknown_outcome_counted_as_free_or_successful",
    "rating_packet_created_from_incomplete_campaign",
    "codex_assistance_claimed_as_human_review",
    "codex_assisted_rating_finalized_without_tof_ratification",
    "ratification_fingerprint_mismatch",
    "private_mapping_exposed_in_review_export",
    "unblinding_before_complete_validation",
    "raw_content_or_open_reason_code_in_durable_artifact",
)
V22_MUTATION_MATRIX = (
    "sampling_parameter_reintroduced",
    "false_compatible_endpoint_accepted",
    "provider_post_before_capability_preflight",
    "http_404_masked_as_transport_error",
    "calls_continue_after_failed_canary",
    "canary_added_as_call_37",
    "retry_or_fallback_added",
    "corpus_scorer_or_messages_changed",
    "v2_1_history_removed_or_reused",
)
V23_MUTATION_MATRIX = (
    "stop_parameter_reintroduced",
    "artificial_structured_outputs_capability_required",
    "required_capability_not_sent_by_payload",
    "sampling_parameter_reintroduced",
    "provider_post_before_capability_preflight",
    "calls_continue_after_failed_canary",
    "canary_added_as_call_37",
    "retry_or_fallback_added",
    "corpus_scorer_or_messages_changed",
    "v2_2_history_removed_or_reused",
)
V24_MUTATION_MATRIX = (
    "prudence_role_reintroduced",
    "substance_priority_removed",
    "proposition_reservation_reason_or_conclusion_mutation_allowed",
    "psychological_attribution_allowed",
    "no_op_fallback_removed",
    "raw_stimmung_injected",
    "countercase_none_path_changed",
    "caller_aggregator_validation_model_settings_or_guards_changed",
    "candidate_differs_from_frozen_policy",
    "single_critical_failure_accepted",
    "call_count_exceeds_24",
    "cost_cap_exceeds_3_usd",
)

_FIXTURE_TOP_KEYS = {
    "schema_version",
    "corpus_id",
    "language",
    "derivation",
    "campaign_contract",
    "thresholds",
    "case_overrides",
    "mutation_matrix",
}
_OVERRIDE_KEYS = {"source_case_id", "id", "dialogue", "factual_basis"}
_FACT_KEYS = {"id", "literal", "visible_at"}
_VISIBLE_AT_KEYS = {"source", "index"}
_RAW_STIMMUNG_MARKERS = v1._RAW_STIMMUNG_MARKERS
_HEX = frozenset("0123456789abcdef")


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


def fixture_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures" / DEFAULT_FIXTURE


def freeze_manifest_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures" / DEFAULT_FREEZE_MANIFEST


def _v1_fixture_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v1.json"


def _v2_freeze_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2.json"


def _v21_freeze_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_1.json"


def _v22_freeze_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_2.json"


def _v23_freeze_path(repo_root: Path) -> Path:
    return repo_root / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v2_3.json"


def _module_paths(repo_root: Path) -> dict[str, Path]:
    base = repo_root / "benchmark/suites/stimmung"
    return {
        "protocol": base / "final_wording_protocol_v2.py",
        "execution": base / "final_wording_execution_v2.py",
        "rating": base / "final_wording_rating_v2.py",
        "v1_message_builder": base / "final_wording_diagnostic.py",
        "openrouter_client": repo_root / "benchmark/core/openrouter.py",
    }


def _load_fixture(repo_root: Path) -> dict[str, Any]:
    raw = json.loads(fixture_path(repo_root).read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("corpus_root_not_object")
    return raw


def _validate_fixture_header(raw: Mapping[str, Any], repo_root: Path) -> None:
    _exact_keys(raw, _FIXTURE_TOP_KEYS, "corpus_fields_invalid")
    if raw.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("corpus_schema_invalid")
    if raw.get("corpus_id") != "lot4c4-final-wording-fr-v2" or raw.get("language") != "fr":
        raise ValueError("corpus_identity_invalid")
    derivation = _exact_keys(
        raw.get("derivation"),
        {"source_path", "source_sha256", "source_protocol_status", "provider_calls_observed"},
        "corpus_derivation_invalid",
    )
    if derivation != {
        "source_path": "benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v1.json",
        "source_sha256": V1_CORPUS_SHA256,
        "source_protocol_status": "superseded_before_provider_calls",
        "provider_calls_observed": 0,
    }:
        raise ValueError("corpus_derivation_changed")
    if _sha256_file(_v1_fixture_path(repo_root)) != V1_CORPUS_SHA256:
        raise ValueError("v1_corpus_fingerprint_changed")
    if raw.get("campaign_contract") != {
        "causal_transition": "control_and_treatment_share_provider_visible_matter_and_differ_only_by_the_bounded_enunciation_directive",
        "absolute_countercase": "one_runtime_active_arm_only",
        "exact_output_expected": False,
        "semantic_regex": False,
    }:
        raise ValueError("campaign_contract_invalid")
    thresholds = _exact_keys(
        raw.get("thresholds"),
        {
            "schema_version",
            "transition_delicacy_improvement_rate",
            "transition_formulation_improvement_rate",
            "countercase_formulation_adequacy_rate",
            "critical_zero_tolerance",
            "countercase_artificial_caution_rate",
        },
        "threshold_fields_invalid",
    )
    if thresholds != {
        "schema_version": THRESHOLD_SCHEMA_VERSION,
        "transition_delicacy_improvement_rate": 0.8,
        "transition_formulation_improvement_rate": 0.75,
        "countercase_formulation_adequacy_rate": 1.0,
        "critical_zero_tolerance": [
            "psychologization",
            "certainty_change",
            "truth_or_evidence_change",
            "masked_target",
        ],
        "countercase_artificial_caution_rate": 0.0,
    }:
        raise ValueError("thresholds_changed")


def _resolved_corpus(repo_root: Path) -> dict[str, Any]:
    raw = _load_fixture(repo_root)
    _validate_fixture_header(raw, repo_root)
    source = v1.load_corpus(repo_root)
    source_by_id = {str(case["id"]): case for case in source["cases"]}
    overrides = raw.get("case_overrides")
    if not isinstance(overrides, list) or len(overrides) != EXPECTED_CASES:
        raise ValueError("case_override_count_invalid")
    resolved_cases: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    seen_ids: set[str] = set()
    for override_raw in overrides:
        override = _exact_keys(override_raw, _OVERRIDE_KEYS, "case_override_fields_invalid")
        source_id = _bounded_text(override.get("source_case_id"), maximum=40)
        case_id = _bounded_text(override.get("id"), maximum=40)
        if source_id in seen_sources or case_id in seen_ids:
            raise ValueError("case_override_duplicate")
        source_case = source_by_id.get(source_id)
        if source_case is None:
            raise ValueError("case_override_source_unknown")
        seen_sources.add(source_id)
        seen_ids.add(case_id)
        case = copy.deepcopy(source_case)
        case["id"] = case_id
        case["version"] = "v2"
        case["dialogue"] = copy.deepcopy(override["dialogue"])
        case["epistemic_matter"]["factual_basis"] = copy.deepcopy(override["factual_basis"])
        resolved_cases.append(case)
    if seen_sources != set(source_by_id):
        raise ValueError("case_override_source_set_invalid")
    return {
        "schema_version": CORPUS_SCHEMA_VERSION,
        "corpus_id": raw["corpus_id"],
        "language": raw["language"],
        "derivation": copy.deepcopy(raw["derivation"]),
        "campaign_contract": copy.deepcopy(raw["campaign_contract"]),
        "measurement_taxonomy": {
            "final_text": list(FINAL_TEXT_PROPERTIES),
            "other_stage": list(OTHER_STAGE_PROPERTIES),
            "contract_only": list(CONTRACT_ONLY_PROPERTIES),
        },
        "thresholds": copy.deepcopy(raw["thresholds"]),
        "cases": resolved_cases,
        "mutation_matrix": copy.deepcopy(raw["mutation_matrix"]),
    }


def load_corpus(repo_root: Path) -> dict[str, Any]:
    corpus = _resolved_corpus(repo_root)
    validate_corpus(corpus)
    return corpus


def _validate_dialogue(case: Mapping[str, Any]) -> None:
    dialogue = _exact_keys(case.get("dialogue"), {"history", "user"}, "dialogue_fields_invalid")
    history = dialogue.get("history")
    if not isinstance(history, list) or len(history) > 4 or len(history) % 2:
        raise ValueError("dialogue_history_invalid")
    expected_role = "user"
    for message in history:
        item = _exact_keys(message, {"role", "content"}, "dialogue_message_invalid")
        if item.get("role") != expected_role:
            raise ValueError("dialogue_order_invalid")
        _bounded_text(item.get("content"), maximum=900)
        expected_role = "assistant" if expected_role == "user" else "user"
    _bounded_text(dialogue.get("user"), maximum=900)


def _validate_visible_facts(case: Mapping[str, Any]) -> int:
    facts = case.get("epistemic_matter", {}).get("factual_basis")
    if not isinstance(facts, list) or not facts:
        raise ValueError("factual_basis_invalid")
    seen: set[str] = set()
    for fact_raw in facts:
        fact = _exact_keys(fact_raw, _FACT_KEYS, "factual_basis_fields_invalid")
        fact_id = _bounded_text(fact.get("id"), maximum=80)
        literal = _bounded_text(fact.get("literal"), maximum=700)
        if fact_id in seen:
            raise ValueError("factual_basis_duplicate")
        seen.add(fact_id)
        visible_at = _exact_keys(
            fact.get("visible_at"), _VISIBLE_AT_KEYS, "visible_at_fields_invalid"
        )
        source = visible_at.get("source")
        index = visible_at.get("index")
        if source == "user":
            if index is not None:
                raise ValueError("visible_at_user_index_invalid")
            visible_content = str(case["dialogue"]["user"])
        elif source == "history":
            if not isinstance(index, int) or isinstance(index, bool):
                raise ValueError("visible_at_history_index_invalid")
            history = case["dialogue"]["history"]
            if not 0 <= index < len(history):
                raise ValueError("visible_at_history_index_invalid")
            visible_content = str(history[index]["content"])
        else:
            raise ValueError("visible_at_source_invalid")
        if literal not in visible_content:
            raise ValueError("required_fact_not_provider_visible")
    return len(facts)


def validate_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    expected_top = {
        "schema_version",
        "corpus_id",
        "language",
        "derivation",
        "campaign_contract",
        "measurement_taxonomy",
        "thresholds",
        "cases",
        "mutation_matrix",
    }
    _exact_keys(corpus, expected_top, "resolved_corpus_fields_invalid")
    if corpus.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("corpus_schema_invalid")
    if corpus.get("corpus_id") != "lot4c4-final-wording-fr-v2":
        raise ValueError("corpus_id_invalid")
    cases = corpus.get("cases")
    if not isinstance(cases, list) or len(cases) != EXPECTED_CASES:
        raise ValueError("case_count_invalid")
    ids: set[str] = set()
    provider_count = 0
    transition_count = 0
    counter_count = 0
    provider_visible_fact_count = 0
    for case_raw in cases:
        case = _exact_keys(case_raw, v1._CASE_KEYS, "case_fields_invalid")
        case_id = _bounded_text(case.get("id"), maximum=40)
        if not case_id.startswith("L4C4-FW2-") or case.get("version") != "v2":
            raise ValueError("case_identity_invalid")
        if case_id in ids:
            raise ValueError("case_id_duplicate")
        ids.add(case_id)
        _validate_dialogue(case)
        fact_count = _validate_visible_facts(case)
        provider = case.get("provider_eligible") is True
        provider_count += int(provider)
        if provider:
            provider_visible_fact_count += fact_count
            if case.get("enunciation_state") == "transition_delicate":
                transition_count += 1
            else:
                counter_count += 1
        expectations = case.get("expectations")
        if not isinstance(expectations, Mapping) or "expected_response" in _compact_json(expectations):
            raise ValueError("expectations_invalid")
        if case.get("enunciation_state") not in v1.ENUNCIATION_STATES:
            raise ValueError("enunciation_state_invalid")
    if provider_count != EXPECTED_PROVIDER_CASES:
        raise ValueError("provider_case_count_invalid")
    if transition_count != EXPECTED_TRANSITION_CASES or counter_count != EXPECTED_COUNTERCASES:
        raise ValueError("campaign_category_count_invalid")
    if provider_visible_fact_count != 17:
        raise ValueError("provider_visible_fact_count_invalid")
    serialized = _compact_json(corpus)
    for forbidden in (
        "[JUGEMENT HERMENEUTIQUE]",
        "Consigne d'enonciation:",
        "Effet d'enonciation:",
        "expected_response",
    ):
        if forbidden in serialized:
            raise ValueError("corpus_copies_runtime_or_exact_output")
    return {
        "case_count": len(cases),
        "provider_case_count": provider_count,
        "causal_transition_case_count": transition_count,
        "absolute_countercase_count": counter_count,
        "provider_visible_fact_count": provider_visible_fact_count,
    }


def case_by_id(corpus: Mapping[str, Any], case_id: Any) -> Mapping[str, Any]:
    for case in corpus.get("cases", []):
        if isinstance(case, Mapping) and case.get("id") == case_id:
            return case
    raise ValueError("unknown_case_id")


def bounded_candidate_instruction() -> str:
    policy = BOUNDED_ENUNCIATION_POLICY
    if (
        set(policy)
        != {"version", "priority", "allowed_operations", "preserved", "forbidden", "fallback"}
        or policy["version"] != "surface_only_v1"
        or policy["priority"] != "direct_answer_and_substance_first"
        or policy["allowed_operations"] != _BOUNDED_ALLOWED_OPERATIONS
        or policy["preserved"] != _BOUNDED_PRESERVED
        or policy["forbidden"] != _BOUNDED_FORBIDDEN
        or policy["fallback"] != "no_op_if_substance_risk"
    ):
        raise ValueError("bounded_enunciation_policy_invalid")
    rendered = (
        "Consigne d'enonciation: politique=surface_only_v1; "
        "priorite=repondre d'abord directement a la demande, sous autorite des faits, sources, "
        "hypotheses, inferences, conclusions, actions, degres de certitude, regimes de preuve et "
        "hard guards; operations_permises=choix lexical, connecteurs et rythme, a longueur "
        "comparable, avec au plus une breve reprise dialogique; fond_invariant=n'ajoute ni ne "
        "retire proposition, reserve, raison ou conclusion, diagnostic, conseil non demande ou "
        "attribution psychologique, et ne masque aucune question, demande, risque ou action; repli=si "
        "l'ajustement risque de toucher au fond, n'ajuste rien."
    )
    if _sha256_text(rendered) != BOUNDED_ENUNCIATION_POLICY_SHA256:
        raise ValueError("bounded_enunciation_policy_fingerprint_invalid")
    return rendered


def _replace_runtime_instruction(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    replaced = copy.deepcopy(messages)
    occurrences = 0
    for message in replaced:
        if message.get("role") != "system":
            continue
        lines = str(message.get("content") or "").splitlines()
        for index, line in enumerate(lines):
            if line.startswith("Consigne d'enonciation:"):
                lines[index] = bounded_candidate_instruction()
                occurrences += 1
        message["content"] = "\n".join(lines)
    if occurrences != 1:
        raise ValueError("runtime_enunciation_instruction_cardinality_invalid")
    return replaced


def _runtime_variant(case: Mapping[str, Any], variant: str) -> str:
    if case.get("enunciation_state") == "transition_delicate" and variant in {
        "runtime_current",
        "bounded_candidate",
    }:
        return "treatment"
    raise ValueError("variant_invalid")


def build_messages(case: Mapping[str, Any], variant: str) -> list[dict[str, Any]]:
    runtime_variant = _runtime_variant(case, variant)
    messages = v1._build_messages(case, runtime_variant)
    if variant == "bounded_candidate":
        messages = _replace_runtime_instruction(messages)
    _validate_provider_visible_matter(case, messages)
    return messages


def countercase_runtime_messages(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    if case.get("enunciation_state") == "transition_delicate":
        raise ValueError("countercase_required")
    return v1._build_messages(case, "treatment")


def v23_countercase_runtime_messages(case: Mapping[str, Any]) -> list[dict[str, Any]]:
    return countercase_runtime_messages(case)


def _validate_provider_visible_matter(
    case: Mapping[str, Any], messages: Sequence[Mapping[str, Any]]
) -> None:
    history = case["dialogue"]["history"]
    expected_user_index = 1 + len(history)
    if len(messages) < expected_user_index + 2:
        raise ValueError("provider_messages_incomplete")
    for fact in case["epistemic_matter"]["factual_basis"]:
        visible_at = fact["visible_at"]
        if visible_at["source"] == "user":
            message_index = expected_user_index
            expected_role = "user"
        else:
            message_index = 1 + int(visible_at["index"])
            expected_role = history[int(visible_at["index"])]["role"]
        message = messages[message_index]
        if message.get("role") != expected_role or fact["literal"] not in str(
            message.get("content") or ""
        ):
            raise ValueError("required_fact_not_provider_visible")


def _variant_order(case_index: int, repetition: int) -> tuple[str, str]:
    control_first = (case_index + repetition) % 2 == 0
    return (
        ("runtime_current", "bounded_candidate")
        if control_first
        else ("bounded_candidate", "runtime_current")
    )


def _payload(messages: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "model": ACTIVE_MAIN_MODEL,
        "messages": messages,
        "max_tokens": ACTIVE_MAX_TOKENS,
        "reasoning": dict(ACTIVE_REASONING),
        "provider": {"allow_fallbacks": False, "require_parameters": True},
    }


def _build_request_schedule(repo_root: Path) -> list[dict[str, Any]]:
    corpus = load_corpus(repo_root)
    provider_cases = [
        case
        for case in corpus["cases"]
        if case["provider_eligible"] and case["enunciation_state"] == "transition_delicate"
    ]
    schedule: list[dict[str, Any]] = []
    sequence = 0
    for repetition in range(1, REPETITIONS + 1):
        for case_index, case in enumerate(provider_cases, start=1):
            variants = _variant_order(case_index, repetition)
            for slot_index, variant in enumerate(variants):
                sequence += 1
                messages = build_messages(case, variant)
                prompt_tokens = int(token_utils.estimate_tokens(messages, ACTIVE_MAIN_MODEL))
                calculated_ceiling = round(
                    (prompt_tokens * PRICING_USD_PER_TOKEN["prompt"])
                    + (ACTIVE_MAX_TOKENS * PRICING_USD_PER_TOKEN["completion"]),
                    8,
                )
                schedule.append(
                    {
                        "sequence": sequence,
                        "case_id": case["id"],
                        "repetition": repetition,
                        "comparison_kind": "causal_transition",
                        "blind_slot": "A" if slot_index == 0 else "B",
                        "variant": variant,
                        "messages_sha256": _sha256_text(_compact_json(messages)),
                        "prompt_token_estimate": prompt_tokens,
                        "calculated_ceiling_cost_usd": calculated_ceiling,
                        "payload": _payload(messages),
                    }
                )
    if len(schedule) != EXPECTED_CALLS:
        raise ValueError("schedule_call_count_invalid")
    return schedule


def _expected_common_payload() -> dict[str, Any]:
    payload = _payload([])
    payload.pop("messages")
    return payload


def validate_schedule(
    corpus: Mapping[str, Any], schedule: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    validate_corpus(corpus)
    if not isinstance(schedule, list) or len(schedule) != EXPECTED_CALLS:
        raise ValueError("schedule_cardinality_invalid")
    expected_keys = {
        "sequence",
        "case_id",
        "repetition",
        "comparison_kind",
        "blind_slot",
        "variant",
        "messages_sha256",
        "prompt_token_estimate",
        "calculated_ceiling_cost_usd",
        "payload",
    }
    causal: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = {}
    absolute: set[tuple[str, int]] = set()
    raw_stimmung_occurrences = 0
    for expected_sequence, item_raw in enumerate(schedule, start=1):
        item = _exact_keys(item_raw, expected_keys, "schedule_item_fields_invalid")
        if item.get("sequence") != expected_sequence:
            raise ValueError("schedule_sequence_invalid")
        case = case_by_id(corpus, item.get("case_id"))
        if case.get("provider_eligible") is not True or item.get("repetition") not in {1, 2}:
            raise ValueError("schedule_case_or_repetition_invalid")
        payload = item.get("payload")
        if not isinstance(payload, Mapping):
            raise ValueError("schedule_payload_invalid")
        common = dict(payload)
        messages = common.pop("messages", None)
        if common != _expected_common_payload() or not isinstance(messages, list):
            raise ValueError("schedule_runtime_policy_invalid")
        if item.get("messages_sha256") != _sha256_text(_compact_json(messages)):
            raise ValueError("schedule_message_fingerprint_invalid")
        prompt_tokens = int(token_utils.estimate_tokens(messages, ACTIVE_MAIN_MODEL))
        if item.get("prompt_token_estimate") != prompt_tokens:
            raise ValueError("schedule_prompt_estimate_invalid")
        expected_cost = round(
            (prompt_tokens * PRICING_USD_PER_TOKEN["prompt"])
            + (ACTIVE_MAX_TOKENS * PRICING_USD_PER_TOKEN["completion"]),
            8,
        )
        if item.get("calculated_ceiling_cost_usd") != expected_cost:
            raise ValueError("schedule_cost_ceiling_invalid")
        _validate_provider_visible_matter(case, messages)
        runtime_variant = _runtime_variant(case, str(item.get("variant") or ""))
        v1._validate_message_contract(
            messages,
            state=str(case["enunciation_state"]),
            variant=runtime_variant,
        )
        serialized = _compact_json(messages)
        raw_stimmung_occurrences += sum(serialized.count(marker) for marker in _RAW_STIMMUNG_MARKERS)
        key = (str(case["id"]), int(item["repetition"]))
        if item.get("comparison_kind") == "causal_transition":
            if case["enunciation_state"] != "transition_delicate":
                raise ValueError("causal_non_transition_invalid")
            if item.get("blind_slot") not in {"A", "B"} or item.get("variant") not in {
                "runtime_current",
                "bounded_candidate",
            }:
                raise ValueError("causal_arm_invalid")
            variants = causal.setdefault(key, {})
            if item["variant"] in variants:
                raise ValueError("causal_variant_duplicate")
            variants[str(item["variant"])] = item
        else:
            raise ValueError("comparison_kind_invalid")
    unauthorized = 0
    identical = 0
    for variants in causal.values():
        if set(variants) != {"runtime_current", "bounded_candidate"}:
            raise ValueError("causal_pair_incomplete")
        current = variants["runtime_current"]["payload"]["messages"]
        candidate = variants["bounded_candidate"]["payload"]["messages"]
        if current == candidate:
            identical += 1
        if v1._normalized_messages_for_pair(current) != v1._normalized_messages_for_pair(
            candidate
        ):
            unauthorized += 1
    if len(causal) != EXPECTED_CAUSAL_COMPARISONS:
        raise ValueError("causal_comparison_count_invalid")
    if len(absolute) != EXPECTED_ABSOLUTE_OBSERVATIONS:
        raise ValueError("absolute_observation_count_invalid")
    if unauthorized:
        raise ValueError("unauthorized_paired_difference")
    if identical:
        raise ValueError("identical_arms_claimed_causal")
    if raw_stimmung_occurrences:
        raise ValueError("raw_stimmung_in_main_payload")
    return {
        "causal_call_count": len(causal) * 2,
        "absolute_call_count": len(absolute),
        "causal_comparison_count": len(causal),
        "absolute_observation_count": len(absolute),
        "unauthorized_difference_count": unauthorized,
        "identical_causal_pair_count": identical,
        "raw_stimmung_occurrence_count": raw_stimmung_occurrences,
    }


def _schedule_fingerprint(schedule: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            key: item[key]
            for key in (
                "sequence",
                "case_id",
                "repetition",
                "comparison_kind",
                "blind_slot",
                "variant",
                "messages_sha256",
                "prompt_token_estimate",
                "calculated_ceiling_cost_usd",
            )
        }
        for item in schedule
    ]


def _build_unfrozen_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    if not _is_commit(freeze_commit):
        raise ValueError("freeze_commit_invalid")
    corpus = load_corpus(repo_root)
    schedule = _build_request_schedule(repo_root)
    validate_schedule(corpus, schedule)
    prompt_tokens = sum(int(item["prompt_token_estimate"]) for item in schedule)
    prompt_cost = round(prompt_tokens * PRICING_USD_PER_TOKEN["prompt"], 8)
    completion_tokens = EXPECTED_CALLS * ACTIVE_MAX_TOKENS
    completion_cost = round(completion_tokens * PRICING_USD_PER_TOKEN["completion"], 8)
    total_ceiling = round(prompt_cost + completion_cost, 8)
    budget = round(total_ceiling * COST_SAFETY_MARGIN, 8)
    if budget > ABSOLUTE_COST_CAP_USD:
        raise ValueError("budget_with_safety_margin_exceeds_absolute_cap")
    paths = _module_paths(repo_root)
    inputs = {
        "corpus_v2_sha256": _sha256_file(fixture_path(repo_root)),
        "corpus_v1_sha256": _sha256_file(_v1_fixture_path(repo_root)),
        "superseded_freeze_v2_sha256": _sha256_file(_v2_freeze_path(repo_root)),
        "superseded_freeze_v2_1_sha256": _sha256_file(_v21_freeze_path(repo_root)),
        "superseded_freeze_v2_2_sha256": _sha256_file(_v22_freeze_path(repo_root)),
        "superseded_freeze_v2_3_sha256": _sha256_file(_v23_freeze_path(repo_root)),
        "protocol_module_sha256": _sha256_file(paths["protocol"]),
        "execution_module_sha256": _sha256_file(paths["execution"]),
        "rating_module_sha256": _sha256_file(paths["rating"]),
        "openrouter_client_sha256": _sha256_file(paths["openrouter_client"]),
        "v1_message_builder_sha256": _sha256_file(paths["v1_message_builder"]),
        "main_system_prompt_sha256": _sha256_file(repo_root / "app/prompts/main_system.txt"),
        "main_hermeneutical_prompt_sha256": _sha256_file(
            repo_root / "app/prompts/main_hermeneutical.txt"
        ),
        "chat_prompt_context_sha256": _sha256_file(repo_root / "app/core/chat_prompt_context.py"),
        "continuity_capsule_sha256": _sha256_file(repo_root / "app/core/continuity_capsule.py"),
        "main_payload_builder_sha256": _sha256_file(repo_root / "app/core/chat_main_payload.py"),
    }
    if inputs["corpus_v1_sha256"] != V1_CORPUS_SHA256:
        raise ValueError("v1_corpus_fingerprint_changed")
    if inputs["v1_message_builder_sha256"] != V1_HARNESS_SHA256:
        raise ValueError("v1_message_builder_fingerprint_changed")
    if inputs["superseded_freeze_v2_sha256"] != V2_FREEZE_SHA256:
        raise ValueError("superseded_v2_freeze_fingerprint_changed")
    if inputs["superseded_freeze_v2_1_sha256"] != V21_FREEZE_SHA256:
        raise ValueError("superseded_v2_1_freeze_fingerprint_changed")
    if inputs["superseded_freeze_v2_2_sha256"] != V22_FREEZE_SHA256:
        raise ValueError("superseded_v2_2_freeze_fingerprint_changed")
    if inputs["superseded_freeze_v2_3_sha256"] != V23_FREEZE_SHA256:
        raise ValueError("superseded_v2_3_freeze_fingerprint_changed")
    return {
        "protocol_version": PROTOCOL_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "campaign_kind": "causal_transition_current_runtime_vs_bounded_candidate",
        "phase_a_status": "provider_campaign_required",
        "freeze_commit": freeze_commit,
        "baseline_head": BASELINE_HEAD,
        "supersedes_protocol_version": SUPERSEDED_V23_PROTOCOL_VERSION,
        "historical_v1_protocol_version": v1.PROTOCOL_VERSION,
        "v2_1_campaign_history": {
            "attempted_call_count": 36,
            "http_404_count": 36,
            "provider_inference_count": 0,
            "observed_cost_usd": 0.0,
            "ledger_conservative_cost_usd": 3.2567175,
            "ledger_conservative_cost_billed": False,
            "reusable": False,
        },
        "v2_2_preflight_history": {
            "metadata_get_count": 1,
            "metadata_http_status": 200,
            "endpoint_count": 5,
            "compatible_endpoint_count": 0,
            "provider_post_count": 0,
            "provider_inference_count": 0,
            "observed_cost_usd": 0.0,
            "campaign_started": False,
            "reusable": False,
        },
        "v2_3_ratified_history": {
            "attempted_call_count": 36,
            "valid_call_count": 36,
            "countercase_adequate_count": 12,
            "transition_delicacy_improved_count": 5,
            "transition_formulation_improved_count": 6,
            "critical_failure_count": 2,
            "classification": "partial",
            "ratified_by": "tof",
            "raw_material_retained": False,
            "reusable": False,
        },
        "v2_provider_calls_observed": 0,
        "v1_provider_calls_observed": 0,
        "corpus_id": corpus["corpus_id"],
        "input_fingerprints": inputs,
        "schedule_sha256": _sha256_text(_compact_json(_schedule_fingerprint(schedule))),
        "model": ACTIVE_MAIN_MODEL,
        "max_tokens": ACTIVE_MAX_TOKENS,
        "reasoning": dict(ACTIVE_REASONING),
        "required_endpoint_capabilities": {
            key: list(values) for key, values in REQUIRED_ENDPOINT_CAPABILITIES.items()
        },
        "candidate_policy": {
            "version": BOUNDED_ENUNCIATION_POLICY["version"],
            "sha256": BOUNDED_ENUNCIATION_POLICY_SHA256,
            "active_in_runtime": False,
        },
        "observability_policy": {
            "current_runtime_policy_version": "unobserved",
            "candidate_version": OBSERVABILITY_POLICY_VERSION,
            "active_in_runtime": False,
            "future_cutover_propagation_required": True,
        },
        "timeout_s": ACTIVE_TIMEOUT_S,
        "transport_policy": {
            "mode": "standard",
            "batch": False,
            "flex": False,
            "priority": False,
            "retry_count": 0,
            "automatic_model_fallback": False,
            "provider_fallbacks": False,
            "require_parameters": True,
            "model_endpoint_preflight": True,
            "canary_sequence": 1,
        },
        "additional_stage_calls": {
            "validation": 0,
            "stimmung": 0,
            "fallback": 0,
            "model_judge": 0,
        },
        "repetitions": REPETITIONS,
        "repetition_rationale": REPETITION_RATIONALE,
        "case_count": EXPECTED_CASES,
        "provider_case_count": EXPECTED_PROVIDER_CASES,
        "causal_transition_case_count": EXPECTED_TRANSITION_CASES,
        "absolute_countercase_count": EXPECTED_COUNTERCASES,
        "causal_comparison_count": EXPECTED_CAUSAL_COMPARISONS,
        "absolute_observation_count": EXPECTED_ABSOLUTE_OBSERVATIONS,
        "expected_call_count": EXPECTED_CALLS,
        "absolute_call_cap": ABSOLUTE_CALL_CAP,
        "prompt_token_estimate_sum": prompt_tokens,
        "completion_token_ceiling": completion_tokens,
        "pricing_observed_at": PRICING_OBSERVED_AT,
        "pricing_source": PRICING_SOURCE,
        "pricing_usd_per_token": dict(PRICING_USD_PER_TOKEN),
        "calculated_prompt_cost_usd": prompt_cost,
        "calculated_completion_ceiling_cost_usd": completion_cost,
        "calculated_total_ceiling_cost_usd": total_ceiling,
        "cost_safety_margin": COST_SAFETY_MARGIN,
        "budget_with_safety_margin_usd": budget,
        "absolute_cost_cap_usd": ABSOLUTE_COST_CAP_USD,
        "rating_policy": {
            "method": "separate_blinded_structured_rating",
            "runner_generates_ratings": False,
            "mapping_hidden_until_rating_validation": True,
            "review_export_separate_from_private_mapping": True,
            "tof_human_review": "direct_human_condition",
            "codex_assisted_review_for_tof": "human_ratification_required",
            "semantic_regex": False,
            "presence_scored_from_final_text": False,
        },
        "decision_rules": {
            "campaign_complete_before_rating": "human_rating_required",
            "ambiguous_started_attempt": "campaign_incomplete",
            "codex_assisted_before_tof_ratification": "human_ratification_required",
            "no_authoritative_provider_results": "provider_campaign_required",
            "complete_provider_and_human_evidence_meets_thresholds": "pass",
            "complete_provider_and_human_evidence_misses_thresholds": "fail",
            "provider_or_rating_evidence_incomplete": "inconclusive",
        },
        "artifact_policy": {
            "temporary_raw_directory_required": True,
            "temporary_file_mode": "0600",
            "private_directory_mode": "0700",
            "atomic_checkpoint_before_each_call": True,
            "deterministic_live_campaign_paths_from_freeze_commit": True,
            "resume_completed_attempts_without_recall": True,
            "ambiguous_attempt_costed_at_call_ceiling": True,
            "review_export_contains_blind_packet_only": True,
            "durable_content_free": True,
            "raw_dialogue_in_durable_artifact": False,
            "raw_prompt_in_durable_artifact": False,
            "raw_provider_response_in_durable_artifact": False,
            "temporary_raw_deleted_after_valid_finalization": True,
        },
        "v2_1_mutation_matrix": list(V21_MUTATION_MATRIX),
        "v2_2_mutation_matrix": list(V22_MUTATION_MATRIX),
        "v2_3_mutation_matrix": list(V23_MUTATION_MATRIX),
        "v2_4_mutation_matrix": list(V24_MUTATION_MATRIX),
    }


def expected_freeze_manifest(protocol: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    corpus = load_corpus(repo_root)
    return {
        "schema_version": "stimmung_final_wording_freeze_v2_4",
        "status": "bounded_candidate_frozen_human_rating_required_after_provider",
        "baseline_head": BASELINE_HEAD,
        "supersedes": {
            "protocol_version": SUPERSEDED_V23_PROTOCOL_VERSION,
            "classification": "partial",
            "valid_call_count": 36,
            "countercase_adequate_count": 12,
            "transition_delicacy_improved_count": 5,
            "transition_formulation_improved_count": 6,
            "critical_failure_count": 2,
            "ratified_by": "tof",
            "cryptographic_reconstruction_claimed": False,
            "campaign_reusable": False,
        },
        "protocol_version": PROTOCOL_VERSION,
        "artifact_version": ARTIFACT_VERSION,
        "corpus": {
            "path": "benchmark/suites/stimmung/fixtures/stimmung_final_wording_corpus_v2.json",
            "sha256": protocol["input_fingerprints"]["corpus_v2_sha256"],
            "derived_v1_sha256": protocol["input_fingerprints"]["corpus_v1_sha256"],
            "case_count": EXPECTED_CASES,
            "provider_case_count": EXPECTED_PROVIDER_CASES,
            "causal_transition_case_count": EXPECTED_TRANSITION_CASES,
            "absolute_countercase_count": EXPECTED_COUNTERCASES,
        },
        "frozen_inputs": copy.deepcopy(protocol["input_fingerprints"]),
        "candidate_policy": copy.deepcopy(protocol["candidate_policy"]),
        "observability_policy": copy.deepcopy(protocol["observability_policy"]),
        "runtime_policy": {
            "model": ACTIVE_MAIN_MODEL,
            "max_tokens": ACTIVE_MAX_TOKENS,
            "reasoning": dict(ACTIVE_REASONING),
            "required_endpoint_capabilities": {
                key: list(values) for key, values in REQUIRED_ENDPOINT_CAPABILITIES.items()
            },
            "timeout_s": ACTIVE_TIMEOUT_S,
            "provider": {"allow_fallbacks": False, "require_parameters": True},
            "transport": "standard",
            "batch": False,
            "flex": False,
            "priority": False,
            "retry_count": 0,
            "model_endpoint_preflight": True,
            "canary_sequence": 1,
        },
        "schedule": {
            "sha256": protocol["schedule_sha256"],
            "repetitions": REPETITIONS,
            "causal_comparison_count": EXPECTED_CAUSAL_COMPARISONS,
            "absolute_observation_count": 0,
            "call_count": EXPECTED_CALLS,
            "absolute_call_cap": ABSOLUTE_CALL_CAP,
            "validation_calls": 0,
            "stimmung_calls": 0,
            "fallback_calls": 0,
            "model_judge_calls": 0,
        },
        "cost": {
            "pricing_observed_at": PRICING_OBSERVED_AT,
            "pricing_source": PRICING_SOURCE,
            "prompt_usd_per_token": PRICING_USD_PER_TOKEN["prompt"],
            "completion_usd_per_token": PRICING_USD_PER_TOKEN["completion"],
            "prompt_token_estimate_sum": protocol["prompt_token_estimate_sum"],
            "completion_token_ceiling": protocol["completion_token_ceiling"],
            "calculated_prompt_cost_usd": protocol["calculated_prompt_cost_usd"],
            "calculated_completion_ceiling_cost_usd": protocol[
                "calculated_completion_ceiling_cost_usd"
            ],
            "calculated_total_ceiling_cost_usd": protocol[
                "calculated_total_ceiling_cost_usd"
            ],
            "safety_margin": COST_SAFETY_MARGIN,
            "budget_with_safety_margin_usd": protocol["budget_with_safety_margin_usd"],
            "absolute_cost_cap_usd": ABSOLUTE_COST_CAP_USD,
        },
        "thresholds": copy.deepcopy(corpus["thresholds"]),
        "rating_policy": copy.deepcopy(protocol["rating_policy"]),
        "decision_rules": copy.deepcopy(protocol["decision_rules"]),
        "artifact_policy": copy.deepcopy(protocol["artifact_policy"]),
        "mutation_matrix": copy.deepcopy(corpus["mutation_matrix"]),
        "v2_1_mutation_matrix": list(V21_MUTATION_MATRIX),
        "v2_2_mutation_matrix": list(V22_MUTATION_MATRIX),
        "v2_3_mutation_matrix": list(V23_MUTATION_MATRIX),
        "v2_4_mutation_matrix": list(V24_MUTATION_MATRIX),
        "phase_limits": {
            "provider_calls_executed_before_frozen_commit": 0,
            "runtime_change": False,
            "prompt_change": False,
            "model_or_setting_change": False,
            "frontend_change": False,
            "rebuild_restart_or_deployment": False,
            "lot4oz_started": False,
        },
        "delivery_requirement": "commit_and_push_before_authorized_24_call_campaign",
    }


def _validate_freeze_manifest(protocol: Mapping[str, Any], repo_root: Path) -> None:
    manifest = json.loads(freeze_manifest_path(repo_root).read_text(encoding="utf-8"))
    if not isinstance(manifest, Mapping):
        raise ValueError("freeze_manifest_root_invalid")
    if dict(manifest) != expected_freeze_manifest(protocol, repo_root):
        raise ValueError("freeze_manifest_mismatch")


def build_protocol(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    protocol = _build_unfrozen_protocol(repo_root, freeze_commit=freeze_commit)
    _validate_freeze_manifest(protocol, repo_root)
    return protocol


def validate_protocol(protocol: Mapping[str, Any], repo_root: Path) -> dict[str, Any]:
    if protocol.get("protocol_version") != PROTOCOL_VERSION:
        raise ValueError("protocol_version_invalid")
    expected = build_protocol(repo_root, freeze_commit=str(protocol.get("freeze_commit") or ""))
    if dict(protocol) != expected:
        raise ValueError("protocol_freeze_mismatch")
    if expected["expected_call_count"] != expected["absolute_call_cap"]:
        raise ValueError("protocol_call_cap_mismatch")
    if expected["budget_with_safety_margin_usd"] > expected["absolute_cost_cap_usd"]:
        raise ValueError("protocol_cost_cap_mismatch")
    return {
        "status": expected["phase_a_status"],
        "expected_call_count": expected["expected_call_count"],
        "causal_comparison_count": expected["causal_comparison_count"],
        "absolute_observation_count": expected["absolute_observation_count"],
        "budget_with_safety_margin_usd": expected["budget_with_safety_margin_usd"],
        "absolute_cost_cap_usd": expected["absolute_cost_cap_usd"],
    }


def validate_freeze_manifest(repo_root: Path, *, freeze_commit: str) -> dict[str, Any]:
    protocol = build_protocol(repo_root, freeze_commit=freeze_commit)
    return validate_protocol(protocol, repo_root)


def build_request_schedule(
    repo_root: Path, protocol: Mapping[str, Any]
) -> list[dict[str, Any]]:
    validate_protocol(protocol, repo_root)
    schedule = _build_request_schedule(repo_root)
    if len(schedule) > int(protocol["absolute_call_cap"]):
        raise ValueError("schedule_exceeds_call_cap")
    return schedule


def protocol_sha256(protocol: Mapping[str, Any]) -> str:
    return _sha256_text(_compact_json(protocol))
