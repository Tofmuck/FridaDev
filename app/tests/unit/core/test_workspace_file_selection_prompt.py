from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from core import active_document_prompt_lane
from core import workspace_file_selection_prompt
from core import workspace_file_selections_store
from core import workspace_files_store


class _CaptureLogger:
    def __init__(self):
        self.lines = []

    def info(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def warning(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def error(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))


class _SelectionPromptCursor:
    def __init__(self, conn):
        self.conn = conn
        self.result = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split()).lower()
        params = tuple(params or ())
        self.conn.queries.append(normalized_sql)
        if "from workspace_file_selections" not in normalized_sql:
            raise AssertionError(f"unexpected SQL: {normalized_sql}")
        conversation_id = params[0]
        file_id = params[1] if len(params) > 1 else None
        self.result = [
            dict(row)
            for row in self.conn.rows
            if row["conversation_id"] == conversation_id and (file_id is None or row["workspace_file_id"] == file_id)
        ]

    def fetchall(self):
        return list(self.result)

    def fetchone(self):
        return self.result[0] if self.result else None


class _SelectionPromptConn:
    def __init__(self, rows):
        self.rows = list(rows)
        self.queries = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _SelectionPromptCursor(self)


def _selection_prompt_row(
    *,
    conversation_id,
    folder_id,
    file_id,
    storage_key,
    display_name="note.txt",
    media_kind="text",
    mime_type="text/plain",
    source_extension=".txt",
    byte_size=7,
    sha256_12="abc123def456",
    image_width=0,
    image_height=0,
    file_status="active",
):
    return {
        "conversation_id": conversation_id,
        "workspace_file_id": file_id,
        "selected_at": "2026-05-20T00:10:00Z",
        "selection_updated_at": "2026-05-20T00:10:00Z",
        "selection_deleted_at": None,
        "last_injected_turn_id": "",
        "last_excluded_turn_id": "",
        "last_excluded_reason_code": "",
        "conversation_workspace_folder_id": folder_id,
        "conversation_deleted_at": None,
        "workspace_folder_id": folder_id,
        "display_name": display_name,
        "original_filename": display_name,
        "storage_key": storage_key,
        "content_kind": "image" if media_kind == "image" else "document",
        "media_kind": media_kind,
        "mime_type": mime_type,
        "source_extension": source_extension,
        "byte_size": byte_size,
        "sha256": "full-hash-hidden",
        "sha256_12": sha256_12,
        "text_chars": 0,
        "text_sha256_12": "",
        "image_width": image_width,
        "image_height": image_height,
        "file_status": file_status,
        "file_reason_code": "",
        "source_kind": "upload",
        "source_file_id": None,
        "file_created_at": "2026-05-20T00:00:00Z",
        "file_updated_at": "2026-05-20T00:00:00Z",
        "file_deleted_at": None,
    }


class WorkspaceFileSelectionPromptTests(unittest.TestCase):
    def test_reads_text_bytes_from_disk(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        raw_text = "bonjour depuis le disque"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
            workspace_files_store.write_file_bytes(root, storage_key, raw_text.encode("utf-8"))
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        byte_size=len(raw_text.encode("utf-8")),
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document["source"], workspace_file_selections_store.SOURCE)
        self.assertEqual(document["document_id"], file_id)
        self.assertEqual(document["workspace_file_id"], file_id)
        self.assertEqual(document["workspace_folder_id"], folder_id)
        self.assertEqual(document["media_kind"], "text")
        self.assertTrue(document["injectable"])
        self.assertEqual(document["text_content"], raw_text)
        self.assertGreater(document["token_estimate"], 0)
        encoded = str(document)
        self.assertNotIn("storage_key", document)
        self.assertNotIn("internal_path", document)
        self.assertNotIn(storage_key, encoded)
        self.assertNotIn(str(root), encoded)

    def test_prepares_pdf_text_with_existing_extractor(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"

        class _PdfTextExtraction:
            status = "complete"
            reason_code = ""

            def to_dict(self):
                return {
                    "text": "texte pdf lisible",
                    "text_chars": 17,
                    "token_estimate": 4,
                    "text_sha256_12": "def456abc123",
                }

        class _PdfTextExtractor:
            STATUS_COMPLETE = "complete"
            REASON_OCR_REQUIRED = "document_ocr_required"
            REASON_UNSUPPORTED = "document_type_unsupported"

            @staticmethod
            def extract_active_document_text(_data, *, filename, media_type):
                self.assertEqual(filename, "texte.pdf")
                self.assertEqual(media_type, "application/pdf")
                return _PdfTextExtraction()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".pdf")
            workspace_files_store.write_file_bytes(root, storage_key, b"%PDF text")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="texte.pdf",
                        mime_type="application/pdf",
                        source_extension=".pdf",
                        byte_size=9,
                    )
                ]
            )

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=_CaptureLogger(),
                extractor_module=_PdfTextExtractor,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertTrue(document["injectable"])
        self.assertEqual(document["media_kind"], "text")
        self.assertEqual(document["text_content"], "texte pdf lisible")
        self.assertEqual(document["text_sha256_12"], "def456abc123")

    def test_returns_empty_without_explicit_selection(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        with tempfile.TemporaryDirectory() as tmp:
            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: _SelectionPromptConn([]),
                storage_root=Path(tmp),
                logger=_CaptureLogger(),
            )

        self.assertEqual(documents, [])

    def test_ocr_required_pdf_without_selection_produces_no_multimodal_payload(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        with tempfile.TemporaryDirectory() as tmp:
            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: _SelectionPromptConn([]),
                storage_root=Path(tmp),
                logger=_CaptureLogger(),
            )

        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]
        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            documents,
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 1,
            max_tokens=1000,
        )

        self.assertEqual(documents, [])
        self.assertEqual(lane.injected_count, 0)
        self.assertFalse(any(isinstance(message.get("content"), list) for message in prompt_messages))
        self.assertNotIn("file_data", str(prompt_messages))
        self.assertNotIn("data:application/pdf", str(prompt_messages))

    def test_defers_image_without_visual_payload(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        image_bytes = b"\x89PNG\r\nimagebytes"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".png")
            workspace_files_store.write_file_bytes(root, storage_key, image_bytes)
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="capture.png",
                        media_kind="image",
                        mime_type="image/png",
                        source_extension=".png",
                        byte_size=len(image_bytes),
                        image_width=40,
                        image_height=30,
                    )
                ]
            )

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=_CaptureLogger(),
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertEqual(document["source"], workspace_file_selections_store.SOURCE)
        self.assertEqual(document["media_kind"], "image")
        self.assertFalse(document["injectable"])
        self.assertEqual(document["reason_code"], "folder_document_pdf_visual_required")
        self.assertNotIn("image_content", document)
        self.assertNotIn("file_content", document)
        self.assertNotIn("text_content", document)
        encoded = str(document)
        self.assertNotIn("storage_key", document)
        self.assertNotIn("internal_path", document)
        self.assertNotIn(storage_key, encoded)
        self.assertNotIn(str(root), encoded)
        self.assertNotIn("data:image", encoded)
        self.assertNotIn("base64", encoded)

    def test_excludes_disk_missing_content_free(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertFalse(document["injectable"])
        self.assertEqual(document["reason_code"], "workspace_file_disk_missing")
        self.assertNotIn("text_content", document)
        self.assertNotIn("image_content", document)
        logged = "\n".join(logger.lines)
        self.assertIn("workspace_files_selection_prompt_excluded", logged)
        self.assertIn("reason_code=workspace_file_disk_missing", logged)
        self.assertNotIn(storage_key, logged)
        self.assertNotIn(str(root), logged)

    def test_marks_ocr_required_pdf_visual_required(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        pdf_bytes = b"%PDF scanned"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".pdf")
            workspace_files_store.write_file_bytes(root, storage_key, pdf_bytes)
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="scan.pdf",
                        mime_type="application/pdf",
                        source_extension=".pdf",
                        byte_size=len(pdf_bytes),
                        file_status=workspace_files_store.STATUS_OCR_REQUIRED,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertFalse(document["injectable"])
        self.assertEqual(document["media_kind"], "text")
        self.assertEqual(document["media_type"], "application/pdf")
        self.assertEqual(document["reason_code"], "folder_document_pdf_visual_required")
        self.assertNotIn("text_content", document)
        self.assertNotIn("image_content", document)
        self.assertNotIn("file_content", document)
        encoded = str(document)
        self.assertNotIn("storage_key", document)
        self.assertNotIn("internal_path", document)
        self.assertNotIn(storage_key, encoded)
        self.assertNotIn(str(root), encoded)
        logged = "\n".join(logger.lines)
        self.assertIn("workspace_files_selection_prompt_excluded", logged)
        self.assertIn("reason_code=folder_document_pdf_visual_required", logged)
        self.assertNotIn(storage_key, logged)
        self.assertNotIn(str(root), logged)

    def test_maps_pdf_extraction_ocr_required_to_visual_required(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"

        class _OcrRequiredExtraction:
            status = "ocr_required"
            reason_code = "document_ocr_required"

        class _OcrRequiredExtractor:
            STATUS_COMPLETE = "complete"
            REASON_OCR_REQUIRED = "document_ocr_required"
            REASON_UNSUPPORTED = "document_type_unsupported"

            @staticmethod
            def extract_active_document_text(_data, *, filename, media_type):
                return _OcrRequiredExtraction()

        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".pdf")
            workspace_files_store.write_file_bytes(root, storage_key, b"%PDF scanned")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="scan.pdf",
                        mime_type="application/pdf",
                        source_extension=".pdf",
                        byte_size=12,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
                extractor_module=_OcrRequiredExtractor,
            )

        self.assertEqual(len(documents), 1)
        self.assertFalse(documents[0]["injectable"])
        self.assertEqual(documents[0]["reason_code"], "folder_document_pdf_visual_required")
        self.assertNotIn("file_content", documents[0])
        self.assertIn("reason_code=folder_document_pdf_visual_required", "\n".join(logger.lines))

    def test_keeps_non_pdf_ocr_required_excluded(self) -> None:
        conversation_id = "11111111-1111-4111-8111-111111111111"
        folder_id = "22222222-2222-4222-8222-222222222222"
        file_id = "33333333-3333-4333-8333-333333333333"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
            workspace_files_store.write_file_bytes(root, storage_key, b"scan")
            conn = _SelectionPromptConn(
                [
                    _selection_prompt_row(
                        conversation_id=conversation_id,
                        folder_id=folder_id,
                        file_id=file_id,
                        storage_key=storage_key,
                        display_name="scan.txt",
                        mime_type="text/plain",
                        source_extension=".txt",
                        byte_size=4,
                        file_status=workspace_files_store.STATUS_OCR_REQUIRED,
                    )
                ]
            )
            logger = _CaptureLogger()

            documents = workspace_file_selection_prompt.list_selected_files_for_prompt(
                conversation_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

        self.assertEqual(len(documents), 1)
        document = documents[0]
        self.assertFalse(document["injectable"])
        self.assertEqual(document["reason_code"], "workspace_file_ocr_required")
        self.assertNotIn("text_content", document)
        self.assertNotIn("image_content", document)
        self.assertNotIn("file_content", document)
        self.assertIn("reason_code=workspace_file_ocr_required", "\n".join(logger.lines))


if __name__ == "__main__":
    unittest.main()
