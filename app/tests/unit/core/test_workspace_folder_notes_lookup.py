from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_lookup


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
OTHER_FOLDER_ID = "22222222-2222-4222-8222-222222222222"
NOTE_ID = "33333333-3333-4333-8333-333333333333"
OTHER_NOTE_ID = "44444444-4444-4444-8444-444444444444"


class _FakeNotesModule:
    def __init__(self, notes=None, *, fail_get: bool = False, fail_list: bool = False):
        self.notes = list(notes or [])
        self.fail_get = fail_get
        self.fail_list = fail_list
        self.calls = []
        self.events = []

    def get_note(self, note_id, *, fail_closed=True):
        self.calls.append({"operation": "get", "note_id": note_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw get failure")
        for note in self.notes:
            if workspace_folder_notes.normalize_note_id(note.get("id")) == note_id:
                return dict(note)
        return None

    def list_notes(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        self.calls.append(
            {
                "operation": "list",
                "workspace_folder_id": workspace_folder_id,
                "include_deleted": include_deleted,
                "fail_closed": fail_closed,
            }
        )
        if self.fail_list:
            raise RuntimeError("raw list failure")
        items = [
            dict(note)
            for note in self.notes
            if workspace_folder_notes.normalize_workspace_folder_id(note.get("workspace_folder_id"))
            == workspace_folder_id
        ]
        if include_deleted:
            return items
        return [
            note
            for note in items
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
    folder_id=FOLDER_ID,
    title="Carnet sensible",
    state=workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
    sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
    deleted_at=None,
    reason_code=workspace_folder_notes.REASON_LOOKUP_OK,
):
    target_name = workspace_folder_notes.sanitize_note_target_name(title)
    return {
        "id": note_id,
        "workspace_folder_id": folder_id,
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


class WorkspaceFolderNotesLookupTests(unittest.TestCase):
    def test_lookup_by_note_id_returns_user_projection_without_technical_leaks(self):
        fake = _FakeNotesModule([_note()])

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            note_id=NOTE_ID,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOOKUP_OK)
        self.assertEqual(result["lookup"]["mode"], "note_id")
        self.assertEqual(result["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertNotIn("Carnet sensible", str(result["note"]["note_v1_technical"]))
        self.assertNotIn("raw-etag-hidden", str(result))
        self.assertNotIn("Carnet-sensible.md", str(result))
        self.assertNotIn("corps markdown interdit", str(result))
        self.assertEqual(fake.calls[0]["fail_closed"], True)

    def test_lookup_by_exact_title_uses_local_read_model_only(self):
        fake = _FakeNotesModule([_note(title="Carnet sensible")])

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            title="Carnet sensible",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["lookup"]["mode"], "title")
        self.assertEqual(result["note"]["note_v1_user"]["title"], "Carnet sensible")
        self.assertEqual(fake.calls[0]["operation"], "list")
        self.assertEqual(fake.calls[0]["fail_closed"], True)

    def test_lookup_by_sanitized_markdown_target_matches_existing_note(self):
        fake = _FakeNotesModule([_note(title="Carnet sensible")])

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            title="Carnet-sensible.md",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["note"]["note_v1_user"]["title"], "Carnet sensible")

    def test_ambiguous_title_refuses_without_arbitrary_choice(self):
        fake = _FakeNotesModule(
            [
                _note(title="Carnet sensible"),
                _note(OTHER_NOTE_ID, title="Carnet sensible"),
            ]
        )

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            title="Carnet sensible",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 409)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOOKUP_AMBIGUOUS)
        self.assertEqual(result["lookup"]["matched_count"], 2)
        self.assertEqual(result["note"], {})

    def test_missing_or_deleted_note_is_not_returned(self):
        fake = _FakeNotesModule(
            [
                _note(
                    title="Archive",
                    state=workspace_folder_notes.NOTE_LOCAL_DELETED,
                    deleted_at="2026-06-18T12:00:00Z",
                )
            ]
        )

        by_id = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            note_id=NOTE_ID,
        )
        by_title = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            title="Archive",
        )

        self.assertEqual(by_id["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(by_title["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)

    def test_note_from_another_folder_is_not_returned(self):
        fake = _FakeNotesModule([_note(folder_id=OTHER_FOLDER_ID)])

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            note_id=NOTE_ID,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)

    def test_lookup_failure_fails_closed_without_raw_error(self):
        fake = _FakeNotesModule(fail_list=True)

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _linked_folder(),
            notes_module=fake,
            title="Carnet sensible",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 503)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOOKUP_FAILED)
        self.assertNotIn("raw list failure", str(result))

    def test_non_linked_folder_is_refused_without_reading_notes(self):
        fake = _FakeNotesModule([_note()])

        result = workspace_folder_notes_lookup.lookup_workspace_folder_note(
            _local_folder(),
            notes_module=fake,
            title="Carnet sensible",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 409)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_FOLDER_NOT_LINKED)
        self.assertEqual(fake.calls, [])


if __name__ == "__main__":
    unittest.main()
