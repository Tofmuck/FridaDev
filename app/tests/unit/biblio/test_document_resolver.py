from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import document_resolver as resolver


class DocumentResolverTests(unittest.TestCase):
    def test_document_id_resolves_with_human_metadata(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "auto title"}}},
            metadata={
                "doc-1": {
                    "document": {"id": "doc-1", "title": "auto title"},
                    "human_metadata": {
                        "canonical_title": "Theetete",
                        "authors": "Platon",
                        "metadata_status": "corrected",
                    },
                    "metadata_status": "corrected",
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1")
        )

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.reason_code, resolver.REASON_DOCUMENT_RESOLVED)
        self.assertEqual(result.document.document_id, "doc-1")
        self.assertEqual(result.document.canonical_title, "Theetete")
        self.assertEqual(result.document.authors, "Platon")
        self.assertNotIn("auto title", str(result.to_observability()))
        self.assertEqual(fake.calls, [("metadata", "doc-1")])

    def test_title_and_author_resolve_single_catalogue_candidate(self) -> None:
        fake = FakeCatalogueClient(
            catalog_payload={
                "total": 1,
                "items": [
                    {
                        "id": "doc-theetete",
                        "title": "Platon - Theetete",
                        "human_canonical_title": "Theetete",
                        "human_authors": "Platon",
                        "human_metadata_status": "validated",
                    }
                ],
            }
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(title="Theetete", author="Platon")
        )

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.document.doc_id_short, "doc-thee")
        self.assertEqual(result.document.match_reasons, ("human_title", "human_author"))
        self.assertEqual(fake.calls, [("catalog", "Theetete", resolver.DOCUMENT_QUERY_LIMIT, 0)])

    def test_multiple_platon_documents_are_ambiguous_and_do_not_call_locate(self) -> None:
        fake = FakeCatalogueClient(
            catalog_payload={
                "total": 2,
                "items": [
                    {"id": "doc-a", "title": "Oeuvres completes", "human_authors": "Platon"},
                    {"id": "doc-b", "title": "Theetete", "human_authors": "Platon"},
                ],
            }
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(title="Platon", locator="126b")
        )

        self.assertEqual(result.status, resolver.STATUS_AMBIGUOUS)
        self.assertEqual(result.reason_code, resolver.REASON_AMBIGUOUS_DOCUMENT)
        self.assertEqual([candidate.doc_id_short for candidate in result.document_candidates], ["doc-a", "doc-b"])
        self.assertEqual(fake.calls, [("catalog", "Platon", resolver.DOCUMENT_QUERY_LIMIT, 0)])

    def test_locator_without_document_signal_is_invalid_request(self) -> None:
        fake = FakeCatalogueClient()

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(locator="126b")
        )

        self.assertEqual(result.status, resolver.STATUS_INVALID_REQUEST)
        self.assertEqual(result.reason_code, resolver.REASON_LOCATOR_REQUIRES_DOCUMENT)
        self.assertEqual(fake.calls, [])

    def test_locator_range_without_start_is_invalid_request(self) -> None:
        fake = FakeCatalogueClient()

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator_end="126e")
        )

        self.assertEqual(result.status, resolver.STATUS_INVALID_REQUEST)
        self.assertEqual(result.reason_code, resolver.REASON_LOCATOR_RANGE_REQUIRES_START)
        self.assertEqual(fake.calls, [])

    def test_single_document_single_stephanus_locator_resolves_without_context(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 12, "para_no": 3},
                    "text": "secret passage must be ignored",
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
        )

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.reason_code, resolver.REASON_DOCUMENT_AND_LOCATOR_RESOLVED)
        self.assertEqual(result.locator.label, "126b")
        self.assertEqual(result.locator.page_no, 12)
        self.assertNotIn("secret passage", str(result.to_observability()))
        self.assertNotIn("context", [call[0] for call in fake.calls])

    def test_multiple_locator_matches_are_ambiguous(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 2,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                    "alternatives": [{"kind": "stephanus", "label": "126b", "page_no": 9, "para_no": 5}],
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
        )

        self.assertEqual(result.status, resolver.STATUS_AMBIGUOUS)
        self.assertEqual(result.reason_code, resolver.REASON_AMBIGUOUS_LOCATOR)
        self.assertEqual(len(result.locator_candidates), 2)

    def test_locator_anchor_disambiguates_multiple_matches_without_text(self) -> None:
        fake = FakeCatalogueClient(
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 2,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                    "alternatives": [
                        {"kind": "stephanus", "label": "126b", "page_no": 9, "para_no": 5, "order_index": 25}
                    ],
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(
                document_id="doc-1",
                locator="126b",
                locator_anchor_page=9,
            )
        )
        observed = result.to_observability()

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.locator.page_no, 9)
        self.assertEqual(result.locator.order_index, 25)
        self.assertEqual(observed["locator_anchor_page"], 9)
        self.assertNotIn("126b", str(observed))

    def test_stephanus_range_is_ambiguous_when_end_locator_is_ambiguous(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                },
                ("doc-1", "stephanus", "126e"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126e",
                    "match_count": 2,
                    "best": {"kind": "stephanus", "label": "126e", "page_no": 2, "para_no": 1},
                    "alternatives": [{"kind": "stephanus", "label": "126e", "page_no": 7, "para_no": 4}],
                },
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="126b", locator_end="126e")
        )

        self.assertEqual(result.status, resolver.STATUS_AMBIGUOUS)
        self.assertEqual(result.reason_code, resolver.REASON_AMBIGUOUS_LOCATOR)
        self.assertIsNone(result.locator_end)

    def test_stephanus_range_resolves_when_document_and_both_locators_are_unique(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                },
                ("doc-1", "stephanus", "126e"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126e",
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126e", "page_no": 2, "para_no": 3},
                },
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="126b", locator_end="126e")
        )

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.reason_code, resolver.REASON_DOCUMENT_AND_LOCATOR_RANGE_RESOLVED)
        self.assertEqual(result.locator.label, "126b")
        self.assertEqual(result.locator_end.label, "126e")

    def test_document_not_found_is_content_free(self) -> None:
        fake = FakeCatalogueClient(document_errors={"missing": catalogue.CatalogueNotFound(doc_id="missing")})

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="missing")
        )

        self.assertEqual(result.status, resolver.STATUS_NOT_FOUND)
        self.assertEqual(result.reason_code, resolver.REASON_DOCUMENT_NOT_FOUND)
        self.assertNotIn("missing", str(result.to_observability()))

    def test_locator_not_found(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_errors={("doc-1", "stephanus", "999z"): catalogue.CatalogueNotFound(doc_id="doc-1")},
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="999z")
        )

        self.assertEqual(result.status, resolver.STATUS_NOT_FOUND)
        self.assertEqual(result.reason_code, resolver.REASON_LOCATOR_NOT_FOUND)

    def test_catalogue_unavailable_is_structured(self) -> None:
        fake = FakeCatalogueClient(catalog_error=catalogue.CatalogueTimeout(endpoint_kind="catalog"))

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(title="Theetete")
        )

        self.assertEqual(result.status, resolver.STATUS_CATALOGUE_UNAVAILABLE)
        self.assertEqual(result.reason_code, resolver.REASON_CATALOGUE_UNAVAILABLE)

    def test_observability_hides_requested_locator_raw_value(self) -> None:
        raw_locator = "SECRET USER RAW LOCATOR SHOULD NOT BE IN OBSERVABILITY"

        result = resolver.BiblioDocumentResolver(FakeCatalogueClient()).resolve(
            resolver.BiblioResolveRequest(locator=raw_locator)
        )
        observed = result.to_observability()

        self.assertEqual(result.status, resolver.STATUS_INVALID_REQUEST)
        self.assertEqual(observed["status"], resolver.STATUS_INVALID_REQUEST)
        self.assertEqual(observed["reason_code"], resolver.REASON_LOCATOR_REQUIRES_DOCUMENT)
        self.assertNotIn(raw_locator, str(observed))
        self.assertEqual(observed["requested_locator"]["present"], True)
        self.assertEqual(observed["requested_locator"]["length"], len(raw_locator))
        self.assertEqual(len(observed["requested_locator"]["hash"]), 12)

    def test_observability_hides_requested_locator_end_raw_value(self) -> None:
        raw_locator_end = "SECRET END RAW LOCATOR SHOULD NOT BE IN OBSERVABILITY"

        result = resolver.BiblioDocumentResolver(FakeCatalogueClient()).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator_end=raw_locator_end)
        )
        observed = result.to_observability()

        self.assertEqual(result.status, resolver.STATUS_INVALID_REQUEST)
        self.assertEqual(observed["reason_code"], resolver.REASON_LOCATOR_RANGE_REQUIRES_START)
        self.assertNotIn(raw_locator_end, str(observed))
        self.assertEqual(observed["requested_locator_end"]["present"], True)
        self.assertEqual(observed["requested_locator_end"]["length"], len(raw_locator_end))

    def test_observability_hides_locator_candidate_label_raw_value(self) -> None:
        raw_locator = "SECRET RAW LOCATOR LABEL"
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "custom", raw_locator): {
                    "document_id": "doc-1",
                    "kind": "custom",
                    "label": raw_locator,
                    "match_count": 1,
                    "best": {"kind": "custom", "label": raw_locator, "page_no": 12, "para_no": 3},
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator=raw_locator, locator_kind="custom")
        )
        observed = result.to_observability()

        self.assertEqual(result.status, resolver.STATUS_RESOLVED)
        self.assertEqual(result.locator.label, raw_locator)
        self.assertNotIn(raw_locator, str(observed))
        self.assertEqual(observed["locator"]["kind"], "custom")
        self.assertEqual(observed["locator"]["label"]["present"], True)
        self.assertEqual(observed["locator"]["label"]["length"], len(raw_locator))
        self.assertEqual(len(observed["locator"]["label"]["hash"]), 12)
        self.assertEqual(observed["locator_candidate_count"], 1)

    def test_observability_keeps_stephanus_ambiguity_content_free(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "document_id": "doc-1",
                    "kind": "stephanus",
                    "label": "126b",
                    "match_count": 2,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                    "alternatives": [{"kind": "stephanus", "label": "126b", "page_no": 9, "para_no": 5}],
                }
            },
        )

        result = resolver.BiblioDocumentResolver(fake).resolve(
            resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
        )
        observed = result.to_observability()

        self.assertEqual(observed["status"], resolver.STATUS_AMBIGUOUS)
        self.assertEqual(observed["reason_code"], resolver.REASON_AMBIGUOUS_LOCATOR)
        self.assertEqual(observed["locator_candidate_count"], 2)
        self.assertNotIn("126b", str(observed))
        self.assertEqual(observed["requested_locator"]["length"], len("126b"))


def response(payload: dict[str, object], endpoint_kind: str) -> catalogue.CatalogueResponse:
    return catalogue.CatalogueResponse(
        endpoint_kind=endpoint_kind,
        status_code=200,
        payload=payload,
        duration_ms=1,
        result_count=payload.get("count") if isinstance(payload.get("count"), int) else None,
    )


class FakeCatalogueClient:
    def __init__(
        self,
        *,
        catalog_payload: dict[str, object] | None = None,
        catalog_error: Exception | None = None,
        documents: dict[str, dict[str, object]] | None = None,
        document_errors: dict[str, Exception] | None = None,
        metadata: dict[str, dict[str, object]] | None = None,
        locate_payloads: dict[tuple[str, str, str], dict[str, object]] | None = None,
        locate_errors: dict[tuple[str, str, str], Exception] | None = None,
    ) -> None:
        self.catalog_payload = catalog_payload or {"total": 0, "items": []}
        self.catalog_error = catalog_error
        self.documents = documents or {}
        self.document_errors = document_errors or {}
        self.metadata_payloads = metadata or {}
        self.locate_payloads = locate_payloads or {}
        self.locate_errors = locate_errors or {}
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        if self.catalog_error:
            raise self.catalog_error
        return response(self.catalog_payload, "catalog")

    def document(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("document", doc_id))
        if doc_id in self.document_errors:
            raise self.document_errors[doc_id]
        if doc_id not in self.documents:
            raise catalogue.CatalogueNotFound(doc_id=doc_id)
        return response(self.documents[doc_id], "document")

    def metadata(self, doc_id: str) -> catalogue.CatalogueResponse:
        self.calls.append(("metadata", doc_id))
        if doc_id not in self.metadata_payloads:
            raise catalogue.CatalogueNotFound(doc_id=doc_id)
        return response(self.metadata_payloads[doc_id], "metadata")

    def locate(
        self,
        doc_id: str,
        locator: str,
        *,
        kind: str = "stephanus",
        limit: int = 200,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("locate", doc_id, locator, kind, limit))
        key = (doc_id, kind, locator)
        if key in self.locate_errors:
            raise self.locate_errors[key]
        if key not in self.locate_payloads:
            raise catalogue.CatalogueNotFound(doc_id=doc_id)
        return response(self.locate_payloads[key], "locate")

    def context(self, *args, **kwargs):  # pragma: no cover - called only on regression.
        raise AssertionError("resolver must not call context in Lot 3")


if __name__ == "__main__":
    unittest.main()
