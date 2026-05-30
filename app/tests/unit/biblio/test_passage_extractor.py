from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from biblio import catalogue_client as catalogue
from biblio import document_resolver as resolver
from biblio import passage_extractor as extractor


class PassageExtractorTests(unittest.TestCase):
    def test_extracts_single_resolved_locator_without_observability_text(self) -> None:
        raw_passage = "RAW PASSAGE SHOULD STAY INTERNAL"
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {"authors": "Platon"}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 12, "para_no": 3},
                }
            },
            context_payloads={
                ("page_para", "doc-1", 12, 3, 0, extractor.DEFAULT_CONTEXT_WINDOW_CHARS): {
                    "document_id": "doc-1",
                    "page_no": 12,
                    "para_no": 3,
                    "paragraph_id": 99,
                    "char_offset": 0,
                    "window_chars": extractor.DEFAULT_CONTEXT_WINDOW_CHARS,
                    "excerpt_start": 0,
                    "excerpt_end": len(raw_passage),
                    "text_length": len(raw_passage),
                    "excerpt": raw_passage,
                    "title": "Raw title must be ignored",
                }
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
            )
        )
        observed = result.to_observability()

        self.assertEqual(result.status, extractor.STATUS_EXTRACTED)
        self.assertEqual(result.reason_code, extractor.REASON_PASSAGE_EXTRACTED)
        self.assertEqual(result.passage, raw_passage)
        self.assertEqual(observed["passage_present"], True)
        self.assertEqual(observed["passage_chars"], len(raw_passage))
        self.assertEqual(len(observed["passage_hash"]), 12)
        self.assertNotIn(raw_passage, str(observed))
        self.assertNotIn("126b", str(observed))
        self.assertNotIn("Raw title", str(observed))
        self.assertEqual(fake.calls[-1], ("context", "doc-1", None, 12, 3, 0, extractor.DEFAULT_CONTEXT_WINDOW_CHARS))

    def test_uses_paragraph_id_context_when_locator_has_paragraph_id(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "paragraph", "p99"): {
                    "match_count": 1,
                    "best": {"kind": "paragraph", "label": "p99", "paragraph_id": 99},
                }
            },
            context_payloads={
                ("paragraph_id", "doc-1", 99, 0, extractor.DEFAULT_CONTEXT_WINDOW_CHARS): {
                    "document_id": "doc-1",
                    "paragraph_id": 99,
                    "excerpt": "paragraph excerpt",
                }
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(
                    document_id="doc-1",
                    locator="p99",
                    locator_kind="paragraph",
                )
            )
        )

        self.assertEqual(result.status, extractor.STATUS_EXTRACTED)
        self.assertEqual(fake.calls[-1], ("context", "doc-1", 99, None, None, 0, extractor.DEFAULT_CONTEXT_WINDOW_CHARS))

    def test_ambiguous_resolution_refuses_context(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 2,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                    "alternatives": [{"kind": "stephanus", "label": "126b", "page_no": 9, "para_no": 5}],
                }
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
            )
        )

        self.assertEqual(result.status, extractor.STATUS_AMBIGUOUS)
        self.assertEqual(result.reason_code, resolver.REASON_AMBIGUOUS_LOCATOR)
        self.assertNotIn("context", [call[0] for call in fake.calls])

    def test_locator_only_126b_refuses_extraction_before_context(self) -> None:
        fake = FakeCatalogueClient()

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(resolve_request=resolver.BiblioResolveRequest(locator="126b"))
        )

        self.assertEqual(result.status, extractor.STATUS_INVALID_REQUEST)
        self.assertEqual(result.reason_code, resolver.REASON_LOCATOR_REQUIRES_DOCUMENT)
        self.assertEqual(fake.calls, [])

    def test_resolved_range_is_not_silently_extracted_from_start(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 1, "para_no": 1},
                },
                ("doc-1", "stephanus", "126e"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126e", "page_no": 2, "para_no": 3},
                },
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(
                    document_id="doc-1",
                    locator="126b",
                    locator_end="126e",
                )
            )
        )

        self.assertEqual(result.status, extractor.STATUS_INVALID_REQUEST)
        self.assertEqual(result.reason_code, extractor.REASON_RANGE_EXTRACTION_NOT_SUPPORTED)
        self.assertNotIn("context", [call[0] for call in fake.calls])

    def test_resolved_same_page_range_extracts_bounded_paragraphs(self) -> None:
        raw_a = "RANGE PASSAGE PART A"
        raw_b = "RANGE PASSAGE PART B"
        fake = FakeCatalogueClient(
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 7, "para_no": 2},
                },
                ("doc-1", "stephanus", "126c"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126c", "page_no": 7, "para_no": 3},
                },
            },
            context_payloads={
                ("page_para", "doc-1", 7, 2, 0, extractor.MAX_CONTEXT_WINDOW_CHARS): {
                    "document_id": "doc-1",
                    "page_no": 7,
                    "para_no": 2,
                    "excerpt": raw_a,
                },
                ("page_para", "doc-1", 7, 3, 0, extractor.MAX_CONTEXT_WINDOW_CHARS): {
                    "document_id": "doc-1",
                    "page_no": 7,
                    "para_no": 3,
                    "excerpt": raw_b,
                },
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(
                    document_id="doc-1",
                    locator="126b",
                    locator_end="126c",
                ),
                window_chars=extractor.MAX_CONTEXT_WINDOW_CHARS,
                max_passage_chars=500,
            )
        )
        observed = result.to_observability()

        self.assertEqual(result.status, extractor.STATUS_EXTRACTED)
        self.assertEqual(result.reason_code, extractor.REASON_RANGE_EXTRACTED)
        self.assertIn(raw_a, result.passage)
        self.assertIn(raw_b, result.passage)
        self.assertNotIn(raw_a, str(observed))
        self.assertNotIn(raw_b, str(observed))
        self.assertEqual(
            [call for call in fake.calls if call[0] == "context"],
            [
                ("context", "doc-1", None, 7, 2, 0, extractor.MAX_CONTEXT_WINDOW_CHARS),
                ("context", "doc-1", None, 7, 3, 0, extractor.MAX_CONTEXT_WINDOW_CHARS),
            ],
        )

    def test_locator_without_context_target_is_invalid(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b"},
                }
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
            )
        )

        self.assertEqual(result.status, extractor.STATUS_INVALID_REQUEST)
        self.assertEqual(result.reason_code, extractor.REASON_LOCATOR_CONTEXT_TARGET_MISSING)
        self.assertNotIn("context", [call[0] for call in fake.calls])

    def test_empty_context_is_explicit_and_content_free(self) -> None:
        fake = _single_locator_client(context_payload={"document_id": "doc-1", "page_no": 12, "para_no": 3, "excerpt": "   "})

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())
        observed = result.to_observability()

        self.assertEqual(result.status, extractor.STATUS_EMPTY)
        self.assertEqual(result.reason_code, extractor.REASON_PASSAGE_EMPTY)
        self.assertEqual(result.passage, "")
        self.assertEqual(observed["passage_chars"], 3)
        self.assertEqual(len(observed["passage_hash"]), 12)
        self.assertNotIn("   ", str(observed))

    def test_context_not_found_is_explicit(self) -> None:
        fake = _single_locator_client(context_error=catalogue.CatalogueNotFound(doc_id="doc-1"))

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())

        self.assertEqual(result.status, extractor.STATUS_NOT_FOUND)
        self.assertEqual(result.reason_code, extractor.REASON_PASSAGE_NOT_FOUND)

    def test_too_long_context_returns_no_passage(self) -> None:
        raw_passage = "x" * (extractor.DEFAULT_MAX_PASSAGE_CHARS + 1)
        fake = _single_locator_client(
            context_payload={
                "document_id": "doc-1",
                "page_no": 12,
                "para_no": 3,
                "excerpt": raw_passage,
                "text_length": len(raw_passage),
            }
        )

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())
        observed = result.to_observability()

        self.assertEqual(result.status, extractor.STATUS_TOO_LONG)
        self.assertEqual(result.reason_code, extractor.REASON_PASSAGE_TOO_LONG)
        self.assertEqual(result.passage, "")
        self.assertEqual(observed["passage_chars"], len(raw_passage))
        self.assertEqual(len(observed["passage_hash"]), 12)
        self.assertNotIn(raw_passage, str(observed))

    def test_incoherent_context_without_excerpt_is_explicit(self) -> None:
        fake = _single_locator_client(context_payload={"document_id": "doc-1", "page_no": 12, "para_no": 3})

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())

        self.assertEqual(result.status, extractor.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, extractor.REASON_INCOHERENT_CATALOGUE_RESPONSE)
        self.assertEqual(result.passage, "")

    def test_incoherent_context_doc_id_mismatch_is_explicit(self) -> None:
        fake = _single_locator_client(
            context_payload={"document_id": "other-doc", "page_no": 12, "para_no": 3, "excerpt": "raw"}
        )

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())

        self.assertEqual(result.status, extractor.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, extractor.REASON_INCOHERENT_CATALOGUE_RESPONSE)
        self.assertEqual(result.passage, "")

    def test_incoherent_context_without_document_id_never_extracts_text(self) -> None:
        raw_passage = "RAW PASSAGE WITHOUT DOCUMENT ID MUST NOT LEAK"
        fake = _single_locator_client(
            context_payload={"page_no": 12, "para_no": 3, "excerpt": raw_passage}
        )

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())
        observed = result.to_observability()

        self.assertEqual(result.status, extractor.STATUS_INCOHERENT_CATALOGUE)
        self.assertEqual(result.reason_code, extractor.REASON_INCOHERENT_CATALOGUE_RESPONSE)
        self.assertEqual(result.passage, "")
        self.assertNotIn(raw_passage, str(observed))

    def test_catalogue_unavailable_from_context_is_content_free(self) -> None:
        fake = _single_locator_client(
            context_error=catalogue.CatalogueTimeout(endpoint_kind="context", error_class="Timeout")
        )

        result = extractor.BiblioPassageExtractor(fake).extract(_single_locator_request())

        self.assertEqual(result.status, extractor.STATUS_CATALOGUE_UNAVAILABLE)
        self.assertEqual(result.reason_code, extractor.REASON_CATALOGUE_UNAVAILABLE)

    def test_valid_string_options_are_accepted_without_truncation(self) -> None:
        fake = FakeCatalogueClient(
            documents={"doc-1": {"document": {"id": "doc-1"}}},
            metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
            locate_payloads={
                ("doc-1", "stephanus", "126b"): {
                    "match_count": 1,
                    "best": {"kind": "stephanus", "label": "126b", "page_no": 12, "para_no": 3},
                }
            },
            context_payloads={
                ("page_para", "doc-1", 12, 3, 5, 80): {
                    "document_id": "doc-1",
                    "page_no": 12,
                    "para_no": 3,
                    "excerpt": "valid excerpt",
                }
            },
        )

        result = extractor.BiblioPassageExtractor(fake).extract(
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(document_id="doc-1", locator="126b"),
                char_offset="5",
                window_chars="80",
                max_passage_chars="100",
            )
        )

        self.assertEqual(result.status, extractor.STATUS_EXTRACTED)
        self.assertEqual(fake.calls[-1], ("context", "doc-1", None, 12, 3, 5, 80))

    def test_invalid_extraction_options_refuse_before_network(self) -> None:
        fake = FakeCatalogueClient()
        cases = [
            extractor.BiblioPassageRequest(resolve_request=resolver.BiblioResolveRequest(document_id="doc-1"), window_chars=1.5),
            extractor.BiblioPassageRequest(resolve_request=resolver.BiblioResolveRequest(document_id="doc-1"), window_chars=True),
            extractor.BiblioPassageRequest(resolve_request=resolver.BiblioResolveRequest(document_id="doc-1"), window_chars="80.9"),
            extractor.BiblioPassageRequest(resolve_request=resolver.BiblioResolveRequest(document_id="doc-1"), char_offset=-1),
            extractor.BiblioPassageRequest(
                resolve_request=resolver.BiblioResolveRequest(document_id="doc-1"),
                max_passage_chars=extractor.MAX_MAX_PASSAGE_CHARS + 1,
            ),
        ]

        for request in cases:
            with self.subTest(request=request):
                result = extractor.BiblioPassageExtractor(fake).extract(request)
                self.assertEqual(result.status, extractor.STATUS_INVALID_REQUEST)
                self.assertEqual(result.reason_code, extractor.REASON_INVALID_PASSAGE_PARAMETER)

        self.assertEqual(fake.calls, [])


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
        documents: dict[str, dict[str, object]] | None = None,
        document_errors: dict[str, Exception] | None = None,
        metadata: dict[str, dict[str, object]] | None = None,
        locate_payloads: dict[tuple[str, str, str], dict[str, object]] | None = None,
        locate_errors: dict[tuple[str, str, str], Exception] | None = None,
        context_payloads: dict[tuple[object, ...], dict[str, object]] | None = None,
        context_error: Exception | None = None,
    ) -> None:
        self.documents = documents or {}
        self.document_errors = document_errors or {}
        self.metadata_payloads = metadata or {}
        self.locate_payloads = locate_payloads or {}
        self.locate_errors = locate_errors or {}
        self.context_payloads = context_payloads or {}
        self.context_error = context_error
        self.calls: list[tuple[object, ...]] = []

    def catalog(self, *, q: str | None = None, limit: int = 100, offset: int = 0) -> catalogue.CatalogueResponse:
        self.calls.append(("catalog", q, limit, offset))
        return response({"total": 0, "items": []}, "catalog")

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

    def context(
        self,
        doc_id: str,
        *,
        page_no: int | None = None,
        para_no: int | None = None,
        paragraph_id: int | None = None,
        char_offset: int = 0,
        window_chars: int = extractor.DEFAULT_CONTEXT_WINDOW_CHARS,
    ) -> catalogue.CatalogueResponse:
        self.calls.append(("context", doc_id, paragraph_id, page_no, para_no, char_offset, window_chars))
        if self.context_error:
            raise self.context_error
        if paragraph_id is not None:
            key = ("paragraph_id", doc_id, paragraph_id, char_offset, window_chars)
        else:
            key = ("page_para", doc_id, page_no, para_no, char_offset, window_chars)
        if key not in self.context_payloads:
            raise catalogue.CatalogueNotFound(doc_id=doc_id)
        return response(self.context_payloads[key], "context")


def _single_locator_client(
    *,
    context_payload: dict[str, object] | None = None,
    context_error: Exception | None = None,
) -> FakeCatalogueClient:
    context_payload = context_payload if context_payload is not None else {"document_id": "doc-1", "excerpt": "ok"}
    return FakeCatalogueClient(
        documents={"doc-1": {"document": {"id": "doc-1", "title": "Theetete"}}},
        metadata={"doc-1": {"document": {"id": "doc-1"}, "human_metadata": {}}},
        locate_payloads={
            ("doc-1", "stephanus", "126b"): {
                "match_count": 1,
                "best": {"kind": "stephanus", "label": "126b", "page_no": 12, "para_no": 3},
            }
        },
        context_payloads={
            ("page_para", "doc-1", 12, 3, 0, extractor.DEFAULT_CONTEXT_WINDOW_CHARS): context_payload
        },
        context_error=context_error,
    )


def _single_locator_request() -> extractor.BiblioPassageRequest:
    return extractor.BiblioPassageRequest(
        resolve_request=resolver.BiblioResolveRequest(document_id="doc-1", locator="126b")
    )


if __name__ == "__main__":
    unittest.main()
