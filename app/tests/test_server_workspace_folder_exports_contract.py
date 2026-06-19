from __future__ import annotations

import sys
import unittest
import uuid
from pathlib import Path


APP_DIR = Path(__file__).resolve().parents[1]
if str(APP_DIR) not in sys.path:
    sys.path.insert(0, str(APP_DIR))

from core import workspace_folder_export_nextcloud_client  # noqa: E402
from core import workspace_folder_export_nextcloud_runtime  # noqa: E402
from core import workspace_folder_exports  # noqa: E402
from tests.support.server_test_bootstrap import load_server_module_for_tests  # noqa: E402


FOLDER_ID = "aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee"
OTHER_FOLDER_ID = "bbbbbbbb-bbbb-4ccc-8ddd-ffffffffffff"
CONVERSATION_ID = "22222222-3333-4444-8555-666666666666"
EXPORT_ID = "11111111-2222-4333-8444-555555555555"


class _FakeWorkspaceFolders:
    def normalize_workspace_folder_id(self, value):
        try:
            return str(uuid.UUID(str(value)))
        except (TypeError, ValueError):
            return None

    def get_workspace_folder(self, folder_id, include_deleted=False):
        normalized = self.normalize_workspace_folder_id(folder_id)
        if normalized != FOLDER_ID:
            return None
        return {
            "id": FOLDER_ID,
            "display_name": "Projet serveur",
            "nextcloud_target_name": "Projet-serveur",
            "nextcloud_sync_state": "linked",
            "deleted_at": None,
        }


class _FakeExportsModule:
    def __init__(self):
        self.stored = []
        self.events = []

    def list_exports(self, workspace_folder_id, *, include_deleted=False, fail_closed=True):
        return []

    def upsert_export(self, **fields):
        self.stored.append(dict(fields))
        target_name = fields["target_name"]
        return {
            "id": fields["export_id"],
            "workspace_folder_id": fields["workspace_folder_id"],
            "title": fields["title"],
            "title_hash": workspace_folder_exports.title_hash_for_target(target_name),
            "target_name": target_name,
            "export_format": fields["export_format"],
            "source_kind": fields["source_kind"],
            "source_ref": fields["source_ref"],
            "source_hash": fields["source_hash"],
            "content_hash": fields["content_hash"],
            "local_state": fields["local_state"],
            "nextcloud_sync_state": fields["nextcloud_sync_state"],
            "remote_export_ref": fields["remote_export_ref"],
            "etag_value": fields["etag_value"],
            "etag_hash": fields["etag_hash"],
            "byte_size": fields["byte_size"],
            "char_count": fields["char_count"],
            "reason_code": fields["reason_code"],
            "created_at": "2026-06-19T10:00:00Z",
            "updated_at": "2026-06-19T10:00:00Z",
            "deleted_at": None,
        }

    def log_content_free_event(self, event, **fields):
        self.events.append((event, fields))


class _FakeNextcloudExports:
    def __init__(self):
        self.status_calls = []
        self.put_calls = []

    def exports_status(self, folder_name):
        self.status_calls.append(folder_name)
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_STORE_OK,
            207,
        )

    def put_export(self, folder_name, export_name, content, *, media_type=""):
        self.put_calls.append(
            {
                "folder_name": folder_name,
                "export_name": export_name,
                "content": bytes(content or b""),
                "media_type": media_type,
            }
        )
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_STORE_OK,
            201,
            etag_value='"server-etag-hidden"',
        )

    def delete_export(self, folder_name, export_name, *, missing_ok=True):
        return workspace_folder_export_nextcloud_client.NextcloudExportResponse(
            True,
            workspace_folder_exports.REASON_REMOTE_COMPENSATION_OK,
            204,
        )


class _FakeConversationStore:
    def __init__(self):
        self.calls = []

    def normalize_conversation_id(self, value):
        self.calls.append(("normalize", value))
        return CONVERSATION_ID if str(value or "") == CONVERSATION_ID else None

    def get_conversation_summary(self, conversation_id, *, include_deleted=False):
        self.calls.append(("summary", conversation_id, include_deleted))
        return {
            "id": CONVERSATION_ID,
            "title": "Conversation serveur",
            "message_count": 2,
            "deleted_at": None,
        }

    def read_conversation(self, conversation_id, system_prompt):
        self.calls.append(("read", conversation_id, system_prompt))
        return {
            "id": CONVERSATION_ID,
            "messages": [
                {"id": "u-store", "role": "user", "content": "Contenu public relu store"},
                {"id": "a-store", "role": "assistant", "content": "Reponse publique relue store"},
            ],
        }


class _RuntimeWithFakeNextcloud:
    def __init__(self, nextcloud):
        self.nextcloud = nextcloud
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        kwargs["nextcloud"] = self.nextcloud
        return workspace_folder_export_nextcloud_runtime.store_workspace_folder_export_nextcloud_first(
            **kwargs
        )


class _RuntimeFailure:
    def __init__(self, reason_code):
        self.reason_code = reason_code
        self.calls = []

    def store_workspace_folder_export_nextcloud_first(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "ok": False,
            "reason_code": self.reason_code,
            "status": 503,
            "export_v1_technical": {"reason_code": self.reason_code},
            "export_nextcloud": {
                "store_state": "blocked",
                "reason_code": self.reason_code,
                "export_name_hash": "",
                "http_status_class": "none",
                "rollback": {},
            },
        }


def _request(**overrides):
    payload = {
        "export_format": "txt",
        "title": "Export serveur",
        "source_kind": "conversation",
        "explicit_source": True,
        "conversation_id": CONVERSATION_ID,
        "messages": [
            {"id": "u-injected", "role": "user", "content": "Message client injecte"},
        ],
    }
    payload.update(overrides)
    return payload


class ServerWorkspaceFolderExportsContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.server = load_server_module_for_tests()

    def setUp(self) -> None:
        self.client = self.server.app.test_client()
        self.original_workspace_folders = self.server.workspace_folders
        self.original_workspace_folder_exports = self.server.workspace_folder_exports
        self.original_workspace_folder_export_nextcloud_runtime = (
            self.server.workspace_folder_export_nextcloud_runtime
        )
        self.original_conv_store = self.server.conv_store
        self.fake_exports = _FakeExportsModule()
        self.fake_nextcloud = _FakeNextcloudExports()
        self.fake_runtime = _RuntimeWithFakeNextcloud(self.fake_nextcloud)
        self.server.workspace_folders = _FakeWorkspaceFolders()
        self.server.workspace_folder_exports = self.fake_exports
        self.server.workspace_folder_export_nextcloud_runtime = self.fake_runtime
        self.server.conv_store = _FakeConversationStore()

    def tearDown(self) -> None:
        self.server.workspace_folders = self.original_workspace_folders
        self.server.workspace_folder_exports = self.original_workspace_folder_exports
        self.server.workspace_folder_export_nextcloud_runtime = (
            self.original_workspace_folder_export_nextcloud_runtime
        )
        self.server.conv_store = self.original_conv_store

    def test_workspace_folder_export_route_is_namespaced_without_global_exports_route(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(),
        )
        global_response = self.client.post("/api/exports", json=_request())
        global_nested_response = self.client.post("/api/exports/anything", json=_request())

        self.assertEqual(response.status_code, 201)
        self.assertIn(global_response.status_code, {404, 405})
        self.assertIn(global_nested_response.status_code, {404, 405})
        routes = {rule.rule for rule in self.server.app.url_map.iter_rules()}
        self.assertIn("/api/workspace-folders/<folder_id>/exports", routes)
        self.assertFalse(any(rule == "/api/exports" or rule.startswith("/api/exports/") for rule in routes))

    def test_workspace_folder_export_route_uses_path_folder_id_over_payload(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(workspace_folder_id=OTHER_FOLDER_ID),
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(self.fake_runtime.calls[0]["request"]["workspace_folder_id"], FOLDER_ID)
        self.assertEqual(self.fake_exports.stored[0]["workspace_folder_id"], FOLDER_ID)

    def test_workspace_folder_export_route_refuses_client_export_id_before_runtime(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(export_id=EXPORT_ID),
        )

        self.assertEqual(response.status_code, 400)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_client_export_id_forbidden")
        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_workspace_folder_export_route_refuses_payload_only_selection_and_response_sources(self) -> None:
        cases = (
            (
                "message_selection",
                {
                    "selected_message_ids": ["a1"],
                    "messages": [
                        {"id": "a1", "role": "assistant", "content": "Selection publique injectee"},
                    ],
                },
            ),
            (
                "frida-response",
                {
                    "response_message_id": "a1",
                    "messages": [
                        {"id": "a1", "role": "assistant", "content": "Reponse publique injectee"},
                    ],
                },
            ),
        )
        for source_kind, extra in cases:
            with self.subTest(source_kind=source_kind):
                response = self.client.post(
                    f"/api/workspace-folders/{FOLDER_ID}/exports",
                    json=_request(source_kind=source_kind, **extra),
                )

                self.assertEqual(response.status_code, 400)
                payload = response.get_json()
                self.assertFalse(payload["ok"])
                self.assertEqual(payload["reason_code"], "folder_export_source_not_prepared")
                self.assertNotIn("Selection publique injectee", str(payload))
                self.assertNotIn("Reponse publique injectee", str(payload))

        self.assertEqual(self.fake_runtime.calls, [])
        self.assertEqual(self.fake_nextcloud.status_calls, [])
        self.assertEqual(self.fake_nextcloud.put_calls, [])
        self.assertEqual(self.fake_exports.stored, [])

    def test_workspace_folder_export_route_conversation_uses_store_not_payload_messages(self) -> None:
        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(),
        )

        self.assertEqual(response.status_code, 201)
        stored_content = self.fake_nextcloud.put_calls[0]["content"]
        self.assertIn(b"Contenu public relu store", stored_content)
        self.assertIn(b"Reponse publique relue store", stored_content)
        self.assertNotIn(b"Message client injecte", stored_content)
        self.assertIn(("read", CONVERSATION_ID, ""), self.server.conv_store.calls)

    def test_workspace_folder_export_route_returns_content_free_runtime_error(self) -> None:
        self.server.workspace_folder_export_nextcloud_runtime = _RuntimeFailure(
            workspace_folder_exports.REASON_LOOKUP_FAILED
        )

        response = self.client.post(
            f"/api/workspace-folders/{FOLDER_ID}/exports",
            json=_request(messages=[{"id": "u1", "role": "user", "content": "Payload prive"}]),
        )

        self.assertEqual(response.status_code, 503)
        payload = response.get_json()
        self.assertFalse(payload["ok"])
        self.assertEqual(payload["reason_code"], "folder_export_lookup_failed")
        self.assertNotIn("Payload prive", str(payload))
        self.assertNotIn("Message client injecte", str(payload))


if __name__ == "__main__":
    unittest.main()
