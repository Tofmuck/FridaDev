from __future__ import annotations

import sys
import unittest
from pathlib import Path


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import web_search_crawl_policy, web_search_profile


class WebSearchCrawlPolicyTests(unittest.TestCase):
    def test_documentation_admin_and_academic_use_bm25_with_fit_fallback(self) -> None:
        for profile in (
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
            web_search_profile.PROFILE_ACADEMIQUE,
        ):
            with self.subTest(profile=profile):
                policy = web_search_crawl_policy.build_search_result_policy(
                    profile,
                    primary_query="documentation officielle API",
                    runtime_max_chars=12000,
                )

                self.assertEqual(policy.primary_filter, "bm25")
                self.assertEqual(policy.fallback_filter, "fit")
                self.assertEqual(policy.query, "documentation officielle API")
                self.assertEqual(policy.cache_mode, "1")
                self.assertEqual(policy.kind, "profile_query_aware_bm25_with_fit_fallback")
                self.assertLessEqual(policy.max_chars, 12000)

    def test_general_and_actualite_remain_fit_without_bm25(self) -> None:
        general = web_search_crawl_policy.build_search_result_policy(
            web_search_profile.PROFILE_GENERAL,
            primary_query="recherche generale",
            runtime_max_chars=9000,
        )
        actualite = web_search_crawl_policy.build_search_result_policy(
            web_search_profile.PROFILE_ACTUALITE,
            primary_query="dernieres nouvelles",
            runtime_max_chars=9000,
        )

        self.assertEqual(general.primary_filter, "fit")
        self.assertEqual(general.fallback_filter, "")
        self.assertEqual(general.cache_mode, "0")
        self.assertEqual(general.kind, "historical_fit")
        self.assertEqual(general.max_chars, 5000)
        self.assertEqual(actualite.primary_filter, "fit")
        self.assertEqual(actualite.fallback_filter, "")
        self.assertEqual(actualite.cache_mode, "0")
        self.assertEqual(actualite.kind, "profile_fit_fresh")
        self.assertEqual(actualite.max_chars, 4500)

    def test_bm25_falls_back_when_empty_error_or_poor(self) -> None:
        policy = web_search_crawl_policy.build_search_result_policy(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
            primary_query="documentation officielle API",
            runtime_max_chars=7000,
        )

        for crawl_result, reason in (
            ({"status": "empty", "markdown": ""}, "bm25_not_success_fit_fallback"),
            ({"status": "error", "markdown": ""}, "bm25_not_success_fit_fallback"),
            ({"status": "success", "markdown": "trop court"}, "bm25_poor_fit_fallback"),
        ):
            with self.subTest(reason=reason):
                should_fallback, actual_reason = web_search_crawl_policy.should_fallback_from_primary(
                    policy,
                    crawl_result,
                )
                self.assertTrue(should_fallback)
                self.assertEqual(actual_reason, reason)

    def test_bm25_does_not_fallback_when_markdown_is_substantial(self) -> None:
        policy = web_search_crawl_policy.build_search_result_policy(
            web_search_profile.PROFILE_ACADEMIQUE,
            primary_query="article academique",
            runtime_max_chars=8000,
        )

        should_fallback, reason = web_search_crawl_policy.should_fallback_from_primary(
            policy,
            {"status": "success", "markdown": "passage pertinent " * 20},
        )

        self.assertFalse(should_fallback)
        self.assertEqual(reason, "")


if __name__ == "__main__":
    unittest.main()
