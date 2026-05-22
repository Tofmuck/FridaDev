from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_file_ocr_service


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
SOURCE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
DERIVED_ID = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OCR_TEXT = "TEXTE OCR BRUT A NE PAS LOGGUER"


class WorkspaceFileOcrServiceTest(unittest.TestCase):
    def test_pdf_ocr_creates_durable_markdown_derivative_without_raw_payload(self) -> None:
        files = _FakeWorkspaceFiles(
            _source_row(
                display_name="scan.pdf",
                mime_type="application/pdf",
                source_extension=".pdf",
                status="ocr_required",
            ),
            source_bytes=b"%PDF source",
        )
        extractor = _FakeExtractor(
            [
                _extraction(text=OCR_TEXT, filename="scan.pdf", media_type="application/pdf"),
                _extraction(text=f"# OCR\n\n{OCR_TEXT}", filename="scan.ocr.md", media_type="text/markdown"),
            ]
        )
        ocr = _FakeOcr()

        payload, status = workspace_file_ocr_service.ocr_workspace_file_response(
            FOLDER_ID,
            SOURCE_ID,
            workspace_folders_module=_FakeFolders(),
            workspace_files_module=files,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 201)
        self.assertTrue(payload["ok"])
        self.assertEqual(ocr.pdf_calls, [b"%PDF source"])
        self.assertEqual(payload["file"]["display_name"], "scan.ocr.md")
        self.assertEqual(payload["file"]["source_kind"], "ocr_derived")
        self.assertEqual(payload["file"]["source_file_id"], SOURCE_ID)
        self.assertIn(OCR_TEXT, files.bytes[DERIVED_ID].decode("utf-8"))
        encoded_payload = json.dumps(payload, ensure_ascii=False)
        self.assertNotIn(OCR_TEXT, encoded_payload)
        self.assertNotIn("ocr_pdf", encoded_payload)
        self.assertNotIn(OCR_TEXT, "\n".join(files.logs))

    def test_image_ocr_reuses_image_ocr_client_then_creates_markdown(self) -> None:
        files = _FakeWorkspaceFiles(
            _source_row(
                display_name="photo-page-12.jpg",
                mime_type="image/jpeg",
                media_kind="image",
                content_kind="image",
                source_extension=".jpg",
                image_width=1200,
                image_height=900,
            ),
            source_bytes=b"jpeg-bytes",
        )
        extractor = _FakeExtractor(
            [
                _extraction(text="Texte depuis photo", filename="photo-page-12.jpg", media_type="application/pdf"),
                _extraction(text="Texte depuis photo", filename="photo-page-12.ocr.md", media_type="text/markdown"),
            ]
        )
        ocr = _FakeOcr()

        payload, status = workspace_file_ocr_service.ocr_workspace_file_response(
            FOLDER_ID,
            SOURCE_ID,
            workspace_folders_module=_FakeFolders(),
            workspace_files_module=files,
            extractor_module=extractor,
            ocr_module=ocr,
        )

        self.assertEqual(status, 201)
        self.assertEqual(ocr.image_calls, [(b"jpeg-bytes", "photo-page-12.jpg", "image/jpeg")])
        self.assertEqual(payload["file"]["display_name"], "photo-page-12.ocr.md")
        self.assertEqual(payload["file"]["media_kind"], "text")
        self.assertEqual(payload["file"]["mime_type"], "text/markdown")

    def test_ocr_refuses_unsupported_workspace_file_type(self) -> None:
        files = _FakeWorkspaceFiles(
            _source_row(display_name="note.txt", mime_type="text/plain", source_extension=".txt"),
            source_bytes=b"note",
        )

        payload, status = workspace_file_ocr_service.ocr_workspace_file_response(
            FOLDER_ID,
            SOURCE_ID,
            workspace_folders_module=_FakeFolders(),
            workspace_files_module=files,
            extractor_module=_FakeExtractor([]),
            ocr_module=_FakeOcr(),
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "workspace_file_ocr_unsupported")
        self.assertEqual(files.bytes, {SOURCE_ID: b"note"})
        self.assertIn("workspace_files_ocr_refused", "\n".join(files.logs))

    def test_ocr_markdown_read_and_save_are_explicit_and_content_free_in_logs(self) -> None:
        files = _FakeWorkspaceFiles(
            _source_row(
                file_id=DERIVED_ID,
                display_name="scan.ocr.md",
                mime_type="text/markdown",
                source_extension=".md",
                source_kind="ocr_derived",
                source_file_id=SOURCE_ID,
            ),
            source_bytes=b"# OCR\n\nancien texte",
        )

        read_payload, read_status = workspace_file_ocr_service.get_ocr_markdown_response(
            FOLDER_ID,
            DERIVED_ID,
            workspace_folders_module=_FakeFolders(),
            workspace_files_module=files,
        )
        self.assertEqual(read_status, 200)
        self.assertEqual(read_payload["content"], "# OCR\n\nancien texte")

        updated_payload, updated_status = workspace_file_ocr_service.patch_ocr_markdown_response(
            FOLDER_ID,
            DERIVED_ID,
            {"content": "# OCR\n\ntexte corrigé"},
            workspace_folders_module=_FakeFolders(),
            workspace_files_module=files,
            extractor_module=_FakeExtractor([_extraction(text="# OCR\n\ntexte corrigé")]),
        )

        self.assertEqual(updated_status, 200)
        self.assertEqual(updated_payload["file"]["id"], DERIVED_ID)
        self.assertEqual(files.bytes[DERIVED_ID], "# OCR\n\ntexte corrigé".encode("utf-8"))
        logged = "\n".join(files.logs)
        self.assertIn("workspace_files_ocr_markdown_edit_ok", logged)
        self.assertNotIn("texte corrigé", logged)
        self.assertNotIn("ancien texte", logged)


class _FakeFolders:
    def normalize_workspace_folder_id(self, value):
        return FOLDER_ID if str(value or "") == FOLDER_ID else None

    def get_workspace_folder(self, folder_id):
        return {"id": folder_id, "deleted_at": None} if folder_id == FOLDER_ID else None


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"
    SOURCE_KIND_OCR_DERIVED = "ocr_derived"

    def __init__(self, source_row, *, source_bytes):
        self.rows = {source_row["id"]: dict(source_row)}
        self.bytes = {source_row["id"]: bytes(source_bytes)}
        self.logs: list[str] = []

    def normalize_workspace_file_id(self, value):
        raw = str(value or "")
        return raw if raw in self.rows or raw in {SOURCE_ID, DERIVED_ID} else None

    def get_workspace_file_storage_row(self, folder_id, file_id):
        row = self.rows.get(file_id)
        return dict(row) if row and row["workspace_folder_id"] == folder_id else None

    def read_file_bytes(self, storage_key):
        for row in self.rows.values():
            if row["storage_key"] == storage_key:
                return self.bytes[row["id"]]
        raise FileNotFoundError(storage_key)

    def find_ocr_derived_file(self, folder_id, source_file_id):
        for row in self.rows.values():
            if (
                row["workspace_folder_id"] == folder_id
                and row.get("source_file_id") == source_file_id
                and row.get("source_kind") == "ocr_derived"
                and row.get("deleted_at") is None
            ):
                return self._public(row)
        return None

    def store_uploaded_file(self, folder_id, *, original_filename, content, metadata):
        row = {
            **_source_row(
                file_id=DERIVED_ID,
                display_name=metadata.get("display_name") or original_filename,
                mime_type=metadata.get("mime_type", "text/markdown"),
                media_kind=metadata.get("media_kind", "text"),
                content_kind=metadata.get("content_kind", "document"),
                source_extension=metadata.get("source_extension", ".md"),
                source_kind=metadata.get("source_kind", "ocr_derived"),
                source_file_id=metadata.get("source_file_id"),
            ),
            "byte_size": len(content),
            "text_chars": int(metadata.get("text_chars") or 0),
            "text_sha256_12": str(metadata.get("text_sha256_12") or ""),
        }
        self.rows[DERIVED_ID] = row
        self.bytes[DERIVED_ID] = bytes(content)
        return self._public(row)

    def update_workspace_text_file(self, folder_id, file_id, *, content, metadata):
        row = self.rows.get(file_id)
        if not row or row["workspace_folder_id"] != folder_id:
            return None
        self.bytes[file_id] = bytes(content)
        row["byte_size"] = len(content)
        row["text_chars"] = int(metadata.get("text_chars") or 0)
        row["text_sha256_12"] = str(metadata.get("text_sha256_12") or "")
        row["status"] = metadata.get("status") or "active"
        row["reason_code"] = metadata.get("reason_code") or ""
        return self._public(row)

    def log_content_free_event(self, event, level="info", **fields):
        safe = [f"workspace_files_{event}", f"level={level}"]
        for key, value in sorted(fields.items()):
            if key in {"content", "text", "text_content", "raw", "payload", "ocr_pdf"}:
                continue
            safe.append(f"{key}={value}")
        self.logs.append(" ".join(safe))

    def _public(self, row):
        return {
            key: value
            for key, value in row.items()
            if key not in {"storage_key", "sha256"}
        }


class _FakeOcr:
    STATUS_COMPLETE = "complete"

    def __init__(self):
        self.pdf_calls: list[bytes] = []
        self.image_calls: list[tuple[bytes, str, str]] = []

    def ocr_pdf_with_stirling(self, content, *, filename):
        self.pdf_calls.append(bytes(content))
        return _ocr_result()

    def ocr_image_with_stirling(self, content, *, filename, media_type):
        self.image_calls.append((bytes(content), filename, media_type))
        return _ocr_result()


class _FakeExtractor:
    STATUS_COMPLETE = "complete"

    def __init__(self, results):
        self.results = list(results)
        self.calls = []

    def extract_active_document_text(self, content, *, filename, media_type):
        self.calls.append({"content": bytes(content), "filename": filename, "media_type": media_type})
        if not self.results:
            raise AssertionError("unexpected extraction")
        return self.results.pop(0)


def _source_row(
    *,
    file_id=SOURCE_ID,
    display_name="scan.pdf",
    mime_type="application/pdf",
    media_kind="text",
    content_kind="document",
    source_extension=".pdf",
    status="active",
    source_kind="upload",
    source_file_id=None,
    image_width=0,
    image_height=0,
):
    return {
        "id": file_id,
        "workspace_folder_id": FOLDER_ID,
        "display_name": display_name,
        "original_filename": display_name,
        "storage_key": f"{FOLDER_ID}/{file_id}{source_extension}",
        "content_kind": content_kind,
        "media_kind": media_kind,
        "mime_type": mime_type,
        "source_extension": source_extension,
        "byte_size": 123,
        "sha256": "full-hidden",
        "sha256_12": "abc123def456",
        "text_chars": 0,
        "text_sha256_12": "",
        "image_width": image_width,
        "image_height": image_height,
        "status": status,
        "reason_code": "",
        "source_kind": source_kind,
        "source_file_id": source_file_id,
        "created_at": "2026-05-20T00:00:00Z",
        "updated_at": "2026-05-20T00:00:00Z",
        "deleted_at": None,
    }


def _ocr_result():
    return SimpleNamespace(
        status="complete",
        reason_code="",
        ocr_pdf=b"%PDF OCR",
        ocr_engine="stirling-pdf",
        ocr_languages="fra+eng+deu",
        ocr_duration_ms=1200,
        content_type="application/pdf",
        to_dict=lambda: {
            "status": "complete",
            "reason_code": "",
            "ocr_pdf": b"%PDF OCR",
            "ocr_applied": True,
            "ocr_engine": "stirling-pdf",
            "ocr_languages": "fra+eng+deu",
            "ocr_duration_ms": 1200,
            "content_type": "application/pdf",
        },
    )


def _extraction(*, text, filename="scan.pdf", media_type="application/pdf"):
    return SimpleNamespace(
        status="complete",
        reason_code="",
        text=text,
        chars=len(text),
        sha256_12="text12345678",
        filename=filename,
        media_type=media_type,
        source_extension=".md" if filename.endswith(".md") else ".pdf",
    )


if __name__ == "__main__":
    unittest.main()
