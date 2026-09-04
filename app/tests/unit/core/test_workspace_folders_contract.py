from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import conversations_maintenance
from core import active_document_prompt_lane
from core import chat_service
from core import workspace_files_store
from core import workspace_folders_store
from core import workspace_folder_nextcloud_client
from core import workspace_folder_nextcloud_links_store
from core import workspace_folder_nextcloud_reconcile
from core import workspace_folder_nextcloud_runtime
from core import workspace_folder_standard_subfolders
from core import workspace_folders_service
from observability import active_documents_observability
from observability import workspace_folders_observability


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


class _CaptureLogger:
    def __init__(self):
        self.lines = []

    def info(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def warning(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))

    def error(self, msg, *args, **_kwargs):
        self.lines.append(msg % args if args else str(msg))


class _FakeNextcloudFolderClient:
    def __init__(self):
        self.created = []
        self.created_paths = []
        self.moved = []
        self.deleted = []
        self.statuses = {}
        self.path_statuses = {}
        self.collections = {}
        self.path_collections = {}
        self.status_checked = []
        self.path_status_checked = []
        self.fail_status = None
        self.fail_path_status = None
        self.fail_create = None
        self.fail_create_path = None
        self.fail_move = None
        self.fail_delete = None

    def folder_status(self, name):
        self.status_checked.append(name)
        if self.fail_status:
            raise self.fail_status
        status = int(self.statuses.get(name, 404))
        if status == 207:
            if self.collections.get(name, True) is not True:
                raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                    workspace_folder_nextcloud_client.REASON_CONFLICT,
                    http_status=status,
                )
            return workspace_folder_nextcloud_client.NextcloudFolderResponse(
                True,
                workspace_folder_nextcloud_reconcile.REASON_RECONCILE_EXISTING_OK,
                status,
            )
        reason = (
            workspace_folder_nextcloud_client.REASON_TARGET_MISSING
            if status == 404
            else workspace_folder_nextcloud_client.REASON_CONFLICT
            if status in {405, 409, 412, 423}
            else workspace_folder_nextcloud_client.REASON_UNAVAILABLE
        )
        raise workspace_folder_nextcloud_client.NextcloudFolderClientError(reason, http_status=status)

    def create_folder(self, name):
        self.created.append(name)
        if self.fail_create:
            raise self.fail_create
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_CREATE_OK,
            201,
        )

    def folder_status_path(self, *segments):
        self.path_status_checked.append(tuple(segments))
        if self.fail_path_status:
            raise self.fail_path_status
        status = int(self.path_statuses.get(tuple(segments), 404))
        if status == 207:
            if self.path_collections.get(tuple(segments), True) is not True:
                raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                    workspace_folder_nextcloud_client.REASON_CONFLICT,
                    http_status=status,
                )
            return workspace_folder_nextcloud_client.NextcloudFolderResponse(
                True,
                workspace_folder_nextcloud_client.REASON_STANDARD_SUBFOLDER_EXISTING_OK,
                status,
            )
        reason = (
            workspace_folder_nextcloud_client.REASON_TARGET_MISSING
            if status == 404
            else workspace_folder_nextcloud_client.REASON_CONFLICT
            if status in {405, 409, 412, 423}
            else workspace_folder_nextcloud_client.REASON_UNAVAILABLE
        )
        raise workspace_folder_nextcloud_client.NextcloudFolderClientError(reason, http_status=status)

    def create_folder_path(self, *segments):
        self.created_paths.append(tuple(segments))
        if self.fail_create_path:
            raise self.fail_create_path
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_STANDARD_SUBFOLDER_CREATED_OK,
            201,
        )

    def move_folder(self, old_name, new_name):
        self.moved.append((old_name, new_name))
        if self.fail_move:
            raise self.fail_move
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_RENAME_OK,
            201,
        )

    def delete_folder(self, name, *, missing_ok=True):
        self.deleted.append((name, missing_ok))
        if self.fail_delete:
            raise self.fail_delete
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_ROLLBACK_OK,
            204,
        )


class _FakeHTTPResponse:
    def __init__(self, status, body=b""):
        self.status = status
        self.body = body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *_args):
        return self.body


class _WorkspaceFilesCursor:
    def __init__(self, conn):
        self.conn = conn
        self.result = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        normalized_sql = " ".join(str(sql).split()).lower()
        params = tuple(params or ())
        self.conn.queries.append(normalized_sql)
        if "select id::text from workspace_files" in normalized_sql:
            folder_id = params[0]
            self.result = [
                (row["id"],)
                for row in self.conn.rows.values()
                if row["workspace_folder_id"] == folder_id and row.get("deleted_at") is None
            ]
            return
        if "select id, workspace_folder_id, storage_key from workspace_files" in normalized_sql:
            file_id, folder_id = params
            row = self.conn.rows.get(file_id)
            if row and row["workspace_folder_id"] == folder_id and row.get("deleted_at") is None:
                self.result = {
                    "id": row["id"],
                    "workspace_folder_id": row["workspace_folder_id"],
                    "storage_key": row["storage_key"],
                }
            else:
                self.result = None
            return
        if "update workspace_files" in normalized_sql:
            status, reason_code, file_id, folder_id = params
            row = self.conn.rows.get(file_id)
            if row and row["workspace_folder_id"] == folder_id:
                row["status"] = status
                row["reason_code"] = reason_code
                row["deleted_at"] = "2026-05-20T00:04:00Z"
                row["updated_at"] = "2026-05-20T00:04:00Z"
                self.result = dict(row)
            else:
                self.result = None
            return
        if "update workspace_file_selections" in normalized_sql:
            self.result = None
            return
        raise AssertionError(f"unexpected SQL: {normalized_sql}")

    def fetchall(self):
        return list(self.result or [])

    def fetchone(self):
        return self.result


class _WorkspaceFilesConn:
    def __init__(self, rows):
        self.rows = rows
        self.queries = []
        self.commits = 0

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _WorkspaceFilesCursor(self)

    def commit(self):
        self.commits += 1


def _workspace_file_row(folder_id, file_id, storage_key):
    return {
        "id": file_id,
        "workspace_folder_id": folder_id,
        "display_name": "note.txt",
        "original_filename": "note.txt",
        "storage_key": storage_key,
        "content_kind": "document",
        "media_kind": "text",
        "mime_type": "text/plain",
        "source_extension": ".txt",
        "byte_size": 7,
        "sha256": "full-hash-hidden",
        "sha256_12": "abc123def456",
        "text_chars": 7,
        "text_sha256_12": "text12345678",
        "image_width": 0,
        "image_height": 0,
        "status": "active",
        "reason_code": "",
        "source_kind": "upload",
        "source_file_id": None,
        "created_at": "2026-05-20T00:00:00Z",
        "updated_at": "2026-05-20T00:00:00Z",
        "deleted_at": None,
    }


PROPFIND_COLLECTION_XML = (
    b'<multistatus xmlns="DAV:"><response><propstat><prop>'
    b"<resourcetype><collection /></resourcetype>"
    b"</prop></propstat></response></multistatus>"
)
PROPFIND_FILE_XML = (
    b'<multistatus xmlns="DAV:"><response><propstat><prop>'
    b"<resourcetype />"
    b"</prop></propstat></response></multistatus>"
)


class WorkspaceFoldersContractTests(unittest.TestCase):
    def test_catalog_init_creates_workspace_table_and_nullable_conversation_relation(self) -> None:
        conn = _FakeConn()
        logger = type("Logger", (), {"info": lambda *_args, **_kwargs: None, "error": lambda *_args, **_kwargs: None})()

        conversations_maintenance.init_catalog_db(db_conn_func=lambda: conn, logger=logger)

        sql = "\n".join(conn.queries).lower()
        self.assertIn("create table if not exists workspace_folders", sql)
        self.assertIn("create table if not exists workspace_folder_nextcloud_links", sql)
        self.assertIn("create table if not exists workspace_files", sql)
        self.assertIn("create table if not exists workspace_file_selections", sql)
        self.assertIn("create table if not exists workspace_folder_notes", sql)
        self.assertIn("add column if not exists workspace_folder_id uuid", sql)
        self.assertIn("conversations_workspace_folder_id_fkey", sql)
        self.assertIn("on delete set null", sql)
        self.assertIn("workspace_folders_active_sort_idx", sql)
        self.assertIn("workspace_folder_nextcloud_links_sync_state_idx", sql)
        self.assertIn("workspace_folder_notes_folder_active_idx", sql)
        self.assertIn("workspace_files_folder_active_idx", sql)
        self.assertIn("workspace_files_storage_key_idx", sql)
        self.assertIn("workspace_file_selections_conversation_active_idx", sql)
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

    def test_folder_nextcloud_fake_mapping_is_derived_content_free(self) -> None:
        row = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "  Projet   Tulu ",
                "icon_key": "spark",
                "description": "UI only",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
            }
        )

        self.assertEqual(row["display_name"], "Projet Tulu")
        self.assertEqual(row["local_status"], "active")
        self.assertEqual(row["nextcloud_logical_root"], "/Frida")
        self.assertEqual(row["nextcloud_target_name"], "Projet-Tulu")
        self.assertEqual(row["nextcloud_logical_path"], "/Frida/Projet-Tulu")
        self.assertEqual(row["nextcloud_sync_state"], "local_only")
        self.assertEqual(row["nextcloud_share_state"], "expected")
        self.assertEqual(row["nextcloud_reason_code"], "workspace_folder_sync_local_only")
        self.assertEqual(row["nextcloud_folder_ref"], row["nextcloud_directory_ref"])
        self.assertFalse(row["nextcloud_live_checked"])
        encoded = str(row)
        self.assertNotIn("http", encoded.lower())
        self.assertNotIn("dav", encoded.lower())
        self.assertNotIn("storage_key", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_folder_nextcloud_persisted_link_overrides_fake_projection_content_free(self) -> None:
        row = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "Projet Tulu",
                "icon_key": "spark",
                "description": "UI only",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": "11111111-2222-4333-8444-555555555555",
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_at": "2026-06-16T00:03:00Z",
                "link_last_sync_reason_code": "workspace_folder_sync_linked",
                "link_last_sync_operation": "observe",
                "link_nextcloud_share_state": "confirmed",
                "link_created_at": "2026-06-16T00:02:00Z",
                "link_updated_at": "2026-06-16T00:03:00Z",
            }
        )

        self.assertEqual(row["nextcloud_sync_state"], "linked")
        self.assertEqual(row["nextcloud_share_state"], "confirmed")
        self.assertEqual(row["nextcloud_reason_code"], "workspace_folder_sync_linked")
        self.assertEqual(row["nextcloud_folder_ref"], "workspace-folder:11111111:abc123def456")
        self.assertEqual(row["nextcloud_name_hash"], "abc123def456")
        self.assertEqual(row["last_sync_at"], "2026-06-16T00:03:00Z")
        self.assertEqual(row["last_sync_operation"], "observe")
        self.assertTrue(row["nextcloud_live_checked"])
        encoded = str(row)
        self.assertNotIn("http", encoded.lower())
        self.assertNotIn("remote.php", encoded)
        self.assertNotIn("storage_key", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_workspace_folder_update_refetches_persisted_nextcloud_link(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        base_row = {
            "id": folder_id,
            "display_name": "Projet Renomme",
            "icon_key": "spark",
            "description": "UI only",
            "sort_order": 1000,
            "created_at": "2026-06-16T00:00:00Z",
            "updated_at": "2026-06-16T00:04:00Z",
            "deleted_at": None,
        }
        linked_payload = workspace_folders_store.serialize_workspace_folder_row(
            {
                **base_row,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_at": "2026-06-16T00:03:00Z",
                "link_last_sync_reason_code": "workspace_folder_sync_linked",
                "link_last_sync_operation": "observe",
                "link_nextcloud_share_state": "confirmed",
            }
        )

        class _UpdateCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, _sql, _params=None):
                return None

            def fetchone(self):
                return dict(base_row)

        class _UpdateConn:
            def __init__(self):
                self.commits = 0

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return _UpdateCursor()

            def commit(self):
                self.commits += 1

        conn = _UpdateConn()
        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(
                workspace_folders_store,
                "get_workspace_folder",
                return_value=linked_payload,
            ) as refetch:
                result = workspace_folders_store.update_workspace_folder(
                    folder_id,
                    display_name="Projet Renomme",
                    db_conn_func=lambda: conn,
                    logger=_CaptureLogger(),
                )

        self.assertEqual(result["nextcloud_sync_state"], "linked")
        self.assertEqual(result["nextcloud_share_state"], "confirmed")
        self.assertEqual(result["nextcloud_reason_code"], "workspace_folder_sync_linked")
        refetch.assert_called_once_with(folder_id, db_conn_func=mock.ANY, logger=mock.ANY)
        self.assertEqual(conn.commits, 1)

    def test_workspace_folder_nextcloud_link_upsert_fail_closed_on_persistence_error(self) -> None:
        logger = _CaptureLogger()

        def _failing_conn():
            raise RuntimeError("Projet Tulu should not leak")

        with self.assertRaises(
            workspace_folder_nextcloud_links_store.WorkspaceFolderNextcloudLinkPersistenceError
        ) as raised:
            workspace_folder_nextcloud_links_store.upsert_link(
                workspace_folder_id="11111111-2222-4333-8444-555555555555",
                nextcloud_sync_state="linked",
                nextcloud_folder_ref="workspace-folder:11111111:abc123def456",
                nextcloud_name_hash="abc123def456",
                last_sync_reason_code="workspace_folder_sync_linked",
                last_sync_operation="create",
                nextcloud_share_state="confirmed",
                db_conn_func=_failing_conn,
                logger=logger,
            )

        encoded_logs = "\n".join(logger.lines)
        self.assertEqual(str(raised.exception), "workspace_folder_nextcloud_error_redacted")
        self.assertIsNone(raised.exception.__cause__)
        self.assertTrue(raised.exception.__suppress_context__)
        self.assertIn("workspace_folder_nextcloud_error_redacted", encoded_logs)
        self.assertNotIn("Projet Tulu", encoded_logs)
        self.assertNotIn("should not leak", encoded_logs)

    def test_workspace_folder_update_fails_closed_when_refetch_fails(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        base_row = {
            "id": folder_id,
            "display_name": "Projet Renomme",
            "icon_key": "spark",
            "description": "UI only",
            "sort_order": 1000,
            "created_at": "2026-06-16T00:00:00Z",
            "updated_at": "2026-06-16T00:04:00Z",
            "deleted_at": None,
        }

        class _UpdateCursor:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def execute(self, _sql, _params=None):
                return None

            def fetchone(self):
                return dict(base_row)

        class _UpdateConn:
            def __init__(self):
                self.commits = 0

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, tb):
                return False

            def cursor(self, *args, **kwargs):
                return _UpdateCursor()

            def commit(self):
                self.commits += 1

        logger = _CaptureLogger()
        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(workspace_folders_store, "get_workspace_folder", return_value=None):
                result = workspace_folders_store.update_workspace_folder(
                    folder_id,
                    display_name="Projet Renomme",
                    db_conn_func=lambda: _UpdateConn(),
                    logger=logger,
                )

        self.assertIsNone(result)
        encoded_logs = "\n".join(logger.lines)
        self.assertIn("workspace_folder_update_refetch_failed", encoded_logs)
        self.assertIn("workspace_folder_nextcloud_error_redacted", encoded_logs)
        self.assertNotIn("local_only", encoded_logs)

    def test_nextcloud_first_create_persists_linked_state_after_mkcol(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        target_hash = workspace_folders_store.nextcloud_projection.hash12("projet-live".casefold())
        linked_folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": f"workspace-folder:11111111:{target_hash}",
                "link_nextcloud_name_hash": target_hash,
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(
                workspace_folders_store,
                "create_workspace_folder",
                return_value={"id": folder_id},
            ) as local_create:
                with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link") as upsert:
                    with mock.patch.object(workspace_folders_store, "get_workspace_folder", return_value=linked_folder):
                        result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                            display_name="Projet Live",
                            icon_key="folder",
                            description="",
                            sort_order=None,
                            folder_id=folder_id,
                            db_conn_func=lambda: None,
                            logger=_CaptureLogger(),
                            client=fake_client,
                        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["folder"]["nextcloud_sync_state"], "linked")
        self.assertEqual(result["folder"]["nextcloud_reason_code"], "workspace_folder_nextcloud_create_ok")
        self.assertEqual(fake_client.created, ["Projet-Live"])
        self.assertEqual(
            fake_client.created_paths,
            [
                ("Projet-Live", "Documents"),
                ("Projet-Live", "Notes"),
                ("Projet-Live", "Exports"),
                ("Projet-Live", "Images"),
            ],
        )
        self.assertEqual(fake_client.deleted, [])
        local_create.assert_called_once()
        upsert.assert_called_once()

    def test_nextcloud_folder_status_accepts_propfind_collection(self) -> None:
        client = workspace_folder_nextcloud_client.NextcloudFolderClient(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )

        with mock.patch.object(
            workspace_folder_nextcloud_client,
            "urlopen",
            return_value=_FakeHTTPResponse(207, PROPFIND_COLLECTION_XML),
        ):
            response = client.folder_status("Projet-Live")

        self.assertTrue(response.ok)
        self.assertEqual(response.http_status, 207)

    def test_nextcloud_folder_status_rejects_propfind_non_collection(self) -> None:
        client = workspace_folder_nextcloud_client.NextcloudFolderClient(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )

        with mock.patch.object(
            workspace_folder_nextcloud_client,
            "urlopen",
            return_value=_FakeHTTPResponse(207, PROPFIND_FILE_XML),
        ):
            with self.assertRaises(workspace_folder_nextcloud_client.NextcloudFolderClientError) as caught:
                client.folder_status("Projet-Live")

        self.assertEqual(caught.exception.reason_code, workspace_folder_nextcloud_client.REASON_CONFLICT)
        encoded = str(caught.exception)
        self.assertNotIn("Projet-Live", encoded)
        self.assertNotIn("remote.php", encoded)
        self.assertNotIn("DAV:", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_folder_status_path_accepts_propfind_collection(self) -> None:
        client = workspace_folder_nextcloud_client.NextcloudFolderClient(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )

        with mock.patch.object(
            workspace_folder_nextcloud_client,
            "urlopen",
            return_value=_FakeHTTPResponse(207, PROPFIND_COLLECTION_XML),
        ):
            response = client.folder_status_path("Projet-Live", "Documents")

        self.assertTrue(response.ok)
        self.assertEqual(response.http_status, 207)

    def test_nextcloud_folder_status_path_rejects_propfind_non_collection(self) -> None:
        client = workspace_folder_nextcloud_client.NextcloudFolderClient(
            workspace_folder_nextcloud_client.NextcloudFolderClientConfig(
                base_url="http://nextcloud.invalid",
                username="frida",
                app_password="redacted",
            )
        )

        with mock.patch.object(
            workspace_folder_nextcloud_client,
            "urlopen",
            return_value=_FakeHTTPResponse(207, PROPFIND_FILE_XML),
        ):
            with self.assertRaises(workspace_folder_nextcloud_client.NextcloudFolderClientError) as caught:
                client.folder_status_path("Projet-Live", "Documents")

        self.assertEqual(caught.exception.reason_code, workspace_folder_nextcloud_client.REASON_CONFLICT)
        encoded = str(caught.exception)
        self.assertNotIn("Projet-Live", encoded)
        self.assertNotIn("Documents/", encoded)
        self.assertNotIn("remote.php", encoded)
        self.assertNotIn("DAV:", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_standard_subfolders_accept_existing_and_create_missing_content_free(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        fake_client.path_statuses[("Projet-Live", "Documents")] = 207
        result = workspace_folder_standard_subfolders.ensure_standard_subfolders(
            nextcloud=fake_client,
            parent_name="Projet-Live",
            folder_ref="workspace-folder:11111111:abc123def456",
            nextcloud_name_hash="abc123def456",
        )

        self.assertTrue(result["ok"])
        self.assertEqual(result["counts"]["inspected"], 4)
        self.assertEqual(result["counts"]["existing"], 1)
        self.assertEqual(result["counts"]["created"], 3)
        self.assertEqual(
            fake_client.created_paths,
            [
                ("Projet-Live", "Notes"),
                ("Projet-Live", "Exports"),
                ("Projet-Live", "Images"),
            ],
        )
        encoded = str(result)
        self.assertNotIn("Projet Live", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("Authorization", encoded)
        self.assertIn("Documents", encoded)

    def test_standard_subfolders_reject_non_collection_existing_target(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        fake_client.path_statuses[("Projet-Live", "Documents")] = 207
        fake_client.path_collections[("Projet-Live", "Documents")] = False
        result = workspace_folder_standard_subfolders.ensure_standard_subfolders(
            nextcloud=fake_client,
            parent_name="Projet-Live",
            folder_ref="workspace-folder:11111111:abc123def456",
            nextcloud_name_hash="abc123def456",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_standard_subfolder_conflict")
        self.assertEqual(result["counts"]["existing"], 0)
        self.assertEqual(result["counts"]["failed"], 1)
        self.assertNotIn(
            "LOT11_STANDARD_SUBFOLDER_EXISTING",
            [record["case_id"] for record in result["records"] if record.get("standard_subfolder") == "Documents"],
        )
        encoded = str(result)
        self.assertNotIn("Projet-Live", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("remote.php", encoded)
        self.assertNotIn("DAV:", encoded)
        self.assertNotIn("Authorization", encoded)
        self.assertNotIn("Basic", encoded)

    def test_standard_subfolders_conflict_is_content_free_failure(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        fake_client.path_statuses[("Projet-Live", "Documents")] = 409
        result = workspace_folder_standard_subfolders.ensure_standard_subfolders(
            nextcloud=fake_client,
            parent_name="Projet-Live",
            folder_ref="workspace-folder:11111111:abc123def456",
            nextcloud_name_hash="abc123def456",
        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_standard_subfolder_conflict")
        self.assertEqual(result["counts"]["failed"], 1)
        encoded = str(result)
        self.assertNotIn("Projet Live", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_first_create_retains_mkcol_when_local_persistence_fails(self) -> None:
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(workspace_folders_store, "create_workspace_folder", return_value=None):
                result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                    display_name="Projet Rollback",
                    icon_key="folder",
                    description="",
                    sort_order=None,
                    folder_id="11111111-2222-4333-8444-555555555555",
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
        self.assertEqual(
            result["rollback_reason_code"],
            "workspace_folder_nextcloud_rollback_ownership_unverified",
        )
        self.assertEqual(fake_client.created, ["Projet-Rollback"])
        self.assertEqual(len(fake_client.created_paths), 4)
        self.assertEqual(fake_client.deleted, [])

    def test_nextcloud_first_create_retains_parent_when_standard_subfolder_fails(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        fake_client.path_statuses[("Projet-Standards", "Documents")] = 409

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(workspace_folders_store, "create_workspace_folder") as local_create:
                result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                    display_name="Projet Standards",
                    icon_key="folder",
                    description="",
                    sort_order=None,
                    folder_id="11111111-2222-4333-8444-555555555555",
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_standard_subfolder_conflict")
        self.assertEqual(
            result["rollback_reason_code"],
            "workspace_folder_nextcloud_rollback_ownership_unverified",
        )
        self.assertEqual(fake_client.created, ["Projet-Standards"])
        self.assertEqual(fake_client.deleted, [])
        local_create.assert_not_called()

    def test_nextcloud_first_create_returns_redacted_error_when_client_unavailable(self) -> None:
        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(
                workspace_folder_nextcloud_client.NextcloudFolderClient,
                "from_env",
                side_effect=workspace_folder_nextcloud_client.NextcloudFolderClientError(
                    workspace_folder_nextcloud_client.REASON_UNAVAILABLE,
                ),
            ):
                result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                    display_name="Projet Secret",
                    icon_key="folder",
                    description="",
                    sort_order=None,
                    folder_id="11111111-2222-4333-8444-555555555555",
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=None,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 502)
        self.assertEqual(result["reason_code"], "workspace_folder_nextcloud_unavailable")
        self.assertEqual(result["nextcloud_reason_code"], "workspace_folder_nextcloud_unavailable")
        encoded = str(result)
        self.assertNotIn("/run/secrets", encoded)
        self.assertNotIn("app_password", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_first_create_reports_local_compensation_failure_after_link_failure(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        folder_id = "11111111-2222-4333-8444-555555555555"
        link_error = workspace_folder_nextcloud_links_store.WorkspaceFolderNextcloudLinkPersistenceError(
            "workspace_folder_nextcloud_error_redacted"
        )

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(workspace_folders_store, "create_workspace_folder", return_value={"id": folder_id}):
                with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link", side_effect=link_error):
                    with mock.patch.object(workspace_folders_store, "soft_delete_workspace_folder", return_value=None):
                        result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                            display_name="Projet Divergent",
                            icon_key="folder",
                            description="",
                            sort_order=None,
                            folder_id=folder_id,
                            db_conn_func=lambda: None,
                            logger=_CaptureLogger(),
                            client=fake_client,
                        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
        self.assertEqual(
            result["rollback_reason_code"],
            "workspace_folder_nextcloud_rollback_ownership_unverified",
        )
        self.assertEqual(result["local_compensation_status"], "failed")
        self.assertEqual(result["local_compensation_reason_code"], "workspace_folder_local_compensation_failed")
        self.assertEqual(fake_client.created, ["Projet-Divergent"])
        self.assertEqual(fake_client.deleted, [])
        encoded = str(result)
        self.assertNotIn("Projet Divergent", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_first_create_reports_clean_compensation_after_link_failure(self) -> None:
        fake_client = _FakeNextcloudFolderClient()
        folder_id = "11111111-2222-4333-8444-555555555555"
        link_error = workspace_folder_nextcloud_links_store.WorkspaceFolderNextcloudLinkPersistenceError(
            "workspace_folder_nextcloud_error_redacted"
        )

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            with mock.patch.object(workspace_folders_store, "create_workspace_folder", return_value={"id": folder_id}):
                with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link", side_effect=link_error):
                    with mock.patch.object(
                        workspace_folders_store,
                        "soft_delete_workspace_folder",
                        return_value={"id": folder_id, "deleted_at": "2026-06-16T00:00:00Z"},
                    ):
                        result = workspace_folder_nextcloud_runtime.create_workspace_folder_nextcloud_first(
                            display_name="Projet Compense",
                            icon_key="folder",
                            description="",
                            sort_order=None,
                            folder_id=folder_id,
                            db_conn_func=lambda: None,
                            logger=_CaptureLogger(),
                            client=fake_client,
                        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
        self.assertEqual(
            result["rollback_reason_code"],
            "workspace_folder_nextcloud_rollback_ownership_unverified",
        )
        self.assertEqual(result["local_compensation_status"], "done")
        self.assertNotIn("local_compensation_reason_code", result)
        self.assertEqual(fake_client.created, ["Projet-Compense"])
        self.assertEqual(fake_client.deleted, [])

    def test_nextcloud_first_rename_moves_then_updates_local_linked_folder(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        existing_folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )
        renamed_folder = dict(existing_folder)
        renamed_folder["display_name"] = "Projet Renomme"
        renamed_folder["nextcloud_reason_code"] = "workspace_folder_nextcloud_rename_ok"
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(workspace_folders_store, "get_workspace_folder", return_value=existing_folder):
            with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[existing_folder]):
                with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link") as upsert:
                    with mock.patch.object(workspace_folders_store, "update_workspace_folder", return_value=renamed_folder):
                        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
                            folder_id,
                            display_name="Projet Renomme",
                            db_conn_func=lambda: None,
                            logger=_CaptureLogger(),
                            client=fake_client,
                        )

        self.assertTrue(result["ok"])
        self.assertEqual(fake_client.moved, [("Projet-Live", "Projet-Renomme")])
        self.assertEqual(result["folder"]["display_name"], "Projet Renomme")
        upsert.assert_called_once()

    def test_nextcloud_first_rename_rolls_back_move_when_local_update_fails(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        existing_folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(workspace_folders_store, "get_workspace_folder", return_value=existing_folder):
            with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[existing_folder]):
                with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link"):
                    with mock.patch.object(workspace_folders_store, "update_workspace_folder", return_value=None):
                        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
                            folder_id,
                            display_name="Projet Renomme",
                            db_conn_func=lambda: None,
                            logger=_CaptureLogger(),
                            client=fake_client,
                        )

        self.assertFalse(result["ok"])
        self.assertEqual(result["reason_code"], "workspace_folder_local_persistence_failed")
        self.assertEqual(result["rollback_reason_code"], "workspace_folder_nextcloud_rollback_ok")
        self.assertEqual(
            fake_client.moved,
            [("Projet-Live", "Projet-Renomme"), ("Projet-Renomme", "Projet-Live")],
        )

    def test_nextcloud_first_rename_returns_redacted_error_when_client_unavailable(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        existing_folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )

        with mock.patch.object(workspace_folders_store, "get_workspace_folder", return_value=existing_folder):
            with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[existing_folder]):
                with mock.patch.object(
                    workspace_folder_nextcloud_client.NextcloudFolderClient,
                    "from_env",
                    side_effect=workspace_folder_nextcloud_client.NextcloudFolderClientError(
                        workspace_folder_nextcloud_client.REASON_UNAVAILABLE,
                    ),
                ):
                    result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
                        folder_id,
                        display_name="Projet Renomme",
                        db_conn_func=lambda: None,
                        logger=_CaptureLogger(),
                        client=None,
                    )

        self.assertFalse(result["ok"])
        self.assertEqual(result["status"], 502)
        self.assertEqual(result["reason_code"], "workspace_folder_nextcloud_unavailable")
        self.assertEqual(result["last_sync_operation"], "rename")
        encoded = str(result)
        self.assertNotIn("/run/secrets", encoded)
        self.assertNotIn("app_password", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_workspace_folder_service_uses_live_create_and_rename_when_available(self) -> None:
        class _LiveWorkspaceModule:
            WORKSPACE_FOLDER_ICON_KEYS = ("folder",)

            def normalize_icon_key(self, value):
                return "folder" if str(value or "folder") == "folder" else None

            def coerce_sort_order(self, value):
                return None if value in (None, "") else int(value)

            def sanitize_description(self, value):
                return str(value or "").strip()

            def sanitize_display_name(self, value):
                return str(value or "").strip()

            def normalize_workspace_folder_id(self, value):
                return workspace_folders_store.normalize_workspace_folder_id(value)

            def validate_workspace_folder_display_name(self, value, *, current_folder_id=None):
                return {
                    "ok": True,
                    "display_name": str(value).strip(),
                    "reason_code": "",
                }

            def create_workspace_folder_nextcloud_first(self, **kwargs):
                return {
                    "ok": True,
                    "reason_code": "workspace_folder_nextcloud_create_ok",
                    "folder": {
                        "id": "11111111-2222-4333-8444-555555555555",
                        "display_name": kwargs["display_name"],
                        "nextcloud_sync_state": "linked",
                        "nextcloud_share_state": "expected",
                        "nextcloud_reason_code": "workspace_folder_nextcloud_create_ok",
                    },
                }

            def rename_workspace_folder_nextcloud_first(self, folder_id, **kwargs):
                return {
                    "ok": True,
                    "reason_code": "workspace_folder_nextcloud_rename_ok",
                    "folder": {
                        "id": folder_id,
                        "display_name": kwargs["display_name"],
                        "nextcloud_sync_state": "linked",
                        "nextcloud_share_state": "expected",
                        "nextcloud_reason_code": "workspace_folder_nextcloud_rename_ok",
                    },
                }

        module = _LiveWorkspaceModule()
        created, create_status = workspace_folders_service.create_workspace_folder(
            {"display_name": "Projet Live", "icon_key": "folder"},
            workspace_folders_module=module,
        )
        renamed, rename_status = workspace_folders_service.patch_workspace_folder(
            "11111111-2222-4333-8444-555555555555",
            {"display_name": "Projet Renomme"},
            workspace_folders_module=module,
        )

        self.assertEqual(create_status, 201)
        self.assertEqual(created["reason_code"], "workspace_folder_nextcloud_create_ok")
        self.assertEqual(created["folder"]["nextcloud_sync_state"], "linked")
        self.assertEqual(rename_status, 200)
        self.assertEqual(renamed["reason_code"], "workspace_folder_nextcloud_rename_ok")
        self.assertEqual(renamed["folder"]["display_name"], "Projet Renomme")

    def test_nextcloud_reconcile_links_existing_target_content_free(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
            }
        )
        linked = dict(folder)
        linked["nextcloud_sync_state"] = "linked"
        fake_client = _FakeNextcloudFolderClient()
        fake_client.statuses["Projet-Live"] = 207

        with mock.patch.object(
            workspace_folders_store,
            "list_workspace_folders",
            side_effect=[[folder], [linked]],
        ):
            with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link") as upsert:
                result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(fake_client.status_checked, ["Projet-Live"])
        self.assertEqual(fake_client.created, [])
        self.assertEqual(fake_client.deleted, [])
        upsert.assert_called_once()
        self.assertEqual(upsert.call_args.kwargs["nextcloud_sync_state"], "linked")
        self.assertEqual(upsert.call_args.kwargs["last_sync_operation"], "reconcile")
        self.assertEqual(
            upsert.call_args.kwargs["last_sync_reason_code"],
            "workspace_folder_nextcloud_reconcile_existing_ok",
        )
        encoded = str(result)
        self.assertIn("LOT9_LINK_EXISTING_TARGET", encoded)
        self.assertNotIn("Projet Live", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_reconcile_linked_folder_creates_standard_subfolders(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Live",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )
        fake_client = _FakeNextcloudFolderClient()
        fake_client.statuses["Projet-Live"] = 207

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", side_effect=[[folder], [folder]]):
            result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                db_conn_func=lambda: None,
                logger=_CaptureLogger(),
                client=fake_client,
            )

        self.assertTrue(result["ok"])
        self.assertEqual(fake_client.status_checked, ["Projet-Live"])
        self.assertEqual(
            fake_client.path_status_checked,
            [
                ("Projet-Live", "Documents"),
                ("Projet-Live", "Notes"),
                ("Projet-Live", "Exports"),
                ("Projet-Live", "Images"),
            ],
        )
        self.assertEqual(len(fake_client.created_paths), 4)
        encoded = str(result)
        self.assertIn("LOT11_STANDARD_SUBFOLDER_CREATED", encoded)
        self.assertNotIn("Projet Live", encoded)
        self.assertNotIn("/Frida", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_nextcloud_reconcile_creates_missing_target_and_links(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Missing",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
            }
        )
        linked = dict(folder)
        linked["nextcloud_sync_state"] = "linked"
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(
            workspace_folders_store,
            "list_workspace_folders",
            side_effect=[[folder], [linked]],
        ):
            with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link") as upsert:
                result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertTrue(result["ok"])
        self.assertEqual(fake_client.status_checked, ["Projet-Missing"])
        self.assertEqual(fake_client.created, ["Projet-Missing"])
        self.assertEqual(fake_client.deleted, [])
        upsert.assert_called_once()
        self.assertEqual(
            upsert.call_args.kwargs["last_sync_reason_code"],
            "workspace_folder_nextcloud_reconcile_created_ok",
        )
        self.assertIn("LOT9_CREATE_MISSING_TARGET", str(result))

    def test_nextcloud_reconcile_retains_created_target_when_link_fails(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Rollback",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
            }
        )
        fake_client = _FakeNextcloudFolderClient()
        link_error = workspace_folder_nextcloud_links_store.WorkspaceFolderNextcloudLinkPersistenceError(
            "workspace_folder_nextcloud_error_redacted"
        )

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", side_effect=[[folder], [folder]]):
            with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link", side_effect=link_error):
                result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(fake_client.created, ["Projet-Rollback"])
        self.assertEqual(fake_client.deleted, [])
        encoded = str(result)
        self.assertIn("LOT9_CREATE_LINK_FAILED_ROLLBACK", encoded)
        self.assertIn("workspace_folder_nextcloud_rollback_ownership_unverified", encoded)
        self.assertNotIn("Projet Rollback", encoded)

    def test_nextcloud_reconcile_linked_missing_target_is_no_go_without_create(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        folder = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": folder_id,
                "display_name": "Projet Linked",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": folder_id,
                "link_nextcloud_sync_state": "linked",
                "link_nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "link_nextcloud_name_hash": "abc123def456",
                "link_last_sync_reason_code": "workspace_folder_nextcloud_create_ok",
                "link_last_sync_operation": "create",
                "link_nextcloud_share_state": "expected",
            }
        )
        errored = dict(folder)
        errored["nextcloud_sync_state"] = "sync_error"
        fake_client = _FakeNextcloudFolderClient()

        with mock.patch.object(workspace_folders_store, "list_workspace_folders", side_effect=[[folder], [errored]]):
            with mock.patch.object(workspace_folder_nextcloud_links_store, "upsert_link") as upsert:
                result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                    db_conn_func=lambda: None,
                    logger=_CaptureLogger(),
                    client=fake_client,
                )

        self.assertFalse(result["ok"])
        self.assertEqual(fake_client.created, [])
        self.assertEqual(fake_client.deleted, [])
        upsert.assert_called_once()
        self.assertEqual(upsert.call_args.kwargs["nextcloud_sync_state"], "sync_error")
        self.assertEqual(upsert.call_args.kwargs["last_sync_reason_code"], "workspace_folder_nextcloud_target_missing")
        self.assertIn("LOT9_LINKED_TARGET_MISSING", str(result))

    def test_nextcloud_reconcile_inventory_marks_expected_examples_absent(self) -> None:
        with mock.patch.object(workspace_folders_store, "list_workspace_folders", return_value=[]):
            result = workspace_folder_nextcloud_reconcile.reconcile_existing_workspace_folders(
                db_conn_func=lambda: None,
                logger=_CaptureLogger(),
                client=_FakeNextcloudFolderClient(),
            )

        self.assertTrue(result["ok"])
        self.assertEqual(result["counts_before"]["active"], 0)
        self.assertEqual(
            result["examples"],
            {
                "philosophie": "expected_example_absent",
                "conflit_lycee": "expected_example_absent",
            },
        )
        self.assertIn("LOT9_INVENTORY_ACTIVE_FOLDERS", str(result))

    def test_folder_nextcloud_persisted_link_redacts_unknown_reason_and_raw_refs(self) -> None:
        row = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "Projet Tulu",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:00:00Z",
                "deleted_at": None,
                "link_workspace_folder_id": "11111111-2222-4333-8444-555555555555",
                "link_nextcloud_sync_state": "sync_error",
                "link_nextcloud_folder_ref": "/Frida/Projet-Tulu",
                "link_nextcloud_name_hash": "Projet Tulu",
                "link_last_sync_reason_code": "/Frida/Projet-Tulu",
                "link_last_sync_operation": "rename",
                "link_nextcloud_share_state": "error",
            }
        )

        self.assertEqual(row["nextcloud_sync_state"], "sync_error")
        self.assertEqual(row["nextcloud_share_state"], "error")
        self.assertEqual(row["nextcloud_reason_code"], "workspace_folder_sync_error")
        self.assertNotEqual(row["nextcloud_folder_ref"], "/Frida/Projet-Tulu")
        self.assertNotIn("/Frida/Projet-Tulu", row["nextcloud_folder_ref"])
        self.assertNotIn("/Frida/Projet-Tulu", row["last_sync_reason_code"])
        self.assertRegex(row["nextcloud_name_hash"], r"^[0-9a-f]{12}$")
        self.assertNotIn("Projet Tulu", row["nextcloud_name_hash"])

    def test_folder_nextcloud_persisted_conflict_state_is_content_free(self) -> None:
        link = workspace_folder_nextcloud_links_store.serialize_link_row(
            {
                "workspace_folder_id": "11111111-2222-4333-8444-555555555555",
                "nextcloud_sync_state": "conflict",
                "nextcloud_folder_ref": "workspace-folder:11111111:abc123def456",
                "nextcloud_name_hash": "abc123def456",
                "last_sync_reason_code": "workspace_folder_name_conflict_nextcloud",
                "last_sync_operation": "reconcile",
                "nextcloud_share_state": "expected",
            }
        )

        self.assertEqual(link["nextcloud_sync_state"], "conflict")
        self.assertEqual(link["last_sync_reason_code"], "workspace_folder_name_conflict_nextcloud")
        self.assertEqual(link["last_sync_operation"], "reconcile")
        self.assertEqual(link["nextcloud_share_state"], "expected")

    def test_folder_nextcloud_fake_mapping_marks_tombstone_deleted_without_live(self) -> None:
        row = workspace_folders_store.serialize_workspace_folder_row(
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "Projet",
                "icon_key": "folder",
                "description": "",
                "sort_order": 1000,
                "created_at": "2026-06-16T00:00:00Z",
                "updated_at": "2026-06-16T00:01:00Z",
                "deleted_at": "2026-06-16T00:01:00Z",
            }
        )

        self.assertEqual(row["local_status"], "deleted")
        self.assertEqual(row["nextcloud_sync_state"], "deleted")
        self.assertEqual(row["nextcloud_share_state"], "unknown")
        self.assertEqual(row["nextcloud_reason_code"], "workspace_folder_deleted")
        self.assertFalse(row["nextcloud_live_checked"])

    def test_folder_nextcloud_name_validation_rejects_invalid_and_colliding_names(self) -> None:
        existing = [
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "Projet Tulu",
                "deleted_at": None,
            },
            {
                "id": "22222222-2222-4222-8222-222222222222",
                "display_name": "Archive",
                "deleted_at": "2026-06-16T00:00:00Z",
            },
        ]

        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name("", existing_folders=existing)["reason_code"],
            "workspace_folder_name_required",
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name("////", existing_folders=existing)["reason_code"],
            "workspace_folder_name_invalid",
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name("x" * 81, existing_folders=existing)["reason_code"],
            "workspace_folder_name_too_long",
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name(
                "Projet Tulu",
                existing_folders=existing,
            )["reason_code"],
            "workspace_folder_name_conflict_local",
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name(
                "Projet/Tulu",
                existing_folders=existing,
            )["reason_code"],
            "workspace_folder_name_conflict_sanitized",
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name(
                "projet tulu",
                existing_folders=existing,
            )["reason_code"],
            "workspace_folder_name_conflict_case",
        )
        self.assertTrue(
            workspace_folders_store.validate_workspace_folder_name(
                "Archive",
                existing_folders=existing,
            )["ok"]
        )

    def test_folder_nextcloud_name_validation_allows_renaming_current_folder_only(self) -> None:
        existing = [
            {
                "id": "11111111-2222-4333-8444-555555555555",
                "display_name": "Projet Tulu",
                "deleted_at": None,
            },
            {
                "id": "22222222-2222-4222-8222-222222222222",
                "display_name": "Autre",
                "deleted_at": None,
            },
        ]

        self.assertTrue(
            workspace_folders_store.validate_workspace_folder_name(
                "Projet Tulu",
                existing_folders=existing,
                current_folder_id="11111111-2222-4333-8444-555555555555",
            )["ok"]
        )
        self.assertEqual(
            workspace_folders_store.validate_workspace_folder_name(
                "Autre",
                existing_folders=existing,
                current_folder_id="11111111-2222-4333-8444-555555555555",
            )["reason_code"],
            "workspace_folder_name_conflict_local",
        )

    def test_workspace_folder_observability_reason_catalog_covers_v1_cases(self) -> None:
        catalog = set(workspace_folders_observability.reason_code_catalog())

        self.assertTrue(
            {
                "workspace_folder_create_ok",
                "workspace_folder_rename_ok",
                "workspace_folder_delete_ok",
                "workspace_folder_name_conflict_local",
                "workspace_folder_name_conflict_sanitized",
                "workspace_folder_name_conflict_case",
                "workspace_folder_name_invalid",
                "workspace_folder_name_too_long",
                "workspace_folder_permission_denied",
                "workspace_folder_target_missing",
                "workspace_folder_target_exists",
                "workspace_folder_delete_refused",
                "workspace_folder_nextcloud_error_redacted",
                "workspace_folder_sync_local_only",
                "workspace_folder_deleted",
            }.issubset(catalog)
        )

    def test_workspace_folder_observation_redacts_errors_paths_and_names(self) -> None:
        observation = workspace_folders_observability.build_workspace_folder_observation(
            "rename",
            {
                "ok": False,
                "error": "Projet Tulu SECRET_PATH REMOTE_DAV_URL",
                "reason_code": "workspace_folder_nextcloud_error_redacted",
                "folder": {
                    "id": "11111111-2222-4333-8444-555555555555",
                    "display_name": "Projet Tulu",
                    "nextcloud_logical_path": "/Frida/Projet-Tulu",
                    "storage_key": "hidden/path",
                    "nextcloud_name_hash": "abc123def456",
                    "nextcloud_sync_state": "sync_error",
                    "nextcloud_share_state": "error",
                    "nextcloud_reason_code": "workspace_folder_nextcloud_error_redacted",
                },
            },
            http_status=502,
        )

        self.assertEqual(observation["status"], "error")
        self.assertEqual(observation["reason_code"], "workspace_folder_nextcloud_error_redacted")
        self.assertEqual(observation["folder_ref"], "cf4c4732fd3b")
        self.assertEqual(observation["nextcloud_name_hash"], "abc123def456")
        self.assertEqual(observation["nextcloud_sync_state"], "sync_error")
        self.assertEqual(observation["server_path_included"], False)
        self.assertEqual(observation["remote_url_included"], False)
        self.assertEqual(observation["secret_included"], False)
        encoded = str(observation)
        self.assertNotIn("Projet Tulu", encoded)
        self.assertNotIn("/Frida/Projet-Tulu", encoded)
        self.assertNotIn("SECRET_PATH", encoded)
        self.assertNotIn("REMOTE_DAV_URL", encoded)
        self.assertNotIn("storage_key", encoded)
        self.assertNotIn("Authorization", encoded)

    def test_workspace_folder_observation_fail_closed_for_pseudo_hashes_and_reasons(self) -> None:
        pseudo_hash = workspace_folders_observability.build_workspace_folder_observation(
            "create",
            {
                "folder": {
                    "id": "id",
                    "nextcloud_name_hash": "Projet Tulu",
                    "nextcloud_reason_code": "workspace_folder_sync_local_only",
                }
            },
            http_status=200,
        )

        self.assertNotIn("nextcloud_name_hash", pseudo_hash)
        self.assertEqual(pseudo_hash["nextcloud_reason_code"], "workspace_folder_sync_local_only")
        self.assertNotIn("Projet Tulu", str(pseudo_hash))

        unknown_folder_reason = workspace_folders_observability.build_workspace_folder_observation(
            "create",
            {
                "folder": {
                    "id": "id",
                    "nextcloud_name_hash": "abc123def456",
                    "nextcloud_reason_code": "/Frida/Projet-Tulu",
                }
            },
            http_status=200,
        )

        self.assertEqual(
            unknown_folder_reason["nextcloud_reason_code"],
            "workspace_folder_nextcloud_error_redacted",
        )
        self.assertEqual(unknown_folder_reason["nextcloud_name_hash"], "abc123def456")
        self.assertNotIn("/Frida/Projet-Tulu", str(unknown_folder_reason))

        unknown_top_reason = workspace_folders_observability.build_workspace_folder_observation(
            "create",
            {"reason_code": "/Frida/Projet-Tulu"},
            http_status=400,
        )

        self.assertEqual(unknown_top_reason["reason_code"], "workspace_folder_nextcloud_error_redacted")
        self.assertNotIn("/Frida/Projet-Tulu", str(unknown_top_reason))

        listed = workspace_folders_observability.build_workspace_folder_observation(
            "list",
            {
                "items": [
                    {
                        "nextcloud_reason_code": "/Frida/Projet-Tulu",
                        "nextcloud_sync_state": "local_only",
                        "nextcloud_share_state": "expected",
                    },
                    {
                        "nextcloud_reason_code": "workspace_folder_sync_local_only",
                        "nextcloud_sync_state": "local_only",
                        "nextcloud_share_state": "expected",
                    },
                ]
            },
            http_status=200,
        )

        self.assertEqual(
            listed["reason_code_counts"],
            {
                "workspace_folder_nextcloud_error_redacted": 1,
                "workspace_folder_sync_local_only": 1,
            },
        )
        self.assertNotIn("/Frida/Projet-Tulu", str(listed))

        deleted = workspace_folders_observability.build_workspace_folder_observation(
            "delete",
            {
                "folder": {
                    "id": "id",
                    "file_delete": {"reason_code": "/Frida/Projet-Tulu"},
                    "files_preserved": True,
                }
            },
            http_status=200,
        )

        self.assertEqual(deleted["file_reason_code"], "workspace_folder_nextcloud_error_redacted")
        self.assertNotIn("/Frida/Projet-Tulu", str(deleted))

    def test_workspace_folder_service_name_conflict_response_is_content_free(self) -> None:
        class _FoldersModule:
            WORKSPACE_FOLDER_ICON_KEYS = ("folder",)

            def validate_workspace_folder_display_name(self, value, *, current_folder_id=None):
                return workspace_folders_store.validate_workspace_folder_name(
                    value,
                    existing_folders=[
                        {
                            "id": "11111111-2222-4333-8444-555555555555",
                            "display_name": "Projet Tulu",
                            "deleted_at": None,
                        }
                    ],
                    current_folder_id=current_folder_id,
                )

            def normalize_icon_key(self, value):
                return "folder"

            def coerce_sort_order(self, value):
                return None

            def sanitize_description(self, value):
                return workspace_folders_store.sanitize_description(value)

            def create_workspace_folder(self, **_kwargs):
                raise AssertionError("create must not run on conflict")

        payload, status = workspace_folders_service.create_workspace_folder(
            {"display_name": "Projet/Tulu", "icon_key": "folder"},
            workspace_folders_module=_FoldersModule(),
        )

        self.assertEqual(status, 409)
        self.assertEqual(payload["reason_code"], "workspace_folder_name_conflict_sanitized")
        self.assertEqual(payload["nextcloud_sync_state"], "conflict")
        self.assertEqual(payload["nextcloud_share_state"], "expected")
        self.assertEqual(payload["observability"]["operation"], "create")
        self.assertEqual(payload["observability"]["status"], "conflict")
        self.assertEqual(payload["observability"]["reason_code"], "workspace_folder_name_conflict_sanitized")
        encoded = str(payload)
        self.assertNotIn("Projet Tulu", encoded)
        self.assertNotIn("/Frida/Projet-Tulu", encoded)
        self.assertNotIn("http", encoded.lower())
        self.assertNotIn("dav", encoded.lower())
        self.assertNotIn("storage_key", encoded)

    def test_workspace_folder_service_fake_local_cycle_stays_local(self) -> None:
        class _FoldersModule:
            WORKSPACE_FOLDER_ICON_KEYS = ("folder", "spark")

            def __init__(self):
                self.folders = {}
                self.remote_calls = []

            def normalize_workspace_folder_id(self, value):
                return workspace_folders_store.normalize_workspace_folder_id(value)

            def normalize_icon_key(self, value):
                return workspace_folders_store.normalize_icon_key(value)

            def sanitize_display_name(self, value):
                return workspace_folders_store.sanitize_display_name(value)

            def sanitize_description(self, value):
                return workspace_folders_store.sanitize_description(value)

            def coerce_sort_order(self, value):
                return workspace_folders_store.coerce_sort_order(value)

            def validate_workspace_folder_display_name(self, value, *, current_folder_id=None):
                return workspace_folders_store.validate_workspace_folder_name(
                    value,
                    existing_folders=list(self.folders.values()),
                    current_folder_id=current_folder_id,
                )

            def list_workspace_folders(self):
                return [
                    workspace_folders_store.serialize_workspace_folder_row(row)
                    for row in self.folders.values()
                    if row.get("deleted_at") is None
                ]

            def get_workspace_folder(self, folder_id):
                normalized = self.normalize_workspace_folder_id(folder_id)
                row = self.folders.get(normalized)
                if not row or row.get("deleted_at"):
                    return None
                return workspace_folders_store.serialize_workspace_folder_row(row)

            def create_workspace_folder(self, *, display_name, icon_key, description, sort_order=None):
                folder_id = "33333333-3333-4333-8333-333333333333"
                row = {
                    "id": folder_id,
                    "display_name": display_name,
                    "icon_key": icon_key,
                    "description": description,
                    "sort_order": sort_order or 1000,
                    "created_at": "2026-06-16T00:00:00Z",
                    "updated_at": "2026-06-16T00:00:00Z",
                    "deleted_at": None,
                }
                self.folders[folder_id] = row
                return workspace_folders_store.serialize_workspace_folder_row(row)

            def update_workspace_folder(self, folder_id, **fields):
                normalized = self.normalize_workspace_folder_id(folder_id)
                row = self.folders.get(normalized)
                if not row or row.get("deleted_at"):
                    return None
                row.update({key: value for key, value in fields.items() if value is not None})
                row["updated_at"] = "2026-06-16T00:01:00Z"
                return workspace_folders_store.serialize_workspace_folder_row(row)

            def soft_delete_workspace_folder(self, folder_id):
                normalized = self.normalize_workspace_folder_id(folder_id)
                row = self.folders.get(normalized)
                if not row or row.get("deleted_at"):
                    return None
                row["deleted_at"] = "2026-06-16T00:02:00Z"
                row["updated_at"] = "2026-06-16T00:02:00Z"
                folder = workspace_folders_store.serialize_workspace_folder_row(row)
                folder["conversations_moved_out"] = 0
                return folder

        class _FilesModule:
            def __init__(self):
                self.deleted_folder_ids = []

            def delete_workspace_files_for_folder(self, folder_id):
                self.deleted_folder_ids.append(folder_id)
                return {"requested": 0, "deleted": 0, "failed": 0, "failed_file_ids": [], "reason_code": ""}

        folders_module = _FoldersModule()
        files_module = _FilesModule()

        created, create_status = workspace_folders_service.create_workspace_folder(
            {"display_name": "Projet Tulu", "icon_key": "spark"},
            workspace_folders_module=folders_module,
        )
        folder_id = created["folder"]["id"]
        self.assertEqual(create_status, 201)
        self.assertEqual(created["folder"]["nextcloud_logical_path"], "/Frida/Projet-Tulu")
        self.assertEqual(created["folder"]["nextcloud_sync_state"], "local_only")
        self.assertFalse(created["folder"]["nextcloud_live_checked"])
        self.assertEqual(created["observability"]["operation"], "create")
        self.assertEqual(created["observability"]["reason_code"], "workspace_folder_create_ok")
        self.assertEqual(created["observability"]["nextcloud_sync_state"], "local_only")
        self.assertEqual(created["observability"]["nextcloud_share_state"], "expected")
        self.assertNotIn("Projet Tulu", str(created["observability"]))
        self.assertNotIn("/Frida", str(created["observability"]))

        listed = workspace_folders_service.list_workspace_folders({}, workspace_folders_module=folders_module)
        self.assertEqual(len(listed["items"]), 1)
        self.assertEqual(listed["items"][0]["nextcloud_share_state"], "expected")
        self.assertEqual(listed["observability"]["reason_code"], "workspace_folder_list_ok")
        self.assertEqual(listed["observability"]["folder_count"], 1)
        self.assertEqual(listed["observability"]["sync_state_counts"], {"local_only": 1})
        self.assertEqual(listed["observability"]["share_state_counts"], {"expected": 1})

        renamed, rename_status = workspace_folders_service.patch_workspace_folder(
            folder_id,
            {"display_name": "Projet Renomme"},
            workspace_folders_module=folders_module,
        )
        self.assertEqual(rename_status, 200)
        self.assertEqual(renamed["folder"]["nextcloud_logical_path"], "/Frida/Projet-Renomme")
        self.assertEqual(renamed["folder"]["nextcloud_reason_code"], "workspace_folder_sync_local_only")
        self.assertEqual(renamed["observability"]["operation"], "rename")
        self.assertEqual(renamed["observability"]["reason_code"], "workspace_folder_rename_ok")
        self.assertNotIn("Projet Renomme", str(renamed["observability"]))

        deleted, delete_status = workspace_folders_service.delete_workspace_folder(
            folder_id,
            workspace_folders_module=folders_module,
            workspace_files_module=files_module,
        )
        self.assertEqual(delete_status, 200)
        self.assertEqual(deleted["folder"]["nextcloud_sync_state"], "deleted")
        self.assertEqual(deleted["folder"]["nextcloud_share_state"], "unknown")
        self.assertEqual(deleted["folder"]["nextcloud_reason_code"], "workspace_folder_deleted")
        self.assertEqual(deleted["folder"]["files_deleted"], 0)
        self.assertEqual(deleted["folder"]["files_preserved"], True)
        self.assertEqual(deleted["folder"]["file_delete"]["reason_code"], "workspace_folder_files_preserved")
        self.assertEqual(deleted["observability"]["operation"], "delete")
        self.assertEqual(deleted["observability"]["reason_code"], "workspace_folder_delete_ok")
        self.assertEqual(deleted["observability"]["nextcloud_sync_state"], "deleted")
        self.assertEqual(deleted["observability"]["files_deleted"], 0)
        self.assertEqual(deleted["observability"]["files_preserved"], True)
        self.assertEqual(deleted["observability"]["file_reason_code"], "workspace_folder_files_preserved")
        self.assertEqual(files_module.deleted_folder_ids, [])
        self.assertEqual(folders_module.remote_calls, [])
        encoded = str(deleted)
        self.assertNotIn("http", encoded.lower())
        self.assertNotIn("dav", encoded.lower())
        self.assertNotIn("storage_key", encoded)

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

    def test_folder_file_delete_summary_deletes_all_bytes_and_tombstones_rows(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id_1 = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        file_id_2 = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_1 = workspace_files_store.storage_key_for(folder_id, file_id_1, ".txt")
            key_2 = workspace_files_store.storage_key_for(folder_id, file_id_2, ".txt")
            path_1 = workspace_files_store.write_file_bytes(root, key_1, b"bonjour")
            path_2 = workspace_files_store.write_file_bytes(root, key_2, b"salut")
            conn = _WorkspaceFilesConn(
                {
                    file_id_1: _workspace_file_row(folder_id, file_id_1, key_1),
                    file_id_2: _workspace_file_row(folder_id, file_id_2, key_2),
                }
            )
            logger = _CaptureLogger()

            summary = workspace_files_store.delete_workspace_files_for_folder(
                folder_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

            self.assertEqual(summary["requested"], 2)
            self.assertEqual(summary["deleted"], 2)
            self.assertEqual(summary["failed"], 0)
            self.assertFalse(path_1.exists())
            self.assertFalse(path_2.exists())
            self.assertEqual(conn.rows[file_id_1]["status"], "deleted")
            self.assertEqual(conn.rows[file_id_2]["reason_code"], "workspace_file_deleted")
            self.assertIn("workspace_files_folder_delete_summary", "\n".join(logger.lines))

    def test_folder_file_delete_summary_reports_partial_failure_without_masking_it(self) -> None:
        folder_id = "11111111-2222-4333-8444-555555555555"
        file_id_ok = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        file_id_bad = "bbbbbbbb-bbbb-4ccc-8ddd-eeeeeeeeeeee"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            key_ok = workspace_files_store.storage_key_for(folder_id, file_id_ok, ".txt")
            path_ok = workspace_files_store.write_file_bytes(root, key_ok, b"bonjour")
            conn = _WorkspaceFilesConn(
                {
                    file_id_ok: _workspace_file_row(folder_id, file_id_ok, key_ok),
                    file_id_bad: _workspace_file_row(folder_id, file_id_bad, "../escape.txt"),
                }
            )
            logger = _CaptureLogger()

            summary = workspace_files_store.delete_workspace_files_for_folder(
                folder_id,
                db_conn_func=lambda: conn,
                storage_root=root,
                logger=logger,
            )

            self.assertEqual(summary["requested"], 2)
            self.assertEqual(summary["deleted"], 1)
            self.assertEqual(summary["failed"], 1)
            self.assertEqual(summary["failed_file_ids"], [file_id_bad])
            self.assertEqual(summary["reason_code"], "workspace_folder_file_delete_failed")
            self.assertFalse(path_ok.exists())
            self.assertEqual(conn.rows[file_id_ok]["status"], "deleted")
            self.assertIsNone(conn.rows[file_id_bad]["deleted_at"])
            logged = "\n".join(logger.lines)
            self.assertIn("workspace_files_delete_failed", logged)
            self.assertNotIn("../escape", logged)

    def test_workspace_file_logs_are_content_free(self) -> None:
        logger = _CaptureLogger()

        workspace_files_store.log_content_free_event(
            logger,
            "upload_ok",
            folder_id="11111111-2222-4333-8444-555555555555",
            file_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
            storage_key="/tmp/secret/path.txt",
            internal_path="/tmp/secret/path.txt",
            text_content="contenu brut",
            binary_content=b"secret",
            base64="data:image/png;base64,secret",
            mime_type="text/plain",
            byte_size=12,
            sha256_12="abc123def456",
        )

        logged = "\n".join(logger.lines)
        self.assertIn("workspace_files_upload_ok", logged)
        self.assertIn("mime_type=text/plain", logged)
        self.assertIn("sha256_12=abc123def456", logged)
        self.assertNotIn("storage_key", logged)
        self.assertNotIn("internal_path", logged)
        self.assertNotIn("/tmp/secret", logged)
        self.assertNotIn("contenu brut", logged)
        self.assertNotIn("data:image", logged)
        self.assertNotIn("base64", logged)

    def test_workspace_file_prompt_lane_injects_text_without_active_document_persistence(self) -> None:
        raw_text = "texte choisi explicitement"
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_folder_id": "11111111-2222-4333-8444-555555555555",
                    "filename": "note.txt",
                    "media_type": "text/plain",
                    "source_extension": ".txt",
                    "byte_size": len(raw_text.encode("utf-8")),
                    "text_chars": len(raw_text),
                    "text_sha256_12": "abc123def456",
                    "media_kind": "text",
                    "text_content": raw_text,
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 10,
            max_tokens=1000,
        )

        joined = "\n".join(str(message.get("content") or "") for message in prompt_messages)
        self.assertEqual(lane.injected_count, 1)
        self.assertIn("Fichier de repertoire selectionne injecte", joined)
        self.assertIn(raw_text, joined)
        self.assertEqual(lane.decisions[0].source, "workspace_file_selection")

    def test_workspace_file_prompt_lane_excludes_too_large_with_workspace_reason(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "filename": "note.txt",
                    "media_type": "text/plain",
                    "source_extension": ".txt",
                    "byte_size": 10,
                    "text_chars": 10,
                    "media_kind": "text",
                    "text_content": "trop long",
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 9999,
            max_tokens=10,
        )

        joined = "\n".join(str(message.get("content") or "") for message in prompt_messages)
        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertEqual(lane.decisions[0].reason_code, "workspace_file_too_large")
        self.assertIn("workspace_file_too_large", joined)

    def test_workspace_file_image_payload_uses_visual_fallback(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        lane = active_document_prompt_lane.inject_active_document_prompt_lane(
            prompt_messages,
            [
                {
                    "source": "workspace_file_selection",
                    "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    "filename": "image.png",
                    "media_type": "image/png",
                    "source_extension": ".png",
                    "byte_size": 8,
                    "media_kind": "image",
                    "content_sha256_12": "abc123def456",
                    "image_width": 40,
                    "image_height": 40,
                    "image_content": b"pngbytes",
                    "injectable": True,
                }
            ],
            model="openai/gpt-5.1",
            count_tokens_func=lambda _messages, _model: 10,
            max_tokens=1000,
        )

        self.assertEqual(lane.injected_count, 1)
        self.assertEqual(lane.not_injected_count, 0)
        self.assertEqual(lane.decisions[0].reason_code, "")
        self.assertEqual(lane.decisions[0].payload_order, "text_then_image_url")
        self.assertTrue(any(isinstance(message.get("content"), list) for message in prompt_messages))
        payload = active_documents_observability.build_prompt_decision_payload(lane)
        encoded_payload = str(payload)
        self.assertEqual(payload["documents"][0]["filename"], "workspace_file")
        self.assertEqual(payload["documents"][0]["decision"], "injected")
        self.assertEqual(payload["documents"][0]["payload_order"], "text_then_image_url")
        self.assertNotIn("image.png", encoded_payload)
        self.assertNotIn("image_content", encoded_payload)
        self.assertNotIn("data:image", encoded_payload)

    def test_workspace_file_ocr_required_pdf_payload_uses_visual_fallback(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        with mock.patch.object(
            active_document_prompt_lane.active_document_visual_limits,
            "check_pdf_visual_pages",
            return_value=type("PageCheck", (), {"ok": True})(),
        ):
            lane = active_document_prompt_lane.inject_active_document_prompt_lane(
                prompt_messages,
                [
                    {
                        "source": "workspace_file_selection",
                        "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                        "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                        "filename": "scan.pdf",
                        "media_type": "application/pdf",
                        "source_extension": ".pdf",
                        "byte_size": 12,
                        "media_kind": "file",
                        "content_sha256_12": "abc123def456",
                        "file_content": b"%PDF scanned",
                        "injectable": True,
                    }
                ],
                model="openai/gpt-5.1",
                count_tokens_func=lambda _messages, _model: 10,
                max_tokens=1000,
            )

        self.assertEqual(lane.injected_count, 1)
        self.assertEqual(lane.not_injected_count, 0)
        self.assertEqual(lane.decisions[0].media_kind, "file")
        self.assertEqual(lane.decisions[0].reason_code, "")
        self.assertEqual(lane.decisions[0].payload_order, "text_then_file")
        self.assertTrue(any(isinstance(message.get("content"), list) for message in prompt_messages))
        text_parts = [
            part.get("text", "")
            for message in prompt_messages
            if isinstance(message.get("content"), list)
            for part in message["content"]
            if part.get("type") == "text"
        ]
        self.assertNotIn("data:application/pdf", "\n".join(text_parts))
        self.assertIn("ne constituent pas un texte OCRise garanti", "\n".join(text_parts))
        self.assertNotIn("imageUrl", str(prompt_messages))

    def test_workspace_file_pdf_visual_over_provider_cap_is_excluded(self) -> None:
        prompt_messages = [{"role": "system", "content": "SYSTEM"}, {"role": "user", "content": "question"}]

        with (
            mock.patch.object(active_document_prompt_lane, "ACTIVE_FILE_PROVIDER_MAX_BYTES", 4),
            mock.patch.object(
                active_document_prompt_lane,
                "_file_data_url",
                side_effect=AssertionError("_file_data_url must not run"),
            ),
        ):
            lane = active_document_prompt_lane.inject_active_document_prompt_lane(
                prompt_messages,
                [
                    {
                        "source": "workspace_file_selection",
                        "document_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                        "workspace_file_id": "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                        "filename": "scan.pdf",
                        "media_type": "application/pdf",
                        "source_extension": ".pdf",
                        "byte_size": 12,
                        "media_kind": "file",
                        "content_sha256_12": "abc123def456",
                        "file_content": b"%PDF scanned",
                        "injectable": True,
                    }
                ],
                model="openai/gpt-5.1",
                count_tokens_func=lambda _messages, _model: 10,
                max_tokens=1000,
            )

        self.assertEqual(lane.injected_count, 0)
        self.assertEqual(lane.not_injected_count, 1)
        self.assertEqual(lane.decisions[0].reason_code, "workspace_file_pdf_visual_too_large")
        joined = "\n".join(str(message.get("content") or "") for message in prompt_messages)
        self.assertIn("workspace_file_pdf_visual_too_large", joined)
        self.assertNotIn("file_data", joined)
        self.assertNotIn("data:application/pdf", joined)

    def test_chat_decision_record_routes_workspace_files_to_selection_store(self) -> None:
        class _SelectionStore:
            def __init__(self):
                self.injected = []
                self.excluded = []

            def record_selection_injected(self, conversation_id, file_id, *, turn_id):
                self.injected.append((conversation_id, file_id, turn_id))
                return True

            def record_selection_excluded(self, conversation_id, file_id, *, turn_id, reason_code):
                self.excluded.append((conversation_id, file_id, turn_id, reason_code))
                return True

        lane = active_document_prompt_lane.ActiveDocumentPromptLane(
            contract_message=None,
            content_message=None,
            decisions=(
                active_document_prompt_lane.ActiveDocumentPromptDecision(
                    document_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    workspace_file_id="aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee",
                    filename="note.txt",
                    media_type="text/plain",
                    source_extension=".txt",
                    byte_size=4,
                    text_chars=4,
                    token_estimate=1,
                    text_sha256_12="abc123def456",
                    injected=True,
                    source="workspace_file_selection",
                ),
            ),
        )
        selection_store = _SelectionStore()

        chat_service._record_active_document_prompt_decisions(
            conversation={"id": "11111111-2222-4333-8444-555555555555"},
            lane=lane,
            turn_id="turn-1",
            active_documents_module=object(),
            workspace_file_selections_module=selection_store,
        )

        self.assertEqual(
            selection_store.injected,
            [("11111111-2222-4333-8444-555555555555", "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee", "turn-1")],
        )


if __name__ == "__main__":
    unittest.main()
