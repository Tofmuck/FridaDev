from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from typing import Any


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import answer_object
from biblio import librarian_agent_contract as agent_contract
from biblio import librarian_agent_first as agent_first
from biblio import librarian_planner as planner
from biblio import librarian_product_methods as product_methods
from biblio import librarian_tools as tools


RAW_QUERY = "RAW AGENT FIRST QUERY MUST NOT LEAK"
RAW_TITLE = "RAW AGENT FIRST TITLE MUST NOT LEAK"
RAW_CHAPTER = "RAW AGENT FIRST CHAPTER MUST NOT LEAK"
RAW_PASSAGE = "RAW AGENT FIRST PASSAGE MUST NOT LEAK"


class BiblioLibrarianAgentFirstTests(unittest.TestCase):
    def test_theme_search_appends_bounded_context_when_agent_returns_search_only(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                        "text": RAW_PASSAGE,
                        "page_no": 12,
                        "para_no": 3,
                        "paragraph_id": 99,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("context", "doc-1234", 99, None, None, 0, 700))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_SEARCH, tools.TOOL_PASSAGE_CONTEXT])
        self.assertEqual(result.consultation_message.passage_count if result.consultation_message else 0, 1)
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        self.assertEqual(result.answer_object.status if result.answer_object else "", answer_object.STATUS_READY)
        consultation_content = result.consultation_message.message["content"] if result.consultation_message else ""
        self.assertIn("Source: catalogue_doc=doc-1234", consultation_content)
        self.assertNotIn(answer_object.ANSWER_HEADER, consultation_content)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_theme_search_completion_follows_product_method_instead_of_deterministic_toc_intent(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                        "text": RAW_PASSAGE,
                        "page_no": 12,
                        "para_no": 3,
                        "paragraph_id": 99,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
            chapters_payload={"total": 1, "chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="show_table_of_contents",
                    product_method=product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="show_table_of_contents"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("context", "doc-1234", 99, None, None, 0, 700))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_SEARCH, tools.TOOL_PASSAGE_CONTEXT])

    def test_theme_search_tries_bounded_significant_fallback_when_agent_query_is_empty(self) -> None:
        fallback_query = "servir propre entendement"
        fake = _FakeAgentFirstClient(
            search_payload={"count": 0, "results": []},
            search_payloads={
                fallback_query: {
                    "count": 1,
                    "results": [
                        {
                            "document_id": "doc-1234",
                            "text": RAW_PASSAGE,
                            "page_no": 12,
                            "para_no": 3,
                        }
                    ],
                }
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(
                intent="search_catalog",
                theme_query="sur oser se servir de son propre entendement",
                theme_query_variants=("sur oser se servir de son propre entendement",),
                limit=8,
            ),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("search", fallback_query, 8))
        self.assertEqual(fake.calls[2], ("context", "doc-1234", None, 12, 3, 0, 700))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT])
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_theme_search_fallbacks_when_search_hits_lack_context_position(self) -> None:
        fallback_query = "Socrate parle maïeutique"
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 2,
                "results": [
                    {"document_id": "doc-1234", "title": RAW_TITLE},
                    {"document_id": "doc-5678", "title": RAW_TITLE},
                ],
            },
            search_payloads={
                fallback_query: {
                    "count": 1,
                    "results": [
                        {
                            "document_id": "doc-1234",
                            "text": RAW_PASSAGE,
                            "page_no": 12,
                            "para_no": 3,
                        }
                    ],
                }
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(
                intent="search_catalog",
                theme_query="dans le Theetete Socrate parle maïeutique",
                theme_query_variants=("dans le Theetete Socrate parle maïeutique",),
                limit=8,
            ),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("search", fallback_query, 8))
        self.assertEqual(fake.calls[2], ("context", "doc-1234", None, 12, 3, 0, 700))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CONTEXT])
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_toc_request_appends_chapters_when_agent_returns_unique_document_search(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            chapters_payload={
                "total": 1,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": RAW_CHAPTER,
                        "page_start": 7,
                    }
                ],
            },
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="show_table_of_contents",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="show_table_of_contents"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("chapters", "doc-1234", 500, 0))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CHAPTERS])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_SEARCH, tools.TOOL_DOCUMENT_TOC])
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_CHAPTER, encoded)

    def test_toc_completion_follows_product_method_instead_of_deterministic_search_intent(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            chapters_payload={
                "total": 1,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": RAW_CHAPTER,
                        "page_start": 7,
                    }
                ],
            },
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    product_method=product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("chapters", "doc-1234", 500, 0))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CHAPTERS])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_SEARCH, tools.TOOL_DOCUMENT_TOC])

    def test_work_lookup_completion_follows_product_method_without_context_repair(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            summary_payload={"document_id": "doc-1234", "title": RAW_TITLE},
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    product_method=product_methods.PRODUCT_METHOD_WORK_LOOKUP,
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("metadata", "doc-1234"))
        self.assertEqual(observed["endpoint_kinds"], [catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_METADATA])
        self.assertEqual(observed["tool_names"], [tools.TOOL_CATALOG_SEARCH, tools.TOOL_DOCUMENT_OPEN_SUMMARY])
        self.assertNotIn(catalogue.ENDPOINT_CONTEXT, observed["endpoint_kinds"])

    def test_inventory_metadata_canonical_method_renders_without_passage_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "total": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                        "human_authors": "RAW AGENT FIRST AUTHOR MUST ONLY APPEAR IN RENDERED CONTENT",
                        "language": "fr",
                        "page_count": 88,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="inventory_metadata",
                    product_method=product_methods.PRODUCT_METHOD_INVENTORY_METADATA,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_LIST,
                            method="GET",
                            params={"limit": 10, "offset": 0},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        observed = result.loop_result.to_observability() if result.loop_result else {}
        encoded = json.dumps(
            {
                "loop": observed,
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", "", 10)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_INVENTORY_METADATA)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(
            result.answer_object.inventory_metadata["family"],
            product_methods.CANONICAL_FAMILY_INVENTORY_METADATA,
        )
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Inventaire / metadonnees:", result.rendered_answer.content)
        self.assertIn("langue=fr", result.rendered_answer.content)
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_document_resolution_canonical_method_keeps_ambiguous_candidates(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "total": 2,
                "items": [
                    {"id": "doc-1", "title": "Candidate 1"},
                    {"id": "doc-2", "title": "Candidate 2"},
                ],
            },
            context_payload={"document_id": "doc-1", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="document_resolution",
                    product_method=product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5, "offset": 0},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="resolve_work"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(result.answer_object.document_id, "")
        self.assertEqual(result.answer_object.document_resolution["status"], "ambiguous")
        self.assertTrue(lock.ok)
        self.assertIn("ambiguite conservee", result.rendered_answer.content)
        self.assertNotIn(("metadata", "doc-1"), fake.calls)
        self.assertNotIn(("context", "doc-1", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_document_structure_canonical_method_renders_toc_for_unique_document(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "total": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            chapters_payload={
                "total": 1,
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": RAW_CHAPTER,
                        "page_start": 7,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="document_structure",
                    product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5, "offset": 0},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5), ("chapters", "doc-1234", 500, 0)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.document_structure["status"], "resolved")
        self.assertEqual(result.answer_object.document_structure["chapter_count"], 1)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Structure documentaire / table des matieres:", result.rendered_answer.content)
        self.assertIn(RAW_CHAPTER, result.rendered_answer.content)
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_CHAPTER, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_document_structure_canonical_method_keeps_ambiguous_documents(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "total": 2,
                "items": [
                    {"id": "doc-1", "title": "Candidate 1"},
                    {"id": "doc-2", "title": "Candidate 2"},
                ],
            },
            chapters_payload={"total": 1, "chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="document_structure",
                    product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5, "offset": 0},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(result.answer_object.document_id, "")
        self.assertEqual(result.answer_object.document_structure["status"], "ambiguous")
        self.assertTrue(lock.ok)
        self.assertIn("ambiguite conservee", result.rendered_answer.content)
        self.assertNotIn(("chapters", "doc-1", 500, 0), fake.calls)

    def test_scoped_search_canonical_method_filters_to_carried_document_without_context(self) -> None:
        scope_query = "scoped target"
        theme_query = RAW_QUERY
        fake = _FakeAgentFirstClient(
            search_payloads={
                scope_query: {
                    "total": 1,
                    "items": [{"id": "doc-1234", "title": RAW_TITLE}],
                },
                theme_query: {
                    "count": 2,
                    "results": [
                        {
                            "document_id": "doc-1234",
                            "title": RAW_TITLE,
                            "text": RAW_PASSAGE,
                            "page_no": 12,
                            "para_no": 3,
                            "paragraph_id": 99,
                        },
                        {
                            "document_id": "doc-5678",
                            "text": "RAW OUT OF SCOPE AGENT HIT MUST NOT RENDER",
                            "page_no": 2,
                        },
                    ],
                },
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="scoped_search",
                    product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": scope_query, "limit": 5, "offset": 0},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": theme_query, "limit": 5},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", scope_query, 5), ("search", theme_query, 5)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_SCOPED_SEARCH)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(result.answer_object.scoped_search["status"], "resolved")
        self.assertEqual(result.answer_object.scoped_search["candidate_count"], 1)
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Recherche scoped:", result.rendered_answer.content)
        self.assertIn(RAW_PASSAGE, result.rendered_answer.content)
        self.assertNotIn("RAW OUT OF SCOPE", result.rendered_answer.content)
        self.assertNotIn(("context", "doc-1234", 99, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_scoped_search_canonical_method_empty_after_scope_filter_is_not_found(self) -> None:
        scope_query = "scoped target"
        theme_query = RAW_QUERY
        fake = _FakeAgentFirstClient(
            search_payloads={
                scope_query: {
                    "total": 1,
                    "items": [{"id": "doc-1234", "title": RAW_TITLE}],
                },
                theme_query: {
                    "count": 1,
                    "results": [
                        {
                            "document_id": "doc-5678",
                            "text": "RAW OUT OF SCOPE AGENT HIT MUST NOT RENDER",
                            "page_no": 9,
                            "para_no": 1,
                            "paragraph_id": 77,
                        }
                    ],
                },
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="scoped_search",
                    product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": scope_query, "limit": 5, "offset": 0},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": theme_query, "limit": 5},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", scope_query, 5), ("search", theme_query, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NOT_FOUND)
        self.assertEqual(result.answer_object.scoped_search["status"], "not_found")
        self.assertEqual(result.answer_object.scoped_search["candidate_count"], 0)
        self.assertTrue(result.answer_object.scoped_search["search_attempted"])
        self.assertIn(
            tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE,
            result.answer_object.scoped_search["reason_codes"],
        )
        self.assertEqual(result.rendered_answer.reason_code, tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE)
        self.assertNotIn(f"Reason: {tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE}", result.rendered_answer.content)
        self.assertNotIn("Reason: ok", result.rendered_answer.content)
        self.assertIn("aucun candidat de recherche ne reste dans le scope", result.rendered_answer.content)
        self.assertNotIn("RAW OUT OF SCOPE", result.rendered_answer.content)
        self.assertNotIn(("context", "doc-1234", 77, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn("RAW OUT OF SCOPE", encoded)

    def test_scoped_search_canonical_method_blocks_unscoped_global_search(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [{"document_id": "doc-1234", "text": RAW_PASSAGE, "paragraph_id": 99}],
            }
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="scoped_search",
                    product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_NEEDS_CLARIFICATION)
        self.assertEqual(fake.calls, [])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.answer_object.scoped_search["status"], "needs_clarification")
        self.assertIn(tools.REASON_SCOPED_SEARCH_SCOPE_MISSING, result.answer_object.scoped_search["reason_codes"])
        self.assertIn("clarification requise", result.rendered_answer.content)
        self.assertNotIn(RAW_PASSAGE, result.rendered_answer.content)

    def test_scoped_search_canonical_method_keeps_ambiguous_scope_before_search(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "total": 2,
                "items": [
                    {"id": "doc-1", "title": "Candidate 1"},
                    {"id": "doc-2", "title": "Candidate 2"},
                ],
            },
            context_payload={"document_id": "doc-1", "text": RAW_PASSAGE},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="scoped_search",
                    product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5, "offset": 0},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": "theme", "limit": 5},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(result.answer_object.document_id, "")
        self.assertEqual(result.answer_object.scoped_search["status"], "ambiguous")
        self.assertEqual(result.answer_object.scoped_search["candidate_count"], 0)
        self.assertIn("ambiguite conservee", result.rendered_answer.content)
        self.assertNotIn(("search", "theme", 5), fake.calls)
        self.assertNotIn(("context", "doc-1", None, None, None, 0, 700), fake.calls)

    def test_extraction_canonical_method_renders_page_read_mechanical_text(self) -> None:
        fake = _FakeAgentFirstClient(
            page_payload={
                "document_id": "doc-1234",
                "raw_text": RAW_PASSAGE,
                "paragraph_count": 4,
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_PAGE_READ,
                            method="GET",
                            params={"document_id": "doc-1234", "page_no": 12},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls, [("page", "doc-1234", 12)])
        self.assertEqual(result.answer_object.product_method, product_methods.PRODUCT_METHOD_EXTRACTION)
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertIn("Source: catalogue_doc=doc-1234, page 12", result.rendered_answer.content)
        self.assertNotIn(answer_object.ANSWER_HEADER, result.rendered_answer.content)
        self.assertNotIn("Contrat de restitution", result.rendered_answer.content)
        self.assertNotIn("Status:", result.rendered_answer.content)
        self.assertNotIn("Render mode:", result.rendered_answer.content)
        self.assertNotIn("Reason:", result.rendered_answer.content)
        self.assertNotIn("Product method:", result.rendered_answer.content)
        self.assertIn(RAW_PASSAGE, result.rendered_answer.content)
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_extraction_canonical_method_renders_two_page_range_mechanically(self) -> None:
        page_12 = "RAW AGENT FIRST PAGE 12 MUST NOT LEAK"
        page_13 = "RAW AGENT FIRST PAGE 13 MUST NOT LEAK"
        fake = _FakeAgentFirstClient(
            page_payloads={
                12: {"document_id": "doc-1234", "raw_text": page_12, "paragraph_count": 4},
                13: {"document_id": "doc-1234", "raw_text": page_13, "paragraph_count": 5},
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_PAGE_READ,
                            method="GET",
                            params={"document_id": "doc-1234", "page_no": 13},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_PAGE_READ,
                            method="GET",
                            params={"document_id": "doc-1234", "page_no": 12},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(fake.calls, [("page", "doc-1234", 13), ("page", "doc-1234", 12)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["content_kind"], "page_range")
        self.assertEqual(result.answer_object.extraction["block_count"], 2)
        self.assertEqual(result.answer_object.extraction["page_start"], 12)
        self.assertEqual(result.answer_object.extraction["page_end"], 13)
        self.assertEqual(len(result.answer_object.anchors), 2)
        self.assertEqual([anchor["page_no"] for anchor in result.answer_object.anchors], [12, 13])
        self.assertEqual([anchor["document_id"] for anchor in result.answer_object.anchors], ["doc-1234", "doc-1234"])
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertLess(result.rendered_answer.content.index(page_12), result.rendered_answer.content.index(page_13))
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(page_12, encoded)
        self.assertNotIn(page_13, encoded)

    def test_extraction_section_bounds_answer_mode_reads_two_section_start_pages(self) -> None:
        page_12 = "RAW AGENT FIRST SECTION PAGE 12 MUST NOT LEAK"
        page_13 = "RAW AGENT FIRST SECTION PAGE 13 MUST NOT LEAK"
        fake = _FakeAgentFirstClient(
            chapters_payload=_section_chapters_payload(),
            page_payloads={
                12: {"document_id": "doc-1234", "raw_text": page_12, "paragraph_count": 4},
                13: {"document_id": "doc-1234", "raw_text": page_13, "paragraph_count": 5},
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="section_start_page_block_2",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SECTION_BOUNDS,
                            method="GET",
                            params={"document_id": "doc-1234", "chapter_no": 2},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(
            fake.calls,
            [
                ("chapters", "doc-1234", 500, 0),
                ("page", "doc-1234", 12),
                ("page", "doc-1234", 13),
            ],
        )
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertEqual(result.answer_object.extraction["content_kind"], "page_range")
        self.assertEqual(result.answer_object.extraction["block_count"], 2)
        self.assertEqual(result.answer_object.extraction["page_start"], 12)
        self.assertEqual(result.answer_object.extraction["page_end"], 13)
        self.assertEqual([anchor["page_no"] for anchor in result.answer_object.anchors], [12, 13])
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertLess(result.rendered_answer.content.index(page_12), result.rendered_answer.content.index(page_13))
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(page_12, encoded)
        self.assertNotIn(page_13, encoded)

    def test_extraction_section_start_carries_resolved_section_to_bounds_and_pages(self) -> None:
        page_12 = "RAW AGENT FIRST CARRIED SECTION PAGE 12 MUST NOT LEAK"
        page_13 = "RAW AGENT FIRST CARRIED SECTION PAGE 13 MUST NOT LEAK"
        fake = _FakeAgentFirstClient(
            search_payloads={
                "Document": {"items": [{"id": "doc-1234", "title": "Document"}]},
            },
            chapters_payload=_section_chapters_payload(),
            page_payloads={
                12: {"document_id": "doc-1234", "raw_text": page_12, "paragraph_count": 4},
                13: {"document_id": "doc-1234", "raw_text": page_13, "paragraph_count": 5},
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="section_start_page_block_2",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_RESOLVE_WORK,
                            method="GET",
                            params={"query": "Document"},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_RESOLVE_SECTION,
                            method="GET",
                            params={"query": "TWO"},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SECTION_BOUNDS,
                            method="GET",
                            params={},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(
            fake.calls,
            [
                ("metadata_search", "Document", 5),
                ("chapters", "doc-1234", 500, 0),
                ("chapters", "doc-1234", 500, 0),
                ("page", "doc-1234", 12),
                ("page", "doc-1234", 13),
            ],
        )
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertEqual(result.answer_object.extraction["content_kind"], "page_range")
        self.assertEqual([anchor["page_no"] for anchor in result.answer_object.anchors], [12, 13])
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertLess(result.rendered_answer.content.index(page_12), result.rendered_answer.content.index(page_13))
        self.assertNotIn(("context", "doc-1234", None, None, None, 0, 700), fake.calls)
        self.assertNotIn(page_12, encoded)
        self.assertNotIn(page_13, encoded)

    def test_extraction_section_bounds_without_explicit_answer_mode_does_not_read_pages(self) -> None:
        fake = _FakeAgentFirstClient(
            chapters_payload=_section_chapters_payload(),
            page_payloads={
                12: {"document_id": "doc-1234", "raw_text": "RAW PAGE 12 MUST NOT RENDER"},
                13: {"document_id": "doc-1234", "raw_text": "RAW PAGE 13 MUST NOT RENDER"},
            },
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SECTION_BOUNDS,
                            method="GET",
                            params={"document_id": "doc-1234", "chapter_no": 2},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("chapters", "doc-1234", 500, 0)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertEqual(result.answer_object.exact_text, "")
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW PAGE", result.rendered_answer.content)

    def test_extraction_unique_scoped_search_hit_reads_mechanical_context(self) -> None:
        snippet = "RAW SEARCH SNIPPET MUST NOT BECOME EXACT"
        context = "RAW MECHANICAL CONTEXT MUST ONLY APPEAR IN RENDERED CONTENT"
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": RAW_TITLE,
                        "text": snippet,
                        "page_no": 12,
                        "para_no": 3,
                        "paragraph_id": 99,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": context},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "document_id": "doc-1234", "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)
        encoded = json.dumps(
            {
                "loop": result.loop_result.to_observability() if result.loop_result else {},
                "answer": result.answer_object.to_observability(),
                "render": result.rendered_answer.to_observability(),
                "lock": lock.to_observability(),
            },
            ensure_ascii=False,
            sort_keys=True,
        )

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5), ("context", "doc-1234", 99, None, None, 0, 700)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertEqual(result.answer_object.extraction["source_tool_name"], tools.TOOL_PASSAGE_CONTEXT)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertEqual(result.answer_object.anchors[0]["document_id"], "doc-1234")
        self.assertEqual(result.answer_object.anchors[0]["paragraph_id"], 99)
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertIn(context, result.rendered_answer.content)
        self.assertNotIn(snippet, result.rendered_answer.content)
        self.assertNotIn(context, encoded)
        self.assertNotIn(snippet, encoded)

    def test_extraction_multiple_scoped_search_hits_do_not_choose_first_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 2,
                "results": [
                    {"document_id": "doc-1234", "text": "RAW HIT ONE MUST NOT RENDER", "paragraph_id": 99},
                    {"document_id": "doc-1234", "text": "RAW HIT TWO MUST NOT RENDER", "paragraph_id": 100},
                ],
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "document_id": "doc-1234", "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW HIT", result.rendered_answer.content)
        self.assertNotIn("RAW CONTEXT", result.rendered_answer.content)

    def test_extraction_mixed_anchored_and_unanchored_scoped_hits_do_not_choose_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 2,
                "results": [
                    {"document_id": "doc-1234", "text": "RAW ANCHORED HIT MUST NOT RENDER", "paragraph_id": 99},
                    {"document_id": "doc-1234", "text": "RAW UNANCHORED HIT MUST NOT RENDER"},
                ],
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "document_id": "doc-1234", "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW ANCHORED HIT", result.rendered_answer.content)
        self.assertNotIn("RAW UNANCHORED HIT", result.rendered_answer.content)
        self.assertNotIn("RAW CONTEXT", result.rendered_answer.content)

    def test_extraction_unanchored_search_hit_does_not_read_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "text": "RAW UNANCHORED SNIPPET MUST NOT RENDER",
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "document_id": "doc-1234", "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW UNANCHORED", result.rendered_answer.content)
        self.assertNotIn("RAW CONTEXT", result.rendered_answer.content)

    def test_extraction_unscoped_unique_search_hit_does_not_read_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {"document_id": "doc-1234", "text": "RAW GLOBAL HIT MUST NOT RENDER", "paragraph_id": 99}
                ],
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW GLOBAL HIT", result.rendered_answer.content)
        self.assertNotIn("RAW CONTEXT", result.rendered_answer.content)

    def test_extraction_page_request_after_document_search_reads_page(self) -> None:
        page_text = "RAW MECHANICAL PAGE MUST ONLY APPEAR IN RENDERED CONTENT"
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            page_payload={"document_id": "doc-1234", "raw_text": page_text},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
            user_msg="Dans ce document, sors exactement la page 12.",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        encoded = json.dumps(result.answer_object.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5), ("page", "doc-1234", 12)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertEqual(result.answer_object.extraction["source_tool_name"], tools.TOOL_PAGE_READ)
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertIn(page_text, result.rendered_answer.content)
        self.assertNotIn(page_text, encoded)

    def test_extraction_page_read_uses_carried_document_over_weak_placeholder_param(self) -> None:
        page_text = "RAW MECHANICAL CARRIED PAGE MUST ONLY APPEAR IN RENDERED CONTENT"
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            page_payload={"document_id": "doc-1234", "raw_text": page_text},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_PAGE_READ,
                            method="GET",
                            params={"document_id": "1", "page_no": 12},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
            user_msg="Dans ce document, sors exactement la page 12.",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5), ("page", "doc-1234", 12)])
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["status"], "resolved")
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertIn(page_text, result.rendered_answer.content)

    def test_extraction_page_read_blocks_conflicting_real_document_id(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            page_payload={
                "document_id": "doc-1234",
                "raw_text": "RAW CONFLICT PAGE MUST NOT BE CALLED",
            },
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_PAGE_READ,
                            method="GET",
                            params={"document_id": "doc-5678", "page_no": 12},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
            user_msg="Dans ce document, sors exactement la page 12.",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.loop_result)
        assert result.loop_result is not None
        observed = result.loop_result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(fake.calls, [("metadata_search", RAW_QUERY, 5)])
        self.assertEqual(result.status, planner.STATUS_TOOL_REJECTED)
        self.assertEqual(result.loop_result.status, planner.STATUS_TOOL_REJECTED)
        self.assertEqual(result.loop_result.steps[-1].reason_code, tools.REASON_PAGE_READ_DOCUMENT_SCOPE_CONFLICT)
        self.assertIsNone(result.answer_object)
        self.assertIsNone(result.rendered_answer)
        self.assertIn(tools.REASON_PAGE_READ_DOCUMENT_SCOPE_CONFLICT, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn("RAW CONFLICT PAGE", encoded)

    def test_extraction_page_range_after_document_search_reads_pages(self) -> None:
        page_12 = "RAW MECHANICAL PAGE 12 MUST ONLY APPEAR IN RENDERED CONTENT"
        page_13 = "RAW MECHANICAL PAGE 13 MUST ONLY APPEAR IN RENDERED CONTENT"
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "items": [
                    {
                        "id": "doc-1234",
                        "title": RAW_TITLE,
                    }
                ],
            },
            page_payloads={
                12: {"document_id": "doc-1234", "raw_text": page_12},
                13: {"document_id": "doc-1234", "raw_text": page_13},
            },
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="extraction",
                    product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
                    case_id="",
                    answer_mode="extraction",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_SEARCH_DOCUMENT,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="extract_passage"),
            user_msg="Dans ce document, sors exactement les pages 12 et 13.",
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None
        lock = answer_object.build_final_response_lock(result.answer_object, result.rendered_answer)

        self.assertEqual(
            fake.calls,
            [("metadata_search", RAW_QUERY, 5), ("page", "doc-1234", 12), ("page", "doc-1234", 13)],
        )
        self.assertEqual(result.answer_object.status, answer_object.STATUS_READY)
        self.assertEqual(result.answer_object.extraction["content_kind"], "page_range")
        self.assertEqual(result.answer_object.extraction["block_count"], 2)
        self.assertEqual(len(result.answer_object.anchors), 2)
        self.assertEqual([anchor["page_no"] for anchor in result.answer_object.anchors], [12, 13])
        self.assertTrue(result.rendered_answer.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertIn(page_12, result.rendered_answer.content)
        self.assertIn(page_13, result.rendered_answer.content)

    def test_legacy_scoped_search_answer_mode_does_not_complete_context(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "text": "RAW SEARCH SNIPPET MUST NOT RENDER AS EXACT",
                        "paragraph_id": 99,
                    }
                ],
            },
            context_payload={"document_id": "doc-1234", "text": "RAW CONTEXT MUST NOT BE CALLED"},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="search_passage",
                    product_method=product_methods.PRODUCT_METHOD_PASSAGE_SEARCH_IN_WORK,
                    case_id="P05",
                    answer_mode="scoped_search",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "document_id": "doc-1234", "limit": 5},
                        )
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="search_catalog"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        self.assertIsNotNone(result.answer_object)
        self.assertIsNotNone(result.rendered_answer)
        assert result.answer_object is not None
        assert result.rendered_answer is not None

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(result.answer_object.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertFalse(result.rendered_answer.exact_text_rendered)
        self.assertNotIn("RAW CONTEXT", result.rendered_answer.content)

    def test_toc_request_recovers_from_unanchored_toc_step_after_search(self) -> None:
        fake = _FakeAgentFirstClient(
            search_payload={
                "count": 2,
                "results": [
                    {"document_id": "doc-1234", "title": RAW_TITLE},
                    {"document_id": "doc-5678", "title": RAW_TITLE},
                ],
            },
            chapters_payload={"total": 1, "chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="show_table_of_contents",
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_CATALOG_SEARCH,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_DOCUMENT_TOC,
                            method="GET",
                            params={},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="show_table_of_contents"),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1], ("chapters", "doc-1234", 500, 0))
        self.assertEqual(observed["status"], "tool_executed")
        self.assertIn(catalogue.ENDPOINT_CHAPTERS, observed["endpoint_kinds"])

    def test_toc_request_recovers_from_unresolved_summary_then_searches_before_chapters(self) -> None:
        fake = _FakeAgentFirstClient(
            summary_payload={},
            search_payload={
                "count": 1,
                "results": [
                    {"document_id": "doc-1234", "title": RAW_TITLE},
                ],
            },
            chapters_payload={"total": 1, "chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]},
        )

        result = agent_first.run_agent_first_plan(
            comparison=_comparison(
                _plan(
                    intent="show_table_of_contents",
                    product_method=product_methods.PRODUCT_METHOD_DOCUMENT_TOC_SHOW,
                    calls=[
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_DOCUMENT_OPEN_SUMMARY,
                            method="GET",
                            params={"query": RAW_QUERY, "limit": 5},
                        ),
                        planner.BiblioLibrarianToolCall(
                            tool_name=tools.TOOL_DOCUMENT_TOC,
                            method="GET",
                            params={},
                        ),
                    ],
                )
            ),
            client=fake,
            deterministic_plan=SimpleNamespace(intent="show_table_of_contents", document_title=RAW_QUERY, limit=5),
        )
        self.assertIsNotNone(result)
        assert result is not None
        observed = result.loop_result.to_observability() if result.loop_result else {}

        self.assertEqual(result.status, agent_first.STATUS_AGENT_FIRST_EXECUTED)
        self.assertEqual(fake.calls[0], ("metadata_search", RAW_QUERY, 5))
        self.assertEqual(fake.calls[1][0], "search")
        self.assertEqual(fake.calls[1][2], 5)
        self.assertEqual(fake.calls[2], ("chapters", "doc-1234", 500, 0))
        self.assertCountEqual(
            observed["endpoint_kinds"],
            [catalogue.ENDPOINT_METADATA, catalogue.ENDPOINT_SEARCH, catalogue.ENDPOINT_CHAPTERS],
        )


def _comparison(plan: planner.BiblioLibrarianPlan) -> SimpleNamespace:
    return SimpleNamespace(
        settings=agent_contract.BiblioLibrarianAgentSettings(mode=agent_contract.MODE_ACTIVE),
        agent_result=SimpleNamespace(candidate_plan=plan),
    )


def _plan(
    *,
    intent: str,
    calls: list[planner.BiblioLibrarianToolCall],
    product_method: str = "",
    case_id: str | None = None,
    answer_mode: str = "tool",
) -> planner.BiblioLibrarianPlan:
    effective_product_method = product_method or product_methods.infer_product_method(
        intent=intent,
        answer_mode=answer_mode,
        tool_names=[call.tool_name for call in calls],
    )
    effective_case_id = case_id if case_id is not None else product_methods.default_case_id_for_method(effective_product_method)
    return planner.BiblioLibrarianPlan(
        schema_version=planner.SCHEMA_VERSION,
        case_id=effective_case_id,
        intent=intent,
        product_method=effective_product_method,
        tool_calls=tuple(calls),
        answer_mode=answer_mode,
    )


def _section_chapters_payload() -> dict[str, Any]:
    return {
        "document": {
            "id": "doc-1234",
            "source_type": "pdf",
            "unit_label": "pages",
            "unit_count": 80,
            "page_count": 80,
            "paragraph_count": 400,
            "chapter_count": 3,
            "toc_source": "synthetic",
        },
        "total": 3,
        "chapters": [
            {"chapter_no": 1, "title": "RAW SECTION ONE MUST STAY INTERNAL", "unit_no": 1, "source": "toc"},
            {"chapter_no": 2, "title": "RAW SECTION TWO MUST STAY INTERNAL", "unit_no": 12, "source": "toc"},
            {"chapter_no": 3, "title": "RAW SECTION THREE MUST STAY INTERNAL", "unit_no": 16, "source": "toc"},
        ],
    }


class _FakeAgentFirstClient:
    def __init__(
        self,
        *,
        search_payload: dict[str, Any] | None = None,
        search_payloads: dict[str, dict[str, Any]] | None = None,
        chapters_payload: dict[str, Any] | None = None,
        summary_payload: dict[str, Any] | None = None,
        context_payload: dict[str, Any] | None = None,
        page_payload: dict[str, Any] | None = None,
        page_payloads: dict[int, dict[str, Any]] | None = None,
    ) -> None:
        self.search_payload = search_payload or {"count": 0, "results": []}
        self.search_payloads = search_payloads or {}
        self.chapters_payload = chapters_payload or {"total": 0, "chapters": []}
        self.summary_payload = summary_payload or {"document_id": "doc-1234", "title": RAW_TITLE}
        self.context_payload = context_payload or {"document_id": "doc-1234", "text": ""}
        self.page_payload = page_payload or {"document_id": "doc-1234", "raw_text": ""}
        self.page_payloads = page_payloads or {}
        self.calls: list[tuple[Any, ...]] = []

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        payload = self.search_payloads.get(q, self.search_payload)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload=payload,
            duration_ms=1,
            result_count=_count(payload, "results"),
        )

    def catalog(self, q: str, *, limit: int = 20, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata_search", q, limit))
        payload = self.search_payloads.get(q, self.search_payload)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_METADATA,
            status_code=200,
            payload=payload,
            duration_ms=1,
            result_count=_count(payload, "results"),
        )

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload=self.chapters_payload,
            duration_ms=1,
            result_count=_count(self.chapters_payload, "chapters"),
            doc_id_short=catalogue.short_doc_id(doc_id),
        )

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata", doc_id))
        payload = dict(self.summary_payload)
        payload.setdefault("document_id", doc_id)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_METADATA,
            status_code=200,
            payload=payload,
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
        )

    def page(self, doc_id: str, page_no: int) -> catalogue.CatalogueResponse:
        self.calls.append(("page", doc_id, page_no))
        payload = dict(self.page_payloads.get(page_no, self.page_payload))
        payload.setdefault("document_id", doc_id)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            status_code=200,
            payload=payload,
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
            content_chars=len(str(payload.get("raw_text") or "")),
        )

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
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload=self.context_payload,
            duration_ms=1,
            result_count=1,
            doc_id_short=catalogue.short_doc_id(doc_id),
            content_chars=len(str(self.context_payload.get("text") or "")),
        )


def _count(payload: dict[str, Any], key: str) -> int:
    value = payload.get(key)
    return len(value) if isinstance(value, list) else 0


if __name__ == "__main__":
    unittest.main()
