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

from tools import web_search_profile, web_search_searxng_params


class WebSearchSearxngProfileParamsTests(unittest.TestCase):
    def test_general_compat_symbol_maps_to_governed_general_divers_when_profiled(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_GENERAL)

        self.assertEqual(params.kind, 'governed_general_divers_general')
        self.assertEqual(params.policy, 'governed_engine_basket_v0')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.engines, ('bing', 'brave', 'mojeek'))

    def test_explicit_url_uses_historical_params_for_fallback_only(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_EXPLICIT_URL)

        self.assertEqual(params.kind, 'historical')
        self.assertEqual(params.categories, ())
        self.assertEqual(params.engines, ())
        self.assertEqual(params.time_range, '')

    def test_actualite_gets_bounded_recent_general_params(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_ACTUALITE)

        self.assertEqual(params.kind, 'governed_actualite_news_general')
        self.assertEqual(params.policy, 'governed_engine_basket_v0')
        self.assertEqual(params.categories, ('general', 'news'))
        self.assertEqual(params.engines, ('bing news', 'reuters', 'bing', 'duckduckgo news'))
        self.assertEqual(params.time_range, 'year')
        self.assertEqual(params.language, 'fr-FR')
        self.assertIn('reuters_not_single_source', params.reason_codes)

    def test_documentation_officielle_allows_multilingual_official_docs(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE
        )

        self.assertEqual(params.kind, 'governed_documentation_officielle_it_general')
        self.assertEqual(params.policy, 'governed_engine_basket_v0')
        self.assertEqual(params.as_request_params()['categories'], 'general,it')
        self.assertEqual(
            params.engines,
            ('microsoft learn', 'mdn', 'docker hub', 'bing', 'brave', 'mojeek'),
        )
        self.assertEqual(params.language, 'all')
        self.assertEqual(
            params.as_request_params()['engines'],
            'microsoft learn,mdn,docker hub,bing,brave,mojeek',
        )
        self.assertIn('source_first_authority_alignment_required_for_strong_bonus', params.reason_codes)

    def test_administratif_francais_stays_french_general(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS
        )

        self.assertEqual(params.kind, 'governed_administratif_francais_general')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.language, 'fr-FR')
        self.assertEqual(params.engines, ('bing', 'brave'))
        self.assertIn('bing_brave_general_support_site_operator', params.reason_codes)

    def test_academique_allows_multilingual_sources(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_ACADEMIQUE
        )

        self.assertEqual(params.kind, 'governed_academique_science_general')
        self.assertEqual(params.categories, ('general', 'science'))
        self.assertEqual(params.engines, ('arxiv', 'openairepublications', 'pubmed', 'bing', 'brave'))
        self.assertEqual(params.language, 'all')
        self.assertIn('google_scholar_and_semantic_scholar_avoided', params.reason_codes)

    def test_general_divers_uses_plural_general_basket_when_profiled(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_GENERAL)

        self.assertEqual(params.kind, 'governed_general_divers_general')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.engines, ('bing', 'brave', 'mojeek'))
        self.assertEqual(params.language, 'fr-FR')
        self.assertIn('mojeek_secondary_candidate', params.reason_codes)

    def test_observability_exposes_governed_reason_codes_without_requesting_unknown_fields(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE
        )

        request_params = params.as_request_params()
        observability = params.as_observability_fields()

        self.assertNotIn('searxng_params_reason_codes', request_params)
        self.assertEqual(observability['searxng_profile_params_policy'], 'governed_engine_basket_v0')
        self.assertIn('engines', observability['searxng_hard_parameters'])
        self.assertIn('qa_not_primary_authority', observability['searxng_params_reason_codes'])
        self.assertEqual(
            observability['searxng_soft_signal_policy'],
            'source_first_and_rerank_remain_soft_no_drop',
        )

    def test_disabled_profile_params_are_historical(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_ACTUALITE,
            enabled=False,
        )

        self.assertEqual(params.kind, 'historical')
        self.assertEqual(params.as_request_params(), {'language': 'fr-FR', 'safesearch': '0'})


if __name__ == "__main__":
    unittest.main()
