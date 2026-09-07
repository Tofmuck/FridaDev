from __future__ import annotations

import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import unittest
from pathlib import Path

from benchmark.suites.stimmung import final_wording_diagnostic
from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.support.stimmung_dialogic_pipeline import (
    affective_signal,
    exercise_stimmung_dialogue,
    primary_signal,
)


REPO_ROOT = Path(__file__).resolve().parents[4]
V1_MANIFEST_PATH = (
    REPO_ROOT
    / "benchmark/suites/stimmung/fixtures/stimmung_final_wording_freeze_v1.json"
)
V1_MANIFEST_SHA256 = "207b44a407b0b468540921e22ffa7a0a49f192770dc07ae31c18e7f57219e996"


def _perfect_provider_observations(corpus: dict[str, object]) -> list[dict[str, object]]:
    observations: list[dict[str, object]] = []
    for case in corpus["cases"]:
        if not case["provider_eligible"]:
            continue
        for repetition in (1, 2):
            observations.append(
                {
                    "case_id": case["id"],
                    "repetition": repetition,
                    "source_kind": "main_model_provider",
                    "call_attempts_complete": True,
                    "responses_complete": True,
                    "control_response_sha256": "a" * 64,
                    "treatment_response_sha256": "b" * 64,
                    "delicacy_effect": (
                        "improved"
                        if case["enunciation_state"] == "transition_delicate"
                        else "not_applicable"
                    ),
                    "formulation_fit": (
                        "improved"
                        if case["enunciation_state"] == "transition_delicate"
                        else "unchanged"
                    ),
                    "psychologization": "none",
                    "certainty_change": "none",
                    "truth_or_evidence_change": "none",
                    "masked_targets": [],
                    "presence_regression": "not_text_measurable",
                    "overapplication": False,
                }
            )
    return observations


class Lot4C4FinalWordingCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = final_wording_diagnostic.load_corpus(REPO_ROOT)

    def test_corpus_is_versioned_paired_bounded_and_covers_required_families(self) -> None:
        summary = final_wording_diagnostic.validate_corpus(self.corpus)

        self.assertEqual(summary["case_count"], 14)
        self.assertEqual(summary["provider_case_count"], 12)
        self.assertEqual(
            set(summary["enunciation_states"]),
            {
                "not_applicable",
                "stable_noop",
                "transition_delicate",
                "fail_open_unknown",
            },
        )
        self.assertEqual(
            set(summary["covered_families"]),
            set(final_wording_diagnostic.REQUIRED_FAMILIES),
        )
        self.assertEqual(
            set(self.corpus["measurement_taxonomy"]),
            {"final_text", "other_stage", "contract_only"},
        )
        self.assertEqual(
            set(self.corpus["measurement_taxonomy"]["final_text"]),
            set(final_wording_diagnostic.FINAL_TEXT_PROPERTIES),
        )
        self.assertEqual(
            set(self.corpus["measurement_taxonomy"]["other_stage"]),
            set(final_wording_diagnostic.OTHER_STAGE_PROPERTIES),
        )
        self.assertEqual(
            set(self.corpus["measurement_taxonomy"]["contract_only"]),
            set(final_wording_diagnostic.CONTRACT_ONLY_PROPERTIES),
        )
        self.assertEqual(
            self.corpus["thresholds"]["countercase_formulation_worse_rate"],
            0.0,
        )

        serialized = json.dumps(self.corpus, ensure_ascii=False, sort_keys=True)
        for forbidden in (
            "[JUGEMENT HERMENEUTIQUE]",
            "Consigne d'enonciation:",
            "Effet d'enonciation:",
            "expected_response",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_corpus_rejects_missing_coverage_exact_output_and_taxonomy_confusion(self) -> None:
        missing = copy.deepcopy(self.corpus)
        missing["cases"] = [
            case for case in missing["cases"] if "hard_guard" not in case["families"]
        ]
        with self.assertRaises(ValueError):
            final_wording_diagnostic.validate_corpus(missing)

        exact_output = copy.deepcopy(self.corpus)
        exact_output["cases"][0]["expectations"]["final_text"]["expected_response"] = "fixture"
        with self.assertRaises(ValueError):
            final_wording_diagnostic.validate_corpus(exact_output)

        taxonomy_confusion = copy.deepcopy(self.corpus)
        taxonomy_confusion["cases"][0]["expectations"]["final_text"][
            "certainty_unchanged"
        ] = True
        with self.assertRaises(ValueError):
            final_wording_diagnostic.validate_corpus(taxonomy_confusion)


class Lot4C4FinalWordingScorerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.corpus = final_wording_diagnostic.load_corpus(REPO_ROOT)

    def test_phase_a_requires_provider_campaign_and_fake_cannot_claim_semantics(self) -> None:
        decision = final_wording_diagnostic.score_campaign(
            self.corpus,
            [],
            provider_results_observed=False,
            source_kind="fake",
            authoritative_existing_semantic_proof=False,
        )
        self.assertEqual(decision["decision"], "provider_campaign_required")
        self.assertEqual(decision["reason_codes"], ["fake_cannot_measure_final_wording"])
        self.assertFalse(decision["provider_results_observed"])

        fake_semantics = _perfect_provider_observations(self.corpus)
        for observation in fake_semantics:
            observation["source_kind"] = "fake"
        with self.assertRaises(ValueError):
            final_wording_diagnostic.score_campaign(
                self.corpus,
                fake_semantics,
                provider_results_observed=False,
                source_kind="fake",
                authoritative_existing_semantic_proof=False,
            )

    def test_complete_provider_observations_are_scored_without_text_or_regex(self) -> None:
        observations = _perfect_provider_observations(self.corpus)
        score = final_wording_diagnostic.score_campaign(
            self.corpus,
            observations,
            provider_results_observed=True,
            source_kind="main_model_provider",
            authoritative_existing_semantic_proof=False,
        )

        self.assertEqual(score["decision"], "pass")
        self.assertEqual(score["observed_pair_count"], 24)
        self.assertEqual(score["critical_failure_count"], 0)
        self.assertEqual(score["overapplication_count"], 0)
        self.assertEqual(score["raw_response_included"], False)

        mutations = {
            "psychologization": "treatment",
            "certainty_change": "treatment",
            "truth_or_evidence_change": "treatment",
            "masked_targets": ["question"],
            "overapplication": True,
        }
        for field, value in mutations.items():
            mutated = copy.deepcopy(observations)
            target = next(
                item
                for item in mutated
                if (
                    field != "overapplication"
                    or final_wording_diagnostic.case_by_id(self.corpus, item["case_id"])[
                        "enunciation_state"
                    ]
                    != "transition_delicate"
                )
            )
            target[field] = value
            with self.subTest(field=field):
                failed = final_wording_diagnostic.score_campaign(
                    self.corpus,
                    mutated,
                    provider_results_observed=True,
                    source_kind="main_model_provider",
                    authoritative_existing_semantic_proof=False,
                )
                self.assertEqual(failed["decision"], "fail")

        countercase_formulation_harm = copy.deepcopy(observations)
        countercase = next(
            item
            for item in countercase_formulation_harm
            if final_wording_diagnostic.case_by_id(self.corpus, item["case_id"])[
                "enunciation_state"
            ]
            != "transition_delicate"
        )
        countercase["formulation_fit"] = "worse"
        failed = final_wording_diagnostic.score_campaign(
            self.corpus,
            countercase_formulation_harm,
            provider_results_observed=True,
            source_kind="main_model_provider",
            authoritative_existing_semantic_proof=False,
        )
        self.assertEqual(failed["decision"], "fail")

        presence_regression = copy.deepcopy(observations)
        presence_regression[0]["presence_regression"] = "treatment"
        failed = final_wording_diagnostic.score_campaign(
            self.corpus,
            presence_regression,
            provider_results_observed=True,
            source_kind="main_model_provider",
            authoritative_existing_semantic_proof=False,
        )
        self.assertEqual(failed["decision"], "fail")

    def test_complete_call_ledger_with_missing_response_is_inconclusive(self) -> None:
        observations = _perfect_provider_observations(self.corpus)
        observations[0]["responses_complete"] = False
        score = final_wording_diagnostic.score_campaign(
            self.corpus,
            observations,
            provider_results_observed=True,
            source_kind="main_model_provider",
            authoritative_existing_semantic_proof=False,
        )
        self.assertEqual(score["decision"], "inconclusive")
        self.assertIn("provider_response_incomplete", score["reason_codes"])

    def test_scorer_rejects_incomplete_or_self_referential_observation_sets(self) -> None:
        observations = _perfect_provider_observations(self.corpus)
        with self.assertRaises(ValueError):
            final_wording_diagnostic.score_campaign(
                self.corpus,
                observations[:-1],
                provider_results_observed=True,
                source_kind="main_model_provider",
                authoritative_existing_semantic_proof=False,
            )

        self_referential = copy.deepcopy(observations)
        self_referential[0]["raw_response"] = "the scorer fixture judges itself"
        with self.assertRaises(ValueError):
            final_wording_diagnostic.score_campaign(
                self.corpus,
                self_referential,
                provider_results_observed=True,
                source_kind="main_model_provider",
                authoritative_existing_semantic_proof=False,
            )


class Lot4C4FinalWordingProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        raw = V1_MANIFEST_PATH.read_bytes()
        cls.manifest = json.loads(raw.decode("utf-8"))
        if hashlib.sha256(raw).hexdigest() != V1_MANIFEST_SHA256:
            raise AssertionError("v1 historical manifest changed")

    def test_v1_protocol_archive_freezes_model_schedule_and_cost_provenance(self) -> None:
        runtime_policy = self.manifest["runtime_policy"]
        schedule = self.manifest["schedule"]
        cost = self.manifest["cost"]
        self.assertEqual(self.manifest["status"], "provider_campaign_required")
        self.assertEqual(self.manifest["protocol_version"], "lot4c4_final_wording_provider_campaign_v1")
        self.assertEqual(runtime_policy["model"], "openai/gpt-5.1")
        self.assertEqual(runtime_policy["temperature"], 0.7)
        self.assertEqual(runtime_policy["top_p"], 1.0)
        self.assertEqual(runtime_policy["max_tokens"], 8192)
        self.assertEqual(runtime_policy["reasoning"], {"effort": "high", "exclude": True})
        self.assertEqual(runtime_policy["timeout_s"], 900)
        self.assertEqual(schedule["repetitions"], 2)
        self.assertEqual(
            schedule["repetition_rationale"],
            "minimum_repeat_to_expose_single_decode_variance_within_48_call_cap",
        )
        self.assertEqual(schedule["call_count"], 48)
        self.assertEqual(schedule["absolute_call_cap"], 48)
        self.assertEqual(
            schedule["sha256"],
            "8fbb172691549621e09849959b6120057df3abd34e1d233e8ce94853072c3b42",
        )
        self.assertGreater(cost["theoretical_max_cost_usd"], 0)
        self.assertLessEqual(
            cost["estimated_max_cost_usd"],
            cost["absolute_cost_cap_usd"],
        )
        self.assertEqual(
            runtime_policy,
            {
                "model": "openai/gpt-5.1",
                "temperature": 0.7,
                "top_p": 1.0,
                "max_tokens": 8192,
                "reasoning": {"effort": "high", "exclude": True},
                "timeout_s": 900,
                "provider": {"allow_fallbacks": False, "require_parameters": True},
                "transport": "standard",
                "batch": False,
                "flex": False,
                "priority": False,
                "retry_count": 0,
            },
        )

        synthetic_raw = "synthetic provider response that must not persist"
        record = final_wording_diagnostic.content_free_call_record(
            {
                "sequence": 1,
                "case_id": "synthetic-case",
                "repetition": 1,
                "blinded_arm": "A",
            },
            {
                "ok": True,
                "status_code": 200,
                "finish_reason": "stop",
                "model": "openai/gpt-5.1",
                "provider": "synthetic",
                "raw_text": synthetic_raw,
                "usage": {"prompt_tokens": 10, "completion_tokens": 4},
                "cost_estimate_usd": 0.001,
            },
        )
        self.assertEqual(record["response_chars"], len(synthetic_raw))
        self.assertEqual(len(record["response_sha256"]), 64)
        self.assertFalse(record["raw_response_included"])
        self.assertNotIn(synthetic_raw, json.dumps(record, sort_keys=True))

    def test_v1_historical_dry_run_is_refused_before_output(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output), self.assertRaisesRegex(
            ValueError,
            "freeze_manifest_mismatch",
        ):
            final_wording_diagnostic.main(
                [
                    "--repo-root", str(REPO_ROOT),
                    "--freeze-commit", str(self.manifest["baseline_head"]),
                    "--dry-run",
                ]
            )
        self.assertEqual(output.getvalue(), "")


class Lot4C4RealCoordinatorFakeProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def test_real_coordinator_main_builder_json_stream_and_fail_open_are_structural_only(self) -> None:
        stable_outcomes = [
            primary_signal(affective_signal("apaisement", 7)) for _ in range(4)
        ]
        transition_outcomes = [
            *[primary_signal(affective_signal("apaisement", 7)) for _ in range(3)],
            primary_signal(affective_signal("colere", 9)),
        ]
        stable = exercise_stimmung_dialogue(
            self.server,
            outcomes=stable_outcomes,
            stream=False,
        )
        transition = exercise_stimmung_dialogue(
            self.server,
            outcomes=transition_outcomes,
            stream=False,
        )
        transition_stream = exercise_stimmung_dialogue(
            self.server,
            outcomes=transition_outcomes,
            stream=True,
        )
        fail_open = exercise_stimmung_dialogue(
            self.server,
            outcomes=[
                primary_signal(affective_signal("apaisement", 7)) for _ in range(4)
            ],
            stream=False,
            validation_fail_after_turns=[4],
        )

        proof = final_wording_diagnostic.validate_fake_pipeline_proof(
            stable=stable,
            transition=transition,
            transition_stream=transition_stream,
            fail_open=fail_open,
        )
        self.assertEqual(proof["decision"], "provider_campaign_required")
        self.assertEqual(proof["main_provider_semantics"], "not_measured")
        self.assertEqual(proof["manifest_schema_version"], "main_payload_manifest_v1")
        self.assertEqual(proof["continuity_capsule_count"], 1)
        self.assertEqual(proof["assistant_final_count"], 1)
        self.assertTrue(proof["json_stream_contract_equal"])
        self.assertTrue(proof["assistant_provenance_preserved"])
        self.assertTrue(proof["epistemic_fields_equal"])

        mutations = []
        removed = copy.deepcopy(transition)
        removed["main_messages"][-1][0]["content"] = removed["main_messages"][-1][0][
            "content"
        ].replace("Effet d'enonciation: delicate_expression", "")
        mutations.append(("directive_removed", removed))

        duplicated = copy.deepcopy(transition)
        duplicated["main_messages"][-1].append(
            copy.deepcopy(duplicated["main_messages"][-1][0])
        )
        mutations.append(("directive_duplicated", duplicated))

        raw = copy.deepcopy(transition)
        raw["main_messages"][-1].append(
            {"role": "system", "content": "stimmung_input active_tones"}
        )
        mutations.append(("raw_stimmung", raw))

        epistemic = copy.deepcopy(transition)
        epistemic["node_calls"][-1]["validated_output"]["epistemic_effect"] = {
            "effect": "unknown",
            "source": "fail_open",
            "reason_code": "unknown_error",
        }
        mutations.append(("epistemic_change", epistemic))

        capsule_removed = copy.deepcopy(transition)
        capsule_removed["main_messages"][-1].pop()
        mutations.append(("capsule_removed", capsule_removed))

        capsule_moved = copy.deepcopy(transition)
        capsule = capsule_moved["main_messages"][-1].pop()
        capsule_moved["main_messages"][-1].insert(0, capsule)
        mutations.append(("capsule_moved", capsule_moved))

        capsule_duplicated = copy.deepcopy(transition)
        capsule_duplicated["main_messages"][-1].append(
            copy.deepcopy(capsule_duplicated["main_messages"][-1][-1])
        )
        mutations.append(("capsule_duplicated", capsule_duplicated))

        manifest = copy.deepcopy(transition)
        manifest["manifests"][-1]["continuity_capsule"]["injected_count"] = 0
        mutations.append(("manifest_incoherent", manifest))

        final_lock = copy.deepcopy(transition)
        final_lock["manifests"][-1]["final_response_lock"]["present"] = True
        final_lock["manifests"][-1]["main_model_called"] = False
        mutations.append(("final_lock_bypassed", final_lock))

        for kind, mutant in mutations:
            with self.subTest(kind=kind):
                with self.assertRaises(ValueError):
                    final_wording_diagnostic.validate_fake_pipeline_proof(
                        stable=stable,
                        transition=mutant,
                        transition_stream=transition_stream,
                        fail_open=fail_open,
                    )


if __name__ == "__main__":
    unittest.main()
