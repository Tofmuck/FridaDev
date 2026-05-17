from __future__ import annotations

import io
import json
import sys
import types
from dataclasses import dataclass
from types import SimpleNamespace
import unittest

try:
    import psycopg  # noqa: F401
except ModuleNotFoundError:  # pragma: no cover - local host may not have repo deps.
    sys.modules["psycopg"] = types.ModuleType("psycopg")
    rows_module = types.ModuleType("psycopg.rows")
    rows_module.dict_row = object()
    sys.modules["psycopg.rows"] = rows_module

from core import active_document_upload_service as upload_service


CONV_ID = "11111111-1111-1111-1111-111111111111"
OCR_TEXT = "OCR TEXT THAT MUST NOT LEAK"


class ActiveDocumentUploadOcrTest(unittest.TestCase):
    def test_ocr_success_activates_after_final_complete_extraction(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [
                _extraction(status="ocr_required", reason_code="document_ocr_required", text="", byte_size=14),
                _extraction(status="complete", reason_code="", text=OCR_TEXT, byte_size=20),
            ]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
            admin_logs_module=_FakeAdminLogs(),
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [b"%PDF scanned"])
        self.assertEqual(len(extractor.calls), 2)
        self.assertEqual(extractor.calls[1]["content"], b"%PDF OCR")
        self.assertEqual(active_docs.activated_texts, [OCR_TEXT])
        self.assertEqual(active_docs.activated_kwargs[0]["byte_size"], len(b"%PDF scanned"))
        self.assertNotIn(OCR_TEXT, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("ocr_pdf", json.dumps(payload, ensure_ascii=False))

    def test_textual_pdf_does_not_call_ocr(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor([_extraction(status="complete", reason_code="", text="texte PDF")])
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF textual"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [])
        self.assertEqual(len(extractor.calls), 1)
        self.assertEqual(active_docs.activated_texts, ["texte PDF"])

    def test_ocr_failed_refuses_without_activation_or_text_leak(self):
        payload, status, active_docs, ocr = _run_ocr_failure("document_ocr_failed")

        self.assertEqual(status, 422)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "document_ocr_failed")
        self.assertEqual(payload["document"]["status"], "ocr_failed")
        self.assertEqual(active_docs.activated_texts, [])
        self.assertEqual(len(ocr.calls), 1)
        self.assertNotIn(OCR_TEXT, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("ocr_pdf", json.dumps(payload, ensure_ascii=False))

    def test_ocr_exception_refuses_without_activation(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor([_extraction(status="ocr_required", reason_code="document_ocr_required", text="")])
        ocr = _ExplodingOcr()

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_failed")
        self.assertEqual(active_docs.activated_texts, [])

    def test_ocr_timeout_refuses_without_activation(self):
        payload, status, active_docs, _ocr = _run_ocr_failure("document_ocr_timeout")

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_timeout")
        self.assertEqual(active_docs.activated_texts, [])

    def test_ocr_too_large_refuses_without_activation(self):
        payload, status, active_docs, _ocr = _run_ocr_failure("document_ocr_too_large")

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_too_large")
        self.assertEqual(active_docs.activated_texts, [])

    def test_ocr_too_many_pages_refuses_without_activation(self):
        payload, status, active_docs, _ocr = _run_ocr_failure("document_ocr_too_many_pages")

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_too_many_pages")
        self.assertEqual(active_docs.activated_texts, [])

    def test_final_empty_extraction_after_ocr_refuses_as_ocr_empty(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [
                _extraction(status="ocr_required", reason_code="document_ocr_required", text=""),
                _extraction(status="empty", reason_code="document_empty_text", text=""),
            ]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_empty")
        self.assertEqual(active_docs.activated_texts, [])
        self.assertNotIn("ocr_pdf", json.dumps(payload, ensure_ascii=False))

    def test_final_parse_error_after_ocr_refuses_as_ocr_failed(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [
                _extraction(status="ocr_required", reason_code="document_ocr_required", text=""),
                _extraction(status="parse_error", reason_code="document_parse_error", text=""),
            ]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "document_ocr_failed")
        self.assertEqual(active_docs.activated_texts, [])


def _run_ocr_failure(reason_code: str):
    active_docs = _FakeActiveDocuments()
    extractor = _FakeExtractor([_extraction(status="ocr_required", reason_code="document_ocr_required", text="")])
    ocr = _FakeOcr(_ocr_result(status="error", reason_code=reason_code))
    payload, status = upload_service.upload_active_document_response(
        CONV_ID,
        _files(b"%PDF scanned " + OCR_TEXT.encode("utf-8")),
        conv_store_module=_FakeConvStore(),
        active_documents_module=active_docs,
        extractor_module=extractor,
        ocr_module=ocr,
    )
    return payload, status, active_docs, ocr


def _files(content: bytes):
    return {"file": _UploadFile(content, filename="scan.pdf", mimetype="application/pdf")}


class _UploadFile:
    def __init__(self, content: bytes, *, filename: str, mimetype: str):
        self._stream = io.BytesIO(content)
        self.filename = filename
        self.mimetype = mimetype

    def read(self):
        return self._stream.read()


class _FakeConvStore:
    def normalize_conversation_id(self, value):
        return str(value or "")

    def read_conversation(self, conversation_id, _system_prompt):
        return {"id": conversation_id, "messages": []} if conversation_id == CONV_ID else None


class _FakeActiveDocuments:
    def __init__(self):
        self.activated_texts = []
        self.activated_kwargs = []

    def activate_document(self, conversation_id, **kwargs):
        self.activated_kwargs.append(dict(kwargs))
        self.activated_texts.append(kwargs.get("text_content") or "")
        return {
            "document_id": "doc-1",
            "conversation_id": conversation_id,
            "filename": kwargs.get("filename", ""),
            "media_type": kwargs.get("media_type", ""),
            "source_extension": kwargs.get("source_extension", ""),
            "byte_size": kwargs.get("byte_size", 0),
            "text_chars": len(kwargs.get("text_content") or ""),
            "text_sha256_12": "abc123def456",
            "token_estimate": kwargs.get("token_estimate", 0),
            "status": "active",
            "active": True,
            "source": "active_conversation_documents",
        }


class _FakeAdminLogs:
    def log_event(self, *_args, **_kwargs):
        return None


class _FakeExtractor:
    STATUS_COMPLETE = "complete"
    STATUS_OCR_REQUIRED = "ocr_required"
    REASON_OCR_REQUIRED = "document_ocr_required"

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def extract_active_document_text(self, content, *, filename, media_type):
        self.calls.append({"content": bytes(content), "filename": filename, "media_type": media_type})
        if not self.results:
            raise AssertionError("unexpected extraction call")
        return self.results.pop(0)


class _FakeOcr:
    STATUS_COMPLETE = "complete"

    def __init__(self, result):
        self.result = result
        self.calls = []

    def ocr_pdf_with_stirling(self, content, *, filename):
        self.calls.append(bytes(content))
        return self.result


class _ExplodingOcr:
    STATUS_COMPLETE = "complete"

    def ocr_pdf_with_stirling(self, _content, *, filename):
        raise RuntimeError(f"boom {filename}")


@dataclass(frozen=True)
class _OcrResult:
    status: str
    reason_code: str
    ocr_pdf: bytes = b""
    page_count: int = 1
    source_bytes: int = 123
    ocr_engine: str = "stirling-pdf"
    ocr_languages: str = "fra+eng+deu"
    ocr_duration_ms: int = 10
    content_type: str = "application/pdf"

    def to_dict(self):
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "source_bytes": self.source_bytes,
            "page_count": self.page_count,
            "ocr_applied": self.status == "complete",
            "ocr_engine": self.ocr_engine,
            "ocr_languages": self.ocr_languages,
            "ocr_duration_ms": self.ocr_duration_ms,
            "content_type": self.content_type,
        }


def _ocr_result(*, status: str, reason_code: str, ocr_pdf: bytes = b""):
    return _OcrResult(status=status, reason_code=reason_code, ocr_pdf=ocr_pdf)


def _extraction(*, status: str, reason_code: str, text: str, byte_size: int = 10):
    chars = len(text)
    return SimpleNamespace(
        filename="scan.pdf",
        media_type="application/pdf",
        source_extension=".pdf",
        parser="pdf",
        status=status,
        reason_code=reason_code,
        text=text,
        chars=chars,
        bytes=byte_size,
        token_estimate=max(1, chars // 4) if chars else 0,
        sha256_12="abc123def456" if text else "",
        warnings=(),
        to_dict=lambda: {
            "filename": "scan.pdf",
            "media_type": "application/pdf",
            "source_extension": ".pdf",
            "parser": "pdf",
            "status": status,
            "reason_code": reason_code,
            "text": text,
            "chars": chars,
            "text_chars": chars,
            "bytes": byte_size,
            "byte_size": byte_size,
            "token_estimate": max(1, chars // 4) if chars else 0,
            "sha256_12": "abc123def456" if text else "",
            "text_sha256_12": "abc123def456" if text else "",
            "warnings": [],
        },
    )


if __name__ == "__main__":
    unittest.main()
