from __future__ import annotations

import unittest

from core import workspace_folder_notes
from core import workspace_folder_notes_store


NOTE_ID = "11111111-2222-4333-8444-555555555555"
FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"


class _FakeCursor:
    def __init__(self):
        self.queries = []

    def execute(self, sql, params=None):
        self.queries.append(" ".join(str(sql).split()))


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


if __name__ == "__main__":
    unittest.main()
