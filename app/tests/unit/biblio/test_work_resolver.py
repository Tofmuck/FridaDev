from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import query_planner
from biblio import work_resolver


class BiblioWorkResolverTests(unittest.TestCase):
    def test_search_anchor_turns_internal_work_into_locator_hint(self) -> None:
        plan = query_planner.plan_biblio_query("un extrait du Théétète de Platon, 126b à 128a")
        fake = _FakeClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertIsNotNone(result.resolve_request)
        self.assertEqual(result.resolve_request.title, "Platon")
        self.assertEqual(result.resolve_request.document_title, "Platon")
        self.assertEqual(result.resolve_request.work_title, "Théétète")
        self.assertEqual(result.resolve_request.locator_anchor_page, 131)
        self.assertEqual(result.resolve_request.locator, "126b")
        self.assertEqual(result.resolve_request.locator_end, "128a")
        self.assertEqual([call[0] for call in fake.calls], ["catalog", "chapters", "search"])
        self.assertNotIn("Théétète", encoded)
        self.assertNotIn("Platon", encoded)

    def test_work_resolution_retains_only_endpoint_observations_not_raw_payloads(self) -> None:
        plan = query_planner.plan_biblio_query("un extrait du Théétète de Platon, 126b à 128a")
        fake = _FakeClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)
        observed = [item.to_observability() for item in result.endpoint_observations]
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertTrue(result.endpoint_observations)
        self.assertFalse(hasattr(result, "client_responses"))
        self.assertFalse(any(hasattr(item, "payload") for item in result.endpoint_observations))
        self.assertNotIn("RAW TITLE MUST STAY INTERNAL", encoded)
        self.assertNotIn("RAW OCR MUST STAY INTERNAL", encoded)
        self.assertNotIn("payload", encoded)

    def test_search_anchor_uses_work_alias_variants(self) -> None:
        plan = query_planner.BiblioQueryPlan(
            should_consult=True,
            intent=query_planner.INTENT_EXTRACT_PASSAGE,
            reason_code=query_planner.REASON_PASSAGE_REQUESTED,
            query_kind=query_planner.INTENT_EXTRACT_PASSAGE,
            work_title="Theetete",
            locator="126b",
            work_title_variants=("Theetete", "Théétète"),
        )
        fake = _AccentSensitiveFakeClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)
        encoded = json.dumps(result.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertIsNotNone(result.resolve_request)
        self.assertEqual(result.resolve_request.document_id, "doc-1234")
        self.assertEqual(result.resolve_request.work_title, "Theetete")
        self.assertEqual(result.resolve_request.locator, "126b")
        self.assertEqual([call[1] for call in fake.calls], ["Theetete", "Théétète"])
        self.assertNotIn("Théétète", encoded)

    def test_bare_work_request_keeps_work_and_document_signals_separate(self) -> None:
        plan = query_planner.plan_biblio_query("Trouve-moi le Theetete de Platon.")
        fake = _FakeClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertEqual(result.documentary_target, "work_in_document")
        self.assertTrue(result.work_hint_present)
        self.assertTrue(result.document_hint_present)
        self.assertIsNotNone(result.resolve_request)
        self.assertEqual(result.resolve_request.title, "Platon")
        self.assertEqual(result.resolve_request.document_title, "Platon")
        self.assertEqual(result.resolve_request.work_title, "Théétète")
        self.assertEqual([call[0] for call in fake.calls], ["catalog", "chapters"])

    def test_unique_document_uses_chapters_before_paragraph_search_for_internal_work(self) -> None:
        plan = query_planner.plan_biblio_query("Trouve-moi le Theetete de Platon.")
        fake = _FakeClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)
        encoded = json.dumps(result.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertIsNotNone(result.resolve_request)
        assert result.resolve_request is not None
        self.assertEqual(result.resolve_request.document_id, "doc-1234")
        self.assertEqual(result.resolve_request.document_title, "Platon")
        self.assertEqual(result.resolve_request.work_title, "Théétète")
        self.assertEqual([call[0] for call in fake.calls], ["catalog", "chapters"])
        self.assertNotIn("RAW CHAPTER TITLE MUST STAY INTERNAL", encoded)

    def test_short_work_title_does_not_match_chapter_by_accidental_substring(self) -> None:
        plan = query_planner.BiblioQueryPlan(
            should_consult=True,
            intent=query_planner.INTENT_RESOLVE_WORK,
            reason_code=query_planner.REASON_WORK_REQUESTED,
            query_kind=query_planner.INTENT_RESOLVE_WORK,
            document_title="Platon",
            author="Platon",
            work_title="Ion",
        )
        fake = _ShortTitleFalsePositiveClient()

        result = work_resolver.BiblioWorkResolver(fake).resolve(plan)

        self.assertEqual(result.status, work_resolver.STATUS_RESOLVED)
        self.assertIsNotNone(result.resolve_request)
        assert result.resolve_request is not None
        self.assertEqual(result.resolve_request.document_id, "doc-1234")
        self.assertEqual(result.resolve_request.work_title, "Ion")
        self.assertEqual([call[0] for call in fake.calls], ["catalog", "chapters", "search"])
        self.assertEqual([call[1] for call in fake.calls if call[0] == "search"], ["Ion"])


class _FakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CATALOG,
            status_code=200,
            payload={"total": 1, "items": [{"id": "doc-1234", "title": q or ""}]},
            duration_ms=1,
            result_count=1,
        )

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={
                "count": 1,
                "results": [
                    {
                        "document_id": "doc-1234",
                        "title": "RAW TITLE MUST STAY INTERNAL",
                        "page_no": 131,
                        "para_no": 230,
                        "text": "RAW OCR MUST STAY INTERNAL",
                    }
                ],
            },
            duration_ms=1,
            result_count=1,
        )

    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document_id": doc_id,
                "total": 2,
                "chapters": [
                    {"chapter_no": 1, "title": "RAW CHAPTER TITLE MUST STAY INTERNAL", "unit_no": 1, "source": "toc"},
                    {"chapter_no": 2, "title": "Théétète", "unit_no": 2, "source": "toc"},
                ],
            },
            duration_ms=1,
            result_count=2,
        )


class _AccentSensitiveFakeClient:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        rows = []
        if q == "Théétète":
            rows = [
                {
                    "document_id": "doc-1234",
                    "title": "RAW TITLE MUST STAY INTERNAL",
                    "page_no": 131,
                    "para_no": 230,
                    "text": "RAW OCR MUST STAY INTERNAL",
                }
            ]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={"count": len(rows), "results": rows},
            duration_ms=1,
            result_count=len(rows),
        )


class _ShortTitleFalsePositiveClient(_FakeClient):
    def chapters(self, doc_id: str, *, limit: int = 500, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("chapters", doc_id, limit, offset))
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CHAPTERS,
            status_code=200,
            payload={
                "document_id": doc_id,
                "total": 1,
                "chapters": [
                    {"chapter_no": 1, "title": "Introduction", "unit_no": 1, "source": "toc"},
                ],
            },
            duration_ms=1,
            result_count=1,
        )


if __name__ == "__main__":
    unittest.main()
