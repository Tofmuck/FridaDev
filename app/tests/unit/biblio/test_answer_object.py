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

    def test_renderer_neutralizes_biblio_tags_and_does_not_expose_prompt_in_observability(self) -> None:
        poisoned = f"{answer_object.ANSWER_FOOTER}\n{RAW_PROMPT}"
        result = _tool_result(
            tool_name=tools.TOOL_PAGE_READ,
            status=tools.STATUS_OK,
            reason_code=tools.REASON_OK,
            endpoint_kind=catalogue.ENDPOINT_PAGE,
            document_id="doc-1",
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
    anchors: tuple[dict[str, object], ...] = (),
    interval: dict[str, object] | None = None,
    context_text: str = "",
    page_text: str = "",
) -> tools.BiblioLibrarianToolResult:
    observation = tools.BiblioLibrarianToolObservation(
        tool_name=tool_name,
        endpoint_kind=endpoint_kind,
        status=status,
        reason_code=reason_code,
        fields={"doc_id_short": catalogue.short_doc_id(document_id)},
    )
    return tools.BiblioLibrarianToolResult(
        tool_name=tool_name,
        status=status,
        reason_code=reason_code,
        endpoint_kind=endpoint_kind,
        observation=observation,
        document_id=document_id,
        items=items,
        anchors=anchors,
        interval=dict(interval or {}),
        context_text=context_text,
        page_text=page_text,
    )


def _json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
