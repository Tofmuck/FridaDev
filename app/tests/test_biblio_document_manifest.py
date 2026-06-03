import unittest

from biblio.structure import build_document_manifest, build_manifest_baseline_payload


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
        self.assertEqual(payload["summary"]["db_audit"]["documents"], 1)


if __name__ == "__main__":
    unittest.main()
