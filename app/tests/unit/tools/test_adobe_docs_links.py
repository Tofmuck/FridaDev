from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import adobe_docs_links, adobe_docs_sources


BASE_PHOTOSHOP = 'https://helpx.adobe.com/photoshop/desktop.html'
SYNTHETIC_MARKDOWN = """
[Relative layers](/photoshop/using/layers.html#intro)
[Relative layers duplicate](/photoshop/using/layers.html?tracking=abc)
[Release notes](/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html)
[Known issues](/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html)
[Illustrator wrong product](/illustrator/desktop.html)
[Community](https://community.adobe.com/p/photoshop)
[Learn](https://www.adobe.com/learn/photoshop)
[PDF](/photoshop/guide.pdf)
[Image](/photoshop/image.png)
[Video](/photoshop/video.mp4)
[External](https://example.com/photoshop/using/layers.html)
"""


class AdobeDocsLinksTests(unittest.TestCase):
    def test_relative_links_are_resolved_and_fragments_removed(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        self.assertEqual(links[0].canonical_url, 'https://helpx.adobe.com/photoshop/using/layers.html')
        self.assertIn(adobe_docs_sources.REASON_FRAGMENT_REMOVED, links[0].reason_codes)
        self.assertIn(adobe_docs_links.REASON_RELATIVE_LINK_RESOLVED, links[0].reason_codes)

    def test_query_string_is_removed_with_reason_code(self) -> None:
        markdown = '[Layers](/photoshop/using/layers.html?tracking=abc)'

        links = adobe_docs_links.extract_adobe_links(markdown, BASE_PHOTOSHOP, 'photoshop')

        self.assertEqual(links[0].canonical_url, 'https://helpx.adobe.com/photoshop/using/layers.html')
        self.assertIn(adobe_docs_sources.REASON_QUERY_REMOVED, links[0].reason_codes)

    def test_duplicates_are_deduped_stably(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        self.assertEqual(
            [link.canonical_url for link in links],
            [
                'https://helpx.adobe.com/photoshop/using/layers.html',
                'https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html',
                'https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html',
            ],
        )

    def test_wrong_product_non_helpx_pdf_media_community_and_learn_are_refused(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')
        urls = {link.canonical_url for link in links}

        self.assertNotIn('https://helpx.adobe.com/illustrator/desktop.html', urls)
        self.assertFalse(any('community.adobe.com' in url for url in urls))
        self.assertFalse(any('www.adobe.com' in url for url in urls))
        self.assertFalse(any(url.endswith('.pdf') for url in urls))
        self.assertFalse(any(url.endswith('.png') for url in urls))
        self.assertFalse(any(url.endswith('.mp4') for url in urls))
        self.assertFalse(any('example.com' in url for url in urls))

    def test_source_types_are_classified(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')
        by_url = {link.canonical_url: link for link in links}

        self.assertEqual(
            by_url['https://helpx.adobe.com/photoshop/desktop/whats-new/photoshop-on-desktop-release-notes.html'].source_type,
            adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES,
        )
        self.assertEqual(
            by_url[
                'https://helpx.adobe.com/photoshop/desktop/troubleshoot/performance-stability-issues/known-and-fixed-issues.html'
            ].source_type,
            adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES,
        )
        self.assertEqual(
            by_url['https://helpx.adobe.com/photoshop/using/layers.html'].source_type,
            adobe_docs_sources.SOURCE_TYPE_HELP_PAGE,
        )

    def test_ranking_favors_release_notes_for_version_question(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        ranked = adobe_docs_links.rank_adobe_links('Quoi de neuf dans la version Photoshop ?', links, 'photoshop')

        self.assertEqual(ranked[0].source_type, adobe_docs_sources.SOURCE_TYPE_RELEASE_NOTES)
        self.assertIn(adobe_docs_links.REASON_RANK_RELEASE_QUERY, ranked[0].reason_codes)

    def test_ranking_favors_known_issues_for_bug_question(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        ranked = adobe_docs_links.rank_adobe_links('Ce bug est-il connu et corrige ?', links, 'photoshop')

        self.assertEqual(ranked[0].source_type, adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES)
        self.assertIn(adobe_docs_links.REASON_RANK_ISSUE_QUERY, ranked[0].reason_codes)

    def test_ranking_favors_help_pages_for_usage_question(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        ranked = adobe_docs_links.rank_adobe_links('Comment utiliser les calques ?', links, 'photoshop')

        self.assertEqual(ranked[0].source_type, adobe_docs_sources.SOURCE_TYPE_HELP_PAGE)
        self.assertIn(adobe_docs_links.REASON_RANK_USAGE_QUERY, ranked[0].reason_codes)

    def test_ranking_limit_is_respected(self) -> None:
        links = adobe_docs_links.extract_adobe_links(SYNTHETIC_MARKDOWN, BASE_PHOTOSHOP, 'photoshop')

        ranked = adobe_docs_links.rank_adobe_links('version et bug', links, 'photoshop', limit=2)

        self.assertEqual(len(ranked), 2)
        self.assertTrue(all(adobe_docs_links.REASON_RANK_LIMIT_APPLIED in link.reason_codes for link in ranked))

    def test_ranking_limit_is_capped_to_max_follow_link_limit(self) -> None:
        links = adobe_docs_links.extract_adobe_links(
            '\n'.join(
                f'[Help {index}](/photoshop/using/help-{index}.html)'
                for index in range(12)
            ),
            BASE_PHOTOSHOP,
            'photoshop',
        )

        ranked = adobe_docs_links.rank_adobe_links('usage', links, 'photoshop', limit=99)

        self.assertEqual(len(ranked), adobe_docs_links.MAX_FOLLOW_LINK_LIMIT)

    def test_registered_seeds_are_available_when_no_links_are_extracted(self) -> None:
        ranked = adobe_docs_links.rank_adobe_links('bug connu', (), 'illustrator', limit=4)

        self.assertGreaterEqual(len(ranked), 3)
        self.assertEqual(ranked[0].source_type, adobe_docs_sources.SOURCE_TYPE_KNOWN_ISSUES)
        self.assertTrue(all(adobe_docs_links.REASON_SEED_CANDIDATE in link.reason_codes for link in ranked))

    def test_repr_and_content_free_export_do_not_include_markdown_or_anchor_text(self) -> None:
        secret_anchor = 'Titre Adobe synthetique tres long qui ne doit pas etre stocke dans les exports'
        markdown = f'[{secret_anchor}](/photoshop/using/layers.html)'

        link = adobe_docs_links.extract_adobe_links(markdown, BASE_PHOTOSHOP, 'photoshop')[0]
        ranked = adobe_docs_links.rank_adobe_links('usage', (link,), 'photoshop')[0]

        self.assertNotIn(secret_anchor, repr(link))
        self.assertNotIn(secret_anchor, repr(ranked))
        self.assertNotIn(secret_anchor, str(link.as_content_free_dict()))
        self.assertNotIn(secret_anchor, str(ranked.as_content_free_dict()))
        self.assertNotIn(markdown, repr(link))
        self.assertNotIn(markdown, repr(ranked))


if __name__ == '__main__':
    unittest.main()
