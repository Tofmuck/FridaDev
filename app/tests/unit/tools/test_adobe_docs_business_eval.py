from __future__ import annotations

from dataclasses import dataclass
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_passages, adobe_docs_pipeline, adobe_docs_reader, adobe_docs_sources


@dataclass(frozen=True)
class _BusinessCase:
    label: str
    product: str
    question: str
    expected_heading: str
    expected_source_type: str
    markdown: str


def _read_result(
    case: _BusinessCase,
    *,
    canonical_url: str | None = None,
) -> adobe_docs_reader.AdobeDocsReadResult:
    url = canonical_url or f'https://helpx.adobe.com/{case.product}/using/{case.label}.html'
    return adobe_docs_reader.AdobeDocsReadResult(
        status=adobe_docs_reader.STATUS_SUCCESS,
        product=case.product,
        source_type=case.expected_source_type,
        canonical_url=url,
        markdown=case.markdown,
        chars=len(case.markdown),
        headings=case.markdown.count('\n#'),
        link_count=case.markdown.count(']('),
        filter_used=adobe_docs_reader.CRAWL4AI_FILTER_RAW,
        cache_mode=adobe_docs_reader.CRAWL4AI_CACHE_DISABLED,
        reason_codes=('crawl_raw_primary',),
        url_sha256_12='synthetic',
    )


class _FakeReader:
    def __init__(self, pages: dict[str, tuple[str, str]]) -> None:
        self.pages = dict(pages)
        self.calls: list[tuple[str, str, str]] = []

    def read_adobe_url(self, url, product, source_type=None, **_kwargs):
        self.calls.append((url, product, source_type or ''))
        markdown, resolved_source_type = self.pages.get(url, ('', source_type or ''))
        status = adobe_docs_reader.STATUS_SUCCESS if markdown else adobe_docs_reader.STATUS_EMPTY
        return adobe_docs_reader.AdobeDocsReadResult(
            status=status,
            product=product,
            source_type=resolved_source_type or source_type or '',
            canonical_url=url,
            markdown=markdown,
            chars=len(markdown),
            headings=markdown.count('\n#'),
            link_count=markdown.count(']('),
            filter_used=adobe_docs_reader.CRAWL4AI_FILTER_RAW,
            cache_mode=adobe_docs_reader.CRAWL4AI_CACHE_DISABLED,
            reason_codes=('crawl_raw_primary',),
            url_sha256_12='synthetic',
        )


class AdobeDocsBusinessEvalTests(unittest.TestCase):
    def test_photoshop_business_cases_select_relevant_adobe_source(self) -> None:
        cases = (
            _BusinessCase(
                label='photoshop-hair-mask',
                product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
                question='Comment detourer des cheveux avec un masque de calque ?',
                expected_heading='Layer masks',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Layer masks
Layer masks refine hair selections and hide or reveal pixels without destructive editing.

# Crop
Crop images and adjust canvas boundaries for composition.
""",
            ),
            _BusinessCase(
                label='photoshop-layers',
                product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
                question='Comment gerer les calques dans Photoshop ?',
                expected_heading='Layers',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Layers
Layers keep image edits, text, masks and adjustments separate from the original pixels.
""",
            ),
            _BusinessCase(
                label='photoshop-remove-tool-release',
                product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
                question='Le Remove Tool change dans la version 27.7 ?',
                expected_heading='Release notes',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
                markdown="""
# Release notes
Version 27.7 lists Remove Tool updates, fixes and Photoshop desktop improvements.
""",
            ),
            _BusinessCase(
                label='photoshop-scratch-disk',
                product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
                question='Mon disque de travail est sature dans Photoshop, que faire ?',
                expected_heading='Scratch disks',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Scratch disks
Scratch disks provide temporary storage. Free disk space or choose another scratch disk when Photoshop reports a full scratch disk.
""",
            ),
            _BusinessCase(
                label='photoshop-export',
                product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
                question='Comment exporter une image pour le web ?',
                expected_heading='Export',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Export
Export images for web delivery with file format, size, quality and metadata options.
""",
            ),
        )

        self._assert_business_cases_select_expected_passage(cases)

    def test_illustrator_business_cases_select_relevant_adobe_source(self) -> None:
        cases = (
            _BusinessCase(
                label='illustrator-pen-tool',
                product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                question='Comment utiliser l outil plume ?',
                expected_heading='Pen tool',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Pen tool
The Pen tool draws straight and curved paths for precise vector artwork in Illustrator.
""",
            ),
            _BusinessCase(
                label='illustrator-paths',
                product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                question='Comment modifier des traces propres ?',
                expected_heading='Paths',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Paths
Paths use anchor points, handles and curves to define precise vector artwork.
""",
            ),
            _BusinessCase(
                label='illustrator-vector-logo',
                product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                question='Comment creer un logo vectoriel redimensionnable ?',
                expected_heading='Vector artwork',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Vector artwork
Vector artwork uses paths, shapes and anchor points so logos remain scalable without loss.
""",
            ),
            _BusinessCase(
                label='illustrator-import-psd',
                product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                question='Comment importer un PSD Photoshop dans Illustrator ?',
                expected_heading='Import Photoshop files',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Import Photoshop files
Import or place Photoshop PSD files in Illustrator and manage layers during import.
""",
            ),
            _BusinessCase(
                label='illustrator-pdf-print',
                product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
                question='Comment exporter un PDF propre pour impression ?',
                expected_heading='Adobe PDF options',
                expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                markdown="""
# Adobe PDF options
Save or export Adobe PDF files for print with marks, bleeds, color settings and presets.
""",
            ),
        )

        self._assert_business_cases_select_expected_passage(cases)

    def test_version_and_bug_questions_require_release_or_known_issue_source(self) -> None:
        release_case = _BusinessCase(
            label='illustrator-release-notes',
            product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
            question='Quelles nouveautes de version concernent Illustrator ?',
            expected_heading='Release notes',
            expected_source_type=adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
            markdown="""
# Release notes
Illustrator version updates list new features, fixed issues and compatibility changes.
""",
        )
        issue_case = _BusinessCase(
            label='photoshop-known-issues',
            product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
            question='Ce bug de crash cloud document est-il connu ?',
            expected_heading='Known issues',
            expected_source_type=adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES,
            markdown="""
# Known issues
Photoshop known issues describe crash problems, fixed status and workarounds for cloud documents.
""",
        )

        self._assert_business_cases_select_expected_passage((release_case, issue_case))

    def test_trick_question_with_no_source_evidence_is_insufficient(self) -> None:
        case = _BusinessCase(
            label='invented-tool',
            product=adobe_docs_sources.PRODUCT_PHOTOSHOP,
            question='Confirme l outil officiel Licorne vectorielle dans Photoshop 2030.',
            expected_heading='Layers',
            expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
            markdown="""
# Layers
Layers keep image edits separate and support masks, text and adjustment workflows.
""",
        )

        selection = adobe_docs_passages.select_adobe_passages(
            case.question,
            [_read_result(case)],
        )

        self.assertEqual(selection.evidence, adobe_docs_passages.EVIDENCE_INSUFFICIENT)
        self.assertEqual(selection.passages, ())
        self.assertIn(adobe_docs_passages.REASON_NO_RELEVANT_PASSAGE, selection.reason_codes)

    def test_adobe_active_vs_inactive_evaluation_uses_sources_only_when_requested(self) -> None:
        hub_url = 'https://helpx.adobe.com/photoshop/desktop.html'
        help_url = 'https://helpx.adobe.com/photoshop/using/layer-masks.html'
        release_url = 'https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html'
        issues_url = 'https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html'
        reader = _FakeReader(
            {
                hub_url: (
                    f"""
# Photoshop Help
[Layer masks]({help_url})
Use Photoshop tools, layers and masks for image editing workflows.
""",
                    adobe_docs_sources.SOURCE_TYPE_HUB,
                ),
                release_url: (
                    """
# Release notes
Version updates and Photoshop desktop improvements are listed here.
""",
                    adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
                ),
                issues_url: (
                    """
# Known issues
Known issues and fixed crash problems are listed here.
""",
                    adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES,
                ),
                help_url: (
                    """
# Layer masks
Layer masks refine hair selections and hide or reveal pixels without destructive editing.
""",
                    adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
                ),
            }
        )

        inactive = adobe_docs_pipeline.not_requested_context()
        active = adobe_docs_pipeline.build_adobe_context(
            'Comment detourer des cheveux avec un masque de calque ?',
            adobe_docs_sources.PRODUCT_PHOTOSHOP,
            reader_module=reader,
            crawl_page_limit=4,
            follow_link_limit=4,
        )

        self.assertFalse(inactive.active)
        self.assertEqual(inactive.passages, ())
        self.assertTrue(active.active)
        self.assertEqual(active.product, adobe_docs_sources.PRODUCT_PHOTOSHOP)
        self.assertGreaterEqual(active.selected_passage_count, 1)
        self.assertIn(adobe_docs_sources.SOURCE_TYPE_HELP_PAGE, active.source_types)
        self.assertEqual(reader.calls[0][0], hub_url)
        self.assertEqual(reader.calls[-1][0], help_url)

    def test_business_eval_exports_are_content_free(self) -> None:
        secret_text = 'Synthetic business eval source text that must not leak.'
        case = _BusinessCase(
            label='privacy',
            product=adobe_docs_sources.PRODUCT_ILLUSTRATOR,
            question='Comment exporter un PDF pour impression ?',
            expected_heading='Adobe PDF options',
            expected_source_type=adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
            markdown=f"""
# Adobe PDF options
{secret_text} Export PDF files for print with marks, bleeds and presets.
""",
        )

        selection = adobe_docs_passages.select_adobe_passages(
            case.question,
            [_read_result(case)],
        )

        exported = str(selection.as_content_free_dict())
        self.assertGreaterEqual(selection.selected_count, 1)
        self.assertNotIn(secret_text, repr(selection))
        self.assertNotIn(secret_text, exported)

    def _assert_business_cases_select_expected_passage(self, cases) -> None:
        for case in cases:
            with self.subTest(case=case.label):
                selection = adobe_docs_passages.select_adobe_passages(
                    case.question,
                    [_read_result(case)],
                )

                self.assertIn(
                    selection.evidence,
                    {adobe_docs_passages.EVIDENCE_PARTIAL, adobe_docs_passages.EVIDENCE_SUFFICIENT},
                )
                self.assertGreaterEqual(selection.selected_count, 1)
                self.assertEqual(selection.passages[0].heading, case.expected_heading)
                self.assertEqual(selection.passages[0].source_type, case.expected_source_type)


if __name__ == '__main__':
    unittest.main()
