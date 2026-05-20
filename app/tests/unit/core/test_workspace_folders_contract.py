from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conversations_maintenance
from core import workspace_files_store
from core import workspace_folders_store


class _FakeCursor:
    def __init__(self, conn):
        self.conn = conn

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.conn.queries.append(" ".join(str(sql).split()))


class _FakeConn:
    def __init__(self):
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _FakeCursor(self)

    def commit(self):
        self.commits += 1


class WorkspaceFoldersContractTests(unittest.TestCase):
    def test_catalog_init_creates_workspace_table_and_nullable_conversation_relation(self) -> None:
        conn = _FakeConn()
        logger = type("Logger", (), {"info": lambda *_args, **_kwargs: None, "error": lambda *_args, **_kwargs: None})()

        conversations_maintenance.init_catalog_db(db_conn_func=lambda: conn, logger=logger)

        sql = "\n".join(conn.queries).lower()
        self.assertIn("create table if not exists workspace_folders", sql)
        self.assertIn("create table if not exists workspace_files", sql)
        self.assertIn("add column if not exists workspace_folder_id uuid", sql)
        self.assertIn("conversations_workspace_folder_id_fkey", sql)
        self.assertIn("on delete set null", sql)
        self.assertIn("workspace_folders_active_sort_idx", sql)
        self.assertIn("workspace_files_folder_active_idx", sql)
        self.assertIn("workspace_files_storage_key_idx", sql)
        self.assertEqual(conn.commits, 1)

    def test_folder_validation_keeps_allowlisted_icons_and_short_ui_metadata(self) -> None:
        self.assertEqual(workspace_folders_store.normalize_icon_key("folder"), "folder")
        self.assertEqual(workspace_folders_store.normalize_icon_key("spark"), "spark")
        self.assertIsNone(workspace_folders_store.normalize_icon_key("<svg>"))
        self.assertEqual(workspace_folders_store.sanitize_display_name("  Projet   A  "), "Projet A")
        self.assertLessEqual(
            len(workspace_folders_store.sanitize_display_name("x" * 120)),
            workspace_folders_store.DISPLAY_NAME_MAX_CHARS,
        )
        self.assertLessEqual(
            len(workspace_folders_store.sanitize_description("d" * 400)),
            workspace_folders_store.DESCRIPTION_MAX_CHARS,
        )

    def test_workspace_file_storage_key_uses_stable_ids_and_serializer_hides_internal_path(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".PDF")

        self.assertEqual(storage_key, f"{folder_id}/{file_id}.pdf")
        serialized = workspace_files_store.serialize_workspace_file_row(
            {
                "id": file_id,
                "workspace_folder_id": folder_id,
                "display_name": "  Scan   Tulu.pdf ",
                "original_filename": "../Scan Tulu.pdf",
                "storage_key": storage_key,
                "content_kind": "document",
                "media_kind": "text",
                "mime_type": "application/pdf",
                "source_extension": ".pdf",
                "byte_size": 12,
                "sha256": "full-hash-should-not-render",
                "sha256_12": "abc123",
                "status": "active",
                "reason_code": "",
            }
        )

        self.assertEqual(serialized["display_name"], "Scan Tulu.pdf")
        self.assertEqual(serialized["original_filename"], "Scan Tulu.pdf")
        self.assertNotIn("storage_key", serialized)
        self.assertNotIn("internal_path", serialized)
        self.assertNotIn("sha256", serialized)

    def test_workspace_file_bytes_are_written_under_folder_prefix_and_removed_physically(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        storage_key = workspace_files_store.storage_key_for(folder_id, file_id, ".txt")
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = workspace_files_store.write_file_bytes(root, storage_key, b"bonjour")

            self.assertTrue(path.exists())
            self.assertEqual(path.relative_to(root).parts[0], folder_id)
            self.assertEqual(path.read_bytes(), b"bonjour")
            self.assertTrue(workspace_files_store.delete_file_bytes(root, storage_key))
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
