from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import query_normalizer, query_planner


class BiblioQueryPlannerTests(unittest.TestCase):
    def test_catalogue_list_request_is_planned(self) -> None:
        for message in (
            "Tu peux chercher et voir les premiers ouvrages ?",
            "cherche dans la bibliothèque",
        ):
            with self.subTest(message=message):
                plan = query_planner.plan_biblio_query(message)

                self.assertTrue(plan.should_consult)
                self.assertEqual(plan.intent, query_planner.INTENT_LIST_CATALOG)
                self.assertEqual(plan.query_kind, query_planner.INTENT_LIST_CATALOG)

    def test_natural_theetete_range_is_planned_as_internal_work(self) -> None:
        plan = query_planner.plan_biblio_query(
            "Bon, vas-y, tu me balances ici un extrait du Théétète de Platon. On va dire 126b à 128a."
        )

        self.assertTrue(plan.should_consult)
        self.assertEqual(plan.intent, query_planner.INTENT_EXTRACT_RANGE)
        self.assertEqual(plan.work_title, "Théétète")
        self.assertEqual(plan.document_title, "Platon")
        self.assertEqual(plan.locator, "126b")
        self.assertEqual(plan.locator_end, "128a")
        self.assertIn("Theetete", plan.work_title_variants)
        self.assertIn("Theaitetos", plan.work_title_variants)
        self.assertIn("Theaetetus", plan.work_title_variants)

    def test_work_title_without_corpus_can_still_be_planned(self) -> None:
        plan = query_planner.plan_biblio_query("Théétète 126b à 128a")

        self.assertTrue(plan.should_consult)
        self.assertEqual(plan.intent, query_planner.INTENT_EXTRACT_RANGE)
        self.assertEqual(plan.work_title, "Théétète")
        self.assertEqual(plan.document_title, "")

    def test_unaccented_work_alias_range_is_normalized(self) -> None:
        for alias in ("Theetete", "Theaitetos", "Theaetetus"):
            with self.subTest(alias=alias):
                plan = query_planner.plan_biblio_query(f"{alias} 126b à 128a")

                self.assertTrue(plan.should_consult)
                self.assertEqual(plan.intent, query_planner.INTENT_EXTRACT_RANGE)
                self.assertEqual(plan.work_title, "Théétète")
                self.assertIn("Théétète", plan.work_title_variants)
                self.assertEqual(plan.locator, "126b")
                self.assertEqual(plan.locator_end, "128a")

    def test_short_range_suffix_keeps_internal_work_and_corpus_separate(self) -> None:
        plan = query_planner.plan_biblio_query("126b à 128a du Theetete de Platon")

        self.assertTrue(plan.should_consult)
        self.assertEqual(plan.intent, query_planner.INTENT_EXTRACT_RANGE)
        self.assertEqual(plan.work_title, "Théétète")
        self.assertEqual(plan.document_title, "Platon")
        self.assertEqual(plan.locator, "126b")
        self.assertEqual(plan.locator_end, "128a")

    def test_thematic_passage_request_separates_work_and_theme(self) -> None:
        cases = (
            "Trouve dans le Théétète le passage où Socrate parle de la maïeutique",
            "Trouve dans le Theetete le passage ou Socrate parle de la maieutique",
            "Peux-tu me trouver dans le Théétète le passage où Socrate parle de la maïeutique ?",
            "Peux-tu me trouver dans le Theetete le passage ou Socrate parle de la maieutique ?",
            "Tu peux me chercher dans le Théétète le passage où Socrate parle de la maïeutique ?",
        )

        for message in cases:
            with self.subTest(message=message):
                plan = query_planner.plan_biblio_query(message)

                self.assertTrue(plan.should_consult)
                self.assertEqual(plan.intent, query_planner.INTENT_SEARCH_CATALOG)
                self.assertEqual(plan.work_title, "Théétète")
                self.assertIn("Socrate", plan.theme_query)
                self.assertIn("maïeutique", plan.theme_query_variants)
                self.assertIn("maieutique", plan.theme_query_variants)
                self.assertIn("Théétète", plan.work_title_variants)

    def test_inverted_thematic_passage_request_separates_theme_and_work(self) -> None:
        cases = (
            ("Trouve le passage sur la maieutique dans le Theetete", "maieutique"),
            ("Cherche le passage sur la maïeutique dans le Théétète", "maïeutique"),
        )

        for message, expected_theme_variant in cases:
            with self.subTest(message=message):
                plan = query_planner.plan_biblio_query(message)

                self.assertTrue(plan.should_consult)
                self.assertEqual(plan.intent, query_planner.INTENT_SEARCH_CATALOG)
                self.assertEqual(plan.work_title, "Théétète")
                self.assertEqual(plan.theme_query, expected_theme_variant)
                self.assertIn("maïeutique", plan.theme_query_variants)
                self.assertIn("maieutique", plan.theme_query_variants)

    def test_vague_book_request_is_not_bibliographic_signal(self) -> None:
        plan = query_planner.plan_biblio_query("Je cherche un livre sympa.")

        self.assertFalse(plan.should_consult)
        self.assertEqual(plan.reason_code, query_planner.REASON_NO_SIGNAL)

    def test_false_titles_remain_unusable(self) -> None:
        fragments = ("le", "la", "l", "bibliotheque", "bibliothèque", "catalogue", "biblio", "ouvrage", "livre")

        for fragment in fragments:
            with self.subTest(fragment=fragment):
                plan = query_planner.plan_biblio_query(f"Trouve 126b chez {fragment}.")

                self.assertFalse(plan.should_consult)
                self.assertEqual(plan.reason_code, query_planner.REASON_CLARIFY_DOCUMENT_REQUIRED)

    def test_query_normalizer_builds_alias_accent_ligature_and_dictation_variants(self) -> None:
        self.assertEqual(query_normalizer.fold_text("œuvres complètes"), "oeuvres completes")
        self.assertEqual(query_normalizer.fold_text("oeuvres completes"), "oeuvres completes")
        self.assertIn("Théétète", query_normalizer.query_variants("Theetete"))
        self.assertIn("Théétète", query_normalizer.query_variants("Theaitetos"))
        self.assertIn("Théétète", query_normalizer.query_variants("Theaetetus"))
        self.assertIn(
            "Socrate parle de la maïeutique",
            query_normalizer.query_variants("Socrate parle de la maieutique"),
        )
        self.assertIn("maïeutique", query_normalizer.query_variants("maieutique"))
        self.assertIn("sage-femme", query_normalizer.query_variants("sage femme"))
        self.assertIn("sage femme", query_normalizer.query_variants("sage-femme"))
        oral = query_planner.plan_biblio_query("126b de l Apologie")
        typed = query_planner.plan_biblio_query("126b de l’Apologie")
        self.assertEqual(oral.document_title or oral.work_title, "Apologie")
        self.assertEqual(typed.document_title or typed.work_title, "Apologie")

    def test_observability_does_not_expose_raw_query_terms(self) -> None:
        raw = "Théétète SECRET RAW"
        plan = query_planner.plan_biblio_query(f"cherche {raw}")
        observed = plan.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertTrue(plan.should_consult)
        self.assertNotIn(raw, encoded)
        self.assertNotIn("SECRET", encoded)
        self.assertNotIn("Théétète", encoded)
        self.assertIn("hash", encoded)


if __name__ == "__main__":
    unittest.main()
