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
from biblio import librarian_tools as tools


RAW_QUERY = "RAW QUERY MUST NOT LEAK"
RAW_TITLE = "RAW TITLE MUST NOT LEAK"
RAW_AUTHOR = "RAW AUTHOR MUST NOT LEAK"
RAW_CHAPTER = "RAW CHAPTER MUST NOT LEAK"
RAW_PASSAGE = "RAW CONTEXT PASSAGE MUST STAY INTERNAL"


class BiblioLibrarianToolTests(unittest.TestCase):
    def test_registry_exposes_only_lot3_tools(self) -> None:
        registry = tools.build_librarian_tool_registry(_FakeToolClient())

        self.assertEqual(
            registry.tool_names,
            (
                tools.TOOL_CATALOG_LIST,
                tools.TOOL_CATALOG_SEARCH,
                tools.TOOL_DOCUMENT_OPEN_SUMMARY,
                tools.TOOL_DOCUMENT_TOC,
                tools.TOOL_PAGE_READ,
                tools.TOOL_LOCATE,
                tools.TOOL_PASSAGE_CONTEXT,
            ),
        )
        self.assertNotIn("export/chunk", registry.tool_names)

    def test_forbidden_and_unknown_tools_fail_before_network(self) -> None:
        fake = _FakeToolClient()
        registry = tools.build_librarian_tool_registry(fake)

        forbidden = ["export/chunk", "latest/page", "latest/context"]
        for tool_name in forbidden:
            with self.subTest(tool_name=tool_name):
                with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
                    registry.run(tool_name, {})
                self.assertEqual(ctx.exception.reason_code, tools.REASON_FORBIDDEN_TOOL)

        with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
            registry.run("catalog_delete", {})
        self.assertEqual(ctx.exception.reason_code, tools.REASON_UNKNOWN_TOOL)
        self.assertEqual(fake.calls, [])

    def test_catalog_list_is_bounded_and_observed_without_raw_query(self) -> None:
        fake = _FakeToolClient(
            catalog_payload={
                "total": 2,
                "items": [
                    {
                        "id": "doc-123456",
                        "title": RAW_TITLE,
                        "human_authors": RAW_AUTHOR,
                        "payload": "raw payload must not be retained",
                    }
                ],
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_CATALOG_LIST, {"q": RAW_QUERY, "limit": "1", "offset": 0})
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(fake.calls, [("catalog", RAW_QUERY, 1, 0)])
        self.assertEqual(result.status, tools.STATUS_OK)
        self.assertEqual(observed["endpoint_kind"], catalogue.ENDPOINT_CATALOG)
        self.assertEqual(observed["result_count"], 1)
        self.assertEqual(observed["total_count"], 2)
        self.assertTrue(observed["truncated"])
        self.assertEqual(observed["query_chars"], len(RAW_QUERY))
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_AUTHOR, encoded)
        self.assertFalse(hasattr(result, "payload"))
        self.assertFalse(hasattr(result, "response"))
        self.assertNotIn("payload", result.items[0])

    def test_catalog_search_requires_query_and_never_observes_it(self) -> None:
        fake = _FakeToolClient(
            search_payload={
                "results": [
                    {
                        "document_id": "doc-a",
                        "text": RAW_PASSAGE,
                        "document_role_signal": "commentary",
                        "document_role_signal_source": "chapter_title",
                        "document_role_signal_strength": "weak",
                    }
                ]
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
            registry.run(tools.TOOL_CATALOG_SEARCH, {})
        self.assertEqual(ctx.exception.reason_code, tools.REASON_MISSING_QUERY)
        self.assertEqual(fake.calls, [])

        result = registry.run(tools.TOOL_CATALOG_SEARCH, {"query": RAW_QUERY, "limit": 5})
        observed = result.to_observability()

        self.assertEqual(fake.calls, [("search", RAW_QUERY, 5)])
        self.assertEqual(observed["query_chars"], len(RAW_QUERY))
        self.assertNotIn(RAW_QUERY, _json(observed))
        self.assertNotIn(RAW_PASSAGE, _json(observed))
        self.assertNotIn("text", result.items[0])
        self.assertEqual(result.items[0]["document_role_signal"], "commentary")
        self.assertEqual(result.items[0]["document_role_signal_source"], "chapter_title")
        self.assertEqual(result.items[0]["document_role_signal_strength"], "weak")

    def test_document_open_summary_uses_metadata_not_heavy_document_route(self) -> None:
        fake = _FakeToolClient(
            metadata_payload={
                "document": {"id": "doc-123456", "title": RAW_TITLE},
                "human_metadata": {"authors": RAW_AUTHOR, "metadata_status": "validated"},
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_DOCUMENT_OPEN_SUMMARY, {"document_id": "doc-123456"})
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(fake.calls, [("metadata", "doc-123456")])
        self.assertEqual(result.document_summary["title"], RAW_TITLE)
        self.assertEqual(observed["endpoint_kind"], catalogue.ENDPOINT_METADATA)
        self.assertEqual(observed["doc_id_short"], "doc-1234")
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_AUTHOR, encoded)

    def test_document_open_summary_can_resolve_compact_catalogue_candidates(self) -> None:
        fake = _FakeToolClient(catalog_payload={"items": [{"id": "doc-a", "title": RAW_TITLE}]})
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_DOCUMENT_OPEN_SUMMARY, {"query": RAW_QUERY, "limit": 2})

        self.assertEqual(fake.calls, [("catalog", RAW_QUERY, 2, 0)])
        self.assertEqual(result.endpoint_kind, catalogue.ENDPOINT_CATALOG)
        self.assertNotIn(RAW_QUERY, _json(result.to_observability()))

    def test_document_toc_is_bounded_and_content_free(self) -> None:
        fake = _FakeToolClient(
            chapters_payload={
                "total": 1,
                "chapters": [{"chapter_no": 1, "title": RAW_TITLE, "page_start": 4}],
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_DOCUMENT_TOC, {"document_id": "doc-1", "limit": 1, "offset": "0"})
        observed = result.to_observability()

        self.assertEqual(fake.calls, [("chapters", "doc-1", 1, 0)])
        self.assertEqual(result.chapters[0]["title"], RAW_TITLE)
        self.assertEqual(observed["endpoint_kind"], catalogue.ENDPOINT_CHAPTERS)
        self.assertNotIn(RAW_TITLE, _json(observed))

    def test_page_read_is_bounded_and_content_free(self) -> None:
        fake = _FakeToolClient(
            page_payload={
                "document_id": "doc-1",
                "title": RAW_TITLE,
                "page_no": 28,
                "raw_text": RAW_PASSAGE,
                "paragraph_count": 3,
                "chapter": {
                    "chapter_no": 4,
                    "title": RAW_CHAPTER,
                    "unit_start": 25,
                    "unit_end": 32,
                    "source": "toc",
                    "next_chapter_no": 5,
                    "next_chapter_title": "RAW NEXT CHAPTER MUST NOT LEAK",
                },
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_PAGE_READ, {"document_id": "doc-1", "page_no": 28})
        observed = result.to_observability()

        self.assertEqual(fake.calls, [("page", "doc-1", 28)])
        self.assertEqual(result.page_text, RAW_PASSAGE)
        self.assertEqual(result.chapter_hint["title"], RAW_CHAPTER)
        self.assertEqual(observed["endpoint_kind"], catalogue.ENDPOINT_PAGE)
        self.assertEqual(observed["positions"][0]["page_no"], 28)
        self.assertEqual(observed["paragraph_count"], 3)
        self.assertEqual(observed["current_chapter_no"], 4)
        self.assertEqual(observed["next_chapter_no"], 5)
        self.assertNotIn(RAW_PASSAGE, _json(observed))
        self.assertNotIn(RAW_TITLE, _json(observed))
        self.assertNotIn(RAW_CHAPTER, _json(observed))

    def test_locate_requires_document_and_locator_with_content_free_position(self) -> None:
        fake = _FakeToolClient(
            locate_payload={
                "count": 1,
                "best": {
                    "label": "126b",
                    "page_no": 12,
                    "para_no": 3,
                    "text": RAW_PASSAGE,
                },
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
            registry.run(tools.TOOL_LOCATE, {"locator": "126b"})
        self.assertEqual(ctx.exception.reason_code, tools.REASON_MISSING_DOCUMENT_ID)

        result = registry.run(tools.TOOL_LOCATE, {"document_id": "doc-1", "locator": "126b", "limit": 1})
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(fake.calls, [("locate", "doc-1", "126b", "stephanus", 1)])
        self.assertEqual(observed["positions"][0]["page_no"], 12)
        self.assertEqual(observed["locator_chars"], 4)
        self.assertNotIn("126b", encoded)
        self.assertNotIn(RAW_PASSAGE, encoded)

    def test_passage_context_rejects_missing_payload_document_id_without_internal_text(self) -> None:
        fake = _FakeToolClient(context_payload={"text": RAW_PASSAGE})
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(
            tools.TOOL_PASSAGE_CONTEXT,
            {"document_id": "doc-1", "page_no": 12, "para_no": 3, "window_chars": 700},
        )
        observed = result.to_observability()

        self.assertEqual(result.status, tools.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, tools.REASON_CONTEXT_INCOHERENT)
        self.assertEqual(result.context_text, "")
        self.assertEqual(observed["reason_code"], tools.REASON_CONTEXT_INCOHERENT)
        self.assertNotIn(RAW_PASSAGE, _json(observed))
        self.assertNotIn(RAW_PASSAGE, repr(result))

    def test_passage_context_rejects_divergent_payload_document_id_without_internal_text(self) -> None:
        fake = _FakeToolClient(context_payload={"document_id": "doc-2", "text": RAW_PASSAGE})
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(
            tools.TOOL_PASSAGE_CONTEXT,
            {"document_id": "doc-1", "page_no": 12, "para_no": 3, "window_chars": 700},
        )

        self.assertEqual(result.status, tools.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, tools.REASON_CONTEXT_INCOHERENT)
        self.assertEqual(result.context_text, "")
        self.assertNotIn(RAW_PASSAGE, _json(result.to_observability()))
        self.assertNotIn(RAW_PASSAGE, repr(result))

    def test_passage_context_accepts_coherent_payload_document_id(self) -> None:
        fake = _FakeToolClient(
            context_payload={
                "document_id": "doc-1",
                "text": RAW_PASSAGE,
                "chapter": {
                    "chapter_no": 4,
                    "title": RAW_CHAPTER,
                    "unit_start": 25,
                    "unit_end": 32,
                    "source": "toc",
                    "next_chapter_no": 5,
                    "next_chapter_title": "RAW NEXT CHAPTER MUST NOT LEAK",
                },
            }
        )
        registry = tools.build_librarian_tool_registry(fake)

        with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
            registry.run(tools.TOOL_PASSAGE_CONTEXT, {"document_id": "doc-1"})
        self.assertEqual(ctx.exception.reason_code, tools.REASON_MISSING_POSITION)

        result = registry.run(
            tools.TOOL_PASSAGE_CONTEXT,
            {"document_id": "doc-1", "page_no": 12, "para_no": 3, "window_chars": 700},
        )
        observed = result.to_observability()
        encoded = _json(observed)

        self.assertEqual(fake.calls, [("context", "doc-1", None, 12, 3, 0, 700)])
        self.assertEqual(result.context_text, RAW_PASSAGE)
        self.assertEqual(result.chapter_hint["title"], RAW_CHAPTER)
        self.assertEqual(observed["content_chars"], len(RAW_PASSAGE))
        self.assertEqual(observed["positions"][0]["page_no"], 12)
        self.assertEqual(observed["current_chapter_no"], 4)
        self.assertEqual(observed["next_chapter_no"], 5)
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_CHAPTER, encoded)
        self.assertNotIn("text", observed)

    def test_result_repr_never_exposes_content_rich_fields(self) -> None:
        catalog = tools.build_librarian_tool_registry(
            _FakeToolClient(
                catalog_payload={
                    "items": [{"id": "doc-1", "title": RAW_TITLE, "human_authors": RAW_AUTHOR}]
                }
            )
        ).run(tools.TOOL_CATALOG_LIST, {"q": RAW_QUERY})
        summary = tools.build_librarian_tool_registry(
            _FakeToolClient(
                metadata_payload={
                    "document": {"id": "doc-1", "title": RAW_TITLE},
                    "human_metadata": {"authors": RAW_AUTHOR},
                }
            )
        ).run(tools.TOOL_DOCUMENT_OPEN_SUMMARY, {"document_id": "doc-1"})
        toc = tools.build_librarian_tool_registry(
            _FakeToolClient(chapters_payload={"chapters": [{"chapter_no": 1, "title": RAW_CHAPTER}]})
        ).run(tools.TOOL_DOCUMENT_TOC, {"document_id": "doc-1"})
        page = tools.build_librarian_tool_registry(
            _FakeToolClient(page_payload={"document_id": "doc-1", "title": RAW_TITLE, "page_no": 28, "raw_text": RAW_PASSAGE})
        ).run(tools.TOOL_PAGE_READ, {"document_id": "doc-1", "page_no": 28})
        context = tools.build_librarian_tool_registry(
            _FakeToolClient(context_payload={"document_id": "doc-1", "text": RAW_PASSAGE})
        ).run(tools.TOOL_PASSAGE_CONTEXT, {"document_id": "doc-1", "page_no": 12, "para_no": 3})

        encoded = "\n".join(repr(result) for result in (catalog, summary, toc, page, context))

        for raw in (RAW_QUERY, RAW_TITLE, RAW_AUTHOR, RAW_CHAPTER, RAW_PASSAGE):
            with self.subTest(raw=raw):
                self.assertNotIn(raw, encoded)

    def test_invalid_parameters_are_rejected_before_network(self) -> None:
        registry = tools.build_librarian_tool_registry(_FakeToolClient())
        cases = [
            (tools.TOOL_CATALOG_LIST, {"limit": 1.2}, tools.REASON_INVALID_PARAMETER),
            (tools.TOOL_CATALOG_LIST, {"limit": True}, tools.REASON_INVALID_PARAMETER),
            (tools.TOOL_CATALOG_LIST, {"limit": "1.2"}, tools.REASON_INVALID_PARAMETER),
            (tools.TOOL_CATALOG_LIST, {"limit": 101}, tools.REASON_BUDGET_OR_LIMIT_EXCEEDED),
            (tools.TOOL_CATALOG_SEARCH, {"query": "x", "offset": 1}, tools.REASON_BUDGET_OR_LIMIT_EXCEEDED),
            (tools.TOOL_DOCUMENT_TOC, {"document_id": "doc-1", "limit": 501}, tools.REASON_BUDGET_OR_LIMIT_EXCEEDED),
            (tools.TOOL_PAGE_READ, {"document_id": "doc-1", "page_no": 0}, tools.REASON_INVALID_PARAMETER),
            (tools.TOOL_PASSAGE_CONTEXT, {"document_id": "doc-1", "page_no": 1, "para_no": 1, "window_chars": 2001}, tools.REASON_BUDGET_OR_LIMIT_EXCEEDED),
            (tools.TOOL_PASSAGE_CONTEXT, {"document_id": "doc/1", "page_no": 1, "para_no": 1}, tools.REASON_INVALID_PARAMETER),
        ]

        for tool_name, params, reason_code in cases:
            fake = _FakeToolClient()
            registry = tools.build_librarian_tool_registry(fake)
            with self.subTest(tool_name=tool_name, params=params):
                with self.assertRaises(tools.BiblioLibrarianToolError) as ctx:
                    registry.run(tool_name, params)
                self.assertEqual(ctx.exception.reason_code, reason_code)
                self.assertEqual(fake.calls, [])

    def test_client_failures_become_content_free_reason_codes(self) -> None:
        fake = _TimeoutClient()
        registry = tools.build_librarian_tool_registry(fake)

        result = registry.run(tools.TOOL_CATALOG_SEARCH, {"query": RAW_QUERY})
        observed = result.to_observability()

        self.assertEqual(result.status, tools.STATUS_ERROR)
        self.assertEqual(result.reason_code, tools.REASON_TIMEOUT)
        self.assertEqual(observed["reason_code"], tools.REASON_TIMEOUT)
        self.assertNotIn(RAW_QUERY, _json(observed))

    def test_module_has_no_model_or_chat_wiring_imports(self) -> None:
        source = inspect.getsource(tools).lower()

        self.assertNotIn("openrouter", source)
        self.assertNotIn("chat_runtime", source)
        self.assertNotIn("model_call", source)
        self.assertNotIn("llm", source)
        self.assertNotIn("._request(", source)
        self.assertNotIn(".document(", source)


class _FakeToolClient:
    def __init__(
        self,
        *,
        catalog_payload: dict[str, object] | None = None,
        search_payload: dict[str, object] | None = None,
        metadata_payload: dict[str, object] | None = None,
        chapters_payload: dict[str, object] | None = None,
        page_payload: dict[str, object] | None = None,
        locate_payload: dict[str, object] | None = None,
        context_payload: dict[str, object] | None = None,
    ) -> None:
        self.catalog_payload = catalog_payload or {"total": 0, "items": []}
        self.search_payload = search_payload or {"count": 0, "results": []}
        self.metadata_payload = metadata_payload or {"document": {"id": "doc-1"}, "human_metadata": {}}
        self.chapters_payload = chapters_payload or {"total": 0, "chapters": []}
        self.page_payload = page_payload or {"document_id": "doc-1", "page_no": 1, "raw_text": ""}
        self.locate_payload = locate_payload or {"count": 0, "matches": []}
        self.context_payload = context_payload or {"document_id": "doc-1", "text": ""}
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return _response(catalogue.ENDPOINT_CATALOG, self.catalog_payload, result_count=_count(self.catalog_payload, "items"))

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        return _response(catalogue.ENDPOINT_SEARCH, self.search_payload, result_count=_count(self.search_payload, "results"))

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata", doc_id))
        return _response(catalogue.ENDPOINT_METADATA, self.metadata_payload, doc_id=doc_id)

    def document(self, doc_id: str) -> catalogue.CatalogueResponse:
        raise AssertionError("document route must not be used by Lot 3 tools")

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return _response(catalogue.ENDPOINT_CHAPTERS, self.chapters_payload, doc_id=doc_id, result_count=_count(self.chapters_payload, "chapters"))

    def page(self, doc_id: str, page_no: int) -> catalogue.CatalogueResponse:
        self.calls.append(("page", doc_id, page_no))
        return _response(
            catalogue.ENDPOINT_PAGE,
            self.page_payload,
            doc_id=doc_id,
            content_chars=len(str(self.page_payload.get("raw_text") or "")),
        )

    def locate(
        self,
        doc_id: str,
        locator: str,
        *,
        kind: str = "stephanus",
        limit: int = 200,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("locate", doc_id, locator, kind, limit))
        return _response(catalogue.ENDPOINT_LOCATE, self.locate_payload, doc_id=doc_id, result_count=_count(self.locate_payload, "matches"))

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


class _TimeoutClient:
    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        raise catalogue.CatalogueTimeout(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            duration_ms=15,
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
