from __future__ import annotations

"""Text extraction for active conversation documents.

This module only turns uploaded file bytes into normalized text plus compact
metadata. It does not activate documents, write state, inject prompts, or expose
observability surfaces.
"""

import hashlib
import io
import mimetypes
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Optional
from xml.etree import ElementTree

from .token_counter import estimate_text_tokens

STATUS_COMPLETE = "complete"
STATUS_UNSUPPORTED = "unsupported"
STATUS_PARSE_ERROR = "parse_error"
STATUS_EMPTY = "empty"
STATUS_OCR_REQUIRED = "ocr_required"

REASON_UNSUPPORTED = "document_type_unsupported"
REASON_PARSE_ERROR = "document_parse_error"
REASON_EMPTY = "document_empty_text"
REASON_OCR_REQUIRED = "document_ocr_required"
REASON_RUNTIME_UNAVAILABLE = "document_runtime_unavailable"

KIND_TXT = "txt"
KIND_MD = "md"
KIND_PDF = "pdf"
KIND_DOCX = "docx"
KIND_ODT = "odt"

SUPPORTED_EXTENSIONS = {
    ".txt": KIND_TXT,
    ".md": KIND_MD,
    ".markdown": KIND_MD,
    ".pdf": KIND_PDF,
    ".docx": KIND_DOCX,
    ".odt": KIND_ODT,
}

SUPPORTED_MEDIA_TYPES = {
    "text/plain": KIND_TXT,
    "text/markdown": KIND_MD,
    "application/pdf": KIND_PDF,
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": KIND_DOCX,
    "application/vnd.oasis.opendocument.text": KIND_ODT,
}

WORD_NS = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
ODT_OFFICE_TEXT = "{urn:oasis:names:tc:opendocument:xmlns:office:1.0}text"
ODT_TEXT_NS = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


@dataclass(frozen=True)
class ActiveDocumentTextExtraction:
    filename: str
    media_type: str
    source_extension: str
    parser: str
    status: str
    reason_code: str
    text: str
    chars: int
    bytes: int
    token_estimate: int
    sha256_12: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "filename": self.filename,
            "media_type": self.media_type,
            "source_extension": self.source_extension,
            "parser": self.parser,
            "status": self.status,
            "reason_code": self.reason_code,
            "text": self.text,
            "chars": self.chars,
            "text_chars": self.chars,
            "bytes": self.bytes,
            "byte_size": self.bytes,
            "token_estimate": self.token_estimate,
            "sha256_12": self.sha256_12,
            "text_sha256_12": self.sha256_12,
            "warnings": list(self.warnings),
        }


def extract_active_document_text(
    content: bytes,
    *,
    filename: str,
    media_type: str = "",
    pdf_reader_factory: Optional[Callable[[io.BytesIO], Any]] = None,
) -> ActiveDocumentTextExtraction:
    """Extract complete text for a supported active document.

    The result is ``complete`` only when the parser can treat the whole file as
    textually extracted. When that cannot be established, the result is an
    explicit non-complete status and the returned text is empty.
    """

    data = bytes(content or b"")
    safe_filename = _safe_filename(filename)
    extension = _detect_extension(safe_filename)
    normalized_media_type = _normalize_media_type(media_type, safe_filename)
    kind = _detect_kind(extension, normalized_media_type)

    if not kind:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser="unsupported",
            status=STATUS_UNSUPPORTED,
            reason_code=REASON_UNSUPPORTED,
            byte_size=len(data),
        )

    if not data:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser=kind,
            status=STATUS_EMPTY,
            reason_code=REASON_EMPTY,
            byte_size=0,
        )

    try:
        if kind == KIND_TXT:
            text = _extract_utf_text(data)
        elif kind == KIND_MD:
            text = _extract_utf_text(data)
        elif kind == KIND_DOCX:
            text = _extract_docx_text(data)
        elif kind == KIND_ODT:
            text = _extract_odt_text(data)
        elif kind == KIND_PDF:
            text = _extract_pdf_text(data, pdf_reader_factory=pdf_reader_factory)
        else:  # pragma: no cover - guarded by _detect_kind.
            return _non_complete(
                filename=safe_filename,
                media_type=normalized_media_type,
                source_extension=extension,
                parser="unsupported",
                status=STATUS_UNSUPPORTED,
                reason_code=REASON_UNSUPPORTED,
                byte_size=len(data),
            )
    except _OcrRequiredError as exc:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser=kind,
            status=STATUS_OCR_REQUIRED,
            reason_code=REASON_OCR_REQUIRED,
            byte_size=len(data),
            warnings=(str(exc),) if str(exc) else (),
        )
    except _RuntimeUnavailableError as exc:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser=kind,
            status=STATUS_PARSE_ERROR,
            reason_code=REASON_RUNTIME_UNAVAILABLE,
            byte_size=len(data),
            warnings=(str(exc),) if str(exc) else (),
        )
    except Exception as exc:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser=kind,
            status=STATUS_PARSE_ERROR,
            reason_code=REASON_PARSE_ERROR,
            byte_size=len(data),
            warnings=(type(exc).__name__,),
        )

    normalized = _normalize_extracted_text(text)
    if not normalized:
        return _non_complete(
            filename=safe_filename,
            media_type=normalized_media_type,
            source_extension=extension,
            parser=kind,
            status=STATUS_EMPTY,
            reason_code=REASON_EMPTY,
            byte_size=len(data),
        )
    return _complete(
        filename=safe_filename,
        media_type=normalized_media_type,
        source_extension=extension,
        parser=kind,
        byte_size=len(data),
        text=normalized,
    )


def _complete(
    *,
    filename: str,
    media_type: str,
    source_extension: str,
    parser: str,
    byte_size: int,
    text: str,
) -> ActiveDocumentTextExtraction:
    return ActiveDocumentTextExtraction(
        filename=filename,
        media_type=media_type,
        source_extension=source_extension,
        parser=parser,
        status=STATUS_COMPLETE,
        reason_code="",
        text=text,
        chars=len(text),
        bytes=byte_size,
        token_estimate=estimate_text_tokens(text),
        sha256_12=_sha256_12(text),
    )


def _non_complete(
    *,
    filename: str,
    media_type: str,
    source_extension: str,
    parser: str,
    status: str,
    reason_code: str,
    byte_size: int,
    warnings: Iterable[str] = (),
) -> ActiveDocumentTextExtraction:
    return ActiveDocumentTextExtraction(
        filename=filename,
        media_type=media_type,
        source_extension=source_extension,
        parser=parser,
        status=status,
        reason_code=reason_code,
        text="",
        chars=0,
        bytes=byte_size,
        token_estimate=0,
        sha256_12="",
        warnings=tuple(str(item) for item in warnings if item),
    )


def _safe_filename(filename: str) -> str:
    name = Path(str(filename or "document")).name.strip()
    return name or "document"


def _detect_extension(filename: str) -> str:
    suffix = Path(filename).suffix.lower()
    return suffix if suffix in SUPPORTED_EXTENSIONS else suffix


def _normalize_media_type(media_type: str, filename: str) -> str:
    raw = str(media_type or "").split(";", 1)[0].strip().lower()
    if raw:
        return raw
    guessed, _ = mimetypes.guess_type(filename)
    return str(guessed or "").strip().lower()


def _detect_kind(extension: str, media_type: str) -> str:
    if extension in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[extension]
    return SUPPORTED_MEDIA_TYPES.get(media_type, "")


def _extract_utf_text(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("unsupported_text_encoding")


def _extract_docx_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = archive.namelist()
        doc_names = ["word/document.xml"]
        doc_names.extend(sorted(name for name in names if name.startswith("word/header") and name.endswith(".xml")))
        doc_names.extend(sorted(name for name in names if name.startswith("word/footer") and name.endswith(".xml")))
        doc_names.extend(name for name in ("word/footnotes.xml", "word/endnotes.xml") if name in names)

        paragraphs: list[str] = []
        for name in doc_names:
            if name not in names:
                continue
            root = ElementTree.fromstring(archive.read(name))
            paragraphs.extend(_extract_docx_paragraphs(root))
    return "\n\n".join(paragraph for paragraph in paragraphs if paragraph.strip())


def _extract_docx_paragraphs(root: ElementTree.Element) -> list[str]:
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{WORD_NS}p"):
        fragments: list[str] = []
        for node in paragraph.iter():
            if node.tag == f"{WORD_NS}t" and node.text:
                fragments.append(node.text)
            elif node.tag == f"{WORD_NS}tab":
                fragments.append("\t")
            elif node.tag in (f"{WORD_NS}br", f"{WORD_NS}cr"):
                fragments.append("\n")
        text = "".join(fragments).strip()
        if text:
            paragraphs.append(text)
    return paragraphs


def _extract_odt_text(data: bytes) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        try:
            content = archive.read("content.xml")
        except KeyError as exc:
            raise ValueError("missing_odt_content_xml") from exc

    root = ElementTree.fromstring(content)
    office_text = root.find(f".//{ODT_OFFICE_TEXT}")
    if office_text is None:
        return ""

    blocks: list[str] = []
    for node in office_text.iter():
        if node.tag in (f"{ODT_TEXT_NS}p", f"{ODT_TEXT_NS}h"):
            text = "".join(node.itertext()).strip()
            if text:
                blocks.append(text)
    return "\n\n".join(blocks)


def _extract_pdf_text(
    data: bytes,
    *,
    pdf_reader_factory: Optional[Callable[[io.BytesIO], Any]] = None,
) -> str:
    reader_factory = pdf_reader_factory
    if reader_factory is None:
        try:
            from pypdf import PdfReader
        except ImportError as exc:  # pragma: no cover - exercised without dependency only.
            raise _RuntimeUnavailableError("pypdf_unavailable") from exc
        reader_factory = PdfReader

    reader = reader_factory(io.BytesIO(data))
    if bool(getattr(reader, "is_encrypted", False)):
        raise ValueError("encrypted_pdf")

    pages = list(getattr(reader, "pages", []) or [])
    if not pages:
        return ""

    page_texts: list[str] = []
    missing_text_pages = 0
    for page in pages:
        extracted = page.extract_text() or ""
        normalized_page = _normalize_extracted_text(extracted)
        if not normalized_page:
            missing_text_pages += 1
        page_texts.append(normalized_page)

    if missing_text_pages:
        raise _OcrRequiredError("pdf_page_without_text")
    return "\n\n".join(page_texts)


def _normalize_extracted_text(text: str) -> str:
    unified = str(text or "").replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "")
    lines = [line.rstrip() for line in unified.split("\n")]
    collapsed: list[str] = []
    blank_seen = False
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if not blank_seen:
                collapsed.append("")
            blank_seen = True
            continue
        collapsed.append(line)
        blank_seen = False
    return "\n".join(collapsed).strip()


def _sha256_12(text: str) -> str:
    if not text:
        return ""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]


class _OcrRequiredError(Exception):
    pass


class _RuntimeUnavailableError(Exception):
    pass
