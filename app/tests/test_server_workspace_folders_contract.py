from __future__ import annotations

import sys
import unittest
import uuid
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
        self.original_conv_store = self.server.conv_store
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_conv_store = _FakeConvStore()
        self.server.workspace_folders = self.fake_workspace
        self.server.conv_store = self.fake_conv_store

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
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
        self.assertEqual(deleted.get_json()["folder"]["conversations_moved_out"], 1)

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


if __name__ == "__main__":
    unittest.main()
