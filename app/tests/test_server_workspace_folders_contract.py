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
from core import workspace_folders_store


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
OTHER_FOLDER_ID = "22222222-2222-4222-8222-222222222222"
CONV_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_CONV_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"
FILE_ID = "99999999-9999-4999-8999-999999999999"


class _FakeWorkspaceFolders:
    WORKSPACE_FOLDER_ICON_KEYS = ("folder", "book", "spark")

    def __init__(self):
        self.folders = {}

    def _serialize(self, item):
        if item is None:
            return None
        return workspace_folders_store.serialize_workspace_folder_row(item)

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
        return [
            self._serialize(item)
            for item in self.folders.values()
            if not item.get("deleted_at")
        ]

    def get_workspace_folder(self, folder_id):
        normalized = self.normalize_workspace_folder_id(folder_id)
        item = self.folders.get(normalized)
        return self._serialize(item) if item and not item.get("deleted_at") else None

    def validate_workspace_folder_display_name(self, value, *, current_folder_id=None):
        return workspace_folders_store.validate_workspace_folder_name(
            value,
            existing_folders=list(self.folders.values()),
            current_folder_id=current_folder_id,
        )

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
        return self._serialize(item)

    def update_workspace_folder(self, folder_id, **fields):
        item = self.get_workspace_folder(folder_id)
        normalized = self.normalize_workspace_folder_id(folder_id)
        raw = self.folders.get(normalized)
        if item is None or raw is None:
            return None
        raw.update({key: value for key, value in fields.items() if value is not None})
        return self._serialize(raw)

    def soft_delete_workspace_folder(self, folder_id):
        item = self.get_workspace_folder(folder_id)
        normalized = self.normalize_workspace_folder_id(folder_id)
        raw = self.folders.get(normalized)
        if item is None or raw is None:
            return None
        raw["deleted_at"] = "2026-05-20T00:01:00Z"
        folder = self._serialize(raw)
        folder["conversations_moved_out"] = 1
        return folder


class _FakeWorkspaceFiles:
    STATUS_ACTIVE = "active"
    STATUS_OCR_REQUIRED = "ocr_required"
    MEDIA_KIND_TEXT = "text"
    MEDIA_KIND_IMAGE = "image"
    CONTENT_KIND_DOCUMENT = "document"
    CONTENT_KIND_IMAGE = "image"
    SOURCE_KIND_UPLOAD = "upload"
    SOURCE_KIND_OCR_DERIVED = "ocr_derived"

    def __init__(self):
        self.files = {}
        self.file_bytes = {}
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
        self.file_bytes[item["id"]] = bytes(content)
        return item

    def delete_workspace_file(self, folder_id, file_id):
        for item in self.files.get(folder_id, []):
            if item["id"] == file_id and not item.get("deleted_at"):
                item["deleted_at"] = "2026-05-20T00:03:00Z"
                item["status"] = "deleted"
                item["disk_deleted"] = True
                return item
        return None

    def get_workspace_file_storage_row(self, folder_id, file_id):
        for item in self.files.get(folder_id, []):
            if item["id"] == file_id and not item.get("deleted_at"):
                return {
                    **item,
                    "storage_key": f"{folder_id}/{file_id}{item.get('source_extension') or ''}",
                    "sha256": "full-hidden",
                }
        return None

    def read_file_bytes(self, storage_key):
        file_id = str(storage_key or "").split("/")[-1].split(".")[0]
        for stored_id, content in self.file_bytes.items():
            if stored_id == file_id or stored_id in str(storage_key or ""):
                return content
        raise FileNotFoundError(storage_key)

    def find_ocr_derived_file(self, folder_id, source_file_id):
        for item in self.files.get(folder_id, []):
            if (
                item.get("source_kind") == "ocr_derived"
                and item.get("source_file_id") == source_file_id
                and not item.get("deleted_at")
            ):
                return dict(item)
        return None

    def update_workspace_text_file(self, folder_id, file_id, *, content, metadata):
        for item in self.files.get(folder_id, []):
            if item["id"] == file_id and not item.get("deleted_at"):
                self.file_bytes[file_id] = bytes(content)
                item["byte_size"] = len(content)
                item["text_chars"] = metadata.get("text_chars", 0)
                item["text_sha256_12"] = metadata.get("text_sha256_12", "")
                item["status"] = metadata.get("status", "active")
                item["reason_code"] = metadata.get("reason_code", "")
                return dict(item)
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
            },
            OTHER_CONV_ID: {
                "id": OTHER_CONV_ID,
                "title": "Autre conversation",
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

    def get_conversation_summary(self, conversation_id, include_deleted=False):
        item = self.conversations.get(conversation_id)
        if item is None:
            return None
        if item.get("deleted_at") and not include_deleted:
            return None
        return dict(item)

    def set_conversation_workspace_folder(self, conversation_id, folder_id):
        item = self.conversations.get(conversation_id)
        if item is None:
            return None
        item["workspace_folder_id"] = folder_id
        return item

    def list_conversations(self, *, limit=100, offset=0, include_deleted=False):
        items = [
            dict(item)
            for item in self.conversations.values()
            if include_deleted or not item.get("deleted_at")
        ]
        return {
            "items": items[offset:offset + limit],
            "total": len(items),
            "limit": limit,
            "offset": offset,
        }


class _FakeWorkspaceFileSelections:
    def __init__(self, conv_store, files_store):
        self.conv_store = conv_store
        self.files_store = files_store
        self.selections = {}
        self.prompt_reads = []
        self.injected = []
        self.excluded = []
        self.cleared = []

    def list_workspace_file_selections(self, conversation_id):
        return [dict(item) for item in self.selections.get(conversation_id, {}).values()]

    def select_workspace_file(self, conversation_id, file_id):
        conversation = self.conv_store.conversations.get(conversation_id)
        if not conversation or not conversation.get("workspace_folder_id"):
            return {"ok": False, "reason_code": "workspace_selection_stale"}
        folder_id = conversation["workspace_folder_id"]
        file_item = next((item for item in self.files_store.files.get(folder_id, []) if item["id"] == file_id), None)
        if file_item is None:
            return {"ok": False, "reason_code": "workspace_file_missing"}
        if file_item.get("deleted_at"):
            return {"ok": False, "reason_code": "workspace_file_deleted"}
        selection = {
            "conversation_id": conversation_id,
            "workspace_file_id": file_id,
            "workspace_folder_id": folder_id,
            "selected": True,
            "selection_status": "selected",
            "reason_code": "",
            "file": dict(file_item),
        }
        self.selections.setdefault(conversation_id, {})[file_id] = selection
        return {"ok": True, "selection": selection}

    def deselect_workspace_file(self, conversation_id, file_id):
        return self.selections.get(conversation_id, {}).pop(file_id, None) is not None

    def clear_stale_selections_for_conversation(self, conversation_id, *, workspace_folder_id):
        self.cleared.append((conversation_id, workspace_folder_id))
        if not workspace_folder_id:
            count = len(self.selections.get(conversation_id, {}))
            self.selections[conversation_id] = {}
            return count
        kept = {
            file_id: item
            for file_id, item in self.selections.get(conversation_id, {}).items()
            if item.get("workspace_folder_id") == workspace_folder_id
        }
        removed = len(self.selections.get(conversation_id, {})) - len(kept)
        self.selections[conversation_id] = kept
        return removed

    def list_selected_files_for_prompt(self, conversation_id):
        self.prompt_reads.append(conversation_id)
        return []

    def record_selection_injected(self, conversation_id, file_id, *, turn_id):
        self.injected.append((conversation_id, file_id, turn_id))
        return True

    def record_selection_excluded(self, conversation_id, file_id, *, turn_id, reason_code):
        self.excluded.append((conversation_id, file_id, turn_id, reason_code))
        return True


class ServerWorkspaceFoldersContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_files = self.server.workspace_files
        self.original_workspace_file_selections = self.server.workspace_file_selections
        self.original_conv_store = self.server.conv_store
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_workspace_files = _FakeWorkspaceFiles()
        self.fake_conv_store = _FakeConvStore()
        self.fake_workspace_file_selections = _FakeWorkspaceFileSelections(
            self.fake_conv_store,
            self.fake_workspace_files,
        )
        self.server.workspace_folders = self.fake_workspace
        self.server.workspace_files = self.fake_workspace_files
        self.server.workspace_file_selections = self.fake_workspace_file_selections
        self.server.conv_store = self.fake_conv_store

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_files = self.original_workspace_files
        self.server.workspace_file_selections = self.original_workspace_file_selections
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
        self.assertEqual(payload["folder"]["nextcloud_logical_path"], "/Frida/Projet-Tulu")
        self.assertEqual(payload["folder"]["nextcloud_sync_state"], "pending")
        self.assertFalse(payload["folder"]["nextcloud_live_checked"])
        self.assertNotIn("prompt", payload["folder"])

        patched = self.client.patch(
            f"/api/workspace-folders/{FOLDER_ID}",
            json={"display_name": "Projet renomme", "description": "Description non injectee"},
        )
        self.assertEqual(patched.status_code, 200)
        self.assertEqual(patched.get_json()["folder"]["display_name"], "Projet renomme")
        self.assertEqual(patched.get_json()["folder"]["nextcloud_logical_path"], "/Frida/Projet-renomme")

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")
        self.assertEqual(deleted.status_code, 200)
        deleted_payload = deleted.get_json()
        self.assertEqual(deleted_payload["folder"]["conversations_moved_out"], 1)
        self.assertEqual(deleted_payload["folder"]["file_delete"]["requested"], 0)
        self.assertEqual(deleted_payload["folder"]["file_delete"]["failed"], 0)
        self.assertEqual(deleted_payload["folder"]["file_delete"]["reason_code"], "workspace_folder_files_preserved")
        self.assertEqual(deleted_payload["folder"]["files_deleted"], 0)
        self.assertEqual(deleted_payload["folder"]["files_preserved"], True)
        self.assertEqual(deleted_payload["folder"]["nextcloud_sync_state"], "deleted")
        self.assertEqual(self.fake_workspace_files.deleted_folder_ids, [])

    def test_conversation_list_keeps_existing_conversations_outside_workspace_by_default(self) -> None:
        response = self.client.get("/api/conversations")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertEqual(payload["total"], 2)
        self.assertEqual(
            {item["id"]: item["workspace_folder_id"] for item in payload["items"]},
            {
                CONV_ID: None,
                OTHER_CONV_ID: None,
            },
        )

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
        self.assertIn((CONV_ID, FOLDER_ID), self.fake_workspace_file_selections.cleared)
        self.assertIn((CONV_ID, None), self.fake_workspace_file_selections.cleared)

    def test_workspace_file_selection_is_conversation_scoped_and_content_free(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_conv_store.set_conversation_workspace_folder(CONV_ID, FOLDER_ID)
        self.fake_conv_store.set_conversation_workspace_folder(OTHER_CONV_ID, FOLDER_ID)
        self.fake_workspace_files.files[FOLDER_ID] = [
            {
                "id": FILE_ID,
                "workspace_folder_id": FOLDER_ID,
                "display_name": "note.txt",
                "content_kind": "document",
                "media_kind": "text",
                "mime_type": "text/plain",
                "source_extension": ".txt",
                "byte_size": 7,
                "status": "active",
                "reason_code": "",
                "deleted_at": None,
            }
        ]

        selected = self.client.post(
            f"/api/conversations/{CONV_ID}/workspace-file-selections",
            json={"file_id": FILE_ID},
        )
        self.assertEqual(selected.status_code, 201)
        payload = selected.get_json()
        self.assertEqual(payload["selection"]["workspace_file_id"], FILE_ID)
        self.assertEqual(payload["selection"]["conversation_id"], CONV_ID)
        self.assertNotIn("storage_key", str(payload))
        self.assertNotIn("text_content", str(payload))
        self.assertNotIn("binary_content", str(payload))

        listed = self.client.get(f"/api/conversations/{CONV_ID}/workspace-file-selections")
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.get_json()["items"]), 1)

        other = self.client.get(f"/api/conversations/{OTHER_CONV_ID}/workspace-file-selections")
        self.assertEqual(other.status_code, 200)
        self.assertEqual(other.get_json()["items"], [])

        removed = self.client.delete(f"/api/conversations/{CONV_ID}/workspace-file-selections/{FILE_ID}")
        self.assertEqual(removed.status_code, 200)
        listed_after = self.client.get(f"/api/conversations/{CONV_ID}/workspace-file-selections")
        self.assertEqual(listed_after.get_json()["items"], [])

    def test_workspace_file_selection_refuses_conversation_outside_folder(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.files[FOLDER_ID] = [
            {"id": FILE_ID, "workspace_folder_id": FOLDER_ID, "display_name": "note.txt", "deleted_at": None}
        ]

        selected = self.client.post(
            f"/api/conversations/{CONV_ID}/workspace-file-selections",
            json={"file_id": FILE_ID},
        )

        self.assertEqual(selected.status_code, 409)
        self.assertEqual(selected.get_json()["reason_code"], "workspace_selection_stale")

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

    def test_workspace_folder_delete_preserves_active_files_and_tombstones_folder(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.files[FOLDER_ID] = [
            {"id": "11111111-1111-4111-8111-111111111111", "deleted_at": None, "status": "active"},
            {"id": "22222222-2222-4222-8222-222222222222", "deleted_at": None, "status": "active"},
        ]

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")

        self.assertEqual(deleted.status_code, 200)
        payload = deleted.get_json()
        self.assertEqual(payload["folder"]["file_delete"]["requested"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["deleted"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["failed"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["reason_code"], "workspace_folder_files_preserved")
        self.assertEqual(payload["folder"]["files_deleted"], 0)
        self.assertEqual(payload["folder"]["files_preserved"], True)
        self.assertEqual(self.fake_workspace.folders[FOLDER_ID]["deleted_at"], "2026-05-20T00:01:00Z")
        self.assertTrue(all(item["status"] == "active" for item in self.fake_workspace_files.files[FOLDER_ID]))
        self.assertEqual(self.fake_workspace_files.deleted_folder_ids, [])

    def test_workspace_folder_delete_ignores_file_delete_failures_in_v1_folder_scope(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.folder_delete_summary = {
            "requested": 2,
            "deleted": 1,
            "failed": 1,
            "failed_file_ids": ["22222222-2222-4222-8222-222222222222"],
            "reason_code": "workspace_folder_file_delete_failed",
        }

        deleted = self.client.delete(f"/api/workspace-folders/{FOLDER_ID}")

        self.assertEqual(deleted.status_code, 200)
        payload = deleted.get_json()
        self.assertEqual(payload["folder"]["file_delete"]["requested"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["deleted"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["failed"], 0)
        self.assertEqual(payload["folder"]["file_delete"]["reason_code"], "workspace_folder_files_preserved")
        self.assertEqual(self.fake_workspace.folders[FOLDER_ID]["deleted_at"], "2026-05-20T00:01:00Z")
        self.assertEqual(self.fake_workspace_files.deleted_folder_ids, [])

    def test_workspace_file_ocr_route_refuses_unsupported_type_without_content_leak(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace_files.files[FOLDER_ID] = [
            {
                "id": FILE_ID,
                "workspace_folder_id": FOLDER_ID,
                "display_name": "note.txt",
                "original_filename": "note.txt",
                "content_kind": "document",
                "media_kind": "text",
                "mime_type": "text/plain",
                "source_extension": ".txt",
                "byte_size": 7,
                "status": "active",
                "reason_code": "",
                "source_kind": "upload",
                "source_file_id": None,
                "deleted_at": None,
            }
        ]
        self.fake_workspace_files.file_bytes[FILE_ID] = b"secret text"

        response = self.client.post(f"/api/workspace-folders/{FOLDER_ID}/files/{FILE_ID}/ocr")

        self.assertEqual(response.status_code, 422)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "workspace_file_ocr_unsupported")
        encoded = str(payload)
        self.assertNotIn("secret text", encoded)
        self.assertNotIn("storage_key", encoded)

    def test_workspace_ocr_markdown_routes_read_and_save_only_derived_markdown(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        derived_id = "33333333-3333-4333-8333-333333333333"
        self.fake_workspace_files.files[FOLDER_ID] = [
            {
                "id": derived_id,
                "workspace_folder_id": FOLDER_ID,
                "display_name": "scan.ocr.md",
                "original_filename": "scan.ocr.md",
                "content_kind": "document",
                "media_kind": "text",
                "mime_type": "text/markdown",
                "source_extension": ".md",
                "byte_size": 12,
                "text_chars": 12,
                "text_sha256_12": "text12345678",
                "status": "active",
                "reason_code": "",
                "source_kind": "ocr_derived",
                "source_file_id": FILE_ID,
                "deleted_at": None,
            }
        ]
        self.fake_workspace_files.file_bytes[derived_id] = b"# OCR\n\nancien"

        read_response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/files/{derived_id}/ocr-markdown")
        self.assertEqual(read_response.status_code, 200)
        self.assertEqual(read_response.get_json()["content"], "# OCR\n\nancien")

        patch_response = self.client.patch(
            f"/api/workspace-folders/{FOLDER_ID}/files/{derived_id}/ocr-markdown",
            json={"content": "# OCR\n\ncorrige"},
        )

        self.assertEqual(patch_response.status_code, 200)
        self.assertEqual(self.fake_workspace_files.file_bytes[derived_id], b"# OCR\n\ncorrige")
        payload = patch_response.get_json()
        self.assertNotIn("storage_key", str(payload))
        self.assertNotIn("# OCR", str(payload))


if __name__ == "__main__":
    unittest.main()
