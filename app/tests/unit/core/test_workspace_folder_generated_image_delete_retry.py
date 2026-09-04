from __future__ import annotations

import sys
import unittest
from pathlib import Path
from typing import Any, Callable


APP_DIR = Path(__file__).resolve().parents[3]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_generated_image_content_service
from core import workspace_folder_generated_image_nextcloud_client
from core import workspace_folder_generated_images
from core import workspace_folder_generated_images_store


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
IMAGE_ID = "11111111-2222-4333-8444-555555555555"
TARGET_NAME = "generated-image-11111111-2222-4333-8444-555555555555.png"
TARGET_REF = workspace_folder_generated_images.target_ref_for_target(TARGET_NAME)
OTHER_TARGET_NAME = "generated-image-22222222-3333-4444-8555-666666666666.png"
OTHER_TARGET_REF = workspace_folder_generated_images.target_ref_for_target(OTHER_TARGET_NAME)
OTHER_FOLDER_ID = "bbbbbbbb-cccc-4ddd-8eee-ffffffffffff"
OTHER_IMAGE_ID = "33333333-4444-4555-8666-777777777777"


def _folder() -> dict[str, Any]:
    return {
        "id": FOLDER_ID,
        "display_name": "Synthetic folder",
        "nextcloud_target_name": "Synthetic-Folder",
        "nextcloud_sync_state": "linked",
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
    def normalize_workspace_folder_id(self, value: Any) -> str:
        return workspace_folder_generated_images.normalize_workspace_folder_id(value)

    def get_workspace_folder(self, folder_id: str, include_deleted: bool = False):
        return _folder()


class _StatefulNextcloud(
    workspace_folder_generated_image_nextcloud_client.NextcloudGeneratedImageClient
):
    def __init__(
        self,
        *,
        remote_present: bool,
        after_delete: Callable[[int], None] | None = None,
    ) -> None:
        self.remote_present = remote_present
        self.after_delete = after_delete
        self.statuses: list[int] = []

    def _url(self, *segments: str) -> str:
        return "synthetic-exact-target"

    def _request_status(self, method: str, url: str, *, data=None, headers=None):
        if method != "DELETE" or url != "synthetic-exact-target":
            raise AssertionError("only the exact synthetic DELETE is allowed")
        status = 204 if self.remote_present else 404
        self.remote_present = False
        self.statuses.append(status)
        if self.after_delete is not None:
            self.after_delete(status)
        return status, ""


class WorkspaceFolderGeneratedImageDeleteRetryTests(unittest.TestCase):
    def test_store_tombstones_only_the_expected_active_identity(self) -> None:
        success_database = _StatefulDatabase()

        tombstone = workspace_folder_generated_images_store.tombstone_generated_image(
            IMAGE_ID,
            expected_workspace_folder_id=FOLDER_ID,
            expected_target_name_internal=TARGET_NAME,
            expected_target_ref=TARGET_REF,
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
                    "expected_workspace_folder_id": FOLDER_ID,
                    "expected_target_name_internal": TARGET_NAME,
                    "expected_target_ref": TARGET_REF,
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
