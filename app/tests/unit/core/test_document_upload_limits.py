from __future__ import annotations

import io
import unittest
from types import SimpleNamespace
from unittest import mock

from core import active_document_upload_service
from core import workspace_files_service


CONVERSATION_ID = "11111111-1111-1111-1111-111111111111"
FOLDER_ID = "11111111-2222-4333-8444-555555555555"


def _sentinel_bytes(size: int) -> bytes:
    start = b"LOT10B-BEGIN"
    middle = b"LOT10B-MIDDLE"
    end = b"LOT10B-END"
    filler_size = int(size) - len(start) - len(middle) - len(end)
    if filler_size < 0:
        raise AssertionError("test size is too small for sentinels")
    left = filler_size // 2
    return start + (b"x" * left) + middle + (b"y" * (filler_size - left)) + end


class _InstrumentedUpload:
    filename = "proof.txt"
    mimetype = "text/plain"

    def __init__(self, content: bytes) -> None:
        self._stream = io.BytesIO(content)
        self.read_sizes: list[int] = []
        self.bytes_returned = 0

    def read(self, size: int = -1) -> bytes:
        self.read_sizes.append(size)
        chunk = self._stream.read(size)
        self.bytes_returned += len(chunk)
        return chunk

    @property
    def remaining(self) -> int:
        position = self._stream.tell()
        return len(self._stream.getbuffer()) - position


class _FakeConvStore:
    @staticmethod
    def normalize_conversation_id(value):
        return str(value or "")

    @staticmethod
    def read_conversation(conversation_id, _system_prompt):
        return {"id": conversation_id, "messages": []}


class _FakeActiveDocuments:
    def __init__(self) -> None:
        self.activations: list[dict[str, object]] = []

    def activate_document(self, conversation_id, **kwargs):
        self.activations.append({"conversation_id": conversation_id, **kwargs})
        return {
            "document_id": "doc-proof",
            "conversation_id": conversation_id,
            "filename": kwargs["filename"],
            "media_type": kwargs["media_type"],
            "source_extension": kwargs["source_extension"],
            "byte_size": kwargs["byte_size"],
            "text_chars": len(kwargs["text_content"]),
            "text_sha256_12": "abc123def456",
            "token_estimate": kwargs["token_estimate"],
            "status": "active",
            "active": True,
        }


class _FakeExtractor:
    STATUS_COMPLETE = "complete"
    STATUS_OCR_REQUIRED = "ocr_required"
    REASON_OCR_REQUIRED = "document_ocr_required"

    def __init__(self) -> None:
        self.calls: list[bytes] = []

    def extract_active_document_text(self, content, *, filename, media_type):
        raw = bytes(content)
        self.calls.append(raw)
        text = raw.decode("ascii")
        return SimpleNamespace(
            status="complete",
            reason_code="",
            filename=filename,
            media_type=media_type,
            source_extension=".txt",
            text=text,
            chars=len(text),
            token_estimate=max(1, len(text) // 4),
            sha256_12="abc123def456",
            to_dict=lambda: {
                "status": "complete",
                "reason_code": "",
                "filename": filename,
                "media_type": media_type,
                "source_extension": ".txt",
                "text": text,
                "text_chars": len(text),
                "byte_size": len(raw),
                "token_estimate": max(1, len(text) // 4),
                "text_sha256_12": "abc123def456",
            },
        )


class _FailIfOcrCalled:
    STATUS_COMPLETE = "complete"

    @staticmethod
    def ocr_pdf_with_stirling(*_args, **_kwargs):
        raise AssertionError("OCR must not run for this upload")


class _FakeFolders:
    @staticmethod
    def normalize_workspace_folder_id(value):
        return str(value or "")

    @staticmethod
    def get_workspace_folder(folder_id):
        return {"id": folder_id, "nextcloud_sync_state": "linked", "deleted_at": None}


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"

    def __init__(self) -> None:
        self.events: list[tuple[str, dict[str, object]]] = []

    @staticmethod
    def sanitize_display_name(value):
        return str(value or "")

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeImageValidator:
    STATUS_COMPLETE = "complete"

    @staticmethod
    def validate_active_image_upload(*_args, **_kwargs):
        return SimpleNamespace(is_image_candidate=False)


class _FakeDocumentsRuntime:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def store_workspace_document_nextcloud_first(self, **kwargs):
        self.calls.append(dict(kwargs))
        return {
            "ok": True,
            "status": 201,
            "file": {"id": "file-proof", "byte_size": len(kwargs["content"])},
            "document_nextcloud": {"reason_code": "folder_document_upload_ok"},
        }


class DocumentUploadLimitsTests(unittest.TestCase):
    def test_active_document_accepts_limit_minus_one_and_exact_limit_without_alteration(self) -> None:
        limit = 96
        for size in (limit - 1, limit):
            with self.subTest(size=size):
                content = _sentinel_bytes(size)
                upload = _InstrumentedUpload(content)
                extractor = _FakeExtractor()
                active_documents = _FakeActiveDocuments()
                with mock.patch.object(
                    active_document_upload_service,
                    "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
                    limit,
                ):
                    payload, status = active_document_upload_service.upload_active_document_response(
                        CONVERSATION_ID,
                        {"file": upload},
                        conv_store_module=_FakeConvStore(),
                        active_documents_module=active_documents,
                        extractor_module=extractor,
                        ocr_module=_FailIfOcrCalled(),
                    )

                self.assertEqual(status, 201)
                self.assertTrue(payload["ok"])
                self.assertEqual(upload.bytes_returned, size)
                self.assertEqual(extractor.calls, [content])
                self.assertEqual(active_documents.activations[0]["text_content"].encode("ascii"), content)

    def test_active_document_rejects_after_limit_plus_one_without_downstream_effect(self) -> None:
        limit = 96
        upload = _InstrumentedUpload(_sentinel_bytes(limit + 64))
        extractor = _FakeExtractor()
        active_documents = _FakeActiveDocuments()
        with mock.patch.object(
            active_document_upload_service,
            "ACTIVE_DOCUMENT_UPLOAD_MAX_CONTENT_LENGTH",
            limit,
        ):
            payload, status = active_document_upload_service.upload_active_document_response(
                CONVERSATION_ID,
                {"file": upload},
                conv_store_module=_FakeConvStore(),
                active_documents_module=active_documents,
                extractor_module=extractor,
                ocr_module=_FailIfOcrCalled(),
            )

        self.assertEqual(status, 413)
        self.assertEqual(payload["reason_code"], "active_document_upload_too_large")
        self.assertEqual(upload.bytes_returned, limit + 1)
        self.assertGreater(upload.remaining, 0)
        self.assertTrue(all(size > 0 for size in upload.read_sizes))
        self.assertEqual(extractor.calls, [])
        self.assertEqual(active_documents.activations, [])

    def test_workspace_accepts_limit_minus_one_and_exact_limit_without_alteration(self) -> None:
        limit = 96
        for size in (limit - 1, limit):
            with self.subTest(size=size):
                content = _sentinel_bytes(size)
                upload = _InstrumentedUpload(content)
                extractor = _FakeExtractor()
                runtime = _FakeDocumentsRuntime()
                with (
                    mock.patch.object(
                        workspace_files_service,
                        "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
                        limit,
                    ),
                    mock.patch.object(
                        workspace_files_service.workspace_folder_documents,
                        "apply_document_v1_projection",
                        side_effect=lambda stored, *, folder: dict(stored),
                    ),
                ):
                    payload, status = workspace_files_service.upload_workspace_file_response(
                        FOLDER_ID,
                        {"file": upload},
                        workspace_folders_module=_FakeFolders(),
                        workspace_files_module=_FakeWorkspaceFiles(),
                        extractor_module=extractor,
                        image_validator_module=_FakeImageValidator(),
                        documents_nextcloud_runtime_module=runtime,
                    )

                self.assertEqual(status, 201)
                self.assertTrue(payload["ok"])
                self.assertEqual(upload.bytes_returned, size)
                self.assertEqual(extractor.calls, [content])
                self.assertEqual(runtime.calls[0]["content"], content)

    def test_workspace_rejects_after_limit_plus_one_without_downstream_effect(self) -> None:
        limit = 96
        upload = _InstrumentedUpload(_sentinel_bytes(limit + 64))
        extractor = _FakeExtractor()
        runtime = _FakeDocumentsRuntime()
        workspace_files = _FakeWorkspaceFiles()
        with mock.patch.object(
            workspace_files_service,
            "WORKSPACE_FILE_UPLOAD_MAX_CONTENT_LENGTH",
            limit,
        ):
            payload, status = workspace_files_service.upload_workspace_file_response(
                FOLDER_ID,
                {"file": upload},
                workspace_folders_module=_FakeFolders(),
                workspace_files_module=workspace_files,
                extractor_module=extractor,
                image_validator_module=_FakeImageValidator(),
                documents_nextcloud_runtime_module=runtime,
            )

        self.assertEqual(status, 413)
        self.assertEqual(payload["reason_code"], "folder_document_too_large")
        self.assertEqual(upload.bytes_returned, limit + 1)
        self.assertGreater(upload.remaining, 0)
        self.assertTrue(all(size > 0 for size in upload.read_sizes))
        self.assertEqual(extractor.calls, [])
        self.assertEqual(runtime.calls, [])
        self.assertEqual(workspace_files.events[-1][1]["reason_code"], "folder_document_too_large")


if __name__ == "__main__":
    unittest.main()
