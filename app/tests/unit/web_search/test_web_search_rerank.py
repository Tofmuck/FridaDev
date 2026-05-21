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

from tools import web_search_profile, web_search_rerank


class WebSearchRerankTests(unittest.TestCase):
    def test_explicit_url_is_not_reranked(self) -> None:
        results = [
            {"title": "A", "url": "https://a.example", "content": "a"},
            {"title": "B", "url": "https://b.example", "content": "b"},
        ]

        reranked, observability = web_search_rerank.rerank_results(
            results,
            user_msg="Lis https://a.example",
            primary_query="https://a.example",
            search_profile=web_search_profile.PROFILE_EXPLICIT_URL,
            max_results=5,
            enabled=True,
        )

        self.assertEqual([item["url"] for item in reranked], ["https://a.example", "https://b.example"])
        self.assertFalse(observability["rerank_applied"])

    def test_institutionnel_francais_downranks_conjugators_without_dropping_them(self) -> None:
        results = [
            {
                "title": "Conjugaison renouveler",
                "url": "https://leconjugueur.lefigaro.fr/conjugaison/verbe/renouveler.html",
                "content": "conjugaison",
            },
            {
                "title": "Renouveler - Bescherelle",
                "url": "https://bescherelle.com/conjugaison/renouveler",
                "content": "conjugaison",
            },
            {
                "title": "Carte d'identite",
                "url": "https://www.service-public.fr/particuliers/vosdroits/N358",
                "content": "procedure carte identite",
            },
            {
                "title": "ANTS identite",
                "url": "https://ants.gouv.fr/demarches/identite",
                "content": "renouvellement identite",
            },
        ]

        reranked, observability = web_search_rerank.rerank_results(
            results,
            user_msg="procedure officielle pour renouveler une carte nationale d'identite",
            primary_query="renouveler carte nationale identite procedure officielle",
            search_profile=web_search_profile.PROFILE_INSTITUTIONNEL_FRANCAIS,
            max_results=4,
            enabled=True,
        )

        urls = [item["url"] for item in reranked]
        self.assertEqual(urls[:2], [
            "https://www.service-public.fr/particuliers/vosdroits/N358",
            "https://ants.gouv.fr/demarches/identite",
        ])
        self.assertIn("https://leconjugueur.lefigaro.fr/conjugaison/verbe/renouveler.html", urls)
        self.assertIn("https://bescherelle.com/conjugaison/renouveler", urls)
        self.assertIn("conjugator_soft_downrank", observability["rerank_reason_counts"])
        self.assertTrue(observability["rerank_applied"])

    def test_technique_officielle_promotes_official_documentation(self) -> None:
        reranked, observability = web_search_rerank.rerank_results(
            [
                {
                    "title": "OpenRouter Tutorial",
                    "url": "https://www.datacamp.com/tutorial/openrouter",
                    "content": "tutorial",
                },
                {
                    "title": "OpenRouter Documentation",
                    "url": "https://openrouter.ai/docs/api-reference/overview",
                    "content": "official API documentation",
                },
            ],
            user_msg="documentation officielle OpenRouter web_search",
            primary_query="OpenRouter web_search documentation officielle",
            search_profile=web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE,
            max_results=5,
            enabled=True,
        )

        self.assertEqual(reranked[0]["url"], "https://openrouter.ai/docs/api-reference/overview")
        self.assertIn("profile_official_domain_soft_bonus", reranked[0]["rerank_reason_codes"])
        self.assertIn("technical_documentation_soft_bonus", reranked[0]["rerank_reason_codes"])
        self.assertEqual(observability["rerank_promoted_count"], 1)

    def test_actualite_promotes_eu_official_source_without_wikipedia_ban(self) -> None:
        reranked, observability = web_search_rerank.rerank_results(
            [
                {
                    "title": "Regulation",
                    "url": "https://fr.wikipedia.org/wiki/R%C3%A9gulation",
                    "content": "encyclopedie generale",
                },
                {
                    "title": "regulation - Wiktionnaire",
                    "url": "https://fr.wiktionary.org/wiki/r%C3%A9gulation",
                    "content": "definition",
                },
                {
                    "title": "Artificial intelligence - European Commission",
                    "url": "https://digital-strategy.ec.europa.eu/en/policies/artificial-intelligence",
                    "content": "AI Act 2026 recent European Commission",
                },
            ],
            user_msg="changements recents regulation IA Europe 2026",
            primary_query="regulation IA Europe 2026 changements recents sources",
            search_profile=web_search_profile.PROFILE_ACTUALITE,
            max_results=5,
            enabled=True,
        )

        urls = [item["url"] for item in reranked]
        self.assertEqual(urls[0], "https://digital-strategy.ec.europa.eu/en/policies/artificial-intelligence")
        self.assertIn("https://fr.wikipedia.org/wiki/R%C3%A9gulation", urls)
        self.assertIn("generic_encyclopedia_soft_downrank", observability["rerank_reason_counts"])
        self.assertIn("dictionary_soft_downrank", observability["rerank_reason_counts"])

    def test_academique_philosophique_promotes_academic_source_and_downranks_homonym(self) -> None:
        reranked, observability = web_search_rerank.rerank_results(
            [
                {
                    "title": "Trace - Larousse",
                    "url": "https://www.larousse.fr/dictionnaires/francais/trace/78961",
                    "content": "definition",
                },
                {
                    "title": "Trace Colmar",
                    "url": "https://www.trace-colmar.fr/",
                    "content": "agenda culturel",
                },
                {
                    "title": "Derrida et la trace",
                    "url": "https://journals.openedition.org/noesis/1693",
                    "content": "philosophie Derrida trace",
                },
            ],
            user_msg="sources academiques sur la notion de trace chez Derrida",
            primary_query="trace Derrida sources primaires commentaires academiques",
            search_profile=web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE,
            max_results=5,
            enabled=True,
        )

        self.assertEqual(reranked[0]["url"], "https://journals.openedition.org/noesis/1693")
        self.assertIn("profile_academic_domain_soft_bonus", reranked[0]["rerank_reason_codes"])
        self.assertIn("homonym_soft_downrank", observability["rerank_reason_counts"])
        self.assertEqual(len(reranked), 3)

    def test_domain_diversity_keeps_plausible_off_domain_source(self) -> None:
        results = [
            {"title": "Doc A", "url": "https://openrouter.ai/docs/a", "content": "official docs api"},
            {"title": "Doc B", "url": "https://openrouter.ai/docs/b", "content": "official docs api"},
            {"title": "Doc C", "url": "https://openrouter.ai/docs/c", "content": "official docs api"},
            {"title": "GitHub example", "url": "https://github.com/openrouter/examples", "content": "api example"},
        ]

        reranked, observability = web_search_rerank.rerank_results(
            results,
            user_msg="OpenRouter documentation API exemples",
            primary_query="OpenRouter documentation API exemples",
            search_profile=web_search_profile.PROFILE_TECHNIQUE_OFFICIELLE,
            max_results=4,
            enabled=True,
        )

        self.assertIn("github.com", [item["source_domain"] if "source_domain" in item else "" for item in reranked] + [
            item["url"].split("/")[2] for item in reranked
        ])
        self.assertEqual(len(reranked), 4)
        self.assertTrue(observability["rerank_applied"])
        self.assertIn("domain_concentration_soft_downrank", observability["rerank_reason_counts"])

    def test_reason_codes_are_fixed_codes_not_raw_content(self) -> None:
        secret_snippet = "snippet ultra sensible"
        reranked, observability = web_search_rerank.rerank_results(
            [
                {"title": "Trace - Larousse", "url": "https://www.larousse.fr/trace", "content": secret_snippet},
                {"title": "Derrida", "url": "https://journals.openedition.org/noesis/1693", "content": "trace Derrida"},
            ],
            user_msg="Derrida trace",
            primary_query="Derrida trace",
            search_profile=web_search_profile.PROFILE_ACADEMIQUE_PHILOSOPHIQUE,
            max_results=5,
            enabled=True,
        )

        reason_blob = str(observability["rerank_reason_counts"]) + str(reranked[0]["rerank_reason_codes"])
        self.assertNotIn(secret_snippet, reason_blob)
        self.assertIn("profile_academic_domain_soft_bonus", reason_blob)


if __name__ == "__main__":
    unittest.main()
