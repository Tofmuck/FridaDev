from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import passage_extractor as extractor
from biblio import prompt_lane


RAW_PASSAGE_ONE = "SYNTHETIC_BIBLIO_PASSAGE_ONE_FOR_PROMPT_ONLY"
RAW_PASSAGE_TWO = "SYNTHETIC_BIBLIO_PASSAGE_TWO_FOR_PROMPT_ONLY"


class BiblioPromptLaneTests(unittest.TestCase):
    def test_extracted_passage_produces_lane_with_exact_tags(self) -> None:
        result = _passage(RAW_PASSAGE_ONE)

        lane = prompt_lane.build_biblio_prompt_lane([result])
        content = lane.message["content"]

        self.assertEqual(lane.message["role"], "system")
        self.assertTrue(content.startswith(prompt_lane.LANE_HEADER))
        self.assertTrue(content.endswith(prompt_lane.LANE_FOOTER))
        self.assertIn("Passage 1", content)
        self.assertIn("Source: catalogue_doc=doc-1234, page=12, paragraphe=3, paragraph_id=99", content)
        self.assertIn("Texte:\n" + RAW_PASSAGE_ONE, content)
        self.assertEqual(lane.passage_count, 1)
        self.assertEqual(lane.skipped_count, 0)

    def test_no_extracted_passage_produces_no_lane(self) -> None:
        lane = prompt_lane.build_biblio_prompt_lane(
            [
                _passage("", status=extractor.STATUS_TOO_LONG, reason_code=extractor.REASON_PASSAGE_TOO_LONG),
                _passage("", status=extractor.STATUS_EMPTY, reason_code=extractor.REASON_PASSAGE_EMPTY),
            ]
        )

        self.assertIsNone(lane.message)
        self.assertEqual(lane.passage_count, 0)
        self.assertEqual(lane.skipped_count, 2)
        self.assertEqual(
            [decision.reason_code for decision in lane.decisions],
            [prompt_lane.REASON_NON_EXTRACTED, prompt_lane.REASON_NON_EXTRACTED],
        )

    def test_non_extracted_results_are_ignored_even_if_they_hold_text(self) -> None:
        skipped_text = "SYNTHETIC_TEXT_SHOULD_NOT_ENTER_BIBLIO_PROMPT"

        lane = prompt_lane.build_biblio_prompt_lane(
            [
                _passage(skipped_text, status=extractor.STATUS_TOO_LONG, reason_code=extractor.REASON_PASSAGE_TOO_LONG),
                _passage(RAW_PASSAGE_ONE),
            ]
        )
        content = lane.message["content"]

        self.assertIn(RAW_PASSAGE_ONE, content)
        self.assertNotIn(skipped_text, content)
        self.assertEqual(lane.passage_count, 1)
        self.assertEqual(lane.skipped_count, 1)

    def test_max_passages_limit_skips_later_extracted_results(self) -> None:
        lane = prompt_lane.build_biblio_prompt_lane(
            [_passage(RAW_PASSAGE_ONE), _passage(RAW_PASSAGE_TWO, paragraph_id=100)],
            max_passages=1,
        )
        content = lane.message["content"]

        self.assertIn(RAW_PASSAGE_ONE, content)
        self.assertNotIn(RAW_PASSAGE_TWO, content)
        self.assertEqual(lane.passage_count, 1)
        self.assertEqual(lane.skipped_count, 1)
        self.assertEqual(lane.decisions[1].reason_code, prompt_lane.REASON_MAX_PASSAGES_REACHED)

    def test_max_total_chars_limit_skips_passage_that_would_overflow_lane(self) -> None:
        first_only = prompt_lane.build_biblio_prompt_lane([_passage(RAW_PASSAGE_ONE)])

        lane = prompt_lane.build_biblio_prompt_lane(
            [_passage(RAW_PASSAGE_ONE), _passage(RAW_PASSAGE_TWO, paragraph_id=100)],
            max_total_chars=first_only.chars,
        )
        content = lane.message["content"]

        self.assertIn(RAW_PASSAGE_ONE, content)
        self.assertNotIn(RAW_PASSAGE_TWO, content)
        self.assertEqual(lane.passage_count, 1)
        self.assertEqual(lane.skipped_count, 1)
        self.assertEqual(lane.decisions[1].reason_code, prompt_lane.REASON_MAX_TOTAL_CHARS_REACHED)
        self.assertGreater(lane.decisions[1].lane_chars_if_injected, first_only.chars)

    def test_observability_is_content_free(self) -> None:
        lane = prompt_lane.build_biblio_prompt_lane(
            [
                _passage(RAW_PASSAGE_ONE, passage_hash="hash-one"),
                _passage(RAW_PASSAGE_TWO, paragraph_id=100, passage_hash="hash-two"),
            ],
            max_passages=1,
        )
        observed = lane.to_observability()

        self.assertEqual(observed["passage_count"], 1)
        self.assertEqual(observed["skipped_count"], 1)
        self.assertEqual(observed["hashes"], ["hash-one"])
        self.assertEqual(observed["doc_id_shorts"], ["doc-1234"])
        self.assertEqual(observed["positions"][0]["paragraph_id"], 99)
        self.assertNotIn(RAW_PASSAGE_ONE, str(observed))
        self.assertNotIn(RAW_PASSAGE_TWO, str(observed))
        self.assertNotIn(RAW_PASSAGE_ONE, repr(lane))

    def test_lane_is_distinct_from_active_document_tags(self) -> None:
        lane = prompt_lane.build_biblio_prompt_lane([_passage(RAW_PASSAGE_ONE)])
        content = lane.message["content"]

        self.assertIn(prompt_lane.LANE_HEADER, content)
        self.assertNotIn("[DOCUMENTS ACTIFS DE CONVERSATION]", content)
        self.assertNotIn("[DOCUMENTS ACTIFS INJECTES]", content)
        self.assertNotIn("[DOCUMENTS ACTIFS NON INJECTES]", content)

    def test_prompt_lane_does_not_import_catalogue_client(self) -> None:
        self.assertFalse(hasattr(prompt_lane, "CatalogueClient"))
        self.assertFalse(hasattr(prompt_lane, "CatalogueResponse"))


def _passage(
    passage: str,
    *,
    status: str = extractor.STATUS_EXTRACTED,
    reason_code: str = extractor.REASON_PASSAGE_EXTRACTED,
    doc_id_short: str = "doc-123456",
    passage_hash: str = "",
    page_no: int | None = 12,
    para_no: int | None = 3,
    paragraph_id: int | None = 99,
) -> extractor.BiblioPassageResult:
    return extractor.BiblioPassageResult(
        status=status,
        reason_code=reason_code,
        passage=passage,
        doc_id_short=doc_id_short,
        passage_chars=len(passage),
        passage_hash=passage_hash,
        char_offset=0,
        window_chars=700,
        max_passage_chars=4_000,
        excerpt_start=0,
        excerpt_end=len(passage),
        text_length=len(passage),
        page_no=page_no,
        para_no=para_no,
        paragraph_id=paragraph_id,
    )


if __name__ == "__main__":
    unittest.main()
