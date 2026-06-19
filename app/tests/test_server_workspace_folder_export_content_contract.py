from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_export_content_service  # noqa: E402
from core import workspace_folder_export_nextcloud_client  # noqa: E402
from core import workspace_folder_exports  # noqa: E402
from tests.support.server_test_bootstrap import load_server_module_for_tests  # noqa: E402


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_FOLDER_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"


class _FakeWorkspaceFolders:
    def __init__(self, *, linked=True, deleted=False, target_name="Projet-serveur"):
        self.linked = linked
        self.deleted = deleted
        self.target_name = target_name

    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        if self.normalize_workspace_folder_id(folder_id) != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Projet serveur",
            "nextcloud_target_name": self.target_name,
            "nextcloud_sync_state": "linked" if self.linked else "local_only",
            "deleted_at": "2026-06-19T12:00:00Z" if self.deleted else None,
        }


class _FakeExportsModule:
    def __init__(self, exports=None, *, fail_get=False):
        self.exports = list(exports or [])
        self.fail_get = fail_get
        self.get_calls = []
        self.events = []

    def get_export(self, export_id, *, fail_closed=True):
        self.get_calls.append({"export_id": export_id, "fail_closed": fail_closed})
        if self.fail_get:
            raise RuntimeError("raw store failure with raw-etag-secret")
        normalized = workspace_folder_exports.normalize_export_id(export_id)
        for item in self.exports:
            if workspace_folder_exports.normalize_export_id(item.get("id")) == normalized:
                return item
        return None

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeNextcloudContent:
    def __init__(self, *, content=b"contenu export", fail_reason=""):
        self.content = bytes(content)
        self.fail_reason = fail_reason
        self.read_calls = []

    def read_export(self, folder_name, export_name, *, max_bytes):
        self.read_calls.append(
            {
                "folder_name": folder_name,
                "export_name": export_name,
                "max_bytes": max_bytes,
            }
        )
        if self.fail_reason:
            raise workspace_folder_export_nextcloud_client.NextcloudExportClientError(
                self.fail_reason,
                http_status=200 if self.fail_reason == workspace_folder_exports.REASON_TOO_LARGE else 503,
            )
        return workspace_folder_export_nextcloud_client.NextcloudExportReadResponse(
            True,
            workspace_folder_exports.REASON_DOWNLOAD_OK,
            200,
            content=self.content,
        )


def _export(**overrides):
    payload = {
        "id": EXPORT_ID,
        "workspace_folder_id": FOLDER_ID,
        "title": "Export serveur",
        "title_hash": workspace_folder_exports.title_hash_for_target("Export-serveur.txt"),
        "target_name": "Export-serveur.txt",
        "export_format": "txt",
        "source_kind": "conversation",
        "source_ref": "conversation:22222222:abc123def456",
        "source_hash": "456defabc123",
        "content_hash": "789abc123def",
        "local_state": "available",
        "nextcloud_sync_state": "linked",
        "remote_export_ref": "workspace-export:11111111:abc123def456",
        "etag_value": '"raw-etag-secret"',
        "etag_hash": "123456abcdef",
        "byte_size": 42,
        "char_count": 12,
        "reason_code": "folder_export_store_ok",
        "created_at": "2026-06-19T10:00:00Z",
        "updated_at": "2026-06-19T10:00:00Z",
        "deleted_at": None,
    }
    payload.update(overrides)
    return payload


class ServerWorkspaceFolderExportContentContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_exports = self.server.workspace_folder_exports
        self.original_from_env = (
            self.server.workspace_folder_export_content_service
            .export_client.NextcloudExportClient.__dict__["from_env"]
        )
        self.fake_exports = _FakeExportsModule(exports=[_export()])
        self.fake_nextcloud = _FakeNextcloudContent()
        self.server.workspace_folders = _FakeWorkspaceFolders()
        self.server.workspace_folder_exports = self.fake_exports
        (
            self.server.workspace_folder_export_content_service
            .export_client.NextcloudExportClient.from_env
        ) = lambda environ=None: self.fake_nextcloud

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_exports = self.original_workspace_folder_exports
        (
            self.server.workspace_folder_export_content_service
            .export_client.NextcloudExportClient.from_env
        ) = self.original_from_env

    def test_download_reads_only_exact_persisted_target(self) -> None:
        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"contenu export")
        self.assertEqual(response.headers["X-Frida-Reason-Code"], "folder_export_download_ok")
        self.assertIn("attachment", response.headers["Content-Disposition"])
        self.assertIn("Export-serveur.txt", response.headers["Content-Disposition"])
        self.assertEqual(
            self.fake_nextcloud.read_calls,
            [
                {
                    "folder_name": "Projet-serveur",
                    "export_name": "Export-serveur.txt",
                    "max_bytes": workspace_folder_export_content_service.DOWNLOAD_MAX_BYTES,
                }
            ],
        )
        self.assertEqual(self.fake_exports.events[0][1]["reason_code"], "folder_export_download_ok")
        self.assertNotIn("Export-serveur.txt", str(self.fake_exports.events))
        self.assertNotIn("raw-etag-secret", str(self.fake_exports.events))

    def test_open_uses_inline_disposition(self) -> None:
        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/open")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"contenu export")
        self.assertIn("inline", response.headers["Content-Disposition"])

    def test_download_refuses_non_linked_folder_before_store_or_nextcloud(self) -> None:
        self.server.workspace_folders = _FakeWorkspaceFolders(linked=False)

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download")

        self.assertEqual(response.status_code, 409)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "folder_export_folder_not_linked")
        self.assertEqual(self.fake_exports.get_calls, [])
        self.assertEqual(self.fake_nextcloud.read_calls, [])

    def test_download_refuses_missing_persisted_folder_target_before_nextcloud(self) -> None:
        self.server.workspace_folders = _FakeWorkspaceFolders(target_name="")

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["reason_code"], "folder_export_name_invalid")
        self.assertEqual(self.fake_nextcloud.read_calls, [])

    def test_download_refuses_absent_deleted_cross_folder_or_non_linked_export(self) -> None:
        cases = (
            ([], 404, "folder_export_not_found"),
            ([_export(local_state="deleted", deleted_at="2026-06-19T12:00:00Z")], 410, "folder_export_deleted"),
            ([_export(workspace_folder_id=OTHER_FOLDER_ID)], 404, "folder_export_not_found"),
            ([_export(nextcloud_sync_state="sync_error")], 409, "folder_export_not_linked"),
        )
        for exports, status, reason in cases:
            with self.subTest(reason=reason):
                self.fake_exports = _FakeExportsModule(exports=exports)
                self.server.workspace_folder_exports = self.fake_exports
                self.fake_nextcloud.read_calls.clear()

                response = self.client.get(
                    f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download"
                )

                self.assertEqual(response.status_code, status)
                payload = response.get_json()
                self.assertEqual(payload["reason_code"], reason)
                self.assertNotIn("Export-serveur.txt", str(payload))
                self.assertNotIn("raw-etag-secret", str(payload))
                self.assertEqual(self.fake_nextcloud.read_calls, [])

    def test_download_failures_are_fail_closed_and_content_free(self) -> None:
        self.server.workspace_folder_exports = _FakeExportsModule(exports=[_export()], fail_get=True)
        store_failure = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download"
        )
        self.assertEqual(store_failure.status_code, 503)
        self.assertEqual(store_failure.get_json()["reason_code"], "folder_export_lookup_failed")
        self.assertEqual(self.fake_nextcloud.read_calls, [])

        self.server.workspace_folder_exports = _FakeExportsModule(exports=[_export()])
        self.fake_nextcloud = _FakeNextcloudContent(
            fail_reason=workspace_folder_exports.REASON_EXPORTS_TARGET_UNAVAILABLE
        )
        (
            self.server.workspace_folder_export_content_service
            .export_client.NextcloudExportClient.from_env
        ) = lambda environ=None: self.fake_nextcloud
        remote_failure = self.client.get(
            f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download"
        )
        self.assertEqual(remote_failure.status_code, 503)
        self.assertEqual(
            remote_failure.get_json()["reason_code"],
            "folder_export_exports_target_unavailable",
        )
        self.assertNotIn("raw-etag-secret", str(remote_failure.get_json()))

    def test_download_refuses_oversized_remote_without_truncation(self) -> None:
        self.fake_nextcloud = _FakeNextcloudContent(
            content=b"x" * 10,
            fail_reason=workspace_folder_exports.REASON_TOO_LARGE,
        )
        (
            self.server.workspace_folder_export_content_service
            .export_client.NextcloudExportClient.from_env
        ) = lambda environ=None: self.fake_nextcloud

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}/download")

        self.assertEqual(response.status_code, 413)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "folder_export_too_large")
        self.assertNotEqual(response.data, b"x" * 10)

    def test_global_download_route_is_absent(self) -> None:
        response = self.client.get(f"/api/exports/{EXPORT_ID}/download")

        self.assertIn(response.status_code, {404, 405})


if __name__ == "__main__":
    unittest.main()
