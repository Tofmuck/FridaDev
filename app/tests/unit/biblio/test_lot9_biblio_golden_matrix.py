from __future__ import annotations

import copy
import unittest

from biblio import answer_object
from biblio import librarian_agent_first
from biblio import librarian_planner
from biblio import librarian_tools
from biblio import smoke_librarian_agent_expectations as smoke_expectations
from tests.support.biblio_method_golden import (
    METHOD_CASES,
    RAW_PASSAGE,
    FakeBiblioCatalogueClient,
    assert_content_free,
    exercise_method_case,
)


class Lot9BiblioGoldenMatrixTests(unittest.TestCase):
    def test_get_only_registry_rejects_forbidden_unknown_and_method_mutations(self) -> None:
        client = FakeBiblioCatalogueClient()
        planner = librarian_planner.BiblioLibrarianPlanner(
            librarian_tools.build_librarian_tool_registry(client)
        )
        calls = (
            (
                "allowed_get",
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name=librarian_tools.TOOL_CATALOG_LIST,
                    method="GET",
                    params={"limit": 3},
                ),
            ),
            (
                "post_mutation",
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name=librarian_tools.TOOL_CATALOG_LIST,
                    method="POST",
                    params={"limit": 3},
                ),
            ),
            (
                "forbidden_route",
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name="export/chunk",
                    method="GET",
                ),
            ),
            (
                "unknown_tool",
                librarian_planner.BiblioLibrarianToolCall(
                    tool_name="synthetic_unknown_tool",
                    method="GET",
                ),
            ),
        )
        observed = {
            name: (step.status, step.reason_code)
            for name, call in calls
            for step in (planner.run_tool_call(0, call),)
        }
        expected = {
            "allowed_get": (
                librarian_planner.STATUS_TOOL_EXECUTED,
                librarian_planner.REASON_TOOL_EXECUTED,
            ),
            "post_mutation": (
                librarian_planner.STATUS_TOOL_REJECTED,
                librarian_tools.REASON_FORBIDDEN_TOOL,
            ),
            "forbidden_route": (
                librarian_planner.STATUS_TOOL_REJECTED,
                librarian_tools.REASON_FORBIDDEN_TOOL,
            ),
            "unknown_tool": (
                librarian_planner.STATUS_TOOL_REJECTED,
                librarian_tools.REASON_UNKNOWN_TOOL,
            ),
        }

        self.assertEqual(observed, expected)
        self.assertEqual([call[0] for call in client.calls], ["catalog"])
        assert_content_free(observed)

        mutated = dict(observed)
        mutated["post_mutation"] = expected["allowed_get"]
        with self.assertRaises(AssertionError):
            self.assertEqual(mutated, expected)

    def test_method_matrix_preserves_runtime_completion_order_answer_and_lock(self) -> None:
        executions = [exercise_method_case(case) for case in METHOD_CASES]

        for execution in executions:
            case = execution["case"]
            observed = execution["observation"]
            result = execution["result"]
            with self.subTest(case=case.name):
                self.assertEqual(result.status, librarian_agent_first.STATUS_AGENT_FIRST_EXECUTED)
                self.assertEqual(observed["case_id"], case.case_id)
                self.assertEqual(observed["product_method"], case.product_method)
                self.assertEqual(observed["tool_names"], case.expected_tool_names)
                self.assertEqual(observed["endpoint_kinds"], case.expected_endpoint_kinds)
                self.assertEqual(observed["client_call_kinds"], case.expected_endpoint_kinds)
                self.assertEqual(observed["answer"]["status"], answer_object.STATUS_READY)
                self.assertEqual(observed["rendered"]["status"], answer_object.STATUS_READY)
                self.assertTrue(observed["rendered"]["present"])
                self.assertEqual(observed["final_lock"]["status"], "authorized")
                assert_content_free(observed)

                mutated = copy.deepcopy(observed)
                mutated["tool_names"] = tuple(reversed(mutated["tool_names"]))
                with self.assertRaises(AssertionError):
                    self.assertEqual(mutated["tool_names"], case.expected_tool_names)

    def test_passage_render_and_fallback_repair_observability_stay_content_free(self) -> None:
        execution = exercise_method_case(METHOD_CASES[-1])
        result = execution["result"]
        observed = execution["observation"]
        self.assertIsNotNone(result.rendered_answer)
        assert result.rendered_answer is not None
        self.assertIn(RAW_PASSAGE, result.rendered_answer.content)
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertNotIn(RAW_PASSAGE, str(observed))
        assert_content_free(observed)

        loop = result.loop_result.to_observability() if result.loop_result else {}
        record = {
            "query_kind": "agent_first",
            "status": "agent_first_executed",
            "endpoint_count": len(loop.get("endpoint_kinds", ())),
            "context_call_count": loop.get("endpoint_kinds", []).count("context"),
            "candidate_count": 1,
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
            "agent_executed_tool_names": loop.get("tool_names", []),
            "agent_tool_execution_status": "executed",
            "agent_tool_call_event_count": len(loop.get("tool_names", ())),
            "agent_used_for_response": True,
            "agent_product_response_changed": True,
            "product_method_effective": METHOD_CASES[-1].product_method,
        }
        expectations = smoke_expectations.evaluate_expectations("theme_search", record)

        self.assertEqual(expectations["runtime_expectation_status"], "met")
        self.assertEqual(expectations["agent_expectation_status"], "fallback_repaired")
        self.assertEqual(
            expectations["agent_expectation_reason_code"],
            "agent_first_fallback_repaired",
        )
        self.assertEqual(expectations["product_expectation_status"], "met")
        assert_content_free(expectations)

        mutated = dict(expectations)
        mutated["agent_expectation_status"] = "met"
        with self.assertRaises(AssertionError):
            self.assertEqual(mutated["agent_expectation_status"], "fallback_repaired")

        leaked = copy.deepcopy(observed)
        leaked["raw_query"] = RAW_PASSAGE
        with self.assertRaises(AssertionError):
            assert_content_free(leaked)


if __name__ == "__main__":
    unittest.main()
