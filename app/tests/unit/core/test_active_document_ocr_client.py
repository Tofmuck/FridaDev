from __future__ import annotations

from types import SimpleNamespace
import unittest

import requests

from core import active_document_ocr_client as ocr


class ActiveDocumentOcrClientTest(unittest.TestCase):
    def test_defaults_match_contract(self):
        config = ocr.get_active_document_ocr_config(SimpleNamespace())

        self.assertEqual(config.url, "http://platform-stirling-pdf:8080/pdf/api/v1/misc/ocr-pdf")
        self.assertIn("/pdf/api/v1/misc/ocr-pdf", config.url)
        self.assertEqual(config.timeout_s, 180)
        self.assertEqual(config.languages, "fra+eng+deu")
        self.assertEqual(config.max_pages, 25)
        self.assertEqual(config.max_bytes, 25 * 1024 * 1024)

    def test_detects_page_count_before_ocr_and_posts_to_stirling(self):
        requests_module = _FakeRequests(
            _FakeResponse(
                status_code=200,
                headers={"Content-Type": "application/pdf; charset=binary"},
                content=b"%PDF OCR",
            )
        )

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            filename="../scan.pdf",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(3),
            monotonic=_monotonic(10.0, 10.250),
        )

        self.assertEqual(result.status, "complete")
        self.assertEqual(result.reason_code, "")
        self.assertEqual(result.page_count, 3)
        self.assertEqual(result.ocr_pdf, b"%PDF OCR")
        self.assertEqual(result.ocr_duration_ms, 250)
        self.assertEqual(result.ocr_languages, "fra+eng+deu")
        self.assertEqual(len(requests_module.calls), 1)
        call = requests_module.calls[0]
        self.assertEqual(call["url"], "http://ocr.example/pdf/api/v1/misc/ocr-pdf")
        self.assertEqual(call["timeout"], 180)
        self.assertEqual(
            call["data"],
            [
                ("languages", "fra"),
                ("languages", "eng"),
                ("languages", "deu"),
                ("ocrType", "force-ocr"),
                ("ocrRenderType", "sandwich"),
            ],
        )
        self.assertEqual(call["files"]["fileInput"][0], "scan.pdf")
        self.assertNotIn("ocr_pdf", result.to_dict())

    def test_refuses_byte_size_before_request(self):
        requests_module = _FakeRequests(_FakeResponse())

        result = ocr.ocr_pdf_with_stirling(
            b"123456",
            config_module=_config(max_bytes=5),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_too_large")
        self.assertEqual(result.source_bytes, 6)
        self.assertEqual(result.page_count, 0)
        self.assertEqual(requests_module.calls, [])

    def test_refuses_page_limit_before_request(self):
        requests_module = _FakeRequests(_FakeResponse())

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(max_pages=2),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(3),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_too_many_pages")
        self.assertEqual(result.page_count, 3)
        self.assertEqual(requests_module.calls, [])

    def test_timeout_is_content_free_failure(self):
        requests_module = _FakeRequests(requests.exceptions.Timeout("too slow"))

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
            monotonic=_monotonic(1.0, 181.0),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_timeout")
        self.assertEqual(result.page_count, 1)
        self.assertEqual(result.ocr_duration_ms, 180000)
        self.assertNotIn("content", result.to_dict())

    def test_unavailable_request_exception_is_failed(self):
        requests_module = _FakeRequests(requests.exceptions.ConnectionError("down"))

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_failed")
        self.assertIn("ConnectionError", result.warnings)

    def test_http_error_is_failed(self):
        requests_module = _FakeRequests(_FakeResponse(status_code=503, headers={"Content-Type": "application/json"}))

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_failed")
        self.assertIn("http_status=503", result.warnings)

    def test_non_pdf_response_is_failed(self):
        requests_module = _FakeRequests(
            _FakeResponse(status_code=200, headers={"Content-Type": "text/plain"}, content=b"not a pdf")
        )

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_failed")
        self.assertEqual(result.content_type, "text/plain")
        self.assertIn("non_pdf_response", result.warnings)

    def test_empty_pdf_response_is_empty_failure(self):
        requests_module = _FakeRequests(
            _FakeResponse(status_code=200, headers={"Content-Type": "application/pdf"}, content=b"")
        )

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=_reader_factory(1),
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_empty")
        self.assertEqual(result.ocr_pdf, b"")

    def test_page_count_failure_is_failed_without_request(self):
        requests_module = _FakeRequests(_FakeResponse())

        def reader_factory(_stream):
            raise ValueError("broken_pdf")

        result = ocr.ocr_pdf_with_stirling(
            b"%PDF source",
            config_module=_config(),
            requests_module=requests_module,
            pdf_reader_factory=reader_factory,
        )

        self.assertEqual(result.status, "error")
        self.assertEqual(result.reason_code, "document_ocr_failed")
        self.assertEqual(requests_module.calls, [])


class _FakeRequests:
    exceptions = requests.exceptions

    def __init__(self, outcome):
        self.outcome = outcome
        self.calls: list[dict] = []

    def post(self, url, *, files, data, timeout):
        self.calls.append({"url": url, "files": files, "data": data, "timeout": timeout})
        if isinstance(self.outcome, BaseException):
            raise self.outcome
        return self.outcome


class _FakeResponse:
    def __init__(self, *, status_code=200, headers=None, content=b"%PDF"):
        self.status_code = status_code
        self.headers = headers or {"Content-Type": "application/pdf"}
        self.content = content


def _config(**overrides):
    values = {
        "ACTIVE_DOCUMENT_OCR_URL": "http://ocr.example/pdf/api/v1/misc/ocr-pdf",
        "ACTIVE_DOCUMENT_OCR_TIMEOUT_S": 180,
        "ACTIVE_DOCUMENT_OCR_LANGUAGES": "fra+eng+deu",
        "ACTIVE_DOCUMENT_OCR_MAX_PAGES": 25,
        "ACTIVE_DOCUMENT_OCR_MAX_BYTES": 25 * 1024 * 1024,
    }
    aliases = {
        "url": "ACTIVE_DOCUMENT_OCR_URL",
        "timeout_s": "ACTIVE_DOCUMENT_OCR_TIMEOUT_S",
        "languages": "ACTIVE_DOCUMENT_OCR_LANGUAGES",
        "max_pages": "ACTIVE_DOCUMENT_OCR_MAX_PAGES",
        "max_bytes": "ACTIVE_DOCUMENT_OCR_MAX_BYTES",
    }
    for key, value in overrides.items():
        values[aliases.get(key, key)] = value
    return SimpleNamespace(**values)


def _reader_factory(page_count):
    def factory(_stream):
        return SimpleNamespace(is_encrypted=False, pages=[object() for _ in range(page_count)])

    return factory


def _monotonic(*values):
    iterator = iter(values)

    def current():
        return next(iterator)

    return current


if __name__ == "__main__":
    unittest.main()
