from __future__ import annotations

import unittest

from core import workspace_folder_note_nextcloud_client as note_client
from core import workspace_folder_notes
from core import workspace_folder_notes_read


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
OTHER_FOLDER_ID = "22222222-2222-4222-8222-222222222222"
NOTE_ID = "33333333-3333-4333-8333-333333333333"


class _ContentResponse:
    ok = True
    reason_code = workspace_folder_notes.REASON_READ_OK
    http_status = 200

    def __init__(self, markdown: str, etag_value: str = '"etag-hidden"'):
        self.markdown = markdown
        self.etag_value = etag_value

    @property
    def status_class(self):
        return "2xx"


class _FakeClient:
    def __init__(self, *, markdown: str = "# Note", etag_value: str = '"etag-hidden"', fail_get: str = ""):
        self.markdown = markdown
        self.etag_value = etag_value
        self.fail_get = fail_get
        self.get_calls = []

    def get_note_content(self, folder_name, note_name, *, max_bytes):
        self.get_calls.append(
            {"folder_name": folder_name, "note_name": note_name, "max_bytes": max_bytes}
        )
        if self.fail_get:
            raise note_client.NextcloudNoteClientError(self.fail_get, http_status=503)
        return _ContentResponse(self.markdown, self.etag_value)


class _FakeNotesModule:
    def __init__(self, *, note=None, fail_get=False):
        self.note = dict(note or _note())
        self.fail_get = fail_get
        self.calls = []
        self.events = []

    def get_note(self, note_id, *, fail_closed=True):
        self.calls.append({"note_id": note_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw db failure with markdown # secret and etag")
        if workspace_folder_notes.normalize_note_id(note_id) == self.note.get("id"):
            return dict(self.note)
        return None

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


def _folder(sync_state="linked"):
    return {
        "id": FOLDER_ID,
        "display_name": "Projet sensible",
        "nextcloud_target_name": "Projet-sensible",
        "nextcloud_sync_state": sync_state,
        "deleted_at": None,
    }


def _note(
    *,
    note_id=NOTE_ID,
    folder_id=FOLDER_ID,
    title="Carnet sensible",
    state=workspace_folder_notes.NOTE_LOCAL_AVAILABLE,
    sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_LINKED,
    deleted_at=None,
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
        "reason_code": workspace_folder_notes.REASON_LOOKUP_OK,
        "created_at": "2026-06-18T11:00:00Z",
        "updated_at": "2026-06-18T11:10:00Z",
        "deleted_at": deleted_at,
        "markdown_body": "corps markdown interdit",
    }


class WorkspaceFolderNotesReadTests(unittest.TestCase):
    def test_read_nominal_returns_markdown_only_in_conversation_payload(self):
        markdown = "# Carnet\n\nContenu utile"
        notes = _FakeNotesModule()
        client = _FakeClient(markdown=markdown, etag_value='"etag-current"')

        result = workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
            _folder(),
            note_id=NOTE_ID,
            notes_module=notes,
            nextcloud=client,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_READ_OK)
        self.assertEqual(result["note_conversation"]["markdown_content"], markdown)
        self.assertEqual(result["note_conversation"]["markdown_char_count"], len(markdown))
        self.assertEqual(result["note_conversation"]["injection_scope"], "current_turn_only")
        self.assertEqual(result["note_conversation"]["memory_rag_identity_summary"], "not_used")
        self.assertEqual(client.get_calls[0]["note_name"], "Carnet-sensible.md")
        self.assertEqual(notes.calls[0]["fail_closed"], True)
        technical_surfaces = (
            str(result["note"]["note_v1_technical"])
            + str(result["note_nextcloud"])
            + str(notes.events)
        )
        self.assertNotIn(markdown, technical_surfaces)
        self.assertNotIn("Carnet sensible", str(result["note"]["note_v1_technical"]))
        self.assertNotIn("etag-current", technical_surfaces)
        self.assertNotIn("Carnet-sensible.md", technical_surfaces)
        self.assertNotIn("corps markdown interdit", str(result))

    def test_too_large_note_is_refused_without_markdown_injection(self):
        markdown = "x" * (workspace_folder_notes_read.NOTE_READ_MAX_CHARS + 1)

        result = workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
            _folder(),
            note_id=NOTE_ID,
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(markdown=markdown),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 413)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_TOO_LARGE)
        self.assertNotIn("markdown_content", result["note_conversation"])
        self.assertNotIn(markdown, str(result))

    def test_missing_deleted_sync_error_and_other_folder_are_refused_before_webdav(self):
        client = _FakeClient(markdown="# should not be read")

        cases = [
            _FakeNotesModule(note=_note(note_id="44444444-4444-4444-8444-444444444444")),
            _FakeNotesModule(
                note=_note(
                    state=workspace_folder_notes.NOTE_LOCAL_DELETED,
                    deleted_at="2026-06-18T12:00:00Z",
                )
            ),
            _FakeNotesModule(
                note=_note(
                    state=workspace_folder_notes.NOTE_LOCAL_SYNC_ERROR,
                    sync_state=workspace_folder_notes.NOTE_NEXTCLOUD_SYNC_ERROR,
                )
            ),
            _FakeNotesModule(note=_note(folder_id=OTHER_FOLDER_ID)),
        ]

        results = [
            workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
                _folder(),
                note_id=NOTE_ID,
                notes_module=notes,
                nextcloud=client,
            )
            for notes in cases
        ]

        self.assertEqual(results[0]["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(results[1]["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(results[2]["reason_code"], workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED)
        self.assertEqual(results[3]["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(client.get_calls, [])
        self.assertNotIn("markdown_content", str(results))

    def test_non_linked_folder_is_refused_before_store_or_webdav(self):
        notes = _FakeNotesModule()
        client = _FakeClient()

        result = workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
            _folder(sync_state="local_only"),
            note_id=NOTE_ID,
            notes_module=notes,
            nextcloud=client,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_FOLDER_NOT_LINKED)
        self.assertEqual(notes.calls, [])
        self.assertEqual(client.get_calls, [])

    def test_store_failure_fails_closed_without_raw_error(self):
        result = workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
            _folder(),
            note_id=NOTE_ID,
            notes_module=_FakeNotesModule(fail_get=True),
            nextcloud=_FakeClient(markdown="# should not be read"),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 503)
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOOKUP_FAILED)
        self.assertNotIn("raw db failure", str(result))
        self.assertNotIn("markdown # secret", str(result))

    def test_remote_get_failure_is_content_free(self):
        result = workspace_folder_notes_read.prepare_workspace_folder_note_for_conversation(
            _folder(),
            note_id=NOTE_ID,
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(
                markdown="# should not escape",
                fail_get=workspace_folder_notes.REASON_REMOTE_READ_FAILED,
            ),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_REMOTE_READ_FAILED)
        self.assertEqual(result["note_nextcloud"]["read_state"], "remote_read_failed")
        self.assertNotIn("# should not escape", str(result))
        self.assertNotIn("markdown_content", result["note_conversation"])


if __name__ == "__main__":
    unittest.main()
