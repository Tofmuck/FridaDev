from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


def _resolve_app_dir() -> Path:
    for parent in Path(__file__).resolve().parents:
        if (parent / "web").exists() and (parent / "server.py").exists():
            return parent
    raise RuntimeError("Unable to resolve APP_DIR from test path")


APP_DIR = _resolve_app_dir()
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tools import web_pdf_reader


def _tiny_pdf(text: str = "Frida web PDF reader fixture") -> bytes:
    escaped = text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
    stream = f"BT /F1 12 Tf 72 720 Td ({escaped}) Tj ET".encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>"
        ),
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    chunks = [b"%PDF-1.4\n"]
    offsets = [0]
    for index, obj in enumerate(objects, 1):
        offsets.append(sum(len(chunk) for chunk in chunks))
        chunks.append(f"{index} 0 obj\n".encode("ascii") + obj + b"\nendobj\n")
    xref_offset = sum(len(chunk) for chunk in chunks)
    chunks.append(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    chunks.append(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        chunks.append(f"{offset:010d} 00000 n \n".encode("ascii"))
    chunks.append(
        (
            f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
            f"startxref\n{xref_offset}\n%%EOF\n"
        ).encode("ascii")
    )
    return b"".join(chunks)


class _FakeResponse:
    def __init__(
        self,
        *,
        headers: dict[str, str] | None = None,
        content: bytes = b"",
        status_code: int = 200,
    ):
        self.headers = headers or {}
        self.content = content
        self.status_code = status_code

    def raise_for_status(self) -> None:
        return None

    def iter_content(self, chunk_size: int = 65536):
        for index in range(0, len(self.content), chunk_size):
            yield self.content[index:index + chunk_size]


def _public_getaddrinfo(*_args, **_kwargs):
    return [(None, None, None, "", ("93.184.216.34", 0))]


class _FakeRequests:
    def __init__(self, *, head: _FakeResponse | Exception, get: _FakeResponse | Exception):
        self._head = head
        self._get = get
        self.calls: list[tuple[str, str]] = []

    def head(self, url: str, **_kwargs):
        self.calls.append(("head", url))
        if isinstance(self._head, Exception):
            raise self._head
        return self._head

    def get(self, url: str, **_kwargs):
        self.calls.append(("get", url))
        if isinstance(self._get, Exception):
            raise self._get
        return self._get


class WebPdfReaderTests(unittest.TestCase):
    def test_detects_pdf_url_extension(self) -> None:
        self.assertTrue(web_pdf_reader.is_pdf_url_candidate("https://example.com/report.PDF?download=1"))
        self.assertFalse(web_pdf_reader.is_pdf_url_candidate("https://example.com/report.html"))

    def test_reads_tiny_text_pdf_without_leaking_text_in_repr_or_observability(self) -> None:
        pdf_text = "Frida PDF text fixture"
        original_page_count = web_pdf_reader._pdf_page_count
        original_extract = web_pdf_reader.active_document_text_extraction.extract_active_document_text
        web_pdf_reader._pdf_page_count = lambda _data: 1
        web_pdf_reader.active_document_text_extraction.extract_active_document_text = lambda *_args, **_kwargs: SimpleNamespace(
            status=web_pdf_reader.active_document_text_extraction.STATUS_COMPLETE,
            text=pdf_text,
            reason_code="",
        )
        try:
            result = web_pdf_reader.read_pdf_bytes(_tiny_pdf(pdf_text), url="https://example.com/doc.pdf")
        finally:
            web_pdf_reader._pdf_page_count = original_page_count
            web_pdf_reader.active_document_text_extraction.extract_active_document_text = original_extract

        self.assertEqual(result.status, "success")
        self.assertEqual(result.pages, 1)
        self.assertIn(pdf_text, result.text)
        self.assertGreater(result.chars, 0)
        self.assertNotIn(pdf_text, repr(result))
        serialized = json.dumps(result.to_observability(), sort_keys=True)
        self.assertNotIn(pdf_text, serialized)

    def test_download_is_bounded_by_content_length(self) -> None:
        fake = _FakeRequests(
            head=_FakeResponse(headers={"Content-Type": "application/pdf", "Content-Length": "999"}),
            get=_FakeResponse(headers={"Content-Type": "application/pdf"}, content=b""),
        )
        original_getaddrinfo = web_pdf_reader.socket.getaddrinfo
        web_pdf_reader.socket.getaddrinfo = _public_getaddrinfo

        try:
            result = web_pdf_reader.read_pdf_url(
                "https://example.com/doc.pdf",
                requests_module=fake,
                max_bytes=10,
            )
        finally:
            web_pdf_reader.socket.getaddrinfo = original_getaddrinfo

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "web_pdf_too_large")
        self.assertEqual(fake.calls, [("head", "https://example.com/doc.pdf")])

    def test_blocks_internal_urls_before_network_requests(self) -> None:
        blocked_urls = [
            "file:///tmp/doc.pdf",
            "http://localhost/doc.pdf",
            "http://127.0.0.1/doc.pdf",
            "http://10.0.0.4/doc.pdf",
            "http://172.18.0.5/doc.pdf",
            "http://192.168.1.10/doc.pdf",
            "http://169.254.169.254/latest/meta-data/doc.pdf",
            "http://224.0.0.1/doc.pdf",
            "http://0.0.0.0/doc.pdf",
            "http://crawl4ai/doc.pdf",
            "http://service.internal/doc.pdf",
            "http://host.docker.internal/doc.pdf",
        ]
        for url in blocked_urls:
            with self.subTest(url=url):
                fake = _FakeRequests(
                    head=AssertionError("head should not be called"),
                    get=AssertionError("get should not be called"),
                )
                result = web_pdf_reader.read_pdf_url(url, requests_module=fake)
                self.assertEqual(result.status, "error")
                self.assertEqual(result.reason_code, "web_pdf_url_blocked_internal")
                self.assertFalse(result.attempted)
                self.assertEqual(fake.calls, [])

    def test_blocks_hostname_that_resolves_to_private_address(self) -> None:
        fake = _FakeRequests(
            head=AssertionError("head should not be called"),
            get=AssertionError("get should not be called"),
        )
        original_getaddrinfo = web_pdf_reader.socket.getaddrinfo
        web_pdf_reader.socket.getaddrinfo = lambda *_args, **_kwargs: [
            (None, None, None, "", ("172.18.0.5", 0))
        ]
        try:
            result = web_pdf_reader.read_pdf_url("https://public-looking.example/doc.pdf", requests_module=fake)
        finally:
            web_pdf_reader.socket.getaddrinfo = original_getaddrinfo

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "web_pdf_url_blocked_internal")
        self.assertFalse(result.attempted)
        self.assertEqual(fake.calls, [])

    def test_blocks_redirect_to_internal_address(self) -> None:
        fake = _FakeRequests(
            head=_FakeResponse(headers={"Content-Type": "application/pdf", "Content-Length": "0"}),
            get=_FakeResponse(
                headers={"Location": "http://127.0.0.1/private.pdf"},
                status_code=302,
            ),
        )
        original_getaddrinfo = web_pdf_reader.socket.getaddrinfo
        web_pdf_reader.socket.getaddrinfo = _public_getaddrinfo
        try:
            result = web_pdf_reader.read_pdf_url(
                "https://example.com/doc.pdf",
                requests_module=fake,
            )
        finally:
            web_pdf_reader.socket.getaddrinfo = original_getaddrinfo

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "web_pdf_url_blocked_internal")
        self.assertEqual(fake.calls, [("head", "https://example.com/doc.pdf"), ("get", "https://example.com/doc.pdf")])

    def test_page_limit_is_enforced_before_text_injection(self) -> None:
        original_page_count = web_pdf_reader._pdf_page_count
        web_pdf_reader._pdf_page_count = lambda _data: 3
        try:
            result = web_pdf_reader.read_pdf_bytes(
                _tiny_pdf("too many pages"),
                url="https://example.com/doc.pdf",
                max_pages=2,
            )
        finally:
            web_pdf_reader._pdf_page_count = original_page_count

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "web_pdf_too_many_pages")
        self.assertEqual(result.pages, 3)
        self.assertEqual(result.text, "")

    def test_chars_limit_truncates_injected_text(self) -> None:
        original_page_count = web_pdf_reader._pdf_page_count
        original_extract = web_pdf_reader.active_document_text_extraction.extract_active_document_text
        web_pdf_reader._pdf_page_count = lambda _data: 1
        web_pdf_reader.active_document_text_extraction.extract_active_document_text = lambda *_args, **_kwargs: SimpleNamespace(
            status=web_pdf_reader.active_document_text_extraction.STATUS_COMPLETE,
            text="abcdefghijklmnopqrstuvwxyz",
            reason_code="",
        )
        try:
            result = web_pdf_reader.read_pdf_bytes(
                _tiny_pdf("abcdefghijklmnopqrstuvwxyz"),
                url="https://example.com/doc.pdf",
                max_chars=10,
            )
        finally:
            web_pdf_reader._pdf_page_count = original_page_count
            web_pdf_reader.active_document_text_extraction.extract_active_document_text = original_extract

        self.assertEqual(result.status, "success")
        self.assertTrue(result.truncated)
        self.assertLessEqual(result.chars, len("abcdefghij\n[...contenu tronqué]"))
        self.assertIn("[...contenu tronqué]", result.text)

    def test_invalid_pdf_fails_cleanly(self) -> None:
        original_page_count = web_pdf_reader._pdf_page_count
        web_pdf_reader._pdf_page_count = lambda _data: (_ for _ in ()).throw(ValueError("broken_pdf"))
        try:
            result = web_pdf_reader.read_pdf_bytes(b"not a pdf", url="https://example.com/doc.pdf")
        finally:
            web_pdf_reader._pdf_page_count = original_page_count

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "web_pdf_extraction_failed")
        self.assertEqual(result.text, "")

    def test_content_type_probe_can_detect_pdf_without_pdf_suffix(self) -> None:
        pdf = _tiny_pdf("content type pdf")
        fake = _FakeRequests(
            head=_FakeResponse(headers={"Content-Type": "application/pdf", "Content-Length": str(len(pdf))}),
            get=_FakeResponse(headers={"Content-Type": "application/pdf"}, content=pdf),
        )
        original_page_count = web_pdf_reader._pdf_page_count
        original_extract = web_pdf_reader.active_document_text_extraction.extract_active_document_text
        original_getaddrinfo = web_pdf_reader.socket.getaddrinfo
        web_pdf_reader._pdf_page_count = lambda _data: 1
        web_pdf_reader.socket.getaddrinfo = _public_getaddrinfo
        web_pdf_reader.active_document_text_extraction.extract_active_document_text = lambda *_args, **_kwargs: SimpleNamespace(
            status=web_pdf_reader.active_document_text_extraction.STATUS_COMPLETE,
            text="content type pdf",
            reason_code="",
        )

        try:
            result = web_pdf_reader.read_pdf_url(
                "https://example.com/download?id=1",
                requests_module=fake,
                probe_content_type=True,
            )
        finally:
            web_pdf_reader._pdf_page_count = original_page_count
            web_pdf_reader.socket.getaddrinfo = original_getaddrinfo
            web_pdf_reader.active_document_text_extraction.extract_active_document_text = original_extract

        self.assertEqual(result.status, "success")
        self.assertEqual(result.reason_code, "web_pdf_read_success")
        self.assertEqual([call[0] for call in fake.calls], ["head", "get"])


if __name__ == "__main__":
    unittest.main()
