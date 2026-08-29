from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from benchmark.suites.stimmung.scorer import ALLOWED_TONES, validate_signal_payload


CORPUS_SCHEMA_VERSION = "stimmung_dialogic_corpus_v1"
THRESHOLD_SCHEMA_VERSION = "stimmung_dialogic_thresholds_v1"
DEFAULT_FIXTURE = "stimmung_dialogic_semantic_v1.json"
TURN_DEFINITION = "complete_user_assistant_pair"
AGGREGATE_MAX_SIGNALS = 4

REQUIRED_FAMILIES = (
    "emergence",
    "stabilite",
    "bascule",
    "retour_neutre",
    "alternance",
    "intensite_sans_effet_epistemique",
    "ironie",
    "citation",
    "affect_rapporte",
    "correction",
    "question",
    "demande",
    "risque",
    "action_materielle",
    "opportunite_presence",
    "contre_presence",
)
REQUIRED_COUNTER_FAMILIES = frozenset(REQUIRED_FAMILIES)
DIRECTLY_SCORABLE_FAMILIES = frozenset(REQUIRED_FAMILIES)
CRITICAL_INVARIANTS = (
    "no_psychologization",
    "reported_affect_not_internalized",
    "quoted_affect_not_internalized",
    "no_affect_epistemic_confusion",
    "question_not_masked",
    "request_not_masked",
    "risk_not_masked",
    "material_action_not_masked",
    "presence_relation_preserved",
)
CONTRACT_ONLY_INVARIANTS = frozenset(
    {
        "no_psychologization",
        "no_affect_epistemic_confusion",
        "question_not_masked",
        "request_not_masked",
        "risk_not_masked",
        "material_action_not_masked",
        "presence_relation_preserved",
    }
)
REQUIRED_MUTATIONS = frozenset(
    {
        "turn_removed",
        "turns_reversed",
        "turn_duplicated",
        "irony_literalized",
        "reported_affect_internalized",
        "quoted_affect_internalized",
        "epistemic_confusion",
        "correction_ignored",
        "stable_as_volatile",
        "shift_erased",
        "alternation_as_stable",
        "neutral_return_without_decay",
        "question_masked",
        "request_masked",
        "risk_masked",
        "material_action_masked",
        "presence_forced",
        "presence_opportunity_removed",
        "fail_open_as_healthy",
        "coverage_without_positive",
        "exact_output_added",
        "free_field_added",
        "signal_unlisted_tone_overcoded",
        "aggregate_unlisted_tone_overcoded",
        "aggregate_turn_count_underreported",
        "signal_tone_duplicated",
    }
)

_SEMANTIC_CONTEXTS = frozenset({"direct", "ironic", "quoted", "reported", "correction", "neutral", "intensity"})
_TRAJECTORY_PHASES = frozenset({"emerging", "steady", "shift_onset", "shifted", "alternating", "decay", "settled"})
_STABILITIES = frozenset({"emerging", "stable", "volatile"})
_SHIFT_STATES = frozenset({"steady", "candidate_shift", "shifted"})
_SIGNAL_STATES = frozenset({"present", "absent", "empty"})
_PRESENCE_RELATIONS = frozenset({"eligible", "forbidden", "not_applicable"})
_ATTRIBUTIONS = frozenset(
    {
        "speaker_profile",
        "assistant_profile",
        "durable_inner_state",
        "reported_affect_internalized",
        "quoted_affect_internalized",
    }
)
_DOWNSTREAM_FIELDS = ("question", "demande", "risque", "action_materielle")
_EXECUTION_STATUSES = frozenset(
    {"ok", "transport_error", "timeout", "refusal", "json_error", "schema_error", "fail_open"}
)

_TOP_KEYS = {
    "schema_version",
    "corpus_id",
    "language",
    "turn_definition",
    "thresholds",
    "dialogues",
    "mutation_matrix",
}
_DIALOGUE_KEYS = {"id", "version", "families", "human_rationale", "turns"}
_TURN_KEYS = {"turn_id", "user", "assistant"}
_EXPECTATION_KEYS = {
    "allowed_signal_states",
    "allowed_dominant_tones",
    "allowed_tones",
    "forbidden_tones",
    "strength_range",
    "semantic_context",
    "trajectory_phase",
    "aggregate",
    "forbidden_attributions",
    "epistemic_effect",
    "downstream",
    "coverage_evidence",
    "human_rationale",
}
_AGGREGATE_EXPECTATION_KEYS = {
    "allowed_presence",
    "allowed_dominant_tones",
    "allowed_active_tones",
    "allowed_stability",
    "allowed_shift_states",
    "decay_required",
}
_DOWNSTREAM_KEYS = {"question", "demande", "risque", "action_materielle", "presence", "must_not_mask"}
_OBSERVATION_KEYS = {"turn_id", "execution_status", "source", "signal", "aggregate"}
_AGGREGATE_KEYS = {
    "schema_version",
    "present",
    "dominant_tone",
    "active_tones",
    "stability",
    "shift_state",
    "turns_considered",
}


def load_corpus(repo_root: Path, fixture_name: str = DEFAULT_FIXTURE) -> dict[str, Any]:
    path = repo_root / "benchmark" / "suites" / "stimmung" / "fixtures" / fixture_name
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("corpus_root_not_object")
    return payload


def validate_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    _exact_keys(corpus, _TOP_KEYS, "corpus")
    if corpus.get("schema_version") != CORPUS_SCHEMA_VERSION:
        raise ValueError("invalid_corpus_schema_version")
    _bounded_string(corpus.get("corpus_id"), 1, 80, "invalid_corpus_id")
    if corpus.get("language") != "fr":
        raise ValueError("invalid_language")
    if corpus.get("turn_definition") != TURN_DEFINITION:
        raise ValueError("invalid_turn_definition")
    _validate_thresholds(corpus.get("thresholds"))

    dialogues = corpus.get("dialogues")
    if not isinstance(dialogues, list) or not 12 <= len(dialogues) <= 16:
        raise ValueError("invalid_dialogue_count")
    dialogue_ids: list[str] = []
    coverage: dict[str, set[str]] = {family: set() for family in REQUIRED_FAMILIES}
    for dialogue in dialogues:
        _validate_dialogue(dialogue, coverage)
        dialogue_id = str(dialogue["id"])
        if dialogue_id in dialogue_ids:
            raise ValueError("duplicate_dialogue_id")
        dialogue_ids.append(dialogue_id)

    for family in REQUIRED_FAMILIES:
        if "positive" not in coverage[family]:
            raise ValueError(f"coverage_missing:{family}:positive")
        if family in REQUIRED_COUNTER_FAMILIES and "counter" not in coverage[family]:
            raise ValueError(f"coverage_missing:{family}:counter")

    mutation_ids = _validate_mutation_matrix(corpus.get("mutation_matrix"))
    return {
        "dialogue_count": len(dialogues),
        "dialogue_ids": dialogue_ids,
        "turn_definition": TURN_DEFINITION,
        "covered_families": sorted(family for family, roles in coverage.items() if "positive" in roles),
        "mutation_ids": sorted(mutation_ids),
        "directly_scorable_families": sorted(DIRECTLY_SCORABLE_FAMILIES),
        "contract_only_invariants": sorted(CONTRACT_ONLY_INVARIANTS),
    }


def score_dialogue(case: Mapping[str, Any], observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected_turns = [turn for turn in case.get("turns", []) if isinstance(turn, Mapping) and "expectation" in turn]
    expected_ids = [turn["turn_id"] for turn in expected_turns]
    observed_ids = [item.get("turn_id") for item in observations if isinstance(item, Mapping)]
    families = sorted(set(case.get("families") or []))
    result = {
        "dialogue_id": case.get("id"),
        "families": families,
        "classification": "pass",
        "error_class": "none",
        "reason_codes": [],
        "evaluated_turns": len(observations),
        "source": "unknown",
        "directly_scorable_families": sorted(set(families) & DIRECTLY_SCORABLE_FAMILIES),
        "contract_only_invariants": sorted(_contract_only_invariants(case)),
    }
    if observed_ids != expected_ids:
        return _inconclusive(result, "schema", "observation_order_invalid")
    sources = {item.get("source") for item in observations}
    if len(sources) != 1:
        return _inconclusive(result, "schema", "mixed_sources")
    result["source"] = next(iter(sources), "unknown")

    semantic_reasons: list[str] = []
    previous_aggregate_strength: int | None = None
    for expected_turn, observation in zip(expected_turns, observations):
        if set(observation.keys()) != _OBSERVATION_KEYS:
            return _inconclusive(result, "schema", "observation_schema_invalid")
        status = observation.get("execution_status")
        if status not in _EXECUTION_STATUSES:
            return _inconclusive(result, "schema", "execution_status_invalid")
        if observation.get("source") not in {"primary", "fallback"}:
            return _inconclusive(result, "schema", "source_invalid")
        if status != "ok":
            code = "fail_open_not_semantic_success" if status == "fail_open" else "caller_result_unavailable"
            return _inconclusive(result, "execution", code)

        expectation = expected_turn["expectation"]
        signal = observation.get("signal")
        signal_state = "absent"
        if signal is not None:
            if not isinstance(signal, dict) or validate_signal_payload(signal):
                return _inconclusive(result, "schema", "signal_schema_invalid")
            signal_state = "present" if signal["present"] else "empty"
        allowed_states = set(expectation["allowed_signal_states"])
        if signal_state not in allowed_states:
            semantic_reasons.append(
                "signal_false_negative" if "present" in allowed_states else "signal_false_positive"
            )

        current_strength: int | None = None
        if signal_state == "present" and isinstance(signal, dict):
            tones = {item["tone"]: int(item["strength"]) for item in signal["tones"]}
            dominant = signal["dominant_tone"]
            current_strength = max(tones.values()) if tones else None
            if dominant not in expectation["allowed_dominant_tones"]:
                semantic_reasons.append("dominant_tone_outside_allowed")
            if not set(tones) & set(expectation["allowed_tones"]):
                semantic_reasons.append("signal_false_negative")
            forbidden_hits = set(tones) & set(expectation["forbidden_tones"])
            if forbidden_hits:
                semantic_reasons.append(_forbidden_tone_reason(expectation["semantic_context"]))
            if set(tones) - set(expectation["allowed_tones"]):
                semantic_reasons.append("signal_overcoded")
            minimum, maximum = expectation["strength_range"]
            if current_strength is None or not minimum <= current_strength <= maximum:
                semantic_reasons.append("strength_outside_allowed")

        aggregate = observation.get("aggregate")
        aggregate_error = _aggregate_schema_error(aggregate)
        if aggregate_error:
            return _inconclusive(result, "schema", aggregate_error)
        aggregate_expectation = expectation["aggregate"]
        aggregate_strength = max(
            (int(item["strength"]) for item in aggregate["active_tones"]),
            default=None,
        )
        if aggregate["present"] not in aggregate_expectation["allowed_presence"]:
            semantic_reasons.append("aggregate_presence_mismatch")
        if aggregate["present"]:
            active_tone_names = {item["tone"] for item in aggregate["active_tones"]}
            if aggregate["dominant_tone"] not in aggregate_expectation["allowed_dominant_tones"]:
                semantic_reasons.append("aggregate_dominant_outside_allowed")
            if active_tone_names - set(aggregate_expectation["allowed_active_tones"]):
                semantic_reasons.append("aggregate_overcoded")
            if aggregate["stability"] not in aggregate_expectation["allowed_stability"]:
                semantic_reasons.append("trajectory_stability_mismatch")
            if aggregate["shift_state"] not in aggregate_expectation["allowed_shift_states"]:
                semantic_reasons.append("trajectory_shift_mismatch")
            expected_count = min(int(expected_turn["turn_id"]), AGGREGATE_MAX_SIGNALS)
            if aggregate["turns_considered"] != expected_count:
                semantic_reasons.append("aggregate_turn_count_mismatch")
        if (
            aggregate_expectation["decay_required"]
            and previous_aggregate_strength is not None
            and aggregate_strength is not None
        ):
            if aggregate_strength >= previous_aggregate_strength:
                semantic_reasons.append("aggregate_decay_mismatch")
        if aggregate_strength is not None:
            previous_aggregate_strength = aggregate_strength

    result["reason_codes"] = sorted(set(semantic_reasons))
    if semantic_reasons:
        result["classification"] = "fail"
        result["error_class"] = "semantic"
    return result


def summarize_configuration(
    *,
    source: str,
    corpus: Mapping[str, Any],
    dialogue_scores: Sequence[Mapping[str, Any]],
    provider_results_observed: bool = False,
) -> dict[str, Any]:
    if source not in {"primary", "fallback"}:
        raise ValueError("invalid_source")
    validate_corpus(corpus)
    expected_dialogue_ids = [case["id"] for case in corpus["dialogues"]]
    observed_dialogue_ids = [score.get("dialogue_id") for score in dialogue_scores]
    if observed_dialogue_ids != expected_dialogue_ids:
        decision = "inconclusive"
        decision_reason = "dialogue_set_incomplete"
    elif any(score.get("source") != source for score in dialogue_scores):
        decision = "inconclusive"
        decision_reason = "source_mismatch"
    elif any(score.get("classification") == "inconclusive" for score in dialogue_scores):
        decision = "inconclusive"
        decision_reason = "dialogue_result_inconclusive"
    else:
        thresholds = corpus["thresholds"][source]["family_pass_rates"]
        rates: dict[str, float] = {}
        for family in REQUIRED_FAMILIES:
            family_scores = [score for score in dialogue_scores if family in (score.get("families") or [])]
            rates[family] = (
                sum(1 for score in family_scores if score.get("classification") == "pass") / len(family_scores)
                if family_scores
                else 0.0
            )
        if all(rates[family] >= thresholds[family] for family in REQUIRED_FAMILIES):
            decision = "pass"
            decision_reason = "all_thresholds_met"
        else:
            decision = "fail"
            decision_reason = "family_threshold_missed"
    rates = {
        family: round(
            sum(
                1
                for score in dialogue_scores
                if family in (score.get("families") or []) and score.get("classification") == "pass"
            )
            / max(sum(1 for score in dialogue_scores if family in (score.get("families") or [])), 1),
            4,
        )
        for family in REQUIRED_FAMILIES
    }
    return {
        "source": source,
        "decision": decision,
        "reason_codes": [decision_reason],
        "threshold_schema_version": THRESHOLD_SCHEMA_VERSION,
        "dialogue_count": len(dialogue_scores),
        "family_pass_rates": rates,
        "semantic_failures": sum(1 for score in dialogue_scores if score.get("classification") == "fail"),
        "inconclusive_results": sum(1 for score in dialogue_scores if score.get("classification") == "inconclusive"),
        "provider_results_observed": bool(provider_results_observed),
    }


def _validate_thresholds(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("invalid_thresholds")
    _exact_keys(
        value,
        {
            "schema_version",
            "provider_results_observed",
            "critical_zero_tolerance",
            "primary",
            "fallback",
            "decision_rules",
        },
        "thresholds",
    )
    if value.get("schema_version") != THRESHOLD_SCHEMA_VERSION or value.get("provider_results_observed") is not False:
        raise ValueError("invalid_threshold_metadata")
    if set(value.get("critical_zero_tolerance") or []) != set(CRITICAL_INVARIANTS):
        raise ValueError("invalid_critical_invariants")
    for source in ("primary", "fallback"):
        settings = value.get(source)
        if not isinstance(settings, Mapping):
            raise ValueError(f"invalid_{source}_thresholds")
        _exact_keys(settings, {"family_pass_rates"}, f"{source}_thresholds")
        rates = settings.get("family_pass_rates")
        if not isinstance(rates, Mapping) or set(rates) != set(REQUIRED_FAMILIES):
            raise ValueError(f"invalid_{source}_family_thresholds")
        if any(not _valid_rate(rate) for rate in rates.values()):
            raise ValueError(f"invalid_{source}_family_rate")
        if any(float(rate) != 1.0 for rate in rates.values()):
            raise ValueError("threshold_contract_changed")
    if value.get("decision_rules") != {
        "all_thresholds_met": "pass",
        "semantic_threshold_missed": "fail",
        "transport_or_schema_missing": "inconclusive",
    }:
        raise ValueError("invalid_decision_rules")


def _validate_dialogue(dialogue: Any, coverage: dict[str, set[str]]) -> None:
    if not isinstance(dialogue, Mapping):
        raise ValueError("dialogue_not_object")
    _exact_keys(dialogue, _DIALOGUE_KEYS, "dialogue")
    dialogue_id = _bounded_string(dialogue.get("id"), 8, 32, "invalid_dialogue_id")
    if not dialogue_id.startswith("L4S0-ST-") or dialogue.get("version") != "v1":
        raise ValueError("invalid_dialogue_identity")
    families = dialogue.get("families")
    if not isinstance(families, list) or not families or len(families) != len(set(families)):
        raise ValueError("invalid_dialogue_families")
    if not set(families).issubset(REQUIRED_FAMILIES):
        raise ValueError("unknown_dialogue_family")
    _bounded_string(dialogue.get("human_rationale"), 12, 320, "invalid_dialogue_rationale")
    turns = dialogue.get("turns")
    if not isinstance(turns, list) or not 4 <= len(turns) <= 6:
        raise ValueError("invalid_turn_count")
    evaluated = 0
    for position, turn in enumerate(turns, start=1):
        if not isinstance(turn, Mapping):
            raise ValueError("turn_not_object")
        allowed_keys = _TURN_KEYS | ({"expectation"} if "expectation" in turn else set())
        _exact_keys(turn, allowed_keys, "turn")
        if turn.get("turn_id") != position:
            raise ValueError("invalid_turn_order")
        _bounded_string(turn.get("user"), 1, 480, "invalid_user_turn")
        _bounded_string(turn.get("assistant"), 1, 480, "invalid_assistant_turn")
        if "expectation" in turn:
            evaluated += 1
            _validate_expectation(turn["expectation"], set(families), coverage)
    if evaluated < 2:
        raise ValueError("insufficient_evaluated_turns")


def _validate_expectation(value: Any, dialogue_families: set[str], coverage: dict[str, set[str]]) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("expectation_not_object")
    _exact_keys(value, _EXPECTATION_KEYS, "expectation")
    _closed_string_list(value.get("allowed_signal_states"), _SIGNAL_STATES, "invalid_signal_states")
    dominant = _closed_string_list(value.get("allowed_dominant_tones"), ALLOWED_TONES, "invalid_dominant_tones")
    allowed = _closed_string_list(value.get("allowed_tones"), ALLOWED_TONES, "invalid_allowed_tones")
    forbidden = _closed_string_list(
        value.get("forbidden_tones"),
        ALLOWED_TONES,
        "invalid_forbidden_tones",
        allow_empty=True,
    )
    if not set(dominant).issubset(allowed) or set(allowed) & set(forbidden):
        raise ValueError("incoherent_tone_sets")
    strength_range = value.get("strength_range")
    if (
        not isinstance(strength_range, list)
        or len(strength_range) != 2
        or any(isinstance(item, bool) or not isinstance(item, int) for item in strength_range)
        or not 1 <= strength_range[0] <= strength_range[1] <= 10
    ):
        raise ValueError("invalid_strength_range")
    context = value.get("semantic_context")
    if context not in _SEMANTIC_CONTEXTS:
        raise ValueError("invalid_semantic_context")
    phase = value.get("trajectory_phase")
    if phase not in _TRAJECTORY_PHASES:
        raise ValueError("invalid_trajectory_phase")
    _validate_aggregate_expectation(value.get("aggregate"))
    attributions = _closed_string_list(
        value.get("forbidden_attributions"), _ATTRIBUTIONS, "invalid_forbidden_attributions"
    )
    required_attributions = {"speaker_profile", "assistant_profile", "durable_inner_state"}
    if not required_attributions.issubset(attributions):
        raise ValueError("psychologization_not_forbidden")
    if context == "reported" and "reported_affect_internalized" not in attributions:
        raise ValueError("reported_affect_internalization_not_forbidden")
    if context == "quoted" and "quoted_affect_internalized" not in attributions:
        raise ValueError("quoted_affect_internalization_not_forbidden")
    if value.get("epistemic_effect") != "forbidden_without_independent_reason":
        raise ValueError("epistemic_confusion_not_forbidden")
    _validate_downstream(value.get("downstream"))
    _bounded_string(value.get("human_rationale"), 12, 240, "invalid_expectation_rationale")

    evidence = value.get("coverage_evidence")
    if not isinstance(evidence, list) or not evidence:
        raise ValueError("missing_coverage_evidence")
    for item in evidence:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_coverage_evidence")
        _exact_keys(item, {"family", "role"}, "coverage_evidence")
        family = item.get("family")
        role = item.get("role")
        if family not in REQUIRED_FAMILIES or family not in dialogue_families or role not in {"positive", "counter"}:
            raise ValueError("invalid_coverage_evidence")
        _validate_evidence_claim(family, role, value)
        coverage[family].add(str(role))


def _validate_aggregate_expectation(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("aggregate_expectation_not_object")
    _exact_keys(value, _AGGREGATE_EXPECTATION_KEYS, "aggregate_expectation")
    presence = value.get("allowed_presence")
    if not isinstance(presence, list) or not presence or any(not isinstance(item, bool) for item in presence):
        raise ValueError("invalid_aggregate_presence")
    _closed_string_list(value.get("allowed_dominant_tones"), ALLOWED_TONES, "invalid_aggregate_dominant_tones")
    active_tones = _closed_string_list(
        value.get("allowed_active_tones"),
        ALLOWED_TONES,
        "invalid_aggregate_active_tones",
    )
    if not set(value["allowed_dominant_tones"]).issubset(active_tones):
        raise ValueError("incoherent_aggregate_tone_sets")
    _closed_string_list(value.get("allowed_stability"), _STABILITIES, "invalid_aggregate_stability")
    _closed_string_list(value.get("allowed_shift_states"), _SHIFT_STATES, "invalid_aggregate_shift_states")
    if not isinstance(value.get("decay_required"), bool):
        raise ValueError("invalid_decay_requirement")


def _validate_downstream(value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ValueError("downstream_not_object")
    _exact_keys(value, _DOWNSTREAM_KEYS, "downstream")
    active: set[str] = set()
    for field in _DOWNSTREAM_FIELDS:
        if not isinstance(value.get(field), bool):
            raise ValueError("invalid_downstream_flag")
        if value[field]:
            active.add(field)
    if value.get("presence") not in _PRESENCE_RELATIONS:
        raise ValueError("invalid_presence_relation")
    must_not_mask = value.get("must_not_mask")
    if not isinstance(must_not_mask, list) or len(must_not_mask) != len(set(must_not_mask)):
        raise ValueError("invalid_must_not_mask")
    if set(must_not_mask) != active:
        raise ValueError("downstream_masking_contract_incomplete")
    if active and value.get("presence") == "eligible":
        raise ValueError("presence_masks_material_turn")
    if not active and value.get("presence") == "forbidden":
        raise ValueError("presence_forbidden_without_counter_case")


def _validate_evidence_claim(family: str, role: str, expectation: Mapping[str, Any]) -> None:
    aggregate = expectation["aggregate"]
    downstream = expectation["downstream"]
    positive = role == "positive"
    predicates = {
        "emergence": expectation["trajectory_phase"] == "emerging",
        "stabilite": "stable" in aggregate["allowed_stability"] and expectation["trajectory_phase"] == "steady",
        "bascule": expectation["trajectory_phase"] in {"shift_onset", "shifted"}
        and bool(set(aggregate["allowed_shift_states"]) & {"candidate_shift", "shifted"}),
        "retour_neutre": expectation["trajectory_phase"] in {"decay", "settled"}
        and aggregate["decay_required"]
        and "neutralite" in aggregate["allowed_dominant_tones"],
        "alternance": expectation["trajectory_phase"] == "alternating"
        and "volatile" in aggregate["allowed_stability"],
        "intensite_sans_effet_epistemique": expectation["semantic_context"] == "intensity"
        and expectation["epistemic_effect"] == "forbidden_without_independent_reason",
        "ironie": expectation["semantic_context"] == "ironic",
        "citation": expectation["semantic_context"] == "quoted",
        "affect_rapporte": expectation["semantic_context"] == "reported",
        "correction": expectation["semantic_context"] == "correction"
        and expectation["trajectory_phase"] in {"shift_onset", "shifted", "decay"},
        "question": downstream["question"],
        "demande": downstream["demande"],
        "risque": downstream["risque"],
        "action_materielle": downstream["action_materielle"],
        "opportunite_presence": downstream["presence"] == "eligible",
        "contre_presence": downstream["presence"] == "forbidden" and bool(downstream["must_not_mask"]),
    }
    if positive != bool(predicates[family]):
        raise ValueError(f"coverage_claim_not_exercised:{family}:{role}")


def _validate_mutation_matrix(value: Any) -> set[str]:
    if not isinstance(value, list):
        raise ValueError("invalid_mutation_matrix")
    ids: set[str] = set()
    families: set[str] = set()
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError("invalid_mutation_entry")
        _exact_keys(item, {"id", "families", "validator"}, "mutation_entry")
        mutation_id = item.get("id")
        mutation_families = item.get("families")
        if mutation_id not in REQUIRED_MUTATIONS or mutation_id in ids:
            raise ValueError("invalid_mutation_id")
        if (
            not isinstance(mutation_families, list)
            or not mutation_families
            or not set(mutation_families).issubset(REQUIRED_FAMILIES)
        ):
            raise ValueError("invalid_mutation_families")
        if item.get("validator") not in {"corpus", "scorer"}:
            raise ValueError("invalid_mutation_validator")
        ids.add(str(mutation_id))
        families.update(str(family) for family in mutation_families)
    if ids != REQUIRED_MUTATIONS:
        raise ValueError("mutation_matrix_incomplete")
    if families != set(REQUIRED_FAMILIES):
        raise ValueError("mutation_family_coverage_incomplete")
    return ids


def _aggregate_schema_error(value: Any) -> str | None:
    if not isinstance(value, Mapping) or set(value) != _AGGREGATE_KEYS:
        return "aggregate_schema_invalid"
    if value.get("schema_version") != "v1" or not isinstance(value.get("present"), bool):
        return "aggregate_schema_invalid"
    active_tones = value.get("active_tones")
    if not isinstance(active_tones, list) or len(active_tones) > 3:
        return "aggregate_schema_invalid"
    seen: set[str] = set()
    for item in active_tones:
        if not isinstance(item, Mapping) or set(item) != {"tone", "strength"}:
            return "aggregate_schema_invalid"
        tone = item.get("tone")
        strength = item.get("strength")
        if (
            tone not in ALLOWED_TONES
            or tone in seen
            or isinstance(strength, bool)
            or not isinstance(strength, int)
            or not 1 <= strength <= 10
        ):
            return "aggregate_schema_invalid"
        seen.add(str(tone))
    turns = value.get("turns_considered")
    if isinstance(turns, bool) or not isinstance(turns, int) or not 0 <= turns <= 4:
        return "aggregate_schema_invalid"
    if value["present"]:
        if (
            value.get("dominant_tone") not in seen
            or value.get("stability") not in _STABILITIES
            or value.get("shift_state") not in _SHIFT_STATES
            or turns == 0
        ):
            return "aggregate_schema_invalid"
    elif (
        active_tones
        or value.get("dominant_tone") is not None
        or value.get("stability") != ""
        or value.get("shift_state") != ""
        or turns != 0
    ):
        return "aggregate_schema_invalid"
    return None


def _forbidden_tone_reason(context: str) -> str:
    return {
        "ironic": "irony_literalized",
        "quoted": "quoted_affect_internalized",
        "reported": "reported_affect_internalized",
    }.get(context, "signal_tone_forbidden")


def _contract_only_invariants(case: Mapping[str, Any]) -> set[str]:
    invariants = {"no_psychologization", "no_affect_epistemic_confusion"}
    families = set(case.get("families") or [])
    mapping = {
        "question": "question_not_masked",
        "demande": "request_not_masked",
        "risque": "risk_not_masked",
        "action_materielle": "material_action_not_masked",
        "opportunite_presence": "presence_relation_preserved",
        "contre_presence": "presence_relation_preserved",
    }
    invariants.update(invariant for family, invariant in mapping.items() if family in families)
    return invariants


def _inconclusive(result: dict[str, Any], error_class: str, reason: str) -> dict[str, Any]:
    return {**result, "classification": "inconclusive", "error_class": error_class, "reason_codes": [reason]}


def _exact_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label}_keys_invalid")


def _bounded_string(value: Any, minimum: int, maximum: int, reason: str) -> str:
    if not isinstance(value, str) or not minimum <= len(value.strip()) <= maximum:
        raise ValueError(reason)
    return value.strip()


def _closed_string_list(
    value: Any,
    allowed: set[str] | frozenset[str],
    reason: str,
    *,
    allow_empty: bool = False,
) -> list[str]:
    if (
        not isinstance(value, list)
        or (not value and not allow_empty)
        or len(value) != len(set(value))
        or any(item not in allowed for item in value)
    ):
        raise ValueError(reason)
    return [str(item) for item in value]


def _valid_rate(value: Any) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and 0.0 <= float(value) <= 1.0
    )
