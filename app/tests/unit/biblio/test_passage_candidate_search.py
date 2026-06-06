from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import passage_candidate_search as candidate_search
from biblio import query_planner


RAW_TITLE = "RAW TITLE MUST STAY INTERNAL"
RAW_TEXT = "RAW OCR TEXT MUST STAY INTERNAL"


class BiblioPassageCandidateSearchTests(unittest.TestCase):
    def test_accented_theme_search_finds_content_free_candidates(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient({"maïeutique": [_row("doc-1", page_no=4, para_no=26, rank=0.3)]})

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertEqual(observed["candidate_count"], 1)
        self.assertEqual(observed["candidates"][0]["doc_id_short"], "doc-1")
        self.assertEqual(observed["candidates"][0]["page_no"], 4)
        self.assertEqual(observed["candidates"][0]["para_no"], 26)
        self.assertEqual(observed["candidates"][0]["catalogue_rank_score"], 0.3)
        self.assertEqual(observed["candidates"][0]["first_result_index"], 1)
        self.assertIn("high_catalogue_rank_score", observed["candidates"][0]["reason_codes"])
        self.assertIn(("search", "maïeutique"), fake.calls)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_TEXT, encoded)
        self.assertNotIn("maïeutique", encoded)

    def test_live_like_float_catalogue_rank_is_preserved_and_scores_candidates(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient(
            {
                "maïeutique": [
                    _row("doc-top", page_no=4, para_no=26, rank=0.3),
                    _row("doc-middle", page_no=4, para_no=27, rank=0.2),
                    _row("doc-low", page_no=4, para_no=28, rank=0.1),
                ]
            }
        )

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertEqual(result.candidates[0].doc_id_short, "doc-top")
        self.assertEqual(result.candidates[0].catalogue_rank_score, 0.3)
        self.assertIsNotNone(result.candidates[0].catalogue_rank_score)
        self.assertGreater(result.candidates[0].score, result.candidates[1].score)
        self.assertEqual(observed["candidates"][0]["catalogue_rank_score"], 0.3)
        self.assertIn("catalogue_rank_score", observed["candidates"][0]["reason_codes"])
        self.assertIn("high_catalogue_rank_score", observed["candidates"][0]["reason_codes"])
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_TEXT, encoded)

    def test_result_retains_only_endpoint_observations_not_raw_search_payloads(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient({"maïeutique": [_row("doc-1", page_no=4, para_no=26, rank=0.3)]})

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = [item.to_observability() for item in result.endpoint_observations]
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_TEXT, encoded)
        self.assertNotIn("payload", encoded)

    def test_unaccented_theme_uses_accented_variant(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maieutique dans la bibliotheque")
        fake = _FakeSearchClient({"maïeutique": [_row("doc-1", page_no=4, para_no=26)]})

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertIn(("search", "maieutique"), fake.calls)
        self.assertIn(("search", "maïeutique"), fake.calls)

    def test_work_and_theme_boost_relevant_document(self) -> None:
        plan = query_planner.plan_biblio_query(
            "Peux-tu me trouver dans le Theetete le passage ou Socrate parle de la maieutique ?"
        )
        fake = _FakeSearchClient(
            {
                "maïeutique": [
                    _row("doc-work", page_no=5, para_no=26, rank=0.2),
                    _row("doc-other", page_no=5, para_no=26, rank=0.2),
                ],
                "Théétète": [_row("doc-work", page_no=4, para_no=20, rank=0.3)],
            }
        )

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = result.to_observability()

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertEqual(result.candidates[0].doc_id_short, "doc-work")
        self.assertGreater(result.candidates[0].score, result.candidates[1].score)
        self.assertIn("work_document_match", observed["candidates"][0]["reason_codes"])

    def test_duplicate_paragraph_hits_are_deduplicated_and_boosted(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maieutique dans la bibliotheque")
        rows = [_row("doc-1", page_no=4, para_no=26, paragraph_id=43430, rank=0.3)]
        fake = _FakeSearchClient({"maieutique": rows, "maïeutique": rows})

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = result.to_observability()

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertEqual(result.total_candidate_count, 1)
        self.assertEqual(result.candidates[0].hit_count, 2)
        self.assertIn("multi_variant_hit", observed["candidates"][0]["reason_codes"])

    def test_commentary_signal_demotes_candidate_without_claiming_primary_truth(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient(
            {
                "maïeutique": [
                    _row(
                        "doc-commentary",
                        page_no=4,
                        para_no=26,
                        rank=0.3,
                        document_role_signal="commentary",
                        document_role_signal_source="chapter_title",
                        document_role_signal_strength="weak",
                    ),
                    _row(
                        "doc-neutral",
                        page_no=4,
                        para_no=27,
                        rank=0.3,
                    ),
                ]
            }
        )

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, candidate_search.STATUS_CANDIDATES_FOUND)
        self.assertEqual(result.candidates[0].doc_id_short, "doc-neut")
        self.assertEqual(result.candidates[0].document_role_signal, "")
        self.assertEqual(result.candidates[1].document_role_signal, "commentary")
        self.assertIn("commentary_role_signal", observed["candidates"][1]["reason_codes"])
        self.assertEqual(observed["candidates"][1]["document_role_signal_source"], "chapter_title")
        self.assertEqual(observed["candidates"][1]["document_role_signal_strength"], "weak")
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_TEXT, encoded)

    def test_equal_top_scores_are_ambiguous(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient(
            {
                "maïeutique": [
                    _row("doc-a", page_no=4, para_no=26, rank=0.3),
                    _row("doc-b", page_no=4, para_no=26, rank=0.3),
                ]
            }
        )

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)

        self.assertEqual(result.status, candidate_search.STATUS_AMBIGUOUS)
        self.assertTrue(result.to_observability()["ambiguous"])
        self.assertEqual(result.to_observability()["candidate_count"], 2)

    def test_no_result_is_not_found(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeSearchClient({})

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)

        self.assertEqual(result.status, candidate_search.STATUS_NOT_FOUND)
        self.assertEqual(result.to_observability()["candidate_count"], 0)
        self.assertGreater(result.to_observability()["endpoint_count"], 0)

    def test_client_error_is_catalogue_unavailable(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FailingSearchClient()

        result = candidate_search.BiblioPassageCandidateSearcher(fake).search(plan)

        self.assertEqual(result.status, candidate_search.STATUS_CATALOGUE_UNAVAILABLE)
        self.assertEqual(result.reason_code, candidate_search.REASON_CATALOGUE_UNAVAILABLE)
        self.assertEqual(result.to_observability()["endpoint_count"], 1)


class _FakeSearchClient:
    def __init__(self, rows_by_query: dict[str, list[dict[str, object]]]) -> None:
        self.rows_by_query = rows_by_query
        self.calls: list[tuple[str, str]] = []

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q))
        rows = list(self.rows_by_query.get(q, []))[:limit]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={"count": len(rows), "results": rows},
            duration_ms=1,
            result_count=len(rows),
        )


class _FailingSearchClient:
    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        raise catalogue.CatalogueServiceUnavailable(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=503,
        )


def _row(
    document_id: str,
    *,
    page_no: int,
    para_no: int,
    paragraph_id: int | None = None,
    rank: object = 0.0,
    document_role_signal: str = "",
    document_role_signal_source: str = "",
    document_role_signal_strength: str = "",
) -> dict[str, object]:
    row: dict[str, object] = {
        "document_id": document_id,
        "page_no": page_no,
        "para_no": para_no,
        "rank": rank,
        "title": RAW_TITLE,
        "text": RAW_TEXT,
    }
    if paragraph_id is not None:
        row["paragraph_id"] = paragraph_id
    if document_role_signal:
        row["document_role_signal"] = document_role_signal
    if document_role_signal_source:
        row["document_role_signal_source"] = document_role_signal_source
    if document_role_signal_strength:
        row["document_role_signal_strength"] = document_role_signal_strength
    return row


if __name__ == "__main__":
    unittest.main()
