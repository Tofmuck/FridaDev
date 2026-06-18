from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_append
from core import workspace_folder_note_nextcloud_client as note_client


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
NOTE_ID = "33333333-3333-4333-8333-333333333333"


class _ContentResponse:
    ok = True
    reason_code = workspace_folder_notes.REASON_LOOKUP_OK
    http_status = 200

    def __init__(self, markdown: str, etag_value: str):
        self.markdown = markdown
        self.etag_value = etag_value

    @property
    def status_class(self):
        return "2xx"


class _PutResponse:
    ok = True
    reason_code = workspace_folder_notes.REASON_APPEND_OK
    http_status = 204

    def __init__(self, etag_value: str):
        self.etag_value = etag_value

    @property
    def status_class(self):
        return "2xx"


class _FakeClient:
    def __init__(
        self,
        *,
        current_markdown: str = "Ancien contenu",
        current_etag: str = '"etag-before"',
        put_etag: str = '"etag-after"',
        recovery_markdown: str | None = None,
        recovery_etag: str | None = None,
        fail_get: str = "",
        fail_put: str = "",
        fail_restore: str = "",
    ):
        self.current_markdown = current_markdown
        self.current_etag = current_etag
        self.put_etag = put_etag
        self.recovery_markdown = recovery_markdown
        self.recovery_etag = recovery_etag
        self.fail_get = fail_get
        self.fail_put = fail_put
        self.fail_restore = fail_restore
        self.get_calls = []
        self.put_calls = []

    def get_note_content(self, folder_name, note_name, *, max_bytes):
        self.get_calls.append(
            {"folder_name": folder_name, "note_name": note_name, "max_bytes": max_bytes}
        )
        if self.fail_get:
            raise note_client.NextcloudNoteClientError(self.fail_get, http_status=503)
        if len(self.get_calls) > 1:
            return _ContentResponse(
                self.recovery_markdown if self.recovery_markdown is not None else self.current_markdown,
                self.recovery_etag if self.recovery_etag is not None else self.current_etag,
            )
        return _ContentResponse(self.current_markdown, self.current_etag)

    def put_note_if_match(self, folder_name, note_name, markdown, *, etag_value):
        self.put_calls.append(
            {
                "folder_name": folder_name,
                "note_name": note_name,
                "markdown": bytes(markdown or b"").decode("utf-8"),
                "etag_value": etag_value,
            }
        )
        if len(self.put_calls) == 1 and self.fail_put:
            raise note_client.NextcloudNoteClientError(self.fail_put, http_status=412)
        if len(self.put_calls) > 1 and self.fail_restore:
            raise note_client.NextcloudNoteClientError(self.fail_restore, http_status=412)
        return _PutResponse(self.put_etag if len(self.put_calls) == 1 else '"etag-restored"')


class _FakeNotesModule:
    def __init__(self, *, note=None, fail_get=False, fail_upsert=False):
        self.note = dict(note or _note())
        self.fail_get = fail_get
        self.fail_upsert = fail_upsert
        self.upserts = []
        self.events = []

    def get_note(self, note_id, *, fail_closed=True):
        if self.fail_get:
            raise RuntimeError("raw lookup failure")
        if workspace_folder_notes.normalize_note_id(note_id) == self.note.get("id"):
            return dict(self.note)
        return None

    def upsert_note(self, **fields):
        if self.fail_upsert:
            raise RuntimeError("raw persistence failure")
        self.upserts.append(dict(fields))
        stored = dict(self.note)
        stored.update(
            {
                "etag_value": fields["etag_value"],
                "etag_hash": fields["etag_hash"],
                "markdown_char_count": fields["markdown_char_count"],
                "reason_code": fields["reason_code"],
                "local_state": fields["local_state"],
                "nextcloud_sync_state": fields["nextcloud_sync_state"],
            }
        )
        self.note = stored
        return dict(stored)

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


def _folder(sync_state="linked"):
    return {
        "id": FOLDER_ID,
        "display_name": "Projet sensible",
        "nextcloud_sync_state": sync_state,
        "deleted_at": None,
    }


def _note(*, state="available", sync_state="linked", deleted_at=None, folder_id=FOLDER_ID):
    return {
        "id": NOTE_ID,
        "workspace_folder_id": folder_id,
        "title": "Carnet sensible",
        "title_hash": workspace_folder_notes.title_hash_for_target("Carnet-sensible.md"),
        "target_name": "Carnet-sensible.md",
        "local_state": state,
        "nextcloud_sync_state": sync_state,
        "remote_note_ref": "workspace-note:33333333:abcdef123456",
        "etag_value": '"etag-before-local"',
        "etag_hash": "123456abcdef",
        "markdown_char_count": 14,
        "reason_code": "folder_note_lookup_ok",
        "created_at": "2026-06-18T11:00:00Z",
        "updated_at": "2026-06-18T11:00:00Z",
        "deleted_at": deleted_at,
        "markdown_body": "corps markdown interdit",
    }


class WorkspaceFolderNotesAppendTests(unittest.TestCase):
    def test_append_nominal_adds_separator_at_end_and_updates_metadata(self):
        notes = _FakeNotesModule()
        client = _FakeClient(current_markdown="Ancien contenu", put_etag='"etag-after"')

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Nouvel ajout",
            notes_module=notes,
            nextcloud=client,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_APPEND_OK)
        self.assertEqual(
            client.put_calls[0]["markdown"],
            f"Ancien contenu{workspace_folder_notes_append.APPEND_SEPARATOR}Nouvel ajout",
        )
        self.assertEqual(client.put_calls[0]["etag_value"], '"etag-before"')
        self.assertEqual(notes.upserts[0]["reason_code"], workspace_folder_notes.REASON_APPEND_OK)
        self.assertEqual(notes.upserts[0]["markdown_char_count"], len(client.put_calls[0]["markdown"]))
        projected = workspace_folder_notes.apply_note_projection(result["note"], folder=_folder())
        self.assertNotIn("Ancien contenu", str(result["note_nextcloud"]) + str(projected))
        self.assertNotIn("Nouvel ajout", str(result["note_nextcloud"]) + str(projected))
        self.assertNotIn("etag-after", str(result["note_nextcloud"]) + str(projected))
        self.assertNotIn("Carnet-sensible.md", str(result["note_nextcloud"]))

    def test_empty_and_too_large_append_are_refused_before_webdav(self):
        empty_client = _FakeClient()
        too_large_client = _FakeClient()

        empty = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="   ",
            notes_module=_FakeNotesModule(),
            nextcloud=empty_client,
        )
        too_large = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="x" * (workspace_folder_notes_append.NOTE_APPEND_MAX_CHARS + 1),
            notes_module=_FakeNotesModule(),
            nextcloud=too_large_client,
        )

        self.assertEqual(empty["reason_code"], workspace_folder_notes_append.REASON_APPEND_EMPTY)
        self.assertEqual(too_large["reason_code"], workspace_folder_notes.REASON_APPEND_TOO_LARGE)
        self.assertEqual(empty_client.get_calls, [])
        self.assertEqual(too_large_client.get_calls, [])

    def test_total_note_too_large_is_refused_before_put(self):
        client = _FakeClient(current_markdown="a" * workspace_folder_notes_append.NOTE_TOTAL_MAX_CHARS)

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="x",
            notes_module=_FakeNotesModule(),
            nextcloud=client,
        )

        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_TOO_LARGE)
        self.assertEqual(client.put_calls, [])

    def test_missing_deleted_sync_error_and_non_linked_folder_are_refused_before_webdav(self):
        client = _FakeClient()
        missing = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id="44444444-4444-4444-8444-444444444444",
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=client,
        )
        deleted = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(note=_note(state="deleted", deleted_at="2026-06-18T12:00:00Z")),
            nextcloud=client,
        )
        sync_error = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(note=_note(state="sync_error", sync_state="sync_error")),
            nextcloud=client,
        )
        non_linked = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(sync_state="local_only"),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=client,
        )

        self.assertEqual(missing["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(deleted["reason_code"], workspace_folder_notes.REASON_NOT_FOUND)
        self.assertEqual(sync_error["reason_code"], workspace_folder_notes.REASON_NEXTCLOUD_ERROR_REDACTED)
        self.assertEqual(non_linked["reason_code"], workspace_folder_notes.REASON_FOLDER_NOT_LINKED)
        self.assertEqual(client.get_calls, [])

    def test_get_failure_etag_missing_version_conflict_and_write_failure_are_content_free(self):
        get_failed = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(fail_get=workspace_folder_notes_append.REASON_REMOTE_READ_FAILED),
        )
        etag_missing = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(current_etag=""),
        )
        conflict = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(fail_put=workspace_folder_notes.REASON_VERSION_CONFLICT),
        )
        write_failed = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeClient(fail_put=workspace_folder_notes_append.REASON_REMOTE_WRITE_FAILED),
        )

        self.assertEqual(get_failed["reason_code"], workspace_folder_notes_append.REASON_REMOTE_READ_FAILED)
        self.assertEqual(etag_missing["reason_code"], workspace_folder_notes_append.REASON_ETAG_MISSING)
        self.assertEqual(conflict["reason_code"], workspace_folder_notes.REASON_VERSION_CONFLICT)
        self.assertEqual(write_failed["reason_code"], workspace_folder_notes_append.REASON_REMOTE_WRITE_FAILED)
        self.assertNotIn("Ajout", str(get_failed) + str(etag_missing) + str(conflict) + str(write_failed))

    def test_local_persistence_failure_triggers_strict_remote_compensation_ok(self):
        client = _FakeClient(current_markdown="Avant", put_etag='"etag-after"')

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(fail_upsert=True),
            nextcloud=client,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED)
        self.assertEqual(result["note_nextcloud"]["rollback"]["reason_code"], workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK)
        self.assertEqual(client.put_calls[1]["markdown"], "Avant")
        self.assertEqual(client.put_calls[1]["etag_value"], '"etag-after"')
        self.assertNotIn("Avant", str(result))
        self.assertNotIn("Ajout", str(result))

    def test_missing_post_write_etag_recovers_etag_and_rolls_back_remote(self):
        client = _FakeClient(
            current_markdown="Avant",
            put_etag="",
            recovery_markdown="Avant---Ajout",
            recovery_etag='"etag-recovered"',
        )
        notes = _FakeNotesModule()

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=notes,
            nextcloud=client,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_ETAG_MISSING)
        self.assertEqual(result["note_nextcloud"]["rollback"]["reason_code"], workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK)
        self.assertEqual(len(client.get_calls), 2)
        self.assertEqual(len(client.put_calls), 2)
        self.assertEqual(client.put_calls[1]["markdown"], "Avant")
        self.assertEqual(client.put_calls[1]["etag_value"], '"etag-recovered"')
        self.assertEqual(notes.upserts, [])
        self.assertNotIn("Avant", str(result))
        self.assertNotIn("Ajout", str(result))
        self.assertNotIn("etag-recovered", str(result))

    def test_missing_post_write_etag_marks_local_sync_error_when_rollback_is_impossible(self):
        client = _FakeClient(
            current_markdown="Avant",
            put_etag="",
            recovery_markdown="Avant---Ajout",
            recovery_etag="",
        )
        notes = _FakeNotesModule()

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=notes,
            nextcloud=client,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_ETAG_MISSING)
        self.assertEqual(result["note_nextcloud"]["rollback"]["reason_code"], workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED)
        self.assertEqual(result["note_nextcloud"]["local_mark_state"], "sync_error")
        self.assertEqual(notes.upserts[0]["local_state"], workspace_folder_notes.NOTE_LOCAL_SYNC_ERROR)
        self.assertEqual(notes.upserts[0]["nextcloud_sync_state"], workspace_folder_notes.NOTE_NEXTCLOUD_SYNC_ERROR)
        self.assertEqual(notes.upserts[0]["reason_code"], workspace_folder_notes.REASON_ETAG_MISSING)
        self.assertEqual(notes.upserts[0]["etag_value"], "")
        projected = workspace_folder_notes.apply_note_projection(notes.note, folder=_folder())
        self.assertEqual(projected["note_v1_user"]["status"], workspace_folder_notes.NOTE_LOCAL_SYNC_ERROR)
        self.assertNotIn("Avant", str(result) + str(projected))
        self.assertNotIn("Ajout", str(result) + str(projected))
        self.assertNotIn("etag-before", str(result) + str(projected))

    def test_local_persistence_failure_reports_compensation_failure(self):
        client = _FakeClient(
            current_markdown="Avant",
            put_etag='"etag-after"',
            fail_restore=workspace_folder_notes.REASON_VERSION_CONFLICT,
        )

        result = workspace_folder_notes_append.append_workspace_folder_note(
            _folder(),
            note_id=NOTE_ID,
            markdown="Ajout",
            notes_module=_FakeNotesModule(fail_upsert=True),
            nextcloud=client,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], workspace_folder_notes.REASON_LOCAL_PERSISTENCE_FAILED)
        self.assertEqual(result["note_nextcloud"]["rollback"]["reason_code"], workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED)


if __name__ == "__main__":
    unittest.main()
