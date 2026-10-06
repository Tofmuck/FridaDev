from __future__ import annotations

import importlib
import importlib.util
import unittest

from core.document_canonical import validate_canonical
from core.document_workshop_contract import DocumentWorkshopError
from tests.unit.core.test_document_workshop_canonical_paths import canonical


def span(text, **styles):
    return {"text": text, "bold": False, "italic": False, "link": None, **styles}


class DocumentMarkdownTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(importlib.util.find_spec("core.document_markdown"), "M4 Markdown serializer absent")
        self.module = importlib.import_module("core.document_markdown")

    def serialize(self, blocks):
        data = {**canonical(), "blocks": blocks}
        validated = validate_canonical(data)
        result = self.module.serialize_markdown(validated)
        self.assertEqual(validated.as_dict(), data)
        return result

    def test_heading_paragraph_and_all_style_combinations(self):
        result = self.serialize([
            {"type": "heading", "level": 2, "spans": [span("Titre")]},
            {"type": "paragraph", "spans": [span("normal "), span("gras", bold=True), span(" "),
                                            span("italique", italic=True), span(" "), span("double", bold=True, italic=True)]},
        ])
        self.assertEqual(result, "## Titre\n\nnormal **gras** *italique* ***double***\n")

    def test_adjacent_identically_styled_spans_do_not_make_delimiter_collisions(self):
        result = self.serialize([{"type": "paragraph", "spans": [span("Bon", bold=True), span("jour", bold=True)]}])
        self.assertEqual(result, "**Bonjour**\n")

    def test_adjacent_punctuation_does_not_insert_text_to_force_emphasis(self):
        result = self.serialize([{"type": "paragraph", "spans": [span("a"), span("*b", bold=True)]}])
        # CommonMark may not open emphasis here; preserve text rather than add a
        # space/invisible character. The separate reader-dependent style limit
        # is projected on the M4 card instead of promising full style fidelity.
        self.assertEqual(result, "a**\\*b**\n")

    def test_lists_quotes_and_multiline_text_keep_one_structural_block(self):
        result = self.serialize([
            {"type": "list", "ordered": False, "items": [[span("un\n# faux titre")], [span("deux")]]},
            {"type": "list", "ordered": True, "items": [[span("premier")], [span("second")]]},
            {"type": "quote", "spans": [span("citation\r\n> imbriquée\t!")]},
        ])
        self.assertEqual(result, "- un&#10;\\# faux titre\n- deux\n\n1. premier\n2. second\n\n> citation&#13;&#10;&gt; imbriquée&#9;\\!\n")

    def test_table_preserves_every_cell_without_inventing_a_header(self):
        result = self.serialize([{"type": "table", "rows": [
            [[span("a|b")], []],
            [[span("cellule", bold=True)], [span("multi\nligne")]],
        ]}])
        self.assertEqual(result, "|  |  |\n| --- | --- |\n| a\\|b |  |\n| **cellule** | multi&#10;ligne |\n")

    def test_passive_link_destination_cannot_split_a_table_cell(self):
        result = self.serialize([{"type": "table", "rows": [[[span("lien", link="https://example.invalid/a|b")]]]}])
        self.assertEqual(result, "|  |\n| --- |\n| [lien](<https://example.invalid/a%7Cb>) |\n")

    def test_page_break_is_fixed_marker_with_no_page_count_claim(self):
        result = self.serialize([
            {"type": "paragraph", "spans": [span("avant")]}, {"type": "page_break"},
            {"type": "paragraph", "spans": [span("après")]},
        ])
        self.assertEqual(result, "avant\n\n<!-- frida-page-break -->\n\naprès\n")

    def test_html_images_link_syntax_and_code_are_literal_text(self):
        text = '<script>alert("x")</script> & ![image](https://img.invalid/x) [lien](javascript:x) `code` # titre _em_ **strong**'
        result = self.module.serialize_markdown(validate_canonical(canonical(text)))
        self.assertEqual(result, '&lt;script&gt;alert\\(\\"x\\"\\)&lt;\\/script&gt; &amp; \\!\\[image\\]\\(https\\:\\/\\/img\\.invalid\\/x\\) \\[lien\\]\\(javascript\\:x\\) \\`code\\` \\# titre \\_em\\_ \\*\\*strong\\*\\*\n')
        self.assertNotIn("<script>", result)
        self.assertNotIn("![image]", result)

    def test_passive_link_has_no_breakout_and_preserves_unicode_label(self):
        result = self.serialize([{"type": "paragraph", "spans": [
            span("Lien e\u0301 😀", bold=True, link='https://example.invalid/a>![x](y)\\z?q=&copy;'),
        ]}])
        self.assertEqual(result, '[**Lien e\u0301 😀**](<https://example.invalid/a%3E![x](y)%5Cz?q=&amp;copy;>)\n')

    def test_link_of_whitespace_still_keeps_its_canonical_target(self):
        result = self.serialize([{"type": "paragraph", "spans": [
            span("Texte "), span(" ", link="https://example.invalid/source"),
        ]}])
        self.assertEqual(result, "Texte [ ](<https://example.invalid/source>)\n")

    def test_trailing_spaces_cannot_create_a_markdown_hard_break(self):
        result = self.module.serialize_markdown(validate_canonical(canonical("texte  ")))
        self.assertEqual(result, "texte&#32;&#32;\n")

    def test_non_bmp_combining_spaces_and_text_are_not_truncated_or_normalized(self):
        text = "  e\u0301 😀  " + "x" * 10000
        result = self.module.serialize_markdown(validate_canonical(canonical(text)))
        self.assertEqual(result, "&#32;&#32;e\u0301 😀  " + "x" * 10000 + "\n")

    def test_only_validated_canonical_is_accepted(self):
        for value in (canonical(), None, "texte"):
            with self.assertRaises(DocumentWorkshopError) as raised:
                self.module.serialize_markdown(value)
            self.assertEqual(raised.exception.reason_code, "document_canonical_invalid")


if __name__ == "__main__":
    unittest.main()
