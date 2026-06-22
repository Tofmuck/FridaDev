from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_list


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
NOTE_ID = "33333333-3333-4333-8333-333333333333"
OTHER_NOTE_ID = "44444444-4444-4444-8444-444444444444"


class _FakeNotesModule:
    def __init__(self, notes=None, *, fail_lookup: bool = False):
        self.notes = list(notes or [])
        self.fail_lookup = fail_lookup
        self.calls = []
        self.events = []

    def list_notes(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        self.calls.append(
            {
                "workspace_folder_id": workspace_folder_id,
                "include_deleted": include_deleted,
                "fail_closed": fail_closed,
            }
        )
        if self.fail_lookup:
            raise RuntimeError("raw db failure should not escape")
        if include_deleted:
            return list(self.notes)
        return [
            note
            for note in self.notes
            if not note.get("deleted_at")
            and note.get("local_state") != workspace_folder_notes.NOTE_LOCAL_DELETED
        ]

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


def _linked_folder():
    return {
        "id": FOLDER_ID,
        "display_name": "Projet sensible",
        "nextcloud_sync_state": "linked",
        "deleted_at": None,
    }


def _local_folder():
    folder = _linked_folder()
    folder["nextcloud_sync_state"] = "local_only"
    return folder


def _note(
    note_id=NOTE_ID,
    *,
    title="Carnet sensible",
    state=workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
    sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
    deleted_at=None,
    reason_code=workspace_folder_notes.REASON_LIST_OK,
):
    target_name = workspace_folder_notes.sanitize_note_target_name(title)
    return {
        "id": note_id,
        "workspace_folder_id": FOLDER_ID,
        "title": title,
        "title_hash": workspace_folder_notes.title_hash_for_target(target_name),
        "target_name": target_name,
        "local_state": state,
        "nextcloud_sync_state": sync_state,
        "remote_note_ref": "workspace-note:33333333:abcdef123456",
        "etag_value": '"raw-etag-hidden"',
        "etag_hash": "123456abcdef",
        "markdown_char_count": 42,
        "reason_code": reason_code,
        "created_at": "2026-06-18T11:00:00Z",
        "updated_at": "2026-06-18T11:10:00Z",
        "deleted_at": deleted_at,
        "markdown_body": "corps markdown interdit",
    }


class WorkspaceFolderNotesListTests(unittest.TestCase):
    def test_lists_active_notes_with_user_titles_and_content_free_technical_projection(self):
        notes = [
            _note(title="Carnet sensible"),
            _note(OTHER_NOTE_ID, title="Suivi equipe"),
        ]
        fake = _FakeNotesModule(notes)

        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _linked_folder(),
            notes_module=fake,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LIST_OK)
        self.assertEqual(result["count"], 2)
        titles = [item["note_v1_user"]["title"] for item in result["items"]]
        self.assertEqual(titles, ["Carnet sensible", "Suivi equipe"])
        for item in result["items"]:
            technical = item["note_v1_technical"]
            self.assertNotIn(item["note_v1_user"]["title"], str(technical))
            self.assertNotIn("raw-etag-hidden", str(technical))
            self.assertNotIn("Carnet-sensible.md", str(item))
            self.assertNotIn("remote_note_ref", item)
            self.assertNotIn("target_name", item)
            self.assertNotIn("etag_value", item)
            self.assertNotIn("markdown_body", item)

        self.assertEqual(fake.calls[0]["include_deleted"], False)
        self.assertEqual(fake.calls[0]["fail_closed"], True)

    def test_excludes_deleted_notes_from_active_list(self):
        fake = _FakeNotesModule(
            [
                _note(title="Active"),
                _note(
                    OTHER_NOTE_ID,
                    title="Supprimee",
                    state=workspace_folder_notes.NOTE_LOCAL_DELETED,
                    deleted_at="2026-06-18T12:00:00Z",
                    reason_code=workspace_folder_notes.REASON_NOT_FOUND,
                ),
            ]
        )

        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _linked_folder(),
            notes_module=fake,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["items"][0]["note_v1_user"]["title"], "Active")

    def test_empty_list_is_not_an_error(self):
        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _linked_folder(),
            notes_module=_FakeNotesModule([]),
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["count"], 0)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LIST_OK)

    def test_sync_error_and_conflict_are_visible_without_raw_technical_values(self):
        fake = _FakeNotesModule(
            [
                _note(
                    title="Conflit",
                    state=workspace_folder_notes.NOTE_LOCAL_CONFLICT,
                    reason_code=workspace_folder_notes.REASON_NAME_CONFLICT,
                ),
                _note(
                    OTHER_NOTE_ID,
                    title="Erreur sync",
                    state=workspace_folder_notes.NOTE_LOCAL_SYNC_ERROR,
                    sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_SYNC_ERROR,
                    reason_code=workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED,
                ),
            ]
        )

        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _linked_folder(),
            notes_module=fake,
        )

        self.assertTrue(result["ok"])
        statuses = [item["note_v1_user"]["status"] for item in result["items"]]
        self.assertEqual(statuses, ["conflict", "sync_error"])
        self.assertNotIn("raw-etag-hidden", str(result["items"]))
        self.assertNotIn("corps markdown interdit", str(result["items"]))

    def test_lookup_failure_fails_closed_instead_of_returning_empty_list(self):
        fake = _FakeNotesModule(fail_lookup=True)

        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _linked_folder(),
            notes_module=fake,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 503)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOOKUP_FAILED)
        self.assertEqual(result["items"], [])
        self.assertEqual(result["count"], 0)
        self.assertIn("list_lookup_failed", [event for event, _ in fake.events])
        self.assertNotIn("raw db failure", str(result))

    def test_non_linked_folder_is_refused_without_reading_notes(self):
        fake = _FakeNotesModule([_note()])

        result = workspace_folder_notes_list.list_workspace_folder_notes(
            _local_folder(),
            notes_module=fake,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 409)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_FOLDER_NOT_LINKED)
        self.assertEqual(result["items"], [])
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
