from __future__ import annotations

import sys
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests
from tests.test_server_workspace_folder_notes_contract import (  # noqa: E402
    FOLDER_ID,
    _FakeWorkspaceFolderNotes,
    _FakeWorkspaceFolders,
)
from core import workspace_folder_notes


class _FakeWorkspaceFolderNotesRead:
    def __init__(self):
        self.calls = []
        self.fail_reason = ""

    def prepare_workspace_folder_note_for_conversation(
        self,
        folder,
        *,
        note_id,
        notes_module,
    ):
        self.calls.append({"folder_id": folder.get("id"), "note_id": note_id})
        if str(folder.get("nextcloud_sync_state") or "") != "linked":
            return _failure("folder_note_folder_not_linked", status=409, state="blocked")
        if self.fail_reason:
            return _failure(self.fail_reason, status=413 if self.fail_reason == "folder_note_too_large" else 502, state="blocked")
        note = notes_module.get_note(note_id, fail_closed=True)
        if not note:
            return _failure("folder_note_not_found", status=404, state="blocked")
        markdown = "# Note synthetique"
        return {
            "ok": True,
            "reason_code": "folder_note_read_ok",
            "status": 200,
            "note": workspace_folder_notes.apply_note_projection(note, folder=folder),
            "note_conversation": {
                "read_state": "ready",
                "reason_code": "folder_note_read_ok",
                "note_ref": workspace_folder_notes.note_ref(note_id),
                "folder_ref": workspace_folder_notes.folder_ref(folder.get("id")),
                "markdown_char_count": len(markdown),
                "markdown_content": markdown,
                "injection_scope": "current_turn_only",
                "memory_rag_identity_summary": "not_used",
            },
            "note_nextcloud": {
                "read_state": "ready",
                "reason_code": "folder_note_read_ok",
                "note_name_hash": "abcdef123456",
                "http_status_class": "2xx",
                "etag_hash": "fedcba654321",
                "etag_present": True,
            },
        }


def _failure(reason_code: str, *, status: int, state: str):
    return {
        "ok": False,
        "reason_code": reason_code,
        "status": status,
        "note": {},
        "note_conversation": {
            "read_state": state,
            "reason_code": reason_code,
            "markdown_char_count": 0,
            "injection_scope": "none",
            "memory_rag_identity_summary": "not_used",
        },
        "note_nextcloud": {
            "read_state": state,
            "reason_code": reason_code,
            "http_status_class": "none",
            "etag_present": False,
        },
    }


class ServerWorkspaceFolderNotesReadContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_notes = self.server.workspace_folder_notes
        self.original_workspace_folder_notes_read = self.server.workspace_folder_notes_read
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_workspace_folder_notes = _FakeWorkspaceFolderNotes()
        self.fake_workspace_folder_notes_read = _FakeWorkspaceFolderNotesRead()
        self.server.workspace_folders = self.fake_workspace
        self.server.workspace_folder_notes = self.fake_workspace_folder_notes
        self.server.workspace_folder_notes_read = self.fake_workspace_folder_notes_read

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_notes = self.original_workspace_folder_notes
        self.server.workspace_folder_notes_read = self.original_workspace_folder_notes_read

    def _create_linked_folder(self):
        self.fake_workspace.create_workspace_folder(
            display_name="Projet",
            icon_key="folder",
            description="",
        )
        self.fake_workspace.folders[FOLDER_ID].update(
            {
                "link_workspace_folder_id": FOLDER_ID,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abcdef123456",
                "link_nextcloud_name_hash": "abcdef123456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "confirmed",
            }
        )

    def _seed_note(self, note_id="33333333-3333-4333-8333-333333333333"):
        target_name = workspace_folder_notes.sanitize_note_target_name("Carnet sensible")
        item = {
            "id": note_id,
            "workspace_folder_id": FOLDER_ID,
            "title": "Carnet sensible",
            "title_hash": workspace_folder_notes.title_hash_for_target(target_name),
            "target_name": target_name,
            "local_state": "available",
            "nextcloud_sync_state": "linked",
            "remote_note_ref": f"workspace-note:{note_id[:8]}:abcdef123456",
            "etag_value": '"raw-etag-hidden"',
            "etag_hash": "123456abcdef",
            "markdown_char_count": 12,
            "reason_code": "folder_note_lookup_ok",
            "created_at": "2026-06-18T11:00:00Z",
            "updated_at": "2026-06-18T11:00:00Z",
            "deleted_at": None,
            "markdown_body": "corps markdown interdit",
        }
        self.fake_workspace_folder_notes.notes.append(item)
        return item

    def test_workspace_folder_note_prepare_route_is_namespaced_and_content_scoped(self) -> None:
        self._create_linked_folder()
        note = self._seed_note()

        global_route = self.client.post(f"/api/notes/{note['id']}/prepare")
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/prepare"
        )

        self.assertIn(global_route.status_code, {404, 405})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_read_ok")
        self.assertEqual(payload["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertEqual(payload["note_conversation"]["markdown_content"], "# Note synthetique")
        self.assertEqual(payload["note_conversation"]["injection_scope"], "current_turn_only")
        self.assertEqual(payload["note_conversation"]["memory_rag_identity_summary"], "not_used")
        self.assertNotIn("# Note synthetique", str(payload["note"]))
        self.assertNotIn("# Note synthetique", str(payload["note_nextcloud"]))
        self.assertNotIn("raw-etag-hidden", str(payload))
        self.assertNotIn("Carnet-sensible.md", str(payload))
        self.assertNotIn("target_name", payload["note"])
        self.assertNotIn("remote_note_ref", payload["note"])

    def test_workspace_folder_note_prepare_route_reports_missing_non_linked_and_too_large(self) -> None:
        self._create_linked_folder()
        missing = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/44444444-4444-4444-8444-444444444444/prepare"
        )
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["reason_code"], "folder_note_not_found")

        note = self._seed_note()
        self.fake_workspace_folder_notes_read.fail_reason = "folder_note_too_large"
        too_large = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/prepare"
        )
        self.assertEqual(too_large.status_code, 413)
        self.assertEqual(too_large.get_json()["reason_code"], "folder_note_too_large")
        self.assertNotIn("markdown_content", too_large.get_json()["note_conversation"])

        self.fake_workspace_folder_notes_read.fail_reason = ""
        self.fake_workspace.folders[FOLDER_ID].update(
            {
                "link_workspace_folder_id": None,
                "link_nextcloud_sync_state": "local_only",
                "link_nextcloud_folder_ref": "",
                "link_nextcloud_name_hash": "",
                "link_last_sync_reason_code": "workspace_folder_sync_local_only",
                "link_last_sync_operation": "",
                "link_nextcloud_share_state": "expected",
            }
        )
        non_linked = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/prepare"
        )
        self.assertEqual(non_linked.status_code, 409)
        self.assertEqual(non_linked.get_json()["reason_code"], "folder_note_folder_not_linked")


if __name__ == "__main__":
    unittest.main()
