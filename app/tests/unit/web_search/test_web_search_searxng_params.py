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
    def test_general_keeps_historical_params(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_GENERAL)

        self.assertEqual(params.kind, 'historical')
        self.assertEqual(params.policy, 'historical_baseline')
        self.assertEqual(params.as_request_params(), {'language': 'fr-FR', 'safesearch': '0'})

    def test_explicit_url_uses_historical_params_for_fallback_only(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_EXPLICIT_URL)

        self.assertEqual(params.kind, 'historical')
        self.assertEqual(params.categories, ())
        self.assertEqual(params.engines, ())
        self.assertEqual(params.time_range, '')

    def test_actualite_gets_bounded_recent_general_params(self) -> None:
        params = web_search_searxng_params.build_profile_params(web_search_profile.PROFILE_ACTUALITE)

        self.assertEqual(params.kind, 'profiled_actualite_year_general')
        self.assertEqual(params.policy, 'soft_broad_hints')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.engines, ())
        self.assertEqual(params.time_range, 'year')
        self.assertEqual(params.language, 'fr-FR')

    def test_technique_officielle_allows_multilingual_official_docs(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE
        )

        self.assertEqual(params.kind, 'profiled_technique_officielle_general_all')
        self.assertEqual(params.policy, 'soft_broad_hints')
        self.assertEqual(params.as_request_params()['categories'], 'general')
        self.assertEqual(params.language, 'all')
        self.assertNotIn('engines', params.as_request_params())

    def test_institutionnel_francais_stays_french_general(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS
        )

        self.assertEqual(params.kind, 'profiled_institutionnel_francais_general_fr')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.language, 'fr-FR')
        self.assertEqual(params.engines, ())

    def test_academique_philosophique_allows_multilingual_sources(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE
        )

        self.assertEqual(params.kind, 'profiled_academique_philosophique_general_all')
        self.assertEqual(params.categories, ('general',))
        self.assertEqual(params.language, 'all')

    def test_disabled_profile_params_are_historical(self) -> None:
        params = web_search_searxng_params.build_profile_params(
            web_search_profile.PROFILE_ACTUALITE,
            enabled=False,
        )

        self.assertEqual(params.kind, 'historical')
        self.assertEqual(params.as_request_params(), {'language': 'fr-FR', 'safesearch': '0'})


if __name__ == "__main__":
    unittest.main()
