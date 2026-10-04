"""Synthetic source completeness corpus, using the actual PDF parser."""
import importlib.util
import io
import unittest
import warnings
import zipfile
import zlib

from core.document_workshop_contract import DocumentWorkshopError

WORD = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def archive_bytes(entries):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", UserWarning)
                archive.writestr(name, data)
    return buffer.getvalue()


def document_xml(text="synthetic", extra=""):
    return f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p>{extra}</w:body></w:document>'


def odt_table_xml(*, cell_repeat=None, row_repeat=None, text="synthetic"):
    cell_attribute = f' table:number-columns-repeated="{cell_repeat}"' if cell_repeat is not None else ""
    row_attribute = f' table:number-rows-repeated="{row_repeat}"' if row_repeat is not None else ""
    return ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
            'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
            'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0"><office:body><office:text>'
            f'<text:p>ordinary</text:p><table:table><table:table-row{row_attribute}>'
            f'<table:table-cell{cell_attribute}><text:p>{text}</text:p></table:table-cell>'
            '</table:table-row></table:table></office:text></office:body></office:document-content>')


def pdf_bytes(count=21, *, blank_last=False, encrypted=False):
    from pypdf import PdfWriter
    from pypdf.generic import DictionaryObject, NameObject, DecodedStreamObject
    writer = PdfWriter()
    for index in range(count):
        page = writer.add_blank_page(width=600, height=800)
        font = DictionaryObject({NameObject("/Type"): NameObject("/Font"),
                                 NameObject("/Subtype"): NameObject("/Type1"),
                                 NameObject("/BaseFont"): NameObject("/Helvetica")})
        page[NameObject("/Resources")] = DictionaryObject({NameObject("/Font"): DictionaryObject({
            NameObject("/F1"): writer._add_object(font)})})
        if not blank_last or index != count - 1:
            stream = DecodedStreamObject()
            stream.set_data(f"BT /F1 12 Tf 10 700 Td (Synthetic page {index + 1}) Tj ET".encode())
            page[NameObject("/Contents")] = writer._add_object(stream)
    if encrypted:
        writer.encrypt("synthetic")
    output = io.BytesIO()
    writer.write(output)
    return output.getvalue()


class CompleteDocumentSourceM2Tests(unittest.TestCase):
    def setUp(self):
        name = "core.workspace_document_source_extraction"
        self.assertIsNotNone(importlib.util.find_spec(name), "M2 complete extraction contract absent")
        self.module = __import__(name, fromlist=["extract_complete_source"])

    def extract(self, data, filename):
        return self.module.extract_complete_source(data, filename=filename, media_type="")

    def test_plain_text_and_markdown_preserve_all_literal_whitespace(self):
        for filename in ("source.txt", "source.md", "source.markdown"):
            original = "  first  \r\n\r\n\r\nlast\t\n"
            result = self.extract(original.encode(), filename)
            self.assertEqual(result.status, "complete")
            self.assertEqual(result.text, original)

    def test_actual_pdf_over_twenty_pages_is_extracted_whole(self):
        result = self.extract(pdf_bytes(), "source.pdf")
        self.assertEqual(result.status, "complete")
        for page in range(1, 22):
            self.assertIn(f"Synthetic page {page}", result.text)

    def test_pdf_missing_text_encrypted_and_broken_never_return_partial_complete(self):
        for data in (pdf_bytes(blank_last=True), pdf_bytes(encrypted=True), b"%PDF-1.7\ninvalid"):
            with self.subTest(length=len(data)), self.assertRaises(DocumentWorkshopError):
                self.extract(data, "source.pdf")

    def test_docx_reads_main_headers_and_footnotes_completely(self):
        data = archive_bytes([("word/document.xml", document_xml("main")),
                              ("word/header1.xml", document_xml("header").replace("w:document", "w:hdr")),
                              ("word/footnotes.xml", document_xml("footnote").replace("w:document", "w:footnotes"))])
        result = self.extract(data, "source.docx")
        self.assertEqual(result.text, "main\n\nheader\n\nfootnote")

    def test_g_r2_odt_repeated_text_cell_or_row_refuses_entire_source(self):
        for attributes in ({"cell_repeat": "3"}, {"row_repeat": "3"}):
            with self.subTest(attributes=attributes), self.assertRaisesRegex(
                    DocumentWorkshopError, "^document_extraction_incomplete$"):
                self.extract(archive_bytes([("content.xml", odt_table_xml(**attributes))]), "source.odt")

    def test_g_r2_odt_ordinary_single_and_empty_repeated_cells_preserve_text(self):
        for attributes, expected in (({}, "ordinary\n\nsynthetic"),
                                     ({"cell_repeat": "1", "row_repeat": "1"}, "ordinary\n\nsynthetic"),
                                     ({"cell_repeat": "3", "row_repeat": "3", "text": ""}, "ordinary")):
            with self.subTest(attributes=attributes):
                result = self.extract(archive_bytes([("content.xml", odt_table_xml(**attributes))]), "source.odt")
                self.assertEqual(result.status, "complete")
                self.assertEqual(result.text, expected)

    def test_g_r3_docx_exclusive_choice_and_fallback_refuse_entire_source(self):
        xml = (f'<w:document xmlns:w="{WORD}" '
               'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
               'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml"><w:body><w:p>'
               '<w:r><w:t>ordinary</w:t></w:r><mc:AlternateContent><mc:Choice Requires="w14">'
               '<w:r><w:t>choice</w:t></w:r></mc:Choice><mc:Fallback><w:r><w:t>fallback</w:t></w:r>'
               '</mc:Fallback></mc:AlternateContent></w:p></w:body></w:document>')
        with self.assertRaisesRegex(DocumentWorkshopError, "^document_extraction_incomplete$"):
            self.extract(archive_bytes([("word/document.xml", xml)]), "source.docx")

    def test_r1_docx_unsupported_rendered_run_nodes_refuse_retained_ordinary_text(self):
        for tag in ("noBreakHyphen", "sym", "softHyphen", "pgNum", "footnoteReference",
                    "endnoteReference", "annotationRef", "ptab", "dayShort", "yearLong",
                    "ruby", "contentPart", "delInstrText"):
            xml = (f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:t>left</w:t>'
                   f'<w:{tag}/><w:t>right</w:t></w:r></w:p></w:body></w:document>')
            with self.subTest(tag=tag), self.assertRaisesRegex(DocumentWorkshopError, "^document_extraction_incomplete$"):
                self.extract(archive_bytes([("word/document.xml", xml)]), "source.docx")

    def test_r1_docx_supported_run_text_spacing_and_format_properties_remain_readable(self):
        xml = (f'<w:document xmlns:w="{WORD}"><w:body><w:p><w:r><w:rPr><w:b/></w:rPr>'
               '<w:t>left</w:t><w:tab/><w:t>middle</w:t><w:br/><w:t>right</w:t>'
               '</w:r></w:p></w:body></w:document>')
        self.assertEqual(self.extract(archive_bytes([("word/document.xml", xml)]), "source.docx").text,
                         "left\tmiddle\nright")

    def test_r2_odt_duplicate_or_out_of_body_text_never_returns_partial_complete(self):
        prefix = ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                  'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">')
        text = '<office:text><text:p>first</text:p></office:text>'
        other = '<office:text><text:p>second</text:p></office:text>'
        cases = [f'<office:body>{text}{other}</office:body>',
                 f'<office:body>{text}</office:body><text:p>outside</text:p>',
                 f'<office:body>{text}</office:body><text:span>outside</text:span>',
                 f'<office:body>{text}</office:body><office:body>{other}</office:body>',
                 f'{text}<office:body>{other}</office:body>',
                 '<office:body><office:text><text:p>first</text:p>outside</office:text></office:body>']
        for body in cases:
            with self.subTest(shape=cases.index(body)), self.assertRaisesRegex(DocumentWorkshopError, "^document_extraction_incomplete$"):
                self.extract(archive_bytes([("content.xml", prefix + body + '</office:document-content>')]), "source.odt")

    def test_r3_pdf_page_and_link_actions_are_refused_before_complete(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ArrayObject, DictionaryObject, NameObject, TextStringObject
        for case in ("page_aa", "link_aa", "javascript", "launch", "next", "remote", "active_uri"):
            writer = PdfWriter()
            writer.add_page(PdfReader(io.BytesIO(pdf_bytes(1))).pages[0])
            page = writer.pages[0]
            dangerous = DictionaryObject({NameObject("/S"): NameObject("/JavaScript"),
                                          NameObject("/JS"): TextStringObject("synthetic()")})
            link = DictionaryObject({NameObject("/Subtype"): NameObject("/Link")})
            if case == "page_aa":
                page[NameObject("/AA")] = DictionaryObject({NameObject("/O"): dangerous})
            elif case == "link_aa":
                link[NameObject("/AA")] = DictionaryObject({NameObject("/E"): dangerous})
            elif case == "javascript":
                link[NameObject("/A")] = dangerous
            elif case == "launch":
                link[NameObject("/A")] = DictionaryObject({NameObject("/S"): NameObject("/Launch"),
                    NameObject("/F"): TextStringObject("synthetic")})
            elif case == "remote":
                link[NameObject("/A")] = DictionaryObject({NameObject("/S"): NameObject("/GoToR"),
                    NameObject("/F"): TextStringObject("synthetic.pdf"), NameObject("/D"): TextStringObject("page")})
            else:
                action = DictionaryObject({NameObject("/S"): NameObject("/URI"),
                    NameObject("/URI"): TextStringObject("javascript:synthetic()" if case == "active_uri" else "https://example.invalid/")})
                if case == "next":
                    action[NameObject("/Next")] = dangerous
                link[NameObject("/A")] = action
            page[NameObject("/Annots")] = ArrayObject([writer._add_object(link)])
            output = io.BytesIO()
            writer.write(output)
            with self.subTest(case=case), self.assertRaisesRegex(DocumentWorkshopError, "^document_extraction_incomplete$"):
                self.extract(output.getvalue(), "source.pdf")

    def test_r3_passive_pdf_http_and_local_links_remain_data_without_destination_fetch(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import ArrayObject, DictionaryObject, NameObject, NumberObject, TextStringObject
        cases = [{"/A": DictionaryObject({NameObject("/S"): NameObject("/URI"),
                     NameObject("/URI"): TextStringObject("https://example.invalid/passive")})},
                 {"/A": DictionaryObject({NameObject("/S"): NameObject("/GoTo"),
                     NameObject("/D"): TextStringObject("local-name")})},
                 {"/Dest": ArrayObject([NumberObject(0), NameObject("/Fit")])}]
        for values in cases:
            writer = PdfWriter()
            writer.add_page(PdfReader(io.BytesIO(pdf_bytes(1))).pages[0])
            link = DictionaryObject({NameObject("/Subtype"): NameObject("/Link"),
                                     **{NameObject(key): value for key, value in values.items()}})
            writer.pages[0][NameObject("/Annots")] = ArrayObject([writer._add_object(link)])
            output = io.BytesIO()
            writer.write(output)
            self.assertEqual(self.extract(output.getvalue(), "source.pdf").text, "Synthetic page 1")

    def test_docx_missing_main_or_detectably_omitted_parts_are_refused(self):
        cases = [[("word/header1.xml", document_xml())],
                 [("word/document.xml", document_xml()), ("word/vbaProject.bin", b"macro")],
                 [("word/document.xml", document_xml()), ("word/media/image1.png", b"image")],
                 [("word/document.xml", document_xml()), ("word/settings.xml", b"")],
                 [("word/document.xml", document_xml(extra="<w:altChunk/>"))],
                 [("word/document.xml", document_xml().replace("w:document", "w:hdr"))],
                 [("word/document.xml", document_xml(extra="<w:t>omitted</w:t>"))],
                 [("word/document.xml", document_xml(extra="<w:p><w:r><w:instrText>hidden</w:instrText></w:r></w:p>"))]]
        for entries in cases:
            with self.subTest(parts=len(entries)), self.assertRaises(DocumentWorkshopError):
                self.extract(archive_bytes(entries), "source.docx")

    def test_archives_reject_traversal_symlink_duplicates_dtd_corrupt_and_entry_overflow(self):
        symlink = zipfile.ZipInfo("word/link")
        symlink.create_system = 3
        symlink.external_attr = 0o120777 << 16
        cases = [[("../word/document.xml", document_xml())], [(symlink, "target")],
                 [("word/document.xml", document_xml()), ("word/document.xml", document_xml())],
                 [("word/document.xml", '<!DOCTYPE x [<!ENTITY a "x">]>' + document_xml("&a;"))],
                 [(f"p{i}", "") for i in range(4097)]]
        for entries in cases:
            with self.subTest(parts=len(entries)), self.assertRaises(DocumentWorkshopError):
                self.extract(archive_bytes(entries), "source.docx")
        with self.assertRaises(DocumentWorkshopError):
            self.extract(b"broken", "source.docx")

    def test_cumulative_expansion_is_checked_by_reading_real_compressed_members(self):
        data = archive_bytes([("word/document.xml", document_xml()), ("oversized.bin", b"x" * (64 * 1024 * 1024))])
        with self.assertRaises(DocumentWorkshopError):
            self.extract(data, "source.docx")

    def test_empty_invalid_text_and_unsupported_are_explicit_refusals(self):
        for data, filename in ((b"", "source.txt"), (b"\xff", "source.txt"), (b"\x00x", "source.txt"),
                               (b"hello", "source.exe"), (b" \n", "source.md")):
            with self.subTest(filename=filename), self.assertRaises(DocumentWorkshopError):
                self.extract(data, filename)

    def test_plain_source_limit_refuses_whole_input_without_mutation(self):
        original = b"x" * (40 * 1024 * 1024 + 1)
        with self.assertRaises(DocumentWorkshopError) as error:
            self.extract(original, "source.txt")
        self.assertEqual(error.exception.reason_code, "document_source_limit")
        self.assertEqual(len(original), 40 * 1024 * 1024 + 1)

    def test_odt_text_is_complete_but_xml_space_expansion_is_bounded(self):
        def odt(count):
            xml = ('<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                   'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"><office:body><office:text>'
                   f'<text:p>A<text:s text:c="{count}"/>B</text:p></office:text></office:body></office:document-content>')
            return archive_bytes([("content.xml", xml)])
        self.assertEqual(self.extract(odt(2), "source.odt").text, "A  B")
        with self.assertRaises(DocumentWorkshopError):
            self.extract(odt(40 * 1024 * 1024 + 1), "source.odt")

    def test_pdf_parser_refuses_repair_partial_file_and_detectable_omitted_images(self):
        good = pdf_bytes(1)
        with self.assertRaises(DocumentWorkshopError):
            self.extract(good[:good.rfind(b"%%EOF")], "source.pdf")
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject, DictionaryObject, DecodedStreamObject, NumberObject
        writer = PdfWriter()
        writer.add_page(PdfReader(io.BytesIO(good)).pages[0])
        image = DecodedStreamObject()
        image.set_data(b"\xff\x00\x00")
        image.update({NameObject("/Type"): NameObject("/XObject"), NameObject("/Subtype"): NameObject("/Image"),
                      NameObject("/Width"): NumberObject(1), NameObject("/Height"): NumberObject(1),
                      NameObject("/ColorSpace"): NameObject("/DeviceRGB"), NameObject("/BitsPerComponent"): NumberObject(8)})
        writer.pages[0]["/Resources"][NameObject("/XObject")] = DictionaryObject({NameObject("/Image1"): writer._add_object(image)})
        mixed = io.BytesIO()
        writer.write(mixed)
        with self.assertRaises(DocumentWorkshopError) as error:
            self.extract(mixed.getvalue(), "source.pdf")
        self.assertEqual(error.exception.reason_code, "document_extraction_incomplete")

    def test_pdf_inline_image_is_not_silently_omitted_from_text(self):
        from pypdf import PdfReader, PdfWriter
        from pypdf.generic import NameObject, DecodedStreamObject
        writer = PdfWriter()
        writer.add_page(PdfReader(io.BytesIO(pdf_bytes(1))).pages[0])
        stream = DecodedStreamObject()
        stream.set_data(b"BT /F1 12 Tf 10 700 Td (Text) Tj ET\nBI /W 1 /H 1 /CS /RGB /BPC 8 ID \xff\x00\x00 EI\n")
        writer.pages[0][NameObject("/Contents")] = writer._add_object(stream)
        output = io.BytesIO()
        writer.write(output)
        with self.assertRaises(DocumentWorkshopError) as error:
            self.extract(output.getvalue(), "source.pdf")
        self.assertEqual(error.exception.reason_code, "document_extraction_incomplete")

    def test_pdf_decompression_cannot_escape_process_memory_guard(self):
        from pypdf import PdfWriter
        from pypdf.generic import EncodedStreamObject, NameObject
        writer = PdfWriter()
        page = writer.add_blank_page(width=600, height=800)
        compressor = zlib.compressobj()
        fragments = [compressor.compress(b"x" * (1024 * 1024)) for _ in range(576)]
        fragments.append(compressor.flush())
        stream = EncodedStreamObject()
        stream._data = b"".join(fragments)
        stream[NameObject("/Filter")] = NameObject("/FlateDecode")
        page[NameObject("/Contents")] = writer._add_object(stream)
        target = io.BytesIO()
        writer.write(target)
        with self.assertRaises(DocumentWorkshopError):
            self.extract(target.getvalue(), "source.pdf")
