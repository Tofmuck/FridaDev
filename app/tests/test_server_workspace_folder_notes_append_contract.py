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


class _FakeWorkspaceFolderNotesAppend:
    def __init__(self):
        self.calls = []
        self.fail_reason = ""

    def append_workspace_folder_note(
        self,
        folder,
        *,
        note_id,
        markdown,
        notes_module,
    ):
        self.calls.append(
            {
                "folder_id": folder.get("id"),
                "note_id": note_id,
                "markdown_size": len(str(markdown or "")),
            }
        )
        if str(folder.get("nextcloud_sync_state") or "") != "linked":
            return _failure("folder_note_folder_not_linked", status=409, state="blocked")
        if self.fail_reason:
            status = 409 if self.fail_reason == "folder_note_version_conflict" else 404
            return _failure(self.fail_reason, status=status, state="remote_write_failed")

        note = notes_module.get_note(note_id, fail_closed=True)
        if not note:
            return _failure("folder_note_not_found", status=404, state="blocked")

        stored = notes_module.upsert_note(
            note_id=note_id,
            workspace_folder_id=folder.get("id"),
            title=note.get("title"),
            target_name=note.get("target_name"),
            local_state="available",
            nextcloud_sync_state="linked",
            remote_note_ref=note.get("remote_note_ref"),
            etag_value='"etag-after-hidden"',
            etag_hash="fedcba654321",
            markdown_char_count=note.get("markdown_char_count", 0) + len(str(markdown or "")),
            reason_code="folder_note_append_ok",
        )
        return {
            "ok": True,
            "note": stored,
            "reason_code": "folder_note_append_ok",
            "status": 200,
            "note_nextcloud": {
                "append_state": "appended",
                "reason_code": "folder_note_append_ok",
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
        "note_nextcloud": {
            "append_state": state,
            "reason_code": reason_code,
            "http_status_class": "4xx" if status >= 400 else "none",
            "note_name_hash": "abcdef123456" if state == "remote_write_failed" else "",
            "rollback": {},
        },
    }


class ServerWorkspaceFolderNotesAppendContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_notes = self.server.workspace_folder_notes
        self.original_workspace_folder_notes_append = self.server.workspace_folder_notes_append
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_workspace_folder_notes = _FakeWorkspaceFolderNotes()
        self.fake_workspace_folder_notes_append = _FakeWorkspaceFolderNotesAppend()
        self.server.workspace_folders = self.fake_workspace
        self.server.workspace_folder_notes = self.fake_workspace_folder_notes
        self.server.workspace_folder_notes_append = self.fake_workspace_folder_notes_append

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_notes = self.original_workspace_folder_notes
        self.server.workspace_folder_notes_append = self.original_workspace_folder_notes_append

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

    def test_workspace_folder_note_append_route_is_namespaced_and_content_free(self) -> None:
        self._create_linked_folder()
        note = self._seed_note()

        global_route = self.client.post(f"/api/notes/{note['id']}/append", json={"markdown": "Ajout"})
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/append",
            json={"markdown": "Ajout synthetique"},
        )

        self.assertIn(global_route.status_code, {404, 405})
        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_append_ok")
        self.assertEqual(payload["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertEqual(payload["note_nextcloud"]["append_state"], "appended")
        self.assertEqual(
            self.fake_workspace_folder_notes_append.calls[0]["markdown_size"],
            len("Ajout synthetique"),
        )
        self.assertNotIn("Ajout synthetique", str(payload))
        self.assertNotIn("etag-after-hidden", str(payload))
        self.assertNotIn("Carnet-sensible.md", str(payload))
        self.assertNotIn("target_name", payload["note"])
        self.assertNotIn("remote_note_ref", payload["note"])

    def test_workspace_folder_note_append_route_reports_missing_non_linked_and_etag_conflict(self) -> None:
        self._create_linked_folder()
        note = self._seed_note()

        missing = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/44444444-4444-4444-8444-444444444444/append",
            json={"markdown": "Ajout"},
        )
        self.fake_workspace_folder_notes_append.fail_reason = "folder_note_version_conflict"
        conflict = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/append",
            json={"markdown": "Ajout"},
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["reason_code"], "folder_note_not_found")
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.get_json()["reason_code"], "folder_note_version_conflict")
        self.assertNotIn("Ajout", str(conflict.get_json()))

        self.fake_workspace_folder_notes_append.fail_reason = ""
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
            f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}/append",
            json={"markdown": "Ajout"},
        )

        self.assertEqual(non_linked.status_code, 409)
        self.assertEqual(non_linked.get_json()["reason_code"], "folder_note_folder_not_linked")


if __name__ == "__main__":
    unittest.main()
