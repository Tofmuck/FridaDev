from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from tests.support.server_test_bootstrap import load_server_module_for_tests  # noqa: E402


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"
CONVERSATION_ID = "22222222-3333-4444-8555-666666666666"


class _FailingWorkspaceFolders:
    def __init__(self, *, fail_normalize=False):
        self.fail_normalize = fail_normalize
        self.get_calls = []

    def normalize_workspace_folder_id(self, value):
        if self.fail_normalize:
            raise RuntimeError("raw folder normalize failure secret-ish")
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        self.get_calls.append(
            {
                "folder_id": folder_id,
                "include_deleted": include_deleted,
            }
        )
        raise RuntimeError("raw folder lookup failure secret-ish")


class _FakeExportsModule:
    def __init__(self):
        self.list_calls = []
        self.get_calls = []
        self.stored = []

    def list_exports(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        self.list_calls.append(workspace_folder_id)
        return []

    def get_export(self, export_id, *, fail_closed=True):
        self.get_calls.append(export_id)
        return None

    def upsert_export(self, **fields):
        self.stored.append(dict(fields))
        return dict(fields)


class _FakeRuntime:
    def __init__(self):
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        raise AssertionError("runtime must not be called after folder lookup failure")


class ServerWorkspaceFolderExportsLookupFailureContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_exports = self.server.workspace_folder_exports
        self.original_runtime = self.server.workspace_folder_export_nextcloud_runtime
        self.fake_folders = _FailingWorkspaceFolders()
        self.fake_exports = _FakeExportsModule()
        self.fake_runtime = _FakeRuntime()
        self.server.workspace_folders = self.fake_folders
        self.server.workspace_folder_exports = self.fake_exports
        self.server.workspace_folder_export_nextcloud_runtime = self.fake_runtime

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_exports = self.original_workspace_folder_exports
        self.server.workspace_folder_export_nextcloud_runtime = self.original_runtime

    def test_create_list_and_lookup_fail_closed_when_folder_lookup_raises(self) -> None:
        responses = [
            self.client.post(
                f"/api/workspace-folders/{FOLDER_ID}/exports",
                json={
                    "export_format": "txt",
                    "title": "Export serveur",
                    "source_kind": "conversation",
                    "explicit_source": True,
                    "conversation_id": CONVERSATION_ID,
                },
            ),
            self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports"),
            self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports/{EXPORT_ID}"),
        ]

        for response in responses:
            with self.subTest(status=response.status_code):
                self.assertEqual(response.status_code, 503)
                payload = response.get_json()
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["reason_code"], "folder_export_lookup_failed")
                self.assertNotIn("raw folder lookup failure secret-ish", str(payload))
                self.assertNotIn("Export serveur", str(payload))

        self.assertEqual(len(self.fake_folders.get_calls), 3)
        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_exports.list_calls, [])
        self.assertEqual(self.fake_exports.get_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_normalize_failure_is_fail_closed_without_folder_or_runtime_call(self) -> None:
        self.fake_folders = _FailingWorkspaceFolders(fail_normalize=True)
        self.server.workspace_folders = self.fake_folders

        response = self.client.get(f"/api/workspace-folders/{FOLDER_ID}/exports")

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertEqual(payload["reason_code"], "folder_export_lookup_failed")
        self.assertNotIn("raw folder normalize failure secret-ish", str(payload))
        self.assertEqual(self.fake_folders.get_calls, [])
        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_exports.list_calls, [])


if __name__ == "__main__":
    unittest.main()
