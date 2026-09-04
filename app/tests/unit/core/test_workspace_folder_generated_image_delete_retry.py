from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Callable
from unittest import mock


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_content_service
from core import workspace_folder_generated_image_nextcloud_client
from core import workspace_folder_generated_images
from core import workspace_folder_generated_images_store
from core import workspace_folder_nextcloud_client
from core import workspace_folder_nextcloud_projection
from core import workspace_folder_nextcloud_runtime
from core import workspace_folders_store


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
IMAGE_ID = "11111111-2222-4333-8444-555555555555"
TARGET_NAME = "generated-image-11111111-2222-4333-8444-555555555555.png"
TARGET_REF = workspace_folder_generated_images.target_ref_for_target(TARGET_NAME)
OTHER_TARGET_NAME = "generated-image-22222222-3333-4444-8555-666666666666.png"
OTHER_TARGET_REF = workspace_folder_generated_images.target_ref_for_target(OTHER_TARGET_NAME)
OTHER_FOLDER_ID = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
OTHER_IMAGE_ID = "33333333-4444-4555-8666-777777777777"
PARENT_TARGET_A = "Synthetic-Folder-A"
PARENT_TARGET_B = "Synthetic-Folder-B"


def _parent_hash(target: str) -> str:
    return workspace_folder_nextcloud_projection.hash12(target.casefold())


def _parent_ref(target: str) -> str:
    return f"workspace-folder:aaaaaaaa:{_parent_hash(target)}"


def _folder(*, parent_target: str = PARENT_TARGET_A, sync_state: str = "linked") -> dict[str, Any]:
    return {
        "id": FOLDER_ID,
        "display_name": "Synthetic folder",
        "nextcloud_target_name": parent_target,
        "nextcloud_sync_state": sync_state,
        "nextcloud_folder_ref": _parent_ref(parent_target),
        "nextcloud_name_hash": _parent_hash(parent_target),
        "deleted_at": None,
    }


def _image_row(**overrides: Any) -> dict[str, Any]:
    row = {
        "id": IMAGE_ID,
        "workspace_folder_id": FOLDER_ID,
        "display_name": "Synthetic image",
        "display_name_hash": "abc123def456",
        "target_name_internal": TARGET_NAME,
        "target_ref": TARGET_REF,
        "mime_type": "image/png",
        "image_format": "png",
        "byte_size": 64,
        "width": 32,
        "height": 32,
        "content_hash": "a" * 64,
        "content_hash_short": "a" * 12,
        "generator_key": "synthetic_generator",
        "provider_model": "synthetic/model",
        "aspect_ratio": "1:1",
        "image_size": "1K",
        "prompt_present": True,
        "prompt_length_bucket": "chars_001_to_250",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "etag_value": "",
        "etag_hash": "",
        "last_reason_code": workspace_folder_generated_images.REASON_STORE_OK,
        "created_at": "2026-09-04T10:00:00Z",
        "updated_at": "2026-09-04T10:00:00Z",
        "deleted_at": None,
    }
    row.update(overrides)
    return row


class _StatefulDatabase:
    def __init__(self, *, fail_tombstones: int = 0) -> None:
        self.row = _image_row()
        self.parent_target = PARENT_TARGET_A
        self.link = {
            "workspace_folder_id": FOLDER_ID,
            "nextcloud_sync_state": "linked",
            "nextcloud_folder_ref": _parent_ref(PARENT_TARGET_A),
            "nextcloud_name_hash": _parent_hash(PARENT_TARGET_A),
        }
        self.fail_tombstones = fail_tombstones
        self.tombstone_attempts = 0
        self.commits = 0

    def connect(self):
        return _StatefulConnection(self)


class _StatefulConnection:
    def __init__(self, database: _StatefulDatabase) -> None:
        self.database = database

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def cursor(self, *args: Any, **kwargs: Any):
        return _StatefulCursor(self.database)

    def commit(self) -> None:
        self.database.commits += 1


class _StatefulCursor:
    def __init__(self, database: _StatefulDatabase) -> None:
        self.database = database
        self.result: dict[str, Any] | None = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql: Any, params: tuple[Any, ...] | None = None) -> None:
        normalized_sql = " ".join(str(sql).split())
        values = tuple(params or ())
        if normalized_sql.startswith("UPDATE workspace_folder_nextcloud_links"):
            self._update_parent_link(normalized_sql, values)
            return
        if normalized_sql.startswith("INSERT INTO workspace_folder_nextcloud_links"):
            self._upsert_parent_link(values)
            return
        if normalized_sql.startswith("SELECT"):
            self.result = (
                dict(self.database.row)
                if values and str(self.database.row.get("id")) == str(values[0])
                else None
            )
            return
        if not normalized_sql.startswith("UPDATE workspace_folder_generated_images"):
            raise AssertionError("unexpected SQL operation")

        self.database.tombstone_attempts += 1
        if self.database.fail_tombstones > 0:
            self.database.fail_tombstones -= 1
            raise RuntimeError("synthetic tombstone failure")

        reason_code = str(values[0])
        expected_image_id = str(values[1])
        expected_folder_id = str(values[2]) if len(values) > 2 else ""
        expected_target_name = str(values[3]) if len(values) > 3 else ""
        expected_target_ref = str(values[4]) if len(values) > 4 else ""
        parent_guard_present = "workspace_folder_nextcloud_links" in normalized_sql
        expected_parent_ref = str(values[5]) if len(values) > 5 else ""
        expected_parent_hash = str(values[6]) if len(values) > 6 else ""
        row = self.database.row
        matches = (
            str(row.get("id")) == expected_image_id
            and str(row.get("workspace_folder_id")) == expected_folder_id
            and str(row.get("target_name_internal")) == expected_target_name
            and str(row.get("target_ref")) == expected_target_ref
            and row.get("deleted_at") is None
            and row.get("local_state") == "available"
            and row.get("nextcloud_sync_state") == "linked"
        )
        if parent_guard_present:
            link = self.database.link
            matches = matches and (
                str(link.get("workspace_folder_id")) == expected_folder_id
                and link.get("nextcloud_sync_state") == "linked"
                and str(link.get("nextcloud_folder_ref")) == expected_parent_ref
                and str(link.get("nextcloud_name_hash")) == expected_parent_hash
            )
        if not matches:
            self.result = None
            return
        row.update(
            {
                "local_state": "deleted",
                "nextcloud_sync_state": "deleted",
                "last_reason_code": reason_code,
                "updated_at": "2026-09-04T10:05:00Z",
                "deleted_at": "2026-09-04T10:05:00Z",
            }
        )
        self.result = dict(row)

    def _update_parent_link(
        self,
        normalized_sql: str,
        values: tuple[Any, ...],
    ) -> None:
        if "SET nextcloud_sync_state = 'sync_error'" in normalized_sql:
            target_state = "sync_error"
            expected_state = "sync_pending"
            share_state = "error"
        elif "SET nextcloud_sync_state = 'sync_pending'" in normalized_sql:
            target_state = "sync_pending"
            expected_state = "linked"
            share_state = self.database.link.get("nextcloud_share_state")
        else:
            raise AssertionError("unexpected parent link transition")
        reason_code, folder_id, expected_ref, expected_hash = values
        link = self.database.link
        matches = (
            str(link.get("workspace_folder_id")) == str(folder_id)
            and link.get("nextcloud_sync_state") == expected_state
            and str(link.get("nextcloud_folder_ref")) == str(expected_ref)
            and str(link.get("nextcloud_name_hash")) == str(expected_hash)
        )
        if not matches:
            self.result = None
            return
        link.update(
            {
                "nextcloud_sync_state": target_state,
                "last_sync_reason_code": str(reason_code),
                "last_sync_operation": "rename",
                "nextcloud_share_state": share_state,
            }
        )
        self.result = {
            f"link_{key}": value
            for key, value in link.items()
        }

    def _upsert_parent_link(self, values: tuple[Any, ...]) -> None:
        folder_id, sync_state, folder_ref, name_hash, reason_code, operation, share_state = values
        self.database.link.update(
            {
                "workspace_folder_id": str(folder_id),
                "nextcloud_sync_state": str(sync_state),
                "nextcloud_folder_ref": str(folder_ref),
                "nextcloud_name_hash": str(name_hash),
                "last_sync_reason_code": str(reason_code),
                "last_sync_operation": str(operation),
                "nextcloud_share_state": str(share_state),
            }
        )
        self.result = {
            f"link_{key}": value
            for key, value in self.database.link.items()
        }

    def fetchone(self):
        return self.result


class _StatefulImages:
    def __init__(self, database: _StatefulDatabase) -> None:
        self.database = database
        self.events: list[tuple[str, dict[str, Any]]] = []

    def get_generated_image(self, image_id: str, *, fail_closed: bool = True):
        return workspace_folder_generated_images_store.get_generated_image(
            image_id,
            db_conn_func=self.database.connect,
            logger=self,
            fail_closed=fail_closed,
        )

    def tombstone_generated_image(
        self,
        image_id: str,
        *,
        reason_code: str = "",
        **expected_identity: Any,
    ):
        return workspace_folder_generated_images_store.tombstone_generated_image(
            image_id,
            reason_code=reason_code,
            db_conn_func=self.database.connect,
            logger=self,
            **expected_identity,
        )

    def apply_generated_image_projection(self, image, *, folder=None):
        return workspace_folder_generated_images.apply_generated_image_projection(
            image,
            folder=folder,
        )

    def log_content_free_event(self, event: str, level: str = "info", **fields: Any) -> None:
        self.events.append((event, dict(fields)))

    def warning(self, message: str, *args: Any, **kwargs: Any) -> None:
        self.events.append((message, dict(kwargs)))


class _StatefulFolders:
    def __init__(self, database: _StatefulDatabase | None = None) -> None:
        self.database = database

    def normalize_workspace_folder_id(self, value: Any) -> str:
        return workspace_folder_generated_images.normalize_workspace_folder_id(value)

    def get_workspace_folder(self, folder_id: str, include_deleted: bool = False):
        if self.database is None:
            return _folder()
        return _folder(
            parent_target=self.database.parent_target,
            sync_state=str(self.database.link["nextcloud_sync_state"]),
        )


class _StatefulNextcloud(
    workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClient
):
    def __init__(
        self,
        *,
        remote_present: bool,
        remote_coordinates: set[tuple[str, str, str]] | None = None,
        events: list[str] | None = None,
        before_delete: Callable[[], None] | None = None,
        after_delete: Callable[[int], None] | None = None,
    ) -> None:
        self.remote_coordinates = (
            remote_coordinates
            if remote_coordinates is not None
            else ({(PARENT_TARGET_A, "Images", TARGET_NAME)} if remote_present else set())
        )
        self.events = events
        self.before_delete = before_delete
        self.after_delete = after_delete
        self.statuses: list[int] = []
        self.moves: list[tuple[str, str]] = []
        self.requested_coordinate: tuple[str, str, str] | None = None

    @property
    def remote_present(self) -> bool:
        return bool(self.remote_coordinates)

    def _url(self, *segments: str) -> str:
        if len(segments) != 3:
            raise AssertionError("exact parent/subfolder/image coordinate required")
        self.requested_coordinate = (segments[0], segments[1], segments[2])
        return "synthetic-exact-target"

    def _request_status(self, method: str, url: str, *, data=None, headers=None):
        if method != "DELETE" or url != "synthetic-exact-target":
            raise AssertionError("only the exact synthetic DELETE is allowed")
        if self.before_delete is not None:
            self.before_delete()
        if self.events is not None:
            self.events.append("delete_exact_coordinate")
        status = 204 if self.requested_coordinate in self.remote_coordinates else 404
        if self.requested_coordinate is not None:
            self.remote_coordinates.discard(self.requested_coordinate)
        self.statuses.append(status)
        if self.after_delete is not None:
            self.after_delete(status)
        return status, ""

    def move_folder(self, source: str, target: str):
        self.moves.append((source, target))
        source_coordinates = {
            coordinate
            for coordinate in self.remote_coordinates
            if coordinate[0] == source
        }
        if not source_coordinates:
            raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                workspace_folder_nextcloud_client.REASON_TARGET_MISSING,
                http_status=404,
            )
        if any(coordinate[0] == target for coordinate in self.remote_coordinates):
            raise workspace_folder_nextcloud_client.NextcloudFolderClientError(
                workspace_folder_nextcloud_client.REASON_CONFLICT,
                http_status=409,
            )
        self.remote_coordinates.difference_update(source_coordinates)
        self.remote_coordinates.update(
            (target, subfolder, image_name)
            for _parent, subfolder, image_name in source_coordinates
        )
        return workspace_folder_nextcloud_client.NextcloudFolderResponse(
            True,
            workspace_folder_nextcloud_client.REASON_RENAME_OK,
            201,
        )


class WorkspaceFolderGeneratedImageDeleteRetryTests(unittest.TestCase):
    def _expected_identity(self) -> dict[str, str]:
        return {
            "expected_workspace_folder_id": FOLDER_ID,
            "expected_target_name_internal": TARGET_NAME,
            "expected_target_ref": TARGET_REF,
            "expected_parent_folder_ref": _parent_ref(PARENT_TARGET_A),
            "expected_parent_name_hash": _parent_hash(PARENT_TARGET_A),
        }

    def test_store_tombstones_only_the_expected_active_identity(self) -> None:
        success_database = _StatefulDatabase()

        tombstone = workspace_folder_generated_images_store.tombstone_generated_image(
            IMAGE_ID,
            expected_workspace_folder_id=FOLDER_ID,
            expected_target_name_internal=TARGET_NAME,
            expected_target_ref=TARGET_REF,
            expected_parent_folder_ref=_parent_ref(PARENT_TARGET_A),
            expected_parent_name_hash=_parent_hash(PARENT_TARGET_A),
            reason_code=workspace_folder_generated_images.REASON_DELETE_OK,
            db_conn_func=success_database.connect,
            logger=None,
        )

        self.assertIsNotNone(tombstone)
        self.assertEqual(success_database.row["local_state"], "deleted")

        cases = (
            ("image", {"generated_image_id": OTHER_IMAGE_ID}, {}),
            ("folder", {"expected_workspace_folder_id": OTHER_FOLDER_ID}, {}),
            (
                "target",
                {
                    "expected_target_name_internal": OTHER_TARGET_NAME,
                    "expected_target_ref": OTHER_TARGET_REF,
                },
                {},
            ),
            ("target_ref", {"expected_target_ref": OTHER_TARGET_REF}, {}),
            ("local_state", {}, {"local_state": "deleted"}),
            ("nextcloud_state", {}, {"nextcloud_sync_state": "deleted"}),
            ("deleted_at", {}, {"deleted_at": "2026-09-04T10:01:00Z"}),
        )
        for name, expected_overrides, row_overrides in cases:
            with self.subTest(case=name):
                database = _StatefulDatabase()
                database.row.update(row_overrides)
                row_before = dict(database.row)
                expected = {
                    "generated_image_id": IMAGE_ID,
                    **self._expected_identity(),
                }
                expected.update(expected_overrides)

                refused = workspace_folder_generated_images_store.tombstone_generated_image(
                    reason_code=workspace_folder_generated_images.REASON_DELETE_OK,
                    db_conn_func=database.connect,
                    logger=None,
                    **expected,
                )

                self.assertIsNone(refused)
                self.assertEqual(database.row, row_before)

    def test_parent_link_identity_and_state_are_part_of_the_tombstone_precondition(self) -> None:
        cases = (
            ("pending", {"nextcloud_sync_state": "sync_pending"}),
            ("other_ref", {"nextcloud_folder_ref": _parent_ref(PARENT_TARGET_B)}),
            ("other_hash", {"nextcloud_name_hash": _parent_hash(PARENT_TARGET_B)}),
            ("other_folder", {"workspace_folder_id": OTHER_FOLDER_ID}),
        )
        for name, link_overrides in cases:
            with self.subTest(case=name):
                database = _StatefulDatabase()
                database.link.update(link_overrides)
                row_before = dict(database.row)

                refused = workspace_folder_generated_images_store.tombstone_generated_image(
                    IMAGE_ID,
                    reason_code=workspace_folder_generated_images.REASON_DELETE_OK,
                    db_conn_func=database.connect,
                    logger=None,
                    **self._expected_identity(),
                )

                self.assertIsNone(refused)
                self.assertEqual(database.row, row_before)

    def test_initial_move_404_cannot_restore_linked_or_tombstone_the_old_coordinate(self) -> None:
        database = _StatefulDatabase()
        images = _StatefulImages(database)
        remote = {(PARENT_TARGET_B, "Images", TARGET_NAME)}
        nextcloud = _StatefulNextcloud(
            remote_present=False,
            remote_coordinates=remote,
        )
        runtime_folder = {
            **_folder(parent_target=PARENT_TARGET_A),
            "display_name": "Synthetic Folder A",
            "icon_key": "folder",
            "description": "",
            "sort_order": 1000,
            "created_at": "2026-09-04T10:00:00Z",
            "updated_at": "2026-09-04T10:00:00Z",
        }

        with (
            mock.patch.object(
                workspace_folders_store,
                "get_workspace_folder",
                return_value=runtime_folder,
            ),
            mock.patch.object(
                workspace_folders_store,
                "list_workspace_folders",
                return_value=[runtime_folder],
            ),
        ):
            rename = workspace_folder_nextcloud_runtime.rename_workspace_folder_nextcloud_first(
                FOLDER_ID,
                display_name="Synthetic Folder B",
                db_conn_func=database.connect,
                logger=images,
                client=nextcloud,
            )

        self.assertFalse(rename["ok"])
        self.assertEqual(
            rename["reason_code"],
            workspace_folder_nextcloud_client.REASON_TARGET_MISSING,
        )
        self.assertEqual(nextcloud.moves, [(PARENT_TARGET_A, PARENT_TARGET_B)])
        self.assertEqual(database.link["nextcloud_sync_state"], "sync_error")
        self.assertEqual(database.link["nextcloud_folder_ref"], _parent_ref(PARENT_TARGET_A))
        self.assertEqual(database.link["nextcloud_name_hash"], _parent_hash(PARENT_TARGET_A))
        self.assertEqual(
            database.link["last_sync_reason_code"],
            workspace_folder_nextcloud_client.REASON_TARGET_MISSING,
        )
        self.assertIn((PARENT_TARGET_B, "Images", TARGET_NAME), remote)

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(database),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(status, 409)
        self.assertFalse(payload["ok"])
        self.assertEqual(database.tombstone_attempts, 0)
        self.assertEqual(database.row["local_state"], "available")
        self.assertIsNone(database.row["deleted_at"])
        self.assertIn((PARENT_TARGET_B, "Images", TARGET_NAME), remote)

    def test_move_in_progress_before_delete_404_cannot_tombstone_old_parent_coordinate(self) -> None:
        database = _StatefulDatabase()
        images = _StatefulImages(database)
        remote = {(PARENT_TARGET_A, "Images", TARGET_NAME)}
        events: list[str] = []

        def begin_rename_and_move() -> None:
            database.link["nextcloud_sync_state"] = "sync_pending"
            events.append("pending_committed")
            remote.remove((PARENT_TARGET_A, "Images", TARGET_NAME))
            remote.add((PARENT_TARGET_B, "Images", TARGET_NAME))
            events.append("move_completed")

        nextcloud = _StatefulNextcloud(
            remote_present=False,
            remote_coordinates=remote,
            events=events,
            before_delete=begin_rename_and_move,
        )

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(database),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertIn((PARENT_TARGET_B, "Images", TARGET_NAME), remote)
        self.assertEqual(
            events,
            ["pending_committed", "move_completed", "delete_exact_coordinate"],
        )
        self.assertEqual(database.tombstone_attempts, 1)
        self.assertEqual(database.row["local_state"], "available")
        self.assertIsNone(database.row["deleted_at"])

    def test_durable_parent_rename_before_tombstone_refuses_stale_delete_coordinate(self) -> None:
        database = _StatefulDatabase()
        images = _StatefulImages(database)
        remote = {(PARENT_TARGET_B, "Images", TARGET_NAME)}

        def finish_parent_rename() -> None:
            database.parent_target = PARENT_TARGET_B
            database.link.update(
                {
                    "nextcloud_sync_state": "linked",
                    "nextcloud_folder_ref": _parent_ref(PARENT_TARGET_B),
                    "nextcloud_name_hash": _parent_hash(PARENT_TARGET_B),
                }
            )

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(database),
            generated_images_module=images,
            nextcloud=_StatefulNextcloud(
                remote_present=False,
                remote_coordinates=remote,
                before_delete=finish_parent_rename,
            ),
        )

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertIn((PARENT_TARGET_B, "Images", TARGET_NAME), remote)
        self.assertEqual(database.row["local_state"], "available")

    def test_delete_2xx_then_parent_rename_start_refuses_tombstone(self) -> None:
        database = _StatefulDatabase()
        images = _StatefulImages(database)

        def begin_rename_after_delete(_status: int) -> None:
            database.link["nextcloud_sync_state"] = "sync_pending"

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(database),
            generated_images_module=images,
            nextcloud=_StatefulNextcloud(
                remote_present=True,
                after_delete=begin_rename_after_delete,
            ),
        )

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertEqual(database.row["local_state"], "available")

    def test_retry_after_remote_delete_and_failed_tombstone_finishes_on_exact_404(self) -> None:
        database = _StatefulDatabase(fail_tombstones=1)
        images = _StatefulImages(database)
        nextcloud = _StatefulNextcloud(remote_present=True)

        first, first_status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(first_status, 503)
        self.assertFalse(first["ok"])
        self.assertEqual(
            first["generated_image_delete"]["delete_state"],
            "remote_deleted_local_tombstone_failed",
        )
        self.assertFalse(nextcloud.remote_present)
        self.assertEqual(database.row["local_state"], "available")
        self.assertEqual(database.tombstone_attempts, 1)

        second, second_status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(second_status, 200)
        self.assertTrue(second["ok"])
        self.assertEqual(nextcloud.statuses, [204, 404])
        self.assertEqual(
            second["generated_image_delete"]["delete_state"],
            "remote_already_missing",
        )
        self.assertEqual(
            second["reason_code"],
            "folder_generated_image_remote_already_missing",
        )
        self.assertEqual(database.tombstone_attempts, 2)
        self.assertEqual(database.row["local_state"], "deleted")
        self.assertEqual(database.row["nextcloud_sync_state"], "deleted")
        self.assertIsNotNone(database.row["deleted_at"])
        self.assertEqual(
            second["generated_image"]["generated_image_v1_technical"]["status"],
            "deleted",
        )
        self.assertNotIn(TARGET_NAME, str(second))

        third, third_status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(third_status, 410)
        self.assertFalse(third["ok"])
        self.assertEqual(nextcloud.statuses, [204, 404])
        self.assertEqual(database.tombstone_attempts, 2)

    def test_changed_target_between_404_and_tombstone_refuses_success(self) -> None:
        database = _StatefulDatabase()

        def change_durable_target(_status: int) -> None:
            database.row["target_name_internal"] = OTHER_TARGET_NAME
            database.row["target_ref"] = OTHER_TARGET_REF

        images = _StatefulImages(database)
        nextcloud = _StatefulNextcloud(
            remote_present=False,
            after_delete=change_durable_target,
        )

        payload, status = workspace_folder_generated_image_content_service.delete_workspace_folder_generated_image_response(
            FOLDER_ID,
            IMAGE_ID,
            workspace_folders_module=_StatefulFolders(),
            generated_images_module=images,
            nextcloud=nextcloud,
        )

        self.assertEqual(status, 503)
        self.assertFalse(payload["ok"])
        self.assertEqual(
            payload["generated_image_delete"]["delete_state"],
            "remote_already_missing_local_tombstone_failed",
        )
        self.assertEqual(database.tombstone_attempts, 1)
        self.assertEqual(database.row["target_name_internal"], OTHER_TARGET_NAME)
        self.assertEqual(database.row["target_ref"], OTHER_TARGET_REF)
        self.assertEqual(database.row["local_state"], "available")
        self.assertIsNone(database.row["deleted_at"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
