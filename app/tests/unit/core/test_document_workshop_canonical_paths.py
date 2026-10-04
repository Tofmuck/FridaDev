from __future__ import annotations

import copy
import importlib
import importlib.util
import unittest
from urllib.parse import unquote


def span(text, **changes):
    return dict(text=text, bold=False, italic=False, link=None, **changes)


def canonical(text="Texte synthétique"):
    return {
        "schema_version": 1,
        "profile": "frida_document_v1",
        "blocks": [{"type": "paragraph", "spans": [span(text)]}],
    }


class CanonicalContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.document_canonical"), "M0 canonical interface absent")
        self.module = importlib.import_module("core.document_canonical")
        self.error = importlib.import_module("core.document_workshop_contract").DocumentWorkshopError

    def reject(self, data, code):
        before = copy.deepcopy(data)
        with self.assertRaises(self.error) as raised:
            self.module.validate_canonical(data)
        self.assertEqual(raised.exception.reason_code, code)
        self.assertEqual(data, before)

    def test_exact_word_limit_and_refusal_do_not_rewrite_input(self):
        result = self.module.validate_canonical(canonical(" ".join(["mot"] * 10000)))
        self.assertEqual(result.word_count, 10000)
        self.reject(canonical(" ".join(["mot"] * 10001)), "document_word_limit")

    def test_codepoint_limit_independent_of_words(self):
        self.assertEqual(self.module.validate_canonical(canonical("x" * 75000)).codepoint_count, 75000)
        self.reject(canonical("x" * 75001), "document_character_limit")

    def test_combining_and_non_bmp_codepoints_are_not_utf16_or_graphemes(self):
        for text in ("😀" * 75000, "e\u0301" * 37500):
            result = self.module.validate_canonical(canonical(text))
            self.assertEqual(result.codepoint_count, 75000)
            self.assertEqual(result.as_dict()["blocks"][0]["spans"][0]["text"], text)
        self.reject(canonical("😀" * 75001), "document_character_limit")
        self.assertEqual(self.module.count_unicode_words("l'été porte-monnaie 42 e\u0301 — 😀 \u0301"), 4)

    def test_unhashable_fields_are_protocol_refusals_and_envelope_is_bounded(self):
        for block in ({"type": []}, {"type": {}}):
            self.reject({**canonical(), "blocks": [block]}, "document_canonical_invalid")
        data = canonical()
        data["blocks"] += [{"type": "page_break"}] * 50000
        self.reject(data, "document_json_envelope_limit")

    def test_unicode_count_and_split_spans_include_all_blocks(self):
        data = canonical()
        data["blocks"] = [
            {"type": "heading", "level": 1, "spans": [span("Bon"), span("jour")]},
            {"type": "paragraph", "spans": [span("été e\u0301 𐐀") ]},
            {"type": "quote", "spans": [span("citation")]},
            {"type": "list", "ordered": False, "items": [[span("liste")]]},
            {"type": "table", "rows": [[[span("cellule")], [span("table")]]]},
            {"type": "page_break"},
        ]
        result = self.module.validate_canonical(data)
        self.assertEqual(result.word_count, 8)
        self.assertEqual(result.codepoint_count, 40)
        self.assertEqual(result.as_dict(), data)
        projected = result.as_dict()
        projected["blocks"].clear()
        self.assertEqual(result.as_dict(), data)

    def test_titles_cells_and_links_cannot_hide_volume(self):
        for block in (
            {"type": "heading", "level": 2, "spans": [span("x" * 75001)]},
            {"type": "table", "rows": [[[span("x" * 75001)]]]},
            {"type": "paragraph", "spans": [dict(text="lien", bold=True, italic=True, link="https://example.invalid/" + "x" * 75000)]},
        ):
            with self.subTest(kind=block["type"]):
                data = canonical()
                data["blocks"] = [block]
                self.reject(data, "document_character_limit")

    def test_schema_is_closed_and_content_complete(self):
        invalid = []
        for field, value in (("image", "x"), ("html", "<script>"), ("macro", "x"), ("command", "x")):
            data = canonical()
            data[field] = value
            invalid.append(data)
        invalid.extend([
            {**canonical(), "schema_version": True},
            {**canonical(), "profile": "another_profile"},
            {**canonical(), "blocks": []},
            {**canonical(), "blocks": [{"type": "paragraph", "spans": []}]},
            {**canonical(), "blocks": [{"type": "table", "rows": [[[span("a")]], [[span("b")], []]]}]},
            canonical("\ud800"), canonical("\x00"), canonical("   "),
        ])
        for data in invalid:
            with self.subTest(index=invalid.index(data)):
                self.reject(data, "document_canonical_invalid")

    def test_passive_links_and_style_preserved_active_references_refused(self):
        data = canonical()
        data["blocks"][0]["spans"] = [dict(text="Lien", bold=True, italic=True, link="https://example.invalid/étude")]
        self.assertEqual(self.module.validate_canonical(data).as_dict(), data)
        for link in ("javascript:alert(1)", "file:///etc/passwd", "data:text/html,x", "https://user:password@example.invalid/x", "https://example.invalid/\n"):
            with self.subTest(scheme=link.split(":")[0]):
                bad = copy.deepcopy(data)
                bad["blocks"][0]["spans"][0]["link"] = link
                self.reject(bad, "document_canonical_invalid")

    def test_json_duplicate_fields_and_nonfinite_values_rejected(self):
        for raw in ('{"schema_version":1,"schema_version":1}', '{"schema_version":NaN}', '{}', ''):
            with self.assertRaises(self.error):
                self.module.read_canonical_json(raw)

    def test_layout_and_final_writer_page_evidence(self):
        contract = importlib.import_module("core.document_workshop_contract")
        self.assertEqual(contract.DOCUMENT_LAYOUT, ("A4", 12, 1.5, 2.5))
        for count in (1, 20):
            self.assertEqual(contract.validate_writer_page_count(count), count)
        for count in (None, "20", True, False, 0, -1, 20.0, [], {}):
            with self.subTest(kind=type(count).__name__):
                with self.assertRaises(self.error) as raised:
                    contract.validate_writer_page_count(count)
                self.assertEqual(raised.exception.reason_code, "document_page_evidence_invalid")
        with self.assertRaises(self.error) as raised:
            contract.validate_writer_page_count(21)
        self.assertEqual(raised.exception.reason_code, "document_page_limit")


class DocumentPathContractTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.workspace_document_paths"), "M0 path interface absent")
        self.module = importlib.import_module("core.workspace_document_paths")
        self.error = importlib.import_module("core.document_workshop_contract").DocumentWorkshopError

    def validate(self, path):
        return self.module.validate_document_path(path, format="markdown")

    def reject(self, path, code):
        with self.assertRaises(self.error) as raised:
            self.validate(path)
        self.assertEqual(raised.exception.reason_code, code)

    def test_eight_directories_are_allowed_ninth_is_refused(self):
        path = "Documents/" + "a/" * 8 + "texte.md"
        self.assertEqual(self.validate(path).relative_path, path)
        self.reject("Documents/" + "a/" * 9 + "texte.md", "document_path_depth_limit")

    def test_segment_codepoints_and_filename_extension_included(self):
        self.validate("Documents/" + "a" * 180 + "/texte.md")
        self.reject("Documents/" + "a" * 181 + "/texte.md", "document_path_segment_limit")
        self.validate("Documents/" + "a" * 177 + ".md")
        self.reject("Documents/" + "a" * 178 + ".md", "document_path_segment_limit")

    def test_segment_utf8_limit_independent_of_codepoints(self):
        self.validate("Documents/" + "é" * 127 + "a/texte.md")
        self.reject("Documents/" + "é" * 128 + "/texte.md", "document_path_segment_limit")
        self.validate("Documents/" + "é" * 126 + ".md")
        self.reject("Documents/" + "é" * 126 + "a.md", "document_path_segment_limit")

    def test_full_relative_path_includes_documents_prefix(self):
        # 10 (Documents/) + 5*(180+1) + 109 (.md included) = 1024 bytes.
        exact = "Documents/" + ("a" * 180 + "/") * 5 + "b" * 106 + ".md"
        self.assertEqual(len(exact.encode("utf-8")), 1024)
        self.validate(exact)
        self.reject(exact[:-3] + "b.md", "document_path_byte_limit")

    def test_french_name_frozen_and_dav_segments_use_same_representation(self):
        path = "Documents/Études/Été e\u0301 — bilan.md"
        result = self.validate(path)
        self.assertEqual(result.relative_path, path)
        self.assertEqual(tuple(unquote(p) for p in result.encoded_relative_path.split("/")), tuple(path.split("/")))
        self.assertEqual(result.dav_segments("Dossier français"), ("Dossier français", *path.split("/")))
        from core.workspace_document_nextcloud_client import NextcloudDocumentClient
        from core.workspace_folder_nextcloud_client import NextcloudFolderClientConfig
        client = NextcloudDocumentClient(NextcloudFolderClientConfig("https://dav.invalid", "synthetic", "synthetic"))
        url = client._url(*result.dav_segments("Dossier français"))
        self.assertTrue(url.endswith(result.encoded_relative_path))
        self.assertNotIn(" ", url)
        equivalent = self.validate("Documents/Études/Été é — BILAN.md")
        self.assertEqual(result.collision_key, equivalent.collision_key)
        self.assertNotEqual(result.relative_path, equivalent.relative_path)

    def test_traversals_encoded_disguised_and_ambiguous_paths_rejected(self):
        for path in (
            "Documents//a.md", "Documents/./a.md", "Documents/../a.md", "/Documents/a.md",
            "Documents/a/", "Documents/a\\b.md", "Documents/%2f.md", "Documents/%252e.md",
            "Documents/a∕b.md", "Documents/a⁄b.md", "Documents/a／b.md", "Documents/．．/a.md",
            "Documents/a\x00.md", "Documents/a\u202e.md", "Documents/a\u200b.md", "Documents/ a.md",
            "Documents/a .md ", "Documents/C:a.md", "documents/a.md", "Elsewhere/Documents/a.md",
        ):
            with self.subTest(index=path):
                self.reject(path, "document_path_invalid")

    def test_formats_closed_and_extension_preserved(self):
        for format, path in (("markdown", "Documents/a.MD"), ("docx", "Documents/a.docx"), ("pdf", "Documents/a.pdf")):
            self.assertEqual(self.module.validate_document_path(path, format=format).relative_path, path)
        for format, path in (("txt", "Documents/a.txt"), ("pdf", "Documents/a.docx"), ("markdown", "Documents/a")):
            with self.assertRaises(self.error):
                self.module.validate_document_path(path, format=format)
        with self.assertRaises(self.error) as raised:
            self.module.validate_document_path("Documents/a.md", format=[])
        self.assertEqual(raised.exception.reason_code, "document_path_invalid")

    def test_unicode_reverse_separators_and_line_paragraph_ambiguities_refused(self):
        for char in ("\u2216", "\u29f9", "\u2028", "\u2029"):
            with self.subTest(codepoint=ord(char)):
                self.reject("Documents/étude" + char + "bilan.md", "document_path_invalid")


if __name__ == "__main__":
    unittest.main()
