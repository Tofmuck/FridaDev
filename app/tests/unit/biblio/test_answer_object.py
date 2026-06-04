from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import answer_object
from biblio import catalogue_client as catalogue
from biblio import librarian_product_methods as product_methods
from biblio import librarian_tools as tools


RAW_EXACT_TEXT = "RAW EXACT PASSAGE MUST ONLY APPEAR IN RENDERED CONTENT"
RAW_TITLE = "RAW TITLE MUST NOT LEAK"
RAW_PROMPT = "RAW PROMPT MUST NOT LEAK"


class BiblioAnswerObjectTests(unittest.TestCase):
    def test_builds_ready_object_from_resolved_section_bounds_content_free(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_SECTION_BOUNDS,
            status=tools.STATUS_RESOLVED,
            reason_code=tools.REASON_RESOLVED,
            document_id="doc-123456",
            items=(
                {
                    "document_id": "doc-123456",
                    "section_id": "doc-1234:section:2",
                    "content_role": "primary_text",
                    "limits": ("section_ends_are_derived_not_imported",),
                    "title": RAW_TITLE,
                },
            ),
            anchors=(
                {"document_id": "doc-123456", "unit_no": 10, "section_id": "doc-1234:section:2"},
                {"document_id": "doc-123456", "unit_no": 29, "section_id": "doc-1234:section:2"},
            ),
            interval={"type": "section", "state": "derived"},
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_PASSAGE_EXTRACT_CANONICAL_RANGE,
            case_id="P04",
        )
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.document_id, "doc-123456")
        self.assertEqual(answer.section_id, "doc-1234:section:2")
        self.assertEqual(answer.content_role, "primary_text")
        self.assertEqual(observed["anchor_count"], 2)
        self.assertNotIn(RAW_TITLE, _json(observed))

    def test_ambiguous_result_stays_ambiguous_and_renderer_does_not_choose_candidate(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_RESOLVE_SECTION,
            status=tools.STATUS_AMBIGUOUS,
            reason_code=tools.REASON_AMBIGUOUS,
            document_id="doc-1",
            items=(
                {"document_id": "doc-1", "section_id": "s1", "title": "Candidate 1"},
                {"document_id": "doc-1", "section_id": "s2", "title": "Candidate 2"},
            ),
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(tool_results=(result,))
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(answer.section_id, "")
        self.assertEqual(answer.exact_text, "")
        self.assertEqual(rendered.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)

    def test_structural_missing_reasons_do_not_become_exact_excerpts(self) -> None:
        for reason_code in (tools.REASON_SECTION_ALIAS_MISSING, tools.REASON_INTERNAL_WORK_UNRESOLVED):
            with self.subTest(reason_code=reason_code):
                result = _tool_result(
                    tool_name=tools.TOOL_RESOLVE_SECTION,
                    status=tools.STATUS_NOT_FOUND,
                    reason_code=reason_code,
                    document_id="doc-1",
                    context_text=RAW_EXACT_TEXT,
                )

                answer = answer_object.build_biblio_answer_object(tool_results=(result,))
                rendered = answer_object.render_biblio_answer_object(answer)

                self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
                self.assertEqual(answer.reason_codes, (reason_code,))
                self.assertEqual(answer.render_mode, answer_object.RENDER_BLOCKED_EXACT)
                self.assertFalse(rendered.exact_text_rendered)
                self.assertNotIn(RAW_EXACT_TEXT, _json(answer.to_observability()))
                self.assertNotIn(RAW_EXACT_TEXT, rendered.content)

    def test_exact_rendering_only_uses_mechanical_tool_text_and_observes_hash(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PASSAGE_CONTEXT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            document_id="doc-1",
            positions=({"page_no": 12, "para_no": 3},),
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(tool_results=(result,))
        rendered = answer_object.render_biblio_answer_object(answer)
        observed_answer = answer.to_observability()
        observed_render = rendered.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertTrue(rendered.exact_text_rendered)
        self.assertIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed_answer))
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed_render))
        self.assertEqual(observed_answer["exact_text_chars"], len(RAW_EXACT_TEXT))
        self.assertEqual(observed_render["exact_text_hash"], observed_answer["exact_text_hash"])

    def test_canonical_extraction_renders_exact_page_read_with_anchor(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PAGE_READ,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            document_id="doc-1",
            positions=({"page_no": 12},),
            page_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertEqual(answer.extraction["status"], "resolved")
        self.assertEqual(answer.extraction["source_tool_name"], tools.TOOL_PAGE_READ)
        self.assertTrue(rendered.exact_text_rendered)
        self.assertIn("Extraction mecanique:", rendered.content)
        self.assertIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_canonical_extraction_renders_exact_context_with_anchor(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PASSAGE_CONTEXT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            document_id="doc-1",
            positions=({"page_no": 12, "para_no": 3, "paragraph_id": 99},),
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertEqual(answer.extraction["status"], "resolved")
        self.assertEqual(answer.extraction["source_tool_name"], tools.TOOL_PASSAGE_CONTEXT)
        self.assertTrue(rendered.exact_text_rendered)
        self.assertIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_canonical_extraction_assembles_two_pages_in_document_order(self) -> None:
        page_12 = "RAW PAGE 12 MUST ONLY APPEAR IN RENDERED CONTENT"
        page_13 = "RAW PAGE 13 MUST ONLY APPEAR IN RENDERED CONTENT"
        results = (
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": 13},),
                page_text=page_13,
            ),
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": 12},),
                page_text=page_12,
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=results,
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_EXACT_EXCERPT)
        self.assertEqual(answer.extraction["content_kind"], "page_range")
        self.assertEqual(answer.extraction["block_count"], 2)
        self.assertEqual(answer.extraction["page_start"], 12)
        self.assertEqual(answer.extraction["page_end"], 13)
        self.assertEqual(answer.exact_text, page_12 + "\n\n" + page_13)
        self.assertTrue(rendered.exact_text_rendered)
        self.assertTrue(lock.ok)
        self.assertLess(rendered.content.index(page_12), rendered.content.index(page_13))
        self.assertNotIn(page_12, _json(answer.extraction))
        self.assertNotIn(page_13, _json(answer.extraction))
        self.assertNotIn(page_12, _json(observed))
        self.assertNotIn(page_13, _json(observed))

    def test_canonical_extraction_assembles_short_three_page_interval(self) -> None:
        results = tuple(
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": page_no},),
                page_text=f"RAW PAGE {page_no} MUST ONLY APPEAR IN RENDERED CONTENT",
            )
            for page_no in (12, 13, 14)
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=results,
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.extraction["block_count"], 3)
        self.assertEqual(answer.extraction["page_start"], 12)
        self.assertEqual(answer.extraction["page_end"], 14)
        self.assertTrue(rendered.exact_text_rendered)
        self.assertIn("intervalle pages lu: 12-14", rendered.content)
        self.assertNotIn("RAW PAGE 12", _json(observed))

    def test_canonical_extraction_blocks_pages_from_different_documents(self) -> None:
        results = (
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": 12},),
                page_text="RAW DOC 1 PAGE MUST NOT RENDER",
            ),
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-2",
                positions=({"page_no": 13},),
                page_text="RAW DOC 2 PAGE MUST NOT RENDER",
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=results,
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertIn(tools.REASON_EXTRACTION_DOCUMENT_MISMATCH, answer.extraction["reason_codes"])
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn("RAW DOC 1", rendered.content)
        self.assertNotIn("RAW DOC 2", rendered.content)
        self.assertNotIn("RAW DOC 1", _json(observed))
        self.assertNotIn("RAW DOC 2", _json(observed))

    def test_canonical_extraction_blocks_incomplete_page_interval(self) -> None:
        results = (
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": 12},),
                page_text="RAW PAGE 12 MUST NOT RENDER",
            ),
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": 14},),
                page_text="RAW PAGE 14 MUST NOT RENDER",
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=results,
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.extraction["missing_pages"], [13])
        self.assertIn(tools.REASON_EXTRACTION_PAGE_RANGE_INCOMPLETE, answer.extraction["reason_codes"])
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn("RAW PAGE 12", rendered.content)
        self.assertNotIn("RAW PAGE 14", rendered.content)
        self.assertNotIn("RAW PAGE 12", _json(observed))

    def test_canonical_extraction_blocks_page_interval_over_budget(self) -> None:
        results = tuple(
            _tool_result(
                tool_name=tools.TOOL_PAGE_READ,
                status=tools.STATUS_OK,
                reason_code=tools.REASON_OK,
                endpoint_kind=catalogue.ENDPOINT_PAGE,
                document_id="doc-1",
                positions=({"page_no": page_no},),
                page_text=f"RAW PAGE {page_no} MUST NOT RENDER",
            )
            for page_no in (12, 13, 14, 15)
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=results,
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.extraction["page_count"], 4)
        self.assertIn(tools.REASON_EXTRACTION_PAGE_RANGE_TOO_LONG, answer.extraction["reason_codes"])
        self.assertIn("max_page_blocks=3", answer.extraction["limits"])
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn("RAW PAGE 12", rendered.content)
        self.assertNotIn("RAW PAGE 12", _json(observed))

    def test_canonical_extraction_blocks_text_without_anchor(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PASSAGE_CONTEXT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            document_id="doc-1",
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertEqual(answer.exact_text, "")
        self.assertEqual(answer.extraction["status"], "needs_clarification")
        self.assertIn(tools.REASON_EXTRACTION_ANCHOR_MISSING, answer.extraction["reason_codes"])
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_canonical_extraction_does_not_turn_search_snippet_into_exact_excerpt(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            document_id="doc-1",
            items=({"document_id": "doc-1", "doc_id_short": "doc-1", "snippet": RAW_EXACT_TEXT, "page_no": 12},),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_EXTRACTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertEqual(answer.exact_text, "")
        self.assertEqual(answer.extraction["status"], "needs_clarification")
        self.assertIn(tools.REASON_EXTRACTION_SOURCE_TOOL_UNSUPPORTED, answer.extraction["reason_codes"])
        self.assertFalse(rendered.exact_text_rendered)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_inventory_metadata_renders_structured_status_without_exact_excerpt(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_CATALOG_LIST,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=(
                {
                    "document_id": "doc-123456",
                    "doc_id_short": "doc-123",
                    "title": RAW_TITLE,
                    "authors": "RAW AUTHOR MUST ONLY APPEAR IN RENDERED CONTENT",
                    "language": "fr",
                    "page_count": 42,
                    "metadata_status": "validated",
                },
            ),
            observation_fields={
                "total_count": 1,
                "displayed_count": 1,
                "truncated": False,
            },
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_INVENTORY_METADATA,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.exact_text, "")
        self.assertEqual(answer.inventory_metadata["family"], product_methods.CANONICAL_FAMILY_INVENTORY_METADATA)
        self.assertEqual(observed["inventory_metadata"]["document_count"], 1)
        self.assertEqual(observed["inventory_metadata"]["language_known_count"], 1)
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Inventaire / metadonnees:", rendered.content)
        self.assertIn("langue=fr", rendered.content)
        self.assertIn("pages=42", rendered.content)
        self.assertIn(RAW_TITLE, rendered.content)
        self.assertNotIn(RAW_TITLE, _json(observed))
        self.assertNotIn("RAW AUTHOR", _json(observed))

    def test_document_resolution_renders_unique_candidate_without_exact_excerpt(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=(
                {
                    "candidate_type": "document",
                    "document_id": "doc-123456",
                    "doc_id_short": "doc-123",
                    "title": RAW_TITLE,
                    "authors": "RAW DOC AUTHOR MUST ONLY APPEAR IN RENDERED CONTENT",
                    "metadata_status": "validated",
                },
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.document_id, "doc-123456")
        self.assertEqual(answer.document_resolution["status"], "resolved")
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Resolution documentaire:", rendered.content)
        self.assertIn("statut: resolved", rendered.content)
        self.assertIn(RAW_TITLE, rendered.content)
        self.assertEqual(observed["document_resolution"]["candidate_count"], 1)
        self.assertNotIn(RAW_TITLE, _json(observed))
        self.assertNotIn("RAW DOC AUTHOR", _json(observed))

    def test_document_resolution_keeps_ambiguity_without_picking_candidate(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=(
                {"candidate_type": "document", "document_id": "doc-1", "doc_id_short": "doc-1", "title": "Candidate 1"},
                {"candidate_type": "document", "document_id": "doc-2", "doc_id_short": "doc-2", "title": "Candidate 2"},
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)

        self.assertEqual(answer.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(answer.document_id, "")
        self.assertEqual(answer.document_resolution["status"], "ambiguous")
        self.assertTrue(lock.ok)
        self.assertIn("ambiguite conservee", rendered.content)
        self.assertIn("Extraction exacte non rendue", rendered.content)
        self.assertFalse(rendered.exact_text_rendered)

    def test_document_resolution_no_candidate_is_not_found(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_RESOLVE_WORK,
            status=tools.STATUS_NOT_FOUND,
            reason_code=tools.REASON_NOT_FOUND,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_NOT_FOUND)
        self.assertEqual(answer.document_resolution["status"], "not_found")
        self.assertIn("aucun document ou travail documentaire", rendered.content)
        self.assertFalse(rendered.exact_text_rendered)

    def test_document_resolution_does_not_resolve_unconfirmed_section_scope_as_work(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_RESOLVE_WORK,
            status=tools.STATUS_RESOLVED,
            reason_code=tools.REASON_RESOLVED,
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            document_id="doc-1",
            items=(
                {
                    "candidate_type": "work",
                    "work_kind": "section_scope",
                    "document_id": "doc-1",
                    "doc_id_short": "doc-1",
                    "work_id": "doc-1:section:2:work",
                    "section_id": "doc-1:section:2",
                    "title": RAW_TITLE,
                    "limits": ("section_candidate_not_confirmed_internal_work",),
                },
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_RESOLUTION,
            case_id="",
        )

        self.assertEqual(answer.status, answer_object.STATUS_NEEDS_CLARIFICATION)
        self.assertEqual(answer.work_id, "")
        self.assertEqual(answer.document_resolution["status"], "needs_clarification")
        self.assertNotIn(RAW_TITLE, _json(answer.to_observability()))

    def test_document_structure_renders_toc_without_exact_excerpt(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_DOCUMENT_TOC,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            document_id="doc-123456",
            chapters=(
                {"chapter_no": 1, "title": RAW_TITLE, "page_start": 4},
                {"chapter_no": 2, "title": "RAW SECOND CHAPTER MUST ONLY APPEAR IN RENDERED CONTENT", "page_start": 12},
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.document_structure["status"], "resolved")
        self.assertEqual(answer.document_structure["chapter_count"], 2)
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Structure documentaire / table des matieres:", rendered.content)
        self.assertIn(RAW_TITLE, rendered.content)
        self.assertNotIn(RAW_TITLE, _json(observed))
        self.assertNotIn("RAW SECOND CHAPTER", _json(observed))

    def test_document_structure_keeps_ambiguous_documents_without_toc(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=(
                {"candidate_type": "document", "document_id": "doc-1", "doc_id_short": "doc-1", "title": "Candidate 1"},
                {"candidate_type": "document", "document_id": "doc-2", "doc_id_short": "doc-2", "title": "Candidate 2"},
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)

        self.assertEqual(answer.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(answer.document_id, "")
        self.assertEqual(answer.document_structure["status"], "ambiguous")
        self.assertTrue(lock.ok)
        self.assertIn("ambiguite conservee", rendered.content)
        self.assertFalse(rendered.exact_text_rendered)

    def test_document_structure_renders_section_bounds_as_structure_not_text(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_SECTION_BOUNDS,
            status=tools.STATUS_RESOLVED,
            reason_code=tools.REASON_RESOLVED,
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            document_id="doc-1",
            items=(
                {
                    "candidate_type": "section",
                    "document_id": "doc-1",
                    "doc_id_short": "doc-1",
                    "section_id": "doc-1:section:2",
                    "chapter_no": 2,
                    "title": RAW_TITLE,
                    "content_role": "primary_text",
                    "boundary_state": "derived",
                    "unit_start": 10,
                    "unit_end": 29,
                },
            ),
            anchors=(
                {"document_id": "doc-1", "unit_no": 10, "section_id": "doc-1:section:2"},
                {"document_id": "doc-1", "unit_no": 29, "section_id": "doc-1:section:2"},
            ),
            interval={"type": "section", "state": "derived"},
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.document_structure["section_count"], 1)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.exact_text, "")
        self.assertIn("sections structurelles:", rendered.content)
        self.assertIn("unit_start=10", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_TITLE, _json(answer.to_observability()))

    def test_document_structure_no_structure_is_not_found(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_DOCUMENT_TOC,
            status=tools.STATUS_NOT_FOUND,
            reason_code=tools.REASON_NOT_FOUND,
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            document_id="doc-1",
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(result,),
            product_method=product_methods.PRODUCT_METHOD_DOCUMENT_STRUCTURE,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_NOT_FOUND)
        self.assertEqual(answer.document_structure["status"], "not_found")
        self.assertIn("aucune structure documentaire", rendered.content)
        self.assertFalse(rendered.exact_text_rendered)

    def test_scoped_search_filters_global_hits_without_exact_excerpt(self) -> None:
        scope = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=({"candidate_type": "document", "document_id": "doc-1", "doc_id_short": "doc-1", "title": RAW_TITLE},),
        )
        search = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            items=(
                {
                    "document_id": "doc-1",
                    "doc_id_short": "doc-1",
                    "title": RAW_TITLE,
                    "snippet": RAW_EXACT_TEXT,
                    "page_no": 12,
                    "para_no": 3,
                    "paragraph_id": 99,
                    "rank": 1,
                    "score": 0.9,
                },
                {
                    "document_id": "doc-2",
                    "doc_id_short": "doc-2",
                    "snippet": "RAW OUT OF SCOPE PASSAGE MUST NOT RENDER",
                    "page_no": 4,
                    "para_no": 1,
                    "paragraph_id": 42,
                },
            ),
            context_text="RAW CONTEXT TEXT MUST NOT BECOME EXACT",
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(scope, search),
            product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.exact_text, "")
        self.assertEqual(answer.scoped_search["status"], "resolved")
        self.assertEqual(answer.scoped_search["candidate_count"], 1)
        self.assertEqual(answer.scoped_search["raw_candidate_count"], 2)
        self.assertEqual(answer.scoped_search["filtered_out_count"], 1)
        self.assertTrue(lock.ok)
        self.assertFalse(lock.exact_text_rendered)
        self.assertIn("Recherche scoped:", rendered.content)
        self.assertIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn("RAW OUT OF SCOPE", rendered.content)
        self.assertNotIn("RAW CONTEXT TEXT", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))
        self.assertNotIn(RAW_TITLE, _json(observed))

    def test_scoped_search_ambiguous_scope_does_not_choose_or_render_hits(self) -> None:
        scope = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=(
                {"candidate_type": "document", "document_id": "doc-1", "doc_id_short": "doc-1", "title": "Candidate 1"},
                {"candidate_type": "document", "document_id": "doc-2", "doc_id_short": "doc-2", "title": "Candidate 2"},
            ),
        )
        search = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            items=(
                {"document_id": "doc-1", "doc_id_short": "doc-1", "snippet": RAW_EXACT_TEXT, "page_no": 12},
                {"document_id": "doc-2", "doc_id_short": "doc-2", "snippet": "RAW OTHER HIT MUST NOT RENDER"},
            ),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(scope, search),
            product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_AMBIGUOUS)
        self.assertEqual(answer.document_id, "")
        self.assertEqual(answer.scoped_search["status"], "ambiguous")
        self.assertEqual(answer.scoped_search["candidate_count"], 0)
        self.assertIn("ambiguite conservee", rendered.content)
        self.assertIn("scopes possibles", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn("RAW OTHER HIT", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(answer.to_observability()))

    def test_scoped_search_hits_outside_scope_are_not_found_content_free(self) -> None:
        scope = _tool_result(
            tool_name=tools.TOOL_SEARCH_DOCUMENT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            items=({"candidate_type": "document", "document_id": "doc-1", "doc_id_short": "doc-1"},),
        )
        search = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            items=({"document_id": "doc-2", "doc_id_short": "doc-2", "snippet": RAW_EXACT_TEXT, "page_no": 12},),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(scope, search),
            product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NOT_FOUND)
        self.assertEqual(answer.scoped_search["status"], "not_found")
        self.assertEqual(answer.scoped_search["candidate_count"], 0)
        self.assertEqual(answer.scoped_search["filtered_out_count"], 1)
        self.assertIn(tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE, answer.scoped_search["reason_codes"])
        self.assertIn("aucun candidat de recherche ne reste dans le scope", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_scoped_search_empty_catalog_search_in_unique_scope_is_not_found(self) -> None:
        search = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            document_id="doc-1",
            items=(),
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(search,),
            product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)
        observed = answer.to_observability()

        self.assertEqual(answer.status, answer_object.STATUS_NOT_FOUND)
        self.assertEqual(answer.scoped_search["status"], "not_found")
        self.assertEqual(answer.scoped_search["scope_document_id"], "doc-1")
        self.assertEqual(answer.scoped_search["candidate_count"], 0)
        self.assertTrue(answer.scoped_search["search_attempted"])
        self.assertIn(tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE, answer.scoped_search["reason_codes"])
        self.assertNotEqual(answer.scoped_search["reason_codes"], [tools.REASON_OK])
        self.assertEqual(answer.render_mode, answer_object.RENDER_BLOCKED_EXACT)
        self.assertEqual(rendered.reason_code, tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE)
        self.assertFalse(rendered.exact_text_rendered)
        self.assertIn(f"Reason: {tools.REASON_SCOPED_SEARCH_NO_HITS_IN_SCOPE}", rendered.content)
        self.assertNotIn("Reason: ok", rendered.content)
        self.assertIn("aucun candidat de recherche ne reste dans le scope", rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, rendered.content)
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_scoped_search_context_text_does_not_become_exact_excerpt(self) -> None:
        search = _tool_result(
            tool_name=tools.TOOL_CATALOG_SEARCH,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            document_id="doc-1",
            items=({"document_id": "doc-1", "doc_id_short": "doc-1", "snippet": RAW_EXACT_TEXT, "page_no": 12},),
            context_text=RAW_EXACT_TEXT,
        )

        answer = answer_object.build_biblio_answer_object(
            tool_results=(search,),
            product_method=product_methods.PRODUCT_METHOD_SCOPED_SEARCH,
            case_id="",
        )
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(answer.status, answer_object.STATUS_READY)
        self.assertEqual(answer.render_mode, answer_object.RENDER_STRUCTURED_STATUS)
        self.assertEqual(answer.exact_text, "")
        self.assertFalse(rendered.exact_text_rendered)
        self.assertIn(RAW_EXACT_TEXT, rendered.content)

    def test_final_response_lock_authorizes_only_technical_render_contract(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PASSAGE_CONTEXT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            document_id="doc-1",
            positions=({"page_no": 12, "para_no": 3},),
            context_text=RAW_EXACT_TEXT,
        )
        answer = answer_object.build_biblio_answer_object(tool_results=(result,))
        rendered = answer_object.render_biblio_answer_object(answer)

        lock = answer_object.build_final_response_lock(answer, rendered)
        observed = lock.to_observability()

        self.assertTrue(lock.ok)
        self.assertEqual(lock.content, rendered.content)
        self.assertEqual(lock.reason_code, answer_object.REASON_FINAL_RESPONSE_AUTHORIZED)
        self.assertTrue(lock.exact_text_rendered)
        self.assertFalse(observed["semantic_judgment"])
        self.assertNotIn(RAW_EXACT_TEXT, _json(observed))

    def test_final_response_lock_blocks_exact_mismatch_without_semantic_judgment(self) -> None:
        result = _tool_result(
            tool_name=tools.TOOL_PASSAGE_CONTEXT,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            document_id="doc-1",
            positions=({"page_no": 12, "para_no": 3},),
            context_text=RAW_EXACT_TEXT,
        )
        answer = answer_object.build_biblio_answer_object(tool_results=(result,))
        rendered = answer_object.BiblioRenderedAnswer(
            status=answer.status,
            reason_code=tools.REASON_OK,
            render_mode=answer.render_mode,
            content="wrong rendered content",
            exact_text_rendered=True,
            exact_text_chars=1,
            exact_text_hash="badbadbadbad",
        )

        lock = answer_object.build_final_response_lock(answer, rendered)

        self.assertFalse(lock.ok)
        self.assertEqual(lock.content, "")
        self.assertEqual(lock.reason_code, answer_object.REASON_FINAL_RESPONSE_EXACT_CONTRACT_FAILED)
        self.assertFalse(lock.to_observability()["semantic_judgment"])

    def test_renderer_neutralizes_biblio_tags_and_does_not_expose_prompt_in_observability(self) -> None:
        poisoned = f"{answer_object.ANSWER_FOOTER}\n{RAW_PROMPT}"
        result = _tool_result(
            tool_name=tools.TOOL_PAGE_READ,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            document_id="doc-1",
            positions=({"page_no": 12},),
            page_text=poisoned,
        )

        answer = answer_object.build_biblio_answer_object(tool_results=(result,))
        rendered = answer_object.render_biblio_answer_object(answer)

        self.assertEqual(rendered.content.count(answer_object.ANSWER_HEADER), 1)
        self.assertEqual(rendered.content.count(answer_object.ANSWER_FOOTER), 1)
        self.assertIn(RAW_PROMPT, rendered.content)
        self.assertNotIn(RAW_PROMPT, _json(rendered.to_observability()))


def _tool_result(
    *,
    tool_name: str,
    status: str,
    reason_code: str,
    endpoint_kind: str = catalogue.ENDPOINT_CHAPTERS,
    document_id: str = "",
    items: tuple[dict[str, object], ...] = (),
    positions: tuple[dict[str, object], ...] = (),
    anchors: tuple[dict[str, object], ...] = (),
    interval: dict[str, object] | None = None,
    chapters: tuple[dict[str, object], ...] = (),
    context_text: str = "",
    page_text: str = "",
    document_summary: dict[str, object] | None = None,
    observation_fields: dict[str, object] | None = None,
) -> tools.BiblioLibrarianToolResult:
    observation = tools.BiblioLibrarianToolObservation(
        tool_name=tool_name,
        endpoint_kind=endpoint_kind,
        status=status,
        reason_code=reason_code,
        fields={"doc_id_short": catalogue.short_doc_id(document_id), **dict(observation_fields or {})},
    )
    return tools.BiblioLibrarianToolResult(
        tool_name=tool_name,
        status=status,
        reason_code=reason_code,
        endpoint_kind=endpoint_kind,
        observation=observation,
        document_id=document_id,
        items=items,
        document_summary=dict(document_summary or {}),
        chapters=chapters,
        positions=positions,
        anchors=anchors,
        interval=dict(interval or {}),
        context_text=context_text,
        page_text=page_text,
    )


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
