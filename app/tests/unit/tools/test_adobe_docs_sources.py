from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_sources


class AdobeDocsSourcesTests(unittest.TestCase):
    def test_photoshop_returns_three_seed_sources(self) -> None:
        sources = adobe_docs_sources.sources_for_product('photoshop')

        self.assertEqual(len(sources), 3)
        self.assertEqual(
            [source.url for source in sources],
            [
                'https://helpx.adobe.com/photoshop/desktop.html',
                'https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html',
                'https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html',
            ],
        )
        self.assertEqual(
            [source.source_type for source in sources],
            [
                adobe_docs_sources.SOURCE_TYPE_HUB,
                adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
                adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES,
            ],
        )

    def test_illustrator_returns_three_seed_sources(self) -> None:
        sources = adobe_docs_sources.sources_for_product('illustrator')

        self.assertEqual(len(sources), 3)
        self.assertEqual(
            [source.url for source in sources],
            [
                'https://helpx.adobe.com/illustrator/desktop.html',
                'https://helpx.adobe.com/illustrator/desktop/new-features/release-notes.html',
                'https://helpx.adobe.com/illustrator/desktop/troubleshoot/known-and-fixed-issues.html',
            ],
        )
        self.assertEqual(
            [source.source_type for source in sources],
            [
                adobe_docs_sources.SOURCE_TYPE_HUB,
                adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
                adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES,
            ],
        )

    def test_unknown_product_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            adobe_docs_sources.sources_for_product('auto')

        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'auto',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_INVALID_PRODUCT)

    def test_photoshop_url_is_rejected_in_illustrator_mode(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html',
            'illustrator',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_WRONG_PRODUCT)

    def test_illustrator_url_is_rejected_in_photoshop_mode(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/illustrator/desktop.html',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_WRONG_PRODUCT)

    def test_community_adobe_is_rejected(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://community.adobe.com/p/photoshop',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_COMMUNITY_FORBIDDEN)

    def test_adobe_learn_is_rejected(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://www.adobe.com/learn/photoshop',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_LEARN_FORBIDDEN)

    def test_pdf_images_and_videos_are_rejected(self) -> None:
        cases = [
            'https://helpx.adobe.com/photoshop/guide.pdf',
            'https://helpx.adobe.com/photoshop/image.png',
            'https://helpx.adobe.com/photoshop/tutorial.mp4',
        ]

        for url in cases:
            with self.subTest(url=url):
                validation = adobe_docs_sources.validate_adobe_url(url, 'photoshop')
                self.assertFalse(validation.ok)
                self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_EXCLUDED_EXTENSION)

    def test_archive_paths_are_rejected(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/archive/old-guide.html',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_EXCLUDED_ARCHIVE_PATH)

    def test_non_https_scheme_is_rejected(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'http://helpx.adobe.com/photoshop/desktop.html',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_INVALID_SCHEME)

    def test_fragment_is_removed_from_canonical_url(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html#workspace',
            'photoshop',
        )

        self.assertTrue(validation.ok)
        self.assertEqual(validation.canonical_url, 'https://helpx.adobe.com/photoshop/desktop.html')
        self.assertIn(adobe_docs_sources.REASON_FRAGMENT_REMOVED, validation.reason_codes)

    def test_query_string_is_removed_with_reason_code(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/desktop.html?tracking=abc',
            'photoshop',
        )

        self.assertTrue(validation.ok)
        self.assertEqual(validation.canonical_url, 'https://helpx.adobe.com/photoshop/desktop.html')
        self.assertIn(adobe_docs_sources.REASON_QUERY_REMOVED, validation.reason_codes)

    def test_strict_host_does_not_allow_wildcard_adobe_domains(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://docs.adobe.com/photoshop/desktop.html',
            'photoshop',
        )

        self.assertFalse(validation.ok)
        self.assertEqual(validation.reason_code, adobe_docs_sources.REASON_HOST_NOT_HELPX)

    def test_help_page_source_type_is_classified(self) -> None:
        validation = adobe_docs_sources.validate_adobe_url(
            'https://helpx.adobe.com/photoshop/using/layers.html',
            'photoshop',
        )

        self.assertTrue(validation.ok)
        self.assertEqual(validation.source_type, adobe_docs_sources.SOURCE_TYPE_HELP_PAGE)

    def test_dedupe_valid_urls_is_stable(self) -> None:
        deduped = adobe_docs_sources.dedupe_valid_adobe_urls(
            [
                'https://helpx.adobe.com/photoshop/desktop.html#workspace',
                'https://helpx.adobe.com/photoshop/desktop.html?tracking=abc',
                'https://helpx.adobe.com/photoshop/using/layers.html',
                'https://community.adobe.com/p/photoshop',
                'https://helpx.adobe.com/photoshop/using/layers.html#intro',
            ],
            'photoshop',
        )

        self.assertEqual(
            [item.canonical_url for item in deduped],
            [
                'https://helpx.adobe.com/photoshop/desktop.html',
                'https://helpx.adobe.com/photoshop/using/layers.html',
            ],
        )


if __name__ == '__main__':
    unittest.main()
