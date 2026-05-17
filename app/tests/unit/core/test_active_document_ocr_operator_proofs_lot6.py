from __future__ import annotations

import io
import inspect
import json
import unittest
from dataclasses import dataclass
from types import SimpleNamespace

from core import active_document_ocr_client
from core import active_document_prompt_lane
from core import active_document_upload_service
from core import chat_service
from observability import active_documents_observability


CONV_ID = "11111111-1111-1111-1111-111111111111"
DOC_ID = "aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa"
OCR_TEXT = "TEXTE OCR DE PREUVE QUI NE DOIT PAS SORTIR DES SURFACES ORDINAIRES"


class ActiveDocumentOcrOperatorProofsLot6Test(unittest.TestCase):
    def test_scanned_pdf_ocr_activates_then_follows_whole_or_absent_prompt_rule(self) -> None:
        active_docs = _StatefulActiveDocuments()
        extractor = _FakeExtractor(
            [
                _extraction(status="ocr_required", reason_code="document_ocr_required", text=""),
                _extraction(status="complete", reason_code="", text=OCR_TEXT, byte_size=24),
            ]
        )
        ocr = _FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCRISE"))

        payload, status = active_document_upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF scan image only"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
            admin_logs_module=_FakeAdminLogs(),
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.calls, [b"%PDF scan image only"])
        self.assertEqual(extractor.calls[1]["content"], b"%PDF OCRISE")
        self.assertEqual(active_docs.activated_texts, [OCR_TEXT])
        self.assertTrue(payload["document"]["ocr_applied"])
        self.assertNotIn(OCR_TEXT, json.dumps(payload, ensure_ascii=False))
        self.assertNotIn("ocr_pdf", json.dumps(payload, ensure_ascii=False))

        injected_messages, injected_lane, injected_events = _run_prompt_turn(
            active_docs,
            turn_id="turn-injected",
            max_tokens=0,
            token_count=1,
        )
        self.assertEqual(injected_lane.injected_count, 1)
        self.assertIn(OCR_TEXT, _joined_contents(injected_messages))
        self.assertTrue(injected_lane.decisions[0].ocr_applied)
        self.assertEqual(injected_events[0]["payload"]["ocr_applied_count"], 1)
        self.assertNotIn(OCR_TEXT, json.dumps(injected_events, ensure_ascii=False))
        self.assertEqual(active_docs.injected_records, [(CONV_ID, DOC_ID, "turn-injected")])

        excluded_messages, excluded_lane, excluded_events = _run_prompt_turn(
            active_docs,
            turn_id="turn-excluded",
            max_tokens=10,
            token_count=9999,
        )
        prompt_text = _joined_contents(excluded_messages)
        self.assertEqual(excluded_lane.injected_count, 0)
        self.assertEqual(excluded_lane.not_injected_count, 1)
        self.assertIn("Question du tour", prompt_text)
        self.assertIn("document_too_large_for_turn", prompt_text)
        self.assertNotIn(OCR_TEXT, prompt_text)
        self.assertEqual(excluded_events[0]["payload"]["too_large_count"], 1)
        self.assertNotIn(OCR_TEXT, json.dumps(excluded_events, ensure_ascii=False))
        self.assertEqual(
            active_docs.excluded_records,
            [(CONV_ID, DOC_ID, "turn-excluded", "document_too_large_for_turn")],
        )

    def test_textual_pdf_skips_ocr_and_ocr_refusals_keep_document_inactive(self) -> None:
        active_docs = _StatefulActiveDocuments()
        extractor = _FakeExtractor([_extraction(status="complete", reason_code="", text="Texte PDF deja lisible")])
        ocr = _FakeOcr(_ocr_result(status="error", reason_code="document_ocr_failed"))

        payload, status = active_document_upload_service.upload_active_document_response(
            CONV_ID,
            _files(b"%PDF textual"),
            conv_store_module=_FakeConvStore(),
            active_documents_module=active_docs,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 201)
        self.assertEqual(ocr.calls, [])
        self.assertFalse(payload["document"]["ocr_applied"])

        for reason_code in (
            "document_ocr_too_large",
            "document_ocr_too_many_pages",
            "document_ocr_timeout",
            "document_ocr_failed",
        ):
            with self.subTest(reason_code=reason_code):
                failure_payload, failure_status, failure_docs = _run_ocr_refusal(reason_code)
                self.assertEqual(failure_status, 422)
                self.assertEqual(failure_payload["reason_code"], reason_code)
                self.assertEqual(failure_docs.documents, {})
                self.assertNotIn(OCR_TEXT, json.dumps(failure_payload, ensure_ascii=False))
                self.assertNotIn("ocr_pdf", json.dumps(failure_payload, ensure_ascii=False))

        empty_payload, empty_status, empty_docs = _run_final_empty_after_ocr()
        self.assertEqual(empty_status, 422)
        self.assertEqual(empty_payload["reason_code"], "document_ocr_empty")
        self.assertEqual(empty_docs.documents, {})

    def test_nominal_path_stays_active_document_only_without_n8n_or_doc_pipeline(self) -> None:
        self.assertIn("platform-stirling-pdf", active_document_ocr_client.DEFAULT_OCR_URL)
        self.assertNotIn("doc-pipeline", active_document_ocr_client.DEFAULT_OCR_URL)
        self.assertNotIn("n8n", active_document_ocr_client.DEFAULT_OCR_URL)

        nominal_sources = "\n".join(
            (
                inspect.getsource(active_document_upload_service),
                inspect.getsource(active_document_ocr_client),
            )
        )
        self.assertNotIn("doc-pipeline", nominal_sources)
        self.assertNotIn("doc_pipeline", nominal_sources)
        self.assertNotIn("n8n", nominal_sources)


def _run_prompt_turn(
    active_docs: "_StatefulActiveDocuments",
    *,
    turn_id: str,
    max_tokens: int,
    token_count: int,
) -> tuple[list[dict[str, object]], object, list[dict[str, object]]]:
    prompt_messages: list[dict[str, object]] = [
        {"role": "system", "content": "SYSTEM"},
        {"role": "user", "content": "Question du tour"},
    ]
    lane = active_document_prompt_lane.inject_active_document_prompt_lane(
        prompt_messages,
        active_docs.list_active_documents_for_prompt(CONV_ID),
        model="model-test",
        count_tokens_func=lambda _messages, _model: token_count,
        max_tokens=max_tokens,
    )
    chat_service._record_active_document_prompt_decisions(
        conversation={"id": CONV_ID},
        lane=lane,
        turn_id=turn_id,
        active_documents_module=active_docs,
        logger=SimpleNamespace(warning=lambda *_args, **_kwargs: None),
    )
    events: list[dict[str, object]] = []
    active_documents_observability.emit_prompt_decision_event(
        lane,
        chat_turn_logger_module=SimpleNamespace(
            emit=lambda stage, status, payload: events.append(
                {"stage": stage, "status": status, "payload": payload}
            )
            or True
        ),
    )
    return prompt_messages, lane, events


def _run_ocr_refusal(reason_code: str) -> tuple[dict[str, object], int, "_StatefulActiveDocuments"]:
    active_docs = _StatefulActiveDocuments()
    payload, status = active_document_upload_service.upload_active_document_response(
        CONV_ID,
        _files(b"%PDF scanned"),
        conv_store_module=_FakeConvStore(),
        active_documents_module=active_docs,
        extractor_module=_FakeExtractor([_extraction(status="ocr_required", reason_code="document_ocr_required", text="")]),
        ocr_module=_FakeOcr(_ocr_result(status="error", reason_code=reason_code)),
    )
    return payload, status, active_docs


def _run_final_empty_after_ocr() -> tuple[dict[str, object], int, "_StatefulActiveDocuments"]:
    active_docs = _StatefulActiveDocuments()
    payload, status = active_document_upload_service.upload_active_document_response(
        CONV_ID,
        _files(b"%PDF scanned"),
        conv_store_module=_FakeConvStore(),
        active_documents_module=active_docs,
        extractor_module=_FakeExtractor(
            [
                _extraction(status="ocr_required", reason_code="document_ocr_required", text=""),
                _extraction(status="empty", reason_code="document_empty_text", text=""),
            ]
        ),
        ocr_module=_FakeOcr(_ocr_result(status="complete", reason_code="", ocr_pdf=b"%PDF OCRISE")),
    )
    return payload, status, active_docs


class _StatefulActiveDocuments:
    def __init__(self) -> None:
        self.documents: dict[str, dict[str, object]] = {}
        self.activated_texts: list[str] = []
        self.injected_records: list[tuple[str, str, str]] = []
        self.excluded_records: list[tuple[str, str, str, str]] = []

    def activate_document(self, conversation_id: str, **kwargs):
        text = str(kwargs.get("text_content") or "")
        self.activated_texts.append(text)
        document = {
            "document_id": DOC_ID,
            "conversation_id": conversation_id,
            "filename": kwargs.get("filename", "scan.pdf"),
            "media_type": kwargs.get("media_type", "application/pdf"),
            "source_extension": kwargs.get("source_extension", ".pdf"),
            "byte_size": int(kwargs.get("byte_size") or 0),
            "text_chars": len(text),
            "text_sha256_12": "abc123def456",
            "token_estimate": int(kwargs.get("token_estimate") or 1),
            "status": "active",
            "active": True,
            "ocr_applied": bool(kwargs.get("ocr_applied", False)),
            "ocr_engine": kwargs.get("ocr_engine", ""),
            "ocr_languages": kwargs.get("ocr_languages", ""),
            "ocr_duration_ms": int(kwargs.get("ocr_duration_ms") or 0),
            "text_content": text,
            "source": "active_conversation_documents",
        }
        self.documents[DOC_ID] = document
        visible = dict(document)
        visible.pop("text_content", None)
        return visible

    def list_active_documents_for_prompt(self, conversation_id: str):
        return [
            dict(item)
            for item in self.documents.values()
            if item.get("conversation_id") == conversation_id and item.get("status") == "active"
        ]

    def record_document_injected(self, conversation_id: str, document_id: str, *, turn_id: str) -> bool:
        self.injected_records.append((conversation_id, document_id, turn_id))
        return True

    def record_document_excluded(
        self,
        conversation_id: str,
        document_id: str,
        *,
        turn_id: str,
        reason_code: str,
    ) -> bool:
        self.excluded_records.append((conversation_id, document_id, turn_id, reason_code))
        return True


class _FakeConvStore:
    def normalize_conversation_id(self, value):
        return str(value or "")

    def read_conversation(self, conversation_id, _system_prompt):
        return {"id": conversation_id, "messages": []} if conversation_id == CONV_ID else None


class _FakeExtractor:
    STATUS_COMPLETE = "complete"
    STATUS_OCR_REQUIRED = "ocr_required"
    REASON_OCR_REQUIRED = "document_ocr_required"

    def __init__(self, results):
        self.results = list(results)
        self.calls: list[dict[str, object]] = []

    def extract_active_document_text(self, content, *, filename, media_type):
        self.calls.append({"content": bytes(content), "filename": filename, "media_type": media_type})
        if not self.results:
            raise AssertionError("unexpected extraction call")
        return self.results.pop(0)


class _FakeOcr:
    STATUS_COMPLETE = "complete"

    def __init__(self, result):
        self.result = result
        self.calls: list[bytes] = []

    def ocr_pdf_with_stirling(self, content, *, filename):
        self.calls.append(bytes(content))
        return self.result


class _FakeAdminLogs:
    def log_event(self, *_args, **_kwargs):
        return None


class _UploadFile:
    def __init__(self, content: bytes):
        self._stream = io.BytesIO(content)
        self.filename = "scan.pdf"
        self.mimetype = "application/pdf"

    def read(self):
        return self._stream.read()


@dataclass(frozen=True)
class _OcrResult:
    status: str
    reason_code: str
    ocr_pdf: bytes = b""
    ocr_engine: str = "stirling-pdf"
    ocr_languages: str = "fra+eng+deu"
    ocr_duration_ms: int = 10

    def to_dict(self):
        return {
            "status": self.status,
            "reason_code": self.reason_code,
            "ocr_pdf": self.ocr_pdf,
            "ocr_applied": self.status == "complete",
            "ocr_engine": self.ocr_engine,
            "ocr_languages": self.ocr_languages,
            "ocr_duration_ms": self.ocr_duration_ms,
            "content_type": "application/pdf",
        }


def _files(content: bytes):
    return {"file": _UploadFile(content)}


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


def _joined_contents(messages) -> str:
    return "\n".join(str(message.get("content") or "") for message in messages)


if __name__ == "__main__":
    unittest.main()
