from __future__ import annotations

import inspect
import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import librarian_planner as planner
from biblio import librarian_tools as tools


RAW_QUERY = "RAW QUERY MUST NOT LEAK FROM PLANNER"
RAW_TITLE = "RAW TITLE MUST NOT LEAK FROM PLANNER"
RAW_AUTHOR = "RAW AUTHOR MUST NOT LEAK FROM PLANNER"
RAW_CHAPTER = "RAW CHAPTER MUST NOT LEAK FROM PLANNER"
RAW_PASSAGE = "RAW PASSAGE MUST NOT LEAK FROM PLANNER"


class BiblioLibrarianPlannerTests(unittest.TestCase):
    def test_executes_simple_catalog_list_plan(self) -> None:
        fake = _FakeToolClient(
            catalog_payload={
                "total": 1,
                "items": [{"id": "doc-1", "title": RAW_TITLE, "human_authors": RAW_AUTHOR}],
            }
        )
        loop = _planner(fake)

        result = loop.run(proposed_tool_calls=[{"tool_name": tools.TOOL_CATALOG_LIST, "params": {"q": RAW_QUERY}}])
        observed = result.to_observability()

        self.assertEqual(result.status, planner.STATUS_TOOL_EXECUTED)
        self.assertEqual(fake.calls, [("catalog", RAW_QUERY, 100, 0)])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_LIST])
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_CATALOG])
        self.assertNotIn(RAW_QUERY, _json(observed))
        self.assertNotIn(RAW_TITLE, _json(observed))
        self.assertNotIn(RAW_AUTHOR, _json(observed))

    def test_executes_bounded_search_then_context_sequence(self) -> None:
        fake = _FakeToolClient(
            search_payload={"results": [{"document_id": "doc-1", "page_no": 12, "para_no": 3, "text": RAW_PASSAGE}]},
            context_payload={"document_id": "doc-1", "text": RAW_PASSAGE},
        )
        loop = _planner(fake)

        result = loop.run(
            proposed_tool_calls=[
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "params": {"query": RAW_QUERY, "limit": 5}},
                {
                    "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                    "params": {"document_id": "doc-1", "page_no": 12, "para_no": 3},
                },
            ]
        )
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(result.status, planner.STATUS_TOOL_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("context", "doc-1", None, 12, 3, 0, 700))
        self.assertEqual(observed["tool_call_count"], 2)
        self.assertIn(catalogue.ENDPOINT_SEARCH, observed["endpoint_kinds"])
        self.assertIn(catalogue.ENDPOINT_CONTEXT, observed["endpoint_kinds"])
        self.assertEqual(observed["positions"][0]["page_no"], 12)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_unknown_tool_is_rejected_before_network(self) -> None:
        fake = _FakeToolClient()
        result = _planner(fake).run(proposed_tool_calls=[{"tool_name": "catalog_delete", "params": {}}])

        self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
        self.assertEqual(result.steps[0].reason_code, tools.REASON_UNKNOWN_TOOL)
        self.assertEqual(fake.calls, [])

    def test_forbidden_tools_are_rejected_before_network(self) -> None:
        forbidden = ["page_read", "export/chunk", "latest/page", "latest/context"]
        for tool_name in forbidden:
            fake = _FakeToolClient()
            with self.subTest(tool_name=tool_name):
                result = _planner(fake).run(proposed_tool_calls=[{"tool_name": tool_name, "params": {}}])
                self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
                self.assertEqual(result.steps[0].reason_code, tools.REASON_FORBIDDEN_TOOL)
                self.assertEqual(fake.calls, [])

    def test_non_get_method_and_mutating_route_names_are_rejected_before_network(self) -> None:
        cases = [
            {"tool_name": tools.TOOL_CATALOG_LIST, "method": "DELETE", "params": {}},
            {"tool_name": "settings/reset", "method": "GET", "params": {}},
        ]
        for call in cases:
            fake = _FakeToolClient()
            with self.subTest(call=call):
                result = _planner(fake).run(proposed_tool_calls=[call])
                self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
                self.assertEqual(result.steps[0].reason_code, tools.REASON_FORBIDDEN_TOOL)
                self.assertEqual(fake.calls, [])

    def test_passage_context_without_document_or_position_is_rejected_before_network(self) -> None:
        cases = [
            {"page_no": 12, "para_no": 3},
            {"document_id": "doc-1"},
        ]
        for params in cases:
            fake = _FakeToolClient()
            with self.subTest(params=params):
                result = _planner(fake).run(
                    proposed_tool_calls=[{"tool_name": tools.TOOL_PASSAGE_CONTEXT, "params": params}]
                )
                self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
                self.assertIn(
                    result.steps[0].reason_code,
                    {tools.REASON_MISSING_DOCUMENT_ID, tools.REASON_MISSING_POSITION},
                )
                self.assertEqual(fake.calls, [])

    def test_max_tool_calls_budget_cuts_loop_cleanly(self) -> None:
        fake = _FakeToolClient(catalog_payload={"items": [{"id": "doc-1"}]})
        result = _planner(fake).run(
            proposed_tool_calls=[
                {"tool_name": tools.TOOL_CATALOG_LIST, "params": {}},
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "params": {"query": RAW_QUERY}},
            ],
            options=planner.BiblioLibrarianLoopOptions(max_tool_calls=1),
        )

        self.assertEqual(result.status, planner.STATUS_BUDGET_EXHAUSTED)
        self.assertEqual(result.reason_code, planner.REASON_BUDGET_EXHAUSTED)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(fake.calls, [("catalog", "", 100, 0)])

    def test_timeout_tool_failure_is_content_free(self) -> None:
        fake = _TimeoutSearchClient()
        result = _planner(fake).run(
            proposed_tool_calls=[{"tool_name": tools.TOOL_CATALOG_SEARCH, "params": {"query": RAW_QUERY}}]
        )
        observed = result.to_observability()

        self.assertEqual(result.status, planner.STATUS_TOOL_FAILED)
        self.assertEqual(result.steps[0].reason_code, tools.REASON_TIMEOUT)
        self.assertNotIn(RAW_QUERY, _json(observed))

    def test_invalid_structured_output_is_rejected_without_suspend(self) -> None:
        fake = _FakeToolClient()
        result = _planner(fake).run(proposed_tool_calls=[{"tool_name": "", "params": {"query": RAW_QUERY}}])

        self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
        self.assertEqual(result.steps[0].reason_code, planner.REASON_INVALID_PLAN)
        self.assertEqual(fake.calls, [])

    def test_empty_plan_falls_back_deterministically(self) -> None:
        fake = _FakeToolClient()
        result = _planner(fake).run(proposed_tool_calls=[])

        self.assertEqual(result.status, planner.STATUS_FALLBACK_DETERMINISTIC)
        self.assertTrue(result.to_observability()["fallback_deterministic"])
        self.assertEqual(fake.calls, [])

    def test_clarification_plan_uses_clarification_budget_without_network(self) -> None:
        fake = _FakeToolClient()
        request = planner.BiblioLibrarianLoopRequest(
            plan=planner.BiblioLibrarianPlan(intent="clarify", answer_mode="clarify")
        )

        result = _planner(fake).run(request)

        self.assertEqual(result.status, planner.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.reason_code, planner.REASON_NEEDS_CLARIFICATION)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].status, planner.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.steps[0].observation["clarification_count"], 1)
        self.assertEqual(fake.calls, [])

    def test_zero_clarification_budget_blocks_clarification_without_network(self) -> None:
        fake = _FakeToolClient()
        request = planner.BiblioLibrarianLoopRequest(
            plan=planner.BiblioLibrarianPlan(intent="clarify"),
            options=planner.BiblioLibrarianLoopOptions(max_clarifications=0),
        )

        result = _planner(fake).run(request)

        self.assertEqual(result.status, planner.STATUS_BUDGET_EXHAUSTED)
        self.assertEqual(result.reason_code, planner.REASON_BUDGET_EXHAUSTED)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.steps[0].observation["budget_exhausted"], "max_clarifications")
        self.assertEqual(fake.calls, [])

    def test_context_window_is_bounded_before_network(self) -> None:
        fake = _FakeToolClient(context_payload={"document_id": "doc-1", "text": "x" * 1000})

        result = _planner(fake).run(
            proposed_tool_calls=[
                {
                    "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                    "params": {
                        "document_id": "doc-1",
                        "page_no": 12,
                        "para_no": 3,
                        "window_chars": 1500,
                    },
                }
            ],
            options=planner.BiblioLibrarianLoopOptions(max_context_chars=1000),
        )

        self.assertEqual(result.status, planner.STATUS_TOOL_EXECUTED)
        self.assertEqual(fake.calls, [("context", "doc-1", None, 12, 3, 0, 1000)])

    def test_context_call_is_refused_before_network_when_no_safe_window_remains(self) -> None:
        fake = _FakeToolClient(context_payload={"document_id": "doc-1", "text": "x" * 30})

        result = _planner(fake).run(
            proposed_tool_calls=[
                {
                    "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                    "params": {"document_id": "doc-1", "page_no": 12, "para_no": 3, "window_chars": 80},
                },
                {
                    "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                    "params": {"document_id": "doc-1", "page_no": 13, "para_no": 1, "window_chars": 80},
                },
            ],
            options=planner.BiblioLibrarianLoopOptions(max_context_chars=100),
        )

        self.assertEqual(result.status, planner.STATUS_BUDGET_EXHAUSTED)
        self.assertEqual(result.reason_code, planner.REASON_BUDGET_EXHAUSTED)
        self.assertEqual(fake.calls, [("context", "doc-1", None, 12, 3, 0, 80)])
        self.assertEqual(result.steps[-1].observation["budget_exhausted"], "max_context_chars")

    def test_max_steps_budget_is_strict_after_first_tool(self) -> None:
        fake = _FakeToolClient(catalog_payload={"items": [{"id": "doc-1"}]})

        result = _planner(fake).run(
            proposed_tool_calls=[
                {"tool_name": tools.TOOL_CATALOG_LIST, "params": {}},
                {"tool_name": tools.TOOL_CATALOG_SEARCH, "params": {"query": RAW_QUERY}},
            ],
            options=planner.BiblioLibrarianLoopOptions(max_steps=1),
        )

        self.assertEqual(result.status, planner.STATUS_BUDGET_EXHAUSTED)
        self.assertEqual(result.reason_code, planner.REASON_BUDGET_EXHAUSTED)
        self.assertEqual(len(result.steps), 1)
        self.assertEqual(result.tool_call_count, 1)
        self.assertEqual(fake.calls, [("catalog", "", 100, 0)])

    def test_observability_and_repr_are_content_free(self) -> None:
        fake = _FakeToolClient(
            catalog_payload={"items": [{"id": "doc-1", "title": RAW_TITLE, "human_authors": RAW_AUTHOR}]},
            chapters_payload={"chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]},
            context_payload={"document_id": "doc-1", "text": RAW_PASSAGE},
        )
        result = _planner(fake).run(
            proposed_tool_calls=[
                {"tool_name": tools.TOOL_CATALOG_LIST, "params": {"q": RAW_QUERY}},
                {"tool_name": tools.TOOL_DOCUMENT_TOC, "params": {"document_id": "doc-1"}},
                {
                    "tool_name": tools.TOOL_PASSAGE_CONTEXT,
                    "params": {"document_id": "doc-1", "page_no": 12, "para_no": 3},
                },
            ]
        )
        encoded = _json(result.to_observability())
        repr_encoded = repr(result) + "\n" + "\n".join(repr(step) for step in result.steps)

        for raw in (RAW_QUERY, RAW_TITLE, RAW_AUTHOR, RAW_CHAPTER, RAW_PASSAGE):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, encoded)
                self.assertNotIn(raw, repr_encoded)

    def test_planner_module_has_no_external_agent_wiring_imports(self) -> None:
        source = inspect.getsource(planner).lower()

        self.assertNotIn("openrouter", source)
        self.assertNotIn("chat_runtime", source)
        self.assertNotIn("model_call", source)
        self.assertNotIn("llm", source)


def _planner(fake: object) -> planner.BiblioLibrarianPlanner:
    return planner.BiblioLibrarianPlanner(tools.build_librarian_tool_registry(fake))


class _FakeToolClient:
    def __init__(
        self,
        *,
        catalog_payload: dict[str, object] | None = None,
        search_payload: dict[str, object] | None = None,
        metadata_payload: dict[str, object] | None = None,
        chapters_payload: dict[str, object] | None = None,
        context_payload: dict[str, object] | None = None,
    ) -> None:
        self.catalog_payload = catalog_payload or {"total": 0, "items": []}
        self.search_payload = search_payload or {"count": 0, "results": []}
        self.metadata_payload = metadata_payload or {"document": {"id": "doc-1"}, "human_metadata": {}}
        self.chapters_payload = chapters_payload or {"total": 0, "chapters": []}
        self.context_payload = context_payload or {"document_id": "doc-1", "text": ""}
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q or "", limit, offset))
        return _response(catalogue.ENDPOINT_CATALOG, self.catalog_payload, result_count=_count(self.catalog_payload, "items"))

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        return _response(catalogue.ENDPOINT_SEARCH, self.search_payload, result_count=_count(self.search_payload, "results"))

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata", doc_id))
        return _response(catalogue.ENDPOINT_METADATA, self.metadata_payload, doc_id=doc_id)

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return _response(catalogue.ENDPOINT_CHAPTERS, self.chapters_payload, doc_id=doc_id, result_count=_count(self.chapters_payload, "chapters"))

    def locate(
        self,
        doc_id: str,
        locator: str,
        *,
        kind: str = "stephanus",
        limit: int = 200,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("locate", doc_id, locator, kind, limit))
        return _response(catalogue.ENDPOINT_LOCATE, {"count": 0}, doc_id=doc_id)

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = 700,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("context", doc_id, paragraph_id, page_no, para_no, char_offset, window_chars))
        return _response(
            catalogue.ENDPOINT_CONTEXT,
            self.context_payload,
            doc_id=doc_id,
            content_chars=len(str(self.context_payload.get("text") or "")),
        )


class _TimeoutSearchClient(_FakeToolClient):
    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        raise catalogue.CatalogueTimeout(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            duration_ms=21,
            error_class="Timeout",
        )


def _response(
    endpoint_kind: str,
    payload: dict[str, object],
    *,
    doc_id: str = "",
    result_count: int | None = None,
    content_chars: int = 0,
) -> catalogue.CatalogueResponse:
    return catalogue.CatalogueResponse(
        endpoint_kind=endpoint_kind,
        status_code=200,
        payload=payload,
        duration_ms=7,
        result_count=result_count,
        doc_id_short=catalogue.short_doc_id(doc_id),
        content_chars=content_chars,
    )


def _count(payload: dict[str, object], key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
