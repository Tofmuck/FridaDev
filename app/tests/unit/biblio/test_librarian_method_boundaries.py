from __future__ import annotations

import inspect
import unittest
from types import SimpleNamespace

from biblio import librarian_method_execution as method_execution
from biblio import librarian_method_navigation as method_navigation
from biblio import librarian_method_planning as method_planning
from biblio import librarian_method_runtime as method_runtime
from biblio import librarian_planner as planner
from biblio import librarian_product_methods as product_methods
from biblio import librarian_tools as tools


class _OneToolRegistry:
    tool_names = (tools.TOOL_CATALOG_LIST,)

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    def run(self, tool_name, params):
        self.calls.append((tool_name, params))
        return tools.BiblioLibrarianToolResult(
            tool_name=tool_name,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind="catalog",
            observation=tools.BiblioLibrarianToolObservation(
                tool_name=tool_name,
                endpoint_kind="catalog",
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                fields={},
            ),
        )


class _StructureClient:
    def sections(self, document_id, *, limit, offset):
        if (document_id, limit, offset) != ("doc-synthetic", 500, 0):
            raise AssertionError("unexpected structure request")
        return SimpleNamespace(
            payload={
                "sections": [
                    {
                        "section_id": "section-a",
                        "section_no": 1,
                        "level": 2,
                        "parent_section_id": "root",
                    },
                    {
                        "section_id": "section-b",
                        "section_no": 2,
                        "level": 2,
                        "parent_section_id": "root",
                    },
                    {
                        "section_id": "nested",
                        "section_no": 3,
                        "level": 3,
                        "parent_section_id": "section-b",
                    },
                ]
            }
        )


class BiblioLibrarianMethodBoundaryTests(unittest.TestCase):
    def test_method_planning_keeps_product_decisions_pure_and_exact(self) -> None:
        scoped_search = planner.BiblioLibrarianPlan(
            product_method=product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
            answer_mode="scoped_search",
        )
        section_start = planner.BiblioLibrarianPlan(
            product_method=product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
            answer_mode="section_start_page_block_2",
        )

        self.assertFalse(method_planning.allows_context_completion(scoped_search))
        self.assertTrue(
            method_planning.wants_section_start_page_block(
                section_start.product_method,
                section_start,
            )
        )
        self.assertEqual(method_planning.explicit_page_numbers("pages 4 a 6"), (4, 5, 6))
        self.assertEqual(method_planning.explicit_page_numbers("pages 4 a 7"), ())

    def test_navigation_resolves_the_next_sibling_from_the_catalogue_client(self) -> None:
        state = SimpleNamespace(
            current_document={"document_id": "doc-synthetic"},
            last_result={
                "document_id": "doc-synthetic",
                "interval_hint": {
                    "kind": "section",
                    "section_id": "section-a",
                    "section_no": 1,
                    "section_level": 2,
                    "parent_section_id": "root",
                },
            },
        )

        target = method_navigation.resolve_next_chapter_target(
            state,
            catalogue_client=_StructureClient(),
        )

        self.assertEqual(target.document_id, "doc-synthetic")
        self.assertEqual(target.section_params, {"section_id": "section-b"})
        self.assertEqual(target.reason_code, "")

    def test_execution_appends_one_get_call_without_mutating_params_or_exceeding_budget(self) -> None:
        registry = _OneToolRegistry()
        original = {"limit": 2}
        initial = planner.BiblioLibrarianLoopResult(
            status=planner.STATUS_TOOL_EXECUTED,
            reason_code=planner.REASON_TOOL_EXECUTED,
            options=planner.BiblioLibrarianLoopOptions(max_tool_calls=1),
        )

        executed = method_execution.append_get_tool_call(
            initial,
            registry=registry,
            tool_name=tools.TOOL_CATALOG_LIST,
            params=original,
        )
        refused_duplicate = method_execution.append_get_tool_call(
            executed,
            registry=registry,
            tool_name=tools.TOOL_CATALOG_LIST,
            params=original,
        )

        self.assertEqual(original, {"limit": 2})
        self.assertEqual(registry.calls, [(tools.TOOL_CATALOG_LIST, {"limit": 2})])
        self.assertEqual(executed.tool_call_count, 1)
        self.assertEqual(executed.steps[0].tool_call.method, "GET")
        self.assertIs(refused_duplicate, executed)

    def test_coordinator_uses_boundaries_instead_of_planner_or_registry_internals(self) -> None:
        source = inspect.getsource(method_runtime)

        self.assertNotIn("BiblioLibrarianPlanner(", source)
        self.assertNotIn('getattr(registry, "_client"', source)
        self.assertIn("method_execution.append_get_tool_call", source)
        self.assertIn("method_navigation.resolve_next_chapter_target", source)
        self.assertIn("method_planning.allows_context_completion", source)
