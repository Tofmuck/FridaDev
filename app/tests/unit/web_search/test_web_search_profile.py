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

from tools import web_search_profile


class WebSearchProfileTests(unittest.TestCase):
    def test_explicit_url_profile_wins(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile(
                "Lis cette page officielle: https://openrouter.ai/docs/guides/features/server-tools/web-fetch.",
            ),
            "explicit_url",
        )

    def test_actualite_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile(
                "Quelles sont les dernières infos aujourd'hui sur la régulation IA en Europe ?",
            ),
            "actualite",
        )

    def test_documentation_officielle_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile(
                "Dans la documentation officielle OpenRouter API, comment utiliser openrouter:web_search ?",
            ),
            "documentation_officielle",
        )

    def test_documentation_officielle_generic_still_profiles_without_vendor(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("Trouve la documentation officielle."),
            "documentation_officielle",
        )

    def test_administratif_francais_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile(
                "Quelle est la procédure officielle service public pour renouveler une carte nationale d'identité ?",
            ),
            "administratif_francais",
        )

    def test_education_institutionnelle_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("eduscol programme philosophie terminale"),
            "administratif_francais",
        )

    def test_academique_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile(
                "Trouve des sources universitaires sur la notion de trace chez Derrida.",
            ),
            "academique",
        )

    def test_academique_large_sciences_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("Article scientifique CRISPR PubMed arXiv"),
            "academique",
        )

    def test_general_fallback_profile(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("Cherche des idées de randonnée autour de Lyon."),
            "general_divers",
        )

    def test_qna_technical_request_does_not_become_official_docs(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("Trouve une réponse StackOverflow sur cette erreur Python."),
            "general_divers",
        )

    def test_ambiguous_jaguar_stays_general_divers(self) -> None:
        self.assertEqual(
            web_search_profile.classify_search_profile("Jaguar vitesse comparaison habitat modèle électrique"),
            "general_divers",
        )


if __name__ == "__main__":
    unittest.main()
