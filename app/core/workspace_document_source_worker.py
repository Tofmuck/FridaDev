"""Fixed binary source extractor; private stdin/stdout protocol, no renderer.

512 MiB address-space and 20 CPU seconds bound parser/decompressor expansion.
The CPU bound is a parsing resource guard, not a preparation wall-clock deadline.
No exceptions, document text or parser warnings go to technical logs.
"""
from __future__ import annotations

import io
import math
from pathlib import Path
import re
import resource
import stat
import sys
import zipfile
from urllib.parse import urlsplit
from xml.etree import ElementTree

MAX_ARCHIVE_BYTES = 64 * 1024 * 1024
MAX_ENTRIES = 4096
MAX_TEXT_BYTES = 40 * 1024 * 1024
WORD = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ODT_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"
ODT_OFFICE = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}"
ODT_TABLE = "{urn:oasis:names:tc:opendocument:xmlns:table:1.0}"
_DOCX_READ = re.compile(r"word/(?:document|header[^/]*|footer[^/]*|footnotes|endnotes)\.xml\Z")
_DOCX_METADATA = re.compile(
    r"(?:\[Content_Types\]\.xml|_rels/\.rels|docProps/(?:core|app|custom)\.xml|"
    r"word/(?:styles|stylesWithEffects|settings|numbering|fontTable|webSettings)\.xml|"
    r"word/theme/[^/]+\.xml|word/_rels/[^/]+\.rels)\Z")


def fail(code):
    raise SystemExit(code)


def xml_root(data):
    if b"\x00" in data or re.search(br"<!\s*(DOCTYPE|ENTITY)\b", data, re.IGNORECASE):
        fail(21)
    try:
        return ElementTree.fromstring(data)
    except (ElementTree.ParseError, ValueError):
        fail(21)


def check_odt_body(root):
    bodies = list(root.iter(ODT_OFFICE + "body"))
    texts = list(root.iter(ODT_OFFICE + "text"))
    if (root.tag != ODT_OFFICE + "document-content" or len(bodies) != 1 or
            bodies != root.findall(ODT_OFFICE + "body") or len(texts) != 1 or list(bodies[0]) != texts):
        fail(23)
    body = texts[0]
    block_tags = {ODT_TEXT + "p", ODT_TEXT + "h"}
    blocks = [node for node in body.iter() if node.tag in block_tags]
    if blocks != [node for node in root.iter() if node.tag in block_tags]:
        fail(23)
    covered = set()
    for block in blocks:
        descendants = list(block.iter())
        if any(node.tag in block_tags for node in descendants[1:]):
            fail(23)
        covered.update(id(node) for node in descendants)
    for node in root.iter():
        repetition = (node.get(ODT_TABLE + "number-rows-repeated") if node.tag == ODT_TABLE + "table-row" else
                      node.get(ODT_TABLE + "number-columns-repeated") if node.tag in {
                          ODT_TABLE + "table-cell", ODT_TABLE + "covered-table-cell"} else None)
        # The historical reader visits each XML paragraph once; it cannot
        # certify the multiplicity of repeated textual rows or cells.
        if (repetition is not None and not re.fullmatch(r"\+?0*1", repetition.strip()) and
                any(text.strip() for text in node.itertext())):
            fail(23)
        if id(node) not in covered and (node in (root, bodies[0], body) or node.tag.startswith(ODT_TEXT)):
            if (node.text or "").strip() or any((child.tail or "").strip() for child in node):
                fail(23)


def check_xml(root, name, kind):
    if kind == "odt" and name == "content.xml":
        check_odt_body(root)
    if kind == "docx" and _DOCX_READ.fullmatch(name):
        basename = name.rsplit("/", 1)[-1]
        expected_root = ("document" if basename == "document.xml" else
                         "hdr" if basename.startswith("header") else
                         "ftr" if basename.startswith("footer") else basename[:-4])
        if root.tag != WORD + expected_root:
            fail(23)
        extracted_nodes = {id(node) for paragraph in root.iter(WORD + "p") for node in paragraph.iter(WORD + "t")}
        if any(id(node) not in extracted_nodes and (node.text or "").strip() for node in root.iter(WORD + "t")):
            fail(23)
    for node in root.iter():
        local = node.tag.rsplit("}", 1)[-1]
        if kind == "docx":
            if node.tag == "{http://schemas.openxmlformats.org/markup-compatibility/2006}AlternateContent":
                fail(23)
            # The historical reader handles only these run children. Other
            # rendered characters/references must not disappear behind w:t.
            if _DOCX_READ.fullmatch(name) and node.tag == WORD + "r":
                supported = {WORD + tag for tag in ("rPr", "t", "tab", "br", "cr", "lastRenderedPageBreak")}
                if any(child.tag not in supported for child in node):
                    fail(23)
            if local in {"altChunk", "instrText", "delText", "drawing", "object", "pict", "txbxContent",
                         "fldSimple", "oMath", "oMathPara", "vanish", "webHidden"}:
                fail(23)
            if not _DOCX_READ.fullmatch(name) and node.tag == WORD + "t" and (node.text or "").strip():
                fail(23)
        else:
            if local in {"image", "object", "object-ole", "frame", "binary-data", "script", "scripts", "forms", "note",
                         "tracked-changes", "annotation"}:
                fail(23)
            if name != "content.xml" and node.tag in {ODT_TEXT + "p", ODT_TEXT + "h"}:
                fail(23)
        if local == "Relationship" and node.get("TargetMode") == "External":
            if not node.get("Type", "").endswith("/hyperlink"):
                fail(23)


def preflight_archive(data, kind):
    total = 0
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_ENTRIES:
            fail(22)
        seen = set()
        for info in infos:
            name = info.filename
            parts = name.removesuffix("/").split("/")
            if (name != info.orig_filename or name in seen or "\\" in name or
                    any(part in {"", ".", ".."} for part in parts) or name.startswith("/") or
                    re.search(r"%[0-9a-fA-F]{2}", name) or ":" in name or
                    any(ord(char) < 32 for char in name) or info.flag_bits & 1 or
                    stat.S_ISLNK(info.external_attr >> 16)):
                fail(21)
            seen.add(name)
            if info.file_size > MAX_ARCHIVE_BYTES - total:
                fail(22)
            chunks = []
            with archive.open(info) as member:
                while True:
                    chunk = member.read(min(65536, MAX_ARCHIVE_BYTES + 1 - total))
                    if not chunk:
                        break
                    total += len(chunk)
                    if total > MAX_ARCHIVE_BYTES:
                        fail(22)
                    if name.endswith((".xml", ".rels")):
                        chunks.append(chunk)
            if info.is_dir():
                continue
            if kind == "docx":
                if not (_DOCX_READ.fullmatch(name) or _DOCX_METADATA.fullmatch(name)):
                    fail(23)
            elif name not in {"mimetype", "META-INF/manifest.xml", "content.xml", "styles.xml", "meta.xml", "settings.xml"}:
                fail(23)
            if name.endswith((".xml", ".rels")):
                check_xml(xml_root(b"".join(chunks)), name, kind)
        if ("word/document.xml" if kind == "docx" else "content.xml") not in seen:
            fail(21)


def check_pdf_local_destination(destination):
    """Validate only the literal shape; never resolve a named/page destination."""
    from pypdf.generic import ArrayObject, IndirectObject, NullObject
    if isinstance(destination, str):
        if not 0 < len(destination) <= 1024 or any(ord(char) < 32 for char in destination):
            fail(23)
        return
    lengths = {"/XYZ": 5, "/Fit": 2, "/FitH": 3, "/FitV": 3, "/FitR": 6,
               "/FitB": 2, "/FitBH": 3, "/FitBV": 3}
    if not isinstance(destination, ArrayObject) or not 2 <= len(destination) <= 6:
        fail(23)
    page, mode = destination[:2]
    if (not isinstance(mode, str) or lengths.get(mode) != len(destination) or
            not (isinstance(page, IndirectObject) or (isinstance(page, int) and page >= 0))):
        fail(23)
    for coordinate in destination[2:]:
        if not isinstance(coordinate, NullObject) and not (
                isinstance(coordinate, (int, float)) and math.isfinite(coordinate)):
            fail(23)


def check_pdf_link(annotation):
    if annotation.get("/Subtype") != "/Link" or any(key in annotation for key in ("/AA", "/OpenAction")):
        fail(23)
    if "/Dest" in annotation:
        if "/A" in annotation:
            fail(23)
        check_pdf_local_destination(annotation.raw_get("/Dest"))
    if "/A" not in annotation:
        return
    action = annotation["/A"]
    if not isinstance(action, dict) or action.get("/Type", "/Action") != "/Action":
        fail(23)
    kind = action.get("/S")
    if kind == "/GoTo" and set(action) <= {"/Type", "/S", "/D"} and "/D" in action:
        check_pdf_local_destination(action.raw_get("/D"))
    elif kind == "/URI" and set(action) <= {"/Type", "/S", "/URI"}:
        uri = action.get("/URI")
        if not isinstance(uri, str) or not 0 < len(uri) <= 4096 or any(ord(char) <= 32 for char in uri):
            fail(23)
        try:
            parsed = urlsplit(uri)
            if parsed.scheme not in {"http", "https"} or not parsed.hostname or parsed.username is not None:
                fail(23)
        except ValueError:
            fail(23)
    else:
        fail(23)


def main():
    resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024,) * 2)
    resource.setrlimit(resource.RLIMIT_CPU, (20, 20))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    # Only the fixed application directory is added; -I ignores PYTHONPATH.
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from core.active_document_text_extraction import extract_active_document_text
    if len(sys.argv) != 2 or sys.argv[1] not in {"docx", "odt", "pdf"}:
        fail(24)
    kind = sys.argv[1]
    data = sys.stdin.buffer.read(MAX_TEXT_BYTES + 1)
    if len(data) > MAX_TEXT_BYTES:
        fail(22)
    if kind in {"docx", "odt"}:
        preflight_archive(data, kind)
    pdf_reader_factory = None
    if kind == "pdf":
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(data), strict=True)
        if reader.is_encrypted:
            fail(24)
        catalog = reader.trailer["/Root"]
        if any(key in catalog for key in ("/AcroForm", "/OpenAction", "/AA")):
            fail(23)
        names = catalog.get("/Names", {})
        if hasattr(names, "get_object"):
            names = names.get_object()
        if any(key in names for key in ("/EmbeddedFiles", "/JavaScript")):
            fail(23)
        for page in reader.pages:
            if "/AA" in page:
                fail(23)
            # Images, forms and annotations are not evidence of complete text.
            # Links remain passive data; they never trigger retrieval.
            resources = page.get("/Resources", {})
            if hasattr(resources, "get_object"):
                resources = resources.get_object()
            if resources.get("/XObject"):
                fail(23)
            contents = page.get_contents()
            if contents is not None and any(operator == b"INLINE IMAGE" for _, operator in contents.operations):
                fail(23)
            for annotation in page.get("/Annots", []):
                check_pdf_link(annotation.get_object())
        pdf_reader_factory = lambda _: reader
    result = extract_active_document_text(data, filename="source." + kind, pdf_reader_factory=pdf_reader_factory)
    if result.status != "complete":
        fail({"document_runtime_unavailable": 26, "document_empty_text": 27,
              "document_ocr_required": 25}.get(result.reason_code, 24))
    encoded = result.text.encode("utf-8")
    if len(encoded) > MAX_TEXT_BYTES:
        fail(22)
    sys.stdout.buffer.write(encoded)


if __name__ == "__main__":
    try:
        main()
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError, NotImplementedError):
        fail(21)
    except Exception:
        fail(24)
