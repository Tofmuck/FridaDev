from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_note_nextcloud_client
from core import workspace_folder_note_nextcloud_runtime
from core import workspace_folder_nextcloud_client
from core import workspace_folder_notes_store


NOTE_ID = "11111111-2222-4333-8444-555555555555"
FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(" ".join(str(sql).split()))


class _FailingConnection:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        raise RuntimeError("raw db failure with Carnet sensible and raw-etag-secret")


class _FakeLogger:
    def __init__(self):
        self.records = []

    def warning(self, message, *args, **kwargs):
        self.records.append((message, args, kwargs))


class _FakeNotesModule:
    def __init__(self, *, existing=None, fail_list=False, fail_upsert=False):
        self.existing = list(existing or [])
        self.fail_list = fail_list
        self.fail_upsert = fail_upsert
        self.stored = []
        self.events = []

    def list_notes(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        if self.fail_list:
            raise workspace_folder_notes_store.WorkspaceFolderNoteLookupError(
                "list",
                workspace_folder_id=workspace_folder_id,
            )
        if include_deleted:
            return list(self.existing)
        return [item for item in self.existing if not item.get("deleted_at")]

    def upsert_note(self, **fields):
        if self.fail_upsert:
            raise workspace_folder_notes_store.WorkspaceFolderNotePersistenceError(
                "folder_note_local_persistence_failed"
            )
        self.stored.append(dict(fields))
        return _note(
            id=fields["note_id"],
            workspace_folder_id=fields["workspace_folder_id"],
            title=fields["title"],
            title_hash=workspace_folder_notes.title_hash_for_target(fields["target_name"]),
            target_name=fields["target_name"],
            local_state=fields["local_state"],
            nextcloud_sync_state=fields["nextcloud_sync_state"],
            remote_note_ref=fields["remote_note_ref"],
            etag_value=fields["etag_value"],
            etag_hash=fields["etag_hash"],
            markdown_char_count=fields["markdown_char_count"],
            reason_code=fields["reason_code"],
        )

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeNextcloudNotes:
    def __init__(self, *, status_reason="", put_reason="", delete_reason="", etag='"etag-secret"'):
        self.status_reason = status_reason
        self.put_reason = put_reason
        self.delete_reason = delete_reason
        self.etag = etag
        self.status_calls = []
        self.put_calls = []
        self.deleted = []

    def notes_status(self, folder_name):
        self.status_calls.append(folder_name)
        if self.status_reason:
            raise workspace_folder_note_nextcloud_client.NextcloudNoteClientError(
                self.status_reason,
                http_status=404 if self.status_reason.endswith("_missing") else 207,
            )
        return workspace_folder_note_nextcloud_client.NextcloudNoteResponse(
            True,
            workspace_folder_notes.REASON_CREATE_OK,
            207,
        )

    def put_note(self, folder_name, note_name, markdown):
        self.put_calls.append((folder_name, note_name, bytes(markdown or b"")))
        if self.put_reason:
            raise workspace_folder_note_nextcloud_client.NextcloudNoteClientError(
                self.put_reason,
                http_status=409 if "conflict" in self.put_reason else 503,
            )
        return workspace_folder_note_nextcloud_client.NextcloudNoteResponse(
            True,
            workspace_folder_notes.REASON_CREATE_OK,
            201,
            etag_value=self.etag,
        )

    def delete_note(self, folder_name, note_name, *, missing_ok=True):
        self.deleted.append((folder_name, note_name, missing_ok))
        if self.delete_reason:
            raise workspace_folder_note_nextcloud_client.NextcloudNoteClientError(
                self.delete_reason,
                http_status=503,
            )
        return workspace_folder_note_nextcloud_client.NextcloudNoteResponse(
            True,
            workspace_folder_notes.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _StatusOnlyNoteClient(workspace_folder_note_nextcloud_client.NextcloudNoteClient):
    def __init__(self, status):
        super().__init__(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )
        self.status = status

    def _request_status(self, method, url, *, data=None, headers=None):
        return self.status, '"etag-secret"'


def _note(**overrides):
    payload = {
        "id": NOTE_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Carnet sensible",
        "title_hash": "abc123def456",
        "target_name": "Carnet-sensible.md",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_note_ref": "note:abc123def456",
        "etag_value": '"raw-etag-secret"',
        "etag_hash": "123456abcdef",
        "markdown_char_count": 42,
        "reason_code": "folder_note_list_ok",
        "created_at": "2026-06-18T10:00:00Z",
        "updated_at": "2026-06-18T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


def _folder(*, linked=True):
    return {
        "id": FOLDER_ID,
        "display_name": "Projet Tulu",
        "nextcloud_target_name": "Projet-Tulu",
        "nextcloud_sync_state": "linked" if linked else "local_only",
        "deleted_at": None,
    }


class WorkspaceFolderNotesTests(unittest.TestCase):
    def test_schema_creates_mandatory_notes_table_without_workspace_files_dependency(self) -> None:
        cur = _FakeCursor()

        workspace_folder_notes_store.ensure_schema(cur)

        sql = "\n".join(cur.queries).lower()
        self.assertIn("create table if not exists workspace_folder_notes", sql)
        self.assertIn("workspace_folder_id uuid", sql)
        self.assertIn("references workspace_folders(id) on delete cascade", sql)
        self.assertIn("workspace_folder_notes_folder_title_active_idx", sql)
        self.assertIn("workspace_folder_notes_state_idx", sql)
        self.assertIn("etag_value", sql)
        self.assertNotIn("markdown_body", sql)
        self.assertNotIn("body text", sql)
        self.assertNotIn("references workspace_files", sql)

    def test_user_projection_keeps_title_and_technical_projection_redacts_sensitive_values(self) -> None:
        item = workspace_folder_notes.apply_note_projection(
            {
                **_note(),
                "markdown_body": "# contenu a ne jamais exposer",
                "body": "autre contenu",
                "url": "https://example.test/remote.php/dav/files/secret",
            }
        )

        user = item["note_v1_user"]
        technical = item["note_v1_technical"]
        self.assertEqual(user["title"], "Carnet sensible")
        self.assertEqual(user["note_id"], NOTE_ID)
        self.assertEqual(technical["title_hash"], "abc123def456")
        self.assertEqual(technical["etag_hash"], "123456abcdef")
        self.assertTrue(technical["etag_present"])
        technical_text = str(technical)
        self.assertNotIn("Carnet sensible", technical_text)
        self.assertNotIn("raw-etag-secret", technical_text)
        self.assertNotIn("contenu", technical_text)
        self.assertNotIn("remote.php", technical_text)
        self.assertNotIn("etag_value", technical_text)
        self.assertNotIn("target_name", technical_text)
        self.assertNotIn("markdown_body", item)
        self.assertNotIn("body", item)
        self.assertNotIn("url", item)

    def test_invalid_ids_are_redacted_in_technical_refs(self) -> None:
        technical = workspace_folder_notes.build_technical_projection(
            _note(id="SecretNoteName", workspace_folder_id="ProjetTulu")
        )

        self.assertNotIn("SecretNoteName", str(technical))
        self.assertNotIn("ProjetTulu", str(technical))
        self.assertTrue(technical["note_ref"].startswith("workspace-note:redacted:"))
        self.assertTrue(technical["folder_ref"].startswith("workspace-folder:redacted:"))

    def test_title_validation_detects_local_sanitized_conflict(self) -> None:
        result = workspace_folder_notes.validate_note_title(
            "Plan",
            existing_notes=[
                {
                    "id": NOTE_ID,
                    "title": "Plan",
                    "target_name": "Plan.md",
                    "title_hash": workspace_folder_notes.title_hash_for_target("Plan.md"),
                    "local_state": "available",
                    "deleted_at": None,
                }
            ],
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_note_name_conflict")

    def test_tombstone_notes_are_excluded_from_active_projection_list(self) -> None:
        active = _note(id=NOTE_ID, title="Active", target_name="Active.md")
        deleted = _note(
            id="22222222-3333-4444-8555-666666666666",
            title="Deleted",
            target_name="Deleted.md",
            local_state="deleted",
            deleted_at="2026-06-18T10:10:00Z",
        )

        items = workspace_folder_notes.apply_note_list([active, deleted])

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["note_v1_user"]["title"], "Active")

    def test_non_linked_folder_marks_note_unavailable_for_future_writes(self) -> None:
        user = workspace_folder_notes.build_user_projection(
            _note(),
            folder={"id": FOLDER_ID, "nextcloud_sync_state": "local_only", "deleted_at": None},
        )
        technical = workspace_folder_notes.build_technical_projection(
            _note(),
            folder={"id": FOLDER_ID, "nextcloud_sync_state": "local_only", "deleted_at": None},
        )

        self.assertEqual(user["status"], "unavailable")
        self.assertEqual(user["reason_code"], "folder_note_folder_not_linked")
        self.assertEqual(technical["status"], "unavailable")
        self.assertEqual(technical["reason_code"], "folder_note_folder_not_linked")

    def test_store_serialization_keeps_etag_internal_but_projection_hides_it(self) -> None:
        row = workspace_folder_notes_store.serialize_note_row(_note())

        self.assertIsNotNone(row)
        self.assertEqual(row["etag_value"], '"raw-etag-secret"')
        projected = workspace_folder_notes.apply_note_projection(row)
        self.assertNotIn("etag_value", projected)
        self.assertNotIn("raw-etag-secret", str(projected["note_v1_technical"]))

    def test_list_notes_fail_closed_raises_content_free_lookup_error(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(workspace_folder_notes_store.WorkspaceFolderNoteLookupError) as ctx:
            workspace_folder_notes_store.list_notes(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(ctx.exception.reason_code, "folder_note_lookup_failed")
        self.assertEqual(ctx.exception.workspace_folder_id, FOLDER_ID)
        self.assertEqual(ctx.exception.note_id, "")
        self.assertNotIn("Carnet sensible", str(ctx.exception))
        self.assertNotIn("raw-etag-secret", str(ctx.exception))
        logged = str(logger.records)
        self.assertIn("folder_note_lookup_failed", logged)
        self.assertNotIn("Carnet sensible", logged)
        self.assertNotIn("raw-etag-secret", logged)

    def test_get_note_fail_closed_raises_content_free_lookup_error(self) -> None:
        logger = _FakeLogger()

        with self.assertRaises(workspace_folder_notes_store.WorkspaceFolderNoteLookupError) as ctx:
            workspace_folder_notes_store.get_note(
                NOTE_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=logger,
                fail_closed=True,
            )

        self.assertIsNone(ctx.exception.__cause__)
        self.assertEqual(ctx.exception.reason_code, "folder_note_lookup_failed")
        self.assertEqual(ctx.exception.note_id, NOTE_ID)
        self.assertEqual(ctx.exception.workspace_folder_id, "")
        self.assertIn("folder_note_lookup_failed", workspace_folder_notes.REASON_CODE_CATALOG)
        logged = str(logger.records)
        self.assertIn("folder_note_lookup_failed", logged)
        self.assertNotIn("Carnet sensible", logged)
        self.assertNotIn("raw-etag-secret", logged)

    def test_lookup_soft_compatibility_is_explicit(self) -> None:
        self.assertEqual(
            workspace_folder_notes_store.list_notes(
                FOLDER_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=None,
                fail_closed=False,
            ),
            [],
        )
        self.assertIsNone(
            workspace_folder_notes_store.get_note(
                NOTE_ID,
                db_conn_func=lambda: _FailingConnection(),
                logger=None,
                fail_closed=False,
            )
        )

    def test_create_note_nextcloud_first_stores_local_read_model_content_free(self) -> None:
        notes = _FakeNotesModule()
        nextcloud = _FakeNextcloudNotes()

        result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="Carnet sensible",
            markdown="# contenu initial",
            notes_module=notes,
            nextcloud=nextcloud,
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["reason_code"], "folder_note_create_ok")
        self.assertEqual(nextcloud.status_calls, ["Projet-Tulu"])
        self.assertEqual(nextcloud.put_calls[0][1], "Carnet-sensible.md")
        self.assertEqual(nextcloud.put_calls[0][2], b"# contenu initial")
        self.assertEqual(notes.stored[0]["target_name"], "Carnet-sensible.md")
        self.assertEqual(notes.stored[0]["etag_value"], '"etag-secret"')
        self.assertNotIn("markdown", notes.stored[0])
        projected = workspace_folder_notes.apply_note_projection(result["note"], folder=_folder(linked=True))
        self.assertEqual(projected["note_v1_user"]["title"], "Carnet sensible")
        technical_text = str(projected["note_v1_technical"])
        self.assertNotIn("Carnet sensible", technical_text)
        self.assertNotIn("contenu initial", str(result["note_nextcloud"]))
        self.assertNotIn("etag-secret", str(result["note_nextcloud"]))
        self.assertNotIn("Carnet-sensible.md", str(result["note_nextcloud"]))

    def test_create_note_refuses_non_linked_folder_before_nextcloud(self) -> None:
        nextcloud = _FakeNextcloudNotes()
        result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=False),
            title="Carnet",
            markdown="",
            notes_module=_FakeNotesModule(),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_note_folder_not_linked")
        self.assertEqual(nextcloud.status_calls, [])

    def test_create_note_refuses_missing_or_non_collection_notes_target(self) -> None:
        for reason in (
            workspace_folder_notes.REASON_NOTES_TARGET_MISSING,
            workspace_folder_notes.REASON_NOTES_TARGET_NOT_COLLECTION,
        ):
            result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
                folder=_folder(linked=True),
                title="Carnet",
                markdown="",
                notes_module=_FakeNotesModule(),
                nextcloud=_FakeNextcloudNotes(status_reason=reason),
            )
            self.assertFalse(result["ok"])
            self.assertEqual(result["reason_code"], reason)

    def test_create_note_refuses_invalid_title_and_local_sanitized_conflict(self) -> None:
        invalid = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="///",
            markdown="",
            notes_module=_FakeNotesModule(),
            nextcloud=_FakeNextcloudNotes(),
        )
        self.assertFalse(invalid["ok"])
        self.assertEqual(invalid["reason_code"], "folder_note_name_invalid")

        existing = _note(target_name="Plan.md", title_hash=workspace_folder_notes.title_hash_for_target("Plan.md"))
        conflict = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="Plan",
            markdown="",
            notes_module=_FakeNotesModule(existing=[existing]),
            nextcloud=_FakeNextcloudNotes(),
        )
        self.assertFalse(conflict["ok"])
        self.assertEqual(conflict["reason_code"], "folder_note_name_conflict")

    def test_create_note_refuses_remote_overwrite_like_conflict(self) -> None:
        notes = _FakeNotesModule()
        result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="Carnet",
            markdown="",
            notes_module=notes,
            nextcloud=_FakeNextcloudNotes(put_reason=workspace_folder_notes.REASON_NAME_CONFLICT),
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_note_name_conflict")
        self.assertEqual(notes.stored, [])

    def test_note_client_accepts_only_creation_status_for_put(self) -> None:
        ok = _StatusOnlyNoteClient(201).put_note("Projet", "Carnet.md", b"")
        self.assertTrue(ok.ok)
        self.assertEqual(ok.status_class, "2xx")

        for status in (200, 204):
            with self.assertRaises(workspace_folder_note_nextcloud_client.NextcloudNoteClientError) as ctx:
                _StatusOnlyNoteClient(status).put_note("Projet", "Carnet.md", b"")
            self.assertEqual(ctx.exception.reason_code, "folder_note_name_conflict")

    def test_create_note_rolls_back_remote_if_local_persistence_fails(self) -> None:
        nextcloud = _FakeNextcloudNotes()
        result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="Carnet sensible",
            markdown="secret local only",
            notes_module=_FakeNotesModule(fail_upsert=True),
            nextcloud=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "folder_note_local_persistence_failed")
        self.assertTrue(result["note_nextcloud"]["rollback"]["ok"])
        self.assertEqual(nextcloud.deleted[0], ("Projet-Tulu", "Carnet-sensible.md", True))
        self.assertNotIn("Carnet sensible", str(result["note_nextcloud"]))
        self.assertNotIn("secret local only", str(result["note_nextcloud"]))

    def test_create_note_reports_content_free_when_remote_rollback_fails(self) -> None:
        result = workspace_folder_note_nextcloud_runtime.create_workspace_note_nextcloud_first(
            folder=_folder(linked=True),
            title="Carnet sensible",
            markdown="secret local only",
            notes_module=_FakeNotesModule(fail_upsert=True),
            nextcloud=_FakeNextcloudNotes(
                delete_reason=workspace_folder_notes.REASON_REMOTE_COMPENSATION_FAILED
            ),
        )

        self.assertFalse(result["ok"])
        self.assertFalse(result["note_nextcloud"]["rollback"]["ok"])
        self.assertEqual(
            result["note_nextcloud"]["rollback"]["reason_code"],
            "folder_note_remote_compensation_failed",
        )
        self.assertNotIn("Carnet sensible", str(result["note_nextcloud"]))
        self.assertNotIn("secret local only", str(result["note_nextcloud"]))


if __name__ == "__main__":
    unittest.main()
