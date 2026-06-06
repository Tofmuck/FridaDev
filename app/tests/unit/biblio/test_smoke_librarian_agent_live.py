from __future__ import annotations

import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import chat_runtime
from biblio import observability
from biblio import passage_extractor as extractor
from biblio import prompt_lane
from biblio import smoke_librarian_agent_live as smoke


RAW_PASSAGE = "RAW_AGENT_SMOKE_PASSAGE_MUST_NOT_APPEAR"
RAW_QUERY = "RAW AGENT SMOKE QUERY MUST NOT APPEAR"


class BiblioLibrarianAgentSmokeLiveTests(unittest.TestCase):
    def test_default_agent_mode_is_active_and_off_is_explicit_only(self) -> None:
        self.assertEqual(smoke.DEFAULT_AGENT_MODE, "active")
        self.assertNotEqual(smoke.DEFAULT_AGENT_MODE, "off")
        self.assertEqual(
            smoke._config_for_agent_mode(smoke.DEFAULT_AGENT_MODE).BIBLIO_LIBRARIAN_AGENT_MODE,
            "active",
        )
        self.assertEqual(
            smoke._config_for_agent_mode("off").BIBLIO_LIBRARIAN_AGENT_MODE,
            "off",
        )

    def test_matrix_contains_required_product_families_without_raw_case_ids(self) -> None:
        messages = "\n".join(case.message for case in smoke.DEFAULT_SMOKE_CASES)
        encoded_public_matrix = json.dumps(
            [{"case_id": case.case_id, "case_kind": case.case_kind} for case in smoke.DEFAULT_SMOKE_CASES],
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertIn("Kant", messages)
        self.assertTrue("maïeutique" in messages or "maieutique" in messages)
        self.assertIn("Quels ouvrages", messages)
        self.assertNotIn("Kant", encoded_public_matrix)
        self.assertNotIn("Theetete", encoded_public_matrix)
        self.assertNotIn("maieutique", encoded_public_matrix)

    def test_smoke_record_is_content_free_even_when_lane_contains_passage(self) -> None:
        records = smoke.run_smokes(
            cases=(smoke.BiblioLibrarianProductSmokeCase("P01", "range_extract", RAW_QUERY),),
            turn_runner=_fake_turn_runner,
            raw_markers=(RAW_PASSAGE, RAW_QUERY),
        )

        self.assertEqual(len(records), 1)
        record = records[0]
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)
        self.assertEqual(record["case_id"], "P01")
        self.assertEqual(record["status"], "extracted")
        self.assertEqual(record["query_kind"], "extract_range")
        self.assertTrue(record["lane_injected"])
        self.assertEqual(record["passage_count"], 1)
        self.assertEqual(record["payload_objects_retained"], 0)
        self.assertFalse(record["raw_marker_leaks"])
        self.assertEqual(record["product_expectation_status"], "met")
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertEqual(record["agent_plan_case_id"], "")
        self.assertEqual(record["agent_plan_product_method"], "")
        self.assertFalse(record["state_present_after"])

    def test_smoke_record_exposes_agent_plan_case_and_method_content_free(self) -> None:
        fake_result = _fake_turn_runner(
            {"biblio_enabled": True},
            user_msg=RAW_QUERY,
        )
        fake_result = chat_runtime.BiblioChatResult(
            enabled=fake_result.enabled,
            used=fake_result.used,
            reason_code=fake_result.reason_code,
            query_kind=fake_result.query_kind,
            context_result=fake_result.context_result,
            passage_result=fake_result.passage_result,
            prompt_lane=fake_result.prompt_lane,
            biblio_state=fake_result.biblio_state,
            state_transition=fake_result.state_transition,
            librarian_agent_result=_fake_librarian_agent_result(
                case_id="P03",
                product_method="work_lookup",
                answer_mode="tool",
            ),
            observability_payload=observability.build_biblio_event_payload(
                enabled=True,
                used=True,
                query_kind="agent_first",
                prompt_lane=fake_result.prompt_lane,
                librarian_agent=_fake_librarian_agent_result(
                    case_id="P03",
                    product_method="work_lookup",
                    answer_mode="tool",
                ),
                product_case_id="P03",
                product_method="work_lookup",
                product_truth="exact",
                status="agent_first_executed",
                reason_code="biblio_agent_first_plan_executed",
            ),
        )

        records = smoke.run_smokes(
            cases=(smoke.BiblioLibrarianProductSmokeCase("P03", "work_lookup", RAW_QUERY),),
            turn_runner=lambda *_args, **_kwargs: fake_result,
            raw_markers=(RAW_PASSAGE, RAW_QUERY),
        )

        self.assertEqual(records[0]["agent_plan_case_id"], "P03")
        self.assertEqual(records[0]["agent_plan_product_method"], "work_lookup")
        self.assertEqual(records[0]["agent_plan_answer_mode"], "tool")
        self.assertEqual(records[0]["product_case_id"], "P03")
        self.assertEqual(records[0]["product_method_effective"], "work_lookup")
        self.assertEqual(records[0]["product_truth"], "exact")

    def test_no_signal_work_lookup_with_local_plan_is_not_product_met(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P03", "work_lookup", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "no_signal",
                "status": "not_used",
                "endpoint_count": 0,
                "dialogue_tool_call_count": 1,
                "agent_mode": "off",
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "failed")
        self.assertNotEqual(expectations["product_expectation_status"], "met")

    def test_work_lookup_agent_plan_only_is_not_product_met_without_catalogue(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P03", "work_lookup", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "no_signal",
                "status": "not_used",
                "endpoint_count": 0,
                "agent_mode": "active",
                "agent_present": True,
                "agent_model_called": True,
                "agent_candidate_plan_present": True,
                "agent_plan_tool_names": ["catalog_search"],
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "failed")
        self.assertEqual(expectations["agent_expectation_status"], "met")
        self.assertEqual(expectations["product_expectation_status"], "failed")

    def test_fallback_repair_is_not_reported_as_model_agent_success(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P04", "range_extract", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "agent_first",
                "status": "agent_first_executed",
                "endpoint_count": 2,
                "context_call_count": 1,
                "passage_count": 1,
                "lane_injected": True,
                "agent_mode": "active",
                "agent_present": True,
                "agent_model_called": True,
                "agent_candidate_plan_present": True,
                "agent_status": "fallback_deterministic",
                "agent_reason_code": "biblio_librarian_agent_tool_not_executable",
                "agent_execution_scope": "agent_first",
                "agent_plan_tool_names": [],
                "agent_executed_tool_names": ["catalog_search", "passage_context"],
                "agent_tool_execution_status": "executed",
                "agent_tool_call_event_count": 2,
                "agent_used_for_response": True,
                "agent_product_response_changed": True,
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "met")
        self.assertEqual(expectations["agent_expectation_status"], "fallback_repaired")
        self.assertEqual(expectations["agent_expectation_reason_code"], "agent_first_fallback_repaired")
        self.assertEqual(expectations["product_expectation_status"], "met")

    def test_p04_product_projection_to_p10_fails_case_closure_consistency(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P04", "range_extract", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "case_id": "P04",
                "query_kind": "agent_first",
                "status": "agent_first_executed",
                "endpoint_count": 2,
                "context_call_count": 1,
                "passage_count": 1,
                "lane_injected": True,
                "agent_mode": "active",
                "agent_present": True,
                "agent_model_called": True,
                "agent_candidate_plan_present": True,
                "agent_status": "evaluated",
                "agent_execution_scope": "agent_first",
                "agent_tool_execution_status": "executed",
                "agent_tool_call_event_count": 2,
                "agent_used_for_response": True,
                "agent_product_response_changed": True,
                "agent_plan_case_id": "P04",
                "agent_plan_product_method": "passage_extract_canonical_range",
                "agent_plan_tool_names": ["catalog_search", "locate", "passage_context"],
                "agent_executed_tool_names": ["catalog_search", "locate", "passage_context"],
                "product_case_id": "P10",
                "product_method_effective": "passage_set_current_reference",
                "product_truth": "exact",
                "endpoint_kinds": ["search", "context"],
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "met")
        self.assertEqual(expectations["agent_expectation_status"], "met")
        self.assertEqual(expectations["product_expectation_status"], "failed")
        self.assertEqual(expectations["product_expectation_reason_code"], "case_closure_product_method_mismatch")

    def test_p10_replay_of_p04_turn_fails_case_closure_consistency(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P10", "state_seed", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "case_id": "P10",
                "query_kind": "agent_first",
                "status": "agent_first_executed",
                "endpoint_count": 2,
                "context_call_count": 1,
                "passage_count": 1,
                "lane_injected": True,
                "agent_mode": "active",
                "agent_present": True,
                "agent_model_called": True,
                "agent_candidate_plan_present": True,
                "agent_status": "evaluated",
                "agent_execution_scope": "agent_first",
                "agent_tool_execution_status": "executed",
                "agent_tool_call_event_count": 2,
                "agent_used_for_response": True,
                "agent_product_response_changed": True,
                "agent_plan_case_id": "P04",
                "agent_plan_product_method": "passage_extract_canonical_range",
                "agent_plan_tool_names": ["catalog_search", "locate", "passage_context"],
                "agent_executed_tool_names": ["catalog_search", "locate", "passage_context"],
                "product_case_id": "P04",
                "product_method_effective": "passage_extract_canonical_range",
                "product_truth": "exact",
                "endpoint_kinds": ["search", "context"],
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "met")
        self.assertEqual(expectations["agent_expectation_status"], "met")
        self.assertEqual(expectations["product_expectation_status"], "failed")
        self.assertEqual(expectations["product_expectation_reason_code"], "case_closure_product_method_mismatch")

    def test_state_followup_local_passage_context_plan_is_not_product_met(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P11", "state_followup", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "no_signal",
                "status": "not_used",
                "endpoint_count": 0,
                "lane_injected": False,
                "dialogue_tool_call_count": 1,
                "dialogue_tool_names": ["passage_context"],
                "agent_mode": "off",
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "failed")
        self.assertNotEqual(expectations["product_expectation_status"], "met")

    def test_origin_clarification_without_anchor_is_partial_not_met(self) -> None:
        case = smoke.BiblioLibrarianProductSmokeCase("P15", "origin_check", RAW_QUERY)
        expectations = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "state_followup",
                "status": "clarification_required",
                "endpoint_count": 0,
                "lane_injected": True,
                "doc_id_shorts": [],
                "hashes": [],
                "agent_mode": "off",
            },
        )

        self.assertEqual(expectations["runtime_expectation_status"], "partial")
        self.assertEqual(expectations["product_expectation_status"], "partial_required_attention")

    def test_nominal_agent_mode_fails_strict_when_model_is_not_called(self) -> None:
        record = {
            "case_id": "P03",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_mode": "active",
            "agent_present": True,
            "agent_model_called": False,
            "agent_candidate_plan_present": False,
            "agent_expectation_status": "failed",
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "product_expectation_status": "failed",
        }

        self.assertEqual(smoke.smoke_exit_code([record]), smoke.EXIT_VALIDATION_FAILURE)

    def test_kant_not_found_without_context_is_not_silent_success(self) -> None:
        self.assertTrue(any("Kant" in case.message for case in smoke.DEFAULT_SMOKE_CASES))
        case = smoke.BiblioLibrarianProductSmokeCase("P16", "external_theme", RAW_QUERY)
        failed = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "search_catalog",
                "status": "not_found",
                "endpoint_count": 1,
                "context_call_count": 0,
                "candidate_count": 0,
                "passage_count": 0,
                "lane_injected": True,
                "agent_mode": "off",
            },
        )
        partial = smoke._evaluate_expectations(
            case,
            {
                "query_kind": "search_catalog",
                "status": "not_found",
                "endpoint_count": 1,
                "context_call_count": 0,
                "candidate_count": 0,
                "passage_count": 0,
                "lane_injected": True,
                "agent_mode": "active",
                "agent_present": True,
                "agent_model_called": True,
                "agent_candidate_plan_present": True,
            },
        )

        self.assertEqual(failed["product_expectation_status"], "failed")
        self.assertEqual(partial["product_expectation_status"], "failed")

    def test_final_record_marker_leak_is_detected_without_emitting_unknown_field(self) -> None:
        record = smoke._finalize_record(
            {
                "case_id": "P01",
                "status": "extracted",
                "payload_objects_retained": 0,
                "product_expectation_status": "met",
                "debug_raw": RAW_PASSAGE,
            },
            raw_markers=(RAW_PASSAGE,),
            source_projection={},
        )
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)

        self.assertTrue(record["raw_marker_leaks"])
        self.assertNotIn("debug_raw", record)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_product_source_projection_markers_do_not_mark_content_free_record_as_leaking(self) -> None:
        record = smoke._finalize_record(
            {
                "case_id": "P01",
                "status": "agent_first_executed",
                "payload_objects_retained": 0,
                "product_expectation_status": "met",
            },
            raw_markers=(RAW_PASSAGE,),
            source_projection={"product_lane": {"content": RAW_PASSAGE}},
        )
        encoded = json.dumps(record, ensure_ascii=False, sort_keys=True)

        self.assertFalse(record["raw_marker_leaks"])
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_strict_exit_fails_on_leaks_payload_and_product_failure(self) -> None:
        safe = {
            "case_id": "P01",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_expectation_status": "met",
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "product_expectation_status": "met",
        }
        raw_leak = {**safe, "raw_marker_leaks": True}
        retained_payload = {**safe, "payload_objects_retained": 1}
        product_failed = {**safe, "product_expectation_status": "failed"}
        product_partial_attention = {**safe, "product_expectation_status": "partial_required_attention"}

        self.assertEqual(smoke.smoke_exit_code([safe]), smoke.EXIT_OK)
        self.assertEqual(smoke.smoke_exit_code([raw_leak]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(smoke.smoke_exit_code([retained_payload]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(smoke.smoke_exit_code([product_failed]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(smoke.smoke_exit_code([product_partial_attention]), smoke.EXIT_VALIDATION_FAILURE)
        self.assertEqual(
            smoke.smoke_exit_code([product_failed], product_strict=False),
            smoke.EXIT_OK,
        )

    def test_no_product_strict_does_not_mask_agent_expectation_failure(self) -> None:
        record = {
            "case_id": "P01",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_expectation_status": "failed",
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "product_expectation_status": "failed",
        }

        self.assertEqual(
            smoke.smoke_exit_code([record], product_strict=False),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([record], product_strict=False, agent_strict=False),
            smoke.EXIT_OK,
        )

    def test_shadow_and_candidate_are_not_nominal_smoke_proof(self) -> None:
        for mode in ("shadow", "candidate"):
            with self.subTest(mode=mode):
                expectations = smoke._evaluate_expectations(
                    smoke.BiblioLibrarianProductSmokeCase("P01", "catalog_full", RAW_QUERY),
                    {
                        "query_kind": "list_catalog",
                        "status": "listed",
                        "displayed_count": 10,
                        "total_count": 10,
                        "truncated": False,
                        "agent_mode": mode,
                        "agent_present": True,
                        "agent_model_called": True,
                        "agent_candidate_plan_present": True,
                    },
                )

                self.assertEqual(expectations["runtime_expectation_status"], "met")
                self.assertEqual(expectations["agent_expectation_status"], "failed")
                self.assertEqual(
                    expectations["agent_expectation_reason_code"],
                    "agent_mode_dev_only_not_nominal",
                )

    def test_strict_exit_fails_on_agent_side_effects(self) -> None:
        base = {
            "case_id": "P01",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_expectation_status": "met",
            "agent_used_for_response": False,
            "agent_product_response_changed": False,
            "agent_tool_execution_status": "not_executed",
            "agent_tool_call_event_count": 0,
            "product_expectation_status": "met",
        }

        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_used_for_response": True}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_product_response_changed": True}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_tool_call_event_count": 1}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**base, "agent_tool_execution_status": "executed"}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )

    def test_strict_exit_allows_bounded_agent_first_execution(self) -> None:
        record = {
            "case_id": "P03",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_mode": "active",
            "agent_present": True,
            "agent_model_called": True,
            "agent_candidate_plan_present": True,
            "agent_expectation_status": "met",
            "agent_execution_scope": "agent_first",
            "agent_plan_tool_names": ["catalog_search"],
            "agent_executed_tool_names": ["catalog_search"],
            "agent_used_for_response": True,
            "agent_product_response_changed": True,
            "agent_tool_execution_status": "executed",
            "agent_tool_call_event_count": 1,
            "endpoint_kinds": ["search"],
            "runtime_expectation_status": "met",
            "product_expectation_status": "met",
        }

        self.assertEqual(smoke.smoke_exit_code([record]), smoke.EXIT_OK)
        self.assertEqual(
            smoke.smoke_exit_code([{**record, "agent_executed_tool_names": ["latest/page"]}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )
        self.assertEqual(
            smoke.smoke_exit_code([{**record, "agent_executed_tool_names": []}]),
            smoke.EXIT_VALIDATION_FAILURE,
        )

    def test_strict_exit_allows_page_read_when_method_declares_it(self) -> None:
        record = {
            "case_id": "P14",
            "raw_marker_leaks": False,
            "payload_objects_retained": 0,
            "forbidden_endpoint_used": False,
            "agent_mode": "active",
            "agent_present": True,
            "agent_model_called": True,
            "agent_candidate_plan_present": True,
            "agent_expectation_status": "met",
            "agent_execution_scope": "agent_first",
            "agent_plan_case_id": "P14",
            "agent_plan_product_method": "passage_continue_next_segment",
            "agent_plan_tool_names": ["passage_context"],
            "agent_executed_tool_names": ["page_read"],
            "agent_used_for_response": True,
            "agent_product_response_changed": True,
            "agent_tool_execution_status": "executed",
            "agent_tool_call_event_count": 1,
            "endpoint_kinds": ["page"],
            "query_kind": "agent_first",
            "product_case_id": "P14",
            "product_method_effective": "passage_continue_next_segment",
            "runtime_expectation_status": "met",
            "product_expectation_status": "met",
        }

        self.assertEqual(smoke.smoke_exit_code([record]), smoke.EXIT_OK)

    def test_main_is_strict_by_default_and_no_strict_is_explicit(self) -> None:
        records = [
            {
                "case_id": "P01",
                "raw_marker_leaks": True,
                "payload_objects_retained": 0,
                "agent_expectation_status": "met",
                "product_expectation_status": "met",
            }
        ]

        with mock.patch("biblio.smoke_librarian_agent_live.run_smokes", return_value=records):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(["--jsonl"]), smoke.EXIT_VALIDATION_FAILURE)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(smoke.main(["--jsonl", "--no-strict"]), smoke.EXIT_OK)

    def test_main_supports_case_id_and_max_cases_for_segmented_live_debug(self) -> None:
        observed = {}

        def fake_run_smokes(**kwargs):
            observed.update(kwargs)
            return [
                {
                    "case_id": "P03",
                    "raw_marker_leaks": False,
                    "payload_objects_retained": 0,
                    "forbidden_endpoint_used": False,
                    "agent_expectation_status": "met",
                    "agent_used_for_response": False,
                    "agent_product_response_changed": False,
                    "agent_tool_execution_status": "not_executed",
                    "agent_tool_call_event_count": 0,
                    "product_expectation_status": "met",
                }
            ]

        with mock.patch("biblio.smoke_librarian_agent_live.run_smokes", side_effect=fake_run_smokes):
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(smoke.main(["--jsonl", "--case-id", "P03", "--max-cases", "1"]), smoke.EXIT_OK)

        self.assertEqual([case.case_id for case in observed["cases"]], ["P03"])
        self.assertIn('"case_id": "P03"', stdout.getvalue())


def _fake_turn_runner(
    data,
    *,
    user_msg,
    conversation_id="",
    conversation_state=None,
    recent_dialogue=(),
    client_factory=None,
    config_module=None,
):
    passage = _passage(RAW_PASSAGE)
    lane = prompt_lane.build_biblio_prompt_lane([passage])
    payload = observability.build_biblio_event_payload(
        enabled=bool(data.get("biblio_enabled")),
        used=True,
        query_kind="extract_range",
        passage_result=passage,
        prompt_lane=lane,
        status="extracted",
        reason_code="biblio_context_passage_extracted",
    )
    return chat_runtime.BiblioChatResult(
        enabled=True,
        used=True,
        reason_code="biblio_context_passage_extracted",
        query_kind="extract_range",
        passage_result=passage,
        prompt_lane=lane,
        observability_payload=payload,
    )


def _passage(passage: str) -> extractor.BiblioPassageResult:
    return extractor.BiblioPassageResult(
        status=extractor.STATUS_EXTRACTED,
        reason_code=extractor.REASON_PASSAGE_EXTRACTED,
        passage=passage,
        doc_id_short="doc-1234",
        passage_chars=len(passage),
        passage_hash="",
        char_offset=0,
        window_chars=700,
        max_passage_chars=4_000,
        excerpt_start=0,
        excerpt_end=len(passage),
        text_length=len(passage),
        page_no=12,
        para_no=3,
        paragraph_id=99,
    )


def _fake_librarian_agent_result(*, case_id: str, product_method: str, answer_mode: str):
    class _FakeInnerAgent:
        def __init__(self):
            self.validation_observation = {
                "tool_call_count": 1,
                "tool_names": ["catalog_search"],
                "plan": {
                    "case_id": case_id,
                    "product_method": product_method,
                    "answer_mode": answer_mode,
                    "tool_call_count": 1,
                    "tool_names": ["catalog_search"],
                },
            }

    class _FakeComparison:
        def __init__(self):
            self.agent_result = _FakeInnerAgent()

        def to_observability(self):
            return {
                "present": True,
                "status": "evaluated",
                "reason_code": "biblio_librarian_agent_compared",
                "mode": "active",
                "model_called": True,
                "candidate_plan_present": True,
                "used_for_response": True,
                "product_response_changed": True,
                "tool_execution_status": "executed",
                "tool_call_event_count": 1,
                "execution_scope": "agent_first",
                "agent": {
                    "validation": self.agent_result.validation_observation,
                },
                "tool_loop": {
                    "status": "tool_executed",
                    "reason_code": "biblio_librarian_tool_executed",
                    "tool_call_count": 1,
                    "tool_names": ["catalog_search"],
                },
            }

    return _FakeComparison()


if __name__ == "__main__":
    unittest.main()
