from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import query_planner


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

    def test_work_title_without_corpus_can_still_be_planned(self) -> None:
        plan = query_planner.plan_biblio_query("Théétète 126b à 128a")

        self.assertTrue(plan.should_consult)
        self.assertEqual(plan.intent, query_planner.INTENT_EXTRACT_RANGE)
        self.assertEqual(plan.work_title, "Théétète")
        self.assertEqual(plan.document_title, "")

    def test_vague_book_request_is_not_bibliographic_signal(self) -> None:
        plan = query_planner.plan_biblio_query("Je cherche un livre sympa.")

        self.assertFalse(plan.should_consult)
        self.assertEqual(plan.reason_code, query_planner.REASON_NO_SIGNAL)

    def test_observability_does_not_expose_raw_query_terms(self) -> None:
        raw = "Théétète SECRET RAW"
        plan = query_planner.plan_biblio_query(f"cherche {raw}")
        observed = plan.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertTrue(plan.should_consult)
        self.assertNotIn(raw, encoded)
        self.assertIn("hash", encoded)


if __name__ == "__main__":
    unittest.main()
