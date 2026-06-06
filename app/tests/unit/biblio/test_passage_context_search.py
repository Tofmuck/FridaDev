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
from biblio import passage_context_search as context_search
from biblio import query_planner


RAW_PASSAGE = "RAW CONTEXT PASSAGE MUST STAY INTERNAL"
RAW_TITLE = "RAW TITLE MUST STAY INTERNAL"
RAW_QUERY = "RAW QUERY MUST STAY INTERNAL"


class BiblioPassageContextSearchTests(unittest.TestCase):
    def test_candidates_found_requires_context_before_extraction(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(context_errors={("page_para", "doc-1", 4, 26): catalogue.CatalogueNotFound(doc_id="doc-1")})

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_NOT_FOUND)
        self.assertEqual(result.passage, "")
        self.assertEqual(fake.calls, [("context", "doc-1", None, 4, 26, 0, context_search.DEFAULT_CONTEXT_WINDOW_CHARS)])

    def test_top_n_context_candidates_are_bounded(self) -> None:
        candidate_result = _candidate_result(
            [
                _candidate("doc-1", page_no=4, para_no=26, score=30),
                _candidate("doc-2", page_no=5, para_no=27, score=29),
                _candidate("doc-3", page_no=6, para_no=28, score=28),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", "A"),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", "B"),
                ("page_para", "doc-3", 6, 28): _context_payload("doc-3", "C"),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(
            _request(candidate_result, max_context_candidates=2)
        )

        self.assertEqual(result.status, context_search.STATUS_AMBIGUOUS)
        self.assertEqual(result.to_observability()["context_call_count"], 2)
        self.assertEqual([call[1] for call in fake.calls], ["doc-1", "doc-2"])

    def test_prefers_paragraph_id_when_available(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26, paragraph_id=99)])
        fake = _FakeContextClient(
            context_payloads={("paragraph_id", "doc-1", 99): _context_payload("doc-1", RAW_PASSAGE, paragraph_id=99)}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertEqual(fake.calls[-1], ("context", "doc-1", 99, None, None, 0, context_search.DEFAULT_CONTEXT_WINDOW_CHARS))

    def test_falls_back_to_page_and_paragraph(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-1", RAW_PASSAGE)}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertEqual(fake.calls[-1], ("context", "doc-1", None, 4, 26, 0, context_search.DEFAULT_CONTEXT_WINDOW_CHARS))

    def test_coherent_context_extracts_bounded_internal_passage(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-1", RAW_PASSAGE)}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertEqual(result.passage, RAW_PASSAGE)
        self.assertTrue(observed["passage_present"])
        self.assertEqual(observed["passage_chars"], len(RAW_PASSAGE))
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)

    def test_dominant_candidate_becomes_extracted_with_selection_reasons(self) -> None:
        selected_passage = _long_passage("SELECTED")
        rejected_passage = _long_passage("REJECTED")
        candidate_result = _candidate_result(
            [
                _candidate(
                    "doc-1",
                    page_no=4,
                    para_no=26,
                    score=42,
                    reason_codes=("exact_theme_variant", "theme_hit", "work_document_match"),
                ),
                _candidate("doc-2", page_no=5, para_no=27, score=25),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", selected_passage),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", rejected_passage),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        observed = result.to_observability()
        encoded = json.dumps(observed, ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertEqual(result.passage, selected_passage)
        self.assertEqual(observed["selected_count"], 1)
        self.assertGreaterEqual(observed["score_gap"], 8)
        self.assertIn("work_document_match", observed["selection_reason_codes"])
        self.assertIn("exact_theme_variant", observed["selection_reason_codes"])
        self.assertEqual(sum(1 for decision in result.decisions if decision.selected), 1)
        self.assertNotIn(selected_passage, encoded)
        self.assertNotIn(rejected_passage, encoded)

    def test_close_candidates_remain_ambiguous(self) -> None:
        candidate_result = _candidate_result(
            [
                _candidate(
                    "doc-1",
                    page_no=4,
                    para_no=26,
                    score=42,
                    reason_codes=("theme_hit", "work_document_match"),
                ),
                _candidate(
                    "doc-2",
                    page_no=5,
                    para_no=27,
                    score=39,
                    reason_codes=("theme_hit", "work_document_match"),
                ),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", _long_passage("A")),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", _long_passage("B")),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        observed = result.to_observability()

        self.assertEqual(result.status, context_search.STATUS_AMBIGUOUS)
        self.assertEqual(result.passage, "")
        self.assertEqual(observed["selected_count"], 0)
        self.assertTrue(observed["selection"]["ambiguous"])
        self.assertLess(observed["score_gap"], 8)

    def test_catalogue_rank_alone_does_not_select(self) -> None:
        candidate_result = _candidate_result(
            [
                _candidate(
                    "doc-1",
                    page_no=4,
                    para_no=26,
                    score=48,
                    reason_codes=("catalogue_rank_score", "high_catalogue_rank_score", "search_hit"),
                    catalogue_rank_score=0.9,
                ),
                _candidate("doc-2", page_no=5, para_no=27, score=25),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", _long_passage("A")),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", _long_passage("B")),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        observed = result.to_observability()

        self.assertEqual(result.status, context_search.STATUS_AMBIGUOUS)
        self.assertEqual(result.passage, "")
        self.assertEqual(observed["selected_count"], 0)
        self.assertEqual(observed["selection"]["reason_code"], "selection_evidence_insufficient")

    def test_work_theme_and_candidate_score_can_disambiguate(self) -> None:
        candidate_result = _candidate_result(
            [
                _candidate(
                    "doc-1",
                    page_no=4,
                    para_no=26,
                    score=36,
                    reason_codes=("theme_hit", "work_document_match"),
                ),
                _candidate("doc-2", page_no=5, para_no=27, score=25),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", _long_passage("A")),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", _long_passage("B")),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        observed = result.to_observability()

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertEqual(observed["selected_count"], 1)
        self.assertIn("work_document_match", observed["selection_reason_codes"])

    def test_context_without_document_id_is_incoherent(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): {"excerpt": RAW_PASSAGE, "title": RAW_TITLE}}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, context_search.REASON_CONTEXT_INCOHERENT)
        self.assertEqual(result.passage, "")

    def test_context_with_divergent_document_id_is_incoherent(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-2", RAW_PASSAGE)}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.passage, "")

    def test_multiple_plausible_contexts_are_ambiguous_without_raw_passages(self) -> None:
        candidate_result = _candidate_result(
            [
                _candidate("doc-1", page_no=4, para_no=26),
                _candidate("doc-2", page_no=5, para_no=27),
            ]
        )
        fake = _FakeContextClient(
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", "RAW PASSAGE A"),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", "RAW PASSAGE B"),
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))
        encoded = json.dumps(result.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, context_search.STATUS_AMBIGUOUS)
        self.assertEqual(result.passage, "")
        self.assertTrue(result.context_observations)
        self.assertFalse(any(hasattr(item, "payload") for item in result.context_observations))
        self.assertNotIn("RAW PASSAGE A", encoded)
        self.assertNotIn("RAW PASSAGE B", encoded)

    def test_ambiguous_result_retains_no_raw_search_or_context_payloads(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeContextClient(
            search_rows={
                "maïeutique": [
                    {
                        "document_id": "doc-1",
                        "page_no": 4,
                        "para_no": 26,
                        "rank": 0.3,
                        "title": RAW_TITLE,
                        "text": RAW_QUERY,
                    },
                    {
                        "document_id": "doc-2",
                        "page_no": 5,
                        "para_no": 27,
                        "rank": 0.3,
                        "title": RAW_TITLE,
                        "text": RAW_QUERY,
                    },
                ]
            },
            context_payloads={
                ("page_para", "doc-1", 4, 26): _context_payload("doc-1", "RAW PASSAGE A"),
                ("page_para", "doc-2", 5, 27): _context_payload("doc-2", "RAW PASSAGE B"),
            },
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(plan)
        candidate_result = result.candidate_result
        encoded = json.dumps(result.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, context_search.STATUS_AMBIGUOUS)
        self.assertIsNotNone(candidate_result)
        self.assertTrue(candidate_result.endpoint_observations)
        self.assertTrue(result.context_observations)
        self.assertFalse(any(hasattr(item, "payload") for item in candidate_result.endpoint_observations))
        self.assertFalse(any(hasattr(item, "payload") for item in result.context_observations))
        self.assertEqual(result.passage, "")
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn("RAW PASSAGE A", encoded)
        self.assertNotIn("RAW PASSAGE B", encoded)

    def test_no_exploitable_context_is_not_found(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-1", "   ")}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_NOT_FOUND)
        self.assertEqual(result.passage, "")

    def test_too_long_context_remains_too_long(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-1", _long_passage("LONG"))}
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(
            _request(candidate_result, max_passage_chars=80)
        )

        self.assertEqual(result.status, context_search.STATUS_TOO_LONG)
        self.assertEqual(result.passage, "")

    def test_catalogue_error_is_catalogue_unavailable(self) -> None:
        candidate_result = _candidate_result([_candidate("doc-1", page_no=4, para_no=26)])
        fake = _FakeContextClient(
            context_errors={
                ("page_para", "doc-1", 4, 26): catalogue.CatalogueServiceUnavailable(
                    endpoint_kind=catalogue.ENDPOINT_CONTEXT,
                    doc_id="doc-1",
                )
            }
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(_request(candidate_result))

        self.assertEqual(result.status, context_search.STATUS_CATALOGUE_UNAVAILABLE)
        self.assertEqual(result.reason_code, context_search.REASON_CONTEXT_CATALOGUE_UNAVAILABLE)

    def test_observability_redacts_raw_payload_query_and_text(self) -> None:
        plan = query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque")
        fake = _FakeContextClient(
            search_rows={
                "maïeutique": [
                    {
                        "document_id": "doc-1",
                        "page_no": 4,
                        "para_no": 26,
                        "rank": 0.3,
                        "title": RAW_TITLE,
                        "text": RAW_QUERY,
                    }
                ]
            },
            context_payloads={("page_para", "doc-1", 4, 26): _context_payload("doc-1", RAW_PASSAGE)},
        )

        result = context_search.BiblioPassageContextSearcher(fake).search(plan)
        encoded = json.dumps(result.to_observability(), ensure_ascii=False, sort_keys=True)

        self.assertEqual(result.status, context_search.STATUS_EXTRACTED)
        self.assertTrue(result.context_observations)
        self.assertFalse(any(hasattr(item, "payload") for item in result.context_observations))
        self.assertIsNotNone(result.candidate_result)
        self.assertFalse(any(hasattr(item, "payload") for item in result.candidate_result.endpoint_observations))
        self.assertNotIn(RAW_PASSAGE, encoded)
        self.assertNotIn(RAW_TITLE, encoded)
        self.assertNotIn(RAW_QUERY, encoded)
        self.assertNotIn("maïeutique", encoded)


class _FakeContextClient:
    def __init__(
        self,
        *,
        search_rows: dict[str, list[dict[str, object]]] | None = None,
        context_payloads: dict[tuple[object, ...], dict[str, object]] | None = None,
        context_errors: dict[tuple[object, ...], catalogue.CatalogueClientError] | None = None,
    ) -> None:
        self.search_rows = search_rows or {}
        self.context_payloads = context_payloads or {}
        self.context_errors = context_errors or {}
        self.calls: list[tuple[object, ...]] = []

    def search(self, q: str, *, limit: int = 20) -> catalogue.CatalogueResponse:
        self.calls.append(("search", q, limit))
        rows = list(self.search_rows.get(q, []))[:limit]
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_SEARCH,
            status_code=200,
            payload={"count": len(rows), "results": rows},
            duration_ms=1,
            result_count=len(rows),
        )

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = context_search.DEFAULT_CONTEXT_WINDOW_CHARS,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("context", doc_id, paragraph_id, page_no, para_no, char_offset, window_chars))
        if paragraph_id is not None:
            key = ("paragraph_id", doc_id, paragraph_id)
        else:
            key = ("page_para", doc_id, page_no, para_no)
        error = self.context_errors.get(key)
        if error is not None:
            raise error
        payload = self.context_payloads.get(key)
        if payload is None:
            raise catalogue.CatalogueNotFound(endpoint_kind=catalogue.ENDPOINT_CONTEXT, doc_id=doc_id)
        return catalogue.CatalogueResponse(
            endpoint_kind=catalogue.ENDPOINT_CONTEXT,
            status_code=200,
            payload=dict(payload),
            duration_ms=1,
            result_count=1,
            doc_id_short=doc_id[:8],
            content_chars=len(str(payload.get("excerpt") or "")),
        )


def _request(
    candidate_result: candidate_search.BiblioPassageCandidateSearchResult,
    *,
    max_context_candidates: int = context_search.DEFAULT_MAX_CONTEXT_CANDIDATES,
    max_passage_chars: int = context_search.DEFAULT_MAX_PASSAGE_CHARS,
) -> context_search.BiblioPassageContextSearchRequest:
    return context_search.BiblioPassageContextSearchRequest(
        plan=query_planner.plan_biblio_query("Cherche maïeutique dans la bibliothèque"),
        candidate_result=candidate_result,
        max_context_candidates=max_context_candidates,
        max_passage_chars=max_passage_chars,
    )


def _candidate_result(
    candidates: list[candidate_search.BiblioPassageCandidate],
) -> candidate_search.BiblioPassageCandidateSearchResult:
    return candidate_search.BiblioPassageCandidateSearchResult(
        status=candidate_search.STATUS_CANDIDATES_FOUND,
        reason_code=candidate_search.REASON_CANDIDATES_FOUND,
        candidates=tuple(candidates),
        total_candidate_count=len(candidates),
    )


def _candidate(
    document_id: str,
    *,
    page_no: int,
    para_no: int,
    paragraph_id: int | None = None,
    score: float = 30.0,
    reason_codes: tuple[str, ...] = ("theme_hit",),
    catalogue_rank_score: float | None = 0.3,
) -> candidate_search.BiblioPassageCandidate:
    return candidate_search.BiblioPassageCandidate(
        document_id=document_id,
        doc_id_short=document_id[:8],
        page_no=page_no,
        para_no=para_no,
        paragraph_id=paragraph_id,
        score=score,
        hit_count=1,
        query_variant_count=1,
        query_hashes=("abc123abc123",),
        reason_codes=reason_codes,
        catalogue_rank_score=catalogue_rank_score,
        first_result_index=1,
    )


def _context_payload(
    document_id: str,
    passage: str,
    *,
    page_no: int = 4,
    para_no: int = 26,
    paragraph_id: int | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "document_id": document_id,
        "page_no": page_no,
        "para_no": para_no,
        "excerpt": passage,
        "excerpt_start": 0,
        "excerpt_end": len(passage),
        "text_length": len(passage),
        "title": RAW_TITLE,
    }
    if paragraph_id is not None:
        payload["paragraph_id"] = paragraph_id
    return payload


def _long_passage(label: str) -> str:
    return f"{label} " * 20


if __name__ == "__main__":
    unittest.main()
