from __future__ import annotations

import sys
import unittest
import uuid
from io import BytesIO
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
CONV_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _FakeWorkspaceFolders:
    WORKSPACE_FOLDER_ICON_KEYS = ("folder", "book", "spark")

    def __init__(self):
        self.folders = {}

    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def normalize_icon_key(self, value):
        icon = str(value or "folder").strip()
        return icon if icon in self.WORKSPACE_FOLDER_ICON_KEYS else None

    def sanitize_display_name(self, value):
        return " ".join(str(value or "").strip().split())[:80].rstrip()

    def sanitize_description(self, value):
        return " ".join(str(value or "").strip().split())[:240].rstrip()

    def coerce_sort_order(self, value):
        if value in (None, ""):
            return None
        return int(value)

    def list_workspace_folders(self):
        return list(self.folders.values())

    def get_workspace_folder(self, folder_id):
        normalized = self.normalize_workspace_folder_id(folder_id)
        item = self.folders.get(normalized)
        return item if item and not item.get("deleted_at") else None

    def create_workspace_folder(self, *, display_name, icon_key, description, sort_order=None):
        item = {
            "id": FOLDER_ID,
            "display_name": display_name,
            "icon_key": icon_key,
            "description": description,
            "sort_order": sort_order or 1000,
            "created_at": "2026-05-20T00:00:00Z",
            "updated_at": "2026-05-20T00:00:00Z",
            "deleted_at": None,
        }
        self.folders[item["id"]] = item
        return item

    def update_workspace_folder(self, folder_id, **fields):
        item = self.get_workspace_folder(folder_id)
        if item is None:
            return None
        item.update({key: value for key, value in fields.items() if value is not None})
        return item

    def soft_delete_workspace_folder(self, folder_id):
        item = self.get_workspace_folder(folder_id)
        if item is None:
            return None
        item["deleted_at"] = "2026-05-20T00:01:00Z"
        item["conversations_moved_out"] = 1
        return item


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"

    def __init__(self):
        self.files = {}
        self.deleted_folder_ids = []
        self.folder_delete_summary = None
        self.events = []

    def normalize_workspace_file_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def sanitize_display_name(self, value):
        return " ".join(str(value or "").strip().split())[:180].rstrip() or "fichier"

    def list_workspace_files(self, folder_id):
        return [item for item in self.files.get(folder_id, []) if not item.get("deleted_at")]

    def store_uploaded_file(self, folder_id, *, original_filename, content, metadata):
        item = {
            "id": "99999999-9999-4999-8999-999999999999",
            "workspace_folder_id": folder_id,
            "display_name": metadata.get("display_name") or original_filename,
            "original_filename": original_filename,
            "content_kind": metadata.get("content_kind", "document"),
            "media_kind": metadata.get("media_kind", "text"),
            "mime_type": metadata.get("mime_type", "text/plain"),
            "source_extension": metadata.get("source_extension", ".txt"),
            "byte_size": len(content),
            "sha256_12": "abc123def456",
            "text_chars": metadata.get("text_chars", 0),
            "text_sha256_12": metadata.get("text_sha256_12", ""),
            "image_width": metadata.get("image_width", 0),
            "image_height": metadata.get("image_height", 0),
            "status": metadata.get("status", "active"),
            "reason_code": metadata.get("reason_code", ""),
            "source_kind": "upload",
            "created_at": "2026-05-20T00:02:00Z",
            "updated_at": "2026-05-20T00:02:00Z",
            "deleted_at": None,
        }
        self.files.setdefault(folder_id, []).append(item)
        return item

    def delete_workspace_file(self, folder_id, file_id):
        for item in self.files.get(folder_id, []):
            if item["id"] == file_id and not item.get("deleted_at"):
                item["deleted_at"] = "2026-05-20T00:03:00Z"
                item["status"] = "deleted"
                item["disk_deleted"] = True
                return item
        return None

    def delete_workspace_files_for_folder(self, folder_id):
        self.deleted_folder_ids.append(folder_id)
        if self.folder_delete_summary is not None:
            return dict(self.folder_delete_summary)
        count = 0
        for item in self.files.get(folder_id, []):
            if not item.get("deleted_at"):
                item["deleted_at"] = "2026-05-20T00:03:00Z"
                item["status"] = "deleted"
                count += 1
        return {"requested": count, "deleted": count, "failed": 0, "failed_file_ids": [], "reason_code": ""}

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeConvStore:
    def __init__(self):
        self.conversations = {
            CONV_ID: {
                "id": CONV_ID,
                "title": "Conversation",
                "created_at": "2026-05-20T00:00:00Z",
                "updated_at": "2026-05-20T00:00:00Z",
                "message_count": 0,
                "last_message_preview": "",
                "workspace_folder_id": None,
                "deleted_at": None,
            }
        }

    def normalize_conversation_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def rename_conversation(self, conversation_id, title):
        item = self.conversations.get(conversation_id)
        if item is None:
            return None
        item["title"] = title
        return item

    def set_conversation_workspace_folder(self, conversation_id, folder_id):
        item = self.conversations.get(conversation_id)
        if item is None:
            return None
        item["workspace_folder_id"] = folder_id
        return item


class ServerWorkspaceFoldersContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_files = self.server.workspace_files
        self.original_conv_store = self.server.conv_store
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_workspace_files = _FakeWorkspaceFiles()
        self.fake_conv_store = _FakeConvStore()
        self.server.workspace_folders = self.fake_workspace
        self.server.workspace_files = self.fake_workspace_files
        self.server.conv_store = self.fake_conv_store

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_files = self.original_workspace_files
        self.server.conv_store = self.original_conv_store

    def test_workspace_folder_crud_routes_are_content_free_and_validate_icon_key(self) -> None:
        invalid = self.client.post("/api/workspace-folders", json={"display_name": "Projet", "icon_key": "<svg>"})
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.get_json()["reason_code"], "workspace_folder_icon_invalid")

        created = self.client.post(
            "/api/workspace-folders",
            json={"display_name": "  Projet   Tulu ", "icon_key": "book", "description": "  UI only  "},
        )
        self.assertEqual(created.status_code, 201)
        payload = created.get_json()
        self.assertEqual(payload["folder"]["id"], FOLDER_ID)
        self.assertEqual(payload["folder"]["display_name"], "Projet Tulu")
        self.assertEqual(payload["folder"]["description"], "UI only")
        self.assertNotIn("prompt", payload["folder"])

        patched = self.client.patch(
            f"/api/workspace-folders/{FOLDER_ID}",
            json={"display_name": "Projet renomme", "description": "Description non injectee"},
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.get_json()["folder"]["display_name"], "Projet renomme")

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")
        self.assertEqual(deleted.status_code, 200)
        deleted_payload = deleted.get_json()
        self.assertEqual(deleted_payload["folder"]["conversations_moved_out"], 1)
        self.assertEqual(deleted_payload["folder"]["file_delete"]["requested"], 0)
        self.assertEqual(deleted_payload["folder"]["file_delete"]["failed"], 0)
        self.assertEqual(self.fake_workspace_files.deleted_folder_ids, [FOLDER_ID])

    def test_conversation_patch_attaches_and_detaches_nullable_workspace_folder(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")

        attached = self.client.patch(f"/api/conversations/{CONV_ID}", json={"workspace_folder_id": FOLDER_ID})
        self.assertEqual(attached.status_code, 200)
        self.assertEqual(attached.get_json()["conversation"]["workspace_folder_id"], FOLDER_ID)

        detached = self.client.patch(f"/api/conversations/{CONV_ID}", json={"workspace_folder_id": None})
        self.assertEqual(detached.status_code, 200)
        self.assertIsNone(detached.get_json()["conversation"]["workspace_folder_id"])

        missing = self.client.patch(
            f"/api/conversations/{CONV_ID}",
            json={"workspace_folder_id": "22222222-2222-4222-8222-222222222222"},
        )
        self.assertEqual(missing.status_code, 404)

    def test_workspace_file_routes_are_content_free_and_separate_from_active_documents(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")

        listed_empty = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/files")
        self.assertEqual(listed_empty.status_code, 200)
        self.assertEqual(listed_empty.get_json()["items"], [])

        uploaded = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/files",
            data={"file": (BytesIO(b"bonjour"), "note.txt")},
            content_type="multipart/form-data",
        )
        self.assertEqual(uploaded.status_code, 201)
        payload = uploaded.get_json()
        self.assertEqual(payload["file"]["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(payload["file"]["display_name"], "note.txt")
        self.assertEqual(payload["file"]["byte_size"], 7)
        self.assertNotIn("storage_key", payload["file"])
        self.assertNotIn("internal_path", payload["file"])
        self.assertNotIn("text", payload["file"])

        listed = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/files")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()["items"]), 1)

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}/files/{payload['file']['id']}")
        self.assertEqual(deleted.status_code, 200)
        self.assertEqual(deleted.get_json()["file"]["disk_deleted"], True)

        listed_after = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/files")
        self.assertEqual(listed_after.status_code, 200)
        self.assertEqual(listed_after.get_json()["items"], [])

    def test_workspace_file_upload_rejects_unsupported_types(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")

        uploaded = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/files",
            data={"file": (BytesIO(b"GIF89a\x01\x00\x01\x00\x00\x00"), "loop.gif")},
            content_type="multipart/form-data",
        )

        self.assertEqual(uploaded.status_code, 422)
        payload = uploaded.get_json()
        self.assertEqual(payload["reason_code"], "workspace_file_type_unsupported")
        self.assertEqual(self.fake_workspace_files.files, {})
        self.assertEqual(self.fake_workspace_files.events[-1][0], "upload_failed")
        self.assertNotIn("text_content", self.fake_workspace_files.events[-1][1])
        self.assertNotIn("binary_content", self.fake_workspace_files.events[-1][1])

    def test_workspace_folder_delete_removes_active_files_before_soft_delete(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.files[FOLDER_ID] = [
            {"id": "11111111-1111-4111-8111-111111111111", "deleted_at": None, "status": "active"},
            {"id": "22222222-2222-4222-8222-222222222222", "deleted_at": None, "status": "active"},
        ]

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")

        self.assertEqual(deleted.status_code, 200)
        payload = deleted.get_json()
        self.assertEqual(payload["folder"]["file_delete"]["requested"], 2)
        self.assertEqual(payload["folder"]["file_delete"]["deleted"], 2)
        self.assertEqual(payload["folder"]["file_delete"]["failed"], 0)
        self.assertEqual(payload["folder"]["files_deleted"], 2)
        self.assertEqual(self.fake_workspace.folders[FOLDER_ID]["deleted_at"], "2026-05-20T00:01:00Z")
        self.assertTrue(all(item["status"] == "deleted" for item in self.fake_workspace_files.files[FOLDER_ID]))

    def test_workspace_folder_delete_does_not_mask_partial_file_failure(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.folder_delete_summary = {
            "requested": 2,
            "deleted": 1,
            "failed": 1,
            "failed_file_ids": ["22222222-2222-4222-8222-222222222222"],
            "reason_code": "workspace_folder_file_delete_failed",
        }

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")

        self.assertEqual(deleted.status_code, 409)
        payload = deleted.get_json()
        self.assertEqual(payload["reason_code"], "workspace_folder_file_delete_failed")
        self.assertEqual(payload["file_delete"]["requested"], 2)
        self.assertEqual(payload["file_delete"]["deleted"], 1)
        self.assertEqual(payload["file_delete"]["failed"], 1)
        self.assertIsNone(self.fake_workspace.folders[FOLDER_ID]["deleted_at"])
        self.assertEqual(self.fake_workspace_files.deleted_folder_ids, [FOLDER_ID])


if __name__ == "__main__":
    unittest.main()
