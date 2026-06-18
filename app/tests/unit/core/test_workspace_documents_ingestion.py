from __future__ import annotations

import unittest
from types import SimpleNamespace

from core import workspace_document_nextcloud_client
from core import workspace_document_existing_files
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
    def __init__(self, *, linked: bool = True, fail_list: bool = False):
        self.fail_list = fail_list
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

    def list_workspace_folders(self):
        if self.fail_list:
            raise RuntimeError("redacted")
        return [dict(self.folder)]


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"

    def __init__(
        self,
        *,
        existing=None,
        fail_store: bool = False,
        fail_link: bool = False,
        fail_delete: bool = False,
        fail_link_lookup: bool = False,
        fail_mark_deleted: bool = False,
        fail_list: bool = False,
    ):
        self.existing = list(existing or [])
        self.fail_store = fail_store
        self.fail_link = fail_link
        self.fail_delete = fail_delete
        self.fail_link_lookup = fail_link_lookup
        self.fail_mark_deleted = fail_mark_deleted
        self.fail_list = fail_list
        self.stored = []
        self.events = []
        self.links = {}
        self.deleted = []
        self.reads = []

    def sanitize_display_name(self, value):
        return " ".join(str(value or "").strip().split())[:180].rstrip() or "fichier"

    def normalize_workspace_file_id(self, value):
        return str(value or "") if str(value or "") else None

    def list_workspace_files(self, folder_id):
        if self.fail_list:
            raise RuntimeError("redacted")
        return list(self.existing + self.stored)

    def get_workspace_file_storage_row(self, folder_id, file_id):
        for item in self.existing + self.stored:
            if item.get("workspace_folder_id", FOLDER_ID) == folder_id and item.get("id") == file_id:
                storage_key = item.get("storage_key") or f"{folder_id}/{file_id}.bin"
                return {**item, "storage_key": storage_key}
        return None

    def read_file_bytes(self, storage_key):
        self.reads.append(storage_key)
        return b"existing-bytes"

    def store_uploaded_file(self, folder_id, *, original_filename, content, metadata, file_id=FILE_ID):
        if self.fail_store:
            return None
        item = {
            "id": file_id or FILE_ID,
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

    def delete_workspace_file(self, folder_id, file_id):
        if self.fail_delete:
            return None
        for item in self.stored:
            if item["workspace_folder_id"] == folder_id and item["id"] == file_id and not item.get("deleted_at"):
                item["deleted_at"] = "2026-06-17T00:00:00Z"
                item["status"] = "deleted"
                item["disk_deleted"] = True
                self.deleted.append((folder_id, file_id))
                return dict(item)
        for item in self.existing:
            if (
                item.get("workspace_folder_id", FOLDER_ID) == folder_id
                and item["id"] == file_id
                and not item.get("deleted_at")
            ):
                item["deleted_at"] = "2026-06-17T00:00:00Z"
                item["status"] = "deleted"
                item["disk_deleted"] = True
                self.deleted.append((folder_id, file_id))
                return dict(item)
        return None

    def upsert_nextcloud_link(self, **fields):
        if self.fail_link:
            raise RuntimeError("redacted")
        link = {
            "workspace_file_id": fields["workspace_file_id"],
            "workspace_folder_id": fields["workspace_folder_id"],
            "nextcloud_sync_state": fields["nextcloud_sync_state"],
            "nextcloud_document_ref": fields["nextcloud_document_ref"],
            "nextcloud_name_hash": fields["nextcloud_name_hash"],
            "nextcloud_target_name": fields["nextcloud_target_name"],
            "last_sync_reason_code": fields["last_sync_reason_code"],
            "last_sync_operation": fields["last_sync_operation"],
        }
        self.links[fields["workspace_file_id"]] = link
        return dict(link)

    def get_nextcloud_link(self, file_id, *, fail_closed=False):
        if self.fail_link_lookup:
            raise RuntimeError("redacted")
        link = self.links.get(file_id)
        return dict(link) if link else None

    def mark_nextcloud_link_deleted(self, file_id, *, reason_code):
        if self.fail_mark_deleted:
            return None
        if file_id not in self.links:
            return None
        self.links[file_id]["nextcloud_sync_state"] = "deleted"
        self.links[file_id]["last_sync_reason_code"] = reason_code
        self.links[file_id]["last_sync_operation"] = "delete"
        return dict(self.links[file_id])

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
    def __init__(
        self,
        *,
        status_reason="",
        put_reason="",
        put_status=201,
        delete_reason="",
        existing_targets=None,
    ):
        self.status_reason = status_reason
        self.put_reason = put_reason
        self.put_status = put_status
        self.delete_reason = delete_reason
        self.existing_targets = set(existing_targets or set())
        self.status_calls = []
        self.document_status_calls = []
        self.put_calls = []
        self.deleted = []

    def documents_status(self, folder_name):
        self.status_calls.append(folder_name)
        if self.status_reason:
            raise workspace_document_nextcloud_client.NextcloudDocumentClientError(
                self.status_reason,
                http_status=207
                if self.status_reason == workspace_document_nextcloud_client.REASON_DOCUMENTS_TARGET_NOT_COLLECTION
                else 404,
            )
        return workspace_document_nextcloud_client.NextcloudDocumentResponse(
            True,
            workspace_document_nextcloud_client.REASON_UPLOAD_OK,
            207,
        )

    def document_status(self, folder_name, document_name):
        self.document_status_calls.append((folder_name, document_name))
        if (folder_name, document_name) in self.existing_targets:
            return workspace_document_nextcloud_client.NextcloudDocumentResponse(
                True,
                workspace_document_nextcloud_client.REASON_UPLOAD_OK,
                207,
            )
        raise workspace_document_nextcloud_client.NextcloudDocumentClientError(
            workspace_document_nextcloud_client.REASON_DOCUMENTS_TARGET_MISSING,
            http_status=404,
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
            self.put_status,
        )

    def delete_document(self, folder_name, document_name, *, missing_ok=True):
        self.deleted.append((folder_name, document_name, missing_ok))
        if self.delete_reason:
            raise workspace_document_nextcloud_client.NextcloudDocumentClientError(
                self.delete_reason,
                http_status=503,
            )
        return workspace_document_nextcloud_client.NextcloudDocumentResponse(
            True,
            workspace_document_nextcloud_client.REASON_DELETE_OK,
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

    def prepare_workspace_document_delete_nextcloud_first(self, **kwargs):
        return workspace_document_nextcloud_runtime.prepare_workspace_document_delete_nextcloud_first(
            **kwargs,
            nextcloud=self.nextcloud,
        )

    def complete_workspace_document_delete(self, **kwargs):
        return workspace_document_nextcloud_runtime.complete_workspace_document_delete(**kwargs)


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
        files = _FakeWorkspaceFiles()
        text_payload, text_status = _upload_response(extractor=_FakeExtractor(), files_store=files)
        self.assertEqual(text_status, 201)
        self.assertEqual(text_payload["file"]["document_v1_user"]["display_name"], "note.txt")
        self.assertEqual(text_payload["file"]["document_v1_status"], "readable")
        self.assertEqual(text_payload["file"]["document_v1_user"]["nextcloud_sync_state"], "linked")
        self.assertEqual(text_payload["file"]["document_v1_technical"]["nextcloud_sync_state"], "linked")
        self.assertEqual(text_payload["document_nextcloud"]["reason_code"], "folder_document_upload_ok")
        encoded_technical = str(text_payload["file"]["document_v1_technical"])
        self.assertNotIn("note.txt", encoded_technical)
        self.assertNotIn("nextcloud_target_name", str(text_payload["file"]))
        self.assertNotIn("storage_key", str(text_payload))
        self.assertNotIn("remote.php", str(text_payload))
        self.assertNotIn("<d:", str(text_payload))
        link = files.get_nextcloud_link(text_payload["file"]["id"])
        self.assertIsNotNone(link)
        self.assertEqual(link["workspace_file_id"], text_payload["file"]["id"])
        self.assertEqual(link["nextcloud_sync_state"], "linked")
        self.assertEqual(text_payload["document_nextcloud"]["document_link_state"], "linked")

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

    def test_link_persistence_failure_rolls_back_remote_and_local_file(self) -> None:
        nextcloud = _FakeNextcloud()
        files = _FakeWorkspaceFiles(fail_link=True)
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
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_document_link_persistence_failed")
        self.assertTrue(result["document_nextcloud"]["rollback"]["remote"]["ok"])
        self.assertTrue(result["document_nextcloud"]["rollback"]["local"]["ok"])
        self.assertEqual(len(files.deleted), 1)
        self.assertEqual(nextcloud.deleted[0][0], "Projet")
        self.assertNotIn("note.txt", str(result["document_nextcloud"]))

    def test_delete_linked_document_deletes_exact_remote_before_local_tombstone(self) -> None:
        nextcloud = _FakeNextcloud()
        files = _FakeWorkspaceFiles()
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=nextcloud,
            files_store=files,
        )
        self.assertEqual(status, 201)
        file_id = payload["file"]["id"]

        delete_payload, delete_status = workspace_files_service.delete_workspace_file_response(
            FOLDER_ID,
            file_id,
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud),
        )

        self.assertEqual(delete_status, 200)
        self.assertTrue(delete_payload["file"]["disk_deleted"])
        self.assertEqual(nextcloud.deleted[-1], ("Projet", "note.txt", True))
        self.assertEqual(files.get_nextcloud_link(file_id)["nextcloud_sync_state"], "deleted")
        self.assertEqual(delete_payload["document_nextcloud"]["link_mark_state"], "deleted")

    def test_delete_remote_failure_does_not_tombstone_local_linked_document(self) -> None:
        nextcloud = _FakeNextcloud(delete_reason=workspace_document_nextcloud_client.REASON_REMOTE_DELETE_FAILED)
        files = _FakeWorkspaceFiles()
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=_FakeNextcloud(),
            files_store=files,
        )
        self.assertEqual(status, 201)

        delete_payload, delete_status = workspace_files_service.delete_workspace_file_response(
            FOLDER_ID,
            payload["file"]["id"],
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud),
        )

        self.assertEqual(delete_status, 502)
        self.assertEqual(delete_payload["reason_code"], "folder_document_remote_delete_failed")
        self.assertEqual(files.deleted, [])
        self.assertIsNone(files.stored[0].get("deleted_at"))

    def test_delete_link_lookup_failure_fails_closed_without_local_tombstone(self) -> None:
        nextcloud = _FakeNextcloud()
        files = _FakeWorkspaceFiles()
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=nextcloud,
            files_store=files,
        )
        self.assertEqual(status, 201)
        files.fail_link_lookup = True

        delete_payload, delete_status = workspace_files_service.delete_workspace_file_response(
            FOLDER_ID,
            payload["file"]["id"],
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud),
        )

        self.assertEqual(delete_status, 503)
        self.assertEqual(delete_payload["reason_code"], "folder_document_link_lookup_failed")
        self.assertEqual(delete_payload["document_nextcloud"]["delete_state"], "link_lookup_failed")
        self.assertEqual(len(nextcloud.deleted), 0)
        self.assertEqual(files.deleted, [])
        self.assertIsNone(files.stored[0].get("deleted_at"))
        self.assertNotIn("note.txt", str(delete_payload.get("document_nextcloud", {})))

    def test_delete_link_mark_failure_is_reported_after_remote_and_local_delete(self) -> None:
        nextcloud = _FakeNextcloud()
        files = _FakeWorkspaceFiles(fail_mark_deleted=True)
        payload, status = _upload_response(
            extractor=_FakeExtractor(),
            nextcloud=nextcloud,
            files_store=files,
        )
        self.assertEqual(status, 201)
        file_id = payload["file"]["id"]

        delete_payload, delete_status = workspace_files_service.delete_workspace_file_response(
            FOLDER_ID,
            file_id,
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud),
        )

        self.assertEqual(delete_status, 200)
        self.assertTrue(delete_payload["file"]["disk_deleted"])
        self.assertEqual(nextcloud.deleted[-1], ("Projet", "note.txt", True))
        self.assertEqual(files.get_nextcloud_link(file_id)["nextcloud_sync_state"], "linked")
        self.assertEqual(delete_payload["document_nextcloud"]["link_mark_state"], "failed")
        self.assertEqual(
            delete_payload["document_nextcloud"]["link_mark_reason_code"],
            "folder_document_link_mark_failed",
        )
        self.assertNotIn("note.txt", str(delete_payload.get("document_nextcloud", {})))

    def test_local_only_file_without_nextcloud_link_keeps_local_delete_behavior(self) -> None:
        files = _FakeWorkspaceFiles()
        stored = files.store_uploaded_file(
            FOLDER_ID,
            original_filename="legacy.txt",
            content=b"legacy",
            metadata={"display_name": "legacy.txt", "source_extension": ".txt"},
            file_id=FILE_ID,
        )
        nextcloud = _FakeNextcloud()

        payload, status = workspace_files_service.delete_workspace_file_response(
            FOLDER_ID,
            stored["id"],
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            documents_nextcloud_runtime_module=_RuntimeAdapter(nextcloud),
        )

        self.assertEqual(status, 200)
        self.assertTrue(payload["file"]["disk_deleted"])
        self.assertEqual(nextcloud.deleted, [])

    def test_list_documents_shows_linked_and_local_only_states_content_free(self) -> None:
        files = _FakeWorkspaceFiles()
        linked = files.store_uploaded_file(
            FOLDER_ID,
            original_filename="note.txt",
            content=b"bonjour",
            metadata={"display_name": "note.txt", "source_extension": ".txt", "text_chars": 7},
            file_id=FILE_ID,
        )
        local = files.store_uploaded_file(
            FOLDER_ID,
            original_filename="legacy.pdf",
            content=b"legacy",
            metadata={
                "display_name": "legacy.pdf",
                "source_extension": ".pdf",
                "mime_type": "application/pdf",
            },
            file_id="bbbbbbbb-bbbb-4ccc-8ddd-bbbbbbbbbbbb",
        )
        files.upsert_nextcloud_link(
            workspace_file_id=linked["id"],
            workspace_folder_id=FOLDER_ID,
            nextcloud_sync_state="linked",
            nextcloud_document_ref="workspace-file:aaaaaaaa:abc123def456",
            nextcloud_name_hash="abc123def456",
            nextcloud_target_name="Projet secret.txt",
            last_sync_reason_code="folder_document_upload_ok",
            last_sync_operation="upload",
        )

        payload, status = workspace_files_service.list_workspace_files_response(
            FOLDER_ID,
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
        )

        self.assertEqual(status, 200)
        self.assertEqual(len(payload["items"]), 2)
        linked_item = payload["items"][0]
        local_item = payload["items"][1]
        self.assertEqual(linked_item["document_v1_user"]["display_name"], "note.txt")
        self.assertEqual(linked_item["document_v1_user"]["nextcloud_sync_state"], "linked")
        self.assertEqual(linked_item["document_v1_technical"]["nextcloud_sync_state"], "linked")
        self.assertEqual(local_item["document_v1_user"]["display_name"], "legacy.pdf")
        self.assertEqual(local_item["document_v1_user"]["nextcloud_sync_state"], "local_only")
        self.assertEqual(local_item["document_v1_technical"]["nextcloud_sync_state"], "local_only")
        encoded_technical = str([item["document_v1_technical"] for item in payload["items"]])
        self.assertNotIn("note.txt", encoded_technical)
        self.assertNotIn("legacy.pdf", encoded_technical)
        self.assertNotIn("Projet secret", encoded_technical)
        self.assertNotIn("nextcloud_target_name", encoded_technical)

    def test_list_documents_link_lookup_failure_is_visible_and_redacted(self) -> None:
        files = _FakeWorkspaceFiles(fail_link_lookup=True)
        files.store_uploaded_file(
            FOLDER_ID,
            original_filename="note.txt",
            content=b"bonjour",
            metadata={"display_name": "note.txt", "source_extension": ".txt", "text_chars": 7},
            file_id=FILE_ID,
        )

        payload, status = workspace_files_service.list_workspace_files_response(
            FOLDER_ID,
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
        )

        self.assertEqual(status, 200)
        item = payload["items"][0]
        self.assertEqual(item["document_v1_user"]["nextcloud_sync_state"], "sync_error")
        self.assertEqual(item["document_v1_user"]["nextcloud_reason_code"], "folder_document_link_lookup_failed")
        self.assertEqual(item["document_v1_technical"]["nextcloud_sync_state"], "sync_error")
        self.assertEqual(item["document_v1_technical"]["nextcloud_reason_code"], "folder_document_link_lookup_failed")
        self.assertEqual(files.events[-1][0], "documents_v1_list_link_lookup_failed")
        self.assertNotIn("note.txt", str(files.events[-1][1]))

    def test_document_client_rejects_update_like_put_statuses(self) -> None:
        class _Client(workspace_document_nextcloud_client.NextcloudDocumentClient):
            def __init__(self, status):
                self._status = status

            def _url(self, *segments):
                return "redacted"

            def _request_status(self, method, url, *, data=None, headers=None):
                return self._status

        for status in (200, 204):
            with self.assertRaises(workspace_document_nextcloud_client.NextcloudDocumentClientError) as ctx:
                _Client(status).put_document("Projet", "note.txt", b"x", media_type="text/plain")
            self.assertEqual(ctx.exception.reason_code, "folder_document_name_conflict")

    def test_existing_local_only_file_is_copied_and_linked_without_source_delete(self) -> None:
        files = _FakeWorkspaceFiles(
            existing=[
                {
                    "id": FILE_ID,
                    "workspace_folder_id": FOLDER_ID,
                    "display_name": "legacy.txt",
                    "original_filename": "legacy.txt",
                    "source_extension": ".txt",
                    "mime_type": "text/plain",
                    "status": "active",
                    "deleted_at": None,
                }
            ]
        )
        nextcloud = _FakeNextcloud()

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["verdict"], "met")
        self.assertEqual(result["summary"]["copied_files"], 1)
        self.assertEqual(result["summary"]["source_preserved_files"], 1)
        self.assertEqual(files.deleted, [])
        self.assertEqual(nextcloud.put_calls[0], ("Projet", "legacy.txt", len(b"existing-bytes"), "text/plain"))
        link = files.get_nextcloud_link(FILE_ID)
        self.assertEqual(link["nextcloud_sync_state"], "linked")
        self.assertEqual(link["last_sync_operation"], "reconcile")
        self.assertEqual(link["last_sync_reason_code"], "folder_document_existing_copy_ok")
        encoded = str(result)
        self.assertNotIn("legacy.txt", encoded)
        self.assertNotIn("existing-bytes", encoded)
        self.assertNotIn("storage_key", encoded)
        self.assertNotIn("remote.php", encoded)

    def test_existing_file_inventory_folder_failure_fails_closed(self) -> None:
        files = _FakeWorkspaceFiles()
        nextcloud = _FakeNextcloud()

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True, fail_list=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["verdict"], "failed")
        self.assertEqual(result["summary"]["error_files"], 1)
        self.assertEqual(result["summary"]["active_files"], 0)
        self.assertEqual(result["events"][0]["operation"], "inventory_folders")
        self.assertEqual(result["events"][0]["reason_code"], "folder_document_existing_inventory_failed")
        self.assertEqual(nextcloud.put_calls, [])
        self.assertEqual(nextcloud.deleted, [])
        self.assertNotIn("redacted", str(result))

    def test_existing_file_inventory_file_failure_fails_closed(self) -> None:
        files = _FakeWorkspaceFiles(fail_list=True)
        nextcloud = _FakeNextcloud()

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["verdict"], "failed")
        self.assertEqual(result["summary"]["active_folders"], 1)
        self.assertEqual(result["summary"]["error_files"], 1)
        self.assertEqual(result["folders"][0]["error_files"], 1)
        self.assertEqual(result["events"][0]["operation"], "inventory_files")
        self.assertEqual(result["events"][0]["reason_code"], "folder_document_existing_inventory_failed")
        self.assertEqual(nextcloud.put_calls, [])
        self.assertEqual(nextcloud.deleted, [])
        self.assertNotIn("redacted", str(result))

    def test_existing_file_conflict_does_not_overwrite_or_link(self) -> None:
        files = _FakeWorkspaceFiles(
            existing=[
                {
                    "id": FILE_ID,
                    "workspace_folder_id": FOLDER_ID,
                    "display_name": "legacy.txt",
                    "source_extension": ".txt",
                    "mime_type": "text/plain",
                    "status": "active",
                    "deleted_at": None,
                }
            ]
        )
        nextcloud = _FakeNextcloud(existing_targets={("Projet", "legacy.txt")})

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertEqual(result["verdict"], "partial")
        self.assertEqual(result["summary"]["conflict_files"], 1)
        self.assertEqual(result["summary"]["copied_files"], 0)
        self.assertEqual(nextcloud.put_calls, [])
        self.assertIsNone(files.get_nextcloud_link(FILE_ID))
        self.assertEqual(result["events"][0]["reason_code"], "folder_document_existing_copy_conflict")

    def test_existing_file_link_failure_rolls_back_remote_only(self) -> None:
        files = _FakeWorkspaceFiles(
            existing=[
                {
                    "id": FILE_ID,
                    "workspace_folder_id": FOLDER_ID,
                    "display_name": "legacy.txt",
                    "source_extension": ".txt",
                    "mime_type": "text/plain",
                    "status": "active",
                    "deleted_at": None,
                }
            ],
            fail_link=True,
        )
        nextcloud = _FakeNextcloud()

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["verdict"], "failed")
        self.assertEqual(result["summary"]["error_files"], 1)
        self.assertEqual(result["summary"]["rollback_ok"], 1)
        self.assertEqual(nextcloud.deleted, [("Projet", "legacy.txt", True)])
        self.assertEqual(files.deleted, [])
        self.assertEqual(result["events"][0]["reason_code"], "folder_document_link_persistence_failed")
        self.assertTrue(result["events"][0]["rollback"]["ok"])
        self.assertNotIn("legacy.txt", str(result["events"][0]))

    def test_existing_already_linked_file_is_inventory_only(self) -> None:
        files = _FakeWorkspaceFiles(
            existing=[
                {
                    "id": FILE_ID,
                    "workspace_folder_id": FOLDER_ID,
                    "display_name": "legacy.txt",
                    "source_extension": ".txt",
                    "mime_type": "text/plain",
                    "status": "active",
                    "deleted_at": None,
                }
            ]
        )
        files.upsert_nextcloud_link(
            workspace_file_id=FILE_ID,
            workspace_folder_id=FOLDER_ID,
            nextcloud_sync_state="linked",
            nextcloud_document_ref="workspace-file:aaaaaaaa:abc123def456",
            nextcloud_name_hash="abc123def456",
            nextcloud_target_name="legacy.txt",
            last_sync_reason_code="folder_document_upload_ok",
            last_sync_operation="upload",
        )
        nextcloud = _FakeNextcloud()

        result = workspace_document_existing_files.reconcile_existing_workspace_documents(
            workspace_folders_module=_FakeFolders(linked=True),
            workspace_files_module=files,
            nextcloud=nextcloud,
        )

        self.assertEqual(result["verdict"], "met")
        self.assertEqual(result["summary"]["linked_files"], 1)
        self.assertEqual(result["summary"]["copied_files"], 0)
        self.assertEqual(nextcloud.status_calls, [])
        self.assertEqual(nextcloud.put_calls, [])
        self.assertEqual(result["events"][0]["operation"], "already_linked")


if __name__ == "__main__":
    unittest.main()
