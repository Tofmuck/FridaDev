import unittest
from typing import Any

from biblio.document_manifest_baseline import (
    build_baseline_from_client,
    collect_content_free_db_audit_from_connection,
)
from biblio.structure import (
    STATUS_INVALID,
    STATUS_VALID_WITH_WARNINGS,
    build_document_manifest,
    build_manifest_baseline_payload,
    validate_document_manifest,
)


class BiblioDocumentManifestTests(unittest.TestCase):
    def test_builds_content_free_section_bounds_from_chapter_successor(self) -> None:
        manifest = build_document_manifest(
            catalog_item={
                "id": "11111111-1111-1111-1111-111111111111",
                "title": "A very real title",
                "source_filename": "source.epub",
                "source_type": "epub",
                "unit_label": "sections",
                "unit_count": 20,
                "page_count": 20,
                "paragraph_count": 80,
                "chapter_count": 2,
                "toc_source": "epub_toc",
            },
            metadata_payload={
                "metadata_status": "validated",
                "human_metadata": {
                    "canonical_title": "A corrected title",
                    "language_override": "fr",
                },
            },
            chapters_payload={
                "chapters": [
                    {"chapter_no": 1, "title": "Intro", "unit_no": 3, "source": "epub_toc"},
                    {"chapter_no": 2, "title": "Body", "unit_no": 8, "source": "epub_toc"},
                ]
            },
            raw_unit_stats={
                "raw_unit_count": 42,
                "raw_unit_kinds": {"page": 20, "paragraph": 80},
            },
        )

        payload = manifest.to_dict()
        self.assertEqual(payload["document"]["technical_origin"], "epub")
        self.assertEqual(payload["document"]["language_signal"]["value"], "fr")
        self.assertEqual(payload["field_states"]["language"], "known")
        self.assertEqual(payload["field_states"]["raw_units"], "known")
        self.assertEqual(payload["sections"][0]["start_anchor"]["unit_no"], 3)
        self.assertEqual(payload["sections"][0]["end_anchor"]["unit_no"], 7)
        self.assertEqual(payload["sections"][1]["end_anchor"]["unit_no"], 20)
        self.assertNotIn("A corrected title", repr(payload))
        self.assertNotIn("source.epub", repr(payload))

    def test_pdf_origin_is_ambiguous_without_ocr_text_signal(self) -> None:
        manifest = build_document_manifest(
            catalog_item={
                "id": "22222222-2222-2222-2222-222222222222",
                "title": "PDF title",
                "source_filename": "source.pdf",
                "source_type": "pdf",
                "unit_label": "pages",
                "unit_count": 5,
                "page_count": 5,
                "paragraph_count": 12,
                "chapter_count": 0,
                "toc_source": "none",
            },
        )

        payload = manifest.to_dict()
        self.assertEqual(payload["document"]["technical_origin"], "pdf_unknown_ocr_or_text")
        self.assertEqual(payload["document"]["technical_origin_state"], "ambiguous")
        self.assertIn("pdf_origin_does_not_distinguish_scanned_ocr_from_text_pdf", payload["ambiguities"])
        self.assertEqual(payload["field_states"]["sections"], "unknown")

    def test_baseline_summary_counts_failures_and_roles(self) -> None:
        manifest = build_document_manifest(
            catalog_item={
                "id": "33333333-3333-3333-3333-333333333333",
                "title": "T",
                "source_filename": "source.epub",
                "source_type": "epub",
                "unit_label": "sections",
                "unit_count": 10,
                "page_count": 10,
                "paragraph_count": 30,
                "chapter_count": 1,
                "toc_source": "epub_toc",
            },
            chapters_payload={
                "chapters": [
                    {
                        "chapter_no": 1,
                        "title": "Commentary",
                        "unit_no": 1,
                        "source": "epub_toc",
                        "document_role_signal": "commentary",
                        "document_role_signal_source": "chapter_title",
                        "document_role_signal_strength": "weak",
                    }
                ]
            },
        )

        payload = build_manifest_baseline_payload(
            manifests=[manifest],
            failures=[{"status": "error", "reason_code": "x"}],
            generated_at="2026-06-03T00:00:00Z",
            db_audit={"documents": 1},
        )

        self.assertTrue(payload["content_policy"]["content_free"])
        self.assertEqual(payload["summary"]["documents_seen"], 2)
        self.assertEqual(payload["summary"]["manifests_produced"], 1)
        self.assertEqual(payload["summary"]["content_role_counts"]["commentary"], 1)
        self.assertEqual(payload["summary"]["validation_status_counts"]["valid_with_warnings"], 1)
        self.assertEqual(payload["summary"]["db_audit"]["documents"], 1)

    def test_validation_accepts_projectable_unknown_origin_new_import(self) -> None:
        manifest = build_document_manifest(
            catalog_item={
                "id": "44444444-4444-4444-4444-444444444444",
                "title": "Manual or unknown source",
                "source_filename": "source.bin",
                "source_type": "unknown",
                "unit_label": "pages",
                "unit_count": 3,
                "page_count": 3,
                "paragraph_count": 9,
                "chapter_count": 0,
                "toc_source": "none",
                "language_detected": "de",
            },
        )

        validation = validate_document_manifest(manifest)

        self.assertEqual(validation.status, STATUS_VALID_WITH_WARNINGS)
        self.assertEqual(validation.reason_codes, ())
        self.assertIn("technical_origin_not_fully_known", validation.warning_codes)
        self.assertIn("sections_unknown", validation.warning_codes)
        self.assertEqual(manifest.document.language_signal["value"], "de")

    def test_validation_fails_content_free_when_minimal_structure_is_missing(self) -> None:
        manifest = build_document_manifest(
            catalog_item={
                "id": "55555555-5555-5555-5555-555555555555",
                "title": "Incomplete source",
                "source_type": "pdf",
                "unit_label": "pages",
                "unit_count": 0,
                "page_count": 0,
                "paragraph_count": 0,
            },
        )

        validation = validate_document_manifest(manifest)

        self.assertEqual(validation.status, STATUS_INVALID)
        self.assertIn("document_units_missing", validation.reason_codes)
        self.assertIn("pages_missing", validation.reason_codes)
        self.assertIn("paragraphs_missing", validation.reason_codes)

    def test_baseline_is_buildable_without_external_json_payloads(self) -> None:
        client = _FakeCatalogueClient(
            items=[
                {
                    "id": "66666666-6666-6666-6666-666666666666",
                    "title": "Catalogue title",
                    "source_type": "epub",
                    "unit_label": "sections",
                    "unit_count": 4,
                    "page_count": 4,
                    "paragraph_count": 12,
                    "chapter_count": 0,
                    "toc_source": "none",
                }
            ]
        )

        payload, failures = build_baseline_from_client(
            client=client,
            generated_at="2026-06-03T00:00:00Z",
            raw_unit_stats={},
            db_audit={"status": "skipped", "reason_code": "test"},
        )

        self.assertEqual(failures, [])
        self.assertEqual(payload["summary"]["documents_seen"], 1)
        self.assertEqual(payload["summary"]["manifests_produced"], 1)
        self.assertIn("validation", payload["manifests"][0])
        self.assertTrue(payload["content_policy"]["content_free"])

    def test_baseline_fails_when_projected_manifest_is_invalid(self) -> None:
        client = _FakeCatalogueClient(
            items=[
                {
                    "id": "88888888-8888-8888-8888-888888888888",
                    "title": "Broken structure",
                    "source_type": "pdf",
                    "unit_label": "pages",
                    "unit_count": 0,
                    "page_count": 0,
                    "paragraph_count": 0,
                    "chapter_count": 0,
                    "toc_source": "none",
                }
            ]
        )

        payload, failures = build_baseline_from_client(
            client=client,
            generated_at="2026-06-03T00:00:00Z",
            raw_unit_stats={},
            db_audit={"status": "skipped", "reason_code": "test"},
        )

        self.assertEqual(len(failures), 1)
        self.assertEqual(payload["summary"]["documents_seen"], 1)
        self.assertEqual(payload["summary"]["manifests_produced"], 0)
        self.assertEqual(payload["summary"]["failures"], 1)
        self.assertEqual(payload["summary"]["invalid_manifest_failures"], 1)
        self.assertEqual(payload["summary"]["failure_reason_counts"]["manifest_validation_failed"], 1)
        self.assertEqual(failures[0]["status"], "invalid")
        self.assertEqual(failures[0]["reason_code"], "manifest_validation_failed")
        self.assertIn("document_units_missing", failures[0]["validation_reason_codes"])
        self.assertIn("pages_missing", failures[0]["validation_reason_codes"])
        self.assertIn("paragraphs_missing", failures[0]["validation_reason_codes"])
        self.assertIn("manifest_validation_failed", repr(payload["failures"]))

    def test_baseline_accepts_valid_with_warnings(self) -> None:
        client = _FakeCatalogueClient(
            items=[
                {
                    "id": "99999999-9999-9999-9999-999999999999",
                    "title": "Warning only structure",
                    "source_type": "unknown",
                    "unit_label": "pages",
                    "unit_count": 2,
                    "page_count": 2,
                    "paragraph_count": 4,
                    "chapter_count": 0,
                    "toc_source": "none",
                }
            ]
        )

        payload, failures = build_baseline_from_client(
            client=client,
            generated_at="2026-06-03T00:00:00Z",
            raw_unit_stats={},
            db_audit={"status": "skipped", "reason_code": "test"},
        )

        self.assertEqual(failures, [])
        self.assertEqual(payload["summary"]["manifests_produced"], 1)
        self.assertEqual(payload["summary"]["failures"], 0)
        self.assertEqual(payload["summary"]["validation_status_counts"]["valid_with_warnings"], 1)
        self.assertIn("technical_origin_not_fully_known", payload["manifests"][0]["validation"]["warning_codes"])

    def test_db_audit_collector_is_content_free(self) -> None:
        payload = collect_content_free_db_audit_from_connection(_FakeDbConnection())

        self.assertEqual(payload["db_audit"]["status"], "ok")
        self.assertEqual(payload["raw_unit_stats"]["77777777-7777-7777-7777-777777777777"]["raw_unit_count"], 3)
        self.assertEqual(payload["db_audit"]["tables"]["documents"], 1)
        self.assertTrue(payload["db_audit"]["content_policy"]["content_free"])
        self.assertNotIn("raw_text", repr(payload))


class _Response:
    def __init__(self, payload: dict[str, Any]) -> None:
        self.payload = payload


class _FakeCatalogueClient:
    def __init__(self, *, items: list[dict[str, Any]]) -> None:
        self.items = items

    def catalog(self, *, limit: int, offset: int) -> _Response:
        batch = self.items[offset : offset + limit]
        return _Response({"items": batch, "total": len(self.items)})

    def metadata(self, document_id: str) -> _Response:
        return _Response({"document": {}, "human_metadata": {}, "metadata_status": "unknown"})

    def document(self, document_id: str) -> _Response:
        return _Response({})

    def chapters(self, document_id: str, *, limit: int, offset: int) -> _Response:
        return _Response({"chapters": []})


class _FakeDbConnection:
    def cursor(self) -> "_FakeDbCursor":
        return _FakeDbCursor()


class _FakeDbCursor:
    def __enter__(self) -> "_FakeDbCursor":
        return self

    def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    def execute(self, sql: str) -> None:
        self.sql = " ".join(sql.lower().split())

    def fetchall(self) -> list[tuple[Any, ...]]:
        sql = self.sql
        if "from raw_units group by document_id" in sql:
            return [
                ("77777777-7777-7777-7777-777777777777", "page", 1),
                ("77777777-7777-7777-7777-777777777777", "paragraph", 2),
            ]
        if "from documents group by 1, 2" in sql:
            return [("epub", "sections", 1)]
        if "from documents group by 1 order by 1" in sql:
            return [("epub_toc", 1)]
        if "from catalogue_human_metadata" in sql:
            return [("validated", 1)]
        if "from milestones" in sql and "group by kind" in sql:
            return [("stephanus", 3)]
        if "where coalesce" in sql and "is not null" in sql:
            return [(1,)]
        if "where coalesce" in sql and "is null" in sql:
            return [(0,)]
        if "llm_json_format_valid is true" in sql:
            return [(1,)]
        if "llm_json_format_valid is false" in sql:
            return [(0,)]
        if "llm_json_safe_for_db is true" in sql:
            return [(1,)]
        if "llm_json_safe_for_db is false" in sql:
            return [(0,)]
        for table in ("documents", "pages", "paragraphs", "raw_units", "document_chapters", "milestones"):
            if f"from {table}" in sql:
                return [(1,)]
        return [(0,)]


if __name__ == "__main__":
    unittest.main()
