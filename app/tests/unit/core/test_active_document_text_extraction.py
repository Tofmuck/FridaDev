from __future__ import annotations

import io
import unittest
import zipfile

from core import active_document_text_extraction as extraction


class ActiveDocumentTextExtractionTest(unittest.TestCase):
    def test_txt_success_extracts_normalized_text_and_metadata(self):
        result = extraction.extract_active_document_text(
            b"  Ligne une\r\nLigne deux  \n",
            filename="note.txt",
            media_type="text/plain",
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.parser, "txt")
        self.assertEqual(result.text, "Ligne une\nLigne deux")
        self.assertEqual(result.chars, len(result.text))
        self.assertEqual(result.bytes, len(b"  Ligne une\r\nLigne deux  \n"))
        self.assertGreater(result.token_estimate, 0)
        self.assertEqual(len(result.sha256_12), 12)
        self.assertEqual(result.to_dict()["text_chars"], result.chars)

    def test_md_success_keeps_markdown_as_plain_text(self):
        result = extraction.extract_active_document_text(
            b"# Titre\n\n- point",
            filename="fiche.md",
            media_type="",
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.parser, "md")
        self.assertEqual(result.text, "# Titre\n\n- point")

    def test_docx_success_extracts_main_body_text(self):
        result = extraction.extract_active_document_text(
            _docx_bytes(("Premier paragraphe", "Deuxieme paragraphe")),
            filename="fiche.docx",
            media_type="",
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.parser, "docx")
        self.assertIn("Premier paragraphe", result.text)
        self.assertIn("Deuxieme paragraphe", result.text)

    def test_odt_success_extracts_content_xml_text(self):
        result = extraction.extract_active_document_text(
            _odt_bytes(("Premier bloc", "Deuxieme bloc")),
            filename="fiche.odt",
            media_type="",
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.parser, "odt")
        self.assertEqual(result.text, "Premier bloc\n\nDeuxieme bloc")

    def test_pdf_success_extracts_textual_pdf(self):
        result = extraction.extract_active_document_text(
            _pdf_bytes(["Tiny PDF text"]),
            filename="fiche.pdf",
            media_type="application/pdf",
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.parser, "pdf")
        self.assertIn("Tiny PDF text", result.text)

    def test_pdf_without_text_is_marked_ocr_required(self):
        result = extraction.extract_active_document_text(
            _pdf_bytes([""]),
            filename="scan.pdf",
            media_type="application/pdf",
        )

        self.assertEqual(result.status, "ocr_required")
        self.assertEqual(result.reason_code, "document_ocr_required")
        self.assertEqual(result.text, "")
        self.assertEqual(result.chars, 0)

    def test_pdf_mixed_text_and_blank_pages_is_not_reported_complete(self):
        result = extraction.extract_active_document_text(
            _pdf_bytes(["Page texte", ""]),
            filename="mixte.pdf",
            media_type="application/pdf",
        )

        self.assertEqual(result.status, "ocr_required")
        self.assertEqual(result.reason_code, "document_ocr_required")
        self.assertEqual(result.text, "")

    def test_unsupported_format_is_explicit(self):
        result = extraction.extract_active_document_text(
            b"{\\rtf1 contenu}",
            filename="note.rtf",
            media_type="application/rtf",
        )

        self.assertEqual(result.status, "unsupported")
        self.assertEqual(result.reason_code, "document_type_unsupported")
        self.assertEqual(result.text, "")

    def test_parse_error_is_explicit(self):
        result = extraction.extract_active_document_text(
            b"not a zip",
            filename="cassé.docx",
            media_type="",
        )

        self.assertEqual(result.status, "parse_error")
        self.assertEqual(result.reason_code, "document_parse_error")
        self.assertEqual(result.text, "")

    def test_empty_file_is_not_success(self):
        result = extraction.extract_active_document_text(
            b"   \n\t",
            filename="vide.txt",
            media_type="text/plain",
        )

        self.assertEqual(result.status, "empty")
        self.assertEqual(result.reason_code, "document_empty_text")
        self.assertEqual(result.text, "")


def _docx_bytes(paragraphs: tuple[str, ...]) -> bytes:
    document_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {paragraphs}
  </w:body>
</w:document>
""".format(
        paragraphs="\n".join(f"<w:p><w:r><w:t>{_xml_escape(text)}</w:t></w:r></w:p>" for text in paragraphs)
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("[Content_Types].xml", "<Types/>")
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _odt_bytes(paragraphs: tuple[str, ...]) -> bytes:
    content_xml = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
  xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
  xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">
  <office:body>
    <office:text>
      {paragraphs}
    </office:text>
  </office:body>
</office:document-content>
""".format(
        paragraphs="\n".join(f"<text:p>{_xml_escape(text)}</text:p>" for text in paragraphs)
    )
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        archive.writestr("content.xml", content_xml)
    return buffer.getvalue()


def _pdf_bytes(page_texts: list[str]) -> bytes:
    objects: list[bytes] = []
    kids = " ".join(f"{3 + index * 2} 0 R" for index in range(len(page_texts)))
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_texts)} >>".encode("ascii"))

    for index, text in enumerate(page_texts):
        page_obj = 3 + index * 2
        content_obj = page_obj + 1
        stream = _pdf_text_stream(text)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 300 144] "
                f"/Resources << /Font << /F1 {3 + len(page_texts) * 2} 0 R >> >> "
                f"/Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        objects.append(b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream")

    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    return _assemble_pdf(objects)


def _pdf_text_stream(text: str) -> bytes:
    if not text:
        return b""
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    return f"BT /F1 12 Tf 72 72 Td ({escaped}) Tj ET".encode("latin-1")


def _assemble_pdf(objects: list[bytes]) -> bytes:
    pdf = b"%PDF-1.4\n"
    offsets = [0]
    for index, obj in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf += f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_start = len(pdf)
    pdf += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    pdf += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        pdf += f"{offset:010d} 00000 n \n".encode("ascii")
    pdf += (
        b"trailer\n"
        + f"<< /Size {len(objects) + 1} /Root 1 0 R >>\n".encode("ascii")
        + b"startxref\n"
        + str(xref_start).encode("ascii")
        + b"\n%%EOF\n"
    )
    return pdf


def _xml_escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    unittest.main()
