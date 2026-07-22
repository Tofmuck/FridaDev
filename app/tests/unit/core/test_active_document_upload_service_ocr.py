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
            pdf_visual_fallback_enabled=False,
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [b"%PDF scanned"])
        self.assertEqual(len(extractor.calls), 2)
        self.assertEqual(extractor.calls[1]["content"], b"%PDF OCR")
        self.assertEqual(active_docs.activated_texts, [OCR_TEXT])
        self.assertEqual(active_docs.activated_kwargs[0]["byte_size"], len(b"%PDF scanned"))
        self.assertIs(active_docs.activated_kwargs[0]["ocr_applied"], True)
        self.assertEqual(active_docs.activated_kwargs[0]["ocr_engine"], "stirling-pdf")
        self.assertEqual(active_docs.activated_kwargs[0]["ocr_languages"], "fra+eng+deu")
        self.assertEqual(active_docs.activated_kwargs[0]["ocr_duration_ms"], 10)
        self.assertIs(payload["document"]["ocr_applied"], True)
        self.assertEqual(payload["document"]["ocr_engine"], "stirling-pdf")
        self.assertNotIn(OCR_TEXT, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("ocr_pdf", json.dumps(payload, ensure_ascii=False))

    def test_direct_upload_pdf_without_text_becomes_visual_file_by_default(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [_extraction(status="ocr_required", reason_code="document_ocr_required", text="", byte_size=14)]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
            visual_limits_module=_FakeVisualLimits(),
            admin_logs_module=_FakeAdminLogs(),
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [])
        self.assertEqual(len(extractor.calls), 1)
        self.assertEqual(active_docs.activated_texts, [])
        self.assertEqual(active_docs.activated_files, [b"%PDF scanned"])
        self.assertEqual(payload["document"]["media_kind"], "file")
        self.assertEqual(payload["document"]["media_type"], "application/pdf")
        self.assertIs(payload["document"]["ocr_applied"], False)
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("file_content", serialized)
        self.assertNotIn("data:application/pdf", serialized)
        self.assertNotIn("ocr_pdf", serialized)

    def test_direct_upload_pdf_visual_too_many_pages_refuses_before_activation(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [_extraction(status="ocr_required", reason_code="document_ocr_required", text="", byte_size=14)]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCR"))

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
            visual_limits_module=_FakeVisualLimits(ok=False, reason_code="pdf_visual_too_many_pages", page_count=26),
            admin_logs_module=_FakeAdminLogs(),
        )

        self.assertEqual(status, 422)
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "file_too_many_pages_for_provider_payload")
        self.assertEqual(payload["document"]["status"], "too_large")
        self.assertEqual(payload["document"]["page_count"], 26)
        self.assertEqual(ocr.calls, [])
        self.assertEqual(active_docs.activated_texts, [])
        self.assertEqual(active_docs.activated_files, [])
        serialized = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn("file_content", serialized)
        self.assertNotIn("data:application/pdf", serialized)
        self.assertNotIn("ocr_pdf", serialized)

    def test_direct_upload_pdf_visual_page_count_error_is_fail_closed(self):
        active_docs = _FakeActiveDocuments()
        extractor = _FakeExtractor(
            [_extraction(status="ocr_required", reason_code="document_ocr_required", text="", byte_size=14)]
        )

        payload, status = upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scanned"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=_ExplodingOcr(),
            visual_limits_module=_FakeVisualLimits(ok=False, reason_code="pdf_visual_page_count_failed"),
            admin_logs_module=_FakeAdminLogs(),
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "file_page_count_failed")
        self.assertEqual(active_docs.activated_texts, [])
        self.assertEqual(active_docs.activated_files, [])

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
            pdf_visual_fallback_enabled=False,
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [])
        self.assertEqual(len(extractor.calls), 1)
        self.assertEqual(active_docs.activated_texts, ["texte PDF"])
        self.assertNotIn("ocr_applied", active_docs.activated_kwargs[0])
        self.assertIs(payload["document"]["ocr_applied"], False)

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
            pdf_visual_fallback_enabled=False,
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
            pdf_visual_fallback_enabled=False,
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
            pdf_visual_fallback_enabled=False,
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
        pdf_visual_fallback_enabled=False,
    )
    return payload, status, active_docs, ocr


def _files(content: bytes):
    return {"file": _UploadFile(content, filename="scan.pdf", mimetype="application/pdf")}


class _UploadFile:
    def __init__(self, content: bytes, *, filename: str, mimetype: str):
        self._stream = io.BytesIO(content)
        self.filename = filename
        self.mimetype = mimetype

    def read(self, size=-1):
        return self._stream.read(size)


class _FakeConvStore:
    def normalize_conversation_id(self, value):
        return str(value or "")

    def read_conversation(self, conversation_id, _system_prompt):
        return {"id": conversation_id, "messages": []} if conversation_id == CONV_ID else None


class _FakeActiveDocuments:
    def __init__(self):
        self.activated_texts = []
        self.activated_kwargs = []
        self.activated_files = []
        self.activated_file_kwargs = []

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
            "ocr_applied": bool(kwargs.get("ocr_applied", False)),
            "ocr_engine": kwargs.get("ocr_engine", ""),
            "ocr_languages": kwargs.get("ocr_languages", ""),
            "ocr_duration_ms": kwargs.get("ocr_duration_ms", 0),
            "source": "active_conversation_documents",
        }

    def activate_file_document(self, conversation_id, **kwargs):
        self.activated_file_kwargs.append(dict(kwargs))
        self.activated_files.append(bytes(kwargs.get("file_content") or b""))
        return {
            "document_id": "doc-file-1",
            "conversation_id": conversation_id,
            "filename": kwargs.get("filename", ""),
            "media_type": kwargs.get("media_type", ""),
            "source_extension": kwargs.get("source_extension", ""),
            "byte_size": kwargs.get("byte_size", 0),
            "text_chars": 0,
            "text_sha256_12": "",
            "media_kind": "file",
            "content_sha256_12": "file123abc456",
            "token_estimate": 0,
            "status": "active",
            "active": True,
            "ocr_applied": False,
            "ocr_engine": "",
            "ocr_languages": "",
            "ocr_duration_ms": 0,
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


class _FakeVisualLimits:
    def __init__(self, *, ok=True, reason_code="", page_count=1, max_pages=25):
        self.ok = ok
        self.reason_code = reason_code
        self.page_count = page_count
        self.max_pages = max_pages
        self.calls = []

    def check_pdf_visual_pages(self, content):
        self.calls.append(bytes(content))
        return SimpleNamespace(
            ok=self.ok,
            reason_code=self.reason_code,
            page_count=self.page_count,
            max_pages=self.max_pages,
        )


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
