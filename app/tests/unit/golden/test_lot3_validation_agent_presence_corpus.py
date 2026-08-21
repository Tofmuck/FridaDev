"""Discoverable Lot 3 goldens for the validation-agent Presence corpus."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory


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

    def test_presence_corpus_is_reviewable_complete_and_still_pending_human_validation(self) -> None:
        self.assertEqual(self.document["schema_version"], "validation_presence_corpus_v1")
        self.assertEqual(self.document["human_validation_status"], "pending")
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
        self.assertEqual(artifact["human_validation_status"], "pending")
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


if __name__ == "__main__":
    unittest.main()
