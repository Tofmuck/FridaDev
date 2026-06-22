from __future__ import annotations

"""DOCX and PDF fake/local rendering for Exports V1.

The renderers are dependency-light by design: they keep binary artifacts in
memory for the caller and never write temporary files.
"""

import io
import textwrap
import zipfile
from dataclasses import dataclass
from typing import Any, Callable
from xml.sax.saxutils import escape

from . import workspace_folder_exports
from .workspace_folder_export_markdown_text import render_txt_export
from .workspace_folder_export_sources import ExportSource


DOCX_MIME_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PDF_MIME_TYPE = "application/pdf"
PDF_MAX_PAGES = 100
PDF_LINES_PER_PAGE = 46
PDF_LINE_WIDTH = 92

DependencyChecker = Callable[[str], bool]


@dataclass(frozen=True)
class BinaryExportResult:
    ok: bool
    reason_code: str
    content_bytes: bytes = b""
    mime_type: str = ""
    page_count: int = 0


def render_binary_export(
    export_format: str,
    source: ExportSource,
    *,
    title: Any = "",
    dependency_checker: DependencyChecker | None = None,
) -> BinaryExportResult:
    fmt = workspace_folder_exports.normalize_export_format(export_format)
    if fmt not in {workspace_folder_exports.EXPORT_FORMAT_DOCX, workspace_folder_exports.EXPORT_FORMAT_PDF}:
        return _failure(workspace_folder_exports.REASON_FORMAT_UNSUPPORTED)
    if not _dependency_available(fmt, dependency_checker):
        return _failure(workspace_folder_exports.REASON_DEPENDENCY_UNAVAILABLE)

    text = render_txt_export(source, title=title)
    if not text:
        return _failure(workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED)

    try:
        if fmt == workspace_folder_exports.EXPORT_FORMAT_DOCX:
            return BinaryExportResult(
                ok=True,
                reason_code=workspace_folder_exports.REASON_CREATE_OK,
                content_bytes=_render_docx(text),
                mime_type=DOCX_MIME_TYPE,
            )
        pdf = _render_pdf(text)
        return BinaryExportResult(
            ok=True,
            reason_code=workspace_folder_exports.REASON_CREATE_OK,
            content_bytes=pdf["content_bytes"],
            mime_type=PDF_MIME_TYPE,
            page_count=pdf["page_count"],
        )
    except _TooManyPagesError:
        return _failure(workspace_folder_exports.REASON_TOO_LARGE)
    except _UnsupportedPdfTextError:
        return _failure(workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED)
    except Exception:
        return _failure(workspace_folder_exports.REASON_GENERATION_FAILED_REDACTED)


def runtime_dependency_status() -> dict[str, bool]:
    return {
        workspace_folder_exports.EXPORT_FORMAT_DOCX: True,
        workspace_folder_exports.EXPORT_FORMAT_PDF: True,
    }


def _dependency_available(fmt: str, dependency_checker: DependencyChecker | None) -> bool:
    if dependency_checker is not None:
        try:
            return bool(dependency_checker(fmt))
        except Exception:
            return False
    return bool(runtime_dependency_status().get(fmt))


def _render_docx(text: str) -> bytes:
    paragraphs = text.splitlines() or [""]
    document_xml = _docx_document_xml(paragraphs)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _docx_content_types())
        archive.writestr("_rels/.rels", _docx_rels())
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


def _docx_document_xml(paragraphs: list[str]) -> str:
    body = "\n".join(_docx_paragraph(line) for line in paragraphs)
    return (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">\n'
        f"<w:body>\n{body}\n"
        '<w:sectPr><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" '
        'w:right="1440" w:bottom="1440" w:left="1440"/></w:sectPr>\n'
        "</w:body>\n</w:document>\n"
    )


def _docx_paragraph(text: str) -> str:
    if not text:
        return "<w:p/>"
    return f"<w:p><w:r><w:t>{escape(text)}</w:t></w:r></w:p>"


def _docx_content_types() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
        '<Default Extension="xml" ContentType="application/xml"/>\n'
        '<Override PartName="/word/document.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>\n'
        "</Types>\n"
    )


def _docx_rels() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="word/document.xml"/>\n'
        "</Relationships>\n"
    )


def _render_pdf(text: str) -> dict[str, Any]:
    _assert_pdf_text_supported(text)
    lines = _pdf_lines(text)
    pages = [lines[index : index + PDF_LINES_PER_PAGE] for index in range(0, len(lines), PDF_LINES_PER_PAGE)]
    if len(pages) > PDF_MAX_PAGES:
        raise _TooManyPagesError()
    if not pages:
        pages = [[""]]

    objects: list[bytes] = []
    page_numbers = [4 + index * 2 for index in range(len(pages))]
    kids = " ".join(f"{number} 0 R" for number in page_numbers)
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(pages)} >>".encode("ascii"))
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    for index, page_lines in enumerate(pages):
        page_obj = page_numbers[index]
        content_obj = page_obj + 1
        stream = _pdf_content_stream(page_lines)
        objects.append(
            (
                f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
                f"/Resources << /Font << /F1 3 0 R >> >> /Contents {content_obj} 0 R >>"
            ).encode("ascii")
        )
        objects.append(
            b"<< /Length "
            + str(len(stream)).encode("ascii")
            + b" >>\nstream\n"
            + stream
            + b"\nendstream"
        )
    return {"content_bytes": _pdf_document(objects), "page_count": len(pages)}


def _pdf_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.splitlines():
        line = " ".join(str(raw_line or "").split())
        if not line:
            lines.append("")
            continue
        lines.extend(
            textwrap.wrap(
                line,
                width=PDF_LINE_WIDTH,
                break_long_words=True,
                replace_whitespace=False,
                drop_whitespace=True,
            )
            or [""]
        )
    return lines


def _pdf_content_stream(lines: list[str]) -> bytes:
    commands = ["BT", "/F1 11 Tf", "14 TL", "50 760 Td"]
    for line in lines:
        if line:
            commands.append(f"{_pdf_literal(line)} Tj")
        commands.append("T*")
    commands.append("ET")
    return "\n".join(commands).encode("cp1252")


def _pdf_literal(text: str) -> str:
    encoded = text.encode("cp1252").decode("cp1252")
    return "(" + encoded.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ")"


def _assert_pdf_text_supported(text: str) -> None:
    try:
        text.encode("cp1252")
    except UnicodeEncodeError as exc:
        raise _UnsupportedPdfTextError() from exc


def _pdf_document(objects: list[bytes]) -> bytes:
    output = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n"
    offsets = [0]
    for number, obj in enumerate(objects, start=1):
        offsets.append(len(output))
        output += f"{number} 0 obj\n".encode("ascii") + obj + b"\nendobj\n"
    xref_offset = len(output)
    output += f"xref\n0 {len(objects) + 1}\n".encode("ascii")
    output += b"0000000000 65535 f \n"
    for offset in offsets[1:]:
        output += f"{offset:010d} 00000 n \n".encode("ascii")
    output += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode("ascii")
    return output


def _failure(reason_code: str) -> BinaryExportResult:
    return BinaryExportResult(ok=False, reason_code=reason_code)


class _TooManyPagesError(ValueError):
    pass


class _UnsupportedPdfTextError(ValueError):
    pass
