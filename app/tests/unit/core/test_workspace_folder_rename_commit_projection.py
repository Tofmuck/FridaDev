from __future__ import annotations

import hashlib
import sys
import unittest
from copy import deepcopy
from pathlib import Path
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_nextcloud_client
from core import workspace_folder_nextcloud_runtime
from core import workspace_folders_store


FOLDER_ID = "11111111-2222-4333-8444-555555555555"
OLD_DISPLAY_NAME = "Alpha Workspace"
NEW_DISPLAY_NAME = "Beta Workspace"
OLD_TARGET = "Alpha-Workspace"
NEW_TARGET = "Beta-Workspace"


def _hash12(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:12]


def _folder_ref(target: str) -> str:
    return f"workspace-folder:11111111:{_hash12(target.casefold())}"


class _CaptureLogger:
    def __init__(self) -> None:
        self.lines: list[str] = []

    def warning(self, message, *args, **_kwargs) -> None:
        self.lines.append(message % args if args else str(message))


class _StatefulNextcloud:
    def __init__(self, *, fail_move_calls: set[int] | None = None) -> None:
        self.folders = {OLD_TARGET}
        self.moves: list[tuple[str, str]] = []
        self.fail_move_calls = set(fail_move_calls or ())

    def move_folder(self, source: str, target: str):
        self.moves.append((source, target))
        if len(self.moves) in self.fail_move_calls:
            raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                workspace_folder_nextcloud_client.REASON_UNAVAILABLE,
            )
        if source not in self.folders or target in self.folders:
            raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                workspace_folder_nextcloud_client.REASON_CONFLICT,
            )
        self.folders.remove(source)
        self.folders.add(target)
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_RENAME_OK,
            201,
        )


class _RelationalDatabase:
    def __init__(
        self,
        *,
        fail_link_upserts: int = 0,
        fail_folder_update: bool = False,
        fail_folder_commit: bool = False,
    ) -> None:
        self.folder = {
            "id": FOLDER_ID,
            "display_name": OLD_DISPLAY_NAME,
            "icon_key": "folder",
            "description": "",
            "sort_order": 1000,
            "created_at": "2026-06-16T00:00:00Z",
            "updated_at": "2026-06-16T00:00:00Z",
            "deleted_at": None,
        }
        self.link = {
            "workspace_folder_id": FOLDER_ID,
            "nextcloud_sync_state": "linked",
            "nextcloud_folder_ref": _folder_ref(OLD_TARGET),
            "nextcloud_name_hash": _hash12(OLD_TARGET.casefold()),
            "last_sync_at": "2026-06-16T00:00:00Z",
            "last_sync_reason_code": workspace_folder_nextcloud_client.REASON_CREATE_OK,
            "last_sync_operation": "create",
            "nextcloud_share_state": "expected",
            "created_at": "2026-06-16T00:00:00Z",
            "updated_at": "2026-06-16T00:00:00Z",
        }
        self.folder_update_committed = False
        self.post_commit_projection_reads = 0
        self.commits: list[str] = []
        self.rollbacks: list[str] = []
        self.events: list[str] = []
        self.fail_link_upserts = fail_link_upserts
        self.fail_folder_update = fail_folder_update
        self.fail_folder_commit = fail_folder_commit
        self.link_upsert_attempts = 0
        self.folder_update_attempts = 0

    def connect(self):
        return _RelationalConnection(self)

    def joined_row(self, folder: dict, link: dict | None) -> dict:
        row = dict(folder)
        if link is None:
            return row
        for key, value in link.items():
            row[f"link_{key}"] = value
        return row


class _RelationalConnection:
    def __init__(self, database: _RelationalDatabase) -> None:
        self.database = database
        self.folder = deepcopy(database.folder)
        self.link = deepcopy(database.link)
        self.dirty_folder = False
        self.dirty_link = False
        self.operation = "read"

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args, **kwargs):
        return _RelationalCursor(self)

    def commit(self) -> None:
        if self.dirty_folder and self.database.fail_folder_commit:
            self.database.events.append("folder_commit_failed")
            raise RuntimeError("folder_commit_failed")
        if self.dirty_folder:
            self.database.folder = deepcopy(self.folder)
            self.database.folder_update_committed = True
        if self.dirty_link:
            self.database.link = deepcopy(self.link)
        self.database.commits.append(self.operation)
        self.database.events.append(f"{self.operation}_committed")

    def rollback(self) -> None:
        self.database.rollbacks.append(self.operation)
        self.database.events.append(f"{self.operation}_rolled_back")


class _RelationalCursor:
    def __init__(self, connection: _RelationalConnection) -> None:
        self.connection = connection
        self.row = None
        self.rows = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None) -> None:
        normalized_sql = " ".join(str(sql).split()).lower()
        params = tuple(params or ())
        if "insert into workspace_folder_nextcloud_links" in normalized_sql:
            self._upsert_link(params)
            return
        if "update workspace_folders" in normalized_sql:
            self._update_folder(normalized_sql, params)
            return
        if "from workspace_folders folders" in normalized_sql:
            self._select_folders(normalized_sql)
            return
        raise AssertionError(f"unexpected SQL family: {normalized_sql[:80]}")

    def _upsert_link(self, params: tuple) -> None:
        self.connection.database.link_upsert_attempts += 1
        if self.connection.database.fail_link_upserts > 0:
            self.connection.database.fail_link_upserts -= 1
            raise RuntimeError("link_upsert_failed")
        self.connection.operation = "link_upsert"
        self.connection.dirty_link = True
        self.connection.link = {
            "workspace_folder_id": params[0],
            "nextcloud_sync_state": params[1],
            "nextcloud_folder_ref": params[2],
            "nextcloud_name_hash": params[3],
            "last_sync_at": "2026-06-16T00:01:00Z",
            "last_sync_reason_code": params[4],
            "last_sync_operation": params[5],
            "nextcloud_share_state": params[6],
            "created_at": self.connection.link["created_at"],
            "updated_at": "2026-06-16T00:01:00Z",
        }
        self.row = {
            f"link_{key}": value
            for key, value in self.connection.link.items()
        }

    def _update_folder(self, normalized_sql: str, params: tuple) -> None:
        self.connection.database.folder_update_attempts += 1
        self.connection.operation = "folder_update"
        self.connection.database.events.append("folder_update_executed")
        if self.connection.database.fail_folder_update:
            raise RuntimeError("folder_update_failed")
        if self.connection.folder.get("deleted_at") is not None:
            self.row = None
            return
        self.connection.dirty_folder = True
        value_index = 0
        for column in ("display_name", "icon_key", "description", "sort_order"):
            if f"{column} = %s" in normalized_sql:
                self.connection.folder[column] = params[value_index]
                value_index += 1
        self.connection.folder["updated_at"] = "2026-06-16T00:02:00Z"
        self.row = dict(self.connection.folder)
        if "from updated_folder folders" in normalized_sql:
            self.row = self.connection.database.joined_row(
                self.connection.folder,
                self.connection.link,
            )

    def _select_folders(self, normalized_sql: str) -> None:
        if (
            "where folders.id" in normalized_sql
            and self.connection.database.folder_update_committed
        ):
            self.connection.database.post_commit_projection_reads += 1
            self.connection.database.events.append("post_commit_projection_read")
            raise RuntimeError("projection_read_unavailable")
        if (
            self.connection.folder.get("deleted_at") is not None
            and "deleted_at is null" in normalized_sql
        ):
            self.rows = []
            self.row = None
            return
        row = self.connection.database.joined_row(
            self.connection.folder,
            self.connection.link,
        )
        if "order by folders.sort_order" in normalized_sql:
            self.rows = [row]
        else:
            self.row = row

    def fetchone(self):
        return deepcopy(self.row)

    def fetchall(self):
        return deepcopy(self.rows)


class WorkspaceFolderRenameCommitProjectionTests(unittest.TestCase):
    def test_committed_rename_does_not_rollback_when_a_later_projection_read_would_fail(self) -> None:
        database = _RelationalDatabase()
        nextcloud = _StatefulNextcloud()

        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
            client=nextcloud,
        )

        self.assertEqual(
            (
                result.get("ok"),
                database.folder["display_name"],
                database.link["nextcloud_name_hash"],
                nextcloud.folders,
                nextcloud.moves,
            ),
            (
                True,
                NEW_DISPLAY_NAME,
                _hash12(NEW_TARGET.casefold()),
                {NEW_TARGET},
                [(OLD_TARGET, NEW_TARGET)],
            ),
        )
        projection = result["folder"]
        self.assertEqual(projection["nextcloud_target_name"], NEW_TARGET)
        self.assertEqual(projection["nextcloud_logical_path"], f"/Frida/{NEW_TARGET}")
        self.assertEqual(projection["nextcloud_folder_ref"], _folder_ref(NEW_TARGET))
        self.assertEqual(projection["nextcloud_name_hash"], _hash12(NEW_TARGET.casefold()))
        self.assertEqual(projection["nextcloud_sync_state"], "linked")
        self.assertEqual(
            projection["nextcloud_reason_code"],
            workspace_folder_nextcloud_client.REASON_RENAME_OK,
        )
        self.assertEqual(database.post_commit_projection_reads, 0)

    def test_update_failure_before_commit_restores_remote_and_link(self) -> None:
        database = _RelationalDatabase(fail_folder_update=True)
        nextcloud = _StatefulNextcloud()

        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
            client=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(
            result["reason_code"],
            workspace_folder_nextcloud_client.REASON_LOCAL_PERSISTENCE_FAILED,
        )
        self.assertEqual(database.folder["display_name"], OLD_DISPLAY_NAME)
        self.assertEqual(database.link["nextcloud_name_hash"], _hash12(OLD_TARGET.casefold()))
        self.assertEqual(nextcloud.folders, {OLD_TARGET})
        self.assertEqual(
            nextcloud.moves,
            [(OLD_TARGET, NEW_TARGET), (NEW_TARGET, OLD_TARGET)],
        )
        self.assertNotIn("folder_update", database.commits)

    def test_commit_failure_does_not_claim_success_and_keeps_compensation(self) -> None:
        database = _RelationalDatabase(fail_folder_commit=True)
        nextcloud = _StatefulNextcloud()

        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
            client=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(database.folder["display_name"], OLD_DISPLAY_NAME)
        self.assertEqual(database.link["nextcloud_name_hash"], _hash12(OLD_TARGET.casefold()))
        self.assertEqual(nextcloud.folders, {OLD_TARGET})
        self.assertEqual(
            nextcloud.moves,
            [(OLD_TARGET, NEW_TARGET), (NEW_TARGET, OLD_TARGET)],
        )
        self.assertIn("folder_commit_failed", database.events)
        self.assertNotIn("folder_update", database.commits)

    def test_initial_move_failure_performs_no_local_mutation(self) -> None:
        database = _RelationalDatabase()
        nextcloud = _StatefulNextcloud(fail_move_calls={1})

        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
            client=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(database.folder["display_name"], OLD_DISPLAY_NAME)
        self.assertEqual(database.link["nextcloud_name_hash"], _hash12(OLD_TARGET.casefold()))
        self.assertEqual(nextcloud.folders, {OLD_TARGET})
        self.assertEqual(database.link_upsert_attempts, 0)
        self.assertEqual(database.folder_update_attempts, 0)

    def test_link_upsert_failure_preserves_existing_compensation(self) -> None:
        database = _RelationalDatabase(fail_link_upserts=1)
        nextcloud = _StatefulNextcloud()

        result = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
            client=nextcloud,
        )

        self.assertFalse(result["ok"])
        self.assertEqual(database.folder["display_name"], OLD_DISPLAY_NAME)
        self.assertEqual(database.link["nextcloud_name_hash"], _hash12(OLD_TARGET.casefold()))
        self.assertEqual(nextcloud.folders, {OLD_TARGET})
        self.assertEqual(database.folder_update_attempts, 0)
        self.assertEqual(database.link_upsert_attempts, 2)

    def test_local_metadata_update_returns_complete_existing_link_projection(self) -> None:
        database = _RelationalDatabase()

        result = workspace_folders_store.update_workspace_folder(
            FOLDER_ID,
            icon_key="spark",
            description="Synthetic description",
            sort_order=2000,
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
        )

        self.assertIsNotNone(result)
        self.assertEqual(result["icon_key"], "spark")
        self.assertEqual(result["description"], "Synthetic description")
        self.assertEqual(result["sort_order"], 2000)
        self.assertEqual(result["nextcloud_sync_state"], "linked")
        self.assertEqual(result["nextcloud_folder_ref"], _folder_ref(OLD_TARGET))
        self.assertEqual(result["nextcloud_name_hash"], _hash12(OLD_TARGET.casefold()))
        self.assertEqual(database.post_commit_projection_reads, 0)

    def test_invalid_projection_rolls_back_before_commit(self) -> None:
        database = _RelationalDatabase()

        with mock.patch.object(workspace_folders_store, "serialize_workspace_folder_row", return_value=None):
            result = workspace_folders_store.update_workspace_folder(
                FOLDER_ID,
                icon_key="spark",
                db_conn_func=database.connect,
                logger=_CaptureLogger(),
            )

        self.assertIsNone(result)
        self.assertEqual(database.folder["icon_key"], "folder")
        self.assertNotIn("folder_update", database.commits)
        self.assertIn("folder_update", database.rollbacks)

    def test_deleted_folder_does_not_commit_or_fabricate_success(self) -> None:
        database = _RelationalDatabase()
        database.folder["deleted_at"] = "2026-06-16T00:03:00Z"

        result = workspace_folders_store.update_workspace_folder(
            FOLDER_ID,
            icon_key="spark",
            db_conn_func=database.connect,
            logger=_CaptureLogger(),
        )

        self.assertIsNone(result)
        self.assertEqual(database.folder["icon_key"], "folder")
        self.assertNotIn("folder_update", database.commits)
        self.assertIn("folder_update", database.rollbacks)

    def test_rename_observability_does_not_expose_folder_names(self) -> None:
        database = _RelationalDatabase()
        nextcloud = _StatefulNextcloud()
        logger = _CaptureLogger()

        workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
            FOLDER_ID,
            display_name=NEW_DISPLAY_NAME,
            db_conn_func=database.connect,
            logger=logger,
            client=nextcloud,
        )

        encoded_logs = "\n".join(logger.lines)
        self.assertNotIn(OLD_DISPLAY_NAME, encoded_logs)
        self.assertNotIn(NEW_DISPLAY_NAME, encoded_logs)
        self.assertNotIn(OLD_TARGET, encoded_logs)
        self.assertNotIn(NEW_TARGET, encoded_logs)


if __name__ == "__main__":
    unittest.main()
