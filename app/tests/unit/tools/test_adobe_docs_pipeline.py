from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_pipeline, adobe_docs_reader, adobe_docs_sources


class _FakeReader:
    def __init__(self, pages: dict[str, str] | None = None, *, fail_all: bool = False) -> None:
        self.pages = dict(pages or {})
        self.fail_all = fail_all
        self.calls: list[tuple[str, str, str]] = []

    def read_adobe_url(self, url, product, source_type=None, **_kwargs):
        self.calls.append((url, product, source_type or ''))
        if self.fail_all:
            return adobe_docs_reader.AdobeDocsReadResult(
                status=adobe_docs_reader.STATUS_ERROR,
                product=product,
                source_type=source_type or '',
                canonical_url=url,
                reason_code='crawl_error',
                reason_codes=('crawl_error',),
                error_class='SyntheticCrawlError',
                url_sha256_12='readhash',
            )
        markdown = self.pages.get(url, '')
        return adobe_docs_reader.AdobeDocsReadResult(
            status=adobe_docs_reader.STATUS_SUCCESS if markdown else adobe_docs_reader.STATUS_EMPTY,
            product=product,
            source_type=source_type or '',
            canonical_url=url,
            markdown=markdown,
            chars=len(markdown),
            headings=markdown.count('\n#'),
            link_count=markdown.count(']('),
            filter_used=adobe_docs_reader.CRAWL4AI_FILTER_RAW,
            cache_mode=adobe_docs_reader.CRAWL4AI_CACHE_DISABLED,
            reason_codes=('crawl_raw_primary',),
            url_sha256_12='readhash',
        )


class AdobeDocsPipelineTests(unittest.TestCase):
    def test_resolve_request_accepts_only_explicit_adobe_product(self) -> None:
        inactive = adobe_docs_pipeline.resolve_adobe_request({'message': 'hello'})
        self.assertFalse(inactive.active)

        missing = adobe_docs_pipeline.resolve_adobe_request({'specialization_profile': 'adobe'})
        self.assertTrue(missing.active)
        self.assertEqual(missing.error_code, adobe_docs_pipeline.ERROR_ADOBE_PRODUCT_REQUIRED)

        invalid = adobe_docs_pipeline.resolve_adobe_request(
            {'specialization_profile': 'adobe', 'adobe_product': 'auto'}
        )
        self.assertTrue(invalid.active)
        self.assertEqual(invalid.error_code, adobe_docs_pipeline.ERROR_ADOBE_PRODUCT_INVALID)

        valid = adobe_docs_pipeline.resolve_adobe_request(
            {'specialization_profile': 'adobe', 'adobe_product': 'photoshop', 'web_search': True}
        )
        self.assertTrue(valid.active)
        self.assertEqual(valid.product, adobe_docs_sources.PRODUCT_PHOTOSHOP)
        self.assertTrue(valid.web_search_requested)

    def test_build_context_reads_seeds_follows_bounded_links_and_selects_passages(self) -> None:
        hub_url = 'https://helpx.adobe.com/photoshop/desktop.html'
        help_url = 'https://helpx.adobe.com/photoshop/using/layer-masks.html'
        release_url = 'https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html'
        issues_url = 'https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html'
        reader = _FakeReader(
            {
                hub_url: f"""
# Photoshop Help
[Layer masks]({help_url})
Use Photoshop tools and layers for image editing workflows.
""",
                release_url: """
# Release notes
Version updates and Photoshop desktop improvements are listed here.
""",
                issues_url: """
# Known issues
Known issues and fixed crash problems are listed here.
""",
                help_url: """
# Layer masks
Layer masks hide and reveal pixels without destructive editing in Photoshop documents.
""",
            }
        )

        context = adobe_docs_pipeline.build_adobe_context(
            'Comment utiliser les masques de calque ?',
            'photoshop',
            reader_module=reader,
            crawl_page_limit=4,
            follow_link_limit=4,
        )

        self.assertIn(context.status, {'success', 'partial'})
        self.assertEqual(context.product, 'photoshop')
        self.assertEqual(context.seed_count, 3)
        self.assertEqual(context.crawled_page_count, 4)
        self.assertEqual(context.link_candidate_count, 1)
        self.assertGreaterEqual(context.selected_passage_count, 1)
        self.assertIn('help_page', context.source_types)
        self.assertTrue(any(passage.heading == 'Layer masks' for passage in context.passages))
        self.assertEqual(reader.calls[0][0], hub_url)
        self.assertEqual(reader.calls[-1][0], help_url)

    def test_context_error_is_content_free_when_all_reads_fail(self) -> None:
        reader = _FakeReader(fail_all=True)

        context = adobe_docs_pipeline.build_adobe_context(
            'Comment utiliser Photoshop ?',
            'photoshop',
            reader_module=reader,
            crawl_page_limit=3,
        )

        exported = str(context.as_content_free_dict())
        self.assertEqual(context.status, adobe_docs_pipeline.STATUS_ERROR)
        self.assertIn('SyntheticCrawlError', context.error_classes)
        self.assertNotIn('Layer masks hide', exported)
        self.assertNotIn('https://helpx.adobe.com/photoshop/desktop.html', exported)


if __name__ == '__main__':
    unittest.main()
