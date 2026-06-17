from __future__ import annotations

import unittest
from types import SimpleNamespace

from core import workspace_document_nextcloud_client
from core import workspace_document_nextcloud_runtime
from core import workspace_files_service


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
FILE_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _UploadFile:
    def __init__(self, data: bytes, filename: str, mimetype: str = "text/plain"):
        self._data = data
        self.filename = filename
        self.mimetype = mimetype
        self.read_called = False

    def read(self):
        self.read_called = True
        return self._data


class _Files:
    def __init__(self, file_obj):
        self.file_obj = file_obj

    def getlist(self, name):
        return [self.file_obj] if name == workspace_files_service.UPLOAD_FIELD else []


class _FakeFolders:
    def __init__(self, *, linked: bool = True):
        self.folder = {
            "id": FOLDER_ID,
            "display_name": "Projet",
            "nextcloud_target_name": "Projet",
            "nextcloud_sync_state": "linked" if linked else "local_only",
            "deleted_at": None,
        }

    def normalize_workspace_folder_id(self, value):
        return FOLDER_ID if str(value or "") == FOLDER_ID else None

    def get_workspace_folder(self, folder_id):
        return dict(self.folder) if folder_id == FOLDER_ID else None


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"

    def __init__(self, *, existing=None, fail_store: bool = False):
        self.existing = list(existing or [])
        self.fail_store = fail_store
        self.stored = []
        self.events = []

    def sanitize_display_name(self, value):
        return " ".join(str(value or "").strip().split())[:180].rstrip() or "fichier"

    def list_workspace_files(self, folder_id):
        return list(self.existing + self.stored)

    def store_uploaded_file(self, folder_id, *, original_filename, content, metadata):
        if self.fail_store:
            return None
        item = {
            "id": FILE_ID,
            "workspace_folder_id": folder_id,
            "display_name": metadata.get("display_name") or original_filename,
            "original_filename": original_filename,
            "content_kind": metadata.get("content_kind", "document"),
            "media_kind": metadata.get("media_kind", "text"),
            "mime_type": metadata.get("mime_type", "text/plain"),
            "source_extension": metadata.get("source_extension", ".txt"),
            "byte_size": len(content or b""),
            "sha256_12": "abc123def456",
            "text_chars": metadata.get("text_chars", 0),
            "text_sha256_12": metadata.get("text_sha256_12", ""),
            "status": metadata.get("status", "active"),
            "reason_code": metadata.get("reason_code", ""),
            "source_kind": "upload",
            "deleted_at": None,
        }
        self.stored.append(item)
        return dict(item)

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeImageValidator:
    STATUS_COMPLETE = "complete"

    def validate_active_image_upload(self, content, *, filename, declared_media_type):
        return SimpleNamespace(is_image_candidate=False)


class _FakeExtractor:
    STATUS_COMPLETE = "complete"
    STATUS_OCR_REQUIRED = "ocr_required"
    STATUS_UNSUPPORTED = "unsupported"

    def __init__(
        self,
        *,
        status="complete",
        filename="note.txt",
        media_type="text/plain",
        source_extension=".txt",
        chars=7,
        reason_code="",
    ):
        self._result = SimpleNamespace(
            status=status,
            filename=filename,
            media_type=media_type,
            source_extension=source_extension,
            chars=chars,
            sha256_12="text1234567",
            reason_code=reason_code,
            to_dict=lambda: {
                "status": status,
                "media_type": media_type,
                "source_extension": source_extension,
                "byte_size": 7,
                "reason_code": reason_code,
            },
        )

    def extract_active_document_text(self, content, *, filename, media_type):
        return self._result


class _FakeNextcloud:
    def __init__(self, *, status_reason="", put_reason=""):
        self.status_reason = status_reason
        self.put_reason = put_reason
        self.status_calls = []
        self.put_calls = []
        self.deleted = []

    def documents_status(self, folder_name):
        self.status_calls.append(folder_name)
        if self.status_reason:
            raise workspace_document_nextcloud_client.NextcloudDocumentClientError(
                self.status_reason,
                http_status=207 if self.status_reason == workspace_document_nextcloud_client.REASON_DOCUMENTS_TARGET_NOT_COLLECTION else 404,
            )
        return workspace_document_nextcloud_client.NextcloudDocumentResponse(
            True,
            workspace_document_nextcloud_client.REASON_UPLOAD_OK,
            207,
        )

    def put_document(self, folder_name, document_name, content, *, media_type=""):
        self.put_calls.append((folder_name, document_name, len(content or b""), media_type))
        if self.put_reason:
            raise workspace_document_nextcloud_client.NextcloudDocumentClientError(
                self.put_reason,
                http_status=412,
            )
        return workspace_document_nextcloud_client.NextcloudDocumentResponse(
            True,
            workspace_document_nextcloud_client.REASON_UPLOAD_OK,
            201,
        )

    def delete_document(self, folder_name, document_name, *, missing_ok=True):
        self.deleted.append((folder_name, document_name, missing_ok))
        return workspace_document_nextcloud_client.NextcloudDocumentResponse(
            True,
            workspace_document_nextcloud_client.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _RuntimeAdapter:
    def __init__(self, nextcloud):
        self.nextcloud = nextcloud

    def store_workspace_document_nextcloud_first(self, **kwargs):
        return workspace_document_nextcloud_runtime.store_workspace_document_nextcloud_first(
            **kwargs,
            nextcloud=self.nextcloud,
        )


def _upload_response(*, extractor, linked=True, nextcloud=None, files_store=None, filename="note.txt"):
    return workspace_files_service.upload_workspace_file_response(
        FOLDER_ID,
        _Files(_UploadFile(b"bonjour", filename, "text/plain")),
        workspace_folders_module=_FakeFolders(linked=linked),
        workspace_files_module=files_store or _FakeWorkspaceFiles(),
        extractor_module=extractor,
        image_validator_module=_FakeImageValidator(),
        documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud or _FakeNextcloud()),
    )


class DocumentsV1IngestionTests(unittest.TestCase):
    def test_upload_refuses_non_linked_folder_without_reading_file(self) -> None:
        file_obj = _UploadFile(b"bonjour", "note.txt")
        payload, status = workspace_files_service.upload_workspace_file_response(
            FOLDER_ID,
            _Files(file_obj),
            workspace_folders_module=_FakeFolders(linked=False),
            workspace_files_module=_FakeWorkspaceFiles(),
            extractor_module=_FakeExtractor(),
            image_validator_module=_FakeImageValidator(),
            documents_nextcloud_runtime_module=_RuntimeAdapter(_FakeNextcloud()),
        )

        self.assertEqual(status, 409)
        self.assertEqual(payload["reason_code"], "folder_document_folder_not_linked")
        self.assertFalse(file_obj.read_called)

    def test_upload_refuses_missing_or_non_collection_documents_target(self) -> None:
        for reason in (
            workspace_document_nextcloud_client.REASON_DOCUMENTS_TARGET_MISSING,
            workspace_document_nextcloud_client.REASON_DOCUMENTS_TARGET_NOT_COLLECTION,
        ):
            payload, status = _upload_response(
                extractor=_FakeExtractor(),
                nextcloud=_FakeNextcloud(status_reason=reason),
            )
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["reason_code"], reason)
            self.assertIn(status, {404, 409})

    def test_upload_refuses_local_sanitized_name_conflict_before_nextcloud(self) -> None:
        nextcloud = _FakeNextcloud()
        files = _FakeWorkspaceFiles(
            existing=[
                {
                    "id": "bbbbbbbb-bbbb-4ccc-8ddd-bbbbbbbbbbbb",
                    "display_name": "note.txt",
                    "source_extension": ".txt",
                    "deleted_at": None,
                }
            ]
        )
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=nextcloud,
            files_store=files,
        )

        self.assertEqual(status, 409)
        self.assertEqual(payload["reason_code"], "folder_document_name_conflict")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])

    def test_upload_refuses_nextcloud_overwrite_conflict(self) -> None:
        files = _FakeWorkspaceFiles()
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=_FakeNextcloud(
                put_reason=workspace_document_nextcloud_client.REASON_NAME_CONFLICT
            ),
            files_store=files,
        )

        self.assertEqual(status, 409)
        self.assertEqual(payload["reason_code"], "folder_document_name_conflict")
        self.assertEqual(files.stored, [])

    def test_text_and_pdf_uploads_are_stored_and_projected_content_free(self) -> None:
        text_payload, text_status = _upload_response(extractor=_FakeExtractor())
        self.assertEqual(text_status, 201)
        self.assertEqual(text_payload["file"]["document_v1_user"]["display_name"], "note.txt")
        self.assertEqual(text_payload["file"]["document_v1_status"], "readable")
        self.assertEqual(text_payload["document_nextcloud"]["reason_code"], "folder_document_upload_ok")
        encoded_technical = str(text_payload["file"]["document_v1_technical"])
        self.assertNotIn("note.txt", encoded_technical)
        self.assertNotIn("storage_key", str(text_payload))
        self.assertNotIn("remote.php", str(text_payload))
        self.assertNotIn("<d:", str(text_payload))

        pdf_payload, pdf_status = _upload_response(
            extractor=_FakeExtractor(
                filename="scan.pdf",
                media_type="application/pdf",
                source_extension=".pdf",
                chars=12,
            ),
            filename="scan.pdf",
        )
        self.assertEqual(pdf_status, 201)
        self.assertEqual(pdf_payload["file"]["document_v1_status"], "pdf_text")

    def test_pdf_without_text_is_accepted_as_visual_required(self) -> None:
        payload, status = _upload_response(
            extractor=_FakeExtractor(
                status="ocr_required",
                filename="scan.pdf",
                media_type="application/pdf",
                source_extension=".pdf",
                chars=0,
                reason_code="document_ocr_required",
            ),
            filename="scan.pdf",
        )

        self.assertEqual(status, 201)
        self.assertEqual(payload["file"]["document_v1_status"], "pdf_visual_required")
        self.assertEqual(payload["file"]["document_v1_reason_code"], "folder_document_pdf_visual_required")

    def test_unsupported_type_is_refused_before_nextcloud(self) -> None:
        nextcloud = _FakeNextcloud()
        payload, status = _upload_response(
            extractor=_FakeExtractor(
                status="unsupported",
                filename="loop.gif",
                media_type="image/gif",
                source_extension=".gif",
                reason_code="document_type_unsupported",
            ),
            nextcloud=nextcloud,
            filename="loop.gif",
        )

        self.assertEqual(status, 422)
        self.assertEqual(payload["reason_code"], "folder_document_type_unsupported")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])

    def test_missing_extension_is_rejected_before_nextcloud(self) -> None:
        nextcloud = _FakeNextcloud()
        payload, status = _upload_response(
            extractor=_FakeExtractor(
                filename="note",
                media_type="text/plain",
                source_extension="",
                chars=7,
            ),
            nextcloud=nextcloud,
            filename="note",
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["reason_code"], "folder_document_name_invalid")
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])

    def test_remote_created_file_is_compensated_when_local_persistence_fails(self) -> None:
        nextcloud = _FakeNextcloud()
        result = workspace_document_nextcloud_runtime.store_workspace_document_nextcloud_first(
            folder=_FakeFolders(linked=True).folder,
            content=b"bonjour",
            original_filename="note.txt",
            metadata={
                "display_name": "note.txt",
                "mime_type": "text/plain",
                "source_extension": ".txt",
                "status": "active",
            },
            workspace_files_module=_FakeWorkspaceFiles(fail_store=True),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_document_local_persistence_failed")
        self.assertTrue(result["document_nextcloud"]["rollback"]["ok"])
        self.assertEqual(nextcloud.deleted[0][0], "Projet")
        self.assertNotIn("note.txt", str(result["document_nextcloud"]))


if __name__ == "__main__":
    unittest.main()
