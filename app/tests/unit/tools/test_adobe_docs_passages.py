from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_passages, adobe_docs_reader, adobe_docs_sources


def _read_result(
    markdown: str,
    source_type: str = adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
    *,
    product: str = adobe_docs_sources.PRODUCT_PHOTOSHOP,
    canonical_url: str = 'https://helpx.adobe.com/photoshop/using/layers.html',
) -> adobe_docs_reader.AdobeDocsReadResult:
    return adobe_docs_reader.AdobeDocsReadResult(
        status=adobe_docs_reader.STATUS_SUCCESS,
        product=product,
        source_type=source_type,
        canonical_url=canonical_url,
        markdown=markdown,
        chars=len(markdown),
        url_sha256_12='testhash',
    )


class AdobeDocsPassagesTests(unittest.TestCase):
    def test_long_page_produces_multiple_bounded_passages(self) -> None:
        markdown = """
# Layers
Use layers to compose images and edit objects without changing the original image. Layers can contain text, masks, shapes and adjustments.

## Masks
Layer masks hide or reveal parts of a layer. Paint with black to hide and white to reveal. Use masks for non destructive photo editing.

## Adjustments
Adjustment layers change color and tone without damaging the original pixels. Clip an adjustment to affect only one layer.
"""

        passages = adobe_docs_passages.split_adobe_markdown(
            markdown,
            _read_result(markdown),
            max_passage_chars=130,
        )

        self.assertGreaterEqual(len(passages), 3)
        self.assertTrue(all(passage.chars <= 130 for passage in passages))

    def test_total_injectable_budget_is_respected(self) -> None:
        markdown = """
# Layers
Use layers to compose images and edit layer masks with non destructive adjustments for a photo project.

## Masks
Layer masks hide or reveal parts of a photo layer with black and white brush edits.

## Adjustment layers
Adjustment layers change color and tone for a photo layer without changing original pixels.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser les layer masks et adjustment layers ?',
            [_read_result(markdown)],
            max_passage_chars=140,
            passage_count=5,
            prompt_budget_chars=180,
        )

        self.assertLessEqual(selection.total_chars, 180)
        self.assertTrue(all(passage.chars <= 140 for passage in selection.passages))

    def test_chunking_does_not_create_heading_only_passages(self) -> None:
        markdown = """
# Layer masks
Layer masks hide and reveal pixels with brush edits, grayscale controls, selections, refinements, density settings, feather settings, non destructive edits and reusable compositions.
"""

        passages = adobe_docs_passages.split_adobe_markdown(
            markdown,
            _read_result(markdown),
            max_passage_chars=80,
        )

        self.assertGreaterEqual(len(passages), 2)
        self.assertTrue(all(passage.text != passage.heading for passage in passages))
        self.assertTrue(all(passage.chars <= 80 for passage in passages))

    def test_ranking_finds_passage_with_question_terms(self) -> None:
        markdown = """
# Tools
The crop tool changes image boundaries.

## Layer masks
Layer masks hide and reveal pixels without destructive editing.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser les layer masks ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.passages[0].heading, 'Layer masks')
        self.assertIn('Layer masks', selection.passages[0].text)

    def test_french_layer_mask_alias_finds_english_passage(self) -> None:
        markdown = """
# Layer masks
Layer masks hide and reveal pixels without destructive editing.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser les masques de calque ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.passages[0].heading, 'Layer masks')
        self.assertIn(adobe_docs_passages.REASON_SCORE_ALIAS_OVERLAP, selection.passages[0].reason_codes)

    def test_french_layers_alias_finds_english_passage(self) -> None:
        markdown = """
# Layers
Layers let you compose images and keep edits separate from original pixels.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment gerer les calques ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.passages[0].heading, 'Layers')
        self.assertIn(adobe_docs_passages.REASON_SCORE_ALIAS_OVERLAP, selection.passages[0].reason_codes)

    def test_illustrator_pen_alias_finds_pen_tool(self) -> None:
        markdown = """
# Pen tool
The Pen tool draws straight and curved paths for precise vector artwork in Illustrator.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser l outil plume ?',
            [
                _read_result(
                    markdown,
                    product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                    canonical_url='https://helpx.adobe.com/illustrator/using/drawing-pen-tool.html',
                )
            ],
        )

        self.assertEqual(selection.passages[0].product, adobe_docs_sources.PRODUCT_ILLUSTRATOR)
        self.assertEqual(selection.passages[0].heading, 'Pen tool')
        self.assertIn(adobe_docs_passages.REASON_SCORE_ALIAS_OVERLAP, selection.passages[0].reason_codes)

    def test_generic_tool_alias_does_not_promote_arbitrary_passage(self) -> None:
        markdown = """
# Crop tool
The Crop tool changes image boundaries and trims a canvas for photo composition.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Quel outil pour gerer une facture ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.evidence, adobe_docs_passages.EVIDENCE_INSUFFICIENT)
        self.assertEqual(selection.passages, ())

    def test_version_question_favors_release_notes(self) -> None:
        help_markdown = """
# Layer masks
Layer masks hide and reveal pixels for editing.
"""
        release_markdown = """
# Release notes
Version 27.7 adds updated Photoshop desktop features and improvements.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Quoi de neuf dans la version 27.7 ?',
            [
                _read_result(help_markdown, adobe_docs_sources.SOURCE_TYPE_HELP_PAGE),
                _read_result(release_markdown, adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES),
            ],
        )

        self.assertEqual(selection.passages[0].source_type, adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES)
        self.assertIn(adobe_docs_passages.REASON_SOURCE_RELEASE_QUERY, selection.passages[0].reason_codes)

    def test_bug_question_favors_known_issues(self) -> None:
        help_markdown = """
# Layers
Layers help compose images.
"""
        issue_markdown = """
# Known issues
Photoshop may crash when opening a cloud document. This known issue has a workaround and fixed status.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Ce bug de crash est-il connu ?',
            [
                _read_result(help_markdown, adobe_docs_sources.SOURCE_TYPE_HELP_PAGE),
                _read_result(issue_markdown, adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES),
            ],
        )

        self.assertEqual(selection.passages[0].source_type, adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES)
        self.assertIn(adobe_docs_passages.REASON_SOURCE_ISSUE_QUERY, selection.passages[0].reason_codes)

    def test_navigation_footer_is_excluded_or_declassified(self) -> None:
        markdown = """
# Navigation
[All apps](/photoshop/desktop.html)
[Buy now](/photoshop/buy.html)
[Privacy](/photoshop/privacy.html)

# Layer masks
Layer masks hide and reveal pixels without destructive editing in Photoshop documents.
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser les layer masks ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.passages[0].heading, 'Layer masks')
        self.assertNotIn('Buy now', selection.passages[0].text)

    def test_no_relevant_passage_gives_insufficient_evidence(self) -> None:
        markdown = """
# Navigation
[All apps](/photoshop/desktop.html)
[Buy now](/photoshop/buy.html)
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Comment utiliser les masques ?',
            [_read_result(markdown)],
        )

        self.assertEqual(selection.evidence, adobe_docs_passages.EVIDENCE_INSUFFICIENT)
        self.assertEqual(selection.passages, ())
        self.assertIn(adobe_docs_passages.REASON_NO_RELEVANT_PASSAGE, selection.reason_codes)

    def test_passages_are_memory_only_and_no_persistence_api_exists(self) -> None:
        self.assertFalse(hasattr(adobe_docs_passages, 'save_adobe_passages'))
        self.assertFalse(hasattr(adobe_docs_passages, 'persist_adobe_passages'))
        self.assertFalse(hasattr(adobe_docs_passages, 'store_adobe_passages'))

    def test_repr_and_content_free_export_do_not_contain_passage_text(self) -> None:
        secret_text = 'Synthetic Adobe procedure text that must stay out of repr and content free exports.'
        markdown = f"""
# Secret section
{secret_text}
"""

        selection = adobe_docs_passages.select_adobe_passages(
            'Synthetic procedure',
            [_read_result(markdown)],
        )
        passage = selection.passages[0]

        self.assertIn(secret_text, passage.text)
        self.assertNotIn(secret_text, repr(passage))
        self.assertNotIn(secret_text, repr(selection))
        self.assertNotIn(secret_text, str(passage.as_content_free_dict()))
        self.assertNotIn(secret_text, str(selection.as_content_free_dict()))

    def test_citation_metadata_is_preserved(self) -> None:
        markdown = """
# Layer masks
Layer masks hide and reveal pixels without destructive editing.
"""

        passage = adobe_docs_passages.select_adobe_passages(
            'layer masks',
            [_read_result(markdown)],
        ).passages[0]

        self.assertEqual(passage.product, adobe_docs_sources.PRODUCT_PHOTOSHOP)
        self.assertEqual(passage.source_type, adobe_docs_sources.SOURCE_TYPE_HELP_PAGE)
        self.assertEqual(passage.canonical_url, 'https://helpx.adobe.com/photoshop/using/layers.html')
        self.assertEqual(passage.heading, 'Layer masks')
        self.assertEqual(passage.section_path, ('Layer masks',))


if __name__ == '__main__':
    unittest.main()
