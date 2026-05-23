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

from tools import web_search_profile, web_search_query_plan


class WebSearchQueryPlanTests(unittest.TestCase):
    def test_explicit_url_produces_no_secondary_queries(self) -> None:
        self.assertEqual(
            web_search_query_plan.build_specialized_queries(
                "Lis https://openrouter.ai/docs",
                "https://openrouter.ai/docs",
                web_search_profile.PROFILE_EXPLICIT_URL,
            ),
            [],
        )

    def test_actualite_produces_at_most_two_recent_official_queries(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "Quels changements récents sur la régulation IA Europe ?",
            "régulation IA Europe 2026 changements récents sources",
            web_search_profile.PROFILE_ACTUALITE,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any("actualite" in query.lower() or "AI Act" in query for query in queries))
        self.assertTrue(any("ec.europa.eu" in query for query in queries))

    def test_documentation_officielle_orients_to_source_first_docs(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "Dans la documentation OpenRouter actuelle, comment utiliser openrouter:web_search ?",
            "OpenRouter web_search paramètres coût documentation actuelle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any("documentation officielle" in query for query in queries))
        self.assertTrue(any("site:openrouter.ai/docs" in query for query in queries))

    def test_documentation_officielle_adobe_uses_adobe_source_first_domains(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "documentation officielle Adobe Photoshop",
            "Adobe Photoshop documentation officielle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any("site:helpx.adobe.com" in query for query in queries))
        self.assertTrue(any("site:developer.adobe.com" in query for query in queries))

    def test_documentation_officielle_unknown_authority_queries_ignore_command_words(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "peux-tu trouver la documentation officielle de AcmeDB vector search",
            "AcmeDB vector search documentation officielle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any(query.startswith("AcmeDB vector documentation officielle") for query in queries))
        self.assertFalse(any(query.lower().startswith(("peux", "trouve", "trouver", "cherche")) for query in queries))

    def test_administratif_francais_orients_to_french_institutions(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "Procédure officielle pour renouveler une carte nationale d'identité.",
            "renouveler carte nationale identité procédure officielle",
            web_search_profile.PROFILE_ADMINISTRATIF_FRANCAIS,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any("service-public.fr" in query for query in queries))
        self.assertTrue(any("ants.gouv.fr" in query for query in queries))

    def test_academique_orients_to_academic_sources(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "Sources solides sur la notion de trace chez Derrida.",
            "trace Derrida sources primaires commentaires académiques",
            web_search_profile.PROFILE_ACADEMIQUE,
        )

        self.assertLessEqual(len(queries), 2)
        self.assertTrue(any("OpenEdition" in query or "Cairn" in query for query in queries))
        self.assertTrue(any("Stanford Encyclopedia" in query for query in queries))

    def test_general_profile_stays_sober(self) -> None:
        self.assertEqual(
            web_search_query_plan.build_specialized_queries(
                "Cherche des idées de randonnée.",
                "idées randonnée Lyon",
                web_search_profile.PROFILE_GENERAL,
            ),
            [],
        )

    def test_query_deduplication_removes_primary_duplicate(self) -> None:
        queries = web_search_query_plan.build_specialized_queries(
            "OpenRouter openrouter:web_search documentation officielle",
            "OpenRouter openrouter:web_search documentation officielle",
            web_search_profile.PROFILE_DOCUMENTATION_OFFICIELLE,
        )

        self.assertNotIn("OpenRouter openrouter:web_search documentation officielle", queries)
        self.assertEqual(len(queries), len(set(queries)))


if __name__ == "__main__":
    unittest.main()
