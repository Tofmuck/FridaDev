from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from benchmark.suites.stimmung import dialogic_semantics
from benchmark.suites.stimmung import scorer as historical_scorer
from core import stimmung_agent


DIRECTLY_MEASURABLE_FAMILIES = {
    "emergence",
    "stabilite",
    "bascule",
    "retour_neutre",
    "alternance",
    "ironie",
    "citation",
    "affect_rapporte",
    "correction",
}
MIXED_FAMILIES = {"intensite_sans_effet_epistemique"}
CONTRACT_ONLY_FAMILIES = {
    "question",
    "demande",
    "risque",
    "action_materielle",
    "opportunite_presence",
    "contre_presence",
}


def _observations_for(case: dict, *, source: str = "primary") -> list[dict]:
    observations: list[dict] = []
    for turn in case["turns"]:
        expectation = turn.get("expectation")
        if expectation is None:
            continue
        dominant = expectation["allowed_dominant_tones"][0]
        state = expectation["allowed_signal_states"][0]
        signal = None
        if state in {"present", "empty"}:
            present = state == "present"
            signal = {
                "schema_version": "v1",
                "present": present,
                "tones": ([{"tone": dominant, "strength": expectation["strength_range"][0]}] if present else []),
                "dominant_tone": dominant if present else None,
                "confidence": 0.8,
            }
        aggregate_expectation = expectation["aggregate"]
        aggregate_present = aggregate_expectation["allowed_presence"][0]
        aggregate = {
            "schema_version": "v1",
            "present": aggregate_present,
            "dominant_tone": dominant if aggregate_present else None,
            "active_tones": (
                [{"tone": dominant, "strength": expectation["strength_range"][0]}]
                if aggregate_present
                else []
            ),
            "stability": aggregate_expectation["allowed_stability"][0] if aggregate_present else "",
            "shift_state": aggregate_expectation["allowed_shift_states"][0] if aggregate_present else "",
            "turns_considered": min(turn["turn_id"], 4) if aggregate_present else 0,
        }
        observations.append(
            {
                "turn_id": turn["turn_id"],
                "execution_status": "ok",
                "source": source,
                "signal": signal,
                "aggregate": aggregate,
            }
        )
    return observations


class StimmungDialogicCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = dialogic_semantics.load_corpus(REPO_ROOT)

    def test_corpus_is_closed_versioned_and_multi_turn(self) -> None:
        summary = dialogic_semantics.validate_corpus(self.corpus)

        self.assertEqual(self.corpus["schema_version"], "stimmung_dialogic_corpus_v2")
        self.assertEqual(summary["dialogue_count"], 16)
        self.assertEqual(summary["turn_definition"], "complete_user_assistant_pair")
        self.assertEqual(len(summary["dialogue_ids"]), len(set(summary["dialogue_ids"])))
        self.assertEqual(set(summary["covered_families"]), set(dialogic_semantics.REQUIRED_FAMILIES))
        self.assertEqual(
            set(summary["directly_measurable_families"]),
            DIRECTLY_MEASURABLE_FAMILIES,
        )
        self.assertEqual(set(summary["mixed_families"]), MIXED_FAMILIES)
        self.assertEqual(
            set(summary["contract_only_families"]),
            CONTRACT_ONLY_FAMILIES,
        )
        self.assertEqual(
            DIRECTLY_MEASURABLE_FAMILIES | MIXED_FAMILIES | CONTRACT_ONLY_FAMILIES,
            set(dialogic_semantics.REQUIRED_FAMILIES),
        )
        self.assertEqual(
            set(summary["contract_only_invariants"]),
            set(dialogic_semantics.CONTRACT_ONLY_INVARIANTS),
        )
        for case in self.corpus["dialogues"]:
            self.assertGreaterEqual(len(case["turns"]), 4)
            self.assertLessEqual(len(case["turns"]), 6)
            self.assertEqual(
                [turn["turn_id"] for turn in case["turns"]],
                list(range(1, len(case["turns"]) + 1)),
            )

    def test_thresholds_are_frozen_for_primary_and_fallback(self) -> None:
        thresholds = self.corpus["thresholds"]

        self.assertEqual(thresholds["schema_version"], "stimmung_dialogic_thresholds_v2")
        self.assertEqual(
            set(thresholds["primary"]["family_pass_rates"]),
            DIRECTLY_MEASURABLE_FAMILIES | MIXED_FAMILIES,
        )
        self.assertEqual(
            set(thresholds["fallback"]["family_pass_rates"]),
            DIRECTLY_MEASURABLE_FAMILIES | MIXED_FAMILIES,
        )
        self.assertEqual(
            set(thresholds["critical_zero_tolerance"]),
            set(dialogic_semantics.CRITICAL_INVARIANTS),
        )
        self.assertFalse(thresholds["provider_results_observed"])

        lowered = copy.deepcopy(self.corpus)
        lowered["thresholds"]["primary"]["family_pass_rates"]["emergence"] = 0.0
        with self.assertRaisesRegex(ValueError, "threshold_contract_changed"):
            dialogic_semantics.validate_corpus(lowered)

    def test_coverage_requires_structural_positive_and_counter_evidence(self) -> None:
        mutation = copy.deepcopy(self.corpus)
        mutation["dialogues"] = [case for case in mutation["dialogues"] if "ironie" not in case["families"]]

        with self.assertRaisesRegex(ValueError, "coverage_missing:ironie:positive"):
            dialogic_semantics.validate_corpus(mutation)

    def test_downstream_contracts_have_no_fabricated_semantic_rates(self) -> None:
        scores = [
            dialogic_semantics.score_dialogue(case, _observations_for(case))
            for case in self.corpus["dialogues"]
        ]
        summary = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=scores,
            provider_results_observed=True,
        )

        self.assertEqual(set(summary["family_pass_rates"]), DIRECTLY_MEASURABLE_FAMILIES | MIXED_FAMILIES)
        self.assertEqual(
            summary["contract_only_families"],
            {family: "not_measured" for family in sorted(CONTRACT_ONLY_FAMILIES)},
        )
        self.assertEqual(
            summary["mixed_families"],
            {
                family: "caller_component_measured_downstream_not_measured"
                for family in sorted(MIXED_FAMILIES)
            },
        )
        downstream_case = next(case for case in self.corpus["dialogues"] if "question" in case["families"])
        downstream_score = dialogic_semantics.score_dialogue(
            downstream_case,
            _observations_for(downstream_case),
        )
        self.assertNotIn("question", downstream_score["directly_measurable_families"])
        self.assertEqual(downstream_score["contract_only_status"], "not_measured")

    def test_hardened_dialogues_have_required_depth_and_hint_policy(self) -> None:
        cases = {case["id"]: case for case in self.corpus["dialogues"]}
        hardened = {
            "L4S0-ST-015": (5, "ironie"),
            "L4S0-ST-016": (6, "affect_rapporte"),
        }

        for dialogue_id, (turn_count, family) in hardened.items():
            with self.subTest(dialogue_id=dialogue_id):
                case = cases.get(dialogue_id)
                self.assertIsNotNone(case)
                self.assertEqual(len(case["turns"]), turn_count)
                self.assertEqual(case.get("difficulty"), "hard")
                self.assertEqual(case.get("hint_policy"), "implicit_context_required")
                roles = {
                    item["role"]
                    for turn in case["turns"]
                    for item in turn.get("expectation", {}).get("coverage_evidence", [])
                    if item["family"] == family
                }
                self.assertEqual(roles, {"positive", "counter"})

        removed = copy.deepcopy(self.corpus)
        removed["dialogues"] = [case for case in removed["dialogues"] if case["id"] != "L4S0-ST-015"]
        with self.assertRaisesRegex(ValueError, "hardened_dialogue_missing"):
            dialogic_semantics.validate_corpus(removed)

        shortened = copy.deepcopy(self.corpus)
        shortened_case = next(case for case in shortened["dialogues"] if case["id"] == "L4S0-ST-016")
        shortened_case["turns"].pop(4)
        shortened_case["turns"][-1]["turn_id"] = 5
        with self.assertRaisesRegex(ValueError, "hardened_dialogue_contract_changed"):
            dialogic_semantics.validate_corpus(shortened)

        metadata = copy.deepcopy(self.corpus)
        metadata_case = next(case for case in metadata["dialogues"] if case["id"] == "L4S0-ST-015")
        metadata_case["hint_policy"] = "context_labels_allowed"
        with self.assertRaises(ValueError):
            dialogic_semantics.validate_corpus(metadata)

    def test_duplicate_tones_match_runtime_normalization_boundary(self) -> None:
        signal = {
            "schema_version": "v1",
            "present": True,
            "tones": [
                {"tone": "neutralite", "strength": 4},
                {"tone": "neutralite", "strength": 4},
            ],
            "dominant_tone": "neutralite",
            "confidence": 0.8,
        }
        self.assertEqual(historical_scorer.validate_signal_payload(signal), [])

        case = self.corpus["dialogues"][0]
        observations = _observations_for(case)
        normalized = stimmung_agent._validate_affective_turn_signal(signal)
        self.assertEqual(normalized["tones"], [{"tone": "neutralite", "strength": 4}])
        observations[0]["signal"] = normalized
        self.assertEqual(dialogic_semantics.score_dialogue(case, observations)["classification"], "pass")

        observations[0]["signal"]["tones"].append(copy.deepcopy(observations[0]["signal"]["tones"][0]))
        result = dialogic_semantics.score_dialogue(case, observations)
        self.assertEqual(result["classification"], "inconclusive")
        self.assertIn("signal_schema_invalid", result["reason_codes"])

    def test_corpus_validator_rejects_controlled_structural_mutations(self) -> None:
        mutations = {
            "turn_removed": self._remove_turn,
            "turns_reversed": self._reverse_turns,
            "turn_duplicated": self._duplicate_turn,
            "exact_output_added": self._add_exact_output,
            "free_field_added": self._add_free_field,
            "question_masked": lambda value: self._mask_downstream(value, "question"),
            "request_masked": lambda value: self._mask_downstream(value, "demande"),
            "risk_masked": lambda value: self._mask_downstream(value, "risque"),
            "material_action_masked": lambda value: self._mask_downstream(value, "action_materielle"),
            "presence_forced": self._force_presence,
            "presence_opportunity_removed": self._remove_presence_opportunity,
            "reported_affect_internalized": lambda value: self._remove_forbidden_attribution(
                value, "reported_affect_internalized"
            ),
            "quoted_affect_internalized": lambda value: self._remove_forbidden_attribution(
                value, "quoted_affect_internalized"
            ),
            "epistemic_confusion": self._allow_epistemic_effect,
            "correction_ignored": self._erase_trajectory_phase,
        }
        self.assertTrue(set(mutations).issubset(dialogic_semantics.REQUIRED_MUTATIONS))

        for mutation_id, mutate in mutations.items():
            with self.subTest(mutation=mutation_id):
                candidate = copy.deepcopy(self.corpus)
                mutate(candidate)
                with self.assertRaises(ValueError):
                    dialogic_semantics.validate_corpus(candidate)

    def test_mutation_matrix_covers_every_family_and_required_mutation(self) -> None:
        summary = dialogic_semantics.validate_corpus(self.corpus)

        self.assertEqual(set(summary["mutation_ids"]), set(dialogic_semantics.REQUIRED_MUTATIONS))
        covered = {family for item in self.corpus["mutation_matrix"] for family in item["families"]}
        self.assertEqual(covered, set(dialogic_semantics.REQUIRED_FAMILIES))

    def test_scorer_accepts_bounded_properties_without_exact_text(self) -> None:
        case = self.corpus["dialogues"][0]
        result = dialogic_semantics.score_dialogue(case, _observations_for(case))

        self.assertEqual(result["classification"], "pass")
        self.assertEqual(result["error_class"], "none")
        self.assertEqual(result["reason_codes"], [])
        self.assertEqual(result["evaluated_turns"], len(_observations_for(case)))
        self.assertNotIn("user", result)
        self.assertNotIn("assistant", result)

    def test_same_scorer_rejects_semantic_output_mutations(self) -> None:
        cases_by_family = {
            family: next(
                case
                for case in self.corpus["dialogues"]
                if family in case["families"]
            )
            for family in (
                "stabilite",
                "bascule",
                "alternance",
                "retour_neutre",
                "ironie",
                "citation",
                "affect_rapporte",
            )
        }
        mutations = {
            "stable_as_volatile": ("stabilite", self._mutate_stable_as_volatile),
            "shift_erased": ("bascule", self._mutate_shift_erased),
            "alternation_as_stable": ("alternance", self._mutate_alternation_as_stable),
            "neutral_return_without_decay": ("retour_neutre", self._mutate_no_decay),
            "irony_literalized": (
                "ironie",
                lambda case, observations: self._mutate_forbidden_tone(case, observations, "ironie"),
            ),
            "quoted_affect_internalized": (
                "citation",
                lambda case, observations: self._mutate_forbidden_tone(case, observations, "citation"),
            ),
            "reported_affect_internalized": (
                "affect_rapporte",
                lambda case, observations: self._mutate_forbidden_tone(
                    case, observations, "affect_rapporte"
                ),
            ),
        }

        for mutation_id, (family, mutate) in mutations.items():
            with self.subTest(mutation=mutation_id):
                case = cases_by_family[family]
                observations = _observations_for(case)
                self.assertEqual(dialogic_semantics.score_dialogue(case, observations)["classification"], "pass")
                mutate(case, observations)
                result = dialogic_semantics.score_dialogue(case, observations)
                self.assertEqual(result["classification"], "fail")
                self.assertTrue(result["reason_codes"])

        emergence = cases_by_family.get("emergence") or next(
            case for case in self.corpus["dialogues"] if "emergence" in case["families"]
        )
        signal_overcoded = _observations_for(emergence)
        signal_overcoded[0]["signal"]["tones"].append({"tone": "anxiete", "strength": 4})
        signal_result = dialogic_semantics.score_dialogue(emergence, signal_overcoded)
        self.assertEqual(signal_result["classification"], "fail")
        self.assertIn("signal_overcoded", signal_result["reason_codes"])

        aggregate_overcoded = _observations_for(emergence)
        aggregate_overcoded[0]["aggregate"]["active_tones"].append({"tone": "anxiete", "strength": 4})
        aggregate_result = dialogic_semantics.score_dialogue(emergence, aggregate_overcoded)
        self.assertEqual(aggregate_result["classification"], "fail")
        self.assertIn("aggregate_overcoded", aggregate_result["reason_codes"])

        duplicated_tone = _observations_for(emergence)
        duplicated_tone[0]["signal"]["tones"].append(
            copy.deepcopy(duplicated_tone[0]["signal"]["tones"][0])
        )
        duplicated_tone_result = dialogic_semantics.score_dialogue(emergence, duplicated_tone)
        self.assertEqual(duplicated_tone_result["classification"], "inconclusive")
        self.assertIn("signal_schema_invalid", duplicated_tone_result["reason_codes"])

        underreported = _observations_for(emergence)
        underreported[0]["aggregate"]["turns_considered"] = 1
        underreported_result = dialogic_semantics.score_dialogue(emergence, underreported)
        self.assertEqual(underreported_result["classification"], "fail")
        self.assertIn("aggregate_turn_count_mismatch", underreported_result["reason_codes"])

    def test_fail_open_and_schema_errors_are_inconclusive_not_semantic_passes(self) -> None:
        case = self.corpus["dialogues"][0]
        fail_open = _observations_for(case)
        fail_open[0]["execution_status"] = "fail_open"
        fail_open[0]["signal"] = {
            "schema_version": "v1",
            "present": False,
            "tones": [],
            "dominant_tone": None,
            "confidence": 0.0,
        }
        schema_error = _observations_for(case)
        schema_error[0]["signal"]["unexpected"] = True
        mixed_sources = _observations_for(case)
        mixed_sources[-1]["source"] = "fallback"
        duplicated_observation = _observations_for(case)
        duplicated_observation.insert(1, copy.deepcopy(duplicated_observation[0]))

        fail_open_result = dialogic_semantics.score_dialogue(case, fail_open)
        schema_result = dialogic_semantics.score_dialogue(case, schema_error)
        self.assertEqual(fail_open_result["classification"], "inconclusive")
        self.assertEqual(fail_open_result["error_class"], "execution")
        self.assertIn("fail_open_not_semantic_success", fail_open_result["reason_codes"])
        self.assertEqual(schema_result["classification"], "inconclusive")
        self.assertEqual(schema_result["error_class"], "schema")
        mixed_result = dialogic_semantics.score_dialogue(case, mixed_sources)
        self.assertEqual(mixed_result["classification"], "inconclusive")
        self.assertIn("mixed_sources", mixed_result["reason_codes"])
        duplicated_result = dialogic_semantics.score_dialogue(case, duplicated_observation)
        self.assertEqual(duplicated_result["classification"], "inconclusive")
        self.assertIn("observation_order_invalid", duplicated_result["reason_codes"])

    def test_configuration_summary_applies_frozen_source_thresholds(self) -> None:
        scores = []
        for case in self.corpus["dialogues"]:
            scores.append(dialogic_semantics.score_dialogue(case, _observations_for(case)))

        not_observed = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=scores,
        )
        self.assertEqual(not_observed["decision"], "inconclusive")
        self.assertEqual(not_observed["reason_codes"], ["provider_results_not_observed"])
        self.assertEqual(not_observed["family_pass_rates"], {})

        primary = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=scores,
            provider_results_observed=True,
        )
        fallback_scores = [
            dialogic_semantics.score_dialogue(case, _observations_for(case, source="fallback"))
            for case in self.corpus["dialogues"]
        ]
        fallback = dialogic_semantics.summarize_configuration(
            source="fallback",
            corpus=self.corpus,
            dialogue_scores=fallback_scores,
            provider_results_observed=True,
        )
        self.assertEqual(primary["decision"], "pass")
        self.assertEqual(fallback["decision"], "pass")
        self.assertEqual(primary["reason_codes"], ["all_thresholds_met"])
        self.assertEqual(primary["threshold_schema_version"], "stimmung_dialogic_thresholds_v2")

        contract_case_index = next(
            index
            for index, score in enumerate(scores)
            if set(score["families"]).issubset(CONTRACT_ONLY_FAMILIES)
        )
        contract_case_failure = copy.deepcopy(scores)
        contract_case_failure[contract_case_index]["classification"] = "fail"
        contract_case_failure[contract_case_index]["error_class"] = "semantic"
        contract_case_failure[contract_case_index]["reason_codes"] = ["signal_false_positive"]
        contract_result = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=contract_case_failure,
            provider_results_observed=True,
        )
        self.assertEqual(contract_result["decision"], "fail")
        self.assertEqual(contract_result["reason_codes"], ["caller_semantic_failure"])

        degraded = copy.deepcopy(scores)
        degraded[0]["classification"] = "inconclusive"
        degraded[0]["error_class"] = "schema"
        degraded[0]["reason_codes"] = ["signal_schema_invalid"]
        result = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=degraded,
            provider_results_observed=True,
        )
        self.assertEqual(result["decision"], "inconclusive")
        self.assertEqual(result["reason_codes"], ["dialogue_result_inconclusive"])

        wrong_source = dialogic_semantics.summarize_configuration(
            source="fallback",
            corpus=self.corpus,
            dialogue_scores=scores,
            provider_results_observed=True,
        )
        self.assertEqual(wrong_source["decision"], "inconclusive")
        self.assertEqual(wrong_source["reason_codes"], ["source_mismatch"])
        missing_dialogue = dialogic_semantics.summarize_configuration(
            source="primary",
            corpus=self.corpus,
            dialogue_scores=scores[:-1],
            provider_results_observed=True,
        )
        self.assertEqual(missing_dialogue["decision"], "inconclusive")
        self.assertEqual(missing_dialogue["reason_codes"], ["dialogue_set_incomplete"])

    @staticmethod
    def _first_evaluated(corpus: dict, family: str | None = None) -> dict:
        for case in corpus["dialogues"]:
            if family is not None and family not in case["families"]:
                continue
            for turn in case["turns"]:
                if "expectation" in turn:
                    return turn["expectation"]
        raise AssertionError("missing evaluated turn")

    def _remove_turn(self, corpus: dict) -> None:
        corpus["dialogues"][0]["turns"].pop()

    def _reverse_turns(self, corpus: dict) -> None:
        corpus["dialogues"][0]["turns"][0], corpus["dialogues"][0]["turns"][1] = (
            corpus["dialogues"][0]["turns"][1],
            corpus["dialogues"][0]["turns"][0],
        )

    def _duplicate_turn(self, corpus: dict) -> None:
        corpus["dialogues"][0]["turns"].insert(1, copy.deepcopy(corpus["dialogues"][0]["turns"][0]))

    def _add_exact_output(self, corpus: dict) -> None:
        self._first_evaluated(corpus)["expected_output"] = "forbidden exact output"

    def _add_free_field(self, corpus: dict) -> None:
        self._first_evaluated(corpus)["free_note"] = "forbidden free field"

    def _mask_downstream(self, corpus: dict, field: str) -> None:
        family = {
            "question": "question",
            "demande": "demande",
            "risque": "risque",
            "action_materielle": "action_materielle",
        }[field]
        expectation = self._positive_expectation(corpus, family)
        expectation["downstream"]["must_not_mask"].remove(field)

    def _force_presence(self, corpus: dict) -> None:
        expectation = self._positive_expectation(corpus, "contre_presence")
        expectation["downstream"]["presence"] = "eligible"

    def _remove_presence_opportunity(self, corpus: dict) -> None:
        expectation = self._positive_expectation(corpus, "opportunite_presence")
        expectation["downstream"]["presence"] = "not_applicable"

    def _remove_forbidden_attribution(self, corpus: dict, value: str) -> None:
        family = "affect_rapporte" if value.startswith("reported") else "citation"
        expectation = self._positive_expectation(corpus, family)
        expectation["forbidden_attributions"].remove(value)

    def _allow_epistemic_effect(self, corpus: dict) -> None:
        self._first_evaluated(corpus, "intensite_sans_effet_epistemique")["epistemic_effect"] = "allowed"

    def _erase_trajectory_phase(self, corpus: dict) -> None:
        self._positive_expectation(corpus, "correction")["trajectory_phase"] = "steady"

    @staticmethod
    def _positive_expectation(corpus: dict, family: str) -> dict:
        for case in corpus["dialogues"]:
            for turn in case["turns"]:
                expectation = turn.get("expectation")
                if expectation and {"family": family, "role": "positive"} in expectation["coverage_evidence"]:
                    return expectation
        raise AssertionError(f"missing positive evidence for {family}")

    @classmethod
    def _mutate_stable_as_volatile(cls, case: dict, observations: list[dict]) -> None:
        index = cls._positive_observation_index(case, "stabilite")
        observations[index]["aggregate"]["stability"] = "volatile"

    @classmethod
    def _mutate_shift_erased(cls, case: dict, observations: list[dict]) -> None:
        index = cls._positive_observation_index(case, "bascule")
        observations[index]["aggregate"]["stability"] = "stable"
        observations[index]["aggregate"]["shift_state"] = "steady"

    @classmethod
    def _mutate_alternation_as_stable(cls, case: dict, observations: list[dict]) -> None:
        index = cls._positive_observation_index(case, "alternance")
        observations[index]["aggregate"]["stability"] = "stable"
        observations[index]["aggregate"]["shift_state"] = "steady"

    @classmethod
    def _mutate_no_decay(cls, case: dict, observations: list[dict]) -> None:
        index = cls._positive_observation_index(case, "retour_neutre")
        previous_strength = observations[index - 1]["aggregate"]["active_tones"][0]["strength"]
        observations[index]["aggregate"]["active_tones"][0]["strength"] = previous_strength

    @classmethod
    def _mutate_forbidden_tone(cls, case: dict, observations: list[dict], family: str) -> None:
        index = cls._positive_observation_index(case, family)
        expectation = [turn["expectation"] for turn in case["turns"] if "expectation" in turn][index]
        forbidden = expectation["forbidden_tones"][0]
        observations[index]["signal"]["tones"].append({"tone": forbidden, "strength": 8})

    @staticmethod
    def _positive_observation_index(case: dict, family: str) -> int:
        evaluated = [turn["expectation"] for turn in case["turns"] if "expectation" in turn]
        for index, expectation in enumerate(evaluated):
            if {"family": family, "role": "positive"} in expectation["coverage_evidence"]:
                return index
        raise AssertionError(f"missing positive observation for {family}")


if __name__ == "__main__":
    unittest.main()
