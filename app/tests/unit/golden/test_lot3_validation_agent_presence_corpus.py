"""Discoverable Lot 3 goldens for the validation-agent Presence corpus."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch


def _repo_root() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "benchmark").exists() and (parent / "app").exists():
            return parent
    raise RuntimeError("Unable to resolve repo root")


REPO_ROOT = _repo_root()
APP_DIR = REPO_ROOT / "app"
for import_root in (REPO_ROOT, APP_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from agenda.chat_runtime import AgendaChatResult
from agenda.response_rendering import AgendaFinalResponseLock
from benchmark.core import openrouter
from benchmark.core.campaign import CampaignConfig
from benchmark.suites.validation_agent import adapter
from benchmark.suites.validation_agent import campaign
from benchmark.suites.validation_agent import scorer
from biblio.answer_object import BiblioFinalResponseLock
from biblio.chat_runtime import BiblioChatResult
from core import chat_agent_lane_orchestration
from core.hermeneutic_node.validation import validation_contract
from core.hermeneutic_node.validation import validation_messages


def _model_output(posture: str, regime: str, *, reason: str = "synthetic reason") -> str:
    return json.dumps(
        {
            "schema_version": "v1",
            "final_judgment_posture": posture,
            "final_output_regime": regime,
            "arbiter_reason": reason,
        },
        ensure_ascii=False,
    )


class ValidationAgentPresenceCorpusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture_path = REPO_ROOT / adapter.PRESENCE_FIXTURE_PATH
        cls.document = adapter.load_fixture_document(cls.fixture_path)
        cls.cases = cls.document["cases"]

    def _case(self, case_id: str) -> dict:
        return next(case for case in self.cases if case["id"] == case_id)

    def test_presence_corpus_records_the_operator_validation_without_semantic_changes(self) -> None:
        self.assertEqual(self.document["schema_version"], "validation_presence_corpus_v1")
        self.assertEqual(self.document["human_validation_status"], "validated")
        self.assertEqual(self.document["human_validation_date"], "2026-08-21")
        self.assertEqual(
            self.document["human_validation_basis"],
            "operator_accepted_fixture_without_changes",
        )
        expected_fingerprint = "646cc504d057021d870b16628b07c5ace83c711cbe36c489c1f0ec62049d2ed1"
        self.assertEqual(self.document["validated_contract_sha256"], expected_fingerprint)
        self.assertEqual(adapter.presence_contract_sha256(self.document), expected_fingerprint)
        self.assertEqual(len(self.cases), 24)
        self.assertEqual(len(self.document["runtime_boundary_cases"]), 6)

        required_families = {
            "received_deposit",
            "shared_closure",
            "authorized_silence",
            "short_question",
            "direct_request",
            "implicit_request",
            "distress",
            "risk",
            "vulnerability",
            "material_instruction",
            "substantive_ambiguity",
            "correction",
            "disagreement",
            "irony",
            "punctuation_only",
            "fragment_only",
            "recent_assistant_changes_meaning",
            "web_hard_guard",
            "truncated_context",
            "missing_secondary_support",
        }
        families = {case["semantic_family"] for case in self.cases}
        self.assertTrue(required_families.issubset(families), sorted(required_families - families))

        boundary_kinds = {case["boundary_kind"] for case in self.document["runtime_boundary_cases"]}
        self.assertEqual(
            boundary_kinds,
            {
                "presence_without_final_lock",
                "biblio_final_lock",
                "agenda_final_lock",
                "agenda_biblio_final_lock_conflict",
                "invalid_final_lock_absent",
                "provider_fail_open",
            },
        )
        for item in [*self.cases, *self.document["runtime_boundary_cases"]]:
            self.assertTrue(item["id"])
            self.assertTrue(item["semantic_family"])
            self.assertIn(item["false_presence_severity"], {"low", "medium", "high", "critical"})
            self.assertTrue(item["human_justification"])
            self.assertIn("synthetic", item["synthetic_provenance_tags"])

        thresholds = self.document["proposed_safety_thresholds"]
        self.assertEqual(thresholds["critical_or_high_false_presence_max"], 0)
        self.assertEqual(thresholds["hard_guard_or_fail_open_presence_max"], 0)
        self.assertEqual(thresholds["final_lock_priority_violation_max"], 0)
        self.assertEqual(thresholds["schema_valid_rate_min"], 1.0)

    def test_benchmark_reuses_runtime_contract_messages_and_hard_guards(self) -> None:
        self.assertEqual(
            set(adapter.ALLOWED_OUTPUT_REGIMES),
            set(validation_contract.ALLOWED_FINAL_OUTPUT_REGIMES),
        )
        self.assertIn("presence", adapter.ALLOWED_OUTPUT_REGIMES)

        case = self._case("P3-019")
        prompt = (REPO_ROOT / adapter.PROMPT_PATH).read_text(encoding="utf-8").strip()
        payload = adapter.build_payload(case, "synthetic/model", prompt)
        primary = adapter.build_primary_verdict(case)
        canonical = adapter.build_canonical_inputs(case)
        hard_guards = adapter.evaluate_hard_guards(primary, canonical)
        expected_messages = validation_messages.build_messages(
            system_prompt=prompt,
            primary_verdict=primary,
            justifications=case.get("justifications") or {},
            validation_dialogue_context=adapter.build_validation_dialogue_context(case),
            canonical_inputs=canonical,
            hard_guard_payload=hard_guards,
        )

        self.assertEqual(payload["messages"], expected_messages)
        self.assertEqual(hard_guards["hard_guard_effect"], "answer_forbidden")
        self.assertIn("simple|meta|presence", payload["messages"][1]["content"])

    def test_presence_scorer_rejects_controlled_semantic_mutations_without_reading_dialogue_text(self) -> None:
        positive = self._case("P3-001")
        forbidden = self._case("P3-005")

        exact = scorer.score_output(positive, _model_output("answer", "presence"))
        missed = scorer.score_output(positive, _model_output("answer", "simple"))
        bureaucratic = scorer.score_output(positive, _model_output("clarify", "simple"))
        false_presence = scorer.score_output(forbidden, _model_output("answer", "presence"))

        self.assertTrue(exact["pass"])
        self.assertFalse(exact["false_presence"])
        self.assertFalse(exact["missed_presence"])
        self.assertFalse(missed["pass"])
        self.assertTrue(missed["missed_presence"])
        self.assertTrue(bureaucratic["bureaucratic_non_answer"])
        self.assertTrue(false_presence["false_presence"])
        self.assertFalse(false_presence["pass"])
        self.assertNotIn("arbiter_reason", exact)
        self.assertTrue(exact["arbiter_reason_present"])
        self.assertGreater(exact["arbiter_reason_chars"], 0)

        summary = scorer.summarize_model_results([exact, missed, bureaucratic, false_presence])
        self.assertEqual(summary["false_presence"], 1)
        self.assertEqual(summary["missed_presence"], 2)
        self.assertEqual(summary["bureaucratic_non_answer"], 1)
        self.assertEqual(scorer.provisional_verdict(summary), "exclure")

        scorer_source = (REPO_ROOT / "benchmark/suites/validation_agent/scorer.py").read_text(encoding="utf-8")
        self.assertNotIn("import re", scorer_source)
        self.assertNotIn('case["dialogue"]', scorer_source)

    def test_context_pair_changes_the_human_contract_not_a_lexical_rule(self) -> None:
        with_context = self._case("P3-017")
        without_context = self._case("P3-018")
        self.assertEqual(with_context["comparison_pair"], "context_pair_01")
        self.assertEqual(without_context["comparison_pair"], "context_pair_01")
        self.assertNotEqual(with_context["dialogue"], without_context["dialogue"])
        self.assertEqual(with_context["expected"]["presence_policy"], "required")
        self.assertEqual(without_context["expected"]["presence_policy"], "forbidden")

    def test_runtime_boundary_matrix_uses_real_final_lock_resolver(self) -> None:
        presence_result = type(
            "PresenceResult",
            (),
            {
                "status": "ok",
                "validated_output": {
                    "final_judgment_posture": "answer",
                    "final_output_regime": "presence",
                },
            },
        )()

        for boundary in self.document["runtime_boundary_cases"]:
            if boundary["boundary_kind"] == "provider_fail_open":
                continue
            locks = set(boundary.get("final_lock_candidates") or [])
            agenda_lock = (
                AgendaFinalResponseLock(ok=True, content="AGENDA_SENTINEL")
                if "agenda" in locks
                else AgendaFinalResponseLock(ok=False, content="")
                if "agenda_invalid" in locks
                else None
            )
            biblio_lock = (
                BiblioFinalResponseLock(
                    ok=True,
                    reason_code="synthetic_biblio_final",
                    content="BIBLIO_SENTINEL",
                )
                if "biblio" in locks
                else None
            )
            agenda_result = AgendaChatResult(
                enabled=bool(agenda_lock),
                used=bool(agenda_lock and agenda_lock.ok),
                status="ok",
                reason_code="synthetic",
                observability_payload={},
                final_response_lock=agenda_lock,
            )
            biblio_result = BiblioChatResult(
                enabled=bool(biblio_lock),
                used=bool(biblio_lock),
                reason_code="synthetic",
                query_kind="not_requested",
                observability_payload={},
                final_response_lock=biblio_lock,
            )
            resolved = chat_agent_lane_orchestration.resolve_agent_lane_assistant_output(
                biblio_result=biblio_result,
                agenda_result=agenda_result,
                validated_result=presence_result,
            )
            selected = resolved.assistant_response_override
            self.assertIsNotNone(selected, boundary["id"])
            self.assertEqual(selected.source, boundary["expected_final_source"], boundary["id"])

            mutated = copy.deepcopy(boundary)
            mutated["expected_final_source"] = "hermeneutic_presence"
            if selected.source != "hermeneutic_presence":
                self.assertNotEqual(selected.source, mutated["expected_final_source"])

    def test_fail_open_and_web_hard_guard_cannot_become_presence(self) -> None:
        fail_open = validation_contract.build_fail_open_result(
            primary_verdict={},
            reason_code="synthetic_provider_failure",
            model="synthetic/fallback",
            applied_hard_guards=[],
            hard_guard_effect=None,
        )
        override = chat_agent_lane_orchestration._hermeneutic_presence_assistant_response_override(fail_open)
        self.assertIsNone(override)

        web_case = self._case("P3-019")
        web_mutation = scorer.score_output(web_case, _model_output("answer", "presence"))
        self.assertTrue(web_mutation["hard_guard_violation"])
        self.assertTrue(web_mutation["false_presence"])
        self.assertFalse(web_mutation["pass"])

    def test_presence_campaign_artifact_is_content_free_and_rejects_raw_mutations(self) -> None:
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "results"
            config = CampaignConfig(
                campaign_id="lot3-presence-dry-run",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=output_dir,
                models=["synthetic/current-validation-model"],
                dry_run=True,
                timeout_s=1,
            )
            result = campaign.run_validation_agent_campaign(
                config=config,
                client=None,
                fixture_path=self.fixture_path,
            )
            artifact = json.loads(Path(result["json_path"]).read_text(encoding="utf-8"))
            markdown = Path(result["markdown_path"]).read_text(encoding="utf-8")

        self.assertEqual(artifact["corpus_schema_version"], "validation_presence_corpus_v1")
        self.assertEqual(artifact["human_validation_status"], "validated")
        self.assertTrue(artifact["content_free_decision_artifact"])
        self.assertEqual(artifact["case_count"], 24)
        self.assertEqual(artifact["runtime_boundary_case_count"], 6)
        self.assertEqual(artifact["caller"], "validation_agent")
        first_call = artifact["results"][0]["calls"][0]
        self.assertEqual(first_call["requested_model"], "synthetic/current-validation-model")
        self.assertEqual(first_call["observed_model"], "")
        self.assertEqual(first_call["observed_provider"], "")
        self.assertEqual(first_call["provider_source"], "dry_run")
        campaign.assert_presence_campaign_content_free(artifact)
        serialized = json.dumps(artifact, ensure_ascii=False)
        self.assertNotIn(self._case("P3-001")["dialogue"][-1]["content"], serialized)
        self.assertNotIn(self._case("P3-001")["human_justification"], serialized)
        self.assertNotIn("synthetic reason", serialized)
        self.assertNotIn(self._case("P3-001")["dialogue"][-1]["content"], markdown)

        for key, value in (
            ("dialogue", [{"role": "user", "content": "RAW_SENTINEL"}]),
            ("arbiter_reason", "RAW_REASON_SENTINEL"),
            ("raw_text", "RAW_PROVIDER_SENTINEL"),
        ):
            mutated = copy.deepcopy(artifact)
            mutated["results"][0]["calls"][0][key] = value
            with self.subTest(key=key):
                with self.assertRaises(ValueError):
                    campaign.assert_presence_campaign_content_free(mutated)

    def test_documented_script_entrypoint_runs_hermetically_with_existing_pythonpath(self) -> None:
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "results"
            completed = subprocess.run(
                [
                    sys.executable,
                    "benchmark/run_benchmark.py",
                    "--suite",
                    "validation_agent",
                    "--validation-agent-corpus",
                    "presence",
                    "--dry-run",
                    "--campaign-id",
                    "lot3-presence-entrypoint-dry-run",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertTrue((output_dir / "lot3-presence-entrypoint-dry-run.json").is_file())
            self.assertTrue((output_dir / "lot3-presence-entrypoint-dry-run.md").is_file())

    def test_role_aware_entrypoint_records_fallback_reasoning_without_exposing_it(self) -> None:
        with TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "results"
            completed = subprocess.run(
                [
                    sys.executable,
                    "benchmark/run_benchmark.py",
                    "--suite",
                    "validation_agent",
                    "--validation-agent-corpus",
                    "presence",
                    "--validation-agent-primary-model",
                    "synthetic/primary",
                    "--validation-agent-fallback-model",
                    "synthetic/fallback",
                    "--validation-agent-fallback-reasoning-effort",
                    "low",
                    "--validation-agent-max-tokens",
                    "300",
                    "--dry-run",
                    "--campaign-id",
                    "lot3-presence-reasoning-dry-run",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=REPO_ROOT,
                check=False,
                capture_output=True,
                text=True,
                timeout=30,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            artifact = json.loads(
                (output_dir / "lot3-presence-reasoning-dry-run.json").read_text(
                    encoding="utf-8"
                )
            )

        self.assertEqual(artifact["generation_params"]["max_tokens"], 300)
        self.assertEqual(
            artifact["reasoning_efforts"],
            {"synthetic/fallback": "low"},
        )
        by_model = {result["model"]: result for result in artifact["results"]}
        fallback_call = by_model["synthetic/fallback"]["calls"][0]
        primary_call = by_model["synthetic/primary"]["calls"][0]
        self.assertEqual(
            fallback_call["request_signature"]["reasoning"],
            {"effort": "low", "exclude": True},
        )
        self.assertNotIn("reasoning", primary_call["request_signature"])
        self.assertEqual(by_model["synthetic/fallback"]["summary"]["reasoning_tokens_total"], 0)
        campaign.assert_presence_campaign_content_free(artifact)

    def test_live_presence_screening_has_no_fake_runtime_roles_and_cannot_close_decision(self) -> None:
        class SyntheticClient:
            @staticmethod
            def chat_completion(payload: dict, *, caller: str, timeout_s: int) -> dict:
                return {
                    "ok": True,
                    "status_code": 200,
                    "elapsed_ms": 1.0,
                    "error": None,
                    "raw_text": _model_output("answer", "simple"),
                    "finish_reason": "stop",
                    "native_finish_reason": "stop",
                    "usage": {
                        "prompt_tokens": 10,
                        "completion_tokens": 12,
                        "completion_tokens_details": {"reasoning_tokens": 4},
                    },
                    "cost_estimate_usd": 0.001,
                    "cost_estimate_source": "synthetic",
                    "generation_id": "synthetic-screening",
                    "model": payload["model"],
                    "provider": "synthetic-provider",
                }

        with TemporaryDirectory() as tmp:
            config = CampaignConfig(
                campaign_id="lot3-presence-screening-live",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=Path(tmp) / "results",
                models=["openai/gpt-5.6-luna"],
                dry_run=False,
                timeout_s=15,
            )
            result = campaign.build_validation_agent_campaign(
                config=config,
                client=SyntheticClient(),
                fixture_path=self.fixture_path,
                reasoning_efforts={"openai/gpt-5.6-luna": "low"},
                repetitions=1,
                screening=True,
            )

            self.assertEqual(result["model_roles"], {"openai/gpt-5.6-luna": "unspecified"})
            self.assertTrue(result["screening"])
            self.assertFalse(result["benchmark_decision_ready"])
            self.assertEqual(result["planned_call_count"], 24)
            self.assertEqual(result["results"][0]["summary"]["reasoning_tokens_total"], 96)
            campaign.assert_presence_campaign_content_free(result)
            screening_markdown = campaign.render_markdown_report(result)
            self.assertIn("candidats de criblage", screening_markdown)
            self.assertNotIn("roles primaire", screening_markdown)

            with self.assertRaisesRegex(ValueError, "one repetition"):
                campaign.build_validation_agent_campaign(
                    config=config,
                    client=SyntheticClient(),
                    fixture_path=self.fixture_path,
                    repetitions=2,
                    screening=True,
                )

    def test_retained_gpt56_artifacts_prove_reasoning_cost_and_candidate_rejection(self) -> None:
        result_dir = REPO_ROOT / "benchmark/results/validation_agent"
        screening = json.loads(
            (result_dir / "2026-08-21-lot3-presence-gpt56-screening.json").read_text(
                encoding="utf-8"
            )
        )
        low = json.loads(
            (result_dir / "2026-08-21-lot3-presence-luna-low-max300.json").read_text(
                encoding="utf-8"
            )
        )
        medium = json.loads(
            (result_dir / "2026-08-21-lot3-presence-luna-medium-max500.json").read_text(
                encoding="utf-8"
            )
        )

        self.assertEqual(screening["completed_call_count"], 144)
        self.assertEqual(len(screening["results"]), 6)
        screening_by_key = {
            (result["model"], result["reasoning_effort_requested"]): result
            for result in screening["results"]
        }
        self.assertEqual(
            screening_by_key[("openai/gpt-5.6-luna", "none")]["summary"][
                "reasoning_tokens_total"
            ],
            0,
        )
        self.assertGreater(
            screening_by_key[("openai/gpt-5.6-luna", "low")]["summary"][
                "reasoning_tokens_total"
            ],
            0,
        )
        self.assertGreater(
            screening_by_key[("openai/gpt-5.6-luna", "medium")]["summary"][
                "reasoning_tokens_total"
            ],
            screening_by_key[("openai/gpt-5.6-luna", "low")]["summary"][
                "reasoning_tokens_total"
            ],
        )
        self.assertLess(
            screening_by_key[("openai/gpt-5.6-luna", "none")]["summary"][
                "cost_estimate_usd"
            ]
            * 5,
            screening_by_key[("openai/gpt-5.6-terra", "none")]["summary"][
                "cost_estimate_usd"
            ],
        )

        for artifact, effort, max_tokens in (
            (low, "low", 300),
            (medium, "medium", 500),
        ):
            with self.subTest(effort=effort):
                campaign.assert_presence_campaign_content_free(artifact)
                self.assertEqual(artifact["planned_call_count"], 144)
                self.assertEqual(artifact["repetitions"], 3)
                self.assertEqual(artifact["generation_params"]["max_tokens"], max_tokens)
                self.assertEqual(
                    artifact["reasoning_efforts"],
                    {"openai/gpt-5.6-luna": effort},
                )
                self.assertTrue(artifact["provider_route_observability_complete"])
                self.assertFalse(artifact["benchmark_decision_ready"])
                self.assertFalse(artifact["production_runtime_changed"])
                fallback = next(
                    result for result in artifact["results"] if result["model_role"] == "fallback"
                )
                self.assertFalse(fallback["summary"]["safety_thresholds_met"])
                self.assertIn(
                    "critical_or_high_false_presence",
                    fallback["summary"]["safety_threshold_failures"],
                )
                self.assertGreater(fallback["summary"]["reasoning_tokens_total"], 0)

        self.assertIn(
            "repetition_stability",
            next(
                result for result in medium["results"] if result["model_role"] == "fallback"
            )["summary"]["safety_threshold_failures"],
        )

    def test_campaign_records_runtime_timeout_model_roles_and_three_repetitions(self) -> None:
        with TemporaryDirectory() as tmp:
            config = CampaignConfig(
                campaign_id="lot3-presence-repetition-dry-run",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=Path(tmp) / "results",
                models=["synthetic/primary", "synthetic/fallback"],
                dry_run=True,
                timeout_s=15,
            )
            try:
                result = campaign.build_validation_agent_campaign(
                    config=config,
                    client=None,
                    fixture_path=self.fixture_path,
                    model_roles={
                        "synthetic/primary": "primary",
                        "synthetic/fallback": "fallback",
                    },
                    repetitions=3,
                )
            except TypeError as exc:
                self.fail(f"campaign repetition contract missing: {exc}")

        self.assertEqual(result["generation_params"]["timeout_s"], 15)
        self.assertEqual(result["timeout_s"], 15)
        self.assertEqual(result["repetitions"], 3)
        self.assertEqual(
            result["model_roles"],
            {"synthetic/primary": "primary", "synthetic/fallback": "fallback"},
        )
        for model_result in result["results"]:
            calls = model_result["calls"]
            self.assertEqual(len(calls), 72)
            self.assertEqual({call["repetition_index"] for call in calls}, {1, 2, 3})
            self.assertEqual(
                {call["model_role"] for call in calls},
                {result["model_roles"][model_result["model"]]},
            )
            summary = model_result["summary"]
            self.assertEqual(summary["semantic_cases"], 24)
            self.assertEqual(summary["repetition_stability_rate"], 1.0)
            self.assertEqual(summary["required_presence_rate"], 1.0)
            self.assertTrue(summary["safety_thresholds_met"])
        markdown = campaign.render_markdown_report(result)
        self.assertIn("primaire et fallback", markdown)
        self.assertIn("Stabilite", markdown)
        self.assertIn("dry-run", markdown)
        self.assertNotIn("au moins un seuil de securite echoue", markdown)
        self.assertNotIn("Elle ne benchmarke pas le fallback", markdown)

    def test_openrouter_client_retains_bounded_observed_route_metadata(self) -> None:
        class SyntheticResponse:
            status_code = 200
            content = b"synthetic"

            @staticmethod
            def json() -> dict:
                return {
                    "id": "generation-synthetic-001",
                    "model": "observed/model",
                    "provider": "observed-provider",
                    "choices": [
                        {
                            "message": {"content": "{}"},
                            "finish_reason": "stop",
                            "native_finish_reason": "stop",
                        }
                    ],
                    "usage": {"prompt_tokens": 1, "completion_tokens": 1},
                }

        client = openrouter.OpenRouterClient(
            openrouter.OpenRouterConfig(
                base_url="https://synthetic.invalid/api/v1",
                api_key="synthetic-key",
            )
        )
        with patch.object(openrouter.requests, "post", return_value=SyntheticResponse()):
            observed = client.chat_completion(
                {"model": "requested/model", "messages": []},
                caller="validation_agent",
                timeout_s=15,
            )

        self.assertEqual(observed.get("generation_id"), "generation-synthetic-001")
        self.assertEqual(observed.get("model"), "observed/model")
        self.assertEqual(observed.get("provider"), "observed-provider")

    def test_validated_presence_corpus_rejects_a_semantic_mutation(self) -> None:
        mutated = json.loads(json.dumps(self.document))
        for case in mutated["cases"]:
            case.pop("dialogue_ref", None)
        mutated["cases"][0]["expected"]["final_output_regime"] = "simple"

        with TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "mutated-presence.json"
            fixture_path.write_text(json.dumps(mutated), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "fingerprint mismatch"):
                adapter.load_fixture_document(fixture_path)

    def test_live_presence_campaign_rejects_unvalidated_or_unbounded_runs(self) -> None:
        pending = json.loads(json.dumps(self.document))
        pending["human_validation_status"] = "pending"
        for case in pending["cases"]:
            case.pop("dialogue_ref", None)

        with TemporaryDirectory() as tmp:
            fixture_path = Path(tmp) / "pending-presence.json"
            fixture_path.write_text(json.dumps(pending), encoding="utf-8")
            config = CampaignConfig(
                campaign_id="lot3-presence-unvalidated-live",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=Path(tmp) / "results",
                models=["synthetic/primary", "synthetic/fallback"],
                dry_run=False,
                timeout_s=15,
            )
            with self.assertRaisesRegex(ValueError, "human-validated corpus"):
                campaign.build_validation_agent_campaign(
                    config=config,
                    client=None,
                    fixture_path=fixture_path,
                    model_roles={
                        "synthetic/primary": "primary",
                        "synthetic/fallback": "fallback",
                    },
                    repetitions=1,
                )

            oversized_config = CampaignConfig(
                campaign_id="lot3-presence-over-call-cap",
                suite="validation_agent",
                repo_root=REPO_ROOT,
                output_dir=Path(tmp) / "results",
                models=["synthetic/one", "synthetic/two", "synthetic/three"],
                dry_run=True,
                timeout_s=15,
            )
            with self.assertRaisesRegex(ValueError, "144-call safety cap"):
                campaign.build_validation_agent_campaign(
                    config=oversized_config,
                    client=None,
                    fixture_path=self.fixture_path,
                    repetitions=3,
                )


if __name__ == "__main__":
    unittest.main()
