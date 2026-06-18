from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests
from core import workspace_folder_notes
from core import workspace_folders_store


FOLDER_ID = "11111111-2222-4333-8444-555555555555"


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

    def get_workspace_folder(self, folder_id, *, include_deleted=False):
        normalized = self.normalize_workspace_folder_id(folder_id)
        item = self.folders.get(normalized)
        if not item or (item.get("deleted_at") and not include_deleted):
            return None
        return self._serialize(item)


class _FakeWorkspaceFolderNotes:
    def __init__(self):
        self.notes = []
        self.events = []
        self.fail_list = False

    def list_notes(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        if self.fail_list:
            raise RuntimeError("raw lookup failure")
        if include_deleted:
            return list(self.notes)
        return [
            item
            for item in self.notes
            if not item.get("deleted_at")
            and item.get("local_state") != workspace_folder_notes.NOTE_LOCAL_DELETED
        ]

    def get_note(self, note_id, *, fail_closed=True):
        if self.fail_list:
            raise RuntimeError("raw lookup failure")
        normalized = workspace_folder_notes.normalize_note_id(note_id)
        for item in self.notes:
            if workspace_folder_notes.normalize_note_id(item.get("id")) == normalized:
                return dict(item)
        return None

    def upsert_note(self, **fields):
        item = {
            "id": fields["note_id"],
            "workspace_folder_id": fields["workspace_folder_id"],
            "title": fields["title"],
            "title_hash": workspace_folder_notes.title_hash_for_target(fields["target_name"]),
            "target_name": fields["target_name"],
            "local_state": fields["local_state"],
            "nextcloud_sync_state": fields["nextcloud_sync_state"],
            "remote_note_ref": fields["remote_note_ref"],
            "etag_value": fields["etag_value"],
            "etag_hash": fields["etag_hash"],
            "markdown_char_count": fields["markdown_char_count"],
            "reason_code": fields["reason_code"],
            "created_at": "2026-06-18T11:00:00Z",
            "updated_at": "2026-06-18T11:00:00Z",
            "deleted_at": None,
        }
        self.notes.append(item)
        return dict(item)

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeWorkspaceFolderNoteNextcloudRuntime:
    def __init__(self):
        self.calls = []

    def create_workspace_note_nextcloud_first(
        self,
        *,
        folder,
        title,
        markdown,
        notes_module,
    ):
        self.calls.append(
            {
                "folder_id": folder.get("id"),
                "title": title,
                "markdown_size": len(markdown or ""),
            }
        )
        stored = notes_module.upsert_note(
            note_id="33333333-3333-4333-8333-333333333333",
            workspace_folder_id=folder.get("id"),
            title=title,
            target_name=workspace_folder_notes.sanitize_note_target_name(title),
            local_state="available",
            nextcloud_sync_state="linked",
            remote_note_ref="workspace-note:33333333:abc123def456",
            etag_value='"raw-etag-hidden"',
            etag_hash="123456abcdef",
            markdown_char_count=len(markdown or ""),
            reason_code="folder_note_create_ok",
        )
        return {
            "ok": True,
            "note": stored,
            "reason_code": "folder_note_create_ok",
            "status": 201,
            "note_nextcloud": {
                "create_state": "stored",
                "reason_code": "folder_note_create_ok",
                "note_name_hash": "abc123def456",
                "http_status_class": "2xx",
                "etag_hash": "123456abcdef",
                "etag_present": True,
            },
        }


class ServerWorkspaceFolderNotesContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_notes = self.server.workspace_folder_notes
        self.original_workspace_folder_note_nextcloud_runtime = (
            self.server.workspace_folder_note_nextcloud_runtime
        )
        self.fake_workspace = _FakeWorkspaceFolders()
        self.fake_workspace_folder_notes = _FakeWorkspaceFolderNotes()
        self.fake_workspace_folder_note_nextcloud_runtime = (
            _FakeWorkspaceFolderNoteNextcloudRuntime()
        )
        self.server.workspace_folders = self.fake_workspace
        self.server.workspace_folder_notes = self.fake_workspace_folder_notes
        self.server.workspace_folder_note_nextcloud_runtime = (
            self.fake_workspace_folder_note_nextcloud_runtime
        )

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_notes = self.original_workspace_folder_notes
        self.server.workspace_folder_note_nextcloud_runtime = (
            self.original_workspace_folder_note_nextcloud_runtime
        )

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

    def _seed_note(
        self,
        note_id="33333333-3333-4333-8333-333333333333",
        *,
        title="Carnet sensible",
        state="available",
        deleted_at=None,
    ):
        target_name = workspace_folder_notes.sanitize_note_target_name(title)
        item = {
            "id": note_id,
            "workspace_folder_id": FOLDER_ID,
            "title": title,
            "title_hash": workspace_folder_notes.title_hash_for_target(target_name),
            "target_name": target_name,
            "local_state": state,
            "nextcloud_sync_state": "linked" if state != "deleted" else "deleted",
            "remote_note_ref": f"workspace-note:{note_id[:8]}:abcdef123456",
            "etag_value": '"raw-etag-hidden"',
            "etag_hash": "123456abcdef",
            "markdown_char_count": 12,
            "reason_code": "folder_note_lookup_ok",
            "created_at": "2026-06-18T11:00:00Z",
            "updated_at": "2026-06-18T11:00:00Z",
            "deleted_at": deleted_at,
            "markdown_body": "corps markdown interdit",
        }
        self.fake_workspace_folder_notes.notes.append(item)
        return item

    def test_workspace_folder_note_create_route_is_namespaced_and_content_free(self) -> None:
        self._create_linked_folder()

        global_route = self.client.post("/api/notes", json={"title": "Carnet"})
        self.assertIn(global_route.status_code, {404, 405})

        created = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/notes",
            json={"title": "Carnet sensible", "markdown": "# contenu initial"},
        )

        self.assertEqual(created.status_code, 201)
        payload = created.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(payload["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertEqual(payload["note"]["note_v1_user"]["status"], "available")
        self.assertEqual(payload["note_nextcloud"]["reason_code"], "folder_note_create_ok")
        self.assertEqual(
            self.fake_workspace_folder_note_nextcloud_runtime.calls[0]["folder_id"],
            FOLDER_ID,
        )
        self.assertEqual(
            self.fake_workspace_folder_note_nextcloud_runtime.calls[0]["markdown_size"],
            len("# contenu initial"),
        )
        self.assertNotIn("markdown", payload["note"])
        self.assertNotIn("etag_value", payload["note"])
        self.assertNotIn("target_name", payload["note"])
        self.assertNotIn("remote_note_ref", payload["note"])
        self.assertNotIn("Carnet sensible", str(payload["note"]["note_v1_technical"]))
        self.assertNotIn("contenu initial", str(payload))
        self.assertNotIn("raw-etag-hidden", str(payload))
        self.assertNotIn("Carnet-sensible.md", str(payload["note_nextcloud"]))

    def test_workspace_folder_note_list_route_uses_local_read_model_and_is_content_free(self) -> None:
        self._create_linked_folder()
        self.fake_workspace_folder_notes.notes = [
            {
                "id": "33333333-3333-4333-8333-333333333333",
                "workspace_folder_id": FOLDER_ID,
                "title": "Carnet sensible",
                "title_hash": workspace_folder_notes.title_hash_for_target("Carnet-sensible.md"),
                "target_name": "Carnet-sensible.md",
                "local_state": "available",
                "nextcloud_sync_state": "linked",
                "remote_note_ref": "workspace-note:33333333:abcdef123456",
                "etag_value": '"raw-etag-hidden"',
                "etag_hash": "123456abcdef",
                "markdown_char_count": 12,
                "reason_code": "folder_note_list_ok",
                "created_at": "2026-06-18T11:00:00Z",
                "updated_at": "2026-06-18T11:00:00Z",
                "deleted_at": None,
                "markdown_body": "corps markdown interdit",
            },
            {
                "id": "44444444-4444-4444-8444-444444444444",
                "workspace_folder_id": FOLDER_ID,
                "title": "Note supprimee",
                "title_hash": workspace_folder_notes.title_hash_for_target("Note-supprimee.md"),
                "target_name": "Note-supprimee.md",
                "local_state": "deleted",
                "nextcloud_sync_state": "deleted",
                "remote_note_ref": "workspace-note:44444444:bbbbbb123456",
                "etag_value": '"deleted-etag-hidden"',
                "etag_hash": "abcdef123456",
                "markdown_char_count": 0,
                "reason_code": "folder_note_not_found",
                "created_at": "2026-06-18T11:00:00Z",
                "updated_at": "2026-06-18T11:00:00Z",
                "deleted_at": "2026-06-18T11:01:00Z",
            },
        ]

        global_route = self.client.get("/api/notes")
        self.assertIn(global_route.status_code, {404, 405})

        listed = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes")

        self.assertEqual(listed.status_code, 200)
        payload = listed.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["count"], 1)
        item = payload["items"][0]
        self.assertEqual(item["note_v1_user"]["title"], "Carnet sensible")
        self.assertEqual(item["note_v1_user"]["status"], "available")
        self.assertEqual(item["note_v1_technical"]["reason_code"], "folder_note_list_ok")
        self.assertNotIn("Carnet sensible", str(item["note_v1_technical"]))
        self.assertNotIn("Note supprimee", str(payload))
        self.assertNotIn("corps markdown interdit", str(payload))
        self.assertNotIn("raw-etag-hidden", str(payload))
        self.assertNotIn("target_name", item)
        self.assertNotIn("remote_note_ref", item)
        self.assertNotIn("etag_value", item)

    def test_workspace_folder_note_list_route_fails_closed_on_read_model_failure(self) -> None:
        self._create_linked_folder()
        self.fake_workspace_folder_notes.fail_list = True

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_lookup_failed")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["count"], 0)
        self.assertNotIn("raw lookup failure", str(payload))

    def test_workspace_folder_note_list_route_refuses_non_linked_folder_without_webdav(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes")

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_folder_not_linked")
        self.assertEqual(payload["items"], [])
        self.assertEqual(payload["count"], 0)
        self.assertEqual(self.fake_workspace_folder_note_nextcloud_runtime.calls, [])

    def test_workspace_folder_note_list_route_returns_deleted_folder_state(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")
        self.fake_workspace.folders[FOLDER_ID]["deleted_at"] = "2026-06-18T12:00:00Z"

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes")

        self.assertEqual(response.status_code, 410)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "workspace_folder_deleted")
        self.assertNotIn("Projet", str(payload))
        self.assertEqual(self.fake_workspace_folder_notes.notes, [])

    def test_workspace_folder_note_get_route_resolves_explicit_note_id_content_free(self) -> None:
        self._create_linked_folder()
        note = self._seed_note()

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes/{note['id']}")

        self.assertEqual(response.status_code, 200)
        payload = response.get_json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_lookup_ok")
        self.assertEqual(payload["lookup"]["mode"], "note_id")
        self.assertEqual(payload["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertNotIn("Carnet sensible", str(payload["note"]["note_v1_technical"]))
        self.assertNotIn("raw-etag-hidden", str(payload))
        self.assertNotIn("Carnet-sensible.md", str(payload))
        self.assertNotIn("corps markdown interdit", str(payload))
        self.assertNotIn("target_name", payload["note"])
        self.assertNotIn("remote_note_ref", payload["note"])

    def test_workspace_folder_note_lookup_route_resolves_exact_or_sanitized_title(self) -> None:
        self._create_linked_folder()
        self._seed_note(title="Carnet sensible")

        exact = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/notes/lookup",
            query_string={"title": "Carnet sensible"},
        )
        sanitized = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/notes/lookup",
            query_string={"title": "Carnet-sensible.md"},
        )

        self.assertEqual(exact.status_code, 200)
        self.assertEqual(sanitized.status_code, 200)
        self.assertEqual(exact.get_json()["lookup"]["mode"], "title")
        self.assertEqual(sanitized.get_json()["note"]["note_v1_user"]["title"], "Carnet sensible")

    def test_workspace_folder_note_lookup_route_refuses_ambiguous_title(self) -> None:
        self._create_linked_folder()
        self._seed_note(title="Carnet sensible")
        self._seed_note(
            note_id="44444444-4444-4444-8444-444444444444",
            title="Carnet sensible",
        )

        response = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/notes/lookup",
            query_string={"title": "Carnet sensible"},
        )

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_note_lookup_ambiguous")
        self.assertEqual(payload["lookup"]["matched_count"], 2)
        self.assertEqual(payload["note"]["status"], "conflict")
        self.assertNotIn("Carnet sensible", str(payload["lookup"]))

    def test_workspace_folder_note_lookup_route_distinguishes_missing_from_store_failure(self) -> None:
        self._create_linked_folder()

        missing = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes/33333333-3333-4333-8333-333333333333")
        self.fake_workspace_folder_notes.fail_list = True
        failed = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/notes/lookup",
            query_string={"title": "Carnet sensible"},
        )

        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.get_json()["reason_code"], "folder_note_not_found")
        self.assertEqual(failed.status_code, 503)
        self.assertEqual(failed.get_json()["reason_code"], "folder_note_lookup_failed")
        self.assertNotIn("raw lookup failure", str(failed.get_json()))

    def test_workspace_folder_note_lookup_route_refuses_non_linked_and_deleted_folder(self) -> None:
        self.fake_workspace.create_workspace_folder(display_name="Projet", icon_key="folder", description="")

        non_linked = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/notes/lookup",
            query_string={"title": "Carnet sensible"},
        )
        self.fake_workspace.folders[FOLDER_ID]["deleted_at"] = "2026-06-18T12:00:00Z"
        deleted = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/notes/33333333-3333-4333-8333-333333333333")

        self.assertEqual(non_linked.status_code, 409)
        self.assertEqual(non_linked.get_json()["reason_code"], "folder_note_folder_not_linked")
        self.assertEqual(deleted.status_code, 410)
        self.assertEqual(deleted.get_json()["reason_code"], "workspace_folder_deleted")
        self.assertEqual(self.fake_workspace_folder_note_nextcloud_runtime.calls, [])


if __name__ == "__main__":
    unittest.main()
